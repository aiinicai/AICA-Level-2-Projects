"""No GUI launch: response to actual Linux narrow-window acceptance failures."""
from pathlib import Path
from types import SimpleNamespace
import copy,datetime,io,json,zipfile
import pytest
from PIL import Image,ImageDraw
import openpyxl,pymupdf
from asset_model import Case
import net_asset_report as ui
from ui_design import wheel_units

class Var:
    def __init__(self,value=''):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value

@pytest.mark.parametrize('button,delta,expected',[(4,0,-3),(5,0,3),(None,120,-3),(None,-120,3),('??',240,-6),('??',1,-3),('??',-1,3)])
def test_wheel_routes_children_to_whole_form_without_focus(button,delta,expected):
    events=[];canvas=SimpleNamespace(yview_scroll=lambda n,mode:events.append((n,mode)))
    body=SimpleNamespace(master=None,_scroll_canvas=canvas);entry=SimpleNamespace(master=body)
    assert wheel_units(button,delta)==expected
    assert ui.App._on_mousewheel(None,SimpleNamespace(widget=entry,num=button,delta=delta))=='break'
    assert events==[(expected,'units')]

@pytest.mark.parametrize('geometry',['1024 x 578','1280 x 800'])
def test_window_size_control_unmaximizes_deterministically(geometry):
    calls=[];fake=SimpleNamespace(window_size=Var(geometry),state=lambda s:calls.append(('state',s)),attributes=lambda *s:calls.append(s),geometry=lambda s:calls.append(('geometry',s)))
    ui.App.set_window_size(fake)
    assert ('state','normal') in calls and ('-zoomed',False) in calls
    assert ('geometry',geometry.replace(' ','')+'+0+0') in calls

def test_pinned_root_and_single_asset_form_no_focus_steal():
    source=Path(ui.__file__).read_text()
    assert "footer.grid(row=3,column=0,sticky='ew')" in source
    assert "self.notebook.grid(row=2,column=0,sticky='nsew'" in source
    assert 'canvas.focus_set()' not in source
    asset=source.split('    def _assets_tab(self):',1)[1].split('    def _asset_fields(self):',1)[0]
    assert 'Panedwindow' not in asset and 'editor_body=self.scroll_frame(self.tab_items)' in asset
    assert "ttk.Button(bar,text='Add item'" in asset
    assert "text='View list'" in asset and 'self.scroll_to' in asset

def test_multiple_ca_deletions_persist_without_changing_current_identity(tmp_path,monkeypatch):
    target=tmp_path/'test_profiles.json';shared=tmp_path/'image.png';shared.write_bytes(b'SYNTHETIC')
    original={'TEST ONE':{'firm_name':'TEST ONE','logo_path':str(shared)},'TEST TWO':{'firm_name':'TEST TWO'},'TEST THREE':{'firm_name':'TEST THREE'}}
    monkeypatch.setattr(ui.engine,'PROFILES_FILE',str(target));monkeypatch.setattr(ui.messagebox,'askyesno',lambda *a,**k:True)
    case=Case();case.settings={'firm_name':'CURRENT SNAPSHOT','partner':'CURRENT SIGNER'};snapshot=copy.deepcopy(case.settings)
    fake=SimpleNamespace(ca_profiles=original,profile_cb=Var(),status=Var(),update_profile_dropdown=lambda:None,case=case)
    for index,name in enumerate(('TEST TWO','TEST ONE','TEST THREE')):
        fake.profile_cb.set(name);ui.App.remove_ca_profile(fake)
        restored=SimpleNamespace(ca_profiles={});ui.engine.App.load_profiles(restored)
        assert restored.ca_profiles==fake.ca_profiles and len(restored.ca_profiles)==2-index
        assert shared.exists() and case.settings==snapshot and fake.profile_cb.get()==''
    assert json.loads(target.read_text())=={}

def test_report_date_warnings_and_historical_rate_approval_are_explicit():
    from currency_rates import IST,validate_rate_for_report,parse_historical_quote
    today=datetime.datetime.now(IST).date();case=Case()
    case.report={'statement_date':(today+datetime.timedelta(days=1)).strftime('%d-%m-%Y')}
    assert any('Future' in text for text in case.formula_warnings())
    case.report['statement_date']=(today-datetime.timedelta(days=30)).strftime('%d-%m-%Y')
    assert any('Past' in text for text in case.formula_warnings())
    quote=parse_historical_quote({'base':'CAD','quote':'INR','date':'2020-01-03','rate':'55'},'CAD',datetime.date(2020,1,4),'SYNTHETIC')
    report={'currency':'CAD - Canadian Dollars','rate':'55','statement_date':'04-01-2020','rate_meta':quote}
    with pytest.raises(ValueError,match='Explicitly review'):validate_rate_for_report(report)
    quote['date_reviewed']=True;validate_rate_for_report(report)

def test_complete_whole_page_background_actual_three_formats(tmp_path):
    from letterpad_asset import load_letterpad,get_bytes
    from report_export import export
    from print_layout import layout_from
    p=tmp_path/'FULL_PAGE_TEST.png';image=Image.new('RGB',(850,1200),'white');draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,849,125),fill='navy');draw.rectangle((200,500,650,650),fill='#DCE2E8');draw.rectangle((0,1120,849,1199),fill='gold');image.save(p)
    case=Case();case.people[0].name='SYNTHETIC';case.report={'statement_date':'07-11-2026','currency':'None','print_layout':{'sections':['movable']}};case.settings={'letterpad':load_letterpad(p,'Whole-page letterpad')};case.add_asset('Cash in Hand',100,case.people[0].id,'Cash')
    p.unlink();assert Image.open(io.BytesIO(get_bytes(case.settings['letterpad'],'background'))).size==(850,1200)
    out=tmp_path/'full.pdf';export(case,out,'pdf')
    with pymupdf.open(out) as pdf:
        assert any(item[2:4]==(850,1200) for item in pdf[0].get_images())
        # Mid-page and footer survive: they are not reconstructed from cropped bands.
        pix=pdf[0].get_pixmap();mid=pix.pixel(int(300/850*pix.width),int(600/1200*pix.height));assert mid[0]<250
        foot=pix.pixel(int(.8*pix.width),int(.96*pix.height));assert foot[0]>200 and foot[1]>100
    out=tmp_path/'full.docx';export(case,out,'docx')
    from docx import Document
    doc=Document(out);anchors=doc.sections[0].header.paragraphs[0]._p.xpath('.//wp:anchor[@behindDoc="1"]');assert anchors
    assert anchors[0].xpath('./wp:positionV')[0].get('relativeFrom')=='page'
    out=tmp_path/'full.xlsx';export(case,out,'xlsx')
    with zipfile.ZipFile(out) as z:
        vml=[name for name in z.namelist() if name.endswith('.vml')];assert vml
        assert b'id="CH"' in z.read(vml[0])
        assert any(b'legacyDrawingHF' in z.read(name) for name in z.namelist() if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'))
        assert Image.open(io.BytesIO(z.read('xl/media/letterpad1.png'))).size==(850,1200)
    workbook=openpyxl.load_workbook(out,data_only=True);assert workbook['certificate']['E20'].value==100
    case.report['print_layout'].update(paper='Legal');layout=layout_from(case.report,case.settings);assert layout['margins_mm']['top']>50
