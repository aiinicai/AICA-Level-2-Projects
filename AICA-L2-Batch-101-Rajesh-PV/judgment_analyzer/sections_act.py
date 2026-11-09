"""Which Act does a section number belong to - Income-tax Act, 1961 or Income-tax Act, 2025?

From 1 April 2026 Indian income-tax judgments and headnotes may refer to the
Income-tax Act, 1961, to the Income-tax Act, 2025, or to both (publishers add
the corresponding 2025 Act section to older orders). The app keeps the two lists
separate, in the key facts and in the precedent register.

Rules applied after the AI has sorted the sections (the AI reads the context):
1. Definite: the highest numbered section of the 1961 Act is 298, so a section
   whose number is above 298 can only be a 2025 Act section. It is moved to the
   2025 list if the AI put it in the 1961 list.
2. Context: for numbers up to 298 both Acts are possible. The app looks at the
   words following each mention of the section in the judgment ("... of the
   Income-tax Act, 1961" / "... Act, 2025"). If the context points to the other
   Act, the section is flagged for the reviewer - it is not moved silently.
3. Sections with a letter suffix (194C, 44AE, 80-IA, 14A) follow the 1961 Act
   numbering style; the 2025 Act numbers its sections sequentially. A lettered
   section in the 2025 list is flagged for checking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MAX_1961_SECTION = 298
ACT_1961, ACT_2025 = "1961", "2025"

_BASE_RE = re.compile(r"^\s*(\d{1,3})\s*-?\s*([A-Za-z]{0,4})")
_ACT_RE = re.compile(r"Act,?\s*(1961|2025)|\b(1961|2025)\s+Act", re.IGNORECASE)
_SEC_PREFIX = r"(?:sections?|secs?\.?|ss?\.|u/s\.?)\s*"


def base_number(section: str) -> int | None:
    m = _BASE_RE.match(str(section or ""))
    return int(m.group(1)) if m else None


def has_letter_suffix(section: str) -> bool:
    m = _BASE_RE.match(str(section or ""))
    return bool(m and m.group(2))


def definite_act(section: str) -> str | None:
    """The Act a section must belong to by its number alone, or None if both are possible."""
    n = base_number(section)
    if n is not None and n > MAX_1961_SECTION:
        return ACT_2025
    return None


def context_act(section: str, source_text: str, window: int = 160) -> str | None:
    """Which Act the judgment names right after mentioning the section (majority of mentions)."""
    sec = str(section or "").strip()
    if not sec or not source_text:
        return None
    head = re.escape(re.split(r"[\s(]", sec, 1)[0])
    pattern = re.compile(_SEC_PREFIX + head + r"(?![0-9A-Za-z])", re.IGNORECASE)
    votes = {ACT_1961: 0, ACT_2025: 0}
    for m in pattern.finditer(source_text):
        after = source_text[m.end():m.end() + window]
        # stop where the next clause starts: "s.194C ... Act, 1961 / s.393 ... Act, 2025"
        nxt = re.search(r"[/;]|\.\s+[A-Z]", after[1:])
        if nxt:
            after = after[:nxt.start() + 1]
        a = _ACT_RE.search(after)
        if a:
            votes[a.group(1) or a.group(2)] += 1
    if votes[ACT_1961] == votes[ACT_2025]:
        return None
    return ACT_1961 if votes[ACT_1961] > votes[ACT_2025] else ACT_2025


@dataclass
class ActCheck:
    sections_1961: list[str] = field(default_factory=list)
    sections_2025: list[str] = field(default_factory=list)
    moved: list[str] = field(default_factory=list)       # moved automatically (number above 298)
    to_check: list[str] = field(default_factory=list)    # messages for the reviewer

    @property
    def notes(self) -> list[str]:
        out = [f"Section {s} moved to the 2025 Act list (the 1961 Act has no section above "
               f"{MAX_1961_SECTION})." for s in self.moved]
        return out + self.to_check


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for s in items:
        k = re.sub(r"\s+", "", s).lower()
        if k and k not in seen:
            seen.add(k)
            out.append(s)
    return out


def sort_sections(sections_1961: list[str], sections_2025: list[str], source_text: str = "") -> ActCheck:
    """Apply the definite rule and flag doubtful placements (see module docstring)."""
    res = ActCheck()
    for s in sections_1961:
        if definite_act(s) == ACT_2025:
            res.sections_2025.append(s)
            res.moved.append(s)
        else:
            res.sections_1961.append(s)
            if source_text and not has_letter_suffix(s) and context_act(s, source_text) == ACT_2025:
                res.to_check.append(f"Section {s}: the judgment mentions it with the 2025 Act - check which Act.")
    for s in sections_2025:
        res.sections_2025.append(s)
        if has_letter_suffix(s):
            res.to_check.append(f"Section {s}: lettered numbering is 1961 Act style - check which Act.")
        elif source_text and definite_act(s) is None and context_act(s, source_text) == ACT_1961:
            res.to_check.append(f"Section {s}: the judgment mentions it with the 1961 Act - check which Act.")
    res.sections_1961 = _dedupe(res.sections_1961)
    res.sections_2025 = _dedupe(res.sections_2025)
    return res


def split_legacy(sections: list[str], source_text: str = "") -> tuple[list[str], list[str]]:
    """Split one mixed list (older data) into 1961 and 2025 lists."""
    a, b = [], []
    for s in sections:
        act = definite_act(s) or (None if has_letter_suffix(s) else context_act(s, source_text))
        (b if act == ACT_2025 else a).append(s)
    return a, b
