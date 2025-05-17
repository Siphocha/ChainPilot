from dotenv import load_dotenv
import os

load_dotenv()

NETWORK = {
    "name": "base_mainnet",
    "rpc_url": os.getenv("NETWORK_RPC_URL", "https://mainnet.base.org"),  # Replace with Alchemy URL if needed
    "chain_id": int(os.getenv("NETWORK_CHAIN_ID", 8453))  # Base Mainnet chain ID
}
WALLET = {
    "private_key": os.getenv("WALLET_PRIVATE_KEY"),
    "address": os.getenv("WALLET_ADDRESS")
}
CONTRACT_ADDRESSES = {
    "Executor": "0x3175F8bDBEE3FaE7e3369eB352BADcd4237161AC",  # Replace with actual address
    "Scheduler": "0x1dc4052FDEc1CC197a280B19a657704bc1910BBf",  # Replace with actual address
    "Token": "0x_MAINNET_TOKEN_ADDRESS_"  # Add if needed for token transfers
}

# ABI directory path
ABI_DIR = r"C:\Users\jules\Desktop\ChainPilot\AI Agent\ChainPilot\abis"