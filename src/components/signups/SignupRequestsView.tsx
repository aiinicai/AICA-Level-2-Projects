import React, { useState } from 'react';
import {
  UserCheck,
  UserX,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Mail,
  Building2,
  Search,
  Filter,
  ShieldAlert,
  Send,
  ExternalLink,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { SignupRequest, EmailNotificationLog, UserRole, Client } from '../../types';
import { StorageService } from '../../services/storage';

export const SignupRequestsView: React.FC = () => {
  const storage = StorageService.getInstance();
  const currentCompany = storage.getCompanyProfile();
  const currentUser = storage.getCurrentUser();
  const clients = storage.getClients();

  const [requests, setRequests] = useState<SignupRequest[]>(storage.getSignupRequests());
  const [emailLogs, setEmailLogs] = useState<EmailNotificationLog[]>(storage.getEmailLogs());
  const [activeTab, setActiveTab] = useState<'requests' | 'email_logs'>('requests');
  const [filterStatus, setFilterStatus] = useState<'all' | 'pending' | 'approved' | 'rejected'>('pending');
  const [searchQuery, setSearchQuery] = useState('');

  const [selectedReq, setSelectedReq] = useState<SignupRequest | null>(null);
  const [linkedClientId, setLinkedClientId] = useState<string>('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);

  const reloadData = () => {
    setRequests(storage.getSignupRequests());
    setEmailLogs(storage.getEmailLogs());
  };

  const handleApprove = (req: SignupRequest) => {
    let clientToLink = linkedClientId;
    if (req.requestedRole === 'client_portal' && !clientToLink) {
      // Check if matching client exists
      const match = clients.find((c) => c.name.toLowerCase().includes(req.linkedClientName?.toLowerCase() || ''));
      if (match) clientToLink = match.id;
    }

    storage.approveSignupRequest(req.id, currentUser.id, clientToLink || undefined);
    reloadData();
    setSelectedReq(null);
    setLinkedClientId('');
  };

  const handleReject = () => {
    if (!selectedReq) return;
    storage.rejectSignupRequest(selectedReq.id, currentUser.id, rejectionReason);
    reloadData();
    setIsRejectModalOpen(false);
    setSelectedReq(null);
    setRejectionReason('');
  };

  const filteredRequests = requests.filter((r) => {
    if (filterStatus !== 'all' && r.status !== filterStatus) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        r.name.toLowerCase().includes(q) ||
        r.email.toLowerCase().includes(q) ||
        r.requestedRole.toLowerCase().includes(q) ||
        (r.linkedClientName && r.linkedClientName.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const pendingCount = requests.filter((r) => r.status === 'pending').length;

  return (
    <div id="signup-requests-screen" className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-blue-600 font-semibold text-xs mb-1">
            <ShieldAlert className="w-4 h-4" />
            <span>Administrator Security Gatekeeper</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            User Access & Client Portal Approvals
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Review incoming staff authorization and client portal access requests for <span className="font-semibold text-slate-800">{currentCompany.name}</span> (Code: <span className="font-mono font-bold text-blue-700">{currentCompany.companyCode}</span>).
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="px-4 py-2 bg-amber-50 border border-amber-200 rounded-xl flex items-center space-x-2">
            <Clock className="w-4 h-4 text-amber-600" />
            <div>
              <p className="text-[10px] text-amber-700 font-semibold uppercase">Pending Actions</p>
              <p className="text-sm font-bold text-amber-900">{pendingCount} Requests</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 bg-white rounded-t-xl px-4">
        <button
          onClick={() => setActiveTab('requests')}
          className={`py-3 px-4 text-xs font-bold border-b-2 flex items-center space-x-2 transition ${
            activeTab === 'requests'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Access Requests ({requests.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('email_logs')}
          className={`py-3 px-4 text-xs font-bold border-b-2 flex items-center space-x-2 transition ${
            activeTab === 'email_logs'
              ? 'border-blue-600 text-blue-700'
              : 'border-transparent text-slate-600 hover:text-slate-900'
          }`}
        >
          <Mail className="w-4 h-4" />
          <span>Simulated Email Notification Queue ({emailLogs.length})</span>
        </button>
      </div>

      {activeTab === 'requests' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center space-x-2 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by name, email, role..."
                  className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                />
              </div>

              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="px-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white font-medium text-slate-700 focus:outline-hidden"
              >
                <option value="all">All Statuses</option>
                <option value="pending">Pending Only</option>
                <option value="approved">Approved Only</option>
                <option value="rejected">Rejected Only</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            {filteredRequests.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-xs">
                <CheckCircle2 className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                <p className="font-semibold text-slate-600">No requests found</p>
                <p>All incoming authorization sign-ups have been resolved.</p>
              </div>
            ) : (
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Applicant</th>
                    <th className="py-3 px-4">Requested Role</th>
                    <th className="py-3 px-4">Company / Department</th>
                    <th className="py-3 px-4">Date Submitted</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredRequests.map((req) => {
                    const isPending = req.status === 'pending';
                    const isClient = req.requestedRole === 'client_portal';

                    return (
                      <tr key={req.id} className="hover:bg-slate-50/80 transition">
                        <td className="py-3.5 px-4">
                          <div className="font-bold text-slate-900">{req.name}</div>
                          <div className="text-[11px] text-slate-500 font-mono">{req.email}</div>
                          {req.mobile && <div className="text-[10px] text-slate-400">{req.mobile}</div>}
                        </td>

                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              isClient
                                ? 'bg-purple-100 text-purple-800'
                                : req.requestedRole === 'finance'
                                ? 'bg-emerald-100 text-emerald-800'
                                : req.requestedRole === 'procurement'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-blue-100 text-blue-800'
                            }`}
                          >
                            {isClient ? 'Client Portal' : req.requestedRole}
                          </span>
                        </td>

                        <td className="py-3.5 px-4 text-slate-600">
                          {isClient ? (
                            <div>
                              <p className="font-semibold text-slate-800">{req.linkedClientName || 'External Contractor'}</p>
                              <p className="text-[10px] text-slate-400">Client Portal User</p>
                            </div>
                          ) : (
                            <div>
                              <p className="font-semibold text-slate-800">Internal Staff</p>
                              <p className="text-[10px] text-slate-400">{currentCompany.name}</p>
                            </div>
                          )}
                          {req.notes && (
                            <p className="text-[10px] text-slate-500 italic mt-0.5 max-w-xs truncate">
                              "{req.notes}"
                            </p>
                          )}
                        </td>

                        <td className="py-3.5 px-4 text-slate-500">
                          {new Date(req.createdAt).toLocaleDateString('en-GB', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>

                        <td className="py-3.5 px-4">
                          {req.status === 'pending' && (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                              <Clock className="w-3 h-3" />
                              <span>Pending Review</span>
                            </span>
                          )}
                          {req.status === 'approved' && (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              <CheckCircle2 className="w-3 h-3" />
                              <span>Approved</span>
                            </span>
                          )}
                          {req.status === 'rejected' && (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800">
                              <XCircle className="w-3 h-3" />
                              <span>Rejected</span>
                            </span>
                          )}
                        </td>

                        <td className="py-3.5 px-4 text-right space-x-2">
                          {isPending ? (
                            <div className="flex items-center justify-end space-x-2">
                              {isClient && (
                                <select
                                  value={linkedClientId}
                                  onChange={(e) => setLinkedClientId(e.target.value)}
                                  className="text-[11px] py-1 px-2 border border-slate-300 rounded-lg bg-white"
                                >
                                  <option value="">-- Link to CRM Client --</option>
                                  {clients.map((c) => (
                                    <option key={c.id} value={c.id}>
                                      {c.name}
                                    </option>
                                  ))}
                                </select>
                              )}
                              <button
                                onClick={() => handleApprove(req)}
                                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-[11px] shadow-xs flex items-center space-x-1 transition"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                <span>Approve</span>
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedReq(req);
                                  setIsRejectModalOpen(true);
                                }}
                                className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg font-bold text-[11px] transition"
                              >
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span className="text-[11px] text-slate-400 italic">Resolved</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {activeTab === 'email_logs' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="text-xs font-bold text-slate-800">
                Simulated Transactional Outbound Email Queue
              </h3>
              <p className="text-[11px] text-slate-500">
                Shows all real-time notifications dispatched to administrators and applicants upon sign-up submissions, approvals, and rejections.
              </p>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            {emailLogs.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">No email dispatches recorded.</div>
            ) : (
              emailLogs.map((log) => (
                <div key={log.id} className="p-4 hover:bg-slate-50/60 transition space-y-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="w-7 h-7 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center">
                        <Mail className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-900">{log.subject}</p>
                        <p className="text-[10px] text-slate-500 font-mono">
                          To: {log.recipientName} &lt;{log.recipientEmail}&gt;
                        </p>
                      </div>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {new Date(log.sentAt).toLocaleTimeString('en-GB')}
                    </span>
                  </div>
                  <pre className="p-3 bg-slate-900 text-slate-200 rounded-lg text-[11px] font-mono whitespace-pre-wrap">
                    {log.bodyText}
                  </pre>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {isRejectModalOpen && selectedReq && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl border border-slate-200 space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <XCircle className="w-5 h-5 text-rose-600" />
              <span>Decline Sign-up Request ({selectedReq.name})</span>
            </h3>
            <p className="text-xs text-slate-600">
              Provide a brief explanation for declining this request. A simulated transactional notification will be dispatched to {selectedReq.email}.
            </p>
            <textarea
              rows={3}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="e.g., Unverified tax identification or unauthorized email domain."
              className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-rose-500 focus:outline-hidden"
            />
            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => {
                  setIsRejectModalOpen(false);
                  setSelectedReq(null);
                }}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                className="px-4 py-2 text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white rounded-lg shadow-sm transition"
              >
                Confirm Decline
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
