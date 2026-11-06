"""AI drafting layer.

Turns the structured findings into auditor-quality prose: audit report
observations, a management letter, member reminder letters, minutes summaries
and a tax note. Uses the Anthropic SDK (Claude) when credentials are present
and `--ai` is passed; otherwise deterministic templates produce the same
documents so the tool always runs.

Guardrails applied to every model call
1. The model only sees a JSON context assembled by the deterministic modules;
   it is told to use no number or legal reference that is not in that context.
2. Every statutory citation in the output (s.xx, bye-law xx, Rule xx, Circular)
   is checked against the context; anything unverified is flagged in the text.
3. Member names, mobiles and PANs are never sent - only flat numbers and amounts.
4. All prompts and responses are logged to output/ai_prompt_log.md for review.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date

from .config import FIRM, SOCIETY, FY_LABEL
from .findings import Finding, inr

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT_TEMPLATE = """You are the audit manager working for {signatory}, Chartered Accountant ({website}), drafting documents for the statutory audit of a co-operative housing society under the Maharashtra Co-operative Societies Act, 1960.

Rules you must follow:
1. Use only the facts, amounts, dates and legal references supplied in the JSON context. Do not add any section number, bye-law number, circular, case law or figure that is not in the context. If a reference is needed but not supplied, write "[reference to be confirmed]".
2. Write in formal Indian audit English. Amounts in Indian format with "Rs" (e.g. Rs 1,45,000).
3. Never speculate about intent or allege fraud; describe the control failure and its effect.
4. Do not include personal data beyond flat numbers.
5. Return plain text (no markdown headings) unless the task says otherwise.
6. Letters and notes are signed by {signatory}; never sign as a firm or leave a placeholder name."""


def system_prompt() -> str:
    """System prompt with the firm's current name (editable in the app, so read at call time)."""
    return SYSTEM_PROMPT_TEMPLATE.format(signatory=FIRM.auditor, website=FIRM.website)


SYSTEM_PROMPT = system_prompt()   # snapshot for docs and tests

# Citation verification: references in the drafted text are normalised to keys (e.g. "section 138" and
# "s.138" both become s:138; "ss.75, 79" yields s:75 and s:79; "bye-laws 142-143" yields b:142 and b:143)
# and must appear, in some form, in the context the model was given.
_NUM = r"\d+[A-Za-z]{0,3}(?:\([^)\s]{1,6}\))*"
_LIST = r"(" + _NUM + r"(?:\s*(?:,|and|&|/|to|-|\u2013)\s*" + _NUM + r")*)"
_REF_FAMILIES = [
    ("s", re.compile(r"(?<![A-Za-z])(?:sections?|secs?\.?|ss?\.)\s*" + _LIST, re.I), "section"),
    ("b", re.compile(r"bye-?\s?laws?\s*(?:no\.?\s*)?" + _LIST, re.I), "bye-law"),
    ("r", re.compile(r"\brules?\s*" + _LIST, re.I), "rule"),
]
_TEXT_REFS_RE = re.compile(r"(?:circular|notification)\s?(?:no\.?\s?)?([\w/-]+(?:\.\w+)*)", re.I)
_NUM_RE = re.compile(_NUM)
_RANGE_RE = re.compile(r"^(\d+)\s*(?:-|\u2013|to)\s*(\d+)$")


