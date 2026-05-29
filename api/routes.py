"""FastAPI route handlers for the Hedera Enterprise Agent."""
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import unquote
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from agent.core import get_agent, get_configuration, get_loaded_plugin_names, make_response_parser
from api.models import AgentRequest, AgentResponse, AuditEntry, HealthStatus
import audit.logger as audit_logger

logger = logging.getLogger(__name__)
router = APIRouter()

NON_QUERY_TOOLS = {
    "transfer_hbar_tool",
    "create_account_tool",
    "update_account_tool",
    "delete_account_tool",
    "create_fungible_token_tool",
    "create_non_fungible_token_tool",
    "mint_fungible_token_tool",
    "mint_non_fungible_token_tool",
    "associate_token_tool",
    "dissociate_token_tool",
    "airdrop_fungible_token_tool",
    "create_topic_tool",
    "submit_topic_message_tool",
    "delete_topic_tool",
    "update_topic_tool",
    "enterprise_kyc_verify_tool",
    "approve_hbar_allowance_tool",
    "transfer_hbar_with_allowance_tool",
}

PLUGIN_NAME_MAP = {
    "transfer_hbar_tool": "core_account",
    "create_account_tool": "core_account",
    "create_fungible_token_tool": "core_token",
    "create_non_fungible_token_tool": "core_token",
    "mint_fungible_token_tool": "core_token",
    "mint_non_fungible_token_tool": "core_token",
    "associate_token_tool": "core_token",
    "create_topic_tool": "core_consensus",
    "submit_topic_message_tool": "core_consensus",
    "enterprise_kyc_verify_tool": "enterprise_kyc",
}


@router.post("/chat", response_model=AgentResponse)
async def chat(request: AgentRequest):
    try:
        agent = get_agent()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    session_id = request.session_id or str(uuid4())
    config = {"configurable": {"thread_id": session_id}}

    try:
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": request.message}]},
            config=config,
        )
    except Exception as e:
        error_msg = str(e).lower()
        if any(k in error_msg for k in ("network", "connect", "timeout", "grpc", "socket")):
            raise HTTPException(
                status_code=503,
                detail="Hedera network unavailable. Please retry in a moment.",
            )
        logger.exception("Agent invocation failed")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    reply = response["messages"][-1].content if response.get("messages") else ""
    tools_invoked: list[str] = []
    transaction_ids: list[str] = []

    parser = make_response_parser()
    parsed_tool_calls = parser.parse_new_tool_messages(response)
    operator_id = os.environ.get("HEDERA_OPERATOR_ID", "unknown")

    for tool_call in parsed_tool_calls:
        tool_name = tool_call.toolName
        raw = tool_call.parsedData.get("raw", {}) if isinstance(tool_call.parsedData, dict) else {}
        error_val = raw.get("error") if raw else None

        tools_invoked.append(tool_name)

        tx_id = raw.get("transaction_id") or "N/A"
        if tx_id and tx_id != "N/A":
            transaction_ids.append(str(tx_id))

        if tool_name in NON_QUERY_TOOLS:
            entry = AuditEntry(
                id=str(uuid4()),
                timestamp=datetime.now(timezone.utc),
                tool_name=tool_name,
                transaction_id=str(tx_id),
                operator_account=operator_id,
                token_id=str(raw.get("token_id")) if raw.get("token_id") else None,
                outcome="FAILURE" if error_val else "SUCCESS",
                error_message=str(error_val) if error_val else None,
                plugin_name=PLUGIN_NAME_MAP.get(tool_name),
            )
            audit_logger.append(entry)
            logger.info("tool=%s tx=%s", tool_name, tx_id)

    return AgentResponse(
        reply=reply,
        tools_invoked=tools_invoked,
        transaction_ids=transaction_ids,
        session_id=session_id,
    )


@router.get("/health", response_model=HealthStatus)
async def health():
    hedera_connected = False
    try:
        config = get_configuration()
        if config and config.context and config.context.account_id:
            hedera_connected = True
    except Exception as e:
        logger.warning("Hedera connectivity check failed: %s", e)

    operator_raw = os.environ.get("HEDERA_OPERATOR_ID", "unknown")
    masked = f"0.0.***{operator_raw[-4:]}" if len(operator_raw) > 4 else operator_raw

    return HealthStatus(
        status="healthy" if hedera_connected else "degraded",
        hedera_connected=hedera_connected,
        network=os.environ.get("HEDERA_NETWORK", "testnet"),
        operator_account=masked,
        plugins_loaded=get_loaded_plugin_names(),
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/audit")
async def get_audit(
    limit: int = Query(default=50, ge=1, le=200),
    outcome: Optional[str] = Query(default=None, pattern="^(SUCCESS|FAILURE)$"),
):
    entries = audit_logger.get_all(limit=limit, outcome_filter=outcome)
    return {"entries": [e.model_dump() for e in entries], "total": len(entries)}


@router.get("/audit/{transaction_id}")
async def get_audit_entry(transaction_id: str):
    tx_id = unquote(transaction_id)
    entry = audit_logger.get_by_transaction_id(tx_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Transaction ID not found in audit log")
    return entry.model_dump()
