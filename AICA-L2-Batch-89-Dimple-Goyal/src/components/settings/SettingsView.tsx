import React, { useState } from 'react';
import {
  Settings,
  Building2,
  Sliders,
  Users,
  ShieldCheck,
  Save,
  CheckCircle2,
  Clock,
  Scale,
  Edit2,
  Check,
  X,
  UserPlus,
  UserCheck,
  Sparkles,
  Lock,
  Key,
  Eye,
  EyeOff,
  Plus,
  ArrowRight,
  MapPin,
  Briefcase
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { UserRole, User, Company } from '../../types';
import { AddCompanyModal } from '../company/AddCompanyModal';

export const SettingsView: React.FC = () => {
  const {
    company,
    companies,
    activeCompanyId,
    switchCompany,
    addCompany,
    updateCompany,
    currentUser,
    setCurrentUserRole,
    users,
    updateUserName,
    updateUser,
    addUser,
    updateUserPassword
  } = useApp();

  const [activeTab, setActiveTab] = useState<'companies' | 'company' | 'reconciliation' | 'users'>('companies');
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [userSuccessMessage, setUserSuccessMessage] = useState<string | null>(null);

  // Multi-Company modal
  const [showAddCompanyModal, setShowAddCompanyModal] = useState(false);

  // User editing states
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editingNameValue, setEditingNameValue] = useState('');

  // Password editing states
  const [changingPassUserId, setChangingPassUserId] = useState<string | null>(null);
  const [newPasswordInput, setNewPasswordInput] = useState('');
  const [showPasswordsInTable, setShowPasswordsInTable] = useState<{ [id: string]: boolean }>({});

  // Add new user states
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUserName, setNewUserName] = useState('');
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserId, setNewUserId] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserRole, setNewUserRole] = useState<UserRole>('Accountant');
  const [newUserCompany, setNewUserCompany] = useState<string>('*');

  // Quick edit for active user
  const [isEditingActiveUser, setIsEditingActiveUser] = useState(false);
  const [activeUserNameInput, setActiveUserNameInput] = useState(currentUser.name);

  // Form states for Active Company Profile
  const [compName, setCompName] = useState(company.name);
  const [legalName, setLegalName] = useState(company.legalName);
  const [gstin, setGstin] = useState(company.gstin);
  const [pan, setPan] = useState(company.pan);
  const [tan, setTan] = useState(company.tan || '');
  const [msme, setMsme] = useState(company.msmeRegNo || '');
  const [state, setState] = useState(company.state);
  const [fy, setFy] = useState(company.financialYear || '2026-27');

  // Tolerances
  const [amountTol, setAmountTol] = useState(10);
  const [dateTol, setDateTol] = useState(15);
  const [autoMatchThreshold, setAutoMatchThreshold] = useState(90);

  const handleSaveCompany = (e: React.FormEvent) => {
    e.preventDefault();
    updateCompany({
      name: compName,
      legalName,
      gstin,
      pan,
      tan,
      msmeRegNo: msme,
      state,
      financialYear: fy
    });
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const handlePasswordSubmit = (targetUserId: string) => {
    if (!newPasswordInput.trim()) return;
    updateUserPassword(targetUserId, newPasswordInput.trim());
    setUserSuccessMessage(`Updated password for user.`);
    setChangingPassUserId(null);
    setNewPasswordInput('');
    setTimeout(() => setUserSuccessMessage(null), 3000);
  };

  const togglePasswordVisibility = (id: string) => {
    setShowPasswordsInTable(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">System & Company Settings</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage multi-company entities, active corporate profile, user ID credentials, and statutory tolerances.
          </p>
        </div>
        {savedSuccess && (
          <div className="flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200">
            <CheckCircle2 className="w-4 h-4" />
            <span>Settings Saved!</span>
          </div>
        )}
      </div>

      {/* Settings Tab Navigation */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-xl px-5 text-xs font-semibold gap-4 shadow-xs overflow-x-auto">
        {[
          { id: 'companies', label: `Companies & Entities (${companies.length})`, icon: Building2 },
          { id: 'company', label: 'Active Company Profile', icon: Briefcase },
          { id: 'reconciliation', label: 'Reconciliation Rules & Tolerances', icon: Sliders },
          { id: 'users', label: `User IDs & Security (${users.length})`, icon: Users }
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3.5 border-b-2 flex items-center gap-2 whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'border-emerald-600 text-emerald-700 font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab 1: Multi-Company Management */}
      {activeTab === 'companies' && (
        <div className="bg-white rounded-b-xl border border-t-0 border-slate-200 p-6 space-y-6 text-xs shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-slate-900 text-sm">Configured Companies & Branches ({companies.length})</h3>
              <p className="text-slate-500 text-xs mt-0.5">
                Switch active books to reconcile customer receivables, bank entries, and GSTIN filings for each corporate entity.
              </p>
            </div>
            <button
              onClick={() => setShowAddCompanyModal(true)}
              className="px-3.5 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold text-xs flex items-center gap-1.5 shadow-xs transition-colors shrink-0"
            >
              <Plus className="w-4 h-4" />
              <span>Add New Company</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {companies.map((comp) => {
              const isActive = comp.id === activeCompanyId;
              return (
                <div
                  key={comp.id}
                  className={`p-4 rounded-xl border flex flex-col justify-between transition-all ${
                    isActive
                      ? 'bg-emerald-50/60 border-emerald-400 ring-2 ring-emerald-500/20 shadow-xs'
                      : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="w-9 h-9 rounded-xl bg-slate-900 text-white flex items-center justify-center font-bold text-sm shadow-xs">
                        {comp.name.charAt(0)}
                      </div>
                      {isActive ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-700 text-white flex items-center gap-1 shadow-2xs">
                          <Check className="w-3 h-3" />
                          Active Books
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                          {comp.businessType || 'Entity'}
                        </span>
                      )}
                    </div>

                    <h4 className="font-bold text-slate-900 text-sm mb-0.5">{comp.name}</h4>
                    <p className="text-slate-500 text-[11px] truncate mb-3">{comp.legalName}</p>

                    <div className="space-y-1.5 pt-2.5 border-t border-slate-100 text-[11px] text-slate-600">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">GSTIN:</span>
                        <span className="font-mono font-semibold text-slate-800">{comp.gstin}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">PAN:</span>
                        <span className="font-mono font-semibold text-slate-800">{comp.pan}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">State:</span>
                        <span>{comp.state} ({comp.stateCode})</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Period:</span>
                        <span className="font-bold text-emerald-800">FY {comp.financialYear || '2026-27'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-[10px] text-slate-400">
                      TDS: {comp.defaultTdsSection} ({comp.defaultTdsRate}%)
                    </span>
                    {isActive ? (
                      <span className="text-emerald-700 font-bold text-xs">Currently Selected</span>
                    ) : (
                      <button
                        onClick={() => switchCompany(comp.id)}
                        className="px-3 py-1.5 text-xs font-bold text-slate-700 hover:text-white bg-slate-100 hover:bg-emerald-700 rounded-lg transition-colors flex items-center gap-1 shadow-2xs"
                      >
                        <span>Switch</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: Company Profile */}
      {activeTab === 'company' && (
        <form onSubmit={handleSaveCompany} className="bg-white rounded-b-xl border border-t-0 border-slate-200 p-6 space-y-5 text-xs shadow-xs">
          <div className="p-3 bg-emerald-50/60 border border-emerald-200 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4 text-emerald-700" />
              <span className="text-xs font-bold text-emerald-900">
                Currently Editing Profile for: <strong>{company.name}</strong> ({company.gstin})
              </span>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-200/60 text-emerald-900">
              FY {company.financialYear}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Company Display Name</label>
              <input
                type="text"
                value={compName}
                onChange={e => setCompName(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Legal Registered Entity Name</label>
              <input
                type="text"
                value={legalName}
                onChange={e => setLegalName(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">15-Digit GSTIN</label>
              <input
                type="text"
                value={gstin}
                onChange={e => setGstin(e.target.value.toUpperCase())}
                className="w-full p-2.5 rounded-lg border border-slate-200 font-mono focus:border-emerald-600 outline-hidden"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">10-Digit PAN</label>
              <input
                type="text"
                value={pan}
                onChange={e => setPan(e.target.value.toUpperCase())}
                className="w-full p-2.5 rounded-lg border border-slate-200 font-mono focus:border-emerald-600 outline-hidden"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Tax Deduction TAN</label>
              <input
                type="text"
                value={tan}
                onChange={e => setTan(e.target.value.toUpperCase())}
                className="w-full p-2.5 rounded-lg border border-slate-200 font-mono focus:border-emerald-600 outline-hidden"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">MSME Udyam Reg. No.</label>
              <input
                type="text"
                value={msme}
                onChange={e => setMsme(e.target.value)}
                placeholder="UDYAM-MH-12-0012345"
                className="w-full p-2.5 rounded-lg border border-slate-200 font-mono focus:border-emerald-600 outline-hidden"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Registered State</label>
              <input
                type="text"
                value={state}
                onChange={e => setState(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Financial Year</label>
              <input
                type="text"
                value={fy}
                readOnly
                className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-100 font-bold text-slate-800 cursor-not-allowed"
              />
            </div>
          </div>

          <div className="pt-3 border-t border-slate-200 flex justify-end">
            <button
              type="submit"
              className="px-5 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold flex items-center gap-1.5 shadow-xs"
            >
              <Save className="w-4 h-4" />
              <span>Save Company Details</span>
            </button>
          </div>
        </form>
      )}

      {/* Tab 3: Reconciliation Tolerances */}
      {activeTab === 'reconciliation' && (
        <div className="bg-white rounded-b-xl border border-t-0 border-slate-200 p-6 space-y-6 text-xs shadow-xs">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="font-bold text-slate-900 block mb-1">
                Amount Variance Tolerance (₹)
              </label>
              <p className="text-[11px] text-slate-500 mb-2">
                Permitted rounding difference for bank charges, penny adjustments, or TDS rounding off.
              </p>
              <select
                value={amountTol}
                onChange={e => setAmountTol(Number(e.target.value))}
                className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-50 font-semibold"
              >
                <option value={1}>₹1.00 (Exact matching)</option>
                <option value={10}>₹10.00 (Standard SME tolerance)</option>
                <option value={50}>₹50 (Bank IMPS / RTGS Surcharge)</option>
                <option value={100}>₹100 (Maximum Permitted)</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-slate-900 block mb-1">
                Date Proximity Window (Days)
              </label>
              <p className="text-[11px] text-slate-500 mb-2">
                Allowable days difference between Invoice Due Date and Bank Receipt credit for proximity scoring.
              </p>
              <select
                value={dateTol}
                onChange={e => setDateTol(Number(e.target.value))}
                className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-50 font-semibold"
              >
                <option value={7}>± 7 Days</option>
                <option value={15}>± 15 Days (Recommended)</option>
                <option value={30}>± 30 Days</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-slate-900 block mb-1">
                Auto-Approval Confidence Threshold (%)
              </label>
              <p className="text-[11px] text-slate-500 mb-2">
                Only matches with a confidence score equal to or exceeding this threshold can be auto-approved in bulk.
              </p>
              <select
                value={autoMatchThreshold}
                onChange={e => setAutoMatchThreshold(Number(e.target.value))}
                className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-50 font-semibold"
              >
                <option value={95}>95% (High Safety - Exact Inv No & TDS match only)</option>
                <option value={90}>90% (Standard SME Default)</option>
                <option value={85}>85% (Includes high-confidence customer alias matches)</option>
              </select>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-200 flex justify-end">
            <button
              onClick={() => {
                setSavedSuccess(true);
                setTimeout(() => setSavedSuccess(false), 2000);
              }}
              className="px-5 py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold flex items-center gap-1.5 shadow-xs"
            >
              <Save className="w-4 h-4" />
              <span>Update Tolerance Settings</span>
            </button>
          </div>
        </div>
      )}

      {/* Tab 4: Users, Passwords & Access Control */}
      {activeTab === 'users' && (
        <div className="bg-white rounded-b-xl border border-t-0 border-slate-200 p-6 space-y-6 text-xs shadow-xs">
          {userSuccessMessage && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 font-bold flex items-center justify-between animate-in fade-in duration-150">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{userSuccessMessage}</span>
              </div>
              <button
                onClick={() => setUserSuccessMessage(null)}
                className="text-emerald-700 hover:text-emerald-900 text-xs"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Active Session Card */}
          <div className="p-4 bg-gradient-to-r from-emerald-50/90 to-teal-50/70 rounded-xl border border-emerald-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-slate-900 text-white font-bold text-lg flex items-center justify-center shadow-xs">
                {currentUser.name.charAt(0)}
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800">Currently Logged In As</span>
                <div className="flex items-center gap-2">
                  <p className="font-bold text-slate-900 text-base">{currentUser.name}</p>
                  <span className="font-mono text-xs bg-emerald-100 text-emerald-900 px-2 py-0.5 rounded font-bold">
                    ID: {currentUser.userId}
                  </span>
                </div>
                <p className="text-emerald-800 text-[11px] font-medium">
                  {currentUser.email} • Role: <strong className="font-bold text-emerald-950">{currentUser.role}</strong>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setChangingPassUserId(currentUser.id);
                  setNewPasswordInput('');
                }}
                className="px-3 py-1.5 bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-300 rounded-lg font-bold text-xs transition-colors flex items-center gap-1.5 shadow-2xs"
              >
                <Key className="w-3.5 h-3.5" />
                <span>Change My Password</span>
              </button>
            </div>
          </div>

          {/* Change Password Inline Dialog */}
          {changingPassUserId && (
            <div className="p-4 bg-slate-50 border border-slate-300 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-emerald-700" />
                  <span className="font-bold text-slate-900 text-xs">
                    Change Password for User: <span className="font-mono text-emerald-800">{users.find(u => u.id === changingPassUserId)?.userId}</span>
                  </span>
                </div>
                <button onClick={() => setChangingPassUserId(null)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newPasswordInput}
                  onChange={(e) => setNewPasswordInput(e.target.value)}
                  placeholder="Enter new confidential password (e.g. Pass@2026)"
                  className="flex-1 p-2 bg-white border border-slate-300 rounded-lg text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
                <button
                  onClick={() => handlePasswordSubmit(changingPassUserId)}
                  className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white font-bold rounded-lg text-xs shadow-xs"
                >
                  Save Password
                </button>
                <button
                  onClick={() => setChangingPassUserId(null)}
                  className="px-3 py-2 bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs hover:bg-slate-300"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Organization Users List */}
          <div className="space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h4 className="font-bold text-slate-900 text-sm tracking-tight">Organization Users & Login IDs ({users.length})</h4>
                <p className="text-slate-500 text-xs mt-0.5">
                  Each user can sign in using their unique User ID and Password.
                </p>
              </div>
              <button
                onClick={() => setShowAddUserModal(true)}
                className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-bold text-xs flex items-center gap-1.5 shadow-xs transition-colors self-start sm:self-auto"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Add User ID</span>
              </button>
            </div>

            <div className="border border-slate-200 rounded-xl overflow-hidden shadow-xs">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    <th className="py-3 px-4">User Name</th>
                    <th className="py-3 px-4">User ID (Login)</th>
                    <th className="py-3 px-4">Password</th>
                    <th className="py-3 px-4">Role</th>
                    <th className="py-3 px-4">Assigned Companies</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.map((u) => {
                    const isEditingThisUser = editingUserId === u.id;
                    const isActive = currentUser.id === u.id;
                    const isPassVisible = !!showPasswordsInTable[u.id];

                    const roleBadgeColor =
                      u.role === 'Business Owner'
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        : u.role === 'Finance Manager'
                        ? 'bg-blue-50 text-blue-800 border-blue-200'
                        : u.role === 'Accountant'
                        ? 'bg-purple-50 text-purple-800 border-purple-200'
                        : u.role === 'CA / Consultant'
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-slate-100 text-slate-700 border-slate-200';

                    return (
                      <tr key={u.id} className={`hover:bg-slate-50/70 transition-colors ${isActive ? 'bg-emerald-50/20' : ''}`}>
                        <td className="py-3 px-4">
                          {isEditingThisUser ? (
                            <div className="flex items-center gap-2">
                              <input
                                type="text"
                                value={editingNameValue}
                                onChange={(e) => setEditingNameValue(e.target.value)}
                                className="px-2 py-1 text-xs font-bold text-slate-900 bg-white border border-emerald-500 rounded-lg focus:outline-none"
                                autoFocus
                              />
                              <button
                                onClick={() => {
                                  if (editingNameValue.trim()) {
                                    updateUserName(u.id, editingNameValue.trim());
                                    setEditingUserId(null);
                                    setUserSuccessMessage(`Updated name to "${editingNameValue.trim()}"`);
                                    setTimeout(() => setUserSuccessMessage(null), 3000);
                                  }
                                }}
                                className="p-1 bg-emerald-700 text-white rounded"
                              >
                                <Check className="w-3 h-3" />
                              </button>
                              <button onClick={() => setEditingUserId(null)} className="p-1 bg-slate-200 text-slate-700 rounded">
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2.5">
                              <div className="w-7 h-7 rounded-full bg-slate-800 text-white text-xs font-bold flex items-center justify-center shrink-0">
                                {u.name.charAt(0)}
                              </div>
                              <span className="font-bold text-slate-900 text-xs">{u.name}</span>
                              {isActive && (
                                <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-1.5 py-0.2 rounded border border-emerald-200">
                                  You
                                </span>
                              )}
                            </div>
                          )}
                        </td>

                        <td className="py-3 px-4 font-mono font-bold text-emerald-800 text-xs">
                          {u.userId || u.email.split('@')[0]}
                        </td>

                        <td className="py-3 px-4 font-mono text-[11px] text-slate-600">
                          <div className="flex items-center gap-1.5">
                            <span>{isPassVisible ? (u.password || 'Admin@2026') : '••••••••'}</span>
                            <button
                              onClick={() => togglePasswordVisibility(u.id)}
                              className="text-slate-400 hover:text-slate-700 p-0.5"
                              title={isPassVisible ? 'Hide Password' : 'Show Password'}
                            >
                              {isPassVisible ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </td>

                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border uppercase tracking-wider ${roleBadgeColor}`}>
                            {u.role}
                          </span>
                        </td>

                        <td className="py-3 px-4 text-slate-600 font-medium">
                          {!u.assignedCompanies || u.assignedCompanies.includes('*') ? (
                            <span className="text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                              All Companies ({companies.length})
                            </span>
                          ) : (
                            <span>{u.assignedCompanies.length} Entities</span>
                          )}
                        </td>

                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => {
                                setChangingPassUserId(u.id);
                                setNewPasswordInput('');
                              }}
                              className="px-2 py-1 text-slate-700 hover:bg-slate-100 border border-slate-200 rounded font-semibold text-[11px] transition-colors flex items-center gap-1"
                              title="Change Password"
                            >
                              <Key className="w-3 h-3 text-slate-500" />
                              <span>Pass</span>
                            </button>

                            {!isEditingThisUser && (
                              <button
                                onClick={() => {
                                  setEditingUserId(u.id);
                                  setEditingNameValue(u.name);
                                }}
                                className="px-2 py-1 text-slate-700 hover:text-emerald-800 hover:bg-emerald-50 border border-slate-200 rounded font-semibold text-[11px] transition-colors flex items-center gap-1"
                                title="Edit Name"
                              >
                                <Edit2 className="w-3 h-3" />
                                <span>Name</span>
                              </button>
                            )}

                            {!isActive && (
                              <button
                                onClick={() => {
                                  setCurrentUserRole(u.role);
                                  setUserSuccessMessage(`Switched active user to ${u.name} (${u.role})`);
                                  setTimeout(() => setUserSuccessMessage(null), 3000);
                                }}
                                className="px-2 py-1 text-emerald-800 hover:bg-emerald-50 border border-emerald-300 rounded font-bold text-[11px] transition-colors flex items-center gap-1"
                                title="Switch to this user session"
                              >
                                <UserCheck className="w-3 h-3" />
                                <span>Switch</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Add User Modal */}
          {showAddUserModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
              <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <UserPlus className="w-5 h-5 text-emerald-600" />
                    <h3 className="font-bold text-slate-900 text-sm">Add New User ID & Password</h3>
                  </div>
                  <button onClick={() => setShowAddUserModal(false)} className="text-slate-400 hover:text-slate-600">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!newUserName.trim() || !newUserEmail.trim()) return;
                    const generatedId = newUserId.trim() || newUserName.toLowerCase().replace(/\s+/g, '.');
                    const generatedPass = newUserPassword.trim() || 'User@2026';
                    addUser({
                      name: newUserName.trim(),
                      email: newUserEmail.trim(),
                      userId: generatedId,
                      password: generatedPass,
                      role: newUserRole,
                      assignedCompanies: newUserCompany === '*' ? ['*'] : [newUserCompany]
                    });
                    setUserSuccessMessage(`Created user "${newUserName.trim()}" with User ID: ${generatedId}`);
                    setShowAddUserModal(false);
                    setNewUserName('');
                    setNewUserEmail('');
                    setNewUserId('');
                    setNewUserPassword('');
                    setTimeout(() => setUserSuccessMessage(null), 3500);
                  }}
                  className="space-y-3.5 text-xs"
                >
                  <div>
                    <label className="font-bold text-slate-800 block mb-1">Full Name *</label>
                    <input
                      type="text"
                      required
                      value={newUserName}
                      onChange={(e) => {
                        setNewUserName(e.target.value);
                        if (!newUserId) {
                          setNewUserId(e.target.value.toLowerCase().replace(/\s+/g, '.'));
                        }
                      }}
                      placeholder="e.g. Priya Nair"
                      className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="font-bold text-slate-800 block mb-1">User ID (Login) *</label>
                      <input
                        type="text"
                        required
                        value={newUserId}
                        onChange={(e) => setNewUserId(e.target.value.toLowerCase().trim())}
                        placeholder="e.g. priya.nair"
                        className="w-full p-2.5 font-mono rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                    </div>
                    <div>
                      <label className="font-bold text-slate-800 block mb-1">Password *</label>
                      <input
                        type="text"
                        required
                        value={newUserPassword}
                        onChange={(e) => setNewUserPassword(e.target.value)}
                        placeholder="e.g. Pass@2026"
                        className="w-full p-2.5 font-mono rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="font-bold text-slate-800 block mb-1">Email Address *</label>
                    <input
                      type="email"
                      required
                      value={newUserEmail}
                      onChange={(e) => setNewUserEmail(e.target.value)}
                      placeholder="e.g. priya.nair@company.in"
                      className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="font-bold text-slate-800 block mb-1">Assigned Role</label>
                      <select
                        value={newUserRole}
                        onChange={(e) => setNewUserRole(e.target.value as UserRole)}
                        className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-50 font-semibold"
                      >
                        <option value="Business Owner">Business Owner</option>
                        <option value="Finance Manager">Finance Manager</option>
                        <option value="Accountant">Accountant</option>
                        <option value="CA / Consultant">CA / Consultant</option>
                        <option value="Viewer">Viewer</option>
                      </select>
                    </div>

                    <div>
                      <label className="font-bold text-slate-800 block mb-1">Company Access</label>
                      <select
                        value={newUserCompany}
                        onChange={(e) => setNewUserCompany(e.target.value)}
                        className="w-full p-2.5 rounded-lg border border-slate-200 bg-slate-50 font-semibold"
                      >
                        <option value="*">All Companies (*)</option>
                        {companies.map(c => (
                          <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setShowAddUserModal(false)}
                      className="px-4 py-2 border border-slate-200 rounded-lg font-bold text-slate-600 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold shadow-xs"
                    >
                      Save User Credentials
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add Company Modal */}
      <AddCompanyModal
        isOpen={showAddCompanyModal}
        onClose={() => setShowAddCompanyModal(false)}
        onAddCompany={(newComp, seedData) => addCompany(newComp, seedData)}
      />
    </div>
  );
};
