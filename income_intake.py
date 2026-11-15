"""Label/table-context tax parsing with independent person/year/source records."""
import copy,re
from decimal import Decimal
from pathlib import Path

LABELS={
 'salary':r'income\s+from\s+salar(?:y|ies)|salary\s+income',
 'house_property':r'income\s+from\s+house\s+property|house\s+property\s+income',
 'business_profession':r'income\s+from\s+business\s*(?:or|and|/)\s*profession|business\s+(?:or\s+profession\s+)?income',
 'capital_gains':r'income\s+from\s+capital\s+gains?|capital\s+gains?',
 'other_sources':r'income\s+from\s+other\s+sources|other\s+sources\s+income',
 'gross_total_income':r'gross\s+total\s+income',
 'deductions':r'(?:total\s+)?deductions?(?:\s+under\s+chapter\s+vi[ -]?a)?|chapter\s+vi[ -]?a\s+deductions?',
 'total_income':r'total\s+(?:taxable\s+)?income|taxable\s+total\s+income',
 'agricultural_income':r'(?:net\s+)?agricultur(?:al|e)\s+income|income\s+from\s+agriculture',
 'exempt_income':r'(?:other\s+)?exempt(?:ed)?\s+income|income\s+exempt\s+from\s+tax',
}
NUMBER=re.compile(r'(?<![A-Za-z\d])(-?\d[\d,]*(?:\.\d{1,2})?)(?![A-Za-z\d])')

def canonical_year(value):
    m=re.search(r'\b(20\d{2})\s*[-/]\s*(\d{2,4})\b',str(value))
    return m[1]+'-'+m[2][-2:] if m else str(value).strip()

def extract_income(text,page_texts=None,page_offset=0):
    pages=page_texts or [text];values={};evidence={};metadata={};warnings=[]
    full='\n'.join(pages)
    for key,pattern in [('assessment_year',r'(?:assessment|asst|a\.y\.?|ay)\s*(?:year|yr)?\s*[:.\-]?\s*(20\d{2}\s*[-/]\s*\d{2,4})'),('financial_year',r'(?:financial|previous)\s*year\s*[:.\-]?\s*(20\d{2}\s*[-/]?\s*(?:20)?\d{2})')]:
        m=re.search(pattern,full,re.I)
        if m:metadata[key]=canonical_year(m[1])
    p=re.search(r'\bPAN\s*[:.-]?\s*([A-Z]{5}\d{4}[A-Z])\b',full,re.I)
    if p:metadata['pan']=p[1].upper()
    n=re.search(r'\bName\s*(?:[:|.-]\s*|\n\s*)([A-Z][A-Z .\'&-]{2,})',full,re.I)
    if n:metadata['name']=re.sub(r'\s+',' ',n[1]).strip(' .:-').title()
    aaddr=re.search(r'\bAddress\s*(?:[:|.-]\s*|\n\s*)(.+?)(?=\n\s*(?:Status|Form Number|PAN|Assessment Year|Date of filing)\b|$)',full,re.I|re.S)
    if aaddr:metadata['address']=re.sub(r'\s+',' ',aaddr[1]).strip(' .:-')[:240]
    a=re.search(r'acknowledge?ment\s*(?:number|no\.?)?\s*[:.-]?\s*(\d{10,18})',full,re.I)
    if a:metadata['acknowledgement']=a[1]
    d=re.search(r'(?:date\s+of\s+(?:filing|e.filing)|filed\s+on|acknowledg.*?dated)\s*[:.-]?\s*(\d{1,2}[./-]\d{1,2}[./-]20\d{2})',full,re.I)
    if d:metadata['filing_date']=d[1]
    else:
        dated=re.search(r'date\s+of\s+(?:filing|e.filing)\s*[:.-]?\s*(\d{1,2}[- /][A-Za-z]{3,9}[- /]20\d{2})',full,re.I)
        if dated:
            import datetime
            for fmt in ('%d-%b-%Y','%d-%B-%Y','%d %b %Y','%d %B %Y'):
                try:metadata['filing_date']=datetime.datetime.strptime(dated[1],fmt).strftime('%d-%m-%Y');break
                except ValueError:pass
    for page_index,page in enumerate(pages,page_offset+1):
        lines=[x.strip() for x in page.splitlines() if x.strip()]
        summary=True
        for i,line in enumerate(lines):
            # Subsequent salary/capital/other-sources detail totals are not the
            # computation's global Total Income. Main summary values win.
            for key,label in LABELS.items():
                if key in values:continue
                match=re.match(r'^(?:\d+[.)]?\s+)?(?:less\s*[:.-]?\s*)?(?:'+label+r')\b',line,re.I)
                if not match:continue
                tail=line[match.end():].strip(' :|=-')
                candidates=NUMBER.findall(tail)
                source_lines=[line]
                if not candidates:
                    following=lines[i+1:i+4]
                    for n,nextline in enumerate(following):
                        if re.fullmatch(r'\d{1,2}[A-Za-z]',nextline):source_lines.append(nextline);continue
                        if re.fullmatch(r'\d{1,2}',nextline) and n+1<len(following) and NUMBER.fullmatch(following[n+1]):source_lines.append(nextline);continue
                        if re.fullmatch(r'(?:Rs\.?|INR|₹)?\s*\(?-?[\d,]+(?:\.\d{1,2})?\)?',nextline,re.I):
                            candidates=NUMBER.findall(nextline);source_lines.append(nextline)
                        break
                if not candidates:continue
                raw=candidates[-1]
                try:amount=Decimal(raw.replace(',',''))
                except Exception:continue
                if '(' in tail and ')' in tail:amount=-abs(amount)
                values[key]=float(amount);evidence[key]=dict(page=page_index,line=i+1,label=line,text='\n'.join(source_lines),value=str(amount))
    # The independent unrounded total remains evidence; never overwrite it with
    # rounding-off, deductions, tax payable or a later sub-schedule total.
    roundoff=re.search(r'rounding\s+off\s+u/s\s*288A\s*[:.-]?\s*([\d,]+)',full,re.I)
    if roundoff:metadata['rounded_total_income']=float(roundoff[1].replace(',',''))
    return dict(income=values,income_evidence=evidence,income_metadata=metadata,year=metadata.get('assessment_year',''),warnings=warnings)

