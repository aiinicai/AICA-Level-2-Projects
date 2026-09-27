import { HospitalDepartment } from './index';

export type CanonicalDatasetType =
  | 'encounters'
  | 'services'
  | 'billing'
  | 'claims'
  | 'collections'
  | 'tariff_master'
  | 'budgets'
  | 'unclassified';

export type InferredDataType = 'string' | 'number' | 'date' | 'boolean' | 'identifier';

export type MappingConfidence = 'HIGH' | 'MEDIUM' | 'LOW';

export interface ColumnProfile {
  columnName: string;
  originalHeader: string;
  inferredType: InferredDataType;
  sampleValues: string[];
  totalValues: number;
  nullCount: number;
  nullRate: number; // 0.0 to 1.0
  uniqueCount: number;
  isLikelyIdentifier: boolean;
  isLikelyAmount: boolean;
  isLikelyQuantity: boolean;
  isLikelyDate: boolean;
  isLikelyStatus: boolean;
}

export interface SheetProfile {
  sheetName: string;
  rowCount: number;
  columnCount: number;
  columns: ColumnProfile[];
  rawRows: Record<string, unknown>[];
  suggestedDatasetType: CanonicalDatasetType;
  confidenceScore: number; // 0 to 100
  classificationReason: string;
}

export interface UploadedFileProfile {
  fileId: string;
  fileName: string;
  fileSize: number;
  fileType: 'xlsx' | 'xls' | 'csv';
  sheets: SheetProfile[];
  activeSheetName: string;
}

export interface ColumnMappingItem {
  sourceColumn: string;
  canonicalField: string; // canonical property key or 'unmapped'
  confidence: MappingConfidence;
  status: 'ACCEPTED' | 'PENDING_REVIEW' | 'OVERRIDDEN' | 'IGNORED';
  reason: string;
  isAmbiguous?: boolean;
  alternativeCandidates?: string[];
  required?: boolean;
}

export interface DatasetMappingConfig {
  fileId: string;
  fileName: string;
  sheetName: string;
  datasetType: CanonicalDatasetType;
  mappings: ColumnMappingItem[];
}

export type QualityIssueType =
  | 'MISSING_REQUIRED'
  | 'INVALID_DATE'
  | 'INVALID_NUMERIC'
  | 'NEGATIVE_QTY'
  | 'DUPLICATE_ID'
  | 'UNMATCHED_REF'
  | 'INCONSISTENT_DEPT'
  | 'INVALID_STATUS'
  | 'SUSPICIOUS_AMOUNT';

export interface DataQualityIssue {
  id: string;
  rowNumber: number;
  column: string;
  issueType: QualityIssueType;
  severity: 'ERROR' | 'WARNING';
  message: string;
  rawValue?: unknown;
}

export interface DataValidationSummary {
  fileId: string;
  fileName: string;
  datasetType: CanonicalDatasetType;
  recordsDetected: number;
  recordsReadyForImport: number;
  recordsRequiringReview: number;
  mappingIssuesCount: number;
  dataQualityIssuesCount: number;
  issues: DataQualityIssue[];
  invalidRowIndices: number[];
}

export interface DetectedRelationship {
  id: string;
  sourceDataset: string;
  sourceField: string;
  targetDataset: string;
  targetField: string;
  matchRate: number; // percentage 0 - 100
  matchedCount: number;
  totalSourceCount: number;
  confidence: MappingConfidence;
  description: string;
  isValid: boolean;
}

export interface ImportHistoryRecord {
  importId: string;
  timestamp: string;
  files: Array<{
    name: string;
    datasetType: string;
    sheetName?: string;
    rows: number;
  }>;
  datasetTypes: string[];
  recordsDetected: number;
  recordsImported: number;
  recordsRejected: number;
  mappingStatus: 'AUTOMATIC' | 'VERIFIED_WITH_OVERRIDES';
  validationStatus: 'CLEAN' | 'WARNINGS_RESOLVED' | 'ERRORS_BYPASSED';
  userId: string;
  userName: string;
  userRole: string;
  mappingsSnapshot: Record<string, Record<string, string>>;
  issuesSnapshotCount: number;
}
