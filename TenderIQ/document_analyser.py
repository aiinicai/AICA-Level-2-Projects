"""
document_analyser.py
Reads downloaded tender PDFs with PyPDF, chunks long documents, and uses the OpenAI SDK
to generate structured, page-traceable summaries for each tender.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Callable, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

from tender_extractor import NOT_AVAILABLE, TenderRecord

DEFAULT_MODEL = "gpt-4o-mini"
CHUNK_CHAR_LIMIT = 12000
MAX_CHUNKS_PER_TENDER = 8
MIN_EXTRACTABLE_ALNUM_CHARS = 50

SUMMARY_FIELDS = (
    "purpose",
    "products_services",
    "scope_of_work",
    "technical_specifications",
    "turnover_requirement",
    "experience_requirement",
    "capability_requirement",
    "emd_requirement",
    "tender_fee",
    "performance_security",
    "important_deadlines",
    "required_certificates",
    "commercial_conditions",
    "disqualification_conditions",
    "risk_observations",
    "overall_summary",
    "document_references",
)

SYSTEM_PROMPT = """You are a senior procurement and tender intelligence analyst.
Extract factual information strictly from the provided tender PDF text.
Rules:
1. Never invent, guess, or extrapolate missing numbers, dates, or requirements.
2. If an item is not mentioned in the provided text, write "Not Specified in Document".
3. Cite supporting PDF filename and page numbers like (Doc.pdf, Page 4) whenever available.
4. Keep financial figures, turnover thresholds, EMD, fees, and deadlines exact and traceable.
5. Return ONLY a valid JSON object matching the exact keys requested."""

SCHEMA_INSTRUCTION = """Return a JSON object with these exact string keys:
- "purpose": Concise purpose of the tender.
- "products_services": Products or services required.
- "scope_of_work": Concise scope of work.
- "technical_specifications": Key technical specifications and standards.
- "turnover_requirement": Minimum annual turnover requirement (with page ref).
- "experience_requirement": Past experience / completed works requirements (with page ref).
- "capability_requirement": Manufacturing or supply capability requirements (with page ref).
- "emd_requirement": Earnest Money Deposit (EMD) amount and mode (with page ref).
- "tender_fee": Tender document fee (with page ref).
- "performance_security": Performance security / PBG requirement (with page ref).
- "important_deadlines": Submission, pre-bid, and opening deadlines (with page ref).
- "required_certificates": Required registrations, licenses, and certificates (with page ref).
- "commercial_conditions": Payment terms, delivery period, warranty, LD, etc.
- "disqualification_conditions": Potential disqualification / rejection criteria.
- "risk_observations": Key risks, ambiguities, or commercial observations.
- "overall_summary": 3-5 sentence executive summary for management.
- "document_references": List of source document filenames and page ranges reviewed."""


@dataclass
class AnalysisStats:
    """Aggregate statistics produced by document analysis."""

    tenders_analysed: int = 0
    documents_unanalysed: int = 0
    api_key_configured: bool = False
    warnings: list[str] = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


def load_openai_config(env_dir: Optional[Path] = None) -> tuple[Optional[str], str]:
    """Load OPENAI_API_KEY and OPENAI_MODEL from .env without hardcoding secrets."""
    candidates = []
    if env_dir:
        candidates.append(env_dir / ".env")
    candidates.append(Path(__file__).resolve().parent / ".env")
    candidates.append(Path.cwd() / ".env")

    for env_path in candidates:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            break
    else:
        load_dotenv(override=False)

    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key or api_key == "your_api_key_here":
        api_key = None

    model = (os.getenv("OPENAI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return api_key, model


def extract_pdf_text(pdf_path: Path) -> tuple[str, int, str, Optional[str]]:
    """
    Extract page-tagged text from a PDF using PyPDF.
    Returns (text, page_count, status, error_note).
    status is one of: 'extracted', 'scanned', 'error'.
    """
    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            try:
                res = reader.decrypt("")
                if res == 0:
                    return "", len(reader.pages), "error", "Encrypted PDF cannot be read without password."
            except Exception:
                return "", 0, "error", "Encrypted PDF cannot be read."

        page_count = len(reader.pages)
        pages_out: list[str] = []
        alnum_count = 0

        for idx, page in enumerate(reader.pages, start=1):
            try:
                txt = page.extract_text() or ""
            except Exception as exc:
                pages_out.append(f"\n--- [{pdf_path.name} - Page {idx}] (extraction error: {exc}) ---\n")
                continue

            cleaned = txt.strip()
            if cleaned:
                alnum_count += sum(1 for ch in cleaned if ch.isalnum())
                pages_out.append(f"\n--- [{pdf_path.name} - Page {idx}] ---\n{cleaned}\n")

        if alnum_count < MIN_EXTRACTABLE_ALNUM_CHARS:
            return (
                "",
                page_count,
                "scanned",
                "Scanned PDF – text extraction unavailable",
            )

        return "\n".join(pages_out), page_count, "extracted", None

    except Exception as exc:
        return "", 0, "error", f"PDF extraction error ({pdf_path.name}): {exc}"


def chunk_document_text(text: str, max_chars: int = CHUNK_CHAR_LIMIT) -> list[str]:
    """Split extracted page-tagged text into manageable sections for OpenAI."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    lines = text.splitlines(keepends=True)
    buffer: list[str] = []
    current_len = 0

    for line in lines:
        if current_len + len(line) > max_chars and buffer:
            chunks.append("".join(buffer))
            buffer = []
            current_len = 0
        # Handle single huge line gracefully
        if len(line) > max_chars:
            for start in range(0, len(line), max_chars):
                chunks.append(line[start : start + max_chars])
            continue
        buffer.append(line)
        current_len += len(line)

    if buffer:
        chunks.append("".join(buffer))

    if len(chunks) > MAX_CHUNKS_PER_TENDER:
        # Keep beginning, middle, and ending sections so key specs & closing terms remain covered
        head = chunks[:4]
        mid = chunks[len(chunks) // 2 : len(chunks) // 2 + 2]
        tail = chunks[-2:]
        return head + mid + tail

    return chunks


def _empty_summary(status_note: str) -> dict:
    """Create a default structured summary dict when AI analysis is skipped or failed."""
    summary = {k: "Not Specified in Document" for k in SUMMARY_FIELDS}
    summary["overall_summary"] = status_note
    summary["document_references"] = NOT_AVAILABLE
    summary["_status"] = status_note
    return summary


def _call_openai_json(client: OpenAI, model: str, user_prompt: str) -> dict:
    """Invoke OpenAI Chat Completions with JSON object output and parse response."""
    resp = client.chat.completions.create(
        model=model,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = resp.choices[0].message.content or "{}"
    parsed = json.loads(raw)
    result = {}
    for k in SUMMARY_FIELDS:
        val = parsed.get(k, "Not Specified in Document")
        if isinstance(val, list):
            val = "; ".join(str(x) for x in val if x)
        result[k] = str(val).strip() or "Not Specified in Document"
    return result


def analyse_tender_documents(
    tenders: list[TenderRecord],
    env_dir: Optional[Path] = None,
    progress_cb: Optional[Callable[[str, str, float], None]] = None,
    client_override: Optional[OpenAI] = None,
) -> AnalysisStats:
    """
    Read downloaded PDFs for every tender and generate AI summaries.
    Continues processing remaining tenders if one fails or if API key is missing.
    """
    api_key, model = load_openai_config(env_dir)
    client = client_override or (OpenAI(api_key=api_key, timeout=60.0) if api_key else None)

    stats = AnalysisStats(api_key_configured=bool(client))
    if not client:
        stats.warnings.append(
            "OPENAI_API_KEY is not configured in .env. Tender extraction and downloads completed, "
            "and AI document analysis was skipped."
        )

    total = max(len(tenders), 1)

    for idx, tender in enumerate(tenders, start=1):
        if progress_cb:
            progress_cb(
                "Analysing documents using AI",
                f"Processing tender {idx} of {len(tenders)}: {tender.tender_id}",
                0.75 + (0.15 * (idx / total)),
            )

        pdf_paths = [Path(p) for p in tender.downloaded_files if Path(p).exists()]
        if not pdf_paths:
            tender.ai_summary = _empty_summary("No downloaded PDF documents available for analysis.")
            continue

        extracted_sections: list[str] = []
        doc_notes: list[str] = []
        tender_unanalysed_docs = 0

        for pdf_path in pdf_paths:
            text, page_count, status, err_note = extract_pdf_text(pdf_path)
            if status == "extracted" and text:
                extracted_sections.append(text)
                doc_notes.append(f"{pdf_path.name} ({page_count} pages)")
            elif status == "scanned":
                tender_unanalysed_docs += 1
                doc_notes.append(f"{pdf_path.name}: Scanned PDF – text extraction unavailable")
                stats.warnings.append(f"{tender.tender_id} / {pdf_path.name}: Scanned PDF – text extraction unavailable")
            else:
                tender_unanalysed_docs += 1
                doc_notes.append(f"{pdf_path.name}: {err_note}")
                stats.warnings.append(f"{tender.tender_id} / {pdf_path.name}: {err_note}")

        stats.documents_unanalysed += tender_unanalysed_docs

        if not extracted_sections:
            note = (
                "Scanned PDF – text extraction unavailable"
                if any("Scanned PDF" in n for n in doc_notes)
                else "Document text extraction failed."
            )
            tender.ai_summary = _empty_summary(note)
            tender.ai_summary["document_references"] = "; ".join(doc_notes) or NOT_AVAILABLE
            continue

        if not client:
            # Count extractable docs as unanalysed by AI since API key is missing
            stats.documents_unanalysed += len(extracted_sections)
            tender.ai_summary = _empty_summary("AI analysis skipped (OPENAI_API_KEY missing in .env).")
            tender.ai_summary["document_references"] = "; ".join(doc_notes)
            continue

        combined_text = "\n".join(extracted_sections)
        chunks = chunk_document_text(combined_text)
        metadata_header = (
            f"Tender Metadata -> ID: {tender.tender_id} | Title: {tender.title} | "
            f"Organisation: {tender.organisation} | Closing Date: {tender.closing_date} | "
            f"Estimated Value: {tender.estimated_value} | EMD: {tender.emd_amount}\n"
        )

        try:
            if len(chunks) == 1:
                prompt = f"{SCHEMA_INSTRUCTION}\n\n{metadata_header}\nDOCUMENT TEXT:\n{chunks[0]}"
                summary = _call_openai_json(client, model, prompt)
            else:
                # Map step: extract facts from each chunk, then Reduce into consolidated JSON
                partial_notes: list[dict] = []
                for c_idx, chunk in enumerate(chunks, start=1):
                    part_prompt = (
                        f"{SCHEMA_INSTRUCTION}\n\n{metadata_header}"
                        f"DOCUMENT SECTION {c_idx} OF {len(chunks)}:\n{chunk}"
                    )
                    partial_notes.append(_call_openai_json(client, model, part_prompt))

                merge_prompt = (
                    f"{SCHEMA_INSTRUCTION}\n\n{metadata_header}"
                    "Consolidate the following section-level extractions from the same tender's documents "
                    "into one concise, non-duplicative JSON summary. Preserve all page citations and exact figures:\n"
                    f"{json.dumps(partial_notes, indent=2)}"
                )
                summary = _call_openai_json(client, model, merge_prompt)

            summary["document_references"] = "; ".join(doc_notes)
            summary["_status"] = "Analysed"
            tender.ai_summary = summary
            stats.tenders_analysed += 1

        except Exception as exc:
            stats.documents_unanalysed += len(extracted_sections)
            err_msg = f"OpenAI API error for {tender.tender_id}: {exc}"
            stats.warnings.append(err_msg)
            tender.ai_summary = _empty_summary(f"AI analysis failed: {exc}")
            tender.ai_summary["document_references"] = "; ".join(doc_notes)

    return stats
