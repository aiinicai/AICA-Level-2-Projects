"""
HTTP interface.

Serves the progressive web application and the endpoints it calls.  The
API is a thin shell: every calculation lives in the engine, so the web
app, the command line and the tests all produce identical figures.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import traceback
import uuid
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .ingest import IngestError
from .narrate import draft_all
from .pipeline import DISCLAIMER, EngagementInputs, EngagementResult, run_engagement
from .report import build_workbook

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
SAMPLES_DIR = ROOT / "samples"
WORK_DIR = Path(tempfile.gettempdir()) / "auditlens"
WORK_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="AuditLens",
    description="Statutory audit analytical review for Indian companies.",
    version="1.0.0",
)

# Engagements live for the life of the process. Nothing is written to a
# database, because an audit file is not ours to keep.
ENGAGEMENTS: dict[str, EngagementResult] = {}

logger = logging.getLogger("auditlens")


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Return JSON for every failure.

    FastAPI's default 500 response is the plain text "Internal Server Error".
    The browser then tries to parse it as JSON and reports
    "Unexpected token 'I'" - which tells the user nothing at all and hides
    the real fault. Every error now arrives as JSON, naming what went wrong
    and carrying a reference that matches the server log.
    """
    reference = uuid.uuid4().hex[:8]
    logger.error(
        "Unhandled error %s on %s\n%s",
        reference, request.url.path, "".join(traceback.format_exception(exc)),
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                f"{type(exc).__name__}: {exc}"
                if str(exc) else f"{type(exc).__name__} (no message)"
            ),
            "reference": reference,
            "hint": (
                "The full traceback is in the terminal window running AuditLens, "
                f"marked with reference {reference}."
            ),
        },
    )


def _serialise(result: EngagementResult) -> dict:
    mapping_review = [
        {
            "account_code": c.account_code,
            "account_name": c.account_name,
            "head": c.head,
            "basis": c.basis,
            "confidence": c.confidence,
            "matched_on": c.matched_on,
        }
        for c in result.mapping.review
    ]

    je = result.je_analysis
    return {
        "headlines": result.headlines(),
        "disclaimer": DISCLAIMER,
        "mapping": {
            "coverage": result.mapping.coverage,
            "total": result.mapping.total,
            "by_code": result.mapping.by_code,
            "by_keyword": result.mapping.by_keyword,
            "unmapped": len(result.mapping.unmapped),
            "review": mapping_review,
        },
        "statements": {
            "balance_sheet": [asdict(line) for line in result.statements.balance_sheet],
            "profit_and_loss": [asdict(line) for line in result.statements.profit_and_loss],
            "reconciliation": result.statements.reconciliation,
            "tallies": result.statements.balance_sheet_tallies,
        },
        "ratios": [
            {
                "key": r.key,
                "name": r.name,
                "numerator_label": r.numerator_label,
                "denominator_label": r.denominator_label,
                "numerator": r.numerator,
                "denominator": r.denominator,
                "value": r.value,
                "prior_value": r.prior_value,
                "variance": r.variance,
                "unit": r.unit,
                "formatted": r.formatted(),
                "requires_explanation": r.requires_explanation,
                "basis": r.basis,
                "note": r.note,
            }
            for r in result.ratios.results
        ],
        "materiality": {
            **{
                k: v
                for k, v in asdict(result.materiality).items()
                if k != "reference"
            },
            "rows": result.materiality.as_rows(),
        },
        "je": None
        if je is None
        else {
            "total_entries": je.total_entries,
            "flagged_entries": len(je.flagged_entries),
            "tests": [
                {
                    "name": t.name,
                    "reference": t.reference,
                    "description": t.description,
                    "population": t.population,
                    "flagged": t.flagged,
                    "rate": t.rate,
                }
                for t in je.tests
            ],
            "benford": {
                "observed_pct": {str(k): v for k, v in je.benford.observed_pct.items()},
                "expected": {str(k): v for k, v in je.benford.expected.items()},
                "mad": je.benford.mad,
                "total": je.benford.total,
                "conforms": je.benford.conforms,
                "conclusion": je.benford.conclusion,
            },
            "flags": [
                {
                    "entry_id": f.entry_id,
                    "test": f.test,
                    "reason": f.reason,
                    "amount": f.amount,
                    "posting_date": f.posting_date.isoformat() if f.posting_date else None,
                    "posted_by": f.posted_by,
                    "severity": f.severity,
                }
                for f in sorted(je.all_flags, key=lambda x: -x.amount)
            ],
        },
        "sample": None
        if result.sample is None
        else {
            "population_size": result.sample.population_size,
            "population_value": result.sample.population_value,
            "sampling_interval": result.sample.sampling_interval,
            "random_start": result.sample.random_start,
            "seed": result.sample.seed,
            "sample_size": result.sample.sample_size,
            "coverage": result.sample.coverage,
            "warnings": result.sample.warnings,
            "items": [asdict(i) for i in result.sample.items[:200]],
        },
        "caro": None
        if result.caro is None
        else {
            "applies": result.caro.applicability.applies,
            "reasons": result.caro.applicability.reasons,
            "prefilled": result.caro.prefilled_count,
            "clauses": [asdict(c) for c in result.caro.clauses],
        },
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "engagements": len(ENGAGEMENTS)}


