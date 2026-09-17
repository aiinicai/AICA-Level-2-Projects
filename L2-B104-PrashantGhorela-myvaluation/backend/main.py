from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from datetime import datetime

import json
import shutil
import re
import hashlib


# =========================================================
# INTERNAL MODULES
# =========================================================

from valuation_engine import (
    calculate_dcf,
    calculate_dcf_sensitivity,
    calculate_nav,
    calculate_weighted_value,
    calculate_value_per_share,
)

from output_generator import (
    generate_excel_working,
    generate_word_report,
)

from financial_extractor import (
    extract_assignment_financials,
)

from financial_analysis_engine import (
    analyze_normalized_financials,
)

from market_data_engine import (
    suggest_market_data,
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="myvaluation API",
    version="1.7"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = (
    BASE_DIR /
    "data"
)

DATA_DIR.mkdir(
    exist_ok=True
)


# =========================================================
# HELPERS
# =========================================================

def safe_filename(
    value: str
) -> str:

    value = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        value.strip()
    )

    return (
        value.strip("_")
        or "company"
    )


def next_assignment_id() -> str:

    year = datetime.now().year

    existing = []

    for folder in DATA_DIR.glob(
        f"VAL-{year}-*"
    ):

        try:

            number = int(
                folder.name
                .split("-")[-1]
            )

            existing.append(
                number
            )

        except Exception:
            pass

    next_number = (
        max(
            existing,
            default=0
        )
        + 1
    )

    return (
        f"VAL-{year}-"
        f"{next_number:03d}"
    )


async def save_files(
    files: Optional[
        List[UploadFile]
    ],
    folder: Path
):

    saved = []

    if not files:
        return saved

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    for upload in files:

        if not upload.filename:
            continue

        destination = (
            folder /
            upload.filename
        )

        with destination.open(
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                upload.file,
                buffer
            )

        saved.append(
            upload.filename
        )

    return saved


def get_assignment_folder(
    assignment_id: str
) -> Path:

    assignment_id = (
        assignment_id
        .strip()
        .upper()
    )

    folder = (
        DATA_DIR /
        assignment_id
    )

    if not folder.exists():

        raise HTTPException(
            status_code=404,
            detail="Assignment not found."
        )

    return folder


def load_assignment(
    assignment_id: str
) -> dict:

    folder = (
        get_assignment_folder(
            assignment_id
        )
    )

    assignment_file = (
        folder /
        "assignment.json"
    )

    if not assignment_file.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Assignment data "
                "not found."
            )
        )

    with assignment_file.open(
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(
            file
        )


def save_json(
    file_path: Path,
    data: dict
):

    with file_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
            default=str
        )


# =========================================================
# REVIEW / DATA VALIDATION HELPERS
# =========================================================

def make_review_item_id(
    item: dict
) -> str:

    identity = "|".join([
        str(item.get("file_name", "")),
        str(item.get("sheet", "")),
        str(item.get("row", "")),
        str(item.get("source_label", "")),
        str(item.get("canonical_field", "")),
        str(item.get("reason", "")),
    ])

    return hashlib.sha1(
        identity.encode("utf-8")
    ).hexdigest()[:16]


def review_log_path(
    assignment_folder: Path
) -> Path:

    return (
        assignment_folder /
        "review_log.json"
    )


def load_review_log(
    assignment_folder: Path
) -> dict:

    path = review_log_path(
        assignment_folder
    )

    if not path.exists():
        return {
            "items": {},
            "updated_at": None,
        }

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {
                "items": {},
                "updated_at": None,
            }

        data.setdefault(
            "items",
            {}
        )

        return data

    except Exception:
        return {
            "items": {},
            "updated_at": None,
        }


def is_material_review_item(
    item: dict
) -> bool:

    sheet_type = str(
        item.get(
            "sheet_type",
            ""
        )
    ).lower()

    statement = str(
        item.get(
            "statement",
            ""
        )
    ).lower()

    material_types = {
        "profit_and_loss",
        "balance_sheet",
        "cash_flow",
        "projected_profit_and_loss",
        "projected_balance_sheet",
        "projected_cash_flow",
        "debt_schedule",
        "capital_structure",
    }

    if sheet_type in material_types:
        return True

    if statement in {
        "income_statement",
        "balance_sheet",
        "cash_flow",
    }:
        return True

    return False


def decorate_review_items(
    raw_items: list,
    review_log: dict
) -> list:

    decisions = review_log.get(
        "items",
        {}
    )

    decorated = []

    for raw in raw_items:

        item = dict(raw)

        item_id = make_review_item_id(
            item
        )

        decision = decisions.get(
            item_id,
            {}
        )

        item[
            "review_id"
        ] = item_id

        item[
            "review_status"
        ] = decision.get(
            "status",
            "pending"
        )

        item[
            "review_note"
        ] = decision.get(
            "note",
            ""
        )

        item[
            "reviewed_at"
        ] = decision.get(
            "updated_at"
        )

        item[
            "material"
        ] = is_material_review_item(
            item
        )

        decorated.append(
            item
        )

    return decorated


