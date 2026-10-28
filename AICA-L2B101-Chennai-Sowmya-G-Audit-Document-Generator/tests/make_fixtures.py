"""Creates the dummy MCA master data PDFs used by the tests.

All companies, people and DINs here are fictitious. The first files copy the
layout of the real MCA V3 "Company Master Data" printout: labels at the left,
values at the right and centred vertically against their label (so a
two-line address starts above the label line), a two-line "books of account"
label, and a bordered Director/Signatory table where a long name wraps.

Run:  python tests/make_fixtures.py
"""
import os

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
os.makedirs(HERE, exist_ok=True)
PAGE_W, PAGE_H = landscape(A4)[0], 612          # same page size as the MCA print


def put(c, x, top, text, size=10):
    """Draw text with its top edge at `top` (pdfplumber's coordinates)."""
    c.setFont("Helvetica", size)
    c.drawString(x, PAGE_H - top - 8.2, text)


def mca_v3(path, address_lines, cin="U74999TN2019PTC123456",
           company="MEENAKSHI TEXTILE TRADERS PRIVATE LIMITED", directors=None,
           company_class="Private"):
    if directors is None:
        directors = [("01234567", ["KARTHIK SUNDARAM"]),
                     ("07654321", ["VALLIAMMAI", "RAMANATHAN"])]       # name wraps
    c = canvas.Canvas(path, pagesize=(792, PAGE_H))
    put(c, 44, 117.8, "Company Information", 11)
    rows = [("CIN", cin, 158.3), ("Company Name", company, 186.8),
            ("ROC Name", "ROC Chennai", 215.3), ("Registration Number", "123456", 243.8),
            ("Date of Incorporation", "09/10/2019", 272.3),
            ("Email Id", "accounts@example.com", 300.8)]
    for label, value, top in rows:
        put(c, 52, top, label)
        put(c, 335, top, value)
    # Registered address: value lines centred on the label line (12 pt apart)
    put(c, 52, 335.3, "Registered Address")
    first = 335.3 - 6 * (len(address_lines) - 1)
    for i, line in enumerate(address_lines):
        put(c, 335, first + 12 * i, line)
    # Books of account address: two-line label, value centred between
    put(c, 52, 369.8, "Address at which the books of account are to be")
    put(c, 52, 381.8, "maintained")
    put(c, 335, 375.8, "NO 9, GODOWN STREET, MADURAI, Tamil Nadu, India, 625001")
    for label, value, top in [("Listed in Stock Exchange(s) (Y/N)", "No", 410.3),
                              ("Category of Company", "Company limited by shares", 438.8),
                              ("Subcategory of the Company", "Non-government company", 467.3),
                              ("Class of Company", company_class, 495.8),
                              ("ACTIVE compliance", "-", 524.3),
                              ("Authorised Capital (Rs)", "10,00,000", 552.8),
                              ("Paid up Capital (Rs)", "5,00,000", 581.3)]:
        put(c, 52, top, label)
        put(c, 335, top, value)
    c.showPage()

    # Page 2: status and the bordered Director/Signatory table
    for label, value, top in [("Date of last AGM", "30/09/2025", 37.0),
                              ("Date of Balance Sheet", "31/03/2025", 65.3),
                              ("Company Status", "Active", 93.8)]:
        put(c, 52, top, label)
        put(c, 335, top, value)
    put(c, 34, 288.3, "Index of Charges", 12)
    put(c, 36, 334.5, "No Records Found")
    put(c, 34, 374.5, "Director/Signatory Details", 12)
    columns = [42, 100, 180, 310, 400, 490, 600, 690, 750]
    headers = ["Sr. No", "DIN/PAN", "Name", "Designation", "Category",
               "Date of Appointment", "Cessation Date", "Signatory"]
    top = 405.0
    row_tops = [top]
    heights = [30] + [max(28.5, 12 * len(name) + 16.5) for _, name in directors]
    for h in heights:
        row_tops.append(row_tops[-1] + h)
    for r in range(len(heights)):
        for k in range(len(headers)):
            c.rect(columns[k], PAGE_H - row_tops[r + 1], columns[k + 1] - columns[k],
                   heights[r])
    for k, text in enumerate(headers):
        put(c, columns[k] + 4, top + 10, text, 9)
    for r, (din, name_lines) in enumerate(directors, start=1):
        centre = (row_tops[r] + row_tops[r + 1]) / 2
        put(c, columns[0] + 6, centre - 5, str(r), 9)
        put(c, columns[1] + 4, centre - 5, din, 9)
        first = centre - 5 - 6 * (len(name_lines) - 1)
        for i, line in enumerate(name_lines):
            put(c, columns[2] + 4, first + 12 * i, line, 9)
        for k, text in ((3, "Director"), (4, "Promoter"), (5, "09/10/2019"), (6, "-"),
                        (7, "Yes")):
            put(c, columns[k] + 4, centre - 5, text, 9)
    c.save()


