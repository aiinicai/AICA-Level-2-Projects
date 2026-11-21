"""Binary-only runtime subprocess capture, hidden Windows children, loss-aware decoding."""
from __future__ import annotations
from dataclasses import dataclass
import base64,subprocess,threading
_state=threading.local()

def reset_evidence():_state.evidence=[]
def take_evidence():
    result=getattr(_state,'evidence',[]);_state.evidence=[];return result

def decode_output(data):
    if isinstance(data,str):return data,'already decoded',[]
    data=bytes(data or b'')
    try:return data.decode('utf-8-sig'),'utf-8',[]
    except UnicodeDecodeError:
        try:return data.decode('cp1252'),'cp1252',['Process output was not UTF-8; decoded as CP1252. Original bytes retained.']
        except UnicodeDecodeError:return data.decode('utf-8',errors='replace'),'utf-8 replacement',['Undecodable process bytes replaced for display only. Original bytes retained as Base64 evidence.']

def windows_options(platform=None):
    import os
    if (platform or os.name)!='nt':return {}
    info=subprocess.STARTUPINFO();info.dwFlags|=subprocess.STARTF_USESHOWWINDOW;info.wShowWindow=subprocess.SW_HIDE
    return dict(startupinfo=info,creationflags=subprocess.CREATE_NO_WINDOW)

@dataclass
class Capture:
    returncode:int
    stdout:str
    stderr:str
    raw_stdout:bytes
    raw_stderr:bytes
    warnings:list

def run_hidden(command,*,timeout=120,env=None,cwd=None):
    # text=False is essential: Python 3.14 must never start locale-decoding readerthreads.
    result=subprocess.run(command,capture_output=True,text=False,check=False,timeout=timeout,env=env,cwd=cwd,**windows_options())
    stdout,encoding,outnotes=decode_output(result.stdout);stderr,errencoding,errnotes=decode_output(result.stderr)
    evidence=dict(executable=str(command[0]),stdout_encoding=encoding,stderr_encoding=errencoding,
                  stdout_base64=base64.b64encode(result.stdout or b'').decode('ascii'),
                  stderr_base64=base64.b64encode(result.stderr or b'').decode('ascii'),warnings=outnotes+errnotes)
    if not hasattr(_state,'evidence'):_state.evidence=[]
    _state.evidence.append(evidence)
    return Capture(result.returncode,stdout,stderr,result.stdout or b'',result.stderr or b'',outnotes+errnotes)
