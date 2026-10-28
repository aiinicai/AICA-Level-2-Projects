"""Per-company storage: profile.json + vendor_master.csv under data/companies/<slug>/."""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pandas as pd

import datetime as _dt

import engine as E
from engine import SCHEMAS

ROOT = Path(os.environ.get("MSME_DATA_DIR", Path(__file__).parent / "data")) / "companies"
MASTER_COLS = [c.name for c in SCHEMAS["vendor_master"]]
PROFILE_FIELDS = ("name", "pan", "gstin", "notes")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "company"


def _dir(slug: str) -> Path:
    return ROOT / slug


def list_companies() -> list[dict]:
    if not ROOT.exists():
        return []
    out = []
    for p in sorted(ROOT.iterdir()):
        f = p / "profile.json"
        if f.exists():
            out.append({"slug": p.name, **json.loads(f.read_text())})
    return sorted(out, key=lambda c: c["name"].casefold())


def create_company(name: str, pan: str = "", gstin: str = "", notes: str = "") -> str:
    name = name.strip()
    if not name:
        raise ValueError("Company name is required.")
    slug = slugify(name)
    if _dir(slug).exists():
        raise ValueError(f"A company named '{name}' already exists.")
    _dir(slug).mkdir(parents=True)
    (_dir(slug) / "profile.json").write_text(json.dumps({"name": name, "pan": pan.strip(), "gstin": gstin.strip(), "notes": notes.strip()}, indent=2))
    save_master(slug, pd.DataFrame(columns=MASTER_COLS + ["vkey"]))
    return slug


def get_profile(slug: str) -> dict:
    return json.loads((_dir(slug) / "profile.json").read_text())


def update_profile(slug: str, **fields) -> None:
    p = get_profile(slug)
    p.update({k: v for k, v in fields.items() if k in PROFILE_FIELDS})
    (_dir(slug) / "profile.json").write_text(json.dumps(p, indent=2))


def delete_company(slug: str) -> None:
    d = _dir(slug)
    if d.exists() and d.parent == ROOT:
        shutil.rmtree(d)


def load_master(slug: str) -> pd.DataFrame:
    f = _dir(slug) / "vendor_master.csv"
    if not f.exists():
        return pd.DataFrame(columns=MASTER_COLS + ["vkey"])
    df = pd.read_csv(f, dtype=object)
    for c in ("Udyam Registration Date",):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["Agreed Credit Days"] = pd.to_numeric(df["Agreed Credit Days"], errors="coerce")
    for c in df.columns:
        if c not in ("Udyam Registration Date", "Agreed Credit Days"):
            df[c] = df[c].astype(object).where(df[c].notna(), None)
    return df


