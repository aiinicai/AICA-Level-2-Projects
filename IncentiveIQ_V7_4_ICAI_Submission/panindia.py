import re,io,json,hashlib,ssl
from pathlib import Path
from urllib.parse import urlencode,urljoin
from engine import official
STATES='Andhra Pradesh|Arunachal Pradesh|Assam|Bihar|Chhattisgarh|Goa|Gujarat|Haryana|Himachal Pradesh|Jharkhand|Karnataka|Kerala|Madhya Pradesh|Maharashtra|Manipur|Meghalaya|Mizoram|Nagaland|Odisha|Punjab|Rajasthan|Sikkim|Tamil Nadu|Telangana|Tripura|Uttar Pradesh|Uttarakhand|West Bengal|Andaman and Nicobar Islands|Chandigarh|Dadra and Nagar Haveli and Daman and Diu|Delhi|Jammu and Kashmir|Ladakh|Lakshadweep|Puducherry'.split('|')
PORTALS=dict(zip(STATES,['ap.gov.in','arunachalpradesh.gov.in','assam.gov.in','bihar.gov.in','cgstate.gov.in','goa.gov.in','gujarat.gov.in','haryana.gov.in','himachal.nic.in','jharkhand.gov.in','karnataka.gov.in','kerala.gov.in','mp.gov.in','maharashtra.gov.in','manipur.gov.in','meghalaya.gov.in','mizoram.gov.in','nagaland.gov.in','odisha.gov.in','punjab.gov.in','rajasthan.gov.in','sikkim.gov.in','tn.gov.in','telangana.gov.in','tripura.gov.in','up.gov.in','uk.gov.in','wb.gov.in','andaman.gov.in','chandigarh.gov.in','ddd.gov.in','delhi.gov.in','jk.gov.in','ladakh.gov.in','lakshadweep.gov.in','py.gov.in']))
DEFAULTS={'Uttar Pradesh':['https://invest.up.gov.in/uttar-pradesh-industrial-investment-employment-promotion-policy-2022/'],'Maharashtra':['https://maitri.maharashtra.gov.in/wp-content/themes/maitri/PDF/Maharashtra%20New%20Industrial%20Policy-2019.pdf']}
ROOT=Path(__file__).resolve().parent/'policy_cache'
def search(state,topic): return 'https://www.google.com/search?'+urlencode({'q':state+' '+topic+' (site:gov.in OR site:nic.in)'})
def cachepath(state): return ROOT/(hashlib.sha256(state.encode()).hexdigest()+'.json')
def load(state):
 p=cachepath(state)
 return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
def save(state,docs):
 ROOT.mkdir(exist_ok=True); p=cachepath(state); t=p.with_suffix('.tmp'); t.write_text(json.dumps(docs,ensure_ascii=False),encoding='utf-8'); t.replace(p)
def pdftext(data, ocr=True, lang='eng', limit=30, progress=None):
 from pypdf import PdfReader
 from ocr66 import read_page
 if len(data)>20_000_000: raise ValueError('PDF exceeds 20 MB')
 r=PdfReader(io.BytesIO(data)); parts=[]; scanned=0; skipped=0; rendered=None
 try:
  for i,p in enumerate(r.pages[:250]):
   if progress: progress(i+1,min(len(r.pages),250))
   try: text=(p.extract_text(extraction_mode='layout') or '').strip()
   except Exception: text=''
   if len(re.findall(r'\w',text))<30:
    if not ocr or scanned>=limit: skipped+=1; continue
    if rendered is None:
     import fitz
     rendered=fitz.open(stream=data,filetype='pdf')
    text=read_page(rendered[i],lang); scanned+=1
    if text: text='[OCR transcription — verify against original] '+text
   if text: parts.append(f'[Page {i+1}] {text}')
 finally:
  if rendered is not None: rendered.close()
 if not parts: raise ValueError('No extractable text. Enable OCR and check installed languages.')
 if skipped or len(r.pages)>250: parts.append(f'[Coverage warning: {skipped+max(0,len(r.pages)-250)} pages not processed; increase OCR limit if needed.]')
 return '\n'.join(parts)
def fetch(url, **pdf_options):
 import requests,truststore
 from bs4 import BeautifulSoup
 # Use OS certificate store, without disabling certificate validation.
 truststore.inject_into_ssl()
 for _ in range(5):
  if not official(url): raise ValueError('Only HTTPS gov.in or nic.in URLs allowed')
  with requests.get(url,timeout=(8,30),allow_redirects=False,stream=True) as r:
   if r.is_redirect: url=urljoin(url,r.headers['Location']); continue
   r.raise_for_status(); data=bytearray()
   for block in r.iter_content(65536):
    data.extend(block)
    if len(data)>20_000_000: raise ValueError('Source exceeds 20 MB')
   break
 else: raise ValueError('Too many redirects')
 if data.startswith(b'%PDF'): body=pdftext(bytes(data), **pdf_options)
 else:
  soup=BeautifulSoup(bytes(data),'html.parser')
  for tag in soup(['script','style','nav','footer']): tag.decompose()
  body=soup.get_text(' ',strip=True)
 if not body.strip(): raise ValueError('No extractable text')
 return url,body

def evidence(docs,q,k=3):
 words=set(re.findall(r'\w+',q.lower()))-set('what is the in and of for to under how much percentage available policy'.split())
 topic=next((t for t in ['stamp duty','sgst','capital subsidy','interest subsidy','electricity duty','employment','power tariff'] if t in q.lower()),None)
 rows=[]
 for src,body in docs.items():
  parts=[body[max(0,m.start()-200):m.end()+900] for m in re.finditer(re.escape(topic),body,re.I)] if topic else [body[i:i+1000] for i in range(0,len(body),800)]
  for p in parts:
   score=len(words & set(re.findall(r'\w+',p.lower())))
   if score: rows.append((score,src,p))
 return sorted(rows,key=lambda x:x[0],reverse=True)[:k]
