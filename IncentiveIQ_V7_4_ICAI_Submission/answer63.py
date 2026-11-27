import re
from answer62 import pages, answer as legacy
from engine import official
CAT=r'\b(?:MSMEs?|micro\s*[,/&-]?\s*small\s*(?:and|&|,)\s*medium(?:\s+enterprises)?|micro and small enterprises)\b'
RATE=r'\b\d+(?:\.\d+)?\s*(?:%|per\s*cent|percent)'
TAX=r'\b(?:SGST|state goods and services tax)\b'
TOPICS=['stamp duty','sgst','capital subsidy','interest subsidy','electricity duty','employment','power tariff','export booster','ecosystem booster']
STOP=set('what is the in and of for to under how much percentage available policy industrial investment reimbursement rate are a an maharashtra gujarat pradesh 2019 2022'.split())
def evidence(docs,q,k=8):
    q=q.lower(); words=set(re.findall(r'\w+',q))-STOP
    topic=next((t for t in TOPICS if t in q),None)
    pattern=TAX if topic=='sgst' else re.escape(topic) if topic else None
    category=CAT if re.search(CAT,q,re.I) else next((r'\b'+x+r'\b' for x in ['ultra mega','super mega','mega','large'] if x in q),None)
    rows=[]
    for src,body in docs.items():
        for page,raw in pages(body):
            t=' '.join(raw.split()); anchors=list(re.finditer(pattern,t,re.I)) if pattern else []
            if pattern and not anchors: continue
            spans=[(max(0,m.start()-500),min(len(t),m.end()+550),m.start()) for m in anchors] if pattern else [(i,min(i+1000,len(t)),i) for i in range(0,len(t),750)]
            for a,b,pos in spans:
                p=t[a:b]; low=p.lower(); score=3*len(words & set(re.findall(r'\w+',low)))
                if not pattern and not score: continue
                score+=5*bool(re.search(RATE,p,re.I))
                score+=5*bool(re.search(r'\b(?:gross|net)\s+SGST',p,re.I))
                if category:
                    distances=[abs(a+m.start()-pos) for m in re.finditer(category,p,re.I)]
                    score+=max(0,40-min(distances)//12) if distances else -25
                if topic=='sgst' and re.search(r'\b(?:reimbursement|refund|industrial promotion subsidy|IPS)\b',p,re.I): score+=8
                if sum('\u0900'<=c<='\u097f' for c in p)>len(p)*.15: score-=20
                if category and re.search(category,p,re.I) and re.search(RATE,p,re.I): score+=8
                rows.append((score,src,(page+' '+p).strip(),a,b,page))
    out=[]; selected=[]
    for score,src,p,a,b,page in sorted(rows,key=lambda x:x[0],reverse=True):
        if any(src==s and page==pg and max(0,min(b,y)-max(a,x))>min(b-a,y-x)*.65 for s,pg,x,y in selected): continue
        selected.append((src,page,a,b)); out.append((score,src,p))
        if len(out)>=k: break
    return out

def answer(hits,q,state):
    # Explicit category + rate + tax basis in a short clause only. Ambiguity remains evidence-only.
    if 'sgst' in q.lower() and re.search(CAT,q,re.I):
        found=[]
        pattern=CAT+r'\s*(?:units?\s*)?(?:[-–—:]\s*|(?:shall|will)\s+(?:be eligible for|receive|get)\s+|(?:are\s+)?eligible for\s+|(?:IPS|industrial promotion subsidy|reimbursement)\s*[:–-]?\s*)*'+r'('+RATE+r')\s*(?:of\s+)?(?:the\s+)?(gross|net)\s+SGST\b'
        for _,src,p in hits:
            if not official(src): continue
            for m in re.finditer(pattern,p,re.I): found.append((src,m.group(),p,re.sub(r'\D','',m.group(1)),m.group(2).lower()))
        if found and len({(x[3],x[4]) for x in found})==1:
            src,quote,p,_,_=found[0]; return src,quote,p
        return None
    return legacy(hits,q,state)
