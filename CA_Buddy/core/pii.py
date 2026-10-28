"""Detection and reversible masking of personal / identifying details in
Indian tax notices. Nothing here talks to the network."""
from __future__ import annotations

import re
from collections import OrderedDict

# ------------------------------------------------------------ validators

GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

STATES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra",
    "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman and Nicobar Islands", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh", "97": "Other Territory", "99": "Centre Jurisdiction",
}

PAN_HOLDER = {
    "P": "an individual", "C": "a company", "H": "a HUF", "F": "a firm / LLP",
    "A": "an AOP", "T": "a trust", "B": "a BOI", "L": "a local authority",
    "J": "an artificial juridical person", "G": "a government body", "K": "Krish (non-standard)",
}


def gstin_checksum_ok(g: str) -> bool:
    total = 0
    for i, ch in enumerate(g[:14]):
        v = GSTIN_CHARS.index(ch) * (2 if i % 2 else 1)
        total += v // 36 + v % 36
    return GSTIN_CHARS[(36 - total % 36) % 36] == g[14]


_V_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_V_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]


def verhoeff_ok(num: str) -> bool:
    c = 0
    for i, d in enumerate(reversed(num)):
        c = _V_D[c][_V_P[i % 8][int(d)]]
    return c == 0


# ------------------------------------------------------------ categories

CATEGORIES = OrderedDict([
    # key: (label, token prefix, on by default)
    ("name", ("Person / business name", "NAME", True)),
    ("gstin", ("GSTIN", "GSTIN", True)),
    ("pan", ("PAN", "PAN", True)),
    ("aadhaar", ("Aadhaar", "AADHAAR", True)),
    ("tan", ("TAN", "TAN", True)),
    ("cin", ("CIN / LLPIN", "CIN", True)),
    ("address", ("Address", "ADDRESS", True)),
    ("pincode", ("PIN code", "PIN", True)),
    ("phone", ("Phone", "PHONE", True)),
    ("email", ("Email", "EMAIL", True)),
    ("bank", ("Bank account", "BANKAC", True)),
    ("ifsc", ("IFSC", "IFSC", True)),
    ("reference", ("Notice ref / DIN", "REF", False)),
    ("custom", ("Added by you", "MASK", True)),
])

NAME_STOP = {
    "sir", "madam", "sir/madam", "the", "taxpayer", "assessee", "proper officer", "na", "n/a",
    "nil", "dear", "notice", "to", "you", "registered person", "applicant", "officer",
    "superintendent", "assistant commissioner", "deputy commissioner", "income tax officer",
    "assessing officer", "national faceless assessment centre", "goods and services tax",
}

NAME_LABELS = (
    r"Legal\s+Name(?:\s+of\s+(?:the\s+)?(?:Business|Taxpayer|Registered\s+Person))?",
    r"Trade\s+Name", r"Name\s+of\s+(?:the\s+)?(?:Taxpayer|Assessee|Registered\s+Person|Business|"
    r"Person|Applicant|Company|Firm|Proprietor|Partner|Director|Authori[sz]ed\s+Signatory)",
    r"Taxpayer'?s?\s+Name", r"Assessee'?s?\s+Name", r"Name\s+of\s+Assessee",
    r"Authori[sz]ed\s+Signatory", r"Proprietor", r"(?<![A-Za-z ])Name",
)

ENTITY_SUFFIX = (r"(?:(?i:Private\s+Limited|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?|LLP|OPC)|Industries|Enterprises|"
                 r"Traders|Associates|Constructions?|Infra(?:structure)?|Technologies|Solutions|"
                 r"& Co\.?|and Company|Corporation|Agencies|INDUSTRIES|ENTERPRISES|TRADERS|"
                 r"ASSOCIATES|CONSTRUCTIONS?|TECHNOLOGIES|SOLUTIONS|CORPORATION|AGENCIES)")
STRONG_SUFFIX = r"(?i:\s+(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?|LLP|OPC))\s*$"

# words too common to treat as identifying on their own
COMMON_WORDS = {
    "private", "limited", "pvt", "ltd", "llp", "company", "india", "indian", "technology", "technologies",
    "infra", "infrastructure", "projects", "project", "solutions", "services", "industries", "enterprises",
    "traders", "trading", "associates", "construction", "constructions", "engineering", "group", "global",
    "international", "systems", "software", "the", "and", "sri", "shri", "smt", "road", "street", "nagar",
    "main", "cross", "floor", "building", "salai", "tamil", "nadu", "state", "district", "east", "west",
    "north", "south", "new", "old", "first", "second", "third", "corporation", "agencies", "power",
}


