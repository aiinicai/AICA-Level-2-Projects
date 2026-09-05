"""Verified Supabase authentication and tenant authorization helpers."""
from dataclasses import dataclass
from typing import Optional, Tuple

from flask import jsonify, request

from supabase_config import supabase_admin


def verified_user_id():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None, (jsonify({"error": "Unauthorized"}), 401)
    try:
        response = supabase_admin.auth.get_user(header.removeprefix("Bearer ").strip())
        user = getattr(response, "user", None)
        if not user:
            raise ValueError("Invalid token")
        return str(user.id), None
    except Exception:
        return None, (jsonify({"error": "Invalid or expired authentication token"}), 401)


@dataclass(frozen=True)
class RequestContext:
    user_id: str
    tenant_id: str
    role: str

    @property
    def is_superadmin(self) -> bool:
        return self.role == "super_admin"


def request_context(required_role: Optional[str] = None) -> Tuple[Optional[RequestContext], Optional[tuple]]:
    user_id, auth_error = verified_user_id()
    if auth_error:
        return None, auth_error
    try:
        membership_response = (
            supabase_admin.table("tenant_memberships")
            .select("tenant_id,role,status")
            .eq("user_id", user_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        memberships = membership_response.data or []
        if not memberships:
            return None, (jsonify({"error": "No active tenant membership"}), 403)
        membership = memberships[0]
        context = RequestContext(user_id, str(membership["tenant_id"]), membership["role"])
    except Exception:
        return None, (jsonify({"error": "Invalid or expired authentication token"}), 401)

    if required_role and context.role != required_role:
        return None, (jsonify({"error": "Superadmin access required"}), 403)
    return context, None


def can_access_agent(context: RequestContext, agent_id: str) -> bool:
    query = (
        supabase_admin.table("agents")
        .select("id")
        .eq("id", agent_id)
        .eq("tenant_id", context.tenant_id)
        .eq("is_active", True)
    )
    if not context.is_superadmin:
        assignments = (
            supabase_admin.table("agent_assignments")
            .select("agent_id")
            .eq("tenant_id", context.tenant_id)
            .eq("agent_id", agent_id)
            .eq("admin_user_id", context.user_id)
            .limit(1)
            .execute()
        )
        if not assignments.data:
            return False
    return bool(query.limit(1).execute().data)
