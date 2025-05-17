import sys
import os
import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime
from config import CONTRACT_ADDRESSES
from utils import MockContractInterface, get_logger
from actions.chainpilot_actions import ChainPilotActions
from wallet_provider import wallet_provider_dict
from nlp_parser import parse_command

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = get_logger(__name__)

class ChainPilotAgent:
    """A blockchain assistant agent for managing token transfers, scheduling, and staking operations.

    Attributes:
        actions (ChainPilotActions): Instance for executing blockchain actions.
        mock (MockContractInterface): Mock interface for testing unsupported actions.
        cat_tz (pytz.timezone): Timezone object for Central Africa Time (CAT, UTC+2).
    """

    def __init__(self):
        """Initialize the ChainPilotAgent with action handlers and timezone settings."""
        self.actions = ChainPilotActions()
        self.mock = MockContractInterface()
        #self.cat_tz = pytz.timezone("Africa/Kigali")  # CAT (UTC+2)

    def _map_action_args(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        """Map parsed command arguments to action-specific parameters.

        Args:
            parsed_command (Dict[str, Any]): Parsed command data from NLP parser.

        Returns:
            Dict[str, Any]: Action-specific arguments.

        Raises:
            ValueError: If required fields are missing (e.g., 'time' for schedule_transfer).
        """
        action = parsed_command.get("action")
        args: Dict[str, Any] = {}

        if action == "list_tasks":
            return args
        elif action == "transfer":
            args = {
                "to": parsed_command.get("to") or parsed_command.get("recipient"),
                "amount": parsed_command.get("amount")
            }
            if not all(args.values()):
                raise ValueError("Missing 'to' or 'amount' for transfer.")
        elif action == "schedule_transfer":
            args = {
                "to": parsed_command.get("to") or parsed_command.get("recipient"),
                "amount": parsed_command.get("amount"),
                "time": parsed_command.get("timestamp") or parsed_command.get("time") or parsed_command.get("schedule"),
                "scheduler_contract": CONTRACT_ADDRESSES["Scheduler"]
            }
            if not args["time"]:
                raise ValueError("Missing required field: 'time' for scheduling transfer.")
            if not isinstance(args["time"], (int, float)) or args["time"] < time.time():
                raise ValueError("Invalid or past 'time' for scheduling transfer.")
        elif action == "cancel":
            args = {
                "scheduler_contract": CONTRACT_ADDRESSES["Scheduler"],
                "task_id": parsed_command.get("task_id", -1)  # Default to -1 if not provided
            }
            if args["task_id"] < 0 and "all" not in parsed_command.get("target", "").lower():
                raise ValueError("Missing or invalid 'task_id'. Use 'list tasks' to find task IDs.")
        elif action == "execute_action":
            args = {
                "executor_contract": CONTRACT_ADDRESSES["Executor"],
                "user": parsed_command.get("user", wallet_provider_dict.get("address")),
                "target": parsed_command.get("target"),
                "payload_hash": parsed_command.get("payload_hash"),
                "value": parsed_command.get("value", 0)
            }
            if not args["target"] or not args["payload_hash"]:
                raise ValueError("Missing 'target' or 'payload_hash' for execute_action.")
        elif action in ["stake", "withdraw", "unstake"]:
            args = {
                "amount": parsed_command.get("amount"),
                "token": parsed_command.get("token", "ETH"),
                "schedule": parsed_command.get("schedule") or parsed_command.get("timing")
            }
            if not args["amount"]:
                raise ValueError(f"Missing 'amount' for {action}.")
        elif action == "check_portfolio":
            args = {"details": parsed_command.get("details", "all")}
        elif action == "show_staking_rewards":
            args = {}

        return args

    def _execute_action(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the specified blockchain or mock action.

        Args:
            action (str): The action to perform (e.g., 'transfer', 'stake').
            args (Dict[str, Any]): Action-specific arguments.

        Returns:
            Dict[str, Any]: Result of the action execution.
        """
        cdp_actions = ["create_token", "deploy_nft", "mint_nft", "register_basename"]
        if action in cdp_actions:
            return {
                "status": "error",
                "message": f"Action '{action}' is not supported in local Hardhat testing. Please use Base Sepolia for CDP actions."
            }
        try:
            action_map = {
                "transfer": self.actions.send_token,
                "schedule_transfer": self.actions.scheduled_transfer,
                "cancel": self.actions.cancel,
                "execute_action": self.actions.execute_action,
                "list_tasks": self.actions.list_tasks,
                "stake": lambda w, a: {"status": "success", "message": self.mock.stake(a["amount"], a["token"], a["schedule"])},
                "withdraw": lambda w, a: {"status": "success", "message": self.mock.withdraw(a["amount"], a["token"])},
                "unstake": lambda w, a: {"status": "success", "message": self.mock.unstake(a["amount"], a["token"], a["schedule"])},
                "check_portfolio": lambda w, a: {"status": "success", "message": self.mock.check_portfolio(a["details"])},
                "show_staking_rewards": lambda w, a: {"status": "success", "message": self.mock.show_staking_rewards()}
            }
            return action_map.get(action, lambda w, a: {
                "status": "error",
                "message": f"Unsupported action: '{action}'. Available actions: {', '.join(action_map.keys())}."
            })(wallet_provider_dict, args)
        except Exception as e:
            logger.error(f"Execution error for {action}: {e}")
            return {"status": "error", "message": str(e)}

    def _format_result(self, result: Dict[str, Any], action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Format the result of an action into a user-friendly message.

        Args:
            result (Dict[str, Any]): Raw result from action execution.
            action (str): The action performed.
            args (Dict[str, Any]): Arguments used for the action.

        Returns:
            Dict[str, Any]: Formatted result with a status and message.
        """
        if result["status"] == "success":
            if action == "transfer":
                return {
                    "status": "success",
                    "message": f"Successfully sent {args.get('amount', 'unknown')} tokens to {args.get('to', 'unknown')}! "
                             f"Transaction hash: {result.get('tx_hash', 'N/A')}"
                }
            elif action == "schedule_transfer":
                utc_dt = datetime.fromtimestamp(args["time"],)
                cat_dt = utc_dt.astimezone(self.cat_tz)
                human_time = cat_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
                return {
                    "status": "success",
                    "message": f"Scheduled transfer of {args.get('amount', 'unknown')} tokens to {args.get('to', 'unknown')} "
                             f"at {human_time}. Transaction hash: {result.get('tx_hash', 'N/A')}"
                }
            elif action == "cancel":
                tx_hashes = result.get("tx_hashes", [])
                if result.get("message") == "No pending tasks to cancel":
                    return {"status": "success", "message": "No scheduled tasks to cancel."}
                return {
                    "status": "success",
                    "message": f"Cancelled {len(tx_hashes)} scheduled task(s). Transaction hash(es): {', '.join(tx_hashes) if tx_hashes else 'N/A'}"
                }
            elif action == "list_tasks":
                jobs = result.get("jobs", [])
                if not jobs:
                    return {"status": "success", "message": "No scheduled tasks found."}
                lines = []
                for job in jobs:
                    utc_dt = datetime.fromtimestamp(job["timestamp"])
                    cat_dt = utc_dt.astimezone(self.cat_tz)
                    human_time = cat_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
                    lines.append(f"- {job.get('amount', 'unknown')} tokens → {job.get('to_address', 'unknown')} @ {human_time} "
                               f"(ID: {job.get('task_id', 'N/A')})")
                return {"status": "success", "message": "Scheduled tasks:\n" + "\n".join(lines)}
            elif action == "execute_action":
                return {
                    "status": "success",
                    "message": f"Executed action on {args.get('executor_contract', 'unknown')}. Transaction hash: {result.get('tx_hash', 'N/A')}"
                }
            elif action in ["stake", "withdraw", "unstake", "check_portfolio", "show_staking_rewards"]:
                return {"status": "success", "message": result.get("message", "Action completed.")}
            return {"status": "success", "message": result.get("message", "Action completed successfully.")}
        else:
            error_message = result.get("message", "An unknown error occurred.")
            error_handlers = {
                "HTTPConnectionPool|connection": "Could not connect to the blockchain network. Ensure the Hardhat node is running or check network settings.",
                "decimals|contract function": "Failed to interact with the contract. Verify the contract address and deployment.",
                "transaction failed": "The transaction failed. Check your wallet balance or contract details and retry."
            }
            for key, message in error_handlers.items():
                if any(substring in error_message.lower() for substring in key.split("|")):
                    return {"status": "error", "message": message}
            return {
                "status": "error",
                "message": f"Failed to execute '{action}': {error_message}. Please retry or contact support."
            }

    def process_command(self, command: str, confirm: bool = None) -> Dict[str, Any]:
        """Process a user command and return the result.

        Args:
            command (str): User input command.
            confirm (bool, optional): Confirmation for critical actions like cancel.

        Returns:
            Dict[str, Any]: Response with status and message.
        """
        try:
            command_lower = command.lower().strip()
            if command_lower in ["hello", "hi"]:
                return {
                    "status": "success",
                    "message": "👋 Hello! I’m ChainPilot, your blockchain assistant.\n"
                             "🧠 Supported actions: send tokens, schedule transfers, cancel tasks, stake, withdraw, unstake, "
                             "check portfolio, show staking rewards.\n"
                             "💬 What would you like me to do? (CDP actions disabled in local testing.)"
                }

            if command_lower in ["list tasks", "show tasks", "list scheduled tasks"]:
                result = self.actions.list_tasks(wallet_provider_dict, {})
                return self._format_result(result, "list_tasks", {})

            parsed_command = parse_command(command)
            logger.info(f"Parsed Command: {parsed_command}")

            action = parsed_command.get("action")
            if action == "cancel" and confirm is None:
                task_id = parsed_command.get("task_id", "unknown")
                return {
                    "status": "prompt",
                    "message": f"Are you sure you want to cancel task {task_id}? Reply with 'yes' or 'no'."
                }
            if action == "cancel" and not confirm:
                return {"status": "success", "message": "Cancel action aborted."}

            if not action:
                return {
                    "status": "error",
                    "message": "❌ Invalid command. Try: 'send 0.5 to 0x...', 'schedule 0.5 to 0x... at 1735689600', "
                             "'cancel task 0', 'stake 50 ETH weekly', etc."
                }

            args = self._map_action_args(parsed_command)
            result = self._execute_action(action, args)
            return self._format_result(result, action, args)

        except ValueError as ve:
            logger.warning(f"Validation error: {ve}")
            return {"status": "error", "message": f"Validation failed: {str(ve)}"}
        except Exception as e:
            logger.error(f"Unexpected error processing command: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"❌ Unexpected error: {str(e)}. Please retry or contact support."
            }

if __name__ == "__main__":
    agent = ChainPilotAgent()
    print("👋 Hello! I’m ChainPilot, your blockchain assistant.")
    print("🧠 Supported actions: send tokens, schedule transfers, cancel tasks, stake, withdraw, unstake, "
          "check portfolio, show staking rewards.")
    print("💬 Enter a command (e.g., 'send 0.5 to 0x...', 'exit' to quit). CDP actions are disabled in local testing.")
    while True:
        try:
            command = input("> ").strip()
            if command.lower() in ["exit", "quit"]:
                print("👋 Goodbye!")
                break
            confirm = True if "cancel" in command.lower() else None
            result = agent.process_command(command, confirm=confirm)
            print(f"✅ Result:\n{result['message']}")
        except KeyboardInterrupt:
            print("\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            logger.error(f"CLI error: {e}", exc_info=True)