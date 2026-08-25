import React, { useState } from 'react';
import {
  Building2,
  Users,
  ShieldCheck,
  UserPlus,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Lock,
  Mail,
  Phone,
  Hash,
  Palette,
  X,
  Copy,
  Briefcase
} from 'lucide-react';
import { CompanyProfile, User, UserRole } from '../../types';
import { StorageService, formatTIN, validateTIN } from '../../services/storage';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUserChanged: (user: User) => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onUserChanged }) => {
  const storage = StorageService.getInstance();
  const companies = storage.getCompanies();
  const currentCompany = storage.getCompanyProfile();
  const currentUser = storage.getCurrentUser();
  const allUsers = storage.getAllUsersAcrossCompanies();

  const [tab, setTab] = useState<'switcher' | 'register_company' | 'join_company'>('switcher');

  // Register Company Form State
  const [newCompanyName, setNewCompanyName] = useState('');
  const [newCompanyTin, setNewCompanyTin] = useState('');
  const [newCompanyVrn, setNewCompanyVrn] = useState('');
  const [newCompanyAddress, setNewCompanyAddress] = useState('');
  const [newCompanyPhone, setNewCompanyPhone] = useState('+255 ');
  const [newCompanyEmail, setNewCompanyEmail] = useState('');
  const [newCompanyBankName, setNewCompanyBankName] = useState('CRDB Bank Plc');
  const [newCompanyAccountNo, setNewCompanyAccountNo] = useState('');
  const [newAdminName, setNewAdminName] = useState('');
  const [newAdminEmail, setNewAdminEmail] = useState('');
  const [newAdminMobile, setNewAdminMobile] = useState('+255 ');
  const [newPrimaryColor, setNewPrimaryColor] = useState('#0F2C59');

  // Join Existing Company Form State
  const [joinCompanyCode, setJoinCompanyCode] = useState('');
  const [joinRoleType, setJoinRoleType] = useState<'staff' | 'client'>('staff');
  const [joinStaffRole, setJoinStaffRole] = useState<UserRole>('operations');
  const [joinApplicantName, setJoinApplicantName] = useState('');
  const [joinApplicantEmail, setJoinApplicantEmail] = useState('');
  const [joinApplicantMobile, setJoinApplicantMobile] = useState('+255 ');
  const [joinClientCompanyName, setJoinClientCompanyName] = useState('');
  const [joinNotes, setJoinNotes] = useState('');

  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleQuickSwitch = (targetCompanyId: string, targetUserId: string) => {
    storage.switchCompany(targetCompanyId, targetUserId);
    const updatedUser = storage.getCurrentUser();
    onUserChanged(updatedUser);
    onClose();
  };

  const handleRegisterCompanySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedbackMsg(null);

    if (!newCompanyName.trim()) {
      setFeedbackMsg({ type: 'error', text: 'Please enter a valid Company Legal Name.' });
      return;
    }
    if (!validateTIN(newCompanyTin)) {
      setFeedbackMsg({ type: 'error', text: 'TIN must be 9 digits (e.g. 104-582-931).' });
      return;
    }
    if (!newAdminName.trim() || !newAdminEmail.trim()) {
      setFeedbackMsg({ type: 'error', text: 'Please specify the Initial Administrator name and email.' });
      return;
    }

    try {
      const { company, adminUser } = storage.registerNewCompany(
        {
          name: newCompanyName.trim(),
          tin: formatTIN(newCompanyTin),
          vrn: newCompanyVrn.trim() || undefined,
          address: newCompanyAddress.trim() || 'Dar es Salaam, Tanzania',
          phone: newCompanyPhone.trim() || '+255 22 000 0000',
          email: newCompanyEmail.trim() || `${newAdminEmail.split('@')[0]}@${newCompanyName.toLowerCase().replace(/[^a-z]/g, '')}.co.tz`,
          website: `https://www.${newCompanyName.toLowerCase().replace(/[^a-z]/g, '')}.co.tz`,
          bankDetails: {
            bankName: newCompanyBankName,
            accountName: newCompanyName.trim(),
            accountNumber: newCompanyAccountNo.trim() || '0150' + Math.floor(100000000 + Math.random() * 900000000),
            swiftCode: 'CORUTZTZ',
            branchName: 'Corporate Branch, Dar es Salaam',
          },
          theme: {
            primaryColor: newPrimaryColor,
            secondaryColor: '#1E40AF',
            accentColor: '#D97706',
            fontFamily: 'Inter, system-ui, sans-serif',
          },
        },
        {
          name: newAdminName.trim(),
          email: newAdminEmail.trim(),
          mobile: newAdminMobile.trim(),
        }
      );

      onUserChanged(adminUser);
      setFeedbackMsg({
        type: 'success',
        text: `Company "${company.name}" registered successfully! Assigned Company Code: ${company.companyCode}. You are logged in as Admin.`,
      });
      setTimeout(() => {
        onClose();
      }, 1400);
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Registration failed.' });
    }
  };

  const handleJoinSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedbackMsg(null);

    if (!joinCompanyCode.trim()) {
      setFeedbackMsg({ type: 'error', text: 'Please enter the Company Code provided by your administrator.' });
      return;
    }

    const assignedRole = joinRoleType === 'client' ? 'client_portal' : joinStaffRole;

    const result = storage.submitSignupRequest({
      companyCode: joinCompanyCode.trim(),
      name: joinApplicantName.trim(),
      email: joinApplicantEmail.trim(),
      mobile: joinApplicantMobile.trim(),
      requestedRole: assignedRole,
      linkedClientName: joinRoleType === 'client' ? joinClientCompanyName.trim() : undefined,
      notes: joinNotes.trim() || undefined,
    });

    if (result.success) {
      setFeedbackMsg({ type: 'success', text: result.message });
      setTimeout(() => {
        setTab('switcher');
      }, 2500);
    } else {
      setFeedbackMsg({ type: 'error', text: result.message });
    }
  };

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-5 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800 shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white tracking-tight">
                Multi-Tenant Account & Role Control Center
              </h3>
              <p className="text-xs text-slate-400">
                Switch tenant company, test role-based permissions, or register a new company
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 bg-slate-50 px-6 shrink-0">
          <button
            onClick={() => {
              setTab('switcher');
              setFeedbackMsg(null);
            }}
            className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center space-x-2 transition ${
              tab === 'switcher'
                ? 'border-blue-600 text-blue-700 bg-white'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Fast Switcher (3 Demo Tenants & Roles)</span>
          </button>
          <button
            onClick={() => {
              setTab('register_company');
              setFeedbackMsg(null);
            }}
            className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center space-x-2 transition ${
              tab === 'register_company'
                ? 'border-blue-600 text-blue-700 bg-white'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <Building2 className="w-4 h-4" />
            <span>Register New Company (Tenant)</span>
          </button>
          <button
            onClick={() => {
              setTab('join_company');
              setFeedbackMsg(null);
            }}
            className={`py-3 px-4 text-xs font-semibold border-b-2 flex items-center space-x-2 transition ${
              tab === 'join_company'
                ? 'border-blue-600 text-blue-700 bg-white'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <UserPlus className="w-4 h-4" />
            <span>Join with Company Code</span>
          </button>
        </div>

        {/* Feedback alert */}
        {feedbackMsg && (
          <div
            className={`mx-6 mt-4 p-3 rounded-lg text-xs flex items-center space-x-2 ${
              feedbackMsg.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}
          >
            {feedbackMsg.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            )}
            <span>{feedbackMsg.text}</span>
          </div>
        )}

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {tab === 'switcher' && (
            <div className="space-y-6">
              <div className="bg-blue-50/60 border border-blue-100 rounded-xl p-4 text-xs text-blue-900 flex items-start space-x-3">
                <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold">True Multi-Tenant Isolation & Role-Based Permissions</p>
                  <p className="text-blue-700">
                    Each company maintains completely isolated clients, vouchers, KYC files, and theme styling. Switch between companies or test different operational roles (Admin, Finance, Operations, Procurement, Client Portal) below.
                  </p>
                </div>
              </div>

              {/* Companies Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {companies.map((company) => {
                  const isCurrentCompany = company.id === currentCompany.id;
                  const companyUsers = allUsers.filter(
                    (u) => u.companyId === company.id && u.status === 'approved'
                  );

                  return (
                    <div
                      key={company.id}
                      className={`rounded-xl border p-4 flex flex-col justify-between transition ${
                        isCurrentCompany
                          ? 'border-blue-500 ring-2 ring-blue-100 bg-blue-50/30'
                          : 'border-slate-200 bg-white hover:border-slate-300 shadow-xs'
                      }`}
                    >
                      <div className="space-y-3">
                        {/* Company Header */}
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2.5">
                            <div
                              className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-xs shadow-xs"
                              style={{ backgroundColor: company.theme.primaryColor }}
                            >
                              {company.name.slice(0, 2).toUpperCase()}
                            </div>
                            <div>
                              <h4 className="text-xs font-bold text-slate-900 leading-tight">
                                {company.name}
                              </h4>
                              <div className="flex items-center space-x-1.5 mt-0.5">
                                <span className="text-[10px] font-mono px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded font-semibold">
                                  {company.companyCode}
                                </span>
                                <button
                                  onClick={() => copyCode(company.companyCode)}
                                  className="text-slate-400 hover:text-slate-600 text-[10px]"
                                  title="Copy company code"
                                >
                                  {copiedCode === company.companyCode ? 'Copied!' : <Copy className="w-3 h-3" />}
                                </button>
                              </div>
                            </div>
                          </div>
                          {isCurrentCompany && (
                            <span className="text-[9px] font-bold px-1.5 py-0.5 bg-blue-600 text-white rounded-full">
                              Active
                            </span>
                          )}
                        </div>

                        {/* Company Info */}
                        <div className="text-[11px] text-slate-500 space-y-0.5 pt-1 border-t border-slate-100 font-mono">
                          <p>TIN: {company.tin}</p>
                          <p className="truncate text-slate-400">{company.phone}</p>
                        </div>

                        {/* Users List for this company */}
                        <div className="space-y-1.5 pt-2">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                            Available Profiles:
                          </p>
                          <div className="space-y-1">
                            {companyUsers.map((user) => {
                              const isCurrentUser = user.id === currentUser.id;
                              const roleBadgeColors: Record<UserRole, string> = {
                                admin: 'bg-rose-100 text-rose-800 border-rose-200',
                                finance: 'bg-emerald-100 text-emerald-800 border-emerald-200',
                                operations: 'bg-blue-100 text-blue-800 border-blue-200',
                                procurement: 'bg-amber-100 text-amber-800 border-amber-200',
                                client_portal: 'bg-purple-100 text-purple-800 border-purple-200',
                              };

                              return (
                                <button
                                  key={user.id}
                                  onClick={() => handleQuickSwitch(company.id, user.id)}
                                  className={`w-full text-left p-2 rounded-lg text-xs flex items-center justify-between transition border ${
                                    isCurrentUser
                                      ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                                      : 'bg-slate-50 hover:bg-slate-100 border-slate-200 text-slate-800'
                                  }`}
                                >
                                  <div className="truncate pr-2">
                                    <p className="font-semibold truncate">{user.name}</p>
                                    <p
                                      className={`text-[10px] truncate ${
                                        isCurrentUser ? 'text-blue-100' : 'text-slate-400'
                                      }`}
                                    >
                                      {user.email}
                                    </p>
                                  </div>
                                  <span
                                    className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded border shrink-0 ${
                                      isCurrentUser
                                        ? 'bg-white/20 text-white border-white/30'
                                        : roleBadgeColors[user.role]
                                    }`}
                                  >
                                    {user.role === 'client_portal' ? 'Client' : user.role}
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {tab === 'register_company' && (
            <form onSubmit={handleRegisterCompanySubmit} className="space-y-6">
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600">
                <p className="font-semibold text-slate-800">New Corporate Tenant Setup</p>
                <p className="mt-0.5">
                  Registering a new company creates a dedicated multi-tenant data container with customized TRA tax settings, bank accounts, and brand styling. You will be assigned as the primary Administrator.
                </p>
              </div>

              {/* Company Details */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Company Legal Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={newCompanyName}
                    onChange={(e) => setNewCompanyName(e.target.value)}
                    placeholder="e.g., Lake Victoria Logistics Ltd"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    TRA Tax Identification Number (TIN) *
                  </label>
                  <input
                    type="text"
                    required
                    value={newCompanyTin}
                    onChange={(e) => setNewCompanyTin(formatTIN(e.target.value))}
                    placeholder="9 Digits (e.g. 109-883-201)"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    VAT Registration Number (VRN - Optional)
                  </label>
                  <input
                    type="text"
                    value={newCompanyVrn}
                    onChange={(e) => setNewCompanyVrn(e.target.value)}
                    placeholder="e.g. 40-029410-X"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Official Telephone
                  </label>
                  <input
                    type="text"
                    value={newCompanyPhone}
                    onChange={(e) => setNewCompanyPhone(e.target.value)}
                    placeholder="+255 22 286 0000"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Physical & Postal Address
                  </label>
                  <input
                    type="text"
                    value={newCompanyAddress}
                    onChange={(e) => setNewCompanyAddress(e.target.value)}
                    placeholder="Plot No, Street, P.O. Box, City, Tanzania"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>
              </div>

              {/* Bank & Theme */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-slate-200">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Bank Name</label>
                  <select
                    value={newCompanyBankName}
                    onChange={(e) => setNewCompanyBankName(e.target.value)}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  >
                    <option value="CRDB Bank Plc">CRDB Bank Plc</option>
                    <option value="NMB Bank Plc">NMB Bank Plc</option>
                    <option value="Stanbic Bank Tanzania">Stanbic Bank Tanzania</option>
                    <option value="Standard Chartered Tanzania">Standard Chartered Tanzania</option>
                    <option value="Absa Bank Tanzania">Absa Bank Tanzania</option>
                    <option value="Exim Bank Tanzania">Exim Bank Tanzania</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Account Number</label>
                  <input
                    type="text"
                    value={newCompanyAccountNo}
                    onChange={(e) => setNewCompanyAccountNo(e.target.value)}
                    placeholder="e.g. 0150389281900"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Brand Theme Color</label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="color"
                      value={newPrimaryColor}
                      onChange={(e) => setNewPrimaryColor(e.target.value)}
                      className="w-8 h-8 rounded border border-slate-300 cursor-pointer p-0.5"
                    />
                    <input
                      type="text"
                      value={newPrimaryColor}
                      onChange={(e) => setNewPrimaryColor(e.target.value)}
                      className="w-full px-2 py-1.5 text-xs font-mono border border-slate-300 rounded-lg"
                    />
                  </div>
                </div>
              </div>

              {/* Initial Admin Details */}
              <div className="pt-4 border-t border-slate-200">
                <h4 className="text-xs font-bold text-slate-900 mb-3 flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-blue-600" />
                  <span>Initial Administrator Profile</span>
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Admin Full Name *</label>
                    <input
                      type="text"
                      required
                      value={newAdminName}
                      onChange={(e) => setNewAdminName(e.target.value)}
                      placeholder="e.g., Frank Mrema"
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Admin Email *</label>
                    <input
                      type="email"
                      required
                      value={newAdminEmail}
                      onChange={(e) => setNewAdminEmail(e.target.value)}
                      placeholder="admin@company.co.tz"
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Mobile Number</label>
                    <input
                      type="text"
                      value={newAdminMobile}
                      onChange={(e) => setNewAdminMobile(e.target.value)}
                      placeholder="+255 754 000 000"
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-4 border-t border-slate-200">
                <button
                  type="submit"
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-md flex items-center space-x-2 transition"
                >
                  <Building2 className="w-4 h-4" />
                  <span>Create Tenant & Sign In as Admin</span>
                </button>
              </div>
            </form>
          )}

          {tab === 'join_company' && (
            <form onSubmit={handleJoinSubmit} className="space-y-6">
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-600">
                <p className="font-semibold text-slate-800">Join an Existing Corporate Workspace</p>
                <p className="mt-0.5">
                  Enter the unique Company Code (e.g. <span className="font-mono font-bold">KILI-2026</span>) provided by your company admin. Your request will be queued for administrator authorization.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Company Code *
                  </label>
                  <input
                    type="text"
                    required
                    value={joinCompanyCode}
                    onChange={(e) => setJoinCompanyCode(e.target.value.toUpperCase())}
                    placeholder="e.g. KILI-2026 or SERE-8840"
                    className="w-full px-3 py-2 text-xs font-mono font-bold border border-slate-300 rounded-lg uppercase tracking-wider focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                  {joinCompanyCode && (
                    <div className="mt-1 text-[11px]">
                      {storage.getCompanyByCode(joinCompanyCode) ? (
                        <span className="text-emerald-700 font-semibold flex items-center space-x-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Found: {storage.getCompanyByCode(joinCompanyCode)?.name}</span>
                        </span>
                      ) : (
                        <span className="text-rose-600">No company registered with this code</span>
                      )}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Account Type *
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setJoinRoleType('staff')}
                      className={`py-2 px-3 text-xs font-semibold rounded-lg border flex items-center justify-center space-x-2 transition ${
                        joinRoleType === 'staff'
                          ? 'bg-blue-50 border-blue-600 text-blue-700'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <Briefcase className="w-3.5 h-3.5" />
                      <span>Staff Member</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setJoinRoleType('client')}
                      className={`py-2 px-3 text-xs font-semibold rounded-lg border flex items-center justify-center space-x-2 transition ${
                        joinRoleType === 'client'
                          ? 'bg-purple-50 border-purple-600 text-purple-700'
                          : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <Users className="w-3.5 h-3.5" />
                      <span>Client Portal</span>
                    </button>
                  </div>
                </div>

                {joinRoleType === 'staff' ? (
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Department / Requested Role *
                    </label>
                    <select
                      value={joinStaffRole}
                      onChange={(e) => setJoinStaffRole(e.target.value as UserRole)}
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    >
                      <option value="operations">Operations (All Vouchers, CRM, Invoices)</option>
                      <option value="finance">Finance (Full Vouchers, CRM, Payment Trends)</option>
                      <option value="procurement">Procurement (LPO Specialist Only)</option>
                      <option value="admin">Administrator (Full Access & Approvals)</option>
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Your Client / Contractor Company Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={joinClientCompanyName}
                      onChange={(e) => setJoinClientCompanyName(e.target.value)}
                      placeholder="e.g. Serengeti Infrastructure Ltd"
                      className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    />
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={joinApplicantName}
                    onChange={(e) => setJoinApplicantName(e.target.value)}
                    placeholder="e.g. Hassan Bakari"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address *</label>
                  <input
                    type="email"
                    required
                    value={joinApplicantEmail}
                    onChange={(e) => setJoinApplicantEmail(e.target.value)}
                    placeholder="hassan.b@example.co.tz"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Mobile Telephone</label>
                  <input
                    type="text"
                    value={joinApplicantMobile}
                    onChange={(e) => setJoinApplicantMobile(e.target.value)}
                    placeholder="+255 754 000 000"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Purpose / Notes for Administrator
                  </label>
                  <textarea
                    rows={2}
                    value={joinNotes}
                    onChange={(e) => setJoinNotes(e.target.value)}
                    placeholder="Briefly state your department, project or trading relationship..."
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-4 border-t border-slate-200">
                <button
                  type="submit"
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-md flex items-center space-x-2 transition"
                >
                  <UserPlus className="w-4 h-4" />
                  <span>Submit Application for Approval</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
