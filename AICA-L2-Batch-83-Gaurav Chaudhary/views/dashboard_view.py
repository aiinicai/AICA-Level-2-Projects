import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import analytics

def render_dashboard(all_assignments):
    st.subheader("📊 Executive Overview & Real-Time Monitoring")
    
    total_assignments = len(all_assignments)
    completed_audits = sum(1 for a in all_assignments if a.get("audit_status") in ["Report Submitted", "Closed"])
    delayed_audits = sum(1 for a in all_assignments if a.get("audit_status") == "Delayed")
    pending_audits = total_assignments - completed_audits
    reports_pending = sum(1 for a in all_assignments if a.get("audit_status") in ["Report Preparation", "Review Pending", "Partner Review Completed"])
    reports_submitted = sum(1 for a in all_assignments if a.get("audit_status") in ["Report Submitted", "Closed"])
    visits_pending = sum(1 for a in all_assignments if a.get("audit_status") in ["Not Started", "Data Awaited from Bank", "Data Awaited from Borrower", "Documents Under Review", "Visit Planned"])

    kpi_cols = st.columns(7)
    with kpi_cols[0]:
        st.markdown(f"<div class='kpi-card' style='border-left-color: #1E3A8A;'><div class='kpi-title'>Total Audits</div><div class='kpi-value'>{total_assignments}</div><div class='kpi-subtitle'>Allocated by Banks</div></div>", unsafe_allow_html=True)
    with kpi_cols[1]:
        st.markdown(f"<div class='kpi-card' style='border-left-color: #10B981;'><div class='kpi-title'>Completed</div><div class='kpi-value'>{completed_audits}</div><div class='kpi-subtitle'>Signed & Submitted</div></div>", unsafe_allow_html=True)
    with kpi_cols[2]:
        st.markdown(f"<div class='kpi-card' style='border-left-color: #3B82F6;'><div class='kpi-title'>Pending</div><div class='kpi-value'>{pending_audits}</div><div class='kpi-subtitle'>In Active Progress</div></div>", unsafe_allow_html=True)
    with kpi_cols[3]:
        st.markdown(f"<div class='kpi-card' style='border-left-color: #EF4444;'><div class='kpi-title'>Delayed</div><div class='kpi-value'>{delayed_audits}</div><div class='kpi-subtitle'>Action Required</div></div>", unsafe_allow_html=True)
    with kpi_cols[4]:
        st.markdown(f"<div class='kpi-card' style='border-left-color: #F59E0B;'><div class='kpi-title'>Reports Pending</div><div class='kpi-value'>{reports_pending}</div><div class='kpi-subtitle'>Under Review</div></div>", unsafe_allow_html=True)
    with kpi_cols[5]:
        st.markdown(f"<div class='kpi-card' style='border-left-color: #059669;'><div class='kpi-title'>Reports Submitted</div><div class='kpi-value'>{reports_submitted}</div><div class='kpi-subtitle'>Delivered to Bank</div></div>", unsafe_allow_html=True)
    with kpi_cols[6]:
        st.markdown(f"<div class='kpi-card' style='border-left-color: #8B5CF6;'><div class='kpi-title'>Visits Pending</div><div class='kpi-value'>{visits_pending}</div><div class='kpi-subtitle'>Physical Verification</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns([1, 1])
    df_all = pd.DataFrame(all_assignments) if all_assignments else pd.DataFrame()

    with col_chart1:
        st.markdown("#### 🍩 Audit Status Distribution")
        if not df_all.empty and "audit_status" in df_all.columns:
            status_counts = df_all["audit_status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig_pie = px.pie(status_counts, names="Status", values="Count", hole=0.45, color_discrete_sequence=px.colors.qualitative.Prism)
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No audit assignment data available.")

    with col_chart2:
        st.markdown("#### 🏦 Bank-Wise Pending Audits")
        if not df_all.empty and "bank_name" in df_all.columns:
            df_pending = df_all[~df_all["audit_status"].isin(["Report Submitted", "Closed"])]
            if not df_pending.empty:
                bank_counts = df_pending["bank_name"].value_counts().reset_index()
                bank_counts.columns = ["Bank", "Pending Audits"]
                fig_bar = px.bar(bank_counts, x="Pending Audits", y="Bank", orientation='h', color="Pending Audits", color_continuous_scale="Blues")
                fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.success("All bank audits are currently completed!")
        else:
            st.info("No bank data available.")

    col_chart3, col_chart4 = st.columns([1, 1])
    with col_chart3:
        st.markdown("#### 👥 Team Member-Wise Assignment Breakdown")
        if not df_all.empty and "team_person_name" in df_all.columns:
            team_counts = df_all.groupby(["team_person_name", "audit_status"]).size().reset_index(name="Count")
            fig_team = px.bar(team_counts, x="team_person_name", y="Count", color="audit_status", barmode="stack", color_discrete_sequence=px.colors.qualitative.Safe)
            fig_team.update_layout(xaxis_title="Team Member", yaxis_title="Number of Audits", margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig_team, use_container_width=True)
        else:
            st.info("No team allocation data.")

    with col_chart4:
        st.markdown("#### ⏳ Upcoming Deadlines (Next 14 Days)")
        today = datetime.date.today()
        upcoming = []
        for a in all_assignments:
            if a.get("audit_status") not in ["Report Submitted", "Closed"]:
                tgt = analytics.parse_date(a.get("report_target_date"))
                if tgt and 0 <= (tgt - today).days <= 14:
                    upcoming.append({
                        "Borrower": a.get("borrower_name"),
                        "Bank": a.get("bank_name"),
                        "Team Person": a.get("team_person_name"),
                        "Due Date": str(tgt),
                        "Days Left": (tgt - today).days,
                        "Status": a.get("audit_status")
                    })
        if upcoming:
            df_up = pd.DataFrame(upcoming).sort_values("Days Left")
            st.dataframe(df_up, use_container_width=True, height=280)
        else:
            st.info("No deadlines approaching in the next 14 days.")

    st.markdown("---")
    st.markdown("### 🚨 Critical Pending & Traffic Light Action Center")
    
    red_items, yellow_items, green_items = [], [], []
    for a in all_assignments:
        status = a.get("audit_status", "")
        borrower = a.get("borrower_name", "")
        bank = a.get("bank_name", "")
        team_person = a.get("team_person_name", "")
        visit_tgt = analytics.parse_date(a.get("target_visit_date"))
        actual_visit = analytics.parse_date(a.get("actual_visit_date"))
        report_tgt = analytics.parse_date(a.get("report_target_date"))
        submission_date = analytics.parse_date(a.get("report_submission_date"))
        
        last_update_str = a.get("last_status_update") or a.get("updated_at")
        days_inactive = 0
        if last_update_str:
            try:
                last_dt = datetime.datetime.strptime(last_update_str[:19], "%Y-%m-%d %H:%M:%S")
                days_inactive = (datetime.datetime.now() - last_dt).days
            except Exception:
                pass

        if status in ["Report Submitted", "Closed"]:
            green_items.append({
                "ID": a["id"],
                "Borrower": borrower,
                "Bank": bank,
                "Auditor": team_person,
                "Submission Date": str(submission_date or "Done"),
                "Status": status
            })
            continue

        is_red = False
        reasons = []
        if visit_tgt and not actual_visit and today > visit_tgt:
            is_red = True
            reasons.append(f"Visit overdue by {(today - visit_tgt).days} days")
        if report_tgt and today > report_tgt:
            is_red = True
            reasons.append(f"Report target crossed by {(today - report_tgt).days} days")
        if days_inactive >= 3:
            is_red = True
            reasons.append(f"No update for {days_inactive} days")
        if status == "Delayed":
            is_red = True
            reasons.append(f"Status flagged Delayed: {a.get('remarks') or 'Pending'}")
            
        if is_red:
            red_items.append({
                "ID": a["id"],
                "Borrower": borrower,
                "Bank": bank,
                "Auditor": team_person,
                "Critical Reason": " | ".join(reasons),
                "Status": status,
                "Report Target": str(report_tgt or "-")
            })
        else:
            if report_tgt and 0 <= (report_tgt - today).days <= 7:
                yellow_items.append({
                    "ID": a["id"],
                    "Borrower": borrower,
                    "Bank": bank,
                    "Auditor": team_person,
                    "Due In": f"{(report_tgt - today).days} days ({report_tgt})",
                    "Status": status,
                    "Pending Docs": a.get("pending_details") or "None"
                })

    tab_red, tab_yellow, tab_green = st.tabs([
        f"🔴 High Risk / Overdue ({len(red_items)})", 
        f"🟡 Approaching Deadline ({len(yellow_items)})", 
        f"🟢 Completed Audits ({len(green_items)})"
    ])
    with tab_red:
        if red_items:
            st.error(f"⚠️ {len(red_items)} Assignment(s) require immediate Partner intervention or Team escalation!")
            st.dataframe(pd.DataFrame(red_items), use_container_width=True)
        else:
            st.success("🎉 Excellent! No assignments are currently in the Red critical zone.")
    with tab_yellow:
        if yellow_items:
            st.warning(f"⚡ {len(yellow_items)} Assignment(s) due within next 7 days. Ensure report preparation is on schedule.")
            st.dataframe(pd.DataFrame(yellow_items), use_container_width=True)
        else:
            st.info("No upcoming deadlines in the next 7 days.")
    with tab_green:
        if green_items:
            st.dataframe(pd.DataFrame(green_items), use_container_width=True)
        else:
            st.info("No completed audits yet.")
