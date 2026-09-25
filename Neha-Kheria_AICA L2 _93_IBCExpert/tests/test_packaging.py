from __future__ import annotations

from pathlib import Path

from scripts.validate_public_key import PublicKeyValidationError, validate_public_key
from scripts.verify_customer_package import verify_customer_package


def _public_key(path: Path) -> Path:
    target = path / "app" / "resources" / "licence_public_key.hex"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("11" * 32 + "\n", encoding="ascii")
    return target


def test_public_key_validator_accepts_exact_ed25519_public_key(tmp_path: Path):
    key = tmp_path / "licence_public_key.hex"
    key.write_text("ab" * 32 + "\n", encoding="ascii")
    assert validate_public_key(key) == "ab" * 32


def test_public_key_validator_rejects_wrong_filename(tmp_path: Path):
    key = tmp_path / "owner_private_key.ibckey"
    key.write_text("ab" * 32, encoding="ascii")
    try:
        validate_public_key(key)
    except PublicKeyValidationError:
        pass
    else:
        raise AssertionError("private/wrongly named key must not be accepted")


def test_customer_package_verifier_accepts_minimal_safe_layout(tmp_path: Path):
    (tmp_path / "IBCExpert.exe").write_bytes(b"MZ")
    _public_key(tmp_path)
    assert verify_customer_package(tmp_path, require_executable=True) == []


def test_customer_package_verifier_rejects_owner_tools(tmp_path: Path):
    (tmp_path / "IBCExpert.exe").write_bytes(b"MZ")
    _public_key(tmp_path)
    owner = tmp_path / "_internal" / "owner_tools" / "licence_generator.pyc"
    owner.parent.mkdir(parents=True)
    owner.write_bytes(b"compiled")
    issues = verify_customer_package(tmp_path, require_executable=True)
    assert any("Forbidden owner/test path" in issue for issue in issues)


def test_customer_package_verifier_rejects_private_key_material(tmp_path: Path):
    (tmp_path / "IBCExpert.exe").write_bytes(b"MZ")
    _public_key(tmp_path)
    private = tmp_path / "owner_private_key.ibckey"
    private.write_bytes(b"IBC-OWNER-KEY-v1\x00secret")
    issues = verify_customer_package(tmp_path, require_executable=True)
    assert any("Private signing-key" in issue for issue in issues)


def test_spec_has_customer_only_exclusions_and_local_assets():
    spec = (Path(__file__).parents[1] / "packaging" / "IBCExpert.spec").read_text(encoding="utf-8")
    assert '"owner_tools"' in spec
    assert '"app/web/templates"' in spec
    assert '"app/web/static"' in spec
    assert "IBC_EXPERT_PUBLIC_KEY" in spec
    assert "launch_desktop.py" in spec
