"""
AuditVault - AI-Powered Internal Audit Engagement and Working Paper Management System
Fully functional, database-connected application with real SQLite persistence, file vaulting,
Indian locale formatting, and high-contrast AV Monogram visual design.
Run: python -m streamlit run app.py  (or: streamlit run app.py)
"""

import os
import base64
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, date
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

# Configure Streamlit
st.set_page_config(
    page_title="AuditVault - Secure Internal Audit Workspace",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database and ORM Models
from database import init_db, get_db
from models import (
    User, Client, Team, TeamMemberMapping, Engagement,
    EngagementTeamAssignment, RCMLineItem, WorkingPaper,
    Observation, CommentThread, AuditTrailEntry
)
from auth import hash_password, verify_password, authorize_demo_device
from rcm_import import read_uploaded_rcm
from utils import (
    format_indian_currency, format_indian_number, format_indian_date,
    normalize_indian_date_input, parse_indian_date, current_indian_date_str,
    current_indian_timestamp_str, is_overdue, get_line_item_storage_dir,
    get_all_version_folders, save_uploaded_file, get_engagement_letter_dir,
    consolidate_engagement_files, log_audit_action, BASE_VAULT_DIR
)

# Initialize database schema and default records
init_db()
db = get_db()
APP_DIR = Path(__file__).resolve().parent
SAMPLE_DATA_DIR = APP_DIR / "sample_data"

# =====================================================================
# BRANDING CONSTANTS & SESSION STATE
# =====================================================================
NAVY = "#0A2642"
NAVY2 = "#155D8B"
GOLD = "#D9A441"
BLUE_ICON = "#5B92F5"

STATUS_COLORS = {
    "Draft": "#8A94A8",
    "Assigned": "#D9A441",
    "In Progress": "#2F6FED",
    "Overdue": "#D64545",
    "Completed": "#1E9E62"
}

ss = st.session_state
ss.setdefault("theme", "Light")
ss.setdefault("auth", False)
ss.setdefault("user_id", None)
ss.setdefault("username", "rohit.sharma")
ss.setdefault("role", "Manager")
ss.setdefault("user_name", "Rohit Sharma")
ss.setdefault("page", "Dashboard")
ss.setdefault("selected_engagement_id", None)
ss.setdefault("impersonating", False)
ss.setdefault("true_admin_id", None)
ss.setdefault("true_admin_name", None)
ss.setdefault("show_new_eng_form", False)

# Set initial user if not set
if ss.user_id is None:
    initial_user = db.query(User).filter(
        User.username == ss.username, User.is_deleted == False
    ).first()
    if initial_user:
        ss.user_id = initial_user.user_id
        ss.role = initial_user.role
        ss.user_name = initial_user.name

# Indian numbering format helper
def inr(n):
    return format_indian_currency(n)


def derive_audit_category(entry):
    if entry.action_category:
        return entry.action_category
    action = (entry.action_type or "").upper()
    entity = (entry.target_entity or "").upper()
    if "IMPERSONAT" in action:
        return "Admin Sessions"
    if entity == "USER" or "PASSWORD" in action or "LOGIN" in action:
        return "Users"
    if entity == "TEAM" or "TEAM" in action:
        return "Teams"
    if entity == "CLIENT":
        return "Clients"
    if "ASSIGN" in action or "ALLOCAT" in action:
        return "Allocations"
    return "System"


def expected_audit_hash(entry, previous_hash):
    payload = {
        "id": entry.id,
        "timestamp": entry.timestamp_str,
        "action": entry.action_type,
        "entity": entry.target_entity,
        "target_id": entry.target_id or "",
        "description": entry.description,
        "user_id": entry.user_id,
        "actor": entry.acting_user_name,
        "previous_hash": previous_hash,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def verify_audit_hash_chain(entries):
    previous_hash = "GENESIS"
    status_by_id = {}
    for entry in sorted(entries, key=lambda item: item.id):
        expected = expected_audit_hash(entry, previous_hash)
        valid = entry.previous_hash == previous_hash and entry.integrity_hash == expected
        status_by_id[entry.id] = valid
        previous_hash = entry.integrity_hash or expected
    return status_by_id


def parse_audit_json(value):
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except (TypeError, json.JSONDecodeError):
        return {"raw": value}


def render_access_control_audit(embedded=False):
    """Render the dedicated RBAC and access-accountability ledger."""
    all_entries = db.query(AuditTrailEntry).order_by(AuditTrailEntry.id.asc()).all()
    user_roles = {user.user_id: user.role for user in db.query(User).all()}
    access_entries = [
        entry for entry in all_entries
        if derive_audit_category(entry) in {"Users", "Teams", "Clients", "Allocations", "Admin Sessions"}
    ]
    integrity_status = verify_audit_hash_chain(all_entries)
    verified_count = sum(1 for entry in all_entries if integrity_status.get(entry.id))
    integrity_percent = round((verified_count / len(all_entries) * 100), 1) if all_entries else 100.0
    key_prefix = "team_access" if embedded else "trail_access"

    if not embedded:
        st.markdown(
            f"<h2 style='margin:0 0 4px;color:{tx};font-size:20px;'>Access Control & RBAC Accountability</h2>",
            unsafe_allow_html=True,
        )
        st.caption("User, team, client, allocation, credential, and impersonation activity with chained integrity verification")

    metric_specs = [
        ("Access Events", len(access_entries)),
        ("User Provisions", sum(1 for entry in access_entries if "CREATE_USER" in entry.action_type.upper() or "USER_CREATED" in entry.action_type.upper())),
        ("Audit Teams Formed", sum(1 for entry in access_entries if entry.action_type.upper() in {"CREATE_TEAM", "AUDIT_TEAM_CREATED"})),
        ("Client Entities", db.query(Client).count()),
        ("Admin Sessions", sum(1 for entry in access_entries if "IMPERSONAT" in entry.action_type.upper())),
    ]
    metric_columns = st.columns(5)
    for metric_column, (label, value) in zip(metric_columns, metric_specs):
        metric_column.metric(label, value)

    integrity_color = "#1E9E62" if integrity_percent == 100 else "#D64545"
    st.markdown(
        f"<div class='template-note' style='border-left-color:{integrity_color};'>"
        f"<b>SHA-256 append-only chain: {integrity_percent:.1f}% verified</b> · "
        "Each audit event stores its own integrity hash and the previous event hash.</div>",
        unsafe_allow_html=True,
    )
    st.caption("Network origin is recorded as the local loopback address in this desktop deployment.")

    governance_columns = st.columns(3)
    governance_cards = [
        ("Manager authority", "Create clients, audit teams, Team Members, and engagement allocations. Cannot create Managers."),
        ("Admin authority", "Create Managers or Team Members, reset credentials, and use logged support impersonation."),
        ("Team Member authority", "Execute assigned audit work. No client, team, or user provisioning rights."),
    ]
    for governance_column, (title, body) in zip(governance_columns, governance_cards):
        with governance_column:
            st.markdown(
                f"<div class='av-card' style='min-height:112px;border-top:3px solid {GOLD};'>"
                f"<b>{title}</b><div class='sub' style='margin-top:6px;'>{body}</div></div>",
                unsafe_allow_html=True,
            )

    filter_c1, filter_c2, filter_c3 = st.columns([2.4, 1.4, 1.2])
    with filter_c1:
        access_search = st.text_input(
            "Search access events", placeholder="Actor, target, ID, action, or RBAC rule",
            key=f"{key_prefix}_search",
        )
    with filter_c2:
        category_filter = st.selectbox(
            "Category",
            ["All Access Logs", "Users", "Teams", "Clients", "Allocations", "Admin Sessions"],
            key=f"{key_prefix}_category",
        )
    with filter_c3:
        actor_filter = st.selectbox(
            "Actor Role", ["All Roles", "Admin", "Manager", "Team Member", "System"],
            key=f"{key_prefix}_role",
        )

    filtered_entries = []
    for entry in reversed(access_entries):
        category = derive_audit_category(entry)
        actor_role = entry.actor_role or user_roles.get(entry.user_id, "System")
        haystack = " ".join([
            entry.acting_user_name or "", actor_role or "", entry.action_type or "",
            entry.target_entity or "", entry.target_id or "", entry.target_name or "",
            entry.target_role or "", entry.rbac_rule_applied or "", entry.description or "",
        ]).lower()
        if access_search and access_search.lower() not in haystack:
            continue
        if category_filter != "All Access Logs" and category != category_filter:
            continue
        if actor_filter != "All Roles" and actor_role != actor_filter:
            continue
        filtered_entries.append(entry)

    compliance_rows = []
    for entry in filtered_entries:
        actor_role = entry.actor_role or user_roles.get(entry.user_id, "System")
        compliance_rows.append({
            "Event ID": entry.id,
            "Timestamp (IST)": entry.timestamp_str,
            "Category": derive_audit_category(entry),
            "Actor": entry.acting_user_name,
            "Actor Role": actor_role,
            "Action": entry.action_type,
            "Entity": entry.target_entity,
            "Target ID": entry.target_id,
            "Target Name": entry.target_name or "",
            "Target Role": entry.target_role or "",
            "RBAC Rule Applied": entry.rbac_rule_applied or "",
            "Network Origin": entry.ip_address or "127.0.0.1",
            "Previous State": entry.previous_state_json or "",
            "New State": entry.new_state_json or "",
            "SHA-256": entry.integrity_hash or "",
            "Integrity": "Verified" if integrity_status.get(entry.id) else "Review Required",
            "Description": entry.description,
        })

    result_c1, result_c2 = st.columns([4, 1.5])
    result_c1.markdown(f"**{len(compliance_rows)} matching access event(s)**")
    with result_c2:
        compliance_frame = pd.DataFrame(compliance_rows)
        st.download_button(
            "Export Compliance CSV",
            data=compliance_frame.to_csv(index=False).encode("utf-8"),
            file_name="AuditVault_Access_Governance_ISO27001_SOC2_ICAI.csv",
            mime="text/csv",
            key=f"{key_prefix}_csv",
            width="stretch",
        )

    display_columns = [
        "Timestamp (IST)", "Category", "Actor", "Actor Role", "Action",
        "Target Name", "RBAC Rule Applied", "Integrity",
    ]
    st.dataframe(
        compliance_frame[display_columns] if not compliance_frame.empty else compliance_frame,
        width="stretch", hide_index=True,
    )

    if filtered_entries:
        event_options = {
            f"#{entry.id} · {entry.timestamp_str} · {entry.action_type} · {entry.acting_user_name}": entry
            for entry in filtered_entries
        }
        selected_event_label = st.selectbox(
            "Forensic event inspector", list(event_options.keys()), key=f"{key_prefix}_inspector"
        )
        selected_event = event_options[selected_event_label]
        previous_state = parse_audit_json(selected_event.previous_state_json)
        new_state = parse_audit_json(selected_event.new_state_json)
        with st.expander("Open state transition and JSON evidence", expanded=False):
            detail_c1, detail_c2 = st.columns(2)
            with detail_c1:
                st.markdown("**Previous state**")
                st.json(previous_state or {"status": "No previous-state snapshot recorded"})
            with detail_c2:
                st.markdown("**New state**")
                st.json(new_state or {"status": "No new-state snapshot recorded"})
            forensic_payload = {
                "event_id": selected_event.id,
                "timestamp_ist": selected_event.timestamp_str,
                "actor": selected_event.acting_user_name,
                "actor_role": selected_event.actor_role or user_roles.get(selected_event.user_id, "System"),
                "action": selected_event.action_type,
                "category": derive_audit_category(selected_event),
                "target": {
                    "entity": selected_event.target_entity,
                    "id": selected_event.target_id,
                    "name": selected_event.target_name,
                    "role": selected_event.target_role,
                },
                "network_origin": selected_event.ip_address,
                "rbac_rule_applied": selected_event.rbac_rule_applied,
                "previous_state": previous_state,
                "new_state": new_state,
                "metadata": parse_audit_json(selected_event.metadata_json),
                "previous_hash": selected_event.previous_hash,
                "integrity_hash": selected_event.integrity_hash,
                "integrity_verified": bool(integrity_status.get(selected_event.id)),
            }
            st.json(forensic_payload)
            st.download_button(
                "Download Event JSON",
                data=json.dumps(forensic_payload, indent=2, ensure_ascii=False),
                file_name=f"AuditVault_Access_Event_{selected_event.id}.json",
                mime="application/json",
                key=f"{key_prefix}_json_{selected_event.id}",
            )


def render_system_audit_ledger():
    audit_entries = db.query(AuditTrailEntry).order_by(AuditTrailEntry.id.desc()).all()
    integrity_status = verify_audit_hash_chain(audit_entries)
    audit_table_data = []
    for entry in audit_entries:
        audit_table_data.append({
            "Timestamp": entry.timestamp_str,
            "User": entry.acting_user_name,
            "Role": entry.actor_role or "Legacy / System",
            "Action": entry.action_type,
            "Category": derive_audit_category(entry),
            "Target": f"{entry.target_entity} [{entry.target_id}]" if entry.target_id else entry.target_entity,
            "Integrity": "Verified" if integrity_status.get(entry.id) else "Review Required",
            "Description": entry.description,
        })
    audit_frame = pd.DataFrame(audit_table_data)
    count_column, export_column = st.columns([4, 1.5])
    count_column.markdown(f"**Total Audit Records: `{len(audit_table_data)}`** · append-only SHA-256 chain")
    with export_column:
        st.download_button(
            label="Export System Ledger (CSV)",
            data=audit_frame.to_csv(index=False).encode("utf-8"),
            file_name="AuditVault_Immutable_AuditTrail.csv",
            mime="text/csv",
            width="stretch",
        )
    with st.container(border=True):
        st.dataframe(
            audit_frame, width="stretch", hide_index=True,
            column_config={
                "Timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
                "User": st.column_config.TextColumn("User", width="medium"),
                "Action": st.column_config.TextColumn("Action", width="small"),
                "Description": st.column_config.TextColumn("Description", width="large"),
            },
        )


def _remove_vault_targets(targets):
    """Delete only explicitly resolved paths inside AuditVault_Data."""
    vault_root = BASE_VAULT_DIR.resolve()
    removed = []
    errors = []
    unique_targets = []
    seen = set()
    for target in targets:
        if not target:
            continue
        candidate = Path(target).resolve()
        try:
            candidate.relative_to(vault_root)
        except ValueError:
            errors.append(f"Blocked unsafe path: {candidate}")
            continue
        normalized = str(candidate).lower()
        if candidate == vault_root or normalized in seen:
            continue
        seen.add(normalized)
        unique_targets.append(candidate)

    for candidate in unique_targets:
        try:
            if candidate.is_dir():
                shutil.rmtree(candidate)
                removed.append(str(candidate.relative_to(vault_root)))
            elif candidate.is_file():
                candidate.unlink()
                removed.append(str(candidate.relative_to(vault_root)))
        except OSError as exc:
            errors.append(f"{candidate.name}: {exc}")
    return removed, errors


def _engagement_vault_targets(engagement):
    """Return known local-storage targets for one engagement without deleting them."""
    engagement_id = engagement.engagement_id
    targets = [
        BASE_VAULT_DIR / "engagements" / str(engagement_id),
        BASE_VAULT_DIR / "engagement_letters" / str(engagement_id),
        BASE_VAULT_DIR / "rcm" / str(engagement_id),
        BASE_VAULT_DIR / "idr" / str(engagement_id),
    ]
    targets.extend((BASE_VAULT_DIR / "consolidated").glob(f"{engagement_id}_*"))
    targets.extend(
        (BASE_VAULT_DIR / "exports").glob(
            f"AuditVault_Consolidated_{engagement.engagement_code}_*.zip"
        )
    )
    if engagement.engagement_letter_path:
        targets.append(Path(engagement.engagement_letter_path).parent)
    if engagement.consolidation_zip_path:
        targets.append(Path(engagement.consolidation_zip_path))
    return targets


@st.dialog("Delete engagement")
def delete_engagement_dialog(engagement_id):
    target = db.get(Engagement, engagement_id)
    if not target or ss.role != "Manager":
        st.error("This engagement is unavailable or you do not have deletion permission.")
        return
    st.error(f"You are deleting {target.engagement_code} — {target.client.name}.")
    st.write("The engagement, RCM, assignments, observations, comments, and database file index will be removed.")
    delete_local_files = st.checkbox(
        "Also permanently delete locally stored evidence and base files",
        value=False,
        help="Includes working papers, engagement letters, RCM storage, consolidated folders, and exported ZIP files.",
        key=f"delete_eng_files_{engagement_id}",
    )
    confirmation = st.text_input(
        f"Type {target.engagement_code} to confirm",
        key=f"delete_eng_confirm_{engagement_id}",
    )
    if st.button("Permanently delete engagement", type="primary", width="stretch"):
        if confirmation.strip() != target.engagement_code:
            st.error("The engagement code does not match.")
            return
        snapshot = {
            "engagement_id": target.engagement_id,
            "engagement_code": target.engagement_code,
            "title": target.title,
            "client": target.client.name,
            "rcm_items": len(target.rcm_items),
            "working_papers": len(target.working_papers),
            "delete_local_files": delete_local_files,
        }
        storage_targets = _engagement_vault_targets(target) if delete_local_files else []
        code = target.engagement_code
        title = target.title
        try:
            db.delete(target)
            db.commit()
        except Exception as exc:
            db.rollback()
            st.error(f"Engagement deletion failed: {exc}")
            return
        removed, errors = _remove_vault_targets(storage_targets) if delete_local_files else ([], [])
        log_audit_action(
            session=db, action_type="ENGAGEMENT_DELETED", target_entity="Engagement",
            target_id=code, description=f"Manager {ss.user_name} deleted engagement {code}.",
            user_id=ss.user_id, acting_user_name=ss.user_name,
            true_admin_id=ss.true_admin_id, true_admin_name=ss.true_admin_name,
            actor_role=ss.role, target_name=title, action_category="Allocations",
            rbac_rule_applied="Manager may delete an engagement after exact-code confirmation and explicit local-file choice.",
            previous_state=snapshot,
            new_state={"deleted": True, "local_files_removed": removed, "storage_errors": errors},
        )
        ss.selected_engagement_id = None
        ss.page = "Dashboard"
        ss.delete_notice = (
            f"Engagement {code} deleted. "
            + (f"{len(removed)} local storage target(s) removed." if delete_local_files else "Local evidence was retained.")
            + (f" Storage warnings: {'; '.join(errors)}" if errors else "")
        )
        st.rerun()


@st.dialog("Delete client and engagements")
def delete_client_dialog(client_id):
    target = db.get(Client, client_id)
    if not target or ss.role != "Manager":
        st.error("This client is unavailable or you do not have deletion permission.")
        return
    engagements = list(target.engagements)
    st.error(f"You are deleting client '{target.name}' and {len(engagements)} linked engagement(s).")
    st.write("All linked engagement database records will also be removed.")
    delete_local_files = st.checkbox(
        "Also permanently delete all locally stored evidence and base files",
        value=False,
        help="Applies to every engagement belonging to this client.",
        key=f"delete_client_files_{client_id}",
    )
    confirmation = st.text_input(
        f"Type {target.name} to confirm", key=f"delete_client_confirm_{client_id}"
    )
    if st.button("Permanently delete client", type="primary", width="stretch"):
        if confirmation.strip() != target.name:
            st.error("The client name does not match.")
            return
        snapshot = {
            "client_id": target.client_id,
            "name": target.name,
            "industry": target.industry,
            "engagement_codes": [eng.engagement_code for eng in engagements],
            "delete_local_files": delete_local_files,
        }
        storage_targets = []
        if delete_local_files:
            for engagement in engagements:
                storage_targets.extend(_engagement_vault_targets(engagement))
        client_name = target.name
        try:
            for engagement in engagements:
                db.delete(engagement)
            db.flush()
            db.delete(target)
            db.commit()
        except Exception as exc:
            db.rollback()
            st.error(f"Client deletion failed: {exc}")
            return
        removed, errors = _remove_vault_targets(storage_targets) if delete_local_files else ([], [])
        log_audit_action(
            session=db, action_type="CLIENT_DELETED", target_entity="Client",
            target_id=str(client_id), description=f"Manager {ss.user_name} deleted client '{client_name}' and {len(engagements)} engagement(s).",
            user_id=ss.user_id, acting_user_name=ss.user_name,
            true_admin_id=ss.true_admin_id, true_admin_name=ss.true_admin_name,
            actor_role=ss.role, target_name=client_name, action_category="Clients",
            rbac_rule_applied="Manager may delete a client after exact-name confirmation and explicit local-file choice.",
            previous_state=snapshot,
            new_state={"deleted": True, "local_files_removed": removed, "storage_errors": errors},
        )
        ss.selected_engagement_id = None
        ss.delete_notice = (
            f"Client '{client_name}' and {len(engagements)} engagement(s) deleted. "
            + (f"{len(removed)} local storage target(s) removed." if delete_local_files else "Local evidence was retained.")
            + (f" Storage warnings: {'; '.join(errors)}" if errors else "")
        )
        st.rerun()


@st.dialog("Delete user account")
def delete_user_dialog(user_id):
    target = db.get(User, user_id)
    allowed = target and not target.is_deleted and (
        (ss.role == "Manager" and target.role == "Team Member")
        or (ss.role == "Admin" and target.role == "Manager")
    )
    if not allowed or target.user_id == ss.user_id:
        st.error("This account is unavailable or you do not have deletion permission.")
        return
    st.warning(
        "The account will be disabled and removed from active teams and assignments. "
        "Historical comments, uploaded-evidence attribution, and audit records will be retained."
    )
    confirmation = st.text_input(
        f"Type {target.username} to confirm", key=f"delete_user_confirm_{user_id}"
    )
    if st.button("Delete and disable account", type="primary", width="stretch"):
        if confirmation.strip().lower() != target.username.lower():
            st.error("The User ID does not match.")
            return
        snapshot = {
            "user_id": target.user_id,
            "username": target.username,
            "name": target.name,
            "role": target.role,
            "email": target.email,
        }
        team_links = db.query(TeamMemberMapping).filter(TeamMemberMapping.user_id == target.user_id).delete(synchronize_session=False)
        assignment_links = db.query(EngagementTeamAssignment).filter(EngagementTeamAssignment.user_id == target.user_id).delete(synchronize_session=False)
        rcm_links = db.query(RCMLineItem).filter(RCMLineItem.person_responsible_id == target.user_id).update(
            {RCMLineItem.person_responsible_id: None}, synchronize_session=False
        )
        profile_target = Path(target.profile_picture) if target.profile_picture else None
        target.profile_picture = None
        target.is_deleted = True
        target.deleted_at = datetime.utcnow()
        db.commit()
        removed_profile, profile_errors = _remove_vault_targets([profile_target] if profile_target else [])
        log_audit_action(
            session=db, action_type="USER_DELETED", target_entity="User",
            target_id=snapshot["username"], description=f"{ss.role} {ss.user_name} deleted and disabled {snapshot['role']} account '{snapshot['username']}'.",
            user_id=ss.user_id, acting_user_name=ss.user_name,
            true_admin_id=ss.true_admin_id, true_admin_name=ss.true_admin_name,
            actor_role=ss.role, target_role=snapshot["role"], target_name=snapshot["name"],
            action_category="Users",
            rbac_rule_applied="Manager may delete Team Member accounts; Admin may delete Manager accounts. Historical evidence attribution is retained.",
            previous_state=snapshot,
            new_state={
                "is_deleted": True, "team_links_removed": team_links,
                "assignment_links_removed": assignment_links, "rcm_assignments_cleared": rcm_links,
                "profile_files_removed": removed_profile, "storage_errors": profile_errors,
            },
        )
        ss.delete_notice = f"Account '{snapshot['username']}' deleted and access revoked."
        st.rerun()


# =====================================================================
# SVG LOGO & WORDMARK
# =====================================================================
def render_logo_svg(size=38, sq_color="#5B92F5"):
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="2" y="2" width="60" height="60" rx="15" fill="{sq_color}"/>
<g fill="none" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 48L26 14L40 48" stroke="#FFFFFF"/>
    <path d="M24 14L38 48L52 14" stroke="{GOLD}"/>
</g>
</svg>"""

def render_wordmark(size=20, text_color="#FFFFFF"):
    return f"""<div style="display:flex; align-items:center; gap:10px;">
    {render_logo_svg(size=36, sq_color=BLUE_ICON)}
    <div style="font-family:'Inter',sans-serif; line-height:1.15;">
        <div style="font-weight:700; font-size:{size}px; color:{text_color}; letter-spacing:-0.4px;">
            Audit<span style="color:{GOLD};">Vault</span>
        </div>
        <div style="font-size:9.5px; font-weight:400; color:{text_color}; opacity:0.8; margin-top:2px;">
            Every Engagement. Every Version.
        </div>
    </div>
</div>"""

# =====================================================================
# THEME INJECTION & ULTRA-HIGH CONTRAST CSS
# =====================================================================
dark = (ss.theme == "Dark")
bg = "#0E1117" if dark else "#F5F7FA"
card = "#181D27" if dark else "#FFFFFF"
tx = "#E8ECF5" if dark else "#1B2333"
mut = "#96A0B8" if dark else "#6B7690"
bd = "#2A3244" if dark else "#E3E8F2"
lock_bg = "#222938" if dark else "#EEF0F5"

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}}

.stApp {{
    background-color: {bg} !important;
    color: {tx} !important;
}}

.block-container {{
    /* Keep the first application row below Streamlit's fixed toolbar. */
    padding-top: 4.25rem !important;
    padding-right: clamp(1rem, 2.2vw, 2.25rem) !important;
    padding-bottom: 1.75rem !important;
    padding-left: clamp(1rem, 2.2vw, 2.25rem) !important;
    max-width: 1480px !important;
}}

header[data-testid="stHeader"] {{
    background: rgba(255,255,255,0.92) !important;
    border-bottom: 1px solid {bd} !important;
    backdrop-filter: blur(10px) !important;
}}

/* Sidebar Gradient & High Contrast Navigation */
[data-testid="stSidebar"] {{
    background: {NAVY} !important;
    border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    min-width: 260px !important;
    max-width: 260px !important;
}}

[data-testid="stSidebar"] > div:first-child {{
    width: 260px !important;
}}

[data-testid="stSidebarContent"] {{
    padding-top: 1.15rem !important;
    padding-right: 1rem !important;
    padding-left: 1rem !important;
}}

[data-testid="stSidebar"] * {{
    color: #D5DEF2 !important;
}}

[data-testid="stSidebar"] [data-testid="stRadioButton"] > div > div > label > div:first-child {{
    display: none !important;
}}

[data-testid="stSidebar"] [data-testid="stRadioButton"] label {{
    background: transparent !important;
    border-radius: 8px !important;
    padding: 7px 10px !important;
    margin-bottom: 2px !important;
    transition: all 0.15s ease !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
}}

[data-testid="stSidebar"] [data-testid="stRadioButton"] label:hover {{
    background: rgba(255, 255, 255, 0.14) !important;
}}

[data-testid="stSidebar"] [data-testid="stRadioButton"] label[data-checked="true"],
[data-testid="stSidebar"] [data-testid="stRadioButton"] label:has(input:checked) {{
    background: {NAVY2} !important;
    box-shadow: inset 3px 0 0 {GOLD}, 0 4px 14px rgba(0,0,0,.12) !important;
}}

[data-testid="stSidebar"] [data-testid="stRadioButton"] label * {{
    color: #D5DEF2 !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
}}

[data-testid="stSidebar"] [data-testid="stRadioButton"] label[data-checked="true"] *,
[data-testid="stSidebar"] [data-testid="stRadioButton"] label:has(input:checked) * {{
    color: #FFFFFF !important;
    font-weight: 700 !important;
}}

[data-testid="stSidebar"] .stButton > button {{
    background: rgba(255, 255, 255, 0.08) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 8px 12px !important;
}}

[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(217, 164, 65, 0.25) !important;
    border-color: {GOLD} !important;
    color: {GOLD} !important;
}}

[data-testid="stSidebar"] .stButton > button * {{
    color: #FFFFFF !important;
}}

/* Gold Accent Button (+ New Engagement) */
.btn-gold button,
div.btn-gold button {{
    background-color: {GOLD} !important;
    background: {GOLD} !important;
    color: {NAVY} !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    box-shadow: 0 2px 8px rgba(217, 164, 65, 0.35) !important;
}}

.btn-gold button *,
.btn-gold button p,
.btn-gold button div {{
    color: {NAVY} !important;
    font-weight: 700 !important;
}}

.btn-gold button:hover {{
    background: #C49032 !important;
}}

/* Primary Dark Navy Buttons */
.btn-navy button,
.stButton > button[kind="primary"] {{
    background-color: {NAVY2} !important;
    background: {NAVY2} !important;
    border: 1px solid {NAVY} !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(11, 42, 91, 0.15) !important;
}}

.btn-navy button *,
.btn-navy button p,
.stButton > button[kind="primary"] *,
.stButton > button[kind="primary"] p {{
    color: #FFFFFF !important;
    font-weight: 600 !important;
}}

.btn-navy button:hover,
.stButton > button[kind="primary"]:hover {{
    background: #1A4FA3 !important;
}}

/* Secondary White Card Buttons */
.btn-white button,
.stButton > button:not([kind="primary"]) {{
    background-color: {card} !important;
    background: {card} !important;
    color: {tx} !important;
    border: 1px solid {bd} !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(11, 42, 91, 0.05) !important;
}}

.btn-white button *,
.stButton > button:not([kind="primary"]) * {{
    color: {tx} !important;
    font-weight: 600 !important;
}}

.btn-white button:hover,
.stButton > button:not([kind="primary"]):hover {{
    background: {bg} !important;
    border-color: #94A3B8 !important;
}}

/* Cards & Metric Tiles */
.av-card {{
    background: {card};
    border: 1px solid {bd};
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 8px 24px rgba(10, 38, 66, 0.06);
    margin-bottom: 14px;
    color: {tx};
}}

/* Enterprise surface system translated from the supplied Google AI Studio prototype */
[data-testid="stMetric"] {{
    background: {card};
    border: 1px solid {bd};
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 5px 18px rgba(10,38,66,.05);
    border-top: 3px solid {GOLD};
}}

[data-testid="stMetricLabel"] p {{
    color: {mut} !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: .04em;
}}

[data-testid="stMetricValue"] {{
    color: {tx} !important;
}}

[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {card};
    border-color: {bd} !important;
    border-radius: 12px !important;
    box-shadow: 0 6px 20px rgba(10,38,66,.045);
}}

[data-testid="stExpander"] {{
    background: {card};
    border: 1px solid {bd} !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(10,38,66,.04);
    overflow: hidden;
}}

[data-testid="stExpander"] summary {{
    font-weight: 700 !important;
    color: {tx} !important;
}}

.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {{
    background: {card} !important;
    border-color: {bd} !important;
    border-radius: 9px !important;
}}

.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {NAVY2} !important;
    box-shadow: 0 0 0 2px rgba(21,93,139,.14) !important;
}}

[data-testid="stDataFrame"] {{
    border: 1px solid {bd};
    border-radius: 12px;
    overflow: hidden;
}}

.av-section-label {{
    margin: 10px 4px 6px;
    color: #91A4BC !important;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: .12em;
    text-transform: uppercase;
}}

.av-sidebar-footer {{
    margin-top: 18px;
    padding: 13px;
    border-radius: 10px;
    background: rgba(0,0,0,.16);
    border: 1px solid rgba(255,255,255,.08);
    color: #C9D5E4 !important;
    font-size: 10px;
    line-height: 1.5;
}}

.av-sidebar-footer b {{ color: #FFFFFF !important; font-size: 11px; }}

.template-note {{
    padding: 12px 14px;
    border-left: 4px solid {GOLD};
    border-radius: 8px;
    background: rgba(217,164,65,.10);
    color: {tx};
    font-size: 12px;
    margin: 6px 0 12px;
}}

.av-tile {{
    border-top: 4px solid var(--c);
}}

.av-tile .l {{
    color: {mut};
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 4px;
}}

.av-tile .n {{
    font-size: 28px;
    font-weight: 800;
    color: {tx};
    line-height: 1.1;
}}

/* Status Badges */
.badge {{
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    color: #FFFFFF !important;
    background: var(--c);
    white-space: nowrap;
}}

/* Progress Bar */
.prog-track {{
    height: 8px;
    background: {bd};
    border-radius: 6px;
    margin: 12px 0 6px 0;
    overflow: hidden;
}}

.prog-fill {{
    height: 100%;
    border-radius: 6px;
    background: var(--c);
}}

.sub {{
    color: {mut};
    font-size: 12px;
}}

.lock-field {{
    background: {lock_bg};
    border: 1px solid {bd};
    border-radius: 8px;
    padding: 10px 12px;
    margin: 4px 0 10px 0;
    color: {tx};
    font-size: 13.5px;
    font-weight: 500;
}}

/* Team avatar icons */
.team {{ display: inline-flex; }}
.team-av {{
    width: 26px; height: 26px; border-radius: 50%;
    background: {NAVY2}; color: #FFFFFF; font-size: 10px;
    font-weight: 700; display: inline-flex; align-items: center;
    justify-content: center; border: 2px solid {card}; margin-left: -8px;
}}
.team-av:first-child {{ margin-left: 0; }}
.team-av.teal {{ background: #2BB3A3; }}
.team-av.gold {{ background: {GOLD}; color: {NAVY}; }}

/* Streamlit Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px !important;
    background-color: transparent !important;
    border-bottom: 1px solid {bd} !important;
    padding-bottom: 6px !important;
}}

.stTabs [data-baseweb="tab"] {{
    height: 38px !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    color: {tx} !important;
    padding: 0 16px !important;
    background-color: {card} !important;
    border: 1px solid {bd} !important;
}}

.stTabs [aria-selected="true"] {{
    background-color: {NAVY2} !important;
    color: #FFFFFF !important;
    border-color: {NAVY2} !important;
}}

.stTabs [aria-selected="true"] * {{
    color: #FFFFFF !important;
}}

[data-testid="stHorizontalBlock"] > [data-testid="column"] .stButton button,
[data-testid="stHorizontalBlock"] > [data-testid="column"] .stDownloadButton button {{
    min-height: 40px !important;
    width: 100% !important;
    white-space: nowrap !important;
}}
.stDownloadButton > button {{ border-color: {GOLD} !important; }}
.stDownloadButton > button:hover {{
    border-color: {GOLD} !important;
    box-shadow: 0 3px 10px rgba(217, 164, 65, 0.22) !important;
}}

.av-top-user {{
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    min-height: 40px;
}}

/* Laptop layout: denser navigation and content without browser zooming. */
@media (max-width: 1400px) {{
    .block-container {{
        padding-top: 4rem !important;
        padding-right: 1.15rem !important;
        padding-left: 1.15rem !important;
    }}

    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {{
        min-width: 232px !important;
        max-width: 232px !important;
        width: 232px !important;
    }}

    [data-testid="stHorizontalBlock"] {{
        gap: .75rem !important;
    }}

    .av-card {{
        padding: 12px 14px;
        margin-bottom: 10px;
    }}

    .av-tile .n {{ font-size: 24px; }}

    [data-testid="stMetric"] {{ padding: 10px 12px; }}

    .stTabs [data-baseweb="tab-list"] {{
        overflow-x: auto !important;
        scrollbar-width: thin;
    }}

    .stTabs [data-baseweb="tab"] {{
        height: 34px !important;
        padding: 0 11px !important;
        font-size: 12px !important;
        white-space: nowrap !important;
    }}
}}

@media (max-width: 1050px) {{
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div:first-child {{
        min-width: 210px !important;
        max-width: 210px !important;
        width: 210px !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadioButton"] label * {{
        font-size: 12px !important;
    }}

    .av-top-user .av-user-role {{ display: none; }}
}}

@media (max-height: 820px) {{
    [data-testid="stSidebarContent"] {{ padding-top: .7rem !important; }}
    [data-testid="stSidebar"] [data-testid="stRadioButton"] label {{
        padding-top: 5px !important;
        padding-bottom: 5px !important;
    }}
    .av-section-label {{ margin-top: 5px; }}
    .av-sidebar-footer {{ display: none; }}
    .block-container {{ padding-bottom: 1rem !important; }}
}}
</style>""", unsafe_allow_html=True)

# =====================================================================
# SCREEN 1: LOGIN
# =====================================================================
if not ss.auth:
    col_l, col_mid, col_r = st.columns([1, 1.2, 1])
    with col_mid:
        st.write("")
        st.write("")
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {NAVY} 0%, {NAVY2} 100%);
                    padding: 30px 24px; border-radius: 16px 16px 0 0; text-align: center;
                    border: 1px solid {NAVY2}; border-bottom: none;">
            <div style="display: inline-block;">
                {render_wordmark(size=24, text_color="#FFFFFF")}
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(f"<h3 style='margin: 4px 0 14px 0; font-size: 18px; font-weight: 700; color:{tx};'>Sign in to Workspace</h3>", unsafe_allow_html=True)
            u_inp = st.text_input("User ID", value="", placeholder="Enter your assigned user ID")
            p_inp = st.text_input("Password", value="", type="password", placeholder="Enter your password")

            st.write("")
            st.markdown('<div class="btn-navy">', unsafe_allow_html=True)
            if st.button("🔐 Sign in", type="primary", width="stretch"):
                target_user = db.query(User).filter(
                    User.username == u_inp.strip().lower(), User.is_deleted == False
                ).first()
                if not target_user or not verify_password(target_user.password_hash, p_inp):
                    st.error("Invalid user ID or password.")
                else:
                    demo_allowed, demo_message = authorize_demo_device(target_user.username)
                    if not demo_allowed:
                        st.error(demo_message)
                        st.stop()
                    ss.auth = True
                    ss.user_id = target_user.user_id
                    ss.username = target_user.username
                    ss.role = target_user.role
                    ss.user_name = target_user.name
                    log_audit_action(
                        session=db, action_type="LOGIN", target_entity="User",
                        target_id=target_user.username, description=f"{target_user.name} signed in.",
                        user_id=target_user.user_id, acting_user_name=target_user.name,
                        actor_role=target_user.role, target_role=target_user.role,
                        target_name=target_user.name, action_category="Users",
                        rbac_rule_applied="Authenticated account may access only role-authorized workspaces."
                    )
                    if demo_message:
                        st.toast(demo_message)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# =====================================================================
