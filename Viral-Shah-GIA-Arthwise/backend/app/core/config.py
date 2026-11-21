import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "GIA_Arthwise | Loan Proposal Evaluation & Debt Syndication"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "giaarthwise-secure-key-change-in-production-1234567890")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    
    # Database: GIAARTHWISE Relational DB
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{Path(__file__).resolve().parent.parent.parent}/giaarthwise.db"
    )
    
    # Storage & Case-wise Backend Folders
    STORAGE_DIR: str = os.getenv(
        "STORAGE_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "uploads")
    )
    CASES_DIR: str = os.getenv(
        "CASES_DIR",
        str(Path(__file__).resolve().parent.parent.parent.parent / "cases")
    )
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg"]
    
    # Cloud AI/OCR status (strictly disabled by default per Indian DPDP & security mandates)
    ENABLE_CLOUD_AI_OCR: bool = False
    CLOUD_AI_PROVIDER: str = "none"
    
    # External API Integrations (disabled by default until credentials & agreements exist)
    ENABLE_BUREAU_API: bool = False
    ENABLE_GST_API: bool = False
    ENABLE_BANK_AA_API: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Ensure base uploads and case-wise directories exist
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(settings.CASES_DIR, exist_ok=True)

def get_case_dir(proposal_code: str) -> str:
    """Returns and ensures the case-specific backend folder exists."""
    clean_code = proposal_code.strip().replace("/", "_").replace(" ", "_")
    case_path = os.path.join(settings.CASES_DIR, clean_code)
    os.makedirs(case_path, exist_ok=True)
    return case_path
