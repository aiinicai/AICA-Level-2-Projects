import React, { useState } from 'react';
import { 
  Lock, 
  KeyRound, 
  CheckCircle2, 
  Copy, 
  ShieldAlert, 
  Sparkles, 
  X, 
  Laptop,
  Check,
  Loader2
} from 'lucide-react';
import { 
  LicenseStatus, 
  activateLicense
} from '../utils/licenseManager';

interface LicenseLockModalProps {
  isOpen: boolean;
  onClose?: () => void;
  status: LicenseStatus;
  isForcedLock?: boolean;
}

export const LicenseLockModal: React.FC<LicenseLockModalProps> = ({
  isOpen,
  onClose,
  status,
  isForcedLock = false
}) => {
  const [licenseKeyInput, setLicenseKeyInput] = useState('');
  const [clientNameInput, setClientNameInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleCopyMachineId = () => {
    navigator.clipboard.writeText(status.machineId);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2500);
  };

  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!licenseKeyInput.trim()) {
      setErrorMessage('Please enter an Activation License Key.');
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await activateLicense(licenseKeyInput.trim(), clientNameInput.trim() || 'Valued Customer');
      if (result.success) {
        setSuccessMessage(result.message);
        setTimeout(() => {
          if (onClose) onClose();
        }, 2000);
      } else {
        setErrorMessage(result.message);
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Activation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden my-6">
        
        {/* Header Ribbon */}
        <div className={`px-6 py-5 ${isForcedLock ? 'bg-gradient-to-r from-red-700 to-rose-800' : 'bg-gradient-to-r from-blue-800 to-indigo-900'} text-white relative`}>
          {!isForcedLock && onClose && (
            <button
              type="button"
              onClick={onClose}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition"
            >
              <X className="w-5 h-5" />
            </button>
          )}

          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-white/15 flex items-center justify-center backdrop-blur-xs shadow-inner">
              {isForcedLock ? <Lock className="w-6 h-6 text-white" /> : <KeyRound className="w-6 h-6 text-white" />}
            </div>
            <div>
              <h2 className="text-lg font-bold tracking-wide">
                {isForcedLock ? 'Trial Expired — Activation Required' : 'Software License & Activation'}
              </h2>
              <p className="text-xs text-white/80 mt-0.5">
                {isForcedLock 
                  ? 'Your 30-minute free trial has ended. Unlock permanent access below.' 
                  : 'Activate your commercial license for lifetime unlimited access.'}
              </p>
            </div>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5">
          
          {/* Machine ID Box */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Laptop className="w-4 h-4 text-blue-700" />
                Physical Computer Hardware ID
              </span>
              <span className="text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300 px-2 py-0.5 rounded-full">
                Motherboard & Hardware Bound
              </span>
            </div>

            <div className="flex items-center gap-2">
              <code className="flex-1 px-3 py-2 bg-white border border-slate-300 rounded-lg font-mono font-bold text-xs sm:text-sm text-slate-900 tracking-wider text-center select-all shadow-2xs">
                {status.machineId}
              </code>
              <button
                type="button"
                onClick={handleCopyMachineId}
                className="flex items-center gap-1.5 px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded-lg text-xs font-bold transition shrink-0"
              >
                {copiedId ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                <span>{copiedId ? 'Copied!' : 'Copy ID'}</span>
              </button>
            </div>

            <div className="p-2.5 bg-blue-50/70 border border-blue-200/60 rounded-lg text-[11px] text-slate-600 leading-relaxed space-y-1">
              <p className="font-semibold text-blue-900 flex items-center gap-1">
                <span>🛡️</span>
                <span>1-Time Demo Policy: Each PC is entitled to only one 30-minute evaluation.</span>
              </p>
              <p className="text-slate-500">
                Reinstalling or deleting the application will not grant another demo period. Share your <b>Hardware ID</b> above with the vendor to receive your unique permanent Activation Key.
              </p>
            </div>
          </div>

          {/* Already Licensed Notice */}
          {status.isLicensed && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-xs space-y-1">
              <div className="font-bold flex items-center gap-1.5 text-sm text-emerald-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                Software is Fully Activated & Licensed
              </div>
              <p>Licensed To: <b>{status.licensedTo}</b></p>
              {status.activatedAt && (
                <p className="text-[11px] text-emerald-700">
                  Activated On: {new Date(status.activatedAt).toLocaleDateString()}
                </p>
              )}
            </div>
          )}

          {/* Key Input Form */}
          <form onSubmit={handleActivate} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-800 mb-1">
                Your Name / Firm Name (Optional)
              </label>
              <input
                type="text"
                value={clientNameInput}
                onChange={(e) => setClientNameInput(e.target.value)}
                placeholder="e.g. Ramesh Patel / ABC Associates"
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-900 focus:ring-2 focus:ring-blue-600 outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-800 mb-1">
                Enter Activation License Key *
              </label>
              <input
                type="text"
                value={licenseKeyInput}
                onChange={(e) => {
                  setLicenseKeyInput(e.target.value.toUpperCase());
                  setErrorMessage(null);
                }}
                placeholder="PDD-ACTV-XXXX-XXXX-XXXX"
                className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-mono font-bold text-slate-900 uppercase tracking-widest text-center focus:ring-2 focus:ring-blue-600 outline-none"
              />
            </div>

            {/* Error banner */}
            {errorMessage && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 font-semibold flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-red-600 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Success banner */}
            {successMessage && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 font-bold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{successMessage}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 bg-gradient-to-r from-blue-700 to-indigo-700 hover:from-blue-800 hover:to-indigo-800 disabled:opacity-60 text-white rounded-xl text-sm font-bold shadow-md transition flex items-center justify-center gap-2 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Validating Hardware License...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Activate Full Lifetime License</span>
                </>
              )}
            </button>
          </form>

          {/* Contact / Help Section */}
          <div className="pt-2 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
            <span>Need an Activation Key?</span>
            <span className="font-semibold text-slate-700">Contact Software Vendor</span>
          </div>

        </div>

      </div>
    </div>
  );
};
