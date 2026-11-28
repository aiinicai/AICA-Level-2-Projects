"""Who is logged in and which company / financial year is active."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CurrentUser:
    id: int
    username: str
    full_name: str
    role: str


@dataclass
class AppContext:
    user: CurrentUser | None = None
    company_id: int | None = None
    fy_id: int | None = None
