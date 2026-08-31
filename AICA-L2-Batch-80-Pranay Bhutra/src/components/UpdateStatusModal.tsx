import React, { useState } from 'react';
import {
  X,
  FileCheck,
  MapPin,
  Truck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Send,
  Building2
} from 'lucide-react';
import { InwardShipment, OutwardShipment, ShipmentStatus, UserProfile } from '../types';
import { ParcelStorageService } from '../services/storage';

interface UpdateStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  shipment: InwardShipment | OutwardShipment | null;
  type: 'inward' | 'outward';
  currentUser: UserProfile;
  onSuccess: () => void;
}

export const UpdateStatusModal: React.FC<UpdateStatusModalProps> = ({
  isOpen,
  onClose,
  shipment,
  type,
  currentUser,
  onSuccess,
}) => {
  const [status, setStatus] = useState<ShipmentStatus>(shipment?.status || 'received');
  const [location, setLocation] = useState(
    type === 'outward' ? 'Central Sorting Hub / Downtown Van' : 'Ground Floor Reception'
  );
  const [description, setDescription] = useState(
    type === 'outward'
      ? `Package updated to ${(shipment?.status || 'dispatched').replace('_', ' ')} by ${currentUser?.name || 'Staff'}.`
      : `Inward package state updated by ${currentUser?.name || 'Staff'}.`
  );

  React.useEffect(() => {
    if (shipment) {
      setStatus(shipment.status);
      setLocation(type === 'outward' ? 'Central Sorting Hub / Downtown Van' : 'Ground Floor Reception');
      setDescription(
        type === 'outward'
          ? `Package updated to ${shipment.status.replace('_', ' ')} by ${currentUser?.name || 'Staff'}.`
          : `Inward package state updated by ${currentUser?.name || 'Staff'}.`
      );
    }
  }, [shipment, isOpen, type, currentUser]);

  if (!isOpen || !shipment) return null;

  const handleUpdate = () => {
    if (type === 'inward') {
      ParcelStorageService.updateInwardStatus(
        shipment.id,
        status,
        location,
        description,
        currentUser?.name || 'Authorized Staff',
        currentUser?.role || 'audit_staff'
      );
    } else {
      ParcelStorageService.updateOutwardStatus(
        shipment.id,
        status,
        location,
        description,
        currentUser?.name || 'Authorized Staff',
        currentUser?.role || 'audit_staff'
      );
    }

    onSuccess();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Update Tracking Milestone
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-blue-400 border border-slate-700">
                  AWB #{shipment.trackingNumber}
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Log real-time location checkpoint or change parcel delivery state.
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

        {/* Body Form */}
        <div className="py-4 space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              New Shipment Status:
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as ShipmentStatus)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
            >
              {type === 'outward' ? (
                <>
                  <option value="draft">Draft / Requested</option>
                  <option value="dispatched">Dispatched (Picked up by Carrier)</option>
                  <option value="in_transit">In Transit (Hub Sorting / Linehaul)</option>
                  <option value="out_for_delivery">Out for Delivery</option>
                  <option value="delivered">Delivered</option>
                  <option value="rto">Return to Origin (RTO / Failed)</option>
                </>
              ) : (
                <>
                  <option value="received_at_reception">Received at Reception</option>
                  <option value="allocated_to_shelf">Allocated to Shelf Rack</option>
                  <option value="handed_over_to_staff">Handed Over to Recipient Staff</option>
                </>
              )}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Checkpoint Location / Hub:
            </label>
            <div className="relative">
              <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Courier Central Sorting Hub, Santacruz East"
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Milestone Activity Description:
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Out with delivery executive for 2:00 PM delivery window."
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
            />
          </div>

          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 flex items-start gap-2">
            <Send className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block">Automated Stakeholder Notification:</span>
              <span>
                Saving this status milestone will automatically send an updated notification to the assigned staff member and client contact.
              </span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
          >
            Cancel
          </button>

          <button
            onClick={handleUpdate}
            className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-all shadow-lg shadow-blue-600/30 flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Publish Milestone Update</span>
          </button>
        </div>
      </div>
    </div>
  );
};
