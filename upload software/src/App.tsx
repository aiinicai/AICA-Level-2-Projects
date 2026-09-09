import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { WorkflowStepper } from './components/WorkflowStepper';
import { ControlSheetView } from './components/ControlSheetView';
import { TrialBalanceView } from './components/TrialBalanceView';
import { ClassificationStudio } from './components/ClassificationStudio';
import { ProfitAndLossView } from './components/ProfitAndLossView';
import { BalanceSheetView } from './components/BalanceSheetView';
import { SchedulesView } from './components/SchedulesView';
import { DepreciationScheduleView } from './components/DepreciationScheduleView';
import { NotesToAccountsView } from './components/NotesToAccountsView';
import { ReconciliationView } from './components/ReconciliationView';
import { EntityDetailsModal } from './components/EntityDetailsModal';
import { AdjustmentsModal } from './components/AdjustmentsModal';
import { AiAssistantModal } from './components/AiAssistantModal';
import { PptDeckModal } from './components/PptDeckModal';
import { LoginScreen } from './components/LoginScreen';
import { UserManagementModal } from './components/UserManagementModal';
import { EntityVaultModal } from './components/EntityVaultModal';

import {
  ActiveTab,
  BalanceSheetHeadConfig,
  DepreciationAssetItem,
  EntityDetails,
  LedgerItem,
  ManualAdjustment,
  NoteToAccountItem,
  AppUser,
  SavedEntityWorkspace,
} from './types/accounting';
import {
  DEFAULT_ENTITIES,
  DEFAULT_HEAD_CONFIGS,
  SAMPLE_APEX_TRIAL_BALANCE,
  SAMPLE_KOTHARI_TRIAL_BALANCE,
} from './utils/defaultData';
import {
  DEFAULT_DEPRECIATION_ASSETS,
  DEFAULT_STANDARD_NOTES,
} from './utils/nonCorporateDefaults';
import { classifyLedgersWithRuleEngine } from './utils/classificationEngine';
import { isNonLedgerText } from './utils/excelParser';
import { extractAssetsFromTrialBalance } from './utils/depreciationParser';
import {
  matchAndMergePreviousYearTrialBalance,
  clearPreviousYearBalances,
  normalizeLedgerName,
} from './utils/previousYearMatcher';
import {
  calculateBalanceSheetSummary,
  calculatePLStatement,
  calculateReconciliation,
  calculateSchedules,
} from './utils/calculator';
import {
  getSavedRulesMap,
  getSavedCustomHeadsConfig,
  saveCustomHeadsConfig,
} from './utils/classificationRulesService';
import { generateBalanceSheetExcelWorkbook } from './utils/excelGenerator';
import { generateBalanceSheetPDF } from './utils/pdfGenerator';
import { downloadPresentationFile } from './utils/presentationGenerator';
import { authService } from './utils/authService';
import { entityVaultService } from './utils/entityVaultService';
import { CheckCircle2, Info } from 'lucide-react';

