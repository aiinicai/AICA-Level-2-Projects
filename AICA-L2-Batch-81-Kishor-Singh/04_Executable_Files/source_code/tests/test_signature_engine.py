"""Tests for core.signature_engine: image prep, position math, PDF stamping."""
import fitz
import pytest

from core.pdf_engine import open_pdf
from core.signature_engine import (
    MM_TO_PT,
    SignatureApplication,
    SignatureImageProcessor,
    apply_signatures_to_pdf,
    resolve_placement,
)
from models.enums import PositionPreset
from models.signature_template import SignatureTemplate
from tests.conftest import A4, LEGAL


# ------------------------------------------------------------------ image prep

def test_autocrop_trims_transparent_margin(sample_signature_png):
    img = SignatureImageProcessor.load(sample_signature_png)
    assert img.size == (400, 200)
    cropped = SignatureImageProcessor.autocrop(img)
    # Ink was drawn at x:[100,300) y:[80,120) with 4px padding -> much smaller than original.
    assert cropped.width < img.width
    assert cropped.height < img.height
    assert cropped.width <= 220
    assert cropped.height <= 60


def test_resize_maintains_aspect_ratio():
    from PIL import Image

    img = Image.new("RGBA", (400, 200), (0, 0, 0, 255))
    resized = SignatureImageProcessor.resize(img, 100, 100, maintain_aspect=True)
    # Original ratio 2:1 must be preserved even though target box is square.
    assert resized.width == 100
    assert resized.height == 50


def test_resize_without_aspect_ratio_stretches():
    from PIL import Image

    img = Image.new("RGBA", (400, 200), (0, 0, 0, 255))
    resized = SignatureImageProcessor.resize(img, 100, 100, maintain_aspect=False)
    assert resized.size == (100, 100)


def test_opacity_reduces_alpha_channel():
    from PIL import Image

    img = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
    faded = SignatureImageProcessor.apply_opacity(img, 50.0)
    r, g, b, a = faded.split()
    assert list(a.getdata())[0] == 127


def test_opacity_100_is_noop():
    from PIL import Image

    img = Image.new("RGBA", (10, 10), (0, 0, 0, 200))
    result = SignatureImageProcessor.apply_opacity(img, 100.0)
    assert list(result.split()[3].getdata())[0] == 200


def test_rotate_expands_canvas_for_non_right_angle():
    from PIL import Image

    img = Image.new("RGBA", (100, 50), (0, 0, 0, 255))
    rotated = SignatureImageProcessor.rotate(img, 45)
    assert rotated.width > 100 or rotated.height > 50


def test_prepare_full_pipeline(sample_signature_png):
    prepared = SignatureImageProcessor.prepare(
        sample_signature_png, autocrop=True, target_width_px=200, target_height_px=100, opacity_pct=60
    )
    assert prepared.width_px <= 200
    assert prepared.height_px <= 100
    assert len(prepared.png_bytes) > 0


# ------------------------------------------------------------- position math

@pytest.mark.parametrize(
    "preset",
    [
        PositionPreset.BOTTOM_LEFT,
        PositionPreset.BOTTOM_CENTRE,
        PositionPreset.BOTTOM_RIGHT,
        PositionPreset.TOP_LEFT,
        PositionPreset.TOP_CENTRE,
        PositionPreset.TOP_RIGHT,
        PositionPreset.CENTRE,
    ],
)
def test_resolve_placement_stays_within_page_bounds(preset):
    template = SignatureTemplate(position_preset=preset, width_pct=20, height_pct=8, margin_mm=10)
    placement = resolve_placement(template, *A4)
    assert placement.x_pt >= 0
    assert placement.y_pt >= 0
    assert placement.x_pt + placement.width_pt <= A4[0] + 0.01
    assert placement.y_pt + placement.height_pt <= A4[1] + 0.01


def test_bottom_right_respects_margin():
    template = SignatureTemplate(position_preset=PositionPreset.BOTTOM_RIGHT, width_pct=20, height_pct=8, margin_mm=10)
    placement = resolve_placement(template, *A4)
    margin_pt = 10 * MM_TO_PT
    expected_x = A4[0] - margin_pt - placement.width_pt
    expected_y = A4[1] - margin_pt - placement.height_pt
    assert placement.x_pt == pytest.approx(expected_x, abs=0.5)
    assert placement.y_pt == pytest.approx(expected_y, abs=0.5)


