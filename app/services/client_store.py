import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import BASE_DIR

REGISTRY_NAME = "clients.json"
COOKIE_NAME = "restroreco_client"
CLIENT_FORMAT = "hsa-restroreco-client-v1"
APP_FOLDER_NAME = "HARSH'S RESTRORECO"
DATA_FOLDER_NAME = "DATA"
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def is_testing() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or os.environ.get("RESTRORECO_TESTING") == "1"


def system_app_root() -> Path:
    if os.name == "nt":
        return Path("C:/") / APP_FOLDER_NAME
    return Path.home() / APP_FOLDER_NAME


def data_root() -> Path:
    override = os.environ.get("RESTRORECO_DATA_DIR")
    if override:
        path = Path(override)
    elif is_testing():
        path = BASE_DIR / "data"
    else:
        path = system_app_root() / DATA_FOLDER_NAME
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"Could not create the data folder at {path}. "
            f"Allow this program to write to {system_app_root() / DATA_FOLDER_NAME}."
        ) from exc
    return path


def registry_path() -> Path:
    return data_root() / REGISTRY_NAME


def clients_root() -> Path:
    """Client books sit directly under DATA, named after the client."""
    return data_root()


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return (slug or "client")[:48]


def sanitize_folder_name(name: str) -> str:
    text = re.sub(r'[<>:"/\\|?*]', " ", name or "")
    text = re.sub(r"\s+", " ", text).strip(" .")
    if not text:
        text = "Client"
    stem = text.split(".")[0].upper()
    if stem in _WINDOWS_RESERVED:
        text = f"{text} Client"
    return text[:80]


def _empty_registry() -> Dict[str, Any]:
    return {"active_id": "", "clients": []}


def load_registry() -> Dict[str, Any]:
    path = registry_path()
    if not path.exists():
        return _empty_registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_registry()
    data.setdefault("active_id", "")
    data.setdefault("clients", [])
    return data


