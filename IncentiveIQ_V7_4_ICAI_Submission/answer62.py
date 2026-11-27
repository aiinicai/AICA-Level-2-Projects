import re
from engine import official, smart_answer

def pages(body):
    marks=list(re.finditer(r'\[Page (\d+)\]',body))
    if not marks:
        yield '',body
    else:
        for i,m in enumerate(marks):
            yield m.group(),body[m.end():marks[i+1].start() if i+1<len(marks) else len(body)]

def evidence(docs,q,k=5):
    q=q.lower(); words=set(re.findall(r'\w+',q))-set('what is the in and of for to under how much percentage available policy industrial investment reimbursement rate are a an'.split())
    topic=next((t for t in ['stamp duty','sgst','capital subsidy','interest subsidy','electricity duty','employment','power tariff','export booster','ecosystem booster'] if t in q),None)
    rows=[]
    for src,body in docs.items():
        for page,raw in pages(body):
            text=' '.join(raw.split())
            if topic:
                pattern=r'\b(?:sgst|state goods and services tax)\b' if topic=='sgst' else re.escape(topic)
                parts=[text[max(0,m.start()-450):m.end()+650] for m in re.finditer(pattern,text,re.I)]
            else:
                parts=[text[i:i+1000] for i in range(0,len(text),750)]
            for p in parts:
                low=p.lower(); tokens=set(re.findall(r'\w+',low)); score=len(words & tokens)
                if not topic and score<min(2,len(words)): continue
                if not topic and not score: continue
                if re.search(r'\d+\s*(?:%|percent|per cent)',low): score+=3
                if 'msme' in q and re.search(r'\bmsmes?\b|micro,? small',low): score+=8
                if 'sgst' in q and re.search(r'\d+\s*%\s*(?:of\s+)?(?:the\s+)?(?:gross|net)\s+sgst',low): score+=5
                rows.append((score,src,(page+' '+p).strip()))
    out=[]
    for row in sorted(rows,key=lambda x:x[0],reverse=True):
        if any(row[1]==r[1] and row[2]==r[2] for r in out): continue
        out.append(row)
        if len(out)>=k: break
    return out

def answer(hits,q,state):
    # Keep only explicit source wording. Never infer a rate from nearby unrelated text.
    q=q.lower()
    if state=='Uttar Pradesh' and 'msme' not in q:
        result=smart_answer([h for h in hits if official(h[1])],q)
        if result: return result
    if 'sgst' in q and 'msme' in q:
        matches=[]
        for _,src,p in hits:
            if not official(src): continue
            # Explicit category followed by rate and tax basis, within one short clause.
            pattern=r'\bMSMEs?\b\s*(?:[-–—:]|units?\b|shall be eligible for|will be eligible for|are eligible for|eligible for|shall get|will get|of|IPS|reimbursement|of SGST|Industrial Promotion Subsidy|\s){0,12}\s*(\d+(?:\.\d+)?\s*%)\s*(?:of\s+)?(?:the\s+)?(gross|net)\s+SGST\b'
            for m in re.finditer(pattern,p,re.I):
                matches.append((src,m.group(0),p,m.group(1).replace(' ',''),m.group(2).lower()))
        if matches and len({(m[3],m[4]) for m in matches})==1:
            src,quote,p,_,_=matches[0]; return src,quote,p
    return None
