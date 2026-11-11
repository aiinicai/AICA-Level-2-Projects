import os, io, re, hashlib, uuid
import collections
import math
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from supabase import create_client
load_dotenv()
URL=os.getenv('SUPABASE_URL',''); KEY=os.getenv('SUPABASE_SERVICE_ROLE_KEY','')
client=create_client(URL,KEY) if URL and KEY else None
app=FastAPI(title='SmartHire AI API',version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
SKILLS=['python','sql','machine learning','deep learning','nlp','data analysis','excel','power bi','tableau','java','javascript','react','fastapi','django','flask','aws','azure','docker','kubernetes','postgresql','mongodb','git','communication','leadership','project management','tensorflow','pytorch','pandas','numpy','scikit-learn','html','css','typescript','api','statistics','gst','income tax','tds','tcs','audit','statutory audit','internal audit','tax audit','financial reporting','ind as','indian gaap','budgeting','forecasting','variance analysis','tally','tally prime','sap fico','zoho books','accounting','financial statements','reconciliation','cash flow','working capital','treasury','compliance','power bi']
def tfidf_similarity(left: str, right: str) -> float:
    """Two-document TF-IDF cosine similarity without NumPy or scikit-learn."""
    stop = set('a an and are as at be by for from has have in is it of on or that the to was were with you your our we will this those their they job role experience required preferred'.split())
    def tokens(text):
        return [word for word in re.findall(r"[a-z][a-z0-9+#.-]*", text.lower()) if word not in stop and len(word)>1]
    docs = [collections.Counter(tokens(left)), collections.Counter(tokens(right))]
    if not docs[0] or not docs[1]:
        return 0.0
    vocab = set(docs[0]) | set(docs[1])
    weights = []
    for counts in docs:
        weights.append({word: (1+math.log(counts[word])) * (1+math.log(3/(1+sum(word in d for d in docs)))) for word in counts})
    dot = sum(weights[0].get(word,0)*weights[1].get(word,0) for word in vocab)
    norm = math.sqrt(sum(v*v for v in weights[0].values())*sum(v*v for v in weights[1].values()))
    return max(0.0,min(1.0,dot/norm)) if norm else 0.0

def skillset(s): return sorted(x for x in SKILLS if re.search(r'(?<!\w)'+re.escape(x)+r'(?!\w)',s.lower()))
def parse_file(name,content):
    if len(content)>10*1024*1024: raise HTTPException(400,'Maximum file size is 10 MB')
    if name.lower().endswith('.pdf'):
        import fitz
        try:
            with fitz.open(stream=content,filetype='pdf') as d:
                if len(d)>30: raise HTTPException(400,'Maximum 30 PDF pages')
                return '\n'.join(p.get_text() for p in d)[:100000]
        except HTTPException: raise
        except Exception: raise HTTPException(400,'Invalid PDF file')
    if name.lower().endswith('.docx'):
        from docx import Document
        try:
            d=Document(io.BytesIO(content)); return '\n'.join([p.text for p in d.paragraphs]+[c.text for t in d.tables for r in t.rows for c in r.cells])[:100000]
        except Exception: raise HTTPException(400,'Invalid DOCX file')
    raise HTTPException(400,'Only PDF and DOCX allowed')
def require_client():
    if not client: raise HTTPException(503,'Supabase is not configured. See README.')
    return client
async def identity(authorization:str=Header(default=''),db=Depends(require_client)):
    if not authorization.startswith('Bearer '): raise HTTPException(401,'Login required')
    try:
        user=db.auth.get_user(authorization[7:]).user
        if not user: raise ValueError('Invalid user')
        rows=db.table('profiles').select('user_id,organization_id,role,full_name').eq('user_id',str(user.id)).execute().data
        if not rows: raise HTTPException(403,'No assigned organization. Ask admin to provision account.')
        return rows[0]
    except HTTPException: raise
    except Exception: raise HTTPException(401,'Invalid or expired session')
def role(user,allowed):
    if user['role'] not in allowed: raise HTTPException(403,'Insufficient permission')
def get_job(db,job_id,user):
    r=db.table('jobs').select('*').eq('id',job_id).eq('organization_id',user['organization_id']).execute().data
    if not r: raise HTTPException(404,'Job not found')
    return r[0]
class JobIn(BaseModel):
    title:str=Field(min_length=2,max_length=150)
    description:str=Field(min_length=20,max_length=20000)
    status:str='open'
class ReviewIn(BaseModel):
    decision:str
    notes:str=''
class InviteIn(BaseModel):
    email:str
    role:str='recruiter'
@app.get('/api/health')
def health(): return {'ok':True,'configured':bool(client)}
@app.get('/api/me')
def me(user=Depends(identity)): return user
@app.get('/api/jobs')
def jobs(user=Depends(identity),db=Depends(require_client)):
    return db.table('jobs').select('*').eq('organization_id',user['organization_id']).order('created_at',desc=True).execute().data
@app.post('/api/jobs')
def create_job(payload:JobIn,user=Depends(identity),db=Depends(require_client)):
    role(user,['admin','recruiter'])
    if payload.status not in ('draft','open','closed'): raise HTTPException(400,'Invalid status')
    data={'organization_id':user['organization_id'],'title':payload.title,'description':payload.description,'status':payload.status,'created_by':user['user_id']}
    return db.table('jobs').insert(data).execute().data[0]
@app.get('/api/jobs/{job_id}/applications')
def applications(job_id:str,user=Depends(identity),db=Depends(require_client)):
    get_job(db,job_id,user)
    return db.table('applications').select('id,created_at,filename,match_score,matched_skills,missing_skills,explanation,review_status').eq('job_id',job_id).eq('organization_id',user['organization_id']).order('match_score',desc=True).execute().data
@app.post('/api/jobs/{job_id}/resumes')
async def upload_resumes(job_id:str,files:list[UploadFile]=File(...),user=Depends(identity),db=Depends(require_client)):
    role(user,['admin','recruiter']); job=get_job(db,job_id,user)
    if len(files)>20: raise HTTPException(400,'Upload up to 20 files per batch')
    results=[]
    for f in files:
        data=await f.read(); text=parse_file(f.filename or '',data)
        if not text.strip(): results.append({'filename':f.filename,'error':'No extractable text; scanned PDF requires OCR'});continue
        js=skillset(job['description']); rs=skillset(text); matched=sorted(set(js)&set(rs)); missing=sorted(set(js)-set(rs))
        sim=tfidf_similarity(job['description'],text)
        coverage=len(matched)/len(js) if js else 0
        score=round(100*(.7*coverage+.3*sim)) if js else round(100*sim)
        app_id=str(uuid.uuid4())
        candidate_id=str(uuid.uuid4())
        resume_id=str(uuid.uuid4())
        filename=f.filename or 'resume'
        safe_name=re.sub(r'[^A-Za-z0-9._-]','_',filename)[:100]
        path=f"{user['organization_id']}/{job_id}/{app_id}/{uuid.uuid4().hex}_{safe_name}"
        uploaded=False
        created_candidate=False
        created_resume=False
        try:
            # Database schema requires candidates -> resumes -> applications.
            # Derive a display name from the filename; recruiters should verify it.
            display_name=re.sub(r'[_-]+',' ',filename.rsplit('.',1)[0]).strip()[:150] or 'Unknown candidate'
            db.table('candidates').insert({
                'id':candidate_id,
                'organization_id':user['organization_id'],
                'full_name':display_name,
            }).execute()
            created_candidate=True
            content_type=('application/pdf' if filename.lower().endswith('.pdf')
                          else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            db.storage.from_('resumes').upload(path,data,{'content-type':content_type})
            uploaded=True
            db.table('resumes').insert({
                'id':resume_id,
                'organization_id':user['organization_id'],
                'candidate_id':candidate_id,
                'storage_path':path,
                'file_hash':hashlib.sha256(data).hexdigest(),
                'parsed_text':text,
                'parsing_status':'complete',
            }).execute()
            created_resume=True
            row={
                'id':app_id,
                'organization_id':user['organization_id'],
                'job_id':job_id,
                'candidate_id':candidate_id,
                'resume_id':resume_id,
                'filename':filename,
                'match_score':score,
                'matched_skills':matched,
                'missing_skills':missing,
                'explanation':f"Matched {len(matched)} of {len(js)} detected job skills; TF-IDF similarity {sim:.2f}. Review the source resume before deciding.",
                'review_status':'pending',
            }
            results.append(db.table('applications').insert(row).execute().data[0])
        except Exception as exc:
            # Best-effort cleanup; never expose private resume text or credentials in errors.
            import logging
            logging.exception('Failed to save resume application for %s',filename)
            if created_resume:
                try: db.table('resumes').delete().eq('id',resume_id).eq('organization_id',user['organization_id']).execute()
                except Exception: logging.exception('Could not clean up resume record')
            if uploaded:
                try: db.storage.from_('resumes').remove([path])
                except Exception: logging.exception('Could not clean up uploaded file')
            if created_candidate:
                try: db.table('candidates').delete().eq('id',candidate_id).eq('organization_id',user['organization_id']).execute()
                except Exception: logging.exception('Could not clean up candidate record')
            results.append({'filename':filename,'error':'Could not save application; see backend terminal for details'})
    return results
@app.post('/api/applications/{app_id}/review')
def review(app_id:str,payload:ReviewIn,user=Depends(identity),db=Depends(require_client)):
    role(user,['admin','recruiter'])
    if payload.decision not in ('pending','reviewed','interview','hold'): raise HTTPException(400,'Invalid decision')
    row=db.table('applications').select('id').eq('id',app_id).eq('organization_id',user['organization_id']).execute().data
    if not row: raise HTTPException(404,'Application not found')
    updated=db.table('applications').update({'review_status':payload.decision}).eq('id',app_id).eq('organization_id',user['organization_id']).execute().data
    if not updated: raise HTTPException(500,'Review status was not saved')
    return {'ok':True}

class InterviewIn(BaseModel):
    application_id: str
    starts_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=240)
    mode: str = 'online'
    interviewer: str = Field(default='', max_length=150)
    meeting_details: str = Field(default='', max_length=1000)
    notes: str = Field(default='', max_length=3000)

class InterviewUpdate(BaseModel):
    starts_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=240)
    mode: str | None = None
    interviewer: str | None = Field(default=None, max_length=150)
    meeting_details: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=3000)
    status: str | None = None

