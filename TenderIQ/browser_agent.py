"""
browser_agent.py
Playwright Chromium automation for navigating tender portals, paginating listings,
extracting tender detail pages, supporting interactive human CAPTCHA/classification pause-resume,
and downloading PDF/ZIP documents safely.
"""

from __future__ import annotations

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import queue
import sys
import threading
from typing import Callable, Optional
from urllib.parse import unquote, urlparse
import uuid
import zipfile

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from tender_extractor import (
    DEFAULT_TIMEOUT_MS,
    MAX_LISTING_PAGES,
    MAX_TENDERS,
    NOT_AVAILABLE,
    TenderRecord,
    classify_page_type,
    deduplicate_tenders,
    detect_captcha_or_block,
    extract_interactive_controls,
    extract_listings_from_html,
    extract_tender_details_from_html,
    find_next_page_url,
    find_tender_search_link,
    sanitize_filename,
)

ProgressCallback = Optional[Callable[[str, str, float], None]]


@dataclass
class ScrapeResult:
    """Outcome of a TenderIQ browser scraping run or paused interactive step."""

    status: str  # "success", "captcha_paused", "captcha", "blocked", "interaction_required", "no_listings", "error"
    message: str
    source_url: str
    tenders: list[TenderRecord] = field(default_factory=list)
    total_documents_downloaded: int = 0
    warnings: list[str] = field(default_factory=list)
    session_id: Optional[str] = None
    interactive_controls: dict = field(default_factory=dict)
    captcha_image_bytes: Optional[bytes] = None


def validate_url(raw_url: str) -> tuple[bool, str]:
    """Validate and normalize a user-supplied website URL."""
    url = (raw_url or "").strip()
    if not url:
        return False, "Please enter a tender website URL."
    if " " in url:
        return False, "Invalid URL: URL must not contain spaces."

    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)

    if parsed.scheme.lower() not in ("http", "https"):
        return False, "Invalid URL: Only http:// and https:// URLs are supported."
    if not parsed.netloc or (
        "." not in parsed.netloc and "localhost" not in parsed.netloc and ":" not in parsed.netloc
    ):
        return False, "Invalid URL: Please enter a complete domain or localhost URL."

    return True, url


def is_permitted_url(target_url: str, root_url: str) -> bool:
    """
    Restrict navigation to the supplied website host (allowing www. equivalence
    and subdomains of the root host).
    """
    if not target_url or target_url.startswith(("javascript:", "mailto:", "tel:", "#")):
        return False
    t_parsed = urlparse(target_url)
    r_parsed = urlparse(root_url)
    if t_parsed.scheme.lower() not in ("http", "https"):
        return False

    t_host = (t_parsed.hostname or "").lower().lstrip("www.")
    r_host = (r_parsed.hostname or "").lower().lstrip("www.")
    if not t_host or not r_host:
        return False
    return t_host == r_host or t_host.endswith("." + r_host)


def extract_pdfs_from_zip(zip_path: Path, dest_dir: Path) -> tuple[list[Path], list[str]]:
    """
    Safely extract PDF files from a ZIP archive into `dest_dir`.
    Protects against Zip Slip path traversal and corrupted archives.
    """
    extracted: list[Path] = []
    errors: list[str] = []

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            pdf_members = [
                info
                for info in zf.infolist()
                if not info.is_dir() and info.filename.lower().endswith(".pdf")
            ]
            if not pdf_members:
                errors.append(f"ZIP archive '{zip_path.name}' contained no PDF files.")
                return extracted, errors

            dest_resolved = dest_dir.resolve()
            for info in pdf_members:
                member_name = Path(info.filename).name
                safe_name = sanitize_filename(Path(member_name).stem) + ".pdf"
                target_path = (dest_dir / safe_name).resolve()

                if dest_resolved not in target_path.parents and target_path.parent != dest_resolved:
                    errors.append(f"Skipped unsafe ZIP entry: {info.filename}")
                    continue

                counter = 1
                while target_path.exists():
                    target_path = (
                        dest_dir / f"{sanitize_filename(Path(member_name).stem)}_{counter}.pdf"
                    ).resolve()
                    counter += 1

                with zf.open(info, "r") as src, open(target_path, "wb") as dst:
                    dst.write(src.read())
                extracted.append(target_path)
    except zipfile.BadZipFile:
        errors.append(f"Corrupted or invalid ZIP archive: {zip_path.name}")
    except Exception as exc:
        errors.append(f"ZIP extraction failed for {zip_path.name}: {exc}")

    return extracted, errors


