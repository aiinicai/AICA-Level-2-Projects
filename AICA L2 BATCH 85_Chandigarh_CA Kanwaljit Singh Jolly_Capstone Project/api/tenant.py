"""Tenant membership, assignment, and shared integration endpoints."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from postgrest.exceptions import APIError

from api.auth import can_access_agent, request_context, verified_user_id
from supabase_config import supabase_admin

tenant_bp = Blueprint("tenant", __name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _active_codex_login(tenant_id: str):
    return (
        supabase_admin.table("tenant_codex_login_sessions")
        .select("*")
        .eq("tenant_id", tenant_id)
        .in_("status", ["QUEUED", "WAITING_FOR_USER"])
        .gt("expires_at", _now())
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )


@tenant_bp.route("/tenant/provision", methods=["POST"])
def provision_tenant():
    """Idempotently make a newly signed-up customer the owner of a new tenant."""
    import re
    import uuid

    user_id, error = verified_user_id()
    if error:
        return error
    existing = supabase_admin.table("tenant_memberships").select("tenant_id,role,status") \
        .eq("user_id", user_id).limit(1).execute().data or []
    if existing:
        return jsonify(existing[0]), 200

    payload = request.get_json(silent=True) or {}
    profile_rows = supabase_admin.table("profiles").select("email,display_name").eq("id", user_id).limit(1).execute().data or []
    profile = profile_rows[0] if profile_rows else {}
    default_name = profile.get("display_name") or (profile.get("email") or "Task Checker").split("@")[0]
    name = (payload.get("name") or f"{default_name}'s workspace").strip()[:100]
    slug_base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "tenant"
    tenant_response = supabase_admin.table("tenants").insert({
        "name": name, "slug": f"{slug_base}-{uuid.uuid4().hex[:8]}"
    }).execute()
    tenant = tenant_response.data[0]
    membership_response = supabase_admin.table("tenant_memberships").insert({
        "tenant_id": tenant["id"], "user_id": user_id, "role": "super_admin", "status": "active"
    }).execute()
    return jsonify(membership_response.data[0]), 201


@tenant_bp.route("/tenant", methods=["GET"])
def get_tenant():
    context, error = request_context()
    if error:
        return error
    tenant = supabase_admin.table("tenants").select("id,name,slug,status,created_at").eq("id", context.tenant_id).single().execute().data
    return jsonify({**(tenant or {}), "role": context.role}), 200


@tenant_bp.route("/tenant/members", methods=["GET"])
def list_members():
    context, error = request_context("super_admin")
    if error:
        return error
    memberships = supabase_admin.table("tenant_memberships").select("*").eq("tenant_id", context.tenant_id).order("created_at").execute().data or []
    profile_ids = [row["user_id"] for row in memberships]
    profiles = supabase_admin.table("profiles").select("id,email,display_name,role").in_("id", profile_ids).execute().data if profile_ids else []
    by_id = {str(profile["id"]): profile for profile in (profiles or [])}
    return jsonify([{**row, "profile": by_id.get(str(row["user_id"]), {})} for row in memberships]), 200


@tenant_bp.route("/agents/<agent_id>/assignments", methods=["GET", "PUT"])
def agent_assignments(agent_id):
    context, error = request_context()
    if error:
        return error
    if not can_access_agent(context, agent_id):
        return jsonify({"error": "Agent not found"}), 404
    if request.method == "GET":
        rows = supabase_admin.table("agent_assignments").select("*").eq("tenant_id", context.tenant_id).eq("agent_id", agent_id).execute().data or []
        return jsonify(rows), 200

    admin_ids = (request.get_json(silent=True) or {}).get("admin_user_ids", [])
    if not isinstance(admin_ids, list):
        return jsonify({"error": "admin_user_ids must be an array"}), 400
    if not context.is_superadmin and context.user_id not in {str(value) for value in admin_ids}:
        admin_ids.append(context.user_id)
    valid = supabase_admin.table("tenant_memberships").select("user_id").eq("tenant_id", context.tenant_id).eq("role", "admin").eq("status", "active").in_("user_id", admin_ids).execute().data if admin_ids else []
    valid_ids = {str(row["user_id"]) for row in (valid or [])}
    if valid_ids != {str(value) for value in admin_ids}:
        return jsonify({"error": "Every assignment must target an active admin in this tenant"}), 400
    supabase_admin.table("agent_assignments").delete().eq("tenant_id", context.tenant_id).eq("agent_id", agent_id).execute()
    if valid_ids:
        supabase_admin.table("agent_assignments").insert([{
            "tenant_id": context.tenant_id, "agent_id": agent_id,
            "admin_user_id": admin_id, "assigned_by": context.user_id,
        } for admin_id in valid_ids]).execute()
    return jsonify({"success": True, "admin_user_ids": sorted(valid_ids)}), 200


@tenant_bp.route("/tenant/integrations", methods=["GET"])
def integration_status():
    context, error = request_context()
    if error:
        return error
    drive = supabase_admin.table("tenant_onedrive_connections").select("account_name,account_email,base_folder_path,updated_at").eq("tenant_id", context.tenant_id).limit(1).execute().data
    codex = supabase_admin.table("tenant_codex_connections").select("account_email,account_plan,sdk_version,connected_at,last_verified_at").eq("tenant_id", context.tenant_id).limit(1).execute().data
    if not context.is_superadmin:
        return jsonify({"onedrive": {"connected": bool(drive)}, "codex": {"connected": bool(codex)}}), 200
    return jsonify({"onedrive": drive[0] if drive else None, "codex": codex[0] if codex else None}), 200


@tenant_bp.route("/tenant/integrations/codex/login", methods=["POST"])
def start_codex_login():
    context, error = request_context("super_admin")
    if error:
        return error
    now = _now()
    supabase_admin.table("tenant_codex_login_sessions").update({
        "status": "EXPIRED", "updated_at": now
    }).eq("tenant_id", context.tenant_id).in_(
        "status", ["QUEUED", "WAITING_FOR_USER"]
    ).lte("expires_at", now).execute()

    active = _active_codex_login(context.tenant_id)
    if active:
        return jsonify(active[0]), 200

    try:
        response = supabase_admin.table("tenant_codex_login_sessions").insert({
            "tenant_id": context.tenant_id, "requested_by": context.user_id, "status": "QUEUED"
        }).execute()
        return jsonify(response.data[0]), 202
    except APIError as exc:
        # The partial unique index closes the race between simultaneous tabs.
        if str(getattr(exc, "code", "")) != "23505":
            raise
        active = _active_codex_login(context.tenant_id)
        if not active:
            raise
        return jsonify(active[0]), 200


@tenant_bp.route("/tenant/integrations/codex/login/<session_id>", methods=["GET"])
def codex_login_status(session_id):
    context, error = request_context("super_admin")
    if error:
        return error
    rows = supabase_admin.table("tenant_codex_login_sessions").select("id,status,verification_url,user_code,last_error,expires_at,updated_at").eq("id", session_id).eq("tenant_id", context.tenant_id).limit(1).execute().data or []
    if not rows:
        return jsonify({"error": "Login session not found"}), 404
    login = rows[0]
    expires_at = datetime.fromisoformat(login["expires_at"].replace("Z", "+00:00"))
    if login["status"] in {"QUEUED", "WAITING_FOR_USER"} and expires_at <= datetime.now(timezone.utc):
        login["status"] = "EXPIRED"
        supabase_admin.table("tenant_codex_login_sessions").update({
            "status": "EXPIRED", "updated_at": _now()
        }).eq("id", session_id).eq("tenant_id", context.tenant_id).execute()
    return jsonify(login), 200


@tenant_bp.route("/tenant/integrations/codex", methods=["DELETE"])
def disconnect_codex():
    context, error = request_context("super_admin")
    if error:
        return error
    supabase_admin.table("tenant_codex_connections").delete().eq("tenant_id", context.tenant_id).execute()
    return jsonify({"success": True}), 200
