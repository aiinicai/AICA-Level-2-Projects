import re, math
from urllib.parse import urlparse
def chunks(text, size=1100, overlap=180):
    return [text[i:i+size] for i in range(0,len(text),size-overlap)]

def retrieve(docs, question, k=3):
    q=question.lower()
    topics=['stamp duty','sgst','capital subsidy','interest subsidy','electricity duty','export booster','ecosystem booster']
    topic=next((t for t in topics if t in q),None)
    words=set(re.findall(r'\w+',q))-set('what is the in and of for to under how much percentage available'.split())
    rows=[]
    for url,body in docs.items():
        if not official(url): continue
        parts=chunks(body) if not topic else [body[max(0,m.start()-100):m.end()+1400] for m in re.finditer(re.escape(topic),body,re.I)]
        for part in parts:
            low=part.lower()
            score=sum(1 for w in words if w in low)
            if topic=='stamp duty' and re.search(r'stamp duty exemption\s+\d+%',low): score+=30
            if topic=='sgst' and re.search(r'reimbursement of\s+\d+%',low): score+=30
            if score: rows.append((score,url,part))
    return sorted(rows,key=lambda x:x[0],reverse=True)[:k]

def smart_answer(hits, question):
    q=question.lower()
    for _,url,part in hits:
        if 'stamp duty' in q:
            m=re.search(r'stamp duty exemption\s+(.+?)(?=investment promotion subsidy|$)',part,re.I|re.S)
            if not m: continue
            clause=m.group(1).strip()
            if not re.search(r'\d+\s*%',clause): continue
            return url,'Stamp duty exemption: '+clause,'Check project eligibility, applicable notification and amendments.'
        if 'sgst' in q:
            m=re.search(r'reimbursement of\s+(\d+\s*%)\s+of the net SGST amount deposited in State.s account',part,re.I)
            if not m: continue
            tail=part[m.start():]
            tail=re.split(r'Option\s*3\s*:',tail,flags=re.I)[0]
            return url,m.group(1)+' of net SGST deposited in the State account, subject to ceilings and eligibility.',tail
    return None

def validate(answer,hits):
    m=re.fullmatch(r'\s*\[(\d+)\]\s*(.+?)\s*',answer,re.S)
    return bool(m and 1<=int(m[1])<=len(hits) and len(m[2])>=25 and ' '.join(m[2].split()) in ' '.join(hits[int(m[1])-1][2].split()))

def finance(capex, operating, incentive, years, rate):
    factor=sum(1/(1+rate/100)**i for i in range(1,years+1))
    return operating*factor-capex,(operating+incentive)*factor-capex,capex/(operating+incentive) if operating+incentive>0 else math.inf
def official(url):
    u=urlparse(url)
    return u.scheme=="https" and bool(u.hostname) and (u.hostname.endswith(".gov.in") or u.hostname.endswith(".nic.in")) and not u.username and not u.password
