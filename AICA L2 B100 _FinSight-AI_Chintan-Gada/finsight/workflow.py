import sqlite3,datetime
from pathlib import Path
DB=Path.home()/'.finsight_ai'/'workflow.db'

def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, company TEXT, state TEXT, created TEXT, updated TEXT, reviewer TEXT, notes TEXT)')
    c.commit();return c

def create(run_id,company):
    with connect() as c:
        now=datetime.datetime.now(datetime.timezone.utc).isoformat()
        c.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?)',(run_id,company,'DRAFT',now,now,'',''))

def transition(run_id,new_state,reviewer='',notes=''):
    allowed={'DRAFT':['VALIDATED','REJECTED'],'VALIDATED':['ANALYSED','REJECTED'],'ANALYSED':['PENDING_REVIEW','REJECTED'],'PENDING_REVIEW':['APPROVED','REJECTED'],'REJECTED':['PENDING_REVIEW'],'APPROVED':[]}
    with connect() as c:
        row=c.execute('SELECT state FROM runs WHERE id=?',(run_id,)).fetchone()
        if not row: raise ValueError('Unknown run')
        if new_state not in allowed[row[0]]: raise ValueError(f'Invalid transition {row[0]} -> {new_state}')
        c.execute('UPDATE runs SET state=?,updated=?,reviewer=?,notes=? WHERE id=?',(new_state,datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer,notes,run_id))

def get(run_id):
    with connect() as c: return c.execute('SELECT * FROM runs WHERE id=?',(run_id,)).fetchone()
