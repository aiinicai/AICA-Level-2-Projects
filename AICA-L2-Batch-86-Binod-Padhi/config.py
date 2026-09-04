"""
config.py
Central configuration and application-defined constants.

IMPORTANT: Threshold values below (pricing bands, yield targets, scoring
weights) are APPLICATION-DEFINED ANALYTICAL DEFAULTS, not official
government, RBI, NHB or bank valuation standards. They are fully
configurable via the Settings screen and are persisted to the
`app_settings` table so user overrides survive restarts.
"""

import os

APP_NAME = "India Property Rent & Valuation Analyzer"
APP_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "resources")
DB_PATH = os.path.join(BASE_DIR, "property_analyzer.db")
LOCATIONS_JSON = os.path.join(DATA_DIR, "india_locations.json")
REPORTS_OUTPUT_DIR = os.path.join(BASE_DIR, "generated_reports")
os.makedirs(REPORTS_OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Overpriced / Underpriced classification thresholds (% deviation from
# estimated fair value). APPLICATION-DEFINED — see docstring above.
# ---------------------------------------------------------------------------
PRICE_BANDS = [
    (-10_000, -10.0, "UNDERPRICED"),
    (-10.0, 10.0, "FAIRLY PRICED"),
    (10.0, 20.0, "MODERATELY OVERPRICED"),
    (20.0, 10_000, "SIGNIFICANTLY OVERPRICED"),
]

# ---------------------------------------------------------------------------
# Default target rental yield used for the rental-capitalization valuation
# method, per city (application default; editable in Settings). Falls back
# to DEFAULT_TARGET_YIELD when a city isn't listed.
# ---------------------------------------------------------------------------
DEFAULT_TARGET_YIELD = 0.035  # 3.5%
CITY_TARGET_YIELD = {
    "Mumbai": 0.030,
    "Delhi": 0.028,
    "Bengaluru": 0.035,
    "Hyderabad": 0.038,
    "Chennai": 0.032,
    "Pune": 0.034,
    "Kolkata": 0.030,
    "Ahmedabad": 0.033,
    "Gurugram": 0.030,
    "Noida": 0.032,
}

# ---------------------------------------------------------------------------
# Combined Property Investment Score weighting (must sum to 1.0)
# ---------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "price_vs_fair_value": 0.30,
    "rental_yield": 0.20,
    "price_to_rent": 0.15,
    "comparable_evidence": 0.15,
    "local_demand": 0.10,
    "price_trend": 0.05,
    "rent_trend": 0.05,
}

SCORE_BANDS = [
    (85, 100, "Excellent"),
    (70, 84, "Good"),
    (55, 69, "Average"),
    (40, 54, "Weak"),
    (0, 39, "Poor"),
]

# ---------------------------------------------------------------------------
# Data quality / cleaning rules
# ---------------------------------------------------------------------------
MIN_REALISTIC_AREA_SQFT = 150
MAX_REALISTIC_AREA_SQFT = 20000
MIN_REALISTIC_RENT = 1000
MAX_REALISTIC_RENT = 2_000_000
MIN_REALISTIC_PRICE = 100_000
MAX_REALISTIC_PRICE = 5_000_000_000
IQR_OUTLIER_MULTIPLIER = 1.5
DATA_FRESHNESS_DAYS_GOOD = 90
DATA_FRESHNESS_DAYS_STALE = 365

DISCLAIMER = (
    "This calculator provides an indicative market analysis based on available "
    "property listings, rental data and selected market benchmarks. It is not a "
    "certified property valuation, legal valuation, bank valuation, government "
    "circle-rate valuation, or professional investment advice. Actual transaction "
    "prices may differ from listed prices. Users should independently verify "
    "property documents, title, approvals, physical condition, location, "
    "marketability and achievable rent."
)
