import React, { useEffect, useState } from 'react';
import type { User, UserRole } from '../types';
import { fetchUsers, createUser, updateUser, deleteUser, resetPassword, changePassword } from '../services/api';
import { Users, UserPlus, Key, ShieldAlert, CheckCircle, XCircle, Search, RefreshCw, Lock, Mail, Phone } from 'lucide-react';


interface UsersPageProps {
  currentUser: User | null;
}

const ROLES: UserRole[] = [
  'System Administrator',
  'Partner',
  'Director',
  'Manager',
  'Assistant Manager',
  'Executive',
  'Article Assistant',
  'Viewer'
];

export const UsersPage: React.FC<UsersPageProps> = ({ currentUser }) => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showResetModal, setShowResetModal] = useState<User | null>(null);
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);

  // Form states
  const [createForm, setCreateForm] = useState({
    employee_code: '',
    name: '',
    email: '',
    mobile: '',
    department: 'Audit & Assurance',
    role: 'Executive' as UserRole,
    password: '',
  });

  const [resetPassInput, setResetPassInput] = useState('');
  const [changePassForm, setChangePassForm] = useState({ old_password: '', new_password: '' });
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const isAdmin = currentUser?.role === 'System Administrator';

  const loadData = async () => {
    setLoading(true);
    setActionError(null);
    try {
      const data = await fetchUsers();
      setUsers(data);
    } catch (e: any) {
      setActionError(e.message || 'Failed to load user directory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setActionSuccess(null);
    try {
      await createUser(createForm);
      setActionSuccess(`User ${createForm.name} (${createForm.employee_code}) created successfully.`);
      setShowCreateModal(false);
      setCreateForm({
        employee_code: '',
        name: '',
        email: '',
        mobile: '',
        department: 'Audit & Assurance',
        role: 'Executive',
        password: '',
      });
      loadData();
    } catch (e: any) {
      setActionError(e.message || 'Failed to create user');
    }
  };

  const handleToggleStatus = async (user: User) => {
    if (!isAdmin) return;
    setActionError(null);
    try {
      if (user.is_active) {
        await deleteUser(user.id);
        setActionSuccess(`User ${user.name} deactivated.`);
      } else {
        await updateUser(user.id, { is_active: true });
        setActionSuccess(`User ${user.name} activated.`);
      }
      loadData();
    } catch (e: any) {
      setActionError(e.message || 'Action failed');
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!showResetModal) return;
    setActionError(null);
    try {
      await resetPassword(showResetModal.id, resetPassInput);
      setActionSuccess(`Password for ${showResetModal.name} reset successfully.`);
      setShowResetModal(null);
      setResetPassInput('');
    } catch (e: any) {
      setActionError(e.message || 'Password reset failed');
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    try {
      await changePassword(changePassForm.old_password, changePassForm.new_password);
      setActionSuccess('Your password has been changed successfully.');
      setShowChangePasswordModal(false);
      setChangePassForm({ old_password: '', new_password: '' });
    } catch (e: any) {
      setActionError(e.message || 'Password change failed');
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.employee_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.department.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesRole = roleFilter === 'ALL' || u.role === roleFilter;
    const matchesStatus =
      statusFilter === 'ALL' ||
      (statusFilter === 'ACTIVE' && u.is_active) ||
      (statusFilter === 'INACTIVE' && !u.is_active);

    return matchesSearch && matchesRole && matchesStatus;
  });

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'System Administrator':
        return 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-800';
      case 'Partner':
        return 'bg-purple-100 dark:bg-purple-950 text-purple-800 dark:text-purple-300 border-purple-300 dark:border-purple-800';
      case 'Director':
        return 'bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800';
      case 'Manager':
        return 'bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-800';
      case 'Assistant Manager':
        return 'bg-cyan-100 dark:bg-cyan-950 text-cyan-800 dark:text-cyan-300 border-cyan-300 dark:border-cyan-800';
      case 'Executive':
        return 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800';
      case 'Article Assistant':
        return 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-800';
      default:
        return 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="flex flex-wrap items-center justify-between border-b border-ca-border pb-4 gap-4">
        <div>
          <h1 className="text-xl font-bold text-navy-900 dark:text-white uppercase tracking-tight flex items-center gap-2">
            <Users className="w-6 h-6 text-orange-600" /> ENTERPRISE USER MANAGEMENT DIRECTORY
          </h1>
          <p className="text-xs text-ca-muted mt-0.5">
            Role-Based Access Control (RBAC), user provisioning & security governance for FS BUILDER LITE FS Builder.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowChangePasswordModal(true)}
            className="btn bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold px-3 py-2 rounded flex items-center gap-1.5 hover:bg-slate-50 cursor-pointer"
          >
            <Key className="w-4 h-4 text-orange-600" /> Change My Password
          </button>

          {isAdmin ? (
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn bg-orange-600 text-white text-xs font-bold px-4 py-2 rounded flex items-center gap-1.5 hover:bg-orange-700 shadow-xs cursor-pointer"
            >
              <UserPlus className="w-4 h-4" /> Provision New User
            </button>
          ) : (
            <div className="bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300 text-[11px] font-bold px-3 py-1.5 rounded flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <span>User Creation Restricted to Administrators</span>
            </div>
          )}
        </div>
      </div>

      {/* Notifications */}
      {actionError && (
        <div className="bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300 p-3 rounded text-xs font-bold flex items-center justify-between">
          <span>{actionError}</span>
          <button onClick={() => setActionError(null)} className="text-xs font-mono underline">Dismiss</button>
        </div>
      )}

      {actionSuccess && (
        <div className="bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-300 p-3 rounded text-xs font-bold flex items-center justify-between">
          <span>{actionSuccess}</span>
          <button onClick={() => setActionSuccess(null)} className="text-xs font-mono underline">Dismiss</button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="ca-card bg-white dark:bg-slate-900 p-4 border border-ca-border space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="relative md:col-span-2">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by Employee Code, Name, Email or Department..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="studio-input text-xs pl-9 py-2 w-full"
            />
          </div>

          <div>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="studio-input text-xs py-2 w-full font-bold"
            >
              <option value="ALL">All Roles ({users.length})</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="studio-input text-xs py-2 w-full font-bold"
            >
              <option value="ALL">All Status</option>
              <option value="ACTIVE">Active Users</option>
              <option value="INACTIVE">Deactivated Users</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main User Directory Table */}
      <div className="ca-card bg-white dark:bg-slate-900 overflow-hidden border border-ca-border">
        <div className="p-3 border-b border-ca-border bg-slate-50 dark:bg-slate-800 flex items-center justify-between">
          <span className="text-xs font-bold text-navy-900 dark:text-white uppercase">
            ACTIVE USERS DIRECTORY ({filteredUsers.length} Users)
          </span>
          <button onClick={loadData} className="text-xs text-orange-600 font-bold flex items-center gap-1 hover:underline">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh List
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-ca-muted text-xs font-semibold">Loading enterprise users directory...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-navy-900 text-white font-bold uppercase text-[10px] tracking-wider border-b border-slate-700">
                  <th className="p-3">User ID</th>
                  <th className="p-3">Emp Code</th>
                  <th className="p-3">Name & Contact</th>
                  <th className="p-3">Department</th>
                  <th className="p-3">Role</th>
                  <th className="p-3">Active Status</th>
                  <th className="p-3">Last Login</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {filteredUsers.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-ca-muted text-xs">
                      No user accounts found matching current filters.
                    </td>
                  </tr>
                ) : (
                  filteredUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors">
                      <td className="p-3 font-mono font-bold text-slate-500">#{u.id}</td>
                      <td className="p-3 font-mono font-bold text-navy-900 dark:text-blue-400">
                        {u.employee_code}
                      </td>
                      <td className="p-3">
                        <div className="font-bold text-slate-900 dark:text-white text-xs">{u.name}</div>
                        <div className="text-[10px] text-ca-muted flex items-center gap-2 mt-0.5">
                          <span className="flex items-center gap-1"><Mail className="w-3 h-3 text-slate-400" /> {u.email}</span>
                          {u.mobile && <span className="flex items-center gap-1"><Phone className="w-3 h-3 text-slate-400" /> {u.mobile}</span>}
                        </div>
                      </td>
                      <td className="p-3 text-slate-700 dark:text-slate-300 font-medium">{u.department}</td>
                      <td className="p-3">
                        <span className={`text-[10px] font-black px-2 py-0.5 rounded border uppercase tracking-wider ${getRoleBadge(u.role)}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="p-3">
                        {u.is_active ? (
                          <span className="bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 w-fit">
                            <CheckCircle className="w-3 h-3 text-emerald-600" /> Active
                          </span>
                        ) : (
                          <span className="bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-400 border border-rose-200 dark:border-rose-800 px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 w-fit">
                            <XCircle className="w-3 h-3 text-rose-600" /> Deactivated
                          </span>
                        )}
                      </td>
                      <td className="p-3 text-ca-muted font-mono text-[11px]">
                        {u.last_login ? new Date(u.last_login).toLocaleString() : 'Never logged in'}
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {isAdmin && (
                            <>
                              <button
                                onClick={() => setShowResetModal(u)}
                                title="Reset User Password"
                                className="px-2 py-1 bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 rounded text-[10px] font-bold hover:bg-amber-100 cursor-pointer"
                              >
                                Reset Pass
                              </button>
                              <button
                                onClick={() => handleToggleStatus(u)}
                                title={u.is_active ? "Deactivate User" : "Activate User"}
                                className={`px-2 py-1 border rounded text-[10px] font-bold cursor-pointer ${
                                  u.is_active
                                    ? 'bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800 hover:bg-rose-100'
                                    : 'bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100'
                                }`}
                              >
                                {u.is_active ? 'Deactivate' : 'Activate'}
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* CREATE NEW USER MODAL (Admin Only) */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="ca-card bg-white dark:bg-slate-900 border border-ca-border max-w-lg w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-ca-border pb-3">
              <h3 className="text-sm font-bold text-navy-900 dark:text-white uppercase flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-orange-600" /> Provision Enterprise User Account
              </h3>
              <button onClick={() => setShowCreateModal(false)} className="text-ca-muted hover:text-slate-900 dark:hover:text-white font-mono text-sm">✕</button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Employee Code *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. EMP005"
                    value={createForm.employee_code}
                    onChange={(e) => setCreateForm({ ...createForm, employee_code: e.target.value })}
                    className="studio-input w-full font-mono font-bold"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Rahul Mehta"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    className="studio-input w-full font-bold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Email Address *</label>
                  <input
                    type="email"
                    required
                    placeholder="rahul@swindia.in"
                    value={createForm.email}
                    onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                    className="studio-input w-full"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Mobile Number</label>
                  <input
                    type="text"
                    placeholder="+91 98765 00000"
                    value={createForm.mobile}
                    onChange={(e) => setCreateForm({ ...createForm, mobile: e.target.value })}
                    className="studio-input w-full"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Department</label>
                  <input
                    type="text"
                    value={createForm.department}
                    onChange={(e) => setCreateForm({ ...createForm, department: e.target.value })}
                    className="studio-input w-full font-semibold"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Assigned Role *</label>
                  <select
                    value={createForm.role}
                    onChange={(e) => setCreateForm({ ...createForm, role: e.target.value as UserRole })}
                    className="studio-input w-full font-bold"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Initial Password *</label>
                <input
                  type="password"
                  required
                  placeholder="Min 6 characters"
                  value={createForm.password}
                  onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                  className="studio-input w-full font-mono"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-ca-border">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs px-3 py-1.5 rounded cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn bg-orange-600 text-white text-xs font-bold px-4 py-1.5 rounded hover:bg-orange-700 cursor-pointer"
                >
                  Create User Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RESET USER PASSWORD MODAL (Admin Only) */}
      {showResetModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="ca-card bg-white dark:bg-slate-900 border border-ca-border max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-ca-border pb-3">
              <h3 className="text-sm font-bold text-navy-900 dark:text-white uppercase flex items-center gap-2">
                <Key className="w-4 h-4 text-amber-600" /> Reset Password for {showResetModal.name}
              </h3>
              <button onClick={() => setShowResetModal(null)} className="text-ca-muted hover:text-slate-900 font-mono text-sm">✕</button>
            </div>

            <form onSubmit={handleResetPassword} className="space-y-3 text-xs">
              <p className="text-ca-muted text-[11px]">
                Resetting password for employee <strong>{showResetModal.name}</strong> ({showResetModal.employee_code}).
              </p>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">New Password *</label>
                <input
                  type="password"
                  required
                  placeholder="Enter new password"
                  value={resetPassInput}
                  onChange={(e) => setResetPassInput(e.target.value)}
                  className="studio-input w-full font-mono"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-ca-border">
                <button
                  type="button"
                  onClick={() => setShowResetModal(null)}
                  className="btn bg-slate-200 dark:bg-slate-800 text-slate-700 text-xs px-3 py-1.5 rounded cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn bg-amber-600 text-white text-xs font-bold px-4 py-1.5 rounded hover:bg-amber-700 cursor-pointer"
                >
                  Reset Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CHANGE MY PASSWORD MODAL */}
      {showChangePasswordModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="ca-card bg-white dark:bg-slate-900 border border-ca-border max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-ca-border pb-3">
              <h3 className="text-sm font-bold text-navy-900 dark:text-white uppercase flex items-center gap-2">
                <Lock className="w-4 h-4 text-orange-600" /> Change My Password
              </h3>
              <button onClick={() => setShowChangePasswordModal(false)} className="text-ca-muted hover:text-slate-900 font-mono text-sm">✕</button>
            </div>

            <form onSubmit={handleChangePassword} className="space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">Current Password *</label>
                <input
                  type="password"
                  required
                  value={changePassForm.old_password}
                  onChange={(e) => setChangePassForm({ ...changePassForm, old_password: e.target.value })}
                  className="studio-input w-full font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">New Password *</label>
                <input
                  type="password"
                  required
                  value={changePassForm.new_password}
                  onChange={(e) => setChangePassForm({ ...changePassForm, new_password: e.target.value })}
                  className="studio-input w-full font-mono"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-ca-border">
                <button
                  type="button"
                  onClick={() => setShowChangePasswordModal(false)}
                  className="btn bg-slate-200 dark:bg-slate-800 text-slate-700 text-xs px-3 py-1.5 rounded cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn bg-orange-600 text-white text-xs font-bold px-4 py-1.5 rounded hover:bg-orange-700 cursor-pointer"
                >
                  Update Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
