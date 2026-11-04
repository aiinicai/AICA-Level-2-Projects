# ============================================================
#  audit_engine.py  -  the document engine (no screen code)
#  Statutory Audit Document Generator  |  Accounting Standards
#  Sowmya G & Associates, Chartered Accountants
#
#  Builds, for one company and one financial year:
#    1. Letter of Engagement             (auditor's letterhead)
#    2. DSC Authorisation Letter         (company's letterhead)
#    3. Letter of Representation         (company's letterhead)
#    4. Independent Auditor's Report     (auditor's letterhead)
#         + CARO 2020 and IFC annexures, where applicable
#  and reads company details from the MCA master data PDF.
#
#  Used by desktop_app.py (window / .exe) and streamlit_app.py (browser).
#  Every make_...() function takes the details dictionary and a file
#  path or an in-memory file.
# ============================================================

import os
import re
import sys
import subprocess
from datetime import date, datetime, timedelta

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_COLOR_INDEX
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


# When packed as an .exe, bundled files (the logo) are unpacked to a temporary
# folder, so documents are saved under Documents\Audit Documents instead.
if getattr(sys, "frozen", False):
    SCRIPT_FOLDER = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    OUTPUT_FOLDER = os.path.join(os.path.expanduser("~"), "Documents", "Audit Documents")
    # python-docx finds its templates via "docx/parts/../templates"; inside the
    # .exe the "parts" folder must exist on disk for that path to work.
    os.makedirs(os.path.join(SCRIPT_FOLDER, "docx", "parts"), exist_ok=True)
else:
    SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_FOLDER = SCRIPT_FOLDER

# Default auditor details (change here once, and they appear every time)
# Change these once to your own firm's details; they then appear every time.
FIRM_DEFAULTS = {
    "firm": "Sowmya G & Associates",
    "auditor": "CA. Sowmya G",
    "designation": "Proprietor",
    "frn": "",
    "membership": "",
    "firm_address1": "Office address line 1,",
    "firm_address2": "Madurai - 6250XX.",
    "phone": "+91 XXXXX XXXXX",
    "email": "audit@yourfirm.in",
    "website": "www.yourfirm.in",
    "place": "Madurai",
}

OPINIONS = ["Unmodified", "Qualified", "Adverse", "Disclaimer"]
DIRECTOR_DESIGNATIONS = ["Director", "Managing Director", "Whole-time Director",
                         "Additional Director", "Nominee Director"]
NUMBER_OF_DIRECTORS = 4
AUDIT_TRAIL_OPTIONS = ["Yes - operated throughout the year",
                       "Yes - enabled during the year",
                       "No - not maintained"]


# ------------------------------------------------------------
# 1. Small helpers for dates and the financial year
# ------------------------------------------------------------

def financial_year_choices():
    """The FY being audited is normally the one that ended last March."""
    today = date.today()
    end_year = today.year if today.month >= 4 else today.year - 1
    years = []
    for end in (end_year, end_year - 1, end_year + 1):
        years.append(str(end - 1) + "-" + str(end))
    return years


def fy_details(fy):
    """'2025-2026' -> year end text, short year end and next FY."""
    start = int(fy[:4])
    end = start + 1
    return {
        "year_end": "31st March " + str(end),
        "year_end_short": "31.03." + str(end),
        "next_fy": str(end) + "-" + str(end + 1),
    }


def check_date(text):
    """Return True if text is a valid dd/mm/yyyy date."""
    try:
        datetime.strptime(text.strip(), "%d/%m/%Y")
        return True
    except ValueError:
        return False


def safe_name(text):
    """Turn a company name into a safe file or folder name."""
    cleaned = ""
    for ch in text:
        if ch.isalnum() or ch in " -":
            cleaned = cleaned + ch
    return "_".join(cleaned.split())


def default_logo():
    for name in ("ca_logo.jpeg", "ca_logo.jpg", "ca_logo.png"):
        path = os.path.join(SCRIPT_FOLDER, name)
        if os.path.exists(path):
            return path
    return ""


# ------------------------------------------------------------
# 2. Reading the MCA master data PDF
#
#    pdfplumber gives the position of every word on the page. We rebuild
#    each printed line from those positions, so the spacing is exactly as
#    in the master data, and we split a line into columns wherever there
#    is a wide gap (label column | value column | ...).
# ------------------------------------------------------------

# Every label on the MCA master data. The full list tells us where one
# value ends and the next field begins.
MCA_LABELS = [
    "CIN", "Company Name", "ROC Code", "ROC Name", "Registration Number",
    "Company Category", "Company SubCategory", "Category of Company",
    "Subcategory of the Company", "Class of Company", "Authorised Capital",
    "Paid up Capital", "Number of Members", "Date of Incorporation",
    "Registered Address", "Registered Office Address",
    "Address at which", "Address other than",
    "Email Id", "Email", "Whether Listed or not", "Listed in Stock Exchange",
    "ACTIVE compliance", "Suspended at stock exchange", "Date of last AGM",
    "Date of Balance Sheet", "Date of latest Balance Sheet", "Company Status",
    "Main division", "Description of main division", "Charges", "Index of Charges",
    "Directors/Signatory Details", "Director/Signatory Details",
]

# Never copy the books-of-account address into the registered office
BOOKS_ADDRESS = re.compile(r"address\s+(at\s+which|other\s+than)|books\s+of\s+account",
                           re.IGNORECASE)

# Words that belong to the designation / category columns, never to a name
NOT_PART_OF_NAME = {
    "director", "managing", "whole-time", "wholetime", "whole", "time", "additional",
    "nominee", "independent", "executive", "non-executive", "non", "promoter",
    "professional", "alternate", "chairman", "chairperson", "ceo", "cfo", "secretary",
    "company", "designated", "partner", "manager", "shareholder", "signatory",
}

CIN_TYPES = {
    "PTC": "Private", "PLC": "Public", "OPC": "One Person Company",
    "NPL": "Section 8 company", "GAP": "Public company limited by guarantee",
    "GAT": "Private company limited by guarantee",
    "ULL": "Public unlimited company", "ULT": "Private unlimited company",
    "GOI": "Union Government company", "SGC": "State Government company",
    "FTC": "Subsidiary of a foreign company",
}

CIN_PATTERN = r"[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}"


def tidy(text):
    """Single spaces, and a space after every comma (as printed on the master data)."""
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,:-")


def page_lines(page):
    """Printed lines of one page: each has top, bottom and columns {x, x1, text}."""
    words = page.extract_words(x_tolerance=1.5, keep_blank_chars=False)
    words.sort(key=lambda w: (round(w["top"]), w["x0"]))
    lines = []
    for word in words:
        if lines and abs(word["top"] - lines[-1]["top"]) <= 3:
            lines[-1]["words"].append(word)
        else:
            lines.append({"top": word["top"], "words": [word]})
    result = []
    for line in lines:
        line["words"].sort(key=lambda w: w["x0"])
        columns = []
        for word in line["words"]:
            height = word["bottom"] - word["top"]
            if columns and word["x0"] - columns[-1]["x1"] < 1.2 * height:
                columns[-1]["text"] += " " + word["text"]          # same column
                columns[-1]["x1"] = word["x1"]
            else:
                columns.append({"x": word["x0"], "x1": word["x1"], "text": word["text"]})
        result.append({"top": line["top"],
                       "bottom": max(w["bottom"] for w in line["words"]),
                       "columns": columns})
    return result


