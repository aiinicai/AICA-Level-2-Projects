# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Bulk Upload page: import many leases from an Excel / CSV file (no AI involved)."""
import hashlib

import pandas as pd
import streamlit as st

from auth_ui import require_login
from core.bulk import (
    MAX_BULK_ROWS,
    BulkFileError,
    analyse_bulk_file,
    build_template_bytes,
    error_frame,
    valid_frame,
)
from core.workflow import import_bulk_lease
from db.database import get_session
from lease_ui import amount_table

st.set_page_config(page_title="LeaseIQ Pro - Bulk Upload", page_icon="📥", layout="wide")
user = require_login("edit")


def _show_summary(summary: dict) -> None:
    """The result of an import: headline, imported leases, and anything that failed."""
    st.success(summary["message"])
    if summary["imported"]:
        st.dataframe(pd.DataFrame(summary["imported"]), hide_index=True)
    for failure in summary["failed"]:
        st.error("Row {} could not be imported: {}".format(failure["Row"], failure["Reason"]))
    st.page_link("pages/2_Leases.py", label="Open the Leases page to see them")


st.title("Bulk Upload")
st.caption(
    "Import many leases at once from an Excel or CSV file. No AI is used: the values you provide are checked "
    "with the same rules as the validation screen, then calculated."
)

st.subheader("1. Download the template")
st.download_button(
    "Download template (.xlsx)",
    data=build_template_bytes(),
    file_name="leaseiq_bulk_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="download_template",
)
st.caption(
    "Fill in one lease per row on the 'Leases' sheet (up to {} per file). The 'Instructions' sheet explains every "
    "column and the 'Example' sheet shows a complete row. A blank currency uses your default currency ({}).".format(
        MAX_BULK_ROWS, user["default_currency"]
    )
)

st.subheader("2. Upload your file")
uploaded = st.file_uploader("Excel (.xlsx) or CSV file", type=["xlsx", "csv"], key="bulk_file")
if uploaded is None:
    st.stop()

data = uploaded.getvalue()
try:
    report = analyse_bulk_file(uploaded.name, data, default_currency=user["default_currency"])
except BulkFileError as exc:
    st.error(str(exc))
    st.stop()

valid_count, error_count = len(report["valid"]), len(report["errors"])
columns = st.columns(3)
columns[0].metric("Rows read", report["total_rows"])
columns[1].metric("Valid", valid_count)
columns[2].metric("With errors", error_count)
if report["ignored_columns"]:
    st.warning("These columns are not part of the template and were ignored: {}".format(", ".join(report["ignored_columns"])))

st.markdown("#### Valid rows ({})".format(valid_count))
if valid_count:
    st.dataframe(amount_table(valid_frame(report), None, user["number_format"]), hide_index=True)
else:
    st.info("No valid rows.")

st.markdown("#### Rows with errors ({})".format(error_count))
if error_count:
    st.dataframe(
        error_frame(report),
        hide_index=True,
        column_config={"Problems": st.column_config.TextColumn("Problems", width="large")},
    )
    st.caption("Fix these rows in your file and upload it again. They will NOT be imported.")
else:
    st.success("No errors found.")

st.subheader("3. Import")
file_id = hashlib.sha256(data).hexdigest()
done = st.session_state.setdefault("bulk_imported", {})
if file_id in done:
    _show_summary(done[file_id])
    st.info("This file has already been imported. Upload a corrected or different file to import more.")
elif not valid_count:
    st.info("There is nothing to import yet: no valid rows.")
else:
    st.write("Only the {} valid row(s) will be imported and calculated. Rows with errors are skipped.".format(valid_count))
    if st.button("Import valid rows", key="bulk_import", type="primary"):
        progress = st.progress(0.0, text="Starting the import...")
        imported, failed = [], []
        for index, item in enumerate(report["valid"], start=1):
            try:
                with get_session() as session:
                    case = import_bulk_lease(
                        session,
                        user["user_id"],
                        user["role"],
                        item["values"],
                        framework=item["framework"],
                        override=item["override"],
                        filename=uploaded.name,
                        source_row=item["row"],
                    )
                    imported.append(
                        {"Row": item["row"], "Lease": case.lease_ref, "Lessor": case.lessor_name, "Status": case.status}
                    )
            except (ValueError, PermissionError) as exc:
                failed.append({"Row": item["row"], "Reason": str(exc)})
            progress.progress(index / valid_count, text="Imported {} of {} valid rows".format(index, valid_count))
        message = "{} of {} leases imported successfully".format(len(imported), report["total_rows"])
        if error_count:
            message += " ({} row(s) with errors were not imported)".format(error_count)
        done[file_id] = {"message": message, "imported": imported, "failed": failed}
        _show_summary(done[file_id])
