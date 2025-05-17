import json
import logging
from typing import Union

def get_logger(name: str) -> logging.Logger:
    """Set up and return a logger with the specified name."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

# Embedded ABI data (replace with actual ABI content from your JSON files)
CHAINPILOT_EXECUTOR_ABI = [
    {"type": "function", "name": "approveTask", "inputs": [{"type": "address"}, {"type": "bytes"}, {"type": "uint256"}, {"type": "uint256"}], "outputs": []},
    {"type": "function", "name": "executeTask", "inputs": [{"type": "address"}, {"type": "address"}, {"type": "bytes32"}, {"type": "uint256"}], "outputs": [{"type": "bool"}]}
]  # Replace with actual ChainPilotExecutor ABI

CHAINPILOT_SCHEDULER_ABI = [
    {"type": "function", "name": "taskIdCounter", "inputs": [], "outputs": [{"type": "uint256"}]},
    {"type": "function", "name": "tasks", "inputs": [{"type": "uint256"}], "outputs": [{"type": "tuple", "components": [{"name": "executeAt", "type": "uint256"}, {"name": "expiryAt", "type": "uint256"}, {"name": "user", "type": "address"}, {"name": "executer", "type": "address"}, {"name": "target", "type": "address"}, {"name": "payloadHash", "type": "bytes32"}, {"name": "value", "type": "uint256"}, {"name": "isCancelled", "type": "bool"}]}]},
    {"type": "function", "name": "scheduleTask", "inputs": [{"type": "uint256"}, {"type": "uint256"}, {"type": "address"}, {"type": "bytes"}, {"type": "uint256"}], "outputs": []},
    {"type": "function", "name": "cancelTask", "inputs": [{"type": "uint256"}], "outputs": []}
]  # Replace with actual ChainPilotScheduler ABI

def load_abi(abi_name: str) -> list:
    """Load an ABI based on the contract name.

    Args:
        abi_name (str): Name of the ABI to load (e.g., 'ChainPilotExecutor', 'ChainPilotScheduler').

    Returns:
        list: ABI data for the specified contract.

    Raises:
        ValueError: If the ABI name is not recognized.
    """
    logger = get_logger(__name__)
    abi_map = {
        "ChainPilotExecutor": CHAINPILOT_EXECUTOR_ABI,
        "ChainPilotScheduler": CHAINPILOT_SCHEDULER_ABI
    }
    if abi_name not in abi_map:
        raise ValueError(f"Unsupported ABI name: {abi_name}")
    logger.info(f"Loading ABI for {abi_name}")
    return abi_map[abi_name]

class MockContractInterface:
    """Mock contract interface for testing unsupported actions."""

    def stake(self, amount: Union[float, int], token: str, schedule: str) -> str:
        """Mock staking action."""
        return f"Staked {amount} {token} with schedule {schedule}."

    def withdraw(self, amount: Union[float, int], currency: str) -> str:
        """Mock withdrawal action."""
        return f"Withdrew {amount} {currency}."

    def unstake(self, amount: Union[float, int], token: str, timing: str) -> str:
        """Mock unstaking action."""
        return f"Unstaked {amount} {token} at {timing}."

    def check_portfolio(self, details: str) -> str:
        """Mock portfolio check action."""
        return f"Portfolio summary: {details} - 100 ETH, 200 USDC."

    def show_staking_rewards(self) -> str:
        """Mock staking rewards display action."""
        return "Staking rewards: 5 ETH earned."