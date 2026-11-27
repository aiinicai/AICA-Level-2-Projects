from answer63 import evidence,answer
from engine import finance
from panindia import STATES
u='https://example.gov.in/policy.pdf'
q='What percentage of SGST reimbursement is available to MSMEs?'
d={u:'[Page 1] Large units receive 40% of net SGST. [Page 2] MSMEs – 100% of Gross SGST subject to eligibility. [Page 3] MSME investment above 50 crore receives 40% of SGST.'}
h=evidence(d,q); assert '[Page 2]' in h[0][2]; assert '100%' in answer(h,q,'Maharashtra')[1]
assert answer(evidence({u:'[Page 69] MSME ceiling is Rs 50 crore. Large units receive 40% of SGST.'},q),q,'Maharashtra') is None
assert answer(evidence({u:'[Page 1] MSMEs: 100% of gross SGST. [Page 2] MSMEs: 50% of net SGST.'},q),q,'Maharashtra') is None
assert tuple(round(x,2) for x in finance(200,40,15,5,10))==(-48.37,8.49,3.64)
assert len(STATES)==36
print('All synthetic regression tests passed')
from multi64 import combined
from answer65 import answer as new_answer
sample='[Page 18] 4.3 Industrial Promotion Subsidy (IPS) 2) Eligible Micro, Small & Medium enterprises shall be offered Industrial Promotion Subsidy (IPS) on 100 % Gross State Goods & Services Tax (SGST) payable by the unit on the first sale of eligible products billed and delivered within Maharashtra.'
r,h=combined({u:sample,'https://other.gov.in/policy.pdf':'[Page 69] MSME ceiling is Rs 50 crore. Large units receive 40% of SGST.'},q,'Maharashtra')
assert r and '100%' in r[1] and 'page 18' in r[1],r
for phrase in ['100% Gross SGST','100 % Gross State Goods & Services Tax (SGST)','Hundred percent of Gross SGST','100 per cent of Gross SGST']:
 assert new_answer([(1,u,'MSMEs: '+phrase)],q,'Maharashtra'),phrase
assert new_answer([(1,u,'MSMEs: 100% Gross SGST'),(1,u,'MSMEs: 50% Net SGST')],q,'Maharashtra') is None
assert new_answer([(1,u,'MSMEs investment ceiling 50 crore. Large units receive 40% Gross SGST')],q,'Maharashtra') is None
print('V6.5 screenshot-clause and format regression tests passed')
from answer67 import structured,rank
q2='What is the maximum combined incentive ceiling for Category A and Category B large industrial undertakings in General Sectors?'
def clause(sector,a,b,y):
 return f'Large Industrial Undertaking for {sector} Sectors shall choose any one or any combination. Note: Maximum ceiling of combined eligible incentives shall be {a}% and {b}% of EFCI over the period of {y} years for Category-A and B respectively.'
