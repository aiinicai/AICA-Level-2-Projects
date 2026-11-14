import React, { useState, useEffect } from 'react';
import {
  Lock,
  Delete,
  ShieldCheck,
  Eye,
  EyeOff,
  KeyRound,
  Mail,
  CheckCircle2,
  AlertCircle,
  X,
  ArrowRight,
  RefreshCw,
  Loader2,
  Clock,
  ShieldAlert
} from 'lucide-react';
import { AuthService, AuthStatusResponse } from '../services/authService';

interface PinLockScreenProps {
  correctPin: string;
  recoveryEmail?: string;
  recoveryPhone?: string;
  onUnlock: () => void;
  onDisablePin?: () => void;
  onResetPin?: (newPin: string, email?: string) => void;
}

export const PinLockScreen: React.FC<PinLockScreenProps> = ({
  correctPin,
  recoveryEmail = 'fmdsmb52@gmail.com',
  onUnlock,
  onDisablePin,
  onResetPin
}) => {
  const [enteredPin, setEnteredPin] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Forgot PIN / Resend Email OTP Recovery State
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [otpStep, setOtpStep] = useState<'request' | 'verify' | 'new_pin'>('request');
  const [emailInput, setEmailInput] = useState(recoveryEmail || 'fmdsmb52@gmail.com');
  const [enteredOtp, setEnteredOtp] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [otpError, setOtpError] = useState('');
  const [isSendingOtp, setIsSendingOtp] = useState(false);
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [otpExpiresInSeconds, setOtpExpiresInSeconds] = useState(300); // 5 minutes
  const [authStatus, setAuthStatus] = useState<AuthStatusResponse | null>(null);

  // New PIN setup in recovery flow
  const [newPin, setNewPin] = useState('');
  const [confirmNewPin, setConfirmNewPin] = useState('');
  const [showNewPin, setShowNewPin] = useState(false);

  // Check Resend configuration status on load
  useEffect(() => {
    AuthService.getStatus().then(status => {
      setAuthStatus(status);
    });
  }, []);

  // 60-second Resend cooldown timer
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (resendCooldown > 0) {
      timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [resendCooldown]);

  // 5-minute (300-second) OTP expiration countdown timer
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (otpStep === 'verify' && otpExpiresInSeconds > 0) {
      timer = setTimeout(() => setOtpExpiresInSeconds(otpExpiresInSeconds - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [otpStep, otpExpiresInSeconds]);

  // Physical keyboard support for numeric entry and backspace
  useEffect(() => {
    if (showForgotModal) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (/^[0-9]$/.test(e.key)) {
        handleDigit(e.key);
      } else if (e.key === 'Backspace') {
        handleDelete();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enteredPin, correctPin, showForgotModal]);

  const handleDigit = (digit: string) => {
    if (enteredPin.length >= 4) return;
    const nextPin = enteredPin + digit;
    setEnteredPin(nextPin);
    setErrorMsg('');

    if (nextPin.length === 4) {
      if (nextPin === correctPin) {
        setTimeout(() => {
          onUnlock();
        }, 150);
      } else {
        setTimeout(() => {
          setErrorMsg('Incorrect PIN. Please try again.');
          setEnteredPin('');
        }, 200);
      }
    }
  };

  const handleDelete = () => {
    setEnteredPin(prev => prev.slice(0, -1));
    setErrorMsg('');
  };

  const maskEmailAddress = (email: string) => {
    if (!email || !email.includes('@')) return 'fmd***@gmail.com';
    const [user, domain] = email.split('@');
    if (user.length <= 2) return `${user}***@${domain}`;
    return `${user.slice(0, 3)}***@${domain}`;
  };

  const formatCountdown = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSendOtp = async () => {
    const targetEmail = (emailInput || recoveryEmail || 'fmdsmb52@gmail.com').trim();
    if (!targetEmail || !targetEmail.includes('@') || !targetEmail.includes('.')) {
      setOtpError('Please enter a valid email address.');
      return;
    }

    setIsSendingOtp(true);
    setOtpError('');

    const res = await AuthService.sendOtp(targetEmail);
    setIsSendingOtp(false);

    if (!res.success) {
      setOtpError(res.error || 'Failed to send OTP verification email.');
      return;
    }

    setOtpStep('verify');
    setResendCooldown(60); // 60s cooldown before allowed to click Resend
    setOtpExpiresInSeconds(300); // 5-minute validity window
    setEnteredOtp('');
    setOtpError('');
  };

  const handleVerifyOtp = async () => {
    if (otpExpiresInSeconds <= 0) {
      setOtpError('This verification code has expired (5-minute limit). Please request a new code.');
      return;
    }

    if (enteredOtp.length !== 6) {
      setOtpError('Please enter the full 6-digit numeric verification code.');
      return;
    }

    const targetEmail = (emailInput || recoveryEmail || 'fmdsmb52@gmail.com').trim();
    setIsVerifyingOtp(true);
    setOtpError('');

    const res = await AuthService.verifyOtp(targetEmail, enteredOtp);
    setIsVerifyingOtp(false);

    if (!res.success) {
      setOtpError(res.error || 'Invalid OTP code. Please check your email and try again.');
      return;
    }

    setResetToken(res.resetToken || '');
    setOtpStep('new_pin');
    setOtpError('');
  };

  const handleSaveNewPinAndUnlock = async () => {
    if (newPin.length !== 4) {
      setOtpError('Please enter a 4-digit numeric PIN.');
      return;
    }
    if (newPin !== confirmNewPin) {
      setOtpError('New PIN codes do not match. Please re-enter.');
      return;
    }

    const targetEmail = (emailInput || recoveryEmail || 'fmdsmb52@gmail.com').trim();
    setIsVerifyingOtp(true);
    setOtpError('');

    const res = await AuthService.resetPin(targetEmail, resetToken, newPin);
    setIsVerifyingOtp(false);

    if (!res.success) {
      setOtpError(res.error || 'Failed to update PIN on server.');
      return;
    }

    if (onResetPin) {
      onResetPin(newPin, targetEmail);
    }
    setShowForgotModal(false);
    onUnlock();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950 p-4 select-none">
      <div className="w-full max-w-sm flex flex-col items-center">
        {/* Brand Icon & Title */}
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-teal-500/20 to-sky-500/20 border border-teal-500/30 flex items-center justify-center mb-4 text-teal-400 shadow-lg shadow-teal-950/40">
          <Lock className="w-8 h-8" />
        </div>

        <h2 className="text-xl font-bold text-white tracking-tight">DirhamTrack</h2>
        <p className="text-xs text-slate-400 mt-1 mb-6">Enter your 4-digit security PIN to unlock</p>

        {/* PIN Dots */}
        <div className="flex items-center gap-4 mb-6">
          {[0, 1, 2, 3].map(i => {
            const isFilled = i < enteredPin.length;
            return (
              <div
                key={i}
                className={`w-4 h-4 rounded-full transition-all duration-200 ${
                  isFilled
                    ? 'bg-teal-400 scale-110 shadow-lg shadow-teal-500/50'
                    : 'bg-slate-800 border border-slate-700'
                }`}
              />
            );
          })}
        </div>

        {errorMsg && (
          <p className="text-xs font-semibold text-rose-400 mb-4 animate-shake text-center">
            {errorMsg}
          </p>
        )}

        {/* Secure Keypad - Pure numeric, Biometric completely removed */}
        <div className="grid grid-cols-3 gap-3.5 w-full max-w-[280px] mb-5">
          {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map(num => (
            <button
              key={num}
              type="button"
              onClick={() => handleDigit(num)}
              className="h-16 rounded-2xl bg-slate-900 border border-slate-800/80 hover:bg-slate-800 text-xl font-semibold text-white active:scale-95 transition-transform flex items-center justify-center cursor-pointer shadow-sm"
            >
              {num}
            </button>
          ))}

          {/* Slot 10: Clear button */}
          <button
            type="button"
            onClick={() => setEnteredPin('')}
            disabled={enteredPin.length === 0}
            className="h-16 rounded-2xl bg-slate-900 border border-slate-800/80 hover:bg-slate-800 text-xs font-semibold text-slate-400 hover:text-white disabled:opacity-20 active:scale-95 transition-transform flex items-center justify-center cursor-pointer shadow-sm"
            title="Clear entered digits"
          >
            Clear
          </button>

          {/* Slot 11: Digit 0 */}
          <button
            type="button"
            onClick={() => handleDigit('0')}
            className="h-16 rounded-2xl bg-slate-900 border border-slate-800/80 hover:bg-slate-800 text-xl font-semibold text-white active:scale-95 transition-transform flex items-center justify-center cursor-pointer shadow-sm"
          >
            0
          </button>

          {/* Slot 12: Delete / Backspace */}
          <button
            type="button"
            onClick={handleDelete}
            className="h-16 rounded-2xl bg-slate-900 border border-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-white active:scale-95 transition-transform flex items-center justify-center cursor-pointer shadow-sm"
            title="Delete last digit"
          >
            <Delete className="w-6 h-6" />
          </button>
        </div>

        {/* Forgot PIN / Resend Email OTP Trigger */}
        <div className="mb-4">
          <button
            type="button"
            onClick={() => {
              setEmailInput(recoveryEmail || 'fmdsmb52@gmail.com');
              setOtpStep('request');
              setOtpError('');
              setEnteredOtp('');
              setShowForgotModal(true);
            }}
            className="text-xs text-teal-400 hover:text-teal-300 font-semibold flex items-center gap-1.5 transition cursor-pointer"
          >
            <KeyRound className="w-3.5 h-3.5" />
            <span>Forgot PIN? Recover via Email OTP</span>
          </button>
        </div>

        {/* Security Status Badge */}
        <div className="w-full bg-slate-900/80 border border-slate-800 rounded-xl p-3 text-center">
          <div className="flex items-center justify-center gap-1.5 text-xs text-teal-400 font-medium">
            <ShieldCheck className="w-4 h-4" />
            <span>App Protected with 4-Digit PIN</span>
          </div>
          {onDisablePin && (
            <div className="mt-1 text-center">
              <button
                type="button"
                onClick={onDisablePin}
                className="text-[11px] text-slate-400 hover:text-rose-400 transition cursor-pointer"
              >
                Turn Off Lock
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Forgot PIN & Resend Email OTP Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-fadeIn">
          <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center">
                  <Mail className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Reset PIN via Email OTP</h3>
                  <p className="text-[11px] text-slate-400">Powered by Resend Email API</p>
                </div>
              </div>
              <button
                onClick={() => setShowForgotModal(false)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Step 1: Request OTP */}
            {otpStep === 'request' && (
              <div className="space-y-4 text-xs">
                <p className="text-slate-300 leading-relaxed">
                  We will send a secure 6-digit verification code to your registered email address using the Resend Email API:
                </p>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-2 font-mono text-sm font-bold text-white">
                  <Mail className="w-4 h-4 text-teal-400 shrink-0" />
                  <span className="truncate">{maskEmailAddress(emailInput || recoveryEmail)}</span>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1 text-[11px]">
                    Verify or update your recovery email address:
                  </label>
                  <input
                    type="email"
                    value={emailInput}
                    onChange={e => {
                      setEmailInput(e.target.value);
                      setOtpError('');
                    }}
                    placeholder="e.g. fmdsmb52@gmail.com"
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-teal-500 font-bold"
                  />
                </div>

                {authStatus && !authStatus.resendConfigured && (
                  <div className="p-2.5 rounded-xl bg-amber-950/40 border border-amber-500/30 text-amber-300 text-[11px] leading-relaxed flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <strong className="font-semibold block text-amber-200">Resend API Key Notice:</strong>
                      Add <code className="bg-slate-900 px-1 py-0.5 rounded text-amber-200 font-mono">RESEND_API_KEY</code> to your environment variables to deliver actual emails.
                    </div>
                  </div>
                )}

                {otpError && (
                  <div className="p-2.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
                    <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{otpError}</span>
                  </div>
                )}

                <button
                  type="button"
                  disabled={isSendingOtp}
                  onClick={handleSendOtp}
                  className="w-full py-2.5 bg-teal-500 hover:bg-teal-400 disabled:opacity-60 text-slate-950 font-bold text-xs rounded-xl transition shadow flex items-center justify-center gap-2 cursor-pointer"
                >
                  {isSendingOtp ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Sending Email via Resend...</span>
                    </>
                  ) : (
                    <>
                      <span>Send 6-Digit Email OTP</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Step 2: Verify OTP */}
            {otpStep === 'verify' && (
              <div className="space-y-4 text-xs">
                <div className="text-center">
                  <p className="text-slate-300 leading-relaxed">
                    Enter the 6-digit verification code sent to{' '}
                    <strong className="text-white">{maskEmailAddress(emailInput || recoveryEmail)}</strong>:
                  </p>
                  <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-950 border border-slate-800 text-[11px] text-amber-400 font-mono">
                    <Clock className="w-3.5 h-3.5" />
                    <span>
                      {otpExpiresInSeconds > 0
                        ? `Valid for ${formatCountdown(otpExpiresInSeconds)}`
                        : 'Code expired (5-min limit)'}
                    </span>
                  </div>
                </div>

                <div>
                  <input
                    type="text"
                    maxLength={6}
                    inputMode="numeric"
                    value={enteredOtp}
                    onChange={e => {
                      setEnteredOtp(e.target.value.replace(/[^0-9]/g, ''));
                      setOtpError('');
                    }}
                    placeholder="••••••"
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-center font-mono text-2xl tracking-[0.3em] text-teal-400 font-bold focus:outline-none focus:border-teal-500"
                  />
                </div>

                {otpError && (
                  <div className="p-2.5 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2">
                    <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{otpError}</span>
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={resendCooldown > 0 || isSendingOtp}
                    onClick={handleSendOtp}
                    className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 text-xs font-semibold rounded-xl transition cursor-pointer"
                  >
                    {isSendingOtp
                      ? 'Sending...'
                      : resendCooldown > 0
                      ? `Resend OTP (${resendCooldown}s)`
                      : 'Resend OTP'}
                  </button>
                  <button
                    type="button"
                    onClick={handleVerifyOtp}
                    disabled={enteredOtp.length !== 6 || isVerifyingOtp || otpExpiresInSeconds <= 0}
                    className="flex-1 py-2.5 bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 text-xs font-bold rounded-xl transition shadow flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    {isVerifyingOtp ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Verifying...</span>
                      </>
                    ) : (
                      <span>Verify Code</span>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Set New 4-Digit PIN */}
            {otpStep === 'new_pin' && (
              <div className="space-y-3.5 text-xs">
                <div className="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                  <span>Email verified! Enter your new 4-digit PIN below.</span>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">
                    Enter New 4-Digit PIN:
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPin ? 'text' : 'password'}
                      maxLength={4}
                      inputMode="numeric"
                      value={newPin}
                      onChange={e => {
                        setNewPin(e.target.value.replace(/[^0-9]/g, ''));
                        setOtpError('');
                      }}
                      placeholder="e.g. 5678"
                      className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-center font-mono text-lg tracking-widest text-white font-bold focus:outline-none focus:border-teal-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPin(!showNewPin)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white cursor-pointer"
                    >
                      {showNewPin ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">
                    Confirm New PIN:
                  </label>
                  <input
                    type={showNewPin ? 'text' : 'password'}
                    maxLength={4}
                    inputMode="numeric"
                    value={confirmNewPin}
                    onChange={e => {
                      setConfirmNewPin(e.target.value.replace(/[^0-9]/g, ''));
                      setOtpError('');
                    }}
                    placeholder="Re-enter 4 digits"
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-center font-mono text-lg tracking-widest text-white font-bold focus:outline-none focus:border-teal-500"
                  />
                </div>

                {otpError && (
                  <p className="text-rose-400 text-xs font-semibold">{otpError}</p>
                )}

                <div className="pt-2">
                  <button
                    type="button"
                    disabled={isVerifyingOtp}
                    onClick={handleSaveNewPinAndUnlock}
                    className="w-full py-2.5 bg-teal-500 hover:bg-teal-400 disabled:opacity-60 text-slate-950 font-bold text-xs rounded-xl transition shadow flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    {isVerifyingOtp ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Updating PIN...</span>
                      </>
                    ) : (
                      <span>Save New PIN &amp; Unlock</span>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
