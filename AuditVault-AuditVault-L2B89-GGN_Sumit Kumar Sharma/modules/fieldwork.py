"""
AuditVault - Fieldwork & Evidence Vault Workspace
Dedicated tab per RCM line item with:
1. Control & Procedure Reference
2. Evidence upload with auto-created daily date versioned folders
3. File version explorer & native file opening / download
4. Audit observations editor
5. In-app comment & query threads
6. Manager review sign-off
"""

import os
from pathlib import Path
from datetime import datetime
import streamlit as st

from models import Engagement, RCMLineItem, WorkingPaper, Observation, CommentThread, User
from utils import (
    format_indian_date, current_indian_date_str, current_indian_timestamp_str,
    get_line_item_storage_dir, get_all_version_folders, save_uploaded_file,
    open_file_in_native_app, log_audit_action, format_indian_number
)
from styles import render_status_badge
from auth import is_manager, is_team_member


def render_fieldwork_workspace(db, eng: Engagement):
    """Render the tabbed fieldwork workspace, with one dedicated tab per RCM line item."""
    st.markdown(f"### 🧪 Fieldwork & Evidence Vault - [{eng.engagement_code}]")
    st.markdown(f"*Client: **{eng.client.name}** | Auto-versioned working paper repository.*")
    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    rcm_items = db.query(RCMLineItem).filter(RCMLineItem.engagement_id == eng.engagement_id).all()
    if not rcm_items:
        st.warning("⚠️ No RCM line items found for this engagement. Please upload or load an RCM matrix first in the 'Risk Control Matrix' section.")
        return

    # Check if engagement is locked
    if eng.is_locked:
        st.info("🔒 **This engagement is Finalized & Locked.** All working papers and observations are in tamper-proof read-only mode.")

    # Create dedicated tab per RCM Line Item
    tab_titles = [f"📌 [{r.line_item_id}] {r.process_area[:22]}..." if len(r.process_area) > 22 else f"📌 [{r.line_item_id}] {r.process_area}" for r in rcm_items]
    tabs = st.tabs(tab_titles)

    for idx, (tab, item) in enumerate(zip(tabs, rcm_items)):
        with tab:
            render_single_line_item_fieldwork(db, eng, item)


