"""SQLite persistence checks. Runs with pytest OR standalone."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from clock45.classify import MICRO, SRC_CERTIFICATE, SRC_DECLARATION, UdyamRecord  # noqa: E402
from clock45.demo_data import build_demo_dataset  # noqa: E402
from clock45.engine import ACC_INVOICE_DATE, run_assessment  # noqa: E402
from clock45.store import DATABASE_FILENAME, Store, StoreError  # noqa: E402


results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name, got, want))
    assert ok, f"{name}: got {got!r}, want {want!r}"


def _demo_store(folder):
    demo = build_demo_dataset()
    store = Store(folder, actor="CA A. Reviewer")
    client_id = store.get_or_create_client(demo["entity_name"], "ABCDE1234F")
    analysis_id = store.start_or_resume_analysis(client_id, demo["fy"])
    total = sum(line.amount for line in demo["purchases"])
    controls = {
        "lines_read": len(demo["purchases"]),
        "total_value_read": total,
        "total_value_accounted_for": total,
        "ties": True,
    }
    store.save_analysis(
        analysis_id,
        stage="vendors",
        purchases=demo["purchases"],
        payments=demo["payments"],
        control_totals=controls,
        source_label="Demo ledger",
        source_type="demo",
    )
    names = {}
    for line in demo["purchases"]:
        names.setdefault(line.vendor_id, line.vendor_name_as_written)
    for vendor_id, record in demo["udyam"].items():
        store.upsert_vendor(
            client_id, record, vendor_name=names.get(vendor_id, vendor_id), changed_by="Demo loader"
        )
    return store, demo, client_id, analysis_id, controls


def test_01_reopen_part_finished_analysis():
    with tempfile.TemporaryDirectory() as folder:
        store, demo, client_id, analysis_id, controls = _demo_store(folder)
        check("01 database in chosen folder", store.path.parent, store.folder)
        check("01 expected filename", store.path.name, DATABASE_FILENAME)
        store.close()

        reopened = Store(folder)
        saved = reopened.load_latest_analysis()
        check("01 same analysis", saved.analysis_id, analysis_id)
        check("01 purchases restored", len(saved.purchases), len(demo["purchases"]))
        check("01 payments restored", len(saved.payments), len(demo["payments"]))
        check("01 control total restored", saved.control_totals["total_value_read"],
              controls["total_value_read"])
        check("01 integrity", reopened.integrity_check(), "ok")
        reopened.close()


def test_02_vendor_audit_is_append_only_and_cross_year():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(folder)
        client_id = store.get_or_create_client("Audit Trail Pvt Ltd", "AAACA1111A")
        record = UdyamRecord(
            vendor_id="V001", udyam_no="UDYAM-MH-01-000001",
            enterprise_class=MICRO, nic_code="25999", activity_label="Fabrication",
            registration_date=date(2021, 4, 1), source=SRC_DECLARATION,
        )
        store.upsert_vendor(client_id, record, vendor_name="Reliable Fabricators", changed_by="Preparer")
        store.upsert_vendor(client_id, record, vendor_name="Reliable Fabricators", changed_by="Preparer")
        record.source = SRC_CERTIFICATE
        record.evidence_file_hash = "sha256:test"
        store.upsert_vendor(client_id, record, vendor_name="Reliable Fabricators", changed_by="Reviewer")
        audit = store.vendor_audit_log(client_id, "V001")
        check("02 only real changes logged", len(audit), 2)
        check("02 who changed", audit[-1]["changed_by"], "Reviewer")
        check("02 evidence captured", audit[-1]["evidence_source"], SRC_CERTIFICATE)
        check("02 changed field explicit", audit[-1]["changes"]["evidence_source"]["after"],
              SRC_CERTIFICATE)

        next_year = store.start_or_resume_analysis(client_id, "2026-27")
        check("02 next year created", bool(next_year), True)
        check("02 vendor persists across years", store.load_vendor_master(client_id)["V001"].source,
              SRC_CERTIFICATE)
        digest = store.add_vendor_evidence(
            client_id, "V001", filename="udyam.pdf", media_type="application/pdf",
            content=b"synthetic certificate", added_by="Reviewer",
        )
        evidence = store.list_vendor_evidence(client_id, "V001")
        check("02 evidence document retained", evidence[0]["sha256"], digest)
        check("02 evidence bytes retained", evidence[0]["bytes"], len(b"synthetic certificate"))
        try:
            store.add_vendor_evidence(
                client_id, "V001", filename="same-again.pdf", media_type="application/pdf",
                content=b"synthetic certificate", added_by="Reviewer",
            )
        except StoreError as exc:
            duplicate_blocked = "already uploaded" in str(exc)
        else:
            duplicate_blocked = False
        check("02 duplicate evidence blocked", duplicate_blocked, True)
        evidence_id = evidence[0]["evidence_id"]
        store.record_evidence_review(
            evidence_id=evidence_id, client_id=client_id, vendor_id="V001",
            parsed={"enterprise_class": "MICRO"}, confirmed={"enterprise_class": "MICRO"},
            conflicts={}, confirmed_by="Reviewer",
            classification_history=[{
                "classification_year": "2025-26", "enterprise_class": "MICRO",
                "classification_date": "2025-04-01",
            }],
        )
        check("02 year history retained", store.classification_history(client_id, "V001")[0]["enterprise_class"], "MICRO")
        with store._transaction():
            try:
                store._connection.execute(
                    "DELETE FROM vendor_classification_audit WHERE audit_id = ?", (audit[0]["audit_id"],)
                )
            except sqlite3.IntegrityError as exc:
                blocked = "append-only" in str(exc)
            else:
                blocked = False
        check("02 audit deletion blocked", blocked, True)
        store.close()


def test_03_completed_run_reproduces_and_is_immutable():
    with tempfile.TemporaryDirectory() as folder:
        store, demo, client_id, analysis_id, _ = _demo_store(folder)
        run = run_assessment(
            entity_name=demo["entity_name"], fy=demo["fy"], operator="CA A. Reviewer",
            purchases=demo["purchases"], payments=demo["payments"], udyam=demo["udyam"],
            acceptance_policy=ACC_INVOICE_DATE,
        )
        run_id = store.save_completed_run(
            analysis_id, run, demo["purchases"], demo["payments"], demo["udyam"],
            entity_pan="ABCDE1234F",
        )
        expected_hash = run.run_hash()
        expected_disallowance = run.disallowance_total
        store.close()

        reopened = Store(folder)
        saved_run, purchases, payments, vendors = reopened.load_completed_run(run_id)
        check("03 hash reproduces", saved_run.run_hash(), expected_hash)
        check("03 number reproduces", saved_run.disallowance_total, expected_disallowance)
        check("03 snapshot purchases", len(purchases), len(demo["purchases"]))
        check("03 snapshot vendors", len(vendors), len(demo["udyam"]))
        check("03 run listed", reopened.list_completed_runs(client_id)[0]["run_id"], run_id)
        reopened.close()

        raw = sqlite3.connect(os.path.join(folder, DATABASE_FILENAME))
        try:
            raw.execute("UPDATE completed_runs SET entity_name = 'Changed' WHERE run_id = ?", (run_id,))
        except sqlite3.IntegrityError as exc:
            update_blocked = "immutable" in str(exc)
        else:
            update_blocked = False
        try:
            raw.execute("DELETE FROM completed_runs WHERE run_id = ?", (run_id,))
        except sqlite3.IntegrityError as exc:
            delete_blocked = "immutable" in str(exc)
        else:
            delete_blocked = False
        raw.close()
        check("03 update blocked", update_blocked, True)
        check("03 delete blocked", delete_blocked, True)


def test_04_mappings_backup_and_restore():
    with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as backups:
        store = Store(folder)
        client_id = store.get_or_create_client("Mapping Ltd", "AAACM2222B")
        mapping = {"invoice_number": "Bill No", "amount": "Gross Amount"}
        store.save_column_mapping(client_id, "purchase", "bill-no|gross-amount", mapping)
        check("04 mapping restored", store.load_column_mapping(
            client_id, "purchase", "bill-no|gross-amount"), mapping)
        backup = store.backup(backups)
        check("04 backup exists", backup.is_file(), True)
        store.get_or_create_client("Added After Backup Ltd")
        check("04 two clients before restore", len(store.list_clients()), 2)
        store.restore(backup)
        check("04 backup rolls back later data", len(store.list_clients()), 1)
        check("04 restored integrity", store.integrity_check(), "ok")
        store.close()


if __name__ == "__main__":
    functions = [value for key, value in sorted(globals().items()) if key.startswith("test_")]
    failed = 0
    for function in functions:
        try:
            function()
        except Exception as exc:
            failed += 1
            print(f"  FAIL  {function.__name__}: {type(exc).__name__}: {exc}")
    for ok, name, got, want in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<37} {got}")
    print(f"\n{len(results)} assertions across {len(functions)} cases · "
          f"{'ALL PASSED' if failed == 0 else f'{failed} FAILED'}")
    sys.exit(1 if failed else 0)
