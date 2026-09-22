# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Leases page: add a lease (upload a contract or type it in), find leases with filters, review and open them."""
import pandas as pd
import streamlit as st

from auth_ui import require_login, set_flash, show_flash
from core.extraction import (
    ExtractionError,
    extract_lease_fields,
    extract_text,
    prepare_document_text,
)
from core.lease_filters import filter_leases, filter_options
from core.workflow import (
    can_delete,
    create_lease_from_extraction,
    delete_case,
    display_status,
    get_case_ids_by_state,
    get_user_cases,
    submit_for_review,
)
from db.database import get_session
from lease_ui import close_view, open_view, render_edit_form, render_manual_form, render_results, render_review

st.set_page_config(page_title="LeaseIQ Pro - Leases", page_icon="📄", layout="wide")
user = require_login()

CONFIDENCE_LABELS = {"High": "🟢 High", "Medium": "🟡 Medium", "Low": "🔴 Low"}
ADD_MODES = ("Upload contract", "Add contract manually")
# (session key, label, key in filter_options)
FILTERS = (
    ("filter_ids", "Lease ID", "lease_ids"),
    ("filter_lessors", "Lessor", "lessors"),
    ("filter_lessees", "Lessee", "lessees"),
    ("filter_status", "Status", "statuses"),
    ("filter_currency", "Currency", "currencies"),
)


def _display(value):
    if value is None:
        return "-"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _submit(case_id):
    current = st.session_state["user"]
    try:
        with get_session() as session:
            submit_for_review(session, case_id, current["user_id"], current["role"])
        set_flash("success", "Lease submitted for review.")
    except (LookupError, ValueError, PermissionError) as exc:
        set_flash("error", str(exc))


def _delete(case_id):
    """Callback of the Admin's 'Delete permanently' button: the lease goes, its audit trail stays."""
    current = st.session_state["user"]
    reason = st.session_state.get("delete_reason_{}".format(case_id), "")
    try:
        with get_session() as session:
            outcome = delete_case(session, case_id, current["user_id"], current["role"], reason)
    except (LookupError, ValueError, PermissionError) as exc:
        set_flash("error", str(exc))
        return
    for key in ("delete_reason_{}".format(case_id), "delete_confirm_{}".format(case_id)):
        st.session_state.pop(key, None)
    set_flash("success", "Lease {} deleted. The audit log keeps its full history and a record of the deletion.".format(outcome["lease_ref"]))


def _clear_filters():
    for key, _, _ in FILTERS:
        st.session_state[key] = []


# ---- review / results screens replace the list while one is open ----
view = st.session_state.get("lease_view")
if view:
    st.button("\u2190 Back to leases", key="back_to_leases", on_click=close_view)
    show_flash()
    if view["mode"] == "review":
        render_review(user, view["case_id"])
    elif view["mode"] == "edit":
        render_edit_form(user, view["case_id"])
    else:
        render_results(user, view["case_id"])
    st.stop()

st.title("Leases")
show_flash()

# ------------------------------- Add lease -------------------------------- #
can_edit = "edit" in user["rights"]  # a view-only person can see every lease and result but not add or change any
if can_edit:
    st.subheader("Add lease")
    mode = st.radio("How do you want to add a lease?", ADD_MODES, horizontal=True, key="add_mode")

    if mode == ADD_MODES[1]:
        render_manual_form(user)
    else:
        uploaded = st.file_uploader(
            "Upload a lease agreement (PDF, Word or Excel - text-based files only, no scanned images)",
            type=["pdf", "docx", "xlsx"],
            key="lease_upload",
        )
        if uploaded is not None and st.button("Extract lease data", key="extract_button", type="primary"):
            try:
                with st.spinner("Reading the document and extracting lease data (this can take a minute or two)..."):
                    text = extract_text(uploaded)
                    prepared, truncated = prepare_document_text(text)
                    fields = extract_lease_fields(prepared)
                with get_session() as session:
                    case = create_lease_from_extraction(
                        session, user["user_id"], uploaded.name, getattr(uploaded, "size", None), prepared, fields
                    )
                    lease_ref = case.lease_ref
                    new_case_id = case.case_id
                st.session_state["last_extraction"] = {
                    "ref": lease_ref,
                    "case_id": new_case_id,
                    "filename": uploaded.name,
                    "fields": fields,
                    "truncated": truncated,
                }
            except ExtractionError as exc:
                st.session_state.pop("last_extraction", None)
                st.error(str(exc))

        last = st.session_state.get("last_extraction")
        if last:
            found = sum(1 for entry in last["fields"].values() if entry["value"] is not None)
            st.success(
                "Lease {} created as Draft from '{}'. The AI found {} of {} fields.".format(
                    last["ref"], last["filename"], found, len(last["fields"])
                )
            )
            if last["truncated"]:
                st.warning("The document was very long, so only the first part was analysed.")
            st.button(
                "Review and validate these values \u2192",
                key="review_after_extraction",
                type="primary",
                on_click=open_view,
                args=("review", last["case_id"]),
            )
            rows = [
                {
                    "Field": key,
                    "Value": _display(entry["value"]),
                    "Confidence": CONFIDENCE_LABELS.get(entry["confidence"], entry["confidence"]),
                    "Source text": entry.get("source_snippet") or "",
                    "Note": entry.get("note") or "",
                }
                for key, entry in last["fields"].items()
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True)
            with st.expander("Raw extracted JSON"):
                st.json(last["fields"])

