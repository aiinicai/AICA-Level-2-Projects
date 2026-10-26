import os,re,uuid,hashlib
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import create_engine,Column,Integer,String,ForeignKey,DateTime,UniqueConstraint,Text,event,update,text
from sqlalchemy.orm import declarative_base,sessionmaker
from sqlalchemy.pool import NullPool
from argon2 import PasswordHasher
ROOT=Path(__file__).resolve().parent
ROOT.joinpath('storage').mkdir(exist_ok=True)
engine=create_engine(os.getenv('AUDITFILE_DATABASE_URL',f'sqlite:///{ROOT / "auditfile.db"}'),connect_args={'check_same_thread':False} if not os.getenv('AUDITFILE_DATABASE_URL') else {},poolclass=NullPool)
@event.listens_for(engine,'connect')
def fk(dbapi,connection):
    if engine.dialect.name=='sqlite': dbapi.execute('PRAGMA foreign_keys=ON')
Session=sessionmaker(bind=engine)
Base=declarative_base()
def now():return datetime.now(timezone.utc)
class User(Base):
 __tablename__='users';id=Column(Integer,primary_key=True);name=Column(String(150));initials=Column(String(3));username=Column(String(80),unique=True);password=Column(String(300));admin=Column(Integer,default=0);active=Column(Integer,default=1);designation=Column(String(30),default="Staff")
class Client(Base):
 __tablename__='clients';id=Column(Integer,primary_key=True);name=Column(String(200));grp=Column(String(100));pan=Column(String(10));gstin=Column(String(15));email=Column(String(150));mobile=Column(String(20));active=Column(Integer,default=1)
class Engagement(Base):
 __tablename__='engagements';id=Column(Integer,primary_key=True);client_id=Column(Integer,ForeignKey('clients.id'));kind=Column(String(100));fy=Column(String(30));start=Column(String(20));end=Column(String(20));status=Column(String(30),default='Open');levels=Column(Integer,default=1)
class Assignment(Base):
 __tablename__='assignments';id=Column(Integer,primary_key=True);engagement_id=Column(Integer,ForeignKey('engagements.id'));user_id=Column(Integer,ForeignKey('users.id'));role=Column(String(20));level=Column(Integer,default=0);__table_args__=(UniqueConstraint('engagement_id','user_id'),)
class Folder(Base):
 __tablename__='folders';id=Column(Integer,primary_key=True);engagement_id=Column(Integer,ForeignKey('engagements.id'));parent_id=Column(Integer,ForeignKey('folders.id'));idx=Column(String(60));title=Column(String(200));__table_args__=(UniqueConstraint('engagement_id','idx'),)
class WP(Base):
 __tablename__='wps';id=Column(Integer,primary_key=True);engagement_id=Column(Integer,ForeignKey('engagements.id'));folder_id=Column(Integer,ForeignKey('folders.id'));idx=Column(String(80));title=Column(String(200));preparer_id=Column(Integer,ForeignKey('users.id'));status=Column(String(40),default='Draft');level=Column(Integer,default=1);version=Column(Integer,default=1);__table_args__=(UniqueConstraint('engagement_id','idx'),)
class Version(Base):
 __tablename__='versions';id=Column(Integer,primary_key=True);wp_id=Column(Integer,ForeignKey('wps.id'));number=Column(Integer);filename=Column(String(255));path=Column(String(300));checksum=Column(String(64));reason=Column(String(500));user_id=Column(Integer,ForeignKey('users.id'));at=Column(DateTime(timezone=True),default=now);__table_args__=(UniqueConstraint('wp_id','number'),)
class Note(Base):
 __tablename__='notes';id=Column(Integer,primary_key=True);wp_id=Column(Integer,ForeignKey('wps.id'));version=Column(Integer);reviewer_id=Column(Integer,ForeignKey('users.id'));level=Column(Integer);body=Column(Text);status=Column(String(30),default='Open');at=Column(DateTime(timezone=True),default=now)
class Response(Base):
 __tablename__='responses';id=Column(Integer,primary_key=True);note_id=Column(Integer,ForeignKey('notes.id'));user_id=Column(Integer,ForeignKey('users.id'));body=Column(Text);at=Column(DateTime(timezone=True),default=now)
class Signoff(Base):
 __tablename__='signoffs';id=Column(Integer,primary_key=True);wp_id=Column(Integer,ForeignKey('wps.id'));user_id=Column(Integer,ForeignKey('users.id'));version=Column(Integer);level=Column(Integer);action=Column(String(30));at=Column(DateTime(timezone=True),default=now)
class Log(Base):
 __tablename__='audit_log';id=Column(Integer,primary_key=True);user_id=Column(Integer);action=Column(String(80));detail=Column(Text);at=Column(DateTime(timezone=True),default=now)
