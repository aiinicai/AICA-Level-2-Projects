"""Numbers behind the Day Book dashboard. Plain functions on the parsed Day Book and the findings, so they can be tested
without a browser; the charts are drawn in ui/charts.py."""
from __future__ import annotations

import pandas as pd

from . import narration
from .narration import _party
from .rules import summarise_vouchers

SEVERITY_ORDER = ["High", "Medium", "Low"]


def family(rule: str, source: str) -> str:
    """Which kind of test raised a finding."""
    if source == "AI":
        return "AI review"
    if rule.startswith(narration.R_NARR_PREFIX):
        return "Narration"
    if rule in (narration.R_NEAR, narration.R_REPEAT, narration.R_BENFORD):
        return "Amount pattern"
    return "Accounting rule"


def daybook_dashboard(df: pd.DataFrame, findings: pd.DataFrame) -> dict:
    """KPIs and the tables the charts need. `findings` is the combined rule and AI findings (it may be empty)."""
    v = summarise_vouchers(df)
    v["date"] = pd.to_datetime(v["date"], errors="coerce")
    v["party"] = [_party(r) for r in v.to_dict("records")]
    f = findings.copy()
    if len(f):
        f["date"] = pd.to_datetime(f["date"], errors="coerce")
    f["family"] = [family(r, s) for r, s in zip(f["rule"], f["source"])] if len(f) else []
    flagged = set(f["voucher_id"]) if len(f) else set()
    v["flagged"] = v["voucher_id"].isin(flagged)
    high = set(f.loc[f["severity"] == "High", "voucher_id"]) if len(f) else set()
    v["high"] = v["voucher_id"].isin(high)

    real = v[v["vch_type"].str.lower() != "contra"]           # a contra is a transfer between our own accounts
    dated = v[v["date"].notna()]
    out = {
        "kpis": {
            "vouchers": int(len(v)),
            "value": float(real["total"].sum()),
            "flagged_vouchers": int(v["flagged"].sum()),
            "flagged_share": float(v["flagged"].mean()) if len(v) else 0.0,
            "flagged_value": float(v.loc[v["flagged"], "total"].sum()),
            "high_vouchers": int(v["high"].sum()),
            "findings": int(len(f)),
            "undated": int(v["date"].isna().sum()),
        },
        "by_type": (v.groupby("vch_type").agg(vouchers=("voucher_id", "size"), value=("total", "sum"), flagged=("flagged", "sum"))
                    .reset_index().sort_values("value", ascending=False)),
        "top_parties": (real[real["party"] != ""].groupby("party").agg(value=("total", "sum"), vouchers=("voucher_id", "size"),
                                                                        flagged=("flagged", "sum"))
                        .reset_index().sort_values("value", ascending=False).head(10)),
        "severity_by_family": (f.groupby(["family", "severity"]).size().rename("findings").reset_index()
                               if len(f) else pd.DataFrame(columns=["family", "severity", "findings"])),
        "top_rules": (f.groupby(["rule", "severity"]).size().rename("findings").reset_index()
                      .sort_values("findings", ascending=False).head(12) if len(f) else pd.DataFrame(columns=["rule", "severity", "findings"])),
        "monthly": None,
        "findings_by_month": None,
    }
    if len(dated):
        month = dated["date"].dt.to_period("M").dt.to_timestamp()
        m = dated.assign(month=month).groupby("month").agg(vouchers=("voucher_id", "size"), value=("total", "sum"),
                                                          flagged=("flagged", "sum")).reset_index()
        out["monthly"] = m
        fd = f[f["date"].notna()] if len(f) else f
        if len(fd):
            out["findings_by_month"] = (fd.assign(month=fd["date"].dt.to_period("M").dt.to_timestamp())
                                        .groupby(["month", "severity"]).size().rename("findings").reset_index())
    return out
