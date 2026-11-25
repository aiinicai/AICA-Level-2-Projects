from __future__ import annotations

from pathlib import Path
import zipfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

OUT = Path(__file__).resolve().parents[1] / "sample-files" / "single_issue_assessment_test"
OUT.mkdir(parents=True, exist_ok=True)
WATERMARK = "FICTIONAL TEST ONLY  |  NOT AN OFFICIAL RECORD  |  NOT FOR FILING"


def base_doc(title: str, subtitle: str = "") -> Document:
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.68)
    sec.bottom_margin = Inches(0.68)
    sec.left_margin = Inches(0.78)
    sec.right_margin = Inches(0.78)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(40, 45, 52)
    normal.paragraph_format.space_after = Pt(5)
    header = sec.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run(WATERMARK)
    run.bold = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(170, 25, 25)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Synthetic names, identifiers, account details and transactions for NOTICE-MATE workflow testing only.")
    footer.runs[0].font.size = Pt(8)
    footer.runs[0].font.color.rgb = RGBColor(105, 105, 105)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title)
    r.bold = True
    r.font.size = Pt(17)
    r.font.color.rgb = RGBColor(31, 50, 74)
    if subtitle:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(subtitle)
        r.italic = True
        r.font.size = Pt(10)
    return doc


def metadata(doc: Document, rows: list[tuple[str, str]]) -> None:
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for k, v in rows:
        cells = table.add_row().cells
        cells[0].text = k
        cells[1].text = v
        cells[0].paragraphs[0].runs[0].bold = True
    doc.add_paragraph()


def save_notice() -> None:
    d = base_doc("NOTICE UNDER SECTION 142(1)", "Mock assessment communication · single issue · fictional training case")
    metadata(d, [
        ("To", "Aarav Stationery (Fictional Proprietorship)"),
        ("PAN", "ABCDE1234F (fictional test identifier)"),
        ("Assessment Year", "2025-26"),
        ("Previous Year", "2024-25"),
        ("Notice reference", "TEST/142(1)/2025-26/001"),
        ("Date of notice", "10 December 2025"),
        ("Response requested by", "24 December 2025"),
    ])
    d.add_paragraph("To the assessee,")
    d.add_paragraph(
        "In connection with the assessment proceedings for the year stated above, please furnish "
        "an explanation and the records listed below by the response date. This is a fictional "
        "training notice and is not issued by any government authority."
    )
    d.add_heading("Information requested", level=2)
    p = d.add_paragraph()
    p.add_run("1. Unsecured loan from Neel Shah — Rs. 1,20,000").bold = True
    d.add_paragraph(
        "The books of account reflect an unsecured loan of Rs. 1,20,000 stated to have been "
        "received from Neel Shah on 18 September 2024. Please explain the nature and source of "
        "this credit and furnish:"
    )
    for item in [
        "a. signed lender confirmation stating the amount, date, address and PAN;",
        "b. lender bank record showing the transfer and a record supporting the lender's capacity;",
        "c. assessee bank record showing receipt and the corresponding loan ledger; and",
        "d. available loan terms, repayment details and interest particulars, if any.",
    ]:
        d.add_paragraph(item)
    d.add_paragraph(
        "If any requested record is not maintained or is unavailable, identify it and briefly "
        "state the reason. Clear copies may be furnished; originals should be retained."
    )
    d.add_paragraph(
        "The information is requested for examination of the credit. No conclusion is stated "
        "in this mock notice."
    )
    d.add_paragraph("For the Mock Assessment Unit\nAuthorised Officer (fictional training sample)")
    d.save(OUT / "01_mock_notice_142_1_single_loan.docx")


def save_confirmation() -> None:
    d = base_doc("LENDER CONFIRMATION", "Unsecured loan · fictional supporting record")
    metadata(d, [
        ("Lender", "Neel Shah (fictional person)"),
        ("PAN", "QQQPS1234Q (fictional test identifier)"),
        ("Address", "17 Sample Lane, Test Nagar, Mumbai, Maharashtra 400000"),
        ("Borrower", "Aarav Stationery (Fictional Proprietorship)"),
        ("Loan amount", "Rs. 1,20,000"),
        ("Date advanced", "18 September 2024"),
        ("Mode", "NEFT; reference TESTNEFT20240918001"),
    ])
    d.add_paragraph(
        "I confirm that I advanced an unsecured loan of Rs. 1,20,000 to Aarav Stationery on "
        "18 September 2024 by bank transfer. The amount was transferred from my fictional "
        "Sample Cooperative Bank account ending 1001 to the borrower's fictional account ending 2002."
    )
    d.add_paragraph(
        "The loan is repayable on demand and carries no interest. As at 31 March 2025, "
        "the principal remained outstanding. This confirmation is created solely as a synthetic test record."
    )
    d.add_paragraph("\nSignature: ______________________________\nName: Neel Shah\nDate: 20 April 2025")
    d.save(OUT / "02_lender_confirmation.docx")


def save_bank_statement(filename: str, title: str, holder: str, account: str, rows: list[tuple[str, str, str, str, str]]) -> None:
    d = base_doc(title, "Synthetic statement extract · all values fabricated")
    metadata(d, [
        ("Account holder", holder),
        ("Bank", "Sample Cooperative Bank (fictional)"),
        ("Account", account),
        ("Period", "01 September 2024 to 30 September 2024"),
        ("Currency", "INR"),
    ])
    t = d.add_table(rows=1, cols=5)
    t.style = "Table Grid"
    for cell, text in zip(t.rows[0].cells, ["Date", "Description", "Reference", "Debit (Rs.)", "Credit (Rs.)"]):
        cell.text = text
        cell.paragraphs[0].runs[0].bold = True
    for row in rows:
        cells = t.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = text
    def amount(text: str) -> int:
        return int(text.replace(",", "")) if text and text != "—" else 0
    balance = sum(amount(row[4]) - amount(row[3]) for row in rows)
    d.add_paragraph(f"Closing balance shown in this synthetic extract: Rs. {balance:,}.")
    d.save(OUT / filename)


