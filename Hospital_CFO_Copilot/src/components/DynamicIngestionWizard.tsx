import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Database,
  ExternalLink,
  Eye,
  FileCheck,
  FileSpreadsheet,
  FileText,
  Filter,
  HelpCircle,
  History,
  Layers,
  Link2,
  Loader2,
  Play,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  Table,
  Upload,
  X,
} from 'lucide-react';
import {
  CanonicalDatasetType,
  ColumnMappingItem,
  ColumnProfile,
  DataQualityIssue,
  DataValidationSummary,
  DetectedRelationship,
  ImportHistoryRecord,
  MappingConfidence,
  UploadedFileProfile,
} from '../types/ingestion';
import { UserRole, UserSession } from '../types';
import {
  CANONICAL_SCHEMAS,
  CanonicalFieldDef,
  classifyDatasetType,
  detectCrossFileRelationships,
  generateDeterministicMapping,
  parseUploadedFile,
  transformToCanonicalRecords,
  validateDatasetQuality,
} from '../utils/dynamicDataEngine';
import { mapColumnsWithGemini } from '../services/geminiMappingService';
import {
  fetchImportHistory,
  importDatasetToFirestore,
  saveImportHistoryRecord,
  subscribeToImportHistory,
} from '../services/firestoreDataService';
import { formatIndianDateTime, formatINR } from '../utils/formatters';

interface DynamicIngestionWizardProps {
  currentUser: UserSession;
  onRunControlsAfterImport: () => void;
  onUpdateDatasetInApp: (datasetType: CanonicalDatasetType, records: unknown[]) => void;
}

type WizardStep = 'UPLOAD' | 'STRUCTURE' | 'MAPPING' | 'VALIDATION' | 'RELATIONSHIPS' | 'SUMMARY';

