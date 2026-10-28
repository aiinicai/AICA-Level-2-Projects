"""ABC Chartered Accountants Team Office. Entirely offline; Python 3.12 standard-library server."""
from __future__ import annotations
import argparse
import base64
import contextlib
import datetime as dt
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

FIRM = 'ABC Chartered Accountants'
VERSION = '1.0.1'
ROOT = Path(__file__).resolve().parent.parent
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
STATUSES = ['Assigned','In progress','Ready for review','Corrections required','Completed','Cancelled']
SCHEMA = {
 'Employees':['id','name','designation','email','mobile','role','manager','active','version','username','forceChange','sessionVersion'],
 'Clients':['id','name','entityType','contact','email','mobile','manager','active','version'],
 'WorkTypes':['id','name','periodicity','active','version'],
 'Periodicities':['id','name','active','version'],
 'Assignments':['id','client','work','periodicity','financialYear','period','employee','reviewer','allocationDate','targetDate','deadline','priority','status','blocker','instructions','progress','nextAction','expectedDate','documentLink','reviewComments','updatedBy','updatedAt','version'],
 'Timesheets':['id','employee','date','assignment','client','minutes','note','updatedBy','updatedAt','version','startTime','endTime','billing'],
 'Communications':['id','title','message','priority','active','createdBy','createdAt','updatedBy','updatedAt','version'],
 'TimeQueries':['id','employee','date','question','answer','askedBy','askedAt','answeredAt','version'],
 'Sessions':['id','employee','expiry','sessionVersion'],
 'ResetRequests':['id','employee','time','status'],
 'History':['id','assignment','actor','time','details']
}
PERIODS = {
 'Monthly':['April','May','June','July','August','September','October','November','December','January','February','March'],
 'Quarterly':['Apr–Jun','Jul–Sep','Oct–Dec','Jan–Mar'],
 'Half-yearly':['Apr–Sep','Oct–Mar'], 'Annually':['Full financial year']
}

def stamp(): return dt.datetime.now(IST).isoformat(timespec='seconds')
def today(): return dt.datetime.now(IST).date().isoformat()
def uid(prefix=''): return prefix + uuid.uuid4().hex

def valid_date(value):
 try: return bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(value))) and dt.date.fromisoformat(value).isoformat() == value
 except (ValueError, TypeError): return False

def password_check(value):
 if not isinstance(value, str) or not 12 <= len(value) <= 128:
  raise ValueError('Use a password between 12 and 128 characters.')

def hash_password(value):
 password_check(value)
 salt = secrets.token_bytes(16)
 hashed = hashlib.pbkdf2_hmac('sha256', value.encode('utf-8'), salt, 600000)
 return 'pbkdf2_sha256$600000$' + salt.hex() + '$' + hashed.hex()

def verify_password(value, stored):
 try:
  algorithm, rounds, salt, expected = stored.split('$')
  if algorithm != 'pbkdf2_sha256' or not isinstance(value, str) or len(value) > 128: return False
  result = hashlib.pbkdf2_hmac('sha256', value.encode('utf-8'), bytes.fromhex(salt), int(rounds))
  return hmac.compare_digest(result.hex(), expected)
 except (ValueError, TypeError, AttributeError): return False

def digest(value): return hashlib.sha256(value.encode('utf-8')).hexdigest()

def clock_minutes(value):
 if not isinstance(value, str) or not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', value):
  raise ValueError('Enter time in 24-hour HH:MM format, for example 09:30.')
 h, m = map(int, value.split(':')); return h * 60 + m

def hours(value): return f'{value // 60}:{value % 60:02d}'

