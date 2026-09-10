"""
data/importer.py

CSV / Excel / JSON import pipeline — the primary way real market data
enters this application (automated scraping of listing portals is
intentionally NOT implemented; see data_sources.py for why).

Pipeline: read file -> map headers -> normalize rows -> validate/clean ->
resolve city/locality ids (creating new ones if needed) -> insert into DB
-> write an import_log row summarizing the outcome.
"""

import os
import json
import pandas as pd

from data.normalizer import normalize_headers, normalize_row
from data.validators import clean_dataframe
from database.database import Database


class ImportResult:
    def __init__(self):
        self.total_rows = 0
        self.new_records = 0
        self.rejected_records = 0
        self.rejections = []  # list of (row_index, reason)

    def as_dict(self):
        return {
            "total_rows": self.total_rows,
            "new_records": self.new_records,
            "rejected_records": self.rejected_records,
        }


def _read_any(file_path: str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(file_path)
    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data if isinstance(data, list) else data.get("records", []))
    raise ValueError(f"Unsupported file type: {ext}. Use .csv, .xlsx, .xls or .json")


def import_market_data(file_path: str, db: Database) -> ImportResult:
    result = ImportResult()
    df = _read_any(file_path)
    result.total_rows = len(df)

    header_map = normalize_headers(df.columns)
    df = df.rename(columns={orig: canon for orig, canon in header_map.items() if canon})
    # Drop columns that couldn't be mapped at all to avoid confusing downstream code,
    # but keep track for the user.
    unmapped = [orig for orig, canon in header_map.items() if not canon]

    # Resolve/create geography as we go.
    city_cache = {}
    locality_cache = {}

    def resolve_city(state_name, city_name):
        key = (state_name, city_name)
        if key in city_cache:
            return city_cache[key]
        state_id = db.upsert_state(state_name or "Unknown")
        city_id = db.upsert_city(state_id, city_name)
        city_cache[key] = city_id
        return city_id

    def resolve_locality(city_id, locality_name):
        key = (city_id, locality_name)
        if key in locality_cache:
            return locality_cache[key]
        locality_id = db.upsert_locality(city_id, locality_name)
        locality_cache[key] = locality_id
        return locality_id

    normalized_rows = []
    for _, raw in df.iterrows():
        row = normalize_row(raw.to_dict(), city_resolver=resolve_city, locality_resolver=resolve_locality)
        normalized_rows.append(row)

    norm_df = pd.DataFrame(normalized_rows)
    if norm_df.empty:
        db.log_import(os.path.basename(file_path), result.total_rows, 0, 0, 0,
                       notes="Empty or unreadable file")
        return result

    clean_df, rejected_df = clean_dataframe(norm_df)

    # Resolve source once per distinct source name in the batch (default to filename).
    if "source" not in clean_df.columns:
        clean_df["source"] = os.path.basename(file_path)
    source_ids = {name: db.upsert_source(str(name)) for name in clean_df["source"].fillna(os.path.basename(file_path)).unique()}

    listings_to_insert = []
    for _, row in clean_df.iterrows():
        listings_to_insert.append({
            "source_id": source_ids.get(row.get("source"), source_ids.get(os.path.basename(file_path))),
            "collected_date": row.get("collected_date"),
            "data_period": row.get("data_period"),
            "city_id": row.get("city_id"),
            "locality_id": row.get("locality_id"),
            "property_type": row.get("property_type"),
            "bhk": row.get("bhk"),
            "area_sqft": row.get("area_sqft"),
            "area_type": row.get("area_type") or "built-up",
            "furnishing": row.get("furnishing"),
            "age_years": row.get("age_years"),
            "listing_kind": row.get("listing_kind"),
            "price": row.get("price"),
            "price_per_sqft": row.get("price_per_sqft"),
            "monthly_rent": row.get("monthly_rent"),
            "rent_per_sqft": row.get("rent_per_sqft"),
            "is_sample_data": 0,
            "is_outlier": int(row.get("is_outlier", 0) or 0),
            "is_valid": 1,
            "rejection_reason": None,
            "raw_row_json": json.dumps(row.to_dict() if hasattr(row, "to_dict") else dict(row), default=str),
        })

    db.bulk_insert_listings(listings_to_insert)

    result.new_records = len(listings_to_insert)
    result.rejected_records = len(rejected_df)
    for _, r in rejected_df.iterrows():
        result.rejections.append(r.get("rejection_reason", "Unknown"))

    notes = f"Unmapped columns: {unmapped}" if unmapped else ""
    db.log_import(os.path.basename(file_path), result.total_rows, result.new_records,
                  0, result.rejected_records, notes=notes)
    return result


def export_template_csv(path: str):
    """Writes an empty CSV with the expected headers, to help users prepare import files."""
    cols = [
        "source", "collected_date", "data_period", "state", "city", "locality",
        "property_type", "bhk", "area_sqft", "area_type", "furnishing", "age_years",
        "listing_kind", "price", "price_per_sqft", "monthly_rent", "rent_per_sqft",
    ]
    pd.DataFrame(columns=cols).to_csv(path, index=False)
