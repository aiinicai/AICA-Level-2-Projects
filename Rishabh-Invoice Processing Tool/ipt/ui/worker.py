"""Run a service call in the thread pool so the window stays responsive."""
from __future__ import annotations

import logging
import traceback

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

log = logging.getLogger(__name__)


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(str)


class Job(QRunnable):
    """Job(fn, *args, **kwargs). If fn accepts a 'progress' keyword, pass with_progress=True."""

    def __init__(self, fn, *args, with_progress: bool = False, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = _Signals()
        if with_progress:
            self.kwargs["progress"] = self.signals.progress.emit

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:  # noqa: BLE001 - every failure is shown to the user
            log.warning("Background job failed: %s\n%s", e, traceback.format_exc())
            self.signals.failed.emit(str(e) or e.__class__.__name__)
            return
        self.signals.done.emit(result)


def start(job: Job, on_done=None, on_failed=None, on_progress=None) -> Job:
    if on_done:
        job.signals.done.connect(on_done)
    if on_failed:
        job.signals.failed.connect(on_failed)
    if on_progress:
        job.signals.progress.connect(on_progress)
    QThreadPool.globalInstance().start(job)
    return job
