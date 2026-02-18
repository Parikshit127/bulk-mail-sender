import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, make_msgid
import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Mailer:
    """SMTP email sender for Hostinger business email."""

    def __init__(self, sender_email=None, sender_password=None, sender_name=None):
        self.connection = None
        self.sender_email = sender_email or config.SMTP_EMAIL
        self.sender_password = sender_password or config.SMTP_PASSWORD
        self.sender_name = sender_name or config.SENDER_NAME

    def connect(self):
        """Open a connection to the SMTP server (SSL or TLS based on port)."""
        try:
            context = ssl.create_default_context()
            
            logger.info(f"Connecting to SMTP server: {config.SMTP_HOST}:{config.SMTP_PORT}")
            
            if config.SMTP_PORT == 465:
                # SSL connection (Hostinger default)
                self.connection = smtplib.SMTP_SSL(
                    config.SMTP_HOST, config.SMTP_PORT, context=context, timeout=30
                )
            else:
                # TLS/STARTTLS connection
                self.connection = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30)
                self.connection.starttls(context=context)
            
            self.connection.login(self.sender_email, self.sender_password)
            logger.info(f"Successfully logged in as {self.sender_email}")
            
        except smtplib.SMTPAuthenticationError:
            logger.error(f"Authentication failed for {self.sender_email}. Check email and password.")
            self.connection = None
            raise
        except smtplib.SMTPConnectError:
            logger.error("Failed to connect to the SMTP server.")
            self.connection = None
            raise
        except Exception as e:
            logger.error(f"Unexpected error during SMTP connection: {e}")
            self.connection = None
            raise

    def disconnect(self):
        """Close the SMTP connection gracefully."""
        if self.connection:
            try:
                self.connection.quit()
                logger.info("SMTP connection closed.")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
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
            try:
                self.connect()
            except Exception:
                logger.error(f"Cannot send email to {to_email} because connection failed.")
                return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr((self.sender_name, self.sender_email))
            msg["To"] = formataddr((to_name, to_email))
            msg["Subject"] = subject
            msg["Reply-To"] = self.sender_email
            # Hostinger requires valid Message-ID domain
            domain = self.sender_email.split("@")[1]
            msg["Message-ID"] = make_msgid(domain=domain)

            # Add sign-off with sender name
            full_body = f"{body}\n\nBest regards,\n{self.sender_name}"
            msg.attach(MIMEText(full_body, "plain"))

            self.connection.sendmail(self.sender_email, to_email, msg.as_string())
            logger.info(f"Email sent successfully to {to_email} from {self.sender_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            # Try to reconnect for next attempt if connection was lost
            self.disconnect()
            return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
