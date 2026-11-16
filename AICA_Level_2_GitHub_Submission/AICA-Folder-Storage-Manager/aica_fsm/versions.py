"""Likely versions / similar files. Kept strictly separate from exact (hash-verified) duplicates:
pairs with identical SHA-256 are never reported here."""
from __future__ import annotations

import difflib
import json
import os
import re
from collections import defaultdict
from datetime import datetime

from .store import ProjectDB
from .textextract import DOC_EXTS, IMAGE_EXTS, cached_extract

VERSION_TOKENS = [
    (re.compile(r"[\s_\-.]*\(\d+\)$"), "copy number"),
    (re.compile(r"[\s_\-.]*-?\s*copy(\s*\(\d+\))?$", re.I), "'copy'"),
    (re.compile(r"^copy of\s+", re.I), "'Copy of'"),
    (re.compile(r"[\s_\-.]*(v|ver|version|rev|r)\s*\.?\s*\d+(\.\d+)*$", re.I), "version number"),
    (re.compile(r"[\s_\-.]*(final|draft|old|new|latest|updated|revised|edited|signed|scan(ned)?)$", re.I), "status word"),
    (re.compile(r"[\s_\-.]*\d{4}[-_.]?\d{2}[-_.]?\d{2}$"), "date"),
    (re.compile(r"[\s_\-.]*\d{1,2}[-_.]\d{1,2}[-_.]\d{2,4}$"), "date"),
    (re.compile(r"[\s_\-]+\d{1,3}$"), "trailing number"),
]
EXT_FAMILY = {"doc": "word", "docx": "word", "xls": "excel", "xlsx": "excel", "xlsm": "excel",
              "jpg": "image", "jpeg": "image", "png": "image", "tif": "image", "tiff": "image", "bmp": "image",
              "gif": "image", "webp": "image"}


def base_name(name: str) -> tuple[str, list[str]]:
    stem, _ = os.path.splitext(name)
    s = stem.strip()
    found = []
    changed = True
    while changed and s:
        changed = False
        for rx, label in VERSION_TOKENS:
            ns = rx.sub("", s).strip()
            if ns != s and ns:
                s = ns
                found.append(label)
                changed = True
    s = re.sub(r"[\s_\-.]+", " ", s).strip().lower()
    return s, found


def _version_num(name: str):
    m = re.search(r"(?:v|ver|version|rev|r)\s*\.?\s*(\d+(?:\.\d+)*)", os.path.splitext(name)[0], re.I)
    if m:
        return tuple(int(x) for x in m.group(1).split("."))
    m = re.search(r"\((\d+)\)\s*$", os.path.splitext(name)[0])
    if m:
        return (int(m.group(1)),)
    return None


def _name_date(name: str):
    stem = os.path.splitext(name)[0]
    m = re.search(r"(\d{4})[-_.]?(\d{2})[-_.]?(\d{2})", stem)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})[-_.](\d{1,2})[-_.](\d{4})", stem)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None


STATUS_RANK = {"draft": 0, "old": 0, "edited": 1, "revised": 1, "updated": 1, "new": 2, "latest": 3, "final": 3, "signed": 4}


def _status_rank(name: str):
    stem = os.path.splitext(name)[0].lower()
    best = None
    for w, r in STATUS_RANK.items():
        if re.search(rf"(^|[\s_\-.]){w}($|[\s_\-.])", stem):
            best = r if best is None else max(best, r)
    return best


def order_evidence(a: dict, b: dict) -> tuple[str | None, str, bool]:
    """-> (older_rel_path or None, explanation, certain)."""
    votes = []  # (+1 means a is older)
    notes = []
    va, vb = _version_num(a["name"]), _version_num(b["name"])
    if va and vb and va != vb:
        votes.append(1 if va < vb else -1)
        notes.append(f"version in name ({'.'.join(map(str, va))} vs {'.'.join(map(str, vb))})")
    da, dbb = _name_date(a["name"]), _name_date(b["name"])
    if da and dbb and da != dbb:
        votes.append(1 if da < dbb else -1)
        notes.append("date in file name")
    sa, sb = _status_rank(a["name"]), _status_rank(b["name"])
    if sa is not None and sb is not None and sa != sb:
        votes.append(1 if sa < sb else -1)
        notes.append("status word in name (draft/final...)")
    ia, ib = a.get("doc_modified") or "", b.get("doc_modified") or ""
    if ia and ib and ia != ib:
        votes.append(1 if ia < ib else -1)
        notes.append("document's internal modified date")
    ma, mb = a.get("mtime") or 0, b.get("mtime") or 0
    fs_vote = 0
    if ma and mb and abs(ma - mb) > 1:
        fs_vote = 1 if ma < mb else -1
        notes.append("file modified date")
    strong = votes
    if strong and all(v == strong[0] for v in strong):
        if fs_vote and fs_vote != strong[0]:
            return None, "Conflicting evidence: " + ", ".join(notes) + " disagree", False
        older = a["rel_path"] if strong[0] == 1 else b["rel_path"]
        return older, "Based on " + ", ".join(notes), True
    if strong:
        return None, "Conflicting evidence: " + ", ".join(notes), False
    if fs_vote:
        older = a["rel_path"] if fs_vote == 1 else b["rel_path"]
        return older, "Only the file modified date suggests the order (dates can change on copy)", False
    return None, "No usable evidence for order", False


def _shingles(text: str, k=5) -> set[int]:
    w = re.findall(r"\w+", text.lower())
    if len(w) < k:
        return {hash(" ".join(w))} if w else set()
    return {hash(" ".join(w[i:i + k])) for i in range(len(w) - k + 1)}


