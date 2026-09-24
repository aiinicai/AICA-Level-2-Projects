"""Conservative annual restated statement extraction from text-based RHP PDFs."""
import io
import re
import time
import logging
from datetime import date

# pypdf logs a "Rotated text discovered" warning once per rotated-text page.
# Large RHPs routinely have dozens of such pages (landscape balance-sheet
# annexures, watermarks, signature stamps), which used to flood the console
# and made the app look stuck. The warning is informational only — pypdf
# still returns whatever text it can — so we drop it to WARNING+ only,
# not stdout noise, without hiding real parsing errors.
logging.getLogger('pypdf').setLevel(logging.ERROR)

# Metrics that must be checked before we allow the scanner to stop early.
# The previous version only checked cash-flow/P&L metrics here, so once it
# found revenue/PAT/CFO/capex/inventory it stopped scanning — even if the
# balance-sheet page (current assets, current liabilities, receivables,
# payables) hadn't been reached yet. That is the direct cause of "Current
# assets / Current liabilities: Not disclosed / not retrieved" even though
# the figures exist later in the same document.
REQUIRED_BEFORE_STOP = ['cfo', 'capex', 'inventory', 'revenue', 'pat',
                         'current_assets', 'current_liabilities',
                         'receivables', 'payables']

def plain(value):
    return re.sub(r'[^a-z0-9]', '', re.sub(r'\b(limited|ltd|private|pvt)\b','',value.lower()))

def number(value):
    value=value.strip().replace(',','').replace('−','-')
    if value in ('-','–','—'): return 0.
    if re.fullmatch(r'\(?-?\d+(?:\.\d+)?\)?',value):
        return -float(value[1:-1]) if value.startswith('(') else float(value)

