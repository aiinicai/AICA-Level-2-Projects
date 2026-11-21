"""Formula-backed workbook, plus existing CA narrative Word/PDF renderers."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import copy, datetime
import legacy_engine as engine
from asset_model import literal, money
from currency_rates import rate_decimal

def round_excel(n):return int(Decimal(str(n)).quantize(Decimal('1'),rounding=ROUND_HALF_UP))

def render_item(case,item):
    owner=case.person(item['owner_id']);it=copy.deepcopy(item)
    fields=it.setdefault('fields',{});fields['holder']=(owner.title+' '+owner.name).strip()
    relation=case.report_owner_relation(owner.id);fields['relation']='Self' if relation=='Applicant' else relation
    from asset_details import template_lines
    lines=template_lines(it)
    it['template_lines']=lines
    identity=case.parent_line(owner)
    it['desc']='; '.join(engine.mark(text,bold) for text,bold in lines)+'. '+engine.mark('Held by '+fields['holder'],True)+(' ('+identity+')' if identity else '')+' ('+relation+')'
    it['note']=''
    return it

def annual_lines(case,record):
    m=record.get('metadata',{});lines=[]
    if m.get('pan'):lines.append(('Pan: '+m['pan'],True))
    else:lines.append(('Annual Income',True))
    if m.get('acknowledgement'):lines.append(('As Per Income Tax Acknowledgement '+m['acknowledgement'],False))
    else:lines.append(('As Per Income Tax Acknowledgement / selected ITR',False))
    if m.get('filing_date'):lines.append(('Dated: '+m['filing_date'],False))
    if m.get('financial_year'):lines.append(('Financial Year: '+m['financial_year'],False))
    lines.append(('Assessment Year: '+record.get('year','[not supplied]'),False))
    review=record.get('reconciliation')
    if review:
        for key,label,include in [('total_income','Reviewed taxable / ITR income',True),('agricultural_income','Additional agricultural income',review['include_agriculture']),('exempt_income','Additional other exempt income (excludes agriculture)',review['include_other_exempt'])]:
            if include:lines.append((label+': INR '+format(review['values'][key],',.2f'),False))
        for key,rid in review.get('source_ids',{}).items():
            source=next((r for r in case.incomes if r['id']==rid),None)
            if source:lines.append((key+' source: '+source['document_type']+' / '+Path(source['source']).name,False))
        lines.append(('Reviewed additions do not overlap taxable income or each other.',False))
    return lines

def report_content(case):
    if not case.applicants or any(not p.name.strip() for p in case.applicants):raise ValueError('Name every applicant before exporting.')
    if not case.items:raise ValueError('Add at least one asset.')
    if any(not it.get('owner_id') for it in case.items):raise ValueError('Review ownership of migrated assets before export.')
    settings={k:case.settings.get(k,'') for k,_ in engine.App.SETTINGS_FIELDS}
    settings['letterhead_first_page']=case.settings.get('letterhead_first_page',True)
    settings['signature_enabled']=case.settings.get('signature_enabled',False);settings['signature_image']=case.settings.get('signature_image')
    from signature_asset import image_bytes
    image_bytes(settings)
    from currency_rates import validate_rate_for_report
    validate_rate_for_report(case.report)
    a={k:'' for k,_,_,_ in engine.App.APP_FIELDS};a.update(case.report)
    a['currency']=a.get('currency') or 'None'
    if a['currency']!='None' and rate_decimal(a.get('rate','0'))<=0:raise ValueError('Enter a positive exchange rate or choose None.')
    p=case.applicants[0];line=case.parent_line(p)
    a.update(title=p.title,name=p.name,passport=p.fields.get('passport_number',''),address=p.fields.get('address',''),parent='',relation='',co_name='')
    a['_bold']={k:v for k,v in p.bold.items()}
    # Rebind display names/relationships to current person records, not stale snapshots.
    refreshed=[render_item(case,item) for item in case.items]
    c=engine.build_content(dict(app=a,items=refreshed,settings=settings))
    if a['currency']!='None':
        # Preserve template per-item ROUND(...,0), not grand-total conversion.
        rate=rate_decimal(a['rate'])
        foreign=sum(round_excel(money(i['amount'])/rate)*(-1 if i['kind']=='liability' else 1) for i in refreshed)
        code,cname=a['currency'].split(' - ',1);c['fx_value']=foreign
        c['words'][1]=f'Net Assets of the applicant(s) are {code} {abs(foreign):,}/- ('+engine.intl_words(abs(foreign))+' '+cname+(' (Negative)' if foreign<0 else '')+' Approximately)'
    parties=[]
    for person in case.applicants:
        parts=[engine.mark((person.title+' '+person.name).strip(),person.bold.get('name',True))]
        parent=case.parent_line(person)
        if parent:parts.append(engine.mark(parent,person.bold.get('parent',True)))
        if person.fields.get('passport_number'):parts.append('bearing Passport No. '+engine.mark(person.fields['passport_number'],person.bold.get('passport',True)))
        if person.fields.get('address'):parts.append('residing at '+engine.mark(person.fields['address'],person.bold.get('address',True)))
        parties.append(', '.join(parts))
    who='; and '.join(parties)
    c['intro'][1]='We have been requested by '+who+' ("Applicant(s)"), to issue a Certificate on the net assets of the Applicant(s).'
    c['intro'][2]='The accompanying Statement of Net Assets as at '+engine.mark(a.get('statement_date',''),True)+' of '+who+', as prepared by the Applicant(s), contains their assets and liabilities for submission to '+a.get('authority','')+' in connection with '+a.get('purpose','')+'.'
    if len(case.applicants)>1:
        c['his']='their'
        c['resp'][0]='The preparation of the accompanying Statement is the responsibility of the applicants '+who+', including maintenance of relevant supporting records, internal control, an appropriate basis of preparation and reasonable estimates.'
        for key in ('resp','prac'):
            c[key]=[t.replace('his assets','their assets').replace('her assets','their assets') for t in c[key]]
        c['concl']=c['concl'].replace('his assets','their assets').replace('her assets','their assets')
    immovable=[i for i in refreshed if i['kind']=='asset' and i['category']=='Immovable Property']
    movable=[i for i in refreshed if i['kind']=='asset' and i['category']!='Immovable Property']
    liabilities=[i for i in refreshed if i['kind']=='liability']
    sums=[sum(i['amount'] for i in rows) for rows in (immovable,movable,liabilities)]
    c['totals']=dict(zip('ABC',sums))
    c['summary']=[('1','Immovable assets (Annexure A)',sums[0],'A'),('2','Movable assets (Annexure B)',sums[1],'B')]+([('3','Less: Liabilities (Annexure D)',sums[2],'C')] if liabilities else [])
    c['sections']=[('A','','ANNEXURE A - IMMOVABLE ASSETS',immovable,'TOTAL IMMOVABLE ASSETS :',sums[0]),('B','','ANNEXURE B - MOVABLE ASSETS',movable,'TOTAL MOVABLE ASSETS :',sums[1]),('C','Less: ','ANNEXURE D - LIABILITIES',liabilities,'TOTAL LIABILITIES :',sums[2])]
    from print_layout import layout_from
    annual=case.annual_rows() if 'annual income' in layout_from(case.report,case.settings)['sections'] else []
    c['annual_income']=[dict(person=case.person(r['person_id']).name,year=r.get('year',''),amount=r['values']['total_income']) for r in annual]
    # Extra report annexure explicitly outside the net-assets calculation.
    if annual:
        rows=[dict(desc='; '.join(engine.mark(text,bold) for text,bold in annual_lines(case,r))+'; '+engine.mark('Held by '+case.person(r['person_id']).name,True)+' ('+case.report_owner_relation(r['person_id'])+')',note='(Not added to net assets)',amount=r['values']['total_income']) for r in annual]
        c['sections'].append(('INCOME','','ANNEXURE C - ANNUAL INCOME (NOT INCLUDED IN NET ASSETS)',rows,'TOTAL ANNUAL INCOME :',sum(i['amount'] for i in rows)))
    c['enclosure']='Enclosures: Annexure A - Immovable assets; Annexure B - Movable assets'+('; Annexure C - Annual income' if annual else '')+('; Annexure D - Liabilities' if liabilities else '')
    return c

def export_workbook(case,path):
    """Same report/annexure organization as supplied templates; no stale sample identities.
    Dynamic rows, explicit ownership, and repaired formulas instead of broken #REF!/VBA UDF.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font,Alignment,PatternFill,Border,Side
    from openpyxl.workbook.properties import CalcProperties
    from openpyxl.worksheet.properties import PageSetupProperties
    c=report_content(case);wb=Workbook();wb.remove(wb.active)
    names=['SUMMARY','Sheet1','intro','certificate','immovable','movable']
    if c['annual_income']:names.append('annual income')
    if any(i['kind']=='liability' for i in case.items):names.append('liabilities')
    for name in names:wb.create_sheet(name)
    wb.calculation=CalcProperties(calcId=191029,fullCalcOnLoad=True)
    navy='173348';gold='B9955B';thin=Side(style='thin',color='CFD5DA')
    for ws in wb:
        ws.sheet_view.showGridLines=False
        for col,width in {'A':8,'B':44,'C':30,'D':21,'E':21,'F':21}.items():ws.column_dimensions[col].width=width
        ws.sheet_properties.pageSetUpPr=PageSetupProperties(fitToPage=True)
        ws.page_setup.orientation='portrait';ws.page_setup.paperSize=ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth=1;ws.page_setup.fitToHeight=0
        ws.page_margins.left=ws.page_margins.right=.35
    def put(ws,r,col,text,bold=False):
        cell=literal(ws.cell(r,col),text);cell.font=Font(name='Arial',size=11,bold=bold,color=navy if bold else '20272D');cell.alignment=Alignment(vertical='top',wrap_text=True);return cell
    def formula(ws,r,col,value,bold=False):
        cell=ws.cell(r,col,value);cell.font=Font(name='Arial',size=11,bold=bold);cell.alignment=Alignment(vertical='top',wrap_text=True);return cell
    def number(ws,r,col,value,bold=False):
        cell=formula(ws,r,col,value,bold);cell.number_format='#,##0.00;[Red](#,##0.00);"—"';return cell
    def title(ws,text):
        ws.merge_cells('A1:F1');cell=put(ws,1,1,text,True);cell.font=Font(name='Arial',size=16,bold=True,color=navy);ws.row_dimensions[1].height=32
        ws.merge_cells('A2:F2');put(ws,2,1,case.settings.get('firm_name',''),True)
    def header(ws,row,labels):
        for col,label in enumerate(labels,1):
            cell=put(ws,row,col,label,True);cell.fill=PatternFill('solid',fgColor='EDE8DE');cell.border=Border(bottom=Side(style='thin',color=gold))
        ws.row_dimensions[row].height=30
    def finish(ws):
        for row in ws:
            if ws.row_dimensions[row[0].row].height is None:ws.row_dimensions[row[0].row].height=25
        ws.print_area=f'A1:F{ws.max_row}';ws.print_options.horizontalCentered=True
    inp=wb['Sheet1']
    # Faithful field coordinates retained for the primary applicant and DOUBLE linking.
    for coord,val in {'B2':'Applicant','C2':'Father / spouse','D2':' having Passport Number ','F2':'Resident of','F3':case.applicants[0].fields.get('address',''),'D3':case.applicants[0].fields.get('passport_number',''),'F5':case.report.get('statement_date',''),'I3':case.report.get('udin','')}.items():put(inp,inp[coord].row,inp[coord].column,val,coord.endswith('2'))
    # Undo title merge conflict with original input coordinates.
    # Sheet1 has no report title in the source; its header/input structure is authoritative.
    for merged in list(inp.merged_cells.ranges):inp.unmerge_cells(str(merged))
    rate=case.report.get('rate','');currency=case.report.get('currency','None');code=currency.split(' - ')[0] if currency!='None' else ''
    symbol={'CAD':'CAD$','AUD':'AUD$','USD':'USD$','GBP':'UK£','EUR':'EUR€'}.get(code,code)
    put(inp,6,2,symbol);number(inp,6,3,float(rate_decimal(rate)) if rate else 0)
    # Excel row 11 is applicant, row 12 father, row 13 spouse, row 14 mother.
    primary=case.applicants[0]
    rows=[(primary.title,primary.name,'Applicant',primary.id),('Mr.',primary.fields.get('father_name',''),'Father of Applicant',''),('Mrs.',primary.fields.get('spouse_name',''),'Spouse of Applicant',''),('Mrs.',primary.fields.get('mother_name',''),'Mother of Applicant','')]
    for p in case.people[1:]:rows.append((p.title,p.name,'Co-applicant' if p.role=='Applicant' else case.owner_relation(p.id,primary.id),p.id))
    while len(rows)<6:rows.append(('','','',''))
    person_rows={};last=10+len(rows)
    for r,(t,n,role,pid) in enumerate(rows,11):
        put(inp,r,1,t);put(inp,r,2,n);put(inp,r,3,role)
        if pid:person_rows[pid]=r
    formula(inp,3,2,'=IF(ISNUMBER(SEARCH("applicant", C11)), A11 & " " & B11, "")')
    # Original DOUBLE C3 function, exactly for original 6-row range; expanded only if needed.
    c3='=IFERROR(IF(INDEX(B11:B{last},MATCH("Spouse of Applicant",C11:C{last},0))<>"","W/o Sh. "&INDEX(B11:B{last},MATCH("Spouse of Applicant",C11:C{last},0)),1/0)," "&IFERROR(IF(OR(ISNUMBER(SEARCH("Ms.",A11)),ISNUMBER(SEARCH("Ms",A11))),"D/o Sh. ","S/o Sh. ")&INDEX(B11:B{last},MATCH("Father of Applicant",C11:C{last},0)),""))'.format(last=last)
    if primary.use_father or primary.parent_override:put(inp,3,3,case.parent_line(primary))
    elif case.formula_mode=='single':
        c3=c3.replace('IF(INDEX','IF(AND(ISERROR(SEARCH("Mrs",A13)),INDEX',1).replace('<>"","W/o','<>""),"W/o',1);formula(inp,3,3,c3)
    else:formula(inp,3,3,c3)
    if len(case.applicants)>1:
        p=case.applicants[1];put(inp,4,2,p.title+' '+p.name);put(inp,4,3,case.parent_line(p));put(inp,4,4,p.fields.get('passport_number',''))
    formula(inp,7,2,'=IF(OR(ISBLANK(Sheet1!B4),Sheet1!B4=0),Sheet1!B3,Sheet1!B3 & " & " & Sheet1!B4)')
    formula(inp,8,6,'="("&CONCATENATE(F5,F3)&")"')
    countries={'CAD':'Canada','AUD':'Australia','USD':'USA','GBP':'UK','EUR':'Europe'}
    formula(inp,2,7,'=IF(A11="Mr."," He wants to go to"," She wants to go to")')
    formula(inp,3,7,'=" "&IF(B6="CAD$","Canada",IF(B6="AUD$","Australia",IF(B6="USD$","USA",IF(B6="UK£","UK",IF(B6="EUR€","Europe","")))))')
    if case.report.get('country') and case.report['country']!='Other / choose currency':put(inp,3,7,' '+case.report['country'])
    title(wb['SUMMARY'],'Net Asset Report — summary')
    header(wb['SUMMARY'],4,['#','Applicant','Relationship line','Passport','Address',''])
    for r,p in enumerate(case.applicants,5):
        for col,val in enumerate([str(r-4),p.title+' '+p.name,case.parent_line(p),p.fields.get('passport_number',''),p.fields.get('address','')],1):put(wb['SUMMARY'],r,col,val,col in (2,3,4,5))
        wb['SUMMARY'].row_dimensions[r].height=65
    intro=wb['intro'];title(intro,'NET ASSET REPORT');header(intro,4,['#','Particular','Details','','',''])
    for r,(label,val) in enumerate([('Applicant(s)','; '.join(p.title+' '+p.name for p in case.applicants)),('Residential address','; '.join(p.fields.get('address','') for p in case.applicants)),('Passport(s)','; '.join(p.fields.get('passport_number','') for p in case.applicants)),('Purpose',case.report.get('purpose','')),('Country',(case.report.get('country') or countries.get(code,''))),('Exchange rate',rate),('Statement date',case.report.get('statement_date','')),('UDIN',case.report.get('udin',''))],5):
        put(intro,r,1,str(r-4),True);put(intro,r,2,label);intro.merge_cells(start_row=r,start_column=3,end_row=r,end_column=6);put(intro,r,3,val,True);intro.row_dimensions[r].height=45
    display_items={i['id']:i for sec in c['sections'] for i in sec[3] if i.get('id')}
    totals={}
    display_items={i['id']:i for section in c['sections'] for i in section[3] if 'id' in i}
    for name,caption,selected,group in [('immovable','DETAIL OF IMMOVABLE ASSETS',[i for i in case.items if i['kind']=='asset' and i['category']=='Immovable Property'],'A'),('movable','DETAIL OF MOVABLE ASSETS',[i for i in case.items if i['kind']=='asset' and i['category']!='Immovable Property'],'B')]+([('liabilities','DETAIL OF LIABILITIES',[i for i in case.items if i['kind']=='liability'],'D')] if 'liabilities' in wb.sheetnames else []):
        ws=wb[name];ws.column_dimensions['F'].width=3;title(ws,caption);put(ws,8,5,'Annexure-'+group,True)
        header(ws,9,['Sr. No.','Assets Details','Ownership','Amount (INR)','Amount ('+(code or 'not selected')+')']);put(ws,10,1,group,True);put(ws,10,2,'IMMOVABLE PROPERTY' if group=='A' else 'MOVABLE PROPERTY' if group=='B' else 'LIABILITIES',True)
        amount_rows=[];r=11 if group=='A' else 12
        for serial,raw in enumerate(selected,1):
            it=display_items[raw['id']];owner=case.person(it['owner_id']);lines=it['template_lines']
            put(ws,r,1,str(serial));amount_rows.append(r)
            for offset,(text,bold) in enumerate(lines):
                put(ws,r+offset,2,text,bold);ws.row_dimensions[r+offset].height=max(26,18*((len(text)//42)+1))
            if owner.id in person_rows:
                pr=person_rows[owner.id];formula(ws,r,3,f'=CONCATENATE(Sheet1!A{pr}&" "&Sheet1!B{pr})')
            else:put(ws,r,3,owner.title+' '+owner.name)
            put(ws,r+1,3,'('+case.report_owner_relation(owner.id)+')',True)
            identity=case.parent_line(owner)
            if identity:put(ws,r+2,3,identity)
            number(ws,r,4,it['amount']);formula(ws,r,5,f'=IF(Sheet1!$C$6>0,ROUND(D{r}/Sheet1!$C$6,0),0)');ws.cell(r,5).number_format='#,##0'
            ws.row_dimensions[r+1].height=max(ws.row_dimensions[r+1].height or 26,18*((len(case.report_owner_relation(owner.id))//27)+1))
            r+=max(3,len(lines))+1
        put(ws,r,2,'Total of '+('Immovable Assets' if group=='A' else 'Movable Assets' if group=='B' else 'Liabilities'),True)
        for col in ('D','E'):number(ws,r,4 if col=='D' else 5,'=SUM('+col+'11:'+col+str(r-1)+')' if amount_rows else '=0',True)
        totals[name]=r;ws.print_title_rows='9:10'
    if 'annual income' in wb.sheetnames:
        ws=wb['annual income'];ws.column_dimensions['F'].width=3;title(ws,'DETAIL OF ANNUAL INCOME');put(ws,8,5,'Annexure-C',True)
        header(ws,11,['','Details','Ownership','Amount (INR)','Amount ('+(code or 'not selected')+')']);put(ws,12,1,'C.',True);put(ws,12,2,'Annual Income',True)
        annual=case.annual_rows() if 'annual income' in __import__('print_layout').layout_from(case.report,case.settings)['sections'] else [];r=14;amount_rows=[]
        for rec in annual:
            person=case.person(rec['person_id']);lines=annual_lines(case,rec);amount_rows.append(r)
            put(ws,r,1,'*',True)
            for offset,(text,bold) in enumerate(lines):put(ws,r+offset,2,text,bold);ws.row_dimensions[r+offset].height=max(26,18*((len(text)//42)+1))
            put(ws,r,3,person.title+' '+person.name);put(ws,r+1,3,'('+case.report_owner_relation(person.id)+')',True)
            number(ws,r,4,rec['values']['total_income']);number(ws,r,5,f'=IF(Sheet1!$C$6>0,ROUND(D{r}/Sheet1!$C$6,0),0)')
            r+=max(3,len(lines))+2
        put(ws,r,2,'Total annual income',True);number(ws,r,4,f'=SUM(D14:D{r-1})' if amount_rows else '=0',True);number(ws,r,5,f'=SUM(E14:E{r-1})' if amount_rows else '=0',True);totals['annual income']=r
        ws.print_title_rows='10:12'
    ws=wb['certificate'];title(ws,'NET ASSET REPORT')
    ws.merge_cells('A4:F4');put(ws,4,1,'; and '.join(p.title+' '+p.name+', '+case.parent_line(p) for p in case.applicants),True);ws.row_dimensions[4].height=60
    ws.merge_cells('A5:F5');put(ws,5,1,'Statement as at '+case.report.get('statement_date','')+' - '+case.report.get('purpose',''))
    ws.merge_cells('A7:F7');put(ws,7,1,'Statement of assets and liabilities based on the documents supplied',True)
    ws.merge_cells('A11:F11');put(ws,11,1,'; and '.join(p.title+' '+p.name+', '+case.parent_line(p)+(' having Passport Number '+p.fields['passport_number'] if p.fields.get('passport_number') else '') for p in case.applicants),True);ws.row_dimensions[11].height=60
    ws.merge_cells('A12:F12');put(ws,12,1,'Resident of: '+'; '.join(p.fields.get('address','') for p in case.applicants),True);ws.row_dimensions[12].height=45
    header(ws,17,['#','Particulars','','Annexure','Value in INR','Value in '+(code or 'not selected')])
    for row,name,label,annexure in [(18,'immovable','Immovable Assets','A'),(19,'movable','Movable Assets','B')]+([(20,'liabilities','Less: Liabilities','D')] if 'liabilities' in totals else []):
        put(ws,row,1,str(row-17));put(ws,row,2,label);put(ws,row,4,annexure);number(ws,row,5,f"='{name}'!D{totals[name]}");number(ws,row,6,f"='{name}'!E{totals[name]}")
    netrow=21 if 'liabilities' in totals else 20;put(ws,netrow,2,'Net Assets',True)
    number(ws,netrow,5,'=E18+E19-E20' if 'liabilities' in totals else '=E18+E19',True);number(ws,netrow,6,'=F18+F19-F20' if 'liabilities' in totals else '=F18+F19',True)
    for col in ('E','F'):number(ws,22 if col=='E' else 24,5,f'={col}{netrow}',True)
    ws.merge_cells('A23:F23');put(ws,23,1,'Indian Rupees '+engine.indian_words(abs(float(case.totals()['net'])))+(' (Negative)' if case.totals()['net']<0 else '')+' only',True);ws.row_dimensions[23].height=50
    if 'annual income' in totals:
        header(ws,27,['','Annual Income (separate)','','Annexure','Value in INR','Value in '+(code or 'not selected')]);put(ws,28,4,'C',True)
        number(ws,28,5,f"='annual income'!D{totals['annual income']}",True);number(ws,28,6,f"='annual income'!E{totals['annual income']}",True)
        number(ws,29,5,'=SUM(E28:E28)',True);number(ws,29,6,'=SUM(F28:F28)',True);put(ws,30,2,'Annual income is not added to net assets.',True)
    ws.merge_cells('A34:F34');put(ws,34,1,'Prepared from documents supplied. Practitioner must review supporting evidence, dates, valuation and report wording before issue.');ws.row_dimensions[34].height=50
    put(ws,39,1,'Place: '+case.settings.get('place',''));put(ws,40,1,'Date: '+case.report.get('cert_date',''));put(ws,39,5,'For '+case.settings.get('firm_name',''),True);put(ws,40,5,case.settings.get('designation','Chartered Accountant'))
    put(ws,46,5,case.settings.get('partner',''),True);put(ws,47,5,'Membership No. '+case.settings.get('mno',''));put(ws,47,1,'UDIN: '+case.report.get('udin',''),True);put(ws,48,5,'FRN: '+case.settings.get('frn',''))
    from signature_asset import excel_signature
    for name in ('immovable','movable','annual income','liabilities'):
        if name not in wb.sheetnames:continue
        sh=wb[name];r=sh.max_row+2
        put(sh,r,2,'For '+case.settings.get('firm_name',''),True);put(sh,r+3,2,case.settings.get('partner',''),True);put(sh,r+4,2,'UDIN: '+case.report.get('udin',''),True)
        sh.row_dimensions[r+1].height=50;excel_signature(sh,case.settings,'D'+str(r))
    excel_signature(wb['certificate'],case.settings,'E42')
    meta=case.report.get('rate_meta',{})
    if meta:
        r=wb['intro'].max_row+2;put(wb['intro'],r,2,'Rate source/date');wb['intro'].merge_cells(start_row=r,start_column=3,end_row=r,end_column=6);put(wb['intro'],r,3,__import__('currency_rates').quote_caption(case.report));wb['intro'].row_dimensions[r].height=45
    from letterpad_asset import add_excel_letterpad
    add_excel_letterpad(wb,case)
    for sh in wb:finish(sh)
    # Sheet1 retains operational inputs beyond its print range, not private raw passport dumps.
    # Like the supplied operational input sheet, complete passport fields remain
    # outside the print area. Raw OCR remains in case JSON, not printed reports.
    from asset_model import PASSPORT_FIELDS
    for col,text in enumerate(['Person ID','Person name','Passport field','Reviewed value'],11):put(inp,1,col,text,True)
    metadata_row=2
    for person in case.people:
        for key in PASSPORT_FIELDS:
            value=person.fields.get(key,'')
            if not value:continue
            for start in range(0,len(str(value)),30000):
                for col,text in enumerate([person.id,person.name,key,str(value)[start:start+30000]],11):put(inp,metadata_row,col,text)
                metadata_row+=1
    inp.print_area=f'A1:I{max(last,16)}'
    from print_layout import apply_workbook_layout
    apply_workbook_layout(wb,case)
    wb.save(path)
    from formula_cache import write_generated_caches
    write_generated_caches(wb,case,path)
    from page_background import excel_background
    excel_background(path,case)

def export(case,path,kind):
    if kind=='xlsx':return export_workbook(case,path)
    content=report_content(case)
    from report_documents import export_pdf,export_word
    if kind=='pdf':
        # Always render the fixed Sandeep-style report layout from the
        # current case data. Never copy pages from an imported client's PDF.
        export_pdf(case,content,str(path))
    else:
        export_word(case,content,str(path))
    if kind=='pdf':
        from preview_render import apply_pdf_page_range
        apply_pdf_page_range(path,case.report.get('print_layout',{}).get('pdf_page_range',''))
