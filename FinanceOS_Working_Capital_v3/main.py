import sys, re, math, json, statistics, traceback
from pathlib import Path
from datetime import date, datetime
import pandas as pd
from docx import Document
from docx.shared import Pt
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QTabWidget,QPushButton,QLabel,QTableWidget,QTableWidgetItem,QFileDialog,QMessageBox,QFormLayout,QDoubleSpinBox,QSpinBox,QLineEdit,QTextEdit,QComboBox,QHeaderView,QGroupBox,QProgressBar)

# Industry constituents are editable candidate peer lists, not verified comparability assertions.
INDUSTRIES = {
    "Automotive & Auto Components": ["MOTHERSON.NS", "BHARATFORG.NS", "BOSCHLTD.NS", "EXIDEIND.NS"],
    "Automotive Lubricants": ["CASTROLIND.NS", "GULFOILLUB.NS", "TIDEWATER.NS"],
    "Chemicals": ["PIDILITIND.NS", "SRF.NS", "DEEPAKNTR.NS", "AARTIIND.NS"],
    "Cement": ["ULTRACEMCO.NS", "AMBUJACEM.NS", "SHREECEM.NS", "ACC.NS"],
    "Consumer Durables": ["VOLTAS.NS", "BLUESTARCO.NS", "CROMPTON.NS", "HAVELLS.NS"],
    "FMCG": ["HINDUNILVR.NS", "DABUR.NS", "MARICO.NS", "GODREJCP.NS"],
    "IT Services": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS"],
    "Logistics": ["BLUEDART.NS", "DELHIVERY.NS", "TCI.NS"],
    "Metals & Steel": ["TATASTEEL.NS", "JSWSTEEL.NS", "SAIL.NS", "JINDALSTEL.NS"],
    "Paints": ["ASIANPAINT.NS", "BERGEPAINT.NS", "KANSAINER.NS"],
    "Pharmaceuticals": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "LUPIN.NS"],
    "Retail": ["TRENT.NS", "ABFRL.NS", "DMART.NS"],
    "Textiles": ["VTL.NS", "KPRMILL.NS", "TRIDENT.NS"],
    "Tyres": ["MRF.NS", "APOLLOTYRE.NS", "CEATLTD.NS", "JKTYRE.NS"],
    "Other / Custom": []
}
# Industries like banks and insurers require sector-specific methods; they are excluded.
COMPANY_HINTS = {
    "castrol": "Automotive Lubricants", "gulf oil": "Automotive Lubricants",
    "motul": "Automotive Lubricants", "tide water": "Automotive Lubricants",
    "asian paints": "Paints", "berger paints": "Paints", "infosys": "IT Services",
    "tata consultancy": "IT Services", "sun pharma": "Pharmaceuticals",
    "ultratech": "Cement", "hindustan unilever": "FMCG",
}

def company_from_file(path):
    """Only use explicit workbook metadata, not debtor/customer names."""
    try:
        if Path(path).suffix.lower() not in ('.xlsx', '.xlsm'): return None
        from openpyxl import load_workbook
        wb=load_workbook(path,read_only=True,data_only=True)
        # Dedicated Metadata sheet is the only automatic source accepted.
        for sheet in wb:
            if sheet.title.lower() not in ('metadata','company info','company details'):continue
            for row in sheet.iter_rows(min_row=1,max_row=30,max_col=2,values_only=True):
                if row[0] and str(row[0]).strip().lower() in ('company','company name','reporting company','entity name'):
                    return str(row[1]).strip() if row[1] else None
    except Exception: pass
    return None

def choose_industry(company):
    name=(company or '').lower()
    return next((industry for hint,industry in COMPANY_HINTS.items() if hint in name),None)

