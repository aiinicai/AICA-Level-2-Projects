"""Regenerates the Excel templates and sample upload files in ./samples  (python make_samples.py)"""
import os

from app import gst
from app.uploads import CHALLAN_COLS, VENDOR_COLS, template_book

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
os.makedirs(OUT, exist_ok=True)

G = lambda st, pan: gst.make_gstin(st, pan)
VENDORS = [
    ("Apex Calibration Services", "Plot 7, Sector 10, PCNTDA Bhosari, Pune", "Maharashtra", "411026", G("27", "AAGCA4521D"), "Mr. Deshmukh", "9800000001", "lab@apex-cal.example", ""),
    ("Bharat Packaging Solutions", "22 Industrial Area Phase 1, Chandigarh", "Chandigarh", "160002", G("04", "AAHFB7812K"), "Ms. Kaur", "9800000002", "", ""),
    ("Cobalt Machine Works", "Survey 41, GIDC Estate, Vadodara", "Gujarat", "390010", G("24", "AACCC3309M"), "Mr. Patel", "9800000003", "", "V20077"),
    ("Delta Sister Entity Pvt Ltd", "Building 3, Electronic City, Bengaluru", "Karnataka", "560100", G("29", "AAACD9087H"), "Admin desk", "9800000004", "", ""),
    ("Unregistered Local Fabricator", "Shed 4, Chakan, Pune", "27", "410501", "", "Mr. Jadhav", "9800000005", "", ""),
]
HDR = [f for _, f in CHALLAN_COLS]


def row(**kw):
    base = dict(ctype="MNRC", status="FINAL", plant="PNQ1", uom="NOS", cess_rate=0, tax_rate=18, line_no=1)
    base.update(kw)
    return [base.get(f, "") for f in HDR]


V = [v[4] for v in VENDORS]
CHALLANS = [
    row(ctype="MRC", number="MRC/25-26/0001", date="10-06-2025", vendor=V[0], purpose="Calibration", reason="Calibrator not yet created in ERP",
        corrective_action="Create vendor in ERP", corrective_owner="Purchase", corrective_target_date="30-06-2025", expected_return_date="10-07-2025",
        goods_category="CAPITAL", transport_mode="Road", vehicle_no="MH12AB1234", ewb_no="341000000001", ewb_date="10-06-2025", ewb_valid_upto="11-06-2025",
        part_no="CMM-PRB-01", description="CMM probe", hsn="9031", qty=1, rate=45000, qty_received=1),
    row(ctype="MRC", number="MRC/25-26/0002", date="02-09-2025", vendor=V[1], purpose="Returnable packing", reason="New customer, ERP vendor pending",
        corrective_action="Create vendor in ERP", corrective_owner="Sales ops", corrective_target_date="30-09-2025", expected_return_date="02-12-2025",
        goods_category="INPUTS", part_no="PLT-01", description="Wooden pallet", hsn="4415", qty=40, rate=800, ewb_no="341000000002", ewb_date="02-09-2025", ewb_valid_upto="03-09-2025", qty_received=25),
    row(ctype="MRC", number="MRC/25-26/0002", date="02-09-2025", vendor=V[1], purpose="Returnable packing", reason="New customer, ERP vendor pending",
        corrective_action="Create vendor in ERP", corrective_owner="Sales ops", corrective_target_date="30-09-2025", expected_return_date="02-12-2025",
        goods_category="INPUTS", line_no=2, part_no="PLT-02", description="Steel crate", hsn="7326", qty=10, rate=2500, ewb_no="341000000002", ewb_date="02-09-2025", ewb_valid_upto="03-09-2025", qty_received=0),
    row(number="MNRC/25-26/0001", date="14-07-2025", vendor=V[3], purpose="Return of sister-entity asset", reason="Laptop lent for project returned",
        part_no="LAP-1022", description="Laptop", hsn="8471", qty=1, rate=35000, ewb_no="341000000003", ewb_date="14-07-2025", ewb_valid_upto="15-07-2025"),
    row(number="MNRC/25-26/0002", date="20-08-2025", vendor=V[2], purpose="Return of customer material", reason="Rework completed; returning to owner",
        ref_doc_no="CUS-CH-5521", ref_doc_date="01-08-2025", part_no="CST-77", description="Casting after rework", hsn="7325", qty=60, rate=420,
        ewb_no="341000000004", ewb_date="20-08-2025", ewb_valid_upto="21-08-2025"),
    row(number="MNRC/25-26/0003", date="25-08-2025", vendor=V[2], purpose="Other", purpose_text="Wrong party", reason="Raised in error",
        status="CANCELLED", cancel_reason="Issued to wrong consignee", part_no="X1", description="Item", hsn="8708", qty=1, rate=100),
]

import openpyxl
for kind in ("vendors", "challans"):
    template_book(kind).save(os.path.join(OUT, f"template_{kind}.xlsx"))
for kind, rows in (("vendors", VENDORS), ("challans", CHALLANS)):
    wb = template_book(kind)
    ws = wb.worksheets[0]
    for r in rows:
        ws.append(list(r))
    wb.save(os.path.join(OUT, f"sample_{kind}.xlsx"))
print("Samples written to", OUT)
