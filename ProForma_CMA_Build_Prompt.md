# Build Prompt — ProForma: Projected Financials, CMA Data & Schedule III Reporting Tool (India)

> **How to use this file.** Paste the whole thing into any AI coding tool (Claude Code, Cursor, Copilot, Codex, Gemini CLI, Windsurf, Aider…) as a single prompt. It is written as instructions to the coding agent, not as documentation. Work through it section by section; build the engine first and prove it with tests before any UI.

---

## 1. Your role and the product

You are building **ProForma** — a web application that a practising Chartered Accountant in India uses to prepare **provisional, estimated and projected financial statements, CMA data (RBI / Tandon Committee Forms I–VI) and Schedule III reports** for a bank loan proposal.

Today this work is done by hand in Excel. That is slow, the figures drift apart between the balance sheet, the notes and the CMA forms, bank norms (MPBF, DSCR, margins) are worked out manually, and every entity constitution needs a different format. Your job is to replace that spreadsheet with a tool where **one calculation engine is the single source of truth**, so the figure on screen is the figure that is saved and the figure that is exported.

Build it as a working, tested application — not a prototype, not mock data.

---

## 2. Non-negotiable engineering rules

Follow these absolutely. They are the whole design, not preferences.

1. **No binary floating point on money — ever.** Every monetary calculation flows through `decimal.js`, configured once at `precision: 34, rounding: ROUND_HALF_UP`. Provide a safe constructor `D(x)` at every boundary that collapses `''`, `null`, `undefined` and `NaN` to zero so a bad input can never poison a model. `number` is allowed only in stored input JSON; it is converted at the edge.
2. **The engine is pure.** No framework, no database, no DOM, no I/O, no `Date.now()` inside it. Pure functions over plain data. The same compiled engine must run unchanged in Node (server, CLI) and in the browser.
3. **Measurement is separate from presentation.** Rounding, unit scaling (Rupees / Thousands / Lakhs / Crores) and Indian digit grouping happen **only** in a presentation module. The engine always carries full-precision rupees.
4. **No hidden balancing plugs.** After everything else is computed there is exactly one residual figure, and it may go **only** to short-term bank borrowing or to cash, according to a stated funding policy. Capital, loans, reserves and profit are never quietly adjusted to force a balance sheet to close. Any remaining difference is *reported* as a funding gap or a critical validation issue.
5. **Imported figures are never mutated.** Adjustments to an imported trial balance are journal entries layered on top, so every figure still traces back to the source file. Show three columns: as imported, journal, as reported.
6. **Nothing lives only in the browser.** No `localStorage`, no state held only in a tab. Preferences and the working draft are read from the API on boot and autosaved back. Closing the laptop and opening the app elsewhere shows the same work.
7. **Never invent a figure you do not have.** Where a derivation is impossible (e.g. movements that need two balance sheets when the opening position is unknown), display a dash and say why — do not guess.
8. **Labels, ordering and note numbers are data**, held in JSON report templates, not hard-coded in components.

---

## 3. Technology stack

A TypeScript monorepo using **npm workspaces**, Node ≥ 20.

```
proforma-cma/
├── package.json                 # workspaces: packages/*, apps/*
├── packages/engine/             # the accounting core
├── apps/api/                    # Express + MongoDB
└── apps/web/                    # Vite + React UI
```

| Layer | Stack |
|---|---|
| **Engine** (`packages/engine`) | TypeScript (ESM, `"type": "module"`, compiled with `tsc` to `dist/`), **decimal.js** ^10, **Vitest** for tests. Zero runtime deps besides decimal.js. |
| **API** (`apps/api`) | Node 20+, **Express 5**, **Mongoose 8** → MongoDB (Atlas), `cors`, `dotenv`, `tsx` for dev watch. |
| **Web** (`apps/web`) | **React 19** + TypeScript, **Vite 6**, **ExcelJS** for `.xlsx` export, print CSS for PDF. No UI framework, no CSS library — hand-written CSS with design tokens. No state library; React context is enough. |

