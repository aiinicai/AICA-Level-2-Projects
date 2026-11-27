"""Form 26AS helper: the parts that can be checked without the portal."""
import builtins
from pathlib import Path

from advtax import portal_26as as p


def test_valid_pan():
    assert p.valid_pan("abcde1234f") and p.valid_pan(" ABCDE1234F ")
    assert not p.valid_pan("ABCDE12345") and not p.valid_pan("") and not p.valid_pan("ABCD1234F")


def test_assessment_year():
    assert p.assessment_year("2026-27") == "2027-28"
    assert p.assessment_year("2099-00") == "2100-01"


def test_safe_folder_name():
    assert p.safe_folder_name('A/B: "C" <D>?') == "A B C D"
    assert p.safe_folder_name("  ...  ") == "client"


def test_downloaded_files_skip_partial_and_status(tmp_path: Path):
    for name in ("26AS.pdf", "x.crdownload", "_status.json"):
        (tmp_path / name).write_text("x")
    assert [f.name for f in p.downloaded_files(tmp_path)] == ["26AS.pdf"]
    assert p.downloaded_files(tmp_path / "missing") == []


def test_status_round_trip(tmp_path: Path):
    s = p.Status(tmp_path / "sub" / "_status.json")
    s.say("Portal opened.")
    s.files(["26AS.pdf"])
    s.say("Saved.", "done")
    data = p.read_status(tmp_path / "sub" / "_status.json")
    assert data["state"] == "done" and data["files"] == ["26AS.pdf"]
    assert [x["message"] for x in data["steps"]] == ["Portal opened.", "Saved."]
    assert p.read_status(tmp_path / "nothing.json") is None


def test_run_without_selenium_fails_cleanly(tmp_path: Path, monkeypatch):
    real = builtins.__import__

    def no_selenium(name, *a, **k):
        if name == "selenium" or name.startswith("selenium."):
            raise ImportError("no selenium")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_selenium)
    code = p.run("ABCDE1234F", tmp_path / "out", tmp_path / "out" / "_status.json")
    data = p.read_status(tmp_path / "out" / "_status.json")
    assert code == 2 and data["state"] == "failed" and "not installed" in data["steps"][-1]["message"]
