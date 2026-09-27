import React, { useState, useMemo, useRef } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  FileCheck2,
  Table,
  Check,
  X,
  ChevronRight,
  Search,
  Eye,
  Layers,
  History,
  AlertCircle,
  Trash2,
} from 'lucide-react';
import {
  CanonicalDatasetType,
  ColumnMappingItem,
  DataValidationSummary,
  DetectedRelationship,
  UploadedFileProfile,
} from '../types/ingestion';
import { UserSession } from '../types';
import {
  CANONICAL_SCHEMAS,
  parseUploadedFile,
  generateDeterministicMapping,
  validateDatasetQuality,
  detectCrossFileRelationships,
  transformToCanonicalRecords,
} from '../utils/dynamicDataEngine';
import { mapColumnsWithGemini } from '../services/geminiMappingService';
import {
  importHospitalDataBatch,
  BatchImportDatasets,
  saveImportHistoryRecord,
} from '../services/firestoreDataService';
import { auditService } from '../services/auditService';
import { formatIndianNumber } from '../utils/formatters';

interface DataIntelligenceViewProps {
  currentUser: UserSession;
  onRunControlsAfterImport: () => void;
  onUpdateDatasetInApp: (datasetType: CanonicalDatasetType, records: unknown[]) => void;
  onBatchUpdateDatasets?: (datasets: BatchImportDatasets) => void;
  onNavigateToTab?: (tabId: string) => void;
  onClearWorkspace?: () => void;
  hasData?: boolean;
}

type StepStatus = 'WAITING' | 'RUNNING' | 'DONE';

