import streamlit as st
try:
 import streamlit_antd_components as sac
except ImportError:
 sac = None
from html import escape as html_escape
import pandas as pd
import re
import io
import zipfile
from io import BytesIO
from pathlib import Path
from core import *
from phase1_features import dashboard as phase1_dashboard, search_papers as phase1_search, export_panel as phase1_export, engagement_detail as phase1_detail
init();st.set_page_config(page_title='AuditFile CA | Engagement Workspace',layout='wide')

# Visual-only theme: no changes to permissions, database or workflow.
st.markdown("""
<style>
:root { --audit-navy:#14253e; --audit-blue:#2557a7; --audit-muted:#63748b; }
.stApp { background: #f5f7fb; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#14253e 0%,#1c3657 100%); }
[data-testid="stSidebar"] * { color:#f1f5fc !important; }
[data-testid="stSidebar"] [role="radiogroup"] label {
  border-radius: 9px; padding: 0.35rem 0.55rem; margin-bottom: 0.18rem;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:rgba(255,255,255,.11); }
[data-testid="stSidebar"] button { border:1px solid rgba(255,255,255,.28); background:rgba(255,255,255,.09); }
.block-container { max-width: 1450px; padding-top: 1.7rem; padding-bottom: 3rem; }
h1, h2, h3 { color:var(--audit-navy); letter-spacing:-.025em; }
h1 { font-weight: 750; font-size: 2.05rem; margin-bottom:.15rem; }
h2 { font-size:1.48rem; }
h3 { font-size:1.22rem; }
[data-testid="stCaptionContainer"] { color:var(--audit-muted); }
[data-testid="stMetric"] {
  background:white; border:1px solid #e3e9f2; border-radius:14px;
  padding:1rem 1.1rem; box-shadow:0 3px 12px rgba(18,38,68,.035);
}
[data-testid="stMetricLabel"] { color:#60738d; }
[data-testid="stMetricValue"] { color:#183b66; }
[data-testid="stForm"], [data-testid="stExpander"] {
  background:white; border:1px solid #e0e7f0; border-radius:13px;
  box-shadow:0 2px 10px rgba(18,38,68,.025);
}
[data-testid="stDataFrame"] { border:1px solid #e2e8f1; border-radius:10px; overflow:hidden; }
div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {
  background:#2557a7; border-color:#2557a7;
}
div.stButton > button, div.stFormSubmitButton > button, div.stDownloadButton > button {
  border-radius:9px; font-weight:600;
}
div[data-testid="stAlert"] { border-radius:10px; }
[data-testid="stSelectbox"] label, [data-testid="stTextInput"] label { font-weight:550; }
@media (max-width: 768px) { .block-container { padding:1.2rem .8rem 2rem; } }
</style>
""", unsafe_allow_html=True)

# Stage 1 enterprise styling: presentation-only, intentionally avoids explorer-specific selectors.
st.markdown("""<style>
:root { --af-ink:#172b49; --af-blue:#2563eb; --af-border:#e4eaf3; }
.stApp { background:linear-gradient(180deg,#f8faff 0%,#f5f7fb 360px); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#11243e 0%,#172f50 100%); border-right:1px solid #233d60; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top:1.15rem; }
[data-testid="stSidebar"] [role="radiogroup"] { gap:0.2rem; }
[data-testid="stSidebar"] [role="radiogroup"] label { padding:.52rem .7rem; border:1px solid transparent; transition:background .15s ease; }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background:rgba(92,156,255,.21); border-color:rgba(145,189,255,.27); box-shadow:inset 3px 0 0 #7eb5ff; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:rgba(255,255,255,.10); }
[data-testid="stSidebar"] button { width:100%; border-radius:9px; }
.block-container { max-width:1540px; padding-top:1.35rem; }
.block-container > div > div > div > [data-testid="stHeading"] h1 { font-size:1.8rem; font-weight:760; }
[data-testid="stMetric"] { border:1px solid var(--af-border); border-top:3px solid #dbe8ff; border-radius:12px; padding:.95rem 1.1rem; box-shadow:0 4px 15px rgba(20,43,75,.04); }
[data-testid="stMetricValue"] { font-weight:750; letter-spacing:-.045em; }
[data-testid="stMetricLabel"] { font-size:.87rem; }
[data-testid="stDataFrame"] { background:#fff; border:1px solid var(--af-border); box-shadow:0 2px 8px rgba(20,43,75,.025); }
[data-testid="stExpander"] { border-radius:11px; }
[data-testid="stExpander"] summary { font-weight:600; }
[data-testid="stSelectbox"] [data-baseweb="select"] > div { border-color:#dce5f1; }
[data-testid="stTextInput"] input { border-color:#dce5f1; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { border-bottom:1px solid #e2e9f3; }
[data-testid="stDownloadButton"] button { border:1px solid #bfd1ea; }
hr { border-color:#e7edf6; }
@media(max-width:950px) { .block-container { padding-top:1rem; } }
</style>""", unsafe_allow_html=True)

