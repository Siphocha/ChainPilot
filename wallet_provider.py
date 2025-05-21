import os
import json
import logging
from dotenv import load_dotenv
from web3 import Web3
from types import SimpleNamespace

# Attempt to load environment variables from .env (for local development), but don't fail if missing
load_dotenv()  # Silently fails if .env is not present, which is fine for Render

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment vars
PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
NETWORK_NAME = os.getenv("NETWORK_NAME", "base_mainnet")
RPC_URL = os.getenv("NETWORK_RPC_URL")

# Validate required environment variables
required_vars = {
    "WALLET_PRIVATE_KEY": PRIVATE_KEY,
    "NETWORK_RPC_URL": RPC_URL,
}
missing_vars = [key for key, value in required_vars.items() if not value]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

class CustomWalletProvider:
    def __init__(self, base_provider):
        self.base_provider = base_provider

    def get_address(self):
        return self.base_provider.get_address()

    def get_network(self):
        network_id = self.base_provider.get_network()
        chain_id = {
            "goerli": 5,
            "sepolia": 11155111,
            "mainnet": 1,
            "hardhat": 84532,
            "base_mainnet": 8453
        }.get(network_id, None)
        if chain_id is None:
            raise ValueError(f"Unsupported network_id: {network_id}")
        return SimpleNamespace(
            network_id=network_id,
            chain_id=chain_id,
            protocol_family="ethereum"
        )

    def transfer_token(self, token_contract, to, amount):
        if not Web3.is_checksum_address(token_contract):
            raise ValueError(f"Invalid token contract address: {token_contract}")
        if not Web3.is_checksum_address(to):
            raise ValueError(f"Invalid recipient address: {to}")
        return self.base_provider.transfer_token(token_contract, to, amount)

    def get_name(self):
        return "Custom Wallet Provider"

    def get_balance(self):
        return self.base_provider.get_balance()

    def vote(self, wallet_provider, params):
        proposal_id = params.get("proposal_id")
        vote_choice = params.get("vote_choice", "yes")
        return f"Voted '{vote_choice}' on proposal {proposal_id}"

    def call_contract(self, contract_address, abi, function_name, args):
        return self.base_provider.call_contract(contract_address, abi, function_name, args)

class WalletProvider:
    def __init__(self, private_key, network_name, rpc_url):
        self.private_key = private_key
        self.network_name = network_name
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to the blockchain network. Check the RPC_URL.")
        self.account = self.w3.eth.account.from_key(private_key)

    def get_address(self):
        return self.account.address

    def get_balance(self):
        try:
            balance = self.w3.eth.get_balance(self.account.address)
            return {"ETH": self.w3.from_wei(balance, 'ether')}
        except Exception as e:
            logging.error("Error getting balance: %s", e)
            return {}

    def get_name(self):
        return "ChainPilot Wallet"

    def get_network(self):
        return self.network_name

    def native_transfer(self, to, value):
        try:
            tx = {
                'to': Web3.to_checksum_address(to),
                'value': self.w3.to_wei(value, 'ether'),
                'gas': 21000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'chainId': self.w3.eth.chain_id
            }
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            logging.info(f"Transferred {value} ETH to {to}, tx hash: {tx_hash.hex()}")
            return {"status": "success", "transaction_hash": tx_hash.hex()}
        except Exception as e:
            logging.error(f"Transfer failed: {e}")
            return {"status": "error", "message": str(e)}

    def transfer_token(self, token_contract, to, amount):
        try:
            logging.warning("Token transfer not implemented: requires TokenABI.json and contract deployment.")
            return {"status": "error", "message": "Token transfer not implemented in wallet provider."}
        except Exception as e:
            logging.error(f"Token transfer failed: {e}")
            return {"status": "error", "message": str(e)}

    def call_contract(self, contract_address, abi, function_name, args):
        try:
            contract = self.w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
            tx = getattr(contract.functions, function_name)(*args).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            logging.info(f"Called {function_name} on contract {contract_address}, tx hash: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logging.error(f"Contract call failed: {e}")
            return f"Error: {e}"

    def sign_message(self, message):
        try:
            signed_message = self.account.sign_message(self.w3.solidity_keccak(['string'], [message]))
            return signed_message.signature.hex()
        except Exception as e:
            logging.error(f"Message signing failed: {e}")
            return f"Error: {e}"

def load_abi(file_path: str):
    try:
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load ABI from {file_path}: {e}")
        raise

wallet_provider = WalletProvider(private_key=PRIVATE_KEY, network_name=NETWORK_NAME, rpc_url=RPC_URL)
wallet_provider_dict = CustomWalletProvider(base_provider=wallet_provider)