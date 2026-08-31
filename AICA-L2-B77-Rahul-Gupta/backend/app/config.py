"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "CompanyVal AI"
    database_url: str = f"sqlite:///{PROJECT_DIR / 'storage' / 'companyval.db'}"
    secret_key: str = "dev-secret-change-me"
    companyval_master_key: str = ""
    upload_dir: str = str(PROJECT_DIR / "storage" / "uploads")
    render_dir: str = str(PROJECT_DIR / "storage" / "rendered_pages")
    report_dir: str = str(PROJECT_DIR / "storage" / "reports")
    frontend_url: str = "http://localhost:5173"
    max_upload_mb: int = 25

    class Config:
        env_file = os.environ.get("COMPANYVAL_ENV_FILE", str(PROJECT_DIR / ".env"))
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    for d in (s.upload_dir, s.render_dir, s.report_dir):
        Path(d).mkdir(parents=True, exist_ok=True)
    return s
