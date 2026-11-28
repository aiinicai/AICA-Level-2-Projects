"""Read-only: find which Tally request returns vouchers of a given date (Day Book date handling)."""
from __future__ import annotations

import re
import sys

from ipt.services.tally.client import TallyClient, esc

company, day, ddmmy = sys.argv[1], sys.argv[2], sys.argv[3]   # "Majisa Lime Product" 20261021 21-Oct-2026
cl = TallyClient(timeout=120)
variants = {
    "daybook_plain": f"<SVFROMDATE>{day}</SVFROMDATE><SVTODATE>{day}</SVTODATE>",
    "daybook_typed": f'<SVFROMDATE TYPE="Date">{day}</SVFROMDATE><SVTODATE TYPE="Date">{day}</SVTODATE>',
    "daybook_typed_cur": f'<SVFROMDATE TYPE="Date">{day}</SVFROMDATE><SVTODATE TYPE="Date">{day}</SVTODATE>'
                         f'<SVCURRENTDATE TYPE="Date">{day}</SVCURRENTDATE>',
    "daybook_text_dates": f'<SVFROMDATE TYPE="Date">{ddmmy}</SVFROMDATE><SVTODATE TYPE="Date">{ddmmy}</SVTODATE>',
}
for name, dates in variants.items():
    xml = ("<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC>"
           "<REPORTNAME>Day Book</REPORTNAME><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
           f"<SVCURRENTCOMPANY>{esc(company)}</SVCURRENTCOMPANY>{dates}</STATICVARIABLES></REQUESTDESC></EXPORTDATA>"
           "</BODY></ENVELOPE>")
    try:
        raw = cl.post(xml)
        dates_found = sorted(set(re.findall(r"<DATE>(\d{8})</DATE>", raw)))
        refs = re.findall(r"<REFERENCE>(.*?)</REFERENCE>", raw)
        print(name, "vouchers:", len(re.findall(r"<VOUCHER[ >]", raw)), "dates:", dates_found[:5], "refs:", refs[:5])
    except Exception as e:  # noqa: BLE001
        print(name, "ERROR", e)
print("DONE (read-only)")
