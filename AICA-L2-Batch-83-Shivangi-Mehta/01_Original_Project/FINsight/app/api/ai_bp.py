"""
AI Explanation blueprint — internal/cross-cutting JSON API, not a
top-level nav destination (it's a modal within the Finding Detail
drawer per Blueprint Section 8). Implemented in Stage 16.

AI is OFF by default (Config.AI_ENABLED = False) and every explanation
call must be per-finding, per-click, with redaction on by default per
Blueprint Ambiguity #7 — this blueprint must never call an AI provider
implicitly from anywhere else in the app.
"""
from flask import Blueprint, jsonify

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.route("/ping")
def ping():
    return jsonify(status="stub", area="ai", enabled=False)