@app.get("/api/sample-files")
def sample_files() -> dict:
    """The synthetic client shipped with the project, for demonstration."""
    return {
        "client": "Bharat Precision Components Private Limited",
        "note": "Fictitious. No client data is used anywhere in this project.",
        "files": [p.name for p in sorted(SAMPLES_DIR.glob("*.csv"))],
    }


@app.post("/api/engagements")
async def create_engagement(
    client_name: str = Form(...),
    financial_year: str = Form(...),
    year_end: str = Form(...),
    company_class: str = Form("private"),
    principal_repayments: float = Form(0.0),
    credit_sales_ratio: float = Form(1.0),
    credit_purchase_ratio: float = Form(1.0),
    working_capital_limit: float = Form(0.0),
    materiality_benchmark: str = Form(""),
    materiality_percentage: float = Form(0.0),
    performance_pct: float = Form(0.75),
    use_samples: bool = Form(False),
    trial_balance: UploadFile | None = File(None),
    prior_trial_balance: UploadFile | None = File(None),
    general_ledger: UploadFile | None = File(None),
) -> JSONResponse:
    """Run an analytical review and return the whole result."""
    engagement_id = uuid.uuid4().hex[:12]
    folder = WORK_DIR / engagement_id
    folder.mkdir(parents=True, exist_ok=True)

    async def save(upload: UploadFile | None, name: str) -> Path | None:
        if upload is None or not upload.filename:
            return None
        destination = folder / f"{name}{Path(upload.filename).suffix or '.csv'}"
        with destination.open("wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        return destination

    if use_samples:
        tb_path = SAMPLES_DIR / "trial_balance_FY2024-25.csv"
        prior_path = SAMPLES_DIR / "trial_balance_FY2023-24.csv"
        gl_path = SAMPLES_DIR / "general_ledger_FY2024-25.csv"
    else:
        tb_path = await save(trial_balance, "trial_balance")
        prior_path = await save(prior_trial_balance, "prior_trial_balance")
        gl_path = await save(general_ledger, "general_ledger")

    if tb_path is None:
        raise HTTPException(status_code=400, detail="A trial balance is required.")

    try:
        parsed_year_end = datetime.strptime(year_end, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Year end must be supplied as YYYY-MM-DD."
        )

    inputs = EngagementInputs(
        client_name=client_name,
        financial_year=financial_year,
        year_end=parsed_year_end,
        company_class=company_class,
        principal_repayments=principal_repayments,
        credit_sales_ratio=credit_sales_ratio,
        credit_purchase_ratio=credit_purchase_ratio,
        working_capital_limit=working_capital_limit,
        materiality_benchmark=materiality_benchmark or None,
        materiality_percentage=materiality_percentage or None,
        performance_pct=performance_pct,
    )

    try:
        result = run_engagement(
            inputs=inputs,
            trial_balance_path=tb_path,
            prior_trial_balance_path=prior_path,
            general_ledger_path=gl_path,
        )
    except IngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    ENGAGEMENTS[engagement_id] = result
    payload = _serialise(result)
    payload["engagement_id"] = engagement_id
    return JSONResponse(payload)


@app.get("/api/engagements/{engagement_id}")
def get_engagement(engagement_id: str) -> JSONResponse:
    result = ENGAGEMENTS.get(engagement_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Engagement not found.")
    payload = _serialise(result)
    payload["engagement_id"] = engagement_id
    return JSONResponse(payload)


@app.post("/api/engagements/{engagement_id}/drafts")
def generate_drafts(engagement_id: str) -> dict:
    """Draft the memorandum, the ratio notes and the enquiry letter."""
    result = ENGAGEMENTS.get(engagement_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Engagement not found.")

    drafts = draft_all(result)
    return {
        "memorandum": asdict(drafts["memorandum"]),
        "ratio_notes": [asdict(d) for d in drafts["ratio_notes"]],
        "je_enquiry": asdict(drafts["je_enquiry"]),
    }


@app.get("/api/engagements/{engagement_id}/workbook")
def download_workbook(engagement_id: str) -> FileResponse:
    result = ENGAGEMENTS.get(engagement_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Engagement not found.")

    name = (
        f"AuditLens_{result.inputs.client_name.split()[0]}_"
        f"{result.inputs.financial_year.replace('-', '_')}.xlsx"
    )
    path = WORK_DIR / engagement_id / name
    path.parent.mkdir(parents=True, exist_ok=True)
    build_workbook(result, path)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=name,
    )


# The web application is served last so that /api routes take precedence.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
