"""Compare two snapshots of the same project.

Result kinds:
  New, Modified, Deleted, Moved            - certain
  Possible move                           - uncertain, needs review (old+new not also listed as Deleted/New)
  Unverified                              - file was in the older snapshot, but its folder could not be
                                            read in the newer one -> NOT reported as deleted
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

MTIME_TOL = 0.0005


@dataclass
class FileRec:
    rel_path: str
    size: int
    mtime: float | None
    file_id: str | None
    sha256: str | None
    name: str = ""

    @property
    def lname(self) -> str:
        return (self.name or self.rel_path.rsplit("\\", 1)[-1]).lower()


@dataclass
class Change:
    kind: str
    old: FileRec | None = None
    new: FileRec | None = None
    method: str = ""


@dataclass
class DiffResult:
    changes: list[Change] = field(default_factory=list)

    def by_kind(self, kind: str) -> list[Change]:
        return [c for c in self.changes if c.kind == kind]


def _under(path: str, blocked: list[str]) -> bool:
    lp = path.lower()
    for b in blocked:
        if b == "":
            return True
        lb = b.lower()
        if lp == lb or lp.startswith(lb + "\\"):
            return True
    return False


def _modified(a: FileRec, b: FileRec) -> bool:
    if a.size != b.size:
        return True
    if a.sha256 and b.sha256:
        return a.sha256 != b.sha256
    if a.mtime is None or b.mtime is None:
        return False
    return abs(a.mtime - b.mtime) > MTIME_TOL


def diff(old: dict[str, FileRec], new: dict[str, FileRec], unverified_locations: list[str]) -> DiffResult:
    """old/new are keyed by lower-cased relative path. *unverified_locations* are relative paths
    (folders or files; '' = whole root) that could not be read in the NEW snapshot."""
    res = DiffResult()
    old_only: dict[str, FileRec] = {}
    new_only: dict[str, FileRec] = dict(new)

    for key, o in old.items():
        n = new_only.pop(key, None)
        if n is None:
            old_only[key] = o
        elif _modified(o, n):
            res.changes.append(Change("Modified", o, n, "Size/content changed" if o.size != n.size or (
                o.sha256 and n.sha256 and o.sha256 != n.sha256) else "Modified date changed"))

    # Files missing from an unreadable location are unverified, never deleted.
    for key in list(old_only):
        if _under(old_only[key].rel_path, unverified_locations):
            res.changes.append(Change("Unverified", old_only.pop(key), None, "Location could not be checked"))

    # 1) Reliable file identity (NTFS / SMB file id on the same volume).
    by_id_new = defaultdict(list)
    for k, n in new_only.items():
        if n.file_id:
            by_id_new[n.file_id].append(k)
    for k in list(old_only):
        o = old_only[k]
        if not o.file_id:
            continue
        cands = [c for c in by_id_new.get(o.file_id, []) if c in new_only]
        if len(cands) == 1:
            n = new_only.pop(cands[0])
            old_only.pop(k)
            m = "File ID"
            if _modified(o, n):
                m += " (content also changed)"
            res.changes.append(Change("Moved", o, n, m))

    # 2) Unambiguous full-content match (SHA-256, one old <-> one new).
    old_by_hash = defaultdict(list)
    new_by_hash = defaultdict(list)
    for k, o in old_only.items():
        if o.sha256 and o.size > 0:
            old_by_hash[o.sha256].append(k)
    for k, n in new_only.items():
        if n.sha256 and n.size > 0:
            new_by_hash[n.sha256].append(k)
    for h, oks in old_by_hash.items():
        nks = new_by_hash.get(h, [])
        if not nks:
            continue
        if len(oks) == 1 and len(nks) == 1:
            res.changes.append(Change("Moved", old_only.pop(oks[0]), new_only.pop(nks[0]), "Identical content (SHA-256)"))
        else:
            # ambiguous: pair them up only as candidates for review
            for ok_, nk in zip(oks, nks):
                res.changes.append(Change("Possible move", old_only.pop(ok_), new_only.pop(nk),
                                          f"Identical content, but {len(oks)} old / {len(nks)} new copies"))

    # 3) Weaker evidence: same name + size, or same size + modified time -> candidate only.
    def weak_pairs(keyfn, label):
        o_idx = defaultdict(list)
        n_idx = defaultdict(list)
        for k, o in old_only.items():
            kk = keyfn(o)
            if kk is not None:
                o_idx[kk].append(k)
        for k, n in new_only.items():
            kk = keyfn(n)
            if kk is not None:
                n_idx[kk].append(k)
        for kk, oks in o_idx.items():
            nks = n_idx.get(kk, [])
            if len(oks) == 1 and len(nks) == 1 and oks[0] in old_only and nks[0] in new_only:
                o0, n0 = old_only[oks[0]], new_only[nks[0]]
                if o0.sha256 and n0.sha256 and o0.sha256 != n0.sha256:
                    continue  # proven different content
                o = old_only.pop(oks[0])
                n = new_only.pop(nks[0])
                res.changes.append(Change("Possible move", o, n, label))

    weak_pairs(lambda r: (r.lname, r.size) if r.size > 0 else None, "Same name and size (content not verified)")
    weak_pairs(lambda r: (r.size, round(r.mtime or 0, 3)) if r.size > 0 and r.mtime else None,
               "Same size and modified date (renamed?)")

    for o in old_only.values():
        res.changes.append(Change("Deleted", o, None, ""))
    for n in new_only.values():
        res.changes.append(Change("New", None, n, ""))
    return res
