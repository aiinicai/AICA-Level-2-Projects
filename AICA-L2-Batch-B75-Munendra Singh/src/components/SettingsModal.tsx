import React, { useState } from 'react';
import { 
  X, 
  Settings, 
  ShieldCheck, 
  Cpu, 
  Cloud, 
  Key, 
  Database, 
  Trash2, 
  CheckCircle2, 
  AlertCircle,
  HardDrive
} from 'lucide-react';
import { AppSettings, saveSettings, clearVault, getSavedAudits } from '../utils/localVault';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onSaveSettings: (newSettings: AppSettings) => void;
  onRefreshAudits: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  onSaveSettings,
  onRefreshAudits,
}) => {
  const [useOfflineEngine, setUseOfflineEngine] = useState(settings.useOfflineEngine);
  const [apiKey, setApiKey] = useState(settings.apiKey || '');
  const [strictTolerance, setStrictTolerance] = useState(settings.strictTolerance);
  const [autoSaveReports, setAutoSaveReports] = useState(settings.autoSaveReports);
  const [savedCount, setSavedCount] = useState(getSavedAudits().length);
  const [clearedMessage, setClearedMessage] = useState(false);

  if (!isOpen) return null;

  const handleSave = () => {
    const updated: AppSettings = {
      useOfflineEngine,
      apiKey: apiKey.trim() || undefined,
      strictTolerance,
      autoSaveReports,
    };
    saveSettings(updated);
    onSaveSettings(updated);
    onClose();
  };

  const handleClearHistory = () => {
    if (window.confirm('Are you sure you want to clear all locally saved audit reports from your device?')) {
      clearVault();
      setSavedCount(0);
      setClearedMessage(true);
      onRefreshAudits();
      setTimeout(() => setClearedMessage(false), 3000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white border-2 border-[#141414] shadow-dense max-w-xl w-full overflow-hidden animate-scaleIn my-8">
        {/* Header */}
        <div className="bg-[#141414] text-white p-4 flex items-center justify-between border-b border-[#141414]">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 bg-[#00FF00] flex items-center justify-center text-[#141414] font-bold">
              <Settings className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm uppercase tracking-tight font-sans">
                Audit Engine & Offline Privacy Settings
              </h3>
              <p className="text-[10px] text-neutral-400 font-mono">
                LOCAL EXECUTION • PRIVACY • DATA PERSISTENCE
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-white p-1 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 sm:p-6 space-y-6 text-xs text-[#141414]">
          {/* Engine Selection */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-[#141414] mb-2 font-mono">
              Audit Verification Engine
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setUseOfflineEngine(true)}
                className={`p-3 border-2 text-left transition flex flex-col justify-between ${
                  useOfflineEngine
                    ? 'border-[#141414] bg-[#F4F4F2] shadow-dense-sm ring-2 ring-[#00FF00]/40'
                    : 'border-neutral-200 bg-white hover:bg-neutral-50'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-[11px] uppercase flex items-center gap-1.5 font-mono">
                      <Cpu className="w-3.5 h-3.5 text-green-700" />
                      Offline CA Engine
                    </span>
                    {useOfflineEngine && (
                      <span className="bg-green-700 text-white text-[8px] px-1.5 py-0.2 font-mono font-bold uppercase">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-neutral-600 leading-relaxed font-sans">
                    100% on-device deterministic statutory rules, casting & note proofreading. Zero cloud communication.
                  </p>
                </div>
                <div className="mt-2.5 pt-2 border-t border-neutral-200 text-[9px] font-mono text-green-800 font-bold uppercase flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Zero Data Leakage
                </div>
              </button>

              <button
                type="button"
                onClick={() => setUseOfflineEngine(false)}
                className={`p-3 border-2 text-left transition flex flex-col justify-between ${
                  !useOfflineEngine
                    ? 'border-[#141414] bg-[#F4F4F2] shadow-dense-sm ring-2 ring-[#00FF00]/40'
                    : 'border-neutral-200 bg-white hover:bg-neutral-50'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-[11px] uppercase flex items-center gap-1.5 font-mono">
                      <Cloud className="w-3.5 h-3.5 text-blue-700" />
                      Cloud Gemini AI
                    </span>
                    {!useOfflineEngine && (
                      <span className="bg-blue-700 text-white text-[8px] px-1.5 py-0.2 font-mono font-bold uppercase">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-neutral-600 leading-relaxed font-sans">
                    Uses remote Gemini 3.7 Flash API server for analysis and conversational follow-ups.
                  </p>
                </div>
                <div className="mt-2.5 pt-2 border-t border-neutral-200 text-[9px] font-mono text-blue-800 font-bold uppercase flex items-center gap-1">
                  Requires API Connection
                </div>
              </button>
            </div>
          </div>

          {/* Cloud API Key (Shown if Cloud selected) */}
          {!useOfflineEngine && (
            <div className="p-3.5 bg-neutral-50 border border-neutral-300 space-y-2 animate-fadeIn font-mono">
              <label className="block text-[10px] font-bold uppercase tracking-wider text-[#141414] flex items-center gap-1.5">
                <Key className="w-3 h-3" />
                Gemini API Key (Optional Override)
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full bg-white border border-[#141414] px-3 py-1.5 text-xs text-[#141414] font-mono focus:outline-none"
              />
              <p className="text-[9px] text-neutral-500 font-sans">
                Leave blank to use the server environment default key. Stored locally in your browser session.
              </p>
            </div>
          )}

          {/* Preferences */}
          <div className="space-y-2.5 pt-2 border-t border-neutral-200">
            <h4 className="text-[10px] font-bold uppercase tracking-wider font-mono text-neutral-700">
              Audit Preferences
            </h4>
            
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={strictTolerance}
                onChange={(e) => setStrictTolerance(e.target.checked)}
                className="accent-[#141414] w-3.5 h-3.5"
              />
              <span className="font-mono text-xs text-[#141414]">
                Strict Zero-Variance Mathematical Casting Check
              </span>
            </label>

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoSaveReports}
                onChange={(e) => setAutoSaveReports(e.target.checked)}
                className="accent-[#141414] w-3.5 h-3.5"
              />
              <span className="font-mono text-xs text-[#141414]">
                Auto-Save Audit Reports to Local Storage Vault
              </span>
            </label>
          </div>

          {/* Local Storage Vault Status */}
          <div className="p-3 bg-[#F9F9F7] border border-[#141414] space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] font-bold uppercase flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-[#141414]" />
                Local Vault Storage
              </span>
              <span className="text-[10px] font-mono font-bold text-neutral-700">
                {savedCount} Audits Stored
              </span>
            </div>
            <p className="text-[10px] text-neutral-600 font-sans">
              All financial statements and audit findings remain 100% stored in your browser/desktop without transmission to any cloud database.
            </p>
            {clearedMessage && (
              <div className="text-[10px] font-mono text-green-700 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Local audit history successfully wiped.
              </div>
            )}
            {savedCount > 0 && (
              <button
                type="button"
                onClick={handleClearHistory}
                className="mt-1 text-[10px] font-mono font-bold uppercase text-red-700 hover:text-red-900 flex items-center gap-1 underline"
              >
                <Trash2 className="w-3 h-3" /> Clear Local Vault History
              </button>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="bg-[#F4F4F2] p-4 border-t border-[#141414] flex items-center justify-between">
          <div className="text-[10px] font-mono text-neutral-500 uppercase">
            PRIVACY: NO EXTERNAL TELEMETRY
          </div>
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-mono font-bold uppercase border border-[#141414] bg-white hover:bg-neutral-100"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-1.5 text-xs font-mono font-bold uppercase bg-[#141414] text-[#00FF00] border border-[#141414] hover:bg-neutral-800 shadow-dense-sm flex items-center gap-1.5"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Save Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
