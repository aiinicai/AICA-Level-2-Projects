import React, { useState, useEffect } from 'react';
import {
  Lock,
  Delete,
  KeyRound,
  AlertCircle,
  ShieldAlert,
  RotateCcw,
  ShieldCheck,
  Trash2,
  CheckCircle2,
} from 'lucide-react';
import { verifyPin } from '../utils/security';
import { verifyRecoveryKey } from '../utils/crypto';
import { LogoSvg } from './Navigation';

interface Props {
  storedPinHash: string;
  pinSalt?: string;
  recoveryKeyHash?: string;
  recoveryKeySalt?: string;
  onUnlock: () => void;
  onResetWithRecoveryKey: (newPin: string) => void;
  onFactoryWipe: () => void;
}

export const PinLockScreen: React.FC<Props> = ({
  storedPinHash,
  pinSalt,
  recoveryKeyHash,
  recoveryKeySalt,
  onUnlock,
  onResetWithRecoveryKey,
  onFactoryWipe,
}) => {
  const [pin, setPin] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [failedAttempts, setFailedAttempts] = useState<number>(0);
  const [lockoutSeconds, setLockoutSeconds] = useState<number>(0);

  // Recovery modal state
  const [showRecoveryModal, setShowRecoveryModal] = useState<boolean>(false);
  const [recoveryCode, setRecoveryCode] = useState<string>('');
  const [recoveryNewPin, setRecoveryNewPin] = useState<string>('');
  const [recoveryConfirmPin, setRecoveryConfirmPin] = useState<string>('');
  const [recoveryError, setRecoveryError] = useState<string>('');
  const [recoverySuccess, setRecoverySuccess] = useState<boolean>(false);

  // Factory wipe confirmation modal state
  const [showWipeModal, setShowWipeModal] = useState<boolean>(false);
  const [wipeConfirmText, setWipeConfirmText] = useState<string>('');

  // Lockout countdown timer
  useEffect(() => {
    if (lockoutSeconds <= 0) return;
    const timer = setInterval(() => {
      setLockoutSeconds((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [lockoutSeconds]);

  const handleDigit = (digit: string) => {
    if (lockoutSeconds > 0) return;
    if (pin.length < 4) {
      const next = pin + digit;
      setPin(next);
      setError('');
      if (next.length === 4) {
        verify(next);
      }
    }
  };

  const handleDelete = () => {
    if (lockoutSeconds > 0) return;
    setPin((prev) => prev.slice(0, -1));
    setError('');
  };

  const handleClear = () => {
    if (lockoutSeconds > 0) return;
    setPin('');
    setError('');
  };

  const verify = async (code: string) => {
    setIsVerifying(true);
    const valid = await verifyPin(code, storedPinHash, pinSalt);
    setIsVerifying(false);

    if (valid) {
      onUnlock();
    } else {
      const nextAttempts = failedAttempts + 1;
      setFailedAttempts(nextAttempts);
      if (nextAttempts >= 5) {
        setLockoutSeconds(30);
        setError('Too many incorrect attempts. Wait 30 seconds.');
      } else {
        setError(`Incorrect 4-digit PIN (${5 - nextAttempts} attempts remaining)`);
      }
      setTimeout(() => setPin(''), 500);
    }
  };

  // Physical keyboard support
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (showRecoveryModal || showWipeModal) return;
      if (/^[0-9]$/.test(e.key)) {
        handleDigit(e.key);
      } else if (e.key === 'Backspace') {
        handleDelete();
      } else if (e.key === 'Escape') {
        handleClear();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [pin, lockoutSeconds, showRecoveryModal, showWipeModal]);

  // Handle Recovery Key Submission
  const handleVerifyRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setRecoveryError('');

    if (!recoveryKeyHash || !recoveryKeySalt) {
      setRecoveryError(
        'No emergency recovery key is on record. If you forgot your PIN, you can erase local storage to start fresh.'
      );
      return;
    }

    const isValid = await verifyRecoveryKey(
      recoveryCode,
      recoveryKeySalt,
      recoveryKeyHash
    );

    if (!isValid) {
      setRecoveryError('Invalid Emergency Recovery Key. Please double check characters.');
      return;
    }

    if (!/^\d{4}$/.test(recoveryNewPin)) {
      setRecoveryError('New PIN must be exactly 4 digits.');
      return;
    }

    if (recoveryNewPin !== recoveryConfirmPin) {
      setRecoveryError('New PINs do not match.');
      return;
    }

    setRecoverySuccess(true);
    setTimeout(() => {
      onResetWithRecoveryKey(recoveryNewPin);
      setShowRecoveryModal(false);
    }, 1200);
  };

  const handleExecuteWipe = () => {
    if (wipeConfirmText.trim().toUpperCase() === 'DELETE') {
      setShowWipeModal(false);
      onFactoryWipe();
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#0F2A47] text-white flex flex-col items-center justify-center p-4 select-none safe-top safe-bottom">
      <div className="w-full max-w-xs flex flex-col items-center space-y-6">
        <div className="flex flex-col items-center space-y-2">
          <LogoSvg className="w-14 h-14" />
          <h1 className="text-xl font-bold tracking-tight">Paisa Pal Locked</h1>
          <p className="text-xs text-[#9FB0C6] flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-[#3CB7C2]" />
            <span>Enter your 4-digit security PIN</span>
          </p>
        </div>

        {/* 4 PIN Dots */}
        <div className="flex items-center gap-4 py-2">
          {[0, 1, 2, 3].map((idx) => {
            const isFilled = pin.length > idx;
            return (
              <div
                key={idx}
                className={`w-4 h-4 rounded-full transition-all duration-200 border-2 ${
                  isFilled
                    ? 'bg-[#3CB7C2] border-[#3CB7C2] scale-110 shadow-sm'
                    : 'border-[#9FB0C6]/40 bg-transparent'
                }`}
              />
            );
          })}
        </div>

        {lockoutSeconds > 0 ? (
          <div className="text-xs text-amber-300 bg-amber-950/70 border border-amber-600/50 px-3 py-2 rounded-xl flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Security cooldown: wait {lockoutSeconds}s before retry</span>
          </div>
        ) : error ? (
          <div className="text-xs text-rose-300 bg-rose-950/60 px-3 py-1.5 rounded-lg flex items-center gap-1.5 animate-shake">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        {/* Number Keypad with touch targets >= 44px */}
        <div className="grid grid-cols-3 gap-3 w-full max-w-[260px]">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
            <button
              key={num}
              onClick={() => handleDigit(String(num))}
              disabled={isVerifying || lockoutSeconds > 0}
              className="w-16 h-16 mx-auto rounded-full bg-[#1B406A]/80 hover:bg-[#1B406A] active:scale-90 text-2xl font-semibold flex items-center justify-center transition shadow-xs border border-[#254F80]/60 disabled:opacity-40"
            >
              {num}
            </button>
          ))}

          <button
            onClick={handleClear}
            disabled={lockoutSeconds > 0}
            className="w-16 h-16 mx-auto rounded-full text-xs font-semibold text-[#9FB0C6] hover:text-white flex items-center justify-center transition active:scale-95 disabled:opacity-40"
          >
            Clear
          </button>

          <button
            onClick={() => handleDigit('0')}
            disabled={isVerifying || lockoutSeconds > 0}
            className="w-16 h-16 mx-auto rounded-full bg-[#1B406A]/80 hover:bg-[#1B406A] active:scale-90 text-2xl font-semibold flex items-center justify-center transition shadow-xs border border-[#254F80]/60 disabled:opacity-40"
          >
            0
          </button>

          <button
            onClick={handleDelete}
            disabled={lockoutSeconds > 0}
            className="w-16 h-16 mx-auto rounded-full text-[#9FB0C6] hover:text-white flex items-center justify-center transition active:scale-95 disabled:opacity-40"
            aria-label="Delete last digit"
          >
            <Delete className="w-6 h-6" />
          </button>
        </div>

        {/* Recovery Options - Secure Authentication Required */}
        <div className="flex flex-col items-center gap-2 pt-2">
          <button
            onClick={() => {
              setRecoveryError('');
              setShowRecoveryModal(true);
            }}
            className="text-xs text-[#9FB0C6] hover:text-[#3CB7C2] flex items-center gap-1.5 transition underline underline-offset-4"
          >
            <KeyRound className="w-3.5 h-3.5" />
            <span>Forgot PIN? Use Emergency Recovery Key</span>
          </button>

          <button
            onClick={() => setShowWipeModal(true)}
            className="text-[11px] text-[#6F7E92] hover:text-rose-400 transition pt-1"
          >
            Lost everything? Reset vault & erase data
          </button>
        </div>
      </div>

      {/* Emergency Recovery Modal */}
      {showRecoveryModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-60 flex items-center justify-center bg-black/80 backdrop-blur-xs p-4"
        >
          <div className="bg-[#0A1626] border border-[#254F80] rounded-2xl max-w-md w-full p-6 text-white space-y-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#3CB7C2]/20 text-[#3CB7C2] flex items-center justify-center flex-shrink-0">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-semibold text-base">PIN Recovery</h3>
                <p className="text-xs text-[#9FB0C6]">
                  Enter your 16-character Emergency Recovery Key
                </p>
              </div>
            </div>

            {recoverySuccess ? (
              <div className="p-4 bg-emerald-950/60 border border-emerald-500/40 rounded-xl text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                <p className="text-sm font-semibold text-emerald-300">
                  Recovery Key Verified!
                </p>
                <p className="text-xs text-[#C9D6E6]">
                  Your new PIN has been set and vault is unlocked.
                </p>
              </div>
            ) : (
              <form onSubmit={handleVerifyRecovery} className="space-y-4 text-xs">
                <p className="text-[#C9D6E6] leading-relaxed">
                  To protect your financial vault, Paisa Pal never exposes records without authentication. Enter the 16-character Emergency Recovery Key provided when you set up security.
                </p>

                <div>
                  <label className="block text-[11px] font-semibold text-[#9FB0C6] mb-1">
                    Emergency Recovery Key (XXXX-XXXX-XXXX-XXXX):
                  </label>
                  <input
                    type="text"
                    required
                    value={recoveryCode}
                    onChange={(e) => setRecoveryCode(e.target.value.toUpperCase())}
                    placeholder="e.g. 4B7K-9XM2-P5R8-T3WY"
                    className="w-full tracking-widest font-mono uppercase bg-[#142338] border border-[#254F80] rounded-xl px-3 py-2 text-sm text-center text-white focus:outline-2 focus:outline-[#3CB7C2]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="block text-[11px] font-semibold text-[#9FB0C6] mb-1">
                      New 4-Digit PIN:
                    </label>
                    <input
                      type="password"
                      inputMode="numeric"
                      maxLength={4}
                      required
                      value={recoveryNewPin}
                      onChange={(e) =>
                        setRecoveryNewPin(e.target.value.replace(/\D/g, '').slice(0, 4))
                      }
                      placeholder="••••"
                      className="w-full text-center tracking-widest text-lg font-bold bg-[#142338] border border-[#254F80] rounded-xl py-2 focus:outline-2 focus:outline-[#3CB7C2]"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-[#9FB0C6] mb-1">
                      Confirm New PIN:
                    </label>
                    <input
                      type="password"
                      inputMode="numeric"
                      maxLength={4}
                      required
                      value={recoveryConfirmPin}
                      onChange={(e) =>
                        setRecoveryConfirmPin(e.target.value.replace(/\D/g, '').slice(0, 4))
                      }
                      placeholder="••••"
                      className="w-full text-center tracking-widest text-lg font-bold bg-[#142338] border border-[#254F80] rounded-xl py-2 focus:outline-2 focus:outline-[#3CB7C2]"
                    />
                  </div>
                </div>

                {recoveryError && (
                  <div className="p-2.5 rounded-lg bg-rose-950/70 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{recoveryError}</span>
                  </div>
                )}

                <div className="flex gap-2 pt-2">
                  <button
                    type="submit"
                    className="flex-1 py-2.5 px-4 rounded-xl bg-[#0E7C86] hover:bg-[#128e9a] text-white text-xs font-semibold transition"
                  >
                    Verify & Reset PIN
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowRecoveryModal(false)}
                    className="py-2.5 px-4 rounded-xl border border-[#254F80] hover:bg-[#1B406A] text-xs font-medium text-[#C9D6E6] transition"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Factory Wipe Confirmation Modal */}
      {showWipeModal && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-60 flex items-center justify-center bg-black/85 backdrop-blur-xs p-4"
        >
          <div className="bg-[#120808] border border-rose-900/60 rounded-2xl max-w-sm w-full p-6 text-white space-y-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/20 text-rose-400 flex items-center justify-center flex-shrink-0">
                <Trash2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-semibold text-base text-rose-300">
                  Erase All Data & Reset App?
                </h3>
                <p className="text-xs text-rose-400/80">Permanent data deletion</p>
              </div>
            </div>

            <p className="text-xs text-rose-200/90 leading-relaxed">
              If you have lost both your PIN and your Emergency Recovery Key, your encrypted records cannot be decrypted. To prevent unauthorized access, existing data will be permanently wiped.
            </p>

            <div className="space-y-1.5 pt-1">
              <label className="block text-[11px] font-semibold text-rose-300">
                Type <strong>DELETE</strong> to confirm:
              </label>
              <input
                type="text"
                value={wipeConfirmText}
                onChange={(e) => setWipeConfirmText(e.target.value)}
                placeholder="DELETE"
                className="w-full uppercase font-mono tracking-wider bg-rose-950/60 border border-rose-800 rounded-xl px-3 py-2 text-sm text-center text-rose-200 focus:outline-2 focus:outline-rose-500"
              />
            </div>

            <div className="flex flex-col gap-2 pt-2">
              <button
                type="button"
                disabled={wipeConfirmText.trim().toUpperCase() !== 'DELETE'}
                onClick={handleExecuteWipe}
                className="w-full py-2.5 px-4 rounded-xl bg-rose-600 hover:bg-rose-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold transition"
              >
                Permanently Erase All Data
              </button>
              <button
                type="button"
                onClick={() => {
                  setWipeConfirmText('');
                  setShowWipeModal(false);
                }}
                className="w-full py-2.5 px-4 rounded-xl border border-rose-900/60 hover:bg-rose-950/40 text-xs font-medium text-slate-300 transition"
              >
                Cancel & Return
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
