"""Screenshots of the main pages in both themes, plus a repaint timing."""
import importlib.util, os, shutil, sys, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
WORK = "/home/claude/pytest/uwork"
shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK)
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "appdata")
spec = importlib.util.spec_from_file_location("bcg", "/home/claude/balance_confirmation_generator.py")
bcg = importlib.util.module_from_spec(spec); sys.modules["bcg"] = bcg; spec.loader.exec_module(bcg)
from PyQt6.QtWidgets import QApplication, QMessageBox, QScrollArea
from PyQt6.QtCore import QDate, QEvent
QMessageBox.exec = lambda self: QMessageBox.StandardButton.Ok
app = QApplication([]); app.setStyle("Fusion"); app.setPalette(bcg.qt_palette()); app.setStyleSheet(bcg.style_sheet())
win = bcg.MainWindow(); win.resize(1500, 950); win.show()
def pump(n=6):
    for _ in range(n):
        app.processEvents(); app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
pump()
win.cl_name.setText("Example Manufacturing Private Limited"); win.add_client()
win.active_client()["signatory_name"] = "Mr. R. Mehta"; win.active_client()["signatory_designation"] = "Director"
win.db["settings"]["firm_name"] = "Ankit & Associates"; win.db["settings"]["partner_name"] = "CA Ankit Soni"
win.fy_year.setText("2025-26"); win.fy_end.setDate(QDate(2026, 3, 31)); win.add_year()
win.aud_name.setText("Audit team"); win.aud_email.setText("audit@firm.example"); win.add_auditor()
tpl = win.download_sample_template(path=os.path.join(WORK, "template.xlsx"))
win.load_file(tpl); pump()
out = os.path.join(WORK, "out"); os.makedirs(out); win.db["settings"]["output_folder"] = out
confs = [win.to_confirmation(r) for r in win.validation()["generable"]]
folder = win.run_output_folder(); os.makedirs(folder, exist_ok=True)
worker = bcg.GenerateWorker(confs, folder); got = []; worker.produced.connect(got.append); worker.run()
win.generated = got; win.save_run(folder)
docs = win.db["runs"][0]["documents"]
for i, d in enumerate(docs):
    d["email_status"] = "sent"; d["sent_at"] = "2026-10-20"; d["thread_id"] = "t%d" % i
win.db["replies"] = [
 {"id": "r0", "thread_id": "t0", "from_email": "accounts@abc-example.com", "subject": "Re: Balance confirmation", "in_reply_to": "<a>", "received_at": "2026-11-02",
  "body": "We confirm the balance of INR 79,60,098.48 is correct.", "attachments": []},
 {"id": "r1", "thread_id": "t1", "from_email": "finance@xyz-example.com", "subject": "Re: Balance confirmation", "in_reply_to": "<b>", "received_at": "2026-11-03",
  "body": "As per our books the balance is Rs. 25,00,000 only.", "attachments": []},
]
win.persist()
os.makedirs("/home/claude/pytest/final", exist_ok=True)
for mode in ("dark", "light"):
    bcg.apply_theme(app, mode); win.refresh_theme_button(); win.style_paper(); win.restyle(); pump()
    for page in ("dashboard", "import", "generate", "email", "recon"):
        win.go(page); pump(10)
        if page == "recon":
            i = win.report_combo.findData(bcg.REPORT_COMPARISON); win.report_combo.setCurrentIndex(i); pump(6)
        if page == "email":
            for area in win.findChildren(QScrollArea):
                bar = area.verticalScrollBar()
                if bar.maximum() and area.isVisible(): bar.setValue(bar.maximum())
            pump(8)
        path = "/home/claude/pytest/final/ui-%s-%s.png" % (page, mode)
        win.grab().save(path); print("wrote", path)
# repaint cost of a table inside a shadowed card
win.go("recon"); pump(10)
t = win.report_table
def cost():
    start = time.perf_counter()
    for _ in range(30):
        t.viewport().update(); win.repaint()
    return (time.perf_counter() - start) / 30 * 1000
print("repaint ms with shadows: %.1f" % cost())
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
for w in app.allWidgets():
    if isinstance(w.graphicsEffect(), QGraphicsDropShadowEffect): w.setGraphicsEffect(None)
pump()
print("repaint ms without:      %.1f" % cost())
