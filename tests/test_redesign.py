import ast,copy,json,math,sys,zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from asset_model import Case,Person,PASSPORT_FIELDS,parse_passport,read_proposal,read_workbook,money,table_assets
import report_export as rex
import legacy_engine as legacy
import openpyxl

@pytest.fixture
def case():
    c=Case();p=c.people[0];p.name='Example Applicant';p.fields.update(full_name=p.name,father_name='Example Father',mother_name='Example Mother',address='Synthetic address only')
    c.report.update(currency='CAD - Canadian Dollars',rate='60',statement_date='07-11-2026',purpose='Study Visa',cert_date='07.11.2026',engagement_date='07.11.2026')
    c.settings.update(firm_name='Example Firm',partner='Example CA',firm_type='Chartered Accountants',frn='TEST',mno='TEST',designation='Partner',place='Example City')
    return c

PASSPORT='''Type: P
Country code: IND
Surname: EXAMPLE
Given Names: ALPHA
Passport No: X0000000
Nationality: INDIAN
Sex: F
Date of Birth: 01.01.1990
Place of Birth: EXAMPLE CITY
Date of Issue: 01.01.2020
Place of Issue: EXAMPLE OFFICE
Date of Expiry: 01.01.2030
Name of Father / Legal Guardian: EXAMPLE FATHER
Name of Mother: EXAMPLE MOTHER
Name of Spouse: EXAMPLE HUSBAND
Address:
House 100, Example Road
Example District
Example State 000000
Old Passport No: Z0000000
Old Date of Issue: 01.01.2010
Old Place of Issue: EXAMPLE OLD OFFICE
File No: SYNTHETICFILE
Personal Number: SYNTHETIC
Observations: Synthetic example only
Other unrecognized endorsement
'''

def test_baseline_both_uploaded_sources_compile():
    # Packaged compatibility engine retains all old export and category capabilities.
    for name in ('build_content','export_excel','export_word','export_pdf','read_document_text','extract_document_proposals','find_tesseract'):
        assert callable(getattr(legacy,name))
    assert len(legacy.CATS)==13

def test_complete_passport_schema():
    p=parse_passport(PASSPORT)
    assert set(PASSPORT_FIELDS)<=set(p['passport_details'])
    for k in ('father_name','mother_name','spouse_name','file_number','passport_number','date_of_birth','old_passport_number','old_date_of_issue','old_place_of_issue','personal_number'):
        assert p['passport_details'][k]
    assert 'Example State' in p['passport_details']['address']
    assert 'Old Passport' not in p['passport_details']['address']
    assert p['passport_details']['date_of_issue']=='01.01.2020'
    assert p['text']==PASSPORT
    assert p['evidence']['father_name']

@pytest.mark.parametrize('field',list(PASSPORT_FIELDS))
def test_every_passport_field_retained_per_person(field):
    c=Case();a=c.people[0];b=c.add_person();proposal=dict(path='synthetic',passport_details={field:'test value'},text='raw untouched')
    c.import_passport(b.id,proposal)
    assert b.fields[field]=='test value'
    assert not a.fields.get(field)
    assert b.passports[0]['raw_text']=='raw untouched'

def test_two_passports_route_without_overwrite(case):
    a=case.people[0];b=case.add_person();b.name='Second Example'
    proposal=parse_passport(PASSPORT);proposal['path']='one.txt'
    case.import_passport(a.id,proposal)
    other=copy.deepcopy(proposal);other['passport_details']['passport_number']='Y0000000'
    case.import_passport(b.id,other)
    assert a.fields['passport_number']=='X0000000';assert b.fields['passport_number']=='Y0000000'
    assert len(a.passports)==len(b.passports)==1
    back=dict(other);back['passport_details']=dict(other['passport_details'],passport_number='N0000000')
    conflicts=case.import_passport(a.id,back)
    assert 'passport_number' in conflicts;assert a.fields['passport_number']=='X0000000';assert len(a.passports)==2
    case.import_passport(a.id,back,True);assert a.fields['passport_number']=='N0000000'

def test_unknown_fields_not_lost():
    c=Case();p=parse_passport('Unrecognized: unusual data\nPassport No: X0000000')
    c.import_passport(c.people[0].id,p)
    assert p['unknown_fields'][0]['text']=='Unrecognized: unusual data'
    assert c.people[0].passports[0]['unknown_fields']==p['unknown_fields']

