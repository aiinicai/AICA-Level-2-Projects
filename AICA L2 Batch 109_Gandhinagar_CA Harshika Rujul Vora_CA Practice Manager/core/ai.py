"""AI assistant: Google Gemini (free tier) with client-confidentiality safeguards.

Responsible-AI design
  * Masking: client names, staff names, PAN, GSTIN, Aadhaar, phone numbers, e-mails and IFSC codes are replaced
    with tokens (CLIENT-01, PAN-1, ...) BEFORE anything leaves the app, and put back only on this computer.
  * Transparency: every screen shows exactly what was sent to the AI.
  * Consent: documents (notices) are sent only after the user reviews the masked text and ticks a box.
  * Human in the loop: AI output is a draft; nothing is filed, sent or changed without a person acting on it.
  * Audit trail: every AI call is logged (who, which feature, when, how many characters) in `ai_log`.
Google's free tier may use submitted content to improve its products and human reviewers may read it,
which is why masking is on for every request.
"""
import io
import json
import os
import re
import urllib.error
import urllib.request
from datetime import timedelta

from . import clock, config, db, duedates

DEFAULT_MODEL = "gemini-3.5-flash-lite"
MODEL_CHOICES = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"]
API_BASE = os.environ.get("CAPM_GEMINI_BASE", "https://generativelanguage.googleapis.com/v1beta")
MAX_DOC_CHARS = 30_000

SYSTEM_BASE = (
    "You are the practice assistant inside 'CA Practice Manager', software used by a firm of Chartered "
    "Accountants in India. You help with GST, Income Tax, TDS and Audit compliance work. Be accurate, brief and "
    "practical; use Indian terminology (GSTR-3B, Form 26Q, section 143(1), etc.) and Indian number formatting "
    "(lakh, crore). Identifiers such as CLIENT-03, STAFF-B, PAN-1 or GSTIN-2 are deliberate privacy masks: use "
    "them exactly as written and never guess the real values. If something cannot be answered from the "
    "information given, say so plainly instead of inventing it. Due dates and provisions can change; when you "
    "rely on a statutory rule, say that it should be checked against the latest notification."
)


class AIError(Exception):
    """A problem the user can understand and act on."""


# ------------------------------------------------------------------ settings
def api_key() -> str | None:
    return (os.environ.get("GEMINI_API_KEY") or config._from_secrets("GEMINI_API_KEY")
            or db.get_setting("gemini_api_key"))


def model() -> str:
    return db.get_setting("gemini_model") or DEFAULT_MODEL


def enabled() -> bool:
    return db.get_setting("ai_enabled", "1") == "1" and bool(api_key())


