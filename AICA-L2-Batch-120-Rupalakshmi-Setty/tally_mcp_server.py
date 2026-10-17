"""
Ledger Sentinel - Live Tally MCP Server (Step 10, optional/stretch)

Exposes Tally Prime's Day Book as MCP tools so Claude (or any MCP client)
can pull live voucher data directly from a running Tally Prime instance,
instead of a manual Export > Excel step.

STRICTLY READ-ONLY BY DESIGN
-----------------------------
Tally's local XML/HTTP gateway accepts two kinds of request: "Export Data"
(read) and "Import Data" (write - creates/modifies vouchers). This server
only ever sends "Export Data" requests. The helper that builds the request
envelope hardcodes TALLYREQUEST to "Export Data" and there is no code path
anywhere in this file that can construct an Import request. This is the
"agent pulls the Day Book itself, set to read-only, with no write
permissions" design called for in the project plan.

PREREQUISITES ON THE TALLY PRIME SIDE
--------------------------------------
1. Open the company in Tally Prime.
2. Press F1 (Help) > Settings > Connectivity > Client/Server configuration.
3. Set "Tally is Acting as" to "Both" (or "Server"), and note the port
   (default 9000). Leave it running while this MCP server is used.
4. Keep the target company open/loaded in Tally during the session.

KNOWN LIMITATION - PLEASE READ
-------------------------------
The standard Day Book XML export returns transaction data (date, ledger
accounts, amount, narration, voucher number) but does NOT include the
edit-log fields (altered_by, altered_date) that several Ledger Sentinel
rules depend on (same-user-create-alter, old-voucher-late-edit). Those
fields live in Tally's audit/edit-log feature and are not exposed through
this basic report in every Tally Prime version. Two rules in the rules
engine will therefore under-fire on live data pulled this way until a
version-specific audit-log export is confirmed and wired in separately.
State this openly in your presentation rather than presenting live-pulled
data as a complete substitute for the synthetic edit-log dataset.

VERIFIED LIVE (2026-10-15): the request format below has been tested
against a real running TallyPrime instance ("Gulf Emirates Trading &
Distribution LLC") and confirmed working - TallyPrime returned
<STATUS>1</STATUS> (success) for a Day Book export request with the
correct company name and date range. That test company had no vouchers
posted yet, so the returned <DATA> was empty, but the connection, the
request shape, and the company targeting are all confirmed correct.
Before your demo, re-run this against a company that actually has
vouchers posted, to see real rows come back - and adjust SVCURRENTCOMPANY
to match your company's exact name (TallyPrime is picky about an exact,
case-sensitive match).

Run as a standalone MCP server:
    python tally_mcp_server.py

Then register it with your MCP client (e.g. Claude Desktop / Claude Code)
pointing at this script - see README.md for the config snippet.
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from mcp.server.fastmcp import FastMCP

TALLY_URL = "http://localhost:9000"  # Tally's default XML/HTTP gateway port
REQUEST_TIMEOUT = 30

mcp = FastMCP("tally-ledger-sentinel")


# TallyPrime's XML export contains control characters that are not legal
# under the XML 1.0 spec, in two forms: (a) raw control bytes, and (b) literal
# numeric character references like "&#4;" that DECODE to an illegal control
# character. Python's parser rejects both with "reference to invalid
# character number" / "not well-formed". Strip both before parsing.
_INVALID_XML_CHARS_RE = re.compile(
    "[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]"
)
_DEC_CHARREF_RE = re.compile(r"&#(\d+);")
_HEX_CHARREF_RE = re.compile(r"&#x([0-9A-Fa-f]+);")


def _is_valid_xml_codepoint(cp: int) -> bool:
    return cp in (0x9, 0xA, 0xD) or (0x20 <= cp <= 0xD7FF) or (0xE000 <= cp <= 0xFFFD)


def _sanitize_xml(text: str) -> str:
    text = _DEC_CHARREF_RE.sub(lambda m: m.group(0) if _is_valid_xml_codepoint(int(m.group(1))) else "", text)
    text = _HEX_CHARREF_RE.sub(lambda m: m.group(0) if _is_valid_xml_codepoint(int(m.group(1), 16)) else "", text)
    return _INVALID_XML_CHARS_RE.sub("", text)


def _post_to_tally(xml_envelope: str) -> str:
    """Send a request envelope to Tally and return the raw XML response,
    sanitized of invalid control characters Tally sometimes embeds.
    Only ever called with Export Data envelopes built by this file."""
    resp = requests.post(
        TALLY_URL,
        data=xml_envelope.encode("utf-8"),
        headers={"Content-Type": "text/xml"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return _sanitize_xml(resp.text)


def _xml_escape(s) -> str:
    """Escape XML special characters - company/account names can contain '&' etc."""
    s = str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _build_export_envelope(report_name: str, static_vars: dict) -> str:
    """Build a READ-ONLY export request envelope. There is no equivalent
    helper for an import/write request anywhere in this file.

    VERIFIED 2026-10-15 against a live TallyPrime instance: this is the
    envelope shape TallyPrime's XML/HTTP gateway actually expects
    (VERSION / TALLYREQUEST=Export / TYPE=Data / ID=<report name>, with
    STATICVARIABLES under <DESC>). An earlier version of this file used
    the older <EXPORTDATA><REQUESTDESC><REPORTNAME> shape, which this
    TallyPrime version did not recognise - it returned a confusing
    unrelated 'Import Data' / 'All Masters' echo instead of an error.
    That older shape has been replaced with this proven one."""
    sv_xml = "".join(f"<{k}>{_xml_escape(v)}</{k}>" for k, v in static_vars.items())
    return f"""<ENVELOPE>
 <HEADER>
  <VERSION>1</VERSION>
  <TALLYREQUEST>Export</TALLYREQUEST>
  <TYPE>Data</TYPE>
  <ID>{report_name}</ID>
 </HEADER>
 <BODY>
  <DESC>
   <STATICVARIABLES>
    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
    {sv_xml}
   </STATICVARIABLES>
  </DESC>
 </BODY>
