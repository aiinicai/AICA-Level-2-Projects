"""Builds ONE self-contained file  CA_Task_Mitra_Share.py  that you can send on WhatsApp / e-mail.
Run:  python make_share.py      (no data, passwords or database are included)"""
import base64, io, os, zipfile
SKIP = {"__pycache__", "data", "dist", "build", ".git", "screenshots"}
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, 9) as z:
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            if f.endswith((".pyc", ".exe")) or f in ("make_share.py", "CA_Task_Mitra_Share.py"):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, "."))
blob = base64.b64encode(buf.getvalue()).decode()
lines = "\n".join(blob[i:i + 100] for i in range(0, len(blob), 100))
open("CA_Task_Mitra_Share.py", "w", encoding="utf-8").write('''"""CA Task Mitra - single-file test copy.  Needs Python 3.10+ only.
Double-click this file (or run:  python CA_Task_Mitra_Share.py).
First run unpacks the app into a folder "CA-Task-Mitra-app" next to this file, then starts it in Chrome.
Use only the fictional demo data - no real client data."""
import base64, io, os, sys, zipfile
BLOB = """
%s
"""
here = os.path.dirname(os.path.abspath(__file__))
app = os.path.join(here, "CA-Task-Mitra-app")
if not os.path.isfile(os.path.join(app, "run.py")):
    zipfile.ZipFile(io.BytesIO(base64.b64decode("".join(BLOB.split())))).extractall(app)
    print("Unpacked to", app)
os.chdir(app)
sys.path.insert(0, app)
sys.argv = ["run.py"] + sys.argv[1:]
exec(compile(open("run.py", encoding="utf-8").read(), "run.py", "exec"), {"__name__": "__main__"})
''' % lines)
print("Created CA_Task_Mitra_Share.py (%d KB)" % (os.path.getsize("CA_Task_Mitra_Share.py") // 1024))
