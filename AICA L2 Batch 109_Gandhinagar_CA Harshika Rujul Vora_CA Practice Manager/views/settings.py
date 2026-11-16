import secrets

import pandas as pd
import streamlit as st

from core import auth, config, db, duedates, importer, invoice_pdf, ui
from core.constants import STATES

from . import common


def render():
    ui.header("Settings", "Logins, firm profile, due-date rules and data")
    t1, t2, t3, t5, t4 = st.tabs(["Team & logins", "Firm profile", "Due-date rules", "AI assistant",
                                  "Data & connection"])
    with t1:
        team_logins()
    with t2:
        firm_profile()
    with t3:
        rules_editor()
    with t5:
        ai_tab()
    with t4:
        data_tab()


def team_logins():
    me = common.me()
    with st.expander("Add a team member", icon=":material/person_add:"):
        with st.form("add_user", clear_on_submit=True):
            a, b, c = st.columns(3)
            name = a.text_input("Full name")
            username = b.text_input("Username", help="Lower-case, no spaces, e.g. priya")
            role = c.selectbox("Role", auth.ROLES, index=2,
                               help="Partner: everything. Manager: all work, billing, team. Staff: own tasks only.")
            email = a.text_input("Email (optional)")
            if st.form_submit_button("Create login", type="primary"):
                uname = username.strip().lower()
                if not name.strip() or not uname or " " in uname:
                    st.error("Enter a name and a username without spaces.")
                elif db.one("SELECT id FROM users WHERE username=:u", u=uname):
                    st.error("That username is taken.")
                else:
                    temp = "Welcome@" + secrets.token_hex(2)
                    auth.create_user(name, uname, temp, role, email, must_change=True)
                    st.success(f"Login created. Share these details privately: username **{uname}**, temporary "
                               f"password **{temp}** (they'll set their own on first sign-in).")
    users = db.query("SELECT id, name, username, role, email, active FROM users ORDER BY active DESC, name")
    df = pd.DataFrame(users)
    df["active"] = df["active"].astype(bool)
    edited = st.data_editor(df, hide_index=True, width="stretch", disabled=["id", "username"], key="users_ed",
                            column_config={"id": None, "role": st.column_config.SelectboxColumn("Role", options=auth.ROLES),
                                           "active": st.column_config.CheckboxColumn("Active")})
    a, b, c = st.columns([1, 1.3, 2])
    if a.button("Save changes", type="primary"):
        partners = sum(1 for _, r in edited.iterrows() if r["role"] == "Partner" and r["active"])
        if partners == 0:
            st.error("Keep at least one active Partner.")
        else:
            for _, r in edited.iterrows():
                db.execute("UPDATE users SET name=:n, role=:r, email=:e, active=:a WHERE id=:i",
                           n=r["name"], r=r["role"], e=r["email"], a=int(r["active"]), i=int(r["id"]))
            st.success("Saved.")
    umap = {u["id"]: f"{u['name']} (@{u['username']})" for u in users if u["id"] != me["id"]}
    if umap:
        who = b.selectbox("Reset password for", list(umap), format_func=umap.get, label_visibility="collapsed")
        if c.button("Reset password"):
            temp = "Reset@" + secrets.token_hex(2)
            auth.set_password(who, temp, must_change=True)
            st.info(f"Temporary password for {umap[who]}: **{temp}**")


def firm_profile():
    st.caption("Printed on every invoice. GST is split as CGST + SGST when the client is in the firm's state, else IGST.")
    f = invoice_pdf.firm()
    with st.form("firm"):
        a, b = st.columns(2)
        vals = {
            "firm_name": a.text_input("Firm name", f["firm_name"]),
            "firm_address": b.text_input("Address", f["firm_address"]),
            "firm_gstin": a.text_input("Firm GSTIN", f["firm_gstin"]),
            "firm_pan": b.text_input("Firm PAN", f["firm_pan"]),
            "firm_state": a.selectbox("Firm state", STATES, index=STATES.index(f["firm_state"]) if f["firm_state"] in STATES else 0),
            "firm_email": b.text_input("Billing email", f["firm_email"]),
            "firm_bank": st.text_input("Bank details line", f["firm_bank"]),
        }
        if st.form_submit_button("Save firm profile", type="primary"):
            for k, v in vals.items():
                db.set_setting(k, v)
            st.success("Saved.")


def rules_editor():
    st.caption("When a date changes permanently, edit its schedule here (or in due_dates.json on GitHub). "
               "Pending tasks move automatically. For a one-off extension use Compliance Calendar → Extend a due date.")
    with st.expander("How to write a schedule"):
        st.markdown("- **Monthly**: the day of the following month, e.g. `20`. `7|3=30` = 7th, but March is due 30 April.\n"
                    "- **Quarterly / Annual**: `MM-DD@N:Label` items separated by commas. `N` = years after the FY start "
                    "year. For FY 2026-27, `01-31@1:Q3` = 31 Jan 2027.")
    rules = pd.DataFrame(duedates.rules(active_only=False))
    rules["active"] = rules["active"].astype(bool)
    ed = st.data_editor(rules[["code", "title", "category", "frequency", "schedule", "active"]], hide_index=True,
                        width="stretch", disabled=["code", "category", "frequency"], key="rules_ed")
    if st.button("Save rules", type="primary"):
        bad = [r["code"] for _, r in ed.iterrows() if duedates.validate_schedule(r["frequency"], r["schedule"])]
        if bad:
            st.error("Schedule format is wrong for: " + ", ".join(bad))
        else:
            for _, r in ed.iterrows():
                db.execute("UPDATE due_date_rules SET title=:t, schedule=:s, active=:a WHERE code=:c",
                           t=r["title"], s=str(r["schedule"]).strip(), a=int(r["active"]), c=r["code"])
            db.execute("UPDATE tasks SET title=(SELECT title FROM due_date_rules r WHERE r.code=tasks.rule_code) "
                       "WHERE rule_code IS NOT NULL")
            moved = duedates.reschedule_pending(common.me()["id"])
            st.success(f"Saved. {moved} pending task(s) moved to new dates.")


