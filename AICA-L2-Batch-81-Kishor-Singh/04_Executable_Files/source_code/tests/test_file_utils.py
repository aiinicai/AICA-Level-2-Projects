"""Tests for utils.file_utils: output naming and collision handling."""
from pathlib import Path

from models.enums import CollisionPolicy, NamingMode
from utils.file_utils import compute_output_path, human_size


def test_add_suffix_default(tmp_path):
    src = tmp_path / "ABC Agreement.pdf"
    src.write_text("x")
    out = compute_output_path(src, tmp_path / "out", NamingMode.ADD_SUFFIX, suffix="_Signed")
    assert out.name == "ABC Agreement_Signed.pdf"


def test_add_prefix(tmp_path):
    src = tmp_path / "Agreement.pdf"
    src.write_text("x")
    out = compute_output_path(src, tmp_path / "out", NamingMode.ADD_PREFIX, prefix="Signed_")
    assert out.name == "Signed_Agreement.pdf"


def test_keep_original_name(tmp_path):
    src = tmp_path / "Agreement.pdf"
    src.write_text("x")
    out = compute_output_path(src, tmp_path / "out", NamingMode.KEEP_ORIGINAL)
    assert out.name == "Agreement.pdf"


def test_overwrite_original_targets_source_path(tmp_path):
    src = tmp_path / "Agreement.pdf"
    src.write_text("x")
    out = compute_output_path(src, None, NamingMode.OVERWRITE_ORIGINAL)
    assert out == src


def test_default_behaviour_never_overwrites_original():
    """The spec's default must be 'do not overwrite the original file'."""
    from utils.config_manager import AppSettings

    assert AppSettings().naming_mode == NamingMode.ADD_SUFFIX.value


def test_collision_skip_returns_none(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "Agreement_Signed.pdf").write_text("existing")
    src = tmp_path / "Agreement.pdf"
    src.write_text("x")
    result = compute_output_path(src, out_dir, NamingMode.ADD_SUFFIX, collision_policy=CollisionPolicy.SKIP)
    assert result is None


def test_collision_replace_returns_same_path(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    existing = out_dir / "Agreement_Signed.pdf"
    existing.write_text("existing")
    src = tmp_path / "Agreement.pdf"
    src.write_text("x")
    result = compute_output_path(src, out_dir, NamingMode.ADD_SUFFIX, collision_policy=CollisionPolicy.REPLACE)
    assert result == existing


def test_collision_rename_automatically(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "Agreement_Signed.pdf").write_text("existing")
    (out_dir / "Agreement_Signed (1).pdf").write_text("existing 2")
    src = tmp_path / "Agreement.pdf"
    src.write_text("x")
    result = compute_output_path(src, out_dir, NamingMode.ADD_SUFFIX, collision_policy=CollisionPolicy.RENAME)
    assert result.name == "Agreement_Signed (2).pdf"


def test_human_size_formatting():
    assert human_size(500) == "500 B"
    assert human_size(2048) == "2.0 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"