export default function App() {
  // Authentication State
  const [currentUser, setCurrentUser] = useState<AppUser | null>(() => authService.getCurrentUser());
  const [isUserManagementOpen, setIsUserManagementOpen] = useState(false);
  const [isEntityVaultOpen, setIsEntityVaultOpen] = useState(false);
  const [pendingUsersCount, setPendingUsersCount] = useState(0);
  const [savedEntitiesCount, setSavedEntitiesCount] = useState(0);
  const [isSavingEntity, setIsSavingEntity] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Navigation State
  const [activeTab, setActiveTab] = useState<ActiveTab>('control');
  const [selectedScheduleNo, setSelectedScheduleNo] = useState<string | number>(1);

  // Core Data States
  const [entity, setEntity] = useState<EntityDetails>(DEFAULT_ENTITIES[0]);
  const [heads, setHeads] = useState<BalanceSheetHeadConfig[]>(() => {
    return getSavedCustomHeadsConfig(DEFAULT_HEAD_CONFIGS);
  });

  // Initialize ledgers classified with rule engine and saved user rules
  const [ledgers, setLedgers] = useState<LedgerItem[]>(() => {
    const initialHeads = getSavedCustomHeadsConfig(DEFAULT_HEAD_CONFIGS);
    return classifyLedgersWithRuleEngine(SAMPLE_APEX_TRIAL_BALANCE, initialHeads, getSavedRulesMap());
  });

  // Default Closing Stock Adjustment
  const [adjustments, setAdjustments] = useState<ManualAdjustment[]>([
    {
      id: 'adj-initial-stock',
      type: 'CLOSING_STOCK',
      description: 'Closing Inventory as on 31st March 2025',
      debitHead: 'A03',
      creditHead: 'PL_DIRECT_INCOME',
      amount: 425000,
    },
  ]);

  // Modals
  const [isEntityModalOpen, setIsEntityModalOpen] = useState(false);
  const [isAdjustmentsModalOpen, setIsAdjustmentsModalOpen] = useState(false);
  const [isAiModalOpen, setIsAiModalOpen] = useState(false);
  const [isPptModalOpen, setIsPptModalOpen] = useState(false);
  const [isExportingExcel, setIsExportingExcel] = useState(false);

  // Depreciation Schedule & Notes to Accounts States
  const [depreciationAssets, setDepreciationAssets] = useState<DepreciationAssetItem[]>(DEFAULT_DEPRECIATION_ASSETS);
  const [notesToAccounts, setNotesToAccounts] = useState<NoteToAccountItem[]>(DEFAULT_STANDARD_NOTES);

  // Refresh counts on mount or user change
  const refreshStats = useCallback(async () => {
    try {
      const list = await entityVaultService.listSavedEntities();
      setSavedEntitiesCount(list.length);

      if (currentUser?.role === 'ADMIN') {
        const users = await authService.getAllUsers();
        const pending = users.filter((u) => u.status === 'PENDING').length;
        setPendingUsersCount(pending);
      }
    } catch (e) {
      console.error('Failed to refresh stats:', e);
    }
  }, [currentUser]);

  useEffect(() => {
    if (currentUser) {
      refreshStats();
    }
  }, [currentUser, refreshStats]);

  // ============================================================
  // CALCULATIONS ENGINE (Reactive and instantaneous)
  // ============================================================
  const plStatement = useMemo(() => {
    return calculatePLStatement(ledgers, adjustments);
  }, [ledgers, adjustments]);

  const schedules = useMemo(() => {
    return calculateSchedules(heads, ledgers, plStatement, adjustments);
  }, [heads, ledgers, plStatement, adjustments]);

  const balanceSheet = useMemo(() => {
    return calculateBalanceSheetSummary(heads, schedules);
  }, [heads, schedules]);

  const reconciliation = useMemo(() => {
    return calculateReconciliation(ledgers, balanceSheet, plStatement);
  }, [ledgers, balanceSheet, plStatement]);

  // ============================================================
  // ENTITY DATA SAVE & FETCH (AUDIT VAULT)
  // ============================================================
  const handleSaveCurrentWorkspace = async (versionTag: string, notes: string): Promise<{ success: boolean; error?: string }> => {
    setIsSavingEntity(true);
    try {
      const workspace: SavedEntityWorkspace = {
        id: `ws-${entity.id}`,
        entityId: entity.id,
        entityName: entity.name,
        entityType: entity.entityType,
        financialYear: entity.financialYear,
        balanceSheetDate: entity.balanceSheetDate,
        savedAt: new Date().toISOString(),
        savedBy: currentUser?.id || 'admin',
        versionTag: versionTag || 'Working Audit Copy',
        notes,
        summary: {
          totalAssets: balanceSheet.totalAssets,
          totalLiabilities: balanceSheet.totalLiabilities,
          netProfit: plStatement.netProfitOrLoss,
          isBalanced: reconciliation.isBalanceSheetBalanced,
          difference: reconciliation.balanceSheetDifference,
          ledgersCount: ledgers.length,
          adjustmentsCount: adjustments.length,
          assetsCount: depreciationAssets.length,
        },
        data: {
          entity,
          ledgers,
          headConfigs: heads,
          adjustments,
          depreciationAssets,
          notesToAccounts,
        },
      };

      const res = await entityVaultService.saveEntityWorkspace(workspace);
      if (res.success) {
        await refreshStats();
        setToastMessage(`Saved "${entity.name}" to Entity Vault successfully.`);
        setTimeout(() => setToastMessage(null), 4000);
        return { success: true };
      }
      return { success: false, error: res.error };
    } catch (err: any) {
      return { success: false, error: err.message || 'Error saving workspace' };
    } finally {
      setIsSavingEntity(false);
    }
  };

  const handleQuickSaveEntity = async () => {
    await handleSaveCurrentWorkspace('Audit Workspace Snapshot', 'Quick saved via top bar action');
  };

  const handleFetchAndReview = (workspace: SavedEntityWorkspace) => {
    if (workspace.data) {
      setEntity(workspace.data.entity);
      setLedgers(workspace.data.ledgers || []);
      setHeads(workspace.data.headConfigs || DEFAULT_HEAD_CONFIGS);
      setAdjustments(workspace.data.adjustments || []);
      setDepreciationAssets(workspace.data.depreciationAssets || DEFAULT_DEPRECIATION_ASSETS);
      setNotesToAccounts(workspace.data.notesToAccounts || DEFAULT_STANDARD_NOTES);
      setActiveTab('balance-sheet');
      setToastMessage(`Retrieved "${workspace.entityName}" (FY ${workspace.financialYear}) from Vault for review.`);
      setTimeout(() => setToastMessage(null), 5000);
    }
  };

  const handleLogout = () => {
    authService.logout();
    setCurrentUser(null);
  };

  // ============================================================
  // HANDLERS
  // ============================================================
  const handleUpdateHeads = (newHeads: BalanceSheetHeadConfig[]) => {
    setHeads(newHeads);
    saveCustomHeadsConfig(newHeads);
  };

  const handleSelectSampleEntity = (sampleId: string) => {
    const selected = DEFAULT_ENTITIES.find(e => e.id === sampleId) || DEFAULT_ENTITIES[0];
    setEntity(selected);

    if (sampleId === 'ent-kothari') {
      const classified = classifyLedgersWithRuleEngine(SAMPLE_KOTHARI_TRIAL_BALANCE, heads, getSavedRulesMap());
      setLedgers(classified);
      setAdjustments([
        {
          id: 'adj-kothari-stock',
          type: 'CLOSING_STOCK',
          description: 'Closing Stock as at 31st March 2025',
          debitHead: 'A03',
          creditHead: 'PL_DIRECT_INCOME',
          amount: 680000,
        },
      ]);
    } else {
      const classified = classifyLedgersWithRuleEngine(SAMPLE_APEX_TRIAL_BALANCE, heads, getSavedRulesMap());
      setLedgers(classified);
      setAdjustments([
        {
          id: 'adj-apex-stock',
          type: 'CLOSING_STOCK',
          description: 'Closing Stock as at 31st March 2025',
          debitHead: 'A03',
          creditHead: 'PL_DIRECT_INCOME',
          amount: 425000,
        },
      ]);
    }
  };

  const handleImportNewLedgers = (
    rawLedgers: Omit<LedgerItem, 'targetType' | 'status' | 'confidence'>[],
    detectedEntity?: Partial<EntityDetails>
  ) => {
    // Classify all imported ledgers with the ICAI rule engine, applying saved user rules
    const classified = classifyLedgersWithRuleEngine(rawLedgers, heads, getSavedRulesMap());
    setLedgers(classified);

    // Reset sample adjustments (e.g. Apex Traders ₹4,25,000) so new imported TBs don't inherit phantom stock
    setAdjustments([]);

    // Automatically extract and populate Fixed Assets from the imported Trial Balance into the Depreciation Schedule
    const extractedAssets = extractAssetsFromTrialBalance(classified);
    if (extractedAssets.length > 0) {
      setDepreciationAssets(extractedAssets);
    }

    // If metadata was detected in the file, seamlessly update entity particulars
    if (detectedEntity && (detectedEntity.name || detectedEntity.pan || detectedEntity.gstin || detectedEntity.financialYear || detectedEntity.balanceSheetDate)) {
      setEntity(prev => ({
        ...prev,
        name: detectedEntity.name || prev.name,
        pan: detectedEntity.pan || prev.pan,
        gstin: detectedEntity.gstin || prev.gstin,
        financialYear: detectedEntity.financialYear || prev.financialYear,
        balanceSheetDate: detectedEntity.balanceSheetDate || prev.balanceSheetDate,
        entityType: detectedEntity.entityType || prev.entityType,
        address: detectedEntity.address || prev.address,
      }));
    }

    setActiveTab('classification');
  };

  const handleImportPreviousYearLedgers = (
    rawLedgers: Omit<LedgerItem, 'targetType' | 'status' | 'confidence'>[],
    detectedEntity?: Partial<EntityDetails>
  ) => {
    const { mergedLedgers, stats, extractedPyAssets } = matchAndMergePreviousYearTrialBalance(
      ledgers,
      rawLedgers,
      heads,
      getSavedRulesMap()
    );

    setLedgers(mergedLedgers);

    // If previous year fixed assets were found, sync them with depreciationAssets
    if (extractedPyAssets.length > 0) {
      setDepreciationAssets(prev =>
        prev.map(asset => {
          const match = extractedPyAssets.find(
            pyA => pyA.assetName && normalizeLedgerName(pyA.assetName) === normalizeLedgerName(asset.assetName)
          );
          if (match && match.previousYearClosing !== undefined) {
            return { ...asset, previousYearClosing: match.previousYearClosing };
          }
          return asset;
        })
      );
    }

    // Update entity previousYearDate if detected in the file
    if (detectedEntity?.balanceSheetDate || detectedEntity?.financialYear) {
      setEntity(prev => ({
        ...prev,
        previousYearDate: detectedEntity.balanceSheetDate || detectedEntity.financialYear || prev.previousYearDate,
      }));
    }

    setToastMessage(
      `✓ Previous Year Trial Balance imported: ${stats.matchedCount} ledgers matched with Current Year, ${stats.addedCount} prior-year ledgers added. (Total Dr: ₹${stats.totalPyDebit.toLocaleString('en-IN')}, Total Cr: ₹${stats.totalPyCredit.toLocaleString('en-IN')}${stats.isPyBalanced ? ' - Balanced' : ` - Difference: ₹${stats.pyDifference}`})`
    );
    setTimeout(() => setToastMessage(null), 8000);
  };

  const handleClearPreviousYearLedgers = () => {
    const cleared = clearPreviousYearBalances(ledgers);
    setLedgers(cleared);
    setToastMessage('Previous year trial balance data cleared.');
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleReclassifyAllLedgers = () => {
    const cleaned = ledgers.filter(l => !isNonLedgerText(l.ledgerName));
    const reclassified = classifyLedgersWithRuleEngine(cleaned, heads, getSavedRulesMap());
    setLedgers(reclassified);
  };

  const handlePurgeNonLedgers = () => {
    const cleaned = ledgers.filter(l => !isNonLedgerText(l.ledgerName));
    setLedgers(cleaned);
  };

  const handleUpdateLedger = (updatedLedger: LedgerItem) => {
    setLedgers(prev => prev.map(l => (l.id === updatedLedger.id ? updatedLedger : l)));
  };

  const handleBulkUpdateLedgers = (ledgerIds: string[], updates: Partial<LedgerItem>) => {
    setLedgers(prev =>
      prev.map(l => (ledgerIds.includes(l.id) ? { ...l, ...updates } : l))
    );
  };

  const handleSelectScheduleAndNavigate = (scheduleNo: string | number) => {
    setSelectedScheduleNo(scheduleNo);
    setActiveTab('schedules');
  };

  const handleSyncWithSchedule8 = (assets: DepreciationAssetItem[]) => {
    setDepreciationAssets(assets);
  };

  const handleSyncWithPL = (depreciationAmount: number) => {
    setAdjustments(prev => {
      const existingIdx = prev.findIndex(a => a.description.includes('Depreciation as per Schedule'));
      const newAdj: ManualAdjustment = {
        id: existingIdx >= 0 ? prev[existingIdx].id : `adj-depr-${Date.now()}`,
        date: entity.balanceSheetDate,
        type: 'DEPRECIATION',
        description: `Depreciation as per Depreciation Schedule (${entity.financialYear})`,
        debitHead: 'PL_INDIRECT_EXP',
        creditHead: 'A01',
        amount: depreciationAmount,
      };
      if (existingIdx >= 0) {
        const copy = [...prev];
        copy[existingIdx] = newAdj;
        return copy;
      }
      return [...prev, newAdj];
    });
  };

  // Primary Output: Download Excel Workbook (.xlsx)
  const handleExportExcel = async () => {
    try {
      setIsExportingExcel(true);
      const blob = await generateBalanceSheetExcelWorkbook(
        entity,
        heads,
        ledgers,
        plStatement,
        schedules,
        balanceSheet,
        reconciliation,
        adjustments,
        depreciationAssets,
        notesToAccounts
      );

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const safeName = entity.name.replace(/[^a-zA-Z0-9]/g, '_');
      link.download = `${safeName}_Financial_Statements_ICAI_${entity.financialYear.replace('/', '-')}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Excel Export error:', err);
      alert(`Export to Excel failed: ${err.message}`);
    } finally {
      setIsExportingExcel(false);
    }
  };

  // Secondary Output: Download PDF Report
  const handleExportPDF = () => {
    try {
      generateBalanceSheetPDF(
        entity,
        heads,
        plStatement,
        schedules,
        balanceSheet,
        adjustments,
        reconciliation,
        ledgers
      );
    } catch (err: any) {
      console.error('PDF Export error:', err);
      alert(`Export to PDF failed: ${err.message}`);
    }
  };

  // Presentation Output: Download 6-Slide PPTX Deck
  const handleExportPPT = async () => {
    try {
      await downloadPresentationFile(entity, reconciliation);
    } catch (err: any) {
      console.error('PPT Export error:', err);
      alert(`Export to PPT failed: ${err.message}`);
    }
  };

  // If not logged in, gate access with user ID & password control
  if (!currentUser) {
    return <LoginScreen onLoginSuccess={(user) => setCurrentUser(user)} />;
  }

  return (
    <div className="min-h-screen bg-[#E4E3E0] text-[#141414] font-sans antialiased flex flex-col selection:bg-[#141414] selection:text-white">
      {/* Top Application Bar with User Controls & Vault */}
      <Navbar
        entity={entity}
        reconciliation={reconciliation}
        isExportingExcel={isExportingExcel}
        onOpenEntityModal={() => setIsEntityModalOpen(true)}
        onSelectSampleEntity={handleSelectSampleEntity}
        onOpenAdjustments={() => setIsAdjustmentsModalOpen(true)}
        onOpenAiAssistant={() => setIsAiModalOpen(true)}
        onExportExcel={handleExportExcel}
        onExportPDF={handleExportPDF}
        onExportPPT={handleExportPPT}
        onOpenPptDeck={() => setIsPptModalOpen(true)}
        currentUser={currentUser}
        onOpenUserManagement={() => setIsUserManagementOpen(true)}
        onOpenEntityVault={() => setIsEntityVaultOpen(true)}
        onSaveEntity={handleQuickSaveEntity}
        onLogout={handleLogout}
        pendingUsersCount={pendingUsersCount}
        savedEntitiesCount={savedEntitiesCount}
        isSavingEntity={isSavingEntity}
      />

      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="bg-[#1b2a1e] border-b border-[#4ade80]/40 text-[#4ade80] py-2 px-4 text-xs font-mono flex items-center justify-center gap-2 shadow-inner">
          <CheckCircle2 className="w-4 h-4 text-[#4ade80] shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-4">
        {/* Step-by-Step Accounting Flow Navigation */}
        <WorkflowStepper
          activeTab={activeTab}
          onTabChange={setActiveTab}
          reconciliation={reconciliation}
          schedulesCount={schedules.length}
        />

        {/* Dynamic Sheet / View Rendering */}
        <div className="transition-all duration-150">
          {activeTab === 'control' && (
            <ControlSheetView
              entity={entity}
              heads={heads}
              onUpdateHeads={handleUpdateHeads}
              onOpenEntityModal={() => setIsEntityModalOpen(true)}
              onNavigateToTab={setActiveTab}
              onOpenPptDeck={() => setIsPptModalOpen(true)}
            />
          )}

          {activeTab === 'trial-balance' && (
            <TrialBalanceView
              ledgers={ledgers}
              entity={entity}
              onImportNewLedgers={handleImportNewLedgers}
              onImportPreviousYearLedgers={handleImportPreviousYearLedgers}
              onClearPreviousYearLedgers={handleClearPreviousYearLedgers}
              onReclassifyAll={handleReclassifyAllLedgers}
              onPurgeNonLedgers={handlePurgeNonLedgers}
              onNavigateToClassification={() => setActiveTab('classification')}
            />
          )}

          {activeTab === 'classification' && (
            <ClassificationStudio
              ledgers={ledgers}
              heads={heads}
              onUpdateLedger={handleUpdateLedger}
              onBulkUpdateLedgers={handleBulkUpdateLedgers}
              onReclassifyAll={handleReclassifyAllLedgers}
              onPurgeNonLedgers={handlePurgeNonLedgers}
              onNavigateToTab={setActiveTab}
            />
          )}

          {activeTab === 'depreciation' && (
            <DepreciationScheduleView
              entity={entity}
              depreciationAssets={depreciationAssets}
              ledgers={ledgers}
              onUpdateAssets={setDepreciationAssets}
              onSyncWithSchedule8={handleSyncWithSchedule8}
              onSyncWithPL={handleSyncWithPL}
              onNavigateToTab={setActiveTab}
            />
          )}

          {activeTab === 'profit-and-loss' && (
            <ProfitAndLossView
              entity={entity}
              plStatement={plStatement}
              onOpenAdjustments={() => setIsAdjustmentsModalOpen(true)}
              onNavigateToTab={setActiveTab}
              onExportPDF={handleExportPDF}
            />
          )}

          {activeTab === 'schedules' && (
            <SchedulesView
              entity={entity}
              heads={heads}
              schedules={schedules}
              plStatement={plStatement}
              selectedScheduleNo={selectedScheduleNo}
              onSelectScheduleNo={setSelectedScheduleNo}
              onExportPDF={handleExportPDF}
              onExportExcel={handleExportExcel}
            />
          )}

          {activeTab === 'balance-sheet' && (
            <BalanceSheetView
              entity={entity}
              heads={heads}
              balanceSheet={balanceSheet}
              schedules={schedules}
              onSelectSchedule={handleSelectScheduleAndNavigate}
              onExportExcel={handleExportExcel}
              onExportPDF={handleExportPDF}
              onExportPPT={handleExportPPT}
            />
          )}

          {activeTab === 'notes' && (
            <NotesToAccountsView
              entity={entity}
              notes={notesToAccounts}
              onUpdateNotes={setNotesToAccounts}
              onNavigateToTab={setActiveTab}
            />
          )}

          {activeTab === 'reconciliation' && (
            <ReconciliationView
              entity={entity}
              reconciliation={reconciliation}
              onNavigateToTab={setActiveTab}
              onExportExcel={handleExportExcel}
              onExportPDF={handleExportPDF}
              onExportPPT={handleExportPPT}
            />
          )}
        </div>
      </main>

      {/* Modals & Dialogs */}
      <EntityDetailsModal
        isOpen={isEntityModalOpen}
        entity={entity}
        onClose={() => setIsEntityModalOpen(false)}
        onSave={setEntity}
      />

      <AdjustmentsModal
        isOpen={isAdjustmentsModalOpen}
        adjustments={adjustments}
        onClose={() => setIsAdjustmentsModalOpen(false)}
        onSaveAdjustments={setAdjustments}
      />

      <AiAssistantModal
        isOpen={isAiModalOpen}
        entity={entity}
        ledgers={ledgers}
        plStatement={plStatement}
        reconciliation={reconciliation}
        onClose={() => setIsAiModalOpen(false)}
      />

      <PptDeckModal
        isOpen={isPptModalOpen}
        onClose={() => setIsPptModalOpen(false)}
        entity={entity}
        reconciliation={reconciliation}
        onDownloadPpt={handleExportPPT}
      />

      {/* Admin User Management Modal */}
      {currentUser && (
        <UserManagementModal
          isOpen={isUserManagementOpen}
          onClose={() => {
            setIsUserManagementOpen(false);
            refreshStats();
          }}
          currentUser={currentUser}
        />
      )}

      {/* Entity Audit Vault Modal (Save & Fetch Workspaces) */}
      {currentUser && (
        <EntityVaultModal
          isOpen={isEntityVaultOpen}
          onClose={() => {
            setIsEntityVaultOpen(false);
            refreshStats();
          }}
          currentUser={currentUser}
          currentEntity={entity}
          currentBalanceSheetSummary={balanceSheet}
          onSaveCurrentWorkspace={handleSaveCurrentWorkspace}
          onFetchAndReview={handleFetchAndReview}
          isSavingCurrent={isSavingEntity}
        />
      )}
    </div>
  );
}
