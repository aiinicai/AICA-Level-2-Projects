"""Tenant-scoped task CRUD.

A task owns the client, input/output, and workflow OneDrive selections used by
one agent. Agent knowledge, references, instructions, and model settings remain
on the agent.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from api.agents import normalize_kb_folder_paths
from api.auth import request_context
from supabase_config import supabase_admin

tasks_bp = Blueprint("tasks", __name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _visible_agent_ids(context) -> list[str]:
    if context.is_superadmin:
        rows = (
            supabase_admin.table("agents").select("id")
            .eq("tenant_id", context.tenant_id).eq("is_active", True).execute().data
            or []
        )
    else:
        rows = (
            supabase_admin.table("agent_assignments").select("agent_id")
            .eq("tenant_id", context.tenant_id).eq("admin_user_id", context.user_id)
            .execute().data
            or []
        )
    return [str(row.get("id") or row.get("agent_id")) for row in rows]


def _agent(context, agent_id: str):
    if agent_id not in _visible_agent_ids(context):
        return None
    rows = (
        supabase_admin.table("agents").select("id,name")
        .eq("id", agent_id).eq("tenant_id", context.tenant_id).eq("is_active", True)
        .limit(1).execute().data
        or []
    )
    return rows[0] if rows else None


def _task(context, task_id: str):
    rows = (
        supabase_admin.table("tasks").select("id,agent_id,config_version")
        .eq("id", task_id).eq("tenant_id", context.tenant_id).eq("is_active", True)
        .limit(1).execute().data
        or []
    )
    if not rows or str(rows[0]["agent_id"]) not in _visible_agent_ids(context):
        return None
    return rows[0]


def _task_values(payload: dict, agent: dict):
    name = (payload.get("name") or "").strip()
    if not name:
        return None, "Task name is required"
    task_paths = normalize_kb_folder_paths(payload.get("task_file_paths"))
    workflow_paths = normalize_kb_folder_paths(payload.get("workflow_file_paths"))
    client_paths = normalize_kb_folder_paths(payload.get("client_file_paths"))
    if task_paths is None or workflow_paths is None or client_paths is None:
        return None, "File selections must be lists of OneDrive paths"

    task_folder = (payload.get("onedrive_folder_path") or "").strip()
    client_folder = (payload.get("client_folder_path") or "").strip()
    if not task_folder and not task_paths:
        return None, "Select a task folder or at least one input/output item"
    if not workflow_paths:
        return None, "Select a Workflow folder or at least one workflow file"

    return {
        "agent_id": agent["id"],
        "name": name[:100],
        "client_folder_path": client_folder or None,
        "client_file_paths": client_paths,
        "onedrive_folder_path": task_folder,
        "task_file_paths": task_paths,
        "workflow_file_paths": workflow_paths,
    }, None


@tasks_bp.route("/tasks", methods=["GET"])
def list_tasks():
    context, error = request_context()
    if error:
        return error
    agent_ids = _visible_agent_ids(context)
    if not agent_ids:
        return jsonify([]), 200
    rows = (
        supabase_admin.table("tasks").select("*")
        .eq("tenant_id", context.tenant_id).eq("is_active", True)
        .in_("agent_id", agent_ids).order("created_at", desc=True).execute().data
        or []
    )
    return jsonify(rows), 200


@tasks_bp.route("/tasks", methods=["POST"])
def create_task():
    context, error = request_context()
    if error:
        return error
    payload = request.get_json(force=True, silent=True) or {}
    agent = _agent(context, str(payload.get("agent_id") or ""))
    if not agent:
        return jsonify({"error": "Select an active agent in this tenant"}), 400
    values, validation_error = _task_values(payload, agent)
    if validation_error:
        return jsonify({"error": validation_error}), 400
    response = supabase_admin.table("tasks").insert({
        **values,
        "tenant_id": context.tenant_id,
        "created_by": context.user_id,
    }).execute()
    return jsonify(response.data[0]), 201


@tasks_bp.route("/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    context, error = request_context()
    if error:
        return error
    current = _task(context, task_id)
    if not current:
        return jsonify({"error": "Task not found"}), 404
    payload = request.get_json(force=True, silent=True) or {}
    agent = _agent(context, str(payload.get("agent_id") or ""))
    if not agent:
        return jsonify({"error": "Select an active agent in this tenant"}), 400
    values, validation_error = _task_values(payload, agent)
    if validation_error:
        return jsonify({"error": validation_error}), 400
    values.update({
        "config_version": int(current.get("config_version") or 1) + 1,
        "updated_at": _now(),
    })
    response = (
        supabase_admin.table("tasks").update(values)
        .eq("id", task_id).eq("tenant_id", context.tenant_id).execute()
    )
    return jsonify(response.data[0]), 200


@tasks_bp.route("/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    context, error = request_context()
    if error:
        return error
    if not _task(context, task_id):
        return jsonify({"error": "Task not found"}), 404
    response = (
        supabase_admin.table("tasks").update({
            "is_active": False, "archived_at": _now(), "updated_at": _now()
        })
        .eq("id", task_id).eq("tenant_id", context.tenant_id).eq("is_active", True)
        .execute()
    )
    if not response.data:
        return jsonify({"error": "Task not found"}), 404
    return jsonify({"success": True}), 200
