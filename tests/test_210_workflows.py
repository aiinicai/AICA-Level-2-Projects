import copy,datetime,io,json,queue,zipfile
from pathlib import Path
from types import SimpleNamespace
from decimal import Decimal
import pytest,openpyxl
from PIL import Image,ImageDraw
import asset_model as model
import document_intake as intake
import report_export as report
from document_records import fingerprint,link_record,remove_document,undo_removal
from income_intake import extract_income,tax_sections,confirm_reconciliation,reconciliation_proposal
from signature_asset import select_image
from letterpad_asset import load_letterpad
from print_layout import layout_from,validate_print_area

class Var:
    def __init__(self,value=''):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value

@pytest.fixture
def case():
    c=model.Case();p=c.people[0];p.name='ALPHA EXAMPLE';p.fields['father_name']='EXAMPLE PARENT'
    c.settings=dict(firm_name='SAMPLE TEST FIRM',partner='TEST SIGNER',designation='Chartered Accountant',frn='DEMO FRN',mno='DEMO',place='Test City')
    c.report=dict(currency='CAD - Canadian Dollar (CAD$)',rate='67.451234',cert_date='07.11.2026',statement_date='07-11-2026',purpose='Demonstration only',authority='Review authority')
    return c

VALUATION='''SAMPLE ASSOCIATES
Engineer, Architect, Estimator, Valuer & Consultant
Er. TEST VALUER (B.Tech Civil)
MCB-Lic. No. DEMO/MTP
Ref no. DEMO/2139
Date:07-11-2026
VALUATION REPORT
PROPERTY: SEMI CONSTRUCTED RESIDENTIAL PLOT
OWNER NAME: ALPHA EXAMPLE S/O EXAMPLE PARENT
Name of Owner
:
Alpha Example S/o Example Parent
3. Address of the property: Test Road, Test Village
4. Locality: Semi constructed residential plot
7. Deed date/no.: Khata No.DEMO
8. Area of Plot:10 Marla
Value of land: Rs.10,00,000/-
Value of construction: Rs.2,50,000/-
Rate: Rs.1,25,000/- Per Marla
Total Value: Rs.12,50,000/-
Final Certified Total Value: Rs.12,00,000/-
'''

def test_final_certified_wins_components_rates_and_keeps_conflicts():
    p=intake.valuation_proposals(VALUATION);item=p['assets'][0]
    assert item['amount']==1200000 and item['asset_name']=='Semi Constructed Residential Plot'
    assert p['component_sum']==1250000 and p['warnings']
    assert item['fields']['valuer_name']=='TEST VALUER' and item['fields']['valuer_firm']=='SAMPLE ASSOCIATES'
    assert 'DEMO/MTP' in item['fields']['valuer_credentials'] and item['fields']['val_ref']=='DEMO/2139'
    assert model.norm(p['owner_candidate']['name'])=='alphaexample' and len(p['owner_candidate']['evidence'])>=3
    assert all('TEST VALUER'!=o['name'] for o in p['owner_candidates'])

@pytest.mark.parametrize('label',['Name of Owner','OWNER NAME','Property owned by','Owned by','Owner:','Applicant Name'])
def test_owner_label_anywhere(label):
    p=intake.valuation_proposals('VALUATION REPORT\nEr. WRONG PERSON (Architect)\nSome address\n'+label+' :\nALPHA EXAMPLE S/O EXAMPLE PARENT\nTotal Value: Rs.50,00,000')
    assert model.norm(p['owner_candidate']['name'])=='alphaexample'
    assert model.norm(p['owner_candidate']['father_name'])=='exampleparent'

def test_true_owner_conflict_is_not_silently_resolved():
    p=intake.valuation_proposals('VALUATION REPORT\nOwner name: ALPHA EXAMPLE\nName of owner: BETA EXAMPLE\nTotal Value: Rs.100000')
    assert not p['owner_candidate']['name'] and len(p['owner_candidates'])==2 and p['warnings']

def apply_doc(c,doc,monkeypatch,amount=None):
    import net_asset_report as ui
    item=doc['assets'][0];owner=c.people[0];label='selected'
    row=(Var(True),Var(item['category']),Var(str(item['amount'] if amount is None else amount)),Var(item.get('desc','')),{k:Var(v) for k,v in item.get('fields',{}).items()},Var(label),Var(item.get('asset_name','Test property')))
    fake=SimpleNamespace(case=c,selected_doc=lambda:doc,doc_target=Var(label),person_id=lambda _:owner.id,_proposal_assets=[row],_proposal_metadata={0:item},_select_person=lambda:None,refresh=lambda:None,status=Var())
    monkeypatch.setattr(ui.messagebox,'askyesno',lambda *a,**k:True)
    monkeypatch.setattr(ui.messagebox,'showwarning',lambda *a,**k:pytest.fail(str(a)))
    ui.App.apply_import(fake)
    return fake

def test_second_ambiguous_document_manual_review_preserves_first_asset(case,tmp_path,monkeypatch):
    first=tmp_path/'one.txt';first.write_text(VALUATION)
    d1=model.read_proposal(first,'Assets');d1.update(id='doc1',applied=False);apply_doc(case,d1,monkeypatch)
    saved=copy.deepcopy(case.items[0]);second=tmp_path/'two.txt';second.write_text('VALUATION REPORT\nProperty: Semi Constructed Residential Plot\nOwner name: ALPHA EXAMPLE\nTotal Value: Rs.10,00,000\nTotal Value: Rs.15,00,000')
    d2=model.read_proposal(second,'Assets');d2.update(id='doc2',applied=False)
    assert d2['assets'][0]['amount']=='' and len(d2['assets'][0]['amount_candidates'])>=2
    apply_doc(case,d2,monkeypatch,amount='1500000')
    assert len(case.items)==2 and case.items[0]==saved and case.items[1]['amount']==1500000
    assert case.items[0]['source_evidence']['sha256']!=case.items[1]['source_evidence']['sha256']
    assert case.items[1]['source_evidence']['document_id']=='doc2'

def test_unrecognized_asset_keeps_editable_draft(tmp_path):
    p=tmp_path/'asset.txt';p.write_text('Unfamiliar supporting statement; please review the original.')
    r=model.read_proposal(p,'Assets');assert len(r['assets'])==1 and r['assets'][0]['amount']==''

