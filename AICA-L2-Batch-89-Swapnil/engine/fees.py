"""Fee engine (brief §6.4-F): normal fee + additional fee by regime, then the
best applicable scheme overlay. Penalties are never computed here (s.454 is
adjudicated by the ROC) — only fees prescribed by the fee rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .rulepack import RulePackError
from .types import EntityIn

HIGHER_FORMS = {"INC22", "INC22_VERIFY", "PAS3", "PAS3_PP"}
REQUIRED_TABLES = {"NORMAL_COMPANY", "NORMAL_LLP", "MULTIPLIER", "MULTIPLIER_S139", "HIGHER_MULTIPLIER",
                   "PER_DAY_100", "CHARGE", "FIXED_KYC", "LLP_MATRIX"}


@dataclass
class FeeBreakdown:
    rule_code: str
    regime: str
    normal: float = 0.0
    additional: float = 0.0
    scheme_relief: float = 0.0
    total: float = 0.0
    delay_days: int = 0
    slab: str = ""
    scheme: str | None = None
    rule_versions: list[str] = field(default_factory=list)
    verified: bool = False
    blocked: str | None = None
    lines: list[str] = field(default_factory=list)

    @property
    def explanation(self) -> str:
        return "\n".join(self.lines)

    @property
    def label(self) -> str:
        return "" if self.verified else "Estimate — unverified"


def fmt_inr(v: float) -> str:
    """₹1,23,456 (Indian digit grouping)."""
    neg, v = v < 0, abs(round(v))
    s = str(int(v))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if neg else "") + "₹" + s


# ------------------------------------------------------------ validation
def _check_slabs(code: str, slabs: Any, key: str = "multiple") -> None:
    if not isinstance(slabs, list) or not slabs:
        raise ValueError(f"{code}: 'slabs' must be a non-empty list")
    last = 0
    for s in slabs:
        up = s.get("upto_days")
        if up is not None and up <= last:
            raise ValueError(f"{code}: slab bounds must increase ({up} after {last})")
        if key not in s and "small" not in s and "see" not in s:
            raise ValueError(f"{code}: slab missing '{key}'")
        last = up if up is not None else float("inf")
    if slabs[-1].get("upto_days") is not None:
        raise ValueError(f"{code}: last slab must be open-ended (upto_days: null)")


def validate_fee_tables(tables) -> None:
    codes = {t.code for t in tables}
    missing = REQUIRED_TABLES - codes
    if missing:
        raise ValueError(f"missing fee tables {sorted(missing)}")
    for t in tables:
        d = t.data
        if t.code in ("MULTIPLIER", "MULTIPLIER_S139", "HIGHER_MULTIPLIER"):
            _check_slabs(t.code, d.get("slabs"))
        elif t.code == "LLP_MATRIX":
            _check_slabs(t.code, d.get("slabs"))
            for k in ("annual_forms_beyond_360", "other_forms_beyond_360"):
                if k not in d:
                    raise ValueError(f"LLP_MATRIX: missing {k}")
        elif t.code in ("NORMAL_COMPANY", "NORMAL_LLP"):
            if not d.get("bands"):
                raise ValueError(f"{t.code}: missing bands")


# ------------------------------------------------------------- helpers
def _slab(slabs: list[dict], delay: int) -> dict:
    for s in slabs:
        if s.get("upto_days") is None or delay <= s["upto_days"]:
            return s
    raise AssertionError("unreachable: last slab is open-ended")  # pragma: no cover


def _slab_label(slabs: list[dict], s: dict) -> str:
    i = slabs.index(s)
    lo = slabs[i - 1]["upto_days"] + 1 if i else 1
    return f"{lo}–{s['upto_days']} days" if s.get("upto_days") is not None else f"more than {lo - 1} days"


def _band(bands: list[dict], amount: float) -> float:
    """bands: [{below: 100000, fee: 200}, ...] (exclusive) or [{upto: 100000, fee: 50}, ...]
    (inclusive); the last band has neither bound."""
    for b in bands:
        if "below" in b and b["below"] is not None and amount < b["below"]:
            return float(b["fee"])
        if "upto" in b and b["upto"] is not None and amount <= b["upto"]:
            return float(b["fee"])
        if b.get("below") is None and b.get("upto") is None:
            return float(b["fee"])
    raise AssertionError("unreachable")  # pragma: no cover


def normal_fee(entity: EntityIn, rulepack, on: date) -> tuple[float, str, bool]:
    if entity.is_llp:
        t = rulepack.fee_table("NORMAL_LLP", on)
        v = _band(t.data["bands"], entity.llp_contribution)
        return v, f"Normal fee {fmt_inr(v)} (LLP contribution {fmt_inr(entity.llp_contribution)}; {t.law})", t.verified
    t = rulepack.fee_table("NORMAL_COMPANY", on)
    if not entity.has_share_capital:
        v = float(t.data["no_share_capital"])
        return v, f"Normal fee {fmt_inr(v)} (company without share capital; {t.law})", t.verified
    v = _band(t.data["bands"], entity.nominal_capital)
    return v, f"Normal fee {fmt_inr(v)} (nominal capital {fmt_inr(entity.nominal_capital)}; {t.law})", t.verified


# --------------------------------------------------------------- main API
def compute_fee(rule_code: str, entity: EntityIn, due_date: date, filing_date: date,
                prior_defaults: int = 0, rulepack=None, *, period_key: str | None = None,
                charge_amount: float | None = None, is_small: bool | None = None) -> FeeBreakdown:
    """Fee payable if ``rule_code`` is filed on ``filing_date``.

    prior_defaults: belated filings of the same form within the last 365 days
    (triggers the higher additional fee for INC-22 / PAS-3).
    is_small: small company/OPC (CHARGE) or small LLP (LLP_MATRIX); for LLPs it
    defaults to the contribution-only test if not supplied.
    """
    if rulepack is None:
        from .rulepack import load
        rulepack = load()
    try:
        return _compute(rule_code, entity, due_date, filing_date, prior_defaults, rulepack, period_key,
                        charge_amount, is_small)
    except RulePackError as e:
        rule = rulepack.rule(rule_code)
        fb = FeeBreakdown(rule_code, rule.fee_regime, verified=False,
                          delay_days=max(0, (filing_date - due_date).days))
        fb.blocked = f"Fee cannot be computed: {e}. The rule pack has no fee table for that date."
        fb.lines.append(fb.blocked)
        return fb


def _compute(rule_code, entity, due_date, filing_date, prior_defaults, rulepack, period_key, charge_amount,
             is_small) -> FeeBreakdown:
    rule = rulepack.rule(rule_code)
    fb = FeeBreakdown(rule_code, rule.fee_regime, rule_versions=[f"{rulepack.version}:{rule.code}@{rule.content_hash}"])
    verified = [rule.verified]
    delay = max(0, (filing_date - due_date).days)
    fb.delay_days = delay
    fb.lines.append(f"{rule.form}: due {due_date:%d-%m-%Y}, filed {filing_date:%d-%m-%Y} — "
                    + (f"{delay} day(s) late" if delay else "on time"))

    regime = rule.fee_regime
    if regime == "NONE":
        fb.lines.append("No filing fee is prescribed for this item.")
        fb.verified = rule.verified
        return fb

    if regime == "FIXED_KYC":
        t = rulepack.fee_table("FIXED_KYC", filing_date)
        verified.append(t.verified)
        if rule.recurrence == "din_event":
            fb.normal = float(t.data["event"])
            fb.lines.append(f"Event-based DIR-3 KYC Web filing: {fmt_inr(fb.normal)} ({t.law})")
        elif delay:
            fb.additional = float(t.data["late"])
            fb.slab = "late / reactivation"
            fb.lines.append(f"Filed after the due date (or for DIN reactivation): {fmt_inr(fb.additional)} ({t.law})")
        else:
            fb.normal = float(t.data["on_time"])
            fb.lines.append(f"Filed on time: {fmt_inr(fb.normal)} ({t.law})")
        return _finish(fb, verified, rulepack, rule, entity, filing_date, period_key)

    fb.normal, line, v = normal_fee(entity, rulepack, filing_date)
    verified.append(v)
    fb.lines.append(line)

    if regime == "PER_DAY_100":
        t = rulepack.fee_table("PER_DAY_100", filing_date)
        verified.append(t.verified)
        fb.additional = float(t.data["per_day"]) * delay
        if delay:
            fb.slab = f"{delay} days × {fmt_inr(t.data['per_day'])}"
            fb.lines.append(f"Additional fee {fmt_inr(t.data['per_day'])} per day × {delay} days = "
                            f"{fmt_inr(fb.additional)} (no upper limit; {t.law})")

    elif regime == "MULTIPLIER":
        code = "MULTIPLIER"
        if rule.code in HIGHER_FORMS and prior_defaults >= 1:
            code = "HIGHER_MULTIPLIER"
        elif rule.fee_slab == "S139":
            code = "MULTIPLIER_S139"
        try:
            t = rulepack.fee_table(code, filing_date)
        except RulePackError:
            # e.g. s.139 slab or higher fee not yet in force on that date -> general table
            code = "MULTIPLIER"
            t = rulepack.fee_table(code, filing_date)
        verified.append(t.verified)
        if delay:
            s = _slab(t.data["slabs"], delay)
            fb.additional = s["multiple"] * fb.normal
            fb.slab = f"{_slab_label(t.data['slabs'], s)}: {s['multiple']}×"
            extra = " (higher additional fee: repeat default within 365 days)" if code == "HIGHER_MULTIPLIER" else ""
            fb.lines.append(f"Additional fee {s['multiple']} × {fmt_inr(fb.normal)} = {fmt_inr(fb.additional)} "
                            f"for delay of {fb.slab.split(':')[0]}{extra} ({t.law})")

    elif regime == "CHARGE":
        t = rulepack.fee_table("CHARGE", filing_date)
        verified.append(t.verified)
        small = bool(is_small) or entity.entity_type == "OPC"
        cat = t.data["small_or_opc" if small else "other"]
        if delay > t.data["max_delay_days"]:
            fb.blocked = ("Beyond the period the Registrar can allow under s.77 — registration needs condonation "
                          "by the Central Government (Regional Director) under s.87. No fee computed.")
            fb.lines.append(fb.blocked)
        elif delay:
            fb.additional = cat["multiple"] * fb.normal
            fb.slab = f"{'small/OPC' if small else 'other'}: {cat['multiple']}×"
            fb.lines.append(f"Additional fee {cat['multiple']} × {fmt_inr(fb.normal)} = {fmt_inr(fb.additional)} ({t.law})")
            if delay > t.data["additional_only_upto_days"]:
                if charge_amount is None:
                    fb.blocked = "Ad valorem fee needs the amount secured by the charge."
                    fb.lines.append(fb.blocked)
                else:
                    adv = min(charge_amount * cat["ad_valorem_pct"] / 100, cat["ad_valorem_cap"])
                    fb.additional += adv
                    fb.slab += f" + ad valorem {cat['ad_valorem_pct']}%"
                    fb.lines.append(f"Ad valorem fee {cat['ad_valorem_pct']}% of {fmt_inr(charge_amount)}, capped at "
                                    f"{fmt_inr(cat['ad_valorem_cap'])} = {fmt_inr(adv)}")

    elif regime == "LLP_MATRIX":
        t = rulepack.fee_table("LLP_MATRIX", filing_date)
        verified.append(t.verified)
        if is_small is None:
            is_small = entity.llp_contribution <= 2_500_000
        col = "small" if is_small else "other"
        if delay:
            slabs = t.data["slabs"]
            s = _slab(slabs, delay)
            if s.get("upto_days") is None:
                key = "annual_forms_beyond_360" if rule.fee_slab == "LLP_ANNUAL" else "other_forms_beyond_360"
                b = t.data[key][col]
                fb.additional = b["multiple"] * fb.normal
                per_day = b.get("per_day", 0) * (delay - slabs[-2]["upto_days"])
                fb.additional += per_day
                fb.slab = f"more than {slabs[-2]['upto_days']} days: {b['multiple']}×" + (
                    f" + {fmt_inr(b['per_day'])}/day" if b.get("per_day") else "")
                fb.lines.append(f"Additional fee {b['multiple']} × {fmt_inr(fb.normal)}"
                                + (f" + {fmt_inr(b['per_day'])} × {delay - slabs[-2]['upto_days']} days beyond "
                                   f"{slabs[-2]['upto_days']}" if b.get("per_day") else "")
                                + f" = {fmt_inr(fb.additional)} ({'small LLP' if is_small else 'other LLP'}; {t.law})")
            else:
                m = s[col]
                fb.additional = m * fb.normal
                fb.slab = f"{_slab_label(slabs, s)}: {m}×"
                fb.lines.append(f"Additional fee {m} × {fmt_inr(fb.normal)} = {fmt_inr(fb.additional)} "
                                f"({'small LLP' if is_small else 'other LLP'}, delay {_slab_label(slabs, s)}; {t.law})")

    return _finish(fb, verified, rulepack, rule, entity, filing_date, period_key)


def _finish(fb: FeeBreakdown, verified: list[bool], rulepack, rule, entity: EntityIn,
            filing_date: date, period_key: str | None) -> FeeBreakdown:
    best, best_relief = None, 0.0
    if fb.additional > 0:
        kind = "LLP" if entity.is_llp else "COMPANY"
        for s in rulepack.schemes:
            if s.kind == "DUE_DATE_EXTENSION" or rule.code not in s.rule_codes or kind not in s.applies_to:
                continue
            if not (s.window_from <= filing_date <= s.window_to):
                continue
            if s.period_keys and period_key not in s.period_keys:
                continue
            if s.respects_ccfs_exclusion and entity.ccfs_excluded:
                fb.lines.append(f"{s.code} not available: entity is in an excluded category ({s.circular_ref})")
                continue
            relief = fb.additional * (1 - s.additional_fee_factor)
            if relief > best_relief:
                best, best_relief = s, relief
    if best is not None:
        fb.scheme_relief = round(best_relief, 2)
        fb.scheme = best.code
        verified.append(best.verified)
        pct = round(best.additional_fee_factor * 100)
        fb.lines.append(f"{best.code} ({best.circular_ref}): pay {pct}% of the additional fee — relief "
                        f"{fmt_inr(fb.scheme_relief)}")
        fb.rule_versions.append(f"scheme:{best.code}")
    fb.total = round(fb.normal + fb.additional - fb.scheme_relief, 2)
    fb.verified = all(verified)
    fb.lines.append(f"Total {fmt_inr(fb.total)}" + ("" if fb.verified else " — Estimate — unverified"))
    return fb
