// Shared data contracts between parsing, engine, export, Smart Recon, tools and the UI.
// Types only. Changing a type here affects several modules: keep changes additive.

import type { ModuleId, SignConvention } from './modules'

// ───────────────────────── Tabular data (src/shared/parsing) ─────────────────────────

export type CellValue = string | number | Date | null

/** A sheet exactly as read from the file (no header detection yet). */
export interface RawSheet {
  name: string
  rows: CellValue[][]
}

export interface WorkbookData {
  fileName: string
  sheets: RawSheet[]
}

export type ExclusionReason =
  | 'blank'
  | 'opening-balance'
  | 'closing-balance'
  | 'total'
  | 'subtotal'
  | 'repeated-header'
  | 'duplicate'

export interface ExcludedRow {
  /** 0-based index into RawSheet.rows. Excel row number = sourceRow + 1. */
  sourceRow: number
  reason: ExclusionReason
  values: CellValue[]
}

export interface TableRow {
  /** Stable within one table: `r${excelRowNumber}`, e.g. "r12". */
  id: string
  sourceRow: number
  values: Record<string, CellValue>
}

export interface ParsedTable {
  fileName: string
  sheetName: string
  /**
   * 0-based index into RawSheet.rows. -1 (NO_HEADER_ROW) means the file has no header row:
   * every row is data and columns are named "Column 1", "Column 2", …
   * For a two-row header this is the lower row, and the column names are merged.
   */
  headerRowIndex: number
  /** Unique column names in file order (duplicates become "Debit (2)"). */
  columns: string[]
  rows: TableRow[]
  excluded: ExcludedRow[]
  openingBalance: number | null
  closingBalance: number | null
}

export type ColumnType = 'id' | 'text' | 'amount' | 'number' | 'date'

// ───────────────────────── Recon configuration (Map & Rules) ─────────────────────────

export type TextRule = 'exact' | 'contains' | 'normalised'

export type Tolerance = { mode: 'exact' } | { mode: 'fixed'; value: number } | { mode: 'percent'; value: number }

/** How a file expresses money. Converted internally to one signed number. */
export type AmountLayout =
  | { kind: 'signed'; column: string }
  | { kind: 'debit-credit'; debit: string; credit: string }
  | { kind: 'amount-indicator'; amount: string; indicator: string }

export interface MatchKey {
  id: string
  name: string
  type: ColumnType
  use: boolean
  /** For type 'amount' the columns come from ReconConfig.amountA / amountB instead. */
  columnA: string
  columnB: string
  /** id / amount / number: always true. date: always false. text: user's "ID key" tick. */
  identifying: boolean
  textRule?: TextRule
  dateToleranceDays?: number
  tolerance?: Tolerance
}

export interface ReconConfig {
  moduleId: ModuleId
  sideAName: string
  sideBName: string
  keys: MatchKey[]
  amountA?: AmountLayout
  amountB?: AmountLayout
  sign: SignConvention
  /** Optional party/name columns used to restrict group (sum) matching. */
  partyColumnA?: string
  partyColumnB?: string
  /** Prefixes stripped by the Normalised rule, e.g. CHQ, FT, INV, REF. */
  referencePrefixes: string[]
  currency: string
  /**
   * Day/month order of numeric text dates ("03/04/2026") in each file. Optional: when absent the engine detects
   * it from the whole date column and falls back to DMY (the UAE convention) when the column is ambiguous.
   */
  dateOrderA?: 'DMY' | 'MDY'
  dateOrderB?: 'DMY' | 'MDY'
}

// ───────────────────────── Engine results (src/engine) ─────────────────────────

export type Side = 'A' | 'B'
export type Tier = 'matched' | 'doubtful' | 'likely' | 'unmatched'

export interface EngineLine {
  /** Globally unique within a recon: `${side}:${rowId}`, e.g. "A:r12". */
  id: string
  side: Side
  rowId: string
  /** Signed amount in this file's own terms (null when no amount key is used). */
  amount: number | null
  /** Amount expressed in side A's sign convention, used for comparing and statements. */
  comparableAmount: number | null
  date: Date | null
  values: Record<string, CellValue>
}

export interface KeyResult {
  keyId: string
  pass: boolean
  /** Plain-English detail, e.g. "differs by 5 days", "90.00 difference". */
  detail?: string
}

