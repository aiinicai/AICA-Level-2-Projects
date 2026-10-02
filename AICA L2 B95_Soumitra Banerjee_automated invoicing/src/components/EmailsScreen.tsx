import React, { useState } from 'react';
import { 
  Mail, 
  Send, 
  CheckCircle2, 
  Paperclip, 
  Clock, 
  FileText, 
  Eye, 
  Sparkles,
  Inbox,
  X
} from 'lucide-react';
import { EmailLogItem } from '../types';
import { systemService } from '../lib/services/systemService';

interface EmailsScreenProps {
  emails: EmailLogItem[];
  loading: boolean;
  onRefresh: () => void;
  onSimulateReply: (billingId: string, clientName: string) => void;
}

export const EmailsScreen: React.FC<EmailsScreenProps> = ({
  emails,
  loading,
  onRefresh,
  onSimulateReply,
}) => {
  const [selectedEmail, setSelectedEmail] = useState<EmailLogItem | null>(null);
  const [filterType, setFilterType] = useState<'ALL' | 'CONFIRMATION' | 'REMINDER' | 'INVOICE'>('ALL');

  const filteredEmails = emails.filter((e) => {
    if (filterType === 'ALL') return true;
    return e.type === filterType;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Email Outbox &amp; Preview</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              Demo Mode Active
            </span>
          </div>
          <p className="text-sm text-slate-500">
            View simulated or SMTP-dispatched quarterly confirmation requests and generated tax invoice emails.
          </p>
        </div>

        {/* Filter Badges */}
        <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-xs font-medium">
          <button
            onClick={() => setFilterType('ALL')}
            className={`px-3 py-1.5 rounded-md transition ${filterType === 'ALL' ? 'bg-white shadow-xs text-blue-600 font-semibold' : 'text-slate-600'}`}
          >
            All Emails ({emails.length})
          </button>
          <button
            onClick={() => setFilterType('CONFIRMATION')}
            className={`px-3 py-1.5 rounded-md transition ${filterType === 'CONFIRMATION' ? 'bg-white shadow-xs text-blue-600 font-semibold' : 'text-slate-600'}`}
          >
            Confirmations ({emails.filter((e) => e.type === 'CONFIRMATION').length})
          </button>
          <button
            onClick={() => setFilterType('REMINDER')}
            className={`px-3 py-1.5 rounded-md transition ${filterType === 'REMINDER' ? 'bg-white shadow-xs text-blue-600 font-semibold' : 'text-slate-600'}`}
          >
            Reminders ({emails.filter((e) => e.type === 'REMINDER').length})
          </button>
          <button
            onClick={() => setFilterType('INVOICE')}
            className={`px-3 py-1.5 rounded-md transition ${filterType === 'INVOICE' ? 'bg-white shadow-xs text-blue-600 font-semibold' : 'text-slate-600'}`}
          >
            Invoices ({emails.filter((e) => e.type === 'INVOICE').length})
          </button>
        </div>
      </div>

      {/* Main Two-Pane View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Email List Left Column */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs divide-y divide-slate-100">
          <div className="p-3.5 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider flex justify-between items-center">
            <span>Sent Messages ({filteredEmails.length})</span>
            <button onClick={onRefresh} className="text-blue-600 hover:underline">
              Refresh
            </button>
          </div>

          <div className="max-h-[600px] overflow-y-auto divide-y divide-slate-100">
            {loading ? (
              <div className="p-8 text-center text-xs text-slate-400">Loading email logs...</div>
            ) : filteredEmails.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400 space-y-1">
                <Inbox className="w-8 h-8 text-slate-300 mx-auto" />
                <p>No email logs found yet.</p>
                <p className="text-[11px]">Send a confirmation email from Billing to populate.</p>
              </div>
            ) : (
              filteredEmails.map((email) => {
                const isSelected = selectedEmail?.id === email.id;
                return (
                  <div
                    key={email.id}
                    onClick={() => setSelectedEmail(email)}
                    className={`p-4 cursor-pointer transition text-xs space-y-2 ${
                      isSelected ? 'bg-blue-50/80 border-l-4 border-blue-600' : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                          email.type === 'CONFIRMATION'
                            ? 'bg-amber-100 text-amber-800'
                            : email.type === 'REMINDER'
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {email.type}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(email.sentAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} •{' '}
                        {new Date(email.sentAt).toLocaleDateString()}
                      </span>
                    </div>

                    <div>
                      <h4 className="font-bold text-slate-900 line-clamp-1">{email.subject}</h4>
                      <p className="text-slate-500 font-mono text-[11px] truncate mt-0.5">To: {email.recipient}</p>
                    </div>

                    <p className="text-slate-600 line-clamp-2 text-[11px] font-sans">
                      {email.body.slice(0, 120)}...
                    </p>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Email Detail Right Column */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
          {selectedEmail ? (
            <div className="p-6 space-y-6">
              {/* Email Header */}
              <div className="border-b border-slate-100 pb-5 space-y-3">
                <div className="flex items-start justify-between">
                  <h2 className="text-lg font-bold text-slate-900 leading-snug">
                    {selectedEmail.subject}
                  </h2>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      selectedEmail.status === 'SIMULATED'
                        ? 'bg-blue-100 text-blue-800 border border-blue-200'
                        : selectedEmail.status === 'FAILED'
                        ? 'bg-red-100 text-red-800 border border-red-200'
                        : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}
                  >
                    Status: {selectedEmail.status}
                  </span>
                </div>

                <div className="text-xs space-y-1 bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-600 font-mono">
                  <div className="flex">
                    <span className="w-16 font-semibold text-slate-400">To:</span>
                    <span className="text-slate-900 font-bold">{selectedEmail.recipient}</span>
                  </div>
                  <div className="flex">
                    <span className="w-16 font-semibold text-slate-400">From:</span>
                    <span>Finance Team &lt;{systemService.getSettings().senderEmail}&gt;</span>
                  </div>
                  <div className="flex">
                    <span className="w-16 font-semibold text-slate-400">Timestamp:</span>
                    <span>{new Date(selectedEmail.sentAt).toLocaleString()}</span>
                  </div>
                </div>

                {(selectedEmail.type === 'CONFIRMATION' || selectedEmail.type === 'REMINDER') && selectedEmail.billingId && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 text-amber-800">
                      <Sparkles className="w-4 h-4 text-amber-600" />
                      <span>Ready to test client confirmation reply?</span>
                    </div>
                    <button
                      onClick={() => {
                        onSimulateReply(selectedEmail.billingId!, selectedEmail.clientName || 'Client');
                      }}
                      className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded font-semibold transition"
                    >
                      Simulate Client Reply &ldquo;CONFIRMED&rdquo;
                    </button>
                  </div>
                )}
              </div>

              {/* Email Body */}
              <div className="bg-slate-50/50 p-5 rounded-xl border border-slate-100">
                <pre className="font-sans whitespace-pre-wrap text-sm text-slate-800 leading-relaxed font-normal">
                  {selectedEmail.body}
                </pre>
              </div>

              {selectedEmail.type === 'INVOICE' && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3 text-xs text-blue-900">
                  <Paperclip className="w-4 h-4 text-blue-600" />
                  <span className="font-semibold">Attachment: Tax Invoice PDF attached with dispatch email.</span>
                </div>
              )}
            </div>
          ) : (
            <div className="p-16 text-center text-slate-400 space-y-2">
              <Mail className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="font-semibold text-slate-700 text-sm">Select an email to view full details</h3>
              <p className="text-xs">
                Shows exact subject line, body template, calculations, and recipient.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
