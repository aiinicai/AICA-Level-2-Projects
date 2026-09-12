import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useCompany } from '../context/CompanyContext';
import { Building2, User, LogOut, ShieldCheck, Tag } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout, isAdmin } = useAuth();
  const { companies, selectedCompany, setSelectedCompany } = useCompany();

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 text-white px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Logo */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
          <Tag className="w-5 h-5" />
        </div>
        <div>
          <div className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
            AssetTag Pro
            <span className="text-[10px] bg-blue-500/20 text-blue-300 font-semibold px-1.5 py-0.5 rounded border border-blue-500/30">
              Enterprise v1.0
            </span>
          </div>
          <div className="text-[11px] text-slate-400">Fixed Asset & Inventory Tagging Engine</div>
        </div>
      </div>

      {/* Center: Active Company Selector */}
      <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
        <Building2 className="w-4 h-4 text-blue-400" />
        <span className="text-xs font-medium text-slate-300">Active Company:</span>
        <select
          value={selectedCompany?.id || ''}
          onChange={(e) => {
            const found = companies.find((c) => c.id === Number(e.target.value));
            if (found) setSelectedCompany(found);
          }}
          className="bg-transparent text-xs font-semibold text-white focus:outline-none cursor-pointer"
        >
          {companies.map((comp) => (
            <option key={comp.id} value={comp.id} className="bg-slate-900 text-white">
              {comp.name} ({comp.asset_id_prefix})
            </option>
          ))}
        </select>
      </div>

      {/* Right User Profile & Role */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 font-bold text-xs border border-slate-600">
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <div className="hidden md:block text-left">
            <div className="text-xs font-semibold text-slate-200">{user?.full_name}</div>
            <div className="text-[10px] font-medium text-slate-400 flex items-center gap-1">
              {isAdmin && <ShieldCheck className="w-3 h-3 text-emerald-400" />}
              <span>{user?.role === 'ADMIN' ? 'Administrator' : 'Field Tagging User'}</span>
            </div>
          </div>
        </div>

        <button
          onClick={logout}
          title="Sign Out"
          className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
