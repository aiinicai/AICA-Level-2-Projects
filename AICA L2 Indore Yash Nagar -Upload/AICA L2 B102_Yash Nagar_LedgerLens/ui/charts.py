"""Dashboards drawn with Altair. The numbers come from daybook_auditor.analytics and fsbuilder.analytics."""
import altair as alt
import pandas as pd
import streamlit as st

from daybook_auditor.analytics import SEVERITY_ORDER, daybook_dashboard
from fsbuilder.analytics import fs_dashboard
from fsbuilder.format import inr

SEVERITY = alt.Scale(domain=SEVERITY_ORDER, range=["#DC2626", "#F59E0B", "#FACC15"])
INK, GOOD, BAD, MUTED = "#1F2A44", "#16A34A", "#DC2626", "#94A3B8"


def _bar(df, x, y, colour=INK, h=300, fmt=",.0f", title=None):
    base = alt.Chart(df).mark_bar(color=colour, cornerRadiusEnd=3).encode(
        y=alt.Y(f"{y}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=240)),
        x=alt.X(f"{x}:Q", title=title, axis=alt.Axis(format="~s")),
        tooltip=[alt.Tooltip(f"{y}:N"), alt.Tooltip(f"{x}:Q", format=fmt)])
    return base.properties(height=h)


def _kpi(col, label, value, help=None):
    col.metric(label, value, help=help)


def daybook(df, findings):
    d = daybook_dashboard(df, findings)
    k = d["kpis"]
    c = st.columns(5)
    _kpi(c[0], "Vouchers", f"{k['vouchers']:,}")
    _kpi(c[1], "Value (excl. contra)", inr(round(k["value"])))
    _kpi(c[2], "Vouchers flagged", f"{k['flagged_vouchers']:,} ({k['flagged_share']:.0%})")
    _kpi(c[3], "Value flagged", inr(round(k["flagged_value"])))
    _kpi(c[4], "Vouchers with a High finding", f"{k['high_vouchers']:,}")
    if k["undated"]:
        st.caption(f"{k['undated']} voucher(s) have no usable date, so they are left out of the month charts.")

    a, b = st.columns(2)
    with a:
        st.markdown("**Findings by test family and severity**")
        if len(d["severity_by_family"]):
            st.altair_chart(alt.Chart(d["severity_by_family"]).mark_bar().encode(
                y=alt.Y("family:N", title=None, sort="-x"), x=alt.X("findings:Q", title="Findings"),
                color=alt.Color("severity:N", scale=SEVERITY, title="Severity"),
                tooltip=["family", "severity", "findings"]).properties(height=240), width="stretch")
        else:
            st.success("No findings.")
    with b:
        st.markdown("**Vouchers by type: value and share flagged**")
        t = d["by_type"].assign(share=lambda x: x["flagged"] / x["vouchers"])
        st.altair_chart(alt.Chart(t).mark_bar(color=INK, cornerRadiusEnd=3).encode(
            y=alt.Y("vch_type:N", sort="-x", title=None), x=alt.X("value:Q", title="Value (Rs)", axis=alt.Axis(format="~s")),
            tooltip=[alt.Tooltip("vch_type:N", title="Type"), alt.Tooltip("vouchers:Q"), alt.Tooltip("value:Q", format=",.0f"),
                     alt.Tooltip("flagged:Q", title="Flagged"), alt.Tooltip("share:Q", format=".0%", title="Share flagged")]
        ).properties(height=240), width="stretch")

    a, b = st.columns(2)
    with a:
        st.markdown("**Most frequent checks**")
        if len(d["top_rules"]):
            st.altair_chart(alt.Chart(d["top_rules"]).mark_bar().encode(
                y=alt.Y("rule:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)), x=alt.X("findings:Q", title="Findings"),
                color=alt.Color("severity:N", scale=SEVERITY, legend=None), tooltip=["rule", "severity", "findings"]
            ).properties(height=300), width="stretch")
    with b:
        st.markdown("**Top parties by value**")
        if len(d["top_parties"]):
            tp = d["top_parties"]
            st.altair_chart(alt.Chart(tp).mark_bar(cornerRadiusEnd=3).encode(
                y=alt.Y("party:N", sort="-x", title=None, axis=alt.Axis(labelLimit=240)),
                x=alt.X("value:Q", title="Value (Rs)", axis=alt.Axis(format="~s")),
                color=alt.condition(alt.datum.flagged > 0, alt.value(BAD), alt.value(INK)),
                tooltip=["party", alt.Tooltip("value:Q", format=",.0f"), "vouchers", "flagged"]).properties(height=300), width="stretch")
            st.caption("Red: the party appears on at least one flagged voucher.")

    if d["monthly"] is not None:
        st.markdown("**Month by month**")
        a, b = st.columns(2)
        m = d["monthly"]
        a.altair_chart(alt.Chart(m).mark_bar(color=INK).encode(
            x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y")), y=alt.Y("value:Q", title="Value (Rs)", axis=alt.Axis(format="~s")),
            tooltip=[alt.Tooltip("month:T", format="%B %Y"), "vouchers", alt.Tooltip("value:Q", format=",.0f"), "flagged"]
        ).properties(height=240), width="stretch")
        if d["findings_by_month"] is not None:
            b.altair_chart(alt.Chart(d["findings_by_month"]).mark_bar().encode(
                x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %y")), y=alt.Y("findings:Q", title="Findings"),
                color=alt.Color("severity:N", scale=SEVERITY, legend=None), tooltip=[alt.Tooltip("month:T", format="%B %Y"), "severity", "findings"]
            ).properties(height=240), width="stretch")
    return d


def statements(model, review):
    d = fs_dashboard(model, review)
    u, k = d["unit"], d["kpis"]
    show = u.fmt
    st.caption(u.heading + ".")
    if review is not None:
        st.caption(("AI review run: " + f"{len(review.ai.observations)} observation(s) and reasons for the flagged ratios are on the AI review tab."
                    ) if review.ai_requested else "AI review not run: every figure here is computed by code. The AI review tab explains what the AI would add.")
    c = st.columns(5)
    _kpi(c[0], "Revenue", show(k["revenue"]))
    _kpi(c[1], "Profit for the year", show(k["profit"]), f"Margin {k['margin']:.1%}" if k["margin"] is not None else None)
    _kpi(c[2], "Total assets", show(k["total_assets"]))
    _kpi(c[3], "Net worth", show(k["equity"]))
    _kpi(c[4], "Cash from operations", show(k["cfo"]))
    c = st.columns(5)
    _kpi(c[0], "Net margin", f"{k['margin']:.1%}" if k["margin"] is not None else "n/a")
    _kpi(c[1], "Current ratio", f"{k['current_ratio']:.2f}" if k["current_ratio"] is not None else "n/a")
    _kpi(c[2], "Debt-equity", f"{k['debt_equity']:.2f}" if k["debt_equity"] is not None else "n/a")
    _kpi(c[3], "Receivable days", k["receivable_days"] if k["receivable_days"] is not None else "n/a", "Year-end receivables / revenue x 365")
    _kpi(c[4], "Cash and bank", show(k["cash"]))

    a, b = st.columns(2)
    with a:
        st.markdown("**Profit and loss: income, costs and profit**")
        p = d["pl_bridge"]
        st.altair_chart(alt.Chart(p).mark_bar(cornerRadiusEnd=3).encode(
            y=alt.Y("item:N", sort=list(p["item"]), title=None, axis=alt.Axis(labelLimit=220)),
            x=alt.X("amount:Q", title=None, axis=alt.Axis(format="~s")),
            color=alt.Color("kind:N", scale=alt.Scale(domain=["Income", "Cost", "Profit"], range=[GOOD, MUTED, INK]), legend=None),
            tooltip=["item", alt.Tooltip("amount:Q", format=",.2f")]).properties(height=300), width="stretch")
    with b:
        st.markdown("**Cash flow: opening to closing cash**")
        cb = d["cash_bridge"].copy()
        run, starts = 0, []
        for _, r in cb.iterrows():
            if r["kind"] == "Balance":
                starts.append(0)
                run = r["amount"]
            else:
                starts.append(run)
                run += r["amount"]
        cb["start"] = starts
        cb["stop"] = [r["amount"] if r["kind"] == "Balance" else s + r["amount"] for (_, r), s in zip(cb.iterrows(), starts)]
        cb["colour"] = ["Balance" if r["kind"] == "Balance" else ("Inflow" if r["amount"] >= 0 else "Outflow") for _, r in cb.iterrows()]
        st.altair_chart(alt.Chart(cb).mark_bar(cornerRadius=2).encode(
            x=alt.X("step:N", sort=list(cb["step"]), title=None, axis=alt.Axis(labelAngle=-20, labelLimit=140)),
            y=alt.Y("start:Q", title=None, axis=alt.Axis(format="~s")), y2="stop:Q",
            color=alt.Color("colour:N", scale=alt.Scale(domain=["Balance", "Inflow", "Outflow"], range=[INK, GOOD, BAD]), legend=None),
            tooltip=["step", alt.Tooltip("amount:Q", format=",.2f")]).properties(height=300), width="stretch")

    a, b = st.columns(2)
    for col, key, title in ((a, "assets", "**What the assets are**"), (b, "funding", "**How the business is funded**")):
        with col:
            st.markdown(title)
            df = d[key]
            if len(df):
                st.altair_chart(alt.Chart(df).mark_arc(innerRadius=55).encode(
                    theta="amount:Q", color=alt.Color("item:N", title=None, legend=alt.Legend(orient="bottom", columns=2)),
                    tooltip=["item", alt.Tooltip("amount:Q", format=",.2f")]).properties(height=300), width="stretch")

    a, b = st.columns(2)
    with a:
        st.markdown("**Largest expense heads**")
        if len(d["top_expenses"]):
            st.altair_chart(_bar(d["top_expenses"], "amount", "item", h=300), width="stretch")
    with b:
        st.markdown("**Working capital days (year-end balances)**")
        if len(d["working_capital"]):
            st.altair_chart(alt.Chart(d["working_capital"]).mark_bar(color=INK, cornerRadiusEnd=3).encode(
                x=alt.X("measure:N", title=None, sort=None), y=alt.Y("days:Q", title="Days"),
                tooltip=["measure", "days"]).properties(height=300), width="stretch")
    st.markdown("**Current year against previous year**")
    st.altair_chart(alt.Chart(d["balance_sheet_change"]).mark_bar().encode(
        x=alt.X("item:N", title=None, sort=None), xOffset="year:N", y=alt.Y("amount:Q", title=None, axis=alt.Axis(format="~s")),
        color=alt.Color("year:N", scale=alt.Scale(domain=["Previous year", "Current year"], range=[MUTED, INK]), title=None),
        tooltip=["item", "year", alt.Tooltip("amount:Q", format=",.2f")]).properties(height=260), width="stretch")
    h = d["health"]
    if h:
        st.markdown("**Review health**")
        order = ["Complete", "Observation", "Partly provided", "Information required", "Applies (likely)", "Exempt (likely)", "Not applicable"]
        hc = pd.DataFrame([(s, h["checklist"].get(s, 0)) for s in order if h["checklist"].get(s, 0)], columns=["status", "items"])
        a, b = st.columns([1, 2])
        a.metric("Tie-outs", f"{h['passed']} passed", f"{h['failed']} failed" if h["failed"] else "none failed", delta_color="inverse")
        b.altair_chart(alt.Chart(hc).mark_bar(color=INK, cornerRadiusEnd=3).encode(
            y=alt.Y("status:N", sort=None, title=None), x=alt.X("items:Q", title="Checklist items"),
            tooltip=["status", "items"]).properties(height=200), width="stretch")
    return d