def _guess_filename_from_url_and_headers(
    url: str, content_disposition: str = "", content_type: str = "", index: int = 1
) -> str:
    """Derive a clean, meaningful Windows-safe filename for a downloaded document."""
    filename = ""
    if content_disposition:
        for part in content_disposition.split(";"):
            part = part.strip()
            if part.lower().startswith("filename*="):
                filename = unquote(part.split("''", 1)[-1]).strip('"\' ')
                break
            if part.lower().startswith("filename="):
                filename = part.split("=", 1)[1].strip('"\' ')
                break

    if not filename:
        path_name = unquote(Path(urlparse(url).path).name)
        if path_name and "." in path_name:
            filename = path_name

    if not filename:
        ext = ".zip" if "zip" in content_type.lower() else ".pdf"
        filename = f"tender_document_{index}{ext}"

    stem = sanitize_filename(Path(filename).stem, max_len=75)
    ext = Path(filename).suffix.lower()
    if ext not in (".pdf", ".zip"):
        ext = ".zip" if "zip" in content_type.lower() else ".pdf"
    return f"{stem}{ext}"


def _open_page_safely(page: Page, url: str) -> tuple[Optional[int], str, str, Optional[str]]:
    """Navigate Playwright page to URL and return (status_code, html, title, error_message)."""
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except PlaywrightTimeoutError:
            pass
        status = response.status if response else None
        html = page.content()
        title = page.title() or ""
        return status, html, title, None
    except PlaywrightTimeoutError:
        return None, "", "", f"Timed out waiting for page to load: {url}"
    except PlaywrightError as exc:
        msg = str(exc)
        if any(
            tok in msg
            for tok in (
                "ERR_NAME_NOT_RESOLVED",
                "ERR_INTERNET_DISCONNECTED",
                "ERR_CONNECTION_REFUSED",
                "ERR_CONNECTION_TIMED_OUT",
            )
        ):
            return None, "", "", f"Website unavailable or no internet connection ({url})."
        return None, "", "", f"Browser navigation error for {url}: {msg.splitlines()[0]}"


def _capture_captcha_image(page: Page) -> Optional[bytes]:
    """Capture the visible CAPTCHA image bytes from the live page if present."""
    for sel in ("#captchaImage", "img[id*='captcha' i]", "img[src*='captcha' i]", "img[alt*='captcha' i]"):
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                src = loc.get_attribute("src") or ""
                if src.startswith("data:image/") and ";base64," in src:
                    b64_part = src.split(";base64,", 1)[1].strip()
                    return base64.b64decode(b64_part)
                return loc.screenshot()
        except Exception:
            continue
    return None


