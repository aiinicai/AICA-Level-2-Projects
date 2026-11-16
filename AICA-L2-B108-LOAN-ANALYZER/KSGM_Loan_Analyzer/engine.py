"""Deterministic daily-product loan analysis; no AI is used for calculations."""
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation
import re

CATEGORIES = ['Other', 'Interest', 'Penal interest', 'Processing fee', 'Bank charges', 'GST / tax', 'Insurance']
RULES = [
 ('GST / tax', r'\b(?:gst|cgst|sgst|igst|service tax)\b'),
 ('Penal interest', r'penal|overdue int|penalty interest'),
 ('Interest', r'\binterest\b|\bint[ ._-]*(?:dr|debit|charged|applied)\b|\bdebit int\b'),
 ('Processing fee', r'processing|renewal fee|documentation fee'),
 ('Insurance', r'insurance|premium'),
 ('Bank charges', r'\bcharges?\b|\bchgs?\b|\bcommission\b|\bfee\b|\bfees\b|\bbounce\b|\breturn chg\b'),
]

def money(value, blank=None):
    s = str('' if value is None else value).strip().replace(',', '').replace('₹', '').replace('INR', '').strip()
    if s in ('', '-', '--', 'nan', 'None'): return blank
    neg = s.startswith('(') and s.endswith(')')
    s = re.sub(r'\s*(?:CR|DR)\s*$', '', s, flags=re.I).strip('() ')
    try:
        result = Decimal(s)
        if not result.is_finite(): raise ValueError('Non-finite amount')
        return -result if neg else result
    except InvalidOperation: raise ValueError('Invalid amount: ' + str(value))

def parse_date(value, dayfirst=True):
    if isinstance(value, datetime): return value.date()
    if isinstance(value, date): return value
    s = str(value).strip().split(' ')[0]
    formats = ['%Y-%m-%d', '%Y/%m/%d', '%d-%b-%Y', '%d-%b-%y', '%d/%b/%Y']
    formats += ['%d/%m/%Y','%d-%m-%Y','%d/%m/%y'] if dayfirst else ['%m/%d/%Y','%m-%d-%Y','%m/%d/%y']
    for fmt in formats:
        try: return datetime.strptime(s, fmt).date()
        except ValueError: pass
    raise ValueError('Unrecognised date: ' + str(value))

def classify(description):
    for category, pattern in RULES:
        if re.search(pattern, description, re.I): return category
    return 'Other'

def normalize(rows, mapping, dayfirst=True, balance_mode='Positive outstanding'):
    output, errors = [], []
    for index, raw in enumerate(rows, 1):
        if not any(str(x or '').strip() for x in raw.values()): continue
        try:
            get = lambda field: raw.get(mapping.get(field, ''), '')
            d = parse_date(get('Date'), dayfirst)
            desc = str(get('Description') or '').strip()
            debit, credit = money(get('Debit'), Decimal(0)), money(get('Credit'), Decimal(0))
            if debit < 0 or credit < 0: raise ValueError('Debit/credit columns must be non-negative')
            if debit and credit: raise ValueError('Both debit and credit populated')
            bal_value = get('Balance')
            bal_raw = str('' if bal_value is None else bal_value).strip()
            balance = money(bal_raw)
            if balance is not None:
                if balance_mode == 'DR/CR suffix':
                    if not re.search(r'(?:DR|CR)\s*$', bal_raw, re.I): raise ValueError('Balance needs DR or CR suffix')
                    balance = abs(balance) if re.search(r'DR\s*$', bal_raw, re.I) else -abs(balance)
                elif balance_mode == 'Negative bank balance': balance = -balance
            output.append(dict(source=index, date=d, description=desc, debit=debit, credit=credit,
                               balance=balance, category=classify(desc)))
        except (ValueError, TypeError) as exc: errors.append(f'Row {index}: {exc}')
    return output, errors

def analyze(rows, start, end, opening, annual_rate, basis='Actual/365', mode='Daily closing balance', rate_changes=None):
    if end < start: raise ValueError('End date must be on or after start date')
    if (end-start).days > 36600: raise ValueError('Choose a period of at most 100 years')
    if opening < 0 or annual_rate < 0: raise ValueError('Opening outstanding and rate cannot be negative')
    changes = sorted(rate_changes or [], key=lambda x:x[0])
    if len({d for d,r in changes}) != len(changes): raise ValueError('Duplicate rate-change dates')
    if any(r < 0 for d,r in changes): raise ValueError('Interest rates cannot be negative')
    ordered = sorted(rows, key=lambda r:(r['date'],r['source']))
    within = [r for r in ordered if start <= r['date'] <= end]
    by_date = {}
    for row in within: by_date.setdefault(row['date'], []).append(row)
    if mode == 'Daily closing balance' and any(r['balance'] is None for r in within):
        raise ValueError('Every transaction needs a closing balance for daily balance mode')
    # Opening means immediately before the selected start date; never infer it from a later row.
    balance, daily, rate = opening, [], annual_rate
    day = start
    while day <= end:
        for effective, new_rate in changes:
            if effective <= day: rate = new_rate
        if mode == 'Daily closing balance':
            for row in by_date.get(day, []): balance = row['balance']
        principal = max(Decimal(0), balance)
        divisor = 360 if basis == 'Actual/360' else 365
        if basis == 'Actual/Actual': divisor = (date(day.year+1,1,1)-date(day.year,1,1)).days
        interest = principal * rate / Decimal(100) / Decimal(divisor)
        daily.append(dict(date=day,outstanding=principal,rate=rate,days_basis=divisor,interest=interest))
        day += timedelta(days=1)
    totals = {c:Decimal(0) for c in CATEGORIES if c != 'Other'}
    for row in within:
        if row['category'] in totals: totals[row['category']] += row['debit']-row['credit']
    expected = sum((r['interest'] for r in daily),Decimal(0))
    exposure = sum((r['outstanding'] for r in daily),Decimal(0))
    reconciliation = []
    previous = opening
    if mode == 'Daily closing balance':
        for row in within:
            difference = row['balance'] - (previous+row['debit']-row['credit'])
            if abs(difference) > Decimal('0.02'):
                reconciliation.append(f"Source row {row['source']}: balance differs by {difference:.2f}")
            previous = row['balance']
    return dict(daily=daily, transactions=within, totals=totals, expected=expected,
                variance=totals['Interest']-expected, exposure=exposure,
                average=exposure/len(daily), days=len(daily),
                implied=(totals['Interest']*36500/exposure if exposure else None),
                all_cost=sum(totals.values(),Decimal(0)), warnings=reconciliation)
