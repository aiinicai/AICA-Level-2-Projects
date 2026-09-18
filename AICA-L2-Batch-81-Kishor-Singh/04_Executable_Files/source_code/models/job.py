"""Batch-processing job models shared between workers and the UI."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from models.enums import JobStatus


@dataclass
class SigningJob:
    """One PDF (or Word document destined to become a PDF) in a batch run."""

    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_path: str = ""
    output_path: str = ""
    total_pages: int = 0
    selected_pages: str = ""  # resolved page list, comma-joined, for display/report
    position_label: str = ""
    template_used: str = ""
    status: JobStatus = JobStatus.PENDING
    error_message: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def file_name(self) -> str:
        from pathlib import Path

        return Path(self.source_path).name if self.source_path else ""

    @property
    def folder(self) -> str:
        from pathlib import Path

        return str(Path(self.source_path).parent) if self.source_path else ""

    @property
    def output_file_name(self) -> str:
        from pathlib import Path

        return Path(self.output_path).name if self.output_path else ""


@dataclass
class BatchResult:
    """Summary produced after a batch run finishes, feeding the report dialog."""

    jobs: list[SigningJob] = field(default_factory=list)
    output_folder: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None

    @property
    def total(self) -> int:
        return len(self.jobs)

    @property
    def succeeded(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.SUCCESS)

    @property
    def failed(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.FAILED)

    @property
    def skipped(self) -> int:
        return sum(1 for j in self.jobs if j.status == JobStatus.SKIPPED)

    def failed_jobs(self) -> list[SigningJob]:
        return [j for j in self.jobs if j.status == JobStatus.FAILED]
