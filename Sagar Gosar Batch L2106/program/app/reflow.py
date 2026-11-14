"""Smart paragraph alignment ("re-flow").

The draft (Word) is the reference.  Both documents are turned into word streams; unique word n-grams that
occur once in each stream are used as anchors (patience / LIS), the gaps are solved recursively, and every
draft paragraph then claims the stretch of the executed copy that holds its words – whatever way the scan
split the paragraphs, across pages or in the wrong order of lines.  What is left over in the executed copy
becomes added text (or stamp/registration noise, which is ignored).
"""
import bisect
import copy
import math
from difflib import SequenceMatcher

from .models import Block
from .textutil import looks_like_stamp, token_key


class Unit:
    __slots__ = ("a", "b", "note")

    def __init__(self, a, b, note=""):
        self.a, self.b, self.note = a, b, note        # a: list of draft block indexes, b: Block or None


# ------------------------------------------------------------------ stream matching
def _lis(pairs):
    """pairs sorted by a; longest strictly increasing subsequence on b."""
    if not pairs:
        return []
    tails, idx, prev = [], [], [-1] * len(pairs)
    for i, (_, b) in enumerate(pairs):
        k = bisect.bisect_left(tails, b)
        if k == len(tails):
            tails.append(b); idx.append(i)
        else:
            tails[k] = b; idx[k] = i
        prev[i] = idx[k - 1] if k else -1
    out, i = [], idx[-1]
    while i != -1:
        out.append(pairs[i]); i = prev[i]
    return out[::-1]


def match_streams(ka, kb, cancel=None):
    pairs = []
    stack = [(0, len(ka), 0, len(kb), 5)]
    steps = 0
    while stack:
        a0, a1, b0, b1, n = stack.pop()
        steps += 1
        if cancel is not None and steps % 200 == 0 and cancel():
            raise RuntimeError("cancelled")
        while a0 < a1 and b0 < b1 and ka[a0] == kb[b0]:
            pairs.append((a0, b0)); a0 += 1; b0 += 1
        while a0 < a1 and b0 < b1 and ka[a1 - 1] == kb[b1 - 1]:
            a1 -= 1; b1 -= 1; pairs.append((a1, b1))
        if a0 >= a1 or b0 >= b1:
            continue
        done = False
        for nn in range(n, 1, -1):
            if a1 - a0 < nn or b1 - b0 < nn:
                continue
            da, db = {}, {}
            for i in range(a0, a1 - nn + 1):
                da.setdefault(tuple(ka[i:i + nn]), []).append(i)
            for j in range(b0, b1 - nn + 1):
                db.setdefault(tuple(kb[j:j + nn]), []).append(j)
            cand = sorted((ia[0], db[g][0]) for g, ia in da.items() if len(ia) == 1 and g in db and len(db[g]) == 1)
            chosen = _lis(cand)
            if not chosen:
                continue
            runs = []
            for ia, ib in chosen:
                if runs and ia - ib == runs[-1][0] - runs[-1][1] and ia <= runs[-1][0] + runs[-1][2]:
                    runs[-1][2] = ia + nn - runs[-1][0]
                elif runs and (ia < runs[-1][0] + runs[-1][2] or ib < runs[-1][1] + runs[-1][2]):
                    continue
                else:
                    runs.append([ia, ib, nn])
            pa, pb = a0, b0
            for ia, ib, ln in runs:
                for k in range(ln):
                    pairs.append((ia + k, ib + k))
                stack.append((pa, ia, pb, ib, nn)); pa, pb = ia + ln, ib + ln
            stack.append((pa, a1, pb, b1, nn)); done = True
            break
        if done:
            continue
        la, lb = a1 - a0, b1 - b0
        if la * lb <= 4_000_000:
            sm = SequenceMatcher(None, ka[a0:a1], kb[b0:b1], autojunk=False)
            for i, j, ln in sm.get_matching_blocks():
                for k in range(ln):
                    pairs.append((a0 + i + k, b0 + j + k))
    pairs.sort()
    return pairs


# ------------------------------------------------------------------ helpers over blocks
class Stream:
    def __init__(self, blocks, opts):
        self.keys, self.blk, self.wi = [], [], []
        self.first = {}                      # block -> first stream position
        self.words = []
        for bi, b in enumerate(blocks):
            ws = b.body.split()
            self.words.append(ws)
            for k, w in enumerate(ws):
                key = token_key(w, opts.ignore_case, opts.compare_punct)
                if not key:
                    continue
                self.first.setdefault(bi, len(self.keys))
                self.keys.append(key); self.blk.append(bi); self.wi.append(k)