def build_review_summary(
    review_items: list,
    cross_checks: list,
    capital_structure: Optional[dict] = None,
) -> dict:

    resolved_statuses = {
        "reviewed",
        "accepted",
        "ignored",
    }

    total = len(
        review_items
    )

    unresolved = sum(
        1
        for item in review_items
        if item.get(
            "review_status",
            "pending"
        ) not in resolved_statuses
    )

    unresolved_material = sum(
        1
        for item in review_items
        if item.get(
            "material",
            False
        )
        and item.get(
            "review_status",
            "pending"
        ) not in resolved_statuses
    )

    failed_cross_checks = sum(
        1
        for check in cross_checks
        if str(
            check.get(
                "status",
                ""
            )
        ).upper() != "OK"
    )

    capital_checks = (
        (capital_structure or {})
        .get(
            "checks",
            []
        )
    )

    failed_capital_checks = sum(
        1
        for check in capital_checks
        if str(
            check.get(
                "status",
                ""
            )
        ).upper() != "OK"
    )

    data_ready = (
        unresolved_material == 0
        and failed_cross_checks == 0
        and failed_capital_checks == 0
    )

    return {
        "total": total,
        "unresolved": unresolved,
        "resolved": total - unresolved,
        "unresolved_material": unresolved_material,
        "failed_cross_checks": failed_cross_checks,
        "failed_capital_checks": failed_capital_checks,
        "data_ready_for_valuation": data_ready,
        "draft_work_allowed": True,
        "final_report_ready": data_ready,
    }


# =========================================================
# PYDANTIC MODELS
# =========================================================

class ProjectionRow(
    BaseModel
):

    year: str

    ebit: float

    depreciation: float

    capex: float

    change_working_capital: float


class WACCRequest(
    BaseModel
):

    risk_free_rate_percent: float

    equity_risk_premium_percent: float

    beta: float

    company_specific_risk_premium_percent: float = 0

    pre_tax_cost_of_debt_percent: float

    tax_rate_percent: float

    equity_weight_percent: float

    debt_weight_percent: float

    market_data_date: str = ""

    risk_free_source: str = ""

    erp_source: str = ""

    beta_source: str = ""

    debt_source: str = ""

    notes: str = ""


class DCFRequest(
    BaseModel
):

    projections: List[
        ProjectionRow
    ]

    tax_rate: float

    wacc: float

    terminal_growth: float

    cash: float

    debt: float

    non_operating_assets: float = 0

    diluted_shares: float


class NAVRequest(
    BaseModel
):

    adjusted_assets: float

    adjusted_liabilities: float

    diluted_shares: float


class WeightageRow(
    BaseModel
):

    method: str

    value: float

    weight: float


class WeightageRequest(
    BaseModel
):

    methods: List[
        WeightageRow
    ]

    diluted_shares: float


class ReviewUpdateRequest(
    BaseModel
):

    review_id: str

    status: str

    note: str = ""


class OutputRequest(
    BaseModel
):

    assignment_id: str

    projections: List[
        ProjectionRow
    ]

    tax_rate_percent: float

    wacc_percent: float

    terminal_growth_percent: float

    cash: float

    debt: float

    non_operating_assets: float

    diluted_shares: float

    adjusted_assets: float

    adjusted_liabilities: float

    dcf_weight: float

    nav_weight: float

    wacc_analysis: Optional[dict] = None


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "message":
            "myvaluation backend is running",
        "version":
            "1.7",
    }


# =========================================================
# CREATE ASSIGNMENT
# =========================================================

