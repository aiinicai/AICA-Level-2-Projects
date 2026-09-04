import React, { useState } from 'react';
import { Truck, Copy, Check, X, AlertCircle, Phone, ExternalLink } from 'lucide-react';
import { OutwardShipment } from '../types';
import { getCarrierTracking } from '../utils/carrierTracking';

interface ManualTrackingModalProps {
  isOpen: boolean;
  onClose: () => void;
  shipment: OutwardShipment | null;
}

export const ManualTrackingModal: React.FC<ManualTrackingModalProps> = ({
  isOpen,
  onClose,
  shipment,
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !shipment) return null;

  const carrierInfo = getCarrierTracking(shipment.carrier, shipment.trackingNumber);

  const handleCopyAWB = () => {
    navigator.clipboard.writeText(shipment.trackingNumber);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <AlertCircle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Carrier Web Tracking Not Available
              </h3>
              <p className="text-xs text-slate-400">
                Manual dispatch verification required
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

        {/* Body */}
        <div className="py-4 space-y-4 text-xs">
          <div className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20 text-amber-200 leading-relaxed">
            <p>
              Direct live web tracking is not integrated for carrier: <b className="text-white">{shipment.carrier}</b>.
            </p>
            <p className="mt-1 text-slate-400 text-[11px]">
              Please track manually using the consignment / docket number below with your local delivery agent or reception desk.
            </p>
          </div>

          {/* Consignment Details */}
          <div className="space-y-2.5 p-3 rounded-xl bg-slate-950 border border-slate-800">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Docket Number:</span>
              <span className="font-mono font-semibold text-slate-200">{shipment.referenceNumber}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Tracking / Token AWB:</span>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-blue-400">{shipment.trackingNumber}</span>
                <button
                  onClick={handleCopyAWB}
                  className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-[10px] font-semibold flex items-center gap-1 transition-colors"
                  title="Copy AWB number"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" />
                      <span className="text-emerald-400">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Client / Matter:</span>
              <span className="font-medium text-slate-200 truncate max-w-[200px]">{shipment.clientName}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Addressee:</span>
              <span className="font-medium text-slate-200">{shipment.recipientName} ({shipment.recipientCity})</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400">Assigned Staff:</span>
              <span className="font-medium text-slate-200">{shipment.assignedStaffName}</span>
            </div>
          </div>

          {/* Contact / Helpline hint */}
          {carrierInfo.helpline && (
            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-800/60 border border-slate-700 text-[11px] text-slate-300">
              <Phone className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>Helpline / Contact: <b>{carrierInfo.helpline}</b></span>
            </div>
          )}

          {carrierInfo.portalUrl && (
            <a
              href={carrierInfo.portalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-200 border border-slate-700 flex items-center justify-center gap-1.5 transition-colors font-medium text-xs"
            >
              <span>Visit Carrier Homepage</span>
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            </a>
          )}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-all"
          >
            Understood & Close
          </button>
        </div>
      </div>
    </div>
  );
};
