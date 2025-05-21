from dotenv import load_dotenv
import os

load_dotenv()

CONTRACT_ADDRESSES = {
    "Executor": os.getenv("CONTRACT_EXECUTOR_ADDRESS", "0x3175F8bDBEE3FaE7e3369eB352BADcd4237161AC"),
    "Scheduler": os.getenv("CONTRACT_SCHEDULER_ADDRESS", "0x1dc4052FDEc1CC197a280B19a657704bc1910BBf"),
}

NETWORK = {
    "rpc_url": f"https://base-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY', 'eIHNpCWBx2UK_lG1EoqlrlCBdYu1bZK1')}",
    "chain_id": 8453,  # Base mainnet chain ID
}

WALLET = {
    "private_key": os.getenv("PRIVATE_KEY", "0xbe379a7f65633e830c36c4c458d52be9cac1f857a57ab65bd7a6a2e990d4e81d"),  # Replace with your private key
}

# Optional: Add BASESCAN_API_KEY for verification if needed
os.environ["BASESCAN_API_KEY"] = "UW519K6C66F6E4YTZHVRD87X29BG9U3ZQ3"


# from dotenv import load_dotenv
# import os

# load_dotenv()

# # Validate environment variables
# def validate_env_vars():
#     required_vars = ["NETWORK_RPC_URL", "NETWORK_CHAIN_ID", "WALLET_ADDRESS", "WALLET_PRIVATE_KEY"]
#     missing_vars = [var for var in required_vars if not os.getenv(var)]
#     if missing_vars:
#         raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# validate_env_vars()

# NETWORK = {
#     "name": "base_mainnet",
#     "rpc_url": os.getenv("NETWORK_RPC_URL", "https://mainnet.base.org"),
#     "chain_id": int(os.getenv("NETWORK_CHAIN_ID", 8453))
# }
# WALLET = {
#     "private_key": os.getenv("WALLET_PRIVATE_KEY"),
#     "address": os.getenv("WALLET_ADDRESS")
# }
# CONTRACT_ADDRESSES = {
#     "Executor": os.getenv("CONTRACT_EXECUTOR_ADDRESS", "0x3175F8bDBEE3FaE7e3369eB352BADcd4237161AC"),
#     "Scheduler": os.getenv("CONTRACT_SCHEDULER_ADDRESS", "0x1dc4052FDEc1CC197a280B19a657704bc1910BBf"),
#     "Token": os.getenv("CONTRACT_TOKEN_ADDRESS", "0xdBe0A782B3f0219475a5Ce7Ca35ae514eeeAB696")
# }