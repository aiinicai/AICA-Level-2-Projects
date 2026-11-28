"""Read Tally masters into IPT (read-only towards Tally)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation

from ipt.services.tally.client import TallyClient, first_text

# Tally reserved primary groups (the 28 predefined groups); ledgers are classified by these.
PRIMARY_GROUPS = {
    "Branch / Divisions", "Capital Account", "Current Assets", "Current Liabilities", "Direct Expenses",
    "Direct Incomes", "Fixed Assets", "Indirect Expenses", "Indirect Incomes", "Investments", "Loans (Liability)",
    "Misc. Expenses (ASSET)", "Purchase Accounts", "Sales Accounts", "Suspense A/c", "Bank Accounts",
    "Bank OD A/c", "Cash-in-Hand", "Deposits (Asset)", "Duties & Taxes", "Loans & Advances (Asset)",
    "Provisions", "Reserves & Surplus", "Secured Loans", "Stock-in-Hand", "Sundry Creditors", "Sundry Debtors",
    "Unsecured Loans",
}

SPECS = {
    # master_type: (Tally TYPE, element tag, FETCH)
    "group": ("Group", "GROUP", "NAME, PARENT"),
    "ledger": ("Ledger", "LEDGER", "NAME, PARENT, GUID, PARTYGSTIN, LEDGSTREGDETAILS.LIST"),
    "stock_item": ("StockItem", "STOCKITEM", "NAME, PARENT, GUID, BASEUNITS, GSTDETAILS.LIST, HSNDETAILS.LIST"),
    "unit": ("Unit", "UNIT", "NAME"),
    "godown": ("Godown", "GODOWN", "NAME, PARENT"),
    "voucher_type": ("VoucherType", "VOUCHERTYPE", "NAME, PARENT"),
    "cost_centre": ("CostCentre", "COSTCENTRE", "NAME, PARENT"),
}


def _name(el: ET.Element) -> str:
    return (el.get("NAME") or first_text(el, "NAME", "NAME.LIST/NAME", "LANGUAGENAME.LIST/NAME.LIST/NAME")).strip()


def _rate(el: ET.Element) -> Decimal | None:
    for path in (".//RATEDETAILS.LIST[GSTRATEDUTYHEAD='IGST']/GSTRATE", ".//GSTRATE"):
        try:
            v = first_text(el, path)
            if v:
                return Decimal(v)
        except InvalidOperation:
            continue
    return None


def fetch_masters(client: TallyClient, company: str, master_type: str) -> list[dict]:
    obj, tag, fetch = SPECS[master_type]
    root = client.collection(f"IPT{obj}s", obj, fetch, company=company)
    rows = []
    for el in root.iter(tag):
        name = _name(el)
        if not name:
            continue
        row = {"name": name, "parent": first_text(el, "PARENT"), "guid": first_text(el, "GUID"), "gstin": "",
               "hsn": "", "gst_rate": None, "base_unit": ""}
        if master_type == "ledger":
            g = first_text(el, "PARTYGSTIN", "LEDGSTREGDETAILS.LIST/GSTIN")
            row["gstin"] = g.upper() if re.fullmatch(r"[0-9A-Z]{15}", g.upper()) else ""
        if master_type == "stock_item":
            row["base_unit"] = first_text(el, "BASEUNITS")
            row["hsn"] = first_text(el, ".//HSNCODE", ".//HSN")[:10]
            row["gst_rate"] = _rate(el)
        rows.append(row)
    return rows


def primary_group_of(parent: str, groups: dict[str, str]) -> str:
    """Walk up the group tree until a reserved primary group is reached."""
    seen = set()
    cur = parent
    while cur and cur not in PRIMARY_GROUPS and cur not in seen:
        seen.add(cur)
        cur = groups.get(cur, "")
    return cur or parent
