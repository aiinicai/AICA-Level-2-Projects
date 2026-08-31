# Gate D — parallel run against three real clients

Review and Sign-Off Protocol, Gate D. Run three completed FY 2024-25 audits
through AuditCraft and compare its output against what the firm actually
issued and signed.

This is the only test that can tell you whether the tool is fit to sign
behind. 664 automated tests prove the machinery works; **none of them knows
what a correct audit report says.** Four defects this session were invisible
to the whole suite and obvious within seconds of opening a page.

---

## Before you start: choose the three clients deliberately

**Three similar clean private companies would prove almost nothing.** Most of
the wording would never render. Of 503 clause bodies in the repository, 357
are mine rather than adapted from your precedents, and **91 clauses have an
exception path that only appears when something is wrong.** A file where
everything is nil exercises perhaps a third of the text.

Pick three that differ in the things that change the output:

| | Pick a client where | Why it matters |
|---|---|---|
| **A** | Clean opinion, CARO applies, IFC exempt, private company | Your commonest file. If this is wrong, it is wrong on most engagements. |
| **B** | **IFC reporting applies** — turnover ≥ ₹50 cr or borrowings ≥ ₹25 cr | The single decision spanning three documents. Also proves the threshold. |
| **C** | **Something was not nil** — a qualification, a CARO exception, disputed statutory dues, a director change, a fraud report, or a going-concern uncertainty | Where my authoring is concentrated. The precedents are all clean files, so every exception body is mine. |

**Do not pick a client the tool can no longer report on.** Decisions 26 and 27
hard-coded eleven answers, so all three clients must be **private limited
companies with no branch office**, with no director disqualified under section
164(2), proper books of account kept, all information and explanations obtained,
and nothing adverse on the maintenance of accounts. If a candidate fails any of
those, AuditCraft will produce a report that is wrong and silent about it.

If you cannot find a client for C, pick the nearest and **answer the exception
options anyway** on a scratch copy. Wording that never renders never gets read.

- [ ] Client A chosen: ________________  FY ________
- [ ] Client B chosen: ________________  FY ________
- [ ] Client C chosen: ________________  FY ________
- [ ] At least one of the three is **not** a clean nil file

---

## Setup, once

- [ ] `python scripts/seed.py` has been run and the firm record at
      **Admin → Firm & Partners** carries your real name, FRN, address and
      signing partner
- [ ] The firm name holds **the name only** — every signature block adds
      "Chartered Accountants" on its own line
- [ ] Each of the three clients created at **Clients → New client**, with
      the financial figures for the year under audit
- [ ] Take a backup before you start: `python scripts/backup.py`

---

## Per client: run this list against the signed file

Repeat for A, B and C. Work from the signed PDF, not from memory.

### 1. Applicability — before reading a word of prose

Wrong applicability does not produce wrong wording. It produces **a document
that should never have existed, or omits one that should have.** Nothing in
the tool will flag it.

- [ ] Open **Applicability** and compare every flag against what the firm
      actually did that year
- [ ] CARO — applied where you applied it, absent where you did not
- [ ] IFC — the annexure is produced only if you issued one
- [ ] CSR, internal audit, secretarial audit, KAM, CFS all match
- [ ] Any flag you had to override: the reason is recorded and reads sensibly

> Confirmed 17 Aug 2026, but never yet tested against a real company. The two
> easiest to get wrong: CARO's private exemption is **"not exceeding" (≤)**
> while the IFC exemption is strictly **"less than" (<)** — a company with
> turnover of exactly ₹50 crore is **not** IFC-exempt; and secretarial audit
> reaches **private** companies at borrowings ≥ ₹100 crore.

### 2. Independent Auditor's Report

- [ ] **The section 143(3) lettering.** Clean file now runs **(a) to (g)** —
      one letter short of your own format, because decisions 26 and 27 removed
      the paragraphs at (c) and (h) and the letters close up over them. Count
      them, and satisfy yourself the run reads correctly with the two gone.
