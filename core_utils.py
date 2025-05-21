import json
import logging
import os

def get_logger(name: str) -> logging.Logger:
    """
    Create and configure a logger with the given name.
    
    Args:
        name (str): Name of the logger
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

def load_abi(path: str) -> list:
    """
    Load ABI from a JSON file.
    
    Args:
        path (str): Path to the ABI JSON file
    Returns:
        list: ABI data
    """
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"ABI file not found at {path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in ABI file at {path}")