import re
from comparison69 import rows_for as old, TOPICS
from answer62 import pages
from engine import official

def rows_for(state,docs,topic):
    rows=old(state,docs,topic)
    for r in rows:
        ev=r['Evidence']; low=ev.lower(); rate=r['Rate']
        if rate and topic=='Capital subsidy':
            if 'industrial park' in low:
                r['Eligibility / scope']='Private industrial park context — verify developer eligibility'
                r['Basis']='ECI excluding land (verify)' if re.search(r'eci.*?except land',low) else 'Not established'
            elif r['Eligibility / scope'].startswith('Not established'):
                r['Status']='Candidate rate — scope not established; do not use for valuation'
                r['Basis']='Not established'
        if rate and topic=='Stamp duty exemption' and r['Eligibility / scope'].startswith('Not established'):
            r['Status']='Candidate rate — scope not established; do not use for valuation'+(' | OCR provisional' if 'OCR' in r['Status'] else '')
        if r['Policy year (URL hint)']=='2019' and state=='Maharashtra':r['Status']+=' | Historical policy'
        if rate and not r['Years']:
            # Only direct duration tied to the named incentive, not nearby unrelated periods.
            m=re.search(r'(?:'+TOPICS[topic]+r')\s+(?:is available |shall be available |is payable )?for\s+(\d+)\s+years',ev,re.I)
            if m:r['Years']=m[1]
        if rate and not r['Maximum ceiling']:
            m=re.search(r'(?:'+TOPICS[topic]+r')\s+(?:is |shall be )?capped at\s+(?:Rs\.?|₹|INR)\s*([\d,.]+\s*(?:crore|lakh|cr))',ev,re.I)
            if m:r['Maximum ceiling']='INR '+m[1]
    valid=[r for r in rows if r['Rate']]
    if valid:
        seen=set(); result=[]
        for r in valid:
            key=tuple(str(r[k]).lower().replace(' ','') for k in ('Rate','Basis','Eligibility / scope','Maximum ceiling','Years','Source','PDF page'))
            if key not in seen:result.append(r);seen.add(key)
        return result
    first=rows[0].copy()
    first['Evidence']='\n\n'.join(dict.fromkeys(f"{r['PDF page']} | {r['Source']}\n{r['Evidence']}" for r in rows))
    return [first]