@app.post("/assignments")
async def create_assignment(

    company_name: str = Form(...),

    cin: str = Form(""),

    pan: str = Form(""),

    valuation_date: str = Form(...),

    engagement_date: str = Form(...),

    report_date: str = Form(...),

    purpose: str = Form(...),

    security_type: str = Form(...),

    applicable_provision: str = Form(...),

    transaction_details: str = Form(...),

    contact_name: str = Form(...),

    designation: str = Form(""),

    mobile: str = Form(...),

    email: str = Form(...),

    provisional_files:
        Optional[
            List[UploadFile]
        ] = File(None),

    historical_files:
        Optional[
            List[UploadFile]
        ] = File(None),

    projection_files:
        Optional[
            List[UploadFile]
        ] = File(None),

    capital_structure_files:
        Optional[
            List[UploadFile]
        ] = File(None),

    debt_schedule_files:
        Optional[
            List[UploadFile]
        ] = File(None),

    company_profile_files:
        Optional[
            List[UploadFile]
        ] = File(None),

    other_files:
        Optional[
            List[UploadFile]
        ] = File(None),
):

    # -----------------------------------------------------
    # DATE VALIDATION
    # -----------------------------------------------------

    try:

        valuation_dt = (
            datetime.strptime(
                valuation_date,
                "%Y-%m-%d"
            )
        )

        engagement_dt = (
            datetime.strptime(
                engagement_date,
                "%Y-%m-%d"
            )
        )

        report_dt = (
            datetime.strptime(
                report_date,
                "%Y-%m-%d"
            )
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid date format."
        )

    if not (
        valuation_dt
        <= engagement_dt
        <= report_dt
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Dates must satisfy: "
                "Valuation Date <= "
                "Engagement Date <= "
                "Report Date."
            )
        )

    # -----------------------------------------------------
    # ASSIGNMENT
    # -----------------------------------------------------

    assignment_id = (
        next_assignment_id()
    )

    company_slug = (
        safe_filename(
            company_name
        )
    )

    assignment_folder = (
        DATA_DIR /
        assignment_id
    )

    documents_folder = (
        assignment_folder /
        "documents"
    )

    outputs_folder = (
        assignment_folder /
        "outputs"
    )

    assignment_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    outputs_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # SAVE DOCUMENTS
    # -----------------------------------------------------

    files_saved = {}

    files_saved[
        "provisional_financials"
    ] = await save_files(
        provisional_files,
        documents_folder /
        "01_provisional_financials"
    )

    files_saved[
        "historical_financials"
    ] = await save_files(
        historical_files,
        documents_folder /
        "02_historical_financials"
    )

    files_saved[
        "projections"
    ] = await save_files(
        projection_files,
        documents_folder /
        "03_projections"
    )

    files_saved[
        "capital_structure"
    ] = await save_files(
        capital_structure_files,
        documents_folder /
        "04_capital_structure"
    )

    files_saved[
        "debt_schedule"
    ] = await save_files(
        debt_schedule_files,
        documents_folder /
        "05_debt_schedule"
    )

    files_saved[
        "company_profile"
    ] = await save_files(
        company_profile_files,
        documents_folder /
        "06_company_profile"
    )

    files_saved[
        "other_documents"
    ] = await save_files(
        other_files,
        documents_folder /
        "07_other_documents"
    )

    # -----------------------------------------------------
    # ASSIGNMENT JSON
    # -----------------------------------------------------

    assignment_data = {

        "assignment_id":
            assignment_id,

        "company_name":
            company_name,

        "company_slug":
            company_slug,

        "cin":
            cin,

        "pan":
            pan,

        "valuation_date":
            valuation_date,

        "engagement_date":
            engagement_date,

        "report_date":
            report_date,

        "purpose":
            purpose,

        "security_type":
            security_type,

        "applicable_provision":
            applicable_provision,

        "transaction_details":
            transaction_details,

        "contact": {

            "name":
                contact_name,

            "designation":
                designation,

            "mobile":
                mobile,

            "email":
                email,
        },

        "documents":
            files_saved,

        "created_at":
            datetime.now()
            .isoformat(),

        "status":
            "Submitted",
    }

    save_json(
        assignment_folder /
        "assignment.json",

        assignment_data
    )

    return {

        "success":
            True,

        "assignment_id":
            assignment_id,

        "message":
            (
                "Valuation assignment "
                "created successfully."
            ),

        "folder":
            str(
                assignment_folder
            ),
    }


# =========================================================
# FINANCIAL EXTRACTION
# =========================================================

@app.post(
    "/financials/analyze/{assignment_id}"
)
def analyze_uploaded_financials(
    assignment_id: str
):

    assignment_folder = (
        get_assignment_folder(
            assignment_id
        )
    )

    try:

        extraction_result = (
            extract_assignment_financials(
                assignment_folder
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Financial extraction "
                f"failed: {str(exc)}"
            )
        )

    extraction_file = (
        assignment_folder /
        "financial_analysis.json"
    )

    save_json(
        extraction_file,
        extraction_result
    )

    summary = (
        extraction_result.get(
            "summary",
            {}
        )
    )

    return {

        "success":
            True,

        "assignment_id":
            assignment_id,

        "message":
            (
                "Financial statements "
                "analyzed and normalized "
                "successfully."
            ),

        "extractor_version":
            extraction_result.get(
                "extractor_version"
            ),

        "workbooks_found":
            summary.get(
                "workbooks_found",
                len(
                    extraction_result.get(
                        "files",
                        []
                    )
                )
            ),

        "historical_periods":
            summary.get(
                "historical_periods",
                []
            ),

        "provisional_periods":
            summary.get(
                "provisional_periods",
                []
            ),

        "projected_periods":
            summary.get(
                "projected_periods",
                []
            ),

        "review_items":
            summary.get(
                "review_items",
                len(
                    extraction_result.get(
                        "review_required",
                        []
                    )
                )
            ),

        "analysis":
            extraction_result,
    }


# =========================================================
# FINANCIAL RATIO / TREND ANALYSIS
# =========================================================

