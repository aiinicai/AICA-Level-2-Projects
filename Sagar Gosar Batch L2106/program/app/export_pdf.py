"""PDF report (ReportLab)."""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import report_model as rm
from .config import APP_NAME
from .preview import crop_for_report

_BASE = ParagraphStyle("b", fontName="Helvetica", fontSize=8.5, leading=11.2, alignment=TA_LEFT)
_SM = ParagraphStyle("s", parent=_BASE, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#64748B"))
_H1 = ParagraphStyle("h1", parent=_BASE, fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#1F2A5A"))
_H2 = ParagraphStyle("h2", parent=_BASE, fontName="Helvetica-Bold", fontSize=13, leading=16, spaceBefore=8, spaceAfter=6, textColor=colors.HexColor("#1F2A5A"))
_H3 = ParagraphStyle("h3", parent=_BASE, fontName="Helvetica-Bold", fontSize=9.5, leading=12, spaceBefore=8)

MAX_RUN = 1000          # characters per table row: a single flowable taller than the frame cannot be laid out
MAX_TOTAL = 1500


def _markup(runs):
    out = []
    for text, style in runs:
        if not text:
            continue
        col, fill, strike, under, ital = rm.STYLE_DEF.get(style, rm.STYLE_DEF[rm.PLAIN])
        t = escape(text)
        if strike:
            t = f"<strike>{t}</strike>"
        if under:
            t = f"<u>{t}</u>"
        if ital:
            t = f"<i>{t}</i>"
        if fill:
            t = f'<font backColor="#{fill}">{t}</font>'
        if col:
            t = f'<font color="#{col}">{t}</font>'
        out.append(t)
    return "".join(out)


def _clip(t, n=MAX_TOTAL):
    return t if len(t) <= n else t[:n].rstrip() + " …"


def _chunk_runs(runs, limit=MAX_RUN):
    """Split runs into chunks of at most `limit` characters (cut at spaces) so each chunk fits on a page."""
    chunks, cur, n = [], [], 0
    for text, style in runs:
        while text:
            room = limit - n
            if len(text) <= room:
                cur.append((text, style)); n += len(text); text = ""
            else:
                cut = text.rfind(" ", 0, room)
                cut = cut if cut > 0 else room
                cur.append((text[:cut], style)); chunks.append(cur); cur, n = [], 0; text = text[cut:].lstrip()
        if n >= limit:
            chunks.append(cur); cur, n = [], 0
    if cur:
        chunks.append(cur)
    return chunks or [[]]


def _tbl(data, widths, header=True, extra=None):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2A5A")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    t.setStyle(TableStyle(st + (extra or [])))
    return t


def export_pdf(result, path, include_info=True, include_ocr=False, include_scans=True, include_redline=False, progress=None, **_):
    prog = progress or (lambda f, m: None)
    PW, PH = landscape(A4)
    doc = SimpleDocTemplate(path, pagesize=(PW, PH), leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title="Agreement Comparison Report", author=APP_NAME)
    W = PW - 28 * mm
    hdr = ParagraphStyle("hh", parent=_BASE, fontName="Helvetica-Bold", textColor=colors.white)
    S = []
    S.append(Paragraph("Agreement Comparison Report", _H1))
    S.append(Paragraph(f"Generated {escape(result.created)} by {escape(APP_NAME)}", _SM)); S.append(Spacer(1, 6))
    meta = []
    for role, lab, (name, size, mod, sha, extra) in rm.meta_rows(result):
        meta.append([Paragraph(f"<b>{escape(role)}</b>", _BASE), Paragraph(escape(name), _BASE),
                     Paragraph(f"{escape(size)} · modified {escape(mod)} · {escape(extra)}<br/>SHA-256 {sha}", _SM)])
    S.append(_tbl(meta, [32 * mm, 75 * mm, W - 107 * mm], header=False, extra=[("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2E8F0"))]))
    S.append(Paragraph("Summary", _H2))
    for ln in rm.summary_lines(result):
        S.append(Paragraph("• " + escape(ln), _BASE))
    by = result.stats["by_severity"]
    cells = [[Paragraph(f'<font color="#{rm.SEV_TEXT[s]}"><b>{s}: {by[s]}</b></font>', ParagraphStyle("c", parent=_BASE, fontSize=11, leading=14)) for s in ("Critical", "Major", "Minor", "Info")]]
    S.append(Spacer(1, 6))
    S.append(_tbl(cells, [W / 4] * 4, header=False, extra=[("BACKGROUND", (i, 0), (i, 0), colors.HexColor("#" + rm.SEV_FILL[s])) for i, s in enumerate(("Critical", "Major", "Minor", "Info"))]))
    if result.observations:
        S.append(Paragraph("Observations", _H2))
        for sev, tx in result.observations:
            S.append(Paragraph(f'<font color="#{rm.SEV_TEXT[sev]}"><b>[{sev}]</b></font> {escape(tx)}', _BASE))
    kl, kr = rm.keyfigure_rows(result)
    if kl:
        S.append(Paragraph("Key figures reconciliation", _H2))
        for ln in kl:
            S.append(Paragraph("• " + escape(ln), _BASE))
        if kr:
            S.append(Spacer(1, 4))
            kd = [[Paragraph(x, hdr) for x in ("Figure", "Draft", "Executed copy", "Clause", "Status")]]
            for r_ in kr:
                kd.append([Paragraph(escape(str(c)), _BASE) for c in r_])
            S.append(_tbl(kd, [24 * mm, 48 * mm, 48 * mm, 30 * mm, W - 150 * mm]))
    oq = rm.ocr_quality(result)
    if oq:
        S.append(Paragraph("Scan reading quality", _H2))
        S.append(Paragraph("; ".join(f"p.{p_} {c_:.0f}% ({n_})" for p_, c_, w_, n_ in oq), _BASE))
    items = [i for i in result.items if (include_ocr or not i.ocr_only) and (include_info or i.severity != "Info" or i.ocr_only)]
    prog(0.1, "Writing the register…")
    S.append(PageBreak()); S.append(Paragraph("Register of differences", _H2))
    data = [[Paragraph(x, hdr) for x in ("#", "Clause", "Severity", "Category", "Nature of difference", "Page")]]
    extra = []
    for r_, it in enumerate(items, start=1):
        data.append([Paragraph(str(it.id), _BASE), Paragraph(escape(rm.clause_label(it)), _BASE),
                     Paragraph(f'<font color="#{rm.SEV_TEXT[it.severity]}"><b>{it.severity}</b></font>', _BASE),
                     Paragraph(escape(", ".join(it.categories) + (" (OCR)" if it.ocr_only else "")), _BASE),
                     Paragraph(escape(_clip(it.summary, 600)), _BASE), Paragraph(escape(",".join(map(str, it.pages_b)) or "—"), _BASE)])
        extra.append(("BACKGROUND", (2, r_), (2, r_), colors.HexColor("#" + rm.SEV_FILL[it.severity])))
    S.append(_tbl(data, [10 * mm, 18 * mm, 20 * mm, 38 * mm, W - 100 * mm, 14 * mm], extra=extra))
    S.append(PageBreak()); S.append(Paragraph("Detailed comparison", _H2))
    leg = "Legend: " + "   ".join(_markup([(lbl, st)]) for lbl, st in rm.LEGEND)
    S.append(Paragraph(leg, _SM))
    half = (W - 4) / 2
    for k, it in enumerate(items):
        if k % 5 == 0:
            prog(0.15 + 0.8 * k / max(1, len(items)), f"Writing difference {k + 1} of {len(items)}…")
        left, right = rm.runs_for_item(it, 40)
        lc, rc = _chunk_runs(left), _chunk_runs(right)
        rows = [[Paragraph("<b>Draft / base</b>", _BASE), Paragraph("<b>Executed copy</b>", _BASE)]]
        for i in range(max(len(lc), len(rc))):
            rows.append([Paragraph(_markup(_clip_runs(lc[i])) if i < len(lc) else "", _BASE), Paragraph(_markup(_clip_runs(rc[i])) if i < len(rc) else "", _BASE)])
        head = Paragraph(f'<font color="#{rm.SEV_TEXT[it.severity]}">#{it.id} &nbsp;Clause {escape(rm.clause_label(it))} &nbsp;·&nbsp; {it.severity} &nbsp;·&nbsp; {escape(", ".join(it.categories))}</font>', _H3)
        block = [head, Paragraph(escape(_clip(it.summary, 600)), _BASE), Spacer(1, 3), _tbl(rows, [half, half], extra=[("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.black)])]
        if include_scans and it.regions_b and result.doc_b.kind in ("pdf", "image"):
            try:
                im = crop_for_report(result.doc_b, it.regions_b[0][0], it.regions_b, dpi=120, max_w=800)
                if im is not None:
                    buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
                    w = min(W * 0.55, 150 * mm); h = w * im.height / im.width
                    maxh = PH - 60 * mm
                    if h > maxh:
                        w, h = w * maxh / h, maxh
                    block += [Spacer(1, 3), Image(buf, width=w, height=h), Paragraph(f"Scan extract – page {it.regions_b[0][0]}", _SM)]
            except Exception:
                pass
        S.append(Spacer(1, 4)); S.append(KeepTogether(block[:4]) if len(rows) <= 2 else block[0]);
        if len(rows) > 2:
            S += block[1:4]
        S += block[4:]
    if include_redline:
        S.append(PageBreak()); S.append(Paragraph("Full redline", _H2))
        for row in result.rows:
            lab = row.label_b or row.label_a
            runs = ([(lab + " ", rm.PLAIN)] if lab else []) + [(tx + " ", st) for tx, st in rm.redline_runs(row)]
            for chunk in _chunk_runs(runs, 1800):
                S.append(Paragraph(_markup(chunk), _BASE))
            S.append(Spacer(1, 4))
    S.append(Spacer(1, 10)); S.append(Paragraph(escape(rm.DISCLAIMER), _SM))

    def deco(c, d):
        c.saveState(); c.setFont("Helvetica", 7); c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(14 * mm, 7 * mm, f"{APP_NAME} – comparison report"); c.drawRightString(PW - 14 * mm, 7 * mm, f"Page {d.page}"); c.restoreState()
    prog(0.97, "Saving…")
    doc.build(S, onFirstPage=deco, onLaterPages=deco)
    prog(1.0, "Done")
    return path


def _clip_runs(runs):
    out, n = [], 0
    for t, s in runs:
        if n >= MAX_TOTAL:
            break
        out.append((t[:MAX_TOTAL - n], s)); n += len(t)
    return out
