"""Phase 3: every answer the screens need must equal the Node app's answer, figure by figure.

The expected answers in tests/golden/*/answers were produced by running the original Node app on the same fictional
XML files (tools/node/golden.ts). `small`: Tally stock valuations, bill-wise ageing, cost centres.
`manual`: the same books with a manual Stock-in-Hand ledger (different stock path).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from compare_golden import run  # noqa: E402

G = Path(__file__).parent / "golden"
REQS = str(G / "golden_requests.json")


def files(*dirs_and_names):
    return [str(G / d / "inputs" / n) for d, n in dirs_and_names]


@pytest.mark.parametrize("name", ["small", "manual"])
def test_python_equals_node(name):
    small = sorted((G / "small" / "inputs").glob("*.xml"))
    inputs = [str(p) for p in small] if name == "small" else [str(G / "manual" / "inputs" / "01-masters.xml"), str(G / "small" / "inputs" / "02-daybook.xml")]
    bad, stats = run(str(G / name / "answers"), inputs, verbose=False, reqs_path=REQS)
    assert bad == 0, stats["failures"]
    assert stats["values"] > 20000 and stats["answers"] == 33
