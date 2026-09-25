"""Read endpoints, one per tab. Each returns everything that tab needs so the
frontend makes a single call per screen."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.models import User
from app.routers.deps import get_ctx
from app.services import (
    burn, capital, cashcalendar, liquidity, payables, people, receivables,
    runway, today as today_svc, variance,
)
from app.services.common import Ctx

router = APIRouter(prefix="/api", tags=["tabs"])


# --- TAB 1 -----------------------------------------------------------------
@router.get("/today")
def tab_today(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    return today_svc.dashboard(ctx)


# --- TAB 2 -----------------------------------------------------------------
@router.get("/runway-burn")
def tab_runway_burn(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    return {
        "runway": {
            "summary": runway.runway_summary(ctx),
            "movement": runway.runway_movement(ctx),
            "milestones": runway.milestones(ctx),
        },
        "burn": {
            "summary": burn.burn_summary(ctx),
            "recurring_vs_one_off": burn.recurring_vs_one_off(ctx),
            "by_category": burn.burn_by_category(ctx),
            "per_unit": burn.burn_per_unit(ctx),
            "monthly": burn.monthly_burn(ctx, months=18, normalised=False),
            "monthly_normalised": burn.monthly_burn(ctx, months=18, normalised=True),
        },
        "people": people.people_cost(ctx),
        "as_on": ctx.as_on.isoformat(),
    }


# --- TAB 3 -----------------------------------------------------------------
@router.get("/liquidity")
def tab_liquidity(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    return {
        "where_the_money_is": liquidity.where_the_money_is(ctx),
        "health": liquidity.health_score(ctx),
        "ratios": liquidity.ratios(ctx),
        "score_history": liquidity.score_history(ctx),
        "as_on": ctx.as_on.isoformat(),
    }


# --- TAB 4 -----------------------------------------------------------------
@router.get("/money-in")
def tab_money_in(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    return {
        "summary": receivables.summary(ctx),
        "ageing": receivables.ageing(ctx),
        "by_client": receivables.by_client(ctx),
        "concentration": receivables.concentration(ctx),
        "disputes": receivables.disputes(ctx),
        "collection_performance": receivables.collection_performance(ctx),
        "invoicing_gap": receivables.invoicing_gap(ctx),
        "as_on": ctx.as_on.isoformat(),
    }


# --- TAB 5 -----------------------------------------------------------------
@router.get("/money-out")
def tab_money_out(horizon_days: int = Query(30, ge=7, le=120),
                  ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    return {
        "obligations": payables.obligations(ctx, horizon_days=horizon_days),
        "statutory": payables.statutory(ctx, horizon_days=horizon_days),
        "commitments": payables.commitments(ctx),
        "vendors": payables.vendor_position(ctx),
        "as_on": ctx.as_on.isoformat(),
    }


# --- TAB 6 -----------------------------------------------------------------
@router.get("/cash-calendar")
def tab_cash_calendar(weeks: int = Query(13, ge=4, le=26),
                      ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    return cashcalendar.build_forecast(ctx, weeks=weeks)


# --- TAB 7 -----------------------------------------------------------------
@router.get("/plan-vs-actual")
def tab_plan_vs_actual(plan_id: int | None = None,
                       ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    data = variance.plan_vs_actual(ctx, plan_id=plan_id)
    data["plans"] = variance.plan_list(ctx)
    return data


# --- TAB 9 -----------------------------------------------------------------
@router.get("/capital-debt")
def tab_capital_debt(ctx: Ctx = Depends(get_ctx), user: User = Depends(get_current_user)):
    return {
        "facilities": capital.facilities(ctx),
        "repayment_calendar": capital.repayment_calendar(ctx),
        "covenants": capital.covenants(ctx),
        "funding_history": capital.funding_history(ctx),
        "next_raise": capital.next_raise(ctx),
        "as_on": ctx.as_on.isoformat(),
    }
