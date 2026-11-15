import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { UserRole } from '../types';
import {
  ShieldCheck,
  Users,
  Lock,
  User,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  KeyRound,
  Mail,
  X
} from 'lucide-react';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  isMandatoryLock?: boolean;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose, isMandatoryLock = false }) => {
  const { login, requestResetEmail, verifyAndResetPassword, verifyGoogleAndResetPassword } = useApp();

  // 2 Logins: Admin and Staff with Fixed User IDs ('ADMIN' and 'STAFF')
  const [selectedRole, setSelectedRole] = useState<UserRole>('admin');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Password reset state strictly tied to rishugarg006@gmail.com for BOTH Admin & Staff
  const [isResetMode, setIsResetMode] = useState(false);
  const [resetRole, setResetRole] = useState<UserRole>('admin');
  const [resetMethod, setResetMethod] = useState<'email_otp' | 'google_verify'>('email_otp');
  const [resetStep, setResetStep] = useState<'request' | 'verify'>('request');
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  if (!isOpen) return null;

  const currentFixedUserId = selectedRole === 'admin' ? 'ADMIN' : 'STAFF';
  const currentResetUserId = resetRole === 'admin' ? 'ADMIN' : 'STAFF';

  const handleRoleSwitch = (role: UserRole) => {
    setSelectedRole(role);
    setPassword('');
    setErrorMsg('');
    setSuccessMsg('');
  };

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const res = login(selectedRole, currentFixedUserId, password);
    if (res.success) {
      setPassword('');
      setSuccessMsg(res.message);
      setTimeout(() => {
        onClose();
      }, 250);
    } else {
      setErrorMsg(res.message);
    }
  };

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');
    setIsSending(true);

    try {
      const res = await requestResetEmail('rishugarg006@gmail.com', resetRole);
      if (res.success) {
        setOtpCode('');
        setResetStep('verify');
        setSuccessMsg(res.message);
      } else {
        setErrorMsg(res.message);
      }
    } finally {
      setIsSending(false);
    }
  };

  const handleVerifyAndReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!newPassword.trim()) {
      setErrorMsg('Please enter a new password');
      return;
    }
    if (newPassword !== confirmPassword) {
      setErrorMsg('Passwords do not match. Please confirm your new password.');
      return;
    }
    if (newPassword.length < 4) {
      setErrorMsg('Password must be at least 4 characters.');
      return;
    }

    setIsVerifying(true);
    try {
      const res = await verifyAndResetPassword(resetRole, otpCode, newPassword);
      if (res.success) {
        setSuccessMsg(res.message);
        setTimeout(() => {
          setIsResetMode(false);
          setResetStep('request');
          setSelectedRole(resetRole);
          setPassword('');
          setOtpCode('');
          setNewPassword('');
          setConfirmPassword('');
          setSuccessMsg('');
        }, 1400);
      } else {
        setErrorMsg(res.message);
      }
    } finally {
      setIsVerifying(false);
    }
  };

  const handleGoogleVerifiedReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!newPassword.trim()) {
      setErrorMsg('Please enter a new password');
      return;
    }
    if (newPassword !== confirmPassword) {
      setErrorMsg('Passwords do not match. Please confirm your new password.');
      return;
    }
    if (newPassword.length < 4) {
      setErrorMsg('Password must be at least 4 characters.');
      return;
    }

    setIsVerifying(true);
    try {
      const res = await verifyGoogleAndResetPassword(resetRole, newPassword);
      if (res.success) {
        setSuccessMsg(res.message);
        setTimeout(() => {
          setIsResetMode(false);
          setResetStep('request');
          setSelectedRole(resetRole);
          setPassword('');
          setNewPassword('');
          setConfirmPassword('');
          setSuccessMsg('');
        }, 1400);
      } else {
        setErrorMsg(res.message);
      }
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center p-4 animate-in fade-in duration-200 ${
        isMandatoryLock
          ? 'bg-gradient-to-br from-amber-100 via-yellow-50 to-amber-200/70'
          : 'bg-slate-900/60 backdrop-blur-xs'
      }`}
    >
      {isMandatoryLock && (
        <div className="mb-4 text-center">
          <h1 className="text-lg sm:text-xl font-black tracking-tight text-amber-950">
            RISHU GARG &amp; ASSOCIATES
          </h1>
          <p className="text-xs font-semibold text-amber-800">
            Chartered Accountants • Office Super App
          </p>
        </div>
      )}
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl border border-amber-200/80 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-6 py-4 text-white flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <span className="p-2 rounded-xl bg-white/10 backdrop-blur-xs">
              <ShieldCheck className="w-5 h-5 text-amber-200" />
            </span>
            <div>
              <h2 className="text-base font-black leading-tight text-white">CA Office Portal Login</h2>
              <p className="text-xs text-amber-200 font-medium">Bishnandi Bazaar, Jaitu</p>
            </div>
          </div>
          {!isMandatoryLock && (
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="p-6">
          {!isResetMode ? (
            <>
              {/* 2 Logins: Admin and Staff Role Switcher */}
              <div className="grid grid-cols-2 gap-2 p-1 bg-amber-50 rounded-xl mb-5 border border-amber-200">
                <button
                  type="button"
                  onClick={() => handleRoleSwitch('admin')}
                  className={`flex items-center justify-center space-x-2 py-2 rounded-lg text-xs font-bold transition-all ${
                    selectedRole === 'admin'
                      ? 'bg-amber-700 text-white shadow-xs'
                      : 'text-amber-900 hover:text-amber-950 hover:bg-amber-100/60'
                  }`}
                >
                  <ShieldCheck className={`w-3.5 h-3.5 ${selectedRole === 'admin' ? 'text-amber-200' : 'text-amber-700'}`} />
                  <span>ADMIN</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleRoleSwitch('staff')}
                  className={`flex items-center justify-center space-x-2 py-2 rounded-lg text-xs font-bold transition-all ${
                    selectedRole === 'staff'
                      ? 'bg-amber-700 text-white shadow-xs'
                      : 'text-amber-900 hover:text-amber-950 hover:bg-amber-100/60'
                  }`}
                >
                  <Users className={`w-3.5 h-3.5 ${selectedRole === 'staff' ? 'text-amber-200' : 'text-amber-700'}`} />
                  <span>STAFF</span>
                </button>
              </div>

              {/* Login Form: Strictly 3 Displays (USER ID Fixed, Password Option, Reset Option) */}
              <form onSubmit={handleLoginSubmit} className="space-y-4">
                {/* 1. USER ID (Fixed) */}
                <div>
                  <label className="block text-xs font-bold text-amber-950 mb-1">
                    USER ID
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-amber-700 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      value={currentFixedUserId}
                      readOnly
                      className="w-full pl-9 pr-3 py-2 bg-amber-50/60 border border-amber-300 rounded-xl text-xs font-black text-amber-950 select-all cursor-not-allowed focus:outline-none tracking-wider"
                    />
                  </div>
                </div>

                {/* 2. Password Option + 3. Reset Option */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-bold text-amber-950">Password</label>
                    <button
                      type="button"
                      onClick={() => {
                        setResetRole(selectedRole);
                        setIsResetMode(true);
                        setResetStep('request');
                        setErrorMsg('');
                        setSuccessMsg('');
                        setOtpCode('');
                        setNewPassword('');
                        setConfirmPassword('');
                      }}
                      className="text-xs text-amber-800 hover:text-amber-950 font-bold hover:underline cursor-pointer"
                    >
                      Reset Option
                    </button>
                  </div>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-amber-700 absolute left-3 top-2.5" />
                    <input
                      type="password"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="Enter password"
                      className="w-full pl-9 pr-3 py-2 bg-white border border-amber-300 rounded-xl text-xs text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-500 font-medium"
                      required
                    />
                  </div>
                </div>

                {errorMsg && (
                  <div className="flex items-center space-x-2 text-xs text-red-700 bg-red-50 p-2.5 rounded-lg border border-red-200">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{errorMsg}</span>
                  </div>
                )}

                {successMsg && (
                  <div className="flex items-center space-x-2 text-xs text-emerald-800 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>{successMsg}</span>
                  </div>
                )}

                <button
                  type="submit"
                  className="w-full py-2.5 px-4 bg-gradient-to-r from-amber-700 to-yellow-700 hover:from-amber-800 hover:to-yellow-800 text-white font-bold rounded-xl shadow-xs transition-all text-xs flex items-center justify-center space-x-1.5 active:scale-98 cursor-pointer"
                >
                  <span>Sign In as {currentFixedUserId}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </form>
            </>
          ) : (
            /* Reset Password Option Flow strictly via rishugarg006@gmail.com (No OTP shown on screen) */
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-amber-200 pb-2.5">
                <div className="flex items-center space-x-2">
                  <KeyRound className="w-4 h-4 text-amber-800" />
                  <h3 className="font-bold text-amber-950 text-xs">
                    Reset Password Option ({currentResetUserId})
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setIsResetMode(false);
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  className="text-xs text-amber-800 hover:text-amber-950 font-semibold"
                >
                  Back to Login
                </button>
              </div>

              {/* Target ID selection */}
              <div className="grid grid-cols-2 gap-2 p-1 bg-amber-50 rounded-xl border border-amber-200">
                <button
                  type="button"
                  onClick={() => {
                    setResetRole('admin');
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  className={`py-1.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-1.5 ${
                    resetRole === 'admin'
                      ? 'bg-amber-700 text-white shadow-xs'
                      : 'text-amber-900 hover:text-amber-950'
                  }`}
                >
                  <ShieldCheck className="w-3 h-3" />
                  <span>ADMIN ID</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setResetRole('staff');
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  className={`py-1.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-1.5 ${
                    resetRole === 'staff'
                      ? 'bg-amber-700 text-white shadow-xs'
                      : 'text-amber-900 hover:text-amber-950'
                  }`}
                >
                  <Users className="w-3 h-3" />
                  <span>STAFF ID</span>
                </button>
              </div>

              {/* Verification Method Toggle: Email OTP vs Google Sign-In (rishugarg006@gmail.com) */}
              <div className="grid grid-cols-2 gap-1.5 p-1 bg-slate-100 rounded-xl text-[11px] font-bold">
                <button
                  type="button"
                  onClick={() => {
                    setResetMethod('email_otp');
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  className={`py-1.5 rounded-lg transition-all ${
                    resetMethod === 'email_otp'
                      ? 'bg-white text-amber-950 shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Email OTP
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setResetMethod('google_verify');
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  className={`py-1.5 rounded-lg transition-all ${
                    resetMethod === 'google_verify'
                      ? 'bg-white text-amber-950 shadow-2xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Verify via Google
                </button>
              </div>

              {resetMethod === 'email_otp' ? (
                resetStep === 'request' ? (
                  <form onSubmit={handleSendOtp} className="space-y-3.5">
                    <div>
                      <label className="block text-xs font-bold text-amber-950 mb-1">
                        USER ID
                      </label>
                      <input
                        type="text"
                        value={currentResetUserId}
                        readOnly
                        className="w-full px-3 py-2 bg-amber-50/60 border border-amber-300 rounded-xl text-xs font-black text-amber-950 tracking-wider cursor-not-allowed"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-amber-950 mb-1">
                        Registered Email for OTP
                      </label>
                      <div className="relative">
                        <Mail className="w-4 h-4 text-amber-700 absolute left-3 top-2.5" />
                        <input
                          type="email"
                          value="rishugarg006@gmail.com"
                          readOnly
                          className="w-full pl-9 pr-3 py-2 bg-amber-50/60 border border-amber-300 rounded-xl text-xs font-semibold text-amber-950 select-all cursor-not-allowed"
                        />
                      </div>
                    </div>

                    {errorMsg && (
                      <div className="flex flex-col space-y-2 text-xs text-red-700 bg-red-50 p-2.5 rounded-lg border border-red-200">
                        <div className="flex items-start space-x-2">
                          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                          <span>{errorMsg}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            setResetMethod('google_verify');
                            setErrorMsg('');
                          }}
                          className="self-start text-[11px] font-bold text-amber-900 underline hover:text-amber-950"
                        >
                          Switch to Verify via Google Account (rishugarg006@gmail.com) →
                        </button>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={isSending}
                      className="w-full py-2.5 px-4 bg-gradient-to-r from-amber-700 to-yellow-700 hover:from-amber-800 hover:to-yellow-800 text-white font-bold rounded-xl shadow-xs transition-all text-xs flex items-center justify-center space-x-1.5 cursor-pointer active:scale-98 disabled:opacity-60"
                    >
                      <span>{isSending ? 'Sending OTP Email...' : 'Send OTP to rishugarg006@gmail.com'}</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </form>
                ) : (
                  <form onSubmit={handleVerifyAndReset} className="space-y-3">
                    {successMsg && (
                      <div className="flex items-start space-x-2 text-xs text-emerald-800 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
                        <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                        <span>{successMsg}</span>
                      </div>
                    )}

                    <div>
                      <label className="block text-xs font-bold text-amber-950 mb-1">
                        Enter 6-Digit OTP from rishugarg006@gmail.com
                      </label>
                      <input
                        type="text"
                        maxLength={6}
                        value={otpCode}
                        onChange={e => setOtpCode(e.target.value.replace(/\D/g, ''))}
                        placeholder="------"
                        className="w-full px-3 py-2 text-center font-mono tracking-widest text-base font-black bg-white border border-amber-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500 text-amber-950"
                        required
                      />
                      <div className="flex items-center justify-between mt-1 text-[10px]">
                        <button
                          type="button"
                          onClick={handleSendOtp}
                          disabled={isSending}
                          className="text-amber-800 hover:underline font-bold"
                        >
                          {isSending ? 'Resending...' : 'Resend OTP'}
                        </button>
                        <span className="text-amber-800/70">Check inbox: rishugarg006@gmail.com</span>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-amber-950 mb-1">
                        New Password for {currentResetUserId}
                      </label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={e => setNewPassword(e.target.value)}
                        placeholder="Enter new password"
                        className="w-full px-3 py-2 bg-white border border-amber-300 rounded-xl text-xs text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-500 font-medium"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-amber-950 mb-1">
                        Confirm New Password
                      </label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={e => setConfirmPassword(e.target.value)}
                        placeholder="Confirm new password"
                        className="w-full px-3 py-2 bg-white border border-amber-300 rounded-xl text-xs text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-500 font-medium"
                        required
                      />
                    </div>

                    {errorMsg && (
                      <div className="flex items-center space-x-2 text-xs text-red-700 bg-red-50 p-2.5 rounded-lg border border-red-200">
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        <span>{errorMsg}</span>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={isVerifying}
                      className="w-full py-2.5 px-4 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-xl shadow-xs transition-all text-xs flex items-center justify-center space-x-1.5 cursor-pointer active:scale-98 disabled:opacity-60"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{isVerifying ? 'Verifying OTP...' : 'Verify OTP & Save Password'}</span>
                    </button>
                  </form>
                )
              ) : (
                /* Google Account Verification Flow for rishugarg006@gmail.com */
                <form onSubmit={handleGoogleVerifiedReset} className="space-y-3">
                  <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-950">
                    Set your new password for <strong>{currentResetUserId}</strong> and confirm ownership of{' '}
                    <strong>rishugarg006@gmail.com</strong> with Google Sign-In.
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-amber-950 mb-1">
                      New Password for {currentResetUserId}
                    </label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={e => setNewPassword(e.target.value)}
                      placeholder="Enter new password"
                      className="w-full px-3 py-2 bg-white border border-amber-300 rounded-xl text-xs text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-500 font-medium"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-amber-950 mb-1">
                      Confirm New Password
                    </label>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={e => setConfirmPassword(e.target.value)}
                      placeholder="Confirm new password"
                      className="w-full px-3 py-2 bg-white border border-amber-300 rounded-xl text-xs text-amber-950 focus:outline-none focus:ring-2 focus:ring-amber-500 font-medium"
                      required
                    />
                  </div>

                  {errorMsg && (
                    <div className="flex items-start space-x-2 text-xs text-red-700 bg-red-50 p-2.5 rounded-lg border border-red-200">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{errorMsg}</span>
                    </div>
                  )}

                  {successMsg && (
                    <div className="flex items-start space-x-2 text-xs text-emerald-800 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
                      <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                      <span>{successMsg}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isVerifying}
                    className="w-full py-2.5 px-4 bg-white hover:bg-slate-50 text-slate-900 font-bold rounded-xl border border-slate-300 shadow-xs transition-all text-xs flex items-center justify-center space-x-2 cursor-pointer active:scale-98 disabled:opacity-60"
                  >
                    <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                      <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.4 1 3.5 3.6 1.6 7.4l3.7 2.8C6.2 7.2 8.9 5 12 5z"/>
                      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.6l3.7 2.9c2.2-2 3.7-5 3.7-8.7z"/>
                      <path fill="#FBBC05" d="M5.3 14.8c-.2-.8-.4-1.6-.4-2.5s.1-1.7.4-2.5L1.6 7C.6 9 0 11.2 0 13.5s.6 4.5 1.6 6.5l3.7-2.9z"/>
                      <path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3.1 0-5.8-2.1-6.7-5l-3.7 2.9C3.5 20.4 7.4 23 12 23z"/>
                    </svg>
                    <span>{isVerifying ? 'Verifying with Google...' : 'Verify with Google (rishugarg006@gmail.com)'}</span>
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