# Stage 2B: compact global headings, navigational spacing and inline WP details.
st.markdown("""<style>
.audit-app-heading{font-size:1.25rem;font-weight:750;color:#172b49;line-height:1.3;margin:0 0 .75rem}
.audit-app-heading span{font-size:.65rem;font-weight:650;letter-spacing:.08em;color:#8292a8;margin-left:12px;vertical-align:middle}
.block-container{padding-top:.9rem!important}
.block-container h2{font-size:1.37rem;margin-top:.6rem;margin-bottom:.5rem}
.block-container h3{font-size:1.14rem;margin-top:.45rem;margin-bottom:.4rem}
.st-key-audit_wp_panel [data-testid="stVerticalBlock"]{gap:.3rem}
.st-key-audit_wp_panel .stButton>button{width:100%;text-align:left;justify-content:flex-start;border-radius:7px;min-height:34px;padding:.25rem .55rem;font-size:.84rem}
.st-key-audit_wp_panel .stDownloadButton>button{font-size:.79rem;min-height:32px}
/* Keep WP index and title at the left of the full-width button. */
.st-key-audit_wp_panel [data-testid="stButton"] > button {
  justify-content:flex-start!important;
  text-align:left!important;
}
.st-key-audit_wp_panel [data-testid="stButton"] > button [data-testid="stMarkdownContainer"] {
  flex:1 1 auto!important;
  width:100%!important;
  text-align:left!important;
}
.st-key-audit_wp_panel [data-testid="stButton"] > button p {
  text-align:left!important;
  width:100%!important;
  margin:0!important;
}
/* Compact sidebar radio indicators; do not change the text or menu icons. */
[data-testid="stSidebar"] [role="radiogroup"] label [data-baseweb="radio"] > div:first-child,
[data-testid="stSidebar"] [role="radiogroup"] label [data-baseweb="radio"] > div:first-child > div {
  width:13px!important;
  height:13px!important;
  min-width:13px!important;
  min-height:13px!important;
  flex:0 0 13px!important;
}
[data-testid="stSidebar"] [role="radiogroup"] label [data-baseweb="radio"] > div:first-child > div > div {
  width:5px!important;height:5px!important;
}

.audit-wp-status{display:inline-block;border-radius:5px;padding:2px 7px;font-size:11px;font-weight:750;white-space:nowrap}
.audit-wp-status.closed{color:#11633a;background:#e6f6ed}
.audit-wp-status.pending{color:#9a5300;background:#fff0d5}
.audit-wp-status.open{color:#b4232e;background:#fff0f0}
.audit-wp-status.other{color:#4c5e77;background:#edf2f7}
.audit-wp-info{font-size:.78rem;color:#52647e;padding:4px 2px 7px}
.audit-wp-detail-title{font-size:.83rem;font-weight:700;color:#173a63;margin-top:6px}
</style>""",unsafe_allow_html=True)

# Login and form visual refinements (presentation only).
st.markdown("""<style>
html, body, [class*="css"] { font-family: 'Segoe UI', 'Inter', Arial, sans-serif; }
[data-testid="stTextInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stTextArea"] textarea { border-radius:9px; min-height:42px; background:#fff; }
[data-testid="stTextInput"] input:focus { border-color:#2675d1; box-shadow:0 0 0 2px rgba(38,117,209,.12); }
[data-testid="stForm"] { padding:1.1rem 1.25rem; }
[data-testid="stFormSubmitButton"] button { min-height:43px; }
.audit-login-welcome { background:linear-gradient(145deg,#087cda,#07519b 74%,#063d80); color:#fff;
 padding:3rem 2.4rem; border-radius:20px; min-height:360px; box-shadow:0 14px 30px rgba(11,49,99,.15); }
.audit-login-welcome .eyebrow { font-size:.74rem; letter-spacing:.18em; font-weight:700; opacity:.85; }
.audit-login-welcome h2 { color:#fff; font-size:2.35rem; line-height:1.1; margin:1.5rem 0 1rem; }
.audit-login-welcome p { color:#e3f2ff; line-height:1.75; font-size:.96rem; }
.audit-login-logo { font-size:1.35rem; font-weight:800; letter-spacing:-.02em; }
.audit-login-heading { padding:.3rem 0 .9rem; }
.audit-login-heading h2 { margin:0 0 .4rem; font-size:1.9rem; }
.audit-login-heading p { color:#718096; margin:0; }
@media(max-width:800px){ .audit-login-welcome {min-height:220px;padding:1.5rem;} }
</style>""", unsafe_allow_html=True)

def act(fn, success_message):
 try:
  fn()
  s.flush()
  s.commit()
  st.session_state['last_success']=success_message
  s.close()
  st.rerun()
 except Exception as ex:
  s.rollback()
  st.error(f'Operation NOT completed: {type(ex).__name__}: {ex}')
message=st.session_state.pop('last_success',None)
if message: st.success(message)
s=Session()
if not s.query(User).count():
 st.header('First-run administrator setup')
 with st.form('first'):
  name=st.text_input('Administrator name');username=st.text_input('Username');password=st.text_input('Password (12+ characters)',type='password');ok=st.form_submit_button('Create administrator')
  if ok:
   if len(password)<12 or not name.strip() or not username.strip():st.error('Enter a name, username and password of at least 12 characters')
   else:act(lambda:s.add(User(name=name,username=username,initials='ADM',password=ph.hash(password),admin=1)),'Administrator account created successfully.')
 s.close();st.stop()
if 'uid' not in st.session_state:
 st.markdown('<div style="height:35px"></div>',unsafe_allow_html=True)
 outer_left,center,outer_right=st.columns([1,5,1])
 with center:
  welcome,signin=st.columns([1.12,1],gap='large',vertical_alignment='center')
  with welcome:
   st.markdown('''<div class="audit-login-welcome"><div class="audit-login-logo">▣ &nbsp; AuditFile CA</div><div class="eyebrow" style="margin-top:3rem">WELCOME TO YOUR WORKSPACE</div><h2>Audit files,<br>organised.</h2><p>Secure documentation, structured review and traceable engagement management—all in one place.</p></div>''',unsafe_allow_html=True)
  with signin:
   st.markdown('''<div class="audit-login-heading"><h2>Sign in</h2><p>Enter your credentials to continue.</p></div>''',unsafe_allow_html=True)
   with st.form('login'):
    username=st.text_input('Username',placeholder='Enter your user ID');password=st.text_input('Password',type='password',placeholder='Enter your password');go=st.form_submit_button('Sign in',use_container_width=True,type='primary')
    if go:
     u=s.query(User).filter_by(username=username,active=1).first()
     try:
      if not u:raise ValueError('Invalid credentials')
      ph.verify(u.password,password);st.session_state.uid=u.id;log(s,u.id,'Login','Success');s.commit();s.close();st.rerun()
     except Exception:st.error('Invalid credentials')
 st.markdown('<div style="text-align:center;color:#8291a4;font-size:.78rem;margin-top:2.5rem">AuditFile CA · Internal firm access only</div>',unsafe_allow_html=True)
 s.close();st.stop()
