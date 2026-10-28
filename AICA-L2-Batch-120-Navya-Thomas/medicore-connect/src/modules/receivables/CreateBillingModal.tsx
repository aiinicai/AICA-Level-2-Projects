import React, { useState } from 'react';
import { X, Plus, Trash2, AlertCircle, Receipt } from 'lucide-react';
import { getDb, updateDb, addAuditLog } from '../../core/storage';
import { getActiveUser } from '../../core/auth';
import { getNextSequenceNumber, peekNextSequenceNumber } from '../../core/sequences';
import { ARTransaction, ARTransactionLine } from '../../core/types';
import { BUSINESS_UNITS } from '../../data/businessUnits';
import { round2, addMoney, subMoney, formatAED } from '../../core/currency';
import { DEMO_TODAY } from '../../core/dates';

interface CreateBillingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (ar: ARTransaction) => void;
}

export const CreateBillingModal: React.FC<CreateBillingModalProps> = ({
  isOpen,
  onClose,
  onCreated,
}) => {
  const db = getDb();
  const currentUser = getActiveUser();

  const [businessUnit, setBusinessUnit] = useState('H01');
  const [customerId, setCustomerId] = useState(db.customers[0]?.id || '');
  const [patientName, setPatientName] = useState('Rashid Al Mansoori');
  const [claimReference, setClaimReference] = useState(`CLM-DMN-${Date.now().toString().slice(-6)}`);
  const [visitDate, setVisitDate] = useState(DEMO_TODAY);
  const [transactionDate, setTransactionDate] = useState(DEMO_TODAY);
  const [dueDate, setDueDate] = useState('2026-11-20');
  const [description, setDescription] = useState('Specialist Clinical Consultation & Diagnostic Imaging');
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const [lines, setLines] = useState<ARTransactionLine[]>([
    {
      lineNumber: 1,
      serviceCategory: 'Outpatient Specialist Consultation',
      description: 'Consultant Cardiologist Examination & Echocardiography',
      revenueAccount: '4010',
      amount: 1850,
      taxCode: 'ZERO_0',
      taxAmount: 0,
      insuranceDiscountAmount: 277.5, // 15% insurer discount
      patientCoPayAmount: 150,
    },
    {
      lineNumber: 2,
      serviceCategory: 'Laboratory & Radiology',
      description: 'Comprehensive Metabolic Panel & Lipid Profile',
      revenueAccount: '4030',
      amount: 650,
      taxCode: 'ZERO_0',
      taxAmount: 0,
      insuranceDiscountAmount: 97.5,
      patientCoPayAmount: 50,
    },
  ]);

  if (!isOpen) return null;

  const currentCustomer = db.customers.find((c) => c.id === customerId);
  const nextSeq = peekNextSequenceNumber('RINV', 2026);

  const handleAddLine = () => {
    setLines([
      ...lines,
      {
        lineNumber: lines.length + 1,
        serviceCategory: 'Clinical Services',
        description: 'Procedure and medical supplies',
        revenueAccount: '4010',
        amount: 500,
        taxCode: 'ZERO_0',
        taxAmount: 0,
        insuranceDiscountAmount: 0,
        patientCoPayAmount: 0,
      },
    ]);
  };

  const handleRemoveLine = (idx: number) => {
    if (lines.length <= 1) return;
    const upd = [...lines];
    upd.splice(idx, 1);
    setLines(upd.map((l, i) => ({ ...l, lineNumber: i + 1 })));
  };

  const updateLine = (idx: number, field: keyof ARTransactionLine, val: any) => {
    const upd = [...lines];
    upd[idx] = { ...upd[idx], [field]: val };
    setLines(upd);
  };

  // Compute totals
  let grossSubtotal = 0;
  let totalDiscount = 0;
  let totalTax = 0;

  lines.forEach((l) => {
    grossSubtotal = addMoney(grossSubtotal, l.amount);
    totalDiscount = addMoney(totalDiscount, l.insuranceDiscountAmount);
    totalTax = addMoney(totalTax, l.taxAmount);
  });

  const netReceivable = addMoney(subMoney(grossSubtotal, totalDiscount), totalTax);

  const handleSubmit = (statusToSet: 'Draft' | 'Pending Approval') => {
    if (grossSubtotal <= 0) {
      setErrorBanner('Transaction lines must have a valid billing amount.');
      return;
    }

    const assignedSeq = getNextSequenceNumber('RINV', 2026);
    const newTxn: ARTransaction = {
      id: `AR-INV-${Date.now()}`,
      number: assignedSeq,
      businessUnit,
      transactionClass: 'Invoice',
      customerId,
      customerName: currentCustomer?.name || 'Customer',
      customerType: currentCustomer?.type || 'Insurance',
      patientName,
      claimReference,
      visitDate,
      transactionDate,
      glDate: transactionDate,
      dueDate,
      description,
      lines,
      subtotal: grossSubtotal,
      discountAmount: totalDiscount,
      taxAmount: totalTax,
      totalAmount: netReceivable,
      paidAmount: 0,
      status: statusToSet,
      createdBy: currentUser.userId,
      createdAt: new Date().toISOString(),
    };

    updateDb((state) => {
      state.arTransactions.unshift(newTxn);
    });

    addAuditLog({
      entityType: 'ARTransaction',
      entityId: newTxn.id,
      action: statusToSet === 'Pending Approval' ? 'SUBMIT' : 'CREATE',
      userId: currentUser.userId,
      userName: currentUser.name,
      comments: `Created AR billing claim ${newTxn.number} (${statusToSet})`,
    });

    onCreated(newTxn);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs" onClick={onClose} />

      <div className="relative bg-white rounded-xl shadow-2xl border border-gray-200 w-full max-w-5xl max-h-[92vh] flex flex-col z-10 animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="bg-[#3F1D5C] text-white px-6 py-4 rounded-t-xl flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <Receipt className="w-5 h-5 text-amber-300" />
            <div>
              <h2 className="font-bold text-base">Create Receivables Transaction / Claim</h2>
              <p className="text-xs text-plum-200">
                Assigned Sequence: <strong className="font-mono text-amber-300">{nextSeq}</strong> | Currency: AED
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-[#5B2C83] text-gray-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {errorBanner && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-300 text-rose-800 rounded-lg text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorBanner}</span>
            </div>
          )}

          {/* Header Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-5 p-4 bg-gray-50 rounded-lg border border-gray-200 text-xs">
            <div>
              <label className="block font-semibold text-gray-700 mb-1">Business Unit</label>
              <select
                value={businessUnit}
                onChange={(e) => setBusinessUnit(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              >
                {BUSINESS_UNITS.map((b) => (
                  <option key={b.code} value={b.code}>
                    {b.code} - {b.name.replace('Meridian ', '')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Customer / Insurer</label>
              <select
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              >
                {db.customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Patient Name</label>
              <input
                type="text"
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Claim / Prior Auth Ref</label>
              <input
                type="text"
                value={claimReference}
                onChange={(e) => setClaimReference(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium focus:ring-1 focus:ring-[#5B2C83]"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Visit Date</label>
              <input
                type="date"
                value={visitDate}
                onChange={(e) => setVisitDate(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Transaction Date</label>
              <input
                type="date"
                value={transactionDate}
                onChange={(e) => setTransactionDate(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Payment Due Date</label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Header Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full p-2 bg-white border border-gray-300 rounded font-medium"
              />
            </div>
          </div>

          {/* Lines Table */}
          <div className="border border-gray-200 rounded-lg overflow-hidden mb-4">
            <table className="w-full text-xs text-left">
              <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider border-b border-plum-200">
                <tr>
                  <th className="py-2.5 px-3 w-8 text-center">#</th>
                  <th className="py-2.5 px-3 w-48">Service Category</th>
                  <th className="py-2.5 px-3">Description</th>
                  <th className="py-2.5 px-3 w-28 text-right">Gross Price</th>
                  <th className="py-2.5 px-3 w-28 text-right">Ins. Discount</th>
                  <th className="py-2.5 px-3 w-28 font-mono">Revenue Acct</th>
                  <th className="py-2.5 px-2 w-8 text-center"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {lines.map((l, idx) => (
                  <tr key={idx} className="hover:bg-plum-50/20">
                    <td className="py-2 px-3 text-center text-gray-400 font-semibold">{idx + 1}</td>
                    <td className="py-2 px-2">
                      <select
                        value={l.serviceCategory}
                        onChange={(e) => updateLine(idx, 'serviceCategory', e.target.value)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs"
                      >
                        <option value="Outpatient Specialist Consultation">Outpatient Consultation</option>
                        <option value="Inpatient Clinical Services">Inpatient Clinical Care</option>
                        <option value="Surgery and Procedures">Surgery and Operating Theatre</option>
                        <option value="Laboratory & Radiology">Laboratory & Diagnostic Imaging</option>
                        <option value="Pharmacy Sales">Pharmacy Prescriptions</option>
                      </select>
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={l.description}
                        onChange={(e) => updateLine(idx, 'description', e.target.value)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="0.01"
                        value={l.amount}
                        onChange={(e) => updateLine(idx, 'amount', parseFloat(e.target.value) || 0)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs text-right font-mono"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="0.01"
                        value={l.insuranceDiscountAmount}
                        onChange={(e) => updateLine(idx, 'insuranceDiscountAmount', parseFloat(e.target.value) || 0)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs text-right font-mono"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <select
                        value={l.revenueAccount}
                        onChange={(e) => updateLine(idx, 'revenueAccount', e.target.value)}
                        className="w-full p-1.5 border border-gray-300 rounded text-xs font-mono"
                      >
                        <option value="4000">4000 - Inpatient</option>
                        <option value="4010">4010 - Outpatient</option>
                        <option value="4020">4020 - Surgery</option>
                        <option value="4030">4030 - Lab & Rad</option>
                        <option value="4040">4040 - Pharmacy</option>
                      </select>
                    </td>
                    <td className="py-2 px-2 text-center">
                      <button
                        type="button"
                        onClick={() => handleRemoveLine(idx)}
                        className="p-1 text-gray-400 hover:text-rose-600 rounded"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mb-4">
            <button
              type="button"
              onClick={handleAddLine}
              className="px-3 py-1.5 rounded bg-gray-100 hover:bg-gray-200 text-gray-800 text-xs font-semibold flex items-center space-x-1"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Service Line</span>
            </button>

            {/* Totals */}
            <div className="bg-plum-50/60 border border-plum-200 rounded-lg p-3 text-xs w-72 space-y-1">
              <div className="flex justify-between text-gray-600">
                <span>Gross Tariff Subtotal:</span>
                <span className="font-mono">{formatAED(grossSubtotal)}</span>
              </div>
              <div className="flex justify-between text-rose-700">
                <span>Contractual Discounts (4090):</span>
                <span className="font-mono">-{formatAED(totalDiscount)}</span>
              </div>
              <div className="flex justify-between font-bold text-gray-900 border-t border-plum-200 pt-1 text-sm">
                <span>Net Receivable (AED):</span>
                <span className="font-mono text-[#5B2C83]">{formatAED(netReceivable)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-3 rounded-b-xl border-t border-gray-200 flex items-center justify-between">
          <div className="text-[11px] text-gray-500">
            Maker: <strong>{currentUser.name}</strong> ({currentUser.role})
          </div>
          <div className="flex space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => handleSubmit('Draft')}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg text-xs font-semibold"
            >
              Save as Draft
            </button>
            <button
              type="button"
              onClick={() => handleSubmit('Pending Approval')}
              className="px-5 py-2 bg-[#5B2C83] hover:bg-[#3F1D5C] text-white rounded-lg text-xs font-semibold shadow-xs"
            >
              Submit for Approval &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
