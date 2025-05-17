import re
from typing import Dict, Any
from datetime import datetime, timedelta
import pytz

def parse_command(command: str) -> Dict[str, Any]:
    """Parse a natural language command into structured data.

    Args:
        command (str): The user command to parse.

    Returns:
        Dict[str, Any]: Parsed command data with action and arguments.
    """
    command_lower = command.lower().strip()
    result: Dict[str, Any] = {}

    # Address pattern (simplified for 0x... format)
    address_pattern = r'0x[a-fA-F0-9]{40}'
    # Amount pattern (e.g., 0.1, 2)
    amount_pattern = r'\d*\.?\d+'
    # Timestamp or time reference (e.g., 1735689600, tomorrow, now)
    time_pattern = r'\d{10}|tomorrow|now'

    # 1. Parse 'send' or 'transfer' commands
    if "send" in command_lower or "transfer" in command_lower:
        result["action"] = "transfer"
        # Extract amount
        amount_match = re.search(amount_pattern, command_lower)
        if amount_match:
            result["amount"] = float(amount_match.group())
        # Extract address
        address_match = re.search(address_pattern, command_lower)
        if address_match:
            result["to"] = address_match.group()

    # 2. Parse 'schedule transfer' commands
    elif "schedule transfer" in command_lower:
        result["action"] = "scheduled_transfer"
        amount_match = re.search(amount_pattern, command_lower)
        if amount_match:
            result["amount"] = float(amount_match.group())
        address_match = re.search(address_pattern, command_lower)
        if address_match:
            result["to"] = address_match.group()
        time_match = re.search(time_pattern, command_lower)
        if time_match:
            time_str = time_match.group()
            if time_str == "tomorrow":
                cat_tz = pytz.timezone("Africa/Kigali")
                tomorrow = (datetime.now(cat_tz) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                result["time"] = int(tomorrow.timestamp())
            elif time_str == "now":
                result["time"] = int(datetime.now(pytz.UTC).timestamp())
            else:
                result["time"] = int(time_str)

    # 3. Parse 'cancel' commands
    elif "cancel" in command_lower:
        result["action"] = "cancel"
        if "task" in command_lower:
            try:
                task_id = int(command_lower.split("task")[1].strip())
                result["task_id"] = task_id
            except (IndexError, ValueError):
                pass  # Handled in process_command

    # 4. Parse 'stake' commands
    elif "stake" in command_lower:
        result["action"] = "stake"
        amount_match = re.search(amount_pattern, command_lower)
        if amount_match:
            result["amount"] = float(amount_match.group())
        # Extract token (e.g., ETH, USDC)
        token_match = re.search(r'(eth|usdc)', command_lower)
        if token_match:
            result["token"] = token_match.group().upper()
        # Extract schedule (e.g., weekly)
        schedule_match = re.search(r'(weekly|monthly|daily)', command_lower)
        if schedule_match:
            result["schedule"] = schedule_match.group()

    # 5. Parse 'unstake' commands
    elif "unstake" in command_lower:
        result["action"] = "unstake"
        amount_match = re.search(amount_pattern, command_lower)
        if amount_match:
            result["amount"] = float(amount_match.group())
        token_match = re.search(r'(eth|usdc)', command_lower)
        if token_match:
            result["token"] = token_match.group().upper()
        timing_match = re.search(r'(now|today)', command_lower)
        if timing_match:
            result["timing"] = timing_match.group()

    # 6. Parse 'check portfolio' commands
    elif "check portfolio" in command_lower:
        result["action"] = "check_portfolio"
        details_match = re.search(r'(summary|all|details)', command_lower)
        if details_match:
            result["details"] = details_match.group()

    # 7. Parse 'show staking rewards' commands
    elif "show staking rewards" in command_lower:
        result["action"] = "show_staking_rewards"

    if not result:
        print(f"Failed to parse command: {command}")
    return result