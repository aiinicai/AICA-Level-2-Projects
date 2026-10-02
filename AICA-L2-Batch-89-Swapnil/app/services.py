"""Service layer: maps DB rows onto the pure engine, upserts obligations,
enforces the status workflow (maker–checker) and records filings."""
from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any

from flask import current_app
from sqlalchemy import func, select

import engine
from engine.dates import fy_key_for_end, standard_fy_end
from engine.generator import entity_fys, horizon_end
from engine.predicates import Ctx, classify_all, classify_small_llp
from engine.types import EntityIn, EventIn, FactsIn, PersonIn

from . import audit
from .models import (CLOSED, AnnualFacts, ClassificationDecision, Entity, EntityPerson, Event, Filing,
                     Obligation, PeriodFlag, Person, RuleVerification, Setting, User, db, utcnow)
from .permissions import Denied, has

DEFAULT_SETTINGS: dict[str, Any] = {
    "firm_name": "Swapnil & Associates",
    "firm_tagline": "Chartered Accountants",
    "firm_address": "Uttam Nagar, New Delhi – 110059",
    "firm_phone": "+91 79821 32093",
    "firm_email": "caswapnil7@gmail.com",
    "firm_signatory": "CA Swapnil, Principal & Founder",
    "show_logo": True,
    "srn_regex": r"^[A-Z][0-9]{8}$",
    "totp_required_for_partners": False,
    "adt1_for_first_auditor": True,
    "retention_years": 8,
    "brand_primary": "#0B1D3A",
    "brand_accent": "#C8973F",
}


class ValidationError(Exception):
    def __init__(self, messages: list[str] | str):
        self.messages = [messages] if isinstance(messages, str) else messages
        super().__init__("; ".join(self.messages))


# ------------------------------------------------------------------ settings
def get_setting(key: str) -> Any:
    row = db.session.get(Setting, key)
    return row.value if row is not None else DEFAULT_SETTINGS.get(key)


def set_setting(key: str, value: Any, actor: audit.Actor) -> None:
    row = db.session.get(Setting, key)
    before = row.value if row else DEFAULT_SETTINGS.get(key)
    if row is None:
        db.session.add(Setting(key=key, value=value))
    else:
        row.value = value
    audit.record(db.session, actor, "SETTING_CHANGED", "setting", key, before={key: before}, after={key: value})


# ------------------------------------------------------------------ rule pack
def rulepack() -> engine.RulePack:
    """YAML pack + partner sign-offs stored in the DB (valid only for the same content hash)."""
    base: engine.RulePack = current_app.extensions["rulepack"]
    rows = db.session.execute(select(RuleVerification).order_by(RuleVerification.id)).scalars().all()
    signed = {}
    for r in rows:
        rule = base.by_code.get(r.rule_code)
        if rule is not None and rule.content_hash == r.rule_hash:
            signed[r.rule_code] = (r.verified_by.full_name, r.verified_at.date())
    return base.with_verifications(signed) if signed else base


# ------------------------------------------------------------ engine inputs
ENTITY_FIELDS = ["name", "entity_type", "incorporation_date", "has_share_capital", "nominal_capital",
                 "paid_up_capital", "llp_contribution", "is_holding", "is_subsidiary", "subsidiary_of_public",
                 "nbfc", "hfc", "banking", "excluded_sector", "government", "special_act", "listed_subsidiary",
                 "startup", "status", "single_director", "ro_furnished_at_incorporation", "engagement_start",
                 "llp_elect_longer_first_fy", "ccfs_excluded"]
FACT_FIELDS = [f for f in FactsIn.__dataclass_fields__ if f != "fy_key"]