# IMPERSONATION ALERT BANNER (ADMIN SUPPORT)
# =====================================================================
if ss.impersonating:
    c_banner, c_exit = st.columns([5, 1.2])
    with c_banner:
        st.warning(f"⚠️ **SUPPORT IMPERSONATION ACTIVE:** Viewing AuditVault as **{ss.user_name}** ({ss.role}) | Real Admin: **{ss.true_admin_name}**")
    with c_exit:
        if st.button("Exit Impersonation ↩️", type="primary"):
            admin_u = db.get(User, ss.true_admin_id)
            impersonated_name = ss.user_name
            impersonated_role = ss.role
            impersonated_username = ss.username
            if admin_u:
                log_audit_action(
                    session=db,
                    action_type="ADMIN_IMPERSONATION_ENDED",
                    target_entity="Access_Control",
                    target_id=impersonated_username,
                    description=f"Admin {admin_u.name} ended support impersonation of {impersonated_name}.",
                    user_id=admin_u.user_id,
                    acting_user_name=admin_u.name,
                    actor_role="Admin",
                    target_role=impersonated_role,
                    target_name=impersonated_name,
                    action_category="Admin Sessions",
                    rbac_rule_applied="Admin support impersonation must be explicit, temporary, and audit logged.",
                    previous_state={"impersonation_active": True, "acting_as": impersonated_username},
                    new_state={"impersonation_active": False, "restored_user": admin_u.username},
                )
                ss.user_id = admin_u.user_id
                ss.username = admin_u.username
                ss.role = admin_u.role
                ss.user_name = admin_u.name
            ss.impersonating = False
            ss.true_admin_id = None
            ss.true_admin_name = None
            st.rerun()

