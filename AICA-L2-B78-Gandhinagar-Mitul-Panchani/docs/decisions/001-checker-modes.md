# Decision 001 — The checker needs two modes, not one

**Date:** 2026-08-23
**Status:** Accepted
**Context:** Found during Phase 2 behavioural testing, before Phases 3–7 were built.

## The problem

`ARCHITECTURE.md` §3.1 defines the write verifier ("checker") as:

> Approves the write only if the classification genuinely looks like a direct first-person
> statement and the fact text itself doesn't read as instruction-shaped.

Implemented literally, this rejects **every** AI-inferred fact — because an inference is by
definition *not* a first-person statement. It is third-person about the user
("User likely avoids leather goods").

That outcome silently breaks three things the same document requires:

| Requirement | Source | Why it breaks |
|---|---|---|
| Provenance distinguishes `user_stated` from `ai_inferred` | Goal 1 | Only one source type would ever be written |
| Inferred memories surface at a lower trust tier | Scenario 3, P1 | No inferred memories exist to surface |
| Deletion cascades through `derived_from` to dependents | Scenario 4, P0 | No dependents are ever created |

So the specification is internally inconsistent: §3.1 forbids what §7 requires. This was caught by
probing actual behaviour rather than by reading the spec — the unit tests passed, because they only
tested the cases the spec described.

## The decision

The first-person test guards the **`user_stated` path specifically**, not all writes.

That path is where the write-path poisoning risk actually lives, because it is the path carrying the
claim *"the user asserted this."* An `ai_inferred` candidate makes no such claim — it is explicitly
marked as AI-derived and lands at the lowest trust tier pending confirmation. It therefore needs a
**different** check, not an exemption from checking.

The checker now branches on the candidate's `source_type`:

**`user_stated`** — unchanged, security-critical:
- must read as a genuine first-person self-statement
- must match its claimed `assertion_type`
- must not be instruction-shaped
- `hypothetical` / `third_party` / `quoted` are rejected

**`ai_inferred`** — a different test, not a weaker one:
- must not be instruction-shaped (*the injection screen still applies*)
- must be **inference-shaped**: third-person and hedged. An inference phrased as a first-person user
  statement is rejected (`not_inference_shaped`) — an inference must never masquerade as something
  the user said, which is exactly the confusion the provenance model exists to prevent.
- must not **overclaim certainty**: a flat assertion with no hedge ("User is a vegan") is rejected
  (`overclaims_certainty`). An unhedged inference presented as fact is the specific failure mode
  this trust tier exists to catch.

## What is explicitly NOT changed

The isolation property is untouched and non-negotiable. The checker still receives **only** the
candidate's content, its assertion type, and its source type. It still never sees the original
message. Adding a second mode does not widen its context — that narrow context is what makes it an
independent check rather than the maker re-reading its own output.

The `user_stated` checks were not loosened in any respect. This change adds a branch; it does not
relax the existing one. A test asserts instruction-shaped candidates are rejected under **both**
source types.

## Defense note

This is worth raising unprompted rather than hiding. It demonstrates the difference between
implementing a specification and validating one: the unit tests written from the spec passed, and
the defect surfaced only when the system was run end-to-end and its actual outputs inspected. A
reviewer asking "how do you know your governance layer works?" gets a better answer from
"we found a contradiction in our own spec and resolved it explicitly" than from a green test suite.
