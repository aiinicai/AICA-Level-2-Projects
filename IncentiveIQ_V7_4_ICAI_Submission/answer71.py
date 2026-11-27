"""Conservative parser for the flattened UP base-capital-subsidy table."""
import re
from answer62 import pages
from engine import official, validate
REGIONS=[('Gautam Buddha Nagar & Ghaziabad',r'Gautam\s*Buddh?a?\s*Nagar\s*(?:&|and)\s*Ghaziabad(?:\s+districts)?'),('Madhyanchal & Paschimanchal (excluding Gautam Buddha Nagar & Ghaziabad)',r'Madhyanchal\s*(?:&|and)\s*Paschimanchal\s*\(except\s+Gautam\s*Buddh?a?\s*Nagar\s*(?:&|and)\s*Ghaziabad(?:\s+districts)?\)'),('Bundelkhand & Poorvanchal',r'Bundelkhand\s*(?:&|and)\s*Poorvanchal')]
CELL=r'(\d+(?:\.\d+)?)\s*%\s+of\s+ECI\s+over\s+a\s+period\s+of\s+(\d+)\s+years?'
HEADER=r'District\s*/\s*Region\s+Large\s+Mega\s+Super\s+Mega\s+Ultra\s+Mega'
SIZES=['Large','Mega','Super Mega','Ultra Mega']
def capital_rows(docs,q,state):
 if state!='Uttar Pradesh' or not re.search(r'capital\s+subsidy',q,re.I): return []
 if re.search(r'private industrial park|housing|additional|booster|combined|msme|interest subsidy',q,re.I): return []
 if re.search(r'\b20\d{2}\b',q) and not re.search(r'\b2022\b',q): return []
 wanted_sizes={m.group().lower() for m in re.finditer(r'\b(?:ultra\s+mega|super\s+mega|mega|large)\b',q,re.I)}
 wanted_regions=set()
 if re.search(r'Gautam\s*Buddh?a?\s*Nagar|Ghaziabad',q,re.I): wanted_regions.add(REGIONS[0][0])
 if re.search(r'Madhyanchal|Paschimanchal',q,re.I): wanted_regions.add(REGIONS[1][0])
 if re.search(r'Bundelkhand|Poorvanchal',q,re.I): wanted_regions.add(REGIONS[2][0])
 rows=[]
 for src,body in docs.items():
  if not official(src): continue
  for page,raw in pages(body):
   t=' '.join(raw.split())
   for h in re.finditer(HEADER,t,re.I):
    if not re.search(r'base capital subsidy',t[max(0,h.start()-350):h.start()],re.I): continue
    tail=t[h.end():h.end()+2500]; pos=0
    for region,pattern in REGIONS:
     m=re.match(r'\s*'+pattern,tail[pos:],re.I)
     if not m: break
     start=pos; pos+=m.end(); cells=[]
     for size in SIZES:
      c=re.match(r'\s*'+CELL,tail[pos:],re.I)
      if not c: break
      pos+=c.end(); rate,years=c.groups()
      if not (0<float(rate)<=100 and 0<int(years)<=50): break
      cells.append((size,rate,int(years)))
     if len(cells)!=4: break
     for size,rate,years in cells:
      if wanted_sizes and size.lower() not in wanted_sizes: continue
      if wanted_regions and region not in wanted_regions: continue
      rows.append(dict(region=region,size=size,rate=rate+'%',basis='ECI',years=years,source=src,page=page or 'Web / unspecified',excerpt=(page+' '+h.group()+' '+tail[start:pos]).strip(),ocr='[OCR transcription' in t))
 out={}
 for r in rows:
  key=(r['region'],r['size']); old=out.get(key)
  if old and (old['rate'],old['years'])!=(r['rate'],r['years']): return []
  out[key]=r
 if wanted_regions-{r['region'] for r in out.values()} or wanted_sizes-{r['size'].lower() for r in out.values()}: return []
 return list(out.values())

def checked_quote(answer,hits):
 # Accept exact evidence only, with harmless surrounding quote marks removed.
 m=re.fullmatch(r'\s*\[(\d+)\]\s*(.*?)\s*',answer,re.S)
 if not m: return None
 quote=m[2].strip().strip('"“”').strip()
 candidate=f'[{m[1]}] {quote}'
 return candidate if validate(candidate,hits) else None
