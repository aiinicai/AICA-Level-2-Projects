"""Annual financial research with multiple sources and field-level evidence."""
import re
import html
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone, date
from urllib.parse import urljoin, urlsplit
from . import network, db, scoring
from .scrapers.base import parse_html_tables, number_text

VERSION=4
INDEX={}
INDEX_AT=0
KNOWN_DOCUMENTS={
 'veegaland-developers':'https://www.veegaland.com/wp-content/uploads/2026/08/VA20260830_Veegaland-RHP_Final.pdf',
 'raksan-transformers':'https://hemadmin.hemsecurities.com/images/Files/offer/3088.pdf',
 'manika-plastech':'https://manikaplastech.com/wp-content/uploads/2026/09/RHP.pdf',
 'spectraa-technology-solutions':'https://www.spectraa.com/wp-content/uploads/2026/09/Red-Herring-Prosppectus.pdf',
}
MONTHS={'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'sept':9,'oct':10,'nov':11,'dec':12}
MAPPING={
 'revenue from ops':'revenue','revenue from operations':'revenue','revenue':'revenue',
 'profit after tax':'pat','pat':'pat','ebitda':'ebitda','profit before tax':'pbt','other income':'other_income',
 'cf from operating activities':'cfo','cash flow from operating activities':'cfo',
 'cf from investing activities':'investing','cash flow from investing activities':'investing',
 'cf from financing activities':'financing','cash flow from financing activities':'financing',
 'finance costs':'finance_cost','finance cost':'finance_cost','depreciation':'depreciation',
 'depreciation and amortisation':'depreciation','inventories':'inventory','inventory':'inventory',
 'trade receivables':'receivables','trade payables':'payables',
 'total current assets':'current_assets','total current liabilities':'current_liabilities',
 'current assets':'current_assets','current liabilities':'current_liabilities',
 'total current asset':'current_assets','total current liability':'current_liabilities',
 'operating cost':'operating_cost','changes in inventories':'inventory_change','cost of revenue':'cost_of_revenue',
 'total assets':'assets','assets':'assets','total equity':'equity','net worth':'equity',
 'total borrowings':'debt','total borrowing':'debt','total debt':'debt',
 'cash & bank bal':'cash','cash and cash equivalents':'cash','debt to equity':'de',
 'roe (%)':'roe','roce (%)':'roce','purchase of fixed assets':'capex',
 'purchase of property, plant and equipment':'capex',
 'roe':'roe','roce':'roce','debt/equity':'de','reserves and surplus':'reserves',
 'net working capital':'net_working_capital','working capital':'net_working_capital',
 'cash flow from operations':'cfo','net cash from operating activities':'cfo',
 'net cash used in investing activities':'investing','net cash from investing activities':'investing',
 'net cash used in financing activities':'financing','net cash from financing activities':'financing',
 # Post-issue P/E only — deliberately NOT mapping any "pre issue"/"pre ipo"
 # P/E variant, since a per-row map can only keep one value per metric and
 # the post-issue (asking-price) P/E is what the scoring model compares
 # against peers. See scoring.valuation_score().
 'p/e post ipo':'pe','p/e (post ipo)':'pe','post ipo p/e':'pe','post-issue p/e':'pe',
 'p/e post-issue':'pe','p/e (post-issue)':'pe','p/e ratio (post issue)':'pe',
}

def names_match(a,b):
    return db.names_match(a,b)

def identity(text,name):
    headings=re.findall(r'<h[12]\b[^>]*>(.*?)</h[12]>',text,re.S|re.I)
    for heading in headings:
        heading=re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>','',heading))).strip()
        heading=re.sub(r'\s+IPO\s+Financial\s+Report.*$','',heading,flags=re.I)
        heading=re.sub(r'\s+IPO\s+Details.*$','',heading,flags=re.I)
        if db.slugify(heading)==db.slugify(name) or names_match(heading,name):return
    raise ValueError('Company identity does not match the statement page')

def annual_year(label):
    label=label.strip()
    m=re.fullmatch(r'Mar-(\d{2})|FY\s*(\d{2})|FY\s*(20\d{2})',label,re.I)
    if m:
        year=int(next(g for g in m.groups() if g));year=year+2000 if year<100 else year
        return year if date(year,3,31)<=date.today() else None
    m=re.fullmatch(r'(\d{1,2})\s+([A-Za-z]{3,})[,]?\s+(20\d{2})',label)
    if m:
        mon=MONTHS.get(m.group(2)[:3].lower())
        if mon:
            try:d=date(int(m.group(3)),mon,int(m.group(1)))
            except ValueError:return None
            return d.year if d<=date.today() else None
    m=re.fullmatch(r'([A-Za-z]{3,})\s+(\d{1,2})[,]?\s+(20\d{2})',label)
    if m:
        mon=MONTHS.get(m.group(1)[:3].lower())
        if mon:
            try:d=date(int(m.group(3)),mon,int(m.group(2)))
            except ValueError:return None
            return d.year if d<=date.today() else None
    return None

def parse_statements(text,name,url,platform=False):
    identity(text,name)
    if not re.search(r'(?:Rs\.?|₹)\s*(?:in\s*)?(?:Cr\b|crores?\b)',html.unescape(re.sub('<[^>]+>',' ',text)),re.I):raise ValueError('INR crore statement units could not be confirmed')
    series,evidence={},[]
    for table in parse_html_tables(text):
        header=next((r for r in table if sum(annual_year(c) is not None for c in r)>=2),None)
        if not header:continue
        cols=[(i,annual_year(c)) for i,c in enumerate(header) if annual_year(c) is not None]
        for row in table:
            label=re.sub(r'\s+',' ',row[0]).strip() if row else ''
            label=re.sub(r'\s*Annualised basis.*$','',label,flags=re.I).strip()
            metric=MAPPING.get(label.lower())
            if not metric:continue
            for i,year in cols:
                if i>=len(row):continue
                raw=row[i].strip()
                if re.search(r'\d\s+\d',raw):continue
                value=0.0 if raw in ('-','—','Nil','nil') else number_text(raw)
                if value is None:continue
                series.setdefault(year,{})[metric]=abs(value) if metric=='capex' else value
                evidence.append(dict(metric=metric,year=year,value=series[year][metric],source=url,label=label,units='ratio' if metric=='de' else '%' if metric in ('roe','roce') else 'INR crore',method='Secondary annual statement',primary=False,basis='Source annual statement'))
    if not evidence:raise ValueError('No supported annual financial rows found')
    result={'series':series,'evidence':evidence,'url':url,'level':'Secondary — prospectus cross-check required','at':db.now_iso(),'version':VERSION}
    derive(result)
    return result

def derive(research):
    series={int(y):dict(r) for y,r in research['series'].items()};evidence=research['evidence']
    def put(year,metric,value,formula,inputs):
        series[year][metric]=round(value,6)
        parents=[next((e for e in reversed(evidence) if e['metric']==k and int(e['year'])==y),None) for y,k in inputs]
        source=next((e['source'] for e in parents if e),'')
        evidence.append(dict(metric=metric,year=year,value=round(value,6),source=source,method='Derived: '+formula,inputs=[{'metric':e['metric'],'year':e['year'],'value':e['value'],'source':e['source']} for e in parents if e],units='days' if metric.endswith('days') or metric=='ccc' else 'ratio' if metric=='de' else 'INR crore',primary=all(e and e.get('primary') for e in parents)))
    for year,r in series.items():
        prev=series.get(year-1,{})
        ebitda_inputs=['pbt','finance_cost','depreciation','other_income']
        primary_components=all(next((e.get('primary',False) for e in reversed(evidence) if int(e['year'])==year and e['metric']==k),False) for k in ebitda_inputs)
        if ('ebitda' not in r or primary_components) and all(k in r for k in ebitda_inputs):put(year,'ebitda',r['pbt']+r['finance_cost']+r['depreciation']-r['other_income'],'PBT + finance cost + depreciation − other income',[(year,k) for k in ebitda_inputs])
        if all(k in r for k in ['cfo','capex']):put(year,'fcf',r['cfo']-r['capex'],'operating cash flow − asset-purchase cash payments',[(year,k) for k in ['cfo','capex']])
        # Last resort only: if no source (RHP or secondary site) disclosed the
        # actual current-asset / current-liability totals, build a partial
        # figure from whichever components ARE on hand, clearly marked as an
        # estimate rather than left blank. This is a floor, not the true
        # total — it excludes items such as loans/advances, prepayments,
        # short-term borrowings and provisions that aren't separately
        # captured elsewhere in this pipeline.
        partial_assets=['inventory','receivables','cash']
        if 'current_assets' not in r and all(k in r for k in partial_assets):
            put(year,'current_assets',sum(r[k] for k in partial_assets),
                'Estimated: inventory + trade receivables + cash (partial total — excludes loans/advances, prepayments and other current assets not separately disclosed; actual figure will be equal or higher)',
                [(year,k) for k in partial_assets])
        if 'current_liabilities' not in r and 'payables' in r:
            put(year,'current_liabilities',r['payables'],
                'Estimated: trade payables only (partial total — excludes short-term borrowings, provisions and other current liabilities not separately disclosed; actual figure will be equal or higher)',
                [(year,'payables')])
        if 'net_working_capital' not in r and all(k in r for k in ['current_assets','current_liabilities']):put(year,'net_working_capital',r['current_assets']-r['current_liabilities'],'current assets − current liabilities',[(year,k) for k in ['current_assets','current_liabilities']])
        if 'de' not in r and 'debt' in r and r.get('equity',0)>0:put(year,'de',r['debt']/r['equity'],'borrowings / net worth',[(year,k) for k in ['debt','equity']])
        if r.get('revenue',0)>0 and 'receivables' in r and 'receivables' in prev:put(year,'deb_days',(r['receivables']+prev['receivables'])/2/r['revenue']*365,'average receivables / annual revenue × 365',[(year,'receivables'),(year-1,'receivables'),(year,'revenue')])
        cost_inputs=['operating_cost','inventory_change'] if 'operating_cost' in r else ['material_cost','purchases','inventory_change']
        if all(k in r for k in cost_inputs):
            cogs=sum(r[k] for k in cost_inputs)
            if cogs>0:
                for metric,balance in [('inv_days','inventory'),('cred_days','payables')]:
                    if balance in r and balance in prev:put(year,metric,(r[balance]+prev[balance])/2/cogs*365,'average '+balance+' / ('+' + '.join(cost_inputs)+') × 365; cost-of-sales proxy',[(year,balance),(year-1,balance)]+[(year,k) for k in cost_inputs])
                if all(k in r for k in ['inv_days','deb_days','cred_days']):put(year,'ccc',r['inv_days']+r['deb_days']-r['cred_days'],'inventory + debtor − creditor days',[(year,k) for k in ['inv_days','deb_days','cred_days']])
    research.update(series=series,method='Completed annual periods only; financial amounts converted to INR crore. Calculations use matching annual periods. Historical capex comes from cash asset purchases, never IPO objects or net investing outflows.')

def links(text,base):
    for href,label in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',text,re.S|re.I):
        yield urljoin(base,html.unescape(href)),html.unescape(re.sub('<[^>]+>',' ',label)).strip()

def get_platform_index():
    global INDEX,INDEX_AT
    now=datetime.now().timestamp()
    if now-INDEX_AT<900:return INDEX
    found={}
    for page in ['https://www.ipoplatform.com/ipo/mainboard','https://www.ipoplatform.com/ipo/sme','https://www.ipoplatform.com/ipo/upcoming']:
        try:
            response=network.get(page,timeout=20)
            if response.status_code!=200:continue
            for url,label in links(response.text,page):
                m=re.fullmatch(r'/ipo/([^/]+)/(\d+)',urlsplit(url).path)
                if m:found[db.slugify(m[1].replace('-',' '))]=url
        except Exception:continue
    INDEX=found;INDEX_AT=now
    return found

IJ_INDEX={};IJ_INDEX_AT=0
def get_ipoji_index():
    """
    Index of IPOJI.com company pages, keyed by slug — mirrors
    get_chittorgarh_index() below. IPOJI is queried as an additional
    financial-statement source (working capital, cash flow, ratios, etc.)
    to fill gaps left by IPO360/IPOPlatform/Chittorgarh, and its GMP figures
    are used as the first GMP fallback whenever Chittorgarh's most recent
    refresh attempt failed (see source_ok_recently() in app/db.py).

    NOTE: built without live network access to ipoji.com, so these listing
    URLs/link patterns are a best-effort guess based on how comparable IPO
    sites (Chittorgarh, IPOPlatform) structure their listing pages. If IPOJI
    uses different paths, update the `pages` list and/or the path regex
    below — everything downstream (parse_statements) already parses by
    column header text, not by fixed layout, so it needs no other changes.
    """
    global IJ_INDEX,IJ_INDEX_AT
    now=datetime.now().timestamp()
    if now-IJ_INDEX_AT<900:return IJ_INDEX
    found={}
    for page in ['https://ipoji.com/ipo-gmp/','https://ipoji.com/upcoming-ipo/','https://ipoji.com/sme-ipo/']:
        try:
            response=network.get(page,timeout=20)
            if response.status_code!=200:continue
            for url,label in links(response.text,page):
                m=re.fullmatch(r'/([^/]+)-ipo/?',urlsplit(url).path)
                if m and m[1] not in ('upcoming','sme','mainboard'):found[db.slugify(m[1].replace('-',' '))]=urljoin(page,m.group(0))
        except Exception:continue
    IJ_INDEX=found;IJ_INDEX_AT=now
    return found

CG_INDEX={};CG_INDEX_AT=0
def get_chittorgarh_index():
    global CG_INDEX,CG_INDEX_AT
    now=datetime.now().timestamp()
    if now-CG_INDEX_AT<900:return CG_INDEX
    found={}
    for page in ['https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/mainboard/',
                 'https://www.chittorgarh.com/report/ipo-in-india-list-main-board-sme/82/sme/',
                 'https://www.chittorgarh.com/report/upcoming-ipos-drhp-filed/158/mainboard/',
                 'https://www.chittorgarh.com/report/upcoming-ipos-drhp-filed/158/sme/']:
        try:
            response=network.get(page,timeout=20)
            if response.status_code!=200:continue
            for url,label in links(response.text,page):
                m=re.fullmatch(r'/ipo/([^/]+)-ipo/(\d+)/?',urlsplit(url).path)
                if m:found[db.slugify(m[1].replace('-',' '))]=urljoin(page,m.group(0))
        except Exception:continue
    CG_INDEX=found;CG_INDEX_AT=now
    return found

def parse_chittorgarh_kpi(text,url):
    """Chittorgarh's single-year KPI table (ROE/ROCE/Debt-Equity/etc.) has no
    multi-year header, so parse_statements() can't read it — handle it here."""
    evidence=[]
    for table in parse_html_tables(text):
        if not table or len(table)<2:continue
        if (table[0][0] or '').strip().lower()!='kpi':continue
        year=None
        if len(table[0])>1:
            header_cell=table[0][1]
            m=re.search(r'(\d{1,2})\s+([A-Za-z]{3,})[,]?\s+(20\d{2})',header_cell)
            if m:
                mon=MONTHS.get(m.group(2)[:3].lower())
                if mon:
                    try:year=date(int(m.group(3)),mon,int(m.group(1))).year
                    except ValueError:year=None
            if not year:
                m=re.search(r'([A-Za-z]{3,})\s+(\d{1,2})[,]?\s+(20\d{2})',header_cell)
                if m:
                    mon=MONTHS.get(m.group(1)[:3].lower())
                    if mon:
                        try:year=date(int(m.group(3)),mon,int(m.group(2))).year
                        except ValueError:year=None
        if not year:continue
        for row in table[1:]:
            if len(row)<2:continue
            label=re.sub(r'\s+',' ',row[0]).strip()
            metric=MAPPING.get(label.lower())
            if not metric:continue
            value=number_text(row[1].strip())
            if value is None:continue
            evidence.append(dict(metric=metric,year=year,value=value,source=url,label=label,
                units='ratio' if metric in ('de','pe') else '%',method='Secondary annual statement (Chittorgarh KPI)',
                primary=False,basis='Chittorgarh KPI summary'))
    return evidence

def combine(research,incoming):
    series=research['series'];evidence=research['evidence']
    for ev in incoming:
        year=int(ev['year']);metric=ev['metric'];r=series.setdefault(year,{})
        old=r.get(metric)
        prior=next((e for e in reversed(evidence) if int(e['year'])==year and e['metric']==metric),{})
        if old is not None and abs(old-ev['value'])>max(.02,abs(old)*.005):research['conflicts'].append(f"FY{year} {metric}: {old:g} versus {ev['value']:g} ({ev['source']}). Review statement basis and rounding.")
        if old is None or (ev.get('primary') and not prior.get('primary')):
            r[metric]=ev['value'];evidence.append(ev)

def combine_scalars(research,incoming):
    """
    Merge point-in-time (non fiscal-year) evidence — currently just the
    experimental prospectus-text values (pe, peer_pe, top_cust, top_supp)
    — into research['scalars']. Kept entirely separate from combine()/
    series above, which are fiscal-year-indexed and consumed by derive();
    mixing a yearless metric into that structure would break every caller
    that does int(ev['year']).
    """
    scalars=research.setdefault('scalars',{})
    evidence=research.setdefault('scalar_evidence',[])
    for ev in incoming:
        scalars[ev['metric']]=ev['value']
        evidence.append(ev)

def fetch_research(record):
    old=record.get('research') or {}
    if old.get('version')==VERSION and old.get('at') and old.get('series') and not old.get('incomplete'):
        try:
            if (datetime.now(timezone.utc)-datetime.fromisoformat(old['at'])).total_seconds()<86400:return old,True
        except ValueError:pass
    result={'series':{},'evidence':[],'attempts':[],'conflicts':[],'scalars':{},'scalar_evidence':[],'at':db.now_iso(),'version':VERSION,'url':'','level':'Source evidence available'}
    key=db.slugify(record['name']);documents=[]
    def attempt(source,fn):
        try:
            value=fn();result['attempts'].append({'source':source,'message':'Retrieved and parsed'});return value
        except Exception as e:result['attempts'].append({'source':source,'message':str(e)});return None
    slug=re.sub(r'[^a-z0-9]+','-',record['name'].lower().replace('&','and').replace(' ltd',' limited')).strip('-')
    url='https://www.ipo360.in/company/'+slug+'-ipo'
    def secondary():
        response=network.get(url,timeout=22)
        if response.status_code!=200:raise ValueError('HTTP '+str(response.status_code))
        return parse_statements(response.text,record['name'],url)
    data=attempt('IPO360',secondary)
    if data:
        combine(result,[e for e in data['evidence'] if not e['method'].startswith('Derived')]);result['url']=url
    def platform():
        page=get_platform_index().get(key)
        if not page:raise ValueError('Company not found in current IPOPlatform directories')
        m=re.fullmatch(r'/ipo/([^/]+)/(\d+)',urlsplit(page).path)
        url='https://www.ipoplatform.com/ipo/financial-report/'+m[1]+'/'+m[2]
        response=network.get(url,timeout=22)
        if response.status_code!=200:raise ValueError('HTTP '+str(response.status_code))
        parsed=parse_statements(response.text,record['name'],url,True)
        for href,label in links(response.text,url):
            if '.pdf' in href.lower() and re.search(r'\bRHP\b|red herring',label,re.I) and not re.search('DRHP|draft',label,re.I):documents.append(href)
        return parsed
    data=attempt('IPOPlatform',platform)
    if data:
        combine(result,[e for e in data['evidence'] if not e['method'].startswith('Derived')]);result['url']=result['url'] or data['url']
    def chittorgarh_source():
        idx=get_chittorgarh_index()
        page=idx.get(key) or next((u for k,u in idx.items() if names_match(k,record['name'])),None)
        if not page:raise ValueError('Company not found in current Chittorgarh IPO listings')
        response=network.get(page,timeout=22)
        if response.status_code!=200:raise ValueError('HTTP '+str(response.status_code))
        parsed=parse_statements(response.text,record['name'],page)
        parsed['evidence'].extend(parse_chittorgarh_kpi(response.text,page))
        return parsed
    data=attempt('Chittorgarh',chittorgarh_source)
    if data:
        combine(result,[e for e in data['evidence'] if not e['method'].startswith('Derived')]);result['url']=result['url'] or data['url']
    def ipoji_source():
        idx=get_ipoji_index()
        page=idx.get(key) or next((u for k,u in idx.items() if names_match(k,record['name'])),None)
        if not page:raise ValueError('Company not found in current IPOJI IPO listings')
        response=network.get(page,timeout=22)
        if response.status_code!=200:raise ValueError('HTTP '+str(response.status_code))
        return parse_statements(response.text,record['name'],page)
    data=attempt('IPOJI',ipoji_source)
    if data:
        combine(result,[e for e in data['evidence'] if not e['method'].startswith('Derived')]);result['url']=result['url'] or data['url']
    if key in KNOWN_DOCUMENTS:documents.insert(0,KNOWN_DOCUMENTS[key])
    for document in list(dict.fromkeys(documents))[:1]:
        def primary():
            from .prospectus import parse_pdf
            cache=Path(db.APP_DIR)/'filing_cache';cache.mkdir(exist_ok=True)
            file=cache/(hashlib.sha256(document.encode()).hexdigest()+'.json')
            if file.exists() and datetime.now().timestamp()-file.stat().st_mtime<86400:
                saved=json.loads(file.read_text(encoding='utf-8'))
                if saved.get('version')==VERSION and saved.get('name')==key:return saved['evidence'],saved.get('scalar_evidence',[])
            response=network.get(document,timeout=60)
            if response.status_code!=200:raise ValueError('HTTP '+str(response.status_code))
            if not response.content.startswith(b'%PDF'):raise ValueError('Source did not return a PDF')
            evidence,scalar_evidence=parse_pdf(response.content,record['name'],document)
            file.write_text(json.dumps({'version':VERSION,'name':key,'evidence':evidence,'scalar_evidence':scalar_evidence}),encoding='utf-8')
            return evidence,scalar_evidence
        parsed=attempt('Issuer / lead-manager RHP',primary)
        if parsed:
            evidence,scalar_evidence=parsed
            combine(result,evidence);result['url']=document
            combine_scalars(result,scalar_evidence)
    result['incomplete']=any(a['message']!='Retrieved and parsed' for a in result['attempts'])
    if old.get('series'):
        for ev in old.get('evidence',[]):
            if not str(ev.get('method','')).startswith('Derived'):
                ev=dict(ev);ev.setdefault('at',old.get('at'))
                if ev.get('primary') or int(ev['year']) not in result['series'] or ev['metric'] not in result['series'][int(ev['year'])]:combine(result,[ev])
    if old.get('scalars'):
        # Old scalars only fill in metrics this run didn't find (e.g. the
        # RHP fetch was skipped this time because it's still within the
        # cache window under a different code path, or failed transiently)
        # — never overwrite a value this run actually found.
        for metric,value in old['scalars'].items():
            if metric not in result['scalars']:result['scalars'][metric]=value
    for ev in result['evidence']:ev.setdefault('at',result['at'])
    if not result['evidence']:raise ValueError('; '.join(a['source']+': '+a['message'] for a in result['attempts']))
    derive(result)
    return result,False

def enrich_record(record):
    research,cached=fetch_research(record)
    series={int(y):r for y,r in research['series'].items()};latest=max(series);years=[latest-2,latest-1,latest]
    current=db.get(record['id']) or record;origins=current.get('field_sources') or {}
    existing=[int(y) for y in current.get('years',[]) if re.fullmatch(r'20\d{2}',str(y))]
    financial_keys=['revenue','pat','ebitda','cfo','fcf']
    manual_arrays=any(origins.get(k,{}).get('source')=='manual' for k in financial_keys)
    if not existing or existing==years or (not manual_arrays and max(existing)<=latest):
        current['years']=[str(y) for y in years]
        for k in financial_keys:
            if origins.get(k,{}).get('source')=='manual':continue
            current[k]=[series.get(y,{}).get(k) for y in years]
            origins[k]={'source':'research','url':research['url'],'official':False,'at':research['at']}
        for k in ['inv_days','deb_days','cred_days','de','roe','roce','pe']:
            if k in series[latest] and origins.get(k,{}).get('source')!='manual':
                current[k]=series[latest][k];origins[k]={'source':'research','url':research['url'],'official':False,'at':research['at']}
        # "Liquidity" has no automated source of its own (see BLANK schema),
        # so it sits at Pending forever unless entered manually. Derive a
        # stand-in from the current ratio (current assets / current
        # liabilities) already parsed for the latest year, when nothing
        # manual has been entered — see scoring.liquidity_score() for what
        # this does and does not measure.
        ca,cl=series[latest].get('current_assets'),series[latest].get('current_liabilities')
        if ca is not None and cl not in (None,0) and origins.get('liquidity',{}).get('source')!='manual':
            derived_liquidity=scoring.liquidity_score(ca/cl)
            if derived_liquidity is not None:
                current['liquidity']=derived_liquidity
                origins['liquidity']={'source':'research: derived from current ratio','url':research['url'],'official':False,'at':research['at']}
    # A plainer, reliable route to the IPO's own P/E when some source has
    # reported market cap directly: P/E = market cap / latest PAT. Plain
    # arithmetic on two already-trusted numbers, so it only fills in when
    # the structural table-sourced 'pe' just above wasn't already found —
    # a real reported P/E always wins over one we compute ourselves.
    latest_pat=(current.get('pat') or [None])[-1]
    if not scoring.has(current.get('pe')) and scoring.has(current.get('market_cap')) and scoring.has(latest_pat) and float(latest_pat)>0 and origins.get('pe',{}).get('source')!='manual':
        current['pe']=round(float(current['market_cap'])/float(latest_pat),2)
        origins['pe']={'source':'research: derived (market cap \u00f7 latest PAT)','url':research['url'],'official':False,'at':research['at']}
    # Experimental prospectus-text values (see prospectus.parse_valuation_
    # and_concentration): lowest priority of the three 'pe' routes above —
    # only fills in what neither the structural table parse nor the
    # market-cap arithmetic could — tagged clearly so it's distinguishable
    # from the more trustworthy figures above, and independent of the
    # fiscal-year gate the first block sits in, since none of these are
    # year-indexed.
    scalars=research.get('scalars') or {}
    for metric in ('pe','peer_pe','top_cust','top_supp'):
        if metric in scalars and scoring.has(scalars[metric]) and origins.get(metric,{}).get('source')!='manual' and not scoring.has(current.get(metric)):
            current[metric]=scalars[metric]
            origins[metric]={'source':'research: prospectus text search (experimental)','url':research['url'],'official':False,'at':research['at']}
    current['research']=research;current['field_sources']=origins
    db.upsert_ipo(current)
    for url in dict.fromkeys(e['source'].split('#')[0] for e in research['evidence'] if e.get('source')):
        db.add_source(current['id'],urlsplit(url).hostname or 'Financial source',url,'Annual statement evidence; see financial tabs and source differences')
    return f'{record["name"]}: FY{latest}; {len(research["evidence"])} financial observations; '+('cached' if cached else 'research updated')
