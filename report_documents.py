"""Paginated report documents from the same template semantics and print configuration."""
import io
from decimal import Decimal
from xml.sax.saxutils import escape
import legacy_engine as engine
from asset_model import money
from currency_rates import rate_decimal,quote_caption
from print_layout import layout_from
from letterpad_asset import get_bytes,effective_letterpad
from signature_asset import image_bytes,fit_dimensions

def rows_for(case,content,name):
    from report_export import annual_lines,round_excel
    code=case.report.get('currency','None').split(' - ')[0];rate=rate_decimal(case.report['rate']) if code!='None' else None
    if name=='annual income':
        records=[]
        for rec in case.annual_rows():
            owner=case.person(rec['person_id']);records.append((annual_lines(case,rec),owner,rec['values']['total_income']))
    else:
        index={'immovable':0,'movable':1,'liabilities':2}[name]
        records=[(i['template_lines'],case.person(i['owner_id']),i['amount']) for i in content['sections'][index][3]]
    return [(str(index),lines,owner,case.report_owner_relation(owner.id),case.parent_line(owner),money(amount),round_excel(money(amount)/rate) if rate else None) for index,(lines,owner,amount) in enumerate(records,1)]

CAPTIONS={'immovable':('ANNEXURE A','DETAIL OF IMMOVABLE ASSETS'),'movable':('ANNEXURE B','DETAIL OF MOVABLE ASSETS'),'annual income':('ANNEXURE C','DETAIL OF ANNUAL INCOME'),'liabilities':('ANNEXURE D','DETAIL OF LIABILITIES')}

def foreign_caption(case):
    code=case.report.get('currency','None').split(' - ')[0]
    return 'Amount ('+code+')' if code!='None' else 'Foreign amount'

def summary_rows(case,c):
    """Parallel INR/FX columns follow the source certificate, never add income to assets."""
    result=[]
    for name,label in [('immovable','Immovable assets (Annexure A)'),('movable','Movable assets (Annexure B)')]+([('liabilities','Less: Liabilities (Annexure D)')] if any(i['kind']=='liability' for i in case.items) else []):
        rows=rows_for(case,c,name)
        result.append((label,sum(r[5] for r in rows),sum(r[6] for r in rows) if rows and rows[0][6] is not None else None))
    result.append(('Net assets (A+B-D)' if any(i['kind']=='liability' for i in case.items) else 'Net assets (A+B)',c['nw'],c.get('fx_value') if case.report.get('currency','None')!='None' else None))
    return result

def income_summary(case,c):
    if not c['annual_income']:return []
    rows=rows_for(case,c,'annual income')
    return [('Total annual income (Annexure C; NOT included in net assets)',sum(r[5] for r in rows),sum(r[6] for r in rows) if rows and rows[0][6] is not None else None)]

