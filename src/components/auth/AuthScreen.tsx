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
  Key,
  Briefcase,
  ChevronRight,
  Globe,
  FileText,
  FileCheck,
  CreditCard,
  Package
} from 'lucide-react';
import { CompanyProfile, User, UserRole } from '../../types';
import { StorageService, formatTIN, validateTIN } from '../../services/storage';

interface AuthScreenProps {
  onLoginSuccess: (user: User) => void;
}

export const AuthScreen: React.FC<AuthScreenProps> = ({ onLoginSuccess }) => {
  const storage = StorageService.getInstance();
  const companies = storage.getCompanies();
  const allUsers = storage.getAllUsersAcrossCompanies();

  const [activeTab, setActiveTab] = useState<'login' | 'register_company' | 'join_company'>('login');

  // Login State
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(companies[0]?.id || 'comp_kilimanjaro');
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('demo123');

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

  // Quick Login Action
  const handleQuickLogin = (user: User) => {
    storage.login(user);
    onLoginSuccess(user);
  };

  const handleStandardLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedbackMsg(null);

    const companyUsers = allUsers.filter((u) => u.companyId === selectedCompanyId && u.status === 'approved');
    const matched = companyUsers.find((u) => u.email.toLowerCase() === loginEmail.trim().toLowerCase());

    if (matched) {
      storage.login(matched);
      onLoginSuccess(matched);
    } else {
      // Pick first user if empty email
      if (!loginEmail.trim() && companyUsers.length > 0) {
        storage.login(companyUsers[0]);
        onLoginSuccess(companyUsers[0]);
      } else {
        setFeedbackMsg({
          type: 'error',
          text: `No active account found with email "${loginEmail}" in the selected company. Try quick login or register.`,
        });
      }
    }
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
          email:
            newCompanyEmail.trim() ||
            `${newAdminEmail.split('@')[0]}@${newCompanyName.toLowerCase().replace(/[^a-z]/g, '')}.co.tz`,
          website: `https://www.${newCompanyName.toLowerCase().replace(/[^a-z]/g, '')}.co.tz`,
          bankDetails: {
            bankName: newCompanyBankName,
            accountName: newCompanyName.trim(),
            accountNumber:
              newCompanyAccountNo.trim() || '0150' + Math.floor(100000000 + Math.random() * 900000000),
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

      storage.login(adminUser);
      onLoginSuccess(adminUser);
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Failed to create new company tenant.' });
    }
  };

  const handleJoinCompanySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFeedbackMsg(null);

    if (!joinCompanyCode.trim()) {
      setFeedbackMsg({ type: 'error', text: 'Please enter the Company Code given by your administrator.' });
      return;
    }
    if (!joinApplicantName.trim() || !joinApplicantEmail.trim()) {
      setFeedbackMsg({ type: 'error', text: 'Please provide your full name and email address.' });
      return;
    }

    const requestedRole: UserRole = joinRoleType === 'client' ? 'client_portal' : joinStaffRole;

    const res = storage.submitSignupRequest({
      companyCode: joinCompanyCode.trim(),
      name: joinApplicantName.trim(),
      email: joinApplicantEmail.trim(),
      mobile: joinApplicantMobile.trim(),
      requestedRole,
      linkedClientName: joinRoleType === 'client' ? joinClientCompanyName.trim() || joinApplicantName.trim() : undefined,
      notes: joinNotes.trim(),
    });

    if (res.success) {
      setFeedbackMsg({
        type: 'success',
        text: `Sign-up request submitted! An email notification has been queued for the Company Administrator to review and approve your account.`,
      });
      setJoinApplicantName('');
      setJoinApplicantEmail('');
      setJoinNotes('');
    } else {
      setFeedbackMsg({ type: 'error', text: res.message });
    }
  };

  const verifiedTargetCompany = joinCompanyCode ? storage.getCompanyByCode(joinCompanyCode) : undefined;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-blue-600 selection:text-white">
      {/* Top Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-black shadow-lg shadow-blue-900/30">
            <Building2 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="font-bold text-base text-white tracking-tight">KiliTrade Enterprise Cloud</h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-blue-950 text-blue-300 border border-blue-800/60 font-semibold">
                Multi-Tenant v3.0
              </span>
            </div>
            <p className="text-xs text-slate-400">Tanzania Trading, Logistics & Invoicing Platform</p>
          </div>
        </div>

        <div className="flex items-center space-x-4 text-xs text-slate-400">
          <div className="flex items-center space-x-1.5 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-300 font-medium">TRA Certified & Isolated</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8 flex flex-col items-center justify-center">
        {/* Hero Tagline */}
        <div className="text-center mb-8 max-w-2xl">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-2">
            Multi-Tenant Business Management & Invoicing
          </h2>
          <p className="text-sm text-slate-400">
            Sign in to your organization tenant or register a new company. Every tenant maintains strict database isolation, custom branding, and role-based governance.
          </p>
        </div>

        {/* Auth Box */}
        <div className="w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-slate-800 bg-slate-950/60 px-4 pt-3 gap-2 overflow-x-auto">
            <button
              onClick={() => {
                setActiveTab('login');
                setFeedbackMsg(null);
              }}
              className={`px-5 py-3 text-xs font-bold rounded-t-xl transition flex items-center space-x-2 border-b-2 ${
                activeTab === 'login'
                  ? 'border-blue-500 text-white bg-slate-900 shadow-sm'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Users className="w-4 h-4 text-blue-400" />
              <span>1. Sign In & Quick Demo Roles</span>
            </button>

            <button
              onClick={() => {
                setActiveTab('register_company');
                setFeedbackMsg(null);
              }}
              className={`px-5 py-3 text-xs font-bold rounded-t-xl transition flex items-center space-x-2 border-b-2 ${
                activeTab === 'register_company'
                  ? 'border-purple-500 text-white bg-slate-900 shadow-sm'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Building2 className="w-4 h-4 text-purple-400" />
              <span>2. Register New Company</span>
            </button>

            <button
              onClick={() => {
                setActiveTab('join_company');
                setFeedbackMsg(null);
              }}
              className={`px-5 py-3 text-xs font-bold rounded-t-xl transition flex items-center space-x-2 border-b-2 ${
                activeTab === 'join_company'
                  ? 'border-emerald-500 text-white bg-slate-900 shadow-sm'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <UserPlus className="w-4 h-4 text-emerald-400" />
              <span>3. Join with Company Code</span>
            </button>
          </div>

          {/* Feedback Banner */}
          {feedbackMsg && (
            <div
              className={`mx-6 mt-4 p-3 rounded-lg text-xs font-medium flex items-center space-x-2 ${
                feedbackMsg.type === 'success'
                  ? 'bg-emerald-950 border border-emerald-800 text-emerald-300'
                  : 'bg-rose-950 border border-rose-800 text-rose-300'
              }`}
            >
              {feedbackMsg.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              )}
              <span>{feedbackMsg.text}</span>
            </div>
          )}

          {/* TAB 1: SIGN IN & QUICK DEMO LOGINS */}
          {activeTab === 'login' && (
            <div className="p-6 space-y-6">
              {/* Quick Demo Logins Matrix */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-400">
                    <Sparkles className="w-4 h-4" />
                    <span>Instant 1-Click Demo Logins by Company & Role</span>
                  </div>
                  <span className="text-[11px] text-slate-400">No passwords required for testing</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {companies.map((company) => {
                    const companyUsers = allUsers.filter(
                      (u) => u.companyId === company.id && u.status === 'approved'
                    );

                    return (
                      <div
                        key={company.id}
                        className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center space-x-2.5 mb-1.5">
                            <div
                              className="w-7 h-7 rounded flex items-center justify-center font-bold text-white text-xs"
                              style={{ backgroundColor: company.theme.primaryColor }}
                            >
                              {company.name.slice(0, 1)}
                            </div>
                            <div className="min-w-0 flex-1">
                              <h3 className="font-bold text-xs text-white truncate" title={company.name}>
                                {company.name}
                              </h3>
                              <p className="text-[10px] text-slate-400 font-mono">
                                Code: <span className="text-blue-400 font-bold">{company.companyCode}</span>
                              </p>
                            </div>
                          </div>
                          <p className="text-[11px] text-slate-400 line-clamp-1">{company.address}</p>
                        </div>

                        {/* Roles List for this Company */}
                        <div className="space-y-1.5 pt-2 border-t border-slate-800">
                          {companyUsers.map((u) => {
                            const getBadgeColor = () => {
                              switch (u.role) {
                                case 'admin':
                                  return 'bg-purple-950 text-purple-300 border-purple-800';
                                case 'finance':
                                  return 'bg-amber-950 text-amber-300 border-amber-800';
                                case 'operations':
                                  return 'bg-blue-950 text-blue-300 border-blue-800';
                                case 'procurement':
                                  return 'bg-cyan-950 text-cyan-300 border-cyan-800';
                                case 'client_portal':
                                  return 'bg-emerald-950 text-emerald-300 border-emerald-800';
                                default:
                                  return 'bg-slate-800 text-slate-300 border-slate-700';
                              }
                            };

                            return (
                              <button
                                key={u.id}
                                onClick={() => handleQuickLogin(u)}
                                className="w-full flex items-center justify-between p-2 rounded-lg bg-slate-800/80 hover:bg-blue-900/60 border border-slate-700/60 hover:border-blue-500 text-left transition group"
                              >
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center space-x-1.5">
                                    <span className="font-semibold text-xs text-slate-200 group-hover:text-white truncate">
                                      {u.name}
                                    </span>
                                  </div>
                                  <p className="text-[10px] text-slate-400 truncate">{u.email}</p>
                                </div>
                                <span
                                  className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase shrink-0 ${getBadgeColor()}`}
                                >
                                  {u.role === 'client_portal' ? 'Client' : u.role}
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Standard Email Login Form */}
              <div className="border-t border-slate-800 pt-5">
                <h3 className="font-bold text-xs uppercase tracking-wider text-slate-400 mb-3">
                  Or Log In with Credentials
                </h3>
                <form onSubmit={handleStandardLogin} className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-1">Select Tenant</label>
                    <select
                      value={selectedCompanyId}
                      onChange={(e) => setSelectedCompanyId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    >
                      {companies.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} ({c.companyCode})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-slate-400 mb-1">Email Address</label>
                    <input
                      type="email"
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      placeholder="e.g. admin@kilimanjaroenergy.co.tz"
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="flex items-end">
                    <button
                      type="submit"
                      className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg text-xs transition flex items-center justify-center space-x-2 shadow-sm"
                    >
                      <span>Sign In to Tenant</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* TAB 2: REGISTER A NEW COMPANY */}
          {activeTab === 'register_company' && (
            <div className="p-6">
              <div className="mb-4 bg-purple-950/40 border border-purple-900/60 p-4 rounded-xl text-xs text-purple-200">
                <div className="font-bold text-sm text-purple-100 flex items-center space-x-1.5 mb-1">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  <span>Create a Brand-New Isolated Corporate Tenant</span>
                </div>
                <p>
                  As the founding registrant, you will be <strong>auto-approved as Company Admin</strong>. A unique Company Code will be generated for your organization so your staff and clients can join.
                </p>
              </div>

              <form onSubmit={handleRegisterCompanySubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Company Info */}
                  <div className="space-y-3 bg-slate-950/50 p-4 rounded-xl border border-slate-800">
                    <h4 className="font-bold text-xs uppercase tracking-wider text-slate-400">
                      Company Profile & Tax Registration
                    </h4>

                    <div>
                      <label className="block text-[11px] font-medium text-slate-300 mb-1">
                        Company Legal Name *
                      </label>
                      <input
                        type="text"
                        value={newCompanyName}
                        onChange={(e) => setNewCompanyName(e.target.value)}
                        placeholder="e.g. Serengeti Haulage & Bitumen Ltd"
                        required
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-[11px] font-medium text-slate-300 mb-1">
                          TRA TIN (9 Digits) *
                        </label>
                        <input
                          type="text"
                          value={newCompanyTin}
                          onChange={(e) => setNewCompanyTin(formatTIN(e.target.value))}
                          placeholder="XXX-XXX-XXX"
                          maxLength={11}
                          required
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-purple-500"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-medium text-slate-300 mb-1">VAT VRN (Optional)</label>
                        <input
                          type="text"
                          value={newCompanyVrn}
                          onChange={(e) => setNewCompanyVrn(e.target.value)}
                          placeholder="40-001928-Z"
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-slate-300 mb-1">Physical Address</label>
                      <input
                        type="text"
                        value={newCompanyAddress}
                        onChange={(e) => setNewCompanyAddress(e.target.value)}
                        placeholder="Plot 42, Kurasini Commercial Area, Dar es Salaam"
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-[11px] font-medium text-slate-300 mb-1">Primary Bank Name</label>
                        <input
                          type="text"
                          value={newCompanyBankName}
                          onChange={(e) => setNewCompanyBankName(e.target.value)}
                          placeholder="CRDB Bank Plc / NMB"
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-medium text-slate-300 mb-1">Bank Account Number</label>
                        <input
                          type="text"
                          value={newCompanyAccountNo}
                          onChange={(e) => setNewCompanyAccountNo(e.target.value)}
                          placeholder="0150123456789"
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-purple-500"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-slate-300 mb-1">Primary Brand Color</label>
                      <div className="flex items-center space-x-3">
                        <input
                          type="color"
                          value={newPrimaryColor}
                          onChange={(e) => setNewPrimaryColor(e.target.value)}
                          className="w-9 h-9 rounded-lg bg-transparent cursor-pointer border border-slate-700"
                        />
                        <span className="font-mono text-xs text-slate-300">{newPrimaryColor}</span>
                      </div>
                    </div>
                  </div>

                  {/* Initial Admin Details */}
                  <div className="space-y-3 bg-slate-950/50 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
                    <div className="space-y-3">
                      <h4 className="font-bold text-xs uppercase tracking-wider text-purple-400">
                        Initial Administrator Account (Auto-Approved)
                      </h4>

                      <div>
                        <label className="block text-[11px] font-medium text-slate-300 mb-1">
                          Administrator Full Name *
                        </label>
                        <input
                          type="text"
                          value={newAdminName}
                          onChange={(e) => setNewAdminName(e.target.value)}
                          placeholder="e.g. Vani Wadhwani / Managing Director"
                          required
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-medium text-slate-300 mb-1">
                          Administrator Email *
                        </label>
                        <input
                          type="email"
                          value={newAdminEmail}
                          onChange={(e) => setNewAdminEmail(e.target.value)}
                          placeholder="e.g. admin@serengetitrade.co.tz"
                          required
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                        />
                      </div>

                      <div>
                        <label className="block text-[11px] font-medium text-slate-300 mb-1">Mobile Contact</label>
                        <input
                          type="text"
                          value={newAdminMobile}
                          onChange={(e) => setNewAdminMobile(e.target.value)}
                          placeholder="+255 754 000 000"
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                        />
                      </div>
                    </div>

                    <div className="pt-4 border-t border-slate-800">
                      <button
                        type="submit"
                        className="w-full py-3 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-lg text-xs transition flex items-center justify-center space-x-2 shadow-lg shadow-purple-900/30"
                      >
                        <Building2 className="w-4 h-4" />
                        <span>Register & Launch Company Tenant</span>
                      </button>
                    </div>
                  </div>
                </div>
              </form>
            </div>
          )}

          {/* TAB 3: JOIN AN EXISTING COMPANY */}
          {activeTab === 'join_company' && (
            <div className="p-6 space-y-4">
              <div className="bg-emerald-950/40 border border-emerald-900/60 p-4 rounded-xl text-xs text-emerald-200">
                <div className="font-bold text-sm text-emerald-100 flex items-center space-x-1.5 mb-1">
                  <UserPlus className="w-4 h-4 text-emerald-400" />
                  <span>Join an Existing Organization with Company Code</span>
                </div>
                <p>
                  Enter the unique <strong>Company Code</strong> given to you by your corporate administrator (e.g.{' '}
                  <code className="bg-emerald-950 px-1 py-0.5 rounded font-mono text-emerald-300">KILI-7890</code>). Sign-ups will be placed in the tenant's Pending Approval queue.
                </p>
              </div>

              <form onSubmit={handleJoinCompanySubmit} className="space-y-4">
                <div className="bg-slate-950/50 p-5 rounded-xl border border-slate-800 space-y-4">
                  {/* Step 1: Code */}
                  <div>
                    <label className="block text-xs font-bold text-slate-200 mb-1">
                      Step 1: Enter Company Code *
                    </label>
                    <div className="flex items-center space-x-3">
                      <input
                        type="text"
                        value={joinCompanyCode}
                        onChange={(e) => setJoinCompanyCode(e.target.value.toUpperCase())}
                        placeholder="e.g. KILI-7890"
                        required
                        className="w-64 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white font-mono tracking-wider placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                      {verifiedTargetCompany && (
                        <div className="flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-950/80 px-3 py-1.5 rounded-lg border border-emerald-800">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Matched: <strong>{verifiedTargetCompany.name}</strong></span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Step 2: Role selection */}
                  <div>
                    <label className="block text-xs font-bold text-slate-200 mb-2">
                      Step 2: Select Account Type *
                    </label>
                    <div className="grid grid-cols-2 gap-3 max-w-md">
                      <button
                        type="button"
                        onClick={() => setJoinRoleType('staff')}
                        className={`p-3 rounded-xl border text-left transition ${
                          joinRoleType === 'staff'
                            ? 'bg-blue-950/80 border-blue-500 text-white shadow-sm'
                            : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
                        }`}
                      >
                        <Briefcase className="w-4 h-4 text-blue-400 mb-1" />
                        <div className="font-bold text-xs">Staff Member</div>
                        <div className="text-[10px] text-slate-400">Procurement / Ops / Finance / Admin</div>
                      </button>

                      <button
                        type="button"
                        onClick={() => setJoinRoleType('client')}
                        className={`p-3 rounded-xl border text-left transition ${
                          joinRoleType === 'client'
                            ? 'bg-emerald-950/80 border-emerald-500 text-white shadow-sm'
                            : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
                        }`}
                      >
                        <Users className="w-4 h-4 text-emerald-400 mb-1" />
                        <div className="font-bold text-xs">Client (Customer)</div>
                        <div className="text-[10px] text-slate-400">Access invoices & PDF toolkit</div>
                      </button>
                    </div>
                  </div>

                  {/* Sub-role if staff */}
                  {joinRoleType === 'staff' && (
                    <div>
                      <label className="block text-xs font-bold text-slate-200 mb-1">
                        Select Staff Department Role *
                      </label>
                      <select
                        value={joinStaffRole}
                        onChange={(e) => setJoinStaffRole(e.target.value as UserRole)}
                        className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                      >
                        <option value="operations">Operations (Invoicing, Delivery Notes, CRM, Repeat Orders)</option>
                        <option value="finance">Finance (All Vouchers, Payment Trends, CRM, KYC)</option>
                        <option value="procurement">Procurement (Vendor Purchase Orders Only & Sourcing)</option>
                        <option value="admin">Admin (Full Root Access & Tenant Branding)</option>
                      </select>
                    </div>
                  )}

                  {joinRoleType === 'client' && (
                    <div>
                      <label className="block text-xs font-bold text-slate-200 mb-1">
                        Client Organization / Company Name *
                      </label>
                      <input
                        type="text"
                        value={joinClientCompanyName}
                        onChange={(e) => setJoinClientCompanyName(e.target.value)}
                        placeholder="e.g. Mwanza Road Contractors Ltd"
                        required
                        className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  )}

                  {/* Applicant Details */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] font-medium text-slate-300 mb-1">Your Full Name *</label>
                      <input
                        type="text"
                        value={joinApplicantName}
                        onChange={(e) => setJoinApplicantName(e.target.value)}
                        placeholder="e.g. Daudi Kibona"
                        required
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-slate-300 mb-1">Your Work Email *</label>
                      <input
                        type="email"
                        value={joinApplicantEmail}
                        onChange={(e) => setJoinApplicantEmail(e.target.value)}
                        placeholder="e.g. daudi@company.co.tz"
                        required
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-slate-300 mb-1">Mobile Number</label>
                      <input
                        type="text"
                        value={joinApplicantMobile}
                        onChange={(e) => setJoinApplicantMobile(e.target.value)}
                        placeholder="+255 754 000 000"
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-slate-300 mb-1">
                      Applicant Remarks / Department Notes
                    </label>
                    <input
                      type="text"
                      value={joinNotes}
                      onChange={(e) => setJoinNotes(e.target.value)}
                      placeholder="e.g. Joining as Senior Logistics Coordinator / Fuel Officer"
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <div className="pt-2">
                    <button
                      type="submit"
                      className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs transition flex items-center space-x-2 shadow-md"
                    >
                      <UserPlus className="w-4 h-4" />
                      <span>Submit Sign-Up for Admin Approval</span>
                    </button>
                  </div>
                </div>
              </form>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 px-6 py-3 text-center text-xs text-slate-400">
        Multi-Tenant Cloud Platform &copy; 2026. Data strictly isolated per Company ID. TRA Compliant.
      </footer>
    </div>
  );
};
