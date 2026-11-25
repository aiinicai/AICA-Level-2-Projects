"""Module 3 — rule-based document classification and keyword indexing.

Classification is a suggestion with a confidence score; the user confirms or
overrides it. No AI is used here, so nothing leaves the machine."""
from __future__ import annotations

import re
from collections import Counter

DOC_TYPES = {
    "NOTICE": ["notice", "under section", "income tax officer", "assessing officer", "din", "compliance",
               "143(2)", "142(1)", "148", "148a", "scrutiny", "you are requested", "faceless", "national faceless",
               "e-proceeding", "show cause", "assessment unit"],
    "BANK_STATEMENT": ["statement of account", "opening balance", "closing balance", "withdrawal", "deposit",
                       "ifsc", "branch", "cheque", "neft", "rtgs", "upi", "imps", "value date"],
    "BANK_BOOK": ["bank book", "bank a/c", "bank account ledger", "voucher", "particulars", "dr", "cr"],
    "CASH_BOOK": ["cash book", "cash in hand", "cash a/c", "cash account", "cash sales", "cash deposited"],
    "SALES_LEDGER": ["sales ledger", "sales register", "sales a/c", "invoice no", "sales account"],
    "DEBTOR_LEDGER": ["debtor", "sundry debtors", "receivable", "customer ledger", "collection"],
    "CAPITAL_ACCOUNT": ["capital account", "partner", "capital introduced", "drawings", "partners' capital"],
    "FINANCIAL_STATEMENTS": ["balance sheet", "profit and loss", "profit & loss", "trading account", "schedule",
                             "reserves and surplus", "notes to accounts"],
    "ITR": ["itr-", "acknowledgement", "return of income", "itr v", "e-filing", "gross total income"],
    "FORM_26AS_AIS": ["26as", "annual information statement", "ais", "tis", "taxpayer information summary",
                      "tds deducted", "sft"],
    "CONFIRMATION": ["confirmation", "confirm that", "we hereby confirm", "balance confirmation", "loan confirmation"],
    "INVOICE": ["tax invoice", "invoice", "gstin", "hsn", "bill no", "cgst", "sgst", "igst"],
    "AGREEMENT": ["agreement", "deed", "witnesseth", "hereinafter", "terms and conditions"],
    "GST_RETURN": ["gstr-1", "gstr-3b", "gstr 3b", "gstr-9", "outward supplies"],
}

_WORD = re.compile(r"[a-z0-9()\-/]{3,}")
_STOP = set("the and for with that this from are was were have has had not but all any you your our their which shall will "
            "been being into upon such than then there here also per its may can under".split())


def classify(text: str, filename: str = "") -> tuple[str, float, dict[str, int]]:
    hay = f"{filename.lower()} \n {text[:20000].lower()}"
    scores: dict[str, int] = {}
    for t, kws in DOC_TYPES.items():
        s = 0
        for kw in kws:
            c = hay.count(kw)
            if c:
                s += min(c, 5) * (3 if " " in kw else 1)
        # filename hints weigh more
        if t.lower().replace("_", " ") in filename.lower().replace("_", " "):
            s += 15
        scores[t] = s
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] < 3:
        return "UNCLASSIFIED", 0.0, scores
    return best, round(scores[best] / total, 2) if total else 0.0, scores


def index_terms(text: str, top: int = 400) -> list[tuple[str, int]]:
    words = [w for w in _WORD.findall(text.lower()) if w not in _STOP and not w.isdigit()]
    return Counter(words).most_common(top)
