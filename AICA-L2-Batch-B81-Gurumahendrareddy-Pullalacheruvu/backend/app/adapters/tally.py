"""Tally Prime connector.

Tally exposes an XML-over-HTTP endpoint on the machine it runs on (default
port 9000, "Enable ODBC/HTTP" switched on in F1 › Advanced Configuration).
There is no REST API and no auth — the trade-off is that the app must run on
the same network as Tally, which suits a local-first tool.

Everything Tally returns is normalised into the common internal schema in
`normalizer.py`, so adding Zoho Books later means writing one more adapter and
touching nothing downstream.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import requests

from app.config import settings


class TallyError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Request envelopes
# ---------------------------------------------------------------------------
def _export(report: str, company: str | None, extra: str = "",
            from_date: date | None = None, to_date: date | None = None) -> str:
    sv = ""
    if from_date and to_date:
        sv = (f"<SVFROMDATE>{from_date:%Y%m%d}</SVFROMDATE>"
              f"<SVTODATE>{to_date:%Y%m%d}</SVTODATE>")
    comp = f"<SVCURRENTCOMPANY>{_esc(company)}</SVCURRENTCOMPANY>" if company else ""
    return f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>
  <BODY><EXPORTDATA><REQUESTDESC>
    <REPORTNAME>{report}</REPORTNAME>
    <STATICVARIABLES>
      <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{comp}{sv}{extra}
    </STATICVARIABLES>
  </REQUESTDESC></EXPORTDATA></BODY>
</ENVELOPE>"""


def _collection(name: str, tdl_type: str, fetch: list[str],
                company: str | None = None,
                from_date: date | None = None, to_date: date | None = None) -> str:
    fetch_xml = "".join(f"<NATIVEMETHOD>{f}</NATIVEMETHOD>" for f in fetch)
    sv = ""
    if from_date and to_date:
        sv = (f"<SVFROMDATE>{from_date:%Y%m%d}</SVFROMDATE>"
              f"<SVTODATE>{to_date:%Y%m%d}</SVTODATE>")
    comp = f"<SVCURRENTCOMPANY>{_esc(company)}</SVCURRENTCOMPANY>" if company else ""
    return f"""<ENVELOPE>
  <HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE><ID>{name}</ID></HEADER>
  <BODY><DESC>
    <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{comp}{sv}</STATICVARIABLES>
    <TDL><TDLMESSAGE>
      <COLLECTION NAME="{name}" ISMODIFY="No">
        <TYPE>{tdl_type}</TYPE>
        {fetch_xml}
      </COLLECTION>
    </TDLMESSAGE></TDL>
  </DESC></BODY>
</ENVELOPE>"""


def _esc(s: str | None) -> str:
    if not s:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------
@dataclass
class TallyClient:
    host: str = settings.TALLY_HOST
    port: int = settings.TALLY_PORT
    timeout: int = settings.TALLY_TIMEOUT

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def post(self, payload: str) -> ET.Element:
        try:
            r = requests.post(self.url, data=payload.encode("utf-8"),
                              timeout=self.timeout,
                              headers={"Content-Type": "text/xml; charset=utf-8"})
        except requests.exceptions.ConnectionError:
            raise TallyError(
                f"Could not reach Tally at {self.url}. Check that Tally Prime is running, "
                f"a company is open, and 'Enable ODBC/HTTP' is set to Yes under "
                f"F1 › Advanced Configuration.")
        except requests.exceptions.Timeout:
            raise TallyError(f"Tally did not respond within {self.timeout}s. A large date "
                             f"range can take a while — try a shorter one.")
        if r.status_code >= 400:
            raise TallyError(f"Tally returned HTTP {r.status_code}.")
        return _parse(r.content)

    def ping(self) -> dict:
        """Used by Setup › Data Sources to show connection status honestly."""
        try:
            root = self.post("""<ENVELOPE><HEADER><VERSION>1</VERSION>
              <TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE>
              <ID>List of Companies</ID></HEADER>
              <BODY><DESC><STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
              </STATICVARIABLES><TDL><TDLMESSAGE>
                <COLLECTION NAME="List of Companies" ISMODIFY="No">
                  <TYPE>Company</TYPE><NATIVEMETHOD>NAME</NATIVEMETHOD>
                </COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>""")
            names = [_text(c.find("NAME")) for c in root.iter("COMPANY")]
            names = [n for n in names if n]
            return {"connected": True, "url": self.url, "companies": names,
                    "message": (f"Connected. {len(names)} company/companies open."
                                if names else
                                "Connected, but no company is open in Tally.")}
        except TallyError as e:
            return {"connected": False, "url": self.url, "companies": [],
                    "message": str(e)}


def _parse(content: bytes) -> ET.Element:
    """Tally emits characters that are not valid in XML (and sometimes an
    unescaped ampersand), so the payload is repaired before parsing."""
    text = content.decode("utf-8", errors="replace")
    text = text.replace("&#4;", "").replace("\x04", "")
    text = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+);)", "&amp;", text)
    try:
        return ET.fromstring(text)
    except ET.ParseError as e:
        raise TallyError(f"Could not parse Tally's response: {e}")


