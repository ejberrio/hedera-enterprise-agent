# Hedera Enterprise Agent

An enterprise-grade AI agent with plugin extensibility and real Hedera blockchain transaction capability.
Built using the [Hedera Agent Kit (Python)](https://github.com/hashgraph/hedera-agent-kit-py).

**Live Demo**: https://hedera-enterprise-agent.up.railway.app *(update after Railway deploy)*

## Features

- Natural-language REST API to execute Hedera transactions
- Core tools: HBAR transfer, fungible token creation and minting
- Custom enterprise plugin: KYC verification via Hedera Consensus Service (HCS)
- Full audit trail at `GET /audit` for all non-query tool invocations
- Health endpoint at `GET /health` confirming Hedera Testnet connectivity
- Deployed publicly on [Railway](https://railway.com) via Railpack (no Docker)

## Architecture

```
POST /chat  →  LangChain Agent (Claude)
                ├── core_account_plugin   → TRANSFER_HBAR_TOOL
                ├── core_token_plugin     → CREATE_FUNGIBLE_TOKEN_TOOL, MINT_FUNGIBLE_TOKEN_TOOL
                ├── core_consensus_plugin → CREATE_TOPIC_TOOL, SUBMIT_TOPIC_MESSAGE_TOOL
                └── enterprise_kyc_plugin → ENTERPRISE_KYC_VERIFY_TOOL (custom plugin)
```

## Prerequisites

- Python 3.11+
- A Hedera Testnet account — create one at [portal.hedera.com](https://portal.hedera.com)
- An Anthropic API key

## Local Setup

```bash
git clone https://github.com/ejberrio/hedera-enterprise-agent.git
cd hedera-enterprise-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
uvicorn main:app --reload --port 8000
```

## Usage Examples

```bash
# Health check
curl http://localhost:8000/health

# Transfer HBAR
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Transfer 1 HBAR to account 0.0.3"}'

# Create a token
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a fungible token named TestCoin with symbol TC and supply 1000"}'

# Submit a KYC verification
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Submit a KYC verification for account 0.0.12345 at level enhanced to topic 0.0.99999"}'

# View audit log
curl http://localhost:8000/audit
```

## Verify Transactions on HashScan

Take the `transaction_id` from any `/chat` response and visit:
```
https://hashscan.io/testnet/transaction/<transaction_id>
```

## Deploy to Railway

1. Push this repo to GitHub (ensure `.env` is in `.gitignore`)
2. Go to [railway.com](https://railway.com) → New Project → Deploy from GitHub repo
3. Add environment variables in Railway dashboard → Variables:
   - `HEDERA_OPERATOR_ID`
   - `HEDERA_OPERATOR_KEY`
   - `HEDERA_NETWORK=testnet`
   - `ANTHROPIC_API_KEY`
4. Railway auto-detects Python via `requirements.txt` and uses Railpack
5. Your app starts via the `Procfile` command

## Running Tests

```bash
# Unit tests (no credentials needed)
pytest tests/unit/

# Integration tests (requires valid .env)
pytest tests/integration/
```

## Feedback

Submitted to Hedera AI Studio as part of the Enterprise Agent + Plugin challenge.
See [Hedera AI Studio](https://docs.hedera.com/hedera/open-source-solutions/ai-studio-on-hedera) for more information.
