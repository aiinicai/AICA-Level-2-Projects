import React, { useState } from 'react';
import {
  LogIn,
  UserPlus,
  ShieldCheck,
  Building2,
  Mail,
  Lock,
  Phone,
  User,
  CheckCircle2,
  X,
  KeyRound,
  AlertCircle,
  Hash,
  ArrowRight,
  ShieldAlert
} from 'lucide-react';
import { UserProfile, UserRole, ThemeStyle } from '../types';
import { ParcelStorageService } from '../services/storage';
import { THEMES } from '../utils/theme';
import { AppLogo } from './AppLogo';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: UserProfile) => void;
  currentTheme?: ThemeStyle;
  initialMode?: 'login' | 'signup' | 'change_password';
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  currentTheme = 'navy',
  initialMode = 'login',
}) => {
  const [mode, setMode] = useState<'login' | 'signup' | 'change_password'>(initialMode);
  const [signupType, setSignupType] = useState<'new_firm' | 'join_firm'>('new_firm');
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Login Form State
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Signup Form State
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [firmName, setFirmName] = useState('');
  const [firmCode, setFirmCode] = useState('');
  const [icaiNumber, setIcaiNumber] = useState('');
  const [role, setRole] = useState<UserRole>('admin_partner');
  const [department, setDepartment] = useState('Statutory Audit & Assurance');
  const [designation, setDesignation] = useState('Senior Partner (FCA)');
  const [signupPassword, setSignupPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Change / Reset Password State
  const [resetEmail, setResetEmail] = useState('');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');

  const themeConfig = THEMES[currentTheme] || THEMES.navy;

  if (!isOpen) return null;

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!loginEmail.trim()) {
      setErrorMsg('Please enter your registered work email or Staff ID');
      return;
    }

    const user = ParcelStorageService.loginUser(loginEmail, loginPassword);
    if (!user) {
      setErrorMsg('No user account found with that email. Please sign up to create your firm workspace.');
      return;
    }

    setSuccessMsg(`Welcome back, ${user.name}! Logging into ${user.firmName}...`);
    setTimeout(() => {
      onSuccess(user);
      onClose();
    }, 400);
  };

  const handleSignupSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!name.trim()) {
      setErrorMsg('Please enter full legal name');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setErrorMsg('Please enter a valid work email address');
      return;
    }

    if (signupType === 'new_firm' && !firmName.trim()) {
      setErrorMsg('Please enter your Chartered Accountancy firm or organization name');
      return;
    }

    if (signupType === 'join_firm' && !firmCode.trim()) {
      setErrorMsg('Please enter the Firm Workspace Code provided by your firm partner');
      return;
    }

    if (signupPassword && confirmPassword && signupPassword !== confirmPassword) {
      setErrorMsg('Passwords do not match');
      return;
    }

    // Check if joining existing firm
    let resolvedFirmName = firmName.trim();
    if (signupType === 'join_firm') {
      const existingOrg = ParcelStorageService.getOrganizationByCode(firmCode);
      if (!existingOrg) {
        setErrorMsg(`No firm workspace found matching code "${firmCode.trim().toUpperCase()}". Please verify the code with your firm administrator.`);
        return;
      }
      resolvedFirmName = existingOrg.name;
    }

    const newUser = ParcelStorageService.registerUser({
      name: name.trim(),
      email: email.trim().toLowerCase(),
      phone: phone.trim() || '+91 98200 00000',
      role,
      department,
      designation:
        designation.trim() ||
        (role === 'admin_partner'
          ? 'Senior Partner (FCA)'
          : role === 'front_desk'
          ? 'Front Desk Lead'
          : 'Staff Consultant'),
      firmName: resolvedFirmName,
      organizationCode: signupType === 'join_firm' ? firmCode.trim() : undefined,
      icaiNumber: icaiNumber.trim() || undefined
    });

    setSuccessMsg(`Workspace created successfully for ${newUser.firmName}! Welcome, ${newUser.name}.`);
    setTimeout(() => {
      onSuccess(newUser);
      onClose();
    }, 400);
  };

  const handleChangePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!resetEmail.trim()) {
      setErrorMsg('Please enter your registered work email or Staff ID');
      return;
    }
    if (!newPassword) {
      setErrorMsg('Please enter a new password or security PIN');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setErrorMsg('New password and confirmation do not match');
      return;
    }

    const user = ParcelStorageService.updateUserPassword(resetEmail, newPassword);
    if (!user) {
      setErrorMsg('No user found matching that email or ID. Please check the email address.');
      return;
    }

    setSuccessMsg(`Password successfully updated for ${user.name}! Logging you in...`);
    setTimeout(() => {
      onSuccess(user);
      onClose();
    }, 500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className={`relative w-full max-w-xl rounded-2xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} shadow-2xl overflow-hidden backdrop-blur-xl transition-all duration-300 max-h-[94vh] flex flex-col`}
      >
        {/* Top Header */}
        <div className={`p-4 sm:p-6 border-b ${themeConfig.cardBorder} flex items-center justify-between`}>
          <div className="flex items-center gap-3">
            <AppLogo concept="parceldesk_official" themeStyle={currentTheme} size="sm" showText={false} />
            <div>
              <h2 className={`text-base sm:text-lg font-bold ${themeConfig.textPrimary} flex items-center gap-2`}>
                <span>
                  {mode === 'login'
                    ? 'CA Firm Workstation Sign In'
                    : mode === 'signup'
                    ? 'Register Firm / Staff Account'
                    : 'Change Password / Security PIN'}
                </span>
              </h2>
              <p className={`text-xs ${themeConfig.textMuted} mt-0.5`}>
                {mode === 'login'
                  ? 'Strict organization-isolated custody tracking for CA firms'
                  : mode === 'signup'
                  ? 'Create an isolated workspace for your firm or join an existing firm'
                  : 'Update credentials to maintain strict document confidentiality'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className={`p-1.5 rounded-lg ${themeConfig.textMuted} hover:${themeConfig.textPrimary} ${themeConfig.cardHover} transition-colors`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 3-Way Tab Switcher */}
        <div className={`px-3 sm:px-6 pt-3 pb-2 bg-slate-500/5 border-b ${themeConfig.cardBorder} flex gap-1.5 sm:gap-2`}>
          <button
            type="button"
            onClick={() => {
              setMode('login');
              setErrorMsg('');
              setSuccessMsg('');
            }}
            className={`flex-1 py-2 px-2 sm:px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
              mode === 'login'
                ? `${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent} shadow-sm`
                : `${themeConfig.textMuted} hover:${themeConfig.textPrimary}`
            }`}
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Sign In</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setMode('signup');
              setErrorMsg('');
              setSuccessMsg('');
            }}
            className={`flex-1 py-2 px-2 sm:px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
              mode === 'signup'
                ? `${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent} shadow-sm`
                : `${themeConfig.textMuted} hover:${themeConfig.textPrimary}`
            }`}
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Register Firm / Staff</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setMode('change_password');
              setErrorMsg('');
              setSuccessMsg('');
              if (loginEmail) setResetEmail(loginEmail);
            }}
            className={`flex-1 py-2 px-2 sm:px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
              mode === 'change_password'
                ? `${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent} shadow-sm`
                : `${themeConfig.textMuted} hover:${themeConfig.textPrimary}`
            }`}
          >
            <KeyRound className="w-3.5 h-3.5" />
            <span>Change PIN</span>
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-4">
          {errorMsg && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {mode === 'login' ? (
            /* ================= LOGIN FORM ================= */
            <div className="space-y-4">
              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-400 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">Organization Data Isolation Guaranteed</span>
                  <p className={`text-[11px] ${themeConfig.textMuted} mt-0.5`}>
                    Signing in connects you exclusively to your firm&apos;s isolated docket registry, client cost recovery, and recipient staff.
                  </p>
                </div>
              </div>

              <form onSubmit={handleLoginSubmit} className="space-y-3.5">
                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Work Email or CA Staff ID *
                  </label>
                  <div className="relative">
                    <Mail className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3.5 top-3`} />
                    <input
                      type="text"
                      required
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      placeholder="e.g., partner@firmca.in or staff.name@firm.com"
                      className={`w-full pl-10 pr-4 py-2.5 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none transition-colors`}
                    />
                  </div>
                </div>

                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Account Password / PIN
                  </label>
                  <div className="relative">
                    <Lock className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3.5 top-3`} />
                    <input
                      type="password"
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className={`w-full pl-10 pr-4 py-2.5 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none transition-colors`}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className={`w-full py-2.5 rounded-xl ${themeConfig.primaryBtn} text-xs font-bold transition-all shadow-md active:scale-95 flex items-center justify-center gap-2 mt-2`}
                >
                  <LogIn className="w-4 h-4" />
                  <span>Sign In to Firm Workspace</span>
                </button>
              </form>

              <div className={`text-center pt-2 border-t ${themeConfig.cardBorder}`}>
                <p className={`text-xs ${themeConfig.textMuted}`}>
                  New firm or new staff member?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setMode('signup');
                      setErrorMsg('');
                    }}
                    className={`font-bold ${themeConfig.textAccent} hover:underline ml-1`}
                  >
                    Register Your CA Practice / Account
                  </button>
                </p>
              </div>
            </div>
          ) : mode === 'signup' ? (
            /* ================= SIGNUP FORM ================= */
            <form onSubmit={handleSignupSubmit} className="space-y-3.5">
              {/* Option to create a new firm workspace or join with a firm code */}
              <div className="grid grid-cols-2 gap-2 p-1 rounded-xl bg-slate-500/10 border border-slate-500/20">
                <button
                  type="button"
                  onClick={() => setSignupType('new_firm')}
                  className={`py-1.5 px-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                    signupType === 'new_firm'
                      ? `${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent} shadow-sm`
                      : `${themeConfig.textMuted} hover:${themeConfig.textPrimary}`
                  }`}
                >
                  <Building2 className="w-3.5 h-3.5" />
                  <span>Create New Practice</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSignupType('join_firm')}
                  className={`py-1.5 px-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                    signupType === 'join_firm'
                      ? `${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent} shadow-sm`
                      : `${themeConfig.textMuted} hover:${themeConfig.textPrimary}`
                  }`}
                >
                  <Hash className="w-3.5 h-3.5" />
                  <span>Join with Firm Code</span>
                </button>
              </div>

              {signupType === 'new_firm' ? (
                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Chartered Accountancy Firm / Practice Name *
                  </label>
                  <div className="relative">
                    <Building2 className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3 top-3`} />
                    <input
                      type="text"
                      required
                      value={firmName}
                      onChange={(e) => setFirmName(e.target.value)}
                      placeholder="e.g., Kothari & Co Chartered Accountants"
                      className={`w-full pl-9 pr-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                    />
                  </div>
                </div>
              ) : (
                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Firm Workspace Code (Given by your firm admin) *
                  </label>
                  <div className="relative">
                    <Hash className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3 top-3`} />
                    <input
                      type="text"
                      required
                      value={firmCode}
                      onChange={(e) => setFirmCode(e.target.value.toUpperCase())}
                      placeholder="e.g., KOTHAR-294"
                      className={`w-full pl-9 pr-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs font-mono font-bold ${themeConfig.textPrimary} focus:outline-none`}
                    />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Full Name & Salutation *
                  </label>
                  <div className="relative">
                    <User className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3 top-3`} />
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g., CA Rajesh Sharma"
                      className={`w-full pl-9 pr-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                    />
                  </div>
                </div>

                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Work Email *
                  </label>
                  <div className="relative">
                    <Mail className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3 top-3`} />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="e.g., rajesh@firmca.in"
                      className={`w-full pl-9 pr-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                    />
                  </div>
                </div>
              </div>

              {/* Role Selection */}
              <div>
                <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1.5`}>
                  Assign User Role & Permissions (RBAC) *
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setRole('admin_partner');
                      setDepartment('Statutory Audit & Assurance');
                      setDesignation('Senior Partner (FCA)');
                    }}
                    className={`text-left p-2.5 rounded-xl border text-xs transition-all ${
                      role === 'admin_partner'
                        ? `border-purple-500 bg-purple-500/10 ring-1 ring-purple-500/30`
                        : `${themeConfig.subCardBg} border ${themeConfig.cardBorder} ${themeConfig.cardHover}`
                    }`}
                  >
                    <span className="font-bold text-purple-600 dark:text-purple-400 block">Partner / Admin</span>
                    <span className={`text-[10px] ${themeConfig.textMuted} block leading-tight mt-0.5`}>
                      Firm-wide visibility, analytics & approvals
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setRole('front_desk');
                      setDepartment('Administration & Dispatch');
                      setDesignation('Front Desk & Dispatch Manager');
                    }}
                    className={`text-left p-2.5 rounded-xl border text-xs transition-all ${
                      role === 'front_desk'
                        ? `border-emerald-500 bg-emerald-500/10 ring-1 ring-emerald-500/30`
                        : `${themeConfig.subCardBg} border ${themeConfig.cardBorder} ${themeConfig.cardHover}`
                    }`}
                  >
                    <span className="font-bold text-emerald-600 dark:text-emerald-400 block">Front Desk / Reception</span>
                    <span className={`text-[10px] ${themeConfig.textMuted} block leading-tight mt-0.5`}>
                      Log inward mail, create courier dockets & shelves
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setRole('audit_staff');
                      setDepartment('Direct Tax & Litigation');
                      setDesignation('Audit & Tax Senior');
                    }}
                    className={`text-left p-2.5 rounded-xl border text-xs transition-all ${
                      role === 'audit_staff'
                        ? `border-blue-500 ${themeConfig.badgeBg} ring-1 ring-blue-500/30`
                        : `${themeConfig.subCardBg} border ${themeConfig.cardBorder} ${themeConfig.cardHover}`
                    }`}
                  >
                    <span className={`font-bold ${themeConfig.textAccent} block`}>Audit / Tax Staff</span>
                    <span className={`text-[10px] ${themeConfig.textMuted} block leading-tight mt-0.5`}>
                      Confidential mailbox & own dispatch tracking
                    </span>
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Department *
                  </label>
                  <select
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                  >
                    <option value="Statutory Audit & Assurance">Statutory Audit & Assurance</option>
                    <option value="Direct Tax & Litigation">Direct Tax & Litigation</option>
                    <option value="GST & Indirect Tax">GST & Indirect Tax</option>
                    <option value="ROC & Corporate Law">ROC & Corporate Law</option>
                    <option value="Administration & Dispatch">Administration & Dispatch</option>
                    <option value="Partner Executive Desk">Partner Executive Desk</option>
                  </select>
                </div>

                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Designation / Title
                  </label>
                  <input
                    type="text"
                    value={designation}
                    onChange={(e) => setDesignation(e.target.value)}
                    placeholder="e.g., Senior Article Assistant / Partner"
                    className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Mobile Number (WhatsApp Notifications)
                  </label>
                  <div className="relative">
                    <Phone className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3 top-3`} />
                    <input
                      type="text"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+91 98200 12345"
                      className={`w-full pl-9 pr-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                    />
                  </div>
                </div>

                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    ICAI Reg / Member No. (Optional)
                  </label>
                  <input
                    type="text"
                    value={icaiNumber}
                    onChange={(e) => setIcaiNumber(e.target.value)}
                    placeholder="e.g., ICAI-158293"
                    className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Create Account Password
                  </label>
                  <input
                    type="password"
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                  />
                </div>

                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                  />
                </div>
              </div>

              <button
                type="submit"
                className={`w-full py-2.5 rounded-xl ${themeConfig.primaryBtn} text-xs font-bold transition-all shadow-md active:scale-95 flex items-center justify-center gap-2 mt-2`}
              >
                <UserPlus className="w-4 h-4" />
                <span>Create Workspace & Start Logging</span>
              </button>
            </form>
          ) : (
            /* ================= CHANGE / RESET PASSWORD FORM ================= */
            <form onSubmit={handleChangePasswordSubmit} className="space-y-3.5">
              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-400">
                <p className="font-semibold flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0" />
                  Self-Service Password & PIN Reset
                </p>
                <p className={`text-[11px] ${themeConfig.textMuted} mt-0.5`}>
                  Enter your registered work email address and configure a new security password.
                </p>
              </div>

              <div>
                <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                  Registered Work Email or Staff ID *
                </label>
                <div className="relative">
                  <Mail className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3 top-3`} />
                  <input
                    type="text"
                    required
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                    placeholder="e.g., rajesh.sharma@firmca.in or USR-01"
                    className={`w-full pl-9 pr-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                  />
                </div>
              </div>

              <div>
                <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                  Current Password (Optional)
                </label>
                <div className="relative">
                  <Lock className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3 top-3`} />
                  <input
                    type="password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    placeholder="••••••••"
                    className={`w-full pl-9 pr-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    New Password / PIN *
                  </label>
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                  />
                </div>

                <div>
                  <label className={`block text-xs font-semibold uppercase tracking-wider ${themeConfig.textMuted} mb-1`}>
                    Confirm New Password *
                  </label>
                  <input
                    type="password"
                    required
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none`}
                  />
                </div>
              </div>

              <button
                type="submit"
                className={`w-full py-2.5 rounded-xl ${themeConfig.primaryBtn} text-xs font-bold transition-all shadow-md active:scale-95 flex items-center justify-center gap-2 mt-2`}
              >
                <KeyRound className="w-4 h-4" />
                <span>Save New Password & Sign In</span>
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
