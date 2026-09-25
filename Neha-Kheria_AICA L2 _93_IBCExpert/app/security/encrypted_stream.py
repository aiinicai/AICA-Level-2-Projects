"""Chunked authenticated container for large vault backups."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from app.core.errors import IntegrityError
from app.security import aead

MAGIC = b"IBCESTR1"
CHUNK = b"D"
FINAL = b"F"
DEFAULT_CHUNK_SIZE = 1024 * 1024


def encrypt_file(source: Path, destination: Path, key: bytes, context: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE) -> tuple[int, str]:
    if chunk_size < 4096 or chunk_size > 16 * 1024 * 1024:
        raise ValueError("encrypted stream chunk size is invalid")
    digest = hashlib.sha256()
    total = 0
    count = 0
    with open(source, "rb") as reader, open(destination, "xb") as writer:
        writer.write(MAGIC + struct.pack(">I", chunk_size))
        while True:
            clear = reader.read(chunk_size)
            if not clear:
                break
            digest.update(clear)
            total += len(clear)
            record_context = context + b"/chunk/" + struct.pack(">Q", count)
            payload = aead.encrypt(key, clear, record_context)
            writer.write(CHUNK + struct.pack(">QI", count, len(payload)) + payload)
            count += 1
        final_clear = json.dumps(
            {"chunks": count, "size": total, "sha256": digest.hexdigest()},
            separators=(",", ":"), sort_keys=True,
        ).encode("ascii")
        final_payload = aead.encrypt(key, final_clear, context + b"/final")
        writer.write(FINAL + struct.pack(">QI", count, len(final_payload)) + final_payload)
        writer.flush()
    return total, digest.hexdigest()


def decrypt_file(source: Path, destination: Path, key: bytes, context: bytes, max_output_bytes: int = 20 * 1024 * 1024 * 1024) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    expected_index = 0
    final_seen = False
    with open(source, "rb") as reader, open(destination, "xb") as writer:
        header = reader.read(len(MAGIC) + 4)
        if len(header) != len(MAGIC) + 4 or not header.startswith(MAGIC):
            raise IntegrityError("Encrypted backup container format is invalid.")
        chunk_size = struct.unpack(">I", header[len(MAGIC):])[0]
        if chunk_size < 4096 or chunk_size > 16 * 1024 * 1024:
            raise IntegrityError("Encrypted backup chunk size is invalid.")
        while True:
            kind = reader.read(1)
            if not kind:
                break
            record_header = reader.read(12)
            if len(record_header) != 12:
                raise IntegrityError("Encrypted backup record is truncated.")
            index, length = struct.unpack(">QI", record_header)
            if index != expected_index or length < aead.NONCE_SIZE + aead.TAG_SIZE or length > chunk_size + 4096:
                raise IntegrityError("Encrypted backup record sequence is invalid.")
            payload = reader.read(length)
            if len(payload) != length:
                raise IntegrityError("Encrypted backup record is truncated.")
            if kind == CHUNK:
                if final_seen:
                    raise IntegrityError("Encrypted backup contains data after its final record.")
                clear = aead.decrypt(key, payload, context + b"/chunk/" + struct.pack(">Q", index))
                total += len(clear)
                if total > max_output_bytes:
                    raise IntegrityError("Encrypted backup expands beyond the permitted size.")
                digest.update(clear)
                writer.write(clear)
                expected_index += 1
            elif kind == FINAL:
                clear = aead.decrypt(key, payload, context + b"/final")
                try:
                    metadata = json.loads(clear.decode("ascii"))
                except Exception as exc:
                    raise IntegrityError("Encrypted backup final record is invalid.") from exc
                if metadata != {"chunks": expected_index, "size": total, "sha256": digest.hexdigest()}:
                    raise IntegrityError("Encrypted backup is incomplete or its final digest is invalid.")
                final_seen = True
                if reader.read(1):
                    raise IntegrityError("Encrypted backup contains trailing data.")
                break
            else:
                raise IntegrityError("Encrypted backup record type is invalid.")
    if not final_seen:
        destination.unlink(missing_ok=True)
        raise IntegrityError("Encrypted backup is truncated before its final record.")
    return total, digest.hexdigest()
