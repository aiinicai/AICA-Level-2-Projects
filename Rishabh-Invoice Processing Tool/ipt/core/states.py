"""Indian GST state / UT codes (first two digits of a GSTIN)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class State:
    code: str
    name: str
    is_ut_without_legislature: bool  # True -> UTGST applies instead of SGST


STATES: dict[str, State] = {s.code: s for s in [
    State("01", "Jammu and Kashmir", False),
    State("02", "Himachal Pradesh", False),
    State("03", "Punjab", False),
    State("04", "Chandigarh", True),
    State("05", "Uttarakhand", False),
    State("06", "Haryana", False),
    State("07", "Delhi", False),
    State("08", "Rajasthan", False),
    State("09", "Uttar Pradesh", False),
    State("10", "Bihar", False),
    State("11", "Sikkim", False),
    State("12", "Arunachal Pradesh", False),
    State("13", "Nagaland", False),
    State("14", "Manipur", False),
    State("15", "Mizoram", False),
    State("16", "Tripura", False),
    State("17", "Meghalaya", False),
    State("18", "Assam", False),
    State("19", "West Bengal", False),
    State("20", "Jharkhand", False),
    State("21", "Odisha", False),
    State("22", "Chhattisgarh", False),
    State("23", "Madhya Pradesh", False),
    State("24", "Gujarat", False),
    State("25", "Daman and Diu (old code)", True),
    State("26", "Dadra and Nagar Haveli and Daman and Diu", True),
    State("27", "Maharashtra", False),
    State("28", "Andhra Pradesh (old code)", False),
    State("29", "Karnataka", False),
    State("30", "Goa", False),
    State("31", "Lakshadweep", True),
    State("32", "Kerala", False),
    State("33", "Tamil Nadu", False),
    State("34", "Puducherry", False),
    State("35", "Andaman and Nicobar Islands", True),
    State("36", "Telangana", False),
    State("37", "Andhra Pradesh", False),
    State("38", "Ladakh", True),
    State("97", "Other Territory", True),
    State("99", "Centre Jurisdiction", False),
]}


def state_name(code: str | None) -> str:
    if not code:
        return ""
    st = STATES.get(code)
    return st.name if st else ""
