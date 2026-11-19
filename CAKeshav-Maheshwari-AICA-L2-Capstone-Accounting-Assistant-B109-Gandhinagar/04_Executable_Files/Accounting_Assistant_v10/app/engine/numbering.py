"""Next voucher number for a voucher type, from the local copy of Tally's day book.

Some voucher types are set to 'Automatic (Manual Override)'. When such a voucher is imported without a number,
TallyPrime may refuse it with an 'exception' and no message (seen on a Receipt type set to Automatic (Manual Override)), so the app sends
the next number itself, continuing the last number's pattern (prefix / zero padding kept)."""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from . import history

_DIG = re.compile(r"\d+")


def _fy(yyyymmdd: str) -> str:
    y, m = int(yyyymmdd[:4]), int(yyyymmdd[4:6])
    return str(y if m >= 4 else y - 1)


def _counter_group(number: str, others: list[str]) -> int:
    """Which digit group is the running counter: the one that varies between this type's numbers; otherwise the
    last group that does not look like a year ('26', '27', '2026', '26-27')."""
    groups = _DIG.findall(number)
    if not groups:
        return -1
    same_shape = [o for o in others if len(_DIG.findall(o)) == len(groups) and o != number]
    for idx in range(len(groups) - 1, -1, -1):
        if any(_DIG.findall(o)[idx] != groups[idx] for o in same_shape):
            return idx
    for idx in range(len(groups) - 1, -1, -1):
        g = groups[idx]
        if not (len(groups) > 1 and (len(g) in (2, 4)) and (20 <= int(g[-2:]) <= 40) and idx != 0
                and len(g) != len(groups[idx - 1] if idx else "")):
            return idx
    return len(groups) - 1


def bump(number: str, others: list[str] | None = None) -> str:
    if not number:
        return "1"
    idx = _counter_group(number, others or [])
    if idx < 0:
        return number + "1"
    spans = [m.span() for m in _DIG.finditer(number)]
    a, b = spans[idx]
    d = number[a:b]
    return number[:a] + str(int(d) + 1).zfill(len(d)) + number[b:]


def next_number(session: Session, company_id: str, vtype: str, on_date: str, live: list | None = None) -> str:
    """live: [(number, date)] read from Tally just now - preferred, because entries made in Tally after the last
    Sync are not in the local copy (that gave a duplicate number, which Tally refuses silently)."""
    fy = _fy(on_date)
    nums = [(v.number, v.date) for v in history.vouchers(session, company_id)
            if v.voucher_type == vtype and v.number and _fy(v.date) == fy]
    nums += [(n, d) for n, d in (live or []) if n and (not d or _fy(d) == fy)]
    if not nums:
        return "1"
    others = [n for n, _ in nums]

    def key(nd):
        n = nd[0]
        idx = _counter_group(n, others)
        g = _DIG.findall(n)
        return (int(g[idx]) if idx >= 0 else -1, nd[1])
    best = max(nums, key=key)[0]
    nxt = bump(best, others)
    taken = set(others)
    while nxt in taken:                       # never reuse a number that already exists
        nxt = bump(nxt, others)
    return nxt


def needs_number(numbering_method: str) -> bool:
    t = (numbering_method or "").lower()
    return "manual" in t
