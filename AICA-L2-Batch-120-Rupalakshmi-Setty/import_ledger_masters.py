"""
Ledger Sentinel - ONE-TIME SEED SCRIPT (Step: live demo data upload)
----------------------------------------------------------------------
Pushes the 27 ledger accounts used by the synthetic Day Book into Tally
as ledger masters, under Tally's own built-in default groups. This is a
WRITE operation (Import Data) - deliberately kept in its own standalone
script, separate from tally_mcp_server.py, which stays strictly
read-only by design.

Run this ONCE, before import_vouchers_from_excel.py.

Run with:
    C:\\Python314\\python.exe import_ledger_masters.py
"""

import requests
import xml.etree.ElementTree as ET

TALLY_URL = "http://localhost:9000"
COMPANY_NAME = "Gulf Emirates Trading & Distribution LLC"

# account_name -> Tally's built-in default parent group (no custom groups needed)
LEDGERS = {
    "Sales - Domestic": "Sales Accounts",
    "Sales - Export": "Sales Accounts",
    "Purchase - Domestic": "Purchase Accounts",
    "Purchase - Import": "Purchase Accounts",
    "Inventory": "Current Assets",
    "Accounts Receivable": "Sundry Debtors",
    "Accounts Payable": "Sundry Creditors",
    "Bank - ADCB Current": "Bank Accounts",
    "Bank - ENBD Current": "Bank Accounts",
    "Cash in Hand": "Cash-in-Hand",
    "VAT Output": "Duties & Taxes",
    "VAT Input": "Duties & Taxes",
    "Salaries Expense": "Indirect Expenses",
    "Rent Expense": "Indirect Expenses",
    "Utilities Expense": "Indirect Expenses",
    "Freight & Logistics": "Direct Expenses",
    "Marketing Expense": "Indirect Expenses",
    "Office Supplies": "Indirect Expenses",
    "Suspense Account": "Suspense A/c",
    "Miscellaneous Expense": "Misc. Expenses (Asset)",
    "Commission Expense": "Indirect Expenses",
    "Bad Debts": "Indirect Expenses",
    "Depreciation": "Indirect Expenses",
    "Interest Expense": "Indirect Expenses",
    "Director's Loan": "Loans (Liability)",
    "Retained Earnings": "Reserves & Surplus",
    "Capital Account": "Capital Account",
}


def xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_envelope():
    messages = []
    for name, parent in LEDGERS.items():
        n = xml_escape(name)
        p = xml_escape(parent)
        messages.append(f"""
    <TALLYMESSAGE xmlns:UDF="TallyUDF">
     <LEDGER NAME="{n}" ACTION="Create">
      <NAME>{n}</NAME>
      <PARENT>{p}</PARENT>
     </LEDGER>
    </TALLYMESSAGE>""")
    data_xml = "".join(messages)

    return f"""<ENVELOPE>
 <HEADER>
  <VERSION>1</VERSION>
  <TALLYREQUEST>Import</TALLYREQUEST>
  <TYPE>Data</TYPE>
  <ID>All Masters</ID>
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


def main():
    envelope = build_envelope()
    print(f"Sending {len(LEDGERS)} ledger masters to Tally at {TALLY_URL} ...")
    resp = requests.post(TALLY_URL, data=envelope.encode("utf-8"),
                          headers={"Content-Type": "text/xml"}, timeout=60)
    print("HTTP status:", resp.status_code)
    print()
    print("---- Tally's response ----")
    print(resp.text[:3000])

    try:
        root = ET.fromstring(resp.text)
        created = root.findtext(".//CREATED")
        altered = root.findtext(".//ALTERED")
        errors = root.findtext(".//ERRORS")
        exceptions = root.findtext(".//EXCEPTIONS")
        print()
        print("---- Summary ----")
        print("Created:", created, "| Altered:", altered, "| Errors:", errors, "| Exceptions:", exceptions)
        line_errors = [el.text for el in root.iter("LINEERROR") if el.text]
        if line_errors:
            print("Line errors reported:")
            for le in line_errors:
                print(" -", le)
    except ET.ParseError:
        print("(Could not parse response as XML - see raw text above)")


if __name__ == "__main__":
    main()
