"""
AuditVault - Risk Control Matrix (RCM) Module
File upload & parsing (Excel, CSV, DOCX), unique Line Item ID generator,
field-level lock & manager override controls, and role-based permissions.
"""

import pandas as pd
import streamlit as st
from datetime import datetime
from models import Engagement, RCMLineItem, User, EngagementTeamAssignment
from utils import (
    save_uploaded_file, get_rcm_storage_dir, log_audit_action,
    format_indian_date
)
from styles import render_status_badge
from auth import is_manager, is_team_member


def render_rcm_workspace(db, eng: Engagement):
    """Render the full RCM management workspace."""
    st.markdown(f"### 🛡️ Risk Control Matrix (RCM) - [{eng.engagement_code}]")
    st.markdown(f"*Client: **{eng.client.name}** | Process: **{eng.process_under_audit}***")
    st.markdown("<hr style='margin: 8px 0 16px 0; border-color: rgba(100,116,139,0.2);'>", unsafe_allow_html=True)

    rcm_items = db.query(RCMLineItem).filter(RCMLineItem.engagement_id == eng.engagement_id).all()
    total_items = len(rcm_items)

    # Status KPI summary
    open_cnt = sum(1 for r in rcm_items if r.status == "Open")
    prog_cnt = sum(1 for r in rcm_items if r.status == "In Progress")
    review_cnt = sum(1 for r in rcm_items if r.status == "Under Review")
    reviewed_cnt = sum(1 for r in rcm_items if r.status == "Reviewed" or r.review_status == "Reviewed")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Line Items", str(total_items))
    c2.metric("Testing In Progress 🔄", str(prog_cnt))
    c3.metric("Under Review 🔍", str(review_cnt))
    c4.metric("Reviewed & Approved ✅", str(reviewed_cnt))

    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Manager Actions: Upload / Template Loading
    if is_manager() and not eng.is_locked:
        with st.expander("📥 Upload RCM Document / Import Template (Manager Controls)", expanded=(total_items == 0)):
            c_up, c_tpl = st.columns([2, 1])
            with c_up:
                uploaded_rcm = st.file_uploader(
                    "Upload RCM Spreadsheet (Excel or CSV)",
                    type=["xlsx", "xls", "csv", "docx"],
                    key=f"rcm_uploader_{eng.engagement_id}"
                )
                if uploaded_rcm and st.button("Parse RCM into AuditVault 🚀", type="primary"):
                    parse_and_load_rcm_file(db, eng, uploaded_rcm)

            with c_tpl:
                st.markdown("##### ⚡ Standard Industry Templates")
                st.caption("Auto-populate standard risk control matrices aligned with ICAI & COSO frameworks:")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("Load IFC Controls"):
                        load_standard_rcm_template(db, eng, "IFC")
                with col_b2:
                    if st.button("Load P2P Controls"):
                        load_standard_rcm_template(db, eng, "P2P")
                if st.button("Load ITGC Matrix"):
                    load_standard_rcm_template(db, eng, "ITGC")

    # Finalize RCM / Transition Status (Manager only)
    if is_manager() and total_items > 0 and eng.status in ["Draft", "Assigned"]:
        st.info("💡 **Ready to begin audit testing?** Finalizing the RCM locks the baseline and transitions the engagement to **'In Progress'**.")
        if st.button("Finalize RCM & Start Fieldwork 🚀", type="primary"):
            eng.status = "In Progress"
            db.commit()
            log_audit_action(
                session=db,
                action_type="FINALIZE_RCM",
                target_entity="RCM",
                target_id=eng.engagement_code,
                description=f"Manager finalized RCM with {total_items} line items. Engagement transitioned to 'In Progress'.",
                user_id=st.session_state.user_id,
                acting_user_name=st.session_state.name,
                true_admin_id=st.session_state.true_admin_id,
                true_admin_name=st.session_state.true_admin_name
            )
            st.success("RCM Finalized! Fieldwork workspace is now fully active.")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Line Items Display with Field-Level Manager Lock Hierarchy
    st.markdown("### 📋 Risk Control Matrix Line Items")
    if not rcm_items:
        st.info("No RCM line items present. Please upload or load an RCM template above.")
        return

    # Team members available for assignment
    assigned_auditors = [a.user for a in eng.team_assignments]
    auditor_map = {f"{u.name} ({u.role})": u.user_id for u in assigned_auditors}
    auditor_map["Unassigned"] = None

    for idx, item in enumerate(rcm_items):
        with st.container():
            render_rcm_line_item_card(db, eng, item, auditor_map, idx)