def page_fields(lines):
    """Label -> value pairs from a two-column (label | value) layout.

    MCA centres each value vertically against its label, so a 2- or 3-line
    address starts ABOVE the label line. Each value line is therefore given
    to the label whose vertical centre is nearest to it.
    """
    # where does the value column start? (x of values next to known labels)
    value_xs = [line["columns"][1]["x"] for line in lines
                if len(line["columns"]) > 1 and label_at_start(line["columns"][0]["text"])]
    if not value_xs:
        return []
    value_x = sorted(value_xs)[len(value_xs) // 2] - 20

    # 1. label blocks (a long label may wrap onto a second line)
    blocks = []
    for line in lines:
        left = [c["text"] for c in line["columns"] if c["x"] < value_x]
        if not left:
            continue
        if blocks and line["top"] - blocks[-1]["bottom"] < 4:
            blocks[-1]["text"] += " " + " ".join(left)
            blocks[-1]["bottom"] = line["bottom"]
        else:
            blocks.append({"text": " ".join(left), "top": line["top"],
                           "bottom": line["bottom"], "values": []})
    if not blocks:
        return []

    # 2. give every value line to the nearest label block (by vertical centre)
    for line in lines:
        right = [c["text"] for c in line["columns"] if c["x"] >= value_x]
        if not right:
            continue
        centre = (line["top"] + line["bottom"]) / 2
        nearest = min(blocks, key=lambda b: abs((b["top"] + b["bottom"]) / 2 - centre))
        if abs((nearest["top"] + nearest["bottom"]) / 2 - centre) < 20:
            nearest["values"].append((line["top"], " ".join(right)))

    fields = []
    for block in blocks:
        value = " ".join(text for _, text in sorted(block["values"]))
        fields.append((tidy(block["text"]), tidy(value)))
    return fields


def read_pdf(path):
    """Return (rows, table_rows, fields).

    rows       - every printed line, split into columns {x, text}
    table_rows - rows of any bordered table, as lists of cell texts
    fields     - (label, value) pairs from the label | value layout
    """
    rows, table_rows, fields = [], [], []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables({"text_x_tolerance": 1.5}):
                for row in table:
                    table_rows.append([tidy((cell or "").replace("\n", " ")) for cell in row])
            lines = page_lines(page)
            fields.extend(page_fields(lines))
            rows.extend(line["columns"] for line in lines)
    return rows, table_rows, fields


def find_in_fields(fields, wanted):
    wanted = [w.lower() for w in wanted]
    for label_text, value in fields:
        label = label_at_start(label_text)
        if label and label.lower() in wanted:
            return "" if value == "-" else value
    return ""


def find_in_tables(table_rows, wanted):
    """Value in the cell next to a label cell (bordered tables only)."""
    wanted = [w.lower() for w in wanted]
    for row in table_rows:
        for k, cell in enumerate(row):
            label = label_at_start(cell)
            if label is None or label.lower() not in wanted:
                continue
            rest = cell[len(label):].strip(" :-")
            later = [c for c in row[k + 1:] if c]
            return tidy(" ".join([rest] + later[:1]))
    return ""


def label_at_start(text):
    """If the text starts with an MCA label, return that label (else None)."""
    best = None
    for label in MCA_LABELS:
        if text.lower().startswith(label.lower()):
            rest = text[len(label):]
            if rest == "" or not rest[0].isalnum():      # "CIN" must not match "CINEMA"
                if best is None or len(label) > len(best):
                    best = label
    return best


def find_value(rows, wanted):
    """Value printed next to (or below) one of the wanted labels, across lines."""
    wanted = [w.lower() for w in wanted]
    for i, row in enumerate(rows):
        label = label_at_start(row[0]["text"])
        if label is None or label.lower() not in wanted:
            continue
        parts = []
        rest = row[0]["text"][len(label):].strip(" :-")
        if rest:
            parts.append(rest)
        parts.extend(column["text"] for column in row[1:])
        value_x = row[1]["x"] if len(row) > 1 else None

        for next_row in rows[i + 1:]:
            if label_at_start(next_row[0]["text"]):
                break                                    # next field has started
            if value_x is not None and next_row[0]["x"] < value_x - 15:
                break                                    # text in the label column
            parts.extend(column["text"] for column in next_row)
        return tidy(" ".join(parts))
    return ""


def clean_name(text):
    """Keep only the name: stop at the first designation / category word."""
    kept = []
    for word in text.split():
        if word.lower().strip(".,") in NOT_PART_OF_NAME:
            break
        kept.append(word)
    return tidy(" ".join(kept))


def find_directors(rows, table_rows):
    """DIN and name only, from the Directors/Signatory Details table."""
    directors = []
    for row in table_rows:
        for k, cell in enumerate(row):
            if re.fullmatch(r"\d{8}", cell) and k + 1 < len(row):
                name = clean_name(row[k + 1])
                if name and not any(x["din"] == cell for x in directors):
                    directors.append({"din": cell, "name": name})
                break
    if directors:
        return directors

    start = None
    for i, row in enumerate(rows):
        if any(c["text"].lower().startswith(("directors/signatory", "director/signatory"))
               for c in row):
            start = i
            break
    if start is None:
        return []
    for row in rows[start + 1:]:
        label = label_at_start(row[0]["text"])
        if label and "signatory" not in label.lower():
            break                                        # the table has ended
        texts = [c["text"] for c in row]
        for k, text in enumerate(texts):
            match = re.fullmatch(r"(\d{8})(\s+.*)?", text)
            if match is None:
                continue
            name_text = (match.group(2) or "").strip() or (texts[k + 1] if k + 1 < len(texts)
                                                           else "")
            name = clean_name(name_text)
            if name and not any(x["din"] == match.group(1) for x in directors):
                directors.append({"din": match.group(1), "name": name})
            break
    return directors


def extract_master_data(path):
    rows, table_rows, fields = read_pdf(path)

    def value(labels):
        """Bordered table first, then the label | value layout, then plain lines."""
        return (find_in_tables(table_rows, labels) or find_in_fields(fields, labels)
                or find_value(rows, labels))

    all_text = " ".join(c["text"] for row in rows for c in row)
    found = {}

    match = re.search(CIN_PATTERN, value(["CIN"]).replace(" ", ""))
    if match is None:
        match = re.search(CIN_PATTERN, all_text)
    found["cin"] = match.group() if match else ""

    found["company"] = value(["Company Name"])
    address = value(["Registered Address", "Registered Office Address"])
    cut = BOOKS_ADDRESS.search(address)
    found["address"] = tidy(address[:cut.start()]) if cut else address
    found["constitution"] = value(["Class of Company"])
    if found["constitution"] == "" and len(found["cin"]) == 21:
        found["constitution"] = CIN_TYPES.get(found["cin"][12:15], "")
    found["directors"] = find_directors(rows, table_rows)
    return found, len(rows)


# ------------------------------------------------------------
# 3. A small "writer" that builds Word documents
# ------------------------------------------------------------

DARK_BLUE = (0x1F, 0x3A, 0x5F)


# Blanks like "________" and notes like "[Review]" are highlighted in yellow
# so they are easy to spot and fill in before issuing.
FILL_IN = re.compile(r"(_{4,}|\[[^\]]+\])")


def add_text(paragraph, text):
    """Add text to a paragraph, highlighting the fill-in parts."""
    for part in FILL_IN.split(text):
        if part:
            run = paragraph.add_run(part)
            if FILL_IN.fullmatch(part):
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return paragraph


def bottom_border(paragraph, colour="1F3A5F", size=12):
    """Draw a line under a paragraph (used for the letterhead)."""
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), colour)
    borders.append(bottom)
    p_pr.append(borders)


def add_page_number(paragraph):
    """Insert a Word PAGE field ("Page 1", "Page 2" ...)."""
    paragraph.add_run("Page ")
    run = paragraph.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            element = OxmlElement("w:fldChar")
            element.set(qn("w:fldCharType"), kind)
        else:
            element = OxmlElement("w:instrText")
            element.set(qn("xml:space"), "preserve")
            element.text = text
        run._r.append(element)


class Writer:
    """Wraps python-docx with the few paragraph styles our letters need."""

    def __init__(self):
        self.doc = Document()
        normal = self.doc.styles["Normal"]
        normal.font.name = "Arial"
        normal.font.size = Pt(10.5)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.15
        section = self.doc.sections[0]
        section.page_width = Inches(8.27)          # A4
        section.page_height = Inches(11.69)
        section.left_margin = section.right_margin = Inches(0.9)
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.header_distance = Inches(0.35)
        section.footer_distance = Inches(0.35)

    # ----- letterheads -----

    def auditor_letterhead(self, d):
        header = self.doc.sections[0].header
        first = header.paragraphs[0]
        table = header.add_table(1, 2, Inches(6.47))
        table.autofit = False
        logo_cell, text_cell = table.rows[0].cells
        for column, cell, width in ((0, logo_cell, Inches(1.0)), (1, text_cell, Inches(5.47))):
            table.columns[column].width = width      # Word reads the column width
            cell.width = width                       # LibreOffice reads the cell width
        if d["logo"] and os.path.exists(d["logo"]):
            logo_cell.paragraphs[0].add_run().add_picture(d["logo"], width=Inches(0.85))

        def text_line(paragraph, text, size, bold=False, italic=False, colour=None):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(text)
            run.font.size = Pt(size)
            run.bold = bold
            run.italic = italic
            if colour:
                run.font.color.rgb = RGBColor(*colour)

        text_line(text_cell.paragraphs[0], d["firm"].upper(), 16, bold=True, colour=DARK_BLUE)
        text_line(text_cell.add_paragraph(), "Chartered Accountants", 10.5, italic=True)
        text_line(text_cell.add_paragraph(),
                  (d["firm_address1"] + " " + d["firm_address2"]).strip(), 9)
        contact = []
        if d["phone"]:
            contact.append("Ph: " + d["phone"])
        if d["email"]:
            contact.append("Email: " + d["email"])
        if d["website"]:
            contact.append(d["website"])
        text_line(text_cell.add_paragraph(), "  |  ".join(contact), 9)

        # move the empty first paragraph below the table and turn it into the rule
        header._element.remove(first._p)
        header._element.append(first._p)
        first.paragraph_format.space_after = Pt(0)
        bottom_border(first)

    def company_letterhead(self, d):
        header = self.doc.sections[0].header
        p = header.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(d["company"].upper())
        run.bold = True
        run.font.size = Pt(14)
        for text in ("CIN: " + d["cin"], d["address"]):
            q = header.add_paragraph()
            q.alignment = WD_ALIGN_PARAGRAPH.CENTER
            q.paragraph_format.space_after = Pt(0)
            q.add_run(text).font.size = Pt(9)
        bottom_border(header.paragraphs[-1], colour="808080", size=8)

    def page_numbers(self):
        footer = self.doc.sections[0].footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_page_number(footer)
        for run in footer.runs:
            run.font.size = Pt(8)

    # ----- body text -----

    def title(self, text, size=12, underline=False):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.bold = True
        run.underline = underline
        run.font.size = Pt(size)
        return p

    def heading(self, text, underline=False):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.underline = underline
        return p

    def para(self, text, bold_start=""):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if bold_start:
            p.add_run(bold_start).bold = True
        add_text(p, text)
        return p

    def lines(self, items, bold_first=False, align=None):
        """Address or signature block: lines with no gap between them."""
        for number, text in enumerate(items):
            p = self.doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            if align == "right":
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            add_text(p, text)
            if bold_first and number == 0:
                p.runs[0].bold = True
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def clause(self, label, text, level=0):
        """Numbered clause with a hanging indent, e.g. '(a)  text...'"""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        indent = Inches(0.45 * (level + 1))
        p.paragraph_format.left_indent = indent
        p.paragraph_format.first_line_indent = -Inches(0.45)
        p.paragraph_format.tab_stops.add_tab_stop(indent)
        add_text(p, label + "\t" + text)
        return p

    def table(self, headers, rows, widths=None, level=0):
        """Bordered table; empty strings in rows give blank cells to fill in."""
        table = self.doc.add_table(rows=1 + len(rows), cols=len(headers))
        table.style = "Table Grid"
        for col, text in enumerate(headers):
            cell = table.rows[0].cells[col]
            cell.paragraphs[0].add_run(text).bold = True
        for r, row in enumerate(rows):
            for col, text in enumerate(row):
                add_text(table.rows[r + 1].cells[col].paragraphs[0], text)
        for row in table.rows:
            row.height = Pt(18)
            for col, cell in enumerate(row.cells):
                if widths:
                    cell.width = Inches(widths[col])
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(0)
                    for run in p.runs:
                        run.font.size = Pt(9.5)
        if widths:
            for col, width in enumerate(widths):
                table.columns[col].width = Inches(width)
        if level:
            indent = OxmlElement("w:tblInd")
            indent.set(qn("w:w"), str(int(0.45 * level * 1440)))
            indent.set(qn("w:type"), "dxa")
            table._tbl.tblPr.append(indent)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)
        return table

    def space(self):
        self.doc.add_paragraph()

    def page_break(self):
        self.doc.add_page_break()

    def side_by_side(self, left_lines, right_lines):
        """Two signature blocks next to each other (borderless table)."""
        table = self.doc.add_table(rows=1, cols=2)
        for cell, items in zip(table.rows[0].cells, (left_lines, right_lines)):
            cell.paragraphs[0].text = items[0] if items else ""
            for text in items[1:]:
                cell.add_paragraph(text)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(0)
        self.doc.add_paragraph()

    def save(self, path):
        self.doc.save(path)
        return path


# ------------------------------------------------------------
# 4. Pieces used in several documents
# ------------------------------------------------------------

