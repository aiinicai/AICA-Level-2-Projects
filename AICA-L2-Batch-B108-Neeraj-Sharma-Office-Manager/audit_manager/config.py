"""Where the app keeps its data, and the few settings read before the database exists."""
import json
import os
import secrets
from pathlib import Path

APP_NAME = "AuditManager"
DEFAULT_PORT = 8765


def base_dir() -> Path:
    """The fixed starting folder. It holds the data unless the firm has moved the data to another drive."""
    override = os.environ.get("AUDIT_MANAGER_DATA")
    if override:
        path = Path(override)
    elif os.name == "nt":
        path = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
    else:
        path = Path.home() / ".audit_manager"
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    """Folder holding the database, uploads and keys. Never inside the install folder. Can be moved (Settings > Data folder)."""
    base = base_dir()
    pointer = base / "location.txt"
    if pointer.exists():
        try:
            target = Path(pointer.read_text(encoding="utf-8").strip())
            if target.is_dir():
                return target
        except OSError:
            pass
    return base


def request_move(target: str) -> None:
    (base_dir() / "move_pending.txt").write_text(target, encoding="utf-8")


def pending_move() -> str | None:
    p = base_dir() / "move_pending.txt"
    return p.read_text(encoding="utf-8").strip() if p.exists() else None


def cancel_move() -> None:
    (base_dir() / "move_pending.txt").unlink(missing_ok=True)


def apply_pending_move() -> str | None:
    """At start-up, before anything is opened: copy the data to the new folder and switch to it. The old copy is left untouched."""
    import shutil

    base = base_dir()
    marker = base / "move_pending.txt"
    if not marker.exists():
        return None
    try:
        target = Path(marker.read_text(encoding="utf-8").strip())
        source = data_dir()
        target.mkdir(parents=True, exist_ok=True)
        if target.resolve() != source.resolve():
            for item in source.iterdir():
                if item.name in ("location.txt", "move_pending.txt") or item.name.endswith((".db-wal", ".db-shm")):
                    continue
                if item.is_dir():
                    shutil.copytree(item, target / item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target / item.name)
            if target.resolve() == base.resolve():
                (base / "location.txt").unlink(missing_ok=True)
            else:
                (base / "location.txt").write_text(str(target), encoding="utf-8")
        return str(target)
    except OSError:
        return None
    finally:
        marker.unlink(missing_ok=True)


def read_secret(name: str, nbytes: int = 32) -> str:
    """A random secret created once and kept in the data folder (session key, encryption key)."""
    path = data_dir() / name
    if path.exists():
        return path.read_text().strip()
    value = secrets.token_urlsafe(nbytes)
    path.write_text(value)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return value


def network_settings() -> dict:
    """Host/port for the built-in server. 0.0.0.0 lets other PCs on the office network connect."""
    defaults = {"host": "0.0.0.0", "port": DEFAULT_PORT}
    path = data_dir() / "config.json"
    if path.exists():
        try:
            defaults.update(json.loads(path.read_text()))
        except (OSError, ValueError):
            pass
    else:
        path.write_text(json.dumps(defaults, indent=2))
    return defaults
