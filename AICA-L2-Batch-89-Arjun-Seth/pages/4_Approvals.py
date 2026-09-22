# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Approvals page: a Reviewer approves leases that are Pending Review, or rejects them with a reason
(a rejected lease goes back to its owner to be corrected and resubmitted)."""
import streamlit as st

from auth_ui import require_login, set_flash, show_flash
from core.workflow import approve_case, approve_cases, can_approve, get_user_cases, reject_case
from db.database import get_session

st.set_page_config(page_title="LeaseIQ Pro - Approvals", page_icon="✅", layout="wide")
user = require_login("approve")


def _approve(case_id):
    current = st.session_state["user"]
    try:
        with get_session() as session:
            approve_case(session, case_id, current["user_id"], current["role"])
        set_flash("success", "Lease approved.")
    except (LookupError, ValueError, PermissionError) as exc:
        set_flash("error", str(exc))


def _set_all(case_ids):
    """'Select all' checkbox callback: tick or untick every lease."""
    value = st.session_state.get("approve_select_all", False)
    for case_id in case_ids:
        st.session_state["approve_pick_{}".format(case_id)] = value


def _approve_selected(case_ids):
    """'Approve selected' button callback: approve every ticked lease, each in its own transaction."""
    current = st.session_state["user"]
    picked = [case_id for case_id in case_ids if st.session_state.get("approve_pick_{}".format(case_id))]
    try:
        with get_session() as session:
            outcome = approve_cases(session, picked, current["user_id"], current["role"])
    except (PermissionError, ValueError) as exc:
        set_flash("error", str(exc))
        return
    for case_id in picked:
        st.session_state.pop("approve_pick_{}".format(case_id), None)
    st.session_state.pop("approve_select_all", None)
    message = "Approved {} lease(s): {}.".format(len(outcome["approved"]), ", ".join(outcome["approved"])) if outcome["approved"] else ""
    if outcome["failed"]:
        problems = "; ".join("lease #{}: {}".format(case_id, reason) for case_id, reason in outcome["failed"])
        set_flash("error", (message + " " if message else "") + "Could not approve " + problems)
    else:
        set_flash("success", message or "Nothing was selected.")


def _reject(case_id):
    current = st.session_state["user"]
    reason = st.session_state.get("reject_reason_{}".format(case_id), "")
    try:
        with get_session() as session:
            case = reject_case(session, case_id, current["user_id"], current["role"], reason)
            ref = case.lease_ref
        st.session_state.pop("reject_reason_{}".format(case_id), None)
        set_flash("success", "Lease {} rejected and sent back for correction.".format(ref))
    except (LookupError, ValueError, PermissionError) as exc:
        set_flash("error", str(exc))


st.title("Approvals")
show_flash()

allowed = can_approve(user["role"])
if not allowed:
    st.info("Your role ({}) cannot approve or reject leases. Only a Reviewer can.".format(user["role"]))

with get_session() as session:
    pending = [
        {
            "case_id": case.case_id,
            "ref": case.lease_ref or "#{}".format(case.case_id),
            "lessor": case.lessor_name or "-",
            "lessee": case.lessee_name or "-",
            "asset": case.asset_type or "-",
            "currency": case.currency or "INR",
        }
        for case in get_user_cases(session, user["user_id"], status="Pending Review")  # only THIS user's leases
    ]

if not pending:
    st.info("No leases are waiting for approval.")

pending_ids = [case["case_id"] for case in pending]
if pending and allowed:
    # keep 'Select all' in step with the individual ticks (set before the checkbox is drawn)
    st.session_state["approve_select_all"] = all(st.session_state.get("approve_pick_{}".format(i), False) for i in pending_ids)
    selected_count = sum(1 for i in pending_ids if st.session_state.get("approve_pick_{}".format(i), False))
    select_column, approve_all_column = st.columns([3, 3])
    select_column.checkbox("Select all ({})".format(len(pending_ids)), key="approve_select_all", on_change=_set_all, args=(pending_ids,))
    approve_all_column.button(
        "Approve selected ({})".format(selected_count),
        key="approve_selected",
        type="primary",
        disabled=selected_count == 0,
        on_click=_approve_selected,
        args=(pending_ids,),
    )

for case in pending:
    with st.container(border=True):
        columns = st.columns([0.6, 2, 4, 2]) if allowed else st.columns([0.01, 2, 4, 2])
        if allowed:
            columns[0].checkbox("Select", key="approve_pick_{}".format(case["case_id"]), label_visibility="collapsed")
        columns = columns[1:]
        columns[0].markdown("**{}**  \n{}".format(case["ref"], case["currency"]))
        columns[1].write("{} / {} - {}".format(case["lessor"], case["lessee"], case["asset"]))
        columns[2].button(
            "Approve",
            key="approve_{}".format(case["case_id"]),
            type="primary",
            disabled=not allowed,
            on_click=_approve,
            args=(case["case_id"],),
        )
        with st.expander("Reject this lease"):
            st.caption(
                "The lease goes back to be corrected (for example a wrong currency) and resubmitted. "
                "Your reason is shown to the person who edits it and is kept in the audit log."
            )
            st.text_input("Reason for rejection", key="reject_reason_{}".format(case["case_id"]), disabled=not allowed)
            reason_given = len(" ".join(st.session_state.get("reject_reason_{}".format(case["case_id"]), "").split())) >= 3
            st.button(
                "Reject lease",
                key="reject_{}".format(case["case_id"]),
                disabled=not allowed or not reason_given,
                on_click=_reject,
                args=(case["case_id"],),
            )
