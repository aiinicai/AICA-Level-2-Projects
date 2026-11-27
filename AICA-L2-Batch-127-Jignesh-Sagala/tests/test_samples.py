"""Samples test. The made-up statements in samples/ are locked, carry the made-up holder (BusyMe, PAN ABCDE1234F),
and every reader passes every check on them. A wrong password is refused. Also: no other person's name is in them.
"""
import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "app"))
import demo_readers as demo   # noqa: E402
import cdsl                   # noqa: E402


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = demo.main()
    out = buf.getvalue()
    assert rc == 0 and "RESULT: ALL PASS" in out, "readers pass on the samples"
    assert " FAIL" not in out.replace("0 FAIL", ""), "no FAIL line"
    files = sorted(demo.SAMPLES.glob("*.pdf"))
    assert len(files) == 6, files
    for p in files:
        assert cdsl.PasswordError is not None
        try:
            cdsl.read_rows(p, "wrong")
            raise AssertionError(f"{p.name} is not locked")
        except cdsl.PasswordError:
            pass
    text = {p.name: " ".join(" ".join(pg) for pg in cdsl.read_rows(p, demo.PW)) for p in files}
    for n in ("cdsl_made_up.pdf", "contract_note_1.pdf", "contract_note_2.pdf", "funds_ledger.pdf"):
        assert "BusyMe" in text[n] and "ABCDE1234F" in text[n], n
    for n in ("kotak_a.pdf", "indus_a.pdf"):
        assert "BusyMe" in text[n], n
    assert not any(re.search(r"MADE UP CLIENT|Kumar", t) for t in text.values()), "no other holder name"
    print("  samples test: 6 locked made-up statements, holder BusyMe, every reader check passes, wrong password refused")
    print("ALL PASS")


if __name__ == "__main__":
    main()
