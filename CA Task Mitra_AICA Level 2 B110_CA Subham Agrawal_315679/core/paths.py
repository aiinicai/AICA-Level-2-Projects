import os, sys

FROZEN = getattr(sys, "frozen", False)
_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = getattr(sys, "_MEIPASS", _here)                      # bundled read-only files (web/)
APP = os.path.dirname(sys.executable) if FROZEN else _here  # folder holding the EXE
DATA = os.environ.get("WD_DATA") or os.path.join(APP, "data")
for _d in ("", "backups", "outbox", "exports"):
    os.makedirs(os.path.join(DATA, _d), exist_ok=True)
DBFILE = os.path.join(DATA, "workdesk.db")
WEB = os.path.join(RES, "web")
