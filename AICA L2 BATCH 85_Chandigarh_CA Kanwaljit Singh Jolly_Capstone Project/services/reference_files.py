"""
Reference-file ingestion.

An agent can attach "example input" and "example output" files that show what good
work looks like. These are a strong signal for the criteria engine ("what should a
correct output contain?"). This module downloads those OneDrive files, extracts
their text, and returns labeled snippets to feed into criteria derivation.

Kept separate from the pipeline so it is easy to test and so a download/extract
failure for one reference file never blocks a run.
"""

import logging
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

from services.file_processor import extract_docx_text, extract_excel_text, extract_pdf_text

logger = logging.getLogger(__name__)

MAX_CHARS_PER_FILE = 6000
MAX_REFERENCE_FILES = 12


def extract_file_text(path: str) -> str:
    """Best-effort text extraction for a local file, dispatched by extension."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in ('.txt', '.md', '.csv'):
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        if ext in ('.docx', '.doc'):
            return extract_docx_text(path)
        if ext == '.pdf':
            return extract_pdf_text(path)
        if ext in ('.xlsx', '.xlsm', '.xls'):
            return extract_excel_text(path)
    except Exception as e:  # noqa: BLE001 - a bad reference file must not break the run
        logger.warning("Failed to extract reference text from %s: %s", path, e)
        return ""
    return ""


def _label(role: str, name: str, text: str) -> str:
    text = (text or "").strip()
    if len(text) > MAX_CHARS_PER_FILE:
        text = text[:MAX_CHARS_PER_FILE] + "\n... [truncated]"
    return f"[{role}] {name}\n{text}"


def gather_reference_texts(
    access_token: str,
    reference_file_paths: Optional[Dict[str, Any]],
    downloader=None,
) -> List[str]:
    """
    Download the agent's example input/output files and return labeled text snippets.

    Args:
        access_token: OneDrive access token.
        reference_file_paths: {'example_inputs': [paths], 'example_outputs': [paths]}.
        downloader: optional callable(access_token, remote_path, local_dest) for tests;
            defaults to services.onedrive.download_onedrive_file.

    Returns:
        List of labeled text blocks (empty list if nothing usable).
    """
    if not reference_file_paths or not isinstance(reference_file_paths, dict):
        return []

    if downloader is None:
        from services.onedrive import download_onedrive_file as downloader

    groups = [
        ("EXAMPLE INPUT", reference_file_paths.get('example_inputs') or []),
        ("EXAMPLE OUTPUT", reference_file_paths.get('example_outputs') or []),
    ]

    texts: List[str] = []
    work_dir = tempfile.mkdtemp(prefix="taskchecker_refs_")
    try:
        count = 0
        for role, paths in groups:
            for remote_path in paths:
                if count >= MAX_REFERENCE_FILES:
                    break
                if not isinstance(remote_path, str) or not remote_path.strip():
                    continue
                name = os.path.basename(remote_path)
                local_dest = os.path.join(work_dir, f"{count}_{name}")
                try:
                    downloader(access_token, remote_path, local_dest)
                except Exception as e:  # noqa: BLE001
                    logger.warning("Failed to download reference file %s: %s", remote_path, e)
                    continue
                text = extract_file_text(local_dest)
                if text and text.strip():
                    texts.append(_label(role, name, text))
                count += 1
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return texts
