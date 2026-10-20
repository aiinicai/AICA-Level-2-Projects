"""End-to-end analysis pipeline (runs on a background thread).

1. Extract text (with OCR where needed).
2. Short documents: one Gemini request with the full text.
   Long documents (or on a token-limit error): split into page-aware sections,
   take detailed loss-averse notes per section ("map"), optionally merge notes
   ("reduce"), then produce the final report from the notes plus verbatim
   opening and closing excerpts so case details and the operative order are
   never paraphrased away.
3. Parse the report into the canonical sections.
4. Source Check: every quotation, citation, section, date, amount and paragraph/page
   reference in the report is looked up in the judgment text (no AI).
5. Consistency check (optional): the key facts are extracted twice and compared.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from . import prompts
from .chunker import Chunk, chunk_pages, estimate_tokens
from .consistency import ConsistencyResult, facts_without_ai, fill_missing, run_consistency
from .config import AppSettings
from .gemini_client import GeminiClient, TokenLimitError
from .paragraphs import add_para_markers, detect_paragraphs
from .pdf_processor import CancelledError, DocumentInfo, ExtractedDocument, extract_text
from .prompts import REPORT_SECTIONS
from .response_parser import ParsedReport, parse_report
from .verifier import VerificationReport, verify_report

log = logging.getLogger(__name__)

ProgressFn = Callable[[float, str], None]  # (fraction 0..1, message)

EXCERPT_CHARS = 8_000
MAX_MERGE_ROUNDS = 4


@dataclass
class AnalysisResult:
    report: ParsedReport
    document: ExtractedDocument
    model: str
    mode: str
    sections_processed: int = 1
    warnings: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0
    verification: VerificationReport | None = None
    consistency: ConsistencyResult | None = None
    para_numbers: set[int] = field(default_factory=set)
    # Set when the reviewer has confirmed the key facts (Save to Register dialog).
    key_facts: dict = field(default_factory=dict)
    facts_filled: list = field(default_factory=list)   # fields taken from the report / judgment text, not the AI
    facts_problem: str = ""                            # why the AI reading of the key facts was incomplete
    key_facts_confirmed: bool = False
    register_ref: str = ""
    approved_by: str = ""
    approved_at: str = ""
    approved_fingerprint: str = ""

    def fingerprint(self) -> str:
        """Hash of the report text and the confirmed key facts - approval is tied to exactly this content."""
        import hashlib
        import json

        raw = self.report.to_markdown() + "\x1f" + json.dumps(self.key_facts, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    @property
    def is_approved(self) -> bool:
        return bool(self.approved_fingerprint) and self.approved_fingerprint == self.fingerprint()

    def approve(self, reviewer: str) -> None:
        from datetime import datetime

        self.approved_by = reviewer.strip()
        self.approved_at = datetime.now().strftime("%d-%m-%Y %H:%M")
        self.approved_fingerprint = self.fingerprint()

    def uncertain_lines(self) -> list[str]:
        """Report lines still marked [Uncertain] - these must be resolved before approval."""
        import re

        return [ln.strip() for ln in self.report.to_markdown().splitlines()
                if re.search(r"[\[\{]\s*Uncertain\s*[\]\}]", ln, re.IGNORECASE)]

    @property
    def source_text(self) -> str:
        return self.document.full_text(with_page_markers=False)

    def recheck_sources(self) -> None:
        """Re-run the Source Check (e.g. after the user edits the report)."""
        self.verification = verify_report(self.report, self.source_text, self.para_numbers,
                                          self.document.info.page_count)

    @property
    def needs_key_fact_review(self) -> bool:
        return bool(self.consistency and self.consistency.disagreements and not self.key_facts_confirmed)


class Analyzer:
    def __init__(self, settings: AppSettings, client: GeminiClient,
                 progress: ProgressFn | None = None, cancel_event: threading.Event | None = None) -> None:
        self.settings = settings
        self.client = client
        self.cancel_event = cancel_event or threading.Event()
        self._progress = progress or (lambda f, m: None)
        self._last_fraction = 0.0

    # -- helpers ------------------------------------------------------------
    def _report(self, fraction: float, message: str) -> None:
        self._progress(max(0.0, min(1.0, fraction)), message)

    def _check_cancel(self) -> None:
        if self.cancel_event.is_set():
            raise CancelledError()

    def _generate(self, prompt: str, warnings: list[str], label: str) -> str:
        result = self.client.generate(
            prompt, prompts.SYSTEM_INSTRUCTION, cancel_event=self.cancel_event,
            on_status=lambda msg: self._report(self._last_fraction, msg),  # retry notices
        )
        if result.truncated:
            warnings.append(f"The AI output for {label} reached the output-token limit and may be incomplete. "
                            "Increase 'Max output tokens' or use a smaller section size.")
        return result.text

    def _step(self, fraction: float, message: str) -> None:
        self._last_fraction = fraction
        self._report(fraction, message)

    # -- pipeline -----------------------------------------------------------
    def run(self, info: DocumentInfo) -> AnalysisResult:
        started = time.monotonic()
        s = self.settings

        self._step(0.01, "Reading PDF...")
        document = extract_text(
            info, ocr_mode=s.ocr_mode, ocr_language=s.ocr_language,
            progress=lambda done, total, msg: self._step(0.02 + 0.23 * done / max(total, 1), msg),
            cancel_event=self.cancel_event,
        )
        warnings = list(document.warnings)
        self._check_cancel()

        marks = detect_paragraphs(document.pages) if s.include_para_refs else []
        para_numbers = {m.number for m in marks}
        if marks:
            marked = ExtractedDocument(info=document.info, pages=add_para_markers(document.pages, marks))
            log.info("Detected %d numbered paragraphs.", len(marks))
        else:
            marked = document
        full_text = marked.full_text(with_page_markers=True)
        use_sections = s.force_sectioned or len(full_text) > s.single_pass_max_chars
        if not use_sections:
            limit = self.client.input_token_limit()
            if limit and estimate_tokens(full_text) > int(limit * 0.75):
                use_sections = True
                log.info("Estimated tokens exceed 75%% of model limit (%s); using sections.", limit)

        raw = None
        mode = "Single pass"
        sections_processed = 1
        if not use_sections:
            self._step(0.30, f"Sending document to Gemini ({s.model}) for analysis...")
            try:
                raw = self._generate(
                    prompts.full_document_prompt(full_text, s.analysis_depth, False, info.file_name,
                                                 bool(marks)),
                    warnings, "the report")
            except TokenLimitError:
                warnings.append("The document exceeded the model's single-request limit and was "
                                "processed section by section instead.")
                use_sections = True

        if use_sections:
            raw, sections_processed = self._sectioned(marked, full_text, warnings, bool(marks))
            mode = f"Section-by-section ({sections_processed} section{'s' if sections_processed != 1 else ''})"

        self._check_cancel()
        self._step(0.90, "Organising the results...")
        report = parse_report(raw)
        missing = report.missing_sections
        if missing:
            names = ", ".join(f"{n}. {REPORT_SECTIONS[n - 1].title}" for n in missing)
            warnings.append(f"The AI response did not include: {names}.")

        result = AnalysisResult(report, document, s.model, mode, sections_processed, warnings,
                                para_numbers=para_numbers)
        self._step(0.92, "Source check: looking up quotations, citations, sections and dates in the judgment...")
        result.recheck_sources()

        # Key facts are always read (once; twice with "Double-check key facts"), so the approval window
        # and the register are filled in. Fields the AI leaves empty are filled from the report's Case
        # Details and the judgment text; if the AI reading fails, those are used for every field.
        source_text = result.source_text
        runs = 2 if s.consistency_check else 1
        consistency = run_consistency(
            self.client, full_text, source_text, runs=runs, cancel_event=self.cancel_event,
            progress=lambda i, n: self._step(0.93 + 0.03 * i, f"Reading the key facts ({i + 1} of {n})..."))
        result.consistency = consistency if s.consistency_check else None
        fallback = facts_without_ai(report, source_text)
        if consistency.has_facts:
            result.key_facts, result.facts_filled = fill_missing(consistency.merged(), fallback)
            if s.consistency_check and consistency.disagreements:
                warnings.append("Two AI readings differ on " + ", ".join(f.label for f in consistency.disagreements)
                                + " - you will choose the correct value when you approve.")
        else:
            result.key_facts, result.facts_filled = fill_missing({}, fallback)
        if (s.consistency_check and not consistency.ok) or not consistency.has_facts:
            result.facts_problem = consistency.summary_line()
            warnings.append(result.facts_problem)

        result.elapsed_s = time.monotonic() - started
        self._step(1.0, f"Analysis complete in {result.elapsed_s:.0f}s.")
        log.info("Analysis complete: mode=%s sections=%d elapsed=%.1fs", mode, sections_processed, result.elapsed_s)
        return result

    def _sectioned(self, document: ExtractedDocument, full_text: str, warnings: list[str],
                   para_refs: bool = False) -> tuple[str, int]:
        s = self.settings
        chunks: list[Chunk] = chunk_pages(document.pages, s.chunk_max_chars, s.chunk_overlap_chars)
        total = len(chunks)
        notes: list[str] = []
        for chunk in chunks:
            self._check_cancel()
            self._step(0.28 + 0.52 * (chunk.index - 1) / total,
                       f"Analysing section {chunk.index} of {total} ({chunk.page_label})...")
            text = self._generate(
                prompts.section_notes_prompt(chunk.text, chunk.overlap_text, chunk.index, total,
                                             chunk.page_label, False),
                warnings, f"section {chunk.index}")
            notes.append(f"=== SECTION {chunk.index} of {total} ({chunk.page_label}) ===\n{text.strip()}")

        notes = self._merge_notes(notes, warnings)
        self._check_cancel()
        self._step(0.85, "Consolidating section notes into the final analysis...")
        opening = full_text[:EXCERPT_CHARS]
        closing = full_text[-EXCERPT_CHARS:] if len(full_text) > EXCERPT_CHARS else ""
        raw = self._generate(
            prompts.consolidation_prompt("\n\n".join(notes), opening, closing or "(Same as opening excerpt.)",
                                         s.analysis_depth, False, document.info.file_name, total,
                                         para_refs),
            warnings, "the consolidated report")
        return raw, total

    def _merge_notes(self, notes: list[str], warnings: list[str]) -> list[str]:
        """Hierarchically merge notes until they fit comfortably in one request."""
        budget = max(self.settings.single_pass_max_chars // 2, 40_000)
        rounds = 0
        while sum(len(n) for n in notes) > budget and len(notes) > 1 and rounds < MAX_MERGE_ROUNDS:
            rounds += 1
            groups: list[list[str]] = [[]]
            for n in notes:
                if groups[-1] and sum(len(x) for x in groups[-1]) + len(n) > budget:
                    groups.append([])
                groups[-1].append(n)
            if len(groups) == len(notes):  # each note alone exceeds budget; merging pairs instead
                groups = [notes[i:i + 2] for i in range(0, len(notes), 2)]
            merged = []
            for i, group in enumerate(groups, 1):
                self._check_cancel()
                self._step(0.80 + 0.04 * i / len(groups), f"Merging notes (round {rounds}, group {i}/{len(groups)})...")
                if len(group) == 1:
                    merged.append(group[0])
                    continue
                merged.append(f"=== MERGED NOTES {i} ===\n" + self._generate(
                    prompts.merge_notes_prompt("\n\n".join(group)), warnings, f"merge group {i}").strip())
            notes = merged
        return notes
