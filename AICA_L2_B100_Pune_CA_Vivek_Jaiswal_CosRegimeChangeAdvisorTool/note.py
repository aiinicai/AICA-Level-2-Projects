"""
note.py - Draft advisory note from the engine's results.

Two ways:
  - template_note(): plain rule-based text, works with no API key
  - ai_note():       an LLM writes a fuller note from the same numbers only
Both export to Word with to_docx(). The CA reviews before anything goes to the client.
"""
import io
import os

from docx import Document
from dotenv import load_dotenv

load_dotenv()
MODEL = os.getenv("REGIMEWISE_MODEL", "claude-sonnet-5-5")


def _rs(x) -> str:
    return f"Rs {x / 1e7:,.2f} crore"


def template_note(summary, detail, discount_pct: float) -> str:
    lines = ["FACTS",
             f"The group has {len(summary)} companies. Five-year projections were analysed under the normal "
             f"regime and the concessional regime under Section 200 (old 115BAA), discounting future tax at {discount_pct:.0f}% a year.",
             "", "ISSUE",
             "Whether, and from which year, each company should opt for the concessional regime under Section 200 of the "
             "Income-tax Act, 2025 (section 115BAA of the Income-tax Act, 1961).",
             "", "ANALYSIS"]
    for r in summary.to_dict("records"):
        sched = detail[r["Entity"]]["schedule"]
        switch_notes = [n.replace("Opts for Section 200 (old 115BAA); ", "On opting, ") for n in sched["Note"] if n and n != "Opts for Section 200 (old 115BAA)"]
        lines.append(f"{r['Entity']}: best option is '{r['Best option']}', present value of tax "
                     f"{_rs(r['PV of tax - best'])} against {_rs(r['PV of tax - stay normal'])} if it stays normal "
                     f"(saving {_rs(r['PV saving'])}). Runner-up '{r['Runner-up']}' is "
                     f"{_rs(r['Margin over runner-up'])} behind." + (f" {switch_notes[0]}." if switch_notes else ""))
    total = summary["PV saving"].sum()
    lines += ["", "CONCLUSION",
              f"Following the best option for each company reduces the group's present value of tax by {_rs(total)}.",
              "", "POINTS TO VERIFY",
              "Rates and thresholds used; accuracy of the projections; any loss or MAT credit nearing expiry; "
              "the option, once exercised, cannot be withdrawn, so a close margin over the runner-up deserves caution."]
    return "\n".join(lines)


PROMPT = """You are drafting a first-cut tax advisory note for a Chartered Accountant in India,
on whether each company in a group should opt for the concessional corporate tax regime under Section 200 of the
Income-tax Act, 2025, which corresponds to section 115BAA of the Income-tax Act, 1961.

Discount rate used: {discount}%.

GROUP SUMMARY (present value of tax over the projection years, Rs):
{summary}

YEAR-BY-YEAR SCHEDULE FOR EACH COMPANY'S BEST OPTION:
{schedules}

ALL OPTIONS PER COMPANY:
{options}

Write the note under these headings exactly: FACTS, ISSUE, ANALYSIS, RECOMMENDATION, POINTS TO VERIFY.
Rules:
- Use ONLY the figures above. Do not invent numbers, sections, rates or case law.
- Express large amounts in crore.
- For each company, explain why the best option wins (MAT credit, losses, rate difference, timing).
- Where the best option beats the runner-up by a small margin, say the choice is sensitive to the projections.
- Refer to the provision as "Section 200 (old 115BAA)" so readers familiar with either Act can follow.
- State that the option, once exercised, cannot be withdrawn.
- End POINTS TO VERIFY with: rates and thresholds against the current law, and the reliability of the projections.
"""


def ai_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def ai_note(summary, detail, discount_pct: float) -> str:
    from anthropic import Anthropic
    schedules = "\n\n".join(f"{k}:\n{v['schedule'].to_string(index=False)}" for k, v in detail.items())
    opts = "\n\n".join(f"{k}:\n{v['options'].to_string(index=False)}" for k, v in detail.items())
    prompt = PROMPT.format(discount=discount_pct, summary=summary.to_string(index=False),
                           schedules=schedules, options=opts)
    msg = Anthropic().messages.create(model=MODEL, max_tokens=2500, temperature=0,
                                      messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text


def to_docx(text: str, title: str = "Draft note: opting for Section 200 (old 115BAA)") -> bytes:
    doc = Document()
    doc.add_heading(title, level=1)
    doc.add_paragraph().add_run(
        "DRAFT - prepared with analytical tools - subject to review by a Chartered Accountant.").italic = True
    heads = {"FACTS", "ISSUE", "ANALYSIS", "RECOMMENDATION", "CONCLUSION", "POINTS TO VERIFY"}
    for line in text.splitlines():
        clean = line.strip().strip("#*: ").upper()
        if clean in heads:
            doc.add_heading(clean.title(), level=2)
        elif line.strip():
            doc.add_paragraph(line.strip().lstrip("-* ").strip())
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