@pytest.mark.parametrize('relation',['Father','Mother','Spouse','Brother'])
def test_relationship_cross_applicant_in_actual_three_files(case,tmp_path,relation):
    second=case.add_person();second.name='BETA EXAMPLE';owner=case.add_person('Family / owner');owner.name='GAMMA EXAMPLE';owner.fields['father_name']='OWNER OWN FATHER'
    case.confirm_relationship(second.id,owner.id,relation,'Reviewed source relationship, not a shared surname')
    case.add_asset('Immovable Property',1250000,owner.id,'',dict(nature='Vacant Plot',area='10 Marla',location='TEST ROAD',valuer_name='TEST VALUER',valuer_firm='SAMPLE ASSOCIATES',valuer_credentials='LICENCE DEMO/MTP',val_date='07-11-2026',val_ref='DEMO/1'),asset_name='Vacant Plot')
    for kind in ('xlsx','docx','pdf'):
        p=tmp_path/('relations.'+kind);report.export(case,p,kind)
        text=file_text(p,kind)
        assert relation+' of Applicant 2 (BETA EXAMPLE)' in text
        assert relation+' of Applicant 1' not in text
        assert 'TEST VALUER' in text and 'SAMPLE ASSOCIATES' in text and 'DEMO/MTP' in text and 'DEMO/1' in text and '07-11-2026' in text
        assert 'OWNER OWN FATHER' in text

def file_text(path,kind):
    if kind=='xlsx':
        w=openpyxl.load_workbook(path,data_only=True);s='\n'.join(str(c.value) for sh in w for row in sh for c in row if c.value is not None);w.close();return s
    if kind=='docx':
        from docx import Document
        d=Document(path);return '\n'.join([p.text for p in d.paragraphs]+[c.text for t in d.tables for r in t.rows for c in r.cells])
    import pymupdf
    with pymupdf.open(path) as d:return ' '.join(' '.join(p.get_text() for p in d).split())

def test_unknown_relation_not_invented_and_self_automatic(case):
    owner=case.add_person('Family / owner');owner.name='BETA EXAMPLE';owner.fields['father_name']=case.people[0].fields['father_name']
    assert case.report_owner_relation(owner.id)=='Relationship not confirmed'
    assert case.report_owner_relation(case.people[0].id)=='Applicant'
    assert 'Brother' not in case.report_owner_relation(owner.id)

def test_bank_gold_template_phrases_and_bold_separate_blocks(case,tmp_path):
    p=case.people[0]
    case.add_asset('Bank Account (Savings / Current)',1200,p.id,'',dict(acno='DEMO-ACCOUNT',bank='SAMPLE',as_on='01-11-2026',evidence_type='Bank Statement'))
    case.add_asset('Fixed Deposit',300,p.id,'',dict(acno='DEMO-FD',bank='SAMPLE',as_on='02-11-2026'))
    case.add_asset('Jewellery',500,p.id,'',dict(details='Gold ornaments - reviewed 10 grams',valuer='SAMPLE JEWELLER',val_date='03-11-2026'),asset_name='Gold Valuation')
    for kind in ('xlsx','docx','pdf'):
        path=tmp_path/('movable.'+kind);report.export(case,path,kind);text=file_text(path,kind)
        for phrase in ['SAMPLE Bank A/c No. DEMO-ACCOUNT','As Per Bank Statement as on 01-11-2026','SAMPLE Bank Fd A/c No. DEMO-FD','As Per Bank Fd Certificate as on 02-11-2026','Gold Valuation','As Valued by SAMPLE JEWELLER as on 03-11-2026']:assert phrase in text
    w=openpyxl.load_workbook(tmp_path/'movable.xlsx');sh=w['movable']
    bank=next(c for row in sh for c in row if c.value=='SAMPLE Bank A/c No. DEMO-ACCOUNT');assert bank.font.bold
    note=next(c for row in sh for c in row if c.value=='(As Per Bank Statement as on 01-11-2026)');assert not note.font.bold
    gold=next(c for row in sh for c in row if c.value=='(As Valued by SAMPLE JEWELLER as on 03-11-2026)');assert not gold.font.bold
    assert sh['C13'].font.bold and sh['B9'].font.bold and sh.print_title_rows=='$9:$10'

def test_cached_excel_values_precise_rate_and_non_asset_income(case,tmp_path):
    p=case.people[0];case.add_asset('Cash in Hand',100,p.id,'Cash');case.add_asset('Jewellery',200,p.id,'Gold');case.add_asset('Immovable Property',1000,p.id,'Plot');case.add_asset('Bank Loan',50,p.id,'Loan')
    case.add_income(p.id,{'total_income':900000},'ITR','itr.txt','2025-26')
    path=tmp_path/'caches.xlsx';report.export(case,path,'xlsx');w=openpyxl.load_workbook(path,data_only=True)
    assert w['certificate']['E21'].value==1250 and w['certificate']['E28'].value==900000
    assert w['Sheet1']['C6'].value==67.451234
    expected=sum(report.round_excel(Decimal(str(a))/Decimal('67.451234'))*sign for a,sign in [(100,1),(200,1),(1000,1),(50,-1)])
    assert w['certificate']['F21'].value==expected
    assert w['movable']['C12'].value=='Mr. ALPHA EXAMPLE'
    f=openpyxl.load_workbook(path,data_only=False);assert f['movable']['E12'].data_type=='f'
    assert f['certificate']['E21'].value=='=E18+E19-E20' and f.calculation.fullCalcOnLoad

def image_fixture(tmp_path,extension='jpg'):
    p=tmp_path/('SAMPLE_signature.'+extension);im=Image.new('RGB',(320,100),'white');ImageDraw.Draw(im).text((10,40),'SAMPLE SIGNATURE - TEST ONLY',fill='navy');im.save(p);return p

@pytest.mark.parametrize('extension',['jpg','png'])
def test_signature_present_actual_three_formats_and_aspect(case,tmp_path,extension):
    image=image_fixture(tmp_path,extension);case.settings.update(signature_image=select_image(image),signature_enabled=True);case.add_asset('Cash in Hand',100,case.people[0].id,'Cash')
    for kind,folder in [('xlsx','xl/media/'),('docx','word/media/')]:
        path=tmp_path/('signed.'+kind);report.export(case,path,kind)
        with zipfile.ZipFile(path) as z:assert any(n.startswith(folder) for n in z.namelist())
    from docx import Document
    d=Document(tmp_path/'signed.docx');assert d.inline_shapes and abs(d.inline_shapes[0].width/d.inline_shapes[0].height-3.2)<.01
    path=tmp_path/'signed.pdf';report.export(case,path,'pdf')
    import pymupdf
    with pymupdf.open(path) as pdf:
        images=[i for page in pdf for i in page.get_images()];assert images and any(i[2]==320 and i[3]==100 for i in images)
    case.settings['signature_enabled']=False
    for kind,folder in [('xlsx','xl/media/'),('docx','word/media/')]:
        path=tmp_path/('unsigned.'+kind);report.export(case,path,kind)
        with zipfile.ZipFile(path) as z:assert not any(n.startswith(folder) for n in z.namelist())
    path=tmp_path/'unsigned.pdf';report.export(case,path,'pdf')
    with pymupdf.open(path) as pdf:assert not any(p.get_images() for p in pdf)