export type PairFlag = 'transposition' | 'bank-charge' | 'rounding' | 'multiple-candidates'
export type PairOrigin = 'engine' | 'manual' | 'code-group' | 'code-partial-ref' | 'ai'
export type PairStatus = 'open' | 'accepted' | 'rejected'

export interface MatchPair {
  id: string
  tier: Tier
  aIds: string[]
  bIds: string[]
  keyResults: KeyResult[]
  /** comparable A total − comparable B total (null without amounts). */
  amountDifference: number | null
  dateDifferenceDays: number | null
  reason: string
  flags: PairFlag[]
  origin: PairOrigin
  /** Engine "matched" pairs start accepted; doubtful/likely/AI start open. */
  status: PairStatus
  /** Other equally good line ids when flagged 'multiple-candidates'. */
  candidateIds?: string[]
  confidence?: number
  /** e.g. "Matched — AI assisted (approved by Sana Fathima)". */
  label?: string
  note?: string
}

export interface ReconStats {
  linesA: number
  linesB: number
  matched: number
  doubtful: number
  likely: number
  unmatchedA: number
  unmatchedB: number
  matchedAmount: number
}

export interface ReconResult {
  config: ReconConfig
  linesA: EngineLine[]
  linesB: EngineLine[]
  pairs: MatchPair[]
  unmatchedA: string[]
  unmatchedB: string[]
  stats: ReconStats
  durationMs: number
}

// ───────────────────────── Smart Recon ─────────────────────────

export type SuggestionSource = 'code-group' | 'code-partial-ref' | 'ai'

export interface Suggestion {
  id: string
  aIds: string[]
  bIds: string[]
  confidence: number // 0-100
  reason: string
  source: SuggestionSource
  status: PairStatus
}

// ───────────────────────── Statements ─────────────────────────

export type StatementKind = 'bank' | 'ledger' | 'general-amount' | 'record-count'

export interface StatementLine {
  label: string
  /** Amount (or count, for record-count statements). Subtotal lines have isTotal = true. */
  value: number
  isTotal?: boolean
  /** Line ids that make up this value, for drill-down and export. */
  lineIds?: string[]
}

export interface Statement {
  kind: StatementKind
  title: string
  lines: StatementLine[]
  unexplainedDifference: number
}

// ───────────────────────── Review, audit and sessions ─────────────────────────

export type AuditAction =
  | 'accept'
  | 'reject'
  | 'manual-match'
  | 'unmatch'
  | 'note'
  | 'approve-suggestion'
  | 'reject-suggestion'
  | 'finalise'

export interface AuditEntry {
  id: string
  at: string // ISO timestamp
  user: string
  action: AuditAction
  pairId?: string
  suggestionId?: string
  before?: string
  after?: string
  note?: string
}

export interface ReconMeta {
  accountLabel: string
  period: string
  fileA: { name: string; sheet: string; rows: number }
  fileB: { name: string; sheet: string; rows: number }
  mappingName?: string
  preparer: string
  currency: string
  balances: { openingA: number | null; closingA: number | null; openingB: number | null; closingB: number | null }
}

/** Everything about one reconciliation. Stored whole in IndexedDB (store "sessions"). */
export interface ReconSession {
  id: string
  createdAt: string
  updatedAt: string
  meta: ReconMeta
  result: ReconResult
  suggestions: Suggestion[]
  audit: AuditEntry[]
  finalised: { by: string; at: string } | null
}

// ───────────────────────── Saved setups ─────────────────────────

export interface SavedMapping {
  id: string
  name: string
  moduleId: ModuleId
  /** Sorted header lists used to auto-load the mapping when the same files come back. */
  headersA: string[]
  headersB: string[]
  config: ReconConfig
  createdAt: string
  updatedAt: string
}

/** General Reconciliation template (same shape; shown under "Load template"). */
export type GeneralTemplate = SavedMapping

export type RecipeTool = 'pdf-to-excel' | 'merge-files' | 'data-cleaner'

export interface ToolRecipe {
  id: string
  name: string
  tool: RecipeTool
  /** Tool-specific options, owned and validated by each tool. */
  options: unknown
  createdAt: string
  updatedAt: string
}

// ───────────────────────── Main-process bridge (window.recoDo) ─────────────────────────

export interface FileFilter {
  name: string
  extensions: string[]
}

export interface OpenedFile {
  name: string
  data: ArrayBuffer
}

