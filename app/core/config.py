from pydantic_settings import BaseSettings

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
        "Lebensmittel", "Restaurant", "Transport", "Fortgehen", "Rechnungen/Fixkosten",
        "Unterhaltung", "Gesundheit", "Reisen", "Shopping", "Geschenke", "Sonstiges"
    ]
    INCOME_CATEGORIES: list[str] = ["Gehalt", "Geschenk", "Sonstiges"]
    CURRENCIES: list[str] = ["EUR", "UNKNOWN"]
    
    # Dashboard Settings
    DASHBOARD_YEARS_LOOKBACK: int = 10 # list of available years

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"

settings = Settings()