def save_registry(data: Dict[str, Any]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_clients() -> List[Dict[str, Any]]:
    return list(load_registry().get("clients") or [])


def get_client(client_id: str) -> Optional[Dict[str, Any]]:
    wanted = (client_id or "").strip()
    if not wanted:
        return None
    for item in list_clients():
        if item.get("id") == wanted or item.get("slug") == wanted:
            return item
    return None


def unique_folder_name(
    name: str,
    exclude_id: str = "",
    clients: Optional[List[Dict[str, Any]]] = None,
) -> str:
    base = sanitize_folder_name(name)
    items = clients if clients is not None else list_clients()
    taken = {
        str(item.get("folder") or "").strip().lower()
        for item in items
        if item.get("id") != exclude_id and str(item.get("folder") or "").strip()
    }
    folder = base
    index = 2
    root = data_root()
    while True:
        path = root / folder
        name_taken = folder.lower() in taken
        own = False
        if exclude_id:
            for item in items:
                if item.get("id") == exclude_id and str(item.get("folder") or "") == folder:
                    own = True
                    break
        disk_taken = path.exists() and not own
        if not name_taken and not disk_taken:
            return folder
        folder = f"{base} ({index})"
        index += 1


def client_dir(client: Dict[str, Any], create: bool = True) -> Path:
    folder = str(client.get("folder") or "").strip()
    if not folder:
        folder = sanitize_folder_name(str(client.get("name") or client.get("slug") or client.get("id") or "Client"))
    path = data_root() / folder
    if create:
        path.mkdir(parents=True, exist_ok=True)
        (path / "uploads").mkdir(parents=True, exist_ok=True)
    return path


def client_db_path(client: Dict[str, Any]) -> Path:
    return client_dir(client) / "restaurant_reconcile.db"


def client_uploads_path(client: Dict[str, Any]) -> Path:
    return client_dir(client) / "uploads"


def unique_slug(name: str) -> str:
    base = slugify(name)
    existing = {item.get("slug") for item in list_clients()}
    slug = base
    index = 2
    while slug in existing:
        slug = f"{base}-{index}"
        index += 1
    return slug


GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", re.I)


def normalize_gstin(value: str) -> str:
    text = re.sub(r"\s+", "", value or "").upper()
    if not text:
        return ""
    if not GSTIN_RE.match(text):
        raise ValueError("Enter a valid 15-character GSTIN")
    return text


def _merge_move_dir(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            _merge_move_dir(item, target)
        elif not target.exists():
            shutil.move(str(item), str(target))
        else:
            try:
                if item.stat().st_size > target.stat().st_size:
                    target.unlink()
                    shutil.move(str(item), str(target))
                else:
                    item.unlink()
            except OSError:
                pass
    try:
        src.rmdir()
    except OSError:
        pass


def migrate_legacy_client_storage() -> None:
    """Move books from the old project data/clients/<slug> folders to C:\\HARSH'S RESTRORECO\\DATA\\<name>."""
    if is_testing() or os.environ.get("RESTRORECO_DATA_DIR"):
        return
    new_root = data_root()
    old_root = BASE_DIR / "data"
    old_registry = old_root / REGISTRY_NAME
    new_registry = new_root / REGISTRY_NAME
    if not new_registry.exists() and old_registry.exists():
        try:
            if old_registry.resolve() != new_registry.resolve():
                shutil.copy2(old_registry, new_registry)
        except OSError:
            return

    registry = load_registry()
    clients = list(registry.get("clients") or [])
    if not clients:
        return

    from app.core.database import dispose_all_sqlite_engines

    dispose_all_sqlite_engines()
    changed = False
    for item in clients:
        folder_name = unique_folder_name(
            str(item.get("name") or item.get("slug") or "Client"),
            exclude_id=str(item.get("id") or ""),
            clients=clients,
        )
        dest = new_root / folder_name
        slug = str(item.get("slug") or item.get("id") or "")
        candidates = []
        if slug:
            candidates.extend(
                [
                    old_root / "clients" / slug,
                    new_root / "clients" / slug,
                    old_root / slug,
                ]
            )
        old_folder = str(item.get("folder") or "").strip()
        if old_folder:
            candidates.extend(
                [
                    old_root / "clients" / old_folder,
                    new_root / "clients" / old_folder,
                    old_root / old_folder,
                ]
            )
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "uploads").mkdir(parents=True, exist_ok=True)
        seen = set()
        for src in candidates:
            try:
                key = str(src.resolve())
            except OSError:
                key = str(src)
            if key in seen:
                continue
            seen.add(key)
            if not src.exists() or not src.is_dir():
                continue
            try:
                if src.resolve() == dest.resolve():
                    continue
            except OSError:
                continue
            _merge_move_dir(src, dest)
        if item.get("folder") != folder_name:
            item["folder"] = folder_name
            changed = True

    if changed:
        registry["clients"] = clients
        save_registry(registry)

    leftover = new_root / "clients"
    try:
        if leftover.is_dir() and not any(leftover.iterdir()):
            leftover.rmdir()
    except OSError:
        pass

    # Older installs kept one shared SQLite file under the project data folder.
    legacy_db = old_root / "restaurant_reconcile.db"
    if legacy_db.exists() and clients:
        first = clients[0]
        dest_db = new_root / str(first.get("folder") or sanitize_folder_name(str(first.get("name") or "Client"))) / "restaurant_reconcile.db"
        try:
            dest_db.parent.mkdir(parents=True, exist_ok=True)
            if not dest_db.exists() or dest_db.stat().st_size < legacy_db.stat().st_size:
                shutil.copy2(legacy_db, dest_db)
        except OSError:
            pass


def add_client(
    name: str,
    slug: Optional[str] = None,
    address: str = "",
    gstin: str = "",
) -> Dict[str, Any]:
    clean_name = (name or "").strip() or "New Client"
    registry = load_registry()
    final_slug = slugify(slug) if slug else unique_slug(clean_name)
    if get_client(final_slug):
        final_slug = unique_slug(clean_name)
    folder = unique_folder_name(clean_name, clients=registry.get("clients") or [])
    item = {
        "id": final_slug,
        "name": clean_name,
        "slug": final_slug,
        "folder": folder,
        "address": (address or "").strip(),
        "gstin": normalize_gstin(gstin),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    registry["clients"].append(item)
    if not registry.get("active_id"):
        registry["active_id"] = item["id"]
    save_registry(registry)
    client_dir(item)
    return item


def _rename_client_folder(client: Dict[str, Any], new_folder: str) -> None:
    old_path = client_dir(client, create=False)
    new_path = data_root() / new_folder
    try:
        if old_path.exists() and old_path.resolve() == new_path.resolve():
            return
    except OSError:
        pass
    from app.core.database import dispose_all_sqlite_engines

    dispose_all_sqlite_engines()
    if not old_path.exists():
        new_path.mkdir(parents=True, exist_ok=True)
        (new_path / "uploads").mkdir(parents=True, exist_ok=True)
        return
    try:
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))
    except OSError as exc:
        raise ValueError(
            "Could not rename this client's folder because Windows still has files open. "
            "Wait a moment and try again."
        ) from exc


