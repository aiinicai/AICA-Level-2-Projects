"""
Builds a standalone Tally master-import XML file for missing ledgers/voucher
types found by the readiness check.

Posting new masters over the live HTTP gateway (port 9000) reliably returns
CREATED=0, EXCEPTIONS=1 with no further detail on this installation -- some
Tally editions restrict master creation over that channel even when voucher
posting works fine. Tally's own Gateway of Tally -> Import Data -> Masters
menu is the fully-supported path for bulk master creation, so this module
produces a file for that menu instead of trying to POST it live.
"""
from __future__ import annotations

import datetime as dt
from xml.sax.saxutils import escape

# GST state code (first 2 digits of GSTIN) -> state name, per the CBIC list.
GST_STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "25": "Daman & Diu", "26": "Dadra & Nagar Haveli", "27": "Maharashtra",
    "28": "Andhra Pradesh (Old)", "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry", "35": "Andaman & Nicobar Islands",
    "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh", "97": "Other Territory",
}


def state_from_gstin(gstin: str | None) -> str | None:
    if not gstin or len(gstin) < 2:
        return None
    return GST_STATE_CODES.get(gstin[:2])


def _language_name_list(name: str) -> str:
    """Tally's importer resolves a master's actual name from this structure (it
    supports multi-language names) -- the NAME="..." XML attribute alone is used
    for addressing/lookup but is NOT sufficient for Create, and is silently
    rejected as 'Master name is missing' without it."""
    return f"""
      <LANGUAGENAME.LIST>
        <NAME.LIST TYPE="String">
          <NAME>{escape(name)}</NAME>
        </NAME.LIST>
        <LANGUAGEID TYPE="Number">1033</LANGUAGEID>
      </LANGUAGENAME.LIST>
    """


def ledger_fragment(name: str, parent: str, gstin: str | None = None, state: str | None = None) -> str:
    """GST registration details do NOT go in flat PARTYGSTIN/GSTREGISTRATIONTYPE/
    STATENAME tags -- verified against a real GST-registered vendor ledger's
    exported XML that those top-level tags are always empty. The actual values
    live in a nested LEDGSTREGDETAILS.LIST, which also requires APPLICABLEFROM
    (a date) and PLACEOFSUPPLY or the whole allocation is silently dropped;
    state uses PRIORSTATENAME."""
    extra = ""
    if gstin:
        applicable_from = dt.date.today().strftime("%Y%m%d")
        extra += f"""
    <LEDGSTREGDETAILS.LIST>
      <APPLICABLEFROM>{applicable_from}</APPLICABLEFROM>
      <GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>
      <PLACEOFSUPPLY>{escape(state or "")}</PLACEOFSUPPLY>
      <GSTIN>{escape(gstin)}</GSTIN>
    </LEDGSTREGDETAILS.LIST>
        """
    if state:
        extra += f"<PRIORSTATENAME>{escape(state)}</PRIORSTATENAME>"
    return f"""
    <LEDGER NAME="{escape(name)}" ACTION="Create">
      <PARENT>{escape(parent)}</PARENT>
      <ISBILLWISEON>Yes</ISBILLWISEON>
      {_language_name_list(name)}
      {extra}
    </LEDGER>
    """


def voucher_type_fragment(name: str, parent: str = "Purchase") -> str:
    return f"""
    <VOUCHERTYPE NAME="{escape(name)}" ACTION="Create">
      <PARENT>{escape(parent)}</PARENT>
      <NUMBERINGMETHOD>Auto</NUMBERINGMETHOD>
      {_language_name_list(name)}
    </VOUCHERTYPE>
    """


def build_masters_file(fragments: list[str]) -> str:
    """Wraps master-creation fragments into a file Tally's own
    Gateway of Tally -> Import Data -> Masters menu can consume directly."""
    body = "\n".join(fragments)
    return f"""<ENVELOPE>
 <HEADER>
  <TALLYREQUEST>Import Data</TALLYREQUEST>
 </HEADER>
 <BODY>
  <IMPORTDATA>
   <REQUESTDESC>
    <REPORTNAME>All Masters</REPORTNAME>
   </REQUESTDESC>
   <REQUESTDATA>
    <TALLYMESSAGE xmlns:UDF="TallyUDF">
{body}
    </TALLYMESSAGE>
   </REQUESTDATA>
  </IMPORTDATA>
 </BODY>
</ENVELOPE>
"""
