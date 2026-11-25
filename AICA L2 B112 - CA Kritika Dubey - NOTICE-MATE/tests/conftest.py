import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Tests must never touch the real workspace: point the data folder at a throwaway temp folder
# BEFORE any noticemate module is imported (logging/settings are created at import time).
import tempfile  # noqa: E402

os.environ["NOTICEMATE_DATA_DIR"] = tempfile.mkdtemp(prefix="nm_test_boot_")

# Tests never load the real .env (keys stay out). Only the two OCR paths are copied from it.
os.environ["NOTICEMATE_NO_DOTENV"] = "1"
for _k in [k for k in os.environ if k.startswith(("ANTHROPIC_", "GEMINI_")) or k in ("NOTICEMATE_AI_ENABLED", "NOTICEMATE_ENCRYPTION_KEY")]:
    os.environ.pop(_k, None)
try:
    from dotenv import dotenv_values

    _vals = dotenv_values(ROOT / ".env") if (ROOT / ".env").exists() else {}
    for _k in ("TESSERACT_CMD", "POPPLER_PATH"):
        if _vals.get(_k) and not os.environ.get(_k):
            os.environ[_k] = _vals[_k]
except Exception:
    pass


@pytest.fixture(scope="session", autouse=True)
def workspace(tmp_path_factory):
    ws = tmp_path_factory.mktemp("nm_ws")
    os.environ["NOTICEMATE_DATA_DIR"] = str(ws)
    os.environ["NOTICEMATE_AI_PROVIDER"] = "offline-echo"
    os.environ.pop("ANTHROPIC_API_KEY", None)
    from noticemate.core.config import reset_settings
    from noticemate.core.db import init_db
    from noticemate.services.taxlaw import seed_registry

    reset_settings()
    init_db()
    seed_registry()
    if not (ROOT / "sample_data" / "bank_statement_PQR.xlsx").exists():
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "generate_fictional_data.py")])
    return ws


@pytest.fixture(scope="session")
def users(workspace):
    from noticemate.services import auth

    admin = auth.create_user("admin", "Admin User", "ADMIN", "Adm1n!Passw0rd")
    ca = auth.create_user("ca.sharma", "CA Test Reviewer", "CA", "Ca!Passw0rd123", membership_no="000000", actor_id=admin["id"])
    staff = auth.create_user("staff1", "Staff One", "STAFF", "Staff!Pass123", actor_id=admin["id"])
    outsider = auth.create_user("staff2", "Staff Two", "STAFF", "Staff!Pass456", actor_id=admin["id"])
    return {"admin": admin, "ca": ca, "staff": staff, "outsider": outsider}


def sample(name: str) -> bytes:
    return (ROOT / "sample_data" / name).read_bytes()
