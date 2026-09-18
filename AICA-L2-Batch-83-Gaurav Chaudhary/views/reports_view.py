import streamlit as st
import datetime
import reports

def render_reports(all_assignments, current_user_name):
    st.subheader("📥 Export Reports & Executive MIS")
    
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        st.markdown("#### 📊 Excel Export Reports")
        excel_all = reports.export_audits_to_excel(all_assignments, "Complete")
        st.download_button(
            label="📥 Download Complete Stock Audit Tracker (.xlsx)",
            data=excel_all,
            file_name=f"Stock_Audit_Master_Tracker_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        pending_list = [a for a in all_assignments if a.get("audit_status") not in ["Report Submitted", "Closed"]]
        excel_pending = reports.export_audits_to_excel(pending_list, "Pending")
        st.download_button(
            label="📥 Download Pending Audits Report (.xlsx)",
            data=excel_pending,
            file_name=f"Pending_Stock_Audits_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        delay_list = [a for a in all_assignments if a.get("audit_status") == "Delayed"]
        excel_delay = reports.export_audits_to_excel(delay_list, "Delayed")
        st.download_button(
            label="📥 Download Delay & Escalation Analysis (.xlsx)",
            data=excel_delay,
            file_name=f"Delay_Analysis_Report_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with exp_col2:
        st.markdown("#### 📑 PDF Executive Summary Reports")
        pdf_bytes = reports.generate_dashboard_pdf(all_assignments, partner_name=current_user_name)
        st.download_button(
            label="📄 Download Partner Dashboard MIS Summary (.pdf)",
            data=pdf_bytes,
            file_name=f"Partner_Executive_MIS_{datetime.date.today()}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
