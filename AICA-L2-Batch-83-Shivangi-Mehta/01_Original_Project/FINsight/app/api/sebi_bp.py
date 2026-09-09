"""
SEBI/LODR Review blueprint — Review > SEBI (Blueprint Section E, #12).

Stage 11 scope change (approved): FinSight V1 does NOT implement SEBI /
Listed Entity review. This was originally going to be a conditional
module (relevant once an engagement's entity_profile has is_listed =
True and the applicability matrix confirms it — Blueprint Section
2.11), with real routes planned for Stage 11 and gated the same way as
Tax (Blueprint Section 6). That plan is DEFERRED, not built, per the
explicit V1 scope decision — see documentation/finsight_v1_scope.md.

This blueprint is kept registered (not removed) so a stray/typed-in URL
to /review/sebi/ gets a clear, honest "outside current scope" message
rather than a 404 or, worse, a page that looks like a working feature.
It performs no SEBI analysis, produces no findings, and is not linked
from the nav (base.html shows a static, non-clickable "Future Module"
label instead) — see app/api/dashboard_bp.py and app/api/engagement_bp.py
for the corresponding V1 scope changes elsewhere.
"""
from flask import Blueprint, render_template

sebi_bp = Blueprint("sebi", __name__, url_prefix="/review/sebi")


@sebi_bp.route("/")
def index():
    return render_template("sebi/deferred.html", section="Review › SEBI")