def _save_downloaded_bytes(
    data: bytes,
    filename: str,
    tender_dir: Path,
    seen_hashes: set[str],
    ready_pdfs: list[Path],
    tender: TenderRecord,
) -> None:
    """Validate PDF/ZIP magic bytes, deduplicate by SHA-256, and extract PDFs from ZIPs."""
    is_pdf = data.startswith(b"%PDF-") or filename.lower().endswith(".pdf")
    is_zip = data.startswith(b"PK") or filename.lower().endswith(".zip")
    if not (is_pdf or is_zip):
        return

    digest = hashlib.sha256(data).hexdigest()
    if digest in seen_hashes:
        return
    seen_hashes.add(digest)

    if is_zip and not filename.lower().endswith(".zip"):
        filename = Path(filename).stem + ".zip"
    elif is_pdf and not filename.lower().endswith(".pdf"):
        filename = Path(filename).stem + ".pdf"

    dest_path = tender_dir / filename
    counter = 1
    while dest_path.exists():
        dest_path = tender_dir / f"{Path(filename).stem}_{counter}{Path(filename).suffix}"
        counter += 1

    dest_path.write_bytes(data)

    if is_zip:
        extracted_pdfs, zip_errs = extract_pdfs_from_zip(dest_path, tender_dir)
        tender.download_errors.extend(zip_errs)
        for p in extracted_pdfs:
            p_hash = hashlib.sha256(p.read_bytes()).hexdigest()
            if p_hash in seen_hashes:
                p.unlink(missing_ok=True)
            else:
                seen_hashes.add(p_hash)
                ready_pdfs.append(p)
    else:
        ready_pdfs.append(dest_path)


def _download_tender_documents(
    context: BrowserContext,
    page: Page,
    tender: TenderRecord,
    downloads_root: Path,
    tender_index: int,
    root_url: str,
) -> tuple[int, list[str]]:
    """
    Download PDF/ZIP documents for a single tender, deduplicating by SHA-256 hash.
    Uses context.request.get first (preserving session cookies) and falls back to
    Playwright download interception when needed.
    """
    warnings: list[str] = []
    if not tender.document_urls:
        tender.document_download_status = "No Document Links Found"
        return 0, warnings

    folder_label = (
        sanitize_filename(tender.tender_id, max_len=60)
        if tender.tender_id != NOT_AVAILABLE
        else f"Tender_{tender_index:02d}"
    )
    tender_dir = downloads_root / folder_label
    tender_dir.mkdir(parents=True, exist_ok=True)
    tender.document_folder = str(tender_dir)

    seen_hashes: set[str] = set()
    for existing_pdf in tender_dir.glob("*.pdf"):
        try:
            seen_hashes.add(hashlib.sha256(existing_pdf.read_bytes()).hexdigest())
        except OSError:
            pass

    ready_pdfs: list[Path] = []

    for idx, doc_url in enumerate(tender.document_urls, start=1):
        if not is_permitted_url(doc_url, root_url):
            tender.download_errors.append(f"Skipped external link: {doc_url}")
            continue

        try:
            resp = context.request.get(doc_url, timeout=DEFAULT_TIMEOUT_MS)
            if not resp.ok:
                tender.download_errors.append(f"HTTP {resp.status} for {doc_url}")
                continue

            data = resp.body()
            if not data:
                tender.download_errors.append(f"Empty response for {doc_url}")
                continue

            headers = {k.lower(): v for k, v in resp.headers.items()}
            ctype = headers.get("content-type", "")
            cdisp = headers.get("content-disposition", "")

            is_pdf = data.startswith(b"%PDF-") or "pdf" in ctype.lower() or doc_url.lower().endswith(".pdf")
            is_zip = data.startswith(b"PK") or "zip" in ctype.lower() or doc_url.lower().endswith(".zip")

            if not (is_pdf or is_zip):
                tender.download_errors.append(
                    f"Unsupported format ({ctype or 'unknown'}) at {doc_url}"
                )
                continue

            filename = _guess_filename_from_url_and_headers(doc_url, cdisp, ctype, idx)
            _save_downloaded_bytes(data, filename, tender_dir, seen_hashes, ready_pdfs, tender)

        except Exception as exc:
            tender.download_errors.append(f"Failed downloading {doc_url}: {exc}")

    all_pdfs = sorted(tender_dir.glob("*.pdf"))
    tender.downloaded_files = [str(p) for p in all_pdfs]

    if tender.downloaded_files and not tender.download_errors:
        tender.document_download_status = f"Downloaded ({len(tender.downloaded_files)} PDF)"
    elif tender.downloaded_files and tender.download_errors:
        tender.document_download_status = (
            f"Partial ({len(tender.downloaded_files)} PDF, {len(tender.download_errors)} failed)"
        )
    else:
        tender.document_download_status = "Download Failed"

    return len(ready_pdfs) if ready_pdfs else len(tender.downloaded_files), warnings


