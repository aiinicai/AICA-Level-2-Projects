"""Conservative parser for the flattened UP base-capital-subsidy table."""
import re
from answer62 import pages
from engine import official, validate
REGIONS=[('Gautam Buddha Nagar & Ghaziabad',r'Gautam\s*Bud(?:d)?h?a?\s*Nagar\s*(?:&|and)\s*Ghaziabad(?:\s+districts)?'),('Madhyanchal & Paschimanchal (excluding Gautam Buddha Nagar & Ghaziabad)',r'Madhyanchal\s*(?:&|and)\s*Paschimanchal\s*\((?:except|excluding)\s+Gautam\s*Bud(?:d)?h?a?\s*Nagar\s*(?:&|and)\s*Ghaziabad(?:\s+districts)?\)'),('Bundelkhand & Poorvanchal',r'Bundelkhand\s*(?:&|and)\s*Poorvanchal')]
CELL=r'(\d+(?:\.\d+)?)\s*%\s*of\s*ECI\s*over\s*(?:a\s*)?period\s*of\s*(\d+)\s*years?'
HEADER=r'District\s*/\s*Region\s*Large\s*Mega\s*Super[\s–—-]*Mega\s*Ultra[\s–—-]*Mega'
SIZES=['Large','Mega','Super Mega','Ultra Mega']
def capital_rows(docs,q,state,diagnostics=None):
 def note(message):
  if diagnostics is not None and message not in diagnostics: diagnostics.append(message)
 if state!='Uttar Pradesh' or not re.search(r'capital\s+subsidy',q,re.I): return []
 if re.search(r'private industrial park|housing|additional|booster|combined|msme|interest subsidy',q,re.I): return []
 if re.search(r'\b20\d{2}\b',q) and not re.search(r'\b2022\b',q): return []
 wanted_sizes={m.group().lower() for m in re.finditer(r'\b(?:ultra\s+mega|super\s+mega|mega|large)\b',q,re.I)}
 wanted_regions=set()
 if re.search(r'Gautam\s*Bud(?:d)?h?a?\s*Nagar|Ghaziabad',q,re.I): wanted_regions.add(REGIONS[0][0])
 if re.search(r'Madhyanchal|Paschimanchal',q,re.I): wanted_regions.add(REGIONS[1][0])
 if re.search(r'Bundelkhand|Poorvanchal',q,re.I): wanted_regions.add(REGIONS[2][0])
 rows=[]
 for src,body in docs.items():
  if not official(src): continue
  for page,raw in pages(body):
   t=' '.join(raw.replace('\u200b','').replace('\ufeff','').split())
   if not re.search(HEADER,t,re.I): note('No recognized District/Region and industry-category header in source section.')
   for h in re.finditer(HEADER,t,re.I):
    if not re.search(r'base capital subsidy',t[max(0,h.start()-350):h.start()],re.I):
     note('Header found without nearby base capital subsidy heading.'); continue
    tail=t[h.end():h.end()+2500]
    for region,pattern in REGIONS:
     # Locate each row independently, but never match a district inside an exclusion.
     matches=list(re.finditer(pattern,tail,re.I))
     for m in matches:
      if region==REGIONS[0][0] and re.search(r'(?:except|excluding)\s*$',tail[max(0,m.start()-30):m.start()],re.I): continue
      break
     else:
      note('Region row not found: '+region); continue
     start=m.start(); pos=m.end(); cells=[]
     for size in SIZES:
      c=re.match(r'[\s|;:]*'+CELL,tail[pos:],re.I)
      if not c: break
      pos+=c.end(); rate,years=c.groups()
      if not (0<float(rate)<=100 and 0<int(years)<=50): break
      cells.append((size,rate,int(years)))
     if len(cells)!=4:
      note('Incomplete or unrecognized four-column rate/period row: '+region); continue
     for size,rate,years in cells:
      if wanted_sizes and size.lower() not in wanted_sizes: continue
      if wanted_regions and region not in wanted_regions: continue
      rows.append(dict(region=region,size=size,rate=rate+'%',basis='ECI',years=years,source=src,page=page or 'Web / unspecified',excerpt=(page+' '+t[h.start():h.end()+pos]).strip(),ocr='[OCR transcription' in t))
 out={}
 for r in rows:
  key=(r['region'],r['size']); old=out.get(key)
  if old and (old['rate'],old['years'])!=(r['rate'],r['years']):
   note('Conflicting source rates or periods for '+r['region']+' / '+r['size']); return []
  out[key]=r
 if wanted_regions-{r['region'] for r in out.values()} or wanted_sizes-{r['size'].lower() for r in out.values()}:
  note('Requested region or industry category could not be mapped safely.'); return []
 return list(out.values())

def checked_quote(answer,hits):
 # Accept exact evidence only, with harmless surrounding quote marks removed.
 m=re.fullmatch(r'\s*\[(\d+)\]\s*(.*?)\s*',answer,re.S)
 if not m: return None
 quote=m[2].strip().strip('"“”').strip()
 candidate=f'[{m[1]}] {quote}'
 return candidate if validate(candidate,hits) else None