ph=PasswordHasher()
def init():
 Base.metadata.create_all(engine)
 # Safe, additive migration for existing SQLite databases.
 if engine.dialect.name=='sqlite':
  with engine.begin() as conn:
   columns=[r[1] for r in conn.exec_driver_sql('PRAGMA table_info(users)').fetchall()]
   if 'designation' not in columns:conn.exec_driver_sql("ALTER TABLE users ADD COLUMN designation VARCHAR(30) DEFAULT 'Staff'")
def log(s,u,a,d):s.add(Log(user_id=u,action=a,detail=str(d)))
def permission(s,user,eid,role=None,level=None):
 u=s.get(User,user);e=s.get(Engagement,eid)
 if not u or not u.active or not e:raise PermissionError('Access denied')
 if u.admin:
  if role in ("Preparer","Reviewer"):raise PermissionError("Administrator cannot prepare or review working papers")
  return True
 a=s.query(Assignment).filter_by(user_id=user,engagement_id=eid).first()
 if not a or (role and a.role!=role) or (level and a.level!=level):raise PermissionError('Access denied')
 return True
PARTNER_DESIGNATIONS=('Junior Partner','Senior Partner')
def is_assigned_partner(s,user,eid):
 u=s.get(User,user)
 return bool(u and u.active and not u.admin and u.designation in PARTNER_DESIGNATIONS and s.query(Assignment).filter_by(user_id=user,engagement_id=eid).first())
def can_manage_engagement(s,user,eid):
 u=s.get(User,user)
 return bool(u and u.active and (u.admin or is_assigned_partner(s,user,eid)))
def assign_employee(s,actor,eid,employee_id,role,level):
 if not can_manage_engagement(s,actor,eid):raise PermissionError('Not authorised to assign staff on this engagement')
 editable(s,eid)
 employee=s.get(User,employee_id)
 if not employee or not employee.active or employee.admin:raise ValueError('Select an active non-admin employee')
 if role not in ('Preparer','Reviewer'):raise ValueError('Invalid assignment role')
 eng=s.get(Engagement,eid)
 if role=='Reviewer' and not 1<=int(level)<=eng.levels:raise ValueError('Invalid review level')
 if s.query(Assignment).filter_by(engagement_id=eid,user_id=employee_id).first():raise ValueError('Employee already assigned to this engagement')
 s.add(Assignment(engagement_id=eid,user_id=employee_id,role=role,level=int(level) if role=='Reviewer' else 0))
 log(s,actor,'Assign',f'Engagement {eid}; employee {employee_id}; role {role}; level {level if role=="Reviewer" else 0}')
def create_engagement_with_partner(s,actor,client_id,kind,fy,levels,start,end,partner_id):
 """Create engagement and partner assignment atomically in one transaction."""
 administrator=s.get(User,actor)
 if not administrator or not administrator.active or not administrator.admin:
  raise PermissionError('Only an active system administrator can create engagements')
 client=s.get(Client,client_id)
 if not client:raise ValueError('Select a valid client')
 partner=s.get(User,partner_id)
 if not partner or not partner.active or partner.admin or partner.designation not in PARTNER_DESIGNATIONS:
  raise ValueError('Select an active Senior Partner or Junior Partner')
 if not 1<=int(levels)<=5:raise ValueError('Review levels must be between 1 and 5')
 engagement=Engagement(client_id=client_id,kind=kind,fy=fy,levels=int(levels),start=str(start),end=str(end))
 s.add(engagement)
 s.flush()
 # Existing assignment model permits one role per employee per engagement.
 # A partner is assigned at the final review level; additional reviewers may
 # be assigned at earlier levels through the existing assignment form.
 s.add(Assignment(engagement_id=engagement.id,user_id=partner_id,role='Reviewer',level=int(levels)))
 log(s,actor,'Create engagement',f'Engagement {engagement.id}; {kind}; {fy}; assigned partner {partner_id}; final review level {levels}')
 return engagement

def finalise_engagement(s,actor,eid):
 if not can_manage_engagement(s,actor,eid):raise PermissionError('Only admin or an assigned partner may finalise')
 s.expire_all()
 e=s.get(Engagement,eid)
 if not e or e.status!='Open':raise ValueError('Engagement is not Open')
 wps=s.query(WP).filter_by(engagement_id=eid).all()
 if not wps:raise ValueError('Cannot finalise an engagement without working papers')
 if any(w.status!='Closed' for w in wps):raise ValueError('Unclosed working papers exist')
 changed=s.execute(update(Engagement).where(Engagement.id==eid,Engagement.status=='Open').values(status='Finalised'))
 if changed.rowcount!=1:raise RuntimeError('Finalisation status update failed')
 log(s,actor,'Finalise',eid)
 s.flush();s.expire_all()
 if s.get(Engagement,eid).status!='Finalised':raise RuntimeError('Finalisation verification failed')
