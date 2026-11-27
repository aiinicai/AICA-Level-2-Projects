"""Shared cell styles (Cambria for the firm's working sheets, as in the master format)."""
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

ACC = '_ * #,##0_ ;_ * \\-#,##0_ ;_ * "-"??_ ;_ @_ '
PCT = '0.00%'
X2 = '0.00"x"'
DAYS = '0'

F_TITLE = Font(name="Cambria", size=14, bold=True)
F_HEAD = Font(name="Cambria", size=12, bold=True)
F_BODY = Font(name="Cambria", size=12)
F_SMALL = Font(name="Cambria", size=10, italic=True, color="595959")
F_NOTE = Font(name="Cambria", size=10, color="7F7F7F")
F_INPUT = Font(name="Cambria", size=12, color="0000FF")
F_GREEN = Font(name="Cambria", size=12, color="00804D")
F_WHITE = Font(name="Cambria", size=12, bold=True, color="FFFFFF")
FILL_INPUT = PatternFill("solid", fgColor="FFF2CC")
FILL_HEAD = PatternFill("solid", fgColor="1F3864")
FILL_SUB = PatternFill("solid", fgColor="DDEBF7")
FILL_PASS = PatternFill("solid", fgColor="C6EFCE")
FILL_FAIL = PatternFill("solid", fgColor="FFC7CE")
FILL_AMBER = PatternFill("solid", fgColor="FFEB9C")
THIN = Side(style="thin", color="000000")
B_TOP = Border(top=THIN)
B_TOPBOT = Border(top=THIN, bottom=Side(style="double", color="000000"))
B_BOTTOM = Border(bottom=THIN)
B_BOX = Border(top=Side(style="thin", color="BFBFBF"), bottom=Side(style="thin", color="BFBFBF"),
               left=Side(style="thin", color="BFBFBF"), right=Side(style="thin", color="BFBFBF"))
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
WRAP = Alignment(wrap_text=True, vertical="top")
RIGHT = Alignment(horizontal="right")


def put(ws, ref, value, font=F_BODY, fmt=None, fill=None, align=None, border=None):
    if isinstance(font, str):            # a number format given in the font's place
        font, fmt = F_BODY, fmt or font
    c = ws[ref]
    c.value = value
    c.font = font
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = fill
    if align:
        c.alignment = align
    if border:
        c.border = border
    return c


def inp(ws, ref, value, fmt=None):
    return put(ws, ref, value, F_INPUT, fmt, FILL_INPUT)


def clean_empty(wb):
    """Excel reports a damaged file for text cells holding an empty string: make them truly empty."""
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value == "":
                    c.value = None


def to_cambria(wb):
    """One font for the whole workbook (size, bold, colour kept)."""
    from copy import copy
    cache = {}
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                f = c.font
                if f is not None and f.name != "Cambria":
                    k = id(f)
                    if k not in cache:
                        nf = copy(f)
                        nf.name = "Cambria"
                        nf.family = None
                        nf.scheme = None
                        cache[k] = nf
                    c.font = cache[k]
        for cf in ws.conditional_formatting:
            for rule in cf.rules:
                if rule.dxf is not None and rule.dxf.font is not None and rule.dxf.font.name:
                    rule.dxf.font.name = "Cambria"
