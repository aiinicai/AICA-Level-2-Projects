# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Approval workflow, tenant-isolated queries and audit logging.

Pure database logic - no UI-framework imports. Pages call these functions and never
write their own queries, so the two rules below are enforced in ONE place:

1. Tenant isolation: every query filters by the logged-in user's id.
2. Every status transition writes an AuditLog row (user id, action, timestamp)
   in the same commit as the change itself.
"""
import json
import os
from datetime import date, datetime, timezone

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core import formatting, permissions, themes
from core import validation as rules
from core.calculation_engine import run_full_calculation
from core.results import (
    FRAMEWORKS,
    calculation_row,
    classification_row,
    group_journal,
    journal_rows,
    schedule_rows,
)
from db.models import (
    LEASE_STATUSES,
    AgreementDocument,
    AmortizationSchedule,
    AuditLog,
    CalculationResult,
    ClassificationResult,
    ExtractedFields,
    JournalEntry,
    LeaseCase,
    LeaseVersion,
    TechnicalMemo,
    User,
    UserPreference,
)

ENGINE_VERSION = "1.0"

# Draft -> Pending Review -> Approved (-> Active -> Expired / Terminated)
STATUS_TRANSITIONS = {
    "Draft": ("Pending Review",),
    "Pending Review": ("Approved", "Draft"),  # Draft here means "rejected": it can be corrected and resubmitted
    "Approved": ("Active",),
    "Active": ("Expired", "Terminated"),
    "Expired": (),
    "Terminated": (),
}

# Audit-log wording for each allowed transition
TRANSITION_ACTIONS = {
    ("Draft", "Pending Review"): "Submitted for review",
    ("Pending Review", "Approved"): "Approved",
    ("Pending Review", "Draft"): "Lease rejected",
    ("Approved", "Active"): "Activated",
    ("Active", "Expired"): "Marked expired",
    ("Active", "Terminated"): "Terminated",
}

# Approval is restricted to a Reviewer role. Single-role MVP: Admin may approve too.
APPROVER_ROLES = ("Reviewer", "Admin")


def can_approve(role) -> bool:
    return role in APPROVER_ROLES


# Only an Admin may delete a lease (and even then its audit trail is kept - see ``delete_case``).
DELETE_ROLES = ("Admin",)


def can_delete(role) -> bool:
    return role in DELETE_ROLES


def check_transition(current_status: str, new_status: str, role=None) -> None:
    """Raise if moving ``current_status`` -> ``new_status`` is not allowed for ``role``.

    ValueError: unknown status or a transition the workflow does not allow.
    PermissionError: the role may not approve.
    """
    if new_status not in LEASE_STATUSES:
        raise ValueError("Unknown status: {!r}".format(new_status))
    if new_status not in STATUS_TRANSITIONS.get(current_status, ()):
        raise ValueError("Cannot move a lease from '{}' to '{}'".format(current_status, new_status))
    if new_status == "Approved" and not can_approve(role):
        raise PermissionError("Only a Reviewer can approve a lease (your role: {})".format(role))
    if current_status == "Pending Review" and new_status == "Draft" and not can_approve(role):
        raise PermissionError("Only a Reviewer can reject a lease (your role: {})".format(role))


def display_status(status, rejection_reason=None) -> str:
    """The status to SHOW: a Draft that has a rejection reason is displayed as 'Rejected'."""
    return "Rejected" if status == "Draft" and str(rejection_reason or "").strip() else status


# --------------------------------------------------------------------------- #
# Workspaces and rights
# --------------------------------------------------------------------------- #
def workspace_id_for(session: Session, user_id: int) -> int:
    """The workspace a user works in: the Admin who owns it (an Admin's own workspace is their own ID). Leases belong to
    a workspace, so every member of it sees the same leases, while each person's actions are still recorded under their own ID.
    An unknown user is treated as their own workspace (so they see nothing)."""
    user = session.get(User, user_id)
    if user is None:
        return user_id
    return user.workspace_id or user.user_id


def user_rights(session: Session, user_id: int) -> frozenset:
    """What this user may do RIGHT NOW, read from the database (so changing someone's access, or deactivating them, takes
    effect at once). An unknown or inactive user has no rights."""
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        return frozenset()
    return permissions.rights_of(permissions.level_for(user.access_level, user.role))


def require_right(session: Session, user_id: int, right: str, what: str = "do this") -> None:
    """Raise PermissionError unless the user has ``right`` (checked in the database, never taken from the page)."""
    if right not in user_rights(session, user_id):
        raise PermissionError("You do not have permission to {}. Ask an Admin to change your access.".format(what))


# --------------------------------------------------------------------------- #
# Tenant-isolated reads
# --------------------------------------------------------------------------- #
def get_case_for_user(session: Session, case_id: int, user_id: int) -> LeaseCase:
    """Return the case if it belongs to ``user_id``; otherwise raise LookupError."""
    case = session.scalar(
        select(LeaseCase).where(LeaseCase.case_id == case_id, LeaseCase.user_id == workspace_id_for(session, user_id))
    )
    if case is None:
        raise LookupError("Lease case not found")
    return case


def get_user_cases(session: Session, user_id: int, status=None) -> list:
    """All of this user's cases, newest first; optionally only those with ``status``."""
    stmt = select(LeaseCase).where(LeaseCase.user_id == workspace_id_for(session, user_id))
    if status is not None:
        stmt = stmt.where(LeaseCase.status == status)
    stmt = stmt.order_by(LeaseCase.case_id.desc())
    return list(session.scalars(stmt).all())


def get_user_audit_log(session: Session, user_id: int, limit: int = 500) -> list:
    """Audit rows for this user: their own actions plus any event on their leases.

    Returns plain dicts (newest first) so pages can show them after the session closes.
    """
    stmt = (
        select(AuditLog, func.coalesce(LeaseCase.lease_ref, AuditLog.lease_ref), User.email)
        .outerjoin(LeaseCase, AuditLog.case_id == LeaseCase.case_id)
        .outerjoin(User, AuditLog.user_id == User.user_id)
        .where(
            or_(
                AuditLog.user_id.in_(
                    select(User.user_id).where(or_(User.user_id == workspace_id_for(session, user_id), User.workspace_id == workspace_id_for(session, user_id)))
                ),
                LeaseCase.user_id == workspace_id_for(session, user_id),
            )
        )
        .order_by(AuditLog.timestamp.desc(), AuditLog.log_id.desc())
        .limit(limit)
    )
    rows = []
    for log, lease_ref, user_email in session.execute(stmt).all():
        rows.append(
            {
                "timestamp": log.timestamp,
                "case_id": log.case_id,
                "lease_ref": lease_ref,
                "user_email": user_email,
                "action": log.action,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "details": log.details,
            }
        )
    return rows


# --------------------------------------------------------------------------- #
# Writes (each commits the change AND its audit row together)
# --------------------------------------------------------------------------- #
def create_lease_case(
    session: Session, user_id: int, lessor_name=None, lessee_name=None, asset_type=None, source="manual"
) -> LeaseCase:
    """Create a new Draft lease for ``user_id`` and log it."""
    require_right(session, user_id, "edit", "add leases")
    case = LeaseCase(
        user_id=workspace_id_for(session, user_id),
        status="Draft",
        lessor_name=lessor_name,
        lessee_name=lessee_name,
        asset_type=asset_type,
        source=source,
    )
    session.add(case)
    try:
        session.flush()  # assigns case_id
        case.lease_ref = "LS-{:04d}".format(case.case_id)
        session.add(
            AuditLog(
                case_id=case.case_id,
                user_id=user_id,
                action="Lease created",
                entity_type="LeaseCase",
                field_name="status",
                new_value="Draft",
                details="Lease {} created as Draft".format(case.lease_ref),
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return case


def _iso_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _as_text(value):
    """Store an extracted value as text (100000.0 -> '100000'); None stays None."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def create_lease_from_extraction(
    session: Session, user_id: int, filename: str, file_size: int, document_text: str, fields: dict
) -> LeaseCase:
    """Save an uploaded document and its AI-extracted fields as a NEW Draft lease.

    ``fields`` is the output of ``core.extraction.extract_lease_fields`` (``{key: {value,
    confidence, source_snippet, note}}``). Creates, in ONE commit: the LeaseCase (status
    Draft, source 'upload'), the AgreementDocument (with the raw extracted JSON), one
    ExtractedFields row per field (ai_value only; final_value stays empty until a human
    validates it) and two AuditLog rows.
    """
    require_right(session, user_id, "edit", "add leases")

    def value_of(key):
        return (fields.get(key) or {}).get("value")

    term = value_of("lease_term_months")
    currency = value_of("currency")
    case = LeaseCase(
        user_id=workspace_id_for(session, user_id),
        status="Draft",
        source="upload",
        lessor_name=(str(value_of("lessor"))[:255] if value_of("lessor") else None),
        lessee_name=(str(value_of("lessee"))[:255] if value_of("lessee") else None),
        asset_type=(str(value_of("asset_type"))[:100] if value_of("asset_type") else None),
        commencement_date=_iso_date(value_of("commencement_date")),
        end_date=_iso_date(value_of("lease_end_date")),
        term_months=int(term) if isinstance(term, (int, float)) and not isinstance(term, bool) else None,
        currency=currency.upper() if isinstance(currency, str) and len(currency.strip()) == 3 else "INR",
    )
    session.add(case)
    try:
        session.flush()  # assigns case_id
        case.lease_ref = "LS-{:04d}".format(case.case_id)

        document = AgreementDocument(
            case_id=case.case_id,
            filename=filename,
            file_type=os.path.splitext(filename)[1].lstrip(".").lower()[:10] or "unknown",
            file_size_bytes=file_size,
            extracted_text=document_text,
            raw_llm_json=json.dumps(fields, ensure_ascii=False),
            uploaded_by=user_id,
        )
        session.add(document)
        session.flush()  # assigns document_id

        for key, entry in fields.items():
            session.add(
                ExtractedFields(
                    case_id=case.case_id,
                    document_id=document.document_id,
                    field_key=key,
                    ai_value=_as_text(entry.get("value")),
                    confidence=entry.get("confidence"),
                    source_snippet=entry.get("source_snippet"),
                    is_edited=False,
                )
            )

        found = sum(1 for entry in fields.values() if entry.get("value") is not None)
        session.add(
            AuditLog(
                case_id=case.case_id,
                user_id=user_id,
                action="Lease created",
                entity_type="LeaseCase",
                field_name="status",
                new_value="Draft",
                details="Lease {} created as Draft from upload '{}'".format(case.lease_ref, filename),
            )
        )
        session.add(
            AuditLog(
                case_id=case.case_id,
                user_id=user_id,
                action="Document extracted",
                entity_type="AgreementDocument",
                details="'{}': AI found {} of {} fields".format(filename, found, len(fields)),
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return case


def _apply_transition(
    session: Session, case: LeaseCase, user_id: int, new_status: str, role=None, note=None
) -> str:
    """Change the status and add its AuditLog row to the session WITHOUT committing.
    ``note`` (for example a rejection reason) is appended to the audit details."""
    old_status = case.status
    check_transition(old_status, new_status, role)
    case.status = new_status
    session.add(
        AuditLog(
            case_id=case.case_id,
            user_id=user_id,
            action=TRANSITION_ACTIONS[(old_status, new_status)],
            entity_type="LeaseCase",
            field_name="status",
            old_value=old_status,
            new_value=new_status,
            details="Lease {}: status {} -> {}{}".format(
                case.lease_ref or case.case_id, old_status, new_status, ": {}".format(note) if note else ""
            ),
        )
    )
    return old_status


def transition_status(session: Session, case_id: int, user_id: int, new_status: str, role=None) -> LeaseCase:
    """Move the user's lease to ``new_status`` and write the AuditLog row.

    Raises LookupError (not this user's lease), ValueError (transition not allowed) or
    PermissionError (role may not approve). On any error nothing is changed or logged.
    """
    case = get_case_for_user(session, case_id, user_id)
    require_right(session, user_id, "edit" if new_status == "Pending Review" else "approve", "submit leases" if new_status == "Pending Review" else "approve leases")
    _apply_transition(session, case, user_id, new_status, role)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    return case


def submit_for_review(session: Session, case_id: int, user_id: int, role=None) -> LeaseCase:
    return transition_status(session, case_id, user_id, "Pending Review", role)


def approve_case(session: Session, case_id: int, user_id: int, role=None) -> LeaseCase:
    return transition_status(session, case_id, user_id, "Approved", role)


def approve_cases(session: Session, case_ids, user_id: int, role) -> dict:
    """Approve several Pending Review leases at once ("select all and approve").

    Each lease is approved in its OWN transaction with its own audit row (exactly like ``approve_case``), so one
    lease that cannot be approved (already approved, not Pending Review, not this user's) never blocks the others.
    Returns {"approved": [lease refs, in order], "failed": [(case_id, reason), ...]}; duplicates in ``case_ids``
    are approved once. Raises PermissionError BEFORE anything happens if the role may not approve.
    """
    if not can_approve(role):
        raise PermissionError("Only a Reviewer can approve a lease (your role: {})".format(role))
    require_right(session, user_id, "approve", "approve leases")
    approved, failed = [], []
    for case_id in dict.fromkeys(case_ids or ()):
        try:
            case = approve_case(session, case_id, user_id, role)
        except (LookupError, ValueError) as exc:
            failed.append((case_id, str(exc)))
        else:
            approved.append(case.lease_ref or "#{}".format(case.case_id))
    return {"approved": approved, "failed": failed}


def reject_case(session: Session, case_id: int, user_id: int, role, reason: str) -> LeaseCase:
    """A Reviewer sends a Pending Review lease back for correction, with a reason.

    The lease returns to Draft (shown as 'Rejected') and can be edited and resubmitted. The reason is
    stored on the lease and written to the audit log. Raises ValueError (no reason, or the lease is not
    Pending Review), PermissionError (role may not review) or LookupError (not this user's lease); on
    any error nothing is changed or logged.
    """
    text = " ".join(str(reason or "").split())
    if len(text) < 3:
        raise ValueError("Please give a reason for rejecting the lease")
    case = get_case_for_user(session, case_id, user_id)
    check_transition(case.status, "Draft", role)
    require_right(session, user_id, "approve", "reject leases")
    case.rejection_reason = text[:1000]
    _apply_transition(session, case, user_id, "Draft", role, note=text)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    return case


def get_rejection_info(session: Session, case_id: int, user_id: int):
    """{"reason", "rejected_by", "rejected_at", "source"} for a rejected lease, else None (LookupError if not this user's lease)."""
    case = get_case_for_user(session, case_id, user_id)
    if not str(case.rejection_reason or "").strip() or case.status != "Draft":
        return None
    log = session.scalar(
        select(AuditLog)
        .where(AuditLog.case_id == case_id, AuditLog.action == "Lease rejected")
        .order_by(AuditLog.log_id.desc())
    )
    who = session.get(User, log.user_id) if log is not None and log.user_id is not None else None
    return {
        "reason": case.rejection_reason,
        "rejected_by": who.email if who is not None else None,
        "rejected_at": log.timestamp if log is not None else None,
        "source": case.source,  # 'upload' leases are corrected on the review screen, the others on the edit form
    }


# --------------------------------------------------------------------------- #
# Validation screen: reading a lease's extracted fields, confirming them, reading results
# --------------------------------------------------------------------------- #
def get_case_ids_by_state(session: Session, user_id: int) -> dict:
    """{"reviewable": ids of this user's leases that have extracted fields,
        "with_results": ids that already have stored calculation results}."""
    reviewable = session.scalars(
        select(ExtractedFields.case_id)
        .join(LeaseCase, LeaseCase.case_id == ExtractedFields.case_id)
        .where(LeaseCase.user_id == workspace_id_for(session, user_id))
        .distinct()
    ).all()
    with_results = session.scalars(
        select(CalculationResult.case_id)
        .join(LeaseCase, LeaseCase.case_id == CalculationResult.case_id)
        .where(LeaseCase.user_id == workspace_id_for(session, user_id))
        .distinct()
    ).all()
    return {"reviewable": set(reviewable), "with_results": set(with_results)}


def get_review_data(session: Session, case_id: int, user_id: int) -> dict:
    """Everything the review screen needs, as plain dicts (LookupError if not this user's lease)."""
    case = get_case_for_user(session, case_id, user_id)
    rows = session.scalars(select(ExtractedFields).where(ExtractedFields.case_id == case_id)).all()
    document = session.scalar(
        select(AgreementDocument).where(AgreementDocument.case_id == case_id).order_by(AgreementDocument.document_id)
    )
    notes = {}
    if document is not None and document.raw_llm_json:
        try:
            notes = {key: (entry or {}).get("note") for key, entry in json.loads(document.raw_llm_json).items()}
        except (ValueError, AttributeError):
            notes = {}
    return {
        "case": {
            "case_id": case.case_id,
            "lease_ref": case.lease_ref,
            "status": case.status,
            "lessor_name": case.lessor_name,
            "rejection_reason": case.rejection_reason,
        },
        "fields": {
            row.field_key: {
                "ai_value": row.ai_value,
                "final_value": row.final_value,
                "confidence": row.confidence,
                "source_snippet": row.source_snippet,
                "note": notes.get(row.field_key),
            }
            for row in rows
        },
        "document": {
            "filename": document.filename if document is not None else None,
            "text": document.extracted_text if document is not None else None,
        },
    }


def _fill_case_from_values(case: LeaseCase, values: dict, inputs: dict) -> None:
    """Copy the validated lease details onto the LeaseCase (shared by validation and bulk import)."""
    case.lessor_name = (values.get("lessor") or None) and str(values["lessor"])[:255]
    case.lessee_name = (values.get("lessee") or None) and str(values["lessee"])[:255]
    case.asset_type = (values.get("asset_type") or None) and str(values["asset_type"])[:100]
    case.commencement_date = inputs["commencement_date"]
    case.term_months = inputs["lease_term_months"]
    case.end_date = values.get("lease_end_date") or rules.expected_end_date(
        inputs["commencement_date"], inputs["lease_term_months"]
    )
    currency = values.get("currency")
    if isinstance(currency, str) and len(currency.strip()) == 3:
        case.currency = currency.strip().upper()
    case.inputs_json = rules.inputs_to_json(inputs)


def _clear_calculation(session: Session, case: LeaseCase) -> None:
    """Remove the lease's stored calculation, classification, schedule and journal rows (used before they are
    recalculated after a rejection, so the old and new results never sit side by side)."""
    for model in (JournalEntry, AmortizationSchedule, ClassificationResult, CalculationResult):
        session.execute(delete(model).where(model.case_id == case.case_id))


def _store_calculation(session: Session, case: LeaseCase, inputs: dict, result: dict) -> None:
    """Store the calculation, classification, schedule (both frameworks) and journal rows, replacing any earlier ones."""
    _clear_calculation(session, case)
    session.add(CalculationResult(case_id=case.case_id, **calculation_row(result, inputs, ENGINE_VERSION)))
    session.add(ClassificationResult(case_id=case.case_id, **classification_row(result)))
    session.add_all(AmortizationSchedule(case_id=case.case_id, **row) for row in schedule_rows(result))
    session.add_all(JournalEntry(case_id=case.case_id, **row) for row in journal_rows(result, inputs["commencement_date"]))


def confirm_validation(session: Session, case_id: int, user_id: int, role, values: dict) -> dict:
    """"Confirm & Proceed": save the validated values, run the calculation, move to Pending Review.

    ``values`` maps every field key to its canonical value (see ``core.validation``).
    Everything happens in ONE transaction, and the calculation runs BEFORE anything is
    written, so any failure leaves the lease exactly as it was (still Draft, nothing logged).

    Saves: ExtractedFields.final_value (the original ``ai_value`` is KEPT for the audit trail),
    one AuditLog row per field changed from its AI value, the LeaseCase details and inputs,
    CalculationResult, ClassificationResult, AmortizationSchedule (both frameworks) and
    JournalEntry rows, and the Draft -> Pending Review transition (also audited).

    Raises LookupError (not this user's lease), ValueError (not a Draft, invalid values,
    or the calculation rejected them) or PermissionError.
    """
    require_right(session, user_id, "edit", "validate leases")
    case = get_case_for_user(session, case_id, user_id)
    if case.status != "Draft":
        raise ValueError("Only a Draft lease can be validated (this lease is '{}')".format(case.status))
    check_transition(case.status, "Pending Review", role)

    errors, _ = rules.validate_values(values)
    if errors:
        raise ValueError("; ".join(errors))
    inputs = rules.build_engine_inputs(values)
    result = run_full_calculation(inputs)  # nothing has been written yet: a failure here changes nothing

    rows = {
        row.field_key: row
        for row in session.scalars(select(ExtractedFields).where(ExtractedFields.case_id == case_id)).all()
    }
    if not rows:
        raise ValueError("This lease has no extracted fields to validate")
    user = session.get(User, user_id)
    email = user.email if user is not None else str(user_id)
    now = datetime.now(timezone.utc)

    # After a rejection the lease is validated again: then a field "changed" means changed from the value the
    # user confirmed last time, not from the AI value (the AI value is still kept for the audit trail).
    validated_before = any(row.final_value is not None for row in rows.values())
    was_rejected = bool(str(case.rejection_reason or "").strip())

    changed = []
    for key, kind in rules.FIELD_KIND.items():
        final = values.get(key)
        row = rows.get(key)
        if row is None:
            row = ExtractedFields(case_id=case.case_id, field_key=key, ai_value=None, is_edited=False)
            session.add(row)
        ai_value = rules.parse_stored(kind, row.ai_value)
        previous_raw = row.final_value if validated_before else row.ai_value
        previous = rules.parse_stored(kind, previous_raw)
        row.final_value = rules.canonical_to_text(kind, final)
        row.is_edited = not rules.values_equal(kind, ai_value, final)  # differs from what the AI found
        if not rules.values_equal(kind, previous, final):
            row.edited_by = user_id
            row.edited_at = now
            changed.append(key)
            old_text = previous_raw if previous_raw not in (None, "") else "(empty)"
            new_text = row.final_value if row.final_value is not None else "(empty)"
            session.add(
                AuditLog(
                    case_id=case.case_id,
                    user_id=user_id,
                    action="Field edited",
                    entity_type="ExtractedFields",
                    field_name=key,
                    old_value=previous_raw,
                    new_value=row.final_value,
                    details="Field {} changed from {} to {} by {}".format(key, old_text, new_text, email),
                )
            )

    _fill_case_from_values(case, values, inputs)
    _store_calculation(session, case, inputs, result)

    asc842 = result["classification"]["asc842_classification"]
    session.add(
        AuditLog(
            case_id=case.case_id,
            user_id=user_id,
            action="Validation confirmed",
            entity_type="LeaseCase",
            details="{} fields confirmed by {} ({} changed from the {}); ASC 842: {}; lease liability {:.2f}".format(
                len(rules.FIELD_KIND),
                email,
                len(changed),
                "previous value, after a rejection" if was_rejected else "AI value",
                asc842,
                result["initial"]["lease_liability_initial"],
            ),
        )
    )
    case.rejection_reason = None  # corrected and resubmitted: no longer 'Rejected'
    _apply_transition(session, case, user_id, "Pending Review", role)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {
        "changed_fields": changed,
        "asc842_classification": asc842,
        "rou_method": result["rou_method"],
        "lease_liability_initial": result["initial"]["lease_liability_initial"],
    }


def _row_to_dict(row) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def get_stored_results(session: Session, case_id: int, user_id: int):
    """The saved calculation results of a lease as plain dicts, or None if it has none yet."""
    case = get_case_for_user(session, case_id, user_id)
    calculation = session.scalar(
        select(CalculationResult).where(CalculationResult.case_id == case_id).order_by(CalculationResult.id.desc())
    )
    if calculation is None:
        return None
    classification = session.scalar(
        select(ClassificationResult).where(ClassificationResult.case_id == case_id).order_by(ClassificationResult.id.desc())
    )
    classification_data = _row_to_dict(classification)
    classification_data["tests"] = json.loads(classification_data["asc842_test_results_json"])

    schedules = {}
    for framework in FRAMEWORKS:
        rows = session.scalars(
            select(AmortizationSchedule)
            .where(AmortizationSchedule.case_id == case_id, AmortizationSchedule.framework == framework)
            .order_by(AmortizationSchedule.period)
        ).all()
        schedules[framework] = {
            "rou_method": rows[0].rou_method if rows else None,
            "rows": [_row_to_dict(row) for row in rows],
        }
    journal = session.scalars(
        select(JournalEntry).where(JournalEntry.case_id == case_id).order_by(JournalEntry.id)
    ).all()
    return {
        "case": {"case_id": case.case_id, "lease_ref": case.lease_ref, "status": case.status, "currency": case.currency},
        "calculation": _row_to_dict(calculation),
        "classification": classification_data,
        "schedules": schedules,
        "journal": group_journal([_row_to_dict(row) for row in journal]),
    }


def _create_calculated_lease(
    session: Session,
    user_id: int,
    role,
    values: dict,
    framework: str,
    override,
    source: str,
    created_text: str,
    calculated_action: str,
) -> LeaseCase:
    """Create ONE lease from structured values, calculate it and store the results (shared by bulk and manual entry).

    One transaction; the calculation runs BEFORE anything is written, so a bad lease never leaves a half-made
    record behind. The lease ends up 'Pending Review' with an audit trail. ``created_text`` may contain the placeholder ``{ref}`` (replaced by the lease ID; other braces are left alone).
    Raises ValueError (invalid values / calculation rejected them) or PermissionError.
    """
    require_right(session, user_id, "edit", "add leases")
    errors, _ = rules.validate_values(values)
    if errors:
        raise ValueError("; ".join(errors))
    inputs = rules.build_engine_inputs(values)
    result = run_full_calculation(inputs, asc842_override=override)  # nothing written yet
    check_transition("Draft", "Pending Review", role)

    case = LeaseCase(
        user_id=workspace_id_for(session, user_id),
        status="Draft",
        source=source,
        reporting_framework=framework,
        classification_override=override,
    )
    _fill_case_from_values(case, values, inputs)
    session.add(case)
    try:
        session.flush()  # assigns case_id
        case.lease_ref = "LS-{:04d}".format(case.case_id)
        session.add(
            AuditLog(
                case_id=case.case_id,
                user_id=user_id,
                action="Lease created",
                entity_type="LeaseCase",
                field_name="status",
                new_value="Draft",
                details=created_text.replace("{ref}", case.lease_ref),
            )
        )
        _store_calculation(session, case, inputs, result)
        classification = result["classification"]
        session.add(
            AuditLog(
                case_id=case.case_id,
                user_id=user_id,
                action=calculated_action,
                entity_type="LeaseCase",
                details="ASC 842: {}{}; lease liability {:.2f}".format(
                    classification["asc842_classification"],
                    " (overridden; the tests gave {})".format(classification["asc842_computed"])
                    if classification.get("is_override")
                    else "",
                    result["initial"]["lease_liability_initial"],
                ),
            )
        )
        _apply_transition(session, case, user_id, "Pending Review", role)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return case


def import_bulk_lease(
    session: Session,
    user_id: int,
    role,
    values: dict,
    framework: str = "BOTH",
    override=None,
    filename=None,
    source_row=None,
) -> LeaseCase:
    """Create ONE lease from a bulk-import row (already checked by ``core.bulk``): calculated, Pending Review,
    source 'bulk'. No AI and no validation screen. See ``_create_calculated_lease`` for the guarantees."""
    where = "'{}'{}".format(filename or "bulk file", " row {}".format(source_row) if source_row else "")
    return _create_calculated_lease(
        session, user_id, role, values, framework, override,
        source="bulk", created_text="Lease {ref} imported from " + where, calculated_action="Calculated (bulk import)",
    )


def create_manual_lease(
    session: Session, user_id: int, role, values: dict, framework: str = "BOTH", override=None
) -> LeaseCase:
    """Create ONE lease from the values the user typed into the manual form: calculated, Pending Review,
    source 'manual'. The same rules as the validation screen and bulk import apply, and lessor and lessee
    are required (a lease with no parties is not a usable record).

    Raises ValueError (missing lessor/lessee, invalid values or framework) or PermissionError.
    """
    missing = [label for key, label in (("lessor", "Lessor"), ("lessee", "Lessee")) if not str(values.get(key) or "").strip()]
    if missing:
        raise ValueError("{} {}".format(" and ".join(missing), "are required" if len(missing) > 1 else "is required"))
    if framework not in ("IND_AS_116", "ASC_842", "BOTH"):
        raise ValueError("Unknown reporting framework: {!r}".format(framework))
    return _create_calculated_lease(
        session, user_id, role, values, framework, override,
        source="manual", created_text="Lease {ref} created by manual entry", calculated_action="Calculated (manual entry)",
    )


def get_lease_edit_values(session: Session, case_id: int, user_id: int) -> dict:
    """What the edit form starts with for a saved lease: its values (rebuilt from what was stored),
    reporting framework, classification override and, if it was rejected, the reason.

    LookupError if it is not this user's lease.
    """
    case = get_case_for_user(session, case_id, user_id)
    try:
        inputs = json.loads(case.inputs_json or "{}")
    except ValueError:
        inputs = {}
    record = {
        "lessor": case.lessor_name,
        "lessee": case.lessee_name,
        "asset_type": case.asset_type,
        "currency": case.currency,
        "end_date": case.end_date,
    }
    return {
        "case_id": case.case_id,
        "lease_ref": case.lease_ref,
        "status": case.status,
        "source": case.source,
        "rejection_reason": case.rejection_reason,
        "framework": case.reporting_framework,
        "override": case.classification_override,
        "values": rules.values_from_stored(record, inputs),
    }


def resubmit_edited_lease(
    session: Session, case_id: int, user_id: int, role, values: dict, framework: str = "BOTH", override=None
) -> dict:
    """Save the corrected values of a Draft (for example a rejected) lease, recalculate, and send it for review again.

    For leases entered by hand or imported in bulk (uploaded leases are corrected on the review screen).
    ONE transaction, and the calculation runs BEFORE anything is written: any failure changes nothing.
    Every changed field is audited ("Field currency changed from USD to INR by ..."); the old results are
    replaced; the rejection reason is cleared; the lease goes Draft -> Pending Review.

    Raises LookupError (not this user's lease), ValueError (not a Draft, lessor/lessee missing, invalid values
    or framework, or the calculation rejected them) or PermissionError.
    """
    require_right(session, user_id, "edit", "edit leases")
    case = get_case_for_user(session, case_id, user_id)
    if case.status != "Draft":
        raise ValueError("Only a rejected (Draft) lease can be edited (this lease is '{}')".format(case.status))
    check_transition(case.status, "Pending Review", role)
    missing = [label for key, label in (("lessor", "Lessor"), ("lessee", "Lessee")) if not str(values.get(key) or "").strip()]
    if missing:
        raise ValueError("{} {}".format(" and ".join(missing), "are required" if len(missing) > 1 else "is required"))
    if framework not in ("IND_AS_116", "ASC_842", "BOTH"):
        raise ValueError("Unknown reporting framework: {!r}".format(framework))
    errors, _ = rules.validate_values(values)
    if errors:
        raise ValueError("; ".join(errors))
    inputs = rules.build_engine_inputs(values)
    result = run_full_calculation(inputs, asc842_override=override)  # nothing written yet

    before = get_lease_edit_values(session, case_id, user_id)
    user = session.get(User, user_id)
    email = user.email if user is not None else str(user_id)
    changes = []
    for key, kind in rules.FIELD_KIND.items():
        if key in ("options", "cpi_details"):
            continue  # information-only text is not stored, so there is nothing to compare
        if not rules.values_equal(kind, before["values"].get(key), values.get(key)):
            changes.append(
                (key, rules.canonical_to_text(kind, before["values"].get(key)), rules.canonical_to_text(kind, values.get(key)))
            )
    if framework != before["framework"]:
        changes.append(("reporting_framework", before["framework"], framework))
    if (override or None) != (before["override"] or None):
        changes.append(("classification_override", before["override"], override or None))

    for key, old, new in changes:
        session.add(
            AuditLog(
                case_id=case.case_id,
                user_id=user_id,
                action="Field edited",
                entity_type="LeaseCase",
                field_name=key,
                old_value=old,
                new_value=new,
                details="Field {} changed from {} to {} by {}".format(
                    key, old if old not in (None, "") else "(empty)", new if new not in (None, "") else "(empty)", email
                ),
            )
        )
    case.reporting_framework = framework
    case.classification_override = override or None
    _fill_case_from_values(case, values, inputs)
    _store_calculation(session, case, inputs, result)
    was_rejected = bool(str(case.rejection_reason or "").strip())
    case.rejection_reason = None
    classification = result["classification"]
    session.add(
        AuditLog(
            case_id=case.case_id,
            user_id=user_id,
            action="Lease edited",
            entity_type="LeaseCase",
            details="{} field(s) changed by {}{}; ASC 842: {}; lease liability {:.2f}".format(
                len(changes),
                email,
                " after a rejection" if was_rejected else "",
                classification["asc842_classification"],
                result["initial"]["lease_liability_initial"],
            ),
        )
    )
    _apply_transition(session, case, user_id, "Pending Review", role)
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {
        "changed_fields": [key for key, _, _ in changes],
        "asc842_classification": classification["asc842_classification"],
        "rou_method": result["rou_method"],
        "lease_liability_initial": result["initial"]["lease_liability_initial"],
    }


# --------------------------------------------------------------------------- #
# Display preferences (number format and default currency)
# --------------------------------------------------------------------------- #
def get_user_preferences(session: Session, user_id: int) -> dict:
    """The user's display preferences: number_format, default_currency, theme and dashboard_layout
    (the defaults if nothing was saved yet)."""
    row = session.get(UserPreference, user_id)
    if row is None:
        return {
            "number_format": formatting.DEFAULT_NUMBER_FORMAT,
            "default_currency": formatting.DEFAULT_CURRENCY,
            "theme": themes.DEFAULT_THEME,
            "dashboard_layout": themes.DEFAULT_LAYOUT,
        }
    return {
        "number_format": row.number_format,
        "default_currency": row.default_currency,
        "theme": row.theme if row.theme in themes.THEMES else themes.DEFAULT_THEME,
        "dashboard_layout": row.dashboard_layout if row.dashboard_layout in themes.LAYOUTS else themes.DEFAULT_LAYOUT,
    }


def save_user_preferences(
    session: Session,
    user_id: int,
    number_format: str,
    default_currency: str,
    theme: str = None,
    dashboard_layout: str = None,
) -> dict:
    """Validate and save the user's display preferences; each real change is audited.

    ``theme`` and ``dashboard_layout`` are optional: left as None they keep their current value.
    Raises ValueError for an unknown number format, currency, theme or layout (nothing is saved).
    """
    if number_format not in formatting.NUMBER_FORMATS:
        raise ValueError("Unknown number format: {!r}".format(number_format))
    code = formatting.parse_currency(default_currency)
    if code is None:
        raise ValueError("Unsupported currency: {!r}".format(default_currency))
    before = get_user_preferences(session, user_id)
    theme = before["theme"] if theme is None else themes.validate_theme(theme)
    layout = before["dashboard_layout"] if dashboard_layout is None else themes.validate_layout(dashboard_layout)

    row = session.get(UserPreference, user_id)
    if row is None:
        row = UserPreference(
            user_id=user_id, number_format=number_format, default_currency=code, theme=theme, dashboard_layout=layout
        )
        session.add(row)
    else:
        row.number_format = number_format
        row.default_currency = code
        row.theme = theme
        row.dashboard_layout = layout
    for field, old, new, label in (
        ("number_format", before["number_format"], number_format, "Number format"),
        ("default_currency", before["default_currency"], code, "Default currency"),
        ("theme", before["theme"], theme, "Theme"),
        ("dashboard_layout", before["dashboard_layout"], layout, "Dashboard layout"),
    ):
        if old != new:
            session.add(
                AuditLog(
                    user_id=user_id,
                    action="Preference changed",
                    entity_type="UserPreference",
                    field_name=field,
                    old_value=old,
                    new_value=new,
                    details="{} changed from {} to {}".format(label, old, new),
                )
            )
    try:
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"number_format": number_format, "default_currency": code, "theme": theme, "dashboard_layout": layout}


# --------------------------------------------------------------------------- #
# Technical memo: inputs for the writer, and versioned saving
# --------------------------------------------------------------------------- #
def get_lease_case_data(session: Session, case_id: int, user_id: int) -> dict:
    """The lease's validated details for the memo writer: the saved engine inputs plus the lease record.

    Contains validated figures only - never the contract text. (LookupError if not this user's lease.)
    """
    case = get_case_for_user(session, case_id, user_id)
    data = {}
    if case.inputs_json:
        try:
            data.update(json.loads(case.inputs_json))
        except ValueError:
            data = {}
    data.update(
        {
            "lease_ref": case.lease_ref,
            "status": display_status(case.status, case.rejection_reason),
            "lessor": case.lessor_name,
            "lessee": case.lessee_name,
            "asset_type": case.asset_type,
            "currency": case.currency,
            "commencement_date": case.commencement_date,
            "end_date": case.end_date,
            "term_months": case.term_months,
            "reporting_framework": case.reporting_framework,
            "classification_override": case.classification_override,
        }
    )
    return data


def save_memo(session: Session, case_id: int, user_id: int, content: str) -> dict:
    """Save the memo as the NEXT version for this lease (1, 2, 3...) and audit it.

    Raises LookupError (not this user's lease) or ValueError (empty / too short).
    """
    require_right(session, user_id, "edit", "save memos")
    get_case_for_user(session, case_id, user_id)
    text = (content or "").strip()
    if len(text) < 50:
        raise ValueError("The memo is empty or too short to save")
    latest = session.scalar(select(func.max(TechnicalMemo.version_number)).where(TechnicalMemo.case_id == case_id)) or 0
    memo = TechnicalMemo(case_id=case_id, version_number=latest + 1, content=text, is_final=True, created_by=user_id)
    session.add(memo)
    user = session.get(User, user_id)
    session.add(
        AuditLog(
            case_id=case_id,
            user_id=user_id,
            action="Technical memo saved",
            entity_type="TechnicalMemo",
            new_value=str(latest + 1),
            details="Version {} of the technical memo saved by {} ({} characters)".format(
                latest + 1, user.email if user is not None else user_id, len(text)
            ),
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("Another save happened at the same time. Please try again.") from None
    except Exception:
        session.rollback()
        raise
    return {"memo_id": memo.memo_id, "version_number": memo.version_number, "created_at": memo.created_at}


def list_memos(session: Session, case_id: int, user_id: int) -> list:
    """All saved memo versions of this user's lease, newest first, as plain dicts."""
    get_case_for_user(session, case_id, user_id)
    stmt = (
        select(TechnicalMemo, User.email)
        .outerjoin(User, TechnicalMemo.created_by == User.user_id)
        .where(TechnicalMemo.case_id == case_id)
        .order_by(TechnicalMemo.version_number.desc())
    )
    return [
        {
            "memo_id": memo.memo_id,
            "version_number": memo.version_number,
            "content": memo.content,
            "is_final": memo.is_final,
            "created_at": memo.created_at,
            "created_by_email": email,
        }
        for memo, email in session.execute(stmt).all()
    ]


# --------------------------------------------------------------------------- #
# Dashboard: what the page needs, always limited to the logged-in user's own leases
# --------------------------------------------------------------------------- #
def get_dashboard_leases(session: Session, user_id: int) -> list:
    """One dict per lease (newest first) with the facts the dashboard needs, incl. its ASC 842 classification."""
    classifications = dict(
        session.execute(
            select(ClassificationResult.case_id, ClassificationResult.asc842_classification)
            .join(LeaseCase, LeaseCase.case_id == ClassificationResult.case_id)
            .where(LeaseCase.user_id == workspace_id_for(session, user_id))
        ).all()
    )
    liabilities = dict(
        session.execute(
            select(CalculationResult.case_id, CalculationResult.lease_liability_initial)
            .join(LeaseCase, LeaseCase.case_id == CalculationResult.case_id)
            .where(LeaseCase.user_id == workspace_id_for(session, user_id))
        ).all()
    )
    return [
        {
            "case_id": case.case_id,
            "lease_ref": case.lease_ref or "#{}".format(case.case_id),
            "status": display_status(case.status, case.rejection_reason),
            "currency": case.currency or "INR",
            "lessor": case.lessor_name or "",
            "lessee": case.lessee_name or "",
            "asset_type": case.asset_type or "",
            "source": case.source,
            "commencement_date": case.commencement_date,
            "created_at": case.created_at,
            "classification": classifications.get(case.case_id),
            "lease_liability_initial": liabilities.get(case.case_id),
            "has_results": case.case_id in liabilities,
        }
        for case in get_user_cases(session, user_id)
    ]


def get_dashboard_schedule_rows(session: Session, user_id: int, framework: str = "ASC_842") -> list:
    """The saved schedule rows (dicts) of this user's leases for ONE framework: ASC_842 or IND_AS_116."""
    if framework not in FRAMEWORKS:
        raise ValueError("framework must be one of {}, got {!r}".format(", ".join(FRAMEWORKS), framework))
    stmt = (
        select(
            AmortizationSchedule.case_id,
            AmortizationSchedule.period_date,
            AmortizationSchedule.net_cash_payment,
            AmortizationSchedule.interest_expense,
            AmortizationSchedule.principal_repayment,
            AmortizationSchedule.closing_liability,
            AmortizationSchedule.amortization_expense,
            AmortizationSchedule.single_lease_cost,
            AmortizationSchedule.rou_net_carrying_value,
        )
        .join(LeaseCase, LeaseCase.case_id == AmortizationSchedule.case_id)
        .where(LeaseCase.user_id == workspace_id_for(session, user_id), AmortizationSchedule.framework == framework)
        .order_by(AmortizationSchedule.case_id, AmortizationSchedule.period)
    )
    return [dict(row) for row in session.execute(stmt).mappings().all()]


def get_dashboard_stamp(session: Session, user_id: int) -> tuple:
    """A cheap fingerprint of the user's data: it changes when a lease is added, changed or calculated,
    so the dashboard's cached numbers refresh exactly when they should."""
    count, latest = session.execute(
        select(func.count(LeaseCase.case_id), func.max(LeaseCase.updated_at)).where(LeaseCase.user_id == workspace_id_for(session, user_id))
    ).one()
    results = session.scalar(
        select(func.count(CalculationResult.id))
        .select_from(CalculationResult)
        .join(LeaseCase, LeaseCase.case_id == CalculationResult.case_id)
        .where(LeaseCase.user_id == workspace_id_for(session, user_id))
    )
    return (int(count or 0), str(latest), int(results or 0))


def count_user_leases_in_status(session: Session, user_id: int, status: str) -> int:
    """How many of this user's leases are in ``status`` (e.g. the Approvals badge)."""
    return int(
        session.scalar(select(func.count(LeaseCase.case_id)).where(LeaseCase.user_id == workspace_id_for(session, user_id), LeaseCase.status == status))
        or 0
    )


def count_ai_extractions_since(session: Session, user_id: int, since: datetime) -> int:
    """How many documents this user has had read by the AI since ``since`` (the 'Plan & Usage' box)."""
    return int(
        session.scalar(
            select(func.count(AuditLog.log_id)).where(
                AuditLog.user_id == user_id, AuditLog.action == "Document extracted", AuditLog.timestamp >= since
            )
        )
        or 0
    )


# --------------------------------------------------------------------------- #
# Reports: the data the disclosure report is built from (the user's own leases only)
# --------------------------------------------------------------------------- #
_REPORT_SCHEDULE_COLUMNS = (
    "period", "period_date", "rou_method", "net_cash_payment", "opening_liability", "interest_expense", "principal_repayment",
    "closing_liability", "rou_gross_cost", "accum_amortization_closing", "amortization_expense", "single_lease_cost",
    "rou_reduction_plug", "rou_net_carrying_value",
)


def get_report_inputs(
    session: Session,
    user_id: int,
    framework: str,
    currency: str,
    statuses,
    case_ids=None,
    include_memo: bool = True,
) -> list:
    """One dict per lease for ``core.reports.build_disclosure_report``, for ONE currency and ONE framework.

    Only this user's leases that have saved calculation results, are in ``currency`` and have a status in ``statuses``
    (and, if given, are in ``case_ids``). Each dict carries the lease's details, its Ind AS 116 / ASC 842 treatment, its
    saved schedule for ``framework`` and - if ``include_memo`` - its latest saved memo, or (when it has none) what is
    needed to generate one from its results. Raises ValueError for an unknown framework.
    """
    if framework not in FRAMEWORKS:
        raise ValueError("framework must be one of {}, got {!r}".format(", ".join(FRAMEWORKS), framework))
    code = formatting.parse_currency(currency) or str(currency).strip().upper()
    wanted = None if case_ids is None else set(case_ids)
    with_results = get_case_ids_by_state(session, user_id)["with_results"]
    cases = [
        case
        for case in get_user_cases(session, user_id)
        if case.case_id in with_results
        and (case.currency or "INR") == code
        and case.status in statuses
        and (wanted is None or case.case_id in wanted)
    ]
    if not cases:
        return []
    ids = [case.case_id for case in cases]
    classifications = {
        row.case_id: row for row in session.scalars(select(ClassificationResult).where(ClassificationResult.case_id.in_(ids))).all()
    }
    calculations = {
        row.case_id: row for row in session.scalars(select(CalculationResult).where(CalculationResult.case_id.in_(ids))).all()
    }
    schedules = {}
    for row in session.scalars(
        select(AmortizationSchedule)
        .where(AmortizationSchedule.case_id.in_(ids), AmortizationSchedule.framework == framework)
        .order_by(AmortizationSchedule.case_id, AmortizationSchedule.period)
    ).all():
        schedules.setdefault(row.case_id, []).append({column: getattr(row, column) for column in _REPORT_SCHEDULE_COLUMNS})
    latest_memo = {}
    if include_memo:
        for memo in session.scalars(
            select(TechnicalMemo).where(TechnicalMemo.case_id.in_(ids)).order_by(TechnicalMemo.case_id, TechnicalMemo.version_number.desc())
        ).all():
            latest_memo.setdefault(memo.case_id, {"version": memo.version_number, "text": memo.content})

    leases = []
    for case in sorted(cases, key=lambda c: c.case_id):
        try:
            inputs = json.loads(case.inputs_json or "{}")
        except ValueError:
            inputs = {}
        classification, calculation = classifications.get(case.case_id), calculations.get(case.case_id)
        rows = schedules.get(case.case_id, [])
        lease = {
            "case_id": case.case_id,
            "lease_ref": case.lease_ref or "#{}".format(case.case_id),
            "status": case.status,
            "currency": case.currency or "INR",
            "lessor": case.lessor_name or "",
            "lessee": case.lessee_name or "",
            "asset_type": case.asset_type or "",
            "commencement_date": case.commencement_date,
            "end_date": case.end_date,
            "term_months": case.term_months,
            "ibr": inputs.get("ibr"),
            "classification": classification.asc842_classification if classification else None,
            "ind_as116_exemption": classification.ind_as116_exemption if classification else None,
            "rou_method": rows[0]["rou_method"] if rows else None,
            "single_lease_cost_per_month": calculation.single_lease_cost_per_month if calculation else None,
            "schedule": rows,
            "memo": latest_memo.get(case.case_id),
        }
        if include_memo and lease["memo"] is None:
            lease["memo_stored"] = get_stored_results(session, case.case_id, user_id)
            lease["case_data"] = get_lease_case_data(session, case.case_id, user_id)
        leases.append(lease)
    return leases


# --------------------------------------------------------------------------- #
# Deleting a lease (Admin only) - the audit trail is KEPT
# --------------------------------------------------------------------------- #
def delete_case(session: Session, case_id: int, user_id: int, role, reason: str) -> dict:
    """Permanently delete one of the user's leases and everything calculated for it. Admin only.

    The AUDIT LOG IS KEPT: every audit row of the lease is detached from it (``case_id`` -> NULL) and stamped with the
    lease's ID (``lease_ref``) BEFORE the lease is removed, so no database cascade can take the history with it, and one
    new "Lease deleted" row records who deleted it, when, why and what was removed. Everything happens in ONE transaction.

    Raises PermissionError (not an Admin), ValueError (no reason, or the lease has amendments), LookupError (not this
    user's lease). On any error nothing is changed.
    Returns {"lease_ref", "removed": {"schedule rows": n, ...}}.
    """
    if not can_delete(role):
        raise PermissionError("Only an Admin can delete a lease (your role: {})".format(role))
    require_right(session, user_id, "delete", "delete leases")
    text = " ".join(str(reason or "").split())
    if len(text) < 3:
        raise ValueError("Please give a reason for deleting the lease")
    case = get_case_for_user(session, case_id, user_id)
    has_children = session.scalar(select(func.count(LeaseCase.case_id)).where(LeaseCase.parent_case_id == case_id)) or 0
    has_versions = session.scalar(select(func.count(LeaseVersion.version_id)).where(LeaseVersion.parent_case_id == case_id)) or 0
    if has_children or has_versions:
        raise ValueError("This lease has amendments. Delete the amendments first.")

    ref = case.lease_ref or "#{}".format(case_id)
    user = session.get(User, user_id)
    email = user.email if user is not None else str(user_id)
    removed = {
        "schedule rows": session.scalar(select(func.count(AmortizationSchedule.id)).where(AmortizationSchedule.case_id == case_id)) or 0,
        "journal rows": session.scalar(select(func.count(JournalEntry.id)).where(JournalEntry.case_id == case_id)) or 0,
        "memo versions": session.scalar(select(func.count(TechnicalMemo.memo_id)).where(TechnicalMemo.case_id == case_id)) or 0,
        "documents": session.scalar(select(func.count(AgreementDocument.document_id)).where(AgreementDocument.case_id == case_id)) or 0,
    }
    summary = "Lease {} ({} / {}, {}) deleted by {}. Reason: {}. Status was {}. Removed: {}.".format(
        ref, case.lessor_name or "-", case.lessee_name or "-", case.currency or "INR", email, text, case.status,
        ", ".join("{} {}".format(count, name) for name, count in removed.items()),
    )
    status = case.status
    try:
        # 1) keep the history: detach the lease's audit rows (they keep the lease's ID) so nothing can cascade away
        session.execute(update(AuditLog).where(AuditLog.case_id == case_id).values(lease_ref=ref, case_id=None))
        # 2) delete the lease and everything that belongs to it. The extracted fields point at the uploaded document
        #    (a foreign key with no cascade), so they must go BEFORE the document or the database refuses the delete.
        session.execute(delete(ExtractedFields).where(ExtractedFields.case_id == case_id))
        session.delete(case)
        # 3) record the deletion itself
        session.add(
            AuditLog(
                case_id=None, lease_ref=ref, user_id=user_id, action="Lease deleted", entity_type="LeaseCase",
                field_name="status", old_value=status, new_value=None, details=summary,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return {"lease_ref": ref, "removed": removed}


# --------------------------------------------------------------------------- #
# Per-lease export: the raw saved rows (with their dates, legs and periods)
# --------------------------------------------------------------------------- #
def get_lease_export_data(session: Session, case_id: int, user_id: int):
    """Everything the single-lease export needs, or None if the lease has no calculation results yet.

    {"stored": get_stored_results(...), "case_data": get_lease_case_data(...), "journal_rows": [raw JournalEntry rows]}.
    The journal rows keep their entry date, leg / period, framework, line number and balanced flag (the grouped view
    on the results screen drops them). LookupError if it is not this user's lease.
    """
    stored = get_stored_results(session, case_id, user_id)
    if stored is None:
        return None
    rows = session.scalars(select(JournalEntry).where(JournalEntry.case_id == case_id).order_by(JournalEntry.id)).all()
    return {
        "stored": stored,
        "case_data": get_lease_case_data(session, case_id, user_id),
        "journal_rows": [_row_to_dict(row) for row in rows],
    }