@app.post(
    "/financials/analysis/{assignment_id}"
)
def run_financial_analysis(
    assignment_id: str
):

    assignment_folder = (
        get_assignment_folder(
            assignment_id
        )
    )

    # -----------------------------------------------------
    # STEP 1:
    # Re-run latest extraction so the analysis always uses
    # current uploaded Excel files.
    # -----------------------------------------------------

    try:

        extraction_result = (
            extract_assignment_financials(
                assignment_folder
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Financial extraction "
                f"failed: {str(exc)}"
            )
        )

    # -----------------------------------------------------
    # SAVE NORMALIZED EXTRACTION
    # -----------------------------------------------------

    extraction_file = (
        assignment_folder /
        "financial_analysis.json"
    )

    save_json(
        extraction_file,
        extraction_result
    )

    # -----------------------------------------------------
    # STEP 2:
    # CALCULATE RATIOS / TRENDS
    # -----------------------------------------------------

    try:

        detailed_analysis = (
            analyze_normalized_financials(
                extraction_result
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Financial analysis "
                f"failed: {str(exc)}"
            )
        )

    # -----------------------------------------------------
    # INCLUDE EXTRACTION INFORMATION
    # -----------------------------------------------------

    detailed_analysis[
        "assignment_id"
    ] = assignment_id

    detailed_analysis[
        "extractor_version"
    ] = extraction_result.get(
        "extractor_version"
    )

    detailed_analysis[
        "generated_at"
    ] = (
        datetime.now()
        .isoformat()
    )

    review_log = load_review_log(
        assignment_folder
    )

    decorated_reviews = (
        decorate_review_items(
            extraction_result.get(
                "review_required",
                []
            ),
            review_log,
        )
    )

    detailed_analysis[
        "review_required"
    ] = decorated_reviews

    detailed_analysis[
        "cross_checks"
    ] = extraction_result.get(
        "cross_checks",
        []
    )

    detailed_analysis[
        "review_summary"
    ] = build_review_summary(
        decorated_reviews,
        detailed_analysis[
            "cross_checks"
        ],
        detailed_analysis.get(
            "capital_structure",
            {}
        ),
    )

    # -----------------------------------------------------
    # SAVE DETAILED ANALYSIS
    # -----------------------------------------------------

    detailed_file = (
        assignment_folder /
        "financial_analysis_detailed.json"
    )

    save_json(
        detailed_file,
        detailed_analysis
    )

    return {

        "success":
            True,

        "assignment_id":
            assignment_id,

        "message":
            (
                "Financial analysis, "
                "ratios and projection "
                "comparison completed "
                "successfully."
            ),

        "analysis_engine_version":
            detailed_analysis.get(
                "analysis_engine_version"
            ),

        "historical":
            detailed_analysis.get(
                "historical",
                []
            ),

        "provisional":
            detailed_analysis.get(
                "provisional",
                []
            ),

        "projected":
            detailed_analysis.get(
                "projected",
                []
            ),

        "historical_cagr":
            detailed_analysis.get(
                "historical_cagr",
                {}
            ),

        "projected_cagr":
            detailed_analysis.get(
                "projected_cagr",
                {}
            ),

        "projection_comparison":
            detailed_analysis.get(
                "projection_comparison",
                {}
            ),

        "projection_schedule_metrics":
            detailed_analysis.get(
                "projection_schedule_metrics",
                {}
            ),

        "capital_structure":
            detailed_analysis.get(
                "capital_structure",
                {}
            ),

        "observations":
            detailed_analysis.get(
                "observations",
                []
            ),

        "cross_checks":
            detailed_analysis.get(
                "cross_checks",
                []
            ),

        "review_required":
            detailed_analysis.get(
                "review_required",
                []
            ),

        "review_summary":
            detailed_analysis.get(
                "review_summary",
                {}
            ),

        "review_items":
            detailed_analysis.get(
                "review_summary",
                {}
            ).get(
                "unresolved",
                0
            ),
    }


# =========================================================
# REVIEW / DATA VALIDATION API
# =========================================================

@app.get(
    "/reviews/{assignment_id}"
)
def get_reviews(
    assignment_id: str
):

    assignment_folder = (
        get_assignment_folder(
            assignment_id
        )
    )

    extraction_file = (
        assignment_folder /
        "financial_analysis.json"
    )

    if extraction_file.exists():
        with extraction_file.open(
            "r",
            encoding="utf-8"
        ) as file:
            extraction_result = json.load(
                file
            )
    else:
        extraction_result = (
            extract_assignment_financials(
                assignment_folder
            )
        )

    review_log = load_review_log(
        assignment_folder
    )

    items = decorate_review_items(
        extraction_result.get(
            "review_required",
            []
        ),
        review_log,
    )

    capital_structure = {}

    detailed_file = (
        assignment_folder /
        "financial_analysis_detailed.json"
    )

    if detailed_file.exists():
        try:
            with detailed_file.open(
                "r",
                encoding="utf-8"
            ) as file:
                detailed_saved = json.load(
                    file
                )

            capital_structure = (
                detailed_saved.get(
                    "capital_structure",
                    {}
                )
            )
        except Exception:
            capital_structure = {}

    summary = build_review_summary(
        items,
        extraction_result.get(
            "cross_checks",
            []
        ),
        capital_structure,
    )

    return {
        "success": True,
        "assignment_id": assignment_id,
        "review_required": items,
        "review_summary": summary,
    }


