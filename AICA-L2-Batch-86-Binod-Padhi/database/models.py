"""
database/models.py
Lightweight dataclasses used to pass structured data between layers
(GUI <-> valuation <-> database) without depending on sqlite3.Row directly.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class PropertyInput:
    city_id: int
    locality_id: int
    property_type: str            # 'Apartment' | 'Independent House' | 'Villa'
    bhk: int
    carpet_area: float
    builtup_area: float
    asking_price: float
    expected_rent: float
    new_or_resale: str = "Resale"
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    age_years: float = 0.0
    furnishing: str = "Unfurnished"      # 'Furnished'|'Semi-furnished'|'Unfurnished'
    parking: bool = False
    lift: bool = False
    gated_community: bool = False
    amenities: List[str] = field(default_factory=list)
    pincode: Optional[str] = None
    maintenance_month: float = 0.0
    property_tax_year: float = 0.0
    insurance_year: float = 0.0
    vacancy_pct: float = 5.0
    brokerage: float = 0.0
    stamp_duty: float = 0.0
    renovation_cost: float = 0.0
    loan_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    loan_tenure_years: Optional[float] = None

    def to_db_dict(self) -> Dict:
        d = self.__dict__.copy()
        d["amenities_json"] = d.pop("amenities")
        d["parking"] = int(bool(self.parking))
        d["lift"] = int(bool(self.lift))
        d["gated_community"] = int(bool(self.gated_community))
        return d


@dataclass
class ValuationResult:
    property_id: int
    market_rent_low: float
    market_rent_high: float
    market_rent_median: float
    comparable_value: float
    rental_cap_value: float
    adjusted_value: float
    fair_value_low: float
    fair_value_high: float
    gross_yield: float
    net_yield: float
    price_to_rent: float
    premium_pct: float
    verdict: str
    investment_score: float
    investment_score_label: str
    confidence_pct: float
    methodology_notes: str
    n_comparables: int = 0
    n_rental_obs: int = 0
    n_sources: int = 0

    def to_db_dict(self) -> Dict:
        return {
            "property_id": self.property_id,
            "market_rent_low": self.market_rent_low,
            "market_rent_high": self.market_rent_high,
            "market_rent_median": self.market_rent_median,
            "comparable_value": self.comparable_value,
            "rental_cap_value": self.rental_cap_value,
            "adjusted_value": self.adjusted_value,
            "fair_value_low": self.fair_value_low,
            "fair_value_high": self.fair_value_high,
            "gross_yield": self.gross_yield,
            "net_yield": self.net_yield,
            "price_to_rent": self.price_to_rent,
            "premium_pct": self.premium_pct,
            "verdict": self.verdict,
            "investment_score": self.investment_score,
            "investment_score_label": self.investment_score_label,
            "confidence_pct": self.confidence_pct,
            "methodology_notes": self.methodology_notes,
            "result_json": {
                "n_comparables": self.n_comparables,
                "n_rental_obs": self.n_rental_obs,
                "n_sources": self.n_sources,
            },
        }
