import calendar
import json
from collections import defaultdict
from datetime import date

import pandas as pd
import streamlit as st

from core import auth, db, duedates, ui
from core.constants import CATEGORY_TONE

from . import common


def render():
    u = common.me()
    managers = auth.sees_all_work(u)
    ver = db.get_setting("due_dates_version", "—")
    checked = db.get_setting("due_dates_checked")
    ui.header("Compliance Calendar",
              f"Statutory deadlines across all clients · due-date set version {ver}"
              + (f" · last checked {ui.ago(checked)}" if checked else ""))

    today = common.today()
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = date(today.year, today.month, 1)
    m = st.session_state.cal_month
    a, b, c, d, _ = st.columns([0.45, 2.2, 0.45, 0.8, 3.5], vertical_alignment="center")
    if a.button("◀", help="Previous month"):
        st.session_state.cal_month = date(m.year - (m.month == 1), (m.month - 2) % 12 + 1, 1); st.rerun()
    b.markdown(f"<h3 style='margin:0;padding:0;text-align:center;white-space:nowrap'>{m.strftime('%B %Y')}</h3>", unsafe_allow_html=True)
    if c.button("▶", help="Next month"):
        st.session_state.cal_month = date(m.year + (m.month == 12), m.month % 12 + 1, 1); st.rerun()
    if d.button("Today"):
        st.session_state.cal_month = date(today.year, today.month, 1); st.rerun()

    month_grid(st.session_state.cal_month)
    tracker()

    if managers:
        st.markdown("### Manage due dates")
        t1, t2, t3 = st.tabs(["Extend a due date", "Updates from GitHub", "Generate tasks for a year"])
        with t1:
            extend_form(u)
        with t2:
            github_updates(u)
        with t3:
            fy0 = duedates.current_fy_start()
            fy = st.selectbox("Financial year", [fy0 - 1, fy0, fy0 + 1], index=1,
                              format_func=lambda y: f"FY {duedates.fy_label(y)}")
            st.caption("Creates every applicable statutory task for every active client. Existing tasks are never duplicated.")
            if st.button(f"Generate tasks for FY {duedates.fy_label(fy)}", type="primary"):
                st.success(f"{duedates.generate_for_all(fy)} new task(s) created.")


@st.fragment(run_every="60s")
def month_grid(m: date):
    scope, p = common.scope_sql()
    last = date(m.year, m.month, calendar.monthrange(m.year, m.month)[1])
    rows = db.query("SELECT t.due_date, t.title, t.category, t.status FROM tasks t JOIN clients c ON c.id=t.client_id "
                    "WHERE c.active=1 AND t.due_date BETWEEN :a AND :b" + scope, a=m.isoformat(), b=last.isoformat(), **p)
    by_day = defaultdict(lambda: defaultdict(lambda: [0, 0, ""]))
    for r in rows:
        x = by_day[r["due_date"]][r["title"]]
        x[0] += 1
        x[1] += r["status"] != "Done"
        x[2] = r["category"]
    today = common.today()
    html = "<table class='pm-cal'><tr>" + "".join(f"<th>{d}</th>" for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]) + "</tr>"
    for week in calendar.Calendar().monthdatescalendar(m.year, m.month):
        html += "<tr>"
        for d in week:
            if d.month != m.month:
                html += "<td class='off'></td>"; continue
            evs = ""
            for title, (tot, open_, cat) in sorted(by_day.get(d.isoformat(), {}).items()):
                tone = "green" if open_ == 0 else ("red" if d < today else CATEGORY_TONE.get(cat, "slate"))
                bg, fg = ui.TONES[tone]
                label = title.split(" (")[0]
                evs += (f"<span class='ev' style='background:{bg};color:{fg}' title='{ui.esc(title)}: {open_} of {tot} pending'>"
                        f"{ui.esc(label)} · {open_}/{tot}</span>")
            html += f"<td class='{'today' if d == today else ''}'><div class='dn'>{d.day}</div>{evs}</td>"
        html += "</tr>"
    st.markdown(html + "</table>", unsafe_allow_html=True)
    st.caption("Each chip shows pending / total clients. Green = everyone done, red = past due with work pending.")


