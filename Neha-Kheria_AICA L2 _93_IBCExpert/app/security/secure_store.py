"""Atomic redundant secure-state storage with Windows registry mirroring."""
from __future__ import annotations

import contextlib
import os
import platform
import secrets
from pathlib import Path

from app.core.errors import IntegrityError
from app.security import dpapi

REGISTRY_PATH = r"Software\IBC Expert\SecureState"


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + secrets.token_hex(4))
    try:
        with open(temp, "xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temp.chmod(mode)
        except OSError:
            if os.name != "nt":
                raise
            # Windows profile ACLs and DPAPI provide the protection boundary;
            # POSIX mode bits are not authoritative there.
        os.replace(temp, path)
    finally:
        with contextlib.suppress(OSError):
            temp.unlink(missing_ok=True)


class RedundantSecureStore:
    def __init__(self, primary: Path, secondary: Path, registry_value: str):
        self.primary = primary
        self.secondary = secondary
        self.registry_value = registry_value

    def _registry_read(self) -> bytes | None:
        if platform.system() != "Windows":
            return None
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
                value, value_type = winreg.QueryValueEx(key, self.registry_value)
                if value_type != winreg.REG_BINARY:
                    raise IntegrityError("Windows secure-state registry value has an invalid type.")
                return bytes(value)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise IntegrityError("Windows secure-state registry could not be read.") from exc

    def _registry_write(self, data: bytes) -> None:
        if platform.system() != "Windows":
            return
        import winreg
        try:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.SetValueEx(key, self.registry_value, 0, winreg.REG_BINARY, data)
        except OSError as exc:
            raise IntegrityError("Windows secure-state registry could not be updated.") from exc

    def raw_copies(self) -> list[bytes]:
        copies: list[bytes] = []
        for path in (self.primary, self.secondary):
            if path.exists():
                try:
                    copies.append(path.read_bytes())
                except OSError as exc:
                    raise IntegrityError("Protected local state could not be read.") from exc
        registry = self._registry_read()
        if registry is not None:
            copies.append(registry)
        return copies

    def write_all(self, data: bytes) -> None:
        protected = dpapi.protect(data)
        atomic_write(self.primary, protected)
        atomic_write(self.secondary, protected)
        self._registry_write(protected)

    def read_candidates(self) -> list[bytes]:
        result: list[bytes] = []
        for copy in self.raw_copies():
            try:
                result.append(dpapi.unprotect(copy))
            except IntegrityError:
                # Presence of any corrupt protected copy is treated as tampering;
                # silently ignoring it could turn deletion/modification into a reset.
                raise
        return result

    def heal(self, canonical: bytes) -> None:
        self.write_all(canonical)
