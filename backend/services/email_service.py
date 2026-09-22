import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from backend.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service to handle transactional email delivery via SMTP."""

    def __init__(self):
        self.server_host = settings.SMTP_SERVER
        self.server_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.is_configured = bool(self.username and self.password)

    def send_email(self, to_email: str, subject: str, content: str) -> bool:
        """Sends an email with plain text body.

        Falls back to console logging if SMTP credentials are missing.
        """
        if not self.is_configured:
            logger.warning(
                "[EMAIL MOCK MODE] To: %s | Subject: %s | Body: %s",
                to_email,
                subject,
                content,
            )
            return True

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.username
        message["To"] = to_email

        # Attach standard plain-text payload
        part = MIMEText(content, "plain", "utf-8")
        message.attach(part)

        try:
            with smtplib.SMTP(self.server_host, self.server_port, timeout=10.0) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.username, self.password)
                server.sendmail(self.username, [to_email], message.as_string())

            logger.info("Email successfully dispatched to %s", to_email)
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Authentication failed. Verify SMTP_USERNAME and SMTP_PASSWORD.")
            return False
        except smtplib.SMTPException as exc:
            logger.error("SMTP error sending email to %s: %s", to_email, str(exc))
            return False
        except Exception as exc:
            logger.error("Unexpected error sending email to %s: %s", to_email, str(exc))
            return False