HONORIFIC = r"(?:Shri|Smt|Sri|Sh|Mr|Mrs|Ms|Kum|Dr|Thiru|Tmt|Selvi)\.?\s+"
LABEL_WORDS = r"(?:Email|E-mail|Mobile|Mob|Phone|Ph|Tel|GSTIN|PAN|Address|Date|DIN|Designation|Ref)\b"


def _clean_name(v: str) -> str:
    v = re.split(rf"\s+{LABEL_WORDS}", v)[0]
    v = re.split(r"\s{3,}|\t|\s+(?:GSTIN|PAN|Address|Date|Ref|DIN|having|bearing|with)\b", v)[0]
    v = v.strip(" .,:;-–()[]\"'")
    v = re.sub(r"\s+", " ", v)
    if not re.match(r"(?i)sri\s+\w+\s+\w+", v):  # 'Sri Lakshmi Traders' is a name, 'Sri X' a title
        v = re.sub(rf"^{HONORIFIC}", "", v)
    else:
        v = re.sub(rf"^(?:Shri|Smt|Sh|Mr|Mrs|Ms|Kum|Dr|Thiru|Tmt|Selvi)\.?\s+", "", v)
    return v


def _plausible_name(v: str) -> bool:
    if len(v) < 3 or len(v) > 90:
        return False
    if v.lower() in NAME_STOP or not re.search(r"[A-Za-z]{2}", v):
        return False
    if re.fullmatch(r"[\d\W]+", v):
        return False
    if len(v.split()) > 9:
        return False
    return True


# ------------------------------------------------------------ detection

def _add(found: dict, cat: str, value: str, note: str = "") -> None:
    value = value.strip()
    if not value:
        return
    key = (cat, re.sub(r"\s+", " ", value).lower())
    if key not in found:
        found[key] = {"category": cat, "value": value, "note": note}


