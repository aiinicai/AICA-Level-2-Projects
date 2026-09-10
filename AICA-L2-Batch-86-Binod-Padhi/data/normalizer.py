"""
data/normalizer.py

Different sources describe the same thing differently (e.g. "2BHK" vs
"2 BHK" vs "2", "Semi Furnished" vs "semi-furnished", carpet vs built-up
area). This module maps arbitrary column names/values onto the internal
canonical schema used by the `listings` table. It does NOT assume that
price/rent figures from different sources are directly comparable — it
only standardizes representation; comparability weighting happens in
valuation/comparable.py.
"""

import re

CANONICAL_COLUMNS = [
    "source", "collected_date", "data_period", "state", "city", "locality",
    "property_type", "bhk", "area_sqft", "area_type", "furnishing", "age_years",
    "listing_kind", "price", "price_per_sqft", "monthly_rent", "rent_per_sqft",
]

# Maps many possible incoming header spellings to the canonical column name.
HEADER_ALIASES = {
    "source": ["source", "site", "portal", "data source"],
    "collected_date": ["collected_date", "date", "scrape_date", "collection date"],
    "data_period": ["data_period", "period", "month", "quarter"],
    "state": ["state"],
    "city": ["city", "town"],
    "locality": ["locality", "area_name", "neighbourhood", "neighborhood", "micro market", "locality/area"],
    "property_type": ["property_type", "type", "property type", "housing_type"],
    "bhk": ["bhk", "bedrooms", "no_of_bedrooms", "configuration"],
    "area_sqft": ["area", "area_sqft", "sqft", "area (sq.ft.)", "carpet_area", "builtup_area", "super_area"],
    "area_type": ["area_type", "area type"],
    "furnishing": ["furnishing", "furnished_status"],
    "age_years": ["age_years", "age", "property_age", "age of property"],
    "listing_kind": ["listing_kind", "kind", "listing_type", "sale_or_rent"],
    "price": ["price", "sale_price", "asking_price"],
    "price_per_sqft": ["price_per_sqft", "price/sqft", "rate_per_sqft", "price per sqft"],
    "monthly_rent": ["monthly_rent", "rent", "rent_per_month", "expected_rent"],
    "rent_per_sqft": ["rent_per_sqft", "rent/sqft", "rent per sqft"],
}

FURNISHING_MAP = {
    "furnished": "Furnished",
    "semi furnished": "Semi-furnished",
    "semi-furnished": "Semi-furnished",
    "semifurnished": "Semi-furnished",
    "unfurnished": "Unfurnished",
    "bare shell": "Unfurnished",
}

PROPERTY_TYPE_MAP = {
    "apartment": "Apartment",
    "flat": "Apartment",
    "independent house": "Independent House",
    "house": "Independent House",
    "villa": "Villa",
    "builder floor": "Builder Floor",
    "penthouse": "Penthouse",
    "plot": "Plot",
    "commercial": "Commercial",
    "office": "Commercial",
    "shop": "Commercial",
}


def _build_reverse_lookup():
    rev = {}
    for canon, aliases in HEADER_ALIASES.items():
        for a in aliases:
            rev[a.strip().lower()] = canon
    return rev


_REVERSE_LOOKUP = _build_reverse_lookup()


def normalize_headers(columns) -> dict:
    """Returns {original_column_name: canonical_name or None}."""
    mapping = {}
    for col in columns:
        key = re.sub(r"\s+", " ", str(col).strip().lower())
        mapping[col] = _REVERSE_LOOKUP.get(key)
    return mapping


def normalize_bhk(value):
    if value is None:
        return None
    s = str(value).strip().upper().replace("BHK", "").strip()
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def normalize_furnishing(value):
    if not value:
        return "Unfurnished"
    key = str(value).strip().lower()
    return FURNISHING_MAP.get(key, str(value).strip().title())


def normalize_property_type(value):
    if not value:
        return "Apartment"
    key = str(value).strip().lower()
    return PROPERTY_TYPE_MAP.get(key, str(value).strip().title())


def normalize_listing_kind(value):
    if not value:
        return None
    key = str(value).strip().lower()
    if key in ("sale", "sell", "resale", "buy"):
        return "sale"
    if key in ("rent", "lease", "rental"):
        return "rent"
    return None


def coerce_number(value):
    if value is None or value == "":
        return None
    try:
        s = str(value).replace(",", "").replace("₹", "").strip()
        s = re.sub(r"[^\d.\-]", "", s)
        return float(s) if s else None
    except (ValueError, TypeError):
        return None


def normalize_row(raw_row: dict, city_resolver=None, locality_resolver=None) -> dict:
    """
    Converts one raw dict (arbitrary headers already mapped to canonical
    names by the caller via normalize_headers) into the canonical schema
    ready for validators.validate_row / database insertion.

    city_resolver / locality_resolver: optional callables that turn a
    city/locality *name* into a database id (city_id, locality_id).
    """
    row = dict(raw_row)

    row["bhk"] = normalize_bhk(row.get("bhk"))
    row["furnishing"] = normalize_furnishing(row.get("furnishing"))
    row["property_type"] = normalize_property_type(row.get("property_type"))
    row["listing_kind"] = normalize_listing_kind(row.get("listing_kind")) or (
        "sale" if coerce_number(row.get("price")) else
        ("rent" if coerce_number(row.get("monthly_rent")) else None)
    )
    row["area_sqft"] = coerce_number(row.get("area_sqft"))
    row["age_years"] = coerce_number(row.get("age_years")) or 0
    row["price"] = coerce_number(row.get("price"))
    row["price_per_sqft"] = coerce_number(row.get("price_per_sqft"))
    row["monthly_rent"] = coerce_number(row.get("monthly_rent"))
    row["rent_per_sqft"] = coerce_number(row.get("rent_per_sqft"))

    # Derive per-sqft figures if missing but derivable.
    if row["area_sqft"]:
        if not row["price_per_sqft"] and row["price"]:
            row["price_per_sqft"] = round(row["price"] / row["area_sqft"], 2)
        if not row["rent_per_sqft"] and row["monthly_rent"]:
            row["rent_per_sqft"] = round(row["monthly_rent"] / row["area_sqft"], 2)

    if city_resolver and row.get("city"):
        row["city_id"] = city_resolver(row.get("state"), row.get("city"))
    if locality_resolver and row.get("locality") and row.get("city_id"):
        row["locality_id"] = locality_resolver(row["city_id"], row.get("locality"))

    return row
