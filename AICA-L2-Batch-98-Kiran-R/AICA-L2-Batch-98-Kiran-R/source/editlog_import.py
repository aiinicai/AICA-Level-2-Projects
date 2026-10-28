"""Turn the Edit Log export produced by tally_editlog_export.tdl (one row per voucher version) into the edit-log layout
the checker expects: LogTime, User, Action, VoucherType, VoucherNo, VoucherDate, Field, OldValue, NewValue, Amount.

Rows are compared version by version, so a change of amount, date, party or number becomes its own row with the old and
new value. Versions whose Action says Create/Alter/Resave/Delete are mapped to Created/Altered/Deleted.
"""
from __future__ import annotations

import re

import pandas as pd

EXPECT = ["Source", "MasterID", "VoucherType", "VoucherNo", "VoucherDate", "Party", "Amount", "Version", "Action", "Activity", "User", "LogTime"]


def is_tdl_export(df: pd.DataFrame) -> bool:
    cols = {re.sub(r"[^a-z]", "", str(c).lower()) for c in df.columns}
    return {"masterid", "version", "logtime", "user"} <= cols


def _norm(df):
    m = {re.sub(r"[^a-z]", "", c.lower()): c for c in EXPECT}
    d = df.rename(columns={c: m.get(re.sub(r"[^a-z]", "", str(c).lower()), c) for c in df.columns})
    # the TDL reads each log through two bindings (variable and field); keep one copy of any row seen twice
    key = [c for c in ("Source", "MasterID", "VoucherNo", "Version", "Action", "User", "LogTime") if c in d.columns]
    return d.drop_duplicates(subset=key) if key else d


def _dt(series):
    """ISO dates (2026-03-10) are read as year-month-day; everything else (10-03-2026, 10-Mar-26) day first."""
    s = series.astype(str).str.strip()
    iso = s.str.match(r"^\d{4}-\d{2}-\d{2}")
    out = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    out[iso] = pd.to_datetime(s[iso], errors="coerce")
    out[~iso] = pd.to_datetime(s[~iso], errors="coerce", dayfirst=True, format="mixed")
    return out


def _act(a: str, v: int, first: bool) -> str:
    s = str(a).lower()
    if "delet" in s or "cancel" in s:
        return "Deleted"
    if "creat" in s or (first and not s.strip()):
        return "Created"
    return "Altered"          # Alter, Resave, anything else after creation


