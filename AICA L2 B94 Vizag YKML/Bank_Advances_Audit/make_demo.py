"""Regenerate fictional demonstration CSVs. No real account information."""
import csv
import json
from datetime import date,timedelta
from pathlib import Path
from audit_engine import SCHEMAS,DEFAULT_POLICY

def make_demo(root=None):
    root=Path(root or Path(__file__).parent);p=root/'sample_data';p.mkdir(parents=True,exist_ok=True)
    accounts=[]
    def a(aid,bid,name,ft,out,limit,dp,expiry='2027-03-31'):
        accounts.append(dict(account_id=aid,borrower_id=bid,borrower_name=name,branch='DEMO-BRANCH',facility_type=ft,
          opened_date='2020-01-01',outstanding=out,sanctioned_limit=limit,bank_dp=dp,
          sanction_expiry=expiry,stock_margin_pct=25,receivable_margin_pct=40,creditor_method='Before margin',
          bank_classification='Standard',source_ref='Fictional sanction/account extract '+aid))
    a('CC001','B001','Example Healthy Traders','CC',600000,1000000,705000)
    a('CC002','B002','Example DP Review Traders','CC',850000,1000000,900000,'2026-08-31')
    a('CC003','B003','Example Shared Borrower','CC',1200000,1000000,1000000)
    a('CC004','B004','Example Partial History','CC',400000,700000,435000)
    a('OD005','B005','Example No Credit OD','OD',200000,500000,300000)
    a('TL006','B006','Example Equipment Finance','TL',600000,1000000,'')
    a('TL007','B003','Example Shared Borrower','TL',300000,500000,'')
    a('TL008','B008','Example Current Term Loan','TL',500000,800000,'')
    stocks=[]
    def s(i,aid,dt,st,si,cr,rt,ri):stocks.append(dict(record_id=i,account_id=aid,statement_date=dt,stock_total=st,stock_ineligible=si,
        trade_creditors=cr,receivables_total=rt,receivables_ineligible=ri,source_ref='Fictional stock/debtor certificate '+i))
    s('ST01','CC001','2026-08-31',1000000,100000,200000,400000,100000)
    s('ST02','CC002','2026-05-31',1000000,100000,200000,400000,100000)
    s('ST03','CC003','2026-08-31',2000000,0,0,0,0)
    s('ST04','CC004','2026-08-31',600000,0,100000,100000,0)
    s('ST05','OD005','2026-08-31',400000,0,0,0,0)
    daily=[];asof=date(2026,9,30)
    for acct in accounts:
        if acct['facility_type']=='TL':continue
        days=30 if acct['account_id']=='CC004' else 90
        for offset in range(days):
            day=asof-timedelta(days=days-1-offset);aid=acct['account_id']
            daily.append(dict(record_id=f'D-{aid}-{day.isoformat()}',account_id=aid,date=day,
                closing_balance=acct['outstanding'],credits=0 if aid=='OD005' else 10000,
                interest_debit=100 if aid=='OD005' else 300,sanctioned_limit=acct['sanctioned_limit'],
                drawing_power=acct['bank_dp'],source_ref='Fictional complete day-end extract '+aid))
    dues=[]
    def due(i,aid,dt,pd,it,pp,ip):dues.append(dict(due_id=i,account_id=aid,due_date=dt,principal_due=pd,interest_due=it,
                  principal_paid=pp,interest_paid=ip,source_ref='Fictional schedule/allocations '+i))
    due('DUE06','TL006','2026-06-30',100000,10000,0,0)
    due('DUE07','TL007','2026-09-15',30000,3000,10000,1000)
    due('DUE08A','TL008','2026-09-01',50000,5000,50000,5000)
    due('DUE08B','TL008','2026-10-01',50000,5000,0,0)
    docs=[]
    for acct in accounts:
        for idx,typ in enumerate(DEFAULT_POLICY['required_documents'][acct['facility_type']],1):
            aid=acct['account_id'];expiry='2027-09-30' if typ=='Insurance' else ''
            status='Available'
            if aid=='CC002' and typ=='Insurance':expiry='2026-09-15'
            if aid=='CC004' and typ=='Charge registration':status='Missing'
            docs.append(dict(doc_id=f'DOC-{aid}-{idx}',account_id=aid,document_type=typ,status=status,valid_until=expiry,
                source_ref='Fictional document register '+aid+' '+typ,remarks='Fictional register assertion; document not authenticated.'))
    data=dict(accounts=accounts,daily=daily,stocks=stocks,dues=dues,documents=docs)
    for kind,rows in data.items():
        for suffix,content in [('demo',rows),('blank_template',[])]:
            with (p/f'{kind}_{suffix}.csv').open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=SCHEMAS[kind]);w.writeheader();w.writerows(content)
    (root/'audit_policy.json').write_text(json.dumps(DEFAULT_POLICY,indent=2),encoding='utf-8')
    print('Fictional inputs created: 8 accounts, 7 borrowers, 390 daily rows.')

if __name__=='__main__':make_demo()
