import re
from pathlib import Path


def test_every_onedrive_file_picker_accepts_markdown():
    project = Path(__file__).parents[1]

    for relative_path in ("static/js/agents.js", "static/js/tasks.js"):
        source = (project / relative_path).read_text(encoding="utf-8")
        file_type_lists = re.findall(r"fileTypes:\s*\[([^\]]+)]", source)

        assert file_type_lists
        assert all("'.md'" in file_types for file_types in file_type_lists)


def test_markdown_is_accepted_and_read_as_text(tmp_path):
    from api.agents import allowed_file
    from services.file_processor import extract_text_from_file, load_kb_files, read_workflow_file
    from services.reference_files import extract_file_text
    from services.section2_ingestion import extract_client_context_text, extract_workflow_text

    markdown = tmp_path / "instructions.MD"
    markdown.write_text("# Validation\n\nCheck the final total.", encoding="utf-8")

    assert allowed_file(markdown.name)
    assert "Check the final total." in read_workflow_file(str(markdown))
    assert "Check the final total." in extract_workflow_text(str(markdown))["raw_text"]
    assert "Check the final total." in extract_client_context_text(str(markdown))["text"]
    assert "Check the final total." in extract_text_from_file(str(markdown))
    assert "Check the final total." in extract_file_text(str(markdown))
    assert "Check the final total." in load_kb_files(str(tmp_path))[0]["content"]
