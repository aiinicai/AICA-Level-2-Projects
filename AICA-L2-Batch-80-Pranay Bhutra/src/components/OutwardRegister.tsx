import React, { useState } from 'react';
import {
  Truck,
  Plus,
  Search,
  Filter,
  User,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  FileText,
  DollarSign,
  ExternalLink,
  Navigation,
  Lock,
  Globe
} from 'lucide-react';
import { OutwardShipment, UserProfile, ShipmentStatus, ThemeStyle } from '../types';
import { getCarrierTracking } from '../utils/carrierTracking';
import { ManualTrackingModal } from './ManualTrackingModal';
import { THEMES } from '../utils/theme';

interface OutwardRegisterProps {
  outwardList: OutwardShipment[];
  currentUser: UserProfile;
  currentTheme?: ThemeStyle;
  onOpenNewOutward: () => void;
  onOpenShipmentDetail: (shipment: OutwardShipment, type: 'outward') => void;
  onOpenPODModal: (shipment: OutwardShipment, type: 'outward') => void;
  onOpenUpdateStatus: (shipment: OutwardShipment, type: 'outward') => void;
}

export const OutwardRegister: React.FC<OutwardRegisterProps> = ({
  outwardList,
  currentUser,
  currentTheme = 'navy',
  onOpenNewOutward,
  onOpenShipmentDetail,
  onOpenPODModal,
  onOpenUpdateStatus,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [assigneeFilter, setAssigneeFilter] = useState<string>('all');
  const [manualTrackingShipment, setManualTrackingShipment] = useState<OutwardShipment | null>(null);

  const themeConfig = THEMES[currentTheme] || THEMES.navy;

  // RBAC Permission Check:
  // Partner & Desk can see all dispatches. Staff accounts (audit_staff) see ONLY dispatches assigned to them.
  const hasFullAccess = currentUser?.role === 'admin_partner' || currentUser?.role === 'front_desk';

  const userScopedList = outwardList.filter((item) => {
    if (hasFullAccess) return true;
    return (
      (currentUser?.id && item.assignedStaffId === currentUser.id) ||
      (currentUser?.name && item.assignedStaffName.toLowerCase().includes(currentUser.name.toLowerCase()))
    );
  });

  const filteredList = userScopedList.filter((item) => {
    const matchesSearch =
      item.referenceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.trackingNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.clientName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.clientJobCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.recipientName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.assignedStaffName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.carrier.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
    const matchesAssignee =
      !hasFullAccess
        ? true
        : assigneeFilter === 'all'
        ? true
        : assigneeFilter === 'my_dispatches'
        ? (currentUser?.id ? item.assignedStaffId === currentUser.id : true)
        : true;

    return matchesSearch && matchesStatus && matchesAssignee;
  });

  const getStatusBadge = (status: ShipmentStatus) => {
    switch (status) {
      case 'delivered':
        return { label: 'Delivered (POD Verified)', bg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' };
      case 'out_for_delivery':
        return { label: 'Out for Delivery', bg: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20' };
      case 'in_transit':
        return { label: 'In Transit', bg: `${themeConfig.badgeBg} ${themeConfig.badgeText}` };
      case 'dispatched':
        return { label: 'Dispatched', bg: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20' };
      default:
        return { label: 'Draft / Requested', bg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20' };
    }
  };

  const handleTrackCarrier = (item: OutwardShipment) => {
    const trackingInfo = getCarrierTracking(item.carrier, item.trackingNumber);
    if (trackingInfo.isTrackable && trackingInfo.trackingUrl) {
      window.open(trackingInfo.trackingUrl, '_blank', 'noopener,noreferrer');
    } else {
      setManualTrackingShipment(item);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Action & Search Bar */}
      <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${themeConfig.cardBg} p-4 rounded-xl border ${themeConfig.cardBorder} backdrop-blur-sm shadow-sm transition-colors duration-300`}>
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${themeConfig.badgeBg} border text-blue-500`}>
            <Truck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className={`text-base font-bold ${themeConfig.textPrimary}`}>
                Outward Dispatch Register
              </h2>
              <span className={`text-xs px-2 py-0.5 rounded-full ${themeConfig.subCardBg} ${themeConfig.textSecondary} font-mono border ${themeConfig.cardBorder}`}>
                {filteredList.length} Dispatches
              </span>
              {!hasFullAccess ? (
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${themeConfig.badgeBg} ${themeConfig.badgeText} flex items-center gap-1`}>
                  <Lock className="w-3 h-3" />
                  Personal View ({currentUser.name})
                </span>
              ) : (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                  <Globe className="w-3 h-3" />
                  Firm-Wide View ({currentUser.role === 'admin_partner' ? 'Partner' : 'Desk'})
                </span>
              )}
            </div>
            <p className={`text-xs ${themeConfig.textMuted} mt-0.5`}>
              Client matter cost-recovery tagging, carrier tracking, and live delivery status.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenNewOutward}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl ${themeConfig.primaryBtn} text-xs font-semibold transition-all shadow-md active:scale-95`}
          >
            <Plus className="w-4 h-4" />
            <span>Create Dispatch Docket</span>
          </button>
        </div>
      </div>

      {/* RBAC Notice for Staff */}
      {!hasFullAccess && (
        <div className={`p-3 rounded-xl ${themeConfig.badgeBg} text-xs ${themeConfig.badgeText} flex items-center justify-between gap-2`}>
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 shrink-0" />
            <span>
              <b>Privacy & Custody Isolation:</b> You are viewing courier dispatches assigned to <b>{currentUser.name}</b>. (To view all firm-wide dispatches, switch role to Partner or Front Desk in the top right).
            </span>
          </div>
        </div>
      )}

      {/* Filter Row */}
      <div className={`grid grid-cols-1 ${hasFullAccess ? 'sm:grid-cols-3' : 'sm:grid-cols-2'} gap-3`}>
        {/* Search Input */}
        <div className="relative">
          <Search className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3.5 top-3`} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by Client, AWB, Carrier..."
            className={`w-full pl-10 pr-4 py-2.5 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs font-mono focus:outline-none transition-colors`}
          />
        </div>

        {/* Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className={`px-3.5 py-2.5 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs focus:outline-none transition-colors`}
        >
          <option value="all">All Delivery Statuses</option>
          <option value="dispatched">Dispatched</option>
          <option value="in_transit">In Transit</option>
          <option value="out_for_delivery">Out for Delivery</option>
          <option value="delivered">Delivered (POD Available)</option>
        </select>

        {/* Assignee Filter (Only for Partner / Desk) */}
        {hasFullAccess && (
          <select
            value={assigneeFilter}
            onChange={(e) => setAssigneeFilter(e.target.value)}
            className={`px-3.5 py-2.5 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs focus:outline-none transition-colors`}
          >
            <option value="all">All Staff Dispatches</option>
            <option value="my_dispatches">My Assigned Dispatches ({currentUser.name})</option>
          </select>
        )}
      </div>

      {/* Outward Shipments Table */}
      <div className={`rounded-xl border ${themeConfig.cardBorder} ${themeConfig.cardBg} overflow-hidden shadow-lg transition-colors duration-300`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className={`${themeConfig.tableHeaderBg} border-b ${themeConfig.cardBorder} uppercase tracking-wider font-semibold text-[11px]`}>
                <th className="py-3 px-4">Docket & AWB No.</th>
                <th className="py-3 px-4">Client Matter / Cost Code</th>
                <th className="py-3 px-4">Addressee & Organization</th>
                <th className="py-3 px-4">Assigned Staff</th>
                <th className="py-3 px-4">Carrier & Cost</th>
                <th className="py-3 px-4">Live Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${themeConfig.cardBorder}`}>
              {filteredList.length === 0 ? (
                <tr>
                  <td colSpan={7} className={`py-8 text-center ${themeConfig.textMuted}`}>
                    No outward dispatches found matching your filters.
                  </td>
                </tr>
              ) : (
                filteredList.map((item) => {
                  const statusInfo = getStatusBadge(item.status);
                  const isAssignedToCurrentUser = item.assignedStaffId === currentUser.id;
                  const tracking = getCarrierTracking(item.carrier, item.trackingNumber);

                  return (
                    <tr
                      key={item.id}
                      className={`${themeConfig.tableRowHover} transition-colors ${
                        isAssignedToCurrentUser ? 'bg-blue-500/5' : ''
                      }`}
                    >
                      {/* Docket & AWB */}
                      <td className="py-3.5 px-4">
                        <div className={`font-mono font-bold ${themeConfig.textPrimary} flex items-center gap-1.5`}>
                          <span>{item.referenceNumber}</span>
                        </div>
                        <span className={`font-mono text-[11px] ${themeConfig.textAccent} block mt-0.5 font-semibold`}>
                          AWB #{item.trackingNumber}
                        </span>
                        <span className={`text-[10px] ${themeConfig.textMuted} block`}>
                          {item.packageType}
                        </span>
                      </td>

                      {/* Client Code */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1 font-mono font-semibold text-amber-500">
                          <Building2 className="w-3.5 h-3.5" />
                          <span>{item.clientJobCode}</span>
                        </div>
                        <span className={`text-[11px] ${themeConfig.textPrimary} font-medium block truncate max-w-[170px] mt-0.5`}>
                          {item.clientName}
                        </span>
                        <span className={`text-[10px] ${themeConfig.textMuted} block`}>
                          Partner: {item.partnerInCharge}
                        </span>
                      </td>

                      {/* Addressee */}
                      <td className="py-3.5 px-4">
                        <span className={`font-medium ${themeConfig.textPrimary} block truncate max-w-[180px]`}>
                          {item.recipientName}
                        </span>
                        <span className={`text-[11px] ${themeConfig.textMuted} block truncate max-w-[180px]`}>
                          {item.recipientOrganization}
                        </span>
                        <span className={`text-[10px] ${themeConfig.textMuted} block truncate max-w-[180px]`}>
                          {item.recipientCity}
                        </span>
                      </td>

                      {/* Assigned Staff */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          <User className={`w-3.5 h-3.5 ${themeConfig.textAccent}`} />
                          <span className={`font-semibold ${themeConfig.textPrimary}`}>
                            {item.assignedStaffName}
                          </span>
                        </div>
                        {isAssignedToCurrentUser && (
                          <span className={`inline-block text-[9px] font-semibold uppercase px-1.5 py-0.2 rounded ${themeConfig.badgeBg} ${themeConfig.badgeText} mt-1`}>
                            Assigned to You
                          </span>
                        )}
                        <span className={`text-[10px] ${themeConfig.textMuted} block mt-0.5`}>
                          {item.department}
                        </span>
                      </td>

                      {/* Carrier & Cost */}
                      <td className="py-3.5 px-4">
                        <span className={`font-medium ${themeConfig.textSecondary} block`}>
                          {item.carrier}
                        </span>
                        <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold block mt-0.5">
                          ₹{item.courierCost}
                          <span className={`text-[10px] ${themeConfig.textMuted} font-normal ml-1`}>
                            ({item.weightKg} kg)
                          </span>
                        </span>
                        <span className={`text-[9px] ${themeConfig.textMuted} block`}>
                          {item.billableToClient ? 'Billable to Client' : 'Firm Admin Cost'}
                        </span>
                      </td>

                      {/* Live Status */}
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-block text-[10px] font-semibold uppercase px-2.5 py-0.5 rounded-full border mb-1 ${statusInfo.bg}`}
                        >
                          {statusInfo.label}
                        </span>
                        <span className={`text-[10px] ${themeConfig.textMuted} flex items-center gap-1`}>
                          <Calendar className={`w-3 h-3 ${themeConfig.textMuted}`} />
                          {item.dispatchedAt.split(' ')[0]}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Real-time Tracking Button */}
                          <button
                            onClick={() => handleTrackCarrier(item)}
                            className={`p-1.5 rounded-lg ${themeConfig.subCardBg} ${themeConfig.cardHover} ${themeConfig.textAccent} border ${themeConfig.cardBorder} transition-colors flex items-center gap-1`}
                            title="Trace carrier airway bill"
                          >
                            <Navigation className="w-3.5 h-3.5" />
                            <span className="text-[11px] font-medium hidden sm:inline">Trace</span>
                          </button>

                          {/* Digital POD Scanner/Viewer */}
                          <button
                            onClick={() => onOpenPODModal(item, 'outward')}
                            className="p-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30 transition-colors"
                            title={item.proofOfDelivery ? 'View Verified POD' : 'Scan Proof of Delivery'}
                          >
                            <ShieldCheck className="w-4 h-4" />
                          </button>

                          {hasFullAccess && (
                            <button
                              onClick={() => onOpenUpdateStatus(item, 'outward')}
                              className={`p-1.5 rounded-lg ${themeConfig.subCardBg} ${themeConfig.cardHover} ${themeConfig.textSecondary} border ${themeConfig.cardBorder} transition-colors`}
                              title="Update Status Milestone"
                            >
                              <CheckCircle2 className="w-4 h-4" />
                            </button>
                          )}

                          <button
                            onClick={() => onOpenShipmentDetail(item, 'outward')}
                            className={`p-1.5 rounded-lg ${themeConfig.subCardBg} ${themeConfig.cardHover} ${themeConfig.textPrimary} border ${themeConfig.cardBorder} transition-colors`}
                            title="Full Docket Details"
                          >
                            <ArrowRight className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Tracking Helper Modal if needed */}
      {manualTrackingShipment && (
        <ManualTrackingModal
          isOpen={!!manualTrackingShipment}
          onClose={() => setManualTrackingShipment(null)}
          carrier={manualTrackingShipment.carrier}
          trackingNumber={manualTrackingShipment.trackingNumber}
        />
      )}
    </div>
  );
};
