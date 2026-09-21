"""Local JSON persistence: supplier master, app settings, mapping profiles."""
from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path

from .logsetup import get_logger
from .models import Supplier
from .paths import profiles_dir, settings_dir
from .profile_default import DEFAULT_PROFILE
from .util import safe_filename

log = get_logger()


def _read(p: Path, default):
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:                     # corrupted file must not crash the app
        log.warning("Could not read %s: %s", p.name, e)
    return default


def _write(p: Path, data) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def load_supplier() -> Supplier:
    d = _read(settings_dir() / "supplier.json", {})
    s = Supplier()
    for k, v in d.items():
        if hasattr(s, k):
            setattr(s, k, str(v or ""))
    return s


def save_supplier(s: Supplier) -> None:
    _write(settings_dir() / "supplier.json", asdict(s))


def load_app_settings() -> dict:
    return _read(settings_dir() / "app_settings.json",
                 {"template_path": "", "output_dir": "", "hsn_rates": {}, "last_profile": ""})


def save_app_settings(d: dict) -> None:
    _write(settings_dir() / "app_settings.json", d)


def list_profiles() -> list[str]:
    names = [DEFAULT_PROFILE["profile_name"]]
    for p in sorted(profiles_dir().glob("*.json")):
        d = _read(p, None)
        if d and d.get("profile_name") and d["profile_name"] not in names:
            names.append(d["profile_name"])
    return names


def load_profile(name: str | None) -> dict:
    base = copy.deepcopy(DEFAULT_PROFILE)
    if not name or name == DEFAULT_PROFILE["profile_name"]:
        return base
    for p in profiles_dir().glob("*.json"):
        d = _read(p, None)
        if d and d.get("profile_name") == name:
            for k in ("fields", "items", "conversion"):          # fill keys added in later versions
                merged = copy.deepcopy(base[k]); merged.update(d.get(k, {})); d[k] = merged
            return d
    return base


def save_profile(profile: dict) -> Path:
    p = profiles_dir() / (safe_filename(profile["profile_name"]) + ".json")
    _write(p, profile)
    return p


def delete_profile(name: str) -> bool:
    for p in profiles_dir().glob("*.json"):
        d = _read(p, None)
        if d and d.get("profile_name") == name:
            p.unlink(); return True
    return False
