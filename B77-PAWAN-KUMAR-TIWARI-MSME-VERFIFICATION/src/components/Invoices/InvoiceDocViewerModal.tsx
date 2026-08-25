import React from 'react';
import {
  X,
  Download,
  FileText,
  Image,
  ExternalLink,
  ShieldCheck,
  Calendar,
  Building2,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { Invoice } from '../../types';
import { formatINR, formatDate } from '../../utils/formatters';

interface InvoiceDocViewerModalProps {
  invoice: Invoice | null;
  onClose: () => void;
}

export const InvoiceDocViewerModal: React.FC<InvoiceDocViewerModalProps> = ({
  invoice,
  onClose,
}) => {
  if (!invoice) return null;

  const isPdf =
    invoice.attachmentType === 'pdf' ||
    invoice.attachmentFileName?.toLowerCase().endsWith('.pdf') ||
    invoice.attachmentUrl?.startsWith('data:application/pdf');

  const handleDownload = () => {
    if (!invoice.attachmentUrl) return;
    const a = document.createElement('a');
    a.href = invoice.attachmentUrl;
    a.download = invoice.attachmentFileName || `${invoice.invoiceNumber}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div
      id="invoice-doc-viewer-modal-backdrop"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div
        id="invoice-doc-viewer-modal"
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-100 border border-blue-200 flex items-center justify-center text-blue-700 font-bold shrink-0">
              {isPdf ? <FileText className="w-5 h-5" /> : <Image className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">
                  {invoice.attachmentFileName || `Invoice Document - ${invoice.invoiceNumber}`}
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-slate-200 text-slate-700">
                  {isPdf ? 'PDF Document' : 'JPEG / Image'}
                </span>
                {invoice.extractedViaAI && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-700 border border-purple-200 flex items-center gap-1">
                    ✨ AI Extracted
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Vendor: <strong>{invoice.vendorName}</strong> | Inv No: <strong>{invoice.invoiceNumber}</strong>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {invoice.attachmentUrl && (
              <button
                onClick={handleDownload}
                className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer"
                title="Download attached document"
              >
                <Download className="w-3.5 h-3.5" />
                Download Original
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body: Left Preview, Right Statutory Details */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-0">
          {/* Document Display Panel */}
          <div className="flex-1 bg-slate-900 p-4 flex items-center justify-center overflow-auto relative">
            {invoice.attachmentUrl ? (
              isPdf ? (
                <iframe
                  src={invoice.attachmentUrl}
                  title="PDF Invoice Document"
                  className="w-full h-full rounded-lg bg-white border-0"
                />
              ) : (
                <div className="max-h-full max-w-full flex items-center justify-center">
                  <img
                    src={invoice.attachmentUrl}
                    alt={`Invoice ${invoice.invoiceNumber}`}
                    className="max-h-[75vh] max-w-full object-contain rounded-lg shadow-lg border border-slate-700"
                  />
                </div>
              )
            ) : (
              /* Fallback Mock Document Preview Canvas */
              <div className="w-full max-w-lg bg-white text-slate-900 p-8 rounded-xl shadow-2xl border border-slate-200 text-xs space-y-6">
                <div className="flex justify-between items-start border-b pb-4">
                  <div>
                    <h2 className="text-base font-extrabold text-slate-900 uppercase tracking-tight">
                      TAX INVOICE
                    </h2>
                    <p className="text-[11px] font-semibold text-slate-700 mt-1">{invoice.vendorName}</p>
                    <p className="text-[10px] text-slate-500">GSTIN: {invoice.vendorCode ? `27${invoice.vendorCode}1Z5` : '27AABCS9876E1Z2'}</p>
                    <p className="text-[10px] text-slate-500">Category: {invoice.msmeCategory} Enterprise</p>
                  </div>
                  <div className="text-right text-[11px]">
                    <div className="font-bold text-slate-800">Invoice #{invoice.invoiceNumber}</div>
                    <div className="text-slate-500">Date: {formatDate(invoice.invoiceDate)}</div>
                    <div className="text-slate-500">PO: {invoice.poNumber}</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
                    Item & Service Particulars
                  </div>
                  <div className="border border-slate-200 rounded-lg p-3 bg-slate-50">
                    <div className="font-semibold text-slate-900">{invoice.materialDescription}</div>
                    <div className="flex justify-between text-[11px] text-slate-500 mt-2">
                      <span>Basic Taxable Value:</span>
                      <strong className="text-slate-800">{formatINR(invoice.invoiceAmount)}</strong>
                    </div>
                    <div className="flex justify-between text-[11px] text-slate-500 mt-1">
                      <span>GST Applicable (18%):</span>
                      <strong className="text-slate-800">{formatINR(invoice.gstAmount)}</strong>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-3 flex justify-between items-center">
                  <span className="font-bold text-slate-900 text-sm">TOTAL AMOUNT PAYABLE:</span>
                  <span className="font-extrabold text-blue-700 text-base">{formatINR(invoice.totalInvoiceAmount)}</span>
                </div>

                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-[10px] text-blue-900 space-y-1">
                  <div className="font-bold flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-blue-700" />
                    MSMED Act Statutory Clause Printed on Invoice:
                  </div>
                  <p>
                    "Supplier is registered under MSMED Act 2006. Payment terms subject to Section 15 statutory limit of 45 days. Delayed payments attract Section 16 compounded monthly interest at 3 times RBI Repo Rate."
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Right Sidebar: Statutory Breakdown & Metadata */}
          <div className="w-full lg:w-80 bg-slate-50 border-l border-slate-200 p-5 overflow-y-auto space-y-5 shrink-0 text-xs">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Statutory Compliance
              </span>
              <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">MSME Classification:</span>
                  <span className="font-bold text-slate-800">{invoice.msmeCategory}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Acceptance Date:</span>
                  <span className="font-semibold text-slate-800">{formatDate(invoice.acceptanceDate)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Section 15 Limit:</span>
                  <span className="font-bold text-emerald-700">{invoice.statutoryLimitDays} Days</span>
                </div>
                <div className="flex justify-between border-t pt-2">
                  <span className="font-bold text-slate-700">Statutory Due Date:</span>
                  <span className="font-bold text-blue-700">{formatDate(invoice.finalDueDate)}</span>
                </div>
              </div>
            </div>

            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Financial Summary
              </span>
              <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-500">Basic Amount:</span>
                  <span className="font-semibold text-slate-800">{formatINR(invoice.invoiceAmount)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">GST Value:</span>
                  <span className="font-semibold text-slate-800">{formatINR(invoice.gstAmount)}</span>
                </div>
                <div className="flex justify-between border-t pt-1 font-bold">
                  <span className="text-slate-900">Total Invoice:</span>
                  <span className="text-slate-900">{formatINR(invoice.totalInvoiceAmount)}</span>
                </div>
                <div className="flex justify-between text-emerald-700">
                  <span>Amount Settled:</span>
                  <span className="font-semibold">{formatINR(invoice.amountPaid)}</span>
                </div>
                <div className="flex justify-between text-rose-700 font-bold border-t pt-1">
                  <span>Outstanding:</span>
                  <span>{formatINR(invoice.outstandingAmount)}</span>
                </div>
              </div>
            </div>

            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Document Details
              </span>
              <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-2xs space-y-1.5 text-[11px] text-slate-600">
                <div>
                  <strong>File:</strong> {invoice.attachmentFileName || 'Invoice_Document.pdf'}
                </div>
                <div>
                  <strong>PO Ref:</strong> {invoice.poNumber} ({formatDate(invoice.poDate)})
                </div>
                <div>
                  <strong>MRN Date:</strong> {formatDate(invoice.mrnDate)}
                </div>
                <div>
                  <strong>Terms:</strong> {invoice.agreedPaymentTerms}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
