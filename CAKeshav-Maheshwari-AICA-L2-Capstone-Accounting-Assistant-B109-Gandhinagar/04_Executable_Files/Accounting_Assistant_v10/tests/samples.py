"""Synthetic invoices (no real client data) in several layouts and file formats."""
from pathlib import Path

COMPANY_GSTIN = "24AAACL1234F1Z5"      # buyer (our company, Gujarat)
SUPPLIER_GJ = "24ABCPS1234K1ZS"        # Gujarat supplier
SUPPLIER_MH = "27AAACL1234F1ZZ"        # Maharashtra supplier

INTRA = f"""
                         TAX INVOICE
Shree Stationers
12, Ashram Road, Ahmedabad 380009
GSTIN: {SUPPLIER_GJ}            PAN: ABCPS1234K
Invoice No: SS/2026/0457                 Invoice Date: 05-11-2026
Buyer: Aarohan Infotech Private Limited
GSTIN/UIN: {COMPANY_GSTIN}
Place of Supply: 24-Gujarat               Reverse Charge: No

Sr  Description              HSN/SAC   Qty   Rate      Amount
1   A4 Copier Paper 75 GSM   4802      20    250.00    5,000.00
2   Toner Cartridge          8443      2     2,500.00  5,000.00

                                   Taxable Value      10,000.00
                                   CGST @ 9%            900.00
                                   SGST @ 9%            900.00
                                   Round Off              0.00
                                   Grand Total        11,800.00
Amount in words: Rupees Eleven Thousand Eight Hundred Only
Bank: HDFC Bank  A/c No: 50200012345678  IFSC: HDFC0001234
"""

INTER = f"""
Cloudnine Software Solutions Pvt Ltd
Andheri East, Mumbai 400069   GSTIN {SUPPLIER_MH}
TAX INVOICE
Inv No. CN-1182                                      Dated 28/10/2026
Bill To: Aarohan Infotech Private Limited, Ahmedabad   GSTIN {COMPANY_GSTIN}
Place of Supply : Gujarat (24)
Particulars                         SAC        Amount
Annual software subscription        997331     24,500.00
Implementation support              998313      5,000.00
Sub Total                                       29,500.00
IGST 18%                                         5,310.00
Rounded off                                         -0.00
Total Invoice Value                             34,810.00
"""

BAD_TOTAL = INTRA.replace("Grand Total        11,800.00", "Grand Total        11,900.00")
WRONG_TAX_TYPE = INTER.replace(f"GSTIN {SUPPLIER_MH}", f"GSTIN {SUPPLIER_GJ}")


def write_pdf(text: str, path: Path) -> Path:
    from PyQt6.QtCore import QMarginsF
    from PyQt6.QtGui import QFont, QPageLayout, QPageSize, QPainter, QPdfWriter
    w = QPdfWriter(str(path))
    w.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    w.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
    p = QPainter(w)
    f = QFont("Courier New")
    f.setPointSize(9)
    p.setFont(f)
    y = 200
    for line in text.splitlines():
        p.drawText(100, y, line)
        y += 220
    p.end()
    return path


def write_docx(text: str, path: Path) -> Path:
    import zipfile
    from xml.sax.saxutils import escape
    paras = "".join(f'<w:p><w:r><w:t xml:space="preserve">{escape(l)}</w:t></w:r></w:p>' for l in text.splitlines())
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w='
           '"http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + paras + "</w:body></w:document>")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
                   'officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("word/document.xml", doc)
    return path


def write_xlsx(text: str, path: Path) -> Path:
    import re
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    for line in text.splitlines():
        ws.append([c for c in re.split(r"\s{3,}", line.strip()) if c] or [""])
    wb.save(path)
    return path

# Layout as printed by Tally: labels in a box with the value on the NEXT line, an HSN tax summary
# table, a mobile number and a bank account on the page, total line with Rs symbol.
TALLY_STYLE = f"""
                                  Tax Invoice
S K AGENCIES                                   Invoice No.            Dated
14, Industrial Estate, Naroda                  SKP/1125/26-27         6-Nov-2026
Ahmedabad - 382330                             Delivery Note          Mode/Terms of Payment
Mob: 6112010419                                                       30 Days
GSTIN/UIN: {SUPPLIER_GJ}
State Name : Gujarat, Code : 24
Buyer (Bill to)
Aarohan Infotech Private Limited
GSTIN/UIN : {COMPANY_GSTIN}
Sl   Description of Goods        HSN/SAC     Quantity      Rate       per    Amount
1    Corrugated Boxes 5 Ply      48191010    4,000 Nos     59.035     Nos    2,36,140.00
                                                    CGST @ 9%                 21,252.60
                                                    SGST @ 9%                 21,252.60
                                                    Round Off                     (-)0.20
     Total                                        4,000 Nos               ₹ 2,78,645.00
Amount Chargeable (in words)
INR Two Lakh Seventy Eight Thousand Six Hundred Forty Five Only
HSN/SAC        Taxable        Central Tax          State Tax           Total
               Value          Rate    Amount       Rate    Amount      Tax Amount
48191010       2,36,140.00    9%      21,252.60    9%      21,252.60   42,505.20
Total          2,36,140.00            21,252.60            21,252.60   42,505.20
Company's Bank Details  A/c No. : 920020045671234   IFSC : UTIB0001234
"""

# Utility bill without GST lines: labels and values on separate lines, many other numbers around.
UTILITY = """
TORRENT POWER LIMITED                      Ahmedabad
Service No: 1100234567                     Unit No: 41
Bill No                Bill Date            Due Date
TP/26/0098123          04/11/2026           18/11/2026
Units consumed: 1,284      Connected load 15.00 kW
Energy charges                                  9,630.00
Fixed charges                                   1,050.00
Electricity duty                                1,602.00
Net Amount Payable                             12,282.00
Payable after due date                         12,404.82
"""
