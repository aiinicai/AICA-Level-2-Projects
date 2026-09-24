# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Lease review and results screens (UI layer - deliberately NOT in core/).

* ``render_review``  - the validation screen: what the AI found (left) next to an editable
                       value (right), then "Confirm & Proceed".
* ``render_results`` - the saved calculation: classification and rationale, schedules, journal entries.
The rules live in ``core/validation.py`` and the saving in ``core/workflow.py``.
"""
from datetime import date, datetime

import pandas as pd
import streamlit as st

from auth_ui import set_flash
from core import validation as rules
from core.bulk import REQUIRED_COLUMNS
from core.disclosures import generate_disclosures_from_stored
from core.extraction import ExtractionError
from core.lease_export import (
    build_lease_excel,
    build_lease_export,
    csv_files,
    csv_zip,
    excel_file_name,
    zip_file_name,
)
from core.formatting import (
    CURRENCY_CODES,
    NUMBER_FORMATS,
    currency_decimals,
    currency_label,
    format_money,
    format_number,
)
from core.results import (
    FRAMEWORK_LABELS,
    FRAMEWORKS,
    format_tests,
    journal_frame,
    schedule_frame,
)
from core.memo_generator import build_memo_facts, build_template_memo, check_memo, generate_memo
from core.workflow import (
    confirm_validation,
    create_manual_lease,
    display_status,
    get_lease_case_data,
    get_lease_edit_values,
    get_lease_export_data,
    get_rejection_info,
    get_review_data,
    get_stored_results,
    list_memos,
    resubmit_edited_lease,
    save_memo,
)
from db.database import get_session

_MIN_DATE, _MAX_DATE = date(1990, 1, 1), date(2100, 12, 31)


# ------------------------------- view routing ------------------------------- #
def open_view(mode: str, case_id: int) -> None:
    """Button callback: show the 'review' or 'results' screen for a lease."""
    st.session_state["lease_view"] = {"mode": mode, "case_id": case_id}


def close_view() -> None:
    st.session_state.pop("lease_view", None)


# ------------------------------ manual entry form ---------------------------- #
_FRAMEWORK_LABELS = {"BOTH": "Ind AS 116 and ASC 842", "IND_AS_116": "Ind AS 116 only", "ASC_842": "ASC 842 only"}
_OVERRIDE_LABELS = {"": "Let the five tests decide", "FINANCE LEASE": "Finance lease (override)", "OPERATING LEASE": "Operating lease (override)"}


def _form_values(prefix: str) -> dict:
    """The canonical values currently typed into the form whose widget keys start with ``prefix``."""
    return {
        key: rules.from_widget(kind, st.session_state.get(prefix + key))
        for _, fields in rules.REVIEW_SECTIONS
        for key, _, kind in fields
    }


def _render_form_fields(prefix: str, user: dict, initial: dict = None) -> dict:
    """The lease fields, section by section. ``initial`` (the values of a saved lease) pre-fills them for
    editing; without it the usual defaults are used. Returns the canonical values currently shown."""
    default_currency = user.get("default_currency", "INR")
    values = {}
    for title, section_fields in rules.REVIEW_SECTIONS:
        st.markdown("#### {}".format(title))
        left, right = st.columns(2)
        counter = 0
        for key, label, kind in section_fields:
            shown = label + (" *" if key in REQUIRED_COLUMNS else "")
            start = initial.get(key) if initial is not None else None
            if start is None:
                start = rules.default_value(key, kind, default_currency)
            default = rules.to_widget(kind, start)
            if kind == "longtext":
                target = st.container()
            else:
                target = (left, right)[counter % 2]
                counter += 1
            with target:
                widget = _widget(key, shown, kind, default, prefix + key, visibility="visible")
            values[key] = rules.from_widget(kind, widget)
    return values


def _render_reporting_options(prefix: str, framework: str = "BOTH", override=None) -> None:
    st.markdown("#### Reporting options")
    first, second = st.columns(2)
    frameworks, overrides = list(_FRAMEWORK_LABELS), list(_OVERRIDE_LABELS)
    first.selectbox(
        "Reporting framework",
        frameworks,
        index=frameworks.index(framework) if framework in frameworks else 0,
        format_func=_FRAMEWORK_LABELS.get,
        key=prefix + "framework",
    )
    second.selectbox(
        "ASC 842 classification",
        overrides,
        index=overrides.index(override) if override in overrides else 0,
        format_func=_OVERRIDE_LABELS.get,
        key=prefix + "override",
        help="Leave this on 'Let the five tests decide' unless you need to force a classification.",
    )


def _show_form_checks(values: dict) -> list:
    """Show what is still missing / wrong / worth a look; returns the errors (the save button stays off while any remain)."""
    errors, warnings = rules.validate_manual_values(values)
    missing = [message for message in errors if rules.is_missing_message(message)]
    problems = [message for message in errors if not rules.is_missing_message(message)]
    if missing:
        st.info("Still to fill in: " + "; ".join(message.replace(" is required", "").replace("Please answer: ", "") for message in missing))
    for message in problems:
        st.error(message)
    for message in warnings:
        st.warning(message)
    return errors


def _clear_form_state(prefix: str, keep: str) -> None:
    for key in [k for k in st.session_state if k.startswith(prefix) and k != keep]:
        del st.session_state[key]  # an empty / fresh form next time (the button's own state is left alone)


def _create_manual_lease() -> None:
    """Button callback: check, calculate and create the lease typed into the manual form."""
    current = st.session_state["user"]
    values = _form_values("manual_")
    errors, _ = rules.validate_manual_values(values)
    if errors:
        set_flash("error", "; ".join(errors))
        return
    framework = st.session_state.get("manual_framework") or "BOTH"
    override = st.session_state.get("manual_override") or None
    try:
        with get_session() as session:
            case = create_manual_lease(session, current["user_id"], current["role"], values, framework, override)
            case_id, lease_ref = case.case_id, case.lease_ref
    except (ValueError, PermissionError) as exc:
        set_flash("error", str(exc))
        return
    _clear_form_state("manual_", keep="manual_create")
    set_flash("success", "Lease {} created and calculated. It is now 'Pending Review'.".format(lease_ref))
    open_view("results", case_id)


def render_manual_form(user: dict) -> None:
    """Type a lease in by hand: the same fields and rules as the validation screen, no document, no AI."""
    if "edit" not in user.get("rights", []):
        st.error("You have view-only access, so you cannot change leases. Ask an Admin if you need to edit.")
        return
    st.caption(
        "Type the lease details yourself - no document or AI is used. Fields marked * are required. When you press the "
        "button the lease is checked, calculated and placed in 'Pending Review' for approval."
    )
    values = _render_form_fields("manual_", user)
    _render_reporting_options("manual_")
    errors = _show_form_checks(values)
    st.button(
        "Calculate and create lease",
        key="manual_create",
        type="primary",
        disabled=bool(errors),
        on_click=_create_manual_lease,
    )


# ----------------------- editing a rejected (Draft) lease ------------------- #
def _save_edited_lease(case_id: int) -> None:
    """Button callback: save the corrected values, recalculate and resubmit the lease for review."""
    current = st.session_state["user"]
    prefix = "edit_{}_".format(case_id)
    values = _form_values(prefix)
    errors, _ = rules.validate_manual_values(values)
    if errors:
        set_flash("error", "; ".join(errors))
        return
    framework = st.session_state.get(prefix + "framework") or "BOTH"
    override = st.session_state.get(prefix + "override") or None
    try:
        with get_session() as session:
            summary = resubmit_edited_lease(session, case_id, current["user_id"], current["role"], values, framework, override)
    except (LookupError, ValueError, PermissionError) as exc:
        set_flash("error", str(exc))
        return
    _clear_form_state(prefix, keep=prefix + "save")
    set_flash(
        "success",
        "Lease corrected and recalculated ({} field(s) changed). It is back in 'Pending Review'.".format(len(summary["changed_fields"])),
    )
    open_view("results", case_id)


def render_edit_form(user: dict, case_id: int) -> None:
    """Correct a rejected lease that was entered by hand or imported in bulk, then resubmit it."""
    if "edit" not in user.get("rights", []):
        st.error("You have view-only access, so you cannot change leases. Ask an Admin if you need to edit.")
        return
    try:
        with get_session() as session:
            data = get_lease_edit_values(session, case_id, user["user_id"])
    except LookupError:
        st.error("Lease not found.")
        return
    st.title("Edit lease - {}".format(data["lease_ref"] or "#{}".format(case_id)))
    if data["status"] != "Draft":
        st.info("Only a rejected lease can be edited (this lease is '{}').".format(data["status"]))
        st.button("View results", key="edit_to_results", on_click=open_view, args=("results", case_id))
        return
    if data["rejection_reason"]:
        st.error("Rejected: {}".format(data["rejection_reason"]))
    st.caption(
        "Correct whatever is wrong, then press 'Save changes and resubmit'. The lease is checked, recalculated and "
        "sent for review again. Every change is recorded in the audit log."
    )
    prefix = "edit_{}_".format(case_id)
    values = _render_form_fields(prefix, user, initial=data["values"])
    _render_reporting_options(prefix, data["framework"], data["override"])
    errors = _show_form_checks(values)
    st.button(
        "Save changes and resubmit",
        key=prefix + "save",
        type="primary",
        disabled=bool(errors),
        on_click=_save_edited_lease,
        args=(case_id,),
    )


# ------------------------------ the review screen --------------------------- #
def _widget(key: str, label: str, kind: str, default, widget_key: str, visibility: str = "collapsed"):
    """The input widget for one field; returns the raw widget value."""
    if kind == "date":
        if default is not None and not (_MIN_DATE <= default <= _MAX_DATE):
            default = None  # outside the allowed range: leave empty for the user to fill in
        return st.date_input(
            label, value=default, min_value=_MIN_DATE, max_value=_MAX_DATE, format="DD/MM/YYYY", key=widget_key,
            label_visibility=visibility,
        )
    if kind == "amount":
        return st.number_input(
            label, min_value=0.0, value=default, step=1000.0, format="%.2f", key=widget_key, label_visibility=visibility
        )
    if kind == "percent":
        if default is not None and not (0.0 <= default <= 100.0):
            default = None  # not a sensible percentage: leave empty for the user to fill in
        return st.number_input(
            label, min_value=0.0, max_value=100.0, value=default, step=0.25, format="%.2f", key=widget_key,
            label_visibility=visibility,
        )
    if kind == "int":
        return st.number_input(label, min_value=0, value=default, step=1, key=widget_key, label_visibility=visibility)
    if kind == "currency":
        index = CURRENCY_CODES.index(default) if default in CURRENCY_CODES else 0
        return st.selectbox(
            label, CURRENCY_CODES, index=index, format_func=currency_label, key=widget_key, label_visibility=visibility
        )
    if kind == "yn":
        options = ["Y", "N"]
        return st.radio(
            label,
            options,
            index=options.index(default) if default in options else None,
            horizontal=True,
            format_func=lambda v: "Yes" if v == "Y" else "No",
            key=widget_key,
            label_visibility=visibility,
        )
    if kind == "longtext":
        return st.text_area(label, value=default or "", key=widget_key, label_visibility=visibility)
    return st.text_input(label, value=default or "", key=widget_key, label_visibility=visibility)


def _render_field(
    case_id: int, key: str, label: str, kind: str, info: dict, default_currency: str = "INR", validated_before: bool = False
):
    """One review row: the lease's own words (left), the editable value plus any flag (right).

    ``validated_before``: the lease was confirmed once already (then rejected), so the value confirmed last
    time is shown, not the AI value."""
    ai_value = rules.parse_stored(kind, info.get("ai_value"))
    confirmed = rules.parse_stored(kind, info.get("final_value")) if validated_before else None
    if validated_before:
        prefill = confirmed if confirmed is not None else rules.default_value(key, kind, default_currency)
    else:
        prefill = ai_value if ai_value is not None else rules.default_value(key, kind, default_currency)
    default = rules.to_widget(kind, prefill)
    confidence = info.get("confidence") or "Low"
    left, right = st.columns(2)
    with left:
        st.markdown("**{}**".format(label))
        snippet = info.get("source_snippet")
        if snippet:
            st.markdown("> {}".format(snippet.replace("$", "\\$")))
        else:
            st.caption("No matching text found in the document.")
        if info.get("note"):
            st.caption("Note: {}".format(info["note"]))
    with right:
        widget = _widget(key, label, kind, default, "val_{}_{}".format(case_id, key))
        needed = key in rules.REQUIRED_FIELDS
        if validated_before:
            if info.get("ai_value") not in (None, "") and not rules.values_equal(kind, ai_value, confirmed):
                st.caption("The value you confirmed last time is shown. The AI had found: {}".format(info["ai_value"]))
        elif kind == "currency" and ai_value is None and info.get("ai_value"):
            st.warning(
                "The lease says '{}', which is not in the list. Shown as {} (your default currency) - please choose.".format(
                    info["ai_value"], prefill
                )
            )
        elif kind == "currency" and ai_value is None:
            st.warning("Not found in the lease. Shown as {} (your default currency) - please confirm.".format(prefill))
        elif ai_value is None and key in rules.DEFAULT_ZERO_FIELDS:
            st.warning("Not found in the lease. Shown as 0 - please confirm.")
        elif ai_value is None and needed:
            st.warning("Not found in the lease - please enter it.")
        elif ai_value is None:
            st.caption("Not found in the lease.")
        elif confidence == "Low":
            st.warning("Low confidence - please check this value.")
        elif confidence == "Medium":
            st.info("Medium confidence - please double-check.")
    return rules.from_widget(kind, widget)


def render_review(user: dict, case_id: int) -> None:
    """The validation screen for a Draft lease that came from an uploaded document."""
    if "edit" not in user.get("rights", []):
        st.error("You have view-only access, so you cannot change leases. Ask an Admin if you need to edit.")
        return
    try:
        with get_session() as session:
            data = get_review_data(session, case_id, user["user_id"])
    except LookupError:
        st.error("Lease not found.")
        return
    case, fields = data["case"], data["fields"]
    st.title("Review and validate - {}".format(case["lease_ref"] or "#{}".format(case_id)))

    if case["status"] != "Draft":
        st.info("This lease has already been validated (status: {}).".format(case["status"]))
        st.button("View results", key="review_to_results", on_click=open_view, args=("results", case_id))
        return
    if not fields:
        st.warning("This lease has no extracted data to validate.")
        return

    st.caption(
        "Check every value against what the AI found in the document. Edit anything that is wrong. "
        "Nothing is calculated until you press 'Confirm & Proceed'."
    )
    if data["document"]["text"]:
        with st.expander("Original document text ({})".format(data["document"]["filename"] or "uploaded file")):
            st.text_area(
                "Document text", value=data["document"]["text"], height=300, disabled=True,
                label_visibility="collapsed", key="doc_text_{}".format(case_id),
            )

    if case.get("rejection_reason"):
        st.error("Rejected: {}".format(case["rejection_reason"]))
        st.caption("Correct whatever is wrong below and press 'Confirm & Proceed' to recalculate and resubmit the lease.")
    validated_before = any(info.get("final_value") is not None for info in fields.values())

    header_left, header_right = st.columns(2)
    header_left.markdown("##### Found in the lease document")
    header_right.markdown("##### Value to use (edit if needed)")

    values = {}
    for title, section_fields in rules.REVIEW_SECTIONS:
        st.markdown("#### {}".format(title))
        for key, label, kind in section_fields:
            values[key] = _render_field(
                case_id, key, label, kind, fields.get(key, {}), user.get("default_currency", "INR"), validated_before
            )

    st.divider()
    errors, warnings = rules.validate_values(values)
    for message in errors:
        st.error(message)
    for message in warnings:
        st.warning(message)

    if st.button("Confirm & Proceed", key="confirm_validation", type="primary", disabled=bool(errors)):
        try:
            with get_session() as session:
                summary = confirm_validation(session, case_id, user["user_id"], user["role"], values)
        except (LookupError, ValueError, PermissionError) as exc:
            st.error(str(exc))
        else:
            set_flash(
                "success",
                "Validated and calculated. {} field(s) changed from the AI value. The lease is now 'Pending Review'.".format(
                    len(summary["changed_fields"])
                ),
            )
            open_view("results", case_id)
            st.rerun()


# ----------------------------- the results screen --------------------------- #
def amount_table(frame: pd.DataFrame, currency=None, style: str = "indian"):
    """A table whose decimal columns show grouped amounts (5,00,000.00 or 500,000.00).

    Uses a pandas Styler, so the cells stay numeric (right-aligned, sortable) while the text
    shown follows the user's number format and the currency's decimals. Integer columns
    (Period, Year, Term...) are left alone.
    """
    decimals = currency_decimals(currency) if currency else 2
    formats = {
        column: (lambda value, d=decimals: format_number(value, style, d))
        for column in frame.columns
        if pd.api.types.is_float_dtype(frame[column])
    }
    return frame.style.format(formats, na_rep="-") if formats else frame


def _render_overview(calc: dict, classification: dict, currency: str, style: str) -> None:
    def money(value):
        return format_money(value, currency, style)

    top, bottom = st.columns(2), st.columns(2)  # two rows of two, so long amounts are not cut off
    top[0].metric("Lease liability (initial)", money(calc["lease_liability_initial"]))
    top[1].metric("ROU asset (initial)", money(calc["rou_asset_gross"]))
    bottom[0].metric("Security deposit (PV)", money(calc["security_deposit_pv"]))
    bottom[1].metric("ASC 842 classification", classification["asc842_classification"].title())

    if classification.get("is_override"):
        computed = "FINANCE LEASE" if any(t["met"] == "Y" for t in classification["tests"]) else "OPERATING LEASE"
        st.warning(
            "The ASC 842 classification was set manually (classification override). "
            "The five tests below would have given: {}.".format(computed)
        )

    with st.expander("Classification result and rationale", expanded=True):
        st.markdown("**ASC 842: {}**".format(classification["asc842_classification"]))
        st.caption("A lease is a finance lease if ANY of the five tests is met.")
        st.dataframe(pd.DataFrame(format_tests(classification["tests"])), hide_index=True)
        st.markdown("**Ind AS 116: {}**".format(classification["ind_as116_exemption"]))
        st.write(classification["ind_as116_rationale"])
        method = classification["rou_method"]
        st.caption(
            "ASC 842 view uses the {} method; Ind AS 116 always uses gross cost and accumulated amortization.".format(
                "gross cost / accumulated amortization" if method == "gross_accum" else "single lease cost / direct ROU reduction"
            )
        )


def _render_schedules(results: dict, currency: str, style: str) -> None:
    tabs = st.tabs([FRAMEWORK_LABELS[fw] for fw in FRAMEWORKS])
    for tab, framework in zip(tabs, FRAMEWORKS):
        with tab:
            schedule = results["schedules"][framework]
            if schedule["rows"]:
                frame = schedule_frame(schedule["rows"], schedule["rou_method"])
                st.dataframe(amount_table(frame, currency, style), hide_index=True)


def _render_journal(results: dict, case_id: int, currency: str, style: str) -> None:
    journal = results["journal"]
    st.markdown("**Day 1** (three separately balanced legs)")
    for letter, title in (("A", "Leg A - lease liability and ROU asset"), ("B", "Leg B - security deposit paid"), ("C", "Leg C - deposit remeasured to present value")):
        lines = journal["day1"][letter]
        with st.expander(title):
            st.dataframe(amount_table(journal_frame(lines), currency, style), hide_index=True)
            st.caption(
                "Debits {} = Credits {}".format(
                    format_money(sum(l["debit"] for l in lines), currency, style),
                    format_money(sum(l["credit"] for l in lines), currency, style),
                )
            )
    count = len(results["schedules"]["IND_AS_116"]["rows"])
    st.markdown("**Monthly entry**")
    period = st.number_input(
        "Period", min_value=1, max_value=max(count, 1), value=min(3, max(count, 1)), step=1, key="je_period_{}".format(case_id)
    )
    left, right = st.columns(2)
    for column, framework in zip((left, right), FRAMEWORKS):
        with column:
            st.markdown("*{}*".format(FRAMEWORK_LABELS[framework]))
            lines = journal["periodic"][framework].get(int(period), [])
            if lines:
                st.dataframe(amount_table(journal_frame(lines), currency, style), hide_index=True)


def _render_disclosures(results: dict, currency: str, style: str) -> None:
    """Maturity analysis, weighted averages and the ROU roll-forward(s) for this lease."""
    disclosures = generate_disclosures_from_stored(results, number_format=style)
    metrics = disclosures["key_metrics"]

    def money(value):
        return format_money(value, currency, style)

    st.markdown("#### Key disclosure figures")
    top, bottom = st.columns(2), st.columns(2)
    top[0].metric("Weighted average discount rate", "{:.2%}".format(metrics["weighted_average_discount_rate"]))
    top[1].metric(
        "Weighted average remaining lease term",
        "{:.0f} months ({:.1f} years)".format(
            metrics["weighted_average_remaining_months"], metrics["weighted_average_remaining_years"]
        ),
    )
    bottom[0].metric("Undiscounted future lease payments", money(metrics["undiscounted_future_payments"]))
    bottom[1].metric("Present value of payments (= lease liability)", money(metrics["present_value_of_payments"]))
    if metrics["liability_reconciles"]:
        st.caption("\u2713 Undiscounted payments less imputed interest reconcile to the initial lease liability.")
    else:
        st.error("The present value of the payments does not reconcile to the lease liability. Please review.")

    st.markdown("#### Maturity analysis - undiscounted lease payments")
    maturity = disclosures["maturity"]
    with_total = pd.concat(
        [
            maturity,
            pd.DataFrame(
                {"Year": ["Total"], "Payments": [disclosures["maturity_total"]], "Cumulative": [disclosures["maturity_total"]]}
            ),
        ],
        ignore_index=True,
    )
    st.dataframe(amount_table(with_total, currency, style), hide_index=True)
    if metrics["maturity_ties_to_payments"]:
        st.caption("\u2713 The yearly payments add up to the total undiscounted payments. Months covered by prepaid rent are excluded.")
    else:
        st.error("The maturity analysis does not add up to the undiscounted payments. Please review.")

    st.markdown("#### Reconciliation to the lease liability")
    st.dataframe(amount_table(pd.DataFrame(disclosures["reconciliation"]), currency, style), hide_index=True)

    st.markdown("#### ROU asset roll-forward")
    st.caption("Each framework uses its own format; the two formats are never mixed.")
    tabs = st.tabs([FRAMEWORK_LABELS[fw] for fw in FRAMEWORKS])
    for tab, framework in zip(tabs, FRAMEWORKS):
        with tab:
            rollforward = disclosures["rollforward"][framework]
            st.markdown("**{}**".format(rollforward["title"]))
            st.dataframe(amount_table(rollforward["table"], currency, style), hide_index=True)
            if rollforward["rou_method"] == "gross_accum":
                st.caption("Closing net carrying value: {}".format(money(rollforward["closing_net"])))
            else:
                st.caption("Net carrying value only - an operating lease has no gross cost or accumulated amortization account.")

    with st.expander("Draft disclosure narrative (for professional review)"):
        st.write(disclosures["narrative"])


def _load_memo(editor_key: str, content: str) -> None:
    """Button callback: put a saved version back into the editor."""
    st.session_state[editor_key] = content


def _render_memo(user: dict, case_id: int, results: dict, currency: str, style: str) -> None:
    """The AI technical memo: generate, edit, check the figures, and save numbered versions."""
    with get_session() as session:
        case_data = get_lease_case_data(session, case_id, user["user_id"])
        versions = list_memos(session, case_id, user["user_id"])
    facts = build_memo_facts(case_data, results, currency, style)
    editor_key = "memo_editor_{}".format(case_id)
    can_edit = "edit" in user.get("rights", [])
    if not can_edit:
        st.info("You have view-only access: you can read saved memos but not generate or save them.")

    st.caption(
        "The AI writes this memo from the validated, already-calculated figures ONLY. It never sees the contract text "
        "and never calculates anything. Every amount in the memo is checked against the calculation results below."
    )
    generate_column, template_column = st.columns(2)
    has_text = bool(st.session_state.get(editor_key, "").strip())
    if generate_column.button(
        "Regenerate memo with AI" if has_text else "Generate memo with AI", key="memo_generate_{}".format(case_id), type="primary", disabled=not can_edit
    ):
        try:
            with st.spinner("The AI is writing the memo (this can take a minute)..."):
                st.session_state[editor_key] = generate_memo(case_data, results, currency=currency, number_format=style)
        except ExtractionError as exc:
            st.error(str(exc))
            st.info("You can still press 'Use template (no AI)' to get the same six sections straight from the results.")
    if template_column.button("Use template (no AI)", key="memo_template_{}".format(case_id), disabled=not can_edit):
        st.session_state[editor_key] = build_template_memo(facts)

    text = st.text_area("Memo (you can edit it before saving)", key=editor_key, height=520)

    if text.strip():
        check = check_memo(text, facts)
        if check["ok"]:
            st.success(
                "Figure check passed: every amount in the memo appears in the calculation results, and the lease "
                "liability and ROU asset are quoted."
            )
        else:
            if check["unverified"]:
                st.warning(
                    "These numbers are NOT in the calculation results - please check or remove them: {}.".format(
                        ", ".join(check["unverified"])
                    )
                )
            if check["missing_amounts"]:
                st.warning("The memo does not quote the exact {}.".format(" or ".join(check["missing_amounts"])))
            if check["missing_sections"]:
                st.warning("Missing section(s): {}.".format(", ".join(check["missing_sections"])))

    if st.button("Save Final Memo", key="memo_save_{}".format(case_id), disabled=not text.strip() or not can_edit):
        try:
            with get_session() as session:
                saved = save_memo(session, case_id, user["user_id"], text)
        except (LookupError, ValueError) as exc:
            st.error(str(exc))
        else:
            set_flash("success", "Memo saved as version {}.".format(saved["version_number"]))
            st.rerun()

    st.markdown("#### Saved versions")
    if not versions:
        st.info("No memo has been saved for this lease yet.")
    for version in versions:
        saved_at = version["created_at"].strftime("%d-%b-%Y %H:%M") if version["created_at"] else "-"
        with st.expander("Version {} - saved {} by {}".format(version["version_number"], saved_at, version["created_by_email"] or "-")):
            st.text(version["content"])
            st.button(
                "Load into editor",
                key="memo_load_{}_{}".format(case_id, version["version_number"]),
                on_click=_load_memo,
                args=(editor_key, version["content"]),
            )


@st.cache_data(show_spinner=False)
def _export_bundle(user_id: int, case_id: int, key: str, style: str, prepared_by: str, minute: str) -> dict:
    """The lease's Excel workbook and CSV files (cached; ``key`` changes when the lease or its results change)."""
    with get_session() as session:
        data = get_lease_export_data(session, case_id, user_id)
    export = build_lease_export(data, style, prepared_by)
    return {"excel": build_lease_excel(export), "excel_name": excel_file_name(export), "csv": csv_files(export), "zip": csv_zip(export),
            "zip_name": zip_file_name(export), "rows": {name: content.count(b"\n") - 1 for name, content in csv_files(export).items()}}