@app.post(
    "/reviews/{assignment_id}"
)
def update_review(
    assignment_id: str,
    request: ReviewUpdateRequest,
):

    assignment_folder = (
        get_assignment_folder(
            assignment_id
        )
    )

    allowed_statuses = {
        "pending",
        "reviewed",
        "accepted",
        "ignored",
    }

    status = request.status.strip().lower()

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                "Review status must be pending, "
                "reviewed, accepted or ignored."
            )
        )

    extraction_file = (
        assignment_folder /
        "financial_analysis.json"
    )

    if extraction_file.exists():
        with extraction_file.open(
            "r",
            encoding="utf-8"
        ) as file:
            extraction_result = json.load(
                file
            )
    else:
        extraction_result = (
            extract_assignment_financials(
                assignment_folder
            )
        )

    current_log = load_review_log(
        assignment_folder
    )

    current_items = decorate_review_items(
        extraction_result.get(
            "review_required",
            []
        ),
        current_log,
    )

    valid_ids = {
        item.get(
            "review_id"
        )
        for item in current_items
    }

    if request.review_id not in valid_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                "Review item was not found in the "
                "current extraction result."
            )
        )

    current_log.setdefault(
        "items",
        {}
    )

    updated_at = (
        datetime.now()
        .isoformat()
    )

    if status == "pending":
        current_log[
            "items"
        ].pop(
            request.review_id,
            None
        )
    else:
        current_log[
            "items"
        ][
            request.review_id
        ] = {
            "status": status,
            "note": request.note.strip(),
            "updated_at": updated_at,
        }

    current_log[
        "updated_at"
    ] = updated_at

    save_json(
        review_log_path(
            assignment_folder
        ),
        current_log
    )

    items = decorate_review_items(
        extraction_result.get(
            "review_required",
            []
        ),
        current_log,
    )

    capital_structure = {}

    detailed_file = (
        assignment_folder /
        "financial_analysis_detailed.json"
    )

    detailed_saved = {}

    if detailed_file.exists():
        try:
            with detailed_file.open(
                "r",
                encoding="utf-8"
            ) as file:
                detailed_saved = json.load(
                    file
                )

            capital_structure = (
                detailed_saved.get(
                    "capital_structure",
                    {}
                )
            )
        except Exception:
            detailed_saved = {}
            capital_structure = {}

    summary = build_review_summary(
        items,
        extraction_result.get(
            "cross_checks",
            []
        ),
        capital_structure,
    )

    if detailed_saved:
        detailed_saved[
            "review_required"
        ] = items

        detailed_saved[
            "review_summary"
        ] = summary

        detailed_saved[
            "review_updated_at"
        ] = updated_at

        save_json(
            detailed_file,
            detailed_saved
        )

    return {
        "success": True,
        "assignment_id": assignment_id,
        "review_required": items,
        "review_summary": summary,
    }


# =========================================================
# WACC / MARKET DATA
# =========================================================