def _ref_keys(text: str) -> dict[str, str]:
    """Map normalised reference key -> human-readable label for every statutory reference in text."""
    keys: dict[str, str] = {}
    for fam, rx, label in _REF_FAMILIES:
        for m in rx.finditer(text):
            blob = m.group(1)
            for rng in re.finditer(r"(\d+)\s*(?:-|\u2013|to)\s*(\d+)", blob):
                a, b = int(rng.group(1)), int(rng.group(2))
                if a < b <= a + 20:
                    for n in range(a, b + 1):
                        keys[f"{fam}:{n}"] = f"{label} {n}"
            for num in _NUM_RE.findall(blob):
                full = num.lower().replace(" ", "")
                base = re.match(r"\d+[A-Za-z]{0,3}", num).group(0).lower()
                keys[f"{fam}:{full}"] = f"{label} {num}"
                keys.setdefault(f"{fam}:{base}", f"{label} {base.upper()}")
    for m in _TEXT_REFS_RE.finditer(text):
        ident = m.group(1).rstrip(".,;:").lower()
        if re.search(r"\d", ident):
            keys["t:" + ident] = m.group(0).rstrip(".,;:")
    return keys


@dataclass
class LogEntry:
    task: str
    source: str            # "claude" or "template"
    prompt: str
    response: str
    unverified_citations: list[str] = field(default_factory=list)