def field_series(df, names):
    if df is None or df.empty: return None, 'statement empty'
    norm=lambda x:re.sub('[^a-z0-9]','',str(x).lower())
    labels={norm(k):k for k in df.index}
    for name in names:
        if norm(name) in labels:
            label=labels[norm(name)]
            series=pd.to_numeric(df.loc[label],errors='coerce')
            if isinstance(series,pd.DataFrame):series=series.iloc[0]
            return {pd.Timestamp(k):float(v) for k,v in series.items() if pd.notna(v)},str(label)
    return None,'missing; fields: '+', '.join(map(str,list(df.index)[:15]))

def benchmark_ticker(ticker):
    import yfinance as yf
    obj=yf.Ticker(ticker)
    errors=[];inc=bal=None
    for name,getter in [('getters',lambda:(obj.get_income_stmt(freq='yearly'),obj.get_balance_sheet(freq='yearly'))),('properties',lambda:(obj.income_stmt,obj.balance_sheet))]:
        try:
            inc,bal=getter()
            if inc is not None and bal is not None and not inc.empty and not bal.empty:break
            errors.append(name+': empty statements')
        except Exception as exc:errors.append(name+': '+type(exc).__name__+': '+str(exc)[:150])
    if inc is None or bal is None or inc.empty or bal.empty:raise ValueError('; '.join(errors))
    rev,rl=field_series(inc,['Total Revenue','Operating Revenue','Revenue'])
    cogs,cl=field_series(inc,['Cost Of Revenue','Cost Of Goods Sold'])
    ar,al=field_series(bal,['Accounts Receivable','Net Receivables','Receivables','Accounts Notes And Other Receivables'])
    ap,pl=field_series(bal,['Accounts Payable','Payables','Current Accounts Payable','Payables And Accrued Expenses'])
    years=sorted(set(rev or {})|set(cogs or {}),reverse=True)
    for year in years:
        previous=sorted((d for d in set(ar or {})|set(ap or {}) if 300<=(year-d).days<=430),reverse=True)
        if not previous:continue
        prior=previous[0]
        dso=365*(ar[year]+ar[prior])/2/rev[year] if ar and rev and year in ar and prior in ar and year in rev and rev[year]>0 else None
        dpo=365*(ap[year]+ap[prior])/2/abs(cogs[year]) if ap and cogs and year in ap and prior in ap and year in cogs and cogs[year] else None
        if dso is not None or dpo is not None:
            return {'ticker':ticker,'dso':dso,'dpo':dpo,'year':year.date().isoformat(),
              'method':'DSO = avg receivables / revenue ×365; DPO = avg payables / cost of revenue ×365. Both are proxies.',
              'source':f'https://finance.yahoo.com/quote/{ticker}/financials/',
              'labels':f'Revenue: {rl}; COGS: {cl}; AR: {al}; AP: {pl}'}
    raise ValueError('No compatible fiscal-year and prior-year balances; '+f'Revenue: {rl}; COGS: {cl}; AR: {al}; AP: {pl}')

CACHE_PATH=Path.home()/'.financeos_peer_cache.json'
class PeerWorker(QThread):
    completed=pyqtSignal(object,object)
    def __init__(self,tickers):super().__init__();self.tickers=tickers
    def run(self):
        try:cache=json.loads(CACHE_PATH.read_text())
        except (OSError,ValueError):cache={}
        data=[];errors=[]
        for ticker in self.tickers:
            try:
                result=benchmark_ticker(ticker)
                result.update(retrieved_at=datetime.now().isoformat(timespec='seconds'),cached=False)
                cache[ticker]=result;data.append(result)
            except Exception as exc:
                errors.append(f'{ticker}: {type(exc).__name__}: {str(exc)[:500]}')
                if ticker in cache:
                    old=dict(cache[ticker]);old['cached']=True;data.append(old)
        try:CACHE_PATH.write_text(json.dumps(cache,indent=2))
        except OSError:pass
        self.completed.emit(data,errors)

ALIASES={
 'party':['party','party name','customer','customer name','debtor','debtor name','vendor','vendor name','supplier','supplier name','account name'],
 'invoice':['invoice','invoice no','invoice number','bill no','bill number','document number','document no','voucher no'],
 'date':['invoice date','bill date','document date','posting date','date'],
 'amount':['outstanding','outstanding amount','outstanding balance','balance','balance amount','amount due','pending amount','net outstanding']}