Root scripts to provide:

```json
{
  "scripts": {
    "build": "npm run build --workspaces --if-present",
    "test": "npm run test --workspaces --if-present",
    "typecheck": "npm run typecheck --workspaces --if-present",
    "dev": "npm run build -w @proforma/engine && (npm run dev:api & npm run dev:web)",
    "dev:api": "npm run dev -w @proforma/api",
    "dev:web": "npm run dev -w @proforma/web",
    "serve": "npm run build && npm start -w @proforma/api",
    "report": "npm run report -w @proforma/engine --",
    "tunnel": "cloudflared tunnel --url http://localhost:4000"
  }
}
```

`npm run serve` must build everything and have **the API serve the built UI from its own origin**, so the browser requests `/api` relative to whatever host it was loaded from — the same build works on localhost, on a LAN IP and behind a tunnel with nothing reconfigured. On startup, print every address it can be reached on (Local, LAN per interface, and `PUBLIC_URL` if set). `HOST` controls reach (`0.0.0.0` default, `127.0.0.1` to stay local). Support optional basic auth via `AUTH_USER` / `AUTH_PASS`, and honour `ALLOWED_HOSTS` for Vite in dev behind a tunnel.

---

## 4. Domain model (build these types first)

Put them in `packages/engine/src/types.ts`.

```ts
type PeriodStatus = 'Audited' | 'Provisional' | 'Estimated' | 'Projected';
type PeriodSource = 'model' | 'tb' | 'direct';   // projected | imported TB | keyed in
type ProfitAppropriation = 'capital' | 'reserves';
type FundingPolicy = 'wc' | 'cash' | 'stated' | 'ratio';
type LoanKind = 'term' | 'wcdl' | 'dropline' | 'od' | 'cc';
type RepaymentMethod = 'emi' | 'equal' | 'bullet';
```

Core interfaces: `Period`, `Entity`, `Opening` (the day-one balance sheet, line by line), `Assumptions`, `LoanInput`, `Scenario`, `TBState` (branches, rows, mapping, merge groups, elimination rules), `Adjustment`, `DirectEntry`, `FinancialModel` (the whole saved document), `ComputedYear`, `ComputeResult`.

**`Assumptions` must carry**, each as a per-year array where it varies: `baseSales`, `salesGrowth[]`, `gmPct[]`, `otherIncome[]`, `empPctSales[]`, `opexPctSales[]`, `opexFixed[]`, `depRate`, `capex[]`, `debtorDays[]`, `invDays[]`, `creditorDays[]`, `creditPct`, `taxRate[]`, `permanentDisallowance[]`, `exemptIncome[]`, `recogniseDeferredTax`, `recogniseLossDTA`, `drawings[]`, `dividends[]`, `dividendPaidPct[]`, `capitalIntro[]`, `otherCAd[]`, `otherCLd[]`, `investd[]`, `wcRate`, `minCash`, `fundingPolicy`, `statedWcBorrow[]`, `targetCurrentRatio[]`, `contributionPct`, plus disclosure policies (`receivableAgeing`, `payableAgeing`, `classification`).

**`ComputedYear` is the contract every report reads.** One object per period, all values `Decimal`. It must include at minimum:

