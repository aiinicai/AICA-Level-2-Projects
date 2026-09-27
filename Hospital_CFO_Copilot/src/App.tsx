/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useMemo, useState } from 'react';
import { onAuthStateChanged, User as FirebaseUser } from 'firebase/auth';
import { auth } from './firebase';

import { executeBudgetEngine } from './engine/budgetEngine';
import {
  executeDepartmentClearanceEngine,
  generateInitialClearanceRecords,
} from './engine/clearanceEngine';
import { DEFAULT_CONFIG, executeControlEngine } from './engine/controlEngine';
import { executeTariffIntelligenceEngine } from './engine/tariffEngine';
import { authService } from './services/authService';
import { auditService } from './services/auditService';
import {
  subscribeToEncounters,
  subscribeToServices,
  subscribeToBilling,
  subscribeToClaims,
  subscribeToCollections,
  subscribeToTariffMaster,
  subscribeToBudgets,
  subscribeToExceptions,
  subscribeToClearances,
  subscribeToAuditLogs,
  subscribeToControlRuns,
  persistControlRunToFirestore,
  updateExceptionInFirestore,
  updateDepartmentClearanceInFirestore,
  importDatasetToFirestore,
  clearAllFinancialDataInFirestore,
  saveCfoReportToFirestore,
  saveTariffInvestigationToFirestore,
  subscribeToTariffInvestigations,
  BatchImportDatasets,
  FirestoreControlRun,
  FirestoreCfoReport,
  hasActiveSession,
} from './services/firestoreDataService';

import { ArWorkingCapitalView } from './components/ArWorkingCapitalView';
import { AuditEvidenceView } from './components/AuditEvidenceView';
import { BudgetVsActualView } from './components/BudgetVsActualView';
import { CfoCopilotView } from './components/CfoCopilotView';
import { CfoFinancialReviewModal } from './components/CfoFinancialReviewModal';
import { CfoManagementPackModal } from './components/CfoManagementPackModal';
import { executeCfoFinancialReview } from './services/cfoFinancialReviewAgent';
import { ControlSettingsView } from './components/ControlSettingsView';
import { DashboardView } from './components/DashboardView';
import { DataIntelligenceView } from './components/DataIntelligenceView';
import { DepartmentClearanceView } from './components/DepartmentClearanceView';
import { FinancialPerformanceView } from './components/FinancialPerformanceView';
import { LoginView } from './components/LoginView';
import { OfflineIndicator } from './components/OfflineIndicator';
import { ReceivablesCollectionsView } from './components/ReceivablesCollectionsView';
import { RevenueControlsView } from './components/RevenueControlsView';
import { Sidebar } from './components/Sidebar';
import { TariffIntelligenceView } from './components/TariffIntelligenceView';
import { TopBar } from './components/TopBar';
import { CanonicalDatasetType } from './types/ingestion';

import {
  AuditTrailRun,
  Billing,
  BudgetRecord,
  Claim,
  Collection,
  ComprehensiveAuditLog,
  ControlRuleConfig,
  DepartmentClearanceRecord,
  Encounter,
  ExceptionStatus,
  FinancialException,
  HospitalDepartment,
  Service,
  TariffDeviationItem,
  TariffMasterItem,
  UserRole,
  UserSession,
  CfoFinancialReviewBrief,
  CfoReviewProgress,
} from './types';
import { formatINR } from './utils/formatters';
import { calculateArAgeing } from './utils/arCalculations';
import { clearImportedDatasets } from './services/dataStorageService';

