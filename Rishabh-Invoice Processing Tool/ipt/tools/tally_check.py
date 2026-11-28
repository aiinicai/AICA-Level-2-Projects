"""Read-only Tally diagnostic. Run with tally_check.bat.

Checks the connection, lists open companies, counts masters and saves the raw
XML of two existing purchase vouchers so IPT's voucher builder can mirror the
exact structure your Tally uses. Nothing is written to Tally.
"""
from __future__ import annotations

import sys
from pathlib import Path

from ipt.services.tally.client import TallyClient, TallyError
from ipt.services.tally.masters import SPECS, fetch_masters, primary_group_of

OUT = Path(__file__).resolve().parents[2] / "tally_check_output"


def main(argv: list[str]) -> int:
    host, port = "localhost", 9000
    company = argv[1] if len(argv) > 1 else None
    OUT.mkdir(exist_ok=True)
    cl = TallyClient(host, port, timeout=60)
    try:
        print("Server:", cl.ping())
        comps = cl.companies()
    except TallyError as e:
        print("ERROR:", e)
        return 1
    print("Open companies:", [c["name"] for c in comps])
    if not comps:
        print("No company is open in Tally.")
        return 1
    company = company or comps[0]["name"]
    print("Using company:", company)
    groups = {g["name"]: g["parent"] for g in fetch_masters(cl, company, "group")}
    for t in ([] if "--vouchers-only" in argv else SPECS):
        rows = fetch_masters(cl, company, t)
        print(f"{t}: {len(rows)}")
        if t == "ledger":
            for pg in ("Purchase Accounts", "Duties & Taxes", "Indirect Expenses", "Sundry Creditors"):
                names = [r["name"] for r in rows if primary_group_of(r["parent"], groups) == pg]
                print(f"  {pg}: {len(names)} e.g. {names[:15]}")
            with_gstin = [r for r in rows if r["gstin"]]
            print(f"  ledgers with GSTIN: {len(with_gstin)} e.g. {[(r['name'], r['gstin']) for r in with_gstin[:5]]}")
        if t in ("stock_item", "unit", "godown", "voucher_type"):
            print("  e.g.", [(r["name"], r["base_unit"], r["hsn"], str(r["gst_rate"])) if t == "stock_item"
                             else r["name"] for r in rows[:15]])
    # existing purchase vouchers of one day (Day Book export = the same structure Tally imports)
    xml = ("<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC>"
           "<REPORTNAME>Day Book</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
           f"<SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY><SVFROMDATE TYPE=\"Date\">20250401</SVFROMDATE>"
           '<SVTODATE TYPE="Date">20250401</SVTODATE><SVCURRENTDATE TYPE="Date">20250401</SVCURRENTDATE>'
           "</STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>")
    cl.timeout = 180
    try:
        raw = cl.post(xml)
    except TallyError as e:
        print("Could not read purchase vouchers:", e)
        return 1
    # keep only the first two VOUCHER elements to keep the file small
    import re
    vouchers = [v for v in re.findall(r"<VOUCHER[ >].*?</VOUCHER>", raw, re.S) if 'VCHTYPE="Purchase"' in v[:400]]
    print("purchase vouchers on 01-04-2025:", len(vouchers))
    (OUT / "sample_purchase_vouchers.xml").write_text("<SAMPLES>\n" + "\n".join(vouchers[:2]) + "\n</SAMPLES>",
                                                       encoding="utf-8")
    print("Saved", OUT / "sample_purchase_vouchers.xml")
    print("DONE (read-only, nothing was written to Tally)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
