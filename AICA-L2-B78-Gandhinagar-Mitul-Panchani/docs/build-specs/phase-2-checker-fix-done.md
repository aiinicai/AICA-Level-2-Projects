PHASE 2 CORRECTION — the checker currently rejects every AI-inferred candidate. Fix it.

Phases 1-2 are built; 19/19 tests pass. But a behavioural probe found a defect that will break
Scenarios 3 and 4 later, so fix it now before building further.

## The bug

Run this and observe:

```
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'src');
from amg.extraction import propose_candidates
from amg.verifier import verify_candidate
for c in propose_candidates('I am strictly vegetarian.'):
    print(verify_candidate(c).approved, c.source_type, c.assertion_type, '|', c.content)"
```

The inferred candidate ("User likely avoids leather goods") is REJECTED with
`not_first_person`. Same for "User likely has professional accounting and finance expertise".

Consequence: no `ai_inferred` memory is ever written. That silently destroys:
- Scenario 3 (provenance / trust tiers) — nothing to show at the lower tier
- Scenario 4 (cascading erasure) — no dependent to cascade into
- Goal 1 of the spec (the two source types treated differently)

## Why it happens, and the correct resolution

ARCHITECTURE.md 3.1 says the checker "approves the write only if the classification genuinely looks
like a direct first-person statement." Read literally that makes inferences unwritable — but Goal 1,
Scenario 3 and Scenario 4 all require inferred memories. The spec is internally ambiguous here.

Resolve it this way, and document the reasoning in the code:

The first-person test exists to guard the **`user_stated`** path specifically. That is where the
write-path poisoning risk lives, because that path carries the claim "the user asserted this."
An `ai_inferred` candidate makes no such claim — it is explicitly marked AI-derived and lands at the
lowest trust tier pending confirmation. It therefore needs a **different** check, not an exemption.

## What to change

### 1. `src/amg/models.py`
`CandidateFact` must carry `source_type` (`user_stated` | `ai_inferred`) as a first-class field set
by the maker. An inferred candidate keeps the `assertion_type` of the statement it was derived from
(normally `direct_self_statement`) — `assertion_type` describes the ORIGINATING user statement,
`source_type` describes how THIS fact came to exist. Document that distinction in the model.

Add to `CheckerReasonCode`: `not_inference_shaped`, `overclaims_certainty`.

### 2. `src/amg/verifier.py` and both LLM providers — branch the checker on `source_type`

`check_candidate` must take `(content, assertion_type, source_type)` and apply:

**When `source_type == user_stated`** — unchanged, this is the security-critical path:
- must read as a genuine first-person self-statement
- must match the claimed `assertion_type`
- must not be instruction-shaped
- reject `hypothetical` / `third_party` / `quoted`

**When `source_type == ai_inferred`** — a different test:
- must NOT be instruction-shaped (same screen — this still applies)
- must be *inference-shaped*: third-person about the user and appropriately hedged
  ("User likely...", "User probably...", "User may..."). Reject with `not_inference_shaped` if it is
  phrased as a first-person user statement (an inference must never masquerade as something the
  user said — that is precisely the confusion the provenance model exists to prevent).
- must not overclaim certainty: reject with `overclaims_certainty` if it asserts flatly
  ("User is a vegan", "User works at X") with no hedge. An unhedged inference presented as fact is
  the failure mode this tier is designed to catch.
- must not be a bare restatement of its parent.

Update the Gemini prompt for the checker to describe both modes explicitly, and update the stub
provider's rule logic to match. **The isolation property is unchanged and non-negotiable**: the
checker still receives ONLY the candidate content, its assertion type, and now its source type.
It must still NEVER receive the original message. Keep the comment saying so.

### 3. `src/amg/providers/llm_stub.py`
Ensure the stub's inference table produces properly hedged, third-person text ("User likely avoids
leather goods" — good). Verify it does not emit unhedged inferences that its own checker would then
reject, and add a test proving maker and checker agree on the persona's two inferences.

### 4. `src/amg/provenance.py`
`tag()` must read `candidate.source_type` rather than deriving it solely from `assertion_type`.
`ai_inferred` + no `confirmed_at` -> `unconfirmed_inference` (lowest tier).

### 5. Tests — add to `tests/test_phase2.py`
- Persona 1.1 and 1.2 each yield BOTH an approved `user_stated` fact AND an approved
  `ai_inferred` fact. This is the regression test for this bug — it must fail against the current
  code and pass after the fix.
- An inference phrased in first person ("I avoid leather goods", `source_type=ai_inferred`) is
  REJECTED with `not_inference_shaped`.
- An unhedged inference ("User is a vegan", `source_type=ai_inferred`) is REJECTED with
  `overclaims_certainty`.
- An instruction-shaped candidate is still rejected under BOTH source types — the injection screen
  is not weakened by this change.
- All existing 6a/6b tests still pass unchanged.
- The checker-isolation test still passes: assert the original message text never reaches
  `check_candidate` under either branch.

## Constraints
- Do not weaken the `user_stated` checks in any way. This change adds a second mode; it must not
  loosen the first.
- Run `.venv/Scripts/python.exe -m pytest -q` — there is NO `python` on PATH, use the venv.

## Finish by
Running the full suite, pasting real output, and re-running the probe command at the top of this
file to show inferred candidates now pass. Then summarize what you changed.
