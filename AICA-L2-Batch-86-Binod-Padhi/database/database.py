"""
database/database.py

SQLite schema creation and a thin Data Access Object (DAO) layer.
No business logic lives here — only persistence.
"""

import sqlite3
import json
import datetime as dt
from contextlib import contextmanager

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT
);

CREATE TABLE IF NOT EXISTS cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY(state_id) REFERENCES states(id),
    UNIQUE(state_id, name)
);

CREATE TABLE IF NOT EXISTS localities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    pincode TEXT,
    FOREIGN KEY(city_id) REFERENCES cities(id),
    UNIQUE(city_id, name)
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    url TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    collected_date TEXT,
    data_period TEXT,
    city_id INTEGER,
    locality_id INTEGER,
    property_type TEXT,
    bhk INTEGER,
    area_sqft REAL,
    area_type TEXT DEFAULT 'built-up',
    furnishing TEXT,
    age_years REAL,
    listing_kind TEXT CHECK(listing_kind IN ('sale','rent')),
    price REAL,
    price_per_sqft REAL,
    monthly_rent REAL,
    rent_per_sqft REAL,
    is_sample_data INTEGER DEFAULT 0,
    is_outlier INTEGER DEFAULT 0,
    is_valid INTEGER DEFAULT 1,
    rejection_reason TEXT,
    raw_row_json TEXT,
    FOREIGN KEY(source_id) REFERENCES sources(id),
    FOREIGN KEY(city_id) REFERENCES cities(id),
    FOREIGN KEY(locality_id) REFERENCES localities(id)
);

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT,
    city_id INTEGER,
    locality_id INTEGER,
    property_type TEXT,
    bhk INTEGER,
    carpet_area REAL,
    builtup_area REAL,
    floor INTEGER,
    total_floors INTEGER,
    age_years REAL,
    furnishing TEXT,
    parking INTEGER DEFAULT 0,
    lift INTEGER DEFAULT 0,
    gated_community INTEGER DEFAULT 0,
    amenities_json TEXT,
    new_or_resale TEXT,
    pincode TEXT,
    asking_price REAL,
    expected_rent REAL,
    maintenance_month REAL DEFAULT 0,
    property_tax_year REAL DEFAULT 0,
    insurance_year REAL DEFAULT 0,
    vacancy_pct REAL DEFAULT 0,
    brokerage REAL DEFAULT 0,
    stamp_duty REAL DEFAULT 0,
    renovation_cost REAL DEFAULT 0,
    loan_amount REAL,
    interest_rate REAL,
    loan_tenure_years REAL,
    FOREIGN KEY(city_id) REFERENCES cities(id),
    FOREIGN KEY(locality_id) REFERENCES localities(id)
);