def test_no_empty_passport_import():
    c=Case()
    with pytest.raises(ValueError):c.import_passport(c.people[0].id,parse_passport('nothing'))

def test_female_husband_precedes_father(case):
    p=case.people[0];p.title='Ms.';p.fields['spouse_name']='Example Husband'
    assert case.parent_line(p)=='W/o Sh. Example Husband'
    p.use_father=True;assert case.parent_line(p)=='D/o Sh. Example Father'

def test_exact_template_discrepancies(case):
    p=case.people[0];p.title='Mrs.';p.fields['spouse_name']='Example Husband';p.use_father=True
    assert case.parent_line(p)=='S/o Sh. Example Father' # literal supplied Excel rule, documented
    p.use_father=False;case.formula_mode='single';assert case.parent_line(p)=='S/o Sh. Example Father'
    case.formula_mode='double';assert case.parent_line(p)=='W/o Sh. Example Husband'

def test_relationships_only_reviewed(case):
    a=case.people[0];f=case.add_person('Family / owner');f.name=a.fields['father_name']
    candidate=next(r for r in case.relationship_candidates() if r['relation']=='Father')
    assert not candidate['confirmed'];assert case.owner_relation(f.id,a.id)=='Relationship not confirmed'
    case.confirm_relationship(a.id,f.id,'Father','Verified father field on source passport')
    assert case.owner_relation(f.id,a.id)=='Father of Applicant'

def test_sibling_not_guessed_brother(case):
    b=case.add_person();b.name='Second Example';b.fields['father_name']=case.people[0].fields['father_name']
    candidates=case.relationship_candidates();assert any(r['relation']=='Sibling' for r in candidates)
    assert not any(r['relation']=='Brother' for r in candidates)
    assert case.relationships==[]

def test_no_name_match_no_relation(case):
    x=case.add_person();x.name='Completely Different'
    assert not case.relationship_candidates()

@pytest.mark.parametrize('value',['nan','NaN','inf','-inf','not money','',None,'-1','0'])
def test_asset_amount_validation(case,value):
    with pytest.raises(ValueError):case.add_asset('Cash in Hand',value,case.people[0].id,'Cash')

def test_cash_and_inline_assets(case):
    p=case.people[0]
    cash=case.add_asset('Cash in Hand','1,000.50',p.id,'Cash self declaration')
    prop=case.add_asset('Immovable Property',2000,p.id,'Residential plot')
    case.add_asset('Bank Loan',100,p.id,'Outstanding loan')
    assert cash['owner_id']==p.id;assert prop['section']=='A'
    assert case.totals()['net']==money('2900.50')
    assert case.totals()['C']==100

def test_asset_identity_is_not_silently_assigned(case):
    with pytest.raises(StopIteration):case.add_asset('Cash in Hand',100,'unknown','Cash')

def test_other_asset_requires_particulars(case):
    with pytest.raises(ValueError):case.add_asset('Other Asset',100,case.people[0].id)

def test_itr_visibility_and_comparison_routing(case):
    a=case.people[0];b=case.add_person();b.name='Other'
    assert not case.has_itr
    case.add_income(a.id,{'total_income':100},'Computation','c','2025-26')
    assert not case.has_itr;assert case.income_comparison()==[]
    case.add_income(b.id,{'total_income':100},'ITR','i','2025-26')
    assert case.has_itr;assert case.income_comparison()==[]
    case.add_income(a.id,{'total_income':100},'ITR','i','2024-25')
    assert case.income_comparison()==[]
    case.add_income(a.id,{'total_income':90},'ITR','i','2025-26')
    assert len(case.income_comparison())==1
    assert 'Difference' in case.income_comparison()[0][-1]

def test_income_not_net_assets(case):
    p=case.people[0];case.add_asset('Cash in Hand',50,p.id,'Cash');before=case.totals()
    case.add_income(p.id,{'total_income':99999},'ITR','synthetic','2025-26')
    assert case.totals()==before

def test_duplicate_itr_does_not_double_count(case):
    p=case.people[0]
    for _ in range(2):case.add_income(p.id,{'total_income':100},'ITR','i','2025-26')
    with pytest.raises(ValueError):case.annual_rows()

def test_computation_never_in_annual(case):
    case.add_income(case.people[0].id,{'total_income':100},'Computation','c','2025-26',True)
    assert case.annual_rows()==[]

