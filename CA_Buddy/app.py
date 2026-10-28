"""CA_Buddy — PDFsmith (PDF toolkit) and SafeAsk (tax-notice assistant).
Run:  python app.py      (opens http://127.0.0.1:8765 in your browser)"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from core import llm, mdconv, notice, pdf_tools, pii, prompts
from core.pdf_tools import ToolError

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
STATIC = BASE / "static"
TMP_ROOT = Path(tempfile.gettempdir()) / "ca_workbench"
shutil.rmtree(TMP_ROOT, ignore_errors=True)  # clear leftovers from the last run
TMP_ROOT.mkdir(exist_ok=True)

app = FastAPI(title="CA_Buddy", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.exception_handler(ToolError)
async def tool_error(_: Request, exc: ToolError):
    return JSONResponse({"error": str(exc)}, status_code=400)


@app.exception_handler(Exception)
async def unexpected(_: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    return JSONResponse({"error": f"Something went wrong while processing: {exc}"}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


# ------------------------------------------------------------------ helpers

def new_workdir() -> Path:
    d = TMP_ROOT / uuid.uuid4().hex
    d.mkdir(parents=True)
    return d


async def save_upload(up: UploadFile, workdir: Path, idx: int = 0) -> Path:
    name = Path(up.filename or f"file{idx}").name
    dest = workdir / f"in{idx:03d}_{name}"
    with dest.open("wb") as f:
        while chunk := await up.read(1024 * 1024):
            f.write(chunk)
    return dest


def send(path: Path, download_name: str, info: str, workdir: Path) -> FileResponse:
    return FileResponse(path, filename=download_name,
                        headers={"X-Result-Info": quote(info)},
                        background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True))


def stem(up: UploadFile) -> str:
    return Path(up.filename or "document").stem


async def run(fn, *args):
    return await asyncio.to_thread(fn, *args)


def truthy(v: str | None) -> bool:
    return str(v).lower() in ("1", "true", "on", "yes")


# ------------------------------------------------------------------ status

@app.get("/api/status")
async def status():
    return {
        "ocr": pdf_tools.tesseract_available(),
        "ocr_languages": pdf_tools.ocr_languages(),
        "office": bool(pdf_tools._find_soffice()) or sys.platform == "win32",
        "providers": llm.PROVIDERS,
        "categories": {k: {"label": v[0], "on": v[2]} for k, v in pii.CATEGORIES.items()},
    }


# ------------------------------------------------------------------ PDF tools

@app.post("/api/pdf/thumbs")
async def thumbs(file: UploadFile = File(...), password: str = Form("")):
    wd = new_workdir()
    try:
        p = await save_upload(file, wd)
        return {"thumbs": await run(pdf_tools.thumbnails, p, password)}
    finally:
        shutil.rmtree(wd, ignore_errors=True)


@app.post("/api/pdf/merge")
async def merge(files: list[UploadFile] = File(...), titles: str = Form("[]"),
                index: str = Form("false"), bookmarks: str = Form("true"), labels: str = Form("false")):
    wd = new_workdir()
    paths = [await save_upload(f, wd, i) for i, f in enumerate(files)]
    t = json.loads(titles) or []
    t = [(t[i] if i < len(t) and t[i].strip() else stem(f)) for i, f in enumerate(files)]
    out, msg = await run(pdf_tools.merge, paths, t, wd / "merged.pdf", truthy(index),
                         truthy(bookmarks), truthy(labels))
    return send(out, "merged.pdf", msg, wd)


@app.post("/api/pdf/split")
async def split(file: UploadFile = File(...), mode: str = Form("ranges"), value: str = Form("")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.split, p, mode, value, wd, wd / f"{stem(file)}_split.zip")
    return send(out, out.name, msg, wd)


@app.post("/api/pdf/organize")
async def organize(file: UploadFile = File(...), pages: str = Form(...)):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.organize, p, json.loads(pages), wd / "out.pdf")
    return send(out, f"{stem(file)}_organised.pdf", msg, wd)


@app.post("/api/pdf/compress")
async def compress(file: UploadFile = File(...), level: str = Form("recommended"),
                   target: str = Form(""), grayscale: str = Form("false")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.compress, p, level, target, truthy(grayscale), wd / "out.pdf")
    return send(out, f"{stem(file)}_compressed.pdf", msg, wd)


@app.post("/api/pdf/to-word")
async def to_word(file: UploadFile = File(...)):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.pdf_to_word, p, wd / "out.docx")
    return send(out, f"{stem(file)}.docx", msg, wd)


@app.post("/api/pdf/to-excel")
async def to_excel(file: UploadFile = File(...)):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.pdf_to_excel, p, wd / "out.xlsx")
    return send(out, f"{stem(file)}.xlsx", msg, wd)


@app.post("/api/pdf/to-images")
async def to_images(file: UploadFile = File(...), fmt: str = Form("png"), dpi: int = Form(150)):
    wd = new_workdir()
    p = await save_upload(file, wd)
    fmt = "jpg" if fmt == "jpg" else "png"
    out, msg = await run(pdf_tools.pdf_to_images, p, fmt, max(50, min(dpi, 400)), wd, wd / "images.zip")
    return send(out, f"{stem(file)}_images.zip", msg, wd)


@app.post("/api/pdf/from-images")
async def from_images(files: list[UploadFile] = File(...), page_size: str = Form("a4")):
    wd = new_workdir()
    paths = [await save_upload(f, wd, i) for i, f in enumerate(files)]
    out, msg = await run(pdf_tools.images_to_pdf, paths, page_size, wd / "out.pdf")
    return send(out, f"{stem(files[0])}.pdf", msg, wd)


@app.post("/api/pdf/office-to-pdf")
async def office_to_pdf(file: UploadFile = File(...)):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.office_to_pdf, p, wd, wd / "converted.pdf")
    return send(out, f"{stem(file)}.pdf", msg, wd)


@app.post("/api/pdf/ocr")
async def ocr(file: UploadFile = File(...), lang: str = Form("eng")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.ocr_pdf, p, lang or "eng", wd / "out.pdf")
    return send(out, f"{stem(file)}_searchable.pdf", msg, wd)


@app.post("/api/pdf/to-text")
async def to_text(file: UploadFile = File(...)):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.pdf_to_text, p, wd / "out.txt")
    return send(out, f"{stem(file)}.txt", msg, wd)


@app.post("/api/pdf/protect")
async def protect(file: UploadFile = File(...), password: str = Form(""), owner_password: str = Form(""),
                  allow_print: str = Form("true"), allow_copy: str = Form("false")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.protect, p, password, owner_password, truthy(allow_print),
                         truthy(allow_copy), wd / "out.pdf")
    return send(out, f"{stem(file)}_protected.pdf", msg, wd)


@app.post("/api/pdf/unlock")
async def unlock(file: UploadFile = File(...), password: str = Form("")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.unlock, p, password, wd / "out.pdf")
    return send(out, f"{stem(file)}_unlocked.pdf", msg, wd)


@app.post("/api/pdf/watermark")
async def watermark(file: UploadFile = File(...), text: str = Form(""), opacity: float = Form(0.18),
                    color: str = Form("#7a7f8c"), size: float = Form(60), diagonal: str = Form("true"),
                    pages: str = Form("all")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.watermark, p, text, max(0.03, min(opacity, 1)), color, size,
                         truthy(diagonal), pages, wd / "out.pdf")
    return send(out, f"{stem(file)}_watermarked.pdf", msg, wd)


@app.post("/api/pdf/stamp")
async def stamp(file: UploadFile = File(...), image: UploadFile | None = File(None), text: str = Form(""),
                position: str = Form("bottom-right"), pages: str = Form("all"), width: float = Form(150),
                color: str = Form("#5b3fa8")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    img = await save_upload(image, wd, 1) if image and image.filename else None
    out, msg = await run(pdf_tools.stamp, p, text, img, position, pages, width, color, wd / "out.pdf")
    return send(out, f"{stem(file)}_stamped.pdf", msg, wd)


@app.post("/api/pdf/page-numbers")
async def page_numbers(file: UploadFile = File(...), fmt: str = Form("Page {n} of {total}"),
                       position: str = Form("bottom-center"), start: int = Form(1), size: float = Form(9),
                       skip_first: str = Form("false")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    out, msg = await run(pdf_tools.page_numbers, p, fmt, position, start, size, truthy(skip_first), wd / "out.pdf")
    return send(out, f"{stem(file)}_numbered.pdf", msg, wd)


@app.post("/api/pdf/redact/detect")
async def redact_detect(file: UploadFile = File(...)):
    wd = new_workdir()
    try:
        p = await save_upload(file, wd)
        return {"items": await run(pdf_tools.detect_redaction_terms, p)}
    finally:
        shutil.rmtree(wd, ignore_errors=True)


@app.post("/api/pdf/redact")
async def redact(file: UploadFile = File(...), terms: str = Form("[]")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    t = [x for x in json.loads(terms) if str(x).strip()]
    if not t:
        raise ToolError("Select or add at least one detail to redact.")
    out, msg = await run(pdf_tools.redact, p, t, wd / "out.pdf")
    return send(out, f"{stem(file)}_redacted.pdf", msg, wd)


# ---- redaction workspace: the PDF stays on this computer while the user marks it

REDACT: dict[str, dict] = {}


def redact_session(sid: str) -> dict:
    s = REDACT.get(sid)
    if not s:
        raise ToolError("This document is no longer open. Load it again.")
    s["t"] = time.time()
    return s


@app.post("/api/pdf/redact/open")
async def redact_open(file: UploadFile = File(...), password: str = Form("")):
    wd = new_workdir()
    src = await save_upload(file, wd)
    doc = pdf_tools.open_pdf(src, password)  # decrypt once so later steps need no password
    p = wd / "doc.pdf"
    doc.save(p)
    doc.close()
    while len(REDACT) >= 10:
        old = REDACT.pop(min(REDACT, key=lambda k: REDACT[k]["t"]))
        shutil.rmtree(old["dir"], ignore_errors=True)
    sid = uuid.uuid4().hex
    REDACT[sid] = {"dir": wd, "pdf": p, "name": stem(file), "t": time.time()}
    sizes = await run(pdf_tools.page_sizes, p)
    try:
        items = await run(pdf_tools.detect_redaction_terms, p)
    except Exception:  # noqa: BLE001 - detection is a convenience only
        items = []
    return {"session": sid, "pages": sizes, "items": items, "name": file.filename}


@app.get("/api/pdf/redact/page/{sid}/{index}")
async def redact_page(sid: str, index: int):
    from fastapi.responses import Response
    s = redact_session(sid)
    png = await run(pdf_tools.render_page, s["pdf"], index, 2.0)
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@app.post("/api/pdf/redact/find")
async def redact_find(session: str = Form(...), query: str = Form(""), match_case: str = Form("false"),
                      whole_word: str = Form("false"), pattern: str = Form("false")):
    s = redact_session(session)
    return await run(pdf_tools.find_text, s["pdf"], query, truthy(match_case), truthy(whole_word), truthy(pattern))


@app.post("/api/pdf/redact/apply")
async def redact_apply(session: str = Form(...), marks: str = Form("[]"), fill: str = Form("black")):
    s = redact_session(session)
    wd = new_workdir()
    out, msg = await run(pdf_tools.redact_marks, s["pdf"], json.loads(marks), wd / "out.pdf", fill)
    return send(out, f"{s['name']}_redacted.pdf", msg, wd)


@app.post("/api/pdf/redact/close")
async def redact_close(session: str = Form(...)):
    s = REDACT.pop(session, None)
    if s:
        shutil.rmtree(s["dir"], ignore_errors=True)
    return {"ok": True}


# ------------------------------------------------------------------ notices

SESSIONS: dict[str, dict] = {}


def get_session(sid: str) -> dict:
    s = SESSIONS.get(sid)
    if not s:
        raise ToolError("This notice is no longer loaded (the app may have restarted). Upload it again.")
    return s


def preview_segments(text: str, items: list[dict]) -> list:
    spans = pii.mask_spans(text, items)
    segs, pos = [], 0
    for a, b, tok in spans:
        if a > pos:
            segs.append(text[pos:a])
        segs.append({"orig": text[a:b], "token": tok})
        pos = b
    segs.append(text[pos:])
    return segs


def leaks_for(s: dict, extra_text: str = "") -> list[dict]:
    """Anything that still looks identifying in what would be sent, minus what the user chose to leave visible."""
    masked = pii.apply_mask(s["text"], s["items"])
    if extra_text:
        masked += "\n\n" + pii.apply_mask(extra_text, s["items"])
    allowed = s.setdefault("allowed", set())
    return [f for f in pii.leak_check(masked, s["items"]) if f["value"].lower() not in allowed]


def session_view(s: dict) -> dict:
    return {"session": s["id"], "items": s["items"], "segments": preview_segments(s["text"], s["items"]),
            "classification": s["classification"], "meta": s["meta"], "filename": s["filename"],
            "masked_chars": len(pii.apply_mask(s["text"], s["items"])), "leaks": leaks_for(s),
            "allowed": sorted(s.get("allowed", set()))}


@app.post("/api/notice/load")
async def notice_load(file: UploadFile = File(...), password: str = Form(""), lang: str = Form("eng")):
    wd = new_workdir()
    p = await save_upload(file, wd)
    try:
        text, meta = await run(notice.extract_text, p, password, True, lang or "eng")
    except ToolError:
        shutil.rmtree(wd, ignore_errors=True)
        raise
    items = pii.detect(text)
    sid = uuid.uuid4().hex
    while len(SESSIONS) >= 25:  # drop the oldest
        old = SESSIONS.pop(next(iter(SESSIONS)))
        shutil.rmtree(old["dir"], ignore_errors=True)
    SESSIONS[sid] = {"id": sid, "dir": wd, "pdf": p, "password": password, "text": text,
                     "items": items, "meta": meta, "classification": notice.classify(text),
                     "filename": file.filename, "history": []}
    return session_view(SESSIONS[sid])


@app.post("/api/notice/items")
async def notice_items(session: str = Form(...), items: str = Form(...)):
    """Accepts the user's edited item list (toggles, additions, removals)."""
    s = get_session(session)
    incoming = json.loads(items)
    clean = []
    for it in incoming:
        value = str(it.get("value", "")).strip()
        if not value:
            continue
        cat = it.get("category") if it.get("category") in pii.CATEGORIES else "custom"
        if not it.get("token"):
            it["token"] = pii.next_token(clean + [c for c in incoming if c.get("token")], cat)
        clean.append({"id": it.get("id") or uuid.uuid4().hex[:8], "category": cat, "value": value,
                      "token": it["token"], "label": pii.CATEGORIES[cat][0],
                      "enabled": bool(it.get("enabled", True)), "note": it.get("note", ""),
                      "count": pii.count_occurrences(s["text"], value)})
    s["items"] = clean
    s["history"] = []  # masking changed; start a fresh conversation
    return session_view(s)


