"""Compliance trackers: default data, due-date maths and bulk generation for all clients."""
from datetime import date

from ..models import (
    Client,
    ComplianceDeadline,
    ComplianceRule,
    GstReturn,
    GstReturnType,
    ItrFiling,
    TdsReturn,
    db,
)

RETURN_STATUSES = {
    "pending": "Pending",
    "documents_pending": "Documents Pending",
    "in_progress": "In Progress",
    "ready": "Ready to File",
    "filed": "Filed",
}
DEADLINE_STATUSES = {"upcoming": "Upcoming", "in_progress": "In Progress", "completed": "Completed"}
COMPLIANCE_TYPES = {
    "gst": "GST", "itr": "ITR", "tds": "TDS", "advance_tax": "Advance Tax",
    "roc": "ROC", "audit": "Audit", "custom": "Custom",
}
ITR_VERIFY = {"": "Not verified yet", "e_verified": "e-Verified", "itrv_sent": "ITR-V sent by post", "itrv_received": "ITR-V received at CPC"}
ITR_FORMS = ["ITR-1", "ITR-2", "ITR-3", "ITR-4", "ITR-5", "ITR-6", "ITR-7"]
TDS_FORMS = ["24Q", "26Q", "27Q", "27EQ"]
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]
TDS_DUE = {"Q1": (7, 31), "Q2": (10, 31), "Q3": (1, 31), "Q4": (5, 31)}  # month, day (Q3 falls in next year)

DEFAULT_GST_TYPES = [
    ("GSTR-1", "monthly", 11),
    ("GSTR-3B", "monthly", 20),
    ("CMP-08", "quarterly", 18),
    ("GSTR-9", "annual", 31),
]


def seed_defaults() -> None:
    if GstReturnType.query.count() == 0:
        for name, freq, day in DEFAULT_GST_TYPES:
            db.session.add(GstReturnType(name=name, frequency=freq, due_day=day))
        db.session.commit()


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _safe_date(year: int, month: int, day: int) -> date:
    import calendar

    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def gst_due_date(rt: GstReturnType, period: str) -> date | None:
    """period: 'YYYY-MM' (monthly), 'YYYY-Qn' (quarterly; calendar quarter), 'YYYY-YY' / 'YYYY' (annual)."""
    try:
        if rt.frequency == "monthly":
            y, m = (int(x) for x in period.split("-"))
            ny, nm = _add_months(y, m, 1)
            return _safe_date(ny, nm, rt.due_day or 20)
        if rt.frequency == "quarterly":
            y, q = period.split("-Q")
            end_month = int(q) * 3
            ny, nm = _add_months(int(y), end_month, 1)
            return _safe_date(ny, nm, rt.due_day or 18)
        fy_start = int(period[:4])
        return date(fy_start + 1, 12, 31)  # annual return for FY starting in fy_start
    except (ValueError, IndexError):
        return None


def valid_gst_period(rt: GstReturnType, period: str) -> bool:
    import re

    pattern = {"monthly": r"^\d{4}-(0[1-9]|1[0-2])$", "quarterly": r"^\d{4}-Q[1-4]$"}.get(rt.frequency, r"^\d{4}(-\d{2})?$")
    return bool(re.match(pattern, period or ""))


def itr_due_date(assessment_year: str) -> date | None:
    try:
        return date(int(assessment_year[:4]), 7, 31)
    except ValueError:
        return None


def tds_due_date(financial_year: str, quarter: str) -> date | None:
    try:
        start = int(financial_year[:4])
        month, day = TDS_DUE[quarter]
        return date(start + 1 if quarter in ("Q3", "Q4") else start, month, day)
    except (ValueError, KeyError):
        return None


def _targets(clients_query, flag):
    q = clients_query.filter(Client.status != "inactive")
    return q.filter(flag.is_(True)).all() if flag is not None else q.all()


def bulk_gst(clients_query, rt: GstReturnType, period: str, assigned_default: bool = True) -> tuple[int, int]:
    created = skipped = 0
    due = gst_due_date(rt, period)
    for c in _targets(clients_query, Client.is_gst_registered):
        exists = GstReturn.query.filter_by(client_id=c.id, return_type_id=rt.id, period=period).first()
        if exists:
            skipped += 1
            continue
        db.session.add(GstReturn(client_id=c.id, return_type_id=rt.id, period=period, due_date=due,
                                 assigned_to_id=c.assigned_to_id if assigned_default else None))
        created += 1
    db.session.commit()
    return created, skipped


def bulk_itr(clients_query, assessment_year: str, form_type: str, due: date | None = None) -> tuple[int, int]:
    created = skipped = 0
    due = due or itr_due_date(assessment_year)
    for c in _targets(clients_query, Client.is_itr_applicable):
        if ItrFiling.query.filter_by(client_id=c.id, assessment_year=assessment_year, form_type=form_type).first():
            skipped += 1
            continue
        db.session.add(ItrFiling(client_id=c.id, assessment_year=assessment_year, form_type=form_type,
                                 due_date=due, assigned_to_id=c.assigned_to_id))
        created += 1
    db.session.commit()
    return created, skipped


def bulk_tds(clients_query, financial_year: str, quarter: str, form_type: str) -> tuple[int, int]:
    created = skipped = 0
    due = tds_due_date(financial_year, quarter)
    for c in _targets(clients_query, Client.is_tds_applicable):
        if TdsReturn.query.filter_by(client_id=c.id, financial_year=financial_year, quarter=quarter, form_type=form_type).first():
            skipped += 1
            continue
        db.session.add(TdsReturn(client_id=c.id, financial_year=financial_year, quarter=quarter, form_type=form_type,
                                 due_date=due, assigned_to_id=c.assigned_to_id))
        created += 1
    db.session.commit()
    return created, skipped


def generate_from_rule(rule: ComplianceRule, year: int, month: int, clients_query) -> tuple[int, int]:
    """Create one deadline per client for the rule. Monthly rules use year+month; quarterly rules
    use the given month; yearly rules use the rule's own month in the given year."""
    flag = {"gst": Client.is_gst_registered, "itr": Client.is_itr_applicable, "tds": Client.is_tds_applicable}.get(rule.applies_to)
    target_month = rule.due_month if rule.frequency == "yearly" and rule.due_month else month
    due = _safe_date(year, target_month, rule.due_day or 1)
    title = f"{rule.title} ({due.strftime('%b %Y')})"
    created = skipped = 0
    for c in _targets(clients_query, flag):
        if ComplianceDeadline.query.filter_by(client_id=c.id, title=title).first():
            skipped += 1
            continue
        db.session.add(ComplianceDeadline(title=title, compliance_type=rule.compliance_type, client_id=c.id,
                                          assigned_to_id=c.assigned_to_id, due_date=due))
        created += 1
    db.session.commit()
    return created, skipped
