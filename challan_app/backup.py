"""Consistent backup of the SQLite database into ./backups (uses SQLite's online backup API)."""
import os
import sqlite3
from datetime import datetime

base = os.path.dirname(os.path.abspath(__file__))
inst = os.environ.get("CHALLAN_INSTANCE", os.path.join(base, "instance"))
src = os.path.join(inst, "challan.db")
os.makedirs(os.path.join(base, "backups"), exist_ok=True)
dst = os.path.join(base, "backups", f"challan_{datetime.now():%Y%m%d_%H%M%S}.db")
s, d = sqlite3.connect(src), sqlite3.connect(dst)
with d:
    s.backup(d)
s.close(); d.close()
files = sorted(os.listdir(os.path.join(base, "backups")))
for old in files[:-30]:                    # keep the latest 30
    os.remove(os.path.join(base, "backups", old))
print("Backup written:", dst)