def export_word(case,c,path):
    from docx import Document
    from docx.shared import Mm,Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc=Document();sec=doc.sections[0];layout=layout_from(case.report,case.settings);m=layout['margins_mm'];letterpad=effective_letterpad(case.settings)
    sec.page_width=Mm(layout['width_mm']);sec.page_height=Mm(layout['height_mm'])
    for side in ('top','bottom','left','right'):setattr(sec,side+'_margin',Mm(m[side]))
    sec.header_distance=Mm(4);sec.footer_distance=Mm(4)
    style=doc.styles['Normal'];style.font.name='Arial';style.font.size=Pt(10.5);style.paragraph_format.space_after=Pt(6)
    usable=layout['width_mm']-m['left']-m['right']
    def rich(paragraph,text,bold=False):
        for part,emphasis in engine.segments(text):paragraph.add_run(part).bold=bold or emphasis
    def p(text='',bold=False,heading=False):
        para=doc.add_paragraph();rich(para,text,bold)
        if heading:para.alignment=WD_ALIGN_PARAGRAPH.CENTER;para.runs[0].font.size=Pt(15)
        return para
    def image(paragraph,data,maxw=50,maxh=20):
        from PIL import Image
        raw=Image.open(io.BytesIO(data));w,h=fit_dimensions(data,maxw,maxh);paragraph.add_run().add_picture(io.BytesIO(data),width=Mm(w),height=Mm(h))
    background=get_bytes(letterpad,'background')
    if background:
        from page_background import word_background
        word_background(sec,background,layout)
    else:
        for position,container in [('header',sec.header),('footer',sec.footer)]:
            data=get_bytes(letterpad,position)
            if data:image(container.paragraphs[0],data,usable,25 if position=='header' else 18)
            elif position=='header':rich(container.paragraphs[0],case.settings.get('firm_name',''),True)
    if not letterpad.get('include_first_page',case.settings.get('letterhead_first_page',True)):sec.different_first_page_header_footer=True
    def signer():
        p('For '+case.settings.get('firm_name',''),True)
        data=image_bytes(case.settings)
        if data:image(doc.add_paragraph(),data)
        for label in ('partner','designation','frn','mno'):
            value=case.settings.get(label,'')
            if value:p(({'frn':'FRN: ','mno':'Membership No. '}.get(label,''))+value,label=='partner')
        p('UDIN: '+case.report.get('udin',''),True);p('Place: '+case.settings.get('place','')+' | Date: '+case.report.get('cert_date',''))
    sections=[s for s in layout['sections'] if s not in ('annual income','liabilities') or (s=='annual income' and bool(c['annual_income'])) or (s=='liabilities' and any(i['kind']=='liability' for i in case.items))]
    for section_index,name in enumerate(sections):
        if section_index:doc.add_page_break()
        if name=='intro':
            p('NET ASSET REPORT',True,True)
            for text in c['intro']:p(text)
            if case.report.get('country'):p('Destination country: '+case.report['country'])
        elif name=='certificate':
            p('NET ASSET REPORT',True,True)
            table=doc.add_table(rows=1,cols=3);table.style='Table Grid'
            for cell,title in zip(table.rows[0].cells,['Particulars','Amount (INR)',foreign_caption(case)]):rich(cell.paragraphs[0],title,True)
            for label,amount,foreign in summary_rows(case,c)+income_summary(case,c):
                cells=table.add_row().cells;cells[0].text=label;cells[1].text=engine.fmt_acct(amount);cells[2].text='-' if foreign is None else format(foreign,',')
            for word in c['words']:p(word,True)
            for title,texts in [(c['resp_head'],c['resp']),(c['prac_head'],c['prac']),('Standards / conclusion',c['standards']+[c['concl']]),(c['restr_head'],[c['restr']])]:
                p(title,True)
                for text in texts:p(text)
                if title==c['prac_head']:
                    for label,text in c['procedures']:p(label+' '+text)
                    p(c['relied'])
            signer();p(c['enclosure'])
        else:
            annexure,title=CAPTIONS[name];p(annexure,True);p(title,True,True)
            rows=rows_for(case,c,name);table=doc.add_table(rows=1,cols=5);table.style='Table Grid';table.alignment=WD_TABLE_ALIGNMENT.CENTER;table.autofit=False
            widths=[usable*.05,usable*.39,usable*.27,usable*.15,usable*.14]
            for cell,title,width in zip(table.rows[0].cells,['#','Details','Ownership','Amount (INR)',foreign_caption(case)],widths):cell.width=Mm(width);rich(cell.paragraphs[0],title,True)
            header=OxmlElement('w:tblHeader');header.set(qn('w:val'),'true');table.rows[0]._tr.get_or_add_trPr().append(header)
            for serial,lines,owner,relation,identity,amount,foreign in rows:
                cells=table.add_row().cells
                for cell,width in zip(cells,widths):cell.width=Mm(width)
                cells[0].text=serial
                for i,(text,bold) in enumerate(lines):rich(cells[1].paragraphs[0] if i==0 else cells[1].add_paragraph(),text,bold)
                cells[2].text=owner.title+' '+owner.name;rich(cells[2].add_paragraph(),'('+relation+')',True)
                if identity:cells[2].add_paragraph(identity)
                cells[3].text=engine.fmt_acct(amount);cells[4].text='-' if foreign is None else format(foreign,',')
            cells=table.add_row().cells;cells[1].text='Total annual income' if name=='annual income' else 'Total';cells[3].text=engine.fmt_acct(sum(r[5] for r in rows));cells[4].text='-' if not rows or rows[0][6] is None else format(sum(r[6] for r in rows),',')
            if name=='annual income':p('Annual income is separate and is not included in asset / net asset totals.')
            signer()
    meta=case.report.get('rate_meta') or {}
    if meta:p('Exchange rate: '+quote_caption(case.report))
    doc.save(path)

