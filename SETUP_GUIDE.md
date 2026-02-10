# AI Email Agent — Complete Setup Guide

This guide walks you through setting up the AI Email Agent from scratch.

---

## Prerequisites

- **Python 3.8+** — Check with `python3 --version`
- **pip** — Comes with Python. Check with `pip3 --version`
- A **Hostinger business email** account
- A **Google account** (for Google Sheets + Google Cloud)
- An **OpenAI account** with API credits

---

## Step 1: Install Python Dependencies

Open your terminal and navigate to the project folder:

```bash
cd ~/Desktop/mail\ bot
pip3 install -r requirements.txt
```

This installs: `flask`, `python-dotenv`, `openai`, `gspread`, `google-auth`

---

## Step 2: Get Your Hostinger SMTP Credentials

1. Log in to [Hostinger hPanel](https://hpanel.hostinger.com)
2. Go to **Emails** in the left sidebar
3. Click **Manage** next to your domain
4. Your SMTP settings are:

| Setting | Value |
|---------|-------|
| SMTP Host | `smtp.hostinger.com` |
| SMTP Port | `465` (SSL) |
| Username | Your full email address (e.g., `hello@yourdomain.com`) |
| Password | The password you set when creating the email account |

> If you forgot your email password, go to **Emails → Email Accounts** and reset it.

---

## Step 3: Get Your OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Go to **API Keys** (left sidebar → API keys)
4. Click **Create new secret key**
5. Copy the key (starts with `sk-...`) — you won't see it again!

> The agent uses `gpt-4o-mini` which costs ~$0.15 per 1M input tokens. Sending 1000 emails costs roughly $0.50–$1.00.

---

## Step 4: Set Up Google Sheets API

This is the longest step, but you only do it once.

### 4a. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown (top bar) → **New Project**
3. Name it anything (e.g., "Email Agent") → **Create**
4. Make sure the new project is selected in the top bar

### 4b. Enable Google Sheets API

1. Go to **APIs & Services → Library** (left sidebar)
2. Search for **Google Sheets API**
3. Click it → **Enable**

### 4c. Create a Service Account

1. Go to **APIs & Services → Credentials** (left sidebar)
2. Click **Create Credentials → Service Account**
3. Name it anything (e.g., "email-agent") → **Done**
4. Click on the service account you just created
5. Go to the **Keys** tab
6. Click **Add Key → Create new key → JSON → Create**
7. A `.json` file will download — **this is your credentials file**

### 4d. Place the Credentials File

1. Rename the downloaded file to `credentials.json`
2. Move it into the `mail bot/` folder (same folder as `app.py`)

### 4e. Share Your Google Sheet

1. Open the `credentials.json` file in any text editor
2. Find the `"client_email"` field — it looks like `email-agent@yourproject.iam.gserviceaccount.com`
3. Copy that email address
4. Open your Google Sheet → click **Share** → paste the service account email → give **Viewer** access → **Send**

---

## Step 5: Prepare Your Google Sheet

Create a Google Sheet with these exact column headers in the **first row**:

| name | email | company | role | custom_note |
|------|-------|---------|------|-------------|
| Jane Smith | jane@acme.com | Acme Inc | CTO | Spoke at AI conf 2024 |
| Bob Wilson | bob@startup.io | Startup IO | Founder | LinkedIn connection |

**Required column:** `email`
**Optional columns:** `name`, `company`, `role`, `custom_note` (or any others — the AI uses all of them for personalization)

### Finding Your Sheet ID

Your Google Sheet URL looks like:
```
https://docs.google.com/spreadsheets/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit
```
The Sheet ID is the long string between `/d/` and `/edit`:
```
1aBcDeFgHiJkLmNoPqRsTuVwXyZ
```

---

## Step 6: Fill In Your .env File

Open the `.env` file in the `mail bot/` folder and fill in your real values:

```env
# Hostinger SMTP Settings
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_EMAIL=hello@yourdomain.com
SMTP_PASSWORD=your_actual_email_password

# Display name for the "From" field
SENDER_NAME=Your Full Name

# OpenAI API Key
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# Google Sheets
GOOGLE_SHEET_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ
SHEET_NAME=Sheet1

# Rate Limiting (adjust if needed)
BATCH_SIZE=50
DELAY_BETWEEN_BATCHES=60

# This tells the AI what the email campaign is about
EMAIL_PURPOSE=We are reaching out to potential clients to introduce our web development services and schedule a discovery call.
```

> **Important:** The `EMAIL_PURPOSE` is critical — it tells the AI what kind of email to write. Be specific!

---

## Step 7: Run the Dashboard

```bash
cd ~/Desktop/mail\ bot
python3 app.py
```

You'll see:
```
  AI Email Agent Dashboard
  http://localhost:5000
```

Open **http://localhost:5000** in your browser.

---

## Step 8: Test With a Few Emails First

**Do NOT send to 1000 people on your first run.** Test first:

1. Create a test Google Sheet with 2–3 of **your own email addresses**
2. Update `GOOGLE_SHEET_ID` in `.env` to point to the test sheet
3. Open the dashboard → click **Load from Google Sheets**
4. Click **Preview** on a recipient to see the AI-generated email
5. If the preview looks good, click **Start Sending**
6. Check your inboxes — verify the emails arrived and look correct

---

## Step 9: Send to Your Full List

Once testing is successful:

1. Update `GOOGLE_SHEET_ID` in `.env` to your real recipient sheet
2. Clear the send log (click **Clear Log** in the dashboard)
3. Click **Load from Google Sheets** → verify the recipient count
4. Click **Start Sending**
5. Watch the progress bar and live counters

### Rate Limits

Hostinger business email allows approximately **500 emails per hour**. The default settings (50 per batch, 60s delay) send ~50/minute = ~3000/hour, which may be too fast.

**If you hit rate limits**, increase the delay:
```env
BATCH_SIZE=25
DELAY_BETWEEN_BATCHES=120
```
This sends ~12/minute = ~750/hour, a safe rate.

---

## Step 10: Resume After Interruption

If the agent stops mid-run (error, closed browser, etc.):

1. Just restart: `python3 app.py`
2. Click **Start Sending** again
3. It automatically skips already-sent emails (tracked in `send_log.csv`)

---

## Troubleshooting

### "Missing required environment variables"
→ Check your `.env` file. Make sure all values are filled in (no quotes needed for values).

### "Google service account file not found"
→ Make sure `credentials.json` is in the `mail bot/` folder.

### "Error loading Google Sheet"
→ Make sure you shared the sheet with the service account email (Step 4e).

### "SMTP Authentication Error"
→ Double-check your Hostinger email and password. Try logging into webmail first to confirm the password works.

### "Rate limit" or "Too many requests" from OpenAI
→ Your OpenAI account may need billing set up. Go to platform.openai.com → Billing → add payment method.

### "Connection timed out" (SMTP)
→ Some networks block port 465. Try changing `SMTP_PORT=587` in `.env`. If using port 587, the mailer will need TLS instead of SSL — let me know if you need this change.

### Emails going to spam
Tips to improve deliverability:
- Make sure your domain has **SPF** and **DKIM** records set up in Hostinger DNS
- Avoid spammy words in the `EMAIL_PURPOSE` (free, guaranteed, limited time, etc.)
- Don't send 1000 emails on day one — ramp up gradually (100/day, then 200, etc.)
- Make sure each email is unique (the AI handles this by personalizing each one)

---

## Project File Reference

| File | Purpose |
|------|---------|
| `app.py` | Web dashboard server (run this) |
| `agent.py` | CLI version (alternative to web dashboard) |
| `config.py` | Loads settings from `.env` |
| `sheets.py` | Reads recipients from Google Sheets |
| `ai_generator.py` | Generates emails using OpenAI GPT |
| `mailer.py` | Sends emails via Hostinger SMTP |
| `tracker.py` | Tracks sent/failed emails in CSV |
| `.env` | Your credentials and settings |
| `credentials.json` | Google service account key |
| `send_log.csv` | Auto-generated send history |

---

## Two Ways to Run

### Web Dashboard (recommended)
```bash
python3 app.py
# Open http://localhost:5000
```

### Command Line
```bash
python3 agent.py
# Follows prompts in terminal
```