def test_same_template_scales_proportionally_across_page_sizes():
    """The core requirement: percentage sizing keeps a template correct on any page size."""
    template = SignatureTemplate(position_preset=PositionPreset.BOTTOM_RIGHT, width_pct=20, height_pct=8, margin_mm=10)
    a4_placement = resolve_placement(template, *A4)
    legal_placement = resolve_placement(template, *LEGAL)
    assert a4_placement.width_pt == pytest.approx(A4[0] * 0.2)
    assert legal_placement.width_pt == pytest.approx(LEGAL[0] * 0.2)


def test_custom_position_uses_percentages():
    template = SignatureTemplate(
        position_preset=PositionPreset.CUSTOM, custom_x_pct=50, custom_y_pct=50, width_pct=10, height_pct=5
    )
    placement = resolve_placement(template, *A4)
    assert placement.x_pt == pytest.approx(A4[0] * 0.5, abs=0.5)
    assert placement.y_pt == pytest.approx(A4[1] * 0.5, abs=0.5)


def test_oversized_template_is_clamped_onto_page():
    template = SignatureTemplate(position_preset=PositionPreset.BOTTOM_RIGHT, width_pct=95, height_pct=95, margin_mm=50)
    placement = resolve_placement(template, *A4)
    assert placement.x_pt >= 0
    assert placement.y_pt >= 0


# --------------------------------------------------------------- end to end

def test_apply_signature_to_last_page(make_pdf, sample_signature_png, tmp_path):
    src = make_pdf("doc.pdf", 5)
    template = SignatureTemplate(
        image_path=str(sample_signature_png),
        position_preset=PositionPreset.BOTTOM_RIGHT,
        page_rule_expression="last",
    )
    out = tmp_path / "doc_signed.pdf"
    outcome = apply_signatures_to_pdf(src, out, [SignatureApplication(template=template)])
    assert outcome.signed_pages == [5]
    assert out.exists()
    with open_pdf(out) as doc:
        assert doc.page_count == 5
        # The last page should now contain an embedded image XObject.
        assert len(doc[4].get_images()) >= 1
        assert len(doc[0].get_images()) == 0


def test_apply_signature_all_pages(make_pdf, sample_signature_png, tmp_path):
    src = make_pdf("doc2.pdf", 3)
    template = SignatureTemplate(image_path=str(sample_signature_png), page_rule_expression="all")
    out = tmp_path / "doc2_signed.pdf"
    outcome = apply_signatures_to_pdf(src, out, [SignatureApplication(template=template)])
    assert outcome.signed_pages == [1, 2, 3]
    with open_pdf(out) as doc:
        for i in range(3):
            assert len(doc[i].get_images()) >= 1


def test_multiple_signature_layers_same_document(make_pdf, sample_signature_png, tmp_path):
    src = make_pdf("doc3.pdf", 2)
    sig_template = SignatureTemplate(
        image_path=str(sample_signature_png), position_preset=PositionPreset.BOTTOM_RIGHT, page_rule_expression="last"
    )
    seal_template = SignatureTemplate(
        image_path=str(sample_signature_png), position_preset=PositionPreset.BOTTOM_LEFT, page_rule_expression="all"
    )
    out = tmp_path / "doc3_signed.pdf"
    outcome = apply_signatures_to_pdf(
        src, out, [SignatureApplication(template=sig_template), SignatureApplication(template=seal_template)]
    )
    assert outcome.signed_pages == [1, 2]
    with open_pdf(out) as doc:
        # Page 1 only gets the seal (1 image); page 2 gets both seal + signature (2 images).
        assert len(doc[0].get_images()) == 1
        assert len(doc[1].get_images()) == 2


def test_original_file_is_never_modified(make_pdf, sample_signature_png, tmp_path):
    src = make_pdf("original.pdf", 2)
    original_bytes = src.read_bytes()
    template = SignatureTemplate(image_path=str(sample_signature_png))
    out = tmp_path / "output.pdf"
    apply_signatures_to_pdf(src, out, [SignatureApplication(template=template)])
    assert src.read_bytes() == original_bytes
    assert out != src


def test_per_file_override_expression(make_pdf, sample_signature_png, tmp_path):
    src = make_pdf("override.pdf", 6)
    template = SignatureTemplate(image_path=str(sample_signature_png), page_rule_expression="last")
    out = tmp_path / "override_signed.pdf"
    # Global rule is "last" but this application overrides to page 1 only.
    application = SignatureApplication(template=template, page_rule_expression="1")
    outcome = apply_signatures_to_pdf(src, out, [application])
    assert outcome.signed_pages == [1]