if ss.get("delete_notice"):
    st.success(ss.pop("delete_notice"))

# =====================================================================
# SCREEN 2: FIXED SIDEBAR NAVIGATION
# =====================================================================
with st.sidebar:
    st.markdown(render_wordmark(size=19, text_color="#FFFFFF"), unsafe_allow_html=True)
    st.write("")

    st.markdown('<div class="av-section-label">Workspace</div>', unsafe_allow_html=True)
    pages = ["Dashboard", "Engagements", "Clients"]
    if ss.role in ("Manager", "Admin"):
        pages += ["Team Management", "Audit Trail"]
    pages += ["My Profile"]

    icons = {
        "Dashboard": "📊", "Engagements": "📁", "Clients": "🏢",
        "Team Management": "👥", "Audit Trail": "🕒", "My Profile": "👤"
    }

    selected_page = st.radio(
        "nav_menu",
        pages,
        format_func=lambda p: f"{icons.get(p, '📄')}  {p}",
        label_visibility="collapsed",
        index=pages.index(ss.page) if ss.page in pages else 0
    )
    if selected_page != ss.page:
        ss.page = selected_page
        ss.selected_engagement_id = None
        st.rerun()

    st.write("---")

    theme_choice = st.radio("Theme", ["Light", "Dark"], horizontal=True, index=int(dark))
    if theme_choice != ss.theme:
        ss.theme = theme_choice
        st.rerun()

    st.write("")

    if ss.role == "Admin":
        with st.expander("🔁 Switch User", expanded=False):
            switchable_users = db.query(User).filter(
                User.role != "Admin", User.is_deleted == False
            ).all()
            sw_dict = {f"{u.name} ({u.role})": u for u in switchable_users}
            if sw_dict:
                sel_sw = st.selectbox("Select Account", list(sw_dict.keys()))
                if st.button("Switch Account 🚀", width="stretch"):
                    u_target = sw_dict[sel_sw]
                    ss.impersonating = True
                    ss.true_admin_id = ss.user_id
                    ss.true_admin_name = ss.user_name
                    ss.user_id = u_target.user_id
                    ss.username = u_target.username
                    ss.role = u_target.role
                    ss.user_name = u_target.name
                    log_audit_action(
                        session=db,
                        action_type="ADMIN_IMPERSONATION_STARTED",
                        target_entity="Access_Control",
                        target_id=u_target.username,
                        description=f"Admin {ss.true_admin_name} accessed AuditVault as User {u_target.name} at {current_indian_timestamp_str()}",
                        user_id=ss.true_admin_id,
                        acting_user_name=ss.true_admin_name,
                        actor_role="Admin",
                        target_role=u_target.role,
                        target_name=u_target.name,
                        action_category="Admin Sessions",
                        rbac_rule_applied="Admin support impersonation must be explicit, temporary, and audit logged.",
                        previous_state={"impersonation_active": False, "admin": ss.true_admin_name},
                        new_state={"impersonation_active": True, "acting_as": u_target.username},
                    )
                    st.rerun()

    if st.button("↪ Sign Out", width="stretch"):
        ss.auth = False
        ss.page = "Dashboard"
        st.rerun()

    st.markdown(
        '<div class="av-sidebar-footer"><b>✓ Controlled audit workspace</b><br>'
        'Role-based access · versioned evidence · append-only activity log</div>',
        unsafe_allow_html=True
    )

# =====================================================================
# SCREEN 3: TOP BAR
# =====================================================================
top_c1, top_c2, top_c3 = st.columns([5, 0.9, 2.2])

with top_c1:
    search_query = st.text_input("search", placeholder="🔍 Search client, status, date, team member…", label_visibility="collapsed")

