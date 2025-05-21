# cli.py
import argparse
import sys
from ChainPilot.actions.chainpilot_actions import send_token
from scheduler.job_scheduler import add_scheduled_job
from utils import log, error
from wallet_provider import wallet_provider

def main():
    parser = argparse.ArgumentParser(description="ChainPilot CLI Tool")

    subparsers = parser.add_subparsers(dest="command")

    # Transfer command
    transfer_parser = subparsers.add_parser("transfer")
    transfer_parser.add_argument("to_address", help="Recipient wallet address")
    transfer_parser.add_argument("amount", type=float, help="Amount of token to send")

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule")
    schedule_parser.add_argument("to_address", help="Recipient wallet address")
    schedule_parser.add_argument("amount", type=float, help="Amount to transfer")
    schedule_parser.add_argument("timestamp", help="Future Unix timestamp to run the job")

    args = parser.parse_args()

    if args.command == "transfer":
        recipient_address = args.to_address
        amount = args.amount
        token_contract = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # Example: USDC contract address
        try:
            tx_hash = send_token(wallet_provider, recipient_address, amount, token_contract)
            log(f"Transaction sent successfully! Hash: {tx_hash}")
        except Exception as e:
            error(f"Transfer failed: {str(e)}")

    elif args.command == "schedule":
        try:
            job = {
                "type": "transfer",
                "to_address": args.to_address,
                "amount": args.amount,
                "timestamp": args.timestamp
            }
            add_scheduled_job(job)
            log("Transfer scheduled successfully.")
        except Exception as e:
            error(f"Scheduling failed: {str(e)}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
