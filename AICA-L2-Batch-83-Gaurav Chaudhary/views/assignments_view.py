import streamlit as st
import pandas as pd
import database as db

def render_assignments(all_assignments):
    st.subheader("📋 Stock Audit Assignment Master & Advanced Filters")
    
    with st.expander("🔍 Search & Filter Tools", expanded=True):
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            search_borrower = st.text_input("Search Borrower Name", placeholder="e.g. Acme, Surya")
        with f_col2:
            bank_list = ["All Banks"] + sorted(list(set(a.get("bank_name") for a in all_assignments if a.get("bank_name"))))
            selected_bank = st.selectbox("Filter by Bank", bank_list)
        with f_col3:
            team_list = ["All Members"] + sorted(list(set(a.get("team_person_name") for a in all_assignments if a.get("team_person_name"))))
            selected_team = st.selectbox("Filter by Auditor", team_list)
        with f_col4:
            status_list = ["All Statuses"] + db.STATUS_CHOICES
            selected_status = st.selectbox("Filter by Audit Status", status_list)
            
        search_pending_doc = st.text_input("Search in Pending Details / Documents", placeholder="e.g. GST returns, Sanction, Stock register")

    filtered = all_assignments
    if search_borrower:
        filtered = [a for a in filtered if search_borrower.lower() in a.get("borrower_name", "").lower()]
    if selected_bank != "All Banks":
        filtered = [a for a in filtered if a.get("bank_name") == selected_bank]
    if selected_team != "All Members":
        filtered = [a for a in filtered if a.get("team_person_name") == selected_team]
    if selected_status != "All Statuses":
        filtered = [a for a in filtered if a.get("audit_status") == selected_status]
    if search_pending_doc:
        filtered = [a for a in filtered if search_pending_doc.lower() in str(a.get("pending_details", "")).lower()]

    st.markdown(f"**Showing {len(filtered)} assignment(s)** matching filter criteria:")
    
    if filtered:
        display_data = []
        for a in filtered:
            display_data.append({
                "ID": a["id"],
                "Borrower Name": a.get("borrower_name"),
                "Bank Name": a.get("bank_name"),
                "Auditor": a.get("team_person_name"),
                "Allotment Date": a.get("allotment_date"),
                "Target Visit": a.get("target_visit_date"),
                "Actual Visit": a.get("actual_visit_date"),
                "Report Target": a.get("report_target_date"),
                "Audit Status": a.get("audit_status"),
                "Pending Docs": a.get("pending_details") or "-"
            })
        st.dataframe(pd.DataFrame(display_data), use_container_width=True, height=360)
        
        st.markdown("---")
        st.markdown("### 🔎 Assignment Deep Dive & Activity History")
        selected_id = st.selectbox("Select Assignment ID to inspect details:", [a["id"] for a in filtered], format_func=lambda x: f"Assignment #{x} - {next((a['borrower_name'] for a in filtered if a['id']==x), '')}")
        
        assign_detail = db.get_assignment_by_id(selected_id)
        if assign_detail:
            d_col1, d_col2 = st.columns([1, 1])
            with d_col1:
                st.markdown(f"""
                <div style="background: #FFFFFF; padding: 18px; border-radius: 8px; border: 1px solid #E2E8F0;">
                    <h4 style="color: #1E3A8A; margin-top:0;">{assign_detail['borrower_name']}</h4>
                    <p><strong>Bank:</strong> {assign_detail['bank_name']}</p>
                    <p><strong>Allotment Date:</strong> {assign_detail['allotment_date'] or '-'}</p>
                    <p><strong>Acceptance Date:</strong> {assign_detail['acceptance_date'] or '-'}</p>
                    <p><strong>Bank Data Req Date:</strong> {assign_detail['data_req_bank_date'] or '-'}</p>
                    <p><strong>Borrower Data Req Date:</strong> {assign_detail['data_req_borrower_date'] or '-'}</p>
                    <p><strong>Assigned Auditor:</strong> {assign_detail['team_person_name']} ({assign_detail['team_person_number'] or '-'})</p>
                </div>
                """, unsafe_allow_html=True)
            with d_col2:
                st.markdown(f"""
                <div style="background: #FFFFFF; padding: 18px; border-radius: 8px; border: 1px solid #E2E8F0;">
                    <h4 style="color: #1E3A8A; margin-top:0;">Timeline & Status</h4>
                    <p><strong>Audit Status:</strong> <span class="badge badge-progress">{assign_detail['audit_status']}</span></p>
                    <p><strong>Target Visit Date:</strong> {assign_detail['target_visit_date'] or '-'}</p>
                    <p><strong>Actual Visit Date:</strong> {assign_detail['actual_visit_date'] or '-'}</p>
                    <p><strong>Partner Review Date:</strong> {assign_detail['review_partner_date'] or '-'}</p>
                    <p><strong>Report Target Date:</strong> {assign_detail['report_target_date'] or '-'}</p>
                    <p><strong>Report Submission Date:</strong> {assign_detail['report_submission_date'] or '-'}</p>
                    <p><strong>Pending Documents:</strong> {assign_detail['pending_details'] or 'None'}</p>
                    <p><strong>Remarks:</strong> {assign_detail['remarks'] or 'None'}</p>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("#### 📜 Audit Log History for this Assignment")
            logs = db.get_activity_logs(limit=20, assignment_id=selected_id)
            if logs:
                st.dataframe(pd.DataFrame(logs)[["timestamp", "user_name", "action", "old_value", "new_value"]], use_container_width=True)
            else:
                st.info("No activity logs recorded yet for this assignment.")
    else:
        st.warning("No assignments matched the search criteria.")
