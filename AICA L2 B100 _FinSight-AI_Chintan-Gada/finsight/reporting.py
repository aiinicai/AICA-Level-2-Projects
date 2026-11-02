from io import BytesIO
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER

def excel_report(metrics,flags,issues,anomalies):
    out=BytesIO()
    with pd.ExcelWriter(out,engine='openpyxl') as writer:
        metrics.to_excel(writer,sheet_name='KPIs')
        pd.DataFrame(flags).to_excel(writer,sheet_name='Risk Flags',index=False)
        pd.DataFrame({'Validation Messages':issues or ['All configured checks passed']}).to_excel(writer,sheet_name='Validation',index=False)
        anomalies.to_excel(writer,sheet_name='Anomalies',index=False)
        for sheet in writer.book:
            sheet.freeze_panes='B2'
            for cell in sheet[1]:
                cell.font=__import__('openpyxl').styles.Font(bold=True,color='FFFFFF')
                cell.fill=__import__('openpyxl').styles.PatternFill('solid',fgColor='17365D')
            for col in sheet.columns:
                letter=col[0].column_letter
                sheet.column_dimensions[letter].width=min(65,max(14,max(len(str(c.value or '')) for c in col)+2))
    return out.getvalue()

def pdf_report(company,unit,metrics,flags,issues,advisory,status):
    out=BytesIO(); doc=SimpleDocTemplate(out,pagesize=(595,842),leftMargin=38,rightMargin=38,topMargin=40,bottomMargin=40)
    styles=getSampleStyleSheet(); story=[]
    def para(t,style='Normal'): return Paragraph(escape(str(t)).replace('\n','<br/>'),styles[style])
    story += [para('FinSight AI — CFO Financial Review','Title'),Spacer(1,8),para(f'Company: {company} | Unit: {unit} | Status: {status}'),Spacer(1,15),para('Financial indicators','Heading2')]
    years=list(metrics.columns); table=[['Indicator']+years]
    for key in ['Revenue','EBITDA','PAT','EBITDA margin %','Current ratio','Debt / Equity','Interest coverage','Operating cash flow','Free cash flow']:
        table.append([key]+[('N/A' if pd.isna(metrics.loc[key,y]) else f'{metrics.loc[key,y]:,.2f}') for y in years])
    t=Table(table,repeatRows=1,colWidths=[190]+[min(100,325/len(years))]*len(years),hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17365D')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.whitesmoke,colors.white]),('GRID',(0,0),(-1,-1),0.3,colors.lightgrey),('FONTSIZE',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story += [t,Spacer(1,15),para('Risk observations','Heading2')]
    for f in flags: story += [para(f'{f["severity"]}: {f["code"]} — {f["evidence"]}. {f["recommendation"]}'),Spacer(1,6)]
    if not flags: story.append(para('No configured risk flags.'))
    story += [Spacer(1,10),para('Validation','Heading2')]
    for s in issues or ['All configured checks passed']: story += [para(s),Spacer(1,5)]
    story += [Spacer(1,10),para('CFO advisory commentary','Heading2')]
    for line in advisory.splitlines():
        if line.strip(): story += [para(line),Spacer(1,6)]
    story += [Spacer(1,18),para('Educational capstone. Not an audit opinion, investment recommendation or assurance engagement. Review and verify all outputs before reliance.')]
    doc.build(story)
    return out.getvalue()
