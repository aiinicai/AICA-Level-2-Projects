"""Builds a core.ai_provider.AIProvider from persisted settings.

Used by any tab (AI Assistant, and future features) that needs "whichever
AI provider the user configured in Settings," as opposed to the Settings
tab itself, which edits the provider config directly.
"""
from __future__ import annotations

from core.ai_provider import AIProvider, AIProviderKind, DEFAULT_MODELS, is_configured
from ui.app_context import AppContext


def get_configured_provider(ctx: AppContext) -> AIProvider:
    s = ctx.config.settings
    kind = AIProviderKind(s.ai_provider)
    model = s.ai_model or DEFAULT_MODELS[kind]
    return AIProvider(kind, model=model, ollama_base_url=s.ai_ollama_base_url)


def is_ai_ready(ctx: AppContext) -> bool:
    s = ctx.config.settings
    kind = AIProviderKind(s.ai_provider)
    return is_configured(kind)