def export_pdf(case,c,path):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,LongTable,TableStyle,Image,KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    layout=layout_from(case.report,case.settings);m=layout['margins_mm'];width,height=layout['width_mm']*mm,layout['height_mm']*mm;usable=width-(m['left']+m['right'])*mm
    styles=getSampleStyleSheet();normal=ParagraphStyle('ReportBody',parent=styles['Normal'],fontName='Helvetica',fontSize=10,leading=13,spaceAfter=7);small=ParagraphStyle('ReportCell',parent=normal,fontSize=9,leading=12,spaceAfter=3);heading=ParagraphStyle('ReportHeading',parent=normal,fontSize=15,leading=19,alignment=1,spaceAfter=14)
    def para(text,bold=False,style=None):
        markup=''.join(('<b>'+escape(part)+'</b>') if bold or emph else escape(part) for part,emph in engine.segments(str(text)))
        return Paragraph(markup.replace('\n','<br/>'),style or normal)
    def fitted(data,maxw,maxh):
        from PIL import Image as PILImage
        raw=PILImage.open(io.BytesIO(data));w,h=fit_dimensions(data,maxw,maxh);return Image(io.BytesIO(data),width=w,height=h,hAlign='LEFT')
    letterpad=effective_letterpad(case.settings)
    def onpage(canvas,doc):
        if letterpad.get('include_first_page',True) or doc.page>1:
            background=get_bytes(letterpad,'background')
            if background:
                image=fitted(background,width,height);image.drawOn(canvas,(width-image.drawWidth)/2,(height-image.drawHeight)/2)
            else:
                for position in ('header','footer'):
                    data=get_bytes(letterpad,position)
                    if data:
                        image=fitted(data,usable,25*mm if position=='header' else 18*mm)
                        y=height-4*mm-image.drawHeight if position=='header' else 4*mm
                        image.drawOn(canvas,m['left']*mm,y)
        if not get_bytes(letterpad,'header') and (case.settings.get('letterhead_first_page',True) or doc.page>1):
            canvas.setFont('Helvetica-Bold',10);canvas.drawString(m['left']*mm,height-9*mm,case.settings.get('firm_name',''))
        canvas.setFont('Helvetica',8);canvas.drawRightString(width-m['right']*mm,8*mm,'Page '+str(doc.page))
    story=[]
    def signer():
        block=[para('For '+case.settings.get('firm_name',''),True)]
        data=image_bytes(case.settings)
        if data:block.append(fitted(data,50*mm,20*mm))
        for key,prefix in [('partner',''),('designation',''),('frn','FRN: '),('mno','Membership No. ')]:
            if case.settings.get(key):block.append(para(prefix+case.settings[key],key=='partner'))
        block.extend([para('UDIN: '+case.report.get('udin',''),True),para('Place: '+case.settings.get('place','')+' | Date: '+case.report.get('cert_date',''))]);story.append(Spacer(1,10));story.append(KeepTogether(block))
    sections=[s for s in layout['sections'] if s not in ('annual income','liabilities') or (s=='annual income' and bool(c['annual_income'])) or (s=='liabilities' and any(i['kind']=='liability' for i in case.items))]
    for index,name in enumerate(sections):
        if index:story.append(PageBreak())
        if name=='intro':
            story.append(para('NET ASSET REPORT',True,heading))
            person=case.applicants[0]
            details=[['Sr.No.','Particulars','Details'],['1','Name of Applicant',(person.title+' '+person.name).strip()],['2','Address of Applicant',person.fields.get('address','')],['3','Passport Number of Applicant',person.fields.get('passport_number','')],['4','Purpose for which Report is made',case.report.get('purpose','')],['5','Name of Country',case.report.get('country','')],['6','1 '+str(case.report.get('currency','').split(' - ')[1] if ' - ' in str(case.report.get('currency','')) else 'Foreign currency')+' (in INR)',case.report.get('rate','')]]
            table=LongTable([[para(str(x),True,small) for x in row] for row in details],colWidths=[usable*.10,usable*.36,usable*.54],repeatRows=1);table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EDE8DE')),('ALIGN',(0,0),(0,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story.append(table)
        elif name=='certificate':
            story.append(para('NET ASSET REPORT',True,heading));story.extend(para(t) for t in c['intro'][1:])
            data=[[para(t,True,small) for t in ['S.No.','Particulars','Annexure','NAV in INR','Value in foreign currency']]]
            rows=summary_rows(case,c)+income_summary(case,c)
            for n,(label,amount,foreign) in enumerate(rows,1): data.append([para(str(n),False,small),para(label,False,small),para('A' if n==1 else 'B' if n==2 else 'D',False,small),para(engine.fmt_acct(amount),False,small),para('-' if foreign is None else format(foreign,','),False,small)])
            data.append(['',para('Total',True,small),'',para(engine.fmt_acct(sum(x[1] for x in rows)),True,small),''])
            table=LongTable(data,colWidths=[usable*.08,usable*.36,usable*.12,usable*.22,usable*.22],repeatRows=1);table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EDE8DE')),('VALIGN',(0,0),(-1,-1),'TOP')]));story.append(table);story.append(Spacer(1,10));story.extend(para(t,True) for t in c['words']);story.extend(para('All annexures attached with this certificate form part of this certificate.'),para('The statement has been prepared from the documents and information supplied for review.'))
            story.append(PageBreak())
            for title,texts in [(c['resp_head'],c['resp']),(c['prac_head'],c['prac']),('Standards / conclusion',c['standards']+[c['concl']]),(c['restr_head'],[c['restr']])]:
                story.append(para(title,True));story.extend(para(t) for t in texts)
                if title==c['prac_head']:
                    story.extend(para(label+' '+text) for label,text in c['procedures']);story.append(para(c['relied']))
            signer();story.append(para(c['enclosure']))
        else:
            annexure,title=CAPTIONS[name];story.extend([para(annexure,True),para(title,True,heading)])
            rows=rows_for(case,c,name);data=[[para(t,True,small) for t in ['#','Details','Ownership','Amount (INR)',foreign_caption(case)]]]
            for serial,lines,owner,relation,identity,amount,foreign in rows:
                details=[para(t,b,small) for t,b in lines];ownership=[para(owner.title+' '+owner.name,False,small),para('('+relation+')',True,small)]
                if identity:ownership.append(para(identity,False,small))
                data.append([para(serial,False,small),details,ownership,para(engine.fmt_acct(amount),False,small),para('-' if foreign is None else format(foreign,','),False,small)])
            data.append(['',para('Total annual income' if name=='annual income' else 'Total',True,small),'',para(engine.fmt_acct(sum(r[5] for r in rows)),True,small),para('-' if not rows or rows[0][6] is None else format(sum(r[6] for r in rows),','),True,small)])
            table=LongTable(data,colWidths=[usable*x for x in (.05,.39,.27,.15,.14)],repeatRows=1,splitByRow=1);table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.grey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EDE8DE')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4)]));story.append(table)
            if name=='annual income':story.append(para('Annual income is separate and is not included in asset / net asset totals.'))
    meta=case.report.get('rate_meta') or {}
    if meta:story.append(para('Exchange rate: '+quote_caption(case.report)))
    if not story:raise ValueError('No selected section contains report data.')
    SimpleDocTemplate(str(path),pagesize=(width,height),leftMargin=m['left']*mm,rightMargin=m['right']*mm,topMargin=m['top']*mm,bottomMargin=m['bottom']*mm).build(story,onFirstPage=onpage,onLaterPages=onpage)
