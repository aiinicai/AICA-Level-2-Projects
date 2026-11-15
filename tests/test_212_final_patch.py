"""Bounded final acceptance corrections; no GUI interaction or portal calls."""
from types import SimpleNamespace
from pathlib import Path
import copy,re
import pytest
import net_asset_report as ui
from asset_model import Case
from ui_design import preview_geometry

class Var:
    def __init__(self,value=''):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value

@pytest.mark.parametrize('screen',[(1024,578),(1280,800),(1920,1080),(800,600)])
def test_preview_is_centered_and_bounded_with_decoration_allowance(screen):
    geometry,minimum=preview_geometry(*screen)
    width,height,x,y=map(int,re.fullmatch(r'(\d+)x(\d+)\+(\d+)\+(\d+)',geometry).groups())
    assert x>=0 and y>=0 and x+width<=screen[0]-20 and y+height<=screen[1]-40
    assert minimum[0]<=width and minimum[1]<=height


def test_tabs_have_constant_state_geometry_and_ignore_wheel():
    source=Path(ui.__file__).read_text()
    assert "font=[('selected',self.fonts['tab']),('!selected',self.fonts['tab'])]" in source
    assert "padding=[('selected',(18,12)),('!selected',(18,12))]" in source
    assert "expand=[('selected',(0,0,0,0)),('!selected',(0,0,0,0))]" in source
    assert "for event in ('<MouseWheel>','<Button-4>','<Button-5>'):self.notebook.bind(event,lambda e:'break')" in source


def test_report_exports_and_preview_pinned_outside_scrolling_form():
    source=Path(ui.__file__).read_text();block=source.split('    def _report_tab(self):',1)[1].split('    def _print_settings',1)[0]
    assert block.index('report_actions.pack')<block.index('body=self.scroll_frame')
    assert "ttk.Button(report_actions,text='Preview final PDF'" in block
    assert 'ttk.Button(report_actions,text=label' in block
    assert 'ttk.Button(actions,text=label' not in block
    assert 'self.preview_canvas._scroll_canvas=self.preview_canvas' in source


def test_cancel_resets_once_without_touching_saved_asset():
    case=Case();case.people[0].name='SYNTHETIC';case.add_asset('Cash in Hand',100,case.people[0].id,'Cash');before=copy.deepcopy(case.to_dict());calls=[]
    fake=SimpleNamespace(case=case,_edit_index=0,_asset_edit_baseline={'old':'snapshot'},asset_type=Var('Immovable Property'),asset_amount=Var('1000'),asset_details=Var('edited'),asset_name=Var('Edited property'),asset_owner=Var('OLD'),more_open=Var(True),asset_fv={'valuer':Var('Edited valuer')},asset_section=Var('A'),current_person=case.people[0].id,_people_labels={case.people[0].id:'SYNTHETIC'},asset_save_button=SimpleNamespace(configure=lambda **kw:calls.append(kw)),_asset_fields=lambda:calls.append('rebuild'),status=Var())
    fake.clear_asset=lambda:ui.App.clear_asset(fake)
    ui.App.cancel_asset_edit(fake)
    assert fake._edit_index is None and fake._asset_edit_baseline is None and not fake.more_open.get()
    assert fake.asset_amount.get()==fake.asset_details.get()==fake.asset_fv['valuer'].get()==''
    assert fake.asset_type.get()==fake.asset_name.get()=='Cash in Hand' and fake.asset_owner.get()=='SYNTHETIC'
    assert calls.count('rebuild')==1 and calls[-1]=={'text':'Add item'} and case.to_dict()==before
    assert 'cancelled' in fake.status.get()


def test_saved_case_is_clean_open_confirmation_only_for_real_changes(tmp_path,monkeypatch):
    case=Case();case.people[0].name='SYNTHETIC';calls=[]
    fake=SimpleNamespace(case=case,client_file=str(tmp_path/'case.json'),_sync_case=lambda:None,status=Var())
    monkeypatch.setattr(ui.messagebox,'askyesno',lambda *a,**k:calls.append(a) or True)
    ui.App.save_client(fake)
    assert not ui.App._case_is_dirty(fake) and ui.App._confirm_discard(fake,'Open another case') and not calls
    case.report['purpose']='changed'
    assert ui.App._case_is_dirty(fake) and ui.App._confirm_discard(fake,'Open another case') and len(calls)==1
    monkeypatch.setattr(ui.filedialog,'asksaveasfilename',lambda **k:str(tmp_path/'save-as.json'))
    ui.App.save_client(fake,save_as=True)
    assert not ui.App._case_is_dirty(fake) and ui.App._confirm_discard(fake,'Open another case') and len(calls)==1


def test_unapplied_inline_edit_remains_dirty_even_if_model_saved():
    case=Case();case.people[0].name='SYNTHETIC'
    fake=SimpleNamespace(case=case,_sync_case=lambda:None,_edit_index=0,asset_type=Var('Cash in Hand'),asset_owner=Var('SYNTHETIC'),asset_amount=Var('100'),asset_name=Var('Cash in Hand'),asset_details=Var('Cash'),asset_fv={},asset_section=Var('B'))
    fake._asset_edit_baseline=ui.App._asset_draft(fake);ui.App._mark_case_clean(fake)
    assert not ui.App._case_is_dirty(fake)
    fake.asset_amount.set('200');assert ui.App._case_is_dirty(fake)
    ui.App._mark_case_clean(fake);assert ui.App._case_is_dirty(fake)
