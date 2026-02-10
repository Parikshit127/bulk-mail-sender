import re
import gspread
from google.oauth2.service_account import Credentials
import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_recipients():
    """Read all recipients from the configured Google Sheet.

    Returns a list of dicts, one per row. Column headers become keys.
    Rows with missing or invalid email addresses are skipped.
    """
    creds = Credentials.from_service_account_file(config.CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID).worksheet(config.SHEET_NAME)

    rows = sheet.get_all_records()

    recipients = []
    skipped = 0
    for row in rows:
        email = str(row.get("email", "")).strip().lower()
        if not email or not EMAIL_RE.match(email):
            skipped += 1
            continue
        row["email"] = email
        recipients.append(row)

    if skipped:
        print(f"Skipped {skipped} rows with missing/invalid email addresses.")
    print(f"Loaded {len(recipients)} recipients from Google Sheets.")
    return recipients