def parse_report(path):
    p=Path(path)
    if p.suffix.lower()=='.csv':
        try: df=pd.read_csv(p,encoding='utf-8-sig')
        except UnicodeDecodeError: df=pd.read_csv(p,encoding='cp1252')
    else: df=pd.read_excel(p)
    cols={re.sub(r'\s+',' ',str(c).strip().lower()):c for c in df.columns}
    found={}
    for key,opts in ALIASES.items():
        for opt in opts:
            if opt in cols: found[key]=cols[opt];break
    missing=[k for k in ALIASES if k not in found]
    if missing: raise ValueError('Missing columns: '+', '.join(missing)+'\nFound: '+', '.join(map(str,df.columns)))
    out=pd.DataFrame({k:df[v] for k,v in found.items()})
    out['party']=out['party'].fillna('').astype(str).str.strip()
    out['invoice']=out['invoice'].fillna('').astype(str).str.strip()
    out['date']=pd.to_datetime(out['date'],errors='coerce',dayfirst=True)
    out['amount']=pd.to_numeric(out['amount'].astype(str).str.replace(',','',regex=False).str.replace('₹','',regex=False).str.replace(r'\((.*?)\)',r'-\1',regex=True),errors='coerce')
    invalid=out['date'].isna()|out['amount'].isna()|(out['party']=='')|(out['invoice']=='')
    if invalid.any(): raise ValueError(f'{invalid.sum()} rows have missing/invalid party, invoice, date or amount. Correct the source and reimport.')
    if out['amount'].lt(0).any(): raise ValueError('Negative outstanding balances found. Resolve credit notes/advances separately before importing.')
    out=out[out['amount']>0].copy()
    if out.duplicated(['party','invoice']).any(): raise ValueError('Duplicate party/invoice pairs found. Aggregate or reconcile them before importing.')
    return out.reset_index(drop=True)

def calculate(sales,purchases,open_ar,close_ar,open_ap,close_ap,days=365):
    avar=(open_ar+close_ar)/2; avap=(open_ap+close_ap)/2
    ar_turn=sales/avar if avar>0 and sales>0 else None
    ap_turn=purchases/avap if avap>0 and purchases>0 else None
    return {'Debtor turnover':ar_turn,'Creditor turnover':ap_turn,'DSO (days)':days/ar_turn if ar_turn else None,'DPO (days)':days/ap_turn if ap_turn else None}

def age_data(df,asof):
    result=df.copy()
    result['days']=(pd.Timestamp(asof)-result['date']).dt.days
    if result['days'].lt(0).any(): raise ValueError('Some invoices are dated after the selected as-of date.')
    result['bucket']=pd.cut(result['days'],bins=[-1,30,60,90,180,365,float('inf')],labels=['0–30','31–60','61–90','91–180','181–365','>365'])
    return result

def safe_filename(value): return re.sub(r'[^A-Za-z0-9_-]+','_',value).strip('_')[:70] or 'Debtor'

