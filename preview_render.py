"""Real PDF export preview; not an emulation of Excel/Word pagination."""
import hashlib,json
from pathlib import Path

def case_fingerprint(case):return hashlib.sha256(json.dumps(case.to_dict(),sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()

def render_pdf_page(path,number,zoom,output):
    import pymupdf
    scale=float(zoom)/100
    if not .25<=scale<=2:raise ValueError('Preview zoom must be 25-200%.')
    with pymupdf.open(path) as doc:
        if not 0<=number<len(doc):raise ValueError('Preview page is outside the PDF page range.')
        pix=doc[number].get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False);pix.save(output)
        return dict(path=str(output),page=number,count=len(doc),zoom=zoom)

def apply_pdf_page_range(path,expression):
    import re,pymupdf
    if not expression.strip():return
    requested=[]
    for part in expression.split(','):
        m=re.fullmatch(r'\s*(\d+)(?:\s*-\s*(\d+))?\s*',part)
        if not m:raise ValueError('PDF pages use 1-based ranges such as 1-3,5.')
        start=int(m[1]);end=int(m[2] or start)
        if start<1 or end<start:raise ValueError('PDF page ranges must be positive and ascending.')
        requested.extend(range(start-1,end))
    with pymupdf.open(path) as doc:
        if any(i>=len(doc) for i in requested):raise ValueError('PDF page range exceeds the generated '+str(len(doc))+' pages.')
        unique=list(dict.fromkeys(requested));doc.select(unique);temporary=Path(str(path)+'.pages.pdf');doc.save(temporary)
    temporary.replace(path)
