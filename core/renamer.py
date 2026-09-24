"""
Renaming engine for TDS & TCS Certificate PDF Auto-Renamer.
Handles template interpolation, Windows filename sanitization, collision avoidance,
and safe execution modes (in-place rename, copy, move).
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, Set, List, Optional, Tuple

from core.models import CertificateData, ProcessingStatus
from config import (
    COLLISION_AUTO_INCREMENT,
    COLLISION_DISAMBIGUATE,
    COLLISION_SKIP,
    COLLISION_OVERWRITE,
    MODE_RENAME_IN_PLACE,
    MODE_COPY_TO_FOLDER,
    MODE_MOVE_TO_FOLDER,
)


class CertificateRenamer:
    """Manages filename generation, collision resolution, and file operations."""

    def __init__(
        self,
        template: str = "{DeducteeName}",
        collision_policy: str = COLLISION_AUTO_INCREMENT,
        execution_mode: str = MODE_RENAME_IN_PLACE,
        output_folder: Optional[Path] = None,
        max_length: int = 120,
    ):
        self.template = template
        self.collision_policy = collision_policy
        self.execution_mode = execution_mode
        self.output_folder = Path(output_folder) if output_folder else None
        self.max_length = max_length

    def sanitize_filename(self, filename: str) -> str:
        """Strip illegal Windows filename characters and normalize whitespace."""
        # Illegal characters in Windows filenames: \ / : * ? " < > |
        cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)
        # Collapse multiple spaces and underscores
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"_+", "_", cleaned)
        cleaned = cleaned.strip(". ")
        return cleaned

    def format_filename(self, cert: CertificateData) -> str:
        """Format base filename using the active template and certificate metadata."""
        # Fallback if deductee name is not available
        name_val = cert.deductee_name or "UNKNOWN_DEDUCTEE"
        pan_val = cert.deductee_pan or "NOPAN"
        form_val = cert.form_type or "Form"
        code_val = cert.form_code or "TDS"
        act_val = "1961_Act" if "1961" in cert.act else ("2025_Act" if "2025" in cert.act else "Act")
        fy_val = cert.financial_year or "FY"
        ay_val = cert.assessment_year or "AY"
        q_val = cert.quarter or "Quarter"
        certno_val = cert.certificate_no or "NoCert"
        orig_val = Path(cert.original_filename).stem if cert.original_filename else "Document"

        token_map = {
            "{DeducteeName}": name_val,
            "{PAN}": pan_val,
            "{FormType}": form_val,
            "{FormCode}": code_val,
            "{Act}": act_val,
            "{FinancialYear}": fy_val,
            "{AssessmentYear}": ay_val,
            "{Quarter}": q_val,
            "{CertificateNo}": certno_val,
            "{OriginalFilename}": orig_val,
        }

        result = self.template
        for token, val in token_map.items():
            result = result.replace(token, str(val))

        sanitized = self.sanitize_filename(result)
        if not sanitized:
            sanitized = self.sanitize_filename(name_val) or "Renamed_Certificate"

        # Restrict max length (excluding .pdf)
        if len(sanitized) > self.max_length:
            sanitized = sanitized[: self.max_length].strip(". ")

        return f"{sanitized}.pdf"

    def plan_batch(self, certificates: List[CertificateData]) -> List[CertificateData]:
        """
        Generate proposed filenames and resolve collisions across the entire batch
        BEFORE executing any file operations (Dry-Run / Preview).
        """
        assigned_names: Set[str] = set()

        # Determine target directory
        for cert in certificates:
            if cert.status == ProcessingStatus.ERROR and not cert.deductee_name:
                cert.proposed_filename = cert.original_filename
                continue

            target_dir = self._get_target_directory(cert)
            base_filename = self.format_filename(cert)
            stem = Path(base_filename).stem
            suffix = Path(base_filename).suffix

            resolved_filename = self._resolve_collision(
                target_dir=target_dir,
                stem=stem,
                suffix=suffix,
                cert=cert,
                assigned_names=assigned_names,
            )

            cert.proposed_filename = resolved_filename
            cert.final_filepath = target_dir / resolved_filename
            assigned_names.add(resolved_filename.lower())
            cert.status = ProcessingStatus.PREVIEW_READY

        return certificates

    def execute_rename(self, cert: CertificateData) -> Tuple[bool, str]:
        """
        Execute renaming / copying for a single certificate based on execution mode.
        Returns: (success: bool, message: str)
        """
        if not cert.proposed_filename:
            return False, "No proposed filename set"

        src_path = Path(cert.file_path)
        if not src_path.exists():
            cert.status = ProcessingStatus.ERROR
            cert.message = f"Source file does not exist: {src_path.name}"
            return False, cert.message

        target_dir = self._get_target_directory(cert)
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_path = target_dir / cert.proposed_filename

        # If source and destination are identical
        if src_path.resolve() == dest_path.resolve():
            cert.status = ProcessingStatus.SKIPPED
            cert.message = "Filename already matches proposed name"
            return True, cert.message

        try:
            if self.execution_mode == MODE_RENAME_IN_PLACE:
                # In-place rename (atomic if same volume)
                src_path.rename(dest_path)
                cert.final_filepath = dest_path
                cert.status = ProcessingStatus.RENAMED
                cert.message = f"Renamed to {dest_path.name}"
                return True, cert.message

            elif self.execution_mode == MODE_COPY_TO_FOLDER:
                # Copy without altering source
                shutil.copy2(str(src_path), str(dest_path))
                cert.final_filepath = dest_path
                cert.status = ProcessingStatus.COPIED
                cert.message = f"Copied to {dest_path.name}"
                return True, cert.message

            elif self.execution_mode == MODE_MOVE_TO_FOLDER:
                # Move to separate folder
                shutil.move(str(src_path), str(dest_path))
                cert.final_filepath = dest_path
                cert.status = ProcessingStatus.MOVED
                cert.message = f"Moved to {dest_path.name}"
                return True, cert.message

        except Exception as e:
            cert.status = ProcessingStatus.ERROR
            cert.message = f"Operation failed: {str(e)}"
            return False, cert.message

        return False, "Unknown execution mode"

    # ==========================================================================
    # COLLISION RESOLUTION LOGIC
    # ==========================================================================

    def _get_target_directory(self, cert: CertificateData) -> Path:
        """Determine target directory based on execution mode."""
        if self.execution_mode in (MODE_COPY_TO_FOLDER, MODE_MOVE_TO_FOLDER) and self.output_folder:
            return self.output_folder
        return Path(cert.file_path).parent

    def _resolve_collision(
        self,
        target_dir: Path,
        stem: str,
        suffix: str,
        cert: CertificateData,
        assigned_names: Set[str],
    ) -> str:
        """Resolve potential name collisions on disk and within the batch."""
        candidate = f"{stem}{suffix}"
        cand_lower = candidate.lower()

        # Check if file exists on disk (and is not the source itself) OR already assigned in batch
        src_resolved = Path(cert.file_path).resolve()
        dest_path = target_dir / candidate

        collision = (cand_lower in assigned_names) or (
            dest_path.exists() and dest_path.resolve() != src_resolved
        )

        if not collision:
            return candidate

        # Collision detected! Apply selected collision policy
        if self.collision_policy == COLLISION_DISAMBIGUATE:
            # Append Quarter and PAN e.g., NAME_Q2_ABCDE1234F.pdf
            extra_parts = [p for p in [cert.quarter, cert.deductee_pan] if p]
            if extra_parts:
                new_stem = f"{stem}_{'_'.join(extra_parts)}"
                return self._find_unique_increment(target_dir, new_stem, suffix, src_resolved, assigned_names)

        if self.collision_policy == COLLISION_SKIP:
            return cert.original_filename

        # Default policy: Auto-Increment (1), (2), etc.
        return self._find_unique_increment(target_dir, stem, suffix, src_resolved, assigned_names)

    def _find_unique_increment(
        self,
        target_dir: Path,
        stem: str,
        suffix: str,
        src_resolved: Path,
        assigned_names: Set[str],
    ) -> str:
        """Find next available increment `Name (1).pdf`, `Name (2).pdf`, etc."""
        counter = 1
        while True:
            candidate = f"{stem} ({counter}){suffix}"
            cand_lower = candidate.lower()
            dest_path = target_dir / candidate
            if cand_lower not in assigned_names and (
                not dest_path.exists() or dest_path.resolve() == src_resolved
            ):
                return candidate
            counter += 1
