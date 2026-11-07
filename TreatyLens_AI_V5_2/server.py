"""TreatyLens AI V5 local-only Python HTTP server (standard library)."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from pathlib import Path
from tax_engine import DB,COUNTRIES,CATEGORIES,assess,InputError
import json
BASE=Path(__file__).resolve().parent
class Handler(BaseHTTPRequestHandler):
 def send_json(self,code,obj):
  b=json.dumps(obj,ensure_ascii=False).encode('utf-8');self.send_response(code)
  self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)))
  self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
 def do_GET(self):
  path=urlsplit(self.path).path
  if path=='/api/health':return self.send_json(200,{'ok':True,'version':'5.1','rate_count':len(DB['rates'])})
  if path=='/api/data':
   return self.send_json(200,{'countries':COUNTRIES,'categories':CATEGORIES,'recipient_types':DB['recipient_types'],'rates':[{k:v for k,v in r.items() if k!='source_text'} for r in DB['rates']]})
  if path=='/api/evidence':
   q=parse_qs(urlsplit(self.path).query);rid=q.get('id',[''])[0];entry=next((x for x in DB['rates'] if x['id']==rid),None)
   return self.send_json(200,entry) if entry else self.send_json(404,{'error':'No matching rate record'})
  if path not in ('/','/index.html'):return self.send_json(404,{'error':'Not found'})
  b=(BASE/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
 def do_POST(self):
  if urlsplit(self.path).path!='/api/assess':return self.send_json(404,{'error':'Not found'})
  try:
   size=int(self.headers.get('Content-Length','0'))
   if size<1 or size>100000:return self.send_json(413,{'error':'Invalid request size'})
   return self.send_json(200,assess(json.loads(self.rfile.read(size))))
  except (InputError,ValueError,TypeError) as e:return self.send_json(400,{'error':str(e)})
  except Exception:return self.send_json(500,{'error':'Unexpected internal error'})
if __name__=='__main__':
 print('TreatyLens AI V5.1 — http://127.0.0.1:8765',flush=True)
 ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
