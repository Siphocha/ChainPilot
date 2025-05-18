from dotenv import load_dotenv
import os

load_dotenv()

# Validate environment variables
def validate_env_vars():
    required_vars = ["NETWORK_RPC_URL", "NETWORK_CHAIN_ID", "WALLET_ADDRESS", "WALLET_PRIVATE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

validate_env_vars()

NETWORK = {
    "name": "base_mainnet",
    "rpc_url": os.getenv("NETWORK_RPC_URL", "https://mainnet.base.org"),
    "chain_id": int(os.getenv("NETWORK_CHAIN_ID", 8453))
}
WALLET = {
    "private_key": os.getenv("WALLET_PRIVATE_KEY"),
    "address": os.getenv("WALLET_ADDRESS")
}
CONTRACT_ADDRESSES = {
    "Executor": os.getenv("CONTRACT_EXECUTOR_ADDRESS", "0x3175F8bDBEE3FaE7e3369eB352BADcd4237161AC"),
    "Scheduler": os.getenv("CONTRACT_SCHEDULER_ADDRESS", "0x1dc4052FDEc1CC197a280B19a657704bc1910BBf"),
    "Token": os.getenv("CONTRACT_TOKEN_ADDRESS", "0x_MAINNET_TOKEN_ADDRESS_")
}