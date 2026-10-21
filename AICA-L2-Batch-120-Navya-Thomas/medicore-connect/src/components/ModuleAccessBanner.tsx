import React from 'react';
import { ShieldCheck, UserCheck, Eye, Lock, ArrowRight } from 'lucide-react';
import { ERPModule } from '../core/types';
import { getActiveUser } from '../core/auth';
import { getModuleAccess, getUserModuleRole } from '../core/accessMatrix';

interface ModuleAccessBannerProps {
  module: ERPModule;
  onNavigate?: (route: string) => void;
  className?: string;
}

export const ModuleAccessBanner: React.FC<ModuleAccessBannerProps> = ({
  module,
  onNavigate,
  className = '',
}) => {
  const currentUser = getActiveUser();
  const access = getModuleAccess(module);
  const userRole = getUserModuleRole(currentUser, module);

  const isMaker = userRole === 'Maker';
  const isApprover = userRole === 'Approver';
  const isViewer = userRole === 'Viewer';

  return (
    <div
      className={`no-print py-1.5 px-3.5 mb-4 rounded-lg text-xs flex flex-wrap items-center justify-between gap-2 border shadow-2xs transition-colors ${
        isMaker
          ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900'
          : isApprover
          ? 'bg-amber-50/80 border-amber-200 text-amber-950'
          : 'bg-plum-50/60 border-plum-200/60 text-gray-700'
      } ${className}`}
    >
      <div className="flex items-center space-x-2.5 flex-wrap">
        <span className="font-semibold text-gray-500 uppercase tracking-wider text-[10px]">
          Access:
        </span>

        {/* Current user role badge */}
        <span
          className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full font-bold text-[11px] ${
            isMaker
              ? 'bg-emerald-600 text-white shadow-2xs'
              : isApprover
              ? 'bg-amber-600 text-white shadow-2xs'
              : 'bg-plum-100 text-[#5B2C83] border border-plum-300/60'
          }`}
        >
          {isMaker && <UserCheck className="w-3 h-3 inline" />}
          {isApprover && <ShieldCheck className="w-3 h-3 inline" />}
          {isViewer && <Eye className="w-3 h-3 inline" />}
          <span>
            {isMaker
              ? `You are the Maker (${currentUser.name})`
              : isApprover
              ? `You are the Approver (${currentUser.name})`
              : 'You are a Viewer (Read-Only)'}
          </span>
        </span>

        <span className="text-gray-300 font-light">|</span>

        {/* Maker Info */}
        <span className="text-gray-700">
          Maker:{' '}
          <strong
            className={
              isMaker ? 'text-emerald-700 font-bold underline decoration-emerald-400' : 'text-gray-900'
            }
          >
            {access.makerName}
          </strong>
        </span>

        <span className="text-gray-300 font-light">|</span>

        {/* Approver Info */}
        <span className="text-gray-700">
          Approver:{' '}
          <strong
            className={
              isApprover ? 'text-amber-800 font-bold underline decoration-amber-400' : 'text-gray-900'
            }
          >
            {access.approverName}
          </strong>
          {access.approvalLimitAED && (
            <span className="text-gray-500 font-normal ml-1">
              (Limit: AED {access.approvalLimitAED.toLocaleString()})
            </span>
          )}
        </span>
      </div>

      <div className="flex items-center space-x-2">
        {isViewer && (
          <span className="text-[11px] text-gray-500 italic flex items-center space-x-1">
            <Lock className="w-3 h-3 text-gray-400" />
            <span>Create & approval controls disabled</span>
          </span>
        )}

        {onNavigate && (
          <button
            onClick={() => onNavigate('#/tools/access-roles')}
            className="text-[11px] font-semibold text-[#5B2C83] hover:text-[#3F1D5C] hover:underline flex items-center space-x-0.5 cursor-pointer"
          >
            <span>Roles Matrix</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
};
