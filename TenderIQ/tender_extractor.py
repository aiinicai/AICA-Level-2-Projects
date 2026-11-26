"""
tender_extractor.py
Resilient HTML parsing, page classification, field extraction, and deduplication
for TenderIQ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

# Fixed configuration limits (kept in code, not exposed in UI)
MAX_TENDERS = 50
MAX_LISTING_PAGES = 5
DEFAULT_TIMEOUT_MS = 30000
NOT_AVAILABLE = "Not Available"


@dataclass
class TenderRecord:
    """Normalized data structure representing one tender and its extracted metadata."""

    tender_id: str = NOT_AVAILABLE
    title: str = NOT_AVAILABLE
    organisation: str = NOT_AVAILABLE
    department: str = NOT_AVAILABLE
    location: str = NOT_AVAILABLE
    published_date: str = NOT_AVAILABLE
    closing_date: str = NOT_AVAILABLE
    estimated_value: str = NOT_AVAILABLE
    emd_amount: str = NOT_AVAILABLE
    tender_fee: str = NOT_AVAILABLE
    detail_url: str = NOT_AVAILABLE
    document_urls: list[str] = field(default_factory=list)
    document_download_status: str = "Not Downloaded"
    document_folder: str = NOT_AVAILABLE
    downloaded_files: list[str] = field(default_factory=list)
    download_errors: list[str] = field(default_factory=list)
    ai_summary: dict = field(default_factory=dict)

    @property
    def document_urls_display(self) -> str:
        """Return a readable string of document download URLs or 'Not Available'."""
        if not self.document_urls:
            return NOT_AVAILABLE
        return "\n".join(self.document_urls)


# Label synonyms mapped to TenderRecord attribute names
FIELD_LABEL_MAP: dict[str, tuple[str, ...]] = {
    "tender_id": (
        "tender id",
        "tender reference",
        "tender ref",
        "reference no",
        "reference number",
        "ref no",
        "nit no",
        "nit number",
        "bid number",
        "bid no",
        "solicitation number",
        "notice number",
    ),
    "title": (
        "tender title",
        "title",
        "work description",
        "name of work",
        "description of work",
        "subject",
        "project name",
        "brief description",
    ),
    "organisation": (
        "organisation",
        "organization",
        "organisation name",
        "organization name",
        "organisation chain",
        "procuring entity",
        "issuing authority",
        "authority",
        "buyer",
        "company name",
        "ministry",
    ),
    "department": (
        "department",
        "division",
        "wing",
        "sub-department",
        "office",
        "branch",
    ),
    "location": (
        "location",
        "place",
        "city",
        "state",
        "region",
        "district",
        "work location",
        "delivery location",
        "site",
    ),
    "published_date": (
        "published date",
        "publish date",
        "e-published date",
        "publication date",
        "issue date",
        "release date",
        "date of issue",
        "nit date",
        "posted date",
        "start date",
    ),
    "closing_date": (
        "closing date",
        "last date",
        "submission deadline",
        "bid submission end date",
        "due date",
        "end date",
        "closing time",
        "bid closing date",
        "deadline",
    ),
    "estimated_value": (
        "estimated value",
        "estimated tender value",
        "tender value",
        "tender value in",
        "estimated cost",
        "approx value",
        "contract value",
        "budget",
        "project cost",
    ),
    "emd_amount": (
        "emd",
        "emd amount",
        "earnest money",
        "earnest money deposit",
        "bid security",
    ),
    "tender_fee": (
        "tender fee",
        "document fee",
        "bid fee",
        "cost of tender",
        "tender document fee",
        "processing fee",
    ),
}

CAPTCHA_PATTERNS = (
    r"g-recaptcha",
    r"h-captcha",
    r"cf-turnstile",
    r"verify you are human",
    r"are you a robot",
    r"enter the captcha",
    r"type the characters",
    r"captcha verification",
    r"security check required",
)

BLOCK_PATTERNS = (
    r"access denied",
    r"request blocked",
    r"automated access",
    r"bot protection",
    r"too many requests",
    r"cloudflare",
    r"ddos protection",
    r"error 403",
)

LOGIN_PATTERNS = (
    r"login to view tender",
    r"sign in to download",
    r"subscription required",
    r"paywall",
)

TENDER_LINK_KEYWORDS = (
    "tender",
    "tenders",
    "e-procurement",
    "eprocurement",
    "procurement",
    "opportunities",
    "active bids",
    "current tenders",
    "open tenders",
    "nit",
    "rfp",
    "rfq",
)

DOCUMENT_KEYWORDS = (
    "download",
    "nit",
    "boq",
    "rfp",
    "rfq",
    "bid document",
    "tender document",
    "specification",
    "corrigendum",
    "annexure",
    "attachment",
    "pdf",
    "zip",
)


def clean_text(value: Optional[str]) -> str:
    """Collapse excessive whitespace and strip control characters."""
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned


def sanitize_filename(name: str, max_len: int = 90) -> str:
    """Make any string safe as a Windows/POSIX file or directory name."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", clean_text(name))
    cleaned = re.sub(r"_+", "_", cleaned).strip(" ._")
    if not cleaned:
        return "document"
    return cleaned[:max_len].rstrip(" ._") or "document"


