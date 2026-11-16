"""The ONLY module that changes files on disk.

Duplicate deletion
  * every group keeps at least one copy; the kept copy and every selected copy are re-fingerprinted
    immediately before acting; if anything differs the whole group is skipped
  * Recycle Bin on fixed local drives; network/removable locations are permanent deletions and must
    be explicitly allowed by the caller (separate confirmation in the UI)
Moves
  * source must exist and be inside the project folder; destination folder must be reachable
  * never overwrites: conflicts are reported and resolved by the user (skip / keep both)
  * cross-volume moves copy -> verify SHA-256 -> remove source
Every per-file outcome is written to the project's audit log.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field

from .paths import is_within, supports_recycle_bin
from .scanner import sha256_file
from .store import ProjectDB


@dataclass
class DeletePlanGroup:
    sha256: str
    size: int
    keep: str               # relative path
    delete: list[str]       # relative paths


@dataclass
class Outcome:
    path: str
    outcome: str
    error: str = ""
    destination: str = ""


@dataclass
class ActionReport:
    results: list[Outcome] = field(default_factory=list)

    def count(self, outcome: str) -> int:
        return sum(1 for r in self.results if r.outcome == outcome)


def classify_deletion(project_root: str, rel_paths: list[str]) -> tuple[list[str], list[str]]:
    """-> (recyclable, permanent)."""
    rec, perm = [], []
    for rp in rel_paths:
        full = os.path.join(project_root, rp)
        (rec if supports_recycle_bin(full) else perm).append(rp)
    return rec, perm


def _recycle(full: str) -> None:
    from send2trash import send2trash
    send2trash(full)
    if os.path.lexists(full):
        raise OSError("File still present after sending to Recycle Bin")


def delete_duplicates(db: ProjectDB, scan_id: str, groups: list[DeletePlanGroup],
                      allow_permanent: bool, progress=None, cancel=None) -> ActionReport:
    root = db.project.root_path
    rep = ActionReport()
    for gi, g in enumerate(groups):
        if cancel is not None and cancel.is_set():
            break
        if progress:
            progress(gi, len(groups), g.keep)
        if not g.delete:
            continue
        keep_full = os.path.join(root, g.keep)
        # sanity: keep is not one of the deletions, everything inside the project
        if any(d.lower() == g.keep.lower() for d in g.delete):
            for d in g.delete:
                _log(db, rep, scan_id, os.path.join(root, d), "Skipped", "Kept copy is also selected for deletion")
            continue
        bad = [d for d in [g.keep, *g.delete] if not is_within(root, os.path.join(root, d))]
        if bad:
            for d in g.delete:
                _log(db, rep, scan_id, os.path.join(root, d), "Skipped", "Path outside project folder")
            continue
        # re-verify kept copy
        try:
            if not os.path.isfile(keep_full):
                raise FileNotFoundError("Kept copy no longer exists")
            if os.path.getsize(keep_full) != g.size or sha256_file(keep_full) != g.sha256:
                raise ValueError("Kept copy has changed since the scan")
        except (OSError, ValueError) as e:
            for d in g.delete:
                _log(db, rep, scan_id, os.path.join(root, d), "Skipped",
                     f"Group skipped - kept copy could not be re-verified: {e}")
            continue
        try:
            keep_id = os.stat(keep_full).st_ino
        except OSError:
            keep_id = None
        for d in g.delete:
            full = os.path.join(root, d)
            try:
                if not os.path.isfile(full):
                    raise FileNotFoundError("File no longer exists")
                st = os.stat(full)
                if keep_id and st.st_ino == keep_id and st.st_ino != 0:
                    raise ValueError("Same physical file as the kept copy (hard link) - not deleted")
                if st.st_size != g.size or sha256_file(full) != g.sha256:
                    raise ValueError("File changed since the scan - not an exact copy any more")
            except (OSError, ValueError) as e:
                _log(db, rep, scan_id, full, "Skipped", str(e))
                continue
            if supports_recycle_bin(full):
                try:
                    _recycle(full)
                    _log(db, rep, scan_id, full, "Recycled", detail=f"Kept: {keep_full}; SHA-256 {g.sha256}")
                except Exception as e:
                    _log(db, rep, scan_id, full, "Failed", f"Recycle Bin: {e}")
            else:
                if not allow_permanent:
                    _log(db, rep, scan_id, full, "Skipped", "Location has no Recycle Bin; permanent deletion not confirmed")
                    continue
                try:
                    os.remove(full)
                    _log(db, rep, scan_id, full, "Deleted permanently", detail=f"Kept: {keep_full}; SHA-256 {g.sha256}")
                except OSError as e:
                    _log(db, rep, scan_id, full, "Failed", f"{type(e).__name__}: {e.strerror or e}")
    return rep


def _log(db, rep, scan_id, path, outcome, error="", destination="", detail="", action="Delete duplicate copy"):
    rep.results.append(Outcome(path, outcome, error, destination))
    db.log_action(action, outcome, source=path, destination=destination, error=error, scan_id=scan_id, detail=detail)


# ------------------------------------------------------------------------------------- moves
@dataclass
class MovePlanItem:
    rel_path: str          # source relative to project root
    dest_folder: str       # absolute folder
    dest_name: str         # file name to use at destination
    on_conflict: str = "ask"   # ask | skip | keep_both
    queue_id: int | None = None

    def source(self, root: str) -> str:
        return os.path.join(root, self.rel_path)

    def destination(self) -> str:
        return os.path.join(self.dest_folder, self.dest_name)


def unique_name(folder: str, name: str) -> str:
    stem, ext = os.path.splitext(name)
    i = 2
    cand = name
    while os.path.lexists(os.path.join(folder, cand)):
        cand = f"{stem} ({i}){ext}"
        i += 1
    return cand


def preflight_moves(root: str, items: list[MovePlanItem]) -> list[dict]:
    """Checks without changing anything. Returns rows for the review screen."""
    out = []
    seen_dest = {}
    for it in items:
        src = it.source(root)
        dst = it.destination()
        problems = []
        conflict = False
        if not is_within(root, src):
            problems.append("Source is outside the project folder")
        elif not os.path.isfile(src):
            problems.append("Source file no longer exists")
        if not it.dest_folder:
            problems.append("No destination folder")
        elif os.path.exists(it.dest_folder) and not os.path.isdir(it.dest_folder):
            problems.append("Destination is not a folder")
        else:
            parent = it.dest_folder
            while parent and not os.path.exists(parent):
                nxt = os.path.dirname(parent)
                if nxt == parent:
                    break
                parent = nxt
            if not parent or not os.path.isdir(parent):
                problems.append("Destination is not reachable")
        if os.path.normcase(os.path.abspath(src)) == os.path.normcase(os.path.abspath(dst)):
            problems.append("Source and destination are the same")
        elif os.path.lexists(dst):
            conflict = True
        key = os.path.normcase(os.path.abspath(dst))
        if key in seen_dest:
            conflict = True
            problems.append(f"Another selected file also goes to this name ({seen_dest[key]})")
        seen_dest[key] = it.rel_path
        out.append({"item": it, "source": src, "destination": dst, "conflict": conflict,
                    "creates_folder": bool(it.dest_folder) and not os.path.isdir(it.dest_folder),
                    "problems": problems})
    return out


def _same_volume(src: str, dest_folder: str) -> bool:
    try:
        probe = dest_folder
        while not os.path.exists(probe):
            probe = os.path.dirname(probe)
        return os.stat(src).st_dev == os.stat(probe).st_dev and (
            src[:2].lower() == probe[:2].lower() or (src.startswith("\\\\") and probe.startswith("\\\\")
                                                     and src.split("\\")[2:4] == probe.split("\\")[2:4]))
    except OSError:
        return False


def move_files(db: ProjectDB, scan_id: str, items: list[MovePlanItem], progress=None, cancel=None) -> ActionReport:
    root = db.project.root_path
    rep = ActionReport()
    for i, it in enumerate(items):
        if cancel is not None and cancel.is_set():
            break
        if progress:
            progress(i, len(items), it.rel_path)
        src = it.source(root)
        try:
            if not is_within(root, src):
                raise ValueError("Source is outside the project folder")
            if not os.path.isfile(src):
                raise FileNotFoundError("Source file no longer exists")
            os.makedirs(it.dest_folder, exist_ok=True)
            name = it.dest_name
            dst = os.path.join(it.dest_folder, name)
            if os.path.lexists(dst):
                if it.on_conflict == "keep_both":
                    name = unique_name(it.dest_folder, name)
                    dst = os.path.join(it.dest_folder, name)
                else:
                    raise FileExistsError("A file with this name already exists at the destination (not overwritten)")
            if _same_volume(src, it.dest_folder):
                os.rename(src, dst)  # raises if dst appeared meanwhile -> never overwrites
                method = "Renamed on same volume"
            else:
                src_hash = sha256_file(src)
                tmp = os.path.join(it.dest_folder, f".{name}.aica-partial")
                if os.path.lexists(tmp):
                    raise FileExistsError(f"Temporary file exists: {tmp}")
                try:
                    shutil.copy2(src, tmp)
                    if sha256_file(tmp) != src_hash:
                        raise OSError("Copy verification failed (SHA-256 mismatch)")
                    if os.path.lexists(dst):
                        raise FileExistsError("A file with this name appeared at the destination (not overwritten)")
                    os.rename(tmp, dst)
                except BaseException:
                    try:
                        if os.path.lexists(tmp):
                            os.remove(tmp)
                    except OSError:
                        pass
                    raise
                os.remove(src)
                method = f"Copied, verified SHA-256 {src_hash[:16]}..., source removed"
            _log(db, rep, scan_id, src, "Moved", destination=dst, detail=method, action="Move file")
            if it.queue_id is not None:
                with db._write_lock:
                    db.con.execute("UPDATE organize_queue SET status='Moved', note=?, selected=0 WHERE id=?",
                                   (dst, it.queue_id))
                    db.con.commit()
        except (OSError, ValueError) as e:
            msg = f"{type(e).__name__}: {getattr(e, 'strerror', None) or e}"
            _log(db, rep, scan_id, src, "Failed", msg, destination=it.destination(), action="Move file")
            if it.queue_id is not None:
                with db._write_lock:
                    db.con.execute("UPDATE organize_queue SET status='Move failed', note=? WHERE id=?", (msg, it.queue_id))
                    db.con.commit()
    return rep