# Annual-facts screen: which obligations depend on each field (brief §7). "(next FY)" = the figure
# is read as the *preceding-year* number when the next FY is classified.
FACT_INFO: dict[str, tuple[str, str]] = {
    "paid_up_capital": ("Paid-up capital at FY end ₹", "Small-company test (MGT-7A vs MGT-7, board-meeting regime, Rule 9B/PAS-6), AOC-4 XBRL, MGT-8; secretarial/internal audit (next FY)"),
    "turnover": ("Turnover for the FY ₹", "AOC-4 XBRL, MGT-8, LLP audit; small company / small LLP, CSR, internal & secretarial audit (next FY)"),
    "net_worth": ("Net worth ₹", "CSR applicability → CSR-2 (next FY)"),
    "net_profit": ("Net profit ₹", "CSR applicability → CSR-2 (next FY)"),
    "bank_borrowings_at_fy_end": ("Bank/PFI borrowings at FY end ₹", "Secretarial audit MR-3 (next FY) — Rule 9 uses the FY-end figure"),
    "bank_borrowings_max": ("Bank/PFI borrowings — maximum in year ₹", "Internal audit (next FY) — Rule 13 uses 'at any point'"),
    "deposits_max": ("Deposits — maximum in year ₹", "Internal audit for unlisted public companies (next FY)"),
    "deposits_outstanding_31mar": ("Deposits / exempted receipts outstanding at 31 March?", "DPT-3 (due 30 June)"),
    "has_subs_assoc_jv": ("Has subsidiaries / associates / JVs?", "AOC-4 CFS"),
    "ind_as": ("Follows Ind AS?", "AOC-4 XBRL / AOC-4 NBFC (Ind AS)"),
    "cost_audit_applicable": ("Cost audit applicable?", "CRA-2, CRA-4"),
    "csr_override": ("CSR applicable (override)", "CSR-2 — overrides the computed test"),
    "agm_date": ("AGM held on", "Due dates of AOC-4, MGT-7/7A, MGT-8, ADT-1, CSR-2, MR-3; next year's AGM deadline"),
    "board_approval_date": ("Board meeting approving accounts on", "MGT-14 for financial statements (public companies)"),
    "auditor_appointed_at_agm": ("Auditor appointed / re-appointed at this AGM?", "ADT-1"),
    "isin_obtained_date": ("ISIN obtained on", "PAS-6 half-yearly (Rule 9B companies)"),
    "llp_contribution": ("LLP contribution at FY end ₹", "Small LLP, LLP audit, LLP filing fees"),
}
COMPANY_ONLY_FACTS = {"paid_up_capital", "net_worth", "net_profit", "bank_borrowings_at_fy_end", "bank_borrowings_max",
                      "deposits_max", "deposits_outstanding_31mar", "has_subs_assoc_jv", "ind_as", "cost_audit_applicable",
                      "csr_override", "agm_date", "board_approval_date", "auditor_appointed_at_agm", "isin_obtained_date"}


def fact_fields_for(entity_type: str) -> list[str]:
    if entity_type == "LLP":
        return ["turnover", "llp_contribution"]
    return [f for f in FACT_INFO if f != "llp_contribution"]


def entity_in(e: Entity) -> EntityIn:
    return EntityIn(id=e.id, **{f: getattr(e, f) for f in ENTITY_FIELDS})


def facts_in(e: Entity) -> dict[str, FactsIn]:
    rows = db.session.execute(select(AnnualFacts).where(AnnualFacts.entity_id == e.id)).scalars()
    return {r.fy_key: FactsIn(r.fy_key, **{f: getattr(r, f) for f in FACT_FIELDS}) for r in rows}


def flags_in(e: Entity) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in db.session.execute(select(PeriodFlag).where(PeriodFlag.entity_id == e.id)).scalars():
        out.setdefault(r.period_key, {})[r.name] = r.value
    return out


ANNUAL_RETURN_CODES = ("MGT7", "MGT7_OPC")     # the small-company question decides the annual-return form


