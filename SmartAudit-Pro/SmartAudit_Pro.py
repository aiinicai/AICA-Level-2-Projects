# SmartAudit Pro - Audit Sample Selector
# ICAI Level 2 Capstone Project
# Desktop app: Excel/CSV upload, multiple sampling methods, risk scoring,
# dashboard charts, indicative sample-size calculator, Excel + PDF audit reports.

import os, sys, csv, math, random, statistics, subprocess, importlib, re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP="SmartAudit Pro - Audit Sample Selector"

def ensure(pkg, import_name=None):
    name=import_name or pkg
    try: return importlib.import_module(name)
    except ImportError:
        try:
            subprocess.check_call([sys.executable,"-m","pip","install",pkg])
            return importlib.import_module(name)
        except Exception as e:
            raise RuntimeError(f"Required package '{pkg}' could not be installed.\n{e}")

openpyxl=ensure("openpyxl")
reportlab=ensure("reportlab")
mpl=ensure("matplotlib")
mpl.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import mm

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP); self.geometry("1320x820"); self.minsize(1120,700)
        self.rows=[]; self.headers=[]; self.samples=[]; self.risk_rows=[]
        self.file=tk.StringVar(); self.sheet=tk.StringVar(); self.amount=tk.StringVar()
        self.datecol=tk.StringVar(); self.usercol=tk.StringVar(); self.narrcol=tk.StringVar()
        self.method=tk.StringVar(value="Risk-based")
        self.threshold=tk.StringVar(value="1000000"); self.n=tk.StringVar(value="25")
        self.seed=tk.StringVar(value="42"); self.conf=tk.StringVar(value="95")
        self.err=tk.StringVar(value="5"); self.expected=tk.StringVar(value="5")
        self.status=tk.StringVar(value="Ready"); self.kpi=tk.StringVar(value="Load a population to begin.")
        self._style(); self._ui()

    def _style(self):
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except:pass
        s.configure("Title.TLabel",font=("Segoe UI",22,"bold"))
        s.configure("H.TLabel",font=("Segoe UI",10,"bold"))
        s.configure("Accent.TButton",font=("Segoe UI",10,"bold"),padding=7)

    def _ui(self):
        top=ttk.Frame(self,padding=14); top.pack(fill="both",expand=True)
        ttk.Label(top,text="SmartAudit Pro",style="Title.TLabel").pack(anchor="w")
        ttk.Label(top,text="Audit Sampling & Population Analytics | ICAI Level 2 Capstone").pack(anchor="w")
        nb=ttk.Notebook(top); nb.pack(fill="both",expand=True,pady=10)
        self.t1=ttk.Frame(nb,padding=12); self.t2=ttk.Frame(nb,padding=12); self.t3=ttk.Frame(nb,padding=12)
        nb.add(self.t1,text="Population & Sampling"); nb.add(self.t2,text="Dashboard"); nb.add(self.t3,text="Sample Size Calculator")
        self._sampling_tab(); self._dashboard_tab(); self._calc_tab()
        ttk.Label(top,textvariable=self.status,relief="sunken",anchor="w").pack(fill="x")

    def _sampling_tab(self):
        f=ttk.LabelFrame(self.t1,text="1. Load CSV / Excel",padding=10); f.pack(fill="x")
        ttk.Entry(f,textvariable=self.file,state="readonly").pack(side="left",fill="x",expand=True,padx=(0,8))
        ttk.Button(f,text="Browse",command=self.load).pack(side="left")
        ttk.Button(f,text="Create Demo Excel",command=self.demo).pack(side="left",padx=6)

        m=ttk.LabelFrame(self.t1,text="2. Map fields & set sampling",padding=10); m.pack(fill="x",pady=8)
        labels=[("Amount",self.amount),("Date",self.datecol),("User",self.usercol),("Narration",self.narrcol)]
        self.combos=[]
        for j,(lab,var) in enumerate(labels):
            ttk.Label(m,text=lab).grid(row=0,column=j*2,sticky="w")
            c=ttk.Combobox(m,textvariable=var,state="readonly",width=18); c.grid(row=0,column=j*2+1,padx=(4,12),sticky="ew"); self.combos.append(c)
        ttk.Label(m,text="Method").grid(row=1,column=0,sticky="w",pady=(8,0))
        ttk.Combobox(m,textvariable=self.method,state="readonly",values=["Random","Systematic","Stratified","Risk-based"],width=18).grid(row=1,column=1,sticky="ew",padx=(4,12),pady=(8,0))
        ttk.Label(m,text="Threshold").grid(row=1,column=2,sticky="w",pady=(8,0))
        ttk.Entry(m,textvariable=self.threshold,width=15).grid(row=1,column=3,sticky="ew",padx=(4,12),pady=(8,0))
        ttk.Label(m,text="Sample size").grid(row=1,column=4,sticky="w",pady=(8,0))
        ttk.Entry(m,textvariable=self.n,width=10).grid(row=1,column=5,sticky="ew",padx=(4,12),pady=(8,0))
        ttk.Label(m,text="Seed").grid(row=1,column=6,sticky="w",pady=(8,0))
        ttk.Entry(m,textvariable=self.seed,width=10).grid(row=1,column=7,sticky="ew",pady=(8,0))
        for i in range(8):m.columnconfigure(i,weight=1)

        a=ttk.Frame(self.t1); a.pack(fill="x")
        ttk.Button(a,text="Analyze Population",command=self.analyze).pack(side="left")
        ttk.Button(a,text="Select Samples",command=self.select,style="Accent.TButton").pack(side="left",padx=6)
        ttk.Button(a,text="Export Excel Report",command=self.export_excel).pack(side="left")
        ttk.Button(a,text="Export PDF Report",command=self.export_pdf).pack(side="left",padx=6)
        ttk.Label(self.t1,textvariable=self.kpi,style="H.TLabel").pack(anchor="w",pady=7)
        box=ttk.Frame(self.t1); box.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(box,show="headings"); ys=ttk.Scrollbar(box,orient="vertical",command=self.tree.yview); xs=ttk.Scrollbar(box,orient="horizontal",command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set); self.tree.grid(row=0,column=0,sticky="nsew"); ys.grid(row=0,column=1,sticky="ns"); xs.grid(row=1,column=0,sticky="ew")
        box.rowconfigure(0,weight=1); box.columnconfigure(0,weight=1)

    def _dashboard_tab(self):
        ttk.Label(self.t2,text="Dashboard refreshes after analysis / sampling.",style="H.TLabel").pack(anchor="w")
        self.fig=Figure(figsize=(10,5),dpi=100); self.ax1=self.fig.add_subplot(121); self.ax2=self.fig.add_subplot(122)
        self.canvas=FigureCanvasTkAgg(self.fig,master=self.t2); self.canvas.get_tk_widget().pack(fill="both",expand=True)

    def _calc_tab(self):
        f=ttk.LabelFrame(self.t3,text="Indicative attribute sample-size calculator",padding=15); f.pack(anchor="nw",fill="x")
        fields=[("Population size",self.n),("Confidence level (%)",self.conf),("Tolerable deviation (%)",self.err),("Expected deviation (%)",self.expected)]
        # separate population variable so sampling n is not overwritten
        self.popcalc=tk.StringVar(value="1000"); fields[0]=("Population size",self.popcalc)
        for i,(lab,var) in enumerate(fields):
            ttk.Label(f,text=lab).grid(row=i,column=0,sticky="w",pady=6); ttk.Entry(f,textvariable=var,width=18).grid(row=i,column=1,padx=10,pady=6)
        ttk.Button(f,text="Calculate",command=self.calc_size,style="Accent.TButton").grid(row=4,column=0,columnspan=2,pady=10)
        self.calc_result=tk.StringVar(value="Indicative sample size will appear here.")
        ttk.Label(f,textvariable=self.calc_result,font=("Segoe UI",12,"bold"),wraplength=750).grid(row=5,column=0,columnspan=3,sticky="w")
        note=("Educational calculator using a finite-population proportion formula. It is not an SA 530 prescribed table. "
              "The auditor must determine sample size considering audit objective, assessed risk, tolerable/expected deviation, "
              "population characteristics and professional judgement.")
        ttk.Label(f,text=note,wraplength=900,foreground="#555").grid(row=6,column=0,columnspan=3,sticky="w",pady=12)

    @staticmethod
    def num(v):
        if v is None:return 0.0
        s=str(v).strip().replace(",","").replace("₹","").replace("(","-").replace(")","")
        try:return float(s)
        except:return 0.0

    def load(self,path=None):
        if not path:path=filedialog.askopenfilename(filetypes=[("Excel/CSV","*.xlsx *.xlsm *.csv"),("All files","*.*")])
        if not path:return
        try:
            if path.lower().endswith(".csv"):
                with open(path,encoding="utf-8-sig",newline="") as fh:
                    r=csv.DictReader(fh); self.headers=r.fieldnames or []; self.rows=list(r)
            else:
                wb=load_workbook(path,data_only=True,read_only=True); ws=wb[wb.sheetnames[0]]
                data=list(ws.iter_rows(values_only=True)); self.headers=[str(x) if x is not None else f"Column{i+1}" for i,x in enumerate(data[0])]
                self.rows=[dict(zip(self.headers,row)) for row in data[1:] if any(v is not None for v in row)]
            if not self.rows:raise ValueError("No data rows found.")
            self.file.set(path)
            for c in self.combos:c["values"]=[""]+self.headers
            def pick(keys,default=""):
                return next((h for h in self.headers if any(k in h.lower() for k in keys)),default)
            self.amount.set(pick(["amount","value","debit","credit"],self.headers[-1])); self.datecol.set(pick(["date"]))
            self.usercol.set(pick(["user","created by","posted by"])); self.narrcol.set(pick(["narration","description","particular"]))
            self.show(self.rows[:500]); self.status.set(f"Loaded {len(self.rows):,} records.")
            self.analyze()
        except Exception as e:messagebox.showerror(APP,str(e))

    def risk_score(self,r):
        score=0; reasons=[]; v=abs(self.num(r.get(self.amount.get())))
        th=self.num(self.threshold.get())
        if th and v>=th:score+=4; reasons.append("Above threshold")
        if v and abs(v-round(v/100000)*100000)<1:score+=2; reasons.append("Round amount")
        d=str(r.get(self.datecol.get(),""))
        dt=None
        for fmt in ("%Y-%m-%d %H:%M:%S","%Y-%m-%d","%d-%m-%Y","%d/%m/%Y","%m/%d/%Y"):
            try:dt=datetime.strptime(d.split(".")[0],fmt);break
            except:pass
        if dt:
            if dt.weekday()>=5:score+=2; reasons.append("Weekend")
            if dt.month==3 and dt.day>=25:score+=2; reasons.append("Year-end")
        nar=str(r.get(self.narrcol.get(),"")).lower()
        if any(x in nar for x in ["manual","adjustment","provision","reversal","misc","suspense"]):score+=2; reasons.append("Sensitive narration")
        return score,", ".join(reasons) or "No rule triggered"

    def analyze(self):
        if not self.rows:return
        vals=[self.num(r.get(self.amount.get())) for r in self.rows]
        self.risk_rows=[]
        for i,r in enumerate(self.rows):
            sc,why=self.risk_score(r); self.risk_rows.append((i,r,sc,why))
        high=sum(1 for _,_,s,_ in self.risk_rows if s>=4)
        self.kpi.set(f"Population {len(vals):,} | Absolute value {sum(map(abs,vals)):,.2f} | Average {statistics.mean(vals):,.2f} | Max abs {max(map(abs,vals)):,.2f} | Higher-risk items {high:,}")
        self.refresh_dashboard(); self.status.set("Population analyzed.")

    def select(self):
        if not self.rows:return messagebox.showwarning(APP,"Load a population first.")
        try:
            n=max(1,int(self.n.get())); rng=random.Random(int(self.seed.get())); method=self.method.get()
            indexed=list(enumerate(self.rows)); selected=[]
            if method=="Random":
                selected=rng.sample(indexed,min(n,len(indexed)))
            elif method=="Systematic":
                N=len(indexed); n=min(n,N); interval=N/n; start=rng.random()*interval
                ids=[]; x=start
                while len(ids)<n and int(x)<N:ids.append(int(x)); x+=interval
                selected=[indexed[i] for i in sorted(set(ids))]
            elif method=="Stratified":
                vals=[abs(self.num(r.get(self.amount.get()))) for _,r in indexed]
                ordered=sorted(indexed,key=lambda z:abs(self.num(z[1].get(self.amount.get()))))
                N=len(ordered); q1=N//3; strata=[ordered[:q1],ordered[q1:2*q1],ordered[2*q1:]]
                alloc=[max(1,round(n*len(s)/N)) if s else 0 for s in strata]
                while sum(alloc)>n:
                    j=max(range(3),key=lambda x:alloc[x]); alloc[j]-=1
                while sum(alloc)<min(n,N):
                    choices=[j for j,s in enumerate(strata) if alloc[j]<len(s)]
                    if not choices:break
                    alloc[choices[-1]]+=1
                for s,k in zip(strata,alloc): selected += rng.sample(s,min(k,len(s)))
            else: # risk-based: highest risk, then highest value; fill randomly if needed
                ranked=sorted(self.risk_rows,key=lambda z:(z[2],abs(self.num(z[1].get(self.amount.get())))),reverse=True)
                selected=[(i,r) for i,r,sc,why in ranked[:min(n,len(ranked))]]
            out=[]
            for i,r in selected:
                sc,why=self.risk_score(r); x=dict(r); x["Selection Method"]=method; x["Risk Score"]=sc; x["Risk Reasons"]=why; out.append(x)
            self.samples=out; self.show(out)
            pop=sum(abs(self.num(r.get(self.amount.get()))) for r in self.rows); sam=sum(abs(self.num(r.get(self.amount.get()))) for r in out)
            self.kpi.set(f"Selected {len(out):,} of {len(self.rows):,} | Method: {method} | Absolute value coverage: {(sam/pop*100 if pop else 0):.2f}%")
            self.refresh_dashboard(); self.status.set("Sample selection completed.")
        except Exception as e:messagebox.showerror(APP,f"Sampling failed:\n{e}")

    def show(self,rows):
        self.tree.delete(*self.tree.get_children())
        extras=["Selection Method","Risk Score","Risk Reasons"] if rows and "Selection Method" in rows[0] else []
        cols=extras+self.headers; self.tree["columns"]=cols
        for c in cols:self.tree.heading(c,text=c); self.tree.column(c,width=145,anchor="w")
        for r in rows[:3000]:self.tree.insert("","end",values=[r.get(c,"") for c in cols])

    def refresh_dashboard(self):
        self.ax1.clear(); self.ax2.clear()
        if not self.rows:self.canvas.draw();return
        vals=[abs(self.num(r.get(self.amount.get()))) for r in self.rows]
        self.ax1.hist(vals,bins=min(12,max(3,int(math.sqrt(len(vals)))))); self.ax1.set_title("Population value distribution"); self.ax1.set_xlabel("Absolute amount"); self.ax1.set_ylabel("Transactions")
        scores=[self.risk_score(r)[0] for r in self.rows]; cats=["Low (0-1)","Medium (2-3)","High (4+)"]; counts=[sum(s<=1 for s in scores),sum(2<=s<=3 for s in scores),sum(s>=4 for s in scores)]
        self.ax2.bar(cats,counts); self.ax2.set_title("Risk-rule distribution"); self.ax2.tick_params(axis="x",rotation=15)
        self.fig.tight_layout(); self.canvas.draw()

    def calc_size(self):
        try:
            N=int(self.popcalc.get()); conf=float(self.conf.get()); e=float(self.err.get())/100; p=float(self.expected.get())/100
            z={90:1.645,95:1.96,99:2.576}.get(round(conf),1.96)
            p=max(.005,min(.5,p)); e=max(.001,e)
            n0=(z*z*p*(1-p))/(e*e); nf=n0/(1+(n0-1)/N); ans=min(N,math.ceil(nf))
            self.calc_result.set(f"Indicative calculated sample size: {ans} items (population {N:,}). Use as planning support only, not as an SA 530 prescribed sample size.")
        except Exception as e:messagebox.showerror(APP,f"Enter valid calculator inputs.\n{e}")

    def export_excel(self):
        if not self.samples:return messagebox.showwarning(APP,"Select samples first.")
        path=filedialog.asksaveasfilename(defaultextension=".xlsx",initialfile=f"SmartAudit_Report_{datetime.now():%Y%m%d_%H%M}.xlsx",filetypes=[("Excel","*.xlsx")])
        if not path:return
        wb=Workbook(); ws=wb.active; ws.title="Audit Summary"
        navy="1F4E78"; light="D9EAF7"; thin=Side(style="thin",color="D9E1F2")
        ws.merge_cells("A1:F1"); ws["A1"]="SmartAudit Pro - Audit Sampling Report"; ws["A1"].font=Font(size=18,bold=True,color="FFFFFF"); ws["A1"].fill=PatternFill("solid",fgColor=navy); ws["A1"].alignment=Alignment(horizontal="center")
        metrics=[("Population records",len(self.rows)),("Sampling method",self.method.get()),("Selected samples",len(self.samples)),("Threshold",self.threshold.get()),("Random seed",self.seed.get()),("Generated",datetime.now().strftime("%d-%m-%Y %H:%M"))]
        for i,(a,b) in enumerate(metrics,3):ws.cell(i,1,a).font=Font(bold=True); ws.cell(i,2,b)
        rs=wb.create_sheet("Selected Samples"); cols=["Selection Method","Risk Score","Risk Reasons"]+self.headers
        rs.append(cols)
        for r in self.samples:rs.append([r.get(c,"") for c in cols])
        for cell in rs[1]:cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor=navy); cell.alignment=Alignment(wrap_text=True)
        rs.freeze_panes="A2"; rs.auto_filter.ref=rs.dimensions
        for col in rs.columns:
            letter=col[0].column_letter; rs.column_dimensions[letter].width=min(32,max(11,max(len(str(c.value or "")) for c in col[:200])+2))
        # Risk summary + chart
        scores=[self.risk_score(r)[0] for r in self.rows]; summary=[("Low (0-1)",sum(s<=1 for s in scores)),("Medium (2-3)",sum(2<=s<=3 for s in scores)),("High (4+)",sum(s>=4 for s in scores))]
        ws["D3"]="Risk category"; ws["E3"]="Count"
        for c in ws[3][3:5]:c.font=Font(bold=True,color="FFFFFF"); c.fill=PatternFill("solid",fgColor=navy)
        for j,(a,b) in enumerate(summary,4):ws.cell(j,4,a);ws.cell(j,5,b)
        ch=BarChart(); ch.title="Population risk distribution"; ch.y_axis.title="Count"; ch.add_data(Reference(ws,min_col=5,min_row=3,max_row=6),titles_from_data=True); ch.set_categories(Reference(ws,min_col=4,min_row=4,max_row=6)); ws.add_chart(ch,"D8")
        notes=wb.create_sheet("Methodology")
        methodology=[
            ["Area","Description"],
            ["Random","Simple random selection using a reproducible seed."],
            ["Systematic","Random start followed by approximately equal intervals through the population."],
            ["Stratified","Population sorted by absolute value and divided into three value strata; samples allocated broadly in proportion to stratum size."],
            ["Risk-based","Ranks items using configurable-style rules: above threshold, round values, weekend/year-end posting and sensitive narration."],
            ["Important","The tool supports audit judgement; it does not replace SA 530 requirements or professional judgement. Risk-based selection is targeted testing and should not be represented as statistical sampling."]
        ]
        for row in methodology:notes.append(row)
        for c in notes[1]:c.font=Font(bold=True,color="FFFFFF");c.fill=PatternFill("solid",fgColor=navy)
        notes.column_dimensions["A"].width=20;notes.column_dimensions["B"].width=100
        for row in notes.iter_rows(): 
            for c in row:c.alignment=Alignment(wrap_text=True,vertical="top")
        wb.save(path); self.status.set(f"Excel report exported: {path}"); messagebox.showinfo(APP,"Excel audit report created.")

    def export_pdf(self):
        if not self.samples:return messagebox.showwarning(APP,"Select samples first.")
        path=filedialog.asksaveasfilename(defaultextension=".pdf",initialfile=f"SmartAudit_Report_{datetime.now():%Y%m%d_%H%M}.pdf",filetypes=[("PDF","*.pdf")])
        if not path:return
        doc=SimpleDocTemplate(path,pagesize=landscape(A4),rightMargin=12*mm,leftMargin=12*mm,topMargin=12*mm,bottomMargin=12*mm)
        styles=getSampleStyleSheet(); title=ParagraphStyle("T",parent=styles["Title"],alignment=TA_CENTER,textColor=colors.HexColor("#1F4E78"))
        story=[Paragraph("SmartAudit Pro - Audit Sampling Report",title),Spacer(1,5*mm)]
        summary=[["Metric","Result"],["Population records",f"{len(self.rows):,}"],["Sampling method",self.method.get()],["Selected samples",str(len(self.samples))],["Threshold",self.threshold.get()],["Generated",datetime.now().strftime("%d-%m-%Y %H:%M")]]
        t=Table(summary,colWidths=[55*mm,80*mm]); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1F4E78")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.3,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP")]))
        story += [t,Spacer(1,5*mm),Paragraph("Methodology and limitation",styles["Heading2"]),Paragraph("The application supports population analysis and sample selection. Risk-based selection is targeted testing, not statistical sampling. Sample size and selection must be designed by the auditor having regard to the audit objective, population characteristics, sampling risk and professional judgement under SA 530.",styles["BodyText"]),Spacer(1,5*mm),Paragraph("Selected samples",styles["Heading2"])]
        showcols=["Selection Method","Risk Score","Risk Reasons"]+self.headers[:5]
        data=[[Paragraph(str(c),styles["BodyText"]) for c in showcols]]
        for r in self.samples[:100]:data.append([Paragraph(str(r.get(c,""))[:120],styles["BodyText"]) for c in showcols])
        widths=[25*mm,18*mm,42*mm]+[30*mm]*min(5,len(self.headers))
        tab=Table(data,colWidths=widths,repeatRows=1); tab.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1F4E78")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.25,colors.lightgrey),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),7)]))
        story.append(tab)
        if len(self.samples)>100:story.append(Paragraph(f"PDF displays first 100 of {len(self.samples)} selected items. Full population is available in the Excel export.",styles["BodyText"]))
        doc.build(story); self.status.set(f"PDF report exported: {path}"); messagebox.showinfo(APP,"PDF audit report created.")

    def demo(self):
        path=filedialog.asksaveasfilename(defaultextension=".xlsx",initialfile="SmartAudit_Demo.xlsx",filetypes=[("Excel","*.xlsx")])
        if not path:return
        wb=Workbook();ws=wb.active;ws.title="GL Population";ws.append(["Voucher No","Date","Vendor","User","Narration","Amount"])
        rng=random.Random(8); vendors=["ABC Ltd","XYZ Pvt Ltd","PQR Services","Alpha Traders","Nova Solutions"]; users=["user01","user02","user03","admin"]
        for i in range(1,301):
            day=rng.randint(1,31); date=datetime(2026,3,day); amt=rng.randint(5,900)*1000
            nar=rng.choice(["Purchase invoice","Service expense","Freight","Regular adjustment","Office expense"])
            if i in (17,71,155,250):amt=rng.choice([1500000,2500000,5000000]);nar="Manual year-end adjustment"
            ws.append([f"JV{i:04}",date,vendors[i%len(vendors)],rng.choice(users),nar,amt])
        ws.freeze_panes="A2"; wb.save(path); self.load(path)

if __name__=="__main__":
    App().mainloop()
