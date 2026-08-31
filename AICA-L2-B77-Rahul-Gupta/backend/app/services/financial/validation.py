"""Deterministic accounting validation checks."""
from __future__ import annotations

from typing import Any

TOLERANCE_PCT = 0.01  # 1% rounding tolerance
TOLERANCE_ABS = 50_000.0  # ₹0.005 Cr absolute floor


def _close(a: float | None, b: float | None) -> bool | None:
    if a is None or b is None:
        return None
    tol = max(abs(b) * TOLERANCE_PCT, TOLERANCE_ABS)
    return abs(a - b) <= tol


def validate_period(data: dict, period: str) -> list[dict[str, Any]]:
    """Run accounting checks for one period; returns list of check results."""
    d = data.get(period, {})
    checks: list[dict[str, Any]] = []

    def add(code: str, name: str, ok: bool | None, detail: str):
        checks.append({
            "code": code, "name": name, "period": period,
            "status": "pass" if ok else ("skipped" if ok is None else "fail"),
            "detail": detail,
        })

    # Balance sheet equation
    ta = d.get("total_assets")
    nw = d.get("net_worth")
    tl = d.get("total_liabilities")
    if ta is not None and nw is not None and tl is not None:
        ok = _close(ta, nw + tl)
        add("BS_EQUATION", "Total Assets ≈ Equity + Liabilities", ok,
            f"Assets {ta:,.0f} vs Equity+Liabilities {nw + tl:,.0f}")
    else:
        add("BS_EQUATION", "Total Assets ≈ Equity + Liabilities", None, "Insufficient data")

    # Net worth composition
    sc, rs = d.get("share_capital"), d.get("reserves")
    if sc is not None and rs is not None and nw is not None:
        add("NW_COMPOSITION", "Net Worth ≈ Share Capital + Reserves", _close(nw, sc + rs),
            f"Net worth {nw:,.0f} vs components {sc + rs:,.0f}")

    # PBT - Tax = PAT
    pbt, tax, pat = d.get("pbt"), d.get("tax"), d.get("pat")
    if pbt is not None and tax is not None and pat is not None:
        add("PAT_CHECK", "PBT − Tax ≈ PAT", _close(pbt - tax, pat),
            f"PBT−Tax {pbt - tax:,.0f} vs PAT {pat:,.0f}")
    else:
        add("PAT_CHECK", "PBT − Tax ≈ PAT", None, "Insufficient data")

    # EBITDA bridge: EBITDA - Dep = EBIT
    ebitda, dep, ebit = d.get("ebitda"), d.get("depreciation"), d.get("ebit")
    if ebitda is not None and dep is not None and ebit is not None:
        add("EBIT_BRIDGE", "EBITDA − Depreciation ≈ EBIT", _close(ebitda - dep, ebit),
            f"EBITDA−Dep {ebitda - dep:,.0f} vs EBIT {ebit:,.0f}")

    # Cash flow: opening + CFO + CFI + CFF = closing
    oc, cfo, cfi, cff, cc = (d.get("opening_cash"), d.get("cfo"), d.get("cfi"),
                             d.get("cff"), d.get("closing_cash"))
    if None not in (oc, cfo, cfi, cff, cc):
        add("CASH_BRIDGE", "Opening Cash + Net Movement ≈ Closing Cash",
            _close(oc + cfo + cfi + cff, cc),
            f"Derived closing {oc + cfo + cfi + cff:,.0f} vs stated {cc:,.0f}")
    else:
        add("CASH_BRIDGE", "Opening Cash + Net Movement ≈ Closing Cash", None, "Insufficient data")

    return checks


def validate_comparatives(data: dict, periods: list[str]) -> list[dict[str, Any]]:
    """Compare closing cash of prior period against opening cash of next period."""
    checks: list[dict[str, Any]] = []
    for i in range(1, len(periods)):
        prev_close = data.get(periods[i - 1], {}).get("closing_cash")
        curr_open = data.get(periods[i], {}).get("opening_cash")
        if prev_close is not None and curr_open is not None:
            ok = _close(prev_close, curr_open)
            checks.append({
                "code": "COMPARATIVE_CASH",
                "name": f"{periods[i-1]} closing cash carries to {periods[i]} opening",
                "period": periods[i],
                "status": "pass" if ok else "fail",
                "detail": f"{prev_close:,.0f} vs {curr_open:,.0f}",
            })
    return checks


def validate_all(data: dict, periods: list[str]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for p in periods:
        checks.extend(validate_period(data, p))
    checks.extend(validate_comparatives(data, periods))
    failed = [c for c in checks if c["status"] == "fail"]
    return {
        "checks": checks,
        "passed": len([c for c in checks if c["status"] == "pass"]),
        "failed": len(failed),
        "skipped": len([c for c in checks if c["status"] == "skipped"]),
        "ok": len(failed) == 0,
    }