st.markdown('<div class="audit-app-heading">AuditFile CA <span>ENGAGEMENT WORKSPACE</span></div>',unsafe_allow_html=True)
u=s.get(User,st.session_state.uid)
if not u or not u.active:del st.session_state.uid;s.close();st.rerun()
st.sidebar.markdown("""<div style="padding:.1rem .15rem .85rem;border-bottom:1px solid rgba(255,255,255,.15);margin-bottom:.9rem"><div style="font-size:1.25rem;font-weight:800;letter-spacing:-.025em;color:#fff">▣ &nbsp; AuditFile CA</div><div style="font-size:.72rem;letter-spacing:.09em;color:#b9cbe5;margin-top:.2rem">ENGAGEMENT WORKSPACE</div></div>""",unsafe_allow_html=True)
st.sidebar.write(f'**{u.name}** — {"Administrator" if u.admin else "Employee"}')
if st.sidebar.button('Logout'):del st.session_state.uid;s.close();st.rerun()
choices=['Dashboard','Working Papers','Reports']+(['Review Queue','Review Notes'] if not u.admin else [])+(['Clients','Administration'] if u.admin else [])+(['Engagements'] if u.admin or u.designation in PARTNER_DESIGNATIONS else [])+(['Audit Trail'] if u.admin or u.designation in PARTNER_DESIGNATIONS else [])
if st.session_state.pop('phase1_nav_to_wp',False):st.session_state['main_navigation']='Working Papers'
nav_icons={'Dashboard':'📊','Working Papers':'📁','Reports':'📑','Review Queue':'📋','Review Notes':'💬','Clients':'🏢','Administration':'⚙️','Engagements':'🗂️','Audit Trail':'🕒'}
page=st.sidebar.radio('Navigation',choices,key='main_navigation',format_func=lambda choice:f'{nav_icons.get(choice,"•")}  {choice}')
engs=s.query(Engagement).all() if u.admin else s.query(Engagement).join(Assignment).filter(Assignment.user_id==u.id).all()
def choose_eng():
 if not engs:st.info('No assigned engagements');s.close();st.stop()
 return st.selectbox('Engagement',engs,index=next((i for i,e in enumerate(engs) if e.id==st.session_state.get('phase1_jump_engagement')),0),format_func=lambda e:f'{e.id} — {s.get(Client,e.client_id).name} — {e.kind} — {e.fy}',key='active_engagement_select')
def table(rows):st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
if page=='Clients':
 st.header('Client master')
 with st.form('client'):
  name=st.text_input('Client name');grp=st.text_input('Group');pan=st.text_input('PAN');gst=st.text_input('GSTIN');email=st.text_input('Email');mobile=st.text_input('Mobile');go=st.form_submit_button('Create')
  if go:
   if not name.strip() or (pan and not re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]',pan.upper())) or (gst and not re.fullmatch(r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]',gst.upper())) or (email and not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email)):st.error('Check name, PAN, GSTIN and email')
   else:act(lambda:(s.add(Client(name=name,grp=grp,pan=pan.upper(),gstin=gst.upper(),email=email,mobile=mobile)),log(s,u.id,'Create client',name)),f'Client {name} created successfully.')
 table([dict(ID=x.id,Name=x.name,PAN=x.pan,GSTIN=x.gstin,Email=x.email) for x in s.query(Client).all()])
elif page=='Administration':
 st.header('Employees')
 with st.form('employee'):
  name=st.text_input('Name');initials=st.text_input('Initials');username=st.text_input('Username');password=st.text_input('Temporary password',type='password');designation=st.selectbox('Designation',['Senior Partner','Junior Partner','Manager','Articled/Audit Assistant','Staff']);go=st.form_submit_button('Create employee')
  if go:
   if not name or not 2<=len(initials)<=3 or len(password)<12:st.error('Name, 2–3 initials and 12-character password required')
   else:act(lambda:(s.add(User(name=name,initials=initials.upper(),username=username,password=ph.hash(password),designation=designation)),log(s,u.id,'Create employee',username)),f'Employee {name} created successfully.')
 users=s.query(User).all();table([dict(ID=x.id,Name=x.name,Username=x.username,Designation=x.designation,Active=bool(x.active)) for x in users])
 with st.form('active'):
  target=st.selectbox('Change account status',[x for x in users if x.id!=u.id],format_func=lambda x:x.name);active=st.checkbox('Active',value=bool(target.active));go=st.form_submit_button('Update')
  if go:act(lambda:setattr(target,'active',int(active)),f'Account for {target.name} {"activated" if active else "deactivated"} successfully.')
 with st.form('designation_change'):
  selected=st.selectbox('Employee designation', [x for x in users if not x.admin],format_func=lambda x:f'{x.name} ({x.designation})')
  new_designation=st.selectbox('New designation',['Senior Partner','Junior Partner','Manager','Articled/Audit Assistant','Staff']);update_designation=st.form_submit_button('Update designation')
  if update_designation:
   def save_designation():
    from sqlalchemy import update, select
    employee_id = selected.id
    if selected.admin:
     raise PermissionError('Administrator designation cannot be changed here')
    result = s.execute(update(User).where(User.id == employee_id, User.admin == 0).values(designation=new_designation))
    if result.rowcount != 1:
     raise ValueError('Employee designation update did not affect exactly one account')
    s.flush()
    actual = s.execute(select(User.designation).where(User.id == employee_id)).scalar_one()
    if actual != new_designation:
     raise RuntimeError('Designation verification failed before commit')
    log(s,u.id,'Change designation',f'{employee_id}: {new_designation}')
   act(save_designation, f'Designation updated to {new_designation}.')
