"""
clock45.normalise
=================
Vendor name normalisation and clustering.

Classical string matching, NOT an LLM. A wrong merge puts a wrong number in a
signed audit report, so the design is deliberately conservative.

IMPORTANT DESIGN CORRECTION (found by the test suite):
An earlier version stripped industry descriptors -- INDUSTRIES, TRADERS,
ENTERPRISES -- along with legal suffixes. That collapsed "Sharma Industries"
and "Sharma Traders" to the same key. Those are different vendors, and in this
product they may fall on OPPOSITE SIDES of the trader exclusion. So:

  * Legal FORM suffixes are stripped:   PVT LTD, LIMITED, LLP, & CO
  * Industry DESCRIPTORS are expanded:  INDS -> INDUSTRIES, ENT -> ENTERPRISES

Expanding rather than deleting is what lets the four spellings of one vendor
converge while keeping two genuinely different vendors apart.

Thresholds:
  >= AUTO_THRESHOLD   -> proposed as the same vendor, still shown to the user
  REVIEW..AUTO        -> human review queue
  <  REVIEW_THRESHOLD -> different vendors
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

try:  # pragma: no cover
    from rapidfuzz.fuzz import token_sort_ratio as _ratio
    BACKEND = "rapidfuzz"
except ImportError:  # pragma: no cover
    from difflib import SequenceMatcher

    def _ratio(a: str, b: str) -> float:
        ta, tb = " ".join(sorted(a.split())), " ".join(sorted(b.split()))
        return SequenceMatcher(None, ta, tb).ratio() * 100

    BACKEND = "difflib"

AUTO_THRESHOLD = 88.0
REVIEW_THRESHOLD = 75.0

# HEAD-TOKEN GUARD.
# Found in the first end-to-end demo run: "Sinha Consultancy Services" merged
# with "Sharma Consultancy Services" at 90.6, and "Sinha Logistics Services"
# with "Sharma Logistics Services" at 89.8. Different vendors. The shared
# descriptor tail dominated the similarity score.
#
# In Indian vendor names the FIRST token is the identifying one (the family or
# brand name) and the tail is a generic descriptor. So no two names may
# auto-merge unless their head tokens themselves match closely, whatever the
# overall score says. This is the guard that stops a wrong number reaching a
# signed audit report.
HEAD_TOKEN_THRESHOLD = 85.0


def head_token(norm_name: str) -> str:
    parts = norm_name.split()
    return parts[0] if parts else ""


def heads_compatible(a: str, b: str) -> bool:
    ha, hb = head_token(a), head_token(b)
    if not ha or not hb:
        return True
    if ha == hb:
        return True
    return _ratio(ha, hb) >= HEAD_TOKEN_THRESHOLD

# Legal form only. Longest first. These carry no identifying information.
LEGAL_SUFFIXES = [
    "PRIVATE LIMITED", "PVT LIMITED", "PRIVATE LTD", "PVT LTD", "P LTD",
    "LIMITED", "LTD", "LLP", "INCORPORATED", "INC",
    "AND COMPANY", "AND CO", "& COMPANY", "& CO",
]

# Descriptors are EXPANDED, never deleted -- they distinguish vendors.
ABBREVIATIONS = {
    "INDS": "INDUSTRIES", "IND": "INDUSTRIES", "INDL": "INDUSTRIAL",
    "ENT": "ENTERPRISES", "ENTP": "ENTERPRISES", "ENTS": "ENTERPRISES",
    "CORP": "CORPORATION", "AGY": "AGENCIES", "AGCY": "AGENCIES",
    "MFG": "MANUFACTURING", "ENGG": "ENGINEERING", "ENGRS": "ENGINEERS",
    "TRDRS": "TRADERS", "TRDG": "TRADING", "DISTR": "DISTRIBUTORS",
    "SERV": "SERVICES", "SVCS": "SERVICES", "TECH": "TECHNOLOGIES",
}

PREFIX_PATTERN = re.compile(r"^(M/S|MESSRS|THE)\b[\s.]*", re.IGNORECASE)


def normalise_name(raw: str) -> str:
    """Canonical form used ONLY for matching. Never display this to a user."""
    s = unicodedata.normalize("NFKD", raw or "")
    s = s.encode("ascii", "ignore").decode("ascii")

    # Strip the M/s prefix BEFORE punctuation removal, or the slash turns it
    # into a stray "M S" token that survives everything downstream.
    s = PREFIX_PATTERN.sub("", s).upper()

    s = re.sub(r"[.,\-_/\\()\[\]'\"]+", " ", s)
    s = re.sub(r"\s*&\s*", " & ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # Strip legal form suffixes repeatedly: "PVT LTD" may sit behind "& CO".
    changed = True
    while changed:
        changed = False
        for suf in LEGAL_SUFFIXES:
            if s.endswith(" " + suf) or s == suf:
                s = s[: len(s) - len(suf)].strip()
                changed = True
                break

    tokens = [ABBREVIATIONS.get(t, t) for t in s.split()]
    return " ".join(tokens).strip()


@dataclass
class Cluster:
    canonical: str
    members: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    needs_review: bool = False


def cluster_vendors(
    names: list[str],
    pan_map: dict[str, str] | None = None,
    auto: float = AUTO_THRESHOLD,
    review: float = REVIEW_THRESHOLD,
) -> tuple[list[Cluster], list[tuple[str, str, float]]]:
    """
    Cluster ledger spellings into vendors.

    A shared PAN/GSTIN is decisive and overrides string distance, because
    identity beats spelling. Returns (clusters, review_queue).
    """
    pan_map = pan_map or {}
    clusters: list[Cluster] = []
    review_queue: list[tuple[str, str, float]] = []

    for name in sorted(set(names), key=lambda n: (-len(n), n)):
        norm = normalise_name(name)
        pan = pan_map.get(name)
        best_idx, best_score = None, 0.0

        for i, c in enumerate(clusters):
            if pan and any(pan_map.get(m) == pan for m in c.members):
                best_idx, best_score = i, 100.0
                break
            c_norm = normalise_name(c.canonical)
            # A shared descriptor tail must never be enough on its own.
            if not heads_compatible(norm, c_norm):
                continue
            score = _ratio(norm, c_norm)
            if score > best_score:
                best_idx, best_score = i, score

        if best_idx is not None and best_score >= auto:
            clusters[best_idx].members.append(name)
            clusters[best_idx].scores[name] = round(best_score, 1)
        elif best_idx is not None and best_score >= review:
            review_queue.append((name, clusters[best_idx].canonical, round(best_score, 1)))
            clusters[best_idx].needs_review = True
            clusters.append(Cluster(canonical=name, members=[name], scores={name: 100.0}))
        else:
            clusters.append(Cluster(canonical=name, members=[name], scores={name: 100.0}))

    return clusters, review_queue
