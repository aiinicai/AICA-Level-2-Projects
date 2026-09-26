"""
routes.py
---------
Flask API + page routes. Kept thin on purpose: all the real logic lives
in flux_engine.py, ai_commentary.py, review_store.py and app/exports/*.

Frontend is a single page (templates/index.html) driven by static/js/app.js
talking to these JSON endpoints.
"""

from __future__ import annotations

import os
from flask import Blueprint, jsonify, render_template, request, send_file
import io

from . import flux_engine, ai_commentary, review_store
from .exports import excel_export, pdf_export, word_export, csv_export
from .legal import PROJECT_NOTICE, SHORT_NOTICE

bp = Blueprint("main", __name__)

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


@bp.route("/")
def index():
    return render_template(
        "index.html",
        statement_types=flux_engine.STATEMENT_TYPES,
        comparison_types=flux_engine.COMPARISON_TYPES,
        legal_notice=PROJECT_NOTICE,
        short_notice=SHORT_NOTICE,
    )


def _row_to_dict(row):
    return {
        "row_id": row.row_id, "entity": row.entity, "category": row.category,
        "line_item": row.line_item, "prior_amount": row.prior_amount,
        "current_amount": row.current_amount, "variance_usd": row.variance_usd,
        "variance_pct": row.variance_pct, "is_material": bool(row.is_material),
        "severity": row.severity,
    }


def _build_run(prior_df, current_df, statement_type, comparison_type, threshold_pct, ai_enabled, api_key):
    threshold = flux_engine.MaterialityThreshold(percent=threshold_pct)
    flux_df = flux_engine.compute_flux(prior_df, current_df, threshold)

    comp = flux_engine.COMPARISON_TYPES[comparison_type]
    records = []
    for row in flux_df.itertuples(index=False):
        d = _row_to_dict(row)
        d["ai_commentary"] = ai_commentary.draft_commentary(d, statement_type, comp["phrase"], threshold_pct)
        records.append(d)

    ai_note = None
    if ai_enabled and api_key and ai_commentary.is_available():
        n_ok, n_failed = 0, 0
        for d in records:
            if d["is_material"]:
                text, err = ai_commentary.enhance_commentary(d["ai_commentary"], api_key)
                d["ai_commentary"] = text
                if err:
                    n_failed += 1
                else:
                    n_ok += 1
        ai_note = f"AI polish applied to {n_ok} line(s)" + (f"; {n_failed} fell back to rule-based text." if n_failed else ".")

    meta = {
        "statement_type": statement_type,
        "statement_label": flux_engine.STATEMENT_TYPES[statement_type],
        "comparison_type": comparison_type,
        "comparison_label": comp["label"],
        "threshold_pct": threshold_pct,
        "ai_note": ai_note,
    }
    run_id = review_store.new_run(records, meta)
    return run_id


@bp.route("/api/run", methods=["POST"])
def create_run():
    try:
        statement_type = request.form["statement_type"]
        comparison_type = request.form["comparison_type"]
        threshold_pct = float(request.form.get("threshold_pct", 10.0))
        ai_enabled = request.form.get("ai_enabled") == "true"
        api_key = request.form.get("api_key", "")

        if statement_type not in flux_engine.STATEMENT_TYPES:
            return jsonify(error="Unknown statement type."), 400
        if comparison_type not in flux_engine.COMPARISON_TYPES:
            return jsonify(error="Unknown comparison type."), 400

        prior_file = request.files.get("prior_file")
        current_file = request.files.get("current_file")
        if not prior_file or not current_file:
            return jsonify(error="Both a prior-period and current-period file are required."), 400

        prior_df = flux_engine.load_period_file(prior_file)
        current_df = flux_engine.load_period_file(current_file)

        run_id = _build_run(prior_df, current_df, statement_type, comparison_type, threshold_pct, ai_enabled, api_key)
        return jsonify(run_id=run_id, **_run_payload(run_id))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Unexpected error: {exc}"), 500


