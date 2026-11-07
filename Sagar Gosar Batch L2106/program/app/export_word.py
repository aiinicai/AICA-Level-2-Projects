"""Word (.docx) report."""
import io

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from . import report_model as rm
from .config import APP_NAME
from .extract_pdf import Cancelled
from .preview import crop_for_report


def _shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_); tcPr.append(shd)


def _runs(par, runs, size=9):
    for text, style in runs:
        if not text:
            continue
        col, fill, strike, under, ital = rm.STYLE_DEF.get(style, rm.STYLE_DEF[rm.PLAIN])
        r = par.add_run(text); r.font.size = Pt(size)
        if col:
            r.font.color.rgb = RGBColor.from_string(col)
        if strike:
            r.font.strike = True
        if under:
            r.font.underline = True
        if ital:
            r.italic = True
        if fill:
            rPr = r._r.get_or_add_rPr(); shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill); rPr.append(shd)


def _cell(cell, text="", bold=False, size=9, color=None):
    cell.text = ""
    p = cell.paragraphs[0]; r = p.add_run(text); r.font.size = Pt(size); r.bold = bold
    if color:
        r.font.color.rgb = RGBColor.from_string(color)
    return p


def _widths(table, widths):
    table.autofit = False
    for row in table.rows:
        for c, w in zip(row.cells, widths):
            c.width = Cm(w)