- Flags/meta: `idx`, `label`, `status`, `actual?`, `openingKnown?`, `sourceLabel?`
- P&L: `sales, cogs, gp, oi, emp, opex, ebitda, dep, ebit, termInt, wcInt, interest, pbt, tax, pat`
- Tax: `deferredTax, deferredTaxBalance, dtl, dta, taxableIncome, lossCarryForward, bookDep, taxDep, disposalProceeds, profitOnSale`
- Working capital: `debtors, inventory, creditors, purchases, debtorDays, creditorDays, inventoryDays, otherCA, otherCL, invest, investCurrent, investNonCurrent, cash, creditSales`
- Funding: `closeFA, closeNW, closeCapital, closeReserves, termTotal, longTermDebt, curMat, wcBorrow, odBorrow, odInt, drawings, capIntro, fundingGap, suggestedWc, fundingBasis, targetCurrentRatio, termDraw, termPrin, openTLClose`
- Dividends: `dividendDeclared, dividendPaid, dividendPayable`
- Totals & cash flow: `curLiabExBank, totalCA, totalCL, totalAssets, totalEqLiab, bsDiff, cfo, cfi, cff, netCF, cfClose, dWC`
- CMA/assessment: `wcGap, nwc, minNWC1, mpbf1, minNWC2, mpbf2`
- Optional `nbfc?: NbfcYear` for a lender's loan book.

---

## 5. Engine modules to write (`packages/engine/src/`)

Create one module per concern and re-export everything from `index.ts`.

