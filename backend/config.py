import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Resolve project root directory dynamically (one level above 'backend')
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Load the environment file if present
load_dotenv(dotenv_path=ENV_PATH)


@dataclass(frozen=True)
class Settings:
    # ---------------------------------------------------------
    # Twilio API Configuration
    # ---------------------------------------------------------
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "").strip()

    # ---------------------------------------------------------
    # SMTP / Email Notification Configuration
    # ---------------------------------------------------------
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()

    # ---------------------------------------------------------
    # Database Configuration
    # ---------------------------------------------------------
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "students.db")).strip()

    # ---------------------------------------------------------
    # OTP Expiry & Rate Control (in seconds)
    # ---------------------------------------------------------
    OTP_EXPIRY_SECONDS: int = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))

    # ---------------------------------------------------------
    # Server / App Settings
    # ---------------------------------------------------------
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0").strip()
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")


# Singleton instance accessible throughout the backend modules
settings = Settings()