def _complete_scrape_from_current_page(
    context: BrowserContext,
    page: Page,
    norm_url: str,
    downloads_root: Path,
    progress_cb: ProgressCallback,
) -> ScrapeResult:
    """Run listing/detail extraction, pagination, and document downloads from the loaded page."""

    def _notify(stage: str, detail: str, pct: float) -> None:
        if progress_cb:
            progress_cb(stage, detail, pct)

    html = page.content()
    page_type = classify_page_type(html, page.url)

    # If homepage, attempt to locate tender search/listings section
    if page_type == "homepage":
        search_link = find_tender_search_link(html, page.url)
        if search_link and is_permitted_url(search_link, norm_url):
            _notify("Reading tender listings", f"Navigating to tender section: {search_link}", 0.25)
            status_code, html, title, err = _open_page_safely(page, search_link)
            if err:
                return ScrapeResult(status="error", message=err, source_url=norm_url)
            block = detect_captcha_or_block(html, status_code, title)
            if block:
                if block[0] == "captcha":
                    return ScrapeResult(
                        status="captcha_paused",
                        message="CAPTCHA detected. Please solve it in the browser window.",
                        source_url=norm_url,
                        interactive_controls=extract_interactive_controls(html),
                        captcha_image_bytes=_capture_captcha_image(page),
                    )
                return ScrapeResult(status=block[0], message=block[1], source_url=norm_url)
            page_type = classify_page_type(html, page.url)

    tenders: list[TenderRecord] = []
    warnings: list[str] = []

    if page_type == "detail":
        _notify("Extracting tender details", "Detected single tender detail page...", 0.40)
        tenders.append(extract_tender_details_from_html(html, page.url))

    elif page_type == "listing":
        current_url = page.url
        visited_pages: set[str] = set()
        for page_num in range(1, MAX_LISTING_PAGES + 1):
            if current_url in visited_pages:
                break
            visited_pages.add(current_url)

            _notify(
                "Reading tender listings",
                f"Reading listing page {page_num} of max {MAX_LISTING_PAGES}...",
                0.22 + (page_num * 0.03),
            )
            page_tenders = extract_listings_from_html(html, current_url)
            tenders.extend(page_tenders)
            tenders = deduplicate_tenders(tenders)

            if len(tenders) >= MAX_TENDERS:
                tenders = tenders[:MAX_TENDERS]
                break

            next_url = find_next_page_url(html, current_url)
            if not next_url or next_url in visited_pages or not is_permitted_url(next_url, norm_url):
                break

            status_code, html, title, err = _open_page_safely(page, next_url)
            if err:
                warnings.append(f"Stopped pagination at page {page_num + 1}: {err}")
                break
            block = detect_captcha_or_block(html, status_code, title)
            if block:
                warnings.append(f"Pagination paused at page {page_num + 1}: {block[1]}")
                break
            current_url = page.url

    else:
        fallback_listings = extract_listings_from_html(html, page.url)
        if fallback_listings:
            tenders = fallback_listings[:MAX_TENDERS]
        else:
            return ScrapeResult(
                status="interaction_required",
                message=(
                    "Reached the portal page, but could not automatically find tender listings "
                    "(a search selection or CAPTCHA may be required). Please select any options in the "
                    "browser window or paste a direct tender search results / detail URL."
                ),
                source_url=norm_url,
            )

    if not tenders:
        return ScrapeResult(
            status="no_listings",
            message="No tender listings were found on the supplied URL.",
            source_url=norm_url,
        )

    tenders = deduplicate_tenders(tenders)[:MAX_TENDERS]

    # Visit individual tender detail pages
    if page_type != "detail":
        total = len(tenders)
        for idx, tender in enumerate(tenders, start=1):
            pct = 0.40 + (0.20 * (idx / max(total, 1)))
            _notify(
                "Extracting tender details",
                f"Opening tender {idx} of {total}: {tender.tender_id}",
                pct,
            )
            if tender.detail_url == NOT_AVAILABLE:
                continue
            if not is_permitted_url(tender.detail_url, norm_url):
                warnings.append(f"Skipped external tender URL: {tender.detail_url}")
                continue
            if tender.detail_url.lower().endswith((".pdf", ".zip")):
                if tender.detail_url not in tender.document_urls:
                    tender.document_urls.append(tender.detail_url)
                continue

            d_status, d_html, d_title, d_err = _open_page_safely(page, tender.detail_url)
            if d_err:
                warnings.append(f"Tender {idx} detail page error: {d_err}")
                continue
            d_block = detect_captcha_or_block(d_html, d_status, d_title)
            if d_block:
                warnings.append(f"Tender {idx} blocked/CAPTCHA: {d_block[1]}")
                continue

            extract_tender_details_from_html(d_html, page.url, existing=tender)

    # Download documents for all identified tenders
    total_docs = 0
    total_t = len(tenders)
    for idx, tender in enumerate(tenders, start=1):
        pct = 0.60 + (0.15 * (idx / max(total_t, 1)))
        _notify(
            "Downloading tender documents",
            f"Downloading documents for tender {idx} of {total_t}...",
            pct,
        )
        count, dl_warns = _download_tender_documents(
            context=context,
            page=page,
            tender=tender,
            downloads_root=downloads_root,
            tender_index=idx,
            root_url=norm_url,
        )
        total_docs += count
        warnings.extend(dl_warns)

    return ScrapeResult(
        status="success",
        message="Tender extraction and document download completed.",
        source_url=norm_url,
        tenders=tenders,
        total_documents_downloaded=total_docs,
        warnings=warnings,
    )


