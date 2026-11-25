"""Generate FICTIONAL test documents for the PQR Traders AY 2026-27 case
(mirrors the project's fictional knowledge-base case). Not real client data.

Outputs to sample_data/:
  notice_143_2_PQR.docx        text notice (DOCX)
  notice_143_2_PQR.pdf         text-layer PDF
  notice_143_2_PQR_scanned.pdf image-only PDF (exercises OCR)
  bank_statement_PQR.xlsx      bank statement (credits ₹28,00,000)
  bank_book_PQR.xlsx           bank book incl. duplicate NEFT25071502 posting
  cash_book_PQR.xlsx           cash book
  sales_ledger_PQR.xlsx        sales ledger (cash sales ₹9,50,000)
  ais_PQR.xlsx                 AIS-style extract (fictional)
  debtor_ledger_PQR.xlsx       debtor roll-forward (Customer W omitted from prior-year ledger)
  source_mapping_PQR.csv       management's proposed deposit source mapping
"""
from __future__ import annotations

import csv
import io
import pathlib
import sys

OUT = pathlib.Path(__file__).resolve().parent.parent / "sample_data"
FICTION = "FICTIONAL TEST DATA – NOT A REAL NOTICE OR CLIENT RECORD"

NOTICE = f"""{FICTION}
GOVERNMENT OF INDIA
INCOME TAX DEPARTMENT
National Faceless Assessment Centre

To,
PQR Traders
(Fictional address withheld)
PAN: AAAFP1234Z

DIN & Notice No: ITBA/AST/S/143(2)/2026-27/1000000001(1)
Dated: 10-11-2026
Assessment Year: 2026-27

Notice under section 143(2) of the Income-tax Act, 1961 — Limited Scrutiny

The return of income for Assessment Year 2026-27 has been selected for Limited Scrutiny. The issues identified are:
(a) Large cash deposits during the year; (b) Unsecured loans and other credits.

You are requested to furnish the following information and documents on or before 25-11-2026 through the e-proceedings facility:

1. Please explain the source of cash deposits aggregating Rs. 18,00,000 made in your bank account during FY 2025-26, and furnish the cash book and supporting evidence for each deposit.
2. Please furnish details of unsecured loans received during the year, including Rs. 1,50,000 received from Amit Verma, along with confirmation, PAN, ITR and bank statement of the lender to establish identity, creditworthiness and genuineness.
3. Please explain the credits of Rs. 2,50,000 stated to be advances received from customers and furnish confirmations from the customers.
4. Please reconcile the cash sales as per cash book with the sales as per sales ledger and furnish copies of invoices.
5. Please furnish details of capital introduced by partners in cash aggregating Rs. 3,00,000 and the source of such capital.

In case of failure to comply with this notice, the case may be proceeded under section 144 of the Income-tax Act, 1961 and penalty under section 272A(1)(d) may be initiated.

Assessment Unit, Income Tax Department
"""

BANK_ROWS = [  # date, narration, ref, debit, credit
    ("01-04-2025", "Opening balance", "", "", ""),
    ("10-05-2025", "UPI/CUSTOMER P/SALES", "UPI25051001", "", 200000),
    ("30-06-2025", "BY CASH DEPOSIT", "CSH25063001", "", 720000),
    ("15-07-2025", "NEFT/CUSTOMER Q/SALES", "NEFT25071502", "", 200000),
    ("05-08-2025", "NEFT/CUSTOMER A/ADVANCE", "NEFT25080504", "", 150000),
    ("31-08-2025", "BY CASH DEPOSIT", "CSH25083101", "", 400000),
    ("30-09-2025", "BY CASH DEPOSIT", "CSH25093001", "", 230000),
    ("20-10-2025", "NEFT/CUSTOMER R/SALES", "NEFT25102003", "", 200000),
    ("14-11-2025", "IMPS/CUSTOMER B/ADVANCE", "IMPS25111405", "", 100000),
    ("20-12-2025", "NEFT/AMIT VERMA/LOAN", "NEFT25122006", "", 150000),
    ("31-12-2025", "BY CASH DEPOSIT", "CSH25123101", "", 250000),
    ("15-03-2026", "BY CASH DEPOSIT", "CSH26031501", "", 200000),
    ("20-03-2026", "RTGS/SUPPLIER S/PURCHASE", "RTGS26032001", 900000, ""),
]

CASH_ROWS = [  # date, particulars, receipt, payment
    ("08-04-2025", "Cash sales", 150000, ""),
    ("15-04-2025", "Collection from Customer X", 120000, ""),
    ("20-05-2025", "Cash sales", 200000, ""),
    ("10-06-2025", "Capital introduced - Partner A (Rahul Sharma)", 150000, ""),
    ("20-06-2025", "Collection from Customer Y", 100000, ""),
    ("30-06-2025", "Cash deposited into bank", "", 720000),
    ("12-07-2025", "Cash sales", 175000, ""),
    ("25-08-2025", "Cash sales", 225000, ""),
    ("31-08-2025", "Cash deposited into bank", "", 400000),
    ("12-09-2025", "Collection from Customer Z", 80000, ""),
    ("15-09-2025", "Capital introduced - Partner B (Neeraj Gupta)", 150000, ""),
    ("30-09-2025", "Cash deposited into bank", "", 230000),
    ("14-11-2025", "Cash sales", 150000, ""),
    ("15-12-2025", "Collection from Customer W", 100000, ""),
    ("31-12-2025", "Cash deposited into bank", "", 250000),
    ("18-02-2026", "Cash sales", 200000, ""),
    ("15-03-2026", "Cash deposited into bank", "", 200000),
]

