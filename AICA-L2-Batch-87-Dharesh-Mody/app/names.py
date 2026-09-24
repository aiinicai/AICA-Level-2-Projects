"""
Company-name normalisation and matching.

Different IPO websites write the same company differently:

    National Stock Exchange of India Limited   (exchange / prospectus)
    NSE                                        (GMP site, abbreviation)
    NSE India Ltd IPO                          (GMP site, extra words)
    Vikran Engineering Limited                 (exchange)
    Vikran Engg Ltd (SME) IPO GMP              (GMP site)
    Shree Ahimsa Naturals  /  Shri Ahimsa Naturals Pvt. Ltd.

Comparing raw strings (or even simple slugs) therefore fails, and a GMP quote
that exists on a source is reported as "no quote published" or is dropped
entirely. This module reduces every name to a comparable list of *core*
tokens and scores how confidently two names refer to the same company.

Scoring tiers (higher = more certain; 0 = not the same company):

    100  identical core tokens        ("Xyz Limited" / "XYZ IPO" / "Xyz (India) Ltd.")
     95  identical once spaces go     ("Sri Lotus" / "Srilotus", "L&T Finance" / "LT Finance")
     85  one name is the leading part of the other, >= 2 distinctive words
     80  same core once soft descriptor words are ignored
         ("Orient Technologies Limited" / "Orient Tech", "Xyz Corp" / "Xyz Corporation")
     70  abbreviation / initialism    ("NSE" / "National Stock Exchange of India Limited",
                                       "NSDL", "L&T", "SBI", "LIC", "ONGC")
     50  near-identical spelling (typos only; opt-in via allow_typos=True)

Users can add their own equivalences in ``name_aliases.json`` (see
``load_aliases``) for the rare case that none of the rules catch.
"""
import html
import json
import os
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache

# Words that carry no identity and are dropped wherever they appear.
STOP_WORDS = {"of", "the", "and", "for", "a", "an"}
LEGAL_NOISE = {
    "limited", "ltd", "private", "pvt", "public", "plc", "llp", "inc",
    "incorporated",
}
IPO_NOISE = {"ipo", "fpo", "gmp"}
GEO_NOISE = {"india"}
# Board / exchange tags that sites append: only stripped from the *end*, so a
# company literally called "NSE" or "BSE" still keeps its own name.
EXCHANGE_TAIL = {"sme", "mainboard", "main", "board", "emerge", "platform", "nse", "bse"}
# InvestorGain glues a status letter onto the tag: IPOO (open), IPOC (closed),
# IPOU (upcoming), IPOL (listed), IPOCT (closing today); likewise SMEC, SMEO...
_IPO_TAG = re.compile(r"(?:ipo|fpo)(?:o|c|u|l|ct)?")
_SME_TAG = re.compile(r"sme(?:o|c|u|l|ct)?")
# "Xyz Industries (formerly known as Abc Traders)": ignore everything after.
CUT_MARKERS = {"formerly", "fka", "erstwhile", "previously"}

# Spelling / abbreviation variants collapsed to one canonical token.
# (Applied to the token itself first, then to its de-pluralised form.)
ABBREVIATIONS = {
    "tech": "technology", "technologies": "technology",
    "corp": "corporation", "co": "company",
    "engg": "engineering", "engr": "engineering",
    "infra": "infrastructure",
    "ind": "industry", "inds": "industry", "industries": "industry",
    "intl": "international", "svc": "service", "svcs": "service",
    "mfg": "manufacturing", "pharma": "pharmaceutical",
    "lab": "laboratory", "labs": "laboratory", "laboratories": "laboratory",
    "sys": "system", "chem": "chemical", "constr": "construction",
    "hldg": "holding", "hldgs": "holding", "soln": "solution", "solns": "solution",
    "shree": "shri", "sri": "shri", "sree": "shri", "shrii": "shri",
}

# Descriptor words that rarely distinguish one company from another.
SOFT_WORDS = {
    "industry", "enterprise", "technology", "solution", "corporation",
    "company", "holding", "group", "service", "international", "global",
    "system", "venture",
}

# Very common first-words: two names sharing only these must not be merged.
GENERIC_WORDS = {
    "shri", "om", "sai", "new", "national", "bharat", "global", "royal", "star",
    "united", "universal", "modern", "classic", "prime", "sun", "ganesh", "shiv",
    "laxmi", "lakshmi", "krishna", "ram", "gold", "golden", "silver", "diamond",
    "indian", "first", "one", "super", "digital", "smart", "pioneer", "eco",
    "mahalaxmi", "balaji", "jai", "ma", "gujarat", "maharashtra", "delhi",
    "mumbai", "south", "north", "east", "west", "central", "general", "standard",
    "premier", "supreme", "victory", "vision", "zenith", "alpha", "omega",
}

# Optional user file, set by db.py once the data folder is known.
ALIAS_FILE = None
_alias_cache = {"mtime": None, "path": None, "map": {}}


def _stem(token):
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us")):
        return token[:-1]
    return token


def _canonical(token):
    if token in ABBREVIATIONS:
        return ABBREVIATIONS[token]
    stem = _stem(token)
    return ABBREVIATIONS.get(stem, stem)


