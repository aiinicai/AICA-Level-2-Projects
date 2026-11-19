"""GST state codes (first two digits of GSTIN)."""
STATE_CODES = {
    "jammu and kashmir": "01", "jammu & kashmir": "01", "himachal pradesh": "02", "punjab": "03",
    "chandigarh": "04", "uttarakhand": "05", "haryana": "06", "delhi": "07", "rajasthan": "08",
    "uttar pradesh": "09", "bihar": "10", "sikkim": "11", "arunachal pradesh": "12", "nagaland": "13",
    "manipur": "14", "mizoram": "15", "tripura": "16", "meghalaya": "17", "assam": "18",
    "west bengal": "19", "jharkhand": "20", "odisha": "21", "orissa": "21", "chhattisgarh": "22",
    "madhya pradesh": "23", "gujarat": "24",
    "dadra and nagar haveli and daman and diu": "26", "dadra & nagar haveli and daman & diu": "26",
    "maharashtra": "27", "karnataka": "29", "goa": "30", "lakshadweep": "31", "kerala": "32",
    "tamil nadu": "33", "puducherry": "34", "pondicherry": "34",
    "andaman and nicobar islands": "35", "andaman & nicobar islands": "35", "telangana": "36",
    "andhra pradesh": "37", "ladakh": "38", "other territory": "97",
}


def state_code(name: str) -> str:
    return STATE_CODES.get((name or "").strip().lower(), "")

_NAMES = {}
for _n, _c in STATE_CODES.items():
    _NAMES.setdefault(_c, _n)


def state_name(code: str) -> str:
    """'24' -> 'Gujarat' (Tally's spelling)."""
    n = _NAMES.get((code or "")[:2], "")
    special = {"jammu and kashmir": "Jammu & Kashmir", "andaman and nicobar islands": "Andaman & Nicobar Islands",
               "dadra and nagar haveli and daman and diu": "Dadra & Nagar Haveli and Daman & Diu"}
    return special.get(n, n.title())
