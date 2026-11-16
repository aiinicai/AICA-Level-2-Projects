"""Offline signed activation keys. Local licensing is not tamper-proof DRM."""
import base64
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from license_public import PUBLIC_KEY

TRIAL_DAYS = 30
TRIAL_END = datetime(2026,11,3,tzinfo=timezone(timedelta(hours=5,minutes=30))).timestamp()+TRIAL_DAYS*86400

class License:
    def __init__(self,root):
        self.path=Path(root)/'license_state.json'
        self.state=json.loads(self.path.read_text()) if self.path.exists() else {'used':[], 'expires':TRIAL_END, 'last_seen':0}
        self.checkpoint()
    def write(self):
        temp=self.path.with_suffix('.tmp'); temp.write_text(json.dumps(self.state,indent=2)); temp.replace(self.path)
    def checkpoint(self):
        now=time.time()
        self.rollback=now+300 < self.state.get('last_seen',0)
        self.state['last_seen']=max(now,self.state.get('last_seen',0)); self.write()
    def remaining(self):
        return 0 if self.rollback else max(0,self.state['expires']-time.time())
    def activate(self,key):
        try:
            payload,signature=key.strip().split('.')
            raw=base64.urlsafe_b64decode(payload+'='*(-len(payload)%4))
            sig=base64.urlsafe_b64decode(signature+'='*(-len(signature)%4))
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY)).verify(sig,raw)
            data=json.loads(raw)
            if data['seconds'] not in (300,86400,2592000): raise ValueError()
        except Exception: raise ValueError('Invalid activation key.')
        if data['id'] in self.state['used']: raise ValueError('This key has already been used on this installation.')
        if self.rollback: raise ValueError('Correct the system clock before activating.')
        self.state['used'].append(data['id']); self.state['expires']=time.time()+data['seconds']; self.write()
