"""Offline question retrieval over supported topics, with answers drawn from the model."""
from collections import Counter
from math import log, sqrt
import re

from excel_report import layout
from xlsxwriter.utility import xl_col_to_name


QUESTIONS = {
    "low": ("When is cash lowest?", "Which month has a funding shortfall or negative cash balance?",
            "What is the peak funding gap or deficit in the forecast?"),
    "actual": ("What is the actual closing cash?", "How much cash do we have at the reporting cutoff?",
               "What is the reconciled balance today?"),
    "drivers": ("Which payments drive the low point?", "What are the largest outflows in the weakest month?",
                "What expenses caused the cash shortfall?"),
    "receipts": ("Which collections are expected in the low period?", "What project receipts support the lowest month?",
                 "Which customers or projects are paying us at the low point?"),
    "exclusions": ("Which cheques or payments were excluded?", "Which security and replaced cheques were removed?",
                   "Why was a deferred creditor or cheque omitted?"),
}
STOP_WORDS = set("a an the is are which what and do we in or at were was us has of how to for on much".split())


def tokens(text):
    return [w for w in re.findall("[a-z0-9]+", text.lower()) if w not in STOP_WORDS]


def topic(question):
    docs = [(key, Counter(tokens(text))) for key, examples in QUESTIONS.items() for text in examples]
    freq = Counter(word for _, words in docs for word in words)
    def vector(counts):
        return {w: n * (1 + log((1 + len(docs)) / (1 + freq[w]))) for w,n in counts.items()}
    def norm(v):
        return sqrt(sum(n*n for n in v.values())) or 1
    query = vector(Counter(tokens(question)))
    scores = {}
    for key, words in docs:
        sample = vector(words)
        similarity = sum(n * sample.get(w, 0) for w,n in query.items()) / (norm(query) * norm(sample))
        scores[key] = max(similarity, scores.get(key, 0))
    ranked = sorted(scores, key=scores.get, reverse=True)
    return ranked[0] if scores[ranked[0]] >= 0.29 and scores[ranked[0]] - scores[ranked[1]] >= 0.035 else None


def answer(model, question):
    key = topic(question)
    if not key:
        return "I could not match that question to a supported topic. Choose a sample question above."
    low = min((model.forecast(m) for m in model.months), key=model.closing.get)
    if key in ("low", "actual"):
        period = low if key == "low" else model.actual
        number = model.closing[period]
        col = xl_col_to_name(model.periods.index(period)+1)
        row = layout().index("Closing cash")+5
        label = "Lowest projected closing cash" if key == "low" else "Actual closing cash"
        return f"{label}: OMR {number:,.3f} ({period}).\n\nWorkbook evidence: Cash flow!{col}{row}."
    records = list(enumerate(model.entries, 5))
    if key == "exclusions":
        records = [(r,e) for r,e in records if e.reason]
        heading = "Entries excluded from cash totals"
    else:
        records = [(r,e) for r,e in records if e.period == low and not e.reason]
        if key == "drivers":
            records = sorted(((r,e) for r,e in records if e.value < 0), key=lambda pair: pair[1].value)[:3]
            heading = f"Largest payments and funding outflows in {low}"
        else:
            records = [(r,e) for r,e in records if e.category in ("Collections","Retention") and e.value > 0]
            heading = f"Planned project collections and retention receipts in {low}"
    lines = [heading, ""]
    for row, entry in records:
        name = entry.party or entry.project or entry.category
        lines += [f"{name}  ·  {entry.category}  ·  OMR {entry.value:,.3f}",
                  f"{entry.reference}  |  {entry.reason or entry.basis}",
                  f"Cash entries!H{row}  |  {entry.evidence}", ""]
    if not records:
        lines.append("No matching entries.")
    return "\n".join(lines)
