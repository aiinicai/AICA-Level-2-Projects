"""Safe, user-friendly RCM spreadsheet import helpers."""

import csv
import io

import pandas as pd


REQUIRED_RCM_COLUMNS = {"risk description", "control description"}


def _normalise_heading(value):
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _promote_detected_header(raw_frame):
    """Find an RCM header in the first ten rows and promote it to columns."""
    scan_limit = min(10, len(raw_frame.index))
    for row_index in range(scan_limit):
        headings = [_normalise_heading(value) for value in raw_frame.iloc[row_index].tolist()]
        if REQUIRED_RCM_COLUMNS.issubset(set(headings)):
            columns = []
            for column_index, value in enumerate(raw_frame.iloc[row_index].tolist(), start=1):
                label = str(value).strip() if pd.notna(value) else ""
                columns.append(label or f"Column_{column_index}")
            data = raw_frame.iloc[row_index + 1 :].copy()
            data.columns = columns
            return data.dropna(how="all").reset_index(drop=True)
    return None


def _repair_legacy_csv(text_payload):
    """Repair older seven-column samples whose comma text was not quoted."""
    rows = list(csv.reader(io.StringIO(text_payload)))
    if not rows:
        raise ValueError("The CSV file is empty.")
    header = rows[0]
    repaired_rows = []
    control_types = {"preventive", "detective", "directive", "corrective", "compensating"}
    for line_number, row in enumerate(rows[1:], start=2):
        if not row or not any(str(value).strip() for value in row):
            continue
        if len(row) == len(header):
            repaired_rows.append(row)
            continue
        if len(header) == 7 and len(row) > 7:
            control_id_index = next(
                (idx for idx in range(2, len(row)) if str(row[idx]).strip().upper().startswith(("CTL-", "CTRL-"))),
                None,
            )
            type_index = next(
                (
                    idx
                    for idx in range((control_id_index or 2) + 1, len(row))
                    if str(row[idx]).strip().lower() in control_types
                ),
                None,
            )
            if control_id_index is not None and type_index is not None:
                repaired_rows.append(
                    [
                        row[0],
                        row[1],
                        ", ".join(row[2:control_id_index]),
                        row[control_id_index],
                        ", ".join(row[control_id_index + 1 : type_index]),
                        row[type_index],
                        ", ".join(row[type_index + 1 :]),
                    ]
                )
                continue
        raise ValueError(
            f"CSV row {line_number} has {len(row)} values but the header has {len(header)}. "
            "Download a fresh AuditVault template and keep description text inside quoted cells."
        )
    return pd.DataFrame(repaired_rows, columns=header)


def read_uploaded_rcm(uploaded_file):
    """Read RCM CSV/XLSX files and return a validated, clean dataframe."""
    payload = uploaded_file.getvalue()
    filename = uploaded_file.name.lower()

    if filename.endswith(".xlsx"):
        raw_frame = pd.read_excel(io.BytesIO(payload), header=None)
        frame = _promote_detected_header(raw_frame)
        if frame is None:
            frame = pd.read_excel(io.BytesIO(payload))
    elif filename.endswith(".csv"):
        text_payload = payload.decode("utf-8-sig")
        try:
            frame = pd.read_csv(io.StringIO(text_payload), sep=None, engine="python")
        except pd.errors.ParserError:
            frame = _repair_legacy_csv(text_payload)
        promoted = _promote_detected_header(frame.reset_index(drop=False))
        if promoted is not None:
            frame = promoted
    else:
        raise ValueError("Unsupported file type. Upload an .xlsx or .csv file.")

    frame = frame.dropna(how="all").reset_index(drop=True)
    normalised = {_normalise_heading(column): column for column in frame.columns}
    missing = sorted(REQUIRED_RCM_COLUMNS.difference(normalised))
    if missing:
        detected = ", ".join(str(column) for column in frame.columns[:10]) or "none"
        raise ValueError(
            "Missing required column(s): "
            + ", ".join(item.title() for item in missing)
            + f". Detected columns: {detected}."
        )
    if frame.empty:
        raise ValueError("The RCM file contains headers but no data rows.")
    return frame
