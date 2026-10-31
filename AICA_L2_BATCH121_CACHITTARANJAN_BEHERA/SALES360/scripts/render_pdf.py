"""Versioned deterministic document renderer. Input is a server-authorized JSON snapshot."""
import sys,json,os,html
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'.tools/python-packages'))
import arabic_reshaper
from bidi.algorithm import get_display
from decimal import Decimal,ROUND_HALF_UP
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.colors import HexColor,white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table,TableStyle,Paragraph
from reportlab.lib.styles import ParagraphStyle

FONT=os.environ.get('SALES360_FONT',r'C:\Windows\Fonts\arial.ttf')
BOLD=os.environ.get('SALES360_FONT_BOLD',r'C:\Windows\Fonts\arialbd.ttf')
pdfmetrics.registerFont(TTFont('Body',FONT));pdfmetrics.registerFont(TTFont('Strong',BOLD))
NAVY=HexColor('#173a42');TEAL=HexColor('#197e6c');MUTED=HexColor('#70877e');LINE=HexColor('#dfe8e2')
def money(n):return f'{Decimal(str(n)):,.2f}'
def shaped(v):
    v=str(v)
    return get_display(arabic_reshaper.reshape(v)) if any('\u0600'<=ch<='\u06ff' for ch in v) else v
def text(v):return html.escape(shaped(v))
normal=ParagraphStyle('body',fontName='Body',fontSize=9,leading=13,textColor=NAVY)
small=ParagraphStyle('small',parent=normal,fontSize=7,leading=10)
def para(v,style=normal):return Paragraph(text(v).replace('\n','<br/>'),style)
def table(c,rows,widths,x,y,header=True,font=8,pad=10):
    style=ParagraphStyle('cell',parent=normal,fontSize=font,leading=font*1.45)
    data=[[para(v,style) for v in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1 if header else 0)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#edf4ef') if header else white),('LINEBELOW',(0,0),(-1,0),.7,LINE),('LINEBELOW',(0,1),(-1,-1),.4,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7)]))
    w,h=t.wrap(sum(widths),2000);t.drawOn(c,x,y-h);return y-h
def base(c,title,page,total,size,d):
    c.setPageSize(size);w,h=size;c.setFillColor(TEAL);c.roundRect(35,h-62,31,31,6,fill=1,stroke=0);c.setFillColor(white);c.setFont('Strong',20);c.drawString(43,h-54,'S');c.setFillColor(NAVY);c.setFont('Strong',17);c.drawString(77,h-48,'SALES360');c.setFont('Body',8);c.setFillColor(MUTED);c.drawRightString(w-35,h-46,'SYNTHETIC DEMONSTRATION | AED')
    c.setStrokeColor(LINE);c.line(35,h-79,w-35,h-79);c.setFillColor(NAVY);c.setFont('Strong',19);c.drawString(35,h-111,title)
    c.setFont('Body',7);c.setFillColor(MUTED);c.drawString(35,26,'SALES360 | Controlled template v1.0 | Asia/Dubai');c.drawRightString(w-35,26,f'Page {page}/{total}');c.setStrokeColor(LINE);c.line(35,40,w-35,40)
    if d.get('state')!='Approved' and 'state' in d:
        c.saveState();c.translate(w/2,h/2);c.rotate(35);c.setFillColor(HexColor('#e8eeea'));c.setFont('Strong',66);c.drawCentredString(0,0,'UNAPPROVED');c.restoreState()
def meta(c,d,y,width):
    pairs=[['Client',d.get('customer',''),'Job no.',d.get('job','')],['Project',d.get('project',''),'Certificate',d.get('reference','')],['Services',d.get('category','Design'),'Claim date',d.get('claim_date','')],['Payment terms',f"{d.get('terms',30)} days",'Due date',d.get('due_date','')]]
    return table(c,pairs,[width*.17,width*.43,width*.16,width*.24],35,y,False,7 if width>600 else 8,4 if width>600 else 10)
def signatures(c,d,y,width):
    approvals=d.get('approvals',[]);roles=['Prepared By','Reviewer 1','Reviewer 2','Approver'];rows=[roles,[]]
    for role in roles:
        if role=='Prepared By':value=f"{d.get('prepared_by','')}\n{d.get('claim_date','')}"
        else:
            a=next((a for a in approvals if a.get('role')==role),None);value=f"{a['actor']}\n{str(a['at'])[:10]}" if a else 'Pending / no approval evidence'
        rows[1].append(value)
    return table(c,rows,[width/4]*4,35,y,True,7)
def certificate(d,path):
    c=canvas.Canvas(path,pagesize=A4,invariant=1);c.setTitle('Payment certificate '+d['reference']);w,h=A4;cw=w-70
    base(c,'PAYMENT CERTIFICATE',1,3,A4,d);y=meta(c,d,h-130,cw)
    y-=25;c.setFillColor(MUTED);c.setFont('Body',8);c.drawString(35,y,'APPROVED CONTRACT FEE BASIS');c.setFillColor(NAVY);c.setFont('Strong',15);c.drawString(35,y-24,'AED '+money(d['fee']));c.setFont('Body',8);c.setFillColor(MUTED);c.drawString(35,y-42,'Pre/post-contract split: not configured; total approved basis shown.')
    rows=[['Assessment summary','Reference','AED'],['Work executed - cumulative assessment','Appendix A',money(d['cumulative'])],['Deductions / advance recovery','No adjustments',money(0)],['Separate advance addition','Included once in milestones',money(0)],['Sub total','',money(d['cumulative'])],['Less previous certified amounts','Appendix B',money(d['previous'])],['Net amount due for this certificate',d['reference'],money(d['settlement'])]]
    y=table(c,rows,[cw*.49,cw*.28,cw*.23],35,y-65,True,8);p=para(d['words']);_,ph=p.wrap(cw,70);p.drawOn(c,35,y-22-ph)
    p=para('Certificate settlement is net of invoice VAT. Final invoice = settlement + reviewed VAT, with any authorized adjustments shown separately. This certificate is not a tax invoice.',small);_,ph=p.wrap(cw,70);p.drawOn(c,35,y-65-ph)
    signatures(c,d,150,cw);c.showPage()
    size=landscape(A4);w,h=size;cw=w-70;base(c,f"{d.get('category','Design').upper()} FEES - APPENDIX A",2,3,size,d);y=meta(c,d,h-130,cw);c.setFont('Strong',9);c.setFillColor(NAVY);c.drawString(35,y-22,'GENERAL SERVICES PAYMENT SCHEDULE');c.setFont('Body',7);c.setFillColor(MUTED);c.drawString(35,y-36,'Completion percentages apply to each stage. Current assessment is cumulative; this payment is the difference.')
    rows=[['Stage / milestone','Contract\n%','Contract\nAED','Claimed\n%','Claimed\nAED','Previously\n%','Previously\nAED','Current\n%','Current\nAED','This payment\nAED']]
    sums=[Decimal(0)]*5
    for i,s in enumerate(d['stages']):
        get=lambda k:s.get(k,s.get(k.lower(),0));amount=Decimal(str(d['fee']))*Decimal(str(get('Allocation')))/100
        calc=lambda k:(amount*Decimal(str(get(k)))/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        claimed,previous,current=calc('Claimed'),calc('Previous'),calc('Assessed');settlement=current-previous
        rows.append([f"{i+1}. {get('Name')}",get('Allocation'),money(amount),get('Claimed'),money(claimed),get('Previous'),money(previous),get('Assessed'),money(current),money(settlement)])
        for j,v in enumerate([amount,claimed,previous,current,settlement]):sums[j]+=v
    rows.append(['TOTAL','100',money(sums[0]),'',money(sums[1]),'',money(sums[2]),'',money(sums[3]),money(sums[4])]);ratios=[.20,.05,.105,.055,.10,.055,.10,.055,.10,.08];ratios=[r/sum(ratios) for r in ratios];y=table(c,rows,[cw*r for r in ratios],35,y-48,True,6.3,5)
    if y<100:raise ValueError('Fee schedule exceeds controlled one-page template; paginate before approving.')
    c.setFont('Body',7);c.setFillColor(MUTED);c.drawString(35,y-22,'Advance policy: included as a milestone. No separate duplicate cash advance added.');signatures(c,d,125,cw);c.showPage()
    w,h=A4;cw=w-70;base(c,'PAYMENT CERTIFICATE APPENDIX - B',3,3,A4,d);y=meta(c,d,h-130,cw);c.setFont('Strong',10);c.setFillColor(NAVY);c.drawString(35,y-30,'PREVIOUS CERTIFIED AMOUNTS');p=para('Basis: previous approved certificates, not proof of cash collection. Actual receipts remain in the customer ledger.',small);_,ph=p.wrap(cw,60);p.drawOn(c,35,y-50-ph)
    previous=d.get('previous_certificates',[]);rows=[['Previous certificate','Certificate date','Certified amount (AED)']]+[[p['reference'],p['claim_date'],money(p['settlement'])] for p in previous];rows+=[['Total previous certified amounts','',money(d['previous'])],['Number of previous certificates',str(len(previous)),'']];y=table(c,rows,[cw*.45,cw*.25,cw*.30],35,y-90,True,9)
    if y<230:raise ValueError('Previous certificates exceed single-page appendix; template pagination required.')
    c.setFont('Body',8);c.setFillColor(MUTED);c.drawString(35,y-30,'Period ending: '+d['claim_date']+' | Payment due: '+d['due_date']);signatures(c,d,180,cw);c.save()
def statement(d,path):
    c=canvas.Canvas(path,pagesize=A4,invariant=1);rows=d['rows'];chunks=[rows[i:i+23] for i in range(0,len(rows),23)] or [[]]
    for i,chunk in enumerate(chunks):
        base(c,'CUSTOMER STATEMENT',i+1,len(chunks),A4,d);w,h=A4;c.setFont('Strong',11);c.drawString(35,h-140,shaped(d['customer']));c.setFont('Body',9);c.setFillColor(MUTED);c.drawString(35,h-160,'As of '+d['asOf']+' | AED | All projects');data=[['Date','Reference','Debit','Credit','Balance']]+[[r['date'],r['reference'],money(r['debit']),money(r['credit']),money(r['balance'])] for r in chunk];y=table(c,data,[65,155,85,85,w-70-390],35,h-190,True,7)
        if i==len(chunks)-1:c.setFont('Strong',11);c.setFillColor(NAVY);c.drawRightString(w-35,y-30,'Closing balance: AED '+money(d['closingBalance']))
        c.showPage()
    c.save()
def analytics(d,path):
    from reportlab.platypus import SimpleDocTemplate,LongTable,Spacer
    size=landscape(A4);width=size[0]-64
    rows=d['rows'];keys=[k for k in (rows[0] if rows else {}) if not k.endswith('_id') and k not in ('id','company_id')]
    story=[para('SALES360 | '+d['company'],ParagraphStyle('title',parent=normal,fontName='Strong',fontSize=18,leading=24)),Spacer(1,12),para(d['kind'].replace('-',' ').title(),ParagraphStyle('heading',parent=normal,fontName='Strong',fontSize=14,leading=20)),Spacer(1,6),para(d['start']+' to '+d['end']+' | AED | Asia/Dubai business dates'),Spacer(1,8),para(d['basis']),Spacer(1,14)]
    story.extend([para('Customer: '+d.get('customer_filter','All customers')+' | Project: '+d.get('project_filter','All projects'),small),Spacer(1,10)])
    # All current report schemas fit in a single landscape column band.
    bands=[keys[i:i+10] for i in range(0,len(keys),10)] or [[]]
    for band_index,band in enumerate(bands):
        if not band:story.append(para('No records match this selection.'));continue
        if band_index:story.extend([Spacer(1,16),para('Additional columns (same row order)')])
        data=[[para(k.replace('_',' ').title(),small) for k in band]]
        for row in rows:data.append([para(money(row[k]) if isinstance(row.get(k),(float,int)) and not isinstance(row.get(k),bool) else row.get(k,''),small) for k in band])
        t=LongTable(data,colWidths=[width/len(band)]*len(band),repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#e5f1ee')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,LINE),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]));story.append(t)
    story.extend([Spacer(1,16),para('Totals: '+' | '.join(k.replace('_',' ')+': '+money(v) for k,v in d.get('totals',{}).items())),Spacer(1,8),para('Generated '+d['generated_at']+' | '+str(d['row_count'])+' rows. Internal management report; not a statutory invoice.',small)])
    def footer(c,doc):
        c.setFont('Body',7);c.setFillColor(MUTED);c.drawString(32,20,'SALES360 | '+d['kind']+' | AED');c.drawRightString(size[0]-32,20,'Page '+str(doc.page))
    SimpleDocTemplate(path,pagesize=size,leftMargin=32,rightMargin=32,topMargin=30,bottomMargin=40).build(story,onFirstPage=footer,onLaterPages=footer)

def tax_invoice(d,path):
    from reportlab.platypus import SimpleDocTemplate,Spacer,LongTable
    supplier=d['supplier_snapshot'];buyer=d['customer_snapshot'];width=A4[0]-72
    title=ParagraphStyle('invoice-title',parent=normal,fontName='Strong',fontSize=23,leading=29)
    heading=ParagraphStyle('invoice-heading',parent=normal,fontName='Strong',fontSize=12,leading=17)
    story=[para('TAX INVOICE',title),Spacer(1,14),para(supplier['legal_name'],heading),para(supplier['registered_address']),para('Supplier TRN: '+supplier['trn']),Spacer(1,16),para('Bill to',heading),para(buyer['name']),para(buyer['address']),para('Customer TRN: '+buyer.get('trn','') if buyer.get('trn') else 'Customer TRN: not provided'),Spacer(1,16)]
    facts=[['Invoice number',d['reference']],['Invoice issue date',d['issue_date']],['Date of supply',d['supply_date']],['VAT tax point',d['tax_point']],['Currency','AED'],['Treatment',d['treatment']]]
    t=Table([[para(k,small),para(v,normal)] for k,v in facts],colWidths=[width*.35,width*.65]);t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),HexColor('#f0f5f3')),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,18)])
    rate='5%' if d['treatment']=='Standard rated' else '0%'
    lines=[['Description','Qty','Unit price AED','Discount AED','Net AED','VAT rate','VAT AED'],[d['description'],'1',money(d['net']),'0.00',money(d['net']),rate,money(d['vat'])]]
    t=LongTable([[para(v,small) for v in row] for row in lines],colWidths=[width*.30,width*.06,width*.15,width*.13,width*.13,width*.09,width*.14],repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#e5f1ee')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.5,LINE),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story.extend([t,Spacer(1,20)])
    for label,value in [('Subtotal excluding VAT',d['net']),('Total VAT',d['vat']),('Total payable including VAT',d['total'])]:story.extend([para(label+' (AED): '+money(value),heading),Spacer(1,6)])
    if supplier.get('bank_details'):story.extend([Spacer(1,18),para('Payment details',heading),para(supplier['bank_details'])])
    if supplier.get('legal_name','').startswith('Imaginary') or buyer.get('name','').startswith('TEST '):story.extend([Spacer(1,16),para('FICTIONAL TEST DATA — for software testing only',small)])
    def footer(c,doc):
        c.setFont('Body',7);c.setFillColor(MUTED);c.drawString(36,24,'SALES360 | '+d['reference']+' | AED');c.drawRightString(A4[0]-36,24,'Page '+str(doc.page))
    SimpleDocTemplate(path,pagesize=A4,leftMargin=36,rightMargin=36,topMargin=36,bottomMargin=46,title='Tax Invoice '+d['reference']).build(story,onFirstPage=footer,onLaterPages=footer)

if __name__=='__main__':
    kind,source,target=sys.argv[1:];d=json.load(open(source,encoding='utf-8'));{'certificate':certificate,'statement':statement,'analytics':analytics,'tax-invoice':tax_invoice}[kind](d,target)
