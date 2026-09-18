"""Folder watcher: automatically process documents dropped into an Incoming
folder, using an explicitly configured and consented template/workflow.

**Disabled by default in every sense** -- there is no code path anywhere in
this module that starts watching without an explicit, populated
:class:`WatcherConsent` with ``enabled=True`` and a non-empty
``acknowledgement_text`` recording what the user agreed to. This is the
"future version can monitor an Incoming folder" feature described in the
project brief, built now with the safety gating it always required.

Deliberately polling-based rather than OS-level filesystem-event watching
(``watchdog``): a fixed-interval scan is simpler to reason about, is what
naturally implements "wait for the file copy to finish" (a file is only
processed once its size is stable across two consecutive scans), and is
trivially unit-testable by calling :meth:`FolderWatcherService.scan_once`
directly against a temp directory -- no background OS watcher thread timing
to fight with in tests. ``watchdog`` remains available as a dependency for
a future event-driven mode if lower latency is ever needed.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from utils.validation import ValidationError


@dataclass
class WatcherConsent:
    """Explicit, informed configuration -- every field must be deliberately
    set; there is no "just turn it on" default that signs/processes anything."""

    enabled: bool = False
    incoming_folder: str = ""
    processing_folder: str = ""
    review_folder: str = ""
    done_folder: str = ""
    failed_folder: str = ""
    allowed_extensions: tuple[str, ...] = (".pdf",)
    template_description: str = ""  # human-readable description of what will be applied, shown in the consent UI
    max_files_per_run: int = 0  # 0 = unlimited
    valid_until: datetime | None = None  # None = no expiry
    acknowledged_by: str = ""
    acknowledged_at: datetime | None = None
    acknowledgement_text: str = ""  # the exact text the user was shown and agreed to

    def validate(self) -> None:
        if not self.enabled:
            raise ValidationError("The folder watcher is not enabled.")
        if not self.acknowledgement_text or not self.acknowledged_by:
            raise ValidationError(
                "The folder watcher requires explicit, recorded user consent "
                "(who acknowledged it, and the exact text they agreed to) before it can run."
            )
        for folder_attr in ("incoming_folder", "processing_folder", "done_folder", "failed_folder"):
            value = getattr(self, folder_attr)
            if not value:
                raise ValidationError(f"'{folder_attr}' must be configured before the watcher can run.")
        if self.valid_until is not None and datetime.now(timezone.utc) > self.valid_until:
            raise ValidationError("This watcher's consent has expired. Reconfigure and re-acknowledge it to continue.")


@dataclass
class ProcessOutcome:
    source_filename: str
    success: bool
    output_path: str = ""
    error_message: str = ""
    processed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


ProcessFn = Callable[[Path], Path]  # takes an incoming file path, returns the produced output path; raises on failure


class FolderWatcherService:
    """Runs `process_fn` on every new, stable, allowed-extension file found in
    ``consent.incoming_folder``, honouring a de-duplication registry so a
    restart never reprocesses a file it already handled."""

    def __init__(self, consent: WatcherConsent, process_fn: ProcessFn, registry_path: str | Path | None = None):
        self.consent = consent
        self.process_fn = process_fn
        self.registry_path = Path(registry_path) if registry_path else None
        self._seen_hashes: set[str] = self._load_registry()
        self._pending_sizes: dict[str, tuple[int, float]] = {}  # path -> (last_seen_size, last_seen_time)
        self._paused = False

    # ------------------------------------------------------------- registry
    def _load_registry(self) -> set[str]:
        if self.registry_path and self.registry_path.exists():
            try:
                return set(json.loads(self.registry_path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                return set()
        return set()

    def _save_registry(self) -> None:
        if self.registry_path:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            self.registry_path.write_text(json.dumps(sorted(self._seen_hashes)), encoding="utf-8")

    @staticmethod
    def _file_hash(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # --------------------------------------------------------------- control
    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    # ---------------------------------------------------------------- scan
    def _is_stable(self, path: Path) -> bool:
        """A file counts as "finished copying" once its size hasn't changed
        since the previous scan -- callers should call scan_once() on a
        regular interval (e.g. every few seconds) for this to work."""
        try:
            size = path.stat().st_size
        except OSError:
            return False
        now = time.monotonic()
        key = str(path)
        previous = self._pending_sizes.get(key)
        self._pending_sizes[key] = (size, now)
        return previous is not None and previous[0] == size

    def scan_once(self, dry_run: bool = False) -> list[ProcessOutcome]:
        """Process every stable, unprocessed, allowed-extension file found
        right now. Safe to call repeatedly (e.g. from a scheduler/timer)."""
        self.consent.validate()
        if self._paused:
            return []

        incoming = Path(self.consent.incoming_folder)
        processing = Path(self.consent.processing_folder)
        done = Path(self.consent.done_folder)
        failed = Path(self.consent.failed_folder)
        for folder in (incoming, processing, done, failed):
            folder.mkdir(parents=True, exist_ok=True)

        outcomes: list[ProcessOutcome] = []
        candidates = [
            p for p in sorted(incoming.iterdir())
            if p.is_file() and p.suffix.lower() in self.consent.allowed_extensions
        ]
        if self.consent.max_files_per_run:
            candidates = candidates[: self.consent.max_files_per_run]

        for path in candidates:
            if not self._is_stable(path):
                continue  # still being copied -- try again next scan

            file_hash = self._file_hash(path)
            if file_hash in self._seen_hashes:
                continue  # already processed in a previous run (e.g. before a restart)

            if dry_run:
                outcomes.append(ProcessOutcome(source_filename=path.name, success=True, output_path="(dry run -- not processed)"))
                continue

            moved_to_processing = processing / path.name
            shutil.move(str(path), str(moved_to_processing))
            try:
                output_path = self.process_fn(moved_to_processing)
                final_path = done / Path(output_path).name
                shutil.move(str(output_path), str(final_path))
                outcomes.append(ProcessOutcome(source_filename=path.name, success=True, output_path=str(final_path)))
                self._seen_hashes.add(file_hash)
            except Exception as exc:  # noqa: BLE001 - one bad file must not stop the watcher or crash silently
                failed_path = failed / path.name
                try:
                    shutil.move(str(moved_to_processing), str(failed_path))
                except OSError:
                    pass
                outcomes.append(ProcessOutcome(source_filename=path.name, success=False, error_message=str(exc)))
            finally:
                self._pending_sizes.pop(str(path), None)

        self._save_registry()
        return outcomes
