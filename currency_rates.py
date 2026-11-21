"""Public currency quote API; explicit direction is INR per one foreign unit."""
import datetime,json,math,urllib.request
from decimal import Decimal
IST=datetime.timezone(datetime.timedelta(hours=5,minutes=30))

PUBLIC_ENDPOINT='https://open.er-api.com/v6/latest/{code}'

def code_from_selection(selection):return selection.split(' - ',1)[0] if selection and selection!='None' else ''

def parse_quote(data,code,source):
    if data.get('result') not in (None,'success'):raise ValueError('Rate provider did not return a successful quote.')
    if data.get('base_code',data.get('base'))!=code:raise ValueError('Provider quote has the wrong base currency.')
    rate=Decimal(str(data.get('rates',{}).get('INR','0')))
    if not rate.is_finite() or rate<=0:raise ValueError('Provider did not return a positive INR conversion rate.')
    stamp=data.get('time_last_update_unix')
    if stamp:
        asof=datetime.datetime.fromtimestamp(float(stamp),datetime.timezone.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M IST')
    else:asof=str(data.get('date') or data.get('time_last_update_utc') or '')
    if not asof:raise ValueError('Provider did not supply a quote date; no undated automatic rate accepted.')
    return dict(code=code,rate=str(rate),direction='INR per 1 '+code,source=source,as_of=asof,fetched_at=datetime.datetime.now(IST).isoformat(),manual=False,quote_timestamp=float(stamp) if stamp else None)

def fetch_quote(code,opener=None):
    if not code.isalpha() or len(code)!=3:raise ValueError('Select a currency first.')
    source=PUBLIC_ENDPOINT.format(code=code)
    request=urllib.request.Request(source,headers={'User-Agent':'NetAssetReport/2.1'})
    with (opener or urllib.request.urlopen)(request,timeout=12) as response:
        data=json.loads(response.read().decode('utf-8'))
    return parse_quote(data,code,source)

def validate_rate_for_report(report):
    code=code_from_selection(report.get('currency','None'))
    if not code:return
    meta=report.get('rate_meta') or {}
    if meta and meta.get('code')!=code:raise ValueError('The saved rate belongs to another currency. Refresh or enter a reviewed manual rate.')
    if meta.get('requested_date'):
        requested=selected_date(report).isoformat()
        if requested!=meta['requested_date']:raise ValueError('FX/report date changed. Refresh the quote or enter a reviewed manual rate for the new date.')
    if meta.get('requires_date_review') and not meta.get('date_reviewed'):raise ValueError('The provider returned a different effective date. Explicitly review/accept it or enter a manual rate.')
    if meta.get('rate') and not meta.get('manual') and rate_decimal(meta['rate'])!=rate_decimal(report.get('rate','')):raise ValueError('The rate changed without updated provenance. Enter/review the manual rate again.')
    stamp=meta.get('quote_timestamp')
    if stamp is not None and not meta.get('manual'):
        age=datetime.datetime.now(datetime.timezone.utc).timestamp()-float(stamp)
        if age>72*3600 or age < -24*3600:raise ValueError('The saved automatic quote is older than 72 hours or has an invalid future date. Refresh or enter a reviewed manual rate.')
        if meta.get('rate') and rate_decimal(meta['rate'])!=rate_decimal(report.get('rate','')):raise ValueError('The rate changed without updated provenance. Enter/review the manual rate again.')
    if meta.get('pending'):raise ValueError('Wait for the rate request or enter a manual rate.')
    if meta.get('error'):raise ValueError('Automatic rate failed. Enter a manual rate and source/date, or retry Refresh rate.')

def rate_decimal(value):
    try:rate=Decimal(str(value).replace(',','').strip())
    except Exception as exc:raise ValueError('Enter a positive INR-per-foreign-unit exchange rate.') from exc
    if not rate.is_finite() or rate<=0:raise ValueError('Enter a positive INR-per-foreign-unit exchange rate.')
    return rate

COUNTRY_CODES={'Canada':'CAD','Australia':'AUD','United States':'USD','USA':'USD','United Kingdom':'GBP','UK':'GBP','New Zealand':'NZD','Germany':'EUR','France':'EUR','Ireland':'EUR','Italy':'EUR','Spain':'EUR','Singapore':'SGD','United Arab Emirates':'AED','UAE':'AED'}
HISTORICAL_ENDPOINT='https://api.frankfurter.dev/v2/rate/{code}/INR?date={date}'

def report_date(value):
    raw=str(value).strip()
    for fmt in ('%d-%m-%Y','%d.%m.%Y','%d/%m/%Y','%Y-%m-%d'):
        try:return datetime.datetime.strptime(raw,fmt).date()
        except ValueError:pass
    raise ValueError('Enter a valid FX/report date (DD-MM-YYYY). Blank FX date uses the statement date.')

def country_code(country):
    return next((code for name,code in COUNTRY_CODES.items() if name.casefold()==str(country).strip().casefold()),'')

def selected_date(report):return report_date(report.get('fx_date') or report.get('statement_date',''))

def parse_historical_quote(data,code,requested,source):
    requested=report_date(requested) if not isinstance(requested,datetime.date) else requested
    if data.get('base','').upper()!=code or data.get('quote','').upper()!='INR':raise ValueError('Provider returned the wrong currency pair; no quote was applied.')
    rate=rate_decimal(data.get('rate',''));effective=datetime.date.fromisoformat(str(data.get('date','')))
    if effective>requested:raise ValueError('Provider effective date is after the requested date; no future/nearest quote was applied.')
    return dict(code=code,rate=str(rate),direction='INR per 1 '+code,source=source,provider='Frankfurter blended daily reference sources',requested_date=requested.isoformat(),effective_date=effective.isoformat(),as_of=effective.isoformat()+' (provider effective date)',fetched_at=datetime.datetime.now(IST).isoformat(),manual=False,requires_date_review=effective!=requested,date_reviewed=effective==requested,historical=requested<datetime.datetime.now(IST).date())

def fetch_quote_for_date(code,date_value,opener=None):
    if not code.isalpha() or len(code)!=3:raise ValueError('Choose a supported foreign currency first.')
    requested=report_date(date_value) if not isinstance(date_value,datetime.date) else date_value
    if requested>datetime.datetime.now(IST).date():raise ValueError('Future FX date: historical reference rates do not exist yet. Choose a valid date or enter an explicitly reviewed manual forecast rate; no current rate will be substituted.')
    source=HISTORICAL_ENDPOINT.format(code=code,date=requested.isoformat());request=urllib.request.Request(source,headers={'User-Agent':'NetAssetReport/2.1'})
    with (opener or urllib.request.urlopen)(request,timeout=12) as response:data=json.loads(response.read().decode('utf-8'))
    return parse_historical_quote(data,code,requested,source)

def quote_caption(report):
    meta=report.get('rate_meta') or {}
    if not meta:return 'Manual / legacy rate; source date not supplied'
    return ('INR '+str(report.get('rate',''))+' per 1 '+str(meta.get('code',''))+' | Requested: '+str(meta.get('requested_date','not supplied'))+' | Effective: '+str(meta.get('effective_date',meta.get('as_of','not supplied')))+' | '+str(meta.get('source','Manual'))+(' | MANUAL, not independently verified' if meta.get('manual') else '')+(' | Non-requested provider date explicitly accepted' if meta.get('requires_date_review') and meta.get('date_reviewed') else ''))