def auditor_signature(d, date_text, with_udin=False):
    items = ["For M/s. " + d["firm"], "Chartered Accountants", "FRN: " + d["frn"], "", "",
             d["auditor"], d["designation"], "M.No: " + d["membership"]]
    if with_udin:
        items.append("UDIN: " + d["udin"])
    items.append("Place: " + d["place"])
    items.append("Date: " + date_text)
    return items


def gap_period(d):
    """'1st April 2025 to 14/06/2025' - the part of the year without audit trail."""
    enabled = datetime.strptime(d["audit_trail_from"], "%d/%m/%Y")
    day_before = (enabled - timedelta(days=1)).strftime("%d/%m/%Y")
    return "01/04/" + d["fy"][:4] + " to " + day_before


def audit_trail_status(d):
    """'full', 'partial' or 'none', from the answer on tab 2."""
    answer = d.get("audit_trail", AUDIT_TRAIL_OPTIONS[0])
    if answer == AUDIT_TRAIL_OPTIONS[1]:
        return "partial"
    if answer == AUDIT_TRAIL_OPTIONS[2]:
        return "none"
    return "full"


def audit_trail_representation(d):
    """MRL wording on audit trail, depending on the answer."""
    status = audit_trail_status(d)
    start = ("The company has used accounting software for maintaining its books of account "
             "for the financial year ended " + d["year_end"])
    if status == "full":
        return (start + ", which has a feature of recording audit trail (edit log) facility, "
                "and the same has operated throughout the year for all relevant transactions "
                "recorded in the software. The audit trail feature has not been disabled or "
                "tampered with, and the audit trail has been preserved as per the statutory "
                "requirements for record retention.")
    if status == "partial":
        return (start + ", which has a feature of recording audit trail (edit log) facility. "
                "The feature was enabled with effect from " + d["audit_trail_from"] + " and has "
                "operated from that date for all relevant transactions recorded in the software; "
                "it was not enabled for the period from " + gap_period(d) + ". After it was "
                "enabled, the feature has not been disabled "
                "or tampered with, and the audit trail has been preserved as per the statutory "
                "requirements for record retention.")
    return (start + ". The accounting software used by the company does not have a feature of "
            "recording audit trail (edit log) facility, or such feature was not enabled during "
            "the year. [State the software used and the reason] We undertake to ensure "
            "compliance with Rule 3(1) of the Companies (Accounts) Rules, 2014 going forward.")


def audit_trail_report(d):
    """Auditor's report wording under Rule 11(g), depending on the answer."""
    status = audit_trail_status(d)
    start = ("Based on our examination, which included test checks, the Company has used "
             "accounting software for maintaining its books of account")
    if status == "full":
        return (start + " which has a feature of recording audit trail (edit log) facility and "
                "the same has operated throughout the year for all relevant transactions "
                "recorded in the software. Further, during the course of our audit we did not "
                "come across any instance of the audit trail feature being tampered with, and "
                "the audit trail has been preserved by the Company as per the statutory "
                "requirements for record retention.")
    if status == "partial":
        return (start + " which has a feature of recording audit trail (edit log) facility; "
                "however, the same was enabled only with effect from " + d["audit_trail_from"] +
                " and did not operate for the period from " + gap_period(d) + ". From the date it was enabled, the audit trail has "
                "operated for all relevant transactions recorded in the software, and during "
                "the course of our audit we did not come across any instance of the audit trail "
                "feature being tampered with. The audit trail has been preserved by the Company "
                "as per the statutory requirements for record retention, for the period for "
                "which the feature was operating.")
    return (start + " which does not have a feature of recording audit trail (edit log) "
            "facility, or such feature was not enabled during the year. [Review] Consequently, "
            "we are unable to comment on whether the audit trail feature was tampered with, or "
            "whether the audit trail has been preserved by the Company as per the statutory "
            "requirements for record retention.")


def director_block(director):
    return ["", "", director["name"], director["designation"], "DIN: " + director["din"]]


def two_director_signatures(w, d):
    """Signature blocks for the first two directors."""
    directors = d["directors"]
    left = director_block(directors[0])
    right = director_block(directors[1]) if len(directors) > 1 else []
    w.side_by_side(left, right)


def statements_list(d):
    """The statements covered by the audit (cash flow is optional for small companies)."""
    if d["cash_flow"]:
        return ("the Balance Sheet as at " + d["year_end"] + ", the Statement of Profit and "
                "Loss and the Statement of Cash Flows for the year then ended, and notes to "
                "the financial statements, including a summary of significant accounting "
                "policies and other explanatory information")
    return ("the Balance Sheet as at " + d["year_end"] + ", the Statement of Profit and Loss "
            "for the year then ended, and notes to the financial statements, including a "
            "summary of significant accounting policies and other explanatory information")


def true_and_fair(d):
    cash = " and its cash flows" if d["cash_flow"] else ""
    return ("a true and fair view in conformity with the accounting principles generally "
            "accepted in India, of the state of affairs of the Company as at " +
            d["year_end"] + ", and its " + d["result"] + cash + " for the year ended on "
            "that date")


# ------------------------------------------------------------
# 5. Letter of Engagement  (auditor's letterhead)
# ------------------------------------------------------------

def make_engagement_letter(d, path):
    w = Writer()
    w.auditor_letterhead(d)
    w.lines(["Date: " + d["engagement_date"]], align="right")
    w.lines(["To", "The Board of Directors", d["company"], d["address"]])
    w.para("Statutory audit for the financial year " + d["fy"], bold_start="Sub: ")
    w.para("Dear Sirs,")
    w.para("You have requested that I audit the financial statements of the Company as "
           "defined in Section 2(40) of the Companies Act, 2013, for the financial year " +
           d["fy"] + ". The financial statements of the Company include, where applicable, "
           "consolidated financial statements of the Company and of all its subsidiaries, "
           "associate companies and joint ventures. I am pleased to confirm my acceptance "
           "and my understanding of this audit engagement by means of this letter.")
    w.para("I will conduct my audit in accordance with the Standards on Auditing (SAs), "
           "specified under Section 143(10) of the Act. Those Standards require that I comply "
           "with ethical requirements. As part of an audit in accordance with SAs, we exercise "
           "professional judgment and maintain professional skepticism throughout the audit. "
           "We also:")
    bullets = [
        "Identify and assess the risks of material misstatement of the financial statements, "
        "whether due to fraud or error, design and perform audit procedures responsive to "
        "those risks, and obtain audit evidence that is sufficient and appropriate to provide "
        "a basis for our opinion. The risk of not detecting a material misstatement resulting "
        "from fraud is higher than for one resulting from error, as fraud may involve "
        "collusion, forgery, intentional omissions, misrepresentations, or the override of "
        "internal control.",
        "Obtain an understanding of internal control relevant to the audit in order to design "
        "audit procedures that are appropriate in the circumstances. Under section 143(3)(i) "
        "of the Companies Act, 2013, we are also responsible for expressing our opinion on "
        "whether the company has adequate internal financial controls system in place and the "
        "operating effectiveness of such controls.",
        "Evaluate the appropriateness of accounting policies used and the reasonableness of "
        "accounting estimates and related disclosures made by management.",
        "Conclude on the appropriateness of management's use of the going concern basis of "
        "accounting and, based on the audit evidence obtained, whether a material uncertainty "
        "exists related to events or conditions that may cast significant doubt on the "
        "company's ability to continue as a going concern. If we conclude that a material "
        "uncertainty exists, we are required to draw attention in our auditor's report to the "
        "related disclosures in the financial statements or, if such disclosures are "
        "inadequate, to modify our opinion. Our conclusions are based on the audit evidence "
        "obtained up to the date of our auditor's report. However, future events or "
        "conditions may cause the company to cease to continue as a going concern.",
        "Evaluate the overall presentation, structure and content of the financial statements, "
        "including the disclosures, and whether the financial statements represent the "
        "underlying transactions and events in a manner that achieves fair presentation.",
    ]
    for text in bullets:
        w.clause("•", text)
    w.para("Because of the inherent limitations of an audit, including the possibility of "
           "collusion or improper management override of controls, there is an unavoidable "
           "risk that material misstatements due to fraud or error may occur and not be "
           "detected, even though the audit is properly planned and performed in accordance "
           "with the SAs. Also, projections of any evaluation of the internal financial "
           "controls over financial reporting to future periods are subject to the risk that "
           "the internal financial controls over financial reporting may become inadequate "
           "because of changes in conditions, or that the degree of compliance with the "
           "policies or procedures may deteriorate.")
    w.para("Our audit will be conducted on the basis that the Management and those charged "
           "with governance acknowledge and understand that they have the responsibility:")
    w.clause("(a)", "For the preparation of financial statements that give a true and fair "
             "view in accordance with the applicable Financial Reporting Standards and other "
             "generally accepted accounting principles in India. This includes:")
    for text in [
        "Compliance with the applicable provisions of the Act.",
        "Proper maintenance of accounts and other matters connected therewith.",
        "The responsibility for the preparation of the financial statements on a going "
        "concern basis.",
        "The preparation of the annual accounts in accordance with the applicable accounting "
        "standards and providing proper explanation relating to any material departures from "
        "those accounting standards;",
        "Selection of accounting policies and applying them consistently and making judgments "
        "and estimates that are reasonable and prudent so as to give a true and fair view of "
        "the state of affairs of the Company at the end of the financial year and of the "
        "profit and loss of the Company for that period;",
        "Taking proper and sufficient care for the maintenance of adequate accounting records "
        "in accordance with the provisions of the Act for safeguarding the assets of the "
        "Company and for preventing and detecting fraud and other irregularities;",
        "Laying down internal financial controls to be followed by the Company and that such "
        "internal financial controls are adequate and were operating effectively; and",
        "Devising proper systems to ensure compliance with the provisions of all applicable "
        "laws and that such systems were adequate and operating effectively.",
    ]:
        w.clause("•", text, level=1)
    w.clause("(b)", "For such internal control as the management determines is necessary to "
             "enable the preparation of financial statements that are free from material "
             "misstatement, whether due to fraud or error; and")
    w.clause("(c)", "To provide us with:")
    w.clause("i)", "Access, at all times, to all information, including the books, account, "
             "vouchers and other records and documentation, of the Company, of which the "
             "management is aware that is relevant to the preparation of the financial statements such as "
             "records, documentation and other matters;", level=1)
    w.clause("ii)", "Additional information that we may request from the management for the "
             "purpose of the audit; and", level=1)
    w.clause("iii)", "Unrestricted access to persons within the entity from whom we determine "
             "it necessary to obtain audit evidence. This includes our entitlement to require "
             "from the officers of the Company such information and explanations as we may "
             "think necessary for the performance of our duties as auditor.", level=1)
    w.para("As part of our audit process, we will request from the management written "
           "confirmation concerning representations made to us in connection with the audit.")
    w.para("I also wish to invite your attention to the fact that our audit process is subject "
           "to 'peer review' under the Chartered Accountants Act, 1949 to be conducted by an "
           "Independent reviewer. The reviewer may inspect, examine or take abstract of our "
           "working papers during the course of the peer review.")
    w.para("We may use technology tools, including Artificial Intelligence (AI) based "
           "applications, to assist in processing and analysing information during the audit. "
           "Before any information is processed using such tools, confidential data, including "
           "names, PAN, Aadhaar, bank account details and other personal or commercially "
           "sensitive information, will be redacted, in line with the Digital Personal Data "
           "Protection Act, 2023. The use of such tools does not change our professional "
           "responsibility: all audit judgments and conclusions will be our own, and all "
           "information will remain subject to the confidentiality requirements of the Code "
           "of Ethics issued by the Institute of Chartered Accountants of India.",
           bold_start="Use of technology: ")
    w.para("I look forward to full cooperation from your staff during our audit and we trust "
           "that they will make available to us whatever records, documentation and other "
           "information are requested in connection with our audit.")
    w.para("Our fees for the same will be billed as the work progresses.")
    w.para("The form and content of our report may need to be amended in the light of our "
           "audit findings.")
    w.para("This letter will be effective for future years unless it is terminated, amended "
           "or superseded.")
    w.para("Please sign and return this letter to indicate that the above is in accordance "
           "with your understanding of the arrangements for our audit of the financial "
           "statements including our respective responsibilities. You may keep a copy of "
           "this letter.")
    w.lines(auditor_signature(d, d["engagement_date"]))
    w.heading("Acknowledged on behalf of " + d["company"])
    two_director_signatures(w, d)
    return w.save(path)


