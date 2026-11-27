"""Read the positioned text in the management system's rotated cash-flow reports."""
from datetime import datetime
from decimal import Decimal
from io import BytesIO
import re

from pypdf import PdfReader
from sources import InputError


def positioned_lines(page):
    """Measure the WinAnsi Tj/TJ runs using the widths embedded in this ERP layout."""
    fonts = page["/Resources"]["/Font"]
    glyphs = []
    font = None
    size, spacing, word_spacing = 1, 0, 0
    def visit(op, args, cm, tm):
        nonlocal font, size, spacing, word_spacing
        if op == b"Tf":
            font, size = fonts[args[0]].get_object(), float(args[1])
        elif op == b"Tc":
            spacing = float(args[0])
        elif op == b"Tw":
            word_spacing = float(args[0])
        elif op in (b"TJ", b"Tj"):
            # These reports draw vertically in PDF coordinates and rotate the page 90°.
            if page.rotation != 90 or abs(tm[0]) > .01 or cm != [1, 0, 0, 1, 0, 0]:
                raise InputError("Unsupported ERP PDF text orientation. Use the original cash-flow PDF export.")
            if not font or "/Widths" not in font:
                raise InputError("ERP PDF is missing the embedded character widths.")
            widths, first = font["/Widths"], int(font["/FirstChar"])
            x, y, scale = tm[5], tm[4], tm[1]
            runs = args[0] if op == b"TJ" else [args[0]]
            for run in runs:
                if isinstance(run, (bytes, str)):
                    raw = run if isinstance(run, bytes) else run.original_bytes
                    for code in raw:
                        char = bytes([code]).decode("cp1252", errors="replace")
                        width = size * float(widths[code-first]) / 1000
                        glyphs.append((y, x, x+width*scale, char))
                        x += (width + spacing + (word_spacing if code == 32 else 0)) * scale
                else:
                    x -= float(run) * size * scale / 1000
    page.extract_text(visitor_operand_before=visit)
    lines = []
    for y,x,right,char in sorted(glyphs):
        if not lines or y - lines[-1][0] > 3:
            lines.append((y, []))
        lines[-1][1].append((x,right,char))
    return [sorted(line) for _,line in lines]


def phrase(chars):
    text, previous = "", None
    for x,right,char in chars:
        if previous is not None and x-previous > 1.6:
            text += " "
        text += char
        previous = right
    return " ".join(text.split())


def read_flow(source):
    reader = PdfReader(BytesIO(source.data))
    records, months, period = [], [], None
    for number,page in enumerate(reader.pages, 1):
        lines = positioned_lines(page)
        heads = []
        for line in lines:
            text = phrase(line)
            match = re.search(r"CASH FLOW FROM\s+(\d\d/\d\d/\d{4})\s+TO\s+(\d\d/\d\d/\d{4})", text, re.I)
            if match:
                dates = tuple(datetime.strptime(s,"%d/%m/%Y").date() for s in match.groups())
                if period and dates != period:
                    raise InputError(f"{source.name} — reporting dates change on page {number}.")
                period = dates
            if not text.startswith("Description"):
                continue
            # Heading positions locate numeric columns even when text objects are drawn out of order.
            letters = "".join(ch for _,_,ch in line)
            for match in re.finditer(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{2})",letters):
                m = datetime.strptime(" ".join(match.groups()),"%b %y").date()
                heads.append((line[match.end()-1][1],m))
            break
        if not heads:
            raise InputError(f"{source.name}, page {number} — could not locate month headings.")
        new_months = [m for _,m in heads]
        if months and months != new_months:
            raise InputError(f"{source.name} — inconsistent period columns.")
        months = new_months
        for line in lines:
            # This ERP right-aligns numbers under the right edge of each month label.
            groups = []
            for x,right,ch in line:
                if not groups or x-groups[-1][-1][1] > 2.8 or ch.isspace():
                    groups.append([])
                if not ch.isspace():
                    groups[-1].append((x,right,ch))
                elif not groups[-1]:
                    groups[-1].append((x,right,ch))
            vals = {}
            others = []
            for group in groups:
                word = "".join(ch for _,_,ch in group).strip()
                right = group[-1][1]
                col = min(range(len(heads)),key=lambda i:abs(heads[i][0]-right))
                if re.fullmatch(r"-?[\d,]+\.\d{3}",word) and abs(heads[col][0]-right)<10:
                    if col in vals:
                        raise InputError(f"{source.name}, page {number} — overlapping amount columns.")
                    vals[col]=Decimal(word.replace(",",""))
                elif group[0][0]<heads[0][0]-20:
                    others.extend(group)
                elif re.fullmatch(r"-?[\d,]+\.\d{3}", word) and Decimal(word.replace(",","")):
                    raise InputError(f"{source.name}, page {number} — nonzero amount outside month headings.")
            if vals:
                label=phrase(others)
                records.append((label, [vals.get(i) for i in range(len(heads))], number))
    if not period:
        raise InputError(f"{source.name} — could not establish internal reporting dates.")
    return period, months, records


def cheques(source):
    rows, printed, end = [], [], None
    for page_number, page in enumerate(PdfReader(BytesIO(source.data)).pages, 1):
        text = page.extract_text(extraction_mode="layout")
        dates = re.search(r"Cheque Date period\s+[\d/]+\s*-\s*([\d/]+)",text,re.I)
        if dates:
            end = datetime.strptime(dates[1],"%d/%m/%Y").date()
        current = None
        for line in text.splitlines():
            match = re.match(r"\s*\d+\s+PDCP\s+\d+\s+[\d/]+\s+(\d+)\s+([\d/]+)\s+\S+\s+(.+?)\s+([\d,]+\.\d{3})\s*$",line)
            if match:
                ref,day,party,value = match.groups()
                current = dict(ref=ref,day=datetime.strptime(day,"%d/%m/%Y").date(),party=party.strip(),
                               amount=Decimal(value.replace(",","")),note="",page=page_number)
                rows.append(current)
            elif "Total" in line and re.search(r"Total\s*(?:for|:-)",line,re.I):
                current = None
            elif current:
                current["note"] += " " + line.strip()
        printed += re.findall(r"Total\s*:-\s*([\d,]+\.\d{3})", text)
    total = sum(x["amount"] for x in rows)
    if not end or len(printed)!=1 or total!=Decimal(printed[0].replace(",","")) or len({x["ref"] for x in rows})!=len(rows):
        raise InputError(f"{source.name} — cheque detail, unique references or printed total failed reconciliation.")
    return end, rows
