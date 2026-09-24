# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Filtering the lease list by lease ID, lessor, lessee, status and currency.

Pure Python (no UI framework, no database): works on the plain dicts the Leases page builds.
Within one filter the choices are OR-ed ("lessor is A or B"); the different filters are AND-ed
("lessor is A AND lessee is X"). Matching ignores case and extra spaces. A missing value is
shown as "-" on the page; that marker is never a choice and never matches a filter.
"""

_NO_VALUE = ("", "-")


def _key(value) -> str:
    """Comparison form of a value: tidy spaces, ignore case. The no-value marker becomes ''."""
    text = " ".join(str(value or "").split())
    return "" if text in _NO_VALUE else text.casefold()


def _options(cases: list, field: str) -> list:
    seen = {}
    for case in cases:
        key = _key(case.get(field))
        if key and key not in seen:
            seen[key] = " ".join(str(case.get(field)).split())  # the first spelling wins, tidied
    return sorted(seen.values(), key=str.casefold)


def filter_options(cases: list) -> dict:
    """What the user can pick from: lease_ids, lessors, lessees, statuses and currencies (sorted, distinct, no blanks)."""
    return {
        "lease_ids": _options(cases, "ref"),
        "lessors": _options(cases, "lessor"),
        "lessees": _options(cases, "lessee"),
        "statuses": _options(cases, "status"),
        "currencies": _options(cases, "currency"),
    }


def filter_leases(cases: list, lease_ids=(), lessors=(), lessees=(), statuses=(), currencies=()) -> list:
    """The leases matching ALL the filters that are set (an empty filter means 'any'), in their original order.

    Returns a new list; the input is never changed.
    """
    wanted = {
        "ref": {_key(v) for v in lease_ids or ()},
        "lessor": {_key(v) for v in lessors or ()},
        "lessee": {_key(v) for v in lessees or ()},
        "status": {_key(v) for v in statuses or ()},
        "currency": {_key(v) for v in currencies or ()},
    }
    matches = []
    for case in cases:
        for field, choices in wanted.items():
            if choices:
                key = _key(case.get(field))
                if not key or key not in choices:  # a lease with no value there can never match a filter on it
                    break
        else:
            matches.append(case)
    return matches