# ------------------------------------------------------------
# 6. DSC Authorisation Letter  (company's letterhead, one page per director)
# ------------------------------------------------------------

def make_dsc_letters(d, path):
    w = Writer()
    w.company_letterhead(d)
    for number, director in enumerate(d["directors"]):
        if number > 0:
            w.page_break()
        w.lines(["Date: " + d["engagement_date"]], align="right")
        w.lines(["To", "M/s. " + d["firm"], "Chartered Accountants,",
                 d["firm_address1"], d["firm_address2"]])
        w.para("Dear Madam,")
        w.para("Authorization to obtain and use Digital Signature Certificate.",
               bold_start="Subject: ")
        w.para("With reference to the above subject, I, " + director["name"] + " (DIN: " +
               director["din"] + "), one of the directors of “" + d["company"] +
               "”, state that as required under various laws of India, including, but "
               "not limited to, the Income-tax Act, 1961, the Integrated Goods and Services Tax "
               "Act, 2017, the Central Goods and Services Tax Act, 2017, the Tamil Nadu Goods "
               "and Services Tax Act, 2017, the Companies Act, 2013 etc., a Director's Digital "
               "Signature Certificate may be required to verify and authenticate various "
               "documents, returns, forms, etc.")
        w.para("For the same purpose, I hereby irrevocably authorize " + d["auditor"] +
               ", Chartered Accountant, " + d["designation"] + " of M/s. " + d["firm"] +
               ", to obtain and use, wherever required for Financial Year " + d["fy"] +
               " & Financial Year " + d["next_fy"] + ", my Digital Signature Certificate, in "
               "my capacity as the company's director under all the laws in India, and the "
               "same will be binding on me at all times.")
        w.para("Thanking You,")
        w.lines(["Yours faithfully,", "For & On Behalf of the Board,", d["company"], "", "",
                 director["name"], director["designation"], "DIN: " + director["din"]])
    return w.save(path)



# ------------------------------------------------------------
# 7. Letter of Representation  (company's letterhead)
#    Covering letter + representation letter, following the firm's model.
#    Figures (depreciation, bank balances, related party transactions,
#    etc.) are left blank and highlighted for the client to fill in.
# ------------------------------------------------------------

BLANK = "________"


def blank_rows(count, columns, numbered=True):
    """Empty table rows; the first column is numbered if asked."""
    rows = []
    for i in range(count):
        row = [""] * columns
        if numbered:
            row[0] = str(i + 1)
        rows.append(row)
    return rows


