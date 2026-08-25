import React, { useState } from 'react';
import {
  X,
  Download,
  Printer,
  FileText,
  CheckCircle2,
  Building2,
  CreditCard,
  Stamp,
  PenTool,
  Sparkles
} from 'lucide-react';
import { Voucher, CompanyProfile } from '../../types';
import { PDFEngine } from '../../services/pdfEngine';

interface VoucherPreviewModalProps {
  voucher: Voucher | null;
  companyProfile: CompanyProfile;
  isOpen: boolean;
  onClose: () => void;
}

export const VoucherPreviewModal: React.FC<VoucherPreviewModalProps> = ({
  voucher,
  companyProfile,
  isOpen,
  onClose,
}) => {
  const [isGenerating, setIsGenerating] = useState(false);

  if (!isOpen || !voucher) return null;

  const typeTitles: Record<string, string> = {
    PO: 'PURCHASE ORDER',
    LPO: 'LOCAL PURCHASE ORDER',
    PROFORMA: 'PROFORMA INVOICE',
    SALES: 'TAX INVOICE',
    DELIVERY: 'DELIVERY NOTE',
    GATE_PASS: 'GATE PASS',
  };

  const isGatePass = voucher.type === 'GATE_PASS';

  const handleDownloadPDF = async () => {
    try {
      setIsGenerating(true);
      const pdfBytes = await PDFEngine.generateVoucherPDF(voucher, companyProfile);
      PDFEngine.downloadFile(
        pdfBytes,
        `${voucher.docNumber}_${voucher.clientName.replace(/\s+/g, '_')}.pdf`
      );
    } catch (e: any) {
      alert(`Error generating PDF: ${e.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 print:p-0">
      <div className="bg-slate-100 rounded-xl shadow-2xl border border-slate-300 max-w-4xl w-full max-h-[95vh] flex flex-col overflow-hidden print:max-w-none print:w-full print:h-auto print:border-none print:shadow-none">
        {/* Top Modal Controls */}
        <div className="px-6 py-3.5 bg-slate-900 text-white flex items-center justify-between shrink-0 print:hidden">
          <div className="flex items-center space-x-2.5">
            <FileText className="w-5 h-5 text-blue-400" />
            <h3 className="font-semibold text-sm">
              Document Preview — {voucher.docNumber} ({typeTitles[voucher.type] || voucher.type})
            </h3>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handlePrint}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold transition"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print</span>
            </button>

            <button
              onClick={handleDownloadPDF}
              disabled={isGenerating}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold transition shadow-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{isGenerating ? 'Generating PDF...' : 'Download Vector PDF'}</span>
            </button>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded transition ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable A4 Document Page */}
        <div className="p-6 overflow-y-auto flex justify-center bg-slate-200/70 print:p-0 print:bg-white">
          <div
            id="printable-a4-document"
            className="w-[794px] min-h-[1123px] bg-white p-10 shadow-lg border border-slate-300 rounded-sm text-slate-800 space-y-6 select-none print:w-full print:shadow-none print:border-none print:p-8"
            style={{ fontFamily: companyProfile.theme.fontFamily || 'Inter, sans-serif' }}
          >
            {/* Top Accent Strip */}
            <div
              className="h-2.5 w-full rounded-xs"
              style={{ backgroundColor: companyProfile.theme.primaryColor || '#0F2C59' }}
            />

            {/* Header: Company Details & Document Title */}
            <div
              className="flex items-start justify-between border-b pb-4 gap-4"
              style={{ borderColor: companyProfile.theme.accentColor || '#D97706' }}
            >
              {/* Left: Logo & Company Address */}
              <div className="flex items-start space-x-4 min-w-0">
                {companyProfile.logoUrl ? (
                  <img
                    src={companyProfile.logoUrl}
                    alt="Company Logo"
                    className="w-16 h-16 object-contain rounded p-1 border border-slate-100"
                  />
                ) : (
                  <div
                    className="w-14 h-14 rounded-lg flex items-center justify-center text-white font-bold text-sm shrink-0"
                    style={{ backgroundColor: companyProfile.theme.primaryColor || '#0F2C59' }}
                  >
                    LOGO
                  </div>
                )}
                <div className="min-w-0">
                  <h1
                    className="text-base font-bold tracking-tight uppercase leading-snug"
                    style={{ color: companyProfile.theme.primaryColor || '#0F2C59' }}
                  >
                    {companyProfile.name}
                  </h1>
                  <p className="text-xs text-slate-600 mt-0.5">{companyProfile.address}</p>
                  <p className="text-xs text-slate-600">
                    Tel: {companyProfile.phone} | Email: {companyProfile.email}
                  </p>
                  <p className="text-xs font-mono font-medium text-slate-700">
                    TIN: {companyProfile.tin} {companyProfile.vrn && `| VRN: ${companyProfile.vrn}`}
                  </p>
                </div>
              </div>

              {/* Right: Badge */}
              <div className="text-right shrink-0">
                <div
                  className="px-4 py-1.5 rounded text-white font-bold text-sm tracking-wider uppercase inline-block shadow-xs"
                  style={{ backgroundColor: companyProfile.theme.primaryColor || '#0F2C59' }}
                >
                  {typeTitles[voucher.type] || voucher.type}
                </div>
                <p className="text-xs font-mono font-bold text-slate-800 mt-2">
                  No: <span className="text-blue-700">{voucher.docNumber}</span>
                </p>
                <p className="text-xs text-slate-600">Date: {voucher.docDate}</p>
              </div>
            </div>

            {/* Recipient & Metadata Grid */}
            {isGatePass ? (
              <div className="grid grid-cols-2 gap-4 text-xs">
                {/* Vehicle & Driver Manifest */}
                <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                  <span
                    className="font-bold text-[10px] uppercase tracking-wider block"
                    style={{ color: companyProfile.theme.secondaryColor || '#1E40AF' }}
                  >
                    VEHICLE & DRIVER MANIFEST:
                  </span>
                  <p className="text-slate-900 font-bold text-sm">
                    Vehicle Reg: <span className="font-mono text-blue-900">{voucher.vehicleRegistration || 'N/A'}</span>
                  </p>
                  <p className="text-slate-700">
                    Driver Name: <strong>{voucher.driverName || 'N/A'}</strong>
                  </p>
                  <p className="text-slate-600 font-mono text-[11px]">
                    Driver ID/License: {voucher.driverLicenseNumber || 'N/A'}
                  </p>
                  {voucher.clientName && (
                    <p className="text-slate-600">Transporter/Customer: {voucher.clientName}</p>
                  )}
                </div>

                {/* Gate Security & Authorization Details */}
                <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                  <span
                    className="font-bold text-[10px] uppercase tracking-wider block"
                    style={{ color: companyProfile.theme.secondaryColor || '#1E40AF' }}
                  >
                    GATE MOVEMENT CONTROL:
                  </span>
                  <p className="text-slate-700">
                    Movement Direction:{' '}
                    <strong
                      className={`uppercase px-2 py-0.5 rounded text-[11px] ${
                        voucher.direction === 'inward'
                          ? 'bg-emerald-100 text-emerald-900 font-bold'
                          : 'bg-amber-100 text-amber-900 font-bold'
                      }`}
                    >
                      {voucher.direction || 'OUTWARD'}
                    </strong>
                  </p>
                  <p className="text-slate-700">
                    Pass Time: <strong className="font-mono">{voucher.gatePassTime || '12:00'}</strong>
                  </p>
                  {voucher.linkedVoucherNumber && (
                    <p className="text-slate-700">
                      Linked Voucher: <strong className="font-mono text-blue-700">{voucher.linkedVoucherNumber}</strong>
                    </p>
                  )}
                  <p className="text-slate-700">
                    Authorized By: <strong>{voucher.authorizedBy || 'Plant Manager'}</strong>
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4 text-xs">
                {/* Left Box */}
                <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                  <span
                    className="font-bold text-[10px] uppercase tracking-wider block"
                    style={{ color: companyProfile.theme.secondaryColor || '#1E40AF' }}
                  >
                    {voucher.type === 'PO' ? 'VENDOR / SUPPLIER:' : 'BILL TO / RECIPIENT:'}
                  </span>
                  <p className="font-bold text-sm text-slate-900">{voucher.clientName}</p>
                  <p className="text-slate-600">{voucher.clientAddress || 'Dar es Salaam, Tanzania'}</p>
                  <p className="text-slate-700 font-mono">
                    TIN: <span className="font-semibold">{voucher.clientTin || 'N/A'}</span> | Mobile: {voucher.clientMobile || 'N/A'}
                  </p>
                </div>

                {/* Right Box */}
                <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                  <span
                    className="font-bold text-[10px] uppercase tracking-wider block"
                    style={{ color: companyProfile.theme.secondaryColor || '#1E40AF' }}
                  >
                    TRANSACTION SPECIFICATIONS:
                  </span>
                  <p className="text-slate-700">
                    Currency: <strong className="font-mono text-slate-900">{voucher.currency}</strong>
                    {voucher.exchangeRate && (
                      <span className="text-slate-500 ml-1 font-mono">(1 USD = {voucher.exchangeRate.toLocaleString()} TZS)</span>
                    )}
                  </p>
                  {voucher.paymentTerms && (
                    <p className="text-slate-700">Payment Terms: <strong>{voucher.paymentTerms}</strong></p>
                  )}
                  {voucher.dueDate && (
                    <p className="text-slate-700">Due Date: <strong>{voucher.dueDate}</strong></p>
                  )}
                  {voucher.requestedDeliveryDate && (
                    <p className="text-slate-700">Delivery Date: <strong>{voucher.requestedDeliveryDate}</strong></p>
                  )}
                </div>
              </div>
            )}

            {/* Line Items Table / Cargo Manifest Table */}
            {isGatePass ? (
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead
                    className="text-white font-bold text-[11px] uppercase tracking-wider"
                    style={{ backgroundColor: companyProfile.theme.primaryColor || '#0F2C59' }}
                  >
                    <tr>
                      <th className="py-2.5 px-3 w-8">#</th>
                      <th className="py-2.5 px-4">Cargo / Goods Description</th>
                      <th className="py-2.5 px-4 text-center w-36">Quantity & Unit</th>
                      <th className="py-2.5 px-4 text-center w-36">Movement</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    <tr className="bg-white">
                      <td className="py-3 px-3 text-slate-400 font-mono text-center">1</td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900 text-sm">
                          {voucher.goodsDescription || voucher.items[0]?.itemName || 'General Cargo'}
                        </div>
                        {voucher.notes && (
                          <div className="text-xs text-slate-500 italic mt-1">
                            Remarks: {voucher.notes}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center font-bold text-sm text-slate-900 font-mono">
                        {voucher.quantityUnit || `${voucher.items[0]?.quantity || 1} Unit`}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="font-bold uppercase text-xs px-2.5 py-1 bg-slate-100 rounded text-slate-800">
                          {voucher.direction || 'Outward'}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead
                    className="text-white font-bold text-[11px] uppercase tracking-wider"
                    style={{ backgroundColor: companyProfile.theme.primaryColor || '#0F2C59' }}
                  >
                    <tr>
                      <th className="py-2.5 px-3 w-8">#</th>
                      <th className="py-2.5 px-4">Item Description</th>
                      <th className="py-2.5 px-3 text-center w-20">Qty</th>
                      <th className="py-2.5 px-3 text-right w-28">Rate ({voucher.currency})</th>
                      <th className="py-2.5 px-3 text-center w-20">VAT %</th>
                      <th className="py-2.5 px-4 text-right w-32">Total ({voucher.currency})</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {voucher.items.map((item, idx) => (
                      <tr key={item.id} className={idx % 2 === 1 ? 'bg-slate-50/70' : 'bg-white'}>
                        <td className="py-2.5 px-3 text-slate-400 font-mono text-center">{idx + 1}</td>
                        <td className="py-2.5 px-4">
                          <div className="font-semibold text-slate-900">{item.itemName}</div>
                          {item.description && (
                            <div className="text-[11px] text-slate-500 italic mt-0.5">{item.description}</div>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono text-slate-800">{item.quantity}</td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-800">
                          {item.rate.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono text-slate-700">{item.vatPercent}%</td>
                        <td className="py-2.5 px-4 text-right font-mono font-bold text-slate-900">
                          {item.lineTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Calculations & Bank Settlement Grid OR Gate Clearance Summary */}
            {isGatePass ? (
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-700 uppercase tracking-wider">
                    SECURITY INSPECTION & CLEARANCE NOTICE
                  </span>
                  <span className="text-[10px] text-teal-800 bg-teal-100 px-2 py-0.5 rounded font-bold">
                    Official Security Gate Document (Non-Financial)
                  </span>
                </div>
                <p className="text-slate-600 leading-relaxed text-[11px]">
                  All cargo entering or departing the facility gates must be physically verified against this authorized Gate Pass.
                  Drivers must present valid national identification and maintain possession of this document throughout transit.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-6 pt-2">
                {/* Left Column: Bank Settlement & Remarks */}
                <div className="space-y-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                    <span
                      className="font-bold text-[10px] uppercase tracking-wider block"
                      style={{ color: companyProfile.theme.secondaryColor || '#1E40AF' }}
                    >
                      BANK SETTLEMENT INSTRUCTIONS:
                    </span>
                    <p className="text-slate-700">Bank: <strong>{companyProfile.bankDetails.bankName || 'CRDB Bank Plc'}</strong></p>
                    <p className="text-slate-700">A/C Name: <strong>{companyProfile.bankDetails.accountName || companyProfile.name}</strong></p>
                    <p className="text-slate-700">A/C No: <strong className="font-mono">{companyProfile.bankDetails.accountNumber}</strong></p>
                    <p className="text-slate-700">SWIFT Code: <strong className="font-mono">{companyProfile.bankDetails.swiftCode || 'CORUTZTZ'}</strong></p>
                  </div>

                  {voucher.notes && (
                    <div className="text-slate-600 text-[11px] italic bg-slate-50/50 p-2.5 rounded border border-slate-200">
                      <strong>Remarks:</strong> {voucher.notes}
                    </div>
                  )}
                </div>

                {/* Right Column: Totals Summary */}
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between py-1 border-b border-slate-200 text-slate-600">
                    <span>Subtotal (Pre-VAT):</span>
                    <span className="font-mono font-semibold text-slate-800">
                      {voucher.currency} {voucher.subtotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-slate-200 text-slate-600">
                    <span>Total Tanzania VAT:</span>
                    <span className="font-mono font-semibold text-slate-800">
                      {voucher.currency} {voucher.totalVat.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>

                  {voucher.roundOffEnabled && Math.abs(voucher.roundOffAdjustment) > 0.001 && (
                    <div className="flex items-center justify-between py-1 border-b border-slate-200 text-slate-500 italic">
                      <span>Round Off Adjustment:</span>
                      <span className="font-mono">
                        {voucher.roundOffAdjustment >= 0 ? '+' : ''}
                        {voucher.roundOffAdjustment.toFixed(2)}
                      </span>
                    </div>
                  )}

                  {/* Grand Total Banner */}
                  <div
                    className="flex items-center justify-between p-3 rounded-lg text-white font-bold text-sm shadow-xs"
                    style={{ backgroundColor: companyProfile.theme.primaryColor || '#0F2C59' }}
                  >
                    <span>GRAND TOTAL:</span>
                    <span className="font-mono text-base">
                      {voucher.currency} {voucher.finalGrandTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>

                  {/* Amount in Words */}
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-700 italic">
                    <strong>Amount in Words:</strong> "{voucher.amountInWords || 'Tanzania Shillings'}"
                  </div>

                  {voucher.type === 'PROFORMA' && voucher.expiresOn && (
                    <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg text-[10px] text-amber-800 font-semibold flex items-center justify-between">
                      <span>Quotation Validity:</span>
                      <span>Valid until {voucher.expiresOn} ({voucher.proformaValidityDays || 7} Days Net)</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Stamp & Authorized Signatory Footer */}
            <div className="pt-8 border-t border-slate-200 flex items-end justify-between">
              <div className="text-[10px] text-slate-500 max-w-xs leading-relaxed">
                <p>This is a verified computer generated commercial document.</p>
                <p className="font-mono mt-0.5">TIN: {companyProfile.tin} | Valid for Tax Reporting</p>
              </div>

              <div className="flex items-center space-x-6">
                {/* Stamp */}
                {companyProfile.stampUrl ? (
                  <img
                    src={companyProfile.stampUrl}
                    alt="Official Seal"
                    className="w-20 h-20 object-contain opacity-90"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-full border-2 border-dashed border-indigo-300 flex items-center justify-center text-[10px] font-bold text-indigo-400 text-center">
                    OFFICIAL SEAL
                  </div>
                )}

                {/* Signature Line */}
                <div className="text-center">
                  {companyProfile.signatureUrl ? (
                    <img
                      src={companyProfile.signatureUrl}
                      alt="Signature"
                      className="h-10 object-contain mx-auto"
                    />
                  ) : (
                    <div className="h-8 w-28 border-b-2 border-slate-700 mb-1" />
                  )}
                  <span className="text-[10px] font-bold text-slate-700 uppercase tracking-wider block">
                    Authorized Signatory
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
