"""Application configuration module.

Loads environment variables from .env file or system runtime environments
(Render / Netlify / Docker) and exposes a strongly typed Settings object.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Resolve repository root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from root if it exists
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.is_file():
    load_dotenv(dotenv_path=ENV_PATH)


@dataclass(frozen=True)
class Settings:
    """Immutable application settings dataclass."""

    # Server Configuration
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0").strip()
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # Database Configuration (supports both raw path or DATABASE_URL)
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "students.db")).strip()
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{BASE_DIR / 'students.db'}"
    ).strip()

    # Security & OTP Configuration
    OTP_EXPIRY_SECONDS: int = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))

    # Twilio SMS API Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "").strip()

    # SMTP / Email Configuration
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()

    @property
    def is_twilio_configured(self) -> bool:
        """Check if Twilio has production-ready credentials."""
        return bool(
            self.TWILIO_ACCOUNT_SID
            and self.TWILIO_AUTH_TOKEN
            and self.TWILIO_PHONE_NUMBER
            and not self.TWILIO_ACCOUNT_SID.startswith("ACxxxxxxxx")
        )

    @property
    def is_smtp_configured(self) -> bool:
        """Check if SMTP credentials are provided for outbound email."""
        return bool(self.SMTP_USERNAME and self.SMTP_PASSWORD)


# Global singleton instance
settings = Settings()