def split_sources(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The TDL export has a Source column: Voucher / Ledger / Group / Stock Item / Company. Older exports have none."""
    d = _norm(df)
    if "Source" not in d:
        return {"Voucher": d}
    src = d["Source"].astype(str).str.strip()
    return {k: d[src == k] if k != "Voucher" else d[(src == "Voucher") | (src == "")] for k in src.replace("", "Voucher").unique()}


def convert_masters(df: pd.DataFrame) -> pd.DataFrame:
    """Master-data and company-level log rows -> LogTime, User, Action, Object, Name, Parent, Activity.
    ICAI FAQ 25: changes to vendor/customer masters feed the books of account, so they are part of the audit trail."""
    d = _norm(df).copy()
    for c in EXPECT:
        if c not in d:
            d[c] = ""
    d = d[d["Source"].astype(str).str.strip().isin(["Ledger", "Group", "Stock Item", "Company"])]
    d["LogTime"] = _dt(d["LogTime"])
    d = d.dropna(subset=["LogTime"]).sort_values("LogTime", kind="stable")
    out = pd.DataFrame({"LogTime": d["LogTime"], "User": d["User"].astype(str), "Object": d["Source"],
                        "Name": d["VoucherNo"].astype(str), "Parent": d["Party"].astype(str),
                        "Version": d["Version"], "Action": [_act(a, 0, False) if str(a).strip() else "" for a in d["Action"]],
                        "Activity": d["Activity"].astype(str)})
    return out.reset_index(drop=True)


def convert(df: pd.DataFrame) -> pd.DataFrame:
    d = _norm(df).copy()
    for c in EXPECT:
        if c not in d:
            d[c] = ""
    if (d["Source"].astype(str).str.strip() != "").any():
        d = d[d["Source"].astype(str).str.strip().isin(["Voucher"])]
    if "Narration" not in d:
        d["Narration"] = ""
    d["Narration"] = d["Narration"].fillna("").astype(str)
    d["Version"] = pd.to_numeric(d["Version"], errors="coerce")
    d["LogTime"] = _dt(d["LogTime"])
    d["VoucherDate"] = _dt(d["VoucherDate"])
    d["Amount"] = pd.to_numeric(d["Amount"].astype(str).str.replace(",", "").str.replace(r"\(|\)|Dr|Cr", "", regex=True), errors="coerce").abs()
    d = d.dropna(subset=["LogTime"]).sort_values(["MasterID", "Version", "LogTime"], kind="stable")
    out = []
    for mid, g in d.groupby("MasterID", sort=False):
        prev = None
        for i, r in enumerate(g.itertuples()):
            act = _act(r.Action, r.Version, i == 0)
            base = dict(LogTime=r.LogTime, User=str(r.User), VoucherType=r.VoucherType, VoucherNo=str(r.VoucherNo),
                        VoucherDate=r.VoucherDate, Amount=r.Amount)
            if act != "Altered" or prev is None:
                out.append({**base, "Action": act, "Field": "", "OldValue": "", "NewValue": ""})
            else:
                changes = []
                for label, a, b in (("Amount", prev.Amount, r.Amount), ("Date", prev.VoucherDate, r.VoucherDate),
                                    ("Party", prev.Party, r.Party), ("VoucherNo", prev.VoucherNo, r.VoucherNo),
                                    ("VoucherType", prev.VoucherType, r.VoucherType),
                                    ("Narration", prev.Narration, r.Narration)):
                    if (pd.notna(a) or pd.notna(b)) and str(a) != str(b):
                        changes.append((label, a, b))
                if not changes:
                    out.append({**base, "Action": "Altered", "Field": "", "OldValue": "", "NewValue": ""})
                for label, a, b in changes:
                    fmt = (lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else str(x))
                    out.append({**base, "Action": "Altered", "Field": label, "OldValue": fmt(a), "NewValue": fmt(b)})
            prev = r
    cols = ["LogTime", "User", "Action", "VoucherType", "VoucherNo", "VoucherDate", "Field", "OldValue", "NewValue", "Amount"]
    return pd.DataFrame(out, columns=cols)


# ---------------------------------------------------------------------------------------------------------------
# Tally's own "Edit Log Summary - Vouchers" report, exported as ASCII (Comma Delimited) with Alt+E.
# Layout (one block per voucher):
#   <date>,"<party / particulars>","<voucher type>","<voucher no>",<no. of versions>,<amount>,,
#   ,<log date-time>,"<Created|Altered|Deleted>","by <user>","Ver n",,,
# A deleted voucher shows as  <date>,"(Deleted)","","",,,,  followed by its version lines.
# It carries who / when / which activity for every version. Old-vs-new field values are NOT in this report;
# they are on the "Differences Between Edit Log Versions" screen (see guided.py, field-level sample).
# ---------------------------------------------------------------------------------------------------------------
_HDR = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2,4}$")


def is_tally_summary_text(text: str) -> bool:
    import csv, io
    n = 0
    for row in csv.reader(io.StringIO(text)):
        if row and _HDR.match(row[0].strip()) and len(row) >= 5:
            n += 1
        if n >= 2:
            break
    return n >= 2 and bool(re.search(r"\bVer \d+", text)) and bool(re.search(r"\b(Created|Altered|Deleted)\b", text))


def _cs(v) -> str:
    import datetime as _d
    if v is None or (isinstance(v, float) and v != v):
        return ""
    if isinstance(v, (_d.datetime, pd.Timestamp)):
        return v.strftime("%d-%b-%y %H:%M") if (v.hour or v.minute) else v.strftime("%d-%b-%y")
    if isinstance(v, _d.date):
        return v.strftime("%d-%b-%y")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


_VER = re.compile(r"^Ver\s*\d+$", re.I)
_ACT = re.compile(r"^(created|altered|deleted|resaved|cancelled|imported|migrated|restored)", re.I)
_TIME = re.compile(r"\d{1,2}[:.]\d{2}")


def is_summary_rows(rows) -> bool:
    hdr = sum(1 for r in rows if r and _HDR.match(_cs(r[0])) and len(r) >= 5)
    ver = sum(1 for r in rows if any(_VER.match(_cs(c)) for c in r))
    return hdr >= 2 and ver >= 2


def parse_rows(rows) -> pd.DataFrame:
    """Rows of Tally's Edit Log Summary (ASCII, Excel or HTML layout) -> TDL-export layout, one row per version."""
    out, cur, dels = [], None, 0
    for r in rows:
        r = [_cs(c) for c in r] + [""] * 8
        if not any(r):
            continue
        if _HDR.match(r[0]):                                  # voucher header line
            party, vt, vn = r[1], r[2], r[3]
            amt = re.sub(r"[^0-9.\-]", "", r[5])
            if party == "(Deleted)":
                dels += 1
                key = f"DELETED-{dels}"
            else:
                key = f"{r[0]}|{vt}|{vn}"
            cur = dict(Source="Voucher", MasterID=key, VoucherType=vt, VoucherNo=vn if vn else "(deleted)",
                       VoucherDate=r[0], Party=party if party != "(Deleted)" else "", Amount=amt, Narration="")
        elif cur is not None and any(_VER.match(c) for c in r):   # version line
            ver = next(c for c in r if _VER.match(c))
            act = next((c for c in r if _ACT.match(c)), "")
            usr = next((c for c in r if re.match(r"^by\s+", c, re.I)), "")
            tm = next((c for c in r if _TIME.search(c) and not re.match(r"^by\s+", c, re.I)), "")
            out.append({**cur, "Version": int(re.search(r"\d+", ver).group()), "Action": act, "Activity": act,
                        "User": re.sub(r"^by\s+", "", usr, flags=re.I), "LogTime": tm})
    d = pd.DataFrame(out, columns=EXPECT + ["Narration"])
    for k in [k for k in d["MasterID"].unique() if str(k).startswith("DELETED-")]:   # stable key across several files
        g = d[d["MasterID"] == k]
        first = g[g["Version"] == g["Version"].min()].iloc[0]
        d.loc[g.index, "MasterID"] = f"DELETED|{first.VoucherDate}|{first.LogTime}"
    return d


def parse_tally_summary(text: str) -> pd.DataFrame:
    import csv, io
    return parse_rows(list(csv.reader(io.StringIO(text.lstrip("\ufeff")))))


def parse_file(name: str, data: bytes):
    """Any Tally export of the Edit Log -> (kind, DataFrame). kind: 'summary' (Edit Log Summary, ready), 'tdl' (Audit Trail TDL
    export, ready), 'table' (some other table: columns need mapping) or None (not readable)."""
    import io
    n = name.lower()
    try:
        if n.endswith((".txt", ".csv", ".asc")):
            t = read_text(data)
            if is_tally_summary_text(t):
                return "summary", parse_tally_summary(t)
            df = pd.read_csv(io.StringIO(t), dtype=str, keep_default_na=False)
        elif n.endswith((".xlsx", ".xls")):
            raw = pd.read_excel(io.BytesIO(data), header=None, dtype=object)
            rows = raw.values.tolist()
            if is_summary_rows(rows):
                return "summary", parse_rows(rows)
            hdr = next((i for i in range(min(len(raw), 30)) if raw.iloc[i].notna().sum() >= max(3, raw.shape[1] // 2)), 0)
            df = raw.iloc[hdr + 1:].copy()
            df.columns = [str(c) if pd.notna(c) else f"col{i}" for i, c in enumerate(raw.iloc[hdr])]
            df = df.dropna(how="all").reset_index(drop=True)
        elif n.endswith((".html", ".htm")):
            tabs = pd.read_html(io.StringIO(read_text(data)), header=None)
            rows = [r for t in tabs for r in t.values.tolist()]
            if is_summary_rows(rows):
                return "summary", parse_rows(rows)
            df = max(tabs, key=len)
        elif n.endswith(".json"):
            import json
            j = json.loads(read_text(data))
            df = pd.json_normalize(j if isinstance(j, list) else next((v for v in j.values() if isinstance(v, list)), [j]))
            rows = df.astype(object).values.tolist()
            if is_summary_rows(rows):
                return "summary", parse_rows(rows)
        elif n.endswith(".xml"):
            df = pd.read_xml(io.BytesIO(data))
            rows = df.astype(object).values.tolist()
            if is_summary_rows(rows):
                return "summary", parse_rows(rows)
        else:
            return None, pd.DataFrame()
    except Exception:
        return None, pd.DataFrame()
    if is_tdl_export(df):
        return "tdl", df
    return "table", df


def parse_many(texts: list[str]) -> pd.DataFrame:
    """Several exports (one per voucher type or per month) -> one table; duplicates removed."""
    parts = [parse_tally_summary(t) for t in texts]
    d = pd.concat([p for p in parts if len(p)], ignore_index=True) if any(len(p) for p in parts) else pd.DataFrame(columns=EXPECT + ["Narration"])
    return d.drop_duplicates(subset=["MasterID", "Version", "LogTime", "User"]).reset_index(drop=True) if len(d) else d


def read_text(b: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("latin-1")
