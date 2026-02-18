import os
import sys
import json
import tempfile
from dotenv import load_dotenv

load_dotenv()

# SMTP
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.hostinger.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "")
COMPANY_NAME = os.getenv("COMPANY_NAME", "")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")

# Rate limiting
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
DELAY_BETWEEN_BATCHES = int(os.getenv("DELAY_BETWEEN_BATCHES", "60"))

# Email context
EMAIL_PURPOSE = os.getenv("EMAIL_PURPOSE", "")

# Multiple sender accounts (Hostinger)
SENDER_ACCOUNTS = [
    {"email": "Adil@avanienterprises.in", "password": "AdilAvani@23", "name": "Adil"},
    {"email": "Vansh@avanienterprises.in", "password": "AvaniVansh@312", "name": "Vansh"},
    {"email": "Farhan@avanienterprises.in", "password": "AvaniFarhan@91", "name": "Farhan"},
    {"email": "Nitika@avanienterprises.in", "password": "AvaniNitika@89", "name": "Nitika"},
]


def get_sender_account(email):
    """Look up a sender account by email address."""
    for account in SENDER_ACCOUNTS:
        if account["email"].lower() == email.lower():
            return account
    return None

# Paths — support both file and env-var for credentials
_BASE_DIR = os.path.dirname(__file__)
_credentials_file_path = os.path.join(_BASE_DIR, "credentials.json")

# If GOOGLE_CREDENTIALS_JSON env var is set, write it to a temp file
# This allows deployment without shipping the credentials file
if os.getenv("GOOGLE_CREDENTIALS_JSON"):
    _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    _tmp.write(os.getenv("GOOGLE_CREDENTIALS_JSON"))
    _tmp.close()
    CREDENTIALS_FILE = _tmp.name
elif os.path.exists(_credentials_file_path):
    CREDENTIALS_FILE = _credentials_file_path
else:
    CREDENTIALS_FILE = _credentials_file_path  # Will fail at validate()

SEND_LOG_FILE = os.path.join(_BASE_DIR, "send_log.csv")

REQUIRED_VARS = {
    "SMTP_EMAIL": SMTP_EMAIL,
    "SMTP_PASSWORD": SMTP_PASSWORD,
    "OPENAI_API_KEY": OPENAI_API_KEY,
}


def reload():
    """Re-read .env and update all module-level variables."""
    global SMTP_HOST, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD, SENDER_NAME, COMPANY_NAME
    global OPENAI_API_KEY, GOOGLE_SHEET_ID, SHEET_NAME
    global BATCH_SIZE, DELAY_BETWEEN_BATCHES, EMAIL_PURPOSE, REQUIRED_VARS

    load_dotenv(override=True)

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.hostinger.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SENDER_NAME = os.getenv("SENDER_NAME", "")
    COMPANY_NAME = os.getenv("COMPANY_NAME", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
    SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
    DELAY_BETWEEN_BATCHES = int(os.getenv("DELAY_BETWEEN_BATCHES", "60"))
    EMAIL_PURPOSE = os.getenv("EMAIL_PURPOSE", "")
    REQUIRED_VARS = {
        "SMTP_EMAIL": SMTP_EMAIL,
        "SMTP_PASSWORD": SMTP_PASSWORD,
        "OPENAI_API_KEY": OPENAI_API_KEY,
    }


def validate():
    missing = [name for name, val in REQUIRED_VARS.items() if not val]
    if missing:
        print(f"WARNING: Missing environment variables: {', '.join(missing)}")
        print("Some features may not work without these.")