def make_mrl(d, path):
    w = Writer()
    w.company_letterhead(d)
    ye = d["year_end"]
    ye_short = d["year_end_short"]
    addressee = ["To", "M/s. " + d["firm"], d["auditor"], "Chartered Accountants",
                 d["firm_address1"], d["firm_address2"]]

    # ----- Covering letter -----
    w.lines(["Date: " + d["mrl_date"]], align="right")
    w.lines(addressee)
    w.para("Dear Madam,")
    w.para("In connection with the finalisation of the audit of our accounts for the period "
           "ended " + ye + ", we are enclosing a “Management Representation Letter” on "
           "the various queries raised by you during the course of the audit.")
    w.para("Thanking You,")
    w.para("Yours faithfully,")
    w.lines(["For " + d["company"]])
    two_director_signatures(w, d)

    # ----- Representation letter -----
    w.page_break()
    w.lines(["Date: " + d["mrl_date"]], align="right")
    w.lines(addressee)
    w.para("Management Representation Letter for the year ended " + ye, bold_start="Sub: ")
    w.para("Dear Madam,")
    w.para("This representation letter is provided in connection with your audit of the "
           "financial statements of " + d["company"] + " for the year ended " + ye + " for "
           "the purpose of expressing an opinion as to whether the financial statements give "
           "a true and fair view in accordance with the Accounting Standards specified under "
           "section 133 of the Companies Act, 2013 and other accounting principles generally "
           "accepted in India.")
    w.para("We confirm that, to the best of our knowledge and belief, having made such "
           "inquiries as we considered necessary for the purpose of appropriately informing "
           "ourselves:")

    counter = [0]

    def item(text, level=0):
        counter[0] = counter[0] + 1
        w.clause(str(counter[0]) + ".", text, level=level)

    def sub(label, text):
        w.clause(label, text, level=1)

    # Financial statements
    w.heading("Financial Statements")
    item("We have fulfilled our responsibilities for the preparation and presentation of the "
         "financial statements as set out in the terms of the audit engagement dated " +
         d["engagement_date"] + "; in particular, the financial statements give a true and "
         "fair view in accordance with the applicable Accounting Standards in India.")
    item("Significant assumptions used by us in making accounting estimates are reasonable.")
    item("All events subsequent to the date of the financial statements and for which the "
         "applicable Accounting Standards require adjustment or disclosure have been adjusted "
         "or disclosed.")
    item("The effects of uncorrected misstatements are immaterial, both individually and in "
         "the aggregate, to the financial statements as a whole.")
    w.para("Further, we confirm the following:")

    # Property, plant and equipment
    w.heading("Property, Plant & Equipment")
    if d["caro_ppe"]:
        item("The net book values at which fixed assets are stated in the Balance Sheet are "
             "arrived at:")
        sub("(a)", "after taking into account all capital expenditure on additions thereto, "
            "but no expenditure properly chargeable to revenue;")
        sub("(b)", "after eliminating the cost and accumulated depreciation related to items "
            "sold, discarded, demolished or destroyed; and")
        sub("(c)", "after charging depreciation on assets put to use during the financial "
            "period.")
        item("Depreciation amounting to Rs. " + BLANK + "/- has been determined on the basis "
             "of assessment of the remaining useful life of the fixed assets as per Schedule II "
             "of the Companies Act, 2013.")
        item("The management has physically verified the fixed assets during the year.")
        item("None of the Property, Plant and Equipment have been revalued during the year.")
        if d["caro_property"]:
            item("All the immovable properties in the financial statements are held in the name "
                 "of the company.")
        item("No proceedings have been initiated or are pending against the company for "
             "holding any benami property under the Prohibition of Benami Property "
             "Transactions Act, 1988.")
        item("We have received a capital subsidy of Rs. " + BLANK + "/-. This has been reduced "
             "from the fixed assets and depreciation is calculated on the net amount. "
             "[Delete if not applicable]")
    else:
        item("The company does not hold any Property, Plant and Equipment.")

    # Investments and long-term loans
    w.heading("Investments")
    if d["caro_loans"]:
        item("The investments held by the company as on " + ye_short + " are as follows:")
        w.table(["Sl. No.", "Particulars", "Amount (Rs.)"], blank_rows(3, 3),
                widths=[0.7, 3.6, 1.6], level=1)
    else:
        item("The company does not have / hold any investments.")
    w.heading("Long-Term Loans and Advances")
    if d["caro_loans"]:
        item("The long-term loans and advances in the books as on " + ye_short + " are as "
             "follows:")
        w.table(["Sl. No.", "Party", "Amount (Rs.)"], blank_rows(3, 3),
                widths=[0.7, 3.6, 1.6], level=1)
    else:
        item("There are no long-term loans and advances in the books.")

    # Other non-current assets: fixed deposits
    w.heading("Other Non-Current Assets")
    item("Details of balances with banks in Fixed Deposits:")
    w.table(["Bank & A/c No.", "Balance as on " + ye_short + " (Rs.)", "Maturity Date"],
            blank_rows(2, 3, numbered=False), widths=[2.9, 1.8, 1.3], level=1)

    # Inventories
    w.heading("Inventories")
    if d["caro_inventory"]:
        item("Inventories as on " + ye + " consisted of the following:")
        w.table(["Particulars", "Amount (Rs.)"],
                [["Raw Materials", ""], ["Work-in-Progress", ""], ["Finished Goods", ""],
                 ["Tools & Spares", ""]], widths=[3.4, 2.0], level=1)
        item("All quantities were determined by actual physical count, weight or measurement "
             "taken under our supervision and in accordance with written instructions as on " +
             ye_short + ".")
        item("Inventories were physically verified at periodical intervals during the year.")
        item("All goods included in the inventory are the property of the company; none of the "
             "goods are subject to any charge except as stated in the financial statements.")
        item("Inventories do not include goods sold to customers for which delivery is yet to "
             "be made.")
        item("Inventories have been valued on the following basis:")
        w.table(["Item", "Basis of valuation"],
                [["Raw Materials", "At cost on FIFO basis or NRV, whichever is lower"],
                 ["Work-in-Progress", "At cost"],
                 ["Finished Goods", "At cost or NRV, whichever is lower"],
                 ["Tools & Spares", "One-third written off to revenue"]],
                widths=[1.8, 3.6], level=1)
        item("No item of inventory has a net realisable value in the ordinary course of business "
             "which is less than the amount at which it is included in inventories.")
        item("No provisions are required at this stage for slow-moving, damaged or obsolete "
             "inventories.")
    else:
        item("The company does not hold any inventory.")

    # Trade receivables
    w.heading("Trade Receivables")
    item("Trade receivables as on " + ye_short + " are as follows, and are considered good and "
         "fully recoverable:")
    w.table(["Sl. No.", "Particulars", "Balance as on " + ye_short + " (Rs.)"],
            blank_rows(2, 3), widths=[0.7, 3.4, 1.8], level=1)

    # Cash and bank
    w.heading("Cash and Cash Equivalents")
    item("The company is operating the following bank accounts:")
    w.table(["Sl. No.", "Bank & A/c No.", "Balance as on " + ye_short + " (Rs.)"],
            blank_rows(3, 3), widths=[0.7, 3.4, 1.8], level=1)
    item("The company does not have any other bank account.")
    item("Physical balance of cash as on " + ye_short + " was Rs. " + BLANK + "/-.")

    # Short-term loans and advances
    w.heading("Short-Term Loans and Advances")
    item("The following items appearing in the books as at " + ye + " are considered good and "
         "fully recoverable:")
    w.table(["Sl. No.", "Party", "Amount (Rs.)"], blank_rows(3, 3),
            widths=[0.7, 3.4, 1.8], level=1)

    w.heading("Other Current Assets")
    item("In the opinion of the Board of Directors, other current assets have a value on "
         "realisation in the ordinary course of the company's business which is equal to the "
         "amount at which they are stated in the financial statements.")

    # Deposits and borrowings
    w.heading("Deposits")
    if d["caro_deposits"]:
        item("Details of deposits accepted and compliance with sections 73 to 76 of the Act: "
             "[Give details]")
    else:
        item("The company has not accepted any deposits as defined under the Companies "
             "(Acceptance of Deposits) Rules, 2014.")
    w.heading("Borrowings from Banks / Financial Institutions")
    if d["caro_borrow"]:
        item("The term loans have been used only for the purpose for which they were taken.")
        if d["caro_wc"]:
            item("The quarterly returns of current assets filed with banks or financial "
                 "institutions are in agreement with the books of account.")
        item("The company has not been declared a wilful defaulter by any bank or financial "
             "institution.")
    else:
        item("There are no borrowings from banks or financial institutions.")

    # Liabilities
    w.heading("Liabilities")
    item("We have recorded all known liabilities in the financial statements.")
    item("We have disclosed in the notes to the financial statements all guarantees that we "
         "have given to third parties, pending litigations and all other contingent "
         "liabilities.")
    item("Contingent liabilities disclosed in the notes to the financial statements do not "
         "include any contingencies which are likely to result in a loss and which, therefore, "
         "require adjustment of assets or liabilities.")
    w.heading("Provision for Claims and Losses")
    item("Provision has been made in the accounts for all known losses and claims of material "
         "amounts.")
    w.heading("Capital Commitments")
    item("At the Balance Sheet date, there are no outstanding commitments for capital "
         "expenditure, except those disclosed in the notes to the financial statements.")

    # Related parties
    w.heading("Related Party Transactions")
    item("Related party relationships and transactions have been properly disclosed and "
         "appropriately accounted for in accordance with AS 18, Related Party Disclosures, and "
         "the Companies Act, 2013.")
    item("The full details of the related party transactions are given below:")
    w.table(["Name of Party", "Relationship", "Nature of Transaction", "Amount (Rs.)",
             "Balance Outstanding (Rs.)"], blank_rows(5, 5, numbered=False),
            widths=[1.5, 1.1, 1.3, 1.0, 1.1])
    item("We confirm that these transactions are not prejudicial to the interests of the "
         "company.")

    # Profit and loss
    w.heading("Profit and Loss Account")
    item("Except as disclosed in the financial statements, the results for the period were not "
         "materially affected by:")
    sub("(a)", "transactions of a nature not usually undertaken by the company;")
    sub("(b)", "circumstances of an exceptional or non-recurring nature;")
    sub("(c)", "charges or credits relating to prior years; or")
    sub("(d)", "changes in accounting policies.")
    item("No personal expenses are charged in the revenue accounts.")

    # General
    w.heading("General")
    item("The company has complied with all the applicable provisions of the Companies Act, "
         "2013.")
    item("The current and non-current classification of assets and liabilities in the "
         "financial statements has been done as per the requirements of Schedule III to the "
         "Companies Act, 2013.")
    item("The financial statements are free of material misstatements and omissions.")
    item("The company has complied with all aspects of contractual agreements that could have a "
         "material effect on the financial statements in the event of non-compliance. There has "
         "been no non-compliance with requirements of regulatory authorities that could have a "
         "material effect on the financial statements in the event of non-compliance.")
    item("The company is regular in depositing undisputed statutory dues including GST, "
         "income-tax and other statutory dues with the appropriate authorities.")
    item("The list of MSME suppliers is given below:")
    w.table(["Name of Supplier", "Nature of Transaction", "Balance Outstanding (Rs.)"],
            blank_rows(3, 3, numbered=False), widths=[2.5, 1.8, 1.7], level=1)
    item("No claims have been raised against the company under the Micro, Small and Medium "
         "Enterprises Development Act, 2006 for interest on delayed payments.")
    item("The company does not have any long-term contracts requiring a provision for material "
         "foreseeable losses.")
    item("The company does not have any amounts required to be transferred to the Investor "
         "Education and Protection Fund.")
    if d["caro_cost"]:
        item("The company has maintained cost records as prescribed by the Central Government "
             "under section 148(1) of the Companies Act, 2013.")
    else:
        item("The company is not required to maintain cost records as prescribed by the Central "
             "Government under section 148(1) of the Companies Act, 2013.")
    item("The company has not had any transaction with struck-off companies.")
    item("The company has not acted as an 'intermediary' for receiving, advancing or investing "
         "monies to or in any other entity.")
    if d["caro_csr"]:
        item("The company has complied with the provisions of section 135 of the Act and there "
             "is no unspent CSR amount requiring transfer. [Review]")
    else:
        item("The provisions of section 135 of the Act are not applicable to the company.")
    item("The company has not had any crypto currency or virtual currency transactions during "
         "the year.")
    item("No unrecorded income has been surrendered or disclosed in any assessment during the "
         "year under the Income Tax Act, 1961.")
    item("The company is capable of meeting its liabilities falling due within a period of one "
         "year from the Balance Sheet date, and the management does not see any material "
         "uncertainty in this regard.")
    item(audit_trail_representation(d))

    # Information provided
    w.heading("Information Provided")
    item("We have provided you with:")
    sub("(a)", "all information, such as records, documentation and other matters, that is "
        "relevant to the preparation and presentation of the financial statements;")
    sub("(b)", "additional information that you have requested from us; and")
    sub("(c)", "unrestricted access to those within the entity.")
    item("All transactions have been recorded in the accounting records and are reflected in "
         "the financial statements.")
    item("We have disclosed to you all information in relation to fraud or suspected fraud "
         "that we are aware of and that affects the entity and involves:")
    sub("(a)", "management;")
    sub("(b)", "employees who have significant roles in internal control; or")
    sub("(c)", "others where the fraud could have a material effect on the financial "
        "statements.")
    item("We have disclosed to you all information in relation to allegations of fraud, or "
         "suspected fraud, affecting the entity's financial statements communicated by "
         "employees, former employees, analysts, regulators or others.")
    item("We have disclosed to you all known instances of non-compliance or suspected "
         "non-compliance with laws and regulations whose effects should be considered when "
         "preparing financial statements.")
    item("We have disclosed to you the identity of the entity's related parties and all the "
         "related party relationships and transactions of which we are aware.")

    w.para("Yours faithfully,")
    w.lines(["For " + d["company"]])
    two_director_signatures(w, d)
    return w.save(path)


# ------------------------------------------------------------
# 8. Independent Auditor's Report  (auditor's letterhead)
# ------------------------------------------------------------

def annexure_letters(d):
    """CARO and IFC annexures are lettered A, B in the order they appear."""
    letters = {}
    next_letter = "A"
    for key in ("caro", "ifc"):
        if d[key]:
            letters[key] = next_letter
            next_letter = chr(ord(next_letter) + 1)
    return letters


