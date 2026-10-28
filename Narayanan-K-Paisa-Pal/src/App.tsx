import React, { useState, useEffect, useMemo } from 'react';
import { AppRow, Kind, UserProfile } from './types';
import {
  loadStoredData,
  saveStoredData,
  clearStoredData,
  generateSampleData,
} from './utils/storage';
import {
  normAll,
  rollForward,
  stateOf,
  todayIST,
  uid,
  reclassifyMisplacedEntries,
} from './utils/calculations';
import { generateWhatsAppDigest } from './utils/exportImport';
import {
  getAttachment,
  saveAttachment,
  deleteAttachment,
  clearAllAttachments,
  AttachmentRecord,
} from './utils/attachmentStorage';
import { hashPin } from './utils/security';
import { generateSalt } from './utils/crypto';
import { Navigation, TabType } from './components/Navigation';
import { OfflineBanner } from './components/OfflineBanner';
import { DashboardView } from './views/DashboardView';
import { DueDatesView } from './views/DueDatesView';
import { InvestmentsView } from './views/InvestmentsView';
import { RecordsView } from './views/RecordsView';
import { UtilitiesView } from './views/UtilitiesView';
import { SettingsView } from './views/SettingsView';
import { ItemModal } from './components/ItemModal';
import { FileUploadModal } from './components/FileUploadModal';
import { WhatsAppModal } from './components/WhatsAppModal';
import { EmergencyKitModal } from './components/EmergencyKitModal';
import { AttachmentViewerModal } from './components/AttachmentViewerModal';
import { PinLockScreen } from './components/PinLockScreen';
import { FDCalculatorModal } from './components/FDCalculatorModal';
import { CashFlowForecastModal } from './components/CashFlowForecastModal';
import { ShareTrialModal } from './components/ShareTrialModal';
import { TrialDocumentsModal } from './components/TrialDocumentsModal';
import { getInitialTrialAppRows, SYNTHETIC_PERSONS } from './data/dummyDocuments';
import { Check, X, Trash2, AlertTriangle } from 'lucide-react';