class AIWriter:
    def __init__(self, enabled: bool = False, model: str = MODEL, api_key: str | None = None):
        self.model = model
        self.client = None
        self.log: list[LogEntry] = []
        self.enabled = False
        self.last_error: str | None = None
        if enabled:
            try:
                import anthropic  # noqa: F401
                self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
                self.enabled = True
            except Exception as exc:  # SDK missing or no credentials
                self.log.append(LogEntry("init", "template", "", f"AI disabled: {exc}"))

    # ------------------------------------------------------------------ core
    def _ask(self, task: str, instruction: str, context: dict, max_tokens: int = 6000) -> str | None:
        prompt = instruction + "\n\nCONTEXT (JSON):\n" + json.dumps(context, indent=1, default=str)
        if not self.enabled:
            return None
        try:
            with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt(),
                messages=[{"role": "user", "content": prompt}],
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                msg = stream.get_final_message()
            if msg.stop_reason == "refusal":
                self.log.append(LogEntry(task, "claude", prompt, "Model declined the request; template used."))
                return None
            text = "".join(b.text for b in msg.content if b.type == "text").strip()
            unverified = self._check_citations(text, prompt)
            if unverified:
                text += "\n\n[Reviewer note: the following references were not in the source data and must be verified: " + ", ".join(sorted(set(unverified))) + "]"
            self.log.append(LogEntry(task, "claude", prompt, text, unverified))
            return text
        except Exception as exc:
            self.last_error = str(exc)
            self.log.append(LogEntry(task, "template", prompt, f"API error, template used: {exc}"))
            if "authentication" in str(exc).lower() or "api_key" in str(exc).lower():
                self.enabled = False   # no point retrying every task without credentials
            return None

    # ------------------------------------------------------------------ streaming (used by the app)
    def stream_task(self, task: str, instruction: str, context: dict, max_tokens: int = 6000):
        """Yield text chunks for the UI; the citation check runs on the full text and is yielded last."""
        prompt = instruction + "\n\nCONTEXT (JSON):\n" + json.dumps(context, indent=1, default=str)
        if not self.enabled:
            raise RuntimeError("AI is not enabled - enter an API key in Settings")
        chunks: list[str] = []
        with self.client.beta.messages.stream(
            model=self.model, max_tokens=max_tokens, system=system_prompt(),
            messages=[{"role": "user", "content": prompt}],
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
                yield text
            msg = stream.get_final_message()
        full = "".join(chunks).strip()
        if msg.stop_reason == "refusal":
            self.log.append(LogEntry(task, "claude", prompt, "Model declined the request."))
            yield "\n\n[The model declined this request.]"
            return
        unverified = self._check_citations(full, prompt)
        if unverified:
            note = "\n\n[Reviewer note: the following references were not in the source data and must be verified: " + ", ".join(sorted(set(unverified))) + "]"
            yield note
            full += note
        self.log.append(LogEntry(task, "claude", prompt, full, unverified))

    def chat_stream(self, question: str, history: list[dict], context: dict, max_tokens: int = 4000):
        """Grounded Q&A over the audit results. History is a list of {role, content} dicts."""
        if not self.enabled:
            raise RuntimeError("AI is not enabled - enter an API key in Settings")
        system = (system_prompt() + "\n\nYou are now answering questions from the engagement partner about this audit. Answer from the AUDIT CONTEXT only; "
                  "if the context does not contain the answer, say so and name the schedule the partner should check. Keep answers concise and cite the observation id (e.g. OBS-03) where relevant.\n\n"
                  "AUDIT CONTEXT (JSON):\n" + json.dumps(context, default=str))
        messages = history + [{"role": "user", "content": question}]
        chunks: list[str] = []
        with self.client.beta.messages.stream(
            model=self.model, max_tokens=max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
                yield text
            msg = stream.get_final_message()
        full = "".join(chunks)
        if msg.stop_reason == "refusal":
            yield "\n\n[The model declined this request.]"
        self.log.append(LogEntry("chat", "claude", question, full, self._check_citations(full, system)))

    # task definitions reused by the app so the CLI and UI send identical prompts
    def task_spec(self, kind: str, **kw) -> tuple[str, dict, int]:
        if kind == "observations":
            findings = kw["findings"]
            return ("Draft the 'Audit Observations and Rectification Required' section of the statutory audit report. "
                    "For each finding write one numbered paragraph with: heading, observation (facts and amount), "
                    "the provision contravened (only from the context), effect, and the rectification required by the committee. "
                    "Order: High severity first. End with a paragraph on the overall state of internal control.",
                    {"society": SOCIETY.name, "financial_year": FY_LABEL, "findings": [f.as_dict() for f in findings]}, 12000)
        if kind == "management_letter":
            findings = kw["findings"]
            return ("Draft a management letter to the Chairman and Managing Committee summarising the control weaknesses and the actions required, "
                    "grouped under: Member dues and billing; Funds and investments; Expenditure controls; Statutory compliance; Taxation. "
                    "Close with a request for a written response within 30 days. Formal letter format, under 600 words.",
                    {"society": SOCIETY.name, "financial_year": FY_LABEL, "date": kw["as_of"],
                     "findings": [{"id": f.id, "area": f.area, "severity": f.severity, "recommendation": f.recommendation, "amount": f.amount} for f in findings]}, 6000)
        if kind == "reminder":
            row = kw["row"]
            return ("Draft a firm but courteous final reminder letter from the Hon. Secretary to the member of this flat for unpaid maintenance dues. "
                    "State the amount, the months of arrears, the interest being charged, the 15-day deadline and the consequence under the recovery provision. Under 200 words.",
                    {"society": SOCIETY.name, "flat_no": row.flat_no, "closing_balance": round(float(row.closing_balance), 2),
                     "months_of_arrears": float(row.months_of_arrears), "date": kw["as_of"], "interest_rate": "21% p.a. simple interest (bye-law 72)",
                     "recovery_provision": "MCS Act 1960 s.101 (recovery as arrears of land revenue)", "payment_deadline_days": 15}, 1500)
        if kind == "governance":
            m, a = kw["meetings"], kw["actions"]
            return ("Write a one-page governance summary for the auditor's file: meetings held, notice and quorum exceptions, "
                    "action items not complied with, and three recommendations on governance process. Use short paragraphs.",
                    {"meetings": m.to_dict(orient="records"), "open_actions": a[~a.status.str.startswith("Complied")].to_dict(orient="records")}, 6000)
        if kind == "tax_note":
            return ("Write a short tax position note (under 250 words) for the committee explaining the computation, the regime choice and the advance tax default.",
                    {"society": SOCIETY.name, "assessment_year": "AY 2026-27", **kw["summary"],
                     "provisions": ["s.80P(2)(d) interest from co-operative bank", "s.115BAD optional 22% regime without 80P", "s.24(a) 30% standard deduction on rent",
                                    "s.234B and s.234C interest on advance tax default", "principle of mutuality for member receipts"]}, 2000)
        if kind == "minutes":
            return ("Analyse these meeting minutes for the audit file. List: (1) decisions with financial effect and amounts, (2) any notice-period or quorum concern, "
                    "(3) action items with owner and due date, (4) matters the auditor should verify against the books. Use short headed sections.",
                    {"file": kw["name"], "minutes_text": kw["text"], "parsed": kw.get("parsed", {})}, 3000)
        raise ValueError(kind)

    @staticmethod
    def _check_citations(text: str, context: str) -> list[str]:
        """Return the references cited in text that cannot be matched to the context."""
        have = _ref_keys(context)
        ctx_flat = re.sub(r"\s+", "", context.lower())
        bad: list[str] = []
        for key, label in _ref_keys(text).items():
            fam, _, ident = key.partition(":")
            if key in have:
                continue
            if fam == "t":
                core = re.match(r"\d+(?:/\d+)*", ident)
                if core and core.group(0) in ctx_flat:
                    continue
            else:
                base = re.match(r"\d+[a-z]{0,3}", ident).group(0)
                if f"{fam}:{base}" in have:
                    continue
            bad.append(label)
        labels = set(bad)
        # "section 66" and "section 66(1)" come from the same citation: keep only the more specific form
        return sorted(l for l in labels if not any(o != l and o.startswith(l + "(") for o in labels))

    def _template(self, task: str, prompt_hint: str, text: str) -> str:
        self.log.append(LogEntry(task, "template", prompt_hint, text))
        return text

    # ------------------------------------------------------------------ tasks
    def audit_observations(self, findings: list[Finding]) -> str:
        ctx = {"society": SOCIETY.name, "financial_year": FY_LABEL, "findings": [f.as_dict() for f in findings]}
        instr = ("Draft the 'Audit Observations and Rectification Required' section of the statutory audit report. "
                 "For each finding write one numbered paragraph with: heading, observation (facts and amount), "
                 "the provision contravened (only from the context), effect, and the rectification required by the committee. "
                 "Order: High severity first. End with a paragraph on the overall state of internal control.")
        out = self._ask("audit_observations", instr, ctx, max_tokens=12000)
        if out:
            return out
        paras = [f"AUDIT OBSERVATIONS AND RECTIFICATION REQUIRED - {SOCIETY.name}, {FY_LABEL}", ""]
        for f in findings:
            paras.append(f"{f.id} {f.area} ({f.module}) - Severity: {f.severity}")
            paras.append(f"Observation: {f.observation}")
            paras.append(f"Provision: {f.reference}")
            if f.amount:
                paras.append(f"Financial effect: {inr(f.amount)}")
            paras.append(f"Rectification required: {f.recommendation}")
            paras.append("")
        high = sum(1 for f in findings if f.severity == "High")
        paras.append(f"Overall: {len(findings)} observations were raised of which {high} are high severity. The pattern of findings (interest waiver, "
                     "related-party payments, split invoices, fund diversion and missing reconciliations) indicates that the committee has not operated "
                     "basic financial controls during the year. The society is advised to adopt the recommendations above and report compliance in the audit rectification report (Form O).")
        return self._template("audit_observations", instr, "\n".join(paras))

    def management_letter(self, findings: list[Finding], as_of: date) -> str:
        ctx = {"society": SOCIETY.name, "financial_year": FY_LABEL, "date": as_of, "findings": [{"id": f.id, "area": f.area, "severity": f.severity, "recommendation": f.recommendation, "amount": f.amount} for f in findings]}
        instr = ("Draft a management letter to the Chairman and Managing Committee summarising the control weaknesses and the actions required, "
                 "grouped under: Member dues and billing; Funds and investments; Expenditure controls; Statutory compliance; Taxation. "
                 "Close with a request for a written response within 30 days. Formal letter format, under 600 words.")
        out = self._ask("management_letter", instr, ctx)
        if out:
            return out
        groups = {"Member dues and billing": ["Member Ledger", "GST", "Bank"], "Funds and investments": ["Funds"], "Expenditure controls": ["Expenses"],
                  "Statutory compliance and governance": ["Compliance", "Governance"], "Taxation": ["Tax - TDS", "Tax - Income tax"]}
        lines = [f"{as_of:%d %B %Y}", "", "To,", "The Chairman and Members of the Managing Committee", SOCIETY.name, SOCIETY.address, "",
                 f"Subject: Management letter - statutory audit for {FY_LABEL}", "", "Dear Sir/Madam,",
                 f"During the statutory audit of the society's accounts for {FY_LABEL} we noted the matters below. They do not form part of our audit report but require the committee's attention.", ""]
        for g, mods in groups.items():
            fs = [f for f in findings if f.module in mods]
            if not fs:
                continue
            lines.append(g.upper())
            for f in fs:
                amt = f" ({inr(f.amount)})" if f.amount else ""
                lines.append(f"- {f.id} {f.area}{amt}: {f.recommendation}")
            lines.append("")
        lines += ["We request a written response on each point within 30 days so that the audit rectification report can be prepared.", "",
                  "Yours faithfully,", *FIRM.signature_block()]
        return self._template("management_letter", instr, "\n".join(lines))

    def reminder_letter(self, row, as_of: date) -> str:
        ctx = {"society": SOCIETY.name, "flat_no": row.flat_no, "closing_balance": round(float(row.closing_balance), 2),
               "months_of_arrears": float(row.months_of_arrears), "date": as_of, "interest_rate": "21% p.a. simple interest (bye-law 72)",
               "recovery_provision": "MCS Act 1960 s.101 (recovery as arrears of land revenue)", "payment_deadline_days": 15}
        instr = ("Draft a firm but courteous final reminder letter from the Hon. Secretary to the member of this flat for unpaid maintenance dues. "
                 "State the amount, the months of arrears, the interest being charged, the 15-day deadline and the consequence under the recovery provision. Under 200 words.")
        out = self._ask(f"reminder_{row.flat_no}", instr, ctx, max_tokens=1500)
        if out:
            return out
        txt = (f"{as_of:%d %B %Y}\n\nTo,\nThe Member, Flat No. {row.flat_no}\n{SOCIETY.name}\n\nSubject: Final reminder - maintenance dues of {inr(row.closing_balance)}\n\n"
               f"Dear Member,\n\nOur records show that maintenance charges of {inr(row.closing_balance)}, representing about {row.months_of_arrears:.0f} months of dues, remain unpaid as on {as_of:%d-%m-%Y} despite earlier bills and reminders. "
               f"Interest at 21% p.a. simple interest continues to accrue on the outstanding amount under bye-law 72.\n\n"
               f"You are requested to clear the full amount within 15 days of this letter. If the dues remain unpaid, the Managing Committee will, as resolved, "
               f"initiate recovery proceedings under section 101 of the Maharashtra Co-operative Societies Act, 1960, and the costs of recovery will be added to your account.\n\n"
               f"If you have already paid or believe there is an error, please share the payment details with the society office so that the ledger can be corrected.\n\n"
               f"Yours faithfully,\nHon. Secretary\n{SOCIETY.name}")
        return self._template(f"reminder_{row.flat_no}", instr, txt)

    def minutes_summary(self, meetings_df, actions_df) -> str:
        ctx = {"meetings": meetings_df.to_dict(orient="records"), "open_actions": actions_df[~actions_df.status.str.startswith("Complied")].to_dict(orient="records")}
        instr = ("Write a one-page governance summary for the auditor's file: meetings held, notice and quorum exceptions, "
                 "action items not complied with, and three recommendations on governance process. Use short paragraphs.")
        out = self._ask("minutes_summary", instr, ctx)
        if out:
            return out
        bad = meetings_df[meetings_df.issues != ""]
        open_a = actions_df[~actions_df.status.str.startswith("Complied")]
        txt = [f"GOVERNANCE SUMMARY - {FY_LABEL}", "",
               f"{len(meetings_df)} meetings were held during the year ({int((meetings_df.type == 'MC').sum())} managing committee meetings and {int((meetings_df.type == 'AGM').sum())} annual general meeting). "
               f"{len(bad)} meetings had notice or quorum exceptions: " + "; ".join(f"{r.meeting_date:%d-%b-%Y} - {r.issues}" for r in bad.itertuples()) + ".", "",
               f"Of {len(actions_df)} recorded action items, {len(open_a)} were open or not complied at the audit date:"]
        txt += [f"- {r.action} (due {r.due_date:%d-%b-%Y}): {r.status}" for r in open_a.itertuples() if r.due_date]
        txt += ["", "Recommendations: (1) issue meeting notices through a register with proof of service and record quorum at the start of each meeting; "
                "(2) maintain an action tracker with owner and due date, reviewed as the first agenda item; (3) place every procurement above the committee limit before the General Body with three quotations, as the AGM itself resolved."]
        return self._template("minutes_summary", instr, "\n".join(txt))

    def tax_note(self, summary: dict) -> str:
        ctx = {"society": SOCIETY.name, "assessment_year": "AY 2026-27", **summary,
               "provisions": ["s.80P(2)(d) interest from co-operative bank", "s.115BAD optional 22% regime without 80P", "s.24(a) 30% standard deduction on rent", "s.234B and s.234C interest on advance tax default", "principle of mutuality for member receipts"]}
        instr = "Write a short tax position note (under 250 words) for the committee explaining the computation, the regime choice and the advance tax default."
        out = self._ask("tax_note", instr, ctx, max_tokens=2000)
        if out:
            return out
        txt = (f"TAX POSITION NOTE - AY 2026-27\n\nReceipts from members are not taxable on the principle of mutuality. Taxable income comprises rent from the mobile tower (after the 30% standard deduction under s.24(a)), "
               f"bank interest and scrap sale, giving a gross total income of {inr(summary['gti'])}. Interest of {inr(summary['deduction_80p'])} from the co-operative bank is deductible under s.80P(2)(d), leaving total income of {inr(summary['total_income'])}.\n\n"
               f"Tax under the normal slab rates is {inr(summary['tax_old'])} against {inr(summary['tax_115bad'])} under the optional s.115BAD regime, which would forfeit the 80P deduction; the normal regime is therefore recommended. "
               f"After TDS credit of {inr(summary['tds_credit'])} the net liability is {inr(summary['net_payable'])}.\n\n"
               f"No advance tax was paid although the liability exceeds Rs 10,000, so interest of about {inr(summary['interest_234c'])} under s.234C and {inr(summary['interest_234b'])} under s.234B (to 31 October 2026) is payable. "
               f"The society should pay self-assessment tax before filing ITR-5 and budget for quarterly advance tax from FY 2026-27.")
        return self._template("tax_note", instr, txt)

    # ------------------------------------------------------------------ log
    def write_log(self, path) -> None:
        lines = ["# AI prompt and response log", "", f"Model: {self.model}  |  AI enabled: {self.enabled}", "",
                 "Each entry shows the instruction sent (the JSON context is truncated here but logged in full in the workbook), the source of the text and any citation flagged by the guardrail.", ""]
        for e in self.log:
            lines += [f"## {e.task}  ({e.source})", "", "**Instruction / context (first 1,200 chars):**", "", "```", e.prompt[:1200], "```", "",
                      "**Output:**", "", e.response[:4000], ""]
            if e.unverified_citations:
                lines += ["**Unverified citations flagged:** " + ", ".join(sorted(set(e.unverified_citations))), ""]
        path.write_text("\n".join(lines), encoding="utf-8")