def tracker():
    scope, p = common.scope_sql()
    rows = db.query(
        "SELECT t.due_date, t.title, t.category, t.period, COUNT(*) AS clients, "
        "SUM(CASE WHEN t.status='Done' THEN 1 ELSE 0 END) AS done FROM tasks t JOIN clients c ON c.id=t.client_id "
        "WHERE c.active=1 AND t.rule_code IS NOT NULL" + scope +
        " GROUP BY t.due_date, t.title, t.category, t.period ORDER BY t.due_date", **p)
    if not rows:
        return
    df = pd.DataFrame(rows)
    today = common.today()
    df["due"] = pd.to_datetime(df["due_date"]).dt.date
    df["days_left"] = df["due"].map(lambda d: (d - today).days)
    df["progress"] = df["done"] / df["clients"]
    df["pending"] = df["clients"] - df["done"]
    st.markdown("### Deadline tracker")
    mode = st.segmented_control("Show", ["Next 45 days", "Past due with work pending", "Whole year"],
                                default="Next 45 days", label_visibility="collapsed") or "Next 45 days"
    if mode == "Next 45 days":
        v = df[(df["days_left"] >= 0) & (df["days_left"] <= 45)]
    elif mode.startswith("Past"):
        v = df[(df["days_left"] < 0) & (df["pending"] > 0)]
    else:
        v = df
    st.dataframe(v[["due", "days_left", "category", "title", "period", "clients", "pending", "progress"]],
                 hide_index=True, width="stretch",
                 column_config={"due": st.column_config.DateColumn("Due", format="DD MMM YYYY"),
                                "days_left": "Days left", "category": "Area", "title": "Compliance",
                                "period": "Period", "clients": "Clients", "pending": "Pending",
                                "progress": st.column_config.ProgressColumn("Completed", format="percent",
                                                                            min_value=0, max_value=1)})


def extend_form(u):
    st.caption("Use this when CBIC/CBDT extend a date. Every pending task for that return moves to the new date.")
    rules = duedates.rules()
    rmap = {r["code"]: f"{r['title']}  ({r['category']})" for r in rules}
    a, b = st.columns(2)
    code = a.selectbox("Return / compliance", list(rmap), format_func=rmap.get)
    fy0 = duedates.current_fy_start()
    fy = b.selectbox("Financial year", [fy0 - 1, fy0, fy0 + 1], index=1, format_func=lambda y: f"FY {duedates.fy_label(y)}",
                     key="ext_fy")
    periods = duedates.periods_for(code, fy)
    c, d = st.columns(2)
    sel = c.multiselect("Period(s) extended", periods)
    new = d.date_input("New due date", format="DD/MM/YYYY")
    note = st.text_input("Reference", placeholder="e.g. CBIC Notification No. xx/2026-Central Tax dated …")
    if st.button("Apply extension", type="primary", disabled=not sel):
        moved = sum(duedates.add_override(code, p, new.isoformat(), note, u["id"]) for p in sel)
        st.success(f"Extension saved. {moved} pending task(s) moved to {new.strftime('%d %b %Y')}.")
    ov = db.query("SELECT rule_code AS code, period, due_date, note FROM due_date_overrides ORDER BY due_date DESC LIMIT 20")
    if ov:
        st.markdown("**Extensions on record**")
        st.dataframe(pd.DataFrame(ov), hide_index=True, width="stretch")


def github_updates(u):
    url = db.get_setting("due_dates_url", "")
    st.markdown(
        "Keep the firm's master **due_dates.json** in your GitHub repository. When a date changes, edit that file on "
        "GitHub, increase its `version`, and every copy of the app updates. The app checks automatically every 6 hours "
        "when a partner or manager signs in, or you can check now.")
    new_url = st.text_input("Link to due_dates.json on GitHub", url,
                            placeholder="https://github.com/<you>/<repo>/blob/main/due_dates.json")
    a, b, c = st.columns([1, 1, 1.4])
    if a.button("Save link", disabled=new_url == url):
        db.set_setting("due_dates_url", new_url.strip()); st.rerun()
    if b.button("Check for updates", type="primary", disabled=not url):
        try:
            status, info = duedates.check_for_updates(u["id"], force=False)
            if status == "up_to_date":
                st.info(f"Already up to date (version {info['version']}).")
            else:
                st.success(f"Updated to version {info['version']}: {info['rules_added']} new rule(s), "
                           f"{info['rules_changed']} changed, {info['overrides']} extension(s), "
                           f"{info['tasks_moved']} pending task(s) moved.")
        except Exception as e:
            st.error(f"Couldn't read the file: {e}")
    c.download_button("Download current due_dates.json", json.dumps(duedates.export_current(), indent=2),
                      "due_dates.json", mime="application/json")