def render_single_line_item_fieldwork(db, eng: Engagement, item: RCMLineItem):
    """Render workspace for a single RCM line item."""
    is_mgr = is_manager()
    is_team = is_team_member()
    is_locked_eng = eng.is_locked

    # 1. Header & Control Card
    status_html = render_status_badge(item.status)
    rev_badge = "<span style='background:#ECFDF5; color:#059669; padding:2px 8px; border-radius:12px; font-weight:700;'>✅ REVIEWED BY MANAGER</span>" if item.review_status == "Reviewed" else "<span style='background:#FEF3C7; color:#D97706; padding:2px 8px; border-radius:12px; font-weight:700;'>⏳ REVIEW PENDING</span>"

    st.markdown(f"#### 🔍 [{item.line_item_id}] {item.process_area}")
    st.markdown(f"**Status:** {status_html} &nbsp;&nbsp;|&nbsp;&nbsp; **Review Status:** {rev_badge}", unsafe_allow_html=True)

    with st.container():
        st.markdown(f"""
        <div style="background-color: rgba(10, 37, 64, 0.03); border: 1px solid rgba(100, 116, 139, 0.2); border-radius: 8px; padding: 14px; margin-bottom: 16px;">
            <b>Risk Description:</b> {item.risk_description}<br>
            <b>Control Description:</b> {item.control_description} <i>({item.control_type})</i><br>
            <b>Audit Procedure:</b> <span style="color: #1E3A8A; font-weight: 600;">{item.audit_procedure}</span><br>
            <small style="color: #64748B;">Assigned Auditor: <b>{item.assigned_person.name if item.assigned_person else 'Unassigned'}</b></small>
        </div>
        """, unsafe_allow_html=True)

    # Manager Review Sign-Off Bar
    if is_mgr and not is_locked_eng:
        c_rev1, c_rev2 = st.columns([3, 1])
        with c_rev1:
            st.caption("Manager Review Control: Inspect evidence and observations below, then mark as Reviewed.")
        with c_rev2:
            if item.review_status != "Reviewed":
                if st.button("Mark as Reviewed ✅", key=f"rev_btn_{item.id}", type="primary"):
                    item.review_status = "Reviewed"
                    item.reviewed_by_name = st.session_state.name
                    item.reviewed_at = datetime.utcnow()
                    db.commit()
                    log_audit_action(
                        session=db,
                        action_type="REVIEW_LINE_ITEM",
                        target_entity="RCM",
                        target_id=item.line_item_id,
                        description=f"Manager marked line item {item.line_item_id} as Reviewed.",
                        user_id=st.session_state.user_id,
                        acting_user_name=st.session_state.name,
                        true_admin_id=st.session_state.true_admin_id,
                        true_admin_name=st.session_state.true_admin_name
                    )
                    st.success("Line item marked as Reviewed!")
                    st.rerun()
            else:
                if st.button("Revert to Pending Review ↩️", key=f"unrev_btn_{item.id}"):
                    item.review_status = "Pending"
                    db.commit()
                    st.rerun()

    st.markdown("<hr style='margin: 12px 0; border-color: rgba(100,116,139,0.15);'>", unsafe_allow_html=True)

    # Two main columns: Left = Evidence & Files, Right = Observations & Queries
    col_files, col_obs = st.columns([1, 1])

    # =====================================================================
    # SECTION A: EVIDENCE & WORKING PAPERS WITH DAILY DATE VERSIONING
    # =====================================================================
    with col_files:
        st.markdown("##### 📁 Working Papers & Evidence Vault")
        st.caption("Automatic date-wise versioned storage: `/AuditVault_Data/engagements/.../{DD-MM-YYYY}/`")

        # Upload evidence (disabled if locked)
        if not is_locked_eng:
            with st.expander("📤 Upload New Evidence / Test Sheet", expanded=False):
                wp_file = st.file_uploader(
                    "Upload Evidence Document (Any Format)",
                    type=None,
                    key=f"wp_upload_{item.id}",
                    help="Upload test sheet, SAP screen dumps, ledger extracts, or confirmations."
                )
                wp_desc = st.text_input("Evidence Description / Testing Scope", placeholder="e.g. Sample 25 milestone contracts cut-off testing", key=f"wp_desc_{item.id}")
                
                if wp_file and st.button("Securely Vault File 🔒", key=f"wp_btn_{item.id}", type="primary"):
                    today_str = current_indian_date_str()
                    dest_dir = get_line_item_storage_dir(eng.engagement_id, eng.client.name, item.line_item_id, today_str)
                    dest_path = dest_dir / wp_file.name

                    file_size = save_uploaded_file(wp_file, dest_path)

                    wp_record = WorkingPaper(
                        engagement_id=eng.engagement_id,
                        rcm_item_id=item.id,
                        line_item_id=item.line_item_id,
                        filename=wp_file.name,
                        file_path=str(dest_path),
                        file_size_bytes=file_size,
                        version_date=today_str,
                        file_type=wp_file.type or "application/octet-stream",
                        description=wp_desc or f"Working paper for {item.line_item_id}",
                        uploaded_by_id=st.session_state.user_id,
                        uploaded_by_name=st.session_state.name,
                        uploaded_at=datetime.utcnow()
                    )
                    db.add(wp_record)
                    # Advance status to In Progress if currently Open
                    if item.status == "Open":
                        item.status = "In Progress"
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="UPLOAD_WORKING_PAPER",
                        target_entity="WorkingPaper",
                        target_id=wp_file.name,
                        description=f"Uploaded working paper '{wp_file.name}' ({format_indian_number(file_size)} bytes) to version folder '{today_str}' for line item {item.line_item_id}.",
                        user_id=st.session_state.user_id,
                        acting_user_name=st.session_state.name,
                        true_admin_id=st.session_state.true_admin_id,
                        true_admin_name=st.session_state.true_admin_name
                    )
                    st.success(f"File securely vaulted into version folder `{today_str}`!")
                    st.rerun()

        # Display Version History and Files
        st.markdown("###### 🗂️ File Version Explorer & History")
        version_folders = get_all_version_folders(eng.engagement_id, eng.client.name, item.line_item_id)
        
        if not version_folders:
            st.info("No evidence uploaded yet for this control line item.")
        else:
            for vdir in version_folders:
                folder_date = vdir.name
                files = [p for p in vdir.iterdir() if p.is_file()]
                with st.expander(f"📅 Version Date: **{folder_date}** ({len(files)} files)", expanded=(folder_date == current_indian_date_str())):
                    for fpath in files:
                        fsize_kb = max(1, int(fpath.stat().st_size / 1024))
                        st.markdown(f"📄 **{fpath.name}** `({fsize_kb} KB)`")

                        col_act1, col_act2 = st.columns(2)
                        with col_act1:
                            # Streamlit file download
                            try:
                                with open(fpath, "rb") as f_bytes:
                                    st.download_button(
                                        label="⬇️ Download",
                                        data=f_bytes.read(),
                                        file_name=fpath.name,
                                        key=f"dl_{item.id}_{folder_date}_{fpath.name}"
                                    )
                            except Exception:
                                pass

                        with col_act2:
                            # Stretch goal: Open in Native OS app (Excel/Word)
                            if st.button("🖥️ Open in Native App", key=f"open_native_{item.id}_{folder_date}_{fpath.name}"):
                                opened = open_file_in_native_app(fpath)
                                if opened:
                                    st.success("Launched in desktop application!")
                                else:
                                    st.info("Native OS launch unavailable; use download button above.")

    # =====================================================================
    # SECTION B: AUDIT OBSERVATIONS & IN-APP QUERY THREADS
    # =====================================================================
    with col_obs:
        st.markdown("##### 📝 Audit Observations")
        obs = db.query(Observation).filter(Observation.rcm_item_id == item.id).first()
        
        # Observations Form
        with st.container():
            obs_text_val = obs.observation_text if obs else ""
            risk_val = obs.risk_rating if obs else "Medium"
            rec_val = obs.recommendation if obs else ""
            mgmt_val = obs.management_response if obs else ""

            if not is_locked_eng:
                risk_sel = st.selectbox(
                    "Observation Risk Rating",
                    ["High", "Medium", "Low", "Informational"],
                    index=["High", "Medium", "Low", "Informational"].index(risk_val) if risk_val in ["High", "Medium", "Low", "Informational"] else 1,
                    key=f"obs_risk_{item.id}"
                )
                obs_text = st.text_area("Observation Details / Gaps Identified", value=obs_text_val, placeholder="Detail testing exceptions, sample sizes, and control failures...", height=120, key=f"obs_txt_{item.id}")
                rec_text = st.text_area("Audit Recommendation", value=rec_val, placeholder="Recommend corrective action or process re-engineering...", height=80, key=f"obs_rec_{item.id}")
                mgmt_text = st.text_area("Management Response / Target Action", value=mgmt_val, placeholder="Client management response, responsible person, implementation target date...", height=80, key=f"obs_mgmt_{item.id}")

                if st.button("Save Observation 💾", key=f"save_obs_{item.id}", type="primary"):
                    if not obs:
                        obs = Observation(engagement_id=eng.engagement_id, rcm_item_id=item.id)
                        db.add(obs)
                    obs.observation_text = obs_text
                    obs.risk_rating = risk_sel
                    obs.recommendation = rec_text
                    obs.management_response = mgmt_text
                    obs.updated_by_id = st.session_state.user_id
                    obs.updated_by_name = st.session_state.name
                    obs.updated_at = datetime.utcnow()
                    db.commit()

                    log_audit_action(
                        session=db,
                        action_type="RECORD_OBSERVATION",
                        target_entity="Observation",
                        target_id=item.line_item_id,
                        description=f"Saved audit observation for line item {item.line_item_id} (Rating: {risk_sel}).",
                        user_id=st.session_state.user_id,
                        acting_user_name=st.session_state.name,
                        true_admin_id=st.session_state.true_admin_id,
                        true_admin_name=st.session_state.true_admin_name
                    )
                    st.success("Observation saved successfully!")
                    st.rerun()
            else:
                # Read-only observation display
                if obs and obs.observation_text:
                    st.markdown(f"**Rating:** `{obs.risk_rating}`")
                    st.markdown(f"**Finding:** {obs.observation_text}")
                    st.markdown(f"**Recommendation:** {obs.recommendation}")
                    st.markdown(f"**Management Response:** {obs.management_response}")
                else:
                    st.info("No observations recorded.")

        st.markdown("<hr style='margin: 12px 0; border-color: rgba(100,116,139,0.15);'>", unsafe_allow_html=True)

        # In-App Comment & Query Thread (Step 6)
        st.markdown("##### 💬 Review Comments & Query Thread")
        st.caption("Direct collaboration between Manager and Auditors within the line item workspace.")

        comments = db.query(CommentThread).filter(CommentThread.rcm_item_id == item.id).order_by(CommentThread.timestamp.asc()).all()
        for c in comments:
            role_color = "#1E3A8A" if c.sender_role == "Manager" else "#0D9488"
            query_tag = " <span style='background:#EF4444; color:white; padding:1px 6px; border-radius:10px; font-size:10px;'>QUERY ❓</span>" if c.is_query and not c.is_resolved else ""
            resolved_tag = " <span style='background:#10B981; color:white; padding:1px 6px; border-radius:10px; font-size:10px;'>RESOLVED ✅</span>" if c.is_resolved else ""
            t_str = c.timestamp.strftime("%d-%m-%Y %H:%M")

            st.markdown(f"""
            <div style="background-color: rgba(255,255,255,0.04); border-left: 3px solid {role_color}; padding: 8px 12px; margin-bottom: 8px; border-radius: 4px;">
                <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                    <b>{c.sender_name} ({c.sender_role})</b>{query_tag}{resolved_tag}
                    <span style="color:#64748B;">{t_str}</span>
                </div>
                <div style="font-size:13px;">{c.message}</div>
            </div>
            """, unsafe_allow_html=True)

        # New comment input
        if not is_locked_eng:
            new_msg = st.text_input("Post message / query", placeholder="Type comment or query for this line item...", key=f"comm_inp_{item.id}")
            col_q1, col_q2 = st.columns([1, 1])
            with col_q1:
                is_q = st.checkbox("Mark as Review Query ❓", key=f"chk_q_{item.id}")
            with col_q2:
                if st.button("Send Comment 🚀", key=f"send_comm_{item.id}"):
                    if new_msg.strip():
                        comm = CommentThread(
                            engagement_id=eng.engagement_id,
                            rcm_item_id=item.id,
                            sender_id=st.session_state.user_id,
                            sender_name=st.session_state.name,
                            sender_role=st.session_state.role,
                            message=new_msg.strip(),
                            is_query=is_q,
                            is_resolved=False,
                            timestamp=datetime.utcnow()
                        )
                        db.add(comm)
                        db.commit()
                        st.rerun()
