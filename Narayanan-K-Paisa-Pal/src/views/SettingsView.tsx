import React, { useState, useRef } from 'react';
import {
  Smartphone,
  Laptop,
  Download,
  Upload,
  FileSpreadsheet,
  Printer,
  Trash2,
  Check,
  ShieldCheck,
  Info,
  ChevronDown,
  ChevronUp,
  Share2,
  Lock,
  Unlock,
  KeyRound,
  ShieldAlert,
  CalendarPlus,
  FolderArchive,
  Copy,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  FileText,
  Sparkles,
} from 'lucide-react';
import { AppRow, Kind, UserProfile } from '../types';
import {
  exportBackupJson,
  exportCsvData,
  importCsvData,
  parseAndRestoreBackup,
  triggerPrint,
  exportStandaloneHtml,
} from '../utils/exportImport';
import { hashPin } from '../utils/security';
import {
  generateEmergencyRecoveryKey,
  hashRecoveryKey,
  generateSalt,
} from '../utils/crypto';
import { generateAllIcs } from '../utils/calendarExport';
import { normAll, reclassifyMisplacedEntries } from '../utils/calculations';
import {
  downloadAllTrialAssetsZip,
  downloadMasterTrialXlsx,
} from '../data/dummyDocuments';

interface Props {
  rows: AppRow[];
  profile: UserProfile;
  onUpdateProfile: (profile: UserProfile) => void;
  onRestoreBackup: (rows: AppRow[], profile: UserProfile) => void;
  onImportCsv: (importedRows: AppRow[]) => void;
  onClearAll: () => void;
  onOpenFileUpload: (kind: Kind) => void;
  onOpenEmergencyKit: () => void;
  onOpenShareTrial?: () => void;
  onOpenTrialDocuments?: () => void;
  onLockNow: () => void;
  onNotify: (msg: string) => void;
}

