"""
bridge.py — QObject exposed to JavaScript via QWebChannel as 'bridge'.

Only handles WRITES (save_key / remove_all) plus a reload request.
READS happen once at boot, via boot data injected directly into the page
HTML by main.py — see db.py and main.py for details on why.

All writes are scoped to whichever company is currently open (self.company_id),
so data for different clients never mixes. main.py updates company_id via
set_company() whenever the user switches companies.
"""
from PySide6.QtCore import QObject, Slot


class Bridge(QObject):
    def __init__(self, db, on_reload_requested, company_id: int = None):
        super().__init__()
        self._db = db
        self._on_reload_requested = on_reload_requested
        self.company_id = company_id

    def set_company(self, company_id: int):
        self.company_id = company_id

    @Slot(str, str)
    def save_key(self, key: str, value_json: str):
        if self.company_id is None:
            print("[bridge] save_key called with no company selected — ignored")
            return
        try:
            self._db.save_key(self.company_id, key, value_json)
        except Exception as e:
            print(f"[bridge] save_key error for '{key}': {e}")

    @Slot()
    def remove_all(self):
        if self.company_id is None:
            return
        try:
            self._db.remove_all_keys(self.company_id)
        except Exception as e:
            print(f"[bridge] remove_all error: {e}")

    @Slot()
    def request_reload(self):
        # Reset Application was just called — the underlying SQLite data is
        # now empty. A plain JS location.reload() would replay the SAME
        # already-loaded HTML string (with its now-stale boot data), so the
        # host window must actually rebuild + reload the page from Python.
        self._on_reload_requested()