class Database:
 def __init__(self, folder):
  self.folder = Path(folder); self.folder.mkdir(parents=True, exist_ok=True)
  self.path = self.folder / 'office.sqlite3'
  self.backups = self.folder / 'backups'; self.backups.mkdir(exist_ok=True)
  with self.connect() as con:
   con.executescript('''
   CREATE TABLE IF NOT EXISTS records(kind TEXT NOT NULL,id TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(kind,id));
   CREATE TABLE IF NOT EXISTS credentials(employee TEXT PRIMARY KEY, password_hash TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY,count INTEGER NOT NULL,expiry REAL NOT NULL);
   ''')
   con.execute('PRAGMA user_version=1')
   con.execute('PRAGMA journal_mode=WAL')
   service = Service(con, self)
   if not service.rows('Periodicities'):
    for i, name in enumerate(['Monthly','Quarterly','Half-yearly','Annually','One-time'],1):
     service.write('Periodicities',dict(id=f'PER{i}',name=name,active='Yes',version='1'))
   if not service.rows('WorkTypes'):
    for i,(name,periodicity) in enumerate([
      ('Accounting / Bookkeeping','Monthly'),('GST compliance','Monthly'),('TDS compliance','Quarterly'),
      ('Payroll processing','Monthly'),('Statutory audit','Annually'),('Income tax return','Annually'),
      ('Internal audit','Quarterly'),('Certification / Other','One-time')],1):
     service.write('WorkTypes',dict(id=f'WK{i}',name=name,periodicity=periodicity,active='Yes',version='1'))
  try:
   self.daily_backup()
  except (OSError, sqlite3.Error) as error:
   # A backup issue must not prevent access to the working office database.
   print('Startup backup could not be completed: '+str(error), flush=True)
   with contextlib.suppress(OSError):
    with (self.folder/'error.log').open('a',encoding='utf-8') as log:
     log.write(stamp()+' Startup backup failed: '+str(error)+'\n')
 @contextlib.contextmanager
 def connect(self):
  con = sqlite3.connect(str(self.path), timeout=30)
  try:
   con.execute('PRAGMA busy_timeout=30000'); con.execute('PRAGMA synchronous=FULL')
   with con:
    yield con
  finally:
   # sqlite3.Connection.__exit__ commits/rolls back but does not close handles.
   con.close()
 def daily_backup(self):
  destination = self.backups / ('office-' + today() + '.sqlite3')
  if not destination.exists():
   self.backup(destination)
 def backup(self, destination):
  destination = Path(destination)
  # Unique staging files avoid collisions between simultaneous backup requests.
  temporary = destination.with_name(destination.name+'.'+uuid.uuid4().hex+'.pending')
  try:
   with self.connect() as src:
    with contextlib.closing(sqlite3.connect(str(temporary))) as target:
     src.backup(target)
     target.commit()
   # Both database handles are CLOSED before rename; required on Windows.
   os.replace(temporary, destination)
   return destination
  finally:
   with contextlib.suppress(OSError):
    temporary.unlink(missing_ok=True)
 def invoke(self, name, args):
  if name not in RPC_METHODS or not isinstance(args, list): raise ValueError('Invalid operation.')
  # Password login throttles must persist even when authentication is rejected.
  if name in ('login','forgotPassword','recoverOwner'):
   identity = str(args[0] if args else '').lower().strip()
   with self.connect() as con:
    Service(con,self).throttle(identity, name, 10 if name == 'login' else 3)
  if name == 'backupDatabase':
   with self.connect() as con: Service(con,self).require_admin(args[0] if args else '')
   filename = 'ABC-Office-Backup-' + dt.datetime.now(IST).strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(2) + '.sqlite3'
   path = self.backup(self.backups / filename)
   return dict(filename=filename,mime='application/vnd.sqlite3',base64=base64.b64encode(path.read_bytes()).decode())
  with self.connect() as con:
   con.execute('BEGIN IMMEDIATE')
   service = Service(con,self)
   return getattr(service,name)(*args)

