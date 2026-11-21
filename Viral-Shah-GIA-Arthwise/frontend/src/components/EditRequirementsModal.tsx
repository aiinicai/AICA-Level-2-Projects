import React, { useState } from 'react';
import { Sliders, X, Check, Building, AlertCircle } from 'lucide-react';
import { Proposal, ProductType } from '../types';
import { NumberInput } from './NumberInput';
import { formatINR, NumberUnitMode } from '../utils/formatters';
import { ApiClient } from '../api/client';

interface EditRequirementsModalProps {
  proposal: Proposal;
  borrowerName: string;
  onClose: () => void;
  onSuccess: () => void;
  unitMode: NumberUnitMode;
}

export const EditRequirementsModal: React.FC<EditRequirementsModalProps> = ({
  proposal,
  borrowerName,
  onClose,
  onSuccess,
  unitMode,
}) => {
  const [productType, setProductType] = useState<ProductType>(proposal.product_type);
  const [requestedAmount, setRequestedAmount] = useState<number>(Number(proposal.requested_amount));
  const [tenureMonths, setTenureMonths] = useState<number>(proposal.tenure_months);
  const [targetRate, setTargetRate] = useState<number>(proposal.target_rate || 9.25);
  const [purpose, setPurpose] = useState<string>(proposal.purpose || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      await ApiClient.request(`/proposals/${proposal.id}/requirements`, {
        method: 'PATCH',
        body: JSON.stringify({
          product_type: productType,
          requested_amount: requestedAmount,
          tenure_months: tenureMonths,
          target_rate: targetRate,
          purpose: purpose.trim() || undefined,
        }),
      });

      alert(`Loan requirements for ${proposal.proposal_code} updated successfully!`);
      onSuccess();
      onClose();
    } catch (err: any) {
      console.error('Failed to update loan requirements:', err);
      setErrorMsg(err.message || 'Error updating loan requirements');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in my-8">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-[#faece7] text-[#a45139] rounded-lg">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Modify Loan Requirements</h3>
              <p className="text-xs text-slate-500 font-mono">
                Case ID: <span className="font-bold text-[#1b2632]">{proposal.proposal_code}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="my-3 p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center gap-2.5 text-xs text-slate-700">
          <Building className="w-4 h-4 text-slate-400 flex-shrink-0" />
          <div>
            <span className="text-slate-500">Borrower:</span>{' '}
            <strong className="text-slate-800">{borrowerName}</strong>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Facility / Loan Product
            </label>
            <select
              value={productType}
              onChange={(e) => setProductType(e.target.value as ProductType)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#a45139]"
              required
            >
              <option value="cash_credit_od">Cash Credit / Overdraft (CC/OD)</option>
              <option value="working_capital">Working Capital Term Facility</option>
              <option value="home_loan">Home Loan (Purchase / Construction)</option>
              <option value="lap">Loan Against Property (LAP)</option>
              <option value="business_loan_secured">Secured Business Loan</option>
              <option value="business_loan_unsecured">Unsecured Business Loan</option>
              <option value="project_finance_term_loan">Project Finance & Term Loan</option>
              <option value="balance_transfer_topup">Balance Transfer & Top-up</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block font-semibold text-slate-700">Requested Loan (INR ₹)</label>
                <span className="text-[10px] text-slate-400 font-mono">
                  {formatINR(requestedAmount, unitMode)}
                </span>
              </div>
              <NumberInput
                value={requestedAmount}
                onChange={setRequestedAmount}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#a45139]"
                required
                min={100000}
                step={50000}
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Tenure (Months)</label>
              <NumberInput
                value={tenureMonths}
                onChange={setTenureMonths}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#a45139]"
                required
                min={1}
                max={360}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Target Rate (% p.a.)</label>
              <NumberInput
                value={targetRate}
                onChange={setTargetRate}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#a45139]"
                step={0.05}
                min={1}
                max={36}
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Facility Purpose</label>
              <input
                type="text"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="e.g. Working capital against debtors"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-[#a45139]"
              />
            </div>
          </div>

          <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-semibold transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 bg-[#a45139] hover:bg-[#863e2a] text-white rounded-lg font-semibold shadow-sm transition-all flex items-center gap-1.5"
            >
              <Check className="w-4 h-4" />
              <span>{isSubmitting ? 'Saving Changes...' : 'Update Requirements'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
