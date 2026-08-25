# Decision 002 — `contradiction_min_confidence` set to 0.70, not 0.95

**Date:** 2026-08-23
**Status:** Accepted, pending live validation at Phase 7
**Resolves:** ARCHITECTURE.md §9 open question — *"Exact similarity/entailment threshold for what
counts as a contradiction — You, empirically, once Phase 4 is running."*

## The observed values

With the offline stub provider, on the persona's Scenario 2 / 2b pair:

| Case | `contradicts` | `confidence` |
|---|---|---|
| Scenario 2 — Northwind → Silverline (genuine contradiction) | `True` | **0.96** |
| Scenario 2b — "our office is in Peelamedu" (additive detail) | `False` | **0.94** |

Codex, having built the stub, recommended **0.95** — the midpoint that cleanly separates those two
numbers. That is a correct reading of the data it had, and it is still the wrong choice.

## Why 0.95 was rejected

**1. It is tuned to synthetic values and will not survive the provider swap.**
0.96 and 0.94 are constants the rule-based stub emits, not measurements of anything. Gemini's
entailment confidence has a different distribution entirely — a clear employer contradiction could
plausibly return 0.85. At a 0.95 threshold that gets rejected, so Scenario 2 fails **live** while
passing every offline test. A threshold with a 0.02 margin calibrated against a provider you are not
demoing on is a demo-day failure waiting to happen.

**2. The threshold is not what separates 2 from 2b anyway.**
Look at the boolean column: the stub already returns `contradicts=False` for the additive case. Since
a contradiction requires `contradicts is True` **AND** `confidence >= threshold`, Scenario 2b is
excluded by the boolean regardless of where the threshold sits. Tightening it to 0.95 therefore buys
no additional precision — it only adds false-negative risk on the recall side.

**3. Asymmetric cost.** A false negative (missing a real contradiction) means the system silently
overwrites reality — the exact failure this project exists to prevent, and the worst thing that
could happen during a defense. A false positive merely flags something for human resolution, which
is a designed, visible workflow. When the costs are asymmetric, bias the threshold toward recall.

## The decision

`contradiction_min_confidence = 0.70`.

High enough to discard genuinely low-confidence noise, low enough to survive a provider whose
confidence calibration differs from the stub's. All 57 tests pass unchanged at this value, which
confirms the suite never depended on the narrow margin.

## Required follow-up (do not skip)

At Phase 7's single controlled live-validation run, record the **actual** confidence values Gemini
returns for the 2 / 2b pair and re-tune if warranted. Until that measurement exists, 0.70 is a
defensive default, not an empirical result — and it should be described that way in the defense.

An honest answer to "how did you pick that number?" is:
*"Offline it could be anything between 0.94 and 0.96. We deliberately set it wide because the value
that matters is the one measured against the provider we actually ship, and we bias toward catching
contradictions rather than missing them."*
