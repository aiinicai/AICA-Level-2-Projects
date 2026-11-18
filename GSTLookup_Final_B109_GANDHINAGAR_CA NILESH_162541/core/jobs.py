"""One portal worker keeps slow network operations off the UI request thread."""
import copy, threading, time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

VIEW_FIELDS=('rows','details','logs','total','completed','message','level','year','phase','current','challenge','return_reports','task_id','cancelled')

class JobRunner:
    def __init__(self,engine,background=False):
        self.engine=engine;self.background=background;self.lock=threading.RLock();self.busy=False;self.stage='Ready';self.started=0.;self.future=None
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='GSTPortal') if background else None
        self.engine.provider.progress=self.progress;self.engine.provider.cancel_requested=self.engine.stop_requested.is_set
        self._publish()
    def _publish(self):
        with self.lock:self.snapshot=copy.deepcopy({k:getattr(self.engine,k) for k in VIEW_FIELDS})
    def progress(self,message):
        with self.lock:self.stage=message
    def view(self):
        with self.lock:
            if not self.background and not self.busy:self._publish()
            return SimpleNamespace(**copy.deepcopy(self.snapshot),settings=self.engine.settings)
    def status(self):
        with self.lock:return {'busy':self.busy,'stage':'Stopping after the current operation…' if self.engine.stop_requested.is_set() and self.busy else self.stage,'elapsed':int(time.monotonic()-self.started) if self.busy else 0,'waiting_captcha':self.snapshot['challenge'] is not None}
    def submit(self,label,action):
        with self.lock:
            if self.busy:raise ValueError('An operation is already running. Please wait for it to finish.')
            self.busy=True;self.stage=label;self.started=time.monotonic()
        if self.pool:self.future=self.pool.submit(self._run,action)
        else:self._run(action)
    def _run(self,action):
        try:action()
        except Exception as exc:
            self.engine.message='Operation could not finish: '+str(exc);self.engine.level='error'
        finally:
            if self.engine.stop_requested.is_set() and not self.engine.cancelled:self.engine.stop()
            self._publish()
            with self.lock:self.busy=False;self.stage=self.engine.message
    def request_stop(self):
        self.engine.stop_requested.set()
        with self.lock:running=self.busy
        if not running:self.submit('Stopping task…',self.engine.stop)
    def wait(self,timeout=10):
        if self.future:self.future.result(timeout=timeout)
    def close(self):
        self.engine.stop_requested.set()
        if self.pool:
            self.pool.submit(self.engine.provider.close).result(timeout=240);self.pool.shutdown(wait=True)
        else:self.engine.provider.close()