def parse_page(text, page, url):
    lines=text.splitlines()
    top=' '.join(lines[:14])
    if not re.search('restated',top,re.I) or not re.search('March|31[./-]03',top,re.I): return []
    if re.search('June|September|December|quarter|six.month|nine.month',top,re.I): return []
    unit=.01 if re.search('in lakhs?|in lacs?',top,re.I) else .1 if re.search('in millions?',top,re.I) else 1 if re.search('in crores?',top,re.I) else None
    if unit is None: return []
    kind='cash' if re.search(r'(statement.*cash\s*flow|cash\s*flow.*statement)',top,re.I) else 'balance' if re.search('assets and liabilities|balance sheet',top,re.I) else 'profit' if re.search('profit and loss|statement of income',top,re.I) else None
    if not kind: return []
    cols=[]
    for ln,line in enumerate(lines[:14]):
        for m in re.finditer(r'\b20\d{2}\b',line):
            year=int(m[0])
            if m.start()>35 and year<=date.today().year and not any(c[0]==year for c in cols): cols.append((year,m.start()+2,ln))
    cols.sort(key=lambda c:c[1])
    if len(cols)!=3 or sorted(c[0] for c in cols)!=list(range(min(c[0] for c in cols),max(c[0] for c in cols)+1)): return []
    gap=min(cols[i+1][1]-cols[i][1] for i in range(len(cols)-1))
    if gap<8:return []
    left=cols[0][1]-gap*.6
    rows=[]
    for line in lines[max(c[2] for c in cols)+1:]:
        label=line[:max(0,int(left))].strip()
        label=re.sub(r'^(?:\([a-zivx0-9]+\)|[a-zivx0-9]+[.)])\s*','',label,flags=re.I).strip()
        values=[None]*len(cols)
        for m in re.finditer(r'\(?-?\d[\d,]*\.\d+\)?|\(?\d[\d,]*\)?|(?<!\S)[—–-](?!\S)',line):
            center=(m.start()+m.end())/2
            if center<left:continue
            ix=min(range(len(cols)),key=lambda i:abs(center-cols[i][1]))
            if abs(center-cols[ix][1])<gap*.58:
                if values[ix] is not None: values[ix]=None;break
                values[ix]=number(m[0])
        rows.append((label,values))
    basis='Consolidated' if re.search('consolidated',top,re.I) else 'Standalone' if re.search('standalone',top,re.I) else 'Company restated'
    evidence=[]
    def add(metric,row,method='Reported in RHP'):
        if row is None or any(v is None for v in row[1]):return
        for (year,_,_),v in zip(cols,row[1]):
            evidence.append(dict(metric=metric,year=year,value=round(v*unit,6),page=page,source=url+'#page='+str(page),label=row[0],units='INR crore',original_units={.01:'INR lakh',.1:'INR million',1:'INR crore'}[unit],method=method,basis=basis,primary=True))
    def find(pattern):return next((r for r in rows if re.search(pattern,r[0],re.I) and all(v is not None for v in r[1])),None)
    if kind=='cash':
        for metric,pattern in [('cfo',r'^net cash.*operating activit'),('investing',r'^net cash.*investing activit'),('financing',r'^net cash.*financing activit')]:add(metric,find(pattern))
        parts=[r for r in rows if re.search(r'^(?:purchase|acquisition|payment).*(?:property|plant|equipment|fixed assets|intangible)',r[0],re.I) and not re.search('advance|subsidiar|investment',r[0],re.I) and all(v is not None for v in r[1])]
        if parts:add('capex',('Cash payments for fixed and intangible assets',[sum(abs(r[1][i]) for r in parts) for i in range(3)]),'Derived: sum of reported asset-purchase cash payments')
    if kind=='profit':
        for metric,pattern in [('revenue',r'^revenue from operations'),('pat',r'^profit (?:for the year|after tax)'),('pbt',r'^profit before tax'),('finance_cost',r'^finance costs?'),('depreciation',r'^depreciation'),('other_income',r'^other income'),('operating_cost',r'^operating cost'),('inventory_change',r'^changes? in inventor')]:add(metric,find(pattern))
    if kind=='balance':
        for metric,pattern in [('inventory',r'^inventories'),('receivables',r'^trade receivables'),('payables',r'^trade payables'),('cash',r'^cash and cash equivalents'),('assets',r'^total assets'),('equity',r'^total equity$'),('current_assets',r'^total current assets'),('current_liabilities',r'^total current liabilities')]:add(metric,find(pattern))
        if not any(e['metric']=='payables' for e in evidence):
            parts=[r for r in rows if re.search('total outstanding dues',r[0],re.I) and all(v is not None for v in r[1])]
            if len(parts)==2:add('payables',('MSME and other trade payables',[sum(r[1][i] for r in parts) for i in range(3)]),'Derived: two trade-payable categories')
        for label,metric in [('current assets','current_assets'),('current liabilities','current_liabilities')]:
            if any(e['metric']==metric for e in evidence):continue
            start=next((i for i,r in enumerate(rows) if r[0].lower()==label),None)
            if start is None:continue
            end_label='total assets' if metric=='current_assets' else 'total equity and liabilities'
            stop=next((i for i in range(start+1,len(rows)) if rows[i][0].lower()==end_label),None)
            if stop is None:continue
            section=[r for r in rows[start+1:stop] if any(v is not None for v in r[1])]
            if len(section)>=3 and all(all(v is not None for v in r[1]) for r in section):
                add(metric,('Sum of complete '+label+' section',[sum(r[1][i] for r in section) for i in range(3)]),'Derived: sum of complete current section')
    return evidence

