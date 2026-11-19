"""TDS/TCS defaults. EDITABLE per company in Settings: verify against the Income-tax Act 2025 (s.393
table) and current Rules before go-live. Legacy 1961-Act codes are kept as familiar labels."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .history import vouchers as _hv
from ..db.models import Posting, VoucherHistory

DEFAULT_SECTIONS = {
    "194C": {"label": "Contractors", "rate_company": 2, "rate_individual": 1,
             "single_limit": 30000, "annual_limit": 100000},
    "194J-P": {"label": "Professional fees", "rate_company": 10, "rate_individual": 10,
               "single_limit": 50000, "annual_limit": 50000},
    "194J-T": {"label": "Technical services / call centre", "rate_company": 2, "rate_individual": 2,
               "single_limit": 50000, "annual_limit": 50000},
    "194I-B": {"label": "Rent - land, building, furniture", "rate_company": 10, "rate_individual": 10,
               "single_limit": 50000, "annual_limit": 0, "monthly": True},
    "194I-P": {"label": "Rent - plant & machinery", "rate_company": 2, "rate_individual": 2,
               "single_limit": 50000, "annual_limit": 0, "monthly": True},
    "194H": {"label": "Commission / brokerage", "rate_company": 2, "rate_individual": 2,
             "single_limit": 20000, "annual_limit": 20000},
    "194Q": {"label": "Purchase of goods", "rate_company": 0.1, "rate_individual": 0.1,
             "single_limit": 0, "annual_limit": 5000000, "excess_only": True},
}


def fy_bounds(d: date) -> tuple[str, str]:
    start = date(d.year if d.month >= 4 else d.year - 1, 4, 1)
    return start.strftime("%Y%m%d"), date(start.year + 1, 3, 31).strftime("%Y%m%d")


def paid_this_fy(session: Session, company_id: str, party_ledger: str, on: date) -> Decimal:
    """Credits to the party in Tally history this FY (taxable base approximated by gross)."""
    lo, hi = fy_bounds(on)
    total = Decimal(0)
    for v in _hv(session, company_id, lo, hi):
        for e in v.entries or []:
            if e["ledger"] == party_ledger and not e["dr"] and v.voucher_type.lower().find("payment") < 0:
                total += Decimal(e["amount"])
    return total


def compute(section: str, base: Decimal, party_is_company: bool, prior_fy: Decimal,
            sections: dict | None = None) -> tuple[Decimal, str]:
    """Returns (tds_amount, explanation). base = taxable value of this bill (excl. GST)."""
    cfg = (sections or DEFAULT_SECTIONS).get(section)
    if not cfg:
        return Decimal(0), f"Unknown section {section}"
    rate = Decimal(str(cfg["rate_company"] if party_is_company else cfg["rate_individual"]))
    single, annual = Decimal(str(cfg.get("single_limit", 0))), Decimal(str(cfg.get("annual_limit", 0)))
    if cfg.get("excess_only"):
        taxable = max(Decimal(0), prior_fy + base - max(annual, prior_fy))
        if taxable <= 0:
            return Decimal(0), f"{section}: below Rs {annual:,.0f} aggregate"
        return (taxable * rate / 100).quantize(Decimal("1")), f"{section} @ {rate}% on excess {taxable}"
    crosses = (single and base > single) or (annual and prior_fy + base > annual) or (cfg.get("monthly") and base > single)
    if not crosses:
        return Decimal(0), f"{section}: below threshold (bill {base}, FY so far {prior_fy})"
    return (base * rate / 100).quantize(Decimal("1")), f"{section} @ {rate}% on {base}"


def is_company_pan(pan: str) -> bool:
    """194C: 1% for individual/HUF (4th PAN char P/H), 2% for everyone else."""
    return len(pan) == 10 and pan[3] not in "PH"


STD_RATES = [Decimal(x) for x in ("0.1", "1", "2", "5", "10", "20")]


def history_tds(session: Session, company_id: str, party_ledger: str, ledgers: dict) -> dict | None:
    """How TDS was deducted for this party in past Tally entries: the TDS ledger used and the rate on the
    expense value. Returns {'ledger','rate','count','last'} for the most common pattern, else None."""
    if not party_ledger:
        return None
    exp_groups = ("Direct Expenses", "Indirect Expenses", "Purchase Accounts", "Fixed Assets")
    from collections import Counter
    seen: Counter = Counter()
    last: dict = {}
    from .history import index as _hindex
    for v in _hindex(session, company_id).credited.get(party_ledger, []):
        ents = v.entries or []
        tds = [e for e in ents if not e["dr"] and e["ledger"] != party_ledger and "tds" in e["ledger"].lower()]
        if not tds:
            continue
        base = sum((Decimal(e["amount"]) for e in ents if e["dr"] and
                    ledgers.get(e["ledger"], {}).get("_primary") in exp_groups), Decimal(0))
        if base <= 0:
            continue
        rate = Decimal(tds[0]["amount"]) * 100 / base
        std = min(STD_RATES, key=lambda r: abs(r - rate))
        if abs(std - rate) > max(Decimal("0.15"), std * Decimal("0.1")):
            continue
        key = (tds[0]["ledger"], std)
        seen[key] += 1
        last[key] = max(last.get(key, ""), v.date)
    if not seen:
        return None
    (ledger, rate), n = seen.most_common(1)[0]
    return {"ledger": ledger, "rate": rate, "count": n, "last": last[(ledger, rate)]}
