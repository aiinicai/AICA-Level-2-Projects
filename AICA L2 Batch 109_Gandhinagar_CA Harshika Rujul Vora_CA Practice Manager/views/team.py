from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from core import db, ui

from . import common


def render():
    ui.header("Team", "Who is working on what, right now")
    live_team()


@st.fragment(run_every=common.REFRESH)
def live_team():
    today = common.today()
    t0 = today.isoformat()
    m0 = today.replace(day=1).isoformat()
    people = db.query(
        "SELECT u.id, u.name, u.role, "
        "SUM(CASE WHEN t.status<>'Done' THEN 1 ELSE 0 END) AS open_, "
        "SUM(CASE WHEN t.status='In Progress' THEN 1 ELSE 0 END) AS wip, "
        "SUM(CASE WHEN t.status='Under Review' THEN 1 ELSE 0 END) AS review, "
        "SUM(CASE WHEN t.status<>'Done' AND t.due_date<:t THEN 1 ELSE 0 END) AS overdue, "
        "SUM(CASE WHEN t.status='Done' AND t.completed_on>=:m THEN 1 ELSE 0 END) AS done_m, "
        "(SELECT MAX(l.at) FROM task_log l WHERE l.user_id=u.id) AS last_seen "
        "FROM users u LEFT JOIN tasks t ON t.assigned_to=u.id "
        "LEFT JOIN clients c ON c.id=t.client_id AND c.active=1 "
        "WHERE u.active=1 GROUP BY u.id, u.name, u.role ORDER BY u.name", t=t0, m=m0)
    unassigned = db.scalar("SELECT COUNT(*) FROM tasks t JOIN clients c ON c.id=t.client_id "
                           "WHERE c.active=1 AND t.assigned_to IS NULL AND t.status<>'Done' AND t.due_date<=:h",
                           h=(today + timedelta(days=30)).isoformat())
    st.markdown(f'<div style="text-align:right;margin:-3.2rem 0 1rem 0">{ui.live()}</div>', unsafe_allow_html=True)
    if unassigned:
        st.warning(f"{unassigned} task(s) due in the next 30 days have nobody assigned. Assign them on the Task Board.",
                   icon=":material/person_off:")

    max_open = max([p["open_"] or 0 for p in people] + [1])
    cols = st.columns(3, gap="medium")
    for i, p in enumerate(people):
        o, od = int(p["open_"] or 0), int(p["overdue"] or 0)
        load = 100 * o / max_open
        color = "#DC2626" if od else "#F59E0B" if load > 75 else ui.TEAL
        with cols[i % 3]:
            st.markdown(f"""
            <div class="pm-card"><div style="display:flex;gap:12px;align-items:center">{ui.avatar(p['name'], 44)}
              <div style="flex:1"><div style="font-weight:700;color:#0B1F3A">{ui.esc(p['name'])}</div>
              <div class="t2" style="color:#64748B;font-size:0.8rem">{ui.esc(p['role'])} · last active
               {ui.esc(ui.ago(p['last_seen']) or 'no activity yet')}</div></div>
              {ui.pill(f'{od} overdue', 'red') if od else ui.pill('On track', 'green')}</div>
              <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:14px;text-align:center">
                <div><div style="font-weight:800;font-size:1.25rem;color:#0B1F3A">{o}</div><div class="t2" style="font-size:0.7rem;color:#64748B">OPEN</div></div>
                <div><div style="font-weight:800;font-size:1.25rem;color:#1D4ED8">{int(p['wip'] or 0)}</div><div style="font-size:0.7rem;color:#64748B">DOING</div></div>
                <div><div style="font-weight:800;font-size:1.25rem;color:#B45309">{int(p['review'] or 0)}</div><div style="font-size:0.7rem;color:#64748B">REVIEW</div></div>
                <div><div style="font-weight:800;font-size:1.25rem;color:#15803D">{int(p['done_m'] or 0)}</div><div style="font-size:0.7rem;color:#64748B">DONE · MTH</div></div>
              </div>
              <div style="font-size:0.72rem;color:#64748B;margin-top:12px">Workload</div>{ui.bar(load, color)}
            </div>""", unsafe_allow_html=True)

    left, right = st.columns([1.1, 1], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Tasks completed per person · last 30 days**")
            done = db.query("SELECT u.name, t.completed_on FROM tasks t JOIN users u ON u.id=t.assigned_to "
                            "WHERE t.status='Done' AND t.completed_on>=:d", d=(today - timedelta(days=30)).isoformat())
            if done:
                df = pd.DataFrame(done).groupby("name").size().reset_index(name="completed").sort_values("completed")
                fig = px.bar(df, x="completed", y="name", orientation="h", color_discrete_sequence=[ui.TEAL])
                st.plotly_chart(ui.style_fig(fig, 280), width="stretch", config={"displayModeBar": False})
            else:
                st.markdown(ui.empty("Nothing completed in the last 30 days"), unsafe_allow_html=True)
    with right:
        from .dashboard import activity_feed
        activity_feed(9)
