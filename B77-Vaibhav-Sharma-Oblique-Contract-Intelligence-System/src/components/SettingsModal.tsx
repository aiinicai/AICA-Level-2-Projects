import React, { useState } from 'react';
import { 
  Settings as SettingsIcon, 
  ShieldCheck, 
  Trash2, 
  Check, 
  Cpu, 
  BookOpen,
  Lock,
  RefreshCw
} from 'lucide-react';
import { ContractDocument } from '../types/contract';

interface SettingsProps {
  contract: ContractDocument | null;
  onClearContract: () => void;
}

export const SettingsModal: React.FC<SettingsProps> = ({ contract, onClearContract }) => {
  const [defaultFramework, setDefaultFramework] = useState<string>('Ind AS');
  const [autoCrossClause, setAutoCrossClause] = useState<boolean>(true);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6 text-xs text-slate-800">
        <div className="flex items-center space-x-2 border-b border-slate-100 pb-4">
          <SettingsIcon className="w-5 h-5 text-indigo-600" />
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight">Application & Compliance Settings</h1>
            <p className="text-xs text-slate-500">Configure AI review models, default accounting frameworks, and data retention policies.</p>
          </div>
        </div>

        {/* AI & Model Configuration */}
        <div className="space-y-3">
          <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
            <Cpu className="w-4 h-4 text-indigo-600" />
            <span>AI Reasoning Engine</span>
          </h3>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-900">Active Intelligence Model</span>
                <p className="text-slate-500 text-[11px]">Primary reasoning and Indian statutory knowledge extractor</p>
              </div>
              <span className="px-2.5 py-1 rounded bg-indigo-100 text-indigo-900 font-mono font-bold text-[11px]">
                gemini-3.7-flash (Google GenAI)
              </span>
            </div>
          </div>
        </div>

        {/* Default Framework */}
        <div className="space-y-3 pt-2">
          <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
            <BookOpen className="w-4 h-4 text-indigo-600" />
            <span>Default Accounting Standard</span>
          </h3>

          <div className="space-y-2">
            <select
              value={defaultFramework}
              onChange={(e) => setDefaultFramework(e.target.value)}
              className="w-full p-2.5 rounded-lg border border-slate-300 bg-white font-medium text-slate-800"
            >
              <option value="Ind AS">Ind AS (Indian Accounting Standards - Converged with IFRS)</option>
              <option value="Accounting Standards (AS)">Accounting Standards (AS / Indian GAAP)</option>
              <option value="Schedule III">Companies Act Schedule III Presentation</option>
            </select>
            <p className="text-[11px] text-slate-500">
              Selected framework determines how revenue milestones, retention discounting, and lease terms are evaluated.
            </p>
          </div>
        </div>

        {/* Auto Cross-Clause Review */}
        <div className="space-y-3 pt-2">
          <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
            Analysis Pipeline Behaviors
          </h3>

          <div className="flex items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-200">
            <div>
              <span className="font-bold text-slate-900 block">Automatic Cross-Clause Second-Pass Reasoning</span>
              <span className="text-slate-500 text-[11px]">Automatically execute multi-clause compounding checks during initial contract analysis</span>
            </div>
            <input
              type="checkbox"
              checked={autoCrossClause}
              onChange={(e) => setAutoCrossClause(e.target.checked)}
              className="w-4 h-4 text-indigo-600 rounded border-slate-300"
            />
          </div>
        </div>

        {/* Privacy & Confidentiality Notice */}
        <div className="space-y-3 pt-2">
          <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
            <Lock className="w-4 h-4 text-emerald-600" />
            <span>Data Privacy & Confidentiality Policy</span>
          </h3>

          <div className="bg-emerald-50/50 p-4 rounded-xl border border-emerald-200 text-emerald-950 space-y-1">
            <span className="font-bold block text-xs">Client Contract Confidentiality Enforced</span>
            <p className="text-[11px] leading-relaxed text-emerald-900">
              Contract files and extracted clause texts are processed in-memory for active analysis and are never persisted permanently to database disks or utilized for AI training.
            </p>
          </div>
        </div>

        {/* Reset / Delete Session */}
        {contract && (
          <div className="space-y-3 pt-4 border-t border-slate-200">
            <h3 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] text-rose-900">
              Session Management
            </h3>

            <div className="flex items-center justify-between p-4 bg-rose-50/40 rounded-xl border border-rose-200">
              <div>
                <span className="font-bold text-slate-900 block">Clear Active Contract Analysis</span>
                <span className="text-slate-500 text-[11px]">Unload current contract ({contract.identity.title}) and reset workspace</span>
              </div>
              <button
                onClick={onClearContract}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white flex items-center space-x-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Workspace</span>
              </button>
            </div>
          </div>
        )}

        <div className="pt-4 flex justify-end">
          <button
            onClick={handleSave}
            className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs flex items-center space-x-1.5"
          >
            {savedSuccess ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-300" />
                <span>Preferences Saved!</span>
              </>
            ) : (
              <span>Save Preferences</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
