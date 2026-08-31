import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, IO, List

from app.services.client_store import (
    CLIENT_FORMAT,
    add_client,
    client_db_path,
    client_dir,
    client_uploads_path,
)

MANIFEST_NAME = "manifest.json"
DB_NAME = "restaurant_reconcile.db"


def _safe_members(zf: zipfile.ZipFile) -> List[zipfile.ZipInfo]:
    members = []
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or ".." in Path(name).parts:
            continue
        members.append(info)
    return members


def backup_client_zip(client: Dict[str, Any], dest: Path) -> Path:
    from app.core.database import dispose_sqlite_engine

    db_path = client_db_path(client)
    dispose_sqlite_engine(db_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": CLIENT_FORMAT,
        "name": client.get("name"),
        "slug": client.get("slug"),
        "address": client.get("address") or "",
        "gstin": client.get("gstin") or "",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "app": "HARSH's RestroReco",
    }
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2))
        if db_path.exists():
            copy_path = dest.with_suffix(".dbcopy")
            src = sqlite3.connect(str(db_path))
            dst = sqlite3.connect(str(copy_path))
            try:
                src.backup(dst)
                dst.commit()
            finally:
                dst.close()
                src.close()
            zf.write(copy_path, DB_NAME)
            try:
                copy_path.unlink()
            except OSError:
                pass
        uploads = client_uploads_path(client)
        if uploads.exists():
            for file_path in uploads.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, Path("uploads") / file_path.relative_to(uploads))
    return dest


def restore_client_from_zip(upload: IO[bytes], filename: str = "") -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "restore.zip"
        zip_path.write_bytes(upload.read())
        if not zipfile.is_zipfile(zip_path):
            raise ValueError("The file is not a client backup ZIP")
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in _safe_members(zf):
                zf.extract(info, extract_dir)
        manifest_file = extract_dir / MANIFEST_NAME
        if not manifest_file.exists():
            nested = list(extract_dir.rglob(MANIFEST_NAME))
            if nested:
                extract_dir = nested[0].parent
                manifest_file = nested[0]
        if not manifest_file.exists():
            raise ValueError("This ZIP is not a RestroReco client backup")
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Backup manifest is invalid") from exc
        if manifest.get("format") != CLIENT_FORMAT:
            raise ValueError("This ZIP is not a RestroReco client backup")
        db_file = extract_dir / DB_NAME
        if not db_file.exists():
            raise ValueError("Backup ZIP is missing the client database")
        name = (manifest.get("name") or Path(filename).stem or "Restored Client").strip()
        client = add_client(
            name,
            address=manifest.get("address") or "",
            gstin=manifest.get("gstin") or "",
        )
        target_db = client_db_path(client)
        shutil.copy2(db_file, target_db)
        uploads_src = extract_dir / "uploads"
        if uploads_src.exists():
            shutil.copytree(uploads_src, client_uploads_path(client), dirs_exist_ok=True)
        return client