def is_valid_value(val: Optional[str]) -> bool:
    """Return True if extracted text represents meaningful non-empty content."""
    if not val:
        return False
    low = clean_text(val).lower()
    return bool(low) and low not in {"-", "--", "n/a", "na", "none", "null", "not available"}


def detect_captcha_or_block(
    html: str, status_code: Optional[int] = None, page_title: str = ""
) -> Optional[tuple[str, str]]:
    """
    Inspect HTTP status and HTML for CAPTCHA, bot blocking, or login walls.
    Returns (kind, user_message) or None if accessible.
    """
    if status_code in (403, 429):
        return (
            "blocked",
            f"Website returned HTTP {status_code} and appears to block automated access.",
        )

    combined = f"{page_title}\n{html[:35000]}".lower()

    for pattern in CAPTCHA_PATTERNS:
        if re.search(pattern, combined):
            return (
                "captcha",
                "A CAPTCHA verification challenge was detected on the page. "
                "Human intervention is required before continuing.",
            )

    # Specific check for <input name="*captcha*"> or <img src="*captcha*">
    soup = BeautifulSoup(html[:40000], "html.parser")
    for el in soup.find_all(["input", "img", "iframe"]):
        attrs = " ".join(
            str(el.get(k, "")) for k in ("id", "name", "class", "src", "alt", "title")
        ).lower()
        if any(tok in attrs for tok in ("captcha", "recaptcha", "hcaptcha", "turnstile")):
            return (
                "captcha",
                "A CAPTCHA element was detected on the page. "
                "Please resolve it manually or provide accessible documents.",
            )

    # Check explicit block page (short body or explicit block heading)
    text_len = len(clean_text(soup.get_text(" ")))
    if text_len < 1500:
        for pattern in BLOCK_PATTERNS:
            if re.search(pattern, combined):
                return (
                    "blocked",
                    "The website blocked automated browser access (anti-bot / access denied page).",
                )

    for pattern in LOGIN_PATTERNS:
        if re.search(pattern, combined):
            return (
                "blocked",
                "The page requires login or paid access, which TenderIQ does not bypass.",
            )

    return None


def _match_field_name(label: str) -> Optional[str]:
    """Map a normalized HTML label to a TenderRecord attribute name."""
    norm = clean_text(label).lower().rstrip(":.- ")
    if not norm or len(norm) > 60:
        return None
    # Exact match first, then substring match for longer synonyms
    for field_name, synonyms in FIELD_LABEL_MAP.items():
        if norm in synonyms:
            return field_name
    for field_name, synonyms in FIELD_LABEL_MAP.items():
        for syn in synonyms:
            if len(syn) >= 5 and syn in norm:
                return field_name
    return None


def _is_document_url(url: str, link_text: str = "") -> bool:
    """Heuristically identify links pointing to tender documents (PDF/ZIP/attachments)."""
    if not url or url.startswith(("javascript:", "mailto:", "tel:", "#")):
        return False
    parsed = urlparse(url.lower())
    path = parsed.path
    query = parsed.query
    low_txt = link_text.lower()
    if (
        path.endswith((".pdf", ".zip"))
        or ".pdf" in query
        or ".zip" in query
        or ".pdf" in low_txt
        or ".zip" in low_txt
    ):
        return True
    combined = f"{path} {query} {low_txt}"
    if any(kw in combined for kw in ("download", "attachment", "nit_doc", "tender_doc", "boq")):
        # Avoid false positives like "download chrome" or page navigation
        if any(bad in combined for bad in ("adobe", "chrome", "firefox", "manual", "help", "faq")):
            return False
        return True
    return False


