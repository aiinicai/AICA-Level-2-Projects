import re
from decimal import Decimal
from answer63 import answer as legacy
from engine import official
CAT=r'\b(?:MSMEs?|micro\s*[,/&-]?\s*small\s*(?:and|&|,)\s*medium(?:\s+(?:manufacturing\s+)?enterprises)?)\b'
TAX=r'(?:SGST|state\s+goods\s*(?:&|and)\s*services\s+tax(?:\s*\(SGST\))?)\b'
RATE=r'(?:\d+(?:\.\d+)?\s*(?:%|per\s*cent|percent)|(?:one\s+)?hundred\s+per\s*cent)'
LINK=r'\s*(?:units?\s*)?(?:[-–—:]\s*|(?:shall|will)\s+(?:be\s+)?(?:offered|eligible\s+for|receive|get|given|provided)\s+|(?:are\s+)?eligible\s+for\s+|(?:industrial|investment)\s+promotion\s+subsidy\s*|\(IPS\)\s*|IPS\s*|reimbursement\s*|on\s+|of\s+)*'
PAT=re.compile(CAT+LINK+r'(?P<rate>'+RATE+r')\s*(?:of\s+)?(?:the\s+)?(?P<basis>gross|net)\s+'+TAX,re.I)
def answer(hits,q,state):
    if not (re.search(TAX,q,re.I) and re.search(CAT,q,re.I)):
        return legacy(hits,q,state)
    found=[]
    for _,src,p in hits:
        if not official(src): continue
        for m in PAT.finditer(p):
            num=re.search(r'\d+(?:\.\d+)?',m['rate']); rate=Decimal(num.group()) if num else Decimal(100)
            if not 0<=rate<=100: continue
            found.append((rate,m['basis'].lower(),src,p,m.group()))
    if not found or len({(x[0],x[1]) for x in found})!=1: return None
    rate,basis,src,p,quote=found[0]
    if re.search(r'\bgross\b',q,re.I) and basis!='gross' or re.search(r'\bnet\b',q,re.I) and basis!='net': return None
    page=re.match(r'\[Page (\d+)\]',p)
    ref=f' (PDF page {page[1]})' if page else ''
    return src,f'{rate:f}% of {basis.title()} SGST for eligible MSMEs, subject to scheme conditions.{ref}',p
