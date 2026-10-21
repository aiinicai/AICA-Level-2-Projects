import React, { useState, useEffect } from 'react';
import {
  Menu,
  Home,
  Star,
  Flag,
  Bell,
  User as UserIcon,
  ChevronDown,
  LogOut,
  RefreshCw,
  CheckCircle,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import { getActiveUser, setActiveUser, signOut, checkCanApprove } from '../core/auth';
import { USERS } from '../data/users';
import { User } from '../core/types';
import { getDb, subscribeToDb } from '../core/storage';
import { WorklistModal } from './WorklistModal';

interface HeaderProps {
  onToggleNavigator: () => void;
  onNavigate: (route: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleNavigator, onNavigate }) => {
  const [currentUser, setCurrentUser] = useState<User>(getActiveUser());
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [notifDropdownOpen, setNotifDropdownOpen] = useState(false);
  const [favDropdownOpen, setFavDropdownOpen] = useState(false);
  const [worklistOpen, setWorklistOpen] = useState(false);
  const [dbState, setDbState] = useState(getDb());

  useEffect(() => {
    const handleUserChange = () => setCurrentUser(getActiveUser());
    window.addEventListener('medicore-user-changed', handleUserChange);
    const unsub = subscribeToDb(() => setDbState(getDb()));

    return () => {
      window.removeEventListener('medicore-user-changed', handleUserChange);
      unsub();
    };
  }, []);

  // Compute pending approvals live count awaiting THIS specific user's action
  const userPendingCount = [
    ...(dbState.apInvoices || []).filter(
      (i) => (i.status === 'Pending Approval' || i.status === 'Pending Higher Approval') && checkCanApprove(currentUser, i, 'Payables').allowed
    ),
    ...(dbState.arTransactions || []).filter(
      (i) => (i.status === 'Pending Approval' || i.status === 'Pending Higher Approval') && checkCanApprove(currentUser, i, 'Receivables').allowed
    ),
    ...(dbState.purchaseOrders || []).filter(
      (i) => i.status === 'Pending Approval' && checkCanApprove(currentUser, i, 'Procurement').allowed
    ),
    ...(dbState.requisitions || []).filter(
      (i) => i.status === 'Pending Approval' && checkCanApprove(currentUser, i, 'Procurement').allowed
    ),
    ...(dbState.receipts || []).filter(
      (i) => i.status === 'Pending Approval' && checkCanApprove(currentUser, i, 'Supply Chain Execution').allowed
    ),
    ...(dbState.cashVouchers || []).filter(
      (i) => i.status === 'Pending Approval' && checkCanApprove(currentUser, i, 'Cash Management').allowed
    ),
    ...(dbState.glJournals || []).filter(
      (i) => i.status === 'Pending Approval' && checkCanApprove(currentUser, { createdBy: i.createdBy, totalAmount: i.totalDebit, status: i.status }, 'General Accounting').allowed
    ),
  ].length;
  const totalPending = userPendingCount;

  const handleSwitchUser = (user: User) => {
    setActiveUser(user);
    setUserDropdownOpen(false);
  };

  return (
    <header className="no-print bg-[#3F1D5C] text-white h-14 px-4 flex items-center justify-between shadow-md relative z-40 select-none">
      {/* Left: Hamburger & Brand */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onToggleNavigator}
          title="Open Navigator"
          className="p-1.5 rounded hover:bg-[#5B2C83] transition-colors focus:outline-none focus:ring-1 focus:ring-amber-400"
        >
          <Menu className="w-5 h-5 text-gray-200" />
        </button>

        <div
          onClick={() => onNavigate('#/')}
          className="flex items-center space-x-2.5 cursor-pointer group"
        >
          {/* MediCore Hexagon Logo Mark */}
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#844db3] to-[#5B2C83] border border-plum-300/30 flex items-center justify-center shadow-inner group-hover:border-amber-400 transition-colors">
            <svg
              viewBox="0 0 24 24"
              className="w-5 h-5 text-amber-300 fill-current"
            >
              <polygon
                points="12,2 21,7.5 21,16.5 12,22 3,16.5 3,7.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              />
              <path
                d="M12 7v10M7 12h10"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-base tracking-tight text-white group-hover:text-amber-200 transition-colors">
              MediCore <span className="font-light text-plum-200">Connect</span>
            </span>
            <span className="text-[10px] text-plum-300 uppercase tracking-widest font-semibold -mt-1">
              Meridian Healthcare Group
            </span>
          </div>
        </div>
      </div>

      {/* Center status pill */}
      <div className="hidden md:flex items-center text-xs space-x-2 bg-[#29103e]/60 px-3 py-1 rounded-full border border-plum-500/30">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span className="text-gray-300">Open Period: <strong className="text-white">Oct-26</strong></span>
        <span className="text-plum-400">|</span>
        <span className="text-gray-300">Fiscal Anchor: <strong className="text-amber-300">19/Oct/2026</strong></span>
      </div>

      {/* Right icons */}
      <div className="flex items-center space-x-1 sm:space-x-2">
        {/* Home */}
        <button
          onClick={() => onNavigate('#/')}
          title="Home"
          className="p-2 rounded-full hover:bg-[#5B2C83] text-gray-200 transition-colors"
        >
          <Home className="w-4 h-4" />
        </button>

        {/* Favourites */}
        <div className="relative">
          <button
            onClick={() => {
              setFavDropdownOpen(!favDropdownOpen);
              setUserDropdownOpen(false);
              setNotifDropdownOpen(false);
            }}
            title="Favourites"
            className="p-2 rounded-full hover:bg-[#5B2C83] text-gray-200 transition-colors"
          >
            <Star className="w-4 h-4 text-amber-400 fill-amber-400/20" />
          </button>
          {favDropdownOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-xl border border-gray-200 text-gray-800 py-2 z-50">
              <div className="px-3 py-1.5 border-b border-gray-100 font-semibold text-xs text-gray-500 uppercase tracking-wider flex items-center justify-between">
                <span>Favorite Apps</span>
                <span className="text-amber-600">★</span>
              </div>
              <div className="py-1 text-sm">
                <button
                  onClick={() => { onNavigate('#/payables/invoices'); setFavDropdownOpen(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 hover:text-[#5B2C83] flex items-center space-x-2"
                >
                  <span className="w-2 h-2 rounded-full bg-[#5B2C83]"></span>
                  <span>Payables — Invoices</span>
                </button>
                <button
                  onClick={() => { onNavigate('#/fixed-assets/assets'); setFavDropdownOpen(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 hover:text-[#5B2C83] flex items-center space-x-2"
                >
                  <span className="w-2 h-2 rounded-full bg-[#5B2C83]"></span>
                  <span>Fixed Assets — Register & Additions</span>
                </button>
                <button
                  onClick={() => { onNavigate('#/general-accounting/journals'); setFavDropdownOpen(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 hover:text-[#5B2C83] flex items-center space-x-2"
                >
                  <span className="w-2 h-2 rounded-full bg-[#5B2C83]"></span>
                  <span>General Accounting — Journals</span>
                </button>
                <button
                  onClick={() => { onNavigate('#/reports/trial-balance'); setFavDropdownOpen(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 hover:text-[#5B2C83] flex items-center space-x-2"
                >
                  <span className="w-2 h-2 rounded-full bg-[#5B2C83]"></span>
                  <span>Reports — Trial Balance</span>
                </button>
                <button
                  onClick={() => { onNavigate('#/reports/ifrs'); setFavDropdownOpen(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 hover:text-[#5B2C83] flex items-center space-x-2"
                >
                  <span className="w-2 h-2 rounded-full bg-[#5B2C83]"></span>
                  <span>Reports — IFRS Financial Statements</span>
                </button>
                <button
                  onClick={() => { onNavigate('#/tools/integrity'); setFavDropdownOpen(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 hover:text-[#5B2C83] flex items-center space-x-2"
                >
                  <span className="w-2 h-2 rounded-full bg-emerald-600"></span>
                  <span className="font-medium text-emerald-700">Tools — System Integrity Check</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Tasks / Worklist */}
        <button
          onClick={() => setWorklistOpen(true)}
          title="Tasks / Worklist (My Approvals)"
          className="p-2 rounded-full hover:bg-[#5B2C83] text-gray-200 transition-colors relative cursor-pointer"
        >
          <Flag className="w-4 h-4" />
          {totalPending > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-amber-400 rounded-full animate-ping"></span>
          )}
        </button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => {
              setNotifDropdownOpen(!notifDropdownOpen);
              setUserDropdownOpen(false);
              setFavDropdownOpen(false);
            }}
            title="Notifications"
            className="p-2 rounded-full hover:bg-[#5B2C83] text-gray-200 transition-colors relative"
          >
            <Bell className="w-4 h-4" />
            {totalPending > 0 && (
              <span className="absolute -top-1 -right-1 bg-rose-600 text-[10px] font-bold text-white px-1.5 py-0.2 rounded-full shadow-sm animate-pulse">
                {totalPending}
              </span>
            )}
          </button>

          {notifDropdownOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-xl border border-gray-200 text-gray-800 py-2 z-50">
              <div className="px-3 py-2 border-b border-gray-100 flex items-center justify-between">
                <span className="font-semibold text-xs text-gray-700 uppercase tracking-wider">
                  Notifications ({dbState.notifications.length})
                </span>
                <span className="text-[11px] bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded-full">
                  {totalPending} Pending Approvals
                </span>
              </div>
              <div className="max-h-72 overflow-y-auto divide-y divide-gray-100 text-xs">
                {dbState.notifications.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => {
                      if (n.linkUrl) onNavigate(n.linkUrl);
                      setNotifDropdownOpen(false);
                    }}
                    className="p-3 hover:bg-plum-50 cursor-pointer transition-colors"
                  >
                    <div className="font-semibold text-gray-800 flex items-center justify-between">
                      <span>{n.title}</span>
                      <span className="text-[10px] text-gray-400">19/Oct</span>
                    </div>
                    <p className="text-gray-600 mt-1">{n.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User Avatar Menu */}
        <div className="relative ml-2">
          <button
            onClick={() => {
              setUserDropdownOpen(!userDropdownOpen);
              setNotifDropdownOpen(false);
              setFavDropdownOpen(false);
            }}
            className="flex items-center space-x-2 pl-2 pr-1.5 py-1 rounded-full hover:bg-[#5B2C83] transition-colors border border-plum-400/40"
          >
            <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-amber-500 to-amber-300 text-[#3F1D5C] font-bold text-xs flex items-center justify-center shadow">
              {currentUser.name
                .split(' ')
                .map((n) => n[0])
                .join('')}
            </div>
            <div className="hidden sm:flex flex-col text-left text-xs leading-tight">
              <span className="font-semibold text-gray-100 truncate max-w-[120px]">
                {currentUser.name}
              </span>
              <span className="text-[10px] text-plum-200 truncate max-w-[120px]">
                {currentUser.role}
              </span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-plum-200" />
          </button>

          {userDropdownOpen && (
            <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-2xl border border-gray-200 text-gray-800 py-2 z-50 animate-in fade-in slide-in-from-top-2">
              <div className="px-4 py-2 border-b border-gray-100">
                <p className="text-xs text-gray-500 font-medium">Signed in as</p>
                <p className="font-bold text-sm text-[#3F1D5C]">{currentUser.name}</p>
                <div className="flex items-center justify-between mt-1 text-xs">
                  <span className="text-gray-600">{currentUser.role}</span>
                  <span className="bg-plum-100 text-[#5B2C83] font-medium px-2 py-0.5 rounded text-[11px]">
                    Limit: {currentUser.approvalLimitAED ? `AED ${currentUser.approvalLimitAED.toLocaleString()}` : 'Unlimited'}
                  </span>
                </div>
              </div>

              {/* Demo Switch User Helper */}
              <div className="px-4 py-2 border-b border-gray-100 bg-plum-50/50">
                <div className="flex items-center space-x-1 text-xs font-semibold text-[#5B2C83] mb-1.5">
                  <RefreshCw className="w-3 h-3 text-[#5B2C83]" />
                  <span>Switch User (Demo Checker / Maker)</span>
                </div>
                <div className="grid grid-cols-1 gap-1">
                  {USERS.map((u) => (
                    <button
                      key={u.userId}
                      onClick={() => handleSwitchUser(u)}
                      className={`text-left px-2.5 py-1.5 rounded text-xs flex items-center justify-between transition-colors ${
                        currentUser.userId === u.userId
                          ? 'bg-[#5B2C83] text-white font-medium'
                          : 'hover:bg-plum-100/70 text-gray-700'
                      }`}
                    >
                      <div>
                        <div className="font-medium">{u.name}</div>
                        <div className={`text-[10px] ${currentUser.userId === u.userId ? 'text-plum-200' : 'text-gray-500'}`}>
                          {u.role} {u.approvalLimitAED ? `(AED ${u.approvalLimitAED.toLocaleString()})` : u.approvalLimitAED === null ? '(Unlimited)' : ''}
                        </div>
                      </div>
                      {currentUser.userId === u.userId && <CheckCircle className="w-3.5 h-3.5 text-amber-300" />}
                    </button>
                  ))}
                </div>
              </div>

              {/* Menu items */}
              <div className="pt-1 text-xs">
                <button
                  onClick={() => {
                    onNavigate('#/tools/administration');
                    setUserDropdownOpen(false);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center space-x-2 text-gray-700"
                >
                  <UserIcon className="w-3.5 h-3.5 text-gray-500" />
                  <span>Administration & Master Charts</span>
                </button>
                <button
                  onClick={() => {
                    onNavigate('#/tools/integrity');
                    setUserDropdownOpen(false);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center space-x-2 text-emerald-700 font-medium"
                >
                  <ShieldAlert className="w-3.5 h-3.5 text-emerald-600" />
                  <span>System Integrity Self-Check</span>
                </button>
                <button
                  onClick={() => {
                    signOut();
                    setUserDropdownOpen(false);
                  }}
                  className="w-full text-left px-4 py-2 hover:bg-rose-50 flex items-center space-x-2 text-rose-600 font-medium"
                >
                  <LogOut className="w-3.5 h-3.5 text-rose-500" />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <WorklistModal
        isOpen={worklistOpen}
        onClose={() => setWorklistOpen(false)}
        onNavigate={onNavigate}
      />
    </header>
  );
};
