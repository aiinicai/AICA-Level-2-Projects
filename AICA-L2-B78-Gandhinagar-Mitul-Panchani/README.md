# AI Memory Governance & Audit Layer

**AICA Level 2 Capstone Project — Batch 78, Gandhinagar**
**Mitul Panchani**

A working prototype of a **governance and audit layer** that wraps an AI memory store — adding
provenance tracking, tamper-evident auditing, contradiction detection, cascading erasure, and access
control that discriminates between a legitimate data request and an extraction attempt.

---

## The problem this addresses

Large language models don't remember anything between conversations by default. That problem is
largely solved — there is a mature ecosystem of memory frameworks (Mem0, Zep, Letta, Cognee) that
store and retrieve facts across sessions.

What remains unsolved is **governing** that memory once it exists:

| Problem | What goes wrong |
|---|---|
| **Staleness** | A stored fact ("works at Company X") is correct until it isn't, and nothing tells you when it went stale |
| **Provenance** | "The user told me this" and "I concluded this" need different trust levels, but most systems store both identically |
| **Right to erasure** | Deleting a fact is easy; deleting everything *derived* from it is not, and most systems don't try |
| **Extraction resistance** | A cleverly worded request can talk a memory store into dumping everything it knows |

This project builds the governance layer that addresses those four directly, rather than building
another memory store. The underlying store is deliberately simple — all the engineering is in the
controls around it.

---

## Quick start

### Just run the demo (no installation)

```
demo/AIMemoryGovernance.exe
```

Double-click it. Your browser opens at `http://127.0.0.1:8000`.

**No Python, no installation, no API key, and no internet connection required.** Windows will show
a "Windows protected your PC" warning on first run because the binary is unsigned — click
**More info → Run anyway**.

### Run from source

```bash
pip install -r requirements.txt
python run_demo.py          # CLI: all 9 scenarios with before/after evidence
python run_web.py           # web UI at http://127.0.0.1:8000
python -m pytest -q         # 143 tests
```

---

## What it demonstrates

Nine scenarios, all runnable from the **Scripted Evidence** panel in the UI or via `run_demo.py`:

| # | Scenario | What it proves |
|---|---|---|
| 1 | Continuity across a fresh session | A fact survives into a session with zero carried-over history |
| 2 | Contradiction detected | A conflicting fact is flagged, not silently overwritten |
| 2b | Additive fact accepted | A *related but non-contradicting* fact is **not** falsely flagged |
| 3 | Provenance and trust tiers | AI inferences sit at lower trust until a human confirms them |
| 4 | Cascading right to erasure | Deleting a fact also deletes what was inferred from it — and both embeddings |
| 5a | Extraction attack refused | An instruction-override request is blocked and logged |
| 5b | Legitimate gated access succeeds | The *same breadth* of request succeeds through the confirmation gate |
| 6a | Write-path poisoning rejected | Instruction-shaped and hypothetical candidates never become memories |
| 6b | Genuine statement accepted | An ordinary statement immediately afterwards is still accepted |

**The paired scenarios are the point.** 2/2b, 5a/5b and 6a/6b each run both halves, because a system
that flags everything or refuses everything would look secure while being useless. Running only the
"blocks it" half would leave open whether the system is actually governing or just saying no.

---

## Architecture

```
Conversation turn (user's own text only)
        │
        ▼
   Maker ──► Checker ──► Provenance ──► Contradiction ──► Write ──► Audit log
 (proposes)  (verifies   (source_type,   (subject_key      (memory   (hash-chained)
             in isolation) trust tier)    + entailment)     + embedding)
```

### The design decisions that matter

**Maker–checker separation.** The extraction layer reads *only* the current turn's direct user text —
never retrieved memory, never prior conversation. The checker then sees *only* the proposed fact and
its classification, never the original message. That narrow context is what makes it an independent
second check rather than the same model re-reading its own output. The function signatures enforce
this: there is no parameter through which the original message could reach the checker.

**Similarity never decides a contradiction.** Embedding search only narrows *which* stored facts are
worth checking; an explicit entailment call makes the actual judgment. Similarity alone both misses
subtle contradictions and false-positives on merely-related content.

**The audit log never contains memory content.** Only structural metadata — subject key, trust tier,
a SHA-256 fingerprint. A deletion that leaves the erased text sitting in an audit row hasn't erased
anything. This is enforced by an allowlist in code, not by convention.

**Retrieval has two separate paths, not one with a flag.** Contextual retrieval is hard-capped at a
small top-k with no parameter to override it. Full export is reachable only through a confirmation
gate. A flag would be exactly the back door the design exists to prevent.

