"""Data models shared across the tool. Plain dataclasses so they serialise cleanly into a project file."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from .resources import resource_path

CONFIG_DIR = resource_path("ct_tool", "config")
if not CONFIG_DIR.exists():
    CONFIG_DIR = Path(__file__).parent / "config"
ZERO_TOL = 0.005   # amounts smaller than this are treated as zero in checks
MATCH_TOL = 1.00   # tolerance (in source currency units) for cross-file reconciliations


def load_json(name: str) -> Any:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class Account:
    """One trial balance line. All amounts are positive numbers in the TB's own currency;
    `net` is signed: debit positive, credit negative."""
    code: str
    name: str
    debit: float = 0.0
    credit: float = 0.0
    net: float = 0.0
    opening: Optional[float] = None        # signed opening balance if the TB provides one
    hint: Optional[str] = None             # raw classification text from the TB, if any
    source_ref: str = ""                   # file / sheet / row for traceability
    currency: Optional[str] = None         # per-account currency if the TB provides one
    notes: list = field(default_factory=list)
    movement: Optional[float] = None       # signed period movement if the TB gives it next to opening and closing columns
    group: str = ""                        # parent group(s) in the source, e.g. 'Current Assets > Sundry Debtors' (Tally-style exports)

    def key(self) -> str:
        """Stable identifier used for mapping overrides and decisions."""
        return self.code if self.code else self.name.strip().lower()


@dataclass
class TrialBalance:
    accounts: list = field(default_factory=list)       # list[Account]
    title: str = ""                                    # text found above the table (often entity / date)
    source_file: str = ""
    sheet: str = ""
    currency: str = ""
    sign_convention: str = ""                          # description of how signs were interpreted
    warnings: list = field(default_factory=list)       # extraction warnings (strings)
    ignored_columns: list = field(default_factory=list)
    extraction_method: str = "table"                   # table | pdf-text | pdf-ocr


@dataclass
class GLLine:
    line_id: str
    date: Optional[str]                    # ISO date string or None
    account_code: str
    account_name: str
    description: str = ""
    debit: float = 0.0
    credit: float = 0.0
    counterparty: str = ""
    reference: str = ""
    source_ref: str = ""

    @property
    def net(self) -> float:
        return self.debit - self.credit


@dataclass
class GeneralLedger:
    lines: list = field(default_factory=list)          # list[GLLine]
    source_file: str = ""
    sheet: str = ""
    warnings: list = field(default_factory=list)
    extraction_method: str = "table"


def to_dict(obj) -> dict:
    return asdict(obj)


def account_from_dict(d: dict) -> Account:
    return Account(**d)


def tb_from_dict(d: dict) -> TrialBalance:
    tb = TrialBalance(**{k: v for k, v in d.items() if k != "accounts"})
    tb.accounts = [account_from_dict(a) for a in d.get("accounts", [])]
    return tb


def gl_from_dict(d: dict) -> GeneralLedger:
    gl = GeneralLedger(**{k: v for k, v in d.items() if k != "lines"})
    gl.lines = [GLLine(**ln) for ln in d.get("lines", [])]
    return gl
