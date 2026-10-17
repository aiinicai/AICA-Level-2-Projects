from pathlib import Path
import json,threading
import customtkinter as ctk
from tkinter import filedialog,messagebox
from engine import FIELDS,FLAGS,blank,calculate,narrative,ai_prompt
from report import export_report
from ai_review import request_draft
ROOT=Path(__file__).resolve().parent
ctk.set_appearance_mode('light'); ctk.set_default_color_theme('blue')

class App(ctk.CTk):
 def __init__(self):
  super().__init__(); self.title('ITR Preparation & Regime Assistant | AY 2026-27'); self.geometry('1200x850'); self.minsize(1000,650)
  self.vars={}; self.last_profile=None; self.draft=''
  ctk.CTkLabel(self,text='ITR preparation • Old vs New regime',font=('',25,'bold')).pack(pady=(16,2))
  ctk.CTkLabel(self,text='AY 2026–27 / FY 2025–26 only • Resident individuals • Preparation working paper; no portal filing').pack()
  bar=ctk.CTkFrame(self); bar.pack(fill='x',padx=15,pady=10)
  for text,fn in [('Load example / profile',self.load),('Save profile',self.save),('Calculate',self.compute),('Export Excel',self.export)]: ctk.CTkButton(bar,text=text,command=fn,width=160).pack(side='left',padx=5,pady=8)
  tabs=ctk.CTkTabview(self); tabs.pack(fill='both',expand=True,padx=15,pady=(0,15))
  inputs=tabs.add('1 • Income & claims'); checks=tabs.add('2 • Eligibility & evidence'); results=tabs.add('3 • Comparison'); review=tabs.add('4 • Review & AI')
  frame=ctk.CTkScrollableFrame(inputs); frame.pack(fill='both',expand=True)
  self.entry(frame,'case','Case reference (avoid PAN / Aadhaar)'); self.entry(frame,'age','Age in completed years at 31 March 2026')
  for k,label in FIELDS.items(): self.entry(frame,k,label+' (Rs, annual)')
  opts=ctk.CTkFrame(frame); opts.pack(fill='x',pady=10)
  for k,label in [('metro','HRA: Mumbai / Delhi / Kolkata / Chennai'),('self_senior','80D: qualifying self/family senior'),('parents_senior','80D: qualifying senior parent')]:
   self.vars[k]=ctk.BooleanVar(); ctk.CTkCheckBox(opts,text=label,variable=self.vars[k]).pack(anchor='w',padx=10,pady=6)
  self.vars['home_cap']=ctk.StringVar(value='200000')
  ctk.CTkLabel(opts,text='Self-occupied loan cap: Rs 2 lakh only if acquisition/construction and statutory conditions met; otherwise Rs 30,000.').pack(anchor='w',padx=10)
  ctk.CTkOptionMenu(opts,values=['200000','30000'],variable=self.vars['home_cap']).pack(anchor='w',padx=10,pady=8)
  ctk.CTkLabel(frame,text='Enter only eligible claims. 80C bucket must already respect individual NPS/80CCC limits; no double counting.\n80D amounts must already respect payment rules and the combined Rs 5,000 preventive-checkup sublimit.\nHRA assumes the same employment/rent period; varying periods need separate calculation. Employer NPS, LTA and other exemptions are outside scope.',justify='left',wraplength=1000).pack(pady=15)
  cf=ctk.CTkScrollableFrame(checks); cf.pack(fill='both',expand=True)
  ctk.CTkLabel(cf,text='First four answers are scope gates. Tick only after verifying the facts.',font=('',17,'bold')).pack(anchor='w',padx=10,pady=15)
  for k,label in FLAGS.items():
   self.vars[k]=ctk.BooleanVar(); ctk.CTkCheckBox(cf,text=label,variable=self.vars[k],width=900).pack(anchor='w',padx=10,pady=10)
  self.output=ctk.CTkTextbox(results,font=('Consolas',13),wrap='none'); self.output.pack(fill='both',expand=True)
  rf=ctk.CTkScrollableFrame(review); rf.pack(fill='both',expand=True)
  self.entry(rf,'reviewer','Reviewer name'); self.entry(rf,'decision','Chosen regime (Old / New / Pending)'); self.entry(rf,'notes','Decision reasons and evidence references')
  ctk.CTkLabel(rf,text='Optional AI: preview the anonymous prompt, review it, then send. API charges may apply.\nAI drafts cannot alter the calculation. API key stays in memory. Profiles and exports contain financial information.',justify='left').pack(pady=8)
  row=ctk.CTkFrame(rf); row.pack(fill='x')
  ctk.CTkButton(row,text='Preview AI prompt',command=self.prompt).pack(side='left',padx=5,pady=8)
  ctk.CTkButton(row,text='Copy prompt',command=self.copy_prompt).pack(side='left',padx=5)
  ctk.CTkButton(row,text='Generate AI draft',command=self.generate).pack(side='left',padx=5)
  self.entry(rf,'model','API model available to your account'); self.entry(rf,'key','OpenAI API key (optional)',secret=True)
  self.ai_box=ctk.CTkTextbox(rf,height=320); self.ai_box.pack(fill='x',pady=10)
  ctk.CTkLabel(rf,text='You may copy the prompt into an AI tool and paste its draft here. All AI text is exported as UNAPPROVED.').pack()
  self.set_profile(blank()); self.output.insert('1.0','Start with Load example / profile, open the samples folder, and choose a fictional example.\nThen review the income and eligibility tabs and click Calculate.')
 def entry(self,parent,k,label,secret=False):
  row=ctk.CTkFrame(parent,fg_color='transparent'); row.pack(fill='x',padx=10,pady=5)
  ctk.CTkLabel(row,text=label,anchor='w',width=650).pack(side='left')
  self.vars[k]=ctk.StringVar(); ctk.CTkEntry(row,textvariable=self.vars[k],width=260,show='*' if secret else '').pack(side='right',padx=5)
 def set_profile(self,p):
  defaults=blank(); defaults.update(p)
  for k in defaults:
   if k in self.vars: self.vars[k].set(defaults[k])
  for k in ('reviewer','decision','notes'): self.vars[k].set('')
  self.last_profile=None; self.draft=''; self.ai_box.delete('1.0','end')
 def profile(self):
  p=blank()
  for k in p:
   if k in self.vars: p[k]=self.vars[k].get()
  return p
 def load(self):
  path=filedialog.askopenfilename(initialdir=ROOT/'samples',filetypes=[('Profile JSON','*.json')])
  if not path:return
  try:
   p=json.loads(Path(path).read_text(encoding='utf-8'))
   if not isinstance(p,dict): raise ValueError('Profile must be a JSON object.')
   if p.get('year')!='2026-27': raise ValueError('Only AY 2026-27 profiles can be loaded.')
   self.set_profile(p); self.compute()
  except Exception as e: messagebox.showerror('Cannot load',str(e))
 def save(self):
  path=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('Profile JSON','*.json')])
  if path: Path(path).write_text(json.dumps(self.profile(),indent=2),encoding='utf-8')
 def compute(self):
  try:
   p=self.profile(); r=calculate(p)
   if self.last_profile!=p:
    self.ai_box.delete('1.0','end'); self.draft=''
    for k in ('reviewer','decision','notes'): self.vars[k].set('')
   self.last_profile=p; self.output.delete('1.0','end'); self.output.insert('1.0',narrative(p,r)); return p,r
  except Exception as e: messagebox.showerror('Check inputs',str(e)); return None
 def export(self):
  p=self.profile()
  if p!=self.last_profile:
   self.compute(); messagebox.showinfo('Recalculated','Inputs changed. Review the refreshed calculation and enter your decision before exporting.');return
  try:
   if self.vars['decision'].get() not in ('Old','New','Pending'): raise ValueError('Enter Old, New or Pending as chosen regime.')
   if not self.vars['reviewer'].get().strip() or not self.vars['notes'].get().strip(): raise ValueError('Enter reviewer and decision reasons / evidence references.')
   if self.vars['decision'].get()=='Old' and not p['old_option']: raise ValueError('Old-regime eligibility / timely election must be confirmed before choosing Old. Use Pending if unresolved.')
   path=filedialog.asksaveasfilename(defaultextension='.xlsx',filetypes=[('Excel working paper','*.xlsx')])
   if path:
    export_report(p,path,self.vars['reviewer'].get(),self.vars['decision'].get(),self.vars['notes'].get(),self.export_draft()); messagebox.showinfo('Exported','Excel working paper saved.')
  except Exception as e: messagebox.showerror('Cannot export',str(e))
 def export_draft(self):
  text=self.ai_box.get('1.0','end').strip()
  return '' if text.startswith('PROMPT PREVIEW') else text
 def prompt(self):
  self.current_prompt=None
  result=self.compute()
  if not result:return
  p,r=result
  if r['blocked']: messagebox.showerror('Blocked','Resolve scope gates first.');return
  self.current_prompt=ai_prompt(p,r); self.ai_box.delete('1.0','end'); self.ai_box.insert('1.0','PROMPT PREVIEW — replace with a draft only after generation.\n'+self.current_prompt)
 def copy_prompt(self):
  self.prompt()
  if getattr(self,'current_prompt',None): self.clipboard_clear(); self.clipboard_append(self.current_prompt)
 def generate(self):
  p=self.profile()
  try:
   r=calculate(p)
   if r['blocked']: raise ValueError('Resolve scope gates first.')
   prompt=ai_prompt(p,r)
   if not hasattr(self,'current_prompt') or prompt!=self.current_prompt:
    self.prompt(); messagebox.showinfo('Preview first','Review the displayed prompt, then click Generate AI draft again.');return
   if not self.vars['key'].get().strip() or not self.vars['model'].get().strip(): raise ValueError('Enter an API key and model, or use Copy prompt.')
   if not messagebox.askyesno('Send to OpenAI?','Send exactly the previewed financial calculation to OpenAI for an unapproved explanation?'):return
   key=self.vars['key'].get(); model=self.vars['model'].get()
   def work():
    try: result=request_draft(prompt,key,model); self.after(0,lambda:self.accept_draft(p,result['text']))
    except Exception as e:
     msg=str(e); self.after(0,lambda:messagebox.showerror('AI request failed',msg))
   threading.Thread(target=work,daemon=True).start()
  except Exception as e:messagebox.showerror('AI',str(e))
 def accept_draft(self,p,text):
  if p!=self.profile(): messagebox.showinfo('Inputs changed','The returned draft was discarded because inputs changed.');return
  self.ai_box.delete('1.0','end'); self.ai_box.insert('1.0','UNAPPROVED AI DRAFT\n'+text)
if __name__=='__main__': App().mainloop()
