import React, { useState, useRef, useEffect } from 'react';
import {
  X,
  Package,
  MapPin,
  User,
  ShieldCheck,
  Building2,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Send,
  Camera,
  RotateCcw,
  Trash2,
  Sparkles,
  UploadCloud,
  Clock,
  Eye,
  RefreshCw,
  Loader2
} from 'lucide-react';
import { InwardShipment, UserProfile, ConfidentialityLevel } from '../types';
import { MOCK_CARRIERS } from '../data/mockData';
import { ParcelStorageService } from '../services/storage';

interface NewInwardModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserProfile;
  onSuccess: () => void;
}

export const NewInwardModal: React.FC<NewInwardModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onSuccess,
}) => {
  const orgUsers = ParcelStorageService.getOrganizationUsers(currentUser?.organizationId);
  const staffList = orgUsers.length > 0 ? orgUsers : (currentUser ? [currentUser] : []);

  const [trackingNumber, setTrackingNumber] = useState(
    `BD-${Math.floor(1000000000 + Math.random() * 9000000000)}`
  );
  const [carrier, setCarrier] = useState(MOCK_CARRIERS[0]);
  const [customCarrier, setCustomCarrier] = useState('');
  const [senderName, setSenderName] = useState('');
  const [senderOrg, setSenderOrg] = useState('');
  const [recipientStaffId, setRecipientStaffId] = useState(staffList[0]?.id || currentUser?.id || 'USR-01');
  const [category, setCategory] = useState<string>('Audit Documents');
  const [customCategory, setCustomCategory] = useState('');
  const [confidentiality, setConfidentiality] = useState<ConfidentialityLevel>('confidential');
  const [shelfLocation, setShelfLocation] = useState('Rack A-02');
  const [packageType, setPackageType] = useState<InwardShipment['packageType']>('Legal Docket');
  const [notes, setNotes] = useState('');

  // Camera & Image Capture State
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isCameraLoading, setIsCameraLoading] = useState(false);
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');
  const [parcelPhoto, setParcelPhoto] = useState<string | null>(null);
  const [photoTimestamp, setPhotoTimestamp] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const selectedStaff = staffList.find((u) => u.id === recipientStaffId) || staffList[0] || currentUser;

  const stopCameraStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch (e) {
          console.warn('Track stop error:', e);
        }
      });
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsCameraActive(false);
    setIsCameraLoading(false);
  };

  // Stop camera when closing modal or unmounting
  useEffect(() => {
    if (!isOpen) {
      stopCameraStream();
    }
    return () => {
      stopCameraStream();
    };
  }, [isOpen]);

  // Keep video element srcObject updated when stream or active state changes
  useEffect(() => {
    if (isCameraActive && videoRef.current && streamRef.current) {
      const video = videoRef.current;
      video.srcObject = streamRef.current;
      video.muted = true;
      video.playsInline = true;
      video.play().catch((err) => {
        console.warn('Video auto-play interrupted:', err);
      });
    }
  }, [isCameraActive, facingMode]);

  if (!isOpen) return null;

  const startCamera = async (targetFacing: 'environment' | 'user' = facingMode) => {
    setCameraError(null);
    setIsCameraLoading(true);

    // Stop any existing active tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Direct camera access is not supported by your current browser or iframe. Please upload a photo or use sample capture.');
      }

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: targetFacing },
            width: { ideal: 1280 },
            height: { ideal: 720 }
          },
          audio: false
        });
      } catch (idealErr) {
        console.warn('Ideal facing mode failed, retrying with standard video request:', idealErr);
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false
        });
      }

      streamRef.current = stream;
      setIsCameraActive(true);
      setFacingMode(targetFacing);

      // Attempt immediate attachment if video is already in DOM
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.muted = true;
        videoRef.current.playsInline = true;
        videoRef.current.play().catch((e) => console.warn('Immediate play:', e));
      }
    } catch (err: any) {
      console.error('Camera open error:', err);
      let message = 'Could not access device camera. Please check camera permissions or upload an image.';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        message = 'Camera permission was denied. Please allow camera access in your browser or select an image from gallery/disk.';
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        message = 'No physical camera device was detected. You can upload an image or generate a sample parcel photo.';
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        message = 'Camera is currently locked by another app or tab. Please close other camera apps and retry.';
      }
      setCameraError(message);
      setIsCameraActive(false);
    } finally {
      setIsCameraLoading(false);
    }
  };

  const toggleCameraFacing = () => {
    const nextFacing = facingMode === 'environment' ? 'user' : 'environment';
    startCamera(nextFacing);
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Draw camera frame
    ctx.drawImage(video, 0, 0, width, height);

    // Apply Watermark Banner with Date & Time Stamp
    const now = new Date();
    const stampDate = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    const stampTime = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const timeString = `${stampDate} ${stampTime}`;

    // Stamp background banner
    const bannerHeight = Math.max(50, Math.floor(height * 0.13));
    ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
    ctx.fillRect(0, height - bannerHeight, width, bannerHeight);

    // Top border on banner
    ctx.fillStyle = '#10b981';
    ctx.fillRect(0, height - bannerHeight, width, 3);

    // Stamp text
    ctx.fillStyle = '#34d399';
    ctx.font = `bold ${Math.max(12, Math.floor(bannerHeight * 0.32))}px sans-serif`;
    ctx.fillText(`📦 ParcelDesk Inward Intake • ${timeString}`, 16, height - bannerHeight + Math.floor(bannerHeight * 0.42));

    ctx.fillStyle = '#f8fafc';
    ctx.font = `${Math.max(11, Math.floor(bannerHeight * 0.28))}px monospace`;
    const resolvedCarrier = carrier.includes('Others') ? (customCarrier.trim() || 'Custom Carrier') : carrier;
    ctx.fillText(`AWB: ${trackingNumber} | Carrier: ${resolvedCarrier} | Rack: ${shelfLocation}`, 16, height - 12);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
    setParcelPhoto(dataUrl);
    setPhotoTimestamp(timeString);
    stopCameraStream();
  };

  const handleSimulateSamplePhoto = () => {
    // High-resolution realistic sample parcel intake image with barcode & verified stamp
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 540;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Cardboard box background
    ctx.fillStyle = '#b89068';
    ctx.fillRect(0, 0, 800, 540);

    // Box tape
    ctx.fillStyle = '#9e754d';
    ctx.fillRect(0, 240, 800, 50);

    // White shipping label
    ctx.fillStyle = '#ffffff';
    if (ctx.roundRect) {
      ctx.roundRect(140, 60, 520, 360, 10);
      ctx.fill();
    } else {
      ctx.fillRect(140, 60, 520, 360);
    }
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 2;
    ctx.stroke();

    const resolvedCarrier = carrier.includes('Others') ? (customCarrier.trim() || 'EXPRESS') : carrier;
    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 22px sans-serif';
    ctx.fillText(`${resolvedCarrier.toUpperCase()} PRIORITY LOGISTICS`, 170, 105);

    // Barcode simulated
    ctx.fillStyle = '#0f172a';
    for (let x = 170; x < 610; x += 6) {
      const barW = (x % 12 === 0 || x % 18 === 0) ? 4 : 2;
      ctx.fillRect(x, 125, barW, 60);
    }

    ctx.font = 'bold 15px monospace';
    ctx.fillText(`AWB: ${trackingNumber}`, 170, 210);

    ctx.font = '13px sans-serif';
    ctx.fillStyle = '#334155';
    ctx.fillText(`FROM: ${senderName || 'Sender Client'} (${senderOrg || 'Tax & Advisory Group'})`, 170, 245);
    ctx.fillText(`TO: ${selectedStaff?.name || 'Reception Staff'} - ${selectedStaff?.department || 'Audit Dept'}`, 170, 275);
    ctx.fillText(`ITEM TYPE: ${packageType} (${category})`, 170, 305);
    ctx.fillText(`ASSIGNED STORAGE: ${shelfLocation}`, 170, 335);

    // Inward Verified Rubber Stamp
    ctx.save();
    ctx.translate(500, 330);
    ctx.rotate(-0.08);
    ctx.strokeStyle = '#059669';
    ctx.lineWidth = 3;
    ctx.strokeRect(-80, -25, 160, 50);
    ctx.fillStyle = '#059669';
    ctx.font = 'bold 13px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('INWARD VERIFIED', 0, -4);
    ctx.font = '10px monospace';
    ctx.fillText(new Date().toLocaleDateString(), 0, 14);
    ctx.restore();

    // Bottom Watermark Banner
    const bannerHeight = 60;
    ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
    ctx.fillRect(0, 540 - bannerHeight, 800, bannerHeight);
    ctx.fillStyle = '#10b981';
    ctx.fillRect(0, 540 - bannerHeight, 800, 3);

    const now = new Date();
    const stampDate = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
    const stampTime = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const timeString = `${stampDate} ${stampTime}`;

    ctx.fillStyle = '#34d399';
    ctx.font = 'bold 13px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`📦 ParcelDesk Inward Intake • ${timeString}`, 20, 540 - bannerHeight + 25);

    ctx.fillStyle = '#f8fafc';
    ctx.font = '11px monospace';
    ctx.fillText(`AWB: ${trackingNumber} | Carrier: ${resolvedCarrier} | Rack: ${shelfLocation}`, 20, 524);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
    setParcelPhoto(dataUrl);
    setPhotoTimestamp(timeString);
    stopCameraStream();
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.drawImage(img, 0, 0);

        // Watermark
        const now = new Date();
        const stampDate = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
        const stampTime = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const timeString = `${stampDate} ${stampTime}`;

        const bannerHeight = Math.max(50, Math.floor(img.height * 0.12));
        ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
        ctx.fillRect(0, img.height - bannerHeight, img.width, bannerHeight);
        ctx.fillStyle = '#10b981';
        ctx.fillRect(0, img.height - bannerHeight, img.width, 3);

        ctx.fillStyle = '#34d399';
        ctx.font = `bold ${Math.max(14, Math.floor(bannerHeight * 0.32))}px sans-serif`;
        ctx.fillText(`📦 ParcelDesk Inward Intake • ${timeString}`, 16, img.height - bannerHeight + Math.floor(bannerHeight * 0.42));

        ctx.fillStyle = '#f8fafc';
        ctx.font = `${Math.max(12, Math.floor(bannerHeight * 0.28))}px monospace`;
        const resolvedCarrier = carrier.includes('Others') ? (customCarrier.trim() || 'Custom Carrier') : carrier;
        ctx.fillText(`AWB: ${trackingNumber} | Carrier: ${resolvedCarrier} | Rack: ${shelfLocation}`, 16, img.height - 12);

        const stampedData = canvas.toDataURL('image/jpeg', 0.88);
        setParcelPhoto(stampedData);
        setPhotoTimestamp(timeString);
        stopCameraStream();
      };
      img.src = ev.target?.result as string;
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!senderName.trim()) return;

    const resolvedCarrier = carrier.includes('Others')
      ? (customCarrier.trim() || 'Other Carrier')
      : carrier;

    const resolvedCategory = category === 'Other'
      ? (customCategory.trim() || 'Other Document')
      : category;

    ParcelStorageService.addInwardShipment({
      organizationId: currentUser?.organizationId || 'org_singhania_ca',
      trackingNumber,
      carrier: resolvedCarrier,
      senderName,
      senderOrganization: senderOrg || undefined,
      recipientStaffId: selectedStaff?.id || currentUser?.id || 'USR-01',
      recipientStaffName: selectedStaff?.name || currentUser?.name || 'Staff User',
      department: selectedStaff?.department || currentUser?.department || 'Audit',
      category: resolvedCategory,
      confidentiality,
      shelfLocation,
      packageType,
      parcelPhotoUrl: parcelPhoto || undefined,
      receivedAt:
        new Date().toLocaleDateString() +
        ' ' +
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      status: 'allocated_to_shelf',
      notes
    });

    stopCameraStream();
    onSuccess();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Package className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Log Inward Courier / Parcel</h2>
              <p className="text-xs text-slate-400">
                Front-desk reception intake with camera photo proof & rack allocation.
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              stopCameraStream();
              onClose();
            }}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="py-4 space-y-4 overflow-y-auto pr-1 flex-1">
          {/* CAMERA CAPTURE SECTION (Prominent Top Feature) */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Camera className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Parcel Photo & Timestamp Proof
                </span>
              </div>
              {photoTimestamp && (
                <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Stamped: {photoTimestamp}
                </span>
              )}
            </div>

            {/* If Camera is Active: Live Video View */}
            {isCameraActive && (
              <div className="relative rounded-xl overflow-hidden bg-black border border-emerald-500/40 aspect-video flex items-center justify-center">
                <video
                  ref={(node) => {
                    videoRef.current = node;
                    if (node && streamRef.current && node.srcObject !== streamRef.current) {
                      node.srcObject = streamRef.current;
                      node.muted = true;
                      node.playsInline = true;
                      node.play().catch((err) => console.warn('Video element play error:', err));
                    }
                  }}
                  autoPlay
                  playsInline
                  muted
                  onLoadedMetadata={() => {
                    if (videoRef.current) {
                      videoRef.current.play().catch((e) => console.warn('Loaded metadata play:', e));
                    }
                  }}
                  className="w-full h-full object-cover"
                />

                {isCameraLoading && (
                  <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs flex flex-col items-center justify-center gap-2 text-emerald-400 z-10">
                    <Loader2 className="w-7 h-7 animate-spin" />
                    <span className="text-xs font-medium text-slate-200">Connecting Camera Feed...</span>
                  </div>
                )}

                {/* Top Controls: Flip camera & Facing badge */}
                <div className="absolute top-3 inset-x-3 flex items-center justify-between pointer-events-auto z-10">
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-900/80 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                    Live ({facingMode === 'environment' ? 'Rear / Main' : 'Front / User'})
                  </span>

                  <button
                    type="button"
                    onClick={toggleCameraFacing}
                    className="p-1.5 rounded-lg bg-slate-900/80 hover:bg-slate-800 text-slate-200 border border-slate-700 text-[11px] flex items-center gap-1 shadow-md transition-colors"
                    title="Switch between front and back camera"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Flip Lens</span>
                  </button>
                </div>

                {/* Target Reticle */}
                <div className="absolute inset-4 border-2 border-dashed border-emerald-400/40 rounded-lg pointer-events-none flex items-center justify-center">
                  <span className="text-[11px] bg-slate-900/80 text-slate-300 px-2 py-0.5 rounded font-mono border border-slate-700">
                    Align Parcel Label & Barcode Inside
                  </span>
                </div>

                {/* Camera Overlay Controls */}
                <div className="absolute bottom-3 inset-x-0 flex items-center justify-center gap-3 z-10">
                  <button
                    type="button"
                    onClick={capturePhoto}
                    className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/50 flex items-center gap-2 transition-all transform active:scale-95 cursor-pointer"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Click & Stamp Photo</span>
                  </button>

                  <button
                    type="button"
                    onClick={stopCameraStream}
                    className="px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-800 text-slate-300 text-xs font-medium border border-slate-700 transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* If Photo is Already Captured: Preview Card with Stamped Watermark */}
            {!isCameraActive && parcelPhoto && (
              <div className="relative rounded-xl overflow-hidden border border-emerald-500/30 bg-slate-900 group">
                <img
                  src={parcelPhoto}
                  alt="Captured Parcel Intake"
                  className="w-full h-44 object-cover rounded-lg"
                />
                <div className="absolute top-2 right-2 flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => startCamera(facingMode)}
                    className="p-1.5 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-slate-200 text-xs border border-slate-700 shadow-md flex items-center gap-1"
                    title="Retake Photo"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span className="text-[10px]">Retake</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setParcelPhoto(null);
                      setPhotoTimestamp(null);
                    }}
                    className="p-1.5 rounded-lg bg-red-950/90 hover:bg-red-900 text-red-300 text-xs border border-red-800 shadow-md"
                    title="Remove Photo"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="p-2 bg-slate-950/90 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-300">
                  <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Photo stamped with date, time & AWB watermark
                  </span>
                </div>
              </div>
            )}

            {/* If No Camera & No Photo: Shutter / Upload Buttons */}
            {!isCameraActive && !parcelPhoto && (
              <div className="space-y-2">
                <div className="flex flex-col sm:flex-row gap-2">
                  <button
                    type="button"
                    onClick={() => startCamera(facingMode)}
                    className="flex-1 py-3 px-4 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-sm group cursor-pointer"
                  >
                    <Camera className="w-4 h-4 group-hover:scale-110 transition-transform text-emerald-400" />
                    <span>Capture Parcel's Image (Live Camera)</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="py-3 px-4 rounded-xl bg-slate-900 hover:bg-slate-850 text-slate-300 border border-slate-800 text-xs font-medium flex items-center justify-center gap-2 transition-colors cursor-pointer"
                  >
                    <UploadCloud className="w-4 h-4 text-slate-400" />
                    <span>Upload / Gallery</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleSimulateSamplePhoto}
                    className="py-3 px-3 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border border-blue-500/20 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                    title="Generate sample intake label with watermark"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                    <span>Sample Proof</span>
                  </button>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </div>
              </div>
            )}

            {cameraError && (
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
                <div className="flex-1 space-y-1.5">
                  <p className="font-medium text-amber-200">{cameraError}</p>
                  <div className="flex items-center gap-3 pt-1">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-emerald-400 hover:text-emerald-300 font-medium underline flex items-center gap-1"
                    >
                      <UploadCloud className="w-3.5 h-3.5" /> Upload image from file
                    </button>
                    <span className="text-slate-600">•</span>
                    <button
                      type="button"
                      onClick={handleSimulateSamplePhoto}
                      className="text-blue-400 hover:text-blue-300 font-medium underline flex items-center gap-1"
                    >
                      <Sparkles className="w-3.5 h-3.5" /> Generate sample parcel photo
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Carrier & AWB */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Carrier Service:
              </label>
              <select
                value={carrier}
                onChange={(e) => setCarrier(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                {MOCK_CARRIERS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Courier AWB / Tracking Reference:
              </label>
              <input
                type="text"
                value={trackingNumber}
                onChange={(e) => setTrackingNumber(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-100 focus:border-blue-500 focus:outline-none"
              >
              </input>
            </div>
          </div>

          {/* If "Others" is Selected: Custom Carrier Name Input */}
          {carrier.includes('Others') && (
            <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 animate-in fade-in duration-150">
              <label className="text-xs font-semibold text-blue-300 block mb-1">
                Enter Custom Carrier / Delivery Person Name:
              </label>
              <input
                type="text"
                value={customCarrier}
                onChange={(e) => setCustomCarrier(e.target.value)}
                required
                placeholder="e.g. Swiggy Genie, ST Courier, Local Messenger, Direct Hand Delivery"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          )}

          {/* Sender Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Sender Name / Authority Contact:
              </label>
              <input
                type="text"
                value={senderName}
                onChange={(e) => setSenderName(e.target.value)}
                required
                placeholder="e.g. CFO Office - Tata Tech or CIT Appeals"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Sender Organization (Optional):
              </label>
              <input
                type="text"
                value={senderOrg}
                onChange={(e) => setSenderOrg(e.target.value)}
                placeholder="e.g. Income Tax Dept / Client Company"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Intended Staff & Shelf Location */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Intended Recipient (Firm Staff / Partner):
              </label>
              <select
                value={recipientStaffId}
                onChange={(e) => setRecipientStaffId(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                {staffList.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.department})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Holding Shelf / Rack Location:
              </label>
              <input
                type="text"
                value={shelfLocation}
                onChange={(e) => setShelfLocation(e.target.value)}
                placeholder="e.g. Rack A-02, Partner Vault"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-emerald-400 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Category, Confidentiality & Type */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Document Category:
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="Audit Documents">Audit Documents</option>
                <option value="Tax Filing Files">Tax Filing Files</option>
                <option value="Client Original Deeds">Client Original Deeds</option>
                <option value="ROC Compliance">ROC Compliance</option>
                <option value="General Letter">General Letter / Bank</option>
                <option value="Cheque / Bank">Cheque / Bank</option>
                <option value="Other">Other (Type Custom Category)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Confidentiality Tag:
              </label>
              <select
                value={confidentiality}
                onChange={(e) => setConfidentiality(e.target.value as any)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="routine">Routine</option>
                <option value="confidential">Confidential</option>
                <option value="urgent">Urgent</option>
                <option value="original_certificates">Original Certificates</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1">
                Packaging Format:
              </label>
              <select
                value={packageType}
                onChange={(e) => setPackageType(e.target.value as any)}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 focus:border-blue-500 focus:outline-none"
              >
                <option value="Envelope">Envelope</option>
                <option value="Legal Docket">Legal Docket</option>
                <option value="Pouch">Pouch</option>
                <option value="Box">Box</option>
                <option value="Sealed Envelope">Sealed Envelope</option>
              </select>
            </div>
          </div>

          {/* If "Other" category is Selected: Custom Category Name Input */}
          {category === 'Other' && (
            <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 animate-in fade-in duration-150">
              <label className="text-xs font-semibold text-purple-300 block mb-1">
                Enter Custom Category Name:
              </label>
              <input
                type="text"
                value={customCategory}
                onChange={(e) => setCustomCategory(e.target.value)}
                required
                placeholder="e.g. Arbitration Award, Tender Bid Docket, Shareholder Ledger, Bank Guarantee"
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-purple-500 focus:outline-none"
              />
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1">
              Internal Intake Notes:
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Received with seal intact, signed by driver."
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none"
            />
          </div>

          {/* Notification Alert Preview */}
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center gap-2">
            <Send className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              Automated alert will be instantly dispatched to <b>{selectedStaff.name}</b> with shelf location [<b>{shelfLocation}</b>].
            </span>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-800 shrink-0">
            <button
              type="button"
              onClick={() => {
                stopCameraStream();
                onClose();
              }}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-medium border border-slate-700 transition-colors"
            >
              Cancel
            </button>

            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all shadow-lg shadow-emerald-600/30 flex items-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Confirm & Allocate Inward</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

