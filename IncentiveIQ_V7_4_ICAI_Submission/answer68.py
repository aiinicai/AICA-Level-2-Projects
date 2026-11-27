import re
from answer67 import PAIR, relevant, rank as old_rank
from answer62 import pages
from engine import official
SECT=re.compile(r'\b(selected\s+thrust|general|thrust)\b',re.I)
SIZE=re.compile(r'\b(ultra[ -]?mega|mega|large|msme)\s+(?:industrial\s+)?(?:undertakings?|units?|industries|projects?)\b',re.I)
HEADER=re.compile(r'\b(ultra[ -]?mega|mega|large|msme)\s+(?:industrial\s+)?(?:undertakings?|units?|industries|projects?)\s+for\s+(selected\s+thrust|general|thrust)\s+sectors?\b',re.I)
def norm(s): return ' '.join(s.lower().replace('-',' ').split())
def scope(q):
 return {norm(m.group()) for m in SECT.finditer(q)}
def sizes(q): return {norm(m.group(1)) for m in SIZE.finditer(q)}
def candidates(docs,q):
 wanted=scope(q); cats=sizes(q); out=[]
 for src,body in docs.items():
  if not official(src): continue
  for page,raw in pages(body):
   t=' '.join(raw.split()); headers=list(HEADER.finditer(t))
   for m in PAIR.finditer(t):
    hs=[h for h in headers if h.end()<=m.start()]
    if not hs: continue
    h=hs[-1]; size,sector=map(norm,h.groups())
    if m.start()-h.end()>650 or (wanted and sector not in wanted) or (cats and size not in cats): continue
    if not all(0<=float(m[i])<=100 for i in (1,2)) or not 1<=int(m[4])<=50: continue
    ocr='[OCR transcription' in t
    out.append(dict(size=size,sector=sector,a=m[1],b=m[2],basis=m[3].upper(),years=int(m[4]),source=src,page=page,ocr=ocr,excerpt=page+' '+('[OCR transcription — verify against original] ' if ocr else '')+t[h.start():m.end()]))
 return out

def structured(docs,q):
 if not relevant(q): return []
 rows=candidates(docs,q); out=[]
 for size,sector in sorted({(r['size'],r['sector']) for r in rows},key=lambda x:(x[0],['general','thrust','selected thrust'].index(x[1]))):
  group=[r for r in rows if (r['size'],r['sector'])==(size,sector)]
  if len({(float(r['a']),float(r['b']),r['basis'],r['years']) for r in group})!=1: return []
  out.append(group[0])
 if scope(q)-{r['sector'] for r in out} or sizes(q)-{r['size'] for r in out}: return []
 return out

def rank(docs,q,k=5):
 rows=old_rank(docs,q,k=max(k,15)); wanted=scope(q); cats=sizes(q)
 return sorted([(score+ (100 if wanted & scope(p) else 0)+(100 if cats & sizes(p) else 0),src,p) for score,src,p in rows],reverse=True)[:k]
