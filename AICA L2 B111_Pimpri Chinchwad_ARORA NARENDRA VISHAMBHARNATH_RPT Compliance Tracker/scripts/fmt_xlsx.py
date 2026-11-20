import sys
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
IND = '[>=10000000]##\\,##\\,##\\,##0;[>=100000]##\\,##\\,##0;##,##0'
HDR = PatternFill("solid", fgColor="1F3864")
for path in sys.argv[1:]:
    wb = load_workbook(path)
    for ws in wb.worksheets:
        hdr = [c.value for c in ws[1]]
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF", name="Arial", size=10)
            c.fill = HDR
            c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.freeze_panes = "A2"
        for col_idx, h in enumerate(hdr, start=1):
            letter = get_column_letter(col_idx)
            maxlen = max([len(str(c.value)) if c.value is not None else 0 for c in ws[letter]][:200] + [8])
            ws.column_dimensions[letter].width = min(max(10, maxlen + 2), 60)
            h = str(h or "")
            for c in ws[letter][1:]:
                c.font = Font(name="Arial", size=10)
                if any(k in h for k in ("(Rs)", "Amount", "Limit", "Value")) and isinstance(c.value, (int, float)):
                    c.number_format = IND
                elif h in ("Rate",) and isinstance(c.value, (int, float)):
                    c.number_format = '#,##0.00'
                elif h == "Deviation" and isinstance(c.value, (int, float)):
                    c.number_format = '0.0%'
                elif "Date" in h or h in ("Valid from", "Valid to"):
                    c.number_format = 'dd-mmm-yyyy'
        if ws.title in ("Company", "Summary"):
            for row in ws.iter_rows(min_row=2):
                for c in row:
                    if isinstance(c.value, (int, float)) and abs(c.value) >= 1000:
                        c.number_format = IND
    wb.save(path)
    print("formatted", path)
