from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, jsonify
from config import TEMPLATE_DIR,DOCX_DIR,ENTITY_OPTIONS,OPINION_OPTIONS,ENTITY_FORM_OPTIONS
from docx_engine import extract_placeholders,replace_texts,validate_template
from report_rules import select_template,classification_label,opinion_label
from applicability_engine import classify, assessment_date_from_year_ending
from register import ensure_register,next_report_id,add_record,list_records
from master_data import *

BASE_DIR=Path(__file__).resolve().parent
app=Flask(__name__); app.secret_key='stage4-change-this-secret-key'
REQUIRED={'client_name':'Client Name','cin':'CIN','city':'City','financial_year':'Financial Year','year_ending':'Year Ending','entity_type':'Entity Type','opinion':'Opinion','firm_id':'CA Firm','partner_id':'Signing CA / Partner','place':'Place','report_date':'Date of Report'}

def format_report_date(v):
    v=(v or '').strip()
    for fmt in ('%Y-%m-%d','%d-%m-%Y','%d/%m/%Y','%B %d, %Y','%b %d, %Y'):
        try:return datetime.strptime(v,fmt).strftime('%B %d, %Y')
        except ValueError:pass
    return v

def safe_filename(v):
    return re.sub(r'\s+','_',re.sub(r'[^A-Za-z0-9._ -]+','',v or 'Report').strip())[:120]

def validate_form(d): return [label for key,label in REQUIRED.items() if not str(d.get(key,'')).strip()]

def resolve_masters(d):
    f=get_firm(d.get('firm_id','')); p=get_partner(d.get('partner_id',''))
    if f: d.update(firm_name=f['FirmName'],frn=f['FRN'],default_place=f.get('DefaultPlace',''))
    if p: d.update(partner_name=p['PartnerName'],membership_no=p['MembershipNo']); d['place']=d.get('place') or p.get('DefaultPlace') or d.get('default_place','')
    return d

def replacements(d):
    return {'{Name of Company}':d['client_name'],'{NAME OF COMPANY}':d['client_name'],'{CIN}':d['cin'],'{City}':d['city'],'{Year ending}':d['year_ending'],'{Date of Report}':format_report_date(d['report_date']),'{UDIN}':d.get('udin',''),'{CA Firm Name}':d['firm_name'],'{Signing CA}':d['partner_name'],'{FRN}':d['frn'],'{Membership No.}':d['membership_no'],'{Place of Signing}':d['place'],'ABC & Co LLP':d['firm_name'],'CA ___________':f"CA {d['partner_name']}",'CA ________________':f"CA {d['partner_name']}",'Membership No.: 000000':f"Membership No.: {d['membership_no']}",'Firm Reg. no.: 000000W/W000000':f"Firm Reg. no.: {d['frn']}",'Place:\tNashik':f"Place:\t{d['place']}",'Place: \tNashik':f"Place: \t{d['place']}"}