def _render_export(user: dict, case_id: int, results: dict, style: str) -> None:
    """Download this lease's schedules and journal entries as an Excel workbook or as CSV files."""
    calc, case = results["calculation"], results["case"]
    key = repr((case["status"], case["currency"], calc["lease_liability_initial"], calc["rou_asset_gross"], calc["id"] if "id" in calc else 0,
                len(results["schedules"]["IND_AS_116"]["rows"]), len(results["schedules"]["ASC_842"]["rows"])))
    try:
        bundle = _export_bundle(user["user_id"], case_id, key, style, user["name"], datetime.now().strftime("%Y-%m-%d %H:%M"))
    except (LookupError, ValueError) as exc:
        st.error(str(exc))
        return
    st.caption(
        "The saved schedules and journal entries of this lease, for both frameworks. Excel is formatted for reading and printing; "
        "the CSV files are plain data for a ledger import or your own analysis."
    )
    st.markdown("#### Excel workbook")
    st.download_button(
        "Download Excel (.xlsx)", bundle["excel"], bundle["excel_name"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="export_lease_xlsx_{}".format(case_id), icon=":material/table_view:",
    )
    st.caption("Sheets: Summary, Schedule for each framework, and Journal for each framework (Day 1 legs, then every month).")
    st.markdown("#### CSV files")
    st.download_button(
        "Download all four (.zip)", bundle["zip"], bundle["zip_name"], "application/zip",
        key="export_lease_zip_{}".format(case_id), icon=":material/folder_zip:",
    )
    for name, content in bundle["csv"].items():
        label = name.replace("LeaseIQ_", "").replace(".csv", "").replace("_", " ")
        column_left, column_right = st.columns([3, 2])
        column_left.write("{}  ({} rows)".format(label, bundle["rows"][name]))
        column_right.download_button("Download CSV", content, name, "text/csv", key="export_lease_{}_{}".format(case_id, name), icon=":material/download:")
    st.caption(
        "CSV: one header row, dates as YYYY-MM-DD, plain decimals with no thousands separators, UTF-8. "
        "Every row starts with the lease ID and currency. Day 1 journal entries are the same under both frameworks."
    )


def render_results(user: dict, case_id: int) -> None:
    """The saved calculation for a validated lease: Overview, Schedules, Journal entries, Disclosures, Technical memo."""
    try:
        with get_session() as session:
            results = get_stored_results(session, case_id, user["user_id"])
    except LookupError:
        st.error("Lease not found.")
        return
    if results is None:
        st.info("This lease has no calculation results yet. Validate it first.")
        st.button("Review and validate", key="results_to_review", disabled="edit" not in user.get("rights", []), on_click=open_view, args=("review", case_id))
        return

    case = results["case"]
    currency = case.get("currency") or "INR"
    style = user.get("number_format", "indian")
    with get_session() as session:
        rejection = get_rejection_info(session, case_id, user["user_id"])
    st.title("Results - {}".format(case["lease_ref"] or "#{}".format(case_id)))
    st.caption(
        "Status: **{}**  |  Amounts in **{}**  |  Number format: {}  (change it on the Settings page)".format(
            "Rejected" if rejection else case["status"], currency_label(currency), NUMBER_FORMATS.get(style, style)
        )
    )
    if rejection:
        who = " by {}".format(rejection["rejected_by"]) if rejection["rejected_by"] else ""
        when = " on {}".format(rejection["rejected_at"].strftime("%d-%b-%Y")) if rejection["rejected_at"] else ""
        st.error("Rejected{}{}: {}".format(who, when, rejection["reason"]))
        st.caption("The figures below are from before the rejection and will be replaced when you correct and resubmit the lease.")
        st.button(
            "Edit and resubmit",
            key="results_edit_{}".format(case_id),
            type="primary",
            disabled="edit" not in user.get("rights", []),
            on_click=open_view,
            args=("review" if rejection["source"] == "upload" else "edit", case_id),
        )
    if case["status"] == "Pending Review":
        st.info("Waiting for a Reviewer to approve it (see the Approvals page).")

    overview, schedules, journal, disclosures, memo, export = st.tabs(
        ["Overview", "Schedules", "Journal entries", "Disclosures", "Technical memo", "Export"]
    )
    with overview:
        _render_overview(results["calculation"], results["classification"], currency, style)
    with schedules:
        _render_schedules(results, currency, style)
    with journal:
        _render_journal(results, case_id, currency, style)
    with disclosures:
        _render_disclosures(results, currency, style)
    with memo:
        _render_memo(user, case_id, results, currency, style)
    with export:
        _render_export(user, case_id, results, style)