def linked_asset(c,doc,amount=100):
    item=c.add_asset('Cash in Hand',amount,c.people[0].id,'Cash');item['source_evidence']={'document_id':doc['id'],'path':doc['path']};item['source_evidence']['applied_fingerprint']=fingerprint(item);return item

@pytest.mark.parametrize('remove_records',[False,True])
def test_applied_removal_preserves_people_manual_assets_and_source(case,tmp_path,remove_records):
    source=tmp_path/'source.txt';source.write_text('PRIVATE SYNTHETIC EVIDENCE');doc={'id':'doc','path':str(source),'applied':True};case.documents=[doc]
    imported=linked_asset(case,doc);edited=linked_asset(case,doc,200);edited['details']='Manually edited later';manual=case.add_asset('Cash in Hand',300,case.people[0].id,'Manual')
    income=case.add_income(case.people[0].id,{'total_income':500},'ITR',str(source),'2025-26');link_record(income,doc)
    case.import_passport(case.people[0].id,dict(doc,passport_details={'full_name':'ALPHA EXAMPLE','mother_name':'REVIEWED MOTHER'}))
    person_before=case.people[0].name;bundle=remove_document(case,'doc',remove_records)
    assert not case.documents and source.read_text()=='PRIVATE SYNTHETIC EVIDENCE' and case.people[0].name==person_before and case.people[0].fields['mother_name']=='REVIEWED MOTHER'
    assert manual in case.items and edited in case.items
    assert len(case.items)==(2 if remove_records else 3)
    assert len(case.incomes)==(0 if remove_records else 1)
    assert len(case.people[0].passports)==(0 if remove_records else 1)
    assert all(i.get('source_evidence',{}).get('document_id')!='doc' for i in case.items)
    saved=tmp_path/'case.json';case.save(saved);loaded=model.Case.load(saved);assert loaded.to_dict()==case.to_dict()
    later=case.add_asset('Cash in Hand',400,case.people[0].id,'Later entry');undo_removal(case,bundle)
    assert len(case.items)==4 and later in case.items and edited['details']=='Manually edited later' and len(case.documents)==1


def test_edit_imported_asset_preserves_id_and_provenance(case):
    doc={'id':'d','path':'synthetic'};item=linked_asset(case,doc);original=item['id']
    case.add_asset('Cash in Hand',120,case.people[0].id,'Edited',index=0,asset_name='Named cash')
    assert case.items[0]['id']==original and case.items[0]['source_evidence']['document_id']=='d'
    assert case.items[0]['source_evidence']['applied_fingerprint']!=fingerprint(case.items[0])

def test_pending_ui_remove_and_undo_never_deletes_source(case,tmp_path,monkeypatch):
    import net_asset_report as ui
    source=tmp_path/'source.txt';source.write_text('SYNTHETIC');doc=dict(id='d',path=str(source),applied=False);case.documents=[doc];reset=[]
    fake=SimpleNamespace(_busy=False,case=case,pending=[doc],selected_doc=lambda:doc,_sync_case=lambda:None,_reset_doc_review=lambda:reset.append(True),refresh=lambda:None,status=Var())
    monkeypatch.setattr(ui.messagebox,'askyesno',lambda *a,**k:True)
    ui.App.remove_document(fake);assert reset and not fake.pending and not case.documents and source.exists()
    ui.App.undo_document_removal(fake);assert len(fake.pending)==1 and len(case.documents)==1 and source.exists()

@pytest.mark.parametrize('paper,orientation',[('A4','Portrait'),('Legal','Portrait'),('Legal','Landscape'),('Letter','Portrait')])
def test_real_page_dimensions_all_exporters(case,tmp_path,paper,orientation):
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash');case.report['print_layout']=dict(paper=paper,orientation=orientation,margins_mm=dict(top=17,bottom=18,left=19,right=20))
    layout=layout_from(case.report,case.settings)
    p=tmp_path/'layout.pdf';report.export(case,p,'pdf')
    import pymupdf
    with pymupdf.open(p) as pdf:
        assert abs(pdf[0].rect.width/72*25.4-layout['width_mm'])<.1 and abs(pdf[0].rect.height/72*25.4-layout['height_mm'])<.1
    p=tmp_path/'layout.docx';report.export(case,p,'docx')
    from docx import Document
    section=Document(p).sections[0];assert abs(section.page_width.mm-layout['width_mm'])<.1 and abs(section.page_height.mm-layout['height_mm'])<.1 and abs(section.left_margin.mm-19)<.1
    p=tmp_path/'layout.xlsx';report.export(case,p,'xlsx');w=openpyxl.load_workbook(p);assert w['movable'].page_setup.orientation==orientation.lower();assert abs(w['movable'].page_margins.left-19/25.4)<1e-9


def test_section_selection_ranges_and_actual_preview(case,tmp_path):
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash');case.report['print_layout']=dict(sections=['movable'],excel_scale='Actual size',excel_print_areas={'movable':'A9:E15'})
    p=tmp_path/'selected.xlsx';report.export(case,p,'xlsx');w=openpyxl.load_workbook(p)
    assert w['movable'].sheet_state=='visible' and all(s.sheet_state=='hidden' for s in w if s.title!='movable')
    assert w['movable'].print_area=="'movable'!$A$9:$E$15" and w['movable'].page_setup.scale==100
    p=tmp_path/'selected.pdf';report.export(case,p,'pdf')
    from preview_render import render_pdf_page,case_fingerprint
    result=render_pdf_page(p,0,75,tmp_path/'page.png');assert result['count']==1 and (tmp_path/'page.png').stat().st_size>1000
    first=case_fingerprint(case);case.report['print_layout']['paper']='Legal';assert first!=case_fingerprint(case)
    with pytest.raises(ValueError):render_pdf_page(p,5,75,tmp_path/'bad.png')
    with pytest.raises(ValueError):validate_print_area('A1:F9999',w['movable'])
    with pytest.raises(ValueError):validate_print_area('=IMPORTDATA("evil")',w['movable'])


