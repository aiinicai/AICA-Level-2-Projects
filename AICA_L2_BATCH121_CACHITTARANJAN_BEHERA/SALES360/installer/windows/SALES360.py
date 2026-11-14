"""Offline SALES360 launcher. Uses bundled Python/.NET/PostgreSQL; no pip or API keys at runtime."""
from __future__ import annotations
import argparse,base64,ctypes,hashlib,json,os,secrets,socket,subprocess,sys,time,uuid,webbrowser,tempfile,zipfile,io
from pathlib import Path
from urllib.request import build_opener,ProxyHandler

VERSION='0.9.1'
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
ROOT=Path(__file__).resolve().parent
HIDDEN=0x08000000 if os.name=='nt' else 0
if os.name=='nt':
    ctypes.windll.kernel32.CreateMutexW.restype=ctypes.c_void_p
    ctypes.windll.kernel32.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
    ctypes.windll.kernel32.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    ctypes.windll.kernel32.ReleaseMutex.argtypes=[ctypes.c_void_p]
    ctypes.windll.kernel32.CloseHandle.argtypes=[ctypes.c_void_p]

class Blob(ctypes.Structure):
    _fields_=[('size',ctypes.c_ulong),('data',ctypes.POINTER(ctypes.c_ubyte))]
def protect(data:bytes,decrypt=False)->bytes:
    if os.name!='nt':raise RuntimeError('This package requires Windows x64.')
    buffer=ctypes.create_string_buffer(data);source=Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    function=ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not function(ctypes.byref(source),None,None,None,None,0,ctypes.byref(target)):raise ctypes.WinError()
    try:return ctypes.string_at(target.data,target.size)
    finally:ctypes.windll.kernel32.LocalFree(target.data)

def free_port(preferred:int)->int:
    for port in range(preferred,preferred+30):
        with socket.socket() as s:
            try:s.bind(('127.0.0.1',port));return port
            except OSError:continue
    raise RuntimeError('No free local port. Close another SALES360 instance or choose another port.')

def health(url):
    try:
        with build_opener(ProxyHandler({})).open(url+'/api/health',timeout=1) as response:return json.load(response)
    except Exception:return None

