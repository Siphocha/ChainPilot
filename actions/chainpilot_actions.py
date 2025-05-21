from typing import Dict, Any
from web3 import Web3
import web3
from web3.exceptions import TransactionNotFound, TimeExhausted, ContractLogicError
import time
from datetime import datetime
from utils import load_abi, get_logger
from config import CONTRACT_ADDRESSES, NETWORK

logger = get_logger(__name__)

class ChainPilotActions:
    def __init__(self, wallet_address: str, private_key: str):
        self.w3 = Web3(Web3.HTTPProvider(NETWORK["rpc_url"]))
        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Base mainnet. Check the RPC URL.")
        
        if not private_key.startswith("0x") or len(private_key) != 66 or len(bytes.fromhex(private_key[2:])) != 32:
            raise ValueError("Invalid private key length. Must be 32 bytes (66 hex chars with 0x prefix).")
        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            raise ValueError("Invalid wallet address format. Must be 0x followed by 40 hex characters.")
        
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.private_key = private_key
        logger.info(f"Initialized ChainPilotActions with wallet address: {self.wallet_address}")

    def get_contract(self, contract_name: str) -> Any:
        """Helper to get a contract instance."""
        # Map contract names to ABI file names
        abi_name_map = {
            "Executor": "ChainPilotExecutor",
            "Scheduler": "ChainPilotScheduler"
        }
        abi_name = abi_name_map.get(contract_name, contract_name)
        contract_address = Web3.to_checksum_address(CONTRACT_ADDRESSES.get(contract_name))
        if not contract_address:
            raise ValueError(f"Contract address for {contract_name} not found in config.")
        abi = load_abi(abi_name)["abi"]
        return self.w3.eth.contract(address=contract_address, abi=abi)

    def _build_and_send_transaction(self, tx: Dict[str, Any], retries: int = 3, delay: int = 5) -> str:
        try:
            gas_estimate = self.w3.eth.estimate_gas(tx)
            tx['gas'] = int(gas_estimate * 1.5)
            logger.info(f"Estimated gas: {gas_estimate}, setting gas limit to: {tx['gas']}")
        except Exception as e:
            logger.warning(f"Gas estimation failed: {e}. Using default gas value.")
            tx['gas'] = 1_000_000

        if 'maxFeePerGas' not in tx or 'maxPriorityFeePerGas' not in tx:
            base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
            max_priority_fee = self.w3.eth.max_priority_fee
            max_fee = int(base_fee * 1.5 + max_priority_fee)
            tx['maxFeePerGas'] = max_fee
            tx['maxPriorityFeePerGas'] = max_priority_fee
            logger.info(f"Set maxFeePerGas: {max_fee}, maxPriorityFeePerGas: {max_priority_fee}")

        attempt = 0
        while attempt < retries:
            try:
                signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if receipt["status"] == 0:
                    raise ValueError("Transaction failed on the blockchain.")
                logger.info(f"Transaction successful: {tx_hash.hex()}")
                return tx_hash.hex()
            except (TransactionNotFound, TimeExhausted, ValueError) as e:
                attempt += 1
                logger.warning(f"Transaction attempt {attempt}/{retries} failed: {e}")
                if attempt == retries:
                    raise Exception(f"Transaction failed after {retries} attempts: {e}")
                time.sleep(delay)
            except ContractLogicError as cle:
                logger.error(f"Contract logic error during transaction: {cle}")
                if "0xf918b990" in str(cle):
                    return "Failed to execute: Not authorized or invalid task state. Ensure you have the necessary permissions."
                raise cle
            except Exception as e:
                logger.error(f"Unexpected error during transaction: {e}")
                raise e

    def check_executor_permissions(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            executor_contract = self.get_contract("Executor")
            return {
                "status": "success",
                "message": f"Executor contract address: {executor_contract.address}\n- Permission checks not supported by this contract."
            }
        except Exception as e:
            logger.error(f"Error checking Executor permissions: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def check_scheduler_permissions(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            scheduler_contract = self.get_contract("Scheduler")
            executer = scheduler_contract.functions.executerAddress().call()
            logger.info(f"Scheduler contract executer: {executer}")
            return {
                "status": "success",
                "message": f"Scheduler contract permissions:\n- Executer address: {executer}\n"
                         f"- Wallet {self.wallet_address} permissions: Not supported by this contract."
            }
        except Exception as e:
            logger.error(f"Error checking Scheduler permissions: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def send_tokens(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not all([args.get("to"), args.get("amount")]):
                raise ValueError("Missing 'to' or 'amount' for send tokens.")
            if not isinstance(args["amount"], (int, float)) or args["amount"] <= 0:
                raise ValueError("Amount must be a positive number.")

            to_address = Web3.to_checksum_address(args["to"])
            executor_contract = self.get_contract("Executor")

            value_wei = self.w3.to_wei(args["amount"], "ether")

            balance = self.w3.eth.get_balance(self.wallet_address)
            if balance < value_wei:
                raise ValueError(f"Insufficient ETH balance: {self.w3.from_wei(balance, 'ether')} ETH available, "
                               f"{self.w3.from_wei(value_wei, 'ether')} ETH required.")

            payload = Web3.to_hex(Web3.to_bytes(hexstr="0x"))
            task_hash = Web3.keccak(hexstr=Web3.to_hex(Web3.solidity_keccak(
                ['address', 'bytes', 'uint256'],
                [to_address, Web3.to_bytes(hexstr=payload), value_wei]
            )))
            logger.info(f"Task hash: {task_hash.hex()}")

            deadline = int(time.time()) + 86400
            logger.info(f"Calling approveTask with target: {to_address}, payload: {payload}, value: {value_wei}, deadline: {deadline}")

            approve_task_tx = executor_contract.functions.approveTask(
                to_address,
                Web3.to_bytes(hexstr=payload),
                value_wei,
                deadline
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'chainId': NETWORK["chain_id"],
            })
            approve_task_hash = self._build_and_send_transaction(approve_task_tx)
            if isinstance(approve_task_hash, str) and "Failed to execute" in approve_task_hash:
                return {"status": "error", "message": approve_task_hash}

            execute_tx = executor_contract.functions.executeTask(
                self.wallet_address,
                to_address,
                task_hash,
                value_wei
            ).build_transaction({
                'from': self.wallet_address,
                'value': value_wei,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address) + 1,
                'chainId': NETWORK["chain_id"],
            })
            execute_hash = self._build_and_send_transaction(execute_tx)
            if isinstance(execute_hash, str) and "Failed to execute" in execute_hash:
                return {"status": "error", "message": execute_hash}

            return {
                "status": "success",
                "tx_hash": f"{approve_task_hash}, {execute_hash}"
            }
        except ValueError as ve:
            logger.warning(f"Validation error in send_tokens: {ve}")
            return {"status": "error", "message": str(ve)}
        except web3.exceptions.ContractCustomError as cce:
            logger.error(f"Contract error sending tokens: {cce}", exc_info=True)
            if "0xf918b990" in str(cce):
                return {
                    "status": "error",
                    "message": "Failed to execute: Not authorized. Only the deployer can execute tasks until permissions are updated."
                }
            return {"status": "error", "message": str(cce)}
        except Exception as e:
            logger.error(f"Error sending tokens: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def schedule_transfers(self, wallet_provider: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            scheduler_contract = self.get_contract("Scheduler")
            execute_at = int(args["time"])
            expiry_at = execute_at + 86400  # 24-hour expiry
            target = Web3.to_checksum_address(args["to"])
            payload = b""
            value = 0  # Set to 0 as the function is not payable

            # Check if the timestamp is in the future
            current_time = int(time.time())
            if execute_at <= current_time:
                raise ValueError("Schedule time must be in the future.")

            tx = scheduler_contract.functions.scheduleTask(
                execute_at, expiry_at, target, payload, value
            ).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'chainId': NETWORK["chain_id"],
                'value': 0  # Explicitly set value to 0
            })
            tx_hash = self._build_and_send_transaction(tx)
            if isinstance(tx_hash, str) and "Failed to execute" in tx_hash:
                return {"status": "error", "message": tx_hash}

            logger.info(f"Scheduled transfer with tx hash: {tx_hash}")
            return {
                "status": "success",
                "message": f"Scheduled transfer to {target} at {datetime.fromtimestamp(execute_at).strftime('%Y-%m-%d %H:%M:%S')}.",
                "tx_hash": tx_hash
            }
        except ValueError as ve:
            logger.warning(f"Validation error in schedule_transfers: {ve}")
            return {"status": "error", "message": str(ve)}
        except Exception as e:
            logger.error(f"Error scheduling transfer: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def list_tasks(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            scheduler_contract = self.get_contract("Scheduler")
            task_count = scheduler_contract.functions.taskIdCounter().call()
            jobs = []

            for task_id in range(task_count):
                task = scheduler_contract.functions.tasks(task_id).call()
                if task[2].lower() == self.wallet_address.lower() and not task[7]:  # owner and not cancelled
                    jobs.append({
                        "task_id": task_id,
                        "timestamp": task[0],
                        "to_address": task[4],
                        "amount": self.w3.from_wei(task[6], "ether") if task[6] else 0,
                        "tx_hash": "N/A"
                    })
            logger.info(f"Found {len(jobs)} active tasks for {self.wallet_address}")
            return {"status": "success", "jobs": jobs}
        except Exception as e:
            logger.error(f"Error listing tasks: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def cancel_tasks(self, wallet_provider: Dict, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            task_id = int(args.get("task_id", -1))
            if task_id < 0:
                raise ValueError("Task ID not provided. Use 'list tasks' to find task IDs.")

            scheduler_contract = self.get_contract("Scheduler")
            task_count = scheduler_contract.functions.taskIdCounter().call()
            if task_id >= task_count:
                raise ValueError(f"Task ID {task_id} not found.")
            task = scheduler_contract.functions.tasks(task_id).call()
            if task[2].lower() != self.wallet_address.lower():
                raise ValueError(f"Task ID {task_id} does not belong to this user.")
            if task[7]:
                raise ValueError(f"Task ID {task_id} is already cancelled.")

            tx = scheduler_contract.functions.cancelTask(task_id).build_transaction({
                'from': self.wallet_address,
                'nonce': self.w3.eth.get_transaction_count(self.wallet_address),
                'chainId': NETWORK["chain_id"],
            })
            tx_hash = self._build_and_send_transaction(tx)
            if isinstance(tx_hash, str) and "Failed to execute" in tx_hash:
                return {"status": "error", "message": tx_hash}
            logger.info(f"Cancelled task {task_id} with tx hash: {tx_hash}")
            return {"status": "success", "tx_hash": tx_hash}
        except ValueError as ve:
            logger.warning(f"Validation error in cancel_tasks: {ve}")
            return {"status": "error", "message": str(ve)}
        except Exception as e:
            logger.error(f"Error cancelling task: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}