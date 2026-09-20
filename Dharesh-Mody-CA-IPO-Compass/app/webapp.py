"""Local-only browser dashboard. No cloud account or hosted service."""
import json
import os
import secrets
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit
from . import db, scoring
from .refresh import run_refresh
from .scrapers import GMP_DIAGNOSTIC_SOURCES

class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address=('127.0.0.1', 0)):
        super().__init__(address, Handler)
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.cancel = threading.Event()
        self.progress = {'running':False, 'message':'Ready', 'log':[], 'revision':0}
        self.preferences = Path(db.APP_DIR)/'dashboard_preferences.json'
        try:
            self.watches = set(json.loads(self.preferences.read_text(encoding='utf-8')).get('watchlist',[]))
        except (OSError,ValueError,TypeError): self.watches=set()
    def emit(self, kind, value):
        with self.lock:
            if kind in ('log','done'):
                self.progress['message'] = value
                self.progress['log'] = (self.progress['log']+[value])[-150:]
            if kind == 'data': self.progress['revision'] += 1
            if kind == 'done': self.progress['running'] = False
    def refresh(self):
        with self.lock:
            if self.progress['running']: return
            self.progress.update(running=True, message='Starting official feeds and company research…', log=[])
            self.cancel.clear()
        def work():
            try: run_refresh(self.emit, self.cancel)
            except Exception as e: self.emit('done', 'Refresh stopped: '+str(e))
        threading.Thread(target=work, daemon=True).start()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def send(self, value, status=200, mime='application/json'):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode() if mime=='application/json' else value
        self.send_response(status)
        self.send_header('Content-Type', mime+'; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)
    def trusted(self):
        return self.headers.get('Host') == '127.0.0.1:'+str(self.server.server_port)
    def do_GET(self):
        if not self.trusted(): return self.send({'error':'Local access only'},403)
        path = urlsplit(self.path).path
        if path == '/api/state':
            records = [r for r in db.all_ipos() if db.in_refresh_scope(r)]
            for r in records:
                r['status'] = db.display_status(r)
                r['analysis'] = scoring.analyse(r)
                r['analysis']['factors'] = [{'name':scoring.FACTOR_NAMES[k], 'score':v, 'weight':100*scoring.RAW_WEIGHTS[k]/scoring.RAW_TOTAL} for k,v in r['analysis']['factors'].items()]
                r['sources'] = db.sources_for(r['id'])
                r['gmp_quotes'] = db.gmp_quotes_for(r['id'], order=GMP_DIAGNOSTIC_SOURCES)
            with self.server.lock: progress = dict(self.server.progress)
            return self.send({'records':records,'progress':progress,'watchlist':sorted(self.server.watches),'logs':db.recent_refresh_log(30),'token':self.server.token})
        assets = {'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
        if path in assets:
            file,mime=assets[path]
            return self.send((Path(__file__).parent/'ui'/'web'/file).read_bytes(),mime=mime)
        self.send({'error':'Not found'},404)
    def do_POST(self):
        origin = self.headers.get('Origin')
        expected='http://127.0.0.1:'+str(self.server.server_port)
        if not self.trusted() or origin not in (None,expected) or self.headers.get('X-Compass-Token') != self.server.token:
            return self.send({'error':'Local session required'},403)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0 <= size <= 5_000_000: raise ValueError('File exceeds 5 MB')
            data=json.loads(self.rfile.read(size) or b'{}')
            path=urlsplit(self.path).path
            if path=='/api/refresh': self.server.refresh()
            elif path=='/api/cancel': self.server.cancel.set()
            elif path=='/api/watch':
                if not db.get(data['id']): raise ValueError('IPO not found')
                with self.server.lock:
                    if data.get('saved'): self.server.watches.add(data['id'])
                    else: self.server.watches.discard(data['id'])
                    temporary=self.server.preferences.with_suffix('.tmp')
                    temporary.write_text(json.dumps({'watchlist':sorted(self.server.watches)}),encoding='utf-8')
                    temporary.replace(self.server.preferences)
            elif path=='/api/import':
                rows=data.get('records',[])
                if not isinstance(rows,list) or len(rows)>500: raise ValueError('Supply at most 500 records')
                rows=[db.validate_incoming(r) for r in rows]
                skipped=0
                primary_source=data.get('primary_source')
                source_key,source_name,official={
                    'NSE India':('nse','NSE India (manually entered)',True),
                    'BSE India':('bse','BSE India (manually entered)',True),
                    'RHP / DRHP':('rhp','RHP / DRHP (manually entered)',True),
                    'Chittorgarh':('chittorgarh','Chittorgarh (manually entered)',False),
                }.get(primary_source,('manual','User imported data',False))
                for r in rows:
                    if data.get('backup'):
                        db.upsert_ipo(db.ensure_record(r))
                    else:
                        result=db.merge_incoming(r,source_key,source_name,data.get('source_url',''),'User import; verify original filing',official)
                        if result is None:skipped+=1
                db.consolidate_duplicates()
                self.server.emit('data',None)
                if skipped:
                    self.send({'ok':True,'skipped':skipped,'note':'Some rows were skipped: no open/close date found (likely closed IPOs).'});return
            elif path=='/api/import_page':
                from .page_import import import_saved_page
                message=import_saved_page(str(data.get('filename',''))[:200],str(data.get('text',''))[:4_000_000])
                self.server.emit('data',None)
                return self.send({'ok':True,'message':message})
            elif path=='/api/notes':
                record=db.get(data['id'])
                if not record: raise ValueError('IPO not found')
                record['notes']=str(data.get('notes',''))[:20000]
                db.upsert_ipo(record)
            else: return self.send({'error':'Not found'},404)
            self.send({'ok':True})
        except (ValueError,TypeError,KeyError) as e: self.send({'error':str(e)},400)

def main(auto_refresh=True):
    db.init_db()
    server=DashboardServer()
    address='http://127.0.0.1:'+str(server.server_port)
    print('\nCA IPO Compass is running on this PC.\nOpen: '+address+'\nKeep this window open. Press Ctrl+C to stop.\n',flush=True)
    threading.Timer(.7, lambda:open_preferred_browser(address)).start()
    # Skip the automatic refresh if the last one completed less than 15
    # minutes ago — the dashboard still opens instantly with the saved
    # database either way. The page itself can keep data live afterwards
    # via the "Refresh every 15 minutes while this page stays open" option.
    if auto_refresh and db.refresh_is_stale(): threading.Timer(1,server.refresh).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        server.cancel.set()
        server.server_close()


def open_preferred_browser(address):
    """Open Edge or Chrome explicitly; never fall back to Internet Explorer on Windows."""
    if sys.platform != 'win32':
        import webbrowser
        return webbrowser.open(address)
    candidates=[]
    try:
        import winreg
        for executable in ('msedge.exe','chrome.exe'):
            try:
                registry_path='SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\'+executable
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,registry_path) as key:
                    candidates.append(str(winreg.QueryValue(key,None)).strip('"'))
            except OSError: pass
    except ImportError: pass
    roots=[os.environ.get('PROGRAMFILES(X86)'),os.environ.get('PROGRAMFILES'),os.environ.get('LOCALAPPDATA')]
    for root in filter(None,roots):
        candidates.extend([
            os.path.join(root,'Microsoft','Edge','Application','msedge.exe'),
            os.path.join(root,'Google','Chrome','Application','chrome.exe'),
        ])
    for executable in dict.fromkeys(candidates):
        if executable and os.path.isfile(executable):
            try:
                subprocess.Popen([executable,'--new-window',address],close_fds=True)
                return True
            except OSError: continue
    print('Edge or Chrome was not found. Copy the local address above into Edge or Chrome.',flush=True)
    return False
