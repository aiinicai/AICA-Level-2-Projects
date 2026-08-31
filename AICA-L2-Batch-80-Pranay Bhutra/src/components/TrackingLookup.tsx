import React, { useState, useEffect } from 'react';
import {
  Search,
  Truck,
  Package,
  CheckCircle2,
  Clock,
  MapPin,
  User,
  ShieldCheck,
  Building2,
  ExternalLink,
  Copy,
  Check,
  AlertCircle,
  FileCheck,
  CornerDownRight
} from 'lucide-react';
import { InwardShipment, OutwardShipment, ShipmentStatus, UserProfile, ThemeStyle } from '../types';
import { ParcelStorageService } from '../services/storage';
import { THEMES } from '../utils/theme';

interface TrackingLookupProps {
  currentUser: UserProfile;
  currentTheme?: ThemeStyle;
  onOpenShipmentDetail: (shipment: InwardShipment | OutwardShipment, type: 'inward' | 'outward') => void;
  onOpenUpdateStatus: (shipment: InwardShipment | OutwardShipment, type: 'inward' | 'outward') => void;
  onOpenPODModal: (shipment: InwardShipment | OutwardShipment, type: 'inward' | 'outward') => void;
}

export const TrackingLookup: React.FC<TrackingLookupProps> = ({
  currentUser,
  currentTheme = 'navy',
  onOpenShipmentDetail,
  onOpenUpdateStatus,
  onOpenPODModal,
}) => {
  const [query, setQuery] = useState('');
  const [activeResult, setActiveResult] = useState<{
    shipment: InwardShipment | OutwardShipment;
    type: 'inward' | 'outward';
  } | null>(null);
  const [copied, setCopied] = useState(false);

  const themeConfig = THEMES[currentTheme] || THEMES.navy;

  const outwardList = ParcelStorageService.getOutwardShipments(currentUser?.organizationId);
  const inwardList = ParcelStorageService.getInwardShipments(currentUser?.organizationId);
  const activeAWBs = [...outwardList, ...inwardList].map((s) => s.trackingNumber).slice(0, 4);

  // Sync active result whenever active organization or shipments change
  useEffect(() => {
    const syncShipments = () => {
      const outward = ParcelStorageService.getOutwardShipments(currentUser?.organizationId);
      const inward = ParcelStorageService.getInwardShipments(currentUser?.organizationId);
      if (outward.length > 0) {
        setActiveResult({ shipment: outward[0], type: 'outward' });
      } else if (inward.length > 0) {
        setActiveResult({ shipment: inward[0], type: 'inward' });
      } else {
        setActiveResult(null);
      }
    };

    syncShipments();

    const handleInwardChange = () => syncShipments();
    const handleOutwardChange = () => syncShipments();

    window.addEventListener('inward_updated', handleInwardChange);
    window.addEventListener('outward_updated', handleOutwardChange);

    return () => {
      window.removeEventListener('inward_updated', handleInwardChange);
      window.removeEventListener('outward_updated', handleOutwardChange);
    };
  }, [currentUser?.organizationId, currentUser?.id]);

  const handleSearch = (searchTerm?: string) => {
    const term = searchTerm !== undefined ? searchTerm : query;
    if (!term.trim()) return;

    const { inward, outward } = ParcelStorageService.searchShipments(term, currentUser?.organizationId);
    if (outward.length > 0) {
      setActiveResult({ shipment: outward[0], type: 'outward' });
    } else if (inward.length > 0) {
      setActiveResult({ shipment: inward[0], type: 'inward' });
    } else {
      setActiveResult(null);
    }
  };

  const copyTrackingLink = (ref: string) => {
    const url = `${window.location.origin}/?track=${ref}`;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStatusBadge = (status: ShipmentStatus) => {
    switch (status) {
      case 'delivered':
      case 'handed_over_to_staff':
        return {
          label: status === 'delivered' ? 'Delivered with POD' : 'Handed Over to Staff',
          bg: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/25',
          icon: CheckCircle2
        };
      case 'in_transit':
        return {
          label: 'In Transit',
          bg: `${themeConfig.badgeBg} ${themeConfig.badgeText}`,
          icon: Truck
        };
      case 'out_for_delivery':
        return {
          label: 'Out for Delivery',
          bg: 'bg-indigo-500/10 text-indigo-500 border-indigo-500/25',
          icon: Truck
        };
      case 'dispatched':
      case 'allocated_to_shelf':
        return {
          label: status === 'dispatched' ? 'Dispatched' : 'Allocated to Shelf',
          bg: 'bg-cyan-500/10 text-cyan-500 border-cyan-500/25',
          icon: Package
        };
      default:
        return {
          label: 'Received at Reception',
          bg: 'bg-amber-500/10 text-amber-500 border-amber-500/25',
          icon: Clock
        };
    }
  };

  const getStepStatus = (stepIndex: number, currentStatus: ShipmentStatus, type: 'inward' | 'outward') => {
    const outwardOrder: ShipmentStatus[] = ['draft', 'dispatched', 'in_transit', 'out_for_delivery', 'delivered'];
    const inwardOrder: ShipmentStatus[] = ['received_at_reception', 'allocated_to_shelf', 'handed_over_to_staff'];
    const order = type === 'outward' ? outwardOrder : inwardOrder;

    const currentIndex = order.indexOf(currentStatus);
    if (currentIndex >= stepIndex) return 'completed';
    if (currentIndex === stepIndex - 1) return 'active';
    return 'pending';
  };

  return (
    <div className={`rounded-2xl ${themeConfig.cardBg} border ${themeConfig.cardBorder} p-5 lg:p-6 shadow-xl relative overflow-hidden backdrop-blur-md transition-colors duration-300`}>
      {/* Background Accent Glow */}
      <div
        className="absolute -top-24 -right-24 w-72 h-72 rounded-full blur-3xl pointer-events-none opacity-20"
        style={{ backgroundColor: themeConfig.accentColor }}
      />

      {/* Header & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className={`p-1.5 rounded-lg ${themeConfig.badgeBg} border`}>
              <Search className={`w-4 h-4 ${themeConfig.textAccent}`} />
            </span>
            <h2 className={`text-base font-bold ${themeConfig.textPrimary} tracking-tight`}>
              Real-Time AWB Reference & Docket Tracker
            </h2>
          </div>
          <p className={`text-xs ${themeConfig.textMuted} mt-1`}>
            Instant tracking lookup for assigned staff, client dispatch codes, and inward shelf slots.
          </p>
        </div>

        {/* Quick Samples from Active Organization */}
        {activeAWBs.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className={`text-[11px] ${themeConfig.textMuted} font-medium mr-1`}>Active Firm AWBs:</span>
            {activeAWBs.map((sample) => (
              <button
                key={sample}
                onClick={() => {
                  setQuery(sample);
                  handleSearch(sample);
                }}
                className={`text-[11px] font-mono px-2 py-1 rounded-md ${themeConfig.subCardBg} ${themeConfig.textSecondary} border ${themeConfig.cardBorder} ${themeConfig.cardHover} transition-colors`}
              >
                #{sample}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Prominent Input Search Bar */}
      <div className="relative flex items-center mb-5">
        <div className="absolute left-4 pointer-events-none">
          <Search className={`w-5 h-5 ${themeConfig.textAccent}`} />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Enter Carrier AWB Number (e.g. 9028172641, 7839281920) or Client / Job Code..."
          className={`w-full pl-12 pr-32 py-3.5 rounded-xl ${themeConfig.inputBg} border ${themeConfig.inputBorder} focus:ring-2 text-sm font-mono transition-all shadow-inner`}
        />
        <button
          onClick={() => handleSearch()}
          className={`absolute right-2 px-4 py-2 rounded-lg ${themeConfig.primaryBtn} text-xs font-semibold tracking-wide transition-all shadow-md flex items-center gap-1.5 active:scale-95`}
        >
          <span>Trace Docket</span>
          <CornerDownRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Active Tracing Result Card */}
      {activeResult ? (
        <div className={`rounded-xl ${themeConfig.subCardBg} border ${themeConfig.cardBorder} p-5 space-y-5 transition-colors duration-300`}>
          {/* Card Top Banner */}
          <div className={`flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b ${themeConfig.cardBorder}`}>
            <div className="flex items-start gap-3">
              <div
                className={`p-3 rounded-xl border ${
                  activeResult.type === 'outward'
                    ? `${themeConfig.badgeBg} ${themeConfig.badgeText}`
                    : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500'
                }`}
              >
                {activeResult.type === 'outward' ? (
                  <Truck className="w-6 h-6" />
                ) : (
                  <Package className="w-6 h-6" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`font-mono text-base font-bold ${themeConfig.textPrimary}`}>
                    AWB #{activeResult.shipment.trackingNumber}
                  </span>
                  <span
                    className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${
                      getStatusBadge(activeResult.shipment.status).bg
                    }`}
                  >
                    {getStatusBadge(activeResult.shipment.status).label}
                  </span>
                  <span className={`text-[11px] font-mono px-2 py-0.5 rounded ${themeConfig.cardBg} ${themeConfig.textSecondary} border ${themeConfig.cardBorder}`}>
                    Ref: {activeResult.shipment.referenceNumber}
                  </span>
                </div>
                <div className={`flex items-center gap-3 mt-1.5 text-xs ${themeConfig.textMuted} flex-wrap`}>
                  <span className={`flex items-center gap-1 font-medium ${themeConfig.textSecondary}`}>
                    <Building2 className={`w-3.5 h-3.5 ${themeConfig.textMuted}`} />
                    Carrier: {activeResult.shipment.carrier}
                  </span>
                  <span>•</span>
                  <span>
                    {activeResult.type === 'outward'
                      ? `To: ${(activeResult.shipment as OutwardShipment).recipientName} (${(activeResult.shipment as OutwardShipment).recipientOrganization})`
                      : `From: ${(activeResult.shipment as InwardShipment).senderName}`}
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Actions for Authorized Personnel */}
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={() => copyTrackingLink(activeResult.shipment.trackingNumber)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${themeConfig.secondaryBtn} text-xs font-medium transition-colors`}
                title="Copy shareable tracking URL"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied Link' : 'Copy Link'}</span>
              </button>

              {/* Status Update Button for Admin / Front Desk */}
              {(currentUser.role === 'admin_partner' || currentUser.role === 'front_desk') && (
                <button
                  onClick={() => onOpenUpdateStatus(activeResult.shipment, activeResult.type)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${themeConfig.badgeBg} ${themeConfig.badgeText} text-xs font-medium border transition-colors hover:brightness-110`}
                >
                  <FileCheck className="w-3.5 h-3.5" />
                  <span>Update Status / Milestones</span>
                </button>
              )}

              {/* Proof of Delivery / Signature Action */}
              <button
                onClick={() => onOpenPODModal(activeResult.shipment, activeResult.type)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 text-xs font-medium border border-emerald-500/30 transition-colors"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>
                  {activeResult.shipment.proofOfDelivery ? 'View Verified POD' : 'Scan & Sign POD'}
                </span>
              </button>

              <button
                onClick={() => onOpenShipmentDetail(activeResult.shipment, activeResult.type)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg ${themeConfig.secondaryBtn} text-xs font-medium transition-colors`}
              >
                <span>Full Audit Log</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* CA Specific Metadata Grid (Assignee, Cost Center, Shelf) */}
          <div className={`grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-lg ${themeConfig.cardBg} border ${themeConfig.cardBorder} text-xs`}>
            <div>
              <span className={`${themeConfig.textMuted} block text-[11px]`}>Assigned Personnel:</span>
              <span className={`font-semibold ${themeConfig.textPrimary} flex items-center gap-1 mt-0.5`}>
                <User className={`w-3.5 h-3.5 ${themeConfig.textAccent}`} />
                {activeResult.type === 'outward'
                  ? (activeResult.shipment as OutwardShipment).assignedStaffName
                  : (activeResult.shipment as InwardShipment).recipientStaffName}
              </span>
            </div>

            <div>
              <span className={`${themeConfig.textMuted} block text-[11px]`}>
                {activeResult.type === 'outward' ? 'Client Job / Cost Code:' : 'Holding Location:'}
              </span>
              <span className="font-semibold text-amber-500 font-mono flex items-center gap-1 mt-0.5">
                {activeResult.type === 'outward' ? (
                  <>
                    <Building2 className="w-3.5 h-3.5" />
                    {(activeResult.shipment as OutwardShipment).clientJobCode}
                  </>
                ) : (
                  <>
                    <MapPin className="w-3.5 h-3.5 text-emerald-500" />
                    {(activeResult.shipment as InwardShipment).shelfLocation}
                  </>
                )}
              </span>
            </div>

            <div>
              <span className={`${themeConfig.textMuted} block text-[11px]`}>Department / Practice:</span>
              <span className={`font-medium ${themeConfig.textSecondary} mt-0.5 block truncate`}>
                {activeResult.shipment.department}
              </span>
            </div>

            <div>
              <span className={`${themeConfig.textMuted} block text-[11px]`}>
                {activeResult.type === 'outward' ? 'Courier Cost & Weight:' : 'Confidentiality:'}
              </span>
              <span className={`font-medium ${themeConfig.textSecondary} mt-0.5 block font-mono`}>
                {activeResult.type === 'outward'
                  ? `₹${(activeResult.shipment as OutwardShipment).courierCost} (${(activeResult.shipment as OutwardShipment).weightKg} kg)`
                  : (activeResult.shipment as InwardShipment).confidentiality.toUpperCase()}
              </span>
            </div>
          </div>

          {/* Stepper Progress Bar */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className={`text-xs font-semibold ${themeConfig.textMuted} uppercase tracking-wider`}>
                Chain of Custody Progress
              </span>
              <span className={`text-xs ${themeConfig.textAccent} font-mono`}>
                Latest: {activeResult.shipment.events[activeResult.shipment.events.length - 1]?.location}
              </span>
            </div>

            {/* Stepper Dots */}
            {activeResult.type === 'outward' ? (
              <div className="grid grid-cols-5 gap-2 text-center pt-2">
                {[
                  { label: 'Draft / Request', desc: 'Staff Initiated' },
                  { label: 'Dispatched', desc: 'Handed to Courier' },
                  { label: 'In Transit', desc: 'Carrier Sorting' },
                  { label: 'Out for Delivery', desc: 'Courier On Route' },
                  { label: 'Delivered (POD)', desc: 'Signed & Archived' }
                ].map((step, idx) => {
                  const state = getStepStatus(idx, activeResult.shipment.status, 'outward');
                  return (
                    <div key={idx} className="flex flex-col items-center">
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                          state === 'completed'
                            ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                            : state === 'active'
                            ? `${themeConfig.primaryBtn} ring-4 ${themeConfig.ringColor}/20 animate-pulse`
                            : `${themeConfig.cardBg} ${themeConfig.textMuted} border ${themeConfig.cardBorder}`
                        }`}
                      >
                        {state === 'completed' ? <Check className="w-3.5 h-3.5 stroke-[3]" /> : idx + 1}
                      </div>
                      <span className={`text-[11px] font-medium ${themeConfig.textSecondary} mt-1.5 leading-tight`}>
                        {step.label}
                      </span>
                      <span className={`text-[10px] ${themeConfig.textMuted} hidden sm:block`}>
                        {step.desc}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2 text-center pt-2">
                {[
                  { label: 'Received at Reception', desc: 'Courier Logged' },
                  { label: 'Allocated to Shelf Rack', desc: 'Secure Holding' },
                  { label: 'Handed Over to Staff', desc: 'Custody Signed' }
                ].map((step, idx) => {
                  const state = getStepStatus(idx, activeResult.shipment.status, 'inward');
                  return (
                    <div key={idx} className="flex flex-col items-center">
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                          state === 'completed'
                            ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
                            : state === 'active'
                            ? `${themeConfig.primaryBtn} ring-4 ${themeConfig.ringColor}/20`
                            : `${themeConfig.cardBg} ${themeConfig.textMuted} border ${themeConfig.cardBorder}`
                        }`}
                      >
                        {state === 'completed' ? <Check className="w-3.5 h-3.5 stroke-[3]" /> : idx + 1}
                      </div>
                      <span className={`text-[11px] font-medium ${themeConfig.textSecondary} mt-1.5 leading-tight`}>
                        {step.label}
                      </span>
                      <span className={`text-[10px] ${themeConfig.textMuted} hidden sm:block`}>
                        {step.desc}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className={`text-center py-8 rounded-xl ${themeConfig.subCardBg} border border-dashed ${themeConfig.cardBorder}`}>
          <AlertCircle className={`w-8 h-8 ${themeConfig.textMuted} mx-auto mb-2`} />
          <p className={`text-sm font-medium ${themeConfig.textPrimary}`}>No matching shipment found</p>
          <p className={`text-xs ${themeConfig.textMuted} mt-1`}>
            Try searching with sample AWB <span className={`font-mono ${themeConfig.textAccent}`}>9028172641</span> or <span className={`font-mono ${themeConfig.textAccent}`}>7839281920</span>.
          </p>
        </div>
      )}
    </div>
  );
};
