import streamlit as st

from core import auth, db, ui

from . import common


def render():
    u = common.me()
    ui.header("My Account", f"{u['role']} · @{u['username']}")
    a, b = st.columns([1, 1.4], gap="large")
    with a:
        open_ = db.scalar("SELECT COUNT(*) FROM tasks WHERE assigned_to=:i AND status<>'Done'", i=u["id"])
        done = db.scalar("SELECT COUNT(*) FROM tasks WHERE assigned_to=:i AND status='Done'", i=u["id"])
        st.markdown(f"""<div class="pm-card" style="text-align:center;padding:28px">{ui.avatar(u['name'], 72)}
            <h3 style="margin:12px 0 2px 0">{ui.esc(u['name'])}</h3><div style="color:#64748B">{ui.esc(u['email'] or '')}</div>
            <div style="margin-top:12px">{ui.pill(u['role'], 'teal')} {ui.pill(f'{open_} open', 'blue')}
            {ui.pill(f'{done} done', 'green')}</div></div>""", unsafe_allow_html=True)
    with b:
        st.markdown("#### Change password")
        with st.form("chpw", clear_on_submit=True):
            cur = st.text_input("Current password", type="password")
            new = st.text_input("New password", type="password")
            new2 = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Update password", type="primary"):
                if not auth.verify_password(cur, u["password_hash"]):
                    st.error("Current password is wrong.")
                elif new != new2:
                    st.error("Passwords don't match.")
                elif auth.password_problem(new):
                    st.error(auth.password_problem(new))
                else:
                    auth.set_password(u["id"], new)
                    st.success("Password updated.")
