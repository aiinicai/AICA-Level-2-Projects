import React, { useState } from 'react';
import {
  Lock, ShieldCheck, Key, Eye, EyeOff, CheckCircle2,
  FileBadge, ShieldAlert, Cpu, ArrowRight, RefreshCw, Layers
} from 'lucide-react';
import { IngestionResult } from '../types';

interface DPDPVaultViewProps {
  ingestionResult: IngestionResult | null;
  onApplySanitization: (mode: string) => Promise<void>;
  isLoading: boolean;
  onProceedToBenford: () => void;
}

export const DPDPVaultView: React.FC<DPDPVaultViewProps> = ({
  ingestionResult,
  onApplySanitization,
  isLoading,
  onProceedToBenford
}) => {
  const [activeMode, setActiveMode] = useState<'PSEUDONYMIZE' | 'MASK' | 'NONE'>('PSEUDONYMIZE');
  const [sanitizationApplied, setSanitizationApplied] = useState(false);

  const handleApply = async (mode: 'PSEUDONYMIZE' | 'MASK' | 'NONE') => {
    setActiveMode(mode);
    await onApplySanitization(mode);
    setSanitizationApplied(true);
  };

  const classifications = ingestionResult?.pii_classifications || {};
  const detectedPiiCols = Object.entries(classifications).filter(([_, meta]) => meta.is_pii);

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-4">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Lock className="w-5 h-5 text-emerald-400" />
            Indian DPDP Act, 2023 Privacy Shell &amp; PII Sanitizer
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Role &amp; Data Governance &bull; Verhoeff Aadhaar Verification &bull; PAN/GSTIN Parsing &bull; Deterministic HMAC-SHA256 Pseudonymization
          </p>
        </div>

        <button
          onClick={onProceedToBenford}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-xs font-bold shadow-lg shadow-brand-500/20 transition-all flex items-center gap-2 self-start sm:self-auto"
        >
          <span>Run Benford Analytics</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* 4 Pillars of Indian DPDP Act Governance */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
        <div className="forensic-card p-4 border-l-4 border-l-brand-500">
          <div className="flex items-center gap-2 text-xs font-bold text-white mb-1">
            <ShieldCheck className="w-4 h-4 text-brand-400" />
            1. Role &amp; Data Governance
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Data Fiduciary / Processor roles enforced. Processing restricted strictly to statutory forensic audit under Sec. 4 &amp; 7.
          </p>
          <div className="mt-2 text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Fiduciary Consent Logged
          </div>
        </div>

        <div className="forensic-card p-4 border-l-4 border-l-emerald-500">
          <div className="flex items-center gap-2 text-xs font-bold text-white mb-1">
            <Key className="w-4 h-4 text-emerald-400" />
            2. PII Scrub &amp; Pseudonymize
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Verhoeff checksum on Aadhaar, structural PAN &amp; GSTIN state validation, with salted HMAC-SHA256 tokenization.
          </p>
          <div className="mt-2 text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Relational Integrity Preserved
          </div>
        </div>

        <div className="forensic-card p-4 border-l-4 border-l-amber-500">
          <div className="flex items-center gap-2 text-xs font-bold text-white mb-1">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            3. HITL External Gateway
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Air-gapped execution by default. Zero external network egress without dual cryptographic auditor approval.
          </p>
          <div className="mt-2 text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Air-Gap Enforced
          </div>
        </div>

        <div className="forensic-card p-4 border-l-4 border-l-purple-500">
          <div className="flex items-center gap-2 text-xs font-bold text-white mb-1">
            <Cpu className="w-4 h-4 text-purple-400" />
            4. Deterministic Telemetry
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            SHA-256 dataset fingerprinting and blockchain-style tamper-evident hash chained audit journal.
          </p>
          <div className="mt-2 text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> SHA-256 Chaining Active
          </div>
        </div>
      </div>

      {/* PII Detection & Sanitization Control Box */}
      <div className="forensic-card p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <FileBadge className="w-4 h-4 text-forensic-gold" />
              Indian Personal Identifiable Information (PII) Auto-Discovery
            </h3>
            <p className="text-xs text-slate-400">
              Scanned columns against Aadhaar (Verhoeff), PAN, GSTIN, Bank A/C, IFSC, Indian Mobile (+91), and Email.
            </p>
          </div>

          {/* Sanitization Mode Buttons */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => handleApply('PSEUDONYMIZE')}
              disabled={isLoading}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeMode === 'PSEUDONYMIZE'
                  ? 'bg-brand-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Key className="w-3.5 h-3.5" />
              Pseudonymize (Recommended)
            </button>

            <button
              onClick={() => handleApply('MASK')}
              disabled={isLoading}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeMode === 'MASK'
                  ? 'bg-brand-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <EyeOff className="w-3.5 h-3.5" />
              Mask Display
            </button>

            <button
              onClick={() => handleApply('NONE')}
              disabled={isLoading}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeMode === 'NONE'
                  ? 'bg-rose-600/80 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Raw Local
            </button>
          </div>
        </div>

        {/* Detected Columns Grid */}
        {detectedPiiCols.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {detectedPiiCols.map(([colName, meta]) => (
              <div key={colName} className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-white block">{colName}</span>
                  <span className="text-[10px] text-brand-400 font-mono">
                    Type: {meta.detected_pii_type}
                  </span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 font-semibold uppercase">
                  {meta.recommended_action}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 rounded-lg bg-slate-950/50 border border-slate-800/80 text-xs text-slate-400 text-center">
            No direct sensitive PII headers detected in schema. Standard financial transaction columns mapped.
          </div>
        )}

        {/* Informational Guidance on Pseudonymization */}
        <div className="p-4 rounded-xl bg-brand-500/5 border border-brand-500/20 text-xs text-slate-300 space-y-1.5">
          <p className="font-semibold text-brand-300 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" /> Why Deterministic Salted HMAC-SHA256 Pseudonymization?
          </p>
          <p className="text-slate-400 leading-relaxed">
            Forensic analysis tests like <b>Relative Size Factor (RSF)</b> and <b>Duplicate Payment Detection</b> require grouping transactions by vendor or account.
            Pseudonymization creates unique tokens (e.g. <code className="text-brand-300 font-mono">VEND-PSEUDO-8F4A2B</code>) for each entity, preserving exact mathematical relationships and grouping without exposing or storing personal names, Aadhaar numbers, or account details.
          </p>
        </div>
      </div>
    </div>
  );
};
