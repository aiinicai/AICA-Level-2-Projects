"""End-to-end generic pipeline test: local fixture + stubbed LLMs."""

import contextlib
import io
import os

from services.file_source import LocalDirSource
from services.section_pipeline import SectionPipeline


def _run(fixtures_dir):
    task_dir = os.path.join(fixtures_dir, "csv_reconcile")
    pipeline = SectionPipeline(user_id="u", agent_id="a", file_source=LocalDirSource(task_dir))
    with contextlib.redirect_stdout(io.StringIO()):
        return pipeline.run(
            task_folder="/",
            task_description="Reconcile the output table against the input table.",
        )


def test_generic_pipeline_flags_seeded_mismatch(fixtures_dir, stub_llms):
    res = _run(fixtures_dir)

    # Routed to the generic engine (CSV is not a specialization)
    assert res["mode"] == "generic"
    assert res["specialization"] is None

    gv = res["generic_validation"]
    summary = gv["summary"]
    # The fixture seeds a wrong amount on id 3 (error severity) -> overall FAIL
    assert summary["overall_status"] == "FAIL"

    by_id = {r["id"]: r for r in gv["criteria_results"]}
    # Coverage + count pass deterministically; value fails deterministically
    assert by_id["C1"]["status"] == "PASS" and by_id["C1"]["decided_by"] == "deterministic"
    assert by_id["C2"]["status"] == "FAIL" and by_id["C2"]["decided_by"] == "deterministic"
    assert by_id["C3"]["status"] == "PASS" and by_id["C3"]["decided_by"] == "deterministic"
    # Semantic criterion answered by the (stubbed) AI
    assert by_id["C4"]["decided_by"] == "ai"


def test_check_spec_present(fixtures_dir, stub_llms):
    res = _run(fixtures_dir)
    spec = res["check_spec"]
    assert spec and len(spec["criteria"]) == 4
    assert spec["task_summary"]