| Module | What it does |
|---|---|
| `decimal.ts` | decimal.js config, `D()`, `sum`, `minD`, `maxD`, `isZero`. |
| `types.ts` | every interface and union above. |
| `coa.ts` | the normalized **chart of accounts**: stable internal codes, each with `{ code, label, stmt: 'BS'\|'PL', grp: 'equity'\|'ncl'\|'cl'\|'nca'\|'ca'\|'income'\|'expense', note, sign: 'D'\|'C' }`. Codes such as `CAPITAL, RESERVES, TERM_LOAN, NCL_OTHER, DEFERRED_TAX_LIAB, WC_BANK, TRADE_PAYABLE, STATUTORY, CURR_MAT, PROVISION, DIVIDEND_PAYABLE, PPE, INTANGIBLE, INVESTMENT, DEPOSIT, DEFERRED_TAX_ASSET, INVENTORY, TRADE_RECEIVABLE, CASH_BANK, CA_OTHER, LOAN_BOOK, REVENUE, OTHER_INCOME, COGS_PURCHASE, COGS_STOCK, EMP_COST, FIN_COST, DEP_EXP, OTHER_EXP, TAX_EXP`. Everything downstream reads codes, never labels. |
| `entityTypes.ts` | registry of `proprietorship \| partnership \| llp \| aop_trust \| company \| company_indas \| nbfc`, each with its reporting framework, face-statement templates, where the year's profit is credited (`capital` vs `reserves`), and the owners'-funds heading. The user picks the type once and the whole pack follows. |
| `templates.ts` | JSON report-template engine. `TemplateRow = { t: 'h1'\|'h2'\|'line'\|'total'\|'grand'\|'sp', label?, codes?, note?, op?, role? }`, where `op` covers derived totals (`rev, exp, pbt, pat, zero`) and `role` covers constitution-dependent wording. Ship **eight templates**: NCE plus Schedule III Divisions I, II and III (BS and P&L each). Switching framework must change labels and grouping, never a figure. |
| `engine.ts` | `compute(model, scenarioName?): ComputeResult` — the orchestrator. Projects each year from the drivers, applies actuals where a period is sourced from books, runs loans/FAR/deferred tax/funding, and produces `ComputedYear[]`. |
| `loans.ts` | amortisation. A **term loan** amortises on a schedule (`emi`, `equal` principal, or `bullet`); a **CC/OD** revolves inside a limit and is entered as expected drawn %; a **dropline OD** does both. A loan may pre-date the window — take the drawdown date and pick the schedule up wherever it has got to. **A rate and an instalment imply each other** — accept either; if both are given, report the difference rather than silently resolving it. Split current maturities out of long-term debt. |
| `fixedAssets.ts` | Fixed Asset Register with **two parallel depreciation bases**: books on Schedule II (SLM or WDV over useful life to a residual value) and tax on **section 32 blocks** (WDV at prescribed rate, additions used < 180 days at half rate, sale consideration deducted from the block not cost, optional additional depreciation u/s 32(1)(iia) on new plant). Asset classes: `land, building, plant, computer, furniture, vehicles, intangible, cwip` — keep computers separate from plant. |
| `deferredTax.ts` | AS 22 / Ind AS 12 on the difference between the two bases. `book NBV > tax WDV → DTL`; unabsorbed loss → DTA recognised **only** when a virtual-certainty flag is set. Handle permanent differences (disallowance, exempt income) and loss carry-forward. |
| `policies.ts` | library of significant accounting policies — standard wording per choice (`basis, estimates, revenue, ppe, depreciation, intangible, inventory, investments, receivables, employee, borrowing, …`), each selectable, editable, droppable. Also **compose a brief** (entity, framework, figures, choices) as plain text the user copies to an assistant of their choice; a pasted reply can be split into the notes it names. **Send nothing anywhere** — no AI API calls from the app. |
| `schedules.ts` | **computed** Schedule III disclosures. Receivable buckets `['< 6 months','6 months – 1 year','1 – 2 years','2 – 3 years','> 3 years']` (MCA G.S.R. 207(E)); payable buckets `['< 1 year','1 – 2 years','2 – 3 years','> 3 years']` with unbilled and not-due shown separately. Age by days: turnover accrues evenly, so a balance of `d` days is the most recent `d` days of invoices — spread that window over the bucket edges (`[0, 182.5, 365, 730, 1095, ∞]` and `[0, 365, 730, 1095, ∞]`). Ageing must reconcile to the face of the balance sheet **by construction** and move when the assumptions move. |
| `facilities.ts` | the proposal. Facility kinds `cc, od, wcdl, dropline, term, bg, lc`; limits sanctioned today vs sought; the **margin** stipulated per class of current asset; the rate. Then the working-capital assessment a credit officer would do, ending at **MPBF on both Tandon methods** (Method I: 75% of working-capital gap; Method II: current assets less 25% of current assets as minimum NWC). Enhancement = sought − sanctioned. State plainly whether the ask is inside the norms. The **cash-credit rate prices all working-capital borrowing** in the model, so an overdraft costs what it actually costs and shows up in interest cover. |
| `cma.ts` | **CMA Forms I–VI** in the format banks ask for: I particulars of limits applied for; II operating statement; III analysis of the balance sheet; IV comparative current assets & current liabilities; V computation of MPBF; VI fund-flow statement. These are their own schedules with their own line items and arithmetic — compute them from the same `ComputedYear[]`, never style them off the P&L, so a bank reconciling Form III to the balance sheet finds them identical. Support `sect` blocks and `colhead` rows so schedules of different shapes can share one sheet. |
| `ratios.ts` | versioned ratio dictionary with lender-adjustable targets: `{ code, name, unit: 'x'\|'%'\|'d', cat: 'Liquidity'\|'Solvency'\|'Profitability'\|'Activity', good, dir, f }`. At minimum CR (1.33), QR (1.0), DE term (2.0 down), TOL/TNW (3.0 down), ICR (2.0), DSCR (1.5), GP% (25), EBITDA% (12), NP% (5), plus activity/turnover and days ratios. Return `null` rather than dividing by zero. |
| `dscr.ts` | debt-service coverage, computed **once** here and read by the ratio sheet, validation and the annexure — a working that disagreed with the headline would be worse than none. Cash available = PAT + depreciation + term interest (which is itself part of the obligation served). Interest on working-capital borrowing is neither added back nor served: a revolving limit is not amortised. |
| `nbfc.ts` | NBFC modelling (Schedule III Division III, Ind AS 109, RBI directions). No inventory, no trade receivable from sales: the asset is the **loan book**, income is interest earned on it, the dominant expense is credit loss. Disbursement and scheduled run-off drive the closing book; stage the book 1/2/3 with its own ECL rate per stage, so impairment is the movement in the provision plus write-offs and never a plug; Stage 3 is the NPA pool giving GNPA, NNPA and provision coverage; appropriate **20% of profit to the statutory reserve u/s 45-IC** of the RBI Act before anything is distributable; measure capital adequacy against risk-weighted assets. |
| `tally.ts` | trial-balance parsing, including **recognising a Tally export as one** with no preparation — see §7. Also `parseAmount` for `1,23,456.00 Cr` and bracketed negatives. |
| `consolidate.ts` | multi-unit consolidation — see §7. |
| `adjustments.ts` | journal entries over an imported TB — see §7. |
| `actuals.ts` | bind a TB (or keyed entries) to a period and treat it as history — see §7. |
| `rollover.ts` | base-year rollover: take the closing position of the year just gone as the opening of the next window. Modes `migrate` (carry assets, funds, loans mid-schedule, TB mapping memory and shifted assumptions) and `scratch` (keep only the entity and its mapping rules). Options: `fromYear`, `years`, `baseStatus`, `keepMapping`. |
| `master.ts` | `EntityMaster` (id, name, type, constitution, PAN, GSTIN, CIN, address, industry, FY convention) and the workspace holding many entities and their saved models. Plain data and pure functions only; `id` is an opaque string, never a DB handle, so the same shapes serialise to JSON or to Mongo documents. Include `WORKSPACE_VERSION`. |
| `validation.ts` | accounting-integrity checks returning `Issue[] = { sev: 'crit'\|'warn'\|'info', title, detail }`. Critical issues block "Final" status. Check at minimum: the opening balance sheet balances; every computed year's `bsDiff` is nil; the journal balances; cash never negative unless explicitly allowed (and then critical); funding gap; current ratio / DSCR / TOL-TNW below target; unmatched inter-unit balances; a stated instalment disagreeing with the stated rate; DTA recognised without the virtual-certainty flag. Each issue must name the figure and the fix. |
| `report.ts` | assemble the whole bound pack as data: cover, statements, comparative notes, asset register, tax reconciliation, Schedule III disclosures, CMA Forms I–VI, ratios, validation. |
| `format.ts` | the only place rounding and scaling live. `UNITS = { 1: 'Rupees', 1000: 'Thousands', 100000: 'Lakhs', 10000000: 'Crores' }`, `indianGroup()` producing `1,23,45,678`, decimals setting, negative/brackets convention, dash for not-applicable. |
| `index.ts` | re-export every module. |

