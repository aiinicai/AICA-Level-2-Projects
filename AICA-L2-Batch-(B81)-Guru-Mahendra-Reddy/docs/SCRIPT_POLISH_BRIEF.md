# Brief — polishing my recorded transcript into video narration

**Paste this whole file into a new conversation before pasting the transcript.**
It carries everything needed to polish what I actually said without changing
what is true.

---

## 1 · What I am asking for

I am recording a walkthrough video of an application I built. Rather than read
a written script aloud — which sounds read — I am **speaking freely to camera
and will paste the raw transcript**.

Your job is to **polish my transcript, not rewrite it**:

- Keep my voice, my phrasing and my sentence rhythm. If you hand me back
  something I would not say out loud, you have done the wrong thing.
- Remove filler ("um", "uh", "you know", "basically", "actually", "sort of"),
  false starts, and repeated words.
- Fix grammar only where it would distract a listener. Leave natural spoken
  constructions alone — spoken English is not written English, and
  over-correcting is what makes narration sound stiff.
- Tighten repetition and rambling. If I circle the same point three times,
  keep the best one.
- **Flag anything factually wrong against section 4 below.** Do not silently
  "correct" it — show me what I said, what is actually true, and let me decide.
  Section 5 lists the specific mistakes I am most likely to make.
- Tell me the word count and the approximate spoken duration (about 145–150
  words per minute), and where I am over or under against section 3.

If a section of transcript is too thin to carry its part of the story, say so
and tell me what is missing — do not invent content and put it in my mouth.

---

## 2 · The project, in one paragraph

**Cash Runway** — a twelve-screen cash-management application for founders and
CFOs, built as my capstone for the **ICAI AICA (AI for Chartered Accountants)
Level 2** certification. I am a Chartered Accountant working in finance; I
wrote the specification and made the design and accounting decisions, and built
it with an AI assistant writing most of the code. Current version **v1.8**.

The problem it addresses: companies fail because they run out of cash while the
P&L still looks healthy. Revenue is recognised when work is done; cash arrives
when the customer pays, which in India is routinely 60–90 days later.

Four design rules run through every screen:

1. **No number without its basis** — every figure carries how it was worked out
   and the date it is as at.
2. **Every number is traceable** — click any figure to see the ledger entries
   behind it.
3. **Colour means one thing** — Red act this week · Amber watch · Green within
   tolerance · Grey data incomplete, do not rely on it.
4. **The tool is honest about itself** — when it does not know, it says so
   rather than showing a confident zero.

---

## 3 · Structure and timing — target 10 minutes

| Part | Section | Target |
|---|---|---|
| 1 | The problem | 1:00 |
| 2 | What I set out to build — the four rules | 1:00 |
| 3 | How it is built — stack and integrations | 1:15 |
| 4 | Walkthrough — prerequisites, set-up, screens, benefits | 5:30 |
| 5 | Limitations and what I learned | 1:15 |

If I run long, cut from part 4. Parts 1, 2 and 5 stay.

**Audience:** the ICAI examiner, but also LinkedIn and work colleagues. So:
the first fifteen seconds must hold someone who is not a CA; CA terms like DSO
get a half-sentence explanation the first time; and it is framed as something I
built to learn — never as a product anyone should buy, and never as a
replacement for anything in use at my employer.

---

## 4 · Verified facts — check everything I say against this

### Technology

- Backend: **Python, FastAPI, SQLAlchemy over SQLite** — **97 API endpoints,
  46 tables**, one database file.
- Frontend: **React, Vite, Tailwind, Recharts**.
- Runs with **Python only** — packages ship pre-built in the folder. No
  internet, no Node, no `npm install`, no database server. One command.
- Integrations: **Tally Prime** (XML over HTTP, port 9000) and **Twilio** (SMS).
- **12 screens. 10 alert rules.**

### The demonstration dataset (18 months, Northwind Robotics, as at 31-Aug-2026)

These are the figures on screen during the walkthrough. If I quote a number,
check it against this table.

| | |
|---|---|
| Cash available | **₹ 4.17 Cr** (₹ 45 L lien-marked, ₹ 2.50 Cr undrawn credit) |
| Net burn | **₹ 54.0 L / month**, 3-month average, normalised |
| Runway | **7.7 months** · cash-out **22-Apr-27** |
| Liquidity health | **52 — Tight** |
| Receivables | **₹ 4.80 Cr** · DSO **72 days** · **42% overdue** |
| Largest client | Bharat Metro Rail — **36%** of receivables, ₹ 84 L, 47 days late |
| Statutory, next 30 days | ₹ 33.05 L due, ₹ 26.55 L earmarked, **₹ 6.50 L gap** |
| Covenant | Current ratio amber — **8.4% headroom**, tested 30-Sep |
| Books vs bank difference | **₹ 3.20 L**, unexplained |

