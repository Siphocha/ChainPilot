from typing import Dict, Any, Optional
from web3 import Web3
from web3.exceptions import TransactionNotFound, TimeExhausted
from utils import load_abi, get_logger
import time
from config import CONTRACT_ADDRESSES, NETWORK, WALLET
import logging
import os

logger = get_logger(__name__)

class ChainPilotActions:
    """Handles blockchain actions such as token transfers, scheduling transfers, and task management.

    Attributes:
        w3 (Web3): Web3 instance for interacting with the blockchain.
        wallet_address (str): The wallet address derived from the private key.
    """

    def __init__(self):
        """Initialize the ChainPilotActions with Web3 and wallet setup."""
        self.w3 = Web3(Web3.HTTPProvider(NETWORK["rpc_url"]))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to the blockchain network. Check the RPC URL.")
        
        private_key = WALLET["private_key"]
        if len(private_key) != 66 or not private_key.startswith("0x") or len(bytes.fromhex(private_key[2:])) != 32:
            raise ValueError("Invalid private key length. Must be 32 bytes (66 hex chars with 0x prefix).")
        self.wallet_address = self.w3.eth.account.from_key(private_key).address
        logger.info(f"Initialized ChainPilotActions with wallet address: {self.wallet_address}")

    def _build_and_send_transaction(self, tx: Dict[str, Any], retries: int = 3, delay: int = 5) -> bytes:
        """Build and send a transaction with retry logic and dynamic gas estimation.

        Args:
            tx (Dict[str, Any]): Transaction dictionary to send.
            retries (int): Number of retry attempts for failed transactions.
            delay (int): Delay between retries in seconds.

        Returns:
            bytes: Transaction hash of the successful transaction.

        Raises:
            Exception: If all retries fail or the transaction cannot be processed.
        """
        try:
            gas_estimate = self.w3.eth.estimate_gas(tx)
            tx['gas'] = int(gas_estimate * 1.2)  # Add 20% buffer to gas estimate
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}. Using default gas value.")
            tx['gas'] = 300000  # Fallback to default gas

        if 'gasPrice' not in tx:
            tx['gasPrice'] = self.w3.eth.gas_price

        attempt = 0
        while attempt < retries:
            try:
                signed_tx = self.w3.eth.account.sign_transaction(tx, WALLET["private_key"])
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if receipt["status"] == 0:
                    raise ValueError("Transaction failed on the blockchain.")
                logger.info(f"Transaction successful: {tx_hash.hex()}")
                return tx_hash
            except (TransactionNotFound, TimeExhausted, ValueError) as e:
                attempt += 1
                logger.warning(f"Transaction attempt {attempt}/{retries} failed: {e}")
                if attempt == retries:
                    raise Exception(f"Transaction failed after {retries} attempts: {e}")
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Unexpected error during transaction: {e}")
                raise e

    def send_token(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send tokens to a specified address using the Executor contract.

        Args:
            wallet_provider (Dict): Wallet provider information (not used currently).
            args (Dict[str, Any]): Arguments containing 'to' (address) and 'amount' (float).

        Returns:
            Dict[str, Any]: Result with status and transaction hash or error message.
        """
        try:
            if not args.get("to") or not args.get("amount"):
                raise ValueError("Missing required fields: 'to' and 'amount' are required.")
            if not isinstance(args["amount"], (int, float)) or args["amount"] <= 0:
                raise ValueError("Amount must be a positive number.")

            to_address = Web3.to_checksum_address(args["to"])
            executor_address = Web3.to_checksum_address(CONTRACT_ADDRESSES["Executor"])
            executor_contract = self.w3.eth.contract(address=executor_address, abi=load_abi("ChainPilotExecutor"))

            payload = Web3.to_hex(Web3.keccak(text="transfer"))
            value_wei = self.w3.to_wei(args["amount"], "ether")
            task_hash = Web3.keccak(hexstr=Web3.to_hex(Web3.solidity_keccak(
                ['address', 'bytes', 'uint256'],
                [to_address, payload, value_wei]
            )))

            balance = self.w3.eth.get_balance(self.wallet_address)
            if balance < value_wei:
                raise ValueError(f"Insufficient balance: {self.w3.from_wei(balance, 'ether')} ETH available, "
                               f"{self.w3.from_wei(value_wei, 'ether')} ETH required.")

            deadline = int(time.time()) + 86400
            approve_tx = executor_contract.functions.approveTask(
                to_address, payload, value_wei, deadline
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'chainId': NETWORK["chain_id"],
            })
            approve_hash = self._build_and_send_transaction(approve_tx)

            execute_tx = executor_contract.functions.executeTask(
                self.wallet_address, to_address, task_hash, value_wei
            ).build_transaction({
                'from': self.wallet_address,
                'value': value_wei,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address) + 1,
                'chainId': NETWORK["chain_id"],
            })
            execute_hash = self._build_and_send_transaction(execute_tx)

            return {
                "status": "success",
                "tx_hash": f"{approve_hash.hex()}, {execute_hash.hex()}"
            }
        except ValueError as ve:
            logger.warning(f"Validation error in send_token: {ve}")
            return {"status": "error", "message": str(ve)}
        except Exception as e:
            logger.error(f"Error sending token: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def scheduled_transfer(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a token transfer using the Scheduler contract.

        Args:
            wallet_provider (Dict): Wallet provider information (not used currently).
            args (Dict[str, Any]): Arguments containing 'to' (address), 'amount' (float), and 'time' (timestamp).

        Returns:
            Dict[str, Any]: Result with status and transaction hash or error message.
        """
        try:
            if not all([args.get("to"), args.get("amount"), args.get("time")]):
                raise ValueError("Missing required fields: 'to', 'amount', and 'time' are required.")
            if not isinstance(args["amount"], (int, float)) or args["amount"] <= 0:
                raise ValueError("Amount must be a positive number.")
            if not isinstance(args["time"], (int, float)) or args["time"] < time.time():
                raise ValueError("Execution time must be a future timestamp.")

            to_address = Web3.to_checksum_address(args["to"])
            scheduler_address = Web3.to_checksum_address(CONTRACT_ADDRESSES["Scheduler"])
            scheduler_contract = self.w3.eth.contract(address=scheduler_address, abi=load_abi("ChainPilotScheduler"))

            execute_at = int(args["time"])
            expiry_at = execute_at + 31557600  # ~1 year expiry
            payload = Web3.to_hex(Web3.keccak(text="transfer"))
            value_wei = self.w3.to_wei(args["amount"], "ether")

            balance = self.w3.eth.get_balance(self.wallet_address)
            if balance < value_wei:
                raise ValueError(f"Insufficient balance: {self.w3.from_wei(balance, 'ether')} ETH available, "
                               f"{self.w3.from_wei(value_wei, 'ether')} ETH required.")

            tx = scheduler_contract.functions.scheduleTask(
                execute_at, expiry_at, to_address, payload, value_wei
            ).build_transaction({
                'from': self.wallet_address,
                'value': value_wei,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'chainId': NETWORK["chain_id"],
            })
            tx_hash = self._build_and_send_transaction(tx)
            return {"status": "success", "tx_hash": tx_hash.hex()}
        except ValueError as ve:
            logger.warning(f"Validation error in scheduled_transfer: {ve}")
            return {"status": "error", "message": str(ve)}
        except Exception as e:
            logger.error(f"Error scheduling transfer: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def list_tasks(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all scheduled tasks for the current wallet address.

        Args:
            wallet_provider (Dict): Wallet provider information (not used currently).
            args (Dict[str, Any]): Arguments (currently unused).

        Returns:
            Dict[str, Any]: Result with status and list of jobs or error message.
        """
        try:
            scheduler_address = Web3.to_checksum_address(CONTRACT_ADDRESSES["Scheduler"])
            scheduler_contract = self.w3.eth.contract(address=scheduler_address, abi=load_abi("ChainPilotScheduler"))

            task_count = scheduler_contract.functions.taskIdCounter().call()
            jobs = []

            for task_id in range(task_count):
                task = scheduler_contract.functions.tasks(task_id).call()
                if task[2].lower() == self.wallet_address.lower() and not task[7]:  # user matches and not cancelled
                    jobs.append({
                        "task_id": task_id,
                        "timestamp": task[0],  # executeAt
                        "to_address": task[4],  # target
                        "amount": self.w3.from_wei(task[6], "ether"),  # value
                        "tx_hash": "N/A"  # Placeholder
                    })
            logger.info(f"Found {len(jobs)} active tasks for {self.wallet_address}")
            return {"status": "success", "jobs": jobs}
        except Exception as e:
            logger.error(f"Error listing tasks: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def cancel(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a scheduled task by task ID.

        Args:
            wallet_provider (Dict): Wallet provider information (not used currently).
            args (Dict[str, Any]): Arguments containing 'task_id' (int).

        Returns:
            Dict[str, Any]: Result with status and transaction hashes or error message.
        """
        try:
            task_id = int(args.get("task_id", -1))
            if task_id < 0:
                raise ValueError("Task ID not provided. Use 'list tasks' to find task IDs.")

            scheduler_address = Web3.to_checksum_address(CONTRACT_ADDRESSES["Scheduler"])
            scheduler_contract = self.w3.eth.contract(address=scheduler_address, abi=load_abi("ChainPilotScheduler"))

            task_count = scheduler_contract.functions.taskIdCounter().call()
            if task_id >= task_count:
                raise ValueError(f"Task ID {task_id} not found.")
            task = scheduler_contract.functions.tasks(task_id).call()
            if task[2].lower() != self.wallet_address.lower():
                raise ValueError(f"Task ID {task_id} does not belong to this user.")
            if task[7]:  # isCancelled == True
                raise ValueError(f"Task ID {task_id} is already cancelled.")

            tx = scheduler_contract.functions.cancelTask(task_id).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'chainId': NETWORK["chain_id"],
            })
            tx_hash = self._build_and_send_transaction(tx)
            logger.info(f"Cancelled task {task_id} with tx hash: {tx_hash.hex()}")
            return {"status": "success", "tx_hashes": [tx_hash.hex()]}
        except ValueError as ve:
            logger.warning(f"Validation error in cancel: {ve}")
            return {"status": "error", "message": str(ve)}
        except Exception as e:
            logger.error(f"Error cancelling task: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def execute_action(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a pre-approved task using the Executor contract.

        Args:
            wallet_provider (Dict): Wallet provider information (not used currently).
            args (Dict[str, Any]): Arguments containing 'user', 'target', 'payload_hash', and 'value'.

        Returns:
            Dict[str, Any]: Result with status and transaction hash or error message.
        """
        try:
            if not all([args.get("target"), args.get("payload_hash")]):
                raise ValueError("Missing required fields: 'target' and 'payload_hash' are required.")
            if not isinstance(args.get("value", 0), (int, float)) or args.get("value", 0) < 0:
                raise ValueError("Value must be a non-negative number.")

            executor_address = Web3.to_checksum_address(CONTRACT_ADDRESSES["Executor"])
            executor_contract = self.w3.eth.contract(address=executor_address, abi=load_abi("ChainPilotExecutor"))

            user = Web3.to_checksum_address(args.get("user", self.wallet_address))
            target = Web3.to_checksum_address(args["target"])
            payload_hash = Web3.to_bytes(hexstr=args["payload_hash"])
            value_wei = self.w3.to_wei(args.get("value", 0), "ether")

            balance = self.w3.eth.get_balance(self.wallet_address)
            if balance < value_wei:
                raise ValueError(f"Insufficient balance: {self.w3.from_wei(balance, 'ether')} ETH available, "
                               f"{self.w3.from_wei(value_wei, 'ether')} ETH required.")

            tx = executor_contract.functions.executeTask(
                user, target, payload_hash, value_wei
            ).build_transaction({
                'from': self.wallet_address,
                'value': value_wei,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'chainId': NETWORK["chain_id"],
            })
            tx_hash = self._build_and_send_transaction(tx)
            return {"status": "success", "tx_hash": tx_hash.hex()}
        except ValueError as ve:
            logger.warning(f"Validation error in execute_action: {ve}")
            return {"status": "error", "message": str(ve)}
        except Exception as e:
            logger.error(f"Error executing action: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}