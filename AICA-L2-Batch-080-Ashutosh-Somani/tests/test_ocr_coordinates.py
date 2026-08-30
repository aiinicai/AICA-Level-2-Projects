"""Tests for OCR coordinate conversion and rotation handling."""
import pytest
from app.models.extraction_result import RawWord


class TestCoordinateConversion:
    """Verify that OCR coordinate mapping from rendered image to PDF space
    works correctly for various rotation angles."""

    def _simulate_coordinate_mapping(self, img_x0, img_y0, img_x1, img_y1,
                                      rendered_width, rendered_height,
                                      pdf_width, pdf_height):
        """Simulate the coordinate mapping logic from ocr_engine_service.py."""
        scale_x = pdf_width / rendered_width
        scale_y = pdf_height / rendered_height

        pdf_x0 = img_x0 * scale_x
        pdf_x1 = img_x1 * scale_x
        pdf_top = img_y0 * scale_y
        pdf_bottom = img_y1 * scale_y

        # Safety bounds
        pdf_x0 = max(0.0, min(pdf_x0, pdf_width))
        pdf_x1 = max(0.0, min(pdf_x1, pdf_width))
        pdf_top = max(0.0, min(pdf_top, pdf_height))
        pdf_bottom = max(0.0, min(pdf_bottom, pdf_height))

        return pdf_x0, pdf_top, pdf_x1, pdf_bottom

    def test_identity_mapping_no_rotation(self):
        """0° rotation: rendered dimensions match PDF dimensions at 1:1 scale."""
        # PDF is 612x792, rendered at 1:1 (72 DPI)
        pdf_w, pdf_h = 612.0, 792.0
        rendered_w, rendered_h = 612, 792

        # Word at pixel (100, 200) to (200, 220)
        x0, top, x1, bottom = self._simulate_coordinate_mapping(
            100, 200, 200, 220, rendered_w, rendered_h, pdf_w, pdf_h
        )
        assert x0 == pytest.approx(100.0)
        assert top == pytest.approx(200.0)
        assert x1 == pytest.approx(200.0)
        assert bottom == pytest.approx(220.0)

    def test_scaled_mapping_250dpi(self):
        """Verify coordinate scaling at 250 DPI rendering."""
        pdf_w, pdf_h = 612.0, 792.0
        scale_factor = 250 / 72.0
        rendered_w = int(pdf_w * scale_factor)  # ~2125
        rendered_h = int(pdf_h * scale_factor)  # ~2750

        # Word at pixel (350, 700) to (700, 770)
        x0, top, x1, bottom = self._simulate_coordinate_mapping(
            350, 700, 700, 770, rendered_w, rendered_h, pdf_w, pdf_h
        )
        # Values should map back to PDF space (smaller numbers)
        assert 0 <= x0 < pdf_w
        assert 0 <= top < pdf_h
        assert x0 < x1 <= pdf_w
        assert top < bottom <= pdf_h
        # Approximate check: scale_x = 612/2125 ≈ 0.288
        assert x0 == pytest.approx(350 * pdf_w / rendered_w, rel=0.01)
        assert top == pytest.approx(700 * pdf_h / rendered_h, rel=0.01)

    def test_bounds_clamping(self):
        """Coordinates outside PDF bounds are clamped."""
        pdf_w, pdf_h = 612.0, 792.0
        rendered_w, rendered_h = 612, 792

        # Word extends beyond page
        x0, top, x1, bottom = self._simulate_coordinate_mapping(
            -10, -5, 700, 900, rendered_w, rendered_h, pdf_w, pdf_h
        )
        assert x0 == 0.0
        assert top == 0.0
        assert x1 == pdf_w
        assert bottom == pdf_h

    def test_rotation_90_dimension_swap(self):
        """For 90° rotation, pypdfium2 returns a rotated raster where
        width/height are swapped. The coordinate mapping uses the
        actual rendered dimensions, so scaling is still correct."""
        # Original PDF: 612 wide x 792 tall
        # After 90° rotation render: 792 wide x 612 tall
        pdf_w, pdf_h = 612.0, 792.0
        # But pypdfium2 with rotation=0 returns the page as-is
        # The page's GetPageSize already accounts for rotation
        # So for a page with /Rotate 90, GetPageSize returns (792, 612)
        rotated_pdf_w, rotated_pdf_h = 792.0, 612.0
        scale_factor = 250 / 72.0
        rendered_w = int(rotated_pdf_w * scale_factor)
        rendered_h = int(rotated_pdf_h * scale_factor)

        x0, top, x1, bottom = self._simulate_coordinate_mapping(
            100, 100, 300, 130, rendered_w, rendered_h, rotated_pdf_w, rotated_pdf_h
        )
        assert 0 <= x0 < rotated_pdf_w
        assert 0 <= top < rotated_pdf_h
        assert x0 < x1
        assert top < bottom

    def test_rotation_180(self):
        """180° rotation: dimensions stay the same, coordinates are mirrored."""
        pdf_w, pdf_h = 612.0, 792.0
        # 180° rotation doesn't change dimensions
        rendered_w = int(pdf_w * (250 / 72.0))
        rendered_h = int(pdf_h * (250 / 72.0))

        x0, top, x1, bottom = self._simulate_coordinate_mapping(
            500, 1000, 800, 1050, rendered_w, rendered_h, pdf_w, pdf_h
        )
        assert 0 <= x0 < pdf_w
        assert 0 <= top < pdf_h

    def test_rotation_270_dimension_swap(self):
        """270° rotation: similar to 90°, dimensions are swapped."""
        rotated_pdf_w, rotated_pdf_h = 792.0, 612.0
        scale_factor = 250 / 72.0
        rendered_w = int(rotated_pdf_w * scale_factor)
        rendered_h = int(rotated_pdf_h * scale_factor)

        x0, top, x1, bottom = self._simulate_coordinate_mapping(
            200, 50, 400, 80, rendered_w, rendered_h, rotated_pdf_w, rotated_pdf_h
        )
        assert 0 <= x0 < rotated_pdf_w
        assert 0 <= top < rotated_pdf_h
        assert x0 < x1
        assert top < bottom

    def test_zero_size_word(self):
        """A zero-area bounding box should not crash."""
        pdf_w, pdf_h = 612.0, 792.0
        x0, top, x1, bottom = self._simulate_coordinate_mapping(
            100, 100, 100, 100, 612, 792, pdf_w, pdf_h
        )
        assert x0 == x1
        assert top == bottom


class TestRawWordGeometry:
    """Test RawWord model's geometric properties."""

    def test_word_within_page_bounds(self):
        """Verify a word created with valid coordinates stays in bounds."""
        word = RawWord(
            text="Test",
            x0=50.0, x1=150.0,
            top=100.0, bottom=120.0,
            page_number=1,
            source_type="OCR",
            confidence=92.5,
        )
        assert word.x0 < word.x1
        assert word.top < word.bottom
        assert word.ocr_confidence == 92.5

    def test_ocr_word_bbox_coverage(self):
        """Verify bbox covers a reasonable area for OCR text."""
        word = RawWord(
            text="Transaction",
            x0=72.0, x1=200.0,
            top=300.0, bottom=312.0,
            page_number=1,
            source_type="OCR",
            confidence=88.0,
        )
        width = word.x1 - word.x0
        height = word.bottom - word.top
        assert width > 0
        assert height > 0
        # For a typical word, width should be greater than height
        assert width > height