def test_multiple_assessment_years_not_summed(case):
    for year in ('2024-25','2025-26'):case.add_income(case.people[0].id,{'total_income':100},'ITR','i',year)
    with pytest.raises(ValueError):case.annual_rows()

def test_case_roundtrip(case,tmp_path):
    p=case.people[0];case.import_passport(p.id,dict(parse_passport(PASSPORT),path='synthetic'))
    b=case.add_person();b.name='Second';case.add_asset('Cash in Hand',100,b.id,'Cash')
    case.confirm_relationship(p.id,b.id,'Brother','User reviewed source')
    path=tmp_path/'case.json';case.save(path);loaded=Case.load(path)
    assert loaded.to_dict()==case.to_dict()

def test_old_client_migration():
    old=dict(applicant=dict(name='Legacy Example',title='Ms.',co_name='Second Legacy',co_passport='Y0000000'),items=[])
    c=Case.from_dict(old);assert len(c.applicants)==2;assert c.people[1].fields['passport_number']=='Y0000000'

def test_template_inputs_outside_print_area(tmp_path):
    w=openpyxl.Workbook();s=w.active;s.title='Passport';s['A1']='Surname';s['B1']='EXAMPLE';s.print_area='A1:B1'
    s['A50']='Name of Mother';s['B50']='EXAMPLE MOTHER';s['A60']='File No';s['B60']='SYNTHETIC';s['D80']='=1+2'
    s['A50'].font=openpyxl.styles.Font(bold=True);path=tmp_path/'all.xlsx';w.save(path)
    pages,cells=read_workbook(path)
    assert any(c['cell']=='D80' and c['formula']=='=1+2' and c['value'] is None for c in cells)
    prop=read_proposal(path,'Passport');assert prop['passport_details']['mother_name']=='EXAMPLE MOTHER'
    assert prop['passport_details']['file_number']=='SYNTHETIC';assert prop['warnings']

def test_csv_multi_asset_import(tmp_path):
    path=tmp_path/'assets.csv';path.write_text('Category,Particulars,Amount,Owner\nCash in Hand,Cash,100,Example\nImmovable Property,Plot,200,Second\nOther Asset,Total,300,Ignored\n')
    p=read_proposal(path,'Assets');assert len(p['assets'])==2;assert p['assets'][1]['amount']==200

def test_original_annexure_columns(tmp_path):
    w=openpyxl.Workbook();s=w.active;s.title='movable';s['B12']='Cash in Hand';s['D12']=100;s['B16']='Bank balance';s['D16']=200;s['B20']='Total movable assets';s['D20']=300
    path=tmp_path/'a.xlsx';w.save(path);p=read_proposal(path,'Assets');assert len(p['assets'])==2;assert sum(i['amount'] for i in p['assets'])==300

def test_itr_text_import(tmp_path):
    path=tmp_path/'itr.txt';path.write_text('Income Tax Return\nTotal income: 500000\nAgricultural income: 10000\nExempt income: 2000')
    p=read_proposal(path,'ITR');assert p['doc_type']=='ITR';assert p['income']['total_income']==500000;assert p['assets']==[]

def test_template_style_formula_export(case,tmp_path):
    a=case.people[0];a.title='Ms.';a.fields['spouse_name']='Example Husband'
    b=case.add_person();b.name='Second Example';b.fields['passport_number']='Y0000000'
    case.add_asset('Immovable Property',1000,a.id,'Plot');case.add_asset('Cash in Hand',200,b.id,'Cash');case.add_asset('Bank Loan',50,a.id,'Loan')
    case.add_income(a.id,{'total_income':500},'ITR','private/path/itr','2025-26')
    path=tmp_path/'report.xlsx';rex.export_workbook(case,path);w=openpyxl.load_workbook(path)
    assert w.sheetnames==['SUMMARY','Sheet1','intro','certificate','immovable','movable','annual income','liabilities']
    assert 'MATCH("Spouse of Applicant"' in w['Sheet1']['C3'].value
    assert 'Sheet1!B3 & " & " & Sheet1!B4' in w['Sheet1']['B7'].value
    assert w['certificate']['E21'].value=='=E18+E19-E20'
    assert w['movable']['E12'].value=='=IF(Sheet1!$C$6>0,ROUND(D12/Sheet1!$C$6,0),0)'
    assert not w['movable']['C12'].font.bold and w['movable']['C13'].font.bold
    assert w['intro']['C5'].font.bold
    assert w['certificate']['E28'].value.startswith("='annual income'!")
    assert not any('#REF!' in str(c.value) for s in w for row in s for c in row)
    assert not any('SPELLNUMBER' in str(c.value) for s in w for row in s for c in row)
    assert w.calculation.fullCalcOnLoad
    for s in w:assert s.print_area and s.max_row<100
    assert 'private/path' not in ''.join(str(c.value) for s in w for row in s for c in row)

