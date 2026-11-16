"""Render every page of the app (offscreen) to PNGs for a visual check.
python tools/screens.py <outdir>"""
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
work = tempfile.mkdtemp(prefix="aica_screens_")
os.environ["AICA_FSM_DATA"] = os.path.join(work, "data")

from make_test_data import make_bulk, make_docs  # noqa
from PySide6.QtWidgets import QApplication  # noqa
from aica_fsm import organize, versions  # noqa
from aica_fsm.store import Catalog  # noqa
from aica_fsm.ui.common import STYLE  # noqa
from aica_fsm.ui.main_window import MainWindow, NAV  # noqa

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
root = os.path.join(work, "Demo")
make_bulk(root, 400, seed=3)
make_docs(os.path.join(root, "Docs"))
cat = Catalog()
p = cat.create("Demo Client Files", root)
w = MainWindow(cat)
w.resize(1400, 860)
w.show()
w.set_active(p)


def wait():
    while w.scan_workers:
        app.processEvents()
        time.sleep(0.02)


w.start_scan(p)
wait()
os.remove(os.path.join(root, "Docs", "notes.txt"))
with open(os.path.join(root, "Docs", "new file.txt"), "w") as f:
    f.write("new")
w.start_scan(p)
wait()
db = w.st.db
organize.save_name(db, "Sharma Textiles", "Sharma Textiles Pvt Ltd", os.path.join(work, "Clients", "Sharma"))
organize.save_name(db, "Mehta Exports", "", os.path.join(work, "Clients", "Mehta"))
organize.build_queue(db, w.st.snapshot_id)
versions.analyse(db, w.st.snapshot_id)
w.reload_pages()
for i, name in enumerate(NAV):
    w.nav.setCurrentRow(i)
    if name == "Compare Versions" and w.pages[5].t.rowCount():
        w.pages[5].t.selectRow(0)
    app.processEvents()
    w.grab().save(os.path.join(out, f"{i}_{name.replace(' ', '_')}.png"))
print("saved to", out)
print("window", w.size().width(), "minhint", w.minimumSizeHint().width())
for i, pg in enumerate(w.pages):
    print(NAV[i], pg.minimumSizeHint().width())
print("ctxpath", w.ctx_path.minimumSizeHint().width(), "status", w.statusBar().minimumSizeHint().width(),
      "scanpanel", w.scan_panel.minimumSizeHint().width())
