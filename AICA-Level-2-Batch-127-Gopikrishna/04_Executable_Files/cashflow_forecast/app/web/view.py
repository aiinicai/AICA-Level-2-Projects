"""Forecast view options (scenario, toggles, horizon) shared by the grid, PDC list and hold register.

Options come from the query string and are remembered in the session, so moving between screens
keeps the same view. Nothing here changes stored data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.forecast import Forecast
from app.engine.loader import get_scenario, run_forecast
from app.models import Scenario
from app.services.settings_service import get_business_settings
from app.services.snapshots import save_snapshot


@dataclass
class View:
    scenario: Scenario
    scenarios: list[Scenario]
    risk: str            # on | off | '' (scenario default)
    delay: str           # on | off | ''
    months: int | None
    as_of: date | None

    @property
    def exclude_risk(self) -> bool:
        return self.scenario.exclude_risk_adjusted if self.risk == "" else self.risk == "on"

    @property
    def use_delay(self) -> bool:
        return self.scenario.use_delay_model if self.delay == "" else self.delay == "on"


def read_view(request: Request, db: Session) -> View:
    q, saved = request.query_params, dict(request.session.get("view", {}))
    if "scenario" in q and q["scenario"] != saved.get("scenario"):
        saved.pop("risk", None)            # another scenario: its own toggle defaults apply
        saved.pop("delay", None)

    def pick(name: str) -> str:
        return q[name] if name in q else saved.get(name, "")

    scenarios = list(db.scalars(select(Scenario).order_by(Scenario.is_default.desc(), Scenario.name)))
    try:
        sc = get_scenario(db, int(pick("scenario"))) if pick("scenario") else get_scenario(db)
    except (LookupError, ValueError):
        sc = get_scenario(db)
    risk = pick("risk") if pick("risk") in ("on", "off") else ""
    delay = pick("delay") if pick("delay") in ("on", "off") else ""
    months = int(pick("months")) if pick("months").isdigit() and 1 <= int(pick("months")) <= 12 else None
    try:
        as_of = date.fromisoformat(pick("as_of")) if pick("as_of") else None
    except ValueError:
        as_of = None
    request.session["view"] = {"scenario": str(sc.id), "risk": risk, "delay": delay,
                               "months": str(months or ""), "as_of": as_of.isoformat() if as_of else ""}
    return View(sc, scenarios, risk, delay, months, as_of)


def forecast_for(db: Session, v: View) -> Forecast:
    s = get_business_settings(db)
    if v.months:
        s = s.model_copy(update={"horizon_months": v.months})
    return run_forecast(db, as_of=v.as_of, scenario=v.scenario, exclude_risk=v.exclude_risk,
                        use_delay_model=v.use_delay, settings=s)


def refresh_daily_snapshot(db: Session, user_id: int | None) -> None:
    """Keep today's snapshot of the default scenario up to date after every change."""
    fc = run_forecast(db)
    save_snapshot(db, fc, user_id)
