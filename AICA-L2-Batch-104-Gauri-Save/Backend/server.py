"""
Orchestrates: agreement + invoices + revenue schedules -> extraction -> reconciliation -> narrative -> Word memo.
"""

import os
import sys
import json
import time
import uuid
import traceback
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from extraction import process_document
from reconciliation import reconcile_all
from agent import generate_batch_narrative
from memo_builder import build_batch_memo

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads_tmp")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

app = Flask(__name__)
CORS(app)


def _allowed(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def run_pipeline(agreement_path: str, invoice_paths: list[str], revenue_schedule_paths: list[str],
                  display_names: dict = None) -> dict:
    """
    display_names: optional {path: original_filename} map so that internal
    uniqueness prefixes added to on-disk paths (to prevent collisions between
    concurrent uploads) don't leak into what the user sees in results/memo.
    """
    agreement = process_document(agreement_path, "agreement")
    invoices = [process_document(p, "invoice") for p in invoice_paths]
    revenue_schedules = [process_document(p, "revenue_schedule") for p in revenue_schedule_paths]

    if display_names:
        agreement.filename = display_names.get(agreement_path, agreement.filename)
        for inv, path in zip(invoices, invoice_paths):
            inv.filename = display_names.get(path, inv.filename)
        for sched, path in zip(revenue_schedules, revenue_schedule_paths):
            sched.filename = display_names.get(path, sched.filename)

    reconciliations = reconcile_all(agreement, invoices, revenue_schedules)

    try:
        narrative = generate_batch_narrative(reconciliations)
    except Exception as e:
        status_counts = {}
        for r in reconciliations:
            status_counts[r.status] = status_counts.get(r.status, 0) + 1
        narrative = {
            "executive_summary": f"[Narrative generation unavailable: {e}] "
                                  f"Status breakdown: {status_counts}. See detailed findings below.",
            "prioritized_items": [
                f"{r.invoice.filename}: {r.status}" for r in reconciliations if r.status in ("CRITICAL", "FLAG")
            ],
            "recommended_next_steps": [
                "Retry narrative generation once connectivity/API access is confirmed.",
                "Review detailed findings directly in the meantime.",
            ],
        }

    # Bug fix: previously the memo filename was derived only from the agreement's
    # original filename, so two different uploads named e.g. "agreement.pdf" would
    # overwrite each other's output, and /api/download/<filename> had no way to
    # distinguish them. A short unique suffix prevents both the collision and the
    # ability to guess/access another run's file.
    base_name = agreement.filename.rsplit('.', 1)[0]
    unique_suffix = uuid.uuid4().hex[:8]
    filename = f"Invoice_Reconciliation_{base_name}_{unique_suffix}.docx"
    output_path = os.path.join(OUTPUT_DIR, filename)
    build_batch_memo(agreement, reconciliations, narrative, output_path, revenue_schedules=revenue_schedules)

    return {
        "agreement": {
            "filename": agreement.filename,
            "provider_name": agreement.provider_name,
            "recipient_name": agreement.recipient_name,
            "currency": agreement.currency,
            "term": f"{agreement.period_start} to {agreement.period_end}",
            "fee_percentage": agreement.fee_percentage,
        },
        "revenue_schedules": [
            {
                "filename": s.filename,
                "month": s.schedule_month,
                "operating_revenue": s.operating_revenue,
                "extraordinary_income": s.extraordinary_income,
                "total_revenue": s.total_revenue,
            }
            for s in revenue_schedules
        ],
        "invoices": [
            {
                "filename": r.invoice.filename,
                "extraction_method": r.invoice.extraction_method,
                "status": r.status,
                "findings": [
                    {"severity": f.severity, "check": f.check, "detail": f.detail}
                    for f in r.findings
                ],
            }
            for r in reconciliations
        ],
        "narrative": narrative,
        "memo_filename": filename,
    }


@app.route("/api/reconcile", methods=["POST"])
def reconcile_endpoint():
    try:
        if "agreement" not in request.files:
            return jsonify({"ok": False, "error": "No agreement file provided."}), 400
        invoice_files = request.files.getlist("invoices")
        if not invoice_files:
            return jsonify({"ok": False, "error": "No invoice files provided."}), 400
        # Revenue schedules are optional in the request, but strongly recommended —
        # without them, every invoice will fall back to a REVIEW "No Reference Data"
        # finding since there is nothing to compute an expected fee against.
        revenue_schedule_files = request.files.getlist("revenue_schedules")

        agreement_file = request.files["agreement"]
        if not _allowed(agreement_file.filename):
            return jsonify({"ok": False, "error": "Unsupported agreement file type."}), 400

        # Bug fix: prefix with a run-specific ID so concurrent uploads with the same
        # original filename (e.g. everyone naming their file "agreement.pdf") don't
        # overwrite each other on disk mid-request. display_names maps the prefixed
        # on-disk path back to the clean original filename so the prefix never leaks
        # into what the user sees in the results or the generated memo.
        run_id = uuid.uuid4().hex[:8]
        display_names = {}

        agreement_path = os.path.join(UPLOAD_DIR, f"{run_id}_{secure_filename(agreement_file.filename)}")
        agreement_file.save(agreement_path)
        display_names[agreement_path] = agreement_file.filename

        invoice_paths = []
        for f in invoice_files:
            if not _allowed(f.filename):
                continue
            path = os.path.join(UPLOAD_DIR, f"{run_id}_{secure_filename(f.filename)}")
            f.save(path)
            invoice_paths.append(path)
            display_names[path] = f.filename

        if not invoice_paths:
            return jsonify({"ok": False, "error": "No valid invoice files after filtering."}), 400

        revenue_schedule_paths = []
        for f in revenue_schedule_files:
            if not _allowed(f.filename):
                continue
            path = os.path.join(UPLOAD_DIR, f"{run_id}_{secure_filename(f.filename)}")
            f.save(path)
            revenue_schedule_paths.append(path)
            display_names[path] = f.filename

        result = run_pipeline(agreement_path, invoice_paths, revenue_schedule_paths, display_names=display_names)
        return jsonify({"ok": True, **result})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/download/<path:filename>", methods=["GET"])
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "invoice-consistency-checker-backend"})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli-test":
        import glob
        agreement_path = "../sample_docs/agreement_management_services.pdf"
        invoice_paths = sorted(glob.glob("../sample_docs/invoice_*"))
        revenue_schedule_paths = sorted(glob.glob("../sample_docs/revenue_schedule_*"))
        out = run_pipeline(agreement_path, invoice_paths, revenue_schedule_paths)
        print(json.dumps(out, indent=2))
    else:
        app.run(host="0.0.0.0", port=5002, debug=True)
