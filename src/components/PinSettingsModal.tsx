import React, { useState } from 'react';
import {
  X,
  Lock,
  ShieldCheck,
  KeyRound,
  Check,
  Eye,
  EyeOff,
  AlertCircle,
  Mail,
  ShieldAlert
} from 'lucide-react';
import { StorageService } from '../services/storage';

interface PinSettingsModalProps {
  onClose: () => void;
  onLockNow: () => void;
  onPinUpdated: (newConfig: { enabled: boolean; pin: string; autoLock: boolean; email: string; phone: string }) => void;
}

export const PinSettingsModal: React.FC<PinSettingsModalProps> = ({
  onClose,
  onLockNow,
  onPinUpdated
}) => {
  const currentConfig = StorageService.getPin();
  const [enabled, setEnabled] = useState(currentConfig.enabled);
  const [pin, setPin] = useState(currentConfig.pin || '1234');
  const [confirmPin, setConfirmPin] = useState(currentConfig.pin || '1234');
  const [email, setEmail] = useState(currentConfig.email || 'fmdsmb52@gmail.com');
  const [autoLock, setAutoLock] = useState(currentConfig.autoLock);
  const [showPin, setShowPin] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleDigitChange = (val: string) => {
    // Keep numeric only and max 4 digits
    const cleaned = val.replace(/[^0-9]/g, '').slice(0, 4);
    setPin(cleaned);
    setErrorMsg('');
  };

  const handleConfirmDigitChange = (val: string) => {
    const cleaned = val.replace(/[^0-9]/g, '').slice(0, 4);
    setConfirmPin(cleaned);
    setErrorMsg('');
  };

  const handleSave = (andLockNow = false) => {
    if (enabled) {
      if (!email.trim() || !email.includes('@') || !email.includes('.')) {
        setErrorMsg('Valid email is required for secure OTP recovery if you forget your PIN.');
        return;
      }
      if (pin.length !== 4) {
        setErrorMsg('Please enter a 4-digit numeric PIN (e.g. 1234)');
        return;
      }
      if (pin !== confirmPin) {
        setErrorMsg('PIN codes do not match. Please re-enter.');
        return;
      }
    }

    StorageService.setPin(enabled, pin, autoLock, email.trim(), currentConfig.phone || '');
    onPinUpdated({ enabled, pin, autoLock, email: email.trim(), phone: currentConfig.phone || '' });

    if (andLockNow && enabled) {
      onLockNow();
      onClose();
    } else {
      setSuccessMsg('Security PIN preferences updated successfully!');
      setTimeout(() => {
        setSuccessMsg('');
        onClose();
      }, 1000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in">
      <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden my-6">
        {/* Header */}
        <div className="p-5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">App Lock &amp; PIN Security</h3>
              <p className="text-xs text-slate-400">Protect your financial balances and ledger</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4 text-xs">
          {/* Status Banner */}
          <div
            className={`p-3 rounded-2xl border flex items-center justify-between ${
              enabled
                ? 'bg-teal-950/40 border-teal-500/30 text-teal-200'
                : 'bg-slate-950 border-slate-800 text-slate-400'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <ShieldCheck
                className={`w-5 h-5 ${enabled ? 'text-teal-400' : 'text-slate-500'}`}
              />
              <div>
                <p className="font-bold text-white">
                  {enabled ? 'App Lock is ENABLED' : 'App Lock is DISABLED'}
                </p>
                <p className="text-[11px] text-slate-400">
                  {enabled ? 'PIN required to open app' : 'No PIN required'}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                const next = !enabled;
                setEnabled(next);
                if (next && !pin) {
                  setPin('1234');
                  setConfirmPin('1234');
                }
              }}
              className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer ${
                enabled ? 'bg-teal-500' : 'bg-slate-700'
              }`}
            >
              <div
                className={`w-5 h-5 rounded-full bg-white absolute top-0.5 transition-transform ${
                  enabled ? 'right-0.5' : 'left-0.5'
                }`}
              />
            </button>
          </div>

          {/* PIN Setup Input */}
          {enabled && (
            <div className="space-y-3.5 p-4 bg-slate-950 rounded-2xl border border-slate-800">
              {/* Recovery Email for OTP */}
              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Recovery Email (for Forgot PIN / OTP Recovery):
                </label>
                <div className="relative flex items-center">
                  <div className="absolute left-3 text-teal-400">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={e => {
                      setEmail(e.target.value);
                      setErrorMsg('');
                    }}
                    placeholder="e.g. fmdsmb52@gmail.com"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-9 pr-4 py-2.5 text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:border-teal-500 font-bold"
                  />
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  Used to deliver real 6-digit email OTP verification codes via Resend.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1.5">
                  Set 4-Digit Security PIN:
                </label>
                <div className="relative">
                  <input
                    type={showPin ? 'text' : 'password'}
                    maxLength={4}
                    inputMode="numeric"
                    value={pin}
                    onChange={e => handleDigitChange(e.target.value)}
                    placeholder="e.g. 1234"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-center font-mono text-lg tracking-widest text-white focus:outline-none focus:border-teal-500 font-bold"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPin(!showPin)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                  >
                    {showPin ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1.5">
                  Confirm 4-Digit PIN:
                </label>
                <input
                  type={showPin ? 'text' : 'password'}
                  maxLength={4}
                  inputMode="numeric"
                  value={confirmPin}
                  onChange={e => handleConfirmDigitChange(e.target.value)}
                  placeholder="Re-enter 4 digits"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-center font-mono text-lg tracking-widest text-white focus:outline-none focus:border-teal-500 font-bold"
                />
              </div>

              {/* Smart PIN Inactivity Information */}
              <div className="pt-2 border-t border-slate-800/80 text-[11px] space-y-1">
                <span className="font-semibold text-white">Smart PIN Rules Active:</span>
                <p className="text-slate-400 text-[10px] leading-relaxed">
                  • Locks when app is completely closed.<br/>
                  • Locks after 5 minutes of user inactivity (or backgrounding).<br/>
                  • Allows switching apps and returning within 5 minutes without re-entering PIN.
                </p>
              </div>
            </div>
          )}

          {errorMsg && (
            <div className="p-2.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
              <Check className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-2 pt-2">
            {enabled && (
              <button
                type="button"
                onClick={() => handleSave(true)}
                className="w-full py-2.5 bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-400 hover:to-emerald-400 text-slate-950 font-bold text-xs rounded-xl shadow-lg transition cursor-pointer flex items-center justify-center gap-2"
              >
                <Lock className="w-4 h-4" />
                <span>Save &amp; Lock App Now</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => handleSave(false)}
              className="w-full py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs rounded-xl transition cursor-pointer"
            >
              Save Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