elif page=='Engagements':
 st.header('Engagement master')
 if u.admin:
  with st.form('eng'):
   clients=s.query(Client).all();client=st.selectbox('Client',clients,format_func=lambda c:c.name) if clients else None
   kind=st.selectbox('Type',['Statutory Audit (Company)','Statutory Audit (LLP)','Statutory Audit (Non-Corporate)','Tax Audit','Statutory Audit + Tax Audit','ITR Filing','TDS Return Filing','Incorporation Services','Litigation','Advisory/Consultancy','Bookkeeping','GST Annual Return Filing','Certification','Other']);fy=st.text_input('Financial year','2025-26');levels=st.number_input('Review levels',1,5,2);start=st.date_input('Start date');end=st.date_input('End date')
   partners=[x for x in s.query(User).all() if x.active and not x.admin and x.designation in PARTNER_DESIGNATIONS]
   partner=st.selectbox('Assigned engagement partner (mandatory)',partners,format_func=lambda x:f'{x.name} ({x.designation})') if partners else None
   st.caption('The selected partner is assigned as reviewer at the final review level and may finalise the engagement after all working papers are closed.')
   if not partners:st.warning('Create or activate a Senior Partner or Junior Partner account before creating an engagement.')
   go=st.form_submit_button('Create engagement',disabled=not clients or not partners)
   if go:
    if not client or not partner:st.error('A client and an active partner are required.')
    else:act(lambda:create_engagement_with_partner(s,u.id,client.id,kind,fy,levels,start,end,partner.id),f'Engagement {kind} — {fy} created with assigned partner {partner.name}.')
 if engs:
  e=choose_eng();st.caption(f'Engagement status: {e.status}')
  if e.status=='Open' and can_manage_engagement(s,u.id,e.id):
   with st.form('assign'):
    employees=[x for x in s.query(User).all() if x.active and not x.admin and not s.query(Assignment).filter_by(engagement_id=e.id,user_id=x.id).first()]
    employee=st.selectbox('Employee',employees,format_func=lambda x:f'{x.name} ({x.designation})') if employees else None
    role=st.selectbox('Role',['Preparer','Reviewer']);level=st.number_input('Reviewer level',1,e.levels,1);go=st.form_submit_button('Assign',disabled=employee is None)
    if go and employee:act(lambda:assign_employee(s,u.id,e.id,employee.id,role,level),'Employee assigned to engagement.')
  table([dict(Employee=s.get(User,a.user_id).name,Role=a.role,Level=a.level) for a in s.query(Assignment).filter_by(engagement_id=e.id)])
  if e.status=='Open' and can_manage_engagement(s,u.id,e.id):
   st.warning('Finalisation locks this engagement against further changes. All working papers must be closed.')
   with st.form('finalise_confirm'):
    confirmed=st.checkbox('I confirm that this engagement is ready to be finalised')
    go=st.form_submit_button('Finalise engagement (all WPs must be closed)')
    if go:
     if not confirmed:st.error('Please confirm finalisation first.')
     else:act(lambda:finalise_engagement(s,u.id,e.id),'Engagement finalised and verified.')
elif page=='Dashboard':
 phase1_dashboard(s,engs,u)