def test_letterpad_portable_and_reserved_without_overlay(case,tmp_path):
    image=tmp_path/'SAMPLE_letterpad.png';im=Image.new('RGB',(700,1000),'white');draw=ImageDraw.Draw(im);draw.rectangle((0,0,699,100),fill='navy');draw.text((30,30),'SAMPLE LETTERPAD TEST ONLY',fill='white');draw.rectangle((0,950,699,999),fill='grey');im.save(image)
    case.settings['letterpad']=load_letterpad(image,'Whole-page letterpad');case.add_asset('Cash in Hand',100,case.people[0].id,'Cash')
    image.unlink();layout=layout_from(case.report,case.settings);assert layout['margins_mm']['top']>=34 and layout['margins_mm']['bottom']>=25
    for kind,prefix in [('xlsx','xl/media/'),('docx','word/media/')]:
        p=tmp_path/('letterpad.'+kind);report.export(case,p,kind)
        with zipfile.ZipFile(p) as z:assert len([n for n in z.namelist() if n.startswith(prefix)])>=1
    p=tmp_path/'letterpad.pdf';report.export(case,p,'pdf')
    import pymupdf
    with pymupdf.open(p) as pdf:assert all(any(image[2:4]==(700,1000) for image in page.get_images()) for page in pdf)
    from docx import Document
    d=Document(tmp_path/'letterpad.docx');assert d.sections[0].header.paragraphs[0]._p.xpath('.//wp:anchor[@behindDoc="1"]')
    case.settings['letterpad']['enabled']=False;p=tmp_path/'off.pdf';report.export(case,p,'pdf')
    with pymupdf.open(p) as pdf:assert not any(page.get_images() for page in pdf)


def test_pdf_page_range_is_not_excel_area(case,tmp_path):
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash');case.report['print_layout']=dict(pdf_page_range='1,3')
    p=tmp_path/'pages.pdf';report.export(case,p,'pdf')
    import pymupdf
    with pymupdf.open(p) as pdf:assert len(pdf)==2
    case.report['print_layout']['pdf_page_range']='999'
    with pytest.raises(ValueError,match='exceeds'):report.export(case,tmp_path/'bad.pdf','pdf')

# Structurally mirrors the actual newly supplied PDF, but all values/identifiers
# are synthetic. Two acknowledgement years + unrounded computation summary.
ACK1='INDIAN INCOME TAX RETURN ACKNOWLEDGEMENT\nAssessment\nYear\n2025-26\nPAN\nAAAAA0000A\nTotal Income\n1A\n5,00,000\nAdjusted Total Income under AMT, where applicable\n3\n0'
ACK2='INDIAN INCOME TAX RETURN ACKNOWLEDGEMENT\nAssessment\nYear\n2024-25\nTotal Income\n2\n6,00,000'
COMP='''Assessment Year :
2024-2025
Previous year : 2023-2024
Computation of Total Income (Old Regime Tax)
Income from Salary 400000 400000
Income from House Property 0 0
Income from Business or Profession 0 0
Income from Capital Gains 174600 174600
Income from Other Sources 10510 10510
Gross Total Income
585110
Less : Deduction under Chapter VIA
85113
Total Income
499997
Rounding off u/s 288A
500000
Agricultural income
100000
Other Exempt Income: 20000
'''

def test_actual_sample_structure_label_codes_zero_and_roundoff_evidence():
    sections=tax_sections([ACK1,ACK2,COMP,'Income From Other Sources\nTotal Income\n10510'])
    assert [(s['kind'],s['year']) for s in sections]==[('ITR','2025-26'),('ITR','2024-25'),('Computation','2024-25')]
    assert sections[0]['income']['total_income']==500000 and sections[1]['income']['total_income']==600000
    c=sections[2];assert c['income']['total_income']==499997 and c['income']['gross_total_income']==585110 and c['income']['house_property']==0
    assert c['income_metadata']['rounded_total_income']==500000 and c['income_evidence']['total_income']['page']==3
    assert c['income']['agricultural_income']==100000 and c['income']['exempt_income']==20000
    assert 'exempt_income' not in extract_income('Salary table\nTotal Exempted Amount\n20000')['income']


def test_agriculture_exempt_pair_requires_review_never_double_counts(case):
    pid=case.people[0].id;case.add_asset('Cash in Hand',100,pid,'Cash')
    a=case.add_income(pid,{'total_income':500000,'agricultural_income':100000},'ITR','itr.txt','2025-26')
    b=case.add_income(pid,{'total_income':499997,'agricultural_income':100000,'exempt_income':20000},'Computation','comp.txt','2025-26')
    with pytest.raises(ValueError,match='Review paired'):case.annual_rows()
    proposal=reconciliation_proposal(case,pid,'2025-26');assert proposal['pair_unique'] and 'total_income' in proposal['conflicts']
    with pytest.raises(ValueError,match='overlap'):confirm_reconciliation(case,pid,'2025-26',{'total_income':500000,'agricultural_income':100000,'exempt_income':20000},{},True,True,False)
    review=confirm_reconciliation(case,pid,'2025-26',{'total_income':500000,'agricultural_income':100000,'exempt_income':20000},{'total_income':a['id'],'agricultural_income':b['id'],'exempt_income':b['id']},True,True,True)
    assert review['report_total']==620000 and case.annual_rows()[0]['values']['total_income']==620000
    assert case.annual_rows()[0]['source_values']['total_income']==500000 and case.totals()['net']==100
    b['values']['exempt_income']=21000
    with pytest.raises(ValueError,match='changed'):case.annual_rows()


def test_year_person_pairing_unknown_values_no_cross_merge(case):
    a=case.people[0];b=case.add_person();b.name='BETA EXAMPLE'
    case.add_income(a.id,{'total_income':500},'ITR','a','2025-26');case.add_income(a.id,{'agricultural_income':100},'Computation','wrong-year','2024-25');case.add_income(b.id,{'agricultural_income':100},'Computation','wrong-person','2025-26')
    assert case.annual_rows()[0]['values']=={'total_income':500.0}
    proposal=reconciliation_proposal(case,a.id,'2025-26');assert not proposal['sources']['agricultural_income']
    result=confirm_reconciliation(case,a.id,'2025-26',{'total_income':500,'agricultural_income':'','exempt_income':''},{})
    assert result['values']['agricultural_income'] is None and result['report_total']==500


