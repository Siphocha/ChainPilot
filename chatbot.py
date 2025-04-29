import sys
import traceback
print("Python executable:", sys.executable)
print("Python path:", sys.path)

import asyncio
from dotenv import load_dotenv  # Import dotenv for loading environment variables

# Debugging: Check available attributes in agentkit
try:
    import agentkit
    print("Available in agentkit:", dir(agentkit))
except ImportError as e:
    print("Error importing agentkit:", e)
    sys.exit(1)

try:
    from create_agent import create_agent
    print("Successfully imported create_agent")
except ImportError as e:
    print("Error importing create_agent:", e)
    sys.exit(1)

"""
AgentKit Chatbot Interface

This file provides a command-line interface for interacting with an AgentKit-powered AI agent.
It supports chat mode for interactive conversations with the agent.

Use this as a starting point for building your own agent interface or integrate
the agent into your existing applications.

# Want to contribute?
Join us in shaping AgentKit! Check out the contribution guide:  
- https://github.com/coinbase/agentkit/blob/main/CONTRIBUTING.md
- https://discord.gg/CDP
"""

# Load environment variables from the .env file
print("Loading environment variables...")
load_dotenv()
print("Environment variables loaded")


async def run_chat_mode(agent, config):
    """Run the agent interactively based on user input."""
    print("Starting chat mode... Type 'exit' to end.")
    print("Agent type:", type(agent))
    print("Agent attributes:", dir(agent))
    print("Config:", config)
    
    # Display agent details to infer capabilities
    print("Agent details:")
    for attr in ['name', 'instructions', 'model', 'tools', 'handoff_description']:
        if hasattr(agent, attr):
            value = getattr(agent, attr)
            if attr == 'tools':
                print("  tools:")
                for tool in value:
                    print(f"    - {tool.name}: {tool.description}")
            else:
                print(f"  {attr}: {value}")
    
    while True:
        try:
            user_input = input("\nPrompt: ")
            if user_input.lower() == "exit":
                break

            # Simple tool selection based on keywords
            selected_tool = None
            tool_params = {}
            user_input_lower = user_input.lower()

            # Map user input to tools (basic keyword matching)
            for tool in getattr(agent, 'tools', []):
                if 'get balance' in user_input_lower and tool.name == 'WalletActionProvider_get_balance':
                    selected_tool = tool
                    tool_params = {}  # No params needed
                elif 'wallet details' in user_input_lower and tool.name == 'WalletActionProvider_get_wallet_details':
                    selected_tool = tool
                    tool_params = {}  # No params needed
                elif 'request faucet' in user_input_lower and tool.name == 'CdpApiActionProvider_request_faucet_funds':
                    selected_tool = tool
                    asset_id = 'eth' if 'eth' in user_input_lower else 'usdc' if 'usdc' in user_input_lower else None
                    tool_params = {'asset_id': asset_id}
                elif 'check reputation' in user_input_lower and tool.name == 'CdpApiActionProvider_address_reputation':
                    selected_tool = tool
                    # Prompt for required parameters
                    print("Please provide the Ethereum address to check:")
                    address = input("Address: ")
                    print("Please provide the network (e.g., 'base-mainnet'):")
                    network = input("Network: ")
                    tool_params = {'address': address, 'network': network}

            # Execute the selected tool or fallback
            try:
                if selected_tool:
                    print(f"Selected tool: {selected_tool.name}")
                    print(f"Tool params: {tool_params}")
                    print(f"Input string: {user_input}")
                    # Call the tool's on_invoke_tool function with both params and input_str
                    output = await selected_tool.on_invoke_tool(tool_params, user_input)
                    print("Tool output:", output)
                else:
                    print("No matching tool found for input. I can assist with the following:")
                    if hasattr(agent, 'instructions'):
                        print(f"Instructions: {agent.instructions}")
                    print("Available tools:")
                    for tool in getattr(agent, 'tools', []):
                        print(f"- {tool.name}: {tool.description}")
            except TypeError as e:
                print(f"TypeError invoking tool (possibly incorrect arguments): {e}")
                traceback.print_exc()
            except Exception as e:
                print(f"Error invoking tool: {e}")
                traceback.print_exc()

        except KeyboardInterrupt:
            print("\nGoodbye Agent!")
            sys.exit(0)


async def main():
    """Start the chatbot agent."""
    print("Starting main function...")
    try:
        print("Calling create_agent...")
        agent_executor, config = create_agent()
        print("Agent created successfully")
        await run_chat_mode(agent=agent_executor, config=config)
    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("Running chatbot.py...")
    asyncio.run(main())