class Service:
 def __init__(self, con, database): self.con = con; self.database = database
 def rows(self, kind):
  if kind not in SCHEMA: raise ValueError('Invalid register.')
  return [json.loads(r[0]) for r in self.con.execute('SELECT data FROM records WHERE kind=? ORDER BY rowid',(kind,))]
 def write(self, kind, record):
  if kind not in SCHEMA or not record.get('id'): raise ValueError('Invalid record.')
  value = {k:str(record.get(k,'') if record.get(k) is not None else '') for k in SCHEMA[kind]}
  self.con.execute('INSERT INTO records(kind,id,data) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data', (kind,value['id'],json.dumps(value,ensure_ascii=False)))
  return value
 def get_meta(self,key):
  row = self.con.execute('SELECT value FROM meta WHERE key=?',(key,)).fetchone(); return row[0] if row else ''
 def set_meta(self,key,value): self.con.execute('INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))
 def history(self,user,assignment,details): self.write('History',dict(id=uid(),assignment=assignment,actor=user['username'],time=stamp(),details=details))
 def find(self,kind,id): return next((x for x in self.rows(kind) if x['id']==id),None)
 def throttle(self,identity,kind,limit):
  key = digest(kind+identity); now=time.time()
  self.con.execute('DELETE FROM attempts WHERE expiry<?',(now,))
  row=self.con.execute('SELECT count,expiry FROM attempts WHERE key=?',(key,)).fetchone()
  if row and row[0]>=limit: raise ValueError('Too many attempts. Try again in 15 minutes.')
  self.con.execute('INSERT INTO attempts VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET count=excluded.count,expiry=excluded.expiry',(key,row[0]+1 if row else 1,row[1] if row else now+900))
 def user(self,token,allow_change=False):
  if not isinstance(token,str) or not token: raise ValueError('Please log in.')
  session=self.find('Sessions',digest(token)); e=self.find('Employees',session['employee']) if session else None
  if not e or e['active']!='Yes' or float(session['expiry'])<time.time() or session['sessionVersion']!=(e['sessionVersion'] or '1'):
   raise ValueError('Session expired. Log in again.')
  if e['forceChange']=='Yes' and not allow_change: raise ValueError('Change your temporary password first.')
  return dict(id=e['id'],name=e['name'],username=e['username'],email=e['email'],role=e['role'],admin=e['role'] in ('Administrator','Manager') or e['id']==self.get_meta('owner'),needsChange=e['forceChange']=='Yes')
 def require_admin(self,token):
  u=self.user(token)
  if not u['admin']: raise ValueError('Administrator or Manager access required.')
  return u
 def issue(self,e):
  for s in self.rows('Sessions'):
   if float(s['expiry']) < time.time(): self.con.execute('DELETE FROM records WHERE kind=? AND id=?',('Sessions',s['id']))
  token=secrets.token_urlsafe(48)
  self.write('Sessions',dict(id=digest(token),employee=e['id'],expiry=str(time.time()+3600),sessionVersion=e['sessionVersion'] or '1'))
  return dict(token=token,user=dict(id=e['id'],name=e['name'],username=e['username'],needsChange=e['forceChange']=='Yes'))
 def set_password(self,e,password):
  self.con.execute('INSERT INTO credentials VALUES(?,?) ON CONFLICT(employee) DO UPDATE SET password_hash=excluded.password_hash',(e['id'],hash_password(password)))
 def verify_employee(self,e,password):
  row=self.con.execute('SELECT password_hash FROM credentials WHERE employee=?',(e['id'],)).fetchone()
  return bool(row and verify_password(password,row[0]))
 def createAdministrator(self,values):
  if self.rows('Employees'): raise ValueError('Initial setup is already complete. Sign in.')
  if not isinstance(values,dict): raise ValueError('Invalid setup details.')
  username=str(values.get('username','')).strip().lower(); name=str(values.get('name','')).strip(); email=str(values.get('email','')).strip()
  if not re.fullmatch(r'[a-z][a-z0-9._-]{2,39}',username): raise ValueError('Username: 3–40 characters; start with a letter.')
  if not name or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise ValueError('Enter your name and contact email.')
  password_check(values.get('password'))
  e=dict(id='EMP001',name=name,email=email,role='Administrator',active='Yes',version='1',username=username,forceChange='No',sessionVersion='1')
  e=self.write('Employees',e); self.set_password(e,values['password']); self.set_meta('owner',e['id'])
  recovery=secrets.token_hex(20); self.set_meta('recovery_hash',digest(recovery))
  result=self.issue(e); result['recoveryCode']=recovery; return result
 def login(self,username,password):
  username=str(username or '').lower().strip()
  e=next((e for e in self.rows('Employees') if e['username']==username and e['active']=='Yes'),None)
  if not e or not self.verify_employee(e,password): raise ValueError('Login failed. Check your username and password.')
  self.con.execute('DELETE FROM attempts WHERE key=?',(digest('login'+username),))
  return self.issue(e)
 def logout(self,token):
  self.con.execute('DELETE FROM records WHERE kind=? AND id=?',('Sessions',digest(str(token or '')))); return True
 def changePassword(self,token,currentPassword,newPassword):
  u=self.user(token,True); e=self.find('Employees',u['id'])
  if not self.verify_employee(e,currentPassword): raise ValueError('Current password is incorrect.')
  self.set_password(e,newPassword); e['forceChange']='No'; e['sessionVersion']=str(int(e['sessionVersion'] or 1)+1); self.write('Employees',e); return self.issue(e)
 def forgotPassword(self,username):
  e=next((e for e in self.rows('Employees') if e['username']==str(username).strip().lower() and e['active']=='Yes'),None)
  if e and not any(r['employee']==e['id'] and r['status']=='Pending' for r in self.rows('ResetRequests')):
   self.write('ResetRequests',dict(id=uid(),employee=e['id'],time=stamp(),status='Pending'))
  return 'If this account is active, a reset request has been recorded. Ask an administrator or manager to verify and reset it. Offline mode does not send email.'
 def recoverOwner(self,username,recoveryCode,newPassword):
  owner=self.find('Employees',self.get_meta('owner'))
  if not owner or owner['username']!=str(username).strip().lower() or not hmac.compare_digest(digest(str(recoveryCode)),self.get_meta('recovery_hash')):
   raise ValueError('Recovery details are incorrect.')
  self.set_password(owner,newPassword); owner['forceChange']='No'; owner['sessionVersion']=str(int(owner['sessionVersion'] or 1)+1); self.write('Employees',owner)
  recovery=secrets.token_hex(20); self.set_meta('recovery_hash',digest(recovery)); result=self.issue(owner); result['recoveryCode']=recovery; return result
 def resetEmployeePassword(self,token,employeeId,temporaryPassword,verified):
  u=self.require_admin(token)
  if verified is not True: raise ValueError('Verify the employee before resetting their password.')
  if employeeId==u['id']: raise ValueError('Use Change password for your own account.')
  e=self.find('Employees',employeeId)
  if not e or e['active']!='Yes': raise ValueError('Active employee not found.')
  self.set_password(e,temporaryPassword); e['forceChange']='Yes'; e['sessionVersion']=str(int(e['sessionVersion'] or 1)+1); self.write('Employees',e)
  for r in self.rows('ResetRequests'):
   if r['employee']==employeeId and r['status']=='Pending': r['status']='Resolved'; self.write('ResetRequests',r)
  self.history(u,'ACCOUNT:'+e['id'],'Password reset after employee verification.'); return self.bootstrap(token)
 def bootstrap(self,token):
  u=self.user(token); data={k:self.rows(k) for k in ['Employees','Clients','WorkTypes','Periodicities','Assignments','Timesheets','TimeQueries','Communications']}
  data['Employees']=[{k:v for k,v in e.items() if k not in ('forceChange','sessionVersion')} for e in data['Employees']]
  data['Communications']=[c for c in data['Communications'] if u['admin'] or c['active']=='Yes']
  data['Assignments']=[a for a in data['Assignments'] if u['admin'] or a['employee']==u['id'] or a['reviewer']==u['id']]
  data['Timesheets']=[t for t in data['Timesheets'] if u['admin'] or t['employee']==u['id']]
  data['TimeQueries']=[q for q in data['TimeQueries'] if u['admin'] or q['employee']==u['id']]
  if not u['admin']:
   data['Clients']=[c for c in data['Clients'] if any(a['client']==c['id'] for a in data['Assignments']) or any(t['client']==c['id'] for t in data['Timesheets'])]
   data['Employees']=[{k:e[k] for k in ('id','name','active')} for e in data['Employees']]
  return dict(user=u,data=data,statuses=STATUSES,today=today(),resetRequests=[r for r in self.rows('ResetRequests') if r['status']=='Pending'] if u['admin'] else [])
 def saveMaster(self,token,kind,input):
  self.require_admin(token)
  if kind not in ('Employees','Clients','WorkTypes','Periodicities'): raise ValueError('Invalid register.')
  old=self.find(kind,input.get('id'))
  if input.get('id') and not old: raise ValueError('Record no longer exists.')
  if old and str(input.get('version'))!=old['version']: raise ValueError('Record changed. Refresh and try again.')
  o={k:str(input.get(k,'') or '').strip() for k in SCHEMA[kind] if k not in ('forceChange','sessionVersion')}
  if not o.get('name') or len(o['name'])>200: raise ValueError('Enter a name of up to 200 characters.')
  o['id']=old['id'] if old else uid(kind[:3].upper()+'-'); o['active']='No' if o.get('active')=='No' else 'Yes'; o['version']=str(int(old['version'])+1 if old else 1)
  if any(x['id']!=o['id'] and x['name'].casefold()==o['name'].casefold() for x in self.rows(kind)): raise ValueError('A record with this name already exists.')
  if kind=='Employees':
   if o.get('role') not in ('Administrator','Manager','Staff'): raise ValueError('Select a role.')
   if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',o.get('email','')): raise ValueError('Enter a valid contact email.')
   o['username']=o.get('username','').lower()
   if not re.fullmatch(r'[a-z][a-z0-9._-]{2,39}',o['username']): raise ValueError('Username: 3–40 characters; start with a letter.')
   if old and old['username']!=o['username']: raise ValueError('Username cannot be changed after login creation.')
   if any(e['id']!=o['id'] and e['username']==o['username'] for e in self.rows(kind)): raise ValueError('Username already used.')
   if o['id']==self.get_meta('owner') and (o['active']!='Yes' or o['role']!='Administrator'): raise ValueError('The owner must remain active as Administrator.')
   if old:
    o['forceChange']=old['forceChange']; o['sessionVersion']=str(int(old['sessionVersion'] or 1)+(1 if any(old.get(k)!=o.get(k) for k in ('role','active','email')) else 0))
   else:
    self.set_password(o,input.get('temporaryPassword')); o['forceChange']='Yes'; o['sessionVersion']='1'
  if kind=='WorkTypes' and not any(p['name']==o.get('periodicity') and p['active']=='Yes' for p in self.rows('Periodicities')): raise ValueError('Select an active periodicity.')
  if kind=='Periodicities' and o['name'] not in ('Monthly','Quarterly','Half-yearly','Annually','One-time'): raise ValueError('Use a supported periodicity name.')
  self.write(kind,o); return self.bootstrap(token)
 def saveAssignment(self,token,input):
  u=self.user(token); old=self.find('Assignments',input.get('id'))
  if input.get('id') and not old: raise ValueError('Assignment no longer exists.')
  if old and str(input.get('version'))!=old['version']: raise ValueError('Another user updated this assignment. Refresh before saving.')
  if not u['admin'] and (not old or old['employee']!=u['id']): raise ValueError('Only your allocated assignments may be updated.')
  o=dict(old or {})
  for k in SCHEMA['Assignments'] if u['admin'] else ['status']:
   if k in input: o[k]=str(input[k] or '').strip()
  if not u['admin']:
   if o.get('status') not in ('In progress','Ready for review'): raise ValueError('Staff may select only In progress or Ready for review.')
   if old['status'] in ('Completed','Cancelled'): raise ValueError('Ask an administrator or manager to reopen closed work.')
  for key,kind in [('client','Clients'),('work','WorkTypes'),('employee','Employees'),('reviewer','Employees')]:
   item=self.find(kind,o.get(key))
   if not item or ((not old or old[key]!=o.get(key)) and item['active']!='Yes'): raise ValueError('Select an active '+key+'.')
  if not any(p['name']==o.get('periodicity') and ((old and old['periodicity']==o.get('periodicity')) or p['active']=='Yes') for p in self.rows('Periodicities')): raise ValueError('Select a periodicity.')
  fy=o.get('financialYear','')
  if not re.fullmatch(r'\d{4}–\d{2}',fy) or int(fy[-2:])!=(int(fy[:4])+1)%100: raise ValueError('Select a valid financial year.')
  if not o.get('period') or (o.get('periodicity') in PERIODS and o['period'] not in PERIODS[o['periodicity']]): raise ValueError('Select a valid work period.')
  if o.get('status') not in STATUSES: raise ValueError('Invalid status.')
  if o.get('priority') not in ('Normal','High','Urgent'): raise ValueError('Invalid priority.')
  if o.get('blocker') not in ('None','Awaiting client documents','Awaiting clarification','Other'): raise ValueError('Invalid blocker.')
  for k in ('allocationDate','targetDate','deadline','expectedDate'):
   if o.get(k) and not valid_date(o[k]): raise ValueError('Invalid '+k)
  if not o.get('allocationDate') or not o.get('targetDate'): raise ValueError('Allocation and target dates are required.')
  if o['targetDate']<o['allocationDate']: raise ValueError('Target date must be on or after allocation date.')
  if o.get('documentLink') and not o['documentLink'].lower().startswith('https://'): raise ValueError('Document link must begin with https://')
  o['id']=old['id'] if old else uid('ASG-')[:16].upper(); o['updatedBy']=u['username']; o['updatedAt']=stamp(); o['version']=str(int(old['version'])+1 if old else 1)
  changes='\n'.join(k+': '+str((old or {}).get(k,''))+' → '+str(o.get(k,'')) for k in SCHEMA['Assignments'] if k not in ('updatedBy','updatedAt','version') and (old or {}).get(k,'')!=o.get(k,''))
  self.write('Assignments',o); self.history(u,o['id'],changes); return self.bootstrap(token)
 def getHistory(self,token,id):
  u=self.user(token); a=self.find('Assignments',id)
  if not a or (not u['admin'] and a['employee']!=u['id'] and a['reviewer']!=u['id']): raise ValueError('Access denied.')
  return [r for r in self.rows('History') if r['assignment']==id]
 def saveTime(self,token,input):
  u=self.user(token); old=self.find('Timesheets',input.get('id'))
  if input.get('id') and not old: raise ValueError('Entry not found.')
  if old and old['employee']!=u['id']: raise ValueError('Only the employee may edit their time.')
  if old and old['version']!=str(input.get('version')): raise ValueError('Entry changed. Refresh first.')
  date=str(input.get('date') or ''); assignment=str(input.get('assignment') or ''); note=str(input.get('note') or '').strip()
  if not valid_date(date): raise ValueError('Select a valid work date.')
  if not note or len(note)>4000: raise ValueError('Enter work details of up to 4000 characters.')
  legacy=old and not old.get('startTime') and not old.get('endTime') and not input.get('startTime') and not input.get('endTime')
  startTime=''; endTime=''
  if legacy:
   try: minutes=int(input.get('minutes'))
   except (TypeError,ValueError): raise ValueError('Invalid duration.')
   if str(minutes)!=str(input.get('minutes')) or not 1<=minutes<=1440: raise ValueError('Duration must be 1–1440 whole minutes.')
  else:
   startTime=str(input.get('startTime') or ''); endTime=str(input.get('endTime') or '')
   start=clock_minutes(startTime); end=clock_minutes(endTime)
   if end<=start: raise ValueError('End time must be after start time on the same day.')
   minutes=end-start
   if any(t['id']!=(old['id'] if old else '') and t['employee']==u['id'] and t['date']==date and t.get('startTime') and t.get('endTime') and start<clock_minutes(t['endTime']) and end>clock_minutes(t['startTime']) for t in self.rows('Timesheets')):
    raise ValueError('This time range overlaps another entry for this date.')
  client=''
  if assignment!='IDLE':
   a=self.find('Assignments',assignment)
   if not a or a['employee']!=u['id']: raise ValueError('Select an assignment allocated to you.')
   client=a['client']
  billing='Non-billable' if assignment=='IDLE' else str(input.get('billing') or '')
  if billing not in ('Billable','Non-billable'):
   if legacy and not old.get('billing'): billing=''
   else: raise ValueError('Select Billable or Non-billable.')
  o=dict(id=old['id'] if old else uid('TIM-'),employee=u['id'],date=date,assignment=assignment,client=client,minutes=str(minutes),note=note,startTime=startTime,endTime=endTime,billing=billing,updatedBy=u['username'],updatedAt=stamp(),version=str(int(old['version'])+1 if old else 1))
  self.write('Timesheets',o); self.history(u,'TIME:'+o['id'],json.dumps(dict(before=old,after=o),ensure_ascii=False)); return self.bootstrap(token)
 def getCommunications(self,token):
  u=self.user(token); return [c for c in self.rows('Communications') if u['admin'] or c['active']=='Yes']
 def saveCommunication(self,token,input):
  u=self.require_admin(token); old=self.find('Communications',input.get('id'))
  if input.get('id') and not old: raise ValueError('Update not found.')
  if old and old['version']!=str(input.get('version')): raise ValueError('Update changed. Refresh first.')
  title=str(input.get('title') or '').strip(); message=str(input.get('message') or '').strip(); priority=str(input.get('priority') or 'Normal')
  if not title or len(title)>150 or not message or len(message)>6000: raise ValueError('Enter a title up to 150 characters and a message up to 6000 characters.')
  if priority not in ('Normal','Important','Urgent'): raise ValueError('Invalid priority.')
  o=dict(id=old['id'] if old else uid('NEWS-'),title=title,message=message,priority=priority,active='No' if input.get('active')=='No' else 'Yes',createdBy=old['createdBy'] if old else u['name'],createdAt=old['createdAt'] if old else stamp(),updatedBy=u['name'],updatedAt=stamp(),version=str(int(old['version'])+1 if old else 1))
  self.write('Communications',o); self.history(u,'NEWS:'+o['id'],('Updated' if old else 'Published')+' office update: '+title); return self.getCommunications(token)
 def timeQuestion(self,token,employee,date,question,version):
  u=self.require_admin(token)
  if not valid_date(date) or not self.find('Employees',employee): raise ValueError('Invalid employee or date.')
  question=str(question or '').strip()
  if not question or len(question)>2000: raise ValueError('Enter a question of up to 2000 characters.')
  old=next((q for q in self.rows('TimeQueries') if q['employee']==employee and q['date']==date),None)
  if old and old['version']!=str(version): raise ValueError('Question changed. Refresh first.')
  o=dict(id=old['id'] if old else uid(),employee=employee,date=date,question=question,answer='',askedBy=u['username'],askedAt=stamp(),answeredAt='',version=str(int(old['version'])+1 if old else 1))
  self.write('TimeQueries',o); self.history(u,'TIMEQUERY:'+o['id'],json.dumps(dict(before=old,after=o),ensure_ascii=False)); return self.bootstrap(token)
 def timeAnswer(self,token,id,answer,version):
  u=self.user(token); q=self.find('TimeQueries',id)
  if not q or q['employee']!=u['id']: raise ValueError('Only the employee may answer.')
  if q['version']!=str(version): raise ValueError('Question changed. Refresh first.')
  answer=str(answer or '').strip()
  if not answer or len(answer)>4000: raise ValueError('Enter an answer of up to 4000 characters.')
  q['answer']=answer; q['answeredAt']=stamp(); q['version']=str(int(q['version'])+1)
  self.write('TimeQueries',q); self.history(u,'TIMEQUERY:'+q['id'],'Response: '+answer); return self.bootstrap(token)
 def previewTimeReport(self,token,f):
  self.require_admin(token)
  if not valid_date(f.get('from')) or not valid_date(f.get('to')) or f['from']>f['to']: raise ValueError('Select a valid date range.')
  if f.get('type') not in ('Staff','Client'): raise ValueError('Select a report type.')
  employees=self.rows('Employees'); clients=self.rows('Clients'); assignments=self.rows('Assignments'); worktypes=self.rows('WorkTypes')
  lookup=lambda records,id: next((r['name'] for r in records if r['id']==id),id or '—')
  if f['type']=='Staff' and not self.find('Employees',f.get('employee')): raise ValueError('Select an employee.')
  if (f['type']=='Client' or f.get('client')) and not self.find('Clients',f.get('client')): raise ValueError('Select a client.')
  if f['type']=='Client' and f.get('assignment') and not any(a['id']==f['assignment'] and a['client']==f['client'] for a in assignments): raise ValueError('Select an assignment of this client.')
  entries=[t for t in self.rows('Timesheets') if f['from']<=t['date']<=f['to'] and ((t['employee']==f['employee'] and (not f.get('client') or t['client']==f['client'])) if f['type']=='Staff' else (t['client']==f['client'] and (not f.get('assignment') or t['assignment']==f['assignment'])))]
  entries.sort(key=lambda t:(t['date'],t['employee'],t.get('startTime','')))
  if len(entries)>1000: raise ValueError('Report exceeds 1000 entries. Select a shorter period.')
  name=lookup(employees,f['employee']) if f['type']=='Staff' else lookup(clients,f['client'])
  groups={}; total=billable=non=idle=0
  for t in entries:
   key=(t['date'],t['employee']); minutes=int(t['minutes'])
   g=groups.setdefault(key,dict(date=t['date'],employee=t['employee'],staff=lookup(employees,t['employee']),minutes=0,rows=[]))
   a=next((a for a in assignments if a['id']==t['assignment']),None)
   work='Idle time' if t['assignment']=='IDLE' else (lookup(worktypes,a['work'])+' / '+a['period']+' '+a['financialYear'] if a else t['assignment'])
   g['rows'].append(['—' if t['assignment']=='IDLE' else lookup(clients,t['client']),work,t.get('startTime',''),t.get('endTime',''),hours(minutes),t.get('billing') or 'Not recorded'])
   g['minutes']+=minutes; total+=minutes
   if t.get('billing')=='Billable': billable+=minutes
   if t.get('billing')=='Non-billable': non+=minutes
   if t['assignment']=='IDLE': idle+=minutes
  return dict(heading='TIME SHEET REPORT OF '+f['type'].upper()+' — '+name+' FOR THE PERIOD '+f['from']+' – '+f['to'],type=f['type'],name=name,**{'from':f['from'],'to':f['to']},count=len(entries),minutes=total,billable=billable,nonBillable=non,idle=idle,unclassified=total-billable-non,groups=sorted(groups.values(),key=lambda g:(g['date'],g['staff'])),clientFilter=lookup(clients,f['client']) if f['type']=='Staff' and f.get('client') else '',assignmentFilter=f.get('assignment','') if f['type']=='Client' else '')
 def exportTimeReport(self,token,f,format):
  layout=self.previewTimeReport(token,f)
  if format not in ('pdf','docx'): raise ValueError('Select PDF or Word.')
  from reports import export_report
  raw=export_report(layout,format)
  if len(raw)>8*1024*1024: raise ValueError('Report too large. Select a shorter period.')
  filename='TIME-SHEET-'+f['type'].upper()+'-'+re.sub(r'[^a-zA-Z0-9_-]+','-',layout['name'])[:60]+'-'+f['from']+'-'+f['to']+'.'+format
  return dict(filename=filename,mime='application/pdf' if format=='pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',base64=base64.b64encode(raw).decode('ascii'))

RPC_METHODS={
 'createAdministrator','login','logout','changePassword','forgotPassword','recoverOwner','resetEmployeePassword',
 'bootstrap','saveMaster','saveAssignment','getHistory','saveTime','getCommunications','saveCommunication',
 'timeQuestion','timeAnswer','previewTimeReport','exportTimeReport','backupDatabase'
}

class OfficeServer(ThreadingHTTPServer):
 daemon_threads=True
 allow_reuse_address=True
 def __init__(self,address,database,lan):
  super().__init__(address,Handler); self.database=database; self.boot_key=secrets.token_urlsafe(32); self.lan=lan
  self.allowed_hosts={'localhost','127.0.0.1',socket.gethostname().lower(),socket.getfqdn().lower()}
  for name in (socket.gethostname(),socket.getfqdn()):
   try: self.allowed_hosts.update(x[4][0] for x in socket.getaddrinfo(name,None,socket.AF_INET))
   except OSError: pass

class Handler(BaseHTTPRequestHandler):
 server_version='ABCOfflineOffice/1.0'
 def log_message(self,*args): pass
 def valid_host(self):
  host=self.headers.get('Host','').split(':')[0].lower()
  return host in (self.server.allowed_hosts if self.server.lan else {'localhost','127.0.0.1'})
 def reply(self,status,body,mime='application/json; charset=utf-8'):
  self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(body)))
  self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('X-Frame-Options','DENY')
  self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'")
  self.end_headers(); self.wfile.write(body)
 def do_GET(self):
  if not self.valid_host(): return self.reply(403,b'Invalid host','text/plain')
  path=urlsplit(self.path).path
  if path=='/api/health': return self.reply(200,json.dumps(dict(product=FIRM,version=VERSION,lan=self.server.lan)).encode())
  if path not in ('/','/index.html'): return self.reply(404,b'Not found','text/plain')
  with self.server.database.connect() as con: first=not Service(con,self.server.database).rows('Employees')
  html=(ROOT/'app'/'index.html').read_text(encoding='utf-8').replace('__BOOT_KEY__',self.server.boot_key).replace('__FIRST_RUN__','true' if first else 'false')
  self.reply(200,html.encode('utf-8'),'text/html; charset=utf-8')
 def do_POST(self):
  if not self.valid_host() or self.path!='/api/rpc': return self.reply(403,b'{}')
  if not hmac.compare_digest(self.headers.get('X-Office-Key',''),self.server.boot_key): return self.reply(403,b'{"error":"Reload the office application."}')
  origin=self.headers.get('Origin')
  if origin and origin!='http://'+self.headers.get('Host',''): return self.reply(403,b'{}')
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size<1 or size>2*1024*1024: raise ValueError('Request is too large or empty.')
   request=json.loads(self.rfile.read(size)); name=request.get('fn'); args=request.get('args',[])
   result=self.server.database.invoke(name,args)
   self.reply(200,json.dumps(dict(result=result),ensure_ascii=False).encode('utf-8'))
  except (ValueError,TypeError,KeyError) as e:
   self.reply(400,json.dumps(dict(error=str(e)),ensure_ascii=False).encode('utf-8'))
  except Exception:
   error=traceback.format_exc()
   with contextlib.suppress(OSError):
    with (self.server.database.folder/'error.log').open('a',encoding='utf-8') as f: f.write(stamp()+'\n'+error+'\n')
   self.reply(500,json.dumps(dict(error='Operation could not finish. Details are in data/error.log. Your saved records remain available.')).encode())