def test_reconciled_annual_template_metadata_all_formats(case,tmp_path):
    pid=case.people[0].id;case.add_asset('Cash in Hand',100,pid,'Cash')
    a=case.add_income(pid,{'total_income':500000},'ITR','ack.txt','2025-26',metadata={'pan':'AAAAA0000A','acknowledgement':'000000000000001','filing_date':'01-07-2026','financial_year':'2024-25'})
    b=case.add_income(pid,{'agricultural_income':100000,'exempt_income':20000},'Computation','computation.txt','2025-26')
    confirm_reconciliation(case,pid,'2025-26',{'total_income':500000,'agricultural_income':100000,'exempt_income':20000},{'total_income':a['id'],'agricultural_income':b['id'],'exempt_income':b['id']},True,True,True)
    for kind in ('xlsx','docx','pdf'):
        p=tmp_path/('annual.'+kind);report.export(case,p,kind);text=file_text(p,kind)
        for phrase in ['Pan: AAAAA0000A','As Per Income Tax Acknowledgement 000000000000001','Financial Year: 2024-25','Assessment Year: 2025-26','Additional agricultural income','Additional other exempt income','computation.txt']:assert phrase in text
    w=openpyxl.load_workbook(tmp_path/'annual.xlsx',data_only=True);assert w['certificate']['E28'].value==620000 and w['certificate']['E20'].value==100


def test_full_portable_json_roundtrip_secrets_and_ids(case,tmp_path):
    b=case.add_person();b.name='BETA EXAMPLE';case.confirm_relationship(case.people[0].id,b.id,'Brother','Reviewed specific source, not inferred')
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash');case.add_asset('Immovable Property',200,b.id,'Plot',asset_name='Named Plot')
    case.settings.update(signature_image=select_image(image_fixture(tmp_path)),signature_enabled=True,password='SECRET',icai_pwd='SECRET',otp='SECRET')
    case.documents=[dict(id='d',kind='Passport',path='missing/source.pdf',raw_text='SYNTHETIC RAW',review={'unknown':'retained'},password='SECRET')]
    case.report['rate_meta']={'code':'CAD','source':'Manual','as_of':'Reviewed date'};case.people[0].bold['passport']=False
    p=tmp_path/'portable.json';case.save(p);loaded=model.Case.load(p)
    assert 'SECRET' not in p.read_text() and loaded.to_dict()==case.to_dict()
    loaded.items[1]['asset_name']='Updated Named Plot';loaded.save(p);again=model.Case.load(p)
    assert again.items[1]['asset_name']=='Updated Named Plot' and again.items[0]['owner_id']==case.people[0].id and again.items[1]['owner_id']==b.id
    assert again.settings['signature_image']['data_base64'] and again.documents[0]['review']['unknown']=='retained'


def test_atomic_save_failure_original_unchanged(tmp_path):
    from file_ops import atomic_write
    p=tmp_path/'report.pdf';p.write_bytes(b'ORIGINAL')
    def fail(temp):Path(temp).write_bytes(b'PARTIAL');raise PermissionError('synthetic locked file')
    with pytest.raises(PermissionError):atomic_write(p,fail,'.pdf')
    assert p.read_bytes()==b'ORIGINAL' and list(tmp_path.iterdir())==[p]


def test_gui_save_reuses_active_path_and_save_as_prompts(case,tmp_path,monkeypatch):
    import net_asset_report as ui
    p=tmp_path/'active.json';other=tmp_path/'other.json';calls=[]
    fake=SimpleNamespace(case=case,client_file=str(p),_sync_case=lambda:None,status=Var())
    monkeypatch.setattr(ui.filedialog,'asksaveasfilename',lambda **kwargs:calls.append(kwargs) or str(other))
    ui.App.save_client(fake);assert p.exists() and not calls
    ui.App.save_client(fake,save_as=True);assert other.exists() and calls[0]['confirmoverwrite'] and fake.client_file==str(other)


def test_gui_export_error_always_queued_and_busy_cleared(case,tmp_path,monkeypatch):
    import net_asset_report as ui
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash');errors=[];destination=tmp_path/'missing'/'report.pdf'
    class ImmediateThread:
        def __init__(self,target,daemon):self.target=target
        def start(self):self.target()
    monkeypatch.setattr(ui.threading,'Thread',ImmediateThread);monkeypatch.setattr(ui.filedialog,'asksaveasfilename',lambda **kwargs:str(destination));monkeypatch.setattr(ui.messagebox,'showerror',lambda *a,**kwargs:errors.append(a));monkeypatch.setattr(ui.messagebox,'showwarning',lambda *a,**kwargs:pytest.fail(str(a)))
    fake=SimpleNamespace(case=case,_busy=False,_generation=1,_sync_case=lambda:None,status=Var(),jobs=queue.Queue(),after=lambda *a:None,_drain=lambda:None)
    ui.App.export(fake,'pdf');assert fake._busy
    ui.App._drain(fake);assert not fake._busy and errors and 'failed' in fake.status.get().lower() and not destination.exists()


def test_quote_orientation_timestamp_and_stale_guard():
    from currency_rates import parse_quote,validate_rate_for_report
    now=datetime.datetime.now(datetime.timezone.utc).timestamp();q=parse_quote({'result':'success','base_code':'CAD','rates':{'INR':67.451234},'time_last_update_unix':now},'CAD','https://public.example')
    assert q['rate']=='67.451234' and q['direction']=='INR per 1 CAD' and 'IST' in q['as_of']
    assert abs(Decimal(q['rate'])*(Decimal(1)/Decimal(q['rate']))-1)<Decimal('1e-20')
    r={'currency':'CAD - Canadian Dollar','rate':q['rate'],'rate_meta':q};validate_rate_for_report(r)
    with pytest.raises(ValueError):validate_rate_for_report(dict(r,currency='USD - Dollar'))
    old=copy.deepcopy(r);old['rate_meta']['quote_timestamp']=now-73*3600
    with pytest.raises(ValueError,match='72'):validate_rate_for_report(old)
    with pytest.raises(ValueError):parse_quote({'base_code':'INR','rates':{'INR':1},'date':'2026-11-07'},'CAD','test')


