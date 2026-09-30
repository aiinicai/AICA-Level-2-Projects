import React, { useState, useMemo } from 'react';
import {
  Plus,
  Upload,
  Search,
  Filter,
  Download,
  Calendar,
  Clock,
  CheckCircle,
  AlertCircle,
  X,
  FileSpreadsheet,
  Eye
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Invoice, InvoiceStatus, GSTType, Customer } from '../../types';
import { formatINR, formatDate, calculateDueDate } from '../../utils/formatters';
import { exportToCSV, exportToExcel } from '../../utils/excelEngine';
import { ExcelImportWizard } from './ExcelImportWizard';
import { ROLE_DEFINITIONS } from '../../utils/rbac';

export const InvoiceListView: React.FC = () => {
  const { invoices, customers, addInvoice, importInvoicesBatch, currentUser } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isImportWizardOpen, setIsImportWizardOpen] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);

  const rolePerms = ROLE_DEFINITIONS[currentUser.role];
  const canUpload = rolePerms?.canUploadInvoices ?? false;
  const canCreate = rolePerms?.canCreateInvoices ?? false;

  const filteredInvoices = useMemo(() => {
    return invoices.filter(inv => {
      const matchSearch =
        inv.invoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
        inv.customerName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        inv.customerGstin.toLowerCase().includes(searchTerm.toLowerCase());

      const matchStatus = statusFilter === 'All' || inv.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [invoices, searchTerm, statusFilter]);

  const handleExport = (type: 'csv' | 'excel') => {
    const exportData = filteredInvoices.map(inv => ({
      'Invoice No': inv.invoiceNumber,
      'Date': inv.invoiceDate,
      'Due Date': inv.dueDate,
      'Customer': inv.customerName,
      'GSTIN': inv.customerGstin,
      'Taxable Value': inv.taxableValue,
      'GST Rate %': inv.gstRate,
      'GST Amount': inv.gstAmount,
      'Total Value': inv.totalInvoiceValue,
      'TDS Expected': inv.expectedTds,
      'Amount Received': inv.amountReceived,
      'Balance Outstanding': inv.balance,
      'Status': inv.status
    }));

    if (type === 'csv') {
      exportToCSV(exportData, 'Sales_Register_FinRecon');
    } else {
      exportToExcel(exportData, 'Sales_Register_FinRecon', 'Sales Register');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Sales / Invoices Register</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            B2B Sales billing, payment receipt statuses, TDS deductions, and customer receivables.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`hidden sm:inline-flex px-2.5 py-1 text-[11px] font-bold rounded-lg border ${rolePerms.badgeClass}`}>
            {currentUser.role}
          </span>
          <button
            onClick={() => handleExport('excel')}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors flex items-center gap-1.5"
            title="Export to Excel"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Export</span>
          </button>
          {canUpload && (
            <button
              onClick={() => setIsImportWizardOpen(true)}
              className="px-3 py-2 text-xs font-semibold text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300 rounded-lg transition-colors flex items-center gap-1.5"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
              <span>Upload Invoices (CSV, Excel, PDF)</span>
            </button>
          )}
          {canCreate && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="px-3.5 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-4 h-4" />
              <span>New Invoice</span>
            </button>
          )}
        </div>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-white p-4 rounded-xl border border-slate-200">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search invoice number, party name, or GSTIN..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600 bg-slate-50/50"
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs font-medium text-slate-500 whitespace-nowrap">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 py-2 px-3 bg-slate-50/50 text-slate-700"
          >
            <option value="All">All Invoices</option>
            <option value="Unpaid">Unpaid</option>
            <option value="Partially Paid">Partially Paid</option>
            <option value="Overdue">Overdue</option>
            <option value="Fully Paid">Fully Paid</option>
          </select>
        </div>
      </div>

      {/* Invoices Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
              <tr>
                <th className="p-3.5">Invoice No & Date</th>
                <th className="p-3.5">Customer / Party</th>
                <th className="p-3.5 text-right">Taxable</th>
                <th className="p-3.5 text-right">Total Inv Value</th>
                <th className="p-3.5 text-right">Expected TDS</th>
                <th className="p-3.5 text-right">Received</th>
                <th className="p-3.5 text-right">Outstanding</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center text-slate-400">
                    No invoices match the selected filter.
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-3.5">
                      <span className="font-mono font-bold text-slate-900 block">{inv.invoiceNumber}</span>
                      <span className="text-[10px] text-slate-400">
                        {formatDate(inv.invoiceDate)} • Due: {formatDate(inv.dueDate)}
                      </span>
                    </td>

                    <td className="p-3.5">
                      <span className="font-bold text-slate-800 block truncate max-w-xs">{inv.customerName}</span>
                      <span className="text-[10px] text-slate-400 font-mono">GST: {inv.customerGstin}</span>
                    </td>

                    <td className="p-3.5 text-right font-mono text-slate-600">
                      {formatINR(inv.taxableValue, false)}
                    </td>

                    <td className="p-3.5 text-right font-mono font-bold text-slate-900">
                      {formatINR(inv.totalInvoiceValue, false)}
                    </td>

                    <td className="p-3.5 text-right font-mono text-purple-700">
                      {inv.expectedTds > 0 ? formatINR(inv.expectedTds, false) : '-'}
                    </td>

                    <td className="p-3.5 text-right font-mono font-semibold text-emerald-700">
                      {formatINR(inv.amountReceived, false)}
                    </td>

                    <td className="p-3.5 text-right font-mono font-bold">
                      <span className={inv.balance > 0 ? (inv.status === 'Overdue' ? 'text-rose-600' : 'text-amber-700') : 'text-slate-400'}>
                        {formatINR(inv.balance, false)}
                      </span>
                    </td>

                    <td className="p-3.5">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                          inv.status === 'Fully Paid'
                            ? 'bg-emerald-100 text-emerald-800'
                            : inv.status === 'Overdue'
                            ? 'bg-rose-100 text-rose-800'
                            : inv.status === 'Partially Paid'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {inv.status}
                      </span>
                    </td>

                    <td className="p-3.5 text-center">
                      <button
                        onClick={() => setSelectedInvoice(inv)}
                        className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg transition-colors"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Invoice Creation Modal */}
      {isCreateModalOpen && (
        <CreateInvoiceModal
          customers={customers}
          onClose={() => setIsCreateModalOpen(false)}
          onSave={(invData) => {
            addInvoice(invData);
            setIsCreateModalOpen(false);
          }}
        />
      )}

      {/* Excel Import Wizard */}
      {isImportWizardOpen && (
        <ExcelImportWizard
          isOpen={isImportWizardOpen}
          customers={customers}
          existingInvoices={invoices}
          onClose={() => setIsImportWizardOpen(false)}
          onImportComplete={(newInvoices) => {
            importInvoicesBatch(newInvoices);
            setIsImportWizardOpen(false);
          }}
        />
      )}

      {/* Invoice Detail Modal */}
      {selectedInvoice && (
        <InvoiceDetailModal
          invoice={selectedInvoice}
          onClose={() => setSelectedInvoice(null)}
        />
      )}
    </div>
  );
};

interface CreateInvoiceModalProps {
  customers: Customer[];
  onClose: () => void;
  onSave: (data: Omit<Invoice, 'id' | 'createdAt'>) => void;
}

const CreateInvoiceModal: React.FC<CreateInvoiceModalProps> = ({ customers, onClose, onSave }) => {
  const [customerId, setCustomerId] = useState(customers[0]?.id || '');
  const [invoiceNumber, setInvoiceNumber] = useState(`INV-2026-${Math.floor(100 + Math.random() * 900)}`);
  const [invoiceDate, setInvoiceDate] = useState('2026-09-15');
  const [taxableValue, setTaxableValue] = useState(100000);
  const [gstRate, setGstRate] = useState(18);
  const [isInterState, setIsInterState] = useState(false);
  const [notes, setNotes] = useState('');

  const selectedCust = customers.find(c => c.id === customerId);

  // Auto calculate Due Date
  const dueDate = useMemo(() => {
    const terms = selectedCust?.paymentTerms || 30;
    return calculateDueDate(invoiceDate, terms);
  }, [invoiceDate, selectedCust]);

  // Tax and TDS Calculations (Section 10 & 18)
  const gstAmount = (taxableValue * gstRate) / 100;
  const totalInvoiceValue = taxableValue + gstAmount;

  const expectedTds = useMemo(() => {
    if (!selectedCust?.tdsApplicable) return 0;
    const rate = selectedCust.tdsRate || (selectedCust.tdsSection === '194J' ? 10 : 2);
    // TDS in India is strictly calculated on Taxable Value (excluding GST) under CBDT circular
    return Math.round((taxableValue * rate) / 100);
  }, [taxableValue, selectedCust]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCust) return;

    onSave({
      invoiceNumber,
      invoiceDate,
      dueDate,
      customerId: selectedCust.id,
      customerName: selectedCust.name,
      customerGstin: selectedCust.gstin,
      customerPan: selectedCust.pan,
      customerState: selectedCust.state,
      hsnSacCode: '998311',
      description: notes || 'Professional / Software Development Services',
      taxableValue,
      gstRate,
      gstType: isInterState ? 'IGST' : 'CGST_SGST',
      cgst: isInterState ? 0 : gstAmount / 2,
      sgst: isInterState ? 0 : gstAmount / 2,
      igst: isInterState ? gstAmount : 0,
      cess: 0,
      cgstAmount: isInterState ? 0 : gstAmount / 2,
      sgstAmount: isInterState ? 0 : gstAmount / 2,
      igstAmount: isInterState ? gstAmount : 0,
      gstAmount,
      totalInvoiceValue,
      paymentTerms: selectedCust.paymentTerms || 30,
      tdsApplicable: selectedCust.tdsApplicable,
      tdsSection: selectedCust.tdsSection,
      tdsRate: selectedCust.tdsRate,
      expectedTds,
      netReceivable: totalInvoiceValue - expectedTds,
      amountAllocated: 0,
      tdsDeducted: 0,
      amountReceived: 0,
      balance: totalInvoiceValue,
      status: 'Unpaid',
      notes
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white w-full max-w-xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-sm">Create New Tax Invoice</h3>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Invoice Number *</label>
              <input
                type="text"
                required
                value={invoiceNumber}
                onChange={e => setInvoiceNumber(e.target.value)}
                className="w-full p-2 font-mono font-bold rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Invoice Date *</label>
              <input
                type="date"
                required
                value={invoiceDate}
                onChange={e => setInvoiceDate(e.target.value)}
                className="w-full p-2 rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
              />
            </div>

            <div className="col-span-2">
              <label className="font-semibold text-slate-700 block mb-1">Customer / Buyer *</label>
              <select
                value={customerId}
                onChange={e => setCustomerId(e.target.value)}
                className="w-full p-2 rounded-lg border border-slate-200 bg-white focus:border-emerald-600"
              >
                {customers.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.gstin}) - Terms: {c.paymentTerms}d
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Taxable Amount (₹) *</label>
              <input
                type="number"
                required
                value={taxableValue}
                onChange={e => setTaxableValue(parseFloat(e.target.value) || 0)}
                className="w-full p-2 font-mono font-bold rounded-lg border border-slate-200 focus:border-emerald-600 outline-hidden"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">GST Rate (%) *</label>
              <select
                value={gstRate}
                onChange={e => setGstRate(parseFloat(e.target.value))}
                className="w-full p-2 rounded-lg border border-slate-200 bg-white"
              >
                <option value={18}>18% (Standard Services/Goods)</option>
                <option value={12}>12%</option>
                <option value={5}>5%</option>
                <option value={28}>28%</option>
                <option value={0}>0% (Nil / Exempt)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="isInterState"
              checked={isInterState}
              onChange={e => setIsInterState(e.target.checked)}
              className="rounded text-emerald-600"
            />
            <label htmlFor="isInterState" className="text-slate-700 font-medium">
              Inter-State Supply (Apply IGST instead of CGST + SGST)
            </label>
          </div>

          {/* Computed Tax & TDS Preview Card */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5 font-medium text-slate-700">
            <div className="flex justify-between">
              <span>Taxable Subtotal:</span>
              <span className="font-mono font-bold text-slate-900">{formatINR(taxableValue)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>GST ({isInterState ? `IGST ${gstRate}%` : `CGST ${gstRate / 2}% + SGST ${gstRate / 2}%`}):</span>
              <span className="font-mono font-bold text-slate-900">{formatINR(gstAmount)}</span>
            </div>
            <div className="flex justify-between text-slate-900 font-bold pt-1 border-t border-slate-200">
              <span>Total Invoice Value:</span>
              <span className="font-mono text-emerald-800 text-sm">{formatINR(totalInvoiceValue)}</span>
            </div>
            <div className="flex justify-between text-purple-700 pt-1 border-t border-dashed border-slate-200 text-[11px]">
              <span>Expected TDS by Customer ({selectedCust?.tdsSection || '194C'} @ {selectedCust?.tdsRate || 2}% on Taxable):</span>
              <span className="font-mono font-bold">{formatINR(expectedTds)}</span>
            </div>
            <div className="flex justify-between text-slate-500 text-[11px]">
              <span>Computed Due Date ({selectedCust?.paymentTerms || 30} days):</span>
              <span className="font-bold text-slate-800">{formatDate(dueDate)}</span>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg font-bold shadow-xs"
            >
              Generate Invoice
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const InvoiceDetailModal: React.FC<{ invoice: Invoice; onClose: () => void }> = ({ invoice, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900 text-sm">{invoice.invoiceNumber}</h3>
            <p className="text-xs text-slate-500">{invoice.customerName}</p>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Invoice Date</span>
              <span className="font-semibold text-slate-800">{formatDate(invoice.invoiceDate)}</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Due Date</span>
              <span className="font-semibold text-slate-800">{formatDate(invoice.dueDate)}</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Customer GSTIN</span>
              <span className="font-mono font-bold text-slate-800">{invoice.customerGstin}</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase font-bold block">Status</span>
              <span className="font-bold text-emerald-700">{invoice.status}</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
            <div className="flex justify-between">
              <span className="text-slate-600">Taxable Value:</span>
              <span className="font-mono font-bold text-slate-900">{formatINR(invoice.taxableValue)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">GST ({invoice.gstRate}%):</span>
              <span className="font-mono font-bold text-slate-900">{formatINR(invoice.gstAmount)}</span>
            </div>
            <div className="flex justify-between font-bold text-slate-900 pt-1 border-t border-slate-200">
              <span>Total Invoice Amount:</span>
              <span className="font-mono text-emerald-800">{formatINR(invoice.totalInvoiceValue)}</span>
            </div>
            <div className="flex justify-between text-purple-700 font-semibold pt-1 border-t border-slate-200">
              <span>Expected TDS:</span>
              <span className="font-mono">{formatINR(invoice.expectedTds)}</span>
            </div>
            <div className="flex justify-between text-emerald-700 font-semibold">
              <span>Amount Received:</span>
              <span className="font-mono">{formatINR(invoice.amountReceived)}</span>
            </div>
            <div className="flex justify-between text-rose-700 font-bold pt-1 border-t border-slate-200 text-sm">
              <span>Balance Due:</span>
              <span className="font-mono">{formatINR(invoice.balance)}</span>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-900 text-white rounded-lg font-semibold"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
