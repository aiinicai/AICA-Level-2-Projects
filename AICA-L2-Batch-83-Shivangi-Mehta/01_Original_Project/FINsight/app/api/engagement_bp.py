"""
Engagement blueprint — engagement creation/selection, entity profile,
and the Applicability Matrix (Blueprint Section E, #2-4).

Stage 5 ("Engagement creation") scope: everything in this file. No
Accounting/Audit/Tax/SEBI rule logic, no file upload/data validation
(Stages 6-7) — those stages own their own screens.
"""
from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from app.engagement.validation import (
    ACCOUNTING_FRAMEWORKS,
    ENTITY_TYPES,
    TAX_AUDIT_STATUSES,
    validate_engagement_form,
    validate_entity_profile_form,
)
from app.services import engagement_service as svc
from app.utils.currency import paise_to_rupees_float

engagement_bp = Blueprint("engagement", __name__, url_prefix="/engagement")

# Stage 18 (approved): the Applicability Matrix was redesigned from a
# detailed per-area (Entity Profile Input / System Suggestion /
# Professional Confirmation) screen covering all 6
# applicability_engine.AREAS, to a single-row Yes/No table covering only
# these three USER-SELECTABLE tasks — "Accounting Standards"/"Ind AS"
# are shown read-only (the auto-detected framework, from the Entity
# Profile screen) rather than as a task, and "SEBI/LODR" stays out of
# V1 scope exactly as before (Stage 11 scope change) — the
# `refresh_applicability()` mechanism still creates a row for every
# `applicability_engine.AREAS` entry underneath, unchanged; this route
# just no longer surfaces the other three as UI. A Yes here sets
# `Applicability.user_confirmed_status = "APPLICABLE"`, No sets
# "NOT_APPLICABLE" — the same field/values the pre-Stage-18 screen
# always used, just simplified to two choices instead of three, and now
# actually read by `engagement_service.get_enabled_review_modules()` to
# decide which review modules the one-click "Run Review" action runs
# (see app/api/review_bp.py) — previously this field was recorded but
# had no functional effect on Accounting/Audit/Tax review at all.
_TASK_AREAS = ("Audit Review", "Income Tax Review", "Tax Audit Review")
_TASK_FIELD_NAMES = {
    "Audit Review": "audit_review",
    "Income Tax Review": "income_tax_review",
    "Tax Audit Review": "tax_audit_review",
}


@engagement_bp.route("/")
def index():
    engagements = svc.list_engagements()
    current = svc.get_current_engagement(session)
    current_id = current.engagement_id if current else None
    return render_template("engagement/index.html", engagements=engagements, current_id=current_id)


@engagement_bp.route("/new", methods=["GET", "POST"])
def new():
    errors: dict = {}
    form_data = {"entity_name": "", "financial_year": ""}
    if request.method == "POST":
        form_data = {
            "entity_name": (request.form.get("entity_name") or "").strip(),
            "financial_year": (request.form.get("financial_year") or "").strip(),
        }
        errors = validate_engagement_form(form_data)
        if not errors:
            engagement = svc.create_engagement(**form_data)
            svc.set_current_engagement(session, engagement.engagement_id)
            return redirect(url_for("engagement.profile", engagement_id=engagement.engagement_id))
    return render_template("engagement/new.html", errors=errors, form_data=form_data)


@engagement_bp.route("/<int:engagement_id>/profile", methods=["GET", "POST"])
def profile(engagement_id):
    engagement = svc.get_engagement(engagement_id)
    if engagement is None:
        abort(404)

    errors: dict = {}
    if request.method == "POST":
        errors, cleaned = validate_entity_profile_form(request.form)
        if not errors:
            svc.save_entity_profile(engagement_id, cleaned)
            return redirect(url_for("engagement.applicability", engagement_id=engagement_id))
        form_values = request.form
    else:
        existing = svc.get_entity_profile(engagement_id)
        form_values = _profile_to_form_values(existing)

    return render_template(
        "engagement/profile.html",
        engagement=engagement,
        errors=errors,
        form_values=form_values,
        entity_types=ENTITY_TYPES,
        accounting_frameworks=ACCOUNTING_FRAMEWORKS,
        tax_audit_statuses=TAX_AUDIT_STATUSES,
    )