def _text(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    return "".join(node.itertext()).strip() or None


def _amount(raw: str | None) -> float:
    """Tally writes amounts as strings; a leading '-' is a credit."""
    if not raw:
        return 0.0
    cleaned = re.sub(r"[^0-9.\-]", "", raw)
    try:
        return float(cleaned or 0.0)
    except ValueError:
        return 0.0


def _tally_date(raw: str | None) -> date | None:
    if not raw:
        return None
    for fmt in ("%Y%m%d", "%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Extractions — each returns plain dicts, ready for the normalizer
# ---------------------------------------------------------------------------
def fetch_ledgers(client: TallyClient, company: str | None = None) -> list[dict]:
    root = client.post(_collection(
        "CR Ledgers", "Ledger",
        ["NAME", "PARENT", "OPENINGBALANCE", "CLOSINGBALANCE", "ISDEEMEDPOSITIVE",
         "GUID", "ISREVENUE", "ISBILLWISEON", "CREDITPERIOD"],
        company=company))
    out = []
    for led in root.iter("LEDGER"):
        name = led.get("NAME") or _text(led.find("NAME"))
        if not name:
            continue
        # Same sign convention as the voucher lines, and the same reason for
        # flipping it here: Tally stores a debit balance as a negative number,
        # everything downstream reads a positive balance as an asset. A bank
        # account that arrives negative is not an overdraft, it is this.
        out.append({
            "external_id": _text(led.find("GUID")),
            "name": name,
            "parent_group": _text(led.find("PARENT")),
            "opening_balance": -_amount(_text(led.find("OPENINGBALANCE"))),
            "closing_balance": -_amount(_text(led.find("CLOSINGBALANCE"))),
            "is_revenue": (_text(led.find("ISREVENUE")) or "No").lower() == "yes",
            "credit_period": _text(led.find("CREDITPERIOD")),
        })
    return out


def fetch_vouchers(client: TallyClient, from_date: date, to_date: date,
                   company: str | None = None) -> list[dict]:
    """Day Book over a date range — one row per ledger line of each voucher."""
    root = client.post(_export("Day Book", company, from_date=from_date, to_date=to_date))
    out = []
    for v in root.iter("VOUCHER"):
        vdate = _tally_date(_text(v.find("DATE")))
        vtype = _text(v.find("VOUCHERTYPENAME")) or "Journal"
        vno = _text(v.find("VOUCHERNUMBER"))
        narration = _text(v.find("NARRATION"))
        party = _text(v.find("PARTYLEDGERNAME")) or _text(v.find("PARTYNAME"))
        guid = _text(v.find("GUID"))
        for line in v.iter("ALLLEDGERENTRIES.LIST"):
            led = _text(line.find("LEDGERNAME"))
            amt = _amount(_text(line.find("AMOUNT")))
            if not led:
                continue
            # Tally's sign convention, which is the opposite of the intuitive
            # one and the source of a whole class of quiet errors: inside
            # ALLLEDGERENTRIES.LIST a **negative AMOUNT is a debit** and a
            # positive one is a credit. ISDEEMEDPOSITIVE=Yes marks the debit
            # side and corroborates it.
            #
            # Everything downstream of this adapter uses the plain reading —
            # positive means money into the account — so the sign is flipped
            # here, once, at the boundary. Get this wrong and a receipt is
            # recorded as a payment: burn reads as income, and every screen is
            # confidently upside down.
            deemed_positive = (_text(line.find("ISDEEMEDPOSITIVE")) or "").lower()
            signed = -amt
            if deemed_positive == "yes" and signed < 0:
                signed = abs(signed)          # trust the explicit marker
            elif deemed_positive == "no" and signed > 0:
                signed = -abs(signed)

            out.append({
                "external_id": f"{guid}:{led}" if guid else None,
                "txn_date": vdate, "voucher_type": vtype, "voucher_no": vno,
                "narration": narration, "party": party, "ledger": led,
                "debit": signed if signed > 0 else 0.0,
                "credit": -signed if signed < 0 else 0.0,
                "amount": signed,
            })
    return out


def fetch_bills_outstanding(client: TallyClient, as_on: date,
                            company: str | None = None,
                            receivable: bool = True) -> list[dict]:
    report = "Bills Receivable" if receivable else "Bills Payable"
    root = client.post(_export(report, company, from_date=as_on, to_date=as_on))
    out = []
    for b in root.iter("BILLFIXED"):
        out.append({
            "party": _text(b.find("BILLPARTY")) or _text(b.find("PARTYNAME")),
            "bill_no": _text(b.find("BILLREF")) or _text(b.find("NAME")),
            "bill_date": _tally_date(_text(b.find("BILLDATE"))),
            "due_date": _tally_date(_text(b.find("BILLDUEDATE"))
                                    or _text(b.find("BILLCL"))),
            "amount": abs(_amount(_text(b.find("BILLAMT"))
                                  or _text(b.find("CLOSINGBALANCE")))),
            "kind": "receivable" if receivable else "payable",
        })
    if not out:
        # Different Tally builds name the outstanding collection differently;
        # fall back to the generic bill list rather than returning nothing.
        for b in root.iter("BILL"):
            out.append({
                "party": _text(b.find("PARTYNAME")),
                "bill_no": _text(b.find("NAME")),
                "bill_date": _tally_date(_text(b.find("BILLDATE"))),
                "due_date": _tally_date(_text(b.find("BILLDUEDATE"))),
                "amount": abs(_amount(_text(b.find("CLOSINGBALANCE")))),
                "kind": "receivable" if receivable else "payable",
            })
    return out


def fetch_trial_balance(client: TallyClient, as_on: date,
                        company: str | None = None) -> list[dict]:
    root = client.post(_export("Trial Balance", company, from_date=as_on, to_date=as_on))
    out = []
    for d in root.iter("DSPACCNAME"):
        pass  # structure varies by build; the ledger collection is authoritative
    for led in root.iter("LEDGER"):
        out.append({
            "name": led.get("NAME") or _text(led.find("NAME")),
            "closing_balance": _amount(_text(led.find("CLOSINGBALANCE"))),
        })
    return out
