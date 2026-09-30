import React, { useState } from 'react';
import { Building2, X, Plus, Search, Check, ShieldCheck, ArrowRight, MapPin, Hash, Sparkles } from 'lucide-react';
import { Company, User } from '../../types';

interface CompanySwitcherModalProps {
  isOpen: boolean;
  onClose: () => void;
  companies: Company[];
  activeCompanyId: string;
  currentUser: User;
  onSelectCompany: (companyId: string) => void;
  onOpenAddCompany: () => void;
}

export const CompanySwitcherModal: React.FC<CompanySwitcherModalProps> = ({
  isOpen,
  onClose,
  companies,
  activeCompanyId,
  currentUser,
  onSelectCompany,
  onOpenAddCompany
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  if (!isOpen) return null;

  // Filter companies accessible by current user
  const accessibleCompanies = companies.filter(c => {
    if (!currentUser.assignedCompanies || currentUser.assignedCompanies.includes('*')) {
      return true;
    }
    return currentUser.assignedCompanies.includes(c.id);
  });

  const filteredCompanies = accessibleCompanies.filter(c => {
    const q = searchQuery.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.legalName.toLowerCase().includes(q) ||
      c.gstin.toLowerCase().includes(q) ||
      c.pan.toLowerCase().includes(q) ||
      c.state.toLowerCase().includes(q)
    );
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-slate-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-slate-800 text-white flex items-center justify-center shadow-xs">
              <Building2 className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Switch Company / Entity</h3>
              <p className="text-xs text-slate-500">
                Logged in as <span className="font-semibold text-slate-800">{currentUser.name}</span> ({currentUser.role})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search & Actions Bar */}
        <div className="p-4 border-b border-slate-100 flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search companies by name, GSTIN, PAN or state..."
              className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600"
            />
          </div>
          <button
            onClick={() => {
              onClose();
              onOpenAddCompany();
            }}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors shadow-xs shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>Add Company</span>
          </button>
        </div>

        {/* Companies List */}
        <div className="p-4 space-y-3 max-h-[60vh] overflow-y-auto">
          {filteredCompanies.length === 0 ? (
            <div className="text-center py-8">
              <Building2 className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-xs font-semibold text-slate-600">No matching companies found</p>
              <p className="text-[11px] text-slate-400 mt-1">Try a different search term or add a new entity</p>
            </div>
          ) : (
            filteredCompanies.map((comp) => {
              const isActive = comp.id === activeCompanyId;
              return (
                <div
                  key={comp.id}
                  onClick={() => {
                    if (!isActive) {
                      onSelectCompany(comp.id);
                      onClose();
                    }
                  }}
                  className={`p-4 rounded-xl border transition-all cursor-pointer relative ${
                    isActive
                      ? 'bg-emerald-50/70 border-emerald-400 shadow-xs ring-1 ring-emerald-400/40'
                      : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/70'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <h4 className="font-bold text-slate-900 text-sm">{comp.name}</h4>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                          {comp.businessType}
                        </span>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-800 border border-blue-200">
                          FY {comp.financialYear || '2026-27'}
                        </span>
                        {isActive && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-600 text-white flex items-center gap-1 shadow-2xs">
                            <Check className="w-3 h-3" />
                            Active Books
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 font-medium truncate">{comp.legalName}</p>

                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px] text-slate-600">
                        <div>
                          <span className="text-slate-400 block text-[10px] uppercase font-bold">GSTIN</span>
                          <span className="font-mono font-semibold text-slate-800">{comp.gstin}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px] uppercase font-bold">State / Code</span>
                          <span>{comp.state} ({comp.stateCode})</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px] uppercase font-bold">TDS Section</span>
                          <span className="font-semibold text-slate-800">{comp.defaultTdsSection} ({comp.defaultTdsRate}%)</span>
                        </div>
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center self-center">
                      {isActive ? (
                        <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold">
                          <Check className="w-4 h-4" />
                        </div>
                      ) : (
                        <button
                          type="button"
                          className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-emerald-600 hover:text-white rounded-lg transition-colors flex items-center gap-1"
                        >
                          <span>Switch</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Multi-entity reconciliation with separate ledger & bank tracking per company</span>
          </div>
          <span className="font-bold text-slate-700">{companies.length} Companies Configured</span>
        </div>
      </div>
    </div>
  );
};
