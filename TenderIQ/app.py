"""
app.py
Simple single-screen Streamlit UI for TenderIQ – AI-Powered Tender Intelligence Agent.
Supports interactive human-in-the-loop pause/resume for CAPTCHAs and classification forms.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import os
from pathlib import Path
import queue
import shutil
import time

import streamlit as st

from browser_agent import (
    ScrapeResult,
    close_interactive_session,
    create_interactive_session,
    extract_pdfs_from_zip,
    get_interactive_session,
)
from document_analyser import AnalysisStats, analyse_tender_documents
from report_generator import EXCEL_FILENAME, PDF_FILENAME, generate_excel_report, generate_pdf_report
from tender_extractor import TenderRecord, sanitize_filename

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"

PROGRESS_STEPS = [
    "Connecting to website",
    "Reading tender listings",
    "Extracting tender details",
    "Downloading tender documents",
    "Analysing documents using AI",
    "Generating reports",
]

st.set_page_config(
    page_title="TenderIQ – AI Tender Intelligence Agent",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .tenderiq-title {
            font-size: 2.2rem;
            font-weight: 800;
            color: #1F3864;
            margin-bottom: 0.1rem;
            letter-spacing: 0.5px;
        }
        .tenderiq-subtitle {
            font-size: 1.0rem;
            font-weight: 600;
            color: #4B5563;
            margin-bottom: 1.5rem;
            letter-spacing: 0.8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def _render_steps(steps_box, current_stage: str, activity_text: str, progress_bar, pct: float) -> None:
    """Update the 6-step progress checklist, current activity text, and progress bar."""
    current_idx = PROGRESS_STEPS.index(current_stage) if current_stage in PROGRESS_STEPS else -1
    lines = []
    for idx, step in enumerate(PROGRESS_STEPS):
        if pct >= 1.0 or idx < current_idx:
            icon = "✅"
        elif idx == current_idx:
            icon = "⏳"
        else:
            icon = "⬜"
        lines.append(f"{icon} **{step}**")
    steps_box.markdown("\n\n".join(lines) + f"\n\n**Current Activity:** {activity_text}")
    progress_bar.progress(min(max(pct, 0.0), 1.0))


def _clear_paused_state() -> None:
    """Close any open browser session and clear paused UI state."""
    old_id = st.session_state.pop("paused_session_id", None)
    if old_id:
        close_interactive_session(old_id)
    st.session_state.pop("paused_controls", None)
    st.session_state.pop("paused_captcha_img", None)
    st.session_state.pop("paused_message", None)


def _save_run_results(
    tenders: list[TenderRecord],
    total_docs: int,
    stats: AnalysisStats,
    excel_path: Path,
    pdf_path: Path,
    warnings: list[str],
) -> None:
    """Persist completed run results in Streamlit session state."""
    st.session_state["run_completed"] = True
    st.session_state["total_tenders"] = len(tenders)
    st.session_state["total_docs"] = total_docs
    st.session_state["total_analysed"] = stats.tenders_analysed
    st.session_state["unanalysed_docs"] = stats.documents_unanalysed
    st.session_state["excel_path"] = str(excel_path)
    st.session_state["pdf_path"] = str(pdf_path)
    st.session_state["warnings"] = warnings


def _drain_and_wait(future, prog_queue: queue.Queue, steps_box, progress_bar) -> ScrapeResult:
    """Wait for a worker future while rendering queued progress updates on the main thread."""
    while not future.done():
        while not prog_queue.empty():
            stage, detail, pct = prog_queue.get_nowait()
            _render_steps(steps_box, stage, detail, progress_bar, pct)
        time.sleep(0.1)

    while not prog_queue.empty():
        stage, detail, pct = prog_queue.get_nowait()
        _render_steps(steps_box, stage, detail, progress_bar, pct)

    return future.result()


def _finalize_scrape_success(scrape_result: ScrapeResult, steps_box, progress_bar) -> None:
    """Run AI analysis and report generation after scraping succeeds."""
    _clear_paused_state()
    tenders = scrape_result.tenders

    def _on_progress(stage: str, detail: str, pct: float) -> None:
        _render_steps(steps_box, stage, detail, progress_bar, pct)

    stats = analyse_tender_documents(
        tenders=tenders,
        env_dir=BASE_DIR,
        progress_cb=_on_progress,
    )

    _render_steps(
        steps_box,
        "Generating reports",
        "Generating consolidated Excel and PDF reports...",
        progress_bar,
        0.94,
    )
    excel_path = generate_excel_report(tenders, OUTPUT_DIR)
    pdf_path = generate_pdf_report(
        tenders=tenders,
        source_url=scrape_result.source_url,
        total_documents_downloaded=scrape_result.total_documents_downloaded,
        analysis_stats=stats,
        output_dir=OUTPUT_DIR,
    )

    _render_steps(steps_box, "Generating reports", "Completed.", progress_bar, 1.0)
    all_warnings = scrape_result.warnings + stats.warnings
    _save_run_results(
        tenders=tenders,
        total_docs=scrape_result.total_documents_downloaded,
        stats=stats,
        excel_path=excel_path,
        pdf_path=pdf_path,
        warnings=all_warnings,
    )


def _handle_scrape_outcome(scrape_result: ScrapeResult, steps_box, progress_bar, status_box) -> None:
    """Route ScrapeResult to either paused CAPTCHA state, error message, or final reports."""
    if scrape_result.status == "captcha_paused":
        st.session_state["paused_session_id"] = scrape_result.session_id
        st.session_state["paused_controls"] = scrape_result.interactive_controls or {}
        st.session_state["paused_captcha_img"] = scrape_result.captcha_image_bytes
        st.session_state["paused_message"] = scrape_result.message
        _render_steps(
            steps_box,
            "Reading tender listings",
            "CAPTCHA detected. Waiting for human input...",
            progress_bar,
            0.18,
        )
        return

    _clear_paused_state()
    if scrape_result.status != "success":
        if scrape_result.status in ("captcha", "blocked", "interaction_required"):
            status_box.warning(scrape_result.message)
        else:
            status_box.error(scrape_result.message)
        return

    _finalize_scrape_success(scrape_result, steps_box, progress_bar)


def _process_manual_uploads(uploaded_files, steps_box, progress_bar) -> None:
    """Fallback pipeline when target portal blocks automation or user supplies local PDF/ZIPs."""
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manual_dir = DOWNLOADS_DIR / "Manual_Uploads"
    if manual_dir.exists():
        shutil.rmtree(manual_dir, ignore_errors=True)
    manual_dir.mkdir(parents=True, exist_ok=True)

    _render_steps(
        steps_box,
        "Downloading tender documents",
        "Saving uploaded tender documents...",
        progress_bar,
        0.55,
    )

    tenders: list[TenderRecord] = []
    seen_hashes: set[str] = set()
    total_docs = 0
    warnings: list[str] = []

    for idx, uf in enumerate(uploaded_files, start=1):
        raw_bytes = uf.getvalue()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)

        orig_name = uf.name
        stem = sanitize_filename(Path(orig_name).stem)
        ext = Path(orig_name).suffix.lower()

        tender_folder = manual_dir / f"Manual_{idx:02d}_{stem[:30]}"
        tender_folder.mkdir(parents=True, exist_ok=True)
        saved_path = tender_folder / f"{stem}{ext}"
        saved_path.write_bytes(raw_bytes)

        ready_pdfs: list[Path] = []
        errs: list[str] = []
        if ext == ".zip":
            ready_pdfs, errs = extract_pdfs_from_zip(saved_path, tender_folder)
            warnings.extend(errs)
        elif ext == ".pdf":
            ready_pdfs = [saved_path]
        else:
            errs.append(f"Unsupported file format: {orig_name}")
            warnings.extend(errs)

        total_docs += len(ready_pdfs)
        tenders.append(
            TenderRecord(
                tender_id=f"MANUAL-{idx:02d}",
                title=stem.replace("_", " "),
                detail_url="Manual Document Upload",
                document_download_status=(
                    f"Uploaded ({len(ready_pdfs)} PDF)" if ready_pdfs else "Upload Failed"
                ),
                document_folder=str(tender_folder),
                downloaded_files=[str(p) for p in ready_pdfs],
                download_errors=errs,
            )
        )

    def _ai_progress(stage: str, msg: str, pct: float) -> None:
        _render_steps(steps_box, stage, msg, progress_bar, pct)

    stats = analyse_tender_documents(tenders, env_dir=BASE_DIR, progress_cb=_ai_progress)
    warnings.extend(stats.warnings)

    _render_steps(steps_box, "Generating reports", "Building Excel and PDF reports...", progress_bar, 0.94)
    excel_path = generate_excel_report(tenders, OUTPUT_DIR)
    pdf_path = generate_pdf_report(tenders, "Manual Document Upload", total_docs, stats, OUTPUT_DIR)

    _render_steps(steps_box, "Generating reports", "All reports generated.", progress_bar, 1.0)
    _save_run_results(tenders, total_docs, stats, excel_path, pdf_path, warnings)


# --- MAIN SINGLE-SCREEN INTERFACE ---
st.markdown('<div class="tenderiq-title">TENDERIQ</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tenderiq-subtitle">AI-POWERED TENDER INTELLIGENCE AGENT</div>',
    unsafe_allow_html=True,
)

url_input = st.text_input(
    "Website URL:",
    placeholder="https://eprocure.gov.in/eprocure/app?page=FrontEndTendersByClassification&service=page",
)
scrape_clicked = st.button("SCRAPE", type="primary", use_container_width=True)

st.markdown("---")
steps_box = st.empty()
progress_bar = st.progress(0.0)
status_box = st.empty()

if not scrape_clicked and not st.session_state.get("run_completed") and not st.session_state.get("paused_session_id"):
    steps_box.markdown(
        "\n\n".join(f"⬜ **{step}**" for step in PROGRESS_STEPS)
        + "\n\n**Current Activity:** Waiting for URL..."
    )

if scrape_clicked:
    st.session_state["run_completed"] = False
    _clear_paused_state()
    status_box.empty()

    headless_mode = os.getenv("TENDERIQ_HEADLESS", "0") == "1"
    sess = create_interactive_session(downloads_root=DOWNLOADS_DIR, headless=headless_mode)

    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(sess.open_url, url_input)
        scrape_result = _drain_and_wait(fut, sess.progress_queue, steps_box, progress_bar)

    _handle_scrape_outcome(scrape_result, steps_box, progress_bar, status_box)
    if scrape_result.status != "captcha_paused":
        sess.close()

# --- PAUSED CAPTCHA / CLASSIFICATION INTERVENTION UI ---
paused_session_id = st.session_state.get("paused_session_id")
if paused_session_id:
    sess = get_interactive_session(paused_session_id)
    if sess is None:
        _clear_paused_state()
        status_box.warning("Browser session expired. Please click SCRAPE to start again.")
    else:
        status_box.warning(
            st.session_state.get("paused_message")
            or "CAPTCHA detected. Please solve it in the browser window."
        )

        controls = st.session_state.get("paused_controls") or {}
        select_defs = controls.get("selects") or []
        selected_values: dict[str, str] = {}

        for sel_info in select_defs:
            opts = sel_info.get("options") or []
            if not opts:
                continue
            labels = [o["label"] for o in opts]
            values = [o["value"] for o in opts]
            chosen_label = st.selectbox(
                sel_info.get("label") or "Select Classification",
                options=labels,
                key=f"ctrl_{paused_session_id}_{sel_info['selector']}",
            )
            chosen_idx = labels.index(chosen_label)
            selected_values[sel_info["selector"]] = values[chosen_idx]

        captcha_img = st.session_state.get("paused_captcha_img")
        if captcha_img:
            st.image(captcha_img, caption="CAPTCHA from open browser session")

        captcha_text = ""
        if controls.get("captcha_input_selector"):
            captcha_text = st.text_input(
                "Enter CAPTCHA (or solve directly in the open browser window):",
                key=f"cap_{paused_session_id}",
            )

        btn_c1, btn_c2 = st.columns([3, 1])
        with btn_c1:
            continue_clicked = st.button("Continue Scraping", type="primary", use_container_width=True)
        with btn_c2:
            cancel_clicked = st.button("Cancel", use_container_width=True)

        if cancel_clicked:
            _clear_paused_state()
            status_box.info("Scraping session cancelled and browser closed.")
            st.rerun()

        if continue_clicked:
            with ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(sess.continue_scraping, selected_values, captcha_text)
                cont_result = _drain_and_wait(fut, sess.progress_queue, steps_box, progress_bar)

            if cont_result.status == "captcha_paused":
                st.session_state["paused_controls"] = cont_result.interactive_controls or {}
                st.session_state["paused_captcha_img"] = cont_result.captcha_image_bytes
                st.session_state["paused_message"] = cont_result.message
                st.rerun()
            else:
                _handle_scrape_outcome(cont_result, steps_box, progress_bar, status_box)
                sess.close()
                st.rerun()

# Fallback for portals that block automation or require login
with st.expander("Manual Document Upload Fallback (if website blocks automation or requires login)"):
    uploaded_docs = st.file_uploader(
        "Upload Tender PDF or ZIP files",
        type=["pdf", "zip"],
        accept_multiple_files=True,
    )
    if st.button("ANALYSE UPLOADED DOCUMENTS", use_container_width=True):
        if not uploaded_docs:
            st.warning("Please upload at least one PDF or ZIP file.")
        else:
            _process_manual_uploads(uploaded_docs, steps_box, progress_bar)

if st.session_state.get("run_completed"):
    st.markdown("---")
    st.subheader("SCRAPING COMPLETED")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total tenders identified", st.session_state["total_tenders"])
        st.metric("Total tenders analysed", st.session_state["total_analysed"])
    with col2:
        st.metric("Total documents downloaded", st.session_state["total_docs"])
        st.metric(
            "Documents that could not be analysed",
            st.session_state["unanalysed_docs"],
        )

    warnings_list = st.session_state.get("warnings") or []
    if warnings_list:
        with st.expander("Notices / Skipped Items"):
            for w in warnings_list[:20]:
                st.write(f"- {w}")

    excel_file = Path(st.session_state["excel_path"])
    pdf_file = Path(st.session_state["pdf_path"])

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if excel_file.exists():
            st.download_button(
                label="DOWNLOAD EXCEL REPORT",
                data=excel_file.read_bytes(),
                file_name=EXCEL_FILENAME,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with btn_col2:
        if pdf_file.exists():
            st.download_button(
                label="DOWNLOAD PDF SUMMARY",
                data=pdf_file.read_bytes(),
                file_name=PDF_FILENAME,
                mime="application/pdf",
                use_container_width=True,
            )