def test_manual_rate_invalidates_inflight_request_without_using_old_quote():
    import net_asset_report as ui
    fake=SimpleNamespace(_setting_rate=False,_loading_case=False,_rate_request=7,av={'currency':Var('CAD - Canadian Dollar')},rate_status=Var())
    ui.App._manual_rate_changed(fake)
    assert fake._rate_request==8 and fake.rate_meta['manual'] and fake.rate_meta['code']=='CAD'

class Element:
    def __init__(self,text='',value='',tag='button'):self.text=text;self.value=value;self.tag_name=tag;self.clicks=0
    def is_displayed(self):return True
    def is_enabled(self):return True
    def get_attribute(self,name):return self.value if name=='value' else ''
    def click(self):self.clicks+=1
    def clear(self):self.value=''
    def send_keys(self,value):self.value+=value


def test_udin_explicit_otp_guard_no_final_submit():
    from udin_assist import UdinSession
    send=Element('Send OTP');submit=Element('Generate UDIN');clock=[0]
    driver=SimpleNamespace(find_elements=lambda by,locator:[send,submit])
    session=UdinSession(driver,waiter=lambda check,timeout:check() or (_ for _ in ()).throw(RuntimeError('not ready')),clock=lambda:clock[0])
    with pytest.raises(ValueError):session.request_otp()
    session.filled=True;session.request_otp();assert send.clicks==1 and submit.clicks==0
    with pytest.raises(ValueError):session.request_otp()
    clock[0]=61;session.request_otp();assert send.clicks==2 and submit.clicks==0


def test_udin_timeout_attempt_not_retried_and_missing_readiness(case):
    from udin_assist import UdinSession,payload_from_case
    session=UdinSession(SimpleNamespace(find_elements=lambda *args:[]),waiter=lambda *args:(_ for _ in ()).throw(RuntimeError('timeout')),clock=lambda:5);session.filled=True
    with pytest.raises(RuntimeError):session.request_otp()
    with pytest.raises(ValueError,match='already attempted'):session.request_otp()
    data,missing=payload_from_case(case);assert missing and 'At least one reviewed asset' in missing
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash');data,missing=payload_from_case(case);assert not missing and data['mov_total']=='100.00' and data['imm_total']=='0.00'
    assert not any(k in data for k in ('password','otp','mrn','pwd'))


def test_udin_unique_success_result_read_only():
    from udin_assist import UdinSession
    body=Element('UDIN generated successfully\nUDIN: 123456ABCDEFGHIJKL')
    # 18-character synthetic identifier, not a real generated UDIN.
    body.text='UDIN generated successfully\nUDIN: 123456ABCDEFGHIJKL'
    session=UdinSession(SimpleNamespace(find_element=lambda *args:body));assert session.read_generated_udin()=='123456ABCDEFGHIJKL'
    body.text='Enter OTP to generate UDIN'
    with pytest.raises(ValueError):session.read_generated_udin()


def test_udin_fake_dom_field_mapping_and_selector_mismatch():
    from udin_assist import UdinSession,NAV
    nav=Element('Generate UDIN');frn=Element(tag='input');cert=Element(tag='input');date=Element(tag='input');desc=Element(tag='textarea');options=[Element('DEMOFRN - TEST FIRM'),Element('Net Worth Certificate')];visited=[]
    def find(by,locator):
        if locator==NAV:return [nav]
        if by=='id':return {'FRN':[frn],'certficateType':[cert]}.get(locator,[])
        if 'mat-option' in locator:return options
        if 'dd-mm-yyyy' in locator:return [date]
        if 'textarea' in locator:return [desc]
        return []
    driver=SimpleNamespace(get=lambda url:visited.append(url),find_elements=find)
    session=UdinSession(driver,waiter=lambda check,timeout:check() or (_ for _ in ()).throw(RuntimeError('missing expected control')))
    errors=session.open_and_fill(dict(frn='DEMOFRN',cert_date='07-11-2026',description='SYNTHETIC',imm_total='100',mov_total='200'))
    assert visited==['https://udin.icai.org/ICAI/login'] and frn.value=='DEMOFRN' and cert.value=='net worth' and date.value=='07-11-2026' and desc.value=='SYNTHETIC'
    assert errors and not session.filled  # Missing numerical rows is explicit, never silent.
    assert all(e.clicks==1 for e in options)


def test_ui_source_accessible_controls_and_no_local_secret_fields():
    import net_asset_report as ui
    source=Path(ui.__file__).read_text()
    for phrase in ['Remove document','Undo removal','Asset name','Value candidates','Preview final PDF','Choose JPEG / PNG signature','Request OTP (after review)','Report assessment year']:assert phrase in source
    assert all(k not in ('icai_id','icai_pwd') for k,_ in ui.App.SETTINGS_FIELDS)

@pytest.mark.parametrize('country,code',[('Canada','CAD'),('Australia','AUD'),('United States','USD'),('United Kingdom','GBP'),('Germany','EUR'),('New Zealand','NZD'),('Singapore','SGD'),('United Arab Emirates','AED')])
def test_country_mapping_preserves_original_supported_currencies(country,code):
    from currency_rates import country_code
    import legacy_engine
    assert country_code(country)==code and any(s.startswith(code+' - ') for s in legacy_engine.CURRENCIES)


def test_historical_quote_exact_and_weekend_require_explicit_approval():
    from currency_rates import parse_historical_quote,validate_rate_for_report
    q=parse_historical_quote({'base':'CAD','quote':'INR','rate':67.123456,'date':'2026-11-06'},'CAD','07-11-2026','https://public.example?date=2026-11-07')
    assert q['requested_date']=='2026-11-07' and q['effective_date']=='2026-11-06' and q['requires_date_review']
    report_data={'currency':'CAD - Canadian Dollars','rate':q['rate'],'statement_date':'07-11-2026','rate_meta':q}
    with pytest.raises(ValueError,match='review'):validate_rate_for_report(report_data)
    q['date_reviewed']=True;validate_rate_for_report(report_data)
    report_data['statement_date']='06-11-2026'
    with pytest.raises(ValueError,match='date changed'):validate_rate_for_report(report_data)


def test_future_date_rejected_without_network_and_valid_past_allowed():
    from currency_rates import fetch_quote_for_date,parse_historical_quote,IST
    future=datetime.datetime.now(IST).date()+datetime.timedelta(days=1);calls=[]
    with pytest.raises(ValueError,match='Future FX'):fetch_quote_for_date('CAD',future,opener=lambda *a,**k:calls.append(a))
    assert not calls
    quote=parse_historical_quote({'base':'CAD','quote':'INR','rate':55,'date':'2020-01-02'},'CAD','02-01-2020','public historical source')
    assert quote['historical'] and quote['date_reviewed']
    from currency_rates import validate_rate_for_report
    validate_rate_for_report({'currency':'CAD - Canadian Dollars','rate':'55','statement_date':'02-01-2020','rate_meta':quote})


