import React from 'react';
import { Clock, ShieldCheck, KeyRound, AlertTriangle } from 'lucide-react';
import { LicenseStatus, formatRemainingTime } from '../utils/licenseManager';

interface TrialBadgeProps {
  status: LicenseStatus;
  onOpenActivation: () => void;
}

export const TrialBadge: React.FC<TrialBadgeProps> = ({ status, onOpenActivation }) => {
  if (status.isLicensed) {
    return (
      <div 
        onClick={onOpenActivation}
        className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300/80 rounded-full text-xs font-semibold cursor-pointer transition shadow-xs"
        title={`Activated & Licensed to ${status.licensedTo || 'Valued User'} (Lifetime)`}
      >
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
        <span className="hidden sm:inline">Licensed:</span>
        <span className="font-bold truncate max-w-[130px]">{status.licensedTo || 'Full Version'}</span>
      </div>
    );
  }

  if (status.isExpired) {
    return (
      <button
        type="button"
        onClick={onOpenActivation}
        className="flex items-center gap-1.5 px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded-full text-xs font-bold shadow-md transition animate-pulse"
        title="30-Minute Trial Expired! Click to Enter License Key"
      >
        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
        <span>Trial Expired &bull; Unlock Full App</span>
      </button>
    );
  }

  const isLowTime = status.remainingSeconds < 5 * 60;

  return (
    <div className="flex items-center gap-2">
      <div 
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border shadow-xs transition ${
          isLowTime 
            ? 'bg-amber-50 text-amber-900 border-amber-300 animate-pulse' 
            : 'bg-blue-50 text-blue-900 border-blue-200'
        }`}
        title="30-Minute Free Trial Active"
      >
        <Clock className={`w-3.5 h-3.5 shrink-0 ${isLowTime ? 'text-amber-600' : 'text-blue-600'}`} />
        <span>Free Trial:</span>
        <span className="font-mono font-bold">{formatRemainingTime(status.remainingSeconds)}</span>
      </div>

      <button
        type="button"
        onClick={onOpenActivation}
        className="hidden md:flex items-center gap-1 px-2.5 py-1 bg-blue-700 hover:bg-blue-800 text-white rounded-full text-xs font-bold shadow-xs transition"
        title="Activate Full Lifetime License"
      >
        <KeyRound className="w-3 h-3" />
        <span>Enter Key</span>
      </button>
    </div>
  );
};
