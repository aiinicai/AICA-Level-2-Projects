"""
AI adapter package — populated in Stage 16, structurally isolated from
the rule engines (Blueprint Section A.2, item 7 / Ambiguity #7).

ai_adapter.py exposes a single interface (explain(finding) -> text). It
must never be called implicitly by rule_runner_service or any rule pack
— only from an explicit, per-finding, per-click user action.
"""