def main():
 parser=argparse.ArgumentParser(description=FIRM+' Offline Team Office')
 parser.add_argument('--lan',action='store_true',help='Allow access over the trusted office LAN. First create the administrator in local mode.')
 parser.add_argument('--port',type=int,default=8765)
 parser.add_argument('--data-dir',type=Path,default=ROOT/'data')
 parser.add_argument('--no-browser',action='store_true')
 args=parser.parse_args()
 database=Database(args.data_dir)
 if args.lan:
  with database.connect() as con:
   if not Service(con,database).rows('Employees'):
    print('First open ABC_Office.exe without LAN mode and create the administrator. Then close it and use Start_Office_Server.bat.'); return 2
 address=('0.0.0.0' if args.lan else '127.0.0.1',args.port)
 try: server=OfficeServer(address,database,args.lan)
 except OSError:
  try:
   from urllib.request import urlopen
   with urlopen('http://127.0.0.1:'+str(args.port)+'/api/health',timeout=2) as response: current=json.load(response)
   if current.get('product')==FIRM:
    print('ABC Office is already running. Close the existing server before switching local/LAN mode.')
    if not args.no_browser: webbrowser.open('http://127.0.0.1:'+str(args.port))
    return 0
  except Exception: pass
  raise RuntimeError('Port '+str(args.port)+' is busy. Start with --port 8766 or close the other application.')
 print('\n'+FIRM+' | Offline Team Office '+VERSION)
 print('Local address: http://127.0.0.1:'+str(args.port))
 if args.lan:
  for host in sorted(server.allowed_hosts-{'localhost','127.0.0.1'}): print('Office network address: http://'+host+':'+str(args.port))
 print('Database: '+str(database.path))
 print('Keep this window open while the office tool is in use. Close it or press Ctrl+C to stop.\n',flush=True)
 if not args.no_browser: threading.Timer(.6,lambda:webbrowser.open('http://127.0.0.1:'+str(args.port))).start()
 try: server.serve_forever(poll_interval=.3)
 except KeyboardInterrupt: pass
 finally: server.server_close()
 return 0

if __name__=='__main__':
 try: sys.exit(main())
 except Exception as e:
  message='ABC Office could not start.\n\n'+str(e)+'\n\nRun Start_Local.bat to view startup details. Keep the complete app and runtime folders beside ABC_Office.exe. If the message concerns file permissions, use a writable location such as Documents.'
  print(message)
  if os.name=='nt':
   import ctypes
   ctypes.windll.user32.MessageBoxW(None,message,'ABC Chartered Accountants',0x10)
  sys.exit(1)
