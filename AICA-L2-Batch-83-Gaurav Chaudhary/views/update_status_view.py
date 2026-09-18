import streamlit as st
import database as db
import analytics

def render_update_status(all_assignments, current_user_name):
    st.subheader("✏️ Easy Mobile-Friendly Status Update Interface")
    st.markdown("Quickly update progress, dates, pending documents, and remarks without editing raw Excel rows.")
    
    if not all_assignments:
        st.warning("No assignments available to update.")
        return
        
    assignment_options = {a["id"]: f"#{a['id']} - {a['borrower_name']} ({a['bank_name']})" for a in all_assignments}
    selected_assign_id = st.selectbox("Select Assignment:", list(assignment_options.keys()), format_func=lambda x: assignment_options[x])
    
    item = db.get_assignment_by_id(selected_assign_id)
    if item:
        st.markdown(f"""
        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <div style="font-size: 16px; font-weight: bold; color: #1E3A8A;">Borrower: {item['borrower_name']}</div>
            <div style="font-size: 14px; color: #1E40AF;">Bank: {item['bank_name']} | Assigned: {item['team_person_name']}</div>
            <div style="font-size: 13px; color: #475569; margin-top: 5px;">
                Target Visit: <strong>{item['target_visit_date'] or 'N/A'}</strong> | Report Target: <strong>{item['report_target_date'] or 'N/A'}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("status_update_form"):
            u_col1, u_col2 = st.columns(2)
            
            with u_col1:
                current_status_idx = db.STATUS_CHOICES.index(item['audit_status']) if item['audit_status'] in db.STATUS_CHOICES else 0
                new_status = st.selectbox("Update Audit Status *", db.STATUS_CHOICES, index=current_status_idx)
                
                curr_visit = analytics.parse_date(item.get("actual_visit_date"))
                new_visit_date = st.date_input("Actual Visit Date", value=curr_visit)
                
                curr_rev = analytics.parse_date(item.get("review_partner_date"))
                new_rev_date = st.date_input("Partner Review Date", value=curr_rev)
                
            with u_col2:
                curr_sub = analytics.parse_date(item.get("report_submission_date"))
                new_sub_date = st.date_input("Report Submission Date", value=curr_sub)
                
                new_pending = st.text_area("Pending Details / Documents Awaited", value=item.get("pending_details") or "", height=85)
                new_remarks = st.text_area("Remarks / Delay Reason / Progress Notes", value=item.get("remarks") or "", height=85)
                
            submitted = st.form_submit_button("💾 Save Status Update", type="primary", use_container_width=True)
            
            if submitted:
                update_data = {
                    "audit_status": new_status,
                    "actual_visit_date": str(new_visit_date) if new_visit_date else "",
                    "review_partner_date": str(new_rev_date) if new_rev_date else "",
                    "report_submission_date": str(new_sub_date) if new_sub_date else "",
                    "pending_details": new_pending.strip(),
                    "remarks": new_remarks.strip()
                }
                db.update_assignment(selected_assign_id, update_data, user_name=current_user_name)
                st.success(f"✅ Audit Status for '{item['borrower_name']}' successfully updated and logged!")
                st.rerun()
