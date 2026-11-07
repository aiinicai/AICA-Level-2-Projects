import copy, json
from dataclasses import replace
from .models import Block, DocText
def _reindex(doc):
    for i, b in enumerate(doc.blocks): b.idx = i
def next_uid(doc): return max([b.uid for b in doc.blocks] + [-1]) + 1
def index_of(doc, uid):
    for i, b in enumerate(doc.blocks):
        if b.uid == uid: return i
    return -1
def working_copy(doc):
    d = replace(doc, blocks=[copy.deepcopy(b) for b in doc.blocks])
    for i, b in enumerate(d.blocks): b.uid = i
    return d
def merge(doc, uids):
    idx = sorted(index_of(doc, u) for u in uids)
    if len(idx) < 2 or idx[0] < 0 or idx != list(range(idx[0], idx[0] + len(idx))): return None
    bl = [doc.blocks[i] for i in idx]
    body = " ".join(b.body.strip() for b in bl if b.body.strip())
    new = Block(idx=idx[0], text=(bl[0].label + " " + body).strip(), label=bl[0].label, body=body, page=bl[0].page,
                regions=[r for b in bl for r in b.regions], uid=next_uid(doc),
                ocr=any(b.ocr for b in bl), conf=min(b.conf for b in bl), word_conf=[c for b in bl for c in (b.word_conf or [])])
    doc.blocks[idx[0]:idx[-1] + 1] = [new]; _reindex(doc); return new.uid
def split(doc, uid, pos):
    i = index_of(doc, uid)
    if i < 0: return None
    b = doc.blocks[i]; a_t, b_t = b.body[:pos].strip(), b.body[pos:].strip()
    if not a_t or not b_t: return None
    u1, u2 = next_uid(doc), next_uid(doc) + 1
    one = Block(text=a_t, label=b.label, body=a_t, page=b.page, regions=b.regions, uid=u1, ocr=b.ocr, conf=b.conf)
    two = Block(text=b_t, body=b_t, page=b.page, regions=b.regions, uid=u2, ocr=b.ocr, conf=b.conf)
    doc.blocks[i:i + 1] = [one, two]; _reindex(doc); return u1, u2
def edit(doc, uid, body):
    i = index_of(doc, uid)
    if i < 0: return False
    b = doc.blocks[i]; b.body = " ".join(body.split()); b.text = (b.label + " " + b.body).strip(); return True
def set_ignored(doc, uids, flag=True):
    s = set(uids)
    for b in doc.blocks:
        if b.uid in s: b.ignored = flag
def ignore_range(doc, uid, above=True):
    i = index_of(doc, uid)
    if i < 0: return
    for k in (range(0, i) if above else range(i + 1, len(doc.blocks))): doc.blocks[k].ignored = True
def _norm_head(t):
    import re
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", re.sub(r"[^\w\s]", " ", t.lower()))).strip()


def drop_repeated_heads(doc):
    """uids of blocks that merely repeat a running header/footer already known for this document."""
    known = set(doc.repeat_heads or [])
    out = []
    for b in doc.blocks:
        if not b.ocr:
            continue
        ys = [r[2] for r in b.regions]; ye = [r[4] for r in b.regions]
        edge = bool(ys) and (min(ys) < 0.10 or max(ye) > 0.90)
        if edge and _norm_head(b.text) in known:
            out.append(b.uid)
    return out
def build_inputs(wa, wb, links):
    ka = [b for b in wa.blocks if not b.ignored]; kb = [b for b in wb.blocks if not b.ignored]
    ua = {b.uid: i for i, b in enumerate(ka)}; ub = {b.uid: i for i, b in enumerate(kb)}
    anchors = []
    for la, lb in links:
        ia = [ua[u] for u in la if u in ua]; ib = [ub[u] for u in lb if u in ub]
        if ia and ib: anchors.append((min(ia), max(ia) + 1, min(ib), max(ib) + 1))
    da = replace(wa, blocks=[copy.copy(b) for b in ka]); db = replace(wb, blocks=[copy.copy(b) for b in kb])
    _reindex(da); _reindex(db); return da, db, anchors
def save_session(path, wa, wb, links, options=None):
    import pickle
    with open(path, "wb") as f: pickle.dump((wa, wb, links, options), f)
    return path
def load_session(path):
    import pickle
    with open(path, "rb") as f: data = pickle.load(f)
    a, b, l = data[:3]
    return a, b, l, (data[3] if len(data) > 3 else None)