def test_no_tax_sheet_without_itr(case,tmp_path):
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash');p=tmp_path/'n.xlsx';rex.export_workbook(case,p);w=openpyxl.load_workbook(p);assert 'annual income' not in w.sheetnames

def test_excel_formula_injection_is_literal(case,tmp_path):
    case.people[0].name='=HYPERLINK("unsafe")';case.add_asset('Cash in Hand',100,case.people[0].id,'=1+1')
    p=tmp_path/'literal.xlsx';rex.export_workbook(case,p);w=openpyxl.load_workbook(p)
    assert w['Sheet1']['B11'].data_type=='s';assert w['Sheet1']['B11'].value.startswith('=')

def test_three_applicants_in_all_outputs(case,tmp_path):
    for name in ('Second Example','Third Example'):case.add_person().name=name
    case.add_asset('Cash in Hand',100,case.applicants[2].id,'Cash')
    c=rex.report_content(case)
    for p in case.applicants:assert p.name in c['intro'][1]
    for ext in ('xlsx','docx','pdf'):
        path=tmp_path/f'three.{ext}';rex.export(case,path,ext);assert path.stat().st_size>1000
        if ext=='docx':
            from docx import Document
            text='\n'.join(p.text for p in Document(path).paragraphs)
        elif ext=='pdf':
            import pymupdf as fitz
            with fitz.open(path) as pdf:text='\n'.join(p.get_text() for p in pdf)
        else:
            w=openpyxl.load_workbook(path);text='\n'.join(str(c.value) for s in w for row in s for c in row)
        for p in case.applicants:assert p.name in text

def test_missing_ocr_graceful(tmp_path):
    with pytest.raises(RuntimeError,match='not installed'):
        legacy._run_local_ocr(str(tmp_path/'no.png'),'')

def test_windows_ocr_hide_flags_and_no_shell():
    source=Path(legacy.__file__).read_text();tree=ast.parse(source)
    f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_run_local_ocr');code=ast.get_source_segment(source,f)
    assert 'run_hidden(' in code
    runtime=(Path(__file__).parents[1]/'runtime_io.py').read_text()
    assert 'CREATE_NO_WINDOW' in runtime and 'STARTF_USESHOWWINDOW' in runtime and 'SW_HIDE' in runtime
    assert 'shell=True' not in code

def test_gui_uses_queue_and_background_import_export():
    text=(Path(__file__).parents[1]/'net_asset_report.py').read_text();ast.parse(text)
    assert 'self.jobs.put' in text and 'self.after(80,self._drain)' in text
    assert text.count('threading.Thread(target=work,daemon=True).start()')>=3
    assert 'ItemDialog(' not in text

def test_rounding_matches_excel_per_item():
    assert rex.round_excel('2.5')==3;assert rex.round_excel('-2.5')==-3
    assert sum(rex.round_excel(x/60) for x in (30,30))==2

def test_legacy_family_passport_not_routed_to_primary():
    c=Case.from_dict(dict(applicant={'name':'Primary'},family_members=[dict(name='Relative',role='Father',passport_fields={'full_name':'Relative','passport_number':'F0000000'})],passport_records=[dict(role='Father',fields={'full_name':'Relative','passport_number':'F0000000'})]))
    assert not c.people[0].fields.get('passport_number')
    family=next(p for p in c.people if p.role!='Applicant')
    assert family.fields['passport_number']=='F0000000';assert len(family.passports)==1
    assert c.relationships==[]

def test_valuation_details_are_not_discarded(case):
    it=case.add_asset('Immovable Property',100,case.people[0].id,'Plot',{'valuer':'Example Valuer','val_date':'07.11.2026'})
    assert 'Example Valuer' in it['note'] and '07.11.2026' in it['note']

