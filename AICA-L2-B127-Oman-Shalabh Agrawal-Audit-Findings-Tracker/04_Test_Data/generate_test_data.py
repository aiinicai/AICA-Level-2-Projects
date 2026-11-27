"""
Creates the test data files in this folder.

Run from this folder:   python generate_test_data.py

It uses the same sample-data generator that is built into app.py, so the files
here always match what the "Load sample data" button creates.  All text is dummy
text marked [SAMPLE].  No real audit, client or personal data is used.

Files created:
  sample_findings_import.xlsx   ~560 dummy findings (30-50 per department), 14 import columns
  import_with_errors.xlsx       7 rows with deliberate mistakes, to test the import checks
  import_missing_column.xlsx    a file with the "Risk level" column removed (must be refused)
  sample_users.csv              the 30 test users and their test password
  sample_full_register.xlsx     what the system holds after sample data is loaded
                                (sheet 1: current status, sheet 2: wide layout, sheet 3: follow-up history)
"""

import os
import sys
import tempfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "03_Code"))
os.environ["EMAIL_MODE"] = "log"

import pandas as pd  # noqa: E402

import app  # noqa: E402


def main():
    today = date.today()

    # 1. Dummy findings for the Excel import test
    findings = app.generate_sample_findings(seed=42, today=today)
    findings.to_excel(os.path.join(HERE, "sample_findings_import.xlsx"), index=False)
    per_dept = findings.groupby("Department").size()
    print(f"sample_findings_import.xlsx: {len(findings)} rows")
    print(per_dept.to_string())

    # 2. A file with deliberate mistakes
    good = findings.iloc[0].to_dict()

    def variant(serial, **changes):
        row = dict(good)
        row["Serial number"] = serial
        row.update(changes)
        return row

    errors = pd.DataFrame([
        variant(9001),                                                       # valid
        variant(9002, Department="Compliance, Recovery, and Legal"),         # valid (comma style differs)
        variant(9003, Department="Space Department"),                        # unknown department
        variant(9004, **{"Original target date": "not a date"}),             # bad date
        variant(9001),                                                       # duplicate serial number
        variant(9006, **{"Risk level": "Extreme"}),                          # bad risk level
        variant(9007, **{"In-house or external auditor": "Somebody"}),       # bad auditor type
    ], columns=app.MASTER_COLUMNS)
    errors.to_excel(os.path.join(HERE, "import_with_errors.xlsx"), index=False)
    findings.drop(columns=["Risk level"]).head(10).to_excel(os.path.join(HERE, "import_missing_column.xlsx"), index=False)

    # 3. Users
    users = pd.DataFrame(
        [{"username": u, "role": r, "department": d or "", "email": e,
          "test_password": app.get_setting("DEFAULT_PASSWORD", "Test@123")} for u, r, d, e in app.default_users()])
    users.to_csv(os.path.join(HERE, "sample_users.csv"), index=False)
    print(f"sample_users.csv: {len(users)} users")

    # 4. What the system holds after the sample data is loaded
    handle, path = tempfile.mkstemp(suffix=".db")
    os.close(handle)
    db = app.Database(url="", sqlite_path=path)
    app.init_db(db)
    admin = app.authenticate(db, "Audit Admin", app.get_setting("DEFAULT_PASSWORD", "Test@123"))
    info = app.load_sample_data(db, admin, today=today)
    status = app.get_status_table(db, today).drop(columns=["id"])
    wide = app.build_wide_export(db, today)
    history = app.followups_table(db)
    with pd.ExcelWriter(os.path.join(HERE, "sample_full_register.xlsx"), engine="openpyxl") as writer:
        status.to_excel(writer, sheet_name="Current status", index=False)
        wide.to_excel(writer, sheet_name="Wide layout", index=False)
        history.to_excel(writer, sheet_name="Follow-up history", index=False)
    print("sample_full_register.xlsx:", info)
    print("Ageing against original target date:")
    print(app.ageing_counts(app.get_status_table(db, today)).to_string())
    os.remove(path)


if __name__ == "__main__":
    main()
