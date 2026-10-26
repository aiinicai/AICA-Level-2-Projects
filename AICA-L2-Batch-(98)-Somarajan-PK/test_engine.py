"""Run: python test_engine.py   (or pytest). Engine must reconcile both sample banks to zero; Bank A must detect all planted issues."""
import subprocess, sys
from recon_engine import main


def test_pipeline(tmp_path=None):
    import tempfile, pathlib
    tmp = pathlib.Path(tmp_path or tempfile.mkdtemp())
    subprocess.run([sys.executable, "generate_data.py"], check=True)
    a = main(["--data", "sample_data", "--bank", "Bank A", "--out", str(tmp / "a.xlsx")])
    assert a["diff"] == 0 and a["evaluation"]["recall"] == 1.0 and a["evaluation"]["false_positives"] == []
    b = main(["--data", "sample_data", "--bank", "Bank B", "--out", str(tmp / "b.xlsx")])
    assert b["diff"] == 0 and b["evaluation"] is None


if __name__ == "__main__":
    test_pipeline(); print("engine tests pass")
