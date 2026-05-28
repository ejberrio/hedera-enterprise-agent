"""Integration tests against Hedera Testnet — requires .env with valid credentials."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def client():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_hbar_transfer_via_chat(client):
    """US1: POST /chat with HBAR transfer instruction returns transaction ID."""
    response = await client.post(
        "/chat",
        json={"message": "Transfer 1 HBAR to account 0.0.3", "session_id": "test-us1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["transaction_ids"]) > 0
    assert any("transfer_hbar_tool" in t for t in data["tools_invoked"])


@pytest.mark.asyncio
async def test_token_creation_via_chat(client):
    """US2: POST /chat with token creation returns token ID."""
    response = await client.post(
        "/chat",
        json={"message": "Create a fungible token named TestCoin with symbol TC and supply 1000", "session_id": "test-us2"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["transaction_ids"]) > 0
    assert any("create_fungible_token_tool" in t for t in data["tools_invoked"])


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """US3: GET /health returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert len(data["plugins_loaded"]) > 0


@pytest.mark.asyncio
async def test_audit_log_populated(client):
    """US3: GET /audit returns entries."""
    response = await client.get("/audit")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data and "total" in data