def filing_dates_in(e: Entity) -> dict[str, date]:
    """FY key -> date that FY's annual return (MGT-7/7A) was filed."""
    rows = db.session.execute(select(Obligation.period_key, Obligation.rule_code, Filing.filing_date).join(
        Filing, Filing.obligation_id == Obligation.id).where(Obligation.entity_id == e.id,
                                                             Obligation.rule_code.in_(ANNUAL_RETURN_CODES))).all()
    out: dict[str, date] = {}
    for period, code, d in sorted(rows, key=lambda r: r[2]):
        out.setdefault(period, d)
    return out


def decisions_in(e: Entity) -> dict[str, str]:
    rows = db.session.execute(select(ClassificationDecision).where(ClassificationDecision.entity_id == e.id))
    return {r.key: r.value for r in rows.scalars()}


def events_in(e: Entity) -> list[EventIn]:
    rows = db.session.execute(select(Event).where(Event.entity_id == e.id)).scalars()
    return [EventIn(r.id, r.type, r.event_date, dict(r.attrs or {})) for r in rows]


def person_in(p: Person) -> PersonIn:
    changes = db.session.execute(select(Event.event_date).where(
        Event.person_id == p.id, Event.type == "DIRECTOR_DETAIL_CHANGE")).scalars().all()
    return PersonIn(p.id, p.name, p.din, p.din_allotment_date, p.din_status, p.last_annual_kyc_fy,
                    p.kyc_override_first_due, sorted(changes))


def active_persons(e: Entity) -> list[Person]:
    rows = db.session.execute(select(EntityPerson).where(EntityPerson.entity_id == e.id,
                                                         EntityPerson.ceased_on.is_(None))).scalars()
    return [r.person for r in rows]


def settings_in() -> dict[str, Any]:
    return {"adt1_for_first_auditor": get_setting("adt1_for_first_auditor")}


def classifications(e: Entity, fy_key: str | None, as_of: date):
    fys = entity_fys(entity_in(e), horizon_end(as_of))
    fy = next((f for f in fys if f.key == fy_key), None) or next(
        (f for f in reversed(fys) if f.end <= as_of), fys[0])
    ctx = Ctx(entity_in(e), rulepack(), as_of, fys, facts_in(e), fy=fy, decisions=decisions_in(e),
              filing_dates=filing_dates_in(e))
    return fy, fys, classify_all(ctx)


# ------------------------------------------------------------------- upsert
SPEC_FIELDS = ["rule_code", "period_key", "form", "title", "law", "fee_regime", "anchor_type", "anchor_date",
               "due_date", "provisional", "facts_stale", "needs_decision", "pre_engagement", "agm_not_held",
               "interpretation", "notes", "rule_version", "rule_hash"]