SALES_ROWS = [  # date, particulars, invoice, debit, credit
    ("08-04-2025", "Cash sales", "INV-001", "", 150000),
    ("10-05-2025", "Sales - Customer P", "INV-002", "", 200000),
    ("20-05-2025", "Cash sales", "INV-003", "", 200000),
    ("12-07-2025", "Cash sales", "INV-004", "", 175000),
    ("15-07-2025", "Sales - Customer Q", "INV-005", "", 150000),
    ("25-08-2025", "Cash sales", "INV-006", "", 225000),
    ("20-10-2025", "Sales - Customer R", "INV-007", "", 200000),
    ("14-11-2025", "Cash sales", "INV-008", "", 100000),
    ("18-02-2026", "Cash sales", "INV-009", "", 100000),
]

AIS_ROWS = [  # information source, description, amount, tds
    ("Customer P Pvt Ltd", "Receipts reported by buyer (fictional)", 200000, 0),
    ("Customer Q", "Receipts reported by buyer (fictional)", 200000, 0),
    ("Customer R", "Receipts reported by buyer (fictional)", 200000, 0),
]

DEBTOR_ROWS = [  # customer, opening, sales, receipts, closing
    ("Customer X", 120000, 0, 120000, 0),
    ("Customer Y", 100000, 0, 100000, 0),
    ("Customer Z", 80000, 0, 80000, 0),
    ("Customer W", 0, 0, 100000, -100000),
]

MAPPING = [
    ("30-06-2025", "08-04-2025", 150000, "Cash sale"), ("30-06-2025", "15-04-2025", 120000, "Customer X"),
    ("30-06-2025", "20-05-2025", 200000, "Cash sale"), ("30-06-2025", "10-06-2025", 150000, "Partner A"),
    ("30-06-2025", "20-06-2025", 100000, "Customer Y"), ("31-08-2025", "12-07-2025", 175000, "Cash sale"),
    ("31-08-2025", "25-08-2025", 225000, "Cash sale"), ("30-09-2025", "12-09-2025", 80000, "Customer Z"),
    ("30-09-2025", "15-09-2025", 150000, "Partner B"), ("31-12-2025", "14-11-2025", 150000, "Cash sale"),
    ("31-12-2025", "15-12-2025", 100000, "Customer W"), ("15-03-2026", "18-02-2026", 200000, "Cash sale"),
]


def _xlsx(path, title, header, rows):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:30]
    ws.append([FICTION])
    ws.append(header)
    for r in rows:
        ws.append(list(r))
    wb.save(path)


def main():
    OUT.mkdir(exist_ok=True)
    import docx

    d = docx.Document()
    for line in NOTICE.splitlines():
        d.add_paragraph(line)
    d.save(OUT / "notice_143_2_PQR.docx")

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(OUT / "notice_143_2_PQR.pdf"), pagesize=A4)
    y = 800
    import textwrap

    for line in NOTICE.splitlines():
        for part in textwrap.wrap(line, 95) or [""]:
            c.drawString(40, y, part)
            y -= 14
            if y < 50:
                c.showPage()
                y = 800
    c.save()

    # image-only ("scanned") PDF
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    lines = []
    for line in NOTICE.splitlines():
        lines += textwrap.wrap(line, 80) or [""]
    img = Image.new("L", (2480, 3508), 255)
    dr = ImageDraw.Draw(img)
    y = 120
    for line in lines:
        dr.text((120, y), line, fill=0, font=font)
        y += 40
    img.save(OUT / "notice_143_2_PQR_scanned.pdf", "PDF", resolution=300)

    _xlsx(OUT / "bank_statement_PQR.xlsx", "Statement", ["Date", "Narration", "Ref No", "Withdrawal", "Deposit"], BANK_ROWS)
    book = [(r[0], r[1], r[2], r[4], r[3]) for r in BANK_ROWS[1:]]  # books: Dr = receipt into bank
    dup = next(r for r in book if r[2] == "NEFT25071502")
    book.insert(book.index(dup) + 1, dup)  # duplicate posting (book error)
    _xlsx(OUT / "bank_book_PQR.xlsx", "Bank Book", ["Date", "Particulars", "Ref No", "Dr", "Cr"], book)
    _xlsx(OUT / "cash_book_PQR.xlsx", "Cash Book", ["Date", "Particulars", "Receipts", "Payments"], CASH_ROWS)
    _xlsx(OUT / "sales_ledger_PQR.xlsx", "Sales Ledger", ["Date", "Particulars", "Invoice No", "Dr", "Cr"], SALES_ROWS)
    _xlsx(OUT / "ais_PQR.xlsx", "AIS", ["Information Source", "Information Description", "Amount", "TDS"], AIS_ROWS)
    _xlsx(OUT / "debtor_ledger_PQR.xlsx", "Debtors", ["Customer", "Opening Balance", "Sales", "Receipts", "Closing Balance"], DEBTOR_ROWS)
    with open(OUT / "source_mapping_PQR.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["deposit_date", "receipt_date", "amount", "description"])
        w.writerows(MAPPING)
    print(f"Fictional sample data written to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
