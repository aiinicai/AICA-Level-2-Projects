"""HTTP client for the local TallyPrime XML server (default http://127.0.0.1:9000).

``DemoTallyClient`` has the same interface and simulates Tally so the whole
pipeline can be exercised without TallyPrime running.
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime

import httpx

from app.tally.response_parser import parse_xml

logger = logging.getLogger("brmco.tally")

MASTER_COLLECTIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    # master_type: (Tally collection TYPE, native methods to fetch)
    "ledger": ("Ledger", ("Name", "Parent")),
    "group": ("Group", ("Name", "Parent")),
    "stock_item": ("StockItem", ("Name", "Parent", "BaseUnits")),
    "unit": ("Unit", ("Name",)),
    "voucher_type": ("VoucherType", ("Name", "Parent")),
}


class TallyConnectionError(Exception):
    """Tally is not reachable (not running, wrong port, XML server disabled)."""


@dataclass
class TallyStatus:
    connected: bool
    message: str
    url: str
    companies: list[str] = field(default_factory=list)
    demo: bool = False


def decode_response(content: bytes) -> str:
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        return content.decode("utf-16")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


@dataclass
class CompanyInfo:
    name: str
    books_from: date | None
    educational_mode: bool


def _tally_date(text: str | None) -> date | None:
    try:
        return datetime.strptime((text or "").strip(), "%Y%m%d").date()
    except ValueError:
        return None


def parse_company_info(text: str) -> list[CompanyInfo]:
    root = parse_xml(text)
    if root is None:
        return []
    out = []
    for c in root.iter("COMPANY"):
        name = element_name(c)
        if name:  # skips the <CMPINFO><COMPANY>1</COMPANY> counter
            out.append(CompanyInfo(name, _tally_date(c.findtext("BOOKSFROM")),
                                   (c.findtext("LICMODE") or "").strip().lower() == "yes"))
    return out


def collection_request(collection_id: str, tally_type: str, methods: tuple[str, ...], company: str = "",
                       computes: tuple[str, ...] = ()) -> bytes:
    env = ET.Element("ENVELOPE")
    h = ET.SubElement(env, "HEADER")
    ET.SubElement(h, "VERSION").text = "1"
    ET.SubElement(h, "TALLYREQUEST").text = "Export"
    ET.SubElement(h, "TYPE").text = "Collection"
    ET.SubElement(h, "ID").text = collection_id
    desc = ET.SubElement(ET.SubElement(env, "BODY"), "DESC")
    static = ET.SubElement(desc, "STATICVARIABLES")
    ET.SubElement(static, "SVEXPORTFORMAT").text = "$$SysName:XML"
    if company:
        ET.SubElement(static, "SVCURRENTCOMPANY").text = company
    coll = ET.SubElement(ET.SubElement(ET.SubElement(desc, "TDL"), "TDLMESSAGE"), "COLLECTION",
                         {"NAME": collection_id, "ISMODIFY": "No"})
    ET.SubElement(coll, "TYPE").text = tally_type
    for m in methods:
        ET.SubElement(coll, "NATIVEMETHOD").text = m
    for c in computes:
        ET.SubElement(coll, "COMPUTE").text = c
    return ET.tostring(env, encoding="utf-8")


def element_name(el: ET.Element) -> str:
    name = el.get("NAME")
    if not name:
        child = el.find("NAME.LIST/NAME")
        if child is None:
            child = el.find("NAME")
        name = child.text if child is not None else ""
    return (name or "").strip()


def parse_collection(text: str, tally_type: str) -> list[dict[str, str | None]]:
    root = parse_xml(text)
    if root is None:
        raise ValueError("Tally returned an unreadable master list.")
    tag = tally_type.upper()
    out: list[dict[str, str | None]] = []
    for el in root.iter(tag):
        name = element_name(el)
        if not name:
            continue
        parent = el.findtext("PARENT")
        base_units = el.findtext("BASEUNITS")
        out.append({"name": name, "parent": (parent or "").strip() or None,
                    "unit": (base_units or "").strip() or None})
    return out


class TallyClient:
    demo = False

    def __init__(self, url: str, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout

    def post(self, xml: bytes) -> str:
        try:
            resp = httpx.post(self.url, content=xml, timeout=httpx.Timeout(self.timeout, connect=5.0),
                              headers={"Content-Type": "text/xml; charset=utf-8"})
        # On Windows a closed port often surfaces as a connect *timeout*, not a refusal.
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise TallyConnectionError(
                f"Cannot connect to Tally at {self.url}. Make sure TallyPrime is open, a company is loaded, "
                "and Tally's XML server is enabled on this port (F1 > Settings > Connectivity).") from exc
        except httpx.TimeoutException as exc:
            raise TallyConnectionError(f"Tally at {self.url} did not respond within {self.timeout:.0f} seconds.") from exc
        except httpx.HTTPError as exc:
            raise TallyConnectionError(f"Communication with Tally failed: {exc}") from exc
        text = decode_response(resp.content)
        logger.info("Tally %s -> HTTP %s, %d bytes", self.url, resp.status_code, len(text))
        if resp.status_code >= 400:
            raise TallyConnectionError(f"Tally returned HTTP {resp.status_code}.")
        return text

    def status(self) -> TallyStatus:
        try:
            text = self.post(collection_request("BRMCoCompanies", "Company", ("Name",)))
        except TallyConnectionError as exc:
            return TallyStatus(False, str(exc), self.url)
        root = parse_xml(text)
        if root is None:
            if re.search(r"tally", text, re.I):
                return TallyStatus(True, "Tally is running but returned an unexpected reply.", self.url)
            return TallyStatus(False, f"A server is running at {self.url} but it does not look like TallyPrime.",
                               self.url)
        companies = [element_name(c) for c in root.iter("COMPANY") if element_name(c)]
        if not companies:
            return TallyStatus(True, "Connected to Tally, but no company is open.", self.url)
        return TallyStatus(True, f"Connected. Open companies: {', '.join(companies)}", self.url, companies)

    def fetch_masters(self, master_type: str, company: str = "") -> list[dict[str, str | None]]:
        tally_type, methods = MASTER_COLLECTIONS[master_type]
        text = self.post(collection_request(f"BRMCo{tally_type}s", tally_type, methods, company))
        return parse_collection(text, tally_type)

    def company_info(self) -> list[CompanyInfo]:
        """Open companies with their books-beginning date, plus the licence mode (read-only)."""
        text = self.post(collection_request(
            "BRMCoCompanyInfo", "Company", ("Name", "BooksFrom", "StartingFrom"),
            computes=("LicMode:$$LicenseInfo:IsEducationalMode",)))
        return parse_company_info(text)


# --------------------------------------------------------------------------- demo
DEMO_COMPANY = "BRMCo Demo Company"
DEMO_MASTERS: dict[str, list[dict[str, str | None]]] = {
    "group": [
        {"name": n, "parent": p} for n, p in (
            ("Sundry Debtors", None), ("Sundry Creditors", None), ("Sales Accounts", None),
            ("Purchase Accounts", None), ("Duties & Taxes", None), ("Indirect Expenses", None),
            ("Indirect Incomes", None), ("Bank Accounts", None), ("Cash-in-Hand", None),
            ("Capital Account", None), ("Current Liabilities", None), ("Provisions", "Current Liabilities"),
        )
    ],
    "ledger": [
        {"name": n, "parent": p} for n, p in (
            ("ABC Traders", "Sundry Debtors"), ("XYZ Enterprises", "Sundry Debtors"),
            ("Global Exports Pvt Ltd", "Sundry Debtors"), ("Sharma Suppliers", "Sundry Creditors"),
            ("Metro Office Supplies", "Sundry Creditors"), ("Sales @ 18%", "Sales Accounts"),
            ("Sales @ 5%", "Sales Accounts"), ("Sales - Services", "Sales Accounts"),
            ("Purchase @ 18%", "Purchase Accounts"), ("Office Expenses", "Indirect Expenses"),
            ("Rent", "Indirect Expenses"), ("Salary", "Indirect Expenses"), ("Bank Charges", "Indirect Expenses"),
            ("Salary Payable", "Provisions"), ("Output CGST", "Duties & Taxes"), ("Output SGST", "Duties & Taxes"),
            ("Output IGST", "Duties & Taxes"), ("Output Cess", "Duties & Taxes"), ("Input CGST", "Duties & Taxes"),
            ("Input SGST", "Duties & Taxes"), ("Input IGST", "Duties & Taxes"), ("Input Cess", "Duties & Taxes"),
            ("Round Off", "Indirect Expenses"), ("HDFC Bank", "Bank Accounts"), ("ICICI Bank", "Bank Accounts"),
            ("Cash", "Cash-in-Hand"), ("Capital A/c", "Capital Account"),
        )
    ],
    "stock_item": [
        {"name": "Steel Rod 12mm", "parent": "Primary", "unit": "Kg"},
        {"name": "Office Chair", "parent": "Primary", "unit": "Nos"},
    ],
    "unit": [{"name": n, "parent": None} for n in ("Nos", "Kg", "Pcs", "Box", "Ltr")],
    "voucher_type": [{"name": n, "parent": n} for n in ("Sales", "Purchase", "Journal", "Receipt", "Payment",
                                                         "Contra", "Credit Note", "Debit Note")],
}


# Ledgers "created" in the demo company during this run of the app (kept in memory only).
DEMO_CREATED_LEDGERS: list[dict[str, str | None]] = []


class DemoTallyClient:
    """Simulates TallyPrime. Nothing is posted anywhere."""

    demo = True

    def __init__(self) -> None:
        self.url = "demo://tally"

    @property
    def _ledgers(self) -> set[str]:
        return {m["name"].lower() for m in DEMO_MASTERS["ledger"] + DEMO_CREATED_LEDGERS}  # type: ignore[union-attr]

    def status(self) -> TallyStatus:
        return TallyStatus(True, f"DEMO MODE — simulated Tally with company '{DEMO_COMPANY}'.", self.url,
                           [DEMO_COMPANY], demo=True)

    def company_info(self) -> list[CompanyInfo]:
        return [CompanyInfo(DEMO_COMPANY, date(2020, 4, 1), False)]

    def fetch_masters(self, master_type: str, company: str = "") -> list[dict[str, str | None]]:
        extra = DEMO_CREATED_LEDGERS if master_type == "ledger" else []
        return [dict(m) for m in DEMO_MASTERS[master_type] + extra]

    def post(self, xml: bytes) -> str:
        """Mimics Tally: creates ledgers; rejects vouchers that use unknown ledgers or don't balance."""
        root = ET.fromstring(xml)
        created, errors, line_errors = 0, 0, []
        groups = {g["name"].lower() for g in DEMO_MASTERS["group"]}  # type: ignore[union-attr]
        for led in root.iter("LEDGER"):
            name = led.get("NAME") or ""
            parent = led.findtext("PARENT") or ""
            if name.lower() in self._ledgers:
                errors += 1
                line_errors.append(f"Ledger '{name}' already exists!")
            elif parent.lower() not in groups:
                errors += 1
                line_errors.append(f"Group '{parent}' does not exist!")
            else:
                DEMO_CREATED_LEDGERS.append({"name": name, "parent": parent})
                created += 1
        for vch in root.iter("VOUCHER"):
            problems = []
            total = 0.0
            for tag in ("ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST", "ACCOUNTINGALLOCATIONS.LIST"):
                for entry in vch.iter(tag):
                    name = entry.findtext("LEDGERNAME") or ""
                    if name.lower() not in self._ledgers:
                        problems.append(f"Ledger '{name}' does not exist!")
                    total += float(entry.findtext("AMOUNT") or 0)
            if abs(total) > 0.005:
                problems.append("Voucher totals do not match!")
            if problems:
                errors += 1
                line_errors.extend(problems)
            else:
                created += 1
        body = "".join(f"<LINEERROR>{e}</LINEERROR>" for e in line_errors)
        return (f"<RESPONSE><CREATED>{created}</CREATED><ALTERED>0</ALTERED><DELETED>0</DELETED>"
                f"<LASTVCHID>{1000 + created if created else 0}</LASTVCHID><LASTMID>0</LASTMID>"
                f"<COMBINED>0</COMBINED><IGNORED>0</IGNORED><ERRORS>{errors}</ERRORS>"
                f"<CANCELLED>0</CANCELLED><EXCEPTIONS>0</EXCEPTIONS>{body}</RESPONSE>")
