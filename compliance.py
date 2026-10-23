"""
Filing status & compliance (rules only), built with pandas from two portal APIs:
  * rolestatus   -> per period: return type, portal due date, FIL / NF
  * efiledReturns -> per FY: return type, tax period, ARN, date of filing
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from portal_config import MONTHS, prd_label
from reports import parse_dmy

FILING_RETURNS = {"GSTR1", "GSTR3B", "GSTR4", "CMP08", "GSTR7", "GSTR8", "GSTR5", "GSTR6", "GSTR9", "GSTR9C"}
PRETTY = {"GSTR1": "GSTR-1", "GSTR3B": "GSTR-3B", "GSTR9": "GSTR-9", "GSTR9C": "GSTR-9C", "CMP08": "CMP-08",
          "GSTR4": "GSTR-4", "GSTR7": "GSTR-7", "GSTR8": "GSTR-8", "GSTR5": "GSTR-5", "GSTR6": "GSTR-6"}
STATES_22 = {"22", "23", "24", "25", "26", "27", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "97"}
QTR_END = {"Apr-Jun": "June", "Jul-Sep": "September", "Oct-Dec": "December", "Jan-Mar": "March"}


def statutory_due(form, period, qrmp=False, gstin=""):
    """period 'YYYY-MM' or 'FYyyyy-yy'."""
    if form in ("GSTR-9", "GSTR-9C"):
        return date(int(period[2:6]) + 1, 12, 31)
    y, m = map(int, period.split("-"))
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    if form == "GSTR-1":
        return date(y, m, 13 if qrmp else 11)
    if form == "GSTR-3B":
        return date(y, m, (22 if gstin[:2] in STATES_22 else 24) if qrmp else 20)
    return None


def _period_from_taxp(taxp: str, fy: str) -> str | None:
    t = str(taxp).strip()
    for k, v in QTR_END.items():
        if k.lower().replace("-", "") in t.lower().replace("-", "").replace(" ", ""):
            t = v
    for i, m in enumerate(MONTHS):
        if t.lower().startswith(m.lower()[:3]):
            mm = (i + 3) % 12 + 1
            yyyy = int(fy[:4]) + (0 if i < 9 else 1)
            return f"{yyyy}-{mm:02d}"
    if "annual" in t.lower() or t == fy:
        return f"FY{fy}"
    return None


def build_status(fy: str, rolestatus: dict[str, dict], efiled: list[dict], gstin: str = "",
                 aato: float | None = None, nil_flags: dict | None = None, today: date | None = None) -> pd.DataFrame:
    today = today or date.today()
    nil_flags = nil_flags or {}

    # --- what the portal says was due, period by period
    due_rows, qrmp = [], False
    for prd, js in rolestatus.items():
        d = (js or {}).get("data") or {}
        if d.get("userPref") == "Q":
            qrmp = True
        for grp in d.get("user", []) or []:
            for r in grp.get("returns", []) or []:
                ty = r.get("return_ty")
                if ty not in FILING_RETURNS:
                    continue
                due_rows.append({"Return": PRETTY.get(ty, ty), "Period": prd_label(prd),
                                 "Portal due date": parse_dmy(r.get("due_dt")),
                                 "Portal status": {"FIL": "Filed", "NF": "Not filed"}.get(r.get("status"), r.get("status"))})
    due = pd.DataFrame(due_rows, columns=["Return", "Period", "Portal due date", "Portal status"]).drop_duplicates(["Return", "Period"])

    # --- what was actually filed (ARN, date)
    ef_rows = []
    for e in efiled or []:
        per = _period_from_taxp(e.get("taxp", ""), e.get("fy", fy))
        if not per:
            continue
        ef_rows.append({"Return": PRETTY.get(e.get("rtntype"), e.get("rtntype")), "Period": per,
                        "Filed on": parse_dmy(e.get("dof")), "ARN": e.get("arn", ""),
                        "Mode": e.get("mof", ""), "Filed by": e.get("filedBy", "")})
    ef = pd.DataFrame(ef_rows, columns=["Return", "Period", "Filed on", "ARN", "Mode", "Filed by"])
    ef = ef.sort_values("Filed on").drop_duplicates(["Return", "Period"], keep="first")

    df = due.merge(ef, on=["Return", "Period"], how="outer")
    if df.empty:
        return df
    df["Due date"] = df.apply(lambda r: r["Portal due date"] if pd.notna(r["Portal due date"]) and r["Portal due date"]
                              else statutory_due(r["Return"], r["Period"], qrmp, gstin), axis=1)

    def classify(r):
        due_d, filed = r["Due date"], r["Filed on"]
        is_filed = (pd.notna(filed) and filed) or r.get("Portal status") == "Filed"
        if is_filed:
            if pd.notna(filed) and filed and due_d and filed > due_d:
                return "Filed late", (filed - due_d).days
            return "Filed on time", 0
        if due_d and today > due_d:
            return "Not filed - overdue", (today - due_d).days
        return "Not yet due", 0

    res = df.apply(classify, axis=1, result_type="expand")
    df["Status"], df["Days late"] = res[0], res[1].astype(int)

    cap = 10000 if (aato or 0) > 5e7 else (5000 if (aato or 0) > 1.5e7 else 2000)

    def fee(r):
        d = r["Days late"]
        if d <= 0:
            return 0.0
        if r["Return"] in ("GSTR-1", "GSTR-3B"):
            nil = nil_flags.get((r["Return"], r["Period"]), False)
            return float(min(d * 20, 500) if nil else min(d * 50, cap))
        if r["Return"] == "GSTR-9":
            t = aato or 0
            per_day, pct = (50, 0.0004) if t <= 5e7 else ((100, 0.0004) if t <= 2e8 else (200, 0.005))
            return float(min(d * per_day, t * pct) if t else d * per_day)
        return 0.0

    df["Est. late fee"] = df.apply(fee, axis=1)
    cols = ["Return", "Period", "Due date", "Filed on", "Days late", "Status", "Est. late fee", "ARN", "Mode", "Filed by",
            "Portal status"]
    out = df[cols].sort_values(["Period", "Return"]).reset_index(drop=True)
    for c in ("ARN", "Mode", "Filed by", "Portal status"):
        out[c] = out[c].fillna("")
    return out


def summary(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"due": 0, "on_time": 0, "late": 0, "pending": 0, "score": 0, "late_fee": 0}
    d = df[df["Status"] != "Not yet due"]
    on, late, pend = (d["Status"] == "Filed on time").sum(), (d["Status"] == "Filed late").sum(), \
        (d["Status"] == "Not filed - overdue").sum()
    return {"due": int(len(d)), "on_time": int(on), "late": int(late), "pending": int(pend),
            "score": int(round(100 * on / len(d))) if len(d) else 100, "late_fee": float(df["Est. late fee"].sum())}


def month_grid(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    sym = {"Filed on time": "OK", "Filed late": "LATE", "Not filed - overdue": "NOT FILED", "Not yet due": "-"}
    m = df[~df["Period"].str.startswith("FY")].copy()
    m["Cell"] = m.apply(lambda r: sym.get(r["Status"], r["Status"]) +
                        (f" {r['Days late']}d" if r["Status"] in ("Filed late", "Not filed - overdue") else ""), axis=1)
    return m.pivot_table(index="Period", columns="Return", values="Cell", aggfunc="first", fill_value="").reset_index()