export interface SampleFile {
  /** Path relative to sample-data, forward slashes, e.g. "bank/GL_101200_Cash_Sep2026.xlsx". */
  path: string
  name: string
  folder: string
  size: number
}

export type AiEffort = 'low' | 'medium' | 'high'

/**
 * The AI service Smart Recon sends rows to, chosen in Settings. 'custom' is any OpenAI-compatible service at a
 * base URL the user saved (OpenRouter, Groq, Mistral, a gateway, or a local server such as LM Studio or Ollama).
 */
export type AiProvider = 'anthropic' | 'openai' | 'gemini' | 'deepseek' | 'custom'

export interface AiKeyStatus {
  hasKey: boolean
  /** Masked form only (e.g. "sk-…3f9a"); the key itself never reaches the page. */
  masked: string | null
}

export interface AiSecretsStatus extends AiKeyStatus {
  /** Every provider's key status. (The top-level hasKey / masked describe the Anthropic key, as before.) */
  providers: Record<AiProvider, AiKeyStatus>
  /** The "Other (OpenAI-compatible)" base URL saved in Settings; the only custom address the app may contact. */
  customBaseUrl: string | null
}

export interface AiRequest {
  /** Which service to call (default 'anthropic'). */
  provider?: AiProvider
  /** Base URL for provider 'custom'. It must equal the address saved in Settings, or the request is refused. */
  baseUrl?: string
  model: string
  system: string
  messages: { role: 'user' | 'assistant'; content: string }[]
  maxTokens: number
  /** How much the model thinks before answering. Sent only when set, and only to models that support it. */
  effort?: AiEffort
  /** Lets `ai.cancel(requestId)` stop this request while it runs (letters, digits and dashes, at most 64). */
  requestId?: string
}

export interface AiResponse {
  text: string
  inputTokens: number
  outputTokens: number
}

export type AiErrorCode = 'no-key' | 'bad-key' | 'rate-limit' | 'overloaded' | 'network' | 'api'

export type AiResult = { ok: true; response: AiResponse } | { ok: false; code: AiErrorCode; message: string }

export interface RecoDoBridge {
  /** The app version and the folder that holds this user's data (IndexedDB, saved keys, settings). */
  appInfo(): Promise<{ version: string; dataPath: string }>
  /** Opens this user's data folder (and only that folder) in File Explorer. */
  openDataFolder(): Promise<void>
  files: {
    open(opts: { title?: string; filters?: FileFilter[]; multiple?: boolean }): Promise<OpenedFile[]>
    save(opts: { defaultName: string; filters?: FileFilter[]; data: ArrayBuffer | Uint8Array }): Promise<{ saved: boolean; path?: string }>
  }
  samples: {
    list(): Promise<SampleFile[]>
    read(path: string): Promise<ArrayBuffer>
  }
  pdf: {
    /** Renders HTML to a real PDF in a hidden window and shows the Save dialog. */
    fromHtml(opts: { html: string; defaultName: string; landscape?: boolean }): Promise<{ saved: boolean; path?: string }>
  }
  secrets: {
    status(): Promise<AiSecretsStatus>
    /** Saves the provider's key encrypted. `warning` is set when the key does not look like that provider's usual format. */
    setApiKey(provider: AiProvider, key: string): Promise<{ warning: string | null }>
    /** Older form: saves an Anthropic key. */
    setApiKey(key: string): Promise<{ warning: string | null }>
    /** Deletes the provider's key (Anthropic when no provider is given). */
    forgetApiKey(provider?: AiProvider): Promise<void>
  }
  ai: {
    complete(req: AiRequest): Promise<AiResult>
    /** Stops the request sent with this `requestId` (its `complete` then resolves with an error result). */
    cancel(requestId: string): Promise<void>
    /**
     * Saves (or with null, clears) the base URL of the "Other (OpenAI-compatible)" provider. Only this exact origin
     * may then be contacted for provider 'custom'. https is required except for localhost. Returns the cleaned URL.
     */
    setCustomBaseUrl(baseUrl: string | null): Promise<string | null>
  }
  lifecycle: {
    /**
     * Registers work to finish before the window closes (e.g. pending saves). The window waits for every
     * registered handler, up to a time limit. Returns a function that unregisters the handler.
     */
    onBeforeClose(handler: () => Promise<void> | void): () => void
  }
}
