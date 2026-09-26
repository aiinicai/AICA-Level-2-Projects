"""
AuditVault - Engagement Hub & Central Workspace
Connects Engagement Letter, IDR, RCM, Fieldwork Vault, and
Step 7 Finalization, Consolidation & Reopening workflows.
"""

from pathlib import Path
from datetime import datetime
import streamlit as st

from models import Engagement, RCMLineItem, IDRItem, WorkingPaper
from utils import (
    format_indian_currency, format_indian_date, is_overdue,
    consolidate_engagement_files, log_audit_action, format_indian_number
)
from styles import render_status_badge
from auth import is_manager, is_team_member

# Import child workspaces
from modules.idr_module import render_idr_workspace
from modules.rcm_module import render_rcm_workspace
from modules.fieldwork import render_fieldwork_workspace


def render_engagement_detail_hub(db):
    """Central view for a selected engagement."""
    eng_id = st.session_state.get("selected_engagement_id")
    if not eng_id:
        st.info("No engagement selected. Please return to the Engagements list.")
        if st.button("⬅️ View Engagements"):
            st.session_state.active_page = "Engagements"
            st.rerun()
        return

    eng = db.query(Engagement).filter(Engagement.engagement_id == eng_id).first()
    if not eng:
        st.error("Engagement not found.")
        return

    # Back button navigation
    col_nav, col_lock = st.columns([4, 2])
    with col_nav:
        if st.button("⬅️ Back to All Engagements", key="back_to_engs"):
            st.session_state.selected_engagement_id = None
            st.session_state.active_page = "Engagements"
            st.rerun()

    with col_lock:
        if eng.is_locked:
            st.markdown("<div style='text-align:right;'><span class='badge badge-locked'>🔒 FINALIZED & LOCKED</span></div>", unsafe_allow_html=True)

    # 1. Header Banner Card
    badge_html = render_status_badge(eng.status)
    budget_fmt = format_indian_currency(eng.estimated_budget)

    # Calculate review completion %
    rcm_items = eng.rcm_items
    total_rcm = len(rcm_items)
    reviewed_rcm = sum(1 for r in rcm_items if r.review_status == "Reviewed" or r.status == "Reviewed")
    comp_pct = int((reviewed_rcm / total_rcm * 100)) if total_rcm > 0 else (100 if eng.status == "Completed" else 0)

    st.markdown(f"""
    <div class="vault-card" style="margin-top: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <span style="font-size: 13px; font-weight: 700; color: #D97706; letter-spacing: 0.5px;">[{eng.engagement_code}]</span>
                <h2 style="margin: 4px 0 6px 0; font-size: 22px; font-weight: 800; color: #0A2540;">{eng.title}</h2>
                <div style="font-size: 14px; color: #475569;">
                    <b>Client:</b> {eng.client.name} &nbsp;|&nbsp; <b>Process:</b> {eng.process_under_audit} &nbsp;|&nbsp; <b>Manager:</b> {eng.manager.name}
                </div>
            </div>
            <div>{badge_html}</div>
        </div>
        <div style="margin-top: 12px; display: flex; gap: 24px; font-size: 13px; color: #64748B;">
            <div>🗓️ <b>Audit Period:</b> {eng.audit_period_start} to {eng.audit_period_end}</div>
            <div>🎯 <b>Deadline:</b> {eng.deadline or 'Not set'}</div>
            <div>💰 <b>Budget:</b> {budget_fmt}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Overdue alert if applicable
    if eng.deadline and eng.status != "Completed":
        overdue_flag, days = is_overdue(eng.deadline)
        if overdue_flag:
            st.error(f"⚠️ **OVERDUE ALERT:** This engagement deadline was **{eng.deadline}** ({days} days overdue!). Prompt completion and review required.")

    # Top-level module navigation tabs
    hub_tabs = st.tabs([
        "1. Overview & Scope",
        "2. Initial Data Request (IDR)",
        "3. Risk Control Matrix (RCM)",
        "4. Fieldwork & Evidence Vault",
        "5. Finalization & Consolidation 🏆"
    ])

    # Tab 1: Overview & Scope
    with hub_tabs[0]:
        render_overview_tab(db, eng)

    # Tab 2: IDR Module
    with hub_tabs[1]:
        render_idr_workspace(db, eng)

    # Tab 3: RCM Module
    with hub_tabs[2]:
        render_rcm_workspace(db, eng)

    # Tab 4: Fieldwork Vault
    with hub_tabs[3]:
        render_fieldwork_workspace(db, eng)

    # Tab 5: Finalization, Consolidation & Reopen
    with hub_tabs[4]:
        render_finalization_tab(db, eng, rcm_items, reviewed_rcm, total_rcm)


# =====================================================================
# TAB 1: OVERVIEW & SCOPE
# =====================================================================

def render_overview_tab(db, eng: Engagement):
    """Render engagement metadata, team assignments, and engagement letter."""
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown("### 📋 Audit Charter & Scope")
        st.markdown(f"**Audit Scope:**")
        st.info(eng.scope or "Standard operational and financial control scope.")

        st.markdown(f"**Specific Areas Covered:**")
        st.markdown(eng.areas_covered or "All in-scope financial and accounting sub-processes.")

    with c2:
        st.markdown("### 👥 Assigned Audit Team")
        assignments = eng.team_assignments
        if not assignments:
            st.warning("No audit team members assigned yet.")
        else:
            for a in assignments:
                st.markdown(f"• **{a.user.name}** - `{a.role_in_audit}` ({a.user.designation or 'Auditor'})")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📎 Signed Engagement Letter")
        if eng.engagement_letter_filename and eng.engagement_letter_path:
            st.markdown(f"📄 **File:** `{eng.engagement_letter_filename}`")
            el_path = Path(eng.engagement_letter_path)
            if el_path.exists():
                with open(el_path, "rb") as el_f:
                    st.download_button(
                        label="⬇️ Download Engagement Letter",
                        data=el_f.read(),
                        file_name=eng.engagement_letter_filename,
                        key="dl_eng_letter"
                    )
        else:
            st.caption("No engagement letter uploaded.")


# =====================================================================
# TAB 5: STEP 7 FINALIZATION, CONSOLIDATION & REOPENING
# =====================================================================

def render_finalization_tab(db, eng: Engagement, rcm_items, reviewed_rcm: int, total_rcm: int):
    """
    Step 7: Finalization and Consolidation
    Manager reviews status -> clicks Complete Audit -> consolidates latest files into:
    /AuditVault_Data/Consolidated/{EngagementID}_{ClientName}/{LineItemID}/[final files]
    Prompts to save consolidated ZIP -> User chooses to retain or cleanup originals.
    Engagement locked for team members.
    Manager can reopen with logged reason.
    """
    is_mgr = is_manager()
    st.markdown("### 🏆 Engagement Finalization & Consolidated Archival")
    st.markdown("*Review completion status, lock working papers, and generate the final consolidated audit repository.*")
    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    # 1. Review Checklist
    st.markdown("#### 📋 Quality Review Checklist")
    c_p1, c_p2 = st.columns(2)
    c_p1.metric("Total RCM Line Items", str(total_rcm))
    c_p2.metric("Manager Reviewed & Approved", f"{reviewed_rcm} of {total_rcm}")

    all_reviewed = (total_rcm > 0 and reviewed_rcm == total_rcm)
    if all_reviewed:
        st.success("✅ All RCM line items have been reviewed and approved by the Audit Manager!")
    else:
        st.warning(f"⚠️ {total_rcm - reviewed_rcm} line item(s) are still pending formal Manager review.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Complete Audit Workflow (if not completed)
    if not eng.is_locked:
        st.markdown("#### 🔐 Finalize Audit & Consolidate Vault")
        st.caption("Consolidates the latest version of every evidence file per line item into a clean folder structure and produces an archival ZIP.")

        if not is_mgr:
            st.info("ℹ️ Only the Audit Manager has authority to finalize and lock the engagement.")
            return

        with st.form("consolidation_form"):
            st.markdown("##### Consolidation Configuration:")
            st.markdown(f"• **Target Consolidated Structure:** `/AuditVault_Data/Consolidated/{eng.engagement_id}_{eng.client.name}/`")
            
            clean_choice = st.radio(
                "Working Files Storage Option:",
                [
                    "Retain original working files in vault storage as backup (Recommended) 🛡️",
                    "Delete original working files from AuditVault storage and retain only consolidated archive"
                ],
                index=0
            )

            delete_originals = (clean_choice != "Retain original working files in vault storage as backup (Recommended) 🛡️")

            confirm_btn = st.form_submit_button("Complete Audit & Consolidate Files 🏆", type="primary")

        if confirm_btn:
            cons_dir, zip_path, stats = consolidate_engagement_files(
                engagement_id=eng.engagement_id,
                client_name=eng.client.name,
                engagement_code=eng.engagement_code,
                delete_originals=delete_originals
            )

            # Update engagement status and lock
            eng.status = "Completed"
            eng.is_locked = True
            eng.completed_at = datetime.utcnow()
            eng.consolidation_zip_path = str(zip_path)
            db.commit()

            log_audit_action(
                session=db,
                action_type="COMPLETE_AUDIT",
                target_entity="Engagement",
                target_id=eng.engagement_code,
                description=f"Manager completed audit. Consolidating {stats['files_consolidated']} files across {stats['line_items_processed']} line items. Locked for all team members.",
                user_id=st.session_state.user_id,
                acting_user_name=st.session_state.name,
                true_admin_id=st.session_state.true_admin_id,
                true_admin_name=st.session_state.true_admin_name
            )

            st.success("🎉 Engagement successfully finalized, locked, and consolidated!")
            st.rerun()

    # 3. Completed State: Download Consolidated Archive & Reopening Controls
    else:
        st.success("🎉 **AUDIT COMPLETED & LOCKED:** This engagement is officially signed off and archived.")
        
        # Download ZIP button
        if eng.consolidation_zip_path and Path(eng.consolidation_zip_path).exists():
            zip_p = Path(eng.consolidation_zip_path)
            with open(zip_p, "rb") as z_f:
                st.download_button(
                    label="⬇️ Download Consolidated Audit ZIP Archive 📦",
                    data=z_f.read(),
                    file_name=zip_p.name,
                    mime="application/zip",
                    type="primary"
                )
            st.caption(f"Archival package contains clean, organized line-item folders and latest file versions.")

        st.markdown("<hr style='margin: 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

        # Manager Reopen Workflow
        if is_mgr:
            st.markdown("#### 🔓 Reopen Engagement (Manager Override)")
            st.caption("Need to conduct additional fieldwork or address post-audit queries? Only the Audit Manager can unlock.")

            with st.expander("Reopen Engagement Controls", expanded=False):
                reopen_reason = st.text_area("Justification / Reason for Reopening *", placeholder="e.g. Client submitted revised revenue reconciliation post external audit committee review...")
                
                if st.button("Unlock & Reopen Engagement ↩️", type="primary"):
                    if not reopen_reason.strip():
                        st.error("Please provide a justification for reopening.")
                        return

                    eng.status = "In Progress"
                    eng.is_locked = False
                    eng.completed_at = None
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="REOPEN_ENGAGEMENT",
                        target_entity="Engagement",
                        target_id=eng.engagement_code,
                        description=f"Manager reopened engagement. Justification: {reopen_reason.strip()}",
                        user_id=st.session_state.user_id,
                        acting_user_name=st.session_state.name,
                        true_admin_id=st.session_state.true_admin_id,
                        true_admin_name=st.session_state.true_admin_name
                    )

                    st.success("Engagement reopened! Team member editing rights have been restored.")
                    st.rerun()
