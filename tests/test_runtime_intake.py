"""Regressions based on reported Windows failure and OCR layout; identities sanitized."""
import ast,base64,copy,subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
import runtime_io as rio
import document_intake as intake
from asset_model import Case,parse_passport,read_proposal
import legacy_engine as legacy

NOISY_PASSPORT='''@SI/ Visa
â€”â€”~
â€˜Hg / Type
aii
ats / Code,
IND
â€˜efter / Nationaitly
â€œuRmitd 7./ Passport No.
ARG / INDIAN
â€˜JAE / Surname
X0000000
er se APH / Given Name(s)
ALPHA EXAMPLE
â€˜WARN / Date of Birth
Re / Sex
25/04/1988
*
â€˜WF RIM/ Place of Birth
EXAMPLE BIRTH CITY
â€˜Sane ZT RIFT / Place of issue
EXAMPLE OFFICE
â€˜ane BRT HI PRL/ Date of issue
ALpHa EXamp1e
PPAR / Date of
15/02/2023
14/02/2033
P<IND<<ALPHA<EXAMPLE<<<<<<<<cccccccecccececc
X0000000<81ND8804257M33021412000000000000<96
nny
if
NO
â€˜Reon aseph sifonres a1 Name of Father / Legal Guardian vi 4683 LY
EXAMPLE FATHER nis
Rn TA / Name of Mother 0) sa
EXAMPLE MOTHER as
â€˜aR at Get a5 FFT / Name of Spouse o25
EXAMPLE SPOUSE r ag
Address
EXAMPLE ROAD ST NO 6 EXAMPLE NAGAR
EXAMPLE CITY,EXAMPLE DISTRICT ia
PIN: 000000 EXAMPLE STATE, INDIA
ge rio fers RL UF / Old Passport No with Date and Place of issue
Z0000000 16/02/2017 ~â€”~ EXAMPLE OLD OFFICE at
'''

VALUATION='''EXAMPLE & ASSOCIATES
Engineer, Architect, Estimator, Valuer & Consultant
MCB-Lic.No.233/MTP
Member of IOV Lic.No.A/23689
Mob.No.9870000000
Ref no.106/2139
Date:07-11-2026
VALUATION REPORT
PROPERTY: VACANT PLOT
At
EXAMPLE LOCATION, EXAMPLE DISTRICT
TEHSIL-EXAMPLE
OWNER NAME: ALPHA EXAMPLE S/O EXAMPLE FATHER
APPLICANT NAME: ALPHA EXAMPLE S/O EXAMPLE FATHER
1. Name of Owner : Alpha Example S/o Example Father
2. Date of Valuation :07-11-2026
3. Address of the property : This Vacant Plot is situated at
Example Location, Example District,
Example Town
Tehsil-Example
4. Locality: Vacant Plot
5. Tenure of Property : Free Hold
7. Deed date/no. : Khata No.46/58
Khasar No.79,
8. Area of Plot :10 Marla
13. Value of land as per Prevailing Market Rate :Rs.1,25,000/- Per Marla
:Rs.12,50,000/-
14. Value of built-up area Rate :N.A
15. Total Value : Land + Building
:Rs.12,50,000/-
Rs.12,50,000/-
(Rs.TWELVE LAC FIFTY THOUSAND ONLY)
Note: No interest in property.
'''

class Var:
    def __init__(self,value=''):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value

def test_byte_9d_never_raises_or_disappears():
    data=b'normal text\x9dremaining'
    text,encoding,notes=rio.decode_output(data)
    assert 'remaining' in text and '\ufffd' in text and notes
    assert encoding=='utf-8 replacement'

@pytest.mark.parametrize('data',[b'ASCII output', 'Unicode — café'.encode('utf-8'),b'CP1252 quote \x93value\x94',b'broken\x9dvalue'])
def test_runtime_capture_is_binary_and_retains_exact_bytes(monkeypatch,data):
    calls=[]
    def run(cmd,**kwargs):
        calls.append(kwargs);return SimpleNamespace(returncode=0,stdout=data,stderr=b'')
    monkeypatch.setattr(rio.subprocess,'run',run);monkeypatch.setattr(rio,'windows_options',lambda:{'creationflags':0x8000000,'startupinfo':'hidden'})
    rio.reset_evidence();result=rio.run_hidden(['tesseract','--version'])
    assert isinstance(result.stdout,str) and result.raw_stdout==data
    assert calls[0]['text'] is False and calls[0]['creationflags']==0x8000000
    evidence=rio.take_evidence();assert base64.b64decode(evidence[0]['stdout_base64'])==data