elif page=='Working Papers':
 e=choose_eng();folders=s.query(Folder).filter_by(engagement_id=e.id).order_by(Folder.idx).all();wps=s.query(WP).filter_by(engagement_id=e.id).order_by(WP.idx).all()
 # Read-only attribution: preparer from WP; reviewers from actual approval signoffs.
 # Assigned reviewers are shown separately and are never represented as approvals.
 wp_user_ids={w.preparer_id for w in wps}
 approvals=s.query(Signoff).filter(Signoff.wp_id.in_([w.id for w in wps]),Signoff.action=='Approve').order_by(Signoff.id).all() if wps else []
 wp_user_ids.update(a.user_id for a in approvals)
 reviewer_assignments=s.query(Assignment).filter_by(engagement_id=e.id,role='Reviewer').all()
 wp_user_ids.update(a.user_id for a in reviewer_assignments)
 wp_users={person.id:person for person in s.query(User).filter(User.id.in_(wp_user_ids)).all()} if wp_user_ids else {}
 def initials(uid):
  person=wp_users.get(uid)
  return person.initials if person and person.initials else '—'
 approvals_by_wp={}
 for approval in approvals:
  approvals_by_wp.setdefault(approval.wp_id,[]).append(approval)
 def reviewed_by(w):
  # A review on an older version is not a signoff on the current version.
  signed={}
  for approval in approvals_by_wp.get(w.id,[]):
   if approval.version==w.version:signed[approval.level]=initials(approval.user_id)
  return ', '.join(f'{name} (L{level})' for level,name in sorted(signed.items())) or '—'
 def assigned_reviewers(w):
  return ', '.join(f'{initials(a.user_id)} (L{a.level})' for a in sorted(reviewer_assignments,key=lambda x:x.level)) or '—'
 with st.expander('🔎 Search and filter working papers',expanded=False):
  phase1_search(s,e)
 st.subheader('Working Paper Explorer')
 st.caption('Browse indexed folders on the left and select a working paper on the right. Existing upload and review controls remain unchanged.')
 folder_by_id={f.id:f for f in folders}
 children={}
 for f in folders:
  parent=f.parent_id if f.parent_id in folder_by_id and f.parent_id!=f.id else None
  children.setdefault(parent,[]).append(f)
 for siblings in children.values():siblings.sort(key=lambda f:f.idx)
 key_prefix=f'explorer_{u.id}_{e.id}'
 selection_key=f'{key_prefix}_folder'
 expanded_key=f'{key_prefix}_expanded'
 if expanded_key not in st.session_state:st.session_state[expanded_key]=set()
 if selection_key not in st.session_state:st.session_state[selection_key]=None
 selected_folder=folder_by_id.get(st.session_state[selection_key])
 visible_wps=[w for w in wps if selected_folder is None or w.folder_id==selected_folder.id]
 st.markdown("""<style>
 /* Stage 2: independently scrollable fixed-height explorer panels. */
 .st-key-audit_wp_panel [data-testid="stVerticalBlockBorderWrapper"] {
   max-height:clamp(280px,45vh,450px);
 }
 .audit-wp-mini {box-sizing:border-box;width:100%;min-width:0; background:white;
   border:1px solid #dce5f0;border-radius:8px;padding:8px;}
 .audit-wp-mini-title {font-size:13px;font-weight:700;color:#193c65;}
 .audit-wp-mini-title span {float:right;color:#6a7b92;font-weight:500;}
 .audit-wp-mini-scroll {overflow-x:auto;overflow-y:auto;max-height:calc(45vh - 95px);scrollbar-width:thin;margin-top:8px;}
 .audit-wp-mini table {border-collapse:collapse;min-width:100%;width:max-content;font-size:12px;}
 .audit-wp-mini th {position:sticky;top:0;background:#eef3f9;z-index:1;text-align:left;color:#4a5e77;}
 .audit-wp-mini td,.audit-wp-mini th {padding:7px 9px;border-bottom:1px solid #e7edf5;white-space:nowrap;}
 .audit-wp-mini td:nth-child(2) {min-width:165px;}
 </style>""",unsafe_allow_html=True)
 def paper_summary(items,title):
  rows=''.join(
   '<tr><td>'+html_escape(str(w.idx))+'</td><td>'+html_escape(str(w.title))+
   '</td><td>'+html_escape(str(w.status))+'</td><td>'+str(w.version)+
   '</td><td>'+str(w.level)+'</td><td>'+html_escape(initials(w.preparer_id))+
   '</td><td>'+html_escape(reviewed_by(w))+
   '</td><td>'+html_escape(assigned_reviewers(w))+'</td></tr>' for w in items
  )
  if not rows:
   rows='<tr><td colspan="8" style="color:#77869c">No working papers directly in this folder</td></tr>'
  st.markdown(
   '<div class="audit-wp-mini"><div class="audit-wp-mini-title">'+html_escape(str(title))+
   ' <span>'+str(len(items))+' WP(s)</span></div>'+
   '<div class="audit-wp-mini-scroll"><table><thead><tr>'+
   '<th>Index</th><th>Working paper</th><th>Status</th><th>V</th><th>Level</th>'+
   '<th>Prepared by</th><th>Reviewed by</th><th>Assigned reviewers</th>'+
   '</tr></thead><tbody>'+rows+'</tbody></table></div></div>',unsafe_allow_html=True)
 reachable=set()
 def mark_reachable(node):
  if node.id in reachable:return
  reachable.add(node.id)
  for child in children.get(node.id,[]):mark_reachable(child)
 for root in children.get(None,[]):mark_reachable(root)
 left_col,right_col=st.columns([35,65],gap='medium',vertical_alignment='top')
 with left_col:
  st.markdown('**Folder hierarchy**')
  with st.container(height=400,border=True,key='audit_folder_tree'):
   if sac is None:
    st.error('The folder-tree component is not installed. Run: py -m pip install streamlit-antd-components')
    st.stop()
   # Native Ant Design tree handles indentation and arrows internally.
   # The labels are unique within this engagement, and contain no database IDs.
   labels={}
   visited=set()
   def make_item(folder):
    if folder.id in visited:return None
    visited.add(folder.id)
    label=f'{folder.idx} — {folder.title}'
    if label in labels:label=f'{label} (folder {folder.id})'
    labels[label]=folder.id
    subitems=[make_item(child) for child in children.get(folder.id,[])]
    subitems=[child for child in subitems if child is not None]
    return sac.TreeItem(label=label,children=subitems)
   items=[sac.TreeItem(label='All working papers',children=[])]
   items.extend(item for root in children.get(None,[]) if (item:=make_item(root)) is not None)
   # Preserve folders whose parent records are missing.
   items.extend(item for folder in folders if folder.id not in visited if (item:=make_item(folder)) is not None)
   # The widget keeps its own expanded-node state. Do not inject CSS into rows.
   chosen=sac.tree(items=items,index=None,open_all=True,key=f'{key_prefix}_antd_tree')
   if isinstance(chosen,(list,tuple)):
    chosen=chosen[-1] if chosen else None
   if isinstance(chosen,str):
    new_selection=None if chosen=='All working papers' else labels.get(chosen)
    if new_selection!=st.session_state[selection_key]:
     st.session_state[selection_key]=new_selection
     st.rerun()
   if not folders:st.caption('No folders created for this engagement.')
 with right_col:
  st.markdown('**Working papers**')
  with st.container(height=400,border=True,key='audit_wp_panel'):
   selected_folder=folder_by_id.get(st.session_state[selection_key])
   visible_wps=[w for w in wps if selected_folder is None or w.folder_id==selected_folder.id]
   title=f'{selected_folder.idx} — {selected_folder.title}' if selected_folder else 'All working papers'
   st.markdown(f'<div class="audit-wp-detail-title">{html_escape(title)} · {len(visible_wps)} WP(s)</div>',unsafe_allow_html=True)
   active_key=f'{key_prefix}_active_wp'
   focused=st.session_state.pop(f'phase1_focus_wp_{e.id}',None)
   if focused is not None and any(w.id==focused for w in visible_wps):st.session_state[active_key]=focused
   if st.session_state.get(active_key) not in [w.id for w in visible_wps]:st.session_state[active_key]=None
   if not visible_wps:st.caption('No working papers directly in this folder.')
   for item in visible_wps:
    is_active=st.session_state.get(active_key)==item.id
    status=str(item.status).lower()
    category='closed' if status=='closed' else ('pending' if status in ('submitted','pending review','pending') else ('open' if status in ('draft','returned','reopened','open') else 'other'))
    line1,line2=st.columns([0.75,0.25],gap='small',vertical_alignment='center')
    with line1:
     if st.button(('▾  ' if is_active else '▸  ')+f'{item.idx} — {item.title}',key=f'{key_prefix}_wp_row_{item.id}',use_container_width=True,type='primary' if is_active else 'secondary'):
      st.session_state[active_key]=None if is_active else item.id
      st.rerun()
    with line2:
     st.markdown(f'<span class="audit-wp-status {category}">{html_escape(str(item.status))}</span>',unsafe_allow_html=True)
    if is_active:
     st.markdown('<div class="audit-wp-info">'+
      f'Version {item.version} · Level {item.level} · Prepared by {html_escape(initials(item.preparer_id))}'+
      '<br>Reviewed by: '+html_escape(reviewed_by(item))+
      '<br>Assigned reviewers: '+html_escape(assigned_reviewers(item))+'</div>',unsafe_allow_html=True)
     versions=s.query(Version).filter_by(wp_id=item.id).order_by(Version.number.desc()).all()
     if versions:st.markdown('<div class="audit-wp-detail-title">Download versions</div>',unsafe_allow_html=True)
     for v in versions:
      file_path=ROOT/'storage'/v.path
      if file_path.exists():st.download_button(f'⬇ Version {v.number} — {v.filename}',file_path.read_bytes(),file_name=v.filename,key=f'v{v.id}')
      else:st.caption(f'Version {v.number}: file unavailable')
     if e.status=='Open' and item.preparer_id==u.id and item.status in ('Draft','Returned','Reopened'):
      with st.form(f'revision_{item.id}'):
       upload=st.file_uploader('Upload revision',key=f'upload_revision_{item.id}')
       reason=st.text_input('Revision reason',key=f'reason_{item.id}')
       go=st.form_submit_button('Save new version')
       if go and upload:act(lambda:save(s,item,upload.name,upload.getvalue(),u.id,reason),f'New version uploaded for working paper {item.idx}.')
      if st.button('Sign off and submit',key=f'submit_{item.id}'):
       try:
        s.expire_all()
        current=s.get(WP,item.id)
        submit(s,current,u.id)
        s.flush();s.commit();s.expire_all()
        verified=s.get(WP,item.id)
        if verified.status!='Submitted':st.error(f'Submission could not be verified. Actual status: {verified.status}')
        else:
         st.session_state['last_success']=f'WP {verified.idx} submitted for review (Version {verified.version}).'
         s.close();st.rerun()
       except Exception as ex:
        s.rollback();st.error(f'Submission failed: {type(ex).__name__}: {ex}')
     st.divider()
 st.divider()
 canprep=not u.admin and bool(s.query(Assignment).filter_by(user_id=u.id,engagement_id=e.id,role='Preparer').first())
 if canprep and e.status=='Open':
  with st.expander('Create folder'):
   with st.form('folder'):
    title=st.text_input('Folder title')
    parent=st.selectbox('Parent',[None]+folders,format_func=lambda f:f'{f.idx} {f.title}' if f else 'Root')
    st.caption('Index number is generated automatically from the selected parent.')
    if st.form_submit_button('Create folder'):
     if not title.strip():st.error('Enter a folder title.')
     else:act(lambda:create_indexed_folder(s,u.id,e.id,title,parent.id if parent else None),'Folder created with automatic index.')
  with st.expander('Manage existing folders — rename, move or delete'):
   st.caption('Rename corrects the folder title. Move changes its parent without altering its index number or working papers. Deletion is permitted only for an empty folder with no subfolders.')
   if folders:
    target=st.selectbox('Folder to manage',folders,format_func=lambda f:f'{f.idx} — {f.title}',key='manage_folder_target')
    action=st.radio('Action',['Rename','Move','Delete empty folder'],horizontal=True,key='manage_folder_action')
    if action=='Rename':
     with st.form('rename_existing_folder'):
      new_title=st.text_input('Corrected folder name',value=target.title)
      if st.form_submit_button('Save folder name'):
       act(lambda:manage_folder(s,u.id,e.id,target.id,'rename',title=new_title),'Folder renamed successfully. Refresh to see the updated tree.')
    elif action=='Move':
     destinations=[None]+[f for f in folders if f.id!=target.id]
     with st.form('move_existing_folder'):
      dest=st.selectbox('New parent folder',destinations,format_func=lambda f:f'{f.idx} — {f.title}' if f else 'Root (top level)')
      st.caption('A folder cannot be moved into itself or its descendants. The folder index is retained.')
      if st.form_submit_button('Move folder'):
       act(lambda:manage_folder(s,u.id,e.id,target.id,'move',parent_id=dest.id if dest else None),'Folder moved successfully. Refresh to see the updated tree.')
    else:
     with st.form('delete_existing_folder'):
      st.warning('Only folders containing no working papers and no subfolders can be deleted.')
      confirmed=st.checkbox(f'Confirm deletion of {target.idx} — {target.title}')
      if st.form_submit_button('Delete empty folder'):
       if not confirmed:st.error('Confirm deletion before proceeding.')
       else:act(lambda:manage_folder(s,u.id,e.id,target.id,'delete'),'Empty folder deleted successfully. Refresh to see the updated tree.')
   else:st.info('There are no folders to manage.')
  with st.expander('New working paper'):
   with st.form('wp'):
    folder=st.selectbox('Folder',folders,format_func=lambda f:f'{f.idx} {f.title}') if folders else None
    title=st.text_input('Title (optional; defaults to filename)')
    upload=st.file_uploader('File',type=['xls','xlsx','doc','docx','pdf','jpg','jpeg','png','ppt','pptx'])
    st.caption('The next index under the selected folder will be assigned automatically.')
    if st.form_submit_button('Create and upload'):
     if not folder or not upload:st.error('Choose a folder and a file.')
     else:act(lambda:create_indexed_wp(s,u.id,e.id,folder.id,upload.name,upload.getvalue(),title),'Working paper created and indexed.')
  with st.expander('Bulk upload working papers'):
   if folders:
    bulk_folder=st.selectbox('Destination folder',folders,format_func=lambda f:f'{f.idx} — {f.title}',key='bulk_destination')
    bulk_files=st.file_uploader('Select multiple files',type=['xls','xlsx','doc','docx','pdf','jpg','jpeg','png','ppt','pptx'],accept_multiple_files=True,key='bulk_files')
    if bulk_files:
     preview=[];reserved=[]
     for file in bulk_files:
      idx=next_audit_index(s,e.id,bulk_folder.id,reserved)
      reserved.append(idx);preview.append({'Index':idx,'Working paper':Path(file.name).stem,'Filename':file.name})
     st.dataframe(preview,use_container_width=True,hide_index=True)
     if st.button(f'Import {len(bulk_files)} working papers',type='primary',key='bulk_confirm'):
      def do_bulk():
       if len(bulk_files)>200:raise ValueError('Maximum 200 files per import')
       for file in bulk_files:create_indexed_wp(s,u.id,e.id,bulk_folder.id,file.name,file.getvalue())
      act(do_bulk,f'Imported {len(bulk_files)} working papers as Draft.')
   else:st.info('Create a destination folder first.')
  with st.expander('Import folder hierarchy from ZIP'):
   st.caption('ZIP files can contain nested folders and supported working papers. Each imported WP is assigned to you as preparer and starts as Draft.')
   zip_parent=st.selectbox('Import under', [None]+folders,format_func=lambda f:f'{f.idx} — {f.title}' if f else 'Engagement root',key='zip_parent')
   zip_file=st.file_uploader('Choose a ZIP archive',type=['zip'],key='zip_import')
   if zip_file:
    try:
     archive_bytes=zip_file.getvalue()
     if len(archive_bytes)>150*1024*1024:raise ValueError('ZIP exceeds 150 MB')
     with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
      entries=[];total=0;names=set()
      for info in z.infolist():
       path=info.filename.replace('\\','/')
       parts=path.rstrip('/').split('/')
       if not path or path.startswith('/') or any(x in ('','..','.') for x in parts) or ':' in path or '\x00' in path:raise ValueError(f'Unsafe archive path: {path}')
       if (info.external_attr >> 16) & 0o170000 == 0o120000:raise ValueError('Symbolic links are not supported')
       if path.casefold() in names:raise ValueError('Duplicate ZIP entry')
       names.add(path.casefold())
       if not info.is_dir():
        if Path(path).suffix.lower() not in ('.xls','.xlsx','.doc','.docx','.pdf','.jpg','.jpeg','.png','.ppt','.pptx'):raise ValueError(f'Unsupported file: {path}')
        if not 0<info.file_size<=50*1024*1024:raise ValueError(f'Invalid file size: {path}')
        total+=info.file_size
       entries.append((path,info.is_dir()))
      if len(entries)>500 or total>150*1024*1024:raise ValueError('Archive exceeds 500 entries or 150 MB uncompressed')
      if not any(not isdir for _,isdir in entries):raise ValueError('ZIP contains no working papers')
     st.caption(f'{sum(isdir for _,isdir in entries)} explicit folders, {sum(not isdir for _,isdir in entries)} working papers · {total/1024/1024:.1f} MB uncompressed')
     st.dataframe([{'Path in ZIP':path,'Type':'Folder' if isdir else 'Working paper'} for path,isdir in entries],use_container_width=True,hide_index=True)
     if st.button('Confirm ZIP import',type='primary',key='zip_confirm'):
      def do_zip_import():
       permission(s,u.id,e.id,'Preparer');editable(s,e.id)
       # Existing destination is unchanged. Each archive directory becomes a new indexed folder.
       mapping={'':zip_parent.id if zip_parent else None}
       directory_paths=set()
       for path,isdir in entries:
        parts=path.rstrip('/').split('/')
        upto=len(parts) if isdir else len(parts)-1
        for k in range(1,upto+1):directory_paths.add('/'.join(parts[:k]))
       for directory in sorted(directory_paths,key=lambda x:(x.count('/'),x.casefold())):
        parent_path=directory.rpartition('/')[0]
        f=create_indexed_folder(s,u.id,e.id,directory.split('/')[-1],mapping[parent_path]);mapping[directory]=f.id
       with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
        for path,isdir in entries:
         if isdir:continue
         parent_path=path.rpartition('/')[0]
         # Files placed at the archive root need a dedicated folder if importing at engagement root.
         parent_id=mapping[parent_path]
         if parent_id is None:
          if '_root_files' not in mapping:
           f=create_indexed_folder(s,u.id,e.id,Path(zip_file.name).stem);mapping['_root_files']=f.id
          parent_id=mapping['_root_files']
         create_indexed_wp(s,u.id,e.id,parent_id,path.split('/')[-1],z.read(path))
      act(do_zip_import,'ZIP folder hierarchy and working papers imported as Draft.')
    except Exception as ex:st.error(f'ZIP cannot be imported: {ex}')
