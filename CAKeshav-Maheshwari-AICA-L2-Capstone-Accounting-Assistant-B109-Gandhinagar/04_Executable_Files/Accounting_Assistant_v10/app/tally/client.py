"""HTTP client for TallyPrime's XML server."""
from __future__ import annotations

from dataclasses import dataclass

import threading
import time

import requests

from . import parsers, xml_requests as rq


class TallyError(Exception):
    pass


def _parse(fn, raw: bytes, label: str, *args):
    """Parse a response; on failure keep the raw XML on this PC for troubleshooting."""
    try:
        return fn(raw, *args)
    except Exception as e:
        path = ""
        try:
            from ..config import app_dir
            d = app_dir() / "diagnostics"
            d.mkdir(exist_ok=True)
            p = d / f"parse_error_{label}.xml"
            p.write_bytes(raw)
            path = str(p)
        except OSError:
            pass
        raise TallyError(f"Could not read Tally's reply for {label} ({e}). Raw reply saved to {path}") from e


_LOCKS: dict = {}
_LAST: dict = {}


def _describe(xml: str) -> str:
    if "<TALLYREQUEST>Import" in xml:
        import re
        m = re.search(r'VCHTYPE="([^"]*)"', xml)
        return f"import {m.group(1) if m else ''}".strip()
    for key, end in (("<ID>", "<"),):
        if key in xml:
            return "export " + xml.split(key, 1)[1].split(end, 1)[0]
    return "request"


def _log(line: str) -> None:
    try:
        import datetime as _dt
        from ..config import app_dir
        d = app_dir() / "logs"
        d.mkdir(parents=True, exist_ok=True)
        f = d / "tally.log"
        if f.exists() and f.stat().st_size > 2_000_000:
            f.replace(d / "tally.old.log")
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(f"{_dt.datetime.now():%d-%m %H:%M:%S}  {line}\n")
    except Exception:
        pass


