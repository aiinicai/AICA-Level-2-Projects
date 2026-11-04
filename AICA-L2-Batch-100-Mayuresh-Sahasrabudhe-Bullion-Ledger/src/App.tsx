import React, { useState, useEffect, useMemo } from 'react';
import {
  Purchase,
  RateRecord,
  AppSettings,
  RateCorrection,
} from './types';
import {
  purchaseRepo,
  rateRepo,
  settingsRepo,
  correctionRepo,
  DEFAULT_SETTINGS,
  createFullBackup,
  restoreFromBackup,
} from './db/repository';
import { DEMO_PURCHASES } from './data/demoPurchases';
import defaultRatesJson from './data/defaultRates.json';
import { buildRateIndex, valuePortfolio, generateChartSeries } from './utils/valuationEngine';
import { Header } from './components/common/Header';
import { Navigation, NavTab } from './components/common/Navigation';
import { DashboardScreen } from './components/dashboard/DashboardScreen';
import { PurchasesScreen } from './components/purchases/PurchasesScreen';
import { HoldingDetailsScreen } from './components/holdings/HoldingDetailsScreen';
import { PriceHistoryScreen } from './components/prices/PriceHistoryScreen';
import { SettingsScreen } from './components/settings/SettingsScreen';
import { VerificationView } from './components/diagnostics/VerificationView';
import { AddEditPurchaseModal } from './components/purchases/AddEditPurchaseModal';
import { AuthModal } from './components/auth/AuthModal';
import { getCurrentUser, onAuthStateChange, signOut, isUserSuperUser, SUPERUSER_EMAIL } from './services/supabaseClient';
import { User } from '@supabase/supabase-js';
import { getTodayKolkata } from './utils/formatters';
import { X } from 'lucide-react';

