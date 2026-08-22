"""
tally_sync.py
--------------
Best-effort auto-sync of saved invoices into Tally Prime via its built-in
HTTP/XML gateway (Gateway of Tally -> F11 -> Connectivity). No extra
libraries are required -- this uses only Python's standard library
(urllib) to POST XML to Tally, exactly like Tally's own XML import feature.

IMPORTANT -- please read before relying on this with real invoices:
  This integration was built without access to a live Tally Prime instance
  to test against (Tally was not yet enabled when this was written), so it
  follows Tally's well-documented XML import conventions but has NOT been
  verified end-to-end against a real company. Before using it for real
  invoices:
    1. Enable Tally's gateway (see README section 8).
    2. Set app/config.py's TALLY_COMPANY_NAME, ledger names, etc. to match
       your actual Tally setup exactly.
    3. Use "Test Tally Connection" from the app toolbar.
    4. Test on a DUMMY/TEST company in Tally first -- create one invoice,
       open Tally, and manually verify the voucher looks correct (correct
       party, correct debit/credit, correct GST ledgers) before trusting
       this against your real company data.
  The app never blocks or loses an invoice because of a Tally failure --
  invoices always save locally first; Tally sync is a best-effort add-on
  that reports success/failure clearly and can be retried.

How a sale is represented in Tally (Accounting Invoice, services only, no
stock items), per the firm's instructions:
  Dr  <Party ledger>                  <grand total, EXACT, unrounded>
  Cr  <Sales ledger>                       <subtotal>
  Cr  <Output CGST {rate}%> (if intra-state, per item rate)
  Cr  <Output SGST {rate}%> (if intra-state, per item rate)
  Cr  <Output IGST {rate}%> (if inter-state, per item rate)
No separate Round-Off ledger is posted (per the firm's instruction) -- the
party is debited with the exact pre-rounding total so the voucher balances.
"""

import http.client
import re
import socket
import urllib.request
import urllib.error
import xml.sax.saxutils as saxutils
from collections import defaultdict
from datetime import datetime

from app import config, utils


class TallySyncError(Exception):
    """Raised when Tally is unreachable or rejects the request."""


# ---------------------------------------------------------------------------
# Low-level XML POST
# ---------------------------------------------------------------------------
def _post_xml(xml_body: str, timeout: float = 10.0) -> str:
    url = f"http://{config.TALLY_HOST}:{config.TALLY_PORT}"
    data = xml_body.encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "text/xml; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise TallySyncError(
            f"Could not reach Tally at {config.TALLY_HOST}:{config.TALLY_PORT}. "
            f"Is Tally Prime running with the HTTP gateway enabled? ({e.reason})"
        ) from e
    except (http.client.HTTPException, socket.timeout) as e:
        raise TallySyncError(f"Tally did not respond in time: {e}") from e


def _xml_escape(text) -> str:
    return saxutils.escape(str(text if text is not None else ""))


# ---------------------------------------------------------------------------
# Connection test
# ---------------------------------------------------------------------------
def test_connection() -> (bool, str):
    """Returns (ok, message). Sends a minimal, harmless request (no data
    changes) just to confirm Tally answers on the configured host/port."""
    probe = (
        "<ENVELOPE><HEADER><VERSION>1</VERSION>"
        "<TALLYREQUEST>Export Data</TALLYREQUEST>"
        "<TYPE>Data</TYPE><ID>List of Companies</ID></HEADER>"
        "<BODY><DESC><STATICVARIABLES>"
        "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
        "</STATICVARIABLES></DESC></BODY></ENVELOPE>"
    )
    try:
        response = _post_xml(probe, timeout=6.0)
    except TallySyncError as e:
        return False, str(e)
    if not response.strip():
        return False, "Tally responded, but with an empty reply -- check the gateway settings."
    return True, "Connected to Tally successfully."


