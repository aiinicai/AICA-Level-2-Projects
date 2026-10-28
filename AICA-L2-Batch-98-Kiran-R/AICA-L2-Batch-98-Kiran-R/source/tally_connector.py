"""Read-only client for TallyPrime's HTTP/XML interface.

Enable it in TallyPrime: F1 Help > Settings > Advanced Configuration > enable the HTTP server
(default port 9000), keep it bound to this computer, and open the company you want to read.

What is documented by Tally: port 9000, Export requests with TYPE/ID, SVCURRENTCOMPANY, embedded <TDL>
and <FETCHLIST>. What is NOT documented on Tally's public pages, and therefore verified at run time by
`selftest()` and `probe_fields()` instead of being assumed: the date format returned, which voucher
fields exist in your release (for example a user/"altered by" field), and whether the Edit Log can be
pulled as a report. Nothing in this module writes to Tally.
"""
from __future__ import annotations

import argparse
import re
import socket
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

import pandas as pd

BASE_FIELDS = ["MasterID", "AlterID", "VoucherTypeName", "VoucherNumber", "Date", "PartyLedgerName", "Amount",
               "IsCancelled", "IsOptional"]
# Candidates for the probe. Whether Tally exposes any of these on vouchers is release-specific.
CANDIDATE_FIELDS = ["GUID", "Narration", "CreatedBy", "AlteredBy", "EnteredBy", "AlteredOn", "CreatedOn", "EntryDate",
                    "VoucherKey", "EffectiveDate"]
EDITLOG_TDL_COLS = ["Source", "MasterID", "VoucherType", "VoucherNo", "VoucherDate", "Party", "Amount", "Version",
                    "Action", "Activity", "User", "LogTime", "Narration"]
EDITLOG_REPORT_CANDIDATES = ["Edit Log", "Edit Log Summary", "Voucher Edit Log", "Edit Log Report", "Edit Log Summary - Vouchers",
                             "Voucher Edit Log Summary", "Edit Log Vouchers", "EditLogSummary"]


class TallyError(Exception):
    """Tally answered, but with an error or something unexpected."""


class TallyUnreachable(TallyError):
    """Nothing is listening: Tally closed, HTTP server off, wrong port."""


# ----------------------------------------------------------------------------- parsing helpers
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_REF = re.compile(r"&#(x[0-9a-fA-F]+|\d+);")


def sanitize_xml(text: str) -> str:
    """Tally can emit control characters (raw or as &#4;) that make the XML invalid."""
    text = text.lstrip("﻿")

    def fix(m):
        v = m.group(1)
        n = int(v[1:], 16) if v[0] == "x" else int(v)
        return "" if (n < 32 and n not in (9, 10, 13)) else m.group(0)

    text = _CTRL.sub("", _REF.sub(fix, text))
    # Tally writes user-defined fields as <UDF:Name.123> without declaring the prefix: not valid XML. Turn ':' into '_'.
    text = re.sub(r"<(/?)([A-Za-z_][\w.\-]*):([\w.\-]+)", r"<\1\2_\3", text)
    text = re.sub(r"(\s)([A-Za-z_][\w.\-]*):([\w.\-]+)=", r"\1\2_\3=", text)
    return text


_DATE_FORMATS = ("%Y%m%d", "%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%B-%Y")


def parse_tally_date(s) -> date | None:
    s = str(s or "").strip()
    if not s:
        return None
    for f in _DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def parse_amount(s) -> float | None:
    t = re.sub(r"[^0-9.\-]", "", str(s or ""))
    try:
        return float(t) if t not in ("", "-", ".") else None
    except ValueError:
        return None


def _truthy(s) -> bool:
    return str(s or "").strip().lower() in ("yes", "true", "1", "y")


