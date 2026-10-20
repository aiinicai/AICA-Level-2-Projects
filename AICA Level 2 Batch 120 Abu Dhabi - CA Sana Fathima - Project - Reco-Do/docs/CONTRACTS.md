# Reco-Do build contracts

This is the working agreement between the parallel build workstreams. The product spec is `docs/Master_Prompt_v3.md`, and the shared types are in `src/shared/contracts.ts`. Every function listed below must exist with the stated signature (extra parameters may be added only as optional ones).

## Team rules (every workstream)

1. **Stay inside the files you own** (ownership map below). If you need a change in someone else's file, do not make it. List it in your final report under "Requests for other workstreams".
2. **Do not run `npm install`** or edit `package.json`. Everything needed is installed: react 19, react-router 7, radix-ui, @tanstack/react-virtual, lucide-react, tailwind v4, xlsx (SheetJS), exceljs, pdfjs-dist 6, pdf-lib, jspdf + jspdf-autotable, jszip, tesseract.js 7 + tesseract.js-core + @tesseract.js-data/eng, idb, fake-indexeddb, vitest. If you truly need another package, say so in your report.
3. **Production grade:** strict TypeScript, no `any` unless unavoidable (and then commented), no TODOs, no placeholder functions, no console noise. Errors shown to users are plain English.
4. **Tests:** pure modules get Vitest tests in `tests/<area>/*.test.ts`. Run only your tests with `npx vitest run tests/<area>`. Use `sample-data/` files and `sample-data/expected-results.json` where relevant.
5. **Typecheck:** `npx tsc --noEmit -p tsconfig.json`. Other workstreams are editing at the same time, so ignore errors in files you do not own. Your own files must be clean.
6. **Electron note:** this shell has `ELECTRON_RUN_AS_NODE=1` (set by VS Code). Use `env -u ELECTRON_RUN_AS_NODE` (bash) when launching Electron.
7. **Do not touch** `sample-data/`, `scripts/generate-samples/`, `docs/` (except your own report notes if asked) or `release/`.
8. UI follows the existing look (navy sidebar, Inter, tokens in `src/renderer/src/index.css`, status colours) and the mockups in `docs/mockups/`.
9. Numbers right-aligned with thousand separators and 2 decimals; dates DD-MMM-YYYY (`src/shared/format.ts`).

## Ownership map

| Area | Path(s) | Owner |
|---|---|---|
| Shared contracts | `src/shared/contracts.ts`, `src/shared/modules.ts`, `src/shared/tools.ts` | orchestrator (request changes) |
| Parsing | `src/shared/parsing/**`, `tests/parsing/**` | **parsing** |
| Matching engine, statements, review logic, code-side Smart Recon | `src/engine/**`, `tests/engine/**` | **engine** |
| AI layer of Smart Recon (payload, batching, prompt, validation, estimate) + Smart Recon UI panel | `src/engine/smart/ai.ts` (+ `tests/engine/ai.test.ts`), `src/renderer/src/features/smart-recon/**` | **smart-recon** (wave 2) |
| Electron main + preload, IPC, key storage, AI HTTP call, sample access, printToPDF, CSP, offline assets | `src/main/**`, `src/preload/**`, `src/renderer/index.html`, `electron.vite.config.ts`, `electron-builder.yml` | **platform** |
| UI kit, local database, settings, workspace pages | `src/renderer/src/components/**`, `src/renderer/src/lib/**`, `src/renderer/src/pages/WorkspacePage.tsx`, `src/renderer/src/pages/workspace/**`, `src/renderer/src/App.tsx`, `src/renderer/src/pages/Dashboard.tsx` | **platform** |
| Reconciliation wizard UI | `src/renderer/src/pages/ModulePage.tsx`, `src/renderer/src/features/wizard/**` | **wizard** (wave 2) |
| Recon export (Excel workbook + PDF summary HTML) | `src/export/**`, `tests/export/**` | **export** (wave 2) |
| PDF tool engines | `src/tools/pdf-to-excel/**`, `src/tools/excel-to-pdf/**`, `src/tools/merge-pdfs/**`, `src/tools/split-pdf/**`, `src/tools/common/**`, `tests/tools/**` | **tools-pdf** |
| Data tool engines, recipes, all tool screens | `src/tools/merge-files/**`, `src/tools/data-cleaner/**`, `src/renderer/src/pages/ToolPage.tsx`, `src/renderer/src/features/tools/**` | **tools-ui** (wave 2) |

## Module APIs

### Parsing: `src/shared/parsing/index.ts`
```ts
readWorkbook(data: ArrayBuffer, fileName: string): WorkbookData        // xlsx/xls/csv via SheetJS, real Date cells
detectHeaderRow(rows: CellValue[][]): { index: number; confidence: number }  // scans first 30 rows
parseTable(sheet: RawSheet, opts: { fileName: string; headerRowIndex?: number }): ParsedTable
  // excludes blank, opening/closing balance, total/subtotal, repeated-header rows (listed in `excluded`),
  // captures opening/closing balances.
parseAmount(v: CellValue): { value: number; indicator: 'DR' | 'CR' | null } | null
  // "1,234.50", "(500.00)", "750.00-", "1,234.50 CR", "AED 1,200", numbers
parseDate(v: CellValue, order?: 'DMY' | 'MDY'): Date | null           // Date cells, Excel serials, text dates
detectDateOrder(values: CellValue[]): 'DMY' | 'MDY' | 'ambiguous'
inferColumnType(header: string, values: CellValue[]): ColumnType
normaliseText(s: string, prefixes?: string[]): string                  // case, spaces, dashes, leading zeros, prefixes
headerSimilarity(a: string, b: string): number                          // 0..1 incl. synonym groups (date, reference, amount…)
valueOverlap(a: CellValue[], b: CellValue[]): number                    // 0..1 share of normalised values in common (sampled)
DEFAULT_REFERENCE_PREFIXES: string[]                                    // CHQ, FT, TT, INV, REF, POS, …
```

