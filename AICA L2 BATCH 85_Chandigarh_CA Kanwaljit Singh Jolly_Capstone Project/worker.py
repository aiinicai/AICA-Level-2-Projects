"""Durable FIFO worker for tenant-scoped Codex validation runs."""
import logging
import os
import signal
import socket
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from services.codex_executor import execute_codex_validation
from services.codex_workspace import build_prompt, materialize_workspace
from supabase_config import supabase_admin

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("taskchecker.worker")

WORKER_ID = os.getenv("TASKCHECKER_WORKER_ID", f"{socket.gethostname()}-{os.getpid()}")
POLL_SECONDS = float(os.getenv("TASKCHECKER_WORKER_POLL_SECONDS", "2"))
MAX_ATTEMPTS = int(os.getenv("TASKCHECKER_MAX_ATTEMPTS", "3"))
SHUTDOWN_REQUESTED = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_shutdown(signum, _frame) -> None:
    """Drain the current run, then exit without claiming another one."""
    global SHUTDOWN_REQUESTED
    SHUTDOWN_REQUESTED = True
    logger.info("Shutdown signal %s received; draining the current run", signum)


def _workspace_parent() -> str | None:
    if os.name != "nt":
        return None
    root = Path(__file__).resolve().parent / ".taskchecker-workspaces"
    root.mkdir(exist_ok=True)
    return str(root)


def _event(run_id: str, tenant_id: str, event_type: str, message: str, data=None) -> None:
    supabase_admin.table("check_run_events").insert({
        "check_run_id": run_id,
        "tenant_id": tenant_id,
        "event_type": event_type,
        "message": message,
        "data": data,
    }).execute()


def _heartbeat() -> None:
    supabase_admin.table("worker_heartbeats").upsert({
        "worker_id": WORKER_ID,
        "worker_type": "codex_validation",
        "last_seen_at": _now(),
        "metadata": {"pid": os.getpid(), "hostname": socket.gethostname()},
    }).execute()


def _claim():
    response = supabase_admin.rpc("claim_next_check_run_task", {
        "p_worker_id": WORKER_ID,
        "p_lease_seconds": int(os.getenv("TASKCHECKER_LEASE_SECONDS", "7200")),
    }).execute()
    return (response.data or [None])[0]


def _load_run_context(run_id: str, tenant_id: str):
    run = supabase_admin.table("check_runs").select("*").eq("id", run_id).eq("tenant_id", tenant_id).single().execute().data
    agent_record = supabase_admin.table("agents").select("*").eq("id", run["agent_id"]).eq("tenant_id", tenant_id).single().execute().data
    drive = supabase_admin.table("tenant_onedrive_connections").select("refresh_token").eq("tenant_id", tenant_id).single().execute().data
    codex = supabase_admin.table("tenant_codex_connections").select("encrypted_auth_blob,updated_at").eq("tenant_id", tenant_id).single().execute().data
    if not run or not agent_record or not drive or not codex:
        raise RuntimeError("Run configuration or tenant integration is missing")
    # The queued snapshot is authoritative; later superadmin edits affect only
    # future runs. Fall back to the record for migrated legacy rows.
    agent = {**agent_record, **(run.get("config_snapshot") or {})}
    return run, agent, drive, codex


def _complete(task_id: str, run: dict, execution: dict) -> None:
    result = execution["result"]
    verdict = result["verdict"]
    requires_review = verdict != "PASS"
    run_updates = {
        "run_status": "COMPLETED",
        "status": verdict,
        "codex_verdict": verdict,
        "review_status": "PENDING" if requires_review else "NOT_REQUIRED",
        "final_verdict": None if requires_review else "PASS",
        "result_json": result,
        "result_summary": result["summary"],
        "codex_sdk_version": execution["sdk_version"],
        "codex_thread_id": execution["thread_id"],
        "codex_turn_id": execution["turn_id"],
        "token_usage": execution["usage"],
        "completed_at": _now(),
    }
    supabase_admin.table("check_runs").update(run_updates).eq("id", run["id"]).execute()
    credential_update = supabase_admin.table("tenant_codex_connections").update({
        "encrypted_auth_blob": execution["updated_encrypted_auth_blob"],
        "last_verified_at": _now(),
        "updated_at": _now(),
    }).eq("tenant_id", run["tenant_id"])
    if execution.get("credential_updated_at"):
        credential_update = credential_update.eq("updated_at", execution["credential_updated_at"])
    credential_update.execute()
    supabase_admin.table("check_run_tasks").update({
        "status": "COMPLETED", "result": result, "lease_expires_at": None, "updated_at": _now()
    }).eq("id", task_id).execute()

    if requires_review:
        supabase_admin.table("human_reviews").insert({
            "check_run_id": run["id"],
            "tenant_id": run["tenant_id"],
            "conflicts": [],
            "model_responses": {"codex": result},
            "consensus_metadata": {"source": "codex_harness"},
            "status": "pending",
            "proposed_verdict": verdict,
        }).execute()
    _event(run["id"], run["tenant_id"], "completed", f"Codex validation completed: {verdict}", {"verdict": verdict})