def write_main_report(w, d, letters):
    opinion = d["opinion"]
    company = d["company"]

    w.title("INDEPENDENT AUDITOR'S REPORT", size=13)
    w.lines(["To the Members of", company], bold_first=False)
    w.heading("Report on the Audit of the Financial Statements", underline=True)

    # ----- Opinion -----
    if opinion == "Unmodified":
        w.heading("Opinion")
    elif opinion == "Disclaimer":
        w.heading("Disclaimer of Opinion")
    else:
        w.heading(opinion + " Opinion")

    if opinion == "Disclaimer":
        w.para("We were engaged to audit the financial statements of " + company +
               " (\"the Company\"), which comprise " + statements_list(d) + ".")
        w.para("We do not express an opinion on the accompanying financial statements of the "
               "Company. Because of the significance of the matter described in the Basis for "
               "Disclaimer of Opinion section of our report, we have not been able to obtain "
               "sufficient appropriate audit evidence to provide a basis for an audit opinion "
               "on these financial statements.")
    else:
        w.para("We have audited the accompanying financial statements of " + company +
               " (\"the Company\"), which comprise " + statements_list(d) + ".")
        start = ("In our opinion and to the best of our information and according to the "
                 "explanations given to us, ")
        if opinion == "Unmodified":
            w.para(start + "the aforesaid financial statements give the information required "
                   "by the Companies Act, 2013 (\"the Act\") in the manner so required and "
                   "give " + true_and_fair(d) + ".")
        elif opinion == "Qualified":
            w.para(start + "except for the effects of the matter described in the Basis for "
                   "Qualified Opinion section of our report, the aforesaid financial "
                   "statements give the information required by the Companies Act, 2013 "
                   "(\"the Act\") in the manner so required and give " + true_and_fair(d) + ".")
        else:
            w.para(start + "because of the significance of the matter discussed in the Basis "
                   "for Adverse Opinion section of our report, the aforesaid financial "
                   "statements do not give the information required by the Companies Act, "
                   "2013 (\"the Act\") in the manner so required and do not give " +
                   true_and_fair(d) + ".")

    # ----- Basis -----
    if opinion == "Unmodified":
        w.heading("Basis for Opinion")
    elif opinion == "Disclaimer":
        w.heading("Basis for Disclaimer of Opinion")
    else:
        w.heading("Basis for " + opinion + " Opinion")
    if d["basis_text"]:
        w.para(d["basis_text"])
    if opinion != "Disclaimer":
        word = "" if opinion == "Unmodified" else opinion.lower() + " "
        w.para("We conducted our audit in accordance with the Standards on Auditing (SAs) "
               "specified under section 143(10) of the Act. Our responsibilities under those "
               "Standards are further described in the Auditor's Responsibilities for the "
               "Audit of the Financial Statements section of our report. We are independent of "
               "the Company in accordance with the Code of Ethics issued by the Institute of "
               "Chartered Accountants of India together with the ethical requirements that are "
               "relevant to our audit of the financial statements under the provisions of the "
               "Act and the Rules made thereunder, and we have fulfilled our other ethical "
               "responsibilities in accordance with these requirements and the Code of Ethics. "
               "We believe that the audit evidence we have obtained is sufficient and "
               "appropriate to provide a basis for our " + word + "audit opinion on the "
               "financial statements.")

    if d["eom"]:
        w.heading("Emphasis of Matter")
        w.para("We draw attention to the following matter: " + d["eom"] + " Our opinion is "
               "not modified in respect of this matter.")

    if opinion != "Disclaimer":
        w.heading("Information Other than the Financial Statements and Auditor's Report "
                  "Thereon")
        w.para("The Company's Board of Directors is responsible for the other information. The "
               "other information comprises the information included in the Board's Report "
               "including Annexures to Board's Report, but does not include the financial "
               "statements and our auditor's report thereon. Our opinion on the financial "
               "statements does not cover the other information and we do not express any form "
               "of assurance conclusion thereon. In connection with our audit of the financial "
               "statements, our responsibility is to read the other information and, in doing "
               "so, consider whether the other information is materially inconsistent with the "
               "financial statements or our knowledge obtained during the audit or otherwise "
               "appears to be materially misstated. If, based on the work we have performed, we "
               "conclude that there is a material misstatement of this other information, we "
               "are required to report that fact. We have nothing to report in this regard.")

    w.heading("Management's Responsibility for the Financial Statements")
    w.para("The Company's Board of Directors is responsible for the matters stated in section "
           "134(5) of the Act with respect to the preparation of these financial statements "
           "that give a true and fair view of the financial position" +
           (", financial performance and cash flows" if d["cash_flow"]
            else " and financial performance") +
           " of the Company in accordance with the accounting principles generally accepted "
           "in India, including the Accounting Standards specified under section 133 of the "
           "Act. This responsibility also includes maintenance of adequate accounting records "
           "in accordance with the provisions of the Act for safeguarding the assets of the "
           "Company and for preventing and detecting frauds and other irregularities; "
           "selection and application of appropriate accounting policies; making judgments and "
           "estimates that are reasonable and prudent; and design, implementation and "
           "maintenance of adequate internal financial controls, that were operating "
           "effectively for ensuring the accuracy and completeness of the accounting records, "
           "relevant to the preparation and presentation of the financial statements that give "
           "a true and fair view and are free from material misstatement, whether due to fraud "
           "or error.")
    w.para("In preparing the financial statements, management and the Board of Directors are "
           "responsible for assessing the Company's ability to continue as a going concern, "
           "disclosing, as applicable, matters related to going concern and using the going "
           "concern basis of accounting unless management either intends to liquidate the "
           "Company or to cease operations, or has no realistic alternative but to do so. The "
           "Board of Directors is also responsible for overseeing the Company's financial "
           "reporting process.")

    w.heading("Auditor's Responsibilities for the Audit of the Financial Statements")
    if opinion == "Disclaimer":
        w.para("Our responsibility is to conduct an audit of the Company's financial statements "
               "in accordance with Standards on Auditing and to issue an auditor's report. "
               "However, because of the matter described in the Basis for Disclaimer of Opinion "
               "section of our report, we were not able to obtain sufficient appropriate audit "
               "evidence to provide a basis for an audit opinion on these financial statements. "
               "We are independent of the Company in accordance with the Code of Ethics issued "
               "by the Institute of Chartered Accountants of India and the ethical requirements "
               "relevant to our audit under the Act, and we have fulfilled our other ethical "
               "responsibilities.")
    else:
        w.para("Our objectives are to obtain reasonable assurance about whether the financial "
               "statements as a whole are free from material misstatement, whether due to fraud "
               "or error, and to issue an auditor's report that includes our opinion. "
               "Reasonable assurance is a high level of assurance, but is not a guarantee that "
               "an audit conducted in accordance with SAs will always detect a material "
               "misstatement when it exists. Misstatements can arise from fraud or error and "
               "are considered material if, individually or in the aggregate, they could "
               "reasonably be expected to influence the economic decisions of users taken on "
               "the basis of these financial statements.")
        w.para("As part of an audit in accordance with SAs, we exercise professional judgment "
               "and maintain professional skepticism throughout the audit. We also:")
        for text in [
            "Identify and assess the risks of material misstatement of the financial "
            "statements, whether due to fraud or error, design and perform audit procedures "
            "responsive to those risks, and obtain audit evidence that is sufficient and "
            "appropriate to provide a basis for our opinion.",
            "Obtain an understanding of internal control relevant to the audit in order to "
            "design audit procedures that are appropriate in the circumstances.",
            "Evaluate the appropriateness of accounting policies used and the reasonableness of "
            "accounting estimates and related disclosures made by management.",
            "Conclude on the appropriateness of management's use of the going concern basis of "
            "accounting and, based on the audit evidence obtained, whether a material "
            "uncertainty exists related to events or conditions that may cast significant "
            "doubt on the Company's ability to continue as a going concern.",
            "Evaluate the overall presentation, structure and content of the financial "
            "statements, including the disclosures, and whether the financial statements "
            "represent the underlying transactions and events in a manner that achieves fair "
            "presentation.",
        ]:
            w.clause("•", text)

    # ----- Other legal and regulatory requirements -----
    w.heading("Report on Other Legal and Regulatory Requirements", underline=True)
    if d["caro"]:
        w.clause("1.", "As required by the Companies (Auditor's Report) Order, 2020 (\"the "
                 "Order\"), issued by the Central Government of India in terms of sub-section "
                 "(11) of section 143 of the Act, we give in \"Annexure " + letters["caro"] +
                 "\" a statement on the matters specified in paragraphs 3 and 4 of the Order, "
                 "to the extent applicable.")
    else:
        w.clause("1.", "In our opinion, the Companies (Auditor's Report) Order, 2020 (\"the "
                 "Order\"), issued by the Central Government of India in terms of sub-section "
                 "(11) of section 143 of the Act, is not applicable to the Company.")
    w.clause("2.", "As required by section 143(3) of the Act, we report that:")

    if opinion == "Unmodified":
        qualifier = "in our opinion, "
    elif opinion == "Disclaimer":
        qualifier = ("because of the matter described in the Basis for Disclaimer of Opinion "
                     "section above, we are unable to state whether ")
    else:
        qualifier = ("except for the effects of the matter described in the Basis for " +
                     opinion + " Opinion section above, in our opinion, ")

    statements = ("The Balance Sheet, the Statement of Profit and Loss" +
                  (" and the Statement of Cash Flows" if d["cash_flow"] else ""))
    w.clause("(a)", "We have sought and obtained all the information and explanations which to "
             "the best of our knowledge and belief were necessary for the purposes of our "
             "audit.", level=1)
    books = ("In our opinion, proper books of account as required by law have been kept by the "
             "Company so far as it appears from our examination of those books")
    if audit_trail_status(d) != "full":
        books = (books + ", except for the matter stated in paragraph 2(h)(vi) below on "
                 "reporting under Rule 11(g) of the Companies (Audit and Auditors) Rules, 2014")
    w.clause("(b)", books + ".", level=1)
    w.clause("(c)", statements + " dealt with by this Report are in agreement with the books "
             "of account.", level=1)
    w.clause("(d)", qualifier[0].upper() + qualifier[1:] + "the aforesaid financial statements "
             "comply with the Accounting Standards specified under section 133 of the Act, "
             "read with the Companies (Accounting Standards) Rules, 2021.", level=1)
    w.clause("(e)", "On the basis of the written representations received from the directors "
             "as on " + d["year_end"] + " taken on record by the Board of Directors, none of "
             "the directors is disqualified as on " + d["year_end"] + " from being appointed "
             "as a director in terms of section 164(2) of the Act.", level=1)
    if d["ifc"]:
        w.clause("(f)", "With respect to the adequacy of the internal financial controls with "
                 "reference to financial statements of the Company and the operating "
                 "effectiveness of such controls, refer to our separate Report in \"Annexure " +
                 letters["ifc"] + "\".", level=1)
    elif d["private"]:
        w.clause("(f)", "Reporting on the adequacy of internal financial controls with "
                 "reference to financial statements and the operating effectiveness of such "
                 "controls under section 143(3)(i) of the Act is not applicable to the Company "
                 "in view of the exemption available to private companies under notification "
                 "G.S.R. 583(E) dated 13th June 2017.", level=1)
    else:
        w.clause("(f)", "Reporting on the adequacy of internal financial controls with "
                 "reference to financial statements is not applicable to the Company.", level=1)
    if d["private"]:
        w.clause("(g)", "With respect to the other matters to be included in the Auditor's "
                 "Report in accordance with the requirements of section 197(16) of the Act, the "
                 "provisions of section 197 are not applicable to the Company, since it is a "
                 "private company.", level=1)
    else:
        w.clause("(g)", "In our opinion and according to the information and explanations given "
                 "to us, the remuneration paid by the Company to its directors during the year "
                 "is in accordance with the provisions of section 197 of the Act.", level=1)
    w.clause("(h)", "With respect to the other matters to be included in the Auditor's Report "
             "in accordance with Rule 11 of the Companies (Audit and Auditors) Rules, 2014, in "
             "our opinion and to the best of our information and according to the "
             "explanations given to us:", level=1)
    if d["litigation"]:
        w.clause("i.", "The Company has disclosed the impact of pending litigations on its "
                 "financial position in its financial statements. [Refer Note __]", level=2)
    else:
        w.clause("i.", "The Company does not have any pending litigations which would impact "
                 "its financial position.", level=2)
    w.clause("ii.", "The Company did not have any long-term contracts including derivative "
             "contracts for which there were any material foreseeable losses.", level=2)
    w.clause("iii.", "There were no amounts which were required to be transferred to the "
             "Investor Education and Protection Fund by the Company.", level=2)
    w.clause("iv.", "(a) The management has represented that, to the best of its knowledge and "
             "belief, no funds have been advanced or loaned or invested by the Company to or in "
             "any other person or entity, including foreign entities (Intermediaries), with the "
             "understanding that the Intermediary shall lend or invest in other persons or "
             "entities identified by or on behalf of the Company (Ultimate Beneficiaries) or "
             "provide any guarantee, security or the like on behalf of the Ultimate "
             "Beneficiaries; (b) the management has represented that, to the best of its "
             "knowledge and belief, no funds have been received by the Company from any person "
             "or entity, including foreign entities (Funding Parties), with the understanding "
             "that the Company shall lend or invest in other persons or entities identified by "
             "or on behalf of the Funding Party or provide any guarantee, security or the like "
             "on behalf of the Ultimate Beneficiaries; and (c) based on the audit procedures "
             "performed, nothing has come to our notice that has caused us to believe that the "
             "representations under (a) and (b) above contain any material misstatement.",
             level=2)
    w.clause("v.", "The Company has not declared or paid any dividend during the year.",
             level=2)
    w.clause("vi.", audit_trail_report(d), level=2)

    w.lines(auditor_signature(d, d["report_date"], with_udin=True))


