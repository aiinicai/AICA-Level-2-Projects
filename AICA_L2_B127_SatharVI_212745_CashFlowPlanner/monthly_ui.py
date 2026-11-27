"""Monthly desktop worksheet, comparison panel and cell-level supporting detail."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from monthly import Monthly, OPEN, CLOSE, IN, OUT, FUND, MOVE, money
from weekly_model import WeeklyModel

INK, RED, PAPER = "#19191e", "#ad1839", "#f3f3f5"
FONT = ("Segoe UI",10)
BOLD = ("Segoe UI Semibold",10)


class MonthlyPage(tk.Frame):
    def __init__(self,parent,model,folder):
        super().__init__(parent,bg=PAPER)
        self.data=Monthly(model)
        self.folder=folder
        self.combined=tk.BooleanVar(self,value=False)
        self.drawer=None
        self.mode=None
        self.columnconfigure(0,weight=1)
        self.rowconfigure(3,weight=1)
        header=tk.Frame(self,bg=PAPER)
        header.grid(row=0,column=0,sticky="ew")
        tk.Label(header,text="Monthly cash flow",font=("Segoe UI Semibold",18),bg=PAPER,fg=INK).pack(side="left")
        self.toggle=ttk.Checkbutton(header,text="Combine current month",variable=self.combined,command=self.toggle_month)
        self.toggle.pack(side="right")
        tools=tk.Frame(self,bg=PAPER)
        tools.grid(row=1,column=0,sticky="ew",pady=(3,8))
        self.compare_button=ttk.Button(tools,text="Compare with previous week",command=self.show_compare)
        self.compare_button.pack(side="left")
        self.detail_button=ttk.Button(tools,text="View supporting detail",command=self.show_detail)
        self.detail_button.pack(side="left",padx=6)
        self.groups=self.data.groups(False)
        self.column=next(i for i,g in enumerate(self.groups) if model.actual in g)
        self.row=self.data.rows.index(OPEN)
        self.selected=tk.StringVar(self)
        self.gridbox=tk.Frame(self,bg="white",bd=1,relief="solid")
        self.gridbox.grid(row=3,column=0,sticky="nsew")
        self.gridbox.rowconfigure(1,weight=1)
        self.gridbox.columnconfigure(1,weight=1)
        self.cw=max(145,int(self.winfo_fpixels("1i")*1.44))
        self.rh=max(28,int(self.winfo_fpixels("1i")*.28))
        self.hh=self.rh*2
        self.lw=max(225,int(self.winfo_fpixels("1i")*2.22))
        self.names=tk.Canvas(self.gridbox,width=self.lw,height=0,bg="white",highlightthickness=0)
        self.head=tk.Canvas(self.gridbox,height=self.hh,width=0,bg=INK,highlightthickness=0)
        self.cells=tk.Canvas(self.gridbox,width=0,height=0,bg="white",highlightthickness=0,takefocus=True)
        tk.Label(self.gridbox,text="Cash-flow item  ·  "+model.currency,font=BOLD,anchor="w",padx=11,
                 bg=INK,fg="white").grid(row=0,column=0,sticky="nsew")
        self.names.grid(row=1,column=0,sticky="ns")
        self.head.grid(row=0,column=1,sticky="ew")
        self.cells.grid(row=1,column=1,sticky="nsew")
        vert=ttk.Scrollbar(self.gridbox,orient="vertical",command=self.cells.yview)
        hori=ttk.Scrollbar(self.gridbox,orient="horizontal",command=self.cells.xview)
        vert.grid(row=1,column=2,sticky="ns")
        hori.grid(row=2,column=1,sticky="ew")
        def sync_x(first,last):
            hori.set(first,last)
            self.head.xview_moveto(first)
        def sync_y(first,last):
            vert.set(first,last)
            self.names.yview_moveto(first)
        self.cells.configure(xscrollcommand=sync_x,yscrollcommand=sync_y)
        for widget in (self.names,self.cells,self.head):
            widget.bind("<MouseWheel>",self.wheel)
            widget.bind("<Shift-MouseWheel>",lambda e: self.cells.xview_scroll(-int(e.delta/120),"units"))
        self.cells.bind("<Button-1>",self.click)
        self.cells.bind("<Double-1>",lambda e:self.show_detail())
        self.names.bind("<Button-1>",lambda e:self.select(int(self.names.canvasy(e.y)//self.rh),self.column))
        for key,dr,dc in (("Up",-1,0),("Down",1,0),("Left",0,-1),("Right",0,1)):
            self.cells.bind("<"+key+">",lambda e,r=dr,c=dc:self.select(self.row+r,self.column+c,True))
        self.cells.bind("<Return>",lambda e:self.show_detail())
        tk.Label(self,textvariable=self.selected,anchor="w",font=FONT,bg=PAPER,fg=INK).grid(row=4,column=0,sticky="ew",pady=(6,0))
        self.paint()
        self.after_idle(self.focus_period)

    def destroy(self):
        super().destroy()
        # Release Tcl variables on the UI thread before a later import triggers Python GC.
        self.combined=None
        self.selected=None

    def focus_period(self):
        if self.winfo_exists():
            self.cells.xview_moveto(max(self.column-1,0)/len(self.groups))

    def wheel(self,e):
        self.cells.yview_scroll(-int(e.delta/120)*3,"units")

    def click(self,e):
        self.cells.focus_set()
        self.select(int(self.cells.canvasy(e.y)//self.rh),int(self.cells.canvasx(e.x)//self.cw))

    def select(self,row,col,reveal=False):
        self.row=max(0,min(row,len(self.data.rows)-1))
        self.column=max(0,min(col,len(self.groups)-1))
        if reveal:
            for index,size,extent,start,view,total in (
                    (self.column,self.cw,self.cells.winfo_width(),self.cells.canvasx(0),self.cells.xview_moveto,len(self.groups)),
                    (self.row,self.rh,self.cells.winfo_height(),self.cells.canvasy(0),self.cells.yview_moveto,len(self.data.rows))):
                if index*size<start:
                    view(index/total)
                elif (index+1)*size>start+extent:
                    view(((index+1)*size-extent)/(total*size))
        self.mark()
        if self.mode=="detail":
            self.show_detail()

    def toggle_month(self):
        old=self.groups[self.column][0]
        self.groups=self.data.groups(self.combined.get())
        self.column=next(i for i,g in enumerate(self.groups) if old in g)
        self.paint()
        if self.mode=="detail":
            self.show_detail()

    def paint(self):
        for canvas in (self.head,self.cells,self.names):
            canvas.delete("all")
        w,h=len(self.groups)*self.cw,len(self.data.rows)*self.rh
        self.cells.configure(scrollregion=(0,0,w,h))
        self.names.configure(scrollregion=(0,0,self.lw,h))
        self.head.configure(scrollregion=(0,0,w,self.hh))
        for j,g in enumerate(self.groups):
            x=j*self.cw
            title,phase=self.data.column_title(g)
            fill=RED if self.data.model.actual in g else "#42424b" if g[0].endswith(" remaining") else INK
            self.head.create_rectangle(x,0,x+self.cw,self.hh,fill=fill,outline="#54545b")
            self.head.create_text(x+11,self.hh*.33,text=title,font=BOLD,anchor="w",fill="white")
            self.head.create_text(x+11,self.hh*.70,text=phase,font=("Segoe UI",9),anchor="w",fill="#f0e9ee")
        for i,row in enumerate(self.data.rows):
            y=i*self.rh
            total=row in (OPEN,CLOSE,IN,OUT,FUND,MOVE)
            bg=INK if row==CLOSE else "#e2e2e7" if total else "#f7f7f9" if i%2 else "white"
            fg="white" if row==CLOSE else INK
            self.names.create_rectangle(0,y,self.lw,y+self.rh,fill=bg,outline="#dedee3")
            self.names.create_text(10,y+self.rh/2,anchor="w",text=self.data.label(row),fill=fg,font=BOLD if total else FONT)
            for j,g in enumerate(self.groups):
                x=j*self.cw
                n=self.data.value(row,g)
                self.cells.create_rectangle(x,y,x+self.cw,y+self.rh,fill=bg,outline="#dedee3")
                color="#ffb9c9" if row==CLOSE and n<0 else RED if n<0 else fg
                self.cells.create_text(x+self.cw-11,y+self.rh/2,anchor="e",text=money(n),fill=color,font=BOLD if total else FONT)
        self.mark()

    def mark(self):
        row,g=self.data.rows[self.row],self.groups[self.column]
        x,y=self.column*self.cw,self.row*self.rh
        self.cells.delete("selected")
        self.cells.create_rectangle(x+1,y+1,x+self.cw-1,y+self.rh-1,outline="#df365c",width=3,tags="selected")
        self.selected.set("Selected   ·   "+"   ·   ".join((self.data.label(row),*self.data.column_title(g),money(self.data.value(row,g))+" OMR")))

    def close_panel(self):
        if self.drawer is not None:
            self.drawer.destroy()
        self.drawer=self.mode=None

    def panel(self,mode,title):
        self.close_panel()
        self.mode=mode
        self.drawer=ttk.Frame(self,padding=8)
        self.drawer.grid(row=2,column=0,sticky="ew",pady=(0,8))
        top=ttk.Frame(self.drawer)
        top.pack(fill="x")
        ttk.Label(top,text=title,font=("Segoe UI Semibold",12)).pack(side="left")
        ttk.Button(top,text="Close",command=self.close_panel).pack(side="right")
        return top

    def table(self,headers,widths,right):
        frame=ttk.Frame(self.drawer)
        frame.pack(fill="x",pady=(5,0))
        frame.columnconfigure(0,weight=1)
        grid=ttk.Treeview(frame,columns=list(range(len(headers))),show="headings",height=4)
        grid.grid(row=0,column=0,sticky="nsew")
        for i,(name,width) in enumerate(zip(headers,widths)):
            anchor="e" if i in right else "w"
            grid.heading(i,text=name,anchor=anchor)
            grid.column(i,width=width,minwidth=75,anchor=anchor)
        for axis in ("vertical","horizontal"):
            vert=axis=="vertical"
            bar=ttk.Scrollbar(frame,orient=axis,command=grid.yview if vert else grid.xview)
            bar.grid(row=0 if vert else 1,column=1 if vert else 0,sticky="ns" if vert else "ew")
            grid.configure(**{"yscrollcommand" if vert else "xscrollcommand":bar.set})
        grid.tag_configure("total",background="#e5e5ea",font=BOLD)
        def full_record(event):
            if grid.selection():
                vals=grid.item(grid.selection()[0],"values")
                messagebox.showinfo("Record detail","\n\n".join(f"{k}\n{v}" for k,v in zip(headers,vals)),parent=self)
        grid.bind("<Double-1>",full_record)
        grid.bind("<Return>",full_record)
        self.panel_table=grid
        return grid

    def show_detail(self):
        row,g=self.data.rows[self.row],self.groups[self.column]
        self.panel("detail","Supporting detail")
        text="   ·   ".join((self.data.label(row),*self.data.column_title(g)))
        ttk.Label(self.drawer,text=text,font=FONT).pack(anchor="w")
        table=self.table(("Record or component","Treatment","Source","Included OMR"),(210,256,285,120),{3})
        for name,basis,loc,val in self.data.detail(row,g):
            table.insert("","end",values=(name,basis,loc,money(val)))
        table.insert("","end",values=("Total included","","",money(self.data.value(row,g))),tags=("total",))

    def show_compare(self,month=None,previous=None):
        top=self.panel("compare","Compare with previous week")
        if not self.data.previous and not isinstance(self.data.model,WeeklyModel):
            try:
                self.data.load_demo_previous(previous or self.folder/"Previous cash flow.xlsx")
            except Exception as exc:
                ttk.Label(self.drawer,text=str(exc),wraplength=730).pack(anchor="w",pady=6)
                def choose():
                    f=filedialog.askopenfilename(parent=self,title="Choose earlier demo export",filetypes=[("Excel workbook","*.xlsx")])
                    if f:
                        self.show_compare(previous=Path(f))
                ttk.Button(self.drawer,text="Choose previous workbook…",command=choose).pack(anchor="w")
                return
        months=list(dict.fromkeys(p[:7] for p in self.data.model.periods))
        month=month or self.groups[self.column][0][:7]
        self.compare_month=ttk.Combobox(top,values=months,state="readonly",width=10)
        self.compare_month.set(month)
        self.compare_month.pack(side="right",padx=8)
        self.compare_month.bind("<<ComboboxSelected>>",lambda e:self.show_compare(self.compare_month.get()))
        ttk.Label(self.drawer,text=f"{self.data.previous_label}     |     This week · actual to {self.data.model.cutoff:%d %b %Y}     |     Full month",
                  wraplength=930).pack(anchor="w",pady=(3,0))
        table=self.table(("Cash-flow item · OMR","Previous week","This week","Change"),(255,150,150,150),{1,2,3})
        values=self.data.month_values(month)
        for row in [CLOSE]+[r for r in self.data.rows if r!=CLOSE]:
            prior=self.data.previous.get((month,row))
            table.insert("","end",values=(self.data.label(row),money(prior),money(values[row]),
                         money(values[row]-prior) if prior is not None else "—"),tags=("total",) if row in (OPEN,CLOSE,IN,OUT,FUND,MOVE) else ())