CREATE TABLE IF NOT EXISTS valuations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    computed_at TEXT,
    market_rent_low REAL,
    market_rent_high REAL,
    market_rent_median REAL,
    comparable_value REAL,
    rental_cap_value REAL,
    adjusted_value REAL,
    fair_value_low REAL,
    fair_value_high REAL,
    gross_yield REAL,
    net_yield REAL,
    price_to_rent REAL,
    premium_pct REAL,
    verdict TEXT,
    investment_score REAL,
    investment_score_label TEXT,
    confidence_pct REAL,
    methodology_notes TEXT,
    result_json TEXT,
    FOREIGN KEY(property_id) REFERENCES properties(id)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS import_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_at TEXT,
    file_name TEXT,
    total_rows INTEGER,
    new_records INTEGER,
    updated_records INTEGER,
    rejected_records INTEGER,
    notes TEXT
);
"""


class Database:
    """Thin DAO wrapper around a single SQLite connection."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)

    # ------------------------------------------------------------------
    # States / Cities / Localities
    # ------------------------------------------------------------------
    def upsert_state(self, name, code=None):
        with self.connect() as conn:
            cur = conn.execute("SELECT id FROM states WHERE name=?", (name,))
            row = cur.fetchone()
            if row:
                return row["id"]
            cur = conn.execute("INSERT INTO states(name, code) VALUES (?,?)", (name, code))
            return cur.lastrowid

    def upsert_city(self, state_id, name):
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id FROM cities WHERE state_id=? AND name=?", (state_id, name)
            )
            row = cur.fetchone()
            if row:
                return row["id"]
            cur = conn.execute(
                "INSERT INTO cities(state_id, name) VALUES (?,?)", (state_id, name)
            )
            return cur.lastrowid

    def upsert_locality(self, city_id, name, pincode=None):
        with self.connect() as conn:
            cur = conn.execute(
                "SELECT id FROM localities WHERE city_id=? AND name=?", (city_id, name)
            )
            row = cur.fetchone()
            if row:
                return row["id"]
            cur = conn.execute(
                "INSERT INTO localities(city_id, name, pincode) VALUES (?,?,?)",
                (city_id, name, pincode),
            )
            return cur.lastrowid

    def get_cities(self):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT c.id, c.name, s.name as state_name FROM cities c "
                "JOIN states s ON s.id = c.state_id ORDER BY c.name"
            )]

    def get_localities(self, city_id):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT id, name, pincode FROM localities WHERE city_id=? ORDER BY name",
                (city_id,),
            )]

    def get_states(self):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT id, name, code FROM states ORDER BY name")]

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------
    def upsert_source(self, name, url=None, notes=None):
        with self.connect() as conn:
            cur = conn.execute("SELECT id FROM sources WHERE name=?", (name,))
            row = cur.fetchone()
            if row:
                return row["id"]
            cur = conn.execute(
                "INSERT INTO sources(name, url, notes) VALUES (?,?,?)", (name, url, notes)
            )
            return cur.lastrowid

    # ------------------------------------------------------------------
    # Listings (market data)
    # ------------------------------------------------------------------
    def insert_listing(self, listing: dict):
        cols = [
            "source_id", "collected_date", "data_period", "city_id", "locality_id",
            "property_type", "bhk", "area_sqft", "area_type", "furnishing", "age_years",
            "listing_kind", "price", "price_per_sqft", "monthly_rent", "rent_per_sqft",
            "is_sample_data", "is_outlier", "is_valid", "rejection_reason", "raw_row_json",
        ]
        values = [listing.get(c) for c in cols]
        placeholders = ",".join(["?"] * len(cols))
        with self.connect() as conn:
            cur = conn.execute(
                f"INSERT INTO listings ({','.join(cols)}) VALUES ({placeholders})", values
            )
            return cur.lastrowid

    def bulk_insert_listings(self, listings: list):
        for l in listings:
            self.insert_listing(l)

    def query_listings(self, city_id=None, locality_id=None, property_type=None,
                        bhk=None, listing_kind=None, only_valid=True):
        q = "SELECT l.*, s.name as source_name FROM listings l LEFT JOIN sources s ON s.id=l.source_id WHERE 1=1"
        params = []
        if city_id:
            q += " AND l.city_id=?"
            params.append(city_id)
        if locality_id:
            q += " AND l.locality_id=?"
            params.append(locality_id)
        if property_type:
            q += " AND l.property_type=?"
            params.append(property_type)
        if bhk:
            q += " AND l.bhk=?"
            params.append(bhk)
        if listing_kind:
            q += " AND l.listing_kind=?"
            params.append(listing_kind)
        if only_valid:
            q += " AND l.is_valid=1"
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(q, params)]

    def count_listings(self):
        with self.connect() as conn:
            return conn.execute("SELECT COUNT(*) c FROM listings").fetchone()["c"]

    # ------------------------------------------------------------------
    # Properties & Valuations
    # ------------------------------------------------------------------
    def insert_property(self, prop: dict) -> int:
        prop = dict(prop)
        prop["created_at"] = dt.datetime.now().isoformat()
        if "amenities_json" in prop and isinstance(prop["amenities_json"], (list, dict)):
            prop["amenities_json"] = json.dumps(prop["amenities_json"])
        cols = list(prop.keys())
        placeholders = ",".join(["?"] * len(cols))
        with self.connect() as conn:
            cur = conn.execute(
                f"INSERT INTO properties ({','.join(cols)}) VALUES ({placeholders})",
                list(prop.values()),
            )
            return cur.lastrowid

    def save_valuation(self, valuation: dict) -> int:
        valuation = dict(valuation)
        valuation["computed_at"] = dt.datetime.now().isoformat()
        if "result_json" in valuation and isinstance(valuation["result_json"], dict):
            valuation["result_json"] = json.dumps(valuation["result_json"])
        cols = list(valuation.keys())
        placeholders = ",".join(["?"] * len(cols))
        with self.connect() as conn:
            cur = conn.execute(
                f"INSERT INTO valuations ({','.join(cols)}) VALUES ({placeholders})",
                list(valuation.values()),
            )
            return cur.lastrowid

    def get_valuation_history(self, property_id=None, limit=50):
        q = "SELECT * FROM valuations"
        params = []
        if property_id:
            q += " WHERE property_id=?"
            params.append(property_id)
        q += " ORDER BY computed_at DESC LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(q, params)]

    # ------------------------------------------------------------------
    # Import log
    # ------------------------------------------------------------------
    def log_import(self, file_name, total_rows, new_records, updated_records,
                    rejected_records, notes=""):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO import_log(imported_at, file_name, total_rows, new_records, "
                "updated_records, rejected_records, notes) VALUES (?,?,?,?,?,?,?)",
                (dt.datetime.now().isoformat(), file_name, total_rows, new_records,
                 updated_records, rejected_records, notes),
            )

    def get_last_update_summary(self):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM import_log ORDER BY imported_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def get_settings(self):
        with self.connect() as conn:
            return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM app_settings")}

    def set_setting(self, key, value):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO app_settings(key, value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
