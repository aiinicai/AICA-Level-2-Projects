"""Separate worker for tenant ChatGPT device-code login sessions."""
import json
import logging
import os
import queue
import shutil
import socket
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from services.credential_vault import encrypt_secret
from supabase_config import supabase_admin

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("taskchecker.codex_login")
WORKER_ID = os.getenv(
    "TASKCHECKER_LOGIN_WORKER_ID",
    f"login-{socket.gethostname()}-{os.getpid()}",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _LoginStopped(RuntimeError):
    pass


def _heartbeat() -> None:
    supabase_admin.table("worker_heartbeats").upsert({
        "worker_id": WORKER_ID, "worker_type": "codex_login", "last_seen_at": _now()
    }).execute()


def _login_session_status(session_id: str) -> str:
    rows = (
        supabase_admin.table("tenant_codex_login_sessions")
        .select("status,expires_at")
        .eq("id", session_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        return "CANCELLED"
    row = rows[0]
    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if row["status"] in {"QUEUED", "WAITING_FOR_USER"} and expires_at <= datetime.now(timezone.utc):
        supabase_admin.table("tenant_codex_login_sessions").update({
            "status": "EXPIRED", "updated_at": _now()
        }).eq("id", session_id).execute()
        return "EXPIRED"
    return row["status"]


def _wait_for_login(login, session_id: str, poll_seconds: float = 2.0):
    outcome = queue.Queue(maxsize=1)

    def wait() -> None:
        try:
            outcome.put((True, login.wait()))
        except BaseException as exc:
            outcome.put((False, exc))

    threading.Thread(target=wait, daemon=True).start()
    while True:
        try:
            succeeded, value = outcome.get(timeout=poll_seconds)
        except queue.Empty:
            _heartbeat()
            status = _login_session_status(session_id)
            if status in {"CANCELLED", "EXPIRED"}:
                try:
                    login.cancel()
                finally:
                    raise _LoginStopped(status)
            continue
        if succeeded:
            return value
        raise value


def process_one() -> bool:
    response = supabase_admin.rpc("claim_next_codex_login", {"p_worker_id": WORKER_ID}).execute()
    claimed = (response.data or [None])[0]
    if not claimed:
        return False
    session_id = claimed["session_id"]
    tenant_id = claimed["tenant_id"]
    requested_by = claimed["requested_by"]
    codex_home = Path(tempfile.mkdtemp(prefix="taskchecker-login-"))
    try:
        from openai_codex import Codex, CodexConfig, __version__

        with Codex(CodexConfig(env={"CODEX_HOME": str(codex_home)})) as codex:
            login = codex.login_chatgpt_device_code()
            supabase_admin.table("tenant_codex_login_sessions").update({
                "verification_url": login.verification_url,
                "user_code": login.user_code,
                "updated_at": _now(),
            }).eq("id", session_id).execute()
            completion = _wait_for_login(login, session_id)
            success = bool(getattr(completion, "success", False))
            if not success:
                raise RuntimeError("ChatGPT device login did not complete")
            session_rows = supabase_admin.table("tenant_codex_login_sessions").select("status") \
                .eq("id", session_id).limit(1).execute().data or []
            if not session_rows or session_rows[0]["status"] == "CANCELLED":
                return True
            account_response = codex.account(refresh_token=True)
            account = getattr(account_response, "account", None)
            account_data = account.model_dump(mode="json") if hasattr(account, "model_dump") else {}

        auth_path = codex_home / "auth.json"
        if not auth_path.exists():
            raise RuntimeError("Codex login completed without creating auth.json")
        supabase_admin.table("tenant_codex_connections").upsert({
            "tenant_id": tenant_id,
            "encrypted_auth_blob": encrypt_secret(auth_path.read_bytes()),
            "account_email": account_data.get("email"),
            "account_plan": account_data.get("plan_type") or account_data.get("planType"),
            "sdk_version": __version__,
            "connected_by": requested_by,
            "last_verified_at": _now(),
            "updated_at": _now(),
        }).execute()
        supabase_admin.table("tenant_codex_login_sessions").update({"status": "CONNECTED", "updated_at": _now()}).eq("id", session_id).execute()
    except _LoginStopped as exc:
        logger.info("Codex login %s stopped: %s", session_id, exc)
    except Exception as exc:
        logger.exception("Codex login %s failed", session_id)
        supabase_admin.table("tenant_codex_login_sessions").update({
            "status": "FAILED", "last_error": str(exc)[:2000], "updated_at": _now()
        }).eq("id", session_id).execute()
    finally:
        shutil.rmtree(codex_home, ignore_errors=True)
    return True


def main() -> None:
    logger.info("Task Checker Codex login worker started")
    while True:
        try:
            _heartbeat()
            if not process_one():
                time.sleep(2)
        except KeyboardInterrupt:
            return
        except Exception:
            logger.exception("Login worker loop error")
            time.sleep(2)


if __name__ == "__main__":
    main()
