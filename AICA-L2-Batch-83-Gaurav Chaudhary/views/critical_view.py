import streamlit as st
import pandas as pd
import datetime

def render_critical(all_assignments):
    st.subheader("⚠️ Critical & Pending Items Monitor")
    st.markdown("Dedicated operational dashboard focusing on bottlenecks, delayed documents, and pending bank inputs.")
    
    pending_bank_data = [a for a in all_assignments if a.get("audit_status") == "Data Awaited from Bank"]
    pending_borrower_data = [a for a in all_assignments if a.get("audit_status") == "Data Awaited from Borrower"]
    pending_visits = [a for a in all_assignments if not a.get("actual_visit_date") and a.get("audit_status") not in ["Report Submitted", "Closed"]]
    pending_reviews = [a for a in all_assignments if a.get("audit_status") in ["Review Pending", "Partner Review Completed", "Report Preparation"]]
    
    p_tab1, p_tab2, p_tab3, p_tab4 = st.tabs([
        f"🏦 Awaited from Bank ({len(pending_bank_data)})",
        f"🏭 Awaited from Borrower ({len(pending_borrower_data)})",
        f"🚗 Physical Visits Pending ({len(pending_visits)})",
        f"📝 Report Preparation & Review ({len(pending_reviews)})"
    ])
    with p_tab1:
        if pending_bank_data:
            st.dataframe(pd.DataFrame(pending_bank_data)[["id", "borrower_name", "bank_name", "data_req_bank_date", "team_person_name", "pending_details"]], use_container_width=True)
        else:
            st.success("No audits currently waiting for Bank data.")
    with p_tab2:
        if pending_borrower_data:
            st.dataframe(pd.DataFrame(pending_borrower_data)[["id", "borrower_name", "bank_name", "data_req_borrower_date", "team_person_name", "pending_details"]], use_container_width=True)
        else:
            st.success("No audits currently waiting for Borrower data.")
    with p_tab3:
        if pending_visits:
            st.dataframe(pd.DataFrame(pending_visits)[["id", "borrower_name", "bank_name", "target_visit_date", "team_person_name", "audit_status"]], use_container_width=True)
        else:
            st.success("All scheduled physical visits are completed!")
    with p_tab4:
        if pending_reviews:
            st.dataframe(pd.DataFrame(pending_reviews)[["id", "borrower_name", "bank_name", "report_target_date", "team_person_name", "audit_status", "remarks"]], use_container_width=True)
        else:
            st.info("No reports currently under drafting or review.")
