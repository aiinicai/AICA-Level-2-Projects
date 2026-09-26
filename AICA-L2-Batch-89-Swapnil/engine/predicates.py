"""Classification functions and the applicability-predicate REGISTRY.

The YAML rule pack may reference only names registered here (combined with
all_of / any_of / not) — nothing in the pack is ever eval()'d.

Every classification returns a :class:`Classification` carrying the numbers
used, the threshold row (version) and the citation, so the entity page can
show *why* (brief §5.4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from .dates import FY, HalfYear, fy_key_for_end
from .types import EntityIn, EventIn, FactsIn

AMBIGUOUS = "AMBIGUOUS"
CRORE = 10_000_000
LAKH = 100_000


def inr_short(v: float | None) -> str:
    if v is None:
        return "not entered"
    if abs(v) >= CRORE:
        return f"₹{v / CRORE:g} cr"
    return f"₹{v / LAKH:g} lakh"


@dataclass
class Classification:
    name: str
    result: Any
    reasons: list[str] = field(default_factory=list)
    citation: str = ""
    threshold_version: str = ""

    @property
    def ambiguous(self) -> bool:
        return self.result == AMBIGUOUS


# --------------------------------------------------------------------- context
@dataclass
class Ctx:
    entity: EntityIn
    rulepack: Any
    as_of: date
    fys: list[FY]
    facts_by_fy: dict[str, FactsIn]
    fy: FY | None = None
    half: HalfYear | None = None
    march31: date | None = None
    event: EventIn | None = None
    period_flags: dict[str, dict[str, Any]] = field(default_factory=dict)
    decisions: dict[str, str] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)
    filing_dates: dict[str, date] = field(default_factory=dict)   # FY key -> date its annual return was filed
    # set during evaluation
    stale: bool = False
    needs_decision: str | None = None

    # ------------------------------------------------------------ fact access
    def _idx(self, fy: FY) -> int:
        return self.fys.index(fy)

    def _fact_for(self, fy: FY, name: str, stale_ok: bool = True) -> Any:
        exact = self.facts_by_fy.get(fy.key)
        if exact is not None and getattr(exact, name) is not None:
            return getattr(exact, name)
        if not stale_ok:
            return None
        # nearest earlier FY with the value, then nearest later one
        i = self._idx(fy)
        order = list(range(i - 1, -1, -1)) + list(range(i + 1, len(self.fys)))
        for j in order:
            f = self.facts_by_fy.get(self.fys[j].key)
            if f is not None and getattr(f, name) is not None:
                self.stale = True
                return getattr(f, name)
        master = {"paid_up_capital": self.entity.paid_up_capital,
                  "llp_contribution": self.entity.llp_contribution}.get(name)
        if master is not None:
            if exact is None:
                self.stale = True
            return master
        if exact is None:
            self.stale = True
        return None

    def fact(self, name: str, stale_ok: bool = True) -> Any:
        assert self.fy is not None, "fact() needs an FY context"
        return self._fact_for(self.fy, name, stale_ok)

    @property
    def prev_fy(self) -> FY | None:
        if self.fy is None:
            return None
        i = self._idx(self.fy)
        return self.fys[i - 1] if i > 0 else None

    def prev_fact(self, name: str) -> Any:
        """Figure for the immediately preceding FY; ``0`` for a first FY (none exists)."""
        p = self.prev_fy
        if p is None:
            return 0.0
        return self._fact_for(p, name)

    def threshold(self, code: str, on: date):
        return self.rulepack.threshold(code, on)

    def flag(self, key: str, name: str) -> Any:
        return self.period_flags.get(key, {}).get(name)


def _ge(v: float | None, limit: float) -> bool:
    return v is not None and v >= limit


# ------------------------------------------------------------- classifiers
def _small_test(paid_up: float, prev_turnover: float, values: dict[str, float]) -> bool:
    return paid_up <= values["paid_up"] and prev_turnover <= values["turnover"]


def classify_small_with(entity: EntityIn, paid_up: float, prev_turnover: float, threshold) -> Classification:
    """Pure s.2(85) test against one explicit threshold row."""
    c = Classification("small_company", False, citation=f"s.2(85) Companies Act 2013; {threshold.law}",
                       threshold_version=f"{threshold.code} from {threshold.effective_from:%d-%m-%Y}")
    if entity.entity_type not in {"PRIVATE", "OPC"}:
        c.reasons.append(f"{entity.entity_type} is not a private company")
        return c
    for flag, why in ((entity.is_holding, "holding company"), (entity.is_subsidiary, "subsidiary company"),
                      (entity.special_act, "governed by a special Act")):
        if flag:
            c.reasons.append(f"excluded: {why}")
            return c
    v = threshold.values
    c.result = _small_test(paid_up, prev_turnover, v)
    c.reasons.append(f"paid-up {inr_short(paid_up)} vs limit {inr_short(v['paid_up'])}; "
                     f"preceding-FY turnover {inr_short(prev_turnover)} vs limit {inr_short(v['turnover'])}")
    return c


def is_small_company(ctx: Ctx, fy: FY | None = None) -> Classification:
    """Small-company status for an FY. The evaluation date is the date the FY's
    annual return was actually filed (if known), otherwise as_of (it would be
    filed now). If the threshold in force at FY end differs from the one in force
    on the evaluation date AND the answer differs, return AMBIGUOUS unless a
    partner decision exists (Q3: always ask) — LEGAL_NOTES I5."""
    fy = fy or ctx.fy
    saved = ctx.fy
    ctx.fy = fy
    try:
        paid_up = ctx.fact("paid_up_capital") or 0.0
        prev_turnover = ctx.prev_fact("turnover") or 0.0
    finally:
        ctx.fy = saved
    t_end = ctx.threshold("SMALL_COMPANY", fy.end)
    c = classify_small_with(ctx.entity, paid_up, prev_turnover, t_end)
    eval_on = max(ctx.filing_dates.get(fy.key) or ctx.as_of, fy.end)
    t_now = ctx.threshold("SMALL_COMPANY", eval_on)
    if t_now.effective_from != t_end.effective_from and ctx.entity.entity_type in {"PRIVATE", "OPC"}:
        c_now = classify_small_with(ctx.entity, paid_up, prev_turnover, t_now)
        if c_now.result != c.result:
            decision = ctx.decisions.get(f"SMALL:{fy.key}")
            if decision in ("SMALL", "NOT_SMALL"):
                c.result = decision == "SMALL"
                c.reasons.append(f"partner decision recorded: {decision}")
            else:
                c.result = AMBIGUOUS
                c.reasons.append(
                    f"limits changed between FY end ({c.threshold_version}) and {eval_on:%d-%m-%Y} "
                    f"({c_now.threshold_version}); old limits say {'small' if not c_now.result else 'not small'}, "
                    f"new limits say {'small' if c_now.result else 'not small'} — partner decision required")
            c.threshold_version += f" / {c_now.threshold_version}"
    return c


def mgt7_variant(ctx: Ctx) -> str:
    if ctx.entity.entity_type == "OPC":
        return "MGT-7A"
    small = is_small_company(ctx)
    if small.ambiguous:
        ctx.needs_decision = f"SMALL:{ctx.fy.key}"
        return "MGT-7 or MGT-7A (small-company decision needed)"
    return "MGT-7A" if small.result else "MGT-7"


def aoc4_variant(ctx: Ctx) -> str:
    return classify_aoc4(ctx).result


def classify_aoc4(ctx: Ctx) -> Classification:
    e = ctx.entity
    t = ctx.threshold("XBRL", ctx.fy.end)
    paid_up, turnover = ctx.fact("paid_up_capital"), ctx.fact("turnover")
    ind_as = bool(ctx.fact("ind_as"))
    c = Classification("aoc4_variant", "AOC-4", citation=t.law, threshold_version=f"XBRL from {t.effective_from:%d-%m-%Y}")
    if e.nbfc and ind_as:
        c.result = "AOC-4 NBFC (Ind AS)"
        c.reasons.append("NBFC following Ind AS")
        return c
    excluded = e.nbfc or e.hfc or e.banking or e.excluded_sector
    if e.entity_type == "PUBLIC_LISTED" or e.listed_subsidiary:
        c.reasons.append("listed company or subsidiary of a listed company")
    elif _ge(paid_up, t.values["paid_up"]):
        c.reasons.append(f"paid-up {inr_short(paid_up)} ≥ {inr_short(t.values['paid_up'])}")
    elif _ge(turnover, t.values["turnover"]):
        c.reasons.append(f"turnover {inr_short(turnover)} ≥ {inr_short(t.values['turnover'])}")
    elif ind_as and not excluded:
        c.reasons.append("required to prepare Ind AS financial statements")
    else:
        c.reasons.append(f"below XBRL limits (paid-up {inr_short(paid_up)}, turnover {inr_short(turnover)})")
        return c
    if excluded:
        c.reasons.append("but excluded sector (banking/insurance/power/NBFC/HFC) — plain AOC-4")
        return c
    c.result = "AOC-4 XBRL"
    return c


def classify_mgt8(ctx: Ctx) -> Classification:
    t = ctx.threshold("MGT8", ctx.fy.end)
    paid_up, turnover = ctx.fact("paid_up_capital"), ctx.fact("turnover")
    r = ctx.entity.entity_type == "PUBLIC_LISTED" or _ge(paid_up, t.values["paid_up"]) or _ge(turnover, t.values["turnover"])
    return Classification("mgt8_required", r,
                          [f"paid-up {inr_short(paid_up)} (limit {inr_short(t.values['paid_up'])}), "
                           f"turnover {inr_short(turnover)} (limit {inr_short(t.values['turnover'])})"],
                          t.law, f"MGT8 from {t.effective_from:%d-%m-%Y}")


def classify_csr(ctx: Ctx) -> Classification:
    t = ctx.threshold("CSR", ctx.fy.end)
    override = ctx.fact("csr_override", stale_ok=False)
    nw, to, np_ = ctx.prev_fact("net_worth"), ctx.prev_fact("turnover"), ctx.prev_fact("net_profit")
    r = _ge(nw, t.values["net_worth"]) or _ge(to, t.values["turnover"]) or _ge(np_, t.values["net_profit"])
    c = Classification("csr_applicable", r,
                       [f"preceding FY: net worth {inr_short(nw)}, turnover {inr_short(to)}, net profit {inr_short(np_)}"],
                       t.law, f"CSR from {t.effective_from:%d-%m-%Y}")
    if override is not None:
        c.result = bool(override)
        c.reasons.append(f"overridden in annual facts: {'applicable' if override else 'not applicable'}")
    return c


def classify_secretarial_audit(ctx: Ctx) -> Classification:
    """Rule 9: figures as on the last date of the latest audited FS (= preceding FY end)."""
    t = ctx.threshold("SEC_AUDIT", ctx.fy.end)
    e = ctx.entity
    paid_up, to = ctx.prev_fact("paid_up_capital"), ctx.prev_fact("turnover")
    borrow = ctx.prev_fact("bank_borrowings_at_fy_end")
    r = (e.entity_type == "PUBLIC_LISTED"
         or (e.is_public and (_ge(paid_up, t.values["public_paid_up"]) or _ge(to, t.values["public_turnover"])))
         or _ge(borrow, t.values["borrowings"]))
    return Classification("secretarial_audit_required", r,
                          [f"latest audited FS: paid-up {inr_short(paid_up)}, turnover {inr_short(to)}, "
                           f"bank/PFI borrowings at FY end {inr_short(borrow)}"],
                          t.law, f"SEC_AUDIT from {t.effective_from:%d-%m-%Y}")


def classify_internal_audit(ctx: Ctx) -> Classification:
    t = ctx.threshold("INTERNAL_AUDIT", ctx.fy.end)
    v, e = t.values, ctx.entity
    paid_up, to = ctx.prev_fact("paid_up_capital"), ctx.prev_fact("turnover")
    borrow, dep = ctx.prev_fact("bank_borrowings_max"), ctx.prev_fact("deposits_max")
    if e.entity_type == "PUBLIC_LISTED":
        r = True
    elif e.is_public:
        r = (_ge(paid_up, v["public_paid_up"]) or _ge(to, v["turnover"])
             or _ge(borrow, v["borrowings"]) or _ge(dep, v["public_deposits"]))
    else:
        r = _ge(to, v["turnover"]) or _ge(borrow, v["borrowings"])
    return Classification("internal_audit_required", r,
                          [f"preceding FY: turnover {inr_short(to)}, max borrowings {inr_short(borrow)}"],
                          t.law, f"INTERNAL_AUDIT from {t.effective_from:%d-%m-%Y}")


RULE_9B_FROM = date(2023, 3, 31)


def rule_9b_trigger_fy(ctx: Ctx) -> tuple[FY | None, Classification]:
    """First FY ending on/after 31-03-2023 at whose end the private company was
    not small (test at FY end — Rule 9B wording). Government cos excluded."""
    e = ctx.entity
    c = Classification("rule_9b_applicable", False, citation="Rule 9B, Companies (Prospectus and Allotment of Securities) Rules 2014")
    if e.entity_type != "PRIVATE" or e.government:
        c.reasons.append("applies only to private companies other than Government companies")
        return None, c
    saved_asof, saved_filed = ctx.as_of, ctx.filing_dates
    ctx.filing_dates = {}          # Rule 9B tests strictly at FY end, whenever the return was filed
    for fy in ctx.fys:
        if fy.end < RULE_9B_FROM or fy.end > ctx.as_of:
            continue
        ctx.as_of = fy.end        # the test date is the FY end itself
        try:
            s = is_small_company(ctx, fy)
        finally:
            ctx.as_of = saved_asof
        if s.result is False:
            ctx.filing_dates = saved_filed
            c.result = True
            c.reasons.append(f"not a small company at {fy.end:%d-%m-%Y} ({s.reasons[-1]})")
            return fy, c
    ctx.filing_dates = saved_filed
    c.reasons.append("small company at every FY end since 31-03-2023")
    return None, c


def board_meeting_regime(ctx: Ctx) -> Classification:
    e = ctx.entity
    cite = "s.173(1) and s.173(5) Companies Act 2013; G.S.R. 583(E) dt 13-06-2017 (start-ups)"
    if e.is_llp:
        return Classification("board_meeting_regime", "NA", ["LLP"], cite)
    if e.entity_type == "OPC" and e.single_director:
        return Classification("board_meeting_regime", "NA", ["OPC with a single director — s.173(5) 2nd proviso"], cite)
    why = []
    if e.entity_type == "OPC":
        why.append("OPC")
    if e.status == "DORMANT":
        why.append("dormant company")
    if e.startup and e.entity_type == "PRIVATE":
        why.append("private start-up")
    if ctx.fy is not None and e.entity_type == "PRIVATE":
        s = is_small_company(ctx)
        if s.result is True:
            why.append("small company")
        elif s.ambiguous:
            why.append("small-company status AMBIGUOUS (decision needed)")
    if why and not all("AMBIGUOUS" in w for w in why):
        return Classification("board_meeting_regime", "RELAXED",
                              [", ".join(why) + ": ≥1 meeting in each half of the calendar year, gap ≥ 90 days"], cite)
    return Classification("board_meeting_regime", "REGULAR",
                          ["≥ 4 meetings a year, not more than 120 days between two meetings"], cite)


def classify_small_llp(ctx: Ctx) -> Classification:
    try:
        t = ctx.threshold("SMALL_LLP", ctx.fy.end)
    except Exception:
        return Classification("small_llp", False, ["'small LLP' not defined for FYs before 01-04-2022"],
                              "s.2(1)(ta), LLP Act 2008")
    contrib = ctx.fact("llp_contribution") or 0.0
    to = ctx.prev_fact("turnover") or 0.0
    r = contrib <= t.values["contribution"] and to <= t.values["turnover"]
    return Classification("small_llp", r,
                          [f"contribution {inr_short(contrib)} (limit {inr_short(t.values['contribution'])}); "
                           f"preceding-FY turnover {inr_short(to)} (limit {inr_short(t.values['turnover'])})"],
                          t.law, f"SMALL_LLP from {t.effective_from:%d-%m-%Y}")


def classify_llp_audit(ctx: Ctx) -> Classification:
    """r.24(8): exempt if turnover ≤ ₹40 L OR contribution ≤ ₹25 L — so audit
    only when BOTH are exceeded (correction C3 to the brief)."""
    t = ctx.threshold("LLP_AUDIT", ctx.fy.end)
    contrib = ctx.fact("llp_contribution") or 0.0
    to = ctx.fact("turnover") or 0.0
    r = to > t.values["turnover"] and contrib > t.values["contribution"]
    return Classification("llp_audit_required", r,
                          [f"turnover {inr_short(to)} (limit {inr_short(t.values['turnover'])}) and "
                           f"contribution {inr_short(contrib)} (limit {inr_short(t.values['contribution'])}) — "
                           "audit only if both limits are exceeded"],
                          t.law, f"LLP_AUDIT from {t.effective_from:%d-%m-%Y}")


def classify_all(ctx: Ctx) -> list[Classification]:
    """Everything the entity page's classification panel shows for ctx.fy."""
    if ctx.entity.is_llp:
        return [classify_small_llp(ctx), classify_llp_audit(ctx)]
    out = [is_small_company(ctx)]
    variant = mgt7_variant(ctx)
    out.append(Classification("mgt7_variant", variant, citation="s.92(1); Rule 11(1) Mgmt & Admin Rules"))
    out += [classify_mgt8(ctx), classify_aoc4(ctx), classify_csr(ctx), classify_secretarial_audit(ctx),
            classify_internal_audit(ctx)]
    _, c9b = rule_9b_trigger_fy(ctx)
    out.append(c9b)
    out.append(board_meeting_regime(ctx))
    return out