def editable(s,eid):
 if s.get(Engagement,eid).status!='Open':raise ValueError('Engagement is finalised')
def manage_folder(s,actor,eid,folder_id,action,title=None,parent_id=None):
 """Safely rename, relocate or delete an engagement folder."""
 permission(s,actor,eid,'Preparer')
 editable(s,eid)
 folder=s.get(Folder,int(folder_id))
 if not folder or folder.engagement_id!=eid:raise ValueError('Folder not found in this engagement')
 if action=='rename':
  new_title=(title or '').strip()
  if not new_title or len(new_title)>200:raise ValueError('Folder name must be between 1 and 200 characters')
  old=folder.title
  folder.title=new_title
  log(s,actor,'Rename folder',f'Engagement {eid}; folder {folder.id}; {old!r} -> {new_title!r}')
 elif action=='move':
  if parent_id is not None:
   parent=s.get(Folder,int(parent_id))
   if not parent or parent.engagement_id!=eid:raise ValueError('Destination folder is invalid')
   cursor=parent
   visited=set()
   while cursor is not None:
    if cursor.id==folder.id:raise ValueError('Cannot move a folder inside itself or one of its descendants')
    if cursor.id in visited:raise ValueError('Invalid existing folder hierarchy')
    visited.add(cursor.id)
    cursor=s.get(Folder,cursor.parent_id) if cursor.parent_id else None
  if folder.parent_id==parent_id:raise ValueError('Folder is already in this location')
  old=folder.parent_id
  folder.parent_id=parent_id
  log(s,actor,'Move folder',f'Engagement {eid}; folder {folder.id}; parent {old} -> {parent_id}')
 elif action=='delete':
  if s.query(Folder).filter_by(parent_id=folder.id).first():
   raise ValueError('Folder has subfolders. Move or delete its subfolders first')
  if s.query(WP).filter_by(folder_id=folder.id).first():
   raise ValueError('Folder contains working papers. Move the papers before deleting the folder')
  log(s,actor,'Delete empty folder',f'Engagement {eid}; folder {folder.id}; index {folder.idx}; title {folder.title}')
  s.delete(folder)
 else:raise ValueError('Unknown folder action')
# Index allocation is shared by folders and WPs, without changing database IDs.
# Existing indexes are retained; gaps are not recycled.
def next_audit_index(s,eid,parent_id=None,reserved=()):
 if parent_id is None:
  parent_prefix=''
 else:
  parent=s.get(Folder,parent_id)
  if not parent or parent.engagement_id!=eid:raise ValueError('Invalid parent folder')
  parent_prefix=parent.idx+'.'
  if parent.idx.count('.')>=7:raise ValueError('Maximum 8 index levels')
 all_indexes=[r[0] for r in s.query(Folder.idx).filter_by(engagement_id=eid)] + [r[0] for r in s.query(WP.idx).filter_by(engagement_id=eid)] + list(reserved)
 if parent_id is None:
  used={x for x in all_indexes if re.fullmatch(r'[A-Z]+',x or '')}
  number=1
  while True:
   n=number;letters=''
   while n:n,r=divmod(n-1,26);letters=chr(65+r)+letters
   if letters not in used:return letters
   number+=1
 used=[]
 for x in all_indexes:
  if not x.startswith(parent_prefix):continue
  rest=x[len(parent_prefix):]
  if re.fullmatch(r'\d+',rest):used.append(int(rest))
 next_num=max(used,default=0)+1
 candidate=f'{parent_prefix}{next_num:02d}'
 if len(candidate)>60:raise ValueError('Index too long')
 return candidate

def create_indexed_folder(s,actor,eid,title,parent_id=None,reserved=()):
 permission(s,actor,eid,'Preparer');editable(s,eid)
 title=title.strip()
 if not title or len(title)>200:raise ValueError('Folder title required (max 200 characters)')
 idx=next_audit_index(s,eid,parent_id,reserved)
 folder=Folder(engagement_id=eid,parent_id=parent_id,idx=idx,title=title)
 s.add(folder);s.flush()
 log(s,actor,'Create folder',f'{eid}: {idx} {title}')
 return folder

def create_indexed_wp(s,actor,eid,folder_id,filename,data,title=None,reserved=()):
 permission(s,actor,eid,'Preparer');editable(s,eid)
 folder=s.get(Folder,folder_id)
 if not folder or folder.engagement_id!=eid:raise ValueError('Choose a valid destination folder')
 title=(title or Path(filename).stem).strip()
 if not title or len(title)>200:raise ValueError('WP title required (max 200 characters)')
 idx=next_audit_index(s,eid,folder_id,reserved)
 wp=WP(engagement_id=eid,folder_id=folder_id,idx=idx,title=title,preparer_id=actor,version=0)
 s.add(wp);s.flush()
 save(s,wp,filename,data,actor,'Initial upload')
 return wp

