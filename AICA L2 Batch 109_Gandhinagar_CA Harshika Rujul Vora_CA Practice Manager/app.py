"""CA Practice Manager — entry point.   Run:  streamlit run app.py"""
import os
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="CA Practice Manager", page_icon="📒", layout="wide",
                   initial_sidebar_state="expanded")

try:
    import fpdf, openpyxl, pandas, plotly, psycopg2, sqlalchemy  # noqa: E401,F401  (check packages are installed)
except ModuleNotFoundError as missing:
    st.error(f"A required package is missing: **{missing.name}**")
    st.markdown("Close this window, open a terminal **inside the project folder** and run:")
    st.code("python -m pip install -r requirements.txt", language="bash")
    st.markdown("Then start the app again (or simply double-click **Start_App.bat**, which does this for you).")
    st.stop()

from core import auth, clock, config, db, duedates, ui  # noqa: E402
ui.inject_css()


@st.cache_resource(show_spinner="Connecting to database…")
def _startup(url: str):
    """Runs once per database (not on every click)."""
    db.init_db()
    auth.ensure_admin()
    duedates.seed_rules()
    return True


def database_error(e: Exception):
    """The saved database can't be reached: explain why in plain words and let the user fix it here."""
    ui.header("Can't reach the database", config.database_label())
    raw = config.raw_database_url() or ""
    hint = db.explain_url_problem(raw, str(e))
    st.error(hint or "The app couldn't connect to the database. Check the internet connection, and that the "
                     "Supabase project isn't paused (supabase.com → your project → Restore).", icon=":material/error:")
    with st.expander("Technical details"):
        st.code(f"{type(e).__name__}: {str(e).splitlines()[0][:400]}", language=None)
    if os.environ.get("DATABASE_URL") or config._from_secrets("DATABASE_URL"):
        st.info("This copy takes its connection from DATABASE_URL in the app's Secrets (Streamlit Cloud → your app → "
                "Settings → Secrets) or an environment variable. Correct it there, then reboot the app.")
        return
    st.markdown("#### Fix the connection")
    st.caption("Paste the corrected Session pooler string from Supabase (Connect → Direct → Session pooler), "
               "with your database password in place of [YOUR-PASSWORD].")
    url = st.text_input("PostgreSQL connection string", type="password", key="fix_url")
    a, b = st.columns(2)
    if a.button("Test and save", type="primary", width="stretch"):
        if not url.strip():
            st.warning("Paste the connection string first.")
        else:
            with st.spinner("Connecting…"):
                ok, msg = db.test_url(url.strip())
            if ok:
                config.save_local_settings({"database_url": url.strip(), "mode": "cloud"})
                st.cache_resource.clear()
                db.reset_engine()
                st.rerun()
            st.error(db.explain_url_problem(url.strip(), msg) or f"Couldn't connect: {msg}")
    if b.button("Go back to this computer's data", width="stretch",
                help="Uses the local database on this PC. Your cloud database is not changed."):
        config.save_local_settings({"database_url": "", "mode": "local"})
        st.cache_resource.clear()
        db.reset_engine()
        st.rerun()