def parse_balance_plain(text,page,url):
    """Fallback for restated balance-sheet pages where parse_page() found
    nothing. parse_page() relies on x-positions from layout-mode extraction
    to line numbers up under the right fiscal year; pypdf's own "Rotated text
    discovered" warning (emitted for exactly these pages — landscape
    annexures, rotated stamps/watermarks) means those x-positions can be
    wrong or missing, so the strict column parser correctly refuses to guess.

    This fallback instead flattens the page to one line and requires a
    metric label to be followed immediately by exactly three numeric tokens,
    in the same order as the three fiscal years found in the heading. It
    doesn't need reliable column positions — only that pypdf's text stream
    keeps label-then-values in reading order, which holds even when layout
    is degraded. It is intentionally limited to a fixed set of exact labels
    (no section-sum reconstruction) to avoid guessing on a garbled page.
    """
    flat=re.sub(r'\s+',' ',text)
    top=flat[:900]
    if not re.search('restated',top,re.I):return []
    if re.search('June|September|December|quarter|six.month|nine.month',top,re.I):return []
    unit=.01 if re.search('in lakhs?|in lacs?',top,re.I) else .1 if re.search('in millions?',top,re.I) else 1 if re.search('in crores?',top,re.I) else None
    if unit is None:return []
    years=[]
    for m in re.finditer(r'\b20\d{2}\b',top):
        year=int(m[0])
        if year<=date.today().year and year not in years:years.append(year)
        if len(years)==3:break
    if len(years)!=3 or sorted(years)!=list(range(min(years),max(years)+1)):return []
    basis='Consolidated' if re.search('consolidated',top,re.I) else 'Standalone' if re.search('standalone',top,re.I) else 'Company restated'
    num_tok=r'\(?-?\d[\d,]*(?:\.\d+)?\)?|(?<!\S)[—–-](?!\S)'
    nums=r'\s+'.join('('+num_tok+')' for _ in range(3))
    evidence=[]
    def add(metric,pattern):
        matches=list(re.finditer(pattern+r'\s+(?:\([a-h]\)\s*)?'+nums+r'(?!\s*(?:'+num_tok+'))',flat,re.I))
        if len(matches)!=1:return
        values=[number(x) for x in matches[0].groups()]
        if any(v is None for v in values):return
        for year,value in zip(years,values):
            evidence.append(dict(metric=metric,year=year,value=round(value*unit,6),page=page,source=url+'#page='+str(page),label=matches[0][0][:60].strip(),units='INR crore',original_units={.01:'INR lakh',.1:'INR million',1:'INR crore'}[unit],method='Reported in RHP; plain-text fallback for rotated/degraded layout',basis=basis,primary=True))
    for metric,pattern in [('inventory',r'\bInventories\b'),('receivables',r'\bTrade Receivables\b'),
                           ('payables',r'\bTrade Payables\b'),('cash',r'\bCash and Cash Equivalents\b'),
                           ('assets',r'\bTotal Assets\b'),('equity',r'\bTotal Equity\b(?! and)'),
                           ('current_assets',r'\bTotal Current Assets\b'),
                           ('current_liabilities',r'\bTotal Current Liabilities\b')]:
        add(metric,pattern)
    return evidence

def parse_valuation_and_concentration(text, url):
    """
    EXPERIMENTAL. Best-effort extraction of the IPO's own P/E, a stated
    peer/industry P/E, and customer/supplier revenue concentration, from
    the free-text "Basis for Issue Price" and "Risk Factors" sections of
    an RHP. Unlike parse_page()/parse_balance_plain() above — which only
    ever accept strictly column-anchored annual-statement tables and
    refuse anything ambiguous — this reads prose and table cells with
    regular expressions, which is inherently less reliable: RHP wording
    and table layout vary company to company, and PDF text extraction
    can scramble the reading order of numbers in a table.

    To keep false positives rare, every pattern below only returns a
    value when it matches EXACTLY ONCE (after de-duplicating identical
    numbers) across the whole document. This matters most for P/E: a
    peer-comparison table lists several *individual* companies' own P/E
    figures next to each other, and a looser regex could easily grab one
    of those instead of the actual "industry"/"average" summary figure —
    so peer_pe only fires on an explicitly labelled summary line, never
    by picking one row out of a peer table. Two or more distinct matches
    for any pattern means that value is ambiguous from text alone, so
    nothing is returned for it — deliberately leaving it "Pending" rather
    than risk feeding a wrong number into the score.

    Always spot-check anything pulled this way against the RHP itself
    before relying on it for a real decision — see the 'method' string on
    each evidence item, which is tagged "experimental" for this reason.
    """
    flat = re.sub(r'\s+', ' ', text)

    def unique_number(pattern, lo, hi):
        found = set()
        for m in re.finditer(pattern, flat, re.I):
            v = number(m.group(1).replace(',', ''))
            if v is not None and lo <= v <= hi:
                found.add(round(v, 2))
        return found.pop() if len(found) == 1 else None

    evidence = []

    def add(metric, value, label, section):
        evidence.append(dict(
            metric=metric, value=value, source=url, label=label,
            method=f'Prospectus text search (experimental) \u2014 {section}',
            confidence='experimental',
        ))

    pe = unique_number(r'P/?E\s+ratio[^.\n]{0,60}?Cap\s+Price[^0-9]{0,20}(\d{1,3}(?:\.\d{1,2})?)', .1, 500)
    if pe is not None:
        add('pe', pe, 'P/E at Cap Price', 'Basis for Issue Price section')

    peer_pe = unique_number(r'(?:Industry|Average|Peer\s+Group\s+Average)\s+P/?E[^0-9]{0,30}(\d{1,3}(?:\.\d{1,2})?)', .1, 500)
    if peer_pe is not None:
        add('peer_pe', peer_pe, 'Industry / average peer P/E', 'peer comparison section')

    top_cust = unique_number(r'top\s+(?:five|5|ten|10|twenty|20)\s+customers?[^%]{0,120}?(\d{1,3}(?:\.\d{1,2})?)\s?%', 0, 100)
    if top_cust is not None:
        add('top_cust', top_cust, 'Top-customer revenue concentration', 'risk factors section')

    top_supp = unique_number(r'top\s+(?:five|5|ten|10|twenty|20)\s+suppliers?[^%]{0,120}?(\d{1,3}(?:\.\d{1,2})?)\s?%', 0, 100)
    if top_supp is not None:
        add('top_supp', top_supp, 'Top-supplier purchase concentration', 'risk factors section')

    return evidence


