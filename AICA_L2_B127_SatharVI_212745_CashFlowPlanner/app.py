"""Local desktop and command-line entry points for Construction Cash Flow Planner."""
from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from planner_workflow import prepare, save, WeeklyModel
from review import QUESTIONS, answer
from sources import InputError
from monthly_ui import MonthlyPage
from monthly import money

BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DEMO = BASE / "demo_week"
INK, RED, LIGHT, PAPER = "#19191e", "#ad1839", "#ececef", "#f3f3f5"


ASSETS = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets"


def caption(period):
    key, phase = period.split(" ", 1)
    return datetime.strptime(key, "%Y-%m").strftime("%b %Y") + " · " + phase


def proposed_file(folder, cutoff):
    first = folder / f"Cash Flow {cutoff}.xlsx"
    candidate, n = first, 2
    while candidate.exists():
        candidate = first.with_name(f"{first.stem} ({n}).xlsx")
        n += 1
    return candidate


def open_output(path):
    if os.name == "nt":
        os.startfile(str(path))
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


class Planner:
    def __init__(self, root):
        self.root = root
        self.folder = self.model = self.output = self.baseline = None
        self.busy = False
        self.monthly_page = None
        self.in_monthly = False
        self.events = queue.Queue()
        root.title("Construction Cash Flow Planner")
        self.icon = tk.PhotoImage(master=root,file=str(ASSETS/"cashflow.png"))
        root.iconphoto(True,self.icon)
        if os.name=="nt":
            root.iconbitmap(default=str(ASSETS/"cashflow.ico"))
            root.iconbitmap(str(ASSETS/"cashflow.ico"))
        root.geometry("1120x780")
        root.minsize(850, 670)
        root.configure(bg=PAPER)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7), background="white", foreground=INK)
        style.configure("Primary.TButton", background=RED, foreground="white", borderwidth=0)
        style.map("Primary.TButton", background=[("disabled", "#dedee2"), ("active", "#87122d")],
                  foreground=[("disabled", "#63636a")])
        style.configure("Treeview", font=("Segoe UI",10), rowheight=28, background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI Semibold",10), foreground="white", background="#36363d",padding=(6,5))
        style.map("Treeview",background=[("selected","#f6d9df")],foreground=[("selected",INK)])
        mast = tk.Frame(root, bg=INK, padx=24, pady=15)
        mast.grid(row=0, column=0, sticky="ew")
        tk.Frame(mast,bg="#e62c53",width=5).pack(side="left",fill="y",padx=(0,14))
        identity=tk.Frame(mast,bg=INK)
        identity.pack(side="left",fill="x",expand=True)
        tk.Label(identity, text="Construction cash flow", font=("Segoe UI Semibold", 24),
                 bg=INK, fg="white").pack(anchor="w")
        self.subtitle=tk.StringVar(value="Weekly actuals and project forecasts")
        tk.Label(identity,textvariable=self.subtitle,font=("Segoe UI",11),bg=INK,fg="#d3d3d8").pack(anchor="w")
        self.home_nav=ttk.Button(mast,text="Overview",command=self.show_overview)
        self.home_nav.pack(side="left",padx=(0,5))
        self.month_nav=ttk.Button(mast,text="Monthly cash flow",command=self.show_monthly,state="disabled")
        self.month_nav.pack(side="left")
        controls = tk.Frame(root, bg="white", padx=18, pady=12)
        controls.grid(row=1, column=0, sticky="ew", padx=20, pady=(12, 0))
        controls.columnconfigure(0, weight=1)
        tk.Label(controls, text="Weekly source folder", font=("Segoe UI Semibold",12), bg="white", fg=INK
                 ).grid(row=0,column=0, sticky="w")
        self.folder_label = tk.StringVar(value="Choose the folder that contains the weekly reports.")
        tk.Label(controls,textvariable=self.folder_label,font=("Segoe UI",10),bg="white",fg="#51515b",
                 anchor="w",wraplength=465,justify="left").grid(row=1,column=0,sticky="w",pady=(3,0))
        self.browse = ttk.Button(controls,text="Select folder…",style="Primary.TButton",command=self.browse_folder)
        self.browse.grid(row=0,column=1,rowspan=2,padx=4)
        self.demo = ttk.Button(controls,text="Use demo folder",command=lambda:self.select_folder(DEMO))
        self.demo.grid(row=0,column=2,rowspan=2)
        self.baseline_label = tk.StringVar(value="Prior workbook will be located automatically.")
        tk.Label(controls,textvariable=self.baseline_label,font=("Segoe UI",10),bg="white",fg=INK,
                 anchor="w",wraplength=510,justify="left").grid(row=2,column=0,sticky="w",pady=(7,0))
        self.choose_seed=ttk.Button(controls,text="Choose baseline…",command=self.choose_baseline,state="disabled")
        self.choose_seed.grid(row=2,column=1,columnspan=2,sticky="e",pady=(7,0))
        mid = tk.Frame(root,bg=PAPER)
        mid.grid(row=2,column=0,sticky="nsew",padx=20,pady=12)
        mid.columnconfigure(0,weight=1)
        mid.rowconfigure(2,weight=1)
        self.status = tk.StringVar(value="Waiting for a folder")
        self.status_label = tk.Label(mid,textvariable=self.status,anchor="w",bg=LIGHT,fg=INK,padx=12,pady=8,
                                     font=("Segoe UI",10),wraplength=840,justify="left")
        self.status_label.grid(row=0,column=0,sticky="ew")
        cards = tk.Frame(mid,bg=PAPER)
        cards.grid(row=1,column=0,sticky="ew",pady=8)
        cards.columnconfigure((0,1), weight=1, uniform="metric")
        self.actual_val = self.card(cards,0,"Actual closing cash · OMR")
        self.low_val = self.card(cards,1,"Lowest projected close · OMR")
        box = tk.Frame(mid,bg="white",padx=12,pady=8)
        box.grid(row=2,column=0,sticky="nsew")
        box.rowconfigure(1,weight=1)
        box.columnconfigure(0,weight=1)
        tk.Label(box,text="Cash by reporting period",font=("Segoe UI Semibold",12),fg=INK,bg="white"
                 ).grid(row=0,column=0,sticky="w",pady=(0,6))
        self.table = ttk.Treeview(box,columns=("period","opening","movement","closing"),show="headings",height=5)
        for key,label,w,align in (("period","Period",190,"w"),("opening","Opening",134,"e"),
                                   ("movement","Net movement",134,"e"),("closing","Closing",134,"e")):
            self.table.column(key,width=w,minwidth=80,anchor=align)
            self.table.heading(key,text=label,anchor=align)
        self.table.grid(row=1,column=0,sticky="nsew")
        scroll=ttk.Scrollbar(box,orient="vertical",command=self.table.yview)
        scroll.grid(row=1,column=1,sticky="ns")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.tag_configure("stripe",background="#f3f3f5")
        self.table.tag_configure("low",background="#fbe9ed",foreground="#8e1431")
        self.table.tag_configure("actual",background="#dcdce1",foreground=INK,font=("Segoe UI Semibold",10))
        self.driver = tk.StringVar(value="The preview appears after the source totals reconcile.")
        tk.Label(box,textvariable=self.driver,bg="white",fg="#55555e",wraplength=810,justify="left",anchor="w",
                 font=("Segoe UI",10)).grid(row=2,column=0,sticky="ew",pady=(8,0))
        footer = tk.Frame(root,bg=PAPER)
        footer.grid(row=3,column=0,sticky="ew",padx=20,pady=(0,15))
        footer.columnconfigure(0,weight=1)
        self.review_button=ttk.Button(footer,text="Ask about cash flow…",command=self.review,state="disabled")
        self.review_button.grid(row=0,column=0,sticky="w")
        self.open_button=ttk.Button(footer,text="Open saved workbook",command=self.open_saved,state="disabled")
        self.open_button.grid(row=0,column=1,padx=5)
        self.month_button=ttk.Button(footer,text="View monthly cash flow",command=self.show_monthly,state="disabled")
        self.month_button.grid(row=0,column=2,padx=(0,5))
        self.generate=ttk.Button(footer,text="Generate Excel…",style="Primary.TButton",command=self.generate_excel,state="disabled")
        self.generate.grid(row=0,column=3)
        self.overview_widgets=(controls,mid)
        self.show_overview()
        root.after(80,self.poll)

    def show_monthly(self):
        if not self.model or self.busy:
            return
        if self.monthly_page is None:
            self.monthly_page=MonthlyPage(self.root,self.model,self.folder)
        for widget in (*self.overview_widgets,self.review_button,self.month_button):
            widget.grid_remove()
        self.monthly_page.grid(row=1,column=0,rowspan=2,sticky="nsew",padx=20,pady=12)
        self.home_nav.configure(style="TButton")
        self.month_nav.configure(style="Primary.TButton")
        self.in_monthly=True

    def show_overview(self):
        if self.monthly_page is not None:
            self.monthly_page.grid_remove()
        for widget in (*self.overview_widgets,self.review_button,self.month_button):
            widget.grid()
        self.month_nav.configure(style="TButton")
        self.home_nav.configure(style="Primary.TButton")
        self.in_monthly=False

    def card(self, parent, index, name):
        color=INK if index==0 else RED
        pane=tk.Frame(parent,bg=color,padx=14,pady=10)
        pane.grid(row=0,column=index,sticky="ew",padx=(0,4) if index==0 else (4,0))
        tk.Label(pane,text=name,fg="#f3eef0",bg=color,font=("Segoe UI",10)).pack(anchor="w")
        value=tk.StringVar(value="—")
        tk.Label(pane,textvariable=value,fg="white",bg=color,font=("Segoe UI Semibold",17)).pack(anchor="w")
        return value

    def browse_folder(self):
        selected=filedialog.askdirectory(parent=self.root,title="Select weekly source folder",
                                         initialdir=str(self.folder or BASE),mustexist=True)
        if selected:
            self.select_folder(Path(selected))

    def choose_baseline(self):
        if not self.folder or self.busy:return
        seed=filedialog.askopenfilename(parent=self.root,title="Choose the preceding week's cash flow",
                                        initialdir=str(self.folder.parent),filetypes=[("Excel workbook","*.xlsx")])
        if seed:self.select_folder(self.folder, Path(seed))

    def reset_preview(self):
        self.show_overview()
        if self.monthly_page is not None:
            self.monthly_page.destroy()
            self.monthly_page=None
        self.month_button.configure(state="disabled")
        self.month_nav.configure(state="disabled")
        self.subtitle.set("Weekly actuals and project forecasts")
        self.model=self.output=None
        self.generate.configure(state="disabled")
        self.review_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.actual_val.set("—")
        self.low_val.set("—")
        self.driver.set("The preview appears after the source totals reconcile.")
        self.table.delete(*self.table.get_children())

    def select_folder(self, folder, baseline=None):
        if self.busy:
            return
        self.folder=Path(folder).resolve()
        self.baseline=baseline
        self.folder_label.set(str(self.folder))
        self.baseline_label.set("Prior workbook  ·  "+str(baseline or "Locating the preceding workbook…"))
        self.reset_preview()
        self.run("Checking source dates and reconciling balances…",lambda: ("preview",prepare(self.folder,self.baseline),None))

    def run(self, text, fn):
        self.busy=True
        for widget in (self.generate,self.browse,self.demo,self.open_button,self.review_button,self.choose_seed,self.month_button,self.month_nav):
            widget.configure(state="disabled")
        self.status.set(text)
        self.status_label.configure(bg=LIGHT,fg=INK)
        def work():
            try:
                self.events.put(fn())
            except Exception as exc:
                self.events.put(("error",str(exc),None))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            stage,result,out=self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy=False
            self.browse.configure(state="normal")
            self.demo.configure(state="normal")
            self.choose_seed.configure(state="normal")
            if stage=="error":
                self.reset_preview()
                self.status.set(result)
                self.baseline_label.set("Prior workbook  ·  "+str(self.baseline or "Automatic selection"))
                self.status_label.configure(bg="#fbe5ea",fg="#86142e")
            else:
                self.present(result)
                self.output=out
                if out:
                    self.open_button.configure(state="normal")
                    self.status.set(f"Workbook saved  ·  {out}")
        self.root.after(80,self.poll)

    def present(self, model):
        self.model=model
        self.month_button.configure(state="normal")
        self.month_nav.configure(state="normal")
        self.subtitle.set(f"{model.company}   ·   Actual to {model.cutoff:%d %B %Y}")
        self.generate.configure(state="normal")
        self.review_button.configure(state="normal")
        self.table.delete(*self.table.get_children())
        forecast=[model.forecast(m) for m in model.months]
        low=min(forecast,key=model.closing.get)
        self.actual_val.set(money(model.closing[model.actual]))
        self.low_val.set(money(model.closing[low])+"   /   "+low[:7])
        for i,p in enumerate(model.periods):
            self.table.insert("","end",iid=p,values=(caption(p),money(model.opening[p]),
                              money(model.closing[p]-model.opening[p]),money(model.closing[p])),
                              tags=("actual",) if p==model.actual else ("low",) if model.closing[p]<0 else ("stripe",) if i%2 else ())
        self.table.yview_moveto(max(0,len(model.periods[:model.periods.index(model.actual)])-1)/len(model.periods))
        if isinstance(model,WeeklyModel):
            self.baseline_label.set(f"Prior workbook  ·  {model.files.baseline.parent.name} / {model.files.baseline.name}")
            self.review_button.configure(text="Sources and review notes…")
            self.generate.configure(text="Save draft Excel…" if model.notes else "Generate Excel…")
            self.driver.set(f"Output  ·  {model.files.original.name}     |     Input reports  ·  {len(model.files.paths)}"
                            f"     |     Actual cutoff  ·  {model.cutoff:%d %b %Y}")
            self.status.set(("Draft — "+model.notes[0]) if model.notes else
                            f"Reconciled through {model.cutoff:%d %b %Y}   ·   {len(model.checks)} checks   ·   Ready to export")
            return
        self.baseline_label.set(f"Starting workbook  ·  {model.sources['Model'].name}")
        self.review_button.configure(text="Ask about cash flow…")
        self.generate.configure(text="Generate Excel…")
        items=sorted(((e.value,e) for e in model.entries if not e.reason and e.period==low and e.value<0),
                     key=lambda pair: pair[0])
        self.driver.set("Largest payments in the low period: " + "   ·   ".join(
            f"{e.category} {money(value)} [{e.reference}]" for value,e in items[:2]) if items else
            "There are no scheduled payments in the lowest forecast period.")
        self.status.set(f"{model.company}   ·   Through {model.cutoff:%d %b %Y}   ·   "
                        f"{len(model.sources)} sources   ·   {len(model.checks)} checks passed")

    def generate_excel(self):
        if self.busy or not self.model:
            return
        if isinstance(self.model,WeeklyModel):
            default=self.model.files.original
            suffix="-DRAFT" if self.model.notes else "-review" if default.exists() else ""
            default=default.with_stem(default.stem+suffix)
            n=2
            first=default
            while default.exists():
                default=first.with_stem(first.stem+f"-{n}")
                n+=1
        else:
            default=proposed_file(self.folder.parent,self.model.cutoff)
        path=filedialog.asksaveasfilename(parent=self.root,title="Save cash flow workbook",initialdir=str(default.parent),
                                         initialfile=default.name,defaultextension=".xlsx",filetypes=[("Excel workbook","*.xlsx")])
        if not path:
            return
        old=self.model
        def generate():
            current=prepare(self.folder,self.baseline)
            if {k:v.digest for k,v in current.sources.items()} != {k:v.digest for k,v in old.sources.items()}:
                raise InputError("The inputs changed after preview. Select the folder again to review the new figures.")
            if current.closing!=old.closing or getattr(current,"notes",[])!=getattr(old,"notes",[]):
                raise InputError("The forecast or management decisions changed. Select the folder again to review them.")
            return "saved",current,save(current,path)
        self.run("Preparing and checking the Excel workbook…",generate)

    def review(self):
        if self.busy or not self.model:
            return
        model = self.model
        win = tk.Toplevel(self.root)
        if isinstance(model,WeeklyModel):
            win.title("Sources and review notes")
            win.geometry("800x560")
            box=tk.Text(win,wrap="word",padx=18,pady=16,font=("Segoe UI",11),bg=PAPER,fg=INK)
            box.pack(fill="both",expand=True)
            box.insert("1.0","\n\n".join(model.evidence))
            box.configure(state="disabled")
            return
        win.title("Review cash flow")
        win.geometry("690x460")
        win.columnconfigure(0, weight=1)
        win.rowconfigure(2, weight=1)
        tk.Label(win, text="Ask a question about the reconciled forecast", anchor="w",
                 font=("Segoe UI Semibold", 14)).grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=12)
        examples = [items[0] for items in QUESTIONS.values()]
        question = ttk.Combobox(win, values=examples, font=("Segoe UI", 11))
        question.grid(row=1, column=0, sticky="ew", padx=(16, 5))
        question.set(examples[0])
        result = tk.Text(win, wrap="word", font=("Segoe UI", 11), padx=12, pady=12, bg="white", fg=INK)
        result.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=16, pady=12)
        def show(event=None):
            result.configure(state="normal")
            result.delete("1.0", "end")
            result.insert("1.0", answer(model, question.get()))
            result.configure(state="disabled")
        ttk.Button(win, text="Answer", command=show).grid(row=1, column=1, padx=(0, 16))
        question.bind("<<ComboboxSelected>>", show)
        question.bind("<Return>", show)
        show()

    def open_saved(self):
        try:
            open_output(self.output)
        except OSError as exc:
            messagebox.showerror("Could not open the workbook",str(exc),parent=self.root)


def main():
    parser=argparse.ArgumentParser(description="Construction Cash Flow Planner")
    parser.add_argument("--input",type=Path,help="Weekly test folder")
    parser.add_argument("--output",type=Path,help="New .xlsx workbook; requires --input")
    parser.add_argument("--baseline",type=Path,help="Explicit prior dated CF workbook")
    args=parser.parse_args()
    if args.output and not args.input:
        parser.error("--output requires --input")
    if args.input:
        try:
            model=prepare(args.input,args.baseline)
            if args.output:
                save(model,args.output)
            for period,value in model.closing.items():
                print(f"{period:20} {money(value):>15} OMR")
            return 0
        except Exception as exc:
            print(str(exc),file=sys.stderr)
            return 1
    root=tk.Tk()
    Planner(root)
    root.mainloop()
    return 0


if __name__=="__main__":
    raise SystemExit(main())
