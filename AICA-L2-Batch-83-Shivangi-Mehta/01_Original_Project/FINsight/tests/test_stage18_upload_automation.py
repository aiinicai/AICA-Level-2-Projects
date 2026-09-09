"""
Stage 18 — Upload automation (approved redesign).

Full HTTP round trip through the real Flask app for the new automatic
Detect Structure / Map Columns / Validate pipeline on the Upload screen
(`app/services/auto_pipeline_service.py`, wired into `app/api/
upload_bp.py`), and the new one-click "Run Review" action it enables.

Mirrors tests/test_upload_http.py's fixture shape. Uses only synthetic,
fabricated CSV/XLSX content — never real client or financial data, per
the standing instruction.
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest

from config import TestConfig
from app import create_app


@pytest.fixture()
def client(tmp_path):
    class IsolatedConfig(TestConfig):
        DATA_INPUT_DIR = tmp_path / "data_input"

    app = create_app(IsolatedConfig)
    from app import extensions
    from app.models import Base

    Base.metadata.create_all(extensions.engine)
    return app.test_client()


def body(resp):
    return resp.get_data(as_text=True)


def _create_and_select_engagement(client, entity_name="Acme Manufacturing Ltd"):
    r = client.post(
        "/engagement/new",
        data={"entity_name": entity_name, "financial_year": "2025-26"},
        follow_redirects=False,
    )
    assert r.status_code == 302


def _csv_bytes(rows) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


TB_ROWS = [
    {"account": "Cash", "debit": 100000, "credit": 0},
    {"account": "Sales", "debit": 0, "credit": 100000},
]


def _upload_tb(client, filename="tb.csv"):
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes(TB_ROWS)), filename), "file_type": "TB"},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302


# --- Auto-preview (GET, nothing persisted) ----------------------------------


def test_upload_page_shows_auto_detected_preview_after_upload(client):
    _create_and_select_engagement(client)
    _upload_tb(client)

    page = body(client.get("/data/upload/"))
    assert "Ready to Confirm" in page
    assert "column(s) matched" in page
    assert "Looks Good" in page  # data-check badge for a clean TB file
    assert "confirm_auto" in page  # the hidden field backing the Confirm button

    from app.services import upload_service
    from app.services import engagement_service
    engagement = engagement_service.list_engagements()[0]
    upload = upload_service.list_uploads(engagement.engagement_id)[0]
    assert upload.upload_status == "UPLOADED"  # nothing persisted by the GET/preview alone


def test_preview_does_not_offer_confirm_when_no_columns_auto_match(client):
    _create_and_select_engagement(client)
    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes([{"xyz1": "a", "xyz2": "b"}])), "weird.csv"), "file_type": "TB"},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    page = body(client.get("/data/upload/"))
    assert "Couldn&#39;t auto-match any columns" in page or "Couldn't auto-match any columns" in page
    assert 'name="action" value="confirm_auto"' not in page
    assert "Review manually" in page  # fallback to the still-functional manual Mapping screen


# --- Confirm & Continue (POST, persists) ------------------------------------


def test_confirm_auto_persists_mapping_and_validation_for_all_pending_files(client):
    _create_and_select_engagement(client)
    _upload_tb(client)

    r = client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)
    assert r.status_code == 200  # renders inline (like the multi-file batch result), no redirect
    page = body(r)
    assert "Confirmed" in page

    from app.services import upload_service
    from app.services import engagement_service
    from app.services import mapping_service
    engagement = engagement_service.list_engagements()[0]
    upload = upload_service.list_uploads(engagement.engagement_id)[0]
    assert upload.upload_status == "VALIDATED"

    confirmed = mapping_service.get_confirmed_mappings(upload.file_id)
    confirmed_fields = {m.target_field for m in confirmed}
    assert "account_name" in confirmed_fields
    assert "debit_amount" in confirmed_fields
    assert "credit_amount" in confirmed_fields
    # Blueprint Section 8 safeguard preserved: every persisted mapping
    # is explicitly marked confirmed, never silently auto-applied.
    assert all(m.is_user_confirmed for m in confirmed)


def test_confirm_auto_skips_a_file_with_no_auto_matched_columns(client):
    _create_and_select_engagement(client)
    client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(_csv_bytes([{"xyz1": "a", "xyz2": "b"}])), "weird.csv"), "file_type": "TB"},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    r = client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)
    assert r.status_code == 200

    from app.services import upload_service
    from app.services import engagement_service
    engagement = engagement_service.list_engagements()[0]
    upload = upload_service.list_uploads(engagement.engagement_id)[0]
    assert upload.upload_status == "UPLOADED"  # untouched — never force-mapped


# --- Multi-sheet auto-pick ---------------------------------------------------


def test_multi_sheet_workbook_auto_picks_the_first_sheet(client):
    _create_and_select_engagement(client)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(TB_ROWS).to_excel(writer, sheet_name="TB Data", index=False)
        pd.DataFrame([{"foo": 1}]).to_excel(writer, sheet_name="Notes", index=False)

    r = client.post(
        "/data/upload/",
        data={"file": (io.BytesIO(buf.getvalue()), "multi.xlsx"), "file_type": "TB"},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    page = body(client.get("/data/upload/"))
    assert "TB Data" in page
    assert "chosen automatically" in page

    r = client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)
    assert "1 file(s) mapped and checked automatically." in body(r)


# --- One-click "Run Review" from the Upload screen --------------------------


def test_run_review_button_appears_only_once_every_file_is_validated(client):
    _create_and_select_engagement(client)
    _upload_tb(client)

    page = body(client.get("/data/upload/"))
    assert 'name="run_source" value="upload_quick_action"' not in page  # not yet mapped/validated

    client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)

    page = body(client.get("/data/upload/"))
    assert 'name="run_source" value="upload_quick_action"' in page


def test_run_review_quick_action_redirects_straight_to_findings_centre(client):
    _create_and_select_engagement(client)
    _upload_tb(client)
    client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)

    r = client.post("/review/", data={"run_source": "upload_quick_action"}, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/review/findings")


def test_legacy_checkbox_run_review_path_is_unaffected_by_the_quick_action(client):
    """The original Stage 12 POST shape (posting `modules`) must still
    render the inline Result Summary on the same page, not redirect —
    proving the Stage 18 dual-path design left this path untouched."""
    _create_and_select_engagement(client)
    _upload_tb(client)
    client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)

    r = client.post("/review/", data={"modules": ["ACCOUNTING"]}, follow_redirects=False)
    assert r.status_code == 200
    assert "Result Summary" in body(r) or "Findings" in body(r)


# --- AS / Ind AS auto-detect (Yes/No question) end-to-end -------------------


def test_entity_profile_ind_as_yes_answer_auto_detects_ind_as_without_manual_selection(client):
    engagement = _create_and_select_engagement(client) or None
    from app.services import engagement_service
    eng = engagement_service.list_engagements()[0]

    r = client.post(
        f"/engagement/{eng.engagement_id}/profile",
        data={
            "entity_type": "Company",
            "ind_as_mandated": "yes",  # no accounting_framework posted at all
            "tax_audit_status": "REQUIRES_REVIEW",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302

    profile = engagement_service.get_entity_profile(eng.engagement_id)
    # bool(...) rather than `is True`: this sandbox's SQLAlchemy shim
    # round-trips a Boolean column through real sqlite3 as a plain 0/1
    # int rather than coercing it back to Python bool — a sandbox
    # artifact, not app behavior (real SQLAlchemy's Boolean type
    # coerces this on load).
    assert bool(profile.ind_as_mandated) is True
    assert profile.accounting_framework == "IND_AS"

    page = body(client.get(f"/engagement/{eng.engagement_id}/applicability"))
    assert "Ind AS" in page
    assert "(detected)" in page


def test_entity_profile_ind_as_no_answer_auto_detects_as(client):
    _create_and_select_engagement(client)
    from app.services import engagement_service
    eng = engagement_service.list_engagements()[0]

    r = client.post(
        f"/engagement/{eng.engagement_id}/profile",
        data={
            "entity_type": "Proprietorship",
            "ind_as_mandated": "no",
            "tax_audit_status": "NOT_APPLICABLE",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302

    profile = engagement_service.get_entity_profile(eng.engagement_id)
    assert bool(profile.ind_as_mandated) is False  # see comment above re: the sandbox shim
    assert profile.accounting_framework == "AS"


# --- Bug fix: a file mapped via the manual Mapping screen is no longer stranded ---
#
# Caught from a real screenshot after Phase 2 shipped: the manual Mapping
# screen (still reachable — only its sidebar shortcut was removed) has no
# "next step" link of its own, and the Upload screen's auto-pipeline used
# to only look at files still sitting at upload_status == "UPLOADED" — so
# a file mapped by hand (status -> "MAPPED") fell into a dead end with no
# visible way to reach Data Quality or Run Review. Fixed in
# auto_pipeline_service.py by also picking up "MAPPED" files (skipping
# straight to a Data Quality preview, since a human already confirmed the
# mapping) and by adding a "Back to Upload" link on the manual screens as
# a second line of defense.

def test_manually_mapped_file_is_picked_up_by_the_upload_screen(client):
    _create_and_select_engagement(client)
    _upload_tb(client)

    from app.services import upload_service
    from app.services import engagement_service
    engagement = engagement_service.list_engagements()[0]
    file_id = upload_service.list_uploads(engagement.engagement_id)[0].file_id

    # Map it by hand through the still-reachable manual Mapping screen,
    # exactly as a user following an old bookmark or a direct link would.
    r = client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "account_name", "target_field__1": "debit_amount", "target_field__2": "credit_amount",
    }, follow_redirects=False)
    assert r.status_code == 302

    upload = upload_service.get_upload(file_id)
    assert upload.upload_status == "MAPPED"

    page = body(client.get("/data/upload/"))
    assert "Ready to Confirm" in page
    assert "Already mapped" in page
    assert 'name="action" value="confirm_auto"' in page

    r = client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)
    assert r.status_code == 200

    upload = upload_service.get_upload(file_id)
    assert upload.upload_status == "VALIDATED"

    page = body(client.get("/data/upload/"))
    assert 'name="run_source" value="upload_quick_action"' in page


def test_manual_mapping_and_data_quality_list_screens_link_back_to_upload(client):
    _create_and_select_engagement(client)
    _upload_tb(client)

    page = body(client.get("/data/mapping/"))
    assert "Back to Upload" in page
    assert 'href="/data/upload/"' in page

    page = body(client.get("/data/quality/"))
    assert "Back to Upload" in page
    assert 'href="/data/upload/"' in page


# --- Bug fix: manual screens actively guide the user forward, not just ---
# --- offer an easy-to-miss escape hatch (2nd screenshot) -----------------
#
# The first fix (above) added a "Back to Upload" button, but the user
# reported it was still not enough: the manual Mapping/Data Quality
# screens each carried the Stage 14 six-step wizard indicator
# (partials/step_indicator.html), which visually implies these screens
# are stops on a required linear path — exactly the impression Stage 18
# was meant to remove now that Upload is the single hub. Fixed by (a)
# removing the step indicator from the Mapping/Data Quality index and
# detail screens, (b) adding an explicit "this is a manual/advanced
# tool, use Upload instead" banner on the index screens, and (c)
# changing the manual Mapping screen's own POST success redirect from
# mapping.index (another list) to upload.index (the real hub), so
# finishing one manual mapping action returns the user to the one
# screen that tells them what to do next, instead of another dead end.

def test_confirming_a_manual_mapping_redirects_to_upload_not_back_to_mapping_list(client):
    _create_and_select_engagement(client)
    _upload_tb(client)

    from app.services import upload_service
    from app.services import engagement_service
    engagement = engagement_service.list_engagements()[0]
    file_id = upload_service.list_uploads(engagement.engagement_id)[0].file_id

    r = client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "account_name", "target_field__1": "debit_amount", "target_field__2": "credit_amount",
    }, follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/data/upload/")


def test_manual_mapping_and_data_quality_screens_no_longer_show_the_step_wizard(client):
    """The Stage 14 six-step wizard (partials/step_indicator.html,
    rendered as <nav class="fs-steps">) falsely implied these manual
    screens were stops on a required sequential path. Removed from the
    Mapping/Data Quality index and detail screens; left untouched
    elsewhere (upload/index.html, review/configure.html) — out of scope
    for this fix."""
    _create_and_select_engagement(client)
    _upload_tb(client)

    from app.services import upload_service
    from app.services import engagement_service
    engagement = engagement_service.list_engagements()[0]
    file_id = upload_service.list_uploads(engagement.engagement_id)[0].file_id

    mapping_index = body(client.get("/data/mapping/"))
    assert "fs-steps" not in mapping_index
    assert "manual, file-by-file tool" in mapping_index

    mapping_detail = body(client.get(f"/data/mapping/{file_id}/"))
    assert "fs-steps" not in mapping_detail

    quality_index = body(client.get("/data/quality/"))
    assert "fs-steps" not in quality_index
    assert "manual, file-by-file tool" in quality_index

    client.post(f"/data/mapping/{file_id}/", data={
        "target_field__0": "account_name", "target_field__1": "debit_amount", "target_field__2": "credit_amount",
    }, follow_redirects=False)
    r = client.post(f"/data/quality/{file_id}/", data={}, follow_redirects=False)
    quality_detail = body(r)
    assert "fs-steps" not in quality_detail
    assert "Back to Upload" in quality_detail  # unconditional now, not gated on VALIDATED-only


# --- Bug fix: real user data exposed two auto-mapping gaps ---------------
#
# Found by testing with the user's own JVS_FinSight_Test_Data sample
# files rather than only this suite's exact-synonym synthetic fixtures.
#
# (1) A Sales/Purchase Register commonly dates each row by its invoice
#     date rather than a generic "transaction date" column — the old
#     ESSENTIAL_ANY_OF only accepted transaction_date, so a real Sales
#     Register with only "Invoice Date" failed Data Quality even though
#     every row plainly has a date. Fixed in data_quality.py by adding
#     invoice_date as an accepted alternative for SALES/PURCHASE.
#
# (2) The auto-pipeline used to auto-confirm any suggestion scoring at
#     or above column_mapper.SUGGESTION_THRESHOLD (0.35) — a bar meant
#     for a human-reviewed suggestion list, not an unattended auto-
#     confirm. Real headers like "GST (INR)" fuzzy-matched "gstin" at
#     0.583 and were silently confirmed. Fixed by adding
#     AUTO_ACCEPT_THRESHOLD = 0.75 in auto_pipeline_service.py: only an
#     exact or substring-contains match auto-confirms; anything in the
#     0.35-0.75 fuzzy band is left unmapped for the manual screen.

SALES_ROWS_WITH_INVOICE_DATE_ONLY = [
    {"party name": "Ramesh Traders", "invoice date": "01-04-2025", "debit amount": 50000},
    {"party name": "Suresh & Co", "invoice date": "02-04-2025", "debit amount": 75000},
]


def test_sales_register_dated_only_by_invoice_date_now_validates(client):
    _create_and_select_engagement(client)
    r = client.post(
        "/data/upload/",
        data={
            "file": (io.BytesIO(_csv_bytes(SALES_ROWS_WITH_INVOICE_DATE_ONLY)), "sales.csv"),
            "file_type": "SALES",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    r = client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)
    assert "1 file(s) mapped and checked automatically." in body(r)

    from app.services import upload_service
    from app.services import engagement_service
    engagement = engagement_service.list_engagements()[0]
    upload = upload_service.list_uploads(engagement.engagement_id)[0]
    assert upload.upload_status == "VALIDATED"  # was ERROR (missing transaction_date) before the fix


GST_ROWS_WITH_LOW_CONFIDENCE_AMOUNT_COLUMN = [
    {
        "GSTIN": "27ABCDE1234F1Z5",
        "Invoice No": "INV-001",
        "Taxable Value": 10000,
        "GST (INR)": 1800,
    },
]


def test_low_confidence_fuzzy_match_is_left_unmapped_not_auto_confirmed(client):
    _create_and_select_engagement(client)
    r = client.post(
        "/data/upload/",
        data={
            "file": (io.BytesIO(_csv_bytes(GST_ROWS_WITH_LOW_CONFIDENCE_AMOUNT_COLUMN)), "gst.csv"),
            "file_type": "GST",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    page = body(client.get("/data/upload/"))
    assert "3 column(s) matched" in page or "column(s) matched" in page

    client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)

    from app.services import upload_service
    from app.services import engagement_service
    from app.services import mapping_service
    engagement = engagement_service.list_engagements()[0]
    upload = upload_service.list_uploads(engagement.engagement_id)[0]
    confirmed = mapping_service.get_confirmed_mappings(upload.file_id)
    confirmed_fields = {m.target_field for m in confirmed}

    # "GSTIN", "Invoice No", "Taxable Value" are exact/substring matches
    # and should be auto-confirmed as before.
    assert "gstin" in confirmed_fields
    assert "invoice_number" in confirmed_fields
    assert "taxable_value_paise" in confirmed_fields
    # "GST (INR)" only fuzzy-matches gstin/cgst-style fields below 0.75
    # (0.583 for gstin) and must NOT have been auto-confirmed onto any
    # field — it should still show up as unmapped in the preview.
    assert len(confirmed) == 3


# --- Bug fix: no way to recover from a wrongly-typed file that can  ---
# --- never validate, permanently blocking Run Review (screenshot 3) ---
#
# Found from a live screenshot: the user uploaded a period-level GST
# summary file (one row per month, no GSTIN/invoice-number columns —
# see the AUTO_ACCEPT_THRESHOLD test above and the v6 manifest's
# "Open scope question" section) as file type GST. It can never reach
# VALIDATED no matter how its columns are mapped, because it
# genuinely doesn't have the columns "GST Data" requires. Before this
# fix there was no way to remove or reclassify an uploaded file, and
# `unified_review_service.check_review_readiness()` requires every
# uploaded file to be VALIDATED before Run Review is allowed — so
# this one file permanently blocked the whole engagement's review
# with no path forward, and the Upload screen gave no indication of
# which file was blocking or what to do about it.
#
# Fixed: (a) a new `action=delete_file` POST lets a file that hasn't
# reached VALIDATED be removed (upload_service.delete_upload() — see
# its docstring), so the user can remove the wrongly-typed file and
# re-upload it under the correct Data Type; (b) the Upload screen now
# shows an explicit "Not Ready for Run Review Yet" panel naming every
# blocking file when readiness isn't met, instead of just silently
# not showing a Run Review button.

def test_removing_a_file_that_cannot_validate_unblocks_run_review(client):
    _create_and_select_engagement(client)
    _upload_tb(client)
    client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)

    # A GST file shaped like a period summary rather than a per-invoice
    # register — no gstin/invoice_number column at all, so it can never
    # satisfy ESSENTIAL_FIELDS["GST"] no matter how it's mapped.
    r = client.post(
        "/data/upload/",
        data={
            "file": (io.BytesIO(_csv_bytes([{"Period": "Apr-25", "Amount": 1800}])), "gst_summary.csv"),
            "file_type": "GST",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302
    client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)

    from app.services import upload_service
    from app.services import engagement_service
    from app.services import unified_review_service
    engagement = engagement_service.list_engagements()[0]
    uploads = upload_service.list_uploads(engagement.engagement_id)
    bad_file = next(u for u in uploads if u.original_filename == "gst_summary.csv")
    assert bad_file.upload_status != "VALIDATED"  # never had a matching column to map

    readiness = unified_review_service.check_review_readiness(engagement.engagement_id)
    assert readiness.ready is False

    page = body(client.get("/data/upload/"))
    assert "Not Ready for Run Review Yet" in page
    assert "gst_summary.csv" in page
    assert 'name="action" value="delete_file"' in page

    r = client.post("/data/upload/", data={"action": "delete_file", "file_id": bad_file.file_id}, follow_redirects=False)
    assert r.status_code == 302

    uploads_after = upload_service.list_uploads(engagement.engagement_id)
    assert all(u.original_filename != "gst_summary.csv" for u in uploads_after)

    readiness_after = unified_review_service.check_review_readiness(engagement.engagement_id)
    assert readiness_after.ready is True

    page = body(client.get("/data/upload/"))
    assert 'name="run_source" value="upload_quick_action"' in page


def test_cannot_remove_a_file_that_is_already_validated(client):
    _create_and_select_engagement(client)
    _upload_tb(client)
    client.post("/data/upload/", data={"action": "confirm_auto"}, follow_redirects=False)

    from app.services import upload_service
    from app.services import engagement_service
    engagement = engagement_service.list_engagements()[0]
    upload = upload_service.list_uploads(engagement.engagement_id)[0]
    assert upload.upload_status == "VALIDATED"

    r = client.post("/data/upload/", data={"action": "delete_file", "file_id": upload.file_id}, follow_redirects=False)
    assert r.status_code == 200  # re-renders inline with an error, no redirect
    assert "already Validated" in body(r)

    # Untouched — still there, still VALIDATED.
    still_there = upload_service.get_upload(upload.file_id)
    assert still_there is not None
    assert still_there.upload_status == "VALIDATED"

    # And the main table never offers "Remove" for a VALIDATED file.
    page = body(client.get("/data/upload/"))
    assert page.count('name="action" value="delete_file"') == 0
