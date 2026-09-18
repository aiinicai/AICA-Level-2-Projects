"""Integration test for the Sign PDF tab's actual processing logic.

Exercises :meth:`ui.sign_tab.SignTab.build_process_fn` directly -- the real
per-file signing closure used by the batch worker -- without driving any
modal Qt dialog (those require a live desktop and a human/timer to close).
This is the most important workflow in the whole application: add a file,
configure one signature layer, sign it, and confirm the output is correct
and the database was updated.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from core.pdf_engine import open_pdf
from models.enums import CollisionPolicy, NamingMode, PositionPreset
from ui.app_context import AppContext
from ui.sign_tab import SignTab
from utils.config_manager import ConfigManager
from utils.database import Database
from utils.file_utils import TempWorkspace


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def sign_tab(qapp, tmp_path):
    cfg = ConfigManager(app_data_dir=tmp_path / "appdata")
    db = Database(cfg.get_database_path())
    ctx = AppContext(config=cfg, database=db, operator="tester")
    return SignTab(ctx)


def test_build_process_fn_signs_last_page_and_records_audit(sign_tab, make_pdf, sample_signature_png, tmp_path):
    src = make_pdf("Agreement.pdf", 4)
    layer = sign_tab.layers[0]
    layer.edit_image_path.setText(str(sample_signature_png))
    layer.combo_position.setCurrentText(PositionPreset.BOTTOM_RIGHT.value)
    layer.combo_page_mode.setCurrentText("Last Page")

    sign_tab._add_file_paths([str(src)])
    job = sign_tab.jobs[0]

    out_dir = tmp_path / "out"
    with TempWorkspace(tmp_path / "tmp") as ws:
        process_fn = sign_tab.build_process_fn(
            str(out_dir),
            NamingMode.ADD_SUFFIX,
            "_Signed",
            "Signed_",
            CollisionPolicy.RENAME,
            [layer.get_template() for layer in sign_tab.layers],
            {},
            {},
            ws,
        )
        process_fn(job)

    assert job.error_message == ""
    assert job.selected_pages == "4"
    from pathlib import Path

    out_file = Path(job.output_path)
    assert out_file.exists()
    assert out_file.name == "Agreement_Signed.pdf"
    with open_pdf(out_file) as doc:
        assert doc.page_count == 4
        assert b"Do" in doc[3].read_contents()
        assert b"Do" not in doc[0].read_contents()

    # Original untouched.
    assert src.exists()

    # Audit trail + recent-job history were recorded.
    assert len(sign_tab.ctx.database.list_audit_entries()) == 1
    assert len(sign_tab.ctx.database.list_recent_jobs()) == 1


def test_build_process_fn_respects_per_file_override(sign_tab, make_pdf, sample_signature_png, tmp_path):
    from ui.sign_tab import FileOverride

    src = make_pdf("Contract.pdf", 6)
    layer = sign_tab.layers[0]
    layer.edit_image_path.setText(str(sample_signature_png))
    layer.combo_page_mode.setCurrentText("Last Page")  # global rule

    sign_tab._add_file_paths([str(src)])
    job = sign_tab.jobs[0]
    overrides = {job.job_id: FileOverride(page_rule_expression="1")}  # override -> page 1 only

    out_dir = tmp_path / "out"
    with TempWorkspace(tmp_path / "tmp") as ws:
        process_fn = sign_tab.build_process_fn(
            str(out_dir),
            NamingMode.ADD_SUFFIX,
            "_Signed",
            "Signed_",
            CollisionPolicy.RENAME,
            [layer.get_template() for layer in sign_tab.layers],
            overrides,
            {},
            ws,
        )
        process_fn(job)

    assert job.selected_pages == "1"  # override wins over the global "last" rule


def test_build_process_fn_skips_on_collision(sign_tab, make_pdf, sample_signature_png, tmp_path):
    src = make_pdf("Duplicate.pdf", 2)
    layer = sign_tab.layers[0]
    layer.edit_image_path.setText(str(sample_signature_png))

    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "Duplicate_Signed.pdf").write_text("existing")

    sign_tab._add_file_paths([str(src)])
    job = sign_tab.jobs[0]

    with TempWorkspace(tmp_path / "tmp") as ws:
        process_fn = sign_tab.build_process_fn(
            str(out_dir),
            NamingMode.ADD_SUFFIX,
            "_Signed",
            "Signed_",
            CollisionPolicy.SKIP,
            [layer.get_template() for layer in sign_tab.layers],
            {},
            {},
            ws,
        )
        process_fn(job)

    from models.enums import JobStatus

    assert job.status == JobStatus.SKIPPED