def test_date_fetch_requests_exact_day_no_current_fallback():
    from currency_rates import fetch_quote_for_date
    captured=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self):return b'{"date":"2020-01-02","base":"CAD","quote":"INR","rate":55.1234}'
    def opener(request,timeout):captured.append((request.full_url,timeout));return Response()
    quote=fetch_quote_for_date('CAD','02-01-2020',opener=opener)
    assert 'date=2020-01-02' in captured[0][0] and 'latest' not in captured[0][0] and quote['rate']=='55.1234' and captured[0][1]==12
    with pytest.raises(ValueError):fetch_quote_for_date('CAD','nonsense',opener=opener)


def test_source_filing_month_name_is_preserved_in_normalized_metadata():
    result=extract_income('Income Tax Return\nAssessment Year:2025-26\nDate of filing: 22-Jul-2025\nTotal Income:500000')
    assert result['income_metadata']['filing_date']=='22-07-2025'


@pytest.mark.parametrize('profiles,selection',[({'A':{'firm_name':'A'},'B':{'firm_name':'B'}},'B'),({'A':{'firm_name':'A'}},'A')])
def test_remove_ca_only_selected_saved_profile_current_snapshot_unchanged(tmp_path,monkeypatch,profiles,selection):
    import net_asset_report as ui
    target=tmp_path/'ca_profiles.json';source=tmp_path/'shared_signature.png';source.write_bytes(b'SYNTHETIC SHARED FILE');questions=[]
    monkeypatch.setattr(ui.engine,'PROFILES_FILE',str(target));monkeypatch.setattr(ui.messagebox,'askyesno',lambda *a,**k:questions.append(a) or True)
    current={'firm_name':'CURRENT CASE SNAPSHOT','partner':'CURRENT SIGNER'}
    fake=SimpleNamespace(ca_profiles=copy.deepcopy(profiles),profile_cb=Var(selection),case=SimpleNamespace(settings=copy.deepcopy(current)),sv={'firm_name':Var(current['firm_name'])},status=Var(),update_profile_dropdown=lambda:None)
    ui.App.remove_ca_profile(fake)
    assert selection in questions[0][1] and selection not in fake.ca_profiles and fake.case.settings==current and fake.sv['firm_name'].get()==current['firm_name'] and source.exists()
    assert fake.profile_cb.get()=='' and json.loads(target.read_text())==fake.ca_profiles


def test_remove_ca_no_selection_and_cancel_do_not_touch_storage(tmp_path,monkeypatch):
    import net_asset_report as ui
    messages=[];monkeypatch.setattr(ui.messagebox,'showinfo',lambda *a,**k:messages.append(a));monkeypatch.setattr(ui.messagebox,'askyesno',lambda *a,**k:False)
    fake=SimpleNamespace(ca_profiles={'A':{'firm_name':'A'}},profile_cb=Var(''))
    ui.App.remove_ca_profile(fake);assert messages
    fake.profile_cb.set('A');ui.App.remove_ca_profile(fake);assert fake.ca_profiles=={'A':{'firm_name':'A'}}


def test_reset_doc_review_does_not_require_nonexistent_checkbox():
    import net_asset_report as ui
    class Raw:
        def configure(self,**k):pass
        def delete(self,*a):pass
    fake=SimpleNamespace(doc_kind=Var('Assets'),doc_target=Var('A'),doc_warning=Var(),doc_fields=SimpleNamespace(winfo_children=lambda:[]),raw=Raw())
    ui.App._reset_doc_review(fake);assert fake._active_doc_id is None and fake._proposal_assets==[] and fake.doc_kind.get()==''


def test_original_source_udin_create_no_window_service_mock(monkeypatch):
    import sys,types,subprocess,udin_assist
    captured={}
    class Service:
        def __init__(self,**kwargs):self.creation_flags=0
    class Options:
        def add_argument(self,value):pass
    webdriver=SimpleNamespace(ChromeOptions=Options,Chrome=lambda **kwargs:captured.update(kwargs) or 'DRIVER')
    monkeypatch.setitem(sys.modules,'selenium',SimpleNamespace(webdriver=webdriver));monkeypatch.setitem(sys.modules,'selenium.webdriver.chrome.service',SimpleNamespace(Service=Service))
    monkeypatch.setattr(udin_assist,'os',SimpleNamespace(name='nt',devnull='/dev/null'));monkeypatch.setattr(subprocess,'CREATE_NO_WINDOW',0x08000000,raising=False)
    assert udin_assist.create_driver()=='DRIVER' and captured['service'].creation_flags==0x08000000


def test_credit_app_only_and_not_implicit_signer(case,tmp_path):
    import net_asset_report as ui
    assert ui.APP_CREDIT=='Made by CA LOVE KUMAR · MB: 88378-83498'
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash')
    for kind in ('xlsx','docx','pdf'):
        p=tmp_path/('no_implicit_credit.'+kind);report.export(case,p,kind);assert 'Made by CA LOVE KUMAR' not in file_text(p,kind)


