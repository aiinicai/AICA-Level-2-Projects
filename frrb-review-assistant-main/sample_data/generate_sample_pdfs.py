"""Generates test PDF documents for demonstration and validation.

Creates:
1. Sample_Draft_FS_Option_A_With_Errors.pdf (For Option A testing: contains arithmetic errors, missing Schedule III notes)
2. Sample_Annual_Report_Option_B_RedFlags.pdf (For Option B testing: contains qualified auditor opinion, CARO variances, red flags)
3. Sample_Compliant_FS_Negative_Test.pdf (For Negative testing: fully compliant statements to ensure no false positives)
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def create_option_a_pdf(filename: str):
    """Creates a draft financial statement PDF with deliberate pre-finalisation defects."""
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor("#1F4E79"))
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=12, leading=15, textColor=colors.HexColor("#1F4E79"))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=9, leading=12)
    table_cell = ParagraphStyle('TableCell', parent=styles['Normal'], fontSize=8, leading=10)

    # Page 1: Title & Draft Balance Sheet
    story.append(Paragraph("ABC TECHNOLOGIES LIMITED (DRAFT FOR AUDIT REVIEW)", title_style))
    story.append(Paragraph("BALANCE SHEET AS AT 31ST MARCH 2024 (DRAFT BEFORE FINALISATION)", h2_style))
    story.append(Spacer(1, 10))

    bs_data = [
        [Paragraph("<b>Particulars</b>", table_cell), Paragraph("<b>Note No.</b>", table_cell), Paragraph("<b>As at 31 March 2024 (₹ in Lakhs)</b>", table_cell), Paragraph("<b>As at 31 March 2023 (₹ in Lakhs)</b>", table_cell)],
        [Paragraph("<b>I. ASSETS</b>", table_cell), "", "", ""],
        [Paragraph("<b>1. Non-Current Assets</b>", table_cell), "", "", ""],
        [Paragraph("Property, Plant and Equipment", table_cell), "3", "5,420.00", "4,900.00"],
        [Paragraph("Capital Work-in-Progress", table_cell), "4", "310.00", "150.00"],
        [Paragraph("Financial Assets - Non-Current Investments", table_cell), "5", "1,200.00", "1,150.00"],
        [Paragraph("Deferred Tax Assets (Net)", table_cell), "6", "180.00", "120.00"],
        [Paragraph("<b>2. Current Assets</b>", table_cell), "", "", ""],
        [Paragraph("Inventories", table_cell), "7", "1,450.00", "1,320.00"],
        [Paragraph("Trade Receivables", table_cell), "8", "2,100.00", "1,850.00"],
        [Paragraph("Cash and Cash Equivalents", table_cell), "9", "400.00", "310.00"],
        [Paragraph("<b>TOTAL ASSETS</b>", table_cell), "", Paragraph("<b>11,060.00</b>", table_cell), Paragraph("<b>9,800.00</b>", table_cell)],
        [Paragraph("<b>II. EQUITY AND LIABILITIES</b>", table_cell), "", "", ""],
        [Paragraph("<b>1. Equity</b>", table_cell), "", "", ""],
        [Paragraph("Equity Share Capital", table_cell), "10", "2,000.00", "2,000.00"],
        [Paragraph("Other Equity", table_cell), "11", "4,210.00", "3,650.00"],
        [Paragraph("<b>2. Non-Current Liabilities</b>", table_cell), "", "", ""],
        [Paragraph("Borrowings", table_cell), "12", "2,350.00", "2,100.00"],
        [Paragraph("<b>3. Current Liabilities</b>", table_cell), "", "", ""],
        [Paragraph("Borrowings (Current)", table_cell), "13", "450.00", "320.00"],
        [Paragraph("Trade Payables", table_cell), "14", "1,550.00", "1,480.00"],
        [Paragraph("Other Current Liabilities", table_cell), "15", "250.00", "250.00"],
        # DELIBERATE ARITHMETIC ERROR: Total Equity & Liab = 2000+4210+2350+450+1550+250 = 10,810 (vs Assets 11,060)
        [Paragraph("<b>TOTAL EQUITY AND LIABILITIES</b>", table_cell), "", Paragraph("<b>10,810.00</b>", table_cell), Paragraph("<b>9,800.00</b>", table_cell)],
    ]

    t_bs = Table(bs_data, colWidths=[200, 50, 140, 140])
    t_bs.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D9E1F2")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ]))
    story.append(t_bs)
    story.append(Spacer(1, 15))

    # Page 2: Statement of Profit and Loss & Cash Flow Statement
    story.append(PageBreak())
    story.append(Paragraph("ABC TECHNOLOGIES LIMITED", title_style))
    story.append(Paragraph("STATEMENT OF PROFIT AND LOSS FOR THE YEAR ENDED 31ST MARCH 2024", h2_style))
    story.append(Spacer(1, 10))

    pl_data = [
        [Paragraph("<b>Particulars</b>", table_cell), Paragraph("<b>Note</b>", table_cell), Paragraph("<b>Year Ended 31-03-2024</b>", table_cell), Paragraph("<b>Year Ended 31-03-2023</b>", table_cell)],
        [Paragraph("Revenue from Operations", table_cell), "16", "14,800.00", "12,500.00"],
        [Paragraph("Other Income", table_cell), "17", "220.00", "180.00"],
        [Paragraph("<b>Total Revenue</b>", table_cell), "", "15,020.00", "12,680.00"],
        [Paragraph("Cost of Materials Consumed", table_cell), "18", "7,100.00", "6,200.00"],
        [Paragraph("Employee Benefits Expense", table_cell), "19", "3,400.00", "2,900.00"],
        [Paragraph("Finance Costs", table_cell), "20", "310.00", "280.00"],
        [Paragraph("Depreciation and Amortisation", table_cell), "3", "520.00", "480.00"],
        [Paragraph("Other Expenses (including CSR ₹42 Lakhs)", table_cell), "21", "2,690.00", "2,120.00"],
        [Paragraph("<b>Total Expenses</b>", table_cell), "", "14,020.00", "11,980.00"],
        [Paragraph("<b>Profit Before Tax</b>", table_cell), "", "1,000.00", "700.00"],
        [Paragraph("Tax Expense (Current & Deferred)", table_cell), "22", "260.00", "182.00"],
        [Paragraph("<b>Profit for the Year</b>", table_cell), "", "740.00", "518.00"],
    ]
    t_pl = Table(pl_data, colWidths=[200, 50, 140, 140])
    t_pl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D9E1F2")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t_pl)
    story.append(Spacer(1, 15))

    story.append(Paragraph("CASH FLOW STATEMENT (SUMMARY)", h2_style))
    story.append(Paragraph(
        "Net cash from operating activities: ₹1,120.00 Lakhs<br/>"
        "Net cash used in investing activities: (₹650.00 Lakhs)<br/>"
        "Net cash used in financing activities: (₹350.00 Lakhs)<br/>"
        "Net increase in cash: ₹120.00 Lakhs<br/>"
        "Cash and cash equivalents at beginning of year: ₹310.00 Lakhs<br/>"
        "<b>Cash and cash equivalents at end of year: ₹430.00 Lakhs</b> "
        "<i>(Note: Does not tie to Balance Sheet Note 9 of ₹400.00 Lakhs)</i>",
        body_style
    ))

    # Page 3: Notes to Accounts with deliberately missing Schedule III disclosures
    story.append(PageBreak())
    story.append(Paragraph("NOTES TO DRAFT FINANCIAL STATEMENTS", title_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Note 1: Significant Accounting Policies</b>", h2_style))
    story.append(Paragraph(
        "<b>Property, Plant and Equipment:</b> Items of Property, Plant and Equipment are stated at cost less accumulated depreciation. "
        "<b>Subsequent expenditure related to an item of PPE is added to its carrying value only if it increases the future benefits from "
        "the existing asset beyond its previously assessed standard of performance.</b>",
        body_style
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Note 10: Share Capital</b>", h2_style))
    story.append(Paragraph(
        "Authorised Share Capital: 2,50,00,000 Equity Shares of ₹10 each: ₹2,500 Lakhs.<br/>"
        "Issued, Subscribed and Paid-up: 2,00,00,000 Equity Shares of ₹10 each: ₹2,000 Lakhs.<br/>"
        "Details of major institutional shareholders holding > 5% shares are disclosed as per past practice.",
        body_style
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Note 12: Borrowings</b>", h2_style))
    story.append(Paragraph(
        "Non-Current Term Loans from Banks: ₹2,350.00 Lakhs (Previous Year: ₹2,100.00 Lakhs).<br/>"
        "Loans are secured by hypothecation of plant and machinery.",
        body_style
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Note 14: Trade Payables</b>", h2_style))
    story.append(Paragraph(
        "Total Trade Payables: ₹1,550.00 Lakhs (Previous Year: ₹1,480.00 Lakhs).<br/>"
        "Sundry creditors for goods and services.",
        body_style
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Note 23: Key Financial Ratios</b>", h2_style))
    story.append(Paragraph(
        "Current Ratio: 1.76 (PY: 1.95) - Variance -9.7%<br/>"
        "Debt-Equity Ratio: 0.45 (PY: 0.37) - Variance +21.6%<br/>"
        "Debt Service Coverage Ratio: 3.20 (PY: 4.80) - Variance -33.3%<br/>"
        "Return on Equity: 11.9% (PY: 9.1%) - Variance +30.8%",
        body_style
    ))

    doc.build(story)


def create_option_b_pdf(filename: str):
    """Creates a published Annual Report PDF with Auditor remarks, CARO observations & Red Flags."""
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor("#1F4E79"))
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=12, leading=15, textColor=colors.HexColor("#1F4E79"))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=9, leading=12)

    # Page 1: Auditor's Report with Qualified Opinion & Emphasis of Matter
    story.append(Paragraph("INDEPENDENT AUDITOR'S REPORT", title_style))
    story.append(Paragraph("To the Members of XYZ Industries Limited", h2_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Report on the Audit of the Financial Statements</b>", h2_style))
    story.append(Paragraph(
        "<b>Qualified Opinion:</b> In our opinion and to the best of our information and according to the explanations given to us, "
        "except for the effects of the matter described in the <i>Basis for Qualified Opinion</i> section of our report, the aforesaid "
        "financial statements give a true and fair view in conformity with Ind AS and the accounting principles generally accepted in India.",
        body_style
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Basis for Qualified Opinion:</b>", h2_style))
    story.append(Paragraph(
        "We draw attention to Note 7 of the financial statements regarding physical verification of inventories at the company's "
        "manufacturing facility at Raigad. Management has not carried out physical verification of raw materials and work-in-progress "
        "amounting to ₹480.00 Lakhs as at 31st March 2024. Consequently, we were unable to determine whether any adjustments were "
        "necessary in respect of the inventory carrying values and the related cost of materials consumed for the year.",
        body_style
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>Emphasis of Matter:</b>", h2_style))
    story.append(Paragraph(
        "We draw attention to Note 28 to the financial statements, which describes the uncertainty relating to the outcome of pending "
        "litigation with the Goods and Services Tax (GST) department demanding differential tax and penalty of ₹650.00 Lakhs. "
        "The Company has contested this demand before the Appellate Tribunal and no provision has been recognized in the financial "
        "statements. Our opinion is not modified in respect of this matter.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Page 2: CARO 2020 Report
    story.append(PageBreak())
    story.append(Paragraph("ANNEXURE 'A' TO THE INDEPENDENT AUDITOR'S REPORT", title_style))
    story.append(Paragraph("Report on Companies (Auditor's Report) Order, 2020 (CARO 2020)", h2_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "<b>Clause 3(i)(c) - Title Deeds:</b> According to the information and explanations given to us, the title deeds of all immovable "
        "properties disclosed in the financial statements are held in the name of the Company, except for one freehold land situated at "
        "Ambernath having carrying value of ₹120.00 Lakhs where title deeds are in the name of erstwhile promoter.<br/><br/>"
        "<b>Clause 3(ii)(b) - Quarterly Statements:</b> The Company has been sanctioned working capital limits in excess of ₹5 Crores "
        "(sanctioned limit ₹2,500 Lakhs) from consortium of banks on the basis of security of current assets. <b>The quarterly statements "
        "of book debts and stock filed by the Company with banks show material discrepancies when compared with the books of accounts "
        "for the quarters ended September 2023 and December 2023, and the same have not been reconciled in the financial statements.</b><br/><br/>"
        "<b>Clause 3(ix)(a) - Default in Repayment:</b> The Company has not defaulted in repayment of loans or other borrowings or in the "
        "payment of interest thereon to any lender.",
        body_style
    ))

    # Page 3: Published Balance Sheet & Notes
    story.append(PageBreak())
    story.append(Paragraph("XYZ INDUSTRIES LIMITED — BALANCE SHEET AS AT 31ST MARCH 2024", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Total Assets: ₹18,400.00 Lakhs | Total Equity and Liabilities: ₹18,400.00 Lakhs<br/>"
        "Revenue from Operations: ₹24,500.00 Lakhs | Profit after Tax: ₹1,240.00 Lakhs<br/><br/>"
        "<b>Note 14: Borrowings</b><br/>"
        "Term Loans from Banks: ₹4,800.00 Lakhs. (Repayment terms and rate of interest not specified).<br/><br/>"
        "<b>Note 24: Related Party Transactions</b><br/>"
        "The Company has issued corporate guarantee of ₹1,500.00 Lakhs to State Bank of India for credit facilities availed by "
        "its wholly owned subsidiary ABC Ltd. The guarantee is given without commission and is not measured at fair value.<br/><br/>"
        "<b>Note 28: Contingent Liabilities</b><br/>"
        "Disputed GST demand: ₹650.00 Lakhs. (Qualitative description regarding timing of cash outflows and possibility of reimbursement omitted).",
        body_style
    ))

    doc.build(story)


def create_compliant_pdf(filename: str):
    """Creates a clean, fully compliant Financial Statements PDF for Negative Testing."""
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor("#1F4E79"))
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=12, leading=15, textColor=colors.HexColor("#1F4E79"))
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=9, leading=12)

    story.append(Paragraph("PRIME COMPLIANCE INDIA LIMITED", title_style))
    story.append(Paragraph("STANDALONE FINANCIAL STATEMENTS FOR THE YEAR ENDED 31ST MARCH 2024", h2_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "<b>Primary Statements Summary (in ₹ Lakhs):</b><br/>"
        "Total Assets: ₹15,000.00 Lakhs<br/>"
        "Total Equity and Liabilities: ₹15,000.00 Lakhs (Perfectly Reconciled: Assets = Equity + Liabilities)<br/>"
        "Revenue from Operations: ₹22,000.00 Lakhs<br/>"
        "Profit After Tax: ₹1,500.00 Lakhs<br/>"
        "Cash and cash equivalents at end of year: ₹850.00 Lakhs (Reconciled with Cash Flow Statement).<br/><br/>"
        "<b>Significant Accounting Policies:</b><br/>"
        "<b>Property, Plant and Equipment:</b> Capitalized at cost. Subsequent expenditure is capitalized only when "
        "it is probable that future economic benefits associated with the item will flow to the entity and cost can be reliably measured "
        "per Ind AS 16.7. Useful lives are reviewed at each financial year-end per Schedule II.<br/><br/>"
        "<b>Note on Share Capital:</b><br/>"
        "Promoter Shareholding Disclosure: Includes full promoter shareholding table specifying promoter name, number of shares, "
        "% of total shares, and % change during the year per Schedule III.<br/><br/>"
        "<b>Note on Trade Payables:</b><br/>"
        "Trade Payables Ageing Schedule: Full ageing table presented (<1 year, 1-2 years, 2-3 years, >3 years) with separate "
        "categorisation for MSME dues, Others, Disputed MSME dues, Disputed Others, and Unbilled dues.<br/>"
        "MSMED Act Section 22 disclosures: Disclosed principal and interest due and remaining unpaid as NIL.<br/><br/>"
        "<b>Note on Trade Receivables:</b><br/>"
        "Trade Receivables Ageing Schedule: Disclosed by age brackets (<6 months, 6 mos-1 yr, 1-2 yrs, 2-3 yrs, >3 yrs) with "
        "undisputed and disputed categories and credit impairment breakdown.<br/><br/>"
        "<b>Note on Key Financial Ratios:</b><br/>"
        "Disclosed all 11 mandatory analytical ratios with comparative figures and comprehensive explanation for variances exceeding 25%.<br/><br/>"
        "<b>Auditor's Report:</b> Unqualified Clean Opinion. No modifications or emphasis of matter. CARO 2020 report contains no unfavorable remarks.",
        body_style
    ))

    doc.build(story)


if __name__ == "__main__":
    os.makedirs("sample_data", exist_ok=True)
    pdf_a = os.path.join("sample_data", "Sample_Draft_FS_Option_A_With_Errors.pdf")
    pdf_b = os.path.join("sample_data", "Sample_Annual_Report_Option_B_RedFlags.pdf")
    pdf_clean = os.path.join("sample_data", "Sample_Compliant_FS_Negative_Test.pdf")

    create_option_a_pdf(pdf_a)
    create_option_b_pdf(pdf_b)
    create_compliant_pdf(pdf_clean)
    print("Sample PDFs successfully created in sample_data directory.")
