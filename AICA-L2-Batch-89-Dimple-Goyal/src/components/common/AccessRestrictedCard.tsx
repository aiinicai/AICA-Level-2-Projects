import React from 'react';
import { ShieldAlert, ArrowLeft, Users, Lock, ChevronRight } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { ActiveTab } from '../layout/Sidebar';
import { ROLE_DEFINITIONS, getTabTitle, getAuthorizedRolesForTab } from '../../utils/rbac';
import { UserRole } from '../../types';

interface AccessRestrictedCardProps {
  attemptedTab: ActiveTab;
  onNavigateHome: () => void;
}

export const AccessRestrictedCard: React.FC<AccessRestrictedCardProps> = ({
  attemptedTab,
  onNavigateHome
}) => {
  const { currentUser, setCurrentUserRole } = useApp();
  const currentRolePerms = ROLE_DEFINITIONS[currentUser.role];
  const tabTitle = getTabTitle(attemptedTab);
  const authorizedRoles = getAuthorizedRolesForTab(attemptedTab);

  return (
    <div className="min-h-[500px] flex items-center justify-center p-6">
      <div className="bg-white max-w-xl w-full rounded-2xl border border-slate-200 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="bg-rose-50 border-b border-rose-100 p-6 flex items-start gap-4">
          <div className="p-3 bg-rose-100 text-rose-700 rounded-xl shrink-0">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-rose-700 bg-rose-200/60 px-2 py-0.5 rounded-full">
                Role-Based Access Control
              </span>
              <span className="text-xs text-rose-500 font-mono">HTTP 403 Forbidden</span>
            </div>
            <h2 className="text-lg font-bold text-slate-900 mt-1">
              Access Restricted to &ldquo;{tabTitle}&rdquo;
            </h2>
            <p className="text-xs text-slate-600 mt-1">
              Your active role <strong className="text-slate-900 font-semibold">{currentUser.role}</strong> does not have permission to view or execute operations in this module.
            </p>
          </div>
        </div>

        <div className="p-6 space-y-5">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-2">
            <div className="flex items-center justify-between text-slate-700 font-semibold">
              <span>Your Current Role Permissions:</span>
              <span className={`px-2 py-0.5 rounded-md border text-[11px] font-bold ${currentRolePerms.badgeClass}`}>
                {currentUser.role}
              </span>
            </div>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              {currentRolePerms.description}
            </p>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              Roles permitted to access this module:
            </p>
            <div className="flex flex-wrap gap-2">
              {authorizedRoles.map(r => (
                <span
                  key={r}
                  className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200"
                >
                  ✓ {r}
                </span>
              ))}
            </div>
          </div>

          {/* Quick Role Switcher for demonstration/testing */}
          <div className="pt-3 border-t border-slate-100">
            <p className="text-xs font-semibold text-slate-700 mb-2 flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-emerald-600" />
              Switch active role to test authorized access:
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {authorizedRoles.map(role => (
                <button
                  key={role}
                  onClick={() => setCurrentUserRole(role as UserRole)}
                  className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-emerald-50 hover:text-emerald-900 border border-slate-200 hover:border-emerald-300 rounded-lg transition-colors text-left flex items-center justify-between group"
                >
                  <span className="truncate">{role}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-600 shrink-0" />
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              onClick={onNavigateHome}
              className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Return to Dashboard</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
