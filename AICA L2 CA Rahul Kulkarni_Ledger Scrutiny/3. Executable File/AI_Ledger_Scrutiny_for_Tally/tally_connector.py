"""
tally_connector.py  -  Pull data directly from Tally (TallyPrime / Tally.ERP 9).

How it works
------------
Tally has a built-in XML server. When it is ON, any program can send an XML
request by HTTP POST to http://localhost:9000 and Tally replies with XML.
Enable it in TallyPrime:  F1 (Help) > Settings > Connectivity >
    "Client/Server configuration" -> TallyPrime acts as = Both / Server, Port = 9000
(Tally.ERP 9: Gateway > F12 Configure > Advanced Configuration.)
The company must be OPEN in Tally while the app fetches data.

This module returns three pandas DataFrames:
    groups   : name, parent
    ledgers  : name, parent, opening_balance  (+ve = Debit, -ve = Credit)
    entries  : one row per ledger line of every voucher
               voucher_id, date, voucher_type, voucher_no, narration, party,
               ledger, amount (always +ve), dr_cr ("Dr"/"Cr")
It can also parse an XML file exported from Tally (Day Book -> Export -> XML),
so the app works even without a live connection.
"""

import re
import xml.etree.ElementTree as ET
from datetime import date
from xml.sax.saxutils import escape

import pandas as pd
import requests

# Tally sometimes sends control characters that are illegal in XML
_BAD_XML = re.compile(r"&#(?:[0-8]|1[0-9]|2[0-9]|3[01]);|[\x00-\x08\x0b\x0c\x0e-\x1f]")


# ----------------------------------------------------------------- helpers
def _clean(xml_text: str) -> str:
    return _BAD_XML.sub("", xml_text)


def _num(text) -> float:
    """'1,250.00 Dr' / '-1250' / '' -> float.  Tally sign: negative = Debit."""
    if text is None:
        return 0.0
    t = str(text).strip().replace(",", "")
    if not t:
        return 0.0
    sign = 1
    if t.endswith("Dr"):
        sign, t = -1, t[:-2]
    elif t.endswith("Cr"):
        t = t[:-2]
    t = re.sub(r"[^\d.\-]", "", t.split("=")[-1]) or "0"
    try:
        return sign * float(t)
    except ValueError:
        return 0.0


def _date(text):
    t = (text or "").strip()
    if len(t) == 8 and t.isdigit():
        return date(int(t[:4]), int(t[4:6]), int(t[6:]))
    try:
        return pd.to_datetime(t, dayfirst=True).date()
    except Exception:
        return None


def _txt(el, tag):
    child = el.find(tag)
    return (child.text or "").strip() if child is not None and child.text else ""


def _name(el):
    return (el.get("NAME") or _txt(el, "NAME") or _txt(el, "NAME.LIST/NAME")).strip()


def _tally_date(d) -> str:
    return pd.to_datetime(d).strftime("%Y%m%d")


# ------------------------------------------------------------ XML requests
def _collection_request(coll_id, obj_type, fetch, company=None,
                        from_date=None, to_date=None, filter_formula=None):
    company_tag = f"<SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY>" if company else ""
    period = ""
    if from_date and to_date:
        period = (f"<SVFROMDATE>{_tally_date(from_date)}</SVFROMDATE>"
                  f"<SVTODATE>{_tally_date(to_date)}</SVTODATE>")
    filt, system = "", ""
    if filter_formula:
        filt = "<FILTER>AppFilter</FILTER>"
        system = f'<SYSTEM TYPE="Formulae" NAME="AppFilter">{escape(filter_formula)}</SYSTEM>'
    return f"""<ENVELOPE>
 <HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>
  <TYPE>Collection</TYPE><ID>{coll_id}</ID></HEADER>
 <BODY><DESC>
  <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{company_tag}{period}</STATICVARIABLES>
  <TDL><TDLMESSAGE>
   <COLLECTION NAME="{coll_id}" ISMODIFY="No"><TYPE>{obj_type}</TYPE>
    <FETCH>{fetch}</FETCH>{filt}</COLLECTION>{system}
  </TDLMESSAGE></TDL>
 </DESC></BODY>
</ENVELOPE>"""


