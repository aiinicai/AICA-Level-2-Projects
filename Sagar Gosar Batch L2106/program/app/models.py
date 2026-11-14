"""Data classes shared by the engine and the interface."""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Block:
    idx: int = 0
    text: str = ""
    label: str = ""
    body: str = ""
    kind: str = "para"
    page: int = 0
    regions: list = field(default_factory=list)      # [(page, x0, y0, x1, y1)] fractions of the page
    conf: float = 100.0
    word_conf: list = field(default_factory=list)    # per word of `body`
    ocr: bool = False
    uid: int = -1
    ignored: bool = False


@dataclass
class DocText:
    path: str = ""
    name: str = ""
    kind: str = "docx"                # docx | pdf | txt | image
    blocks: List[Block] = field(default_factory=list)
    n_pages: int = 0
    ocr_pages: List[int] = field(default_factory=list)
    page_conf: dict = field(default_factory=dict)
    page_words: dict = field(default_factory=dict)
    page_transform: dict = field(default_factory=dict)    # page -> (rotation, skew) applied before OCR
    page_pixels: dict = field(default_factory=dict)
    pages_used: List[int] = field(default_factory=list)
    repeat_heads: List[str] = field(default_factory=list)
    excluded_pages: List[int] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sha256: str = ""
    size: int = 0
    modified: str = ""


@dataclass
class CompareOptions:
    ignore_case: bool = True
    compare_punct: bool = False
    ocr_tolerance: bool = True
    force_ocr: bool = False
    ocr_dpi: int = 300
    ocr_lang: str = "eng"
    drop_headers_footers: bool = True
    include_ocr_variances_in_export: bool = False
    include_info_in_export: bool = True
    ignore_colour_ink: bool = True
    seal_recovery: bool = True
    second_engine: bool = True
    enhance_scan: bool = True
    reflow: bool = True
    ignore_stamps: bool = True
    auto_rotate: bool = True
    page_rotation: Optional[dict] = None
    pages: Optional[List[int]] = None


@dataclass
class Item:
    id: int = 0
    kind: str = "changed"             # changed | added | deleted | replaced
    severity: str = "Minor"           # Critical | Major | Minor | Info
    categories: List[str] = field(default_factory=list)
    summary: str = ""
    text_a: str = ""
    text_b: str = ""
    label_a: str = ""
    label_b: str = ""
    idx_a: int = -1
    idx_b: int = -1
    pages_b: List[int] = field(default_factory=list)
    regions_b: list = field(default_factory=list)
    ocr_only: bool = False
    ops: list = field(default_factory=list)      # [(tag, words_a, words_b)] of the whole paragraph pair, for display
    low_conf: bool = False


@dataclass
class Row:
    label_a: str = ""
    label_b: str = ""
    kind: str = "equal"
    ops: list = field(default_factory=list)
    text_a: str = ""
    text_b: str = ""


@dataclass
class CompareResult:
    doc_a: DocText = None
    doc_b: DocText = None
    items: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    observations: list = field(default_factory=list)
    similarity: float = 0.0
    raw_a: DocText = None
    raw_b: DocText = None
    ignored_b: list = field(default_factory=list)
    anchors_used: int = 0
    created: str = ""
    label_a: str = "Draft / base document"
    label_b: str = "Executed copy"
    n_pairs: int = 0
    n_identical: int = 0