def export_word(result, path, progress=None, include_info=True, include_ocr=False, include_scans=True, include_redline=False, **_):
    prog = progress or (lambda f, m: None)
    d = Document()
    s = d.sections[0]; s.orientation = WD_ORIENT.LANDSCAPE; s.page_width, s.page_height = s.page_height, s.page_width
    for m in ("left_margin", "right_margin"):
        setattr(s, m, Cm(1.6))
    s.top_margin = s.bottom_margin = Cm(1.5)
    d.styles["Normal"].font.name = "Calibri"; d.styles["Normal"].font.size = Pt(10)
    t = d.add_paragraph(); r = t.add_run("Agreement Comparison Report"); r.bold = True; r.font.size = Pt(20); r.font.color.rgb = RGBColor(0x1F, 0x2A, 0x5A)
    sub = d.add_paragraph(f"Generated {result.created} by {APP_NAME}"); sub.runs[0].font.size = Pt(9); sub.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    tb = d.add_table(rows=0, cols=3); tb.style = "Table Grid"
    for role, lab, (name, size, mod, sha, extra) in rm.meta_rows(result):
        c = tb.add_row().cells
        _cell(c[0], role, True); _cell(c[1], name, False); _cell(c[2], f"{size} · modified {mod} · {extra}\nSHA-256 {sha}", size=8)
        _shade(c[0], "E2E8F0")
    _widths(tb, [3.5, 8.0, 14.5])
    d.add_paragraph()
    h = d.add_paragraph(); h.add_run("Summary").bold = True; h.runs[0].font.size = Pt(13)
    for ln in rm.summary_lines(result):
        d.add_paragraph(ln, style="List Bullet")
    by = result.stats["by_severity"]
    st = d.add_table(rows=1, cols=4); st.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, sv in enumerate(("Critical", "Major", "Minor", "Info")):
        c = st.rows[0].cells[i]; _cell(c, f"{sv}: {by[sv]}", True, 11, rm.SEV_TEXT[sv]); _shade(c, rm.SEV_FILL[sv])
    if result.observations:
        d.add_paragraph()
        h = d.add_paragraph(); h.add_run("Observations").bold = True; h.runs[0].font.size = Pt(13)
        for sev, tx in result.observations:
            p = d.add_paragraph(style="List Bullet"); rr = p.add_run(f"[{sev}] "); rr.bold = True; rr.font.color.rgb = RGBColor.from_string(rm.SEV_TEXT[sev]); p.add_run(tx)
    kl, kr = rm.keyfigure_rows(result)
    if kl:
        d.add_paragraph()
        h = d.add_paragraph(); h.add_run("Key figures reconciliation").bold = True; h.runs[0].font.size = Pt(13)
        for ln in kl:
            d.add_paragraph(ln, style="List Bullet")
        if kr:
            kt = d.add_table(rows=1, cols=5); kt.style = "Table Grid"
            for i, x in enumerate(("Figure", "Draft", "Executed copy", "Clause", "Status")):
                _cell(kt.rows[0].cells[i], x, True); _shade(kt.rows[0].cells[i], "1F2A5A")
                kt.rows[0].cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
            for r_ in kr:
                c = kt.add_row().cells
                for i, x in enumerate(r_):
                    _cell(c[i], str(x), False)
            _widths(kt, [3.0, 5.0, 5.0, 3.5, 9.5])
    oq = rm.ocr_quality(result)
    if oq:
        d.add_paragraph()
        h = d.add_paragraph(); h.add_run("Scan reading quality").bold = True; h.runs[0].font.size = Pt(13)
        d.add_paragraph("; ".join(f"p.{p_} {c_:.0f}% ({n_})" for p_, c_, w_, n_ in oq))
    items = [i for i in result.items if (include_ocr or not i.ocr_only) and (include_info or i.severity != "Info" or i.ocr_only)]
    prog(0.1, "Writing the register…")
    d.add_page_break()
    h = d.add_paragraph(); h.add_run("Register of differences").bold = True; h.runs[0].font.size = Pt(13)
    tb = d.add_table(rows=1, cols=6); tb.style = "Table Grid"
    for c, tx in zip(tb.rows[0].cells, ("#", "Clause", "Severity", "Category", "Nature of difference", "Page")):
        _cell(c, tx, True, 9, "FFFFFF"); _shade(c, "1F2A5A")
    for it in items:
        c = tb.add_row().cells
        _cell(c[0], str(it.id)); _cell(c[1], rm.clause_label(it)); _cell(c[2], it.severity, True, 9, rm.SEV_TEXT[it.severity]); _shade(c[2], rm.SEV_FILL[it.severity])
        _cell(c[3], ", ".join(it.categories) + (" (OCR)" if it.ocr_only else "")); _cell(c[4], it.summary); _cell(c[5], ",".join(map(str, it.pages_b)) or "—")
    _widths(tb, [1.2, 2.0, 2.2, 4.0, 14.0, 1.6])
    d.add_page_break()
    h = d.add_paragraph(); h.add_run("Detailed comparison").bold = True; h.runs[0].font.size = Pt(13)
    lg = d.add_paragraph("Legend: "); lg.runs[0].font.size = Pt(8)
    for label, style in rm.LEGEND:
        _runs(lg, [(label + "   ", style)], 8)
    for k, it in enumerate(items):
        if k % 5 == 0:
            if progress:
                prog(0.15 + 0.8 * k / max(1, len(items)), f"Writing difference {k + 1} of {len(items)}…")
        hp = d.add_paragraph(); hp.paragraph_format.space_before = Pt(10); hp.paragraph_format.keep_with_next = True
        rr = hp.add_run(f"#{it.id}  Clause {rm.clause_label(it)}  ·  {it.severity}  ·  {', '.join(it.categories)}"); rr.bold = True; rr.font.size = Pt(10.5)
        rr.font.color.rgb = RGBColor.from_string(rm.SEV_TEXT[it.severity])
        sp = d.add_paragraph(it.summary); sp.runs[0].font.size = Pt(9.5); sp.paragraph_format.keep_with_next = True
        left, right = rm.runs_for_item(it, 40)
        tb = d.add_table(rows=2, cols=2); tb.style = "Table Grid"
        _cell(tb.rows[0].cells[0], "Draft / base", True, 8); _cell(tb.rows[0].cells[1], "Executed copy", True, 8)
        for c in tb.rows[0].cells:
            _shade(c, "E2E8F0")
        _runs(tb.rows[1].cells[0].paragraphs[0], left); _runs(tb.rows[1].cells[1].paragraphs[0], right)
        _widths(tb, [13.0, 13.0])
        if include_scans and it.regions_b and result.doc_b.kind in ("pdf", "image"):
            try:
                im = crop_for_report(result.doc_b, it.regions_b[0][0], it.regions_b)
                if im is not None:
                    buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
                    p = d.add_paragraph(); p.add_run().add_picture(buf, width=Cm(13.5))
                    cp = d.add_paragraph(f"Scan extract – page {it.regions_b[0][0]}"); cp.runs[0].font.size = Pt(7.5); cp.runs[0].italic = True
            except Exception:
                pass
    if include_redline:
        d.add_page_break()
        h = d.add_paragraph(); h.add_run("Full redline").bold = True; h.runs[0].font.size = Pt(13)
        for row in result.rows:
            p = d.add_paragraph(); lab = row.label_b or row.label_a
            runs = ([(lab + " ", rm.PLAIN)] if lab else [])
            for tx, stl in rm.redline_runs(row):
                runs.append((tx + " ", stl))
            _runs(p, runs, 9.5); p.paragraph_format.space_after = Pt(4)
    d.add_paragraph()
    dp = d.add_paragraph(rm.DISCLAIMER); dp.runs[0].font.size = Pt(8); dp.runs[0].italic = True
    prog(0.97, "Saving…")
    d.save(path)
    prog(1.0, "Done")
    return path
