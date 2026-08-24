"""Tests for .streamlit/config.toml - validates it's well-formed TOML,
uses only theme keys actually supported by the pinned Streamlit version,
and the colors are valid hex codes."""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
THEME_PATH = PROJECT_ROOT / ".streamlit" / "config.toml"

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def _load_theme() -> dict:
    with open(THEME_PATH, "rb") as f:
        return tomllib.load(f)


class TestThemeConfigWellFormed:
    def test_file_exists(self):
        assert THEME_PATH.exists()

    def test_parses_as_valid_toml(self):
        data = _load_theme()
        assert "theme" in data

    def test_only_uses_keys_supported_by_pinned_streamlit_version(self):
        import streamlit.config as st_config

        supported_keys = set(st_config.get_options_for_section("theme").keys())
        data = _load_theme()
        used_keys = set(data["theme"].keys())
        unsupported = used_keys - supported_keys
        assert not unsupported, (
            f"config.toml uses theme key(s) not supported by the pinned "
            f"Streamlit version: {unsupported}"
        )

    def test_base_is_light_or_dark(self):
        data = _load_theme()
        assert data["theme"]["base"] in ("light", "dark")

    def test_color_values_are_valid_hex_codes(self):
        data = _load_theme()
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for key in ("primaryColor", "backgroundColor", "secondaryBackgroundColor", "textColor"):
            value = data["theme"][key]
            assert hex_pattern.match(value), f"{key}={value!r} is not a valid #RRGGBB hex color"

    def test_background_and_text_have_sufficient_contrast(self):
        data = _load_theme()

        def luminance(hex_color: str) -> float:
            hex_color = hex_color.lstrip("#")
            r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        bg_luminance = luminance(data["theme"]["backgroundColor"])
        text_luminance = luminance(data["theme"]["textColor"])
        assert abs(bg_luminance - text_luminance) > 100

    def test_font_is_a_safe_base_option_not_a_newer_version_only_feature(self):
        data = _load_theme()
        assert data["theme"]["font"] in ("sans serif", "serif", "monospace")
