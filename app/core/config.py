from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    
    # AI Settings
    AI_PROVIDER: str = "gemini" # Default to gemini
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

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
    UPLOAD_RETENTION_MINUTES: int = 2

    # Logging Settings
    LOG_LEVEL: str = "INFO"

    # UI Settings
    DEFAULT_CURRENCY: str = "EUR"
    THEME_MODE: str = "light" # light, dark, auto

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

# Load user settings from JSON if it exists (overrides .env)
import json
import os

USER_SETTINGS_PATH = "app/user_settings.json"
if os.path.exists(USER_SETTINGS_PATH):
    try:
        with open(USER_SETTINGS_PATH, "r") as f:
            user_data = json.load(f)
            for key, value in user_data.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
    except Exception as e:
        print(f"Failed to load user settings: {e}")
