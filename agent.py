"""
AI Email Agent — Main Orchestrator

Reads recipients from Google Sheets, generates personalized emails with OpenAI,
and sends them via Hostinger SMTP in rate-limited batches.

Usage:
    python agent.py
"""

import time
import sys
import config
from sheets import get_recipients
from ai_generator import generate_email
from mailer import Mailer
from tracker import get_sent_emails, log_result


def run():
    print("=" * 60)
    print("  AI Email Agent")
    print("=" * 60)

    # Validate configuration
    config.validate()
    print("[OK] Configuration validated.\n")

    # Load recipients from Google Sheets
    print("Loading recipients from Google Sheets...")
    recipients = get_recipients()
    if not recipients:
        print("No recipients found. Check your Google Sheet.")
        sys.exit(1)

    # Filter out already-sent recipients
    already_sent = get_sent_emails()
    pending = [r for r in recipients if r["email"] not in already_sent]

    print(f"\nTotal recipients: {len(recipients)}")
    print(f"Already sent:    {len(already_sent)}")
    print(f"Pending:         {len(pending)}")

    if not pending:
        print("\nAll emails have already been sent. Nothing to do.")
        return

    # Confirm before sending
    print(f"\nReady to send {len(pending)} emails in batches of {config.BATCH_SIZE}.")
    answer = input("Proceed? (yes/no): ").strip().lower()
    if answer not in ("yes", "y"):
        print("Aborted.")
        return

    # Process in batches
    total = len(pending)
    sent_count = 0
    fail_count = 0

    for batch_start in range(0, total, config.BATCH_SIZE):
        batch = pending[batch_start : batch_start + config.BATCH_SIZE]
        batch_num = (batch_start // config.BATCH_SIZE) + 1
        total_batches = (total + config.BATCH_SIZE - 1) // config.BATCH_SIZE

        print(f"\n--- Batch {batch_num}/{total_batches} ({len(batch)} emails) ---")

        mailer = Mailer()
        try:
            mailer.connect()

            for i, recipient in enumerate(batch, 1):
                email = recipient["email"]
                name = recipient.get("name", "")
                progress = f"[{batch_start + i}/{total}]"

                try:
                    # Generate personalized email
                    print(f"{progress} Generating email for {name or email}...", end=" ")
                    result = generate_email(recipient)

                    # Send it
                    mailer.send(
                        to_email=email,
                        subject=result["subject"],
                        body=result["body"],
                        to_name=name,
                    )

                    log_result(email, name, "sent")
                    sent_count += 1
                    print("SENT")

                except Exception as e:
                    log_result(email, name, "failed", str(e))
                    fail_count += 1
                    print(f"FAILED: {e}")

        finally:
            mailer.disconnect()

        # Wait between batches (except after the last one)
        if batch_start + config.BATCH_SIZE < total:
            wait = config.DELAY_BETWEEN_BATCHES
            print(f"\nWaiting {wait}s before next batch...")
            time.sleep(wait)

    # Summary
    print("\n" + "=" * 60)
    print("  COMPLETE")
    print("=" * 60)
    print(f"  Sent:   {sent_count}")
    print(f"  Failed: {fail_count}")
    print(f"  Log:    {config.SEND_LOG_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    run()