def test_renamed_owner_and_relationship_are_current_in_report(case):
    family=case.add_person('Family / owner');family.name='Before Name'
    case.add_asset('Cash in Hand',100,family.id,'Cash')
    family.name='After Name';case.confirm_relationship(case.people[0].id,family.id,'Mother','Reviewed source')
    c=rex.report_content(case);cash=next(i for s in c['sections'] for i in s[3] if i.get('category')=='Cash in Hand')
    assert 'After Name' in cash['desc'] and 'Mother of Applicant' in cash['desc']
    assert 'Before Name' not in cash['desc'] and 'not confirmed' not in cash['desc']

def test_legacy_excel_engine_still_exports(case,tmp_path):
    case.add_asset('Cash in Hand',100,case.people[0].id,'Cash')
    c=rex.report_content(case);path=tmp_path/'legacy.xlsx';legacy.export_excel(c,path)
    assert path.stat().st_size>1000
    w=openpyxl.load_workbook(path);assert w.active.print_area

def test_all_categories_add_inline_without_modal(case):
    for category in legacy.CATS:
        case.add_asset(category,100,case.people[0].id,'Synthetic particulars')
    assert len(case.items)==13
    assert case.totals()['net']==700 # 10 assets less 3 liabilities

def test_single_formula_export_remains_explicit(case,tmp_path):
    p=case.people[0];p.title='Ms.';p.fields['spouse_name']='Husband';case.formula_mode='single'
    case.add_asset('Cash in Hand',100,p.id,'Cash');path=tmp_path/'single.xlsx';rex.export_workbook(case,path)
    w=openpyxl.load_workbook(path);assert 'ISERROR(SEARCH("Mrs",A13))' in w['Sheet1']['C3'].value
    assert case.parent_line(p)=='D/o Sh. Example Father'

def test_missing_original_owner_blocks_export():
    c=Case.from_dict(dict(applicant={'name':'Primary'},items=[dict(category='Cash in Hand',kind='asset',section='B',fields={},desc='Cash',note='',amount=100)]))
    with pytest.raises(ValueError,match='ownership'):rex.report_content(c)

def test_pdf_and_word_income_annexure_separate(case,tmp_path):
    p=case.people[0];case.add_asset('Cash in Hand',100,p.id,'Cash');case.add_income(p.id,{'total_income':500},'ITR','synthetic','2025-26')
    c=rex.report_content(case);assert c['nw']==100
    assert c['sections'][-1][0]=='INCOME';assert c['sections'][-1][-1]==500
    for kind in ('pdf','docx'):rex.export(case,tmp_path/f'income.{kind}',kind)

def test_actual_templates_audit_has_all_sheets_and_broken_formulas_documented():
    path=Path(__file__).parents[1]/'docs/reference_structure_2.1.0.json';audit=json.loads(path.read_text())
    assert len(audit)==3
    for data in audit:
        assert len(data['sheets'])==7 and not data['named_ranges']
        assert any('#REF!' in f for sheet in data['sheets'] for f in sheet['formulas'].values())
        assert any(sheet['state']=='hidden' for sheet in data['sheets'])
        assert all('styled_empty_cells' in sheet and 'cache_types' in sheet for sheet in data['sheets'])
    double,single,itr=({sheet['name']:sheet for sheet in data['sheets']} for data in audit)
    assert 'SUM(D20:D27)' in double['annual income']['formulas']['D28']
    assert 'ISERROR(SEARCH("Mrs", A13))' in single['Sheet1']['formulas']['C3']
    assert 'SUM(D12:D27)' in itr['annual income']['formulas']['D28']


def test_no_automatic_otp_request():
    code=Path(legacy.__file__).read_text()
    assert 'send_otp.click()' not in code
    assert 'click Send OTP yourself' in code

def test_launcher_and_build_are_windowless():
    root=Path(__file__).parents[1];vbs=(root/'Launch Net Asset Report.vbs').read_text()
    assert 'pythonw.exe' in vbs and ', 0, False' in vbs
    build=(root/'build_net_asset_exe.py').read_text()
    assert '"--windowed"' in build and '"NetAssetReport"' in build
    assert 'networth_ocr' in build and 'eng.traineddata' in build
    assert 'net_asset_report.py' in build

class Var:
    def __init__(self,value=''):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value