Also ship `packages/engine/scripts/report.mjs` — a CLI that prints the whole pack to the terminal, taking the same flags as the UI tabs: `--types`, `--type company`, `--nbfc`, `--far`, `--schedules`, `--rollover`, `--tb --notes`, `--json`.

---

## 6. The funding decision (get this exactly right)

Assets less every other claim leaves one figure, and there are only two places it can go. `Assumptions.fundingPolicy` decides which, and the balance-sheet screen must show the working:

- **`wc` — bank borrowing takes the strain.** Borrowing is the funding need; cash sits at the stated minimum.
- **`cash` — cash is the residual.** Borrowing is held flat; any shortfall is reported as a funding gap.
- **`stated` — state the borrowing.** The suggestion is offered year by year and can be overridden. Cash is whatever that leaves, **including negative**, which is raised as a critical issue rather than absorbed.
- **`ratio` — hold a current ratio.** State the ratio and the borrowing follows from it.

Whichever is chosen, compute the funding need anyway and show it beside what was taken, so an override is a choice made against a stated alternative. The difference goes to cash and nowhere else, and print the resulting current ratio under it.

For the `ratio` policy, tell the truth rather than faking it: cash and borrowing both rise one-for-one with a drawing, so **borrowing moves the current ratio towards 1** and can never raise it above what the business already carries; and the range is bounded below by cash reaching nil. If the requested ratio is outside that range, say so, quote the ratio the business actually supports at its own funding need, and note that only the working-capital cycle can do better.

---

## 7. Trial balance import, adjustment and actuals

**Import.** Read `.xlsx`, `.csv`, `.tsv` and plain text, by file picker, drag-and-drop onto the source box, or direct paste. **Refuse the old binary `.xls`** with a clear message rather than parsing it wrongly.