**Erasure destroys the embedding too.** An embedding can partially reconstruct the text it was built
from, so leaving one behind is not deletion.

Full specification: [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## Tamper-evidence

Every audit row's SHA-256 hash covers its own fields **plus the previous row's hash**. SQLite will
happily let someone edit a row — nothing stops them. The point is that the moment they do, the chain
no longer adds up and the system can name the altered row.

The UI has a **Tamper Test** button that deliberately mutates a row via raw SQL so you can watch
`✓ Chain valid` become `✕ Chain broken at row N`, then repair it. It proves the claim rather than
asserting it.

---

## Regulatory framing — DPDP Act 2023

This project is framed against India's Digital Personal Data Protection Act because the Act's
structure — consent, correction, erasure, retention exceptions — maps unusually well onto the exact
problems memory systems still struggle with.

> **This is not a compliance claim.** It demonstrates *architectural alignment* with DPDP principles.
> A real compliance claim requires legal review, which this project does not attempt.

| Principle | Basis | How the architecture reflects it |
|---|---|---|
| Consent & notice | Core obligation | **Not implemented.** Named explicitly rather than skipped silently — a real deployment would need consent capture before any write. |
| Right to access | Section 11 | Two mechanisms: bounded contextual retrieval for ordinary questions, gated full export for "give me everything" |
| Correction & erasure | Section 12 | `status`/`supersedes_id` model correction as a logged event; erasure removes content, embedding, and all derived facts |
| Retention vs erasure | Section 12(4)–(5) | Content is erased; a content-free hashed audit row proves the deletion happened without retaining the data |
| Accountability logging | General | The hash-chained log, including `access_denied` events — every attempt, successful or blocked, is on record |

---

## Known limitations

Naming these precisely is more defensible than pretending they don't exist.

- **Write-path trust is raised, not solved.** The maker–checker split makes memory poisoning
  substantially harder, but a sufficiently sophisticated message could in principle fool both passes.
  This is a research problem and the project does not claim to have solved it.
- **Consent is assumed, not captured.** See the table above.
- **The export gate is not real authentication.** A fixed passphrase stands in for it, so that the
  gate is a genuine code path rather than a suggestion.
- **Single user, single persona.** Multi-user isolation and cross-session identity resolution are
  real problems, but separate ones.
- **The contradiction threshold is a defensive default.** Set to 0.70 and chosen from offline values;
  see [`docs/decisions/002-contradiction-threshold.md`](docs/decisions/002-contradiction-threshold.md)
  for why, and why it should be re-measured against a live provider.

---

## Technology

| Layer | Choice | Why |
|---|---|---|
| LLM | Google Gemini (`gemini-3.5-flash`), with a deterministic offline fallback | Only does structured classification — extraction, verification, entailment |
| Embeddings | Voyage AI (`voyage-4-lite`), with a local deterministic fallback | Anthropic does not offer an embedding model and recommends Voyage |
| Vector search | Brute-force cosine similarity in plain Python | Deliberate — at demo scale, being able to show the exact retrieval math beats a vector DB |
| Storage | SQLite, single file, no ORM | Zero infrastructure, fully inspectable |
| Interface | FastAPI + Jinja2 + vanilla JS | No build step, runs offline |

**The governance layer is model-agnostic by design.** The LLM is a swappable component behind an
interface — adding an API key switches it to live calls with no code change, and the system reports
honestly which backend actually served each call. It will never show "live" when the offline engine
answered.

---

## Repository contents

```
├── README.md                  this file
├── ARCHITECTURE.md            full specification (v2.1)
├── DEMO-SCRIPT.md             step-by-step presenter guide
├── VIDEO-NARRATION.md         narration script for the demo video
├── DISTRIBUTION.md            guide for anyone running the .exe
├── demo/
│   ├── AIMemoryGovernance.exe        portable Windows build (53 MB)
│   └── *.docx                        the two scripts, formatted
├── video/
│   └── *.mp4                         demo walkthrough recording
├── src/amg/                   application source
├── tests/                     143 tests, all offline
└── docs/
    ├── decisions/             architectural decisions made during the build
    ├── build-specs/           the phase specifications the build followed
    └── demo-persona.md        the scripted synthetic dataset
```

`docs/decisions/` is worth a look — it records two points where the specification contradicted
itself and how each was resolved.

---

## Notes for reviewers

**All demo data is synthetic.** No real personal data about any identifiable person appears anywhere
in this project.

**No API keys are included.** The `.env` file is deliberately excluded; `.env.example` shows the
shape. The application runs fully offline without any key, which is how all 143 tests pass.

**Tests run with no network access.** A socket guard in `tests/conftest.py` raises on any outbound
connection, so the suite cannot silently depend on a live API.