@app.before_request
def init(): ensure_master(); ensure_register(); DOCX_DIR.mkdir(parents=True,exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html',entity_options=ENTITY_OPTIONS,opinion_options=OPINION_OPTIONS,firms=list_firms(),clients=list_clients(),form={})

@app.get('/api/firm/<firm_id>')
def api_firm(firm_id): return jsonify(get_firm(firm_id) or {})
@app.get('/api/partners/<firm_id>')
def api_partners(firm_id): return jsonify(list_partners(firm_id))
@app.get('/api/client/<client_id>')
def api_client(client_id): return jsonify(get_client(client_id) or {})
@app.get('/api/engagements/<client_id>')
def api_engagements(client_id): return jsonify(list_engagements(client_id))

@app.get('/clients')
def clients(): return render_template('clients.html',clients=list_clients(False))
@app.route('/clients/new',methods=['GET','POST'])
def client_new():
    if request.method=='POST': save_client(request.form.to_dict()); return redirect(url_for('clients'))
    return render_template('client_form.html',entity_options=ENTITY_OPTIONS)
@app.route('/clients/<client_id>/edit',methods=['GET','POST'])
def client_edit(client_id):
    c=get_client(client_id)
    if not c:return 'Client not found',404
    if request.method=='POST': update_client(client_id,request.form.to_dict()); return redirect(url_for('clients'))
    return render_template('client_form.html',client=c,entity_options=ENTITY_OPTIONS,edit_mode=True)

@app.get('/engagements')
def engagements(): return render_template('engagements.html',engagements=list_engagements(),clients=list_clients(False),firms=list_firms(False))
@app.route('/engagements/new',methods=['GET','POST'])
def engagement_new():
    if request.method=='POST': save_engagement(request.form.to_dict()); return redirect(url_for('engagements'))
    return render_template('engagement_form.html',clients=list_clients(),firms=list_firms(),partners=[],entity_options=ENTITY_OPTIONS,opinion_options=OPINION_OPTIONS)
@app.route('/engagements/<engagement_id>/edit',methods=['GET','POST'])
def engagement_edit(engagement_id):
    e=get_engagement(engagement_id)
    if not e:return 'Engagement not found',404
    if request.method=='POST': update_engagement(engagement_id,request.form.to_dict()); return redirect(url_for('engagements'))
    return render_template('engagement_form.html',engagement=e,clients=list_clients(False),firms=list_firms(False),partners=list_partners(e.get('FirmID'),False),entity_options=ENTITY_OPTIONS,opinion_options=OPINION_OPTIONS,edit_mode=True)

@app.route('/engagements/<engagement_id>/carry-forward', methods=['GET','POST'])
def carry_forward(engagement_id):
    prev=get_engagement(engagement_id)
    if not prev:return 'Engagement not found',404
    c=get_client(prev['ClientID'])
    if not c:return 'Client not found',404
    if request.method=='POST':
        save_engagement(request.form.to_dict())
        return redirect(url_for('engagements'))
    return render_template('engagement_form.html',clients=list_clients(),firms=list_firms(),partners=list_partners(prev.get('FirmID')),entity_options=ENTITY_OPTIONS,opinion_options=OPINION_OPTIONS,carry_from=prev,client=c)

def apply_optional_master_defaults(d):
    """
    Use Client/Engagement selections only as defaults.

    A selected master record must never silently overwrite a value that the CA
    has subsequently changed on the New Audit Report screen. This is the key
    Stage 5 rule: master data provides defaults; the current report form is
    authoritative for the report being generated.
    """
    client_id=str(d.get('client_id','')).strip()
    engagement_id=str(d.get('engagement_id','')).strip()

    if client_id:
        c=get_client(client_id)
        if c:
            for key, master_key in (
                ('client_name','ClientName'),
                ('cin','CIN'),
                ('city','City'),
            ):
                if not str(d.get(key,'')).strip():
                    d[key]=c.get(master_key,'') or ''

    if engagement_id:
        e=get_engagement(engagement_id)
        if e:
            defaults={
                'financial_year':e.get('FinancialYear',''),
                'year_ending':e.get('YearEnding',''),
                'entity_type':e.get('EntityType',''),
                'small_company':'yes' if str(e.get('SmallCompany','')).lower()=='yes' else 'no',
                'opinion':e.get('Opinion',''),
                'firm_id':e.get('FirmID',''),
                'partner_id':e.get('PartnerID',''),
                'place':e.get('Place',''),
            }
            # Only populate fields that are actually blank. If the CA changed
            # anything after selecting the engagement, preserve that change.
            for key, value in defaults.items():
                if not str(d.get(key,'')).strip() and str(value).strip():
                    d[key]=value

    return d

@app.post('/review')
def review():
    d=request.form.to_dict(); d['small_company']=str(d.get('small_company','')).lower()=='yes'
    # Existing Client and Existing Engagement are OPTIONAL. If selected they
    # provide defaults only; current-screen CA edits always take precedence.
    apply_optional_master_defaults(d)
    resolve_masters(d); missing=validate_form(d)
    if missing:return render_template('index.html',error='Please complete: '+', '.join(missing),entity_options=ENTITY_OPTIONS,opinion_options=OPINION_OPTIONS,firms=list_firms(),clients=list_clients(),form=d)
    try: fn=select_template(d['entity_type'],d['small_company'],d['opinion'])
    except ValueError as e:return render_template('index.html',error=str(e),entity_options=ENTITY_OPTIONS,opinion_options=OPINION_OPTIONS,firms=list_firms(),clients=list_clients(),form=d)
    path=TEMPLATE_DIR/fn; ph=extract_placeholders(path); repl=replacements(d)
    d.update(template_name=fn,template_version='1.0',classification_label=classification_label(d['entity_type'],d['small_company']),opinion_label=opinion_label(d['opinion']),placeholders=ph,unmapped=[p for p in ph if p not in repl],replacement_map=repl,report_date_formatted=format_report_date(d['report_date']))
    return render_template('review.html',data=d)

@app.post('/generate')
def generate():
    d=request.form.to_dict(); d['small_company']=str(d.get('small_company','')).lower()=='yes'
    # Preserve all values from the Review screen. Optional Client/Engagement
    # records are only used to fill blanks, never to overwrite CA edits.
    apply_optional_master_defaults(d)
    resolve_masters(d); missing=validate_form(d)
    if missing:return render_template('index.html',error='Please complete: '+', '.join(missing),entity_options=ENTITY_OPTIONS,opinion_options=OPINION_OPTIONS,firms=list_firms(),clients=list_clients(),form=d)
    try:
        fn=select_template(d['entity_type'],d['small_company'],d['opinion']); tp=TEMPLATE_DIR/fn
        if not tp.exists(): raise FileNotFoundError(f'Master Word template not found: {fn}')
        rid=next_report_id(); base=safe_filename(f"{d['client_name']}_{d['financial_year']}_Statutory_Audit_Report"); path=DOCX_DIR/f'{rid}_{base}.docx'
        count,remaining=replace_texts(tp,path,replacements(d)); validation=validate_template(path)
        if not validation.get('readable') or remaining: raise ValueError('Generated report failed validation: '+(', '.join(remaining) if remaining else 'invalid DOCX package'))
        record={'ReportID':rid,'ClientID':d.get('client_id',''),'EngagementID':d.get('engagement_id',''),'ClientName':d['client_name'],'CIN':d['cin'],'City':d['city'],'EntityType':classification_label(d['entity_type'],d['small_company']),'SmallCompany':'Yes' if d['small_company'] else 'No','Opinion':opinion_label(d['opinion']),'FinancialYear':d['financial_year'],'YearEnding':d['year_ending'],'TemplateName':fn,'TemplateVersion':'1.0','PartnerName':d['partner_name'],'MembershipNo':d['membership_no'],'FirmName':d['firm_name'],'FRN':d['frn'],'Place':d['place'],'ReportDate':format_report_date(d['report_date']),'UDIN':d.get('udin','').strip(),'GeneratedAt':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'Status':'UDIN_PENDING' if not d.get('udin','').strip() else 'GENERATED','DOCXPath':str(path.relative_to(BASE_DIR))}
        add_record(record); d['report_date_formatted']=format_report_date(d['report_date'])
        return render_template('result.html',data=d,report_id=rid,docx_name=path.name,replaced_count=count,remaining=remaining)
    except Exception as exc:return render_template('error.html',message=f'{type(exc).__name__}: {exc}'),500

@app.get('/download/docx/<path:filename>')
def download_docx(filename): return send_from_directory(DOCX_DIR,filename,as_attachment=True)
@app.get('/register')
def register(): return render_template('register.html',records=list_records())
@app.get('/templates')
def templates():
    rows=[]
    for p in sorted(TEMPLATE_DIR.glob('AR_*.docx')):
        try:rows.append(validate_template(p))
        except Exception as e:rows.append({'file':p.name,'readable':False,'error':str(e)})
    return render_template('templates.html',rows=rows,template_master=list_templates(),variables=list_variables(),wordings=list_wordings())
@app.get('/masters')
def masters(): return render_template('masters.html',firms=list_firms(False),partners=list_partners(None,False))
@app.route('/masters/firm',methods=['GET','POST'])
def firm_master():
    if request.method=='POST':save_firm(request.form.to_dict());return redirect(url_for('masters'))
    return render_template('firm_form.html')
@app.route('/masters/firm/<firm_id>/edit',methods=['GET','POST'])
def edit_firm(firm_id):
    firm=get_firm(firm_id)
    if not firm:return 'Firm not found',404
    if request.method=='POST':update_firm(firm_id,request.form.to_dict());return redirect(url_for('masters'))
    return render_template('firm_form.html',firm=firm,edit_mode=True)
@app.route('/masters/partner/<partner_id>/edit',methods=['GET','POST'])
def edit_partner(partner_id):
    partner=get_partner(partner_id)
    if not partner:return 'Partner not found',404
    if request.method=='POST':update_partner(partner_id,request.form.to_dict());return redirect(url_for('masters'))
    return render_template('partner_form.html',firms=list_firms(False),partner=partner,edit_mode=True)
@app.route('/masters/partner',methods=['GET','POST'])
def partner_master():
    if request.method=='POST':save_partner(request.form.to_dict());return redirect(url_for('masters'))
    return render_template('partner_form.html',firms=list_firms(False))

@app.get('/applicability')
def applicability_home():
    return render_template(
        'applicability_home.html',
        engagements=list_engagements(),
        clients=list_clients(False),
        classifications=[r for r in list_classification() if r]
    )

def _applicability_initial_facts(e):
    # Carry forward the engagement-level facts as sensible defaults, while
    # leaving all regulatory facts editable by the professional.
    entity = e.get('EntityType','private_ltd')
    assessment = assessment_date_from_year_ending(e.get('YearEnding',''))
    return {
        'entity_form': entity,
        'assessment_date': assessment,
        'listed':'no','in_process_listing':'no','bank':'no','financial_institution':'no',
        'insurance':'no','section8':'no','opc':'yes' if entity=='opc' else 'no',
        'holding':'no','subsidiary':'no','holding_subsidiary_of_non_msme':'no','special_act':'no',
        'paid_up_capital':'','reserves_surplus':'','turnover_prior':'',
        'revenue_current':'','borrowings_max':'','net_worth':'',
        'indas_required':'no','accounting_framework':'AS – Companies',
        'professional_notes':''
    }

@app.route('/applicability/<engagement_id>', methods=['GET','POST'])
def applicability(engagement_id):
    e=get_engagement(engagement_id)
    if not e: return 'Engagement not found',404
    c=get_client(e['ClientID'])
    if not c: return 'Client not found',404

    if request.method=='POST':
        d=request.form.to_dict()
        d['entity_form']=d.get('entity_form','private_ltd')
        # Classification and applicability are recalculated from current facts.
        result=classify(d)

        # Apply final CA conclusions and rationale.
        for r in result['results']:
            final=request.form.get('final_'+r['RuleCode'],r['SystemResult'])
            rationale=request.form.get('rationale_'+r['RuleCode'],r['Rationale'])
            r['FinalResult']=final
            r['Override']='Yes' if final != r['SystemResult'] else 'No'
            r['Rationale']=rationale

        f=result['facts']
        summary={
            'EngagementID':engagement_id,
            'AssessmentBasis':'Current Companies Act / ICAI rules with legacy classification shown for historical reference',
            'AssessmentDate':result['assessment_date'],
            'EntityForm':f.entity_form,
            'Listed':'Yes' if f.listed else 'No',
            'InProcessListing':'Yes' if f.in_process_listing else 'No',
            'Bank':'Yes' if f.bank else 'No',
            'FinancialInstitution':'Yes' if f.financial_institution else 'No',
            'Insurance':'Yes' if f.insurance else 'No',
            'Section8':'Yes' if f.section8 else 'No',
            'OPC':'Yes' if f.opc else 'No',
            'SmallCompany':'Yes' if result['small_company'] else 'No',
            'PrivateCompany':'Yes' if f.private_company else 'No',
            'PublicCompany':'Yes' if f.public_company else 'No',
            'HoldingCompany':'Yes' if f.holding else 'No',
            'SubsidiaryCompany':'Yes' if f.subsidiary else 'No',
            'HoldingSubsidiaryOfNonMSME':'Yes' if f.holding_subsidiary_of_non_msme else 'No',
            'SpecialActEntity':'Yes' if f.special_act else 'No',
            'PaidUpCapital':f.paid_up_capital,
            'ReservesSurplus':f.reserves_surplus,
            'TurnoverPriorYear':f.turnover_prior,
            'RevenueCurrentYear':f.revenue_current,
            'BorrowingsMax':f.borrowings_max,
            'NetWorth':f.net_worth,
            'IndASRequired':'Yes' if f.indas_required else 'No',
            'AccountingFramework':f.accounting_framework,
            'NonCompanyASCategory':result['noncompany_category'],
            'LegacyLevel':result['legacy_level'], 'CorporateSMCResult':result['corporate_smc'],
            'CAROSystemResult':next((r['SystemResult'] for r in result['results'] if r['RuleCode']=='CARO_2020'),''),
            'IFCSystemResult':next((r['SystemResult'] for r in result['results'] if r['RuleCode']=='IFC_143_3_I'),''),
            'CashFlowSystemResult':next((r['SystemResult'] for r in result['results'] if r['RuleCode']=='CASH_FLOW'),''),
            'ScheduleIIISystemResult':next((r['SystemResult'] for r in result['results'] if r['RuleCode']=='SCHEDULE_III'),''),
            'ProfessionalNotes':d.get('professional_notes','')
        }
        save_classification(summary)
        save_applicability_results(engagement_id,result['results'])
        if request.form.get('apply_to_engagement') == 'yes':
            # Deliberate opt-in: Stage 5 never silently changes Stage 4 engagement data.
            update_engagement(engagement_id, {
                'SmallCompany': 'Yes' if result['small_company'] else 'No'
            })
        return redirect(url_for('applicability',engagement_id=engagement_id))

    # GET: use saved classification if available; otherwise engagement defaults.
    saved=get_classification(engagement_id)
    if saved:
        facts={
            'entity_form':saved.get('EntityForm') or e.get('EntityType','private_ltd'),
            'assessment_date':saved.get('AssessmentDate') or assessment_date_from_year_ending(e.get('YearEnding','')),
            'listed':str(saved.get('Listed','No')).lower(),
            'in_process_listing':str(saved.get('InProcessListing','No')).lower(),
            'bank':str(saved.get('Bank','No')).lower(),
            'financial_institution':str(saved.get('FinancialInstitution','No')).lower(),
            'insurance':str(saved.get('Insurance','No')).lower(),
            'section8':str(saved.get('Section8','No')).lower(),
            'opc':str(saved.get('OPC','No')).lower(),
            'holding':str(saved.get('HoldingCompany','No')).lower(),
            'subsidiary':str(saved.get('SubsidiaryCompany','No')).lower(),
            'holding_subsidiary_of_non_msme':str(saved.get('HoldingSubsidiaryOfNonMSME','No')).lower(),
            'special_act':str(saved.get('SpecialActEntity','No')).lower(),
            'paid_up_capital':saved.get('PaidUpCapital',''),
            'reserves_surplus':saved.get('ReservesSurplus',''),
            'turnover_prior':saved.get('TurnoverPriorYear',''),
            'revenue_current':saved.get('RevenueCurrentYear',''),
            'borrowings_max':saved.get('BorrowingsMax',''),
            'net_worth':saved.get('NetWorth',''),
            'indas_required':str(saved.get('IndASRequired','No')).lower(),
            'accounting_framework':saved.get('AccountingFramework') or 'AS – Companies',
            'professional_notes':saved.get('ProfessionalNotes','')
        }
    else:
        facts=_applicability_initial_facts(e)
    result=classify(facts)
    old_results={r['RuleCode']:r for r in list_applicability(engagement_id)}
    for r in result['results']:
        if r['RuleCode'] in old_results:
            r['FinalResult']=old_results[r['RuleCode']].get('FinalResult') or r['SystemResult']
            r['Override']=old_results[r['RuleCode']].get('Override') or 'No'
            r['Rationale']=old_results[r['RuleCode']].get('Rationale') or r['Rationale']
    facts['assessment_date']=result['assessment_date']
    return render_template('applicability.html',
        engagement=e,client=c,entity_form_options=ENTITY_FORM_OPTIONS,
        facts=facts,classification=result)


if __name__=='__main__': ensure_master();ensure_register();DOCX_DIR.mkdir(parents=True,exist_ok=True);app.run(host='127.0.0.1',port=5000,debug=False)