def test_windows_flags_configured_without_creating_window(monkeypatch):
    monkeypatch.setattr(rio.subprocess,'STARTUPINFO',lambda:SimpleNamespace(dwFlags=0,wShowWindow=1),raising=False)
    monkeypatch.setattr(rio.subprocess,'STARTF_USESHOWWINDOW',1,raising=False)
    monkeypatch.setattr(rio.subprocess,'SW_HIDE',0,raising=False)
    monkeypatch.setattr(rio.subprocess,'CREATE_NO_WINDOW',0x8000000,raising=False)
    opts=rio.windows_options('nt')
    assert opts['creationflags']==0x8000000
    assert opts['startupinfo'].dwFlags&1 and opts['startupinfo'].wShowWindow==0
    assert rio.windows_options('posix')=={}

def test_all_legacy_ocr_and_version_calls_use_safe_capture():
    text=Path(legacy.__file__).read_text()
    assert 'run_hidden(command, timeout=120' in text
    assert 'run_hidden([tesseract, "--version"], timeout=15)' in text
    for n in ast.walk(ast.parse(text)):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess':
            assert not any(k.arg in ('text','universal_newlines') and isinstance(k.value,ast.Constant) and k.value.value is True for k in n.keywords)

def test_reversible_mojibake_keeps_source_untouched():
    prop=parse_passport(NOISY_PASSPORT)
    assert prop['original_text']==NOISY_PASSPORT
    assert 'â€”' not in prop['text'] and '—' in prop['text']
    assert prop['text_repairs'] and prop['warnings']
    text='Already correct — “quoted” café';assert intake.repair_text(text)==(text,[])

def test_noisy_interleaved_passport_keeps_source_grounded_fields():
    p=parse_passport(NOISY_PASSPORT);f=p['passport_details']
    assert f['full_name']=='ALPHA EXAMPLE'
    assert f['passport_number']=='X0000000'
    assert f['surname']=='' # Number under surname is not a surname.
    assert f['date_of_birth']=='25/04/1988'
    assert f['date_of_issue']=='15/02/2023'
    assert f['date_of_expiry']=='' # Truncated/missing expiry label and malformed MRZ: no guess.
    assert f['sex']=='' # '*' is not evidence of sex.
    assert f['father_name']=='EXAMPLE FATHER'
    assert f['mother_name']=='EXAMPLE MOTHER'
    assert f['spouse_name']=='EXAMPLE SPOUSE'
    assert 'PIN: 000000' in f['address']
    assert f['old_passport_number']=='Z0000000' and f['old_date_of_issue']=='16/02/2017'
    assert any(d['value']=='14/02/2033' for d in p['date_candidates'])
    assert any('MRZ' in w for w in p['warnings'])

def test_passport_selected_as_itr_is_detected_before_empty_income_parse(tmp_path):
    path=tmp_path/'mistaken_itr.txt';path.write_text(NOISY_PASSPORT,encoding='utf-8')
    p=read_proposal(path,'ITR')
    assert p['kind']=='Passport' and p['doc_type']=='Passport'
    assert p['requested_kind']=='ITR' and p['reclassification_required']
    assert not p['income'] and not p['assets']
    assert p['passport_details']['full_name']=='ALPHA EXAMPLE'

def test_passport_applies_to_explicit_unnamed_target_without_preexisting_name():
    c=Case();target=c.people[0];assert not target.name
    c.import_passport(target.id,parse_passport(NOISY_PASSPORT))
    assert target.name=='ALPHA EXAMPLE'
    assert target.passports[0]['raw_text']==NOISY_PASSPORT