elif page=='Review Queue':
 if u.admin:st.error('Administrator cannot perform professional reviews.');st.stop()
 st.subheader('My review queue')
 st.caption('Working papers submitted for your assigned review level. Review permissions and decisions are unchanged.')
 e=choose_eng()
 queue=s.query(WP).filter_by(engagement_id=e.id,status='Submitted').all()
 queue=[w for w in queue if s.query(Assignment).filter_by(user_id=u.id,engagement_id=e.id,role='Reviewer',level=w.level).first()]
 c1,c2,c3=st.columns(3)
 c1.metric('Awaiting my review',len(queue))
 c2.metric('Level 1',sum(w.level==1 for w in queue))
 c3.metric('Level 2 or higher',sum(w.level>=2 for w in queue))
 if queue:
  st.markdown('#### Pending working papers')
  table([{'Index':w.idx,'Working paper':w.title,'Review level':w.level,'Current version':w.version,'Status':w.status} for w in queue])
  wp=st.selectbox('Select working paper to review',queue,format_func=lambda w:f'{w.idx} — {w.title} (Level {w.level})')
  v=s.query(Version).filter_by(wp_id=wp.id).order_by(Version.number.desc()).first()
  st.markdown('#### Review details')
  c1,c2,c3=st.columns(3)
  c1.metric('Current WP version',wp.version)
  c2.metric('Review level',wp.level)
  c3.metric('Latest stored version',v.number if v else '—')
  if v is None:
   st.error('No stored working-paper version was found. Review decision is unavailable.')
  elif v.number!=wp.version:
   st.error('Version mismatch. Approval blocked until the preparer resubmits the latest version.')
  else:
   st.download_button('⬇ Download current working paper',(ROOT/'storage'/v.path).read_bytes(),file_name=v.filename)
   with st.form('review'):
    st.markdown('**Record your review decision**')
    action=st.radio('Decision',['Return','Approve'],horizontal=True)
    observation=st.text_area('Review observation',placeholder='Describe the correction required when returning the working paper.')
    st.caption('An observation is mandatory when returning a working paper. Approval follows existing review permissions.')
    go=st.form_submit_button('Record review decision',type='primary')
    if go:act(lambda:review(s,wp,u.id,action,observation),f'Review decision recorded: {action}. Refresh to verify status and level.')
 else:st.info('No working papers awaiting your review for this engagement.')
