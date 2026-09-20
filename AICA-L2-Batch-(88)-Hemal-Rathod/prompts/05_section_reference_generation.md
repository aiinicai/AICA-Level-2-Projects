# 05 — Section reference card generation

## Objective

Build a reference card for each provision relied on, keeping **statutory text**,
**professional interpretation** and **application to the facts** in three separate,
separately-labelled blocks.

Implemented in `generateLegalReferences()` in `app/js/reasoning.js`.

## Inputs

1. The provision key (e.g. `44AB(a)`).
2. Verified statutory text, **if and only if** a CA has entered it in `statutoryTexts`.
3. The configured parameters for that provision.
4. The evaluated test record for the present case.

## Instructions

```
Produce a reference card with exactly these blocks, in this order:

  provision              the section reference
  title                  short description of what the limb does
  applicability          who and what the provision applies to
  statutoryText          VERBATIM text, or null
  practicalInterpretation the firm's plain-language reading
  applicationToFacts     how the entered figures meet or fail the condition
  conclusion             applicable / not applicable / could not be concluded on this limb

ABSOLUTE RULES

1. statutoryText is either the exact words supplied to you, or null. NEVER paraphrase into
   this field. NEVER reconstruct it from memory. If no text was supplied, emit null and the
   renderer will show an explicit "not reproduced" state telling the reader to read the
   bare Act. That state is the correct output, not a failure.

2. practicalInterpretation is the firm's own explanation and is ALWAYS rendered under the
   label "Simplified professional explanation". Write it so that label is honest: explain
   the mechanism, do not assert a settled legal position.

3. applicationToFacts quotes only figures present in the test record.

4. Never merge blocks. A reader must be able to tell, at a glance, which sentences are the
   Act's words and which are the firm's.

5. Where the provision admits more than one reading on a point the engine relies on, say so
   in practicalInterpretation and cross-reference documentation/limitations.md.
```

## Expected output

An array of card objects. The section 44AA card is always included with conclusion
"Not evaluated — determine separately".

## Validation requirements

- [ ] **Every `statutoryText` is either verbatim-from-source or null.** This is the single
      most important check in the project. A paraphrase in this field reads as the Act and
      is not.
- [ ] Each card shows the "Simplified professional explanation" label on the interpretation
      block.
- [ ] Parameters quoted match `ruleset.js`.
- [ ] The section 44AA card is present and marked not evaluated.

## Limitations

- In this distribution every `statutoryText` is null by design. The cards are structurally
  complete and legally incomplete, and they say so on their face.
- The interpretation blocks are the firm's, drafted with AI assistance and edited. They
  carry no authority and the label says as much.
