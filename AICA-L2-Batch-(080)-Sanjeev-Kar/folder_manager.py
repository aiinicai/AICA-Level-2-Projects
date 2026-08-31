"""
folder_manager.py
-------------------
Recursive folder locking (encryption) and unlocking (decryption), built on
top of the streaming AEAD container format in encryption.py.

The folder's name and location NEVER change. Locking a folder called
"TaxDocs2024" leaves it at the same path, still called "TaxDocs2024" —
only its *contents* change (plaintext files -> `<name>.enc` files plus an
encrypted manifest, or back again on unlock).

Two independent protections are applied when locking:

1. ENCRYPTION (the real protection). Every file's contents become
   AES-256-GCM ciphertext. Unreadable without the password, no matter who
   has access to the disk.
2. ACCESS RESTRICTION (a deterrent, Windows/NTFS only). An explicit "Deny
   Read" permission is applied so the folder refuses to open in Explorer
   at all. See access_control.py for an honest account of what this does
   and does not stop — the folder's owner can always undo it through
   Windows' own security dialog, which is exactly why protection #1 is
   the one that actually matters.

Because protection #2 makes the folder unreadable to this app too, lock
state can no longer be detected by looking for the manifest *inside* the
folder. A registry of locked folder paths is therefore kept in the app's
own vault directory, and is the authoritative source for `is_locked()`
(with the in-folder manifest as a fallback for folders locked without
access restriction).

Safety model
~~~~~~~~~~~~
All operations for a given lock/unlock are confined to the user-selected
folder and two sibling temp paths derived from its name (a hidden working
directory and a hidden "previous version" holding directory). Nothing
outside that is ever read, written, or deleted.

Both locking and unlocking build the new version *completely* in a hidden
temp sibling directory first (encrypting/decrypting every file and
verifying it), while the folder at the real path is left completely
untouched. Only once that new version is fully built and verified does the
swap happen, and the swap itself is done as two back-to-back directory
*renames* (not copies — instant regardless of folder size, since they're
just filesystem directory-entry updates on the same volume), with the
previous version kept under a hidden name until the very end:

    1. rename <folder>            -> <folder>.<op>_old_<uuid>   (the real
       path briefly does not exist, but the complete original data is
       simply sitting under a different name right next to it — nothing
       was deleted, and this step is effectively instantaneous)
    2. rename <temp working dir>  -> <folder>                    (the new,
       already-fully-verified version is now live under the real name —
       also instantaneous)
    3. delete <folder>.<op>_old_<uuid>                            (only now,
       once the new version is confirmed in place, is the old version's
       disk space reclaimed)

If interrupted before step 1, the folder is completely untouched and only
the incomplete working temp directory needs cleaning up. If interrupted
between steps 1 and 2 (an exceedingly small window — a directory rename on
the same volume is not a bulk data operation), the previous version is
still fully intact under its `<op>_old_<uuid>` name and can be renamed back
manually. If interrupted between steps 2 and 3, the folder is already
correctly in its new state; the leftover `<op>_old_<uuid>` directory is
simply redundant and safe to delete.
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

import access_control
import config
import encryption
from access_control import AccessControlError
from security import SecurityError

ProgressCB = Optional[Callable[[str], None]]


class FolderManagerError(SecurityError):
    pass


MANIFEST_FILENAME = config.MANIFEST_RELPATH + ".enc"


@dataclass
class ManifestEntry:
    relpath: str
    sha256: str
    size: int


@dataclass
class Manifest:
    version: int
    original_name: str
    created_at: float
    files: List[ManifestEntry] = field(default_factory=list)
    empty_dirs: List[str] = field(default_factory=list)

    def to_json_bytes(self) -> bytes:
        return json.dumps(
            {
                "version": self.version,
                "original_name": self.original_name,
                "created_at": self.created_at,
                "files": [f.__dict__ for f in self.files],
                "empty_dirs": self.empty_dirs,
            },
            indent=2,
        ).encode("utf-8")

    @staticmethod
    def from_json_bytes(data: bytes) -> "Manifest":
        obj = json.loads(data.decode("utf-8"))
        return Manifest(
            version=obj["version"],
            original_name=obj["original_name"],
            created_at=obj["created_at"],
            files=[ManifestEntry(**f) for f in obj["files"]],
            empty_dirs=obj.get("empty_dirs", []),
        )


# ---------------------------------------------------------------------------
# Locked-folder registry
#
# Authoritative record of which folders this app has locked. Required
# because an access-restricted folder cannot be read by this app either,
# so the in-folder manifest is not always visible (see module docstring).
# ---------------------------------------------------------------------------


def _norm(folder_path: Path) -> str:
    return str(Path(folder_path).resolve())


def _same_path(a: str, b: str) -> bool:
    # Windows paths are case-insensitive; POSIX paths are not.
    if os.name == "nt":
        return a.casefold() == b.casefold()
    return a == b


def _load_registry() -> List[dict]:
    _migrate_legacy_layout_if_needed()
    registry_file = config.folder_registry_file()
    if not registry_file.exists():
        return []
    try:
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        entries = data.get("folders", [])
        return [e for e in entries if isinstance(e, dict) and "path" in e]
    except (json.JSONDecodeError, OSError):
        # A damaged registry must never make existing locked folders
        # unrecoverable — is_locked() still falls back to the in-folder
        # manifest, and unlock still works on any folder we can read.
        return []


def _save_registry(entries: List[dict]) -> None:
    registry_file = config.folder_registry_file()
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text(
        json.dumps({"version": 2, "folders": entries}, indent=2), encoding="utf-8"
    )
    config._restrict_permissions(registry_file)


def _migrate_legacy_layout_if_needed() -> None:
    """Version 1 of this app used a single global password + face for every
    folder. If that layout is present, fold it into one profile and point
    the folders it locked at that profile, so they remain unlockable with
    the credentials the user already has. Runs once; never destroys the
    legacy files, only copies them forward."""
    legacy_registry = config.legacy_registry_file()
    legacy_vault = config.legacy_password_vault_file()
    if not legacy_registry.exists() and not legacy_vault.exists():
        return
    if config.folder_registry_file().exists():
        return  # already migrated

    legacy_profile = "legacy-shared"
    try:
        if legacy_vault.exists():
            dst = config.profile_password_vault(legacy_profile)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(legacy_vault, dst)
        legacy_face = config.legacy_face_template_file()
        if legacy_face.exists():
            dst_face = config.profile_face_template(legacy_profile)
            dst_face.parent.mkdir(parents=True, exist_ok=True)
            if not dst_face.exists():
                shutil.copy2(legacy_face, dst_face)

        entries: List[dict] = []
        if legacy_registry.exists():
            data = json.loads(legacy_registry.read_text(encoding="utf-8"))
            for old in data.get("folders", []):
                if not isinstance(old, dict) or "path" not in old:
                    continue
                entries.append({
                    "path": old["path"],
                    "profile_id": legacy_profile,
                    "locked": True,
                    "locked_at": old.get("locked_at", time.time()),
                    "access_restricted": bool(old.get("access_restricted")),
                })
        _save_registry(entries)
    except (OSError, json.JSONDecodeError):
        # Migration is best-effort. Failing it must not block the app; the
        # legacy files are left untouched for manual recovery.
        pass


def _registry_entry(folder_path: Path) -> Optional[dict]:
    target = _norm(folder_path)
    for entry in _load_registry():
        if _same_path(entry["path"], target):
            return entry
    return None


def _upsert_entry(folder_path: Path, **fields) -> None:
    target = _norm(folder_path)
    entries = _load_registry()
    for entry in entries:
        if _same_path(entry["path"], target):
            entry.update(fields)
            break
    else:
        base = {"path": target, "profile_id": None, "locked": False}
        base.update(fields)
        entries.append(base)
    _save_registry(entries)


def new_profile_id() -> str:
    """A fresh, random identifier for a folder's credential profile. Random
    rather than derived from the path, so profile directory names leak
    nothing about which folders are protected, and so a folder can be
    renamed without invalidating its credentials."""
    return uuid.uuid4().hex


def delete_profile(profile_id: str) -> None:
    """Permanently removes a credential profile's stored password vault and
    face template. Only ever used to discard a profile that was abandoned
    part-way through setup — never for a profile that is protecting a
    locked folder, since that would make the folder undecryptable."""
    if not profile_id:
        return
    in_use = any(
        e.get("profile_id") == profile_id and e.get("locked")
        for e in _load_registry()
    )
    if in_use:
        raise FolderManagerError(
            "Refusing to delete credentials that are protecting a locked folder."
        )
    shutil.rmtree(config.profile_dir(profile_id), ignore_errors=True)


def profile_id_for(folder_path: Path) -> Optional[str]:
    entry = _registry_entry(folder_path)
    return entry.get("profile_id") if entry else None


def assign_profile(folder_path: Path, profile_id: str) -> None:
    """Associates a credential profile with a folder without locking it."""
    _upsert_entry(folder_path, profile_id=profile_id)


def has_credentials(folder_path: Path) -> bool:
    """Whether this folder already has its own password + face enrolled."""
    profile_id = profile_id_for(folder_path)
    if not profile_id:
        return False
    return config.profile_password_vault(profile_id).exists()


def list_known_folders() -> List[dict]:
    """Every folder this app has credentials for, locked or not, newest
    first. `exists` reports whether the folder is still on disk."""
    entries = sorted(_load_registry(), key=lambda e: e.get("locked_at", 0), reverse=True)
    for entry in entries:
        entry["exists"] = Path(entry["path"]).is_dir()
    return entries


def list_locked_folders() -> List[dict]:
    """Only the folders currently locked, newest first."""
    return [e for e in list_known_folders() if e.get("locked")]


def forget_folder(folder_path: Path, delete_profile: bool = False) -> None:
    """Drops a registry entry (e.g. the folder was deleted or moved outside
    the app). Never touches the folder itself. Optionally also deletes the
    stored credentials for it, which is irreversible."""
    target = _norm(folder_path)
    entries = _load_registry()
    remaining = []
    removed_profile = None
    for entry in entries:
        if _same_path(entry["path"], target):
            removed_profile = entry.get("profile_id")
        else:
            remaining.append(entry)
    _save_registry(remaining)

    if delete_profile and removed_profile:
        still_used = any(e.get("profile_id") == removed_profile for e in remaining)
        if not still_used:
            shutil.rmtree(config.profile_dir(removed_profile), ignore_errors=True)


# Kept under the old name so existing callers/tests keep working.
forget_locked_folder = forget_folder


def is_locked(folder_path: Path) -> bool:
    """Registry is authoritative; the in-folder manifest is a fallback for
    folders locked without access restriction (or on non-Windows)."""
    entry = _registry_entry(folder_path)
    if entry is not None:
        return bool(entry.get("locked"))
    try:
        return (Path(folder_path) / MANIFEST_FILENAME).is_file()
    except OSError:
        return False


def _validate_folder(folder_path: Path) -> Path:
    folder_path = Path(folder_path).resolve()
    if not folder_path.exists() or not folder_path.is_dir():
        raise FolderManagerError("The selected path is not an existing folder.")
    if folder_path == config.APP_DATA_DIR or config.APP_DATA_DIR in folder_path.parents:
        raise FolderManagerError("Refusing to operate on the application's own data directory.")
    return folder_path


def _iter_files_and_empty_dirs(root: Path):
    files = []
    empty_dirs = []
    for dirpath, dirnames, filenames in _walk_sorted(root):
        rel_dir = Path(dirpath).relative_to(root)
        if not dirnames and not filenames and str(rel_dir) != ".":
            empty_dirs.append(rel_dir.as_posix())
        for name in filenames:
            full = Path(dirpath) / name
            rel = full.relative_to(root)
            files.append((full, rel.as_posix()))
    return files, empty_dirs


def _walk_sorted(root: Path):
    import os
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        filenames.sort()
        yield dirpath, dirnames, filenames


def _swap_in(folder_path: Path, new_dir: Path, op: str, status) -> None:
    """Atomically-as-possible replaces folder_path's contents with new_dir's
    contents, keeping folder_path's name unchanged throughout. See module
    docstring for the safety reasoning behind this exact ordering."""
    old_dir = folder_path.parent / f".{folder_path.name}.{op}_old_{uuid.uuid4().hex[:8]}"
    status("Finalizing...")
    folder_path.rename(old_dir)
    try:
        new_dir.rename(folder_path)
    except Exception:
        # Put the original back exactly as it was before giving up.
        old_dir.rename(folder_path)
        raise
    status("Cleaning up previous version...")
    shutil.rmtree(old_dir)


def lock_folder(
    folder_path: Path,
    master_key: bytes,
    profile_id: str,
    progress_cb: ProgressCB = None,
) -> Path:
    def status(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)

    folder_path = _validate_folder(folder_path)
    if is_locked(folder_path):
        raise FolderManagerError("This folder is already locked.")

    temp_dir = folder_path.parent / f".{folder_path.name}.locking_tmp_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=False, exist_ok=False)

    try:
        status("Scanning folder...")
        files, empty_dirs = _iter_files_and_empty_dirs(folder_path)
        manifest = Manifest(version=1, original_name=folder_path.name, created_at=time.time())

        for index, (src_file, relpath) in enumerate(files, start=1):
            status(f"Encrypting {relpath} ({index}/{len(files)})...")
            original_sha256 = encryption.sha256_of_file(src_file)
            dst_file = temp_dir / (relpath + ".enc")
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            aad = relpath.encode("utf-8")

            encryption.encrypt_file(src_file, dst_file, master_key, aad)

            # Verify before trusting this file: decrypt to a scratch file and
            # hash-compare against the original plaintext.
            scratch = dst_file.with_suffix(dst_file.suffix + ".verify")
            try:
                encryption.decrypt_file(dst_file, scratch, master_key, aad)
                if encryption.sha256_of_file(scratch) != original_sha256:
                    raise FolderManagerError(f"Verification mismatch after encrypting '{relpath}'.")
            finally:
                if scratch.exists():
                    scratch.unlink()

            manifest.files.append(
                ManifestEntry(relpath=relpath, sha256=original_sha256, size=src_file.stat().st_size)
            )

        manifest.empty_dirs = empty_dirs

        status("Writing manifest...")
        manifest_plain_tmp = temp_dir / "__manifest_plain__.tmp"
        manifest_plain_tmp.write_bytes(manifest.to_json_bytes())
        try:
            manifest_dst = temp_dir / MANIFEST_FILENAME
            encryption.encrypt_file(
                manifest_plain_tmp, manifest_dst, master_key, config.MANIFEST_RELPATH.encode("utf-8")
            )
        finally:
            manifest_plain_tmp.unlink(missing_ok=True)

        _swap_in(folder_path, temp_dir, "locking", status)

        # Encryption has fully succeeded at this point. Everything below is
        # the second, best-effort layer: if restricting access fails, the
        # folder is still properly encrypted, so we record the outcome and
        # let the caller warn rather than failing the whole operation and
        # leaving the user unsure whether their data was protected.
        access_restricted = False
        settings = config.get_settings()
        if settings.get("restrict_folder_access", True) and access_control.is_available():
            status("Restricting folder access...")
            try:
                access_control.deny_access(folder_path)
                access_restricted = True
            except AccessControlError as exc:
                status(f"Warning: folder is encrypted, but access could not be restricted. {exc}")

        _upsert_entry(
            folder_path,
            profile_id=profile_id,
            locked=True,
            locked_at=time.time(),
            access_restricted=access_restricted,
        )

        status("Encryption completed.")
        return folder_path

    except Exception:
        status("Encryption failed.")
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def unlock_folder(
    folder_path: Path,
    master_key: bytes,
    progress_cb: ProgressCB = None,
) -> Path:
    def status(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)

    folder_path = _validate_folder(folder_path)
    if not is_locked(folder_path):
        raise FolderManagerError("This folder is not locked.")

    # Access must be restored before anything can be read out of the folder
    # — including by this app. If this fails we stop immediately and tell the
    # user the exact command to fix it by hand, rather than proceeding into
    # a confusing cascade of permission errors.
    entry = _registry_entry(folder_path)
    was_restricted = bool(entry and entry.get("access_restricted")) or access_control.is_access_denied(folder_path)
    if was_restricted:
        status("Restoring folder access...")
        try:
            access_control.restore_access(folder_path)
        except AccessControlError as exc:
            raise FolderManagerError(str(exc)) from exc

    def _reapply_restriction_after_failure() -> None:
        """Leave the folder locked-and-restricted exactly as we found it if
        the unlock did not complete — a failed unlock attempt must never
        quietly downgrade the folder's protection."""
        if not was_restricted:
            return
        try:
            access_control.deny_access(folder_path)
        except AccessControlError:
            pass  # already reported via the primary exception

    temp_dir = folder_path.parent / f".{folder_path.name}.unlocking_tmp_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=False, exist_ok=False)

    try:
        status("Reading manifest...")
        manifest_src = folder_path / MANIFEST_FILENAME
        manifest_plain_tmp = temp_dir / "__manifest_plain__.tmp"
        encryption.decrypt_file(
            manifest_src, manifest_plain_tmp, master_key, config.MANIFEST_RELPATH.encode("utf-8")
        )
        manifest = Manifest.from_json_bytes(manifest_plain_tmp.read_bytes())
        manifest_plain_tmp.unlink(missing_ok=True)

        total = len(manifest.files)
        for index, entry in enumerate(manifest.files, start=1):
            status(f"Decrypting {entry.relpath} ({index}/{total})...")
            src_file = folder_path / (entry.relpath + ".enc")
            if not src_file.exists():
                raise FolderManagerError(f"Encrypted file for '{entry.relpath}' is missing.")
            dst_file = temp_dir / entry.relpath
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            aad = entry.relpath.encode("utf-8")

            encryption.decrypt_file(src_file, dst_file, master_key, aad)

            actual_sha256 = encryption.sha256_of_file(dst_file)
            if actual_sha256 != entry.sha256:
                raise FolderManagerError(
                    f"Integrity check failed for '{entry.relpath}': file does not match the original."
                )

        for rel_dir in manifest.empty_dirs:
            (temp_dir / rel_dir).mkdir(parents=True, exist_ok=True)

        _swap_in(folder_path, temp_dir, "unlocking", status)
        # Keep the folder's profile on record so re-locking it later reuses
        # the same password and face rather than silently starting over.
        _upsert_entry(folder_path, locked=False, access_restricted=False)

        status("Folder unlocked.")
        return folder_path

    except Exception:
        status("Decryption failed. The locked folder has not been modified.")
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        _reapply_restriction_after_failure()
        raise


def find_stale_temp_dirs(parent: Path) -> List[Path]:
    """Locates leftover working/previous-version directories from a
    previous interrupted operation, for the user to review and remove. They
    are never deleted automatically."""
    parent = Path(parent)
    if not parent.exists():
        return []
    markers = ("locking_tmp_", "unlocking_tmp_", "locking_old_", "unlocking_old_")
    stale = []
    for child in parent.iterdir():
        if child.is_dir() and any(marker in child.name for marker in markers):
            stale.append(child)
    return stale
