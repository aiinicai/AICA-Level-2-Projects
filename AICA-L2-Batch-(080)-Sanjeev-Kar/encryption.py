"""
encryption.py
--------------
Streaming, chunked, authenticated file encryption built on AES-256-GCM.

Container format (all integers big-endian / network order)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    MAGIC            8 bytes   b"FLOCKv1\x00"
    file_salt        16 bytes  random, used to derive this file's AES key
    nonce_prefix     4 bytes   random, combined with a chunk counter
    chunk_size       4 bytes   uint32, plaintext bytes per chunk
    original_size    8 bytes   uint64, total plaintext size
    --- repeated chunks until original_size bytes have been produced ---
    chunk_len        4 bytes   uint32, length of this ciphertext chunk
    chunk_ciphertext chunk_len bytes  (AES-GCM ciphertext, tag included)

Per-file key:   HKDF-SHA256(master_key, salt=file_salt, info=b"folderlock-file-v1")
Per-chunk nonce: nonce_prefix (4 bytes) || chunk_index (8 bytes, big-endian)
Per-chunk AAD:   aad_context || b"|" || chunk_index (8 bytes BE) || b"|" || (b"LAST" or b"MORE")

Binding the caller-supplied `aad_context` (the file's relative path within
the protected folder) into every chunk's authentication tag means a chunk
cannot be silently moved to a different file/path, reordered, duplicated,
or truncated without detection: any such change fails AES-GCM tag
verification and raises TamperDetectedError/CorruptedFileError.

Files are streamed in fixed-size chunks so encrypting/decrypting does not
require loading an entire (potentially huge) file into memory.
"""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Callable, Optional

import config
import security
from security import CorruptedFileError, TamperDetectedError

_HEADER_STRUCT = struct.Struct(">8s16s4sIQ")  # magic, salt, nonce_prefix, chunk_size, orig_size
_CHUNK_LEN_STRUCT = struct.Struct(">I")

ProgressCB = Optional[Callable[[int, int], None]]  # (bytes_done, bytes_total)


def _derive_file_key(master_key: bytes, file_salt: bytes) -> bytearray:
    return security.hkdf_derive(master_key, salt=file_salt, info=b"folderlock-file-v1")


def _chunk_nonce(nonce_prefix: bytes, chunk_index: int) -> bytes:
    return nonce_prefix + chunk_index.to_bytes(8, "big")


def _chunk_aad(aad_context: bytes, chunk_index: int, is_last: bool) -> bytes:
    marker = b"LAST" if is_last else b"MORE"
    return aad_context + b"|" + chunk_index.to_bytes(8, "big") + b"|" + marker


def encrypt_file(
    src_path: Path,
    dst_path: Path,
    master_key: bytes,
    aad_context: bytes,
    progress_cb: ProgressCB = None,
) -> None:
    """Encrypt src_path -> dst_path using a fresh random salt/nonce prefix.
    dst_path's parent directory must already exist."""
    settings = config.get_settings()
    chunk_size = int(settings["chunk_size_bytes"])

    file_salt = security.random_bytes(security.SALT_SIZE)
    nonce_prefix = security.random_bytes(4)
    file_key = _derive_file_key(master_key, file_salt)

    original_size = src_path.stat().st_size
    bytes_done = 0

    tmp_dst = dst_path.with_name(dst_path.name + ".part")
    try:
        with open(src_path, "rb") as fin, open(tmp_dst, "wb") as fout:
            fout.write(_HEADER_STRUCT.pack(
                config.MAGIC, file_salt, nonce_prefix, chunk_size, original_size
            ))
            chunk_index = 0
            while True:
                plaintext = fin.read(chunk_size)
                if not plaintext and original_size > 0:
                    break
                is_last = (bytes_done + len(plaintext)) >= original_size
                nonce = _chunk_nonce(nonce_prefix, chunk_index)
                aad = _chunk_aad(aad_context, chunk_index, is_last)
                ciphertext = security.aes_gcm_encrypt(file_key, nonce, plaintext, aad)
                fout.write(_CHUNK_LEN_STRUCT.pack(len(ciphertext)))
                fout.write(ciphertext)

                bytes_done += len(plaintext)
                chunk_index += 1
                if progress_cb:
                    progress_cb(bytes_done, original_size)
                if is_last:
                    break
        tmp_dst.replace(dst_path)
    finally:
        security.best_effort_zero(file_key)
        if tmp_dst.exists():
            try:
                tmp_dst.unlink()
            except OSError:
                pass


