"""Styled, formula-safe, local Excel exports."""
from datetime import date, datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from config import COLUMNS, NA

def safe(value):
    if value is None or value == "": return NA
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')): return "'"+value
    return value

def export(path: Path, rows: list[dict], details: list[dict], logs: list[dict]) -> Path:
    wb=Workbook();wb.remove(wb.active)
    specs=[('Taxpayers',COLUMNS+(['Other'] if any('Other' in r for r in rows) else []),rows),('Return_Detail',['GST NUMBER','Return Type','Tax Period','Status','Filing Date','Financial Year'],details),('Run_Log',['Timestamp','Input','Result','Message'],logs)]
    for name,headers,records in specs:
        ws=wb.create_sheet(name);ws.append(headers);ws.freeze_panes='A2'
        for record in records: ws.append([safe(record.get(h,NA)) for h in headers])
        for cell in ws[1]: cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='163D55')
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width=min(65,max(18,max(len(str(c.value or '').split('\n')[0]) for c in col)+2))
            for c in col:
                c.alignment=Alignment(vertical='top',wrap_text=True)
                if isinstance(c.value,(date,datetime)): c.number_format='DD/MM/YYYY'
        ws.auto_filter.ref=ws.dimensions
    path.parent.mkdir(parents=True,exist_ok=True);wb.save(path);return path