def detect(text: str) -> list[dict]:
    found: dict = OrderedDict()
    T = text

    for m in re.finditer(r"\b(\d{2})([A-Z]{5}\d{4}[A-Z])([1-9A-Z])Z([0-9A-Z])\b", T):
        g = m.group(0)
        state = STATES.get(m.group(1), "unknown state")
        ok = gstin_checksum_ok(g)
        note = f"registered in {state} (state code {m.group(1)})"
        if not ok:
            note += "; checksum doesn't match, possibly mistyped/OCR"
        _add(found, "gstin", g, note)

    gstin_pans = {m.group(1) for m in re.finditer(r"\b\d{2}([A-Z]{5}\d{4}[A-Z])[1-9A-Z]Z[0-9A-Z]\b", T)}
    for m in re.finditer(r"(?<![A-Z0-9])([A-Z]{3}([ABCFGHLJPTK])[A-Z]\d{4}[A-Z])(?![A-Z0-9])", T):
        holder = PAN_HOLDER.get(m.group(2), "")
        note = f"PAN of {holder}" if holder else ""
        if m.group(1) in gstin_pans:
            note += "; same PAN as in a GSTIN"
        _add(found, "pan", m.group(1), note)

    for m in re.finditer(r"(?<!\d)([2-9]\d{3})[ -]?(\d{4})[ -]?(\d{4})(?!\d)", T):
        digits = "".join(m.groups())
        if verhoeff_ok(digits):
            _add(found, "aadhaar", m.group(0))

    for m in re.finditer(r"(?<![A-Z0-9])[A-Z]{4}\d{5}[A-Z](?![A-Z0-9])", T):
        _add(found, "tan", m.group(0))

    for m in re.finditer(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b|\b[A-Z]{3}-\d{4}\b", T):
        if re.match(r"[A-Z]{3}-\d{4}$", m.group(0)) and not re.search(r"LLP", T[max(0, m.start() - 40):m.start()], re.I):
            continue
        _add(found, "cin", m.group(0))

    for m in re.finditer(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", T):
        _add(found, "ifsc", m.group(0))

    for m in re.finditer(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", T):
        _add(found, "email", m.group(0))

    for m in re.finditer(r"(?<![\d/])(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?![\d/])", T):
        _add(found, "phone", m.group(0))
    for m in re.finditer(r"(?:Ph(?:one)?|Tel|Mob(?:ile)?|Contact)\.?\s*(?:No\.?)?\s*[:\-]?\s*((?:\+91[\s-]?)?[\d][\d\s-]{6,14}\d)", T, re.I):
        _add(found, "phone", m.group(1))

    for m in re.finditer(r"(?:A/?c|Account)\.?\s*(?:No\.?|Number)?\s*[:\-]?\s*(\d[\d ]{7,20}\d)", T, re.I):
        _add(found, "bank", m.group(1))

    for m in re.finditer(r"(?:\bDIN\b(?:\s*(?:&|and)\s*Notice\s+No)?|Notice\s+No|Reference\s+No|Ref\.?\s*No|\bARN\b|Document\s+Identification\s+Number)"
                         r"\.?\s*[:\-]?\s*([A-Z0-9][A-Z0-9/\-.]{7,45})", T, re.I):
        v = m.group(1).rstrip(".-/")
        if re.search(r"\d", v):
            _add(found, "reference", v)

    # --- names
    label_re = "|".join(NAME_LABELS)
    for m in re.finditer(rf"(?im)^[ \t]*(?:\d+[.)]\s*)?(?:{label_re})\s*[:\-–]\s*(.+)$", T):
        v = _clean_name(m.group(1))
        if _plausible_name(v):
            _add(found, "name", v)
    for m in re.finditer(r"\bM/[Ss]\.?\s*([A-Z0-9][A-Za-z0-9&.'\- ]{2,70}?)(?=\s*(?:,|\n|\(|;|$|\s{2,}|\bGSTIN|\bhaving|\bbearing|\bPAN))", T):
        v = _clean_name(m.group(1))
        if _plausible_name(v):
            _add(found, "name", v)
    for m in re.finditer(r"\b(?:Shri|Smt|Sh|Mr|Mrs|Ms|Kum|Dr|Thiru|Tmt|Selvi)\.?[ \t]+((?:[A-Z][A-Za-z]*\.?[ \t]?){1,4})", T):
        v = _clean_name(m.group(1))
        if _plausible_name(v) and len(v) > 3:
            _add(found, "name", v)
    for m in re.finditer(rf"\b((?:[A-Z][A-Za-z0-9&.'\-]*\s+){{1,6}}{ENTITY_SUFFIX})(?![A-Za-z])", T):
        v = _clean_name(m.group(1))
        if _plausible_name(v) and not re.match(r"(?i)(the|of|to|by|for|in)\b", v):
            _add(found, "name", v)

    # --- addresses (label then rest of line + continuation lines)
    for m in re.finditer(r"(?im)^[ \t]*(?:\d+[.)]\s*)?(?:Address(?:\s+of\s+(?:the\s+)?[A-Za-z ]+)?|"
                         r"Principal\s+Place\s+of\s+Business|Registered\s+Office|Place\s+of\s+Business)"
                         r"\s*[:\-–]\s*(.+(?:\n\n?(?![^\n]*:)[^\n]{3,}){0,3})", T):
        block = m.group(1)
        lines = []
        for ln in block.splitlines():
            ln = ln.strip()
            if not ln or re.match(r"(?i)(sub(ject)?|ref|date|din|gstin|pan|dear|sir|madam|notice)\b", ln):
                break
            lines.append(ln)
        v = "\n".join(lines).strip(" ,.")
        if len(v) >= 8:
            _add(found, "address", v)
    for name, addr in _to_blocks(T):
        if name and _plausible_name(name):
            _add(found, "name", name)
        if addr:
            _add(found, "address", addr)
    # PIN right after a town name: "CHENNAI 600008", "Vellore-632007"
    for m in re.finditer(r"(?<![\w₹.])([A-Za-z]{3,})[ \t]*[-–,]?[ \t]*([1-9]\d{2}\s?\d{3})(?![\d,.])", T):
        if m.group(1).lower() not in ("rs", "inr", "no", "section", "sec", "rule", "year", "amount", "rupees", "of", "is", "pay", "total", "tax", "din", "arn"):
            _add(found, "pincode", m.group(2))
    for m in re.finditer(r"(?i)(?:PIN(?:\s*code)?\s*[:\-]?\s*|[-–,]\s*)([1-9]\d{2}\s?\d{3})(?!\d)", T):
        if not re.search(r"\d", T[max(0, m.start() - 1):m.start()]):
            _add(found, "pincode", m.group(1))

    items = _drop_contained(list(found.values()), T)
    counters: dict[str, int] = {}
    name_tokens: dict[str, str] = {}
    out = []
    for it in sorted(items, key=lambda x: list(CATEGORIES).index(x["category"])):
        cat = it["category"]
        label, prefix, default_on = CATEGORIES[cat]
        it.update(label=label, enabled=default_on, count=count_occurrences(T, it["value"]))
        if not it["count"]:
            continue
        core = None
        if cat == "name":  # 'LNV TECHNOLOGY PVT LTD' and 'LNV Technology Private Limited' are one party
            core = re.sub(r"[^a-z0-9]", "", re.sub(STRONG_SUFFIX, "", it["value"]).lower())
        if core and core in name_tokens:
            it.update(token=name_tokens[core], variant_of=name_tokens[core],
                      note=it.get("note") or "another spelling of the same name")
        else:
            counters[cat] = counters.get(cat, 0) + 1
            it["token"] = f"[{prefix}_{counters[cat]}]"
            if core:
                name_tokens[core] = it["token"]
        out.append(it)
    out = _add_name_variants(out, T)
    for i, it in enumerate(out):
        it["id"] = f"d{i}"
    return out


BLOCK_STOP = re.compile(r"(?i)^(?:sub(?:ject)?\b|ref\b|date[d]?\b|din\b|gstin\b|pan\b|a\.?y\.?\b|dear\b|sir\b|madam\b|"
                        r"notice\b|whereas\b|please\b|kindly\b|you\b|with reference\b|in the matter\b)")


def _to_blocks(T: str) -> list[tuple[str, str]]:
    """The addressee block after 'To,' - first line is the name, the rest the address."""
    out = []
    for m in re.finditer(r"(?im)^[ \t]*To[,:]?[ \t]*$\n?", T):
        lines = []
        blank = 0
        for raw in T[m.end():].splitlines():
            ln = raw.strip()
            if not ln:
                blank += 1
                if lines and blank >= 1:
                    break
                continue
            blank = 0
            if BLOCK_STOP.match(ln) or (":" in ln and not re.search(r"\d:\d", ln)) or len(lines) >= 9:
                break
            lines.append(ln)
        if not lines:
            continue
        first = re.sub(r"^M/[Ss]\.?\s*", "", lines[0]).strip(" ,.")
        if re.match(r"(?i)(the\s+)?(proper officer|assistant|deputy|joint|additional|commissioner|superintendent|"
                    r"income tax officer|assessing officer|principal|chief|state tax officer)", first):
            continue  # addressed to an officer, not the taxpayer
        addr = "\n".join(lines[1:]).strip(" ,.")
        out.append((_clean_name(first), addr if len(addr) >= 8 else ""))
    return out


def _add_name_variants(items: list[dict], text: str) -> list[dict]:
    """'LNV TECHNOLOGY PVT LTD' also appears as 'LNV Technology Private Limited' or just 'LNV'.
    Variants share the same token so they unmask to the main name."""
    extra = []
    have = {i["value"].lower() for i in items}
    for it in [i for i in items if i["category"] == "name"]:
        core = re.sub(STRONG_SUFFIX, "", it["value"]).strip(" ,.")
        if core == it["value"]:
            continue
        cands = [core] if len(core) >= 4 and core.lower() not in COMMON_WORDS else []
        first = core.split()[0] if core.split() else ""
        if (len(first) >= 3 and first.lower() not in COMMON_WORDS and not first.isdigit()
                and len(core.split()) > 1):
            cands.append(first)
        for c in cands:
            if c.lower() in have:
                continue
            if count_occurrences(text, c) > count_occurrences(text, it["value"]):
                have.add(c.lower())
                extra.append({"category": "name", "value": c, "note": f"short form of {it['value']}",
                              "token": it["token"], "label": it["label"], "enabled": True,
                              "count": count_occurrences(text, c), "variant_of": it["token"]})
    return items + extra


def _drop_contained(items: list[dict], text: str) -> list[dict]:
    """Drop a name that is just part of another detected name; keep identifiers."""
    names = [i for i in items if i["category"] == "name"]
    keep = []
    for it in items:
        if it["category"] == "name":
            v = it["value"].lower()
            containers = [o for o in names if v != o["value"].lower() and v in o["value"].lower()]
            if containers and count_occurrences(text, it["value"]) <= sum(
                    count_occurrences(text, o["value"]) for o in containers):
                continue  # only ever appears inside a longer detected name
        keep.append(it)
    return keep


# ------------------------------------------------------------ masking

def _pattern(value: str) -> str:
    parts = [re.escape(p) for p in re.split(r"\s+", value.strip()) if p]
    body = r"[\s,]*\s+".join(parts) if len(parts) > 1 else parts[0]
    # don't match inside a longer word/number
    lead = r"(?<![A-Za-z0-9])" if re.match(r"[A-Za-z0-9]", value.strip()) else ""
    tail = r"(?![A-Za-z0-9])" if re.search(r"[A-Za-z0-9]$", value.strip()) else ""
    return lead + body + tail


def count_occurrences(text: str, value: str) -> int:
    if not value.strip():
        return 0
    return len(re.findall(_pattern(value), text, flags=re.I))


def next_token(items: list[dict], category: str) -> str:
    prefix = CATEGORIES[category][1]
    nums = [int(m.group(1)) for it in items
            for m in [re.fullmatch(rf"\[{prefix}_(\d+)\]", it["token"])] if m]
    return f"[{prefix}_{max(nums, default=0) + 1}]"


def apply_mask(text: str, items: list[dict]) -> str:
    active = sorted((i for i in items if i.get("enabled")), key=lambda i: -len(i["value"]))
    if not active:
        return text
    lookup = {}
    alts = []
    for i, it in enumerate(active):
        alts.append(f"(?P<g{i}>{_pattern(it['value'])})")
        lookup[f"g{i}"] = it["token"]
    rx = re.compile("|".join(alts), re.I)
    return rx.sub(lambda m: lookup[m.lastgroup], text)


def mask_spans(text: str, items: list[dict]) -> list[tuple[int, int, str]]:
    """Positions of each masked value in the ORIGINAL text (for preview highlighting)."""
    active = sorted((i for i in items if i.get("enabled")), key=lambda i: -len(i["value"]))
    if not active:
        return []
    alts, lookup = [], {}
    for i, it in enumerate(active):
        alts.append(f"(?P<g{i}>{_pattern(it['value'])})")
        lookup[f"g{i}"] = it["token"]
    rx = re.compile("|".join(alts), re.I)
    return [(m.start(), m.end(), lookup[m.lastgroup]) for m in rx.finditer(text)]


def unmask(text: str, items: list[dict]) -> str:
    mapping = {}
    for it in items:
        if it.get("enabled") and not it.get("variant_of"):
            mapping.setdefault(it["token"].strip("[]"), it["value"])
    for it in items:
        if it.get("enabled"):
            mapping.setdefault(it["token"].strip("[]"), it["value"])
    if not mapping:
        return text
    keys = sorted(mapping, key=len, reverse=True)
    rx = re.compile(r"\[?\b(" + "|".join(re.escape(k) for k in keys) + r")\b\]?")

    def rep(m):
        val = mapping[m.group(1)]
        return re.sub(r",?\s*\n\s*", ", ", val)

    return rx.sub(rep, text)


def context_notes(items: list[dict]) -> list[str]:
    """Non-identifying hints about masked tokens that help the model reason."""
    notes = []
    for it in items:
        if it.get("enabled") and it.get("note") and it["category"] in ("gstin", "pan"):
            notes.append(f"{it['token']}: {it['note']}")
    return notes


def leak_check(masked: str, items: list[dict]) -> list[dict]:
    """A stricter second pass over the text that is about to be sent.
    Returns anything that still looks identifying and that the user hasn't
    deliberately left visible."""
    visible = {re.sub(r"\s+", " ", i["value"]).lower() for i in items if not i.get("enabled")}
    findings, seen = [], set()

    def add(value, reason):
        key = re.sub(r"\s+", " ", value).lower()
        if key in seen or key in visible or not value.strip():
            return
        seen.add(key)
        findings.append({"value": value.strip(), "reason": reason, "count": count_occurrences(masked, value)})

    token_only = re.compile(r"^[\s\[\]A-Z_\d,.;:-]*$")
    for it in detect(masked):
        if it["category"] == "reference" or re.search(r"\[?\b[A-Z]+_\d+\b\]?", it["value"]) and token_only.match(it["value"]):
            continue
        add(it["value"], f"looks like {it['label'].lower()}")
    # pieces of masked names that still appear on their own ("LNV", "LNV's")
    for it in items:
        if not it.get("enabled") or it["category"] not in ("name", "custom", "address"):
            continue
        for w in re.findall(r"[A-Za-z][A-Za-z0-9&]{2,}", it["value"]):
            if w.lower() in COMMON_WORDS or len(w) < 3 or (it["category"] == "address" and len(w) < 5):
                continue
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(w)}(?![A-Za-z0-9])", masked, re.I):
                add(w, f"part of masked {it['label'].lower()} {it['token']}")
    # numbers that look like account / phone numbers
    for m in re.finditer(r"(?<![\d,./\-A-Za-z])\d{9,18}(?![\d,./\-(A-Za-z])", masked):
        add(m.group(0), "long number, could be an account or phone number")
    return findings