def save_master(slug: str, df: pd.DataFrame) -> None:
    out = df.copy()
    for c in MASTER_COLS + ["vkey"]:
        if c not in out.columns:
            out[c] = None
    out = out[MASTER_COLS + ["vkey"]]
    out["Udyam Registration Date"] = pd.to_datetime(out["Udyam Registration Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out.to_csv(_dir(slug) / "vendor_master.csv", index=False)


def merge_master(existing: pd.DataFrame, incoming: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Upsert incoming vendors into existing by vendor key. Blank incoming fields do not erase stored values."""
    base = existing.set_index("vkey") if len(existing) else pd.DataFrame(columns=existing.columns).set_index("vkey")
    added = updated = 0
    for _, r in incoming.iterrows():
        k = r["vkey"]
        if k in base.index:
            for c in MASTER_COLS:
                v = r[c]
                if v is not None and not (isinstance(v, float) and pd.isna(v)) and not (v is pd.NaT):
                    base.at[k, c] = v
            updated += 1
        else:
            base.loc[k, MASTER_COLS] = [r[c] for c in MASTER_COLS]
            added += 1
    merged = base.reset_index()
    return merged, added, updated


# ---- RBI bank-rate table (shared by all companies) ----
def _rates_file() -> Path:
    return ROOT.parent / "bank_rates.csv"


def load_bank_rates() -> pd.DataFrame:
    import interest
    f = _rates_file()
    if f.exists():
        try:
            return interest.clean_rates(pd.read_csv(f))
        except Exception:  # noqa: BLE001
            pass
    return interest.DEFAULT_BANK_RATES.copy()


def save_bank_rates(df: pd.DataFrame) -> None:
    import interest
    ROOT.parent.mkdir(parents=True, exist_ok=True)
    out = interest.clean_rates(df)
    out["Effective From"] = out["Effective From"].dt.strftime("%Y-%m-%d")
    out.to_csv(_rates_file(), index=False)


# ---- Saved runs (inputs + vendor-master snapshot + Form 1 reasons), per company ----
def _runs(slug: str) -> Path:
    return _dir(slug) / "runs"


def _write_csv(df: pd.DataFrame, path: Path, cols: list[str], date_cols: list[str]) -> None:
    out = df.reindex(columns=cols).copy()
    for c in date_cols:
        out[c] = pd.to_datetime(out[c], errors="coerce").dt.strftime("%d-%m-%Y")
    out.to_csv(path, index=False)


def save_run(slug: str, name: str, bills: pd.DataFrame, pays: pd.DataFrame, master: pd.DataFrame,
             as_of, fy: int, warnings: list[str]) -> str:
    """Persist a run. Dates are written dd-mm-yyyy so reloading goes through the normal standardise() path."""
    rid = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    d = _runs(slug) / rid
    n = 1
    while d.exists():
        n += 1
        d = _runs(slug) / f"{rid}-{n}"
    d.mkdir(parents=True)
    _write_csv(bills, d / "bills.csv", [c.name for c in SCHEMAS["bills"]], ["Bill Date", "Acceptance Date"])
    _write_csv(pays, d / "payments.csv", [c.name for c in SCHEMAS["payments"]], ["Payment Date"])
    _write_csv(master, d / "vendor_master.csv", MASTER_COLS, ["Udyam Registration Date"])
    meta = {"name": name.strip() or d.name, "created": _dt.datetime.now().isoformat(timespec="seconds"),
            "as_of": pd.Timestamp(as_of).strftime("%Y-%m-%d"), "fy": int(fy),
            "bills": int(len(bills)), "payments": int(len(pays)), "warnings": list(warnings)}
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    return d.name


def list_runs(slug: str) -> list[dict]:
    root = _runs(slug)
    if not root.exists():
        return []
    out = []
    for p in root.iterdir():
        f = p / "meta.json"
        if f.exists():
            out.append({"id": p.name, **json.loads(f.read_text())})
    return sorted(out, key=lambda m: m["created"], reverse=True)


def _read_std(path: Path, kind: str) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype=object)
    if raw.dropna(how="all").empty:
        cols = [c.name for c in SCHEMAS[kind]]
        empty = pd.DataFrame(columns=cols + (["vkey"] + (["bkey"] if kind != "vendor_master" else [])))
        for c in SCHEMAS[kind]:
            if c.kind == "date":
                empty[c.name] = pd.to_datetime(empty[c.name])
            elif c.kind == "number":
                empty[c.name] = pd.to_numeric(empty[c.name])
        return empty
    return E.standardise(raw, kind)[0]


def load_run(slug: str, rid: str) -> dict:
    d = _runs(slug) / rid
    meta = json.loads((d / "meta.json").read_text())
    reasons_f = d / "reasons.json"
    return {"meta": meta, "bills": _read_std(d / "bills.csv", "bills"), "pays": _read_std(d / "payments.csv", "payments"),
            "master": _read_std(d / "vendor_master.csv", "vendor_master"),
            "as_of": pd.Timestamp(meta["as_of"]), "fy": int(meta["fy"]),
            "reasons": json.loads(reasons_f.read_text()) if reasons_f.exists() else {}}


def save_reasons(slug: str, rid: str, reasons: dict[str, str]) -> None:
    clean = {k: v for k, v in reasons.items() if isinstance(v, str) and v.strip()}
    (_runs(slug) / rid / "reasons.json").write_text(json.dumps(clean, indent=2, ensure_ascii=False))


def delete_run(slug: str, rid: str) -> None:
    d = _runs(slug) / rid
    if d.exists() and d.parent == _runs(slug):
        shutil.rmtree(d)
