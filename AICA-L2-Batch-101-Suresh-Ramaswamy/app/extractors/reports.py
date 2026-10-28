"""Summary reports from billing software (no invoice-level rows).

* HSN-wise sales report     -> Table 12 (HSN summary)
* GST output register       -> Table 7 (B2C others), Table 8 (exempt) and Table 13 (documents issued), date-wise
Both give rows in the same form as an uploaded Master Template, so they flow through the normal checks and CSV export.
"""
import re
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .. import hsn as hsn_mod
from ..models import DocSeries
from ..series import split_no
from ..utils import D, ZERO

HSN_REPORT = "hsn-report"
OUTPUT_REGISTER = "output-register"


def _q2(v) -> str:
    return str(D(v).quantize(Decimal("0.01")))


def _plain(v) -> str:
    v = D(v)
    return str(int(v)) if v == v.to_integral_value() else str(v.normalize())


def _sheet0(path: Path):
    if Path(path).suffix.lower() in (".csv", ".txt"):
        return pd.read_csv(path, header=None, dtype=object, keep_default_na=False)
    return pd.read_excel(path, sheet_name=0, header=None, dtype=object)


def detect_report(path: Path) -> Optional[str]:
    try:
        df = _sheet0(path)
    except Exception:  # noqa
        return None
    top = " ".join(str(v) for v in df.head(8).values.ravel() if isinstance(v, str)).lower()
    if "hsnwise sales report" in top or "hsn wise sales report" in top:
        return HSN_REPORT
    if "gst output register" in top:
        return OUTPUT_REGISTER
    return None


def _find_header(df, must: Tuple[str, ...]) -> int:
    for i in range(min(len(df), 25)):
        vals = [str(v).strip().lower() for v in df.iloc[i].tolist() if v is not None and str(v).strip()]
        if all(any(m in v for v in vals) for m in must):
            return i
    return -1


def _s(v) -> str:
    """Cell as text; blank for None / NaN."""
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return str(v).strip()


def _num(v) -> Decimal:
    if v is None or (isinstance(v, float) and v != v):
        return ZERO
    return D(v)


def _rate_of(text) -> Optional[Decimal]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(text or ""))
    return D(m.group(1)) if m else None


def read_hsn_report(path: Path, schema: dict) -> Tuple[Dict[str, list], list]:
    df = _sheet0(path)
    msgs = []
    h = _find_header(df, ("hsn", "base"))
    if h < 0:
        return {}, ["HSN report: heading row (HSN Code, Tax Rate, Base ...) not found"]
    cols = {}
    for j, v in enumerate(df.iloc[h].tolist()):
        t = _s(v).lower()
        if t.startswith("hsn"):
            cols["hsn"] = j
        elif t == "tax rate" or t == "rate":
            cols["rate"] = j
        elif t == "uqc" or t == "unit":
            cols["uqc"] = j
        elif "quantity" in t:
            cols["qty"] = j
        elif t == "base" or "taxable" in t:
            cols["base"] = j
        elif t in ("sgst", "cgst", "igst", "cess"):
            cols[t] = j
        elif t == "total value":
            cols["total"] = j
        elif t == "productname" or t == "product name":
            cols["name"] = j
    if not {"hsn", "base"} <= set(cols):
        return {}, ["HSN report: HSN Code / Base columns not found"]
    agg: "OrderedDict[tuple, dict]" = OrderedDict()
    ex_rows = 0
    for i in range(h + 1, len(df)):
        row = df.iloc[i].tolist()
        hsn = row[cols["hsn"]]
        if hsn is None or (isinstance(hsn, float) and hsn != hsn) or not str(hsn).strip():
            continue
        hsn = re.sub(r"\.0$", "", str(hsn).strip())
        if not hsn.isdigit():
            continue
        rt_text = _s(row[cols["rate"]]) if "rate" in cols else ""
        rate = _rate_of(rt_text)
        if rate is None:
            rate = ZERO
            if re.search(r"exempt", rt_text, re.I):
                ex_rows += 1
        uqc_raw = _s(row[cols["uqc"]]) if "uqc" in cols else ""
        code = uqc_raw.upper().split("-")[0].strip()
        codes = {u.split("-")[0]: u for u in schema.get("uqc", [])}
        uqc = "NA" if hsn.startswith("99") else codes.get(code, schema.get("default_uqc", "OTH-OTHERS"))
        key = (hsn, _plain(rate), uqc)
        a = agg.setdefault(key, dict(qty=ZERO, taxable=ZERO, igst=ZERO, cgst=ZERO, sgst=ZERO, cess=ZERO, total=ZERO, names=[]))
        if "name" in cols and _s(row[cols["name"]]) and _s(row[cols["name"]]) not in a["names"]:
            a["names"].append(_s(row[cols["name"]]))
        a["qty"] += _num(row[cols["qty"]]) if "qty" in cols else ZERO
        a["taxable"] += _num(row[cols["base"]])
        for t in ("igst", "cgst", "sgst", "cess"):
            if t in cols:
                a[t] += _num(row[cols[t]])
        a["total"] += _num(row[cols["total"]]) if "total" in cols else ZERO
    rows = []
    for (hsn, rate, uqc), a in agg.items():
        total = a["total"] or (a["taxable"] + a["igst"] + a["cgst"] + a["sgst"] + a["cess"])
        rows.append(dict(hsn=hsn, description=hsn_mod.short(hsn_mod.describe(hsn)), uqc=uqc, qty=_plain(a["qty"]),
                         total_value=_q2(total), rate=rate, taxable=_q2(a["taxable"]), igst=_q2(a["igst"]),
                         cgst=_q2(a["cgst"]), sgst=_q2(a["sgst"]), cess=_q2(a["cess"]),
                         __file=path.name,
                         __ref="HSN report" + (": " + "; ".join(a["names"][:3]) + (" ..." if len(a["names"]) > 3 else "")
                                               if a["names"] else "")))
    msgs.append(f"HSN report: {len(rows)} HSN / rate rows built from the product lines (Table 12)")
    if ex_rows:
        msgs.append(f"{ex_rows} exempt product line(s) shown at 0% rate")
    return {"hsn": rows}, msgs


