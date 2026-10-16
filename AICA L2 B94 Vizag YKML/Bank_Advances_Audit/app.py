"""Bank advances audit desktop; start with run.bat or python app.py."""
import json
import queue
import threading
import hashlib
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import customtkinter as ctk
from audit_engine import (SCHEMAS,DEFAULT_POLICY,REVIEW_STATES,DISPOSITIONS,load_audit,
    dashboard,update_review,review_coverage,save_session,restore_session,draft_prompt,stamp)
from reports import export_excel,export_html,account_rows
from ai_review import request_draft

ROOT=Path(__file__).resolve().parent
ctk.set_appearance_mode('light');ctk.set_default_color_theme('blue')

class App(ctk.CTk):
    def __init__(self):
        super().__init__();self.title('Bank Advances | Audit & Evidence Review');self.geometry('1320x850');self.minsize(1050,700)
        self.result=None;self.selected=None;self.policy=json.loads((ROOT/'audit_policy.json').read_text())
        self.paths={k:tk.StringVar() for k in SCHEMAS};self.asof=tk.StringVar(value='2026-09-30')
        self.policy_vars={k:tk.StringVar(value=str(self.policy[k])) for k in
            ('conduct_window_days','term_overdue_review_days','stock_stale_days','renewal_reminder_days','tolerance_inr')}
        self.filter=tk.StringVar(value='All');self.review_state=tk.StringVar(value='Open');self.disposition=tk.StringVar(value='Unresolved');self.reviewer=tk.StringVar()
        self.notes={};self.prompt_snapshot=None
        ctk.CTkLabel(self,text='Bank Advances Audit & Exception Review',font=('',26,'bold')).pack(anchor='w',padx=22,pady=(16,2))
        ctk.CTkLabel(self,text='Drawing power • Account conduct • Repayment • Evidence and reviewer conclusions',text_color='#526C7A').pack(anchor='w',padx=22)
        tabs=ctk.CTkTabview(self);tabs.pack(fill='both',expand=True,padx=15,pady=10)
        self.tabs={name:tabs.add(name) for name in ['Audit setup','Findings & review','Calculations','Closing & coverage','AI drafting','Method']}
        self.setup_ui();self.review_ui();self.calc_ui();self.closing_ui();self.ai_ui()
        method=ctk.CTkTextbox(self.tabs['Method']);method.pack(fill='both',expand=True)
        method.insert('1.0',(ROOT/'docs'/'METHOD.md').read_text(encoding='utf-8'));method.configure(state='disabled')

    def scroll(self,parent):
        f=ctk.CTkScrollableFrame(parent);f.pack(fill='both',expand=True);return f
    def label(self,f,text):ctk.CTkLabel(f,text=text,anchor='w',justify='left',wraplength=1120).pack(fill='x',padx=8,pady=4)
    def textbox(self,f,height=90):
        b=ctk.CTkTextbox(f,height=height);b.pack(fill='x',padx=8,pady=4);return b
    def show(self,b,text):b.configure(state='normal');b.delete('1.0','end');b.insert('1.0',text)
    def need(self):
        if self.result is None:raise ValueError('Load the inputs and Run audit first.')
    def guarded(self,fn):
        def wrapped():
            try:fn()
            except Exception as exc:messagebox.showerror('Please check',str(exc))
        return wrapped
    def button(self,f,text,fn):ctk.CTkButton(f,text=text,command=self.guarded(fn),width=240).pack(anchor='w',padx=8,pady=5)

    def setup_ui(self):
        f=self.scroll(self.tabs['Audit setup'])
        self.label(f,'Load five normalized files. Header-only files are allowed for supporting schedules; missing coverage is reported. Use one branch per run.')
        for k in SCHEMAS:
            row=ctk.CTkFrame(f);row.pack(fill='x',pady=4)
            ctk.CTkLabel(row,text=k.title(),width=130,anchor='w').pack(side='left',padx=8)
            ctk.CTkEntry(row,textvariable=self.paths[k]).pack(side='left',fill='x',expand=True)
            ctk.CTkButton(row,text='Browse',width=100,command=lambda key=k:self.browse(key)).pack(side='left',padx=8,pady=6)
        self.button(f,'Load fictional demo files',self.demo)
        self.label(f,'Audit date (YYYY-MM-DD). Account amounts and payment allocations must be as of this date.')
        ctk.CTkEntry(f,textvariable=self.asof,width=220).pack(anchor='w',padx=8)
        self.button(f,'Load bank/audit policy JSON',self.load_policy)
        self.policy_label=ctk.CTkLabel(f,text=self.policy['profile_name'],anchor='w',wraplength=1100);self.policy_label.pack(fill='x',padx=8,pady=5)
        for k,var in self.policy_vars.items():
            row=ctk.CTkFrame(f);row.pack(fill='x',pady=2)
            ctk.CTkLabel(row,text=k.replace('_',' ').title(),width=350,anchor='w').pack(side='left',padx=8)
            ctk.CTkEntry(row,textvariable=var,width=160).pack(side='left',pady=4)
        self.label(f,'These are illustrative review settings, not a certified RBI ruleset. Verify the applicable bank type, audit period, sanctions and latest instructions before using results professionally.')
        self.button(f,'Run audit',self.run)
        self.summary=self.textbox(f,120);self.show(self.summary,'Start with Load fictional demo files, then Run audit.')

    def browse(self,k):
        p=filedialog.askopenfilename(filetypes=[('Excel/CSV','*.xlsx *.csv')])
        if p:self.paths[k].set(p)
    def demo(self):
        for k,v in self.paths.items():v.set(str(ROOT/'sample_data'/f'{k}_demo.csv'))
        self.asof.set('2026-09-30')
    def load_policy(self):
        path=filedialog.askopenfilename(filetypes=[('Audit policy','*.json')])
        if path:
            from audit_engine import validate_policy
            p=json.loads(Path(path).read_text(encoding='utf-8'));validate_policy(p);self.policy=p
            for k,v in self.policy_vars.items():v.set(str(p[k]))
            self.policy_label.configure(text=p['profile_name'])
    def run(self):
        if self.result is not None and not messagebox.askyesno('New audit','A new run clears current reviews. Save the session first if needed. Continue?'):return
        p=dict(self.policy)
        for k,v in self.policy_vars.items():p[k]=v.get()
        self.result=load_audit({k:v.get() for k,v in self.paths.items()},self.asof.get(),p)
        self.selected=None;self.filter.set('All');self.refresh()

    def tree(self,f,columns,height=8):
        frame=ctk.CTkFrame(f);frame.pack(fill='both',expand=True,pady=5)
        tree=ttk.Treeview(frame,columns=columns,show='headings',selectmode='browse',height=height)
        for c in columns:tree.heading(c,text=c.replace('_',' ').title());tree.column(c,width=150,minwidth=90)
        xs=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview);ys=ttk.Scrollbar(frame,orient='vertical',command=tree.yview)
        tree.configure(xscrollcommand=xs.set,yscrollcommand=ys.set)
        tree.grid(row=0,column=0,sticky='nsew');xs.grid(row=1,column=0,sticky='ew');ys.grid(row=0,column=1,sticky='ns')
        frame.grid_columnconfigure(0,weight=1);frame.grid_rowconfigure(0,weight=1)
        return tree

    def review_ui(self):
        f=self.scroll(self.tabs['Findings & review'])
        ctk.CTkOptionMenu(f,variable=self.filter,values=['All','High','Open','Reviewed','Reporting points'],command=lambda _:self.refresh_findings()).pack(anchor='w',padx=8)
        self.findings=self.tree(f,['finding_id','account_id','priority','title','review_status','disposition'])
        self.findings.bind('<<TreeviewSelect>>',self.select_finding)
        self.condition=self.textbox(f,160);self.condition.configure(state='disabled')
        row=ctk.CTkFrame(f);row.pack(fill='x',pady=5)
        ctk.CTkLabel(row,text='Reviewer').pack(side='left',padx=8)
        ctk.CTkEntry(row,textvariable=self.reviewer,width=200).pack(side='left')
        ctk.CTkOptionMenu(row,variable=self.review_state,values=REVIEW_STATES).pack(side='left',padx=8)
        ctk.CTkOptionMenu(row,variable=self.disposition,values=DISPOSITIONS,width=250).pack(side='left')
        for k,title in [('evidence_assessment','Evidence inspected / references / limitations'),('management_response','Branch or management response (unverified assertion)'),
            ('auditor_conclusion','Auditor conclusion'),('recommended_action','Recommended action / follow-up'),('proposed_reporting_point','Proposed reporting-point wording, if applicable')]:
            self.label(f,title);self.notes[k]=self.textbox(f,70)
        self.button(f,'Save finding decision',self.save_decision)
        self.label(f,'Save the decision before changing findings. Save session writes all decisions to disk. Reviewed is documentation status, not proof that the bank performed the action.')
    def refresh_findings(self):
        self.findings.delete(*self.findings.get_children());self.selected=None
        self.show(self.condition,'Select a finding to inspect its immutable source condition and requested evidence.');self.condition.configure(state='disabled')
        for b in self.notes.values():self.show(b,'')
        if self.result is None:return
        for r in self.result['findings']:
            mode=self.filter.get()
            if mode=='High' and r['priority']!='High':continue
            if mode=='Open' and r['review_status']=='Reviewed':continue
            if mode=='Reviewed' and r['review_status']!='Reviewed':continue
            if mode=='Reporting points' and not(r['disposition']=='Potential reporting point' and r['review_status']=='Reviewed'):continue
            self.findings.insert('','end',iid=r['finding_id'],values=[r[c] for c in self.findings['columns']])
    def select_finding(self,_=None):
        sel=self.findings.selection()
        if not sel:return
        self.selected=next(r for r in self.result['findings'] if r['finding_id']==sel[0]);r=self.selected
        self.show(self.condition,r['title']+'\n\n'+r['condition']+'\n\nSOURCE REFERENCES\n'+r['evidence_refs']+'\n\nREQUESTED EVIDENCE\n'+r['requested_evidence']);self.condition.configure(state='disabled')
        self.reviewer.set(r['reviewer']);self.review_state.set(r['review_status']);self.disposition.set(r['disposition'])
        for k,b in self.notes.items():self.show(b,r[k])
    def save_decision(self):
        self.need()
        if not self.selected:raise ValueError('Select a finding first.')
        values=dict(review_status=self.review_state.get(),disposition=self.disposition.get(),reviewer=self.reviewer.get())
        values.update({k:b.get('1.0','end').strip() for k,b in self.notes.items()})
        update_review(self.result,self.selected['finding_id'],values);self.refresh()

    def calc_ui(self):
        f=self.tabs['Calculations'];self.calc_choice=tk.StringVar(value='Drawing power')
        ctk.CTkOptionMenu(f,variable=self.calc_choice,values=['Drawing power','Conduct','Term dues','Accounts'],command=lambda _:self.refresh_calcs()).pack(anchor='w',padx=8,pady=5)
        self.calcs=self.tree(f,['message'],height=15)
        self.label(f,'Drawing power shows the complete calculation bridge. Conduct tests use historical daily sanction and DP supplied in the daily file, not a single current snapshot.')
    def refresh_calcs(self):
        self.calcs.delete(*self.calcs.get_children())
        if self.result is None:return
        key={'Drawing power':'drawing_power','Conduct':'conduct','Term dues':'term_dues','Accounts':'account_summary'}[self.calc_choice.get()]
        rows=self.result[key];cols=list(rows[0]) if rows else ['message'];self.calcs.configure(columns=cols)
        for c in cols:self.calcs.heading(c,text=c.replace('_',' ').title());self.calcs.column(c,width=170,minwidth=100)
        for r in rows:self.calcs.insert('','end',values=[str(r[c]) for c in cols])

    def closing_ui(self):
        f=self.scroll(self.tabs['Closing & coverage'])
        self.close_box=self.textbox(f,170)
        self.coverage_choice=tk.StringVar(value='(none)');self.coverage_menu=ctk.CTkOptionMenu(f,variable=self.coverage_choice,values=['(none)'],width=850,command=lambda _:self.coverage_select());self.coverage_menu.pack(anchor='w',padx=8,pady=5)
        self.coverage_reviewer=tk.StringVar();self.label(f,'Account coverage reviewer');ctk.CTkEntry(f,textvariable=self.coverage_reviewer,width=300).pack(anchor='w',padx=8)
        self.label(f,'Account-level population/evidence/policy assessment, including accounts with no generated findings')
        self.coverage_text=self.textbox(f,90)
        self.button(f,'Record account coverage',self.coverage_save)
        self.coverage_list=self.textbox(f,150)
        for label,fn in [('Export Excel working papers',self.excel),('Export printable HTML report',self.html),('Save session',self.save),('Load session',self.restore)]:self.button(f,label,fn)
        self.label(f,'Open the HTML file in a browser and use Print for PDF. Exposure counts each supplied account once. Generated findings are not the full audit universe.')
    def coverage_save(self):
        self.need();aid=self.coverage_choice.get().split(' | ')[0]
        review_coverage(self.result,aid,self.coverage_reviewer.get(),self.coverage_text.get('1.0','end').strip());self.refresh()
    def coverage_select(self):
        if self.result is None:return
        aid=self.coverage_choice.get().split(' | ')[0];review=self.result['coverage_reviews'].get(aid,{})
        self.coverage_reviewer.set(review.get('reviewer',''));self.show(self.coverage_text,review.get('assessment',''))
    def excel(self):
        self.need();p=filedialog.asksaveasfilename(defaultextension='.xlsx',initialfile='Bank_Advances_Audit.xlsx')
        if p:export_excel(self.result,p);messagebox.showinfo('Saved','Excel working papers exported.')
    def html(self):
        self.need();p=filedialog.asksaveasfilename(defaultextension='.html',initialfile='Bank_Audit_Closing_Review.html')
        if p:export_html(self.result,p);messagebox.showinfo('Saved','Open the HTML report in your browser.')
    def save(self):
        self.need();p=filedialog.asksaveasfilename(defaultextension='.json',initialfile='bank_audit_session.json')
        if p:save_session(self.result,p);messagebox.showinfo('Saved','Applied reviews, policy and source signatures saved.')
    def restore(self):
        self.need();p=filedialog.askopenfilename(filetypes=[('Audit session','*.json')])
        if p:self.result=restore_session(self.result,p);self.refresh()

    def ai_ui(self):
        f=self.scroll(self.tabs['AI drafting']);self.ai_choice=tk.StringVar(value='(none)')
        self.ai_menu=ctk.CTkOptionMenu(f,variable=self.ai_choice,values=['(none)'],width=1000,command=lambda _:self.clear_prompt());self.ai_menu.pack(anchor='w',padx=8,pady=5)
        self.label(f,'AI drafts are based on the selected account, its calculation summaries, finding and document register. This is not full transaction-file analysis or automatic NPA classification.')
        self.button(f,'Preview / save evidence prompt',self.preview_prompt)
        self.key=tk.StringVar();self.model=tk.StringVar()
        self.label(f,'Optional OpenAI API key (memory only)');ctk.CTkEntry(f,textvariable=self.key,show='*',width=650).pack(anchor='w',padx=8)
        self.label(f,'Model ID available to your separate API account');ctk.CTkEntry(f,textvariable=self.model,width=400).pack(anchor='w',padx=8)
        self.api_button=ctk.CTkButton(f,text='Generate unapproved API draft',command=self.guarded(self.api_send),width=270);self.api_button.pack(anchor='w',padx=8,pady=7)
        self.ai_output=self.textbox(f,220)
        self.button(f,'Save pasted external AI draft',self.save_external)
        self.label(f,'No API key needed for the audit engine. Export the prompt for manual use in an authorized AI tool, then paste the response here. External drafts are labeled as unverified provenance. All drafts require auditor validation.')
        self.queue=queue.Queue()
    def ai_id(self):
        self.need();fid=self.ai_choice.get().split(' | ')[0]
        if fid not in {r['finding_id'] for r in self.result['findings']}:raise ValueError('Select a generated finding.')
        return fid
    def clear_prompt(self):self.prompt_snapshot=None;self.show(self.ai_output,'')
    def preview_prompt(self):
        fid=self.ai_id();prompt=draft_prompt(self.result,fid);self.prompt_snapshot=(fid,prompt)
        win=ctk.CTkToplevel(self);win.title('Exact bank-audit evidence prompt');win.geometry('960x650')
        b=ctk.CTkTextbox(win);b.pack(fill='both',expand=True,padx=10,pady=10);b.insert('1.0',prompt);b.configure(state='disabled')
        def save():
            p=filedialog.asksaveasfilename(defaultextension='.txt',initialfile='Bank_Audit_AI_Prompt.txt')
            if p:Path(p).write_text(prompt,encoding='utf-8')
        ctk.CTkButton(win,text='Save prompt for manual use',command=self.guarded(save),width=260).pack(pady=6)
    def api_send(self):
        fid=self.ai_id();prompt=draft_prompt(self.result,fid)
        if self.prompt_snapshot!=(fid,prompt):raise ValueError('Preview the exact current prompt before sending.')
        key,model=self.key.get().strip(),self.model.get().strip()
        if not key or not model:raise ValueError('Enter API key/model, or use manual prompt export.')
        if not messagebox.askyesno('Send account information to OpenAI?',
           'Send the exact previewed prompt to https://api.openai.com? It contains selected account/borrower identifiers, financial figures, bank classification, policy, document references and reviewer/branch notes. API charges may apply. store=false does not guarantee zero retention. No audit decision changes automatically.'):return
        run=self.result;self.api_button.configure(state='disabled',text='Generating...')
        def worker():
            try:self.queue.put(('ok',request_draft(prompt,key,model),run,fid,prompt))
            except Exception as exc:self.queue.put(('error',str(exc),run,fid,prompt))
        threading.Thread(target=worker,daemon=True).start();self.after(150,self.api_poll)
    def api_poll(self):
        try:status,value,run,fid,prompt=self.queue.get_nowait()
        except queue.Empty:self.after(150,self.api_poll);return
        self.api_button.configure(state='normal',text='Generate unapproved API draft')
        if status=='error':messagebox.showerror('AI request',value);return
        if self.result is not run:messagebox.showinfo('Run changed','Draft discarded because audit run changed.');return
        run['ai_notes'].append(dict(timestamp_utc=stamp(),finding_id=fid,source='OpenAI Responses API',status='Unapproved draft',
          prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),prompt_text=prompt,**value))
        if self.ai_choice.get().split(' | ')[0]==fid:self.show(self.ai_output,value['text'])
        else:messagebox.showinfo('AI draft saved','Draft saved for '+fid+'. View it in the exported AI drafts sheet or saved session.')
    def save_external(self):
        fid=self.ai_id();text=self.ai_output.get('1.0','end').strip()
        if not text:raise ValueError('Paste an externally generated draft first.')
        prompt=draft_prompt(self.result,fid)
        self.result['ai_notes'].append(dict(timestamp_utc=stamp(),finding_id=fid,source='User-pasted external AI',status='Unapproved; provenance unverified',
           prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),prompt_text=prompt,text=text,model='User supplied',response_id='',usage={}))
        messagebox.showinfo('Saved','External draft recorded; no finding decision changed.')

    def refresh(self):
        self.need();stats=dashboard(self.result);summary='\n'.join(k.replace('_',' ').title()+': '+str(v) for k,v in stats.items())
        self.show(self.summary,summary);self.show(self.close_box,summary)
        self.refresh_findings();self.refresh_calcs()
        choices=[a['account_id']+' | '+a['borrower_name'] for a in self.result['raw']['accounts']]
        self.coverage_menu.configure(values=choices)
        if self.coverage_choice.get() not in choices:self.coverage_choice.set(choices[0])
        self.coverage_select()
        self.show(self.coverage_list,'\n\n'.join(f'{a["account_id"]}: {a["total_findings"]} findings, {a["open_findings"]} open. Coverage reviewer: {a["coverage_reviewer"] or "PENDING"}\n{a["coverage_assessment"]}' for a in account_rows(self.result)))
        ai_values=[f['finding_id']+' | '+f['title'] for f in self.result['findings']] or ['(none)']
        self.ai_menu.configure(values=ai_values)
        if self.ai_choice.get() not in ai_values:self.ai_choice.set(ai_values[0])
        self.prompt_snapshot=None

if __name__=='__main__':App().mainloop()