elif page=='Review Notes':
 if u.admin:st.error('Administrator cannot manage professional review notes.');st.stop()
 st.subheader('Review observations')
 st.caption('Track reviewer observations, preparer responses and closure of review points.')
 e=choose_eng()
 notes=s.query(Note).join(WP).filter(WP.engagement_id==e.id).all()
 c1,c2,c3=st.columns(3)
 c1.metric('Open observations',sum(n.status=='Open' for n in notes))
 c2.metric('Responded',sum(n.status=='Responded' for n in notes))
 c3.metric('Closed',sum(n.status=='Closed' for n in notes))
 if notes:
  status_filter=st.selectbox('Filter observations',['All','Open','Responded','Closed'],key='review_notes_status_filter')
  filtered=[n for n in notes if status_filter=='All' or n.status==status_filter]
  st.caption(f'{len(filtered)} of {len(notes)} observation(s) displayed')
  for n in filtered:
   wp=s.get(WP,n.wp_id)
   with st.expander(f'{wp.idx} — {wp.title}  |  Observation {n.id}  |  {n.status}'):
    st.markdown('**Reviewer observation**')
    st.write(n.body)
    responses=s.query(Response).filter_by(note_id=n.id).all()
    if responses:
     st.markdown('**Preparer responses / discussion**')
     for r in responses:
      responder=s.get(User,r.user_id)
      st.write(f'**{responder.initials if responder else "User"}:** {r.body}')
    else:st.caption('No response recorded yet.')
    if wp.preparer_id==u.id and e.status=='Open' and n.status!='Closed':
     with st.form(f'res{n.id}'):
      answer=st.text_area('Your response');go=st.form_submit_button('Submit response')
      if go and answer.strip():act(lambda:(s.add(Response(note_id=n.id,user_id=u.id,body=answer)),setattr(n,'status','Responded'),log(s,u.id,'Respond note',n.id)),f'Response saved for review note {n.id}.')
    if n.reviewer_id==u.id and e.status=='Open' and n.status=='Responded' and st.button('Close observation',key=f'close{n.id}'):
     act(lambda:(setattr(n,'status','Closed'),log(s,u.id,'Close note',n.id)),f'Review note {n.id} closed successfully.')
 else:st.info('No review observations for this engagement.')
