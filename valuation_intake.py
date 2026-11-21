"""Draft-first valuation intake: ranked values and explicit, evidence-based identity proposals."""
import re
from decimal import Decimal

def valuation_proposals(text,path=''):
    from asset_model import money,norm
    from document_intake import clean_name,valid_date
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    warnings=[];values=[];owners=[];last_label='';last_kind='';last_score=0
    currency=re.compile(r'(?:Rs\.?|INR|₹)\s*[:.]?\s*([0-9][0-9,]*(?:\.\d{1,2})?)',re.I)
    def classify(line):
        low=line.lower()
        if re.search(r'per\s+(?:marla|acre|sq|square|cent|grams?|gm|tola|kg)|/\s*(?:marla|acre|sq)|unit\s*rate',low):return 'unit rate',-100
        if re.search(r'(?:final|certified|adopted|concluded)\s+(?:market\s+)?(?:total\s+)?(?:value|valuation)|grand\s+total',low):return 'final certified total',950
        if re.search(r'total\s+(?:market\s+)?value\s+(?:of\s+)?(?:the\s+)?(?:property|land\s*(?:and|\+)\s*building)|total\s+(?:property|land\s*(?:and|\+)\s*building)\s+value',low):return 'property total',850
        if re.search(r'total\s+(?:(?:market|assessed)\s+)?value|total\s+valuation|market\s+value\s+of\s+(?:the\s+)?property',low):return 'total value',750
        if re.search(r'(?:value|cost)\s+of\s+(?:the\s+)?(?:land|plot)|land\s+(?:value|cost)',low):return 'land component',400
        if re.search(r'(?:value|cost)\s+of\s+(?:the\s+)?(?:building|construction|built[ -]?up)|(?:building|construction)\s+(?:value|cost)',low):return 'building component',400
        return '',0
    for i,line in enumerate(lines):
        kind,score=classify(line)
        if kind:last_label=line;last_kind=kind;last_score=score
        elif re.match(r'(?i)(?:note\b|\d+\.\s*[A-Za-z]|ref\b|mob\b)',line):last_label='';last_kind='';last_score=0
        matches=currency.findall(line)
        if not matches and kind:
            tail=line.rsplit(':',1)[-1].strip()
            if re.fullmatch(r'[0-9][0-9,]*(?:\.\d{1,2})?(?:/-)?',tail):matches=[tail.removesuffix('/-')]
        if not matches and last_kind and re.fullmatch(r'\s*:?[ ]*[0-9][0-9,]*(?:\.\d{1,2})?(?:/-)?',line):matches=[line.strip(' :').removesuffix('/-')]
        for raw in matches:
            try:amount=float(money(raw,True))
            except ValueError:continue
            actual_kind,actual_score=kind or last_kind,score or last_score
            if re.search(r'\d\s*%|per\s+(?:marla|acre|sq|square|cent|grams?|gm|tola|kg)|/\s*(?:marla|acre|sq)',line,re.I):actual_kind,actual_score='unit rate / percentage',-100
            values.append(dict(amount=amount,kind=actual_kind or 'unlabelled amount',score=actual_score,line=i+1,text=line,context=last_label))
    components={k:sorted({v['amount'] for v in values if v['kind']==k}) for k in ('land component','building component')}
    component_sum=None
    if all(len(v)==1 for v in components.values()):
        component_sum=float(sum(Decimal(str(v[0])) for v in components.values()))
        for v in values:
            if v['score']>=750 and money(v['amount'])==money(component_sum):v['score']+=40
        values.append(dict(amount=component_sum,kind='calculated land + building',score=650,line=0,text='Calculated from unique land and building components; review required.',context='components',calculated=True))
    eligible=[v for v in values if v['score']>=650]
    top=max((v['score'] for v in eligible),default=0)
    top_amounts=sorted({v['amount'] for v in eligible if v['score']==top})
    chosen=top_amounts[0] if len(top_amounts)==1 else ''
    if not chosen:warnings.append('Choose a value candidate or enter the reviewed amount below. No total has been guessed.')
    elif component_sum is not None and money(chosen)!=money(component_sum):warnings.append('Selected certified/total value differs from the land + building sum. Review source basis; no value was silently changed.')
    if len({v['amount'] for v in eligible})>1:warnings.append('Other value candidates are retained for review; explicit final/certified context takes precedence over components and rates.')
    def scan_label(pattern):
        found=[]
        for i,line in enumerate(lines):
            m=re.search(pattern,line,re.I)
            if not m:continue
            tail=line[m.end():].strip(' :|.-')
            j=i
            if not tail:
                for j in range(i+1,min(i+5,len(lines))):
                    tail=lines[j].strip(' :|')
                    if tail:break
            if tail:found.append((tail,j,i))
        return found
    for pattern,score in [(r'\b(?:owner\s*name|name\s+of\s+(?:the\s+)?owners?|owners?\s*\(s\)|property\s+owned\s+by|owned\s+by)\b',900),
                           (r'\b(?:applicant\s*name|name\s+of\s+(?:the\s+)?applicant|client\s*name)\b',700),
                           (r'\bowner\s*:',850)]:
        for tail,j,i in scan_label(pattern):
            name,_=clean_name(tail)
            if not name or re.search(r'architect|valuer|engineer|consultant|@|lic\b',name,re.I):continue
            relation=re.search(r'\s+([SDW])\s*/\s*[Oo]\s+(.+)',tail,re.I)
            owners.append(dict(name=name,father_name=relation[2].strip() if relation and relation[1].upper() in ('S','D') else '',spouse_name=relation[2].strip() if relation and relation[1].upper()=='W' else '',relation_text=tail,score=score,evidence=[dict(line=i+1,text=lines[i]),dict(line=j+1,text=lines[j])]))
    merged={}
    for candidate in owners:
        key=(norm(candidate['name']),norm(candidate['father_name']),norm(candidate['spouse_name']))
        if key not in merged:merged[key]=dict(candidate,evidence=[])
        merged[key]['score']=max(merged[key]['score'],candidate['score'])
        for evidence in candidate['evidence']:
            if evidence not in merged[key]['evidence']:merged[key]['evidence'].append(evidence)
    owners=list(merged.values())
    # Retain cover/body corroboration, but treat genuinely different owner identities as a conflict.
    owner_score=max((o['score'] for o in owners),default=0)
    primary=[o for o in owners if o['score']==owner_score]
    identities={norm(o['name']) for o in primary}
    if len(identities)==1:
        owner=primary[0].copy();owner['evidence']=[e for o in owners if norm(o['name'])==norm(owner['name']) for e in o['evidence']]
        fathers={norm(o['father_name']) for o in owners if norm(o['name'])==norm(owner['name']) and o['father_name']}
        if len(fathers)>1:warnings.append('Owner name agrees but parent names differ; verify the owner evidence.')
    else:
        owner=dict(name='',father_name='',spouse_name='',relation_text='',evidence=[])
        if primary:warnings.append('Different owner names are explicitly stated. Select or enter the reviewed owner below.')
    def first(pattern):
        found=scan_label(pattern);return (found[0][0],found[0][1]) if found else ('',-1)
    asset_name,_=first(r'\b(?:property|nature\s+of\s+property|asset\s+name)\s*:')
    if not asset_name:
        match=re.search(r'(?i)(semi[ -]?constructed[^\n]{0,70}(?:plot|house|property)|vacant\s+plot|residential\s+(?:plot|house))',text)
        asset_name=match[0] if match else 'Immovable property - enter asset name'
    if asset_name.isupper():asset_name=asset_name.title()
    address,ai=first(r'address\s+of\s+(?:the\s+)?property\b|property\s+address\b')
    if ai>=0:
        parts=[address]
        for line in lines[ai+1:]:
            if re.match(r'\d+\s*[.)]',line):break
            parts.append(line)
        address=re.sub(r'^This\s+.*?\s+(?:situated|located)\s+at\s*','',' '.join(parts),flags=re.I)
    date,_=first(r'date\s+of\s+valuation\b|valuation\s+date\b');date=valid_date(date)
    if not date:raw,_=first(r'\bdate\s*:');date=valid_date(raw)
    deed,di=first(r'deed\s*(?:date\s*/\s*no\.?|no\.?)')
    if di>=0:
        rest=[]
        for line in lines[di+1:]:
            if re.match(r'\d+\s*[.)]',line):break
            rest.append(line)
        deed=' '.join([deed]+rest)
    area,_=first(r'area\s+of\s+(?:the\s+)?(?:plot|property)\b');tenure,_=first(r'tenure\s+of\s+property\b')
    ref,_=first(r'\bref(?:erence)?\.?\s*(?:no\.?|number)?\s*[:.-]?')
    valuer_name,_=first(r'\b(?:name\s+of\s+(?:the\s+)?(?:architect|valuer)|architect\s*name|valuer\s*name|prepared\s+by|architect\s*:|valuer\s*:)')
    if not valuer_name:
        for line in lines:
            m=re.match(r'(?:Er\.|Architect\s+)\s*([A-Za-z .]+)(?:\(|,|$)',line,re.I)
            if m:valuer_name=m[1].strip();break
    firm=next((line for line in lines if re.search(r'associates|consultants|valuation\s+(?:firm|services)',line,re.I) and not re.search(r'owner|applicant|@|mob|lic\b|engineer,\s*architect',line,re.I)),'')
    credentials=[]
    for line in lines:
        if re.search(r'(?:lic(?:en[cs]e)?\.?\s*(?:no|number)|MCB[- ]|member\s+of\s+IOV|registered\s+valuer)',line,re.I) and line not in credentials:credentials.append(line)
    fields=dict(valuer_credentials='; '.join(credentials),nature=asset_name,holder=owner['name'],relation='Unconfirmed',location=address,valuer=' / '.join(x for x in (valuer_name,firm) if x),valuer_name=valuer_name,valuer_firm=firm,val_date=date,val_ref=ref,deed=deed,area=area,tenure=tenure)
    details=asset_name+(' at '+address if address else '')+('; Area: '+area if area else '')+('; Deed: '+deed if deed else '')
    proposal=dict(category='Immovable Property',asset_name=asset_name,amount=chosen,fields=fields,desc=details,source=path,owner_candidate=owner,owner_candidates=owners,amount_candidates=values,amount_evidence=values,requires_amount_review=not bool(chosen))
    return dict(assets=[proposal],owner_candidate=owner,owner_candidates=owners,amount_candidates=values,component_sum=component_sum,warnings=warnings)