def _direct_table_rows(table: Tag) -> list[Tag]:
    """Return direct row children of `table` (including thead/tbody/tfoot) without nested tables."""
    rows: list[Tag] = []
    for child in table.children:
        if not isinstance(child, Tag):
            continue
        if child.name == "tr":
            rows.append(child)
        elif child.name in ("thead", "tbody", "tfoot"):
            rows.extend(r for r in child.children if isinstance(r, Tag) and r.name == "tr")
    return rows


def _direct_row_cells(row: Tag) -> list[Tag]:
    """Return direct <th>/<td> cells of `row`."""
    return [c for c in row.children if isinstance(c, Tag) and c.name in ("th", "td")]


def extract_interactive_controls(html: str) -> dict:
    """
    Detect interactive search/classification dropdowns, CAPTCHA text input, and submit button
    on pages such as eProcure FrontEndTendersByClassification.
    """
    soup = BeautifulSoup(html, "html.parser")
    selects: list[dict] = []

    for sel in soup.find_all("select"):
        sel_id = sel.get("id") or ""
        sel_name = sel.get("name") or ""
        if not sel_id and not sel_name:
            continue

        options = [
            {"value": str(opt.get("value", "")), "label": clean_text(opt.get_text(" "))}
            for opt in sel.find_all("option")
            if clean_text(opt.get_text(" "))
        ]
        if len(options) < 2:
            continue

        # Determine friendly label
        label = ""
        if sel_id:
            lbl_tag = soup.find("label", attrs={"for": sel_id})
            if lbl_tag:
                label = clean_text(lbl_tag.get_text(" "))
        if not label:
            parent_tr = sel.find_parent("tr")
            if parent_tr:
                cells = _direct_row_cells(parent_tr)
                if len(cells) >= 2:
                    label = clean_text(cells[0].get_text(" ")).rstrip(":* ")
        if not label:
            if "contract" in (sel_id + sel_name).lower() or "classif" in (sel_id + sel_name).lower():
                label = "Select Classification"
            else:
                label = sel_name or sel_id

        if "classification" in label.lower() or "formofcontract" in (sel_id + sel_name).lower():
            label = "Select Classification"

        selector = f"#{sel_id}" if sel_id else f'select[name="{sel_name}"]'
        selects.append({"selector": selector, "label": label, "options": options})

    captcha_input_selector = None
    for inp in soup.find_all("input"):
        itype = (inp.get("type") or "text").lower()
        if itype in ("hidden", "submit", "button", "reset", "image"):
            continue
        attrs = " ".join(str(inp.get(k, "")) for k in ("id", "name", "placeholder", "class")).lower()
        if "captcha" in attrs:
            if inp.get("id"):
                captcha_input_selector = f'#{inp["id"]}'
            elif inp.get("name"):
                captcha_input_selector = f'input[name="{inp["name"]}"]'
            break

    submit_selector = None
    for btn in soup.find_all(["input", "button"]):
        btype = (btn.get("type") or "").lower()
        bval = clean_text(btn.get("value") or btn.get_text(" ")).lower()
        if btype == "submit" or any(tok in bval for tok in ("submit", "search", "proceed", "go")):
            if btn.get("id"):
                submit_selector = f'#{btn["id"]}'
            elif btn.get("name"):
                submit_selector = f'{btn.name}[name="{btn["name"]}"]'
            else:
                submit_selector = f'{btn.name}[type="submit"]'
            break

    return {
        "selects": selects,
        "captcha_input_selector": captcha_input_selector,
        "submit_selector": submit_selector,
    }


