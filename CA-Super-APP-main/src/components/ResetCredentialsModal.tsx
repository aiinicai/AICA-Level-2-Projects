import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { UserRole } from '../types';
import { Settings2, ShieldCheck, Users, Key, CheckCircle2, AlertCircle, X, Phone } from 'lucide-react';

interface ResetCredentialsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ResetCredentialsModal: React.FC<ResetCredentialsModalProps> = ({ isOpen, onClose }) => {
  const { auth, adminCredentials, staffCredentials, updateCredentials } = useApp();
  
  const [targetRole, setTargetRole] = useState<UserRole>('staff');
  const [newUsername, setNewUsername] = useState(targetRole === 'admin' ? adminCredentials.username : staffCredentials.username);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  if (!isOpen) return null;

  const handleRoleTabChange = (role: UserRole) => {
    setTargetRole(role);
    setNewUsername(role === 'admin' ? adminCredentials.username : staffCredentials.username);
    setNewPassword('');
    setConfirmPassword('');
    setStatusMessage(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMessage(null);

    if (newPassword !== confirmPassword) {
      setStatusMessage({ type: 'error', text: 'Passwords do not match. Please verify both fields.' });
      return;
    }

    if (newPassword.length < 4) {
      setStatusMessage({ type: 'error', text: 'Password must be at least 4 characters long.' });
      return;
    }

    const res = updateCredentials(targetRole, newUsername, newPassword);
    if (res.success) {
      setStatusMessage({ type: 'success', text: res.message });
      setNewPassword('');
      setConfirmPassword('');
    } else {
      setStatusMessage({ type: 'error', text: res.message });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-amber-700 via-amber-800 to-yellow-800 px-6 py-4 text-white flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Settings2 className="w-5 h-5 text-amber-200" />
            <div>
              <h2 className="text-base font-bold leading-tight">Admin Security Management</h2>
              <p className="text-xs text-amber-200">Reset User ID &amp; Password for Admin &amp; Staff</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-white/80 hover:text-white hover:bg-white/10"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {auth.role !== 'admin' ? (
            <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200 text-sm">
              <p className="font-bold">Access Restricted</p>
              <p className="text-xs mt-1">Only the CA Administrator can modify user credentials and passwords.</p>
            </div>
          ) : (
            <>
              {/* Target Selector */}
              <div className="flex p-1 bg-slate-100 rounded-xl mb-5">
                <button
                  type="button"
                  onClick={() => handleRoleTabChange('staff')}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold flex items-center justify-center space-x-2 transition-all ${
                    targetRole === 'staff'
                      ? 'bg-white text-teal-800 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Users className="w-4 h-4 text-teal-600" />
                  <span>Reset Staff Login (All Staff)</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleRoleTabChange('admin')}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold flex items-center justify-center space-x-2 transition-all ${
                    targetRole === 'admin'
                      ? 'bg-white text-amber-800 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <ShieldCheck className="w-4 h-4 text-amber-600" />
                  <span>Reset CA Admin Login</span>
                </button>
              </div>

              {/* Current Creds Indicator */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 mb-4 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-slate-800">
                    {targetRole === 'admin' ? 'CA Admin Current ID: ' : 'Staff Common Current ID: '}
                  </span>
                  <span className="font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-emerald-700 font-bold">
                    {targetRole === 'admin' ? adminCredentials.username : staffCredentials.username}
                  </span>
                </div>
                <span className="text-[11px] text-slate-400">Firm Policy Regulated</span>
              </div>

              {/* Reset Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Fixed USER ID
                  </label>
                  <input
                    type="text"
                    value={targetRole === 'admin' ? 'ADMIN' : 'STAFF'}
                    readOnly
                    className="w-full px-3 py-2 bg-slate-100 border border-slate-200 rounded-xl text-sm font-bold text-slate-800 tracking-wider cursor-not-allowed select-all"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      New Password
                    </label>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={e => setNewPassword(e.target.value)}
                      placeholder="New password"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Confirm Password
                    </label>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={e => setConfirmPassword(e.target.value)}
                      placeholder="Re-type password"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      required
                    />
                  </div>
                </div>

                {statusMessage && (
                  <div className={`p-3 rounded-xl text-xs flex items-center space-x-2 ${
                    statusMessage.type === 'success'
                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                      : 'bg-red-50 text-red-800 border border-red-200'
                  }`}>
                    {statusMessage.type === 'success' ? (
                      <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                    ) : (
                      <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                    )}
                    <span>{statusMessage.text}</span>
                  </div>
                )}

                <div className="pt-2 flex items-center justify-end space-x-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 border border-slate-200 text-slate-600 hover:bg-slate-50 rounded-xl text-xs font-semibold"
                  >
                    Close
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-700 hover:to-teal-800 text-white rounded-xl text-xs font-bold shadow-md transition-all flex items-center space-x-1.5"
                  >
                    <Key className="w-3.5 h-3.5" />
                    <span>Save New Credentials</span>
                  </button>
                </div>
              </form>

              {/* Information box about registered email */}
              <div className="mt-5 pt-4 border-t border-slate-100 flex items-start space-x-2 text-xs text-slate-600">
                <ShieldCheck className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                <span>
                  Admin &amp; Staff emergency password recovery OTP is permanently linked to: <strong>rishugarg006@gmail.com</strong>.
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
