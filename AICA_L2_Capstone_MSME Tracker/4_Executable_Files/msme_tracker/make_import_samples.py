"""Create sample import files in demo_data/import_samples (needs reportlab only for the PDF sample)."""
import io
from pathlib import Path

import pandas as pd

out = Path("demo_data/import_samples"); out.mkdir(parents=True, exist_ok=True)

# 1. Vendor's own statement (Excel, preamble + Debit/Credit + running balance)
rows = [["Sri Lakshmi Plastics"], ["Statement of Account - Led Lum Lighting Solutions LLP"], ["01-04-2026 to 30-09-2026"], [],
        ["Date", "Particulars", "Vch No", "Debit", "Credit", "Balance"],
        ["01-04-2026", "Opening Balance", None, 0, None, 0],
        ["05-04-2026", "Sales Invoice", "SL/001", 59000, None, 59000],
        ["28-04-2026", "Receipt NEFT against SL/001", "UTR7781", None, 59000, 0],
        ["10-06-2026", "Sales Invoice", "SL/002", 118000, None, 118000],
        ["02-07-2026", "Sales Invoice", "SL/003", 47200, None, 165200],
        ["20-07-2026", "Receipt TReDS against SL/002", "TR-55", None, 118000, 47200],
        ["15-08-2026", "Credit Note", "CN/01", None, 2200, 45000],
        ["30-09-2026", "Total", None, 224200, 179200, None]]
pd.DataFrame(rows).to_excel(out / "vendor_statement_sri_lakshmi.xlsx", index=False, header=False)

# 2. Export from accounting software (CSV, multi-vendor, Voucher Type + Amount)
exp = pd.DataFrame([
    ["2026-05-03", "Kaveri Packaging", "Purchase", "KP-101", 82600, "Cartons"],
    ["2026-05-30", "Kaveri Packaging", "Payment", "PV-20", 82600, "Paid against KP-101 NEFT"],
    ["2026-06-12", "Kaveri Packaging", "Purchase", "KP-102", 41300, "Cartons"],
    ["2026-06-20", "Anand Die Casting", "Purchase", "AD-77", 177000, "Die cast parts"],
    ["2026-07-25", "Anand Die Casting", "Payment", "PV-31", 100000, "Part payment AD-77"],
], columns=["Voucher Date", "Supplier Name", "Voucher Type", "Voucher No", "Amount", "Narration"])
exp.to_csv(out / "software_export_purchases.csv", index=False)

# 3. Text-based PDF statement
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    t = Table([["Date", "Particulars", "Ref No", "Debit", "Credit", "Balance"],
               ["05-05-2026", "Sales Invoice", "KP-201", "35,400.00", "", "35,400.00"],
               ["02-06-2026", "Receipt NEFT KP-201", "UTR55", "", "35,400.00", "0.00"],
               ["14-07-2026", "Sales Invoice", "KP-202", "59,000.00", "", "59,000.00"]])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    SimpleDocTemplate(str(out / "vendor_statement_kaveri.pdf"), pagesize=A4).build(
        [Paragraph("Kaveri Packaging - Statement of Account", getSampleStyleSheet()["Title"]), t])
except ImportError:
    print("reportlab not installed - PDF sample skipped")
print("Samples in", out.resolve())
