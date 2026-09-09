import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  UserCheck,
  UserX,
  Plus,
  Trash2,
  Lock,
  Mail,
  User,
  CheckCircle2,
  Clock,
  X,
  Search,
  Filter,
  ShieldCheck,
} from 'lucide-react';
import { AppUser, UserRole, UserStatus } from '../types/accounting';
import { authService } from '../utils/authService';

interface UserManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: AppUser;
}

export const UserManagementModal: React.FC<UserManagementModalProps> = ({
  isOpen,
  onClose,
  currentUser,
}) => {
  const [users, setUsers] = useState<AppUser[]>([]);
  const [activeTab, setActiveTab] = useState<'PENDING' | 'ALL' | 'ADD_USER'>('PENDING');
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // New User Form (Admin Direct Provisioning)
  const [newId, setNewId] = useState('');
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<UserRole>('AUDITOR');

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const list = await authService.getAllUsers();
      setUsers(list);
    } catch (e) {
      console.error('Failed to load users:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchUsers();
      setFeedback(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const pendingUsers = users.filter((u) => u.status === 'PENDING');
  const approvedUsers = users.filter((u) => u.status !== 'PENDING');

  const handleApprove = async (userId: string, role: UserRole) => {
    setLoading(true);
    setFeedback(null);
    try {
      const res = await authService.updateUserStatus(userId, 'APPROVED', role, currentUser.id);
      if (res.success) {
        setFeedback({ type: 'success', text: `User "${userId}" approved successfully as ${role}.` });
        await fetchUsers();
      } else {
        setFeedback({ type: 'error', text: res.error || 'Failed to approve user.' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message || 'Error approving user.' });
    } finally {
      setLoading(false);
    }
  };

  const handleRejectOrDelete = async (userId: string) => {
    if (userId.toLowerCase() === currentUser.id.toLowerCase()) {
      alert('You cannot delete your own active administrator account.');
      return;
    }

    if (!confirm(`Are you sure you want to delete / reject user "${userId}"?`)) return;

    setLoading(true);
    setFeedback(null);
    try {
      const res = await authService.deleteUser(userId);
      if (res.success) {
        setFeedback({ type: 'success', text: `User "${userId}" removed.` });
        await fetchUsers();
      } else {
        setFeedback({ type: 'error', text: res.error || 'Failed to delete user.' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message || 'Error deleting user.' });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (userId: string, currentStatus: UserStatus) => {
    if (userId.toLowerCase() === currentUser.id.toLowerCase()) {
      alert('You cannot suspend your own administrator account.');
      return;
    }

    const nextStatus: UserStatus = currentStatus === 'APPROVED' ? 'SUSPENDED' : 'APPROVED';
    setLoading(true);
    try {
      const res = await authService.updateUserStatus(userId, nextStatus, undefined, currentUser.id);
      if (res.success) {
        setFeedback({ type: 'success', text: `User "${userId}" status updated to ${nextStatus}.` });
        await fetchUsers();
      } else {
        setFeedback({ type: 'error', text: res.error || 'Failed to update status.' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: UserRole) => {
    setLoading(true);
    try {
      const res = await authService.updateUserStatus(userId, 'APPROVED', newRole, currentUser.id);
      if (res.success) {
        setFeedback({ type: 'success', text: `Role for "${userId}" updated to ${newRole}.` });
        await fetchUsers();
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDirectUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newId.trim() || !newName.trim() || !newPassword) {
      setFeedback({ type: 'error', text: 'Please provide User ID, Full Name, and Password.' });
      return;
    }

    setLoading(true);
    setFeedback(null);
    try {
      const res = await authService.adminCreateUser(
        {
          id: newId.trim(),
          name: newName.trim(),
          email: newEmail.trim(),
          password: newPassword,
          role: newRole,
        },
        currentUser.id
      );

      if (res.success) {
        setFeedback({ type: 'success', text: `User "${newId}" created and pre-approved as ${newRole}.` });
        setNewId('');
        setNewName('');
        setNewEmail('');
        setNewPassword('');
        setActiveTab('ALL');
        await fetchUsers();
      } else {
        setFeedback({ type: 'error', text: res.error || 'Failed to create user.' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const filteredApproved = approvedUsers.filter(
    (u) =>
      u.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4">
      <div className="bg-[#141414] text-[#E4E3E0] border border-[#333333] w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl rounded-none">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#262626] flex items-center justify-between bg-[#1a1a1a]">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-[#2a2415] border border-[#f59e0b]/40 text-[#f59e0b]">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold font-mono tracking-tight text-white flex items-center gap-2">
                ADMIN ACCESS CONTROL & USER APPROVALS
                {pendingUsers.length > 0 && (
                  <span className="px-2 py-0.5 bg-[#dc2626] text-white text-[10px] font-mono rounded-full font-bold">
                    {pendingUsers.length} PENDING
                  </span>
                )}
              </h2>
              <p className="text-[11px] font-mono text-[#8E8C85]">
                Manage team authorizations, approve newly registered User IDs, and grant roles
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#8E8C85] hover:text-white hover:bg-[#262626] transition cursor-pointer"
            id="btn-close-user-management"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[#262626] bg-[#171717] px-6">
          <button
            onClick={() => {
              setActiveTab('PENDING');
              setFeedback(null);
            }}
            className={`py-3 px-4 text-xs font-mono font-bold tracking-wider border-b-2 flex items-center gap-2 cursor-pointer transition ${
              activeTab === 'PENDING'
                ? 'border-[#f59e0b] text-[#f59e0b] bg-[#1f1f1f]'
                : 'border-transparent text-[#8E8C85] hover:text-white'
            }`}
            id="tab-pending-approvals"
          >
            <Clock className="w-3.5 h-3.5" />
            PENDING APPROVALS ({pendingUsers.length})
          </button>

          <button
            onClick={() => {
              setActiveTab('ALL');
              setFeedback(null);
            }}
            className={`py-3 px-4 text-xs font-mono font-bold tracking-wider border-b-2 flex items-center gap-2 cursor-pointer transition ${
              activeTab === 'ALL'
                ? 'border-[#58a6ff] text-[#58a6ff] bg-[#1f1f1f]'
                : 'border-transparent text-[#8E8C85] hover:text-white'
            }`}
            id="tab-all-users"
          >
            <UserCheck className="w-3.5 h-3.5" />
            ACTIVE USERS ({approvedUsers.length})
          </button>

          <button
            onClick={() => {
              setActiveTab('ADD_USER');
              setFeedback(null);
            }}
            className={`py-3 px-4 text-xs font-mono font-bold tracking-wider border-b-2 flex items-center gap-2 cursor-pointer transition ${
              activeTab === 'ADD_USER'
                ? 'border-[#10b981] text-[#10b981] bg-[#1f1f1f]'
                : 'border-transparent text-[#8E8C85] hover:text-white'
            }`}
            id="tab-add-user"
          >
            <Plus className="w-3.5 h-3.5" />
            PROVISION NEW USER ID
          </button>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div
            className={`mx-6 mt-4 p-3 text-xs font-mono border flex items-center gap-2 ${
              feedback.type === 'success'
                ? 'bg-[#1b2a1e] border-[#4ade80]/40 text-[#4ade80]'
                : 'bg-[#2d1b1b] border-[#f87171]/40 text-[#f87171]'
            }`}
          >
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <ShieldAlert className="w-4 h-4 shrink-0" />
            )}
            <span>{feedback.text}</span>
          </div>
        )}

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* TAB 1: PENDING APPROVALS */}
          {activeTab === 'PENDING' && (
            <div>
              {pendingUsers.length === 0 ? (
                <div className="text-center py-12 border border-dashed border-[#333333] bg-[#171717] p-8">
                  <CheckCircle2 className="w-10 h-10 text-[#4ade80] mx-auto mb-3 opacity-80" />
                  <h3 className="text-sm font-bold font-mono text-white">NO PENDING USER REQUESTS</h3>
                  <p className="text-xs font-mono text-[#8E8C85] mt-1 max-w-sm mx-auto">
                    All User ID registration requests have been reviewed and approved. When new staff or clients register, their requests will appear here for Admin authorization.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="text-xs font-mono text-[#fbbf24] flex items-center gap-1.5 mb-2">
                    <Clock className="w-4 h-4" />
                    <span>The following User IDs have registered and cannot log in until an Admin approves them:</span>
                  </div>

                  {pendingUsers.map((pUser) => (
                    <div
                      key={pUser.id}
                      className="bg-[#1a1a1a] border border-[#f59e0b]/40 p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
                      id={`pending-user-${pUser.id}`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono font-bold text-white">{pUser.name}</span>
                          <span className="px-2 py-0.5 bg-[#f59e0b]/20 text-[#fcd34d] border border-[#f59e0b]/40 text-[10px] font-mono font-bold">
                            PENDING ID: {pUser.id}
                          </span>
                          <span className="text-[10px] font-mono text-[#8E8C85]">
                            Requested: {pUser.role}
                          </span>
                        </div>
                        <div className="text-xs font-mono text-[#A3A29E] mt-1 flex items-center gap-3">
                          {pUser.email && <span>Email: {pUser.email}</span>}
                          <span>Registered: {new Date(pUser.createdAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </div>

                      {/* Approval Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        <select
                          defaultValue={pUser.role}
                          id={`select-role-${pUser.id}`}
                          className="bg-[#0f0f0f] border border-[#444] text-white text-xs font-mono px-2 py-1.5 focus:border-[#f59e0b] focus:outline-none"
                        >
                          <option value="AUDITOR">Approve as Auditor</option>
                          <option value="ACCOUNTANT">Approve as Staff Accountant</option>
                          <option value="ADMIN">Approve as Administrator</option>
                          <option value="VIEWER">Approve as Read-Only Viewer</option>
                        </select>

                        <button
                          onClick={() => {
                            const sel = document.getElementById(`select-role-${pUser.id}`) as HTMLSelectElement;
                            handleApprove(pUser.id, (sel?.value as UserRole) || pUser.role);
                          }}
                          disabled={loading}
                          className="px-3 py-1.5 bg-[#166534] hover:bg-[#15803d] text-white text-xs font-mono font-bold flex items-center gap-1 cursor-pointer transition disabled:opacity-50"
                          id={`btn-approve-${pUser.id}`}
                        >
                          <UserCheck className="w-3.5 h-3.5" />
                          ALLOW / APPROVE
                        </button>

                        <button
                          onClick={() => handleRejectOrDelete(pUser.id)}
                          disabled={loading}
                          className="px-2.5 py-1.5 bg-[#7f1d1d] hover:bg-[#991b1b] text-white text-xs font-mono flex items-center gap-1 cursor-pointer transition disabled:opacity-50"
                          title="Reject and Delete Request"
                          id={`btn-reject-${pUser.id}`}
                        >
                          <UserX className="w-3.5 h-3.5" />
                          REJECT
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: ALL ACTIVE USERS */}
          {activeTab === 'ALL' && (
            <div className="space-y-4">
              {/* Search Bar */}
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#8E8C85]" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search users by name, User ID, or email..."
                  className="w-full bg-[#171717] border border-[#333] pl-9 pr-3 py-2 text-xs font-mono text-white focus:border-[#58a6ff] focus:outline-none"
                  id="input-search-users"
                />
              </div>

              {/* Users Table */}
              <div className="overflow-x-auto border border-[#262626]">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-[#1f1f1f] text-[#A3A29E] border-b border-[#262626]">
                    <tr>
                      <th className="py-2.5 px-3">USER ID</th>
                      <th className="py-2.5 px-3">FULL NAME & EMAIL</th>
                      <th className="py-2.5 px-3">ROLE</th>
                      <th className="py-2.5 px-3">STATUS</th>
                      <th className="py-2.5 px-3">LAST ACTIVE</th>
                      <th className="py-2.5 px-3 text-right">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#262626]">
                    {filteredApproved.map((u) => (
                      <tr key={u.id} className="hover:bg-[#1a1a1a] transition">
                        <td className="py-2.5 px-3 font-bold text-white">
                          {u.id}
                          {u.id.toLowerCase() === currentUser.id.toLowerCase() && (
                            <span className="ml-1 text-[10px] text-[#4ade80] font-normal">(You)</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="text-white font-medium">{u.name}</div>
                          <div className="text-[11px] text-[#8E8C85]">{u.email || 'No email specified'}</div>
                        </td>
                        <td className="py-2.5 px-3">
                          <select
                            value={u.role}
                            onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                            disabled={u.id.toLowerCase() === currentUser.id.toLowerCase()}
                            className="bg-[#111] border border-[#333] text-[11px] font-mono px-2 py-1 text-white focus:border-[#58a6ff] focus:outline-none disabled:opacity-60"
                          >
                            <option value="ADMIN">ADMIN</option>
                            <option value="AUDITOR">AUDITOR</option>
                            <option value="ACCOUNTANT">ACCOUNTANT</option>
                            <option value="VIEWER">VIEWER</option>
                          </select>
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-2 py-0.5 text-[10px] font-bold border ${
                              u.status === 'APPROVED'
                                ? 'bg-[#142918] text-[#4ade80] border-[#4ade80]/30'
                                : 'bg-[#331c1c] text-[#f87171] border-[#f87171]/30'
                            }`}
                          >
                            {u.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-[11px] text-[#8E8C85]">
                          {u.lastLoginAt
                            ? new Date(u.lastLoginAt).toLocaleDateString('en-IN', {
                                day: '2-digit',
                                month: 'short',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : 'Never'}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {u.id.toLowerCase() !== currentUser.id.toLowerCase() && (
                              <>
                                <button
                                  onClick={() => handleToggleStatus(u.id, u.status)}
                                  className={`px-2 py-1 text-[10.5px] border cursor-pointer transition ${
                                    u.status === 'APPROVED'
                                      ? 'bg-[#2a1c1c] border-[#f87171]/40 text-[#f87171] hover:bg-[#3d2424]'
                                      : 'bg-[#1c2a1c] border-[#4ade80]/40 text-[#4ade80] hover:bg-[#243d24]'
                                  }`}
                                >
                                  {u.status === 'APPROVED' ? 'SUSPEND' : 'ACTIVATE'}
                                </button>
                                <button
                                  onClick={() => handleRejectOrDelete(u.id)}
                                  className="p-1 text-[#8E8C85] hover:text-[#f87171] transition cursor-pointer"
                                  title="Delete User Account"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: PROVISION NEW USER DIRECTLY */}
          {activeTab === 'ADD_USER' && (
            <form onSubmit={handleCreateDirectUser} className="max-w-md mx-auto space-y-4 py-2">
              <div className="bg-[#171717] p-3 border border-[#333] text-xs font-mono text-[#A3A29E]">
                As an Administrator, you can create new user credentials directly with immediate approval status (bypassing the registration waiting queue).
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-[#A3A29E] mb-1">User ID *</label>
                <input
                  type="text"
                  value={newId}
                  onChange={(e) => setNewId(e.target.value.toLowerCase().replace(/[^a-z0-9._-]/g, ''))}
                  placeholder="e.g. rohit.auditor"
                  required
                  className="w-full bg-[#111] border border-[#333] px-3 py-2 text-xs font-mono text-white focus:border-[#10b981] focus:outline-none"
                  id="input-direct-userid"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-[#A3A29E] mb-1">Full Name *</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. CA Rohit Sharma"
                  required
                  className="w-full bg-[#111] border border-[#333] px-3 py-2 text-xs font-mono text-white focus:border-[#10b981] focus:outline-none"
                  id="input-direct-name"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-[#A3A29E] mb-1">Email</label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="rohit@cafirm.com"
                  className="w-full bg-[#111] border border-[#333] px-3 py-2 text-xs font-mono text-white focus:border-[#10b981] focus:outline-none"
                  id="input-direct-email"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-[#A3A29E] mb-1">Password *</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 5 characters"
                  required
                  className="w-full bg-[#111] border border-[#333] px-3 py-2 text-xs font-mono text-white focus:border-[#10b981] focus:outline-none"
                  id="input-direct-password"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-[#A3A29E] mb-1">Assigned Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as UserRole)}
                  className="w-full bg-[#111] border border-[#333] px-3 py-2 text-xs font-mono text-white focus:border-[#10b981] focus:outline-none"
                  id="select-direct-role"
                >
                  <option value="AUDITOR">Auditor / Reviewer</option>
                  <option value="ACCOUNTANT">Accountant / Staff</option>
                  <option value="ADMIN">Firm Administrator</option>
                  <option value="VIEWER">Read-Only Viewer</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-[#10b981] hover:bg-[#059669] text-white font-mono text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 cursor-pointer transition disabled:opacity-50"
                id="btn-submit-direct-user"
              >
                <Plus className="w-4 h-4" />
                {loading ? 'CREATING...' : 'CREATE & AUTHORIZE USER ID'}
              </button>
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#262626] bg-[#1a1a1a] flex justify-between items-center text-xs font-mono text-[#8E8C85]">
          <div>Logged in as Admin: <span className="text-white font-bold">{currentUser.name} ({currentUser.id})</span></div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-[#262626] hover:bg-[#333333] text-white text-xs font-mono cursor-pointer transition"
          >
            CLOSE
          </button>
        </div>
      </div>
    </div>
  );
};
