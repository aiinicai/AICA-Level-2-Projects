import io

from flask import Blueprint, g, render_template, request, send_file

from .. import parse_date
from ..access import manager_required
from ..services import letterhead
from ..services import reports as svc

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _params():
    kind = request.args.get("type", "client_compliance")
    if kind not in svc.TYPES:
        kind = "client_compliance"
    return kind, parse_date(request.args.get("from_date")), parse_date(request.args.get("to_date"))


@bp.route("/")
@manager_required
def index():
    kind, start, end = _params()
    report = svc.build(kind, g.user, start, end)
    rows = [[svc.display(v, i in report["money_cols"]) for i, v in enumerate(r)] for r in report["rows"]]
    return render_template("reports/index.html", kind=kind, types=svc.TYPES, report=report, rows=rows, meta=svc.meta(kind, start, end),
                           from_date=request.args.get("from_date", ""), to_date=request.args.get("to_date", ""), firm=letterhead.report_profile(),
                           contact=letterhead.contact_line(letterhead.report_profile()), ids=letterhead.id_line(letterhead.report_profile()),
                           signatory=letterhead.signatory_line(letterhead.report_profile()))


def _download(fmt: str):
    kind, start, end = _params()
    report, meta = svc.build(kind, g.user, start, end), svc.meta(kind, start, end)
    if fmt == "csv":
        data, mime = svc.to_csv(report, meta), "text/csv"
    elif fmt == "xlsx":
        data, mime = svc.to_xlsx(report, meta), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        data, mime = svc.to_pdf(report, meta), "application/pdf"
    return send_file(io.BytesIO(data), as_attachment=True, download_name=f"{kind}.{fmt}", mimetype=mime)


@bp.route("/export.csv")
@manager_required
def export_csv():
    return _download("csv")


@bp.route("/export.xlsx")
@manager_required
def export_xlsx():
    return _download("xlsx")


@bp.route("/export.pdf")
@manager_required
def export_pdf():
    return _download("pdf")
