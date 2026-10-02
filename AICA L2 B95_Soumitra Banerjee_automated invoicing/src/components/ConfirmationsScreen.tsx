import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  CheckCircle2,
  Clock,
  FileText,
  Download,
  Sparkles,
  AlertCircle,
  Search,
  Send,
  BellRing
} from 'lucide-react';
import { ConfirmationItem } from '../types';
import { systemService } from '../lib/services/systemService';

interface ConfirmationsScreenProps {
  confirmations: ConfirmationItem[];
  loading: boolean;
  onRefresh: () => void;
  onNavigateToInvoices: () => void;
  onNavigateToAudit: () => void;
}

export const ConfirmationsScreen: React.FC<ConfirmationsScreenProps> = ({
  confirmations,
  loading,
  onRefresh,
  onNavigateToInvoices,
  onNavigateToAudit,
}) => {
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [successInfo, setSuccessInfo] = useState<{
    clientName: string;
    invoiceNumber: string;
  } | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [checkingReplies, setCheckingReplies] = useState(false);
  const [replyCheckNote, setReplyCheckNote] = useState('');
  const [resendingId, setResendingId] = useState<string | null>(null);
  const [resendNote, setResendNote] = useState('');
  const [sendingReminders, setSendingReminders] = useState(false);
  const [reminderNote, setReminderNote] = useState('');
  const checkInFlight = useRef(false);

  const handleCheckReplies = useCallback(async (silent = false) => {
    if (checkInFlight.current) return;
    checkInFlight.current = true;
    if (!silent) setCheckingReplies(true);

    try {
      const result = await systemService.checkForReplies();
      if (!result.checked) {
        if (!silent) setReplyCheckNote(result.reason || 'Could not check the inbox right now.');
        return;
      }
      const total = result.confirmedClients.length + result.rejectedClients.length;
      if (total > 0) {
        onRefresh();
        setReplyCheckNote(
          `Detected ${result.confirmedClients.length} confirmation(s) and ${result.rejectedClients.length} rejection(s) from real email replies.`
        );
      } else if (!silent) {
        setReplyCheckNote('No new CONFIRMED/REJECTED replies found in the inbox.');
      }
    } finally {
      checkInFlight.current = false;
      if (!silent) setCheckingReplies(false);
    }
  }, [onRefresh]);

  // Poll for real email replies every 25s while this screen is open (only
  // does anything when Demo Mode is off - checkForReplies no-ops otherwise).
  useEffect(() => {
    const interval = setInterval(() => {
      handleCheckReplies(true);
    }, 25000);
    return () => clearInterval(interval);
  }, [handleCheckReplies]);

  // Automated follow-up reminders (every "Reminder Interval" days, Settings
  // screen, default 5) already run app-wide in App.tsx regardless of which
  // tab is open. This button is just a manual, on-demand trigger for the
  // same check - handy for testing without waiting on the real interval, or
  // for firing a reminder wave right before ending a work session.
  const handleSendReminders = async (silent = false) => {
    if (!silent) setSendingReminders(true);
    try {
      const result = await systemService.checkAndSendReminders();
      if (result.sentClients.length > 0) {
        onRefresh();
        setReminderNote(`Sent reminder email(s) to: ${result.sentClients.join(', ')}.`);
      } else if (!silent) {
        setReminderNote('No clients are currently overdue for a reminder.');
      }
    } finally {
      if (!silent) setSendingReminders(false);
    }
  };

  const handleSimulateConfirmation = async (billingId: string, clientName: string) => {
    setProcessingId(billingId);
    setErrorMsg('');
    setSuccessInfo(null);

    try {
      const res = await systemService.simulateConfirmation(billingId);
      setSuccessInfo({
        clientName,
        invoiceNumber: res.invoiceNumber,
      });
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to simulate confirmation.');
    } finally {
      setProcessingId(null);
    }
  };

  const handleResendInvoice = async (billingId: string, clientName: string) => {
    setResendingId(billingId);
    setResendNote('');
    setErrorMsg('');

    try {
      const res = await systemService.resendInvoiceEmail(billingId);
      setResendNote(
        res.status === 'SENT'
          ? `Invoice ${res.invoiceNumber} was re-sent to ${clientName} with the PDF attached.`
          : res.status === 'SIMULATED'
          ? `Invoice ${res.invoiceNumber} resend was simulated (Demo Mode is on) for ${clientName}.`
          : `Invoice ${res.invoiceNumber} resend to ${clientName} failed. Check the mail server / SMTP settings.`
      );
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to resend invoice email.');
    } finally {
      setResendingId(null);
    }
  };

  const handleReject = (billingId: string) => {
    const reason = window.prompt('Please enter rejection reason:', 'File count mismatch reported by client');
    if (!reason) return;

    setProcessingId(billingId);
    setErrorMsg('');
    try {
      systemService.rejectConfirmation(billingId, reason);
      onRefresh();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to reject billing.');
    } finally {
      setProcessingId(null);
    }
  };

  const pendingConfirmations = confirmations.filter(
    (c) => c.status === 'PENDING_CONFIRMATION'
  );

  const completedConfirmations = confirmations.filter(
    (c) => c.status !== 'PENDING_CONFIRMATION'
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Client Confirmations &amp; Automation</h1>
          <p className="text-sm text-slate-500">
            Real client email replies (Demo Mode off) are auto-detected every 25s, or use the manual Simulate button.
            Clients still awaiting confirmation get an automatic reminder email every few days.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => handleSendReminders(false)}
            disabled={sendingReminders}
            title="Manually check for, and send, any overdue confirmation reminders right now"
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-xs transition disabled:opacity-50"
          >
            <BellRing className="w-3.5 h-3.5" />
            <span>{sendingReminders ? 'Sending Reminders...' : 'Send Reminders Now'}</span>
          </button>
          <button
            onClick={() => handleCheckReplies(false)}
            disabled={checkingReplies}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-xs transition disabled:opacity-50"
          >
            <Search className="w-3.5 h-3.5" />
            <span>{checkingReplies ? 'Checking Inbox...' : 'Check for Replies Now'}</span>
          </button>
        </div>
      </div>

      {reminderNote && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg text-xs font-medium flex items-center justify-between gap-3">
          <span>{reminderNote}</span>
          <button onClick={() => setReminderNote('')} className="text-amber-400 hover:text-amber-700 shrink-0">✕</button>
        </div>
      )}

      {replyCheckNote && (
        <div className="p-3 bg-blue-50 border border-blue-200 text-blue-800 rounded-lg text-xs font-medium flex items-center justify-between gap-3">
          <span>{replyCheckNote}</span>
          <button onClick={() => setReplyCheckNote('')} className="text-blue-400 hover:text-blue-700 shrink-0">✕</button>
        </div>
      )}

      {resendNote && (
        <div className="p-3 bg-indigo-50 border border-indigo-200 text-indigo-800 rounded-lg text-xs font-medium flex items-center justify-between gap-3">
          <span>{resendNote}</span>
          <button onClick={() => setResendNote('')} className="text-indigo-400 hover:text-indigo-700 shrink-0">✕</button>
        </div>
      )}

      {/* Instant Success Banner */}
      {successInfo && (
        <div className="p-5 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-xl space-y-3 shadow-xs">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <h3 className="text-base font-bold">
                Workflow Automation Succeeded for {successInfo.clientName}!
              </h3>
            </div>
            <span className="text-xs font-semibold bg-emerald-200/60 text-emerald-900 px-2 py-0.5 rounded">
              Status: INVOICE_SENT
            </span>
          </div>
          <p className="text-xs text-emerald-800 leading-relaxed">
            The client confirmation was recorded, tax invoice{' '}
            <strong className="font-mono font-bold text-emerald-950">{successInfo.invoiceNumber}</strong> was generated as PDF, 
            and the dispatch email was archived in Email Logs.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button
              onClick={onNavigateToInvoices}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-semibold shadow-xs transition"
            >
              <FileText className="w-4 h-4" />
              <span>View &amp; Download Invoice PDF</span>
            </button>
            <button
              onClick={onNavigateToAudit}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-emerald-300 text-emerald-900 hover:bg-emerald-100 rounded-lg text-xs font-semibold transition"
            >
              <span>View Audit Trail →</span>
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

      {/* Awaiting Confirmation Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Clock className="w-4 h-4 text-amber-500" />
            <span>Awaiting Client Confirmation ({pendingConfirmations.length})</span>
          </h2>
          <span className="text-xs text-slate-500">
            Click &ldquo;Simulate Client Confirmation&rdquo; to demonstrate immediate downstream flow.
          </span>
        </div>

        {pendingConfirmations.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-8 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
            <h4 className="text-sm font-semibold text-slate-800">No Pending Confirmations</h4>
            <p className="text-xs text-slate-500">
              All calculated quarterly billing cycles have been confirmed or invoiced.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pendingConfirmations.map((item) => (
              <div
                key={item.id}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs hover:border-blue-300 transition space-y-4"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="font-mono text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                      {item.clientCode}
                    </span>
                    <h3 className="text-base font-bold text-slate-900 mt-1">{item.clientName}</h3>
                    <p className="text-xs text-slate-500">{item.clientEmail}</p>
                  </div>
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    <Clock className="w-3 h-3 mr-1" /> Awaiting Confirmation
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 p-3 bg-slate-50 rounded-lg text-xs">
                  <div>
                    <span className="text-slate-500 block">Period</span>
                    <strong className="text-slate-800 font-semibold">{item.quarter} FY {item.financialYear}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Total Files</span>
                    <strong className="text-slate-800 font-mono font-semibold">{item.totalFileCount.toLocaleString('en-IN')}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Total Amount</span>
                    <strong className="text-blue-900 font-mono font-bold">
                      ₹{item.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </strong>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    onClick={() => handleReject(item.id)}
                    disabled={processingId === item.id}
                    className="px-3 py-1.5 border border-slate-200 hover:bg-slate-100 text-slate-600 rounded-lg text-xs font-semibold transition"
                  >
                    Reject
                  </button>
                  <button
                    onClick={() => handleSimulateConfirmation(item.id, item.clientName)}
                    disabled={processingId === item.id}
                    className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-blue-200" />
                    <span>{processingId === item.id ? 'Processing...' : 'Simulate Client Confirmation'}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Completed Confirmations & Invoiced Section */}
      <div className="space-y-4 pt-4 border-t border-slate-200">
        <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <FileText className="w-4 h-4 text-emerald-600" />
          <span>Processed Billing &amp; Automated Invoices ({completedConfirmations.length})</span>
        </h2>

        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold uppercase text-slate-600 tracking-wider">
                <tr>
                  <th className="py-3 px-4">Client</th>
                  <th className="py-3 px-4">Quarter</th>
                  <th className="py-3 px-4 text-right">Total Files</th>
                  <th className="py-3 px-4 text-right">Total Amount</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4">Invoice Generated</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {completedConfirmations.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">
                      No processed confirmations yet. Click simulate confirmation above to see live result.
                    </td>
                  </tr>
                ) : (
                  completedConfirmations.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50 transition">
                      <td className="py-3 px-4 font-semibold text-slate-900">
                        {item.clientName}
                        <span className="font-mono text-xs text-slate-400 block">{item.clientCode}</span>
                      </td>
                      <td className="py-3 px-4 text-xs font-mono">{item.quarter} FY {item.financialYear}</td>
                      <td className="py-3 px-4 text-right font-mono font-medium">{item.totalFileCount.toLocaleString('en-IN')}</td>
                      <td className="py-3 px-4 text-right font-mono font-bold text-blue-900">
                        ₹{item.totalAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 mr-1" /> {item.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-xs font-bold text-slate-800">
                        {item.invoiceNumber || 'Generated'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-3">
                          <button
                            onClick={onNavigateToInvoices}
                            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 font-semibold"
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>PDF</span>
                          </button>
                          {item.status === 'INVOICE_SENT' && (
                            <button
                              onClick={() => handleResendInvoice(item.id, item.clientName)}
                              disabled={resendingId === item.id}
                              className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-semibold disabled:opacity-50"
                              title="Re-send the invoice email with the PDF attached"
                            >
                              <Send className="w-3.5 h-3.5" />
                              <span>{resendingId === item.id ? 'Sending...' : 'Resend Invoice'}</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
