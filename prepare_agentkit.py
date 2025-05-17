from coinbase_agentkit import AgentKit, AgentKitConfig
from wallet_provider import wallet_provider
from ChainPilot.actions.chainpilot_actions import ChainPilotActions

# Register wallet and ChainPilot's custom actions
agentkit = AgentKit(AgentKitConfig(
    wallet_provider=wallet_provider,
    action_providers=[
        ChainPilotActions(),
    ]
))

