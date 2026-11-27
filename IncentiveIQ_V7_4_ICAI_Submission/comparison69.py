import re
from answer62 import pages
from answer65 import PAT
from answer68 import structured
from engine import official
TOPICS={'Stamp duty exemption':r'stamp duty(?:\s*/\s*registration(?: charges| fees)?)?', 'SGST reimbursement':r'SGST|state goods\s*(?:&|and)\s*services tax','Capital subsidy':r'capital subsidy','Interest subsidy':r'interest subsidy','Electricity duty exemption':r'electricity duty','Power tariff subsidy':r'power tariff','Combined incentive ceiling':r'combined incentive'}
RATE=r'\d+(?:\.\d+)?\s*(?:%|per\s*cent|percent)'
STOP=r'(?=\s+(?:investment promotion subsidy|option\s*\d|capital subsidy|interest subsidy|electricity duty|power tariff)\b|[.;]|$)'
def rows_for(state,docs,topic):
 out=[]; candidates=[]
 def add(src,page,raw,rate='',basis='',scope='',years='',ceiling='',status='Explicit rate — verify eligibility',quote=''):
  year=re.search(r'(?:policy|incentives)[%\s_/-]*(20\d{2})',src,re.I)
  out.append({'State':state,'Incentive':topic,'Rate':rate,'Basis':basis,'Eligibility / scope':scope,'Maximum ceiling':ceiling,'Years':years,'Policy year (URL hint)':year[1] if year else 'Not established','PDF page':page or 'Web / unspecified','Status':status+(' | OCR provisional' if '[OCR transcription' in raw else '')+(' | incomplete document' if '[Coverage warning:' in docs.get(src,'') else ''),'Source':src,'Evidence':quote})
 if topic=='Combined incentive ceiling':
  for r in structured(docs,'combined incentive ceiling'):
   add(r['source'],r['page'],r['excerpt'],r['a']+'% (A); '+r['b']+'% (B)',r['basis'],r['size']+' / '+r['sector'],r['years'],'Combined ceiling',quote=r['excerpt'])
 for src,body in docs.items():
  if not official(src): continue
  for page,raw in pages(body):
   t=' '.join(raw.split()); pattern=TOPICS[topic]
   for m in re.finditer(pattern,t,re.I):
    excerpt=t[max(0,m.start()-220):m.end()+450]; candidates.append((bool(re.search(RATE,excerpt,re.I)),src,page,raw,excerpt))
   if topic=='Combined incentive ceiling': continue
   if topic=='SGST reimbursement':
    for m in PAT.finditer(t):
     add(src,page,raw,m['rate'],m['basis'].title()+' SGST','MSME; see scheme conditions',quote=t[m.start():min(len(t),m.end()+180)])
    for m in re.finditer(r'reimbursement of\s+('+RATE+r')\s+of\s+the\s+net\s+SGST\b',t,re.I):
     add(src,page,raw,m[1],'Net SGST','See scheme conditions',quote=t[m.start():m.end()+180])
   elif topic=='Stamp duty exemption':
    for m in re.finditer(r'stamp duty exemption\s*[:–-]?\s*('+RATE+r'\s+in\s+.+?)'+STOP,t,re.I):
     clause=m[1]
     if len(clause)>500: continue
     for p in re.finditer('('+RATE+r')\s+in\s+(.+?)(?=\s*,?\s*'+RATE+r'\s+in\b|$)',clause,re.I):
      add(src,page,raw,p[1],'Stamp duty',p[2].strip(' ,'),quote=m.group())
   if topic!='SGST reimbursement':
    # Only directly adjacent rates; no nearby unrelated percentage inference.
    for m in re.finditer(r'('+pattern+r')\s*(?:exemption|reimbursement|subsidy)?\s*(?:@|at|of|:|shall be|is)\s*('+RATE+r')|('+RATE+r')\s+(?:exemption|reimbursement|subsidy)\s+(?:on|of|in)\s+('+pattern+r')',t,re.I):
     add(src,page,raw,m[2] or m[3],topic,'Not established — read evidence',quote=t[max(0,m.start()-100):m.end()+180])
 unique=[]; seen=set()
 for r in out:
  key=tuple(r[k] for k in ('Rate','Basis','Eligibility / scope','Source','PDF page'))
  if key not in seen: seen.add(key); unique.append(r)
 if unique: return unique
 if candidates:
  for _,src,page,raw,excerpt in sorted(candidates,key=lambda x:x[0],reverse=True)[:3]:
   add(src,page,raw,status='Insufficient evidence for structured rate',quote=excerpt)
  return out
 add('','', '',status='Insufficient evidence — fetch official policy or relevant clause')
 return out
