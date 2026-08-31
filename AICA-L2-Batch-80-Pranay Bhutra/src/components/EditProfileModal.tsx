import React, { useState, useEffect } from 'react';
import {
  User,
  Shield,
  Briefcase,
  Building2,
  Mail,
  Phone,
  Hash,
  CheckCircle2,
  X,
  Save,
  Check,
  ShieldAlert,
  Sparkles
} from 'lucide-react';
import { UserProfile, UserRole, ThemeStyle } from '../types';
import { ParcelStorageService } from '../services/storage';
import { THEMES } from '../utils/theme';
import { MOCK_DEPARTMENTS } from '../data/mockData';

interface EditProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserProfile;
  onSuccess: (updatedUser: UserProfile) => void;
  currentTheme?: ThemeStyle;
}

export const EditProfileModal: React.FC<EditProfileModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onSuccess,
  currentTheme = 'navy',
}) => {
  const themeConfig = THEMES[currentTheme] || THEMES.navy;

  const [name, setName] = useState(currentUser?.name || '');
  const [email, setEmail] = useState(currentUser?.email || '');
  const [phone, setPhone] = useState(currentUser?.phone || '');
  const [role, setRole] = useState<UserRole>(currentUser?.role || 'admin_partner');
  const [department, setDepartment] = useState(currentUser?.department || 'Statutory Audit & Assurance');
  const [customDepartment, setCustomDepartment] = useState('');
  const [isCustomDept, setIsCustomDept] = useState(
    !MOCK_DEPARTMENTS.includes(currentUser?.department || '') && currentUser?.department !== ''
  );
  const [designation, setDesignation] = useState(currentUser?.designation || '');
  const [firmName, setFirmName] = useState(currentUser?.firmName || '');
  const [icaiNumber, setIcaiNumber] = useState(currentUser?.icaiNumber || '');
  
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (currentUser && isOpen) {
      setName(currentUser.name || '');
      setEmail(currentUser.email || '');
      setPhone(currentUser.phone || '');
      setRole(currentUser.role || 'admin_partner');
      const dept = currentUser.department || 'Statutory Audit & Assurance';
      if (MOCK_DEPARTMENTS.includes(dept)) {
        setDepartment(dept);
        setIsCustomDept(false);
        setCustomDepartment('');
      } else {
        setDepartment('Other Department');
        setIsCustomDept(true);
        setCustomDepartment(dept);
      }
      setDesignation(currentUser.designation || '');
      setFirmName(currentUser.firmName || '');
      setIcaiNumber(currentUser.icaiNumber || '');
      setErrorMsg('');
      setSuccessMsg('');
    }
  }, [currentUser, isOpen]);

  if (!isOpen) return null;

  const handleDepartmentSelect = (val: string) => {
    if (val === 'Other Department') {
      setIsCustomDept(true);
      setDepartment('Other Department');
    } else {
      setIsCustomDept(false);
      setDepartment(val);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (!name.trim()) {
      setErrorMsg('Full name cannot be empty');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setErrorMsg('Please enter a valid work email address');
      return;
    }

    const resolvedDept = isCustomDept
      ? (customDepartment.trim() || 'General Department')
      : department;

    setIsSaving(true);

    try {
      const updated = ParcelStorageService.updateUserProfile(currentUser.id, {
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        role,
        department: resolvedDept,
        designation: designation.trim() || (role === 'admin_partner' ? 'Partner' : role === 'front_desk' ? 'Front Desk Staff' : 'Audit Staff'),
        firmName: firmName.trim() || currentUser.firmName,
        icaiNumber: icaiNumber.trim() || undefined,
      });

      if (updated) {
        setSuccessMsg('Profile and permissions updated successfully!');
        setTimeout(() => {
          setIsSaving(false);
          onSuccess(updated);
          onClose();
        }, 600);
      } else {
        setIsSaving(false);
        setErrorMsg('Failed to update profile. User account could not be found.');
      }
    } catch (err: any) {
      setIsSaving(false);
      setErrorMsg(err.message || 'An unexpected error occurred while saving profile.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className={`relative w-full max-w-xl rounded-2xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} shadow-2xl p-5 sm:p-6 overflow-hidden max-h-[90vh] flex flex-col`}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-700/30">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl bg-gradient-to-tr ${themeConfig.accentGlow} text-white shadow-md`}>
              <User className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className={`text-base sm:text-lg font-bold ${themeConfig.textPrimary}`}>
                  Edit Staff Profile & Role Permissions
                </h2>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold uppercase ${themeConfig.badgeBg} ${themeConfig.badgeText} border ${themeConfig.borderAccent}`}>
                  {currentUser?.id}
                </span>
              </div>
              <p className={`text-xs ${themeConfig.textMuted}`}>
                Manage account identification, department, CA credentials, and workstation access levels.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className={`p-1.5 rounded-xl ${themeConfig.textMuted} hover:${themeConfig.textPrimary} hover:${themeConfig.subCardBg} transition-colors`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error / Success Feedback */}
        {errorMsg && (
          <div className="mt-3 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2 animate-in fade-in">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div className="mt-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2 animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="mt-4 space-y-4 overflow-y-auto pr-1 flex-1">
          {/* 1. Name & Email */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className={`text-xs font-semibold ${themeConfig.textSecondary} flex items-center gap-1.5 mb-1`}>
                <User className="w-3.5 h-3.5 text-blue-400" />
                Full Name / Staff Name:
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="e.g. CA Rajesh Sharma"
                className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none focus:border-blue-500 transition-colors`}
              />
            </div>

            <div>
              <label className={`text-xs font-semibold ${themeConfig.textSecondary} flex items-center gap-1.5 mb-1`}>
                <Mail className="w-3.5 h-3.5 text-emerald-400" />
                Work Email Address:
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="name@firmca.in"
                className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none focus:border-blue-500 transition-colors`}
              />
            </div>
          </div>

          {/* 2. Role & Access Permission Level (RBAC) */}
          <div className={`p-3.5 rounded-xl ${themeConfig.subCardBg} border ${themeConfig.cardBorder} space-y-2.5`}>
            <label className={`text-xs font-bold ${themeConfig.textPrimary} flex items-center gap-1.5`}>
              <Shield className="w-4 h-4 text-amber-500" />
              Role & Workstation Permission Level (RBAC)
            </label>
            <p className={`text-[11px] ${themeConfig.textMuted}`}>
              Adjust which modules, confidential registers, and desk tools this user can access:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {/* Partner */}
              <button
                type="button"
                onClick={() => {
                  setRole('admin_partner');
                  if (!designation || designation === 'Front Desk & Dispatch Manager' || designation === 'Senior Article Assistant') {
                    setDesignation('Senior Partner (FCA)');
                  }
                }}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  role === 'admin_partner'
                    ? `${themeConfig.badgeBg} ${themeConfig.badgeText} border-amber-500/50 shadow-md ring-1 ring-amber-500/30`
                    : `${themeConfig.cardBg} border-slate-700/30 opacity-70 hover:opacity-100`
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-amber-400">Partner / FCA</span>
                  {role === 'admin_partner' && <Check className="w-3.5 h-3.5 text-amber-400" />}
                </div>
                <p className={`text-[10px] ${themeConfig.textMuted} leading-tight`}>
                  Executive access, courier recovery billing, partner approvals & firm audit metrics.
                </p>
              </button>

              {/* Front Desk */}
              <button
                type="button"
                onClick={() => {
                  setRole('front_desk');
                  if (!designation || designation === 'Senior Partner (FCA)' || designation === 'Senior Article Assistant') {
                    setDesignation('Front Desk & Dispatch Manager');
                  }
                }}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  role === 'front_desk'
                    ? `${themeConfig.badgeBg} ${themeConfig.badgeText} border-cyan-500/50 shadow-md ring-1 ring-cyan-500/30`
                    : `${themeConfig.cardBg} border-slate-700/30 opacity-70 hover:opacity-100`
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-cyan-400">Front Desk</span>
                  {role === 'front_desk' && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                </div>
                <p className={`text-[10px] ${themeConfig.textMuted} leading-tight`}>
                  Inward parcel intake camera, shelf holding racks, outward manifest & physical POD handovers.
                </p>
              </button>

              {/* Audit Staff */}
              <button
                type="button"
                onClick={() => {
                  setRole('audit_staff');
                  if (!designation || designation === 'Senior Partner (FCA)' || designation === 'Front Desk & Dispatch Manager') {
                    setDesignation('Senior Article Assistant');
                  }
                }}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  role === 'audit_staff'
                    ? `${themeConfig.badgeBg} ${themeConfig.badgeText} border-emerald-500/50 shadow-md ring-1 ring-emerald-500/30`
                    : `${themeConfig.cardBg} border-slate-700/30 opacity-70 hover:opacity-100`
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-emerald-400">Audit & Tax Staff</span>
                  {role === 'audit_staff' && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                </div>
                <p className={`text-[10px] ${themeConfig.textMuted} leading-tight`}>
                  Personal mailbox custody, draft outward dispatches & handover digital sign-offs.
                </p>
              </button>
            </div>
          </div>

          {/* 3. Department & Custom Department */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className={`text-xs font-semibold ${themeConfig.textSecondary} flex items-center gap-1.5 mb-1`}>
                <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
                Practice Department:
              </label>
              <select
                value={department}
                onChange={(e) => handleDepartmentSelect(e.target.value)}
                className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none focus:border-blue-500 transition-colors`}
              >
                {MOCK_DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={`text-xs font-semibold ${themeConfig.textSecondary} flex items-center gap-1.5 mb-1`}>
                <Building2 className="w-3.5 h-3.5 text-purple-400" />
                Designation / Job Title:
              </label>
              <input
                type="text"
                value={designation}
                onChange={(e) => setDesignation(e.target.value)}
                placeholder="e.g. Senior Partner (FCA), Senior Article Assistant, Manager"
                className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none focus:border-blue-500 transition-colors`}
              />
            </div>
          </div>

          {/* If Custom Department Selected */}
          {isCustomDept && (
            <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 animate-in fade-in duration-150">
              <label className="text-xs font-semibold text-purple-300 block mb-1">
                Enter Custom Department Name:
              </label>
              <input
                type="text"
                value={customDepartment}
                onChange={(e) => setCustomDepartment(e.target.value)}
                required
                placeholder="e.g. Transfer Pricing Desk, Insolvency & Bankruptcy, Forensic Audit"
                className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} placeholder:text-slate-500 focus:border-purple-500 focus:outline-none`}
              />
            </div>
          )}

          {/* 4. Phone, ICAI Number & Firm Name */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className={`text-xs font-semibold ${themeConfig.textSecondary} flex items-center gap-1.5 mb-1`}>
                <Phone className="w-3.5 h-3.5 text-blue-400" />
                Mobile / Phone:
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 98200 XXXXX"
                className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none focus:border-blue-500 transition-colors`}
              />
            </div>

            <div>
              <label className={`text-xs font-semibold ${themeConfig.textSecondary} flex items-center gap-1.5 mb-1`}>
                <Hash className="w-3.5 h-3.5 text-amber-400" />
                ICAI / Reg. Number:
              </label>
              <input
                type="text"
                value={icaiNumber}
                onChange={(e) => setIcaiNumber(e.target.value)}
                placeholder="e.g. FCA-048291"
                className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} font-mono focus:outline-none focus:border-blue-500 transition-colors`}
              />
            </div>

            <div>
              <label className={`text-xs font-semibold ${themeConfig.textSecondary} flex items-center gap-1.5 mb-1`}>
                <Building2 className="w-3.5 h-3.5 text-emerald-400" />
                Firm / Practice Name:
              </label>
              <input
                type="text"
                value={firmName}
                onChange={(e) => setFirmName(e.target.value)}
                placeholder="e.g. Singhania & Associates CA"
                className={`w-full px-3 py-2 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs ${themeConfig.textPrimary} focus:outline-none focus:border-blue-500 transition-colors`}
              />
            </div>
          </div>

          {/* Modal Action Buttons */}
          <div className="pt-4 border-t border-slate-700/30 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className={`px-4 py-2 rounded-xl ${themeConfig.secondaryBtn} text-xs font-semibold transition-colors`}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className={`flex items-center gap-2 px-5 py-2 rounded-xl ${themeConfig.primaryBtn} text-xs font-bold shadow-lg transition-all active:scale-95 disabled:opacity-50`}
            >
              {isSaving ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Saving Updates...</span>
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  <span>Save Profile & Permissions</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
