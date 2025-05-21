import re
from typing import Dict, Any
from datetime import datetime, timedelta
import pytz

def parse_command(command: str) -> Dict[str, Any]:
    command_lower = command.lower().strip()
    print(f"Debug: Command received: '{command_lower}'")  # Debug log
    result: Dict[str, Any] = {}

    address_pattern = r'0x[a-fA-F0-9]{40}'
    amount_pattern = r'\d*\.?\d+'
    time_pattern = r'\d{10}|tomorrow|now'

    # Command matching with specific patterns
    if command_lower == "check executor permissions":
        result["action"] = "check_executor_permissions"
    elif command_lower == "check scheduler permissions":
        result["action"] = "check_scheduler_permissions"
    elif command_lower in ["list tasks", "list_tasks"]:  # Handle both forms
        result["action"] = "list_tasks"
    elif command_lower in ["help", "hi", "hello"]:
        result["action"] = "help"
    elif re.match(r"^cancel_tasks\s+(?:task\s*)?(\d+)$", command_lower):
        task_id_match = re.search(r"cancel_tasks\s+(?:task\s*)?(\d+)", command_lower)
        if task_id_match:
            result["action"] = "cancel_tasks"
            result["task_id"] = int(task_id_match.group(1))
            if "yes" in command_lower:
                result["confirm"] = True
    elif re.match(r"^send_tokens\s+" + amount_pattern + r"\s+to\s+" + address_pattern + r"(?:\s+yes)?$", command_lower):
        match = re.match(r"^send_tokens\s(" + amount_pattern + r")\s+to\s(" + address_pattern + r")(?:\s+yes)?$", command_lower)
        if match:
            result["action"] = "send_tokens"
            result["amount"] = float(match.group(1))
            result["to"] = match.group(2)
            if "yes" in command_lower:
                result["confirm"] = True
    elif re.match(r"^schedule_transfers\s+" + amount_pattern + r"\s+to\s+" + address_pattern + r"\s+at\s+" + time_pattern + r"(?:\s+yes)?$", command_lower):
        match = re.match(r"^schedule_transfers\s(" + amount_pattern + r")\s+to\s(" + address_pattern + r")\s+at\s(" + time_pattern + r")(?:\s+yes)?$", command_lower)
        if match:
            result["action"] = "schedule_transfers"
            result["amount"] = float(match.group(1))
            result["to"] = match.group(2)
            time_str = match.group(3)
            cat_tz = pytz.timezone("Africa/Kigali")
            current_time = datetime.now(cat_tz)
            if time_str == "tomorrow":
                tomorrow = current_time + timedelta(days=1)
                tomorrow = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                result["time"] = int(tomorrow.timestamp())
            elif time_str == "now":
                result["time"] = int(current_time.timestamp())
            else:
                result["time"] = int(time_str)
            if "yes" in command_lower:
                result["confirm"] = True

    if not result:
        print(f"Failed to parse command: {command}")
    else:
        print(f"Debug: Parsed result: {result}")
    return result