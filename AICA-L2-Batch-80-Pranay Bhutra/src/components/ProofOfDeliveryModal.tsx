import React, { useState, useRef, useEffect } from 'react';
import {
  X,
  ShieldCheck,
  Camera,
  Upload,
  PenTool,
  RotateCcw,
  CheckCircle2,
  Calendar,
  User,
  Building2,
  FileText,
  Check
} from 'lucide-react';
import { InwardShipment, OutwardShipment, ProofOfDelivery, UserProfile } from '../types';
import { ParcelStorageService } from '../services/storage';

interface ProofOfDeliveryModalProps {
  isOpen: boolean;
  onClose: () => void;
  shipment: InwardShipment | OutwardShipment | null;
  type: 'inward' | 'outward';
  currentUser: UserProfile;
  onSuccess: () => void;
}

export const ProofOfDeliveryModal: React.FC<ProofOfDeliveryModalProps> = ({
  isOpen,
  onClose,
  shipment,
  type,
  currentUser,
  onSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<'signature' | 'photo'>(
    shipment?.proofOfDelivery?.imageUrl ? 'photo' : 'signature'
  );
  const [signerName, setSignerName] = useState(
    shipment?.proofOfDelivery?.signerName ||
      (type === 'inward' ? (shipment as InwardShipment)?.recipientStaffName || '' : '')
  );
  const [relationship, setRelationship] = useState(
    shipment?.proofOfDelivery?.relationshipToConsignee ||
      (type === 'inward' ? 'Self / Recipient Staff' : 'Authorized Receiver / Inward Counter')
  );
  const [notes, setNotes] = useState(shipment?.proofOfDelivery?.deliveryNotes || '');
  const [uploadedImage, setUploadedImage] = useState<string | null>(
    shipment?.proofOfDelivery?.imageUrl || null
  );
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasSignature, setHasSignature] = useState(!!shipment?.proofOfDelivery?.signatureUrl);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Sync state when shipment or isOpen changes
  useEffect(() => {
    if (shipment && isOpen) {
      setActiveTab(shipment.proofOfDelivery?.imageUrl ? 'photo' : 'signature');
      setSignerName(
        shipment.proofOfDelivery?.signerName ||
          (type === 'inward' ? (shipment as InwardShipment)?.recipientStaffName || '' : '')
      );
      setRelationship(
        shipment.proofOfDelivery?.relationshipToConsignee ||
          (type === 'inward' ? 'Self / Recipient Staff' : 'Authorized Receiver / Inward Counter')
      );
      setNotes(shipment.proofOfDelivery?.deliveryNotes || '');
      setUploadedImage(shipment.proofOfDelivery?.imageUrl || null);
      setHasSignature(!!shipment.proofOfDelivery?.signatureUrl);
    }
  }, [shipment, isOpen, type]);

  // Initialize Canvas
  useEffect(() => {
    if (isOpen && shipment && activeTab === 'signature' && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2.5;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        if (shipment.proofOfDelivery?.signatureUrl) {
          const img = new Image();
          img.onload = () => ctx.drawImage(img, 0, 0);
          img.src = shipment.proofOfDelivery.signatureUrl;
        }
      }
    }
  }, [activeTab, isOpen, shipment]);

  if (!isOpen || !shipment) return null;

  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;

    ctx.beginPath();
    ctx.moveTo(clientX - rect.left, clientY - rect.top);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;

    ctx.lineTo(clientX - rect.left, clientY - rect.top);
    ctx.stroke();
    setHasSignature(true);
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearSignature = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasSignature(false);
  };

  const handleSimulateChallanPhoto = () => {
    // Generate simulated high-res signed delivery challan slip with stamp
    const svgChallan = `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="500" height="320" viewBox="0 0 500 320">
      <rect width="500" height="320" fill="%23f8fafc" rx="8"/>
      <rect x="15" y="15" width="470" height="290" fill="none" stroke="%23cbd5e1" stroke-width="2"/>
      <text x="30" y="45" font-family="sans-serif" font-size="16" font-weight="bold" fill="%230f172a">CARRIER ACKNOWLEDGMENT RECEIPT</text>
      <text x="30" y="70" font-family="monospace" font-size="12" fill="%23475569">AWB: ${shipment.trackingNumber} | Ref: ${shipment.referenceNumber}</text>
      <line x1="30" y1="85" x2="470" y2="85" stroke="%23e2e8f0" stroke-width="1.5"/>
      <text x="30" y="115" font-family="sans-serif" font-size="12" fill="%23334155">Delivered To: ${signerName || 'Client Inward Desk'}</text>
      <text x="30" y="140" font-family="sans-serif" font-size="12" fill="%23334155">Carrier Agent: ${shipment.carrier} Delivery Exec</text>
      <text x="30" y="165" font-family="sans-serif" font-size="12" fill="%23334155">Timestamp: ${new Date().toLocaleString()}</text>
      <circle cx="380" cy="200" r="45" fill="none" stroke="%232563eb" stroke-width="3" stroke-dasharray="4 2"/>
      <text x="380" y="195" font-family="sans-serif" font-size="11" font-weight="bold" text-anchor="middle" fill="%231e40af">RECEIVED %26 VERIFIED</text>
      <text x="380" y="212" font-family="monospace" font-size="9" text-anchor="middle" fill="%231e40af">CA FIRM AUDIT</text>
      <path d="M 330 250 Q 360 220 400 245 T 440 230" fill="none" stroke="%230f172a" stroke-width="3" stroke-linecap="round"/>
    </svg>`;

    setUploadedImage(svgChallan);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      setUploadedImage(event.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleSavePOD = () => {
    let sigUrl = shipment.proofOfDelivery?.signatureUrl;
    if (canvasRef.current && hasSignature) {
      sigUrl = canvasRef.current.toDataURL();
    }

    const podData: ProofOfDelivery = {
      signerName: signerName || 'Authorized Receiver',
      relationshipToConsignee: relationship,
      deliveredAt: new Date().toLocaleString(),
      verifiedBy: currentUser?.name || 'Staff User',
      deliveryNotes: notes,
      signatureUrl: sigUrl,
      imageUrl: uploadedImage || undefined
    };

    if (type === 'inward') {
      ParcelStorageService.updateInwardStatus(
        shipment.id,
        'handed_over_to_staff',
        'Staff Custody Desk',
        `Physical handover completed to ${signerName} (${relationship}). Signed digital POD verified.`,
        currentUser?.name || 'Authorized Staff',
        currentUser?.role || 'audit_staff',
        podData
      );
    } else {
      ParcelStorageService.updateOutwardStatus(
        shipment.id,
        'delivered',
        'Consignee Destination',
        `Consignment delivered to ${signerName} (${relationship}). Scanned proof of delivery verified.`,
        currentUser?.name || 'Authorized Staff',
        currentUser?.role || 'audit_staff',
        podData
      );
    }

    onSuccess();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Proof of Delivery (POD) & Handover Sign
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-blue-400 border border-slate-700">
                  AWB #{shipment.trackingNumber}
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                {type === 'inward'
                  ? 'Digital staff acknowledgment & custody signature.'
                  : 'Capture signed carrier challan or receiver acknowledgment stamp.'}
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

        {/* Tab Selector: Signature Pad vs Scanned Photo */}
        <div className="flex items-center gap-2 mt-4 p-1 rounded-xl bg-slate-950 border border-slate-800">
          <button
            onClick={() => setActiveTab('signature')}
            className={`flex-1 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'signature'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <PenTool className="w-3.5 h-3.5" />
            <span>Digital Touch Signature</span>
          </button>
          <button
            onClick={() => setActiveTab('photo')}
            className={`flex-1 py-1.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
              activeTab === 'photo'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Scanned Slip / Challan Photo</span>
          </button>
        </div>

        {/* Body */}
        <div className="py-4 space-y-4 max-h-[60vh] overflow-y-auto pr-1">
          {/* Active Tab Content */}
          {activeTab === 'signature' ? (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-slate-300">
                  Receiver Touch / Stylus Signature:
                </label>
                <button
                  type="button"
                  onClick={clearSignature}
                  className="text-[11px] text-slate-400 hover:text-red-400 flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Clear Pad</span>
                </button>
              </div>

              <div className="rounded-xl border border-slate-700 bg-slate-950 p-1">
                <canvas
                  ref={canvasRef}
                  width={460}
                  height={150}
                  onMouseDown={startDrawing}
                  onMouseMove={draw}
                  onMouseUp={stopDrawing}
                  onMouseLeave={stopDrawing}
                  onTouchStart={startDrawing}
                  onTouchMove={draw}
                  onTouchEnd={stopDrawing}
                  className="w-full h-36 bg-slate-950 rounded-lg cursor-crosshair touch-none"
                />
              </div>
              <p className="text-[10px] text-slate-500 mt-1">
                Sign with finger on touchscreen mobile/tablet or drag with mouse pointer.
              </p>
            </div>
          ) : (
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">
                Physical Slip / POD Challan Image:
              </label>

              {uploadedImage ? (
                <div className="relative rounded-xl border border-slate-700 bg-slate-950 p-2 overflow-hidden">
                  <img
                    src={uploadedImage}
                    alt="Proof of Delivery Challan"
                    className="w-full h-40 object-contain rounded"
                  />
                  <button
                    onClick={() => setUploadedImage(null)}
                    className="absolute top-3 right-3 p-1 rounded-full bg-slate-900/90 text-slate-300 hover:text-white border border-slate-700"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="rounded-xl border-2 border-dashed border-slate-700 bg-slate-950/50 p-4 text-center">
                  <Camera className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                  <p className="text-xs text-slate-300 font-medium">Capture or Upload Signed POD</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Attach photo of physical courier stamp, ROC inward acknowledgment, or client delivery receipt.
                  </p>

                  <div className="mt-3 flex items-center justify-center gap-2">
                    <label className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold cursor-pointer transition-all flex items-center gap-1">
                      <Upload className="w-3.5 h-3.5" />
                      <span>Upload Photo</span>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                    </label>

                    <button
                      type="button"
                      onClick={handleSimulateChallanPhoto}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
                    >
                      Use Sample Challan Slip
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Form Fields: Signer Info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Receiver / Signer Full Name:
              </label>
              <input
                type="text"
                value={signerName}
                onChange={(e) => setSignerName(e.target.value)}
                placeholder="e.g. Sneha Kulkarni or Client Inward Clerk"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Role / Relationship:
              </label>
              <input
                type="text"
                value={relationship}
                onChange={(e) => setRelationship(e.target.value)}
                placeholder="e.g. Recipient Staff / Official Receiver"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">
              Delivery / Handover Notes (Optional):
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Delivered with original seals intact, inward entry logged."
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
            />
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
            onClick={handleSavePOD}
            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all shadow-lg shadow-emerald-600/30 flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Verify & Save Proof of Delivery</span>
          </button>
        </div>
      </div>
    </div>
  );
};
