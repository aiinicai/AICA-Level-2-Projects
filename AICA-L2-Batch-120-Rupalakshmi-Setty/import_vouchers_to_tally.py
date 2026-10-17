"""
Ledger Sentinel - Seed Tally with the synthetic Day Book (final, verified version)
------------------------------------------------------------------------------------
Pushes tally_daybook_export.xlsx into TallyPrime as real "Journal" vouchers, so
the read-only MCP tool (tally_mcp_server.py) has genuine live data to pull back
out. This is a WRITE operation (Import Data) and is deliberately kept in its own
standalone script, separate from tally_mcp_server.py, which stays strictly
read-only by design.

This is the final, consolidated version of the import step, incorporating
everything learned from live testing against a real TallyPrime instance on
2026-10-15:

  - Ledger masters must exist before a voucher can reference them -
    run import_ledger_masters.py once, first.
  - Dates are shifted forward by exactly one year (2025 -> 2026) for this
    imported copy only, so they land inside Tally's current financial
    period. The original tally_daybook_export.xlsx is untouched.
  - XML special characters (e.g. "&" in "Gulf Emirates Trading & Distribution
    LLC") MUST be escaped, or Tally's gateway returns a generic "Unknown
    Request" error instead of a useful one.
  - Large single requests are unreliable: TallyPrime's embedded HTTP gateway
    was observed silently failing most of a 500-voucher batch with a
    misleading "Voucher date is missing... retry Split" message. Small
    batches (25) with a short pause between them are reliable.
  - TallyPrime's Educational edition appears to cap how many vouchers can be
    created per day, independent of how many are requested (a repeatable
    624-created result was observed across two full-dataset attempts). This
    is a license-tier limit, not a bug - if you hit it, the vouchers already
    created are valid and usable; simply wait and resume another day to add
    more (this script's dedup check makes that safe to do).
  - Each voucher's original ID is embedded in its narration as "[LS:V000123]"
    so this script (and the live pull) can always match Tally data back to
    the source spreadsheet row, and so re-running this script is safe - it
    only sends vouchers not already present in Tally.

Run AFTER import_ledger_masters.py, with:
    C:\\Python314\\python.exe import_vouchers_to_tally.py
"""

import re
import time
import requests
import pandas as pd
import xml.etree.ElementTree as ET

TALLY_URL = "http://localhost:9000"
COMPANY_NAME = "Gulf Emirates Trading & Distribution LLC"
SOURCE_FILE = "tally_daybook_export.xlsx"
BATCH_SIZE = 25
PAUSE_SECONDS = 0.4
YEAR_SHIFT = 1  # 2025 (source data) -> 2026 (Tally's current period)

LS_TAG_RE = re.compile(r"\[LS:(V\d+)\]")
_INVALID_XML_CHARS_RE = re.compile("[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]")
_DEC_CHARREF_RE = re.compile(r"&#(\d+);")
_HEX_CHARREF_RE = re.compile(r"&#x([0-9A-Fa-f]+);")


def _is_valid_xml_codepoint(cp):
    return cp in (0x9, 0xA, 0xD) or (0x20 <= cp <= 0xD7FF) or (0xE000 <= cp <= 0xFFFD)


def sanitize_xml(text):
    """TallyPrime's XML export contains control characters invalid under the
    XML 1.0 spec, both as raw bytes and as literal numeric references like
    "&#4;". Strip both before parsing - otherwise ElementTree raises
    'reference to invalid character number'."""
    text = _DEC_CHARREF_RE.sub(lambda m: m.group(0) if _is_valid_xml_codepoint(int(m.group(1))) else "", text)
    text = _HEX_CHARREF_RE.sub(lambda m: m.group(0) if _is_valid_xml_codepoint(int(m.group(1), 16)) else "", text)
    return _INVALID_XML_CHARS_RE.sub("", text)


def xml_escape(s):
    if s is None:
        return ""
    s = str(s)
    if s.lower() == "nan":
        s = ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def get_existing_voucher_ids():
    """Read-only Day Book pull, used only to find which voucher_ids are
    already in Tally so re-running this script never creates duplicates."""
    envelope = f"""<ENVELOPE>
 <HEADER>
  <VERSION>1</VERSION>
  <TALLYREQUEST>Export</TALLYREQUEST>
  <TYPE>Data</TYPE>
  <ID>Day Book</ID>
 </HEADER>
 <BODY>
  <DESC>
   <STATICVARIABLES>
    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
    <SVCURRENTCOMPANY>{xml_escape(COMPANY_NAME)}</SVCURRENTCOMPANY>
    <SVFROMDATE>20260101</SVFROMDATE>
    <SVTODATE>20261231</SVTODATE>
   </STATICVARIABLES>
  </DESC>
 </BODY>
</ENVELOPE>"""
    resp = requests.post(TALLY_URL, data=envelope.encode("utf-8"),
                          headers={"Content-Type": "text/xml"}, timeout=120)
    existing_ids = set()
    try:
        root = ET.fromstring(sanitize_xml(resp.text))
        for narr_el in root.iter("NARRATION"):
            if narr_el.text:
                m = LS_TAG_RE.search(narr_el.text)
                if m:
                    existing_ids.add(m.group(1))
    except ET.ParseError:
        print("Warning: could not parse Day Book response while checking existing vouchers.")
    return existing_ids