class TallyConnector:
    def __init__(self, host="http://localhost", port=9000, timeout=120):
        self.url = f"{host.rstrip('/')}:{port}"
        self.timeout = timeout

    def _post(self, xml: str) -> ET.Element:
        r = requests.post(self.url, data=xml.encode("utf-8"),
                          headers={"Content-Type": "text/xml;charset=utf-8"},
                          timeout=self.timeout)
        r.raise_for_status()
        text = r.content.decode("utf-8", errors="ignore")
        return ET.fromstring(_clean(text))

    # -- connection test & company list
    def is_alive(self) -> bool:
        try:
            r = requests.get(self.url, timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def companies(self):
        root = self._post(_collection_request("AppCompanies", "Company", "Name"))
        return sorted({_name(c) for c in root.iter("COMPANY") if _name(c)})

    # -- masters
    def groups(self, company=None) -> pd.DataFrame:
        root = self._post(_collection_request("AppGroups", "Group", "Name, Parent", company))
        return parse_groups(root)

    def ledgers(self, company=None) -> pd.DataFrame:
        root = self._post(_collection_request(
            "AppLedgers", "Ledger", "Name, Parent, OpeningBalance", company))
        return parse_ledgers(root)

    # -- vouchers
    def vouchers(self, company=None, from_date=None, to_date=None) -> pd.DataFrame:
        fetch = ("Date, VoucherTypeName, VoucherNumber, Narration, PartyLedgerName, GUID, "
                 "IsCancelled, IsOptional, AllLedgerEntries, LedgerEntries, AllInventoryEntries")
        formula = "$Date >= ##SVFromDate AND $Date <= ##SVToDate" if from_date else None
        root = self._post(_collection_request(
            "AppVouchers", "Voucher", fetch, company, from_date, to_date, formula))
        df = parse_vouchers(root)
        if from_date is not None and not df.empty:      # safety filter in Python too
            df = df[(df["date"] >= pd.to_datetime(from_date).date()) &
                    (df["date"] <= pd.to_datetime(to_date).date())]
        return df.reset_index(drop=True)

    def fetch_all(self, company=None, from_date=None, to_date=None):
        return (self.groups(company), self.ledgers(company),
                self.vouchers(company, from_date, to_date))


# ----------------------------------------------------------------- parsers
def parse_groups(root) -> pd.DataFrame:
    rows = [{"name": _name(g), "parent": _txt(g, "PARENT")} for g in root.iter("GROUP")]
    return pd.DataFrame(rows, columns=["name", "parent"]).drop_duplicates("name")


def parse_ledgers(root) -> pd.DataFrame:
    rows = [{"name": _name(l), "parent": _txt(l, "PARENT"),
             "opening_balance": _num(_txt(l, "OPENINGBALANCE")) * -1}  # make +ve = Dr
            for l in root.iter("LEDGER")]
    df = pd.DataFrame(rows, columns=["name", "parent", "opening_balance"])
    return df[df["name"] != ""].drop_duplicates("name")


def _ledger_lines(v):
    """Yield (ledger, signed_amount) from every place Tally may keep them."""
    seen = False
    for tag in ("ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST"):
        for le in v.findall(tag):
            seen = True
            yield _txt(le, "LEDGERNAME"), _num(_txt(le, "AMOUNT"))
        if seen:
            break
    # invoice-mode vouchers: sales/purchase ledger sits inside inventory allocations
    for inv in v.findall("ALLINVENTORYENTRIES.LIST") + v.findall("INVENTORYENTRIES.LIST"):
        for acc in inv.findall("ACCOUNTINGALLOCATIONS.LIST"):
            yield _txt(acc, "LEDGERNAME"), _num(_txt(acc, "AMOUNT"))


def parse_vouchers(root) -> pd.DataFrame:
    rows = []
    for i, v in enumerate(root.iter("VOUCHER")):
        if _txt(v, "ISCANCELLED") == "Yes" or _txt(v, "ISOPTIONAL") == "Yes":
            continue
        vid = _txt(v, "GUID") or f"V{i}"
        base = {
            "voucher_id": vid,
            "date": _date(_txt(v, "DATE")),
            "voucher_type": _txt(v, "VOUCHERTYPENAME") or v.get("VCHTYPE", ""),
            "voucher_no": _txt(v, "VOUCHERNUMBER"),
            "narration": _txt(v, "NARRATION"),
            "party": _txt(v, "PARTYLEDGERNAME"),
        }
        for ledger, amt in _ledger_lines(v):
            if not ledger or amt == 0:
                continue
            rows.append({**base, "ledger": ledger, "amount": abs(amt),
                         "dr_cr": "Dr" if amt < 0 else "Cr"})
    cols = ["voucher_id", "date", "voucher_type", "voucher_no", "narration",
            "party", "ledger", "amount", "dr_cr"]
    return pd.DataFrame(rows, columns=cols)


def parse_xml_file(file_bytes: bytes):
    """Parse a Tally XML export (Day Book / Masters).  Returns groups, ledgers, entries."""
    if file_bytes[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00<" in file_bytes[:200]:
        text = file_bytes.decode("utf-16", errors="ignore")      # Tally often exports UTF-16
    else:
        text = file_bytes.decode("utf-8-sig", errors="ignore")
    text = re.sub(r"^\s*<\?xml[^>]*\?>", "", text)
    root = ET.fromstring(_clean(text))
    return parse_groups(root), parse_ledgers(root), parse_vouchers(root)
