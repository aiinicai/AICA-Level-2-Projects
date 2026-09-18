import React, { useState, useEffect } from 'react';
import { Users, Plus, ShieldCheck, UserCheck, Edit2, X, Lock, Mail, User } from 'lucide-react';
import api from '../services/api';
import { User as UserType } from '../types';

export const UserManagementPage: React.FC = () => {
  const [users, setUsers] = useState<UserType[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);

  // Form State
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'ADMIN' | 'STANDARD_USER'>('STANDARD_USER');
  const [isActive, setIsActive] = useState(true);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await api.get<UserType[]>('/admin/users');
      setUsers(res.data);
    } catch (e) {
      console.error('Failed to load users:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const openCreateModal = () => {
    setIsEditing(false);
    setEditId(null);
    setFullName('');
    setEmail('');
    setPassword('');
    setRole('STANDARD_USER');
    setIsActive(true);
    setShowModal(true);
  };

  const openEditModal = (u: UserType) => {
    setIsEditing(true);
    setEditId(u.id);
    setFullName(u.full_name);
    setEmail(u.email);
    setPassword('');
    setRole(u.role);
    setIsActive(u.is_active);
    setShowModal(true);
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (isEditing && editId) {
        await api.put(`/admin/users/${editId}`, {
          full_name: fullName,
          role,
          is_active: isActive,
          password: password || undefined,
        });
      } else {
        if (!password) {
          alert('Password is required for new users.');
          return;
        }
        await api.post('/admin/users', {
          full_name: fullName,
          email,
          password,
          role,
          is_active: isActive,
        });
      }
      setShowModal(false);
      fetchUsers();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to save user.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">User Management & Permissions</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Administer tagging staff, assign Administrator vs Standard User roles, and manage credentials
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-sm transition"
        >
          <Plus className="w-4 h-4" />
          Add User Account
        </button>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">User</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Assigned Role</th>
                <th className="py-3 px-4">Account Status</th>
                <th className="py-3 px-4">Created Date</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/70 transition">
                  <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-700 text-xs">
                      {u.full_name?.charAt(0) || 'U'}
                    </div>
                    <span>{u.full_name}</span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-600">{u.email}</td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                        u.role === 'ADMIN'
                          ? 'bg-blue-50 text-blue-700 border border-blue-200'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {u.role === 'ADMIN' ? <ShieldCheck className="w-3 h-3" /> : <UserCheck className="w-3 h-3" />}
                      {u.role === 'ADMIN' ? 'Administrator' : 'Standard User'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                        u.is_active
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px]">
                    {u.created_at?.substring(0, 10)}
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <button
                      onClick={() => openEditModal(u)}
                      className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-slate-100 rounded transition"
                      title="Edit User"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* User Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">
                {isEditing ? 'Edit User Profile' : 'Create New User'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveUser} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Prasanth Kumar"
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 font-medium"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Work Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isEditing}
                  placeholder="name@company.com"
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 font-medium disabled:opacity-60"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  {isEditing ? 'Reset Password (Leave blank to retain)' : 'Password'}
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Role Permissions</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as any)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 font-medium"
                >
                  <option value="STANDARD_USER">Standard User (Field Tagging & Printing)</option>
                  <option value="ADMIN">Administrator (Full Access & Master Setup)</option>
                </select>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="user-active-chk"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="rounded text-blue-600"
                />
                <label htmlFor="user-active-chk" className="text-xs font-semibold text-slate-700 cursor-pointer">
                  Account is Active
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
                >
                  Save User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
