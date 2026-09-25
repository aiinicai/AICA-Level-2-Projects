"""First-run dependency bootstrap with online and local wheelhouse modes."""
from __future__ import annotations

import hashlib
import importlib.util
import importlib.metadata
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Dependency:
    requirement: str
    import_name: str
    distribution_name: str
    pinned_version: str | None = None




_HASH_LINE = re.compile(r"^(?P<hash>[0-9a-f]{64})\s{2}(?P<name>[^\\/]+)$")


def verify_wheelhouse_integrity(wheelhouse: Path) -> None:
    """Fail closed if a selected offline wheelhouse is missing/tampered."""
    manifest = wheelhouse / "SHA256SUMS.txt"
    if not manifest.is_file():
        raise RuntimeError(
            "Offline wheelhouse is present but SHA256SUMS.txt is missing. "
            "Regenerate it with scripts/prepare_wheelhouse.ps1 on the trusted build computer."
        )
    expected: dict[str, str] = {}
    for lineno, raw in enumerate(manifest.read_text(encoding="ascii", errors="replace").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        match = _HASH_LINE.fullmatch(line)
        if not match:
            raise RuntimeError(f"Invalid wheelhouse SHA256SUMS.txt line {lineno}.")
        expected[match.group("name")] = match.group("hash")
    wheels = sorted(path for path in wheelhouse.iterdir() if path.is_file() and path.suffix.lower() == ".whl")
    if not wheels:
        raise RuntimeError("Offline wheelhouse contains no wheel files.")
    if {p.name for p in wheels} != set(expected):
        raise RuntimeError("Offline wheelhouse contents do not match SHA256SUMS.txt.")
    for path in wheels:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected[path.name]:
            raise RuntimeError(f"Offline wheelhouse integrity check failed for {path.name}.")


_IMPORT_NAMES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "jinja2": "jinja2",
    "python-multipart": "multipart",
    "pywebview": "webview",
    "cryptography": "cryptography",
    "argon2-cffi": "argon2",
    "pytesseract": "pytesseract",
    "pillow": "PIL",
    "pypdf": "pypdf",
    "pymupdf": "fitz",
    "python-docx": "docx",
    "openpyxl": "openpyxl",
    "reportlab": "reportlab",
    "pytest": "pytest",
    "pytest-cov": "pytest_cov",
    "httpx": "httpx",
    "pyinstaller": "PyInstaller",
}


def parse_requirements(path: Path) -> list[Dependency]:
    dependencies: list[Dependency] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        requirement_body = line.split(";", 1)[0].strip()
        if "==" in requirement_body:
            package_part, pinned_version = requirement_body.split("==", 1)
            pinned_version = pinned_version.strip()
        else:
            package_part, pinned_version = requirement_body, None
        distribution_name = package_part.split("[", 1)[0].strip()
        base = distribution_name.lower()
        dependencies.append(
            Dependency(
                line,
                _IMPORT_NAMES.get(base, base.replace("-", "_")),
                distribution_name,
                pinned_version,
            )
        )
    return dependencies


def dependency_is_satisfied(dep: Dependency) -> bool:
    if importlib.util.find_spec(dep.import_name) is None:
        return False
    if dep.pinned_version is None:
        return True
    try:
        installed = importlib.metadata.version(dep.distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return False
    return installed == dep.pinned_version


def missing_dependencies(requirements_path: Path) -> list[Dependency]:
    return [d for d in parse_requirements(requirements_path) if not dependency_is_satisfied(d)]


def install_missing(
    project_root: Path,
    progress: Callable[[str], None] = print,
    *,
    python_executable: str | None = None,
) -> None:
    requirements = project_root / "requirements.txt"
    wheelhouse = project_root / "wheelhouse"
    missing = missing_dependencies(requirements)
    if not missing:
        progress("All required Python packages are already installed.")
        return
    python = python_executable or sys.executable
    offline = wheelhouse.exists() and any(path.is_file() for path in wheelhouse.iterdir())
    if offline:
        progress("Verifying offline wheelhouse integrity ...")
        verify_wheelhouse_integrity(wheelhouse)
        progress("Offline wheelhouse integrity verified.")
    mode = "offline wheelhouse" if offline else "internet package index"
    progress(f"Installing {len(missing)} missing package(s) using {mode}.")
    started = time.monotonic()
    for index, dep in enumerate(missing, start=1):
        progress(f"[{index}/{len(missing)}] Installing {dep.requirement} ...")
        command = [python, "-m", "pip", "install", "--disable-pip-version-check"]
        if offline:
            command += ["--no-index", "--find-links", str(wheelhouse)]
        command.append(dep.requirement)
        last_error = ""
        for attempt in (1, 2):
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                progress(f"[{index}/{len(missing)}] Installed {dep.requirement} ({time.monotonic() - started:.1f}s elapsed).")
                break
            last_error = (result.stderr or result.stdout or "unknown pip error").strip()
            if attempt == 1:
                progress(f"Retrying {dep.requirement} once ...")
        else:
            raise RuntimeError(
                f"Critical dependency installation failed for {dep.requirement}.\n{last_error}\n"
                + ("Check that the wheelhouse contains the required compatible wheel." if offline else "Check internet access and Python/pip configuration.")
            )