**Recognise a Tally export as one, with no preparation.** Detect and handle: the company name, report title and period above the table; the two-row header where Opening, Transactions and Closing each span a Debit/Credit pair; amounts like `1,23,456.00 Cr` and bracketed negatives; group lines carrying the total of the ledgers indented beneath them; and the Grand Total. **Drop the group lines** — keeping both them and their ledgers double-counts every figure — but **carry their names onto the ledgers**, which is what the mapping rules need. Report everything read, including what was dropped and why.

**Mapping.** Map each ledger to a COA code with learned rules; remember the mapping per entity so next year's import is mostly automatic. Show a mapping table with what the file said, what the journal passed, and what the statements read.

**Merging ledgers.** Ticking two or more ledgers presents them as one line. Net nothing away and keep the members, so a merge is exactly reversible. The same grouping appears in Notes to Accounts, where it can also be created and split — both write to the same trial balance.

**More than one unit.** Allow a TB per branch. On consolidation the balances units hold against each other are **set off, not added**: the reciprocal current accounts each pair keeps, and the ledgers carrying goods between them. Detect both by name, list them with amounts, and let any be switched off or capped where only part of a ledger is internal (`EliminationKind = 'reciprocal' | 'trading' | 'manual'`). The matched amount comes off the debit and credit side together so the consolidated TB still tallies. **What does not match is not absorbed** — it stands as a stated in-transit balance and is reported, because an unmatched inter-unit account is a real difference for someone to reconcile.

**Adjustments.** A TB pulled before the accounts are closed is rarely final, so take depreciation, the tax provision, interest accrued, the closing stock entry and reclassifications as **journal entries, not edits**. Standard entries write both legs; the journal must balance before it is applied; nothing touches the imported figures. An entry may name a ledger the TB does not carry — passing depreciation on a TB that has none has to mean exactly that — so create the ledger and classify it by the code on the entry, flagging it as introduced.

**Period sources.** Each period on the Periods screen carries a source: **Projected** from the drivers; **Imported** with a TB bound to it; **Keyed in** for finalised accounts entered against the same COA note by note (a keyed balance sheet is post-closing, so profit is already in reserves and nothing is transferred). Imported and keyed are both *actual*: assumptions are **not** applied to them (grey those cells out on the Assumptions screen), and the projection continues from the actual rather than from a keyed base-sales figure, carrying the deferred tax the books actually show.

