import json,html
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
content=json.loads(Path('docs/manual-content.json').read_text(encoding='utf-8'));version=content['version'];out=Path('output/guides');out.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Guide',r'C:\Windows\Fonts\arial.ttf'));pdfmetrics.registerFont(TTFont('GuideBold',r'C:\Windows\Fonts\arialbd.ttf'))
body=ParagraphStyle('Body',fontName='Guide',fontSize=9.3,leading=13.4,textColor=HexColor('#34525b'),spaceAfter=8)
heading=ParagraphStyle('Heading',fontName='GuideBold',fontSize=12,leading=16,textColor=HexColor('#137f70'),spaceBefore=11,spaceAfter=5)
title=ParagraphStyle('Title',fontName='GuideBold',fontSize=23,leading=28,textColor=HexColor('#163744'),spaceAfter=12)
intro=ParagraphStyle('Intro',parent=body,fontSize=10.5,leading=15,textColor=HexColor('#6b858d'),spaceAfter=14)
story=[]
for index,page in enumerate(content['pages']):
    if index:story.append(PageBreak())
    story.append(Paragraph(html.escape(page['title']),title));story.append(Paragraph(html.escape(page['intro']),intro))
    for section in page['sections']:story.extend([Paragraph(html.escape(section['heading']),heading),Paragraph(html.escape(section['text']),body)])
def decorate(canvas,doc):
    w,h=A4;canvas.drawImage('assets/brand/sales360.png',45,h-49,25,25,mask='auto');canvas.setFont('GuideBold',9);canvas.setFillColor(HexColor('#163744'));canvas.drawString(80,h-38,'SALES360  |  OFFLINE WORKSPACE');canvas.setFont('Guide',8);canvas.setFillColor(HexColor('#6b858d'));canvas.drawRightString(w-45,h-38,'Installation & usage · '+version);canvas.setStrokeColor(HexColor('#dbe6e3'));canvas.line(45,45,w-45,45);canvas.drawString(45,30,'29 October 2026  |  Asia/Dubai  |  See release acceptance boundary');canvas.drawRightString(w-45,30,f'Page {doc.page}')
SimpleDocTemplate(str(out/'INSTALLATION-AND-USAGE.pdf'),pagesize=A4,rightMargin=45,leftMargin=45,topMargin=72,bottomMargin=60,title='SALES360 Installation and Usage '+version).build(story,onFirstPage=decorate,onLaterPages=decorate)
sections=''.join('<section id="page'+str(i+1)+'"><h2>'+html.escape(page['title'])+'</h2><p class="intro">'+html.escape(page['intro'])+'</p>'+''.join('<h3>'+html.escape(s['heading'])+'</h3><p>'+html.escape(s['text'])+'</p>' for s in page['sections'])+'</section>' for i,page in enumerate(content['pages']))
nav=''.join('<a href="#page'+str(i+1)+'">'+html.escape(p['title'])+'</a>' for i,p in enumerate(content['pages']))
document='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SALES360 Installation and Usage</title><style>body{margin:0;font:15px/1.75 Segoe UI,Arial,sans-serif;background:#f0f5f3;color:#29454e}header{background:#13343e;color:#fff;padding:44px max(25px,calc((100vw - 960px)/2))}h1{font-size:36px;margin:0}header p{color:#a6d9ca;margin:8px 0}main{max-width:960px;margin:25px auto;padding:0 20px}nav{display:flex;gap:12px;flex-wrap:wrap;background:white;padding:22px;border-radius:12px}nav a{color:#137f70;text-decoration:none;font-weight:600;font-size:13px}section{background:white;border:1px solid #dde8e2;border-radius:12px;padding:32px 38px;margin:24px 0}h2{font-size:25px;color:#143945;margin:0 0 10px}h3{color:#148271;margin-bottom:6px}.intro{color:#78928c}p{margin-top:0}footer{text-align:center;color:#769087;font-size:12px;padding:20px}@media print{nav{display:none}section{page-break-before:always;border:0}header{color:#13343e;background:white}body{background:white}}@media(max-width:650px){section{padding:24px}h1{font-size:30px}}</style><header><h1>SALES360 Offline</h1><p>Installation & everyday use · Version VERSION</p><p>No runtime internet or API keys required. Review the release acceptance boundary before live-company use.</p></header><main><nav>NAV</nav>SECTIONS</main><footer>29 October 2026 · Asia/Dubai · Windows x64</footer></html>'''.replace('VERSION',version).replace('NAV',nav).replace('SECTIONS',sections)
Path('docs/INSTALLATION-AND-USAGE.html').write_text(document,encoding='utf-8');print('Generated HTML and PDF user guides.')
