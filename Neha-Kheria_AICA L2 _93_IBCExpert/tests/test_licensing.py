from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import LicenceError
from app.core.time import FixedClock, to_utc_iso
from app.db.connection import connect
from app.db.migrate import migrate
from app.licensing.entitlement import Entitlement, issue_credentials, verify_credentials
from app.licensing.service import LicenseService
from app.licensing.trial import TrialService
from app.security import ed25519

UTC = timezone.utc


def make_trial(tmp_path, clock):
    return TrialService(
        tmp_path / "a" / "trial.bin", tmp_path / "b" / "trial.bin",
        tmp_path / "a" / "secret.bin", tmp_path / "b" / "secret.bin",
        clock=clock,
    )


def entitlement(request_code, now, **overrides):
    values = dict(
        protocol=1,
        licence_id="LIC-2026-0001",
        licence_type="PROFESSIONAL",
        customer_name="Test Insolvency Professional",
        organisation="Test Practice",
        email_reference="reference@example.invalid",
        issued_at=to_utc_iso(now),
        starts_at=to_utc_iso(now),
        expires_at=to_utc_iso(now + timedelta(days=365)),
        device_request_code=request_code,
        device_allowance=1,
        features=("client_management", "legal_database", "form_generation"),
        notes=None,
    )
    values.update(overrides)
    return Entitlement(**values)


def test_trial_persists_expires_and_detects_clock_rollback(tmp_path):
    start = datetime(2026, 1, 1, 12, tzinfo=UTC)
    clock = FixedClock(start)
    trial = make_trial(tmp_path, clock)
    initial = trial.check()
    assert initial.mode == "TRIAL"
    assert initial.days_remaining == 30

    # New service instance proves restart does not reset the trial.
    clock.value = start + timedelta(days=29)
    restarted = make_trial(tmp_path, clock).check()
    assert restarted.days_remaining == 1
    assert restarted.request_code == initial.request_code

    clock.value = start + timedelta(days=30)
    assert make_trial(tmp_path, clock).check().mode == "EXPIRED"

    # Move backwards after a higher time was securely recorded.
    clock.value = start + timedelta(days=10)
    anomaly = make_trial(tmp_path, clock).check()
    assert anomaly.mode == "CLOCK_ANOMALY"
    assert not anomaly.normal_use_allowed


def test_trial_corruption_is_not_treated_as_a_new_trial(tmp_path):
    clock = FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    trial = make_trial(tmp_path, clock)
    trial.check()
    primary = tmp_path / "a" / "trial.bin"
    changed = bytearray(primary.read_bytes())
    changed[-1] ^= 1
    primary.write_bytes(changed)
    with pytest.raises(Exception):
        make_trial(tmp_path, clock).check()


def test_signed_offline_activation_validates_and_tampering_fails(tmp_path):
    now = datetime(2026, 2, 1, tzinfo=UTC)
    clock = FixedClock(now)
    trial = make_trial(tmp_path, clock)
    request = trial.check().request_code
    seed = bytes(range(32))
    public = ed25519.publickey_from_seed(seed)
    activation_id, activation_code = issue_credentials(entitlement(request, now), seed)
    valid = verify_credentials(activation_id, activation_code, public, request, now)
    assert valid.licence_id == "LIC-2026-0001"

    changed = activation_id[:-1] + ("A" if activation_id[-1] != "A" else "B")
    with pytest.raises(LicenceError):
        verify_credentials(changed, activation_code, public, request, now)
    changed_signature = activation_code[:-1] + ("A" if activation_code[-1] != "A" else "B")
    with pytest.raises(LicenceError):
        verify_credentials(activation_id, changed_signature, public, request, now)


def test_device_bound_activation_rejects_other_installation(tmp_path):
    now = datetime(2026, 2, 1, tzinfo=UTC)
    seed = bytes(range(32))
    public = ed25519.publickey_from_seed(seed)
    request_a = make_trial(tmp_path / "one", FixedClock(now)).check().request_code
    request_b = make_trial(tmp_path / "two", FixedClock(now)).check().request_code
    assert request_a != request_b
    activation_id, activation_code = issue_credentials(entitlement(request_a, now), seed)
    with pytest.raises(LicenceError):
        verify_credentials(activation_id, activation_code, public, request_b, now)


def test_complete_trial_expiry_activation_and_restart_sequence(tmp_path):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    clock = FixedClock(start)
    trial = make_trial(tmp_path, clock)
    request = trial.check().request_code
    clock.value = start + timedelta(days=31)
    assert trial.check().mode == "EXPIRED"

    seed = bytes(range(32))
    public = ed25519.publickey_from_seed(seed)
    activation_id, activation_code = issue_credentials(
        entitlement(request, clock.value, expires_at=None), seed
    )
    db_path = tmp_path / "licence.sqlite3"
    db = connect(db_path)
    migrate(db)
    service = LicenseService(db, trial, public, clock=clock)
    service.activate(activation_id, activation_code)
    assert service.status().mode == "LICENSED"
    assert service.has_feature("client_management")
    assert not service.has_feature("semantic_search")
    db.close()

    # Re-open database and trial stores to prove activation persists.
    reopened = connect(db_path)
    restarted_service = LicenseService(reopened, make_trial(tmp_path, clock), public, clock=clock)
    assert restarted_service.status().mode == "LICENSED"
    assert restarted_service.has_feature("form_generation")