export const App: React.FC = () => {
  const getInitialTab = (): NavTab => {
    if (typeof window !== 'undefined' && window.location.hash) {
      const h = window.location.hash.replace('#', '') as NavTab;
      if (['dashboard', 'purchases', 'holdings', 'prices', 'settings', 'diagnostics'].includes(h)) {
        return h;
      }
    }
    return 'dashboard';
  };

  const [activeTab, setActiveTab] = useState<NavTab>(getInitialTab);

  const handleTabChange = (tab: NavTab) => {
    setActiveTab(tab);
    if (typeof window !== 'undefined') {
      window.location.hash = tab;
    }
  };

  useEffect(() => {
    const handleHash = () => {
      const h = window.location.hash.replace('#', '') as NavTab;
      if (['dashboard', 'purchases', 'holdings', 'prices', 'settings', 'diagnostics'].includes(h)) {
        setActiveTab(h);
      }
    };
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);
  const [valuationDate, setValuationDate] = useState<string>(() => getTodayKolkata());
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [rates, setRates] = useState<RateRecord[]>([]);
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [corrections, setCorrections] = useState<RateCorrection[]>([]);
  const [lastBatchId, setLastBatchId] = useState<string | null>(null);

  // Authentication State
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Global modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isDiagnosticsModalOpen, setIsDiagnosticsModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Supabase Auth listener
  useEffect(() => {
    getCurrentUser().then(setCurrentUser).catch(console.warn);
    const unsubscribe = onAuthStateChange((user) => {
      setCurrentUser(user);
      if (user && typeof window !== 'undefined') {
        // Clean up hash if it contained access_token or refresh_token from OAuth
        if (window.location.hash && (window.location.hash.includes('access_token') || window.location.hash.includes('refresh_token'))) {
          window.history.replaceState({}, document.title, window.location.pathname + '#dashboard');
          setActiveTab('dashboard');
        }
        // Clean up search query if it contained ?code= from PKCE flow
        if (window.location.search && window.location.search.includes('code=')) {
          window.history.replaceState({}, document.title, window.location.pathname + '#dashboard');
          setActiveTab('dashboard');
        }
      }
    });
    return () => {
      unsubscribe();
    };
  }, []);

  const handleSignOut = async () => {
    await signOut();
    setCurrentUser(null);
  };

  const isSuperUser = isUserSuperUser(currentUser);

  // Initialize data on mount
  useEffect(() => {
    let isMounted = true;

    async function initData() {
      try {
        // Seed default 5,666 historical rates if not in IndexedDB
        await rateRepo.seedDefaultsIfEmpty();

        const [loadedPurchases, loadedRates, loadedSettings, loadedCorrections] = await Promise.all([
          purchaseRepo.getAll(),
          rateRepo.getAll(),
          settingsRepo.get(),
          correctionRepo.getAll(),
        ]);

        if (isMounted) {
          setPurchases(loadedPurchases);
          // If indexeddb rates were somehow empty, fallback directly to defaultRatesJson
          setRates(loadedRates.length > 0 ? loadedRates : (defaultRatesJson as RateRecord[]));
          setSettings(loadedSettings);
          setCorrections(loadedCorrections);
          setIsLoading(false);
        }
      } catch (err) {
        console.error('Failed to initialize local IndexedDB database:', err);
        // Fallback to static archive for instant usability
        if (isMounted) {
          setRates(defaultRatesJson as RateRecord[]);
          setIsLoading(false);
        }
      }
    }

    initData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fast rate indexing memoized on rates dataset change
  const rateIndex = useMemo(() => {
    return buildRateIndex(rates);
  }, [rates]);

  // Full portfolio valuation evaluated dynamically for valuationDate
  const { summary, lotValuations } = useMemo(() => {
    return valuePortfolio(purchases, valuationDate, rateIndex, settings);
  }, [purchases, valuationDate, rateIndex, settings]);

  // Growth chart historical series
  const chartData = useMemo(() => {
    return generateChartSeries(purchases, valuationDate, rateIndex, settings);
  }, [purchases, valuationDate, rateIndex, settings]);

  // Check if any lot valuation relies on a carried forward rate
  const hasGapOrCarriedWarning = useMemo(() => {
    return lotValuations.some((l) => l.hasRate && l.isCarriedForward);
  }, [lotValuations]);

  // Purchases Handlers
  const handleSavePurchase = async (purchase: Purchase) => {
    // 1. Optimistically update React state immediately
    setPurchases((prev) => {
      const idx = prev.findIndex((p) => p.id === purchase.id);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = purchase;
        return updated;
      }
      return [purchase, ...prev];
    });

    // 2. Automatically advance valuationDate if purchase is newer than current valuation date
    if (purchase.purchaseDate > valuationDate) {
      setValuationDate(purchase.purchaseDate);
    }

    // 3. Persist to storage (LocalStorage + IndexedDB)
    try {
      await purchaseRepo.save(purchase);
    } catch (err) {
      console.warn('Purchase save warning:', err);
    }
  };

  const handleSoftDeletePurchase = async (id: string) => {
    setPurchases((prev) =>
      prev.map((p) => (p.id === id ? { ...p, deleted: true, deletedAt: new Date().toISOString() } : p))
    );
    try {
      await purchaseRepo.softDelete(id);
    } catch (err) {
      console.warn('Soft delete warning:', err);
    }
  };

  const handleRestorePurchase = async (id: string) => {
    setPurchases((prev) =>
      prev.map((p) => (p.id === id ? { ...p, deleted: false, deletedAt: undefined } : p))
    );
    try {
      await purchaseRepo.restore(id);
    } catch (err) {
      console.warn('Restore warning:', err);
    }
  };

  const handlePermanentDeletePurchase = async (id: string) => {
    setPurchases((prev) => prev.filter((p) => p.id !== id));
    try {
      await purchaseRepo.permanentDelete(id);
    } catch (err) {
      console.warn('Permanent delete warning:', err);
    }
  };

  const handleImportPurchases = async (newPurchases: Purchase[], batchId: string) => {
    if (newPurchases.length === 0) return;

    // 1. Optimistically update React state immediately
    setPurchases((prev) => [...newPurchases, ...prev]);
    setLastBatchId(batchId);

    // 2. Automatically advance valuationDate if imported purchases are newer than valuationDate
    const maxImportDate = newPurchases.reduce(
      (max, p) => (p.purchaseDate > max ? p.purchaseDate : max),
      valuationDate
    );
    if (maxImportDate > valuationDate) {
      setValuationDate(maxImportDate);
    }

    // 3. Persist to storage
    try {
      await purchaseRepo.saveBatch(newPurchases);
    } catch (err) {
      console.warn('Import batch save warning:', err);
    }
  };

  const handleUndoLastBatch = async () => {
    if (!lastBatchId) return;
    if (confirm('Undo the last imported batch and remove all its purchases?')) {
      setPurchases((prev) => prev.filter((p) => p.batchId !== lastBatchId));
      const batchIdToUndo = lastBatchId;
      setLastBatchId(null);
      try {
        await purchaseRepo.undoBatch(batchIdToUndo);
      } catch (err) {
        console.warn('Undo batch warning:', err);
      }
    }
  };

  const handleLoadDemoData = async () => {
    setPurchases((prev) => [...DEMO_PURCHASES, ...prev]);
    try {
      await purchaseRepo.saveBatch(DEMO_PURCHASES);
    } catch (err) {
      console.warn('Demo data save warning:', err);
    }
  };

  const handleClearAllPurchases = async () => {
    if (confirm('Are you sure you want to delete all purchases from the ledger? This action cannot be undone.')) {
      setPurchases([]);
      try {
        await purchaseRepo.clearAll();
      } catch (err) {
        console.warn('Clear purchases warning:', err);
      }
    }
  };

  // Settings Handlers
  const handleUpdateSettings = async (newSettings: AppSettings) => {
    await settingsRepo.save(newSettings);
    setSettings(newSettings);
  };

  const handleExportBackup = async () => {
    const backup = await createFullBackup(false);
    const blob = new Blob([JSON.stringify(backup, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Bullion_Ledger_Backup_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleRestoreBackup = async (file: File) => {
    try {
      const text = await file.text();
      const backupData = JSON.parse(text);
      const res = await restoreFromBackup(backupData);
      const [updatedPurchases, updatedSettings] = await Promise.all([
        purchaseRepo.getAll(),
        settingsRepo.get(),
      ]);
      setPurchases(updatedPurchases);
      setSettings(updatedSettings);
      alert(
        `Successfully restored backup! Restored ${res.purchasesRestored} purchases and configuration settings.`
      );
    } catch (err: any) {
      alert(`Failed to restore backup: ${err.message}`);
    }
  };

  // Supplemental Rates & Corrections Handlers
  const handleImportSupplementalRates = async (newRates: RateRecord[]) => {
    await rateRepo.saveBatch(newRates);
    const updated = await rateRepo.getAll();
    setRates(updated);
  };

  const handleSaveCorrection = async (correction: RateCorrection) => {
    await correctionRepo.save(correction);
    // Update matching rate in rates store
    const targetRate = rates.find((r) => r.id === correction.rateId);
    if (targetRate) {
      const updatedRate: RateRecord = {
        ...targetRate,
        pricePerGram: correction.correctedPricePerGram,
        notes: `Audited correction: ${correction.reason}`,
      };
      await rateRepo.save(updatedRate);
      const allRates = await rateRepo.getAll();
      setRates(allRates);
    }
    const allCorrections = await correctionRepo.getAll();
    setCorrections(allCorrections);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#FAF7F2] flex items-center justify-center p-4">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-3 border-[#B88B2A] border-t-transparent rounded-full animate-spin mx-auto" />
          <h2 className="text-sm font-bold text-stone-900">Loading Bullion Ledger...</h2>
          <p className="text-xs text-stone-500">
            Initializing local IndexedDB and 5,666 historical rate observations
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF7F2] text-[#1C1A18] flex flex-col font-sans pb-16 md:pb-0">
      {/* Top Header */}
      <Header
        valuationDate={valuationDate}
        onValuationDateChange={setValuationDate}
        onOpenAddModal={() => {
          if (!isSuperUser) {
            setIsAuthModalOpen(true);
          } else {
            setIsAddModalOpen(true);
          }
        }}
        onOpenDiagnostics={() => setIsDiagnosticsModalOpen(true)}
        onOpenIbjaFetch={() => setActiveTab('prices')}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
        onSignOut={handleSignOut}
        currentUser={currentUser}
        isSuperUser={isSuperUser}
        hasGapWarning={hasGapOrCarriedWarning}
      />

      {/* Main Container */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        {/* Navigation (Sidebar on Desktop, Bottom nav on Mobile) */}
        <Navigation
          activeTab={activeTab}
          onTabChange={handleTabChange}
          purchasesCount={purchases.filter((p) => !p.deleted).length}
          ratesCount={rates.length}
        />

        {/* Screen Content */}
        <main className="flex-1 p-3.5 sm:p-6 lg:p-8 max-w-full overflow-x-hidden">
          {activeTab === 'dashboard' && (
            <DashboardScreen
              summary={summary}
              lotValuations={lotValuations}
              allPurchases={purchases}
              chartData={chartData}
              selectedDate={valuationDate}
              onSelectDate={setValuationDate}
              onOpenAddModal={() => {
                if (!isSuperUser) {
                  setIsAuthModalOpen(true);
                } else {
                  setIsAddModalOpen(true);
                }
              }}
              onLoadDemoData={handleLoadDemoData}
            />
          )}

          {activeTab === 'purchases' && (
            <PurchasesScreen
              purchases={purchases}
              onSavePurchase={handleSavePurchase}
              onSoftDeletePurchase={handleSoftDeletePurchase}
              onRestorePurchase={handleRestorePurchase}
              onPermanentDeletePurchase={handlePermanentDeletePurchase}
              onImportPurchases={handleImportPurchases}
              onUndoLastBatch={handleUndoLastBatch}
              lastBatchId={lastBatchId}
              onLoadDemoData={handleLoadDemoData}
              isSuperUser={isSuperUser}
              onRequireAuth={() => setIsAuthModalOpen(true)}
            />
          )}

          {activeTab === 'holdings' && (
            <HoldingDetailsScreen
              lotValuations={lotValuations}
              selectedDate={valuationDate}
            />
          )}

          {activeTab === 'prices' && (
            <PriceHistoryScreen
              rates={rates}
              corrections={corrections}
              onImportSupplementalRates={handleImportSupplementalRates}
              onSaveCorrection={handleSaveCorrection}
              isSuperUser={isSuperUser}
              onRequireAuth={() => setIsAuthModalOpen(true)}
              onRatesUpdated={(newRates, marketDate) => {
                if (marketDate > valuationDate) {
                  setValuationDate(marketDate);
                }
                const updatedSettings = { ...settings, lastSuccessfulUpdate: new Date().toISOString() };
                setSettings(updatedSettings);
                settingsRepo.save(updatedSettings).catch(console.warn);
              }}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsScreen
              settings={settings}
              onUpdateSettings={handleUpdateSettings}
              onExportBackup={handleExportBackup}
              onRestoreBackup={handleRestoreBackup}
              onLoadDemoData={handleLoadDemoData}
              onClearAllPurchases={handleClearAllPurchases}
              purchasesCount={purchases.filter((p) => !p.deleted).length}
              ratesCount={rates.length}
              currentUser={currentUser}
              onOpenAuthModal={() => setIsAuthModalOpen(true)}
              onSignOut={handleSignOut}
            />
          )}

          {activeTab === 'diagnostics' && (
            <VerificationView rates={rates} settings={settings} />
          )}
        </main>
      </div>

      {/* Super User Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={() => setIsAuthModalOpen(false)}
      />

      {/* Global Add Purchase Modal */}
      <AddEditPurchaseModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSave={handleSavePurchase}
        existingPurchases={purchases}
        editingPurchase={null}
      />

      {/* Diagnostics Modal if triggered from Header button */}
      {isDiagnosticsModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-2xs flex items-center justify-center p-3 sm:p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full border border-stone-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between px-5 py-3 border-b border-stone-200 bg-[#FAF7F2] shrink-0">
              <span className="text-sm font-bold text-stone-900">
                System Diagnostics & Technical Verification
              </span>
              <button
                type="button"
                onClick={() => setIsDiagnosticsModalOpen(false)}
                className="text-stone-400 hover:text-stone-700 p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-5 overflow-y-auto">
              <VerificationView
                rates={rates}
                settings={settings}
                onClose={() => setIsDiagnosticsModalOpen(false)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default App;