export default function App() {
  const [rows, setRows] = useState<AppRow[]>([]);
  const [profile, setProfile] = useState<UserProfile>({
    whatsapp: '',
    showUpload: true,
    theme: 'system',
    pinEnabled: false,
    pinHash: '',
  });
  const [currentTab, setCurrentTab] = useState<TabType>('home');
  const [selectedPerson, setSelectedPerson] = useState<string>('');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isUnlocked, setIsUnlocked] = useState<boolean>(false);

  // In-app deletion confirmation state (never blocks or relies on window.confirm in iframes)
  const [deleteConfirmTarget, setDeleteConfirmTarget] = useState<{
    id: string;
    name: string;
    kind: Kind;
  } | null>(null);

  // Modals state
  const [itemModal, setItemModal] = useState<{
    isOpen: boolean;
    kind: Kind;
    initialRow?: AppRow | null;
    presetData?: Record<string, any> | null;
    presetFile?: File | null;
  }>({
    isOpen: false,
    kind: 'due',
    initialRow: null,
    presetData: null,
    presetFile: null,
  });

  const [fileUploadModal, setFileUploadModal] = useState<{
    isOpen: boolean;
    kind: Kind | 'auto';
  }>({
    isOpen: false,
    kind: 'auto',
  });

  const [whatsAppModalOpen, setWhatsAppModalOpen] = useState(false);
  const [emergencyKitOpen, setEmergencyKitOpen] = useState(false);
  const [cashFlowForecastOpen, setCashFlowForecastOpen] = useState(false);
  const [fdCalculatorOpen, setFdCalculatorOpen] = useState(false);
  const [shareTrialOpen, setShareTrialOpen] = useState(false);
  const [trialDocumentsOpen, setTrialDocumentsOpen] = useState(false);
  const [activeAttachment, setActiveAttachment] = useState<{
    attachment: AttachmentRecord | null;
    itemName: string;
  } | null>(null);

  // Initialize from storage on mount
  useEffect(() => {
    const data = loadStoredData();
    let currentRows = data.rows;

    const isFirstTimeSetup = localStorage.getItem('paisa-pal-v10-seeded') === null;

    if (isFirstTimeSetup) {
      currentRows = getInitialTrialAppRows();
      localStorage.setItem('paisa-pal-v10-seeded', 'true');
    }

    // Safely reclassify existing misplaced entries (Utilities, Insurance, Identity)
    const { migratedRows, reclassifiedCount } = reclassifyMisplacedEntries(currentRows);
    if (reclassifiedCount > 0 || isFirstTimeSetup) {
      currentRows = migratedRows;
      saveStoredData(currentRows, data.profile);
    }

    setRows(currentRows);
    setProfile(data.profile);
    if (!data.profile.pinEnabled) {
      setIsUnlocked(true);
    }
  }, []);

  // Sync theme
  useEffect(() => {
    const root = document.documentElement;
    if (profile.theme === 'dark') {
      root.setAttribute('data-theme', 'dark');
    } else if (profile.theme === 'light') {
      root.setAttribute('data-theme', 'light');
    } else {
      root.removeAttribute('data-theme');
    }
  }, [profile.theme]);

  // Toast auto-hide
  const notify = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((prev) => (prev === msg ? null : prev));
    }, 3200);
  };

  // Save changes to storage with explicit status return and error reporting
  const updateRowsAndSave = (nextRows: AppRow[]): boolean => {
    setRows(nextRows);
    const result = saveStoredData(nextRows, profile);
    if (!result.success) {
      notify(result.error || 'Failed to save to local storage: storage quota exceeded');
      return false;
    }
    return true;
  };

  const updateProfileAndSave = (nextProfile: UserProfile): boolean => {
    setProfile(nextProfile);
    const result = saveStoredData(rows, nextProfile);
    if (!result.success) {
      notify(result.error || 'Failed to save settings to local storage');
      return false;
    }
    return true;
  };

  // Actions
  const handleMarkPaid = (id: string) => {
    const today = todayIST();
    const nextRows = rows.map((r) => {
      if (r.id === id) {
        return {
          ...r,
          data: rollForward(r.data, today),
        };
      }
      return r;
    });
    const saved = updateRowsAndSave(nextRows);
    if (saved) {
      notify('Marked paid & rolled forward');
    }
  };

  const handleSaveRow = async (
    kind: Kind,
    data: Record<string, any>,
    id?: string,
    attachmentFile?: File | null,
    deleteAttachmentReq?: boolean
  ) => {
    const targetId = id || uid();

    try {
      if (attachmentFile) {
        await saveAttachment(targetId, attachmentFile);
        data.hasAttachment = true;
      } else if (deleteAttachmentReq) {
        await deleteAttachment(targetId);
        data.hasAttachment = false;
      }
    } catch (e: any) {
      console.error(e);
      notify(e.message || 'Error processing attachment');
    }

    if (id) {
      const nextRows = rows.map((r) => (r.id === id ? { ...r, data } : r));
      const saved = updateRowsAndSave(nextRows);
      if (saved) {
        notify('Entry updated');
      }
    } else {
      const newRow: AppRow = { id: targetId, kind, data };
      const nextRows = [...rows, newRow];
      const saved = updateRowsAndSave(nextRows);
      if (saved) {
        notify('Entry added');
      }
    }
    setItemModal((prev) => ({ ...prev, isOpen: false }));
  };

  const handleDeleteRow = (id: string) => {
    const target = rows.find((r) => r.id === id);
    if (!target) return;
    setDeleteConfirmTarget({
      id,
      name: target.data?.name || target.data?.title || 'this entry',
      kind: target.kind,
    });
  };

  const confirmDeleteAction = async () => {
    if (!deleteConfirmTarget) return;
    const { id, name } = deleteConfirmTarget;
    try {
      await deleteAttachment(id);
    } catch (e) {
      console.error('Error deleting attachment', e);
    }
    const nextRows = rows.filter((r) => r.id !== id);
    const saved = updateRowsAndSave(nextRows);
    if (saved) {
      notify(`✓ "${name}" deleted`);
    }
    setDeleteConfirmTarget(null);
  };

  const handleViewAttachment = async (rowId: string, itemName: string) => {
    // 1. Find the target row from current state
    const targetRow = rows.find((r) => r.id === rowId);
    let fallbackUrl = targetRow?.data?.attachmentUrl;
    let fallbackName = targetRow?.data?.attachmentName;

    // Smart resolution for known FD vouchers if URL is not yet populated
    if (!fallbackUrl) {
      const ref = String(targetRow?.data?.ref || '');
      const inst = String(targetRow?.data?.institution || '').toLowerCase();
      const name = String(targetRow?.data?.name || '').toLowerCase();
      const id = String(rowId).toLowerCase();

      if (
        id.includes('sbi') ||
        ref.includes('43203056352') ||
        inst.includes('state bank') ||
        name.includes('sbi')
      ) {
        fallbackUrl = '/assets/aistudio/Irin_FD_SBI_74546726.pdf';
        fallbackName = 'Irin_FD_SBI_74546726.pdf';
      } else if (
        id.includes('kgb') ||
        ref.includes('40328202400250') ||
        inst.includes('gramin') ||
        name.includes('gramin')
      ) {
        fallbackUrl = '/assets/aistudio/Irin_FD_Gramin_Bank_5d23749c.pdf';
        fallbackName = 'Irin_FD_Gramin_Bank_5d23749c.pdf';
      }
    }

    const att = await getAttachment(rowId, fallbackUrl, fallbackName);
    if (!att) {
      if (targetRow) {
        // Open the item details modal so user can view all fields & attach scan
        setItemModal({
          isOpen: true,
          kind: targetRow.kind,
          initialRow: targetRow,
          presetData: null,
          presetFile: null,
        });
        notify(`Viewing details for "${itemName}". Attach a document photo or PDF anytime.`);
        return;
      }
      notify('No document found for this entry.');
      return;
    }
    setActiveAttachment({
      attachment: att,
      itemName: itemName || targetRow?.data?.name || 'Document',
    });
  };

  const handleBatchSave = async (
    items: { kind: Kind; data: Record<string, any>; file?: File }[]
  ) => {
    const newRows: AppRow[] = [];
    for (const it of items) {
      const id = uid();
      const rowData = { ...it.data };
      if (it.file) {
        try {
          await saveAttachment(id, it.file);
          rowData.hasAttachment = true;
          rowData.attachmentName = it.file.name;
        } catch (e) {
          console.error('Error saving batch attachment', e);
        }
      }
      newRows.push({
        id,
        kind: it.kind,
        data: rowData,
      });
    }
    const nextRows = [...rows, ...newRows];
    const saved = updateRowsAndSave(nextRows);
    if (saved) {
      const counts: Record<string, number> = {};
      items.forEach((it) => {
        counts[it.kind] = (counts[it.kind] || 0) + 1;
      });
      const parts: string[] = [];
      if (counts.rec) parts.push(`${counts.rec} record${counts.rec > 1 ? 's' : ''} saved in Records`);
      if (counts.inv) parts.push(`${counts.inv} investment${counts.inv > 1 ? 's' : ''} saved in Investments`);
      if (counts.due) parts.push(`${counts.due} due date${counts.due > 1 ? 's' : ''} saved in Due Dates`);
      if (counts.util) parts.push(`${counts.util} utility bill${counts.util > 1 ? 's' : ''} saved in Utilities`);
      notify(`✓ ${parts.join(', ') || `Saved ${items.length} new entries`}`);
    }
  };

  const handleLoadSample = () => {
    const sample = generateSampleData();
    const saved = updateRowsAndSave(sample);
    if (saved) {
      notify('Loaded sample data');
    }
  };

  const handleToggleTheme = () => {
    const next =
      profile.theme === 'dark'
        ? 'light'
        : profile.theme === 'light'
        ? 'system'
        : 'dark';
    updateProfileAndSave({ ...profile, theme: next });
    notify(`Theme set to ${next}`);
  };

  // Urgent count for badge in sidebar
  const dueAttentionCount = useMemo(() => {
    return rows
      .filter((r) => r.kind !== 'util')
      .flatMap(normAll)
      .filter((a) => ['overdue', 'today'].includes(stateOf(a))).length;
  }, [rows]);

  const utilityAttentionCount = useMemo(() => {
    return rows
      .filter((r) => r.kind === 'util')
      .flatMap(normAll)
      .filter((a) => ['overdue', 'today'].includes(stateOf(a))).length;
  }, [rows]);

  const whatsAppDigest = useMemo(() => {
    return generateWhatsAppDigest(rows);
  }, [rows]);

  // If PIN lock is enabled and user has not unlocked in current session
  if (profile.pinEnabled && !isUnlocked && profile.pinHash) {
    return (
      <PinLockScreen
        storedPinHash={profile.pinHash}
        pinSalt={profile.pinSalt}
        recoveryKeyHash={profile.recoveryKeyHash}
        recoveryKeySalt={profile.recoveryKeySalt}
        onUnlock={() => setIsUnlocked(true)}
        onResetWithRecoveryKey={async (newPin: string) => {
          const pinSalt = profile.pinSalt || generateSalt(16);
          const { hash } = await hashPin(newPin, pinSalt);
          updateProfileAndSave({
            ...profile,
            pinEnabled: true,
            pinHash: hash,
            pinSalt,
          });
          setIsUnlocked(true);
          notify('PIN reset successfully with Recovery Key');
        }}
        onFactoryWipe={async () => {
          clearStoredData();
          await clearAllAttachments();
          setRows([]);
          setProfile({ whatsapp: '', showUpload: true, theme: 'system' });
          setIsUnlocked(true);
          notify('Vault erased and app reset to initial state');
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[#EEF1F5] dark:bg-[#0B1220] text-[#0F1B2D] dark:text-[#E8EDF5] flex flex-col md:flex-row transition-colors">
      {/* Offline notification banner */}
      <div className="w-full fixed top-0 left-0 right-0 z-50">
        <OfflineBanner />
      </div>

      {/* Navigation (Sidebar on Desktop, Bottom bar on Mobile) */}
      <Navigation
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        dueAttentionCount={dueAttentionCount}
        utilityAttentionCount={utilityAttentionCount}
        theme={profile.theme || 'system'}
        onToggleTheme={handleToggleTheme}
        onOpenShareTrial={() => setShareTrialOpen(true)}
        onOpenTrialDocuments={() => setTrialDocumentsOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-8 py-6 md:py-8 mb-20 md:mb-0">
        {currentTab === 'home' && (
          <DashboardView
            rows={rows}
            profile={profile}
            selectedPerson={selectedPerson}
            onSelectPerson={setSelectedPerson}
            onAdd={(k) =>
              setItemModal({ isOpen: true, kind: k, initialRow: null, presetData: null })
            }
            onUpload={(k) => setFileUploadModal({ isOpen: true, kind: k })}
            onOpenWhatsApp={() => setWhatsAppModalOpen(true)}
            onOpenCashFlow={() => setCashFlowForecastOpen(true)}
            onOpenShareTrial={() => setShareTrialOpen(true)}
            onLoadSample={handleLoadSample}
            onMarkPaid={handleMarkPaid}
            onEdit={(row) =>
              setItemModal({ isOpen: true, kind: row.kind, initialRow: row, presetData: null })
            }
            onDelete={handleDeleteRow}
            onViewAttachment={handleViewAttachment}
            onOpenTrialDocuments={() => setTrialDocumentsOpen(true)}
            onNavigate={(tab) => setCurrentTab(tab)}
          />
        )}

        {currentTab === 'util' && (
          <UtilitiesView
            rows={rows}
            selectedPerson={selectedPerson}
            onSelectPerson={setSelectedPerson}
            onAdd={() =>
              setItemModal({
                isOpen: true,
                kind: 'util',
                initialRow: null,
                presetData: { utilityType: 'electricity', status: 'pending' },
              })
            }
            onEdit={(row) =>
              setItemModal({ isOpen: true, kind: row.kind, initialRow: row, presetData: null })
            }
            onDelete={(id) => handleDeleteRow(id)}
            onUpdateRow={(updatedRow) => {
              const nextRows = rows.map((r) => (r.id === updatedRow.id ? updatedRow : r));
              updateRowsAndSave(nextRows);
            }}
            onViewAttachment={(attName, title) => {
              const targetRow = rows.find(
                (r) => r.data?.attachmentName === attName || r.data?.name === title
              );
              if (targetRow) {
                handleViewAttachment(targetRow.id, title);
              } else {
                notify('Attachment viewer opened');
              }
            }}
          />
        )}

        {currentTab === 'due' && (
          <DueDatesView
            rows={rows}
            profile={profile}
            selectedPerson={selectedPerson}
            onSelectPerson={setSelectedPerson}
            onAdd={(k) =>
              setItemModal({ isOpen: true, kind: k, initialRow: null, presetData: null })
            }
            onUpload={(k) => setFileUploadModal({ isOpen: true, kind: k })}
            onOpenCashFlow={() => setCashFlowForecastOpen(true)}
            onMarkPaid={handleMarkPaid}
            onEdit={(row) =>
              setItemModal({ isOpen: true, kind: row.kind, initialRow: row, presetData: null })
            }
            onDelete={handleDeleteRow}
            onViewAttachment={handleViewAttachment}
          />
        )}

        {currentTab === 'inv' && (
          <InvestmentsView
            rows={rows}
            profile={profile}
            selectedPerson={selectedPerson}
            onSelectPerson={setSelectedPerson}
            onAdd={(k) =>
              setItemModal({ isOpen: true, kind: k, initialRow: null, presetData: null })
            }
            onUpload={(k) => setFileUploadModal({ isOpen: true, kind: k })}
            onOpenCalculator={() => setFdCalculatorOpen(true)}
            onOpenCashFlow={() => setCashFlowForecastOpen(true)}
            onEdit={(row) =>
              setItemModal({ isOpen: true, kind: row.kind, initialRow: row, presetData: null })
            }
            onDelete={handleDeleteRow}
            onViewAttachment={handleViewAttachment}
          />
        )}

        {currentTab === 'rec' && (
          <RecordsView
            rows={rows}
            profile={profile}
            selectedPerson={selectedPerson}
            onSelectPerson={setSelectedPerson}
            onAdd={(k) =>
              setItemModal({ isOpen: true, kind: k, initialRow: null, presetData: null })
            }
            onUpload={(k) => setFileUploadModal({ isOpen: true, kind: k })}
            onEdit={(row) =>
              setItemModal({ isOpen: true, kind: row.kind, initialRow: row, presetData: null })
            }
            onDelete={handleDeleteRow}
            onViewAttachment={handleViewAttachment}
          />
        )}

        {currentTab === 'set' && (
          <SettingsView
            rows={rows}
            profile={profile}
            onUpdateProfile={updateProfileAndSave}
            onRestoreBackup={(restoredRows, restoredProfile) => {
              setRows(restoredRows);
              setProfile(restoredProfile);
              saveStoredData(restoredRows, restoredProfile);
            }}
            onImportCsv={(importedRows) => {
              const combined = [...rows, ...importedRows];
              updateRowsAndSave(combined);
            }}
            onClearAll={async () => {
              try {
                await clearAllAttachments();
              } catch (e) {
                console.error(e);
              }
              setSelectedPerson('');
              updateRowsAndSave([]);
              notify('All entries and documents cleared');
            }}
            onOpenFileUpload={(k) => setFileUploadModal({ isOpen: true, kind: k })}
            onOpenEmergencyKit={() => setEmergencyKitOpen(true)}
            onOpenShareTrial={() => setShareTrialOpen(true)}
            onOpenTrialDocuments={() => setTrialDocumentsOpen(true)}
            onLockNow={() => {
              setIsUnlocked(false);
              notify('App locked');
            }}
            onNotify={notify}
          />
        )}
      </main>

      {/* Item Modal (Add / Edit) with Attachment upload */}
      <ItemModal
        isOpen={itemModal.isOpen}
        kind={itemModal.kind}
        rows={rows}
        initialRow={itemModal.initialRow}
        presetData={itemModal.presetData}
        presetFile={itemModal.presetFile}
        onClose={() => setItemModal((prev) => ({ ...prev, isOpen: false, presetFile: null }))}
        onSave={handleSaveRow}
        onViewAttachment={handleViewAttachment}
      />

      {/* File Upload / OCR Modal */}
      <FileUploadModal
        isOpen={fileUploadModal.isOpen}
        kind={fileUploadModal.kind}
        rows={rows}
        onClose={() => setFileUploadModal((prev) => ({ ...prev, isOpen: false }))}
        onSaveBatch={handleBatchSave}
        onEditSingle={(k, preset, file) => {
          setItemModal({
            isOpen: true,
            kind: k,
            initialRow: null,
            presetData: preset,
            presetFile: file || null,
          });
        }}
        onOpenTrialDocuments={() => setTrialDocumentsOpen(true)}
      />

      {/* WhatsApp Modal */}
      <WhatsAppModal
        isOpen={whatsAppModalOpen}
        whatsappNumber={profile.whatsapp || ''}
        digestText={whatsAppDigest}
        onSaveNumber={(num) => updateProfileAndSave({ ...profile, whatsapp: num })}
        onClose={() => setWhatsAppModalOpen(false)}
      />

      {/* Family Emergency & Nominee Kit Modal */}
      <EmergencyKitModal
        isOpen={emergencyKitOpen}
        rows={rows}
        profile={profile}
        onUpdateProfile={updateProfileAndSave}
        onClose={() => setEmergencyKitOpen(false)}
      />

      {/* Attachment High-Res Viewer Modal */}
      {activeAttachment && (
        <AttachmentViewerModal
          attachment={activeAttachment.attachment}
          itemName={activeAttachment.itemName}
          onClose={() => setActiveAttachment(null)}
        />
      )}

      {/* FD & RD Return Calculator Modal */}
      <FDCalculatorModal
        isOpen={fdCalculatorOpen}
        onClose={() => setFdCalculatorOpen(false)}
        onAddToInvestments={(data) => {
          handleSaveRow('inv', data);
        }}
      />

      {/* Cash Flow & Liquidity Forecast Modal */}
      <CashFlowForecastModal
        isOpen={cashFlowForecastOpen}
        rows={rows}
        onClose={() => setCashFlowForecastOpen(false)}
        onEditItem={(row) =>
          setItemModal({ isOpen: true, kind: row.kind, initialRow: row, presetData: null })
        }
      />

      {/* Send for Trial Modal */}
      <ShareTrialModal
        isOpen={shareTrialOpen}
        onClose={() => setShareTrialOpen(false)}
        onNotify={notify}
      />

      {/* DPDP-Compliant Trial Documents & Excel Hub Modal */}
      <TrialDocumentsModal
        isOpen={trialDocumentsOpen}
        onClose={() => setTrialDocumentsOpen(false)}
        onViewDocument={(att, title) =>
          setActiveAttachment({ attachment: att, itemName: title })
        }
        onAddSingleTrialDoc={(newRow) => {
          const updated = [...rows.filter((r) => r.id !== newRow.id), newRow];
          updateRowsAndSave(updated);
        }}
        onLoadAllTrialData={(trialRows) => {
          updateRowsAndSave(trialRows);
        }}
        onTestScanDoc={(file, kind) => {
          setItemModal({
            isOpen: true,
            kind: kind,
            initialRow: null,
            presetData: null,
            presetFile: file,
          });
        }}
        onNotify={notify}
      />

      {/* In-App Delete Confirmation Modal (sandboxed safe, no window.confirm) */}
      {deleteConfirmTarget && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-fadeIn"
        >
          <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-md w-full p-5 sm:p-6 shadow-2xl text-[#0F1B2D] dark:text-[#E8EDF5]">
            <div className="flex items-start gap-3.5">
              <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex-shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-bold text-[#0F1B2D] dark:text-[#E8EDF5] truncate">
                  Delete {deleteConfirmTarget.name}?
                </h3>
                <p className="text-xs sm:text-sm text-[#6F7E92] dark:text-[#8594AA] mt-1.5 leading-relaxed">
                  Are you sure you want to delete this {deleteConfirmTarget.kind === 'inv' ? 'investment' : deleteConfirmTarget.kind === 'rec' ? 'official record' : 'due date'}? Any attached scans or receipts will also be permanently deleted.
                </p>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setDeleteConfirmTarget(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:bg-slate-50 dark:hover:bg-slate-800 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDeleteAction}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition shadow-sm cursor-pointer"
              >
                Delete Entry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          className="fixed bottom-16 md:bottom-6 right-1/2 translate-x-1/2 md:translate-x-0 md:right-6 z-50 flex items-center gap-2 bg-[#0F1B2D] dark:bg-[#E8EDF5] text-white dark:text-[#08121F] px-4 py-2.5 rounded-full text-xs sm:text-sm font-medium shadow-2xl animate-bounce-subtle"
        >
          <Check className="w-4 h-4 text-emerald-400 dark:text-emerald-600 flex-shrink-0" />
          <span>{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-1 opacity-70 hover:opacity-100"
            aria-label="Dismiss message"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