def bordered_table(path):
    """All fields in one bordered two-column table (another common print)."""
    styles = getSampleStyleSheet()
    p = lambda t: Paragraph(t, styles["Normal"])
    rows = [("CIN", "U51909TN2021PTC765432"), ("Company Name", "VAIGAI AGRO EXPORTS PRIVATE LIMITED"),
            ("Registered Address", "PLOT 14, SIPCOT INDUSTRIAL ESTATE, KAPPALUR, MADURAI, "
                                   "Tamil Nadu, India, 625008"),
            ("Address at which the books of account are to be maintained", "-"),
            ("Class of Company", "Private")]
    table = Table([[p(a), p(b)] for a, b in rows], colWidths=[200, 300])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, "grey"),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    directors = [["Sr. No", "DIN/PAN", "Name", "Designation", "Category", "Date of Appointment"],
                 ["1", "02345678", "PRIYA NATARAJAN", "Managing Director", "Promoter", "01/06/2021"],
                 ["2", "03456789", "ARUL MURUGAN", "Director", "Professional", "01/06/2021"]]
    t2 = Table([[p(x) for x in r] for r in directors])
    t2.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, "grey")]))
    SimpleDocTemplate(path, pagesize=A4).build(
        [table, Spacer(1, 12), p("Director/Signatory Details"), t2])


def value_below(path):
    """Each value printed on the line below its label."""
    c = canvas.Canvas(path, pagesize=A4)
    y = 800
    for text in ["CIN", "U85300TN2020NPL112233", "Company Name", "THIRUPARANKUNDRAM EDUCATION FOUNDATION",
                 "Registered Address", "12 ANNA SALAI,", "CHENNAI 600002", "Email Id", "office@example.org"]:
        c.drawString(40, y, text)
        y -= 16
    c.save()


def scanned(path):
    """A 'scanned' page: only a picture, no text layer."""
    c = canvas.Canvas(path, pagesize=A4)
    c.setFillGray(0.85)
    c.rect(40, 500, 500, 300, fill=1)
    c.save()


if __name__ == "__main__":
    mca_v3(os.path.join(HERE, "mca_v3_two_line_address.pdf"),
           ["NO 12, SOUTH MASI STREET, NEAR MEENAKSHI AMMAN TEMPLE,",
            "MADURAI, Madurai, Tamil Nadu, India, 625001"])
    mca_v3(os.path.join(HERE, "mca_v3_three_line_address.pdf"),
           ["DOOR NO 4/122, PLOT NO 7, SRI RAM NAGAR 2ND STREET,",
            "K.PUDUR, OPP. TO GOVT HIGHER SECONDARY SCHOOL,",
            "MADURAI, Madurai, Tamil Nadu, India, 625007"])
    mca_v3(os.path.join(HERE, "mca_v3_one_line_address.pdf"),
           ["NO 5, WEST VELI STREET, MADURAI, Tamil Nadu, India, 625001"],
           cin="L17111TN2015PLC098765", company="PANDIAN SPINNING MILLS LIMITED",
           company_class="Public")
    bordered_table(os.path.join(HERE, "bordered_table.pdf"))
    value_below(os.path.join(HERE, "value_below_label.pdf"))
    scanned(os.path.join(HERE, "scanned_no_text.pdf"))
    print("fixtures written to", HERE)