# ------------------------------------------------------------------ registry
def _isin_by(ctx: Ctx, d: date) -> bool:
    return any(f.isin_obtained_date and f.isin_obtained_date <= d for f in ctx.facts_by_fy.values())


def _pas6(ctx: Ctx) -> bool:
    e = ctx.entity
    if e.entity_type == "PUBLIC_UNLISTED" and e.has_share_capital:
        return True                                   # Rule 9A
    if e.entity_type == "PRIVATE" and ctx.half is not None:
        return _isin_by(ctx, ctx.half.end) and rule_9b_trigger_fy(ctx)[0] is not None
    return False


def _deposits(ctx: Ctx) -> bool:
    v = ctx.flag(fy_key_for_end(ctx.march31), "deposits_outstanding")
    if v is None:
        f = next((ff for ff in ctx.fys if ff.end == ctx.march31), None)
        if f is not None:
            v = ctx.facts_by_fy.get(f.key).deposits_outstanding_31mar if ctx.facts_by_fy.get(f.key) else None
    return bool(v)


def _event_attr(name: str, value: Any) -> Callable[[Ctx], bool]:
    return lambda ctx: ctx.event is not None and ctx.event.attrs.get(name) == value


PREDICATES: dict[str, Callable[[Ctx], bool]] = {
    "always": lambda ctx: True,
    "has_share_capital": lambda ctx: ctx.entity.has_share_capital,
    "not_single_director_opc": lambda ctx: not (ctx.entity.entity_type == "OPC" and ctx.entity.single_director),
    "ro_not_furnished_at_incorporation": lambda ctx: not ctx.entity.ro_furnished_at_incorporation,
    "adt1_for_first_auditor_setting": lambda ctx: bool(ctx.settings.get("adt1_for_first_auditor", True)),
    "is_dormant": lambda ctx: ctx.entity.status == "DORMANT",
    "deposit_rules_apply": lambda ctx: not (ctx.entity.nbfc or ctx.entity.hfc or ctx.entity.banking),
    "deposits_outstanding": _deposits,
    "msme_dues_over_45": lambda ctx: bool(ctx.flag(ctx.half.key, "msme_over_45")) if ctx.half else False,
    "pas6_applicable": _pas6,
    "rule_9b_trigger": lambda ctx: rule_9b_trigger_fy(ctx)[0] is not None,
    "csr_applicable": lambda ctx: bool(classify_csr(ctx).result),
    "cost_audit_applicable": lambda ctx: bool(ctx.fact("cost_audit_applicable")),
    "public_company": lambda ctx: ctx.entity.is_public,
    "public_or_private_sub_of_public": lambda ctx: ctx.entity.is_public or ctx.entity.subsidiary_of_public,
    "secretarial_audit_required": lambda ctx: bool(classify_secretarial_audit(ctx).result),
    "internal_audit_required": lambda ctx: bool(classify_internal_audit(ctx).result),
    "has_subs_assoc_jv": lambda ctx: bool(ctx.fact("has_subs_assoc_jv")),
    "auditor_appointed_at_agm": lambda ctx: bool(ctx.fact("auditor_appointed_at_agm", stale_ok=False)),
    "mgt8_required": lambda ctx: bool(classify_mgt8(ctx).result),
    "llp_audit_required": lambda ctx: bool(classify_llp_audit(ctx).result),
    "not_first_fy": lambda ctx: ctx.fy is not None and ctx.prev_fy is not None,
    "event_private_placement": _event_attr("kind", "PRIVATE_PLACEMENT"),
    "event_cause_resignation": _event_attr("cause", "RESIGNATION"),
    "event_special_resolution": _event_attr("special_resolution", True),
}

VARIANTS: dict[str, Callable[[Ctx], str]] = {
    "mgt7_variant": mgt7_variant,
    "aoc4_variant": aoc4_variant,
}


def validate_expr(expr: Any) -> None:
    if isinstance(expr, str):
        if expr not in PREDICATES:
            raise ValueError(f"unknown predicate {expr!r} (registered: {', '.join(sorted(PREDICATES))})")
        return
    if isinstance(expr, dict) and len(expr) == 1:
        (op, arg), = expr.items()
        if op in ("all_of", "any_of") and isinstance(arg, list) and arg:
            for a in arg:
                validate_expr(a)
            return
        if op == "not":
            validate_expr(arg)
            return
    raise ValueError(f"invalid applicability expression {expr!r}; use a predicate name or all_of/any_of/not")


def evaluate(expr: Any, ctx: Ctx) -> bool:
    if isinstance(expr, str):
        return bool(PREDICATES[expr](ctx))
    (op, arg), = expr.items()
    if op == "all_of":
        return all(evaluate(a, ctx) for a in arg)
    if op == "any_of":
        return any(evaluate(a, ctx) for a in arg)
    return not evaluate(arg, ctx)