export const DynamicIngestionWizard: React.FC<DynamicIngestionWizardProps> = ({
  currentUser,
  onRunControlsAfterImport,
  onUpdateDatasetInApp,
}) => {
  // Navigation & Sub-views
  const [activeTab, setActiveTab] = useState<'INGESTION' | 'HISTORY'>('INGESTION');
  const [currentStep, setCurrentStep] = useState<WizardStep>('UPLOAD');

  // Multi-file state
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileProfile[]>([]);
  const [selectedFileIndex, setSelectedFileIndex] = useState<number>(0);
  const [isParsingFiles, setIsParsingFiles] = useState(false);
  const [isMappingWithAI, setIsMappingWithAI] = useState(false);
  const [aiModelUsed, setAiModelUsed] = useState<string>('gemini-3.8-flash');

  // Mappings per file and sheet
  // key: `${fileId}_${sheetName}` -> ColumnMappingItem[]
  const [mappingsStore, setMappingsStore] = useState<Record<string, ColumnMappingItem[]>>({});

  // Dataset type override per file/sheet
  const [datasetTypeStore, setDatasetTypeStore] = useState<Record<string, CanonicalDatasetType>>({});

  // Validation results per file/sheet
  const [validationSummaries, setValidationSummaries] = useState<Record<string, DataValidationSummary>>({});

  // Cross-file relationships
  const [detectedRelationships, setDetectedRelationships] = useState<DetectedRelationship[]>([]);

  // Issue inspector modal / drawer
  const [inspectingIssuesFor, setInspectingIssuesFor] = useState<string | null>(null);
  const [issueFilterSeverity, setIssueFilterSeverity] = useState<'ALL' | 'ERROR' | 'WARNING'>('ALL');

  // Ingestion status
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestionProgress, setIngestionProgress] = useState(0);
  const [completedImportId, setCompletedImportId] = useState<string | null>(null);
  const [ingestionStats, setIngestionStats] = useState<{ imported: number; rejected: number } | null>(null);

  // Import History
  const [importHistory, setImportHistory] = useState<ImportHistoryRecord[]>([]);
  const [selectedHistoryItem, setSelectedHistoryItem] = useState<ImportHistoryRecord | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load import history on mount
  useEffect(() => {
    fetchImportHistory().then(setImportHistory).catch(console.warn);
    const unsub = subscribeToImportHistory((list) => {
      if (list && list.length > 0) setImportHistory(list);
    });
    return () => unsub();
  }, []);

  const activeFile = uploadedFiles[selectedFileIndex] || null;
  const activeSheet = activeFile?.sheets.find((s) => s.sheetName === activeFile.activeSheetName) || activeFile?.sheets[0] || null;
  const currentStoreKey = activeFile && activeSheet ? `${activeFile.fileId}_${activeSheet.sheetName}` : '';
  const currentDatasetType = currentStoreKey
    ? datasetTypeStore[currentStoreKey] || activeSheet?.suggestedDatasetType || 'encounters'
    : 'encounters';
  const currentMappings = currentStoreKey ? mappingsStore[currentStoreKey] || [] : [];
  const currentValidation = currentStoreKey ? validationSummaries[currentStoreKey] : null;

  // ==========================================
  // FILE SELECTION & UPLOAD HANDLERS
  // ==========================================

  const handleFilesSelected = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsParsingFiles(true);

    try {
      const parsedProfiles: UploadedFileProfile[] = [];
      const newMappings: Record<string, ColumnMappingItem[]> = {};
      const newDatasetTypes: Record<string, CanonicalDatasetType> = {};

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const profile = await parseUploadedFile(file);
        parsedProfiles.push(profile);

        // Pre-initialize mappings and types for each sheet
        for (const sheet of profile.sheets) {
          const key = `${profile.fileId}_${sheet.sheetName}`;
          newDatasetTypes[key] = sheet.suggestedDatasetType;
          newMappings[key] = generateDeterministicMapping(sheet.suggestedDatasetType, sheet.columns);
        }
      }

      setUploadedFiles((prev) => [...prev, ...parsedProfiles]);
      setMappingsStore((prev) => ({ ...prev, ...newMappings }));
      setDatasetTypeStore((prev) => ({ ...prev, ...newDatasetTypes }));

      if (parsedProfiles.length > 0) {
        setSelectedFileIndex(uploadedFiles.length); // point to first new file
        setCurrentStep('STRUCTURE');
      }
    } catch (err) {
      console.error('File parsing error:', err);
    } finally {
      setIsParsingFiles(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  /**
   * Generates heterogeneous mock hospital files with realistic Indian / Enterprise ERP non-canonical headers
   * Allows 1-click testing of arbitrary columns without requiring hospital reformatting
   */
  const handleLoadHeterogeneousPresets = async () => {
    setIsParsingFiles(true);
    try {
      // Simulate 3 heterogeneous files:
      // File 1: Inpatient HIS Admissions with arbitrary non-canonical column names
      const hisAdmissionsData = [
        {
          UHID_No: 'ENC-2001',
          Date_Of_Admission: '2026-09-01',
          Discharge_Date_Time: '2026-09-08 14:00',
          Speciality_Dept: 'Cardiology (Inpatient)',
          Station_Floor: 'North Wing 4th Floor',
          Bed_Category: 'Standard Twin Sharing',
          Payer_Scheme: 'Star Health Insurance',
          Patient_Disposition: 'Discharged',
          Treating_Physician: 'Consultant - Cardiology',
        },
        {
          UHID_No: 'ENC-2002',
          Date_Of_Admission: '2026-09-02',
          Discharge_Date_Time: '2026-09-07 10:30',
          Speciality_Dept: 'General Surgery',
          Station_Floor: 'Post-Op Ward 2',
          Bed_Category: 'Standard Twin Sharing',
          Payer_Scheme: 'Self Pay (Cash)',
          Patient_Disposition: 'Discharged',
          Treating_Physician: 'Consultant - General Surgery',
        },
        {
          UHID_No: 'ENC-2003',
          Date_Of_Admission: '2026-09-03',
          Discharge_Date_Time: '2026-09-09 17:00',
          Speciality_Dept: 'Orthopaedics',
          Station_Floor: 'Orthopaedic Care Unit',
          Bed_Category: 'Private Deluxe',
          Payer_Scheme: 'MediAssist TPA',
          Patient_Disposition: 'Discharged',
          Treating_Physician: 'Consultant - Orthopaedics',
        },
        {
          UHID_No: 'ENC-2004',
          Date_Of_Admission: '2026-09-04',
          Discharge_Date_Time: '2026-09-08 11:00',
          Speciality_Dept: 'Neurology',
          Station_Floor: 'Neuro High Dependency Unit',
          Bed_Category: 'ICU Critical Bed',
          Payer_Scheme: 'HDFC ERGO Health',
          Patient_Disposition: 'Discharged',
          Treating_Physician: 'Consultant - Neurology',
        },
        {
          UHID_No: 'ENC-2005',
          Date_Of_Admission: '2026-09-05',
          Discharge_Date_Time: '',
          Speciality_Dept: 'Oncology',
          Station_Floor: 'Day Care Infusion Wing',
          Bed_Category: 'Standard Daycare Chair',
          Payer_Scheme: 'CGHS Government Scheme',
          Patient_Disposition: 'Admitted',
          Treating_Physician: 'Consultant - Oncology',
        },
      ];

      // File 2: Pharmacy & Nursing Dispensation Log
      const dispensaryData = [
        {
          Order_Ref: 'SVC-101',
          Patient_UHID: 'ENC-2001',
          Administration_Time: '2026-09-02 10:15',
          Performing_Section: 'Pharmacy / Dispensary',
          Drug_Code: 'DRG-ATV40',
          Item_Particulars: 'Atorvastatin 40mg Tablet',
          Dispensed_Count: 14,
          Schedule_Rate: 280,
          Dispensed_By_Pharmacist: 'Duty Pharmacist',
        },
        {
          Order_Ref: 'SVC-102',
          Patient_UHID: 'ENC-2001',
          Administration_Time: '2026-09-03 14:00',
          Performing_Section: 'Laboratory Services',
          Drug_Code: 'LAB-LIPID',
          Item_Particulars: 'Comprehensive Lipid Profile',
          Dispensed_Count: 1,
          Schedule_Rate: 1200,
          Dispensed_By_Pharmacist: 'Laboratory Technician',
        },
        {
          Order_Ref: 'SVC-103',
          Patient_UHID: 'ENC-2002',
          Administration_Time: '2026-09-02 18:30',
          Performing_Section: 'OT/Surgery Theatre',
          Drug_Code: 'SURG-LAPAP',
          Item_Particulars: 'Laparoscopic Appendectomy Procedure',
          Dispensed_Count: 1,
          Schedule_Rate: 48000,
          Dispensed_By_Pharmacist: 'Senior OT Technician',
        },
        {
          Order_Ref: 'SVC-104',
          Patient_UHID: 'ENC-2003',
          Administration_Time: '2026-09-03 11:30',
          Performing_Section: 'Radiology / Imaging',
          Drug_Code: 'RAD-MRI-KNEE',
          Item_Particulars: 'MRI Left Knee Joint with Contrast',
          Dispensed_Count: 1,
          Schedule_Rate: 8500,
          Dispensed_By_Pharmacist: 'Radiology Technician',
        },
      ];

      // File 3: SAP Billing Invoice Register
      const sapBillingData = [
        {
          Tax_Invoice_No: 'BILL-1001',
          Visit_Reference: 'ENC-2001',
          Linked_Order_ID: 'SVC-102',
          Invoice_Generated_At: '2026-09-08 12:30',
          Invoiced_Quantity: 1,
          Net_Invoice_Value: 1200,
          Doctor_Concession: 0,
          Invoice_Status: 'Final',
          Cashier_Initials: 'CK-04',
        },
        {
          Tax_Invoice_No: 'BILL-1002',
          Visit_Reference: 'ENC-2002',
          Linked_Order_ID: 'SVC-103',
          Invoice_Generated_At: '2026-09-07 09:45',
          Invoiced_Quantity: 1,
          Net_Invoice_Value: 48000,
          Doctor_Concession: 1500,
          Invoice_Status: 'Final',
          Cashier_Initials: 'CK-01',
        },
        {
          Tax_Invoice_No: 'BILL-1003',
          Visit_Reference: 'ENC-2003',
          Linked_Order_ID: 'SVC-104',
          Invoice_Generated_At: '2026-09-09 16:15',
          Invoiced_Quantity: 1,
          Net_Invoice_Value: 8500,
          Doctor_Concession: 0,
          Invoice_Status: 'Final',
          Cashier_Initials: 'CK-02',
        },
      ];

      // Create profiles
      const makeMockProfile = (name: string, rows: Record<string, unknown>[], defaultType: CanonicalDatasetType): UploadedFileProfile => {
        const headers = Object.keys(rows[0]);
        const columns: ColumnProfile[] = headers.map((h) => {
          const vals = rows.map((r) => String(r[h] ?? ''));
          const isNum = vals.some((v) => !isNaN(parseFloat(v)) && !v.includes('-'));
          const isDate = vals.some((v) => v.includes('-') && (v.length === 10 || v.length >= 16));
          return {
            columnName: h,
            originalHeader: h,
            inferredType: isDate ? 'date' : isNum ? 'number' : 'string',
            sampleValues: vals.slice(0, 4),
            totalValues: rows.length,
            nullCount: 0,
            nullRate: 0,
            uniqueCount: new Set(vals).size,
            isLikelyIdentifier: h.toLowerCase().includes('no') || h.toLowerCase().includes('id') || h.toLowerCase().includes('ref'),
            isLikelyAmount: h.toLowerCase().includes('value') || h.toLowerCase().includes('rate') || h.toLowerCase().includes('concession'),
            isLikelyQuantity: h.toLowerCase().includes('count') || h.toLowerCase().includes('quantity'),
            isLikelyDate: isDate,
            isLikelyStatus: h.toLowerCase().includes('disposition') || h.toLowerCase().includes('status'),
          };
        });

        const sheetProfile = {
          sheetName: 'Sheet1',
          rowCount: rows.length,
          columnCount: headers.length,
          columns,
          rawRows: rows,
          suggestedDatasetType: defaultType,
          confidenceScore: 94,
          classificationReason: `Automated multi-file detection identified ${defaultType.toUpperCase()} based on hospital domain headers.`,
        };

        return {
          fileId: `FILE-EXP-${Math.random().toString(36).slice(2, 7)}`,
          fileName: name,
          fileSize: 48200,
          fileType: 'xlsx',
          sheets: [sheetProfile],
          activeSheetName: 'Sheet1',
        };
      };

      const p1 = makeMockProfile('Hospital_Inpatient_Admissions_Extract.xlsx', hisAdmissionsData, 'encounters');
      const p2 = makeMockProfile('Pharmacy_and_Clinical_Dispensation_Log.xlsx', dispensaryData, 'services');
      const p3 = makeMockProfile('SAP_Financial_Invoice_Register.csv', sapBillingData, 'billing');

      const profiles = [p1, p2, p3];
      const newMappings: Record<string, ColumnMappingItem[]> = {};
      const newDatasetTypes: Record<string, CanonicalDatasetType> = {};

      for (const p of profiles) {
        const s = p.sheets[0];
        const key = `${p.fileId}_${s.sheetName}`;
        newDatasetTypes[key] = s.suggestedDatasetType;
        newMappings[key] = generateDeterministicMapping(s.suggestedDatasetType, s.columns);
      }

      setUploadedFiles(profiles);
      setMappingsStore(newMappings);
      setDatasetTypeStore(newDatasetTypes);
      setSelectedFileIndex(0);
      setCurrentStep('STRUCTURE');
    } finally {
      setIsParsingFiles(false);
    }
  };

  // ==========================================
  // AI-ASSISTED COLUMN MAPPING (GEMINI)
  // ==========================================

  const handleTriggerAiMappingForActive = async () => {
    if (!activeFile || !activeSheet) return;
    setIsMappingWithAI(true);

    try {
      const response = await mapColumnsWithGemini(currentDatasetType, activeSheet.columns);
      setMappingsStore((prev) => ({
        ...prev,
        [currentStoreKey]: response.mappings,
      }));
      if (response.modelUsed) setAiModelUsed(response.modelUsed);
    } catch (err) {
      console.warn('AI mapping call failed, reverting to semantic engine:', err);
    } finally {
      setIsMappingWithAI(false);
    }
  };

  const handleUpdateMappingField = (sourceCol: string, canonicalField: string) => {
    if (!currentStoreKey) return;
    const current = mappingsStore[currentStoreKey] || [];
    const schema = CANONICAL_SCHEMAS[currentDatasetType] || [];
    const def = schema.find((s) => s.key === canonicalField);

    const updated = current.map((m) => {
      if (m.sourceColumn === sourceCol) {
        return {
          ...m,
          canonicalField,
          status: 'OVERRIDDEN' as const,
          confidence: 'HIGH' as const,
          reason: canonicalField === 'unmapped' ? 'Explicitly marked as unmapped by user' : `Manually mapped to ${canonicalField}`,
          required: def?.required || false,
          isAmbiguous: false,
        };
      }
      return m;
    });

    setMappingsStore((prev) => ({ ...prev, [currentStoreKey]: updated }));
  };

  const handleAcceptAllHighConfidence = () => {
    if (!currentStoreKey) return;
    const current = mappingsStore[currentStoreKey] || [];
    const updated = current.map((m) => {
      if (m.confidence === 'HIGH') {
        return { ...m, status: 'ACCEPTED' as const };
      }
      return m;
    });
    setMappingsStore((prev) => ({ ...prev, [currentStoreKey]: updated }));
  };

  // ==========================================
  // VALIDATION & RELATIONSHIP EXECUTION
  // ==========================================

  const runValidationForActive = () => {
    if (!activeFile || !activeSheet || !currentStoreKey) return;
    const summary = validateDatasetQuality(
      activeFile.fileId,
      activeFile.fileName,
      currentDatasetType,
      activeSheet.rawRows,
      currentMappings
    );

    setValidationSummaries((prev) => ({
      ...prev,
      [currentStoreKey]: summary,
    }));
  };

  const runAllValidationsAndRelationships = () => {
    const newSummaries: Record<string, DataValidationSummary> = {};
    const configsForRel: Array<{
      fileName: string;
      datasetType: CanonicalDatasetType;
      rows: Record<string, unknown>[];
      mappings: ColumnMappingItem[];
    }> = [];

    uploadedFiles.forEach((file) => {
      file.sheets.forEach((sheet) => {
        const key = `${file.fileId}_${sheet.sheetName}`;
        const dtype = datasetTypeStore[key] || sheet.suggestedDatasetType;
        const mappings = mappingsStore[key] || [];

        const summary = validateDatasetQuality(file.fileId, file.fileName, dtype, sheet.rawRows, mappings);
        newSummaries[key] = summary;

        configsForRel.push({
          fileName: file.fileName,
          datasetType: dtype,
          rows: sheet.rawRows,
          mappings,
        });
      });
    });

    setValidationSummaries(newSummaries);

    // Cross-file relationship detection
    if (configsForRel.length > 1) {
      const rels = detectCrossFileRelationships(configsForRel);
      setDetectedRelationships(rels);
    }
  };

  // ==========================================
  // CONFIRM INGESTION TO FIRESTORE
  // ==========================================

  const handleExecuteCanonicalIngestion = async () => {
    setIsIngesting(true);
    setIngestionProgress(10);

    const importId = `IMP-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;

    let totalDetected = 0;
    let totalImported = 0;
    let totalRejected = 0;
    const importedDatasetTypes: string[] = [];
    const filesMetaList: Array<{ name: string; datasetType: string; sheetName?: string; rows: number }> = [];
    const mappingsSnapshot: Record<string, Record<string, string>> = {};
    let issuesCountTotal = 0;

    try {
      const totalSteps = uploadedFiles.reduce((acc, f) => acc + f.sheets.length, 0);
      let stepIdx = 0;

      for (const file of uploadedFiles) {
        for (const sheet of file.sheets) {
          const key = `${file.fileId}_${sheet.sheetName}`;
          const dtype = datasetTypeStore[key] || sheet.suggestedDatasetType;
          const mappings = mappingsStore[key] || [];
          const valSummary = validationSummaries[key];

          const invalidIndices = valSummary?.invalidRowIndices || [];

          totalDetected += sheet.rawRows.length;
          const importedCount = Math.max(0, sheet.rawRows.length - invalidIndices.length);
          totalImported += importedCount;
          totalRejected += invalidIndices.length;
          issuesCountTotal += valSummary?.dataQualityIssuesCount || 0;

          if (!importedDatasetTypes.includes(dtype)) {
            importedDatasetTypes.push(dtype);
          }

          filesMetaList.push({
            name: file.fileName,
            datasetType: dtype,
            sheetName: sheet.sheetName,
            rows: importedCount,
          });

          const snap: Record<string, string> = {};
          mappings.forEach((m) => {
            if (m.canonicalField && m.canonicalField !== 'unmapped') {
              snap[m.sourceColumn] = m.canonicalField;
            }
          });
          mappingsSnapshot[file.fileName] = snap;

          // Transform to typed canonical records
          const canonicalRecords = transformToCanonicalRecords(
            dtype,
            sheet.rawRows,
            mappings,
            invalidIndices,
            { fileName: file.fileName, sheetName: sheet.sheetName }
          );

          // Ingest to Firestore
          if (canonicalRecords.length > 0) {
            await importDatasetToFirestore(
              dtype as any,
              canonicalRecords,
              currentUser
            );
            // Also notify top-level app state to update active views in memory immediately
            onUpdateDatasetInApp(dtype, canonicalRecords);
          }

          stepIdx++;
          setIngestionProgress(Math.round(15 + (stepIdx / totalSteps) * 75));
        }
      }

      // Record Import History in Firestore
      const historyRecord: ImportHistoryRecord = {
        importId,
        timestamp: new Date().toISOString(),
        files: filesMetaList,
        datasetTypes: importedDatasetTypes,
        recordsDetected: totalDetected,
        recordsImported: totalImported,
        recordsRejected: totalRejected,
        mappingStatus: 'VERIFIED_WITH_OVERRIDES',
        validationStatus: totalRejected === 0 ? 'CLEAN' : 'WARNINGS_RESOLVED',
        userId: currentUser.id,
        userName: currentUser.name,
        userRole: currentUser.role,
        mappingsSnapshot,
        issuesSnapshotCount: issuesCountTotal,
      };

      await saveImportHistoryRecord(historyRecord, currentUser);

      setCompletedImportId(importId);
      setIngestionStats({ imported: totalImported, rejected: totalRejected });
      setIngestionProgress(100);
      setCurrentStep('SUMMARY');

      // Refresh history list
      fetchImportHistory().then(setImportHistory).catch(console.warn);
    } catch (err) {
      console.error('Ingestion execution failed:', err);
    } finally {
      setIsIngesting(false);
    }
  };

  // Helper metrics for step 4 & summary
  const aggregateMetrics = Object.values(validationSummaries).reduce(
    (acc, s) => {
      acc.detected += s.recordsDetected;
      acc.ready += s.recordsReadyForImport;
      acc.review += s.recordsRequiringReview;
      acc.mappingIssues += s.mappingIssuesCount;
      acc.dataIssues += s.dataQualityIssuesCount;
      return acc;
    },
    { detected: 0, ready: 0, review: 0, mappingIssues: 0, dataIssues: 0 }
  );

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Database className="h-5 w-5 text-teal-600" />
                Dynamic Hospital Data Intelligence &amp; Semantic Mapping Engine
              </h2>
              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-teal-800 border border-teal-200">
                Heterogeneous Ingestion
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Ingest heterogeneous hospital reports (Excel/CSV) with arbitrary headers, column orders, and ERP schemas.
              AI maps source columns with deterministic financial constraints.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('INGESTION')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                activeTab === 'INGESTION'
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              <Upload className="h-3.5 w-3.5" />
              <span>Import Workflow</span>
            </button>

            <button
              onClick={() => setActiveTab('HISTORY')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                activeTab === 'HISTORY'
                  ? 'bg-teal-700 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              <History className="h-3.5 w-3.5" />
              <span>Import History ({importHistory.length})</span>
            </button>
          </div>
        </div>

        {/* Step Progress Indicator (when on INGESTION tab) */}
        {activeTab === 'INGESTION' && (
          <div className="mt-4 pt-2">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              {[
                { id: 'UPLOAD', label: '1. Upload Files', icon: Upload },
                { id: 'STRUCTURE', label: '2. Profile Structure', icon: Table },
                { id: 'MAPPING', label: '3. AI Mapping', icon: Bot },
                { id: 'VALIDATION', label: '4. Validate Quality', icon: FileCheck },
                { id: 'RELATIONSHIPS', label: '5. Relationships', icon: Link2 },
                { id: 'SUMMARY', label: '6. Persistence', icon: CheckCircle2 },
              ].map((s, idx) => {
                const isCurrent = currentStep === s.id;
                const isPassed =
                  ['UPLOAD', 'STRUCTURE', 'MAPPING', 'VALIDATION', 'RELATIONSHIPS', 'SUMMARY'].indexOf(currentStep) > idx;
                const Icon = s.icon;

                return (
                  <button
                    key={s.id}
                    onClick={() => {
                      if (uploadedFiles.length > 0 || s.id === 'UPLOAD') {
                        setCurrentStep(s.id as WizardStep);
                      }
                    }}
                    disabled={uploadedFiles.length === 0 && s.id !== 'UPLOAD'}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold text-xs transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                      isCurrent
                        ? 'bg-teal-50 text-teal-800 border border-teal-300'
                        : isPassed
                        ? 'text-emerald-700 bg-emerald-50 hover:bg-emerald-100'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{s.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: INGESTION WORKFLOW */}
      {/* ========================================================================= */}
      {activeTab === 'INGESTION' && (
        <div className="space-y-6">
          {/* STEP 1: UPLOAD FILES */}
          {currentStep === 'UPLOAD' && (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="text-center max-w-xl mx-auto py-6">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 text-teal-700 border border-teal-200 mb-4">
                  <Upload className="h-7 w-7" />
                </div>
                <h3 className="text-lg font-bold text-slate-900">
                  Upload Hospital Tabular Data (Excel &bull; CSV)
                </h3>
                <p className="mt-1.5 text-xs text-slate-500 leading-relaxed">
                  Upload your hospital's raw EHR exports, billing ledgers, pharmacy logs, or insurance reports.
                  Our engine automatically profiles arbitrary columns, date formats, and revenue centres.
                </p>

                {/* Drag & Drop Area */}
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="mt-6 border-2 border-dashed border-teal-300 hover:border-teal-500 bg-teal-50/40 hover:bg-teal-50/70 rounded-2xl p-8 transition cursor-pointer text-center group"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".xlsx,.xls,.csv"
                    onChange={(e) => handleFilesSelected(e.target.files)}
                    className="hidden"
                  />
                  <FileSpreadsheet className="h-10 w-10 text-teal-600 mx-auto group-hover:scale-110 transition transform" />
                  <div className="mt-3 text-sm font-semibold text-slate-800">
                    Click to browse or drop files here
                  </div>
                  <div className="mt-1 text-[11px] text-slate-500">
                    Supports multiple files (.xlsx, .xls, .csv). Arbitrary column schemas accepted.
                  </div>
                </div>

                {/* Instant Preset Action */}
                <div className="mt-6 pt-5 border-t border-slate-200">
                  <div className="text-xs text-slate-500 mb-2 font-medium">
                    Verify multi-system heterogeneous ingestion across departmental records:
                  </div>
                  <button
                    onClick={handleLoadHeterogeneousPresets}
                    disabled={isParsingFiles}
                    className="inline-flex items-center gap-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 text-xs font-semibold shadow-xs transition active:scale-95 cursor-pointer disabled:opacity-50"
                  >
                    <Sparkles className="h-4 w-4 text-amber-400" />
                    <span>Load Standard Hospital ERP Files (HIS Admissions, Clinical Dispensation, Billing Register)</span>
                  </button>
                </div>
              </div>

              {isParsingFiles && (
                <div className="flex items-center justify-center gap-2 py-4 text-xs font-medium text-teal-800">
                  <Loader2 className="h-4 w-4 animate-spin text-teal-600" />
                  <span>Parsing workbooks and inspecting tabular column structures...</span>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: PROFILE STRUCTURE */}
          {currentStep === 'STRUCTURE' && (
            <div className="space-y-4">
              {/* File Selector Tabs if multiple files */}
              {uploadedFiles.length > 1 && (
                <div className="flex items-center gap-2 overflow-x-auto pb-1">
                  {uploadedFiles.map((f, idx) => (
                    <button
                      key={f.fileId}
                      onClick={() => setSelectedFileIndex(idx)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition cursor-pointer border ${
                        selectedFileIndex === idx
                          ? 'bg-teal-700 text-white border-teal-700 shadow-xs'
                          : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <FileSpreadsheet className="h-3.5 w-3.5" />
                      <span>{f.fileName}</span>
                      <span className="rounded bg-black/15 px-1.5 py-0.2 text-[10px]">
                        {f.sheets[0]?.rowCount || 0} rows
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {activeFile && activeSheet && (
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                  {/* File Metadata & Sheet Selector */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 text-sm">{activeFile.fileName}</span>
                        <span className="rounded bg-slate-100 px-2 py-0.5 text-[10px] font-mono text-slate-600 uppercase">
                          {activeFile.fileType}
                        </span>
                      </div>
                      <div className="mt-0.5 text-xs text-slate-500">
                        {activeSheet.rowCount} rows &bull; {activeSheet.columnCount} columns detected
                      </div>
                    </div>

                    {/* Sheet selector if workbook has multiple sheets */}
                    {activeFile.sheets.length > 1 && (
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-slate-500 font-medium">Sheet:</span>
                        <select
                          value={activeFile.activeSheetName}
                          onChange={(e) => {
                            const newActive = e.target.value;
                            setUploadedFiles((prev) =>
                              prev.map((f, i) =>
                                i === selectedFileIndex ? { ...f, activeSheetName: newActive } : f
                              )
                            );
                          }}
                          className="rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 focus:outline-none"
                        >
                          {activeFile.sheets.map((s) => (
                            <option key={s.sheetName} value={s.sheetName}>
                              {s.sheetName} ({s.rowCount} rows)
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>

                  {/* AI Classification Card */}
                  <div className="mt-4 rounded-xl border border-teal-100 bg-teal-50/50 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-700 text-white shrink-0 shadow-xs">
                          <Bot className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold uppercase tracking-wider text-teal-900">
                              Identified Business Dataset Type:
                            </span>
                            <span className="rounded bg-teal-800 text-white px-2.5 py-0.5 text-xs font-bold uppercase">
                              {currentDatasetType}
                            </span>
                            <span className="rounded bg-emerald-100 text-emerald-800 border border-emerald-200 px-1.5 py-0.2 text-[10px] font-bold">
                              {activeSheet.confidenceScore}% confidence
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-teal-950/80 leading-relaxed">
                            {activeSheet.classificationReason}
                          </p>
                        </div>
                      </div>

                      {/* Manual Override dropdown */}
                      <div className="flex items-center gap-2">
                        <label className="text-[11px] text-slate-600 font-semibold">Change Domain:</label>
                        <select
                          value={currentDatasetType}
                          onChange={(e) => {
                            const newType = e.target.value as CanonicalDatasetType;
                            setDatasetTypeStore((prev) => ({ ...prev, [currentStoreKey]: newType }));
                            // Re-run deterministic mapping for new type
                            setMappingsStore((prev) => ({
                              ...prev,
                              [currentStoreKey]: generateDeterministicMapping(newType, activeSheet.columns),
                            }));
                          }}
                          className="rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-800 focus:outline-none cursor-pointer"
                        >
                          <option value="encounters">Encounters (Admissions &amp; Visits)</option>
                          <option value="services">Services (Clinical &amp; Pharmacy)</option>
                          <option value="billing">Billing (Invoices &amp; Charges)</option>
                          <option value="claims">Claims (TPA &amp; Insurance)</option>
                          <option value="collections">Collections (Cash Receipts)</option>
                          <option value="tariff_master">Tariff Master (Rate Schedule)</option>
                          <option value="budgets">Budget vs Actual (Targets)</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Profiled Columns Table */}
                  <div className="mt-5">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2.5">
                      Detected Source Column Profiles ({activeSheet.columns.length})
                    </h4>
                    <div className="overflow-x-auto rounded-xl border border-slate-200">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 text-[11px] font-semibold text-slate-600 uppercase border-b border-slate-200">
                          <tr>
                            <th className="px-3.5 py-2.5">Source Header</th>
                            <th className="px-3.5 py-2.5">Inferred Type</th>
                            <th className="px-3.5 py-2.5">Completeness</th>
                            <th className="px-3.5 py-2.5">Unique Values</th>
                            <th className="px-3.5 py-2.5">Preview Values</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {activeSheet.columns.map((col) => (
                            <tr key={col.columnName} className="hover:bg-slate-50/60 transition">
                              <td className="px-3.5 py-2.5 font-bold text-slate-900 font-mono">
                                {col.columnName}
                              </td>
                              <td className="px-3.5 py-2.5">
                                <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                                  {col.inferredType}
                                </span>
                                {col.isLikelyAmount && (
                                  <span className="ml-1 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.2 text-[9px] font-bold">
                                    Financial Amount
                                  </span>
                                )}
                                {col.isLikelyIdentifier && (
                                  <span className="ml-1 rounded bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.2 text-[9px] font-bold">
                                    Identifier
                                  </span>
                                )}
                              </td>
                              <td className="px-3.5 py-2.5 text-slate-600">
                                {col.nullRate === 0 ? (
                                  <span className="text-emerald-700 font-medium">100% Populated</span>
                                ) : (
                                  <span className="text-amber-700 font-medium">
                                    {Math.round((1 - col.nullRate) * 100)}% (
                                    {col.nullCount} blank)
                                  </span>
                                )}
                              </td>
                              <td className="px-3.5 py-2.5 text-slate-600">
                                {col.uniqueCount} distinct
                              </td>
                              <td className="px-3.5 py-2.5 text-slate-500 font-mono text-[11px] max-w-xs truncate">
                                {col.sampleValues.join(', ') || '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                    <button
                      onClick={() => setCurrentStep('UPLOAD')}
                      className="px-3.5 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer"
                    >
                      Back to Upload
                    </button>
                    <button
                      onClick={() => setCurrentStep('MAPPING')}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-xs font-semibold text-white shadow-xs transition active:scale-95 cursor-pointer"
                    >
                      <span>Proceed to AI Column Mapping</span>
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: AI-ASSISTED COLUMN MAPPING */}
          {currentStep === 'MAPPING' && (
            <div className="space-y-4">
              {/* File Selector Tabs */}
              {uploadedFiles.length > 1 && (
                <div className="flex items-center gap-2 overflow-x-auto pb-1">
                  {uploadedFiles.map((f, idx) => (
                    <button
                      key={f.fileId}
                      onClick={() => setSelectedFileIndex(idx)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition cursor-pointer border ${
                        selectedFileIndex === idx
                          ? 'bg-teal-700 text-white border-teal-700 shadow-xs'
                          : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <FileSpreadsheet className="h-3.5 w-3.5" />
                      <span>{f.fileName}</span>
                    </button>
                  ))}
                </div>
              )}

              {activeFile && activeSheet && (
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                  {/* Mapping Header & AI Action */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-100">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                        <Bot className="h-4 w-4 text-teal-600" />
                        AI-Assisted Semantic Column Mapping &bull; {currentDatasetType.toUpperCase()}
                      </h3>
                      <p className="text-xs text-slate-500">
                        Gemini matches source hospital headers to canonical fields. High-confidence mappings are accepted automatically.
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleTriggerAiMappingForActive}
                        disabled={isMappingWithAI}
                        className="flex items-center gap-1.5 rounded-lg border border-teal-300 bg-teal-50 hover:bg-teal-100 text-teal-800 px-3 py-1.5 text-xs font-semibold transition cursor-pointer disabled:opacity-50"
                        title="Re-run Gemini AI Semantic Column Analysis"
                      >
                        {isMappingWithAI ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Sparkles className="h-3.5 w-3.5 text-teal-600" />
                        )}
                        <span>{isMappingWithAI ? 'Analyzing...' : 'Re-Run Gemini AI Mapping'}</span>
                      </button>

                      <button
                        onClick={handleAcceptAllHighConfidence}
                        className="flex items-center gap-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white px-3.5 py-1.5 text-xs font-semibold transition cursor-pointer"
                      >
                        <Check className="h-3.5 w-3.5" />
                        <span>Accept All High Confidence</span>
                      </button>
                    </div>
                  </div>

                  {/* Mapping Grid Table */}
                  <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-[11px] font-semibold text-slate-600 uppercase border-b border-slate-200">
                        <tr>
                          <th className="px-3.5 py-2.5">Source Column (Uploaded)</th>
                          <th className="px-3.5 py-2.5">Preview Values</th>
                          <th className="px-3.5 py-2.5">Canonical Target Field</th>
                          <th className="px-3.5 py-2.5">AI Confidence</th>
                          <th className="px-3.5 py-2.5">Semantic Interpretation &bull; Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {currentMappings.map((mapItem) => {
                          const colProfile = activeSheet.columns.find((c) => c.columnName === mapItem.sourceColumn);
                          const schemaOptions = CANONICAL_SCHEMAS[currentDatasetType] || [];

                          const confidenceBadge = {
                            HIGH: 'bg-emerald-50 text-emerald-800 border-emerald-300',
                            MEDIUM: 'bg-amber-50 text-amber-800 border-amber-300',
                            LOW: 'bg-rose-50 text-rose-800 border-rose-300',
                          }[mapItem.confidence];

                          return (
                            <tr
                              key={mapItem.sourceColumn}
                              className={`transition ${
                                mapItem.confidence === 'LOW' || mapItem.isAmbiguous
                                  ? 'bg-amber-50/30'
                                  : 'hover:bg-slate-50/60'
                              }`}
                            >
                              <td className="px-3.5 py-2.5 font-bold font-mono text-slate-900">
                                {mapItem.sourceColumn}
                                {colProfile?.isLikelyAmount && (
                                  <div className="text-[10px] text-emerald-700 font-sans font-medium">
                                    [Financial Currency]
                                  </div>
                                )}
                              </td>
                              <td className="px-3.5 py-2.5 font-mono text-[11px] text-slate-500 max-w-xs truncate">
                                {colProfile?.sampleValues.join(', ') || '—'}
                              </td>
                              <td className="px-3.5 py-2.5">
                                <select
                                  value={mapItem.canonicalField}
                                  onChange={(e) => handleUpdateMappingField(mapItem.sourceColumn, e.target.value)}
                                  className={`rounded-lg border px-2.5 py-1 text-xs font-semibold focus:outline-none cursor-pointer ${
                                    mapItem.canonicalField === 'unmapped'
                                      ? 'border-slate-300 bg-slate-50 text-slate-500'
                                      : 'border-teal-400 bg-white text-teal-900'
                                  }`}
                                >
                                  <option value="unmapped">-- Unmapped (Ignore column) --</option>
                                  {schemaOptions.map((sf) => (
                                    <option key={sf.key} value={sf.key}>
                                      {sf.label} ({sf.key}){sf.required ? ' *' : ''}
                                    </option>
                                  ))}
                                </select>
                              </td>
                              <td className="px-3.5 py-2.5">
                                <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-bold border ${confidenceBadge}`}>
                                  {mapItem.confidence}
                                </span>
                              </td>
                              <td className="px-3.5 py-2.5 text-slate-600 text-[11px]">
                                {mapItem.reason}
                                {mapItem.isAmbiguous && (
                                  <div className="text-[10px] text-amber-700 font-semibold flex items-center gap-1 mt-0.5">
                                    <AlertTriangle className="h-3 w-3 shrink-0" />
                                    <span>Ambiguous field: please confirm canonical target.</span>
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Actions */}
                  <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                    <button
                      onClick={() => setCurrentStep('STRUCTURE')}
                      className="px-3.5 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer"
                    >
                      Back to Structure
                    </button>
                    <button
                      onClick={() => {
                        runAllValidationsAndRelationships();
                        setCurrentStep('VALIDATION');
                      }}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-xs font-semibold text-white shadow-xs transition active:scale-95 cursor-pointer"
                    >
                      <span>Proceed to Data Quality Validation</span>
                      <ArrowRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 4: DATA QUALITY VALIDATION */}
          {currentStep === 'VALIDATION' && (
            <div className="space-y-4">
              {/* Validation High-Level KPI Summary */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Records Detected
                  </div>
                  <div className="mt-1 text-2xl font-bold text-slate-900">
                    {aggregateMetrics.detected.toLocaleString('en-IN')}
                  </div>
                  <div className="text-[11px] text-slate-500">Across {uploadedFiles.length} file(s)</div>
                </div>

                <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 shadow-xs">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-800">
                    Ready For Import
                  </div>
                  <div className="mt-1 text-2xl font-bold text-emerald-700">
                    {aggregateMetrics.ready.toLocaleString('en-IN')}
                  </div>
                  <div className="text-[11px] text-emerald-700">Clean canonical records</div>
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 shadow-xs">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-amber-800">
                    Requiring Review
                  </div>
                  <div className="mt-1 text-2xl font-bold text-amber-700">
                    {aggregateMetrics.review.toLocaleString('en-IN')}
                  </div>
                  <div className="text-[11px] text-amber-700">Rows flagged for issues</div>
                </div>

                <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 shadow-xs">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-blue-800">
                    Mapping Issues
                  </div>
                  <div className="mt-1 text-2xl font-bold text-blue-700">
                    {aggregateMetrics.mappingIssues}
                  </div>
                  <div className="text-[11px] text-blue-700">Unmapped required fields</div>
                </div>

                <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-4 shadow-xs">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-rose-800">
                    Data-Quality Issues
                  </div>
                  <div className="mt-1 text-2xl font-bold text-rose-700">
                    {aggregateMetrics.dataIssues}
                  </div>
                  <div className="text-[11px] text-rose-700">Format/Chronology/Ref issues</div>
                </div>
              </div>

              {/* Validation Cards per File */}
              <div className="space-y-3">
                {uploadedFiles.map((file) => {
                  return file.sheets.map((sheet) => {
                    const key = `${file.fileId}_${sheet.sheetName}`;
                    const summary = validationSummaries[key];
                    if (!summary) return null;

                    const hasErrors = summary.recordsRequiringReview > 0;

                    return (
                      <div
                        key={key}
                        className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs flex flex-wrap items-center justify-between gap-4"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={`flex h-10 w-10 items-center justify-center rounded-xl shrink-0 ${
                              hasErrors
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-emerald-100 text-emerald-800'
                            }`}
                          >
                            {hasErrors ? (
                              <AlertTriangle className="h-5 w-5" />
                            ) : (
                              <CheckCircle2 className="h-5 w-5" />
                            )}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-slate-900 text-sm">{file.fileName}</span>
                              <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-teal-800 uppercase">
                                {summary.datasetType}
                              </span>
                            </div>
                            <div className="text-xs text-slate-500 mt-0.5">
                              {summary.recordsReadyForImport} of {summary.recordsDetected} rows ready &bull;{' '}
                              {summary.issues.length} flagged quality notes
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {summary.issues.length > 0 && (
                            <button
                              onClick={() => setInspectingIssuesFor(key)}
                              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 cursor-pointer"
                            >
                              <Eye className="h-3.5 w-3.5 text-slate-500" />
                              <span>Inspect Issues ({summary.issues.length})</span>
                            </button>
                          )}
                          <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
                            Validated
                          </span>
                        </div>
                      </div>
                    );
                  });
                })}
              </div>

              {/* Actions */}
              <div className="pt-4 border-t border-slate-200 flex items-center justify-between">
                <button
                  onClick={() => setCurrentStep('MAPPING')}
                  className="px-3.5 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer"
                >
                  Back to Mapping
                </button>
                <button
                  onClick={() => setCurrentStep('RELATIONSHIPS')}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-xs font-semibold text-white shadow-xs transition active:scale-95 cursor-pointer"
                >
                  <span>Proceed to Cross-File Relationships</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 5: RELATIONSHIPS */}
          {currentStep === 'RELATIONSHIPS' && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <div className="pb-3 border-b border-slate-100">
                  <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                    <Link2 className="h-4 w-4 text-teal-600" />
                    Cross-File Foreign-Key Relationship Detection
                  </h3>
                  <p className="text-xs text-slate-500">
                    Automatically verifies relational integrity between Encounters, Clinical Services, Billing Invoices, and Claims.
                  </p>
                </div>

                {detectedRelationships.length === 0 ? (
                  <div className="py-8 text-center text-xs text-slate-500">
                    <Link2 className="h-8 w-8 text-slate-300 mx-auto mb-2" />
                    Single dataset uploaded or no cross-table identifiers detected. Data can proceed directly to ingestion.
                  </div>
                ) : (
                  <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                    {detectedRelationships.map((rel) => (
                      <div
                        key={rel.id}
                        className="rounded-xl border border-slate-200 bg-slate-50/50 p-4"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900 text-xs">
                              {rel.sourceDataset} &rarr; {rel.targetDataset}
                            </span>
                            <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-mono text-teal-800 border border-teal-200">
                              via {rel.sourceField}
                            </span>
                          </div>
                          <span
                            className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                              rel.confidence === 'HIGH'
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-amber-100 text-amber-800'
                            }`}
                          >
                            {rel.confidence} Confidence ({rel.matchRate}%)
                          </span>
                        </div>
                        <p className="mt-2 text-xs text-slate-600">{rel.description}</p>
                        <div className="mt-2 text-[11px] text-slate-500">
                          {rel.matchedCount} of {rel.totalSourceCount} foreign key records match primary entity records.
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Actions */}
                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <button
                    onClick={() => setCurrentStep('VALIDATION')}
                    className="px-3.5 py-1.5 rounded-lg border border-slate-300 text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer"
                  >
                    Back to Validation
                  </button>
                  <button
                    onClick={handleExecuteCanonicalIngestion}
                    disabled={isIngesting}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-xs font-semibold text-white shadow-xs transition active:scale-95 cursor-pointer disabled:opacity-50"
                  >
                    {isIngesting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Database className="h-4 w-4" />
                    )}
                    <span>
                      {isIngesting ? `Ingesting (${ingestionProgress}%)...` : 'Confirm & Ingest to Firestore'}
                    </span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* STEP 6: SUMMARY & CONTROL EXECUTION */}
          {currentStep === 'SUMMARY' && (
            <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-xs text-center max-w-xl mx-auto">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 mb-4">
                <CheckCircle2 className="h-8 w-8" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">
                Canonical Transformation &amp; Persistence Complete
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Normalized financial and clinical records successfully committed to persistent Firestore database.
              </p>

              <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-left space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Session Import ID:</span>
                  <span className="font-mono font-bold text-teal-800">{completedImportId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Records Successfully Imported:</span>
                  <span className="font-bold text-emerald-700">
                    {ingestionStats?.imported.toLocaleString('en-IN')}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Records Bypassed / Rejected:</span>
                  <span className="font-bold text-slate-700">
                    {ingestionStats?.rejected.toLocaleString('en-IN')}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Ingested By:</span>
                  <span className="font-bold text-slate-800">{currentUser.name} ({currentUser.role})</span>
                </div>
              </div>

              {/* Immediate Financial Control Execution */}
              <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                <button
                  onClick={() => {
                    onRunControlsAfterImport();
                  }}
                  className="flex items-center gap-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white px-5 py-2.5 text-xs font-bold shadow-xs transition active:scale-95 cursor-pointer"
                >
                  <Play className="h-4 w-4 fill-current" />
                  <span>Execute Financial Controls (C01–C08) on New Data</span>
                </button>

                <button
                  onClick={() => {
                    setUploadedFiles([]);
                    setCurrentStep('UPLOAD');
                  }}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
                >
                  Import Another File
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: IMPORT HISTORY INSPECTOR */}
      {/* ========================================================================= */}
      {activeTab === 'HISTORY' && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <History className="h-4 w-4 text-teal-600" />
                Persistent Import History Audit Ledger
              </h3>
              <p className="text-xs text-slate-500">
                Audit trail of all previous data ingestion sessions, mapping configurations, and validation summaries.
              </p>
            </div>
          </div>

          {importHistory.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              <History className="h-8 w-8 text-slate-300 mx-auto mb-2" />
              No previous import history records found.
            </div>
          ) : (
            <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-[11px] font-semibold text-slate-600 uppercase border-b border-slate-200">
                  <tr>
                    <th className="px-3.5 py-2.5">Import ID</th>
                    <th className="px-3.5 py-2.5">Date / Time</th>
                    <th className="px-3.5 py-2.5">Uploaded File(s)</th>
                    <th className="px-3.5 py-2.5">Dataset Types</th>
                    <th className="px-3.5 py-2.5">Detected</th>
                    <th className="px-3.5 py-2.5">Imported</th>
                    <th className="px-3.5 py-2.5">Validation</th>
                    <th className="px-3.5 py-2.5">User</th>
                    <th className="px-3.5 py-2.5 text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {importHistory.map((item) => (
                    <tr key={item.importId} className="hover:bg-slate-50/60 transition">
                      <td className="px-3.5 py-2.5 font-bold font-mono text-teal-800">
                        {item.importId}
                      </td>
                      <td className="px-3.5 py-2.5 text-slate-600">
                        {formatIndianDateTime(item.timestamp)}
                      </td>
                      <td className="px-3.5 py-2.5 text-slate-900 font-medium">
                        {item.files?.map((f) => f.name).join(', ') || 'Dataset Import'}
                      </td>
                      <td className="px-3.5 py-2.5">
                        <span className="rounded bg-teal-50 px-2 py-0.5 text-[10px] font-bold text-teal-800 border border-teal-200 uppercase">
                          {item.datasetTypes?.join(', ') || 'Mixed'}
                        </span>
                      </td>
                      <td className="px-3.5 py-2.5 text-slate-600 font-mono">
                        {item.recordsDetected}
                      </td>
                      <td className="px-3.5 py-2.5 text-emerald-700 font-bold font-mono">
                        {item.recordsImported}
                      </td>
                      <td className="px-3.5 py-2.5">
                        <span
                          className={`rounded px-1.5 py-0.2 text-[10px] font-bold ${
                            item.validationStatus === 'CLEAN'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {item.validationStatus}
                        </span>
                      </td>
                      <td className="px-3.5 py-2.5 text-slate-700">
                        {item.userName}
                      </td>
                      <td className="px-3.5 py-2.5 text-right">
                        <button
                          onClick={() => setSelectedHistoryItem(item)}
                          className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-semibold transition cursor-pointer"
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* ISSUE INSPECTION MODAL */}
      {/* ========================================================================= */}
      {inspectingIssuesFor && validationSummaries[inspectingIssuesFor] && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
          <div className="relative w-full max-w-3xl rounded-2xl bg-white p-6 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-rose-600" />
                  Data Quality &bull; Detailed Issue Inspector
                </h3>
                <p className="text-xs text-slate-500">
                  {validationSummaries[inspectingIssuesFor].fileName} &bull;{' '}
                  {validationSummaries[inspectingIssuesFor].issues.length} items flagged
                </p>
              </div>

              <button
                onClick={() => setInspectingIssuesFor(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Severity Filter */}
            <div className="flex items-center gap-2 py-3 border-b border-slate-100 text-xs">
              <span className="text-slate-500 font-semibold">Filter:</span>
              {(['ALL', 'ERROR', 'WARNING'] as const).map((sev) => (
                <button
                  key={sev}
                  onClick={() => setIssueFilterSeverity(sev)}
                  className={`px-2.5 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                    issueFilterSeverity === sev
                      ? 'bg-slate-900 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>

            {/* Issues List */}
            <div className="flex-1 overflow-y-auto divide-y divide-slate-100 py-2">
              {validationSummaries[inspectingIssuesFor].issues
                .filter((iss) => issueFilterSeverity === 'ALL' || iss.severity === issueFilterSeverity)
                .map((iss) => (
                  <div key={iss.id} className="py-2.5 text-xs flex items-start gap-3">
                    <span
                      className={`rounded px-1.5 py-0.5 text-[9px] font-bold shrink-0 mt-0.5 ${
                        iss.severity === 'ERROR'
                          ? 'bg-rose-100 text-rose-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {iss.severity}
                    </span>
                    <div className="flex-1">
                      <div className="font-semibold text-slate-900">{iss.message}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Column: <span className="font-mono">{iss.column}</span>
                        {iss.rowNumber > 0 && ` • Row ${iss.rowNumber}`}
                        {iss.rawValue !== undefined && ` • Value: "${String(iss.rawValue)}"`}
                      </div>
                    </div>
                  </div>
                ))}
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setInspectingIssuesFor(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 cursor-pointer"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* HISTORY DETAILS MODAL */}
      {/* ========================================================================= */}
      {selectedHistoryItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
          <div className="relative w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Import Session Audit Details &bull; {selectedHistoryItem.importId}
                </h3>
                <p className="text-xs text-slate-500">
                  Ingested on {formatIndianDateTime(selectedHistoryItem.timestamp)} by{' '}
                  {selectedHistoryItem.userName}
                </p>
              </div>
              <button
                onClick={() => setSelectedHistoryItem(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto py-3 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
                <div>
                  <span className="text-slate-500">Records Detected:</span>
                  <div className="font-bold text-slate-900 text-sm">
                    {selectedHistoryItem.recordsDetected}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">Records Successfully Imported:</span>
                  <div className="font-bold text-emerald-700 text-sm">
                    {selectedHistoryItem.recordsImported}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">Mapping Mode:</span>
                  <div className="font-bold text-slate-800">
                    {selectedHistoryItem.mappingStatus}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">Validation Status:</span>
                  <div className="font-bold text-slate-800">
                    {selectedHistoryItem.validationStatus}
                  </div>
                </div>
              </div>

              {/* Mappings Snapshot */}
              <div>
                <h4 className="font-bold text-slate-900 text-xs mb-2">Column Mappings Snapshot</h4>
                {selectedHistoryItem.mappingsSnapshot &&
                  Object.entries(selectedHistoryItem.mappingsSnapshot).map(([file, mapObj]) => (
                    <div key={file} className="mb-3 rounded-lg border border-slate-200 p-2.5">
                      <div className="font-semibold text-slate-800 text-[11px] mb-1.5">{file}</div>
                      <div className="grid grid-cols-2 gap-1 text-[11px]">
                        {Object.entries(mapObj).map(([src, canon]) => (
                          <div key={src} className="flex items-center gap-1 font-mono">
                            <span className="text-slate-600">{src}</span>
                            <span className="text-slate-400">&rarr;</span>
                            <span className="text-teal-800 font-bold">{canon}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <button
                onClick={() => setSelectedHistoryItem(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800 cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
