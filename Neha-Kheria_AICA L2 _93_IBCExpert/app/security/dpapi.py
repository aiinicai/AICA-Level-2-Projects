"""Windows DPAPI wrapper with an explicit non-Windows protected-file mode.

There is no silent plaintext fallback. On Windows, CryptProtectData is mandatory.
On non-Windows development/test systems callers must protect filesystem access and
receive the tagged `POSIX1` envelope so a Windows package can reject it.
"""
from __future__ import annotations

import ctypes
import os
import platform
from ctypes import wintypes

from app.core.errors import ConfigurationError, IntegrityError

WIN_MAGIC = b"DPAPI1"
POSIX_MAGIC = b"POSIX1"


if platform.system() == "Windows":
    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    def _blob(data: bytes):
        buffer = ctypes.create_string_buffer(data)
        return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer

    def protect(data: bytes, entropy: bytes = b"IBC-EXPERT/v1") -> bytes:
        source, source_buffer = _blob(data)
        extra, extra_buffer = _blob(entropy)
        result = DATA_BLOB()
        flags = 0x01  # CRYPTPROTECT_UI_FORBIDDEN
        if not crypt32.CryptProtectData(
            ctypes.byref(source), "IBC Expert protected state", ctypes.byref(extra),
            None, None, flags, ctypes.byref(result)
        ):
            raise ConfigurationError("Windows could not protect IBC Expert secure state.")
        try:
            protected = ctypes.string_at(result.pbData, result.cbData)
            return WIN_MAGIC + protected
        finally:
            kernel32.LocalFree(result.pbData)

    def unprotect(payload: bytes, entropy: bytes = b"IBC-EXPERT/v1") -> bytes:
        if not payload.startswith(WIN_MAGIC):
            raise IntegrityError("Secure state is not protected for this Windows profile.")
        source, source_buffer = _blob(payload[len(WIN_MAGIC):])
        extra, extra_buffer = _blob(entropy)
        result = DATA_BLOB()
        flags = 0x01
        if not crypt32.CryptUnprotectData(
            ctypes.byref(source), None, ctypes.byref(extra), None, None, flags, ctypes.byref(result)
        ):
            raise IntegrityError("Secure state cannot be opened by this Windows user or was altered.")
        try:
            return ctypes.string_at(result.pbData, result.cbData)
        finally:
            kernel32.LocalFree(result.pbData)
else:
    def protect(data: bytes, entropy: bytes = b"IBC-EXPERT/v1") -> bytes:
        # Development/test portability marker. Confidential application payloads
        # are still independently AEAD-encrypted; this function only wraps the
        # random local integrity key on platforms without DPAPI.
        return POSIX_MAGIC + data

    def unprotect(payload: bytes, entropy: bytes = b"IBC-EXPERT/v1") -> bytes:
        if not payload.startswith(POSIX_MAGIC):
            raise IntegrityError("Secure state belongs to another operating-system protection mode.")
        return payload[len(POSIX_MAGIC):]
