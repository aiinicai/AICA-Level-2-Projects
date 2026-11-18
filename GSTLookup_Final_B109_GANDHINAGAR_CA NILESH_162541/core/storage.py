"""Thread-safe local task history, snapshots and persistent daily budget."""
import sqlite3, json, threading, re
from datetime import datetime, date
from pathlib import Path

def encode(value):
    if isinstance(value,(datetime,date)): return {'__date__':value.isoformat()}
    raise TypeError(type(value).__name__)

def decode(value):
    if set(value)=={'__date__'}:
        try:return date.fromisoformat(value['__date__'])
        except ValueError:return datetime.fromisoformat(value['__date__'])
    return value

class Storage:
    def __init__(self,folder: Path):
        self.folder=folder.resolve();self.folder.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock()
        self.db=sqlite3.connect(self.folder/'history.sqlite',check_same_thread=False,timeout=10)
        self.db.execute('CREATE TABLE IF NOT EXISTS log (timestamp TEXT, input TEXT, result TEXT, message TEXT)')
        if 'task_id' not in [r[1] for r in self.db.execute('PRAGMA table_info(log)')]:self.db.execute('ALTER TABLE log ADD COLUMN task_id TEXT')
        self.db.execute('CREATE TABLE IF NOT EXISTS budget (day TEXT PRIMARY KEY, count INTEGER)')
        self.db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, created TEXT, finished TEXT, status TEXT, year TEXT, inputs INTEGER, taxpayers INTEGER, returns INTEGER, payload TEXT)');self.db.commit()
    def reserve(self,cap: int):
        day=date.today().isoformat()
        with self.lock,self.db:
            self.db.execute('INSERT OR IGNORE INTO budget VALUES (?,0)',(day,))
            cur=self.db.execute('UPDATE budget SET count=count+1 WHERE day=? AND count<?',(day,cap))
            if cur.rowcount!=1: raise ValueError(f'Daily cap of {cap} reached; resume tomorrow.')
    def log(self,value,result,message,task_id=None):
        record={'Timestamp':datetime.now().isoformat(timespec='seconds'),'Input':value,'Result':result,'Message':message}
        with self.lock,self.db:self.db.execute('INSERT INTO log(timestamp,input,result,message,task_id) VALUES (?,?,?,?,?)',(*record.values(),task_id))
        return record
    def history(self):
        with self.lock:
            return [dict(zip(['Timestamp','Input','Result','Message'],r)) for r in self.db.execute('SELECT timestamp,input,result,message FROM log ORDER BY rowid DESC LIMIT 1000')]
    def save_task(self,engine):
        if not engine.task_id:return
        payload=json.dumps({'rows':engine.rows,'details':engine.details,'logs':engine.logs,'reports':engine.return_reports},default=encode,ensure_ascii=False)
        status='STOPPED' if engine.cancelled else ('NEEDS ATTENTION' if any(r['State']=='ERROR' for r in engine.return_reports) or any(r['Result']!='OK' for r in engine.logs) else 'COMPLETE')
        with self.lock,self.db:
            self.db.execute('INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?,?,?,?)',(engine.task_id,engine.task_created,datetime.now().isoformat(timespec='seconds'),status,engine.year,engine.total,len(engine.rows),len(engine.details),payload))
    def tasks(self):
        with self.lock:
            return [dict(zip(['id','created','finished','status','year','inputs','taxpayers','returns'],r)) for r in self.db.execute('SELECT id,created,finished,status,year,inputs,taxpayers,returns FROM tasks ORDER BY finished DESC LIMIT 100')]
    def task(self,identifier):
        with self.lock:row=self.db.execute('SELECT payload FROM tasks WHERE id=?',(identifier,)).fetchone()
        if not row:raise ValueError('Task no longer exists.')
        return json.loads(row[0],object_hook=decode)
    def delete_task(self,identifier):
        if not re.fullmatch('[0-9a-f]{32}',identifier):raise ValueError('Invalid task identifier.')
        (self.folder/'exports'/f'task-{identifier}.xlsx').unlink(missing_ok=True)
        with self.lock,self.db:
            self.db.execute('DELETE FROM tasks WHERE id=?',(identifier,));self.db.execute('DELETE FROM log WHERE task_id=?',(identifier,))
