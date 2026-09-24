"""
Sample TDS and TCS Certificate PDF Generator for Testing & Verification.
Generates realistic mock certificates compliant with TRACES layouts for both
Income-tax Act, 1961 and Income-tax Act, 2025.
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_mock_certificates(output_dir: Path) -> list[Path]:
    """Generate mock PDF certificates covering all supported forms and acts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    samples_data = [
        # --- 1961 Act Certificates ---
        {
            "filename": "raw_download_001_f16a.pdf",
            "act": "Income-tax Act, 1961",
            "form_title": "FORM NO. 16A",
            "rule": "[See rule 31(1)(b)]",
            "subtitle": "Certificate under section 203 of the Income-tax Act, 1961 for tax deducted at source on payments other than salary",
            "cert_no": "TR16A9928172",
            "deductor_name": "STATE BANK OF INDIA\nSAMRIDDHI BHAVAN, STRAND ROAD\nKOLKATA - 700001",
            "deductor_tan": "CALB00123D",
            "deductor_pan": "AAACS0012B",
            "target_label": "Name and address of the Deductee",
            "target_name": "TATA CONSULTANCY SERVICES LIMITED",
            "target_addr": "TCS HOUSE, RAVELINE STREET, FORT\nMUMBAI - 400001, MAHARASHTRA",
            "target_pan": "AAACT1234K",
            "ay": "2025-26",
            "fy": "2024-25",
            "quarter": "Q2",
            "tax_deducted": "Rs. 1,45,200",
        },
        {
            "filename": "raw_download_002_f16.pdf",
            "act": "Income-tax Act, 1961",
            "form_title": "FORM NO. 16",
            "rule": "[See rule 31(1)(a)]",
            "subtitle": "Certificate under section 203 of the Income-tax Act, 1961 for tax deducted at source on salary (Part A)",
            "cert_no": "TR16S8821901",
            "deductor_name": "INFOSYS LIMITED\nELECTRONICS CITY, HOSUR ROAD\nBENGALURU - 560100",
            "deductor_tan": "BLRI09876C",
            "deductor_pan": "AAACI1234N",
            "target_label": "Name and address of the Employee",
            "target_name": "RAHUL ARVIND DESHMUKH",
            "target_addr": "FLAT 402, SUNSHINE APARTMENTS, WHITEFIELD\nBENGALURU - 560066, KARNATAKA",
            "target_pan": "ABCDE1234F",
            "ay": "2024-25",
            "fy": "2023-24",
            "quarter": "Q4",
            "tax_deducted": "Rs. 2,84,000",
        },
        {
            "filename": "raw_download_003_f27d.pdf",
            "act": "Income-tax Act, 1961",
            "form_title": "FORM NO. 27D",
            "rule": "[See rule 37D]",
            "subtitle": "Certificate under section 206C of the Income-tax Act, 1961 for tax collected at source",
            "cert_no": "TR27D1122334",
            "deductor_name": "MINERAL TRADING CORPORATION LTD\nCORE-1, SCOPE COMPLEX, LODHI ROAD\nNEW DELHI - 110003",
            "deductor_tan": "DELM09988G",
            "deductor_pan": "AAACM8877D",
            "target_label": "Name and address of the Collectee",
            "target_name": "JINDAL STEEL AND POWER LIMITED",
            "target_addr": "JINDAL CENTRE, 12 BHIKAJI CAMA PLACE\nNEW DELHI - 110066",
            "target_pan": "AAACJ5544K",
            "ay": "2025-26",
            "fy": "2024-25",
            "quarter": "Q3",
            "tax_deducted": "Rs. 5,12,800",
        },
        {
            "filename": "raw_download_004_f16b.pdf",
            "act": "Income-tax Act, 1961",
            "form_title": "FORM NO. 16B",
            "rule": "[See rule 31(1)(c)]",
            "subtitle": "Certificate under section 194-IA of the Income-tax Act, 1961 for tax deducted at source on transfer of certain immovable property",
            "cert_no": "TR16B3344556",
            "deductor_name": "AMITABH HARIVANSH RAI\nB-104, BANDRA WEST, MUMBAI",
            "deductor_tan": "MUMA11223E",
            "deductor_pan": "AARPA1122D",
            "target_label": "Name and address of the Transferor (Seller / Deductee)",
            "target_name": "PRIYA SURESH MEHTA",
            "target_addr": "C-201, JUHU TARA ROAD, VILE PARLE\nMUMBAI - 400049",
            "target_pan": "BNZPM9876Q",
            "ay": "2025-26",
            "fy": "2024-25",
            "quarter": "Q1",
            "tax_deducted": "Rs. 85,000",
        },

        # --- Duplicate Deductee to test Collision Avoidance ---
        {
            "filename": "raw_download_005_f16a_duplicate.pdf",
            "act": "Income-tax Act, 1961",
            "form_title": "FORM NO. 16A",
            "rule": "[See rule 31(1)(b)]",
            "subtitle": "Certificate under section 203 of the Income-tax Act, 1961 for tax deducted at source on payments other than salary",
            "cert_no": "TR16A9928173",
            "deductor_name": "HDFC BANK LIMITED\nSENAPATI BAPAT MARG, LOWER PAREL\nMUMBAI - 400013",
            "deductor_tan": "MUMH00123E",
            "deductor_pan": "AAACH0012F",
            "target_label": "Name and address of the Deductee",
            "target_name": "TATA CONSULTANCY SERVICES LIMITED",
            "target_addr": "TCS HOUSE, RAVELINE STREET, FORT\nMUMBAI - 400001, MAHARASHTRA",
            "target_pan": "AAACT1234K",
            "ay": "2025-26",
            "fy": "2024-25",
            "quarter": "Q3",
            "tax_deducted": "Rs. 2,10,000",
        },

        # --- 2025 Act Certificates ---
        {
            "filename": "raw_download_006_f130.pdf",
            "act": "Income-tax Act, 2025",
            "form_title": "FORM NO. 130",
            "rule": "Rules under Income-tax Act, 2025",
            "subtitle": "Certificate for Tax Deducted at Source on Salary under the Income-tax Act, 2025",
            "cert_no": "ACT25F130001",
            "deductor_name": "BHARTI AIRTEL LIMITED\nBHARTI CRESCENT, 1 NELSON MANDELA ROAD, VASANT KUNJ\nNEW DELHI - 110070",
            "deductor_tan": "DELB12345T",
            "deductor_pan": "AAACB4433D",
            "target_label": "Name and address of the Employee",
            "target_name": "VIKRAM NARENDRA PATEL",
            "target_addr": "B-302, GREEN ACRES, GANDHINAGAR\nGUJARAT - 382010",
            "target_pan": "BTRPP5432M",
            "ay": "2026-27",
            "fy": "2025-26",
            "quarter": "Q4",
            "tax_deducted": "Rs. 1,98,400",
        },
        {
            "filename": "raw_download_007_f131.pdf",
            "act": "Income-tax Act, 2025",
            "form_title": "FORM NO. 131",
            "rule": "Rules under Income-tax Act, 2025",
            "subtitle": "Certificate for Tax Deducted at Source on Non-Salary Payments under the Income-tax Act, 2025",
            "cert_no": "ACT25F131002",
            "deductor_name": "LARSEN AND TOUBRO LIMITED\nL&T HOUSE, BALLARD ESTATE\nMUMBAI - 400001",
            "deductor_tan": "MUML55667K",
            "deductor_pan": "AAACL6677K",
            "target_label": "Name and address of the Deductee",
            "target_name": "HCL TECHNOLOGIES LIMITED",
            "target_addr": "TECHNOLOGY HUB, SECTOR 126\nNOIDA - 201304, UTTAR PRADESH",
            "target_pan": "AAACH9988P",
            "ay": "2026-27",
            "fy": "2025-26",
            "quarter": "Q1",
            "tax_deducted": "Rs. 3,75,000",
        },
        {
            "filename": "raw_download_008_f132.pdf",
            "act": "Income-tax Act, 2025",
            "form_title": "FORM NO. 132",
            "rule": "Rules under Income-tax Act, 2025",
            "subtitle": "Certificate for Tax Deducted at Source on Immovable Property and Specified Transactions under the Income-tax Act, 2025",
            "cert_no": "ACT25F132003",
            "deductor_name": "RAJIV CHATTERJEE\n14/2 PARK STREET, KOLKATA",
            "deductor_tan": "CALR99881A",
            "deductor_pan": "ACHPC7766R",
            "target_label": "Name and address of the Payee / Transferor",
            "target_name": "ANANYA KRISHNAMURTHY",
            "target_addr": "NO 45, INDIRANAGAR 100 FT ROAD\nBENGALURU - 560038",
            "target_pan": "AKMPA8877B",
            "ay": "2026-27",
            "fy": "2025-26",
            "quarter": "Q2",
            "tax_deducted": "Rs. 1,20,000",
        },
        {
            "filename": "raw_download_009_f133.pdf",
            "act": "Income-tax Act, 2025",
            "form_title": "FORM NO. 133",
            "rule": "Rules under Income-tax Act, 2025",
            "subtitle": "Certificate for Tax Collected at Source under the Income-tax Act, 2025",
            "cert_no": "ACT25F133004",
            "deductor_name": "MAHINDRA AND MAHINDRA LIMITED\nGATEWAY BUILDING, APOLLO BUNDER\nMUMBAI - 400001",
            "deductor_tan": "MUMM00778C",
            "deductor_pan": "AAACM0077F",
            "target_label": "Name and address of the Collectee",
            "target_name": "ROYAL MOTORS PRIVATE LIMITED",
            "target_addr": "PLOT 88, INDUSTRIAL AREA PHASE 1\nCHANDIGARH - 160002",
            "target_pan": "AABCR4455E",
            "ay": "2026-27",
            "fy": "2025-26",
            "quarter": "Q4",
            "tax_deducted": "Rs. 92,500",
        },
    ]

    for sample in samples_data:
        file_path = output_dir / sample["filename"]
        _create_pdf_certificate(file_path, sample)
        generated_files.append(file_path)

    return generated_files


