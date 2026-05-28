"""Enterprise KYC verification plugin using Hedera Consensus Service.

Custom plugin for the Hedera Agent Kit demonstrating plugin extensibility.
Submits structured KYC verification records to an HCS topic as immutable
audit-trail entries — a real enterprise KYC/identity workflow.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Annotated, Optional

from hiero_sdk_python import Client
from pydantic import Field

from hedera_agent_kit import Plugin, BaseToolV2
from hedera_agent_kit.shared.configuration import Context
from hedera_agent_kit.shared.hedera_utils.hedera_builder import HederaBuilder
from hedera_agent_kit.shared.hedera_utils.hedera_parameter_normalizer import (
    HederaParameterNormaliser,
)
from hedera_agent_kit.shared.models import ToolResponse
from hedera_agent_kit.shared.parameter_schemas import BaseModelWithArbitraryTypes
from hedera_agent_kit.shared.strategies.tx_mode_strategy import handle_transaction
from hedera_agent_kit.shared.utils.default_tool_output_parsing import (
    transaction_tool_output_parser,
)

logger = logging.getLogger(__name__)

ENTERPRISE_KYC_VERIFY_TOOL = "enterprise_kyc_verify_tool"


class KycVerifyParameters(BaseModelWithArbitraryTypes):
    account_id: Annotated[
        str,
        Field(description="The Hedera account ID to KYC-verify (e.g. 0.0.12345)."),
    ]
    kyc_level: Annotated[
        str,
        Field(description="KYC verification level: basic, enhanced, or full."),
    ] = "basic"
    topic_id: Annotated[
        str,
        Field(description="The HCS topic ID to submit the KYC record to (e.g. 0.0.99999)."),
    ]
    verifier_notes: Annotated[
        Optional[str],
        Field(description="Optional notes from the verifier."),
    ] = None


class KycVerifyTool(BaseToolV2):
    """Custom enterprise tool: submits a KYC verification record to Hedera HCS."""

    def __init__(self, context: Context):
        self.method: str = ENTERPRISE_KYC_VERIFY_TOOL
        self.name: str = "Enterprise KYC Verify"
        self.description: str = (
            "Submit a KYC (Know Your Customer) verification record to a Hedera Consensus Service "
            "topic. Use this tool to record identity verification for a Hedera account on the "
            "immutable HCS ledger.\n\nParameters:\n"
            "- account_id (str, required): The Hedera account ID being verified (e.g. 0.0.12345)\n"
            "- kyc_level (str, optional): Verification level: basic, enhanced, or full (default: basic)\n"
            "- topic_id (str, required): The HCS topic ID to write the KYC record to\n"
            "- verifier_notes (str, optional): Additional notes from the verifier\n"
        )
        self.parameters = KycVerifyParameters
        self.outputParser = transaction_tool_output_parser

    async def normalize_params(
        self, params: Any, context: Context, client: Client
    ) -> Any:
        if isinstance(params, dict):
            p = KycVerifyParameters(**params)
        else:
            p = params

        kyc_record = json.dumps({
            "type": "kyc_verification",
            "account_id": p.account_id,
            "kyc_level": p.kyc_level,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "verified_by_operator": context.account_id,
            "notes": p.verifier_notes,
        })

        return await HederaParameterNormaliser.normalise_submit_topic_message(
            {"topic_id": p.topic_id, "message": kyc_record},
            context,
            client,
        )

    async def core_action(
        self, normalized_params: Any, context: Context, client: Client
    ) -> Any:
        return HederaBuilder.submit_topic_message(normalized_params)

    async def secondary_action(
        self, transaction: Any, client: Client, context: Context
    ) -> ToolResponse:
        def post_process(resp) -> str:
            tx_id = str(resp.transaction_id) if resp.transaction_id else "N/A"
            return f"KYC verification submitted to HCS. Transaction ID: {tx_id}"

        return await handle_transaction(transaction, client, context, post_process)

    async def handle_error(self, error: Exception, context: Context) -> ToolResponse:
        msg = f"Failed to submit KYC verification: {str(error)}"
        logger.error("[%s] %s", ENTERPRISE_KYC_VERIFY_TOOL, msg)
        return ToolResponse(human_message=msg, error=msg)


enterprise_kyc_plugin = Plugin(
    name="enterprise-kyc-plugin",
    version="1.0.0",
    description="Enterprise KYC verification plugin using Hedera Consensus Service",
    tools=lambda context: [KycVerifyTool(context)],
)

enterprise_kyc_plugin_tool_names = {
    "ENTERPRISE_KYC_VERIFY_TOOL": ENTERPRISE_KYC_VERIFY_TOOL,
}
