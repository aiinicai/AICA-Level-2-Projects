"""Tk desktop interface: standard Python install, SQLite, no local web server."""
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from datetime import datetime
from ..webapp import open_preferred_browser
from .. import db, scoring
from ..refresh import run_refresh
from ..scrapers import REGISTRY, SOURCE_URLS
from ..scrapers.base import import_text
from ..report import make_report

def fmt(value):
    return f'{value:,.2f}' if scoring.has(value) else 'Pending'

class MainWindow(tk.Tk):
    def __init__(self, auto_refresh=True):
        super().__init__()
        self.title('CA IPO Compass — Desktop')
        self.geometry('1180x760'); self.minsize(860,580)
        self.configure(background='#eef3f6')
        db.init_db()
        self.events=queue.Queue(); self.cancel=threading.Event(); self.worker=None
        self.selected=None; self.closing=False
        style=ttk.Style(self)
        style.theme_use('clam')
        style.configure('.',font=('Segoe UI',10))
        style.configure('Treeview',rowheight=29,background='white',fieldbackground='white')
        style.configure('Treeview.Heading',font=('Segoe UI',10,'bold'))
        style.configure('TNotebook.Tab',padding=(18,10))
        style.configure('TButton',padding=7)
        top=tk.Frame(self,bg='#102536',padx=18,pady=15); top.pack(fill='x')
        tk.Label(top,text='CA IPO COMPASS',font=('Segoe UI',19,'bold'),fg='white',bg='#102536').pack(side='left')
        tk.Label(top,text='Local research desk · D P Mody & Associates',fg='#b4d7e2',bg='#102536').pack(side='right')
        self.tabs=ttk.Notebook(self); self.tabs.pack(fill='both',expand=True,padx=12,pady=12)
        self.pages={}
        for title in ('Dashboard','IPO Issues','Analysis','Financial statements','Import / Edit','Data Sources'):
            frame=ttk.Frame(self.tabs,padding=12); self.tabs.add(frame,text=title); self.pages[title]=frame
        self.status=tk.StringVar(value='Ready. Saved data stays on this computer.')
        self.summary=tk.StringVar()
        dash=self.pages['Dashboard']; bar=ttk.Frame(dash); bar.pack(fill='x')
        self.refresh_btn=ttk.Button(bar,text='Refresh & analyse all',command=self.start_refresh); self.refresh_btn.pack(side='left')
        ttk.Button(bar,text='Stop after current request',command=self.cancel.set).pack(side='left',padx=8)
        self.auto=tk.BooleanVar(value=True)
        ttk.Checkbutton(bar,text='Repeat every 15 minutes',variable=self.auto).pack(side='left',padx=8)
        ttk.Label(dash,textvariable=self.summary,font=('Segoe UI',15,'bold')).pack(anchor='w',pady=16)
        ttk.Label(dash,textvariable=self.status,wraplength=1000).pack(anchor='w',pady=5)
        self.log=ScrolledText(dash,height=15,wrap='word',font=('Consolas',10),state='disabled'); self.log.pack(fill='both',expand=True)
        tools=ttk.Frame(dash);tools.pack(fill='x',pady=8)
        ttk.Button(tools,text='Export refresh log',command=self.export_log).pack(side='left')
        ttk.Button(tools,text='Export all records (JSON)',command=self.export_records).pack(side='left',padx=8)
        ttk.Label(dash,text='Database: '+db.DB_PATH,wraplength=1000).pack(anchor='w')
        issue=self.pages['IPO Issues']; self.search=tk.StringVar()
        ttk.Label(issue,text='Search by company / symbol').pack(anchor='w')
        entry=ttk.Entry(issue,textvariable=self.search); entry.pack(fill='x',pady=6)
        self.search.trace_add('write',lambda *_:self.reload())
        self.issue_table=self.table(issue,('Company','Board','Status','Price upper ₹','GMP ₹','Score /10','Coverage','Verdict'),(300,80,90,100,80,80,80,170))
        self.issue_table.bind('<<TreeviewSelect>>',self.select_issue)
        self.issue_table.bind('<Double-1>',lambda _:self.tabs.select(self.pages['Analysis']))
        ttk.Label(issue,text='Select an IPO to view its analysis, financial statements and evidence.').pack(anchor='w',pady=8)
        analysis=self.pages['Analysis']; self.verdict=tk.StringVar(value='Select an IPO in IPO Issues.')
        ttk.Label(analysis,textvariable=self.verdict,font=('Segoe UI',15,'bold'),wraplength=1050).pack(anchor='w',pady=8)
        self.factors=self.table(analysis,('Factor','Weight','Score /10'),(400,150,150))
        self.notes=ScrolledText(analysis,height=7,wrap='word',state='disabled');self.notes.pack(fill='x',pady=8)
        ttk.Button(analysis,text='Export analysis report (HTML)',command=self.export_report).pack(anchor='w')
        finances=self.pages['Financial statements']; self.fin_summary=tk.StringVar(value='Select an IPO.')
        ttk.Label(finances,textvariable=self.fin_summary,wraplength=1000).pack(anchor='w',pady=8)
        self.financials=self.table(finances,('Metric','FY-2','FY-1','Latest FY'),(380,180,180,180))
        ttk.Button(finances,text='Open statement source',command=self.open_research).pack(anchor='w',pady=8)
        imp=self.pages['Import / Edit']
        ttk.Label(imp,text='Paste CSV / JSON / saved HTML. Financial JSON arrays contain three annual values, oldest first; null means missing.',wraplength=1000).pack(anchor='w')
        self.editor=ScrolledText(imp,font=('Consolas',10),wrap='none');self.editor.pack(fill='both',expand=True,pady=8)
        ib=ttk.Frame(imp);ib.pack(fill='x')
        for text,action in [('Import pasted text',self.import_paste),('Import file',self.import_file),('Edit selected IPO',self.edit_selected),('Blank JSON template',self.template)]:
            ttk.Button(ib,text=text,command=action).pack(side='left',padx=(0,8))
        ttk.Label(imp,text='Manual entries are labelled manual. Existing official exchange fields are protected. Use an override reason to record an analyst decision.',wraplength=1000).pack(anchor='w',pady=8)
        source=self.pages['Data Sources']
        for key,(_,name,_,_) in REGISTRY.items():
            ttk.Button(source,text='Open '+name,command=lambda k=key:open_preferred_browser(SOURCE_URLS[k])).pack(anchor='w',pady=3)
        self.source_text=ScrolledText(source,height=8,wrap='word',state='disabled');self.source_text.pack(fill='both',expand=True,pady=10)
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.reload();self.after(100,self.poll);self.after(900000,self.periodic)
        # Skip the immediate on-open refresh if the last one finished less
        # than 15 minutes ago — the window still opens instantly with the
        # saved database either way; periodic() above keeps it live afterwards.
        if auto_refresh and db.refresh_is_stale():self.after(1000,self.start_refresh)

    def table(self,parent,columns,widths):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
        tree=ttk.Treeview(frame,columns=columns,show='headings',selectmode='browse')
        y=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);x=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview)
        tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        tree.grid(row=0,column=0,sticky='nsew');y.grid(row=0,column=1,sticky='ns');x.grid(row=1,column=0,sticky='ew')
        frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        for c,w in zip(columns,widths):tree.heading(c,text=c);tree.column(c,width=w,minwidth=70)
        return tree

    @staticmethod
    def put(widget,text):
        widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0',text);widget.configure(state='disabled')

    def append_log(self,text):
        self.log.configure(state='normal');self.log.insert('end',datetime.now().strftime('%H:%M:%S')+'  '+text+'\n');self.log.see('end');self.log.configure(state='disabled')

    def start_refresh(self):
        if self.worker and self.worker.is_alive():return
        self.cancel.clear();self.refresh_btn.configure(state='disabled');self.status.set('Refreshing sources and analysing every current/upcoming IPO…')
        def work():
            try:run_refresh(lambda kind,value:self.events.put((kind,value)),self.cancel)
            except Exception as e:self.events.put(('done','Refresh stopped: '+str(e)))
        self.worker=threading.Thread(target=work,daemon=False);self.worker.start()

    def poll(self):
        while True:
            try:kind,value=self.events.get_nowait()
            except queue.Empty:break
            if kind=='log':self.append_log(value)
            elif kind=='data':self.reload()
            elif kind=='done':self.status.set(value);self.append_log(value);self.refresh_btn.configure(state='normal');self.reload()
        if self.closing and not (self.worker and self.worker.is_alive()):self.destroy();return
        self.after(150,self.poll)

    def periodic(self):
        if self.auto.get() and not self.closing:self.start_refresh()
        self.after(900000,self.periodic)

    def reload(self):
        records=db.all_ipos();query=self.search.get().lower()
        for item in self.issue_table.get_children():self.issue_table.delete(item)
        for r in records:
            if query not in (r['name']+' '+(r.get('symbol') or '')).lower():continue
            a=scoring.analyse(r)
            self.issue_table.insert('', 'end', iid=r['id'], values=(r['name'],r['board'],r['status'],fmt(r['price_high']),fmt(r['gmp_amount']),fmt(a['score']),f'{a["coverage"]:.0f}%',a['final']))
        self.summary.set(f'{len(records)} tracked IPOs   ·   {sum(r["status"]=="Open" for r in records)} marked open   ·   source dates shown in analysis')
        if not self.selected and records:self.selected=records[0]['id']
        self.render_analysis()

    def select_issue(self,_=None):
        selected=self.issue_table.selection()
        if selected:self.selected=selected[0];self.render_analysis()

    def render_analysis(self):
        r=db.get(self.selected) if self.selected else None
        if not r:return
        a=scoring.analyse(r)
        self.verdict.set(f'{r["name"]} — {a["final"]} | {fmt(a["score"])} /10 | Coverage {a["coverage"]:.0f}%')
        for item in self.factors.get_children():self.factors.delete(item)
        for key,value in a['factors'].items():self.factors.insert('','end',values=(scoring.FACTOR_NAMES[key],f'{scoring.RAW_WEIGHTS[key]/scoring.RAW_TOTAL*100:.1f}%',fmt(value)))
        self.put(self.notes,'BUSINESS / LOCATION: '+(r.get('sector') or 'Pending')+' / '+(r.get('location') or 'Pending')+'\nPOSITIVES: '+('; '.join(a['positives']) or 'No evidenced positive signal')+'\nRISKS: '+('; '.join(a['flags']) or 'None identified from available data')+'\nMISSING: '+', '.join(a['missing'])+'\nNOTES: '+(r.get('notes') or ''))
        research=r.get('research') or {};series={str(y):v for y,v in research.get('series',{}).items()}
        years=r.get('years') or ['FY-2','FY-1','Latest']
        for col,y in zip(('FY-2','FY-1','Latest FY'),years):self.financials.heading(col,text=str(y))
        for item in self.financials.get_children():self.financials.delete(item)
        for key,label in [('revenue','Revenue ₹ Cr'),('ebitda','EBITDA ₹ Cr'),('pat','PAT ₹ Cr'),('cfo','Operating cash flow ₹ Cr'),('fcf','Free cash flow ₹ Cr')]:
            self.financials.insert('','end',values=(label,*[fmt(v) for v in r.get(key,[None]*3)]))
        for key in ('inventory','receivables','payables','current_assets','current_liabilities','net_working_capital','finance_cost','investing','financing','deb_days','inv_days','cred_days','ccc'):
            self.financials.insert('','end',values=(key.replace('_',' ').title()+(' (days; creditor/CCC proxy)' if key.endswith('days') or key=='ccc' else ' ₹ Cr'),*[fmt(series.get(str(y),{}).get(key)) for y in years]))
        self.fin_summary.set('CFO/PAT: '+fmt(a['ratio'])+'x · Cumulative: '+fmt(a['cum'])+'x\n'+research.get('level','No automatic statement import yet')+' · Retrieved '+research.get('at','not recorded')+'\n'+research.get('method','CFO and PAT must refer to matching annual periods. Missing values stay pending.'))
        sources=db.sources_for(r['id'])
        lines=[f'{x["name"]} | {x["at"]}\n{x["url"]}\n{x["fields"]}' for x in sources]
        history=db.gmp_history(r['id'])
        lines+=['GMP OBSERVATIONS (retrieval time, not exchange data)']+[f'{x["source"]}: ₹{fmt(x["amount"])} ({fmt(x["pct"])}%) — {x["at"]}' for x in history]
        self.put(self.source_text,'\n\n'.join(lines) or 'No source observations yet.')

    def open_research(self):
        r=db.get(self.selected) if self.selected else None
        url=(r or {}).get('research',{}).get('url','')
        if url.startswith('https://'):open_preferred_browser(url)

    def import_paste(self):self.import_content(self.editor.get('1.0','end'))

    def import_content(self,text):
        try:
            rows=import_text(text)
            rows=[db.validate_incoming(r) for r in rows]
            if not rows:raise ValueError('No recognised IPO records found. A saved page must contain the actual populated table.')
            for r in rows:self.selected=db.merge_incoming(r,'manual','Manual import','','User-supplied data',False)
            self.reload();self.status.set(f'Imported {len(rows)} records and recalculated available scores.');messagebox.showinfo('Imported',self.status.get())
        except Exception as e:messagebox.showerror('Import failed',str(e))

    def import_file(self):
        path=filedialog.askopenfilename(filetypes=[('IPO data','*.json *.csv *.html *.htm *.txt')])
        if path:
            try:self.import_content(Path(path).read_text(encoding='utf-8-sig'))
            except Exception as e:messagebox.showerror('Cannot read file',str(e))

    def edit_selected(self):
        r=db.get(self.selected) if self.selected else None
        if not r:return
        for key in ('field_sources','research','updated_at','id'):r.pop(key,None)
        self.editor.delete('1.0','end');self.editor.insert('1.0',json.dumps(r,indent=2,ensure_ascii=False))

    def template(self):
        r=db.ensure_record({'name':'Enter company name'});r.pop('id');r.pop('research');r.pop('field_sources')
        self.editor.delete('1.0','end');self.editor.insert('1.0',json.dumps(r,indent=2))

    def export_records(self):
        path=filedialog.asksaveasfilename(defaultextension='.json',initialfile='IPO_Compass_Backup.json')
        if path:Path(path).write_text(json.dumps(db.all_ipos(),indent=2,ensure_ascii=False),encoding='utf-8')

    def export_log(self):
        path=filedialog.asksaveasfilename(defaultextension='.txt',initialfile='IPO_Compass_Refresh_Log.txt')
        if path:Path(path).write_text(self.log.get('1.0','end'),encoding='utf-8')

    def export_report(self):
        r=db.get(self.selected) if self.selected else None
        if not r:return
        path=filedialog.asksaveasfilename(defaultextension='.html',initialfile='IPO_Analysis.html')
        if path:Path(path).write_text(make_report(r),encoding='utf-8');messagebox.showinfo('Saved','HTML report saved. Open it in a browser to read or print.')

    def close(self):
        if self.worker and self.worker.is_alive():
            self.closing=True;self.cancel.set();self.status.set('Closing after the current bounded network request finishes…');return
        self.destroy()
