"""Start an ISOLATED V3 test copy with fictional PQR data only.

    python scripts\\test_workspace.py            set up (first time) and start the test app
    python scripts\\test_workspace.py --setup    set up only, do not start

What makes it separate from your real V3 case workspace:
* Its data folder is V3\\test-workspace (its own database, documents, logs, backups).
* It runs on different ports: engine 8010, screens http://localhost:8511
  (your normal instance uses 8000 / 8501).
* It does NOT load .env. Only the two OCR paths are copied from .env; API keys and the
  encryption key never reach the test processes. AI is forced OFF.
* Test logins are fictional, created only in this test database, and written to
  test-workspace\\TEST-LOGIN.txt (never printed to the screen).
* Before starting and after stopping it fingerprints (SHA-256) V3\\workspace\\noticemate.db and
  V3\\source-data\\noticemate.db and reports whether either changed. It only reads them.
Press Ctrl+C in this window to stop the test app.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = ROOT / "test-workspace"
REAL_DBS = [ROOT / "workspace" / "noticemate.db", ROOT / "source-data" / "noticemate.db"]
API_PORT, UI_PORT = 8010, 8511
MARKER = "FICTIONAL TEST WORKSPACE — contains only fictional PQR sample data. Safe to delete.\n"


def fingerprint() -> dict[str, str]:
    out = {}
    for p in REAL_DBS:
        if p.exists():
            h = hashlib.sha256()
            with open(p, "rb") as f:  # read-only
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            out[str(p.relative_to(ROOT))] = h.hexdigest()
        else:
            out[str(p.relative_to(ROOT))] = "(not present)"
    return out


def normal_data_dir() -> str:
    """Where the NORMAL configuration (with .env) points. Reads config only; creates nothing."""
    code = "from noticemate.core.config import Settings; print(Settings().data_dir)"
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    return (r.stdout or "").strip() or "(could not be determined)"


def build_test_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("NOTICEMATE_", "ANTHROPIC_", "GEMINI_")) and k not in ("TESSERACT_CMD", "POPPLER_PATH")}
    try:
        from dotenv import dotenv_values

        vals = dotenv_values(ROOT / ".env")
        for k in ("TESSERACT_CMD", "POPPLER_PATH"):  # OCR paths only — nothing else is read
            if vals.get(k):
                env[k] = vals[k]
    except Exception:
        pass
    env.update({
        "NOTICEMATE_NO_DOTENV": "1",
        "NOTICEMATE_DATA_DIR": str(TEST_DIR),
        "NOTICEMATE_AI_ENABLED": "false",
        "NOTICEMATE_API_HOST": "127.0.0.1",
        "NOTICEMATE_API_PORT": str(API_PORT),
        "NOTICEMATE_API_URL": f"http://127.0.0.1:{API_PORT}/api",
        "NOTICEMATE_UI_ORIGIN": f"http://localhost:{UI_PORT}",
        "PYTHONPATH": str(ROOT),
    })
    return env


def setup(env: dict[str, str]) -> None:
    TEST_DIR.mkdir(exist_ok=True)
    (TEST_DIR / "FICTIONAL-TEST-WORKSPACE.txt").write_text(MARKER, encoding="utf-8")
    if not (ROOT / "sample_data" / "bank_statement_PQR.xlsx").exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_fictional_data.py")], cwd=ROOT, env=env, check=True)
    login_file = TEST_DIR / "TEST-LOGIN.txt"
    if login_file.exists():
        print("Test workspace already set up (logins in test-workspace\\TEST-LOGIN.txt).")
        return
    pw = {r: f"Test-{secrets.token_hex(5)}-Aa1!" for r in ("admin", "ca", "staff")}
    code = (
        "import json,sys\n"
        "from noticemate.core.db import init_db\n"
        "from noticemate.services import auth, taxlaw, authorities\n"
        "pw=json.loads(sys.stdin.read())\n"
        "init_db(); taxlaw.seed_registry(); authorities.import_registry()\n"
        "a=auth.create_user('test.admin','Test Admin (fictional)','ADMIN',pw['admin'])\n"
        "auth.create_user('test.ca','Test CA Reviewer (fictional)','CA',pw['ca'],membership_no='000000',actor_id=a['id'])\n"
        "auth.create_user('test.staff','Test Staff (fictional)','STAFF',pw['staff'],actor_id=a['id'])\n"
    )
    import json

    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, input=json.dumps(pw), text=True, check=True)
    login_file.write_text(
        "FICTIONAL TEST ACCOUNTS — valid only in this isolated test workspace (http://localhost:%d).\n"
        "test.admin   %s\ntest.ca      %s\ntest.staff   %s\n" % (UI_PORT, pw["admin"], pw["ca"], pw["staff"]), encoding="utf-8")
    print("Created test database and three fictional test logins (saved in test-workspace\\TEST-LOGIN.txt).")


def main() -> int:
    if TEST_DIR.resolve() == (ROOT / "workspace").resolve():
        sys.exit("Refusing: test folder would be the real workspace.")
    print("=" * 66)
    print("NOTICE-MATE V3 — ISOLATED FICTIONAL TEST WORKSPACE")
    print("=" * 66)
    normal = normal_data_dir()
    print(f"Your NORMAL configuration stores data in : {normal}")
    nd = Path(normal)
    if nd.is_dir():
        b = sorted(p.name for p in (nd / "backups").glob("noticemate_pre_v3_*.db")) if (nd / "backups").is_dir() else []
        print(f"  pre-V3 automatic backups found there    : {', '.join(b) if b else 'none'}")
    if nd.resolve() == TEST_DIR.resolve():
        sys.exit("Refusing: your normal configuration points at the test folder.")
    print(f"This TEST copy stores data in            : {TEST_DIR}")
    before = fingerprint()
    env = build_test_env()
    setup(env)
    if "--setup" in sys.argv:
        return 0
    print(f"\nStarting test engine on port {API_PORT} and test screens on http://localhost:{UI_PORT} …")
    api = subprocess.Popen([sys.executable, "-m", "noticemate.api.main"], cwd=ROOT, env=env)
    time.sleep(3)
    ui = subprocess.Popen([sys.executable, "-m", "streamlit", "run", str(ROOT / "frontend" / "app.py"), "--server.address", "127.0.0.1",
                           "--server.port", str(UI_PORT), "--server.headless", "true", "--browser.gatherUsageStats", "false"],
                          cwd=ROOT, env=env)
    print(f"\nTEST APP READY: http://localhost:{UI_PORT}   (press Ctrl+C here to stop)\n")
    try:
        while api.poll() is None and ui.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in (ui, api):
            if p.poll() is None:
                p.terminate()
    after = fingerprint()
    print("\nReal V3 databases after the test session:")
    for k in before:
        print(f"  {k}: {'UNCHANGED' if before[k] == after[k] else 'CHANGED — tell Claude'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
