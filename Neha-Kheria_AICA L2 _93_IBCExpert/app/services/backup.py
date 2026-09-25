"""Encrypted, integrity-verified local backup and transactional restore."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.core.errors import BackupError, IntegrityError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.db.connection import connect, integrity_check, transaction
from app.db.migrate import migrate
from app.documents.safety import contained_path
from app.security.audit import AuditService
from app.security.encrypted_stream import decrypt_file, encrypt_file
from app.security.kdf import derive_subkey

BACKUP_MAGIC = b"IBCBACK1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class BackupService:
    connection: sqlite3.Connection
    database_path: Path
    vault_root: Path
    backup_root: Path
    master_key: bytes
    audit: AuditService
    clock: Clock = SystemClock()

    def __post_init__(self) -> None:
        if len(self.master_key) != 32:
            raise ValueError("master key must contain 32 bytes")
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def _key(self, backup_uuid: str) -> bytes:
        return derive_subkey(self.master_key, "encrypted-backup", backup_uuid)

    def create(self, label: str | None = None, *, record: bool = True, backup_type: str = "MANUAL") -> Path:
        if backup_type not in {"MANUAL", "SCHEDULED", "PRE_RESTORE"}:
            raise BackupError("Backup type is invalid.")
        backup_uuid = str(uuid.uuid4())
        now = to_utc_iso(self.clock.now())
        filename = f"ibc-expert-{now[:10]}-{backup_uuid[:8]}.ibcbackup"
        target = self.backup_root / filename
        with tempfile.TemporaryDirectory(prefix="ibc-backup-") as temp_name:
            temp = Path(temp_name)
            snapshot = temp / "database.sqlite3"
            archive = temp / "payload.zip"
            snapshot_connection = sqlite3.connect(str(snapshot))
            try:
                self.connection.backup(snapshot_connection)
            finally:
                snapshot_connection.close()
            manifest_files: dict[str, dict[str, int | str]] = {
                "database.sqlite3": {"sha256": _sha256(snapshot), "size": snapshot.stat().st_size}
            }
            vault_files = [path for path in self.vault_root.rglob("*") if path.is_file()]
            for path in vault_files:
                relative = path.relative_to(self.vault_root).as_posix()
                manifest_files[f"vault/{relative}"] = {"sha256": _sha256(path), "size": path.stat().st_size}
            manifest = {
                "format": "IBC-EXPERT-BACKUP-1",
                "backup_uuid": backup_uuid,
                "created_at": now,
                "label": label,
                "files": manifest_files,
            }
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as bundle:
                bundle.write(snapshot, "database.sqlite3")
                for path in vault_files:
                    bundle.write(path, "vault/" + path.relative_to(self.vault_root).as_posix())
                bundle.writestr("manifest.json", json.dumps(manifest, separators=(",", ":"), sort_keys=True))
            encrypted_temp = target.with_suffix(target.suffix + ".tmp")
            try:
                with open(encrypted_temp, "xb") as output:
                    output.write(BACKUP_MAGIC + uuid.UUID(backup_uuid).bytes)
                stream_temp = temp / "stream.enc"
                encrypt_file(archive, stream_temp, self._key(backup_uuid), BACKUP_MAGIC + backup_uuid.encode("ascii"))
                with open(encrypted_temp, "ab") as output, open(stream_temp, "rb") as source:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                    output.flush(); os.fsync(output.fileno())
                os.replace(encrypted_temp, target)
            finally:
                encrypted_temp.unlink(missing_ok=True)
        digest = _sha256(target)
        if record:
            with transaction(self.connection):
                self.connection.execute(
                    """INSERT INTO backups(backup_uuid,path,content_hash,size_bytes,status,created_at,verified_at,backup_type,label)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (backup_uuid, str(target), digest, target.stat().st_size, "VALID", now, now, backup_type, label),
                )
                self.audit.append("BACKUP_CREATED", "Created encrypted local backup.", entity_type="backup", entity_id=backup_uuid, details={"sha256": digest, "size": target.stat().st_size, "backup_type": backup_type})
        return target

    def _decrypt_and_validate(self, backup: Path, destination: Path) -> tuple[str, dict]:
        try:
            with open(backup, "rb") as source:
                header = source.read(len(BACKUP_MAGIC) + 16)
                if len(header) != len(BACKUP_MAGIC) + 16 or not header.startswith(BACKUP_MAGIC):
                    raise BackupError("Backup file format is invalid.")
                backup_uuid = str(uuid.UUID(bytes=header[len(BACKUP_MAGIC):]))
                stream = destination / "payload.stream"
                with open(stream, "wb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
            archive = destination / "payload.zip"
            decrypt_file(stream, archive, self._key(backup_uuid), BACKUP_MAGIC + backup_uuid.encode("ascii"))
            extract = destination / "extract"
            extract.mkdir()
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                if "manifest.json" not in names or "database.sqlite3" not in names:
                    raise BackupError("Backup is missing its manifest or database.")
                for info in bundle.infolist():
                    if info.is_dir():
                        continue
                    target = contained_path(extract, info.filename)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(info) as src, open(target, "xb") as out:
                        shutil.copyfileobj(src, out, 1024 * 1024)
            manifest = json.loads((extract / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("format") != "IBC-EXPERT-BACKUP-1" or manifest.get("backup_uuid") != backup_uuid:
                raise BackupError("Backup manifest identity is invalid.")
            expected_files = manifest.get("files")
            if not isinstance(expected_files, dict):
                raise BackupError("Backup manifest file list is invalid.")
            actual_files = {path.relative_to(extract).as_posix() for path in extract.rglob("*") if path.is_file() and path.name != "manifest.json"}
            if actual_files != set(expected_files):
                raise BackupError("Backup contents do not match its manifest.")
            for relative, metadata in expected_files.items():
                path = contained_path(extract, relative)
                if path.stat().st_size != metadata["size"] or _sha256(path) != metadata["sha256"]:
                    raise BackupError(f"Backup integrity failed for {relative}.")
            restored_db = connect(extract / "database.sqlite3")
            try:
                ok, detail = integrity_check(restored_db)
                if not ok:
                    raise BackupError(f"Backup database integrity check failed: {detail}")
                migrate(restored_db)
            finally:
                restored_db.close()
            return backup_uuid, manifest
        except (OSError, zipfile.BadZipFile, json.JSONDecodeError, IntegrityError) as exc:
            if isinstance(exc, BackupError):
                raise
            raise BackupError("Backup is damaged, altered, or encrypted for a different installation profile.") from exc

    def verify(self, backup: Path | str) -> dict:
        backup = Path(backup)
        with tempfile.TemporaryDirectory(prefix="ibc-verify-") as temp:
            backup_uuid, manifest = self._decrypt_and_validate(backup, Path(temp))
            return {"valid": True, "backup_uuid": backup_uuid, "created_at": manifest["created_at"], "file_count": len(manifest["files"])}

    def restore(self, backup: Path | str) -> None:
        backup = Path(backup)
        with tempfile.TemporaryDirectory(prefix="ibc-restore-") as temp_name:
            temp = Path(temp_name)
            backup_uuid, manifest = self._decrypt_and_validate(backup, temp)
            extract = temp / "extract"
            safety = self.create(label="Automatic pre-restore safety backup", record=False, backup_type="PRE_RESTORE")
            staged_vault = temp / "staged-vault"
            source_vault = extract / "vault"
            if source_vault.exists():
                shutil.copytree(source_vault, staged_vault)
            else:
                staged_vault.mkdir()
            old_vault = self.vault_root.with_name(self.vault_root.name + ".pre-restore-" + uuid.uuid4().hex[:8])
            source_db = connect(extract / "database.sqlite3")
            try:
                if self.vault_root.exists():
                    os.replace(self.vault_root, old_vault)
                os.replace(staged_vault, self.vault_root)
                source_db.backup(self.connection)
            except Exception as exc:
                if self.vault_root.exists():
                    shutil.rmtree(self.vault_root, ignore_errors=True)
                if old_vault.exists():
                    os.replace(old_vault, self.vault_root)
                raise BackupError(f"Restore failed. Current information was preserved; safety backup: {safety.name}") from exc
            finally:
                source_db.close()
            shutil.rmtree(old_vault, ignore_errors=True)
            self.audit.append("BACKUP_RESTORED", "Restored a validated encrypted local backup.", entity_type="backup", entity_id=backup_uuid, details={"safety_backup": safety.name})