# ------------------------------------------------------------------ masking
PATTERNS = [  # order matters: GSTIN contains a PAN, so it goes first
    ("GSTIN", re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", re.I)),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)),
    ("AADHAAR", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")),
    ("IFSC", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")),
]
ADDRESS_RX = re.compile(r"(?im)^(\s*(?:registered\s+|principal\s+place\s+of\s+business\s*/?\s*)?address\s*[:\-]\s*)"
                        r"(.+?)(?=\s+(?:mobile|phone|ph|tel|email|e-mail)\b|$)")
_SUFFIXES = re.compile(r"\b(private|pvt\.?|limited|ltd\.?|llp|& co\.?|and co\.?)\s*$", re.I)


class Masker:
    """Replaces confidential values with tokens, and puts them back in the AI's reply."""

    def __init__(self, extra_names: list[str] | None = None):
        self.forward: dict[str, str] = {}   # real (lower-case key) -> token
        self.back: dict[str, str] = {}      # token -> real (original spelling)
        self.counts: dict[str, int] = {}
        self.names: list[tuple[str, str]] = []  # (real name, kind)
        for c in db.query("SELECT name FROM clients ORDER BY id"):
            self._add_name(c["name"], "CLIENT")
        for u in db.query("SELECT name FROM users ORDER BY id"):
            self._add_name(u["name"], "STAFF")
        for n in extra_names or []:
            if n and n.strip():
                self._add_name(n.strip(), "PARTY")
        self.names.sort(key=lambda x: -len(x[0]))  # longest first: "Navkar Textiles Pvt Ltd" before "Navkar"

    def _token(self, kind: str, real: str) -> str:
        key = real.strip().lower()
        if key in self.forward:
            return self.forward[key]
        self.counts[kind] = self.counts.get(kind, 0) + 1
        n = self.counts[kind]
        tok = f"{kind}-{n:02d}" if kind == "CLIENT" else (f"STAFF-{chr(64 + n)}" if kind == "STAFF" and n <= 26
                                                          else f"{kind}-{n}")
        self.forward[key] = tok
        self.back[tok] = real.strip()
        return tok

    def _add_name(self, name: str, kind: str):
        name = name.strip()
        if len(name) < 3:
            return
        tok = self._token(kind, name)
        self.names.append((name, kind))
        short = name
        while True:  # "Navkar Textiles Pvt Ltd" -> "Navkar Textiles Pvt" -> "Navkar Textiles"
            nxt = _SUFFIXES.sub("", short).strip(" ,.")
            if nxt == short:
                break
            short = nxt
        if short and short != name and len(short) >= 4:
            self.forward[short.lower()] = tok
            self.names.append((short, kind))
        if kind == "STAFF":  # "CA Priya Shah" -> also mask "Priya Shah"
            bare = re.sub(r"^(ca|cs|dr|mr|ms|mrs)\.?\s+", "", name, flags=re.I)
            if bare != name and len(bare) >= 4:
                self.forward[bare.lower()] = tok
                self.names.append((bare, kind))

    def mask(self, text: str) -> str:
        if not text:
            return text
        for real, _ in self.names:
            tok = self.forward[real.lower()]
            text = re.sub(rf"(?<![\w-]){re.escape(real)}(?![\w-])", tok, text, flags=re.I)
        # an "Address: ..." line is replaced up to the end of the line (addresses follow no fixed pattern)
        text = ADDRESS_RX.sub(lambda m: m.group(1) + self._token("ADDRESS", m.group(2)), text)
        for kind, rx in PATTERNS:
            text = rx.sub(lambda m, k=kind: self._token(k, m.group(0)), text)
        return text

    def unmask(self, text: str) -> str:
        for tok in sorted(self.back, key=len, reverse=True):
            text = text.replace(tok, self.back[tok])
        return text

    def leaks(self, text: str) -> list[str]:
        """Any real value that would still leave the app (used by tests and as a last check)."""
        low = text.lower()
        return [real for real, _ in self.names if real.lower() in low] + \
               [m.group(0) for _, rx in PATTERNS for m in rx.finditer(text)]


# ------------------------------------------------------------------ the API call
def generate(system: str, prompt: str, *, json_mode=False, temperature=0.3, feature="ask", user_id=None) -> str:
    key = api_key()
    if not key:
        raise AIError("The AI assistant isn't set up yet. A Partner can add a free Gemini API key in "
                      "Settings → AI assistant.")
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_BASE + "\n\n" + system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 2048},
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    req = urllib.request.Request(
        f"{API_BASE}/models/{model()}:generateContent", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode()).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        if e.code in (400, 403) and "key" in msg.lower():
            raise AIError("Google rejected the API key. Check it in Settings → AI assistant.") from None
        if e.code == 404:
            raise AIError(f"The AI model '{model()}' isn't available. Pick another model in Settings → AI assistant.") from None
        if e.code == 429:
            raise AIError("The free AI quota is used up for now. Wait a minute (or until tomorrow for the daily "
                          "limit) and try again.") from None
        raise AIError(f"The AI service returned an error ({e.code}). {msg[:200]}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AIError("Couldn't reach the AI service. Check the internet connection and try again.") from None
    db.execute("INSERT INTO ai_log(user_id, feature, model, chars_sent, at) VALUES (:u,:f,:m,:c,:a)",
               u=user_id, f=feature, m=model(), c=len(prompt), a=db.now())
    try:
        cand = data["candidates"][0]
        text = "".join(p.get("text", "") for p in cand["content"]["parts"])
    except (KeyError, IndexError, TypeError):
        reason = (data.get("promptFeedback") or {}).get("blockReason") or \
                 ((data.get("candidates") or [{}])[0].get("finishReason"))
        raise AIError(f"The AI returned no answer{f' ({reason})' if reason else ''}. Try rephrasing.") from None
    return text.strip()


def test_connection() -> str:
    return generate("Reply with the single word OK.", "Connection test.", feature="test")


# ------------------------------------------------------------------ feature 1: ask about the practice
def practice_context(user: dict, m: Masker) -> str:
    """A compact, masked snapshot of the firm's current work for the AI to answer from."""
    today = clock.today()
    horizon = today.replace(day=1).isoformat()  # include work completed this month
    staff_only = user["role"] == "Staff"
    scope = " AND t.assigned_to = :me" if staff_only else ""
    tasks = db.query(
        "SELECT c.name AS client, t.title, t.period, t.due_date, t.status, t.priority, u.name AS who "
        "FROM tasks t JOIN clients c ON c.id=t.client_id LEFT JOIN users u ON u.id=t.assigned_to "
        "WHERE c.active=1 AND (t.status<>'Done' OR t.completed_on>=:h) AND t.due_date<=:far" + scope +
        " ORDER BY t.due_date LIMIT 350", h=horizon, far=(today + timedelta(days=365)).isoformat(),
        **({"me": user["id"]} if staff_only else {}))
    lines = [f"Today: {today.isoformat()} ({today.strftime('%A')}). Financial year: FY {duedates.fy_label(duedates.current_fy_start(today))}.",
             f"The person asking: {m.mask(user['name'])} ({user['role']}). "
             + ("They can only see tasks assigned to them." if staff_only else "They can see the whole firm."),
             "", "TASKS (client | task | period | due date | status | priority | assigned to):"]
    for t in tasks:
        lines.append(" | ".join([m.mask(t["client"]), t["title"], t["period"] or "", t["due_date"], t["status"],
                                 t["priority"] or "", m.mask(t["who"] or "Unassigned")]))
    if not staff_only:
        inv = db.query("SELECT c.name AS client, COUNT(*) AS n, SUM(i.total) AS amt, MIN(i.due_date) AS oldest "
                       "FROM invoices i JOIN clients c ON c.id=i.client_id WHERE i.status='Unpaid' "
                       "GROUP BY c.name ORDER BY amt DESC")
        lines += ["", "UNPAID INVOICES (client | count | amount incl. GST in Rs. | oldest due date):"]
        lines += [f"{m.mask(r['client'])} | {r['n']} | {r['amt']:.0f} | {r['oldest']}" for r in inv]
        cl = db.query("SELECT name, entity_type, gst_freq, has_tds, needs_audit FROM clients WHERE active=1")
        lines += ["", "CLIENTS (client | entity | GST filing | TDS | tax audit):"]
        lines += [f"{m.mask(c['name'])} | {c['entity_type']} | {c['gst_freq']} | {'yes' if c['has_tds'] else 'no'} | "
                  f"{'yes' if c['needs_audit'] else 'no'}" for c in cl]
    return "\n".join(lines)


def ask(user: dict, question: str) -> dict:
    m = Masker()
    context = practice_context(user, m)
    q = m.mask(question)
    prompt = f"FIRM DATA\n{context}\n\nQUESTION\n{q}"
    system = ("Answer the question using only the FIRM DATA. Prefer short bullet points or a small table. "
              "Mention due dates as DD Mon YYYY. When listing work, put overdue items first.")
    answer = generate(system, prompt, feature="ask", user_id=user["id"])
    return {"answer": m.unmask(answer), "sent": prompt, "leaks": m.leaks(prompt)}


# ------------------------------------------------------------------ feature 2: client reminder
def client_reminder(user: dict, client_id: int, channel: str, language: str, tone: str, extra: str = "") -> dict:
    m = Masker()
    c = db.one("SELECT * FROM clients WHERE id=:i", i=client_id)
    today = clock.today()
    tasks = db.query("SELECT title, period, due_date FROM tasks WHERE client_id=:c AND status<>'Done' "
                     "AND due_date<=:h ORDER BY due_date", c=client_id, h=(today + timedelta(days=30)).isoformat())
    unpaid = db.query("SELECT invoice_no, invoice_date, total, due_date FROM invoices WHERE client_id=:c AND "
                      "status='Unpaid' ORDER BY invoice_date", c=client_id)
    firm = db.get_setting("firm_name", "our firm")
    facts = [f"Client: {m.mask(c['name'])} ({c['entity_type']}). Contact person: {m.mask(c['contact_person'] or 'Sir/Madam')}.",
             f"Our firm: {firm}. Today: {today.strftime('%d %b %Y')}.", "Pending compliances (task | period | due date):"]
    facts += [f"- {t['title']} | {t['period']} | {t['due_date']}" + (" (OVERDUE)" if t["due_date"] < today.isoformat() else "")
              for t in tasks] or ["- none pending in the next 30 days"]
    if unpaid:
        facts.append("Unpaid invoices (number | date | amount Rs. incl. GST | due):")
        facts += [f"- {i['invoice_no']} | {i['invoice_date']} | {i['total']:.0f} | {i['due_date']}" for i in unpaid]
    if extra.strip():
        facts.append("Extra instructions from the firm: " + m.mask(extra.strip()))
    prompt = "\n".join(facts)
    length = {"WhatsApp": "under 90 words, friendly, no subject line, 1-2 emojis at most",
              "Email": "a subject line, then a short professional e-mail of 120-180 words"}[channel]
    system = (f"Write a reminder from the CA firm to its client asking for the information or documents needed "
              f"for the pending compliances, and mentioning the due dates. Format: {length}. Language: {language}. "
              f"Tone: {tone}. List what the client must send, inferred from each compliance (for example sales and "
              f"purchase data for GST returns, salary and vendor payment details for TDS, bank statements and "
              f"investment proofs for ITR). Mention unpaid invoices politely only if listed. Sign off with the firm's "
              f"name. Output only the message.")
    draft = generate(system, prompt, temperature=0.6, feature="reminder", user_id=user["id"])
    return {"draft": m.unmask(draft), "sent": prompt, "leaks": m.leaks(prompt)}


# ------------------------------------------------------------------ feature 3: notice reader
def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((p.extract_text() or "") for p in reader.pages[:15])
        except Exception as e:
            raise AIError(f"Couldn't read this PDF ({type(e).__name__}).") from None
        if len(text.strip()) < 40:
            raise AIError("This PDF has no readable text (it's probably a scanned image). Copy the notice text "
                          "and paste it in the box instead.")
        return text
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", "ignore")


NOTICE_FIELDS = ["notice_type", "law", "section", "issued_by", "reference_no", "notice_date", "period",
                 "reply_due_date", "amount_involved", "summary", "issues", "documents_needed", "reply_points",
                 "risk_level", "confidence_note"]


def analyse_notice(user: dict, masked_text: str) -> dict:
    system = (
        "You read Indian tax notices (GST: ASMT-10, DRC-01/01A, REG-03/17, etc.; Income Tax: 143(1), 142(1), "
        "143(2), 148/148A, 133(6), 139(9), 245, demand notices; TDS defaults). Return ONLY a JSON object with "
        "these keys: notice_type (short name), law ('GST' | 'Income Tax' | 'TDS' | 'Other'), section, issued_by, "
        "reference_no, notice_date (YYYY-MM-DD or ''), period (tax period / AY / FY), reply_due_date "
        "(YYYY-MM-DD or '' — the date by which a reply or compliance is required), amount_involved (number in "
        "rupees or 0), summary (3-4 plain sentences), issues (list of strings: what the department is asking or "
        "alleging), documents_needed (list of strings), reply_points (list of strings: the points a reply should "
        "cover), risk_level ('Low' | 'Medium' | 'High'), confidence_note (one sentence on anything unclear or "
        "missing). Never invent a date or amount that is not in the text: use '' or 0.")
    raw = generate(system, "NOTICE TEXT (masked)\n" + masked_text[:MAX_DOC_CHARS], json_mode=True,
                   temperature=0.1, feature="notice", user_id=user["id"])
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
    except ValueError:
        raise AIError("The AI's answer wasn't in the expected format. Please try again.") from None
    out = {k: data.get(k, "" if k not in ("issues", "documents_needed", "reply_points") else []) for k in NOTICE_FIELDS}
    for k in ("issues", "documents_needed", "reply_points"):
        if isinstance(out[k], str):
            out[k] = [out[k]] if out[k] else []
    try:
        out["amount_involved"] = float(str(out["amount_involved"]).replace(",", "") or 0)
    except ValueError:
        out["amount_involved"] = 0.0
    return out


def draft_notice_reply(user: dict, masked_text: str, analysis: dict, firm_points: str) -> str:
    system = ("Draft a formal reply to this tax notice on behalf of the taxpayer, prepared by their Chartered "
              "Accountant. Structure: To / Subject / Reference / opening paragraph / point-wise response to each "
              "issue / list of enclosures / closing. Use placeholders in square brackets, like [amount] or "
              "[date of payment], wherever facts are not given. Keep the masked identifiers as they are. "
              "Add one line at the end: 'Draft prepared with AI assistance: to be reviewed by the engagement partner.'")
    prompt = (f"NOTICE TEXT (masked)\n{masked_text[:MAX_DOC_CHARS]}\n\nANALYSIS\n{json.dumps(analysis, indent=1)}"
              f"\n\nFIRM'S POINTS FOR THE REPLY\n{firm_points or '(none given: use placeholders)'}")
    return generate(system, prompt, temperature=0.3, feature="notice_reply", user_id=user["id"])
