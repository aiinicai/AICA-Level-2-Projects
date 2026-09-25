"""Encrypted local document vault and actual ingestion pipeline."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.errors import DocumentError, StorageError, ValidationError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.db.connection import transaction
from app.documents.extract import ExtractionResult, extract_text
from app.documents.safety import ZipLimits, detect_media_type, safe_extract_zip, sanitize_filename
from app.security import aead
from app.security.audit import AuditService
from app.security.kdf import derive_subkey
from app.security.secure_store import atomic_write


def _fts_query(value: str) -> str:
    """Convert user text to a conservative literal-token FTS query."""
    tokens = re.findall(r"[\w@.+-]+", value, flags=re.UNICODE)
    if not tokens:
        raise ValidationError("Enter at least one searchable word.")
    return " AND ".join('"' + token.replace('"', '""') + '"' for token in tokens[:20])


def _parse_tags(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = value.split(",")
    else:
        values = value
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        tag = str(raw).strip()
        if not tag:
            continue
        if len(tag) > 80:
            raise ValidationError("A document tag is longer than 80 characters.")
        key = tag.casefold()
        if key not in seen:
            result.append(tag)
            seen.add(key)
    if len(result) > 50:
        raise ValidationError("A document may have at most 50 tags.")
    return result


@dataclass
class DocumentVault:
    connection: sqlite3.Connection
    vault_root: Path
    master_key: bytes
    audit: AuditService
    clock: Clock = SystemClock()
    max_upload_bytes: int = 100 * 1024 * 1024
    ocr_command: str = "tesseract"

    def __post_init__(self) -> None:
        if len(self.master_key) != 32:
            raise ValueError("master key must contain 32 bytes")
        self.vault_root.mkdir(parents=True, exist_ok=True)

    def _key(self, document_uuid: str) -> bytes:
        return derive_subkey(self.master_key, "document-vault", document_uuid)

    def _normalize_association(self, client_id: int | None, matter_id: int | None) -> tuple[int | None, int | None]:
        if client_id is not None and self.connection.execute(
            "SELECT 1 FROM clients WHERE id=? AND status!='DELETED'", (client_id,)
        ).fetchone() is None:
            raise ValidationError("Selected client was not found.")
        if matter_id is not None:
            row = self.connection.execute("SELECT client_id FROM matters WHERE id=?", (matter_id,)).fetchone()
            if row is None:
                raise ValidationError("Selected matter was not found.")
            matter_client = int(row[0])
            if client_id is not None and matter_client != client_id:
                raise ValidationError("Selected matter does not belong to the selected client.")
            client_id = client_id or matter_client
        return client_id, matter_id

    def find_duplicate(self, source: Path | str, *, client_id: int | None = None, matter_id: int | None = None) -> int | None:
        path = Path(source)
        if not path.is_file():
            raise DocumentError("Selected document does not exist or is not a regular file.")
        client_id, matter_id = self._normalize_association(client_id, matter_id)
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        row = self.connection.execute(
            """SELECT id FROM documents WHERE content_hash=? AND
               ((client_id=? ) OR (client_id IS NULL AND ? IS NULL)) AND
               ((matter_id=? ) OR (matter_id IS NULL AND ? IS NULL))""",
            (content_hash, client_id, client_id, matter_id, matter_id),
        ).fetchone()
        return int(row[0]) if row else None

    def ingest(
        self,
        source: Path | str,
        *,
        client_id: int | None = None,
        matter_id: int | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        source_label: str | None = None,
        force_ocr: bool = False,
        user_id: int | None = None,
    ) -> int:
        path = Path(source)
        if not path.is_file():
            raise DocumentError("Selected document does not exist or is not a regular file.")
        size = path.stat().st_size
        if size <= 0 or size > self.max_upload_bytes:
            raise DocumentError("Document is empty or exceeds the configured upload limit.")
        client_id, matter_id = self._normalize_association(client_id, matter_id)
        media_type = detect_media_type(path)
        if path.suffix.lower() == ".zip":
            raise DocumentError("Use ZIP import for archives so every contained file is validated.")
        clear = path.read_bytes()
        content_hash = hashlib.sha256(clear).hexdigest()
        duplicate = self.connection.execute(
            """SELECT id FROM documents WHERE content_hash=? AND
               ((client_id=? ) OR (client_id IS NULL AND ? IS NULL)) AND
               ((matter_id=? ) OR (matter_id IS NULL AND ? IS NULL))""",
            (content_hash, client_id, client_id, matter_id, matter_id),
        ).fetchone()
        if duplicate:
            return int(duplicate[0])
        try:
            extraction = extract_text(path, media_type, ocr_command=self.ocr_command, force_ocr=force_ocr)
        except DocumentError:
            raise
        document_uuid = str(uuid.uuid4())
        safe = sanitize_filename(path.name)
        shard = content_hash[:2]
        relative = Path(shard) / f"{document_uuid}.ibcvault"
        destination = self.vault_root / relative
        encrypted = aead.seal_container(
            self._key(document_uuid), clear,
            f"document:{document_uuid}:{content_hash}".encode("ascii"),
        )
        try:
            atomic_write(destination, encrypted)
        except OSError as exc:
            raise StorageError("Encrypted document could not be written. Check disk space and permissions.") from exc
        now = to_utc_iso(self.clock.now())
        clean_tags = _parse_tags(tags)
        clean_category = category.strip()[:200] if category and category.strip() else None
        try:
            with transaction(self.connection):
                cursor = self.connection.execute(
                    """INSERT INTO documents(
                        document_uuid,client_id,matter_id,original_filename,safe_filename,
                        media_type,category,content_hash,encrypted_path,size_bytes,source,
                        tags_json,ocr_status,review_status,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        document_uuid, client_id, matter_id, path.name, safe, media_type,
                        clean_category, content_hash, str(relative).replace("\\", "/"), size,
                        source_label, json.dumps(clean_tags, ensure_ascii=False),
                        extraction.ocr_status, "REVIEW_REQUIRED", now, now,
                    ),
                )
                document_id = int(cursor.lastrowid)
                if extraction.text:
                    self.connection.execute(
                        """INSERT INTO document_text(document_id,page_number,text_content,extraction_method,confidence,created_at)
                           VALUES(?,?,?,?,?,?)""",
                        (document_id, None, extraction.text, extraction.method, extraction.confidence, now),
                    )
                # Always index the filename, even when OCR/text extraction produced no body.
                self.connection.execute(
                    "INSERT INTO search_index(entity_type,entity_id,title,body,citation,verification_status) VALUES(?,?,?,?,?,?)",
                    ("document", str(document_id), safe, extraction.text or "", "", "REVIEW_REQUIRED"),
                )
                self.audit.append(
                    "DOCUMENT_IMPORTED", f"Imported encrypted document '{safe}'.",
                    entity_type="document", entity_id=document_id, user_id=user_id,
                    details={"sha256": content_hash, "size": size, "ocr_status": extraction.ocr_status},
                )
            return document_id
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def read(self, document_id: int) -> bytes:
        row = self.connection.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if row is None:
            raise ValidationError("Document was not found.")
        path = (self.vault_root / row["encrypted_path"]).resolve()
        try:
            path.relative_to(self.vault_root.resolve())
        except ValueError as exc:
            raise DocumentError("Stored document path failed containment validation.") from exc
        try:
            container = path.read_bytes()
        except OSError as exc:
            raise DocumentError("Encrypted document file is missing or unreadable.") from exc
        clear = aead.open_container(
            self._key(row["document_uuid"]), container,
            f"document:{row['document_uuid']}:{row['content_hash']}".encode("ascii"),
        )
        if hashlib.sha256(clear).hexdigest() != row["content_hash"]:
            raise DocumentError("Decrypted document hash does not match its database record.")
        return clear

    def metadata(self, document_id: int, *, text_limit: int = 50_000) -> dict[str, Any]:
        row = self.connection.execute(
            """SELECT d.*,c.name AS client_name,m.title AS matter_title
               FROM documents d
               LEFT JOIN clients c ON c.id=d.client_id
               LEFT JOIN matters m ON m.id=d.matter_id
               WHERE d.id=?""",
            (document_id,),
        ).fetchone()
        if row is None:
            raise ValidationError("Document was not found.")
        item = dict(row)
        try:
            item["tags"] = json.loads(item.pop("tags_json"))
        except (json.JSONDecodeError, TypeError):
            item["tags"] = []
            item.pop("tags_json", None)
        text_rows = self.connection.execute(
            "SELECT text_content,extraction_method,confidence FROM document_text WHERE document_id=? ORDER BY COALESCE(page_number,0),id",
            (document_id,),
        ).fetchall()
        full_text = "\n\n".join(str(r["text_content"]) for r in text_rows)
        item["extracted_text"] = full_text[:text_limit]
        item["text_truncated"] = len(full_text) > text_limit
        item["extraction_methods"] = sorted({str(r["extraction_method"]) for r in text_rows})
        return item

    def list_documents(
        self,
        *,
        query: str = "",
        client_id: int | None = None,
        matter_id: int | None = None,
        category: str = "",
        limit: int = 250,
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValidationError("Document result limit is invalid.")
        if client_id is not None or matter_id is not None:
            client_id, matter_id = self._normalize_association(client_id, matter_id)
        clauses: list[str] = []
        params: list[Any] = []
        if client_id is not None:
            clauses.append("d.client_id=?")
            params.append(client_id)
        if matter_id is not None:
            clauses.append("d.matter_id=?")
            params.append(matter_id)
        if category.strip():
            clauses.append("d.category=?")
            params.append(category.strip())
        q = query.strip()
        if q:
            matched = [
                int(row[0]) for row in self.connection.execute(
                    "SELECT entity_id FROM search_index WHERE search_index MATCH ? AND entity_type='document' LIMIT 500",
                    (_fts_query(q),),
                ).fetchall()
                if str(row[0]).isdigit()
            ]
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            metadata_clause = "(d.original_filename LIKE ? ESCAPE '\\' OR d.safe_filename LIKE ? ESCAPE '\\' OR COALESCE(d.category,'') LIKE ? ESCAPE '\\' OR d.tags_json LIKE ? ESCAPE '\\')"
            params_like = [f"%{escaped}%"] * 4
            if matched:
                placeholders = ",".join("?" for _ in matched)
                clauses.append(f"(d.id IN ({placeholders}) OR {metadata_clause})")
                params.extend(matched)
                params.extend(params_like)
            else:
                clauses.append(metadata_clause)
                params.extend(params_like)
        sql = """SELECT d.id,d.document_uuid,d.client_id,d.matter_id,d.original_filename,d.safe_filename,
                        d.media_type,d.category,d.content_hash,d.size_bytes,d.source,d.tags_json,d.version,
                        d.ocr_status,d.review_status,d.created_at,d.updated_at,
                        c.name AS client_name,m.title AS matter_title
                 FROM documents d
                 LEFT JOIN clients c ON c.id=d.client_id
                 LEFT JOIN matters m ON m.id=d.matter_id"""
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY d.created_at DESC,d.id DESC LIMIT ?"
        params.append(limit)
        items: list[dict[str, Any]] = []
        for row in self.connection.execute(sql, params).fetchall():
            item = dict(row)
            try:
                item["tags"] = json.loads(item.pop("tags_json"))
            except (json.JSONDecodeError, TypeError):
                item["tags"] = []
                item.pop("tags_json", None)
            items.append(item)
        return items

    def reprocess_ocr(self, document_id: int, *, user_id: int | None = None) -> ExtractionResult:
        row = self.connection.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if row is None:
            raise ValidationError("Document was not found.")
        if row["media_type"] != "application/pdf" and not str(row["media_type"]).startswith("image/"):
            raise DocumentError("OCR is available only for PDF and image documents.")
        clear = self.read(document_id)
        suffix = Path(str(row["safe_filename"])).suffix or ".bin"
        with tempfile.TemporaryDirectory(prefix="ibc-doc-ocr-") as temporary:
            source = Path(temporary) / ("source" + suffix)
            atomic_write(source, clear, mode=0o600)
            extraction = extract_text(
                source,
                str(row["media_type"]),
                ocr_command=self.ocr_command,
                force_ocr=True,
            )
        now = to_utc_iso(self.clock.now())
        with transaction(self.connection):
            self.connection.execute(
                "UPDATE documents SET ocr_status=?,updated_at=? WHERE id=?",
                (extraction.ocr_status, now, document_id),
            )
            if extraction.text:
                self.connection.execute("DELETE FROM document_text WHERE document_id=?", (document_id,))
                self.connection.execute(
                    """INSERT INTO document_text(document_id,page_number,text_content,extraction_method,confidence,created_at)
                       VALUES(?,?,?,?,?,?)""",
                    (document_id, None, extraction.text, extraction.method, extraction.confidence, now),
                )
                updated = self.connection.execute(
                    "UPDATE search_index SET title=?,body=?,verification_status=? WHERE entity_type='document' AND entity_id=?",
                    (row["safe_filename"], extraction.text, row["review_status"], str(document_id)),
                )
                if updated.rowcount == 0:
                    self.connection.execute(
                        "INSERT INTO search_index(entity_type,entity_id,title,body,citation,verification_status) VALUES(?,?,?,?,?,?)",
                        ("document", str(document_id), row["safe_filename"], extraction.text, "", row["review_status"]),
                    )
            self.audit.append(
                "DOCUMENT_OCR_REPROCESSED",
                f"Reprocessed OCR for document '{row['safe_filename']}'.",
                entity_type="document",
                entity_id=document_id,
                user_id=user_id,
                details={"ocr_status": extraction.ocr_status, "method": extraction.method, "text_length": len(extraction.text)},
            )
        return extraction

    def update_metadata(
        self,
        document_id: int,
        *,
        category: str | None,
        tags: list[str] | str | None,
        review_status: str,
        user_id: int | None = None,
    ) -> None:
        if review_status not in {"ACCEPTED", "REVIEW_REQUIRED", "REJECTED"}:
            raise ValidationError("Document review status is invalid.")
        row = self.connection.execute("SELECT safe_filename FROM documents WHERE id=?", (document_id,)).fetchone()
        if row is None:
            raise ValidationError("Document was not found.")
        clean_category = category.strip()[:200] if category and category.strip() else None
        clean_tags = _parse_tags(tags)
        now = to_utc_iso(self.clock.now())
        with transaction(self.connection):
            self.connection.execute(
                "UPDATE documents SET category=?,tags_json=?,review_status=?,updated_at=? WHERE id=?",
                (clean_category, json.dumps(clean_tags, ensure_ascii=False), review_status, now, document_id),
            )
            self.connection.execute(
                "UPDATE search_index SET verification_status=? WHERE entity_type='document' AND entity_id=?",
                (review_status, str(document_id)),
            )
            self.audit.append(
                "DOCUMENT_METADATA_UPDATED",
                f"Updated document metadata for '{row['safe_filename']}'.",
                entity_type="document",
                entity_id=document_id,
                user_id=user_id,
                details={"category": clean_category, "tags": clean_tags, "review_status": review_status},
            )

    def export(self, document_id: int, destination: Path) -> Path:
        row = self.connection.execute("SELECT safe_filename FROM documents WHERE id=?", (document_id,)).fetchone()
        if row is None:
            raise ValidationError("Document was not found.")
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / sanitize_filename(row["safe_filename"])
        if target.exists():
            target = destination / f"{target.stem}-{document_id}{target.suffix}"
        atomic_write(target, self.read(document_id), mode=0o600)
        return target

    def import_zip(
        self,
        archive: Path | str,
        *,
        client_id: int | None = None,
        matter_id: int | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        limits: ZipLimits = ZipLimits(),
        user_id: int | None = None,
    ) -> dict[str, Any]:
        archive_path = Path(archive)
        if archive_path.stat().st_size > self.max_upload_bytes:
            raise DocumentError("ZIP archive exceeds the configured upload limit.")
        if detect_media_type(archive_path) != "application/zip":
            raise DocumentError("Selected archive is not a valid ZIP file.")
        client_id, matter_id = self._normalize_association(client_id, matter_id)
        imported: list[int] = []
        duplicates: list[int] = []
        rejected: list[dict[str, str]] = []
        with tempfile.TemporaryDirectory(prefix="ibc-zip-") as temporary:
            files = safe_extract_zip(archive_path, Path(temporary), limits)
            for file in files:
                try:
                    if file.suffix.lower() == ".zip":
                        raise DocumentError("Nested ZIP archives are not imported automatically.")
                    duplicate_id = self.find_duplicate(file, client_id=client_id, matter_id=matter_id)
                    document_id = self.ingest(
                        file,
                        client_id=client_id,
                        matter_id=matter_id,
                        category=category,
                        tags=tags,
                        source_label=f"ZIP: {archive_path.name}",
                        user_id=user_id,
                    )
                    if duplicate_id is not None:
                        duplicates.append(document_id)
                    else:
                        imported.append(document_id)
                except DocumentError as exc:
                    rejected.append({"file": file.name, "reason": str(exc)})
        self.audit.append(
            "ZIP_IMPORT_COMPLETE",
            f"ZIP import completed: {len(imported)} imported, {len(duplicates)} duplicate, {len(rejected)} rejected.",
            entity_type="import",
            user_id=user_id,
            details={
                "archive": sanitize_filename(archive_path.name),
                "imported": len(imported),
                "duplicates": len(duplicates),
                "rejected": rejected,
            },
        )
        return {"imported_document_ids": imported, "duplicate_document_ids": duplicates, "rejected": rejected}
