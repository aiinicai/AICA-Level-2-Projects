"""Currency handling: everything the tool outputs (P&L, balance sheet, computation) is in UAE dirhams.

Conversion follows the hierarchy in FTA Decision No. 13 of 2023 (see config/rules.json FX-01):
spot rate on transaction date > CBUAE monthly average > CBUAE annual average, applied consistently,
with a record of the method, reason and rates used.

Rates are NEVER fetched from the internet by this module. They are entered by the user (or loaded
from a rate file), except the USD peg which comes from config/rules.json.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .mapping import MappedAccount, fs_lines
from .models import GeneralLedger, load_json, MATCH_TOL, ZERO_TOL

METHODS = {
    "peg": "Fixed official peg rate (USD only)",
    "manual": "Rates entered by user: one P&L rate (e.g. CBUAE annual average), one closing rate",
    "annual": "CBUAE annual average rate for P&L; closing rate for balance sheet",
    "monthly": "CBUAE monthly average rates applied to GL transactions (needs GL)",
    "spot": "CBUAE spot rate on each transaction date (needs GL)",
}


@dataclass
class FXSettings:
    tb_currency: str = ""                              # deliberately empty until the user chooses (AED is a choice like any other)
    functional_currency: str = ""
    method: str = "peg"
    rates: dict = field(default_factory=dict)          # ccy -> {"pl":..., "closing":..., "equity":...}
    monthly_rates: dict = field(default_factory=dict)  # ccy -> {"YYYY-MM": rate}
    spot_rates: dict = field(default_factory=dict)     # ccy -> {"YYYY-MM-DD": rate}
    rate_source: str = ""                              # e.g. "CBUAE published rates, downloaded 11 Oct 2026"
    method_reason: str = ""                            # reason for choosing the method (Decision 13 record)
    translation_diff_approved: bool = False
    period_start: str = ""
    period_end: str = ""

    @property
    def is_aed(self) -> bool:
        return self.tb_currency.upper() == "AED"


def peg_rates() -> dict:
    return load_json("rules.json")["params"]["peg_rates"]


def default_settings(ccy: str, period_start: str = "", period_end: str = "") -> FXSettings:
    ccy = (ccy or "AED").upper().strip()
    fx = FXSettings(tb_currency=ccy, functional_currency=ccy, period_start=period_start, period_end=period_end)
    if ccy == "AED":
        fx.method = "peg"
        fx.rates = {"AED": {"pl": 1.0, "closing": 1.0, "equity": 1.0}}
    elif ccy in peg_rates():
        r = peg_rates()[ccy]
        fx.method = "peg"
        fx.rates = {ccy: {"pl": r, "closing": r, "equity": r}}
        fx.rate_source = f"Official AED/{ccy} peg of {r} (config/rules.json)"
        fx.method_reason = f"{ccy} is pegged to the dirham; a single fixed rate gives the same result as spot/average conversion."
    else:
        fx.method = "manual"
        fx.rates = {ccy: {"pl": 0.0, "closing": 0.0, "equity": 0.0}}
    return fx


def validate_settings(fx: FXSettings, gl: Optional[GeneralLedger] = None) -> list:
    """Return a list of (severity, message). Severity: ERROR blocks processing; WARN needs attention."""
    out = []
    ccy = fx.tb_currency.upper()
    if not ccy or len(ccy) != 3 or not ccy.isalpha():
        return [("ERROR", "Enter the TB currency as a three-letter ISO code, e.g. USD, EUR, AED.")]
    if ccy == "AED":
        return out
    r = fx.rates.get(ccy, {})
    if fx.method == "peg":
        if ccy not in peg_rates():
            out.append(("ERROR", f"{ccy} is not an official peg currency in the configuration. Choose another method and enter rates."))
        elif any(abs(r.get(k, 0) - peg_rates()[ccy]) > 1e-9 for k in ("pl", "closing", "equity")):
            out.append(("WARN", f"The rate differs from the configured official {ccy} peg ({peg_rates()[ccy]}). Record why."))
    else:
        for k, label in (("pl", "P&L rate"), ("closing", "closing (balance sheet) rate")):
            if not r.get(k) or r[k] <= 0:
                out.append(("ERROR", f"Enter a positive {label} for {ccy}."))
        if r.get("equity", 0) <= 0:
            out.append(("WARN", f"No historical equity rate for {ccy}: the closing rate will be used for equity, which may overstate the translation difference."))
    if fx.method in ("monthly", "spot"):
        if gl is None or not gl.lines:
            out.append(("ERROR", f"Method '{fx.method}' needs a General Ledger. Upload the GL or choose the annual-average method."))
        elif fx.method == "monthly" and not fx.monthly_rates.get(ccy):
            out.append(("ERROR", "Enter or upload monthly average rates for each month of the period."))
        elif fx.method == "spot" and not (fx.spot_rates.get(ccy) or fx.monthly_rates.get(ccy)):
            out.append(("ERROR", "Enter or upload daily spot rates (or at least monthly rates as a fallback)."))
    if not fx.rate_source:
        out.append(("WARN", "State the rate source (e.g. CBUAE published rates) - Decision No. 13 requires a record of the rates used."))
    if not fx.method_reason:
        out.append(("WARN", "State the reason for the conversion method - Decision No. 13 requires the rationale to be recorded."))
    return out


@dataclass
class AEDAccount:
    mapped: MappedAccount
    net_src: float
    net_aed: float
    debit_aed: float
    credit_aed: float
    rate: float
    rate_basis: str
    flags: list = field(default_factory=list)

    @property
    def account(self):
        return self.mapped.account

    @property
    def line(self) -> str:
        return self.mapped.line


@dataclass
class TranslationResult:
    accounts: list
    translation_diff: float                 # amount to add to equity (signed, credit negative as in net convention)
    diff_applicable: bool
    rate_table: list                        # rows for the FX sheet
    method_record: dict
    flags: list = field(default_factory=list)
    source_balanced: bool = True

    @property
    def total_net_aed(self) -> float:
        return sum(a.net_aed for a in self.accounts)


def _bucket(m: MappedAccount) -> str:
    lines = fs_lines()
    ln = lines[m.line]
    if ln["statement"] == "PL":
        return "pl"
    if ln["section"] == "EQUITY":
        return "equity"
    return "closing"


def _gl_index(gl: GeneralLedger):
    idx = {}
    for ln in gl.lines:
        idx.setdefault(ln.account_code or ln.account_name.strip().lower(), []).append(ln)
    return idx


def translate_tb(mapped: list, fx: FXSettings, gl: Optional[GeneralLedger] = None) -> TranslationResult:
    ccy = fx.tb_currency.upper()
    out, flags, rate_rows = [], [], []
    src_total = sum(m.account.net for m in mapped)
    source_balanced = abs(src_total) <= MATCH_TOL
    record = {"currency": ccy, "method": fx.method, "method_description": METHODS.get(fx.method, fx.method),
              "reason": fx.method_reason, "rate_source": fx.rate_source, "decision": "FTA Decision No. 13 of 2023, Art. 2",
              "gl_used": False}
    if ccy == "AED":
        for m in mapped:
            n = m.account.net
            out.append(AEDAccount(m, n, n, m.account.debit, m.account.credit, 1.0, "AED - no conversion"))
        record["method"] = "none"
        record["method_description"] = "TB is already in AED"
        return TranslationResult(out, 0.0, False, [], record, flags, source_balanced)

    r = fx.rates.get(ccy, {})
    pl_rate = r.get("pl") or 0.0
    cl_rate = r.get("closing") or pl_rate
    eq_rate = r.get("equity") or cl_rate
    if cl_rate <= 0 or pl_rate <= 0:
        raise ValueError(f"Missing rates for {ccy}. Enter them in the currency step.")
    rate_rows.append({"purpose": "Profit and loss - " + ("fixed peg" if fx.method == "peg" else "annual average / fallback"),
                      "currency": ccy, "rate": pl_rate, "basis": fx.rate_source or fx.method})
    rate_rows.append({"purpose": "Balance sheet - closing rate", "currency": ccy, "rate": cl_rate, "basis": fx.rate_source or fx.method})
    rate_rows.append({"purpose": "Equity - historical rate", "currency": ccy, "rate": eq_rate, "basis": fx.rate_source or fx.method})

    gl_idx = _gl_index(gl) if (gl and fx.method in ("monthly", "spot")) else {}
    months_used = {}

    def gl_rate_for(ln):
        d = ln.date
        if not d:
            return None, None
        if fx.method == "spot":
            rr = fx.spot_rates.get(ccy, {}).get(d)
            if rr:
                return rr, "spot"
        mr = fx.monthly_rates.get(ccy, {}).get(d[:7])
        if mr:
            return mr, "monthly"
        return None, None

    for m in mapped:
        a = m.account
        b = _bucket(m)
        rate = {"pl": pl_rate, "closing": cl_rate, "equity": eq_rate}[b]
        basis = {"pl": "P&L rate", "closing": "Closing rate", "equity": "Historical equity rate"}[b]
        net_aed = a.net * rate
        acc_flags = []
        if b == "pl" and gl_idx:
            lines = [l for l in gl_idx.get(a.code or a.name.strip().lower(), [])
                     if (not fx.period_start or (l.date and l.date >= fx.period_start))
                     and (not fx.period_end or (l.date and l.date <= fx.period_end))]
            if lines and abs(sum(l.net for l in lines) - a.net) <= MATCH_TOL:
                total, ok, kinds = 0.0, True, set()
                for l in lines:
                    rr, kind = gl_rate_for(l)
                    if rr is None:
                        ok = False
                        break
                    total += l.net * rr
                    kinds.add(kind)
                    months_used.setdefault(l.date[:7], rr)
                if ok:
                    net_aed = total
                    rate = net_aed / a.net if a.net else pl_rate
                    basis = "GL transactions - " + ("spot rate per date" if "spot" in kinds and kinds == {"spot"} else "monthly average" if kinds == {"monthly"} else "spot/monthly mix")
                    record["gl_used"] = True
                else:
                    acc_flags.append("GL line(s) without a usable rate - single P&L rate used for this account.")
            elif lines:
                acc_flags.append("GL movement does not agree to the TB for this account - single P&L rate used.")
            else:
                acc_flags.append("No GL lines for this account - single P&L rate used.")
        if "GL" in basis:
            d_aed, c_aed = max(net_aed, 0.0), max(-net_aed, 0.0)
        else:
            d_aed, c_aed = a.debit * rate, a.credit * rate
        out.append(AEDAccount(m, a.net, net_aed, d_aed, c_aed, rate, basis, acc_flags))

    if months_used:
        for mth in sorted(months_used):
            rate_rows.append({"purpose": f"GL conversion - {mth}", "currency": ccy, "rate": months_used[mth],
                              "basis": "CBUAE " + ("spot/monthly" if fx.method == "spot" else "monthly average")})
    total_aed = sum(x.net_aed for x in out)
    diff, diff_applicable = 0.0, False
    if source_balanced:
        diff = -total_aed
        diff_applicable = abs(diff) > ZERO_TOL
        if diff_applicable:
            flags.append(f"Translating the P&L, balance sheet and equity at different rates leaves a difference of AED {diff:,.2f}. "
                         "It is shown as a derived 'Currency translation difference' in equity and must be approved - it is not a figure from the TB.")
    else:
        flags.append("The source TB does not balance, so no translation difference was derived.")
    return TranslationResult(out, diff, diff_applicable, rate_rows, record, flags, source_balanced)