@pytest.mark.parametrize('target_index',[0,1,2])
def test_ui_apply_routes_to_review_selected_target(case,target_index,monkeypatch):
    from types import SimpleNamespace
    import net_asset_report as ui
    while len(case.people)<3:case.add_person()
    target=case.people[target_index];target.name='ALPHA EXAMPLE'
    doc=dict(parse_passport(PASSPORT),id='doc',kind='Passport',path='synthetic.txt',applied=False)
    vars={k:Var(v) for k,v in doc['passport_details'].items()}
    fake=SimpleNamespace(case=case,review_vars=vars,selected_doc=lambda:doc,doc_target=Var('review target'),person_id=lambda value:target.id,_select_person=lambda:None,refresh=lambda:None,status=Var())
    monkeypatch.setattr(ui.messagebox,'askyesno',lambda *a,**k:False)
    monkeypatch.setattr(ui.messagebox,'showwarning',lambda *a,**k:pytest.fail(str(a)))
    ui.App.apply_import(fake)
    assert doc['applied'] and doc['target_id']==target.id
    assert target.fields['passport_number']=='X0000000'
    assert all(not p.fields.get('passport_number') for p in case.people if p.id!=target.id)


def test_ui_applies_reviewed_itr_not_assets(case,monkeypatch):
    from types import SimpleNamespace
    import net_asset_report as ui
    target=case.people[0];doc=dict(id='doc',kind='ITR',path='itr.txt',text='evidence',applied=False)
    fake=SimpleNamespace(case=case,review_vars={'total_income':Var('123000'),'year':Var('2025-26')},selected_doc=lambda:doc,doc_target=Var('target'),person_id=lambda _:target.id,_select_person=lambda:None,refresh=lambda:None,status=Var())
    monkeypatch.setattr(ui.messagebox,'showwarning',lambda *a,**k:pytest.fail(str(a)))
    ui.App.apply_import(fake)
    assert case.has_itr and not case.items and not case.incomes[0]['include']
    assert case.incomes[0]['values']['total_income']==123000


def test_ui_failed_asset_batch_is_atomic(case,monkeypatch):
    from types import SimpleNamespace
    import net_asset_report as ui
    doc=dict(id='doc',kind='Assets',path='assets.csv',text='source',applied=False)
    proposals=[(Var(True),Var('Cash in Hand'),Var('100'),Var('Cash'),{}),(Var(True),Var('Other Asset'),Var('invalid'),Var('Other'),{})]
    warnings=[]
    fake=SimpleNamespace(case=case,_proposal_assets=proposals,selected_doc=lambda:doc,doc_target=Var('target'),person_id=lambda _:case.people[0].id,_select_person=lambda:None,refresh=lambda:None,status=Var())
    monkeypatch.setattr(ui.messagebox,'showwarning',lambda *a,**k:warnings.append(a))
    ui.App.apply_import(fake)
    assert warnings and not case.items and not doc['applied']

def test_international_mrz_with_valid_check_digits():
    text='P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\nL898902C36UTO7408122F1204159ZE184226B<<<<<10'
    assert all(len(s)==44 for s in text.splitlines())
    p=parse_passport(text);f=p['passport_details']
    assert f['passport_number']=='L898902C3';assert f['nationality']=='UTO'
    assert f['full_name']=='ANNA MARIA ERIKSSON';assert f['date_of_birth']=='12.08.1974'
    assert f['date_of_expiry']=='15.04.2012'
    assert not any('check digit failed' in s for s in p['warnings'])

def test_mrz_bad_check_digit_not_trusted():
    text='P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\nL898902C30UTO7408122F1204159ZE184226B<<<<<10'
    p=parse_passport(text)
    assert p['passport_details']['passport_number']==''
    assert any('passport_number' in s for s in p['warnings'])
    assert p['text']==text

def test_full_multiline_address_not_truncated():
    address='\n'.join('Synthetic address line '+str(i) for i in range(15))
    p=parse_passport('Address:\n'+address+'\nFile No: SYNTHETIC')
    assert len(p['passport_details']['address'])>180
    assert 'line 14' in p['passport_details']['address']
    assert p['passport_details']['file_number']=='SYNTHETIC'

@pytest.mark.parametrize('label',['NON-ECR','ECNR','ECR'])
def test_ecr_status_without_label(label):
    p=parse_passport(label);assert p['passport_details']['emigration_status']==label

