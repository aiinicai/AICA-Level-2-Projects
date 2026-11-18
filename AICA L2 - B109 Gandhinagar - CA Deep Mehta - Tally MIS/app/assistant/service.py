"""The assistant: decides what a question is about, hands the model finished figures, and checks the reply."""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from ..engine import reports as R
from . import facts as F
from . import lmstudio as L

GENERAL_LABEL = "General knowledge — not from your company data"
REFUSAL = ("I answer questions about the open company's figures only. Ask about revenue, profit, expenses, receivables, "
           "payables or cash for the period on screen — or turn on “Allow general questions” in Settings.")

SYSTEM_COMPANY = (
    "You are the assistant inside an accounting dashboard. You explain figures that the app has already calculated.\n"
    "Rules:\n"
    "1. Use ONLY the FACTS provided. Never calculate, add, subtract, convert, round or estimate numbers yourself.\n"
    "2. Copy every number exactly as written in the FACTS, including the ₹ sign and the commas.\n"
    "3. If the FACTS do not contain what is asked, reply exactly: I don't have that in the open company's data.\n"
    "4. Be brief: at most 6 short sentences, plain English, no markdown tables.\n"
    "5. Say when a figure is marked ESTIMATED or not available.\n"
    "6. For \"who\" or \"which\" questions, name the top items from the FACTS together with their amounts, largest first."
)
SYSTEM_GENERAL = "You are a helpful assistant. Answer briefly and clearly. You know nothing about the user's own company or its figures."
SYSTEM_CLASSIFY = ("Decide if the question is about a company's own accounts, figures, customers, suppliers, expenses, sales, profit, cash, "
                   "receivables, payables, stock or this dashboard. Reply with exactly one word: YES or NO.")

_COMPANY_WORDS = re.compile(
    r"revenue|sales|turnover|profit|loss|margin|ebitda|expense|cost|cogs|purchase|cash|bank|receivable|payable|owe|owes|debtor|creditor|"
    r"customer|supplier|vendor|ledger|voucher|invoice|bill|stock|inventory|tax|gst|balance|working capital|ratio|kpi|overdue|ageing|aging|"
    r"quarter|this year|last year|this month|period|compare|growth|dashboard|company|figures?|numbers?|salary|salaries|rent|interest|depreciation|business|product|biggest|largest|healthy|position|owed|owing|performance|"
    r"\b(?:doing|item|items|best|late|due|sell|sells|sold|earn|spend|spent|money|worth)\b", re.I)


@dataclass
class Prefs:
    allowGeneral: bool = False
    model: str = L.DEFAULT_MODEL
    baseUrl: str = L.DEFAULT_URL


def _prefs_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "TallyMIS" / "settings.json"


class Assistant:
    """Preferences (kept on this PC, not company data) plus the chat logic. `client` can be replaced in tests."""

    def __init__(self, client: httpx.Client | None = None, persist: bool = True):
        self.client, self.persist = client, persist
        self.prefs = Prefs()
        if persist:
            try:
                data = json.loads(_prefs_path().read_text(encoding="utf-8"))
                self.prefs = Prefs(**{k: v for k, v in data.items() if k in Prefs.__dataclass_fields__})
            except (OSError, ValueError, TypeError):
                pass

    def update(self, patch: dict) -> Prefs:
        if "baseUrl" in patch:
            patch["baseUrl"] = L.check_local(str(patch["baseUrl"]))
        if "model" in patch and not str(patch["model"]).strip():
            raise L.AssistantError("The model name cannot be empty.")
        for k, v in patch.items():
            if k in Prefs.__dataclass_fields__:
                setattr(self.prefs, k, bool(v) if k == "allowGeneral" else str(v).strip())
        if self.persist:
            try:
                p = _prefs_path()
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(asdict(self.prefs)), encoding="utf-8")
            except OSError:
                pass
        return self.prefs

    def settings(self) -> dict:
        s = L.status(self.prefs.baseUrl, self.prefs.model, self.client)
        return {**asdict(self.prefs), "online": s.online, "modelLoaded": s.model_loaded, "message": s.message}

    # ------------------------------------------------------------------ chat
    def _is_company_question(self, question: str, f: R.Filters | None) -> bool:
        if _COMPANY_WORDS.search(question):
            return True
        q = question.lower()
        if f and any(len(e.name) >= 4 and e.name.lower() in q for e in f.ctx.chart.entries.values()):
            return True
        try:
            r = L.chat(self.prefs.baseUrl, self.prefs.model, [{"role": "system", "content": SYSTEM_CLASSIFY}, {"role": "user", "content": question}],
                       max_tokens=3, client=self.client)
            return r.strip().upper().startswith("YES")
        except L.AssistantError:
            raise

    def chat(self, question: str, f: R.Filters | None) -> dict:
        question = question.strip()[:400]
        t0 = time.perf_counter()
        base = {"answer": "", "kind": "company", "label": None, "facts": None, "unmatched": [], "model": self.prefs.model}
        try:
            about_company = f is not None and self._is_company_question(question, f)
            if not about_company and not self.prefs.allowGeneral:
                return {**base, "kind": "refused", "answer": REFUSAL}
            if not about_company:
                ans = L.chat(self.prefs.baseUrl, self.prefs.model, [{"role": "system", "content": SYSTEM_GENERAL}, {"role": "user", "content": question}],
                             client=self.client)
                return {**base, "kind": "general", "label": GENERAL_LABEL, "answer": ans}
            facts = F.build_facts(f, question)
            user = "FACTS:\n" + "\n".join(f"- {x}" for x in facts) + f"\n\nQUESTION: {question}"
            ans = L.chat(self.prefs.baseUrl, self.prefs.model, [{"role": "system", "content": SYSTEM_COMPANY}, {"role": "user", "content": user}],
                         client=self.client)
            bad = F.unmatched_numbers(ans, facts, question)
            if bad:
                return {**base, "kind": "warning", "facts": facts, "unmatched": bad, "label": "Reply withheld",
                        "answer": ("The assistant's reply contained numbers that are not among the figures the app calculated, so it is not shown. "
                                   "The figures it was given are listed below — please read them there, or ask again in other words.")}
            return {**base, "answer": ans or "I don't have that in the open company's data.", "facts": facts,
                    "label": "From your company data"}
        except L.AssistantError as e:
            return {**base, "kind": "offline", "label": "Assistant unavailable", "answer": str(e)}
        finally:
            base["ms"] = round((time.perf_counter() - t0) * 1000)
