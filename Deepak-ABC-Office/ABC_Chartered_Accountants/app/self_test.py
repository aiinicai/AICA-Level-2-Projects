"""Run using runtime/python.exe -I app/self_test.py. Uses temporary data only."""
import base64
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import os
import zipfile
from app import Database,Service

ADMIN_PASSWORD='Administrator-Test-2026!'
TEMP_PASSWORD='Temporary-Password-2026!'
STAFF_PASSWORD='Staff-New-Password-2026!'

class OfficeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.db=Database(Path(self.temp.name)/'data')
  self.owner=self.db.invoke('createAdministrator',[dict(name='Office Administrator',email='owner@example.test',username='admin',password=ADMIN_PASSWORD)])
  self.token=self.owner['token']
  self.db.invoke('saveMaster',[self.token,'Clients',dict(name='Test Client',entityType='Company',active='Yes')])
  for name,username,role in [('Staff One','staff1','Staff'),('Office Manager','manager1','Manager')]:
   self.db.invoke('saveMaster',[self.token,'Employees',dict(name=name,username=username,email='office@example.test',role=role,active='Yes',temporaryPassword=TEMP_PASSWORD)])
  initial=self.db.invoke('bootstrap',[self.token]); self.data=initial['data']; self.staff=next(e for e in self.data['Employees'] if e['username']=='staff1')
  login=self.db.invoke('login',['staff1',TEMP_PASSWORD]); self.staff_token=self.db.invoke('changePassword',[login['token'],TEMP_PASSWORD,STAFF_PASSWORD])['token']
  self.client=self.data['Clients'][0]['id']
  self.assignment=dict(client=self.client,work='WK2',employee=self.staff['id'],reviewer='EMP001',periodicity='Monthly',financialYear='2026–27',period='October',priority='Normal',status='Assigned',blocker='None',allocationDate='2026-10-01',targetDate='2026-10-31')
  result=self.db.invoke('saveAssignment',[self.token,self.assignment]); self.assignment=result['data']['Assignments'][0]
 def tearDown(self): self.temp.cleanup()
 def save_time(self,**kwargs):
  values=dict(date='2026-10-06',assignment=self.assignment['id'],startTime='09:30',endTime='10:30',billing='Billable',note='GST reconciliation'); values.update(kwargs)
  return self.db.invoke('saveTime',[self.staff_token,values])
 def test_login_and_passwords(self):
  with self.assertRaises(ValueError): self.db.invoke('login',['staff1','Wrong password'])
  with self.db.connect() as con:
   hashes=[r[0] for r in con.execute('SELECT password_hash FROM credentials')]
   self.assertTrue(all(h.startswith('pbkdf2_sha256$600000$') for h in hashes)); self.assertFalse(any(STAFF_PASSWORD in h for h in hashes))
  self.assertFalse(self.db.invoke('bootstrap',[self.staff_token])['user']['admin'])
  with self.assertRaises(ValueError): self.db.invoke('createAdministrator',[{}])
 def test_staff_permissions(self):
  values={**self.assignment,'status':'In progress','client':'INVALID'}
  result=self.db.invoke('saveAssignment',[self.staff_token,values]); changed=result['data']['Assignments'][0]
  self.assertEqual(changed['client'],self.client)
  with self.assertRaises(ValueError): self.db.invoke('saveAssignment',[self.staff_token,{**changed,'status':'Completed'}])
  with self.assertRaises(ValueError): self.db.invoke('saveMaster',[self.staff_token,'Clients',dict(name='Forbidden')])
 def test_manager_access(self):
  session=self.db.invoke('login',['manager1',TEMP_PASSWORD]); token=self.db.invoke('changePassword',[session['token'],TEMP_PASSWORD,STAFF_PASSWORD])['token']
  self.assertTrue(self.db.invoke('bootstrap',[token])['user']['admin'])
  self.db.invoke('saveCommunication',[token,dict(title='Office update',message='Meeting at 15:00',priority='Normal',active='Yes')])
 def test_time_ranges_and_idle(self):
  self.save_time(); row=self.db.invoke('bootstrap',[self.staff_token])['data']['Timesheets'][0]
  self.assertEqual(row['minutes'],'60'); self.assertEqual(row['startTime'],'09:30')
  with self.assertRaises(ValueError): self.save_time(startTime='10:00',endTime='11:00')
  self.save_time(startTime='10:30',endTime='11:00')
  self.save_time(assignment='IDLE',startTime='12:00',endTime='13:30',billing='Billable')
  last=self.db.invoke('bootstrap',[self.staff_token])['data']['Timesheets'][-1]
  self.assertEqual(last['minutes'],'90'); self.assertEqual(last['billing'],'Non-billable')
 def test_legacy_and_stale_edit(self):
  with self.db.connect() as con:
   Service(con,self.db).write('Timesheets',dict(id='OLD',employee=self.staff['id'],date='2026-10-01',assignment=self.assignment['id'],client=self.client,minutes='90',note='Earlier duration entry',version='1'))
  result=self.save_time(id='OLD',version='1',date='2026-10-01',startTime='',endTime='',minutes=90,billing='')
  row=result['data']['Timesheets'][0]; self.assertEqual(row['minutes'],'90'); self.assertEqual(row['startTime'],'')
  with self.assertRaises(ValueError): self.save_time(id='OLD',version='1')
 def test_explanations(self):
  result=self.db.invoke('timeQuestion',[self.token,self.staff['id'],'2026-10-06','Explain idle time.',''])
  q=result['data']['TimeQueries'][0]
  result=self.db.invoke('timeAnswer',[self.staff_token,q['id'],'Waiting for allocation.',q['version']])
  self.assertEqual(result['data']['TimeQueries'][0]['answer'],'Waiting for allocation.')
 def test_communications_visibility(self):
  rows=self.db.invoke('saveCommunication',[self.token,dict(title='Meeting',message='15:00',priority='Important',active='Yes')]); self.assertEqual(len(rows),1)
  self.assertEqual(len(self.db.invoke('getCommunications',[self.staff_token])),1)
  with self.assertRaises(ValueError): self.db.invoke('saveCommunication',[self.staff_token,dict(title='Blocked',message='Blocked')])
  self.db.invoke('saveCommunication',[self.token,{**rows[0],'active':'No'}]); self.assertEqual(self.db.invoke('getCommunications',[self.staff_token]),[])
 def test_reports(self):
  self.save_time(); self.save_time(assignment='IDLE',startTime='13:00',endTime='14:00')
  f=dict(type='Staff',employee=self.staff['id'],client='',assignment='',**{'from':'2026-10-01','to':'2026-10-31'})
  report=self.db.invoke('previewTimeReport',[self.token,f]); self.assertEqual(report['minutes'],120); self.assertEqual(report['groups'][0]['rows'][0][2:5],['09:30','10:30','1:00'])
  client=self.db.invoke('previewTimeReport',[self.token,{**f,'type':'Client','client':self.client}]); self.assertEqual(client['minutes'],60)
  with self.assertRaises(ValueError): self.db.invoke('previewTimeReport',[self.staff_token,f])
  for format in ['pdf','docx']:
   result=self.db.invoke('exportTimeReport',[self.token,f,format]); raw=base64.b64decode(result['base64'])
   self.assertTrue(raw.startswith(b'%PDF') if format=='pdf' else zipfile.is_zipfile(io.BytesIO(raw)))
 def test_resets_and_recovery(self):
  self.db.invoke('forgotPassword',['staff1']); self.assertEqual(len(self.db.invoke('bootstrap',[self.token])['resetRequests']),1)
  self.db.invoke('resetEmployeePassword',[self.token,self.staff['id'],TEMP_PASSWORD,True])
  with self.assertRaises(ValueError): self.db.invoke('bootstrap',[self.staff_token])
  recovered=self.db.invoke('recoverOwner',['admin',self.owner['recoveryCode'],'Owner-New-Password-2026!'])
  self.assertTrue(recovered.get('recoveryCode'))
  with self.assertRaises(ValueError): self.db.invoke('bootstrap',[self.token])
  with self.assertRaises(ValueError): self.db.invoke('recoverOwner',['admin',self.owner['recoveryCode'],'Owner-New-Password-2026!'])
 def test_backup_and_persistence(self):
  self.save_time(); backup=self.db.invoke('backupDatabase',[self.token]); path=Path(self.temp.name)/'restored.sqlite3'; path.write_bytes(base64.b64decode(backup['base64']))
  with sqlite3.connect(path) as con:
   self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
   self.assertEqual(con.execute("SELECT count(*) FROM records WHERE kind='Timesheets'").fetchone()[0],1)
  db=Database(Path(self.temp.name)/'data'); self.assertEqual(len(db.invoke('bootstrap',[self.token])['data']['Timesheets']),1)