def caro_clauses(d):
    """Return the CARO 2020 paragraph 3 as a list of (label, text, level)."""
    c = []
    ye = d["year_end"]

    # (i) Property, plant and equipment
    if d["caro_ppe"]:
        c.append(("(i)", "In respect of the Company's Property, Plant and Equipment and "
                  "intangible assets:", 0))
        c.append(("(a)", "(A) The Company has maintained proper records showing full "
                  "particulars, including quantitative details and situation of Property, "
                  "Plant and Equipment.", 1))
        if d["caro_intangible"]:
            c.append(("", "(B) The Company has maintained proper records showing full "
                      "particulars of intangible assets.", 1))
        else:
            c.append(("", "(B) The Company does not have any intangible assets; hence "
                      "reporting under clause 3(i)(a)(B) of the Order is not applicable.", 1))
        c.append(("(b)", "The Property, Plant and Equipment have been physically verified by "
                  "the management at reasonable intervals and no material discrepancies were "
                  "noticed on such verification.", 1))
        if d["caro_property"]:
            c.append(("(c)", "The title deeds of all the immovable properties (other than "
                      "properties where the Company is the lessee and the lease agreements are "
                      "duly executed in favour of the lessee) disclosed in the financial "
                      "statements are held in the name of the Company.", 1))
        else:
            c.append(("(c)", "The Company does not hold any immovable property; hence "
                      "reporting under clause 3(i)(c) of the Order is not applicable.", 1))
        c.append(("(d)", "The Company has not revalued its Property, Plant and Equipment or "
                  "intangible assets during the year.", 1))
        c.append(("(e)", "No proceedings have been initiated or are pending against the Company "
                  "for holding any benami property under the Prohibition of Benami Property "
                  "Transactions Act, 1988 and the rules made thereunder.", 1))
    else:
        c.append(("(i)", "The Company does not hold any Property, Plant and Equipment or "
                  "intangible assets. Further, no proceedings have been initiated or are "
                  "pending against the Company for holding any benami property under the "
                  "Prohibition of Benami Property Transactions Act, 1988. Accordingly, "
                  "reporting under clause 3(i)(a) to (d) of the Order is not applicable.", 0))

    # (ii) Inventory and working capital
    c.append(("(ii)", "", 0))
    if d["caro_inventory"]:
        c.append(("(a)", "The inventory has been physically verified by the management during "
                  "the year at reasonable intervals. In our opinion, the coverage and procedure "
                  "of such verification by the management is appropriate. No discrepancies of "
                  "10% or more in the aggregate for each class of inventory were noticed.", 1))
    else:
        c.append(("(a)", "The Company does not hold any inventory; hence reporting under "
                  "clause 3(ii)(a) of the Order is not applicable.", 1))
    if d["caro_wc"]:
        c.append(("(b)", "The Company has been sanctioned working capital limits in excess of "
                  "₹5 crore, in aggregate, from banks or financial institutions on the "
                  "basis of security of current assets. The quarterly returns or statements "
                  "filed by the Company with such banks or financial institutions are in "
                  "agreement with the books of account of the Company. [Review]", 1))
    else:
        c.append(("(b)", "The Company has not been sanctioned working capital limits in excess "
                  "of ₹5 crore, in aggregate, from banks or financial institutions on the "
                  "basis of security of current assets. Accordingly, reporting under clause "
                  "3(ii)(b) of the Order is not applicable.", 1))

    # (iii) and (iv) Loans, investments, guarantees
    if d["caro_loans"]:
        c.append(("(iii)", "[Report the investments made, guarantees or security provided and "
                  "loans or advances in the nature of loans granted during the year, as "
                  "required by clauses 3(iii)(a) to (f) of the Order.]", 0))
        c.append(("(iv)", "In our opinion and according to the information and explanations "
                  "given to us, in respect of loans, investments, guarantees and security, the "
                  "Company has complied with the provisions of sections 185 and 186 of the Act, "
                  "to the extent applicable.", 0))
    else:
        c.append(("(iii)", "During the year, the Company has not made investments in, provided "
                  "any guarantee or security, or granted any loans or advances in the nature of "
                  "loans, secured or unsecured, to companies, firms, limited liability "
                  "partnerships or any other parties. Accordingly, reporting under clause "
                  "3(iii)(a) to (f) of the Order is not applicable.", 0))
        c.append(("(iv)", "The Company has not granted any loans, made any investments or "
                  "provided any guarantees or security covered under sections 185 and 186 of "
                  "the Act. Accordingly, reporting under clause 3(iv) of the Order is not "
                  "applicable.", 0))

    # (v) Deposits
    if d["caro_deposits"]:
        c.append(("(v)", "[Report compliance with the directives issued by the Reserve Bank of "
                  "India and the provisions of sections 73 to 76 of the Act and the rules "
                  "framed thereunder in respect of deposits accepted.]", 0))
    else:
        c.append(("(v)", "The Company has not accepted any deposits or amounts which are deemed "
                  "to be deposits within the meaning of sections 73 to 76 of the Act and the "
                  "rules made thereunder. Accordingly, reporting under clause 3(v) of the Order "
                  "is not applicable.", 0))

    # (vi) Cost records
    if d["caro_cost"]:
        c.append(("(vi)", "We have broadly reviewed the cost records maintained by the Company "
                  "as specified by the Central Government under section 148(1) of the Act and "
                  "are of the opinion that, prima facie, the prescribed accounts and records "
                  "have been made and maintained. We have not, however, made a detailed "
                  "examination of the cost records with a view to determine whether they are "
                  "accurate or complete.", 0))
    else:
        c.append(("(vi)", "The maintenance of cost records has not been specified by the Central "
                  "Government under section 148(1) of the Act for the business activities "
                  "carried out by the Company. Accordingly, reporting under clause 3(vi) of the "
                  "Order is not applicable.", 0))

    # (vii) Statutory dues
    c.append(("(vii)", "In respect of statutory dues:", 0))
    if d["caro_dues_arrear"]:
        c.append(("(a)", "The Company has not been regular in depositing undisputed statutory "
                  "dues. The undisputed amounts payable in respect of statutory dues which were "
                  "in arrears as at " + ye + " for a period of more than six months from the "
                  "date they became payable are as follows: [Insert table: Name of statute, "
                  "Nature of dues, Amount, Period, Due date, Date of payment]", 1))
    else:
        c.append(("(a)", "The Company has generally been regular in depositing undisputed "
                  "statutory dues, including Goods and Services Tax, provident fund, employees' "
                  "state insurance, income-tax, duty of customs, cess and other material "
                  "statutory dues applicable to it with the appropriate authorities. There were "
                  "no undisputed amounts payable in respect of the above which were in arrears "
                  "as at " + ye + " for a period of more than six months from the date they "
                  "became payable.", 1))
    if d["caro_dues_dispute"]:
        c.append(("(b)", "The statutory dues referred to in sub-clause (a) which have not been "
                  "deposited on account of any dispute are as follows: [Insert table: Name of "
                  "statute, Nature of dues, Amount, Period, Forum where dispute is pending]", 1))
    else:
        c.append(("(b)", "There are no statutory dues referred to in sub-clause (a) which have "
                  "not been deposited on account of any dispute.", 1))

    # (viii) Unrecorded income
    c.append(("(viii)", "There were no transactions relating to previously unrecorded income "
              "that have been surrendered or disclosed as income during the year in the tax "
              "assessments under the Income Tax Act, 1961.", 0))

    # (ix) Borrowings
    if d["caro_borrow"]:
        c.append(("(ix)", "In respect of borrowings:", 0))
        c.append(("(a)", "The Company has not defaulted in the repayment of loans or other "
                  "borrowings or in the payment of interest thereon to any lender.", 1))
        c.append(("(b)", "The Company has not been declared a wilful defaulter by any bank or "
                  "financial institution or government or government authority.", 1))
        c.append(("(c)", "The term loans have been applied for the purpose for which they were "
                  "obtained.", 1))
        c.append(("(d)", "On an overall examination of the financial statements, funds raised "
                  "on short-term basis have not been utilised for long-term purposes.", 1))
        c.append(("(e)", "The Company does not have any subsidiaries, associates or joint "
                  "ventures. Accordingly, reporting under clauses 3(ix)(e) and (f) of the Order "
                  "is not applicable.", 1))
    else:
        c.append(("(ix)", "The Company has not taken any loans or other borrowings from any "
                  "lender. Accordingly, reporting under clause 3(ix) of the Order is not "
                  "applicable.", 0))

    # (x) Raising of money
    c.append(("(x)", "", 0))
    c.append(("(a)", "The Company has not raised moneys by way of initial public offer or "
              "further public offer (including debt instruments) during the year. Accordingly, "
              "reporting under clause 3(x)(a) of the Order is not applicable.", 1))
    c.append(("(b)", "The Company has not made any preferential allotment or private placement "
              "of shares or convertible debentures (fully, partially or optionally convertible) "
              "during the year. Accordingly, reporting under clause 3(x)(b) of the Order is not "
              "applicable.", 1))

    # (xi) Fraud
    c.append(("(xi)", "", 0))
    c.append(("(a)", "No fraud by the Company and no fraud on the Company has been noticed or "
              "reported during the year.", 1))
    c.append(("(b)", "No report under sub-section (12) of section 143 of the Act has been filed "
              "by the auditors in Form ADT-4 as prescribed under rule 13 of the Companies (Audit "
              "and Auditors) Rules, 2014 with the Central Government.", 1))
    c.append(("(c)", "As represented to us by the management, there are no whistle-blower "
              "complaints received by the Company during the year.", 1))

    # (xii) Nidhi
    c.append(("(xii)", "The Company is not a Nidhi Company. Accordingly, reporting under clause "
              "3(xii) of the Order is not applicable.", 0))

    # (xiii) Related parties
    if d["private"]:
        c.append(("(xiii)", "In our opinion, the Company is in compliance with section 188 of "
                  "the Act, where applicable, for all transactions with related parties, and "
                  "the details of related party transactions have been disclosed in the "
                  "financial statements as required by AS 18, Related Party Disclosures. The "
                  "provisions of section 177 of the Act are not applicable to the Company.", 0))
    else:
        c.append(("(xiii)", "In our opinion, the Company is in compliance with sections 177 and "
                  "188 of the Act, where applicable, for all transactions with related parties, "
                  "and the details of related party transactions have been disclosed in the "
                  "financial statements as required by AS 18, Related Party Disclosures.", 0))

    # (xiv) Internal audit
    if d["caro_ia"]:
        c.append(("(xiv)", "", 0))
        c.append(("(a)", "In our opinion, the Company has an internal audit system commensurate "
                  "with the size and nature of its business.", 1))
        c.append(("(b)", "We have considered the reports of the internal auditors for the "
                  "period under audit.", 1))
    else:
        c.append(("(xiv)", "In our opinion, the Company is not required to have an internal "
                  "audit system under section 138 of the Act. Accordingly, reporting under "
                  "clause 3(xiv) of the Order is not applicable.", 0))

    # (xv) Non-cash transactions
    c.append(("(xv)", "The Company has not entered into any non-cash transactions with its "
              "directors or persons connected with them. Accordingly, reporting under clause "
              "3(xv) of the Order is not applicable.", 0))

    # (xvi) RBI registration
    c.append(("(xvi)", "", 0))
    c.append(("(a)", "The Company is not required to be registered under section 45-IA of the "
              "Reserve Bank of India Act, 1934.", 1))
    c.append(("(b)", "The Company has not conducted any Non-Banking Financial or Housing Finance "
              "activities during the year.", 1))
    c.append(("(c)", "The Company is not a Core Investment Company (CIC) as defined in the "
              "regulations made by the Reserve Bank of India. Accordingly, reporting under "
              "clauses 3(xvi)(c) and (d) of the Order is not applicable.", 1))

    # (xvii) Cash losses
    if d["caro_cashloss"]:
        c.append(("(xvii)", "The Company has incurred cash losses of ₹[______] in the "
                  "current financial year and ₹[______] in the immediately preceding "
                  "financial year.", 0))
    else:
        c.append(("(xvii)", "The Company has not incurred cash losses in the current financial "
                  "year and in the immediately preceding financial year.", 0))

    # (xviii) Resignation of auditors
    c.append(("(xviii)", "There has been no resignation of the statutory auditors during the "
              "year. Accordingly, reporting under clause 3(xviii) of the Order is not "
              "applicable.", 0))

    # (xix) Material uncertainty
    c.append(("(xix)", "On the basis of the financial ratios, ageing and expected dates of "
              "realisation of financial assets and payment of financial liabilities, other "
              "information accompanying the financial statements, our knowledge of the Board "
              "of Directors and management plans, we are of the opinion that no material "
              "uncertainty exists as on the date of the audit report that the Company is not "
              "capable of meeting its liabilities existing at the date of the balance sheet as "
              "and when they fall due within a period of one year from the balance sheet date. "
              "We, however, state that this is not an assurance as to the future viability of "
              "the Company.", 0))

    # (xx) CSR
    if d["caro_csr"]:
        c.append(("(xx)", "", 0))
        c.append(("(a)", "There is no unspent amount towards Corporate Social Responsibility "
                  "(CSR) on other than ongoing projects requiring a transfer to a Fund specified "
                  "in Schedule VII to the Act in compliance with second proviso to section "
                  "135(5) of the Act. [Review]", 1))
        c.append(("(b)", "There is no unspent amount under section 135(5) of the Act pursuant to "
                  "any ongoing project. [Review]", 1))
    else:
        c.append(("(xx)", "The provisions of section 135 of the Act are not applicable to the "
                  "Company. Accordingly, reporting under clause 3(xx) of the Order is not "
                  "applicable.", 0))

    # (xxi) Consolidated financial statements
    c.append(("(xxi)", "The reporting under clause 3(xxi) of the Order is not applicable in "
              "respect of the audit of standalone financial statements.", 0))
    return c


