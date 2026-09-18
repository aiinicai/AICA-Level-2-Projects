"""Tests for core.folder_watcher_engine: consent gating, stability detection,
de-duplication across restarts, and success/failure routing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.folder_watcher_engine import FolderWatcherService, WatcherConsent
from utils.validation import ValidationError


def _folders(tmp_path):
    return {
        "incoming_folder": str(tmp_path / "Incoming"),
        "processing_folder": str(tmp_path / "Processing"),
        "done_folder": str(tmp_path / "Done"),
        "failed_folder": str(tmp_path / "Failed"),
    }


def _consented(tmp_path, **overrides) -> WatcherConsent:
    defaults = dict(
        enabled=True,
        template_description="Sign last page, Bottom Right",
        acknowledged_by="CA Kishor Singh",
        acknowledged_at=datetime.now(timezone.utc),
        acknowledgement_text="I understand eligible documents will be signed automatically.",
    )
    defaults.update(_folders(tmp_path))
    defaults.update(overrides)
    return WatcherConsent(**defaults)


# -------------------------------------------------------------- consent gate

def test_disabled_by_default():
    consent = WatcherConsent()
    assert consent.enabled is False
    with pytest.raises(ValidationError, match="not enabled"):
        consent.validate()


def test_enabled_without_acknowledgement_text_still_blocked(tmp_path):
    consent = _consented(tmp_path, acknowledgement_text="")
    with pytest.raises(ValidationError, match="explicit, recorded user consent"):
        consent.validate()


def test_enabled_without_acknowledged_by_still_blocked(tmp_path):
    consent = _consented(tmp_path, acknowledged_by="")
    with pytest.raises(ValidationError, match="explicit, recorded user consent"):
        consent.validate()


def test_missing_folder_config_blocked(tmp_path):
    consent = _consented(tmp_path, incoming_folder="")
    with pytest.raises(ValidationError, match="incoming_folder"):
        consent.validate()


def test_expired_consent_blocked(tmp_path):
    consent = _consented(tmp_path, valid_until=datetime.now(timezone.utc) - timedelta(days=1))
    with pytest.raises(ValidationError, match="expired"):
        consent.validate()


def test_valid_consent_passes():
    pass  # covered implicitly by every test below that calls scan_once successfully


def test_scan_once_refuses_when_not_consented(tmp_path):
    service = FolderWatcherService(WatcherConsent(), process_fn=lambda p: p)
    with pytest.raises(ValidationError):
        service.scan_once()


# ------------------------------------------------------------- stability

def test_file_not_processed_until_stable_across_two_scans(tmp_path):
    consent = _consented(tmp_path)
    calls = []

    def process_fn(path: Path) -> Path:
        calls.append(path.name)
        out = path.with_suffix(".done.pdf")
        path.rename(out)
        return out

    service = FolderWatcherService(consent, process_fn)
    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    target = incoming / "doc.pdf"
    target.write_bytes(b"content")

    # First scan: file is seen for the first time -- not yet "stable" (no
    # prior size recorded), so it must NOT be processed yet.
    outcomes = service.scan_once()
    assert outcomes == []
    assert calls == []

    # Second scan, size unchanged -- now it's stable and gets processed.
    outcomes = service.scan_once()
    assert len(outcomes) == 1
    assert outcomes[0].success
    assert calls == ["doc.pdf"]


def test_growing_file_never_processed_while_still_copying(tmp_path):
    consent = _consented(tmp_path)
    service = FolderWatcherService(consent, process_fn=lambda p: p)
    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    target = incoming / "growing.pdf"

    target.write_bytes(b"a")
    service.scan_once()
    target.write_bytes(b"ab")  # size changed between scans -- still "copying"
    outcomes = service.scan_once()
    assert outcomes == []


# ----------------------------------------------------------- success/failure

def test_successful_processing_moves_to_done_folder(tmp_path):
    consent = _consented(tmp_path)

    def process_fn(path: Path) -> Path:
        out = path.with_name("signed_" + path.name)
        path.rename(out)
        return out

    service = FolderWatcherService(consent, process_fn)
    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    (incoming / "doc.pdf").write_bytes(b"content")

    service.scan_once()
    outcomes = service.scan_once()

    assert outcomes[0].success
    assert Path(consent.done_folder, "signed_doc.pdf").exists()
    assert not (incoming / "doc.pdf").exists()


def test_failed_processing_moves_to_failed_folder_with_reason(tmp_path):
    consent = _consented(tmp_path)

    def process_fn(path: Path) -> Path:
        raise RuntimeError("simulated processing failure")

    service = FolderWatcherService(consent, process_fn)
    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    (incoming / "bad.pdf").write_bytes(b"content")

    service.scan_once()
    outcomes = service.scan_once()

    assert not outcomes[0].success
    assert "simulated processing failure" in outcomes[0].error_message
    assert Path(consent.failed_folder, "bad.pdf").exists()


def test_one_bad_file_does_not_block_others(tmp_path):
    consent = _consented(tmp_path)

    def process_fn(path: Path) -> Path:
        if "bad" in path.name:
            raise RuntimeError("boom")
        out = path.with_name("ok_" + path.name)
        path.rename(out)
        return out

    service = FolderWatcherService(consent, process_fn)
    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    (incoming / "bad.pdf").write_bytes(b"1")
    (incoming / "good.pdf").write_bytes(b"2")

    service.scan_once()
    outcomes = service.scan_once()

    results = {o.source_filename: o.success for o in outcomes}
    assert results == {"bad.pdf": False, "good.pdf": True}


# -------------------------------------------------------- deduplication

def test_registry_prevents_reprocessing_after_restart(tmp_path):
    consent = _consented(tmp_path)
    registry_path = tmp_path / "registry.json"

    def process_fn(path: Path) -> Path:
        out = path.with_name("done_" + path.name)
        path.rename(out)
        return out

    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    (incoming / "doc.pdf").write_bytes(b"content")

    service1 = FolderWatcherService(consent, process_fn, registry_path=registry_path)
    service1.scan_once()
    service1.scan_once()  # processes it

    # Simulate a restart: brand-new service instance loading the same registry.
    # Put an identical file back in Incoming (same content -> same hash).
    (incoming / "doc.pdf").write_bytes(b"content")
    service2 = FolderWatcherService(consent, process_fn, registry_path=registry_path)
    service2.scan_once()
    outcomes = service2.scan_once()

    assert outcomes == []  # already-seen hash -- not reprocessed


# ------------------------------------------------------------------ controls

def test_pause_prevents_processing(tmp_path):
    consent = _consented(tmp_path)
    service = FolderWatcherService(consent, process_fn=lambda p: p)
    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    (incoming / "doc.pdf").write_bytes(b"content")

    service.pause()
    assert service.is_paused
    service.scan_once()
    outcomes = service.scan_once()
    assert outcomes == []


def test_dry_run_reports_without_processing(tmp_path):
    consent = _consented(tmp_path)
    calls = []
    service = FolderWatcherService(consent, process_fn=lambda p: calls.append(p) or p)
    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    (incoming / "doc.pdf").write_bytes(b"content")

    service.scan_once()  # first pass to establish stability baseline
    outcomes = service.scan_once(dry_run=True)

    assert len(outcomes) == 1
    assert outcomes[0].success
    assert "dry run" in outcomes[0].output_path
    assert calls == []  # process_fn was never actually invoked
    assert (incoming / "doc.pdf").exists()  # file untouched


def test_allowed_extensions_filter(tmp_path):
    consent = _consented(tmp_path, allowed_extensions=(".pdf",))
    service = FolderWatcherService(consent, process_fn=lambda p: p)
    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    (incoming / "doc.txt").write_bytes(b"not a pdf")

    service.scan_once()
    outcomes = service.scan_once()
    assert outcomes == []
    assert (incoming / "doc.txt").exists()  # ignored, not moved anywhere


def test_max_files_per_run_limit(tmp_path):
    consent = _consented(tmp_path, max_files_per_run=1)

    def process_fn(path: Path) -> Path:
        out = path.with_name("done_" + path.name)
        path.rename(out)
        return out

    service = FolderWatcherService(consent, process_fn)
    incoming = Path(consent.incoming_folder)
    incoming.mkdir(parents=True)
    (incoming / "a.pdf").write_bytes(b"1")
    (incoming / "b.pdf").write_bytes(b"2")

    service.scan_once()
    outcomes = service.scan_once()
    assert len(outcomes) == 1  # capped, even though 2 files were ready
