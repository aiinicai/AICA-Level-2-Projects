"""
smoke_test.py
-------------
Optional self-check you can run after `pip install -r requirements.txt` to
confirm the environment and the rule engine are working correctly, using a
small synthetic sample LC (no real LC document needed).

Run with:  python smoke_test.py
"""
import os
import sys
import tempfile

import pdf_extract
import lc_parser
import rules_engine
import exporter
from models import AnalysisResult, SECTION_ORDER

SAMPLE_LC = """
27 : Sequence of Total
1/1
40A : Form of Documentary Credit
IRREVOCABLE
20 : Documentary Credit Number
ILCBOM2026001234
31C : Date of Issue
260815
40E : Applicable Rules
UCP LATEST VERSION
31D : Date and Place of Expiry
261130 IN INDIA
50 : Applicant
ABC TRADING CO LTD
123 INDUSTRIAL AREA, MUMBAI, INDIA
59 : Beneficiary
XYZ EXPORTS PTE LTD
45 ROBINSON ROAD, SINGAPORE
32B : Currency Code, Amount
USD 250000,00
41A : Available With...By...
ANY BANK IN SINGAPORE BY NEGOTIATION
43P : Partial Shipments
NOT ALLOWED
44E : Port of Loading / Airport of Departure
SINGAPORE PORT
44F : Port of Discharge / Airport of Destination
MUMBAI PORT, INDIA
44C : Latest Date of Shipment
261031
45A : Description of Goods and/or Services
50,000 UNITS OF ELECTRONIC COMPONENTS AS PER PROFORMA INVOICE NO. PI-2026-77
46A : Documents Required
+SIGNED COMMERCIAL INVOICE IN TRIPLICATE
+FULL SET OF CLEAN ON BOARD BILLS OF LADING MADE OUT TO ORDER OF ISSUING BANK
+CERTIFICATE OF ORIGIN ISSUED BY CHAMBER OF COMMERCE
+INSURANCE POLICY COVERING 110% OF CIF INVOICE VALUE, ALL RISKS
48 : Period for Presentation
21 DAYS AFTER THE DATE OF SHIPMENT BUT WITHIN THE VALIDITY OF THE CREDIT
71B : Charges
ALL BANKING CHARGES OUTSIDE INDIA ARE FOR BENEFICIARY'S ACCOUNT
"""


def make_sample_pdf(path: str, text: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 40
    for line in text.split("\n"):
        if y < 40:
            c.showPage()
            y = height - 40
        c.setFont("Courier", 8)
        c.drawString(30, y, line[:120])
        y -= 11
    c.save()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "sample_lc.pdf")
        make_sample_pdf(pdf_path, SAMPLE_LC)

        text = pdf_extract.normalise_text(pdf_extract.extract_text(pdf_path))
        classification = lc_parser.classify_document(text, "issued")
        assert classification.is_lc, "sample should be recognised as an LC"
        assert classification.dc_number == "ILCBOM2026001234", f"unexpected DC number: {classification.dc_number}"

        fields = lc_parser.extract_fields(text)
        clauses = rules_engine.build_clause_points(fields, "issued")
        assert clauses, "no clauses were produced"

        result = AnalysisResult(lc_type="Issued / Transmitted LC", dc_number=classification.dc_number,
                                 source_filename="sample_lc.pdf", full_text=text, clauses=clauses)
        for section in SECTION_ORDER:
            print(f"{section}: {len(result.by_section(section))} point(s)")

        word_path = os.path.join(tmp, "summary.docx")
        pdf_out_path = os.path.join(tmp, "summary.pdf")
        exporter.export_to_word(result, word_path)
        exporter.export_to_pdf(result, pdf_out_path)
        assert os.path.getsize(word_path) > 0
        assert os.path.getsize(pdf_out_path) > 0

    print("\nAll checks passed - your environment is set up correctly.")
    print("Run 'python main.py' to launch the LC Analyser GUI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
