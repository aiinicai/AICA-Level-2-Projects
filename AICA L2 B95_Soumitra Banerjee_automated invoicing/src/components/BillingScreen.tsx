import React, { useState } from 'react';
import { 
  Calculator, 
  Mail, 
  Send, 
  CheckCircle2, 
  Clock, 
  FileText, 
  CheckCheck,
  RefreshCw,
  AlertCircle,
  ExternalLink
} from 'lucide-react';
import { BillingClientSummary } from '../types';
import { systemService } from '../lib/services/systemService';

interface BillingScreenProps {
  quarter: string;
  financialYear: string;
  onQuarterChange: (q: string) => void;
  onFyChange: (fy: string) => void;
  billingData: {
    summaries: BillingClientSummary[];
    totalFiles: number;
    totalBilling: number;
  };
  loading: boolean;
  onRecalculate: () => void;
  onNavigateToConfirmations: () => void;
  onNavigateToEmails: () => void;
}

export const BillingScreen: React.FC<BillingScreenProps> = ({
  quarter,
  financialYear,
  onQuarterChange,
  onFyChange,
  billingData,
  loading,
  onRecalculate,
  onNavigateToConfirmations,
  onNavigateToEmails,
}) => {
  const [sendingEmails, setSendingEmails] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const quarterMonths: Record<string, string[]> = {
    Q1: ['April', 'May', 'June'],
    Q2: ['July', 'August', 'September'],
    Q3: ['October', 'November', 'December'],
    Q4: ['January', 'February', 'March'],
  };

  const months = quarterMonths[quarter] || ['Month 1', 'Month 2', 'Month 3'];

  const pendingClients = billingData.summaries.filter(
    (s) => s.status === 'PENDING_CONFIRMATION' && s.totalFileCount > 0
  );

  const handleSendAllConfirmations = async () => {
    if (pendingClients.length === 0) {
      setErrorMsg('No pending billing records to send confirmation emails to.');
      return;
    }

    setSendingEmails(true);
    setSuccessMsg('');
    setErrorMsg('');

    try {
      const results = [];
      for (const s of pendingClients) {
        if (s.billingId) {
          results.push(await systemService.sendConfirmationEmail(s.billingId));
          // A short gap between sends looks like normal human-paced outbound
          // mail rather than a burst, which providers weigh when deciding
          // spam vs inbox placement for a batch of similar-looking emails.
          if (pendingClients.length > 1) {
            await new Promise((resolve) => setTimeout(resolve, 600));
          }
        }
      }

      const failed = results.filter((r) => r.status === 'FAILED').length;
      const simulated = results.filter((r) => r.status === 'SIMULATED').length;

      if (failed > 0) {
        setErrorMsg(
          `${failed} of ${results.length} confirmation email(s) failed to send (mail server unreachable or SMTP misconfigured). Check Email Preview / Outbox for details.`
        );
      } else if (simulated > 0) {
        setSuccessMsg(
          `Generated and simulated ${results.length} quarterly confirmation email(s) (Demo Mode is on). Check Email Preview.`
        );
      } else {
        setSuccessMsg(
          `Successfully sent quarterly confirmation emails to ${results.length} client(s)! Check Email Preview.`
        );
      }
      onRecalculate();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to send confirmation emails.');
    } finally {
      setSendingEmails(false);
    }
  };

  const handleSendSingleConfirmation = async (billingId: string | null, clientName: string) => {
    if (!billingId) return;
    setSendingEmails(true);
    setSuccessMsg('');
    setErrorMsg('');

    try {
      const res = await systemService.sendConfirmationEmail(billingId);
      if (res.status === 'FAILED') {
        setErrorMsg(`Confirmation email to ${clientName} could not be sent. Check the mail server / SMTP settings.`);
      } else if (res.status === 'SIMULATED') {
        setSuccessMsg(`Confirmation email simulated for ${clientName} (Demo Mode is on).`);
      } else {
        setSuccessMsg(`Confirmation email sent to ${clientName}!`);
      }
      onRecalculate();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to send confirmation email.');
    } finally {
      setSendingEmails(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PENDING_CONFIRMATION':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3 h-3 mr-1" /> Pending Confirmation
          </span>
        );
      case 'CONFIRMED':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-teal-50 text-teal-700 border border-teal-200">
            <CheckCircle2 className="w-3 h-3 mr-1" /> Confirmed
          </span>
        );
      case 'INVOICE_GENERATED':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <FileText className="w-3 h-3 mr-1" /> Invoice Generated
          </span>
        );
      case 'INVOICE_SENT':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Send className="w-3 h-3 mr-1" /> Invoice Sent
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            Rejected
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Quarterly Billing Calculation</h1>
          <p className="text-sm text-slate-500">
            Aggregated delivery logs per client with custom rates, GST, and email dispatch.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-white border border-slate-300 rounded-lg p-1 text-sm shadow-xs">
            <span className="text-xs font-medium text-slate-500 pl-2">FY:</span>
            <select
              value={financialYear}
              onChange={(e) => onFyChange(e.target.value)}
              className="py-1 px-2 border-0 bg-transparent text-sm font-semibold text-slate-800 focus:ring-0"
            >
              <option value="2026-27">2026-27</option>
              <option value="2025-26">2025-26</option>
              <option value="2027-28">2027-28</option>
            </select>

            <div className="w-px h-5 bg-slate-200" />

            <span className="text-xs font-medium text-slate-500 pl-1">Quarter:</span>
            <select
              value={quarter}
              onChange={(e) => onQuarterChange(e.target.value)}
              className="py-1 px-2 border-0 bg-transparent text-sm font-semibold text-slate-800 focus:ring-0"
            >
              <option value="Q1">Q1 (Apr - Jun)</option>
              <option value="Q2">Q2 (Jul - Sep)</option>
              <option value="Q3">Q3 (Oct - Dec)</option>
              <option value="Q4">Q4 (Jan - Mar)</option>
            </select>
          </div>

          <button
            onClick={onRecalculate}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-xs transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Recalculate Billing</span>
          </button>

          <button
            onClick={handleSendAllConfirmations}
            disabled={sendingEmails || pendingClients.length === 0}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition disabled:opacity-50"
          >
            <Mail className="w-4 h-4" />
            <span>Send Confirmation Emails ({pendingClients.length})</span>
          </button>
        </div>
      </div>

      {/* Messages */}
      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <CheckCheck className="w-5 h-5 text-emerald-600 shrink-0" />
            <span className="font-medium">{successMsg}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onNavigateToEmails}
              className="px-3 py-1 bg-white border border-emerald-300 text-emerald-800 hover:bg-emerald-50 rounded-lg text-xs font-semibold transition"
            >
              View Email Outbox
            </button>
            <button
              onClick={onNavigateToConfirmations}
              className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition"
            >
              Simulate Client Confirmation →
            </button>
          </div>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl flex items-center gap-3 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span className="font-medium">{errorMsg}</span>
        </div>
      )}

      {/* Summary KPI Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Quarterly File Volume</span>
          <div className="text-2xl font-bold text-slate-900 mt-1 font-mono">
            {billingData.totalFiles.toLocaleString('en-IN')} <span className="text-xs text-slate-500 font-sans">files</span>
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Gross Billing Amount (incl. 18% GST)</span>
          <div className="text-2xl font-bold text-blue-700 mt-1 font-mono">
            ₹{billingData.totalBilling.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Action Required</span>
          <div className="text-2xl font-bold text-amber-600 mt-1 flex items-center justify-between">
            <span>{pendingClients.length} Pending</span>
            {pendingClients.length > 0 && (
              <button
                onClick={handleSendAllConfirmations}
                className="text-xs font-semibold text-blue-600 hover:underline"
              >
                Send Batch Emails
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Billing Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold uppercase text-slate-600 tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Client</th>
                <th className="py-3.5 px-3 text-right">{months[0]?.slice(0, 3)}</th>
                <th className="py-3.5 px-3 text-right">{months[1]?.slice(0, 3)}</th>
                <th className="py-3.5 px-3 text-right">{months[2]?.slice(0, 3)}</th>
                <th className="py-3.5 px-3 text-right bg-slate-100/50">Total Files</th>
                <th className="py-3.5 px-3 text-right">Rate</th>
                <th className="py-3.5 px-3 text-right">Subtotal</th>
                <th className="py-3.5 px-3 text-right">Tax (18%)</th>
                <th className="py-3.5 px-4 text-right bg-blue-50/50 text-blue-900 font-bold">Total Amount</th>
                <th className="py-3.5 px-4 text-center">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={11} className="py-12 text-center text-slate-400">
                    Calculating quarterly billing...
                  </td>
                </tr>
              ) : billingData.summaries.length === 0 ? (
                <tr>
                  <td colSpan={11} className="py-12 text-center text-slate-400">
                    No delivery records found for {quarter} FY {financialYear}. Please upload an Excel delivery log.
                  </td>
                </tr>
              ) : (
                billingData.summaries.map((row, idx) => {
                  const m1Count = row.months[months[0]] || 0;
                  const m2Count = row.months[months[1]] || 0;
                  const m3Count = row.months[months[2]] || 0;

                  return (
                    <tr key={idx} className="hover:bg-slate-50/80 transition">
                      <td className="py-3.5 px-4">
                        <span className="font-semibold text-slate-900 block">{row.clientName}</span>
                        <span className="font-mono text-xs text-blue-600 font-medium">{row.clientCode}</span>
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono text-xs">
                        {m1Count ? m1Count.toLocaleString('en-IN') : '—'}
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono text-xs">
                        {m2Count ? m2Count.toLocaleString('en-IN') : '—'}
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono text-xs">
                        {m3Count ? m3Count.toLocaleString('en-IN') : '—'}
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono font-bold text-slate-900 bg-slate-50/50">
                        {row.totalFileCount.toLocaleString('en-IN')}
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono text-xs">
                        ₹{row.ratePerFile}
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono text-xs">
                        ₹{row.subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3.5 px-3 text-right font-mono text-xs text-slate-500">
                        ₹{row.tax.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-bold text-blue-900 bg-blue-50/40">
                        ₹{row.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {getStatusBadge(row.status)}
                      </td>
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        {row.status === 'PENDING_CONFIRMATION' && (
                          <button
                            onClick={() => handleSendSingleConfirmation(row.billingId, row.clientName)}
                            disabled={sendingEmails}
                            className="px-2.5 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-md text-xs font-medium transition inline-flex items-center gap-1"
                          >
                            <Mail className="w-3.5 h-3.5" />
                            <span>Send Email</span>
                          </button>
                        )}
                        {row.status === 'CONFIRMED' && (
                          <span className="text-xs text-teal-700 font-medium">Ready for Invoice</span>
                        )}
                        {(row.status === 'INVOICE_GENERATED' || row.status === 'INVOICE_SENT') && (
                          <button
                            onClick={onNavigateToConfirmations}
                            className="text-xs text-blue-600 hover:underline inline-flex items-center gap-1 font-medium"
                          >
                            <span>View Flow</span>
                            <ExternalLink className="w-3 h-3" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