### The Tally demonstration data (separate from the above)

17 months across two financial years, **50 ledgers, 475 vouchers**, generated
and checked against a trial balance before the files are written.

---

## 5 · Mistakes I am most likely to make — correct me on these

These are specific, and each one has already caught me out once.

**The commentary in the app is NOT written by AI.**
The "Reading of the Position" box is produced by `_rule_narrative()` — ordinary
conditional logic assembling sentences from figures already computed. The
`anthropic` SDK is not in `requirements.txt` and no API key is set, so the
optional model path cannot run. If I say "AI writes the commentary", that is
wrong. The correct framing: *deterministic, reproducible, nothing leaves the
machine — in a finance tool, reproducible beats eloquent.* The AI was in the
**building**, not the **running**.

**Alerts go by SMS through Twilio, not WhatsApp.**
An earlier version used Meta's WhatsApp Cloud API and it could never have
worked — Meta refuses business-initiated messages outside a 24-hour window the
recipient opens, and an alert is business-initiated by definition. If I say
WhatsApp, correct me.

**"Accepted", not "delivered".**
Twilio accepting a message is not a handset showing it. There is no delivery
webhook, so the app says accepted. Do not let me claim delivery confirmation.

**The Tally connection in the demo is a local stand-in.**
I do not have a licensed Tally. Educational mode only accepts vouchers dated
the 1st, 2nd or 31st of a month, so 441 of the 475 will not import. The demo
runs against a mock endpoint speaking the same XML on the same port. The
connector cannot tell the difference, but I must not claim I have tested
against production Tally.

**It IS a multi-user, multi-device application — but it is not deployed.**
Four roles, real sign-in, and the board account is filtered server-side.
Several people can use it at once over the office network. What it lacks is a
server, a domain, HTTPS, and always-on running. Do not let me say "single
user" or "single machine" — that undersells it. Do not let me say "deployed"
or "production-ready" either.

**Do not let me quote a statistic about how many businesses fail from cash
flow.** The commonly circulated figures do not survive checking, and one shaky
number undermines a section built on defensible ones.

---

## 6 · Part 5 — limitations. The most important minute.

This section is what separates the video from a sales demo, so it should not be
rushed or softened. Five points:

1. **Tally is a stand-in** — no licensed copy; educational mode's date
   restriction; demo runs against a local endpoint.
2. **SMS needs DLT registration in India** — the domestic route requires the
   entity, sender header and every template pre-approved, and unregistered
   messages are dropped at the network with no error returned. The code is
   production-shaped; the account is not production-registered.
3. **Accepted ≠ delivered** — no status webhook.
4. **Not deployed** — no server, no domain, no HTTPS; runs only while started.
5. **Three bugs passed every test.** All three worked in demo mode and would
   have failed only in production:
   - **Tally's sign convention is backwards** — inside `ALLLEDGERENTRIES.LIST`
     a negative amount is a debit, and the adapter read it the intuitive way.
     Every receipt would have been recorded as a payment; burn would have read
     as income.
   - **A save button called a method that did not exist** — the browser API
     client had `get`, `post`, `patch` and `del` but no `put`, and three
     screens called `put`. Board visibility switches appeared to work and never
     saved.
   - **The WhatsApp integration could never have worked** — the 24-hour window
     problem above. The template setting existed in config and no code read it.

   What caught them was building a fake Tally that behaved like the real one
   and then reading what came back. **The test that matters is the one that
   fails the way production fails.** That line is the point of the whole
   section — keep it.

Saying all this is a deliberate choice. It shows judgement rather than
weakness, and on an AI certification a candidate who can say precisely where AI
assistance failed them is more credible than one who implies it did not.

---

## 7 · Language and tone

- Indian English and Indian numbering — **lakh and crore, never million**.
  "₹ 4.17 crore", "₹ 54 lakh".
- Spoken numbers: "four point one seven crore", "seven point seven months".
- Keep contractions. Keep short sentences. Keep my asides if they land.
- Do not add marketing language, superlatives, or phrases like "game-changing",
  "seamless", "powerful", "revolutionise".
- Do not add a call to action. This is a walkthrough, not a pitch.

---

## 8 · What to give me back

1. **The polished transcript**, section by section, ready to record or to use
   as subtitles.
2. **A separate list of factual corrections** — what I said, what is true, and
   the sentence I should say instead. Do not bury these in the transcript.
3. **Word count and estimated duration**, with a note on where I am over or
   under the timings in section 3.
4. **Anything missing** — a part of the story I skipped that the structure
   needs.
