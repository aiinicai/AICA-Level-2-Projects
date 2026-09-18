import streamlit as st
import datetime
import database as db

def render_new_allocation(current_user_name):
    st.subheader("➕ Allocate New Stock Audit Assignment")
    
    team_users = db.get_users()
    team_names = [u["full_name"] for u in team_users if u["status"] == "Active"]
    
    with st.form("new_assignment_form"):
        n_col1, n_col2 = st.columns(2)
        with n_col1:
            borrower_name = st.text_input("Borrower Company / Firm Name *", placeholder="e.g. Reliance Polyesters Ltd")
            bank_name = st.selectbox("Allocating Bank Name *", [
                "State Bank of India", "Punjab National Bank", "Bank of Baroda",
                "HDFC Bank", "ICICI Bank", "Canara Bank", "Union Bank of India",
                "Axis Bank", "Bank of India", "Kotak Mahindra Bank", "Other Bank"
            ])
            if bank_name == "Other Bank":
                bank_name = st.text_input("Enter Custom Bank Name")
                
            allotment_date = st.date_input("Allotment Letter Date", value=datetime.date.today())
            acceptance_date = st.date_input("Acceptance Letter Date", value=datetime.date.today())
            data_req_bank = st.date_input("Data Requirement Sent Date (Bank)", value=datetime.date.today())
            data_req_borrower = st.date_input("Data Requirement Sent Date (Borrower)", value=datetime.date.today())
            
        with n_col2:
            assigned_person = st.selectbox("Assign to Team Member *", team_names if team_names else ["Priya Verma", "Amit Gupta", "Sneha Patel"])
            
            selected_user_obj = next((u for u in team_users if u["full_name"] == assigned_person), None)
            assigned_mobile = selected_user_obj.get("mobile", "") if selected_user_obj else ""
            team_mobile = st.text_input("Team Member Mobile", value=assigned_mobile)
            
            target_visit_date = st.date_input("Target Visit Date", value=datetime.date.today() + datetime.timedelta(days=7))
            report_target_date = st.date_input("Report Target Date", value=datetime.date.today() + datetime.timedelta(days=14))
            
            initial_status = st.selectbox("Initial Audit Status", db.STATUS_CHOICES, index=0)
            pending_docs = st.text_input("Initial Pending Documents List", placeholder="e.g. Sanction letter, Audited financials")
            remarks = st.text_area("Remarks / Special Bank Instructions", placeholder="e.g. Special focus on slow moving inventory")
            
        create_btn = st.form_submit_button("🚀 Create & Allocate Assignment", type="primary", use_container_width=True)
        if create_btn:
            if not borrower_name or not bank_name:
                st.error("Borrower Name and Bank Name are required.")
            else:
                new_data = {
                    "borrower_name": borrower_name.strip(),
                    "bank_name": bank_name.strip(),
                    "allotment_date": str(allotment_date),
                    "acceptance_date": str(acceptance_date),
                    "data_req_bank_date": str(data_req_bank),
                    "data_req_borrower_date": str(data_req_borrower),
                    "pending_details": pending_docs.strip(),
                    "team_person_name": assigned_person,
                    "team_person_number": team_mobile.strip(),
                    "target_visit_date": str(target_visit_date),
                    "actual_visit_date": "",
                    "audit_status": initial_status,
                    "review_partner_date": "",
                    "report_target_date": str(report_target_date),
                    "report_submission_date": "",
                    "remarks": remarks.strip()
                }
                new_id = db.create_assignment(new_data, user_name=current_user_name)
                st.success(f"🎉 Stock audit assignment for '{borrower_name}' created successfully with Assignment ID #{new_id}!")