g={u:'[Page 8] [OCR transcription — verify against original] '+clause('General',20,15,10)+' '+clause('Thrust',35,25,8)+' [Page 11] '+clause('Selected Thrust',50,45,8)}
r=structured(g,q2); assert len(r)==1 and r[0]['a']=='20' and r[0]['b']=='15' and r[0]['ocr']
assert len(structured(g,'What combined incentive ceilings apply?'))==3
assert not structured({u:g[u]+' [Page 12] '+clause('General',25,15,10)},q2)
assert not structured(g,'What is the capital subsidy?')
print('V6.7 sector, paired rates, OCR warning and conflict tests passed')
from answer68 import structured as compare
q3='Compare the maximum combined incentive ceilings for Category A and Category B across General, Thrust and Selected Thrust Sectors under Viksit Gujarat Industrial Policy 2026 for Large Industrial Undertakings.'
mega=clause('Selected Thrust',50,45,10).replace('Large Industrial','Mega Industrial')
g2={u:g[u]+' '+mega}
r=compare(g2,q3); assert len(r)==3 and [x['years'] for x in r]==[10,8,8],r
r=compare(g2,q3.replace(' for Large Industrial Undertakings','')); assert len(r)==4 and {x['size'] for x in r}=={'large','mega'},r
assert not compare({u:g[u]+' [Page 12] '+clause('General',25,15,10)},q3)
assert not compare({u:'[Page 8] '+clause('General',20,15,10)},q3)
assert len(compare(g2,q2))==1
print('V6.8 multi-sector, industry category, missing and conflict tests passed')
from comparison69 import rows_for
rr=rows_for('UP',{u:'Stamp Duty Exemption 100% in Bundelkhand & Poorvanchal, 75% in Madhyanchal & Paschimanchal (except Gautam Buddh Nagar & Ghaziabad) 50% in Gautambuddh Nagar & Ghaziabad districts Investment Promotion Subsidy'},'Stamp duty exemption')
assert [r['Rate'] for r in rr]==['100%','75%','50%'],rr
assert rows_for('MH',{u:sample},'SGST reimbursement')[0]['Rate']=='100 %'
assert not rows_for('GJ',{u:'[Page 13] Stamp duty reimbursement available. Capital subsidy 40%.'},'Stamp duty exemption')[0]['Rate']
assert len(rows_for('GJ',g2,'Combined incentive ceiling'))==4
print('V6.9 comparison tests passed')
from finance70 import project
f=project(200,40,15,5,10)
assert round(f['npv'],2)==8.49 and round(f['payback'],2)==3.64
assert abs(f['irr']-11.659)<0.1
assert project(200,40,15,5,10,2)['npv']<f['npv']
assert project(200,0,0,5,10)['payback'] is None
from comparison70 import rows_for as v70
assert len(v70('GJ',{u:'[Page 1] Capital subsidy available. [Page 2] Capital subsidy available.'},'Capital subsidy'))==1
print('V7.0 finance and missing evidence tests passed')
from answer71 import capital_rows,checked_quote
head='Base Capital subsidy is as follows - District/ Region Large Mega Super Mega Ultra Mega '
row='Gautam Buddha Nagar & Ghaziabad 10% of ECI over a period of 10 years 18% of ECI over a period of 12 years 20% of ECI over a period of 15 years 22% of ECI over a period of 20 years'
question='What is the base capital subsidy percentage and eligibility period for large industrial units in Gautam Buddha Nagar and Ghaziabad under Uttar Pradesh Industrial Policy 2022?'
r=capital_rows({u:head+row},question,'Uttar Pradesh'); assert len(r)==1 and r[0]['rate']=='10%' and r[0]['years']==10,r
assert not capital_rows({u:head+row.split('18%')[0]},question,'Uttar Pradesh')
assert not capital_rows({u:head+row},question,'Gujarat')
assert not capital_rows({u:head+row+' '+head+row.replace('10%','11%')},question,'Uttar Pradesh')
assert checked_quote('[1] "'+row+'"',[(1,u,row)])
assert not checked_quote('[1] '+row.replace('10%','99%'),[(1,u,row)])
print('V7.1 synthetic table and quote validation tests passed')
from answer72 import capital_rows as v72
assert v72({u:head+row},question,'Uttar Pradesh')[0]['rate']=='10%'
variant=head.replace('Super Mega Ultra Mega','Super-Mega Ultra-Mega')+row.replace('Gautam Buddha Nagar','Gautambuddh Nagar').replace(' years ',' years').replace('over a period','over period')
assert v72({u:variant},question,'Uttar Pradesh')[0]['years']==10
assert not v72({u:head+row.split('18%')[0]},question,'Uttar Pradesh')
assert not v72({u:head+row+' '+head+row.replace('10%','11%')},question,'Uttar Pradesh')
diag=[]; assert not v72({u:'Capital subsidy available'},question,'Uttar Pradesh',diag) and diag
print('V7.2 flexible header, spacing, incomplete row, conflict and diagnostic tests passed')
from unittest.mock import patch, Mock
from local73 import select_answer,status
mock=Mock(); mock.json.return_value={'models':[{'name':'qwen2.5:1.5b'}]}
with patch('local73.requests.get',return_value=mock): assert status('qwen2.5:1.5b')[0]
for raw,expected in [('1',1),('[2]',2),('99%',None),('0',None),('4',None)]:
 mock.json.return_value={'response':raw}
 with patch('local73.requests.post',return_value=mock):
  assert select_answer('qwen','question',[(1,u,row),(1,u,head)])[0]==expected
print('V7.3 mocked Ollama connection and selection tests passed')

# Regression: SGST alone must not match a duration or ceiling.
for text in [sample, 'Reimbursement of 100% of the net SGST']:
 r=v70('Test',{u:text},'SGST reimbursement')[0]
 assert r['Rate'] and not r['Maximum ceiling'] and not r['Years'],r
r=v70('Test',{u:'Reimbursement of 100% of the net SGST. SGST capped at INR 20 crore. SGST for 5 years'},'SGST reimbursement')[0]
assert r['Maximum ceiling']=='INR 20 crore' and r['Years']=='5',r
print('V7.3.1 SGST regression tests passed')
from stamp74 import stamp_rows
sq='What are the stamp duty exemption benefits available to new manufacturing industrial units under the industrial policy of the selected state?'
assert stamp_rows({u:'[Page 68] eligible MSMEs will be entitled to 100 per cent stamp duty exemption within investment period'},sq,'Maharashtra')[0]['rate']=='100%'
assert stamp_rows({u:'[Page 12] [OCR transcription — verify against original] The industrial units under selected thrust sectors shall be eligible to claim 100% reimbursement of stamp duty and registration charges'},sq,'Gujarat')[0]['ocr']
assert not stamp_rows({u:'[Page 1] 100% electricity duty exemption. Stamp duty benefits available.'},sq,'Gujarat')
print('V7.4 scoped stamp duty tests passed')
