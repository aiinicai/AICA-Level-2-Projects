"""v2.3.4: GST portal buttons on the review tab and in the Edit line window:  python -m tests.test_v234"""
import os, sys, tempfile
from pathlib import Path
os.environ["CAGST_DATA"] = str(Path(tempfile.mkdtemp()) / "data")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests import tk_stub  # noqa: E402
tk_stub.install()
from app import ui  # noqa: E402

opened, clip, shown = [], [], []
ui.webbrowser.open = lambda url: opened.append(url)
ui.messagebox.showinfo = lambda *a, **k: shown.append(a)


class L:
    def __init__(self, i, g, h):
        self.id, self.recipient_gstin, self.hsn, self.description = i, g, h, "Boxes"


class Fake:
    _open_portal = ui.App._open_portal
    check_gstin_online = ui.App.check_gstin_online
    lookup_hsn_online = ui.App.lookup_hsn_online
    def __init__(self, sel): self.sel = sel; self.status = ""
    def _sel_lines(self): return self.sel
    def clipboard_clear(self): clip.clear()
    def clipboard_append(self, t): clip.append(t)
    def set_status(self, t): self.status = t


a = Fake([L(8, "33abcde1234f1zl", "39231090")])
a.check_gstin_online()
assert opened[-1].endswith("/searchtp") and clip == ["33ABCDE1234F1ZL"] and "Ctrl" not in a.status and "copied" in a.status
a.lookup_hsn_online()
assert opened[-1].endswith("/searchhsnsac") and clip == ["39231090"]
# from the Edit window: the typed (unsaved) value is used
a.check_gstin_online(" 33xyzab1234c1z5 ")
assert clip == ["33XYZAB1234C1Z5"]
a.lookup_hsn_online("")
assert opened[-1].endswith("/searchhsnsac")
# unregistered line: message, portal still opens
n = len(opened)
Fake([L(5, "", "39231090")]).check_gstin_online()
assert shown and len(opened) == n + 1
# the buttons are wired: third row on tab 6, and in the edit dialog
src = open(ui.__file__, encoding="utf8").read()
assert "bar3 = ttk.Frame(f)" in src and src.index('("Check GSTIN on GST portal", self.check_gstin_online)') > src.index("bar3 =")
assert "extra_buttons=[(\"Check GSTIN on GST portal\"" in src
print("ALL v2.3.4 TESTS PASSED")