def render_rcm_line_item_card(db, eng: Engagement, item: RCMLineItem, auditor_map: dict, idx: int):
    """
    Render individual RCM line item card with field-level manager lock indicators.
    Permission Rule: If manager locked, team members cannot modify control descriptions.
    """
    is_mgr = is_manager()
    is_team = is_team_member()
    is_locked = item.manager_locked
    card_border = "#F59E0B" if is_locked else "#E2E8F0"

    # Status badge
    status_html = render_status_badge(item.status)
    lock_badge = "<span style='color: #4F46E5; font-weight: 700; font-size: 12px; background: rgba(79, 70, 229, 0.1); padding: 2px 8px; border-radius: 12px;'>🔒 MANAGER LOCKED</span>" if is_locked else ""

    st.markdown(f"""
    <div style="border-left: 4px solid {card_border}; padding-left: 12px; margin-bottom: 8px;">
        <span style="font-size: 16px; font-weight: 800; color: #1E3A8A;">[{item.line_item_id}] {item.process_area}</span>
        &nbsp;&nbsp;{status_html}&nbsp;&nbsp;{lock_badge}
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown(f"**Risk [{item.risk_id or 'N/A'}]:** {item.risk_description}")
        
        # Display Control Description with Lock Styling
        if is_locked and is_team:
            # Field is read-only for team members
            st.markdown(f"""
            <div class="manager-locked-box">
                <div class="lock-indicator">🔒 Locked by Audit Manager (Read-Only)</div>
                <b>Control [{item.control_id or 'CTL'}]:</b> {item.control_description}
                <br><small style="color: #64748B;"><b>Audit Procedure:</b> {item.audit_procedure}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Manager or unlocked view
            st.markdown(f"**Control [{item.control_id or 'CTL'}]:** {item.control_description}")
            st.markdown(f"**Audit Procedure:** *{item.audit_procedure or 'Standard substantive testing.'}*")

        if item.manager_notes:
            st.caption(f"📌 **Manager Guidance:** {item.manager_notes}")

    with col2:
        st.markdown(f"**Control Type:** `{item.control_type}`")
        resp_name = item.assigned_person.name if item.assigned_person else "Unassigned"
        st.markdown(f"**Responsible Auditor:** **{resp_name}**")

        # Edit controls / Status Update
        if not eng.is_locked:
            with st.expander(f"⚙️ Manage Line Item {item.line_item_id}", expanded=False):
                new_status = st.selectbox(
                    "Testing Status",
                    ["Open", "In Progress", "Under Review", "Reviewed", "Closed"],
                    index=["Open", "In Progress", "Under Review", "Reviewed", "Closed"].index(item.status) if item.status in ["Open", "In Progress", "Under Review", "Reviewed", "Closed"] else 0,
                    key=f"status_sel_{item.id}"
                )

                # Manager Lock Toggle (Manager Only)
                new_lock_state = item.manager_locked
                if is_mgr:
                    new_lock_state = st.checkbox(
                        "🔒 Lock Line Item from Team Overwrite",
                        value=item.manager_locked,
                        key=f"lock_chk_{item.id}",
                        help="When locked, engagement team members cannot alter the risk/control specifications."
                    )
                    mgr_notes_edit = st.text_area("Manager Instructions", value=item.manager_notes or "", key=f"mgr_note_{item.id}")

                if st.button("Save Changes 💾", key=f"save_line_{item.id}"):
                    # Permission enforcement
                    if is_team and item.manager_locked and item.status != new_status:
                        # Team can only update status
                        item.status = new_status
                    elif is_mgr:
                        item.status = new_status
                        item.manager_locked = new_lock_state
                        item.manager_notes = mgr_notes_edit

                    db.commit()
                    log_audit_action(
                        session=db,
                        action_type="EDIT_RCM_LINE",
                        target_entity="RCM",
                        target_id=item.line_item_id,
                        description=f"Updated line item {item.line_item_id}: Status={new_status}, Locked={item.manager_locked}",
                        user_id=st.session_state.user_id,
                        acting_user_name=st.session_state.name,
                        true_admin_id=st.session_state.true_admin_id,
                        true_admin_name=st.session_state.true_admin_name
                    )
                    st.success("Line item updated!")
                    st.rerun()

    st.markdown("<hr style='margin: 8px 0; border-color: rgba(100,116,139,0.15);'>", unsafe_allow_html=True)


# =====================================================================
# RCM PARSING AND TEMPLATE INGESTION
# =====================================================================

def parse_and_load_rcm_file(db, eng: Engagement, uploaded_file):
    """Parse uploaded RCM Excel/CSV and generate unique Line Item IDs."""
    filename = uploaded_file.name.lower()
    rcm_dir = get_rcm_storage_dir(eng.engagement_id)
    save_uploaded_file(uploaded_file, rcm_dir / uploaded_file.name)

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            st.warning("Please upload Excel (.xlsx) or CSV format for RCM matrix.")
            return

        records_added = ingest_dataframe_to_rcm(db, eng, df)
        log_audit_action(
            session=db,
            action_type="RCM_UPLOAD",
            target_entity="RCM",
            target_id=eng.engagement_code,
            description=f"Uploaded and parsed RCM spreadsheet '{uploaded_file.name}' with {records_added} controls.",
            user_id=st.session_state.user_id,
            acting_user_name=st.session_state.name,
            true_admin_id=st.session_state.true_admin_id,
            true_admin_name=st.session_state.true_admin_name
        )
        st.success(f"Successfully loaded {records_added} RCM controls!")
        st.rerun()
    except Exception as e:
        st.error(f"Error parsing RCM file: {e}")


def ingest_dataframe_to_rcm(db, eng: Engagement, df: pd.DataFrame) -> int:
    """Ingest dataframe rows into RCMLineItem with auto-generated unique IDs."""
    cols = {c.lower().strip(): c for c in df.columns}
    
    # Heuristics for mapping columns
    def find_col(candidates, default_idx=0):
        for cand in candidates:
            if cand in cols:
                return cols[cand]
        return df.columns[default_idx] if len(df.columns) > default_idx else None

    proc_col = find_col(["process", "process area", "sub process", "area"])
    risk_col = find_col(["risk", "risk description", "risk title"], 1)
    ctl_col = find_col(["control", "control description", "internal control"], 2)
    proc_test_col = find_col(["audit procedure", "test procedure", "testing steps", "procedure"], 3)
    type_col = find_col(["control type", "type", "nature"])

    existing_count = db.query(RCMLineItem).filter(RCMLineItem.engagement_id == eng.engagement_id).count()
    count = 0

    for _, row in df.iterrows():
        risk_desc = str(row[risk_col]).strip() if risk_col and pd.notna(row[risk_col]) else ""
        ctl_desc = str(row[ctl_col]).strip() if ctl_col and pd.notna(row[ctl_col]) else ""
        if not risk_desc and not ctl_desc:
            continue

        count += 1
        line_item_id = f"AREA-{existing_count + count:02d}"
        proc_area = str(row[proc_col]).strip() if proc_col and pd.notna(row[proc_col]) else eng.process_under_audit
        ctl_type = str(row[type_col]).strip() if type_col and pd.notna(row[type_col]) else "Preventive"
        audit_proc = str(row[proc_test_col]).strip() if proc_test_col and pd.notna(row[proc_test_col]) else "Substantive test of details and design effectiveness."

        rcm_row = RCMLineItem(
            engagement_id=eng.engagement_id,
            line_item_id=line_item_id,
            process_area=proc_area,
            risk_id=f"RSK-{count:02d}",
            risk_description=risk_desc or "Risk of misstatement or operational deficiency.",
            control_id=f"CTL-{count:02d}",
            control_description=ctl_desc or "Standard managerial review and control check.",
            control_type=ctl_type,
            audit_procedure=audit_proc,
            status="Open",
            manager_locked=False,
            review_status="Pending"
        )
        db.add(rcm_row)

    db.commit()
    return count


def load_standard_rcm_template(db, eng: Engagement, template_type: str):
    """Load standard pre-defined RCM templates (IFC, P2P, ITGC)."""
    db.query(RCMLineItem).filter(RCMLineItem.engagement_id == eng.engagement_id).delete()

    templates = {
        "IFC": [
            ("FIN-01", "Revenue Recognition & Milestone Invoicing", "RSK-01", "Revenue recognized prior to performance obligation satisfaction under Ind AS 115.", "CTL-01", "SAP billing block released only on signed Delivery Acceptance Certificate.", "Preventive", "Sample 25 revenue entries > ₹ 10 Lakhs. Verify milestone sign-offs."),
            ("FIN-02", "Credit Notes & Billing Adjustments", "RSK-02", "Unapproved credit notes issued to mask bad debts or fictitious billing.", "CTL-02", "Credit notes > ₹ 2 Lakhs mandate dual approval from Business Unit Head and CFO.", "Preventive", "Inspect 100% credit notes issued during period against DOA thresholds."),
            ("FIN-03", "Accounts Receivable & Provisioning", "RSK-03", "Overdue debtors > 180 days not provisioned per ECL guidelines.", "CTL-03", "Monthly aging analysis reviewed by Credit Committee; automated ECL calculation.", "Detective", "Recalculate ECL matrix across aging buckets and verify write-offs.")
        ],
        "P2P": [
            ("P2P-01", "Vendor Onboarding & Due Diligence", "RSK-01", "Fictitious vendors created in ERP leading to unauthorized fund transfers.", "CTL-01", "Vendor creation requires independent GST verification, PAN check, and 2-tier approval.", "Preventive", "Sample 15 new vendors. Cross-verify with MCA / GST portal records."),
            ("P2P-02", "Purchase Order Generation & Approvals", "RSK-02", "PO split to bypass DOA approval thresholds.", "CTL-02", "Automated system control checks total vendor PO volume; split POs automatically flagged.", "Detective", "Run duplicate PO and split-value analysis on ERP procurement dump."),
            ("P2P-03", "3-Way Invoice Matching & Payment", "RSK-03", "Invoices paid without verified physical receipt of goods (GRN).", "CTL-03", "ERP enforces 3-way match: PO, GRN, and Vendor Invoice before payment release.", "Preventive", "Test 30 payment vouchers. Validate GRN number and warehouse sign-off.")
        ],
        "ITGC": [
            ("IT-01", "User Access Management & Privileges", "RSK-01", "Terminated employees retain active ERP access; unauthorized privilege escalation.", "CTL-01", "HR exit trigger automatically revokes ERP credentials within 24 hours.", "Preventive", "Match HR exit list of 50 employees against ERP active user directory."),
            ("IT-02", "Change Management & Code Promotion", "RSK-02", "Untested program modifications promoted directly into production environment.", "CTL-02", "Change Advisory Board (CAB) review and UAT sign-off required prior to transport.", "Preventive", "Inspect CAB minutes and test transport logs for all emergency changes."),
            ("IT-03", "Backup & Disaster Recovery (DR)", "RSK-03", "Backup failures go undetected; data loss during system outage.", "CTL-03", "Daily automated backup verification logs; quarterly DR drill restoration testing.", "Detective", "Inspect daily backup logs and latest DR drill restoration report.")
        ]
    }

    selected_list = templates.get(template_type, templates["IFC"])
    for lid, p_area, r_id, r_desc, c_id, c_desc, c_type, a_proc in selected_list:
        db.add(RCMLineItem(
            engagement_id=eng.engagement_id,
            line_item_id=lid,
            process_area=p_area,
            risk_id=r_id,
            risk_description=r_desc,
            control_id=c_id,
            control_description=c_desc,
            control_type=c_type,
            audit_procedure=a_proc,
            status="Open",
            manager_locked=True if is_manager() else False,
            review_status="Pending"
        ))

    db.commit()
    log_audit_action(
        session=db,
        action_type="LOAD_STANDARD_RCM",
        target_entity="RCM",
        target_id=eng.engagement_code,
        description=f"Loaded standard '{template_type}' RCM template with {len(selected_list)} line items.",
        user_id=st.session_state.user_id,
        acting_user_name=st.session_state.name,
        true_admin_id=st.session_state.true_admin_id,
        true_admin_name=st.session_state.true_admin_name
    )
    st.success(f"Standard {template_type} RCM Template Loaded successfully!")
    st.rerun()