def read_output_register(path: Path, client: dict, schema: dict) -> Tuple[Dict[str, list], list, List[DocSeries]]:
    df = _sheet0(path)
    msgs = []
    h = _find_header(df, ("bill date", "series"))
    if h < 0:
        return {}, ["Output register: heading row (Bill Date, Series, ...) not found"], []
    heads = [_s(v) for v in df.iloc[h].tolist()]
    intra, inter = OrderedDict(), OrderedDict()
    exempt_col = cess_col = bills_col = from_col = to_col = desc_col = series_col = credit_col = debit_col = None
    for j, t in enumerate(heads):
        tl = t.lower()
        m1 = re.match(r"^(\d+(?:\.\d+)?)%\s*gst base$", tl)
        m2 = re.match(r"^(\d+(?:\.\d+)?)%\s*igst base$", tl)
        if m1:
            intra[D(m1.group(1))] = j
        elif m2:
            inter[D(m2.group(1))] = j
        elif tl == "exempt":
            exempt_col = j
        elif tl == "cess":
            cess_col = j
        elif tl == "billcount":
            bills_col = j
        elif tl.startswith("from bill"):
            from_col = j
        elif tl.startswith("to bill"):
            to_col = j
        elif tl == "series description":
            desc_col = j
        elif tl == "series":
            series_col = j
        elif tl == "credit":
            credit_col = j
        elif tl == "debit":
            debit_col = j
    own = client["gstin"][:2]
    by_rate: "OrderedDict[Decimal, Decimal]" = OrderedDict((r, ZERO) for r in intra)
    inter_tot, exempt, cess, credit, debit = ZERO, ZERO, ZERO, ZERO, ZERO
    series_rows: "OrderedDict[tuple, list]" = OrderedDict()
    for i in range(h + 1, len(df)):
        row = df.iloc[i].tolist()
        d = _s(row[desc_col]) if desc_col is not None else ""
        if re.search(r"total", d, re.I) or not _s(row[0]):
            continue
        for r, j in intra.items():
            by_rate[r] += _num(row[j])
        for r, j in inter.items():
            inter_tot += _num(row[j])
        exempt += _num(row[exempt_col]) if exempt_col is not None else ZERO
        cess += _num(row[cess_col]) if cess_col is not None else ZERO
        credit += _num(row[credit_col]) if credit_col is not None else ZERO
        debit += _num(row[debit_col]) if debit_col is not None else ZERO
        if from_col is not None and to_col is not None and _s(row[from_col]) and _s(row[to_col]):
            series_rows.setdefault((_s(row[series_col]), d), []).append(
                (_s(row[from_col]), _s(row[to_col]), int(_num(row[bills_col])) if bills_col is not None else 0))
    b2cs = [dict(supply_type="OE", pos=own, applicable_pct="", rate=_plain(r), taxable=_q2(v), cess="0.00",
                 ecom_gstin="", __file=path.name, __ref="Output register")
            for r, v in by_rate.items() if v]
    tables: Dict[str, list] = {"b2cs": b2cs}
    if exempt:
        tables["exemp"] = [dict(description="Intra-State supplies to unregistered persons", nil_rated="0.00",
                                exempted=_q2(exempt), non_gst="0.00", __file=path.name, __ref="Output register")]
    msgs.append("Output register: sales taken as B2C (unregistered, same state) - "
                + ", ".join(f"{_plain(r)}%: {_q2(v)}" for r, v in by_rate.items() if v)
                + (f"; exempt: {_q2(exempt)}" if exempt else ""))
    if inter_tot:
        msgs.append(f"WARNING: inter-state (IGST) sales of {_q2(inter_tot)} are in the register but the states are not "
                    "given - not imported; enter them state-wise in the Master Template (B2CS)")
    if cess:
        msgs.append(f"WARNING: cess of {_q2(cess)} is in the register but is not imported - add it in the Master Template")
    if credit or debit:
        msgs.append(f"WARNING: the register shows credit {_q2(credit)} / debit {_q2(debit)} - check for credit/debit notes "
                    "or sales returns that must be reported separately")
    docs: List[DocSeries] = []
    for (code, desc), items in series_rows.items():
        nature = "Credit Note" if re.search(r"credit|return", desc, re.I) else \
            "Debit Note" if re.search(r"debit", desc, re.I) else "Invoices for outward supply"
        first, last = items[0][0], items[-1][1]
        total = sum(n for _, _, n in items)
        cancelled = 0
        a, b = split_no(first), split_no(last)
        if a and b and a[0] == b[0] and a[3] == b[3] and b[1] >= a[1]:
            span = b[1] - a[1] + 1
            if span > total:
                cancelled = span - total
                msgs.append(f"WARNING: series {first} - {last}: {span} numbers but only {total} bills in the register; "
                            f"{cancelled} counted as cancelled - confirm")
        docs.append(DocSeries(nature=nature, from_no=first, to_no=last, total=total + cancelled, cancelled=cancelled,
                              origin="register", source_file=path.name))
        msgs.append(f"Series {first} - {last}: {total + cancelled} documents, {cancelled} cancelled (Table 13)")
    return tables, msgs, docs
