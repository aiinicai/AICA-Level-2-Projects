"""
Risk blueprint — internal/cross-cutting JSON API, not a top-level nav
destination (the approved nav, Blueprint Section 8, has no standalone
Risk screen; risk factor breakdowns render inside the Finding Detail
drawer). Implemented alongside Stage 12 ("Risk engine").
"""
from flask import Blueprint, jsonify

risk_bp = Blueprint("risk", __name__, url_prefix="/api/risk")


@risk_bp.route("/ping")
def ping():
    return jsonify(status="stub", area="risk")
