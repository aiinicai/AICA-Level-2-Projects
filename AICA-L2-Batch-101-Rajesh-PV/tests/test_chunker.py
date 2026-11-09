import pytest

from judgment_analyzer.chunker import _split_long_text, chunk_pages, estimate_tokens
from judgment_analyzer.pdf_processor import PageText


def _pages(n, size):
    return [PageText(i, f"Page {i} text. " + "x" * size) for i in range(1, n + 1)]


def test_small_document_single_chunk():
    chunks = chunk_pages(_pages(3, 100), max_chars=10_000, overlap_chars=0)
    assert len(chunks) == 1
    assert (chunks[0].page_start, chunks[0].page_end) == (1, 3)
    assert chunks[0].page_label == "pages 1-3"
    assert "[Page 2]" in chunks[0].text


def test_chunks_respect_limit_and_keep_all_pages():
    pages = _pages(20, 900)
    chunks = chunk_pages(pages, max_chars=3_000, overlap_chars=200)
    assert len(chunks) > 1
    assert all(c.char_count <= 3_000 for c in chunks)
    # every page appears exactly once, in order
    combined = "\n".join(c.text for c in chunks)
    for p in pages:
        assert combined.count(f"[Page {p.page_number}]") == 1
    assert [c.index for c in chunks] == list(range(1, len(chunks) + 1))
    for prev, nxt in zip(chunks, chunks[1:]):
        assert nxt.page_start >= prev.page_end


def test_overlap_carries_previous_tail():
    chunks = chunk_pages(_pages(10, 900), max_chars=2_500, overlap_chars=150)
    assert chunks[0].overlap_text == ""
    assert chunks[1].overlap_text == chunks[0].text[-150:]


def test_oversized_page_is_split_without_loss():
    sentences = " ".join(f"Sentence number {i} about the finding." for i in range(400))
    chunks = chunk_pages([PageText(7, sentences)], max_chars=2_000, overlap_chars=0)
    assert len(chunks) > 1
    assert all(c.page_start == c.page_end == 7 for c in chunks)
    assert "[Page 7, part 1/" in chunks[0].text
    for i in (0, 199, 399):
        assert any(f"Sentence number {i} about" in c.text for c in chunks)


def test_split_long_text_handles_no_breaks():
    parts = _split_long_text("y" * 5_000, 1_200)
    assert all(len(p) <= 1_200 for p in parts)
    assert "".join(parts) == "y" * 5_000


def test_empty_pages_skipped():
    chunks = chunk_pages([PageText(1, ""), PageText(2, "  "), PageText(3, "Content")], max_chars=5_000)
    assert len(chunks) == 1 and chunks[0].page_label == "page 3"


def test_invalid_arguments():
    with pytest.raises(ValueError):
        chunk_pages([], max_chars=10)
    with pytest.raises(ValueError):
        chunk_pages([], max_chars=5_000, overlap_chars=5_000)


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 400) == 100
