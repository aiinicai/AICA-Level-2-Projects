import os
import pymupdf
from app.processor import DocumentProcessor, DocumentItem
from app.tesseract_utils import get_tesseract_status

def test_document_processor():
    print("=" * 60)
    print("DocDeskew AI - Automated Verification Test Suite")
    print("=" * 60)

    # 1. Verify Tesseract Installation
    is_avail, exe_path, version_info = get_tesseract_status()
    print(f"[1/4] Tesseract OCR Status: Available={is_avail}, Version={version_info}")
    assert is_avail, f"Tesseract not available: {version_info}"

    # 2. Load Synthetic Test Files
    test_files = [
        os.path.join("sample_test_docs", "test_page_1_rot90_skew5.png"),
        os.path.join("sample_test_docs", "test_page_2_rot180_skew7.png"),
        os.path.join("sample_test_docs", "test_multipage_doc.pdf"),
    ]

    all_items = []
    print("\n[2/4] Loading Test Files...")
    for fpath in test_files:
        assert os.path.exists(fpath), f"File not found: {fpath}"
        items = DocumentProcessor.load_file(fpath)
        print(f"  - Loaded '{fpath}': {len(items)} page(s)")
        all_items.extend(items)

    total_loaded = len(all_items)
    print(f"Total Document Pages Loaded: {total_loaded}")
    assert total_loaded == 4, f"Expected 4 pages total, got {total_loaded}"

    # 3. Test Auto-Rotate & Deskew Engine on each page
    print("\n[3/4] Running Auto-Rotate & OpenCV Deskew Engine...")
    for idx, item in enumerate(all_items):
        print(f"\n--- Processing Page {idx + 1}/{total_loaded}: {item.display_name} ---")
        DocumentProcessor.process_item(item, do_auto_rotate=True, do_deskew=True)

        print(f"  Status: {item.status}")
        print(f"  Detected Tesseract OSD Rotation: {item.auto_rotate_angle}°")
        print(f"  Detected OpenCV Skew Angle:      {item.deskew_angle:+.2f}°")

        assert item.status == "Done", f"Processing failed for item {item.display_name}: {item.error_message}"
        assert item.processed_image is not None, "Processed image should not be None"

    # 4. Test AI Auto-Arrange by OCR Page Numbers
    print("\n[4/5] Running AI Auto-Arrange Page Sorting...")
    sorted_items, count_reordered = DocumentProcessor.auto_arrange_items(all_items)
    print(f"  AI Auto-Arrange completed: Reordered {count_reordered} page(s).")
    for i, it in enumerate(sorted_items):
        print(f"  Pos {i+1}: {it.display_name} (Detected Page Seq: {it.detected_page_seq})")

    # 5. Export Merged PDF and Verify Output
    print("\n[5/5] Exporting Merged PDF Document...")
    output_pdf = "test_merged_output.pdf"
    if os.path.exists(output_pdf):
        os.remove(output_pdf)

    res = DocumentProcessor.export_pdf(all_items, output_pdf)
    out_path = res["output_path"] if isinstance(res, dict) else res
    final_sz = res.get("final_size", 0) if isinstance(res, dict) else os.path.getsize(out_path)
    assert os.path.exists(out_path), "Merged output PDF was not created."

    # Inspect generated PDF with PyMuPDF
    doc = pymupdf.open(out_path)
    page_count = len(doc)
    print(f"[OK] Compressed Merged PDF generated at '{out_path}' ({final_sz / 1024:.1f} KB, {page_count} pages).")
    assert page_count == 4, f"Expected output PDF to have 4 pages, got {page_count}"
    doc.close()

    print("\n" + "=" * 60)
    print("ALL VERIFICATION TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 60)

if __name__ == "__main__":
    test_document_processor()