### Engine: `src/engine/index.ts`
```ts
validateConfig(cfg: ReconConfig, tableA: ParsedTable, tableB: ParsedTable): string[]   // plain-English errors; [] = OK
buildLines(table: ParsedTable, side: Side, cfg: ReconConfig): EngineLine[]
reconcile(tableA: ParsedTable, tableB: ParsedTable, cfg: ReconConfig): ReconResult    // deterministic, master prompt §4 Step 3
suggestKeys(moduleId: ModuleId, tableA: ParsedTable, tableB: ParsedTable): { keys: MatchKey[]; amountA?: AmountLayout; amountB?: AmountLayout; partyColumnA?: string; partyColumnB?: string }
detectSignMismatch(tableA, tableB, cfg): { opposite: number; same: number; warn: boolean }  // >80% rule
previewFirstPair(tableA, tableB, cfg): { a: EngineLine; b: EngineLine } | null
// Smart Recon, code side
findGroupMatches(result: ReconResult, opts?: { maxGroupSize?: number; maxCandidates?: number; includeDoubtful?: boolean }): { suggestions: Suggestion[]; capped: boolean }
findPartialReferenceMatches(result: ReconResult, opts?: { includeDoubtful?: boolean }): Suggestion[]
// Statements
buildStatement(result: ReconResult, meta: ReconMeta): Statement   // bank / ledger (AR, AP) / general-amount / record-count
// Review (pure, returns a new session; never mutates)
acceptPair(s: ReconSession, pairId: string, user: string, note?: string): ReconSession
rejectPair(s: ReconSession, pairId: string, user: string, note?: string): ReconSession
manualMatch(s: ReconSession, aIds: string[], bIds: string[], user: string, reason?: string): ReconSession  // totals must agree or reason required (throws plain-English Error)
unmatchPair(s, pairId, user, note?): ReconSession
addNote(s, pairId, user, note): ReconSession
approveSuggestion(s, suggestionId, user): ReconSession   // → Matched pair, label "Matched — AI assisted (approved by <user>)" for AI
rejectSuggestion(s, suggestionId, user): ReconSession
canFinalise(s): { ok: boolean; reasons: string[] }        // Doubtful + AI Suggested must be empty
finalise(s, user): ReconSession                            // locks
createSession(result: ReconResult, meta: ReconMeta): ReconSession
summariseForHistory(s: ReconSession): HistoryEntry         // from src/shared/kpis.ts
ageingBucket(date: Date, asOf: Date): '0-30' | '31-60' | '61-90' | '90+'
```

### Smart Recon AI: `src/engine/smart/ai.ts`
```ts
buildAiPayload(result: ReconResult, opts: { includeDoubtful: boolean; maskParties: boolean; batchSize?: number; codeCandidates?: Suggestion[] }):
  { batches: AiRequestBody[]; previewRows: Array<Record<string, string | number>>; estimate: { inputTokens: number; outputTokens: number; usd: number } }
parseAiResponse(text: string, result: ReconResult, maskMap: Map<string, string>): Suggestion[]   // strict JSON, discards invalid/unbalanced/reused
```

### Export: `src/export/index.ts`
```ts
buildReconWorkbook(session: ReconSession, statement: Statement): Promise<Uint8Array>   // ExcelJS, 7 sheets, master prompt §4 Step 5
buildSummaryHtml(session: ReconSession, statement: Statement): string                  // self-contained print HTML for window.recoDo.pdf.fromHtml
```

### Tools: each `src/tools/<tool>/index.ts` exports pure functions (no React), e.g.
```ts
// pdf-to-excel
extractPdf(data: ArrayBuffer, opts: PdfExtractOptions, onProgress?: (p: { page: number; pages: number; stage: 'text' | 'ocr' }) => void, signal?: AbortSignal): Promise<PdfExtractResult>
toWorkbook(result: PdfExtractResult, opts): Promise<Uint8Array>
// excel-to-pdf
sheetToPdf(table: ParsedTable, opts: ExcelToPdfOptions): Uint8Array
// merge-pdfs / split-pdf
mergePdfs(files: { name: string; data: ArrayBuffer; pages?: { index: number; rotate: 0 | 90 | 180 | 270 }[] }[]): Promise<Uint8Array>
splitPdf(data: ArrayBuffer, plan: SplitPlan): Promise<{ name: string; data: Uint8Array }[]>
pdfInfo(data: ArrayBuffer): Promise<{ pages: number; encrypted: boolean }>
// merge-files / data-cleaner (wave 2)
```

## Bridge (`window.recoDo`)
Typed as `RecoDoBridge` in `src/shared/contracts.ts`; implemented by platform in `src/preload` + `src/main`.

## Local database (`src/renderer/src/lib/db.ts`, platform)
Stores: `settings` (preparerName, department, currency, aiModel, maskPartiesDefault), `history` (HistoryEntry), `sessions` (ReconSession), `mappings` (SavedMapping), `templates` (GeneralTemplate), `recipes` (ToolRecipe). Typed functions: `getSettings/saveSettings`, `listHistory`, `saveSession(session, historyEntry)/getSession/listSessions/deleteSession` (the caller builds `historyEntry` with the engine's `summariseForHistory`; both are written in one transaction; deleteSession removes both), `listMappings/saveMapping/deleteMapping/findMappingByHeaders`, `listTemplates/saveTemplate/deleteTemplate`, `listRecipes/saveRecipe/deleteRecipe`.