def test_udin_full_original_figure_mapping_and_actual_denomination_fake_dom():
    from udin_assist import UdinSession,NAV
    nav=Element('Generate UDIN');frn=Element(tag='input');cert=Element(tag='input');date=Element(tag='input');description=Element(tag='textarea');send=Element('Send OTP');final=Element('Generate')
    actual=Element('Actual');options=[Element('DEMOFRN TEST FIRM'),Element('Net Worth'),actual]
    particulars=[Element(tag='input'),Element(tag='input')];figures=[Element(tag='input'),Element(tag='input')]
    containers=[Element(),Element()];denominators=[Element(tag='ng-select'),Element(tag='ng-select')]
    for index in range(2):
        denominators[index].find_elements=lambda *args,i=index:[containers[i]]
        row=SimpleNamespace(find_elements=lambda *args,i=index:[denominators[i]])
        particulars[index].find_elements=lambda *args,r=row:[r]
    def find(by,locator):
        if locator==NAV:return [nav]
        if by=='id':return {'FRN':[frn],'certficateType':[cert]}.get(locator,[])
        if 'mat-option' in locator:return options
        if 'dd-mm-yyyy' in locator:return [date]
        if 'mat-datepicker-content' in locator:return []
        if 'textarea' in locator:return [description]
        if locator.startswith('//input[') and "='particulars'" in locator:return particulars
        if locator.startswith('//input[') and "='figures in inr'" in locator:return figures
        if locator.startswith('//button'):return [send,final]
        return []
    driver=SimpleNamespace(get=lambda url:None,find_elements=find)
    session=UdinSession(driver,waiter=lambda check,timeout:check() or (_ for _ in ()).throw(RuntimeError('selector missing')))
    failures=session.open_and_fill({'frn':'DEMOFRN','cert_date':'07-11-2026','description':'SYNTHETIC CERTIFICATE','imm_total':'1250000.00','mov_total':'5000.00'})
    assert not failures and session.filled and figures[0].value=='1250000.00' and figures[1].value=='5000.00'
    assert particulars[0].value=='Total Immovable Assets' and particulars[1].value=='Total Movable Assets' and actual.clicks==2
    assert send.clicks==0 and final.clicks==0
    session.request_otp();assert send.clicks==1 and final.clicks==0


def test_complete_passport_inputs_retained_outside_excel_print_area(case,tmp_path):
    p=case.people[0];p.fields.update(mother_name='SYNTHETIC MOTHER',place_of_issue='TEST ISSUE CITY',date_of_issue='01/01/2020',date_of_expiry='01/01/2030')
    case.add_asset('Cash in Hand',100,p.id,'Cash');path=tmp_path/'passport_meta.xlsx';report.export(case,path,'xlsx');w=openpyxl.load_workbook(path)
    sh=w['Sheet1'];assert sh.sheet_state=='hidden' and sh.print_area.endswith('$I$16')
    assert any(c.value=='SYNTHETIC MOTHER' and c.column>=11 for row in sh for c in row)
    assert any(c.value=='TEST ISSUE CITY' and c.column>=11 for row in sh for c in row)


def test_unselected_itr_does_not_create_empty_income_report(case,tmp_path):
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash');case.add_income(case.people[0].id,{'total_income':500000},'ITR','itr.txt','2025-26',include=False)
    path=tmp_path/'no_empty_annual.xlsx';report.export(case,path,'xlsx');w=openpyxl.load_workbook(path);assert 'annual income' not in w.sheetnames
    path=tmp_path/'no_empty_annual.pdf';report.export(case,path,'pdf');assert 'DETAIL OF ANNUAL INCOME' not in file_text(path,'pdf')


def test_gold_report_not_immovable_no_fabricated_weight_and_rate_not_total(tmp_path):
    p=tmp_path/'gold.txt';p.write_text('SAMPLE JEWELLERS\nGOLD VALUATION REPORT\nOwner name: ALPHA EXAMPLE\nDate:07-11-2026\nPurity:22K\nNet weight:10 grams\nRate:Rs.7,000/- per gram\nTotal Value:Rs.70,000/-')
    proposal=model.read_proposal(p,'Assets');item=proposal['assets'][0]
    assert item['category']=='Jewellery' and item['amount']==70000 and item['asset_name']=='Gold Valuation'
    assert item['fields']['valuer']=='SAMPLE JEWELLERS' and item['fields']['val_date']=='07-11-2026' and item['fields']['purity']=='22K' and item['fields']['net_weight']=='10 grams'
    assert any(c['score']<0 and c['amount']==7000 for c in item['amount_candidates'])
    p.write_text('GOLD VALUATION REPORT\nTotal Value:Rs.70,000')
    item=model.read_proposal(p,'Assets')['assets'][0]
    assert '____' not in item['fields']['details'] and 'net_weight' not in item['fields']


def test_historical_rate_tampering_requires_manual_review():
    from currency_rates import parse_historical_quote,validate_rate_for_report
    quote=parse_historical_quote({'base':'CAD','quote':'INR','date':'2020-01-02','rate':'55'},'CAD',datetime.date(2020,1,2),'SYNTHETIC')
    with pytest.raises(ValueError,match='provenance'):
        validate_rate_for_report({'currency':'CAD - Canadian Dollars','rate':'99','statement_date':'02-01-2020','rate_meta':quote})


def test_certificate_parallel_foreign_and_separate_income_actual_files(case,tmp_path):
    from docx import Document
    import pymupdf
    from report_documents import summary_rows,income_summary
    case.report.update(currency='CAD - Canadian Dollars',rate='50')
    case.add_asset('Cash in Hand',5000,case.applicants[0].id,'Cash held by applicant')
    case.add_income(case.applicants[0].id,{'total_income':600000},'ITR','synthetic.txt','2025-26')
    content=report.report_content(case)
    assert summary_rows(case,content)[-1][1]==content['nw']
    assert income_summary(case,content)[0][1]==600000
    path=tmp_path/'actual.docx';report.export(case,path,'docx');document=Document(path)
    summary=document.tables[0]
    assert len(summary.columns)==3 and summary.rows[0].cells[2].text=='Amount (CAD)'
    assert any('NOT included in net assets' in row.cells[0].text for row in summary.rows)
    path=tmp_path/'actual.pdf';report.export(case,path,'pdf')
    with pymupdf.open(path) as pdf:
        text='\n'.join(p.get_text() for p in pdf)
    assert 'Amount (CAD)' in text and 'NOT included in net assets' in text


def test_secret_key_variants_excluded_without_erasing_passport_fields():
    from asset_model import strip_secrets
    cleaned=strip_secrets({'passport_number':'SYNTHETIC','old_passport_number':'DEMO','nested':{'udin_otp':'secret','selenium-login-password':'secret','api_key':'secret','safe':'reviewed'}})
    assert cleaned=={'passport_number':'SYNTHETIC','old_passport_number':'DEMO','nested':{'safe':'reviewed'}}


def test_excel_letterpad_first_page_flag_skips_first_selected_sheet(case,tmp_path):
    from letterpad_asset import load_letterpad
    from PIL import Image
    path=tmp_path/'pad.png';Image.new('RGB',(500,100),'navy').save(path)
    case.add_asset('Cash in Hand',5000,case.applicants[0].id,'Cash held by applicant')
    case.settings['letterpad']=load_letterpad(path)
    case.settings['letterpad']['include_first_page']=False
    path=tmp_path/'report.xlsx';report.export(case,path,'xlsx');w=openpyxl.load_workbook(path)
    assert not w['intro']._images and w['certificate']._images
