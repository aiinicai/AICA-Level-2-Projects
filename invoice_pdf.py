"""One ReportLab document used by export, preview, and printing."""
from html import escape
from pathlib import Path
from io import BytesIO
import base64
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.pagesizes import A4

def generate(invoice, filename):
    styles = getSampleStyleSheet()
    styles['Heading3'].fontSize=10
    styles['Heading3'].leading=12
    styles['Heading3'].spaceBefore=6
    styles['Heading3'].spaceAfter=4
    styles.add(ParagraphStyle(name='SmallText', fontSize=9, leading=13, wordWrap='CJK'))
    styles.add(ParagraphStyle(name='RightText', parent=styles['SmallText'], alignment=TA_RIGHT))
    def p(text, style='SmallText'):
        return Paragraph(escape(str(text or '')).replace('\n','<br/>'), styles[style])
    seller, customer = invoice['seller'], invoice['customer']
    story = []
    title = [p(seller.get('trade_name',''), 'Title'), p(seller.get('address','')),
             p(' | '.join(x for x in [seller.get('mobile',''), seller.get('email','')] if x)),
             p('GSTIN: '+seller['gst']) if seller.get('gst') else Spacer(1,1)]
    logo = seller.get('logo','')
    if seller.get('logo_data') or (logo and Path(logo).is_file()):
        source = BytesIO(base64.b64decode(seller['logo_data'])) if seller.get('logo_data') else logo
        image = Image(source, width=70, height=55, kind='proportional')
        story.append(Table([[image,title]], colWidths=[90,425]))
    else:
        story.extend(title)
    story += [Spacer(1,18), p('INVOICE', 'Heading1'),
              p(f"{invoice.get('number') or 'DRAFT'}  |  Date: {invoice['date']}"), Spacer(1,14),
              p('BILL TO','Heading3'), p(customer['name']), p(customer['address']),
              p('Mobile: '+customer.get('mobile',''))]
    if customer.get('gst'): story.append(p('GSTIN: '+customer['gst']))
    story.append(Spacer(1,16))
    rows = [['#','Item / Description','Qty','Rate','GST %','Amount','GST','Total']]
    for i,item in enumerate(invoice['items'],1):
        rows.append([str(i),p(item['name']),p(item['quantity'],'RightText'),p(item['rate'],'RightText'),p(item['gst'],'RightText'),p(item['amount'],'RightText'),p(item['tax'],'RightText'),p(item['total'],'RightText')])
    table = Table(rows,colWidths=[23,155,40,60,40,65,60,72],repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1557a5')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTSIZE',(0,0),(-1,0),9),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f0f5fc')]),('BOTTOMPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,0),1,colors.HexColor('#1557a5'))]))
    story.extend([table,Spacer(1,16)])
    totals = Table([[label,p(invoice[key],'RightText')] for label,key in [('Subtotal (INR)','subtotal'),('Total GST','total_gst'),('Round off','round_off'),('GRAND TOTAL (INR)','grand_total')]],colWidths=[375,120])
    totals.setStyle(TableStyle([('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#e5eefb')),('FONTNAME',(0,-1),(-1,-1),'Helvetica-Bold'),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
    story.append(KeepTogether([totals,Spacer(1,16)]))
    taxrows = [['GST rate','Taxable value (INR)','GST (INR)']]+[[k+'%',v['taxable'],v['tax']] for k,v in invoice['tax_summary'].items()]
    summary=Table(taxrows,colWidths=[100,200,195],hAlign='LEFT')
    summary.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5eefb')),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.extend([p('TAX SUMMARY','Heading3'),summary,Spacer(1,12),p('BANK DETAILS','Heading3'),p(seller.get('bank','')),Spacer(1,6),p('DECLARATION','Heading3'),p(seller.get('declaration','')),Spacer(1,12),KeepTogether([p('For '+seller['trade_name'],'RightText'),Spacer(1,16),p('Authorised Signatory','RightText')])])
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#1557a5'))
        canvas.line(40,38,555,38)
        canvas.setFont('Helvetica',8)
        canvas.drawString(40,25,'Smart Billing Manager | '+(invoice.get('number') or 'DRAFT'))
        canvas.drawRightString(555,25,f'Page {doc.page}')
    SimpleDocTemplate(str(filename),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=35,bottomMargin=55,title='Invoice '+str(invoice.get('number') or 'DRAFT')).build(story,onFirstPage=footer,onLaterPages=footer)
    return Path(filename)
