from coinbase_agentkit_openai_agents_sdk import get_openai_agents_sdk_tools
from agentkit import Agent
from prepare_agentkit import prepare_agentkit
from actions.chainpilot_actions import TOOLS

AGENT_INSTRUCTIONS = (
    "You are ChainPilot, a blockchain automation AI agent on the Base network. You can manage a secure digital wallet, "
    "send and receive tokens, schedule token transfers, execute smart contract actions, create ERC-20 tokens, deploy and "
    "mint ERC-721 NFTs, and register Basenames for identity management. Your wallet supports Base Sepolia (testnet) and "
    "Base Mainnet, with testnet faucet access for ETH/USDC. Users can switch networks via the .env file.\n\n"
    
    "Core capabilities:\n"
    "- Check wallet balances and request testnet tokens\n"
    "- Send tokens and schedule transfers\n"
    "- Execute actions via ChainPilotExecutor\n"
    "- Create and manage ERC-20 tokens and NFTs\n"
    "- Register Basenames (e.g., myname.basetest.eth)\n\n"
    
    "Explain technical terms simply (e.g., testnet as a sandbox for testing). For 5XX errors, suggest retrying later. "
    "If a user requests an unsupported action, explain your capabilities and refer them to docs.cdp.coinbase.com for "
    "custom implementations. You're an AI with payment and automation capabilities, enabling unique blockchain interactions."
)

def create_agent():
    """Initialize the agent with tools from AgentKit and custom actions."""
    # Get AgentKit instance
    agentkit = prepare_agentkit()
    
    # Get OpenAI Agents SDK tools
    agentkit_tools = get_openai_agents_sdk_tools(agentkit)
    
    # Combine AgentKit tools with custom action tools
    all_tools = agentkit_tools + TOOLS

    # Create Agent
    agent = Agent(
        name="ChainPilot",
        instructions=AGENT_INSTRUCTIONS,
        tools=all_tools
    )

    return agent, {}  # Return empty config to match Langchain interface

# Save agent configuration
agent = Agent(
    name="ChainPilot",
    description="An AI agent to help users interact with blockchain smart contracts and manage tokens/NFTs.",
    llm_provider="openai",
    model="gpt-3.5-turbo",
    tools=["stake_tool", "transfer_tool", "unstake_tool", "check_portfolio_tool", "create_token", "deploy_nft", "mint_nft", "register_basename"],
    prompt=(
        "You are ChainPilot, an AI assistant for blockchain interactions. Understand commands like "
        "'Stake 50 USDC weekly', 'Create token MyToken MTK 1000000', or 'Register basename myname' and respond with "
        "structured JSON actions."
    )
)
agent.save("chainpilot_agent.yaml")