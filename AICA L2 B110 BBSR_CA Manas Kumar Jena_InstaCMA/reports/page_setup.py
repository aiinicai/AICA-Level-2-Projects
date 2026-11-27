"""
Print layout for the single PDF:
  * A4 on every page; portrait, except Projection Basis (landscape);
  * narrow margins (0.25" sides, 0.5" top / bottom);
  * all columns on one page width; print area = used range, hidden columns skipped;
  * no sheet ends on a nearly empty page: short tail sections are joined to the
    previous page and the sheet is scaled to fit;
  * footer: client | sheet | Page x of y.
The PDF exporter checks the finished PDF and tightens any sheet that still
spills (fit_overrides).
"""
import copy
import math

from openpyxl.utils import get_column_letter as CL
from openpyxl.worksheet.dimensions import ColumnDimension
from openpyxl.worksheet.pagebreak import Break, RowBreak
from openpyxl.worksheet.properties import PageSetupProperties

A4_W, A4_H = 595.0, 842.0
LANDSCAPE = {"Projection Basis"}
MIN_FILL = 0.30
ONE_PAGE_UPTO = 1.6


def ungroup_columns(ws):
    """Split grouped column dimensions (min..max) into one entry per column."""
    for key, dim in list(ws.column_dimensions.items()):
        if dim.min and dim.max and dim.max > dim.min:
            for idx in range(dim.min, dim.max + 1):
                letter = CL(idx)
                nd = ColumnDimension(ws, index=letter, width=dim.width, hidden=dim.hidden,
                                     outlineLevel=dim.outlineLevel, collapsed=dim.collapsed)
                nd._style = copy.copy(dim._style)
                ws.column_dimensions[letter] = nd
            if key != CL(dim.min):
                del ws.column_dimensions[key]


def _used(ws):
    max_r = max_c = 1
    for row in ws.iter_rows():
        for c in row:
            if c.value not in (None, ""):
                cd = ws.column_dimensions.get(c.column_letter)
                if cd is not None and cd.hidden:
                    continue
                max_r = max(max_r, c.row)
                max_c = max(max_c, c.column)
    return max_r, max_c


def _width(ws, first_c, last_c):
    tot = 0.0
    for i in range(first_c, last_c + 1):
        cd = ws.column_dimensions.get(CL(i))
        if cd is not None and cd.hidden:
            continue
        w = cd.width if (cd is not None and cd.width) else 8.43
        tot += w * 5.6 + 3
    return tot


def _height(ws, r1, r2, default):
    tot = 0.0
    for r in range(r1, r2 + 1):
        rd = ws.row_dimensions.get(r)
        if rd is not None and rd.hidden:
            continue
        tot += rd.height if (rd is not None and rd.height) else default
    return tot


def apply(wb, c, fit_overrides=None):
    fit_overrides = fit_overrides or {}
    client = (c.it.client_name or "").replace("&", "&&")
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            continue
        land = ws.title in LANDSCAPE
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.orientation = "landscape" if land else "portrait"
        ws.page_margins.left = ws.page_margins.right = 0.25
        ws.page_margins.top = ws.page_margins.bottom = 0.5
        ws.page_margins.header = ws.page_margins.footer = 0.2
        ws.print_options.horizontalCentered = True
        max_r, max_c = _used(ws)
        statement = ws.title in ("Profit and Loss", "Balance Sheet")
        first_c = 2 if statement else 1
        if statement:
            max_c = 9
        while max_c > first_c and ws.column_dimensions.get(CL(max_c)) is not None and \
                ws.column_dimensions[CL(max_c)].hidden:
            max_c -= 1
        ws.print_area = "%s1:%s%d" % (CL(first_c), CL(max_c), max_r)
        pw = (A4_H if land else A4_W) - 0.5 * 72
        ph = (A4_W if land else A4_H) - 1.0 * 72 - 24
        default_h = 12.75 if ws.title.startswith(("FORM-I", "FORM-V", "ABF", "CHECK", "RATIOS", "CRA", "ANALYSIS")) \
            else 15.75
        wscale = min(1.0, pw / max(_width(ws, first_c, max_c), 1))
        breaks = sorted(b.id for b in ws.row_breaks.brk if b.id < max_r)
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.page_setup.fitToWidth = 1
        if breaks:
            # drop a break whose tail section is short, then scale so every section fits one page
            segs, start = [], 1
            for b in breaks + [max_r]:
                segs.append((start, b))
                start = b + 1
            heights = [_height(ws, a, b, default_h) for a, b in segs]
            tallest = max(heights)
            keep = []
            for k, (a, b) in enumerate(segs[:-1]):
                nxt = heights[k + 1]
                if not statement and nxt < MIN_FILL * tallest:
                    continue
                keep.append(b)
            ws.row_breaks = RowBreak()
            for b in keep:
                ws.row_breaks.append(Break(id=b))
            segs2, start = [], 1
            for b in keep + [max_r]:
                segs2.append(_height(ws, start, b, default_h))
                start = b + 1
            hscale = ph / max(segs2) if max(segs2) else 1.0
            scale = int(max(35, min(100, math.floor(min(wscale, hscale) * 100 * 0.97))))
            ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=False)
            ws.page_setup.scale = scale
        else:
            pages = _height(ws, 1, max_r, default_h) * wscale / ph
            if ws.title in fit_overrides:
                ws.page_setup.fitToHeight = fit_overrides[ws.title]
            elif pages <= ONE_PAGE_UPTO:
                ws.page_setup.fitToHeight = 1
            else:
                whole = math.floor(pages)
                ws.page_setup.fitToHeight = whole if (pages - whole) < MIN_FILL + 0.2 else 0
        ws.oddFooter.left.text = client[:60]
        ws.oddFooter.left.size = 8
        ws.oddFooter.center.text = "&A"
        ws.oddFooter.center.size = 8
        ws.oddFooter.right.text = "Page &P of &N"
        ws.oddFooter.right.size = 8
