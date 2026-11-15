from flask import Blueprint, Response, g, jsonify, request

from ..access import login_required
from ..services import lookup as svc

bp = Blueprint("lookup", __name__, url_prefix="/lookup")


@bp.route("/pincode/<pin>")
@login_required
def pincode(pin):
    return jsonify(svc.pincode(pin))


@bp.route("/gst/captcha")
@login_required
def gst_captcha():
    try:
        data, mime = svc.gst_captcha(g.user.id)
    except svc.LookupError_ as e:
        return jsonify(ok=False, message=str(e)), 502
    return Response(data, mimetype=mime, headers={"Cache-Control": "no-store"})


@bp.route("/gst", methods=["POST"])
@login_required
def gst():
    body = request.get_json(silent=True) or {}
    return jsonify(svc.gst_details(g.user.id, body.get("gstin", ""), body.get("captcha", "")))


@bp.route("/gst/history", methods=["POST"])
@login_required
def gst_history():
    """Fill a client's GST tracker from the filing table on the GST portal's public search page."""
    from .. import log_activity
    from ..access import get_client_or_403
    from ..models import db

    body = request.get_json(silent=True) or {}
    client = get_client_or_403(g.user, int(body.get("client_id") or 0))
    if not client.gstin:
        return jsonify(ok=False, message="This client has no GSTIN.")
    found = svc.gst_filing_history(g.user.id, client.gstin, body.get("captcha", ""))
    if not found.get("ok"):
        return jsonify(found)
    result = svc.save_filings(client, found["rows"])
    log_activity("gst", f"Fetched GST filing history of {client.name} from the portal: {result['created']} added, {result['updated']} updated")
    db.session.commit()
    return jsonify(ok=True, **result)