class InteractiveBrowserSession:
    """
    Persistent Playwright Chromium session kept open on a dedicated thread so Streamlit
    can pause when a CAPTCHA or search classification form appears, keep the live browser
    window and cookies open across reruns, and continue scraping after human input.
    """

    def __init__(self, downloads_root: Path, headless: bool = False) -> None:
        self.session_id = uuid.uuid4().hex
        self.downloads_root = downloads_root
        self.headless = headless
        self.norm_url = ""
        self.progress_queue: queue.Queue[tuple[str, str, float]] = queue.Queue()
        self._cmd_queue: queue.Queue[tuple[str, dict]] = queue.Queue()
        self._res_queue: queue.Queue[ScrapeResult] = queue.Queue()
        self._closed = False
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def _emit_progress(self, stage: str, detail: str, pct: float) -> None:
        self.progress_queue.put((stage, detail, pct))

    def _worker_loop(self) -> None:
        if sys.platform.startswith("win"):
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass

        pw = None
        browser: Optional[Browser] = None
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=self.headless)
            context = browser.new_context(
                accept_downloads=True,
                viewport={"width": 1366, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            while True:
                cmd, payload = self._cmd_queue.get()
                if cmd == "close":
                    break

                if cmd == "open":
                    url = payload["url"]
                    ok, norm_url = validate_url(url)
                    if not ok:
                        self._res_queue.put(ScrapeResult(status="error", message=norm_url, source_url=url))
                        break

                    self.norm_url = norm_url
                    self.downloads_root.mkdir(parents=True, exist_ok=True)
                    self._emit_progress("Connecting to website", f"Opening {norm_url}...", 0.08)

                    status_code, html, title, err = _open_page_safely(page, norm_url)
                    if err:
                        self._res_queue.put(ScrapeResult(status="error", message=err, source_url=norm_url))
                        break

                    block = detect_captcha_or_block(html, status_code, title)
                    controls = extract_interactive_controls(html)

                    if block and block[0] == "blocked":
                        self._res_queue.put(ScrapeResult(status="blocked", message=block[1], source_url=norm_url))
                        break

                    if block and block[0] == "captcha":
                        self._emit_progress(
                            "Reading tender listings",
                            "CAPTCHA detected. Waiting for user to solve it...",
                            0.18,
                        )
                        self._res_queue.put(
                            ScrapeResult(
                                status="captcha_paused",
                                message="CAPTCHA detected. Please solve it in the browser window.",
                                source_url=norm_url,
                                session_id=self.session_id,
                                interactive_controls=controls,
                                captcha_image_bytes=_capture_captcha_image(page),
                            )
                        )
                        continue

                    self._emit_progress("Reading tender listings", "Analysing page structure...", 0.20)
                    result = _complete_scrape_from_current_page(
                        context=context,
                        page=page,
                        norm_url=norm_url,
                        downloads_root=self.downloads_root,
                        progress_cb=self._emit_progress,
                    )
                    if result.status == "captcha_paused":
                        result.session_id = self.session_id
                        self._res_queue.put(result)
                        continue

                    self._res_queue.put(result)
                    break

                if cmd == "continue":
                    selected_values: dict[str, str] = payload.get("selected_values") or {}
                    captcha_text: str = (payload.get("captcha_text") or "").strip()

                    try:
                        # Apply any classification/dropdown selection chosen in Streamlit
                        for sel, val in selected_values.items():
                            if val and val != "0":
                                try:
                                    page.locator(sel).first.select_option(val)
                                except Exception:
                                    pass

                        controls = extract_interactive_controls(page.content())
                        cap_input_sel = controls.get("captcha_input_selector")
                        submit_sel = controls.get("submit_selector")

                        if captcha_text and cap_input_sel:
                            page.locator(cap_input_sel).first.fill(captcha_text)
                            if submit_sel:
                                with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                                    page.locator(submit_sel).first.click()
                        else:
                            # If user typed CAPTCHA in the visible browser without clicking Submit yet
                            if cap_input_sel and submit_sel:
                                try:
                                    cur_val = page.locator(cap_input_sel).first.input_value().strip()
                                    if cur_val:
                                        with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                                            page.locator(submit_sel).first.click()
                                except Exception:
                                    pass

                        try:
                            page.wait_for_load_state("networkidle", timeout=5000)
                        except PlaywrightTimeoutError:
                            pass
                    except PlaywrightTimeoutError:
                        pass
                    except Exception as exc:
                        self._res_queue.put(
                            ScrapeResult(
                                status="captcha_paused",
                                message=f"Could not submit form automatically ({exc}). Please complete in browser and click Continue Scraping.",
                                source_url=self.norm_url,
                                session_id=self.session_id,
                                interactive_controls=extract_interactive_controls(page.content()),
                                captcha_image_bytes=_capture_captcha_image(page),
                            )
                        )
                        continue

                    html = page.content()
                    title = page.title() or ""
                    page_type = classify_page_type(html, page.url)
                    still_captcha = detect_captcha_or_block(html, None, title)

                    if still_captcha and still_captcha[0] == "captcha" and page_type not in ("listing", "detail"):
                        self._res_queue.put(
                            ScrapeResult(
                                status="captcha_paused",
                                message="CAPTCHA detected. Please solve it in the browser window.",
                                source_url=self.norm_url,
                                session_id=self.session_id,
                                interactive_controls=extract_interactive_controls(html),
                                captcha_image_bytes=_capture_captcha_image(page),
                            )
                        )
                        continue

                    self._emit_progress("Reading tender listings", "Continuing after verification...", 0.22)
                    result = _complete_scrape_from_current_page(
                        context=context,
                        page=page,
                        norm_url=self.norm_url,
                        downloads_root=self.downloads_root,
                        progress_cb=self._emit_progress,
                    )
                    result.session_id = None
                    self._res_queue.put(result)
                    break

        except PlaywrightError as exc:
            msg = str(exc)
            if "Executable doesn't exist" in msg:
                self._res_queue.put(
                    ScrapeResult(
                        status="error",
                        message=(
                            "Playwright Chromium browser is not installed. "
                            "Please run 'playwright install chromium' in CMD and restart TenderIQ."
                        ),
                        source_url=self.norm_url,
                    )
                )
            else:
                self._res_queue.put(
                    ScrapeResult(
                        status="error",
                        message=f"Browser automation failed: {msg.splitlines()[0]}",
                        source_url=self.norm_url,
                    )
                )
        except Exception as exc:
            self._res_queue.put(
                ScrapeResult(
                    status="error",
                    message=f"Unexpected scraping error: {exc}",
                    source_url=self.norm_url,
                )
            )
        finally:
            self._closed = True
            try:
                if context:
                    context.close()
            except Exception:
                pass
            try:
                if browser:
                    browser.close()
            except Exception:
                pass
            try:
                if pw:
                    pw.stop()
            except Exception:
                pass

    def open_url(self, url: str) -> ScrapeResult:
        """Open initial URL and return either completion or captcha_paused state."""
        self._cmd_queue.put(("open", {"url": url}))
        return self._res_queue.get()

    def continue_scraping(
        self, selected_values: Optional[dict[str, str]] = None, captcha_text: str = ""
    ) -> ScrapeResult:
        """Continue scraping in the existing open browser session after human action."""
        self._cmd_queue.put(
            (
                "continue",
                {"selected_values": selected_values or {}, "captcha_text": captcha_text},
            )
        )
        return self._res_queue.get()

    def close(self) -> None:
        """Close the browser session cleanly."""
        if not self._closed:
            self._cmd_queue.put(("close", {}))
            self._thread.join(timeout=5)
            self._closed = True


_ACTIVE_SESSIONS: dict[str, InteractiveBrowserSession] = {}
_SESSIONS_LOCK = threading.Lock()


def get_interactive_session(session_id: Optional[str]) -> Optional[InteractiveBrowserSession]:
    """Retrieve an open InteractiveBrowserSession by ID."""
    if not session_id:
        return None
    with _SESSIONS_LOCK:
        return _ACTIVE_SESSIONS.get(session_id)


def close_interactive_session(session_id: Optional[str]) -> None:
    """Close and remove an active InteractiveBrowserSession."""
    if not session_id:
        return
    with _SESSIONS_LOCK:
        sess = _ACTIVE_SESSIONS.pop(session_id, None)
    if sess:
        sess.close()


def create_interactive_session(downloads_root: Path, headless: bool = False) -> InteractiveBrowserSession:
    """Create and register a new persistent InteractiveBrowserSession."""
    sess = InteractiveBrowserSession(downloads_root=downloads_root, headless=headless)
    with _SESSIONS_LOCK:
        _ACTIVE_SESSIONS[sess.session_id] = sess
    return sess


def run_tender_scraper(
    url: str,
    downloads_root: Path,
    progress_cb: ProgressCallback = None,
    headless: bool = True,
) -> ScrapeResult:
    """
    One-shot synchronous scraping helper (pauses are mapped to 'captcha' and session closed).
    Used for headless automated runs/tests.
    """
    sess = InteractiveBrowserSession(downloads_root=downloads_root, headless=headless)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(sess.open_url, url)
        while not future.done():
            while not sess.progress_queue.empty():
                stage, detail, pct = sess.progress_queue.get_nowait()
                if progress_cb:
                    progress_cb(stage, detail, pct)
            threading.Event().wait(0.05)
        while not sess.progress_queue.empty():
            stage, detail, pct = sess.progress_queue.get_nowait()
            if progress_cb:
                progress_cb(stage, detail, pct)
        res = future.result()

    if res.status == "captcha_paused":
        sess.close()
        return ScrapeResult(status="captcha", message=res.message, source_url=res.source_url)
    sess.close()
    return res
