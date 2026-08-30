"""
AI provider implementations.

disabled_provider.py is the default (AI_ENABLED = False) and must be a
true no-op. external_api_provider.py is only imported when AI is
explicitly enabled in Settings, and must apply redaction by default
(Blueprint Ambiguity #7) before sending anything off-machine.
"""
