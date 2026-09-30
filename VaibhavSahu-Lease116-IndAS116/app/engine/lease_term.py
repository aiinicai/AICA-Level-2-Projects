"""Lease term engine (Ind AS 116.18–21, B34–B41).

The accounting lease term is determined separately from the contractual maximum:

    non-cancellable period
  + periods covered by lessee extension options reasonably certain to be exercised
  + periods covered by lessee termination options reasonably certain NOT to be exercised

Termination rights held only by the lessor are ignored (B35). Where both parties can
terminate without more than an insignificant penalty, the enforceable period caps the
term (B34) — this is always flagged as an accounting judgment.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from .calendar_utils import months_between_frac, next_day
from .models import (JudgmentFlag, LeaseOption, LeaseTermInput, OptionHolder, OptionKind,
                     TermResult)
from .references import ref


def _fmt(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def determine_lease_term(ti: LeaseTermInput) -> TermResult:
    expl: list[str] = []
    flags: list[JudgmentFlag] = []
    c = ti.commencement
    contract_end = ti.contract_end
    expl.append(f"Commencement date {_fmt(c)}; contractual term ends {_fmt(contract_end)}.")

    lessee_terms = sorted(
        [o for o in ti.options if o.kind == OptionKind.TERMINATION and o.holder in (OptionHolder.LESSEE, OptionHolder.BOTH)
         and o.exercise_date is not None],
        key=lambda o: o.exercise_date)
    lessor_terms = [o for o in ti.options if o.kind == OptionKind.TERMINATION and o.holder == OptionHolder.LESSOR]
    extensions = sorted(
        [o for o in ti.options if o.kind == OptionKind.EXTENSION and o.holder in (OptionHolder.LESSEE, OptionHolder.BOTH)],
        key=lambda o: (o.exercise_date or contract_end))
    lessor_ext = [o for o in ti.options if o.kind == OptionKind.EXTENSION and o.holder == OptionHolder.LESSOR]
    purchases = [o for o in ti.options if o.kind == OptionKind.PURCHASE]

    for o in lessor_terms:
        expl.append(f"Lessor-only termination right ({o.description or 'lessor option'}) ignored in determining the lease term ({ref('LESSOR_OPTION')}).")
    for o in lessor_ext:
        expl.append("Extension at the lessor's option / mutual consent is not a lessee option and is excluded unless enforceable "
                    f"({ref('TERM')}).")
        flags.append(JudgmentFlag("TERM_MUTUAL_RENEWAL", "Renewal requires lessor consent",
                                  "Renewal is not a unilateral lessee option. Confirm whether the renewal period is enforceable "
                                  "(B34) considering the broader economics of the arrangement (IFRIC agenda decision, Nov 2019).",
                                  ref("ENFORCEABLE")))

    # Non-cancellable period ends at the first date the lessee can terminate
    noncancellable_end = contract_end
    for o in lessee_terms:
        te = o.exercise_date
        if te is not None and te <= contract_end:
            last_day = te if te <= contract_end else contract_end
            # lessee may terminate with effect from te (lease ends at the end of te - 1 day) — we store te as the
            # last day of occupancy if the option is described as "terminate on te".
            noncancellable_end = min(noncancellable_end, last_day)
            break
    if noncancellable_end < contract_end:
        expl.append(f"Non-cancellable period ends {_fmt(noncancellable_end)} (earliest lessee termination option).")

    term_end = contract_end
    termination_reflected = False
    for o in lessee_terms:
        te = o.exercise_date
        if te is None or te >= contract_end:
            continue
        flags.append(JudgmentFlag("TERM_TERMINATION_OPTION", "Termination option — lease term judgment",
                                  f"Lessee termination option (lease would end {_fmt(te)}). Assessment: "
                                  f"{'reasonably certain NOT to exercise' if o.reasonably_certain else 'not reasonably certain to continue'}.",
                                  ref("TERM"), assumptions=[o.rationale or "Rationale not documented"]))
        if o.reasonably_certain:
            expl.append(f"Termination option (lease would end {_fmt(te)}): lessee reasonably certain NOT to exercise — "
                        f"period after the option included ({ref('TERM')}). Rationale: {o.rationale or 'not documented'}.")
        else:
            term_end = min(term_end, te)
            termination_reflected = True
            expl.append(f"Termination option (lease would end {_fmt(te)}): NOT reasonably certain that lessee will continue — "
                        f"lease term ends {_fmt(te)}; any termination penalty is a lease payment (27(e)).")
            break

    purchase_rc = False
    if term_end == contract_end:
        for o in extensions:
            end = o.extension_end_date
            if end is None:
                continue
            if o.reasonably_certain:
                expl.append(f"Extension option to {_fmt(end)}: reasonably certain to be exercised — included "
                            f"({ref('TERM')}). Rationale: {o.rationale or 'not documented'}.")
                term_end = max(term_end, end)
            else:
                expl.append(f"Extension option to {_fmt(end)}: not reasonably certain — excluded. "
                            "Potential future cash outflows to be considered for disclosure (para 59(b)(ii)).")
                flags.append(JudgmentFlag("TERM_EXTENSION_OPTION", "Extension option — lease term judgment",
                                          f"Extension option to {_fmt(end)} excluded (not reasonably certain).",
                                          ref("TERM"), assumptions=[o.rationale or "Rationale not documented"]))
                break
            flags.append(JudgmentFlag("TERM_EXTENSION_OPTION", "Extension option — lease term judgment",
                                      f"Extension option to {_fmt(end)} included (reasonably certain).",
                                      ref("TERM"), assumptions=[o.rationale or "Rationale not documented"]))

    for o in purchases:
        if o.reasonably_certain:
            purchase_rc = True
            if o.exercise_date and o.exercise_date < term_end:
                term_end = o.exercise_date
            expl.append(f"Purchase option{(' at ' + _fmt(o.exercise_date)) if o.exercise_date else ''} reasonably certain — "
                        f"exercise price included (27(d)); ROU depreciated over the useful life of the asset ({ref('DEPRECIATION')}).")
        else:
            expl.append("Purchase option not reasonably certain — exercise price excluded.")
        flags.append(JudgmentFlag("PURCHASE_OPTION", "Purchase option assessment",
                                  "Assess whether the lessee is reasonably certain to exercise the purchase option.",
                                  ref("PAYMENTS"), assumptions=[o.rationale or "Rationale not documented"]))

    if ti.enforceable_end is not None and ti.enforceable_end < term_end:
        term_end = ti.enforceable_end
        expl.append(f"Lease term capped at enforceable period ending {_fmt(ti.enforceable_end)} ({ref('ENFORCEABLE')}). "
                    f"Rationale: {ti.enforceable_rationale or 'not documented'}.")
        flags.append(JudgmentFlag("ENFORCEABLE_PERIOD", "Enforceable period (B34)",
                                  "Lease term limited by the enforceable period. Document the broader-economics assessment.",
                                  ref("ENFORCEABLE"), assumptions=[ti.enforceable_rationale or "Rationale not documented"]))

    max_end = contract_end
    for o in extensions:
        if o.extension_end_date:
            max_end = max(max_end, o.extension_end_date)
    if term_end < c:
        term_end = c
    term_days = (next_day(term_end) - c).days
    term_months = months_between_frac(c, next_day(term_end))
    expl.append(f"Accounting lease term: {_fmt(c)} to {_fmt(term_end)} ({term_months.quantize(Decimal('0.01'))} months; "
                f"{term_days} days). Contractual maximum incl. all options: {_fmt(max_end)}.")
    return TermResult(commencement=c, contract_end=contract_end, noncancellable_end=noncancellable_end,
                      term_end=term_end, max_possible_end=max_end, term_days=term_days, term_months=term_months,
                      purchase_option_rc=purchase_rc, explanation=expl, flags=flags,
                      termination_reflected=termination_reflected)


def is_short_term(term: TermResult, has_purchase_option: bool) -> tuple[bool, str]:
    """Short-term lease test per Appendix A definition."""
    if has_purchase_option:
        return False, "Lease contains a purchase option — cannot be a short-term lease (App. A)."
    if term.term_months <= Decimal(12):
        return True, f"Accounting lease term {term.term_months.quantize(Decimal('0.01'))} months ≤ 12 months at commencement."
    return False, f"Accounting lease term {term.term_months.quantize(Decimal('0.01'))} months exceeds 12 months."