@bp.route("/api/run/sample", methods=["POST"])
def create_sample_run():
    try:
        statement_type = request.form.get("statement_type", "income_statement")
        comparison_type = request.form.get("comparison_type", "mom")
        threshold_pct = float(request.form.get("threshold_pct", 10.0))
        ai_enabled = request.form.get("ai_enabled") == "true"
        api_key = request.form.get("api_key", "")

        prefix = "income_statement" if statement_type == "income_statement" else "balance_sheet"
        prior_path = os.path.join(SAMPLE_DIR, f"{prefix}_prior.csv")
        current_path = os.path.join(SAMPLE_DIR, f"{prefix}_current.csv")

        prior_df = flux_engine.load_period_file(prior_path)
        current_df = flux_engine.load_period_file(current_path)

        run_id = _build_run(prior_df, current_df, statement_type, comparison_type, threshold_pct, ai_enabled, api_key)
        return jsonify(run_id=run_id, **_run_payload(run_id))
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Unexpected error: {exc}"), 500


def _run_payload(run_id):
    run = review_store.get_run(run_id)
    rows = []
    for row_id, entry in run["rows"].items():
        rows.append({
            **entry["data"],
            "status": entry["status"],
            "ai_commentary": entry["ai_commentary"],
            "controller_commentary": entry["controller_commentary"],
            "reviewer": entry["reviewer"],
        })
    ready, n_material, n_approved = review_store.is_ready_for_final_export(run_id)
    return {
        "meta": run["meta"],
        "rows": rows,
        "signoff": run["signoff"],
        "readiness": {"ready": ready, "n_material": n_material, "n_approved": n_approved},
    }


@bp.route("/api/run/<run_id>", methods=["GET"])
def get_run(run_id):
    run = review_store.get_run(run_id)
    if not run:
        return jsonify(error="Run not found. It may have expired — please start a new analysis."), 404
    return jsonify(run_id=run_id, **_run_payload(run_id))


@bp.route("/api/run/<run_id>/row/<row_id>", methods=["POST"])
def update_row(run_id, row_id):
    body = request.get_json(force=True)
    entry = review_store.update_row(
        run_id, row_id,
        status=body.get("status"),
        controller_commentary=body.get("controller_commentary"),
        reviewer=body.get("reviewer"),
    )
    if entry is None:
        return jsonify(error="Row or run not found."), 404
    return jsonify(run_id=run_id, **_run_payload(run_id))


@bp.route("/api/run/<run_id>/signoff", methods=["POST"])
def signoff(run_id):
    body = request.get_json(force=True)
    name = (body.get("controller_name") or "").strip()
    title = (body.get("controller_title") or "").strip()
    if not name:
        return jsonify(error="Controller name is required to sign off."), 400
    result = review_store.sign_off(run_id, name, title)
    if result is None:
        return jsonify(error="Run not found."), 404
    return jsonify(run_id=run_id, **_run_payload(run_id))


@bp.route("/api/run/<run_id>/export/<fmt>", methods=["GET"])
def export_run(run_id, fmt):
    run = review_store.get_run(run_id)
    if not run:
        return jsonify(error="Run not found."), 404

    label = run["meta"]["statement_label"].replace(" ", "")
    if fmt == "excel":
        data = excel_export.build_workbook(run)
        return send_file(io.BytesIO(data), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                          as_attachment=True, download_name=f"{label}_Flux.xlsx")
    if fmt == "pdf":
        data = pdf_export.build_pdf(run)
        return send_file(io.BytesIO(data), mimetype="application/pdf",
                          as_attachment=True, download_name=f"{label}_Flux.pdf")
    if fmt == "docx":
        data = word_export.build_docx(run)
        return send_file(io.BytesIO(data), mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          as_attachment=True, download_name=f"{label}_Flux.docx")
    if fmt == "csv":
        data = csv_export.build_csv(run)
        return send_file(io.BytesIO(data), mimetype="text/csv",
                          as_attachment=True, download_name=f"{label}_Flux.csv")
    return jsonify(error="Unknown export format."), 400


@bp.route("/api/ai-status", methods=["GET"])
def ai_status():
    return jsonify(available=ai_commentary.is_available())
