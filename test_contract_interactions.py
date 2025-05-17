from web3 import Web3
import json
from config import NETWORK, WALLET, CONTRACT_ADDRESSES

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(NETWORK["rpc_url"]))

# Load Token ABI
with open("contracts/TokenABI.json", "r") as f:
    token_abi = json.load(f)["abi"]

# Token Contract
token_contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESSES["Token"]), abi=token_abi)

# Fetch Token Decimals
def fetch_token_decimals():
    try:
        decimals = token_contract.functions.decimals().call()
        print(f"Token Decimals: {decimals}")
    except Exception as e:
        print(f"Error fetching token decimals: {e}")

# Perform Token Transfer
def transfer_tokens(to_address, amount):
    try:
        decimals = token_contract.functions.decimals().call()
        amount_wei = int(amount * (10 ** decimals))
        tx = token_contract.functions.transfer(to_address, amount_wei).build_transaction({
            "from": Web3.to_checksum_address(WALLET["address"]),
            "gas": 2000000,
            "gasPrice": w3.toWei("10", "gwei"),
            "nonce": w3.eth.get_transaction_count(Web3.to_checksum_address(WALLET["address"]))
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=WALLET["private_key"])
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"Transaction sent: {tx_hash.hex()}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction receipt: {receipt}")
    except Exception as e:
        print(f"Error transferring tokens: {e}")

if __name__ == "__main__":
    fetch_token_decimals()
    transfer_tokens("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", 0.5)