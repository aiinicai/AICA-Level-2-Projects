import React, { useState } from 'react';
import { 
  FileText, 
  Download, 
  Send, 
  Search, 
  Eye, 
  CheckCircle2, 
  X
} from 'lucide-react';
import { InvoiceItem } from '../types';
import { systemService } from '../lib/services/systemService';

interface InvoicesScreenProps {
  invoices: InvoiceItem[];
  loading: boolean;
  onRefresh: () => void;
  onNavigateToEmails: () => void;
}

export const InvoicesScreen: React.FC<InvoicesScreenProps> = ({
  invoices,
  loading,
  onRefresh,
  onNavigateToEmails,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedInvoice, setSelectedInvoice] = useState<InvoiceItem | null>(null);
  const [noticeMsg, setNoticeMsg] = useState('');

  const handleDownloadPdf = (invoice: InvoiceItem) => {
    try {
      systemService.downloadInvoicePdf(invoice);
      setNoticeMsg(`Downloading ${invoice.invoiceNumber}.pdf`);
    } catch (err: any) {
      setNoticeMsg('Failed to generate PDF: ' + err.message);
    }
  };

  const handleResendEmail = (invoice: InvoiceItem) => {
    try {
      setNoticeMsg(`Invoice email for ${invoice.invoiceNumber} archived in Email Outbox!`);
      onRefresh();
    } catch (err: any) {
      setNoticeMsg('Error: ' + err.message);
    }
  };

  const filteredInvoices = invoices.filter(
    (inv) =>
      inv.invoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.clientName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inv.clientCode.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Tax Invoices Master</h1>
          <p className="text-sm text-slate-500">
            Automatically generated PDF tax invoices, sequential numbers (INV-YYYY-XXXX), and dispatch tracking.
          </p>
        </div>

        <button
          onClick={onNavigateToEmails}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 rounded-lg text-xs font-semibold shadow-xs transition"
        >
          <Send className="w-4 h-4 text-blue-600" />
          <span>View Invoice Email Outbox</span>
        </button>
      </div>

      {noticeMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl flex items-center justify-between text-sm">
          <span>{noticeMsg}</span>
          <button onClick={() => setNoticeMsg('')} className="text-emerald-600 hover:text-emerald-800">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter / Search */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search invoice number, client..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="text-xs text-slate-500 font-medium">
          Total Invoices: <strong className="text-slate-900">{invoices.length}</strong>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold uppercase text-slate-600 tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Invoice No</th>
                <th className="py-3.5 px-4">Invoice Date</th>
                <th className="py-3.5 px-4">Client</th>
                <th className="py-3.5 px-4">Billing Period</th>
                <th className="py-3.5 px-3 text-right">Subtotal</th>
                <th className="py-3.5 px-3 text-right">Tax (18%)</th>
                <th className="py-3.5 px-4 text-right bg-blue-50/40 text-blue-950 font-bold">Total Amount</th>
                <th className="py-3.5 px-4 text-center">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    Loading invoices...
                  </td>
                </tr>
              ) : filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    No invoices generated yet. Confirm billing to generate invoices automatically.
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4 font-mono font-bold text-blue-700">
                      {inv.invoiceNumber}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-600">
                      {new Date(inv.invoiceDate).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-semibold text-slate-900 block">{inv.clientName}</span>
                      <span className="font-mono text-xs text-slate-400">{inv.clientCode}</span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-600">
                      {inv.quarter} FY {inv.financialYear}
                    </td>
                    <td className="py-3.5 px-3 text-right font-mono text-xs">
                      ₹{inv.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-3 text-right font-mono text-xs text-slate-500">
                      ₹{inv.tax.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-blue-900 bg-blue-50/30">
                      ₹{inv.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3 h-3 mr-1" /> {inv.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-2">
                      <button
                        onClick={() => setSelectedInvoice(inv)}
                        title="View Details"
                        className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-md transition"
                      >
                        <Eye className="w-4 h-4" />
                      </button>

                      <button
                        onClick={() => handleDownloadPdf(inv)}
                        title="Download Vector PDF"
                        className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-md transition inline-block"
                      >
                        <Download className="w-4 h-4" />
                      </button>

                      <button
                        onClick={() => handleResendEmail(inv)}
                        title="Resend Invoice Email"
                        className="p-1.5 text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 rounded-md transition"
                      >
                        <Send className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invoice Details Preview Modal */}
      {selectedInvoice && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-slate-200">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50 sticky top-0 z-10">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-base">
                  Tax Invoice Details: {selectedInvoice.invoiceNumber}
                </h3>
              </div>
              <button onClick={() => setSelectedInvoice(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-8 space-y-6 text-sm">
              {/* Header Box */}
              <div className="border border-slate-200 rounded-xl p-6 bg-slate-50/50 space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900">TAX INVOICE</h2>
                    <p className="font-mono text-xs text-blue-600 font-bold mt-1">{selectedInvoice.invoiceNumber}</p>
                    <p className="text-xs text-slate-500">
                      Date: {new Date(selectedInvoice.invoiceDate).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </p>
                  </div>
                  <div className="text-right text-xs text-slate-500 space-y-1">
                    <p className="font-bold text-slate-800">FinTech Automated Solutions Pvt Ltd</p>
                    <p>401 Cyber Towers, Hi-Tech City, Hyderabad</p>
                    <p>GSTIN: 36AAACF1234D1Z5</p>
                  </div>
                </div>

                <div className="border-t border-slate-200 pt-4 grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="font-semibold text-slate-500 block uppercase text-[10px]">Billed To:</span>
                    <strong className="text-sm font-bold text-slate-900">{selectedInvoice.clientName}</strong>
                    <p className="font-mono text-slate-500">{selectedInvoice.clientCode}</p>
                    <p className="text-slate-600">{selectedInvoice.clientEmail}</p>
                  </div>
                  <div>
                    <span className="font-semibold text-slate-500 block uppercase text-[10px]">Billing Period:</span>
                    <strong className="text-slate-800">{selectedInvoice.quarter} FY {selectedInvoice.financialYear}</strong>
                    <p className="text-slate-500 mt-1">Payment Terms: 30 days</p>
                    <p className="text-emerald-700 font-semibold mt-1">Status: Dispatched via Email</p>
                  </div>
                </div>
              </div>

              {/* Items Breakdown */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100 text-slate-700 uppercase font-semibold">
                    <tr>
                      <th className="py-2.5 px-4">Item Description</th>
                      <th className="py-2.5 px-4 text-right">File Count</th>
                      <th className="py-2.5 px-4 text-right">Rate / File</th>
                      <th className="py-2.5 px-4 text-right">Amount (₹)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr>
                      <td className="py-3 px-4 font-medium text-slate-800">
                        Quarterly Automated File Processing Services ({selectedInvoice.quarter} FY {selectedInvoice.financialYear})
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-semibold">
                        {selectedInvoice.totalFileCount.toLocaleString('en-IN')}
                      </td>
                      <td className="py-3 px-4 text-right font-mono">
                        ₹{selectedInvoice.ratePerFile}
                      </td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-slate-900">
                        ₹{selectedInvoice.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                  </tbody>
                  <tfoot className="bg-slate-50 divide-y divide-slate-200 text-xs">
                    <tr>
                      <td colSpan={3} className="py-2 px-4 text-right font-medium text-slate-600">Subtotal:</td>
                      <td className="py-2 px-4 text-right font-mono">
                        ₹{selectedInvoice.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                    <tr>
                      <td colSpan={3} className="py-2 px-4 text-right font-medium text-slate-600">GST / Tax (18%):</td>
                      <td className="py-2 px-4 text-right font-mono">
                        ₹{selectedInvoice.tax.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                    <tr className="bg-blue-50/60 font-bold text-blue-950">
                      <td colSpan={3} className="py-3 px-4 text-right text-sm">TOTAL AMOUNT:</td>
                      <td className="py-3 px-4 text-right font-mono text-base text-blue-900">
                        ₹{selectedInvoice.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between sticky bottom-0">
              <span className="text-xs text-slate-500">
                Official Tax Invoice Document
              </span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleDownloadPdf(selectedInvoice)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition flex items-center gap-1.5"
                >
                  <Download className="w-4 h-4" />
                  <span>Download PDF</span>
                </button>
                <button
                  onClick={() => setSelectedInvoice(null)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-100 transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
