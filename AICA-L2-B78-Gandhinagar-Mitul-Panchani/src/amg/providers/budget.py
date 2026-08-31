"""UTC-daily live-call ledger and hard quota boundary."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path

from amg.config import writable_app_path


logger = logging.getLogger(__name__)
USAGE_PATH = writable_app_path(".amg_usage.json")
_LOCK = threading.Lock()


class BudgetExceeded(RuntimeError):
    """Quota policy blocked a call before outbound provider I/O."""


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _read_ledger(path: Path) -> dict[str, object]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"dates": {}}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Usage ledger is unreadable; starting a fresh ledger: %s", exc)
        return {"dates": {}}
    if not isinstance(loaded, dict) or not isinstance(loaded.get("dates"), dict):
        logger.warning("Usage ledger has an invalid shape; starting a fresh ledger")
        return {"dates": {}}
    return loaded


def _write_ledger(path: Path, ledger: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary_path = Path(handle.name)
    try:
        with handle:
            json.dump(ledger, handle, sort_keys=True, indent=2)
            handle.write("\n")
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _day_entry(ledger: dict[str, object], date: str) -> dict[str, object]:
    dates = ledger.setdefault("dates", {})
    assert isinstance(dates, dict)
    day = dates.setdefault(date, {"providers": {}})
    assert isinstance(day, dict)
    day.setdefault("providers", {})
    return day


def _calls_used(day: dict[str, object]) -> int:
    providers = day.get("providers", {})
    if not isinstance(providers, dict):
        return 0
    return sum(
        int(model_totals.get("calls", 0))
        for models in providers.values()
        if isinstance(models, dict)
        for model_totals in models.values()
        if isinstance(model_totals, dict)
    )


def record_live_call(provider: str, model: str, cap: int) -> None:
    """Atomically reserve one call before outbound I/O, blocking call cap+1."""

    with _LOCK:
        ledger = _read_ledger(USAGE_PATH)
        day = _day_entry(ledger, _today())
        used = _calls_used(day)
        if used >= cap:
            logger.warning(
                "Daily live provider call cap reached (%s/%s); blocking %s/%s",
                used,
                cap,
                provider,
                model,
            )
            raise BudgetExceeded(
                f"Daily live provider call cap reached ({used}/{cap})"
            )
        providers = day["providers"]
        assert isinstance(providers, dict)
        models = providers.setdefault(provider, {})
        assert isinstance(models, dict)
        totals = models.setdefault(model, {"calls": 0, "tokens": 0})
        assert isinstance(totals, dict)
        totals["calls"] = int(totals.get("calls", 0)) + 1
        totals["tokens"] = int(totals.get("tokens", 0))
        try:
            _write_ledger(USAGE_PATH, ledger)
        except OSError as exc:
            logger.warning("Usage ledger could not reserve a live call: %s", exc)
            raise BudgetExceeded("Usage ledger unavailable; live call blocked") from exc


def record_tokens(provider: str, model: str, token_count: int | None) -> None:
    """Add provider-reported tokens to a call that was already reserved."""

    if token_count is None or token_count <= 0:
        return
    with _LOCK:
        ledger = _read_ledger(USAGE_PATH)
        day = _day_entry(ledger, _today())
        providers = day["providers"]
        assert isinstance(providers, dict)
        models = providers.setdefault(provider, {})
        assert isinstance(models, dict)
        totals = models.setdefault(model, {"calls": 0, "tokens": 0})
        assert isinstance(totals, dict)
        totals["tokens"] = int(totals.get("tokens", 0)) + token_count
        try:
            _write_ledger(USAGE_PATH, ledger)
        except OSError as exc:
            # The call count was already safely persisted before outbound I/O.
            # Missing token telemetry should not discard a valid live response.
            logger.warning("Usage ledger could not record provider tokens: %s", exc)


def budget_report() -> dict[str, object]:
    """Return today's aggregate and per-provider usage for UI/CLI display."""

    from amg.config import get_settings

    cap = get_settings().daily_live_call_cap
    with _LOCK:
        ledger = _read_ledger(USAGE_PATH)
        day = _day_entry(ledger, _today())
        used = _calls_used(day)
        providers = day.get("providers", {})
        provider_totals: dict[str, object] = {}
        if isinstance(providers, dict):
            for provider, models in providers.items():
                if not isinstance(models, dict):
                    continue
                provider_totals[str(provider)] = {
                    "calls": sum(
                        int(totals.get("calls", 0))
                        for totals in models.values()
                        if isinstance(totals, dict)
                    ),
                    "tokens": sum(
                        int(totals.get("tokens", 0))
                        for totals in models.values()
                        if isinstance(totals, dict)
                    ),
                    "models": models,
                }
        return {
            "date": _today(),
            "calls_used": used,
            "cap": cap,
            "remaining": max(0, cap - used),
            "providers": provider_totals,
        }
