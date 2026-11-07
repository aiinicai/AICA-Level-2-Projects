"""TreatyLens V5: deterministic workbook-based withholding illustration.

Rates are transcribed from the user-supplied workbook. They are not certified
as current law. This application does not establish chargeability or treaty
entitlement and must not be relied on to file/remit without review.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from datetime import date
import json

DB=json.loads((Path(__file__).parent/'rates_database.json').read_text(encoding='utf-8'))
COUNTRIES=sorted(set(x['country'] for x in DB['rates']))
CATEGORIES=list(DB['recipient_types'])
CORE=('trc','form41','nope')

class InputError(ValueError):pass

def money(x):return str(x.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
def norm(x):return str(x or '').strip().lower()
def money_input(v):
 try:
  x=Decimal(str(v))
  if not x.is_finite() or x<=0 or x>Decimal('1000000000000000'):raise InputError('Gross payment must be a positive amount')
  return x
 except (InvalidOperation,TypeError):raise InputError('Enter a valid gross payment amount')

def find_rate(country,category,recipient_type,shareholding=None):
 """Select a workbook row only where the recipient-specific conditions identify it.

 Returns (rate record, explanation). A nonnumeric rate stays unresolved.
 """
 entries=[r for r in DB['rates'] if r['country']==country and r['category']==category]
 if not entries:return None,'No rate record for this country/payment combination in the revised workbook.'
 rt=norm(recipient_type)
 generic=[r for r in entries if norm(r['recipient_condition']) in ('any','any person','any other recipient')]
 def only(items,label):
  if len(items)==1:return items[0],label
  if len(items)>1:return None,'Multiple '+label+' rows in workbook; manual review required.'
  return None,None
 if category=='Interest' and rt=='bank':
  matched=[r for r in entries if 'bank' in norm(r['recipient_condition'])]
  result,msg=only(matched,'bank-specific')
  if msg:return result,msg
 if category=='Dividend' and 'immovable' in rt:
  matched=[r for r in entries if 'immovable' in norm(r['recipient_condition'])]
  result,msg=only(matched,'immovable-property')
  if msg:return result,msg
 if category=='Dividend' and 'control' in rt:
  conditional=[]
  for r in entries:
   t=norm(r['recipient_condition'])
   if 'voting' not in t:continue
   m=__import__('re').search(r'(\d+(?:\.\d+)?)\s*%',t)
   if m:conditional.append((Decimal(m.group(1)),r))
  if conditional:
   if shareholding in (None,''):return None,'Shareholding percentage required for conditional treaty rate.'
   try:sh=Decimal(str(shareholding))
   except InvalidOperation:return None,'Invalid shareholding percentage.'
   if not sh.is_finite() or sh<0 or sh>100:return None,'Shareholding must be between 0 and 100%.'
   eligible=[(n,r) for n,r in conditional if sh>=n and ('more than' not in rt or sh>Decimal(10))]
   if eligible:
    eligible.sort(key=lambda x:x[0],reverse=True)
    result=eligible[0][1]
    if len(eligible)>1 and eligible[0][0]==eligible[1][0]:return None,'More than one qualifying rate row for the same shareholding threshold; manual review required.'
    return result,'Conditional voting-power rate from workbook; legal eligibility requires review.'
   # Threshold not met; assess generic rate without guessing.
 if category in ('Royalty','Fees for technical services') and 'equipment' in rt:
  matched=[r for r in entries if 'equipment' in norm(r['recipient_condition'])]
  result,msg=only(matched,'equipment-specific')
  if msg:return result,msg
 if category=='Royalty' and 'trademark' in rt:
  matched=[r for r in entries if 'trademark' in norm(r['recipient_condition'])]
  result,msg=only(matched,'trademark-specific')
  if msg:return result,msg
 if len(generic)==1:return generic[0],'General recipient workbook row selected.'
 if len(generic)>1:return None,'Multiple general rates in workbook; review original treaty provisions.'
 return None,'No general rate for the selected recipient; review special treaty conditions.'

def domestic(category,amount):
 rows=DB['domestic_rates'].get(category,[])
 if not rows:raise InputError('Domestic rate row missing from workbook')
 rate=Decimal(str(rows[0]['base_rate_percent']));cess=Decimal(str(rows[0]['cess_percent']))
 if amount<Decimal('10000000'): surcharge=Decimal('0')
 elif amount<Decimal('100000000'):surcharge=Decimal('2')
 elif amount>Decimal('100000000'):surcharge=Decimal('5')
 else:raise InputError('Sheet 3 does not specify the surcharge band at exactly ₹10 crore; confirm rate manually.')
 # surcharge on the basic tax; cess on the tax plus surcharge
 effective=rate*(Decimal(1)+surcharge/100)*(Decimal(1)+cess/100)
 return {'basic_rate_percent':str(rate),'surcharge_percent':str(surcharge),'cess_percent':str(cess),'effective_rate_percent':str(effective.quantize(Decimal('0.000001'))),'remittance_code':rows[0]['remittance_code']}

def assess(payload):
 if not isinstance(payload,dict):raise InputError('JSON object required')
 country=str(payload.get('country','')).strip();category=str(payload.get('paymentType','')).strip()
 recipient_type=str(payload.get('residentType','')).strip()
 if country not in COUNTRIES:raise InputError('Select a country from the workbook')
 if category not in CATEGORIES:raise InputError('Select a supported payment category')
 if recipient_type not in DB['recipient_types'][category]:raise InputError('Recipient type does not match the selected payment category')
 amount=money_input(payload.get('amount'))
 ds=payload.get('payDate','')
 try:when=date.fromisoformat(ds)
 except (ValueError,TypeError):raise InputError('Enter a valid payment date')
 if when.year<2000 or when.year>2100:raise InputError('Invalid payment date')
 grossup=payload.get('grossUp')=='Yes'
 core={k:payload.get(k)=='Yes' for k in CORE}
 missing=[k for k in CORE if not core[k]]
 business=payload.get('businessProfitsClause')=='Yes'
 regime=('Income Tax Act, 2025; Income Tax Rules, 2026' if when>=date(2026,4,1) else 'Income-tax Act, 1961; Income-tax Rules, 1962')
 warnings=['Workbook rates are not independently verified as current applicable law. Treaty protocols, MLI, classification, benefits and surcharge applicability require professional review.']
 record=None;dom=None
 # Always expose an informational treaty excerpt, even if treaty relief is not used.
 excerpt_record,excerpt_note=find_rate(country,category,recipient_type,payload.get('shareholding'))
 if excerpt_record is None:
  excerpt_record=next((r for r in DB['rates'] if r['country']==country and r['category']==category),None)
 if missing:
  route='DOMESTIC';dom=domestic(category,amount);applicable=Decimal(dom['effective_rate_percent'])
  remarks='Treaty benefits are not available as one or all of the core documents are not available and hence withholding rate will apply as per Income Tax, 2025.' if when>=date(2026,4,1) else 'Treaty documentation incomplete. Domestic-law withholding mode selected under the applicable historical framework.'
  warnings.append('Domestic rates and surcharge thresholds are taken from Sheet 3 of the uploaded workbook, not independently certified for the recipient or transaction.')
 elif business:
  route='NIL_REVIEW';applicable=Decimal('0')
  remarks='NIL withholding selected under the user-requested business-profits-clause rule; professional verification is mandatory before reliance.'
  warnings.append('A No-PE declaration with business-profits wording does NOT, by itself, make dividend, interest, royalty or FTS non-taxable. Confirm Article 7 characterisation, entitlement and PE facts before applying NIL.')
 else:
  route='TREATY';record,note=find_rate(country,category,recipient_type,payload.get('shareholding'))
  warnings.append(note)
  applicable=Decimal(str(record['rate_percent'])) if record and record['rate_percent'] is not None else None
  remarks=('Workbook DTAA reference rate used, subject to legal verification of treaty entitlement and conditions.' if record and record['rate_percent'] is not None else 'No numeric treaty cap for this selection is established by the revised workbook; review the treaty and charging provisions.')
 tax=None
 if applicable is not None:
  tax=amount*applicable/(Decimal(100)+applicable) if grossup else amount*applicable/Decimal(100)
 result={
  'engine_version':'5.1','status':'COMPUTED_FROM_WORKBOOK_PENDING_LEGAL_REVIEW' if applicable is not None else 'NEEDS_MANUAL_REVIEW',
  'country':country,'category':category,'recipient_type':recipient_type,
  'payment_date':ds,'amount_inr':money(amount),'tax_gross_up':'Yes' if grossup else 'No',
  'business_profits_clause':'Yes' if business else 'No','legal_framework':regime+'; India–'+country+' DTAA',
  'core_documents':core,'missing_core_documents':missing,'mode':route,
  'applicable_rate_percent':str(applicable) if applicable is not None else None,
  'withholding_amount_inr':money(tax) if tax is not None else None,
  'domestic_breakdown':dom,'treaty_rate_record':record,'treaty_evidence_record':excerpt_record,'remarks':remarks,'warnings':warnings,
  'computation_formula':'Gross payment × rate / (100 + rate)' if grossup else 'Gross payment × rate / 100',
  'calculation_label':'User-prescribed gross-up formula (tax-inclusive payment)' if grossup else 'Withholding on payment',
  'review_required':True}
 return result