@app.post("/api/notice/allow")
async def notice_allow(session: str = Form(...), values: str = Form("[]"), undo: str = Form("false")):
    """Mark leftover findings as deliberately visible (or undo that)."""
    s = get_session(session)
    allowed = s.setdefault("allowed", set())
    for v in json.loads(values):
        (allowed.discard if truthy(undo) else allowed.add)(str(v).strip().lower())
    return session_view(s)


@app.post("/api/notice/check")
async def notice_check(session: str = Form(...), instructions: str = Form("")):
    """Leak check over the notice plus the instructions the user typed."""
    return {"leaks": leaks_for(get_session(session), instructions)}


@app.post("/api/notice/masked-text")
async def notice_masked_text(session: str = Form(...)):
    s = get_session(session)
    return {"text": pii.apply_mask(s["text"], s["items"])}


@app.post("/api/notice/ask")
async def notice_ask(session: str = Form(...), task: str = Form("summary"), provider: str = Form(...),
                     model: str = Form(""), api_key: str = Form(""), instructions: str = Form(""),
                     tone: str = Form("balanced"), refine: str = Form("false"),
                     send_anyway: str = Form("false")):
    s = get_session(session)
    items = s["items"]
    masked_instr = pii.apply_mask(instructions, items)
    # hard stop: nothing that still looks identifying leaves this computer unless the user says so
    pending = leaks_for(s, instructions)
    if pending and not truthy(send_anyway):
        shown = ", ".join(f"“{f['value']}”" for f in pending[:6]) + (" and more" if len(pending) > 6 else "")
        return JSONResponse({"error": f"Not sent. These still look identifying: {shown}. Mask them, or mark them as fine to send.",
                             "leaks": pending}, status_code=409)
    if truthy(refine):
        if not s["history"]:
            raise ToolError("Ask for a summary or a draft first, then refine it.")
        if not instructions.strip():
            raise ToolError("Describe what to change.")
        msgs = s["history"] + [{"role": "user", "content": prompts.REFINE.format(instructions=masked_instr)}]
        task = s.get("task", task)
    else:
        masked = pii.apply_mask(s["text"], items)
        user = prompts.build_user_message(task, masked, pii.context_notes(items), s["classification"],
                                          masked_instr, tone)
        msgs = [{"role": "user", "content": user}]
    started = time.time()
    answer = await llm.complete(provider, model, api_key, prompts.SYSTEM, msgs)
    if not answer.strip():
        raise ToolError("The model returned an empty answer. Try again or choose another model.")
    s["history"] = msgs + [{"role": "assistant", "content": answer}]
    s["task"] = task
    real = pii.unmask(answer, items)
    return {"task": task, "markdown": real, "html": mdconv.to_html(real), "masked_markdown": answer,
            "sent_chars": sum(len(m["content"]) for m in msgs), "seconds": round(time.time() - started, 1),
            "provider": provider, "model": model or llm.PROVIDERS[provider]["default"]}


