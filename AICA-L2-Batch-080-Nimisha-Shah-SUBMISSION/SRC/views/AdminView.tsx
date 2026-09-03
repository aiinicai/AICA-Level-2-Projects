import React, { useState, useEffect } from "react";
import { 
  ShieldCheck, 
  Users, 
  UserCheck, 
  Database, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  Lock,
  Mail,
  Calendar,
  Layers
} from "lucide-react";
import { useAuth, UserProfile } from "../context/AuthContext";
import { supabase, isSupabaseConfigured } from "../lib/supabaseClient";

export const AdminView: React.FC = () => {
  const { user, profile, isAdmin } = useAuth();
  const [profilesList, setProfilesList] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchAllProfiles = async () => {
    if (!isSupabaseConfigured || !isAdmin) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) {
        throw error;
      }

      setProfilesList((data || []) as UserProfile[]);
    } catch (err: any) {
      console.error('Error fetching admin profiles:', err);
      setErrorMessage(err.message || 'Failed to load user profiles from database.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllProfiles();
  }, [isAdmin]);

  if (!isAdmin) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-slate-200 shadow-xs max-w-lg mx-auto mt-12 space-y-3">
        <div className="w-12 h-12 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center mx-auto">
          <Lock className="w-6 h-6" />
        </div>
        <h2 className="text-base font-bold text-slate-900">Access Restricted</h2>
        <p className="text-xs text-slate-500">
          This administration section is restricted strictly to accounts with the <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-800 font-mono">admin</code> role.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-purple-600 text-white flex items-center justify-center shadow-md shadow-purple-600/20">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900">Administration Console</h1>
              <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 font-bold text-[10px] border border-purple-200 uppercase">
                Admin Role Active
              </span>
            </div>
            <p className="text-xs text-slate-500">
              System governance, user roles, and platform status
            </p>
          </div>
        </div>

        <button
          onClick={fetchAllProfiles}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold transition-colors cursor-pointer disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Profiles</span>
        </button>
      </div>

      {/* Error Alert */}
      {errorMessage && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-xl flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
          <div>
            <span className="font-bold">Database Notice: </span>
            <span>{errorMessage}</span>
            <div className="mt-1 text-[11px] text-rose-600">
              Ensure the <code className="bg-rose-100 px-1 py-0.5 rounded font-mono">profiles</code> table migration has been executed in your Supabase SQL Editor.
            </div>
          </div>
        </div>
      )}

      {/* Status Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>Registered Accounts</span>
            <Users className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 font-mono">
            {profilesList.length}
          </div>
          <p className="text-[11px] text-slate-400">Authenticated user profiles in Supabase</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>Administrator Accounts</span>
            <ShieldCheck className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-purple-700 font-mono">
            {profilesList.filter(p => p.role === 'admin').length}
          </div>
          <p className="text-[11px] text-slate-400">Accounts with full admin privileges</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>Standard User Accounts</span>
            <UserCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-700 font-mono">
            {profilesList.filter(p => p.role === 'user').length}
          </div>
          <p className="text-[11px] text-slate-400">Default analyst role accounts</p>
        </div>
      </div>

      {/* Profiles Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-900 tracking-wider uppercase">
            User Accounts & Role Directory
          </h2>
          <span className="text-[11px] text-slate-400 font-medium">
            Managed via Supabase PostgreSQL RLS
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[11px]">
              <tr>
                <th className="px-5 py-3">User / Name</th>
                <th className="px-5 py-3">Email Address</th>
                <th className="px-5 py-3">Assigned Role</th>
                <th className="px-5 py-3">Registered At</th>
                <th className="px-5 py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
                    <span>Loading registered user profiles...</span>
                  </td>
                </tr>
              ) : profilesList.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-400">
                    <span>No user profiles retrieved. Ensure the <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">profiles</code> table has been created in Supabase.</span>
                  </td>
                </tr>
              ) : (
                profilesList.map((p) => {
                  const isCurrent = p.id === user?.id;
                  return (
                    <tr key={p.id} className={isCurrent ? "bg-purple-50/40" : "hover:bg-slate-50/60"}>
                      <td className="px-5 py-3.5 text-slate-900 font-semibold">
                        <div className="flex items-center gap-2">
                          <span>{p.full_name || 'Unnamed User'}</span>
                          {isCurrent && (
                            <span className="px-1.5 py-0.2 rounded bg-purple-100 text-purple-700 text-[9px] font-bold">
                              You
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-slate-600 font-mono text-[11px]">
                        {p.email}
                      </td>
                      <td className="px-5 py-3.5">
                        {p.role === 'admin' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-purple-100 text-purple-800 font-bold text-[10px] border border-purple-200">
                            <ShieldCheck className="w-3 h-3 text-purple-600" />
                            <span>ADMIN</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold text-[10px] border border-slate-200">
                            <UserCheck className="w-3 h-3 text-slate-500" />
                            <span>USER</span>
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500 text-[11px]">
                        {p.created_at ? new Date(p.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-600 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Active</span>
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
