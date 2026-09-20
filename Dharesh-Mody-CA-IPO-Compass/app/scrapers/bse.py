from .. import network
from .base import parse_html_tables, rows_to_records, number_text, price_text, normalize_status
NAME = 'BSE India'
URL = 'https://www.bseindia.com/markets/PublicIssues/IPOIssues?Type=p&expandable=4&id=1'
# flag=1 (the only value this scraper previously ever requested) has only
# ever been confirmed to return currently-active issues, so a BSE IPO that
# has already closed or listed dropped out of this feed entirely and never
# got an official close_date/subscription update again. flag=2/3 are a
# best-effort attempt at BSE's closed/listed equivalents, following the
# same numbered-flag convention as flag=1; each is requested independently
# below and a wrong/unsupported flag simply yields zero rows rather than
# failing the whole fetch.
API_URL = 'https://api.bseindia.com/BseIndiaAPI/api/GetPublicIssue_par_updated/w?flag=1'
API_URL_CLOSED = 'https://api.bseindia.com/BseIndiaAPI/api/GetPublicIssue_par_updated/w?flag=2'
API_URL_LISTED = 'https://api.bseindia.com/BseIndiaAPI/api/GetPublicIssue_par_updated/w?flag=3'
HEADERS = {'User-Agent':'Mozilla/5.0','Referer':'https://www.bseindia.com/'}

def parse_api(data):
    rows = []
    if isinstance(data, list):
        for item in data: rows.extend(parse_api(item))
        return rows
    if not isinstance(data, dict): return []
    values = {str(k).lower().replace('_',''):v for k,v in data.items()}
    def val(*keys):
        return next((values[k.lower().replace('_','')] for k in keys if values.get(k.lower().replace('_','')) not in (None,'')), None)
    name = val('companyName','issuerName','scripName','issueName','company')
    if name:
        kind = str(val('IR_FLAG_FULL','IR_flag','typeOfIssue','issueKind') or 'IPO').upper()
        if kind not in ('IPO','I','INITIAL PUBLIC OFFER'): return []
        low, high = price_text(val('priceBand','issuePrice','price','offerPrice'))
        return [{'name':str(name),'exchange':'BSE','board':'SME' if 'sme' in str(val('board','segment','platform','EXCHANGE_PLATFORM')).lower() else 'Mainboard',
                 'open_date':val('startDate','Start_Dt','issueStartDate','openDate'), 'close_date':val('endDate','End_Dt','issueEndDate','closeDate'),
                 # Not previously mapped — see scrapers/base.py's listing_date
                 # alias comment; without this a BSE-listed IPO could never
                 # reach the "Listed" status bucket from an automatic refresh.
                 'listing_date':val('listingDate','ListingDate','dateOfListing','listing_Dt'),
                 'status':normalize_status({'F':'Upcoming','H':'Closed','L':'Open'}.get(str(val('status','issueStatus')), str(val('status','issueStatus') or ''))),
                 'price_low':low,'price_high':high,'sub_total':number_text(val('totalSubscription','noOfTimes'))}]
    for value in data.values():
        if isinstance(value,(dict,list)): rows.extend(parse_api(value))
    return rows

def fetch():
    errors = []
    records = []
    for url, label in ((API_URL, 'active'), (API_URL_CLOSED, 'closed'), (API_URL_LISTED, 'listed')):
        try:
            response = network.get(url, headers=HEADERS, timeout=15)
            if response.status_code != 200: raise RuntimeError(f'HTTP {response.status_code}')
            rows = parse_api(response.json())
            records.extend(rows)
        except Exception as e:
            errors.append(f'{label}: {e}')
    if records:
        return records, f'Parsed {len(records)} BSE IPO records from JSON' + ('; PARTIAL: '+'; '.join(errors) if errors else '')
    errors.append('No recognised IPO rows in BSE JSON')
    response = network.get(URL, headers=HEADERS, timeout=15)
    if response.status_code != 200: raise RuntimeError(f'BSE page HTTP {response.status_code}; '+ '; '.join(errors))
    records = []
    for table in parse_html_tables(response.text):
        headers = [x.lower() for x in table[0]]
        type_col = next((i for i,h in enumerate(headers) if 'type of issue' in h), None)
        if type_col is not None: table = [table[0]]+[r for r in table[1:] if len(r)>type_col and r[type_col].upper()=='IPO']
        records.extend(rows_to_records(table))
    if not records: raise RuntimeError('BSE supplied no recognised public IPO table; '+ '; '.join(errors))
    for r in records: r['exchange']='BSE'
    return records, f'Parsed {len(records)} BSE IPO rows from public HTML'
