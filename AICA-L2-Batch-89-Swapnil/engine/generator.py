"""engine.generate(): a pure function from (entity, facts, events, directors,
rule pack, as_of) to obligation specs (brief §5.8). No Flask, no DB.

The service layer upserts specs by their stable key; this module only decides
*what* is due and *when*.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable

from .dates import (FY, agm_deadline, company_first_fy_end, due_date, financial_years,
                    fy_containing, fy_key_for_end, half_years, kyc_cycle_dues, kyc_cycle_key,
                    llp_first_fy_end, march31s_after, standard_fy_end)
from .predicates import VARIANTS, Ctx, evaluate, is_small_company, rule_9b_trigger_fy
from .rulepack import Rule, RulePack
from .types import EntityIn, EventIn, FactsIn, PersonIn, Spec

PERSON_RECURRENCES = {"din_annual", "din_cycle", "din_event"}


def horizon_end(as_of: date) -> date:
    """Generate up to the end of FY(as_of) + 1."""
    return date(standard_fy_end(as_of).year + 1, 3, 31)


def entity_fys(entity: EntityIn, upto: date) -> list[FY]:
    first_end = (llp_first_fy_end(entity.incorporation_date, entity.llp_elect_longer_first_fy)
                 if entity.is_llp else company_first_fy_end(entity.incorporation_date))
    return financial_years(entity.incorporation_date, first_end, upto)


def agm_deadlines(fys: list[FY], facts_by_fy: dict[str, FactsIn]) -> dict[str, date]:
    """s.96 chain: the 15-month limit runs from the previous AGM actually held,
    or from its last permissible date if it was not held."""
    out: dict[str, date] = {}
    prev: date | None = None
    for i, fy in enumerate(fys):
        dl = agm_deadline(fy, i == 0, prev)
        out[fy.key] = dl
        f = facts_by_fy.get(fy.key)
        prev = f.agm_date if f and f.agm_date else dl
    return out


def _next_fixed(after: date, month: int, day: int) -> date:
    d = date(after.year, month, day)
    return d if d > after else date(after.year + 1, month, day)


class _Builder:
    def __init__(self, entity: EntityIn, rulepack: RulePack, as_of: date, fys: list[FY],
                 facts_by_fy: dict[str, FactsIn], period_flags, decisions, settings, filing_dates=None):
        self.e, self.rp, self.as_of, self.fys = entity, rulepack, as_of, fys
        self.facts = facts_by_fy
        self.period_flags, self.decisions, self.settings = period_flags, decisions, settings
        self.filing_dates = filing_dates or {}
        self.specs: dict[str, Spec] = {}
        self.agm = agm_deadlines(fys, facts_by_fy)

    def ctx(self, **kw) -> Ctx:
        return Ctx(self.e, self.rp, self.as_of, self.fys, self.facts, period_flags=self.period_flags,
                   decisions=self.decisions, settings=self.settings, filing_dates=self.filing_dates, **kw)

    # ------------------------------------------------------------------ emit
    def emit(self, rule: Rule, ctx: Ctx, period_key: str, anchor_type: str, anchor_date: date,
             ref_date: date, *, provisional: bool = False, agm_not_held: bool = False,
             event: EventIn | None = None, fixed_due: date | None = None, notes: Iterable[str] = ()) -> Spec | None:
        if not rule.in_force(ref_date):
            return None
        ctx.stale, ctx.needs_decision = False, None
        if not all(evaluate(x, ctx) for x in rule.applicability):
            return None
        variant = VARIANTS[rule.variant](ctx) if rule.variant else None
        if fixed_due is not None:
            due = fixed_due
        elif rule.fixed is not None:
            due = _next_fixed(anchor_date, rule.fixed.month, rule.fixed.day)
        else:
            due = due_date(anchor_date, rule.offset.model_dump())
        notes = list(notes)
        for s in self.rp.schemes:
            if (s.kind == "DUE_DATE_EXTENSION" and rule.code in s.rule_codes and s.new_due_date
                    and (not s.period_keys or period_key in s.period_keys) and s.new_due_date > due):
                notes.append(f"Due date extended from {due:%d-%m-%Y} to {s.new_due_date:%d-%m-%Y} by {s.circular_ref}")
                due = s.new_due_date
        key = f"{self.e.id}:{rule.code}:{period_key}" + (f":{event.id}" if event is not None else "")
        spec = Spec(
            key=key, rule_code=rule.code, form=variant or rule.form, title=rule.title, period_key=period_key,
            anchor_type=anchor_type, anchor_date=anchor_date, due_date=due, entity_id=self.e.id,
            event_id=event.id if event is not None else None, variant=variant,
            provisional=provisional or rule.provisional, facts_stale=ctx.stale,
            needs_decision=ctx.needs_decision, agm_not_held=agm_not_held,
            pre_engagement=bool(self.e.engagement_start and due < self.e.engagement_start),
            interpretation=rule.interpretation, verified=rule.verified, rule_version=self.rp.version,
            rule_hash=rule.content_hash, law=rule.law, fee_regime=rule.fee_regime, notes=notes)
        if rule.notes:
            spec.notes.append(rule.notes)
        self.specs[key] = spec
        return spec

    # --------------------------------------------------------- recurrences
    def once(self, rule: Rule) -> None:
        ctx = self.ctx(fy=self.fys[0])
        inc = self.e.incorporation_date
        if rule.anchor == "FIRST_AUDITOR_APPOINTMENT":
            ev = next((x for x in self._events if x.type == "FIRST_AUDITOR_APPOINTED"), None)
            if ev:
                self.emit(rule, ctx, "ONCE", rule.anchor, ev.date, inc)
            else:
                self.emit(rule, ctx, "ONCE", rule.anchor, due_date(inc, {"days": 30}), inc, provisional=True,
                          notes=["Appointment date not recorded: assumed on the last permissible day (incorporation + 30)"])
            return
        self.emit(rule, ctx, "ONCE", "INCORPORATION", inc, inc)

    def annual(self, rule: Rule) -> None:
        for fy in self.fys:
            ctx = self.ctx(fy=fy)
            f = self.facts.get(fy.key)
            a = rule.anchor
            if a == "FY_END":
                self.emit(rule, ctx, fy.key, a, fy.end, fy.end)
            elif a == "FY_START":
                self.emit(rule, ctx, fy.key, a, fy.start, fy.end)
            elif a == "AGM_DEADLINE":
                self.emit(rule, ctx, fy.key, a, self.agm[fy.key], fy.end)
            elif a == "AGM_ACTUAL_OR_DEADLINE":
                if f and f.agm_date:
                    self.emit(rule, ctx, fy.key, "AGM_ACTUAL", f.agm_date, fy.end)
                else:
                    dl = self.agm[fy.key]
                    held = self.as_of > dl
                    self.emit(rule, ctx, fy.key, "AGM_DEADLINE", dl, fy.end, provisional=not held,
                              agm_not_held=held,
                              notes=["AGM not held: due date runs from the last date on which it should have been held "
                                     "(s.137(1) proviso / s.92(4))"] if held else
                                    ["Provisional: AGM date not yet entered; computed from the last permissible AGM date"])
            elif a == "BOARD_APPROVAL_OR_AGM":
                if f and f.board_approval_date:
                    self.emit(rule, ctx, fy.key, "BOARD_APPROVAL", f.board_approval_date, fy.end)
                else:
                    self.emit(rule, ctx, fy.key, "AGM_DEADLINE", self.agm[fy.key] - timedelta(days=21), fy.end,
                              provisional=True, notes=["Board approval date not entered: assumed 21 days before the AGM deadline"])
            else:  # pragma: no cover - guarded by pack validation tests
                raise ValueError(f"{rule.code}: anchor {a} not valid for annual rules")

    def half_yearly(self, rule: Rule, upto: date) -> None:
        for hy in half_years(self.e.incorporation_date, upto):
            if rule.half and hy.half != rule.half:
                continue
            ctx = self.ctx(fy=fy_containing(self.fys, hy.end) or self.fys[-1], half=hy)
            self.emit(rule, ctx, hy.key, "HALF_YEAR_END", hy.end, hy.end)

    def march31(self, rule: Rule, upto: date) -> None:
        for m in march31s_after(self.e.incorporation_date, upto):
            ctx = self.ctx(fy=fy_containing(self.fys, m) or self.fys[-1], march31=m)
            self.emit(rule, ctx, fy_key_for_end(m), "CALENDAR_FIXED", m, m)

    def event(self, rule: Rule) -> None:
        for ev in self._events:
            if ev.type not in rule.event_types:
                continue
            ctx = self.ctx(fy=fy_containing(self.fys, ev.date) or self.fys[-1], event=ev)
            self.emit(rule, ctx, f"EVT-{ev.date.isoformat()}", "EVENT_DATE", ev.date, ev.date, event=ev)

    def first_trigger(self, rule: Rule) -> None:
        ctx = self.ctx(fy=self.fys[-1])
        trig, _ = rule_9b_trigger_fy(ctx)
        if trig is None:
            return
        ctx = self.ctx(fy=trig)
        spec = self.emit(rule, ctx, trig.key, "FY_END", trig.end, trig.end)
        if spec is None:
            return
        # I6: company became small again after the trigger -> partner decides whether 9B continues
        later = [f for f in self.fys if trig.end < f.end <= self.as_of]
        if later and self.decisions.get("9B_REVERSION") is None:
            c = self.ctx(fy=later[-1])
            if is_small_company(c).result is True:
                spec.needs_decision = "9B_REVERSION"
                spec.notes.append(f"Company is small again at {later[-1].end:%d-%m-%Y}: partner to decide "
                                  "whether Rule 9B obligations continue (LEGAL_NOTES I6)")


def generate(entity: EntityIn, facts_by_fy: dict[str, FactsIn], events: list[EventIn],
             directors: list[PersonIn], rulepack: RulePack, as_of: date, *,
             period_flags: dict[str, dict[str, Any]] | None = None,
             decisions: dict[str, str] | None = None,
             settings: dict[str, Any] | None = None,
             filing_dates: dict[str, date] | None = None) -> list[Spec]:
    """All obligation specs for one entity (and its directors' DIN obligations)
    from incorporation up to the end of FY(as_of) + 1. Deterministic and pure.

    filing_dates: FY key -> date that FY's annual return was filed (used to judge
    small-company status under the limits in force when it was filed)."""
    upto = horizon_end(as_of)
    fys = entity_fys(entity, upto)
    b = _Builder(entity, rulepack, as_of, fys, facts_by_fy, period_flags or {}, decisions or {}, settings or {},
                 filing_dates)
    b._events = sorted(events, key=lambda e: (e.date, str(e.id)))
    for rule in rulepack.rules:
        if rule.recurrence in PERSON_RECURRENCES or entity.entity_type not in rule.entity_types:
            continue
        {"once": b.once, "annual": b.annual, "event": b.event, "first_trigger": b.first_trigger,
         "half_yearly": lambda r: b.half_yearly(r, upto), "march31": lambda r: b.march31(r, upto)}[rule.recurrence](rule)
    specs = list(b.specs.values())
    for p in directors:
        specs.extend(generate_person(p, rulepack, as_of))
    uniq = {s.key: s for s in specs}
    return sorted(uniq.values(), key=lambda s: (s.due_date, s.key))


def generate_person(person: PersonIn, rulepack: RulePack, as_of: date) -> list[Spec]:
    """DIN-level obligations (DIR-3 KYC). Keyed by DIN, not by company, so a
    director on three boards gets one KYC obligation, not three."""
    upto = horizon_end(as_of)
    out: list[Spec] = []

    def mk(rule: Rule, period: str, anchor_type: str, anchor: date, due: date, notes=()) -> None:
        out.append(Spec(key=f"person:{person.din}:{rule.code}:{period}", rule_code=rule.code, form=rule.form,
                        title=rule.title, period_key=period, anchor_type=anchor_type, anchor_date=anchor,
                        due_date=due, person_din=person.din, interpretation=rule.interpretation,
                        verified=rule.verified, rule_version=rulepack.version, rule_hash=rule.content_hash,
                        law=rule.law, fee_regime=rule.fee_regime, notes=list(notes) + ([rule.notes] if rule.notes else [])))

    for rule in rulepack.rules:
        if rule.recurrence == "din_annual":
            y = standard_fy_end(person.din_allotment_date).year
            while date(y, 3, 31) <= upto:
                ref = date(y, 3, 31)
                key = fy_key_for_end(ref)
                if rule.in_force(ref) and not (person.last_annual_kyc_fy and key <= person.last_annual_kyc_fy):
                    mk(rule, key, "DIN_FY_END", ref, _next_fixed(ref, rule.fixed.month, rule.fixed.day))
                y += 1
        elif rule.recurrence == "din_cycle":
            for due in kyc_cycle_dues(person.din_allotment_date, upto, person.kyc_override_first_due):
                if rule.in_force(due):
                    notes = ["Partner override of the KYC cycle"] if person.kyc_override_first_due else []
                    mk(rule, kyc_cycle_key(due), "DIN_CYCLE", date(due.year, 3, 31), due, notes)
        elif rule.recurrence == "din_event":
            for d in person.detail_changes:
                if rule.in_force(d):
                    mk(rule, f"CHG-{d.isoformat()}", "DETAIL_CHANGE", d, due_date(d, rule.offset.model_dump()))
    return out
