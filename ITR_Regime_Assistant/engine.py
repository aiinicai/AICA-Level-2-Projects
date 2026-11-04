"""AY 2026-27 only. Decimal calculations; no model participates in tax arithmetic."""
from decimal import Decimal, InvalidOperation
from copy import deepcopy
D=Decimal
YEAR='2026-27'
FIELDS={
 'salary':'Gross taxable salary / regular pension before standard deduction (includes HRA)',
 'savings':'Eligible savings-bank interest', 'deposits':'Eligible bank / post-office deposit interest',
 'other':'Other normal-rate income (e.g. domestic dividend; no family pension)',
 'hra':'HRA actually received (included in salary)', 'hra_salary':'HRA salary: basic + eligible DA + turnover commission',
 'rent':'Rent paid for the same HRA period', 'professional_tax':'Professional tax actually paid',
 'c80':'Eligible 80C / 80CCC / 80CCD(1) combined (after individual limits)',
 'nps':'Eligible additional 80CCD(1B), excluding contributions in 80C bucket',
 'health_self':'Eligible 80D self/family amount', 'health_parents':'Eligible 80D parents amount',
 'home_interest':'Eligible self-occupied home interest (review conditions first)',
 'credits':'Verified TDS + TCS + advance / self-assessment tax credits'}
FLAGS={
 'resident':'Resident and ordinarily resident individual',
 'normal_income_only':'No business, capital gains, special-rate, agricultural, foreign, clubbed or family-pension income',
 'simple_property':'No let-out property, multiple-property computation, brought-forward losses or carry-forward claims',
 'supported_claims':'No additional exemptions, deductions, reliefs or AMT outside this application',
 'facts_complete':'All income and claim eligibility checked against evidence',
 'old_option':'Eligibility and timely valid election for old regime confirmed',
 'form_simple':'No director/unlisted shares/foreign assets or signing authority/194N/deferred ESOP/form exclusions',
 'evidence':'Form 16 / pension certificate, AIS / TIS / 26AS and interest certificates reconciled',
 'claims_evidence':'Rent, deductions and home-loan documents verified where applicable',
 'filing_steps':'Portal particulars, bank validation, taxes/interest/fees and e-verification separately checked'}
BLOCKERS=['resident','normal_income_only','simple_property','supported_claims']
def blank():
 return dict(year=YEAR,case='New case',age=35,metro=False,self_senior=False,parents_senior=False,home_cap='200000',**{k:'0' for k in FIELDS},**{k:False for k in FLAGS})
def money(v):
 try: x=D(str(v).replace(',',''))
 except (InvalidOperation,ValueError): raise ValueError('Enter valid numeric amounts.')
 if not x.is_finite() or x<0: raise ValueError('Amounts must be finite and non-negative.')
 return x

