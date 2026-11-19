

# ===========================================================================
# SECTION 3 - WORD (.docx) WRITER
# ---------------------------------------------------------------------------
# A .docx is a ZIP of XML parts.  Writing those parts directly keeps the file
# genuine, needs no third-party document library, and gives exact control over
# row heights and spacing, which is what keeps every letter on one page.
# ===========================================================================

def xml_escape(value):
    text = str("" if value is None else value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;")
                .replace("'", "&apos;"))


def _run(text, bold=False, italic=False, size=None, color=None):
    """One run of text.  rPr children must follow the schema order."""
    props = ""
    if bold:
        props += "<w:b/>"
    if italic:
        props += "<w:i/>"
    if color:
        props += '<w:color w:val="%s"/>' % color
    if size:
        props += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size)
    rpr = ("<w:rPr>%s</w:rPr>" % props) if props else ""
    return ('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>'
            % (rpr, xml_escape(text)))


def _para(runs, before=0, after=120, line=264, justify=None, indent=0,
          hanging=0, keep_next=False, keep_lines=False, rule=False):
    """One paragraph.  pPr children must follow the schema order."""
    props = ""
    if keep_next:
        props += "<w:keepNext/>"
    if keep_lines:
        props += "<w:keepLines/>"
    if rule:
        props += ('<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="3" '
                  'w:color="9A9A9A"/></w:pBdr>')
    props += ('<w:spacing w:before="%d" w:after="%d" w:line="%d" '
              'w:lineRule="auto"/>' % (before, after, line))
    if indent:
        props += '<w:ind w:left="%d"%s/>' % (
            indent, (' w:hanging="%d"' % hanging) if hanging else "")
    if justify:
        props += '<w:jc w:val="%s"/>' % justify
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % (props, runs or "")


# ---------------------------------------------------------------- layout
def _slip_table(rows, compact=False):
    """Borderless two-column grid: 'Name and Title   :  ______'."""
    borders = "".join(
        '<w:%s w:val="none" w:sz="0" w:space="0" w:color="auto"/>' % side
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"))
    xml = ('<w:tbl><w:tblPr><w:tblW w:w="6600" w:type="dxa"/>'
           '<w:tblBorders>%s</w:tblBorders><w:tblLayout w:type="fixed"/>'
           '<w:tblCellMar><w:left w:w="0" w:type="dxa"/>'
           '<w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
           '<w:tblLook w:val="0000"/></w:tblPr>'
           '<w:tblGrid><w:gridCol w:w="2600"/><w:gridCol w:w="4000"/>'
           '</w:tblGrid>' % borders)
    for label in rows:
        xml += ('<w:tr><w:trPr><w:cantSplit/><w:trHeight w:val="%d" '
                'w:hRule="atLeast"/></w:trPr>'
                '<w:tc><w:tcPr><w:tcW w:w="2600" w:type="dxa"/></w:tcPr>%s</w:tc>'
                '<w:tc><w:tcPr><w:tcW w:w="4000" w:type="dxa"/></w:tcPr>%s</w:tc>'
                '</w:tr>'
                % (300 if compact else 340,
                   _para(_run(label), after=0, line=240),
                   _para(_run(":  ______________________"), after=0, line=240)))
    return xml + "</w:tbl>"


def document_xml(model):
    compact = model.get("compact")
    scale = 0.78 if compact else 1.0

    def sp(value):
        return int(round(value * scale))

    body = ""
    if model.get("letterhead_note"):
        body += _para(_run(model["letterhead_note"]), justify="center",
                      after=sp(40), line=240)
    body += _para(_run(model["title"], bold=True), justify="center",
                  after=sp(260), line=240, keep_next=True)
    body += _para(_run(model["date_line"]), justify="right",
                  after=0 if model.get("reference_line") else sp(60), line=240)
    if model.get("reference_line"):
        # quoted back by the party, and what ties their reply to this letter
        body += _para(_run(model["reference_line"]), justify="right",
                      after=sp(60), line=240)
    last = len(model["party_block"]) - 1
    for i, line in enumerate(model["party_block"]):
        body += _para(_run(line["text"], bold=line["bold"]),
                      after=sp(240) if i == last else 0, line=240)
    body += _para(_run(model["salutation"]), after=sp(200), line=240)
    for i, text in enumerate(model["paras"]):
        body += _para(_run(text), justify="both",
                      after=sp(150 if i == len(model["paras"]) - 1 else 200),
                      keep_next=i == len(model["paras"]) - 1)
    last = len(model["auditor_block"]) - 1
    for i, line in enumerate(model["auditor_block"]):
        body += _para(_run(line["text"], bold=line["bold"]),
                      after=sp(200) if i == last else 0, line=240)
    for text in model["closing_paras"]:
        body += _para(_run(text), justify="both", after=sp(200))
    last = len(model["signature"]) - 1
    for i, line in enumerate(model["signature"]):
        body += _para(_run(line["text"], bold=line["bold"]),
                      before=sp(360) if line.get("gap") else 0,
                      after=sp(420) if i == last else sp(20), line=240,
                      keep_lines=True, keep_next=i < last)
    body += _para(_run(model["slip"]["sentence"]), justify="both",
                  after=sp(160), keep_next=True)
    body += _slip_table(model["slip"]["rows"], compact)
    body += '<w:p><w:pPr><w:spacing w:after="0"/></w:pPr></w:p>'

    margin = 1021 if compact else 1134        # 1.8 cm when tight, else 2 cm
    top = margin if model.get("letterhead_note") else int(round(margin * 1.25))
    body += ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
             '<w:pgMar w:top="%d" w:right="1134" w:bottom="%d" w:left="1134" '
             'w:header="567" w:footer="567" w:gutter="0"/>'
             '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>'
             % (top, margin))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            'wordprocessingml/2006/main" xmlns:r="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships">'
            '<w:body>%s</w:body></w:document>' % body)


STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/'
    '2006/main"><w:docDefaults><w:rPrDefault><w:rPr>'
    '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" '
    'w:cs="Calibri"/><w:sz w:val="21"/><w:szCs w:val="21"/>'
    '<w:lang w:val="en-IN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
    '<w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr>'
    '</w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
    '<w:name w:val="Normal"/><w:qFormat/></w:style>'
    '<w:style w:type="table" w:default="1" w:styleId="TableNormal">'
    '<w:name w:val="Normal Table"/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/>'
    '<w:tblCellMar><w:top w:w="0" w:type="dxa"/>'
    '<w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/>'
    '<w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>'
    '</w:styles>')

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
    'content-types"><Default Extension="rels" ContentType="application/'
    'vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/'
    'vnd.openxmlformats-package.core-properties+xml"/>'
    '<Override PartName="/docProps/app.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>')

PKG_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.'
    'openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/><Relationship Id="rId2" Type="http://'
    'schemas.openxmlformats.org/package/2006/relationships/metadata/'
    'core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/extended-properties" Target="docProps/app.xml"/>'
    '</Relationships>')

DOC_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.'
    'openxmlformats.org/officeDocument/2006/relationships/styles" '
    'Target="styles.xml"/></Relationships>')

APP_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/'
    '2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/'
    'officeDocument/2006/docPropsVTypes"><Application>Balance Confirmation '
    'Generator</Application><Company></Company></Properties>')


def core_xml(conf, stamp=None):
    when = stamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    span = period_label(conf.get("basis"),
                        conf.get("as_at") or conf.get("year_end"),
                        conf.get("period_start")) \
        or ("year ended " + (conf.get("year_end_label") or ""))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/'
            'package/2006/metadata/core-properties" xmlns:dc="http://purl.org/'
            'dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>%s</dc:title><dc:subject>%s</dc:subject>'
            '<dc:creator>%s</dc:creator><cp:lastModifiedBy>%s'
            '</cp:lastModifiedBy>'
            '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified>'
            '</cp:coreProperties>'
            % (xml_escape("Balance confirmation — %s — %s"
                          % (conf.get("party_name"), conf.get("category"))),
               xml_escape("%s of %s — %s"
                          % (conf.get("audit_type", "Statutory Audit"),
                             conf.get("client_name"), span)),
               xml_escape(conf.get("firm_name")),
               xml_escape(conf.get("firm_name")), when, when))


def docx_parts(model, conf, stamp=None):
    return {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": PKG_RELS,
        "docProps/core.xml": core_xml(conf, stamp),
        "docProps/app.xml": APP_XML,
        "word/document.xml": document_xml(model),
        "word/_rels/document.xml.rels": DOC_RELS,
        "word/styles.xml": STYLES_XML,
    }


