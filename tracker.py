import csv
import os
from datetime import datetime
import config


FIELDNAMES = ["email", "name", "status", "timestamp", "error"]


def _ensure_log_file():
    """Create the send log CSV with headers if it doesn't exist."""
    if not os.path.exists(config.SEND_LOG_FILE):
        with open(config.SEND_LOG_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def get_sent_emails():
    """Return a set of email addresses that have already been sent successfully."""
    _ensure_log_file()
    sent = set()
    with open(config.SEND_LOG_FILE, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") == "sent":
                sent.add(row["email"].strip().lower())
    return sent


def log_result(email, name, status, error=""):
    """Append a send result to the log file.

    Args:
        email: Recipient email address.
        name: Recipient name.
        status: 'sent' or 'failed'.
        error: Error message if failed.
    """
    _ensure_log_file()
    with open(config.SEND_LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow({
            "email": email,
            "name": name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "error": error,
        })


def get_log_entries():
    """Return all log entries as a list of dicts."""
    _ensure_log_file()
    with open(config.SEND_LOG_FILE, "r", newline="") as f:
        return list(csv.DictReader(f))


def clear_log():
    """Delete the send log to start fresh."""
    if os.path.exists(config.SEND_LOG_FILE):
        os.remove(config.SEND_LOG_FILE)