def check_interview_time(starts_at):
    if starts_at.tzinfo is None or starts_at.utcoffset() is None:
        raise HTTPException(400, 'Interview time must include a timezone offset')
    if starts_at.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(400, 'Choose a future interview time')

def check_interview_mode(mode):
    if mode not in ('online', 'in_person', 'phone'):
        raise HTTPException(400, 'Invalid interview mode')

@app.get('/api/interviews')
def list_interviews(user=Depends(identity), db=Depends(require_client)):
    return db.table('interviews').select('*').eq('organization_id', user['organization_id']).order('starts_at').execute().data

@app.post('/api/interviews')
def create_interview(payload: InterviewIn, user=Depends(identity), db=Depends(require_client)):
    role(user, ['admin', 'recruiter'])
    check_interview_time(payload.starts_at)
    check_interview_mode(payload.mode)
    application = db.table('applications').select('id,job_id').eq('id', payload.application_id).eq('organization_id', user['organization_id']).execute().data
    if not application: raise HTTPException(404, 'Application not found')
    row = {'organization_id': user['organization_id'], 'application_id': payload.application_id,
           'job_id': application[0]['job_id'], 'starts_at': payload.starts_at.isoformat(),
           'duration_minutes': payload.duration_minutes, 'mode': payload.mode,
           'interviewer': payload.interviewer, 'meeting_details': payload.meeting_details,
           'notes': payload.notes, 'created_by': user['user_id'], 'status': 'scheduled'}
    result = db.table('interviews').insert(row).execute().data[0]
    db.table('applications').update({'review_status': 'interview'}).eq('id', payload.application_id).eq('organization_id', user['organization_id']).execute()
    return result

