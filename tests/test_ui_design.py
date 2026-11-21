"""Headless screenshot-regression policy tests; never open a Tk window."""
import ast
from pathlib import Path
from types import SimpleNamespace
import pytest
from ui_design import choose_family,readable_scaling,initial_geometry,POINT_SIZES,PALETTE

@pytest.mark.parametrize('available,expected',[
    (['Inter','DejaVu Sans'],'Inter'),(['Segoe UI','Inter'],'Segoe UI'),
    (['DejaVu Sans','Liberation Sans'],'DejaVu Sans'),(['NOTO SANS'],'NOTO SANS'),([], 'TkDefaultFont')])
def test_installed_family_selection(available,expected):assert choose_family(available)==expected

@pytest.mark.parametrize('value',[0,.2,.7,1.0,None,'invalid',10,float('nan')])
def test_bad_virtual_dpi_is_repaired(value):assert readable_scaling(value)==pytest.approx(4/3)

@pytest.mark.parametrize('value',[4/3,1.5,2,2.6667,3,4])
def test_valid_hidpi_not_double_scaled(value):assert readable_scaling(value)==value

def test_human_readable_point_sizes():
    assert POINT_SIZES['body']==12 and POINT_SIZES['small']==11
    assert 18<=POINT_SIZES['title']<=22 and 18<=POINT_SIZES['heading']<=22
    assert POINT_SIZES['tab']>=11

def test_1280_by_800_fallback_fits_desktop():
    geometry=initial_geometry(1280,800);dims,_,offset=geometry.partition('+');w,h=map(int,dims.split('x'));x,y=map(int,offset.split('+'))
    assert w+x<=1280 and h+y<=760

def luminance(color):
    values=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    a=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values]
    return sum(v*k for v,k in zip(a,[.2126,.7152,.0722]))
@pytest.mark.parametrize('fg,bg',[('white','navy'),('ink','paper'),('muted','paper'),('navy','gold')])
def test_contrast_meets_normal_text_aa(fg,bg):
    a,b=sorted([luminance(PALETTE[fg]),luminance(PALETTE[bg])]);assert (b+.05)/(a+.05)>=4.5

def test_named_fonts_and_tab_maps_without_opening_tk(monkeypatch):
    import net_asset_report as ui
    class Font:
        def __init__(self,**kw):self.options=kw
        def configure(self,**kw):self.options.update(kw)
        def actual(self,which):return self.options.get(which,'DejaVu Sans')
        def metrics(self,which):return 18
    class Style:
        def __init__(self,*_):self.styles={};self.maps={}
        def theme_use(self,which):self.theme=which
        def configure(self,name,**kw):self.styles.setdefault(name,{}).update(kw)
        def map(self,name,**kw):self.maps.setdefault(name,{}).update(kw)
    style=Style();calls=[]
    def tkcall(*args):
        calls.append(args)
        return .5 if len(args)==2 else None
    fake=SimpleNamespace(tk=SimpleNamespace(call=tkcall),configure=lambda **k:None,option_add=lambda *a:None)
    monkeypatch.setattr(ui.tkfont,'families',lambda root:['DejaVu Sans','DejaVu Sans Mono'])
    monkeypatch.setattr(ui.tkfont,'Font',Font)
    monkeypatch.setattr(ui.tkfont,'nametofont',lambda *a,**k:Font())
    monkeypatch.setattr(ui.ttk,'Style',lambda *_:style)
    ui.App._style(fake)
    assert fake.fonts['body'].options['family']=='DejaVu Sans'
    assert fake.fonts['body'].options['size']==12
    assert fake.fonts['title'].options['size']==22
    assert style.styles['Treeview']['rowheight']==38
    assert style.maps['TNotebook.Tab']['background'][0]==('selected',PALETTE['navy'])
    assert ('tk','scaling',4/3) in calls

def test_no_symbol_only_currency_or_decorative_native_labels():
    text=(Path(__file__).parents[1]/'net_asset_report.py').read_text();tree=ast.parse(text)
    strings=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
    assert not any('₹' in s or '•' in s for s in strings)
    assert 'Value (INR)' in strings
    assert any('PRIVATE  /  LOCAL  /  REVIEWED'==s for s in strings)

def test_small_screen_forms_and_metadata_remain_scrollable():
    text=(Path(__file__).parents[1]/'net_asset_report.py').read_text()
    assert 'editor_body=self.scroll_frame(self.tab_items)' in text
    assert "self.rowconfigure(2,weight=1)" in text
    assert "footer.grid(row=3,column=0,sticky='ew')" in text
    assert "split=ttk.Panedwindow(self.tab_items" not in text
    assert "canvas.focus_set()" not in text
    assert 'self.tab_tax=self.scroll_frame(outer)' in text
    assert "self.after_idle(self._maximize_startup)" in text
    assert "style='Sidebar.TFrame'" in text
