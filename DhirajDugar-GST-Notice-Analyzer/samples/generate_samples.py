"""Optional sample regeneration: pip install reportlab==4.2.5 first.
ReportLab is not required to run the app; the PDFs are already included.
"""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
ROOT = Path(__file__).resolve().parent
NOTICES = [
 ('01_ASMT10_Scrutiny', 'GST ASMT-10', [
  'Taxpayer name: Demo Aravalli Components Private Limited',
  'GSTIN: 24DEMOX0000X1Z0',
  'Notice reference: DEMO/ASMT10/2026/001',
  'Issue date: 05-11-2026',
  'Tax period: April 2023 to March 2024 (FY 2023-24)',
  'Reply due date: 25-11-2026',
  'Total proposed tax: INR 2,16,000 (allegation only; subject to reconciliation)',
 ], [
  ('1. Input tax credit discrepancy',
   'ITC mismatch between GSTR-2B and GSTR-3B is noticed.\nThe credit claimed in GSTR-3B is INR 14,40,000 against INR 12,96,000 reflected in GSTR-2B. The alleged difference is INR 1,44,000. Provide invoice-wise reconciliation including amendments, reversals and timing differences. This is an allegation for explanation, not a final determination.'),
  ('2. Output liability discrepancy',
   'GSTR-1 vs GSTR-3B liability difference is INR 72,000.\nOutput tax declared in GSTR-1 is INR 18,00,000 against INR 17,28,000 discharged in GSTR-3B. Furnish a period-wise bridge and details of any subsequent reporting or payment.'),
  ('Response instructions',
   'This fictional scrutiny notice refers to section 61 and rule 99. Furnish an explanation with supporting documents in ASMT-11. The sample reply date is explicitly stated above for demonstration only. In a live case, verify the date of service, portal record and extension, if any.'),
 ], [
  ['Item', 'Statement amount (INR)', 'Return amount (INR)', 'Difference (INR)'],
  ['Input credit', '12,96,000', '14,40,000', '1,44,000'],
  ['Output tax', '18,00,000', '17,28,000', '72,000'],
 ]),
 ('02_DRC01_ShowCause', 'GST DRC-01', [
  'Taxpayer name: Demo Sabarmati Services LLP',
  'GSTIN: 24DEMOY0000Y1Z0',
  'Notice reference: DEMO/DRC01/2026/002',
  'Issue date: 06-11-2026',
  'Tax period: April 2024 to March 2025 (FY 2024-25)',
  'Reply due date: 26-11-2026',
  'Total proposed tax: INR 1,26,000 (allegation only)',
 ], [
  ('Nature of document',
   'This is a fictional summary of a show-cause notice under section 74A read with rule 142. For a live DRC-01, obtain the full SCN and relied-upon documents. The following illustrative grounds are supplied only to make this training sample self-contained.'),
  ('1. Reverse charge on professional services',
   'RCM short-payment of INR 54,000 is alleged.\nLegal service expenses of INR 3,00,000 are stated in the expense ledger. The department alleges reverse charge tax on a notified category of services has not been paid. Verify the supplier, recipient, exemption conditions, notification and payment records before taking a position.'),
  ('2. Alleged ineligible credit',
   'Blocked ITC under section 17(5) of INR 72,000 is alleged.\nCredit on a passenger motor vehicle is questioned. Confirm seating capacity, nature of use and statutory exceptions. No conclusion is drawn in this sample about eligibility or utilisation.'),
  ('Response instructions',
   'A response to the SCN is to be reviewed for filing in DRC-06 under rule 142(4). Proposed interest and penalty, if any, require a separate verified computation; they are not quantified in this sample.'),
 ], [
  ['Allegation', 'Tax base (INR)', 'Alleged tax (INR)'],
  ['RCM on legal services', '3,00,000', '54,000'],
  ['Blocked vehicle credit', 'Not reproduced', '72,000'],
 ]),
 ('03_DRC01A_PreNotice', 'GST DRC-01A', [
  'Taxpayer name: Demo Narmada Trading Company',
  'GSTIN: 24DEMOZ0000Z1Z0',
  'Notice reference: DEMO/DRC01A/2026/003',
  'Issue date: 07-11-2026',
  'Tax period: April 2023 to March 2024 (FY 2023-24)',
  'Reply due date: 24-11-2026',
  'Total proposed tax: INR 36,000 (excluding unquantified fee/interest)',
 ], [
  ('Nature of document',
   'Fictional Part A pre-notice intimation under rule 142(1A), referring to section 73. This is not a final demand order. Submissions against the proposed liability may be made in Part B under rule 142(2A).'),
  ('1. Recipient-side liability',
   'Reverse charge short-payment of INR 36,000 is alleged.\nThe intimation identifies legal-service invoices on which recipient-side GST is said to be unpaid. Verify transaction coverage, notified exemptions and any amounts already discharged.'),
  ('2. Filing delay',
   'Late filing of GSTR-3B is noticed for three months.\nThe returns for July, August and September 2023 were allegedly filed after their applicable due dates. The department proposes late fee, subject to verification of extensions, caps, waivers and prior payments. No fee amount is supplied in this sample.'),
  ('Response instructions',
   'Provide the relevant filing acknowledgements, due-date notification references and payment records. The app must not invent a fee computation or treat an intimation as an adjudication order.'),
 ], [
  ['Period', 'Illustrative filing date', 'Review needed'],
  ['July 2023', '25-09-2023', 'Check actual applicable due date'],
  ['August 2023', '25-10-2023', 'Check actual applicable due date'],
  ['September 2023', '25-11-2023', 'Check actual applicable due date'],
 ]),
]