def tax_sections(pages):
    sections=[]
    for index,text in enumerate(pages,1):
        is_itr=bool(re.search(r'indian\s+income\s+tax\s+return\s+acknowledg|\bitr[- ]?v\b',text,re.I))
        is_comp=bool(re.search(r'computation\s+of\s+(?:total\s+)?income',text,re.I))
        kind='ITR' if is_itr else 'Computation' if is_comp else ''
        if kind:sections.append(dict(kind=kind,pages=[index],page_texts=[text]))
        elif sections:sections[-1]['pages'].append(index);sections[-1]['page_texts'].append(text)
    for section in sections:
        section['text']='\n'.join(section['page_texts']);section.update(extract_income(section['text'],section['page_texts'],section['pages'][0]-1))
    return sections

def reconciliation_proposal(case,person_id,year):
    year=canonical_year(year);records=[r for r in case.incomes if r['person_id']==person_id and canonical_year(r.get('year',''))==year]
    itr=[r for r in records if r['document_type']=='ITR'];included=[r for r in itr if r.get('include')];itr=included or itr;comp=[r for r in records if r['document_type']=='Computation']
    sources={};conflicts=[]
    for key in ('total_income','agricultural_income','exempt_income'):
        options=[(r['id'],r['document_type'],r['values'][key]) for r in records if key in r['values']]
        sources[key]=options
        if len({Decimal(str(o[2])) for o in options})>1:conflicts.append(key)
    return dict(person_id=person_id,year=year,sources=sources,conflicts=conflicts,itr_ids=[r['id'] for r in itr],computation_ids=[r['id'] for r in comp],pair_unique=len(itr)==1 and len(comp)==1)

def confirm_reconciliation(case,person_id,year,values,source_ids,include_agriculture=False,include_other_exempt=False,no_overlap=False):
    from asset_model import money
    from document_records import fingerprint
    year=canonical_year(year);proposal=reconciliation_proposal(case,person_id,year)
    if len(proposal['itr_ids'])!=1:raise ValueError('Select a single reviewed ITR for this person and assessment year.')
    if (include_agriculture or include_other_exempt) and not no_overlap:raise ValueError('Confirm additional income is not already included in taxable income and exempt categories do not overlap.')
    if values.get('total_income') in ('',None):raise ValueError('Review the taxable / ITR total income before confirming.')
    selected={k:None if v in ('',None) else float(money(v)) for k,v in values.items()}
    if include_agriculture and selected.get('agricultural_income') is None:raise ValueError('Agricultural income is unknown. Enter a reviewed value or leave it excluded.')
    if include_other_exempt and selected.get('exempt_income') is None:raise ValueError('Other exempt income is unknown. Enter a reviewed value or leave it excluded.')
    record_ids={r['id'] for r in case.incomes if r['person_id']==person_id and canonical_year(r.get('year',''))==year}
    for key,record_id in source_ids.items():
        if record_id and record_id not in record_ids:raise ValueError('Income source is not linked to this person and year.')
    source_ids=copy.deepcopy(source_ids)
    for key,record_id in list(source_ids.items()):
        original=next((r for r in case.incomes if r['id']==record_id),None)
        if original and (key not in original['values'] or selected.get(key) is None or money(original['values'][key])!=money(selected[key])):source_ids[key]=''
    snapshot={r['id']:fingerprint(r) for r in case.incomes if r['id'] in record_ids}
    result=dict(person_id=person_id,year=year,values=selected,source_ids=source_ids,include_agriculture=bool(include_agriculture),include_other_exempt=bool(include_other_exempt),no_overlap_confirmed=bool(no_overlap),source_fingerprints=snapshot,reviewed=True)
    total=Decimal(str(selected['total_income']))
    if include_agriculture:total+=Decimal(str(selected['agricultural_income']))
    if include_other_exempt:total+=Decimal(str(selected['exempt_income']))
    result['report_total']=float(total);case.income_reviews[person_id+'|'+year]=result;return result