def first_run_setup():
    """Desktop app, first launch: join the firm's shared cloud database, or work on this computer only."""
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.markdown("""
        <div class="pm-login-art" style="min-height:480px"><div class="glow"></div>
          <div class="pm-brand"><div class="mark">CA</div>
            <div><div class="nm">CA Practice Manager</div><div class="tg">First-time setup</div></div></div>
          <h2>Welcome! Let's connect<br/>this computer.</h2>
          <p>Join your firm's shared database to see the same clients, tasks and live team status as everyone else.
             Your partner or administrator can give you the connection details.</p>
        </div>""", unsafe_allow_html=True)
    with right:
        st.write("")
        st.markdown("### Join my firm (recommended)")
        st.caption("Paste the connection details your partner shared with you. "
                   "Partners find them in Settings → Data & connection.")
        url = st.text_input("Connection details", type="password",
                            placeholder="postgresql://postgres.xxxx:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
        if st.button("Connect", type="primary", width="stretch"):
            if not url.strip():
                st.warning("Paste the connection details first.")
            else:
                with st.spinner("Connecting…"):
                    ok, msg = db.test_url(url.strip())
                if ok:
                    config.save_local_settings({"database_url": url.strip(), "mode": "cloud"})
                    st.cache_resource.clear()
                    db.reset_engine()
                    st.rerun()
                st.error(db.explain_url_problem(url.strip(), msg) or f"Couldn't connect: {msg}")
        st.divider()
        st.markdown("### Use on this computer only")
        st.caption("Good for trying the app or a single-user setup. Data stays on this PC. "
                   "You can connect to the firm's database later from Settings.")
        if st.button("Start on this computer", width="stretch"):
            config.save_local_settings({"mode": "local"})
            st.rerun()


if config.needs_setup():
    first_run_setup()
    st.stop()

try:
    _startup(config.database_url())
except Exception as e:  # bad cloud URL, no internet, etc.
    database_error(e)
    st.stop()


# ------------------------------------------------------------------ login
def login_page():
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown("""
        <div class="pm-login-art"><div class="glow"></div>
          <div class="pm-brand"><div class="mark">CA</div>
            <div><div class="nm">CA Practice Manager</div><div class="tg">For Chartered Accountant firms</div></div></div>
          <h2>Every client. Every deadline.<br/>One live workspace.</h2>
          <p>Run GST, Income Tax, TDS and Audit work for the whole firm, with real-time status for partners and staff.</p>
          <ul style="padding-left:0;margin-top:26px">
            <li>Statutory due dates generated automatically for every client</li>
            <li>Kanban task board with live team status</li>
            <li>GST invoices with CGST / SGST / IGST and PDF</li>
            <li>Secure document vault by client and financial year</li>
          </ul>
        </div>""", unsafe_allow_html=True)
    with right:
        st.write("")
        st.write("")
        st.markdown("### Welcome back")
        st.caption("Sign in with the username and password given by your firm's partner.")
        with st.form("login"):
            u = st.text_input("Username", placeholder="e.g. priya")
            p = st.text_input("Password", type="password")
            ok = st.form_submit_button("Sign in", type="primary", width="stretch")
        if ok:
            user = auth.authenticate(u, p)
            if user:
                st.session_state.uid = user["id"]
                st.session_state.login_at = clock.now()
                st.rerun()
            st.error("Wrong username or password, or the account is inactive.")
        if db.scalar("SELECT COUNT(*) FROM users") == 1 and db.scalar("SELECT COUNT(*) FROM clients") == 0:
            st.info("First time here? Sign in with **admin** / **admin@123**. You'll be asked to set a new password.")
        st.caption(f"🔒 {config.database_label()}")


def change_password_page(user, forced=False):
    ui.header("Set a new password" if forced else "Change password",
              "Your account uses a temporary password. Choose your own to continue." if forced else "")
    with st.form("pw"):
        if not forced:
            cur = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password", help="At least 8 characters, letters and numbers")
        new2 = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Save password", type="primary"):
            if not forced and not auth.verify_password(cur, user["password_hash"]):
                st.error("Current password is wrong.")
            elif new != new2:
                st.error("The two passwords don't match.")
            elif auth.password_problem(new):
                st.error(auth.password_problem(new))
            else:
                auth.set_password(user["id"], new)
                st.success("Password changed.")
                st.rerun()


def _auto_check_due_dates(user):
    """Partners/managers: quietly check GitHub for due-date updates at most every 6 hours."""
    if not auth.sees_all_work(user) or st.session_state.get("dd_checked"):
        return
    st.session_state.dd_checked = True
    last = db.get_setting("due_dates_checked")
    if last and (clock.now() - datetime.strptime(last, "%Y-%m-%d %H:%M:%S")).total_seconds() < 6 * 3600:
        return
    try:
        status, info = duedates.check_for_updates(user["id"])
        if status == "updated":
            st.toast(f"📅 Due dates updated to version {info['version']}: {info['tasks_moved']} task(s) moved.")
    except Exception:
        pass  # offline or bad URL: the Calendar page shows the error when checked manually


# ------------------------------------------------------------------ routing
user = None
if st.session_state.get("uid"):
    user = db.one("SELECT * FROM users WHERE id=:i AND active=1", i=st.session_state.uid)
    if not user:
        st.session_state.clear()

if not user:
    st.navigation([st.Page(login_page, title="Sign in", icon=":material/lock:")], position="hidden").run()
    st.stop()

st.session_state.user = user
if user["must_change"]:
    st.navigation([st.Page(lambda: change_password_page(user, True), title="Set password")], position="hidden").run()
    st.stop()

_auto_check_due_dates(user)

from views import (account, ai_assistant, billing, calendar_view, clients, dashboard,  # noqa: E402
                   documents, settings, tasks, team)

PAGES = {
    "dashboard": st.Page(dashboard.render, title="Dashboard", icon=":material/space_dashboard:", url_path="dashboard",
                         default=True),
    "tasks": st.Page(tasks.render, title="Task Board" if auth.sees_all_work(user) else "My Work",
                     icon=":material/view_kanban:", url_path="tasks"),
    "calendar": st.Page(calendar_view.render, title="Compliance Calendar", icon=":material/event:", url_path="calendar"),
    "ai": st.Page(ai_assistant.render, title="AI Assistant", icon=":material/auto_awesome:", url_path="ai"),
    "clients": st.Page(clients.render, title="Clients", icon=":material/groups:", url_path="clients"),
    "billing": st.Page(billing.render, title="Billing", icon=":material/receipt_long:", url_path="billing"),
    "documents": st.Page(documents.render, title="Documents", icon=":material/folder_open:", url_path="documents"),
    "team": st.Page(team.render, title="Team", icon=":material/badge:", url_path="team"),
    "settings": st.Page(settings.render, title="Settings", icon=":material/settings:", url_path="settings"),
    "account": st.Page(account.render, title="My Account", icon=":material/person:", url_path="account"),
}
SECTIONS = {"Workspace": ["dashboard", "tasks", "calendar", "ai"], "Practice": ["clients", "billing", "documents"],
            "Firm": ["team", "settings", "account"]}
allowed = {sec: [k for k in keys if auth.can(user, k)] for sec, keys in SECTIONS.items()}
page = st.navigation([PAGES[k] for keys in allowed.values() for k in keys], position="hidden")

with st.sidebar:
    st.markdown("""<div class="pm-brand"><div class="mark">CA</div><div><div class="nm">Practice Manager</div>
        <div class="tg">GST · Income Tax · TDS · Audit</div></div></div>""", unsafe_allow_html=True)
    for sec, keys in allowed.items():
        if keys:
            st.markdown(f'<div class="pm-sec">{sec}</div>', unsafe_allow_html=True)
            for k in keys:
                st.page_link(PAGES[k])
    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    st.markdown(f"""<div class="pm-user">{ui.avatar(user['name'], 34)}<div><div class="n">{ui.esc(user['name'])}</div>
        <div class="r">{ui.esc(user['role'])} · @{ui.esc(user['username'])}</div></div></div>""", unsafe_allow_html=True)
    if st.button("Sign out", icon=":material/logout:"):
        st.session_state.clear()
        st.rerun()
    st.caption(f"FY {duedates.fy_label(duedates.current_fy_start())} · {config.database_label()}")

page.run()