def _extract_kv_pairs(soup: BeautifulSoup) -> dict[str, str]:
    """Extract label-value pairs from tables, definition lists, and label blocks."""
    pairs: dict[str, str] = {}

    def _store(raw_label: str, raw_value: str) -> None:
        field_name = _match_field_name(raw_label)
        val = clean_text(raw_value)
        if field_name and is_valid_value(val) and field_name not in pairs:
            pairs[field_name] = val

    # 1. Table rows (2-column or multi-column label/value pairs)
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            cells = tr.find_all(["th", "td"])
        if len(cells) == 2:
            _store(cells[0].get_text(" "), cells[1].get_text(" "))
        elif len(cells) == 4:
            _store(cells[0].get_text(" "), cells[1].get_text(" "))
            _store(cells[2].get_text(" "), cells[3].get_text(" "))

    # 2. Definition lists <dt>/<dd>
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd:
            _store(dt.get_text(" "), dd.get_text(" "))

    # 3. Elements with explicit label/value children or "Label: Value" text
    for container in soup.find_all(["div", "p", "li", "span"]):
        # Skip huge wrapper containers
        if len(container.find_all(True)) > 6:
            continue
        txt = clean_text(container.get_text(" "))
        if ":" in txt and len(txt) < 300:
            left, right = txt.split(":", 1)
            _store(left, right)

    return pairs


def _is_listing_table(table: Tag) -> bool:
    """
    Return True if `table` looks like a multi-tender listing table rather than
    a vertical 2-column key-value detail table or an outer layout table.
    """
    rows = _direct_table_rows(table)
    if len(rows) < 2:
        return False
    first_cells = _direct_row_cells(rows[0])
    if len(first_cells) < 2:
        return False

    # A vertical KV table typically has <th>Label</th><td>Value</td> in row 0 (and 2 or 4 cells)
    first_row_tds = [c for c in first_cells if c.name == "td"]
    first_row_ths = [c for c in first_cells if c.name == "th"]
    if first_row_ths and first_row_tds:
        return False
    if len(first_cells) == 2 and not first_row_ths:
        # Check if col 0 looks like KV labels across rows (e.g. Tender ID, Organisation, Closing Date)
        kv_hits = sum(
            1
            for r in rows[:6]
            if _match_field_name(
                (_direct_row_cells(r)[0].get_text(" ") if _direct_row_cells(r) else "")
            )
        )
        if kv_hits >= 2:
            return False

    header_text = clean_text(rows[0].get_text(" ")).lower()
    if len(header_text) > 350:
        return False
    return any(
        k in header_text
        for k in ("tender", "title", "closing", "reference", "organisation", "bid", "work", "corrigendum")
    )