def update_client(client_id: str, name: str = "", address: Optional[str] = None, gstin: Optional[str] = None) -> Dict[str, Any]:
    client = get_client(client_id)
    if not client:
        raise ValueError("Client not found")
    registry = load_registry()
    for item in registry["clients"]:
        if item.get("id") == client["id"]:
            if name and name.strip():
                new_name = name.strip()
                item["name"] = new_name
                new_folder = unique_folder_name(new_name, exclude_id=item["id"], clients=registry["clients"])
                if new_folder != str(item.get("folder") or ""):
                    _rename_client_folder(item, new_folder)
                    item["folder"] = new_folder
            if address is not None:
                item["address"] = address.strip()
            if gstin is not None:
                item["gstin"] = normalize_gstin(gstin)
            if not item.get("folder"):
                item["folder"] = unique_folder_name(item.get("name") or "Client", exclude_id=item["id"], clients=registry["clients"])
            save_registry(registry)
            return item
    raise ValueError("Client not found")


def _rmtree_with_retry(folder: Path, attempts: int = 10) -> None:
    import gc
    import time

    last_error: Optional[Exception] = None
    for index in range(attempts):
        gc.collect()
        try:
            shutil.rmtree(folder)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.08 * (index + 1))
    raise ValueError(
        "Could not delete this client's files because Windows still has them open. "
        "Wait a moment and try Delete again."
    ) from last_error


def delete_client(client_id: str) -> Dict[str, Any]:
    clients = list_clients()
    if len(clients) <= 1:
        raise ValueError("At least one client must remain")
    client = get_client(client_id)
    if not client:
        raise ValueError("Client not found")
    from app.core.database import dispose_all_sqlite_engines

    folder = client_dir(client, create=False)
    legacy = data_root() / "clients" / str(client.get("slug") or client.get("id"))
    dispose_all_sqlite_engines()
    for path in (folder, legacy):
        if path.exists() and path.is_dir():
            _rmtree_with_retry(path)
    registry = load_registry()
    registry["clients"] = [item for item in registry["clients"] if item.get("id") != client["id"]]
    remaining = registry["clients"]
    if registry.get("active_id") == client["id"] and remaining:
        registry["active_id"] = remaining[0]["id"]
    save_registry(registry)
    return {"deleted_id": client["id"], "active_id": registry.get("active_id") or ""}


def set_active_id(client_id: str) -> Dict[str, Any]:
    client = get_client(client_id)
    if not client:
        raise ValueError("Client not found")
    registry = load_registry()
    registry["active_id"] = client["id"]
    save_registry(registry)
    return client


def resolve_active_slug(preferred: str = "") -> str:
    clients = list_clients()
    if not clients:
        return ""
    if preferred and get_client(preferred):
        return get_client(preferred)["slug"]
    registry = load_registry()
    active = get_client(registry.get("active_id") or "")
    if active:
        return active["slug"]
    return clients[0]["slug"]


def get_active_client(preferred: str = "") -> Optional[Dict[str, Any]]:
    slug = resolve_active_slug(preferred)
    return get_client(slug) if slug else None


def public_client(client: Dict[str, Any], active_id: str = "") -> Dict[str, Any]:
    return {
        "id": client.get("id"),
        "name": client.get("name"),
        "slug": client.get("slug"),
        "folder": client.get("folder") or "",
        "data_path": str(client_dir(client, create=False)),
        "address": client.get("address") or "",
        "gstin": client.get("gstin") or "",
        "is_active": client.get("id") == active_id or client.get("slug") == active_id,
    }