def test_noisy_assets_total_not_unit_rate_or_reference(tmp_path):
    path=tmp_path/'valuation.txt';path.write_text(VALUATION)
    p=read_proposal(path,'Assets')
    assert len(p['assets'])==1
    it=p['assets'][0];assert it['category']=='Immovable Property' and it['amount']==1250000
    assert it['fields']['nature']=='Vacant Plot'
    assert it['fields']['val_date']=='07-11-2026'
    assert it['fields']['area']=='10 Marla'
    assert 'Khata No.46/58' in it['fields']['deed']
    assert 'Khasar No.79' in it['fields']['deed']
    assert 'Example District' in it['fields']['location']
    assert 'Mob' not in it['fields']['location']
    assert p['owner_candidate']['name']=='ALPHA EXAMPLE'
    assert p['owner_candidate']['father_name']=='EXAMPLE FATHER'
    assert it['fields']['holder']=='ALPHA EXAMPLE'

def test_different_explicit_totals_are_ambiguous_not_largest():
    p=intake.valuation_proposals('VALUATION REPORT\nTotal Value: Rs.10,00,000/-\nTotal Value: Rs.12,50,000/-')
    assert len(p['assets'])==1 and p['assets'][0]['amount']=='' and len(p['amount_candidates'])>=2 and p['warnings']

@pytest.mark.parametrize('text',[
    'VALUATION REPORT\nRef no.1250000\nMobile9870000000\nLic.233/MTP',
    'VALUATION REPORT\nTotal Value: Rs.1,25,000/- Per Marla',
    'VALUATION REPORT\nTotal Value: Rs.125000/- at 10%',
])
def test_unit_rates_percent_and_reference_not_used_as_total(text):
    proposal=intake.valuation_proposals(text)
    assert len(proposal['assets'])==1 and proposal['assets'][0]['amount']==''  # editable draft, never a guessed total

def test_reclassification_to_real_itr_never_creates_assets(tmp_path):
    path=tmp_path/'itr.txt';path.write_text('Income Tax Return\nAssessment Year:2025-26\nTotal income:500000')
    p=read_proposal(path,'Assets');assert p['kind']=='ITR' and p['income']['total_income']==500000 and not p['assets']

def test_mixed_passport_itr_is_flagged_for_split(tmp_path):
    path=tmp_path/'mixed.txt';path.write_text(NOISY_PASSPORT+'\nIncome Tax Return\nAssessment Year:2025-26')
    p=read_proposal(path,'ITR');assert p['mixed_document']

def test_real_binary_subprocess_invalid_cp1252_byte_no_readerthread_failure():
    import sys
    rio.reset_evidence()
    result=rio.run_hidden([sys.executable,'-c',"import sys;sys.stdout.buffer.write(b'output\\x9dOK');sys.stderr.buffer.write(b'warning\\x93test\\x94')"])
    assert result.returncode==0 and 'OK' in result.stdout
    assert result.raw_stdout==b'output\x9dOK' and result.warnings
    assert base64.b64decode(rio.take_evidence()[0]['stdout_base64'])==result.raw_stdout

def test_ui_wrong_type_passport_confirmation_then_names_selected_unnamed_person(monkeypatch):
    import net_asset_report as ui
    c=Case();target=c.people[0]
    doc=intake.reparse(dict(id='passport',path='synthetic.txt',original_text=NOISY_PASSPORT,applied=False),'ITR')
    questions=[]
    monkeypatch.setattr(ui.messagebox,'askyesno',lambda *a,**k:questions.append(a) or True)
    monkeypatch.setattr(ui.messagebox,'showwarning',lambda *a,**k:pytest.fail(str(a)))
    fake=SimpleNamespace(case=c,review_vars={k:Var(v) for k,v in doc['passport_details'].items()},selected_doc=lambda:doc,doc_target=Var('selected'),person_id=lambda _:target.id,_select_person=lambda:None,refresh=lambda:None,status=Var())
    ui.App.apply_import(fake)
    assert questions and doc['applied'] and target.name=='ALPHA EXAMPLE'
    assert not c.incomes and not c.items

