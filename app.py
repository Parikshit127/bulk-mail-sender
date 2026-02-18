"""
AI Email Agent — Web Dashboard

Run with: python app.py
Opens at:  http://localhost:5002
"""

import threading
import time
import os
import re
import io
from flask import Flask, render_template, jsonify, request

import config
from sheets import get_recipients
from ai_generator import generate_email
from mailer import Mailer
from tracker import get_sent_emails, log_result, get_log_entries, clear_log

app = Flask(__name__)

# Email validation regex
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ── Shared state for background send process ────────────────────────────────
send_state = {
    "running": False,
    "stop_requested": False,
    "total": 0,
    "current": 0,
    "sent": 0,
    "failed": 0,
    "current_email": "",
    "status_message": "Idle",
}
send_lock = threading.Lock()

# ── In-memory recipient storage (for manual/file uploads) ──────────────────
uploaded_recipients = []


def _send_worker(recipients, sender_email=None, sender_password=None, sender_name=None):
    """Background worker that sends emails in batches."""
    global send_state

    total = len(recipients)
    send_state.update({
        "running": True,
        "stop_requested": False,
        "total": total,
        "current": 0,
        "sent": 0,
        "failed": 0,
        "current_email": "",
        "status_message": "Starting...",
    })

    try:
        batch_size = config.BATCH_SIZE
        delay = config.DELAY_BETWEEN_BATCHES

        for batch_start in range(0, total, batch_size):
            if send_state["stop_requested"]:
                send_state["status_message"] = "Stopped by user"
                break

            batch = recipients[batch_start : batch_start + batch_size]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            send_state["status_message"] = f"Batch {batch_num}/{total_batches}"

            mailer = Mailer(sender_email=sender_email, sender_password=sender_password, sender_name=sender_name)
            try:
                send_state["status_message"] = f"Connecting to SMTP server..."
                mailer.connect()
                send_state["status_message"] = f"Sending batch {batch_num}/{total_batches}"
                
                for recipient in batch:
                    if send_state["stop_requested"]:
                        break

                    email = recipient["email"]
                    name = recipient.get("name", "")
                    send_state["current"] += 1
                    send_state["current_email"] = email

                    try:
                        result = generate_email(recipient)
                        mailer.send(
                            to_email=email,
                            subject=result["subject"],
                            body=result["body"],
                            to_name=name,
                        )
                        log_result(email, name, "sent")
                        send_state["sent"] += 1
                    except Exception as e:
                        log_result(email, name, "failed", str(e))
                        send_state["failed"] += 1
            except Exception as e:
                # SMTP connection failed - log error for all remaining recipients in batch
                send_state["status_message"] = f"SMTP Error: {str(e)[:50]}"
                for recipient in batch:
                    if recipient["email"] != send_state.get("current_email", ""):
                        log_result(recipient["email"], recipient.get("name", ""), "failed", f"SMTP connection failed: {str(e)}")
                        send_state["failed"] += 1
                        send_state["current"] += 1
            finally:
                mailer.disconnect()

            # Wait between batches (skip after last batch or if stopping)
            if batch_start + batch_size < total and not send_state["stop_requested"]:
                send_state["status_message"] = f"Waiting {delay}s before next batch..."
                for _ in range(delay):
                    if send_state["stop_requested"]:
                        break
                    time.sleep(1)

        if not send_state["stop_requested"]:
            send_state["status_message"] = "Complete"
    except Exception as e:
        send_state["status_message"] = f"Error: {str(e)[:50]}"
    finally:
        # ALWAYS reset the running state
        send_state["running"] = False
        send_state["current_email"] = ""




def parse_csv_data(content, filename="uploaded.csv"):
    """Parse CSV content and return list of recipient dicts."""
    import csv
    
    recipients = []
    # Try to decode if bytes
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig')
    
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        # Normalize keys to lowercase
        normalized = {k.lower().strip(): v.strip() for k, v in row.items() if v}
        email = normalized.get('email', '').lower()
        if email and EMAIL_RE.match(email):
            normalized['email'] = email
            recipients.append(normalized)
    
    return recipients


def parse_excel_data(file_content):
    """Parse Excel content and return list of recipient dicts."""
    import pandas as pd
    
    df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
    # Normalize column names
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    recipients = []
    for _, row in df.iterrows():
        record = {k: str(v).strip() for k, v in row.items() if pd.notna(v) and str(v).strip()}
        email = record.get('email', '').lower()
        if email and EMAIL_RE.match(email):
            record['email'] = email
            recipients.append(record)
    
    return recipients


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/senders")
def api_senders():
    """Return available sender accounts (email + name only, no passwords)."""
    senders = [{"email": a["email"], "name": a["name"]} for a in config.SENDER_ACCOUNTS]
    return jsonify({"ok": True, "senders": senders})