class Installation:
    def __init__(self,args):
        self.args=args;self.data=Path(args.data_dir or os.environ.get('SALES360_DATA_DIR') or Path(os.environ.get('LOCALAPPDATA',str(ROOT)))/'SALES360'/'data').resolve()
        if self.data==Path(self.data.anchor):raise RuntimeError('Data directory cannot be a drive root.')
        self.python=ROOT/'runtime/python/python.exe';self.pg=ROOT/'runtime/postgres/bin';self.host=ROOT/'host/Sales360.Api.exe';self.process=None;self.started_db=False
    def run(self,args,*,env=None,input=None,timeout=60,check=True):
        # A database daemon can inherit pipe handles. File-backed output avoids waiting for its EOF.
        with tempfile.TemporaryFile(mode='w+',encoding='utf-8',errors='replace') as output:
            result=subprocess.run([str(x) for x in args],input=input,text=True,stdout=output,stderr=output,creationflags=HIDDEN,env=env,timeout=timeout)
            output.seek(0);result.stdout=output.read()
        if check and result.returncode:raise RuntimeError(f'{Path(str(args[0])).name} failed (exit {result.returncode}). Check the protected local logs; no credentials are printed.')
        return result
    def check(self):
        missing=[str(p.relative_to(ROOT)) for p in [self.python,self.pg/'initdb.exe',self.pg/'pg_ctl.exe',self.host,ROOT/'apps/web/dist/index.html'] if not p.exists()]
        if missing:raise RuntimeError('Missing package components: '+', '.join(missing))
        result=self.run([self.python,'-c',"import reportlab,arabic_reshaper,bidi.algorithm,PIL,charset_normalizer;print('Offline PDF libraries OK')"])
        return {'version':VERSION,'offline':True,'python':str(self.python),'libraries':result.stdout.strip(),'apiKeysRequired':False}
    def load(self):
        return json.loads(protect(base64.b64decode((self.data/'settings.dpapi').read_bytes()),True))
    def save(self,settings):
        target=self.data/'settings.dpapi';temporary=self.data/'settings.dpapi.tmp';temporary.write_bytes(base64.b64encode(protect(json.dumps(settings).encode())));temporary.replace(target)
    def lock(self,wait=0):
        name='Local\\SALES360-'+hashlib.sha256(str(self.data).casefold().encode()).hexdigest()[:24]
        handle=ctypes.windll.kernel32.CreateMutexW(None,False,name)
        if not handle:raise ctypes.WinError()
        status=ctypes.windll.kernel32.WaitForSingleObject(handle,wait)
        if status not in (0,128):
            ctypes.windll.kernel32.CloseHandle(handle)
            if status==258:return None
            raise ctypes.WinError()
        return handle
    def unlock(self,handle):
        ctypes.windll.kernel32.ReleaseMutex(handle);ctypes.windll.kernel32.CloseHandle(handle)
    def initialize(self):
        new=not self.data.exists();self.data.mkdir(parents=True,exist_ok=True)
        if new:
            # Protect only this newly created application data folder, never its parent.
            import csv,io
            sid=list(csv.reader(io.StringIO(self.run(['whoami.exe','/user','/fo','csv','/nh']).stdout)))[0][1]
            self.run(['icacls.exe',self.data,'/inheritance:r','/grant:r',f'*{sid}:(OI)(CI)F','*S-1-5-18:(OI)(CI)F'])
        if (self.data/'settings.dpapi').exists():return self.load()
        db_port=free_port(55540);web_port=free_port(self.args.port)
        if web_port==db_port:web_port=free_port(web_port+1)
        settings={'instance':str(uuid.uuid4()),'dbPort':db_port,'webPort':web_port,'databasePassword':secrets.token_hex(32),'adminDatabasePassword':secrets.token_hex(32),'setupToken':secrets.token_hex(32),'demo':bool(self.args.demo or (ROOT/'offline-demo.flag').exists())}
        if settings['demo']:settings.pop('setupToken');settings['firstPassword']=secrets.token_urlsafe(24)
        self.save(settings);return settings
    def database(self,settings):
        cluster=self.data/'postgres';pwfile=self.data/'initdb-password.tmp'
        if not (cluster/'PG_VERSION').exists():
            pwfile.write_text(settings['adminDatabasePassword'],encoding='utf-8')
            try:self.run([self.pg/'initdb.exe','-D',cluster,'-U','sales360_admin',f'--pwfile={pwfile}','--auth-host=scram-sha-256','--auth-local=scram-sha-256','--encoding=UTF8','--locale=C'],timeout=120)
            finally:pwfile.unlink(missing_ok=True)
        running=self.run([self.pg/'pg_ctl.exe','-D',cluster,'status'],check=False).returncode==0
        if not running:
            self.run([self.pg/'pg_ctl.exe','-D',cluster,'-l',self.data/'postgres.log','-o',f"-h 127.0.0.1 -p {settings['dbPort']}",'-w','start'],timeout=90);self.started_db=True
        env=os.environ.copy();env.update(PGHOST='127.0.0.1',PGPORT=str(settings['dbPort']),PGUSER='sales360_admin',PGPASSWORD=settings['adminDatabasePassword'],PGDATABASE='postgres')
        role=self.run([self.pg/'psql.exe','-At','-c',"SELECT 1 FROM pg_roles WHERE rolname='sales360_app'"],env=env).stdout.strip()
        if role!='1':self.run([self.pg/'psql.exe','-v','ON_ERROR_STOP=1'],env=env,input=f"CREATE ROLE sales360_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '{settings['databasePassword']}';\n")
        exists=self.run([self.pg/'psql.exe','-At','-c',"SELECT 1 FROM pg_database WHERE datname='sales360'"],env=env).stdout.strip()
        if exists!='1':self.run([self.pg/'createdb.exe','-O','sales360_app','sales360'],env=env)
    def stop(self):
        # The launcher owns this mutex until both the API and PostgreSQL have stopped.
        # Waiting for a missing HTTP response alone races installer repair/uninstall.
        for _ in range(150):
            handle=self.lock()
            if handle:
                try:
                    if not (self.data/'settings.dpapi').exists():return {'stopped':True,'alreadyStopped':True}
                    settings=self.load();response=health(f"http://127.0.0.1:{settings['webPort']}")
                    if response and response.get('instance')==settings['instance']:
                        raise RuntimeError('The backend is running without its launcher. Close that SALES360 backend before updating.')
                    cluster=self.data/'postgres'
                    if (cluster/'PG_VERSION').exists():
                        status=self.run([self.pg/'pg_ctl.exe','-D',cluster,'status'],check=False)
                        if status.returncode==0:self.run([self.pg/'pg_ctl.exe','-D',cluster,'-m','fast','-w','stop'],timeout=60)
                    (self.data/'running.json').unlink(missing_ok=True)
                    (self.data/'stop.request').unlink(missing_ok=True)
                    return {'stopped':True,'databaseStopped':True}
                finally:self.unlock(handle)
            if (self.data/'settings.dpapi').exists():
                settings=self.load();response=health(f"http://127.0.0.1:{settings['webPort']}")
                if response:
                    if response.get('instance')!=settings['instance']:raise RuntimeError('This port belongs to another application. It has not been stopped.')
                    (self.data/'stop.request').touch()
            time.sleep(1)
        raise RuntimeError('Application or maintenance operation did not stop. Inspect server.log before updating.')
    def backup(self):
        settings=self.load()
        if health(f"http://127.0.0.1:{settings['webPort']}"):raise RuntimeError('Stop SALES360 before creating this consistent local backup.')
        self.database(settings)
        try:
            with tempfile.TemporaryDirectory(prefix='backup-stage-',dir=self.data) as folder:
                dump=Path(folder)/'database.dump';env=os.environ.copy();env.update(PGHOST='127.0.0.1',PGPORT=str(settings['dbPort']),PGUSER='sales360_app',PGPASSWORD=settings['databasePassword'],PGDATABASE='sales360')
                self.run([self.pg/'pg_dump.exe','--format=custom','--no-owner','--no-acl','--no-comments','--file',dump],env=env,timeout=180)
                archive=io.BytesIO();manifest=[]
                with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as package:
                    files=[(dump,'database.dump')]
                    for name in ['settings.dpapi','first-run-credentials.txt','first-run-setup.txt','demo-access.txt','keys','documents']:
                        source=self.data/name
                        if source.is_file():files.append((source,name))
                        elif source.is_dir():files.extend((p,str(p.relative_to(self.data))) for p in source.rglob('*') if p.is_file())
                    for file,name in files:
                        name=name.replace('\\','/');content=file.read_bytes();package.writestr(name,content);manifest.append({'path':name,'sha256':hashlib.sha256(content).hexdigest()})
                    package.writestr('manifest.json',json.dumps({'version':VERSION,'createdAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':manifest,'scope':'Same Windows identity/machine; isolated restore only'}))
                target=self.data/'backups'/('SALES360-'+time.strftime('%Y%m%d-%H%M%S')+'.s360local');target.parent.mkdir(exist_ok=True);target.write_bytes(b'S360LOCAL1'+protect(archive.getvalue()));return {'backup':str(target),'encrypted':True,'files':len(manifest),'sameWindowsIdentityRequired':True}
        finally:
            if self.started_db:self.run([self.pg/'pg_ctl.exe','-D',self.data/'postgres','-m','fast','-w','stop'],timeout=45,check=False)
    def restore(self,source):
        if self.data.exists():raise RuntimeError('Restore requires a NEW isolated --data-dir. Existing business data will never be overwritten.')
        payload=Path(source).resolve().read_bytes();header=b'S360LOCAL1'
        if not payload.startswith(header):raise RuntimeError('Not a SALES360 local backup.')
        decoded=protect(payload[len(header):],True)
        with zipfile.ZipFile(io.BytesIO(decoded)) as package:
            manifest=json.loads(package.read('manifest.json'))
            for item in manifest['files']:
                name=item['path'].replace('\\','/');target=(self.data/name).resolve()
                if not target.is_relative_to(self.data):raise RuntimeError('Unsafe backup path.')
                if hashlib.sha256(package.read(name)).hexdigest()!=item['sha256']:raise RuntimeError('Backup integrity verification failed.')
            self.initialize()
            for item in manifest['files']:
                if item['path']=='database.dump':continue
                target=self.data/item['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(package.read(item['path'].replace('\\','/')))
            settings=self.load();settings['dbPort']=free_port(55540);settings['webPort']=free_port(self.args.port);settings['instance']=str(uuid.uuid4());self.save(settings);self.database(settings)
            try:
                dump=self.data/'restore-database.tmp';dump.write_bytes(package.read('database.dump'));env=os.environ.copy();env.update(PGHOST='127.0.0.1',PGPORT=str(settings['dbPort']),PGUSER='sales360_app',PGPASSWORD=settings['databasePassword'],PGDATABASE='sales360')
                self.run([self.pg/'pg_restore.exe','--no-owner','--no-acl','--exit-on-error','--dbname','sales360',dump],env=env,timeout=180);dump.unlink()
                self.run([self.pg/'psql.exe','-v','ON_ERROR_STOP=1'],env=env,input="UPDATE outbox SET status='Suppressed after isolated restore'; UPDATE identity_mail SET state='Suppressed after isolated restore',encrypted_payload=''; UPDATE identity_token SET consumed_at=now() WHERE consumed_at IS NULL; UPDATE app_user SET session_version=session_version+1;\n")
                evidence={'restoredTo':str(self.data),'filesVerified':len(manifest['files']),'externalJobsSuppressed':True,'sessionsRevoked':True};(self.data/'restore-evidence.json').write_text(json.dumps(evidence,indent=2));return evidence
            finally:
                if self.started_db:self.run([self.pg/'pg_ctl.exe','-D',self.data/'postgres','-m','fast','-w','stop'],timeout=45,check=False)
    def start(self):
        self.check();mutex=self.lock()
        if not mutex:
            if (self.data/'settings.dpapi').exists():
                settings=self.load();url=f"http://127.0.0.1:{settings['webPort']}";existing=health(url)
                if existing and existing.get('instance')==settings['instance']:
                    if not self.args.no_browser:webbrowser.open(url+('/#setup='+settings['setupToken'] if settings.get('setupToken') else ''))
                    return
            raise RuntimeError('SALES360 is already starting or performing maintenance. Wait a moment and open its shortcut again.')
        logfile=None
        try:
            settings=self.initialize();url=f"http://127.0.0.1:{settings['webPort']}";existing=health(url)
            if existing:raise RuntimeError('The configured port is already in use. Close that application before starting SALES360.')
            self.database(settings);(self.data/'stop.request').unlink(missing_ok=True)
            env=os.environ.copy();env.update(SALES360_ROOT=str(ROOT),SALES360_DATA=str(self.data),SALES360_PYTHON=str(self.python),SALES360_URL=url,SALES360_PUBLIC_URL=url,SALES360_INSTANCE=settings['instance'],SALES360_MAIL_MODE='Offline',SALES360_SIGNUP_COMPANY='demo' if settings['demo'] else 'local',SALES360_SEED='1' if settings['demo'] else '0',ASPNETCORE_ENVIRONMENT='Production')
            env['SALES360_DB']=f"Host=127.0.0.1;Port={settings['dbPort']};Username=sales360_app;Password={settings['databasePassword']};Database=sales360"
            env.pop('SALES360_BOOTSTRAP_PASSWORD',None);env.pop('SALES360_SETUP_TOKEN_HASH',None)
            if settings.get('firstPassword') and not settings['demo']:env['SALES360_BOOTSTRAP_PASSWORD']=settings['firstPassword']
            if settings.get('setupToken') and not settings['demo']:env['SALES360_SETUP_TOKEN_HASH']=hashlib.sha256(settings['setupToken'].encode()).hexdigest()
            logfile=open(self.data/'server.log','a',encoding='utf-8');self.process=subprocess.Popen([str(self.host)],cwd=self.host.parent,env=env,stdout=logfile,stderr=logfile,creationflags=HIDDEN)
            for _ in range(120):
                response=health(url)
                if response and response.get('instance')==settings['instance']:break
                if self.process.poll() is not None:raise RuntimeError('Backend could not start. Read server.log in the application data folder.')
                time.sleep(1)
            else:raise RuntimeError('Application startup timed out. Inspect server.log.')
            if settings.get('firstPassword'):
                if not settings['demo']:(self.data/'first-run-credentials.txt').write_text('SALES360 OFFLINE - keep private\nUsername: administrator\nPassword: '+settings['firstPassword']+'\n\nCreate local users in Sign up; approve them and assign duties in User access.\nNo real email is sent. Recovery links are in identity-mail.\n',encoding='utf-8')
                settings.pop('firstPassword');self.save(settings)
                if not self.args.no_browser:
                    credentials=self.data/('demo-access.txt' if settings['demo'] else 'first-run-credentials.txt')
                    os.startfile(str(credentials))
            launch_url=url
            if settings.get('setupToken') and not settings['demo']:
                with build_opener(ProxyHandler({})).open(url+'/api/auth/config',timeout=5) as response:setup_required=json.load(response).get('setupRequired',False)
                if setup_required:
                    launch_url=url+'/#setup='+settings['setupToken']
                    setup_file=self.data/'first-run-setup.txt'
                    setup_file.write_text('SALES360 FIRST ADMINISTRATOR SETUP - keep private\nOpen this local link and choose your own Administrator email or username and password:\n'+launch_url+'\n\nThis code can enroll the first Administrator once. Never share it.\n',encoding='utf-8')
                else:
                    settings.pop('setupToken');self.save(settings);(self.data/'first-run-setup.txt').unlink(missing_ok=True)
            (self.data/'running.json').write_text(json.dumps({'url':url,'version':VERSION,'instance':settings['instance']}),encoding='utf-8')
            if not self.args.no_browser:webbrowser.open(launch_url)
            if sys.stdout:print(f'SALES360 offline is running: {url}\nData: {self.data}\nUse Stop-SALES360.bat to stop it.',flush=True)
            while self.process.poll() is None and not (self.data/'stop.request').exists():time.sleep(1)
        finally:
            try:
                if self.process and self.process.poll() is None:self.process.terminate();self.process.wait(timeout=15)
                if logfile:logfile.close()
                if self.started_db:self.run([self.pg/'pg_ctl.exe','-D',self.data/'postgres','-m','fast','-w','stop'],timeout=45,check=False)
                (self.data/'stop.request').unlink(missing_ok=True)
                (self.data/'running.json').unlink(missing_ok=True)
            finally:self.unlock(mutex)

def main():
    parser=argparse.ArgumentParser(description='SALES360 offline Windows launcher');parser.add_argument('--data-dir');parser.add_argument('--port',type=int,default=5088);parser.add_argument('--demo',action='store_true');parser.add_argument('--no-browser',action='store_true');parser.add_argument('--check',action='store_true');parser.add_argument('--stop',action='store_true');parser.add_argument('--backup',action='store_true');parser.add_argument('--restore');parser.add_argument('--repair',action='store_true');parser.add_argument('--open-recovery',action='store_true');args=parser.parse_args()
    if not 1024<=args.port<=65000:parser.error('Port must be between 1024 and 65000.')
    installation=Installation(args)
    try:
        if args.open_recovery:
            from email import policy
            from email.parser import BytesParser
            from urllib.parse import quote
            directory=installation.data/'identity-mail'
            messages=[]
            for file in sorted(directory.glob('*.eml'),key=lambda p:p.stat().st_mtime,reverse=True):
                if time.time()-file.stat().st_mtime>1800:continue
                message=BytesParser(policy=policy.default).parsebytes(file.read_bytes())
                if str(message.get('Subject',''))!='Reset your SALES360 password':continue
                messages.append(message)
            if not messages:raise RuntimeError('No recent recovery email. Use Forgot password first, wait a moment, and run this command again. The link expires after 30 minutes.')
            for i,message in enumerate(messages):print(str(i+1)+'. '+str(message['To']))
            choice=int(input('Select recovery email number (keep it private): '))-1
            if not 0<=choice<len(messages):raise RuntimeError('Invalid selection.')
            message=messages[choice];recipient=str(message['To']);body=message.get_content()
            if recipient.endswith('@offline.invalid'):raise RuntimeError('This is a username-only account. Ask an Administrator to open its local reset link in Setting > Recovery mailbox.')
            print('Opening a draft in the default email client. Review it and click Send. Sending needs a configured mailbox and connectivity. The reset link works on this SALES360 PC only.')
            mail_args=quote(recipient,safe='@')+'?subject='+quote(str(message['Subject']),safe='')+'&body='+quote(body,safe='')
            candidates=[]
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE') as key:candidates.append(Path(winreg.QueryValue(key,None).strip('"')))
                except OSError:pass
            for key in ('ProgramFiles','ProgramFiles(x86)'):
                if os.environ.get(key):candidates.append(Path(os.environ[key])/'Microsoft Office/root/Office16/OUTLOOK.EXE')
            outlook=next((p for p in candidates if p.is_file()),None)
            if outlook:subprocess.Popen([str(outlook),'/c','ipm.note','/m',mail_args])
            else:os.startfile('mailto:'+mail_args)
            return 0
        if args.repair:
            result=installation.check();manifest=ROOT/'bundle-manifest.json';damaged=[]
            if manifest.exists():
                for entry in json.loads(manifest.read_text(encoding='utf-8-sig'))['files']:
                    if '__pycache__' in Path(entry['path']).parts or Path(entry['path']).suffix.lower() in ('.pyc','.pyo'):continue
                    file=(ROOT/entry['path']).resolve()
                    if not file.is_relative_to(ROOT):raise RuntimeError('Invalid package manifest path.')
                    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest().lower()!=entry['sha256'].lower():damaged.append(entry['path'])
            if installation.data.exists():
                for name in ('generated','identity-mail'):(installation.data/name).mkdir(exist_ok=True)
            print(json.dumps({'checks':result,'damagedProgramFiles':damaged,'action':'Stop SALES360 and rerun the installer in the same program folder if files are damaged. Preserve the separate data folder. If startup still fails, read server.log and postgres.log in the data folder. Never delete keys or database files. Restore a verified backup to a new folder if needed.','financialDataChanged':False},indent=2));return 1 if damaged else 0
        if args.check:print(json.dumps(installation.check(),indent=2));return 0
        if args.stop:print(json.dumps(installation.stop()));return 0
        if args.backup or args.restore:
            handle=installation.lock()
            if not handle:raise RuntimeError('Stop SALES360 and wait for maintenance to finish before backup or restore.')
            try:print(json.dumps(installation.backup() if args.backup else installation.restore(args.restore)));return 0
            finally:installation.unlock(handle)
        installation.start();return 0
    except Exception as error:
        message=str(error)
        if args.repair:message+='\nStop SALES360 and rerun the installer in the same program folder. Preserve your separate data folder and backups. Do not delete database files or keys.'
        if sys.stderr:print(message,file=sys.stderr)
        elif os.name=='nt':ctypes.windll.user32.MessageBoxW(None,message,'SALES360 could not start',0x10)
        return 1
if __name__=='__main__':raise SystemExit(main())
