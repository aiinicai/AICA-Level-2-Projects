import streamlit as st
import pandas as pd
import database as db
import notifications

def render_reminders(all_assignments):
    st.subheader("🔔 Automated Reminder Engine & Escalation System")
    r_col1, r_col2 = st.columns([1, 1])
    with r_col1:
        st.markdown("#### ⚡ Run Automated Reminder Scan Now")
        if st.button("🚀 Trigger Daily Reminder Scan", type="primary", use_container_width=True):
            with st.spinner("Scanning all active assignments and checking alert conditions..."):
                results = notifications.run_automated_reminders()
                if results:
                    st.success(f"Dispatched {len(results)} automated reminder notifications!")
                    for r in results:
                        st.info(f"**{r['type']}** for **{r['borrower']}** ({r['bank']}) -> {r['recipient']} | Result: {r['detail']}")
                else:
                    st.success("All assignments are on track! No reminder conditions triggered.")
                    
    with r_col2:
        st.markdown("#### ✉️ Send Direct Custom Alert")
        if not all_assignments:
            st.info("No assignments available to alert.")
            return
            
        with st.form("custom_alert_form"):
            target_assign = st.selectbox("Select Assignment", [a["id"] for a in all_assignments], format_func=lambda x: f"#{x} - {next((a['borrower_name'] for a in all_assignments if a['id']==x), '')}")
            alert_channel = st.selectbox("Channel", ["Email", "WhatsApp / SMS"])
            custom_msg = st.text_area("Custom Notification Message", value="Please provide an urgent update on stock verification and physical tally sheet.")
            
            if st.form_submit_button("Send Custom Notification", use_container_width=True):
                chosen_a = db.get_assignment_by_id(target_assign)
                auditor_name = chosen_a.get("team_person_name", "Auditor")
                auditor_email = f"{auditor_name.lower().replace(' ', '.')}@ca-firm.com"
                
                if alert_channel == "Email":
                    notifications.send_smtp_email(auditor_email, f"Urgent Notice: {chosen_a['borrower_name']}", custom_msg)
                else:
                    notifications.send_whatsapp_or_sms(chosen_a.get("team_person_number", ""), custom_msg)
                    
                db.log_reminder(chosen_a["id"], chosen_a["borrower_name"], auditor_name, auditor_email, chosen_a.get("team_person_number", ""), "Manual Alert", custom_msg, alert_channel, "Sent")
                st.success("Custom notification dispatched and logged.")

    st.markdown("---")
    st.markdown("### 📜 Reminder History & Dispatch Log")
    reminders = db.get_reminders(limit=50)
    if reminders:
        st.dataframe(pd.DataFrame(reminders)[["sent_at", "borrower_name", "recipient_name", "reminder_type", "channel", "status", "message"]], use_container_width=True)
    else:
        st.info("No reminders sent yet.")