def ai_tab():
    from core import ai
    st.markdown("The AI Assistant uses **Google Gemini**. Its free tier needs only a Google account: open "
                "[Google AI Studio](https://aistudio.google.com/), click **Get API key → Create API key**, and paste "
                "the key here. One key serves the whole firm.")
    st.warning("Privacy: on Google's free tier, what is sent may be used to improve Google's products and may be "
               "read by human reviewers. This app therefore masks client names, staff names, PAN, GSTIN, Aadhaar, "
               "phone numbers and e-mails before every request, and asks for confirmation before a notice is sent. "
               "Never paste unmasked confidential documents into other AI tools.", icon=":material/shield:")
    cur_key = db.get_setting("gemini_api_key") or ""
    with st.form("ai_settings"):
        on = st.toggle("AI Assistant switched on", db.get_setting("ai_enabled", "1") == "1")
        key = st.text_input("Gemini API key", type="password",
                            placeholder=("saved: ••••" + cur_key[-4:]) if cur_key else "paste the key from Google AI Studio",
                            help="Leave empty to keep the saved key.")
        choices = ai.MODEL_CHOICES + ["Other…"]
        cur_model = ai.model()
        pick = st.selectbox("Model", choices, index=choices.index(cur_model) if cur_model in choices else len(choices) - 1,
                            help="Flash-Lite has the most generous free limits. Google renames models over time; "
                                 "if one stops working, pick another or type the new name.")
        other = st.text_input("Other model name", "" if cur_model in choices else cur_model)
        if st.form_submit_button("Save", type="primary"):
            db.set_setting("ai_enabled", "1" if on else "0")
            if key.strip():
                db.set_setting("gemini_api_key", key.strip())
            db.set_setting("gemini_model", other.strip() if pick == "Other…" and other.strip() else
                           (cur_model if pick == "Other…" else pick))
            st.success("Saved.")
    if st.button("Test the AI connection", icon=":material/bolt:"):
        try:
            with st.spinner("Contacting Gemini…"):
                reply = ai.test_connection()
            st.success(f"Working. Gemini replied: {reply[:60]}")
        except ai.AIError as e:
            st.error(str(e))
    usage = db.query("SELECT feature, COUNT(*) AS calls, COALESCE(SUM(chars_sent),0) AS chars FROM ai_log "
                     "WHERE at >= :d GROUP BY feature ORDER BY calls DESC",
                     d=(common.today().replace(day=1)).isoformat())
    if usage:
        st.markdown("**AI usage this month** (audit trail)")
        st.dataframe(pd.DataFrame(usage), hide_index=True, width="stretch",
                     column_config={"feature": "Feature", "calls": "Requests", "chars": "Characters sent (masked)"})


def data_tab():
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("#### Backup & reports")
        st.caption("Everything (clients, tasks, invoices, activity) in one Excel workbook.")
        if st.button("Prepare Excel export", icon=":material/table_view:"):
            st.session_state.export = importer.export_all()
        if st.session_state.get("export"):
            st.download_button("Download export.xlsx", st.session_state.export, "ca_practice_export.xlsx", type="primary")
        st.markdown("#### Demo data")
        st.caption("Fictitious staff, clients, tasks, invoices and activity, for a presentation. Only works on an empty database.")
        if st.button("Load demo data", disabled=db.scalar("SELECT COUNT(*) FROM clients") > 0):
            import seed
            seed.run()
            st.success("Demo data loaded. Demo staff logins use password Demo@1234.")
    with b:
        st.markdown("#### Database connection")
        st.markdown(f"Connected to: **{config.database_label()}**")
        raw = config.raw_database_url()
        if raw and common.me()["role"] == "Partner":
            with st.expander("Share with colleagues (desktop app)", icon=":material/share:"):
                st.caption("Colleagues using the desktop app paste this on their first-run screen to join the firm's "
                           "database. It contains the database password: share it privately (not by email to "
                           "outsiders), and change the password in Supabase if someone leaves the firm.")
                st.code(raw, language=None)
        if config.FROZEN or config.local_settings() or config.database_url().startswith("sqlite"):
            st.caption("Connect this copy to your firm's shared database. In Supabase use Connect → **Session pooler**.")
            url = st.text_input("PostgreSQL connection string", type="password",
                                placeholder="postgresql://postgres.xxxx:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
            c1, c2 = st.columns(2)
            test, save = c1.button("Test connection"), c2.button("Save & restart", type="primary")
            if (test or save) and not url.strip():
                st.warning("Paste the connection string first.")
            elif test or save:
                with st.spinner("Connecting…"):
                    ok, msg = db.test_url(url.strip())
                if not ok:
                    st.error(db.explain_url_problem(url.strip(), msg) or f"Couldn't connect: {msg}")
                elif test:
                    st.success("Connection works.")
            if save and url.strip() and ok:
                config.save_local_settings({"database_url": url.strip(), "mode": "cloud"})
                st.cache_resource.clear()
                db.reset_engine()
                st.session_state.clear()
                st.rerun()
        else:
            st.caption("This copy gets its database from DATABASE_URL (Streamlit secrets or environment).")
