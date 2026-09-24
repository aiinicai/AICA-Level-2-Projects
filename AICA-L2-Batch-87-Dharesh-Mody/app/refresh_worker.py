from PySide6.QtCore import QObject, Signal, QThread
from . import db
from .scrapers import REGISTRY, SOURCE_URLS


class RefreshWorker(QObject):
    """Runs all five source scrapers sequentially on a background thread and
    reports progress line-by-line so the GUI never freezes during a refresh."""
    progress = Signal(str)          # one log line per source
    source_done = Signal(str, bool, str)  # key, ok, message
    finished = Signal(int, int)     # ok_count, blocked_count

    def __init__(self, keys=None):
        super().__init__()
        self.keys = keys or list(REGISTRY.keys())

    def run(self):
        ok = blocked = 0
        for key in self.keys:
            module, name, official, _needs_browser = REGISTRY[key]
            self.progress.emit(f"Checking {name}…")
            try:
                records, message = module.fetch()
                count = skipped = 0
                for rec in records:
                    if rec.get("name"):
                        # Same rule as app/refresh.py: skip only brand-new
                        # companies this source has no open/close date for
                        # (likely closed IPOs dropped from the live table).
                        # Companies we already track can still get updates
                        # (e.g. GMP-only rows) from a dateless record.
                        if not db.find_by_name(rec["name"]) and not rec.get("open_date") and not rec.get("close_date"):
                            skipped += 1
                            continue
                        db.merge_incoming(
                            rec, key, name, SOURCE_URLS.get(key, ""),
                            fields="Live scrape", official=official,
                        )
                        count += 1
                if skipped:
                    self.progress.emit(
                        f"{name}: skipped {skipped} row(s) with no open/close date "
                        "(likely closed IPOs no longer listed by the source)"
                    )
                db.log_refresh(name, True, message, count)
                self.progress.emit(f"{name}: {message}")
                self.source_done.emit(key, True, message)
                ok += 1
            except Exception as e:
                msg = str(e)
                db.log_refresh(name, False, msg, 0)
                self.progress.emit(f"{name}: blocked — {msg}")
                self.source_done.emit(key, False, msg)
                blocked += 1
        db.consolidate_duplicates()
        self.finished.emit(ok, blocked)


def run_refresh_in_thread(parent, keys, on_progress, on_source_done, on_finished):
    """Convenience helper: creates the thread+worker pair and wires signals.
    Returns (thread, worker) — caller must keep references alive until finished."""
    thread = QThread(parent)
    worker = RefreshWorker(keys)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.progress.connect(on_progress)
    worker.source_done.connect(on_source_done)
    worker.finished.connect(on_finished)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread, worker
