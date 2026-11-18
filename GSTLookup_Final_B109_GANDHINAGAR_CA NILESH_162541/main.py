"""Start web UI or optional native webview; all data stays local."""
import argparse, logging, os, sys, threading, webbrowser, json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from werkzeug.serving import make_server
from config import Settings
from core.portal_client import PortalClient
from core.storage import Storage
from core.engine import Engine
from ui_web import create_app

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--demo',action='store_true');ap.add_argument('--desktop',action='store_true');ap.add_argument('--no-browser',action='store_true');ap.add_argument('--port',type=int,default=8501);ap.add_argument('--data-dir',type=Path);ap.add_argument('--smoke-test',action='store_true');args=ap.parse_args()
    folder=args.data_dir or Path.home()/'Documents'/'GSTLookup';folder.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(handlers=[RotatingFileHandler(folder/'app.log',maxBytes=1000000,backupCount=3)],level=logging.INFO)
    configfile=folder/'settings.json'
    if not configfile.exists(): configfile.write_text(json.dumps({'interval':3.0,'daily_cap':100,'timeout':45.0,'retries':3},indent=2))
    cfg=json.loads(configfile.read_text());settings=Settings(interval=float(cfg.get('interval',3)),daily_cap=int(cfg.get('daily_cap',100)),demo=args.demo,timeout=max(2,min(60,float(cfg.get('timeout',45)))),retries=int(cfg.get('retries',3)))
    mock=None
    if args.demo:
        from core.mock_portal import create_mock
        mock=make_server('127.0.0.1',0,create_mock(),threaded=True);threading.Thread(target=mock.serve_forever,daemon=True).start();settings.base=f'http://127.0.0.1:{mock.server_port}'
    storage=Storage(folder);provider=PortalClient(settings);engine=Engine(provider,storage,settings);app=create_app(engine,background=True)
    server=make_server('127.0.0.1',args.port,app,threaded=True);url=f'http://127.0.0.1:{server.server_port}'
    print(f'GST Lookup: {url} | data: {folder}',flush=True)
    if args.smoke_test:
        threading.Thread(target=server.serve_forever,daemon=True).start()
        import requests
        assert requests.get(url,timeout=10).status_code==200
        server.shutdown();app.extensions['jobs'].close();storage.db.close();server.server_close()
        if mock:mock.shutdown()
        print('SMOKE PASS',flush=True);return
    if args.desktop:
        try:import webview
        except ImportError:print('pywebview unavailable; opening default browser.',flush=True)
        else:
            serving=threading.Thread(target=server.serve_forever,daemon=True);serving.start()
            try:
                try:
                    webview.create_window('GST Lookup',url,width=1200,height=850);webview.start()
                except Exception as exc:
                    print('Native window unavailable; opening default browser. '+str(exc),flush=True)
                    webbrowser.open(url)
                    while serving.is_alive():serving.join(.5)
            except KeyboardInterrupt:pass
            finally:
                server.shutdown();app.extensions['jobs'].close();server.server_close();storage.db.close()
                if mock:mock.shutdown()
            return
    if not args.no_browser: threading.Timer(.7,lambda:webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        app.extensions['jobs'].close();server.server_close();storage.db.close()
        if mock: mock.shutdown()
if __name__=='__main__': main()
