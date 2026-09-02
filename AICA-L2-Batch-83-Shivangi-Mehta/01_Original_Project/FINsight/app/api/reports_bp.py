"""
Report Centre blueprint (Blueprint Section E, #17).

CORRECTION: this module's docstring previously claimed "Real routes
implemented in Stage 15, generating PDF (ReportLab) and Excel
(OpenPyXL) reports" — that was never true; the route below has always
rendered a placeholder only. Flagged and fixed here rather than left to
mislead a future reader: no PDF/Excel report generation exists in
FinSight V1. See documentation/finsight_v1_scope.md.

Renders a SEBI-deferred-style "future module" notice (mirroring
app/api/sebi_bp.py's own wording/pattern) naming the three statutory
reports a future FinSight version is expected to cover: the Auditor's
Report, CARO (where applicable), and the Tax Audit Report.
"""
from flask import Blueprint, render_template

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
def index():
    return render_template("reports/deferred.html", section="Reports")