Where the **first** period is actual and the file carried an opening-balance column, read day one from the file and do not use the Opening Balance Sheet screen at all — two statements of the same thing can only disagree, so the file wins. Where the first period is actual and **nothing** states the position at the start of it, set `openingKnown: false` and show the movements two balance sheets would have forced (capex, owners' account, borrowings, cash flow) as a **dash**, not derived from nothing.

A few figures a TB cannot state directly are derived from it and the previous position, and each must be labelled as a derivation, not an assumption: the split of interest between term and working-capital borrowing, capital expenditure, the movement on the owners' account, and the movement in borrowings.

Ship two worked examples openable from a link — `?demo=tally` (first period stated by a Tally import) and `?demo=branches` (two units to consolidate) — plus a "Load a two-unit example" button on the import screen.

---

## 8. API (`apps/api`)

Express 5 + Mongoose 8. **The API will not start without a reachable database and has no local fallback** — a fallback would mean an afternoon's work going somewhere other than the database without anyone noticing. If the connection fails, say so and name the likely cause (IP allowlist).

`.env`: `MONGODB_URI`, `MONGODB_DB`, `PORT` (4000), `HOST`, `PUBLIC_URL`, `AUTH_USER`, `AUTH_PASS`, `ALLOWED_HOSTS`.

Four collections, one shape each:

| collection | holds |
|---|---|
| `entities` | the entity master — captured once, reused every year |
| `models` | filed models, keyed by entity and base year |
| `preferences` | display unit, decimals, theme, last view, last entity |
| `drafts` | the live working copy, autosaved as it is edited |

A draft is the model on screen; **filing it under an entity is a deliberate act**, so autosave never rewrites something already filed. Provide "Discard working draft", which clears the draft and leaves filed models untouched.

Routes (mount under `/api`):

```
GET    /health
POST   /compute                 → run the engine, return ComputeResult
POST   /compute/statements
POST   /compute/schedules
POST   /compute/notes
GET    /entity-types
GET    /entities                POST /entities
GET    /entities/:id            PUT /entities/:id        DELETE /entities/:id
POST   /entities/:id/rollover
GET    /models                  POST /models
GET    /models/:id              DELETE /models/:id
GET    /models/seed/:kind       → demo models
GET    /workspace               PUT /workspace/prefs
PUT    /workspace/draft         DELETE /workspace/draft
```

Serialise money at the persistence/API boundary (string or `Decimal128`), never as a JS `number`. Provide `npm run migrate -w @proforma/api` to lift any legacy JSON file store into Mongo, skipping ids the database already holds and renaming the file when done.

---

## 9. Web UI (`apps/web`)

React 19 + Vite 6, TypeScript strict. Left-hand navigation with these screens, in this order:

`entities` · `entity` · `periods` · `tb` (Trial Balance & Mapping) · `opening` (Opening Balance Sheet) · `assumptions` · `loans` (Borrowings) · `facilities` (Facilities & Working Capital) · `far` (Fixed Assets) · `nbfc` · `statements` · `notes` (Notes to Accounts) · `policies` (Policies & Narrative) · `schedules` (Schedule III) · `tax` · `cma` · `ratios` · `validation` · `export` (Export & Backup)

Requirements:

- Dense, spreadsheet-like grids; keyboard-navigable numeric cells; per-year columns.
- A global toolbar for display unit, decimals and theme (light/dark), applied through `format.ts` only.
- Autosave the draft to the API on change (debounced); show save state.
- Inert/greyed cells for periods that are actual.
- Every screen that shows a derived figure shows its working — especially the balance sheet's funding decision.
- The validation screen groups issues by severity and links to the screen that fixes each.
- Show a dash, never a zero or a guess, for figures that cannot be derived.

---

## 10. Export: the printable pack

**Export & Backup → Printable pack** builds the whole bound pack: cover, statements, comparative notes, asset register, tax reconciliation, Schedule III disclosures, CMA Forms I–VI, ratios and validation.

- **PDF** — printed from the browser via print CSS. **A4 landscape**, running header, column headers repeated on every page, rows kept off page breaks. Text stays **selectable and searchable** — never rasterise.
- **Excel** (ExcelJS) — one sheet per section plus a cover, frozen headers, **Indian digit grouping** (`1,23,45,678.00`), print titles and fit-to-width already set. Write figures as **numbers**, so the recipient can still calculate with them.

By default bind the notes as **one** annexure, the register as **one** schedule and the Schedule III disclosures as **one** — a single spreadsheet tab each, so the pack reads down the page instead of putting every note on its own sheet. Offer an "unbind notes & schedules" option for a section per note.

Let the user tick which periods the pack is bound for (a renewal often wants two historical years and one projected where a fresh proposal wants five). The selection applies to **every section at once**, so the statements, notes, schedules and CMA forms can never end up on different columns.

Provide `npm run verify:xlsx -w @proforma/web -- /tmp/pack.xlsx` to prove a generated workbook actually opens.

---

## 11. Testing and verification

Use Vitest in the engine, with a test file per module: `decimal, coa, engine, loans, facilities, dscr, dividends, deferredTax, fixedAssets, schedules, policies, templates, entityTypes, master, rollover, actuals, adjustments, tally, consolidate, cma, nbfc, report, validation`. Aim for **400+ assertions**; treat each of these as a required test:

1. Every computed year's `bsDiff` is exactly nil, for all four funding policies and all seven entity types.
2. Switching report template changes labels only — never a figure.
3. A Tally export parses to the same balances as a clean CSV of the same data; group lines are dropped and their names carried down; the TB still tallies.
4. Consolidation of two units sets off reciprocals on both sides and leaves unmatched amounts stated, not absorbed.
5. A journal that does not balance is refused; an applied journal leaves imported figures untouched.
6. Loan: rate→instalment and instalment→rate agree; a mid-schedule loan picks up at the right outstanding; current maturities split correctly.
7. FAR: book and tax depreciation diverge as expected (half-rate additions, sale off the block), and deferred tax equals the tax effect of the timing difference.
8. Ageing schedules sum exactly to the balance-sheet figure and shift when debtor/creditor days change.
9. MPBF Method I and Method II on a worked example match hand-computed figures; the enhancement and the in/out-of-norms verdict are right.
10. NBFC: staged ECL movement plus write-offs equals the impairment charge; the 45-IC statutory reserve is appropriated before distribution.
11. DSCR from `dscr.ts` equals the figure on the ratio sheet, in validation and in the annexure.
12. Rollover: closing position becomes the next window's opening; mapping memory survives `migrate` and `scratch` keeps only the entity.
13. `indianGroup()` produces `1,23,45,678`; no rounding happens outside `format.ts`.

Also provide `npm run typecheck` across engine, api and web, and `npm run build` for all three.

---

## 12. Deliverables and order of work

Build in this sequence, and do not start a step before the previous one's tests pass.

1. Monorepo scaffold, workspaces, TypeScript configs, lint/typecheck/test scripts.
2. `decimal.ts`, `types.ts`, `coa.ts`, `format.ts` + tests.
3. `entityTypes.ts`, `templates.ts` (all eight) + tests.
4. `loans.ts`, `fixedAssets.ts`, `deferredTax.ts` + tests.
5. `engine.ts` with all four funding policies + the balance-sheet-ties tests.
6. `ratios.ts`, `dscr.ts`, `validation.ts` + tests.
7. `schedules.ts`, `facilities.ts`, `cma.ts` + tests.
8. `tally.ts`, `adjustments.ts`, `consolidate.ts`, `actuals.ts` + tests.
9. `nbfc.ts`, `policies.ts`, `master.ts`, `rollover.ts`, `report.ts` + tests; the CLI report script.
10. `apps/api` — Mongo models, routes, auth, static serving of the built UI, address printing, migrate script.
11. `apps/web` — all nineteen screens, autosave, display controls, demos.
12. Export — print CSS pack and the ExcelJS workbook, plus the xlsx verifier.
13. A `README.md` covering: layout, running it (`npm run dev`), serving it to others (`npm run serve`, `HOST`, `PUBLIC_URL`, tunnel vs port forwarding vs VPN), the database and its four collections, the export pack, importing a trial balance, multi-unit consolidation, adjustments, binding a TB to a period, the proposal and facilities, the funding decision, period sources, policies and narrative, verification commands, and a closing "what the engine guarantees" section.

---

## 13. What the finished engine must guarantee (state these in the README and hold to them)

- **No binary floating point on money.** Every calculation goes through decimal.js at 34 significant digits.
- **No hidden balancing plugs.** One residual figure, placeable only to short-term borrowing or cash. Capital, loans and profit are never quietly adjusted to make a balance sheet close.
- **Presentation is separate from measurement.** Eight report templates read the same normalized balances, so switching framework changes labels and grouping, never a figure.
- **Two depreciation bases.** Schedule II in the books, section 32 blocks for tax — with deferred tax measured on the difference.
- **Disclosures are computed.** Receivable and payable ageing derive from the collection and payment periods, so they reconcile to the balance sheet by construction and move when the assumptions move.
- **Every figure traces to its source.** An imported figure traces to the file; an adjusted figure traces to a journal entry; a projected figure traces to a stated driver.
