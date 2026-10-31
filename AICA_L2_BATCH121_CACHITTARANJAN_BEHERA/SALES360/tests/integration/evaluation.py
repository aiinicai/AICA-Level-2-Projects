"""Exercise a freshly built offline bundle with isolated fictional import records."""
import json,os,re,secrets,subprocess,sys,time
from pathlib import Path
from urllib.request import build_opener,ProxyHandler,Request
from urllib.error import HTTPError
root=Path(__file__).resolve().parents[2];(root/'test-results').mkdir(exist_ok=True);(root/'output').mkdir(exist_ok=True);bundle=Path(sys.argv[1]).resolve();tag=sys.argv[2] if len(sys.argv)>2 else 'final';assert tag.replace('-','').isalnum();data=root/('output/test101-installed-data-'+tag);assert not data.exists()
python=bundle/'runtime/python/python.exe';launcher=bundle/'SALES360.py';env={k:v for k,v in os.environ.items() if not k.startswith('SALES360_')};env['SALES360_BOOTSTRAP_PASSWORD']='Inherited value must not enroll an owner';opener=build_opener(ProxyHandler({}));log=open(root/'output/installed090.log','a',encoding='utf-8')
process=subprocess.Popen([str(python),str(launcher),'--data-dir',str(data),'--port','5131','--no-browser'],env=env,stdout=log,stderr=log,creationflags=0x08000000)
def request(path,body=None,cookie=None):
    r=Request(base+'/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','X-Sales360-Request':'1',**({'Cookie':cookie} if cookie else {})})
    try:response=opener.open(r,timeout=180)
    except HTTPError as e:response=e
    raw=response.read();return response.status,json.loads(raw) if raw else {},response.headers.get('Set-Cookie','').split(';')[0]
try:
    for _ in range(150):
        try:
            base=json.loads((data/'running.json').read_text())['url'];health=request('/health')[1]
            if health['version']=='0.9.1':break
        except Exception:pass
        time.sleep(1)
    else:raise AssertionError('Runtime did not start')
    d=json.loads((root/'examples/dataset.json').read_text());tot=d['totals'];token=re.search(r'#setup=([a-f0-9]{64})',(data/'first-run-setup.txt').read_text())[1];pw=secrets.token_urlsafe(24)
    enrolled=request('/auth/first-administrator',{'name':'Fictional Test Owner','identifier':'test101owner','recovery_email':'test101owner@example.invalid','company_name':d['supplier']['legal_name'],'period_start':'2026-01-01','period_end':'2026-12-31','password':pw,'confirm_password':pw,'setup_token':token});assert enrolled[0]==200,enrolled;cookie=enrolled[2]
    import_results=[]
    for filename,count in [('01-Import-Customers-001-to-100.xlsx',100),('02-Import-Customer-101.xlsx',1)]:
        content=(root/'examples'/filename).read_bytes();boundary='Corrected'+secrets.token_hex(8)
        raw=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'.encode()+content+f'\r\n--{boundary}--\r\n'.encode())
        batch=json.load(opener.open(Request(base+'/api/workbook-imports/preview',data=raw,headers={'Cookie':cookie,'X-Sales360-Request':'1','Content-Type':'multipart/form-data; boundary='+boundary}),timeout=120))
        assert not batch['errors'],batch['errors'];assert not batch['payload']['masterPlanErrors'],batch['payload']['masterPlanErrors'];assert len(batch['payload']['statements'])==count
        postbody={'auto_create_masters':True,'confirm_master_plan':True,'currency':'AED','vat_rate':5,'review_reference':'Fictional template matched workbook reconciliation','acknowledge_warnings':True,'confirm_posted_invoices':True,'confirm_project_override':True}
        posted=request('/workbook-imports/'+batch['id']+'/commit',postbody,cookie);assert posted[0]==200,posted;assert posted[1]['created']==count,posted
        assert posted[1]['masters']['customers_created']==count and posted[1]['masters']['projects_created']==count
        assert request('/workbook-imports/'+batch['id']+'/commit',postbody,cookie)[1]['created']==0
        import_results.append({'file':filename,'statements':count,'previewErrors':0,'masterPlanErrors':0,'invoicesCreated':count,'duplicateCommitCreatesZero':True})
    customers=request('/customers',cookie=cookie)[1];assert len(customers)==101
    assert request('/projects?page=1',cookie=cookie)[1]['total']==101
    invoices=request('/invoices?asOf=2026-10-29',cookie=cookie)[1];assert len(invoices)==101
    for key in ['net','vat']:assert round(sum(i[key] for i in invoices),2)==tot[key]
    receipts=request('/receipts',cookie=cookie)[1];assert len(receipts)==sum(r['paid']>0 for r in d['records']);assert round(sum(r['amount'] for r in receipts),2)==tot['paid']
    for record in d['records']:
        customer=next(c for c in customers if c['name']==record['customer']);statement=request('/statements?customerId='+customer['id']+'&asOf=2026-10-29',cookie=cookie)[1];assert round(statement['closingBalance'],2)==record['outstanding'],record['number']
    assert request('/workbook-imports/'+batch['id']+'/commit',postbody,cookie)[1]['created']==0
    assert len(request('/invoices?asOf=2026-10-29',cookie=cookie)[1])==101
    result={'passed':True,'version':'0.9.1','batchResults':import_results,'customers':101,'projects':101,'invoices':101,'matchingCustomerBalancesChecked':101,'receiptCount':len(receipts),'duplicateCommitCreatesZero':True,'totals':tot,'dataIsolatedFromLiveCompany':True}
    (root/('test-results/evaluation-'+tag+'.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result))
finally:
    subprocess.run([str(python),str(launcher),'--data-dir',str(data),'--stop'],env=env,stdout=log,stderr=log,timeout=180,check=True,creationflags=0x08000000);process.wait(timeout=15);log.close()

