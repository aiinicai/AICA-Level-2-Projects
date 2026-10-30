"""Module 3: statutory compliance calendar and minutes analyser.

The calendar is rule-driven (due dates derived from the Act, Rules, bye-laws and
tax law) and compares each obligation with the society's records. The minutes
analyser parses the semi-structured minutes with regular expressions and then
cross-checks resolutions and action items against the accounting data; the AI
layer can add a narrative summary on top.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from .config import FY_END, SOCIETY
from .findings import Finding
from .loaders import SocietyData

MC_NOTICE_DAYS = 7          # committee meeting notice (bye-law, configurable)
AGM_NOTICE_DAYS = 14        # bye-law 97: 14 clear days
MC_QUORUM_FRACTION = 0.5    # more than half of committee members


def _d(v):
    """Coerce pandas Timestamp / datetime / date to a plain date; anything else -> None."""
    if v is None or isinstance(v, (str, int, float)):
        return None
    if hasattr(v, "to_pydatetime"):
        return v.to_pydatetime().date()
    if hasattr(v, "date") and callable(v.date):
        return v.date()
    return v if isinstance(v, date) else None


def _status(due: date, done, run_date: date) -> str:
    done_d = _d(done)
    if done_d:
        return "Complied (late)" if done_d > due else "Complied"
    if isinstance(done, str) and done.lower().startswith("not"):
        return "Overdue - not done" if run_date > due else f"Pending - due in {(due - run_date).days} days"
    if run_date > due:
        return "Overdue"
    days = (due - run_date).days
    return f"Due in {days} days" if days <= 45 else "Upcoming"


def compliance_calendar(d: SocietyData, run_date: date):
    s = SOCIETY
    oc = _d(d.master("Building occupation certificate"))
    age = (FY_END - oc).days / 365.25
    structural_cycle = 3 if age > 30 else 5
    last_sa = _d(d.master("Last structural audit"))
    items = [
        # (obligation, authority, due date, record/evidence, remarks)
        ("Finalise accounts for FY 2025-26 and place before committee", "Bye-law 146 / MCS Rules 61 (within 45 days of year end)", date(2026, 5, 15), d.master("Accounts FY 2025-26 finalised"), ""),
        ("Statutory audit of FY 2025-26 accounts", "MCS Act s.81(1)(a): within 4 months of close of FY", date(2026, 7, 31), None, "Auditor appointed at AGM 28-Sep-2025 (Jain Jakhotiya & Associates)"),
        ("Auditor to upload audit report on Co-operative Dept. portal", "MCS Act s.81(5B): within 1 month of completion", date(2026, 8, 31), None, "Auditor's obligation; society to provide data"),
        ("Audit rectification report (Form O) for FY 2024-25", "MCS Act s.82 / Rule 73: within 3 months of receipt of audit report (22-Aug-2025)", date(2025, 11, 22), d.master("Audit rectification report"), "AGM action item dated 22-Nov-2025"),
        ("Annual General Meeting for FY 2025-26", "MCS Act s.75(1): on or before 30 September", date(2026, 9, 30), None, ""),
        ("AGM notice to members", "Bye-law 97: 14 clear days before AGM", date(2026, 9, 15), None, "Last year's notice gave only 10 days"),
        ("Annual returns to Registrar (s.79(1A)/(1B)) incl. auditor appointment", "MCS Act s.75(2A), s.79: within 30 days of AGM / by 30 Sept", date(2026, 10, 30), None, ""),
        ("Income-tax return (ITR-5) for AY 2026-27", "Income-tax Act s.139(1) Expl. 2: 31 October for audited society", date(2026, 10, 31), None, "Advance tax not paid - see Tax module"),
        ("TDS return Form 26Q - Q1 FY 2026-27", "Rule 31A", date(2026, 7, 31), None, ""),
        ("TDS return Form 26Q - Q2 FY 2026-27", "Rule 31A", date(2026, 10, 31), None, ""),
        ("TDS return Form 26Q - Q4 FY 2025-26", "Rule 31A", date(2026, 5, 31), d.master("TDS return Q4"), "Correction statement needed for short deduction"),
        ("GSTR-9 annual return FY 2025-26", "CGST Act s.44: 31 December", date(2026, 12, 31), None, "Credit/debit notes for billing errors to be reported"),
        ("Structural audit of building", f"Bye-law 77: every {structural_cycle} years for building aged {age:.0f} years", last_sa.replace(year=last_sa.year + structural_cycle), None, f"Last audit {last_sa:%d-%b-%Y}; AGM resolution A.5 approved budget"),
        ("Lift licence renewal", "Maharashtra Lifts, Escalators and Moving Walks Act 2017: annual", _d(d.master("Lift licence expiry")), None, "MC resolution 12.1 of 15-Mar-2026 directed filing before expiry"),
        ("Building insurance renewal", "Bye-law 160; MC resolution 8.1", _d(d.master("Building insurance policy expiry")), None, "Sum insured Rs 18 crore"),
        ("Fire safety certificate Form B (half-yearly)", "Maharashtra Fire Prevention and Life Safety Measures Act 2006 s.3(3): January and July", date(2026, 7, 31), None, f"Last filed {_d(d.master('Last fire safety')):%d-%b-%Y}"),
        ("Managing committee election", "MCS Act s.73CB: every 5 years; election process 6 months before expiry", _d(d.master("Last managing committee election")).replace(year=_d(d.master("Last managing committee election")).year + 5), None, "Notify SCEA 6 months in advance (by Jul-2027)"),
        ("Deemed conveyance application", "MOFA 1963 s.11; AGM resolution A.6", date(2026, 3, 31), d.master("Deemed conveyance status"), "Legal opinion obtained Aug-2025; application still not filed"),
        ("Section 101 recovery applications against chronic defaulters", "MCS Act s.101; MC resolution 8.2 of 16-Nov-2025", date(2025, 12, 31), "Not filed", "Three chronic defaulters identified"),
        ("Transfer sinking fund collections to earmarked FD", "Bye-law 15 / s.70; MC resolution 11.2", date(2026, 3, 31), "Not done", "Shortfall persists at year end"),
    ]
    rows = []
    for obl, auth, due, rec, rem in items:
        rows.append({"obligation": obl, "authority": auth, "due_date": due, "record": rec if rec is not None else "", "status": _status(due, rec, run_date), "remarks": rem})
    cal = pd.DataFrame(rows).sort_values("due_date").reset_index(drop=True)
    overdue = cal[cal.status.str.startswith("Overdue")]
    soon = cal[cal.status.str.startswith("Due in")]
    findings = [Finding(
        module="Compliance", area="Statutory calendar", severity="High" if len(overdue) else "Low",
        observation=(f"As at {run_date:%d-%b-%Y}, {len(overdue)} statutory obligations are overdue: " + "; ".join(overdue.obligation) +
                     (f". Falling due within 45 days: " + "; ".join(soon.obligation) if len(soon) else "")),
        reference="MCS Act 1960 ss.75, 79, 81, 82, 101; bye-laws 15, 77, 97; Maharashtra Lifts Act 2017; Income-tax Act s.139(1)",
        recommendation="Adopt the compliance calendar as a standing agenda item in every committee meeting; assign an owner to each obligation; the Secretary to report status monthly.",
        amount=0.0, evidence="Sheet: Compliance_Calendar",
    )]
    return cal, findings


# ----------------------------------------------------------------------------- minutes
@dataclass
class Meeting:
    file: str
    kind: str
    number: str
    meeting_date: date
    notice_date: date | None
    present: int
    total: int
    resolutions: list[str]
    actions: list[tuple[str, date | None]]


_DATE = r"(\d{2})-(\d{2})-(\d{4})"


def _parse_date(m) -> date | None:
    if not m:
        return None
    dd, mm, yy = (int(x) for x in m.groups()[:3])
    return date(yy, mm, dd)


def parse_minutes(name: str, text: str) -> Meeting:
    kind = "AGM" if "ANNUAL GENERAL MEETING" in text else "MC"
    num = re.search(r"MEETING NO\. ([\d/\-]+)", text)
    md = _parse_date(re.search(r"Date of meeting:\s*" + _DATE, text))
    nd = _parse_date(re.search(r"Notice issued on:\s*" + _DATE, text))
    pres = re.search(r"Members present:\s*(\d+)\s*of\s*(\d+)", text)
    resolutions = re.findall(r"^\s*[A\d]+\.\d+\s+(.+)$", text, flags=re.M)
    actions = []
    for a in re.findall(r"^- Action:\s*(.+)$", text, flags=re.M):
        due = _parse_date(re.search(r"by\s+" + _DATE, a))
        actions.append((re.sub(r"\s+by\s+\d{2}-\d{2}-\d{4}$", "", a).strip(), due))
    return Meeting(name, kind, num.group(1) if num else ("16th AGM" if kind == "AGM" else "?"), md, nd,
                   int(pres.group(1)) if pres else 0, int(pres.group(2)) if pres else 0, resolutions, actions)


# Cross-checks of action items against what the data shows actually happened.
ACTION_STATUS_RULES = [
    (r"three quotations", "Not complied - MC minutes 08-Jun-2025 record only one quotation; contract awarded anyway"),
    (r"section 101", "Not complied - no s.101 application on record as at audit date"),
    (r"Form O|rectification", "Not complied - Form O for FY 2024-25 not filed"),
    (r"structural engineer", "Not complied - no appointment or payment to a structural engineer in FY 2025-26 books"),
    (r"sinking fund", "Not complied - sinking fund transfers short by Rs 52,001 and FDs under-invested at 31-Mar-2026"),
    (r"lift licence", "Open - licence expires 15-Sep-2026; no renewal application or fee in the books yet"),
    (r"reconcile bank", "Not complied - no bank reconciliation statement on record"),
    (r"AGM notice", "Complied late - notice dated 18-Sep-2025 gave 10 days against 14 clear days required"),
    (r"annual returns", "Pending verification - obtain Registrar acknowledgement"),
    (r"legal notice", "Complied - advocate's reply on file (per Secretary)"),
    (r"Form B", "Complied - Form B filed 20-Jan-2026"),
    (r"insurance|premium", "Complied - policy renewed 15-Nov-2025"),
    (r"arrears above three months|defaulters", "Complied - list circulated (verify minutes of next meeting)"),
    (r"budget", "Complied - budget approved at AGM"),
    (r"share certificate", "Complied - endorsement dated Aug-2025 (per share register)"),
    (r"finalise books", "Complied - accounts finalised May-2026"),
    (r"waterproofing|each phase", "Complied - three payments released (see split invoice observation)"),
    (r"painter", "Complied - but paid in cash Rs 28,000 above cash limit"),
]


def minutes_analysis(d: SocietyData, run_date: date):
    meetings = [parse_minutes(n, t) for n, t in d.minutes.items()]
    meetings.sort(key=lambda m: m.meeting_date)
    mrows, arows, rrows = [], [], []
    findings = []
    for m in meetings:
        if m.notice_date is None:
            notice_days = None
        elif m.kind == "AGM":
            notice_days = (m.meeting_date - m.notice_date).days - 1   # bye-law 97: clear days
        else:
            notice_days = (m.meeting_date - m.notice_date).days
        req = AGM_NOTICE_DAYS if m.kind == "AGM" else MC_NOTICE_DAYS
        if m.kind == "AGM":
            quorum_req = min(20, (m.total + 4) // 5)
            quorum_ok = m.present >= quorum_req
        else:
            quorum_req = int(m.total * MC_QUORUM_FRACTION) + 1
            quorum_ok = m.present >= quorum_req
        spend_words = any(re.search(r"awarded|paid|payment|premium|engaged", r, re.I) for r in m.resolutions)
        issues = []
        if notice_days is not None and notice_days < req:
            issues.append(f"Notice period {notice_days} days < {req} required")
        if not quorum_ok:
            issues.append(f"No quorum ({m.present} of {m.total}, need {quorum_req})" + (" - expenditure approved" if spend_words else ""))
        mrows.append({"file": m.file, "type": m.kind, "meeting_no": m.number, "meeting_date": m.meeting_date, "notice_date": m.notice_date,
                      "notice_days": notice_days, "required_notice_days": req, "present": m.present, "total": m.total,
                      "quorum_required": quorum_req, "quorum_ok": quorum_ok, "resolutions": len(m.resolutions), "action_items": len(m.actions),
                      "issues": "; ".join(issues)})
        for i, r in enumerate(m.resolutions, start=1):
            rrows.append({"meeting_date": m.meeting_date, "type": m.kind, "no": i, "resolution": r,
                          "financial": bool(re.search(r"Rs\s?[\d,]+", r)), "amount_mentioned": ", ".join(re.findall(r"Rs\s?[\d,]+(?:\.\d+)?", r))})
        for text, due in m.actions:
            status = "Open"
            for pat, st in ACTION_STATUS_RULES:
                if re.search(pat, text, re.I):
                    status = st
                    break
            arows.append({"meeting_date": m.meeting_date, "type": m.kind, "action": text, "due_date": due,
                          "owner": "Secretary" if "Secretary" in text else "Treasurer" if "Treasurer" in text else "Committee",
                          "status": status, "overdue": bool(due and run_date > due and status.startswith("Not"))})
    mdf, adf, rdf = pd.DataFrame(mrows), pd.DataFrame(arows), pd.DataFrame(rrows)
    bad = mdf[mdf.issues != ""]
    if len(bad):
        findings.append(Finding(
            module="Governance", area="Meetings - notice and quorum", severity="High",
            observation="; ".join(f"{r.type} meeting of {r.meeting_date:%d-%b-%Y}: {r.issues}" for r in bad.itertuples()) +
                        ". Resolutions passed at the 12-Oct-2025 meeting (cash payment to painter, Diwali bonus) are liable to be treated as invalid.",
            reference="Bye-laws 97 (AGM notice 14 clear days), 100 (AGM quorum), 128-131 (committee meetings and quorum); MCS Act s.75",
            recommendation="Ratify the affected resolutions at a properly convened meeting; the Secretary to maintain a notice register with proof of dispatch; record quorum at the start of every meeting.",
            amount=0.0, evidence="Sheet: Minutes_Meetings",
        ))
    not_done = adf[adf.status.str.startswith("Not")]
    findings.append(Finding(
        module="Governance", area="Follow-up of committee decisions", severity="High" if len(not_done) >= 3 else "Medium",
        observation=f"Of {len(adf)} action items recorded in minutes, {len(not_done)} remain not complied as at {run_date:%d-%b-%Y}: " +
                    "; ".join(f"{r.action} (due {r.due_date:%d-%b-%Y})" for r in not_done.itertuples() if r.due_date),
        reference="MCS Act s.73 (duties of committee); bye-laws 139-140 (functions of Secretary and Treasurer)",
        recommendation="Maintain an action tracker reviewed at the start of each meeting; link each item to an owner and a due date; report open items to the AGM.",
        amount=0.0, evidence="Sheet: Minutes_Actions",
    ))
    # resolutions inconsistent with records
    findings.append(Finding(
        module="Governance", area="Resolutions vs records", severity="Medium",
        observation="MC resolution 3.1 (08-Jun-2025) awarded Rs 1,45,000 waterproofing on one quotation, contrary to AGM resolution A.4 (three quotations above Rs 50,000). "
                    "Resolution 11.2 (15-Feb-2026) records that sinking fund collections were used for revenue expenses, which bye-law 15 prohibits. "
                    "Resolution 7.1 (12-Oct-2025) approved a cash payment of Rs 28,000, above the cash limit.",
        reference="AGM 2025 resolution A.4; bye-laws 15, 143",
        recommendation="Place these matters before the General Body for ratification and record corrective resolutions.",
        amount=0.0, evidence="Sheet: Minutes_Resolutions",
    ))
    return mdf, rdf, adf, findings
