"""Offline licence and trial checks. Runs with pytest OR standalone."""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from clock45.license import (  # noqa: E402
    LicenceError, LicenceManager, TRIAL_LINE_LIMIT, canonical_payload,
    verify_licence_document,
)
from clock45.store import Store  # noqa: E402


results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name, got, want))
    assert ok, f"{name}: got {got!r}, want {want!r}"


def _signed_document(payload):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return {
        "licence": payload,
        "signature": base64.b64encode(private.sign(canonical_payload(payload))).decode("ascii"),
    }, base64.b64encode(public).decode("ascii")


def test_01_ed25519_signature_and_tamper_detection():
    payload = {"firm_name": "A & Co LLP", "seat_count": 4, "expiry_date": "2030-03-31"}
    document, public = _signed_document(payload)
    verified = verify_licence_document(document, public_key_b64=public)
    check("01 firm verified", verified["firm_name"], "A & Co LLP")
    check("01 seats verified", verified["seat_count"], 4)
    document["licence"]["seat_count"] = 40
    try:
        verify_licence_document(document, public_key_b64=public)
    except LicenceError:
        rejected = True
    else:
        rejected = False
    check("01 tampering rejected", rejected, True)


def test_02_trial_is_local_and_limited():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(folder)
        manager = LicenceManager(store)
        status = manager.status(today=date(2026, 8, 9))
        check("02 trial mode", status.mode, "TRIAL")
        check("02 line limit", status.line_limit, TRIAL_LINE_LIMIT)
        check("02 no internet setting", store.get_setting("trial_started_on"), "2026-08-09")
        check("02 limit accepted", manager.require_analysis(TRIAL_LINE_LIMIT).can_analyse, True)
        try:
            manager.require_analysis(TRIAL_LINE_LIMIT + 1)
        except LicenceError as exc:
            limited = "at most 200" in str(exc)
        else:
            limited = False
        check("02 line 201 rejected", limited, True)
        store.close()


def test_03_trial_expiry_and_clock_rollback():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(folder)
        manager = LicenceManager(store)
        started = date(2026, 1, 1)
        store.set_setting("trial_started_on", started.isoformat())
        store.set_setting("trial_last_seen_on", started.isoformat())
        check("03 day 29 active", manager.status(today=started + timedelta(days=29)).mode, "TRIAL")
        check("03 day 30 expired", manager.status(today=started + timedelta(days=30)).mode,
              "EXPIRED_TRIAL")
        store.set_setting("trial_last_seen_on", "2026-02-01")
        check("03 clock rollback blocked", manager.status(today=date(2026, 1, 31)).mode,
              "TRIAL_CLOCK_ERROR")
        store.close()


def test_04_invalid_installed_file_is_rejected():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(folder)
        source = os.path.join(folder, "forged.json")
        with open(source, "w", encoding="utf-8") as handle:
            json.dump({"licence": {"firm_name": "Forged", "seat_count": 99,
                                   "expiry_date": "2099-01-01"}, "signature": "AAAA"}, handle)
        try:
            LicenceManager(store).install(source)
        except LicenceError:
            rejected = True
        else:
            rejected = False
        check("04 forged licence rejected", rejected, True)
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
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<30} {got}")
    print(f"\n{len(results)} assertions across {len(functions)} cases - "
          f"{'ALL PASSED' if failed == 0 else f'{failed} FAILED'}")
    sys.exit(1 if failed else 0)