@app.post("/api/render")
async def render(markdown: str = Form("")):
    return {"html": mdconv.to_html(markdown)}


@app.post("/api/notice/docx")
async def notice_docx(markdown: str = Form(...), task: str = Form("summary"), filename: str = Form("notice")):
    wd = new_workdir()
    base = Path(filename).stem or "notice"
    if task == "summary":
        out = mdconv.to_docx(markdown, wd / "out.docx", title=f"Notice summary — {base}",
                             footer="AI-assisted summary. Verify against the notice before relying on it.")
        name = f"{base}_summary.docx"
    else:
        out = mdconv.to_docx(markdown, wd / "out.docx")
        name = f"{base}_draft_reply.docx"
    return send(out, name, "Word file ready.", wd)


@app.post("/api/notice/masked-pdf")
async def notice_masked_pdf(session: str = Form(...)):
    s = get_session(session)
    terms = [i["value"] for i in s["items"] if i.get("enabled")]
    wd = new_workdir()
    src = s["pdf"]
    if s.get("password"):
        tmp = wd / "unlocked.pdf"
        pdf_tools.unlock(src, s["password"], tmp)
        src = tmp
    out, msg = await run(pdf_tools.redact, src, terms, wd / "redacted.pdf")
    return send(out, f"{Path(s['filename']).stem}_redacted.pdf", msg, wd)


@app.post("/api/models")
async def models(provider: str = Form(...), api_key: str = Form("")):
    return {"models": await llm.list_models(provider, api_key)}


# ------------------------------------------------------------------ launcher

def free_port(start: int = 8765) -> int:
    for port in range(start, start + 30):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit("No free port found between 8765 and 8795.")


def main():
    import uvicorn
    port = int(os.environ.get("CAWB_PORT") or free_port())
    url = f"http://127.0.0.1:{port}"
    print(f"\n  CA_Buddy is running at {url}\n  Keep this window open while you use it. Close it to stop.\n")
    if not os.environ.get("CAWB_NO_BROWSER"):
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