def parse_pdf(content,name,url):
    from pypdf import PdfReader
    reader=PdfReader(io.BytesIO(content))
    if reader.is_encrypted:raise ValueError('Encrypted prospectus requires manual review')
    identity=' '.join((p.extract_text() or '') for p in reader.pages[:3])
    if plain(name) not in plain(identity):raise ValueError('Prospectus company identity could not be confirmed')
    evidence=[];basis=None;start=time.monotonic();relevant_pages=[]
    # Budget generously — annual restated statements plus their balance-sheet
    # pages can sit 100+ pages apart in a large RHP, and scanning must not
    # stop before reaching all of them.
    for i,page in enumerate(reader.pages[:1200]):
        if time.monotonic()-start>180:break
        text=page.extract_text(extraction_mode='layout') or ''
        ev=parse_page(text,i+1,url)
        plain_text=None
        if not ev and re.search('restated',text[:1600],re.I) and re.search('June',text[:1600],re.I):
            plain_text=page.extract_text() or ''
            ev=parse_mixed_page(plain_text,i+1,url)
        if not ev and re.search('restated',text[:1600],re.I) and re.search('assets and liabilities|balance sheet',text[:1600],re.I):
            # Layout-mode column detection failed — very often because pypdf
            # flagged this exact page as containing rotated text, which
            # scrambles the x-positions parse_page() relies on. Fall back to
            # plain extraction with a looser, order-based row parser instead
            # of giving up on the balance sheet entirely.
            plain_text=plain_text if plain_text is not None else (page.extract_text() or '')
            ev=parse_balance_plain(plain_text,i+1,url)
        if not ev:
            # Not a financial-statement page. Cheap keyword pre-check on the
            # layout-mode text already extracted above (no extra pypdf call)
            # decides whether this page is worth a second, plain-mode
            # extraction (better suited to prose) for the experimental
            # valuation/concentration search below — keeps that search from
            # adding real cost to every page of a 1000+ page RHP.
            if re.search(r'P\s*/?\s*E\s*ratio|Price\s*/?\s*Earnings|top\s+(?:five|5|ten|10|twenty|20)\s+(?:customers?|suppliers?)',text,re.I):
                relevant_pages.append(plain_text if plain_text is not None else (page.extract_text() or ''))
            continue
        this_basis=ev[0]['basis']
        if basis is not None and this_basis!=basis:continue
        basis=this_basis
        existing={(e['metric'],e['year']) for e in evidence}
        evidence.extend(e for e in ev if (e['metric'],e['year']) not in existing)
        if all(any(e['metric']==k for e in evidence) for k in REQUIRED_BEFORE_STOP):break
    if not any(e['metric']=='cfo' for e in evidence):raise ValueError('Annual net operating cash flow could not be extracted reliably from this PDF layout')
    scalar_evidence=parse_valuation_and_concentration('\n'.join(relevant_pages),url) if relevant_pages else []
    return evidence,scalar_evidence

