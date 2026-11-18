import json, threading
from datetime import date
from pathlib import Path
import pytest
from werkzeug.serving import make_server
from openpyxl import load_workbook
from config import Settings,COLUMNS,NA
from core.mock_portal import create_mock,demo_gstin
from core.portal_client import PortalClient,PortalError
from core.parser import parse
from core.storage import Storage
from core.engine import Engine
from core.exporter import export
from ui_web import create_app

@pytest.fixture
def portal(tmp_path):
    app=create_mock();server=make_server('127.0.0.1',0,app,threaded=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    sleeps=[];settings=Settings(base=f'http://127.0.0.1:{server.server_port}',demo=True,interval=0,timeout=2)
    client=PortalClient(settings,sleeper=sleeps.append);store=Storage(tmp_path)
    yield app,client,Engine(client,store,settings),sleeps
    client.close();store.db.close();server.shutdown();thread.join()

def answer(app,client):
    # Test-only access to synthetic server session, never used against GST portal.
    cookie=client.session.cookies.get('session')
    return app.session_interface.get_signing_serializer(app).loads(cookie)['captcha']

def test_correct(portal):
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    assert len(e.rows)==1 and e.logs[-1]['Result']=='OK' and len(e.details)==4

def test_wrong_then_correct(portal):
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26');e.submit('wrong');assert e.challenge.attempts==1
    e.submit(answer(app,c));assert len(e.rows)==1

def test_three_wrong(portal):
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26')
    for _ in range(3): e.submit('wrong')
    assert e.logs[-1]['Result']=='CAPTCHA FAILED' and e.current is None

def test_notfound(portal):
    app,c,e,_=portal;app.config['SCENARIO']='notfound';e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    assert e.logs[-1]['Result']=='NOT FOUND'

def test_timeout(portal):
    app,c,e,s=portal;app.config['SCENARIO']='timeout';c.settings.timeout=.02
    e.start([demo_gstin()],'2025-26');e.submit(answer(app,c));assert e.logs[-1]['Result']=='NETWORK ERROR'
    assert app.config['HITS']==3

def test_500(portal):
    app,c,e,s=portal;app.config['SCENARIO']='500';e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    assert e.logs[-1]['Result']=='NETWORK ERROR' and app.config['HITS']==3
    assert 2 in s and 4 in s

def test_429(portal):
    app,c,e,s=portal;app.config['SCENARIO']='429';e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    assert len(e.rows)==1 and app.config['HITS']==3 and 2 in s and 4 in s

def test_batch_ten(portal):
    app,c,e,_=portal
    good=[demo_gstin(entity=str(n)) for n in range(1,8)]
    e.start(good+['bad','ABCXE1234F','00AAACT1234K1Z0'],'2025-26')
    while e.current:e.submit(answer(app,c))
    assert len(e.rows)==7 and sum(x['Result']=='INVALID' for x in e.logs)==3
    assert app.config['HITS']==7

def test_pan_three(portal):
    app,c,e,_=portal;e.start(['AAACT1234K'],'2025-26');e.submit(answer(app,c))
    while e.current:e.submit(answer(app,c))
    assert len(e.rows)==3 and {r['PAN'] for r in e.rows}=={'AAACT1234K'}

def test_invalid_never_sent(portal):
    app,c,e,_=portal;e.start(['ABCXE1234F','bad'],'2025-26');assert app.config['HITS']==0 and e.current is None

def test_cap_persists(portal):
    app,c,e,_=portal;e.settings.daily_cap=1;e.start([demo_gstin(),demo_gstin('07')],'2025-26');e.submit(answer(app,c))
    assert len(e.rows)==1 and 'cap' in e.logs[-1]['Message']
    other=Storage(e.storage.folder)
    with pytest.raises(ValueError):other.reserve(1)
    other.db.close()

@pytest.mark.parametrize('variant',['regular','composition','cancelled','zero','five','many','missing'])
def test_parser_variants(variant):
    fixture=json.loads((Path(__file__).parent/'fixtures'/f'{variant}.json').read_text())
    row,details=parse(fixture,demo_gstin(),'2025-26')
    assert list(row)[:len(COLUMNS)]==COLUMNS
    if variant=='composition':assert row['TAXPAYER']=='Composition'
    if variant=='cancelled':assert row['GSTIN/UIN STATUS']=='Cancelled (Effective date: 02/08/2024)'
    if variant in ('zero','missing'):assert row['ADDITIONAL PLACE OF BUSINESS']==NA
    if variant=='five':assert row['ADDITIONAL PLACE OF BUSINESS']==' | '.join(f'Address {n}' for n in range(5))
    if variant=='many':assert len(row[COLUMNS[11]].splitlines())==25
    if variant=='missing':assert row['TRADE NAME']==NA
    else:assert row['DATE OF REGISTRATION']==date(2017,7,1)

def test_html():
    row,_=parse('<p data-field="tradeNam">HTML Demo</p>',demo_gstin(),'2025-26');assert row['TRADE NAME']=='HTML Demo'

def test_extra():
    row,_=parse({'newField':'extra'},demo_gstin(),'2025-26');assert 'newField' in row['Other']

def test_output(portal,tmp_path):
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    e.rows[0]['TRADE NAME']='=HYPERLINK("x")'
    path=export(tmp_path/'out.xlsx',e.rows,e.details,e.logs);wb=load_workbook(path)
    assert wb.sheetnames==['Taxpayers','Return_Detail','Run_Log']
    ws=wb['Taxpayers'];assert [c.value for c in ws[1]][:len(COLUMNS)]==COLUMNS and ws.max_row==2
    assert ws['K2'].value==NA and ws['C2'].data_type=='s' and ws['C2'].value.startswith("'=")
    assert ws['D2'].is_date and ws.freeze_panes=='A2' and wb['Return_Detail']['E2'].is_date
    wb.close()

@pytest.mark.parametrize('prefix',['=','+','-','@','  ='])
def test_injection(prefix,tmp_path):
    path=export(tmp_path/'safe.xlsx',[{'PAN':prefix+'payload'}],[],[]);wb=load_workbook(path)
    assert wb.active['A2'].value.startswith("'") and wb.active['A2'].data_type=='s';wb.close()

def test_web(portal):
    from bs4 import BeautifulSoup
    app,c,e,_=portal;web=create_app(e);ui=web.test_client()
    assert ui.get('/').status_code==200
    assert ui.post('/start',data={'values':'bad'}).status_code==403
    token=BeautifulSoup(ui.get('/').data,'html.parser').select_one('input[name=token]')['value']
    assert ui.post('/start',data={'token':token,'values':demo_gstin(),'year':'2025-26'}).status_code==302
    assert ui.get('/captcha').data.startswith(b'\x89PNG')
    ui.post('/submit',data={'token':token,'answer':answer(app,c)})
    assert len(e.rows)==1 and ui.get('/download').status_code==200
    assert ui.get('/',headers={'Host':'evil.example'}).status_code==403


def test_new_batch_resets_results(portal):
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    e.start([demo_gstin()],'2024-25');assert e.rows==[] and e.current==demo_gstin()
    e.submit(answer(app,c));assert len(e.rows)==1 and e.rows[0]['RETURN STATUS YEAR']=='2024-25'

@pytest.mark.parametrize('suffix',['.txt','.csv','.xlsx'])
def test_upload(suffix):
    from ui_web import read_upload
    from werkzeug.datastructures import FileStorage
    import io
    if suffix=='.xlsx':
        from openpyxl import Workbook
        wb=Workbook();wb.active.append(['PAN']);wb.active.append(['AAACT1234K']);out=io.BytesIO();wb.save(out);out.seek(0)
    else:out=io.BytesIO(b'PAN\nAAACT1234K\n')
    assert read_upload(FileStorage(stream=out,filename='input'+suffix))==['AAACT1234K']

def test_live_interval_minimum():
    assert Settings(interval=0).interval==2 and Settings().interval==3


def test_observed_goods_and_jurisdiction():
    row,_=parse({'ctj':'Centre division (Jurisdictional Office)','stj':'State circle','bzgddtls':[{'hsncd':'1001','gdes':'Wheat'}],'bzsdtls':[{'saccd':'9983','sdes':'Services'}]},demo_gstin(),'2025-26')
    assert row[COLUMNS[11]]=='HSN 1001 - Wheat\nSAC 9983 - Services'
    assert row['ADMIN OFFICE']=='Centre: Centre division' and row['OTHER OFFICE']=='State: State circle'


def token_for(ui):
    from bs4 import BeautifulSoup
    return BeautifulSoup(ui.get('/').data,'html.parser').select_one('input[name=token]')['value']

def test_batch_library_web(portal):
    import io
    from core.batches import BatchStore
    app,c,e,_=portal;ui=create_app(e).test_client();token=token_for(ui)
    response=ui.post('/batches/add',data={'token':token,'header':'on','files':(io.BytesIO(b'Name,PAN\nSample,AAACT1234K\nSecond,bad\n'),'bulk.csv')})
    assert response.status_code==302
    store=BatchStore(e.storage.folder);file=store.list()[0];identifier=file['id']
    assert file['count']==2 and 'Sample' in ui.get(f'/batches/{identifier}/preview').text
    data={'token':token,'batch_id':identifier,'column_'+identifier:'1','kind':'PAN','year':'2025-26'}
    ui.post('/validate-batch',data=data)
    assert e.current is None and app.config['HITS']==0
    assert '1 valid, 1 invalid' in ui.get('/').text
    ui.post('/start',data=data);assert e.current=='AAACT1234K'
    # Deletion removes the local saved upload, while the active run keeps its copied queue.
    ui.post(f'/batches/{identifier}/delete',data={'token':token});assert store.list()==[]
    assert e.current=='AAACT1234K'

def test_input_type_mismatch_never_sent(portal):
    app,c,e,_=portal;e.start(['AAACT1234K'],'2025-26','GSTIN')
    assert e.current is None and app.config['HITS']==0
    assert e.logs[0]['Result']=='INVALID' and 'Expected GSTIN' in e.logs[0]['Message']

def test_pan_mode_expands_gstins(portal):
    app,c,e,_=portal;e.start(['AAACT1234K'],'2025-26','PAN')
    while e.current:e.submit(answer(app,c))
    assert len(e.rows)==3 and all(r['Result']=='OK' for r in e.logs)

def test_batch_files_persist_and_delete(tmp_path):
    from core.batches import BatchStore
    store=BatchStore(tmp_path);record=store.add('list.csv',b'Name,GSTIN\nIgnore,AAACT1234K\n')
    other=BatchStore(tmp_path);assert other.values(record['id'],1)==['AAACT1234K']
    other.delete(record['id']);assert store.list()==[]
    with pytest.raises(ValueError):other.delete('../../original.csv')

def test_bulk_preview_duplicates_and_empty():
    from core.batches import preview
    rows=preview([' aaact1234k ','AAACT1234K','','bad'],'PAN')
    assert rows[0]['Validation']=='VALID' and rows[1]['Duplicate'].startswith('Yes')
    assert rows[2]['Validation']=='INVALID' and rows[3]['Validation']=='INVALID'

def test_headerless_and_delimited_uploads(tmp_path):
    from core.batches import BatchStore
    store=BatchStore(tmp_path)
    a=store.add('list.csv',b'AAACT1234K;Sample\nAABCU9603R;Other\n',header=False)
    assert store.values(a['id'],0)==['AAACT1234K','AABCU9603R']
    b=store.add('list.txt',b'AAACT1234K\nAABCU9603R\n',header=True)
    assert store.values(b['id'],0)==['AAACT1234K','AABCU9603R']

def test_delete_requires_csrf(portal):
    import io
    from core.batches import BatchStore
    app,c,e,_=portal;ui=create_app(e).test_client();store=BatchStore(e.storage.folder)
    f=store.add('list.txt',b'AAACT1234K')
    assert ui.post(f"/batches/{f['id']}/delete").status_code==403
    assert len(store.list())==1

def test_empty_uploaded_cells_logged(portal):
    app,c,e,_=portal;e.start(['','bad'],'2025-26','PAN')
    assert len(e.logs)==2 and all(r['Result']=='INVALID' for r in e.logs)


def test_download_with_relative_data_folder(portal):
    import os
    app,c,e,_=portal;e.storage.folder=Path(os.path.relpath(e.storage.folder))
    assert create_app(e).test_client().get('/download').status_code==200


def test_return_year_value_and_all_types(portal):
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    assert {d['Return Type'] for d in e.details}=={'GSTR3B','GSTR1','GSTR9','GSTR9C'}
    assert all(e.rows[0][name]!=NA for name in COLUMNS[13:17])
    assert e.return_reports[0]['State']=='AVAILABLE'

def test_returns_error_visible_and_retry(portal):
    app,c,e,_=portal;app.config['RETURN_ERROR']=True
    e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    assert e.return_reports[0]['State']=='ERROR' and e.rows[0]['GSTR-3B']==NA
    assert any(r['Result']=='NETWORK ERROR' and 'Return filing' in r['Message'] for r in e.logs)
    app.config['RETURN_ERROR']=False;e.retry_returns(demo_gstin())
    assert len(e.rows)==1 and len(e.details)==4 and e.return_reports[0]['State']=='AVAILABLE'

def test_returns_separate_human_captcha(portal):
    app,c,e,_=portal;app.config['RETURN_CAPTCHA']=True
    e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    assert e.phase=='returns' and e.challenge is not None
    e.submit('wrong');assert e.challenge.attempts==1
    e.submit(answer(app,c));assert len(e.details)==4 and len(e.rows)==1

def test_returns_three_wrong_retains_profile(portal):
    app,c,e,_=portal;app.config['RETURN_CAPTCHA']=True
    e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    for _ in range(3): e.submit('wrong')
    assert len(e.rows)==1 and e.return_reports[0]['State']=='ERROR' and e.current is None
    assert any(r['Result']=='CAPTCHA FAILED' for r in e.logs)

@pytest.mark.parametrize('label',['2025-2026','20252026','202526','2025-26'])
def test_return_year_formats(label):
    row,details=parse({},demo_gstin(),'2025-26',{'data':{'filingStatus':[[{'rtntype':'gstr-1/iff','taxp':'April','status':'Filed','dof':'11/05/2025','fy':label}]]}})
    assert len(details)==1 and row['GSTR-1/IFF']!=NA

def test_captcha_image_validation():
    from core.captcha import png_image
    with pytest.raises(PortalError):png_image(b'<html>offline</html>')


def test_unknown_returns_response_is_error(portal):
    app,c,e,_=portal
    def responses(path,payload=None,method='POST'):
        return {'status':1,'data':[{'year':'2025-26','value':'opaque-year-value'}]} if 'dropdown' in path else {'unexpected':'schema'}
    c._json=responses
    with pytest.raises(PortalError,match='recognized filing list'):c.returns(demo_gstin(),'2025-26')

def test_return_captcha_uses_cached_year_token(portal):
    app,c,e,_=portal;calls=[]
    def responses(path,payload=None,method='POST'):
        calls.append((path,payload))
        return {'status':1,'data':[{'year':'2025-26','value':'opaque-value'}]} if 'dropdown' in path else {'filingStatus':[]}
    c._json=responses;c.returns(demo_gstin(),'2025-26');c.returns(demo_gstin(),'2025-26','typed-answer')
    assert len([x for x in calls if 'dropdown' in x[0]])==1
    assert calls[-1][1]=={'gstin':demo_gstin(),'fy':'opaque-value','captcha':'typed-answer'}

def test_unavailable_year_explained(portal):
    app,c,e,_=portal
    with pytest.raises(PortalError,match='not offered'):c.returns(demo_gstin(),'2030-31')


def test_legal_name_excel_and_missing_value(portal,tmp_path):
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26');e.submit(answer(app,c))
    assert e.rows[0]['Legal Name of Business']=='DEMO ONLY - Sample Legal Company Limited'
    workbook=load_workbook(export(tmp_path/'legal.xlsx',e.rows,e.details,e.logs));ws=workbook['Taxpayers']
    headings=[v.value for v in ws[1]];index=headings.index('Legal Name of Business')+1
    assert index==18 and ws.cell(2,index).value==e.rows[0]['Legal Name of Business'];workbook.close()
    row,_=parse({},demo_gstin(),'2025-26');assert row['Legal Name of Business']==NA

def test_completed_task_download_delete_and_new_task(portal):
    import io
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26');e.submit(answer(app,c));identifier=e.task_id
    ui=create_app(e).test_client();token=token_for(ui)
    assert len(e.storage.tasks())==1
    saved=e.storage.task(identifier);assert saved['rows'][0]['DATE OF REGISTRATION']==date(2017,7,1)
    response=ui.get(f'/tasks/{identifier}/download');assert response.status_code==200
    wb=load_workbook(io.BytesIO(response.data));assert 'Legal Name of Business' in [c.value for c in wb.active[1]];wb.close()
    ui.post('/tasks/new',data={'token':token});assert e.task_id is None and e.rows==[] and len(e.storage.tasks())==1
    ui.post(f'/tasks/{identifier}/delete',data={'token':token})
    assert e.storage.tasks()==[] and e.storage.history()==[]
    assert not (e.storage.folder/'exports'/f'task-{identifier}.xlsx').exists()

def test_delete_current_task_keeps_uploaded_files_and_budget(portal):
    from core.batches import BatchStore
    app,c,e,_=portal;e.settings.daily_cap=1
    BatchStore(e.storage.folder).add('input.txt',b'AAACT1234K')
    e.start([demo_gstin()],'2025-26');e.submit(answer(app,c));identifier=e.task_id
    ui=create_app(e).test_client();ui.post(f'/tasks/{identifier}/delete',data={'token':token_for(ui)})
    assert e.rows==[] and len(BatchStore(e.storage.folder).list())==1
    with pytest.raises(ValueError):e.storage.reserve(1)

def test_legacy_history_database_migration(tmp_path):
    import sqlite3
    db=sqlite3.connect(tmp_path/'history.sqlite');db.execute('CREATE TABLE log(timestamp TEXT,input TEXT,result TEXT,message TEXT)')
    db.execute("INSERT INTO log VALUES ('old','input','OK','message')");db.commit();db.close()
    storage=Storage(tmp_path);assert storage.history()[0]['Message']=='message';assert storage.tasks()==[];storage.db.close()

def test_captcha_short_input_not_sent(portal):
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26');ui=create_app(e).test_client()
    ui.post('/submit',data={'token':token_for(ui),'answer':'12'})
    assert app.config['HITS']==0 and e.challenge.attempts==0
    assert 'Enter all 6 digits' in ui.get('/').text

def test_captcha_stale_image_rejected(portal):
    app,c,e,_=portal;e.start([demo_gstin()],'2025-26');old=e.challenge.token;e.refresh();ui=create_app(e).test_client()
    ui.post('/submit',data={'token':token_for(ui),'answer':answer(app,c),'challenge_token':old})
    assert app.config['HITS']==0 and 'CAPTCHA has changed' in ui.get('/').text

def test_captcha_session_page_loaded_once(portal):
    from config import PATHS
    app,c,e,_=portal;calls=[];original=c._request
    def request(method,path,payload=None):calls.append(path);return original(method,path,payload)
    c._request=request;c.captcha();c.captcha()
    assert calls.count(PATHS['page'])==1 and len(calls)==3

def test_background_ui_responsive_and_duplicate_guard(portal):
    import threading,time
    app,c,e,_=portal;gate=threading.Event();started=threading.Event();original=c.captcha
    def slow():started.set();gate.wait(3);return original()
    c.captcha=slow;web=create_app(e,background=True);jobs=web.extensions['jobs'];ui=web.test_client();token=token_for(ui)
    try:
        before=time.monotonic();ui.post('/start',data={'token':token,'values':demo_gstin(),'year':'2025-26'})
        assert time.monotonic()-before<.75 and started.wait(1)
        before=time.monotonic();assert ui.get('/api/status').json['busy'] and ui.get('/').status_code==200
        assert time.monotonic()-before<.75
        ui.post('/start',data={'token':token,'values':'AAACT1234K','year':'2025-26'})
        assert 'already running' in web.test_client().get('/').text or jobs.status()['busy']
        gate.set();jobs.wait();assert e.current==demo_gstin() and e.challenge is not None
    finally:gate.set();jobs.close()

def test_background_portal_operations_use_one_worker(portal):
    import threading
    app,c,e,_=portal;ids=[];orig_captcha=c.captcha;orig_lookup=c.lookup
    def captcha():ids.append(threading.get_ident());return orig_captcha()
    def lookup(value,typed):ids.append(threading.get_ident());return orig_lookup(value,typed)
    c.captcha=captcha;c.lookup=lookup;web=create_app(e,background=True);ui=web.test_client();jobs=web.extensions['jobs'];token=token_for(ui)
    try:
        ui.post('/start',data={'token':token,'values':demo_gstin(),'year':'2025-26'});jobs.wait()
        ui.post('/submit',data={'token':token,'answer':answer(app,c),'challenge_token':jobs.view().challenge.token});jobs.wait()
        assert len(e.rows)==1 and len(set(ids))==1 and ids[0]!=threading.get_ident()
    finally:jobs.close()

def test_stop_slow_task_and_start_fresh(portal):
    import threading
    app,c,e,_=portal;gate=threading.Event();started=threading.Event();original=c.captcha
    def slow():started.set();gate.wait(3);return original()
    c.captcha=slow;web=create_app(e,background=True);ui=web.test_client();jobs=web.extensions['jobs'];token=token_for(ui)
    try:
        ui.post('/start',data={'token':token,'values':demo_gstin(),'year':'2025-26'});assert started.wait(1)
        ui.post('/tasks/stop',data={'token':token});gate.set();jobs.wait()
        assert e.cancelled and e.current is None and e.storage.tasks()[0]['status']=='STOPPED'
        ui.post('/tasks/new',data={'token':token});jobs.wait();assert e.task_id is None and e.rows==[]
    finally:gate.set();jobs.close()


def test_stop_after_response_prevents_browser_or_more_requests(portal):
    import threading
    app,c,e,_=portal;cancel=threading.Event();calls=[]
    class Reply:status_code=403;content=b'blocked'
    def request(*args,**kwargs):calls.append(1);cancel.set();return Reply()
    c.settings.demo=False;c.cancel_requested=cancel.is_set;c.session.request=request
    c._browser=lambda:(_ for _ in ()).throw(AssertionError('Fallback must not start after stop'))
    with pytest.raises(PortalError,match='stopped'):c._request('GET','/services/searchtp')
    assert len(calls)==1


@pytest.mark.parametrize('status',['Cancelled','Cancelled suo-moto','Cancelled on application of Taxpayer','Suspended'])
def test_status_effective_date(status):
    row,_=parse({'sts':status,'cxdt':'2024-08-02'},demo_gstin(),'2025-26')
    assert row['GSTIN/UIN STATUS']==status+' (Effective date: 02/08/2024)'

@pytest.mark.parametrize('status',['Cancelled','Suspended'])
def test_status_missing_date_explicit(status):
    row,_=parse({'sts':status},demo_gstin(),'2025-26')
    assert row['GSTIN/UIN STATUS']==status+' (Effective date: Not Available)'

def test_active_status_does_not_attach_old_cancellation_date():
    row,_=parse({'sts':'Active','cxdt':'02/08/2024'},demo_gstin(),'2025-26');assert row['GSTIN/UIN STATUS']=='Active'

def test_cancelled_date_export(tmp_path):
    row,details=parse({'sts':'Cancelled','cxdt':'02/08/2024','lgnm':'Published Legal Name'},demo_gstin(),'2025-26')
    wb=load_workbook(export(tmp_path/'cancelled.xlsx',[row],details,[]));ws=wb['Taxpayers']
    assert ws['F2'].value=='Cancelled (Effective date: 02/08/2024)' and ws.cell(2,18).value=='Published Legal Name';wb.close()
