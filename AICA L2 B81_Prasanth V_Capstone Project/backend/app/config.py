import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
LOGOS_DIR = UPLOADS_DIR / "logos"
EXPORTS_DIR = UPLOADS_DIR / "exports"
BACKUPS_DIR = UPLOADS_DIR / "backups"

# Ensure runtime directories exist
for folder in [DATA_DIR, UPLOADS_DIR, LOGOS_DIR, EXPORTS_DIR, BACKUPS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'asset_tagging.db'}"

SECRET_KEY = os.getenv("SECRET_KEY", "asset-tagging-secret-key-super-secure-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
