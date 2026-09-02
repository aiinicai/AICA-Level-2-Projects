"""
database/seed_data.py

Loads reference geography (states/cities/localities) from
resources/india_locations.json, and optionally loads a SMALL set of
clearly-flagged SAMPLE/DEMO listings so the application is usable
out-of-the-box before the user imports real data.

IMPORTANT: Sample listings inserted here have is_sample_data=1 and are
labeled "DEMO SOURCE — SAMPLE DATA" as their source. They are NOT real
market observations and must never be presented to the end user as real
sourced data. The GUI must visually flag any record/result that is based
on sample data (see gui/market_dashboard.py).
"""

import json
import random
import datetime as dt

from config import LOCATIONS_JSON
from database.database import Database


def load_geography(db: Database):
    with open(LOCATIONS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    state_ids = {}
    for state_name in data["states"]:
        state_ids[state_name] = db.upsert_state(state_name)

    city_ids = {}
    locality_ids = {}
    for city in data["cities"]:
        state_id = state_ids.get(city["state"])
        if state_id is None:
            state_id = db.upsert_state(city["state"])
        city_id = db.upsert_city(state_id, city["name"])
        city_ids[city["name"]] = city_id
        for loc_name in city.get("localities", []):
            locality_ids[(city["name"], loc_name)] = db.upsert_locality(city_id, loc_name)

    return city_ids, locality_ids


def seed_demo_listings(db: Database, city_ids: dict, locality_ids: dict, n_per_locality: int = 18):
    """
    Generates a SMALL, CLEARLY-LABELED set of synthetic demo listings so
    every screen has data to display before any real CSV/Excel import.
    This is NOT real market data — random.seed is fixed only for
    reproducibility of the demo, not to imply authenticity.
    """
    demo_source_id = db.upsert_source(
        "DEMO SOURCE — SAMPLE DATA",
        url=None,
        notes="Synthetic placeholder data generated locally for first-run demo purposes only. "
              "Not sourced from any real listing. Replace by importing real CSV/Excel data.",
    )

    rng = random.Random(42)
    today = dt.date.today()

    # A handful of illustrative localities with rough baseline price/rent
    # bands (₹/sqft sale, ₹/sqft rent) — purely illustrative starting points
    # for synthetic generation, NOT a real published benchmark.
    baseline = {
        ("Bengaluru", "Whitefield"): (7100, 26),
        ("Bengaluru", "HSR Layout"): (9200, 32),
        ("Mumbai", "Andheri West"): (21000, 65),
        ("Mumbai", "Powai"): (19500, 60),
        ("Pune", "Hinjewadi"): (6800, 22),
        ("Hyderabad", "Gachibowli"): (7600, 24),
        ("Chennai", "OMR"): (6600, 20),
        ("Delhi", "Dwarka"): (11500, 30),
        ("Noida", "Sector 62"): (7800, 21),
        ("Bhubaneswar", "Patia"): (4600, 14),
    }

    bhk_area = {1: (450, 650), 2: (850, 1250), 3: (1250, 1800), 4: (1800, 2600)}
    furnishings = ["Unfurnished", "Semi-furnished", "Furnished"]
    property_types = ["Apartment", "Apartment", "Apartment", "Independent House"]

    inserted = 0
    for (city_name, loc_name), (base_price_sqft, base_rent_sqft) in baseline.items():
        city_id = city_ids.get(city_name)
        locality_id = locality_ids.get((city_name, loc_name))
        if not city_id or not locality_id:
            continue

        for _ in range(n_per_locality):
            bhk = rng.choice([1, 2, 2, 3, 3, 4])
            lo, hi = bhk_area[bhk]
            area = round(rng.uniform(lo, hi))
            noise = rng.uniform(0.85, 1.18)
            price_per_sqft = round(base_price_sqft * noise, -1)
            rent_per_sqft = round(base_rent_sqft * rng.uniform(0.85, 1.20), 1)
            sale_price = round(price_per_sqft * area, -3)
            monthly_rent = round(rent_per_sqft * area, -2)
            age_years = round(rng.uniform(0, 15), 1)
            collected_date = (today - dt.timedelta(days=rng.randint(1, 340))).isoformat()

            for kind in ("sale", "rent"):
                listing = {
                    "source_id": demo_source_id,
                    "collected_date": collected_date,
                    "data_period": collected_date[:7],
                    "city_id": city_id,
                    "locality_id": locality_id,
                    "property_type": rng.choice(property_types),
                    "bhk": bhk,
                    "area_sqft": area,
                    "area_type": "built-up",
                    "furnishing": rng.choice(furnishings),
                    "age_years": age_years,
                    "listing_kind": kind,
                    "price": sale_price if kind == "sale" else None,
                    "price_per_sqft": price_per_sqft if kind == "sale" else None,
                    "monthly_rent": monthly_rent if kind == "rent" else None,
                    "rent_per_sqft": rent_per_sqft if kind == "rent" else None,
                    "is_sample_data": 1,
                    "is_outlier": 0,
                    "is_valid": 1,
                    "rejection_reason": None,
                    "raw_row_json": None,
                }
                db.insert_listing(listing)
                inserted += 1
    return inserted


def run_full_seed(db: Database, include_demo_listings: bool = True):
    city_ids, locality_ids = load_geography(db)
    n = 0
    if include_demo_listings and db.count_listings() == 0:
        n = seed_demo_listings(db, city_ids, locality_ids)
    return {"cities": len(city_ids), "localities": len(locality_ids), "demo_listings": n}


if __name__ == "__main__":
    db = Database()
    result = run_full_seed(db)
    print("Seed complete:", result)