def save(s,wp,filename,data,user,reason):
 permission(s,user,wp.engagement_id,'Preparer');editable(s,wp.engagement_id)
 if wp.preparer_id!=user or wp.status not in ('Draft','Returned','Reopened'):raise PermissionError('Document not editable')
 ext=Path(filename).suffix.lower()
 if ext not in ('.xls','.xlsx','.doc','.docx','.pdf','.jpg','.jpeg','.png','.ppt','.pptx'):raise ValueError('Unsupported file type')
 if not data or len(data)>50*1024*1024:raise ValueError('File must be 1 byte to 50 MB')
 number=(s.query(__import__("sqlalchemy").func.max(Version.number)).filter_by(wp_id=wp.id).scalar() or 0)+1
 dest=ROOT/'storage'/(uuid.uuid4().hex+ext);dest.write_bytes(data)
 s.add(Version(wp_id=wp.id,number=number,filename=Path(filename).name,path=dest.name,checksum=hashlib.sha256(data).hexdigest(),reason=reason,user_id=user));wp.version=number;wp.status='Draft' if wp.status=='Reopened' else wp.status
 log(s,user,'Upload',f'WP {wp.id} v{number}')
def submit(s,wp,user):
 permission(s,user,wp.engagement_id,'Preparer');editable(s,wp.engagement_id)
 if wp.preparer_id!=user or wp.status not in ('Draft','Returned'):raise PermissionError('Cannot submit')
 latest=s.query(__import__('sqlalchemy').func.max(Version.number)).filter_by(wp_id=wp.id).scalar()
 if latest is None:raise ValueError('Upload a file first')
 wp.version=latest
 if wp.status=='Returned' and s.query(Note).filter_by(wp_id=wp.id,status='Open').count():raise ValueError('Respond to review notes first')
 wp.status='Submitted';s.add(Signoff(wp_id=wp.id,user_id=user,version=wp.version,level=0,action='Submit'));log(s,user,'Submit',wp.id)
def review(s,wp,user,action,observation=''):
 # Reload and lock the workflow transition with a conditional SQL update.
 s.expire_all()
 wp=s.get(WP,wp.id)
 permission(s,user,wp.engagement_id,'Reviewer',wp.level);editable(s,wp.engagement_id)
 if wp.preparer_id==user:raise PermissionError('Self-review prohibited')
 if wp.status!='Submitted':raise ValueError('Not awaiting review')
 latest=s.query(__import__('sqlalchemy').func.max(Version.number)).filter_by(wp_id=wp.id).scalar()
 if latest!=wp.version:raise ValueError('Version mismatch: resubmit latest version')
 if not s.query(Signoff).filter_by(wp_id=wp.id,version=wp.version,action='Submit').first():raise ValueError('No preparer signoff for this version')
 if action=='Return':
  if not observation.strip():raise ValueError('Observation required')
  if s.query(Note).filter_by(wp_id=wp.id,version=wp.version,reviewer_id=user,level=wp.level,body=observation).first():raise ValueError('Duplicate observation')
  next_level=wp.level;next_status='Returned'
 elif action=='Approve':
  if s.query(Note).filter_by(wp_id=wp.id).filter(Note.status!='Closed').count():raise ValueError('Unclosed review notes remain')
  if s.query(Signoff).filter_by(wp_id=wp.id,version=wp.version,level=wp.level,action='Approve').first():raise ValueError('This review level has already been approved. Contact administrator to repair existing records.')
  final=wp.level>=s.get(Engagement,wp.engagement_id).levels
  next_level=wp.level if final else wp.level+1
  next_status='Closed' if final else 'Submitted'
 else:raise ValueError('Invalid action')
 old_level=wp.level;old_version=wp.version
 result=s.execute(update(WP).where(WP.id==wp.id,WP.status=='Submitted',WP.level==old_level,WP.version==old_version).values(level=next_level,status=next_status))
 if result.rowcount!=1:raise ValueError('Working paper changed during approval. Refresh and retry.')
 if action=='Return':s.add(Note(wp_id=wp.id,version=old_version,reviewer_id=user,level=old_level,body=observation))
 else:s.add(Signoff(wp_id=wp.id,user_id=user,version=old_version,level=old_level,action='Approve'))
 log(s,user,action,wp.id)
 s.flush();s.expire_all()
 check=s.get(WP,wp.id)
 if check.level!=next_level or check.status!=next_status:raise RuntimeError('Review transition did not persist; transaction aborted')