def round10(x):
 x=D(x); sign=-1 if x<0 else 1
 return D(sign)*D(((int(abs(x))+5)//10)*10)

def validate(p):
 if p.get('year')!=YEAR: raise ValueError('Only AY 2026-27 / FY 2025-26 is supported.')
 try: age=int(str(p.get('age')))
 except ValueError: raise ValueError('Age must be a whole number.')
 if not 18<=age<=110: raise ValueError('Supported age range is 18 to 110, at 31 March 2026.')
 for k in FLAGS:
  if type(p.get(k)) is not bool: raise ValueError('Checklist answers must be true or false: '+k)
 for k in ('metro','self_senior','parents_senior'):
  if type(p.get(k)) is not bool: raise ValueError('Invalid option: '+k)
 a={k:money(p.get(k,0)) for k in FIELDS}
 if p.get('home_cap') not in ('30000','200000'): raise ValueError('Home interest cap must be 30000 or 200000.')
 if a['hra']>a['salary'] or a['hra_salary']+a['hra']>a['salary']: raise ValueError('HRA plus HRA salary cannot exceed gross salary.')
 if a['hra'] and not a['hra_salary']: raise ValueError('Enter HRA salary for a positive HRA claim.')
 if a['salary']+a['savings']+a['deposits']+a['other']>5000000: raise ValueError('Gross supported income exceeds Rs 50 lakh; surcharge cases require separate review.')
 return age,a

def tax(total,regime,age):
 t=round10(max(D(0),D(total))); base=D(0); rows=[]
 if regime=='New': bands=[(400000,0),(800000,'.05'),(1200000,'.10'),(1600000,'.15'),(2000000,'.20'),(2400000,'.25'),(None,'.30')]
 else: bands=[(500000 if age>=80 else 300000 if age>=60 else 250000,0)] + ([] if age>=80 else [(500000,'.05')])+[(1000000,'.20'),(None,'.30')]
 lower=D(0)
 for upper,rate in bands:
  part=max(D(0),min(t,D(upper) if upper else t)-lower); amount=part*D(rate)
  rows.append(dict(lower=lower,upper=upper,rate=str(rate),taxable=part,tax=amount)); base+=amount
  if upper: lower=D(upper)
 rebate=min(base,D(60000)) if regime=='New' and t<=1200000 else min(base,D(12500)) if regime=='Old' and t<=500000 else D(0)
 marginal=max(D(0),base-(t-1200000)) if regime=='New' and t>1200000 else D(0)
 net=base-rebate-marginal; cess=net*D('.04')
 return dict(total_income=t,slab_tax=base,rebate=rebate,marginal_relief=marginal,cess=cess,raw_tax=net+cess,tax=round10(net+cess),bands=rows)

def calculate(p):
 age,a=validate(p)
 blocked=[FLAGS[k] for k in BLOCKERS if not p[k]]
 if blocked: return dict(blocked=blocked)
 if min(a['home_interest'],D(p['home_cap']))>max(D(0),a['salary']-50000)+a['savings']+a['deposits']+a['other']:
  return dict(blocked=['Potential house-property loss carry-forward: requires separate review.'])
 hra=max(D(0),min(a['hra'],a['rent']-a['hra_salary']*D('.1'),a['hra_salary']*(D('.5') if p['metro'] else D('.4'))))
 claims={'80C combined':min(a['c80'],D(150000)),'80CCD(1B)':min(a['nps'],D(50000)),
  '80D self/family':min(a['health_self'],D(50000 if p['self_senior'] or age>=60 else 25000)),
  '80D parents':min(a['health_parents'],D(50000 if p['parents_senior'] else 25000)),
  '80TTB' if age>=60 else '80TTA':min(a['savings']+a['deposits'] if age>=60 else a['savings'],D(50000 if age>=60 else 10000))}
 out={}; warnings=[]
 if a['c80']>150000 or a['nps']>50000: warnings.append('Entered investment deductions exceed a section cap; only capped amounts allowed.')
 if p['self_senior'] and age<60: warnings.append('Self/family senior flag requires a qualifying senior spouse or family member; verify eligibility.')
 for regime in ('Old','New'):
  exempt=hra if regime=='Old' else D(0)
  standard=min(max(D(0),a['salary']-exempt),D(50000 if regime=='Old' else 75000))
  pt=min(a['professional_tax'],max(D(0),a['salary']-exempt-standard)) if regime=='Old' else D(0)
  sal=max(D(0),a['salary']-exempt-standard-pt)
  before_house=sal+a['savings']+a['deposits']+a['other']
  if regime=='Old' and min(a['home_interest'],D(p['home_cap']))>before_house:
   return dict(blocked=['House-property loss exceeds available income; carry-forward review required.'])
  house=min(a['home_interest'],D(p['home_cap']),before_house) if regime=='Old' else D(0)
  gti=before_house-house
  deduction=min(gti,sum(claims.values())) if regime=='Old' else D(0)
  r=tax(gti-deduction,regime,age)
  r.update(hra_exemption=exempt,standard_deduction=standard,professional_tax=pt,salary_income=sal,house_loss_setoff=house,gti=gti,chapter_via=deduction,claims=claims if regime=='Old' else {},balance=round10(r['raw_tax']-a['credits']))
  out[regime]=r
 old,new=out['Old']['tax'],out['New']['tax']; winner='Tie' if old==new else 'Old' if old<new else 'New'
 conditional=not p['facts_complete'] or (winner=='Old' and not p['old_option'])
 out.update(blocked=[],winner=winner,saving=abs(old-new),status='Conditional comparison — eligibility/evidence pending' if conditional else 'Reviewed inputs — numeric preference only',warnings=warnings,
 form='ITR-1 candidate only; verify portal eligibility' if p['form_simple'] else 'Return form requires manual review',
 readiness=[v for k,v in FLAGS.items() if not p[k]])
 return out

def scenarios(p):
 base=calculate(p)
 if base['blocked']: return []
 rows=[]
 for label,changes in [('Entered facts',{}),('80C filled to cap (hypothetical)',{'c80':'150000'}),('Additional NPS filled to cap (hypothetical)',{'nps':'50000'}),('Both caps (hypothetical)',{'c80':'150000','nps':'50000'})]:
  q=deepcopy(p); q.update(changes); r=calculate(q)
  cost=max(D(0),min(money(q['c80']),D(150000))-min(money(p['c80']),D(150000)))+max(D(0),min(money(q['nps']),D(50000))-min(money(p['nps']),D(50000)))
  rows.append(dict(scenario=label,additional_contribution=cost,old_tax=r['Old']['tax'],new_tax=r['New']['tax'],old_tax_reduction=base['Old']['tax']-r['Old']['tax'],winner=r['winner']))
 return rows

def narrative(p,r):
 if r['blocked']: return 'COMPARISON BLOCKED\n'+'\n'.join(r['blocked'])+'\nDo not use partial data to select a regime.'
 lines=[f"{p['case']} | AY {YEAR} / FY 2025-26",f"Numeric preference: {r['winner']} | Difference: Rs {r['saving']:,.0f}",r['status'],r['form'],'','Particular                                      OLD             NEW']
 for key in ['hra_exemption','standard_deduction','professional_tax','salary_income','house_loss_setoff','gti','chapter_via','total_income','slab_tax','rebate','marginal_relief','cess','tax','balance']:
  lines.append(f"{key:40} {r['Old'][key]:>14,.2f} {r['New'][key]:>14,.2f}")
 lines+=['','Balance: positive = indicative payable; negative = indicative refund. Excludes interest, fees and reliefs.','Old-regime allowed deduction buckets:']+[f'{k}: Rs {v:,.2f}' for k,v in r['Old']['claims'].items()]
 lines+=['','PENDING CHECKS:']+r['readiness']+r['warnings']
 lines+=['','HYPOTHETICAL CONTRIBUTIONS — NOT retrospective claims or investment advice:']
 for s in scenarios(p): lines.append(f"{s['scenario']}: additional Rs {s['additional_contribution']:,.0f}; old tax Rs {s['old_tax']:,.0f}; reduction Rs {s['old_tax_reduction']:,.0f}")
 return '\n'.join(lines)

def ai_prompt(p,r):
 return 'Draft a plain-language taxpayer explanation and an auditor review checklist using ONLY the supplied calculation. Do not change figures, invent deductions, promise filing eligibility or give investment advice. Mark unresolved checks. This is an unapproved draft. No identifiers are supplied.\n\n'+narrative({**p,'case':'Anonymous case'},r)
