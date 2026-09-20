# Demonstration script

Eight to ten minutes, twelve beats. Beats 07, 08 and 11 matter most.

**Before you start:** switch to **Executive Bright** if you are projecting. Open the
Overview panel. Use only the synthetic sample cases — never a real client file.

---

### 01 · The problem (45s)

> "Whether tax audit applies under section 44AB looks like a threshold test. It is not. It
> turns on turnover, on the cash split of receipts and payments, on whether a presumptive
> scheme is available and actually declared, on whether it was used in an earlier year, on
> the profit declared against a deemed rate, on the constitution, and on the basic exemption.
>
> And the law moved in 2023. Since AY 2024-25, a person who declares under section 44AD or
> 44ADA is outside section 44AB altogether. Many checklists still don't reflect that."

### 02 · The manual process (30s)

> "Today this is done from memory, and the conclusion goes on the file as two words. If a
> notice arrives two years later, there is no record of which limbs were examined or on what
> figures."

### 03 · The solution (30s)

Overview panel. Point at the green strip.

> "This determines applicability, explains it limb by limb with the section, and produces
> the working paper. It runs entirely in the browser — no server, no AI call at run time.
>
> The legal basis is stated at the top: the thresholds were checked against the Finance Act
> 2023 as published in the Gazette, and I confirmed that the 2024 and 2025 Finance Acts did
> not amend these sections."

### 04 · Enter the facts — live (75s)

Click **Reset**. Go to Financial Inputs. Type: turnover **1,00,00,000**; receipts, payments
and cash **0**; profit **5,00,000**; total income **5,00,000**.

> "Watch what it asks for. Only the fields marked *Needed* are required on these facts. At
> ₹1 crore of turnover the cash split cannot change the answer, so it doesn't insist on it."

Go to Decision.

> "It doesn't say 'cannot conclude'. It says one more answer is needed — whether the year
> falls in a five-year bar under section 44AD(4) — and why that matters."

Click **Go to**. Answer **No**.

> "Now profit is 5% — below the 6% floor of the deemed income, and income exceeds ₹4 lakh. So
> it asks the question the law actually turns on: was section 44AD used in the last five
> years?"

Answer **No** → NOT APPLICABLE. Then change it to **Yes** → APPLICABLE under s. 44AB(e).

> "Same turnover, same profit. One fact — whether the scheme was used before — decides
> whether this client needs an audit. That is the question a turnover checklist never asks."

### 05 · Cash tests and limits (45s)

Load **Case 3 — Firm relying on the ₹10 crore limit**. Legal Tests panel.

> "Cash received 3.5%, cash paid 3.4% — both within 5%, so the limit is ₹10 crore, not ₹1
> crore. Headroom ₹1.8 crore. The meters show each figure against its statutory limit."

### 06 · The decision and its reasons (45s)

Decision panel.

> "Not applicable — and reasoned. It lists each limb it tested and why it's clear. It also
> says, every time, that section 44AA — books of account — is separate and not evaluated."

### 07 · The 2023 change most people miss (60s)

Load **Case 4 — Trader at ₹2.5 crore declaring under s. 44AD**.

> "Turnover ₹2.5 crore. Cash payments are 12%, so the section 44AB(a) limit is ₹1 crore —
> crossed. The old answer is: audit.
>
> But cash receipts are within 5% of turnover, so the 44AD ceiling is ₹3 crore. Profit meets
> the deemed income. And income is declared under section 44AD(1). Under the first proviso,
> substituted by the Finance Act 2023, section 44AB does not apply at all."

Open **Section References** → first proviso card.

> "That's the Gazette text, quoted with its source. Not a paraphrase."

### 08 · The error this tool used to make (60s)

Load **Case 8 — Professional declaring below 50%, first year**.

> "A lawyer, ₹38 lakh receipts, profit 39%. First year declaring below 50%.
>
> My first version of this tool said *not applicable* — because it required the professional
> to have used 44ADA in an earlier year. Section 44AB(d) contains no such condition. When I
> checked the statute, that was wrong. The correct answer is: audit applies.
>
> That's why the verification record in the project lists every error found and a test for
> each one."

### 09 · The five-year bar (30s)

Load **Case 10 — Firm within a s. 44AD(4) bar**.

> "Turnover only ₹75 lakh. But the firm is barred under 44AD(4), and a firm has no basic
> exemption. Audit applies — whatever the turnover."

### 10 · The working paper (45s)

Working Paper panel. Generate the detailed PDF and the one-page summary.

> "Detailed working paper for the file — ten sections, statutory text, sign-off. A one-page
> summary for the partner or client. Word, if it needs editing. And a JSON audit trail. All
> four from one model, so they cannot disagree."

### 11 · AI and human review (75s)

**Do not rush this.**

> "AI helped build this: structuring the logic, drafting explanations, the document templates.
> The prompt library is in the project.
>
> AI was not trusted for the law. I read the Finance Act 2023 in the Gazette, searched the
> 2024 and 2025 Finance Acts in full, and checked the e-filing portal for which Act governs
> this year. That check found three errors in my first version — two of which could have
> told a client no audit was needed when it was. They are listed, fixed, and tested.
>
> The engine is deterministic and makes no AI call. Where it takes a position — the
> five-year bar — it takes the conservative one and says so. The final conclusion and the
> filing stay with the Chartered Accountant."

### 12 · Close (30s)

> "Next: my own sign-off on the verification record, a check for any CBDT due-date extension,
> and — from AY 2027-28 — a new engine for the Income-tax Act, 2025. Thank you."

---

## Short version (3 minutes)

Beats 04, 07, 08, 11 — your own data walked through live, the 2023 proviso, the error found
by verification, and the AI boundary.

## Questions to expect

**"Is this in line with the Act for FY 2025-26?"**
> "It is built on the Finance Act 2023 Gazette text and I confirmed there has been no
> amendment since. The research record is in `legal/sources.md`. The one interpretive choice
> — the five-year bar — follows the conservative reading reported from the ICAI Guidance Note."

**"What if the client's facts are unusual?"**
> "It asks for the facts the law turns on — residential status, exclusions like commission or
> agency, the profession, the bar. For derivatives it takes turnover computed per the ICAI
> Guidance Note."

**"Why no AI in the app itself?"**
> "A legal determination that varies between runs is not a determination, and client figures
> would have to leave the machine."