def write_caro_annexure(w, d, letter):
    w.page_break()
    w.title("ANNEXURE \"" + letter + "\" TO THE INDEPENDENT AUDITOR'S REPORT", size=11)
    w.para("(Referred to in paragraph 1 under 'Report on Other Legal and Regulatory "
           "Requirements' section of our report to the Members of " + d["company"] +
           " of even date)")
    w.para("To the best of our information and according to the explanations provided to us by "
           "the Company and the books of account and records examined by us in the normal "
           "course of audit, we state that:")
    for label, text, level in caro_clauses(d):
        if label == "":
            w.clause("", text, level=level)
        elif text == "":
            p = w.doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = True
            p.add_run(label)
        else:
            w.clause(label, text, level=level)
    w.lines(auditor_signature(d, d["report_date"], with_udin=True))


def write_ifc_annexure(w, d, letter):
    w.page_break()
    w.title("ANNEXURE \"" + letter + "\" TO THE INDEPENDENT AUDITOR'S REPORT", size=11)
    w.para("(Referred to in paragraph 2(f) under 'Report on Other Legal and Regulatory "
           "Requirements' section of our report to the Members of " + d["company"] +
           " of even date)")
    w.title("Report on the Internal Financial Controls with reference to financial statements "
            "under Clause (i) of Sub-section 3 of Section 143 of the Companies Act, 2013",
            size=10.5)
    w.heading("Opinion")
    w.para("We have audited the internal financial controls with reference to financial "
           "statements of " + d["company"] + " (\"the Company\") as of " + d["year_end"] +
           " in conjunction with our audit of the financial statements of the Company for the "
           "year ended on that date.")
    w.para("In our opinion, the Company has, in all material respects, adequate internal "
           "financial controls with reference to financial statements and such internal "
           "financial controls were operating effectively as at " + d["year_end"] + ", based "
           "on the internal control with reference to financial statements criteria "
           "established by the Company considering the essential components of internal "
           "control stated in the Guidance Note on Audit of Internal Financial Controls Over "
           "Financial Reporting issued by the Institute of Chartered Accountants of India "
           "(\"the Guidance Note\").")
    w.heading("Management's Responsibility for Internal Financial Controls")
    w.para("The Company's Board of Directors is responsible for establishing and maintaining "
           "internal financial controls based on the internal control with reference to "
           "financial statements criteria established by the Company considering the essential "
           "components of internal control stated in the Guidance Note. These responsibilities "
           "include the design, implementation and maintenance of adequate internal financial "
           "controls that were operating effectively for ensuring the orderly and efficient "
           "conduct of its business, including adherence to the Company's policies, the "
           "safeguarding of its assets, the prevention and detection of frauds and errors, the "
           "accuracy and completeness of the accounting records, and the timely preparation of "
           "reliable financial information, as required under the Act.")
    w.heading("Auditor's Responsibility")
    w.para("Our responsibility is to express an opinion on the Company's internal financial "
           "controls with reference to financial statements based on our audit. We conducted "
           "our audit in accordance with the Guidance Note and the Standards on Auditing, "
           "prescribed under section 143(10) of the Act, to the extent applicable to an audit "
           "of internal financial controls. Those Standards and the Guidance Note require that "
           "we comply with ethical requirements and plan and perform the audit to obtain "
           "reasonable assurance about whether adequate internal financial controls with "
           "reference to financial statements were established and maintained and if such "
           "controls operated effectively in all material respects.")
    w.para("We believe that the audit evidence we have obtained is sufficient and appropriate "
           "to provide a basis for our audit opinion on the Company's internal financial "
           "controls with reference to financial statements.")
    w.heading("Meaning of Internal Financial Controls with reference to Financial Statements")
    w.para("A company's internal financial control with reference to financial statements is a "
           "process designed to provide reasonable assurance regarding the reliability of "
           "financial reporting and the preparation of financial statements for external "
           "purposes in accordance with generally accepted accounting principles. It includes "
           "those policies and procedures that (1) pertain to the maintenance of records that, "
           "in reasonable detail, accurately and fairly reflect the transactions and "
           "dispositions of the assets of the company; (2) provide reasonable assurance that "
           "transactions are recorded as necessary to permit preparation of financial "
           "statements in accordance with generally accepted accounting principles, and that "
           "receipts and expenditures of the company are being made only in accordance with "
           "authorisations of management and directors of the company; and (3) provide "
           "reasonable assurance regarding prevention or timely detection of unauthorised "
           "acquisition, use, or disposition of the company's assets that could have a "
           "material effect on the financial statements.")
    w.heading("Inherent Limitations of Internal Financial Controls with reference to Financial "
              "Statements")
    w.para("Because of the inherent limitations of internal financial controls with reference "
           "to financial statements, including the possibility of collusion or improper "
           "management override of controls, material misstatements due to error or fraud may "
           "occur and not be detected. Also, projections of any evaluation of the internal "
           "financial controls with reference to financial statements to future periods are "
           "subject to the risk that the internal financial control with reference to "
           "financial statements may become inadequate because of changes in conditions, or "
           "that the degree of compliance with the policies or procedures may deteriorate.")
    w.lines(auditor_signature(d, d["report_date"], with_udin=True))


def make_audit_report(d, path):
    w = Writer()
    w.auditor_letterhead(d)
    w.page_numbers()
    letters = annexure_letters(d)
    write_main_report(w, d, letters)
    if d["caro"]:
        write_caro_annexure(w, d, letters["caro"])
    if d["ifc"]:
        write_ifc_annexure(w, d, letters["ifc"])
    return w.save(path)


# Company facts that drive CARO 2020 and the Letter of Representation
# (key, label shown on screen, ticked by default)
CARO_ITEMS = [
    ("caro_ppe", "Holds Property, Plant & Equipment", True),
    ("caro_intangible", "Holds intangible assets", False),
    ("caro_property", "Holds immovable property (title deeds)", False),
    ("caro_inventory", "Holds inventory", False),
    ("caro_wc", "Working capital limits above ₹5 crore", False),
    ("caro_loans", "Loans / investments / guarantees given", False),
    ("caro_deposits", "Accepted deposits", False),
    ("caro_cost", "Cost records required u/s 148", False),
    ("caro_dues_arrear", "Undisputed dues outstanding > 6 months", False),
    ("caro_dues_dispute", "Disputed statutory dues pending", False),
    ("caro_borrow", "Has loans / borrowings", False),
    ("caro_ia", "Internal audit required u/s 138", False),
    ("caro_cashloss", "Cash losses (this year or last year)", False),
    ("caro_csr", "CSR applicable u/s 135", False),
]