def _create_pdf_certificate(file_path: Path, data: dict):
    """Build a styled TRACES-like A4 PDF certificate."""
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=1,  # Center
    )
    rule_style = ParagraphStyle(
        "CertRule",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=1,
    )
    sub_style = ParagraphStyle(
        "CertSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.HexColor("#2C3E50"),
    )
    cell_head = ParagraphStyle(
        "CellHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1A365D"),
    )
    cell_body = ParagraphStyle(
        "CellBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    )
    cell_name = ParagraphStyle(
        "CellName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#0D47A1"),
    )

    story = []

    # Header section
    story.append(Paragraph(data["form_title"], title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(data["rule"], rule_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(data["subtitle"], sub_style))
    story.append(Spacer(1, 10))

    # Certificate No bar
    cert_no_table = Table(
        [[Paragraph(f"<b>Certificate No.:</b> {data['cert_no']}", cell_body)]],
        colWidths=[523],
    )
    cert_no_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B0BEC5")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(cert_no_table)
    story.append(Spacer(1, 6))

    # Party Table: Left = Deductor, Right = Deductee/Employee/Collectee
    deductor_html = f"<b>Name and address of the Deductor</b><br/>{data['deductor_name'].replace(chr(10), '<br/>')}"
    target_html = f"<b>{data['target_label']}</b><br/><font color='#0D47A1'><b>{data['target_name']}</b></font><br/>{data['target_addr'].replace(chr(10), '<br/>')}"

    party_table_data = [
        [Paragraph(deductor_html, cell_body), Paragraph(target_html, cell_body)],
        [
            Paragraph(f"<b>PAN of Deductor:</b> {data['deductor_pan']}<br/><b>TAN of Deductor:</b> {data['deductor_tan']}", cell_body),
            Paragraph(f"<b>PAN of Deductee:</b> <b>{data['target_pan']}</b>", cell_body),
        ],
        [
            Paragraph(f"<b>CIT (TDS):</b> CIT (TDS), Circle 1", cell_body),
            Paragraph(f"<b>Assessment Year:</b> {data['ay']}<br/><b>Financial Year:</b> {data['fy']}<br/><b>Quarter:</b> {data['quarter']}", cell_body),
        ],
    ]

    party_table = Table(party_table_data, colWidths=[261.5, 261.5])
    party_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#90A4AE")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAFAFA")),
            ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#FFFFFF")),
        ])
    )
    story.append(party_table)
    story.append(Spacer(1, 10))

    # Summary of Tax Deducted/Collected table
    tax_table_data = [
        [
            Paragraph("<b>Quarter</b>", cell_head),
            Paragraph("<b>Receipt Numbers</b>", cell_head),
            Paragraph("<b>Amount Paid / Credited</b>", cell_head),
            Paragraph("<b>Amount of Tax Deducted / Collected</b>", cell_head),
        ],
        [
            Paragraph(data["quarter"], cell_body),
            Paragraph("TRAC-REC-9988210", cell_body),
            Paragraph("Rs. 14,50,000.00", cell_body),
            Paragraph(f"<b>{data['tax_deducted']}</b>", cell_body),
        ],
        [
            Paragraph("<b>Total (Rs.)</b>", cell_head),
            Paragraph("-", cell_body),
            Paragraph("Rs. 14,50,000.00", cell_body),
            Paragraph(f"<b>{data['tax_deducted']}</b>", cell_head),
        ],
    ]

    tax_table = Table(tax_table_data, colWidths=[80, 150, 140, 153])
    tax_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(tax_table)
    story.append(Spacer(1, 15))

    # Verification footer
    verification_text = (
        f"I, Principal Officer, do hereby certify that a sum of {data['tax_deducted']} has been "
        f"deducted and deposited to the credit of the Central Government in accordance with the provisions of "
        f"the {data['act']}."
    )
    story.append(Paragraph(verification_text, cell_body))

    doc.build(story)


if __name__ == "__main__":
    test_dir = Path("./sample_test_certificates")
    print(f"Generating mock certificates in: {test_dir.resolve()}")
    files = generate_mock_certificates(test_dir)
    print(f"Successfully generated {len(files)} mock certificates.")