export const DataIntelligenceView: React.FC<DataIntelligenceViewProps> = ({
  currentUser,
  onRunControlsAfterImport,
  onUpdateDatasetInApp,
  onBatchUpdateDatasets,
  onNavigateToTab,
  onClearWorkspace,
  hasData,
}) => {
  const [phase, setPhase] = useState<'UPLOAD' | 'ANALYSING' | 'REVIEW' | 'PROCESSING' | 'COMPLETED'>('UPLOAD');
  const [isDragging, setIsDragging] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Uploaded files profiles
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileProfile[]>([]);

  // Pipeline progress
  const [stepsStatus, setStepsStatus] = useState<{
    analysing: StepStatus;
    mapping: StepStatus;
    validating: StepStatus;
    matching: StepStatus;
  }>({
    analysing: 'WAITING',
    mapping: 'WAITING',
    validating: 'WAITING',
    matching: 'WAITING',
  });

  // Mappings per file and sheet
  const [mappingsStore, setMappingsStore] = useState<Record<string, ColumnMappingItem[]>>({});
  const [datasetTypeStore, setDatasetTypeStore] = useState<Record<string, CanonicalDatasetType>>({});
  const [validationSummaries, setValidationSummaries] = useState<Record<string, DataValidationSummary>>({});
  const [detectedRelationships, setDetectedRelationships] = useState<DetectedRelationship[]>([]);

  // Processing summary
  const [processedCount, setProcessedCount] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Compute aggregated stats
  const analysisStats = useMemo(() => {
    let totalFields = 0;
    let autoMappedFields = 0;
    let reviewRequiredFields = 0;
    let totalRecords = 0;
    let qualityExceptions = 0;

    uploadedFiles.forEach((file) => {
      file.sheets.forEach((sheet) => {
        const storeKey = `${file.fileId}_${sheet.sheetName}`;
        const mappings = mappingsStore[storeKey] || [];
        const val = validationSummaries[storeKey];

        mappings.forEach((m) => {
          totalFields++;
          if (m.confidence === 'HIGH') {
            autoMappedFields++;
          } else {
            reviewRequiredFields++;
          }
        });

        if (val) {
          totalRecords += val.recordsDetected;
          qualityExceptions += val.recordsRequiringReview;
        } else {
          totalRecords += sheet.rowCount;
        }
      });
    });

    const ambiguousMatches = detectedRelationships.filter((r) => r.confidence === 'LOW').length;
    const totalExceptions = reviewRequiredFields + qualityExceptions + ambiguousMatches;

    return {
      filesCount: uploadedFiles.length,
      totalFields,
      autoMappedFields,
      reviewRequiredFields,
      totalRecords,
      qualityExceptions,
      ambiguousMatches,
      totalExceptions,
    };
  }, [uploadedFiles, mappingsStore, validationSummaries, detectedRelationships]);

  // Extract only exception mapping items that need user attention
  const mappingExceptionsList = useMemo(() => {
    const list: Array<{
      fileId: string;
      fileName: string;
      sheetName: string;
      storeKey: string;
      mapping: ColumnMappingItem;
      datasetType: CanonicalDatasetType;
    }> = [];

    uploadedFiles.forEach((file) => {
      file.sheets.forEach((sheet) => {
        const key = `${file.fileId}_${sheet.sheetName}`;
        const mappings = mappingsStore[key] || [];
        const dType = datasetTypeStore[key];
        mappings.forEach((m) => {
          if (m.confidence !== 'HIGH') {
            list.push({
              fileId: file.fileId,
              fileName: file.fileName,
              sheetName: sheet.sheetName,
              storeKey: key,
              mapping: m,
              datasetType: dType,
            });
          }
        });
      });
    });

    return list;
  }, [uploadedFiles, mappingsStore, datasetTypeStore]);

  // Automatic Pipeline Handler
  const handleFilesSelected = async (files: FileList | File[]) => {
    if (!files || files.length === 0) return;
    const fileArray = Array.from(files);
    setErrorMessage(null);
    setPhase('ANALYSING');

    setStepsStatus({
      analysing: 'RUNNING',
      mapping: 'WAITING',
      validating: 'WAITING',
      matching: 'WAITING',
    });

    try {
      // 1. Parse all files
      const parsedProfiles: UploadedFileProfile[] = [];
      for (const f of fileArray) {
        const profile = await parseUploadedFile(f);
        parsedProfiles.push(profile);
      }
      setUploadedFiles(parsedProfiles);
      setStepsStatus((prev) => ({ ...prev, analysing: 'DONE', mapping: 'RUNNING' }));

      // 2. Identify purpose & map fields
      const newTypeStore: Record<string, CanonicalDatasetType> = {};
      const newMappingsStore: Record<string, ColumnMappingItem[]> = {};

      parsedProfiles.forEach((file) => {
        file.sheets.forEach((sheet) => {
          const key = `${file.fileId}_${sheet.sheetName}`;
          newTypeStore[key] = sheet.suggestedDatasetType;
        });
      });
      setDatasetTypeStore(newTypeStore);

      for (const file of parsedProfiles) {
        for (const sheet of file.sheets) {
          const key = `${file.fileId}_${sheet.sheetName}`;
          const dType = newTypeStore[key];
          try {
            const res = await mapColumnsWithGemini(dType, sheet.columns);
            newMappingsStore[key] = res.mappings;
          } catch {
            newMappingsStore[key] = generateDeterministicMapping(dType, sheet.columns);
          }
        }
      }
      setMappingsStore(newMappingsStore);
      setStepsStatus((prev) => ({ ...prev, mapping: 'DONE', validating: 'RUNNING' }));

      // 3. Validate data
      const newValSummaries: Record<string, DataValidationSummary> = {};
      parsedProfiles.forEach((file) => {
        file.sheets.forEach((sheet) => {
          const key = `${file.fileId}_${sheet.sheetName}`;
          const dType = newTypeStore[key];
          const mappings = newMappingsStore[key] || [];
          newValSummaries[key] = validateDatasetQuality(
            file.fileId,
            file.fileName,
            dType,
            sheet.rawRows,
            mappings
          );
        });
      });
      setValidationSummaries(newValSummaries);
      setStepsStatus((prev) => ({ ...prev, validating: 'DONE', matching: 'RUNNING' }));

      // 4. Cross-file record matching
      const relConfigs: Array<{
        fileName: string;
        datasetType: CanonicalDatasetType;
        rows: Record<string, unknown>[];
        mappings: ColumnMappingItem[];
      }> = [];

      parsedProfiles.forEach((file) => {
        file.sheets.forEach((sheet) => {
          const key = `${file.fileId}_${sheet.sheetName}`;
          const dType = newTypeStore[key] || 'unclassified';
          if (dType !== 'unclassified') {
            relConfigs.push({
              fileName: file.fileName,
              datasetType: dType,
              rows: sheet.rawRows,
              mappings: newMappingsStore[key] || [],
            });
          }
        });
      });

      const relationships = detectCrossFileRelationships(relConfigs);
      setDetectedRelationships(relationships);
      setStepsStatus((prev) => ({ ...prev, matching: 'DONE' }));

      // Ready for review
      setPhase('REVIEW');
    } catch (err: any) {
      console.error('File parsing error:', err);
      setErrorMessage(err?.message || 'Failed to analyze hospital files. Please verify format.');
      setPhase('UPLOAD');
    }
  };

  // Update a single mapping when user adjusts in review table
  const handleUpdateMappingField = (
    storeKey: string,
    sourceCol: string,
    newCanonicalField: string
  ) => {
    setMappingsStore((prev) => {
      const existing = prev[storeKey] || [];
      const updated = existing.map((m) =>
        m.sourceColumn === sourceCol
          ? {
              ...m,
              canonicalField: newCanonicalField,
              confidence: 'HIGH' as const,
              status: 'ACCEPTED' as const,
            }
          : m
      );
      return { ...prev, [storeKey]: updated };
    });
  };

  // Confirm and Process Data Batch
  const handleConfirmAndProcess = async () => {
    setPhase('PROCESSING');
    setErrorMessage(null);

    try {
      const batchData: BatchImportDatasets = {
        encounters: [],
        services: [],
        billing: [],
        claims: [],
        collections: [],
        tariffs: [],
        budgets: [],
      };

      let totalRecords = 0;

      for (const file of uploadedFiles) {
        for (const sheet of file.sheets) {
          const key = `${file.fileId}_${sheet.sheetName}`;
          const dType = datasetTypeStore[key];
          const mappings = mappingsStore[key] || [];
          const valSummary = validationSummaries[key];
          const excludeIndices = valSummary ? valSummary.invalidRowIndices : [];

          const records = transformToCanonicalRecords(
            dType,
            sheet.rawRows,
            mappings,
            excludeIndices
          );

          if (records.length > 0) {
            totalRecords += records.length;
            if (dType === 'encounters') batchData.encounters!.push(...(records as any));
            else if (dType === 'services') batchData.services!.push(...(records as any));
            else if (dType === 'billing') batchData.billing!.push(...(records as any));
            else if (dType === 'claims') batchData.claims!.push(...(records as any));
            else if (dType === 'collections') batchData.collections!.push(...(records as any));
            else if (dType === 'tariff_master') batchData.tariffs!.push(...(records as any));
            else if (dType === 'budgets') batchData.budgets!.push(...(records as any));

            // Immediate state update
            onUpdateDatasetInApp(dType, records);
          }
        }
      }

      if (onBatchUpdateDatasets) {
        onBatchUpdateDatasets(batchData);
      }

      // Persist to Firestore in one centralized, deduplicated batch
      const result = await importHospitalDataBatch(batchData, currentUser);
      if (!result.success) {
        setErrorMessage(result.error || 'Database rejected the batch import.');
        setPhase('REVIEW');
        return;
      }

      // Automatically execute C01–C08 controls on the new hospital records
      onRunControlsAfterImport();

      setProcessedCount(totalRecords);

      auditService.logEvent({
        user: currentUser.name,
        role: currentUser.role,
        action: 'DATA_IMPORT',
        entityType: 'Dataset',
        entityId: 'HOSPITAL_BATCH',
        details: `Imported and validated ${totalRecords} hospital records across mapped datasets into active financial workspace.`,
      });

      setPhase('COMPLETED');
    } catch (err: any) {
      console.error('Import processing error:', err);
      setErrorMessage(err?.message || 'Error occurred while saving imported records.');
      setPhase('REVIEW');
    }
  };

  const handleReset = () => {
    setUploadedFiles([]);
    setMappingsStore({});
    setDatasetTypeStore({});
    setValidationSummaries({});
    setDetectedRelationships([]);
    setErrorMessage(null);
    setPhase('UPLOAD');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Data Import &amp; Mapping
            </h1>
            <p className="mt-1 text-xs text-slate-500">
              Upload existing hospital reports and extracts. The system will identify the data structure, map fields and validate the information before processing.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {phase !== 'UPLOAD' && phase !== 'ANALYSING' && (
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs cursor-pointer"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Upload Different Files</span>
              </button>
            )}

            {onClearWorkspace && hasData && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 text-xs font-semibold text-rose-700 shadow-2xs cursor-pointer transition"
                title="Permanently delete all imported hospital data and reset controls"
              >
                <Trash2 className="h-3.5 w-3.5 text-rose-600" />
                <span>Delete Stored Data &amp; Re-upload</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ACTIVE DATASET NOTICE */}
      {hasData && phase === 'UPLOAD' && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-teal-200 bg-teal-50/50 p-4 text-xs text-slate-700 shadow-2xs">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="h-4 w-4 text-teal-700 shrink-0" />
            <span>
              <strong>Hospital financial records are currently loaded.</strong> You can upload new files to supplement existing records, or clear and start completely from scratch.
            </span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {onNavigateToTab && (
              <button
                onClick={() => onNavigateToTab('dashboard')}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-semibold text-xs shadow-xs transition cursor-pointer"
              >
                <span>View Finance Control Tower</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            )}
            {onClearWorkspace && (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="inline-flex items-center gap-1.5 font-bold text-rose-700 hover:text-rose-800 underline shrink-0 cursor-pointer text-xs"
              >
                <Trash2 className="h-3 w-3" />
                <span>Delete Stored Data &amp; Re-upload</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* ERROR BANNER */}
      {errorMessage && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-900 shadow-2xs flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-xs font-bold uppercase tracking-wider">Import Error</h3>
            <p className="mt-1 text-xs">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* PHASE 1: UPLOAD AREA */}
      {phase === 'UPLOAD' && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-2xs">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (e.dataTransfer.files) handleFilesSelected(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 text-center transition cursor-pointer ${
              isDragging
                ? 'border-teal-500 bg-teal-50/50'
                : 'border-slate-300 hover:border-teal-400 bg-slate-50/50'
            }`}
          >
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-teal-50 text-teal-700 mb-4 border border-teal-200 shadow-xs">
              <UploadCloud className="h-8 w-8" />
            </div>
            <h3 className="text-base font-bold text-slate-900">
              Drop Excel or CSV files here
            </h3>
            <p className="mt-1.5 text-xs text-slate-500 max-w-sm">
              Multiple files supported &bull; IP/OP Registrations, Charge Sheets, Billing Summaries, Insurance Claims, Receipts, Tariff Masters or Budgets
            </p>
            <div className="mt-5 inline-flex items-center gap-2 rounded-lg bg-teal-700 hover:bg-teal-800 px-4 py-2 text-xs font-semibold text-white shadow-xs transition">
              <FileSpreadsheet className="h-4 w-4" />
              <span>Select Files from Computer</span>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".xlsx,.xls,.csv"
              className="hidden"
              onChange={(e) => e.target.files && handleFilesSelected(e.target.files)}
            />
          </div>
        </div>
      )}

      {/* PHASE 2: AUTOMATIC PROGRESS WORKFLOW */}
      {phase === 'ANALYSING' && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-2xs">
          <h2 className="text-base font-bold text-slate-900 mb-6 text-center">
            Analysing Hospital Files &amp; Standardising Data
          </h2>

          <div className="max-w-md mx-auto space-y-4">
            {/* Step 1: Analysing */}
            <div className="flex items-center gap-3 p-3 rounded-lg border border-slate-100 bg-slate-50">
              {stepsStatus.analysing === 'DONE' ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              ) : (
                <RefreshCw className="h-5 w-5 text-teal-600 animate-spin shrink-0" />
              )}
              <div className="flex-1">
                <div className="text-xs font-bold text-slate-900">Analysing Files</div>
                <div className="text-[11px] text-slate-500">Reading sheets and data columns</div>
              </div>
              <span className="text-[10px] font-bold uppercase text-slate-400">
                {stepsStatus.analysing === 'DONE' ? '✓' : '...'}
              </span>
            </div>

            {/* Step 2: Mapping */}
            <div className="flex items-center gap-3 p-3 rounded-lg border border-slate-100 bg-slate-50">
              {stepsStatus.mapping === 'DONE' ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              ) : stepsStatus.mapping === 'RUNNING' ? (
                <RefreshCw className="h-5 w-5 text-teal-600 animate-spin shrink-0" />
              ) : (
                <div className="h-5 w-5 rounded-full border border-slate-300 shrink-0" />
              )}
              <div className="flex-1">
                <div className="text-xs font-bold text-slate-900">Field Mapping</div>
                <div className="text-[11px] text-slate-500">Matching hospital fields to standards</div>
              </div>
              <span className="text-[10px] font-bold uppercase text-slate-400">
                {stepsStatus.mapping === 'DONE' ? '✓' : stepsStatus.mapping === 'RUNNING' ? '...' : ''}
              </span>
            </div>

            {/* Step 3: Validating */}
            <div className="flex items-center gap-3 p-3 rounded-lg border border-slate-100 bg-slate-50">
              {stepsStatus.validating === 'DONE' ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              ) : stepsStatus.validating === 'RUNNING' ? (
                <RefreshCw className="h-5 w-5 text-teal-600 animate-spin shrink-0" />
              ) : (
                <div className="h-5 w-5 rounded-full border border-slate-300 shrink-0" />
              )}
              <div className="flex-1">
                <div className="text-xs font-bold text-slate-900">Data Validation</div>
                <div className="text-[11px] text-slate-500">Auditing identifiers, dates, and amounts</div>
              </div>
              <span className="text-[10px] font-bold uppercase text-slate-400">
                {stepsStatus.validating === 'DONE' ? '✓' : stepsStatus.validating === 'RUNNING' ? '...' : ''}
              </span>
            </div>

            {/* Step 4: Matching */}
            <div className="flex items-center gap-3 p-3 rounded-lg border border-slate-100 bg-slate-50">
              {stepsStatus.matching === 'DONE' ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              ) : stepsStatus.matching === 'RUNNING' ? (
                <RefreshCw className="h-5 w-5 text-teal-600 animate-spin shrink-0" />
              ) : (
                <div className="h-5 w-5 rounded-full border border-slate-300 shrink-0" />
              )}
              <div className="flex-1">
                <div className="text-xs font-bold text-slate-900">Cross-File Record Matching</div>
                <div className="text-[11px] text-slate-500">Linking IP/OP, billing, and claims</div>
              </div>
              <span className="text-[10px] font-bold uppercase text-slate-400">
                {stepsStatus.matching === 'DONE' ? '✓' : stepsStatus.matching === 'RUNNING' ? '...' : ''}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* PHASE 3: REVIEW ONLY EXCEPTIONS & CONFIRM */}
      {phase === 'REVIEW' && (
        <div className="space-y-5">
          {/* Executive Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Files Analysed</span>
              <div className="text-xl font-bold text-slate-900 mt-1">{analysisStats.filesCount}</div>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/30 p-4 shadow-2xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">Mapped Automatically</span>
              <div className="text-xl font-bold text-emerald-950 mt-1">{analysisStats.autoMappedFields} fields</div>
            </div>
            <div className={`rounded-xl border p-4 shadow-2xs ${
              analysisStats.totalExceptions > 0 ? 'border-amber-200 bg-amber-50/40' : 'border-slate-200 bg-white'
            }`}>
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800">Requires Review</span>
              <div className="text-xl font-bold text-amber-950 mt-1">{analysisStats.totalExceptions} items</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Ready for Processing</span>
              <div className="text-xl font-bold text-slate-900 mt-1">{formatIndianNumber(analysisStats.totalRecords)} records</div>
            </div>
          </div>

          {/* If NO exceptions exist */}
          {analysisStats.totalExceptions === 0 ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-6 text-center shadow-2xs">
              <CheckCircle2 className="h-8 w-8 text-emerald-600 mx-auto mb-2" />
              <h3 className="text-sm font-bold text-emerald-950">Data is ready for processing.</h3>
              <p className="mt-1 text-xs text-emerald-800">
                All fields mapped with high confidence &bull; No data anomalies detected &bull; Cross-file links verified
              </p>
            </div>
          ) : (
            /* Show ONLY Exceptions that require review */
            <div className="rounded-xl border border-amber-200 bg-white p-5 shadow-2xs space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <span>Review Required ({analysisStats.totalExceptions} Items)</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Review and confirm suggestions for fields with medium/low mapping confidence.
                  </p>
                </div>
              </div>

              {/* Exception Mappings Table */}
              {mappingExceptionsList.length > 0 && (
                <div className="overflow-x-auto rounded-lg border border-slate-200">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 text-[11px] font-bold uppercase text-slate-600 border-b border-slate-200">
                      <tr>
                        <th className="px-3.5 py-2.5">Source File</th>
                        <th className="px-3.5 py-2.5">Hospital Field</th>
                        <th className="px-3.5 py-2.5">Suggested Standard Field</th>
                        <th className="px-3.5 py-2.5">Mapping Confidence</th>
                        <th className="px-3.5 py-2.5 text-right">Confirm</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {mappingExceptionsList.map((item, idx) => {
                        const schema = CANONICAL_SCHEMAS[item.datasetType] || [];
                        return (
                          <tr key={idx} className="hover:bg-slate-50/60">
                            <td className="px-3.5 py-2.5 text-slate-600 font-medium truncate max-w-[140px]">
                              {item.fileName}
                            </td>
                            <td className="px-3.5 py-2.5 font-semibold text-slate-900">
                              {item.mapping.sourceColumn}
                            </td>
                            <td className="px-3.5 py-2.5">
                              <select
                                value={item.mapping.canonicalField}
                                onChange={(e) =>
                                  handleUpdateMappingField(
                                    item.storeKey,
                                    item.mapping.sourceColumn,
                                    e.target.value
                                  )
                                }
                                className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 font-medium focus:border-teal-500"
                              >
                                <option value="">-- Ignore Field --</option>
                                {schema.map((f) => (
                                  <option key={f.key} value={f.key}>
                                    {f.label} ({f.key})
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td className="px-3.5 py-2.5">
                              <span className={`inline-flex rounded px-2 py-0.5 text-[10px] font-bold ${
                                item.mapping.confidence === 'MEDIUM'
                                  ? 'bg-amber-100 text-amber-900 border border-amber-200'
                                  : 'bg-rose-100 text-rose-900 border border-rose-200'
                              }`}>
                                {item.mapping.confidence}
                              </span>
                            </td>
                            <td className="px-3.5 py-2.5 text-right">
                              <button
                                onClick={() =>
                                  handleUpdateMappingField(
                                    item.storeKey,
                                    item.mapping.sourceColumn,
                                    item.mapping.canonicalField
                                  )
                                }
                                className="inline-flex items-center gap-1 rounded bg-teal-50 hover:bg-teal-100 px-2.5 py-1 text-[11px] font-semibold text-teal-800 border border-teal-200 cursor-pointer"
                              >
                                <Check className="h-3 w-3" />
                                <span>Accept</span>
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
              {/* Ambiguous Relationship Review Section */}
              {detectedRelationships.length > 0 && (
                <div className="space-y-3 pt-4 border-t border-slate-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                        Cross-File Dataset Relationships
                      </h4>
                      <p className="text-[11px] text-slate-500">
                        High-confidence links ({detectedRelationships.filter((r) => r.confidence === 'HIGH').length}) accepted automatically. Ambiguous links require verification.
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                    {detectedRelationships.map((rel) => {
                      const isHigh = rel.confidence === 'HIGH';
                      return (
                        <div
                          key={rel.id}
                          className={`p-3 rounded-lg border flex items-center justify-between ${
                            isHigh
                              ? 'bg-emerald-50/50 border-emerald-200 text-emerald-950'
                              : 'bg-amber-50/50 border-amber-200 text-amber-950'
                          }`}
                        >
                          <div>
                            <div className="font-semibold flex items-center gap-1.5">
                              <span>{rel.sourceDataset} &rarr; {rel.targetDataset}</span>
                              <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                                isHigh ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                              }`}>
                                {rel.matchRate}% Match
                              </span>
                            </div>
                            <div className="text-[10px] text-slate-500 mt-0.5">
                              {rel.matchedCount} of {rel.totalSourceCount} records linked via {rel.sourceField}
                            </div>
                          </div>

                          <div>
                            {isHigh ? (
                              <span className="text-[10px] font-bold text-emerald-700 bg-white px-2 py-0.5 rounded border border-emerald-200">
                                Auto-Accepted
                              </span>
                            ) : (
                              <button
                                onClick={() => {
                                  setDetectedRelationships((prev) =>
                                    prev.map((r) =>
                                      r.id === rel.id ? { ...r, confidence: 'HIGH' as const, isValid: true } : r
                                    )
                                  );
                                }}
                                className="inline-flex items-center gap-1 rounded bg-white hover:bg-amber-100 px-2 py-1 text-[10px] font-semibold text-amber-800 border border-amber-200 cursor-pointer"
                              >
                                <Check className="h-3 w-3" />
                                <span>Approve Link</span>
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Confirm & Process Button */}
          <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
            <div className="text-xs text-slate-600">
              Ready to process <strong className="text-slate-900">{formatIndianNumber(analysisStats.totalRecords)}</strong> records into hospital accounts and run financial controls.
            </div>
            <button
              onClick={handleConfirmAndProcess}
              className="inline-flex items-center gap-2 rounded-lg bg-teal-700 hover:bg-teal-800 px-5 py-2.5 text-xs font-semibold text-white shadow-xs transition active:scale-95 cursor-pointer"
            >
              <span>Confirm &amp; Process Data</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* PHASE 4: PROCESSING IN PROGRESS */}
      {phase === 'PROCESSING' && (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center shadow-2xs">
          <RefreshCw className="h-8 w-8 text-teal-600 animate-spin mx-auto mb-3" />
          <h2 className="text-base font-bold text-slate-900">
            Standardising and Ingesting Hospital Data…
          </h2>
          <p className="mt-1.5 text-xs text-slate-500">
            Writing validated records to database and executing C01–C08 revenue controls.
          </p>
        </div>
      )}

      {/* PHASE 5: COMPLETED */}
      {phase === 'COMPLETED' && (
        <div className="rounded-xl border border-emerald-200 bg-white p-8 text-center shadow-2xs">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-700 mx-auto mb-3 border border-emerald-200 shadow-xs">
            <CheckCircle2 className="h-7 w-7" />
          </div>
          <h2 className="text-lg font-bold text-slate-900">
            Hospital Data Ingested &amp; Controls Executed
          </h2>
          <p className="mt-1.5 text-xs text-slate-500 max-w-md mx-auto">
            Successfully standardized and processed <strong>{formatIndianNumber(processedCount)}</strong> records. Deterministic revenue controls C01–C08 have been re-run across all patient encounters.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <button
              onClick={() => onNavigateToTab?.('dashboard')}
              className="inline-flex items-center gap-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 px-4 py-2 text-xs font-semibold text-white shadow-xs transition cursor-pointer"
            >
              <span>View Finance Control Tower</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => onNavigateToTab?.('revenue-controls')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 px-4 py-2 text-xs font-semibold text-slate-700 shadow-xs transition cursor-pointer"
            >
              <span>Inspect Revenue Controls</span>
            </button>
          </div>
        </div>
      )}

      {/* DELETE STORED DATA CONFIRMATION MODAL */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl text-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2 text-rose-700 font-bold text-base">
                <AlertTriangle className="h-5 w-5" />
                <span>Delete All Uploaded Hospital Data?</span>
              </div>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100 cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to permanently delete all uploaded encounters, billing lines, services, claims, and collections from your active workspace?
            </p>

            <div className="rounded-lg bg-rose-50 p-3 border border-rose-200 text-[11px] text-rose-900 space-y-1">
              <div className="font-bold">What happens next:</div>
              <ul className="list-disc list-inside space-y-0.5 text-rose-800">
                <li>All active records, controls (C01–C08), and exceptions will be reset.</li>
                <li>Your workspace returns to a pristine initial empty state.</li>
                <li>You can immediately upload new data files from scratch.</li>
              </ul>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-lg transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onClearWorkspace?.();
                  handleReset();
                  setShowDeleteConfirm(false);
                }}
                className="px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-xs transition cursor-pointer"
              >
                Yes, Delete Stored Data &amp; Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