def calculate_wacc_working(
    request: WACCRequest
) -> dict:

    if request.beta < 0:
        raise ValueError(
            "Beta cannot be negative."
        )

    if not (
        0 <= request.tax_rate_percent <= 100
    ):
        raise ValueError(
            "Tax rate must be between 0% and 100%."
        )

    weight_total = (
        request.equity_weight_percent
        + request.debt_weight_percent
    )

    if abs(weight_total - 100) > 0.01:
        raise ValueError(
            "Equity Weight and Debt Weight must total 100%."
        )

    if (
        request.equity_weight_percent < 0
        or request.debt_weight_percent < 0
    ):
        raise ValueError(
            "Capital structure weights cannot be negative."
        )

    cost_of_equity = (
        request.risk_free_rate_percent
        + (
            request.beta
            * request.equity_risk_premium_percent
        )
        + request.company_specific_risk_premium_percent
    )

    after_tax_cost_of_debt = (
        request.pre_tax_cost_of_debt_percent
        * (
            1
            - request.tax_rate_percent / 100
        )
    )

    wacc_percent = (
        cost_of_equity
        * request.equity_weight_percent / 100
        + after_tax_cost_of_debt
        * request.debt_weight_percent / 100
    )

    sensitivity_rows = []

    beta_offsets = [
        -0.20,
        0.00,
        0.20,
    ]

    debt_cost_offsets = [
        -1.00,
        0.00,
        1.00,
    ]

    for beta_offset in beta_offsets:

        adjusted_beta = max(
            request.beta + beta_offset,
            0
        )

        row = {
            "beta": round(
                adjusted_beta,
                4
            ),
            "values": [],
        }

        for debt_offset in debt_cost_offsets:

            adjusted_debt_cost = max(
                request.pre_tax_cost_of_debt_percent
                + debt_offset,
                0
            )

            adjusted_ke = (
                request.risk_free_rate_percent
                + adjusted_beta
                * request.equity_risk_premium_percent
                + request.company_specific_risk_premium_percent
            )

            adjusted_after_tax_debt = (
                adjusted_debt_cost
                * (
                    1
                    - request.tax_rate_percent / 100
                )
            )

            adjusted_wacc = (
                adjusted_ke
                * request.equity_weight_percent / 100
                + adjusted_after_tax_debt
                * request.debt_weight_percent / 100
            )

            row[
                "values"
            ].append({
                "pre_tax_cost_of_debt_percent": round(
                    adjusted_debt_cost,
                    4
                ),
                "wacc_percent": round(
                    adjusted_wacc,
                    4
                ),
            })

        sensitivity_rows.append(
            row
        )

    return {
        "risk_free_rate_percent": round(
            request.risk_free_rate_percent,
            4
        ),
        "equity_risk_premium_percent": round(
            request.equity_risk_premium_percent,
            4
        ),
        "beta": round(
            request.beta,
            4
        ),
        "company_specific_risk_premium_percent": round(
            request.company_specific_risk_premium_percent,
            4
        ),
        "cost_of_equity_percent": round(
            cost_of_equity,
            4
        ),
        "pre_tax_cost_of_debt_percent": round(
            request.pre_tax_cost_of_debt_percent,
            4
        ),
        "tax_rate_percent": round(
            request.tax_rate_percent,
            4
        ),
        "after_tax_cost_of_debt_percent": round(
            after_tax_cost_of_debt,
            4
        ),
        "equity_weight_percent": round(
            request.equity_weight_percent,
            4
        ),
        "debt_weight_percent": round(
            request.debt_weight_percent,
            4
        ),
        "wacc_percent": round(
            wacc_percent,
            4
        ),
        "market_data_date": request.market_data_date,
        "sources": {
            "risk_free_rate": request.risk_free_source,
            "equity_risk_premium": request.erp_source,
            "beta": request.beta_source,
            "cost_of_debt": request.debt_source,
        },
        "notes": request.notes,
        "formula": (
            "Cost of Equity = Risk-free Rate + "
            "Beta x Equity Risk Premium + CSRP; "
            "After-tax Cost of Debt = Pre-tax Cost of Debt x (1 - Tax Rate); "
            "WACC = Ke x Equity Weight + Kd(after-tax) x Debt Weight"
        ),
        "sensitivity": {
            "beta_offsets": beta_offsets,
            "debt_cost_offsets_percent": debt_cost_offsets,
            "rows": sensitivity_rows,
        },
    }


@app.post(
    "/valuation/wacc"
)
def valuation_wacc(
    request: WACCRequest
):

    try:
        return calculate_wacc_working(
            request
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )



# =========================================================
# MARKET DATA SUGGESTIONS
# =========================================================

@app.get(
    "/valuation/market-data/suggest/{assignment_id}"
)
def valuation_market_data_suggest(
    assignment_id: str
):

    assignment = load_assignment(
        assignment_id
    )

    assignment_folder = (
        get_assignment_folder(
            assignment_id
        )
    )

    # Re-run the current deterministic extraction / analysis
    # so debt cost and capital weights use the latest uploaded data.
    try:

        extraction_result = (
            extract_assignment_financials(
                assignment_folder
            )
        )

        detailed_analysis = (
            analyze_normalized_financials(
                extraction_result
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to prepare market-data suggestions: "
                f"{str(exc)}"
            )
        )

    try:

        result = suggest_market_data(
            assignment=assignment,
            detailed_analysis=detailed_analysis,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Market-data suggestion engine failed: "
                f"{str(exc)}"
            )
        )

    save_json(
        assignment_folder /
        "market_data_suggestions.json",
        {
            **result,
            "generated_at":
                datetime.now()
                .isoformat(),
        }
    )

    return result


# =========================================================
# DCF
# =========================================================

@app.post(
    "/valuation/dcf"
)
def valuation_dcf(
    request: DCFRequest
):

    try:

        result = calculate_dcf(

            projections=[
                row.model_dump()
                for row
                in request.projections
            ],

            tax_rate=
                request.tax_rate,

            wacc=
                request.wacc,

            terminal_growth=
                request.terminal_growth,

            cash=
                request.cash,

            debt=
                request.debt,

            non_operating_assets=
                request.non_operating_assets,
        )

        result[
            "value_per_share"
        ] = (
            calculate_value_per_share(
                result[
                    "equity_value"
                ],
                request.diluted_shares
            )
        )

        result[
            "sensitivity"
        ] = (
            calculate_dcf_sensitivity(
                projections=[
                    row.model_dump()
                    for row
                    in request.projections
                ],
                tax_rate=
                    request.tax_rate,
                base_wacc=
                    request.wacc,
                base_terminal_growth=
                    request.terminal_growth,
                cash=
                    request.cash,
                debt=
                    request.debt,
                non_operating_assets=
                    request.non_operating_assets,
                diluted_shares=
                    request.diluted_shares,
            )
        )

        return result

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(
                exc
            )
        )