elif page=='Audit Trail':
 st.header('Audit Trail (read-only)')
 if not (u.admin or u.designation in PARTNER_DESIGNATIONS):st.error('Access denied');st.stop()
 visible_engs=s.query(Engagement).all() if u.admin else s.query(Engagement).join(Assignment).filter(Assignment.user_id==u.id).all()
 if not visible_engs:st.info('No assigned engagements');st.stop()
 selected_eng=st.selectbox('Engagement',visible_engs,format_func=lambda e:f'{e.id} — {s.get(Client,e.client_id).name} — {e.kind} — {e.fy}')
 # Logs are linked through structured action details or referenced WP/note IDs in older records.
 wpids={w.id for w in s.query(WP).filter_by(engagement_id=selected_eng.id)}
 noteids={n.id for n in s.query(Note).filter(Note.wp_id.in_(wpids))} if wpids else set()
 relevant=[]
 for item in s.query(Log).order_by(Log.id.desc()).all():
  detail=str(item.detail or '').strip()
  if item.action in ('Finalise','Create folder','Create engagement','Assign'):
   belongs=(detail==str(selected_eng.id) if item.action=='Finalise' else (f'Engagement {selected_eng.id};' in detail if item.action=='Assign' else False))
  elif item.action in ('Submit','Approve','Return','Upload'):
   belongs=(detail in {str(i) for i in wpids} or any(detail.startswith(f'WP {i} ') for i in wpids))
  elif item.action in ('Respond note','Close note'):
   belongs=detail in {str(i) for i in noteids}
  else:belongs=False
  if belongs:relevant.append(item)
 st.caption('Engagement-linked events only. Historic records without an engagement reference may not appear; original database logs are preserved.')
 action_filter=st.selectbox('Action',['All']+sorted({x.action for x in relevant}))
 rows=[dict(Log_ID=x.id,Date_Time=str(x.at),User=(s.get(User,x.user_id).name if s.get(User,x.user_id) else f'User {x.user_id}'),Action=x.action,Detail=x.detail) for x in relevant if action_filter=='All' or x.action==action_filter]
 table(rows)
 buf=BytesIO()
 with pd.ExcelWriter(buf,engine='openpyxl') as writer:pd.DataFrame(rows,columns=['Log_ID','Date_Time','User','Action','Detail']).to_excel(writer,index=False,sheet_name='Audit Trail')
 st.download_button('Export filtered audit trail to Excel',buf.getvalue(),file_name=f'audit_trail_engagement_{selected_eng.id}.xlsx')
elif page=='Reports':
 e=choose_eng();rows=[dict(Index=w.idx,Title=w.title,Status=w.status,Version=w.version,Review_Level=w.level,Preparer=s.get(User,w.preparer_id).initials) for w in s.query(WP).filter_by(engagement_id=e.id)];table(rows)
 from io import BytesIO
 buf=BytesIO()
 with pd.ExcelWriter(buf,engine='openpyxl') as writer:pd.DataFrame(rows,columns=['Index','Title','Status','Version','Review_Level','Preparer']).to_excel(writer,index=False)
 st.download_button('Export register to Excel',buf.getvalue(),file_name='working_paper_register.xlsx')
 st.divider()
 phase1_export(s,e)
s.close()
