"""Offline-safe pre-demo provider, cache, and budget sanity report."""

from __future__ import annotations

import json
import sys
from pathlib import Path


SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from amg.config import get_settings
from amg.providers.budget import budget_report
from amg.providers.cache import cache_entry_count


def main() -> None:
    """Print configuration state without constructing or calling any provider."""

    settings = get_settings()
    usage = budget_report()
    print(f"Offline mode: {'ON' if settings.offline else 'OFF'}")
    print(f"Resolved LLM provider: {settings.resolved_llm_provider()}")
    print(f"Resolved embedding provider: {settings.resolved_embed_provider()}")
    print(f"GEMINI_API_KEY present: {'yes' if settings.gemini_api_key else 'no'}")
    print(f"VOYAGE_API_KEY present: {'yes' if settings.voyage_api_key else 'no'}")
    print(f"Cache mode: {settings.cache_mode}")
    print(f"Cache entries: {cache_entry_count()}")
    print(
        "Budget today (UTC): "
        f"{usage['calls_used']}/{usage['cap']} calls used; "
        f"{usage['remaining']} remaining"
    )
    print(f"Budget by provider/model: {json.dumps(usage['providers'], sort_keys=True)}")


if __name__ == "__main__":
    main()
