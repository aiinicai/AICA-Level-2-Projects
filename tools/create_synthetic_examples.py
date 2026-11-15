"""Create local, conspicuously synthetic GUI/format QA fixtures. No actual client data."""
from pathlib import Path
import sys,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from asset_model import Case,read_proposal
from signature_asset import select_image
from letterpad_asset import load_letterpad
from document_records import fingerprint
from income_intake import confirm_reconciliation
from report_export import export

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples';EX.mkdir(exist_ok=True)
first='''SAMPLE ASSOCIATES
Er. TEST VALUER (B.Tech Civil)
MCB-Lic. No. DEMO/MTP
VALUATION REPORT
PROPERTY: VACANT PLOT
Owner Name: ALPHA EXAMPLE S/O EXAMPLE FATHER
Ref No. DEMO/01
Date:07-11-2026
3. Address of the property: Test Road, Sample Village
7. Deed date/no.: DEMO-RECORD
8. Area of Plot:10 Marla
Rate:Rs.1,25,000/- Per Marla
Total Value:Rs.12,50,000/-
'''
second='''SAMPLE OTHER ARCHITECTS
VALUATION REPORT
PROPERTY: SEMI CONSTRUCTED RESIDENTIAL PLOT
Name of Owner:
ALPHA EXAMPLE S/O EXAMPLE FATHER
Ref No. DEMO/02
Date:07-11-2026
Total Value:Rs.15,00,000/-
Total Value:Rs.18,00,000/-
No final certified total identified in this synthetic conflict fixture.
'''
# Avoid the explanatory final line being mistaken for a financial label.
second=second.replace('No final certified total identified in this synthetic conflict fixture.','Two contradictory totals are deliberately supplied for review.')
(EX/'SYNTHETIC_valuation_first.txt').write_text(first,encoding='utf-8');(EX/'SYNTHETIC_valuation_second_ambiguous.txt').write_text(second,encoding='utf-8')
itr='Income Tax Return\nAssessment Year:2025-26\nFinancial Year:2024-25\nPAN:AAAAA0000A\nAcknowledgement Number:000000000000001\nDate of filing:22-Jul-2025\nTotal Income:500000\n'
comp='Computation of Total Income\nAssessment Year:2025-26\nGross Total Income:585110\nDeductions under Chapter VIA:85113\nTotal Income:499997\nAgricultural income:100000\nOther exempt income:20000\n'
(EX/'SYNTHETIC_ITR_2025_26.txt').write_text(itr);(EX/'SYNTHETIC_computation_2025_26.txt').write_text(comp)
sig=Image.new('RGB',(480,150),'white');draw=ImageDraw.Draw(sig);draw.line([(20,100),(70,40),(130,110),(200,50),(290,100),(400,60)],fill='navy',width=4);draw.text((20,120),'SAMPLE SIGNATURE - NOT FOR ISSUE',fill='navy');sig.save(EX/'SAMPLE_signature.jpg');sig.save(EX/'SAMPLE_signature.png')
pad=Image.new('RGB',(850,1200),'white');draw=ImageDraw.Draw(pad);draw.rectangle((0,0,849,125),fill='#173348');draw.text((40,45),'SAMPLE TEST LETTERPAD - NOT FOR ISSUE',fill='white');draw.rectangle((0,1120,849,1199),fill='#B9955B');font=ImageFont.load_default(size=110);draw.text((150,510),'SAMPLE',font=font,fill='#DCE2E8');draw.ellipse((120,300,730,1000),outline='#E4E9ED',width=8);draw.text((40,1125),'FULL PAGE FOOTER - SYNTHETIC TEST',font=ImageFont.load_default(size=26),fill='#173348');pad.save(EX/'SAMPLE_whole_page_letterpad.png')
c=Case();a=c.people[0];a.name='ALPHA EXAMPLE';a.fields.update(full_name=a.name,father_name='EXAMPLE FATHER',mother_name='EXAMPLE MOTHER',passport_number='X0000000',nationality='INDIAN',date_of_birth='01/01/1990',place_of_issue='TEST CITY',date_of_issue='01/01/2020',date_of_expiry='01/01/2030',address='DEMONSTRATION ADDRESS ONLY')
b=c.add_person();b.name='BETA EXAMPLE';b.title='Ms.';b.fields.update(full_name=b.name,passport_number='Y0000000',father_name='GAMMA EXAMPLE',spouse_name='EXAMPLE HUSBAND',address='SECOND DEMONSTRATION ADDRESS')
f=c.add_person('Family / owner');f.name='GAMMA EXAMPLE';f.fields['father_name']='OWNER OWN FATHER';c.confirm_relationship(b.id,f.id,'Father','SYNTHETIC reviewed source; not inferred from surname')
c.report=dict(currency='CAD - Canadian Dollars',country='Canada',rate='67.451234',cert_date='07.11.2026',statement_date='07-11-2026',engagement_date='07.11.2026',purpose='DEMONSTRATION ONLY - NOT FOR ISSUE',authority='TEST AUTHORITY',income_report_year='2025-26',rate_meta=dict(code='CAD',manual=True,requested_date='2026-11-07',effective_date='2026-11-07',as_of='SYNTHETIC manual sample - not a market quote',source='SYNTHETIC MANUAL SAMPLE'),print_layout=dict(paper='A4',orientation='Portrait',sections=['intro','certificate','immovable','movable','annual income'],margins_mm=dict(top=15,bottom=15,left=15,right=15)))
c.settings=dict(firm_name='SAMPLE TEST FIRM - NOT FOR ISSUE',firm_type='Demonstration',partner='SAMPLE SIGNER',designation='Test role',frn='DEMO FRN',mno='DEMO',place='TEST CITY',signature_enabled=True,signature_image=select_image(EX/'SAMPLE_signature.jpg'),letterpad=load_letterpad(EX/'SAMPLE_whole_page_letterpad.png','Whole-page letterpad'))
p=read_proposal(EX/'SYNTHETIC_valuation_first.txt','Assets');p.update(id='SYNTHETIC-DOCUMENT-1',path='examples/SYNTHETIC_valuation_first.txt',target_id=a.id,applied=True)
i=p['assets'][0];it=c.add_asset(i['category'],i['amount'],a.id,i['desc'],i['fields'],asset_name=i['asset_name']);it['source_evidence']=dict(document_id=p['id'],path=p['path'],sha256=p['sha256'],proposal=i);it['source_evidence']['applied_fingerprint']=fingerprint(it);c.documents.append(p)
c.add_asset('Cash in Hand',5000,b.id,'Cash held by selected applicant',asset_name='Cash in Hand')
c.add_asset('Bank Account (Savings / Current)',1200,f.id,'',dict(bank='SAMPLE',acno='DEMO-ACCOUNT',as_on='07-11-2026',evidence_type='Bank Statement'))
c.add_asset('Jewellery',70000,b.id,'',dict(details='Gold ornaments: 10 grams (synthetic)',valuer='SAMPLE JEWELLER',val_date='07-11-2026'),asset_name='Gold Valuation')
r1=c.add_income(a.id,{'total_income':500000},'ITR','examples/SYNTHETIC_ITR_2025_26.txt','2025-26',metadata=dict(pan='AAAAA0000A',acknowledgement='000000000000001',filing_date='22-07-2025',financial_year='2024-25'))
r2=c.add_income(a.id,{'total_income':499997,'agricultural_income':100000,'exempt_income':20000},'Computation','examples/SYNTHETIC_computation_2025_26.txt','2025-26')
confirm_reconciliation(c,a.id,'2025-26',dict(total_income=500000,agricultural_income=100000,exempt_income=20000),dict(total_income=r1['id'],agricultural_income=r2['id'],exempt_income=r2['id']),True,True,True)
c.save(EX/'SYNTHETIC_review_case_2.1.2.json')
for kind in ('xlsx','docx','pdf'):export(c,EX/('SYNTHETIC_report_2.1.2.'+kind),kind)
proof=copy.deepcopy(c);proof.report['print_layout']['sections']=['movable'];export(proof,EX/'SYNTHETIC_full_page_background_2.1.2.pdf','pdf')
print('Synthetic case + 3 reports + ambiguous import + signature + letterpad fixtures created.')
