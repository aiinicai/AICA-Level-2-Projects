"""
Single-PDF export of the whole CMA workbook, with an automatic page check.

Converter, in order of preference:
  1. Microsoft Excel (through pywin32 / COM) - exact Excel printing;
  2. LibreOffice (soffice) if installed;
  3. otherwise the user is told to use the PDF macro saved next to the workbook.

After export every page is checked: A4 size, which sheet it belongs to (from
the footer), and how full the last page of each sheet is.  A sheet that ends
on a page less than 30% full is squeezed onto one page fewer and the PDF is
made again (at most twice).
"""
import os
import shutil
import subprocess
import sys
import tempfile

MIN_FILL = 0.30


class NoConverter(Exception):
    pass


# ----------------------------------------------------------------------
def _excel_export(xlsx, pdf):
    import win32com.client  # noqa - Windows only
    import pythoncom
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    try:
        try:
            wb = xl.Workbooks.Open(os.path.abspath(xlsx))
        except Exception:                           # let Excel repair the file rather than give up
            wb = xl.Workbooks.Open(os.path.abspath(xlsx), CorruptLoad=1)
        xl.CalculateFull()
        wb.Save()                                   # cache the calculated values in the .xlsx
        wb.ExportAsFixedFormat(0, os.path.abspath(pdf), 0, True, False)
        wb.Close(False)
    finally:
        xl.Quit()
    return pdf


def _find_soffice():
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if os.path.exists(p):
            return p
    return None


def _lo_export(xlsx, pdf):
    soffice = _find_soffice()
    if not soffice:
        raise NoConverter("LibreOffice not found")
    out = tempfile.mkdtemp()
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", out, os.path.abspath(xlsx)],
                   capture_output=True, timeout=300)
    produced = os.path.join(out, os.path.splitext(os.path.basename(xlsx))[0] + ".pdf")
    if not os.path.exists(produced):
        raise NoConverter("LibreOffice could not convert the workbook")
    shutil.move(produced, pdf)
    return pdf


def convert(xlsx, pdf):
    errors = []
    if sys.platform.startswith("win"):
        try:
            return _excel_export(xlsx, pdf), "Microsoft Excel"
        except Exception as e:      # Excel missing or COM failure
            errors.append("Excel: %s" % e)
    try:
        return _lo_export(xlsx, pdf), "LibreOffice"
    except Exception as e:
        errors.append("LibreOffice: %s" % e)
    raise NoConverter("; ".join(errors))


# ----------------------------------------------------------------------
def check_pdf(pdf, sheet_names):
    """Return {pages, a4, per_sheet: {name: [fill,...]}, problems: [...]}."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    per, a4_ok, problems = {}, True, []
    names = sorted(sheet_names, key=len, reverse=True)
    for i in range(len(doc)):
        page = doc[i]
        w, h = page.get_size()
        if abs(min(w, h) - 595) > 3 or abs(max(w, h) - 842) > 3:
            a4_ok = False
            problems.append("Page %d is not A4." % (i + 1))
        tp = page.get_textpage()
        text = tp.get_text_range()
        low = h
        for k in range(tp.count_rects()):
            _, b, _, _ = tp.get_rect(k)
            if b > 40:
                low = min(low, b)
        fill = (h - low) / h if text.strip() else 0.0
        if fill == 0:
            problems.append("Page %d is blank." % (i + 1))
        footer = [ln for ln in text.splitlines() if "Page " in ln and " of " in ln]
        sheet = "?"
        for ln in footer + [text]:
            hit = next((n for n in names if n in ln), None)
            if hit:
                sheet = hit
                break
        per.setdefault(sheet, []).append(fill)
    for name, fills in per.items():
        if len(fills) > 1 and fills[-1] < MIN_FILL:
            problems.append("%s: last page only %d%% filled." % (name, fills[-1] * 100))
    return {"pages": len(doc), "a4": a4_ok, "per_sheet": per, "problems": problems}


def export_pdf(xlsx, pdf=None, project=None, settings=None, log=print):
    """Export, check, and tighten sheets that spill (re-export at most twice)."""
    import openpyxl
    pdf = pdf or os.path.splitext(xlsx)[0] + ".pdf"
    _, engine = convert(xlsx, pdf)
    wb = openpyxl.load_workbook(xlsx)
    names = [ws.title for ws in wb.worksheets if ws.sheet_state == "visible"]
    rep = check_pdf(pdf, names)
    for attempt in range(2):
        spill = {n: len(f) - 1 for n, f in rep["per_sheet"].items() if len(f) > 1 and f[-1] < MIN_FILL}
        if not spill:
            break
        log("Tightening: " + ", ".join(spill))
        wb = openpyxl.load_workbook(xlsx)
        from openpyxl.worksheet.properties import PageSetupProperties
        for n, pages in spill.items():
            if n in wb.sheetnames:
                ws = wb[n]
                ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
                ws.page_setup.fitToWidth = 1
                ws.page_setup.fitToHeight = max(pages, 1)
        from reports.styles import clean_empty
        clean_empty(wb)
        wb.save(xlsx)
        convert(xlsx, pdf)
        rep = check_pdf(pdf, names)
    rep["engine"] = engine
    return pdf, rep
