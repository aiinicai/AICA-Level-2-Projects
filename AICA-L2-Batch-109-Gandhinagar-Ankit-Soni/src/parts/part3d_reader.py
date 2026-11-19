

# ===========================================================================
#  READING A REPLY'S OWN DOCUMENT
# ---------------------------------------------------------------------------
#  The signed slip is the evidence; the covering e-mail is only a note about
#  it.  So where a reply carries a PDF or a scan, the application opens the
#  file itself: the text layer is read where there is one, and every page is
#  also put through OCR, because a slip that was printed, filled in by hand
#  and scanned has no text layer at all, and a figure written onto a digital
#  PDF sits in an annotation the text layer does not carry.
#
#  Both libraries are optional.  Without them the application still works,
#  on whatever text the bridge could extract, and says what is missing.
# ===========================================================================
READER_MAX_PAGES = 8          # a confirmation is one page; a statement more
READER_DPI = 220              # enough for handwriting, light on memory
READABLE_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff",
                       ".bmp", ".webp")

_OCR_ENGINE = None
_OCR_FAILED = ""


def _pymupdf():
    try:
        import pymupdf                      # the current name
        return pymupdf
    except Exception:
        try:
            import fitz                     # the name older releases used
            return fitz
        except Exception:
            return None


def _ocr_engine():
    """The OCR engine, built once.  Returns None when it is not installed."""
    global _OCR_ENGINE, _OCR_FAILED
    if _OCR_ENGINE is not None or _OCR_FAILED:
        return _OCR_ENGINE
    try:
        import logging
        logging.getLogger("RapidOCR").setLevel(logging.ERROR)
        try:
            from rapidocr import RapidOCR
        except Exception:
            from rapidocr_onnxruntime import RapidOCR
        _OCR_ENGINE = RapidOCR()
        for name in ("RapidOCR", "rapidocr"):          # it logs every call
            logging.getLogger(name).setLevel(logging.ERROR)
            logging.getLogger(name).disabled = True
    except Exception as exc:
        _OCR_FAILED = str(exc) or exc.__class__.__name__
        _OCR_ENGINE = None
    return _OCR_ENGINE


def reader_status():
    """What the application can read for itself, in words for the auditor."""
    # asked on every repaint, so it only looks for the libraries; the engine
    # itself takes seconds to build and is built by the worker that uses it
    def present(module):
        try:
            return importlib.util.find_spec(module) is not None
        except Exception:
            return False
    have_pdf = present("pymupdf") or present("fitz")
    have_ocr = not _OCR_FAILED and present("onnxruntime") and (
        present("rapidocr") or present("rapidocr_onnxruntime"))
    if have_pdf and have_ocr:
        return True, "PDFs and scans are read on this computer (text and OCR)"
    missing = []
    if not have_pdf:
        missing.append("pymupdf")
    if not have_ocr:
        missing.append("rapidocr and onnxruntime")
    return False, ("Not installed: %s. Run  python -m pip install pymupdf "
                   "rapidocr onnxruntime  and start the application again."
                   % " and ".join(missing))


def is_readable_file(name, content_type=""):
    lowered = str(name or "").lower()
    kind = str(content_type or "").lower()
    return lowered.endswith(READABLE_EXTENSIONS) or "pdf" in kind or \
        kind.startswith("image/")


def _ocr_boxes(result):
    """(box, text) pairs out of whichever result shape the engine returns."""
    pairs = []
    boxes = getattr(result, "boxes", None)
    texts = getattr(result, "txts", None)
    if boxes is not None and texts is not None:            # rapidocr 2 and 3
        for box, text in zip(boxes, texts):
            pairs.append((box, text))
        return pairs
    if isinstance(result, tuple) and result and result[0]:   # rapidocr 1
        for item in result[0]:
            pairs.append((item[0], item[1]))
    return pairs


