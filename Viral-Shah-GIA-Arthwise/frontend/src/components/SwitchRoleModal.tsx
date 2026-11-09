import React, { useState } from 'react';
import { ShieldCheck, Lock, User, Eye, EyeOff, ArrowRight, X, AlertCircle } from 'lucide-react';
import { ApiClient } from '../api/client';
import { UserRole } from '../types';

interface SwitchRoleModalProps {
  targetRole: UserRole;
  currentRole: UserRole;
  onSuccess: (token: string, user: { id: string; email: string; full_name: string; role: UserRole }) => void;
  onCancel: () => void;
}

const ROLE_META: Record<UserRole, { label: string; defaultEmail: string; desc: string }> = {
  analyst: {
    label: 'Senior Debt Analyst',
    defaultEmail: 'analyst@giaarthwise.com',
    desc: 'Underwriting, financial statement analysis, checklist verification, and CMA model drafting.',
  },
  reviewer: {
    label: 'Credit Reviewer',
    defaultEmail: 'reviewer@giaarthwise.com',
    desc: 'Credit committee approval, sanction conditions, loan covenants, and stage sign-off.',
  },
  admin: {
    label: 'Chief Administrator',
    defaultEmail: 'admin@giaarthwise.com',
    desc: 'Full administrative governance, API configuration, audit trail logs, and master settings.',
  },
  client: {
    label: 'Borrower Client',
    defaultEmail: 'client@giaarthwise.com',
    desc: 'Self-service borrower portal, checklist uploads, and proposal tracking.',
  },
};

export const SwitchRoleModal: React.FC<SwitchRoleModalProps> = ({
  targetRole,
  currentRole,
  onSuccess,
  onCancel,
}) => {
  const meta = ROLE_META[targetRole] || {
    label: targetRole,
    defaultEmail: `${targetRole}@giaarthwise.com`,
    desc: 'Switches account role permissions.',
  };

  const [username, setUsername] = useState(meta.defaultEmail);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage('Please enter both username/email and password to authenticate.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await ApiClient.request<{ access_token: string; user: { id: string; email: string; full_name: string; role: UserRole } }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email: username.trim(), password: password.trim() }),
      });

      // Verify that the authenticated user matches the target role
      if (res.user.role !== targetRole) {
        setErrorMessage(`Authenticated role '${res.user.role}' does not match requested profile '${targetRole}'. Please log in with valid credentials for ${meta.label}.`);
        return;
      }

      onSuccess(res.access_token, res.user);
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please verify username and password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Modal Header */}
        <div className="bg-[#1b2632] text-white p-5 flex items-start justify-between border-b border-[#2a3c4f]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#a45139] text-white flex items-center justify-center shadow-md">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-white">Switch User Profile</h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-[#faece7] text-[#a45139]">
                  Authentication Required
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-0.5">
                Switching to <strong>{meta.label}</strong>
              </p>
            </div>
          </div>

          <button
            onClick={onCancel}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors"
            title="Cancel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6">
          <div className="mb-4 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
            <span className="font-semibold text-[#1b2632] block mb-0.5">Role Governance Note:</span>
            {meta.desc}
          </div>

          {errorMessage && (
            <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Authentication Error: </span>
                <span>{errorMessage}</span>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Username or Email ID
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. analyst@giaarthwise.com or analyst"
                  className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#a45139] focus:bg-white transition-all font-medium"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-bold text-slate-700">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setPassword(`${targetRole.charAt(0).toUpperCase() + targetRole.slice(1)}@123`)}
                  className="text-[10px] text-[#a45139] hover:underline font-mono"
                  title="Click to fill default demo password"
                >
                  Quick Fill: {targetRole.charAt(0).toUpperCase() + targetRole.slice(1)}@123
                </button>
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  autoFocus
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={`Enter password for ${meta.label}`}
                  className="w-full pl-9 pr-10 py-2 text-xs bg-slate-50 border border-slate-300 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#a45139] focus:bg-white transition-all font-medium"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2 text-slate-400 hover:text-slate-600 transition-colors p-0.5"
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-[#a45139] hover:bg-[#863e2a] rounded-lg shadow-md transition-all cursor-pointer disabled:opacity-50"
              >
                <span>{isLoading ? 'Verifying...' : `Authenticate as ${meta.label}`}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
