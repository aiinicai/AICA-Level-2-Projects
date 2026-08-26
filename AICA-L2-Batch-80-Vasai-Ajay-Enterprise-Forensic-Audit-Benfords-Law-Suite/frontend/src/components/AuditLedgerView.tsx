import React, { useState, useEffect } from 'react';
import {
  Link2, CheckCircle2, AlertOctagon, Shield, RefreshCw,
  FileCheck, Key, Lock, Hash, ShieldCheck, ArrowRight
} from 'lucide-react';
import { AuditBlock } from '../types';

interface AuditLedgerViewProps {
  onProceedToReport: () => void;
}

export const AuditLedgerView: React.FC<AuditLedgerViewProps> = ({ onProceedToReport }) => {
  const [ledger, setLedger] = useState<AuditBlock[]>([]);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<{
    is_valid: boolean;
    verification_message: string;
    corrupted_block_index: number | null;
  } | null>(null);

  const fetchLedger = async () => {
    try {
      const res = await fetch('/api/audit/ledger');
      const data = await res.json();
      if (data.success) {
        setLedger(data.ledger);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const verifyIntegrity = async () => {
    setIsVerifying(true);
    try {
      const res = await fetch('/api/audit/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      setVerificationResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsVerifying(false);
    }
  };

  useEffect(() => {
    fetchLedger();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Link2 className="w-5 h-5 text-brand-400" />
            Tamper-Evident SHA-256 Chained Audit Trail
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Immutable Blockchain-Style Journal &bull; Mathematical Hash Continuity &bull; Indian DPDP Act 2023 Integrity Mandate
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={verifyIntegrity}
            disabled={isVerifying}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 border border-slate-700 text-xs font-bold text-white flex items-center gap-2 transition-all shadow"
          >
            {isVerifying ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />}
            Verify Chain Integrity
          </button>

          <button
            onClick={onProceedToReport}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 text-white text-xs font-bold shadow-lg shadow-brand-500/20 transition-all flex items-center gap-2"
          >
            <span>Generate Executive Report</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Verification Status Banner (if verified) */}
      {verificationResult && (
        <div className={`p-4 rounded-xl border flex items-center gap-3 text-xs ${
          verificationResult.is_valid
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
            : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
        }`}>
          {verificationResult.is_valid ? (
            <CheckCircle2 className="w-6 h-6 flex-shrink-0 text-emerald-400" />
          ) : (
            <AlertOctagon className="w-6 h-6 flex-shrink-0 text-rose-400" />
          )}
          <div>
            <span className="font-bold text-sm block">
              {verificationResult.is_valid ? 'Cryptographic Hash Chain Verified Tamper-Free' : 'Tampering Detected in Audit Trail!'}
            </span>
            <span>{verificationResult.verification_message}</span>
          </div>
        </div>
      )}

      {/* Blockchain Blocks List */}
      <div className="space-y-3">
        {ledger.map((block) => (
          <div
            key={block.index}
            className="forensic-card p-4 hover:border-slate-700 transition-all space-y-2.5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-brand-500/10 text-brand-400 font-mono font-bold text-xs flex items-center justify-center border border-brand-500/20">
                  #{block.index}
                </span>
                <span className="text-xs font-bold text-white font-mono">{block.action}</span>
              </div>
              <div className="flex items-center gap-3 text-[11px] text-slate-400">
                <span className="font-mono">{block.datetime}</span>
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-medium">
                  {block.user_role}
                </span>
              </div>
            </div>

            {/* Hashes & Linkage */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
              <div className="truncate">
                <span className="text-slate-500">Block Hash: </span>
                <span className="text-brand-300 font-semibold">{block.block_hash}</span>
              </div>
              <div className="truncate">
                <span className="text-slate-500">Prev Hash: </span>
                <span className="text-slate-400">{block.prev_hash}</span>
              </div>
            </div>

            {/* Details JSON */}
            <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
              <span className="text-slate-500 block text-[10px] uppercase font-bold mb-1">Payload Metadata:</span>
              <pre>{JSON.stringify(block.details, null, 2)}</pre>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
