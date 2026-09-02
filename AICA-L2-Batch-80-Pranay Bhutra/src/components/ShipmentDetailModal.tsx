import React from 'react';
import {
  X,
  Package,
  Truck,
  MapPin,
  Clock,
  User,
  Building2,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  Share2,
  Printer,
  FileText,
  AlertCircle,
  Camera
} from 'lucide-react';
import { InwardShipment, OutwardShipment, UserProfile } from '../types';

interface ShipmentDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  shipment: InwardShipment | OutwardShipment | null;
  type: 'inward' | 'outward';
  currentUser: UserProfile;
  onOpenPODModal: () => void;
  onOpenUpdateStatus: () => void;
}

export const ShipmentDetailModal: React.FC<ShipmentDetailModalProps> = ({
  isOpen,
  onClose,
  shipment,
  type,
  currentUser,
  onOpenPODModal,
  onOpenUpdateStatus,
}) => {
  if (!isOpen || !shipment) return null;

  const isInward = type === 'inward';
  const inwardItem = isInward ? (shipment as InwardShipment) : null;
  const outwardItem = !isInward ? (shipment as OutwardShipment) : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-xl ${
                isInward
                  ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                  : 'bg-blue-500/10 border border-blue-500/20 text-blue-400'
              }`}
            >
              {isInward ? <Package className="w-5 h-5" /> : <Truck className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white font-mono">
                  {shipment.referenceNumber}
                </h2>
                <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-mono border border-blue-500/30">
                  AWB: {shipment.trackingNumber}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {isInward
                  ? `Inward Intake • ${inwardItem?.category}`
                  : `Outward Dispatch • Matter Code: ${outwardItem?.clientJobCode}`}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="py-4 space-y-5 max-h-[70vh] overflow-y-auto pr-1">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs">
            <div>
              <span className="text-slate-400 block text-[11px]">Carrier Service:</span>
              <span className="font-semibold text-slate-200 block mt-0.5">{shipment.carrier}</span>
            </div>

            <div>
              <span className="text-slate-400 block text-[11px]">
                {isInward ? 'Holding Shelf Location:' : 'Client Code / Partner:'}
              </span>
              <span className="font-mono font-semibold text-amber-400 block mt-0.5">
                {isInward ? inwardItem?.shelfLocation : `${outwardItem?.clientJobCode} (${outwardItem?.partnerInCharge})`}
              </span>
            </div>

            <div>
              <span className="text-slate-400 block text-[11px]">Assigned Personnel:</span>
              <span className="font-semibold text-slate-200 block mt-0.5">
                {isInward ? inwardItem?.recipientStaffName : outwardItem?.assignedStaffName}
              </span>
            </div>

            <div>
              <span className="text-slate-400 block text-[11px]">Confidentiality:</span>
              <span className="font-medium text-slate-300 uppercase block mt-0.5">
                {shipment.confidentiality.replace('_', ' ')}
              </span>
            </div>

            <div>
              <span className="text-slate-400 block text-[11px]">Package Format:</span>
              <span className="font-medium text-slate-300 block mt-0.5">{shipment.packageType}</span>
            </div>

            <div>
              <span className="text-slate-400 block text-[11px]">
                {isInward ? 'Received Timestamp:' : 'Courier Cost:'}
              </span>
              <span className="font-medium text-emerald-400 font-mono block mt-0.5">
                {isInward ? inwardItem?.receivedAt : `₹${outwardItem?.courierCost} (${outwardItem?.weightKg} kg)`}
              </span>
            </div>
          </div>

          {/* Parties Involved */}
          <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/80 text-xs space-y-2">
            <h3 className="font-semibold text-slate-300 uppercase text-[11px] tracking-wider">
              Consignor & Consignee Entity Details
            </h3>
            {isInward ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div>
                  <span className="text-slate-400 block text-[11px]">Sender / Consignor:</span>
                  <span className="font-semibold text-slate-200 block">{inwardItem?.senderName}</span>
                  <span className="text-slate-400 block">{inwardItem?.senderOrganization}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Firm Addressee (Recipient):</span>
                  <span className="font-semibold text-slate-200 block">{inwardItem?.recipientStaffName}</span>
                  <span className="text-slate-400 block">{inwardItem?.department}</span>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div>
                  <span className="text-slate-400 block text-[11px]">Client Matter / Sender:</span>
                  <span className="font-semibold text-slate-200 block">{outwardItem?.clientName}</span>
                  <span className="text-slate-400 block font-mono">{outwardItem?.clientJobCode}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Recipient Consignee:</span>
                  <span className="font-semibold text-slate-200 block">{outwardItem?.recipientName}</span>
                  <span className="text-slate-400 block">{outwardItem?.recipientOrganization}, {outwardItem?.recipientCity}</span>
                </div>
              </div>
            )}

            {shipment.notes && (
              <div className="pt-2 border-t border-slate-800/80">
                <span className="text-slate-400 text-[11px] block">Docket Notes:</span>
                <p className="text-slate-300 italic text-[11px] mt-0.5">{shipment.notes}</p>
              </div>
            )}
          </div>

          {/* Captured Parcel Intake Photo (if available) */}
          {isInward && inwardItem?.parcelPhotoUrl && (
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-emerald-500/30 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="font-semibold text-emerald-400 flex items-center gap-1.5">
                  <Camera className="w-4 h-4" />
                  Intake Parcel Photo & Timestamp Proof
                </span>
                <span className="text-[11px] font-mono text-slate-400">
                  {inwardItem.receivedAt}
                </span>
              </div>
              <div className="pt-2.5 flex flex-col sm:flex-row gap-3 items-center">
                <img
                  src={inwardItem.parcelPhotoUrl}
                  alt="Captured Parcel"
                  className="rounded-lg max-h-48 w-full object-cover border border-slate-800"
                />
              </div>
            </div>
          )}

          {/* Scanned Proof of Delivery (if available) */}
          {shipment.proofOfDelivery && (
            <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-emerald-500/20">
                <span className="font-semibold text-emerald-300 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Verified Proof of Delivery & Signature Stamp
                </span>
                <span className="text-[11px] font-mono text-emerald-400">
                  {shipment.proofOfDelivery.deliveredAt}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3">
                <div>
                  <span className="text-slate-400 text-[11px] block">Signed Receiver Name:</span>
                  <span className="font-semibold text-slate-100 block">
                    {shipment.proofOfDelivery.signerName} ({shipment.proofOfDelivery.relationshipToConsignee})
                  </span>
                  <span className="text-[11px] text-slate-400 block mt-1">
                    Verified By: {shipment.proofOfDelivery.verifiedBy}
                  </span>
                </div>

                {shipment.proofOfDelivery.signatureUrl && (
                  <div>
                    <span className="text-slate-400 text-[11px] block mb-1">Digital Handover Signature:</span>
                    <div className="bg-slate-950 p-2 rounded-lg border border-slate-800 inline-block">
                      <img
                        src={shipment.proofOfDelivery.signatureUrl}
                        alt="Signature"
                        className="h-12 w-auto object-contain"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Complete Event Milestone Audit Trail */}
          <div>
            <h3 className="font-semibold text-slate-300 text-xs uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-blue-400" />
              Chain-of-Custody Timeline Log ({shipment.events.length} Milestones)
            </h3>

            <div className="space-y-3 relative pl-4 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
              {shipment.events.map((ev, index) => (
                <div key={ev.id || index} className="relative pl-4">
                  <div className="absolute -left-[18px] top-1 w-3 h-3 rounded-full bg-blue-500 ring-4 ring-slate-900 border border-slate-700" />
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs">
                    <div className="flex items-center justify-between gap-2 flex-wrap mb-1">
                      <span className="font-semibold text-slate-200">
                        {ev.location}
                      </span>
                      <span className="font-mono text-[11px] text-slate-400">
                        {ev.timestamp}
                      </span>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed">
                      {ev.description}
                    </p>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-slate-400">
                      <span>Logged By: {ev.actorName}</span>
                      <span>•</span>
                      <span className="capitalize">{ev.actorRole.replace('_', ' ')}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
          >
            Close
          </button>

          <div className="flex items-center gap-2">
            {!shipment.proofOfDelivery && (
              <button
                onClick={() => {
                  onClose();
                  onOpenPODModal();
                }}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all shadow-md shadow-emerald-600/20 flex items-center gap-1.5"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Upload / Sign POD</span>
              </button>
            )}

            {(currentUser.role === 'admin_partner' || currentUser.role === 'front_desk') && (
              <button
                onClick={() => {
                  onClose();
                  onOpenUpdateStatus();
                }}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-all shadow-md shadow-blue-600/20"
              >
                Update Milestone
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