def test_ui_wrong_type_decline_does_not_modify_case(monkeypatch):
    import net_asset_report as ui
    c=Case();doc=intake.reparse(dict(path='synthetic',original_text=NOISY_PASSPORT,applied=False),'ITR')
    monkeypatch.setattr(ui.messagebox,'askyesno',lambda *a,**k:False)
    fake=SimpleNamespace(case=c,selected_doc=lambda:doc)
    ui.App.apply_import(fake)
    assert not c.people[0].name and not c.people[0].passports and not c.incomes

def test_ui_asset_unnamed_owner_error_is_actionable(monkeypatch):
    import net_asset_report as ui
    c=Case();warnings=[];doc=dict(kind='Assets',path='assets',applied=False)
    monkeypatch.setattr(ui.messagebox,'showwarning',lambda *a,**k:warnings.append(a))
    fake=SimpleNamespace(case=c,selected_doc=lambda:doc,doc_target=Var('selected'),person_id=lambda _:c.people[0].id,owner_review_vars={})
    ui.App.apply_import(fake)
    assert warnings and 'Owner name in the review panel' in warnings[0][1]
    assert not c.items and not doc['applied']

def test_assets_wrong_itr_button_reclassifies_to_assets_and_keeps_total(tmp_path):
    path=tmp_path/'valuation.txt';path.write_text(VALUATION)
    p=read_proposal(path,'ITR');assert p['kind']=='Assets' and p['reclassification_required']
    assert p['assets'][0]['amount']==1250000 and not p['income']

def test_bad_encoding_source_bytes_kept_in_proposal(tmp_path):
    path=tmp_path/'bad.txt';original=b'Passport No: X0000000\nGiven Names: ALPHA\nSurname: EXAMPLE\nDate of Birth: 01/01/1990\n\x9d'
    path.write_bytes(original);prop=read_proposal(path,'Passport')
    assert base64.b64decode(prop['source_bytes_base64'])==original and prop['warnings']

def test_manual_reclassification_does_not_drop_raw_source_or_markers():
    prop=intake.reparse(dict(path='synthetic',original_text=NOISY_PASSPORT),'ITR')
    again=intake.reparse(prop,'Passport',explicit=True)
    assert again['original_text']==NOISY_PASSPORT and again['passport_details']['full_name']=='ALPHA EXAMPLE'
    assert again['detected_kind']=='Passport' and not again['reclassification_required']

@pytest.mark.parametrize('create',[False,True])
def test_owner_name_review_is_explicit_and_creates_no_family_relationship(create,monkeypatch):
    import net_asset_report as ui
    c=Case();target=c.people[0];old_label='1. Unnamed | Applicant'
    doc=dict(id='valuation',kind='Assets',path='synthetic',target_id=target.id,applied=False)
    owner=Var(old_label);row=(Var(True),Var('Immovable Property'),Var('1250000'),Var('Vacant plot'),{},owner)
    fake=SimpleNamespace(case=c,_people_labels={target.id:old_label},current_person=target.id,selected_doc=lambda:doc,
        owner_review_vars={'name':Var('ALPHA EXAMPLE'),'father_name':Var('EXAMPLE FATHER')},
        doc_target=Var(old_label),_proposal_assets=[row],_select_person=lambda:None,status=Var())
    fake.person_id=lambda label:next(pid for pid,value in fake._people_labels.items() if value==label)
    fake.refresh=lambda:setattr(fake,'_people_labels',{p.id:f'{i}. {p.name} | {p.role}' for i,p in enumerate(c.people,1)})
    ui.App.use_reviewed_owner(fake,create=create)
    reviewed=c.person(doc['target_id'])
    assert reviewed.name=='ALPHA EXAMPLE' and reviewed.fields['father_name']=='EXAMPLE FATHER'
    assert reviewed.role==('Family / owner' if create else 'Applicant')
    assert owner.get()==fake._people_labels[reviewed.id]
    assert len(c.people)==(2 if create else 1)
    assert not c.relationships and not c.items and not c.incomes

def test_optional_driver_has_explicit_no_console_service_flag():
    source=Path(legacy.__file__).read_text()
    assert 'service = ChromeService()' in source
    assert 'service.creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)' in source
    assert 'webdriver.Chrome(options=options, service=service)' in source