class BackupHandleTests(unittest.TestCase):
 def test_connection_context_closes_even_on_error(self):
  with tempfile.TemporaryDirectory() as folder:
   db=Database(folder)
   with db.connect() as con: con.execute('SELECT 1')
   with self.assertRaises(sqlite3.ProgrammingError): con.execute('SELECT 1')
   with self.assertRaises(ValueError):
    with db.connect() as failed:
     failed.execute("INSERT INTO meta VALUES('rollback-test','no')")
     raise ValueError('Simulated operation failure')
   with self.assertRaises(sqlite3.ProgrammingError): failed.execute('SELECT 1')
   with db.connect() as fresh:
    self.assertIsNone(fresh.execute("SELECT value FROM meta WHERE key='rollback-test'").fetchone())
 def test_backup_closes_handles_before_windows_style_rename(self):
  with tempfile.TemporaryDirectory() as folder:
   db=Database(folder); real_connect=sqlite3.connect; real_replace=os.replace; connections=[]
   class TrackedConnection(sqlite3.Connection):
    closed=False
    def close(self):
     self.closed=True
     return super().close()
   def tracked_connect(*args,**kwargs):
    kwargs['factory']=TrackedConnection
    con=real_connect(*args,**kwargs); connections.append(con); return con
   def windows_replace(source,destination):
    if any(not con.closed for con in connections):
     raise PermissionError(32,'The process cannot access the file because it is being used by another process')
    return real_replace(source,destination)
   destination=Path(folder)/'backups'/'windows-test.sqlite3'
   with patch('app.sqlite3.connect',tracked_connect), patch('app.os.replace',windows_replace):
    db.backup(destination)
   self.assertEqual(len(connections),2)
   self.assertTrue(all(con.closed for con in connections))
   with real_connect(destination) as con:
    self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
   self.assertEqual(list(Path(folder).rglob('*.pending')),[])
 def test_startup_survives_backup_failure(self):
  with tempfile.TemporaryDirectory() as folder:
   with patch.object(Database,'backup',side_effect=PermissionError(32,'Simulated locked backup')):
    db=Database(folder)
   result=db.invoke('createAdministrator',[dict(name='Owner',username='admin',email='owner@example.test',password=ADMIN_PASSWORD)])
   self.assertTrue(result['token'])
   self.assertTrue((Path(folder)/'error.log').exists())

if __name__=='__main__': unittest.main(verbosity=2)