def _raw_tokens(name):
    s = html.unescape(re.sub(r"<[^>]+>", " ", str(name or "")))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[\u2019'`]", "", s)
    # "S.M. Foods" -> "sm foods"
    s = re.sub(r"\b(?:[a-z]\.){2,}", lambda m: m.group(0).replace(".", ""), s)
    return re.sub(r"[^a-z0-9]+", " ", s).split()


def _normalise(name):
    """Return (core_tokens tuple, joined_single_letters flag)."""
    return _normalise_cached(name, _alias_version())


@lru_cache(maxsize=8192)
def _normalise_cached(name, _alias_version_key):
    raw = _raw_tokens(name)
    for i, t in enumerate(raw):
        if i >= 1 and t in CUT_MARKERS:
            raw = raw[:i]
            break
    # "Xyz IPO Date, Price Band, Review" / "Xyz IPOC" -> "Xyz"
    for i, t in enumerate(raw):
        if i >= 1 and _IPO_TAG.fullmatch(t):
            raw = raw[:i]
            break
    noise = LEGAL_NOISE | IPO_NOISE | GEO_NOISE | STOP_WORDS
    tokens = [t for t in raw if t not in noise and not _IPO_TAG.fullmatch(t)]
    while len(tokens) > 1 and (tokens[-1] in EXCHANGE_TAIL or _SME_TAG.fullmatch(tokens[-1])):
        tokens.pop()
    if not tokens:  # name was nothing but noise: keep what identity there is
        tokens = [t for t in raw if t not in STOP_WORDS] or ["ipo"]
    joined = False
    if len(tokens) > 1 and all(len(t) == 1 for t in tokens):  # "L&T" -> "lt"
        tokens, joined = ["".join(tokens)], True
    tokens = tuple(_canonical(t) for t in tokens)
    alias = _load_aliases(_alias_version_key).get(" ".join(tokens))
    if alias:
        tokens, joined = alias, False
    return tokens, joined


def name_tokens(name):
    return list(_normalise(name)[0])


def name_key(name):
    """Stable comparison key (like db.slugify, but alias/abbreviation aware)."""
    return "-".join(_normalise(name)[0])


# ---------------------------------------------------------------- aliases --

def _alias_version():
    """Modification time of name_aliases.json (None if absent) - part of the cache key."""
    try:
        return os.path.getmtime(ALIAS_FILE) if ALIAS_FILE and os.path.isfile(ALIAS_FILE) else None
    except OSError:
        return None


def load_aliases():
    """Read the optional ``name_aliases.json`` from the data folder.

    Format: {"Canonical Company Name": ["Other spelling", "ABBR", ...], ...}
    Returns {normalised variant: canonical core tokens}.
    """
    return dict(_load_aliases(_alias_version()))


def _load_aliases(version):
    if version is None:
        return {}
    if _alias_cache["path"] == ALIAS_FILE and _alias_cache["mtime"] == version:
        return _alias_cache["map"]
    mapping = {}
    try:
        with open(ALIAS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
        for canonical, variants in (data or {}).items():
            variants = [variants] if isinstance(variants, str) else list(variants or [])
            target = tuple(_canonical(t) for t in _bare_tokens(canonical))
            for variant in variants:
                key = " ".join(_canonical(t) for t in _bare_tokens(variant))
                if key and target:
                    mapping[key] = target
    except Exception:
        mapping = {}
    _alias_cache.update(mtime=version, path=ALIAS_FILE, map=mapping)
    return mapping


def _bare_tokens(name):
    noise = LEGAL_NOISE | IPO_NOISE | GEO_NOISE | STOP_WORDS
    tokens = [t for t in _raw_tokens(name) if t not in noise]
    return tokens or _raw_tokens(name)


# --------------------------------------------------------------- matching --

def _compact(tokens):
    """Tokens run together, with Shri/Shree/Sri/Sree fused-prefix spellings unified."""
    return re.sub(r"^(?:shree|sree|shri|sri)(?=.)", "shri", "".join(tokens))


def _soft_split(tokens):
    core = tuple(t for t in tokens if t not in SOFT_WORDS) or tuple(tokens)
    soft = frozenset(t for t in tokens if t in SOFT_WORDS)
    return core, soft


def _distinctive(core):
    if all(t in GENERIC_WORDS for t in core):
        return False
    return len(core) >= 2 or len(core[0]) >= 4


def _initialisms(tokens):
    base = "".join(t[0] for t in tokens if t)
    # Sites often keep the dropped words' initials: NSDL (Limited), SBI (India).
    return {base, base + "l", base + "i", base + "il"}


def match_score(a, b, allow_typos=False):
    """0 if the names are not the same company, else a tier score (see module doc)."""
    (ta, ja), (tb, jb) = _normalise(a), _normalise(b)
    if not ta or not tb:
        return 0
    if ta == tb:
        return 100
    ka, kb = _compact(ta), _compact(tb)
    if ka == kb:
        return 95
    shorter, longer = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if len(shorter) >= 2 and longer[:len(shorter)] == shorter and _distinctive(shorter):
        return 85
    ca, sa = _soft_split(ta)
    cb, sb = _soft_split(tb)
    if ca == cb and (sa <= sb or sb <= sa) and _distinctive(ca):
        return 80
    # Abbreviations: one side is a single short token, the other spells it out.
    for (acr, joined), full in (((ta, ja), tb), ((tb, jb), ta)):
        if len(acr) == 1 and len(full) >= 2 and acr[0].isalpha() and len(acr[0]) <= 7 \
                and (len(acr[0]) >= 3 or joined) and acr[0] in _initialisms(full):
            return 70
    if allow_typos and min(len(ka), len(kb)) >= 12 \
            and re.findall(r"\d+", ka) == re.findall(r"\d+", kb) \
            and SequenceMatcher(None, ka, kb).ratio() >= 0.95:
        return 50
    return 0


def names_match(a, b, allow_typos=False):
    return match_score(a, b, allow_typos) > 0


def rank_matches(name, items, get_name=lambda x: x, allow_typos=True):
    """Items whose name matches `name`, best match first (stable)."""
    scored = []
    for item in items:
        score = match_score(get_name(item), name, allow_typos)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: -pair[0])
    return [item for _, item in scored]