def _fail(task_id: str, run_id: str, tenant_id: str, exc: Exception) -> None:
    task = supabase_admin.table("check_run_tasks").select("attempt_count").eq("id", task_id).single().execute().data or {}
    attempts = int(task.get("attempt_count", 1))
    detail = str(exc)[:4000]
    if attempts < MAX_ATTEMPTS:
        retry_at = datetime.now(timezone.utc) + timedelta(seconds=min(300, 15 * (2 ** (attempts - 1))))
        supabase_admin.table("check_run_tasks").update({
            "status": "PENDING", "last_error": detail, "claimed_by": None,
            "lease_expires_at": None, "next_attempt_at": retry_at.isoformat(), "updated_at": _now(),
        }).eq("id", task_id).execute()
        supabase_admin.table("check_runs").update({"run_status": "QUEUED", "status": "QUEUED", "error_detail": detail}).eq("id", run_id).execute()
        _event(run_id, tenant_id, "retry_scheduled", "Transient run failure; retry scheduled", {"attempt": attempts})
        return
    supabase_admin.table("check_run_tasks").update({
        "status": "FAILED", "last_error": detail, "lease_expires_at": None, "updated_at": _now()
    }).eq("id", task_id).execute()
    supabase_admin.table("check_runs").update({
        "run_status": "ERROR", "status": "ERROR", "error_code": type(exc).__name__,
        "error_detail": detail, "result_summary": "Codex validation failed", "completed_at": _now(),
    }).eq("id", run_id).execute()
    _event(run_id, tenant_id, "failed", "Codex validation failed", {"error": type(exc).__name__})


def process_one() -> bool:
    claimed = _claim()
    if not claimed:
        return False
    task_id = claimed.get("task_id") or claimed.get("id")
    run_id = claimed["check_run_id"]
    tenant_id = claimed["tenant_id"]
    try:
        run, agent, drive, codex = _load_run_context(run_id, tenant_id)
        if run.get("cancel_requested"):
            raise RuntimeError("Run was cancelled before execution")
        _event(run_id, tenant_id, "preparing", "Downloading tenant-configured OneDrive files")
        with tempfile.TemporaryDirectory(
            prefix=f"taskchecker-{run_id}-", dir=_workspace_parent()
        ) as workspace:
            materialize_workspace(agent, drive["refresh_token"], workspace)
            supabase_admin.table("check_runs").update({"run_status": "RUNNING"}).eq("id", run_id).execute()
            _event(run_id, tenant_id, "running", "Official Codex harness started")
            execution = execute_codex_validation(
                workspace=workspace,
                prompt=build_prompt(agent),
                model=run.get("codex_model") or agent.get("codex_model") or "gpt-5.6-sol",
                effort=run.get("codex_reasoning_effort") or agent.get("codex_reasoning_effort") or "xhigh",
                encrypted_auth_blob=codex["encrypted_auth_blob"],
            )
            execution["credential_updated_at"] = codex.get("updated_at")
        supabase_admin.table("check_runs").update({"run_status": "FINALIZING"}).eq("id", run_id).execute()
        _complete(task_id, run, execution)
    except Exception as exc:
        logger.exception("Run %s failed", run_id)
        _fail(task_id, run_id, tenant_id, exc)
    return True


def main() -> None:
    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)
    logger.info("Task Checker Codex worker %s started", WORKER_ID)
    while not SHUTDOWN_REQUESTED:
        try:
            _heartbeat()
            if not process_one():
                time.sleep(POLL_SECONDS)
        except Exception:
            logger.exception("Worker loop error")
            time.sleep(POLL_SECONDS)
    logger.info("Task Checker Codex worker %s stopped cleanly", WORKER_ID)


if __name__ == "__main__":
    main()