else:
    st.info("You have view-only access, so you can see every lease and its results but not add or change leases. Ask an Admin if you need to edit.")

st.divider()

# -------------------------------- Lease list ------------------------------ #
st.subheader("Your leases")
with get_session() as session:
    cases = [
        {
            "case_id": case.case_id,
            "ref": case.lease_ref or "#{}".format(case.case_id),
            "lessor": case.lessor_name or "-",
            "lessee": case.lessee_name or "-",
            "currency": case.currency or "INR",
            "asset": case.asset_type or "-",
            "status": display_status(case.status, case.rejection_reason),  # a rejected lease shows as 'Rejected'
            "rejection_reason": case.rejection_reason if case.status == "Draft" else None,
            "source": case.source,
            "created": case.created_at.strftime("%d-%b-%Y %H:%M") if case.created_at else "-",
        }
        for case in get_user_cases(session, user["user_id"])  # only THIS user's leases
    ]
    lease_states = get_case_ids_by_state(session, user["user_id"])

if not cases:
    st.info("You have no leases yet. Upload a lease agreement, or add one manually, above.")
    st.stop()

# ---- filters: lease ID, lessor, lessee, status and currency ----
choices = filter_options(cases)
with st.container(border=True):
    st.markdown("**Filter leases** - leave a filter empty to include everything")
    filter_columns = st.columns(5)
    selected = {}
    for column, (key, label, option_key) in zip(filter_columns, FILTERS):
        st.session_state[key] = [v for v in st.session_state.get(key, []) if v in choices[option_key]]  # drop stale picks
        selected[option_key] = column.multiselect(label, choices[option_key], key=key, placeholder="All")
    st.button("Clear filters", key="clear_filters", on_click=_clear_filters)

shown = filter_leases(
    cases, selected["lease_ids"], selected["lessors"], selected["lessees"], selected["statuses"], selected["currencies"]
)
st.caption("Showing {} of {} lease(s)".format(len(shown), len(cases)))
if not shown:
    st.info("No leases match these filters. Use 'Clear filters' to see them all.")

for case in shown:
    with st.container(border=True):
        columns = st.columns([2, 4, 2, 2, 3])
        columns[0].markdown("**{}**".format(case["ref"]))
        columns[1].markdown("{} *(lessor)*  \n{} *(lessee)*  \n{}".format(case["lessor"], case["lessee"], case["asset"]))
        columns[2].markdown("{}  \n**{}**".format(case["created"], case["currency"]))
        columns[3].write("Status: **{}**".format(case["status"]))
        case_id = case["case_id"]
        if case["status"] == "Rejected":
            # sent back by a Reviewer: correct it (uploaded leases on the review screen, the others on the edit form)
            columns[4].button(
                "Edit and resubmit",
                key="edit_{}".format(case_id),
                type="primary",
                disabled=not can_edit,
                on_click=open_view,
                args=("review" if case["source"] == "upload" and case_id in lease_states["reviewable"] else "edit", case_id),
            )
            if case_id in lease_states["with_results"]:
                columns[4].button("View last results", key="results_{}".format(case_id), on_click=open_view, args=("results", case_id))
            st.caption("Rejected: {}".format(case["rejection_reason"]))
        elif case["status"] == "Draft" and case_id in lease_states["reviewable"]:
            # a lease from an uploaded document must be validated before it can go for review
            columns[4].button(
                "Review and validate", key="review_{}".format(case_id), disabled=not can_edit, on_click=open_view, args=("review", case_id)
            )
        elif case["status"] == "Draft":
            columns[4].button("Submit for review", key="submit_{}".format(case_id), disabled=not can_edit, on_click=_submit, args=(case_id,))
        elif case_id in lease_states["with_results"]:
            columns[4].button("View results", key="results_{}".format(case_id), on_click=open_view, args=("results", case_id))
        elif case["status"] == "Pending Review":
            columns[4].caption("Waiting for a Reviewer (see Approvals)")
        if can_delete(user["role"]):  # only an Admin sees this
            with columns[4].popover("Delete", icon=":material/delete:"):
                st.warning(
                    "This permanently deletes {} and everything calculated for it. The audit log keeps the lease's full "
                    "history and records who deleted it and why.".format(case["ref"])
                )
                st.text_input("Reason for deleting", key="delete_reason_{}".format(case_id))
                confirmed = st.checkbox("I understand this cannot be undone", key="delete_confirm_{}".format(case_id))
                reason_given = len(" ".join(st.session_state.get("delete_reason_{}".format(case_id), "").split())) >= 3
                st.button(
                    "Delete permanently",
                    key="delete_{}".format(case_id),
                    type="primary",
                    disabled=not (confirmed and reason_given),
                    on_click=_delete,
                    args=(case_id,),
                )
