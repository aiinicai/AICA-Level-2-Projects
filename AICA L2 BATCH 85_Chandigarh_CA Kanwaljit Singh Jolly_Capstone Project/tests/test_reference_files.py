"""Reference-file ingestion: extraction + labeled gathering (offline)."""

import os
import shutil
import tempfile

from services.reference_files import extract_file_text, gather_reference_texts


def test_extract_text_csv_and_txt():
    d = tempfile.mkdtemp()
    try:
        csv = os.path.join(d, "ex.csv")
        open(csv, "w").write("id,amount\n1,100\n")
        assert "amount" in extract_file_text(csv)

        txt = os.path.join(d, "notes.txt")
        open(txt, "w").write("Output must include a summary section.")
        assert "summary section" in extract_file_text(txt)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_gather_reference_texts_labels_roles():
    # local files act as "remote" paths; fake downloader just copies them
    d = tempfile.mkdtemp()
    try:
        in_path = os.path.join(d, "good_input.csv")
        out_path = os.path.join(d, "good_output.csv")
        open(in_path, "w").write("id,amount\n1,100\n")
        open(out_path, "w").write("id,amount,status\n1,100,ok\n")

        def fake_downloader(token, remote, dest):
            shutil.copy(remote, dest)

        texts = gather_reference_texts(
            access_token="x",
            reference_file_paths={"example_inputs": [in_path], "example_outputs": [out_path]},
            downloader=fake_downloader,
        )
        joined = "\n".join(texts)
        assert any(t.startswith("[EXAMPLE INPUT]") for t in texts)
        assert any(t.startswith("[EXAMPLE OUTPUT]") for t in texts)
        assert "status" in joined  # output example content present
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_gather_handles_empty():
    assert gather_reference_texts("x", None) == []
    assert gather_reference_texts("x", {}) == []