- [ ] The Opinion and Basis for Opinion paragraphs read as yours
- [ ] Where the opinion was modified: the **description of the matter actually
      appears** under the Basis heading, not just the heading
- [ ] Rule 11 renders as **(1) to (6)** under your paragraph (g), with **no
      (d)**
- [ ] Section 197(16) is the last lettered paragraph
- [ ] Signature block: firm, FRN, partner, membership number, UDIN, place,
      date — and **"Chartered Accountants" appears once**

### 3. CARO 2020 annexure

- [ ] All 21 clauses present, numbered (i) to (xxi), **nothing skipped after
      (vii)** — the prototype's defect
- [ ] (i)(a) splits into (A) and (B); (iii)(a) splits into (A) and (B)
- [ ] Every clause you reported an exception on says what you said
- [ ] **(xvi)(b)** — I did not reproduce your annexure's wording here. Yours
      repeats the (xvi)(a) 45-IA text; mine asks the different question the
      Order actually asks. Read it and decide.
- [ ] **(ix)(e) and (ix)(f)** — mine say "subsidiaries, joint ventures and
      associates" where yours said subsidiaries only

### 4. Annexure B — internal financial controls (client B)

- [ ] The phrase is **"with reference to financial statements"** throughout —
      your precedent used the pre-2017 "over financial reporting"
- [ ] The only exception is the ICAI **Guidance Note title**, cited verbatim
- [ ] The report paragraph, the annexure heading and the engagement letter all
      say the same thing

### 5. Management Representation Letter

- [ ] Addressed to the firm, signed by a named Director and the CFO
- [ ] Every representation matches what the client actually gave you
- [ ] **No client's facts from another file appear anywhere** — the precedent
      was a live client file and everything specific to it was stripped
- [ ] The audit trail representation appears only for FY 2023-24 onwards

### 6. Board's Report

- [ ] **No Form MGT-9.** Omitted by G.S.R. 159(E) dated 5 March 2021 —
      your FY 2023-24 precedent still annexed it
- [ ] The **annual return web address** paragraph appears in its place
- [ ] **POSH**, **Maternity Benefit Act** and **Secretarial Standards**
      statements are present — none was in your precedent
- [ ] Directors appointed and ceased are **computed from the register** and
      match the file. Correct the client's director register, not the report.
- [ ] Directors' Responsibility Statement: the internal-controls limb appears
      only if it should

### 7. Engagement letter

- [ ] Reads as a letter your firm would send
- [ ] "We" throughout, and the terms are ICAI's current ones
- [ ] The limitation-on-damages and jurisdiction clauses are acceptable to the
      firm

### 8. Numbers and dates, everywhere

- [ ] Every amount is grouped **₹42,60,000**, never `4260000.00`
- [ ] Every date reads **31st March, 2025**, never `2025-03-31`
- [ ] Amounts agree with the signed financial statements

---

## After all three

- [ ] **Roll one forward** to the next year. Confirm the financial figures come
      through **blank**, and that carried-forward answers arrive unconfirmed
      and block export until reviewed.
- [ ] Export a document and reprint it from the snapshot. The two must be
      **byte-identical**.
- [ ] Nothing in any document names another client.

---

## Recording the result

For each difference found, note which is right — the tool or the signed file.
**Not every difference is a defect in the tool.** Several were deliberate
corrections to the precedents and are listed in `docs/GATE_A_DECISIONS.md`;
one, the MGT-9 annexure, is a defect in the firm's own template.

| # | Client | Document | What differs | Tool wrong / File wrong / By design |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

**Gate D passes when a document produced by AuditCraft could be signed
without amendment.** Not when it is close.

- [ ] Client A complete
- [ ] Client B complete
- [ ] Client C complete
- [ ] Every difference resolved or recorded

Signed: ______________________  Date: ____________

---

## If something is wrong

Record it rather than editing a rendered document. A clause corrected in
`content/` is corrected for every engagement; a document corrected by hand is
corrected once and wrong again next year — which is the failure this tool
exists to remove.
