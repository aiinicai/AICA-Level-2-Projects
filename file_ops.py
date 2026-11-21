"""Atomic, validated local writes with clean failure reporting."""
import json,os,tempfile
from pathlib import Path

def validate_destination(path,suffix=None):
    dest=Path(path).expanduser()
    if not str(path).strip() or dest.is_dir():raise ValueError('Choose a file name, not a directory.')
    if not dest.parent.is_dir():raise ValueError('The output folder does not exist. Choose an existing folder.')
    if suffix and dest.suffix.lower()!=suffix:raise ValueError('Choose a file ending in '+suffix+'.')
    return dest

def atomic_write(path,writer,suffix=None):
    dest=validate_destination(path,suffix);temporary=None
    try:
        fd,name=tempfile.mkstemp(prefix='.net_asset_',suffix=dest.suffix,dir=dest.parent);os.close(fd);temporary=Path(name)
        writer(temporary)
        if not temporary.is_file() or temporary.stat().st_size==0:raise ValueError('No output was produced; the previous file was not replaced.')
        temporary.replace(dest);temporary=None
        return dest
    finally:
        if temporary:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass # Never mask the original error or strand the UI busy flag.

def atomic_json(path,data):
    return atomic_write(path,lambda temp:temp.write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8'),'.json')
