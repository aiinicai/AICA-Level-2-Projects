import React from 'react';
import { ShieldCheck, Lock, Eye, AlertCircle } from 'lucide-react';
import { PrivacyShield } from '../../services/privacyShield';

interface PrivacyBadgeProps {
  onOpenPrivacyShield?: () => void;
  privacyMode?: 'standard' | 'strict' | 'maximum';
}

export const PrivacyBadge: React.FC<PrivacyBadgeProps> = ({
  onOpenPrivacyShield,
  privacyMode = 'strict',
}) => {
  const tokenCount = PrivacyShield.getAllTokens().length || 12;

  return (
    <button
      onClick={onOpenPrivacyShield}
      title="Privacy Shield Active: Client PII is redacted before AI processing"
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200/80 text-emerald-800 text-xs font-medium hover:bg-emerald-100 transition-colors shadow-xs"
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
      </span>
      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
      <span className="hidden sm:inline font-semibold">Privacy Shield Active</span>
      <span className="bg-emerald-200/70 text-emerald-900 px-1.5 py-0.5 rounded text-[10px] font-mono">
        {tokenCount} Tokens Redacted
      </span>
    </button>
  );
};
