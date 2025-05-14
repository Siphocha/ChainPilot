import sys
import os
import logging
from typing import Dict, Any
from datetime import datetime
import pytz
from actions.chainpilot_actions import ChainPilotActions
from wallet_provider import wallet_provider_dict
from nlp_parser import parse_command
from config import CONTRACT_ADDRESSES, NETWORK

# Clear existing handlers to avoid duplicate logging
for handler in logging.getLogger().handlers[:]:
    logging.getLogger().removeHandler(handler)

logger = logging.getLogger(__name__)

class ChainPilotAgent:
    def __init__(self):
        wallet_address = os.getenv("WALLET_ADDRESS")
        private_key = os.getenv("WALLET_PRIVATE_KEY")

        if not wallet_address:
            raise ValueError("WALLET_ADDRESS environment variable is not set")
        if not private_key:
            raise ValueError("WALLET_PRIVATE_KEY environment variable is not set")

        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            raise ValueError("Invalid wallet address format. Must be 0x followed by 40 hex characters.")
        if not private_key.startswith("0x") or len(private_key) != 66:
            raise ValueError("Invalid private key format. Must be 0x followed by 64 hex characters.")

        self.actions = ChainPilotActions(wallet_address, private_key)
        self.cat_tz = pytz.timezone("Africa/Kigali")
        self.pending_action = None

    def _map_action_args(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        action = parsed_command.get("action")
        args: Dict[str, Any] = {}

        if action in ["check_executor_permissions", "check_scheduler_permissions", "list_tasks"]:
            return args
        elif action == "send_tokens":
            args = {"to": parsed_command.get("to"), "amount": parsed_command.get("amount")}
            if not all(args.values()):
                raise ValueError("Missing 'to' or 'amount' for send tokens.")
        elif action == "schedule_transfers":
            args = {"to": parsed_command.get("to"), "amount": parsed_command.get("amount"), "time": parsed_command.get("time")}
            if not args["time"]:
                raise ValueError("Missing required field: 'time' for schedule transfers.")
            current_time = int(datetime.now(pytz.UTC).timestamp())
            if not isinstance(args["time"], (int, float)) or args["time"] <= current_time:
                raise ValueError(f"Invalid or past 'time' for schedule transfers. Provided: {args['time']}, Current UTC: {current_time}")
        elif action == "cancel_tasks":
            args = {"task_id": parsed_command.get("task_id", -1)}
            if args["task_id"] < 0:
                raise ValueError("Missing or invalid 'task_id'. Use 'list tasks' to find task IDs.")
        return args

    def _execute_action(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        action_map = {
            "check_executor_permissions": self.actions.check_executor_permissions,
            "check_scheduler_permissions": self.actions.check_scheduler_permissions,
            "send_tokens": self.actions.send_tokens,
            "schedule_transfers": self.actions.schedule_transfers,
            "list_tasks": self.actions.list_tasks,
            "cancel_tasks": self.actions.cancel_tasks,
            "help": lambda w, a: {"status": "success", "message": self._get_help_message()}
        }
        return action_map.get(action, lambda w, a: {"status": "error", "message": f"Unsupported action: '{action}'. Available actions: {', '.join(action_map.keys())}."})(wallet_provider_dict, args)

    def _get_help_message(self) -> str:
        return ("👋 Hello! I’m ChainPilot, your blockchain assistant on Base mainnet.\n"
                "🧠 Supported actions:\n"
                "- check_executor_permissions: Check Executor contract address.\n"
                "- check_scheduler_permissions: Check Scheduler contract executor address.\n"
                "- send_tokens <amount> to <address>: Send ETH via Executor (requires executor permissions).\n"
                "- schedule_transfers <amount> to <address> at <timestamp>: Schedule ETH transfer via Scheduler.\n"
                "- list_tasks: List scheduled tasks.\n"
                "- cancel_tasks <task_id>: Cancel a scheduled task.\n"
                "- help: Show this message.\n"
                "💬 Use the API endpoints to interact (e.g., POST /command with 'send_tokens 0.1 to 0x...').")

    def _format_result(self, result: Dict[str, Any], action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if result.get("status") == "success":
            # existing formatting...
            # omitted for brevity
            return result
        else:
            raw_msg = result.get("message", "Unknown error")
            # Map known errors to friendly messages
            if "insufficient" in raw_msg.lower():
                friendly = "Oops! Your wallet doesn’t have enough ETH to complete this. Please top up and try again."
            elif "already cancelled" in raw_msg.lower():
                friendly = "That task has already been cancelled. No further action needed."
            elif "invalid or past 'time'" in raw_msg.lower():
                friendly = raw_msg  # Let validation message show
            else:
                friendly = f"Error: {raw_msg}. Please retry or contact support."
            return {"status": "error", "message": friendly}

    def process_command(self, command: str, confirm: bool = None) -> Dict[str, Any]:
        try:
            command_lower = command.lower().strip()
            if self.pending_action and command_lower in ["yes", "no"]:
                if command_lower == "yes":
                    confirm = True
                else:
                    self.pending_action = None
                    return {"status": "success", "message": "Cancel action aborted."}
                parsed = self.pending_action["parsed_command"]
                action = parsed.get("action")
                args = self._map_action_args(parsed)
                result = self._execute_action(action, args)
                self.pending_action = None
                return self._format_result(result, action, args)

            self.pending_action = None
            if command_lower in ["hello", "hi", "help"]:
                return self._execute_action("help", {})

            parsed_command = parse_command(command)
            logger.info(f"Parsed Command: {parsed_command}")

            action = parsed_command.get("action")
            if action == "cancel_tasks" and confirm is None:
                self.pending_action = {"parsed_command": parsed_command}
                task_id = parsed_command.get("task_id")
                return {"status": "prompt", "message": f"Are you sure you want to cancel task {task_id}? Reply with 'yes' or 'no'."}

            if not action:
                return {"status": "error", "message": "❌ Invalid command. Type 'help' for available actions."}

            args = self._map_action_args(parsed_command)
            result = self._execute_action(action, args)
            return self._format_result(result, action, args)

        except ValueError as ve:
            logger.warning(f"Validation error: {ve}")
            return {"status": "error", "message": f"Validation failed: {str(ve)}"}
        except Exception as e:
            logger.error(f"Unexpected error processing command: {e}", exc_info=True)
            return {"status": "error", "message": f"❌ Unexpected error: {str(e)}. Please retry or contact support."}

if __name__ == "__main__":
    agent = ChainPilotAgent()
    print("👋 Hello! I’m ChainPilot, your blockchain assistant on Base mainnet.")
    while True:
        command = input("> ").strip()
        if command.lower() in ["exit", "quit"]:
            break
        result = agent.process_command(command)
        print(result["message"])
