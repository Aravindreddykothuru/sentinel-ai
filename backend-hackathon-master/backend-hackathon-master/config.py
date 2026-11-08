from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./sentinel.db"

    # AI API Keys
    GOOGLE_API_KEY: str = ""
    XAI_API_KEY: str = ""

    # Gmail SMTP
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_FROM_EMAIL: str = ""

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_WHATSAPP_TO: str = ""

    # Application
    APP_NAME: str = "SENTINEL AI"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # CORS: comma-separated list of allowed origins ("*" allows any origin),
    # plus an optional regex, e.g. "https://.*\.vercel\.app" for preview deployments
    CORS_ORIGINS: str = "*"
    CORS_ORIGIN_REGEX: str = ""

    # Alert Settings
    ALERT_THRESHOLD: int = 80
    CONFIRMATION_WAIT_SECONDS: int = 60
    ESCALATION_TIMEOUT_MINUTES: int = 15

    # Monitoring
    MAX_CONCURRENT_MACHINES: int = 50
    WEBSOCKET_UPDATE_INTERVAL: int = 2
    SCHEDULER_INTERVAL_SECONDS: int = 60
    # Force every Nth scheduled reading to critical values to exercise the alert pipeline (0 = off)
    DEMO_FORCE_CRITICAL_EVERY: int = 0
    # Seed the four dashboard demo machines on startup if they don't exist
    SEED_DEMO_DATA: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