export default function App() {
  // Authentication & Session State
  const [currentUser, setCurrentUser] = useState<UserSession | null>(() => {
    return authService.getStoredSession();
  });

  // Active Navigation Tab
  const [currentTab, setCurrentTab] = useState<string>(() => {
    const session = authService.getStoredSession();
    if (session?.role === 'Department Manager') return 'department-clearance';
    if (session?.role === 'Finance/Billing Manager') return 'revenue-controls';
    if (session?.role === 'Auditor') return 'audit-evidence';
    return 'dashboard';
  });

  // Authoritative Datasets State - Starts empty, populated strictly from Firestore
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [billings, setBillings] = useState<Billing[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [tariffMaster, setTariffMaster] = useState<TariffMasterItem[]>([]);
  const [budgetRecords, setBudgetRecords] = useState<BudgetRecord[]>([]);

  // Persistent Tariff Investigation & Override Responses from Firestore
  const [tariffInvestigations, setTariffInvestigations] = useState<
    Record<
      string,
      {
        status: TariffDeviationItem['status'];
        notes?: string;
        investigatedBy?: string;
        updatedAt?: string;
      }
    >
  >({});

  // Persistent Exceptions from Firestore / Control Engine
  const [persistedExceptions, setPersistedExceptions] = useState<FinancialException[]>([]);

  // Persistent Department Clearance Records
  const [clearanceRecords, setClearanceRecords] = useState<DepartmentClearanceRecord[]>([]);

  // Configurable thresholds for deterministic control engine
  const [controlConfig, setControlConfig] = useState<ControlRuleConfig>(DEFAULT_CONFIG);

  // Selected encounter for line-item drill-down
  const [selectedEncounterId, setSelectedEncounterId] = useState<string | null>(null);
  const [selectedException, setSelectedException] = useState<FinancialException | null>(null);

  // Persistent Audit Logs State from Firestore
  const [auditLogs, setAuditLogs] = useState<ComprehensiveAuditLog[]>(() =>
    auditService.getStoredAuditLogs()
  );

  // Persistent Control Runs from Firestore
  const [firestoreControlRuns, setFirestoreControlRuns] = useState<FirestoreControlRun[]>([]);

  // CFO Management Pack Modal
  const [isCfoPackOpen, setIsCfoPackOpen] = useState(false);

  // Agentic CFO Financial Review State
  const [isCfoReviewOpen, setIsCfoReviewOpen] = useState(false);
  const [cfoReviewBrief, setCfoReviewBrief] = useState<CfoFinancialReviewBrief | null>(null);
  const [isCfoReviewRunning, setIsCfoReviewRunning] = useState(false);
  const [cfoReviewProgress, setCfoReviewProgress] = useState<CfoReviewProgress | null>(null);

  // Mobile sidebar open state
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  // Database sync state indicator
  const [isDatabaseReady, setIsDatabaseReady] = useState(false);

  // Firebase Authentication State
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(() => auth.currentUser);

  // Monitor Firebase Auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setFirebaseUser(user);
    });
    return () => unsubscribe();
  }, []);

  // 1. Subscribe to all persistent Firestore collections when user session is active
  useEffect(() => {
    // When no session and not signed in with Firebase Auth, baseline dataset is ready
    if (!currentUser && !firebaseUser && !auth.currentUser) {
      setIsDatabaseReady(true);
      return;
    }

    let isMounted = true;
    let unsubs: Array<() => void> = [];

    async function syncFirestore() {
      try {
        if (!isMounted) return;
        setIsDatabaseReady(true);

        // Attach Real-Time Firestore collection listeners (authoritative data flow)
        unsubs.push(
          subscribeToEncounters((data) => {
            setEncounters(data || []);
          })
        );
        unsubs.push(
          subscribeToServices((data) => {
            setServices(data || []);
          })
        );
        unsubs.push(
          subscribeToBilling((data) => {
            setBillings(data || []);
          })
        );
        unsubs.push(
          subscribeToClaims((data) => {
            setClaims(data || []);
          })
        );
        unsubs.push(
          subscribeToCollections((data) => {
            setCollections(data || []);
          })
        );
        unsubs.push(
          subscribeToTariffMaster((data) => {
            setTariffMaster(data || []);
          })
        );
        unsubs.push(
          subscribeToBudgets((data) => {
            setBudgetRecords(data || []);
          })
        );
        unsubs.push(
          subscribeToExceptions((data) => {
            if (data) setPersistedExceptions(data);
          })
        );
        unsubs.push(
          subscribeToClearances((data) => {
            if (data) setClearanceRecords(data);
          })
        );
        unsubs.push(
          subscribeToAuditLogs((data) => {
            if (data) setAuditLogs(data);
          })
        );
        unsubs.push(
          subscribeToControlRuns((data) => {
            if (data) setFirestoreControlRuns(data);
          })
        );
        unsubs.push(
          subscribeToTariffInvestigations((data) => {
            if (data) setTariffInvestigations((prev) => ({ ...prev, ...data }));
          })
        );
      } catch (err) {
        console.warn('Firestore subscription initialized with local cache fallback:', err);
      }
    }

    syncFirestore();

    return () => {
      isMounted = false;
      unsubs.forEach((unsub) => {
        try {
          unsub();
        } catch {}
      });
    };
  }, [firebaseUser, currentUser]);

  // Login handler with role-based post-login routing
  const handleLoginSuccess = (session: UserSession) => {
    setCurrentUser(session);
    if (session.role === 'CFO') {
      setCurrentTab('dashboard');
    } else if (session.role === 'Finance/Billing Manager') {
      setCurrentTab('revenue-controls');
    } else if (session.role === 'Department Manager') {
      setCurrentTab('department-clearance');
    } else if (session.role === 'Auditor') {
      setCurrentTab('audit-evidence');
    } else {
      setCurrentTab('dashboard');
    }
  };

  // Logout handler
  const handleLogout = async () => {
    if (currentUser) {
      await auditService.logEvent({
        user: currentUser.name,
        role: currentUser.role,
        action: 'LOGOUT',
        entityType: 'Dataset',
        entityId: currentUser.id,
        details: `${currentUser.name} signed out of Hospital CFO Copilot session.`,
      });
    }
    await authService.logout();
    setCurrentUser(null);
  };

  // If encounters is empty but other datasets exist (e.g. billing, services, claims),
  // derive minimal encounter shells so all encounter-based aggregations and controls run seamlessly.
  const effectiveEncounters = useMemo(() => {
    if (encounters.length > 0) return encounters;
    const seen = new Set<string>();
    const derived: Encounter[] = [];
    const addEnc = (encId?: string, dateStr?: string, dept?: string, payer?: string) => {
      if (!encId || seen.has(encId)) return;
      seen.add(encId);
      derived.push({
        Encounter_ID: encId,
        Admission_Date: (dateStr || '').slice(0, 10) || new Date().toISOString().slice(0, 10),
        Discharge_Date: (dateStr || '').slice(0, 10) || new Date().toISOString().slice(0, 10),
        Department: (dept as HospitalDepartment) || 'General',
        Ward: 'Inpatient',
        Bed_Type: 'Standard',
        Payer_Type: payer || 'Self Pay',
        Discharge_Status: 'Discharged',
      });
    };
    billings.forEach((b) => addEnc(b.Encounter_ID, b.Bill_DateTime));
    services.forEach((s) => addEnc(s.Encounter_ID, s.Service_DateTime, s.Revenue_Centre));
    claims.forEach((c) => addEnc(c.Encounter_ID, c.Submission_Date, undefined, c.Payer));
    collections.forEach((col) => addEnc(col.Encounter_ID, col.Receipt_Date));
    return derived;
  }, [encounters, billings, services, claims, collections]);

  // Deterministic Control Engine (C01–C08) execution
  const controlResult = useMemo(() => {
    const role: UserRole = currentUser ? currentUser.role : 'CFO';
    return executeControlEngine(
      effectiveEncounters,
      services,
      billings,
      claims,
      collections,
      controlConfig,
      role,
      persistedExceptions
    );
  }, [
    effectiveEncounters,
    services,
    billings,
    claims,
    collections,
    controlConfig,
    currentUser,
    persistedExceptions,
  ]);

  // Department Clearance Engine Results
  const clearanceSummary = useMemo(() => {
    return executeDepartmentClearanceEngine(clearanceRecords);
  }, [clearanceRecords]);

  // Tariff Intelligence Engine Results
  const tariffSummary = useMemo(() => {
    return executeTariffIntelligenceEngine(
      tariffMaster,
      services,
      billings,
      effectiveEncounters,
      tariffInvestigations
    );
  }, [tariffMaster, services, billings, effectiveEncounters, tariffInvestigations]);

  // Budget vs Actual Engine Results
  const budgetSummary = useMemo(() => {
    return executeBudgetEngine(budgetRecords, services, billings);
  }, [budgetRecords, services, billings]);

  // AR Summary for CFO Management Pack
  const arSummaryForPack = useMemo(() => {
    return calculateArAgeing(effectiveEncounters, billings, collections, claims);
  }, [effectiveEncounters, billings, collections, claims]);

  // TPA totals for CFO Management Pack
  const tpaPackTotals = useMemo(() => {
    const submitted = claims.reduce((s, c) => s + (Number(c.Claim_Amount) || 0), 0);
    const approved = claims.reduce((s, c) => s + (Number(c.Approved_Amount) || 0), 0);
    const pending = claims
      .filter(
        (c) =>
          c.Claim_Status === 'Submitted' ||
          c.Claim_Status === 'Pending Info' ||
          c.Claim_Status === 'Under Query' ||
          c.Claim_Status === 'In Adjudication'
      )
      .reduce((s, c) => s + (Number(c.Claim_Amount) || 0), 0);
    return { submitted, approved, pending };
  }, [claims]);

  // Track if any hospital dataset is currently active in the workspace
  const hasHospitalData =
    encounters.length > 0 ||
    billings.length > 0 ||
    services.length > 0 ||
    claims.length > 0 ||
    collections.length > 0 ||
    tariffMaster.length > 0 ||
    budgetRecords.length > 0;

  // Manual Control Execution Run -> Persists to Firestore
  const handleRunControls = async () => {
    if (!currentUser) return;

    const newRun = executeControlEngine(
      effectiveEncounters,
      services,
      billings,
      claims,
      collections,
      controlConfig,
      currentUser.role,
      persistedExceptions
    );

    const updatedClearances = generateInitialClearanceRecords(
      effectiveEncounters,
      services,
      billings,
      newRun.exceptions
    );

    // Optimistic UI state update
    setPersistedExceptions(newRun.exceptions);
    setClearanceRecords(updatedClearances);

    const runDoc: FirestoreControlRun = {
      runId: newRun.runId,
      executedAt: newRun.auditTrail.Run_Date_Time,
      executedBy: currentUser.name,
      role: currentUser.role,
      recordsProcessed: newRun.auditTrail.Records_Processed,
      exceptionsGenerated: newRun.auditTrail.Exceptions_Generated,
      grossBilling: newRun.metrics.grossBilling,
      potentialExposure: newRun.metrics.potentialFinancialExposure,
      totalExpectedAmount: newRun.metrics.totalExpectedAmount,
      outstandingCollections: newRun.metrics.outstandingCollections,
      tpaPendingAmount: newRun.metrics.tpaPendingAmount,
    };

    try {
      await persistControlRunToFirestore(
        runDoc,
        newRun.exceptions,
        updatedClearances,
        currentUser
      );
    } catch (err) {
      console.warn('Persistent run saved with local cache:', err);
    }
  };

  // Clear all hospital financial records -> Resets workspace to clean state
  const handleResetPlantedData = async () => {
    if (!currentUser) return;

    // Reset local state to empty state
    clearImportedDatasets();
    setEncounters([]);
    setServices([]);
    setBillings([]);
    setClaims([]);
    setCollections([]);
    setTariffMaster([]);
    setBudgetRecords([]);
    setPersistedExceptions([]);
    setClearanceRecords([]);
    setFirestoreControlRuns([]);
    setCfoReviewBrief(null);
    setControlConfig(DEFAULT_CONFIG);
    setSelectedException(null);
    setSelectedEncounterId(null);
    setTariffInvestigations({});

    await auditService.logEvent({
      user: currentUser.name,
      role: currentUser.role,
      action: 'DATA_IMPORT',
      entityType: 'Dataset',
      entityId: 'WORKSPACE_RESET',
      details: `${currentUser.name} reset hospital workspace and deleted all uploaded financial data.`,
    });

    if (hasActiveSession()) {
      try {
        await clearAllFinancialDataInFirestore(currentUser);
      } catch (err) {
        console.error('Error clearing database in Firestore:', err);
      }
    }
  };

  // Exception update workflow -> Persists to Firestore
  const handleUpdateException = async (
    exceptionId: string,
    updates: {
      status: ExceptionStatus;
      assignedTo: string;
      resolution: string;
    }
  ) => {
    if (!currentUser) return;
    const nowStr = new Date().toISOString().split('T')[0];

    const matchExc = controlResult.exceptions.find((e) => e.Exception_ID === exceptionId);
    const encounterId = matchExc?.Encounter_ID || 'N/A';

    // Optimistic local state update
    setPersistedExceptions((prev) =>
      prev.map((e) =>
        e.Exception_ID === exceptionId
          ? {
              ...e,
              Status: updates.status,
              Assigned_To: updates.assignedTo,
              Resolution: updates.resolution,
              Resolved_Date: updates.status === 'RESOLVED' ? nowStr : null,
            }
          : e
      )
    );

    if (auth.currentUser) {
      try {
        await updateExceptionInFirestore(
          exceptionId,
          {
            Status: updates.status,
            Assigned_To: updates.assignedTo,
            Resolution: updates.resolution,
            Resolved_Date: updates.status === 'RESOLVED' ? nowStr : null,
          },
          currentUser,
          encounterId
        );
      } catch (err) {
        console.error('Failed to persist exception resolution in Firestore:', err);
      }
    }
  };

  // Department clearance verification / dispute workflow -> Persists to Firestore
  const handleUpdateClearance = async (
    recordId: string,
    updates: {
      status: DepartmentClearanceRecord['status'];
      comment?: string;
      evidenceRef?: string;
    }
  ) => {
    if (!currentUser) return;

    // Optimistic local update
    setClearanceRecords((prev) =>
      prev.map((r) =>
        r.id === recordId
          ? {
              ...r,
              status: updates.status,
              comment: updates.comment !== undefined ? updates.comment : r.comment,
              evidenceRef: updates.evidenceRef !== undefined ? updates.evidenceRef : r.evidenceRef,
            }
          : r
      )
    );

    if (auth.currentUser) {
      try {
        await updateDepartmentClearanceInFirestore(
          recordId,
          {
            status: updates.status,
            comment: updates.comment,
            evidenceRef: updates.evidenceRef,
          },
          currentUser
        );
      } catch (err) {
        console.error('Failed to persist department clearance in Firestore:', err);
      }
    }
  };

  // Dataset import handler -> Persists to Firestore
  const handleUpdateDataset = async (
    type: 'encounters' | 'services' | 'billing' | 'claims' | 'collections',
    data: unknown[]
  ) => {
    if (!currentUser) return;

    // Optimistic local state update
    if (type === 'encounters') setEncounters(data as Encounter[]);
    if (type === 'services') setServices(data as Service[]);
    if (type === 'billing') setBillings(data as Billing[]);
    if (type === 'claims') setClaims(data as Claim[]);
    if (type === 'collections') setCollections(data as Collection[]);

    if (auth.currentUser) {
      try {
        await importDatasetToFirestore(type, data, currentUser);
      } catch (err) {
        console.error(`Failed to import ${type} dataset into Firestore:`, err);
      }
    }
  };

  // Helper to ensure primary key uniqueness across datasets
  const deduplicateById = <T,>(items: T[], keyFn: (item: T) => string): T[] => {
    const map = new Map<string, T>();
    for (const item of items) {
      if (!item) continue;
      const key = keyFn(item);
      if (key) {
        map.set(key, item);
      }
    }
    return Array.from(map.values());
  };

  // Handle in-memory dataset updates after automated import
  const handleUpdateDatasetInApp = (datasetType: CanonicalDatasetType, newRecords: unknown[]) => {
    if (datasetType === 'encounters') {
      const recs = deduplicateById(newRecords as Encounter[], (e) => e.Encounter_ID);
      setEncounters(recs);
    } else if (datasetType === 'services') {
      const recs = deduplicateById(newRecords as Service[], (s) => s.Service_ID);
      setServices(recs);
    } else if (datasetType === 'billing') {
      const recs = deduplicateById(newRecords as Billing[], (b) => b.Bill_ID);
      setBillings(recs);
    } else if (datasetType === 'claims') {
      const recs = deduplicateById(newRecords as Claim[], (c) => c.Claim_ID);
      setClaims(recs);
    } else if (datasetType === 'collections') {
      const recs = deduplicateById(newRecords as Collection[], (c) => c.Receipt_ID);
      setCollections(recs);
    } else if (datasetType === 'tariff_master') {
      const recs = deduplicateById(newRecords as TariffMasterItem[], (t) => `${t.Service_Code}::${t.Payer}`);
      setTariffMaster(recs);
    } else if (datasetType === 'budgets') {
      const recs = deduplicateById(newRecords as BudgetRecord[], (b) => `${b.Department}::${b.Month}`);
      setBudgetRecords(recs);
    }
  };

  const handleBatchUpdateDatasets = (batchData: BatchImportDatasets) => {
    if (batchData.encounters && batchData.encounters.length > 0) {
      setEncounters((prev) => deduplicateById([...prev, ...batchData.encounters!], (e) => e.Encounter_ID));
    }
    if (batchData.services && batchData.services.length > 0) {
      setServices((prev) => deduplicateById([...prev, ...batchData.services!], (s) => s.Service_ID));
    }
    if (batchData.billing && batchData.billing.length > 0) {
      setBillings((prev) => deduplicateById([...prev, ...batchData.billing!], (b) => b.Bill_ID));
    }
    if (batchData.claims && batchData.claims.length > 0) {
      setClaims((prev) => deduplicateById([...prev, ...batchData.claims!], (c) => c.Claim_ID));
    }
    if (batchData.collections && batchData.collections.length > 0) {
      setCollections((prev) => deduplicateById([...prev, ...batchData.collections!], (c) => c.Receipt_ID));
    }
    if (batchData.tariffs && batchData.tariffs.length > 0) {
      setTariffMaster((prev) => deduplicateById([...prev, ...batchData.tariffs!], (t) => `${t.Service_Code}::${t.Payer}`));
    }
    if (batchData.budgets && batchData.budgets.length > 0) {
      setBudgetRecords((prev) => deduplicateById([...prev, ...batchData.budgets!], (b) => `${b.Department}::${b.Month}`));
    }
  };

  // Tariff investigation handler -> Optimistic UI + Persists to Firestore
  const handleInvestigateTariffDeviation = async (
    deviationId: string,
    updates: {
      status: TariffDeviationItem['status'];
      notes?: string;
    }
  ) => {
    const invRecord = {
      status: updates.status,
      notes: updates.notes || '',
      investigatedBy: currentUser?.name || 'Authorized User',
      updatedAt: new Date().toISOString(),
    };

    // Immediate local state update
    setTariffInvestigations((prev) => ({
      ...prev,
      [deviationId]: invRecord,
    }));

    // Persist to Firestore
    if (auth.currentUser) {
      try {
        await saveTariffInvestigationToFirestore({
          deviationId,
          status: updates.status,
          notes: updates.notes,
          investigatedBy: currentUser?.name || 'Authorized User',
          investigatedAt: new Date().toISOString(),
        });
      } catch (err) {
        console.error('Failed to persist tariff investigation in Firestore:', err);
      }
    }

    // Audit Log
    if (currentUser) {
      await auditService.logEvent({
        user: currentUser.name,
        role: currentUser.role,
        action: 'TARIFF_INVESTIGATION',
        entityType: 'Tariff',
        entityId: deviationId,
        details: `Investigated tariff variance: marked as ${updates.status}. Notes: ${updates.notes || 'None'}`,
      });
    }
  };

  // Department Manager navigation guard: default to department-clearance for strictly executive views
  useEffect(() => {
    if (
      currentUser?.role === 'Department Manager' &&
      (currentTab === 'dashboard' ||
        currentTab === 'financial-performance' ||
        currentTab === 'receivables-collections')
    ) {
      setCurrentTab('department-clearance');
    }
  }, [currentUser, currentTab]);

  // Drilldown handler to encounter financial view
  const handleSelectEncounter = (encounterId: string | null) => {
    setSelectedEncounterId(encounterId);
    if (encounterId) {
      setCurrentTab('revenue-controls');
    }
  };

  // Save CFO Management Dossier to Firestore
  const handleOpenCfoPack = async () => {
    setIsCfoPackOpen(true);
    if (currentUser && (currentUser.role === 'CFO' || currentUser.role === 'Finance/Billing Manager')) {
      const report: FirestoreCfoReport = {
        reportId: `REP-${Date.now()}`,
        generatedAt: new Date().toISOString(),
        generatedBy: currentUser.name,
        role: currentUser.role,
        runId: controlResult.runId,
        grossBilling: controlResult.metrics.grossBilling,
        potentialExposure: controlResult.metrics.potentialFinancialExposure,
        outstandingAr: controlResult.metrics.outstandingCollections,
        departmentClearancePct: clearanceSummary.clearancePercent,
        title: `Hospital CFO Boardroom Report - Run ${controlResult.runId}`,
      };
      try {
        await saveCfoReportToFirestore(report, currentUser);
      } catch (err) {
        console.warn('Saved report locally:', err);
      }
    }
  };

  // Agentic CFO Financial Review Execution
  const handleRunCfoReview = async () => {
    if (!currentUser) return;
    if (currentUser.role !== 'CFO' && currentUser.role !== 'Finance/Billing Manager') {
      alert('Access Restricted: Only CFO and Finance/Billing Managers can initiate the institutional review.');
      return;
    }

    setIsCfoReviewRunning(true);
    setCfoReviewProgress({ step: 1, totalSteps: 10, label: 'Control Position', isComplete: false, stageId: 'CONTROL_POSITION', stageStatus: 'RUNNING' });

    try {
      const brief = await executeCfoFinancialReview({
        user: currentUser,
        controlResult,
        encounters: effectiveEncounters,
        services,
        billings,
        claims,
        collections,
        tariffMaster,
        tariffSummary: tariffSummary.summary,
        tariffDeviations: tariffSummary.deviations,
        budgetRecords,
        budgetSummary,
        clearanceRecords,
        clearanceSummary,
        onProgress: setCfoReviewProgress,
      });

      setCfoReviewBrief(brief);

      await auditService.logEvent({
        user: currentUser.name,
        role: currentUser.role,
        action: 'CFO_REVIEW_GENERATED',
        entityType: 'Report',
        entityId: brief.briefId,
        details: `Generated CFO Financial Review Briefing (${brief.narrativeSource}). Potential Exposure: ₹${brief.groundedFigures.potentialExposure.toLocaleString('en-IN')}, Open Exceptions: ${brief.groundedFigures.openExceptionsCount}.`,
      });
    } catch (err) {
      console.error('Failed to execute CFO Financial Review:', err);
    } finally {
      setIsCfoReviewRunning(false);
    }
  };

  // Human CFO Approval Workflow
  const handleApproveCfoReview = async (brief: CfoFinancialReviewBrief, notes?: string) => {
    if (!currentUser) return;
    if (currentUser.role !== 'CFO') {
      alert('Access Restricted: Institutional financial review sign-off requires CFO executive authority.');
      return;
    }

    const approvedBrief: CfoFinancialReviewBrief = {
      ...brief,
      status: 'APPROVED',
      approvedAt: new Date().toISOString(),
      approvedBy: currentUser.name,
      approvalNotes: notes || '',
    };

    setCfoReviewBrief(approvedBrief);

    // 1. Audit trail logging
    await auditService.logEvent({
      user: currentUser.name,
      role: currentUser.role,
      action: 'CFO_REVIEW_APPROVED',
      entityType: 'Report',
      entityId: brief.briefId,
      details: `CFO ${currentUser.name} officially approved Financial Review Briefing ${brief.briefId}. Sign-off Notes: "${notes || 'No notes'}"`,
    });

    // 2. Persist to Firestore cfo_reports collection
    if (hasActiveSession()) {
      const report: FirestoreCfoReport = {
        reportId: brief.briefId,
        generatedAt: brief.generatedAt,
        generatedBy: brief.generatedBy,
        role: brief.userRole,
        runId: brief.runId,
        grossBilling: brief.groundedFigures.grossBilling,
        potentialExposure: brief.groundedFigures.potentialExposure,
        outstandingAr: brief.groundedFigures.totalAR,
        departmentClearancePct: brief.groundedFigures.clearancePercent,
        title: `Approved CFO Financial Review Briefing - ${brief.briefId}`,
      };
      try {
        await saveCfoReportToFirestore(report, currentUser);
      } catch (err) {
        console.warn('Saved report locally:', err);
      }
    }
  };

  // If user is not authenticated, render Login Page
  if (!currentUser) {
    return <LoginView onLoginSuccess={handleLoginSuccess} />;
  }

  // Control runs list for audit evidence
  const allControlRuns: AuditTrailRun[] = [controlResult.auditTrail];

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-900 antialiased flex font-sans">
      {/* Left-side Vertical Navigation (fixed on desktop, drawer on mobile) */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={(tabId) => {
          setSelectedEncounterId(null);
          setSelectedException(null);
          setCurrentTab(tabId);
        }}
        currentUser={currentUser}
        onLogout={handleLogout}
        isOpenMobile={isMobileNavOpen}
        onCloseMobile={() => setIsMobileNavOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-64">
        {/* Top Header Bar */}
        <TopBar
          currentTab={currentTab}
          onOpenMobileMenu={() => setIsMobileNavOpen(true)}
          currentUser={currentUser}
          onRunControls={handleRunControls}
          onOpenManagementPack={handleOpenCfoPack}
          onClearWorkspace={handleResetPlantedData}
          hasData={hasHospitalData}
        />

        {/* Main Content Workspace */}
        <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-6 sm:px-6">
          {/* 1. DASHBOARD / FINANCE CONTROL TOWER */}
          {currentTab === 'dashboard' && (
            <DashboardView
              metrics={controlResult.metrics}
              clearanceSummary={clearanceSummary}
              tariffSummary={tariffSummary.summary}
              hasData={hasHospitalData}
              encounters={effectiveEncounters}
              billings={billings}
              claims={claims}
              collections={collections}
              controlRuns={firestoreControlRuns}
              onSelectEncounter={handleSelectEncounter}
              onSelectException={(exc) => {
                setSelectedException(exc);
                setSelectedEncounterId(null);
                setCurrentTab('revenue-controls');
              }}
              onNavigateToTab={(tab) => {
                setSelectedEncounterId(null);
                setCurrentTab(tab);
              }}
              onOpenManagementPack={handleOpenCfoPack}
              onOpenCfoReview={() => {
                setIsCfoReviewOpen(true);
                if (!cfoReviewBrief) {
                  handleRunCfoReview();
                }
              }}
              currentUser={currentUser}
            />
          )}

          {/* 2. BILLING & REVENUE CONTROLS */}
          {currentTab === 'revenue-controls' && (
            <RevenueControlsView
              metrics={controlResult.metrics}
              exceptions={controlResult.exceptions}
              encounters={effectiveEncounters}
              services={services}
              billings={billings}
              claims={claims}
              collections={collections}
              dischargeMonitor={controlResult.dischargeMonitor}
              currentUser={currentUser}
              selectedEncounterId={selectedEncounterId}
              selectedException={selectedException}
              onSelectEncounter={setSelectedEncounterId}
              onSelectException={setSelectedException}
              onUpdateException={handleUpdateException}
            />
          )}

          {/* 3. DEPARTMENTAL BILLING REVIEW */}
          {currentTab === 'department-clearance' && (
            <DepartmentClearanceView
              records={clearanceRecords}
              summary={clearanceSummary}
              encounters={effectiveEncounters}
              currentUser={currentUser}
              onUpdateClearanceRecord={handleUpdateClearance}
              onSelectEncounter={handleSelectEncounter}
              onNavigateToTab={(tab) => setCurrentTab(tab)}
            />
          )}

          {/* 4. TARIFF & RATE REVIEW */}
          {currentTab === 'tariff-intelligence' && (
            <TariffIntelligenceView
              tariffMaster={tariffMaster}
              deviations={tariffSummary.deviations}
              summary={tariffSummary.summary}
              currentUser={currentUser}
              onInvestigateDeviation={handleInvestigateTariffDeviation}
              onSelectEncounter={handleSelectEncounter}
              onNavigateToTab={(tab) => setCurrentTab(tab)}
            />
          )}

          {/* 5. RECEIVABLES & COLLECTIONS */}
          {(currentTab === 'receivables-collections' ||
            currentTab === 'ar-working-capital' ||
            currentTab === 'tpa-collections') && (
            <ReceivablesCollectionsView
              encounters={effectiveEncounters}
              billings={billings}
              claims={claims}
              collections={collections}
              onSelectEncounter={handleSelectEncounter}
              onNavigateToTab={(tab) => setCurrentTab(tab)}
            />
          )}

          {/* 6. FINANCIAL PERFORMANCE */}
          {currentTab === 'financial-performance' && (
            <FinancialPerformanceView
              encounters={effectiveEncounters}
              services={services}
              billings={billings}
              budgetSummary={budgetSummary}
              currentUser={currentUser}
              onNavigateToTab={(tab) => setCurrentTab(tab)}
            />
          )}

          {/* 7. BUDGET VS ACTUAL */}
          {currentTab === 'budget-vs-actual' && (
            <BudgetVsActualView
              summary={budgetSummary}
              currentUser={currentUser}
              onNavigateToTab={(tab) => setCurrentTab(tab)}
            />
          )}

          {/* 8. CFO COPILOT */}
          {currentTab === 'cfo-copilot' && (
            <CfoCopilotView
              metrics={controlResult.metrics}
              exceptions={controlResult.exceptions}
              dischargeMonitor={controlResult.dischargeMonitor}
              onSelectEncounter={handleSelectEncounter}
              onNavigateToTab={(tab) => setCurrentTab(tab)}
              extraContext={{
                pendingClearanceCount: clearanceSummary.pendingCount,
                tariffVarianceExposure: tariffSummary.summary.underbilledExposure,
                budgetVariance: budgetSummary.totalRevenueVariance,
                totalAR: controlResult.metrics.outstandingCollections,
                knownPayers: Array.from(new Set(claims.map((c) => c.Payer).filter((p): p is string => Boolean(p)))),
              }}
            />
          )}

          {/* 9. DATA IMPORT & MAPPING */}
          {(currentTab === 'data-intelligence' || currentTab === 'data-controls') && (
            <DataIntelligenceView
              currentUser={currentUser}
              onRunControlsAfterImport={handleRunControls}
              onUpdateDatasetInApp={handleUpdateDatasetInApp}
              onBatchUpdateDatasets={handleBatchUpdateDatasets}
              onClearWorkspace={handleResetPlantedData}
              hasData={hasHospitalData}
              onNavigateToTab={(tab) => {
                setSelectedEncounterId(null);
                setCurrentTab(tab);
              }}
            />
          )}

          {/* 10. AUDIT TRAIL */}
          {currentTab === 'audit-evidence' && (
            <AuditEvidenceView
              auditLogs={auditLogs}
              controlRuns={allControlRuns}
              exceptions={controlResult.exceptions}
              encounters={effectiveEncounters}
              currentUser={currentUser}
              onSelectEncounter={handleSelectEncounter}
              onNavigateToTab={(tab) => setCurrentTab(tab)}
            />
          )}

          {/* 11. CONTROL SETTINGS */}
          {(currentTab === 'control-settings' ||
            currentTab === 'admin' ||
            currentTab === 'administration') && (
            <ControlSettingsView
              config={controlConfig}
              auditTrail={allControlRuns}
              currentUser={currentUser}
              onUpdateConfig={setControlConfig}
              onRunControls={handleRunControls}
            />
          )}
        </main>
      </div>

      {/* CFO Management Pack Printable Dossier Modal */}
      <CfoManagementPackModal
        isOpen={isCfoPackOpen}
        onClose={() => setIsCfoPackOpen(false)}
        metrics={controlResult.metrics}
        exceptions={controlResult.exceptions}
        clearanceSummary={clearanceSummary}
        currentUser={currentUser}
        runId={controlResult.runId}
        arSummary={arSummaryForPack}
        totalClaimsSubmitted={tpaPackTotals.submitted}
        totalApproved={tpaPackTotals.approved}
        totalPending={tpaPackTotals.pending}
      />

      {/* Agentic CFO Financial Review Modal */}
      <CfoFinancialReviewModal
        isOpen={isCfoReviewOpen}
        onClose={() => setIsCfoReviewOpen(false)}
        currentUser={currentUser}
        brief={cfoReviewBrief}
        isRunning={isCfoReviewRunning}
        progress={cfoReviewProgress}
        onRegenerate={handleRunCfoReview}
        onApprove={handleApproveCfoReview}
        onSelectEncounter={handleSelectEncounter}
        hasData={hasHospitalData}
      />

      {/* Offline Status Badge */}
      <OfflineIndicator />
    </div>
  );
}
