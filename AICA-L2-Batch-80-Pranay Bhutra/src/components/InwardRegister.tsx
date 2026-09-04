import React, { useState } from 'react';
import {
  Package,
  Plus,
  Search,
  Filter,
  MapPin,
  Clock,
  ShieldCheck,
  User,
  AlertTriangle,
  Building2,
  FileCheck,
  CheckCircle2,
  Download,
  Share2,
  ArrowRight,
  Camera,
  Lock,
  Globe
} from 'lucide-react';
import { InwardShipment, UserProfile, ConfidentialityLevel, ShipmentStatus, ThemeStyle } from '../types';
import { THEMES } from '../utils/theme';

interface InwardRegisterProps {
  inwardList: InwardShipment[];
  currentUser: UserProfile;
  currentTheme?: ThemeStyle;
  onOpenNewInward: () => void;
  onOpenShipmentDetail: (shipment: InwardShipment, type: 'inward') => void;
  onOpenPODModal: (shipment: InwardShipment, type: 'inward') => void;
  onOpenUpdateStatus: (shipment: InwardShipment, type: 'inward') => void;
}

export const InwardRegister: React.FC<InwardRegisterProps> = ({
  inwardList,
  currentUser,
  currentTheme = 'navy',
  onOpenNewInward,
  onOpenShipmentDetail,
  onOpenPODModal,
  onOpenUpdateStatus,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const themeConfig = THEMES[currentTheme] || THEMES.navy;

  // RBAC Permission Check:
  // Partner & Desk can see all inward mail. Staff accounts (audit_staff) see ONLY parcels addressed to them.
  const hasFullAccess = currentUser?.role === 'admin_partner' || currentUser?.role === 'front_desk';

  const userScopedList = inwardList.filter((item) => {
    if (hasFullAccess) return true;
    return (
      (currentUser?.id && item.recipientStaffId === currentUser.id) ||
      (currentUser?.name && item.recipientStaffName.toLowerCase().includes(currentUser.name.toLowerCase()))
    );
  });

  const filteredList = userScopedList.filter((item) => {
    const matchesSearch =
      item.referenceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.trackingNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.senderName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.recipientStaffName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.shelfLocation.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.carrier.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
    const matchesCategory = categoryFilter === 'all' || item.category === categoryFilter;

    return matchesSearch && matchesStatus && matchesCategory;
  });

  const getConfidentialityBadge = (level: ConfidentialityLevel) => {
    switch (level) {
      case 'urgent':
        return 'bg-red-500/10 text-red-500 border-red-500/30';
      case 'confidential':
        return 'bg-amber-500/10 text-amber-500 border-amber-500/30';
      case 'original_certificates':
        return 'bg-purple-500/10 text-purple-500 border-purple-500/30';
      default:
        return `${themeConfig.subCardBg} ${themeConfig.textMuted} border ${themeConfig.cardBorder}`;
    }
  };

  const getStatusBadge = (status: ShipmentStatus) => {
    switch (status) {
      case 'handed_over_to_staff':
        return { label: 'Collected / Handed Over', bg: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' };
      case 'allocated_to_shelf':
        return { label: 'In Shelf Rack', bg: `${themeConfig.badgeBg} ${themeConfig.badgeText}` };
      default:
        return { label: 'At Reception', bg: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20' };
    }
  };

  const handleQuickHandover = (shipment: InwardShipment) => {
    onOpenPODModal(shipment, 'inward');
  };

  return (
    <div className="space-y-4">
      {/* Top Action & Search Bar */}
      <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${themeConfig.cardBg} p-4 rounded-xl border ${themeConfig.cardBorder} backdrop-blur-sm transition-colors duration-300 shadow-sm`}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400">
            <Package className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className={`text-base font-bold ${themeConfig.textPrimary}`}>
                Inward Courier Register
              </h2>
              <span className={`text-xs px-2 py-0.5 rounded-full ${themeConfig.subCardBg} ${themeConfig.textSecondary} font-mono border ${themeConfig.cardBorder}`}>
                {filteredList.length} Dockets
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
              Reception intake, secure shelf slotting, and digital recipient custody handovers.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onOpenNewInward}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all shadow-md shadow-emerald-600/20 active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>Log Inward Courier</span>
          </button>
        </div>
      </div>

      {/* RBAC Notice for Staff */}
      {!hasFullAccess && (
        <div className={`p-3 rounded-xl ${themeConfig.badgeBg} text-xs ${themeConfig.badgeText} flex items-center justify-between gap-2`}>
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 shrink-0" />
            <span>
              <b>Confidentiality Protocol:</b> You are viewing inward parcels addressed specifically to <b>{currentUser.name}</b>. (To view all firm-wide records, switch role to Partner or Front Desk in the top right).
            </span>
          </div>
        </div>
      )}

      {/* Filter Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Search Input */}
        <div className="relative">
          <Search className={`w-4 h-4 ${themeConfig.textMuted} absolute left-3.5 top-3`} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search Inward by Sender, Staff, Shelf, AWB..."
            className={`w-full pl-10 pr-4 py-2.5 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs focus:outline-none transition-colors`}
          />
        </div>

        {/* Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className={`px-3.5 py-2.5 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs focus:outline-none transition-colors`}
        >
          <option value="all">All Inward Statuses</option>
          <option value="received_at_reception">At Reception Desk</option>
          <option value="allocated_to_shelf">Allocated in Holding Shelf</option>
          <option value="handed_over_to_staff">Handed Over to Recipient</option>
        </select>

        {/* Category Filter */}
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className={`px-3.5 py-2.5 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} text-xs focus:outline-none transition-colors`}
        >
          <option value="all">All Document Categories</option>
          <option value="Audit Documents">Audit Documents</option>
          <option value="Tax Filing Files">Tax Filing Files</option>
          <option value="Client Original Deeds">Client Original Deeds</option>
          <option value="ROC Compliance">ROC Compliance</option>
          <option value="General Letter">General Letter / Bank</option>
        </select>
      </div>

      {/* Inward Shipments Table / Card Grid */}
      <div className={`rounded-xl border ${themeConfig.cardBorder} ${themeConfig.cardBg} overflow-hidden shadow-lg transition-colors duration-300`}>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className={`${themeConfig.tableHeaderBg} border-b ${themeConfig.cardBorder} uppercase tracking-wider font-semibold text-[11px]`}>
                <th className="py-3 px-4">Docket & AWB No.</th>
                <th className="py-3 px-4">Sender / Client</th>
                <th className="py-3 px-4">Intended Recipient (Staff)</th>
                <th className="py-3 px-4">Shelf / Bin Location</th>
                <th className="py-3 px-4">Carrier & Intake Time</th>
                <th className="py-3 px-4">Status & Priority</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${themeConfig.cardBorder}`}>
              {filteredList.length === 0 ? (
                <tr>
                  <td colSpan={7} className={`py-8 text-center ${themeConfig.textMuted}`}>
                    No inward parcels found matching your filters.
                  </td>
                </tr>
              ) : (
                filteredList.map((item) => {
                  const statusInfo = getStatusBadge(item.status);
                  return (
                    <tr
                      key={item.id}
                      className={`${themeConfig.tableRowHover} transition-colors group`}
                    >
                      {/* Docket & AWB */}
                      <td className="py-3.5 px-4">
                        <div className={`font-mono font-bold ${themeConfig.textPrimary} flex items-center gap-1.5`}>
                          <span>{item.referenceNumber}</span>
                          {item.parcelPhotoUrl && (
                            <span className="p-0.5 rounded bg-emerald-500/20 text-emerald-500 border border-emerald-500/30" title="Parcel photo attached">
                              <Camera className="w-3 h-3" />
                            </span>
                          )}
                        </div>
                        <span className={`font-mono text-[11px] ${themeConfig.textAccent} block mt-0.5 font-semibold`}>
                          AWB #{item.trackingNumber}
                        </span>
                        <span className={`text-[10px] ${themeConfig.textMuted} block`}>
                          {item.packageType}
                        </span>
                      </td>

                      {/* Sender */}
                      <td className="py-3.5 px-4">
                        <span className={`font-medium ${themeConfig.textPrimary} block truncate max-w-[180px]`}>
                          {item.senderName}
                        </span>
                        {item.senderOrganization && (
                          <span className={`text-[11px] ${themeConfig.textMuted} block truncate max-w-[180px]`}>
                            {item.senderOrganization}
                          </span>
                        )}
                        <span className={`text-[10px] ${themeConfig.textMuted} block mt-0.5`}>
                          {item.category}
                        </span>
                      </td>

                      {/* Recipient Staff */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5">
                          <User className={`w-3.5 h-3.5 ${themeConfig.textAccent}`} />
                          <span className={`font-semibold ${themeConfig.textPrimary}`}>
                            {item.recipientStaffName}
                          </span>
                        </div>
                        <span className={`text-[10px] ${themeConfig.textMuted} block mt-0.5`}>
                          {item.department}
                        </span>
                      </td>

                      {/* Shelf Slot */}
                      <td className="py-3.5 px-4">
                        <div className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md ${themeConfig.subCardBg} border ${themeConfig.cardBorder} font-mono text-emerald-600 dark:text-emerald-400 text-xs font-bold`}>
                          <MapPin className="w-3 h-3" />
                          <span>{item.shelfLocation}</span>
                        </div>
                      </td>

                      {/* Carrier & Time */}
                      <td className="py-3.5 px-4">
                        <span className={`font-medium ${themeConfig.textSecondary} block`}>
                          {item.carrier}
                        </span>
                        <span className={`text-[11px] ${themeConfig.textMuted} flex items-center gap-1 mt-0.5`}>
                          <Clock className={`w-3 h-3 ${themeConfig.textMuted}`} />
                          {item.receivedAt}
                        </span>
                      </td>

                      {/* Status & Priority */}
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-block text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full border mb-1 ${statusInfo.bg}`}
                        >
                          {statusInfo.label}
                        </span>
                        <div>
                          <span
                            className={`text-[9px] uppercase px-1.5 py-0.2 rounded border font-mono ${getConfidentialityBadge(
                              item.confidentiality
                            )}`}
                          >
                            {item.confidentiality.replace('_', ' ')}
                          </span>
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Custody Signature Action */}
                          {item.status !== 'handed_over_to_staff' && (
                            <button
                              onClick={() => handleQuickHandover(item)}
                              className="px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition-colors shadow-sm flex items-center gap-1"
                              title="Sign digital handover receipt"
                            >
                              <ShieldCheck className="w-3.5 h-3.5" />
                              <span className="hidden sm:inline">Handover</span>
                            </button>
                          )}

                          {item.proofOfDelivery && (
                            <button
                              onClick={() => onOpenPODModal(item, 'inward')}
                              className="p-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30 transition-colors"
                              title="View Scanned Proof of Handover"
                            >
                              <CheckCircle2 className="w-4 h-4" />
                            </button>
                          )}

                          {hasFullAccess && (
                            <button
                              onClick={() => onOpenUpdateStatus(item, 'inward')}
                              className={`p-1.5 rounded-lg ${themeConfig.subCardBg} ${themeConfig.cardHover} ${themeConfig.textSecondary} border ${themeConfig.cardBorder} transition-colors`}
                              title="Update Location / Status"
                            >
                              <FileCheck className="w-4 h-4" />
                            </button>
                          )}

                          <button
                            onClick={() => onOpenShipmentDetail(item, 'inward')}
                            className={`p-1.5 rounded-lg ${themeConfig.subCardBg} ${themeConfig.cardHover} ${themeConfig.textPrimary} border ${themeConfig.cardBorder} transition-colors`}
                            title="Audit Trail & Docket Details"
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
    </div>
  );
};