def _upsert(specs, *, entity_id=None, persons_by_din=None, events_ids=None, actor=audit.SYSTEM,
            scope_filter=None) -> dict[str, int]:
    s = db.session
    stats = {"inserted": 0, "updated": 0, "superseded": 0, "restored": 0}
    existing = {o.key: o for o in s.execute(select(Obligation).where(scope_filter)).scalars()}
    seen, created, preparer = set(), [], None
    if entity_id is not None:
        preparer = s.get(Entity, entity_id).preparer_id
    for sp in specs:
        seen.add(sp.key)
        values = {f: getattr(sp, f) for f in SPEC_FIELDS}
        o = existing.get(sp.key)
        if o is None:
            o = s.execute(select(Obligation).where(Obligation.key == sp.key)).scalar()
        if o is None:
            o = Obligation(key=sp.key, entity_id=None if sp.person_din else sp.entity_id,
                           person_id=persons_by_din[sp.person_din].id if sp.person_din else None,
                           event_id=sp.event_id, status="NOT_STARTED", assignee_id=preparer, **values)
            s.add(o)
            created.append(sp.key)
            stats["inserted"] += 1
            continue
        changed = {f: (getattr(o, f), v) for f, v in values.items() if getattr(o, f) != v}
        if o.superseded_at is not None:
            o.superseded_at, o.superseded_reason = None, None
            stats["restored"] += 1
        if changed:
            if "due_date" in changed:
                audit.record(s, actor, "DUE_DATE_CHANGED", "obligation", o.key, o.entity_id,
                             before={"due_date": changed["due_date"][0], "anchor": o.anchor_type,
                                     "anchor_date": o.anchor_date, "rule_version": o.rule_version},
                             after={"due_date": changed["due_date"][1], "anchor": values["anchor_type"],
                                    "anchor_date": values["anchor_date"], "rule_version": values["rule_version"]})
            for f, (_, v) in changed.items():
                setattr(o, f, v)
            stats["updated"] += 1
    for key, o in existing.items():
        if key not in seen and o.superseded_at is None:
            o.superseded_at = utcnow()
            o.superseded_reason = "No longer generated by the rule pack for the current facts/events"
            audit.record(s, actor, "OBLIGATION_SUPERSEDED", "obligation", key, o.entity_id,
                         before={"status": o.status, "due_date": o.due_date}, after={"reason": o.superseded_reason})
            stats["superseded"] += 1
    if created:
        obj = entity_id if entity_id is not None else next(iter(persons_by_din.values())).id
        audit.record(s, actor, "OBLIGATIONS_GENERATED", "entity" if entity_id is not None else "person", obj,
                     entity_id, after={"count": len(created), "keys": created[:500]})
    return stats


def sync_entity(e: Entity, as_of: date, actor=audit.SYSTEM) -> dict[str, int]:
    rp = rulepack()
    persons = active_persons(e)
    specs = engine.generate(entity_in(e), facts_in(e), events_in(e), [person_in(p) for p in persons], rp, as_of,
                            period_flags=flags_in(e), decisions=decisions_in(e), settings=settings_in(),
                            filing_dates=filing_dates_in(e))
    ent_specs = [sp for sp in specs if not sp.person_din]
    stats = _upsert(ent_specs, entity_id=e.id, actor=actor, scope_filter=Obligation.entity_id == e.id)
    for p in persons:
        p_specs = [sp for sp in specs if sp.person_din == p.din]
        st = _upsert(p_specs, persons_by_din={p.din: p}, actor=actor, scope_filter=Obligation.person_id == p.id)
        for k in stats:
            stats[k] += st[k]
    return stats


def sync_person(p: Person, as_of: date, actor=audit.SYSTEM) -> dict[str, int]:
    specs = engine.generate_person(person_in(p), rulepack(), as_of)
    return _upsert(specs, persons_by_din={p.din: p}, actor=actor, scope_filter=Obligation.person_id == p.id)


def recompute_all(as_of: date, actor=audit.SYSTEM) -> dict[str, int]:
    total = {"entities": 0, "inserted": 0, "updated": 0, "superseded": 0, "restored": 0}
    for e in db.session.execute(select(Entity).where(Entity.archived.is_(False),
                                                     Entity.status.in_(["ACTIVE", "DORMANT"]))).scalars():
        st = sync_entity(e, as_of, actor)
        total["entities"] += 1
        for k, v in st.items():
            total[k] += v
    db.session.commit()
    return total


# --------------------------------------------------------------- validation
CIN_RE = re.compile(r"^[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$")
LLPIN_RE = re.compile(r"^[A-Z]{3}-\d{4}$")
PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
DIN_RE = re.compile(r"^\d{8}$")
CIN_SUFFIX = {"PTC": {"PRIVATE"}, "OPC": {"OPC"}, "PLC": {"PUBLIC_UNLISTED", "PUBLIC_LISTED"},
              "NPL": {"SECTION8"}, "GAP": {"SECTION8"}, "GOI": {"PRIVATE", "PUBLIC_UNLISTED"},
              "SGC": {"PRIVATE", "PUBLIC_UNLISTED"}, "FTC": {"PRIVATE"}, "ULL": {"PUBLIC_UNLISTED"}}