# =========================================================
# NAV
# =========================================================

@app.post(
    "/valuation/nav"
)
def valuation_nav(
    request: NAVRequest
):

    try:

        equity_value = (
            calculate_nav(
                request.adjusted_assets,
                request.adjusted_liabilities
            )
        )

        value_per_share = (
            calculate_value_per_share(
                equity_value,
                request.diluted_shares
            )
        )

        return {

            "equity_value":
                equity_value,

            "value_per_share":
                value_per_share,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(
                exc
            )
        )


# =========================================================
# METHOD WEIGHTAGE
# =========================================================

@app.post(
    "/valuation/weightage"
)
def valuation_weightage(
    request: WeightageRequest
):

    try:

        result = (
            calculate_weighted_value(
                [
                    row.model_dump()
                    for row
                    in request.methods
                ]
            )
        )

        result[
            "value_per_share"
        ] = (
            calculate_value_per_share(
                result[
                    "concluded_value"
                ],
                request.diluted_shares
            )
        )

        return result

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(
                exc
            )
        )


# =========================================================
# GENERATE EXCEL + WORD
# =========================================================

@app.post(
    "/outputs/generate"
)
def generate_outputs(
    request: OutputRequest
):

    assignment = (
        load_assignment(
            request.assignment_id
        )
    )

    assignment_folder = (
        get_assignment_folder(
            request.assignment_id
        )
    )

    outputs_folder = (
        assignment_folder /
        "outputs"
    )

    outputs_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # DCF
    # -----------------------------------------------------

    try:

        dcf_result = (
            calculate_dcf(

                projections=[
                    row.model_dump()
                    for row
                    in request.projections
                ],

                tax_rate=
                    request.tax_rate_percent
                    / 100,

                wacc=
                    request.wacc_percent
                    / 100,

                terminal_growth=
                    request
                    .terminal_growth_percent
                    / 100,

                cash=
                    request.cash,

                debt=
                    request.debt,

                non_operating_assets=
                    request
                    .non_operating_assets,
            )
        )

        dcf_result[
            "value_per_share"
        ] = (
            calculate_value_per_share(
                dcf_result[
                    "equity_value"
                ],
                request.diluted_shares
            )
        )

        dcf_result[
            "sensitivity"
        ] = (
            calculate_dcf_sensitivity(
                projections=[
                    row.model_dump()
                    for row
                    in request.projections
                ],
                tax_rate=
                    request.tax_rate_percent
                    / 100,
                base_wacc=
                    request.wacc_percent
                    / 100,
                base_terminal_growth=
                    request
                    .terminal_growth_percent
                    / 100,
                cash=
                    request.cash,
                debt=
                    request.debt,
                non_operating_assets=
                    request
                    .non_operating_assets,
                diluted_shares=
                    request.diluted_shares,
            )
        )

        # -------------------------------------------------
        # NAV
        # -------------------------------------------------

        nav_equity_value = (
            calculate_nav(
                request.adjusted_assets,
                request.adjusted_liabilities
            )
        )

        nav_result = {

            "equity_value":
                nav_equity_value,

            "value_per_share":
                calculate_value_per_share(
                    nav_equity_value,
                    request.diluted_shares
                ),
        }

        # -------------------------------------------------
        # WEIGHTAGE
        # -------------------------------------------------

        weightage_result = (
            calculate_weighted_value(
                [
                    {
                        "method":
                            "DCF",

                        "value":
                            dcf_result[
                                "equity_value"
                            ],

                        "weight":
                            request.dcf_weight,
                    },

                    {
                        "method":
                            "NAV",

                        "value":
                            nav_result[
                                "equity_value"
                            ],

                        "weight":
                            request.nav_weight,
                    },
                ]
            )
        )

        weightage_result[
            "value_per_share"
        ] = (
            calculate_value_per_share(
                weightage_result[
                    "concluded_value"
                ],
                request.diluted_shares
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(
                exc
            )
        )

    # -----------------------------------------------------
    # INPUTS
    # -----------------------------------------------------

    valuation_inputs = {

        "tax_rate_percent":
            request.tax_rate_percent,

        "wacc_percent":
            request.wacc_percent,

        "terminal_growth_percent":
            request
            .terminal_growth_percent,

        "cash":
            request.cash,

        "debt":
            request.debt,

        "non_operating_assets":
            request
            .non_operating_assets,

        "diluted_shares":
            request.diluted_shares,

        "adjusted_assets":
            request.adjusted_assets,

        "adjusted_liabilities":
            request.adjusted_liabilities,

        "dcf_weight":
            request.dcf_weight,

        "nav_weight":
            request.nav_weight,

        "wacc_analysis":
            request.wacc_analysis,
    }

    # -----------------------------------------------------
    # SAVE VALUATION JSON
    # -----------------------------------------------------

    review_summary = {}
    capital_structure = {}
    financial_analysis = {}

    detailed_file = (
        assignment_folder /
        "financial_analysis_detailed.json"
    )

    if detailed_file.exists():
        try:
            with detailed_file.open(
                "r",
                encoding="utf-8"
            ) as file:
                detailed_saved = json.load(
                    file
                )

            review_summary = (
                detailed_saved.get(
                    "review_summary",
                    {}
                )
            )

            capital_structure = (
                detailed_saved.get(
                    "capital_structure",
                    {}
                )
            )

            financial_analysis = detailed_saved
        except Exception:
            review_summary = {}
            capital_structure = {}
            financial_analysis = {}

    valuation_json = {

        "assignment_id":
            request.assignment_id,

        "review_summary":
            review_summary,

        "report_status":
            (
                "READY_FOR_FINAL_REVIEW"
                if review_summary.get(
                    "final_report_ready",
                    False
                )
                else "DRAFT_ONLY_REVIEW_PENDING"
            ),

        "inputs":
            valuation_inputs,

        "dcf":
            dcf_result,

        "nav":
            nav_result,

        "weightage":
            weightage_result,

        "wacc_analysis":
            request.wacc_analysis,

        "capital_structure":
            capital_structure,

        "generated_at":
            datetime.now()
            .isoformat(),
    }

    save_json(
        assignment_folder /
        "valuation.json",

        valuation_json
    )

    # -----------------------------------------------------
    # EXCEL
    # -----------------------------------------------------

    excel_path = (
        outputs_folder /
        "Valuation_Working.xlsx"
    )

    generate_excel_working(

        output_path=
            excel_path,

        assignment=
            assignment,

        dcf_result=
            dcf_result,

        nav_result=
            nav_result,

        weightage_result=
            weightage_result,

        valuation_inputs=
            valuation_inputs,

        wacc_analysis=
            request.wacc_analysis,

        capital_structure=
            capital_structure,

        review_summary=
            review_summary,

        report_status=
            valuation_json[
                "report_status"
            ],

        financial_analysis=
            financial_analysis,
    )

    # -----------------------------------------------------
    # WORD REPORT
    # -----------------------------------------------------

    word_path = (
        outputs_folder /
        "Draft_Valuation_Report.docx"
    )

    generate_word_report(

        output_path=
            word_path,

        assignment=
            assignment,

        dcf_result=
            dcf_result,

        nav_result=
            nav_result,

        weightage_result=
            weightage_result,

        valuation_inputs=
            valuation_inputs,

        wacc_analysis=
            request.wacc_analysis,

        capital_structure=
            capital_structure,

        review_summary=
            review_summary,

        report_status=
            valuation_json[
                "report_status"
            ],

        financial_analysis=
            financial_analysis,
    )

    return {

        "success":
            True,

        "message":
            (
                "Excel working and "
                "draft valuation report "
                "generated successfully."
            ),

        "assignment_id":
            request.assignment_id,

        "report_status":
            valuation_json[
                "report_status"
            ],

        "review_summary":
            review_summary,

        "excel_download":
            (
                f"/outputs/"
                f"{request.assignment_id}"
                f"/excel"
            ),

        "word_download":
            (
                f"/outputs/"
                f"{request.assignment_id}"
                f"/word"
            ),
    }


# =========================================================
# DOWNLOAD EXCEL
# =========================================================

@app.get(
    "/outputs/{assignment_id}/excel"
)
def download_excel(
    assignment_id: str
):

    folder = (
        get_assignment_folder(
            assignment_id
        )
    )

    file_path = (
        folder /
        "outputs" /
        "Valuation_Working.xlsx"
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Excel working "
                "not found."
            )
        )

    return FileResponse(

        path=file_path,

        filename=
            "Valuation_Working.xlsx",

        media_type=(
            "application/"
            "vnd.openxmlformats-"
            "officedocument."
            "spreadsheetml.sheet"
        ),
    )


# =========================================================
# DOWNLOAD WORD
# =========================================================

@app.get(
    "/outputs/{assignment_id}/word"
)
def download_word(
    assignment_id: str
):

    folder = (
        get_assignment_folder(
            assignment_id
        )
    )

    file_path = (
        folder /
        "outputs" /
        "Draft_Valuation_Report.docx"
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Draft valuation report "
                "not found."
            )
        )

    return FileResponse(

        path=file_path,

        filename=
            "Draft_Valuation_Report.docx",

        media_type=(
            "application/"
            "vnd.openxmlformats-"
            "officedocument."
            "wordprocessingml.document"
        ),
    )