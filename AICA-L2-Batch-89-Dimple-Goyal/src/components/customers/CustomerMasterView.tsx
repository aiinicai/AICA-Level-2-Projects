import React, { useState, useMemo } from 'react';
import {
  Plus,
  Search,
  Building2,
  Phone,
  Mail,
  Edit2,
  Trash2,
  Eye,
  Download,
  CheckCircle,
  X
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { Customer } from '../../types';
import { formatINR, isValidGSTIN, isValidPAN, extractPANFromGSTIN } from '../../utils/formatters';
import { exportToCSV, exportToExcel } from '../../utils/excelEngine';
import { Customer360Modal } from './Customer360Modal';

export const CustomerMasterView: React.FC = () => {
  const { customers, invoices, bankTransactions, allocations, tdsRecords, addCustomer, updateCustomer, deleteCustomer, currentUser } = useApp();

  const [searchTerm, setSearchTerm] = useState('');
  const [filterState, setFilterState] = useState('All');
  const [selectedCustomerFor360, setSelectedCustomerFor360] = useState<Customer | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);

  const canEdit = currentUser.role !== 'Viewer';

  // State filtering options
  const states = useMemo(() => {
    const list = Array.from(new Set(customers.map(c => c.state)));
    return ['All', ...list];
  }, [customers]);

  const filteredCustomers = useMemo(() => {
    return customers.filter(c => {
      const matchSearch =
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.gstin.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.customerId.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.contactPerson.toLowerCase().includes(searchTerm.toLowerCase());

      const matchState = filterState === 'All' || c.state === filterState;
      return matchSearch && matchState;
    });
  }, [customers, searchTerm, filterState]);

  // Compute live customer balances
  const getCustomerBalance = (custId: string) => {
    const custInvoices = invoices.filter(i => i.customerId === custId && i.balance > 0);
    const totalOut = custInvoices.reduce((s, i) => s + i.balance, 0);
    const overdue = custInvoices.filter(i => i.status === 'Overdue').reduce((s, i) => s + i.balance, 0);
    return { totalOut, overdue, openBills: custInvoices.length };
  };

  const handleExport = (type: 'csv' | 'excel') => {
    const exportData = customers.map(c => ({
      'Customer ID': c.customerId,
      'Name': c.name,
      'Legal Name': c.legalName,
      'GSTIN': c.gstin,
      'PAN': c.pan,
      'Type': c.customerType,
      'State': c.state,
      'Contact Person': c.contactPerson,
      'Email': c.email,
      'Phone': c.phone,
      'Payment Terms (Days)': c.paymentTerms,
      'Credit Limit': c.creditLimit,
      'TDS Applicable': c.tdsApplicable ? 'Yes' : 'No',
      'TDS Section': c.tdsSection || 'N/A',
      'Status': c.status
    }));

    if (type === 'csv') {
      exportToCSV(exportData, 'Customer_Master_FinRecon');
    } else {
      exportToExcel(exportData, 'Customer_Master_FinRecon', 'Customers');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Customer Master</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage debtors, payment terms, GSTIN/PAN profiles, and customer-specific TDS sections.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleExport('excel')}
            className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors flex items-center gap-1.5"
            title="Export to Excel"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Export</span>
          </button>
          {canEdit && (
            <button
              onClick={() => {
                setEditingCustomer(null);
                setIsCreateModalOpen(true);
              }}
              className="px-3.5 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-4 h-4" />
              <span>Add Customer</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3 bg-white p-4 rounded-xl border border-slate-200">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search by customer name, GSTIN, PAN, contact person..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600 bg-slate-50/50"
          />
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-xs font-medium text-slate-500 whitespace-nowrap">State:</label>
          <select
            value={filterState}
            onChange={(e) => setFilterState(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 py-2 px-3 bg-slate-50/50 text-slate-700"
          >
            {states.map(st => (
              <option key={st} value={st}>{st}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Customer Master Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500 tracking-wider">
              <tr>
                <th className="p-4">Customer Name & ID</th>
                <th className="p-4">GSTIN & PAN</th>
                <th className="p-4">Terms & Credit</th>
                <th className="p-4">TDS Profile</th>
                <th className="p-4 text-right">Outstanding</th>
                <th className="p-4 text-right">Overdue</th>
                <th className="p-4 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {filteredCustomers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-400">
                    No customers match your search criteria.
                  </td>
                </tr>
              ) : (
                filteredCustomers.map((cust) => {
                  const bal = getCustomerBalance(cust.id);
                  return (
                    <tr key={cust.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="p-4">
                        <div className="flex items-start gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center justify-center font-bold text-xs shrink-0">
                            {cust.name.charAt(0)}
                          </div>
                          <div>
                            <button
                              onClick={() => setSelectedCustomerFor360(cust)}
                              className="font-bold text-slate-900 hover:text-emerald-700 text-left transition-colors"
                            >
                              {cust.name}
                            </button>
                            <p className="text-[10px] text-slate-400 font-mono">{cust.customerId} • {cust.state}</p>
                          </div>
                        </div>
                      </td>

                      <td className="p-4">
                        <span className="font-mono font-semibold text-slate-800 block text-[11px]">{cust.gstin}</span>
                        <span className="text-[10px] text-slate-400 font-mono">PAN: {cust.pan}</span>
                      </td>

                      <td className="p-4">
                        <span className="font-semibold text-slate-800 block">{cust.paymentTerms} Days</span>
                        <span className="text-[10px] text-slate-500">Limit: {formatINR(cust.creditLimit, false)}</span>
                      </td>

                      <td className="p-4">
                        {cust.tdsApplicable ? (
                          <div>
                            <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800">
                              {cust.tdsSection} ({cust.tdsRate}%)
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Exempt</span>
                        )}
                      </td>

                      <td className="p-4 text-right">
                        <span className="font-mono font-bold text-slate-900 block">{formatINR(bal.totalOut, false)}</span>
                        <span className="text-[10px] text-slate-400">{bal.openBills} open invoices</span>
                      </td>

                      <td className="p-4 text-right">
                        {bal.overdue > 0 ? (
                          <span className="font-mono font-bold text-rose-600 block">{formatINR(bal.overdue, false)}</span>
                        ) : (
                          <span className="text-emerald-600 text-[11px] font-semibold">Current</span>
                        )}
                      </td>

                      <td className="p-4">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => setSelectedCustomerFor360(cust)}
                            className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg transition-colors"
                            title="Open Customer 360 View"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {canEdit && (
                            <>
                              <button
                                onClick={() => {
                                  setEditingCustomer(cust);
                                  setIsCreateModalOpen(true);
                                }}
                                className="p-1.5 text-slate-500 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
                                title="Edit Customer"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => {
                                  if (window.confirm(`Archive customer ${cust.name}?`)) {
                                    deleteCustomer(cust.id);
                                  }
                                }}
                                className="p-1.5 text-slate-500 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition-colors"
                                title="Archive Customer"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Customer 360 View Modal */}
      {selectedCustomerFor360 && (
        <Customer360Modal
          customer={selectedCustomerFor360}
          invoices={invoices}
          bankTransactions={bankTransactions}
          allocations={allocations}
          tdsRecords={tdsRecords}
          onClose={() => setSelectedCustomerFor360(null)}
        />
      )}

      {/* Create / Edit Customer Modal */}
      {isCreateModalOpen && (
        <CustomerFormModal
          existingCustomer={editingCustomer}
          onClose={() => {
            setIsCreateModalOpen(false);
            setEditingCustomer(null);
          }}
          onSave={(data) => {
            if (editingCustomer) {
              updateCustomer(editingCustomer.id, data);
            } else {
              addCustomer(data);
            }
            setIsCreateModalOpen(false);
            setEditingCustomer(null);
          }}
        />
      )}
    </div>
  );
};

interface CustomerFormModalProps {
  existingCustomer: Customer | null;
  onClose: () => void;
  onSave: (data: Omit<Customer, 'id' | 'createdAt'>) => void;
}

const CustomerFormModal: React.FC<CustomerFormModalProps> = ({ existingCustomer, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    customerId: existingCustomer?.customerId || `CUST-${Math.floor(1000 + Math.random() * 9000)}`,
    name: existingCustomer?.name || '',
    legalName: existingCustomer?.legalName || '',
    pan: existingCustomer?.pan || '',
    gstin: existingCustomer?.gstin || '',
    customerType: existingCustomer?.customerType || 'B2B',
    state: existingCustomer?.state || 'Maharashtra',
    address: existingCustomer?.address || '',
    contactPerson: existingCustomer?.contactPerson || '',
    email: existingCustomer?.email || '',
    phone: existingCustomer?.phone || '',
    paymentTerms: existingCustomer?.paymentTerms || 30,
    creditLimit: existingCustomer?.creditLimit || 1000000,
    tdsApplicable: existingCustomer?.tdsApplicable ?? true,
    tdsSection: existingCustomer?.tdsSection || '194C',
    tdsRate: existingCustomer?.tdsRate || 2,
    openingBalance: existingCustomer?.openingBalance || 0,
    status: existingCustomer?.status || 'Active',
    notes: existingCustomer?.notes || '',
    aliases: existingCustomer?.aliases?.join(', ') || ''
  });

  const [errorMsg, setErrorMsg] = useState('');

  // Auto-extract PAN from GSTIN
  const handleGstinChange = (val: string) => {
    const upper = val.toUpperCase();
    const extractedPan = extractPANFromGSTIN(upper);
    setFormData(prev => ({
      ...prev,
      gstin: upper,
      pan: extractedPan || prev.pan
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setErrorMsg('Customer name is required');
      return;
    }
    if (formData.gstin && !isValidGSTIN(formData.gstin)) {
      setErrorMsg('Please enter a valid 15-digit Indian GSTIN format');
      return;
    }

    const aliasArray = formData.aliases
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);

    onSave({
      customerId: formData.customerId,
      name: formData.name.trim(),
      legalName: formData.legalName.trim() || formData.name.trim(),
      pan: formData.pan.trim().toUpperCase(),
      gstin: formData.gstin.trim().toUpperCase(),
      customerType: formData.customerType as any,
      state: formData.state,
      address: formData.address,
      contactPerson: formData.contactPerson,
      email: formData.email,
      phone: formData.phone,
      paymentTerms: Number(formData.paymentTerms),
      creditLimit: Number(formData.creditLimit),
      tdsApplicable: formData.tdsApplicable,
      tdsSection: formData.tdsSection,
      tdsRate: Number(formData.tdsRate),
      openingBalance: Number(formData.openingBalance),
      status: formData.status as any,
      notes: formData.notes,
      aliases: aliasArray
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-sm">
            {existingCustomer ? 'Edit Customer' : 'Add New Customer Master'}
          </h3>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 overflow-y-auto space-y-4 text-xs">
          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg">
              {errorMsg}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Customer Name *</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={e => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g. ABC Technologies Pvt Ltd"
                className="w-full p-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Legal Entity Name</label>
              <input
                type="text"
                value={formData.legalName}
                onChange={e => setFormData({ ...formData, legalName: e.target.value })}
                placeholder="Official registered company name"
                className="w-full p-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">GSTIN (15 Digits)</label>
              <input
                type="text"
                value={formData.gstin}
                onChange={e => handleGstinChange(e.target.value)}
                placeholder="27AAACA1234B1Z2"
                className="w-full p-2 font-mono uppercase rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">PAN (10 Digits)</label>
              <input
                type="text"
                value={formData.pan}
                onChange={e => setFormData({ ...formData, pan: e.target.value.toUpperCase() })}
                placeholder="AAACA1234B"
                className="w-full p-2 font-mono uppercase rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">State</label>
              <input
                type="text"
                value={formData.state}
                onChange={e => setFormData({ ...formData, state: e.target.value })}
                className="w-full p-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Payment Terms (Days)</label>
              <input
                type="number"
                value={formData.paymentTerms}
                onChange={e => setFormData({ ...formData, paymentTerms: parseInt(e.target.value, 10) || 30 })}
                className="w-full p-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Credit Limit (₹)</label>
              <input
                type="number"
                value={formData.creditLimit}
                onChange={e => setFormData({ ...formData, creditLimit: parseFloat(e.target.value) || 0 })}
                className="w-full p-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Contact Person</label>
              <input
                type="text"
                value={formData.contactPerson}
                onChange={e => setFormData({ ...formData, contactPerson: e.target.value })}
                placeholder="e.g. Sunil Deshmukh"
                className="w-full p-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={e => setFormData({ ...formData, email: e.target.value })}
                placeholder="accounts@client.com"
                className="w-full p-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Phone</label>
              <input
                type="text"
                value={formData.phone}
                onChange={e => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+91 98200 00000"
                className="w-full p-2 rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
              />
            </div>
          </div>

          {/* TDS Setup */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="tdsApplicable"
                checked={formData.tdsApplicable}
                onChange={e => setFormData({ ...formData, tdsApplicable: e.target.checked })}
                className="rounded text-emerald-600 focus:ring-emerald-500"
              />
              <label htmlFor="tdsApplicable" className="font-semibold text-slate-800">
                Customer Deducts TDS on Invoices
              </label>
            </div>

            {formData.tdsApplicable && (
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-[11px] font-medium text-slate-600 block mb-1">TDS Section</label>
                  <select
                    value={formData.tdsSection}
                    onChange={e => {
                      const sec = e.target.value;
                      const rate = sec === '194C' ? 2 : sec === '194J' ? 10 : sec === '194Q' ? 0.1 : 2;
                      setFormData({ ...formData, tdsSection: sec, tdsRate: rate });
                    }}
                    className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                  >
                    <option value="194C">194C (Contractor / Works - 2%)</option>
                    <option value="194J">194J (Professional / Tech - 10%)</option>
                    <option value="194Q">194Q (Purchase of Goods - 0.1%)</option>
                    <option value="194I">194I (Rent / Plant - 10%)</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-600 block mb-1">Default Rate (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.tdsRate}
                    onChange={e => setFormData({ ...formData, tdsRate: parseFloat(e.target.value) || 0 })}
                    className="w-full p-2 rounded-lg border border-slate-200 bg-white"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Narration Aliases */}
          <div>
            <label className="font-semibold text-slate-700 block mb-1">
              Bank Narration Aliases (comma separated)
            </label>
            <input
              type="text"
              value={formData.aliases}
              onChange={e => setFormData({ ...formData, aliases: e.target.value })}
              placeholder="e.g. ABC PVT LTD, ABC LTD, ABC TECH"
              className="w-full p-2 font-mono text-xs rounded-lg border border-slate-200 focus:outline-hidden focus:border-emerald-600"
            />
            <span className="text-[10px] text-slate-400 mt-0.5 block">
              Used by deterministic narration parser to match bank deposits automatically.
            </span>
          </div>

          <div className="pt-3 border-t border-slate-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg shadow-xs"
            >
              {existingCustomer ? 'Save Changes' : 'Create Customer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