def _vblock(blocks, lo_blk, lo_wi, hi_blk, hi_wi, first_wi_of_blk):
    """Virtual paragraph made of body words [lo_blk:lo_wi .. hi_blk:hi_wi] (inclusive) of consecutive blocks."""
    parts, conf, regions, label = [], [], [], ""
    oc, cs = False, []
    for bi in range(lo_blk, hi_blk + 1):
        b = blocks[bi]
        ws = b.body.split()
        s = lo_wi if bi == lo_blk else 0
        e = hi_wi if bi == hi_blk else len(ws) - 1
        if e < s:
            continue
        parts += ws[s:e + 1]
        wc = list(b.word_conf) if len(b.word_conf) == len(ws) else [b.conf] * len(ws)
        conf += wc[s:e + 1]
        oc = oc or b.ocr; cs.append(b.conf)
        if bi == lo_blk and s <= first_wi_of_blk.get(bi, 0):
            label = b.label
        n = max(1, len(ws)); f0, f1 = s / n, (e + 1) / n
        for r in b.regions:
            if f0 <= 0.0 and f1 >= 1.0:
                regions.append(r)
            else:
                pg, x0, y0, x1, y1 = r
                regions.append((pg, x0, y0 + (y1 - y0) * f0, x1, y0 + (y1 - y0) * f1))
    body = " ".join(parts)
    base = blocks[lo_blk]
    v = Block(idx=-1, text=(label + " " + body).strip(), label=label, body=body, kind=base.kind, page=base.page, regions=regions,
              conf=round(sum(cs) / len(cs), 1) if cs else 100.0, word_conf=conf, ocr=oc, uid=base.uid)
    return v


def merge_blocks(blocks, lo, hi):
    """One Block built from blocks[lo:hi] (used for user-defined links)."""
    bl = blocks[lo:hi]
    if len(bl) == 1:
        return copy.copy(bl[0])
    first = {i: 0 for i in range(len(bl))}
    return _vblock(bl, 0, 0, len(bl) - 1, max(0, len(bl[-1].body.split()) - 1), first)


# ------------------------------------------------------------------ similarity / pairing DP
def _bag(keys):
    d = {}
    for k in keys:
        d[k] = d.get(k, 0) + 1
    return d


def similarity(ka, kb):
    if not ka or not kb:
        return 0.0
    ba, bb = _bag(ka), _bag(kb)
    inter = sum(min(v, bb.get(k, 0)) for k, v in ba.items())
    dice = 2.0 * inter / (len(ka) + len(kb))
    if dice < 0.25:
        return dice
    return SequenceMatcher(None, ka, kb, autojunk=False).ratio()


def _pair_dp(a_keys, b_keys, thr=0.30):
    """Order-preserving pairing of unmatched draft paragraphs with leftover executed paragraphs."""
    n, m = len(a_keys), len(b_keys)
    if not n or not m:
        return []
    sim = [[similarity(a_keys[i], b_keys[j]) for j in range(m)] for i in range(n)]
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            best = max(dp[i + 1][j], dp[i][j + 1])
            if sim[i][j] >= thr:
                best = max(best, sim[i][j] + dp[i + 1][j + 1])
            dp[i][j] = best
    out, i, j = [], 0, 0
    while i < n and j < m:
        if sim[i][j] >= thr and abs(dp[i][j] - (sim[i][j] + dp[i + 1][j + 1])) < 1e-9:
            out.append((i, j)); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


# ------------------------------------------------------------------ window alignment
def _clusters(positions, nwords):
    positions = sorted(positions)
    gap = max(60, 3 * nwords)
    cl, cur = [], [positions[0]]
    for p in positions[1:]:
        if p - cur[-1] > gap:
            cl.append(cur); cur = [p]
        else:
            cur.append(p)
    cl.append(cur)
    return max(cl, key=len)


