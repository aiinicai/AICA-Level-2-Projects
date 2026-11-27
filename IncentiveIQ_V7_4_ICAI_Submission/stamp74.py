"""Extract explicitly scoped stamp-duty clauses, not nearby unrelated rates."""
import re
from answer62 import pages
from engine import official
RATE=r'(\d+(?:\.\d+)?)\s*(?:%|per\s+cent|percent)'
PATTERNS=[
 r'(?P<scope>eligible\s+MSMEs?)\s+will\s+be\s+entitled\s+to\s+'+RATE+r'\s+stamp\s+duty\s+exemption\b',
 r'(?P<scope>(?:the\s+)?industrial\s+units?\s+under\s+selected\s+thrust\s+sectors?)\s+shall\s+be\s+eligible\s+to\s+claim\s+'+RATE+r'\s+reimbursement\s+of\s+stamp\s+duty\b',
 r'(?P<scope>eligible\s+ultra[ -]mega\s+industrial\s+undertakings?)\s+shall\s+be\s+eligible\s+to\s+claim\s+'+RATE+r'\s+reimbursement\s+of\s+stamp\s+duty\b',
]
def stamp_rows(docs,q,state):
 if not re.search(r'stamp\s+duty',q,re.I): return []
 out=[]; seen=set()
 for src,body in docs.items():
  if not official(src): continue
  for page,raw in pages(body):
   t=' '.join(raw.split())
   for pattern in PATTERNS:
    for m in re.finditer(pattern,t,re.I):
     rate=m[2]; scope=m['scope']; ocr='[OCR transcription' in raw
     if not 0<float(rate)<=100: continue
     if re.search(r'\bMSMEs?\b',q,re.I) and not re.search(r'MSME',scope,re.I): continue
     if re.search(r'\blarge\b',q,re.I) and re.search(r'MSME|ultra',scope,re.I): continue
     key=(scope.lower(),rate,src,page)
     if key in seen: continue
     seen.add(key)
     year=re.search(r'(?:policy|incentives)[%\s_/-]*(20\d{2})',src,re.I)
     out.append(dict(scope=scope,rate=rate+'%',kind='Exemption' if 'exemption' in m.group().lower() else 'Reimbursement',year=year[1] if year else 'Not established',page=page or 'Web / unspecified',source=src,excerpt=(page+' '+t[max(0,m.start()-100):min(len(t),m.end()+650)]).strip(),ocr=ocr))
 return out
