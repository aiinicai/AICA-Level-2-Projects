"""
Batch Processor for TDS & TCS Certificate PDF Auto-Renamer.
Provides both a PyQt6 QThread worker for smooth, non-blocking UI updates
and a pure Python synchronous runner for command-line automation.
"""

import time
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

from core.models import CertificateData, ProcessingStatus
from core.classifier import CertificateClassifier
from core.extractor import CertificateExtractor
from core.renamer import CertificateRenamer
from core.undo_manager import UndoManager
from config import AppConfig, ACT_1961, ACT_2025


class BatchWorkerThread(QThread):
    """
    QThread worker for executing batch extraction and renaming operations
    without freezing the PyQt6 GUI.
    """

    # Signals
    progress_changed = pyqtSignal(int, int, str)  # current, total, filename
    item_analyzed = pyqtSignal(object)           # CertificateData
    item_renamed = pyqtSignal(object)            # CertificateData
    log_message = pyqtSignal(str, str)           # level ('INFO', 'WARNING', 'ERROR', 'SUCCESS'), message
    batch_finished = pyqtSignal(dict)            # summary dict

    def __init__(
        self,
        files: List[Path],
        config: AppConfig,
        phase: str = "analyze",  # "analyze" or "rename"
        existing_certs: Optional[List[CertificateData]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.files = files
        self.config = config
        self.phase = phase
        self.existing_certs = existing_certs or []
        self._is_cancelled = False

        self.classifier = CertificateClassifier()
        self.extractor = CertificateExtractor(
            classifier=self.classifier,
            enable_ocr=self.config.enable_ocr_fallback,
        )
        self.renamer = CertificateRenamer(
            template=self.config.naming_template,
            collision_policy=self.config.collision_policy,
            execution_mode=self.config.execution_mode,
            output_folder=Path(self.config.output_folder) if self.config.output_folder else None,
            max_length=self.config.max_filename_length,
        )
        self.undo_manager = UndoManager()

    def cancel(self):
        """Signal thread to gracefully cancel operation."""
        self._is_cancelled = True

    def run(self):
        """Execute either analysis phase or rename phase."""
        if self.phase == "analyze":
            self._run_analysis()
        elif self.phase == "rename":
            self._run_rename()

    def _run_analysis(self):
        total = len(self.files)
        self.log_message.emit("INFO", f"Starting batch analysis of {total} PDF files...")
        start_time = time.perf_counter()

        analyzed_certs: List[CertificateData] = []
        act_1961_count = 0
        act_2025_count = 0
        success_count = 0
        error_count = 0

        for idx, file_path in enumerate(self.files, start=1):
            if self._is_cancelled:
                self.log_message.emit("WARNING", "Batch analysis cancelled by user.")
                break

            self.progress_changed.emit(idx, total, file_path.name)

            # Extract certificate metadata
            cert = self.extractor.extract(file_path)

            if cert.status != ProcessingStatus.ERROR and cert.deductee_name:
                success_count += 1
                if "1961" in cert.act:
                    act_1961_count += 1
                elif "2025" in cert.act:
                    act_2025_count += 1
                self.log_message.emit(
                    "SUCCESS",
                    f"[{cert.form_type} | {cert.act}] Extracted: {cert.deductee_name} (PAN: {cert.deductee_pan or 'N/A'}) - {file_path.name}",
                )
            else:
                error_count += 1
                self.log_message.emit(
                    "WARNING",
                    f"Could not extract deductee name from {file_path.name}: {cert.message}",
                )

            analyzed_certs.append(cert)
            self.item_analyzed.emit(cert)

        # Plan proposed filenames and resolve collisions
        self.log_message.emit("INFO", "Resolving filename collisions and preparing preview...")
        self.renamer.plan_batch(analyzed_certs)

        elapsed = round(time.perf_counter() - start_time, 2)
        summary = {
            "phase": "analyze",
            "total": total,
            "processed": len(analyzed_certs),
            "success": success_count,
            "errors": error_count,
            "act_1961_count": act_1961_count,
            "act_2025_count": act_2025_count,
            "elapsed_seconds": elapsed,
            "cancelled": self._is_cancelled,
        }
        self.log_message.emit("INFO", f"Batch analysis complete in {elapsed}s. Valid: {success_count}, Issues: {error_count}")
        self.batch_finished.emit(summary)

    def _run_rename(self):
        targets = [c for c in self.existing_certs if c.status != ProcessingStatus.ERROR and c.proposed_filename]
        total = len(targets)
        self.log_message.emit("INFO", f"Starting batch rename execution for {total} files...")
        start_time = time.perf_counter()

        renamed_count = 0
        skipped_count = 0
        error_count = 0
        completed_certs: List[CertificateData] = []

        for idx, cert in enumerate(targets, start=1):
            if self._is_cancelled:
                self.log_message.emit("WARNING", "Batch rename cancelled by user.")
                break

            self.progress_changed.emit(idx, total, cert.original_filename)

            success, msg = self.renamer.execute_rename(cert)
            if success:
                if cert.status == ProcessingStatus.SKIPPED:
                    skipped_count += 1
                    self.log_message.emit("INFO", f"Skipped {cert.original_filename}: {msg}")
                else:
                    renamed_count += 1
                    self.log_message.emit("SUCCESS", f"Renamed: {cert.original_filename} -> {cert.proposed_filename}")
                completed_certs.append(cert)
            else:
                error_count += 1
                self.log_message.emit("ERROR", f"Failed {cert.original_filename}: {msg}")

            self.item_renamed.emit(cert)

        # Record undo session if any files were renamed/copied
        session_id = ""
        if completed_certs:
            folder_str = str(Path(completed_certs[0].file_path).parent)
            session_id = self.undo_manager.record_session(
                folder_path=folder_str,
                certificates=completed_certs,
                mode=self.config.execution_mode,
            )
            self.log_message.emit("INFO", f"Saved rollback checkpoint: {session_id}")

        elapsed = round(time.perf_counter() - start_time, 2)
        summary = {
            "phase": "rename",
            "total": total,
            "renamed": renamed_count,
            "skipped": skipped_count,
            "errors": error_count,
            "session_id": session_id,
            "elapsed_seconds": elapsed,
            "cancelled": self._is_cancelled,
        }
        self.log_message.emit("INFO", f"Rename execution complete in {elapsed}s. Renamed: {renamed_count}, Skipped: {skipped_count}, Errors: {error_count}")
        self.batch_finished.emit(summary)


# ==============================================================================
# CLI SYNCHRONOUS RUNNER
# ==============================================================================
class BatchProcessorCLI:
    """Synchronous processor for headless command-line execution."""

    def __init__(self, config: AppConfig, log_callback: Optional[Callable[[str, str], None]] = None):
        self.config = config
        self.log_callback = log_callback or (lambda lvl, msg: print(f"[{lvl}] {msg}"))
        self.classifier = CertificateClassifier()
        self.extractor = CertificateExtractor(self.classifier, enable_ocr=config.enable_ocr_fallback)
        self.renamer = CertificateRenamer(
            template=config.naming_template,
            collision_policy=config.collision_policy,
            execution_mode=config.execution_mode,
            output_folder=Path(config.output_folder) if config.output_folder else None,
            max_length=config.max_filename_length,
        )
        self.undo_manager = UndoManager()

    def process_directory(self, folder: Path, dry_run: bool = False) -> List[CertificateData]:
        folder = Path(folder)
        pattern = "**/*.pdf" if self.config.include_subfolders else "*.pdf"
        pdf_files = list(folder.glob(pattern))

        self.log_callback("INFO", f"Found {len(pdf_files)} PDF files in {folder}")

        # Analyze
        certs: List[CertificateData] = []
        for p in pdf_files:
            c = self.extractor.extract(p)
            certs.append(c)

        # Plan
        self.renamer.plan_batch(certs)

        if dry_run:
            self.log_callback("INFO", "Dry-run complete. No files were modified.")
            return certs

        # Execute
        renamed_count = 0
        for c in certs:
            if c.status != ProcessingStatus.ERROR:
                success, msg = self.renamer.execute_rename(c)
                if success:
                    renamed_count += 1
                    self.log_callback("SUCCESS", f"{c.original_filename} -> {c.proposed_filename}")
                else:
                    self.log_callback("ERROR", f"{c.original_filename}: {msg}")

        if renamed_count > 0:
            session_id = self.undo_manager.record_session(
                folder_path=str(folder),
                certificates=certs,
                mode=self.config.execution_mode,
            )
            self.log_callback("INFO", f"Audit checkpoint saved: {session_id}")

        return certs
