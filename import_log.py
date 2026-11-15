"""Local diagnostic log for document intake; document contents are never logged."""
import datetime, json, threading, uuid
from pathlib import Path

LOG_PATH=Path(__file__).resolve().parent/'import_diagnostics.jsonl'
_lock=threading.Lock()

def start(path, requested_kind):
    token=uuid.uuid4().hex
    write(token,'start',path=str(path),requested_kind=requested_kind)
    return token

def write(token, step, **data):
    record={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'id':token,'step':step,**data}
    with _lock:
        with LOG_PATH.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(record,ensure_ascii=False,default=str)+'\n')

def fail(token, error):write(token,'error',error=str(error),error_type=type(error).__name__)
def finish(token, **data):write(token,'complete',**data)
