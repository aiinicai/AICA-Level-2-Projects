"""App settings: stored as JSON in %APPDATA%, secrets via Windows DPAPI (keyring)."""
from __future__ import annotations

import json
import os
import socket
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

APP_NAME = "AccountingAssistant"


def app_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class Settings:
    machine_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    user_name: str = field(default_factory=lambda: os.environ.get("USERNAME") or os.environ.get("USER") or "user")
    host_name: str = field(default_factory=socket.gethostname)
    local_db_path: str = ""          # blank -> app_dir()/local.db
    remote_db_url: str = ""          # e.g. postgresql+pg8000://acct@192.168.1.10/acct  (password in keyring)
    default_tally_host: str = "localhost"
    default_tally_port: int = 9000
    tally_timeout_s: int = 60
    lock_stale_seconds: int = 300
    voucher_history_months: int = 12
    theme: str = "midnight"
    default_voucher_style: str = "journal"     # purchase_accounting | purchase_item | journal (new companies)
    use_gemini: bool = True
    gemini_model: str = "gemini-3.5-flash-lite"   # cheapest; "auto-lite" = newest Flash-Lite, "auto" = newest Flash
    gemini_threshold: float = 0.8     # kept for compatibility (Gemini-first now)
    gemini_parallel: int = 4
    allow_unredacted_image: bool = False

    @property
    def local_db_url(self) -> str:
        path = self.local_db_path or str(app_dir() / "local.db")
        return f"sqlite:///{path}"

    # ---- persistence -------------------------------------------------
    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or app_dir() / "settings.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            s = cls(**known)
            if str(s.gemini_model).startswith(("gemini-1.", "gemini-2.")) or s.gemini_model == "auto":
                s.gemini_model = "gemini-3.5-flash-lite"   # retired models -> cheapest current model
                s.save(path)
        else:
            s = cls()
            s.save(path)
        return s

    def save(self, path: Path | None = None) -> None:
        path = path or app_dir() / "settings.json"
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def desktop_dir() -> Path:
    """Real Desktop folder (OneDrive often redirects it away from %USERPROFILE%\\Desktop)."""
    if os.name == "nt":
        try:
            import subprocess
            out = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                  "[Environment]::GetFolderPath('Desktop')"], capture_output=True, text=True,
                                 timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
            if out and Path(out).is_dir():
                return Path(out)
        except Exception:
            pass
        for base in (os.environ.get("OneDrive"), os.environ.get("USERPROFILE")):
            if base and (Path(base) / "Desktop").is_dir():
                return Path(base) / "Desktop"
    return Path.home() / "Desktop"


# ---- secrets (DPAPI-backed Windows Credential Manager via keyring) ------
def set_secret(name: str, value: str) -> None:
    import keyring
    keyring.set_password(APP_NAME, name, value)


def delete_secret(name: str) -> None:
    """Remove a saved secret from Windows Credential Manager (no error if none was saved)."""
    try:
        import keyring
        keyring.delete_password(APP_NAME, name)
    except Exception:
        pass


def get_secret(name: str) -> str | None:
    try:
        import keyring
        return keyring.get_password(APP_NAME, name)
    except Exception:
        return None
