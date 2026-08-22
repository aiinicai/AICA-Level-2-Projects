from __future__ import annotations

import html
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# Word text-bearing XML parts. This includes headers and footers, which is
# essential because CA Firm Name may occur in the report header.
WORD_TEXT_PART_RE = re.compile(
    r"^word/(document|header\d+|footer\d+|footnotes|endnotes|comments)\.xml$"
)

# We deliberately do not parse/re-serialize the complete Word XML. We only
# modify the character data contained in existing w:t nodes.
W_T_RE = re.compile(rb"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
W_P_RE = re.compile(rb"<w:p(?:\s[^>]*)?>(.*?)</w:p>", re.S)
PLACEHOLDER_RE = re.compile(r"\{[^{}]+\}")


def _xml_escape(value: str) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _decode_text(raw: bytes) -> str:
    # Word text nodes can contain XML entities. html.unescape safely decodes
    # the standard XML entities used in text while leaving normal characters.
    return html.unescape(raw.decode("utf-8", errors="replace"))


def _paragraph_nodes(xml_bytes: bytes):
    """Yield paragraph byte ranges and their w:t node ranges.

    Paragraph-level processing allows placeholders such as {Signing CA} to be
    detected/replaced even when Word has split them across multiple runs:

        <w:t>{</w:t><w:t>Signing CA</w:t><w:t>}</w:t>

    No XML is reconstructed; only existing w:t body bytes are changed.
    """
    for p in W_P_RE.finditer(xml_bytes):
        nodes = []
        for t in W_T_RE.finditer(p.group(1)):
            # Coordinates are relative to p.group(1), then translated to the
            # original XML byte stream.
            body_start = p.start(1) + t.start(1)
            body_end = p.start(1) + t.end(1)
            nodes.append({
                "start": body_start,
                "end": body_end,
                "text": _decode_text(t.group(1)),
            })
        if nodes:
            yield p.start(1), p.end(1), nodes


def _replace_in_paragraph(nodes: List[dict], replacements: Dict[str, str]) -> int:
    """Replace placeholders in one paragraph, including cross-run tokens."""
    count = 0

    # Work on the current node text values. We repeatedly rebuild the logical
    # paragraph string, so multiple occurrences and multiple placeholders are
    # handled correctly.
    while True:
        logical = "".join(n["text"] for n in nodes)
        found = None
        # Longest tokens first prevents a shorter token from stealing a match
        # when aliases overlap.
        for token in sorted(replacements, key=len, reverse=True):
            pos = logical.find(token)
            if pos >= 0:
                found = (pos, token, str(replacements[token]))
                break
        if found is None:
            break

        pos, token, replacement = found
        end_pos = pos + len(token)

        # Map logical character positions to node/offset positions.
        start_node = end_node = None
        start_off = end_off = None
        cursor = 0
        for i, node in enumerate(nodes):
            nend = cursor + len(node["text"])
            if start_node is None and cursor <= pos < nend:
                start_node, start_off = i, pos - cursor
            # A token can end exactly at the end of a node. Use <= for the
            # ending boundary and then normalise to the last involved node.
            if cursor < end_pos <= nend:
                end_node, end_off = i, end_pos - cursor
                break
            cursor = nend

        if start_node is None or end_node is None:
            # Defensive guard; should never occur because the match came from
            # the concatenated node text.
            break

        if start_node == end_node:
            s = nodes[start_node]["text"]
            nodes[start_node]["text"] = s[:start_off] + replacement + s[end_off:]
        else:
            first = nodes[start_node]["text"]
            last = nodes[end_node]["text"]
            nodes[start_node]["text"] = first[:start_off] + replacement
            for i in range(start_node + 1, end_node):
                nodes[i]["text"] = ""
            nodes[end_node]["text"] = last[end_off:]

        count += 1

    return count


def _process_xml(data: bytes, replacements: Dict[str, str]) -> Tuple[bytes, int]:
    patches = []
    total = 0

    for _, _, nodes in _paragraph_nodes(data):
        original = [(n["start"], n["end"], n["text"]) for n in nodes]
        n = _replace_in_paragraph(nodes, replacements)
        if not n:
            continue
        total += n
        for node, old in zip(nodes, original):
            if node["text"] != old[2]:
                patches.append((node["start"], node["end"], _xml_escape(node["text"]).encode("utf-8")))

    if not patches:
        return data, total

    result = bytearray(data)
    for start, end, new_body in sorted(patches, key=lambda x: x[0], reverse=True):
        result[start:end] = new_body
    return bytes(result), total


def _iter_word_parts(z: zipfile.ZipFile):
    for item in z.infolist():
        if WORD_TEXT_PART_RE.match(item.filename):
            yield item


def extract_placeholders(docx_path: Path) -> List[str]:
    found = set()
    with zipfile.ZipFile(docx_path, "r") as z:
        for item in _iter_word_parts(z):
            data = z.read(item.filename)
            for _, _, nodes in _paragraph_nodes(data):
                text = "".join(n["text"] for n in nodes)
                found.update(PLACEHOLDER_RE.findall(text))
    return sorted(found)


def replace_texts(docx_path: Path, output_path: Path, replacements: Dict[str, str]) -> Tuple[int, List[str]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(output_path, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if WORD_TEXT_PART_RE.match(item.filename):
                data, n = _process_xml(data, replacements)
                total += n
            zout.writestr(item, data)
    return total, extract_placeholders(output_path)


def validate_template(docx_path: Path, expected_placeholders: Iterable[str] | None = None) -> dict:
    placeholders = extract_placeholders(docx_path)
    readable = False
    paragraph_count = table_count = section_count = 0

    with zipfile.ZipFile(docx_path, "r") as z:
        names = set(z.namelist())
        readable = "[Content_Types].xml" in names and "word/document.xml" in names
        for name in z.namelist():
            if not WORD_TEXT_PART_RE.match(name):
                continue
            try:
                root = ET.fromstring(z.read(name))
            except Exception:
                continue
            paragraph_count += sum(1 for e in root.iter() if e.tag.endswith("}p"))
            table_count += sum(1 for e in root.iter() if e.tag.endswith("}tbl"))
            if name == "word/document.xml":
                section_count += sum(1 for e in root.iter() if e.tag.endswith("}sectPr"))

    result = {
        "file": docx_path.name,
        "readable": readable,
        "placeholders": placeholders,
        "paragraph_count": paragraph_count,
        "table_count": table_count,
        "section_count": section_count,
    }
    if expected_placeholders is not None:
        expected = set(expected_placeholders)
        actual = set(placeholders)
        result["missing_expected"] = sorted(expected - actual)
        result["unexpected"] = sorted(actual - expected)
    return result
