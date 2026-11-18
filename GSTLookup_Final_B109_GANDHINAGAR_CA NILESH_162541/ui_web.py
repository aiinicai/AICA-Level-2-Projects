"""Loopback-only Flask interface, with per-launch anti-CSRF token."""
import io, re, secrets, sys, threading
from pathlib import Path
from flask import Flask, request, render_template, redirect, send_file, abort, jsonify
from openpyxl import load_workbook
from core.validators import batch
from core.exporter import export
from core.portal_client import PortalError
from core.batches import BatchStore, preview
from core.validators import normalize
from core.jobs import JobRunner
from config import CAPTCHA_PATTERN, COLUMNS

def read_upload(file):
    suffix=Path(file.filename).suffix.lower()
    if suffix=='.xlsx':
        wb=load_workbook(file,read_only=True,data_only=True)
        values=[str(c) for row in wb.active.iter_rows(values_only=True) for c in row if c is not None];wb.close()
        return [v for v in values if v.upper() not in ('PAN','GSTIN','GST NUMBER')]
    if suffix in ('.csv','.txt'):
        import csv
        value=file.read().decode('utf-8-sig')
        values=[v for row in csv.reader(io.StringIO(value)) for v in row] if suffix=='.csv' else batch(value)
        return [v for v in values if v.strip().upper() not in ('PAN','GSTIN','GST NUMBER')]
    raise ValueError('Upload .xlsx, .csv or .txt only.')

