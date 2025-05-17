import json
import os
import time
from typing import Dict, List, Any
from utils import send_token, get_logger
from config import CONTRACT_ADDRESSES

logger = get_logger(__name__)
logger.info("Scheduler started")  # Debug

DATA_DIR = "data"
JOBS_FILE = os.path.join(DATA_DIR, "scheduled_jobs.json")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_jobs() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(JOBS_FILE):
            with open(JOBS_FILE, "r") as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading jobs: {e}")
        return []

def save_jobs(jobs: List[Dict[str, Any]]) -> None:
    try:
        with open(JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving jobs: {e}")

def schedule_job(tx_hash: str, amount: float, to_address: str, token_contract: str, timestamp: int) -> None:
    jobs = load_jobs()
    jobs.append({
        "tx_hash": tx_hash,
        "amount": amount,
        "to_address": to_address,
        "token_contract": token_contract,
        "timestamp": timestamp
    })
    save_jobs(jobs)
    logger.info(f"Scheduled job {tx_hash}: {amount} tokens to {to_address} at {timestamp}")

def cancel_all_jobs() -> List[str]:
    jobs = load_jobs()
    cancelled = [job["tx_hash"] for job in jobs]
    save_jobs([])
    logger.info(f"Cancelled jobs: {cancelled}")
    return cancelled


def get_all_jobs() -> List[Dict[str, Any]]:
    """Return all pending scheduled jobs."""
    return load_jobs()

def run_scheduler() -> None:
    while True:
        logger.info("Checking jobs...")  # Debug
        try:
            jobs = load_jobs()
            current_time = int(time.time())
            logger.info(f"Current time: {current_time}, Jobs: {len(jobs)}")  # Debug
            remaining_jobs = []
            for job in jobs:
                if job["timestamp"] <= current_time:
                    result = send_token(job["to_address"], job["amount"], job["token_contract"])
                    if result["status"] == "success":
                        logger.info(f"Executed job {job['tx_hash']}: Sent {job['amount']} tokens to {job['to_address']}")
                    else:
                        logger.error(f"Failed to execute job {job['tx_hash']}: {result['message']}")
                        remaining_jobs.append(job)
                else:
                    remaining_jobs.append(job)
            save_jobs(remaining_jobs)
            time.sleep(10)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    run_scheduler()