def _lines_from_boxes(pairs):
    """Put OCR fragments back into reading order.

    The engine returns one box per run of text.  A figure written on the
    slip's blank comes back as its own box, so the boxes are grouped into
    lines by their vertical position and each line is read left to right:
    that is what puts the handwritten amount back after the words 'is INR'.
    """
    items = []
    for box, text in pairs:
        text = str(text or "").strip()
        if not text:
            continue
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        items.append({"x": min(xs), "y": (min(ys) + max(ys)) / 2.0,
                      "h": max(1.0, max(ys) - min(ys)), "text": text})
    items.sort(key=lambda item: (item["y"], item["x"]))
    lines = []
    for item in items:
        # handwriting sits a little above or below the printed baseline, so
        # the band is generous: 60% of the taller of the two heights
        if lines and abs(item["y"] - lines[-1]["y"]) <= \
                0.6 * max(item["h"], lines[-1]["h"]):
            lines[-1]["items"].append(item)
            count = len(lines[-1]["items"])
            lines[-1]["y"] += (item["y"] - lines[-1]["y"]) / count
            lines[-1]["h"] = max(lines[-1]["h"], item["h"])
        else:
            lines.append({"y": item["y"], "h": item["h"], "items": [item]})
    out = []
    for line in lines:
        line["items"].sort(key=lambda item: item["x"])
        out.append(" ".join(item["text"] for item in line["items"]))
    return "\n".join(out)


def tidy_ocr_text(text):
    """Remove what OCR adds that is not content.

    The rule on a slip's blank comes back as a run of underscores, dots or
    dashes; left in, it would sit between 'is INR' and the figure written
    over it.  Letters commonly mistaken inside a figure are put right only
    where the token is otherwise plainly a grouped number."""
    text = str(text or "")
    text = re.sub(r"[_]{2,}|[.]{4,}|[-—–]{3,}", " ", text)

    def digits_only(match):
        token = match.group(0)
        fixed = (token.replace("O", "0").replace("o", "0")
                 .replace("l", "1").replace("I", "1")
                 .replace("S", "5").replace("B", "8"))
        return fixed
    # e.g. 25,OO,000 or 2S,00,000 - grouped like a figure, digits in the main
    text = re.sub(r"(?<![A-Za-z])(?=[\dOolISB,]*\d)[\dOolISB]{1,3}"
                  r"(?:,[\dOolISB]{2,3})+(?![A-Za-z])", digits_only, text)
    return re.sub(r"[ \t]+", " ", text)


def ocr_image(image):
    """OCR one image (PNG/JPEG bytes, or a numpy array).  Returns text."""
    engine = _ocr_engine()
    if engine is None:
        return ""
    result = engine(image)
    return tidy_ocr_text(_lines_from_boxes(_ocr_boxes(result)))


