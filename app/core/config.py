from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Database Selection
    DB_TYPE: str = "postgres" # postgres, sqlite
    SQLITE_FILE: str = "xpensetracker.db"

    # Postgres Settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "xpense"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    # AI Settings
    AI_PROVIDER: str = "gemini" # Default to gemini
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Auth Settings
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    AUTH_SECRET: str = "change-this-secret-in-production"

    # App Constants
    EXPENSE_CATEGORIES: list[str] = [
        "Lebensmittel", "Restaurant", "Transport", "Fortgehen", "Rechnungen/Fixkosten", "Miete",
        "Unterhaltung", "Gesundheit", "Reisen", "Shopping", "Geschenke", "Sonstiges"
    ]
    INCOME_CATEGORIES: list[str] = ["Gehalt", "Geschenk", "Sonstiges"]
    CURRENCIES: list[str] = ["EUR", "UNKNOWN"]
    
    # Dashboard Settings
    DASHBOARD_YEARS_LOOKBACK: int = 10 # list of available years

    # File Upload Settings
    UPLOAD_RETENTION_MINUTES: int = 1440

    # Logging Settings
    LOG_LEVEL: str = "INFO"

    # UI Settings
    DEFAULT_CURRENCY: str = "EUR"
    THEME_MODE: str = "light" # light, dark, auto

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            # Store in the app/data directory so it persists with the volume mount in Docker
            return f"sqlite:///./app/data/{self.SQLITE_FILE}"
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

# Load user settings from JSON if it exists (overrides .env)
import json
import os

USER_SETTINGS_PATH = "app/data/user_settings.json"
if os.path.exists(USER_SETTINGS_PATH):
    try:
        with open(USER_SETTINGS_PATH, "r") as f:
            user_data = json.load(f)
            for key, value in user_data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
    except Exception as e:
        print(f"Failed to load user settings: {e}")
