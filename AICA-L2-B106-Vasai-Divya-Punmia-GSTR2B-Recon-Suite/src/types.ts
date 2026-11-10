/** Which register a row was imported into. */
export type Kind = 'g2b' | 'bks' | 'cdn_g2b' | 'cdn_bks' | 'rcm';

/** Stored register names (see shared/db.mjs DATASET_KINDS). */
export type DatasetKind =
  | 'g2b'
  | 'g2b_cdn'
  | 'g2b_excl'
  | 'bks'
  | 'bks_cdn'
  | 'bks_excl'
  | 'cdn_g2b'
  | 'cdn_bks'
  | 'rcm';

export interface Row {
  gstin: string;
  name: string;
  inv: string;
  /** Always dd/mm/yyyy (or '' when the file had no usable date). */
  date: string;
  taxable: number;
  igst: number;
  cgst: number;
  sgst: number;
  total: number;
  source: Kind;
  rowNum: number;
  sheet: string;
  isAmendment?: boolean;
  rcm?: boolean;
  rcmReason?: string;
  blocked?: boolean;
  blockedSec?: string;
  blockedReason?: string;
  /** Only on excluded rows. */
  reason?: string;
}

export interface Engagement {
  id: number;
  name: string;
  gstin: string;
  period: string;
  tolerance: number;
  createdAt: string;
  updatedAt: string;
  g2bCount?: number;
  bksCount?: number;
}

export interface BlockedCredit {
  id: number;
  gstin: string;
  invKey: string;
  inv: string;
  name: string;
  date: string;
  taxable: number;
  igst: number;
  cgst: number;
  sgst: number;
  catId: string;
  catLbl: string;
  sec: string;
  reason: string;
  origin: 'auto' | 'manual';
  active: boolean;
  blockedOn: string;
}

export type MsmeStatus = 'unverified' | 'unregistered' | 'micro' | 'small' | 'medium';

export interface Supplier {
  gstin: string;
  email: string;
  msmeStatus: MsmeStatus;
  udyamNumber: string;
  notes: string;
  verifiedAt: string;
}

export interface FirmDetails {
  name: string;
  ca: string;
  memNo: string;
  email: string;
  phone: string;
}

export interface LogEntry {
  id: number;
  tag: string;
  message: string;
  createdAt: string;
}

export type Datasets = Record<DatasetKind, Row[]>;

export interface EngagementState {
  engagement: Engagement;
  datasets: Datasets;
  datasetInfo: Partial<Record<DatasetKind, { fileName: string; rowCount: number; importedAt: string }>>;
  blocked: BlockedCredit[];
  remarks: Record<string, string>;
}

/* ------------------------------ Reconciliation ------------------------------ */

/** Primary pass: ok = matched (exact or within tolerance), am = ITC mismatch, mb = missing in books, m2 = missing in 2B. */
export type PrimaryStatus = 'ok' | 'am' | 'mb' | 'm2';

/**
 * Smart passes (run only on rows the primary pass left unmatched):
 * cm/cx = pass 1 invoice-core match (within / outside tolerance), ad = pass 2 amount + date,
 * ti = pass 3 tax values with invoice no. ignored, smb/sm2 = still unresolved.
 */
export type SmartStatus = 'cm' | 'cx' | 'ad' | 'ti' | 'smb' | 'sm2';

export interface PrimaryResult {
  s: PrimaryStatus;
  g2b: Row | null;
  bk: Row | null;
  diff: number;
  /** Matched only because the difference is within tolerance. */
  tm: boolean;
}

export interface SmartResult {
  s: SmartStatus;
  g2b: Row | null;
  bk: Row | null;
  diff: number;
  gc?: string;
  bc?: string;
}

/** Final status of every invoice after both stages; each invoice appears exactly once. */
export type FinalStatus = 'exact' | 'tol' | 'mismatch' | 'smart' | 'missBooks' | 'miss2b';
