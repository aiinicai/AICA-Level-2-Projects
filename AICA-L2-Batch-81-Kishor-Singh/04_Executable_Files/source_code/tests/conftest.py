"""Shared pytest fixtures: generate throwaway PDFs of various sizes for engine tests.

No fixture PDF is ever checked into the repo -- everything is synthesized
on the fly with PyMuPDF so tests are hermetic and fast.
"""
from __future__ import annotations

from pathlib import Path

import fitz
import pytest

# Common page sizes in points (width, height), portrait.
A4 = (595, 842)
LETTER = (612, 792)
LEGAL = (612, 1008)


def _make_pdf(path: Path, page_count: int, size=A4, landscape: bool = False) -> Path:
    doc = fitz.open()
    w, h = (size[1], size[0]) if landscape else size
    for i in range(page_count):
        page = doc.new_page(width=w, height=h)
        page.insert_text((36, 36), f"Test page {i + 1} of {page_count}")
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def make_pdf(tmp_path):
    """Factory fixture: make_pdf(name, pages, size=A4, landscape=False) -> Path"""

    def _factory(name: str, pages: int, size=A4, landscape: bool = False) -> Path:
        return _make_pdf(tmp_path / name, pages, size, landscape)

    return _factory


@pytest.fixture
def sample_signature_png(tmp_path) -> Path:
    """A small synthetic signature-like PNG with transparency and whitespace margins."""
    import numpy as np
    from PIL import Image

    arr = np.zeros((200, 400, 4), dtype=np.uint8)
    arr[:, :] = [255, 255, 255, 0]  # fully transparent white background
    # Draw a simple opaque "stroke" rectangle off-center, surrounded by margin.
    arr[80:120, 100:300, :] = [10, 10, 120, 255]
    img = Image.fromarray(arr, mode="RGBA")
    path = tmp_path / "signature.png"
    img.save(path)
    return path


@pytest.fixture
def encrypted_pdf(tmp_path) -> Path:
    """Password-protected PDF where the user password grants full (modify) permission."""
    path = tmp_path / "encrypted.pdf"
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(
        str(path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw="user-secret",
        permissions=int(fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT | fitz.PDF_PERM_MODIFY),
    )
    doc.close()
    return path


@pytest.fixture
def permission_restricted_pdf(tmp_path) -> Path:
    """Password-protected PDF whose owner password disallows modification."""
    path = tmp_path / "restricted.pdf"
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(
        str(path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-secret",
        user_pw="user-secret",
        permissions=int(fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT),
    )
    doc.close()
    return path
