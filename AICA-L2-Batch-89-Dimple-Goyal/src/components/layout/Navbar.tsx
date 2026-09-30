import React, { useState } from 'react';
import {
  Search,
  Bell,
  Building2,
  UserCheck,
  ChevronDown,
  FileCheck2,
  AlertTriangle,
  RotateCcw,
  Menu,
  Edit2,
  Check,
  X,
  Users,
  LogOut,
  Lock,
  Plus
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { UserRole } from '../../types';
import { CompanySwitcherModal } from '../company/CompanySwitcherModal';
import { AddCompanyModal } from '../company/AddCompanyModal';

interface NavbarProps {
  onOpenSearch: () => void;
  onOpenNotifications: () => void;
  onToggleSidebar?: () => void;
  unreadNotificationsCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenSearch,
  onOpenNotifications,
  onToggleSidebar,
  unreadNotificationsCount
}) => {
  const {
    company,
    companies,
    activeCompanyId,
    switchCompany,
    addCompany,
    currentUser,
    setCurrentUserRole,
    resetToDemoData,
    updateUserName,
    logout
  } = useApp();

  const [roleDropdownOpen, setRoleDropdownOpen] = useState(false);
  const [isCompanySwitcherOpen, setIsCompanySwitcherOpen] = useState(false);
  const [isAddCompanyOpen, setIsAddCompanyOpen] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(currentUser.name);
  const [nameSavedToast, setNameSavedToast] = useState(false);
  const [resetToast, setResetToast] = useState(false);

  const handleResetData = () => {
    resetToDemoData();
    setResetToast(true);
    setTimeout(() => setResetToast(false), 3000);
  };

  const roles: UserRole[] = [
    'Business Owner',
    'Accountant',
    'Finance Manager',
    'CA / Consultant',
    'Viewer'
  ];

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 px-3 sm:px-6 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-2 sm:gap-3">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="md:hidden p-2 text-slate-600 hover:bg-slate-100 rounded-lg"
              aria-label="Toggle menu"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
          
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-emerald-700 text-white flex items-center justify-center font-bold text-base sm:text-lg shadow-sm">
              ₹
            </div>
            
            {/* Interactive Company Switcher Button */}
            <button
              onClick={() => setIsCompanySwitcherOpen(true)}
              className="flex items-center gap-2 px-2.5 py-1 text-left rounded-xl hover:bg-slate-100/90 border border-slate-200 hover:border-emerald-300 transition-all group"
              title="Click to Switch Company or Add Entity"
            >
              <div className="w-6 h-6 rounded-md bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0 border border-emerald-200">
                <Building2 className="w-3.5 h-3.5" />
              </div>
              <div className="truncate max-w-[130px] sm:max-w-[190px] md:max-w-[240px]">
                <div className="flex items-center gap-1">
                  <span className="font-bold text-slate-900 text-xs truncate group-hover:text-emerald-800 transition-colors">
                    {company.name}
                  </span>
                  <ChevronDown className="w-3 h-3 text-slate-400 group-hover:text-slate-700 shrink-0" />
                </div>
                <div className="text-[10px] text-slate-500 font-medium flex items-center gap-1 truncate">
                  <span className="font-mono text-[9px] text-emerald-800 font-semibold">{company.gstin}</span>
                  <span className="text-slate-300 hidden sm:inline">•</span>
                  <span className="text-[9px] font-bold text-slate-600 hidden sm:inline">FY {company.financialYear}</span>
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* Center: Search Bar */}
        <div className="hidden lg:flex items-center max-w-md w-full mx-4">
          <button
            onClick={onOpenSearch}
            className="w-full flex items-center gap-2.5 px-3.5 py-1.5 text-xs text-slate-400 bg-slate-100 hover:bg-slate-200/80 rounded-lg border border-slate-200 transition-colors text-left"
          >
            <Search className="w-4 h-4 text-slate-400 shrink-0" />
            <span className="truncate">Search customer, invoice, UTR, PAN...</span>
            <kbd className="hidden xl:inline-block ml-auto text-[10px] font-mono bg-white px-1.5 py-0.5 rounded text-slate-500 border border-slate-300">
              Ctrl+K
            </kbd>
          </button>
        </div>

        {/* Right Side: Reset Data, Notifications, User */}
        <div className="flex items-center gap-1.5 sm:gap-2.5">
          {/* Quick Add Company Button */}
          <button
            onClick={() => setIsAddCompanyOpen(true)}
            title="Add New Company Entity"
            className="hidden sm:flex items-center gap-1 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-200 transition-colors shadow-2xs"
          >
            <Plus className="w-3.5 h-3.5 text-emerald-600" />
            <span>New Entity</span>
          </button>

          {/* Reset Demo Data button */}
          <button
            onClick={handleResetData}
            title="Reset back to initial FY 2026-27 master demo data"
            className="flex items-center gap-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 hover:text-emerald-900 px-2.5 py-1.5 rounded-lg border border-emerald-300 transition-colors shadow-2xs"
          >
            <RotateCcw className="w-3.5 h-3.5 text-emerald-700" />
            <span className="hidden xl:inline">Reset FY 2026-27 Data</span>
            <span className="xl:hidden">Reset</span>
          </button>

          {/* Notifications Icon */}
          <button
            onClick={onOpenNotifications}
            className="relative p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors"
            title="Notifications & Exceptions"
          >
            <Bell className="w-5 h-5" />
            {unreadNotificationsCount > 0 && (
              <span className="absolute top-1.5 right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-rose-600 text-[10px] font-bold text-white ring-2 ring-white">
                {unreadNotificationsCount > 9 ? '9+' : unreadNotificationsCount}
              </span>
            )}
          </button>

          {/* User Profile & Role Switcher */}
          <div className="relative">
            <button
              onClick={() => setRoleDropdownOpen(!roleDropdownOpen)}
              className="flex items-center gap-2 p-1 sm:px-2.5 sm:py-1 rounded-xl hover:bg-slate-100 border border-transparent hover:border-slate-200 transition-colors text-left"
            >
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-emerald-700 text-white flex items-center justify-center font-bold text-xs uppercase shadow-xs">
                {currentUser.name.charAt(0)}
              </div>
              <div className="hidden sm:block text-left">
                <div className="flex items-center gap-1">
                  <p className="text-xs font-bold text-slate-800 leading-tight truncate max-w-[100px]">
                    {currentUser.name}
                  </p>
                  <ChevronDown className="w-3 h-3 text-slate-400" />
                </div>
                <p className="text-[10px] text-emerald-800 font-semibold leading-tight">
                  {currentUser.role}
                </p>
              </div>
            </button>

            {roleDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => {
                    setRoleDropdownOpen(false);
                    setIsEditingName(false);
                  }}
                />
                <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-xl border border-slate-200 py-1.5 z-50 text-xs">
                  {/* User Profile info */}
                  <div className="px-3.5 py-3 border-b border-slate-100 bg-slate-50/80">
                    {isEditingName ? (
                      <div className="space-y-2">
                        <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          Edit Your Display Name
                        </label>
                        <input
                          type="text"
                          value={nameInput}
                          onChange={(e) => setNameInput(e.target.value)}
                          className="w-full px-2.5 py-1.5 text-xs font-semibold border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500/20 bg-white"
                          autoFocus
                        />
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => {
                              setIsEditingName(false);
                              setNameInput(currentUser.name);
                            }}
                            className="px-2 py-1 text-[11px] font-semibold text-slate-600 hover:bg-slate-200 rounded"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => {
                              if (nameInput.trim()) {
                                updateUserName(currentUser.id, nameInput.trim());
                                setIsEditingName(false);
                                setNameSavedToast(true);
                                setTimeout(() => setNameSavedToast(false), 2500);
                              }
                            }}
                            className="px-2.5 py-1 text-[11px] font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded flex items-center gap-1 shadow-xs"
                          >
                            <Check className="w-3 h-3" />
                            <span>Save</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <p className="font-bold text-slate-900 text-sm truncate">{currentUser.name}</p>
                          <button
                            onClick={() => {
                              setNameInput(currentUser.name);
                              setIsEditingName(true);
                            }}
                            className="px-2 py-0.5 bg-white hover:bg-emerald-50 text-emerald-800 border border-slate-200 hover:border-emerald-300 rounded font-semibold text-[10px] flex items-center gap-1 transition-colors shadow-2xs"
                            title="Edit Your Name"
                          >
                            <Edit2 className="w-3 h-3" />
                            <span>Edit</span>
                          </button>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-500">
                          <span>User ID: <strong className="font-mono text-slate-800">{currentUser.userId || 'N/A'}</strong></span>
                          <span className="font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 text-[10px]">
                            {currentUser.role}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 truncate mt-0.5">{currentUser.email}</p>
                      </div>
                    )}
                  </div>

                  {/* Switch Company quick option in menu */}
                  <div className="p-2 border-b border-slate-100">
                    <button
                      onClick={() => {
                        setRoleDropdownOpen(false);
                        setIsCompanySwitcherOpen(true);
                      }}
                      className="w-full flex items-center justify-between px-3 py-2 text-slate-700 hover:bg-slate-50 rounded-lg transition-colors border border-slate-200"
                    >
                      <div className="flex items-center gap-2">
                        <Building2 className="w-3.5 h-3.5 text-emerald-700" />
                        <span className="font-semibold text-xs text-slate-800">Switch Company</span>
                      </div>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                        {companies.length} Entities
                      </span>
                    </button>
                  </div>

                  {/* Role Switcher */}
                  <div className="px-3.5 py-1.5">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Switch Role Permissions</p>
                  </div>
                  <div className="py-1">
                    {roles.map((r) => (
                      <button
                        key={r}
                        onClick={() => {
                          setCurrentUserRole(r);
                          setRoleDropdownOpen(false);
                        }}
                        className={`w-full text-left px-3.5 py-1.5 flex items-center justify-between hover:bg-slate-50 transition-colors ${
                          currentUser.role === r ? 'font-bold text-emerald-800 bg-emerald-50/50' : 'text-slate-700'
                        }`}
                      >
                        <span>{r}</span>
                        {currentUser.role === r && <UserCheck className="w-3.5 h-3.5 text-emerald-600" />}
                      </button>
                    ))}
                  </div>

                  {/* Logout Button */}
                  <div className="p-2 border-t border-slate-100 mt-1">
                    <button
                      onClick={() => {
                        setRoleDropdownOpen(false);
                        logout();
                      }}
                      className="w-full flex items-center justify-between px-3 py-2 text-rose-700 hover:bg-rose-50 rounded-lg font-bold text-xs transition-colors border border-rose-200"
                    >
                      <div className="flex items-center gap-2">
                        <LogOut className="w-3.5 h-3.5" />
                        <span>Sign Out / Switch User</span>
                      </div>
                      <span className="text-[10px] bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded font-bold">Lock ID</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {resetToast && (
          <div className="absolute top-16 left-1/2 -translate-x-1/2 mt-2 px-4 py-2 bg-emerald-900 text-white text-xs font-semibold rounded-lg shadow-lg flex items-center gap-2 border border-emerald-700 z-50">
            <Check className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>All records updated to FY 2026-27 master data (INV-2026-001... & 2026 bank entries)</span>
          </div>
        )}
      </header>

      {/* Company Switcher Modal */}
      <CompanySwitcherModal
        isOpen={isCompanySwitcherOpen}
        onClose={() => setIsCompanySwitcherOpen(false)}
        companies={companies}
        activeCompanyId={activeCompanyId}
        currentUser={currentUser}
        onSelectCompany={(compId) => switchCompany(compId)}
        onOpenAddCompany={() => setIsAddCompanyOpen(true)}
      />

      {/* Add Company Modal */}
      <AddCompanyModal
        isOpen={isAddCompanyOpen}
        onClose={() => setIsAddCompanyOpen(false)}
        onAddCompany={(newComp, seedData) => addCompany(newComp, seedData)}
      />
    </>
  );
};
