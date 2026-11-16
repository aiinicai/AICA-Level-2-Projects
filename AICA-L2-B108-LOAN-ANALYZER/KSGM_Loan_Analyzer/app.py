import csv
import io
import json
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
import webbrowser
from engine import CATEGORIES, normalize, analyze, money, parse_date

TITLE = 'KSGM and company loan analyzer'
BASE = 'https://generativelanguage.googleapis.com/v1beta/'

def api(key, endpoint, payload=None):
    req = Request(BASE+endpoint, data=None if payload is None else json.dumps(payload).encode(),
                  headers={'x-goog-api-key':key,'Content-Type':'application/json'})
    try:
        with urlopen(req, timeout=90) as resp: return json.load(resp)
    except HTTPError as exc:
        # Do not include request headers or secret in error output.
        raise ValueError(f'Gemini HTTP {exc.code}. Check key, model access, quota and billing.') from None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITLE); self.geometry('1260x850'); self.minsize(1000,700)
        self.configure(bg='#eef3fa'); self.rows=[]; self.raw=[]; self.result=None; self.events=queue.Queue()
        style=ttk.Style(self); style.theme_use('clam')
        style.configure('.',font=('Segoe UI',10),background='#eef3fa',foreground='#172c48')
        style.configure('TButton',padding=9,background='#dfe9f7')
        style.configure('Accent.TButton',background='#127c89',foreground='white',font=('Segoe UI',10,'bold'))
        style.configure('TNotebook.Tab',padding=(18,10))
        style.configure('Treeview',rowheight=28,background='white',fieldbackground='white')
        style.configure('Treeview.Heading',background='#dae6f5',font=('Segoe UI',10,'bold'))
        header=tk.Frame(self,bg='#122c4e',padx=24,pady=18);header.pack(fill='x')
        tk.Label(header,text=TITLE,bg='#122c4e',fg='white',font=('Segoe UI',23,'bold')).pack(anchor='w')
        tk.Label(header,text='BANK CHARGES  /  DAILY LOAN INTEREST  /  GEMINI REVIEW',bg='#122c4e',fg='#7edbd3',font=('Segoe UI',10)).pack(anchor='w',pady=(5,0))
        self.tabs=ttk.Notebook(self);self.tabs.pack(fill='both',expand=True,padx=18,pady=14)
        self.import_tab=self.tab('1  Import & review');self.calc_tab=self.tab('2  Loan analysis');self.ai_tab=self.tab('3  Gemini assistant')
        self.build_import();self.build_calc();self.build_ai()
        self.status=tk.StringVar(value='Ready • Load a statement or try the included sample.')
        ttk.Label(self,textvariable=self.status,padding=(20,8)).pack(fill='x')
        self.after(100,self.poll)

    def tab(self,name):
        frame=ttk.Frame(self.tabs,padding=14);self.tabs.add(frame,text=name);return frame
    def button(self,parent,text,fn,accent=False):
        b=ttk.Button(parent,text=text,command=fn,style='Accent.TButton' if accent else 'TButton');b.pack(side='left',padx=(0,8));return b
    def field(self,parent,label,value,width=18):
        frame=ttk.Frame(parent);frame.pack(side='left',padx=(0,15),pady=6)
        ttk.Label(frame,text=label).pack(anchor='w');v=tk.StringVar(value=value)
        ttk.Entry(frame,textvariable=v,width=width).pack();return v
    def table(self,parent,cols):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True,pady=8)
        tree=ttk.Treeview(frame,columns=cols,show='headings',selectmode='browse')
        y=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);x=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview)
        tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        tree.grid(row=0,column=0,sticky='nsew');y.grid(row=0,column=1,sticky='ns');x.grid(row=1,column=0,sticky='ew')
        frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        for c in cols: tree.heading(c,text=c);tree.column(c,width=120,stretch=True)
        return tree
    def build_import(self):
        bar=ttk.Frame(self.import_tab);bar.pack(fill='x')
        self.button(bar,'Load CSV / Excel / PDF',self.load,True)
        self.button(bar,'Try sample',lambda:self.load_path(Path(__file__).with_name('sample_statement.csv')))
        self.header_row=self.field(bar,'Header row (1-based)','1',5)
        ttk.Label(self.import_tab,text='PDF: text-based tables only. Export scanned statements to CSV/Excel first. Excel: first worksheet.').pack(anchor='w',pady=6)
        options=ttk.Frame(self.import_tab);options.pack(fill='x')
        self.dayfirst=tk.BooleanVar(value=True);ttk.Checkbutton(options,text='Day-first dates (DD/MM/YYYY)',variable=self.dayfirst).pack(side='left')
        self.balance_mode=tk.StringVar(value='Positive outstanding')
        ttk.Label(options,text='Balance convention:').pack(side='left',padx=12)
        ttk.Combobox(options,textvariable=self.balance_mode,values=['Positive outstanding','Negative bank balance','DR/CR suffix'],state='readonly',width=24).pack(side='left')
        self.mapping_frame=ttk.Frame(self.import_tab);self.mapping_frame.pack(fill='x',pady=8);self.maps={}
        for label in ['Date','Description','Debit','Credit','Balance']:
            f=ttk.Frame(self.mapping_frame);f.pack(side='left',padx=(0,10))
            ttk.Label(f,text=label).pack(anchor='w');v=tk.StringVar();box=ttk.Combobox(f,textvariable=v,state='readonly',width=18);box.pack();self.maps[label]=(v,box)
        bar=ttk.Frame(self.import_tab);bar.pack(fill='x')
        self.button(bar,'Apply column mapping',self.apply_mapping,True)
        self.button(bar,'Change selected category',self.reclassify)
        ttk.Label(bar,text='Review candidates: narration matching is only a starting point.').pack(side='left')
        self.tree=self.table(self.import_tab,['Row','Date','Description','Debit','Credit','Outstanding','Category'])
        self.tree.column('Description',width=340)
        self.import_notes=tk.Text(self.import_tab,height=4,wrap='word',font=('Segoe UI',10));self.import_notes.pack(fill='x')

    def load(self):
        p=filedialog.askopenfilename(filetypes=[('Statements','*.csv *.xlsx *.xls *.pdf'),('All files','*.*')])
        if p:self.load_path(Path(p))
    def load_path(self,p):
        try:
            h=int(self.header_row.get())-1
            if h<0:raise ValueError('Header row must be 1 or higher')
            if p.suffix.lower()=='.csv':
                try:text=p.read_text(encoding='utf-8-sig')
                except UnicodeDecodeError:text=p.read_text(encoding='cp1252')
                try:dialect=csv.Sniffer().sniff(text[:8192],delimiters=',;\t')
                except csv.Error:dialect=csv.excel
                grid=list(csv.reader(io.StringIO(text),dialect))
            elif p.suffix.lower() in ('.xlsx','.xls'):
                import pandas as pd
                grid=pd.read_excel(p,header=None).fillna('').values.tolist()
            elif p.suffix.lower()=='.pdf':
                import pdfplumber
                grid=[]
                with pdfplumber.open(p) as doc:
                    for page in doc.pages:
                        for table in page.extract_tables():grid.extend(table)
                if not grid:raise ValueError('No readable PDF table found. Use the bank CSV/Excel export; scanned PDFs need OCR first.')
            else:raise ValueError('Use CSV, XLSX, XLS or text-based PDF')
            if len(grid)<=h+1:raise ValueError('No transactions below selected header row')
            headers=[str(x or '').replace('\n',' ').strip() or f'Column {i+1}' for i,x in enumerate(grid[h])]
            if len(set(headers))!=len(headers):raise ValueError('Duplicate headers. Choose the correct header row or rename columns in the source file.')
            self.raw=[dict(zip(headers,(list(row)+['']*len(headers))[:len(headers)])) for row in grid[h+1:] if list(row)!=list(grid[h])]
            aliases={'Date':['value date','transaction date','txn date','date'],'Description':['narration','description','particulars','remarks'],'Debit':['debit','withdrawal','withdrawals','debit amount'],'Credit':['credit','deposit','deposits','credit amount'],'Balance':['balance','closing balance','outstanding','running balance']}
            for name,(v,box) in self.maps.items():
                box['values']=['']+headers
                match=next((x for a in aliases[name] for x in headers if x.lower()==a),None)
                if match is None:match=next((x for x in headers if any(a in x.lower() for a in aliases[name])), '')
                v.set(match)
            self.rows=[];self.result=None;self.clear_result();self.tree.delete(*self.tree.get_children())
            self.status.set(f'Loaded {p.name} • {len(self.raw)} source rows. Confirm mapping, then Apply.')
            self.import_notes.delete('1.0','end');self.import_notes.insert('end','First source rows:\n'+ '\n'.join(str(r) for r in self.raw[:3]))
        except ImportError as exc:messagebox.showerror('Missing dependency',f'{exc}\nRun Install_and_Run.bat first.')
        except Exception as exc:messagebox.showerror('Import problem',str(exc))
    def apply_mapping(self):
        try:
            if not self.raw:raise ValueError('Load a statement first')
            mapping={k:v.get() for k,(v,b) in self.maps.items()}
            if not mapping['Date'] or not mapping['Description'] or not (mapping['Debit'] or mapping['Credit']):raise ValueError('Map Date, Description and at least Debit or Credit. Separate debit/credit columns are required.')
            used=[x for x in mapping.values() if x]
            if len(set(used))!=len(used):raise ValueError('Each mapped field needs a different source column')
            rows,errors=normalize(self.raw,mapping,self.dayfirst.get(),self.balance_mode.get())
            self.import_notes.delete('1.0','end');self.import_notes.insert('end','\n'.join(errors) if errors else 'All rows parsed. Confirm statement is complete and in chronological order within each date. Review all detected categories.')
            if errors:raise ValueError(f'{len(errors)} row(s) could not be parsed. Analysis blocked: correct source/mapping. Details below the table.')
            if not rows:raise ValueError('No transaction rows found')
            self.rows=rows;self.result=None;self.clear_result();self.refresh_rows()
            self.start.set(min(r['date'] for r in rows).isoformat());self.end.set(max(r['date'] for r in rows).isoformat())
            self.status.set(f'{len(rows)} transactions ready • Set period, opening balance and contractual rate.')
        except Exception as exc:
            self.rows=[];self.result=None;self.clear_result();self.tree.delete(*self.tree.get_children());messagebox.showerror('Mapping problem',str(exc))
    def refresh_rows(self):
        self.tree.delete(*self.tree.get_children())
        for i,r in enumerate(self.rows):
            self.tree.insert('', 'end',iid=str(i),values=[r['source'],r['date'],r['description'],f"{r['debit']:.2f}",f"{r['credit']:.2f}",'' if r['balance'] is None else f"{r['balance']:.2f}",r['category']])
    def reclassify(self):
        sel=self.tree.selection()
        if not sel:return
        i=int(sel[0]);win=tk.Toplevel(self);win.title('Review transaction category');win.geometry('420x180')
        ttk.Label(win,text=self.rows[i]['description'],wraplength=390,padding=12).pack()
        v=tk.StringVar(value=self.rows[i]['category']);ttk.Combobox(win,textvariable=v,values=CATEGORIES,state='readonly',width=28).pack()
        def save():
            self.rows[i]['category']=v.get();self.result=None;self.clear_result();self.refresh_rows();win.destroy()
        ttk.Button(win,text='Save category',command=save).pack(pady=12)

    def build_calc(self):
        bar=ttk.Frame(self.calc_tab);bar.pack(fill='x')
        self.start=self.field(bar,'From (YYYY-MM-DD)',date.today().replace(day=1).isoformat(),14)
        self.end=self.field(bar,'To (inclusive)',date.today().isoformat(),14)
        self.opening=self.field(bar,'Opening loan outstanding','100000',20)
        self.rate=self.field(bar,'Annual rate (%)','12',12)
        bar=ttk.Frame(self.calc_tab);bar.pack(fill='x')
        self.mode=tk.StringVar(value='Daily closing balance');self.basis=tk.StringVar(value='Actual/365')
        ttk.Combobox(bar,textvariable=self.mode,values=['Daily closing balance','Fixed principal'],state='readonly',width=24).pack(side='left',padx=(0,12))
        ttk.Combobox(bar,textvariable=self.basis,values=['Actual/365','Actual/360','Actual/Actual'],state='readonly',width=18).pack(side='left')
        self.button(bar,'Calculate',self.calculate,True);self.button(bar,'Export Excel report',self.export)
        ttk.Label(self.calc_tab,text='Rate changes (optional): one YYYY-MM-DD,annual_rate per line. Effective from that date.').pack(anchor='w',pady=(12,3))
        self.changes=tk.Text(self.calc_tab,height=2,font=('Consolas',10));self.changes.pack(fill='x')
        ttk.Label(self.calc_tab,text='Opening = outstanding immediately before From date. Same-day rows must follow statement order. End-of-day balances apply to that day; both endpoints count.',wraplength=1100).pack(anchor='w',pady=6)
        self.cards=tk.StringVar(value='Calculate to see expected interest and bank costs.')
        tk.Label(self.calc_tab,textvariable=self.cards,bg='#127c89',fg='white',font=('Segoe UI',13,'bold'),padx=18,pady=16,justify='left').pack(fill='x',pady=8)
        self.daily_tree=self.table(self.calc_tab,['Date','Outstanding (INR)','Rate %','Year basis','Interest (unrounded)'])
        self.report=tk.Text(self.calc_tab,height=7,wrap='word',font=('Segoe UI',10));self.report.pack(fill='x')
    def clear_result(self):
        if hasattr(self,'cards'):
            self.cards.set('Calculate to refresh results.');self.daily_tree.delete(*self.daily_tree.get_children());self.report.delete('1.0','end')
    def calculate(self):
        try:
            if not self.rows:raise ValueError('Import and apply a valid statement first')
            changes=[]
            for line in self.changes.get('1.0','end').strip().splitlines():
                if line.strip():
                    d,r=line.split(',');changes.append((parse_date(d.strip()),money(r.strip(),Decimal(0))))
            args=dict(start=parse_date(self.start.get()),end=parse_date(self.end.get()),opening=money(self.opening.get(),Decimal(0)),annual_rate=money(self.rate.get(),Decimal(0)),basis=self.basis.get(),mode=self.mode.get(),rate_changes=changes)
            result=analyze(self.rows,**args)
            # An unchanged calculation snapshot is exported, even if input widgets are later edited.
            self.snapshot={k:str(v) for k,v in args.items()};self.result=result
            self.cards.set(f"Expected interest  ₹{result['expected']:,.2f}     |     Bank interest (net)  ₹{result['totals']['Interest']:,.2f}\nDifference  ₹{result['variance']:,.2f}     |     Total detected bank costs  ₹{result['all_cost']:,.2f}     |     {result['days']} days")
            self.daily_tree.delete(*self.daily_tree.get_children())
            for r in result['daily']:self.daily_tree.insert('','end',values=[r['date'],f"{r['outstanding']:,.2f}",r['rate'],r['days_basis'],f"{r['interest']:.8f}"])
            implied='N/A' if result['implied'] is None else f"{result['implied']:.3f}%"
            info=[f"Average outstanding: ₹{result['average']:,.2f} | Implied simple annual interest rate (365-day): {implied}"]
            info += [f'{c}: ₹{v:,.2f}' for c,v in result['totals'].items()]
            info += ['Difference = bank interest less calculated interest. A difference is a review item, not proof of overcharging. GST, penalties and other fees are excluded from interest comparison. Credit entries in reviewed categories reduce costs.','Calculation uses daily outstanding × annual rate ÷ 100 ÷ year basis; no separate compounding. Posted interest included in statement balances remains in outstanding. Posting delays, rate resets and lender rounding can affect comparison.']
            info += result['warnings'] or ['Balance movement reconciliation: no differences found (or fixed principal mode selected).']
            self.report.delete('1.0','end');self.report.insert('end','\n'.join(info));self.status.set('Analysis complete • Review reconciliation and categories before relying on totals.')
        except Exception as exc:self.result=None;self.clear_result();messagebox.showerror('Calculation problem',str(exc))

    def export(self):
        if not self.result:messagebox.showinfo('Export','Calculate first.');return
        p=filedialog.asksaveasfilename(defaultextension='.xlsx',initialfile='KSGM_Loan_Analysis.xlsx',filetypes=[('Excel','*.xlsx')])
        if not p:return
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            wb=Workbook();ws=wb.active;ws.title='Summary'
            ws.append([TITLE]);ws.append(['Calculation settings','Value'])
            for k,v in self.snapshot.items():ws.append([k,v])
            for k in ['days','average','expected','variance','all_cost','implied']:ws.append([k,None if self.result[k] is None else float(self.result[k])])
            for k,v in self.result['totals'].items():ws.append([k,float(v)])
            ws.append(['Interpretation','Difference is a review item, not proof of excess charges. Implied rate uses 365 days.'])
            for warning in self.result['warnings']:ws.append(['Reconciliation warning',warning])
            for title,rows in [('Transactions',self.result['transactions']),('Daily interest',self.result['daily'])]:
                sheet=wb.create_sheet(title)
                if rows:
                    fields=list(rows[0]);sheet.append(fields)
                    for r in rows:sheet.append([float(r[k]) if isinstance(r[k],Decimal) else r[k] for k in fields])
            for sheet in wb:
                sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
                for cell in sheet[1]:cell.font=Font(color='FFFFFF',bold=True);cell.fill=PatternFill('solid',fgColor='122C4E')
                for col in sheet.columns:
                    letter=col[0].column_letter;sheet.column_dimensions[letter].width=min(70,max(18,max(len(str(c.value or '')) for c in col)+2))
                    for cell in col:
                        if isinstance(cell.value,str) and cell.value.startswith(('=','+','-','@')):cell.data_type='s'
                        if isinstance(cell.value,float):cell.number_format='#,##0.00000000' if sheet.title=='Daily interest' else '#,##0.00'
                        if isinstance(cell.value,date):cell.number_format='yyyy-mm-dd'
            wb.save(p);self.status.set('Excel report saved: '+p)
        except Exception as exc:messagebox.showerror('Export problem',str(exc))

    def build_ai(self):
        ttk.Label(self.ai_tab,text='Optional AI review • local calculations work without an API key',font=('Segoe UI',16,'bold')).pack(anchor='w',pady=8)
        bar=ttk.Frame(self.ai_tab);bar.pack(fill='x')
        ttk.Label(bar,text='Gemini API key').pack(side='left');self.key=tk.StringVar(value=os.environ.get('GEMINI_API_KEY',''))
        ttk.Entry(bar,textvariable=self.key,show='•',width=48).pack(side='left',padx=12)
        self.button(bar,'Get API key',lambda:webbrowser.open('https://aistudio.google.com/app/apikey'))
        self.button(bar,'Load available models',self.load_models,True)
        bar=ttk.Frame(self.ai_tab);bar.pack(fill='x',pady=12)
        ttk.Label(bar,text='Model').pack(side='left');self.model=tk.StringVar();self.models=ttk.Combobox(bar,textvariable=self.model,width=58,state='readonly');self.models.pack(side='left',padx=12)
        self.button(bar,'Review analysis',self.ai_review,True)
        ttk.Label(self.ai_tab,text='Only the calculated summary and settings are sent after you click Review analysis. No transaction narrations, account numbers or statement files are sent. API key stays in memory. Google usage charges and limits may apply.',wraplength=1100).pack(anchor='w',pady=8)
        self.ai_text=tk.Text(self.ai_tab,wrap='word',font=('Segoe UI',11),padx=14,pady=14);self.ai_text.pack(fill='both',expand=True)
    def background(self,fn,callback):
        self.status.set('Contacting Gemini…')
        def run():
            try:self.events.put((callback,fn(),None))
            except Exception as exc:self.events.put((callback,None,str(exc)))
        threading.Thread(target=run,daemon=True).start()
    def poll(self):
        try:
            while True:
                cb,value,error=self.events.get_nowait()
                if error:messagebox.showerror('Gemini',error);self.status.set('Gemini request failed; local analysis remains available.')
                else:cb(value);self.status.set('Gemini request complete.')
        except queue.Empty:pass
        self.after(100,self.poll)
    def load_models(self):
        key=self.key.get().strip()
        if not key:messagebox.showinfo('API key','Create your own API key in Google AI Studio and paste it here.');return
        def work():
            models=[];token=None
            while True:
                data=api(key,'models'+('?' + urlencode({'pageToken':token}) if token else ''))
                models.extend(m['name'].removeprefix('models/') for m in data.get('models',[]) if 'generateContent' in m.get('supportedGenerationMethods',[]) and 'gemini' in m.get('name','').lower())
                token=data.get('nextPageToken')
                if not token:break
            if not models:raise ValueError('No Gemini content-generation models available for this key')
            return sorted(set(models))
        def done(models):self.models['values']=models;self.model.set(models[0])
        self.background(work,done)
    def ai_review(self):
        if not self.result:messagebox.showinfo('AI review','Calculate the loan analysis first.');return
        key,model=self.key.get().strip(),self.model.get()
        if not key or not model:messagebox.showinfo('AI review','Enter your key and load available models first.');return
        payload={k:str(self.result[k]) for k in ['days','average','expected','variance','implied','all_cost']}
        payload['categories']={k:str(v) for k,v in self.result['totals'].items()};payload['settings']=self.snapshot;payload['reconciliation_warning_count']=len(self.result['warnings'])
        prompt='Review this loan-interest reconciliation summary in INR. Explain differences and missing evidence to request. Do not assert unlawful overcharging, invent contractual terms, or change deterministic figures. Expected interest is daily closing outstanding times annual rate divided by day basis; dates inclusive. Implied rate uses 365 days. Categories are user-reviewed narration matches, credits netted. Give a short professional review. Data: '+json.dumps(payload)
        def work():
            result=api(key,'models/'+model+':generateContent',{'contents':[{'parts':[{'text':prompt}]}]})
            parts=[p.get('text','') for c in result.get('candidates',[]) for p in c.get('content',{}).get('parts',[]) if not p.get('thought')]
            if not any(parts):raise ValueError('Model returned no text. Try another available model.')
            return '\n'.join(parts)
        def done(text):self.ai_text.delete('1.0','end');self.ai_text.insert('end',text)
        self.background(work,done)

if __name__=='__main__':App().mainloop()