@app.route("/api/recipients")
def api_recipients():
    """Load recipients from Google Sheets."""
    try:
        config.reload()
        recipients = get_recipients()
        return jsonify({"ok": True, "recipients": recipients, "source": "google_sheets"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/recipients/upload", methods=["POST"])
def api_upload_recipients():
    """Upload recipients from CSV or Excel file."""
    global uploaded_recipients
    
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({"ok": False, "error": "No file selected"}), 400
    
    filename = file.filename.lower()
    content = file.read()
    
    try:
        if filename.endswith('.csv'):
            recipients = parse_csv_data(content, filename)
        elif filename.endswith(('.xlsx', '.xls')):
            recipients = parse_excel_data(content)
        else:
            return jsonify({"ok": False, "error": "Unsupported file format. Use CSV or Excel (.xlsx)"}), 400
        
        if not recipients:
            return jsonify({"ok": False, "error": "No valid email addresses found in file. Ensure you have an 'email' column."}), 400
        
        uploaded_recipients = recipients
        return jsonify({
            "ok": True, 
            "recipients": recipients, 
            "count": len(recipients),
            "source": "file_upload",
            "filename": file.filename
        })
    except Exception as e:
        return jsonify({"ok": False, "error": f"Failed to parse file: {str(e)}"}), 500


@app.route("/api/recipients/manual", methods=["POST"])
def api_manual_recipients():
    """Add recipients manually."""
    global uploaded_recipients
    
    data = request.json
    if not data:
        return jsonify({"ok": False, "error": "No data provided"}), 400
    
    recipients = data.get('recipients', [])
    if not recipients:
        return jsonify({"ok": False, "error": "No recipients provided"}), 400
    
    # Validate and clean recipients
    valid_recipients = []
    for r in recipients:
        email = str(r.get('email', '')).strip().lower()
        if email and EMAIL_RE.match(email):
            cleaned = {
                'email': email,
                'name': str(r.get('name', '')).strip(),
                'company': str(r.get('company', '')).strip(),
                'role': str(r.get('role', '')).strip(),
                'custom_note': str(r.get('custom_note', '')).strip(),
            }
            # Remove empty fields
            cleaned = {k: v for k, v in cleaned.items() if v}
            cleaned['email'] = email  # Always keep email
            valid_recipients.append(cleaned)
    
    if not valid_recipients:
        return jsonify({"ok": False, "error": "No valid email addresses provided"}), 400
    
    # Append to existing uploaded recipients or replace
    mode = data.get('mode', 'replace')  # 'replace' or 'append'
    if mode == 'append':
        # Avoid duplicates
        existing_emails = {r['email'] for r in uploaded_recipients}
        for r in valid_recipients:
            if r['email'] not in existing_emails:
                uploaded_recipients.append(r)
                existing_emails.add(r['email'])
    else:
        uploaded_recipients = valid_recipients
    
    return jsonify({
        "ok": True,
        "recipients": uploaded_recipients,
        "count": len(uploaded_recipients),
        "source": "manual"
    })


@app.route("/api/recipients/current")
def api_current_recipients():
    """Get currently loaded recipients (from any source)."""
    return jsonify({
        "ok": True,
        "recipients": uploaded_recipients,
        "count": len(uploaded_recipients)
    })


@app.route("/api/recipients/clear", methods=["POST"])
def api_clear_recipients():
    """Clear uploaded recipients."""
    global uploaded_recipients
    uploaded_recipients = []
    return jsonify({"ok": True})


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """Generate a preview email for one recipient."""
    try:
        config.reload()
        recipient = request.json
        result = generate_email(recipient)
        # Add sign-off for preview
        result["body"] = f"{result['body']}\n\nBest regards,\n{config.SENDER_NAME}"
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/send", methods=["POST"])
def api_send():
    """Start the bulk send process in a background thread."""
    global uploaded_recipients
    
    with send_lock:
        if send_state["running"]:
            return jsonify({"ok": False, "error": "Send already in progress"}), 409

    try:
        config.reload()
        
        # Check request body for source preference and sender selection
        data = request.json or {}
        source = data.get('source', 'auto')  # 'auto', 'uploaded', 'sheets'
        selected_sender = data.get('sender_email', '')
        
        # Look up sender credentials
        sender_email = None
        sender_password = None
        sender_name = None
        if selected_sender:
            account = config.get_sender_account(selected_sender)
            if account:
                sender_email = account["email"]
                sender_password = account["password"]
                sender_name = account["name"]
            else:
                return jsonify({"ok": False, "error": f"Unknown sender: {selected_sender}"}), 400
        
        if source == 'sheets':
            recipients = get_recipients()
        elif source == 'uploaded' or (source == 'auto' and uploaded_recipients):
            recipients = uploaded_recipients
        else:
            recipients = get_recipients()
        
        if not recipients:
            return jsonify({"ok": False, "error": "No recipients loaded. Please load recipients first."}), 400
        
        already_sent = get_sent_emails()
        pending = [r for r in recipients if r["email"] not in already_sent]

        if not pending:
            return jsonify({"ok": False, "error": "No pending recipients. All emails already sent."})

        thread = threading.Thread(
            target=_send_worker,
            args=(pending,),
            kwargs={"sender_email": sender_email, "sender_password": sender_password, "sender_name": sender_name},
            daemon=True
        )
        thread.start()
        return jsonify({"ok": True, "pending": len(pending), "sender": sender_email or config.SMTP_EMAIL})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/stop", methods=["POST"])
def api_stop():
    """Request the send process to stop after the current email."""
    send_state["stop_requested"] = True
    return jsonify({"ok": True})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Force reset the send state (use if stuck)."""
    global send_state
    send_state.update({
        "running": False,
        "stop_requested": False,
        "total": 0,
        "current": 0,
        "sent": 0,
        "failed": 0,
        "current_email": "",
        "status_message": "Reset - Ready",
    })
    return jsonify({"ok": True, "message": "Send state has been reset"})



@app.route("/api/status")
def api_status():
    """Return current send progress."""
    return jsonify(send_state)


@app.route("/api/log")
def api_log():
    """Return all send log entries."""
    try:
        entries = get_log_entries()
        return jsonify({"ok": True, "entries": entries})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/log/clear", methods=["POST"])
def api_log_clear():
    """Clear the send log."""
    try:
        clear_log()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("\n  AI Email Agent Dashboard")
    print("  http://localhost:5002\n")
    app.run(debug=True, port=5002)
