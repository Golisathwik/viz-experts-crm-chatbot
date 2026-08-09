"""
Application Settings
--------------------
Central configuration for the entire backend.

Every module should import settings only from here.

Example:
    from config.settings import settings
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project Root
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application configuration loaded from .env
    """

    # ==========================================================
    # Application
    # ==========================================================
    APP_NAME: str = "Zoho CRM AI Assistant"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # ==========================================================
    # Server
    # ==========================================================
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ==========================================================
    # Database
    # ==========================================================
    DATABASE_NAME: str = "zoho_assistant.db"
    DATABASE_PATH: str = str(BASE_DIR.parent / "zoho_assistant.db")

    # ==========================================================
    # Security
    # ==========================================================
    JWT_SECRET_KEY: str = "change_this_secret_key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ==========================================================
    # API Keys (Optional)
    # ==========================================================
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ZOHO_API_KEY: str = ""
    
    # ==========================================================
    # Zoho OAuth
    # ==========================================================
    ZOHO_ACCOUNTS_URL: str = "https://accounts.zoho.in"

    ZOHO_REDIRECT_URI: str = ""

    # ==========================================================
    # Logging
    # ==========================================================
    LOG_LEVEL: str = "INFO"

    # ==========================================================
    # Uploads
    # ==========================================================
    MAX_UPLOAD_SIZE_MB: int = 25

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()