def build():
 styles = getSampleStyleSheet()
 styles.add(ParagraphStyle(name='Title2', fontName='Helvetica-Bold', fontSize=24, leading=29, textColor=colors.HexColor('#251f21'), spaceAfter=14))
 styles.add(ParagraphStyle(name='Body2', fontName='Helvetica', fontSize=9.5, leading=13.5, spaceAfter=7))
 styles.add(ParagraphStyle(name='Note2', fontName='Helvetica-Bold', fontSize=9, leading=13, textColor=colors.HexColor('#a03030'), spaceAfter=12))
 for stem, form, fields, sections, rows in NOTICES:
  elements = [Paragraph('FICTIONAL TRAINING DOCUMENT - NOT ISSUED BY ANY AUTHORITY', styles['Note2']),
              Paragraph(form, styles['Title2']),
              Paragraph('GST Notice Analyzer / AICA Level-2 demonstration', styles['Body2'])]
  for line in fields: elements.append(Paragraph(line, styles['Body2']))
  elements.append(Paragraph('All entities, identifiers, amounts and events are fabricated. GSTIN strings are intentionally invalid demo identifiers and must never be used for a return, registration or portal search.', styles['Note2']))
  for heading, body in sections:
   elements.append(Paragraph(heading, styles['Heading2']))
   for line in body.split('\n'): elements.append(Paragraph(line, styles['Body2']))
  elements.append(Paragraph('Illustrative supporting schedule', styles['Heading2']))
  widths = [150, 115, 115, 100] if len(rows[0])==4 else [160, 155, 165]
  table = Table([[Paragraph(c, styles['Body2']) for c in row] for row in rows], colWidths=widths, repeatRows=1)
  table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4eee9')),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#d4d4d4')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),8)]))
  elements.append(table)
  def footer(canvas, doc):
   canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#585254'))
   canvas.drawString(56,32,'Fictional educational example | No official seal or signature | Professional review required')
   canvas.drawRightString(540,32,str(doc.page))
  SimpleDocTemplate(str(ROOT/(stem+'.pdf')), pagesize=(595,842), leftMargin=56, rightMargin=56, topMargin=42, bottomMargin=44).build(elements,onFirstPage=footer,onLaterPages=footer)
  text = form+'\n'+'\n'.join(fields)+'\n\n'+'\n\n'.join(h+'\n'+b for h,b in sections)+'\n\nFICTIONAL TRAINING DOCUMENT. All details fabricated; identifiers intentionally invalid.'
  (ROOT/(stem+'.txt')).write_text(text,encoding='utf-8')

if __name__ == '__main__': build()