def test_family_relation_can_be_to_second_applicant(case,tmp_path):
    a=case.people[0];b=case.add_person();b.name='Second Applicant';father=case.add_person('Family / owner');father.name='Father of Second'
    case.confirm_relationship(b.id,father.id,'Father','Confirmed on second applicant source passport')
    case.add_asset('Cash in Hand',100,father.id,'Cash')
    c=rex.report_content(case);it=next(i for s in c['sections'] for i in s[3] if i.get('category')=='Cash in Hand')
    assert 'Father of Applicant 2 (Second Applicant)' in it['desc']
    assert 'Father of Applicant 1' not in it['desc']
    path=tmp_path/'second.xlsx';rex.export_workbook(case,path);w=openpyxl.load_workbook(path)
    assert w['movable']['C13'].value=='(Father of Applicant 2 (Second Applicant))'

def test_owner_can_have_reviewed_relations_to_both_applicants(case):
    a=case.people[0];b=case.add_person();b.name='Second'
    parent=case.add_person('Family / owner');parent.name='Common Parent'
    for p in (a,b):case.confirm_relationship(p.id,parent.id,'Mother','Each source explicitly reviewed')
    rel=case.report_owner_relation(parent.id)
    assert 'Mother of Applicant 1' in rel and 'Mother of Applicant 2' in rel

def test_remove_accidental_blank_applicant(case):
    p=case.add_person();case.remove_person(p.id);assert len(case.applicants)==1
    with pytest.raises(ValueError):case.remove_person(case.applicants[0].id)

def test_cannot_remove_person_with_evidence_or_assets(case):
    p=case.add_person();p.name='Linked Example';case.add_asset('Cash in Hand',100,p.id,'Cash')
    with pytest.raises(ValueError):case.remove_person(p.id)

def test_inconsistent_source_formula_warns_instead_of_silent_guess(case):
    p=case.people[0];p.title='Mr.';p.fields['spouse_name']='Spouse'
    assert case.parent_line(p).startswith('W/o')
    assert any('W/o for Mr.' in s for s in case.formula_warnings())
    p.use_father=True;assert not case.formula_warnings()
    p.title='Mrs.';assert any('S/o' in s for s in case.formula_warnings())

def test_word_pdf_fx_matches_template_per_item_rounding(case):
    p=case.people[0]
    case.add_asset('Cash in Hand',30,p.id,'Cash one');case.add_asset('Cash in Hand',30,p.id,'Cash two')
    content=rex.report_content(case)
    assert content['nw']==60
    assert content['fx_value']==2 # ROUND(30/60,0)+ROUND(30/60,0), not ROUND(60/60,0)
    assert 'CAD 2/-' in content['words'][1]

def test_ui_mixed_owner_asset_import_routes_each_row(case,monkeypatch):
    from types import SimpleNamespace
    import net_asset_report as ui
    a=case.people[0];b=case.add_person();b.name='Second Owner'
    doc=dict(id='doc',kind='Assets',path='assets.csv',text='source',applied=False)
    proposals=[(Var(True),Var('Cash in Hand'),Var('100'),Var('Cash'),{},Var('a')),(Var(True),Var('Immovable Property'),Var('200'),Var('Plot'),{},Var('b'))]
    fake=SimpleNamespace(case=case,_proposal_assets=proposals,selected_doc=lambda:doc,doc_target=Var('a'),person_id=lambda label:a.id if label=='a' else b.id,_select_person=lambda:None,refresh=lambda:None,status=Var())
    monkeypatch.setattr(ui.messagebox,'showwarning',lambda *a,**k:pytest.fail(str(a)))
    ui.App.apply_import(fake)
    assert doc['applied'];assert case.items[0]['owner_id']==a.id;assert case.items[1]['owner_id']==b.id
    assert case.totals()['net']==300

def test_two_passports_in_one_file_are_not_silently_merged():
    proposal=parse_passport('Passport No: X0000000\nGiven Names: FIRST\nSurname: EXAMPLE\nPassport No: Y0000000\nGiven Names: SECOND\nSurname: EXAMPLE')
    assert proposal['multiple_passports'];assert proposal['field_conflicts']['passport_number']==['X0000000','Y0000000']
    c=Case()
    with pytest.raises(ValueError,match='Split'):c.import_passport(c.people[0].id,proposal)
    assert not c.people[0].passports
