#!/usr/bin/env python3
"""
ChatVault CLI — archive a WhatsApp chat export from the command line.

Reads the ZIP (or .txt) that WhatsApp produces with "Export chat → Include media",
and writes an organised archive folder:

    <Chat>_archive/
        Media/Photos|Videos|Audio|Documents/<date>_<time>_<sender>_<file>
        Index.xlsx                 every message and attachment, with SHA-256
        Transcript.pdf             paginated, court-friendly transcript
        Original transcript.txt
        INTEGRITY STATEMENT.txt    source hash, counts, period, operator
        SHA256SUMS.txt             verify later with:  sha256sum -c SHA256SUMS.txt

Usage:
    python chatvault.py "WhatsApp Chat with X.zip" [-o out_dir] [--me "Your Name"] [--mask]

Requires: openpyxl, reportlab   (pip install openpyxl reportlab)
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import io
import os
import re
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

VERSION = "1.0"

# ----------------------------------------------------------------- parsing
RE_ANDROID = re.compile(
    r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4}),?\s+(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?"
    r"(?:[\s\u202f\u00a0]*([AaPp])\.?\s?[Mm]\.?)?\s*[-–]\s(.*)$")
RE_IOS = re.compile(
    r"^[\u200e\u200f]?\[(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4}),?\s+(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?"
    r"(?:[\s\u202f\u00a0]*([AaPp])\.?\s?[Mm]\.?)?\]\s?(.*)$")
RE_SYS = re.compile(r"(end-to-end encrypted|created group|created this group|\badded\b|\bremoved\b|\bleft$|joined using|"
                    r"changed the subject|changed this group|changed the group|security code|changed their phone number|"
                    r"pinned a message|disappearing messages|is a contact|now an admin|turned (on|off))", re.I)
RE_OMIT = re.compile(r"^(?:<Media omitted>|(image|video|audio|document|sticker|GIF|Contact card|video note) omitted)$", re.I)
RE_DEL = re.compile(r"^(This message was deleted\.?|You deleted this message\.?)$", re.I)
RE_ATT_IOS = re.compile(r"<attached:\s*([^>]+)>")
RE_ATT_AND = re.compile(r"^\u200e?(.+?\.[A-Za-z0-9]{2,5})\s\(file attached\)\s*(?:\n([\s\S]*))?$")
INVIS = re.compile(r"[\u200e\u200f\u202a-\u202e]")
PHONE = re.compile(r"(\+?\d[\d\s\-]{8,}\d)")
MAIL = re.compile(r"([\w.+-]+)@([\w-]+\.[\w.-]+)")

FOLDERS = {"image": "Photos", "sticker": "Photos", "video": "Videos", "audio": "Audio", "doc": "Documents", "contact": "Contacts"}


def kind_of(name: str) -> str:
    n = name.lower()
    if (n.startswith("stk-") or "sticker" in n) and n.endswith(".webp"):
        return "sticker"
    if re.search(r"\.(jpe?g|png|webp|gif|heic|bmp)$", n): return "image"
    if re.search(r"\.(mp4|3gp|mov|mkv|webm|m4v)$", n): return "video"
    if re.search(r"\.(opus|ogg|m4a|mp3|aac|amr|wav)$", n): return "audio"
    if n.endswith(".vcf"): return "contact"
    return "doc"


@dataclass
class Message:
    id: int
    ts: datetime
    sender: str | None
    type: str = "text"           # text | media | system | deleted | omitted
    text: str = ""
    media: str | None = None
    kind: str | None = None
    edited: bool = False
    saved_as: str = ""
    sha256: str = ""


@dataclass
class Chat:
    title: str
    fmt: str
    messages: list[Message]
    participants: dict[str, int] = field(default_factory=dict)


def parse_chat(raw: str, title: str) -> Chat:
    text = raw.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    ios = sum(1 for l in lines[:80] if RE_IOS.match(l))
    andr = sum(1 for l in lines[:80] if not RE_IOS.match(l) and RE_ANDROID.match(l))
    if not ios and not andr:
        raise ValueError("This file does not look like a WhatsApp chat export.")
    rx, fmt = (RE_IOS, "iPhone") if ios > andr else (RE_ANDROID, "Android")

    raws: list[dict] = []
    for l in lines:
        m = rx.match(l)
        if m:
            raws.append({"g": m.groups(), "more": []})
        elif raws:
            raws[-1]["more"].append(l)
    if raws and raws[-1]["more"] and raws[-1]["more"][-1] == "":
        raws[-1]["more"].pop()
    mdy = not any(int(r["g"][0]) > 12 for r in raws) and any(int(r["g"][1]) > 12 for r in raws)

    msgs: list[Message] = []
    counts: dict[str, int] = {}
    for i, r in enumerate(raws, 1):
        a, b, y, H, M, S, ap, rest = r["g"]
        day, mon = (int(b), int(a)) if mdy else (int(a), int(b))
        yr = int(y) + (2000 if int(y) < 100 else 0)
        hh = int(H)
        if ap and ap.lower() == "p" and hh < 12: hh += 12
        if ap and ap.lower() == "a" and hh == 12: hh = 0
        ts = datetime(yr, mon, day, hh, int(M), int(S or 0))
        sender, body = None, rest
        ci = rest.find(": ")
        if 0 < ci <= 80:
            sender, body = INVIS.sub("", rest[:ci]).strip(), rest[ci + 2:]
        body = "\n".join([body] + r["more"])
        msg = Message(i, ts, sender)
        if re.search(r"<This message was edited>\s*$", body):
            msg.edited = True
            body = re.sub(r"\s*\u200e?<This message was edited>\s*$", "", body)
        clean = lambda s: INVIS.sub("", s).strip()
        att_i, att_a = RE_ATT_IOS.search(body), RE_ATT_AND.match(body)
        if not sender:
            msg.type, msg.text = "system", clean(body)
        elif att_i:
            msg.type, msg.media = "media", att_i.group(1).strip()
            rem = clean(body.replace(att_i.group(0), ""))
            msg.text = "" if " • " in rem else rem
        elif att_a:
            msg.type, msg.media, msg.text = "media", att_a.group(1).strip(), clean(att_a.group(2) or "")
        elif RE_OMIT.match(clean(body)):
            msg.type, msg.text = "omitted", (RE_OMIT.match(clean(body)).group(1) or "media").lower()
        elif RE_DEL.match(clean(body)):
            msg.type, msg.text = "deleted", clean(body)
        elif body.startswith("\u200e") and fmt == "iPhone" and RE_SYS.search(body):
            msg.type, msg.text, msg.sender = "system", clean(body), None
        else:
            msg.text = body.replace("\u200e", "").replace("\u200f", "")
        if msg.media:
            msg.kind = kind_of(msg.media)
        if msg.sender:
            counts[msg.sender] = counts.get(msg.sender, 0) + 1
        msgs.append(msg)
    return Chat(title, fmt, msgs, dict(sorted(counts.items(), key=lambda kv: -kv[1])))


# ----------------------------------------------------------------- helpers
def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def slug(s: str) -> str:
    s = re.sub(r"[^\w\s.-]", "", s, flags=re.UNICODE).strip()
    return re.sub(r"-{2,}", "-", re.sub(r"\s+", "-", s))[:60] or "chat"


def mask_text(s: str) -> str:
    def ph(m):
        d = re.sub(r"\D", "", m.group(0))
        return m.group(0) if len(d) < 10 else "•••• ••" + d[-3:]
    return MAIL.sub(lambda m: m.group(1)[0] + "•••@" + m.group(2), PHONE.sub(ph, s))


def title_from(name: str) -> str:
    t = re.sub(r"\.(zip|txt)$", "", Path(name).name, flags=re.I)
    t = re.sub(r"^WhatsApp Chat (with |- )?", "", t, flags=re.I).strip()
    return "" if t == "_chat" else t


# ----------------------------------------------------------------- outputs
def write_xlsx(path: Path, chat: Chat, files: list[tuple[str, int, str]], cert: str, M):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active; ws.title = "Messages"
    head = ["No.", "Date", "Time", "Sender", "Type", "Message", "Attachment", "Saved as", "Attachment SHA-256", "Edited"]
    ws.append(head)
    for m in chat.messages:
        ws.append([m.id, m.ts.strftime("%Y-%m-%d"), m.ts.strftime("%I:%M %p").lstrip("0").lower(),
                   M(m.sender) if m.sender else "(system)", m.kind if m.type == "media" else m.type,
                   M(m.text), m.media or "", m.saved_as, m.sha256, "Yes" if m.edited else ""])
    bold, fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="0D7A65")
    for c in ws[1]:
        c.font, c.fill = bold, fill
    for col, w in zip("ABCDEFGHIJ", [6, 11, 9, 22, 9, 70, 34, 52, 66, 7]):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2, min_col=6, max_col=6):
        row[0].alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions

    wp = wb.create_sheet("Participants"); wp.append(["Participant", "Messages", "Attachments"])
    for n, c in chat.participants.items():
        wp.append([M(n), c, sum(1 for m in chat.messages if m.sender == n and m.type == "media")])
    wf = wb.create_sheet("File fingerprints"); wf.append(["File", "Size (bytes)", "SHA-256"])
    for f in files: wf.append(list(f))
    wc = wb.create_sheet("Integrity statement")
    for line in cert.split("\n"): wc.append([line])
    for sh, widths in [(wp, [28, 10, 12]), (wf, [48, 12, 66]), (wc, [110])]:
        for c in sh[1]:
            if sh is not wc: c.font, c.fill = bold, fill
        for i, w in enumerate(widths):
            sh.column_dimensions["ABC"[i]].width = w
    wb.save(path)


def write_pdf(path: Path, chat: Chat, cert: str, me: str | None, M):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak, Preformatted

    font, fontb = "Helvetica", "Helvetica-Bold"
    for cand in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/segoeui.ttf", "/Library/Fonts/Arial Unicode.ttf"]:
        if os.path.exists(cand):
            try:
                pdfmetrics.registerFont(TTFont("CV", cand)); font = fontb = "CV"
                b = cand.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf").replace("segoeui.ttf", "segoeuib.ttf")
                if os.path.exists(b): pdfmetrics.registerFont(TTFont("CVB", b)); fontb = "CVB"
            except Exception:
                pass
            break
    brand = colors.HexColor("#0d7a65")
    st_t = ParagraphStyle("t", fontName=fontb, fontSize=16, leading=20, textColor=brand)
    st_s = ParagraphStyle("s", fontName=font, fontSize=9, leading=12, textColor=colors.HexColor("#54656f"))
    st_m = ParagraphStyle("m", fontName=font, fontSize=9.5, leading=13)
    st_h = ParagraphStyle("h", fontName=fontb, fontSize=8.5, leading=11, textColor=colors.HexColor("#3b4a52"))
    st_d = ParagraphStyle("d", fontName=fontb, fontSize=9, leading=12, alignment=1, textColor=colors.HexColor("#54656f"))
    emoji = re.compile("[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F]")  # PDF fonts rarely include emoji
    esc = lambda s: emoji.sub("", s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")

    def footer(c, d):
        c.saveState(); c.setFont(font, 7.5); c.setFillColor(colors.HexColor("#83939b"))
        c.drawString(15 * mm, 10 * mm, f"{chat.title} · ChatVault {VERSION}")
        c.drawRightString(195 * mm, 10 * mm, f"Page {d.page}"); c.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=18 * mm,
                            title=f"{chat.title} – WhatsApp transcript", author="ChatVault")
    first, last = chat.messages[0].ts, chat.messages[-1].ts
    story = [Paragraph(esc(M(chat.title)), st_t),
             Paragraph(f"WhatsApp {chat.fmt} export · {first:%d %b %Y} to {last:%d %b %Y} · {len(chat.messages)} messages", st_s),
             Spacer(1, 8)]
    rows, day = [], None
    for m in chat.messages:
        if m.ts.date() != day:
            day = m.ts.date()
            rows.append(("day", Paragraph(m.ts.strftime("%A, %d %B %Y").upper(), st_d)))
        if m.type == "system":
            rows.append(("sys", Paragraph(f"<i>{esc(M(m.text))}</i>", st_d))); continue
        body = {"deleted": "<i>This message was deleted</i>", "omitted": f"<i>{esc(m.text.capitalize())} not included in export</i>"}.get(m.type)
        if body is None:
            body = esc(M(m.text))
            if m.type == "media":
                tag = f"[{(m.kind or 'file').upper()}: {esc(m.media)}{'' if m.sha256 else ' — missing from export'}]"
                body = f"<font color='#0d7a65'>{tag}</font>" + ("<br/>" + body if body else "")
        who = "You" if me and m.sender == me else M(m.sender)
        rows.append(("msg", [Paragraph(f"#{m.id}", st_s), Paragraph(m.ts.strftime("%I:%M %p").lstrip("0").lower(), st_s),
                             Paragraph(esc(who), st_h), Paragraph(body + (" <font color='#83939b' size='7.5'>(edited)</font>" if m.edited else ""), st_m)]))
    data, styles = [], [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e1e7e4")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    for kind, val in rows:
        if kind == "msg":
            data.append(val)
        else:
            data.append([val, "", "", ""]); r = len(data) - 1
            styles += [("SPAN", (0, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f2f5f4" if kind == "day" else "#fff8dc"))]
    t = Table(data, colWidths=[11 * mm, 20 * mm, 32 * mm, None], repeatRows=0)
    t.setStyle(TableStyle(styles)); story += [t, PageBreak(), Paragraph("Integrity statement", st_t), Spacer(1, 6),
                                             Preformatted(cert, ParagraphStyle("pre", fontName="Courier", fontSize=7, leading=9))]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


# ----------------------------------------------------------------- main
def archive(src: Path, out_dir: Path, me: str | None, mask: bool) -> Path:
    raw = src.read_bytes()
    src_hash = sha256(raw)
    files: list[tuple[str, int, str]] = []
    media: dict[str, bytes] = {}
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = [n for n in z.namelist() if not n.endswith("/") and not n.startswith("__MACOSX/")]
            txts = [n for n in names if n.lower().endswith(".txt")]
            chat_name = next((n for n in txts if Path(n).name == "_chat.txt"), None) or \
                next((n for n in txts if "whatsapp chat" in n.lower()), None) or \
                max(txts, key=lambda n: z.getinfo(n).file_size, default=None)
            if not chat_name:
                sys.exit("No chat text file found inside the ZIP.")
            for n in names:
                b = z.read(n); files.append((Path(n).name, len(b), sha256(b)))
                if n != chat_name: media[Path(n).name] = b
            text = z.read(chat_name).decode("utf-8", errors="replace")
    else:
        text = raw.decode("utf-8", errors="replace"); files.append((src.name, len(raw), src_hash))

    title = title_from(src.name) or "WhatsApp chat"
    chat = parse_chat(text, title)
    if not me and len(chat.participants) == 2:
        me = next((p for p in chat.participants if p != title), None)
    M = mask_text if mask else (lambda s: s or "")

    root = out_dir / f"{slug(title)}_archive"
    (root / "Media").mkdir(parents=True, exist_ok=True)
    sums, linked, missing, placed = [], 0, 0, set()
    for m in chat.messages:
        if m.type != "media": continue
        b = media.get(m.media) or next((v for k, v in media.items() if k.endswith(m.media) or m.media.endswith(k)), None)
        if b is None:
            missing += 1; continue
        linked += 1
        base = re.sub(r"^\d{8}-", "", m.media)
        rel = f"Media/{FOLDERS.get(m.kind, 'Other')}/{m.ts:%Y-%m-%d_%H%M}_{slug(m.sender)}_{base}"
        m.saved_as, m.sha256 = rel, sha256(b)
        if rel not in placed:
            (root / rel).parent.mkdir(parents=True, exist_ok=True); (root / rel).write_bytes(b)
            sums.append(f"{m.sha256}  {rel}"); placed.add(rel)

    first, last = chat.messages[0].ts, chat.messages[-1].ts
    operator = getpass.getuser()
    cert = "\n".join([
        "ELECTRONIC RECORD INTEGRITY STATEMENT", "=" * 38, "",
        f"Chat: {title}", f"Source file: {src.name}", f"Source size: {len(raw):,} bytes",
        f"SHA-256 of source file: {src_hash}", f"Export format: WhatsApp {chat.fmt}",
        f"Period covered: {first:%d %b %Y %H:%M:%S} to {last:%d %b %Y %H:%M:%S}",
        f"Messages: {len(chat.messages)}   Participants: {len(chat.participants)}   Files in export: {len(files)}",
        f"Attachments linked: {linked}   Referenced but missing: {missing}",
        f"Archive generated: {datetime.now():%d %b %Y %H:%M:%S} by operator \"{operator}\" using ChatVault CLI {VERSION}",
        "Contact details: phone numbers and email addresses masked in this archive" if mask else "Contact details: not masked", "",
        "SHA-256 values of every file in the source export:",
        *[f"  {h}  {n} ({s} bytes)" for n, s, h in files], "",
        "Hash values were computed at the time of processing. Any change to a file changes its value.",
        "This statement supports, and does not replace, the certificate required for electronic records",
        "under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023.",
    ])
    (root / "INTEGRITY STATEMENT.txt").write_text(cert, encoding="utf-8")
    (root / "Original transcript.txt").write_text(M(text), encoding="utf-8")
    (root / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    write_xlsx(root / "Index.xlsx", chat, files, cert, M)
    write_pdf(root / "Transcript.pdf", chat, cert, me, M)

    print(f"Chat:          {title} ({chat.fmt} export)")
    print(f"Messages:      {len(chat.messages)}  ·  participants: {', '.join(M(p) for p in chat.participants)}")
    print(f"Attachments:   {linked} linked, {missing} missing")
    print(f"Source SHA-256 {src_hash}")
    print(f"Archive:       {root}")
    return root


def main():
    ap = argparse.ArgumentParser(description="Archive a WhatsApp chat export with SHA-256 fingerprints.")
    ap.add_argument("export", type=Path, help="the .zip (with media) or .txt exported from WhatsApp")
    ap.add_argument("-o", "--out", type=Path, default=Path("."), help="folder to write the archive into")
    ap.add_argument("--me", help="your name as it appears in the chat (shown as 'You' in the transcript)")
    ap.add_argument("--mask", action="store_true", help="mask phone numbers and email addresses")
    a = ap.parse_args()
    if not a.export.exists():
        sys.exit(f"File not found: {a.export}")
    archive(a.export, a.out, a.me, a.mask)


if __name__ == "__main__":
    main()
