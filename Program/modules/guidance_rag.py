"""
Offline Technical Guidance Search Engine (RAG)
Indexes local PDF, Word, and TXT documents from the ICAI / Firm Guidance folder (e.g. ..\\Knowlege).
Performs rapid semantic and keyword matching 100% offline without external services.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Dict, List, Optional
import docx
import pymupdf
from rapidfuzz import fuzz

@dataclass
class GuidanceMatch:
    doc_name: str
    page_or_section: str
    snippet: str
    relevance_score: float  # 0 to 100


class GuidanceSearchEngine:
    def __init__(self, guidance_dir: str):
        self.guidance_dir = Path(guidance_dir)
        self.chunks: List[Dict] = []
        self.is_indexed: bool = False

    def build_index(self, max_pages_per_doc: int = 150) -> int:
        """
        Parses all PDFs, DOCX, and TXT files in the guidance directory.
        Returns total number of searchable chunks indexed.
        """
        self.chunks.clear()
        if not self.guidance_dir.exists() or not self.guidance_dir.is_dir():
            return 0

        for file_path in self.guidance_dir.iterdir():
            if file_path.name.startswith("~$") or file_path.name.startswith("."):
                continue

            ext = file_path.suffix.lower()
            if ext == ".pdf":
                self._index_pdf(file_path, max_pages=max_pages_per_doc)
            elif ext == ".docx":
                self._index_docx(file_path)
            elif ext in [".txt", ".md"]:
                self._index_txt(file_path)

        self.is_indexed = True
        return len(self.chunks)

    def _index_pdf(self, path: Path, max_pages: int):
        try:
            doc = pymupdf.open(str(path))
            limit = min(len(doc), max_pages)
            for idx in range(limit):
                page_num = idx + 1
                text = doc[idx].get_text("text").strip()
                if not text:
                    continue
                # Split page text into multi-sentence paragraphs
                paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 60]
                for p in paras:
                    self.chunks.append({
                        "doc_name": path.name,
                        "location": f"Page {page_num}",
                        "text": p
                    })
            doc.close()
        except Exception:
            pass

    def _index_docx(self, path: Path):
        try:
            d = docx.Document(str(path))
            for i, p in enumerate(d.paragraphs):
                txt = p.text.strip()
                if len(txt) > 60:
                    self.chunks.append({
                        "doc_name": path.name,
                        "location": f"Paragraph {i + 1}",
                        "text": txt
                    })
        except Exception:
            pass

    def _index_txt(self, path: Path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            paras = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 60]
            for i, p in enumerate(paras):
                self.chunks.append({
                    "doc_name": path.name,
                    "location": f"Section {i + 1}",
                    "text": p
                })
        except Exception:
            pass

    def search(self, query: str, top_k: int = 5) -> List[GuidanceMatch]:
        """
        Searches indexed paragraphs using token set fuzzy and substring scoring.
        """
        if not self.chunks:
            self.build_index()

        if not self.chunks or not query.strip():
            return []

        clean_query = query.lower().strip()
        query_words = set(re.findall(r'\w+', clean_query))
        results = []

        for item in self.chunks:
            txt_lower = item["text"].lower()
            
            # 1. Fuzzy token score
            fuzzy_score = fuzz.token_set_ratio(clean_query, txt_lower)

            # 2. Keyword overlap bonus
            match_count = sum(1 for w in query_words if w in txt_lower)
            overlap_pct = (match_count / max(1, len(query_words))) * 100

            # Combined score
            final_score = (fuzzy_score * 0.6) + (overlap_pct * 0.4)

            # Exact phrase bonus
            if clean_query in txt_lower:
                final_score = min(100.0, final_score + 25.0)

            if final_score >= 45.0:
                results.append(GuidanceMatch(
                    doc_name=item["doc_name"],
                    page_or_section=item["location"],
                    snippet=item["text"][:380] + ("..." if len(item["text"]) > 380 else ""),
                    relevance_score=round(final_score, 1)
                ))

        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]