def create_letter(party,rows,destination,company,asof):
    doc=Document(); sec=doc.sections[0]; sec.header.paragraphs[0].text=company
    doc.add_heading('Outstanding Payment Reminder',0)
    doc.add_paragraph(f'Date: {date.today():%d %B %Y}')
    doc.add_paragraph(f'To: {party}')
    doc.add_paragraph('Subject: Request for settlement of outstanding invoices')
    doc.add_paragraph('Dear Accounts Team,')
    doc.add_paragraph(f'As per our records as of {asof:%d %B %Y}, the following invoices remain outstanding. We request you to review these balances and arrange settlement at the earliest.')
    table=doc.add_table(rows=1,cols=4);table.style='Table Grid'
    for cell,head in zip(table.rows[0].cells,['Invoice','Invoice date','Age (days)','Outstanding (INR)']):cell.text=head
    for _,r in rows.iterrows():
        cells=table.add_row().cells
        for c,v in zip(cells,[str(r['invoice']),r['date'].strftime('%d-%b-%Y'),str(int(r['days'])),f"{r['amount']:,.2f}"]):c.text=v
    doc.add_paragraph(f"Total outstanding listed: INR {rows['amount'].sum():,.2f}")
    doc.add_paragraph('If payment has already been made, or if any invoice is disputed, please share the payment details or discrepancy so that our records can be reconciled. Kindly confirm the expected payment date.')
    doc.add_paragraph(f'Regards,\nAccounts Receivable Department\n{company}')
    doc.add_paragraph('Draft for internal review — not sent.')
    doc.styles['Normal'].font.size=Pt(10)
    doc.save(destination)

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('FinanceOS Pro | Working Capital Intelligence');self.resize(1150,760)
        self.reports={'Debtors':None,'Creditors':None};self.paths={};self.metrics={};self.peers=[];self.online_peers=[];self.worker=None
        self.tabs=QTabWidget();self.setCentralWidget(self.tabs)
        self.build_import();self.build_ratios();self.build_aging();self.build_peers();self.build_letters()
        self.setStyleSheet('QMainWindow,QWidget{background:#f5f7fb;color:#18243a;font-family:Arial;font-size:13px}QPushButton{background:#164b86;color:white;border-radius:7px;padding:9px 14px}QPushButton:hover{background:#2467ad}QTabBar::tab{padding:12px 16px;background:#e5ebf4}QTabBar::tab:selected{background:#164b86;color:white}QTableWidget{background:white;gridline-color:#dce3ed}QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox,QTextEdit{background:white;border:1px solid #cdd7e5;border-radius:5px;padding:5px}QGroupBox{font-weight:bold;border:1px solid #d4deeb;border-radius:8px;margin-top:10px;padding:10px}')
    def add_tab(self,name):
        w=QWidget();layout=QVBoxLayout(w);layout.setSpacing(12);self.tabs.addTab(w,name);return layout
    def build_import(self):
        l=self.add_tab('Import Reports');l.addWidget(QLabel('Import invoice-level aging reports (.xlsx or .csv). All amounts must be in INR.'))
        for kind in ('Debtors','Creditors'):
            row=QHBoxLayout();b=QPushButton('Import '+kind);b.clicked.connect(lambda _,k=kind:self.import_file(k));row.addWidget(b)
            label=QLabel('No file loaded');setattr(self,'status_'+kind,label);row.addWidget(label,1);l.addLayout(row)
        l.addWidget(QLabel('Required columns: Party Name, Invoice No, Invoice Date, Outstanding.\nInvoice date determines aging; negative balances and duplicate invoice keys are flagged.'))
        l.addStretch()
    def import_file(self,kind):
        path,_=QFileDialog.getOpenFileName(self,'Select '+kind+' report','','Excel/CSV (*.xlsx *.csv)')
        if not path:return
        try:
            df=parse_report(path);self.reports[kind]=df;self.paths[kind]=path
            getattr(self,'status_'+kind).setText(f'{Path(path).name} | {len(df)} invoices | INR {df.amount.sum():,.2f}')
            detected=company_from_file(path)
            if detected and hasattr(self,'company_input'):
                self.company_input.setText(detected)
                industry=choose_industry(detected)
                if industry:self.industry_combo.setCurrentText(industry)
            self.refresh_aging();self.refresh_letters()
        except Exception as e:QMessageBox.critical(self,'Import validation',str(e))
    def build_ratios(self):
        l=self.add_tab('Turnover & Ratios');form=QFormLayout();self.inputs={}
        for key in ['Net credit sales','Net credit purchases','Opening receivables','Closing receivables','Opening payables','Closing payables']:
            sp=QDoubleSpinBox();sp.setRange(0,1e15);sp.setDecimals(2);sp.setGroupSeparatorShown(True);sp.setPrefix('₹ ');self.inputs[key]=sp;form.addRow(key,sp)
        self.period=QSpinBox();self.period.setRange(1,366);self.period.setValue(365);form.addRow('Reporting period (days)',self.period);l.addLayout(form)
        b=QPushButton('Calculate ratios');b.clicked.connect(self.compute);l.addWidget(b)
        self.ratio_output=QTextEdit();self.ratio_output.setReadOnly(True);l.addWidget(self.ratio_output)
    def compute(self):
        v=[self.inputs[k].value() for k in self.inputs];self.metrics=calculate(*v,self.period.value())
        lines=[]
        for k,n in self.metrics.items():lines.append(f'{k}: {n:.2f}'+(' days' if 'days' in k else ' times') if n is not None else f'{k}: N/A (missing/zero denominator)')
        lines.append('\nInterpretation: Higher turnover generally means faster collection/payment. Higher DSO/DPO means slower collection/payment.')
        for k,n in self.metrics.items():
            if n is not None and 'DSO' in k and n>90:lines.append('Review credit terms, overdue customer concentrations, disputes and unapplied receipts.')
            if n is not None and 'DPO' in k and n>90:lines.append('Review supplier payment terms, overdue balances and treasury constraints.')
        self.ratio_output.setPlainText('\n'.join(lines));self.refresh_benchmarks()
    def asof(self):return date.fromisoformat(self.asof_edit.text().strip())
    def build_aging(self):
        l=self.add_tab('Aging Analysis');r=QHBoxLayout();r.addWidget(QLabel('As-of date (YYYY-MM-DD):'));self.asof_edit=QLineEdit(date.today().isoformat());r.addWidget(self.asof_edit)
        b=QPushButton('Refresh aging');b.clicked.connect(self.refresh_aging);r.addWidget(b);l.addLayout(r)
        self.aging_summary=QLabel('Import reports to see aging.');l.addWidget(self.aging_summary)
        self.aging_table=QTableWidget();self.aging_table.setColumnCount(6);self.aging_table.setHorizontalHeaderLabels(['Type','Party','Invoice','Invoice date','Age (days)','Outstanding (INR)']);self.aging_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);l.addWidget(self.aging_table)
    def refresh_aging(self):
        try:
            asof=self.asof();allrows=[];summary=[]
            for kind,df in self.reports.items():
                if df is None:continue
                aged=age_data(df,asof);summary.append(f'{kind}: INR {aged.amount.sum():,.2f} total | 180+ days: INR {aged.loc[aged.days>=180,"amount"].sum():,.2f}')
                for _,r in aged.sort_values('days',ascending=False).iterrows():allrows.append([kind,str(r.party),str(r.invoice),r.date.strftime('%Y-%m-%d'),str(int(r.days)),f'{r.amount:,.2f}'])
            self.aging_summary.setText('     |     '.join(summary) if summary else 'Import reports to see aging.')
            self.aging_table.setRowCount(len(allrows))
            for i,row in enumerate(allrows):
                for j,val in enumerate(row):self.aging_table.setItem(i,j,QTableWidgetItem(val))
            if hasattr(self,'letter_table'):self.refresh_letters()
        except Exception as e:QMessageBox.warning(self,'Aging error',str(e))
    def build_peers(self):
        l=self.add_tab('Peer Benchmarks')
        l.addWidget(QLabel('Online peer analysis: financial statement PROXIES; no customer data is uploaded.'))
        form=QFormLayout()
        self.company_input=QLineEdit();self.company_input.setPlaceholderText('Optional: reporting company (e.g., Castrol India)')
        form.addRow('Reporting company',self.company_input)
        self.company_input.editingFinished.connect(self.auto_industry)
        self.industry_combo=QComboBox();self.industry_combo.addItems(sorted(INDUSTRIES))
        form.addRow('Industry',self.industry_combo)
        self.tickers_input=QLineEdit();self.tickers_input.setPlaceholderText('Optional override: CASTROLIND.NS, GULFOILLUB.NS')
        form.addRow('Peer tickers (optional)',self.tickers_input)
        l.addLayout(form)
        row=QHBoxLayout()
        self.auto_btn=QPushButton('Detect industry from company');self.auto_btn.clicked.connect(self.auto_industry)
        self.fetch_btn=QPushButton('Fetch online peer financials');self.fetch_btn.clicked.connect(self.fetch_peers)
        row.addWidget(self.auto_btn);row.addWidget(self.fetch_btn);l.addLayout(row)
        self.peer_status=QLabel('Select an industry, then fetch. Internet required.');l.addWidget(self.peer_status)
        self.peer_table=QTableWidget(0,6)
        self.peer_table.setHorizontalHeaderLabels(['Peer ticker','DSO (days)','DPO (days)','FY end','Retrieved','Data source'])
        self.peer_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        l.addWidget(self.peer_table)
        self.peer_output=QTextEdit();self.peer_output.setReadOnly(True);l.addWidget(self.peer_output)
        l.addWidget(QLabel('Important: figures use annual revenue/COGS proxies; compare only similar business models and periods.'))

    def auto_industry(self):
        company=self.company_input.text().strip()
        industry=choose_industry(company)
        if industry:
            self.industry_combo.setCurrentText(industry)
            self.peer_status.setText(f'Suggested industry: {industry}. Confirm before fetching.')
        elif company:
            self.peer_status.setText('Industry could not be reliably inferred. Select it manually.')

    def fetch_peers(self):
        raw=self.tickers_input.text().strip()
        tickers=[x.strip().upper() for x in raw.split(',') if x.strip()] if raw else INDUSTRIES[self.industry_combo.currentText()]
        tickers=list(dict.fromkeys(tickers))
        if not tickers:
            QMessageBox.warning(self,'No peer universe','Select an industry with candidate peers or enter tickers.');return
        self.peer_status.setText('Downloading annual statements for '+', '.join(tickers)+' ...')
        self.fetch_btn.setEnabled(False)
        self.worker=PeerWorker(tickers)
        self.worker.completed.connect(self.peers_ready)
        self.worker.start()

    def peers_ready(self,data,errors):
        self.online_peers=data
        self.fetch_btn.setEnabled(True)
        self.peer_table.setRowCount(len(data))
        for i,p in enumerate(data):
            vals=[p['ticker'],f"{p['dso']:.1f}" if p['dso'] is not None else 'Unavailable',
                  f"{p['dpo']:.1f}" if p['dpo'] is not None else 'Unavailable',p['year'],('CACHED ' if p.get('cached') else '')+p.get('retrieved_at','unknown'),p['source']]
            for j,val in enumerate(vals):self.peer_table.setItem(i,j,QTableWidgetItem(val))
        self.peer_status.setText(f'{len(data)} peer datasets available; {len(errors)} retrieval errors. See diagnostics below.')
        self.fetch_errors=errors
        self.refresh_benchmarks()

    def refresh_benchmarks(self):
        if not hasattr(self,'peer_output'):return
        if not self.online_peers:
            self.peer_output.setPlainText('No online peer data retrieved.\n\nDiagnostics:\n'+'\n'.join(getattr(self,'fetch_errors',[])));return
        lines=['ONLINE PEER BENCHMARKS — ANNUAL FINANCIAL STATEMENT PROXIES',
               'DSO = avg trade receivables / total revenue × 365',
               'DPO = avg trade payables / cost of revenue × 365',
               'These are NOT verified credit-sales/credit-purchases turnover ratios.','']
        for p in self.online_peers:
            ds=f"{p['dso']:.1f}" if p['dso'] is not None else 'N/A'
            dp=f"{p['dpo']:.1f}" if p['dpo'] is not None else 'N/A'
            lines.extend([f"{p['ticker']} | FY {p['year']} | DSO {ds} | DPO {dp}",f"Source: {p['source']}",f"Retrieved: {p.get('retrieved_at','unknown')} {'(CACHED)' if p.get('cached') else ''}",f"Fields: {p.get('labels','unknown')}"])
        for name,key in [('DSO','dso'),('DPO','dpo')]:
            vals=[p[key] for p in self.online_peers if p[key] is not None]
            if len(vals)<2:
                lines.append(f'\n{name} benchmark unavailable: fewer than two valid peer observations.')
                continue
            median=statistics.median(vals)
            lines.append(f'\nPeer median {name}: {median:.1f} days (n={len(vals)})')
            own=self.metrics.get(f'{name} (days)')
            if own is None:
                lines.append('Enter own-company ratio inputs in Turnover & Ratios to compare.')
            else:
                diff=own-median
                lines.append(f'Own {name}: {own:.1f} days; gap: {diff:+.1f} days')
                if diff>15:
                    lines.append(('Potential collection issues: aging concentration, longer credit terms, disputed invoices.' if name=='DSO' else 'Potential supplier issues: negotiated terms, delayed payments, liquidity pressure.')+' Verify against invoice-level data.')
                elif diff< -15:
                    lines.append('Below peer median: review contractual terms and business mix; not automatically good or bad.')
                else:lines.append('Within ±15 days of this selected peer median.')
        if getattr(self,'fetch_errors',[]):
            lines.append('\nDetailed retrieval errors:')
            lines.extend(self.fetch_errors)
        lines.append('\nData provider: Yahoo Finance via yfinance. Cached values are marked; figures are unverified provider extractions. Confirm against annual reports before external reporting.')
        self.peer_output.setPlainText('\n'.join(lines))

    def build_letters(self):
        l=self.add_tab('Collection Letters');form=QFormLayout();self.company=QLineEdit('Your Company');form.addRow('Company name',self.company)
        self.threshold=QSpinBox();self.threshold.setRange(1,3650);self.threshold.setValue(180);self.threshold.valueChanged.connect(self.refresh_letters);form.addRow('Invoice age threshold (days)',self.threshold);l.addLayout(form)
        self.letter_table=QTableWidget();self.letter_table.setColumnCount(3);self.letter_table.setHorizontalHeaderLabels(['Debtor','Eligible invoices','Amount (INR)']);self.letter_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);l.addWidget(self.letter_table)
        b=QPushButton('Generate Word drafts for review');b.clicked.connect(self.generate_letters);l.addWidget(b);l.addWidget(QLabel('Letters are saved locally and never sent automatically. Verify balances and disputes before issuing.'))
    def eligible(self):
        df=self.reports['Debtors'];return age_data(df,self.asof()).loc[lambda x: x['days'] >= self.threshold.value()] if df is not None else pd.DataFrame()
    def refresh_letters(self):
        if not hasattr(self,'letter_table'):return
        try:
            eligible=self.eligible();grouped=eligible.groupby('party').agg(invoices=('invoice','count'),amount=('amount','sum')).reset_index() if not eligible.empty else pd.DataFrame(columns=['party','invoices','amount'])
            self.letter_table.setRowCount(len(grouped))
            for i,r in grouped.iterrows():
                for j,val in enumerate([r.party,str(int(r.invoices)),f'{r.amount:,.2f}']):self.letter_table.setItem(i,j,QTableWidgetItem(val))
        except Exception:pass
    def generate_letters(self):
        try:
            eligible=self.eligible()
            if eligible.empty:QMessageBox.information(self,'Letters','No eligible invoices.');return
            folder=QFileDialog.getExistingDirectory(self,'Choose output folder')
            if not folder:return
            count=0
            for i,(party,rows) in enumerate(eligible.groupby('party'),1):
                dest=Path(folder)/f'{i:03d}_{safe_filename(party)}_Reminder.docx'
                create_letter(party,rows,dest,self.company.text().strip() or 'Company',self.asof());count+=1
            QMessageBox.information(self,'Drafts generated',f'{count} Word drafts saved in:\n{folder}\nReview before sending.')
        except Exception as e:QMessageBox.critical(self,'Generation error',str(e))

if __name__=='__main__':
    app=QApplication(sys.argv);window=Window();window.show();sys.exit(app.exec())
