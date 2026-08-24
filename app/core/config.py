import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Restaurant Sales & Reconciliation System"
    APP_ENV: str = "development"
    SECRET_KEY: str = "restaurant-super-secret-key-reconciliation-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/restaurant_reconcile.db"
    
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    EXPORT_DIR: str = str(BASE_DIR / "exports")
    LOG_DIR: str = str(BASE_DIR / "logs")
    SAMPLE_DATA_DIR: str = str(BASE_DIR / "sample_data")
    
    DEFAULT_DATE_TOLERANCE_DAYS: int = 3
    DEFAULT_AMOUNT_TOLERANCE: float = 0.05
    DEFAULT_CURRENCY: str = "INR"

    # Used only to read day-book photos. Excel / bank files stay local.
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_VISION_MODEL: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
for path_str in [settings.UPLOAD_DIR, settings.EXPORT_DIR, settings.LOG_DIR, settings.SAMPLE_DATA_DIR, str(BASE_DIR / "data")]:
    os.makedirs(path_str, exist_ok=True)
