"""Helpers shared by the pages."""
from datetime import date

import streamlit as st

from core import auth, clock, db

REFRESH = "30s"  # how often live panels re-read the database


def me() -> dict:
    return st.session_state.user


def today() -> date:
    return clock.today()


def users(active_only=True) -> dict:
    sql = "SELECT id, name FROM users" + (" WHERE active=1" if active_only else "") + " ORDER BY name"
    return {u["id"]: u["name"] for u in db.query(sql)}


def clients(active_only=True) -> dict:
    sql = "SELECT id, name FROM clients" + (" WHERE active=1" if active_only else "") + " ORDER BY name"
    return {c["id"]: c["name"] for c in db.query(sql)}


def scope_sql(alias="t") -> tuple[str, dict]:
    """Staff only see their own tasks; partners and managers see everything."""
    u = me()
    if auth.sees_all_work(u):
        return "", {}
    return f" AND {alias}.assigned_to = :me", {"me": u["id"]}


def set_status(task: dict, new_status: str):
    if new_status == task["status"]:
        return
    db.execute("UPDATE tasks SET status=:s, completed_on=:c, updated_on=:u WHERE id=:i",
               s=new_status, c=today().isoformat() if new_status == "Done" else None, u=db.now(), i=task["id"])
    db.log(task["id"], me()["id"], "Status", f"{task['status']} → {new_status}")


def reassign(task: dict, new_user_id):
    if new_user_id == task["assigned_to"]:
        return
    names = users(active_only=False)
    db.execute("UPDATE tasks SET assigned_to=:a, updated_on=:u WHERE id=:i", a=new_user_id, u=db.now(), i=task["id"])
    db.log(task["id"], me()["id"], "Assigned", f"{names.get(task['assigned_to'], 'Unassigned')} → "
                                              f"{names.get(new_user_id, 'Unassigned')}")


def no_clients_yet():
    st.info("No clients yet. Add one under **Clients** (or import your list from Excel).", icon=":material/info:")
