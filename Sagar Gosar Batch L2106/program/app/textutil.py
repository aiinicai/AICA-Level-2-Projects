"""Text helpers: cleaning, label splitting, tokenisation, Indian-number parsing, stamp detection."""
import re
import unicodedata

_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "−": "-", " ": " ",
           "​": "", "­": "", "﻿": "", "•": "*", "": "*"}


def clean_text(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = "".join(_QUOTES.get(c, c) for c in s)
    return " ".join(s.split())


_LABEL_RE = re.compile(r"""^(
    (?:clause|article|section|schedule|annexure|annex|appendix|exhibit)\s+[0-9IVXLivxl]+[A-Za-z]?[.:)]?
  | \d{1,3}(?:\.\d{1,3}){1,4}[.)]? | \d{1,3}[.)]
  | \(\s*(?:[a-z]{1,3}|[ivxl]{1,6}|\d{1,2})\s*\)
  | [a-z][.)]
  | [IVXL]{1,6}[.)]
  | \*
)(?=\s+\S)""", re.X | re.I)


def split_label(text):
    """Return (label, body).  A label is an outline number such as '1.', '4.2', '(a)', '(iii)'."""
    t = text.strip()
    m = _LABEL_RE.match(t)
    if not m:
        return "", t
    lab = m.group(1).strip()
    body = t[m.end():].strip()
    if re.fullmatch(r"[a-z][.)]", lab):          # "a." / "b)" at the start of ordinary prose
        return "", t
    if lab == "*":
        return "", body
    return lab, body


_EQUIV = {"&": "and", "pvt": "private", "ltd": "limited", "co": "company", "inc": "incorporated", "corp": "corporation", "rs": "rs",
          "inr": "rs", "₹": "rs", "no": "no", "nos": "no", "dt": "dated", "w.e.f": "wef", "approx": "approximately", "st": "st"}
_WORD_STRIP = re.compile(r"[^\w₹%]+", re.U)
_NUM_RE = re.compile(r"^\(?\d[\d,]*(?:\.\d+)?\)?[/-]*$")


_BLANK = re.compile(r"^[\(\[]?(?:_{3,}|\.{4,}|\u2026+|-{4,})[\)\]]?[.,;:]?$")


def is_blank(w):
    return bool(_BLANK.match(w.strip()))


def token_key(word, ignore_case=True, compare_punct=False):
    w = word
    if is_blank(w):
        return "<blank>"
    if compare_punct:
        return w.lower() if ignore_case else w
    w = w.strip()
    if _NUM_RE.match(w):
        k = re.sub(r"[(),/\-]", "", w)
        k = k.rstrip(".")
        return k
    k = _WORD_STRIP.sub("", w.lower() if ignore_case else w)
    if k.lower() in _EQUIV:
        k = _EQUIV[k.lower()]
    return k


def words_of(text):
    return text.split()


NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
             "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45,
             "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100, "twenty-four": 24, "thirty-six": 36}
_MULT = {"thousand": 1e3, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "crore": 1e7, "crores": 1e7, "cr": 1e7, "million": 1e6,
         "mn": 1e6, "billion": 1e9, "bn": 1e9}
_CUR = {"rs", "rs.", "inr", "₹", "usd", "$", "eur", "€", "rupees", "rupee"}


def parse_number(tok):
    t = tok.strip().strip("()/-").rstrip(".,;:")
    t = t.replace(",", "")
    t = re.sub(r"^(rs\.?|inr|₹|\$|usd)", "", t, flags=re.I)
    try:
        return float(t)
    except ValueError:
        return None


def parse_amounts(words):
    """Amounts (with Indian multipliers) found in a list of words -> list of floats."""
    out = []
    n = len(words)
    for i, w in enumerate(words):
        lw = w.lower().strip(",;:()")
        if not re.search(r"\d", w):
            continue
        v = parse_number(w)
        if v is None:
            continue
        m = 1.0
        if i + 1 < n:
            nxt = words[i + 1].lower().strip(".,;:()/-")
            if nxt in _MULT:
                m = _MULT[nxt]
        out.append(v * m)
    return out


def fmt_inr(v):
    neg = v < 0
    v = abs(v)
    whole, _, frac = f"{v:.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    s = whole + ("" if frac == "00" else "." + frac)
    return ("-" if neg else "") + s


# ---------------------------------------------------------------- stamps / registration noise
_STAMP_KW = ["e-stamp", "estamp", "non judicial", "non-judicial", "certificate no", "certificate issued", "stamp duty", "unique doc",
             "account reference", "purchased by", "description of document", "property description", "consideration price",
             "first party", "second party", "statutory alert", "sub-registrar", "subregistrar", "sub registrar", "registrar",
             "government of", "shcil", "stock holding", "grn", "challan", "franking", "franked", "treasury", "registered at",
             "presented for registration", "endorsement", "book 1", "document no", "thumb impression", "e-registration", "scanned",
             "stamp paper", "stamp vendor", "licence no", "license no", "vendor", "denomination", "rupees only", "government of india",
             "india non", "issued by", "registration fee", "receipt no", "date & time", "date and time of issuance",
             "authorised signatory of stamp", "not valid without", "verify", "barcode", "qr code"]


def stamp_score(text):
    t = text.lower()
    hits = sum(1 for k in _STAMP_KW if k in t)
    return hits


def looks_like_stamp(text, draft_sim=0.0):
    t = text.strip()
    if not t:
        return True
    alnum = sum(c.isalnum() for c in t)
    if alnum < 0.45 * len(t):
        return True
    hits = stamp_score(t)
    nw = len(t.split())
    if hits >= 2 or (hits >= 1 and nw <= 18):
        return draft_sim < 0.40
    return False