</ENVELOPE>"""


@mcp.tool()
def check_tally_connection() -> str:
    """Check whether Tally Prime's XML/HTTP gateway is reachable on localhost:9000.
    Read-only ping - sends a minimal Export Data request and reports success/failure."""
    try:
        envelope = _build_export_envelope("List of Companies", {})
        _post_to_tally(envelope)
        return json.dumps({"status": "connected", "url": TALLY_URL})
    except requests.exceptions.ConnectionError:
        return json.dumps({
            "status": "unreachable",
            "message": (
                "Could not reach Tally at localhost:9000. Confirm Tally Prime is open, "
                "a company is loaded, and F1 > Settings > Connectivity has the HTTP "
                "gateway enabled (Tally is Acting as: Both or Server)."
            ),
        })
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def list_tally_companies() -> str:
    """List companies currently open in Tally Prime (read-only)."""
    envelope = _build_export_envelope("List of Companies", {})
    raw = _post_to_tally(envelope)
    try:
        root = ET.fromstring(raw)
        names = [el.text for el in root.iter() if el.tag.upper() in ("NAME", "COMPANYNAME") and el.text]
        return json.dumps({"companies": list(dict.fromkeys(names))})
    except ET.ParseError:
        return json.dumps({"raw_response": raw[:2000], "note": "Could not parse as XML - returning raw text for inspection."})


@mcp.tool()
def export_daybook(from_date: str, to_date: str, company_name: str = "") -> str:
    """
    Export the Day Book for a date range directly from Tally Prime (read-only).

    Args:
        from_date: start date as YYYYMMDD (e.g. "20250101")
        to_date: end date as YYYYMMDD (e.g. "20251231")
        company_name: exact company name as shown in Tally (optional - uses
            the currently active company in Tally if left blank)

    Returns a JSON string: {"vouchers": [ {date, voucher_id, debit_account,
    credit_account, amount, narration}, ... ], "count": N,
    "limitation_note": "..."}

    NOTE: altered_by / altered_date are not included - see the module
    docstring's "KNOWN LIMITATION" section.
    """
    static_vars = {"SVFROMDATE": from_date, "SVTODATE": to_date}
    if company_name:
        static_vars["SVCURRENTCOMPANY"] = company_name

    envelope = _build_export_envelope("Day Book", static_vars)
    raw = _post_to_tally(envelope)

    vouchers = []
    try:
        root = ET.fromstring(raw)
        for v in root.iter("VOUCHER"):
            date_raw = v.findtext("DATE", default="")
            date_fmt = ""
            if len(date_raw) == 8:
                date_fmt = f"{date_raw[0:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
            voucher_id = v.findtext("VOUCHERNUMBER", default="") or v.get("REMOTEID", "")
            narration = v.findtext("NARRATION", default="")

            debit_account, credit_account, amount = "", "", 0.0
            for entry in v.iter("ALLLEDGERENTRIES.LIST"):
                ledger = entry.findtext("LEDGERNAME", default="")
                amt_text = entry.findtext("AMOUNT", default="0")
                is_debit = entry.findtext("ISDEEMEDPOSITIVE", default="No") == "Yes"
                try:
                    amt_val = abs(float(amt_text))
                except ValueError:
                    amt_val = 0.0
                if is_debit:
                    debit_account = ledger
                    amount = amt_val
                else:
                    credit_account = ledger

            vouchers.append({
                "voucher_id": voucher_id,
                "date": date_fmt,
                "debit_account": debit_account,
                "credit_account": credit_account,
                "amount": amount,
                "narration": narration,
            })
    except ET.ParseError as exc:
        return json.dumps({
            "error": f"Could not parse Tally's XML response: {exc}",
            "raw_response_preview": raw[:2000],
        })

    return json.dumps({
        "vouchers": vouchers,
        "count": len(vouchers),
        "limitation_note": (
            "altered_by and altered_date are not available via the standard Day Book "
            "export - the 'same user create/alter' and 'old voucher late edit' rules "
            "will not fire correctly on this data until a version-specific audit-log "
            "export is added."
        ),
        "fetched_at": datetime.now().isoformat(),
    })


@mcp.tool()
def export_daybook_to_excel(from_date: str, to_date: str, output_path: str, company_name: str = "") -> str:
    """
    Same as export_daybook, but writes the result straight to an Excel file
    in the same column layout as tally_daybook_export.xlsx, so it can be fed
    directly into rules_engine.py. Read-only on the Tally side.

    Args:
        from_date: start date as YYYYMMDD
        to_date: end date as YYYYMMDD
        output_path: where to save the .xlsx file, e.g. "live_daybook_export.xlsx"
        company_name: exact Tally company name (optional)
    """
    import pandas as pd

    result = json.loads(export_daybook(from_date, to_date, company_name))
    if "error" in result:
        return json.dumps(result)

    rows = result["vouchers"]
    for r in rows:
        r.setdefault("time", "")
        r.setdefault("day_of_week", "")
        r.setdefault("created_by", "")
        r.setdefault("created_by_name", "")
        r.setdefault("altered_by", "")
        r.setdefault("altered_date", "")

    df = pd.DataFrame(rows, columns=[
        "voucher_id", "date", "time", "day_of_week", "created_by", "created_by_name",
        "altered_by", "altered_date", "debit_account", "credit_account", "amount", "narration",
    ])
    df.to_excel(output_path, index=False, engine="openpyxl")
    return json.dumps({
        "saved_to": output_path,
        "rows_written": len(df),
        "limitation_note": result["limitation_note"],
    })


if __name__ == "__main__":
    mcp.run()
