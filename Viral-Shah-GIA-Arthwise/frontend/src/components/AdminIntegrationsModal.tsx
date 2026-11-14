import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, X, Activity, Server, Lock, AlertTriangle, 
  RefreshCw, CheckCircle2, XCircle, Users, UserPlus, KeyRound,
  Eye, EyeOff, Building2, Palette, Upload, Globe, Phone, Mail,
  Image as ImageIcon, Check, MapPin
} from 'lucide-react';
import { ApiClient } from '../api/client';
import { UserRole, CompanyProfile, LocationCity, PANValidationResult } from '../types';

interface AdminIntegrationsModalProps {
  onClose: () => void;
  onCompanyChanged?: () => void;
}

interface PlatformUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export const AdminIntegrationsModal: React.FC<AdminIntegrationsModalProps> = ({ 
  onClose,
  onCompanyChanged
}) => {
  const [activeTab, setActiveTab] = useState<'users' | 'company' | 'audit' | 'integrations'>('users');
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [companies, setCompanies] = useState<CompanyProfile[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [integrations, setIntegrations] = useState<any>(null);
  const [citiesList, setCitiesList] = useState<LocationCity[]>([]);
  const [statesList, setStatesList] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Create User state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newFullName, setNewFullName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState<UserRole>('analyst');
  const [newPassword, setNewPassword] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);

  // Reset Password state
  const [resetTargetUser, setResetTargetUser] = useState<PlatformUser | null>(null);
  const [newResetPassword, setNewResetPassword] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState<string | null>(null);

  // Create White-Label Company state
  const [showCreateCompanyModal, setShowCreateCompanyModal] = useState(false);
  const [compCode, setCompCode] = useState('');
  const [compLegalName, setCompLegalName] = useState('');
  const [compBrandName, setCompBrandName] = useState('');
  const [compTagline, setCompTagline] = useState('');
  const [compLogoData, setCompLogoData] = useState<string | null>(null);
  const [compPrimaryColor, setCompPrimaryColor] = useState('#1b2632');
  const [compSecondaryColor, setCompSecondaryColor] = useState('#a45139');
  const [compAddress, setCompAddress] = useState('');
  const [compCity, setCompCity] = useState('');
  const [compState, setCompState] = useState('');
  const [compPin, setCompPin] = useState('');
  const [compPan, setCompPan] = useState('');
  const [compGstin, setCompGstin] = useState('');
  const [compCin, setCompCin] = useState('');
  const [compEmail, setCompEmail] = useState('');
  const [compPhone, setCompPhone] = useState('');
  const [compWebsite, setCompWebsite] = useState('');
  const [compLoading, setCompLoading] = useState(false);
  const [compError, setCompError] = useState<string | null>(null);
  const [compSuccess, setCompSuccess] = useState<string | null>(null);
  const [compPanValidation, setCompPanValidation] = useState<PANValidationResult | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [userList, compList, logs, intStatus, cts, sts] = await Promise.all([
        ApiClient.request<PlatformUser[]>('/admin/users'),
        ApiClient.request<CompanyProfile[]>('/companies'),
        ApiClient.request<any[]>('/admin/audit-logs'),
        ApiClient.request<any>('/admin/integrations'),
        ApiClient.request<LocationCity[]>('/master/cities?limit=200'),
        ApiClient.request<string[]>('/master/states'),
      ]);
      setUsers(userList);
      setCompanies(compList);
      setAuditLogs(logs);
      setIntegrations(intStatus);
      setCitiesList(cts);
      setStatesList(sts);
    } catch (err: any) {
      console.error('Error fetching admin data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFullName.trim() || !newEmail.trim() || !newPassword.trim()) {
      setCreateError('Please fill in all user profile fields.');
      return;
    }

    setCreateLoading(true);
    setCreateError(null);
    setCreateSuccess(null);

    try {
      const res = await ApiClient.request<PlatformUser>('/admin/users', {
        method: 'POST',
        body: JSON.stringify({
          full_name: newFullName.trim(),
          email: newEmail.trim().toLowerCase(),
          role: newRole,
          password: newPassword.trim(),
        }),
      });

      setCreateSuccess(`User '${res.email}' successfully provisioned as ${res.role}.`);
      setNewFullName('');
      setNewEmail('');
      setNewPassword('');
      setShowCreateModal(false);
      await fetchData();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create user account.');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetTargetUser || !newResetPassword.trim()) {
      setResetError('Please enter a new password (min 6 characters).');
      return;
    }

    setResetLoading(true);
    setResetError(null);

    try {
      await ApiClient.request(`/admin/users/${resetTargetUser.id}/reset-password`, {
        method: 'POST',
        body: JSON.stringify({
          new_password: newResetPassword.trim(),
        }),
      });

      setResetSuccess(`Password for ${resetTargetUser.email} was reset successfully.`);
      setResetTargetUser(null);
      setNewResetPassword('');
      await fetchData();
    } catch (err: any) {
      setResetError(err.message || 'Failed to reset password.');
    } finally {
      setResetLoading(false);
    }
  };

  const handleToggleActive = async (targetUser: PlatformUser) => {
    try {
      await ApiClient.request(`/admin/users/${targetUser.id}/toggle-active`, {
        method: 'PATCH',
      });
      await fetchData();
    } catch (err: any) {
      alert(err.message || 'Failed to update user status.');
    }
  };

  // Logo file upload handler
  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => {
      setCompLogoData(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  // City selection with auto-fill for Company
  const handleCompCityChange = (cityName: string) => {
    setCompCity(cityName);
    const matched = citiesList.find(
      (c) => c.city.trim().toLowerCase() === cityName.trim().toLowerCase()
    );
    if (matched) {
      setCompState(matched.state);
    }
  };

  // PAN validation for Company
  const handleValidateCompPan = async (panStr: string) => {
    const clean = panStr.trim().toUpperCase();
    setCompPan(clean);
    if (clean.length === 10) {
      try {
        const res = await ApiClient.request<PANValidationResult>('/master/pan/validate', {
          method: 'POST',
          body: JSON.stringify({
            pan: clean,
            entity_name: compLegalName,
            constitution: 'pvt_ltd',
          }),
        });
        setCompPanValidation(res);
      } catch (err) {
        console.warn('PAN validation check failed:', err);
      }
    } else {
      setCompPanValidation(null);
    }
  };

  // Create White-Label Company
  const handleCreateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!compCode.trim() || !compLegalName.trim() || !compBrandName.trim()) {
      setCompError('Company Code, Legal Name, and Brand Name are required.');
      return;
    }

    setCompLoading(true);
    setCompError(null);

    try {
      const res = await ApiClient.request<CompanyProfile>('/companies', {
        method: 'POST',
        body: JSON.stringify({
          company_code: compCode.trim().toUpperCase(),
          company_name: compLegalName.trim(),
          brand_name: compBrandName.trim(),
          tagline: compTagline.trim() || 'Loan Proposal Evaluation & Debt Syndication Suite',
          logo_data: compLogoData,
          primary_color: compPrimaryColor,
          secondary_color: compSecondaryColor,
          address: compAddress.trim() || null,
          city: compCity.trim() || null,
          state: compState.trim() || null,
          pin_code: compPin.trim() || null,
          pan: compPan.trim().toUpperCase() || null,
          gstin: compGstin.trim().toUpperCase() || null,
          cin: compCin.trim().toUpperCase() || null,
          email: compEmail.trim() || null,
          phone: compPhone.trim() || null,
          website: compWebsite.trim() || null,
        }),
      });

      setCompSuccess(`New legal entity & company '${res.company_name}' successfully registered!`);
      setShowCreateCompanyModal(false);
      // Reset form
      setCompCode('');
      setCompLegalName('');
      setCompBrandName('');
      setCompTagline('');
      setCompLogoData(null);
      setCompAddress('');
      setCompCity('');
      setCompState('');
      setCompPin('');
      setCompPan('');
      setCompGstin('');
      setCompCin('');
      setCompEmail('');
      setCompPhone('');
      setCompWebsite('');
      await fetchData();
    } catch (err: any) {
      setCompError(err.message || 'Failed to create company profile.');
    } finally {
      setCompLoading(false);
    }
  };

  // Set Active Company
  const handleSetActiveCompany = async (companyId: string) => {
    try {
      const updated = await ApiClient.request<CompanyProfile>(`/companies/${companyId}/set-active`, {
        method: 'POST',
      });
      setCompSuccess(`Active software white-label brand switched to '${updated.brand_name}'!`);
      await fetchData();
      onCompanyChanged?.();
    } catch (err: any) {
      alert(err.message || 'Failed to activate white-label company.');
    }
  };

  const getRoleBadge = (role: UserRole) => {
    switch (role) {
      case 'admin':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">Administrator</span>;
      case 'analyst':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#1b2632] text-white">Senior Analyst</span>;
      case 'reviewer':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#faece7] text-[#a45139] border border-[#f5d7cf]">Credit Reviewer</span>;
      case 'client':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-200">Borrower Client</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700">{role}</span>;
    }
  };

  const activeCompany = companies.find((c) => c.is_active);

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 font-sans">
      <div className="bg-white rounded-2xl max-w-5xl w-full max-h-[92vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Modal Header */}
        <div className="px-6 py-4 bg-[#1b2632] text-white flex items-center justify-between border-b border-[#2a3c4f]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#a45139] text-white flex items-center justify-center shadow-md">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-white">Administrator Governance &amp; White-Label Console</h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#faece7] text-[#a45139]">
                  Strictly Admin Only
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                White-Label Legal Entities, User Provisioning, Credential Resets &amp; Audit Trail
              </p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors cursor-pointer"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Buttons */}
        <div className="px-6 pt-3 bg-slate-50 border-b border-slate-200 flex items-center gap-6 text-xs font-bold overflow-x-auto">
          <button
            onClick={() => setActiveTab('users')}
            className={`pb-2.5 transition-all border-b-2 flex items-center gap-2 cursor-pointer whitespace-nowrap ${
              activeTab === 'users' ? 'border-[#a45139] text-[#a45139]' : 'border-transparent text-slate-500 hover:text-[#1b2632]'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>User Accounts &amp; Passwords ({users.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('company')}
            className={`pb-2.5 transition-all border-b-2 flex items-center gap-2 cursor-pointer whitespace-nowrap ${
              activeTab === 'company' ? 'border-[#a45139] text-[#a45139]' : 'border-transparent text-slate-500 hover:text-[#1b2632]'
            }`}
          >
            <Building2 className="w-4 h-4" />
            <span>White-Label &amp; Companies ({companies.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('audit')}
            className={`pb-2.5 transition-all border-b-2 flex items-center gap-2 cursor-pointer whitespace-nowrap ${
              activeTab === 'audit' ? 'border-[#a45139] text-[#a45139]' : 'border-transparent text-slate-500 hover:text-[#1b2632]'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Immutable Audit Trail ({auditLogs.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('integrations')}
            className={`pb-2.5 transition-all border-b-2 flex items-center gap-2 cursor-pointer whitespace-nowrap ${
              activeTab === 'integrations' ? 'border-[#a45139] text-[#a45139]' : 'border-transparent text-slate-500 hover:text-[#1b2632]'
            }`}
          >
            <Server className="w-4 h-4" />
            <span>Regulated API Adapters &amp; DPDP</span>
          </button>
        </div>

        {/* Notifications */}
        {(createSuccess || resetSuccess || compSuccess) && (
          <div className="px-6 pt-3">
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{createSuccess || resetSuccess || compSuccess}</span>
              </div>
              <button 
                onClick={() => { setCreateSuccess(null); setResetSuccess(null); setCompSuccess(null); }}
                className="text-emerald-700 hover:text-emerald-900 font-bold ml-2 cursor-pointer"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Content Area */}
        <div className="p-6 overflow-y-auto flex-1 text-xs">
          {isLoading ? (
            <div className="text-center py-16 text-slate-400 font-medium">Loading system governance records...</div>
          ) : activeTab === 'users' ? (
            <div className="space-y-4">
              {/* Administrator Governance Notice Banner */}
              <div className="p-3.5 bg-[#faece7] border border-[#f5d7cf] rounded-xl text-xs text-[#a45139] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="w-5 h-5 text-[#a45139] flex-shrink-0" />
                  <div className="text-slate-700">
                    <strong className="text-[#1b2632] block sm:inline mr-1">Administrator Privileges Enforced:</strong>
                    Only Chief Administrators have the rights to create user accounts and reset credentials. Other roles are strictly restricted from user management.
                  </div>
                </div>
                <button
                  onClick={() => { setShowCreateModal(true); setCreateError(null); }}
                  className="px-3.5 py-1.5 bg-[#a45139] hover:bg-[#863e2a] text-white rounded-lg font-bold text-xs shadow-sm transition-all flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  <span>Create User</span>
                </button>
              </div>

              {/* Users Table */}
              <div className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-xs">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[11px] uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">User / Name</th>
                      <th className="py-3 px-4">Role Profile</th>
                      <th className="py-3 px-4">Account Status</th>
                      <th className="py-3 px-4">Created Date</th>
                      <th className="py-3 px-4 text-right">Administrative Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {users.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-bold text-[#1b2632]">{u.full_name}</div>
                          <div className="font-mono text-[11px] text-slate-500">{u.email}</div>
                        </td>
                        <td className="py-3 px-4">
                          {getRoleBadge(u.role)}
                        </td>
                        <td className="py-3 px-4">
                          <button
                            onClick={() => handleToggleActive(u)}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer transition-all ${
                              u.is_active
                                ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200'
                                : 'bg-rose-100 text-rose-800 hover:bg-rose-200'
                            }`}
                            title="Click to toggle account activation status"
                          >
                            {u.is_active ? 'Active' : 'Suspended'}
                          </button>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-500">
                          {new Date(u.created_at).toLocaleDateString('en-IN', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric'
                          })}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              setResetTargetUser(u);
                              setNewResetPassword('');
                              setResetError(null);
                            }}
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold text-[#a45139] hover:text-white bg-[#faece7] hover:bg-[#a45139] border border-[#f5d7cf] rounded-lg transition-all cursor-pointer"
                            title={`Reset password for ${u.email}`}
                          >
                            <KeyRound className="w-3.5 h-3.5" />
                            <span>Reset Password</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : activeTab === 'company' ? (
            <div className="space-y-5">
              {/* White Label Banner */}
              <div className="p-4 bg-gradient-to-r from-slate-900 to-[#1b2632] text-white rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-md">
                <div className="flex items-center gap-3.5">
                  {activeCompany?.logo_data ? (
                    <div className="w-12 h-12 rounded-xl bg-white p-1 flex items-center justify-center shadow-md">
                      <img
                        src={activeCompany.logo_data}
                        alt={activeCompany.brand_name}
                        className="w-full h-full object-contain"
                      />
                    </div>
                  ) : (
                    <div className="w-12 h-12 rounded-xl bg-[#a45139] text-white flex items-center justify-center shadow-md">
                      <Building2 className="w-6 h-6" />
                    </div>
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-base font-black tracking-tight">{activeCompany?.brand_name || 'GIA_Arthwise'}</h4>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        Active Operating Brand
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 mt-0.5">{activeCompany?.company_name}</p>
                    <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1">
                      <span>PAN: <strong>{activeCompany?.pan || 'AAACX0000M'}</strong></span>
                      <span>•</span>
                      <span>GSTIN: <strong>{activeCompany?.gstin || '24AAACX0000M1Z5'}</strong></span>
                      <span>•</span>
                      <span>CIN: <strong>{activeCompany?.cin || 'U00000GJ2000PTC000000'}</strong></span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => { setShowCreateCompanyModal(true); setCompError(null); }}
                  className="px-4 py-2 bg-[#a45139] hover:bg-[#863e2a] text-white rounded-xl font-bold text-xs shadow-md transition-all flex items-center gap-2 cursor-pointer whitespace-nowrap"
                >
                  <Building2 className="w-4 h-4" />
                  <span>+ Create New User Company</span>
                </button>
              </div>

              {/* Companies Directory */}
              <div>
                <h5 className="font-bold text-slate-800 text-xs uppercase tracking-wider mb-3 flex items-center gap-2">
                  <span>Registered Legal Entities &amp; White-Label Tenants ({companies.length})</span>
                </h5>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {companies.map((comp) => (
                    <div
                      key={comp.id}
                      className={`p-4 rounded-xl border bg-white shadow-xs transition-all flex flex-col justify-between ${
                        comp.is_active ? 'border-[#a45139] ring-1 ring-[#a45139]/30' : 'border-slate-200'
                      }`}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="flex items-center gap-2.5">
                            {comp.logo_data ? (
                              <div className="w-9 h-9 rounded-lg bg-slate-50 border border-slate-200 p-0.5 flex items-center justify-center">
                                <img src={comp.logo_data} alt={comp.brand_name} className="w-full h-full object-contain" />
                              </div>
                            ) : (
                              <div className="w-9 h-9 rounded-lg bg-[#1b2632] text-white flex items-center justify-center font-bold text-xs">
                                {comp.company_code.slice(0, 3)}
                              </div>
                            )}
                            <div>
                              <div className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
                                <span>{comp.brand_name}</span>
                                <span className="font-mono text-[10px] text-slate-500 font-normal">[{comp.company_code}]</span>
                              </div>
                              <p className="text-[11px] text-slate-500 leading-tight">{comp.company_name}</p>
                            </div>
                          </div>

                          {comp.is_active ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1">
                              <Check className="w-3 h-3 text-emerald-600" />
                              Active
                            </span>
                          ) : (
                            <button
                              onClick={() => handleSetActiveCompany(comp.id)}
                              className="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-[#faece7] hover:bg-[#a45139] text-[#a45139] hover:text-white transition-all cursor-pointer"
                              title="Set this legal entity as the active operating white label"
                            >
                              Set as Active Brand
                            </button>
                          )}
                        </div>

                        <div className="mt-3 pt-2.5 border-t border-slate-100 grid grid-cols-2 gap-2 text-[11px] text-slate-600">
                          <div>
                            <span className="text-slate-400 block text-[10px]">Location:</span>
                            <span className="font-medium">{comp.city || 'Vadodara'}, {comp.state || 'Gujarat'}</span>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[10px]">PAN / GSTIN:</span>
                            <span className="font-mono text-[10px]">{comp.pan || 'N/A'}</span>
                          </div>
                          {comp.email && (
                            <div className="col-span-2">
                              <span className="text-slate-400 block text-[10px]">Support Contact:</span>
                              <span className="font-mono text-[10px]">{comp.email}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                        <span className="flex items-center gap-1">
                          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: comp.primary_color }} />
                          {comp.primary_color}
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: comp.secondary_color }} />
                          {comp.secondary_color}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : activeTab === 'audit' ? (
            <div className="space-y-3">
              <table className="w-full text-left">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[11px] uppercase">
                  <tr>
                    <th className="py-2.5 px-3">Timestamp</th>
                    <th className="py-2.5 px-3">Actor</th>
                    <th className="py-2.5 px-3">Action</th>
                    <th className="py-2.5 px-3">Resource</th>
                    <th className="py-2.5 px-3">Audit Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50">
                      <td className="py-2 px-3 text-slate-500 whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString('en-IN')}
                      </td>
                      <td className="py-2 px-3 font-sans font-medium text-slate-800">{log.user_email}</td>
                      <td className="py-2 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                          {log.action}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-slate-600">{log.resource_type}</td>
                      <td className="py-2 px-3 font-sans text-slate-700 max-w-xs truncate" title={log.details}>
                        {log.details}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-900 leading-relaxed text-xs">
                <strong>DPDP Act &amp; RBI Compliance Mandate:</strong> External API integrations for PAN, GST, Credit Bureau, and Account Aggregator data retrieval are kept disabled in sandbox mode by default. Core syndication workflows run locally with document upload and native extraction without paid external APIs.
              </div>

              {integrations && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(integrations).map(([key, val]: [string, any]) => (
                    <div key={key} className="p-4 rounded-xl border border-slate-200 bg-white shadow-xs space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 text-xs uppercase tracking-wide">
                          {key.replace(/_/g, ' ')}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            val.status === 'SANDBOX_MOCK'
                              ? 'bg-amber-100 text-amber-800'
                              : val.status === 'ACTIVE'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {val.status}
                        </span>
                      </div>
                      <p className="text-slate-500 text-[11px]">Provider: <strong>{val.provider}</strong></p>
                      <p className="text-slate-600 text-[11px] leading-relaxed">{val.notes}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#1b2632] hover:bg-black text-white rounded-lg text-xs font-semibold shadow-xs cursor-pointer transition-colors"
          >
            Close Settings
          </button>
        </div>
      </div>

      {/* Sub-modal: Create User */}
      {showCreateModal && (
        <div className="fixed inset-0 z-60 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="bg-[#1b2632] text-white p-4 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <UserPlus className="w-4 h-4 text-[#a45139]" />
                <h4 className="font-bold text-sm">Provision New Platform User</h4>
              </div>
              <button 
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="p-5 space-y-3.5">
              {createError && (
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                  <span>{createError}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  placeholder="e.g. Anand Mahindra"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#a45139] focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Email ID</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="e.g. analyst@example.com"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#a45139] focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Role Permission Profile</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as UserRole)}
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#a45139]"
                >
                  <option value="analyst">Senior Debt Analyst (Underwriting &amp; CMA drafting)</option>
                  <option value="reviewer">Credit Reviewer (Approval, Committee Sign-off)</option>
                  <option value="admin">Chief Administrator (Full Access &amp; User Governance)</option>
                  <option value="client">Borrower Client (Self-service Portal)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Initial Password</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 6 characters (e.g. Secure@123)"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#a45139] focus:bg-white"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3.5 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-4 py-1.5 text-xs font-bold text-white bg-[#a45139] hover:bg-[#863e2a] rounded-lg shadow-sm cursor-pointer disabled:opacity-50"
                >
                  {createLoading ? 'Provisioning...' : 'Provision User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sub-modal: Reset Password */}
      {resetTargetUser && (
        <div className="fixed inset-0 z-60 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="bg-[#1b2632] text-white p-4 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <KeyRound className="w-4 h-4 text-[#a45139]" />
                <h4 className="font-bold text-sm">Reset User Password</h4>
              </div>
              <button 
                onClick={() => setResetTargetUser(null)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleResetPassword} className="p-5 space-y-4">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                <div className="text-slate-500">Target User Account:</div>
                <div className="font-bold text-[#1b2632] text-sm mt-0.5">{resetTargetUser.full_name}</div>
                <div className="font-mono text-slate-600 text-[11px]">{resetTargetUser.email}</div>
              </div>

              {resetError && (
                <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                  <span>{resetError}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">New Password</label>
                <div className="relative">
                  <input
                    type={showResetPassword ? 'text' : 'password'}
                    required
                    autoFocus
                    minLength={6}
                    value={newResetPassword}
                    onChange={(e) => setNewResetPassword(e.target.value)}
                    placeholder="Enter new password (min 6 chars)"
                    className="w-full pr-10 pl-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#a45139] focus:bg-white"
                  />
                  <button
                    type="button"
                    onClick={() => setShowResetPassword(!showResetPassword)}
                    className="absolute right-3 top-2 text-slate-400 hover:text-slate-600 p-0.5 cursor-pointer"
                  >
                    {showResetPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setResetTargetUser(null)}
                  className="px-3.5 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resetLoading}
                  className="px-4 py-1.5 text-xs font-bold text-white bg-[#a45139] hover:bg-[#863e2a] rounded-lg shadow-sm cursor-pointer disabled:opacity-50"
                >
                  {resetLoading ? 'Updating...' : 'Confirm Reset'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sub-modal: Create White-Label Company */}
      {showCreateCompanyModal && (
        <div className="fixed inset-0 z-60 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="bg-[#1b2632] text-white p-4 flex items-center justify-between border-b border-[#2a3c4f]">
              <div className="flex items-center gap-2.5">
                <Building2 className="w-5 h-5 text-[#a45139]" />
                <div>
                  <h4 className="font-bold text-sm text-white">Create New User Company / Tenant</h4>
                  <p className="text-[11px] text-slate-300">White-label branding, corporate legal entity &amp; logo</p>
                </div>
              </div>
              <button 
                onClick={() => setShowCreateCompanyModal(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateCompany} className="p-6 overflow-y-auto space-y-4 text-xs">
              {compError && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                  <span>{compError}</span>
                </div>
              )}

              {/* Basic Information */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-1">
                  <label className="block text-xs font-bold text-slate-700 mb-1">Company Code *</label>
                  <input
                    type="text"
                    required
                    maxLength={10}
                    value={compCode}
                    onChange={(e) => setCompCode(e.target.value.toUpperCase())}
                    placeholder="e.g. APEX"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-mono font-bold uppercase"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 mb-1">Software Brand Display Name *</label>
                  <input
                    type="text"
                    required
                    value={compBrandName}
                    onChange={(e) => setCompBrandName(e.target.value)}
                    placeholder="e.g. ApexCapital or FinTrust"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-bold"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Legal Company / Entity Name *</label>
                <input
                  type="text"
                  required
                  value={compLegalName}
                  onChange={(e) => setCompLegalName(e.target.value)}
                  placeholder="e.g. Apex Debt Advisory &amp; Syndication Private Limited"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Marketing Tagline</label>
                <input
                  type="text"
                  value={compTagline}
                  onChange={(e) => setCompTagline(e.target.value)}
                  placeholder="e.g. Institutional Debt Syndication, CMA Models &amp; Banking Advisory"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900"
                />
              </div>

              {/* Logo Upload & Preview */}
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                <label className="block text-xs font-bold text-slate-700">Corporate Logo</label>
                <div className="flex items-center gap-4">
                  {compLogoData ? (
                    <div className="w-16 h-16 rounded-xl bg-white border border-slate-300 p-1 flex items-center justify-center relative shadow-xs">
                      <img src={compLogoData} alt="Logo Preview" className="w-full h-full object-contain" />
                      <button
                        type="button"
                        onClick={() => setCompLogoData(null)}
                        className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-rose-600 text-white rounded-full flex items-center justify-center text-[10px] font-bold"
                        title="Remove logo"
                      >
                        ×
                      </button>
                    </div>
                  ) : (
                    <div className="w-16 h-16 rounded-xl bg-slate-200 border border-dashed border-slate-300 flex flex-col items-center justify-center text-slate-400">
                      <ImageIcon className="w-6 h-6" />
                      <span className="text-[9px] mt-0.5">No Logo</span>
                    </div>
                  )}

                  <div className="flex-1">
                    <label className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 font-semibold cursor-pointer shadow-2xs">
                      <Upload className="w-3.5 h-3.5 text-[#a45139]" />
                      <span>Upload Logo File (PNG / JPG / SVG)</span>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleLogoUpload}
                        className="hidden"
                      />
                    </label>
                    <p className="text-[10px] text-slate-400 mt-1">Recommended: 200x200 square or horizontal logo with transparent background.</p>
                  </div>
                </div>
              </div>

              {/* Brand Colors */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Primary Color</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={compPrimaryColor}
                      onChange={(e) => setCompPrimaryColor(e.target.value)}
                      className="w-8 h-8 rounded-lg cursor-pointer border border-slate-300 p-0.5"
                    />
                    <input
                      type="text"
                      value={compPrimaryColor}
                      onChange={(e) => setCompPrimaryColor(e.target.value)}
                      className="flex-1 px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono text-xs uppercase"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Secondary Color</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={compSecondaryColor}
                      onChange={(e) => setCompSecondaryColor(e.target.value)}
                      className="w-8 h-8 rounded-lg cursor-pointer border border-slate-300 p-0.5"
                    />
                    <input
                      type="text"
                      value={compSecondaryColor}
                      onChange={(e) => setCompSecondaryColor(e.target.value)}
                      className="flex-1 px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-lg font-mono text-xs uppercase"
                    />
                  </div>
                </div>
              </div>

              {/* Statutory Information & PAN Validation */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Company PAN</label>
                  <input
                    type="text"
                    maxLength={10}
                    value={compPan}
                    onChange={(e) => handleValidateCompPan(e.target.value)}
                    placeholder="e.g. AAACX0000M"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-mono uppercase"
                  />
                  {compPanValidation && (
                    <div className={`mt-1 p-1.5 rounded text-[10px] ${
                      compPanValidation.is_valid && compPanValidation.constitution_match
                        ? 'bg-emerald-50 text-emerald-800'
                        : 'bg-amber-50 text-amber-800'
                    }`}>
                      {compPanValidation.pan_type}: {compPanValidation.status}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">GSTIN</label>
                  <input
                    type="text"
                    maxLength={15}
                    value={compGstin}
                    onChange={(e) => setCompGstin(e.target.value.toUpperCase())}
                    placeholder="e.g. 24AAACX0000M1Z5"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-mono uppercase"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Corporate CIN</label>
                  <input
                    type="text"
                    maxLength={25}
                    value={compCin}
                    onChange={(e) => setCompCin(e.target.value.toUpperCase())}
                    placeholder="e.g. U00000GJ2000PTC000000"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-mono uppercase"
                  />
                </div>
              </div>

              {/* Location & Contact with Auto-prompt LOV */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    City <span className="text-[10px] text-slate-400 font-normal">(LOV or new)</span>
                  </label>
                  <input
                    type="text"
                    list="comp-cities-lov"
                    value={compCity}
                    onChange={(e) => handleCompCityChange(e.target.value)}
                    placeholder="e.g. Vadodara"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900"
                  />
                  <datalist id="comp-cities-lov">
                    {citiesList.map((c, i) => (
                      <option key={i} value={c.city}>{c.city} ({c.state})</option>
                    ))}
                  </datalist>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">State</label>
                  <input
                    type="text"
                    list="comp-states-lov"
                    value={compState}
                    onChange={(e) => setCompState(e.target.value)}
                    placeholder="e.g. Gujarat"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900"
                  />
                  <datalist id="comp-states-lov">
                    {statesList.map((s, i) => (
                      <option key={i} value={s} />
                    ))}
                  </datalist>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">PIN Code</label>
                  <input
                    type="text"
                    maxLength={6}
                    value={compPin}
                    onChange={(e) => setCompPin(e.target.value)}
                    placeholder="e.g. 390023"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Registered Address</label>
                <input
                  type="text"
                  value={compAddress}
                  onChange={(e) => setCompAddress(e.target.value)}
                  placeholder="e.g. 123 Example Street"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={compEmail}
                    onChange={(e) => setCompEmail(e.target.value)}
                    placeholder="contact@example.com"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={compPhone}
                    onChange={(e) => setCompPhone(e.target.value)}
                    placeholder="+1 202 555 0101"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Website</label>
                  <input
                    type="url"
                    value={compWebsite}
                    onChange={(e) => setCompWebsite(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-900"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-slate-200 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setShowCreateCompanyModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={compLoading}
                  className="px-5 py-2 text-xs font-bold text-white bg-[#a45139] hover:bg-[#863e2a] rounded-lg shadow-md cursor-pointer disabled:opacity-50"
                >
                  {compLoading ? 'Creating Company...' : 'Save & Register Company'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
