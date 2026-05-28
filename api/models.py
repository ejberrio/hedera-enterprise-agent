from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class AgentResponse(BaseModel):
    reply: str
    tools_invoked: list[str]
    transaction_ids: list[str]
    session_id: Optional[str] = None


class AuditEntry(BaseModel):
    id: str
    timestamp: datetime
    tool_name: str
    transaction_id: str
    operator_account: str
    target_account: Optional[str] = None
    amount_hbar: Optional[float] = None
    token_id: Optional[str] = None
    outcome: str
    error_message: Optional[str] = None
    plugin_name: Optional[str] = None


class HealthStatus(BaseModel):
    status: str
    hedera_connected: bool
    network: str
    operator_account: str
    plugins_loaded: list[str]
    checked_at: datetime