def validate_entity(d: dict[str, Any], today: date) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings) in plain English (brief §5.1)."""
    errors, warnings = [], []
    if not (d.get("name") or "").strip():
        errors.append("Enter the entity's name.")
    etype = d.get("entity_type")
    inc = d.get("incorporation_date")
    if inc is None:
        errors.append("Enter the date of incorporation.")
    elif inc > today:
        errors.append("The date of incorporation cannot be in the future.")
    cin = (d.get("cin") or "").strip().upper()
    if etype == "LLP":
        if cin and not LLPIN_RE.match(cin):
            errors.append("The LLPIN should look like AAB-1234 (three letters, a hyphen, four digits).")
    elif cin:
        if len(cin) != 21:
            errors.append(f"A CIN has exactly 21 characters; this one has {len(cin)}.")
        elif not CIN_RE.match(cin):
            errors.append("The CIN format is not valid (expected e.g. U62099DL2026PTC000101).")
        else:
            suffix = cin[12:15]
            if suffix in CIN_SUFFIX and etype not in CIN_SUFFIX[suffix]:
                warnings.append(f"The CIN says '{suffix}' but the entity type is {etype}. Please check.")
    pan = (d.get("pan") or "").strip().upper()
    if pan and not PAN_RE.match(pan):
        errors.append("The PAN should be 5 letters, 4 digits and a letter (e.g. ABCDE1234F).")
    nominal, paid = d.get("nominal_capital") or 0, d.get("paid_up_capital") or 0
    if nominal < 0 or paid < 0:
        errors.append("Capital amounts cannot be negative.")
    if etype != "LLP" and d.get("has_share_capital", True) and paid > nominal:
        errors.append("Paid-up capital cannot be more than the authorised (nominal) capital.")
    if d.get("llp_elect_longer_first_fy") and etype == "LLP" and inc:
        from engine.dates import llp_election_available
        if not llp_election_available(inc):
            errors.append("The longer first financial year is only available to an LLP registered "
                          "between 1 October and 31 March.")
    return errors, warnings


def validate_din(din: str) -> str | None:
    return None if DIN_RE.match(din or "") else "A DIN/DPIN has exactly 8 digits."


# ------------------------------------------------------------ status flow
TRANSITIONS: dict[str, dict[str, str]] = {
    # from -> {to: permission}
    "NOT_STARTED": {"IN_PROGRESS": "work_status", "READY_FOR_REVIEW": "work_status"},
    "IN_PROGRESS": {"READY_FOR_REVIEW": "work_status", "NOT_STARTED": "work_status"},
    "READY_FOR_REVIEW": {"APPROVED_FOR_FILING": "approve", "IN_PROGRESS": "approve"},
    "APPROVED_FOR_FILING": {"FILED": "mark_filed", "IN_PROGRESS": "approve"},
    "FILED": {"ROC_APPROVED": "mark_filed", "RESUBMISSION_REQUIRED": "mark_filed"},
    "RESUBMISSION_REQUIRED": {"FILED": "mark_filed", "IN_PROGRESS": "work_status"},
}
LABELS = {"NOT_STARTED": "Not started", "IN_PROGRESS": "In progress", "READY_FOR_REVIEW": "Ready for review",
          "APPROVED_FOR_FILING": "Approved for filing", "FILED": "Filed", "ROC_APPROVED": "ROC approved",
          "RESUBMISSION_REQUIRED": "Resubmission required", "NOT_APPLICABLE": "Not applicable",
          "WAIVED": "Waived"}


def obligation_snapshot(o: Obligation) -> dict[str, Any]:
    return {"status": o.status, "assignee_id": o.assignee_id, "reviewer_id": o.reviewer_id,
            "due_date": o.due_date, "status_reason": o.status_reason}


def change_status(o: Obligation, new: str, user: User, actor: audit.Actor, reason: str | None = None) -> None:
    """Raise Denied (403) or ValidationError (422); otherwise apply and audit."""
    if new in ("NOT_APPLICABLE", "WAIVED"):
        if not has(user, "waive"):
            raise Denied("waive")
        if o.status in CLOSED:
            raise ValidationError(f"This obligation is already {LABELS[o.status].lower()}.")
        if len((reason or "").strip()) < 20:
            raise ValidationError("Give a reason of at least 20 characters for marking this "
                                  f"{LABELS[new].lower()}.")
    else:
        if new == "FILED" and not has(user, "mark_filed"):
            raise Denied("mark_filed")
        allowed = TRANSITIONS.get(o.status, {})
        if new not in allowed:
            raise ValidationError(f"An obligation that is {LABELS.get(o.status, o.status).lower()} cannot move "
                                  f"to {LABELS.get(new, new).lower()}.")
        perm = allowed[new]
        if not has(user, perm):
            raise Denied(perm)
        if new == "FILED":
            raise ValidationError("Use the 'Mark filed' form: it needs the SRN, filing date and fees paid.")
        if new == "APPROVED_FOR_FILING" and o.ready_by_id == user.id:
            raise Denied("approve", "You marked this obligation Ready for review yourself. A different "
                                    "manager, partner or owner must approve it (maker–checker).")
    before = obligation_snapshot(o)
    if new == "READY_FOR_REVIEW":
        o.ready_by_id = user.id
    if new == "APPROVED_FOR_FILING":
        o.reviewer_id = user.id
    o.status = new
    o.status_reason = reason.strip() if reason else o.status_reason
    audit.record(db.session, actor, "STATUS_CHANGED", "obligation", o.key, o.entity_id, before=before,
                 after=obligation_snapshot(o))


# ------------------------------------------------------------------- fees
def fee_for(o: Obligation, filing_date: date) -> engine.FeeBreakdown:
    rp = rulepack()
    e = db.session.get(Entity, o.entity_id) if o.entity_id is not None else None
    if e is None and o.person and o.person.links:
        e = o.person.links[0].entity           # DIN obligations: fee is per DIN, entity only for display
    ein = entity_in(e) if e is not None else EntityIn(0, "—", "PRIVATE", date(2000, 1, 1))
    year_ago = filing_date - timedelta(days=365)
    prior = 0
    if o.entity_id is not None:
        prior = db.session.execute(select(func.count(Filing.id)).join(Obligation).where(
            Obligation.entity_id == o.entity_id, Obligation.rule_code == o.rule_code, Obligation.id != o.id,
            Filing.delay_days > 0, Filing.filing_date >= year_ago, Filing.filing_date <= filing_date)).scalar()
    is_small, charge_amount = None, None
    if ein.is_llp:
        fys = entity_fys(ein, horizon_end(filing_date))
        fy = next((f for f in fys if f.key == o.period_key), None) or next(
            (f for f in reversed(fys) if f.end <= filing_date), fys[0])
        is_small = bool(classify_small_llp(Ctx(ein, rp, filing_date, fys, facts_in(e), fy=fy)).result)
    elif o.rule_code == "CHG1" and o.event_id:
        ev = db.session.get(Event, o.event_id)
        charge_amount = (ev.attrs or {}).get("amount")
        is_small = ein.entity_type == "OPC"
    return engine.compute_fee(o.rule_code, ein, o.due_date, filing_date, prior, rp, period_key=o.period_key,
                              charge_amount=charge_amount, is_small=is_small)


def fee_json(fb: engine.FeeBreakdown) -> dict[str, Any]:
    d = asdict(fb)
    d["explanation"] = fb.explanation
    return d


def record_filing(o: Obligation, user: User, actor: audit.Actor, *, srn: str, filing_date: date,
                  normal_paid: float, additional_paid: float, today: date,
                  attachment: tuple[str, str] | None = None) -> Filing:
    if not has(user, "mark_filed"):
        raise Denied("mark_filed")
    if o.status not in ("APPROVED_FOR_FILING", "RESUBMISSION_REQUIRED"):
        raise ValidationError("Only an obligation that is Approved for filing (or needs resubmission) "
                              "can be marked filed.")
    problems = []
    pattern = get_setting("srn_regex")
    if not srn or (pattern and not re.match(pattern, srn.strip().upper())):
        problems.append(f"The SRN '{srn}' does not match the firm's SRN format ({pattern}).")
    if filing_date > today:
        problems.append("The filing date cannot be in the future.")
    if normal_paid < 0 or additional_paid < 0:
        problems.append("Fees paid cannot be negative.")
    if problems:
        raise ValidationError(problems)
    fb = fee_for(o, filing_date)
    mismatch = abs((normal_paid + additional_paid) - fb.total) > 0.5
    f = Filing(obligation_id=o.id, srn=srn.strip().upper(), filing_date=filing_date, normal_fee_paid=normal_paid,
               additional_fee_paid=additional_paid, delay_days=fb.delay_days, computed_fee_json=fee_json(fb),
               fee_mismatch=mismatch, created_by_id=user.id,
               attachment_path=attachment[0] if attachment else None,
               attachment_name=attachment[1] if attachment else None)
    db.session.add(f)
    before = obligation_snapshot(o)
    o.status = "FILED"
    db.session.flush()
    audit.record(db.session, actor, "FILED", "obligation", o.key, o.entity_id, before=before,
                 after={**obligation_snapshot(o), "srn": f.srn, "filing_date": filing_date,
                        "delay_days": fb.delay_days, "computed_total": fb.total,
                        "paid_total": normal_paid + additional_paid, "fee_mismatch": mismatch,
                        "fee_verified": fb.verified})
    return f


# ------------------------------------------------------------------ health
def health(o: Obligation, today: date) -> str:
    if o.superseded_at:
        return "superseded"
    if o.status in CLOSED:
        return "closed"
    days = (o.due_date - today).days
    if days < 0:
        return "overdue"
    if days <= 7:
        return "due7"
    if days <= 30:
        return "due30"
    return "upcoming"


HEALTH_LABELS = {"overdue": "Overdue", "due7": "Due ≤ 7 days", "due30": "Due ≤ 30 days", "upcoming": "Upcoming",
                 "closed": "Filed / closed", "superseded": "Superseded"}


def visible_entities_query(user: User):
    q = select(Entity).where(Entity.archived.is_(False))
    if not has(user, "view_all"):
        q = q.where((Entity.preparer_id == user.id) | (Entity.rm_id == user.id))
    return q


def visible_obligations_query(user: User, include_pre_engagement: bool = False):
    """Entity obligations of visible entities + DIN obligations of their directors."""
    ents = visible_entities_query(user).with_only_columns(Entity.id)
    persons = select(EntityPerson.person_id).where(EntityPerson.entity_id.in_(ents),
                                                   EntityPerson.ceased_on.is_(None))
    q = select(Obligation).where(Obligation.superseded_at.is_(None),
                                 (Obligation.entity_id.in_(ents)) | (Obligation.person_id.in_(persons)))
    if not include_pre_engagement:
        # Closed items from before the engagement are history; OPEN ones were inherited and are now the
        # firm's to clear, so they stay visible (tagged "Pre-engagement"). KPIs exclude both (Phase 4).
        q = q.where((Obligation.pre_engagement.is_(False)) | (Obligation.status.not_in(list(CLOSED))))
    return q


def can_see_obligation(user: User, o: Obligation) -> bool:
    from .permissions import can_see_entity
    if has(user, "view_all"):
        return True
    if o.entity_id is not None:
        return can_see_entity(user, o.entity)
    return any(can_see_entity(user, link.entity) for link in (o.person.links if o.person else []))


def fy_label_for(d: date) -> str:
    return fy_key_for_end(standard_fy_end(d))