export const SettingsView: React.FC<Props> = ({
  rows,
  profile,
  onUpdateProfile,
  onRestoreBackup,
  onImportCsv,
  onClearAll,
  onOpenFileUpload,
  onOpenEmergencyKit,
  onOpenShareTrial,
  onOpenTrialDocuments,
  onLockNow,
  onNotify,
}) => {
  const [waNum, setWaNum] = useState(profile.whatsapp || '');
  const [showUploadButtons, setShowUploadButtons] = useState(profile.showUpload !== false);
  const [showSyncInfo, setShowSyncInfo] = useState(false);
  const [showInstallGuide, setShowInstallGuide] = useState(false);

  // PIN & Vault Setup State
  const [newPin, setNewPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [showPinSetup, setShowPinSetup] = useState(false);
  const [pinError, setPinError] = useState('');
  const [generatedRecoveryKey, setGeneratedRecoveryKey] = useState<string | null>(null);
  const [hasCopiedRecovery, setHasCopiedRecovery] = useState(false);
  const [showRecoveryViewModal, setShowRecoveryViewModal] = useState(false);
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);

  const handleSaveWa = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = waNum.replace(/\D/g, '');
    if (clean && (clean.length < 10 || clean.length > 15)) {
      onNotify('Phone number looks invalid: include your country code (e.g. 919876543210).');
      return;
    }
    onUpdateProfile({ ...profile, whatsapp: clean });
    onNotify('WhatsApp number saved');
  };

  const handleToggleUpload = (checked: boolean) => {
    setShowUploadButtons(checked);
    onUpdateProfile({ ...profile, showUpload: checked });
    onNotify(checked ? 'Upload buttons enabled' : 'Upload buttons hidden');
  };

  const handleStartPinSetup = () => {
    setPinError('');
    setNewPin('');
    setConfirmPin('');
    // Generate an emergency recovery key upfront so the user can store it
    const recKey = generateEmergencyRecoveryKey();
    setGeneratedRecoveryKey(recKey);
    setHasCopiedRecovery(false);
    setShowPinSetup(true);
  };

  const handleSetPin = async (e: React.FormEvent) => {
    e.preventDefault();
    setPinError('');
    if (!/^\d{4}$/.test(newPin)) {
      setPinError('PIN must be exactly 4 digits');
      return;
    }
    if (newPin !== confirmPin) {
      setPinError('PINs do not match. Re-enter carefully.');
      return;
    }

    const pinSalt = profile.pinSalt || generateSalt(16);
    const { hash } = await hashPin(newPin, pinSalt);

    let recKeyHash = profile.recoveryKeyHash;
    let recKeySalt = profile.recoveryKeySalt;

    if (generatedRecoveryKey) {
      recKeySalt = generateSalt(16);
      recKeyHash = await hashRecoveryKey(generatedRecoveryKey, recKeySalt);
    }

    onUpdateProfile({
      ...profile,
      pinEnabled: true,
      pinHash: hash,
      pinSalt,
      recoveryKeyHash: recKeyHash,
      recoveryKeySalt: recKeySalt,
      vaultEncrypted: true,
    });

    setNewPin('');
    setConfirmPin('');
    setShowPinSetup(false);
    onNotify('4-Digit Security PIN and Emergency Key activated.');
  };

  const handleDisablePin = () => {
    if (
      window.confirm(
        'Disable 4-digit PIN lock? Your records will no longer require a PIN to open.'
      )
    ) {
      onUpdateProfile({
        ...profile,
        pinEnabled: false,
        pinHash: undefined,
        pinSalt: undefined,
      });
      onNotify('PIN lock removed');
    }
  };

  const handleCopyRecoveryKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setHasCopiedRecovery(true);
    onNotify('Recovery key copied to clipboard.');
    setTimeout(() => setHasCopiedRecovery(false), 2500);
  };

  const handleGenerateNewRecoveryKey = async () => {
    const newKey = generateEmergencyRecoveryKey();
    const salt = generateSalt(16);
    const hash = await hashRecoveryKey(newKey, salt);
    onUpdateProfile({
      ...profile,
      recoveryKeyHash: hash,
      recoveryKeySalt: salt,
    });
    setGeneratedRecoveryKey(newKey);
    setShowRecoveryViewModal(true);
    onNotify('New Emergency Recovery Key generated.');
  };

  const handleExportAllCalendar = () => {
    const alerts = rows.flatMap(normAll).filter((a) => !a.paid);
    if (!alerts.length) {
      onNotify('No upcoming dues or maturities to export.');
      return;
    }
    const icsContent = generateAllIcs(alerts);
    const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `paisa-pal-all-reminders-${new Date().toISOString().slice(0, 10)}.ics`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    onNotify(`Exported ${alerts.length} calendar events to .ics`);
  };

  const handleExportBackup = async () => {
    try {
      const { attachmentCount } = await exportBackupJson(rows, profile);
      const updatedProfile = { ...profile, lastBackupAt: new Date().toISOString() };
      onUpdateProfile(updatedProfile);
      onNotify(
        `Backup downloaded (${rows.length} entries, ${attachmentCount} document attachments).`
      );
    } catch (err: any) {
      onNotify('Error creating backup: ' + (err.message || 'Unknown error'));
    }
  };

  const handleRestoreFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const text = String(evt.target?.result);
        const { rows: restoredRows, profile: restoredProfile, attachmentCount } =
          await parseAndRestoreBackup(text);

        if (!Array.isArray(restoredRows)) {
          throw new Error('Not a valid Paisa Pal backup');
        }

        if (
          window.confirm(
            `Restore backup with ${restoredRows.length} entries and ${attachmentCount} document attachments? This will update your local records.`
          )
        ) {
          onRestoreBackup(restoredRows, restoredProfile);
          onNotify(
            `Successfully restored ${restoredRows.length} entries and ${attachmentCount} attachments.`
          );
        }
      } catch (err: any) {
        onNotify('Could not read backup file: ' + (err.message || 'Invalid format'));
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleImportCsvFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const text = String(evt.target?.result);
        const { imported, count } = importCsvData(text);
        if (count === 0) {
          onNotify('No valid entries found in CSV.');
          return;
        }
        onImportCsv(imported);
        onNotify(`Successfully imported ${count} entries.`);
      } catch (err: any) {
        onNotify(err.message || 'Error importing CSV.');
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleClear = () => {
    setShowDeleteAllModal(true);
  };

  const confirmDeleteAll = () => {
    onClearAll();
    setShowDeleteAllModal(false);
  };

  return (
    <div className="space-y-6 max-w-4xl pb-16">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-[#0F1B2D] dark:text-[#E8EDF5]">
          Settings & Security
        </h1>
        <p className="text-xs sm:text-sm text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
          App lock PIN, emergency recovery key, family emergency kit, and offline backups
        </p>
      </div>

      {/* 4-Digit Security PIN & Vault Lock */}
      <section className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#0B3B66]/10 text-[#0B3B66] dark:bg-[#5B9BE0]/15 dark:text-[#5B9BE0] flex items-center justify-center flex-shrink-0">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
                  4-Digit Security PIN Lock
                </h2>
                {profile.pinEnabled && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30">
                    Active
                  </span>
                )}
              </div>
              <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
                {profile.pinEnabled
                  ? 'PIN lock is active. App requires your 4-digit PIN to open and protects your bank details.'
                  : 'Protect your bank details, passport numbers, and investments with a security PIN.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {profile.pinEnabled ? (
              <>
                <button
                  onClick={onLockNow}
                  className="min-h-[44px] px-3.5 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-white transition flex items-center gap-1.5"
                >
                  <Lock className="w-3.5 h-3.5" />
                  <span>Lock Now</span>
                </button>
                <button
                  onClick={handleDisablePin}
                  className="min-h-[44px] px-3.5 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  Remove PIN
                </button>
              </>
            ) : (
              <button
                onClick={handleStartPinSetup}
                className="min-h-[44px] px-4 py-2 rounded-xl text-xs font-semibold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm"
              >
                Set 4-Digit PIN
              </button>
            )}
          </div>
        </div>

        {/* PIN Setup Form with Emergency Recovery Key */}
        {showPinSetup && !profile.pinEnabled && (
          <form onSubmit={handleSetPin} className="mt-4 pt-4 border-t border-[#DCE2EA] dark:border-[#25324A] max-w-md space-y-4">
            <div className="bg-slate-50 dark:bg-slate-900/70 border border-[#DCE2EA] dark:border-[#25324A] p-3.5 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                <KeyRound className="w-4 h-4 text-[#0E7C86]" />
                <span>Emergency Recovery Key</span>
              </div>
              <p className="text-[11px] text-[#6F7E92] dark:text-[#8594AA] leading-relaxed">
                If you ever forget your PIN, this 16-character recovery key is the <strong>only way</strong> to regain access without wiping your data. Save or copy it now:
              </p>
              <div className="flex items-center gap-2 bg-white dark:bg-[#0B1220] border border-slate-300 dark:border-slate-700 px-3 py-2 rounded-lg font-mono text-xs font-bold tracking-widest text-[#0E7C86]">
                <span className="flex-1 select-all">{generatedRecoveryKey}</span>
                <button
                  type="button"
                  onClick={() => generatedRecoveryKey && handleCopyRecoveryKey(generatedRecoveryKey)}
                  className="p-1 hover:text-[#0B3B66] dark:hover:text-[#5B9BE0] transition"
                  title="Copy recovery key"
                >
                  {hasCopiedRecovery ? (
                    <Check className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="text-xs text-[#46566C] dark:text-[#A9B6C9]">
              Choose a 4-digit PIN for quick day-to-day unlock:
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-[#6F7E92] dark:text-[#8594AA] mb-1">
                  Enter 4-digit PIN:
                </label>
                <input
                  type="password"
                  inputMode="numeric"
                  maxLength={4}
                  required
                  value={newPin}
                  onChange={(e) => setNewPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  placeholder="••••"
                  className="w-full text-center tracking-widest text-lg font-bold bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl py-2 focus:outline-2 focus:outline-[#0E7C86]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-[#6F7E92] dark:text-[#8594AA] mb-1">
                  Confirm PIN:
                </label>
                <input
                  type="password"
                  inputMode="numeric"
                  maxLength={4}
                  required
                  value={confirmPin}
                  onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  placeholder="••••"
                  className="w-full text-center tracking-widest text-lg font-bold bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl py-2 focus:outline-2 focus:outline-[#0E7C86]"
                />
              </div>
            </div>

            {pinError && (
              <div className="text-xs text-rose-600 dark:text-rose-400 font-medium flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{pinError}</span>
              </div>
            )}

            <div className="flex items-center gap-2 pt-1">
              <button
                type="submit"
                className="min-h-[44px] px-5 py-2 rounded-xl text-xs font-semibold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm"
              >
                Activate Security PIN & Vault
              </button>
              <button
                type="button"
                onClick={() => setShowPinSetup(false)}
                className="min-h-[44px] px-4 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>

      {/* Emergency Recovery Key Management */}
      {profile.pinEnabled && (
        <section className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center flex-shrink-0">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
                Emergency Recovery Key
              </h2>
              <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
                {profile.recoveryKeyHash
                  ? 'Configured. Used to securely reset your PIN if forgotten.'
                  : 'Generate a 16-character safety key to recover your vault.'}
              </p>
            </div>
          </div>

          <button
            onClick={handleGenerateNewRecoveryKey}
            className="min-h-[44px] flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold border border-[#DCE2EA] dark:border-[#25324A] hover:border-purple-500 dark:hover:border-purple-400 bg-slate-50 dark:bg-slate-800 transition whitespace-nowrap"
          >
            <KeyRound className="w-4 h-4 text-purple-600 dark:text-purple-400" />
            <span>Generate New Recovery Key</span>
          </button>
        </section>
      )}

      {/* Family Emergency & Nominee Kit */}
      <section className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center flex-shrink-0">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
              Family Financial Emergency Kit
            </h2>
            <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
              Generates a 1-page printable dossier of all bank FDs, policies, documents, nominees and emergency contacts for your home safe.
            </p>
          </div>
        </div>

        <button
          onClick={onOpenEmergencyKit}
          className="min-h-[44px] flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-semibold bg-[#0B3B66] dark:bg-[#5B9BE0] text-white dark:text-[#08121F] hover:brightness-110 transition shadow-sm whitespace-nowrap"
        >
          <Printer className="w-4 h-4" />
          <span>Open Emergency Dossier</span>
        </button>
      </section>

      {/* WhatsApp Alerts Configuration */}
      <section className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
        <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-2">
          <Share2 className="w-4 h-4 text-emerald-600" />
          <span>WhatsApp Alerts Number</span>
        </h2>
        <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-1 mb-3">
          Used by the "Send alerts on WhatsApp" button on the dashboard to compose high-priority digests.
        </p>

        <form onSubmit={handleSaveWa} className="flex flex-col sm:flex-row gap-2.5 max-w-md">
          <input
            type="tel"
            value={waNum}
            onChange={(e) => setWaNum(e.target.value)}
            placeholder="e.g. 919876543210 (country code + number)"
            className="flex-1 bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
          />
          <button
            type="submit"
            className="min-h-[44px] px-5 py-2 rounded-xl text-xs font-semibold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm"
          >
            Save number
          </button>
        </form>
      </section>

      {/* Calendar Export (.ics) */}
      <section className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center flex-shrink-0">
            <CalendarPlus className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
              Phone Calendar Reminders (.ics)
            </h2>
            <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
              Export all upcoming payment dues and maturities directly to your iPhone or Android calendar so your calendar alerts you before due dates.
            </p>
          </div>
        </div>

        <button
          onClick={handleExportAllCalendar}
          className="min-h-[44px] flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50 dark:bg-slate-800 transition whitespace-nowrap"
        >
          <CalendarPlus className="w-4 h-4 text-[#0E7C86]" />
          <span>Export All to Calendar (.ics)</span>
        </button>
      </section>

      {/* Add Data from Saved Files */}
      <section className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
        <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
          Add Data from Saved Files
        </h2>
        <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-1 mb-4">
          Choose photos, receipts, PDF statements, Word (.docx), or spreadsheets. Paisa Pal parses them offline so you can review before saving.
        </p>

        <div className="flex flex-wrap gap-2.5">
          <button
            onClick={() => onOpenFileUpload('due')}
            className="min-h-[44px] px-4 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50 dark:bg-slate-800 text-[#0F1B2D] dark:text-[#E8EDF5] transition"
          >
            Scan due dates
          </button>
          <button
            onClick={() => onOpenFileUpload('inv')}
            className="min-h-[44px] px-4 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50 dark:bg-slate-800 text-[#0F1B2D] dark:text-[#E8EDF5] transition"
          >
            Scan investments
          </button>
          <button
            onClick={() => onOpenFileUpload('rec')}
            className="min-h-[44px] px-4 py-2 rounded-xl text-xs font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50 dark:bg-slate-800 text-[#0F1B2D] dark:text-[#E8EDF5] transition"
          >
            Scan document records
          </button>
        </div>

        <label className="flex items-center gap-2 mt-4 text-xs text-[#46566C] dark:text-[#A9B6C9] cursor-pointer">
          <input
            type="checkbox"
            checked={showUploadButtons}
            onChange={(e) => handleToggleUpload(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-[#0E7C86] focus:ring-[#0E7C86]"
          />
          <span>Show the "Add from file" shortcut button at the top of each page</span>
        </label>
      </section>

      {/* AICA Demonstration & Privacy Notice */}
      <section className="bg-gradient-to-r from-teal-500/10 via-[#0E7C86]/10 to-blue-500/10 dark:from-teal-950/40 dark:via-[#0E7C86]/20 dark:to-blue-950/40 border border-teal-500/30 rounded-2xl p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#0E7C86] to-[#0B3B66] text-white flex items-center justify-center flex-shrink-0 shadow-md">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
                  AICA Project Demonstration &amp; Privacy Shield
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-600 text-white">DPDP Safe</span>
              </div>
              <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-1">
                Demonstration Mode uses 100% synthetic test data across 10 fictional family members. Real documents are never required. All data stays local in your browser with WebCrypto encryption; no documents are transmitted to external AI servers.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Complete Backup, Export & Restore */}
      <section className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-[#0E7C86]" />
            <span>Complete Local Backups & CSV</span>
          </h2>
          {profile.lastBackupAt && (
            <span className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
              Last backup: {new Date(profile.lastBackupAt).toLocaleDateString()}
            </span>
          )}
        </div>
        <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mb-4">
          All your entries and uploaded document photos are stored 100% locally in your browser. Download a backup file regularly to preserve all records and attachments.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {/* Download JSON Backup */}
          <button
            onClick={handleExportBackup}
            className="flex items-center gap-2.5 p-3 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50/70 dark:bg-slate-800/60 transition text-left min-h-[56px]"
          >
            <Download className="w-5 h-5 text-[#0E7C86] flex-shrink-0" />
            <div>
              <div className="text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                Download Backup (.json)
              </div>
              <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                Full snapshot with rows & scans
              </div>
            </div>
          </button>

          {/* Restore JSON Backup */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2.5 p-3 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50/70 dark:bg-slate-800/60 transition text-left min-h-[56px]"
          >
            <Upload className="w-5 h-5 text-[#0B3B66] dark:text-[#5B9BE0] flex-shrink-0" />
            <div>
              <div className="text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                Restore Backup
              </div>
              <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                Load a previous .json backup file
              </div>
            </div>
          </button>

          {/* Download CSV */}
          <button
            onClick={() => {
              exportCsvData(rows);
              onNotify('CSV exported with all dues, investments and records.');
            }}
            className="flex items-center gap-2.5 p-3 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50/70 dark:bg-slate-800/60 transition text-left min-h-[56px]"
          >
            <FileSpreadsheet className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <div>
              <div className="text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                Download CSV
              </div>
              <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                Open in Microsoft Excel or Google Sheets
              </div>
            </div>
          </button>

          {/* Import CSV */}
          <button
            onClick={() => csvInputRef.current?.click()}
            className="flex items-center gap-2.5 p-3 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50/70 dark:bg-slate-800/60 transition text-left min-h-[56px]"
          >
            <Upload className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <div>
              <div className="text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                Import CSV
              </div>
              <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                Import spreadsheet rows
              </div>
            </div>
          </button>

          {/* Print / Save PDF */}
          <button
            onClick={triggerPrint}
            className="flex items-center gap-2.5 p-3 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50/70 dark:bg-slate-800/60 transition text-left min-h-[56px] cursor-pointer"
          >
            <Printer className="w-5 h-5 text-slate-600 dark:text-slate-400 flex-shrink-0" />
            <div>
              <div className="text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                Print / Save PDF
              </div>
              <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                Clean printer-friendly format
              </div>
            </div>
          </button>

          {/* Export Standalone HTML Statement */}
          <button
            onClick={() => {
              exportStandaloneHtml(rows, profile);
              onNotify('Standalone HTML statement exported.');
            }}
            className="flex items-center gap-2.5 p-3 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-slate-50/70 dark:bg-slate-800/60 transition text-left min-h-[56px] cursor-pointer"
          >
            <FileText className="w-5 h-5 text-[#0E7C86] flex-shrink-0" />
            <div>
              <div className="text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                Export HTML Statement (.html)
              </div>
              <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                Standalone offline HTML statement
              </div>
            </div>
          </button>

          {/* Reclassify Misplaced Entries (Safe Repeatable Migration) */}
          <button
            onClick={async () => {
              try {
                // 1. Take safety backup first
                await exportBackupJson(rows, profile);
                // 2. Perform repeatable migration
                const { migratedRows, reclassifiedCount } = reclassifyMisplacedEntries(rows);
                if (reclassifiedCount > 0) {
                  onRestoreBackup(migratedRows, profile);
                  onNotify(
                    `✓ Backup downloaded. Successfully reclassified ${reclassifiedCount} entries into Utilities, Records (Insurance), and Investments.`
                  );
                } else {
                  onNotify('All entries are already cleanly classified. No changes needed.');
                }
              } catch (e: any) {
                onNotify('Migration error: ' + (e?.message || 'unknown error'));
              }
            }}
            className="flex items-center gap-2.5 p-3 rounded-xl border border-blue-500/40 hover:border-blue-500 bg-blue-50/60 dark:bg-blue-950/30 transition text-left min-h-[56px] cursor-pointer"
          >
            <Sparkles className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
            <div className="flex-1">
              <div className="text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                Reclassify Misplaced Entries
              </div>
              <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                Backup first & segregate Utilities / Insurance / IDs
              </div>
            </div>
          </button>




          {/* Download Master Excel Workbook (.XLSX) */}
          <button
            type="button"
            onClick={() => {
              downloadMasterTrialXlsx();
              onNotify('✓ Downloaded PaisaPal_Trial_Master_Data_10_Persons.xlsx (7 sheets).');
            }}
            className="flex items-center gap-2.5 p-3 rounded-xl border border-emerald-500/40 hover:border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/30 transition text-left min-h-[56px] cursor-pointer"
          >
            <FileSpreadsheet className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
            <div className="flex-1">
              <div className="text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-1.5">
                <span>Trial Master Excel (.XLSX)</span>
                <span className="text-[9px] px-1.5 py-0.2 bg-emerald-600 text-white rounded font-bold">7 Sheets</span>
              </div>
              <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                10 Persons Index + FDs + IDs + Insurance + Dues
              </div>
            </div>
          </button>

          {/* Trial Documents & Excel Hub */}
          {onOpenTrialDocuments && (
            <button
              type="button"
              onClick={onOpenTrialDocuments}
              className="flex items-center gap-2.5 p-3 rounded-xl border border-indigo-500/40 hover:border-indigo-500 bg-gradient-to-r from-teal-500/10 via-blue-500/10 to-indigo-500/10 transition text-left min-h-[56px] cursor-pointer sm:col-span-2 lg:col-span-1"
            >
              <Sparkles className="w-5 h-5 text-amber-500 flex-shrink-0" />
              <div className="flex-1">
                <div className="text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-1.5">
                  <span>Explore 10 Persons Hub</span>
                  <span className="text-[9px] px-1.5 py-0.2 bg-indigo-600 text-white rounded font-bold">Previews</span>
                </div>
                <div className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                  Visual document previews, zoom &amp; OCR test scan
                </div>
              </div>
            </button>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          className="hidden"
          onChange={handleRestoreFile}
        />
        <input
          ref={csvInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={handleImportCsvFile}
        />
      </section>

      {/* Storage vs Multi-Device Synchronisation Explanation */}
      <section className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
        <button
          onClick={() => setShowSyncInfo((prev) => !prev)}
          className="flex items-center justify-between w-full text-left min-h-[44px]"
        >
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-[#0E7C86]" />
            <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
              How does storage work across phone and computer?
            </h2>
          </div>
          {showSyncInfo ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showSyncInfo && (
          <div className="mt-3 text-xs sm:text-sm text-[#46566C] dark:text-[#A9B6C9] space-y-3 leading-relaxed border-t border-[#DCE2EA] dark:border-[#25324A] pt-3">
            <p>
              <strong>1. Local Private Storage:</strong> Paisa Pal saves your financial records inside your browser’s private storage (<code>localStorage</code> and <code>IndexedDB</code>) on this specific computer or phone. No external servers or third-party databases hold your confidential balances, FD account numbers, or document scans.
            </p>
            <p>
              <strong>2. Transferring data between Desktop and Phone:</strong> Because local storage is private to each device and does not send data over the internet, you can move your data between devices anytime:
              <br />
              • Step A: Tap <strong>Download Backup (.json)</strong> on your computer.
              <br />
              • Step B: Send the file to your phone (via WhatsApp, Google Drive, email, or USB).
              <br />
              • Step C: Open Paisa Pal on your phone and tap <strong>Restore Backup</strong>.
            </p>
          </div>
        )}
      </section>

      {/* Installation Guides */}
      <section className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl p-5 shadow-xs">
        <button
          onClick={() => setShowInstallGuide((prev) => !prev)}
          className="flex items-center justify-between w-full text-left min-h-[44px]"
        >
          <div className="flex items-center gap-2">
            <Smartphone className="w-4 h-4 text-[#0B3B66] dark:text-[#5B9BE0]" />
            <h2 className="font-semibold text-base text-[#0F1B2D] dark:text-[#E8EDF5]">
              Step-by-Step Installation Guide (Windows, Android, iPhone & Mac)
            </h2>
          </div>
          {showInstallGuide ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        {showInstallGuide && (
          <div className="mt-3 text-xs sm:text-sm text-[#46566C] dark:text-[#A9B6C9] space-y-4 border-t border-[#DCE2EA] dark:border-[#25324A] pt-3">
            <div className="bg-[#EEF1F5] dark:bg-[#0B1220] p-3.5 rounded-xl space-y-1.5">
              <strong className="text-sm text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-1.5">
                <Smartphone className="w-4 h-4 text-emerald-600" />
                <span>On Android Phones (Google Chrome or Brave):</span>
              </strong>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Open this app in Chrome on your phone.</li>
                <li>Tap the <strong>three dots (⋮)</strong> at the top right of Chrome.</li>
                <li>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li>
                <li>Confirm by tapping <strong>Install</strong>.</li>
              </ol>
            </div>

            <div className="bg-[#EEF1F5] dark:bg-[#0B1220] p-3.5 rounded-xl space-y-1.5">
              <strong className="text-sm text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-1.5">
                <Smartphone className="w-4 h-4 text-[#0E7C86]" />
                <span>On Apple iPhone & iPad (Safari):</span>
              </strong>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Open this app link in <strong>Safari</strong>.</li>
                <li>Tap the <strong>Share</strong> button at the bottom toolbar.</li>
                <li>Scroll down the share sheet and tap <strong>Add to Home Screen</strong>.</li>
                <li>Tap <strong>Add</strong> in the top right corner.</li>
              </ol>
            </div>

            <div className="bg-[#EEF1F5] dark:bg-[#0B1220] p-3.5 rounded-xl space-y-1.5">
              <strong className="text-sm text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-1.5">
                <Laptop className="w-4 h-4 text-blue-600" />
                <span>On Windows PC & Laptop (Google Chrome or Microsoft Edge):</span>
              </strong>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>In Chrome or Edge, click the <strong>Install</strong> icon on the right side of the address bar.</li>
                <li>Or click the <strong>Install App</strong> button inside Paisa Pal’s sidebar.</li>
                <li>Click <strong>Install</strong>.</li>
              </ol>
            </div>
          </div>
        )}
      </section>

      {/* Delete All Data */}
      <section className="bg-white dark:bg-[#131C2E] border border-rose-200 dark:border-rose-950 rounded-2xl p-5 shadow-xs">
        <h2 className="font-semibold text-base text-rose-700 dark:text-rose-400 flex items-center gap-2">
          <Trash2 className="w-4 h-4" />
          <span>Delete All Data</span>
        </h2>
        <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-1 mb-3">
          Removes all entries, document scans and settings stored on this device. Be sure to download a backup file first if you might ever need your entries back.
        </p>
        <button
          onClick={handleClear}
          className="min-h-[44px] px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition shadow-sm"
        >
          Delete all my data
        </button>
      </section>

      {/* Modal displaying newly generated recovery key */}
      {showRecoveryViewModal && generatedRecoveryKey && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-60 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4"
        >
          <div className="bg-[#0A1626] border border-[#254F80] rounded-2xl max-w-sm w-full p-6 text-white space-y-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
                <KeyRound className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-semibold text-base">New Emergency Recovery Key</h3>
                <p className="text-xs text-[#9FB0C6]">Store in a safe place</p>
              </div>
            </div>

            <p className="text-xs text-[#C9D6E6] leading-relaxed">
              Your previous recovery key has been replaced. Please write down or save your new key:
            </p>

            <div className="bg-[#142338] border border-[#254F80] p-3 rounded-xl font-mono text-center text-sm font-bold tracking-widest text-[#3CB7C2] select-all">
              {generatedRecoveryKey}
            </div>

            <div className="flex flex-col gap-2 pt-2">
              <button
                type="button"
                onClick={() => handleCopyRecoveryKey(generatedRecoveryKey)}
                className="w-full py-2.5 px-4 rounded-xl bg-[#0E7C86] hover:bg-[#128e9a] text-white text-xs font-semibold transition flex items-center justify-center gap-2"
              >
                {hasCopiedRecovery ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                <span>{hasCopiedRecovery ? 'Copied!' : 'Copy to Clipboard'}</span>
              </button>
              <button
                type="button"
                onClick={() => setShowRecoveryViewModal(false)}
                className="w-full py-2.5 px-4 rounded-xl border border-[#254F80] hover:bg-[#1B406A] text-xs font-medium text-[#C9D6E6] transition"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* In-App Confirmation Modal for Delete All Data (works safely in iframes) */}
      {showDeleteAllModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-60 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-fadeIn"
        >
          <div className="bg-white dark:bg-[#131C2E] border border-rose-300 dark:border-rose-900 rounded-2xl max-w-md w-full p-6 text-[#0F1B2D] dark:text-[#E8EDF5] space-y-4 shadow-2xl">
            <div className="flex items-start gap-3.5">
              <div className="p-3 rounded-xl bg-rose-100 dark:bg-rose-950/80 text-rose-600 dark:text-rose-400 flex-shrink-0">
                <Trash2 className="w-6 h-6" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-bold text-[#0F1B2D] dark:text-[#E8EDF5]">
                  Delete Entire Vault Data?
                </h3>
                <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-1.5 leading-relaxed">
                  This will remove all <strong className="text-rose-600 dark:text-rose-400">{rows.length} entries</strong>, all scanned document attachments, and local caches from this browser. This lets you test starting with an empty vault and uploading fresh documents.
                </p>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setShowDeleteAllModal(false)}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold border border-[#DCE2EA] dark:border-[#25324A] bg-white dark:bg-[#131C2E] hover:bg-slate-50 dark:hover:bg-slate-800 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDeleteAll}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition shadow-sm cursor-pointer"
              >
                Yes, Delete Everything
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
