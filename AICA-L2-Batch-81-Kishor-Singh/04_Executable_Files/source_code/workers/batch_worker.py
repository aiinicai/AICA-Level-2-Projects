"""Generic, cancellable background batch worker.

A single :class:`BatchWorker` drives any batch operation (signing, Word
conversion, splitting, workflow execution, ...) by calling a supplied
``process_fn(job)`` once per :class:`SigningJob`, off the GUI thread, and
reporting progress/results back to Qt via signals. This keeps the UI
responsive for 10, 100 or 500+ files and gives every tab consistent
progress/cancel/retry behaviour for free.
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Callable

from PySide6.QtCore import QThread, Signal

from models.enums import JobStatus
from models.job import BatchResult, SigningJob
from utils.logging_utils import get_logger

logger = get_logger("batch_worker")

ProcessFn = Callable[[SigningJob], None]


class BatchWorker(QThread):
    """Runs ``process_fn`` for each job in ``jobs`` sequentially on a worker thread.

    ``process_fn`` must mutate the passed :class:`SigningJob` in place
    (setting ``total_pages``, ``selected_pages`` etc. on success) and may
    raise any exception on failure -- the worker catches it, records
    ``error_message`` and marks the job FAILED without aborting the batch.
    """

    progress_changed = Signal(int, int, str)  # completed, total, current_filename
    job_finished = Signal(object)  # SigningJob
    batch_finished = Signal(object)  # BatchResult
    fatal_error = Signal(str)

    def __init__(self, jobs: list[SigningJob], process_fn: ProcessFn, output_folder: str = "", parent=None):
        super().__init__(parent)
        self.jobs = jobs
        self.process_fn = process_fn
        self.output_folder = output_folder
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run(self) -> None:  # noqa: D102 - Qt override
        # Initialize COM on this thread in case process_fn drives Word via
        # pywin32 (win32com requires COM to be initialized per-thread).
        com_initialized = False
        try:
            import pythoncom

            pythoncom.CoInitialize()
            com_initialized = True
        except ImportError:
            pass

        total = len(self.jobs)
        result = BatchResult(output_folder=self.output_folder, started_at=datetime.now())
        try:
            for index, job in enumerate(self.jobs, start=1):
                if self._cancel_event.is_set():
                    job.status = JobStatus.CANCELLED
                    result.jobs.append(job)
                    continue

                self.progress_changed.emit(index - 1, total, job.file_name)
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.now()
                try:
                    self.process_fn(job)
                    if job.status == JobStatus.PROCESSING:  # process_fn didn't set a terminal status
                        job.status = JobStatus.SUCCESS
                except Exception as exc:  # noqa: BLE001 - one file's failure must not kill the batch
                    job.status = JobStatus.FAILED
                    job.error_message = str(exc)
                    logger.error("Job failed for '%s': %s", job.file_name, exc)
                finally:
                    job.finished_at = datetime.now()
                    result.jobs.append(job)
                    self.job_finished.emit(job)
                    self.progress_changed.emit(index, total, job.file_name)
        except Exception as exc:  # noqa: BLE001 - defensive: never let the thread die silently
            logger.exception("Fatal error in batch worker")
            self.fatal_error.emit(str(exc))
        finally:
            if com_initialized:
                import pythoncom

                pythoncom.CoUninitialize()
            result.finished_at = datetime.now()
            self.batch_finished.emit(result)


def build_retry_worker(previous_result: BatchResult, process_fn: ProcessFn) -> BatchWorker:
    """Build a new :class:`BatchWorker` covering only the failed jobs from a prior run."""
    failed = previous_result.failed_jobs()
    for job in failed:
        job.status = JobStatus.PENDING
        job.error_message = ""
    return BatchWorker(failed, process_fn, output_folder=previous_result.output_folder)