# ----------------------------------------------------------------------------- client
class TallyConnector:
    def __init__(self, host: str = "localhost", port: int = 9000, timeout: float = 120):
        self.host, self.port, self.timeout = host, int(port), timeout
        self.last_raw, self.last_diag = "", {}

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    # -- transport
    def _post(self, xml: str) -> str:
        req = urllib.request.Request(self.url, data=xml.encode("utf-8"),
                                     headers={"Content-Type": "text/xml; charset=utf-8"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raise TallyError(f"Tally returned HTTP {e.code}") from e
        except (urllib.error.URLError, ConnectionError, socket.timeout, OSError) as e:
            raise TallyUnreachable(
                f"Cannot reach Tally at {self.url} ({getattr(e, 'reason', e)}). Is TallyPrime running with the "
                f"HTTP server enabled and the company open?") from e
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or (len(raw) > 3 and raw[1:2] == b"\x00"):
            return raw.decode("utf-16", errors="replace")
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _parse(text: str) -> ET.Element:
        clean = sanitize_xml(text)
        try:
            root = ET.fromstring(clean)
        except ET.ParseError as e:
            raise TallyError(f"Tally's reply is not valid XML ({e}). Start of reply: {clean[:200]!r}") from e
        if root.tag.upper() in ("RESPONSE",):
            raise TallyError((root.text or "Tally rejected the request").strip())
        err = root.find(".//LINEERROR")
        if err is not None:
            raise TallyError((err.text or "Tally reported a line error").strip())
        st = root.find("./HEADER/STATUS")
        if st is not None and (st.text or "").strip() == "0":
            d = root.find(".//STATUS.LIST/DESC")
            raise TallyError(f"Tally reported failure: {(d.text if d is not None else 'no description')}")
        return root

    # -- request builders
    @staticmethod
    def _static(company=None, from_d: date | None = None, to_d: date | None = None) -> str:
        s = "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
        if company:
            s += f"<SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY>"
        if from_d:
            s += f"<SVFROMDATE>{from_d:%Y%m%d}</SVFROMDATE>"
        if to_d:
            s += f"<SVTODATE>{to_d:%Y%m%d}</SVTODATE>"
        return s

    def _collection(self, name, obj_type, fields, company=None, from_d=None, to_d=None) -> list[dict]:
        xml = (f"<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE>"
               f"<ID>{escape(name)}</ID></HEADER><BODY><DESC><STATICVARIABLES>{self._static(company, from_d, to_d)}"
               f"</STATICVARIABLES><TDL><TDLMESSAGE><COLLECTION NAME=\"{escape(name)}\" ISMODIFY=\"No\">"
               f"<TYPE>{escape(obj_type)}</TYPE><FETCH>{escape(', '.join(fields))}</FETCH></COLLECTION></TDLMESSAGE>"
               f"</TDL></DESC></BODY></ENVELOPE>")
        root = self._parse(self._post(xml))
        tag = obj_type.upper()
        rows = []
        for el in root.iter(tag):
            rows.append({c.tag.upper(): (c.text or "").strip() for c in el if len(c) == 0})
        return rows

    # -- public API
    def list_companies(self) -> list[dict]:
        rows = self._collection("ATC Companies", "Company", ["Name", "BooksFrom"])
        out = []
        for r in rows:
            nm = r.get("NAME", "")
            if nm:
                out.append({"name": nm, "books_from": parse_tally_date(r.get("BOOKSFROM"))})
        return out

    def fetch_vouchers(self, company: str, from_d: date, to_d: date, extra_fields=()) -> pd.DataFrame:
        fields = BASE_FIELDS + [f for f in extra_fields if f not in BASE_FIELDS]
        rows = self._collection("ATC Vouchers", "Voucher", fields, company, from_d, to_d)
        recs = []
        for r in rows:
            d = parse_tally_date(r.get("DATE"))
            vno = r.get("VOUCHERNUMBER", "")
            vtype = r.get("VOUCHERTYPENAME", "")
            mid = r.get("MASTERID") or f"{vtype}|{vno}|{d}"
            amt = parse_amount(r.get("AMOUNT"))
            rec = {"MasterID": str(mid), "AlterID": int(r["ALTERID"]) if r.get("ALTERID", "").isdigit() else 0,
                   "VoucherType": vtype, "VoucherNo": vno, "VoucherDate": pd.Timestamp(d) if d else pd.NaT,
                   "Party": r.get("PARTYLEDGERNAME") or "—", "Amount": abs(amt) if amt is not None else 0.0,
                   "Cancelled": _truthy(r.get("ISCANCELLED")), "Optional": _truthy(r.get("ISOPTIONAL"))}
            for f in extra_fields:
                rec[f] = r.get(f.upper(), "")
            recs.append(rec)
        cols = ["MasterID", "AlterID", "VoucherType", "VoucherNo", "VoucherDate", "Party", "Amount", "Cancelled",
                "Optional"] + [f for f in extra_fields if f not in BASE_FIELDS]
        return pd.DataFrame(recs, columns=cols)

    def probe_fields(self, company: str, from_d: date, to_d: date, candidates=None) -> list[dict]:
        """Which optional voucher fields does this Tally release actually return values for?"""
        cands = list(candidates or CANDIDATE_FIELDS)
        window_end = min(to_d, from_d + timedelta(days=45))
        out = []
        try:                                             # one request for all candidates
            rows = self._collection("ATC Probe", "Voucher", ["MasterID"] + cands, company, from_d, window_end)
            n = len(rows)
            for f in cands:
                filled = sum(1 for r in rows if r.get(f.upper(), "").strip())
                out.append({"field": f, "vouchers_checked": n, "with_value": filled,
                            "status": "returns data" if filled else "blank",
                            "sample": next((r[f.upper()] for r in rows if r.get(f.upper(), "").strip()), "")})
            return out
        except TallyUnreachable:
            raise
        except TallyError:
            pass                                         # a bad field name can fail the whole request: go one by one
        for f in cands:
            try:
                rows = self._collection("ATC Probe", "Voucher", ["MasterID", f], company, from_d, window_end)
                filled = sum(1 for r in rows if r.get(f.upper(), "").strip())
                out.append({"field": f, "vouchers_checked": len(rows), "with_value": filled,
                            "status": "returns data" if filled else "blank",
                            "sample": next((r[f.upper()] for r in rows if r.get(f.upper(), "").strip()), "")})
            except TallyError as e:
                out.append({"field": f, "vouchers_checked": 0, "with_value": 0, "status": "error", "sample": str(e)[:80]})
        return out

    def fetch_report(self, company: str, report_id: str, from_d: date, to_d: date) -> pd.DataFrame:
        """EXPERIMENTAL: ask Tally to export a named report and flatten the repeating rows to a table.
        Report names and columns differ by release; map the columns in the app after pulling."""
        xml = (f"<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Data</TYPE>"
               f"<ID>{escape(report_id)}</ID></HEADER><BODY><DESC><STATICVARIABLES>"
               f"{self._static(company, from_d, to_d)}</STATICVARIABLES></DESC></BODY></ENVELOPE>")
        root = self._parse(self._post(xml))
        return _flatten_repeats(root)

    def fetch_report_text(self, company: str, report_id: str, from_d: date, to_d: date, fmt: str = "ASCII") -> str:
        """Ask Tally to export a named report as ASCII (comma delimited) text and return it unchanged (to be saved as a file)."""
        sv = self._static(company, from_d, to_d).replace("$$SysName:XML", f"$$SysName:{fmt}")
        xml = (f"<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Data</TYPE>"
               f"<ID>{escape(report_id)}</ID></HEADER><BODY><DESC><STATICVARIABLES>{sv}</STATICVARIABLES></DESC></BODY></ENVELOPE>")
        return self._post(xml)

    def fetch_editlog_tdl(self, company: str, from_d: date, to_d: date, report_id: str = "AT EL Report") -> pd.DataFrame:
        """Pull ALL Edit Log versions through the TDL report in AuditTrail_EditLog.tdl (the TDL must be loaded in Tally).
        Returns the 13-column flat table (Source, MasterID, ... Narration); rows without a Version are dropped."""
        xml = (f"<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Data</TYPE>"
               f"<ID>{escape(report_id)}</ID></HEADER><BODY><DESC><STATICVARIABLES>"
               f"{self._static(company, from_d, to_d)}</STATICVARIABLES></DESC></BODY></ENVELOPE>")
        raw = self._post(xml)
        if "unknown request" in raw.lower() or "could not find report" in raw.lower() or "report not found" in raw.lower():
            raise TallyError(f"Tally does not know the report '{report_id}'. Load AuditTrail_EditLog.tdl in Tally "
                             f"(F1 Help > Settings > TDL & Add-on) and restart the company.")
        self.last_raw = raw
        root = self._parse(raw)
        rows = _rows_from_report(root)
        df = pd.DataFrame(rows)
        self.last_diag = diagnose_reply(raw)
        if df.empty:
            return pd.DataFrame(columns=EDITLOG_TDL_COLS)
        for c in EDITLOG_TDL_COLS:
            if c not in df:
                df[c] = ""
        df = df[EDITLOG_TDL_COLS]
        df = df[df["Version"].astype(str).str.strip().ne("") & df["Version"].astype(str).str.lower().ne("version")]
        return df.reset_index(drop=True)

    # -- end-to-end check
    def selftest(self, company: str, from_d: date, to_d: date) -> list[dict]:
        res = []

        def add(step, ok, detail):
            ok = None if ok is None else bool(ok)
            res.append({"Step": step, "Result": "PASS" if ok is True else "FAIL" if ok is False else "NOTE",
                        "Detail": detail})

        try:
            comps = self.list_companies()
            add("Connect to Tally", True, f"{self.url}; {len(comps)} open company(ies): "
                                         + ", ".join(c["name"] for c in comps) if comps else f"{self.url}; no company open")
        except TallyError as e:
            add("Connect to Tally", False, str(e))
            return res
        names = [c["name"] for c in comps]
        add("Company is open", company in names,
            f"'{company}' found" if company in names else f"'{company}' not among open companies; use the exact name")
        if company not in names:
            return res
        try:
            df = self.fetch_vouchers(company, from_d, to_d)
        except TallyError as e:
            add("Fetch vouchers", False, str(e))
            return res
        add("Fetch vouchers", len(df) > 0, f"{len(df)} voucher(s) between {from_d} and {to_d}")
        if len(df):
            bad_d = int(df.VoucherDate.isna().sum())
            add("Dates parsed", bad_d == 0, f"{bad_d} voucher(s) with an unreadable date" if bad_d
                else f"{df.VoucherDate.min():%d-%b-%Y} to {df.VoucherDate.max():%d-%b-%Y}")
            zero = int((df.Amount == 0).sum())
            add("Amounts", zero < len(df) * 0.5, f"{zero} of {len(df)} vouchers have amount 0. "
                f"Compare total {df.Amount.sum():,.0f} with a Day Book total before relying on amount tests")
            add("Unique voucher IDs", df.MasterID.is_unique and (df.MasterID != "").all(),
                "MasterID present and unique" if df.MasterID.is_unique else "duplicate MasterIDs: monitor would misread changes")
            add("AlterID present", int((df.AlterID > 0).sum()) > 0, f"max AlterID {int(df.AlterID.max())}")
        try:
            pr = self.probe_fields(company, from_d, to_d)
            have = [p["field"] for p in pr if p["status"] == "returns data"]
            user_like = [f for f in have if f in ("CreatedBy", "AlteredBy", "EnteredBy")]
            add("Optional voucher fields", None, "return data: " + (", ".join(have) or "none"))
            add("User attribution", True if user_like else None,
                f"use '{user_like[0]}' as the attribution field" if user_like else
                "no user field returned: changes will be detected but not attributed to a person; use the Edit Log "
                "export (CSV) for names")
        except TallyError as e:
            add("Optional voucher fields", False, str(e))
        try:
            et = self.fetch_editlog_tdl(company, from_d, to_d)
            add("Edit Log TDL report (AT EL Report)", len(et) > 0,
                f"{len(et)} version row(s); sources: " + ", ".join(f"{k} {v}" for k, v in et.Source.value_counts().items())
                if len(et) else "report answered but returned no versions: is Edit Log ON for this company and period?")
        except TallyError as e:
            add("Edit Log TDL report (AT EL Report)", False, str(e))
        found = None
        for rid in EDITLOG_REPORT_CANDIDATES:
            try:
                t = self.fetch_report(company, rid, from_d, min(to_d, from_d + timedelta(days=30)))
                if len(t):
                    found = (rid, len(t), list(t.columns)[:8])
                    break
            except TallyError:
                continue
        add("Edit Log as report (experimental)", True if found else None,
            f"report '{found[0]}' returned {found[1]} rows, columns {found[2]}" if found
            else "not available over XML under the tried names; export the Edit Log from Tally to CSV and upload it")
        return res


_COLSET = {c.upper(): c for c in EDITLOG_TDL_COLS}


def _rows_from_report(root: ET.Element) -> list[dict]:
    """Rows from the TDL report. Tally may or may not wrap each line in the XML tags we asked for, so read the stream of
    column elements in order and start a new row at every 'Source' element. Works for nested or flat replies."""
    rows, cur = [], None
    for el in root.iter():
        col = _COLSET.get(el.tag.upper())
        if col is None or len(el):
            continue
        if col == "Source":
            cur = {}
            rows.append(cur)
        if cur is not None:
            cur[col] = (el.text or "").strip()
    return rows


def diagnose_reply(raw: str) -> dict:
    """What came back, for the auditor/support: size, distinct tags and the start of the reply."""
    tags = re.findall(r"<([A-Za-z_][\w.\-]*)", raw or "")
    from collections import Counter
    c = Counter(t.upper() for t in tags)
    return {"chars": len(raw or ""), "top_tags": c.most_common(12), "head": (raw or "")[:1500],
            "has_columns": any(k in _COLSET for k in c)}


def _flatten_repeats(root: ET.Element) -> pd.DataFrame:
    best, best_n = None, 1
    for parent in root.iter():
        counts: dict[str, int] = {}
        for c in parent:
            counts[c.tag] = counts.get(c.tag, 0) + 1
        for tag, n in counts.items():
            if n > best_n:
                best, best_n = (parent, tag), n
    if not best:
        return pd.DataFrame()
    parent, tag = best
    rows = [{c.tag: (c.text or "").strip() for c in el.iter() if len(c) == 0 and c is not el} for el in parent.findall(tag)]
    return pd.DataFrame(rows)


def to_register(df: pd.DataFrame) -> pd.DataFrame:
    """Shape a pulled voucher table like the register the checker expects."""
    return df[["VoucherType", "VoucherNo", "VoucherDate", "Party", "Amount"]].copy()


def extract_cli(a) -> int:
    """Ask Tally for the Edit Log (all versions) via the TDL and save a CSV in the Drop folder."""
    import os
    t = TallyConnector(a.host, a.port)
    try:
        df = t.fetch_editlog_tdl(a.company, date.fromisoformat(a.from_d), date.fromisoformat(a.to_d))
    except TallyError as e:
        print("FAILED:", e)
        return 2
    os.makedirs(a.out, exist_ok=True)
    name = f"editlog_{re.sub(r'[^A-Za-z0-9]+', '_', a.company)[:30]}_{a.from_d}_{a.to_d}.csv"
    path = os.path.join(a.out, name)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"OK: {len(df)} Edit Log version rows saved to {path}")
    if len(df):
        print("   by source:", ", ".join(f"{k} {v}" for k, v in df.Source.value_counts().items()))
    else:
        print("   No rows: check that Edit Log is ON for the company and the dates cover the year.")
    return 0 if len(df) else 3


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Self-test the connection to TallyPrime (read-only), or extract the Edit Log.")
    ap.add_argument("--extract", action="store_true", help="save the Edit Log (all versions) from the TDL report as CSV")
    ap.add_argument("--out", default=r"C:\AuditTrail\Drop")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--company", required=True)
    ap.add_argument("--from", dest="from_d", required=True, help="YYYY-MM-DD")
    ap.add_argument("--to", dest="to_d", required=True, help="YYYY-MM-DD")
    a = ap.parse_args()
    if a.extract:
        raise SystemExit(extract_cli(a))
    t = TallyConnector(a.host, a.port)
    for r in t.selftest(a.company, date.fromisoformat(a.from_d), date.fromisoformat(a.to_d)):
        print(f"[{r['Result']:4}] {r['Step']}: {r['Detail']}")
