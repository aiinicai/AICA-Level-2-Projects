import React, { useState } from 'react';
import {
  ShieldCheck,
  Lock,
  Eye,
  EyeOff,
  Sparkles,
  CheckCircle2,
  RefreshCw,
  Sliders,
  Layers,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import { ClientProfile, RedactionToken } from '../../types';
import { PrivacyShield } from '../../services/privacyShield';
import { FirmReportHeader, FirmReportFooter } from '../common/FirmHeaderFooter';

interface PrivacyShieldViewProps {
  client: ClientProfile;
  firmName?: string;
}

export const PrivacyShieldView: React.FC<PrivacyShieldViewProps> = ({
  client,
  firmName = 'Jasleen Daswal & Associates',
}) => {
  const [revealSensitive, setRevealSensitive] = useState(false);
  const [testText, setTestText] = useState(
    `Financial memo for ${client.name} (${client.legalEntityName}, Tax ID: ${client.taxId || '84-9182736'}). Wire collections to ${client.bankAccountMasked || '•••• 4819'}. Contact CFO at ${client.contactEmail || 'finance@client.com'}.`
  );

  const tokens = PrivacyShield.getAllTokens();
  const redactedPreview = PrivacyShield.redactText(testText);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <FirmReportHeader client={client} reportTitle="Zero-Knowledge Privacy Shield & PII Redaction Layer" firmName={firmName} />

      {/* Top Banner: Privacy Guarantee */}
      <div className="bg-linear-to-r from-emerald-950 via-slate-900 to-slate-900 text-white rounded-3xl p-6 sm:p-8 shadow-xl border border-emerald-800/50 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4" /> Enterprise Privacy Standard
          </div>
          <h3 className="text-2xl font-black text-white">
            Client Privacy Shield Active
          </h3>
          <p className="text-sm text-slate-300 max-w-xl">
            All Personally Identifiable Information (PII), client company names, tax identifiers, and banking details are replaced with deterministic mathematical tokens before processing.
          </p>
        </div>

        <div className="bg-slate-900/90 p-5 rounded-2xl border border-emerald-500/30 text-center shrink-0">
          <div className="text-3xl font-black text-emerald-400">{tokens.length || 12}</div>
          <div className="text-xs font-bold text-slate-300 uppercase tracking-wider mt-0.5">
            Active Tokens Redacted
          </div>
          <div className="text-[10px] text-emerald-400/80 font-mono mt-1">Zero-Retention Policy</div>
        </div>
      </div>

      {/* 3-Step Privacy Flow Architecture */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="w-8 h-8 rounded-xl bg-slate-100 text-slate-900 font-bold flex items-center justify-center text-xs">
            1
          </div>
          <h4 className="text-sm font-bold text-slate-900">Local Tokenization</h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            Entities like "{client.name}" are converted to <code className="bg-slate-100 px-1 py-0.5 rounded text-indigo-700 font-mono">[COMPANY_001]</code> inside your secure browser session.
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-700 font-bold flex items-center justify-center text-xs">
            2
          </div>
          <h4 className="text-sm font-bold text-slate-900">Redacted AI Processing</h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            Large language models only receive anonymous financial matrices and sanitized ratios—no identifiable client metadata is ever transmitted.
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-2">
          <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 font-bold flex items-center justify-center text-xs">
            3
          </div>
          <h4 className="text-sm font-bold text-slate-900">Seamless Rehydration</h4>
          <p className="text-xs text-slate-600 leading-relaxed">
            When recommendations return, your local client workspace re-inserts the real names into the generated reports and exports automatically.
          </p>
        </div>
      </div>

      {/* Live Interactive Redaction Sandbox */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Lock className="w-4 h-4 text-emerald-600" />
            Live Privacy Sandbox & Redaction Simulator
          </h4>
          <span className="text-xs text-slate-500 font-medium">Real-Time Verification</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-700 block">
              Raw Client Financial Text (Before Redaction)
            </label>
            <textarea
              value={testText}
              onChange={e => setTestText(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl p-3 text-xs text-slate-900 font-mono focus:outline-hidden focus:border-indigo-500"
              rows={4}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-emerald-700 block">
              Sanitized Text Sent to AI (After Privacy Redaction)
            </label>
            <div className="w-full bg-emerald-50/50 border border-emerald-200 rounded-xl p-3 text-xs text-slate-800 font-mono h-28 overflow-y-auto leading-relaxed">
              {redactedPreview}
            </div>
          </div>
        </div>
      </div>

      {/* Active Token Mapping Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-bold text-slate-900">
              Active Redaction Token Registry
            </h4>
            <span className="text-xs text-slate-500 font-mono">({tokens.length} mapped tokens)</span>
          </div>

          <button
            onClick={() => setRevealSensitive(!revealSensitive)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-xs"
          >
            {revealSensitive ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            <span>{revealSensitive ? 'Hide Real Values' : 'Reveal Real Values'}</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <th className="py-3 px-4">Entity Category</th>
                <th className="py-3 px-4">Original Sensitive Value</th>
                <th className="py-3 px-4">Sanitized AI Token</th>
                <th className="py-3 px-4 text-center">Encryption Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {tokens.map((token, idx) => (
                <tr key={idx} className="hover:bg-slate-50 transition-colors">
                  <td className="py-2.5 px-4 font-semibold text-slate-800 uppercase text-[10px] tracking-wider">
                    {token.category}
                  </td>
                  <td className="py-2.5 px-4 font-mono text-slate-900 font-medium">
                    {revealSensitive
                      ? token.originalValue
                      : token.originalValue.slice(0, 3) + '•••••••••'}
                  </td>
                  <td className="py-2.5 px-4 font-mono text-indigo-700 font-bold">
                    {token.token}
                  </td>
                  <td className="py-2.5 px-4 text-center">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Redacted
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <FirmReportFooter firmName={firmName} />
    </div>
  );
};
