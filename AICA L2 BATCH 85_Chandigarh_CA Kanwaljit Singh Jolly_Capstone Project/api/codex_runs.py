"""Tenant-scoped Codex validation queue and run reporting API."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, send_file

from api.auth import can_access_agent, request_context
from services.check_report_pdf import build_check_report_pdf, report_filename
from supabase_config import supabase_admin

codex_runs_bp = Blueprint("codex_runs", __name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_run_snapshot(agent: dict, task: dict) -> dict:
    """Freeze agent intelligence and task inputs for a reproducible run."""
    return {
        "agent_id": agent["id"],
        "task_id": task["id"],
        "task_name": task.get("name"),
        "agent_config_version": agent.get("config_version", 1),
        "task_config_version": task.get("config_version", 1),
        "workflow_text": agent.get("workflow_text") or agent.get("system_prompt"),
        "workflow_file_paths": task.get("workflow_file_paths") or [],
        "onedrive_folder_path": task.get("onedrive_folder_path"),
        "task_file_paths": task.get("task_file_paths") or [],
        "client_folder_path": task.get("client_folder_path"),
        "client_file_paths": task.get("client_file_paths") or [],
        "kb_folder_paths": agent.get("kb_folder_paths") or [],
        "kb_file_paths": agent.get("kb_file_paths") or [],
        "reference_file_paths": agent.get("reference_file_paths") or {},
        "codex_model": agent.get("codex_model") or "gpt-5.6-sol",
        "codex_reasoning_effort": agent.get("codex_reasoning_effort") or "xhigh",
    }


def enqueue_codex_check(agent_id: str):
    context, error = request_context()
    if error:
        return error
    if not can_access_agent(context, agent_id):
        return jsonify({"error": "Agent not found or not assigned to you"}), 404

    agent_response = (
        supabase_admin.table("agents").select("*")
        .eq("id", agent_id).eq("tenant_id", context.tenant_id).single().execute()
    )
    agent = agent_response.data
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    payload = request.get_json(silent=True) or {}
    selected_task_id = str(payload.get("task_id") or "").strip()
    task_query = (
        supabase_admin.table("tasks").select("*")
        .eq("tenant_id", context.tenant_id).eq("agent_id", agent_id).eq("is_active", True)
    )
    if selected_task_id:
        task_rows = task_query.eq("id", selected_task_id).limit(1).execute().data or []
    else:
        task_rows = task_query.order("created_at", desc=True).limit(2).execute().data or []
    if not task_rows:
        return jsonify({"error": "Create and assign a task to this agent before running it"}), 409
    if not selected_task_id and len(task_rows) > 1:
        return jsonify({"error": "Select which assigned task this agent should run"}), 409
    task = task_rows[0]
    if not task.get("workflow_file_paths"):
        return jsonify({"error": "The selected task has no validation workflow configured"}), 409

    drive = supabase_admin.table("tenant_onedrive_connections").select("tenant_id").eq("tenant_id", context.tenant_id).limit(1).execute()
    codex = supabase_admin.table("tenant_codex_connections").select("tenant_id").eq("tenant_id", context.tenant_id).limit(1).execute()
    missing = []
    if not drive.data:
        missing.append("OneDrive")
    if not codex.data:
        missing.append("ChatGPT/Codex")
    if missing:
        return jsonify({"error": f"Tenant integration not connected: {', '.join(missing)}"}), 409

    snapshot = build_run_snapshot(agent, task)
    run_data = {
        "agent_id": agent_id,
        "task_id": task["id"],
        "tenant_id": context.tenant_id,
        "requested_by": context.user_id,
        "status": "QUEUED",
        "run_status": "QUEUED",
        "review_status": "NOT_REQUIRED",
        "result_summary": "Waiting for the tenant Codex worker",
        "config_snapshot": snapshot,
        "codex_model": snapshot["codex_model"],
        "codex_reasoning_effort": snapshot["codex_reasoning_effort"],
        "queued_at": _now(),
    }
    run_response = supabase_admin.table("check_runs").insert(run_data).execute()
    if not run_response.data:
        return jsonify({"error": "Unable to create check run"}), 500
    run = run_response.data[0]
    queue_task_response = supabase_admin.table("check_run_tasks").insert({
        "check_run_id": run["id"],
        "stage": "codex_validate",
        "status": "PENDING",
        "payload": {
            "agent_id": agent_id, "task_id": task["id"],
            "tenant_id": context.tenant_id, "requested_by": context.user_id,
        },
    }).execute()
    supabase_admin.table("check_run_events").insert({
        "check_run_id": run["id"], "tenant_id": context.tenant_id,
        "event_type": "queued", "message": "Validation queued",
    }).execute()
    return jsonify({
        "success": True,
        "check_run_id": run["id"],
        "task_id": task["id"],
        "queue_task_id": queue_task_response.data[0]["id"] if queue_task_response.data else None,
        "status": "QUEUED",
        "summary": "Validation queued. It will use the tenant-owned OneDrive and ChatGPT accounts.",
    }), 202


def _visible_run(context, run_id: str):
    query = supabase_admin.table("check_runs").select("*").eq("id", run_id).eq("tenant_id", context.tenant_id)
    if not context.is_superadmin:
        query = query.eq("requested_by", context.user_id)
    rows = query.limit(1).execute().data or []
    return rows[0] if rows else None


@codex_runs_bp.route("/check-runs", methods=["GET"])
def list_check_runs():
    context, error = request_context()
    if error:
        return error
    summary_only = request.args.get("summary_only", "").lower() == "true"
    columns = (
        "id,agent_id,task_id,status,run_status,codex_verdict,final_verdict,result_summary,"
        "review_status,codex_model,codex_reasoning_effort,created_at,queued_at,completed_at"
        if summary_only else "*"
    )
    query = supabase_admin.table("check_runs").select(columns).eq("tenant_id", context.tenant_id)
    if not context.is_superadmin:
        query = query.eq("requested_by", context.user_id)
    return jsonify(query.order("created_at", desc=True).limit(500 if summary_only else 100).execute().data or []), 200


#: Statuses that occupy the tenant's single Codex slot. Mirrors the guard in
#: claim_next_check_run_task(), which refuses to claim for a tenant that already
#: has a run in any of these states.
ACTIVE_RUN_STATUSES = ("PREPARING", "RUNNING", "FINALIZING")


def _queue_standing(run: dict) -> dict:
    """Where this run sits in its tenant's queue.

    Computed server-side because an admin can only read their own runs: the
    position is meaningless unless something can see the whole tenant queue.

    This is the position within the WORKSPACE, not a global one. The claim
    function is globally FIFO and merely skips tenants that are busy, so runs
    belonging to other tenants also sit ahead of this one. We cannot see those
    from here and deliberately do not guess at a wait time.
    """
    if run.get("run_status") != "QUEUED":
        return {"queue_position": None, "queue_ahead": None, "workspace_busy": False}

    queued_at = run.get("queued_at") or run.get("created_at")
    ahead = 0
    if queued_at:
        earlier = supabase_admin.table("check_runs").select("id", count="exact") \
            .eq("tenant_id", run["tenant_id"]).eq("run_status", "QUEUED") \
            .lt("queued_at", queued_at).execute()
        ahead = earlier.count or 0

    active = supabase_admin.table("check_runs").select("id", count="exact") \
        .eq("tenant_id", run["tenant_id"]).in_("run_status", list(ACTIVE_RUN_STATUSES)) \
        .neq("id", run["id"]).execute()

    return {
        "queue_position": ahead + 1,
        "queue_ahead": ahead,
        "workspace_busy": bool(active.count),
    }


@codex_runs_bp.route("/check-runs/<run_id>", methods=["GET"])
def get_check_run(run_id):
    context, error = request_context()
    if error:
        return error
    run = _visible_run(context, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    return jsonify({**run, **_queue_standing(run)}), 200


@codex_runs_bp.route("/check-runs/<run_id>/report.pdf", methods=["GET"])
def download_check_run_report(run_id):
    context, error = request_context()
    if error:
        return error
    run = _visible_run(context, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    if run.get("run_status") != "COMPLETED" or not run.get("result_json"):
        return jsonify({"error": "This run does not have a completed report"}), 409

    agent_rows = (
        supabase_admin.table("agents").select("name")
        .eq("id", run["agent_id"]).eq("tenant_id", context.tenant_id)
        .limit(1).execute().data or []
    )
    agent_name = agent_rows[0].get("name") if agent_rows else "Task Check"
    pdf = build_check_report_pdf(run, agent_name, include_config=context.is_superadmin)
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=report_filename(run, agent_name),
        max_age=0,
    )


@codex_runs_bp.route("/check-runs/<run_id>/events", methods=["GET"])
def get_check_run_events(run_id):
    context, error = request_context()
    if error:
        return error
    if not _visible_run(context, run_id):
        return jsonify({"error": "Run not found"}), 404
    events = supabase_admin.table("check_run_events").select("*").eq("check_run_id", run_id).order("id").execute().data or []
    return jsonify(events), 200


@codex_runs_bp.route("/check-runs/<run_id>/cancel", methods=["POST"])
def cancel_check_run(run_id):
    context, error = request_context()
    if error:
        return error
    run = _visible_run(context, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    if run.get("run_status") in {"COMPLETED", "ERROR", "CANCELLED"}:
        return jsonify({"error": "Run has already finished"}), 409
    supabase_admin.table("check_runs").update({"cancel_requested": True}).eq("id", run_id).execute()
    if run.get("run_status") == "QUEUED":
        supabase_admin.table("check_runs").update({"run_status": "CANCELLED", "status": "ERROR", "completed_at": _now()}).eq("id", run_id).execute()
        supabase_admin.table("check_run_tasks").update({"status": "CANCELLED"}).eq("check_run_id", run_id).eq("status", "PENDING").execute()
    return jsonify({"success": True}), 200


@codex_runs_bp.route("/check-runs/<run_id>/resolve", methods=["POST"])
def resolve_check_run(run_id):
    context, error = request_context("super_admin")
    if error:
        return error
    run = _visible_run(context, run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    payload = request.get_json(silent=True) or {}
    verdict = payload.get("verdict")
    reasoning = (payload.get("reasoning") or "").strip()
    if verdict not in {"PASS", "FAIL", "INDETERMINATE"} or not reasoning:
        return jsonify({"error": "verdict and reasoning are required"}), 400
    supabase_admin.table("check_runs").update({
        "final_verdict": verdict, "review_status": "RESOLVED", "status": verdict,
    }).eq("id", run_id).eq("tenant_id", context.tenant_id).execute()
    supabase_admin.table("human_reviews").update({
        "status": "resolved", "resolved_by": context.user_id, "final_verdict": verdict,
        "resolution": {"verdict": verdict}, "resolution_reasoning": reasoning,
        "resolved_at": _now(),
    }).eq("check_run_id", run_id).eq("tenant_id", context.tenant_id).execute()
    return jsonify({"success": True, "final_verdict": verdict}), 200