_PART_ORDER = ["[Content_Types].xml", "_rels/.rels", "word/document.xml",
               "word/_rels/document.xml.rels", "word/styles.xml",
               "docProps/core.xml", "docProps/app.xml"]


def docx_bytes(conf, stamp=None):
    """Build one complete .docx in memory and return it as bytes."""
    parts = docx_parts(build_letter_model(conf), conf, stamp)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in _PART_ORDER:
            archive.writestr(name, parts[name])
    return buffer.getvalue()


# ------------------------------------------------------------- file names
_WINDOWS_RESERVED = re.compile(
    r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])$", re.I)


# ---------------------------------------------------------------- the PDF
# The same letter as a PDF: what is e-mailed to the party, and what the client
# prints on its letterhead.  It is drawn from the same model as the Word file,
# so the two always read alike.
_PDF_FONTS = None
_PDF_FONT_FILES = [
    (r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\calibrib.ttf"),
    ("/Library/Fonts/Microsoft/Calibri.ttf",
     "/Library/Fonts/Microsoft/Calibri Bold.ttf"),
    ("/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
     "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"),
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def _pdf_fonts():
    """Calibri where the computer has it, so the PDF matches the Word letter;
    otherwise the nearest face found, and Helvetica if there is none."""
    global _PDF_FONTS
    if _PDF_FONTS:
        return _PDF_FONTS
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for regular, bold in _PDF_FONT_FILES:
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                pdfmetrics.registerFont(TTFont("BCG-Regular", regular))
                pdfmetrics.registerFont(TTFont("BCG-Bold", bold))
                _PDF_FONTS = ("BCG-Regular", "BCG-Bold")
                return _PDF_FONTS
            except Exception:
                continue
    _PDF_FONTS = ("Helvetica", "Helvetica-Bold")
    return _PDF_FONTS


def _pdf_story(model, size, scale):
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    regular, bold_face = _pdf_fonts()
    single, body_lead = size * 1.20, size * 1.32

    def pt(twips):                       # the Word file measures in twentieths
        return twips / 20.0 * scale

    def para(text, bold=False, align=TA_LEFT, after=0, before=0, lead=single,
             keep=False):
        style = ParagraphStyle(
            "p", fontName=bold_face if bold else regular, fontSize=size,
            leading=lead, alignment=align, spaceAfter=pt(after),
            spaceBefore=pt(before), keepWithNext=1 if keep else 0)
        return Paragraph(xml_escape(text), style)

    story = []
    if model.get("letterhead_note"):
        story.append(para(model["letterhead_note"], align=TA_CENTER, after=40))
    story.append(para(model["title"], bold=True, align=TA_CENTER, after=260,
                      keep=True))
    story.append(para(model["date_line"], align=TA_RIGHT,
                      after=0 if model.get("reference_line") else 60))
    if model.get("reference_line"):
        story.append(para(model["reference_line"], align=TA_RIGHT, after=60))
    last = len(model["party_block"]) - 1
    for i, line in enumerate(model["party_block"]):
        story.append(para(line["text"], bold=line["bold"],
                          after=240 if i == last else 0))
    story.append(para(model["salutation"], after=200))
    for i, text in enumerate(model["paras"]):
        final = i == len(model["paras"]) - 1
        story.append(para(text, align=TA_JUSTIFY, lead=body_lead,
                          after=150 if final else 200, keep=final))
    last = len(model["auditor_block"]) - 1
    for i, line in enumerate(model["auditor_block"]):
        story.append(para(line["text"], bold=line["bold"],
                          after=200 if i == last else 0))
    for text in model["closing_paras"]:
        story.append(para(text, align=TA_JUSTIFY, lead=body_lead, after=200))
    last = len(model["signature"]) - 1
    for i, line in enumerate(model["signature"]):
        story.append(para(line["text"], bold=line["bold"],
                          before=360 if line.get("gap") else 0,
                          after=420 if i == last else 20, keep=i < last))
    story.append(para(model["slip"]["sentence"], align=TA_JUSTIFY,
                      lead=body_lead, after=160, keep=True))
    rows = [[para(label), para(":  ______________________")]
            for label in model["slip"]["rows"]]
    grid = Table(rows, colWidths=[130, 200], hAlign="LEFT",
                 rowHeights=[max(single + 2, 17 * scale)] * len(rows))
    grid.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(grid)
    story.append(Spacer(1, 1))
    return story


def pdf_bytes(conf, top_space_cm=0.0):
    """The letter as a one-page A4 PDF.

    top_space_cm leaves the head of the page clear, for printing on the
    client's own letterhead.  The spacing is tightened step by step until the
    letter, slip included, sits on a single page."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate
    model = build_letter_model(conf)
    compact = model.get("compact")
    margin = (1.8 if compact else 2.0) * cm
    top = (margin if model.get("letterhead_note") else margin * 1.25) \
        + max(0.0, float(top_space_cm or 0)) * cm
    payload = b""
    for size, scale in ((10.5, 0.78 if compact else 1.0), (10.5, 0.62),
                        (10.0, 0.5), (9.5, 0.4), (9.0, 0.3), (8.5, 0.22)):
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=top, bottomMargin=margin,
            title="%s - %s" % (model["title"].title(),
                               conf.get("party_name", "")),
            author=conf.get("client_name", ""),
            subject="Balance confirmation %s" % (conf.get("reference") or ""),
            creator="Balance Confirmation Generator")
        document.build(_pdf_story(model, size, scale))
        payload = buffer.getvalue()
        if document.page <= 1:
            break
    return payload


def pdf_page_count(payload):
    """Pages in a PDF this application wrote (used by the tests and the
    one-page check)."""
    return len(re.findall(rb"/Type\s*/Page[^s]", payload or b""))


def looks_like_pdf(path):
    try:
        with open(path, "rb") as handle:
            return handle.read(5) == b"%PDF-"
    except Exception:
        return False


def match_signed_pdfs(paths, documents):
    """Tie a folder of signed PDFs to the parties they belong to.

    documents: [{id, party_name, category, reference, filename}].
    A file is linked when its name carries the letter's reference code, or the
    party's name (and the category, where the same party has two letters).
    Returns ({document id: path}, [paths that matched nothing or too much])."""
    def squash(text):
        return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())

    linked, loose = {}, []
    for path in paths:
        stem = os.path.splitext(os.path.basename(path))[0]
        flat = squash(stem)
        # an underscore is a word character, so "scan_BCG-7F3K2A" would hide
        # the code from a whole-word search
        reference = find_reference(stem.replace("_", " "))
        hits = [d for d in documents
                if reference and (d.get("reference") or "").upper() == reference]
        if not hits:
            hits = [d for d in documents
                    if squash(os.path.splitext(d.get("filename", ""))[0])
                    and squash(os.path.splitext(d.get("filename", ""))[0])
                    in flat]
        if not hits:
            hits = [d for d in documents
                    if len(squash(d.get("party_name"))) >= 4
                    and squash(d.get("party_name")) in flat]
            if len(hits) > 1:
                narrowed = [d for d in hits if squash(d.get("category")) in flat]
                hits = narrowed or hits
        if len(hits) == 1 and hits[0]["id"] not in linked:
            linked[hits[0]["id"]] = path
        else:
            loose.append(path)
    return linked, loose


def sanitize_filename(text):
    value = re.sub(r'[\\/:*?"<>|]', " ", str("" if text is None else text))
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    if len(value) > 110:
        value = value[:110].strip()
    if not value:
        value = "Party"
    if _WINDOWS_RESERVED.match(value):
        value += "_"
    return value


def unique_filename(base, extension, used):
    name = base + extension
    key = name.lower()
    counter = 1
    while key in used:
        counter += 1
        name = "%s (%d)%s" % (base, counter, extension)
        key = name.lower()
    used.add(key)
    return name


# ===========================================================================
# SECTION 4 - WORKBOOK READER
# ===========================================================================

SAMPLE_TEMPLATE_NAME = "Balance confirmation - sample template.xlsx"
SAMPLE_COLUMNS = [
    # heading, width, required?, what goes in it
    ("Name", 30, "Required", "The party's legal name, exactly as it should "
                             "read on the letter."),
    ("Address line 1", 46, "Optional", "Building, street, area and city."),
    ("Pincode", 11, "Optional", "Joined to the address on the letter."),
    ("State", 18, "Optional", "Joined to the address on the letter."),
    ("Country", 12, "Optional", "Joined to the address on the letter."),
    ("Currency", 11, "Optional", "Three-letter code such as INR or USD. "
                                 "Blank means the default currency in "
                                 "Settings."),
    ("Closing balance", 20, "Recommended", "The balance as per the client's "
                                           "books at the as-at date, as a "
                                           "plain number. No commas, symbols "
                                           "or Dr/Cr needed."),
    ("Category", 26, "Recommended", "Exactly one of: Trade Receivable, Trade "
                                    "Payable, Advance from Customers, "
                                    "Advance to Vendors. Pick it from the "
                                    "drop-down."),
    ("Email ID", 34, "Needed to e-mail", "Where the confirmation request is "
                                         "to be sent. One address per row."),
    ("Contact person", 24, "Optional", "Printed as 'Kind attention' on the "
                                       "letter."),
]
SAMPLE_ROWS = [
    ("ABC Private Limited", "Unit 12, 10th Road, Vile Parle (East), Mumbai",
     400057, "Maharashtra", "India", "INR", 7960098.48, "Trade Receivable",
     "accounts@abc-example.com", "Mr. A. Shah"),
    ("XYZ Suppliers LLP", "Plot 4, Industrial Estate, Okhla Phase II, "
     "New Delhi", 110020, "Delhi", "India", "INR", 3515723.34,
     "Trade Payable", "finance@xyz-example.com", "Ms. R. Gupta"),
    ("Customer P Limited", "5th Floor, Baner Road, Pune", 411045,
     "Maharashtra", "India", "INR", 500000, "Advance from Customers",
     "payables@customerp-example.com", ""),
    ("Vendor Q Industries", "Survey No. 21, GIDC, Vapi", 396195, "Gujarat",
     "India", "INR", 275000, "Advance to Vendors",
     "receivables@vendorq-example.com", ""),
]


def write_sample_template(path):
    """Write the ready-to-fill party listing the application reads without
    any mapping: the headings are the ones its own detection looks for."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    olive = PatternFill("solid", fgColor="5F7232")
    pale = PatternFill("solid", fgColor="F3F5EA")
    thin = Side(style="thin", color="C9CFB4")
    edge = Border(left=thin, right=thin, top=thin, bottom=thin)

    book = Workbook()
    sheet = book.active
    sheet.title = "Party balances"
    for index, (heading, width, _need, _help) in enumerate(SAMPLE_COLUMNS, 1):
        cell = sheet.cell(row=1, column=index, value=heading)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = olive
        cell.border = edge
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.row_dimensions[1].height = 24
    for r, values in enumerate(SAMPLE_ROWS, 2):
        for c, value in enumerate(values, 1):
            cell = sheet.cell(row=r, column=c, value=value if value != ""
                              else None)
            cell.border = edge
            cell.font = Font(italic=True, color="6E755B")
    for r in range(2, 502):
        sheet.cell(row=r, column=7).number_format = "#,##0.00"
        sheet.cell(row=r, column=3).number_format = "0"
    sheet.freeze_panes = "A2"

    categories = DataValidation(
        type="list", formula1='"%s"' % ",".join(CATEGORIES),
        allow_blank=True, showErrorMessage=True,
        errorTitle="Category",
        error="Choose one of the four categories from the list.")
    currencies = DataValidation(
        type="list", formula1='"INR,USD,EUR,GBP,AED,SGD,JPY,AUD,CAD,CHF"',
        allow_blank=True, showErrorMessage=False)
    sheet.add_data_validation(categories)
    sheet.add_data_validation(currencies)
    categories.add("H2:H501")
    currencies.add("F2:F501")

    guide = book.create_sheet("How to fill")
    guide.column_dimensions["A"].width = 22
    guide.column_dimensions["B"].width = 20
    guide.column_dimensions["C"].width = 96
    guide["A1"] = "Balance Confirmation Generator - party listing template"
    guide["A1"].font = Font(bold=True, size=14, color="5F7232")
    steps = [
        "1.  Fill the 'Party balances' sheet, one party per row. The four "
        "rows in grey italics are examples: overwrite or delete them.",
        "2.  Keep the headings in row 1 as they are. The application "
        "recognises them, so no column mapping is needed.",
        "3.  Enter the closing balance as a plain number, as it stands in "
        "the client's books at the as-at date.",
        "4.  A party with balances in two categories takes two rows, one "
        "for each category.",
        "5.  Save the file, then drop it on 03 Import data in the "
        "application.",
    ]
    for offset, line in enumerate(steps, 3):
        guide.cell(row=offset, column=1, value=line)
        guide.merge_cells(start_row=offset, start_column=1,
                          end_row=offset, end_column=3)
    top = len(steps) + 5
    for c, heading in enumerate(("Column", "Needed?", "What goes in it"), 1):
        cell = guide.cell(row=top, column=c, value=heading)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = olive
        cell.border = edge
    for offset, (heading, _w, need, text) in enumerate(SAMPLE_COLUMNS, 1):
        row = top + offset
        for c, value in enumerate((heading, need, text), 1):
            cell = guide.cell(row=row, column=c, value=value)
            cell.border = edge
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if offset % 2 == 0:
                cell.fill = pale
        guide.cell(row=row, column=1).font = Font(bold=True)
    note = top + len(SAMPLE_COLUMNS) + 2
    guide.cell(row=note, column=1, value="Which category?").font = \
        Font(bold=True)
    meanings = [
        ("Trade Receivable", "The party owes the client (debtor / customer)."),
        ("Trade Payable", "The client owes the party (creditor / supplier)."),
        ("Advance from Customers", "The client has received an advance from "
                                   "the party."),
        ("Advance to Vendors", "The client has paid an advance to the "
                               "party."),
    ]
    for offset, (name, meaning) in enumerate(meanings, 1):
        guide.cell(row=note + offset, column=1, value=name)
        guide.cell(row=note + offset, column=3, value=meaning)
    book.save(path)
    return path


def read_workbook(path):
    """Return {sheet name: grid of rows}.  Nothing is written to the source."""
    lower = path.lower()
    if lower.endswith(".csv") or lower.endswith(".txt"):
        return {"CSV": _read_csv(path)}
    if lower.endswith(".xls"):
        if not HAS_XLRD:
            raise RuntimeError(
                "Reading .xls needs the xlrd library, which is not installed. "
                "Re-save the file as .xlsx, or install it with:\n\n"
                "    %s -m pip install xlrd" % sys.executable)
        import xlrd
        book = xlrd.open_workbook(path)
        sheets = {}
        for sheet in book.sheets():
            sheets[sheet.name] = [[sheet.cell_value(r, c)
                                   for c in range(sheet.ncols)]
                                  for r in range(sheet.nrows)]
        return sheets
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheets = {}
    try:
        for sheet in workbook.worksheets:
            sheets[sheet.title] = [list(row)
                                   for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()
    return sheets


def _read_csv(path):
    """Read a CSV, coping with the encodings Excel commonly writes."""
    raw = open(path, "rb").read()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    width = max((len(r) for r in rows), default=0)
    return [r + [None] * (width - len(r)) for r in rows]


def trim_grid(grid):
    """Drop trailing blank rows so the row count matches what the user sees."""
    trimmed = list(grid or [])
    while trimmed and not any(clean(c) for c in (trimmed[-1] or [])):
        trimmed.pop()
    return trimmed


# ===========================================================================
# SECTION 5 - E-MAIL COMPOSITION
# ===========================================================================

LEGACY_SUBJECT = "Balance confirmation request as at {date} — {client}"
# the reference rides in the subject, so every reply ("Re: ...") carries
# it back even when the party writes nothing else
DEFAULT_SUBJECT = ("Balance confirmation request as at {date} — {client} "
                   "— Ref {reference}")
DEFAULT_BODY = "\n".join([
    "Dear Sir/Madam,",
    "",
    "We are the auditors of {client} and are carrying out {audittype_article} "
    "of its financial statements {period}.",
    "",
    "Please find attached a balance confirmation request issued by {client} in "
    "respect of the {category} balance appearing in its books as at {date}, "
    "being {amount}.",
    "",
    "Kindly sign the attached letter and e-mail it directly to us at:",
    "{auditors}",
    "",
    "Should the amount not agree with your records, please let us know the "
    "balance as per your books together with particulars of the difference.",
    "",
    "We thank you in advance for your co-operation.",
    "",
    "Yours faithfully,",
    "For {firm}",
    "{designation}",
])

PLACEHOLDERS = ["{party}", "{client}", "{audittype}", "{audittype_article}",
                "{period}", "{category}", "{date}", "{amount}", "{words}",
                "{currency}", "{reference}", "{auditors}", "{firm}",
                "{designation}"]


def fill_template(template, conf):
    label = amount_label(conf.get("amount"), conf.get("currency"))
    team = "\n".join(
        "  " + ((a.get("name") + " — ") if a.get("name") else "")
        + a.get("email", "")
        for a in (conf.get("auditors") or []))
    span = period_phrase(conf.get("basis"),
                         conf.get("as_at") or conf.get("year_end"),
                         conf.get("period_start"))
    if not span and conf.get("year_end_label"):
        span = "for the year ended " + conf["year_end_label"]
    replacements = {
        "{party}": conf.get("party_name", ""),
        "{client}": conf.get("client_name", ""),
        "{audittype}": audit_phrase(conf.get("audit_type"),
                                    conf.get("audit_type_other")),
        "{audittype_article}": engagement_phrase(conf.get("audit_type"),
                                                 conf.get("audit_type_other")),
        "{words}": amount_in_words(conf.get("amount"), conf.get("currency")),
        "{period}": span,
        "{category}": conf.get("category", ""),
        "{date}": conf.get("year_end_label", ""),
        "{amount}": "not available" if label is None else label,
        "{currency}": conf.get("currency", ""),
        "{reference}": conf.get("reference", ""),
        "{firm}": conf.get("firm_name", ""),
        "{designation}": conf.get("firm_designation", ""),
        "{auditors}": team,
    }
    text = str(template or "")
    for token, value in replacements.items():
        text = text.replace(token, value)
    return text


def build_email_message(conf, filename, attachment, options):
    """Compose a complete RFC-5322 message with the letter attached - a PDF
    or a Word file, told apart by the file name."""
    message = EmailMessage()
    sender_name = options.get("sender_name") or ""
    sender = options.get("sender", "")
    message["From"] = formataddr((sender_name, sender)) if sender_name else sender
    message["To"] = conf.get("party_email", "")
    team = [a["email"] for a in (conf.get("auditors") or [])
            if valid_email(a.get("email"))]
    if options.get("cc_team", True) and team:
        message["Cc"] = ", ".join(team)
    if options.get("reply_to_team", True) and team:
        message["Reply-To"] = ", ".join(team)
    message["Subject"] = fill_template(
        options.get("subject") or DEFAULT_SUBJECT, conf)
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    # marks the message as our own request: a copy of it reaches the mailbox
    # the bridge reads, and must never be mistaken for the party's reply
    message["X-BCG-Request"] = str(conf.get("reference") or "request")
    message.set_content(fill_template(options.get("body") or DEFAULT_BODY, conf))
    is_pdf = str(filename).lower().endswith(".pdf")
    message.add_attachment(
        attachment, maintype="application",
        subtype="pdf" if is_pdf else
        "vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename)
    return message


SMTP_PRESETS = {
    "Gmail / Google Workspace": ("smtp.gmail.com", 587, "starttls"),
    "Outlook / Microsoft 365":  ("smtp.office365.com", 587, "starttls"),
    "Zoho Mail (India)":        ("smtp.zoho.in", 587, "starttls"),
    "Zoho Mail (global)":       ("smtp.zoho.com", 587, "starttls"),
    "Yahoo Mail":               ("smtp.mail.yahoo.com", 587, "starttls"),
    "Other / in-house server":  ("", 587, "starttls"),
}


def smtp_connect(host, port, security, username, password, timeout=45):
    """Open an authenticated SMTP session.  Raises on failure."""
    context = ssl.create_default_context()
    if security == "ssl":
        server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
    else:
        server = smtplib.SMTP(host, port, timeout=timeout)
        server.ehlo()
        if security == "starttls":
            server.starttls(context=context)
            server.ehlo()
    if username:
        server.login(username, password)
    return server


def friendly_smtp_error(exc):
    """Turn an SMTP exception into something an accountant can act on."""
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return ("The mail server rejected the sign-in. For Gmail, Outlook, "
                "Yahoo and Zoho you must use an app password, not your normal "
                "password, and two-factor authentication must be on.")
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "The server refused the recipient address."
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return ("The server refused the From address. It usually has to match "
                "the account you signed in with.")
    if isinstance(exc, smtplib.SMTPConnectError):
        return "Could not connect to the mail server. Check the host and port."
    if isinstance(exc, (TimeoutError, OSError)) and not isinstance(
            exc, smtplib.SMTPException):
        return ("Could not reach the mail server. Check your internet "
                "connection, the host and port, and any firewall.")
    text = str(exc).strip()
    return text[:300] if text else exc.__class__.__name__