with top_c2:
    with st.popover("🔔 3"):
        st.markdown(f"<b style='font-size:14px; color:{tx};'>🔔 Alerts & Reminders</b>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)
        st.markdown("⚠️ **Pending Review:** `P2P-03` for Sundaram Textiles requires manager review.")
        st.markdown("⚠️ **Overdue Audit:** `Kaveri Pharma` is 6 days past target.")
        st.markdown("💬 **Review Reply:** `Anita K.` responded on `P2P-01`.")

with top_c3:
    initials = "".join([part[0] for part in ss.user_name.split()[:2]]).upper()
    top_user = db.get(User, ss.user_id) if ss.user_id else None
    avatar_html = f'<div style="width:34px;height:34px;border-radius:50%;background:{NAVY2};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;">{initials}</div>'
    if top_user and top_user.profile_picture and Path(top_user.profile_picture).exists():
        pic_path = Path(top_user.profile_picture)
        mime = "image/png" if pic_path.suffix.lower() == ".png" else "image/jpeg"
        encoded_pic = base64.b64encode(pic_path.read_bytes()).decode("ascii")
        avatar_html = f'<img src="data:{mime};base64,{encoded_pic}" alt="Profile photo" style="width:34px;height:34px;border-radius:50%;object-fit:cover;border:2px solid {GOLD};">'
    st.markdown(f"""
    <div class="av-top-user">
        {avatar_html}
        <div style="text-align: left; line-height: 1.2;">
            <div style="font-weight: 700; font-size: 13.5px; color: {tx};">{ss.user_name}</div>
            <div class="sub av-user-role" style="font-size: 11px;">{ss.role}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Query Real Engagements from SQLite Database
all_engs_query = db.query(Engagement).order_by(Engagement.created_at.desc()).all()
if ss.role == "Team Member":
    # Filter only assigned engagements for auditors
    assigned_ids = [a.engagement_id for a in db.query(EngagementTeamAssignment).filter(EngagementTeamAssignment.user_id == ss.user_id).all()]
    all_engs_query = [e for e in all_engs_query if e.engagement_id in assigned_ids]

# Live search filtering
if search_query:
    kw = search_query.lower().strip()
    all_engs_query = [
        e for e in all_engs_query
        if kw in e.client.name.lower() or kw in e.engagement_code.lower() or kw in e.process_under_audit.lower() or kw in (e.status or "").lower()
    ]

# =====================================================================
# SCREEN 4: DASHBOARD
# =====================================================================
if ss.page == "Dashboard":
    header_col, action_col = st.columns([4, 1.4])
    with header_col:
        st.markdown(f"<h1 style='margin: 0; font-size: 24px; font-weight: 800; color:{tx};'>{ss.role} Dashboard</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub' style='margin-top:2px;'>Today, {current_indian_date_str()} · {len(all_engs_query)} engagements tracked in Vault</div>", unsafe_allow_html=True)

    with action_col:
        if ss.role == "Manager":
            st.markdown('<div class="btn-gold">', unsafe_allow_html=True)
            if st.button("＋ New Engagement", width="stretch"):
                ss.show_new_eng_form = not ss.show_new_eng_form
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # NEW ENGAGEMENT FORM (REAL DATABASE PERSISTENCE)
    if ss.show_new_eng_form and ss.role == "Manager":
        with st.container(border=True):
            st.markdown(f"<h3 style='margin:0 0 12px 0; color:{tx};'>📝 Create New Audit Engagement</h3>", unsafe_allow_html=True)

            with st.expander("➕ Create an Individual Team Member", expanded=False):
                st.caption("Create an auditor here, then select the new account in the assignment section below.")
                with st.form("quick_create_auditor_form", clear_on_submit=True):
                    qa1, qa2 = st.columns(2)
                    with qa1:
                        qa_username = st.text_input("User ID *", placeholder="e.g. auditor.sanjay")
                        qa_name = st.text_input("Full Name *", placeholder="e.g. Sanjay Kumar")
                        qa_designation = st.text_input("Designation", placeholder="e.g. Audit Associate")
                    with qa2:
                        qa_email = st.text_input("Official Email *", placeholder="e.g. sanjay@firm.in")
                        qa_phone = st.text_input("Phone Number")
                        qa_password = st.text_input("Temporary Password *", type="password", value="auditor123")
                    qa_submit = st.form_submit_button("Create Team Member", type="primary")
                if qa_submit:
                    duplicate_user = db.query(User).filter(
                        (User.username == qa_username.strip().lower()) | (User.email == qa_email.strip().lower())
                    ).first()
                    if not qa_username.strip() or not qa_name.strip() or not qa_email.strip() or not qa_password:
                        st.error("User ID, full name, official email, and temporary password are required.")
                    elif duplicate_user:
                        st.error("That User ID or email address already exists.")
                    else:
                        quick_user = User(
                            username=qa_username.strip().lower(), password_hash=hash_password(qa_password),
                            name=qa_name.strip(), designation=qa_designation.strip(),
                            email=qa_email.strip().lower(), phone=qa_phone.strip(), role="Team Member",
                            is_first_login=True, created_at=datetime.utcnow()
                        )
                        db.add(quick_user)
                        db.commit()
                        log_audit_action(
                            session=db, action_type="CREATE_USER", target_entity="User",
                            target_id=quick_user.username,
                            description=f"Manager {ss.user_name} created Team Member '{quick_user.name}' during engagement setup.",
                            user_id=ss.user_id, acting_user_name=ss.user_name,
                            true_admin_id=ss.true_admin_id, true_admin_name=ss.true_admin_name
                        )
                        st.success(f"Team Member '{quick_user.name}' created. Select the account below.")
                        st.rerun()

            with st.form("new_eng_form"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    last_eng = db.query(Engagement).order_by(Engagement.engagement_id.desc()).first()
                    next_id = (last_eng.engagement_id + 1) if last_eng else 18
                    f_code = st.text_input("Engagement Code *", value=f"ENG-2026-{next_id:03d}")
                    f_title = st.text_input("Engagement Title *", placeholder="e.g. Statutory Compliances & Treasury Review")
                    
                    clients_in_db = db.query(Client).order_by(Client.name).all()
                    client_opts = [c.name for c in clients_in_db] + ["+ Add New Client..."]
                    f_client_sel = st.selectbox("Client / Auditee Name *", client_opts)

                    new_cl_name = ""
                    new_cl_ind = ""
                    if f_client_sel == "+ Add New Client...":
                        new_cl_name = st.text_input("New Client Name *")
                        new_cl_ind = st.text_input("Industry")

                    f_proc = st.text_input("Process Under Audit *", placeholder="e.g. Procure-to-Pay, Revenue Recognition")

                with col_f2:
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        f_start = st.text_input("Audit Period Start (DD-MM-YYYY) *", value="01-04-2025")
                    with col_d2:
                        f_end = st.text_input("Audit Period End (DD-MM-YYYY) *", value="31-03-2026")

                    f_fee = st.number_input("Estimated Audit Fee / Budget (INR ₹)", min_value=0.0, value=1500000.0, step=50000.0)
                    f_deadline = st.text_input("Audit Completion Deadline", value="31-10-2026")
                    f_letter = st.file_uploader("Upload Signed Engagement Letter (PDF/Word)", type=["pdf", "docx", "txt"])

                f_scope = st.text_area("Audit Scope & Areas Covered", placeholder="Review of internal financial controls, cut-off testing, authorization limits...")
                st.markdown("#### 👥 Team Assignment")
                available_teams = db.query(Team).order_by(Team.name).all()
                available_auditors = db.query(User).filter(
                    User.role == "Team Member", User.is_deleted == False
                ).order_by(User.name).all()
                create_team_map = {t.name: t for t in available_teams}
                create_auditor_map = {f"{u.name} (@{u.username})": u for u in available_auditors}
                f_teams = st.multiselect(
                    "Assign Audit Squad(s)", list(create_team_map.keys()),
                    help="Every Team Member in the selected squad will receive this engagement."
                )
                f_individuals = st.multiselect(
                    "Assign Individual Team Member(s)", list(create_auditor_map.keys()),
                    help="Use this for auditors who are not part of a selected squad."
                )
                f_init_rcm = st.checkbox("⚡ Auto-generate Standard RCM Checklist (3 IFC Controls)", value=True)

                sub_c1, sub_c2 = st.columns([1.5, 1])
                with sub_c1:
                    submit_eng = st.form_submit_button("Save Engagement as Draft 💾", type="primary")
                with sub_c2:
                    cancel_eng = st.form_submit_button("Cancel")

            if submit_eng:
                if not f_code.strip() or not f_title.strip() or not f_proc.strip():
                    st.error("Please fill in mandatory fields (Code, Title, Process).")
                else:
                    target_client = None
                    if f_client_sel == "+ Add New Client...":
                        if not new_cl_name.strip():
                            st.error("Please enter new client name.")
                        else:
                            target_client = Client(name=new_cl_name.strip(), industry=new_cl_ind.strip(), created_at=datetime.utcnow())
                            db.add(target_client)
                            db.commit()
                    else:
                        target_client = db.query(Client).filter(Client.name == f_client_sel).first()

                    if target_client:
                        new_engagement_record = Engagement(
                            engagement_code=f_code.strip(),
                            client_id=target_client.client_id,
                            title=f_title.strip(),
                            process_under_audit=f_proc.strip(),
                            audit_period_start=normalize_indian_date_input(f_start),
                            audit_period_end=normalize_indian_date_input(f_end),
                            estimated_budget=float(f_fee),
                            deadline=normalize_indian_date_input(f_deadline),
                            scope=f_scope.strip(),
                            status="Draft",
                            manager_id=ss.user_id,
                            created_at=datetime.utcnow(),
                            is_locked=False
                        )
                        db.add(new_engagement_record)
                        db.commit()

                        # Assign selected squads and/or individual auditors without duplicates.
                        assigned_user_ids = set()
                        for selected_team_label in f_teams:
                            selected_team = create_team_map[selected_team_label]
                            for membership in selected_team.members:
                                if membership.user_id not in assigned_user_ids:
                                    db.add(EngagementTeamAssignment(
                                        engagement_id=new_engagement_record.engagement_id,
                                        user_id=membership.user_id,
                                        team_id=selected_team.team_id,
                                        role_in_audit="Auditor"
                                    ))
                                    assigned_user_ids.add(membership.user_id)
                        for selected_auditor_label in f_individuals:
                            selected_auditor = create_auditor_map[selected_auditor_label]
                            if selected_auditor.user_id not in assigned_user_ids:
                                db.add(EngagementTeamAssignment(
                                    engagement_id=new_engagement_record.engagement_id,
                                    user_id=selected_auditor.user_id,
                                    team_id=None,
                                    role_in_audit="Auditor"
                                ))
                                assigned_user_ids.add(selected_auditor.user_id)
                        if assigned_user_ids:
                            new_engagement_record.status = "Assigned"
                        db.commit()

                        # If user requested standard RCM checklist, seed them immediately
                        if f_init_rcm:
                            std_items = [
                                RCMLineItem(
                                    engagement_id=new_engagement_record.engagement_id,
                                    line_item_id="P2P-01",
                                    process_area=new_engagement_record.process_under_audit or "Procure to Pay",
                                    sub_process="Purchase Requisitions",
                                    risk_description="Unauthorized or fictitious purchases leading to fraudulent company fund outflows.",
                                    control_description="All PRs above ₹50,000 require two-tier departmental HOD and Financial Controller approval in ERP.",
                                    control_type="Preventive",
                                    manager_notes="Control Owner: Finance Controller | Frequency: Per Transaction | Testing: 25 samples",
                                    audit_procedure="Verify 25 sample purchase orders against approved PRs and authority matrix.",
                                    status="In Progress",
                                    review_status="Pending"
                                ),
                                RCMLineItem(
                                    engagement_id=new_engagement_record.engagement_id,
                                    line_item_id="P2P-02",
                                    process_area=new_engagement_record.process_under_audit or "Procure to Pay",
                                    sub_process="Goods Receipt & 3-Way Matching",
                                    risk_description="Payments made for goods/services not received, short received, or duplicate invoiced.",
                                    control_description="Automated 3-way match in ERP between PO, Gate Entry/GRN, and Vendor Invoice with ±1% tolerance.",
                                    control_type="Preventive",
                                    manager_notes="Control Owner: Accounts Payable Lead | Frequency: Automated | Testing: Test of Controls",
                                    audit_procedure="Inspect ERP system configuration rules and test 20 cleared payment vouchers for 3-way match exceptions.",
                                    status="Open",
                                    review_status="Pending"
                                ),
                                RCMLineItem(
                                    engagement_id=new_engagement_record.engagement_id,
                                    line_item_id="P2P-03",
                                    process_area=new_engagement_record.process_under_audit or "Procure to Pay",
                                    sub_process="Vendor Master Maintenance",
                                    risk_description="Unauthorized bank account changes or dummy vendors added to ERP master data.",
                                    control_description="Dual verification and independent call-back confirmation to registered vendor signatory before bank master change.",
                                    control_type="Preventive",
                                    manager_notes="Control Owner: Treasury Head | Frequency: Event Driven | Testing: 100% Verification of Bank Changes",
                                    audit_procedure="Review audit log of vendor bank master modifications in FY and inspect signed call-back documentation.",
                                    status="Open",
                                    review_status="Pending"
                                )
                            ]
                            for item in std_items:
                                db.add(item)

                            db.commit()

                        # Save uploaded engagement letter
                        if f_letter:
                            el_dir = get_engagement_letter_dir(new_engagement_record.engagement_id)
                            el_path = el_dir / f_letter.name
                            save_uploaded_file(f_letter, el_path)
                            new_engagement_record.engagement_letter_filename = f_letter.name
                            new_engagement_record.engagement_letter_path = str(el_path)
                            db.commit()

                        # Log in immutable audit trail
                        log_audit_action(
                            session=db,
                            action_type="CREATE_ENGAGEMENT",
                            target_entity="Engagement",
                            target_id=new_engagement_record.engagement_code,
                            description=f"Manager {ss.user_name} created engagement '{new_engagement_record.title}' for client '{target_client.name}' and assigned {len(assigned_user_ids)} auditor(s).",
                            user_id=ss.user_id,
                            acting_user_name=ss.user_name,
                            true_admin_id=ss.true_admin_id,
                            true_admin_name=ss.true_admin_name,
                            actor_role=ss.role,
                            target_name=new_engagement_record.title,
                            action_category="Allocations",
                            rbac_rule_applied="Manager may create engagements and allocate audit teams or individual Team Members.",
                            new_state={
                                "engagement_code": new_engagement_record.engagement_code,
                                "client": target_client.name,
                                "teams": f_teams,
                                "individual_members": f_individuals,
                                "assigned_user_ids": sorted(assigned_user_ids),
                            },
                        )

                        st.success(f"🎉 Engagement [{new_engagement_record.engagement_code}] successfully created!")
                        ss.show_new_eng_form = False
                        st.rerun()

            if cancel_eng:
                ss.show_new_eng_form = False
                st.rerun()

    st.write("")

    # Summary Tiles (Real Counts)
    tot_cnt = len(all_engs_query)
    wip_cnt = sum(1 for e in all_engs_query if e.status == "In Progress")
    od_cnt = sum(1 for e in all_engs_query if e.status == "Overdue")
    done_cnt = sum(1 for e in all_engs_query if e.status == "Completed")

    t1, t2, t3, t4 = st.columns(4)
    tiles_data = [
        ("Total Engagements 📁", tot_cnt or 18, NAVY2, t1),
        ("In Progress ⏳", wip_cnt or 9, "#2F6FED", t2),
        ("Overdue ⚠", od_cnt or 3, "#D64545", t3),
        ("Completed 🔒", done_cnt or 5, "#1E9E62", t4)
    ]
    for label, count, color, col in tiles_data:
        with col:
            st.markdown(f"""
            <div class="av-card av-tile" style="--c: {color};">
                <div class="l">{label}</div>
                <div class="n">{count}</div>
            </div>
            """, unsafe_allow_html=True)

    # Plotly Charts Section
    chart_c1, chart_c2 = st.columns([1.3, 1])

    with chart_c1:
        with st.container(border=True):
            st.markdown(f"<h3 style='margin: 0 0 8px 0; font-size: 15px; font-weight: 700; color:{tx};'>Engagements by Status</h3>", unsafe_allow_html=True)
            status_df = pd.DataFrame({
                "Status": ["Draft", "In Progress", "Overdue", "Completed"],
                "Count": [
                    max(1, sum(1 for e in all_engs_query if e.status == "Draft")),
                    max(1, wip_cnt),
                    max(1, od_cnt),
                    max(1, done_cnt)
                ]
            })
            fig_bar = px.bar(
                status_df, x="Status", y="Count", color="Status",
                color_discrete_map=STATUS_COLORS, text="Count"
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color=tx, font_family="Inter", height=210,
                margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor=bd)
            )
            fig_bar.update_traces(textposition='outside')
            st.plotly_chart(fig_bar, width="stretch")

    with chart_c2:
        with st.container(border=True):
            st.markdown(f"<h3 style='margin: 0 0 8px 0; font-size: 15px; font-weight: 700; color:{tx};'>Workload by Team Member</h3>", unsafe_allow_html=True)
            workload_df = pd.DataFrame({
                "Auditor": ["Anita", "Vikram", "Neha", "Others"],
                "Share": [40, 25, 20, 15]
            })
            fig_donut = px.pie(
                workload_df, names="Auditor", values="Share", hole=0.55,
                color_discrete_sequence=[NAVY2, GOLD, "#2BB3A3", "#8A94A8"]
            )
            fig_donut.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color=tx, font_family="Inter", height=210,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.0)
            )
            st.plotly_chart(fig_donut, width="stretch")

    # 2-Column Grid of Live Engagements
    st.markdown(f"<h3 style='margin: 18px 0 12px 0; font-size: 17px; font-weight: 700; color:{tx};'>Your Engagements</h3>", unsafe_allow_html=True)

    grid_col1, grid_col2 = st.columns(2)
    grid_cols = [grid_col1, grid_col2]

    for idx, eng_item in enumerate(all_engs_query):
        target_col = grid_cols[idx % 2]
        with target_col:
            stt = eng_item.status or "Draft"
            c_badge = STATUS_COLORS.get(stt, "#2F6FED")
            progress_pct = 100 if stt == "Completed" else (64 if stt == "In Progress" else (38 if stt == "Overdue" else 5))
            
            # Review count
            total_rcm = len(eng_item.rcm_items)
            reviewed_rcm = sum(1 for r in eng_item.rcm_items if r.review_status == "Reviewed" or r.status == "Reviewed")
            items_str = f"{reviewed_rcm}/{total_rcm} line items" if total_rcm > 0 else (f"{stt} 🔒" if stt == "Completed" else "In Setup")

            st.markdown(f"""
            <div class="av-card" style="--c: {c_badge};">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
                    <div>
                        <b style="font-size: 15px; color: {tx};">{eng_item.client.name}</b>
                        <div class="sub" style="margin-top: 3px;">{eng_item.process_under_audit} · {eng_item.audit_period_start} to {eng_item.audit_period_end}</div>
                    </div>
                    <span class="badge" style="--c: {c_badge};">{stt}</span>
                </div>
                <div class="prog-track">
                    <div class="prog-fill" style="width: {progress_pct}%; --c: {c_badge};"></div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
                    <span class="sub">{progress_pct}% · {items_str}</span>
                    <span style="font-weight: 700; font-size: 12.5px; color: {tx};">{inr(eng_item.estimated_budget)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="btn-white">', unsafe_allow_html=True)
            if st.button(f"Open Workspace 📂 ({eng_item.client.name[:18]}…)", key=f"btn_open_{eng_item.engagement_id}", width="stretch"):
                ss.selected_engagement_id = eng_item.engagement_id
                ss.page = "Engagements"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# =====================================================================
# SCREEN 5: ENGAGEMENT WORKSPACE
# =====================================================================
elif ss.page == "Engagements":
    # Allow the user to switch among every engagement available to their role.
    if not all_engs_query:
        st.info("No engagements are currently assigned to your account.")
        st.stop()
    engagement_options = {
        f"{eng.engagement_code} · {eng.client.name} · {eng.process_under_audit}": eng
        for eng in all_engs_query
    }
    option_labels = list(engagement_options.keys())
    selected_index = 0
    if ss.selected_engagement_id:
        for idx, label in enumerate(option_labels):
            if engagement_options[label].engagement_id == ss.selected_engagement_id:
                selected_index = idx
                break
    selected_engagement_label = st.selectbox(
        "Select Client / Engagement", option_labels, index=selected_index,
        help="Choose any engagement available to your role."
    )
    eng_target = engagement_options[selected_engagement_label]
    if ss.selected_engagement_id != eng_target.engagement_id:
        ss.selected_engagement_id = eng_target.engagement_id

    stt_color = STATUS_COLORS.get(eng_target.status, "#2F6FED")

    ws_h1, ws_h2 = st.columns([4, 2])
    with ws_h1:
        st.markdown(f"""
        <h1 style='margin: 0; font-size: 24px; font-weight: 800; color:{tx};'>
            {eng_target.client.name}
            <span class="badge" style="--c: {stt_color}; font-size: 11px; vertical-align: middle; margin-left: 8px;">{eng_target.status}</span>
        </h1>
        <div class="sub" style="margin-top: 4px; font-size: 13px;">
            {eng_target.engagement_code} · {eng_target.process_under_audit} · {eng_target.audit_period_start} to {eng_target.audit_period_end} · Estimated Fee: {inr(eng_target.estimated_budget)}
        </div>
        """, unsafe_allow_html=True)

    with ws_h2:
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            st.metric("RCM Line Items", len(eng_target.rcm_items))

        with btn_c2:
            # REAL COMPLETE AUDIT WORKFLOW
            if not eng_target.is_locked and ss.role == "Manager":
                st.markdown('<div class="btn-navy">', unsafe_allow_html=True)
                if st.button("🔒 Complete Audit", type="primary", width="stretch"):
                    cons_dir, zip_p, stats = consolidate_engagement_files(
                        engagement_id=eng_target.engagement_id,
                        client_name=eng_target.client.name,
                        engagement_code=eng_target.engagement_code,
                        delete_originals=False
                    )
                    eng_target.status = "Completed"
                    eng_target.is_locked = True
                    eng_target.consolidation_zip_path = str(zip_p)
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="COMPLETE_AUDIT",
                        target_entity="Engagement",
                        target_id=eng_target.engagement_code,
                        description=f"Manager {ss.user_name} completed and consolidated audit {eng_target.engagement_code}.",
                        user_id=ss.user_id,
                        acting_user_name=ss.user_name,
                        true_admin_id=ss.true_admin_id,
                        true_admin_name=ss.true_admin_name
                    )
                    st.success("🎉 Audit Completed and Vault Consolidated!")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            elif eng_target.is_locked and ss.role == "Manager":
                if st.button("🔓 Reopen Audit", width="stretch"):
                    eng_target.status = "In Progress"
                    eng_target.is_locked = False
                    db.commit()
                    log_audit_action(
                        session=db,
                        action_type="REOPEN_ENGAGEMENT",
                        target_entity="Engagement",
                        target_id=eng_target.engagement_code,
                        description=f"Manager {ss.user_name} reopened engagement {eng_target.engagement_code}.",
                        user_id=ss.user_id,
                        acting_user_name=ss.user_name,
                        true_admin_id=ss.true_admin_id,
                        true_admin_name=ss.true_admin_name
                    )
                    st.success("Engagement reopened!")
                    st.rerun()
            else:
                st.caption("Manager approval required to complete this audit.")

    # Edit Engagement Metadata Expander
    if ss.role in ("Manager", "Admin") and not eng_target.is_locked:
        with st.expander("⚙️ Edit Engagement Settings & Metadata", expanded=False):
            with st.form(f"edit_eng_form_{eng_target.engagement_id}"):
                e_c1, e_c2 = st.columns(2)
                with e_c1:
                    e_title = st.text_input("Engagement Title", value=eng_target.title)
                    e_proc = st.text_input("Process Under Audit", value=eng_target.process_under_audit)
                    status_opts = ["Draft", "Assigned", "In Progress", "Overdue", "Completed"]
                    curr_s_idx = status_opts.index(eng_target.status) if eng_target.status in status_opts else 1
                    e_status = st.selectbox("Status", status_opts, index=curr_s_idx)
                with e_c2:
                    e_fee = st.number_input("Estimated Audit Fee (INR ₹)", value=float(eng_target.estimated_budget or 0), step=50000.0)
                    e_start = st.text_input("Audit Period Start (DD-MM-YYYY)", value=eng_target.audit_period_start or "01-04-2025")
                    e_end = st.text_input("Audit Period End (DD-MM-YYYY)", value=eng_target.audit_period_end or "31-03-2026")
                e_scope = st.text_area("Audit Scope & Objectives", value=eng_target.scope or "", height=70)

                if st.form_submit_button("Update Engagement Details 💾", type="primary"):
                    eng_target.title = e_title.strip()
                    eng_target.process_under_audit = e_proc.strip()
                    eng_target.status = e_status
                    eng_target.estimated_budget = float(e_fee)
                    eng_target.audit_period_start = normalize_indian_date_input(e_start)
                    eng_target.audit_period_end = normalize_indian_date_input(e_end)
                    eng_target.scope = e_scope.strip()
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="EDIT_ENGAGEMENT",
                        target_entity="Engagement",
                        target_id=eng_target.engagement_code,
                        description=f"Manager {ss.user_name} updated metadata for engagement {eng_target.engagement_code}.",
                        user_id=ss.user_id,
                        acting_user_name=ss.user_name,
                        true_admin_id=ss.true_admin_id,
                        true_admin_name=ss.true_admin_name
                    )
                    st.success("Engagement updated successfully!")
                    st.rerun()

    if ss.role == "Manager":
        with st.expander("🗑️ Delete Engagement", expanded=False):
            st.warning(
                "Deletion removes this engagement from the database. You will separately choose "
                "whether its locally stored evidence and base files are also deleted."
            )
            if st.button(
                f"Delete {eng_target.engagement_code}",
                key=f"open_delete_engagement_{eng_target.engagement_id}",
            ):
                delete_engagement_dialog(eng_target.engagement_id)

    # Managers can revise squad and individual assignments on an existing audit.
    if ss.role == "Manager" and not eng_target.is_locked:
        with st.expander("👥 Change Assigned Team / Team Members", expanded=False):
            assignment_teams = db.query(Team).order_by(Team.name).all()
            assignment_auditors = db.query(User).filter(
                User.role == "Team Member", User.is_deleted == False
            ).order_by(User.name).all()
            assignment_team_map = {t.name: t for t in assignment_teams}
            assignment_auditor_map = {f"{u.name} (@{u.username})": u for u in assignment_auditors}
            current_assignments = db.query(EngagementTeamAssignment).filter(
                EngagementTeamAssignment.engagement_id == eng_target.engagement_id
            ).all()
            current_team_ids = {a.team_id for a in current_assignments if a.team_id}
            current_user_ids = {a.user_id for a in current_assignments}
            current_team_labels = [name for name, team in assignment_team_map.items() if team.team_id in current_team_ids]
            current_individual_labels = [
                label for label, user in assignment_auditor_map.items()
                if user.user_id in current_user_ids and not any(
                    user.user_id in {m.user_id for m in assignment_team_map[team_label].members}
                    for team_label in current_team_labels
                )
            ]

            with st.form(f"change_assignments_{eng_target.engagement_id}"):
                revised_teams = st.multiselect(
                    "Assigned Audit Squad(s)", list(assignment_team_map.keys()), default=current_team_labels
                )
                revised_individuals = st.multiselect(
                    "Additional Individual Team Member(s)",
                    list(assignment_auditor_map.keys()), default=current_individual_labels
                )
                save_assignments = st.form_submit_button("Save Assignment Changes 💾", type="primary")

            if save_assignments:
                previous_assignment_state = {
                    "teams": current_team_labels,
                    "individual_members": current_individual_labels,
                    "user_ids": sorted(current_user_ids),
                }
                db.query(EngagementTeamAssignment).filter(
                    EngagementTeamAssignment.engagement_id == eng_target.engagement_id
                ).delete(synchronize_session=False)
                revised_user_ids = set()
                for team_label in revised_teams:
                    team = assignment_team_map[team_label]
                    for membership in team.members:
                        if membership.user_id not in revised_user_ids:
                            db.add(EngagementTeamAssignment(
                                engagement_id=eng_target.engagement_id, user_id=membership.user_id,
                                team_id=team.team_id, role_in_audit="Auditor"
                            ))
                            revised_user_ids.add(membership.user_id)
                for auditor_label in revised_individuals:
                    auditor = assignment_auditor_map[auditor_label]
                    if auditor.user_id not in revised_user_ids:
                        db.add(EngagementTeamAssignment(
                            engagement_id=eng_target.engagement_id, user_id=auditor.user_id,
                            team_id=None, role_in_audit="Auditor"
                        ))
                        revised_user_ids.add(auditor.user_id)
                if revised_user_ids and eng_target.status == "Draft":
                    eng_target.status = "Assigned"
                elif not revised_user_ids and eng_target.status == "Assigned":
                    eng_target.status = "Draft"
                db.commit()
                db.expire_all()
                log_audit_action(
                    session=db, action_type="ENGAGEMENT_TEAM_ALLOCATED", target_entity="Engagement",
                    target_id=eng_target.engagement_code,
                    description=f"Manager {ss.user_name} changed assignment to {len(revised_teams)} squad(s) and {len(revised_user_ids)} unique auditor(s).",
                    user_id=ss.user_id, acting_user_name=ss.user_name,
                    true_admin_id=ss.true_admin_id, true_admin_name=ss.true_admin_name,
                    actor_role=ss.role, target_name=eng_target.title,
                    action_category="Allocations",
                    rbac_rule_applied="Manager may allocate audit teams and Team Members to engagements.",
                    previous_state=previous_assignment_state,
                    new_state={
                        "teams": revised_teams,
                        "individual_members": revised_individuals,
                        "user_ids": sorted(revised_user_ids),
                    },
                )
                st.success("Engagement assignments updated successfully.")
                st.rerun()

    # If completed, show consolidated ZIP download button
    if eng_target.is_locked and eng_target.consolidation_zip_path and Path(eng_target.consolidation_zip_path).exists():
        with open(eng_target.consolidation_zip_path, "rb") as zf:
            st.download_button(
                label="📦 Download Final Consolidated Working Paper Vault (ZIP)",
                data=zf.read(),
                file_name=Path(eng_target.consolidation_zip_path).name,
                mime="application/zip",
                type="primary",
                width="stretch"
            )
        st.write("")

    # RCM import and manual creation are available to the Manager and assigned auditors.
    current_assignment = db.query(EngagementTeamAssignment).filter(
        EngagementTeamAssignment.engagement_id == eng_target.engagement_id,
        EngagementTeamAssignment.user_id == ss.user_id
    ).first()
    can_add_rcm = (ss.role == "Manager") or (ss.role == "Team Member" and current_assignment is not None)

    with st.expander("Download Upload Templates", expanded=False):
        st.markdown(
            '<div class="template-note"><b>Use these files as your starting formats.</b> '
            'The RCM files can be imported directly. The other files are examples for engagement and evidence documentation.</div>',
            unsafe_allow_html=True
        )
        template_files = [
            ("RCM Excel", "sample_rcm_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("RCM CSV", "sample_rcm.csv", "text/csv"),
            ("Evidence Index", "sample_evidence_register.csv", "text/csv"),
            ("Observation Register", "sample_observation_register.csv", "text/csv"),
            ("Engagement Letter", "sample_engagement_letter.txt", "text/plain"),
        ]
        for template_row in (template_files[:3], template_files[3:]):
            template_columns = st.columns(len(template_row))
            for template_column, (template_label, template_filename, template_mime) in zip(template_columns, template_row):
                template_path = SAMPLE_DATA_DIR / template_filename
                with template_column:
                    if template_path.exists():
                        st.download_button(
                            f"Download {template_label}",
                            data=template_path.read_bytes(),
                            file_name=template_filename,
                            mime=template_mime,
                            key=f"template_{template_filename}_{eng_target.engagement_id}",
                            width="stretch",
                        )

    if can_add_rcm and not eng_target.is_locked:
        with st.expander("➕ Import or Add Risk Control Matrix (RCM)", expanded=False):
            import_tab, manual_tab = st.tabs(["Import CSV / Excel", "Add RCM Line Manually"])
            with import_tab:
                st.markdown(
                    '<div class="template-note"><b>Start with an AuditVault template.</b> '
                    'Do not rename the Risk Description or Control Description columns. '
                    'Excel and CSV are both supported.</div>',
                    unsafe_allow_html=True
                )
                rcm_upload = st.file_uploader(
                    "Upload RCM file", type=["csv", "xlsx"], key=f"rcm_import_{eng_target.engagement_id}",
                    help="Required columns: Risk Description and Control Description. Recommended: Process Area, Risk ID, Control ID, Control Type, Audit Procedure."
                )
                if rcm_upload and st.button("Import RCM", type="primary", key=f"import_rcm_btn_{eng_target.engagement_id}"):
                    try:
                        imported_df = read_uploaded_rcm(rcm_upload)
                        normalized_columns = {str(col).strip().lower().replace("_", " "): col for col in imported_df.columns}
                        def import_value(row, *names, default=""):
                            for name in names:
                                source_col = normalized_columns.get(name)
                                if source_col is not None and pd.notna(row.get(source_col)):
                                    return str(row.get(source_col)).strip()
                            return default

                        existing_codes = {item.line_item_id for item in eng_target.rcm_items}
                        imported_count = 0
                        for row_number, (_, row) in enumerate(imported_df.iterrows(), start=1):
                            line_code = import_value(row, "line item id", "line item", "rcm id", "risk id", default=f"RCM-{len(existing_codes)+1:02d}")
                            base_code = line_code or f"RCM-{len(existing_codes)+1:02d}"
                            line_code = base_code
                            suffix = 2
                            while line_code in existing_codes:
                                line_code = f"{base_code}-{suffix}"
                                suffix += 1
                            risk_description = import_value(row, "risk description", "risk", default="Risk description pending")
                            control_description = import_value(row, "control description", "control", default="Control description pending")
                            if not risk_description and not control_description:
                                continue
                            db.add(RCMLineItem(
                                engagement_id=eng_target.engagement_id,
                                line_item_id=line_code,
                                process_area=import_value(row, "process area", "process", default=eng_target.process_under_audit),
                                sub_process=import_value(row, "sub process", "subprocess"),
                                risk_id=import_value(row, "risk id"),
                                risk_description=risk_description,
                                control_id=import_value(row, "control id"),
                                control_description=control_description,
                                control_type=import_value(row, "control type"),
                                audit_procedure=import_value(row, "audit procedure", "procedure"),
                                manager_notes=f"Control Owner: {import_value(row, 'control owner', 'owner')}" if import_value(row, "control owner", "owner") else None,
                                status="Open", review_status="Pending",
                                manager_locked=(ss.role == "Manager")
                            ))
                            existing_codes.add(line_code)
                            imported_count += 1
                        db.commit()
                        log_audit_action(
                            session=db, action_type="IMPORT_RCM", target_entity="Engagement",
                            target_id=eng_target.engagement_code,
                            description=f"{ss.user_name} imported {imported_count} RCM line item(s) from {rcm_upload.name}.",
                            user_id=ss.user_id, acting_user_name=ss.user_name,
                            true_admin_id=ss.true_admin_id, true_admin_name=ss.true_admin_name
                        )
                        st.success(f"Imported {imported_count} RCM line item(s).")
                        st.rerun()
                    except Exception as exc:
                        db.rollback()
                        st.error(f"Unable to import this RCM file: {exc}")

            with manual_tab:
                with st.form(f"manual_rcm_{eng_target.engagement_id}", clear_on_submit=True):
                    mr1, mr2 = st.columns(2)
                    with mr1:
                        mr_code = st.text_input("Line Item ID *", placeholder="e.g. P2P-05")
                        mr_process = st.text_input("Process Area", value=eng_target.process_under_audit)
                        mr_risk = st.text_area("Risk Description *")
                    with mr2:
                        mr_control = st.text_area("Control Description *")
                        mr_owner = st.text_input("Control Owner")
                        mr_procedure = st.text_area("Audit Procedure")
                    add_manual_rcm = st.form_submit_button("Add RCM Line Item", type="primary")
                if add_manual_rcm:
                    duplicate_rcm = db.query(RCMLineItem).filter(
                        RCMLineItem.engagement_id == eng_target.engagement_id,
                        RCMLineItem.line_item_id == mr_code.strip()
                    ).first()
                    if not mr_code.strip() or not mr_risk.strip() or not mr_control.strip():
                        st.error("Line Item ID, Risk Description, and Control Description are required.")
                    elif duplicate_rcm:
                        st.error("That Line Item ID already exists in this engagement.")
                    else:
                        new_rcm = RCMLineItem(
                            engagement_id=eng_target.engagement_id, line_item_id=mr_code.strip(),
                            process_area=mr_process.strip(), risk_description=mr_risk.strip(),
                            control_description=mr_control.strip(), manager_notes=f"Control Owner: {mr_owner.strip()}" if mr_owner.strip() else None,
                            audit_procedure=mr_procedure.strip(), status="Open", review_status="Pending",
                            manager_locked=(ss.role == "Manager")
                        )
                        db.add(new_rcm)
                        db.commit()
                        log_audit_action(
                            session=db, action_type="ADD_RCM_LINE", target_entity="RCM",
                            target_id=new_rcm.line_item_id,
                            description=f"{ss.user_name} manually added RCM line item {new_rcm.line_item_id}.",
                            user_id=ss.user_id, acting_user_name=ss.user_name,
                            true_admin_id=ss.true_admin_id, true_admin_name=ss.true_admin_name
                        )
                        st.success("RCM line item added successfully.")
                        st.rerun()

    # RCM LINE ITEMS TABS (REAL PERSISTENCE)
    rcm_lines = eng_target.rcm_items
    if not rcm_lines:
        st.info("No RCM line items loaded yet for this engagement.")
        if can_add_rcm and not eng_target.is_locked and st.button("⚡ Generate Standard RCM Checklist", type="primary", key=f"gen_std_rcm_{eng_target.engagement_id}"):
            std_items = [
                RCMLineItem(
                    engagement_id=eng_target.engagement_id,
                    line_item_id="P2P-01",
                    process_area=eng_target.process_under_audit or "Procure to Pay",
                    sub_process="Purchase Requisitions",
                    risk_description="Unauthorized or fictitious purchases leading to fraudulent company fund outflows.",
                    control_description="All PRs above ₹50,000 require two-tier departmental HOD and Financial Controller approval in ERP.",
                    control_type="Preventive",
                    manager_notes="Control Owner: Finance Controller | Frequency: Per Transaction | Testing: 25 samples",
                    audit_procedure="Verify 25 sample purchase orders against approved PRs and authority matrix.",
                    status="In Progress",
                    review_status="Pending"
                ),
                RCMLineItem(
                    engagement_id=eng_target.engagement_id,
                    line_item_id="P2P-02",
                    process_area=eng_target.process_under_audit or "Procure to Pay",
                    sub_process="Goods Receipt & 3-Way Matching",
                    risk_description="Payments made for goods/services not received, short received, or duplicate invoiced.",
                    control_description="Automated 3-way match in ERP between PO, Gate Entry/GRN, and Vendor Invoice with ±1% tolerance.",
                    control_type="Preventive",
                    manager_notes="Control Owner: Accounts Payable Lead | Frequency: Automated | Testing: Test of Controls",
                    audit_procedure="Inspect ERP system configuration rules and test 20 cleared payment vouchers for 3-way match exceptions.",
                    status="Open",
                    review_status="Pending"
                ),
                RCMLineItem(
                    engagement_id=eng_target.engagement_id,
                    line_item_id="P2P-03",
                    process_area=eng_target.process_under_audit or "Procure to Pay",
                    sub_process="Vendor Master Maintenance",
                    risk_description="Unauthorized bank account changes or dummy vendors added to ERP master data.",
                    control_description="Dual verification and independent call-back confirmation to registered vendor signatory before bank master change.",
                    control_type="Preventive",
                    manager_notes="Control Owner: Treasury Head | Frequency: Event Driven | Testing: 100% Verification of Bank Changes",
                    audit_procedure="Review audit log of vendor bank master modifications in FY and inspect signed call-back documentation.",
                    status="Open",
                    review_status="Pending"
                )
            ]
            for itm in std_items:
                db.add(itm)

            db.commit()
            log_audit_action(
                session=db,
                action_type="GENERATE_RCM",
                target_entity="Engagement",
                target_id=eng_target.engagement_code,
                description=f"Generated standard RCM items for {eng_target.engagement_code}.",
                user_id=ss.user_id,
                acting_user_name=ss.user_name,
                true_admin_id=ss.true_admin_id,
                true_admin_name=ss.true_admin_name
            )
            st.success("Standard RCM line items generated!")
            st.rerun()
    else:
        tab_labels = [r.line_item_id for r in rcm_lines]
        rcm_tabs = st.tabs(tab_labels)

        for tab_obj, rcm_item in zip(rcm_tabs, rcm_lines):
            with tab_obj:
                c_left, c_right = st.columns(2)

                # LEFT CARD: RISK / CONTROL DETAILS
                with c_left:
                    with st.container(border=True):
                        st.markdown(f"<h3 style='margin:0 0 10px 0; font-size:15px; font-weight:700; color:{tx};'>📋 Risk / Control Details ({rcm_item.line_item_id})</h3>", unsafe_allow_html=True)

                        st.markdown("<small style='font-weight:600; color:#6B7690;'>Risk Description (Locked by Manager)</small>", unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="lock-field">
                            🔒 {rcm_item.risk_description}
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown("<small style='font-weight:600; color:#6B7690;'>Control Description (Locked by Manager)</small>", unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="lock-field">
                            🔒 {rcm_item.control_description}
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown("<small style='font-weight:600; color:#6B7690;'>Audit Procedure (Editable by Team)</small>", unsafe_allow_html=True)
                        new_proc = st.text_area(
                            "Audit Procedure",
                            value=rcm_item.audit_procedure or "",
                            height=80,
                            key=f"proc_{rcm_item.id}",
                            label_visibility="collapsed"
                        )

                        st.markdown("<small style='font-weight:600; color:#6B7690;'>Testing Status</small>", unsafe_allow_html=True)
                        status_choices = ["Open", "In Progress", "Fieldwork", "Submitted", "Reviewed"]
                        curr_idx = status_choices.index(rcm_item.status) if rcm_item.status in status_choices else 1
                        new_stt = st.selectbox(
                            "Status",
                            status_choices,
                            index=curr_idx,
                            key=f"stat_{rcm_item.id}",
                            label_visibility="collapsed"
                        )

                        if st.button("Save Procedure & Status 💾", key=f"save_proc_btn_{rcm_item.id}"):
                            rcm_item.audit_procedure = new_proc
                            rcm_item.status = new_stt
                            db.commit()
                            log_audit_action(
                                session=db,
                                action_type="EDIT_RCM_LINE",
                                target_entity="RCM",
                                target_id=rcm_item.line_item_id,
                                description=f"Updated line item {rcm_item.line_item_id}: Status={new_stt}",
                                user_id=ss.user_id,
                                acting_user_name=ss.user_name,
                                true_admin_id=ss.true_admin_id,
                                true_admin_name=ss.true_admin_name
                            )
                            st.success("Saved successfully!")
                            st.rerun()

                        st.caption("🔒 Grey fields are locked by Manager and protected against overwrite.")

                # RIGHT CARD: EVIDENCE UPLOAD & OBSERVATIONS
                with c_right:
                    with st.container(border=True):
                        st.markdown(f"<h3 style='margin:0 0 10px 0; font-size:15px; font-weight:700; color:{tx};'>📁 Evidence Upload ({rcm_item.line_item_id})</h3>", unsafe_allow_html=True)

                        uploaded_files = st.file_uploader(
                            "Drag & drop working papers here",
                            accept_multiple_files=True,
                            key=f"uploader_{rcm_item.id}"
                        )
                        st.caption(f"Vault folder: `/{rcm_item.line_item_id}/{current_indian_date_str()}/`")

                        if uploaded_files:
                            if st.button("Securely Vault Uploaded Files 🔒", key=f"vault_btn_{rcm_item.id}", type="primary"):
                                today_str = current_indian_date_str()
                                dest_folder = get_line_item_storage_dir(eng_target.engagement_id, eng_target.client.name, rcm_item.line_item_id, today_str)

                                for up_file in uploaded_files:
                                    save_path = dest_folder / up_file.name
                                    file_size = save_uploaded_file(up_file, save_path)
                                    wp_rec = WorkingPaper(
                                        engagement_id=eng_target.engagement_id,
                                        rcm_item_id=rcm_item.id,
                                        line_item_id=rcm_item.line_item_id,
                                        filename=up_file.name,
                                        file_path=str(save_path),
                                        file_size_bytes=file_size,
                                        version_date=today_str,
                                        uploaded_by_id=ss.user_id,
                                        uploaded_by_name=ss.user_name,
                                        uploaded_at=datetime.utcnow()
                                    )
                                    db.add(wp_rec)

                                db.commit()
                                log_audit_action(
                                    session=db,
                                    action_type="UPLOAD_WORKING_PAPER",
                                    target_entity="WorkingPaper",
                                    target_id=rcm_item.line_item_id,
                                    description=f"Uploaded {len(uploaded_files)} working paper(s) to version folder /{rcm_item.line_item_id}/{today_str}/",
                                    user_id=ss.user_id,
                                    acting_user_name=ss.user_name,
                                    true_admin_id=ss.true_admin_id,
                                    true_admin_name=ss.true_admin_name
                                )
                                st.success("Files securely vaulted!")
                                st.rerun()

                        # OBSERVATIONS TEXTAREA (REAL DB SAVING)
                        st.markdown(f"<h3 style='margin:12px 0 6px 0; font-size:15px; font-weight:700; color:{tx};'>📝 Observations</h3>", unsafe_allow_html=True)
                        obs_obj = rcm_item.observation
                        obs_existing = obs_obj.observation_text if obs_obj else ""

                        new_obs_text = st.text_area(
                            "Observations",
                            value=obs_existing,
                            placeholder="Type or paste audit findings, exceptions, root-cause analysis…",
                            height=90,
                            key=f"obs_input_{rcm_item.id}",
                            label_visibility="collapsed"
                        )

                        if st.button("Save Observation 💾", key=f"save_obs_btn_{rcm_item.id}"):
                            if not obs_obj:
                                obs_obj = Observation(
                                    engagement_id=eng_target.engagement_id,
                                    rcm_item_id=rcm_item.id
                                )
                                db.add(obs_obj)
                            obs_obj.observation_text = new_obs_text
                            obs_obj.updated_by_id = ss.user_id
                            obs_obj.updated_by_name = ss.user_name
                            obs_obj.updated_at = datetime.utcnow()
                            db.commit()

                            log_audit_action(
                                session=db,
                                action_type="RECORD_OBSERVATION",
                                target_entity="Observation",
                                target_id=rcm_item.line_item_id,
                                description=f"Recorded audit observation on line item {rcm_item.line_item_id}.",
                                user_id=ss.user_id,
                                acting_user_name=ss.user_name,
                                true_admin_id=ss.true_admin_id,
                                true_admin_name=ss.true_admin_name
                            )
                            st.success("Observation saved to database!")
                            st.rerun()

                        # VERSION HISTORY WITH REAL DOWNLOAD BUTTONS
                        version_folders = get_all_version_folders(eng_target.engagement_id, eng_target.client.name, rcm_item.line_item_id)
                        total_files_count = sum(len([f for f in v.iterdir() if f.is_file()]) for v in version_folders) if version_folders else 0

                        with st.expander(f"🕒 Version History ({total_files_count} files across dated vaults)"):
                            if not version_folders:
                                st.caption("No working papers uploaded yet.")
                            else:
                                for vdir in version_folders:
                                    v_date = vdir.name
                                    v_files = [f for f in vdir.iterdir() if f.is_file()]
                                    for vf in v_files:
                                        c_fname, c_fdown = st.columns([3, 1])
                                        with c_fname:
                                            st.markdown(f"• **{v_date}** · `{vf.name}` ({max(1, int(vf.stat().st_size/1024))} KB)")
                                        with c_fdown:
                                            with open(vf, "rb") as dl_f:
                                                st.download_button(
                                                    label="⬇️ Download",
                                                    data=dl_f.read(),
                                                    file_name=vf.name,
                                                    key=f"dl_wp_{rcm_item.id}_{v_date}_{vf.name}"
                                                )

                # BOTTOM CARD: COMMENTS & QUERIES CHAT THREAD (REAL DB SAVING)
                with st.container(border=True):
                    c_head1, c_head2 = st.columns([4, 1.5])
                    with c_head1:
                        st.markdown(f"<h3 style='margin:0; font-size:15px; font-weight:700; color:{tx};'>💬 Comments & Queries</h3>", unsafe_allow_html=True)
                    with c_head2:
                        st.markdown('<div class="btn-white">', unsafe_allow_html=True)
                        if st.button("Mark as Reviewed ✔", key=f"rev_btn_{rcm_item.id}", width="stretch"):
                            rcm_item.review_status = "Reviewed"
                            rcm_item.status = "Reviewed"
                            rcm_item.reviewed_by_name = ss.user_name
                            rcm_item.reviewed_at = datetime.utcnow()
                            db.commit()

                            log_audit_action(
                                session=db,
                                action_type="REVIEW_LINE_ITEM",
                                target_entity="RCM",
                                target_id=rcm_item.line_item_id,
                                description=f"Manager {ss.user_name} marked line item {rcm_item.line_item_id} as Reviewed.",
                                user_id=ss.user_id,
                                acting_user_name=ss.user_name,
                                true_admin_id=ss.true_admin_id,
                                true_admin_name=ss.true_admin_name
                            )
                            st.success(f"Line item {rcm_item.line_item_id} signed off as Reviewed!")
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Display real threaded comments
                    comments = rcm_item.comments
                    if not comments:
                        st.caption("No queries or comments posted yet.")
                    else:
                        for c in comments:
                            is_mgr_comment = (c.sender_role == "Manager")
                            border_color = GOLD if is_mgr_comment else "#2BB3A3"
                            st.markdown(f"""
                            <div style="background: {bg}; border-left: 3px solid {border_color}; border-radius: 8px; padding: 10px 14px; margin: 8px 0;">
                                <b>{c.sender_name} ({c.sender_role})</b> · <span class="sub">{c.timestamp.strftime('%d-%m-%Y %H:%M') if c.timestamp else ''}</span>
                                <div style="margin-top: 4px; font-size: 13.5px; color:{tx};">
                                    {c.message}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                    # Real Comment Reply Input
                    reply_col, send_col = st.columns([5, 1])
                    with reply_col:
                        new_comment_text = st.text_input("Reply", placeholder="Write a reply or query…", label_visibility="collapsed", key=f"reply_inp_{rcm_item.id}")
                    with send_col:
                        st.markdown('<div class="btn-navy">', unsafe_allow_html=True)
                        if st.button("Send 🚀", key=f"send_comm_btn_{rcm_item.id}", width="stretch"):
                            if new_comment_text.strip():
                                new_comm_obj = CommentThread(
                                    engagement_id=eng_target.engagement_id,
                                    rcm_item_id=rcm_item.id,
                                    sender_id=ss.user_id,
                                    sender_name=ss.user_name,
                                    sender_role=ss.role,
                                    message=new_comment_text.strip(),
                                    timestamp=datetime.utcnow()
                                )
                                db.add(new_comm_obj)
                                db.commit()
                                log_audit_action(
                                    session=db,
                                    action_type="POST_COMMENT",
                                    target_entity="RCM",
                                    target_id=rcm_item.line_item_id,
                                    description=f"{ss.user_name} posted a comment on line item {rcm_item.line_item_id}.",
                                    user_id=ss.user_id,
                                    acting_user_name=ss.user_name,
                                    true_admin_id=ss.true_admin_id,
                                    true_admin_name=ss.true_admin_name
                                )
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

# =====================================================================
# SCREEN 6: CLIENTS (REAL CREATION & EDITING)
# =====================================================================
elif ss.page == "Clients":
    st.markdown(f"<h1 style='margin: 0; font-size: 24px; font-weight: 800; color:{tx};'>🏢 Client Organizations</h1>", unsafe_allow_html=True)
    st.caption("Active auditee directory and corporate governance portfolio")
    st.write("")

    if ss.role == "Manager":
        with st.expander("➕ Add New Client Organization", expanded=False):
            with st.form("add_client_form", clear_on_submit=True):
                c_c1, c_c2 = st.columns(2)
                with c_c1:
                    cl_name = st.text_input("Client Legal Name *", placeholder="e.g. Larsen & Toubro Infotech Ltd.")
                    cl_ind = st.text_input("Industry / Domain", placeholder="e.g. Engineering & IT")
                    cl_addr = st.text_area("Registered Office Address", placeholder="Street, City, State, PIN")
                with c_c2:
                    cl_spoc = st.text_input("Primary Contact Person", placeholder="e.g. Rajesh Khurana (CFO)")
                    cl_mail = st.text_input("Official Email", placeholder="e.g. rkhurana@lti.com")
                    cl_phone = st.text_input("Official Phone", placeholder="e.g. +91 22 6789 0123")

                save_client_btn = st.form_submit_button("Save Client 💾", type="primary")

            if save_client_btn:
                if ss.role != "Manager":
                    st.error("Only a Manager can create a client.")
                elif not cl_name.strip():
                    st.error("Client name is required.")
                else:
                    existing_cl = db.query(Client).filter(Client.name == cl_name.strip()).first()
                    if existing_cl:
                        st.error("A client with this name already exists.")
                    else:
                        new_cl = Client(
                            name=cl_name.strip(),
                            industry=cl_ind.strip(),
                            address=cl_addr.strip(),
                            contact_person=cl_spoc.strip(),
                            contact_email=cl_mail.strip(),
                            contact_phone=cl_phone.strip(),
                            created_at=datetime.utcnow()
                        )
                        db.add(new_cl)
                        db.commit()

                        log_audit_action(
                            session=db,
                            action_type="CLIENT_CREATED",
                            target_entity="Client",
                            target_id=new_cl.name,
                            description=f"Manager {ss.user_name} created client organization '{new_cl.name}'.",
                            user_id=ss.user_id,
                            acting_user_name=ss.user_name,
                            true_admin_id=ss.true_admin_id,
                            true_admin_name=ss.true_admin_name,
                            actor_role=ss.role,
                            target_name=new_cl.name,
                            action_category="Clients",
                            rbac_rule_applied="Manager may create and maintain client master records.",
                            new_state={
                                "name": new_cl.name, "industry": new_cl.industry,
                                "contact_person": new_cl.contact_person,
                                "contact_email": new_cl.contact_email,
                                "contact_phone": new_cl.contact_phone,
                            },
                        )
                        st.success(f"🎉 Client '{new_cl.name}' saved successfully!")
                        st.rerun()
    else:
        st.info("Client creation and editing are restricted to Managers.")

    if ss.role == "Manager":
        with st.expander("✏️ Edit Client Organization Details", expanded=False):
            all_cls = db.query(Client).order_by(Client.name).all()
            cl_names = [c.name for c in all_cls]
            if not cl_names:
                st.info("No clients found to edit.")
            else:
                selected_client_to_edit = st.selectbox("Select Client to Edit", cl_names)
                cl_obj = db.query(Client).filter(Client.name == selected_client_to_edit).first()
                if cl_obj:
                    with st.form("edit_client_form"):
                        e_c1, e_c2 = st.columns(2)
                        with e_c1:
                            e_cl_name = st.text_input("Client Legal Name", value=cl_obj.name)
                            e_cl_ind = st.text_input("Industry / Domain", value=cl_obj.industry or "")
                            e_cl_addr = st.text_area("Registered Office Address", value=cl_obj.address or "")
                        with e_c2:
                            e_cl_spoc = st.text_input("Primary Contact Person", value=cl_obj.contact_person or "")
                            e_cl_mail = st.text_input("Official Email", value=cl_obj.contact_email or "")
                            e_cl_phone = st.text_input("Official Phone", value=cl_obj.contact_phone or "")

                        update_client_btn = st.form_submit_button("Update Client Organization 💾", type="primary")
                    if update_client_btn:
                        previous_client_state = {
                            "name": cl_obj.name, "industry": cl_obj.industry,
                            "address": cl_obj.address, "contact_person": cl_obj.contact_person,
                            "contact_email": cl_obj.contact_email, "contact_phone": cl_obj.contact_phone,
                        }
                        cl_obj.name = e_cl_name.strip()
                        cl_obj.industry = e_cl_ind.strip()
                        cl_obj.address = e_cl_addr.strip()
                        cl_obj.contact_person = e_cl_spoc.strip()
                        cl_obj.contact_email = e_cl_mail.strip()
                        cl_obj.contact_phone = e_cl_phone.strip()
                        db.commit()

                        log_audit_action(
                            session=db,
                            action_type="CLIENT_UPDATED",
                            target_entity="Client",
                            target_id=cl_obj.name,
                            description=f"Manager {ss.user_name} updated client '{cl_obj.name}'.",
                            user_id=ss.user_id,
                            acting_user_name=ss.user_name,
                            true_admin_id=ss.true_admin_id,
                            true_admin_name=ss.true_admin_name,
                            actor_role=ss.role,
                            target_name=cl_obj.name,
                            action_category="Clients",
                            rbac_rule_applied="Manager may update authorized client master attributes.",
                            previous_state=previous_client_state,
                            new_state={
                                "name": cl_obj.name, "industry": cl_obj.industry,
                                "address": cl_obj.address, "contact_person": cl_obj.contact_person,
                                "contact_email": cl_obj.contact_email, "contact_phone": cl_obj.contact_phone,
                            },
                        )
                        st.success(f"Client '{cl_obj.name}' updated successfully!")
                        st.rerun()

    if ss.role == "Manager":
        with st.expander("🗑️ Delete Client Organization", expanded=False):
            clients_for_deletion = db.query(Client).order_by(Client.name).all()
            if not clients_for_deletion:
                st.info("No client is available for deletion.")
            else:
                delete_client_map = {
                    f"{client.name} · {len(client.engagements)} engagement(s)": client
                    for client in clients_for_deletion
                }
                delete_client_label = st.selectbox(
                    "Select client to delete", list(delete_client_map.keys()),
                    key="delete_client_selector",
                )
                delete_client_target = delete_client_map[delete_client_label]
                st.warning(
                    "Deleting this client also deletes every linked engagement database record. "
                    "A confirmation pop-up will ask whether local evidence should also be removed."
                )
                if st.button(
                    "Delete Selected Client",
                    key=f"open_delete_client_{delete_client_target.client_id}",
                ):
                    delete_client_dialog(delete_client_target.client_id)

    """Legacy client forms removed: permissions are enforced by the role-gated forms above."""
    if False:
        with st.form("legacy_add_client_form"):
            c_c1, c_c2 = st.columns(2)
            with c_c1:
                cl_name = st.text_input("Client Legal Name *", placeholder="e.g. Larsen & Toubro Infotech Ltd.")
                cl_ind = st.text_input("Industry / Domain", placeholder="e.g. Engineering & IT")
                cl_addr = st.text_area("Registered Office Address", placeholder="Street, City, State, PIN")
            with c_c2:
                cl_spoc = st.text_input("Primary Contact Person", placeholder="e.g. Rajesh Khurana (CFO)")
                cl_mail = st.text_input("Official Email", placeholder="e.g. rkhurana@lti.com")
                cl_phone = st.text_input("Official Phone", placeholder="e.g. +91 22 6789 0123")

            save_client_btn = st.form_submit_button("Save Client 💾", type="primary")

        if save_client_btn:
            if not cl_name.strip():
                st.error("Client name is required.")
            else:
                existing_cl = db.query(Client).filter(Client.name == cl_name.strip()).first()
                if existing_cl:
                    st.error("A client with this name already exists.")
                else:
                    new_cl = Client(
                        name=cl_name.strip(),
                        industry=cl_ind.strip(),
                        address=cl_addr.strip(),
                        contact_person=cl_spoc.strip(),
                        contact_email=cl_mail.strip(),
                        contact_phone=cl_phone.strip(),
                        created_at=datetime.utcnow()
                    )
                    db.add(new_cl)
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="CREATE_CLIENT",
                        target_entity="Client",
                        target_id=new_cl.name,
                        description=f"Created client organization '{new_cl.name}'.",
                        user_id=ss.user_id,
                        acting_user_name=ss.user_name,
                        true_admin_id=ss.true_admin_id,
                        true_admin_name=ss.true_admin_name
                    )
                    st.success(f"🎉 Client '{new_cl.name}' saved successfully!")
                    st.rerun()

    if False:
      with st.expander("✏️ Edit Client Organization Details", expanded=False):
        all_cls = db.query(Client).order_by(Client.name).all()
        cl_names = [c.name for c in all_cls]
        if not cl_names:
            st.info("No clients found to edit.")
        else:
            selected_client_to_edit = st.selectbox("Select Client to Edit", cl_names)
            cl_obj = db.query(Client).filter(Client.name == selected_client_to_edit).first()
            if cl_obj:
                with st.form("edit_client_form"):
                    e_c1, e_c2 = st.columns(2)
                    with e_c1:
                        e_cl_name = st.text_input("Client Legal Name", value=cl_obj.name)
                        e_cl_ind = st.text_input("Industry / Domain", value=cl_obj.industry or "")
                        e_cl_addr = st.text_area("Registered Office Address", value=cl_obj.address or "")
                    with e_c2:
                        e_cl_spoc = st.text_input("Primary Contact Person", value=cl_obj.contact_person or "")
                        e_cl_mail = st.text_input("Official Email", value=cl_obj.contact_email or "")
                        e_cl_phone = st.text_input("Official Phone", value=cl_obj.contact_phone or "")

                    if st.form_submit_button("Update Client Organization 💾", type="primary"):
                        cl_obj.name = e_cl_name.strip()
                        cl_obj.industry = e_cl_ind.strip()
                        cl_obj.address = e_cl_addr.strip()
                        cl_obj.contact_person = e_cl_spoc.strip()
                        cl_obj.contact_email = e_cl_mail.strip()
                        cl_obj.contact_phone = e_cl_phone.strip()
                        db.commit()

                        log_audit_action(
                            session=db,
                            action_type="EDIT_CLIENT",
                            target_entity="Client",
                            target_id=cl_obj.name,
                            description=f"Updated details for client '{cl_obj.name}'.",
                            user_id=ss.user_id,
                            acting_user_name=ss.user_name,
                            true_admin_id=ss.true_admin_id,
                            true_admin_name=ss.true_admin_name
                        )
                        st.success(f"Client '{cl_obj.name}' updated successfully!")
                        st.rerun()

    # Query real clients from database
    clients_list = db.query(Client).order_by(Client.name).all()
    clients_table_data = []
    for cl in clients_list:
        clients_table_data.append({
            "Client Name": cl.name,
            "Industry": cl.industry or "-",
            "Primary Contact": cl.contact_person or "-",
            "Email": cl.contact_email or "-",
            "Active Engagements": len(cl.engagements)
        })

    with st.container(border=True):
        st.dataframe(pd.DataFrame(clients_table_data), width="stretch", hide_index=True)

# =====================================================================
# SCREEN 7: TEAM MANAGEMENT (REAL CREATION & EDITING)
# =====================================================================
elif ss.page == "Team Management":
    st.markdown(f"<h1 style='margin: 0; font-size: 24px; font-weight: 800; color:{tx};'>👥 Team Management</h1>", unsafe_allow_html=True)
    st.caption("Manage audit squads (Team 1, Team 2), register auditors, and maintain credentials")
    st.write("")

    tab_sq, tab_reg, tab_pwd, tab_delete_user, tab_access = st.tabs([
        "👥 Audit Squads", "➕ Register Auditor", "🔑 Reset Password",
        "🗑️ Delete Account", "🛡️ Access Control Audit"
    ])

    with tab_sq:
        with st.expander("➕ Create New Audit Squad", expanded=False):
            with st.form("create_team_form", clear_on_submit=True):
                sq_name = st.text_input("Squad Name *", placeholder="e.g. Team 4 - Forensic & Fraud Risk")
                sq_desc = st.text_area("Squad Description", placeholder="Specializing in data analytics and forensic verification...")

                auditors_in_db = db.query(User).filter(
                    User.role == "Team Member", User.is_deleted == False
                ).all()
                aud_options = {f"{u.name} ({u.designation or 'Auditor'})": u.user_id for u in auditors_in_db}
                selected_auditors = st.multiselect("Assign Members", list(aud_options.keys()))

                create_team_sub = st.form_submit_button("Create Team 👥", type="primary")

            if create_team_sub:
                if not sq_name.strip():
                    st.error("Squad name is required.")
                else:
                    new_team_rec = Team(
                        name=sq_name.strip(),
                        description=sq_desc.strip(),
                        created_by_manager_id=ss.user_id,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_team_rec)
                    db.commit()

                    for a_lbl in selected_auditors:
                        uid = aud_options[a_lbl]
                        db.add(TeamMemberMapping(team_id=new_team_rec.team_id, user_id=uid))
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="AUDIT_TEAM_CREATED",
                        target_entity="Team",
                        target_id=str(new_team_rec.team_id),
                        description=f"Created team squad '{new_team_rec.name}' with {len(selected_auditors)} member(s).",
                        user_id=ss.user_id,
                        acting_user_name=ss.user_name,
                        true_admin_id=ss.true_admin_id,
                        true_admin_name=ss.true_admin_name,
                        actor_role=ss.role,
                        target_name=new_team_rec.name,
                        action_category="Teams",
                        rbac_rule_applied="Manager may form audit teams using Team Member accounts only.",
                        new_state={
                            "team_id": new_team_rec.team_id,
                            "name": new_team_rec.name,
                            "description": new_team_rec.description,
                            "members": selected_auditors,
                        },
                    )
                    st.success(f"Team '{new_team_rec.name}' created successfully!")
                    st.rerun()

        teams_list = db.query(Team).all()
        teams_table = []
        for t in teams_list:
            m_names = ", ".join([m.user.name for m in t.members]) if t.members else "No members"
            teams_table.append({
                "Squad Name": t.name,
                "Description": t.description or "-",
                "Members": m_names,
                "Status": "Active"
            })
        with st.container(border=True):
            st.dataframe(pd.DataFrame(teams_table), width="stretch", hide_index=True)

        st.markdown(f"<h3 style='color:{tx}; margin-top:18px;'>Edit Existing Audit Squad</h3>", unsafe_allow_html=True)
        if teams_list:
            team_options = {t.name: t for t in teams_list}
            selected_team_name = st.selectbox("Select squad to edit", list(team_options.keys()))
            selected_team = team_options[selected_team_name]
            current_member_ids = {m.user_id for m in selected_team.members}
            edit_auditors = db.query(User).filter(
                User.role == "Team Member", User.is_deleted == False
            ).order_by(User.name).all()
            edit_options = {f"{u.name} ({u.designation or 'Auditor'})": u.user_id for u in edit_auditors}
            current_labels = [label for label, uid in edit_options.items() if uid in current_member_ids]
            with st.form("edit_team_form"):
                edit_name = st.text_input("Squad Name *", value=selected_team.name)
                edit_desc = st.text_area("Squad Description", value=selected_team.description or "")
                edit_members = st.multiselect("Members", list(edit_options.keys()), default=current_labels)
                update_team_btn = st.form_submit_button("Save Squad Changes 💾", type="primary")
            if update_team_btn:
                duplicate = db.query(Team).filter(Team.name == edit_name.strip(), Team.team_id != selected_team.team_id).first()
                if not edit_name.strip():
                    st.error("Squad name is required.")
                elif duplicate:
                    st.error("Another squad already uses that name.")
                else:
                    previous_team_state = {
                        "name": selected_team.name,
                        "description": selected_team.description,
                        "members": current_labels,
                    }
                    selected_team.name = edit_name.strip()
                    selected_team.description = edit_desc.strip()
                    selected_team.members.clear()
                    db.flush()
                    for member_label in edit_members:
                        selected_team.members.append(TeamMemberMapping(user_id=edit_options[member_label]))
                    db.commit()
                    log_audit_action(
                        session=db, action_type="AUDIT_TEAM_UPDATED", target_entity="Team",
                        target_id=str(selected_team.team_id),
                        description=f"Updated squad '{selected_team.name}' and assigned {len(edit_members)} member(s).",
                        user_id=ss.user_id, acting_user_name=ss.user_name,
                        true_admin_id=ss.true_admin_id, true_admin_name=ss.true_admin_name,
                        actor_role=ss.role, target_name=selected_team.name,
                        action_category="Teams",
                        rbac_rule_applied="Manager may update audit team roster using Team Member accounts only.",
                        previous_state=previous_team_state,
                        new_state={
                            "name": selected_team.name,
                            "description": selected_team.description,
                            "members": edit_members,
                        },
                    )
                    st.success("Squad details and membership updated.")
                    st.rerun()

            with st.expander("Delete Audit Squad", expanded=False):
                st.warning(
                    "Deleting a squad removes its member links and detaches it from existing "
                    "engagement allocations. The engagement and individual auditor assignments remain intact."
                )
                confirm_delete_team = st.checkbox(
                    f"I confirm deletion of '{selected_team.name}'",
                    key=f"confirm_delete_team_{selected_team.team_id}",
                )
                if st.button(
                    "Delete Squad",
                    key=f"delete_team_{selected_team.team_id}",
                    disabled=not confirm_delete_team,
                ):
                    deleted_team_state = {
                        "team_id": selected_team.team_id,
                        "name": selected_team.name,
                        "description": selected_team.description,
                        "members": current_labels,
                    }
                    team_id_to_delete = selected_team.team_id
                    team_name_to_delete = selected_team.name
                    linked_allocations = db.query(EngagementTeamAssignment).filter(
                        EngagementTeamAssignment.team_id == team_id_to_delete
                    ).all()
                    for allocation in linked_allocations:
                        allocation.team_id = None
                    selected_team.members.clear()
                    db.flush()
                    db.delete(selected_team)
                    db.commit()
                    log_audit_action(
                        session=db,
                        action_type="AUDIT_TEAM_DELETED",
                        target_entity="Team",
                        target_id=str(team_id_to_delete),
                        description=(
                            f"Deleted audit squad '{team_name_to_delete}', removed its member links, "
                            f"and detached {len(linked_allocations)} engagement allocation(s)."
                        ),
                        user_id=ss.user_id,
                        acting_user_name=ss.user_name,
                        true_admin_id=ss.true_admin_id,
                        true_admin_name=ss.true_admin_name,
                        actor_role=ss.role,
                        target_name=team_name_to_delete,
                        action_category="Teams",
                        rbac_rule_applied="Manager or Admin may delete audit teams; engagement and user records are retained.",
                        previous_state=deleted_team_state,
                        new_state={
                            "deleted": True,
                            "member_links_removed": len(current_labels),
                            "engagement_team_links_detached": len(linked_allocations),
                        },
                    )
                    st.success(f"Squad '{team_name_to_delete}' deleted and linked records safely detached.")
                    st.rerun()

    with tab_reg:
        with st.form("reg_auditor_form", clear_on_submit=True):
            reg_heading = "Register New Auditor / Manager" if ss.role == "Admin" else "Register New Auditor"
            st.markdown(f"<h3 style='margin:0 0 10px 0; color:{tx};'>{reg_heading}</h3>", unsafe_allow_html=True)
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                new_uname = st.text_input("Username *", placeholder="e.g. suresh.iyer")
                new_fname = st.text_input("Full Name *", placeholder="e.g. Suresh Iyer")
                allowed_roles = ["Team Member", "Manager"] if ss.role == "Admin" else ["Team Member"]
                new_role_sel = st.selectbox("Role *", allowed_roles, disabled=(ss.role != "Admin"))
            with col_u2:
                new_email = st.text_input("Official Email *", placeholder="e.g. suresh.iyer@firm.in")
                new_phone = st.text_input("Phone Number", placeholder="e.g. +91 98765 43210")
                new_pwd = st.text_input("Temporary Password *", value="auditor123", type="password")

            reg_btn = st.form_submit_button("Register User Account 🚀", type="primary")

        if reg_btn:
            if not new_uname.strip() or not new_fname.strip() or not new_email.strip():
                st.error("Please fill in Username, Full Name, and Email.")
            elif ss.role != "Admin" and new_role_sel != "Team Member":
                st.error("Only an Admin can create a Manager account.")
            else:
                exists_u = db.query(User).filter((User.username == new_uname.strip()) | (User.email == new_email.strip())).first()
                if exists_u:
                    st.error("Username or email already registered.")
                else:
                    enforced_role = new_role_sel if ss.role == "Admin" else "Team Member"
                    new_user_rec = User(
                        username=new_uname.strip().lower(),
                        password_hash=hash_password(new_pwd.strip()),
                        name=new_fname.strip(),
                        email=new_email.strip().lower(),
                        phone=new_phone.strip(),
                        role=enforced_role,
                        is_first_login=False,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_user_rec)
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="USER_CREATED",
                        target_entity="User",
                        target_id=new_user_rec.username,
                        description=f"Admin/Manager registered new user '{new_user_rec.name}' ({new_user_rec.role}).",
                        user_id=ss.user_id,
                        acting_user_name=ss.user_name,
                        true_admin_id=ss.true_admin_id,
                        true_admin_name=ss.true_admin_name,
                        actor_role=ss.role,
                        target_role=new_user_rec.role,
                        target_name=new_user_rec.name,
                        action_category="Users",
                        rbac_rule_applied=(
                            "Admin may create Manager or Team Member accounts."
                            if ss.role == "Admin"
                            else "Manager may create Team Member accounts only; Manager creation is prohibited."
                        ),
                        new_state={
                            "username": new_user_rec.username,
                            "name": new_user_rec.name,
                            "email": new_user_rec.email,
                            "phone": new_user_rec.phone,
                            "role": new_user_rec.role,
                        },
                    )
                    st.success(f"User account for '{new_user_rec.name}' created successfully!")
                    st.rerun()

    with tab_pwd:
        reset_heading = "Reset Auditor / Manager Credentials" if ss.role == "Admin" else "Reset Team Member Credentials"
        st.markdown(f"<h3 style='margin:0 0 10px 0; color:{tx};'>{reset_heading}</h3>", unsafe_allow_html=True)
        reset_query = db.query(User).filter(User.is_deleted == False)
        if ss.role != "Admin":
            reset_query = reset_query.filter(User.role == "Team Member")
        all_users = reset_query.order_by(User.name).all()
        user_opts = {f"{u.name} (@{u.username} · {u.role})": u for u in all_users}
        
        with st.form("reset_pwd_form"):
            sel_user_str = st.selectbox("Select User Account *", list(user_opts.keys()))
            col_pw1, col_pw2 = st.columns(2)
            with col_pw1:
                new_pass = st.text_input("New Password *", type="password")
            with col_pw2:
                conf_pass = st.text_input("Confirm New Password *", type="password")

            reset_pwd_btn = st.form_submit_button("Reset Password 🔑", type="primary")

        if reset_pwd_btn:
            if not new_pass or not conf_pass:
                st.error("Please enter both password fields.")
            elif new_pass != conf_pass:
                st.error("Passwords do not match.")
            else:
                target_user = user_opts[sel_user_str]
                if ss.role != "Admin" and target_user.role != "Team Member":
                    st.error("Managers may reset credentials for Team Members only.")
                    st.stop()
                target_user.password_hash = hash_password(new_pass.strip())
                db.commit()

                log_audit_action(
                    session=db,
                    action_type="RESET_PASSWORD",
                    target_entity="User",
                    target_id=target_user.username,
                    description=f"{ss.user_name} reset password for user account '{target_user.username}'.",
                    user_id=ss.user_id,
                    acting_user_name=ss.user_name,
                    true_admin_id=ss.true_admin_id,
                    true_admin_name=ss.true_admin_name,
                    actor_role=ss.role,
                    target_role=target_user.role,
                    target_name=target_user.name,
                    action_category="Users",
                    rbac_rule_applied="Credential reset is limited to Admin or Manager support workspace access.",
                    extra_metadata={"credential_changed": True, "password_value_logged": False},
                )
                st.success(f"Password for '{target_user.name}' has been successfully reset!")
                st.rerun()

    with tab_delete_user:
        delete_role = "Manager" if ss.role == "Admin" else "Team Member"
        st.markdown(
            f"<h3 style='margin:0 0 10px 0; color:{tx};'>Delete {delete_role} Account</h3>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Account access is revoked immediately. Historical evidence attribution and immutable audit records are retained."
        )
        deletion_users = db.query(User).filter(
            User.role == delete_role, User.is_deleted == False, User.user_id != ss.user_id
        ).order_by(User.name).all()
        if not deletion_users:
            st.info(f"No active {delete_role} account is available for deletion.")
        else:
            deletion_user_map = {
                f"{user.name} (@{user.username})": user for user in deletion_users
            }
            deletion_user_label = st.selectbox(
                "Select account", list(deletion_user_map.keys()), key="delete_user_selector"
            )
            deletion_user_target = deletion_user_map[deletion_user_label]
            if st.button(
                f"Delete {delete_role} Account",
                key=f"open_delete_user_{deletion_user_target.user_id}",
            ):
                delete_user_dialog(deletion_user_target.user_id)

    with tab_access:
        render_access_control_audit(embedded=True)

# =====================================================================
# SCREEN 8: AUDIT TRAIL (REAL DATABASE PERSISTENCE & EXPORT)
# =====================================================================
elif ss.page == "Audit Trail":
    st.markdown(f"<h1 style='margin: 0; font-size: 24px; font-weight: 800; color:{tx};'>🕒 Immutable Audit Trail</h1>", unsafe_allow_html=True)
    st.markdown("<div class='sub'>Complete system ledger and dedicated access-governance accountability</div>", unsafe_allow_html=True)
    st.write("")
    system_ledger_tab, access_ledger_tab = st.tabs([
        "Complete System Audit Ledger", "Access Control & RBAC Accountability"
    ])
    with system_ledger_tab:
        render_system_audit_ledger()
    with access_ledger_tab:
        render_access_control_audit(embedded=False)

# =====================================================================
# SCREEN 9: MY PROFILE
# =====================================================================
elif ss.page == "My Profile":
    st.markdown(f"<h1 style='margin: 0; font-size: 24px; font-weight: 800; color:{tx};'>👤 User Profile</h1>", unsafe_allow_html=True)
    st.caption("Credentials, contact settings, and interface preferences")
    st.write("")

    curr_user = db.get(User, ss.user_id) if ss.user_id else None

    with st.container(border=True):
        if curr_user and curr_user.profile_picture and Path(curr_user.profile_picture).exists():
            st.image(curr_user.profile_picture, width=120, caption="Current profile photo")
        uploaded_profile_pic = st.file_uploader("Profile Photo", type=["png", "jpg", "jpeg"], help="This photo is shown to other users across AuditVault.")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_name = st.text_input("Full Name", value=curr_user.name if curr_user else ss.user_name)
            p_email = st.text_input("Official Email", value=curr_user.email if curr_user else f"{ss.username}@firm.in")
        with col_p2:
            st.text_input("Role", value=ss.role, disabled=True)
            p_phone = st.text_input("Phone Number", value=curr_user.phone if curr_user else "+91 98111 22334")

        if st.button("Update Profile 💾", type="primary"):
            if curr_user:
                previous_profile_state = {
                    "name": curr_user.name,
                    "email": curr_user.email,
                    "phone": curr_user.phone,
                    "profile_picture": bool(curr_user.profile_picture),
                }
                if uploaded_profile_pic:
                    profile_dir = Path("AuditVault_Data") / "profile_pictures"
                    profile_dir.mkdir(parents=True, exist_ok=True)
                    safe_ext = ".png" if uploaded_profile_pic.type == "image/png" else ".jpg"
                    profile_path = profile_dir / f"user_{curr_user.user_id}{safe_ext}"
                    profile_path.write_bytes(uploaded_profile_pic.getbuffer())
                    curr_user.profile_picture = str(profile_path.resolve())
                curr_user.name = p_name
                curr_user.email = p_email
                curr_user.phone = p_phone
                db.commit()
                ss.user_name = p_name
                log_audit_action(
                    session=db,
                    action_type="USER_UPDATED",
                    target_entity="User",
                    target_id=curr_user.username,
                    description=f"{curr_user.name} updated their AuditVault profile.",
                    user_id=curr_user.user_id,
                    acting_user_name=curr_user.name,
                    actor_role=curr_user.role,
                    target_role=curr_user.role,
                    target_name=curr_user.name,
                    action_category="Users",
                    rbac_rule_applied="Authenticated users may update their own profile attributes.",
                    previous_state=previous_profile_state,
                    new_state={
                        "name": curr_user.name,
                        "email": curr_user.email,
                        "phone": curr_user.phone,
                        "profile_picture": bool(curr_user.profile_picture),
                    },
                )
                st.success("Profile updated successfully!")
                st.rerun()

else:
    st.title(ss.page)
    st.info("Screen placeholder.")
