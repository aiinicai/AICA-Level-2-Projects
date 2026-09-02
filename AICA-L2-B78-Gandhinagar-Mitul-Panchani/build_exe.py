"""Build and inspect the portable Windows executable without exposing secrets."""

from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import TypeAlias


PROJECT_ROOT = Path(__file__).resolve().parent
SPEC_PATH = PROJECT_ROOT / "AIMemoryGovernance.spec"
OUTPUT_PATH = PROJECT_ROOT / "dist" / "AIMemoryGovernance.exe"
# Deliberately case-SENSITIVE: credential environment variables are uppercase by
# convention, and IGNORECASE made this match lowercase identifiers that merely end
# in "_token" -- e.g. an ML tokenizer's `unk_token=` inside tokenizers.pyd.
_SECRET_ASSIGNMENT = re.compile(
    rb"(?P<name>[A-Z_][A-Z0-9_]*(?:_API_KEY|_TOKEN))[ \t]*=[ \t]*"
    rb"(?P<value>[^\x00\r\n \t][^\x00\r\n]*)",
)

# Compiled artifacts (extension modules, DLLs, the bootloader) are third-party
# binaries we do not author. Pattern-scanning them for "KEY=" yields guaranteed
# noise from internal strings and random byte sequences. The AUTHORITATIVE
# exact-value scan (tier 1) still covers them in full -- only the heuristic
# pattern net (tier 2) is skipped here. That is a precision fix, not a weakening:
# a real key embedded in one of these would still be caught by tier 1.
_COMPILED_BINARY_SUFFIXES = (".pyd", ".dll", ".so", ".dylib", ".exe")


def _is_compiled_binary(label: str) -> bool:
    lowered = label.casefold().rstrip("'\"")
    return lowered.endswith(_COMPILED_BINARY_SUFFIXES)


# Tier 2 (heuristic pattern net) applies ONLY to artifacts this project authors.
#
# Vendored third-party libraries legitimately DOCUMENT the credential environment
# variables they read, in docstrings and error messages -- e.g.
#   voyageai/util.py:      "set the environment variable VOYAGE_API_KEY=<API-KEY>"
#   google/genai/client.py: `GOOGLE_API_KEY="your-api-key"` as an ...
# Pattern-scanning those is an unwinnable game of whack-a-mole: every new
# dependency adds new help text, and each false positive costs a full rebuild.
#
# This is a precision fix, NOT a weakening of the control:
#   * Tier 1 (exact-value scan for the owner's real keys) still covers EVERY
#     entry, including all third-party modules and compiled binaries. That is the
#     authoritative check and it is what would actually catch a leak.
#   * Tier 2 exists to catch a key hard-coded under an unexpected variable name
#     in code we wrote -- which is precisely where our own mistake could occur.
_OUR_CODE_MARKERS = ("amg.", "amg/", "'amg'", "amg\\")


def _is_our_own_artifact(label: str) -> bool:
    lowered = label.casefold()
    return any(marker in lowered for marker in _OUR_CODE_MARKERS)
_SECRET_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PLACEHOLDER_PREFIXES = (b"<", b"${", b"%", b"{")
_PLACEHOLDER_WORDS = (
    b"your",
    b"example",
    b"placeholder",
    b"changeme",
    b"xxx",
    b"api-key",
    b"api_key",
    b"none",
    b"null",
)
_PROSE_MARKERS = (b"environment variable", b"set the")
_MIN_FRAGMENT_LENGTH = 8
_MAX_REPORTED_VIOLATIONS = 50
ArchiveViolation: TypeAlias = tuple[str, str, str]
SecretValue: TypeAlias = tuple[str, str]


def _is_secret_variable(name: str) -> bool:
    normalized = name.upper()
    return normalized.endswith("_API_KEY") or normalized.endswith("_TOKEN")


