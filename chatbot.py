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
        # Prompt for wallet address and private key
        wallet_address = input("Please enter the wallet address (e.g., 0x...): ").strip()
        private_key = input("Please enter the private key: ").strip()

        # Validate input (basic check)
        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            raise ValueError("Invalid wallet address format. Must be 0x followed by 40 hex characters.")
        if not private_key.startswith("0x") or len(private_key) != 66:
            raise ValueError("Invalid private key format. Must be 0x followed by 64 hex characters.")

        # Pass credentials directly to ChainPilotActions
        self.actions = ChainPilotActions(wallet_address, private_key)
        self.cat_tz = pytz.timezone("Africa/Kigali")
        self.pending_action = None  # To track pending actions requiring confirmation

    def _map_action_args(self, parsed_command: Dict[str, Any]) -> Dict[str, Any]:
        action = parsed_command.get("action")
        args: Dict[str, Any] = {}

        if action in ["check_executor_permissions", "check_scheduler_permissions", "list_tasks"]:
            return args
        elif action == "send_tokens":
            args = {
                "to": parsed_command.get("to"),
                "amount": parsed_command.get("amount")
            }
            if not all(args.values()):
                raise ValueError("Missing 'to' or 'amount' for send tokens.")
        elif action == "schedule_transfers":
            args = {
                "to": parsed_command.get("to"),
                "amount": parsed_command.get("amount"),
                "time": parsed_command.get("time")
            }
            if not args["time"]:
                raise ValueError("Missing required field: 'time' for schedule transfers.")
            current_time = int(datetime.now(pytz.UTC).timestamp())
            if not isinstance(args["time"], (int, float)) or args["time"] <= current_time:
                raise ValueError(f"Invalid or past 'time' for schedule transfers. Provided: {args['time']}, Current UTC: {current_time}")
        elif action == "cancel_tasks":
            args = {
                "task_id": parsed_command.get("task_id", -1)
            }
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
        return action_map.get(action, lambda w, a: {
            "status": "error",
            "message": f"Unsupported action: '{action}'. Available actions: {', '.join(action_map.keys())}."
        })(wallet_provider_dict, args)

    def _get_help_message(self) -> str:
        return ("👋 Hello! I’m ChainPilot, your blockchain assistant on Base mainnet.\n"
                "🧠 Supported actions:\n"
                "- check_executor_permissions: Check Executor contract address.\n"
                "- check_scheduler_permissions: Check Scheduler contract executer address.\n"
                "- send_tokens <amount> to <address>: Send ETH via Executor (requires executer permissions).\n"
                "- schedule_transfers <amount> to <address> at <timestamp>: Schedule ETH transfer via Scheduler (anyone can schedule, but only the executer can execute).\n"
                "- list_tasks: List scheduled tasks.\n"
                "- cancel_tasks <task_id>: Cancel a scheduled task.\n"
                "- help: Show this message.\n"
                "💬 Use the API endpoints to interact (e.g., POST /command with 'send_tokens 0.1 to 0x...').")

    def _format_result(self, result: Dict[str, Any], action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if result["status"] == "success":
            if action == "send_tokens":
                return {
                    "status": "success",
                    "message": f"Successfully sent {args.get('amount', 'unknown')} ETH to {args.get('to', 'unknown')}. "
                             f"Transaction hashes: {result.get('tx_hash', 'N/A')}"
                }
            elif action == "schedule_transfers":
                utc_dt = datetime.fromtimestamp(args["time"], tz=pytz.UTC)
                cat_dt = utc_dt.astimezone(self.cat_tz)
                human_time = cat_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
                return {
                    "status": "success",
                    "message": f"Scheduled transfer of {args.get('amount', 'unknown')} ETH to {args.get('to', 'unknown')} "
                             f"at {human_time}. Transaction hash: {result.get('tx_hash', 'N/A')}"
                }
            elif action == "list_tasks":
                jobs = result.get("jobs", [])
                if not jobs:
                    return {"status": "success", "message": "No active tasks found."}
                task_list = "\n".join(
                    f"Task ID: {job['task_id']}, To: {job['to_address']}, Amount: {job['amount']} ETH, "
                    f"Scheduled: {datetime.fromtimestamp(job['timestamp'], tz=pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')}"
                    for job in jobs
                )
                return {"status": "success", "message": f"Active tasks:\n{task_list}"}
            elif action == "cancel_tasks":
                return {
                    "status": "success",
                    "message": f"Cancelled task {args.get('task_id', 'unknown')}. Transaction hash: {result.get('tx_hash', 'N/A')}"
                }
            elif action in ["check_executor_permissions", "check_scheduler_permissions"]:
                return {
                    "status": "success",
                    "message": result.get("message", "Permissions checked.")
                }
            elif action == "help":
                return {
                    "status": "success",
                    "message": result.get("message", "Help displayed.")
                }
            return {"status": "success", "message": "Action completed successfully."}
        else:
            return {
                "status": "error",
                "message": f"Failed to execute '{action}': {result.get('message', 'Unknown error')}. Please retry or contact support."
            }

    def process_command(self, command: str, confirm: bool = None) -> Dict[str, Any]:
        try:
            command_lower = command.lower().strip()
            # Handle confirmation responses
            if self.pending_action and command_lower in ["yes", "no"]:
                if command_lower == "yes":
                    confirm = True
                else:
                    self.pending_action = None
                    return {"status": "success", "message": "Cancel action aborted."}
                # Process the pending action with confirmation
                parsed_command = self.pending_action["parsed_command"]
                action = parsed_command.get("action")
                args = self._map_action_args(parsed_command)
                result = self._execute_action(action, args)
                self.pending_action = None  # Clear pending action
                return self._format_result(result, action, args)

            # Clear pending action if a new command is issued
            self.pending_action = None

            if command_lower in ["hello", "hi", "help"]:
                return self._execute_action("help", {})

            parsed_command = parse_command(command)
            logger.info(f"Parsed Command: {parsed_command}")

            action = parsed_command.get("action")
            if action == "cancel_tasks" and confirm is None:
                task_id = parsed_command.get("task_id", "unknown")
                self.pending_action = {"parsed_command": parsed_command}
                return {
                    "status": "prompt",
                    "message": f"Are you sure you want to cancel task {task_id}? Reply with 'yes' or 'no'."
                }

            if not action:
                return {
                    "status": "error",
                    "message": "❌ Invalid command. Type 'help' for available actions."
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
    print("👋 Hello! I’m ChainPilot, your blockchain assistant on Base mainnet.")
    print("🧠 Supported actions: check_executor_permissions, check_scheduler_permissions, send_tokens, schedule_transfers, list_tasks, cancel_tasks, help.")
    print("💬 Type 'help' for more information.")
    print("💬 Enter a command (e.g., 'send_tokens 0.1 to 0x...', 'exit' to quit).")
    while True:
        try:
            command = input("> ").strip()
            if command.lower() in ["exit", "quit"]:
                print("👋 Goodbye!")
                break
            result = agent.process_command(command)
            print(f"✅ Result:\n{result['message']}")
        except KeyboardInterrupt:
            print("\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            logger.error(f"CLI error: {e}", exc_info=True)