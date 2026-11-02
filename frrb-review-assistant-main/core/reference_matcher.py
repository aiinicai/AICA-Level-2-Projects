"""Compares new observations with a reference / previously identified observations sheet.

The reviewer can upload earlier observations (an earlier review points sheet, a TR report, the auditor's
or management's list). Each new observation is then tagged "Previously identified (Ref n)" or "New",
so genuinely new, evidence-based matters stand out.
"""

import io
import re
from typing import Any, Dict, List

STOP = set("""the and for with that this from have has are was were been which shall should not into under than such their
there these those other also only any all its per each note notes company financial statements statement year disclosed
disclosure disclosures required requirement amount amounts reported presented para paragraph schedule companies act""".split())
STD = re.compile(r"\b(?:ind\s?as|as)\s?\d{1,3}\b|\bschedule\s+iii\b|\bcaro\b|\bsection\s+\d+\w*|\bsa\s?\d{3}\b|\bmsmed\b|\blodr\b", re.I)


def _keywords(text: str) -> set:
    return {w for w in re.findall(r"[a-z][a-z\-]{3,}", text.lower()) if w not in STOP}


def _standards(text: str) -> set:
    return {re.sub(r"\s+", "", m.lower()) for m in STD.findall(text)}


class ReferenceMatcher:

    @staticmethod
    def extract(data: bytes, filename: str) -> List[str]:
        name = filename.lower()
        items: List[str] = []
        if name.endswith((".xlsx", ".xlsm")):
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    # the observation itself sits in the first descriptive columns; later columns hold long requirement text
                    texts = [str(v) for v in row if isinstance(v, str) and len(v) > 25][:3]
                    if texts:
                        items.append(" | ".join(texts)[:1500])
        elif name.endswith(".pdf"):
            import pymupdf
            doc = pymupdf.open(stream=data, filetype="pdf")
            text = "\n".join(p.get_text() for p in doc)
            title = r"(?<!Other )(?<!Sub )\bTitle\s*:"
            parts = re.split(rf"(?={title})", text) if re.search(title, text) else re.split(r"\n\s*\n", text)
            items = [re.sub(r"\s+", " ", p).strip()[:1200] for p in parts if len(p.strip()) > 80]
        elif name.endswith(".docx"):
            import docx
            d = docx.Document(io.BytesIO(data))
            items = [p.text for p in d.paragraphs if len(p.text) > 60]
            for t in d.tables:
                for r in t.rows:
                    cells = [c.text for c in r.cells if len(c.text) > 25]
                    if cells:
                        items.append(" | ".join(dict.fromkeys(cells))[:1500])
        return items

    @staticmethod
    def tag(findings: List[Dict[str, Any]], references: List[str]) -> None:
        # header / title rows of a sheet are not observations
        references = [r for r in references if not re.search(r"^(issue id|s\.?\s*no|entity:|financial reporting review)", r.strip(), re.I)]
        refs = [(i, r, _keywords(r), _standards(r)) for i, r in enumerate(references, start=1)]
        for f in findings:
            topic = _keywords(f"{f.get('sub_title', '')} {f.get('title', '')}")
            text = f"{f.get('title', '')} {f.get('sub_title', '')} {f.get('view', '')}"
            kw, st = _keywords(text), _standards(text)
            best, best_score = None, 0.0
            need = max(1, -(-len(topic) * 6 // 10))       # at least 60% of the topic words
            for i, r, rkw, rst in refs:
                if not rkw or len(topic & rkw) < need:     # the reference must be about the same topic
                    continue
                shared = kw & rkw
                if len(shared) < 5:
                    continue
                score = len(shared) / max(1, len(kw)) + (0.1 if st & rst else 0)
                if score > best_score:
                    best, best_score = (i, r), score
            f.pop("reference_text", None)
            if best and best_score >= 0.3:
                f["reference_status"] = f"Previously identified (Ref {best[0]})"
                f["reference_text"] = best[1][:300]
            else:
                f["reference_status"] = "New"
