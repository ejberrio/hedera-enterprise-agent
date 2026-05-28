"""Agent orchestrator: builds the Hedera LangChain agent with plugins and tools."""
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from hiero_sdk_python import Client, Network, AccountId, PrivateKey
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import InMemorySaver

from hedera_agent_kit import Configuration, Context
from hedera_agent_kit.langchain import HederaLangchainToolkit
from hedera_agent_kit.langchain.response_parser_service import ResponseParserService
from hedera_agent_kit.shared.configuration import AgentMode
from hedera_agent_kit.plugins import (
    core_account_plugin,
    core_account_query_plugin,
    core_token_plugin,
    core_token_query_plugin,
    core_consensus_plugin,
    core_consensus_query_plugin,
)
from agent.plugins.enterprise_kyc import enterprise_kyc_plugin

load_dotenv()

logger = logging.getLogger(__name__)

_agent = None
_hedera_tools = []
_loaded_plugin_names: list[str] = []
_configuration: Optional[Configuration] = None


def build_agent():
    """Initialize the Hedera client, toolkit, and LangChain agent. Called once at startup."""
    global _agent, _hedera_tools, _loaded_plugin_names, _configuration

    operator_id = AccountId.from_string(os.environ["HEDERA_OPERATOR_ID"])
    operator_key = PrivateKey.from_string(os.environ["HEDERA_OPERATOR_KEY"])
    network = os.environ.get("HEDERA_NETWORK", "testnet")

    client = Client(Network(network))
    client.set_operator(operator_id, operator_key)

    _configuration = Configuration(
        plugins=[
            core_account_plugin,
            core_account_query_plugin,
            core_token_plugin,
            core_token_query_plugin,
            core_consensus_plugin,
            core_consensus_query_plugin,
            enterprise_kyc_plugin,
        ],
        tools=[],
        context=Context(
            mode=AgentMode.AUTONOMOUS,
            account_id=str(operator_id),
        ),
    )

    toolkit = HederaLangchainToolkit(client, _configuration)
    _hedera_tools = toolkit.get_tools()

    _loaded_plugin_names = [
        "core_account", "core_account_query", "core_token", "core_token_query",
        "core_consensus", "core_consensus_query", "enterprise_kyc",
    ]

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        temperature=0,
    )

    _agent = create_agent(
        model=llm,
        tools=_hedera_tools,
        system_prompt=(
            "You are an enterprise Hedera blockchain agent. You have access to Hedera tools "
            "for HBAR transfers, token creation and minting, consensus service operations, "
            "and enterprise KYC verification. When asked to perform a transaction, use the "
            "appropriate tool and always report the transaction ID. "
            "Operator account: " + str(operator_id)
        ),
        checkpointer=InMemorySaver(),
    )

    logger.info("Agent built with %d tools across %d plugins", len(_hedera_tools), len(_loaded_plugin_names))


def get_agent():
    if _agent is None:
        raise RuntimeError("Agent not initialized. Call build_agent() first.")
    return _agent


def get_hedera_tools():
    return _hedera_tools


def get_loaded_plugin_names() -> list[str]:
    return _loaded_plugin_names


def get_configuration() -> Optional[Configuration]:
    return _configuration


def make_response_parser() -> ResponseParserService:
    """Create a fresh ResponseParserService per request (tracks processed message IDs)."""
    return ResponseParserService(tools=_hedera_tools)
