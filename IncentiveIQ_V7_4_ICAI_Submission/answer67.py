import re
from answer62 import pages
from engine import official
from answer65 import answer as legacy
from answer63 import evidence as old_rank
SECTOR=re.compile(r'\b(selected\s+thrust|general|thrust)\s+sectors?\b',re.I)
PAIR=re.compile(r'maximum\s+ceiling\s+of\s+combined\s+eligible\s+incentives\s+shall\s+be\s+(\d+(?:\.\d+)?)\s*%\s+and\s+(\d+(?:\.\d+)?)\s*%\s+of\s+(EFCI|ECI)\s+over\s+(?:a\s+)?(?:the\s+)?period\s+of\s+(\d+)\s+years?\s+for\s+category\s*[-–]?\s*A\s+and\s+(?:category\s*[-–]?\s*)?B\s+respectively',re.I)
def scope(q):
    return {m.group(1).lower() for m in SECTOR.finditer(q)}
def relevant(q):
    return bool(re.search(r'combined|financial incentives|incentive ceiling',q,re.I))
def candidates(docs,q):
    wanted=scope(q); rows=[]
    for src,body in docs.items():
        if not official(src): continue
        for page,raw in pages(body):
            t=' '.join(raw.split())
            for m in PAIR.finditer(t):
                preceding=list(SECTOR.finditer(t[:m.start()]))
                if not preceding: continue
                s=preceding[-1]; sector=s.group(1).lower()
                if m.start()-s.end()>650 or (wanted and sector not in wanted): continue
                if not all(0<=float(m[i])<=100 for i in (1,2)) or not 1<=int(m[4])<=50: continue
                excerpt=(page+' '+ ('[OCR transcription — verify against original] ' if '[OCR transcription' in t else '')+t[max(0,s.start()-100):m.end()]).strip()
                rows.append(dict(sector=sector,a=m[1],b=m[2],basis=m[3].upper(),years=int(m[4]),source=src,page=page,excerpt=excerpt,ocr='[OCR transcription' in t))
    return rows

def structured(docs,q):
    if not relevant(q): return []
    rows=candidates(docs,q); out=[]
    for sector in sorted({r['sector'] for r in rows}):
        group=[r for r in rows if r['sector']==sector]
        if len({(r['a'],r['b'],r['basis'],r['years']) for r in group})!=1: return []
        out.append(group[0])
    if scope(q)-{r['sector'] for r in out}: return []
    return out

def rank(docs,q,k=5):
    rows=old_rank(docs,q,k=max(k,15))
    wanted=scope(q)
    if wanted:
        rows=[(score+(100 if scope(p)&wanted else -100),src,p) for score,src,p in rows]
    return sorted(rows,key=lambda r:r[0],reverse=True)[:k]
