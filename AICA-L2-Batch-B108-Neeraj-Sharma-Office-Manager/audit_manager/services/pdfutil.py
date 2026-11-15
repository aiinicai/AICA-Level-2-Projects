"""Shared PDF pieces (letterhead block, fonts, money) built on reportlab."""
import io
import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

from . import letterhead

NAVY = colors.HexColor("#1e3a5f")
TEAL = colors.HexColor("#0d9488")
GREY = colors.HexColor("#475569")
LIGHT = colors.HexColor("#eff6ff")

_CANDIDATES = [
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]
_font_cache: dict = {}


def fonts() -> tuple[str, str, bool]:
    """(regular, bold, supports_rupee_sign). Uses a system TrueType font if one is found, so names in
    other scripts and the rupee sign print; otherwise falls back to Helvetica and 'Rs.'."""
    if _font_cache:
        return _font_cache["v"]
    result = ("Helvetica", "Helvetica-Bold", False)
    for regular, bold in _CANDIDATES:
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                face = TTFont("AMRegular", regular)
                pdfmetrics.registerFont(face)
                pdfmetrics.registerFont(TTFont("AMBold", bold))
                result = ("AMRegular", "AMBold", 0x20B9 in face.face.charToGlyph)
                break
            except Exception:
                continue
    _font_cache["v"] = result
    return result


def money(value) -> str:
    """Indian grouping, with the rupee sign only when the font can print it."""
    number = float(value or 0)
    neg = number < 0
    whole, _, frac = f"{abs(number):.2f}".partition(".")
    if len(whole) > 3:
        head, tail, parts = whole[:-3], whole[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    prefix = "₹" if fonts()[2] else "Rs. "
    return ("-" if neg else "") + prefix + whole + "." + frac


def styles() -> dict:
    regular, bold, _ = fonts()
    return {
        "firm": ParagraphStyle("firm", fontName=bold, fontSize=15, textColor=NAVY, leading=18),
        "small": ParagraphStyle("small", fontName=regular, fontSize=8.5, textColor=GREY, leading=11),
        "sig": ParagraphStyle("sig", fontName=regular, fontSize=8.5, textColor=GREY, leading=11, alignment=2),
        "sigb": ParagraphStyle("sigb", fontName=bold, fontSize=9, textColor=NAVY, leading=12, alignment=2),
        "title": ParagraphStyle("title", fontName=bold, fontSize=13, textColor=TEAL, leading=16),
        "body": ParagraphStyle("body", fontName=regular, fontSize=8, leading=10),
        "bodyb": ParagraphStyle("bodyb", fontName=bold, fontSize=8, leading=10),
        "th": ParagraphStyle("th", fontName=bold, fontSize=7.5, textColor=NAVY, leading=9),
        "right": ParagraphStyle("right", fontName=regular, fontSize=8, leading=10, alignment=2),
    }


def P(text, style) -> Paragraph:
    return Paragraph(escape(str(text if text is not None else "")).replace("\n", "<br/>"), style)


def letterhead_block(profile: dict, width: float, title: str | None = None, right_text: str | None = None,
                     subtitle: str | None = None) -> list:
    """Logo | firm details | signatory, a rule, then the document title and period."""
    st = styles()
    text = [P(profile["name"], st["firm"])]
    for line in (profile["tagline"], profile["address"], letterhead.contact_line(profile), letterhead.id_line(profile)):
        if line:
            text.append(P(line, st["small"]))

    cells, widths = [], []
    logo = None if profile.get("hide_logo") else letterhead.logo_bytes()
    if logo:
        reader = ImageReader(io.BytesIO(logo))
        iw, ih = reader.getSize()
        h = min(18 * mm, iw and ih and 18 * mm)
        w = h * iw / ih
        if w > 32 * mm:
            w, h = 32 * mm, 32 * mm * ih / iw
        cells.append(Image(io.BytesIO(logo), width=w, height=h))
        widths.append(36 * mm)
    sig = letterhead.signatory_line(profile)
    right = [P(sig, st["sigb"]), P(letterhead.profession()["title"], st["sig"])] if sig else [""]
    sig_w = 55 * mm if sig else 0
    cells.append(text)
    widths.append(width - sum(widths) - sig_w)
    if sig:
        cells.append(right)
        widths.append(sig_w)

    head = Table([cells], colWidths=widths)
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                              ("LINEBELOW", (0, 0), (-1, 0), 1.2, NAVY)]))
    out = [head, Spacer(1, 6)]
    if title:
        row = [[[P(title, st["title"])] + ([P(subtitle, st["small"])] if subtitle else []),
                P(right_text or "", st["sig"])]]
        t = Table(row, colWidths=[width * 0.7, width * 0.3])
        t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        out += [t, Spacer(1, 6)]
    return out
