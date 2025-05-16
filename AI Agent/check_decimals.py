from web3 import Web3
import json

w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
token_address = "0xYOUR_TOKEN_ADDRESS"  # From deployment

with open("contracts/TokenABI.json") as f:
    abi = json.load(f)

contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=abi)
decimals = contract.functions.decimals().call()
print(f"Token decimals: {decimals}")