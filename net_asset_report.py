"""Net Asset Report  -  local desktop UI. Start with pythonw on Windows.
Workers communicate by a queue; all Tk updates happen on the main thread.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path

_root=Path(__file__).resolve().parent
_venv_python=_root/'.venv'/'Scripts'/'pythonw.exe'
_venv_dir=(_root/'.venv'/'Scripts').resolve()
if _venv_python.exists() and Path(sys.executable).resolve().parent!=_venv_dir:
    subprocess.Popen([str(_venv_python),str(Path(__file__).resolve())],cwd=str(_root))
    raise SystemExit

import copy, datetime, json, queue, threading, traceback, webbrowser, tempfile, os
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from tkinter import font as tkfont
from ui_design import choose_family,readable_scaling,initial_geometry,MONO_CANDIDATES,POINT_SIZES,PALETTE
import legacy_engine as engine
from asset_model import Case,Person,PASSPORT_FIELDS,BOLD_PERSON,BOLD_ASSET,money,read_proposal,uid,norm,VERSION,strip_secrets,asset_bold_fields
import report_export

TITLE='Net Asset Report'
APP_CREDIT='Made by CA LOVE KUMAR · MB: 88378-83498'
NAVY=PALETTE['navy'];GOLD=PALETTE['gold'];PAPER=PALETTE['paper'];INK=PALETTE['ink']

class App(engine.App):
    SETTINGS_FIELDS=[field for field in engine.App.SETTINGS_FIELDS if field[0] not in ('icai_id','icai_pwd')]
    def __init__(self):
        tk.Tk.__init__(self)
        self.title(TITLE+' '+VERSION);self.geometry(initial_geometry(self.winfo_screenwidth(),self.winfo_screenheight()));self.minsize(940,520)
        self.case=Case();self.current_person=self.case.people[0].id;self.pending=[];self._busy=False;self._generation=0
        self.jobs=queue.Queue();self._edit_index=None;self._loading=False;self.client_file=None
        self.rate_meta={};self._rate_request=0;self._setting_rate=False;self._loading_case=False;self.signature_image=None;self.letterpad=None
        self.ca_profiles={};self.load_profiles();self.architect_profiles={};self.load_architect_profiles();self._style()
        self.items=self.case.items
        today=datetime.date.today()
        defaults=dict(currency='None',purpose='Study Visa',authority='immigration or embassy authorities',engagement_date=today.strftime('%d.%m.%Y'),statement_date=today.strftime('%d-%m-%Y'),cert_date=today.strftime('%d.%m.%Y'))
        self.av={k:tk.StringVar(value=defaults.get(k,'')) for k,_,_,_ in engine.App.APP_FIELDS}
        self.av['income_report_year']=tk.StringVar(value='');self.av['country']=tk.StringVar(value='');self.av['fx_date']=tk.StringVar(value='')
        self.ab={k:tk.BooleanVar(value=k in BOLD_PERSON) for k in self.av}
        self.rowconfigure(2,weight=1);self.columnconfigure(0,weight=1)
        top=tk.Frame(self,bg=NAVY,padx=16,pady=7);top.grid(row=0,column=0,sticky='ew')
        heading=tk.Frame(top,bg=NAVY);heading.pack(fill='x')
        tk.Label(heading,text='NA',font=self.fonts['heading'],bg=GOLD,fg=NAVY,padx=9,pady=3).pack(side='left',padx=(0,16))
        identity=tk.Frame(heading,bg=NAVY);identity.pack(side='left')
        tk.Label(identity,text=TITLE,font=self.fonts['title'],fg='white',bg=NAVY,anchor='w').pack(anchor='w')
        tk.Label(heading,text='PRIVATE  /  LOCAL  /  REVIEWED',font=self.fonts['small'],fg='#D6C29D',bg=NAVY,anchor='w').pack(side='right',padx=5)
        commands=tk.Frame(top,bg=NAVY);commands.pack(fill='x',pady=(5,0))
        for label,command,style in [('Save case',self.save_client,'Gold.TButton'),('Save as / JSON',lambda:self.save_client(save_as=True),'Header.TButton'),('Open case',self.open_client,'Header.TButton'),('New',self.new_client,'Header.TButton')]:
            ttk.Button(commands,text=label,command=command,style=style).pack(side='left',padx=(0,6))
        self.window_size=tk.StringVar(value='Maximized')
        size=ttk.Combobox(commands,textvariable=self.window_size,state='readonly',values=['1024 x 578','1280 x 800','Maximized'],width=14);size.pack(side='right');size.bind('<<ComboboxSelected>>',self.set_window_size)
        tk.Label(commands,text='Window ',font=self.fonts['small'],bg=NAVY,fg='white').pack(side='right')
        tk.Frame(self,bg=GOLD,height=3).grid(row=1,column=0,sticky='ew')
        self.notebook=ttk.Notebook(self);self.notebook.grid(row=2,column=0,sticky='nsew',padx=12,pady=(8,5))
        self.tab_people=ttk.Frame(self.notebook,padding=10);self.tab_items=ttk.Frame(self.notebook,padding=10)
        self.tab_docs=ttk.Frame(self.notebook,padding=10);self.tab_tax=ttk.Frame(self.notebook,padding=10)
        self.tab_report=ttk.Frame(self.notebook,padding=10);self.tab_settings=ttk.Frame(self.notebook,padding=10)
        for frame,name in [(self.tab_people,'1  Applicants'),(self.tab_items,'2  Assets'),(self.tab_docs,'Documents & review'),(self.tab_report,'3  Report'),(self.tab_settings,'Firm settings')]:self.notebook.add(frame,text=name)
        self._people_tab();self._assets_tab();self._documents_tab();self._income_tab();self._report_tab();self._build_settings_tab()
        # User credentials are session-only, never saved with a case or CA profile.
        footer=ttk.Frame(self,padding=(16,6),style='Footer.TFrame');footer.grid(row=3,column=0,sticky='ew');footer.columnconfigure(0,weight=1)
        self.totals_lbl=ttk.Label(footer,style='Footer.TLabel');self.totals_lbl.grid(row=0,column=0,sticky='ew')
        self.status=tk.StringVar(value='Ready. Add applicants, enter assets, then export.')
        ttk.Label(footer,textvariable=self.status,style='FooterHint.TLabel',width=1).grid(row=1,column=0,sticky='ew',pady=(3,0))
        ttk.Label(self,text=APP_CREDIT,style='Hint.TLabel',anchor='center').grid(row=4,column=0,sticky='ew',pady=(0,3))
        self._seen_tabs=set();self.notebook.bind('<<NotebookTabChanged>>',self._tab_changed)
        for event in ('<MouseWheel>','<Button-4>','<Button-5>'):self.notebook.bind(event,lambda e:'break')
        self.bind_class('NARScroll','<MouseWheel>',self._on_mousewheel)
        self.bind_class('NARScroll','<Button-4>',self._on_mousewheel);self.bind_class('NARScroll','<Button-5>',self._on_mousewheel)
        # Controls in the review form are created dynamically.  Route wheel
        # events from the actual pointer widget so nested panes remain usable.
        self.bind_all('<MouseWheel>',self._on_mousewheel,add='+')
        self.bind_all('<Button-4>',self._on_mousewheel,add='+')
        self.bind_all('<Button-5>',self._on_mousewheel,add='+')
        self.protocol('WM_DELETE_WINDOW',self._close)
        if self.ca_profiles:self.profile_cb.set(next(iter(self.ca_profiles)));self.load_profile()
        self._select_person();self.refresh();self._sync_case();App._mark_case_clean(self);self.after(80,self._drain);self.after_idle(self._maximize_startup)

    def _maximize_startup(self):
        try:
            if self.tk.call('tk','windowingsystem')=='win32':self.state('zoomed')
            else:self.attributes('-zoomed',True)
        except tk.TclError:pass  # Centered, screen-bounded fallback already set.

    def _style(self):
        # Named fonts avoid unsupported family fallback and tuple interpretation quirks.
        # Tk sizes are points; normalize DPI once, never multiply font sizes by DPI.
        self.tk.call('tk','scaling',readable_scaling(self.tk.call('tk','scaling')))
        family=choose_family(tkfont.families(self));mono=choose_family(tkfont.families(self),MONO_CANDIDATES)
        self.fonts={}
        for key,size in POINT_SIZES.items():
            selected=mono if key=='mono' else family
            if selected=='TkDefaultFont':selected=tkfont.nametofont('TkDefaultFont',root=self).actual('family')
            self.fonts[key]=tkfont.Font(root=self,name='NAR_'+key,family=selected,size=size,
                                       weight='bold' if key in ('title','heading','bold','tab') else 'normal')
        for default in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont'):
            tkfont.nametofont(default,root=self).configure(family=family if family!='TkDefaultFont' else 'sans-serif',size=12)
        self.option_add('*Font',self.fonts['body']);self.option_add('*Listbox.font',self.fonts['body'])
        st=ttk.Style(self);st.theme_use('clam');self.configure(bg=PAPER)
        st.configure('.',font=self.fonts['body'],background=PAPER,foreground=INK)
        st.configure('TFrame',background=PAPER);st.configure('TLabel',background=PAPER,font=self.fonts['body'])
        st.configure('TLabelframe',background='white',bordercolor=PALETTE['border'],relief='solid',borderwidth=1)
        st.configure('TLabelframe.Label',background=PAPER,font=self.fonts['bold'],foreground=NAVY)
        st.configure('H1.TLabel',font=self.fonts['title'],foreground=NAVY)
        st.configure('H2.TLabel',font=self.fonts['heading'],foreground=NAVY)
        st.configure('Bold.TLabel',font=self.fonts['bold'],foreground=NAVY)
        st.configure('Hint.TLabel',font=self.fonts['small'],foreground=PALETTE['muted'])
        st.configure('TButton',font=self.fonts['body'],padding=(15,9),background='white',foreground=NAVY,
                     borderwidth=1,bordercolor=PALETTE['border'],lightcolor='white',darkcolor='white',relief='flat')
        st.map('TButton',background=[('active',PALETTE['pale'])],bordercolor=[('focus',GOLD)])
        st.configure('Accent.TButton',font=self.fonts['bold'],padding=(16,10),background=NAVY,foreground='white',bordercolor=NAVY)
        st.map('Accent.TButton',background=[('active',PALETTE['slate'])],foreground=[('disabled','#B8C2C9')])
        st.configure('Gold.TButton',font=self.fonts['bold'],padding=(18,10),background=GOLD,foreground=NAVY,bordercolor=GOLD)
        st.map('Gold.TButton',background=[('active','#DBC493')])
        st.configure('Header.TButton',font=self.fonts['body'],padding=(15,10),background=PALETTE['slate'],foreground='white',bordercolor='#557080')
        st.map('Header.TButton',background=[('active','#34566C')])
        st.configure('TEntry',font=self.fonts['body'],padding=(10,8),fieldbackground='white',bordercolor=PALETTE['border'],lightcolor='white',darkcolor='white')
        st.map('TEntry',bordercolor=[('focus',GOLD)])
        st.configure('TCombobox',font=self.fonts['body'],padding=(9,8),fieldbackground='white',background='white',foreground=INK,arrowsize=15,bordercolor=PALETTE['border'])
        st.map('TCombobox',fieldbackground=[('readonly','white')],foreground=[('readonly',INK)],selectbackground=[('readonly','white')],selectforeground=[('readonly',INK)],bordercolor=[('focus',GOLD)])
        st.configure('TCheckbutton',font=self.fonts['small'],padding=(0,6),background=PAPER)
        rowheight=self.fonts['body'].metrics('linespace')+20
        st.configure('Treeview',background='white',fieldbackground='white',foreground=INK,rowheight=rowheight,font=self.fonts['body'],borderwidth=0)
        st.map('Treeview',background=[('selected','#E0E9EF')],foreground=[('selected',NAVY)])
        st.configure('Treeview.Heading',font=self.fonts['bold'],padding=(10,10),background=PALETTE['pale'],foreground=NAVY,relief='flat')
        st.configure('TNotebook',background=PAPER,borderwidth=0,tabmargins=(0,0,0,10))
        st.configure('TNotebook.Tab',font=self.fonts['tab'],padding=(18,12),background='#E5EAEC',foreground=PALETTE['muted'],borderwidth=0,lightcolor=PAPER,darkcolor=PAPER)
        st.map('TNotebook.Tab',background=[('selected',NAVY),('active','#D6E1E7')],foreground=[('selected','white'),('active',NAVY)],font=[('selected',self.fonts['tab']),('!selected',self.fonts['tab'])],padding=[('selected',(18,12)),('!selected',(18,12))],expand=[('selected',(0,0,0,0)),('!selected',(0,0,0,0))])
        st.configure('Sidebar.TFrame',background=NAVY)
        st.configure('SidebarHeading.TLabel',background=NAVY,foreground='white',font=self.fonts['bold'])
        st.configure('SidebarHint.TLabel',background=NAVY,foreground='#D2DDE3',font=self.fonts['small'])
        st.configure('Sidebar.TButton',font=self.fonts['body'],padding=(10,9),background=PALETTE['slate'],foreground='white',bordercolor=PALETTE['slate'])
        st.map('Sidebar.TButton',background=[('active','#35566B')])
        st.configure('Sidebar.Treeview',font=self.fonts['body'],background=NAVY,fieldbackground=NAVY,foreground='white',rowheight=rowheight)
        st.map('Sidebar.Treeview',background=[('selected',PALETTE['slate'])],foreground=[('selected','#F0DDB8')])
        st.configure('Footer.TFrame',background='white')
        st.configure('Footer.TLabel',background='white',foreground=NAVY,font=self.fonts['bold'])
        st.configure('FooterHint.TLabel',background='white',foreground=PALETTE['muted'],font=self.fonts['small'])

    def set_window_size(self,_=None):
        value=self.window_size.get()
        if value=='Maximized':self._maximize_startup();return
        try:self.state('normal');self.attributes('-zoomed',False)
        except tk.TclError:pass
        self.geometry(value.replace(' ','')+'+0+0')

    def _tab_changed(self,_=None):
        selected=self.notebook.select()
        if selected not in self._seen_tabs:
            self._seen_tabs.add(selected)
            def reset():
                def visit(widget):
                    if isinstance(widget,tk.Canvas):widget.yview_moveto(0)
                    for child in widget.winfo_children():visit(child)
                try:visit(self.nametowidget(selected))
                except tk.TclError:pass
            self.after_idle(reset)

    def _tag_scroll_children(self,widget):
        tags=widget.bindtags()
        if 'NARScroll' not in tags:widget.bindtags(('NARScroll',)+tags)
        for child in widget.winfo_children():self._tag_scroll_children(child)

    def _on_mousewheel(self,event):
        from ui_design import wheel_units
        widget=event.widget
        if isinstance(widget,(tk.Text,tk.Listbox,ttk.Treeview)):return
        while widget is not None:
            canvas=getattr(widget,'_scroll_canvas',None)
            if canvas is not None:
                canvas.yview_scroll(wheel_units(getattr(event,'num',None),getattr(event,'delta',0)),'units');return 'break'
            widget=getattr(widget,'master',None)

    def _refresh_scroll_bindings(self):
        """Retag dynamically-created nested review widgets for wheel routing."""
        try:
            self._tag_scroll_children(self)
        except tk.TclError:
            pass

    def scroll_to(self,body,widget=None):
        canvas=getattr(body,'_scroll_canvas',None)
        if canvas is None:return
        def move():
            canvas.update_idletasks();height=max(body.winfo_height(),1)
            y=(widget.winfo_y() if widget else 0);canvas.yview_moveto(max(0,(y-8)/height))
        self.after_idle(move)

    def scroll_frame(self,parent,dark=False):
        box=ttk.Frame(parent,style='Sidebar.TFrame' if dark else 'TFrame');box.pack(fill='both',expand=True)
        canvas=tk.Canvas(box,bg=NAVY if dark else PAPER,highlightthickness=0,yscrollincrement=20);sb=ttk.Scrollbar(box,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set);canvas.pack(side='left',fill='both',expand=True);sb.pack(side='right',fill='y')
        body=ttk.Frame(canvas,padding=(12,14,12,14) if dark else (0,0,10,0),style='Sidebar.TFrame' if dark else 'TFrame');window=canvas.create_window((0,0),window=body,anchor='nw')
        body._scroll_canvas=canvas;box._scroll_canvas=canvas
        last_width=[None]
        def resized(event):
            if last_width[0]!=event.width:canvas.itemconfigure(window,width=event.width);last_width[0]=event.width
        def content_changed(_):
            canvas.configure(scrollregion=canvas.bbox('all'));self._tag_scroll_children(box)
        body.bind('<Configure>',content_changed);canvas.bind('<Configure>',resized)
        return body

    def field(self,parent,row,label,var,options=None,boldvar=None):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=5,padx=(0,12))
        w=ttk.Combobox(parent,textvariable=var,values=options,state='readonly') if options else ttk.Entry(parent,textvariable=var)
        w.grid(row=row,column=1,sticky='ew',pady=5)
        if boldvar is not None:ttk.Checkbutton(parent,text='Bold in Word/PDF',variable=boldvar).grid(row=row,column=2,sticky='w',padx=8)
        parent.columnconfigure(1,weight=1);return w

    def _people_tab(self):
        sidebar=ttk.Frame(self.tab_people,width=264,style='Sidebar.TFrame');sidebar.pack(side='left',fill='y',padx=(0,24));sidebar.pack_propagate(False)
        left=self.scroll_frame(sidebar,dark=True)
        ttk.Label(left,text='Applicants & family',style='SidebarHeading.TLabel').pack(anchor='w',pady=(0,12))
        self.people_tree=ttk.Treeview(left,show='tree',height=4,selectmode='browse',style='Sidebar.Treeview');self.people_tree.pack(fill='x')
        self.people_tree.bind('<<TreeviewSelect>>',self._person_changed)
        ttk.Button(left,text='+ Add applicant',style='Gold.TButton',command=lambda:self.add_person('Applicant')).pack(fill='x',pady=(12,4))
        ttk.Button(left,text='+ Add family / owner',style='Sidebar.TButton',command=lambda:self.add_person('Family / owner')).pack(fill='x',pady=4)
        ttk.Button(left,text='Import passport',style='Sidebar.TButton',command=lambda:self.import_documents('Passport')).pack(fill='x',pady=8)
        ttk.Label(left,text='Select a person, then import their passport. Front and back stay together.',style='SidebarHint.TLabel',wraplength=200).pack(anchor='w',pady=8)
        ttk.Button(left,text='Relationships',style='Sidebar.TButton',command=self.show_relationships).pack(fill='x',pady=8)
        ttk.Button(left,text='Remove unused',style='Sidebar.TButton',command=self.remove_person).pack(fill='x',pady=4)
        right=ttk.Frame(self.tab_people);right.pack(side='left',fill='both',expand=True)
        body=self.scroll_frame(right)
        ttk.Label(body,text='Identity',style='H2.TLabel').grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,10))
        self.pv={k:tk.StringVar() for k in ('title','name','passport_number','address','father_name','mother_name','spouse_name')}
        self.pb={k:tk.BooleanVar(value=True) for k in BOLD_PERSON}
        self.field(body,1,'Title',self.pv['title'],['Mr.','Ms.','Mrs.','Miss'])
        self.field(body,2,'Full name',self.pv['name'],boldvar=self.pb['name'])
        self.field(body,3,'Passport number',self.pv['passport_number'],boldvar=self.pb['passport'])
        self.field(body,4,'Full address',self.pv['address'],boldvar=self.pb['address'])
        self.field(body,5,'Father / legal guardian',self.pv['father_name'])
        self.field(body,6,'Mother',self.pv['mother_name'])
        self.field(body,7,'Spouse / husband',self.pv['spouse_name'])
        self.use_father=tk.BooleanVar();ttk.Checkbutton(body,text='Use father\u0027s name instead',variable=self.use_father,command=self._commit_person).grid(row=8,column=1,sticky='w',pady=8)
        ttk.Checkbutton(body,text='Bold in Word/PDF',variable=self.pb['parent']).grid(row=8,column=2,sticky='w')
        self.parent_preview=tk.StringVar();ttk.Label(body,textvariable=self.parent_preview,style='Bold.TLabel').grid(row=9,column=0,columnspan=3,sticky='w',pady=8)
        ttk.Label(body,text='Uses the Excel relationship rule. Formula exceptions are explained in Report.',style='Hint.TLabel',wraplength=700).grid(row=10,column=0,columnspan=3,sticky='w',pady=5)
        self.show_metadata=tk.BooleanVar(value=False)
        self.metadata_frame=ttk.LabelFrame(body,text='Passport details',padding=10)
        self.metadata_frame.grid(row=12,column=0,columnspan=3,sticky='ew',pady=10);self.metadata_frame.grid_remove()
        def toggle_metadata():
            if self.show_metadata.get():self.metadata_frame.grid()
            else:self.metadata_frame.grid_remove()
        ttk.Checkbutton(body,text='More passport details',variable=self.show_metadata,command=toggle_metadata).grid(row=11,column=0,columnspan=3,sticky='w',pady=(18,4))
        self.extra_pv={}
        for r,(key,label) in enumerate([(k,v) for k,v in PASSPORT_FIELDS.items() if k not in self.pv and k!='full_name']):
            self.extra_pv[key]=tk.StringVar();self.field(self.metadata_frame,r,label,self.extra_pv[key])
        for v in list(self.pv.values())+list(self.extra_pv.values()):v.trace_add('write',lambda *_:self._commit_person())
        for v in self.pb.values():v.trace_add('write',lambda *_:self._commit_person())

    def _commit_person(self):
        if self._loading:return
        p=self.case.person(self.current_person)
        p.title=self.pv['title'].get();p.name=self.pv['name'].get()
        for k,v in self.pv.items():
            if k not in ('title','name'):p.fields[k]=v.get()
        for k,v in self.extra_pv.items():p.fields[k]=v.get()
        p.fields['full_name']=p.name;p.use_father=self.use_father.get();p.bold={k:v.get() for k,v in self.pb.items()}
        # Imported legacy overrides are cleared when editable source relationship fields are supplied.
        if p.fields.get('father_name') or p.fields.get('spouse_name'):p.parent_override=''
        self.parent_preview.set('Report line: '+self.case.parent_line(p))
        if self.people_tree.exists(p.id):self.people_tree.item(p.id,text=(p.name or 'Unnamed')+'  |  '+p.role)
        if hasattr(self,'asset_owner_cb'):self._update_people_choices()

    def _select_person(self):
        p=self.case.person(self.current_person);self._loading=True
        for k,v in self.pv.items():v.set(getattr(p,k) if k in ('title','name') else p.fields.get(k,''))
        for k,v in self.extra_pv.items():v.set(p.fields.get(k,''))
        for k,v in self.pb.items():v.set(p.bold.get(k,True))
        self.use_father.set(p.use_father);self.parent_preview.set('Report line: '+self.case.parent_line(p));self._loading=False

    def _person_changed(self,_=None):
        selected=self.people_tree.selection()
        if selected and selected[0]!=self.current_person:
            self._commit_person();self.current_person=selected[0];self._select_person()

    def add_person(self,role):
        self._commit_person();p=self.case.add_person(role);self.current_person=p.id;self._select_person();self.refresh()

    def remove_person(self):
        try:
            self.case.remove_person(self.current_person);self.current_person=self.case.applicants[0].id;self._select_person();self.refresh()
        except ValueError as e:messagebox.showwarning(TITLE,str(e),parent=self)

    def _update_people_choices(self):
        old=getattr(self,'_people_labels',{})
        choices={p.id:f'{i+1}. {p.name or "Unnamed"}  |  {p.role}' for i,p in enumerate(self.case.people)}
        asset_choices=choices
        if getattr(self,'asset_type',None) is not None and self.asset_type.get() in ('Bank Account (Savings / Current)','Fixed Deposit'):
            asset_choices={p.id:label for p,label in choices.items() if self.case.person(p).role=='Applicant'}
        self._people_labels=choices
        for cb,var in [(self.asset_owner_cb,self.asset_owner),(self.doc_target_cb,self.doc_target),(self.income_owner_cb,self.income_owner)]:
            chosen=next((k for k,v in old.items() if v==var.get()),None)
            available=asset_choices if cb is self.asset_owner_cb else choices
            cb.configure(values=list(available.values()))
            if chosen in available:var.set(available[chosen])
            elif not var.get() or (cb is self.asset_owner_cb and chosen not in available):var.set(available.get(self.current_person,next(iter(available.values()),'')))
        if self.doc_tree.selection():pass

    def person_id(self,label):
        pid=next((k for k,v in self._people_labels.items() if v==label),None)
        if pid is None:raise ValueError('Select an applicant or family owner.')
        return pid

    def _assets_tab(self):
        bar=ttk.Frame(self.tab_items);bar.pack(fill='x',pady=(0,10))
        ttk.Label(bar,text='Assets',style='H2.TLabel').pack(side='left')
        ttk.Button(bar,text='Import',command=lambda:self.import_documents('Assets')).pack(side='right')
        ttk.Button(bar,text='+ Cash',style='Accent.TButton',command=self.cash_button).pack(side='right',padx=8)
        editor_body=self.scroll_frame(self.tab_items);self.asset_scroll_body=editor_body
        table_host=ttk.Frame(editor_body)
        editor=ttk.LabelFrame(editor_body,text='Add an item',padding=14);editor.pack(fill='x');self.asset_editor=editor
        self.asset_type=tk.StringVar(value='Cash in Hand');self.asset_owner=tk.StringVar();self.asset_amount=tk.StringVar();self.asset_details=tk.StringVar()
        cb=self.field(editor,0,'Type',self.asset_type,list(engine.CATS));cb.bind('<<ComboboxSelected>>',self._category_changed)
        self.asset_owner_cb=self.field(editor,1,'Owner',self.asset_owner,[]);self.asset_owner_cb.destroy()
        self.asset_owner_cb=ttk.Combobox(editor,textvariable=self.asset_owner,state='readonly');self.asset_owner_cb.grid(row=1,column=1,sticky='ew',pady=5)
        self.field(editor,2,'Value (INR)',self.asset_amount)
        self.asset_name=tk.StringVar(value='Cash in Hand');self._last_category='Cash in Hand'
        self.field(editor,3,'Asset name',self.asset_name)
        self.field(editor,4,'Particulars',self.asset_details)
        self.asset_more=ttk.Frame(editor);self.asset_more.grid(row=5,column=0,columnspan=3,sticky='ew')
        self.more_open=tk.BooleanVar(value=False)
        ttk.Checkbutton(editor,text='Supporting details',variable=self.more_open,command=self._asset_fields).grid(row=6,column=0,columnspan=2,sticky='w',pady=6)
        self.asset_save_button=ttk.Button(bar,text='Add item',style='Accent.TButton',command=self.add_inline_asset);self.asset_save_button.pack(side='left',padx=6)
        ttk.Button(bar,text='Cancel edit',command=self.cancel_asset_edit).pack(side='left',padx=3)
        ttk.Button(bar,text='View list',command=lambda:self.scroll_to(editor_body,table_host)).pack(side='left',padx=3)
        ttk.Button(bar,text='Edit selected',command=self.edit_item).pack(side='left',padx=3)
        ttk.Label(editor,text='Report emphasis: asset details, ownership and confirmed relationships.',style='Hint.TLabel',wraplength=900).grid(row=7,column=0,columnspan=3,sticky='w',pady=4)
        self.asset_fv={};self._asset_fields()
        table_host.pack(fill='both',expand=True,pady=(14,0))
        table=ttk.Frame(table_host);table.pack(fill='both',expand=True,pady=(12,8))
        cols=('category','owner','relation','particulars','amount');self.tree=ttk.Treeview(table,columns=cols,show='headings',selectmode='browse',height=5)
        for key,label,width in [('category','Group / asset name',235),('owner','Owner',165),('relation','Relation to applicant(s)',220),('particulars','Particulars',300),('amount','Value (INR)',135)]:
            self.tree.heading(key,text=label);self.tree.column(key,width=width,anchor='e' if key=='amount' else 'w')
        xbar=ttk.Scrollbar(table_host,orient='horizontal',command=self.tree.xview);xbar.pack(side='bottom',fill='x');self.tree.configure(xscrollcommand=xbar.set)
        self.tree.pack(side='left',fill='both',expand=True);sb=ttk.Scrollbar(table,command=self.tree.yview);sb.pack(side='right',fill='y');self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind('<Double-1>',lambda e:self.edit_item())
        self.tree.bind('<<TreeviewSelect>>',self.show_asset_detail)
        self.tree.tag_configure('group',font=self.fonts['bold'],background='#E9EEF0',foreground=NAVY)
        self.asset_detail=tk.Text(table_host,height=3,wrap='word',font=self.fonts['small'],background='white',relief='flat');self.asset_detail.pack(fill='x',pady=(0,8));self.asset_detail.configure(state='disabled')
        acts=ttk.Frame(table_host);acts.pack(fill='x')
        for text,cmd in [('Edit inline',self.edit_item),('Duplicate',self.duplicate_item),('Delete',self.delete_item),('Move up',lambda:self.move_item(-1)),('Move down',lambda:self.move_item(1))]:ttk.Button(acts,text=text,command=cmd).pack(side='left',padx=4)

    def _asset_fields(self):
        old={k:v.get() for k,v in self.asset_fv.items()};self.asset_fv={}
        for child in self.asset_more.winfo_children():child.destroy()
        self.asset_section=tk.StringVar(value=getattr(self,'asset_section',tk.StringVar(value=engine.CATS[self.asset_type.get()]['section'])).get())
        extra=[]
        if self.asset_type.get()=='Immovable Property':extra=[(k,label,'text',None) for k,label in [('area','Land area / measure'),('deed','Deed / land record reference'),('tenure','Tenure'),('valuer_name','Architect / valuer name'),('valuer_firm','Architect / valuer firm'),('valuer_credentials','Reported licence / credentials'),('val_ref','Valuation report reference')]]
        if self.asset_type.get() in ('Bank Account (Savings / Current)','Fixed Deposit'):
            extra=[('bank','Bank name','combo',[
                'State Bank of India','HDFC Bank','ICICI Bank','Axis Bank','Punjab National Bank',
                'Bank of Baroda','Canara Bank','Union Bank of India','Kotak Mahindra Bank',
                'IndusInd Bank','Yes Bank','IDBI Bank','Other / type bank name']),
                ('evidence_type','Bank balance as per','combo',['Bank Certificate','Bank Statement']),
                ('as_on','Statement / certificate date','text',None),('acno','Account number','text',None),('branch','Branch (if supplied)','text',None)]
        for k,label,typ,opts in engine.CATS[self.asset_type.get()].get('fields',[])+extra:
            if k in ('holder','relation'):continue
            var=tk.StringVar(value=old.get(k,''));self.asset_fv[k]=var
            if self.more_open.get() or self.asset_type.get() in ('Bank Account (Savings / Current)','Fixed Deposit'):
                self.field(self.asset_more,len(self.asset_fv)-1,label,var,opts if typ=='combo' else None)
        self.asset_fv['_note']=tk.StringVar(value=old.get('_note',''))
        if self.more_open.get():
            self.field(self.asset_more,len(self.asset_fv),'Supporting note (optional)',self.asset_fv['_note'])
            self.field(self.asset_more,len(self.asset_fv)+1,'Classification (A/B/C)',self.asset_section,['A','B','C'])
        if self.asset_type.get()=='Immovable Property':
            row=len(self.asset_fv)+2; bar=ttk.Frame(self.asset_more);bar.grid(row=row,column=0,columnspan=3,sticky='ew',pady=(6,0))
            ttk.Label(bar,text='Saved architect / valuer').pack(side='left')
            self.architect_profile_var=tk.StringVar();self.architect_profile_cb=ttk.Combobox(bar,textvariable=self.architect_profile_var,state='readonly',values=list(self.architect_profiles),width=28);self.architect_profile_cb.pack(side='left',padx=6)
            self.architect_profile_cb.bind('<<ComboboxSelected>>',lambda _e:self.apply_architect_profile())
            ttk.Button(bar,text='Save current',command=self.save_architect_profile).pack(side='left',padx=3)
            ttk.Button(bar,text='Delete',command=self.delete_architect_profile).pack(side='left',padx=3)

    def _category_changed(self,_=None):
        if self.asset_name.get() in ('',getattr(self,'_last_category','')):self.asset_name.set(self.asset_type.get())
        self._last_category=self.asset_type.get()
        if self.asset_type.get()=='Cash in Hand' and not self.asset_details.get().strip():
            self.asset_details.set('Cash in hand as per self-declaration')
        self.asset_section.set(engine.CATS[self.asset_type.get()]['section']);self._asset_fields()
        self._update_people_choices()

    def _architect_profile_path(self):return Path.home()/'.networth_architect_profiles.json'

    def load_architect_profiles(self):
        try:
            data=json.loads(self._architect_profile_path().read_text(encoding='utf-8'));self.architect_profiles=data if isinstance(data,dict) else {}
        except (OSError,ValueError,TypeError):self.architect_profiles={}

    def save_architect_profile(self):
        if self.asset_type.get()!='Immovable Property':return
        name=self.asset_fv.get('valuer_name',tk.StringVar()).get().strip();firm=self.asset_fv.get('valuer_firm',tk.StringVar()).get().strip();lic=self.asset_fv.get('valuer_credentials',tk.StringVar()).get().strip()
        if not name:messagebox.showwarning(TITLE,'Enter the architect / valuer name first.',parent=self);return
        key=name+' | '+firm if firm else name;self.architect_profiles[key]=dict(name=name,firm=firm,licence=lic)
        self._architect_profile_path().write_text(json.dumps(self.architect_profiles,indent=2,ensure_ascii=False),encoding='utf-8');self.architect_profile_var.set(key);self.architect_profile_cb.configure(values=list(self.architect_profiles));self.status.set('Architect / valuer profile saved locally.')

    def apply_architect_profile(self):
        profile=self.architect_profiles.get(self.architect_profile_var.get(),{})
        for key,value in [('valuer_name',profile.get('name','')),('valuer_firm',profile.get('firm','')),('valuer_credentials',profile.get('licence',''))]:
            if key in self.asset_fv:self.asset_fv[key].set(value)

    def delete_architect_profile(self):
        key=getattr(self,'architect_profile_var',tk.StringVar()).get()
        if not key or key not in self.architect_profiles:return
        if not messagebox.askyesno(TITLE,'Delete saved architect / valuer profile '+key+'?',parent=self):return
        self.architect_profiles.pop(key);self._architect_profile_path().write_text(json.dumps(self.architect_profiles,indent=2,ensure_ascii=False),encoding='utf-8');self.architect_profile_cb.configure(values=list(self.architect_profiles));self.architect_profile_var.set('')

    def cash_button(self):
        self.clear_asset();self.asset_type.set('Cash in Hand');self.asset_details.set('Cash in hand as per self-declaration');self._category_changed()
        self.asset_owner.set(self._people_labels.get(self.current_person,''))

    def add_inline_asset(self):
        try:
            if self.asset_type.get() in ('Bank Account (Savings / Current)','Fixed Deposit'):
                raw_date=self.asset_fv.get('as_on',tk.StringVar()).get().strip()
                if raw_date:self.asset_fv['as_on'].set(engine.format_smart_date(raw_date,'-'))
            fields={k:v.get() for k,v in self.asset_fv.items()}
            self.case.add_asset(self.asset_type.get(),self.asset_amount.get(),self.person_id(self.asset_owner.get()),self.asset_details.get(),fields,section=self.asset_section.get(),index=self._edit_index,asset_name=self.asset_name.get())
            self.clear_asset();self.refresh()
        except Exception as e:messagebox.showwarning(TITLE,str(e),parent=self)

    def clear_asset(self):
        if getattr(self,'_resetting_asset',False):return
        self._resetting_asset=True
        try:
            self._edit_index=None;self._asset_edit_baseline=None
            self.asset_type.set('Cash in Hand');self._last_category='Cash in Hand';self.asset_amount.set('');self.asset_details.set('');self.asset_name.set('Cash in Hand')
            self.asset_owner.set(getattr(self,'_people_labels',{}).get(self.current_person,''));self.more_open.set(False)
            for v in self.asset_fv.values():v.set('')
            self.asset_section.set(engine.CATS['Cash in Hand']['section']);self._asset_fields();self.asset_save_button.configure(text='Add item')
        finally:self._resetting_asset=False

    def cancel_asset_edit(self):
        self.clear_asset();self.status.set('Edit cancelled. No asset record changed; ready to add an item.')

    def _asset_draft(self):
        if not hasattr(self,'asset_amount'):return None
        return dict(category=self.asset_type.get(),owner=self.asset_owner.get(),amount=self.asset_amount.get(),name=self.asset_name.get(),details=self.asset_details.get(),fields={k:v.get() for k,v in self.asset_fv.items()},section=self.asset_section.get())

    def _pending_asset_changes(self):
        draft=App._asset_draft(self)
        if draft is None:return False
        if getattr(self,'_edit_index',None) is not None:return draft!=getattr(self,'_asset_edit_baseline',draft)
        return bool(draft['amount'].strip() or draft['details'].strip() or draft['name'].strip()!=draft['category'] or any(str(v).strip() for v in draft['fields'].values()))

    def edit_item(self):
        i=self.selected_index()
        if i is None:return
        it=self.case.items[i];self._edit_index=i;self.asset_type.set(it['category']);self.asset_name.set(it.get('asset_name',it['category']));self.asset_details.set(it.get('details') or engine.strip_marks(it['desc']));self.asset_amount.set(str(it['amount']))
        self.asset_owner.set(self._people_labels.get(it.get('owner_id'),''));self.more_open.set(True);self.asset_section.set(it['section']);self._asset_fields()
        for k,v in self.asset_fv.items():v.set(it.get('fields',{}).get(k,''))
        self.asset_save_button.configure(text='Save changes');self._asset_edit_baseline=App._asset_draft(self)
        if hasattr(self,'asset_scroll_body'):self.scroll_to(self.asset_scroll_body,self.asset_editor)

    def duplicate_item(self):
        i=self.selected_index()
        if i is not None:
            it=copy.deepcopy(self.case.items[i]);it['id']=uid();self.case.items.insert(i+1,it);self.refresh(select=i+1)

    def delete_item(self):
        i=self.selected_index()
        if i is not None and messagebox.askyesno(TITLE,'Delete selected item?',parent=self):self.case.items.pop(i);self.clear_asset();self.refresh()

    def move_item(self,delta):
        i=self.selected_index()
        if i is not None and 0<=i+delta<len(self.case.items):self.case.items[i],self.case.items[i+delta]=self.case.items[i+delta],self.case.items[i];self.refresh(select=i+delta)

    def _documents_tab(self):
        outer=self.tab_docs;self.tab_docs=self.scroll_frame(outer)
        top=ttk.Frame(self.tab_docs);top.pack(fill='x')
        ttk.Label(top,text='Documents',style='H2.TLabel').pack(side='left')
        ttk.Button(top,text='OCR engine',command=self.choose_ocr).pack(side='right',padx=3)
        for kind in ('Passport','ITR','Computation','Assets'):ttk.Button(top,text='Import '+kind,command=lambda k=kind:self.import_documents(k)).pack(side='right',padx=3)
        self.doc_tree=ttk.Treeview(self.tab_docs,columns=('type','state','target'),show='tree headings',height=3,selectmode='browse')
        self.doc_tree.heading('#0',text='Document');self.doc_tree.heading('type',text='Import type');self.doc_tree.heading('state',text='Review');self.doc_tree.heading('target',text='Linked person')
        self.doc_tree.column('#0',width=380);self.doc_tree.column('type',width=100);self.doc_tree.column('state',width=110);self.doc_tree.column('target',width=230)
        self.doc_tree.pack(fill='x',pady=8);self.doc_tree.bind('<<TreeviewSelect>>',self._show_doc)
        removal=ttk.Frame(self.tab_docs);removal.pack(fill='x',pady=(0,6))
        ttk.Button(removal,text='Remove document',command=self.remove_document).pack(side='left')
        ttk.Button(removal,text='Undo removal',command=self.undo_document_removal).pack(side='left',padx=8)
        typebar=removal
        ttk.Label(typebar,text='Document type').pack(side='left',padx=(14,0))
        self.doc_kind=tk.StringVar()
        ttk.Combobox(typebar,textvariable=self.doc_kind,state='readonly',width=16,values=['Passport','ITR','Computation','Assets']).pack(side='left',padx=8)
        ttk.Button(typebar,text='Use this type',command=self.reclassify_document).pack(side='left')
        route=ttk.Frame(self.tab_docs);route.pack(fill='x')
        ttk.Label(route,text='Link to').pack(side='left')
        self.doc_target=tk.StringVar();self.doc_target_cb=ttk.Combobox(route,textvariable=self.doc_target,state='readonly',width=26);self.doc_target_cb.pack(side='left',padx=8)
        ttk.Button(route,text='Apply import',style='Accent.TButton',command=self.apply_import).pack(side='left',padx=8)
        ttk.Button(route,text='Discard pending',command=self.remove_pending).pack(side='left')
        self.doc_warning=tk.StringVar(value='Raw text is retained in the case, never silently discarded. OCR proposals require review.')
        ttk.Label(self.tab_docs,textvariable=self.doc_warning,style='Hint.TLabel',wraplength=1050).pack(anchor='w',pady=8)
        viewbar=ttk.Frame(self.tab_docs);viewbar.pack(fill='x',pady=(0,6))
        ttk.Label(viewbar,text='Review layout:').pack(side='left')
        ttk.Button(viewbar,text='Widen source',command=lambda:self.set_document_pane('source')).pack(side='left',padx=4)
        ttk.Button(viewbar,text='Widen fields',command=lambda:self.set_document_pane('fields')).pack(side='left',padx=4)
        ttk.Button(viewbar,text='Balanced',command=lambda:self.set_document_pane('balanced')).pack(side='left',padx=4)
        panes=ttk.Panedwindow(self.tab_docs,orient='horizontal',height=520);panes.pack(fill='both',expand=True)
        self.doc_panes=panes
        rawframe=ttk.LabelFrame(panes,text='Source text and evidence',padding=6);panes.add(rawframe,weight=1)
        self.raw=tk.Text(rawframe,wrap='word',font=self.fonts['mono'],bg='white',width=45,height=12);self.raw.pack(side='left',fill='both',expand=True)
        sb=ttk.Scrollbar(rawframe,command=self.raw.yview);sb.pack(side='right',fill='y');self.raw.configure(yscrollcommand=sb.set)
        self.doc_fields_container=ttk.Frame(panes);panes.add(self.doc_fields_container,weight=1)
        self.doc_fields=self.scroll_frame(self.doc_fields_container);self.review_vars={};self.owner_review_vars={};self._proposal_assets=[];self._active_doc_id=None
        self.tab_docs=outer
        # The right-hand review form is nested inside the main documents
        # canvas; tag it after all controls exist and again after Tk lays out.
        self._refresh_scroll_bindings()
        self.after_idle(self._refresh_scroll_bindings)

    def set_document_pane(self,mode):
        if not hasattr(self,'doc_panes'):return
        self.update_idletasks();width=max(self.doc_panes.winfo_width(),600)
        fraction={'source':0.72,'fields':0.28,'balanced':0.50}[mode]
        self.doc_panes.sashpos(0,int(width*fraction))

    def choose_ocr(self):
        path=filedialog.askopenfilename(parent=self,title='Choose installed Tesseract engine',filetypes=[('Tesseract executable','tesseract.exe'),('All files','*')])
        if path:
            try:
                Path(engine.OCR_SETTINGS_FILE).write_text(json.dumps({'tesseract_path':path}),encoding='utf-8')
                self.status.set('OCR path configured. First import validates it in the background.')
            except OSError as e:messagebox.showerror(TITLE,str(e),parent=self)

    def import_documents(self,kind='Passport'):
        if self._busy:messagebox.showinfo(TITLE,'An import/export is already running.');return
        paths=filedialog.askopenfilenames(parent=self,title='Import '+kind,filetypes=[
            ('PDF files','*.pdf'),
            ('Image files','*.jpg *.jpeg *.png'),
            ('Excel files','*.xlsx *.xlsm *.xls'),
            ('Text / CSV files','*.txt *.csv'),
            ('All supported files','*.pdf *.jpg *.jpeg *.png *.xlsx *.xlsm *.xls *.txt *.csv'),
            ('All files','*.*'),
        ])
        if not paths:return
        self._commit_person();target=self.current_person;generation=self._generation
        self._busy=True;self.status.set('Reading documents in background...');self.notebook.select(self.tab_docs)
        def work():
            docs=[];errors=[]
            for path in paths:
                try:
                    prop=read_proposal(path,kind)
                    sections=prop.get('tax_sections',[])
                    if len(sections)>1:
                        for section in sections:
                            child=copy.deepcopy(prop);child.pop('tax_sections',None);child['source_document_text']=prop['original_text'];child.update(section)
                            child.update(original_text=section['text'],kind=section['kind'],doc_type=section['kind'],source_pages=section['pages'],reclassification_required=section['kind']!=kind,requested_kind=kind,id=uid(),target_id=target,applied=False)
                            child['warnings']=prop.get('warnings',[])+['Tax section: '+section['kind']+' AY '+section['year']+'. Check person and year separately.'];docs.append(child)
                    else:prop.update(id=uid(),target_id=target,applied=False);docs.append(prop)
                except Exception as e:errors.append(Path(path).name+': '+str(e))
            self.jobs.put(('import',generation,docs,errors))
        threading.Thread(target=work,daemon=True).start()

    def _drain(self):
        try:
            while True:
                kind,generation,result,errors=self.jobs.get_nowait()
                if generation!=self._generation:continue
                if kind=='rate':
                    if result.get('request_id')!=self._rate_request:continue
                    if errors:
                        self.rate_meta=dict(code=result['code'],error=errors[0],source='Automatic request failed');self.rate_status.set('Rate unavailable - enter a reviewed manual rate or Refresh. '+errors[0])
                        if 'Future FX date' in errors[0]:messagebox.showwarning(TITLE,errors[0],parent=self)
                    else:
                        if result.get('requires_date_review') and not result.get('date_reviewed'):
                            if not self.av['fx_date'].get().strip():
                                result['date_reviewed']=True
                                self.rate_status.set('Latest available rate applied for '+result['effective_date']+'; requested date was '+result['requested_date']+'.')
                            elif not messagebox.askyesno(TITLE,'Requested FX date: '+result['requested_date']+'\nProvider effective date: '+result['effective_date']+'\nUse the immediately previous available rate?',parent=self):
                                self.rate_meta=dict(code=result['code'],requested_date=result['requested_date'],error='Provider effective date not accepted');self.rate_status.set('Alternate effective date declined. Enter a manual reviewed rate.');continue
                            else:result['date_reviewed']=True
                        self.rate_meta={k:v for k,v in result.items() if k!='request_id'};self._setting_rate=True
                        try:self.av['rate'].set(result['rate'])
                        finally:self._setting_rate=False
                        from currency_rates import quote_caption
                        self.rate_status.set(('HISTORICAL | ' if result.get('historical') else '')+quote_caption(dict(rate=result['rate'],rate_meta=self.rate_meta)))
                        if result.get('historical'):
                            messagebox.showinfo(TITLE,'Historical FX rate applied for '+result.get('effective_date',result.get('requested_date',''))+'. Review that this rate matches the report date and supporting records.',parent=self)
                    continue
                if kind=='preview':
                    self._busy=False
                    if errors:messagebox.showerror(TITLE,'\n'.join(errors),parent=self)
                    else:self._show_pdf_preview(result);self.status.set('Actual PDF preview ready.')
                    continue
                if kind=='previewpage':
                    if errors:messagebox.showerror(TITLE,'\n'.join(errors),parent=self)
                    elif result['request']==getattr(self,'_preview_render_request',None) and self.preview_window.winfo_exists():
                        from PIL import Image,ImageTk
                        self._preview_photo=ImageTk.PhotoImage(Image.open(result['path']));self.preview_canvas.delete('all');self.preview_canvas.create_image(12,12,image=self._preview_photo,anchor='nw');self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox('all'));self.preview_status.set('Page '+str(result['page']+1)+' / '+str(result['count'])+' | '+str(result['zoom'])+'% | Actual generated PDF. Rebuild after changing inputs.')
                    continue
                if kind=='udin':
                    self.udin_status.set(str(result))
                    if not errors and str(result).startswith('Generated UDIN: '):self.av['udin'].set(str(result).split(': ',1)[1])
                    if errors:messagebox.showwarning(TITLE,'\n'.join(errors),parent=self)
                    continue
                self._busy=False
                if kind=='import':
                    self.pending.extend(result);self.refresh_documents()
                    if result:self.doc_tree.selection_set(result[0]['id']);self.doc_tree.see(result[0]['id']);self._show_doc()
                    self.status.set(f'{len(result)} documents ready for review')
                elif errors:self.status.set('Export failed - see the error message; your previous file is unchanged.')
                else:self.status.set('Saved: '+str(result))
                if errors:messagebox.showerror(TITLE,'\n\n'.join(errors),parent=self)
        except queue.Empty:pass
        except Exception as exc:self._busy=False;self.report_callback_exception(type(exc),exc,None)
        finally:self.after(80,self._drain)

    def report_callback_exception(self,kind,value,tb):
        self._busy=False
        if hasattr(self,'status'):self.status.set('Action failed - review the error below and retry.')
        messagebox.showerror(TITLE,kind.__name__+': '+str(value),parent=self)

    def _reset_doc_review(self):
        self._active_doc_id=None;self.review_vars={};self.owner_review_vars={};self._proposal_assets=[];self._proposal_metadata={}
        self.doc_kind.set('');self.doc_target.set('');self.doc_warning.set('Select or import a document to review.')
        for child in self.doc_fields.winfo_children():child.destroy()
        self.raw.configure(state='normal');self.raw.delete('1.0','end');self.raw.configure(state='disabled')

    def remove_document(self):
        if self._busy:messagebox.showinfo(TITLE,'Wait for the current import/export/preview before removing a document.',parent=self);return
        doc=self.selected_doc()
        if not doc:messagebox.showinfo(TITLE,'Select a document to remove.',parent=self);return
        remove_records=False
        if doc.get('applied'):
            choice=messagebox.askyesnocancel(TITLE,'Remove this document from the case? The original source file is never deleted.\n\nYES: also remove unchanged imported asset/income records and this passport evidence.\nNO: remove document only; keep imported records/evidence.\nCANCEL: make no changes.\n\nApplicant identity fields and manually edited assets/income are always kept.',parent=self)
            if choice is None:return
            remove_records=choice
        elif not messagebox.askyesno(TITLE,'Remove the pending document and its proposal? The source file stays on disk.',parent=self):return
        try:
            self._sync_case()
            from document_records import remove_document
            self._removed_document=remove_document(self.case,doc['id'],remove_records)
            self.pending=[d for d in self.pending if d['id']!=doc['id']];self._reset_doc_review();self.refresh()
            self.status.set('Document removed. Source file and applicant identity kept. '+str(self._removed_document['protected'])+' edited records protected. Undo removal is available.')
        except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self)

    def undo_document_removal(self):
        bundle=getattr(self,'_removed_document',None)
        if not bundle:messagebox.showinfo(TITLE,'No document removal to undo in this session.',parent=self);return
        try:
            from document_records import undo_removal
            undo_removal(self.case,bundle);self.pending=copy.deepcopy(self.case.documents);self._removed_document=None;self.refresh();self.status.set('Document removal undone; later edits were not replaced.')
        except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self)

    def refresh_documents(self):
        sel=self.doc_tree.selection();self.doc_tree.delete(*self.doc_tree.get_children())
        for doc in self.pending:
            p=next((p for p in self.case.people if p.id==doc.get('target_id')),None)
            self.doc_tree.insert('','end',iid=doc['id'],text=Path(doc['path']).name+(' ['+doc['kind']+' AY '+doc.get('year','?')+'; pages '+','.join(map(str,doc['source_pages']))+']' if doc.get('source_pages') else ''),values=(doc.get('kind',doc.get('doc_type','')), 'Applied' if doc.get('applied') else 'Needs review',p.name if p else 'Select target'))
        if sel and self.doc_tree.exists(sel[0]):self.doc_tree.selection_set(sel)

    def selected_doc(self):
        sel=self.doc_tree.selection();return next((d for d in self.pending if sel and d['id']==sel[0]),None)

    def _stash_review(self):
        previous=next((d for d in self.pending if d['id']==getattr(self,'_active_doc_id',None)),None)
        if not previous or previous.get('applied'):return
        if previous['kind']=='Passport':previous['passport_details']={k:v.get() for k,v in self.review_vars.items()}
        elif previous['kind'] in ('ITR','Computation'):
            previous['year']=self.review_vars.get('year',tk.StringVar()).get()
            previous['income']={k:v.get() for k,v in self.review_vars.items() if k!='year'}
        elif self._proposal_assets:
            if getattr(self,'owner_review_vars',{}):previous.setdefault('owner_candidate',{}).update({k:v.get() for k,v in self.owner_review_vars.items()})
            previous['assets']=[dict(asset_name=row[6].get() if len(row)>6 else row[1].get(),amount_candidates=getattr(self,'_proposal_metadata',{}).get(i,{}).get('amount_candidates',[]),category=row[1].get(),amount=row[2].get(),desc=row[3].get(),fields={k:v.get() for k,v in row[4].items()},owner_id=next((pid for pid,label in self._people_labels.items() if len(row)>5 and label==row[5].get()),'')) for i,row in enumerate(self._proposal_assets) if row[0].get()]

    def reclassify_document(self):
        doc=self.selected_doc()
        if not doc or doc.get('applied'):return
        from document_intake import reparse
        self._stash_review();updated=reparse(doc,self.doc_kind.get(),explicit=True)
        doc.clear();doc.update(updated);doc['reclassification_required']=False
        self._active_doc_id=None;self.refresh_documents();self._show_doc()

    def use_reviewed_owner(self,create=False):
        doc=self.selected_doc()
        if not doc or doc.get('applied'):return
        name=self.owner_review_vars.get('name').get().strip()
        if not name:
            messagebox.showwarning(TITLE,'Enter the reviewed owner name in the field above.',parent=self);return
        old_labels=dict(self._people_labels)
        if create:
            person=self.case.add_person('Family / owner')
        else:
            person=self.case.person(self.person_id(self.doc_target.get()))
            if person.name and person.name!=name and not messagebox.askyesno(TITLE,'Replace the selected person name with the reviewed owner name?',parent=self):return
        doc.setdefault('owner_candidate',{})['name']=name
        person.name=name;person.fields['full_name']=name
        father=self.owner_review_vars.get('father_name').get().strip()
        if father and not person.fields.get('father_name'):person.fields['father_name']=father
        person.fields['_reviewed_owner_source']=doc.get('path','')
        if getattr(self,'owner_relation_confirmed',None) is not None and self.owner_relation_confirmed.get():
            target_id=self.person_id(self.owner_relation_target.get());relation=self.owner_relation_choice.get()
            if relation=='Not confirmed' or target_id==person.id:
                messagebox.showwarning(TITLE,'Choose a distinct applicant and a reviewed family relation; self ownership is automatic.',parent=self);return
            self.case.confirm_relationship(target_id,person.id,relation,'User reviewed relationship in '+Path(doc.get('path','source')).name)
        
        doc['target_id']=person.id
        self.current_person=person.id;self._select_person();self.refresh()
        self.doc_target.set(self._people_labels[person.id])
        for row in self._proposal_assets:
            if len(row)>5:
                old_id=next((pid for pid,label in old_labels.items() if label==row[5].get()),None)
                row[5].set(self._people_labels[person.id] if create or old_id==person.id else self._people_labels.get(old_id,row[5].get()))
        self.status.set('Owner name reviewed. Check each asset owner, then Apply import.')

    def _show_doc(self,_=None):
        self._stash_review()
        doc=self.selected_doc()
        if not doc:return
        self._active_doc_id=doc['id']
        self.doc_kind.set(doc['kind'])
        self.doc_target.set(self._people_labels.get(doc.get('target_id'),''))
        self.raw.configure(state='normal');self.raw.delete('1.0','end');self.raw.insert('1.0',doc.get('original_text',doc.get('text','')))
        if doc.get('original_text')!=doc.get('text') and doc.get('text_repairs'):
            self.raw.insert('end','\n\nREADABLE COPY (original above is retained unchanged)\n'+doc.get('text',''))
        if doc.get('runtime_evidence'):
            self.raw.insert('end','\n\nPROCESS DECODE NOTES (original bytes retained in saved case)\n'+'\n'.join(w for ev in doc['runtime_evidence'] for w in ev.get('warnings',[])))
        if doc.get('cells'):self.raw.insert('end','\n\nEXCEL CELL EVIDENCE (values, formulas, emphasis)\n'+json.dumps(doc['cells'],indent=2,ensure_ascii=False,default=str))
        self.raw.configure(state='disabled')
        for w in self.doc_fields.winfo_children():w.destroy()
        self.review_vars={};self.owner_review_vars={};self._proposal_assets=[];self._proposal_metadata={}
        notes=doc.get('warnings',[])
        if doc.get('reclassification_required'):
            self.doc_warning.set('Detected '+doc['kind']+' instead of '+doc.get('requested_kind','selected type')+'. Confirm the type when applying. Full review notes are below the source text.')
        else:self.doc_warning.set((notes[0]+(' Additional review notes below the source text.' if len(notes)>1 else '')) if notes else 'Review the fields and linked person, then apply.')
        if notes:self.raw.configure(state='normal');self.raw.insert('end','\n\nREVIEW NOTES\n'+'\n'.join(notes));self.raw.configure(state='disabled')
        if doc['kind']=='Passport':
            for r,(k,label) in enumerate(PASSPORT_FIELDS.items()):
                v=tk.StringVar(value=doc.get('passport_details',{}).get(k,''));self.review_vars[k]=v;self.field(self.doc_fields,r,label,v)
        elif doc['kind'] in ('ITR','Computation'):
            v=tk.StringVar(value=doc.get('year',''));self.review_vars['year']=v;self.field(self.doc_fields,0,'Assessment year (required)',v)
            for r,(k,label,_) in enumerate(engine.INCOME_FIELDS,1):
                value=doc.get('income',{}).get(k,'');v=tk.StringVar(value=str(value));self.review_vars[k]=v;self.field(self.doc_fields,r,label,v)
            start=len(engine.INCOME_FIELDS)+2
            for r,(key,label) in enumerate([('name','Name detected in ITR'),('address','Address detected in ITR'),('pan','PAN'),('acknowledgement','ITR acknowledgement'),('filing_date','Filing / acknowledgement date'),('financial_year','Financial year')],start):
                var=tk.StringVar(value=doc.get('income_metadata',{}).get(key,''));self.review_vars['_meta_'+key]=var;self.field(self.doc_fields,r,label,var)
        else:
            ownerbox=ttk.LabelFrame(self.doc_fields,text='Review owner name',padding=8);ownerbox.pack(fill='x',pady=(0,8))
            candidate=doc.get('owner_candidate',{})
            self.owner_review_vars={'name':tk.StringVar(value=candidate.get('name','')),'father_name':tk.StringVar(value=candidate.get('father_name',''))}
            self.field(ownerbox,0,'Owner name',self.owner_review_vars['name'])
            self.field(ownerbox,1,'Father name (if stated)',self.owner_review_vars['father_name'])
            owneractions=ttk.Frame(ownerbox);owneractions.grid(row=6,column=0,columnspan=2,sticky='w',pady=4)
            ttk.Button(owneractions,text='Use for selected',command=self.use_reviewed_owner).pack(side='left',padx=(0,6))
            ttk.Button(owneractions,text='Add new owner',command=lambda:self.use_reviewed_owner(create=True)).pack(side='left')
            self.owner_relation_target=tk.StringVar(value=self._people_labels.get(self.case.applicants[0].id,'') if self.case.applicants else '')
            self.owner_relation_choice=tk.StringVar(value='Not confirmed');self.owner_relation_confirmed=tk.BooleanVar(value=False)
            self.field(ownerbox,2,'Relationship to applicant',self.owner_relation_target,[self._people_labels[p.id] for p in self.case.applicants])
            self.field(ownerbox,3,'Owner is their',self.owner_relation_choice,['Not confirmed','Father','Mother','Spouse','Brother','Sister','Son','Daughter','Other'])
            ttk.Checkbutton(ownerbox,text='I reviewed source evidence for this relationship',variable=self.owner_relation_confirmed).grid(row=4,column=0,columnspan=2,sticky='w')
            suggestions=doc.get('assets',[])
            if not suggestions:ttk.Label(self.doc_fields,text='No reliable amount found. Enter reviewed values inline in Assets.\nThe full source remains available here.',wraplength=400).pack(anchor='w')
            for idx,it in enumerate(suggestions):
                frame=ttk.LabelFrame(self.doc_fields,text=f'Proposed item {idx+1}',padding=8);frame.pack(fill='x',pady=8)
                keep=tk.BooleanVar(value=True);ttk.Checkbutton(frame,text='Include this item',variable=keep).grid(row=0,column=0,columnspan=2,sticky='w')
                category=tk.StringVar(value=it['category']);amount=tk.StringVar(value=str(it['amount'] or ''));detail=tk.StringVar(value=engine.strip_marks(it.get('desc','')))
                assetname=tk.StringVar(value=it.get('asset_name') or it['category'])
                self.field(frame,1,'Type',category,list(engine.CATS));self.field(frame,2,'Asset name',assetname);self.field(frame,3,'Value (INR)',amount)
                candidates={}
                for candidate in it.get('amount_candidates',[]):
                    if candidate.get('score',0)<0:continue
                    caption=f"INR {candidate['amount']:,.2f} | {candidate.get('kind','source')} | {candidate.get('text','')[:80]}"
                    candidates[caption]=candidate['amount']
                if candidates:
                    choice=tk.StringVar();selector=self.field(frame,4,'Value candidates',choice,list(candidates))
                    selector.bind('<<ComboboxSelected>>',lambda e,v=choice,a=amount,options=candidates:a.set(str(options[v.get()])))
                self.field(frame,5,'Particulars',detail)
                suggested_owner=it.get('owner_id','')
                if not suggested_owner:
                    matching=[p.id for p in self.case.people if norm(p.name) and norm(p.name)==norm(it.get('fields',{}).get('holder',''))]
                    if len(matching)==1:suggested_owner=matching[0]
                target_person=next((p for p in self.case.people if p.id==self.person_id(self.doc_target.get())),None)
                source_holder=it.get('fields',{}).get('holder','')
                default_owner=self._people_labels.get(suggested_owner,'')
                if not default_owner and source_holder and target_person and norm(source_holder)!=norm(target_person.name):
                    default_owner=''
                    if not any('owner' in str(n).lower() for n in notes):
                        notes.append('Source identifies '+source_holder+' as owner, not the selected person. Review the owner and relationship before applying.')
                owner=tk.StringVar(value=default_owner or (self.doc_target.get() if not source_holder or not target_person or norm(source_holder)==norm(target_person.name) else ''))
                self.field(frame,6,'Owner',owner,list(self._people_labels.values()))
                fields={}
                for r,(k,value) in enumerate(it.get('fields',{}).items(),7):
                    if k in ('holder','relation'):continue
                    v=tk.StringVar(value=value);fields[k]=v;self.field(frame,r,k,v)
                self._proposal_metadata[len(self._proposal_assets)]=copy.deepcopy(it)
                self._proposal_assets.append((keep,category,amount,detail,fields,owner,assetname))

        if doc.get('applied'):
            self.doc_warning.set('Applied record: edit the linked person or asset inline. The original source evidence is retained here.')
            def freeze(widget):
                for child in widget.winfo_children():
                    if child.winfo_class() in ('TEntry','TCombobox','TCheckbutton'):child.configure(state='disabled')
                    freeze(child)
            freeze(self.doc_fields)

    def apply_import(self):
        doc=self.selected_doc()
        if not doc:return
        import import_log
        log_id=doc.get('_import_log_id')
        if not log_id:
            log_id=import_log.start(doc.get('path',''),doc.get('requested_kind',doc.get('kind','')));doc['_import_log_id']=log_id
        import_log.write(log_id,'apply_started',document_kind=doc.get('kind',''))
        if doc.get('applied'):messagebox.showinfo(TITLE,'Already applied. Edit the linked person or asset inline.');return
        try:
            if doc.get('mixed_document'):raise ValueError('Different document types are present. Split the source before applying; original text is retained.')
            if doc.get('reclassification_required'):
                if not messagebox.askyesno(TITLE,'This document looks like '+doc['kind']+' rather than '+doc.get('requested_kind','the selected type')+'. Import it as '+doc['kind']+'?',parent=self):return
                doc['reclassification_required']=False
            target=self.person_id(self.doc_target.get());person=self.case.person(target)
            if not person.name and doc['kind']!='Passport':
                if getattr(self,'owner_review_vars',{}).get('name') and self.owner_review_vars['name'].get().strip():
                    if not messagebox.askyesno(TITLE,'Use the reviewed owner name for the selected unnamed person before importing?',parent=self):return
                    self.use_reviewed_owner();target=self.person_id(self.doc_target.get());person=self.case.person(target)
                else:raise ValueError('Enter Owner name in the review panel, then click Use for selected person. Or select a named applicant under Link to. For tax documents, name the applicant in Applicants first.')
            if doc['kind']=='Passport':
                reviewed=dict(doc,passport_details={k:v.get().strip() for k,v in self.review_vars.items()})
                detected=reviewed['passport_details'].get('full_name','')
                if person.name and detected and person.name.casefold()!=detected.casefold():
                    if not messagebox.askyesno(TITLE,'The passport name differs from the selected person. Link it to this person anyway?',parent=self):return
                conflicts=[k for k,v in reviewed['passport_details'].items() if v and person.fields.get(k) and person.fields[k]!=v]
                replace=False
                if conflicts:replace=messagebox.askyesno(TITLE,'Existing fields differ: '+', '.join(conflicts)+'.\nReplace current values? No retains them and stores the new passport as separate evidence.',parent=self)
                self.case.import_passport(target,reviewed,replace=replace)
                doc['passport_details']=reviewed['passport_details']
            elif doc['kind'] in ('ITR','Computation'):
                year=self.review_vars['year'].get().strip()
                if not year:raise ValueError('Enter the assessment year to avoid comparing different years.')
                name_var=self.review_vars.get('_meta_name')
                source_name=name_var.get().strip() if name_var else doc.get('income_metadata',{}).get('name','').strip()
                if name_var and not source_name:
                    if not messagebox.askyesno(TITLE,'No applicant name was detected in this ITR. Import it for the selected person anyway after reviewing the source?',parent=self):return
                    import_log.write(log_id,'mismatch_override',reason='ITR name missing',target_id=target)
                elif source_name and person.name and norm(source_name)!=norm(person.name):
                    if not messagebox.askyesno(TITLE,'The ITR belongs to '+source_name+', but the selected person is '+person.name+'. Import it for the selected person anyway?',parent=self):return
                    import_log.write(log_id,'mismatch_override',reason='ITR name differs',source_name=source_name,target_name=person.name,target_id=target)
                values={k:money(v.get()) for k,v in self.review_vars.items() if k!='year' and not k.startswith('_meta_') and v.get().strip()}
                if not values:raise ValueError('No income amounts reviewed.')
                record=self.case.add_income(target,values,doc['kind'],doc['path'],year,include=False,metadata={k.removeprefix('_meta_'):v.get().strip() for k,v in self.review_vars.items() if k.startswith('_meta_')},evidence=copy.deepcopy(doc.get('income_evidence',{})))
                from document_records import link_record
                link_record(record,doc)
                doc.update(income={k:float(v) for k,v in values.items()},year=year)
            else:
                # Validate every item before mutating the case.
                if doc.get('sha256') and any(d.get('applied') and d.get('sha256')==doc['sha256'] and d.get('id')!=doc.get('id') for d in self.case.documents):
                    if not messagebox.askyesno(TITLE,'This exact source file was already applied. Import an additional copy deliberately?',parent=self):return
                trial=Case.from_dict(self.case.to_dict())
                for idx,row in enumerate(self._proposal_assets):
                    keep,cat,amount,detail,fields=row[:5]
                    if not keep.get():continue
                    owner_id=self.person_id(row[5].get()) if len(row)>5 else target
                    if keep.get():
                        item=trial.add_asset(cat.get(),amount.get(),owner_id,detail.get(),{k:v.get() for k,v in fields.items()},asset_name=row[6].get() if len(row)>6 else None)
                        item['source_evidence']=dict(document_id=doc.get('id'),path=doc.get('path'),sha256=doc.get('sha256'),proposal=copy.deepcopy(getattr(self,'_proposal_metadata',{}).get(idx,{})))
                        from document_records import fingerprint
                        item['source_evidence']['applied_fingerprint']=fingerprint(item)
                self.case.items[:]=trial.items
                if not self._proposal_assets:raise ValueError('No asset proposals. Enter an item in Assets; do not infer missing values.')
            doc.update(target_id=target,applied=True);self.case.documents.append(copy.deepcopy(doc));self._select_person();self.refresh()
            import_log.write(log_id,'apply_complete',document_kind=doc.get('kind',''),target_id=target)
            import_log.finish(log_id,applied=True)
            self.status.set('Applied to '+(person.name or 'selected person')+'. Evidence retained.')
        except Exception as e:
            import_log.fail(log_id,e);messagebox.showwarning(TITLE,str(e),parent=self)

    def remove_pending(self):
        doc=self.selected_doc()
        if doc and not doc.get('applied'):self.remove_document()

    def _income_tab(self):
        outer=self.tab_tax;self.tab_tax=self.scroll_frame(outer)
        ttk.Label(self.tab_tax,text='ITR figures  -  never added to net assets',style='H2.TLabel').pack(anchor='w')
        ttk.Label(self.tab_tax,text='Import ITR / computation under Documents. Select one reviewed ITR per person and assessment year for the income annexure. Comparison appears only for the same person/year.',style='Hint.TLabel',wraplength=1000).pack(anchor='w',pady=6)
        self.income_tree=ttk.Treeview(self.tab_tax,columns=('person','type','year','total','include'),show='headings',height=5,selectmode='browse')
        for k,label in [('person','Owner'),('type','Document'),('year','Assessment year'),('total','Total income (INR)'),('include','In report')]:self.income_tree.heading(k,text=label);self.income_tree.column(k,width=180)
        self.income_tree.pack(fill='x',pady=8)
        bar=ttk.Frame(self.tab_tax);bar.pack(fill='x')
        ttk.Button(bar,text='Toggle selected ITR in report',command=self.toggle_income).pack(side='left')
        ttk.Button(bar,text='Remove selected record',command=self.remove_income_record).pack(side='left',padx=8)
        ttk.Label(self.tab_tax,text='Comparison',style='H2.TLabel').pack(anchor='w',pady=(20,8))
        self.compare=tk.Text(self.tab_tax,height=8,font=self.fonts['mono'],bg='white');self.compare.pack(fill='both',expand=True)
        # Hidden until an ITR exists; computation-only imports remain reviewable under Documents.
        self.income_owner=tk.StringVar();self.income_owner_cb=ttk.Combobox(self.tab_tax,textvariable=self.income_owner,state='readonly')
        review=ttk.LabelFrame(self.tab_tax,text='Reviewed annual-income composition',padding=12);review.pack(fill='x',pady=12)
        ttk.Label(review,text='Report assessment year').grid(row=0,column=0,sticky='w');self.income_year_cb=ttk.Combobox(review,textvariable=self.av['income_report_year'],state='readonly',width=18);self.income_year_cb.grid(row=0,column=1,sticky='w',padx=8)
        ttk.Button(review,text='Review selected person / year',command=self.load_income_reconciliation).grid(row=0,column=2,padx=8)
        self.reconcile_target=tk.StringVar(value='Select an ITR or computation row, then Review.');ttk.Label(review,textvariable=self.reconcile_target,style='Hint.TLabel',wraplength=900).grid(row=1,column=0,columnspan=3,sticky='w',pady=6)
        self.reconcile_values={};self.reconcile_sources={};self.reconcile_source_boxes={};self.reconcile_options={}
        for row,(key,label) in enumerate([('total_income','Taxable / ITR total'),('agricultural_income','Agricultural income'),('exempt_income','Other exempt (excluding agriculture)')],2):
            value=tk.StringVar();source=tk.StringVar(value='Reviewed manual');self.reconcile_values[key]=value;self.reconcile_sources[key]=source
            self.field(review,row,label+' (INR)',value);box=ttk.Combobox(review,textvariable=source,state='readonly',width=42);box.grid(row=row,column=2,sticky='ew',padx=8);self.reconcile_source_boxes[key]=box
            box.bind('<<ComboboxSelected>>',lambda e,k=key:self.choose_income_source(k))
        self.reconcile_agri=tk.BooleanVar(value=False);self.reconcile_exempt=tk.BooleanVar(value=False);self.reconcile_no_overlap=tk.BooleanVar(value=False)
        ttk.Checkbutton(review,text='Add agricultural income',variable=self.reconcile_agri).grid(row=5,column=0,sticky='w')
        ttk.Checkbutton(review,text='Add other exempt income',variable=self.reconcile_exempt).grid(row=5,column=1,sticky='w')
        ttk.Checkbutton(review,text='I verified these additions are outside taxable income and do not overlap each other',variable=self.reconcile_no_overlap).grid(row=6,column=0,columnspan=3,sticky='w',pady=5)
        ttk.Button(review,text='Confirm reviewed annual income',style='Accent.TButton',command=self.confirm_income_reconciliation).grid(row=7,column=1,sticky='w',pady=8)
        review.columnconfigure(1,weight=1)
        self.tab_tax=outer

    def load_income_reconciliation(self):
        selection=self.income_tree.selection()
        if not selection:messagebox.showinfo(TITLE,'Select a source row for the person/year to review.',parent=self);return
        record=next(r for r in self.case.incomes if r['id']==selection[0]);person_id=record['person_id'];year=record['year']
        from income_intake import reconciliation_proposal
        proposal=reconciliation_proposal(self.case,person_id,year);self._reconcile_key=(person_id,year)
        self.reconcile_target.set(self.case.person(person_id).name+' | AY '+year+(' | Conflicting source components: '+', '.join(proposal['conflicts']) if proposal['conflicts'] else ' | Missing values remain unknown, not zero.'))
        previous=self.case.income_reviews.get(person_id+'|'+year,{})
        for key in self.reconcile_values:
            options={'Reviewed manual':('',None)}
            for rid,kind,value in proposal['sources'][key]:
                source=next(r for r in self.case.incomes if r['id']==rid);caption=kind+' | '+Path(source['source']).name+' | INR '+str(value)+' | '+rid[:6];options[caption]=(rid,value)
            self.reconcile_options[key]=options;self.reconcile_source_boxes[key]['values']=list(options)
            preferred=next((caption for caption,option in options.items() if option[0] and option[0]==previous.get('source_ids',{}).get(key)),None)
            if not preferred:preferred=next((caption for caption in options if caption.startswith('ITR')),next((caption for caption in options if caption!='Reviewed manual'),'Reviewed manual'))
            self.reconcile_sources[key].set(preferred);self.choose_income_source(key)
            if key in previous.get('values',{}):self.reconcile_values[key].set('' if previous['values'][key] is None else str(previous['values'][key]))
        self.reconcile_agri.set(previous.get('include_agriculture',False));self.reconcile_exempt.set(previous.get('include_other_exempt',False));self.reconcile_no_overlap.set(previous.get('no_overlap_confirmed',False))

    def choose_income_source(self,key):
        option=self.reconcile_options.get(key,{}).get(self.reconcile_sources[key].get(),('',None));self.reconcile_values[key].set('' if option[1] is None else str(option[1]))

    def confirm_income_reconciliation(self):
        if not getattr(self,'_reconcile_key',None):messagebox.showinfo(TITLE,'Review a selected source person/year first.',parent=self);return
        try:
            from income_intake import confirm_reconciliation
            person_id,year=self._reconcile_key;sources={k:self.reconcile_options[k].get(self.reconcile_sources[k].get(),('',None))[0] for k in self.reconcile_values}
            result=confirm_reconciliation(self.case,person_id,year,{k:v.get() for k,v in self.reconcile_values.items()},sources,self.reconcile_agri.get(),self.reconcile_exempt.get(),self.reconcile_no_overlap.get())
            self.reconcile_target.set(self.case.person(person_id).name+' | AY '+year+' | Reviewed report income INR '+str(result['report_total'])+' (never added to assets).');self.status.set('Income reconciliation saved. Include the selected ITR and choose the report year to export.')
        except Exception as exc:messagebox.showwarning(TITLE,str(exc),parent=self)

    def refresh_income_table(self):
        years=sorted({r.get('year','') for r in self.case.incomes if r.get('year')});self.income_year_cb['values']=years
        if len(years)==1 and not self.av['income_report_year'].get():self.av['income_report_year'].set(years[0])
        if self.case.has_itr:
            self.notebook.add(self.tab_tax,text='ITR & income')
        else:
            if str(self.tab_tax) in self.notebook.tabs():self.notebook.hide(self.tab_tax)
        self.income_tree.delete(*self.income_tree.get_children())
        for r in self.case.incomes:
            self.income_tree.insert('','end',iid=r['id'],values=(self.case.person(r['person_id']).name,r['document_type'],r.get('year',''),r['values'].get('total_income','Not found'),'Yes' if r.get('include') else 'No'))
        self.compare.configure(state='normal');self.compare.delete('1.0','end')
        rows=self.case.income_comparison()
        self.compare.insert('end','\n'.join(f"{self.case.person(pid).name} | AY {year} | {key}: ITR {a} / computation {b} | {status}" for pid,year,key,a,b,status in rows) if rows else 'No unique matching ITR + computation pair for the same person and year.')
        self.compare.configure(state='disabled')

    def toggle_income(self):
        sel=self.income_tree.selection()
        if not sel:return
        rec=next(r for r in self.case.incomes if r['id']==sel[0])
        if rec['document_type']!='ITR':messagebox.showwarning(TITLE,'Only ITR figures are included, not a duplicate computation.');return
        if not rec.get('include'):
            for r in self.case.incomes:
                if r['person_id']==rec['person_id'] and r.get('year')==rec.get('year'):r['include']=False
        rec['include']=not rec.get('include',False);self.refresh_income_table()

    def remove_income_record(self):
        sel=self.income_tree.selection()
        if sel:self.case.incomes[:]=[r for r in self.case.incomes if r['id']!=sel[0]];self.refresh_income_table()

    def _report_tab(self):
        report_actions=ttk.Frame(self.tab_report);report_actions.pack(fill='x',pady=(0,8))
        ttk.Button(report_actions,text='Preview final PDF',style='Accent.TButton',command=self.preview_report).pack(side='left',padx=(0,8))
        for kind,label in [('xlsx','Export Excel'),('docx','Export Word'),('pdf','Export PDF')]:ttk.Button(report_actions,text=label,style='Accent.TButton',command=lambda k=kind:self.export(k)).pack(side='left',padx=4)
        body=self.scroll_frame(self.tab_report)
        ttk.Label(body,text='Review & export',style='H2.TLabel').grid(row=0,column=0,columnspan=3,sticky='w',pady=10)
        from currency_rates import COUNTRY_CODES
        fields=[('country','Destination country','combo',list(COUNTRY_CODES)+['Other / choose currency']),('fx_date','FX date (blank = statement date)','text',None)]+[f for f in engine.App.APP_FIELDS if f[0] not in ('title','name','relation','parent','passport','address') and not f[0].startswith('co_')]
        self.purpose_options=['Study Visa','Visitor Visa','Tourist Visa','Work Visa','Spouse Visa','Dependent Visa','PR Application','Business Visa','Family Visit','Immigration / Embassy Purpose','Other']
        for row,(k,label,typ,opts) in enumerate(fields,1):
            if k=='purpose':opts=self.purpose_options
            w=self.field(body,row,label.replace('Net worth','Net assets'),self.av[k],opts if typ in ('combo','readonly') else None)
            if k=='purpose':
                self.purpose_cb=w
                ttk.Button(body,text='Add purpose',command=self.add_purpose).grid(row=row,column=2,sticky='w',padx=8)
                ttk.Button(body,text='Delete purpose',command=self.delete_purpose).grid(row=row,column=2,sticky='w',padx=(105,8))
            if k=='country':w.configure(state='normal')
            if k in ('engagement_date','statement_date','cert_date'):w.bind('<FocusOut>',lambda e,key=k:self.on_date_focusout(key))
        row=len(fields)+2
        ttk.Button(body,text='Refresh rate',command=self.fetch_exchange_rate).grid(row=row,column=1,sticky='w',pady=8)
        self.rate_status=tk.StringVar(value='Select a currency to fetch INR per 1 foreign unit. Manual rate entry is also available.')
        ttk.Label(body,textvariable=self.rate_status,style='Hint.TLabel',wraplength=420).grid(row=row,column=2,sticky='w',padx=10)
        self.av['currency'].trace_add('write',self._currency_changed);self.av['rate'].trace_add('write',self._manual_rate_changed)
        self.av['country'].trace_add('write',self._country_changed);self.av['statement_date'].trace_add('write',self._fx_date_changed);self.av['fx_date'].trace_add('write',self._fx_date_changed)
        self.formula_mode=tk.StringVar(value='double')
        self.formula_mode.trace_add('write',lambda *_:self._formula_changed())
        ttk.Label(body,text='Formula policy').grid(row=row+1,column=0,sticky='w')
        ttk.Combobox(body,textvariable=self.formula_mode,state='readonly',values=['double','single']).grid(row=row+1,column=1,sticky='w')
        ttk.Label(body,text='Default DOUBLE reproduces Sheet1 C3 spouse-first function. SINGLE retains its A13 \u0022Mrs\u0022 condition.\nBoth source templates contain broken #REF! owner links; annual income DOUBLE excludes its first block.\nThis export repairs those references and totals all selected ITRs; VBA SPELLNUMBERINDIAN is replaced locally.\nAmounts in foreign currency use ROUND(value/rate,0) per item, then sum, exactly as the templates.\nExcel formulas recalculate when opened in Excel; no macro is executed. See docs/FORMULA_REVIEW.md.',style='Hint.TLabel',wraplength=900).grid(row=row+2,column=0,columnspan=3,sticky='w',pady=12)
        actions=ttk.Frame(body);actions.grid(row=row+3,column=0,columnspan=3,sticky='w',pady=10)
        ttk.Button(actions,text='UDIN portal (manual)',command=lambda:webbrowser.open('https://udin.icai.org/')).pack(side='left',padx=5)
        ttk.Button(actions,text='Open UDIN assistant',command=self.trigger_udin_generation).pack(side='left',padx=5)
        portal=ttk.Frame(body);portal.grid(row=row+5,column=0,columnspan=3,sticky='ew',pady=6)
        ttk.Button(portal,text='Request OTP (after review)',command=lambda:self.udin_action('otp')).pack(side='left',padx=5)
        ttk.Button(portal,text='Read generated UDIN',command=lambda:self.udin_action('read')).pack(side='left',padx=5)
        self._print_settings(body,row+7)
        self.udin_status=tk.StringVar(value='UDIN selectors unverified live. User controls login, OTP entry and final generation.')
        ttk.Label(body,textvariable=self.udin_status,style='Hint.TLabel',wraplength=900).grid(row=row+6,column=0,columnspan=3,sticky='w',pady=8)
        ttk.Label(body,text='Raw passports and unknown OCR text stay in the saved case, not in the printed report.\nNames, passport/address fields and relationship emphasis are visible in Applicants.\nExcel uses fixed template bold; the toggles apply to Word/PDF narrative. Word/PDF preserve the existing CA narrative.',style='Hint.TLabel',wraplength=900).grid(row=row+4,column=0,columnspan=3,sticky='w',pady=8)

    def add_purpose(self):
        value=simpledialog.askstring(TITLE,'Enter a new submission purpose:',parent=self)
        if not value or not value.strip():return
        value=value.strip()
        if value.casefold() not in {item.casefold() for item in self.purpose_options}:self.purpose_options.append(value)
        self.purpose_cb.configure(values=self.purpose_options);self.av['purpose'].set(value)

    def delete_purpose(self):
        value=self.av['purpose'].get().strip()
        defaults={'Study Visa','Visitor Visa','Tourist Visa','Work Visa','Spouse Visa','Dependent Visa','PR Application','Business Visa','Family Visit','Immigration / Embassy Purpose','Other'}
        if not value or value.casefold() in {item.casefold() for item in defaults}:
            messagebox.showinfo(TITLE,'Select a custom purpose to delete. Common purposes cannot be deleted.',parent=self);return
        if messagebox.askyesno(TITLE,'Delete custom purpose "'+value+'"?',parent=self):
            self.purpose_options=[item for item in self.purpose_options if item.casefold()!=value.casefold()]
            self.purpose_cb.configure(values=self.purpose_options);self.av['purpose'].set('Study Visa')

    def _print_settings(self,body,row):
        self.layout_open=tk.BooleanVar(value=False);host=ttk.Frame(body);host.grid(row=row+1,column=0,columnspan=3,sticky='ew')
        ttk.Checkbutton(body,text='Print layout, sections & Excel print areas',variable=self.layout_open,command=lambda:host.grid() if self.layout_open.get() else host.grid_remove()).grid(row=row,column=0,columnspan=2,sticky='w',pady=12)
        host.grid_remove();self.layout_vars={}
        for index,(key,label,default,options) in enumerate([('paper','Paper','A4',['A4','Legal','Letter']),('orientation','Orientation','Portrait',['Portrait','Landscape']),('top','Top margin (mm)','15',None),('bottom','Bottom margin (mm)','15',None),('left','Left margin (mm)','15',None),('right','Right margin (mm)','15',None),('excel_scale','Excel scaling','Fit width',['Fit width','Actual size']),('pdf_page_range','PDF pages (blank = all)','',None)]):
            var=tk.StringVar(value=default);self.layout_vars[key]=var;self.field(host,index,label,var,options);var.trace_add('write',lambda *_:self.invalidate_preview())
        from print_layout import SECTIONS
        self.layout_sections={}
        for index,name in enumerate(SECTIONS):
            var=tk.BooleanVar(value=True);self.layout_sections[name]=var;ttk.Checkbutton(host,text='Print '+name,variable=var,command=self.invalidate_preview).grid(row=index,column=2,sticky='w',padx=12)
        self.excel_areas={};self.area_sheet=tk.StringVar(value='certificate');self.area_value=tk.StringVar()
        areas=ttk.LabelFrame(host,text='Excel print area (optional, per worksheet)',padding=8);areas.grid(row=8,column=0,columnspan=3,sticky='ew',pady=8)
        ttk.Combobox(areas,textvariable=self.area_sheet,state='readonly',values=['intro','certificate','immovable','movable','annual income','liabilities','SUMMARY','Sheet1'],width=18).pack(side='left',padx=4)
        ttk.Entry(areas,textvariable=self.area_value,width=18).pack(side='left',padx=4)
        self.area_sheet.trace_add('write',lambda *_:self.area_value.set(self.excel_areas.get(self.area_sheet.get(),'')))
        ttk.Button(areas,text='Set / clear range',command=self.set_excel_area).pack(side='left',padx=4)
        self.area_status=tk.StringVar(value='Blank = generated used range. Example A1:F40. Validated against generated rows on export.')
        ttk.Label(host,textvariable=self.area_status,style='Hint.TLabel',wraplength=900).grid(row=9,column=0,columnspan=3,sticky='w')
        ttk.Label(host,text='Preview is the actual generated PDF, including paper, margins, selected sections, letterpad and signature. Excel/Word paginate in their own apps; Excel A1 print areas and PDF page ranges are separate. Custom letterpad is selected in Firm settings.',style='Hint.TLabel',wraplength=900).grid(row=10,column=0,columnspan=3,sticky='w',pady=8)

    def set_excel_area(self):
        value=self.area_value.get().strip()
        if value and not __import__('re').fullmatch(r'\$?[A-Z]{1,3}\$?\d+:\$?[A-Z]{1,3}\$?\d+',value):messagebox.showwarning(TITLE,'Use an Excel A1 range, for example A1:F40, or leave blank.',parent=self);return
        if value:self.excel_areas[self.area_sheet.get()]=value
        else:self.excel_areas.pop(self.area_sheet.get(),None)
        self.area_status.set(' | '.join(k+': '+v for k,v in self.excel_areas.items()) or 'All worksheets use their generated used range.');self.invalidate_preview()

    def _get_print_layout(self):
        return dict(paper=self.layout_vars['paper'].get(),orientation=self.layout_vars['orientation'].get(),margins_mm={k:self.layout_vars[k].get() for k in ('top','bottom','left','right')},excel_scale=self.layout_vars['excel_scale'].get(),pdf_page_range=self.layout_vars['pdf_page_range'].get(),sections=[k for k,v in self.layout_sections.items() if v.get()],excel_print_areas=copy.deepcopy(self.excel_areas))

    def _load_print_layout(self):
        saved=self.case.report.get('print_layout') or {}
        for key,var in self.layout_vars.items():var.set(saved.get('margins_mm',{}).get(key,'15') if key in ('top','bottom','left','right') else saved.get(key,{'paper':'A4','orientation':'Portrait','excel_scale':'Fit width','pdf_page_range':''}[key]))
        for key,var in self.layout_sections.items():var.set(key in saved.get('sections',list(self.layout_sections)))
        self.excel_areas=copy.deepcopy(saved.get('excel_print_areas',{}));self.area_value.set(self.excel_areas.get(self.area_sheet.get(),''))

    def invalidate_preview(self):
        if hasattr(self,'preview_status'):self.preview_status.set('Data / layout may have changed. Rebuild before printing; stale previews cannot be opened/printed.')

    def preview_report(self):
        if self._busy:messagebox.showinfo(TITLE,'Wait for the current import/export/preview.',parent=self);return
        try:
            self._sync_case();report_export.report_content(self.case)
            from preview_render import case_fingerprint
            snapshot=Case.from_dict(self.case.to_dict());fingerprint=case_fingerprint(snapshot)
            if not getattr(self,'_preview_temp',None):self._preview_temp=tempfile.TemporaryDirectory(prefix='net_asset_preview_',ignore_cleanup_errors=True)
            path=Path(self._preview_temp.name)/('report_'+uid()+'.pdf');generation=self._generation;self._busy=True;self.status.set('Building actual PDF preview in background...')
            def work():
                try:
                    report_export.export(snapshot,path,'pdf');self.jobs.put(('preview',generation,dict(path=str(path),fingerprint=fingerprint),[]))
                except Exception as exc:self.jobs.put(('preview',generation,None,[type(exc).__name__+': '+str(exc)]))
            threading.Thread(target=work,daemon=True).start()
        except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self)

    def _show_pdf_preview(self,result):
        self._preview_path=result['path'];self._preview_fingerprint=result['fingerprint'];self._preview_page=0
        if not getattr(self,'preview_window',None) or not self.preview_window.winfo_exists():
            win=tk.Toplevel(self);self.preview_window=win;win.title('Final PDF preview - not Excel pagination');
            from ui_design import preview_geometry
            geometry,minimum=preview_geometry(self.winfo_screenwidth(),self.winfo_screenheight());win.geometry(geometry);win.minsize(*minimum)
            bar=ttk.Frame(win,padding=8);bar.pack(fill='x')
            for label,command in [('Previous',lambda:self.preview_page(-1)),('Next',lambda:self.preview_page(1)),('Last',lambda:self.preview_page('last')),('Rebuild',self.preview_report),('Print / Open PDF',self.open_preview_pdf)]:ttk.Button(bar,text=label,command=command).pack(side='left',padx=3)
            self.preview_zoom=tk.StringVar(value='100');zoom=ttk.Combobox(bar,textvariable=self.preview_zoom,state='readonly',values=['50','75','100','125','150','200'],width=5);zoom.pack(side='left',padx=8);zoom.bind('<<ComboboxSelected>>',lambda e:self.preview_page(0))
            self.preview_status=tk.StringVar();ttk.Label(win,textvariable=self.preview_status,wraplength=900,style='Hint.TLabel').pack(fill='x',padx=10)
            body=ttk.Frame(win);body.pack(fill='both',expand=True);self.preview_canvas=tk.Canvas(body,bg='#D8DEE2',highlightthickness=0);self.preview_canvas.grid(row=0,column=0,sticky='nsew');vs=ttk.Scrollbar(body,orient='vertical',command=self.preview_canvas.yview);vs.grid(row=0,column=1,sticky='ns');hs=ttk.Scrollbar(body,orient='horizontal',command=self.preview_canvas.xview);hs.grid(row=1,column=0,sticky='ew');self.preview_canvas.configure(yscrollcommand=vs.set,xscrollcommand=hs.set);self.preview_canvas._scroll_canvas=self.preview_canvas;self.preview_canvas.bindtags(('NARScroll',)+self.preview_canvas.bindtags());body.rowconfigure(0,weight=1);body.columnconfigure(0,weight=1)
        self.preview_window.deiconify();self.preview_window.lift();self.preview_page(0)

    def _preview_is_current(self):
        self._sync_case()
        from preview_render import case_fingerprint
        if case_fingerprint(self.case)!=getattr(self,'_preview_fingerprint',None):
            self.invalidate_preview();messagebox.showwarning(TITLE,'Case or print layout changed. Rebuild the PDF preview first.',parent=self.preview_window);return False
        return True

    def preview_page(self,delta):
        try:
            if not self._preview_is_current():return
            import pymupdf
            with pymupdf.open(self._preview_path) as pdf:count=len(pdf)
            page=count-1 if delta=='last' else max(0,min(count-1,self._preview_page+delta));self._preview_page=page
            request=uid();self._preview_render_request=request;generation=self._generation;output=Path(self._preview_temp.name)/(request+'.png');zoom=int(self.preview_zoom.get());self.preview_status.set('Rendering page '+str(page+1)+' of '+str(count)+'...')
            def work():
                try:
                    from preview_render import render_pdf_page
                    result=render_pdf_page(self._preview_path,page,zoom,output);result['request']=request;self.jobs.put(('previewpage',generation,result,[]))
                except Exception as exc:self.jobs.put(('previewpage',generation,None,[str(exc)]))
            threading.Thread(target=work,daemon=True).start()
        except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self)

    def open_preview_pdf(self):
        try:
            if not self._preview_is_current():return
            webbrowser.open(Path(self._preview_path).as_uri());self.preview_status.set('Opened final PDF. Use the viewer Print dialog (Ctrl+P) to choose printer and page range. No automatic printer submission.')
        except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self)

    def _formula_changed(self):
        self.case.formula_mode=self.formula_mode.get()
        if hasattr(self,'parent_preview'):self.parent_preview.set('Report line: '+self.case.parent_line(self.case.person(self.current_person)))

    def show_relationships(self):
        win=tk.Toplevel(self);win.title('Review source-supported relationships');win.geometry('1000x620')
        ttk.Label(win,text='Name matches are suggestions, not established family relationships.',style='H2.TLabel').pack(anchor='w',padx=16,pady=16)
        tree=ttk.Treeview(win,columns=('subject','relative','relation','evidence'),show='headings',height=4,selectmode='browse');tree.pack(fill='both',expand=True,padx=16)
        for k in ('subject','relative','relation','evidence'):tree.heading(k,text=k.title());tree.column(k,width=200)
        candidates=self.case.relationship_candidates()
        for i,r in enumerate(candidates):tree.insert('','end',iid=str(i),values=(self.case.person(r['subject']).name,self.case.person(r['relative']).name,r['relation'],r['evidence']))
        form=ttk.Frame(win,padding=16);form.pack(fill='x')
        subject=tk.StringVar();relative=tk.StringVar();relation=tk.StringVar(value='Spouse');evidence=tk.StringVar()
        self.field(form,0,'Applicant (relationship is to)',subject,list(self._people_labels.values()));self.field(form,1,'Relative / owner',relative,list(self._people_labels.values()));self.field(form,2,'Reviewed relation',relation,['Father','Mother','Spouse','Brother','Sister','Sibling','Son','Daughter','Other']);self.field(form,3,'Evidence / source confirmation',evidence)
        def select(_):
            sel=tree.selection()
            if sel:
                r=candidates[int(sel[0])];subject.set(self._people_labels[r['subject']]);relative.set(self._people_labels[r['relative']]);relation.set(r['relation']);evidence.set(r['evidence'])
        tree.bind('<<TreeviewSelect>>',select)
        def confirm():
            try:self.case.confirm_relationship(self.person_id(subject.get()),self.person_id(relative.get()),relation.get(),evidence.get());self.status.set('Relationship explicitly reviewed.');win.destroy()
            except ValueError as e:messagebox.showwarning(TITLE,str(e),parent=win)
        ttk.Button(form,text='Confirm reviewed relationship',style='Accent.TButton',command=confirm).grid(row=4,column=1,sticky='w',pady=10)

    def refresh(self,select=None):
        self.items=self.case.items
        self.people_tree.delete(*self.people_tree.get_children())
        for p in self.case.people:self.people_tree.insert('','end',iid=p.id,text=(p.name or 'Unnamed')+'  |  '+p.role)
        self.people_tree.selection_set(self.current_person);self._update_people_choices()
        self.tree.delete(*self.tree.get_children())
        groups=[('A','Immovable assets',lambda i:i['kind']=='asset' and i['category']=='Immovable Property'),('B','Movable assets',lambda i:i['kind']=='asset' and i['category']!='Immovable Property'),('D','Liabilities',lambda i:i['kind']=='liability')]
        for key,label,predicate in groups:
            entries=[(i,it) for i,it in enumerate(self.case.items) if predicate(it)]
            if not entries:continue
            self.tree.insert('','end',iid='group:'+key,values=(key+' | '+label,'','','Subtotal',f"{sum(it['amount'] for _,it in entries):,.2f}"),tags=('group',))
            for i,item in entries:
                it=report_export.render_item(self.case,item) if item.get('owner_id') else item;owner=self.case.person(it['owner_id']) if it.get('owner_id') else None
                self.tree.insert('','end',iid=str(i),values=(it.get('asset_name',it['category']),owner.name if owner else 'REVIEW OWNER',self.case.report_owner_relation(owner.id) if owner else 'Review ownership',engine.strip_marks(it['desc']),f"{it['amount']:,.2f}"))
        if select is not None and self.tree.exists(str(select)):self.tree.selection_set(str(select))
        t=self.case.totals();self.totals_lbl.configure(text=f"Assets INR {t['A']+t['B']:,.2f}    Liabilities INR {t['C']:,.2f}    Net assets INR {t['net']:,.2f}")
        self.refresh_documents();self.refresh_income_table()

    def selected_index(self):
        selection=self.tree.selection()
        return int(selection[0]) if selection and selection[0].isdigit() else None

    def show_asset_detail(self,_=None):
        index=self.selected_index()
        if index is None:return
        item=self.case.items[index]
        if item.get('owner_id'):
            item=report_export.render_item(self.case,item);owner=self.case.person(item['owner_id'])
            identity=self.case.parent_line(owner)
            text='Asset: '+item.get('asset_name',item['category'])+'\nOwner: '+owner.name+(' | Owner identity: '+identity if identity else '')+'\nRelationship to applicant(s): '+self.case.report_owner_relation(owner.id)+'\n'+engine.strip_marks(item['desc'])+'\n'+engine.strip_marks(item.get('note',''))
        else:text='Review the asset owner before export.\n'+engine.strip_marks(item['desc'])
        self.asset_detail.configure(state='normal');self.asset_detail.delete('1.0','end');self.asset_detail.insert('1.0',text);self.asset_detail.configure(state='disabled')

    def refresh_totals(self):
        if hasattr(self,'totals_lbl'):self.refresh()

    def _sync_case(self):
        self._stash_review()
        self._commit_person();self.case.report={k:v.get().strip() for k,v in self.av.items()};self.case.report['rate_meta']=copy.deepcopy(self.rate_meta);self.case.report['print_layout']=self._get_print_layout();self.case.formula_mode=self.formula_mode.get()
        self.case.settings=self.get_ca_dict();self.case.settings.pop('icai_pwd',None);self.case.settings.pop('icai_id',None)
        # Snapshot unresolved proposal review edits too, so a saved pending import is not lost.
        doc=self.selected_doc()
        if doc and not doc.get('applied'):
            if doc['kind']=='Passport':doc['passport_details']={k:v.get() for k,v in self.review_vars.items()}
        accepted={d['id']:d for d in self.case.documents}
        for d in self.pending:accepted[d['id']]=copy.deepcopy(d)
        self.case.documents=list(accepted.values())

    def _mark_case_clean(self):
        from preview_render import case_fingerprint
        self._saved_case_fingerprint=case_fingerprint(self.case)

    def _case_is_dirty(self):
        from preview_render import case_fingerprint
        self._sync_case()
        return case_fingerprint(self.case)!=getattr(self,'_saved_case_fingerprint',None) or App._pending_asset_changes(self)

    def _confirm_discard(self,action):
        if not App._case_is_dirty(self):return True
        return messagebox.askyesno(TITLE,action+'? There are unsaved changes, including any unapplied asset edit. Save or apply them first if needed.',parent=self)

    def save_client(self,save_as=False):
        try:
            self._sync_case()
            p=self.client_file if self.client_file and not save_as else filedialog.asksaveasfilename(parent=self,title='Export / Save private case JSON',defaultextension='.json',initialfile=Path(self.client_file).name if self.client_file else 'Net Asset Report case.json',filetypes=[('Private case JSON (contains personal evidence)','*.json')],confirmoverwrite=True)
            if not p:return
            self.case.save(p);self.client_file=str(p);App._mark_case_clean(self);self.status.set('Case JSON saved (private evidence included). Save reuses this path; Save as creates another file.')
        except Exception as e:messagebox.showerror(TITLE,'Could not save case: '+str(e),parent=self)

    def open_client(self):
        if self._busy:messagebox.showinfo(TITLE,'Wait for the current import/export to finish.',parent=self);return
        p=filedialog.askopenfilename(parent=self,title='Import / Open case JSON for changes',filetypes=[('Case JSON','*.json')])
        if not p:return
        if not App._confirm_discard(self,'Replace the current case'):return
        try:
            loaded=Case.load(p)
            self._loading_case=True
            try:
                self.case=loaded;self._udin_session=None;self._reconcile_key=None;self._removed_document=None;self._generation+=1;self._rate_request+=1;self.current_person=self.case.people[0].id;self.pending=copy.deepcopy(self.case.documents)
                for d in self.pending:d.setdefault('id',uid());d.setdefault('kind',d.get('doc_type','Assets'));d.setdefault('applied',True)
                for k,v in self.av.items():v.set(self.case.report.get(k,'' if k!='currency' else 'None'))
                for k,v in self.sv.items():v.set(self.case.settings.get(k,''))
                self.rate_meta=copy.deepcopy(self.case.report.get('rate_meta',{}));self.rate_status.set('Saved rate: '+str(self.rate_meta.get('source','Manual / legacy, date not supplied'))+' | '+str(self.rate_meta.get('as_of','not supplied'))+'; Refresh if outdated.')
                self.signature_image=copy.deepcopy(self.case.settings.get('signature_image'));self.signature_enabled.set(self.case.settings.get('signature_enabled',False));self._signature_label();self.lh_first.set(self.case.settings.get('letterhead_first_page',True))
                self._load_print_layout();self.letterpad=copy.deepcopy(self.case.settings.get('letterpad'));
                if self.letterpad and self.letterpad.get('mode')=='Whole-page letterpad' and not self.letterpad.get('background'):messagebox.showwarning(TITLE,'This older case contains cropped letterpad strips only. Re-select the original whole-page image/PDF in Firm settings to restore its full background; no missing pixels can be reconstructed.',parent=self)
                self.letterpad_enabled.set(bool(self.letterpad and self.letterpad.get('enabled')));self.letterpad_mode.set((self.letterpad or {}).get('mode','Header image'));self.letterpad_status.set((self.letterpad or {}).get('source_name','No custom letterpad selected'));self.formula_mode.set(self.case.formula_mode);self._active_doc_id=None;self._select_person();self.refresh();self.client_file=str(p)
            finally:self._loading_case=False
            self.clear_asset();self._sync_case();App._mark_case_clean(self)
            missing=[Path(d.get('path','')).name for d in self.case.documents if d.get('path') and not Path(d['path']).exists()]
            self.status.set('Case opened for editing.'+(' Original source files unavailable: '+', '.join(missing)+'. Saved extraction evidence retained.' if missing else ''))
        except Exception as e:messagebox.showerror(TITLE,'Could not load case: '+str(e),parent=self)

    def new_client(self):
        if self._busy:return
        if not App._confirm_discard(self,'Start a new case'):return
        self.case=Case();self._udin_session=None;self._reconcile_key=None;self._removed_document=None;self._generation+=1;self._rate_request+=1;self.rate_meta={};self.current_person=self.case.people[0].id;self.pending=[];self.client_file=None
        for k in self.av:self.av[k].set('None' if k=='currency' else '')
        today=datetime.date.today()
        for k in ('engagement_date','statement_date','cert_date'):self.av[k].set(today.strftime('%d-%m-%Y' if k=='statement_date' else '%d.%m.%Y'))
        self.av['purpose'].set('Study Visa');self.av['authority'].set('immigration or embassy authorities')
        self._load_print_layout();self.formula_mode.set('double');self._active_doc_id=None
        self._select_person();self.clear_asset();self.refresh();self._sync_case();App._mark_case_clean(self);self.status.set('New case')

    def export(self,kind):
        if self._busy:messagebox.showinfo(TITLE,'Wait for the current import/export to finish.',parent=self);return
        try:self._sync_case();report_export.report_content(self.case)
        except Exception as e:messagebox.showwarning(TITLE,str(e),parent=self);return
        warnings=self.case.formula_warnings()
        if warnings and getattr(self,'tk',None) is not None and not messagebox.askyesno(TITLE,'Report date / source formula checks:\n\n'+'\n'.join(warnings)+'\n\nExport this literal source result after your review?',parent=self):return
        p=filedialog.asksaveasfilename(parent=self,defaultextension='.'+kind,initialfile='Net Asset Report.'+kind,filetypes=[(kind.upper(),'*.'+kind)],confirmoverwrite=True)
        if not p:return
        snapshot=Case.from_dict(self.case.to_dict());generation=self._generation;self._busy=True;self.status.set('Exporting in background...')
        def work():
            try:
                from file_ops import atomic_write
                atomic_write(p,lambda temporary:report_export.export(snapshot,temporary,kind),'.'+kind)
                self.jobs.put(('export',generation,p,[]))
            except Exception as e:self.jobs.put(('export',generation,'',[type(e).__name__+': '+str(e)]))
        threading.Thread(target=work,daemon=True).start()

    def _country_changed(self,*_):
        if self._loading_case:return
        from currency_rates import country_code
        code=country_code(self.av['country'].get())
        if not code:
            self._rate_request+=1;self._setting_rate=True
            try:self.av['rate'].set('')
            finally:self._setting_rate=False
            self.rate_meta={};self.rate_status.set('Country/currency is not uniquely mapped. Choose currency explicitly; no rate is assumed.');return
        choice=next((s for s in engine.CURRENCIES if s.startswith(code+' - ')),None)
        if choice:
            if self.av['currency'].get()!=choice:self.av['currency'].set(choice)
            else:self._fx_date_changed()

    def _fx_date_changed(self,*_):
        if self._loading_case:return
        self._rate_request+=1;self._setting_rate=True
        try:self.av['rate'].set('')
        finally:self._setting_rate=False
        self.rate_meta={}
        if getattr(self,'_rate_debounce',None):
            try:self.after_cancel(self._rate_debounce)
            except tk.TclError:pass
        self._rate_debounce=self.after(450,self.fetch_exchange_rate)
        self.rate_status.set('FX/report date changed. Previous rate invalidated; checking the chosen date...')

    def _currency_changed(self,*_):
        if self._loading_case:return
        self._rate_request+=1;self._setting_rate=True
        try:self.av['rate'].set('')
        finally:self._setting_rate=False
        self.rate_meta={}
        if self.av['currency'].get()=='None':self.rate_status.set('Foreign currency not selected.');return
        self.fetch_exchange_rate()

    def _manual_rate_changed(self,*_):
        if self._setting_rate or self._loading_case:return
        from currency_rates import code_from_selection
        self._rate_request+=1
        self.rate_meta=dict(code=code_from_selection(self.av['currency'].get()),source='Manual user entry',as_of=datetime.datetime.now().strftime('%Y-%m-%d %H:%M IST')+' (market date not verified)',manual=True)
        try:
            from currency_rates import selected_date
            requested=selected_date({k:v.get() for k,v in self.av.items()}).isoformat();self.rate_meta.update(requested_date=requested,effective_date=requested)
        except ValueError:pass
        self.rate_status.set('Manual INR per 1 foreign unit for the chosen FX date. Market rate/date not independently verified.')

    def fetch_exchange_rate(self,*_):
        from currency_rates import code_from_selection,fetch_quote_for_date,selected_date
        code=code_from_selection(self.av['currency'].get())
        if not code:self.rate_status.set('Choose a foreign currency first.');return
        try:requested=selected_date({k:v.get() for k,v in self.av.items()})
        except ValueError as exc:self.rate_status.set(str(exc));self.rate_meta=dict(code=code,error=str(exc));return
        self._rate_request+=1;request_id=self._rate_request;generation=self._generation
        self._setting_rate=True
        try:self.av['rate'].set('')
        finally:self._setting_rate=False
        self.rate_meta=dict(code=code,pending=True);self.rate_status.set('Fetching '+code+' to INR in background...')
        def work():
            try:quote=fetch_quote_for_date(code,requested);quote['request_id']=request_id;self.jobs.put(('rate',generation,quote,[]))
            except Exception as exc:self.jobs.put(('rate',generation,dict(code=code,request_id=request_id),[str(exc)]))
        threading.Thread(target=work,daemon=True).start()

    def load_profiles(self):
        try:engine.App.load_profiles(self)
        except (OSError,ValueError,TypeError):self.ca_profiles={}
        self.ca_profiles={name:strip_secrets(data) for name,data in self.ca_profiles.items() if isinstance(data,dict)}

    def _build_settings_tab(self):
        outer=self.tab_settings;body=self.scroll_frame(outer);self.tab_settings=body
        engine.App._build_settings_tab(self);self.tab_settings=outer
        profile_frame=body.grid_slaves(row=0,column=0)[0]
        for child in profile_frame.winfo_children():child.destroy()
        line=ttk.Frame(profile_frame);line.pack(fill='x');ttk.Label(line,text='Saved CA profiles').pack(side='left')
        self.profile_cb=ttk.Combobox(line,state='readonly',width=32);self.profile_cb.pack(side='left',padx=12);self.update_profile_dropdown()
        actions=ttk.Frame(profile_frame);actions.pack(fill='x',pady=8)
        for label,command in [('Load CA',self.load_profile),('Update CA',self.update_current_profile),('Add CA',self.save_new_profile),('Remove CA',self.remove_ca_profile),('Clear form',self.clear_ca_form)]:ttk.Button(actions,text=label,command=command).pack(side='left',padx=(0,6))
        row=len(self.SETTINGS_FIELDS)+4
        frame=ttk.LabelFrame(body,text='Signing image (private local asset)',padding=12);frame.grid(row=row,column=0,columnspan=3,sticky='ew',pady=14)
        self.signature_enabled=tk.BooleanVar(value=False);self.signature_status=tk.StringVar(value='No signature image selected')
        ttk.Button(frame,text='Choose JPEG / PNG signature',command=self.choose_signature).pack(side='left',padx=5)
        ttk.Checkbutton(frame,text='Include in reports',variable=self.signature_enabled).pack(side='left',padx=10)
        ttk.Label(frame,textvariable=self.signature_status,style='Hint.TLabel').pack(side='left',padx=10)
        pad=ttk.LabelFrame(body,text='Custom letterpad',padding=12);pad.grid(row=row+2,column=0,columnspan=3,sticky='ew',pady=12)
        self.letterpad_mode=tk.StringVar(value='Header image');self.letterpad_enabled=tk.BooleanVar(value=False);self.letterpad_status=tk.StringVar(value='No custom letterpad selected')
        ttk.Combobox(pad,textvariable=self.letterpad_mode,state='readonly',values=['Header image','Whole-page letterpad'],width=24).pack(side='left',padx=5)
        ttk.Button(pad,text='Choose image / one-page PDF',command=self.choose_letterpad).pack(side='left',padx=5)
        ttk.Checkbutton(pad,text='Include letterpad',variable=self.letterpad_enabled,command=self.invalidate_preview).pack(side='left',padx=5)
        ttk.Label(body,textvariable=self.letterpad_status,style='Hint.TLabel',wraplength=900).grid(row=row+3,column=0,columnspan=3,sticky='w')
        ttk.Label(body,text='The image signs only the selected firm/partner block, not an architect identity. It is embedded in private case JSON for portability. Portal login and OTP are entered in the browser only.',style='Hint.TLabel',wraplength=920).grid(row=row+1,column=0,columnspan=3,sticky='w')

    def choose_letterpad(self):
        path=filedialog.askopenfilename(parent=self,title='Choose your custom letterpad',filetypes=[('Image / one-page PDF','*.png *.jpg *.jpeg *.pdf')])
        if not path:return
        try:
            from letterpad_asset import load_letterpad
            self.letterpad=load_letterpad(path,self.letterpad_mode.get());self.letterpad_enabled.set(True);self.letterpad_status.set(self.letterpad['source_name']+' | '+self.letterpad['mode']+' | Whole-page mode retains the complete background; inspect the PDF preview for clear body text.');self.invalidate_preview()
        except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self)

    def choose_signature(self):
        path=filedialog.askopenfilename(parent=self,title='Choose your authorized signing image',filetypes=[('JPEG or PNG','*.jpg *.jpeg *.png')])
        if not path:return
        try:
            from signature_asset import select_image
            self.signature_image=select_image(path);self.signature_enabled.set(True);self._signature_label();self.invalidate_preview()
        except Exception as e:messagebox.showerror(TITLE,str(e),parent=self)

    def _signature_label(self):self.signature_status.set(self.signature_image.get('name','Selected image') if self.signature_image else 'No signature image selected')

    def get_ca_dict(self):
        d={k:v.get().strip() for k,v in self.sv.items()};d['letterhead_first_page']=self.lh_first.get();d['signature_enabled']=self.signature_enabled.get();d['signature_image']=copy.deepcopy(self.signature_image);d['letterpad']=copy.deepcopy(self.letterpad or {})
        d['letterpad'].update(enabled=self.letterpad_enabled.get(),include_first_page=self.lh_first.get())
        if not self.letterpad and self.sv.get('logo_path') and self.sv['logo_path'].get().strip():
            from signature_asset import select_image
            path=self.sv['logo_path'].get().strip()
            if Path(path).exists():d['logo_image']=select_image(path)
            elif self.case.settings.get('logo_image') or getattr(self,'_profile_logo_image',None):d['logo_image']=copy.deepcopy(self.case.settings.get('logo_image') or self._profile_logo_image)
        return strip_secrets(d)

    def load_profile(self):
        engine.App.load_profile(self)
        profile=self.ca_profiles.get(self.profile_cb.get(),{});self._profile_logo_image=copy.deepcopy(profile.get('logo_image'))
        self.signature_image=copy.deepcopy(profile.get('signature_image'));self.signature_enabled.set(profile.get('signature_enabled',False));self._signature_label()
        self.lh_first.set(profile.get('letterhead_first_page',True));self.letterpad=copy.deepcopy(profile.get('letterpad'));self.letterpad_enabled.set(bool(self.letterpad and self.letterpad.get('enabled')));self.letterpad_mode.set((self.letterpad or {}).get('mode','Header image'));self.letterpad_status.set((self.letterpad or {}).get('source_name','No custom letterpad selected'))

    def clear_ca_form(self):
        for var in self.sv.values():var.set('')
        self.signature_image=None;self._profile_logo_image=None;self.signature_enabled.set(False);self._signature_label();self.letterpad=None;self.letterpad_enabled.set(False);self.letterpad_mode.set('Header image');self.letterpad_status.set('No custom letterpad selected');self.profile_cb.set('')

    def save_new_profile(self):
        try:
            data=self.get_ca_dict();name=data.get('firm_name','')
            if not name:messagebox.showwarning(TITLE,'Enter the firm name.',parent=self);return
            if name in self.ca_profiles and not messagebox.askyesno(TITLE,'Replace saved CA profile '+name+'? Existing case snapshots are not changed.',parent=self):return
            updated=copy.deepcopy(self.ca_profiles);updated[name]=data
            __import__('file_ops').atomic_json(engine.PROFILES_FILE,strip_secrets(updated));self.ca_profiles=updated
            self.update_profile_dropdown();self.profile_cb.set(name);self.status.set('CA profile saved; portal credentials/OTP excluded.')
        except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self)

    def update_current_profile(self):self.save_new_profile()

    def remove_ca_profile(self):
        name=self.profile_cb.get()
        if not name or name not in self.ca_profiles:messagebox.showinfo(TITLE,'Select a saved CA profile to remove.',parent=self);return
        if not messagebox.askyesno(TITLE,'Remove saved CA profile '+name+'?\nThe current firm/report/signature snapshot and existing cases remain unchanged. No source/signature files are deleted and no other CA is selected automatically.',parent=self):return
        try:
            updated=copy.deepcopy(self.ca_profiles);updated.pop(name)
            __import__('file_ops').atomic_json(engine.PROFILES_FILE,strip_secrets(updated));self.ca_profiles=updated;self.update_profile_dropdown();self.profile_cb.set('')
            self.status.set('Saved CA removed: '+name+'. Current report/signature identity kept; no image/source files deleted.')
        except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self)

    def trigger_udin_generation(self):
        try:
            self._sync_case()
            from udin_assist import payload_from_case,create_driver,UdinSession,SELECTOR_STATUS
            data,missing=payload_from_case(self.case)
            if missing:messagebox.showwarning(TITLE,'Complete the highlighted readiness fields before assisted filling:\n- '+'\n- '.join(missing),parent=self);self.udin_status.set('Missing: '+', '.join(missing));return
            username=simpledialog.askstring(TITLE,'ICAI MRN / username (used only for this browser session):',parent=self)
            if not username:return
            password=simpledialog.askstring(TITLE,'ICAI portal password (not saved or logged):',show='*',parent=self)
            if password is None:return
            text='UDIN mapping review ('+SELECTOR_STATUS+'):\nFRN: '+data['frn']+'\nApplicant(s): '+data['name']+'\nSigning date: '+data['cert_date']+'\nImmovable INR '+data['imm_total']+' | Movable INR '+data['mov_total']+'\n\nChrome will open. Enter login/CAPTCHA yourself. The assistant fills visible report fields after login. Review them; Request OTP is a separate explicit button. OTP entry and final generation stay entirely with you. Continue?'
            if not messagebox.askyesno(TITLE,text,parent=self):return
            if getattr(self,'_udin_busy',False):messagebox.showinfo(TITLE,'A portal action is already running.',parent=self);return
            self._udin_busy=True;generation=self._generation;self.udin_status.set('Opening Chrome; sign in directly there. No credentials or OTP are saved.')
            def work():
                try:
                    session=UdinSession(create_driver());self._udin_session=session;self._udin_payload=copy.deepcopy(data)
                    missing=session.open_and_fill(data,{'username':username,'password':password})
                    self.jobs.put(('udin',generation,'Form mapping incomplete: '+', '.join(missing) if missing else 'Fields filled for review. Request OTP only after checking the browser form.',missing))
                except Exception as exc:self.jobs.put(('udin',generation,'Assistant stopped. Browser may remain open for manual completion.',[type(exc).__name__+': '+str(exc).split('Stacktrace:',1)[0]]))
                finally:self._udin_busy=False
            threading.Thread(target=work,daemon=True).start()
        except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self)

    def udin_action(self,action):
        if action=='otp':
            try:
                self._sync_case()
                from udin_assist import payload_from_case
                current,missing=payload_from_case(self.case)
                if missing or current!=getattr(self,'_udin_payload',None):messagebox.showwarning(TITLE,'Report/firm figures changed since portal preparation. Restart the assistant or finish manually in the browser; no OTP was requested.',parent=self);return
            except Exception as exc:messagebox.showerror(TITLE,str(exc),parent=self);return
        session=getattr(self,'_udin_session',None)
        if not session:messagebox.showinfo(TITLE,'Open the UDIN assistant first.',parent=self);return
        if getattr(self,'_udin_busy',False):messagebox.showinfo(TITLE,'Wait for the current portal action.',parent=self);return
        if action=='otp' and not messagebox.askyesno(TITLE,'I reviewed the filled portal fields. Request one OTP now? You will enter it and generate the final UDIN in Chrome yourself.',parent=self):return
        self._udin_busy=True;generation=self._generation
        def work():
            try:
                if action=='otp':result=session.request_otp()
                else:result='Generated UDIN: '+session.read_generated_udin()
                self.jobs.put(('udin',generation,result,[]))
            except Exception as exc:self.jobs.put(('udin',generation,'Portal action needs attention.',[type(exc).__name__+': '+str(exc).split('Stacktrace:',1)[0]]))
            finally:self._udin_busy=False
        threading.Thread(target=work,daemon=True).start()

    def _close(self):
        if self._busy and not messagebox.askyesno(TITLE,'A background task is running. Close anyway?',parent=self):return
        if App._confirm_discard(self,'Close'):
            if getattr(self,'_preview_temp',None):self._preview_temp.cleanup()
            self.destroy()

if __name__=='__main__':
    App().mainloop()
