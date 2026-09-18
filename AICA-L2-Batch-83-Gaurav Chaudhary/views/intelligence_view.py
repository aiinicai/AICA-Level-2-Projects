import streamlit as st
import pandas as pd
import plotly.express as px
import analytics

def render_intelligence(all_assignments):
    st.subheader("📈 AI Delay Prediction & CA Firm Performance Intelligence")
    
    st.markdown("### 🤖 Automatic Delay Prediction Engine")
    pred_data = []
    for a in all_assignments:
        pred = analytics.compute_delay_prediction(a)
        pred_data.append({
            "ID": a["id"],
            "Borrower": a.get("borrower_name"),
            "Bank": a.get("bank_name"),
            "Auditor": a.get("team_person_name"),
            "Status": a.get("audit_status"),
            "Target Date": a.get("report_target_date") or "-",
            "Delay Risk Level": pred["risk_level"],
            "Risk Score": f"{pred['risk_score']}%",
            "Prediction Insight": pred["prediction"]
        })
    if pred_data:
        df_pred = pd.DataFrame(pred_data)
        st.dataframe(df_pred, use_container_width=True)
        
    st.markdown("---")
    st.markdown("### 🏆 Team Productivity & On-Time Performance Scorecard")
    df_prod = analytics.compute_team_productivity(all_assignments)
    if not df_prod.empty:
        st.dataframe(df_prod, use_container_width=True)
        fig_score = px.bar(df_prod, x="Team Member", y="Productivity Score (%)", color="Productivity Score (%)", color_continuous_scale="Greens", title="Productivity Rating by Team Member")
        fig_score.update_layout(height=300)
        st.plotly_chart(fig_score, use_container_width=True)
    else:
        st.info("No team performance data available.")

    st.markdown("---")
    st.markdown("### ⏱️ Bank-Wise Turnaround Time (TAT) Benchmarks")
    df_tat = analytics.compute_bank_turnaround_times(all_assignments)
    if not df_tat.empty:
        st.dataframe(df_tat, use_container_width=True)
    else:
        st.info("No bank TAT data available.")

    st.markdown("---")
    st.markdown("### 📅 Monthly MIS Summary")
    df_mis = analytics.generate_monthly_mis(all_assignments)
    if not df_mis.empty:
        st.dataframe(df_mis, use_container_width=True)
    else:
        st.info("No monthly MIS records available.")