@app.patch('/api/interviews/{interview_id}')
def update_interview(interview_id: str, payload: InterviewUpdate, user=Depends(identity), db=Depends(require_client)):
    role(user, ['admin', 'recruiter'])
    current = db.table('interviews').select('id').eq('id', interview_id).eq('organization_id', user['organization_id']).execute().data
    if not current: raise HTTPException(404, 'Interview not found')
    changes = payload.model_dump(exclude_unset=True)
    if 'starts_at' in changes:
        if changes['starts_at'] is None: raise HTTPException(400, 'Date is required')
        check_interview_time(changes['starts_at'])
        changes['starts_at'] = changes['starts_at'].isoformat()
    if 'mode' in changes: check_interview_mode(changes['mode'])
    if 'status' in changes and changes['status'] not in ('scheduled', 'completed', 'cancelled'):
        raise HTTPException(400, 'Invalid interview status')
    if not changes: raise HTTPException(400, 'No changes provided')
    return db.table('interviews').update(changes).eq('id', interview_id).eq('organization_id', user['organization_id']).execute().data[0]

@app.get('/api/dashboard')
def dashboard(user=Depends(identity),db=Depends(require_client)):
    jobs=db.table('jobs').select('id,status').eq('organization_id',user['organization_id']).execute().data
    apps=db.table('applications').select('id,match_score,review_status').eq('organization_id',user['organization_id']).execute().data
    return {'jobs':len(jobs),'open_jobs':sum(j['status']=='open' for j in jobs),'applications':len(apps),'reviewed':sum(a['review_status']!='pending' for a in apps),'average_match':round(sum(float(a['match_score'] or 0) for a in apps)/len(apps),1) if apps else 0}
@app.post('/api/admin/invite')
def invite(payload:InviteIn,user=Depends(identity),db=Depends(require_client)):
    role(user,['admin'])
    if payload.role not in ('admin','recruiter','viewer'): raise HTTPException(400,'Invalid role')
    if '@' not in payload.email: raise HTTPException(400,'Invalid email')
    try:
        invited=db.auth.admin.invite_user_by_email(payload.email)
        if not invited.user: raise ValueError('Invite did not return user')
        db.table('profiles').upsert({'user_id':str(invited.user.id),'organization_id':user['organization_id'],'role':payload.role,'full_name':payload.email.split('@')[0]}).execute()
        return {'ok':True,'email':payload.email}
    except Exception: raise HTTPException(400,'Could not invite user; check Auth settings or existing account')