def align_window(A, B, opts, cancel=None):
    """-> (units, ignored_b_blocks) for lists of Blocks A (draft) and B (executed)."""
    units, ignored = [], []
    if not A and not B:
        return units, ignored
    sa, sb = Stream(A, opts), Stream(B, opts)
    pairs = match_streams(sa.keys, sb.keys, cancel) if sa.keys and sb.keys else []
    per_a = {}
    for ia, ib in pairs:
        per_a.setdefault(sa.blk[ia], []).append(ib)
    spans = {}                   # draft block -> [start, end] stream positions in B
    prev_end = -1
    for ai in range(len(A)):
        pos = per_a.get(ai)
        nw = len(A[ai].body.split())
        if not pos:
            continue
        need = 1 if nw <= 3 else max(2, math.ceil(0.22 * nw))
        cl = _clusters(pos, nw)
        if len(cl) < need:
            continue
        s, e = cl[0], cl[-1]
        if s <= prev_end:
            s = prev_end + 1
        if s > e:
            continue
        spans[ai] = [s, e]; prev_end = e
    matched = sorted(spans)
    nB = len(sb.keys)
    # gap attachment ------------------------------------------------------------
    gaps = []                      # (left_draft_idx or None, right_draft_idx or None, lo, hi)  hi exclusive
    if not matched:
        gaps.append((None, None, 0, nB))
    else:
        gaps.append((None, matched[0], 0, spans[matched[0]][0]))
        for x, y in zip(matched, matched[1:]):
            gaps.append((x, y, spans[x][1] + 1, spans[y][0]))
        gaps.append((matched[-1], None, spans[matched[-1]][1] + 1, nB))
    leftovers = {}                 # gap index -> list of (lo, hi) stream-position runs forming pseudo paragraphs
    for gi, (x, y, lo, hi) in enumerate(gaps):
        if lo >= hi:
            leftovers[gi] = []
            continue
        runs = []
        i = lo
        while i < hi:
            j = i
            while j + 1 < hi and sb.blk[j + 1] == sb.blk[i]:
                j += 1
            runs.append([i, j]); i = j + 1
        if x is not None and runs and sb.blk[runs[0][0]] == sb.blk[spans[x][1]]:
            spans[x][1] = runs[0][1]; runs.pop(0)          # continuation of the paragraph the draft block ended in
        if y is not None and runs and sb.blk[runs[-1][1]] == sb.blk[spans[y][0]]:
            spans[y][0] = runs[-1][0]; runs.pop()
        leftovers[gi] = [tuple(r) for r in runs]

    def vb(lo, hi):
        l_blk, h_blk = sb.blk[lo], sb.blk[hi]
        return _vblock(B, l_blk, sb.wi[lo], h_blk, sb.wi[hi], sb.first_wi)
    sb.first_wi = {bi: sb.wi[p] for bi, p in sb.first.items()}

    def emit_gap(gi, a_lo, a_hi):
        """Unmatched draft paragraphs a_lo..a_hi-1 and leftover executed runs of gap gi."""
        runs = leftovers.get(gi, [])
        ablocks = list(range(a_lo, a_hi))
        bblocks = [vb(lo, hi) for lo, hi in runs]
        ak = [sa_keys_of(i) for i in ablocks]
        bk = [[token_key(w, opts.ignore_case, opts.compare_punct) for w in b.body.split() if token_key(w, opts.ignore_case, opts.compare_punct)] for b in bblocks]
        pr = dict(_pair_dp(ak, bk))
        used_b = set(pr.values())
        # order-preserving interleave
        bi = 0
        for k, ai in enumerate(ablocks):
            if k in pr:
                while bi < pr[k]:
                    _emit_b_only(bblocks[bi], units, ignored, A, opts); bi += 1
                units.append(Unit([ai], bblocks[pr[k]], "paired")); bi = pr[k] + 1
            else:
                units.append(Unit([ai], None, "deleted"))
        while bi < len(bblocks):
            _emit_b_only(bblocks[bi], units, ignored, A, opts); bi += 1

    def sa_keys_of(ai):
        return [token_key(w, opts.ignore_case, opts.compare_punct) for w in A[ai].body.split() if token_key(w, opts.ignore_case, opts.compare_punct)]

    if not matched:
        emit_gap(0, 0, len(A))
    else:
        emit_gap(0, 0, matched[0])
        for n_, ai in enumerate(matched):
            s, e = spans[ai]
            units.append(Unit([ai], vb(s, e), "matched"))
            nxt = matched[n_ + 1] if n_ + 1 < len(matched) else len(A)
            emit_gap(n_ + 1, ai + 1, nxt)
    return units, ignored


def _emit_b_only(b, units, ignored, A, opts):
    best = 0.0
    if opts.ignore_stamps:
        kb = [token_key(w, opts.ignore_case, opts.compare_punct) for w in b.body.split()]
        kb = [k for k in kb if k]
        if looks_like_stamp(b.text, 0.0 if len(kb) < 6 else 0.0):
            ignored.append(b); return
    units.append(Unit([], b, "added"))


# ------------------------------------------------------------------ public entry
def align(doc_a, doc_b, opts, anchors=None, cancel=None):
    """-> (units, ignored_b).  `anchors` = [(ia0, ia1, ib0, ib1)] block-index ranges forced to be compared with each other."""
    A, B = doc_a.blocks, doc_b.blocks
    anchors = sorted(anchors or [], key=lambda t: (t[0], t[2]))
    clean, la, lb = [], 0, 0
    for t in anchors:                    # keep only monotonic, non-overlapping anchors
        if t[0] >= la and t[2] >= lb and t[1] > t[0] and t[3] > t[2]:
            clean.append(t); la, lb = t[1], t[3]
    units, ignored = [], []
    pa = pb = 0
    for (a0, a1, b0, b1) in clean + [(len(A), len(A), len(B), len(B))]:
        u, ig = align_window(A[pa:a0], B[pb:b0], opts, cancel)
        for x in u:
            x.a = [i + pa for i in x.a]
        units += u; ignored += ig
        if a1 > a0 and b1 > b0:
            units.append(Unit(list(range(a0, a1)), merge_blocks(B, b0, b1), "forced"))
        pa, pb = a1, b1
    return units, ignored