def save_lender_financials() -> None:
    d = base_doc("LENDER INCOME SUMMARY", "Synthetic FY 2024-25 supporting record")
    metadata(d, [
        ("Taxpayer", "Neel Shah (fictional person)"),
        ("PAN", "QQQPS1234Q (fictional test identifier)"),
        ("Assessment Year", "2025-26"),
        ("Previous Year", "2024-25"),
    ])
    d.add_paragraph("Fictional computation summary prepared for testing the application workflow.")
    t = d.add_table(rows=1, cols=2)
    t.style = "Table Grid"
    t.rows[0].cells[0].text = "Particulars"
    t.rows[0].cells[1].text = "Amount (Rs.)"
    for c in t.rows[0].cells:
        c.paragraphs[0].runs[0].bold = True
    for a, b in [("Salary and other disclosed income", "8,40,000"), ("Deductions (illustrative)", "1,00,000"),
                 ("Taxable income (illustrative)", "7,40,000")]:
        row = t.add_row().cells
        row[0].text, row[1].text = a, b
    d.add_paragraph("This is not an ITR acknowledgement and is not a tax filing document.")
    d.save(OUT / "05_lender_income_summary.docx")


def save_ledger() -> None:
    d = base_doc("UNSECURED LOAN LEDGER", "Aarav Stationery · fictional books extract")
    metadata(d, [
        ("Entity", "Aarav Stationery (Fictional Proprietorship)"),
        ("PAN", "ABCDE1234F (fictional test identifier)"),
        ("Financial year", "2024-25"),
        ("Ledger", "Neel Shah — unsecured loan"),
    ])
    t = d.add_table(rows=1, cols=5)
    t.style = "Table Grid"
    for c, x in zip(t.rows[0].cells, ["Date", "Particulars", "Debit (Rs.)", "Credit (Rs.)", "Balance (Rs.)"]):
        c.text = x
        c.paragraphs[0].runs[0].bold = True
    row = t.add_row().cells
    for c, x in zip(row, ["18-09-2024", "NEFT received; TESTNEFT20240918001", "—", "1,20,000", "1,20,000 Cr"]):
        c.text = x
    d.add_paragraph("Balance as at 31 March 2025: Rs. 1,20,000 payable.")
    d.save(OUT / "06_borrower_loan_ledger.docx")


def save_terms() -> None:
    d = base_doc("LOAN TERMS NOTE", "Synthetic record · no interest")
    metadata(d, [
        ("Lender", "Neel Shah (fictional person)"),
        ("Borrower", "Aarav Stationery (Fictional Proprietorship)"),
        ("Principal", "Rs. 1,20,000"),
        ("Date", "18 September 2024"),
        ("Repayment", "On demand"),
        ("Interest", "Nil"),
    ])
    d.add_paragraph(
        "This short-form note records the parties' understanding for the fictional test loan. "
        "The loan is unsecured, repayable on demand and interest-free. No repayment had been "
        "made as at 31 March 2025."
    )
    d.add_paragraph("Lender signature: ____________________    Borrower signature: ____________________")
    d.save(OUT / "07_loan_terms_note.docx")


def main() -> None:
    save_notice()
    save_confirmation()
    save_bank_statement("03_lender_bank_statement.docx", "BANK STATEMENT EXTRACT", "Neel Shah", "XXXX-TEST-1001", [
        ("01-09-2024", "Opening balance", "—", "—", "5,00,000"),
        ("18-09-2024", "NEFT to Aarav Stationery", "TESTNEFT20240918001", "1,20,000", "—"),
    ])
    save_bank_statement("04_borrower_bank_statement.docx", "BANK STATEMENT EXTRACT", "Aarav Stationery", "XXXX-TEST-2002", [
        ("01-09-2024", "Opening balance", "—", "—", "95,000"),
        ("18-09-2024", "NEFT from Neel Shah", "TESTNEFT20240918001", "—", "1,20,000"),
    ])
    save_lender_financials()
    save_ledger()
    save_terms()
    (OUT / "README_TEST_ONLY.txt").write_text(
        "NOTICE-MATE SINGLE-ISSUE TEST CASE\\n\\n"
        "All people, businesses, PAN-like identifiers, addresses, banks, account references and transactions in this pack are invented. "
        "These files are for local software testing only and must never be filed, submitted or relied upon.\\n\\n"
        "Suggested upload order: notice first; then lender confirmation, lender bank statement, borrower bank statement, "
        "lender income summary, borrower ledger, and loan terms note. Assign document types in the app where prompted.\\n"
        "Expected issue count: one unsecured-loan concern. The lettered a-d entries in the notice are supporting-record requests, not separate issues.\\n",
        encoding="utf-8",
    )
    archive = OUT.parent / "NOTICE-MATE_single_issue_test_pack.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.iterdir()):
            z.write(f, arcname=f"{OUT.name}/{f.name}")
    print(f"Created {len(list(OUT.iterdir()))} files in {OUT}")
    print(archive)


if __name__ == "__main__":
    main()