@dataclass
class TallyClient:
    host: str = "localhost"
    port: int = 9000
    timeout: int = 60

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _post(self, xml: str) -> bytes:
        """One request at a time per Tally: TallyPrime's XML server can crash ('Memory Access Violation') when
        several requests arrive together (background screens + posting). Each request is logged to
        logs/tally.log, so the step before a Tally crash is known."""
        lock = _LOCKS.setdefault(self.url, threading.Lock())
        with lock:
            gap = time.monotonic() - _LAST.get(self.url, 0)
            if gap < 0.05:
                time.sleep(0.05 - gap)
            t0 = time.monotonic()
            what = _describe(xml)
            try:
                body = self._post_unlocked(xml)
            except TallyError as e:
                _log(f"{what:<28} FAILED after {time.monotonic() - t0:5.1f}s  {str(e)[:120]}")
                raise
            finally:
                _LAST[self.url] = time.monotonic()
            _log(f"{what:<28} ok     {time.monotonic() - t0:5.1f}s  {len(body):>9,} bytes")
            return body

    def _post_unlocked(self, xml: str) -> bytes:
        try:
            r = requests.post(self.url, data=xml.encode("utf-8"), timeout=self.timeout,
                              headers={"Content-Type": "text/xml; charset=utf-8"})
        except requests.ConnectionError as e:
            if "reset" in str(e).lower() or "aborted" in str(e).lower() or "RemoteDisconnected" in str(e):
                raise TallyError("Tally closed the connection in the middle of a reply (not reachable now). If it "
                                 "shows 'Memory Access Violation', close the message, reopen the company in Tally "
                                 "and try again.") from e
            raise TallyError(f"TallyPrime not reachable at {self.url}. Is Tally open with "
                             "'TallyPrime acts as Server' and port set?") from e
        except requests.Timeout as e:
            raise TallyError(f"TallyPrime at {self.url} timed out after {self.timeout}s") from e
        if r.status_code != 200:
            raise TallyError(f"TallyPrime returned HTTP {r.status_code}")
        body = r.content
        if b"<LINEERROR>" in body and b"<CREATED>" not in body:
            msg = parsers.parse_root(body).findtext(".//LINEERROR") or "unknown error"
            raise TallyError(f"Tally error: {msg}")
        return body

    # ---- health ---------------------------------------------------------
    def ping(self) -> bool:
        try:
            r = requests.get(self.url, timeout=5)
            return r.status_code == 200 and b"Running" in r.content
        except requests.RequestException:
            return False

    # ---- reads ------------------------------------------------------------
    def companies(self) -> list[dict]:
        return _parse(parsers.parse_companies, self._post(rq.companies_request()), "companies")

    def company_gstins(self, company: str, state_code: str = "") -> tuple[list[str], dict[str, bytes]]:
        """Try GST Registration masters, then the full company record. Returns (gstins, raw responses)."""
        raws: dict[str, bytes] = {}
        found: list[str] = []
        for label, req in (("gst_registrations", rq.gst_registrations_request(company)),
                           ("company_detail", rq.company_detail_request(company))):
            try:
                raws[label] = self._post(req)
            except TallyError as e:
                if "not reachable" in str(e) or "timed out" in str(e):
                    raise TallyError("Tally stopped answering while reading the company's GST details. If Tally "
                                     "shows 'Memory Access Violation', close that message, reopen the company and "
                                     "Sync again - the app will skip that step. You can enter the GSTIN in "
                                     "Setup > Company.") from e
                continue
            for g in parsers.scan_gstins(raws[label]):
                if g not in found:
                    found.append(g)
            if found:
                break
        if state_code:
            found.sort(key=lambda g: g[:2] != state_code)
        return found, raws

    def masters(self, kind: str, company: str) -> list[dict]:
        return _parse(parsers.parse_masters, self._post(rq.masters_request(kind, company)), kind, kind)

    def vouchers(self, company: str, from_date: str, to_date: str,
                 base_types: list[str] | None = None) -> list[dict]:
        return _parse(parsers.parse_vouchers,
                      self._post(rq.vouchers_request(company, from_date, to_date, base_types)), "vouchers")

    def vouchers_range(self, company: str, start: "date", end: "date", base_types=None,
                       progress=lambda m: None) -> list[dict]:
        """Fetch month by month (small replies, no timeouts). Dates are re-checked in Python, so
        a Tally that ignores the requested period can't silently cut or pad the result."""
        from datetime import date, timedelta
        lo, hi = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
        out: dict[str, dict] = {}
        self.skipped = 0
        cur = start
        while cur <= end:
            nxt = (date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1))
            stop = min(end, nxt - timedelta(days=1))
            progress(f"vouchers {cur:%b %Y}")
            chunk = self.vouchers(company, cur.strftime("%Y%m%d"), stop.strftime("%Y%m%d"), base_types)
            self.skipped += parsers.LAST_SKIPPED[0]
            outside = sum(1 for v in chunk if not (cur.strftime("%Y%m%d") <= v["date"] <= stop.strftime("%Y%m%d")))
            for v in chunk:
                if lo <= v["date"] <= hi:
                    out[v["guid"] or f"{v['date']}|{v['voucher_type']}|{v['number']}"] = v
            if chunk and outside == len(chunk):
                progress("Tally ignored the month filter; using one full fetch")
                break                               # every chunk would be the same full list
            cur = nxt
        return sorted(out.values(), key=lambda v: v["date"])

    def ledger_balance(self, company: str, ledger: str, from_date: str, to_date: str) -> dict | None:
        """{'closing': Decimal (Tally sign), 'opening': Decimal} or None if the ledger isn't found."""
        raw = self._post(rq.ledger_balance_request(company, ledger, from_date, to_date))
        for d in parsers.parse_collection(raw, "LEDGER"):
            if d.get("NAME", "").strip().lower() == ledger.strip().lower():
                return {"closing": parsers.amount(d.get("CLOSINGBALANCE", "")),
                        "opening": parsers.amount(d.get("OPENINGBALANCE", ""))}
        return None

    def bills(self, company: str, party: str = "", on_date: str = "") -> list[dict]:
        """[{name, party, date, due, amount (Tally sign: negative = Dr = receivable)}]"""
        raw = self._post(rq.bills_request(company, party, on_date))
        out = []
        for d in _parse(parsers.parse_collection, raw, "bills", "BILL"):
            amt = parsers.amount(d.get("CLOSINGBALANCE", ""))
            if not amt:
                continue
            out.append({"name": d.get("NAME", ""), "party": d.get("PARENT", ""), "date": d.get("BILLDATE", ""),
                        "due": d.get("BILLDUEDATE", ""), "credit": d.get("BILLCREDITPERIOD", ""), "amount": amt})
        if party:
            out = [b for b in out if b["party"].strip().lower() == party.strip().lower()]
        return out

    def ledger_closings(self, company: str, from_date: str, to_date: str) -> dict[str, dict]:
        """name -> {parent, opening, closing} (Tally sign: negative = Dr)."""
        raw = self._post(rq.ledger_closings_request(company, from_date, to_date))
        return {d.get("NAME", "").strip(): {"parent": d.get("PARENT", ""),
                                            "opening": parsers.amount(d.get("OPENINGBALANCE", "")),
                                            "closing": parsers.amount(d.get("CLOSINGBALANCE", ""))}
                for d in _parse(parsers.parse_collection, raw, "ledger_closings", "LEDGER") if d.get("NAME")}

    def groups(self, company: str) -> dict[str, dict]:
        raw = self._post(rq.groups_request(company))
        return {d.get("NAME", "").strip(): d for d in _parse(parsers.parse_collection, raw, "groups", "GROUP")
                if d.get("NAME")}

    def stock_values(self, company: str, from_date: str, to_date: str) -> tuple:
        """(opening value, closing value) of all stock items, as Tally computes them."""
        raw = self._post(rq.stock_values_request(company, from_date, to_date))
        rows = _parse(parsers.parse_collection, raw, "stock_values", "STOCKITEM")
        op = sum((abs(parsers.amount(d.get("OPENINGVALUE", ""))) for d in rows), parsers.amount("0"))
        cl = sum((abs(parsers.amount(d.get("CLOSINGVALUE", ""))) for d in rows), parsers.amount("0"))
        return op, cl

    def trial_balance_report(self, company: str, from_date: str, to_date: str) -> tuple[list, bytes]:
        raw = self._post(rq.trial_balance_report_request(company, from_date, to_date))
        return _parse(parsers.parse_tb_report, raw, "trial_balance_report"), raw

    # ---- writes
    def create_ledger(self, company: str, **kw) -> dict:
        from .masters_write import import_masters_envelope, ledger_xml
        res = parsers.parse_import_response(self._post(import_masters_envelope(company, [ledger_xml(**kw)])))
        if not (res["created"] or res["altered"]) or res["errors"]:
            raise TallyError("Tally did not create the ledger: " + ("; ".join(res["line_errors"]) or str(res)))
        return res

    def voucher_ids(self, company: str, from_date: str, to_date: str) -> set[str]:
        raw = self._post(rq.voucher_ids_request(company, from_date, to_date))
        return {d.get("MASTERID", "").strip() for d in _parse(parsers.parse_collection, raw, "voucher_ids", "VOUCHER")
                if d.get("MASTERID", "").strip() and from_date <= d.get("DATE", from_date) <= to_date}

    def voucher_numbers(self, company: str, vtype: str, from_date: str, to_date: str) -> list[tuple]:
        """[(number, date)] of one voucher type, live from Tally."""
        raw = self._post(rq.voucher_numbers_request(company, vtype, from_date, to_date))
        return [(d.get("VOUCHERNUMBER", "").strip(), d.get("DATE", "")) for d in
                _parse(parsers.parse_collection, raw, "voucher_numbers", "VOUCHER")
                if d.get("VOUCHERNUMBER", "").strip() and d.get("VOUCHERTYPENAME", vtype) == vtype]

    def import_vouchers(self, company: str, fragments: list[str]) -> dict:
        return parsers.parse_import_response(self._post(rq.import_vouchers_envelope(company, fragments)))
