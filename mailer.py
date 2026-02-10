import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, make_msgid
import config


class Mailer:
    """SMTP email sender for Hostinger business email."""

    def __init__(self):
        self.connection = None

    def connect(self):
        """Open a connection to the SMTP server (SSL or TLS based on port)."""
        context = ssl.create_default_context()
        
        if config.SMTP_PORT == 465:
            # SSL connection (Hostinger, some providers)
            self.connection = smtplib.SMTP_SSL(
                config.SMTP_HOST, config.SMTP_PORT, context=context, timeout=30
            )
        else:
            # TLS/STARTTLS connection (Gmail, port 587)
            self.connection = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30)
            self.connection.starttls(context=context)
        
        self.connection.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)

    def disconnect(self):
        """Close the SMTP connection gracefully."""
        if self.connection:
            try:
                self.connection.quit()
            except Exception:
                pass
            self.connection = None

    def send(self, to_email, subject, body, to_name=""):
        """Send a single email.

        Args:
            to_email: Recipient email address.
            subject: Email subject line.
            body: Email body (plain text).
            to_name: Recipient display name (optional).
        """
        if not self.connection:
            self.connect()

        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr((config.SENDER_NAME, config.SMTP_EMAIL))
        msg["To"] = formataddr((to_name, to_email))
        msg["Subject"] = subject
        msg["Reply-To"] = config.SMTP_EMAIL
        msg["Message-ID"] = make_msgid(domain=config.SMTP_EMAIL.split("@")[1])

        # Add sign-off with sender name
        full_body = f"{body}\n\nBest regards,\n{config.SENDER_NAME}"
        msg.attach(MIMEText(full_body, "plain"))

        self.connection.sendmail(config.SMTP_EMAIL, to_email, msg.as_string())

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