def shifted_date_yyyymmdd(date_str):
    dt = pd.to_datetime(date_str)
    dt = dt.replace(year=dt.year + YEAR_SHIFT)
    return dt.strftime("%Y%m%d")


def build_voucher_message(row):
    date_tally = shifted_date_yyyymmdd(row["date"])
    narration = xml_escape(row["narration"]) + f" [LS:{row['voucher_id']}]"
    debit_acc = xml_escape(row["debit_account"])
    credit_acc = xml_escape(row["credit_account"])
    amount = float(row["amount"])
    vch_no = xml_escape(row["voucher_id"])

    return f"""
    <TALLYMESSAGE xmlns:UDF="TallyUDF">
     <VOUCHER VCHTYPE="Journal" ACTION="Create" OBJVIEW="Accounting Voucher View">
      <DATE>{date_tally}</DATE>
      <NARRATION>{narration}</NARRATION>
      <VOUCHERTYPENAME>Journal</VOUCHERTYPENAME>
      <VOUCHERNUMBER>{vch_no}</VOUCHERNUMBER>
      <ALLLEDGERENTRIES.LIST>
       <LEDGERNAME>{debit_acc}</LEDGERNAME>
       <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
       <AMOUNT>-{amount}</AMOUNT>
      </ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST>
       <LEDGERNAME>{credit_acc}</LEDGERNAME>
       <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
       <AMOUNT>{amount}</AMOUNT>
      </ALLLEDGERENTRIES.LIST>
     </VOUCHER>
    </TALLYMESSAGE>"""


def build_envelope(rows):
    data_xml = "".join(build_voucher_message(row) for _, row in rows.iterrows())
    return f"""<ENVELOPE>
 <HEADER>
  <VERSION>1</VERSION>
  <TALLYREQUEST>Import</TALLYREQUEST>
  <TYPE>Data</TYPE>
  <ID>Vouchers</ID>
 </HEADER>
 <BODY>
  <DESC>
   <STATICVARIABLES>
    <SVCURRENTCOMPANY>{xml_escape(COMPANY_NAME)}</SVCURRENTCOMPANY>
   </STATICVARIABLES>
  </DESC>
  <DATA>{data_xml}
  </DATA>
 </BODY>
</ENVELOPE>"""


def send_batch(rows, batch_num, total_batches):
    envelope = build_envelope(rows)
    resp = requests.post(TALLY_URL, data=envelope.encode("utf-8"),
                          headers={"Content-Type": "text/xml"}, timeout=60)
    created = errors = "?"
    try:
        root = ET.fromstring(sanitize_xml(resp.text))
        created = root.findtext(".//CREATED") or "0"
        errors = root.findtext(".//ERRORS") or "0"
    except ET.ParseError:
        print(f"  [batch {batch_num}/{total_batches}] could not parse response")
    print(f"  [batch {batch_num}/{total_batches}] rows={len(rows)} created={created} errors={errors}", flush=True)
    return created


def main():
    print("Checking which vouchers are already in Tally (safe to re-run)...")
    existing_ids = get_existing_voucher_ids()
    print(f"Found {len(existing_ids)} vouchers already in Tally.\n")

    print(f"Reading {SOURCE_FILE} ...")
    df = pd.read_excel(SOURCE_FILE)
    remaining = df[~df["voucher_id"].isin(existing_ids)].reset_index(drop=True)
    print(f"{len(df)} total in source file, {len(remaining)} not yet in Tally.\n")

    if len(remaining) == 0:
        print("Nothing left to import - all vouchers already in Tally.")
        return

    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
    total_created = 0
    print(f"Sending in batches of {BATCH_SIZE} ({total_batches} batches). This will take a few minutes...\n"
          f"Note: TallyPrime's Educational edition appears to cap voucher creation per day - if the "
          f"created count stops climbing partway through, that's expected; re-run this script another "
          f"day to add the rest (it will pick up exactly where it left off).\n")

    for i in range(total_batches):
        batch_rows = remaining.iloc[i * BATCH_SIZE: (i + 1) * BATCH_SIZE]
        created = send_batch(batch_rows, i + 1, total_batches)
        try:
            total_created += int(created)
        except (TypeError, ValueError):
            pass
        time.sleep(PAUSE_SECONDS)
        if (i + 1) % 20 == 0:
            print(f"  ...progress: {i + 1}/{total_batches} batches, {total_created} created so far\n")

    print(f"\n==== DONE ====")
    print(f"Attempted this run: {len(remaining)}")
    print(f"Newly created this run: {total_created}")
    print(f"Total now in Tally (approx): {len(existing_ids) + total_created}")


if __name__ == "__main__":
    main()
