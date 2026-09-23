"""Email Dispatch Service using Resend HTTPS API (Port 443).

Bypasses cloud provider (Render) socket blocks on SMTP ports 25, 465, and 587.
Falls back cleanly to mock logging if RESEND_API_KEY is not configured.
"""

import json
import os
import re
import urllib.error
import urllib.request
from typing import Optional

try:
    from backend.config import settings
except ImportError:
    try:
        from config import settings
    except ImportError:
        settings = None


class EmailService:
    def __init__(self):
        # Read directly from environment or fallback to settings object if defined
        self.api_key: Optional[str] = os.getenv("RESEND_API_KEY")
        if not self.api_key and settings and hasattr(settings, "RESEND_API_KEY"):
            self.api_key = getattr(settings, "RESEND_API_KEY")

        # Free tier default domain sender; update once custom domain is verified
        self.from_email: str = os.getenv("EMAIL_FROM", "EduPortal <onboarding@resend.dev>")

    def send_email(self, to_email: str, subject: str, content: str) -> bool:
        """Dispatches an email via Resend HTTPS REST API.

        Args:
            to_email: Target recipient address.
            subject: Subject line.
            content: Raw message text containing the OTP.

        Returns:
            bool: True if accepted by Resend (HTTP 200/201), False otherwise.
        """
        clean_email = to_email.strip().lower()

        # Fallback to mock logging if no API key is provided
        if not self.api_key or self.api_key.startswith("your_"):
            print(f"\n================================================")
            print(f"[EMAIL MOCK MODE] Outbound to: {clean_email}")
            print(f"Subject: {subject}")
            print(f"Body:\n{content}")
            print(f"================================================\n")
            return False

        # Extract 6-digit OTP passcode for styled HTML presentation
        otp_match = re.search(r"\b\d{4,8}\b", content)
        otp_display = otp_match.group(0) if otp_match else "------"

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 500px; margin: 0 auto; background-color: #0b0f19; color: #f8fafc; padding: 28px; border-radius: 12px; border: 1px solid #222f49;">
            <div style="margin-bottom: 20px;">
                <h2 style="color: #3b82f6; margin: 0; font-size: 20px;">⚡ EduPortal Verification</h2>
                <p style="color: #94a3b8; font-size: 13px; margin: 6px 0 0 0;">Two-Step Student Account Activation</p>
            </div>
            
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.5;">Hello,</p>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.5;">Please use the one-time verification passcode below to complete your registration:</p>
            
            <div style="font-size: 32px; font-weight: 700; letter-spacing: 6px; padding: 18px; background: #151d30; color: #10b981; text-align: center; border-radius: 8px; margin: 24px 0; border: 1px solid #222f49;">
                {otp_display}
            </div>
            
            <p style="color: #94a3b8; font-size: 12px; line-height: 1.5;">
                This code is valid for <strong>5 minutes</strong>. If you did not initiate this request, you can safely ignore this message.
            </p>
            
            <hr style="border: 0; border-top: 1px solid #222f49; margin: 24px 0 16px 0;" />
            <p style="color: #64748b; font-size: 11px; margin: 0;">Automated message from EduPortal Verification Engine.</p>
        </div>
        """

        payload = {
            "from": self.from_email,
            "to": [clean_email],
            "subject": subject,
            "html": html_body,
            "text": content,
        }

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key.strip()}",
                "Content-Type": "application/json",
                "User-Agent": "EduPortal-Backend/2.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=12.0) as response:
                if response.status in (200, 201):
                    res_body = response.read().decode("utf-8")
                    print(f"[✓] Resend API Success: Dispatched to {clean_email} | Response: {res_body}")
                    return True

        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            print(f"[!] Resend HTTP API Error ({e.code}) for {clean_email}: {err_msg}")
            return False
        except Exception as e:
            print(f"[!] Unexpected error during email dispatch to {clean_email}: {e}")
            return False

        return False
