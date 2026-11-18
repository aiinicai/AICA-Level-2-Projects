"""Persistent uploaded batches with explicit column selection and offline preview."""
import csv
import io
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook
from core.validators import normalize, validate

MAX_ROWS = 20000

def parse_table(content: bytes, suffix: str, header: bool) -> tuple[list[str], list[list[str]]]:
    """Read first worksheet or delimited text without flattening unrelated columns."""
    if suffix == '.xlsx':
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        try:
            rows=[]
            for row in wb.active.iter_rows(values_only=True):
                rows.append(['' if v is None else str(v) for v in row])
                if len(rows)>MAX_ROWS+1: raise ValueError(f'Maximum {MAX_ROWS} data rows per file.')
        finally: wb.close()
    elif suffix == '.csv':
        text=content.decode('utf-8-sig')
        try: dialect=csv.Sniffer().sniff(text[:8192], delimiters=',;\t')
        except csv.Error: dialect=csv.excel
        rows=list(csv.reader(io.StringIO(text),dialect))
    elif suffix == '.txt':
        rows=[[v] for v in re.split(r'[,;\s]+',content.decode('utf-8-sig')) if v]
        # A TXT header is optional; normal values are never discarded.
        header=header and bool(rows) and rows[0][0].upper() in ('PAN','GSTIN','GST NUMBER','GST')
    else: raise ValueError('Upload .xlsx, .csv or .txt only.')
    rows=[r for r in rows if any(v.strip() for v in r)]
    if not rows: raise ValueError('The file has no populated rows.')
    width=max(len(r) for r in rows)
    if width>200: raise ValueError('Maximum 200 columns per file; upload only the relevant sheet.')
    columns=[str(v).strip() or f'Column {i+1}' for i,v in enumerate(rows.pop(0))] if header else [f'Column {i+1}' for i in range(width)]
    columns += [f'Column {i+1}' for i in range(len(columns),width)]
    if len(rows)>MAX_ROWS: raise ValueError(f'Maximum {MAX_ROWS} data rows per file.')
    return columns,[r+['']*(width-len(r)) for r in rows]

class BatchStore:
    def __init__(self,folder: Path):
        self.folder=folder/'batches';self.folder.mkdir(parents=True,exist_ok=True)
    def _path(self,identifier: str) -> Path:
        if not re.fullmatch('[0-9a-f]{32}',identifier): raise ValueError('Unknown batch file.')
        return self.folder/(identifier+'.json')
    def add(self,filename: str,content: bytes,header: bool=True) -> dict:
        if len(content)>5*1024*1024: raise ValueError('Maximum file size is 5 MB.')
        columns,rows=parse_table(content,Path(filename).suffix.lower(),header)
        identifier=uuid.uuid4().hex
        record={'id':identifier,'name':Path(filename.replace('\\','/')).name,'columns':columns,'rows':rows,'added':datetime.now().isoformat(timespec='seconds')}
        self._path(identifier).write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
        return record
    def get(self,identifier: str) -> dict:
        try: return json.loads(self._path(identifier).read_text(encoding='utf-8'))
        except FileNotFoundError: raise ValueError('Batch file no longer exists.') from None
    def list(self) -> list[dict]:
        result=[]
        for path in self.folder.glob('*.json'):
            record=self.get(path.stem)
            result.append({k:v for k,v in record.items() if k!='rows'}|{'count':len(record['rows'])})
        return sorted(result,key=lambda r:r['added'])
    def delete(self,identifier: str) -> None:
        self._path(identifier).unlink(missing_ok=True)
    def values(self,identifier: str,column: int) -> list[str]:
        record=self.get(identifier)
        if not 0<=column<len(record['columns']): raise ValueError('Select a valid input column.')
        # Retain empty cells to show row validation failures instead of silently dropping them.
        return [r[column] for r in record['rows']]

def preview(values: list[str],kind: str) -> list[dict]:
    if kind not in ('AUTO','GSTIN','PAN'): raise ValueError('Choose GSTIN, PAN or auto-detect.')
    seen=set();result=[]
    for value in values:
        normalized=normalize(value);duplicate=normalized in seen;seen.add(normalized)
        try:
            item=validate(value)
            if kind!='AUTO' and item.kind!=kind: raise ValueError(f'Expected {kind}, found {item.kind}.')
            status='VALID';message=item.meaning
        except ValueError as exc: status='INVALID';message=str(exc)
        result.append({'Value':normalized,'Type':item.kind if status=='VALID' else '—','Validation':status,'Message':message,'Duplicate':'Yes — run once' if duplicate else 'No'})
    return result
