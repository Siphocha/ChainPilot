import json
import logging
import os
from typing import Dict

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

def load_abi(abi_name: str) -> Dict[str, any]:
    """Load an ABI and bytecode (if available) from a JSON file based on the contract name.
    Args:
        abi_name (str): Name of the ABI to load (e.g., 'ERC20', 'ChainPilotExecutor', 'ChainPilotScheduler').
    Returns:
        Dict[str, any]: A dictionary containing 'abi' (list) and 'bytecode' (str, if available).
    Raises:
        FileNotFoundError: If the ABI file is not found in either directory.
        ValueError: If the ABI file is invalid or missing required fields.
    """
    logger = get_logger(__name__)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Explicitly set the abis directory
    abis_dir = os.path.join(base_dir, "abis")
    contracts_dir = os.path.join(base_dir, "contracts")

    # Check both 'abis' and 'contracts' directories
    for directory in [abis_dir, contracts_dir]:
        abi_file_path = os.path.join(directory, f"{abi_name}.json")
        try:
            with open(abi_file_path, "r") as f:
                data = json.load(f)
            if "abi" not in data:
                raise ValueError(f"ABI not found in {abi_name}.json")
            abi = data["abi"]
            bytecode = data.get("bytecode", "")
            if isinstance(bytecode, dict) and "object" in bytecode:
                bytecode = bytecode["object"]
            if bytecode and isinstance(bytecode, str) and not bytecode.startswith("0x"):
                bytecode = "0x" + bytecode
            logger.info(f"Loaded ABI for {abi_name} from {abi_file_path}")
            return {"abi": abi, "bytecode": bytecode}
        except FileNotFoundError:
            continue  # Try the next directory if file not found

    # If file not found in either directory
    logger.error(f"ABI file not found in contracts or abis: {abi_name}.json")
    raise FileNotFoundError(f"ABI file not found in contracts or abis: {abi_name}.json")