# ---------------------------------------------------------------------------
# Party name normalisation (so e.g. "Pvt Ltd" vs "Private Limited" match)
# ---------------------------------------------------------------------------
def normalize_party_name(name: str) -> str:
    n = (name or "").strip().lower()
    n = re.sub(r"[.,]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    for suffix in sorted(config.TALLY_NAME_SUFFIXES_TO_IGNORE, key=len, reverse=True):
        suffix_clean = suffix.replace(".", "").strip()
        pattern = r"\s*" + re.escape(suffix_clean) + r"\s*$"
        n = re.sub(pattern, "", n).strip()
    return n


# ---------------------------------------------------------------------------
# GST ledger name resolution
# ---------------------------------------------------------------------------
def _gst_ledger_breakup(computed: dict) -> list:
    """Return [(ledger_name, amount), ...] for CGST/SGST/IGST, grouped by
    rate, based on config's ledger-name templates. Amounts are summed per
    distinct rate across all line items (most invoices use one rate, but
    mixed-rate invoices are handled too)."""
    intra = computed.get("is_intra_state")
    per_rate_cgst = defaultdict(float)
    per_rate_sgst = defaultdict(float)
    per_rate_igst = defaultdict(float)

    for item in computed.get("items", []):
        rate = utils.format_gst_rate(item.get("gst_percent", 0))
        half_rate = utils.format_gst_rate(float(item.get("gst_percent", 0)) / 2)
        if intra:
            per_rate_cgst[half_rate] += item.get("cgst", 0)
            per_rate_sgst[half_rate] += item.get("sgst", 0)
        else:
            per_rate_igst[rate] += item.get("igst", 0)

    entries = []
    for rate, amt in per_rate_cgst.items():
        if amt:
            entries.append((config.TALLY_CGST_LEDGER_TEMPLATE.format(rate=rate), round(amt, 2)))
    for rate, amt in per_rate_sgst.items():
        if amt:
            entries.append((config.TALLY_SGST_LEDGER_TEMPLATE.format(rate=rate), round(amt, 2)))
    for rate, amt in per_rate_igst.items():
        if amt:
            entries.append((config.TALLY_IGST_LEDGER_TEMPLATE.format(rate=rate), round(amt, 2)))
    return entries


# ---------------------------------------------------------------------------
# Party ledger auto-create (safe no-op if it already exists)
# ---------------------------------------------------------------------------
def _party_ledger_create_xml(customer: dict) -> str:
    name = customer.get("name", "").strip()
    address = _xml_escape(customer.get("address", ""))
    gstin = _xml_escape(customer.get("gstin", ""))
    state_name = _xml_escape(customer.get("state_name", ""))

    return f"""
    <TALLYMESSAGE xmlns:UDF="TallyUDF">
      <LEDGER NAME="{_xml_escape(name)}" ACTION="Create">
        <NAME>{_xml_escape(name)}</NAME>
        <PARENT>{_xml_escape(config.TALLY_PARTY_GROUP)}</PARENT>
        <ADDRESS.LIST><ADDRESS>{address}</ADDRESS></ADDRESS.LIST>
        <STATENAME>{state_name}</STATENAME>
        <PARTYGSTIN>{gstin}</PARTYGSTIN>
        <ISBILLWISEON>Yes</ISBILLWISEON>
      </LEDGER>
    </TALLYMESSAGE>
    """


# ---------------------------------------------------------------------------
# Voucher XML
# ---------------------------------------------------------------------------
def _voucher_xml(invoice: dict, action: str) -> str:
    computed = invoice["computed"]
    customer = invoice["customer"]
    party_name = customer.get("name", "").strip()

    try:
        tally_date = datetime.strptime(invoice["invoice_date"], "%Y-%m-%d").strftime("%Y%m%d")
    except (KeyError, ValueError):
        tally_date = datetime.now().strftime("%Y%m%d")

    # Party is debited with the exact pre-rounding total (no Round Off
    # ledger is used, per the firm's instruction) so the voucher balances.
    party_amount = computed.get("grand_total_raw", computed.get("grand_total", 0))

    narration_parts = [item.get("particulars", "") for item in invoice.get("items", []) if item.get("particulars")]
    narration = _xml_escape("; ".join(narration_parts)[:500])

    ledger_entries = [
        f"""<ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{_xml_escape(party_name)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{party_amount:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""",
        f"""<ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{_xml_escape(config.TALLY_SALES_LEDGER)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{computed['subtotal']:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""",
    ]
    for ledger_name, amount in _gst_ledger_breakup(computed):
        ledger_entries.append(f"""<ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{_xml_escape(ledger_name)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{amount:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")

    return f"""
    <TALLYMESSAGE xmlns:UDF="TallyUDF">
      <VOUCHER VCHTYPE="{_xml_escape(config.TALLY_VOUCHER_TYPE)}" ACTION="{action}">
        <DATE>{tally_date}</DATE>
        <VOUCHERTYPENAME>{_xml_escape(config.TALLY_VOUCHER_TYPE)}</VOUCHERTYPENAME>
        <VOUCHERNUMBER>{_xml_escape(invoice['invoice_number'])}</VOUCHERNUMBER>
        <PARTYLEDGERNAME>{_xml_escape(party_name)}</PARTYLEDGERNAME>
        <NARRATION>{narration}</NARRATION>
        {''.join(ledger_entries)}
      </VOUCHER>
    </TALLYMESSAGE>
    """


def build_import_xml(invoice: dict, action: str = "Create", include_party_create: bool = True) -> str:
    """Build the full <ENVELOPE> for creating/altering a sales voucher for
    `invoice`. Exposed separately so the GUI can offer a "Preview XML"
    (dry-run) option before actually sending anything to Tally."""
    messages = []
    if include_party_create:
        messages.append(_party_ledger_create_xml(invoice["customer"]))
    messages.append(_voucher_xml(invoice, action))

    return f"""<ENVELOPE>
 <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
 <BODY>
  <IMPORTDATA>
   <REQUESTDESC>
    <REPORTNAME>Vouchers</REPORTNAME>
    <STATICVARIABLES>
     <SVCURRENTCOMPANY>{_xml_escape(config.TALLY_COMPANY_NAME)}</SVCURRENTCOMPANY>
    </STATICVARIABLES>
   </REQUESTDESC>
   <REQUESTDATA>
    {''.join(messages)}
   </REQUESTDATA>
  </IMPORTDATA>
 </BODY>
</ENVELOPE>"""


def _parse_response_summary(response_xml: str) -> dict:
    def _extract(tag):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", response_xml)
        return m.group(1) if m else None

    errors = re.findall(r"<LINEERROR>(.*?)</LINEERROR>", response_xml)
    return {
        "created": _extract("CREATED"),
        "altered": _extract("ALTERED"),
        "exceptions": _extract("EXCEPTIONS"),
        "errors": _extract("ERRORS"),
        "line_errors": errors,
    }


# ---------------------------------------------------------------------------
# Public entry point used by the GUI
# ---------------------------------------------------------------------------
def sync_invoice(invoice: dict, is_edit: bool) -> dict:
    """
    Push `invoice` (already run through utils.compute_invoice_totals under
    invoice["computed"]) into Tally as a Create (new) or Alter (edit)
    voucher. Never raises for ordinary failures -- returns a dict:
        {"ok": bool, "message": str, "raw_response": str or None}
    so the caller can show a clear status without ever blocking the
    (already-successful) local JSON save.
    """
    if not config.TALLY_SYNC_ENABLED:
        return {"ok": False, "message": "Tally sync is disabled in app/config.py (TALLY_SYNC_ENABLED = False).", "raw_response": None}

    action = "Alter" if is_edit else "Create"
    xml_body = build_import_xml(invoice, action=action, include_party_create=True)

    try:
        response = _post_xml(xml_body)
    except TallySyncError as e:
        return {"ok": False, "message": str(e), "raw_response": None}

    summary = _parse_response_summary(response)
    if summary["line_errors"]:
        return {
            "ok": False,
            "message": "Tally reported an error: " + "; ".join(summary["line_errors"]),
            "raw_response": response,
        }
    if summary["errors"] and summary["errors"] != "0":
        return {
            "ok": False,
            "message": f"Tally reported {summary['errors']} error(s). Open Tally's Import log for details.",
            "raw_response": response,
        }

    created = summary["created"] or "0"
    altered = summary["altered"] or "0"
    if created == "0" and altered == "0":
        return {
            "ok": False,
            "message": "Tally did not confirm the voucher was created or altered -- please verify manually in Tally.",
            "raw_response": response,
        }

    verb = "created" if action == "Create" else "altered"
    return {"ok": True, "message": f"Voucher {verb} in Tally successfully.", "raw_response": response}
