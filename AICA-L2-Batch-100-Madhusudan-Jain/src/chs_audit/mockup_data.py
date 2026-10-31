"""A second, independent synthetic society used by the "mock-up data upload" button.

It re-uses the generator with a different random seed and a different society
profile (Green Meadows, Pune) so the demo shows the tool running on data it has
never seen, with the same deliberately seeded control failures. Everything is
invented; no real society, member or vendor is described.
"""
from __future__ import annotations

import random
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd

from . import generate_data as g
from .config import SOCIETY

ROOT = Path(__file__).resolve().parents[2]
MOCKUP_DIR = ROOT / "data" / "mockup"
MOCKUP_LABEL = "Mock-up upload (Green Meadows, Pune, 64 flats)"

MOCK_SOCIETY = replace(
    SOCIETY,
    name="Green Meadows Co-operative Housing Society Ltd.",
    reg_no="PNA/PNA(1)/HSG/(TC)/8821/2012",
    address="Survey No. 42, Baner Road, Pune 411045, Maharashtra",
    registration_date=date(2012, 6, 18),
    occupation_certificate_date=date(2011, 12, 5),
    gstin="27AABAG4521C1ZK",
    pan="AABAG4521C",
    tan="PNEG08712B",
    last_structural_audit=date(2022, 1, 10),
    last_mc_election=date(2022, 11, 20),
    lift_licence_expiry=date(2026, 8, 2),
    insurance_policy_expiry=date(2026, 10, 1),
    last_fire_audit_form_b=date(2026, 1, 8),
)

REPLACEMENTS = [
    ("Sunrise Heights Co-operative Housing Society Ltd.", MOCK_SOCIETY.name),
    ("Sunrise Heights", "Green Meadows"),
    ("Ghodbunder Road, Thane (W)", "Baner Road, Pune"),
    ("Thane Municipal Corporation", "Pune Municipal Corporation"),
    ("Wagle Estate, Thane", "Hinjewadi, Pune"), ("Majiwada, Thane", "Aundh, Pune"), ("Naupada, Thane", "Kothrud, Pune"),
    ("Kalwa, Thane", "Wakad, Pune"), ("Kasarvadavali, Thane", "Balewadi, Pune"), ("Thane", "Pune"),
]


def _swap(text: str) -> str:
    for a, b in REPLACEMENTS:
        text = text.replace(a, b)
    return text


def generate(out_dir: Path = MOCKUP_DIR) -> Path:
    g.rng = random.Random(20250915)
    g.SOCIETY = MOCK_SOCIETY
    try:
        path = g.generate(out_dir)
    finally:
        g.rng = random.Random(g.SEED)
        g.SOCIETY = SOCIETY
    sheets = pd.read_excel(path, sheet_name=None)
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        for name, df in sheets.items():
            for c in df.columns:
                if df[c].dtype == object:
                    df[c] = df[c].map(lambda v: _swap(v) if isinstance(v, str) else v)
            df.to_excel(xw, sheet_name=name, index=False)
    for f in (out_dir / "minutes").glob("*.txt"):
        f.write_text(_swap(f.read_text(encoding="utf-8")), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(f"written {generate()}")
