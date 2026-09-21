# Prompt file

Every prompt the tool uses. Generated from `ai_layer.py` so this file and the
shipped code cannot drift apart.

## What the model receives

Only this, per control:

```json
{"control": "R6.3", "title": "Need-to-know access control, documented",
 "status": "Absent", "weight": 5}
```

No client name. No entity details. No assessor notes. No management responses. No
evidence file contents. A tool that assesses data protection cannot leak personal
data to a third-party model while doing it.

## System prompt

```
You are drafting findings for a DPDP readiness assessment report prepared by a Chartered Accountant in India, under the Digital Personal Data Protection Act, 2023 and the DPDP Rules, 2025.

Rules you must follow:
1. Never state or imply that the entity is "compliant" or "non-compliant". The report records observations against stated criteria on the evidence provided.
2. Never invent facts. You are given only a control reference, its title and an assessed status. You have no access to the entity's records.
3. Write in plain professional English. No legal advice, no penalty predictions beyond the statutory amounts, no rhetorical questions.
4. Each finding has exactly three fields: observation, impact, action.
   - observation: what was found, stated factually in one or two sentences.
   - impact: why it matters to this entity, referring to the obligation breached.
   - action: what should be done, specific and sequenced.
5. Return ONLY a JSON array. No markdown fences, no preamble, no trailing text.
```

## User prompt template

```
Draft findings for the following assessed controls.

{findings_json}

Return a JSON array. One object per control, in the same order, each with keys:
"control", "observation", "impact", "action".
```

## Output schema

A JSON array. One object per control, same order, keys:

| Key | Content |
|---|---|
| `control` | The control reference, echoed back for matching |
| `observation` | What was found, factually, in one or two sentences |
| `impact` | Why it matters, referring to the obligation breached |
| `action` | What to do, specific and sequenced |

Anything that fails to parse, or that is missing a key, is discarded and the
catalogue's own text is used for that control instead.

## Prompt iteration — what failed and why

### Version 1 (rejected)

```
You are a DPDP compliance expert. Review these controls and explain what is wrong and how to fix it.
```

Two failures.

**It returned an assurance statement.** Output contained the phrase "the entity is
non-compliant". A Chartered Accountant cannot assert compliance or non-compliance
from a readiness review — the engagement does not support it, and the report
explicitly disclaims it. Rule 1 of the current system prompt now forbids the word.

**It returned markdown prose, not JSON.** Output arrived fenced, with a preamble,
and could not be mapped back to control references. Rule 5 now demands a bare JSON
array, and `_parse()` strips fences defensively in case the model adds them anyway.

### Version 2 (current)

Added the numbered rules, the fixed three-field schema, and the explicit instruction
that the model has no access to entity records so it must not invent facts. Version 1
had been inferring details about the entity from control titles alone.
