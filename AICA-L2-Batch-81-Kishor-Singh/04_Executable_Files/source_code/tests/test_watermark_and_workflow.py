"""Tests for core.watermark_engine and core.workflow_engine (non-Word steps)."""
from core.pdf_engine import open_pdf
from core.watermark_engine import PageNumberOptions, TextWatermarkOptions, add_page_numbers, add_text_watermark
from core.workflow_engine import WorkflowEngine, WorkflowStep, WorkflowStepKind
from core.signature_engine import SignatureApplication
from models.enums import PositionPreset
from models.signature_template import SignatureTemplate
from utils.file_utils import TempWorkspace


def test_text_watermark_all_pages(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 3)
    out = tmp_path / "watermarked.pdf"
    add_text_watermark(src, out, TextWatermarkOptions(text="CONFIDENTIAL", pages_expression="all"))
    with open_pdf(out) as doc:
        for i in range(3):
            assert "confidential" in doc[i].get_text().lower()


def test_text_watermark_selected_pages_only(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 4)
    out = tmp_path / "watermarked.pdf"
    add_text_watermark(src, out, TextWatermarkOptions(text="DRAFT", pages_expression="1"))
    with open_pdf(out) as doc:
        assert "draft" in doc[0].get_text().lower()
        assert "draft" not in doc[1].get_text().lower()


def test_page_numbers_format(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 3)
    out = tmp_path / "numbered.pdf"
    add_page_numbers(src, out, PageNumberOptions(format="Page {n} of {total}", position=PositionPreset.BOTTOM_CENTRE))
    with open_pdf(out) as doc:
        assert "page 1 of 3" in doc[0].get_text().lower()
        assert "page 3 of 3" in doc[2].get_text().lower()


def test_page_numbers_start_number_offset(make_pdf, tmp_path):
    src = make_pdf("doc.pdf", 2)
    out = tmp_path / "numbered.pdf"
    add_page_numbers(src, out, PageNumberOptions(format="{n}", start_number=5))
    with open_pdf(out) as doc:
        assert doc[0].get_text().strip() != ""


def test_workflow_merge_then_sign(make_pdf, sample_signature_png, tmp_path):
    main_doc = make_pdf("main.pdf", 2)
    annexure = make_pdf("annexure.pdf", 3)
    template = SignatureTemplate(
        image_path=str(sample_signature_png),
        position_preset=PositionPreset.BOTTOM_RIGHT,
        page_rule_expression="last",
    )
    steps = [
        WorkflowStep(WorkflowStepKind.MERGE_WITH, {"additional_files": [str(annexure)]}),
        WorkflowStep(WorkflowStepKind.SIGN, {"applications": [SignatureApplication(template=template)]}),
    ]
    final_output = tmp_path / "Agreement_Final.pdf"
    with TempWorkspace(tmp_path) as ws:
        result_path = WorkflowEngine().run(main_doc, steps, ws, final_output)

    with open_pdf(result_path) as doc:
        assert doc.page_count == 5  # 2 + 3
        # NOTE: after garbage-collecting save passes, PyMuPDF can share an
        # empty/near-empty /Resources object across pages that started out
        # identical, which makes Page.get_images() report a false positive
        # on pages that never actually paint the image. The only reliable
        # signal that an image is genuinely rendered on a page is a "Do"
        # (paint XObject) operator in *that page's own* content stream, so
        # we check the raw content stream rather than get_images().
        assert b"/Do" in doc[4].read_contents() or b" Do" in doc[4].read_contents()
        assert b"Do" not in doc[0].read_contents()
