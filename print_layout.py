"""Validated shared physical-page settings. Excel ranges are not PDF page ranges."""
import copy,re
PAPERS={'A4':(210.0,297.0),'Legal':(215.9,355.6),'Letter':(215.9,279.4)}
SECTIONS=('intro','certificate','immovable','movable','annual income','liabilities')

def layout_from(report,settings=None):
    raw=copy.deepcopy(report.get('print_layout') or {});paper=raw.get('paper','A4');orientation=raw.get('orientation','Portrait')
    if paper not in PAPERS:raise ValueError('Choose A4, Legal or Letter paper.')
    if orientation not in ('Portrait','Landscape'):raise ValueError('Choose Portrait or Landscape.')
    margins={}
    for side in ('top','bottom','left','right'):
        try:v=float(raw.get('margins_mm',{}).get(side,15))
        except Exception as exc:raise ValueError('Margins must be numeric millimetres.') from exc
        if not 5<=v<=50:raise ValueError('Each margin must be between 5 and 50 mm.')
        margins[side]=v
    width,height=PAPERS[paper]
    if orientation=='Landscape':width,height=height,width
    sections=raw.get('sections',list(SECTIONS))
    if not isinstance(sections,list) or not sections or any(s not in SECTIONS for s in sections):raise ValueError('Choose at least one valid printed report section.')
    scale=raw.get('excel_scale','Fit width')
    if scale not in ('Fit width','Actual size'):raise ValueError('Choose Fit width or Actual size for Excel scaling.')
    areas=raw.get('excel_print_areas',{})
    if not isinstance(areas,dict):raise ValueError('Excel print areas must be a worksheet-to-range mapping.')
    from letterpad_asset import effective_letterpad
    letterpad=effective_letterpad(settings or {})
    if letterpad.get('enabled'):
        if letterpad.get('background'):
            from letterpad_asset import get_bytes
            from signature_asset import fit_dimensions
            _,h=fit_dimensions(get_bytes(letterpad,'background'),width,height);inset=(height-h)/2
            margins['top']=max(margins['top'],34,inset+h*.118+4)
            margins['bottom']=max(margins['bottom'],25,inset+h*.067+4)
        else:
            if letterpad.get('header'):margins['top']=max(margins['top'],34)
            if letterpad.get('footer'):margins['bottom']=max(margins['bottom'],25)
    return dict(paper=paper,orientation=orientation,width_mm=width,height_mm=height,margins_mm=margins,sections=sections,excel_scale=scale,excel_print_areas=areas)

def validate_print_area(area,ws):
    from openpyxl.utils.cell import range_boundaries
    if not re.fullmatch(r'\$?[A-Z]{1,3}\$?\d+:\$?[A-Z]{1,3}\$?\d+',str(area).strip()):raise ValueError('Use a single Excel A1 range, for example A1:F40.')
    left,top,right,bottom=range_boundaries(area)
    if min(left,top)<1 or right<left or bottom<top or right>ws.max_column or bottom>ws.max_row:raise ValueError('Print area must stay within '+ws.title+' used range A1:'+__import__('openpyxl').utils.get_column_letter(ws.max_column)+str(ws.max_row))
    if not any(ws.cell(r,c).value is not None for r in range(top,bottom+1) for c in range(left,right+1)):raise ValueError('This print area contains no report content.')
    return area

def apply_workbook_layout(wb,case):
    from openpyxl.worksheet.page import PageMargins
    from openpyxl.worksheet.properties import PageSetupProperties
    layout=layout_from(case.report,case.settings);m=layout['margins_mm']
    for sh in wb:
        sh.page_setup.paperSize={'A4':sh.PAPERSIZE_A4,'Legal':sh.PAPERSIZE_LEGAL,'Letter':sh.PAPERSIZE_LETTER}[layout['paper']]
        sh.page_setup.orientation=layout['orientation'].lower();sh.page_margins=PageMargins(left=m['left']/25.4,right=m['right']/25.4,top=m['top']/25.4,bottom=m['bottom']/25.4,header=.15,footer=.15)
        sh.sheet_properties.pageSetUpPr=PageSetupProperties(fitToPage=layout['excel_scale']=='Fit width')
        sh.page_setup.fitToWidth=1 if layout['excel_scale']=='Fit width' else None;sh.page_setup.fitToHeight=0 if layout['excel_scale']=='Fit width' else None;sh.page_setup.scale=None if layout['excel_scale']=='Fit width' else 100
        if sh.title in layout['excel_print_areas']:sh.print_area=validate_print_area(layout['excel_print_areas'][sh.title],sh)
        sh.sheet_state='hidden' if sh.title in ('SUMMARY','Sheet1') or sh.title not in layout['sections'] else 'visible'
    if not any(sh.sheet_state=='visible' for sh in wb):raise ValueError('No selected report section contains report data.')
    wb.active=next(i for i,s in enumerate(wb) if s.sheet_state=='visible')
    return layout