def _dhash(path: str) -> int | None:
    try:
        from PIL import Image
        with Image.open(path) as im:
            g = im.convert("L").resize((9, 8))
            px = list(g.tobytes())
        bits = 0
        for row in range(8):
            for col in range(8):
                bits = (bits << 1) | (1 if px[row * 9 + col] > px[row * 9 + col + 1] else 0)
        return bits
    except Exception:
        return None


def analyse(db: ProjectDB, scan_id: str, progress=None, cancel=None, text_threshold=0.5, image_max_dist=10,
            max_docs=3000, max_images=4000) -> int:
    root = db.project.root_path
    rows = [dict(r) for r in db.con.execute(
        "SELECT rel_path, name, ext, size, mtime, sha256 FROM files WHERE scan_id=?", (scan_id,))]
    pairs: dict[tuple[str, str], dict] = {}

    def add(a, b, reason, score):
        if a["sha256"] and a["sha256"] == b["sha256"]:
            return  # exact duplicate -> Duplicates view, not here
        key = tuple(sorted((a["rel_path"], b["rel_path"])))
        p = pairs.setdefault(key, {"a": a if a["rel_path"] == key[0] else b,
                                   "b": b if a["rel_path"] == key[0] else a, "reasons": [], "score": 0.0})
        p["reasons"].append(reason)
        p["score"] = max(p["score"], score)

    # 1) filename patterns
    groups = defaultdict(list)
    for r in rows:
        b, toks = base_name(r["name"])
        if len(b) < 3:
            continue
        fam = EXT_FAMILY.get(r["ext"], r["ext"])
        groups[(b, fam)].append((r, toks))
    for (b, fam), items in groups.items():
        if len(items) < 2 or len(items) > 30:
            continue
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (ra, ta), (rb, tb) = items[i], items[j]
                if ra["name"].lower() == rb["name"].lower():
                    why = f"Same file name in different folders ('{ra['name']}')"
                else:
                    tags = sorted(set(ta + tb)) or ["name variant"]
                    why = f"Name pattern: same base name '{b}' ({', '.join(tags)})"
                add(ra, rb, why, 0.6)

    # 2) extracted text similarity (documents)
    docs = [r for r in rows if r["ext"] in DOC_EXTS and r["size"] > 0][:max_docs]
    sigs = {}
    texts = {}
    for i, r in enumerate(docs):
        if cancel is not None and cancel.is_set():
            break
        if progress:
            progress(i, len(docs) + 1, f"Reading {r['rel_path']}")
        try:
            ex = cached_extract(db, r["rel_path"])
        except OSError:
            continue
        r["doc_modified"] = ex.doc_modified
        t = ex.text
        if len(t.strip()) < 40:
            continue
        texts[r["rel_path"]] = t
        sigs[r["rel_path"]] = _shingles(t)
    # candidate generation through an inverted index on a sample of shingles
    index = defaultdict(set)
    for rp, sh in sigs.items():
        for h in sorted(sh)[:200]:
            index[h].add(rp)
    cand = set()
    for rps in index.values():
        if 1 < len(rps) <= 50:
            lst = sorted(rps)
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    cand.add((lst[i], lst[j]))
    for key in pairs:
        if key[0] in sigs and key[1] in sigs:
            cand.add(key)
    byrel = {r["rel_path"]: r for r in rows}
    for a, b in cand:
        sa, sb = sigs[a], sigs[b]
        if not sa or not sb:
            continue
        jac = len(sa & sb) / len(sa | sb)
        if jac >= text_threshold or (tuple(sorted((a, b))) in pairs and jac >= 0.2):
            add(byrel[a], byrel[b], f"Extracted text {jac:.0%} similar", jac)

    # 3) images: perceptual difference hash
    imgs = [r for r in rows if r["ext"] in IMAGE_EXTS and r["size"] > 0][:max_images]
    hashes = []
    for i, r in enumerate(imgs):
        if cancel is not None and cancel.is_set():
            break
        if progress and i % 20 == 0:
            progress(len(docs) + 1, len(docs) + 1, f"Image fingerprint {i}/{len(imgs)}")
        h = _dhash(os.path.join(root, r["rel_path"]))
        if h is not None:
            hashes.append((r, h))
    for i in range(len(hashes)):
        ra, ha = hashes[i]
        for j in range(i + 1, len(hashes)):
            rb, hb = hashes[j]
            d = (ha ^ hb).bit_count()
            if d <= image_max_dist:
                add(ra, rb, f"Images look alike (difference {d}/64)", 1 - d / 64)

    with db._write_lock:
        db.con.execute("DELETE FROM version_pairs WHERE scan_id=?", (scan_id,))
        out = []
        for key, p in pairs.items():
            older, note, certain = order_evidence(p["a"], p["b"])
            out.append((scan_id, key[0], key[1], p["score"], json.dumps(p["reasons"]), older, note, 1 if certain else 0))
        db.con.executemany("INSERT INTO version_pairs(scan_id,path_a,path_b,score,reasons,older,order_note,order_certain)"
                           " VALUES(?,?,?,?,?,?,?,?)", out)
        db.con.commit()
    db.log_action("Analyse versions", "Done", scan_id=scan_id, detail=f"{len(pairs)} candidate pair(s)")
    return len(pairs)


def pairs_for(db: ProjectDB, scan_id: str):
    return db.con.execute("SELECT * FROM version_pairs WHERE scan_id=? ORDER BY score DESC, path_a", (scan_id,)).fetchall()


def text_diff(a: str, b: str, max_lines=4000) -> list[tuple[str, str]]:
    """-> list of (tag, line) where tag in ' ', '-', '+'."""
    al = a.splitlines()[:max_lines]
    bl = b.splitlines()[:max_lines]
    out = []
    for line in difflib.ndiff(al, bl):
        tag = line[:1]
        if tag in " -+":
            out.append((tag, line[2:]))
    return out