def read_document(data, name="", content_type=""):
    """Read one attached file.

    Returns {text, method, pages, error}.  method is 'text', 'OCR' or
    'text + OCR', and is carried through to the register so the auditor can
    see how a figure was obtained."""
    result = {"text": "", "method": "", "pages": 0, "error": ""}
    if not data:
        result["error"] = "The file is empty"
        return result
    lowered = str(name or "").lower()
    is_pdf = data[:5] == b"%PDF-" or lowered.endswith(".pdf") or \
        "pdf" in str(content_type or "").lower()

    if not is_pdf:                                   # a photograph or a scan
        if _ocr_engine() is None:
            result["error"] = "OCR is not installed"
            return result
        try:
            result["text"] = ocr_image(data)
            result["method"], result["pages"] = "OCR", 1
        except Exception as exc:
            result["error"] = "The image could not be read: %s" % exc
        return result

    library = _pymupdf()
    if library is None:
        result["error"] = "PDF reading is not installed"
        return result
    try:
        document = library.open(stream=data, filetype="pdf")
    except Exception as exc:
        result["error"] = "The PDF could not be opened: %s" % exc
        return result
    if getattr(document, "needs_pass", False):
        result["error"] = "The PDF is password-protected"
        return result

    layer_parts, ocr_parts = [], []
    have_ocr = _ocr_engine() is not None
    try:
        for number, page in enumerate(document):
            if number >= READER_MAX_PAGES:
                break
            result["pages"] += 1
            layer = (page.get_text("text") or "").strip()
            if layer:
                layer_parts.append(tidy_ocr_text(layer))
            if have_ocr:
                try:
                    # rendered WITH annotations: a figure typed or inked onto
                    # a digital PDF lives there and nowhere else
                    pixmap = page.get_pixmap(dpi=READER_DPI, annots=True)
                    seen = ocr_image(pixmap.tobytes("png"))
                    if seen.strip():
                        ocr_parts.append(seen)
                except Exception as exc:
                    result["error"] = "OCR failed on page %d: %s" % (
                        number + 1, exc)
    finally:
        document.close()

    # the two readings are kept apart, the OCR one first: it is the only one
    # that can hold what was written on the page after it was printed
    parts = []
    if ocr_parts:
        parts.append("\n".join(ocr_parts))
    if layer_parts:
        parts.append("\n".join(layer_parts))
    result["text"] = "\n\n".join(parts).strip()
    result["method"] = " + ".join(
        label for label, present in (("text", layer_parts),
                                     ("OCR", ocr_parts)) if present)
    if not result["text"] and not result["error"]:
        result["error"] = ("Nothing could be read from the PDF" if have_ocr
                           else "The PDF is a scan and OCR is not installed")
    return result


def attachment_entry(name, reading):
    """A reply attachment record built from what the application read."""
    return {"name": name, "text": reading.get("text", ""),
            "method": reading.get("method", ""),
            "pages": reading.get("pages", 0),
            "read_by": "application",
            "error": reading.get("error", "")}


def reply_has_unread_files(reply):
    """True when a reply carries a PDF or image this application has not yet
    opened for itself."""
    if reply.get("files_read") or reply.get("bounced"):
        return False
    names = list(reply.get("files") or [])
    if not names:
        for attachment in reply.get("attachments") or []:
            if attachment.get("read_by") == "application":
                continue
            names += [part.strip() for part in
                      str(attachment.get("name") or "").split(";")]
    return any(is_readable_file(name) for name in names)


def attachment_url(feed_url, message_id):
    """The feed address asking for one message's own files."""
    parts = urllib.parse.urlsplit(feed_url)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query = [(k, v) for k, v in query if k != "message"]
    query.append(("message", message_id))
    return urllib.parse.urlunsplit(parts._replace(
        query=urllib.parse.urlencode(query)))


def fetch_reply_files(feed_url, message_id, timeout=90):
    """Download one reply's PDFs and images from the bridge.

    Returns ([(name, content_type, bytes)], skipped, error)."""
    request = urllib.request.Request(
        attachment_url(feed_url, message_id),
        headers={"User-Agent": "BalanceConfirmationGenerator/" + APP_VERSION,
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
        payload = json.loads(raw)
    except urllib.error.HTTPError as exc:
        return [], [], "the bridge refused the request (HTTP %s)" % exc.code
    except ValueError:
        return [], [], "the bridge returned a page rather than data"
    except Exception as exc:
        return [], [], "could not reach the bridge: %s" % exc
    if not isinstance(payload, dict):
        return [], [], "the bridge sent an unexpected answer"
    if "files" not in payload:
        # an older copy of the script ignores ?message= and sends the feed
        return [], [], ("the bridge script is an older version that cannot "
                        "hand over attachments. Paste the new script into "
                        "the Apps Script project and deploy a new version.")
    if payload.get("error"):
        return [], [], str(payload["error"])
    files = []
    for entry in payload.get("files") or []:
        try:
            data = base64.b64decode(entry.get("data") or "")
        except Exception:
            continue
        files.append((entry.get("name") or "attachment",
                      entry.get("type") or "", data))
    return files, list(payload.get("skipped") or []), ""
