from eth_account import Account
Account.enable_unaudited_hdwallet_features()
acct = Account.create()
print("Address:", acct.address)
print("Private key:", acct.key.hex())