def classify_page_type(html: str, url: str = "") -> str:
    """
    Classify the page as 'detail', 'listing', or 'homepage'.
    """
    soup = BeautifulSoup(html, "html.parser")
    kv_pairs = _extract_kv_pairs(soup)

    # Check tables that look like multi-row horizontal tender listings
    listing_row_count = 0
    for table in soup.find_all("table"):
        if _is_listing_table(table):
            rows = _direct_table_rows(table)
            if len(rows) >= 3:
                listing_row_count += len(rows) - 1

    # Check repeating card/list items with tender detail links
    card_count = len(
        soup.select(
            ".tender-item, .tender-card, .tender-row, .bid-item, "
            "[data-tender-id], article.tender, li.tender"
        )
    )

    doc_links = [
        a for a in soup.find_all("a", href=True) if _is_document_url(a["href"], a.get_text(" "))
    ]

    # Detail page typically has several extracted metadata fields and is not a multi-row table
    if len(kv_pairs) >= 4 and listing_row_count < 2 and card_count < 2:
        return "detail"
    if listing_row_count >= 2 or card_count >= 2:
        return "listing"
    if len(kv_pairs) >= 3 and doc_links:
        return "detail"

    # URL hints as secondary check
    low_url = url.lower()
    if any(tok in low_url for tok in ("tender-detail", "viewtender", "tender_detail", "/detail")):
        if len(kv_pairs) >= 2 or doc_links:
            return "detail"

    # Check generic anchor links that point to tender pages
    tender_anchors = 0
    for a in soup.find_all("a", href=True):
        txt = clean_text(a.get_text(" ")).lower()
        href = a["href"].lower()
        if len(txt) > 12 and any(k in href or k in txt for k in ("tender", "nit", "rfp", "bid")):
            tender_anchors += 1
    if tender_anchors >= 4 and len(kv_pairs) < 3:
        # Distinguish navigation menu vs tender listing: listings usually have longer titles or dates
        date_hits = len(re.findall(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\w{3,9}[-/]20\d{2}\b", soup.get_text(" ")))
        if date_hits >= 2:
            return "listing"

    return "homepage"


def find_tender_search_link(html: str, base_url: str) -> Optional[str]:
    """
    On a portal homepage, find the most likely internal link leading to tender listings/search.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc.lower().lstrip("www.")
    candidates: list[tuple[int, str]] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        abs_url = urljoin(base_url, href)
        target_host = urlparse(abs_url).netloc.lower().lstrip("www.")
        if target_host and base_host and not (
            target_host == base_host or target_host.endswith("." + base_host)
        ):
            continue
        if abs_url.rstrip("/") == base_url.rstrip("/"):
            continue

        text = clean_text(a.get_text(" ")).lower()
        combined = f"{text} {href.lower()}"
        score = 0
        if "active tender" in combined or "current tender" in combined or "open tender" in combined:
            score += 10
        if "tender search" in combined or "search tender" in combined or "tenders" in combined:
            score += 7
        if any(k in combined for k in TENDER_LINK_KEYWORDS):
            score += 4
        if _is_document_url(abs_url, text):
            score -= 5
        if score > 0:
            candidates.append((score, abs_url))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def extract_listings_from_html(html: str, base_url: str) -> list[TenderRecord]:
    """
    Extract tender listing entries from tables, cards, or tender link lists.
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[TenderRecord] = []

    # Strategy 1: Structured HTML tables
    for table in soup.find_all("table"):
        if not _is_listing_table(table):
            continue
        rows = _direct_table_rows(table)
        headers = [clean_text(c.get_text(" ")).lower() for c in _direct_row_cells(rows[0])]

        col_map: dict[int, str] = {}
        for idx, h in enumerate(headers):
            mapped = _match_field_name(h)
            if mapped:
                col_map[idx] = mapped

        for row in rows[1:]:
            cells = _direct_row_cells(row)
            if not cells:
                continue
            rec = TenderRecord()
            for idx, cell in enumerate(cells):
                val = clean_text(cell.get_text(" "))
                field_name = col_map.get(idx)
                if field_name and is_valid_value(val):
                    setattr(rec, field_name, val)

                # Look for detail links and doc links inside each cell
                for a in cell.find_all("a", href=True):
                    abs_url = urljoin(base_url, a["href"].strip())
                    link_txt = clean_text(a.get_text(" "))
                    if _is_document_url(abs_url, link_txt):
                        if abs_url not in rec.document_urls:
                            rec.document_urls.append(abs_url)
                    elif rec.detail_url == NOT_AVAILABLE and not abs_url.startswith(
                        ("javascript:", "mailto:", "#")
                    ):
                        rec.detail_url = abs_url
                        if rec.title == NOT_AVAILABLE and len(link_txt) > 5:
                            rec.title = link_txt

            if rec.title != NOT_AVAILABLE or rec.tender_id != NOT_AVAILABLE or rec.detail_url != NOT_AVAILABLE:
                records.append(rec)

    if records:
        return deduplicate_tenders(records)

    # Strategy 2: Repeating tender cards / items
    cards = soup.select(
        ".tender-item, .tender-card, .tender-row, .bid-item, "
        "[data-tender-id], article.tender, li.tender, .listing-item"
    )
    for card in cards:
        rec = TenderRecord()
        kv = _extract_kv_pairs(card)
        for k, v in kv.items():
            setattr(rec, k, v)

        heading = card.find(["h1", "h2", "h3", "h4", "a"])
        if heading and rec.title == NOT_AVAILABLE:
            heading_txt = clean_text(heading.get_text(" "))
            if is_valid_value(heading_txt):
                rec.title = heading_txt

        for a in card.find_all("a", href=True):
            abs_url = urljoin(base_url, a["href"].strip())
            link_txt = clean_text(a.get_text(" "))
            if _is_document_url(abs_url, link_txt):
                if abs_url not in rec.document_urls:
                    rec.document_urls.append(abs_url)
            elif rec.detail_url == NOT_AVAILABLE and not abs_url.startswith(
                ("javascript:", "mailto:", "#")
            ):
                rec.detail_url = abs_url

        if rec.title != NOT_AVAILABLE or rec.detail_url != NOT_AVAILABLE:
            records.append(rec)

    if records:
        return deduplicate_tenders(records)

    # Strategy 3: Fallback anchor links that clearly point to individual tenders
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = clean_text(a.get_text(" "))
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        abs_url = urljoin(base_url, href)
        low_href = href.lower()
        if len(text) >= 12 and (
            any(tok in low_href for tok in ("tender", "nit", "bid", "rfp", "detail"))
            or any(tok in text.lower() for tok in ("tender for", "supply of", "construction of", "procurement of"))
        ):
            if not _is_document_url(abs_url, text):
                records.append(TenderRecord(title=text, detail_url=abs_url))

    return deduplicate_tenders(records)


def find_next_page_url(html: str, current_url: str) -> Optional[str]:
    """Find the pagination 'Next' URL if present on the same host."""
    soup = BeautifulSoup(html, "html.parser")
    curr_host = urlparse(current_url).netloc.lower().lstrip("www.")

    # 1. Explicit rel="next"
    rel_next = soup.find("a", rel=lambda v: v and "next" in [x.lower() for x in (v if isinstance(v, list) else [v])])
    if rel_next and rel_next.get("href"):
        candidate = urljoin(current_url, rel_next["href"].strip())
        if candidate != current_url:
            return candidate

    # 2. Anchor text/aria-label matching Next
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:")):
            continue
        text = clean_text(a.get_text(" ")).lower()
        aria = clean_text(a.get("aria-label", "")).lower()
        classes = " ".join(a.get("class", [])).lower()
        if "disabled" in classes:
            continue
        if text in {"next", "next >", "next »", ">", "»", "next page"} or "next" in aria:
            candidate = urljoin(current_url, href)
            cand_host = urlparse(candidate).netloc.lower().lstrip("www.")
            if cand_host == curr_host and candidate != current_url:
                return candidate

    return None


def extract_tender_details_from_html(
    html: str, url: str, existing: Optional[TenderRecord] = None
) -> TenderRecord:
    """
    Extract full tender metadata and document URLs from a tender detail page.
    Preserves any already-known valid values from `existing`.
    """
    rec = existing if existing is not None else TenderRecord()
    if rec.detail_url == NOT_AVAILABLE and url:
        rec.detail_url = url

    soup = BeautifulSoup(html, "html.parser")
    kv_pairs = _extract_kv_pairs(soup)

    for field_name, value in kv_pairs.items():
        current = getattr(rec, field_name, NOT_AVAILABLE)
        if current == NOT_AVAILABLE or (field_name == "title" and len(value) > len(current)):
            setattr(rec, field_name, value)

    # Extract title from main heading if still unavailable
    if rec.title == NOT_AVAILABLE:
        for tag_name in ("h1", "h2"):
            for h in soup.find_all(tag_name):
                txt = clean_text(h.get_text(" "))
                if len(txt) > 8 and txt.lower() not in {"tender details", "tender notice", "home"}:
                    rec.title = txt
                    break
            if rec.title != NOT_AVAILABLE:
                break

    # Extract Tender ID via regex pattern if still unavailable
    if rec.tender_id == NOT_AVAILABLE:
        body_text = soup.get_text(" ")
        m = re.search(
            r"(?:Tender\s*(?:ID|Ref(?:erence)?\s*(?:No\.?|Number)?)|NIT\s*No\.?)\s*[:\-]\s*([A-Za-z0-9/\-_]{4,40})",
            body_text,
            re.IGNORECASE,
        )
        if m:
            rec.tender_id = clean_text(m.group(1))

    # Extract document download links
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = urljoin(url, href)
        link_txt = clean_text(a.get_text(" "))
        if _is_document_url(abs_url, link_txt):
            if abs_url not in rec.document_urls:
                rec.document_urls.append(abs_url)

    return rec


def deduplicate_tenders(tenders: list[TenderRecord]) -> list[TenderRecord]:
    """Deduplicate tender records by Tender ID or Detail URL."""
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    unique: list[TenderRecord] = []

    for t in tenders:
        tid_key = clean_text(t.tender_id).lower() if t.tender_id != NOT_AVAILABLE else ""
        url_key = t.detail_url.strip().rstrip("/").lower() if t.detail_url != NOT_AVAILABLE else ""

        if tid_key and tid_key in seen_ids:
            continue
        if url_key and url_key in seen_urls:
            continue

        if tid_key:
            seen_ids.add(tid_key)
        if url_key:
            seen_urls.add(url_key)
        unique.append(t)

    return unique
