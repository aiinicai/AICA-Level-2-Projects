"""Batch Workflow: chain multiple engines into one repeatable multi-step job.

A workflow is an ordered list of :class:`WorkflowStep` objects. Each step
consumes the PDF produced by the previous step (the very first step may
instead consume a Word document, for ``CONVERT_WORD_TO_PDF``) and produces a
new intermediate PDF in a shared :class:`~utils.file_utils.TempWorkspace`.
The final step's output is copied to the user-chosen destination.

Example (matches the "Convert & Sign" and "Batch Workflow" requirements)::

    steps = [
        WorkflowStep(WorkflowStepKind.CONVERT_WORD_TO_PDF),
        WorkflowStep(WorkflowStepKind.MERGE_WITH, {"additional_files": ["Annexure.pdf"]}),
        WorkflowStep(WorkflowStepKind.SIGN, {"applications": [signature_application]}),
        WorkflowStep(WorkflowStepKind.ADD_WATERMARK_IMAGE, {"options": seal_options}),
    ]
    final_path = WorkflowEngine().run(input_path, steps, workspace, final_output_path)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from core.merge_engine import MergeItem, merge_pdfs
from core.signature_engine import SignatureApplication, apply_signatures_to_pdf
from core.watermark_engine import (
    ImageWatermarkOptions,
    PageNumberOptions,
    TextWatermarkOptions,
    add_image_watermark,
    add_page_numbers,
    add_text_watermark,
)
from core.word_converter import WordToPdfConverter
from models.enums import WordEngine
from utils.file_utils import TempWorkspace
from utils.validation import ValidationError


class WorkflowStepKind(str, Enum):
    CONVERT_WORD_TO_PDF = "Convert Word to PDF"
    MERGE_WITH = "Merge With Other Documents"
    SIGN = "Apply Signature"
    ADD_WATERMARK_TEXT = "Add Text Watermark"
    ADD_WATERMARK_IMAGE = "Add Image Watermark / Seal"
    ADD_PAGE_NUMBERS = "Add Page Numbers"


@dataclass
class WorkflowStep:
    kind: WorkflowStepKind
    params: dict[str, Any] = field(default_factory=dict)

    def label(self) -> str:
        return self.kind.value


class WorkflowEngine:
    """Executes a linear chain of :class:`WorkflowStep` for one input document."""

    def __init__(self, word_engine: WordEngine = WordEngine.AUTO, libreoffice_path: str = ""):
        self.word_converter = WordToPdfConverter(word_engine, libreoffice_path)

    def run(
        self,
        input_path: str | Path,
        steps: list[WorkflowStep],
        workspace: TempWorkspace,
        final_output_path: str | Path,
    ) -> str:
        if not steps:
            raise ValidationError("Workflow has no steps configured.")

        current = Path(input_path)
        for step in steps:
            current = self._run_step(step, current, workspace)

        final_output_path = Path(final_output_path)
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        final_output_path.write_bytes(current.read_bytes())
        return str(final_output_path)

    def _run_step(self, step: WorkflowStep, current: Path, workspace: TempWorkspace) -> Path:
        kind = step.kind
        params = step.params

        if kind == WorkflowStepKind.CONVERT_WORD_TO_PDF:
            out = workspace.new_file(".pdf")
            result = self.word_converter.convert(current, out)
            return Path(result.output_path)

        if kind == WorkflowStepKind.MERGE_WITH:
            additional: list[str] = params.get("additional_files", [])
            page_expr_map: dict[str, str] = params.get("page_expression_map", {})
            append_after: bool = params.get("append_after", True)
            items = [MergeItem(str(current), page_expr_map.get(str(current), "all"))]
            others = [MergeItem(f, page_expr_map.get(f, "all")) for f in additional]
            merge_items = items + others if append_after else others + items
            out = workspace.new_file(".pdf")
            result = merge_pdfs(merge_items, out)
            return Path(result.output_path)

        if kind == WorkflowStepKind.SIGN:
            applications: list[SignatureApplication] = params.get("applications", [])
            out = workspace.new_file(".pdf")
            apply_signatures_to_pdf(current, out, applications)
            return out

        if kind == WorkflowStepKind.ADD_WATERMARK_TEXT:
            options: TextWatermarkOptions = params.get("options", TextWatermarkOptions())
            out = workspace.new_file(".pdf")
            add_text_watermark(current, out, options)
            return out

        if kind == WorkflowStepKind.ADD_WATERMARK_IMAGE:
            options: ImageWatermarkOptions = params.get("options", ImageWatermarkOptions())
            out = workspace.new_file(".pdf")
            add_image_watermark(current, out, options)
            return out

        if kind == WorkflowStepKind.ADD_PAGE_NUMBERS:
            options: PageNumberOptions = params.get("options", PageNumberOptions())
            out = workspace.new_file(".pdf")
            add_page_numbers(current, out, options)
            return out

        raise ValidationError(f"Unknown workflow step: {kind}")


def build_convert_and_sign_workflow(applications: list[SignatureApplication]) -> list[WorkflowStep]:
    """Convenience builder for the "Convert & Sign" one-click workflow."""
    return [
        WorkflowStep(WorkflowStepKind.CONVERT_WORD_TO_PDF),
        WorkflowStep(WorkflowStepKind.SIGN, {"applications": applications}),
    ]
