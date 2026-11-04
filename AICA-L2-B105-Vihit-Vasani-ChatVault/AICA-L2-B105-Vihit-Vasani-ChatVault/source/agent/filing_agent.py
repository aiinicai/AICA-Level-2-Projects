#!/usr/bin/env python3
"""
ChatVault filing agent.

Watches a folder (usually Downloads) for archives exported from ChatVault, checks every
SHA-256 value inside them, and files each verified archive into a folder tree by client:

    <Archive root>/<client, else first tag, else "Untagged">/<chat name>/<date>_<chat>_archive.zip
                                                       /<date>_<chat>_archive/   (extracted copy)
    <Archive root>/Backups/ChatVault_backup_<date>.json
    <Archive root>/register.csv                        (one row per filed archive)

An archive that fails verification is moved to <Archive root>/_Quarantine and is not filed.
Optionally mirrors everything into a cloud-synced folder (Google Drive, OneDrive, Dropbox).

Usage:
    python filing_agent.py                                   # watch ~/Downloads, file into ~/ChatVault Archive
    python filing_agent.py --watch D:/Downloads --archive "E:/Client Records/WhatsApp" --sync "G:/My Drive/ChatVault"
    python filing_agent.py --once                            # process what is there now, then exit

Standard library only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

ARCHIVE_RE = re.compile(r"_(\d{4}-\d{2}-\d{2})_archive\.zip$", re.I)
BACKUP_RE = re.compile(r"^ChatVault_backup_.*\.json$", re.I)
HASH_LINE = re.compile(r"^([0-9a-f]{64})\s{2}(.+)$")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", name).strip(" .")[:80] or "Untitled"


def stable(p: Path, wait: float = 1.5) -> bool:
    """True when the file has stopped growing (download finished)."""
    try:
        a = p.stat().st_size
        time.sleep(wait)
        return a == p.stat().st_size and a > 0
    except FileNotFoundError:
        return False


def verify_archive(zpath: Path) -> tuple[bool, dict, list[str]]:
    """Check SHA256SUMS.txt and OUTPUT HASHES.txt against the files inside the ZIP."""
    info, problems, checked = {}, [], 0
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        root = names[0].split("/")[0] + "/" if names and "/" in names[0] else ""
        def read(n):
            return z.read(root + n) if root + n in names else None
        stmt = read("INTEGRITY STATEMENT.txt")
        if stmt is None:
            return False, info, ["INTEGRITY STATEMENT.txt not found: not a ChatVault archive"]
        for line in stmt.decode("utf-8", "replace").splitlines():
            if line.startswith("Chat: "): info["chat"] = line[6:].strip()
            elif line.startswith("Client: "): info["client"] = line[8:].strip()
            elif line.startswith("Tags: "): info["tags"] = [t.strip() for t in line[6:].split(",") if t.strip() and t.strip() != "none"]
            elif line.startswith("Messages: "): info["messages"] = line.split()[1]
        for listing in ("SHA256SUMS.txt", "OUTPUT HASHES.txt"):
            data = read(listing)
            if data is None:
                problems.append(f"{listing} missing"); continue
            for line in data.decode("utf-8", "replace").splitlines():
                m = HASH_LINE.match(line.strip())
                if not m: continue
                digest, rel = m.groups()
                body = read(rel)
                if body is None:
                    continue  # e.g. the original export, which is not inside the archive
                checked += 1
                if sha256_bytes(body) != digest:
                    problems.append(f"Hash mismatch: {rel}")
    info["checked"] = checked
    if checked == 0:
        problems.append("No files could be checked")
    return not problems, info, problems


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def register_row(root: Path, row: dict):
    reg = root / "register.csv"
    new = not reg.exists()
    with reg.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["filed_at", "file", "sha256", "chat", "tag", "messages", "files_checked", "result", "destination"])
        if new: w.writeheader()
        w.writerow(row)


def already_filed(root: Path, digest: str) -> bool:
    reg = root / "register.csv"
    return reg.exists() and digest in reg.read_text(encoding="utf-8")


def mirror(src: Path, root: Path, sync: Path | None):
    if not sync: return
    dest = sync / src.relative_to(root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir(): shutil.copytree(src, dest, dirs_exist_ok=True)
    else: shutil.copy2(src, dest)


def file_archive(z: Path, root: Path, sync: Path | None, keep_source: bool):
    digest = sha256_file(z)
    if already_filed(root, digest):
        log(f"Skipped (already filed): {z.name}"); return
    ok, info, problems = verify_archive(z)
    chat = safe(info.get("chat", z.stem))
    tag = safe(info.get("client") or (info.get("tags") or ["Untagged"])[0])
    date = (ARCHIVE_RE.search(z.name) or [None, datetime.now().strftime("%Y-%m-%d")])[1]
    row = {"filed_at": datetime.now().isoformat(timespec="seconds"), "file": z.name, "sha256": digest, "chat": info.get("chat", ""), "tag": tag,
           "messages": info.get("messages", ""), "files_checked": info.get("checked", 0)}
    if not ok:
        q = root / "_Quarantine"; q.mkdir(parents=True, exist_ok=True)
        shutil.move(str(z), q / z.name)
        register_row(root, {**row, "result": "FAILED: " + "; ".join(problems[:3]), "destination": str(q / z.name)})
        log(f"QUARANTINED {z.name}: {problems[0]}"); return
    dest_dir = root / tag / chat
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{date}_{chat}_archive.zip"
    n = 2
    while dest.exists():
        dest = dest_dir / f"{date}_{chat}_archive ({n}).zip"; n += 1
    (shutil.copy2 if keep_source else shutil.move)(str(z), dest)
    extract = dest.with_suffix("")
    with zipfile.ZipFile(dest) as zz: zz.extractall(extract)
    register_row(root, {**row, "result": "verified", "destination": str(dest)})
    mirror(dest, root, sync); mirror(extract, root, sync); mirror(root / "register.csv", root, sync)
    log(f"Filed {z.name} -> {dest.relative_to(root)}  ({info.get('checked')} files verified)")


def file_backup(b: Path, root: Path, sync: Path | None, keep_source: bool):
    dest = root / "Backups" / b.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and sha256_file(dest) == sha256_file(b):
        log(f"Skipped (already kept): {b.name}"); return
    (shutil.copy2 if keep_source else shutil.move)(str(b), dest)
    mirror(dest, root, sync)
    log(f"Kept backup {b.name} -> Backups/")


def scan(watch: Path, root: Path, sync: Path | None, keep_source: bool):
    for p in sorted(watch.iterdir()):
        if not p.is_file(): continue
        try:
            if ARCHIVE_RE.search(p.name) and stable(p):
                file_archive(p, root, sync, keep_source)
            elif BACKUP_RE.match(p.name) and stable(p):
                file_backup(p, root, sync, keep_source)
        except zipfile.BadZipFile:
            log(f"Not a valid ZIP, left in place: {p.name}")
        except Exception as e:  # keep the agent running
            log(f"Error with {p.name}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Verify and file ChatVault archives by client tag.")
    ap.add_argument("--watch", type=Path, default=Path.home() / "Downloads", help="folder to watch (default: Downloads)")
    ap.add_argument("--archive", type=Path, default=Path.home() / "ChatVault Archive", help="where filed archives go")
    ap.add_argument("--sync", type=Path, help="optional cloud-synced folder to mirror into (Google Drive, OneDrive…)")
    ap.add_argument("--keep", action="store_true", help="copy instead of move, leaving the download in place")
    ap.add_argument("--once", action="store_true", help="process current files and exit")
    ap.add_argument("--interval", type=float, default=5, help="seconds between scans")
    a = ap.parse_args()
    if not a.watch.is_dir(): sys.exit(f"Watch folder not found: {a.watch}")
    a.archive.mkdir(parents=True, exist_ok=True)
    log(f"Watching {a.watch}  ->  filing into {a.archive}" + (f"  (mirroring to {a.sync})" if a.sync else ""))
    while True:
        scan(a.watch, a.archive, a.sync, a.keep)
        if a.once: break
        time.sleep(a.interval)


if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: log("Stopped")
