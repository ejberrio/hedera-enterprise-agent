"""Unit tests for audit/logger.py — no Hedera credentials required."""
from datetime import datetime, timezone

import pytest

import audit.logger as audit_logger
from api.models import AuditEntry


def _make_entry(
    tool_name: str = "transfer_hbar_tool",
    tx_id: str = "0.0.12345@123.000",
    outcome: str = "SUCCESS",
) -> AuditEntry:
    return AuditEntry(
        id="test-id",
        timestamp=datetime.now(timezone.utc),
        tool_name=tool_name,
        transaction_id=tx_id,
        operator_account="0.0.99999",
        outcome=outcome,
    )


@pytest.fixture(autouse=True)
def clear_audit_log():
    import audit.logger as _logger
    with _logger._lock:
        _logger._entries.clear()
    yield


def test_append_and_get_all():
    audit_logger.append(_make_entry())
    results = audit_logger.get_all()
    assert len(results) == 1
    assert results[0].tool_name == "transfer_hbar_tool"


def test_filter_by_outcome_success():
    audit_logger.append(_make_entry(outcome="SUCCESS"))
    audit_logger.append(_make_entry(tool_name="create_fungible_token_tool", outcome="FAILURE"))
    results = audit_logger.get_all(outcome_filter="SUCCESS")
    assert len(results) == 1
    assert results[0].outcome == "SUCCESS"


def test_filter_by_outcome_failure():
    audit_logger.append(_make_entry(outcome="FAILURE"))
    audit_logger.append(_make_entry(outcome="SUCCESS"))
    results = audit_logger.get_all(outcome_filter="FAILURE")
    assert len(results) == 1
    assert results[0].outcome == "FAILURE"


def test_get_by_transaction_id_found():
    audit_logger.append(_make_entry(tx_id="0.0.12345@999.000"))
    found = audit_logger.get_by_transaction_id("0.0.12345@999.000")
    assert found is not None
    assert found.transaction_id == "0.0.12345@999.000"


def test_get_by_transaction_id_not_found():
    found = audit_logger.get_by_transaction_id("0.0.99999@000.000")
    assert found is None


def test_limit_respected():
    for i in range(10):
        audit_logger.append(_make_entry(tx_id=f"0.0.12345@{i}.000"))
    results = audit_logger.get_all(limit=3)
    assert len(results) == 3