def parse_mixed_page(text,page,url):
    """Verified four-column layout: June stub followed by three March year ends.

    Require explicit dates, decimal-valued rows, and an annual statement heading.
    Drop the interim column, never annualise it. Unknown layouts return no data.
    """
    text=re.sub(r'\s+',' ',text)
    top=text[:650]
    if not re.search('restated consolidated statement',top,re.I):return []
    dates=re.findall(r'\b(June|March)\s+(?:30|31),?\s*(20\d{2})',top,re.I)[:4]
    if len(dates)!=4 or [m.lower() for m,y in dates]!=['june','march','march','march']:return []
    years=[int(y) for m,y in dates[1:]]
    if years!=[years[0],years[0]-1,years[0]-2] or date(years[0],3,31)>date.today():return []
    scale=.1 if re.search('in million',top,re.I) else .01 if re.search('in lakhs?',top,re.I) else 1 if re.search('in crore',top,re.I) else None
    if scale is None:return []
    kind='cash' if re.search('statement of cash flow',top,re.I) else 'balance' if re.search('assets and liabilities',top,re.I) else 'profit' if re.search('profit and loss',top,re.I) else None
    if not kind:return []
    decimal=r'(\(?-?\d[\d,]*\.\d+\)?|[—–-])'
    nums=r'\s+'.join([decimal]*4)
    evidence=[]
    def add(metric,pattern,absolute=False):
        matches=list(re.finditer(pattern+r'\s+(?:\([a-c]\s*\)\s*)?'+nums+r'(?!\s+\(?\d[\d,]*\.\d)',text,re.I))
        if len(matches)!=1:return
        match=matches[0];values=[number(x) for x in match.groups()[-4:]][1:]
        if any(v is None for v in values):return
        for year,value in zip(years,values):
            evidence.append(dict(metric=metric,year=year,value=round((abs(value) if absolute else value)*scale,6),page=page,source=url+'#page='+str(page),label=match[0].split(match.groups()[-4])[0].strip(),units='INR crore',original_units='INR million' if scale==.1 else 'INR lakh' if scale==.01 else 'INR crore',method='Reported in RHP; June stub excluded',basis='Consolidated',primary=True))
    if kind=='balance':
        for metric,pattern in [('inventory',r'\bInventories'),('receivables',r'\bTrade Receivables'),('current_assets',r'\bTotal Current Assets'),('current_liabilities',r'\bTotal Current Liabilities'),('assets',r'\bTOTAL ASSETS'),('equity',r'\bTotal Equity(?! and)'),('cash',r'\bCash & Cash Equivalent')]:add(metric,pattern)
        add('payables_msme',r'Outstanding Dues of Micro Enterprises and Small Enterprises \(MESE\)')
        add('payables_other',r'Outstanding Dues of Creditors Other than MESE')
        for year in years:
            parts=[e for e in evidence if e['year']==year and e['metric'] in ['payables_msme','payables_other']]
            if len(parts)==2:evidence.append({**parts[0],'metric':'payables','value':round(sum(e['value'] for e in parts),6),'method':'Derived: MSME + other trade payables'})
    if kind=='profit':
        for metric,pattern in [('revenue',r'\bRevenue from Operations'),('other_income',r'\bOther Income'),('pbt',r'\bProfit Before Tax(?:\s*\([^)]*\))?'),('pat',r'\bProfit (?:After Tax(?: for the period)?|for the period)(?:\s*\([^)]*\))?'),('finance_cost',r'\bFinance Costs'),('depreciation',r'\bDepreciation and Amorti[sz]ation(?: Expenses)?'),('material_cost',r'\bCost of Materials Consumed'),('purchases',r'\bPurchase of Trading goods'),('inventory_change',r'\bChanges in inventories of Finished Goods & Stock in Trade')]:add(metric,pattern)
    if kind=='cash':
        for metric,pattern in [('cfo',r'\bNet Cash Flow from Operating Activities'),('investing',r'\bNet Cash used in Investing Activities'),('financing',r'\bNet Cash used in Financing Activities')]:add(metric,pattern)
        add('capex',r'\bPurchase of Property, Plant & Equipment, Intangible Assets & CWIP',True)
    return evidence