@engagement_bp.route("/<int:engagement_id>/applicability", methods=["GET", "POST"])
def applicability(engagement_id):
    engagement = svc.get_engagement(engagement_id)
    if engagement is None:
        abort(404)

    rows_by_area = {r.area: r for r in svc.list_applicability(engagement_id)}

    if request.method == "POST":
        for area in _TASK_AREAS:
            if area not in rows_by_area:
                continue  # no Applicability row yet (e.g. profile never saved) — nothing to confirm
            answer = (request.form.get(_TASK_FIELD_NAMES[area]) or "").strip().lower()
            if answer == "yes":
                svc.confirm_applicability(engagement_id, area, "APPLICABLE", None, None)
            elif answer == "no":
                svc.confirm_applicability(engagement_id, area, "NOT_APPLICABLE", None, None)
            # any other value (missing/unrecognized): leave the existing confirmation untouched
        return redirect(url_for("engagement.applicability", engagement_id=engagement_id))

    profile = svc.get_entity_profile(engagement_id)

    def task_value(area: str) -> str:
        row = rows_by_area.get(area)
        if row is None:
            return "yes"
        if row.user_confirmed_status == "APPLICABLE":
            return "yes"
        if row.user_confirmed_status == "NOT_APPLICABLE":
            return "no"
        # Not yet confirmed by a professional — default to the system
        # suggestion (today's "everything runs" behavior), so an
        # engagement nobody has touched this screen for is unaffected.
        return "yes" if row.system_suggested_status == "YES" else "no"

    tasks = [
        {"area": area, "field_name": _TASK_FIELD_NAMES[area], "value": task_value(area)}
        for area in _TASK_AREAS
    ]

    return render_template(
        "engagement/applicability.html",
        engagement=engagement,
        profile=profile,
        tasks=tasks,
    )


@engagement_bp.route("/<int:engagement_id>/select", methods=["POST"])
def select(engagement_id):
    engagement = svc.get_engagement(engagement_id)
    if engagement is None:
        abort(404)
    svc.set_current_engagement(session, engagement_id)
    return redirect(url_for("dashboard.index"))


@engagement_bp.route("/<int:engagement_id>/delete", methods=["POST"])
def delete(engagement_id):
    """Stage 20 addition: permanently removes an engagement/client and
    every row tracing back to it (see engagement_service.delete_engagement()
    for the full cascade). There is no undo — the confirming click
    happens client-side (see engagement/index.html's confirm() dialog).
    A no-op 404 if the engagement is already gone (e.g. a double
    submit)."""
    engagement = svc.get_engagement(engagement_id)
    if engagement is None:
        abort(404)

    was_current = svc.get_current_engagement(session)
    is_current = was_current is not None and was_current.engagement_id == engagement_id

    svc.delete_engagement(engagement_id)

    if is_current:
        svc.clear_current_engagement(session)

    return redirect(url_for("engagement.index"))


def _profile_to_form_values(profile) -> dict:
    """Prefill the Entity Profile form from an existing EntityProfile
    row (or blank defaults for a first-time save). Money fields are
    shown as plain rupee numbers (not the Indian-grouped display
    string) since this feeds an editable <input>, not read-only text."""
    if profile is None:
        return {
            "entity_type": "", "industry": "", "is_listed": False,
            "accounting_framework": "", "ind_as_mandated": "", "is_gst_registered": False,
            "statutory_audit_applicable": False, "tax_audit_status": "REQUIRES_REVIEW",
            "consolidated_fs_applicable": False, "prior_year_data_available": False,
            "turnover": "", "overall_materiality": "", "performance_materiality": "",
            "clearly_trivial_threshold": "",
        }

    def money(paise):
        value = paise_to_rupees_float(paise)
        return "" if value is None else str(value)

    return {
        "entity_type": profile.entity_type,
        "industry": profile.industry or "",
        "is_listed": profile.is_listed,
        "accounting_framework": profile.accounting_framework,
        "ind_as_mandated": (
            "" if profile.ind_as_mandated is None else ("yes" if profile.ind_as_mandated else "no")
        ),
        "is_gst_registered": profile.is_gst_registered,
        "statutory_audit_applicable": profile.statutory_audit_applicable,
        "tax_audit_status": profile.tax_audit_status,
        "consolidated_fs_applicable": profile.consolidated_fs_applicable,
        "prior_year_data_available": profile.prior_year_data_available,
        "turnover": money(profile.turnover),
        "overall_materiality": money(profile.overall_materiality),
        "performance_materiality": money(profile.performance_materiality),
        "clearly_trivial_threshold": money(profile.clearly_trivial_threshold),
    }
