"""The vendored libraries must be the ones that were downloaded. §1, §13.

A URL that changes under you is a supply-chain problem everyone understands.
A file in the repository that changes under you is the same problem with no
symptom: the page looks identical and nothing fetches anything. So the bytes
are pinned to a digest recorded in `docs/VENDORED_ASSETS.md`.
"""

from __future__ import annotations

from pathlib import Path

from scripts.check_vendored_assets import VENDOR_DIR, expected, problems

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_the_vendored_files_match_their_recorded_digests() -> None:
    found = problems()
    assert not found, "vendored assets have drifted:\n  " + "\n  ".join(found)


def test_both_libraries_the_build_prompt_names_are_present() -> None:
    names = " ".join(expected())
    assert "htmx" in names, "Build Prompt v2 §1 names HTMX 2.x"
    assert "alpine" in names, "Build Prompt v2 §1 names Alpine.js 3.x"


def test_the_base_template_serves_them_locally() -> None:
    """§13 — no CDN. The tags must point at /static, not at a hostname."""
    html = (PROJECT_ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    for name in expected():
        assert f"/static/vendor/{name}" in html, f"{name} is vendored but never loaded"
    assert "//unpkg.com" not in html
    assert "//cdn." not in html


def test_no_vendored_file_is_an_error_page() -> None:
    """A failed download that still writes a file is the quiet failure here."""
    for name in expected():
        text = (VENDOR_DIR / name).read_text(encoding="utf-8", errors="replace")
        assert not text.lstrip()[:15].lower().startswith(("<!doctype", "<html")), name
        assert len(text) > 10_000, f"{name} is suspiciously small"