def create_app(engine,background=False):
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    app=Flask(__name__,template_folder=str(root/'templates'));app.config['MAX_CONTENT_LENGTH']=5*1024*1024
    jobs=JobRunner(engine,background);app.extensions['jobs']=jobs;download_lock=threading.Lock()
    token=secrets.token_urlsafe(32)
    batches=BatchStore(engine.storage.folder)
    state={'validation':[], 'kind':'AUTO', 'year':'2025-26', 'values':'', 'selected':None, 'columns':{},'notice':None}
    def fail(exc):
        state['notice']={'message':str(exc),'level':'error'}
    def collect():
        kind=request.form.get('kind','AUTO')
        if kind not in ('AUTO','GSTIN','PAN'): raise ValueError('Choose GSTIN, PAN or auto-detect.')
        selected=request.form.getlist('batch_id')
        values=batch(request.form.get('values',''))
        columns={}
        for identifier in dict.fromkeys(selected):
            column=int(request.form.get('column_'+identifier,'0'))
            values.extend(batches.values(identifier,column));columns[identifier]=column
        f=request.files.get('file')
        if f and f.filename: values+=read_upload(f)
        if not values: raise ValueError('Select at least one batch file or enter values.')
        if len(values)>50000: raise ValueError('Maximum 50,000 combined input rows per run.')
        state.update(kind=kind,selected=selected,columns=columns,values=request.form.get('values',''),year=request.form.get('year','2025-26'))
        return values,kind
    @app.post('/batches/add')
    def add_batches():
        messages=[]
        for file in request.files.getlist('files'):
            if not file.filename: continue
            try:
                item=batches.add(file.filename,file.read(),request.form.get('header')=='on')
                if state['selected'] is not None: state['selected'].append(item['id'])
                messages.append(item['name']+': added')
            except Exception as exc: messages.append(file.filename+': '+str(exc))
        state['notice']={'message':' | '.join(messages) or 'Choose one or more files to add.','level':'info'}
        state['validation']=[]
        return redirect('/#batch-files')
    @app.post('/batches/<identifier>/delete')
    def delete_batch(identifier):
        try:
            batches.delete(identifier)
            if state['selected'] is not None: state['selected']=[x for x in state['selected'] if x!=identifier]
            state['validation']=[]
            state['notice']={'message':'Uploaded batch removed from this app. Your original file is unchanged.','level':'info'}
        except ValueError as exc: fail(exc)
        return redirect('/#batch-files')
    @app.get('/batches/<identifier>/preview')
    def preview_file(identifier):
        try:
            item=batches.get(identifier);page=max(1,int(request.args.get('page','1')))
            total=max(1,(len(item['rows'])+199)//200);page=min(page,total)
            return render_template('preview.html',item=item,rows=item['rows'][(page-1)*200:page*200],page=page,total=total)
        except ValueError as exc: fail(exc);return redirect('/')
    @app.post('/validate-batch')
    def validate_batch():
        try:
            values,kind=collect();state['validation']=preview(values,kind)
            valid=sum(r['Validation']=='VALID' for r in state['validation']);invalid=len(values)-valid
            state['notice']={'message':f'Offline validation: {valid} valid, {invalid} invalid. Duplicate values run once. Review below, then Run extraction.','level':'ok' if not invalid else 'retry'}
        except (ValueError,KeyError) as exc: fail(exc)
        return redirect('/#validation')

    @app.before_request
    def protect():
        if request.host.split(':')[0] not in ('localhost','127.0.0.1'): abort(403)
        if request.method=='POST' and not secrets.compare_digest(request.form.get('token',''),token): abort(403)
    @app.after_request
    def headers(response):
        response.headers['Cache-Control']='no-store';response.headers['X-Frame-Options']='DENY';response.headers['X-Content-Type-Options']='nosniff';return response
    @app.get('/')
    def index():
        with jobs.lock:view=jobs.view();status=jobs.status()
        if state['notice'] and not status['busy']:view.message=state['notice']['message'];view.level=state['notice']['level']
        columns=['GST NUMBER','Legal Name of Business','TRADE NAME']+[k for k in COLUMNS if k not in ('GST NUMBER','Legal Name of Business','TRADE NAME')]
        if any('Other' in r for r in view.rows):columns.append('Other')
        return render_template('index.html',e=view,token=token,history=engine.storage.history(),files=batches.list(),state=state,job=status,tasks=engine.storage.tasks(),result_columns=columns)
    @app.get('/api/status')
    def status():return jsonify(jobs.status())
    def schedule(label,action):
        jobs.submit(label,action);state['notice']=None
    def challenge_matches():
        challenge=jobs.view().challenge;posted=request.form.get('challenge_token')
        if not challenge:raise ValueError('No CAPTCHA is pending.')
        if (background and not posted) or (posted and posted!=challenge.token):raise ValueError('This CAPTCHA has changed. Use the current image shown below.')

    @app.post('/start')
    def start():
        try:
            year=request.form.get('year','')
            if not re.fullmatch(r'20[0-9]{2}-[0-9]{2}',year) or int(year[-2:])!=(int(year[:4])+1)%100: raise ValueError('Use a financial year such as 2025-26.')
            values,kind=collect()
            state['validation']=preview(values,kind)
            schedule("Preparing the next CAPTCHA…",lambda:engine.start(values,year,kind))
        except Exception as exc: fail(exc)
        return redirect('/#captcha-panel')
    @app.get('/captcha')
    def captcha():
        challenge=jobs.view().challenge
        if not challenge:abort(404)
        return send_file(io.BytesIO(challenge.image),mimetype='image/png')
    @app.post('/submit')
    def submit():
        try:
            challenge_matches();answer=request.form.get('answer','').strip()
            if not re.fullmatch(CAPTCHA_PATTERN,answer):raise ValueError('Enter all 6 digits shown in the CAPTCHA. No request has been sent.')
            schedule('Validating CAPTCHA with the GST portal…',lambda:engine.submit(answer))
        except (ValueError,PortalError) as exc:fail(exc)
        return redirect('/#captcha-panel')
    @app.post('/refresh')
    def refresh():
        try:
            challenge_matches();schedule('Refreshing the portal CAPTCHA…',engine.refresh)
        except (ValueError,PortalError) as exc:fail(exc)
        return redirect('/#captcha-panel')
    @app.post('/returns/retry')
    def retry_returns():
        try:
            value=request.form.get('gstin','');schedule('Retrying return filings…',lambda:engine.retry_returns(value))
        except (ValueError,PortalError) as exc: fail(exc)
        return redirect('/#filings')
    @app.get('/download')
    def download():
        view=jobs.view()
        with download_lock:
            path=engine.storage.folder/'exports'/f'task-{view.task_id}.xlsx' if view.task_id else engine.storage.folder/'GSTLookup.xlsx'
            export(path,view.rows,view.details,view.logs);content=path.read_bytes()
        return send_file(io.BytesIO(content),download_name='GSTLookup.xlsx',as_attachment=True)
    def clear_form():
        state.update(validation=[],values='',selected=[],columns={},notice=None)
    @app.post('/tasks/new')
    def new_task():
        try:
            if jobs.view().current:raise ValueError('Finish or stop the current task before starting a new one.')
            schedule('Starting a clean task…',engine.reset_task);clear_form()
        except ValueError as exc:fail(exc)
        return redirect('/#batch-files')
    @app.post('/tasks/stop')
    def stop_task():
        jobs.request_stop();state['notice']=None
        return redirect('/')
    @app.post('/tasks/<identifier>/delete')
    def delete_task(identifier):
        try:
            if jobs.status()['busy']:raise ValueError('Wait until the current operation finishes before deleting a task.')
            engine.storage.task(identifier)
            def remove():
                with download_lock:engine.storage.delete_task(identifier)
                if engine.task_id==identifier:engine.reset_task()
            schedule('Deleting saved task…',remove);clear_form()
        except ValueError as exc:fail(exc)
        return redirect('/#tasks')
    @app.get('/tasks/<identifier>/download')
    def download_task(identifier):
        try:
            task=engine.storage.task(identifier)
            with download_lock:
                path=export(engine.storage.folder/'exports'/f'task-{identifier}.xlsx',task['rows'],task['details'],task['logs']);content=path.read_bytes()
            return send_file(io.BytesIO(content),download_name=f'GSTLookup-{identifier[:8]}.xlsx',as_attachment=True)
        except ValueError as exc:fail(exc);return redirect('/#tasks')
    return app
