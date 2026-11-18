"""Resumable batch state, shared by browser and native window."""
import uuid, threading
from datetime import datetime
from config import FIELDS
from core.validators import batch, validate
from core.portal_client import PortalError
from core.captcha import Challenge
from core.parser import parse
class Engine:
    def __init__(self,provider,storage,settings):
        self.provider=provider;self.storage=storage;self.settings=settings
        self.queue=[];self.current=None;self.challenge=None;self.rows=[];self.details=[];self.logs=[];self.done=set();self.total=0;self.completed=0;self.message='Ready';self.level='info';self.year='';self.phase='lookup';self.pending=None;self.return_reports=[];self.payloads={};self.retrying=False;self.task_id=None;self.task_created='';self.cancelled=False;self.stop_requested=threading.Event()
    def record(self,value,result,message):
        self.logs.append(self.storage.log(value,result,message,self.task_id));self.message=message;self.level='ok' if result=='OK' else 'error'
    def start(self,values,year,kind="AUTO"):
        if kind not in ("AUTO","GSTIN","PAN"): raise ValueError("Choose GSTIN, PAN or auto-detect.")
        if self.current or self.queue: raise ValueError('Finish the current batch first.')
        self.task_id=uuid.uuid4().hex;self.task_created=datetime.now().isoformat(timespec='seconds');self.cancelled=False;self.stop_requested.clear()
        self.rows=[];self.details=[];self.logs=[];self.done=set();self.input_kind=kind;self.expanded=set();self.return_reports=[];self.payloads={};self.phase='lookup';self.retrying=False
        if isinstance(values,str): values=batch(values)
        self.queue=list(dict.fromkeys(v.strip().upper() if isinstance(v,str) else "" for v in values));self.total=len(self.queue);self.completed=0;self.year=year;self.advance()
    def advance(self):
        self.current=None;self.challenge=None;self.pending=None;self.phase='lookup'
        if self.stop_requested.is_set():
            self.cancelled=True;self.queue=[];self.message='Task stopped. Partial results are retained.';self.level='retry';self.storage.save_task(self);return
        while self.queue:
            if self.stop_requested.is_set():
                self.cancelled=True;self.queue=[];self.message='Task stopped. Partial results are retained.';self.level='retry';self.storage.save_task(self);return
            value=self.queue.pop(0)
            try:
                v=validate(value)
                if self.input_kind!="AUTO" and v.kind!=self.input_kind and value not in self.expanded:
                    raise ValueError(f"Expected {self.input_kind}, found {v.kind}.")
            except ValueError as exc:
                self.record(value,'INVALID',str(exc));self.completed+=1;continue
            if v.value in self.done:
                self.completed+=1;continue
            try:
                self.storage.reserve(self.settings.daily_cap)
                self.current=v.value;self.challenge=Challenge(self.provider.captcha());self.message=f'{v.kind}: {v.meaning}';self.level='retry';return
            except (PortalError,ValueError) as exc:
                self.record(value,'NETWORK ERROR',str(exc));self.completed+=1;self.current=None
        if self.completed:
            errors=sum(r['State']=='ERROR' for r in self.return_reports)
            self.message=f'Batch complete. {len(self.rows)} taxpayers, {len(self.details)} filing records.'+(f' {errors} filing lookup(s) need attention below.' if errors else '')
            self.level='retry' if errors else ('ok' if self.rows else 'error')
            self.storage.save_task(self)
    def reset_task(self):
        if self.current or self.queue: raise ValueError('Finish or stop the current task first.')
        self.rows=[];self.details=[];self.logs=[];self.done=set();self.return_reports=[];self.payloads={}
        self.total=0;self.completed=0;self.year='';self.phase='lookup';self.pending=None;self.challenge=None;self.retrying=False
        self.task_id=None;self.task_created='';self.cancelled=False;self.stop_requested.clear();self.message='New task ready. Choose files or paste new identifiers.';self.level='info'
    def stop(self):
        self.stop_requested.set();self.advance()
    def refresh(self):
        if self.current:
            self.challenge=Challenge(self.provider.captcha(),self.challenge.attempts if self.challenge else 0)
    def finish_taxpayer(self,value,data,returns,note,error=None):
        row,detail=parse(data,value,self.year,returns)
        index=next((i for i,r in enumerate(self.rows) if r['GST NUMBER']==value),None)
        if index is None: self.rows.append(row)
        else: self.rows[index]=row
        self.details=[d for d in self.details if d['GST NUMBER']!=value]+detail
        state='ERROR' if error else ('AVAILABLE' if detail else 'EMPTY')
        message=str(error) if error else (f'{len(detail)} filing records retrieved.' if detail else f'No published filing records returned for {self.year}.')
        self.return_reports=[r for r in self.return_reports if r['GST NUMBER']!=value]
        self.return_reports.append({'GST NUMBER':value,'Year':self.year,'State':state,'Records':len(detail),'Message':message})
        self.payloads[value]=data;self.done.add(value)
        if error: self.record(value,error.result,'Return filing lookup: '+str(error))
        self.record(value,'OK',note+' '+message)
        if not self.retrying: self.completed+=1
        self.retrying=False;self.advance()
    def wait_for_returns(self,value,data,note):
        self.phase='returns';self.pending=(value,data,note)
        self.challenge=Challenge(self.provider.captcha())
        self.message='Taxpayer details retrieved. Enter this CAPTCHA to retrieve return filings for '+self.year+'.';self.level='retry'
    def retry_returns(self,value):
        if self.current or self.queue: raise ValueError('Finish the active batch before retrying return filings.')
        if value not in self.payloads: raise ValueError('Taxpayer is not in the current results.')
        self.current=value;self.retrying=True
        try: returns=self.provider.returns(value,self.year)
        except PortalError as exc:
            if exc.result=='CAPTCHA FAILED':
                try: self.wait_for_returns(value,self.payloads[value],'Taxpayer retained.');return
                except PortalError as image_error: exc=image_error
            self.finish_taxpayer(value,self.payloads[value],{},'Taxpayer retained.',exc);return
        self.finish_taxpayer(value,self.payloads[value],returns,'Taxpayer retained.')
    def submit(self,answer):
        if not self.current or not self.challenge: raise ValueError('No CAPTCHA is pending.')
        value=self.current
        if self.phase=='returns':
            value,data,note=self.pending
            try: returns=self.provider.returns(value,self.year,answer)
            except PortalError as exc:
                if exc.result=='CAPTCHA FAILED' and not self.challenge.failed():
                    try: self.refresh();self.message='Return filings: '+str(exc);self.level='retry';return
                    except PortalError as image_error: exc=image_error
                self.finish_taxpayer(value,data,{},note,exc);return
            self.finish_taxpayer(value,data,returns,note);return
        try:
            data=self.provider.lookup(value,answer)
            if validate(value).kind=='PAN':
                found=[]
                for item in data.get(FIELDS['pan_list'],[]):
                    g=item.get(FIELDS['GSTIN']) if isinstance(item,dict) else item
                    v=validate(g)
                    if v.kind!='GSTIN' or v.value[2:12]!=value: raise PortalError('NETWORK ERROR','Portal returned a mismatched GSTIN.')
                    if v.value not in self.done and v.value not in self.queue: found.append(v.value)
                if not found: raise PortalError('NOT FOUND','No GSTIN records returned for this PAN.')
                self.expanded.update(found)
                self.queue=found+self.queue;self.total+=len(found)
                self.record(value,'OK',f'PAN returned {len(found)} GSTINs; each requires its own CAPTCHA.')
            else:
                if data.get(FIELDS['GSTIN'])!=value: raise PortalError('NETWORK ERROR','Unexpected taxpayer response: missing or mismatched GSTIN.')
                note='Taxpayer retrieved.'
                try: data.update(self.provider.goods(value))
                except PortalError as exc: note+=' Goods/services unavailable: '+str(exc)
                try: returns=self.provider.returns(value,self.year)
                except PortalError as exc:
                    if exc.result=='CAPTCHA FAILED':
                        try: self.wait_for_returns(value,data,note);return
                        except PortalError as image_error: exc=image_error
                    self.finish_taxpayer(value,data,{},note,exc);return
                self.finish_taxpayer(value,data,returns,note);return
        except PortalError as exc:
            if exc.result=='CAPTCHA FAILED' and not self.challenge.failed():
                try: self.refresh();self.message=str(exc);self.level='retry';return
                except PortalError as refresh_error: exc=refresh_error
            self.record(value,exc.result,str(exc))
        except ValueError as exc: self.record(value,'NETWORK ERROR',str(exc))
        self.completed+=1;self.advance()