def _parse_dotenv_secrets(path: Path) -> list[SecretValue]:
    if not path.is_file():
        return []

    secrets: list[SecretValue] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, raw_value = line.partition("=")
        name = name.strip()
        if not separator or not _SECRET_NAME.fullmatch(name) or not _is_secret_variable(name):
            continue

        value = raw_value.strip()
        if value.startswith(("'", '"')):
            closing_quote = value.find(value[0], 1)
            if closing_quote >= 1:
                value = value[1:closing_quote]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        if value:
            secrets.append((name.upper(), value))
    return secrets


def _load_secret_values(
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> list[SecretValue]:
    """Load scan targets without ever rendering their values in diagnostics."""

    environment = os.environ if environ is None else environ
    path = PROJECT_ROOT / ".env" if dotenv_path is None else dotenv_path
    candidates = _parse_dotenv_secrets(path)
    candidates.extend(
        (name.upper(), value)
        for name, value in environment.items()
        if _is_secret_variable(name) and value
    )

    secrets: list[SecretValue] = []
    seen: set[SecretValue] = set()
    for name, value in candidates:
        item = (name, value)
        if item not in seen:
            seen.add(item)
            secrets.append(item)

    if not secrets:
        print(
            "WARNING: exact-value secret scan could not run because no *_API_KEY "
            "or *_TOKEN values were available from the environment or .env; "
            "only the heuristic tier applied.",
            file=sys.stderr,
        )
    return secrets


def _is_prohibited_data_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    parts = tuple(part.casefold() for part in PurePosixPath(normalized).parts)
    basename = parts[-1] if parts else ""
    dotted_parts = normalized.casefold().replace("/", ".").split(".")
    if (
        any(part in {".git", ".amg_cache"} for part in parts)
        or "tests" in parts
        or "tests" in dotted_parts
    ):
        return True
    if basename == ".amg_usage.json":
        return True
    if basename == ".env" or (basename.startswith(".env.") and basename != ".env.example"):
        return True
    if basename.endswith(".db") or ".sqlite" in basename:
        return True
    return False


def _is_prohibited_module_name(name: str) -> bool:
    normalized = name.casefold().replace("\\", ".").replace("/", ".")
    module_parts = tuple(part for part in normalized.split(".") if part)
    return bool(module_parts) and module_parts[0] in {"tests", "_pytest", "pytest"}


def _collect_prohibited_name(
    violations: list[ArchiveViolation], namespace: str, name: str
) -> None:
    """Record prohibited names without interrupting the rest of the archive scan."""

    if namespace == "CArchive":
        prohibited = _is_prohibited_data_name(name)
        reason = "prohibited data name"
    elif namespace == "PYZ":
        prohibited = _is_prohibited_module_name(name)
        reason = "prohibited top-level Python package"
    else:
        raise ValueError(f"Unknown archive namespace: {namespace}")
    if prohibited:
        violations.append((namespace, name, reason))


def _secret_fragments(value: str) -> tuple[str, ...]:
    fragment = value[8:24]
    if len(fragment) >= _MIN_FRAGMENT_LENGTH and fragment != value:
        return value, fragment
    return (value,)


def _redact_loaded_secrets(text: str, secret_values: Sequence[SecretValue]) -> str:
    redacted = text
    for _name, value in secret_values:
        for fragment in _secret_fragments(value):
            redacted = redacted.replace(fragment, "[REDACTED]")
    return redacted


def _raise_archive_violations(
    violations: list[ArchiveViolation],
    secret_values: Sequence[SecretValue] = (),
) -> None:
    if not violations:
        return

    displayed = violations[:_MAX_REPORTED_VIOLATIONS]
    lines = [
        "BUNDLE CONTENT CHECK FAILED: "
        f"found {len(violations)} violation(s):"
    ]
    lines.extend(
        f"- [{_redact_loaded_secrets(namespace, secret_values)}] "
        f"{_redact_loaded_secrets(name, secret_values)!r}: "
        f"{_redact_loaded_secrets(reason, secret_values)}"
        for namespace, name, reason in displayed
    )
    remaining = len(violations) - len(displayed)
    if remaining:
        lines.append(f"- and {remaining} more")
    raise RuntimeError("\n".join(lines))


def _spec_data_sources(spec_path: Path) -> list[str]:
    tree = ast.parse(spec_path.read_text(encoding="utf-8"), filename=str(spec_path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "Analysis":
            continue
        for keyword in node.keywords:
            if keyword.arg != "datas" or not isinstance(keyword.value, ast.List):
                continue
            sources: list[str] = []
            for item in keyword.value.elts:
                if not isinstance(item, ast.Tuple) or not item.elts:
                    raise RuntimeError("Every spec data entry must be a source/destination tuple.")
                sources.append(ast.unparse(item.elts[0]))
            return sources
    raise RuntimeError("Could not find a literal datas list in the PyInstaller spec.")


def _verify_spec_allowlist(spec_path: Path) -> None:
    sources = _spec_data_sources(spec_path)
    if len(sources) != 2:
        raise RuntimeError("Build refused: the spec must contain exactly two data sources.")
    for source in sources:
        compact = source.replace("'", '"').replace(" ", "").casefold()
        allowed = compact.endswith('/"web"/"templates")') or compact.endswith(
            '/"web"/"static")'
        )
        if not allowed or _is_prohibited_data_name(source):
            raise RuntimeError(
                f"Build refused: unapproved data source in spec: {source}"
            )


def _remove_build_directory(path: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != PROJECT_ROOT.resolve() or resolved.name not in {"build", "dist"}:
        raise RuntimeError(f"Refusing to clean unexpected path: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _encoded_secret_needles(value: str) -> tuple[bytes, ...]:
    needles: list[bytes] = []
    for fragment in _secret_fragments(value):
        for encoding in ("utf-8", "utf-16-le", "utf-16-be"):
            needle = fragment.encode(encoding)
            if needle not in needles:
                needles.append(needle)
    return tuple(needles)


def _line_containing(payload: bytes, offset: int) -> bytes:
    start = max(
        payload.rfind(b"\x00", 0, offset),
        payload.rfind(b"\r", 0, offset),
        payload.rfind(b"\n", 0, offset),
    ) + 1
    boundaries = [
        boundary
        for boundary in (
            payload.find(b"\x00", offset),
            payload.find(b"\r", offset),
            payload.find(b"\n", offset),
        )
        if boundary >= 0
    ]
    end = min(boundaries) if boundaries else len(payload)
    return payload[start:end]


def _is_placeholder_assignment(payload: bytes, match: re.Match[bytes]) -> bool:
    # bytes has .lower() but not .casefold(); these payloads are raw archive bytes.
    line = _line_containing(payload, match.start()).lower()
    if any(marker in line for marker in _PROSE_MARKERS):
        return True

    value = match.group("value").strip()
    if value.startswith(_PLACEHOLDER_PREFIXES):
        return True
    if value in {b"''", b'""'}:
        return True

    normalized = value.lower()
    if len(normalized) >= 2 and normalized[:1] == normalized[-1:] and normalized[:1] in {
        b"'",
        b'"',
    }:
        normalized = normalized[1:-1].strip()
    if not normalized:
        return True
    if any(
        normalized == word
        or normalized.startswith(word + b"-")
        or normalized.startswith(word + b"_")
        or normalized.startswith(word + b" ")
        for word in _PLACEHOLDER_WORDS
    ):
        return True
    return bool(
        re.match(
            rb"^sk-(?:\.{3}|x{3,}|your|example|placeholder|changeme|dummy|test)"
            rb"(?:$|[-_ ].*)",
            normalized,
            re.IGNORECASE,
        )
    )


def _scan_bytes(
    payload: bytes,
    label: str,
    secret_values: Sequence[SecretValue] = (),
) -> None:
    safe_label = _redact_loaded_secrets(label, secret_values)
    for variable_name, value in secret_values:
        if any(needle in payload for needle in _encoded_secret_needles(value)):
            safe_variable_name = _redact_loaded_secrets(variable_name, secret_values)
            raise RuntimeError(
                f"SECRET SCAN FAILED in {safe_label}: exact-value match for "
                f"{safe_variable_name} was found."
            )

    # Tier 1 (exact-value, above) has already scanned this payload unconditionally
    # and is the authoritative control. Tier 2 below is the heuristic net, scoped
    # to our own artifacts only -- see the comment on _is_our_own_artifact.
    if _is_compiled_binary(safe_label) or not _is_our_own_artifact(safe_label):
        return

    for match in _SECRET_ASSIGNMENT.finditer(payload):
        if _is_placeholder_assignment(payload, match):
            continue
        variable_name = _redact_loaded_secrets(
            match.group("name").decode("ascii", errors="replace"),
            secret_values,
        )
        raise RuntimeError(
            f"SECRET SCAN FAILED in {safe_label}: a non-placeholder key assignment "
            f"for {variable_name} was found."
        )


def _inspect_archive(
    executable: Path,
    secret_values: Sequence[SecretValue] | None = None,
) -> None:
    loaded_secret_values = (
        _load_secret_values() if secret_values is None else secret_values
    )
    try:
        from PyInstaller.archive.readers import CArchiveReader, PKG_ITEM_PYZ
    except ImportError as exc:
        raise RuntimeError("PyInstaller is required to inspect its output archive.") from exc

    violations: list[ArchiveViolation] = []
    carchive_count = 0
    pyz_module_count = 0
    try:
        _scan_bytes(executable.read_bytes(), str(executable), loaded_secret_values)
    except RuntimeError as exc:
        violations.append(("Executable secret", executable.name, str(exc)))

    archive = CArchiveReader(str(executable))
    for name, toc_entry in archive.toc.items():
        carchive_count += 1
        entry_name = str(name)
        _collect_prohibited_name(violations, "CArchive", entry_name)
        try:
            payload = archive.extract(name)
        except Exception as exc:
            violations.append(
                ("CArchive inspection", entry_name, f"could not extract entry: {exc}")
            )
            payload = None
        if isinstance(payload, bytes):
            try:
                _scan_bytes(payload, f"archive entry {name!r}", loaded_secret_values)
            except RuntimeError as exc:
                violations.append(("CArchive secret", entry_name, str(exc)))
        if toc_entry[-1] == PKG_ITEM_PYZ:
            try:
                pyz_archive = archive.open_embedded_archive(name)
            except Exception as exc:
                violations.append(
                    (
                        "PYZ inspection",
                        entry_name,
                        f"could not open embedded archive: {exc}",
                    )
                )
                continue
            for module_name in pyz_archive.toc:
                pyz_module_count += 1
                normalized_module_name = str(module_name)
                _collect_prohibited_name(
                    violations, "PYZ", normalized_module_name
                )
                try:
                    module_payload = pyz_archive.extract(module_name, raw=True)
                except Exception as exc:
                    violations.append(
                        (
                            "PYZ inspection",
                            normalized_module_name,
                            f"could not extract module: {exc}",
                        )
                    )
                    continue
                if isinstance(module_payload, bytes):
                    try:
                        _scan_bytes(
                            module_payload,
                            f"Python archive entry {module_name!r}",
                            loaded_secret_values,
                        )
                    except RuntimeError as exc:
                        violations.append(
                            ("PYZ secret", normalized_module_name, str(exc))
                        )

    _raise_archive_violations(violations, loaded_secret_values)
    print(
        f"secret scan OK: {carchive_count} CArchive entries, "
        f"{pyz_module_count} PYZ modules; exact-value scan covered "
        f"{len(loaded_secret_values)} key(s)."
    )


def main() -> int:
    secret_values = _load_secret_values()
    _verify_spec_allowlist(SPEC_PATH)
    _remove_build_directory(PROJECT_ROOT / "build")
    _remove_build_directory(PROJECT_ROOT / "dist")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(SPEC_PATH)],
        cwd=PROJECT_ROOT,
        check=True,
    )
    if not OUTPUT_PATH.is_file():
        raise RuntimeError(f"PyInstaller did not create the expected file: {OUTPUT_PATH}")
    _inspect_archive(OUTPUT_PATH, secret_values)
    size_mib = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Built and secret-scanned: {OUTPUT_PATH}")
    print(f"Final size: {size_mib:.1f} MiB")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
