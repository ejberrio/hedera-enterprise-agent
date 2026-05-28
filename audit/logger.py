import logging
import threading
from typing import Optional

from api.models import AuditEntry

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_entries: list[AuditEntry] = []


def append(entry: AuditEntry) -> None:
    with _lock:
        _entries.append(entry)
    logger.info("audit tool=%s tx=%s outcome=%s", entry.tool_name, entry.transaction_id, entry.outcome)


def get_all(limit: int = 50, outcome_filter: Optional[str] = None) -> list[AuditEntry]:
    with _lock:
        entries = list(_entries)
    if outcome_filter:
        entries = [e for e in entries if e.outcome == outcome_filter]
    return entries[:limit]


def get_by_transaction_id(tx_id: str) -> Optional[AuditEntry]:
    with _lock:
        for entry in _entries:
            if entry.transaction_id == tx_id:
                return entry
    return None
