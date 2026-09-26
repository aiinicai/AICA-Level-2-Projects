import React, { useState } from 'react';
import {
  Settings,
  Sliders,
  Shield,
  Layers,
  Building,
  Key,
  Database,
  CheckCircle2,
  Save,
  Server,
} from 'lucide-react';
import { SystemSettings } from '../../types';

interface SettingsViewProps {
  settings: SystemSettings;
  onUpdateSettings: (newSettings: SystemSettings) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  settings,
  onUpdateSettings,
}) => {
  const [formState, setFormState] = useState<SystemSettings>(settings);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateSettings(formState);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div id="settings-module-container" className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">System Configuration & Policies</h2>
            <span className="text-[11px] bg-indigo-500/10 text-indigo-300 font-medium px-2 py-0.5 rounded-full border border-indigo-500/20">
              CFO Level Control
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage multi-GSTIN branches, OCR auto-posting confidence thresholds, AS 2 inventory write-down policies, and external portal APIs.
          </p>
        </div>

        <button
          onClick={handleSave}
          className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm cursor-pointer"
        >
          <Save className="w-4 h-4" />
          <span>Save Accounting Policies</span>
        </button>
      </div>

      {saveSuccess && (
        <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>System configuration and AS 2 policies updated successfully across all branches!</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6 text-xs">
        {/* Section 1: Entity Details & CIN */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <Building className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-slate-100 text-sm">Corporate Legal Entity Details</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 font-medium mb-1">Company Legal Name</label>
              <input
                type="text"
                value={formState.companyName}
                onChange={(e) => setFormState({ ...formState, companyName: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-slate-300 font-medium mb-1">Corporate Identity Number (CIN)</label>
              <input
                type="text"
                value={formState.cin}
                onChange={(e) => setFormState({ ...formState, cin: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
              />
            </div>
            <div>
              <label className="block text-slate-300 font-medium mb-1">Permanent Account Number (PAN)</label>
              <input
                type="text"
                value={formState.pan}
                onChange={(e) => setFormState({ ...formState, pan: e.target.value })}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
              />
            </div>
            <div>
              <label className="block text-slate-300 font-medium mb-1">Accounting Standards Framework</label>
              <select
                value={formState.accountingStandard}
                onChange={(e) => setFormState({ ...formState, accountingStandard: e.target.value as any })}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200"
              >
                <option value="IND_AS">Indian Accounting Standards (Ind AS)</option>
                <option value="INDIAN_GAAP">Indian GAAP (Companies Accounting Standard Rules 2006)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Section 2: OCR Threshold & Internal Controls */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <Sliders className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-slate-100 text-sm">
              OCR Auto-Posting Threshold & Internal Financial Controls (IFC)
            </h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-slate-200 font-semibold block">
                  Minimum Extraction Confidence for Auto-Posting: {formState.ocrAutoPostThreshold}%
                </label>
                <span className="text-slate-400 text-[11px]">
                  Invoices/bills with confidence score below this percentage are automatically routed to the Review Queue for Maker-Checker approval.
                </span>
              </div>
              <span className="font-mono font-bold text-indigo-400 text-sm">{formState.ocrAutoPostThreshold}%</span>
            </div>

            <input
              type="range"
              min="70"
              max="98"
              value={formState.ocrAutoPostThreshold}
              onChange={(e) => setFormState({ ...formState, ocrAutoPostThreshold: Number(e.target.value) })}
              className="w-full accent-indigo-500 cursor-pointer"
            />
          </div>
        </div>

        {/* Section 3: AS 2 / Ind AS 2 Inventory Provision Policy */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <Shield className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-slate-100 text-sm">
              AS 2 / Ind AS 2 Inventory Write-Down & Provisioning Policy
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 font-medium mb-1">Slow-Moving Inactive Threshold</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={formState.inventoryProvisionPolicy.slowMovingMonths}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      inventoryProvisionPolicy: {
                        ...formState.inventoryProvisionPolicy,
                        slowMovingMonths: Number(e.target.value),
                      },
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
                />
                <span className="text-slate-400">Months</span>
              </div>
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">Dead Stock Inactive Threshold</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={formState.inventoryProvisionPolicy.deadStockMonths}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      inventoryProvisionPolicy: {
                        ...formState.inventoryProvisionPolicy,
                        deadStockMonths: Number(e.target.value),
                      },
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
                />
                <span className="text-slate-400">Months</span>
              </div>
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">6 to 12 Months Provision (%)</label>
              <input
                type="number"
                value={formState.inventoryProvisionPolicy.provision6To12MonthsPct}
                onChange={(e) =>
                  setFormState({
                    ...formState,
                    inventoryProvisionPolicy: {
                      ...formState.inventoryProvisionPolicy,
                      provision6To12MonthsPct: Number(e.target.value),
                    },
                  })
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-medium mb-1">&gt; 12 Months Provision (%)</label>
              <input
                type="number"
                value={formState.inventoryProvisionPolicy.provisionAbove12MonthsPct}
                onChange={(e) =>
                  setFormState({
                    ...formState,
                    inventoryProvisionPolicy: {
                      ...formState.inventoryProvisionPolicy,
                      provisionAbove12MonthsPct: Number(e.target.value),
                    },
                  })
                }
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-200 font-mono"
              />
            </div>
          </div>
        </div>

        {/* Section 4: Multi-Branch & GSTIN Entities */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-slate-100 text-sm">Multi-GSTIN Operating Branches</h3>
          </div>

          <div className="space-y-2.5">
            {formState.multiGstinList.map((branch) => (
              <div key={branch.gstin} className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between font-mono">
                <div>
                  <div className="font-sans font-semibold text-slate-200">{branch.branchName}</div>
                  <div className="text-[11px] text-slate-400">{branch.gstin} • State: {branch.stateName} (Code {branch.stateCode})</div>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-sans">
                  Active
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Section 5: Portal APIs & Connected Integrations */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <Server className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-slate-100 text-sm">Government Portals & Banking Gateway Integrations</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
              <div>
                <div className="font-semibold text-slate-200">GSTN Returns & 2B Recon API</div>
                <div className="text-[11px] text-slate-400">GSP Direct Sync Active</div>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Connected
              </span>
            </div>

            <div className="p-3.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
              <div>
                <div className="font-semibold text-slate-200">NIC E-Invoicing (IRN) & E-way Bill</div>
                <div className="text-[11px] text-slate-400">Real-time QR Code generation</div>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Connected
              </span>
            </div>

            <div className="p-3.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
              <div>
                <div className="font-semibold text-slate-200">HDFC Corporate Banking Gateway</div>
                <div className="text-[11px] text-slate-400">Automated MT940 daily feed</div>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Connected
              </span>
            </div>

            <div className="p-3.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
              <div>
                <div className="font-semibold text-slate-200">Gemini 3.8 Flash OCR Pipeline</div>
                <div className="text-[11px] text-slate-400">Server-side multi-modal extraction</div>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Active
              </span>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};