def decrypt_file(
    src_path: Path,
    dst_path: Path,
    master_key: bytes,
    aad_context: bytes,
    progress_cb: ProgressCB = None,
) -> None:
    """Decrypt src_path -> dst_path. Raises TamperDetectedError if any
    chunk fails authentication, or CorruptedFileError if the container is
    structurally invalid. dst_path is only ever written to a temporary
    sibling file and atomically renamed on full success, so a failed or
    interrupted decryption never leaves a partial/corrupt plaintext file
    at the final destination."""
    tmp_dst = dst_path.with_name(dst_path.name + ".part")
    try:
        with open(src_path, "rb") as fin:
            header = fin.read(_HEADER_STRUCT.size)
            if len(header) != _HEADER_STRUCT.size:
                raise CorruptedFileError("Encrypted file is truncated (missing header).")
            magic, file_salt, nonce_prefix, chunk_size, original_size = _HEADER_STRUCT.unpack(header)
            if magic != config.MAGIC:
                raise CorruptedFileError("Encrypted file has an unrecognized format.")

            file_key = _derive_file_key(master_key, file_salt)
            try:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tmp_dst, "wb") as fout:
                    bytes_done = 0
                    chunk_index = 0
                    while bytes_done < original_size:
                        len_bytes = fin.read(_CHUNK_LEN_STRUCT.size)
                        if len(len_bytes) != _CHUNK_LEN_STRUCT.size:
                            raise CorruptedFileError("Encrypted file is truncated (missing chunk length).")
                        (chunk_len,) = _CHUNK_LEN_STRUCT.unpack(len_bytes)
                        ciphertext = fin.read(chunk_len)
                        if len(ciphertext) != chunk_len:
                            raise CorruptedFileError("Encrypted file is truncated (missing chunk data).")

                        # AES-GCM appends a fixed 16-byte tag, so the plaintext
                        # length of this chunk is known before decrypting,
                        # which lets us compute `is_last` exactly (no guessing).
                        if chunk_len < 16:
                            raise CorruptedFileError("Encrypted file has an invalid chunk length.")
                        plaintext_len = chunk_len - 16
                        is_last = (bytes_done + plaintext_len) >= original_size
                        nonce = _chunk_nonce(nonce_prefix, chunk_index)
                        aad = _chunk_aad(aad_context, chunk_index, is_last)
                        plaintext = security.aes_gcm_decrypt(file_key, nonce, ciphertext, aad)

                        fout.write(plaintext)
                        bytes_done += len(plaintext)
                        chunk_index += 1
                        if progress_cb:
                            progress_cb(bytes_done, original_size)

                    if original_size == 0:
                        len_bytes = fin.read(_CHUNK_LEN_STRUCT.size)
                        if len(len_bytes) == _CHUNK_LEN_STRUCT.size:
                            (chunk_len,) = _CHUNK_LEN_STRUCT.unpack(len_bytes)
                            ciphertext = fin.read(chunk_len)
                            aad = _chunk_aad(aad_context, 0, True)
                            security.aes_gcm_decrypt(file_key, nonce_prefix + (0).to_bytes(8, "big"), ciphertext, aad)

                    trailing = fin.read(1)
                    if trailing:
                        raise CorruptedFileError("Encrypted file has unexpected trailing data.")

                    if bytes_done != original_size:
                        raise CorruptedFileError("Decrypted size does not match the recorded original size.")
            finally:
                security.best_effort_zero(file_key)
        tmp_dst.replace(dst_path)
    except (TamperDetectedError, CorruptedFileError):
        if tmp_dst.exists():
            try:
                tmp_dst.unlink()
            except OSError:
                pass
        raise
    finally:
        if tmp_dst.exists():
            try:
                tmp_dst.unlink()
            except OSError:
                pass


def sha256_of_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()
