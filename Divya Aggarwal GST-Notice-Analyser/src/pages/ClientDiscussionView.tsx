import React, { useState, useEffect } from 'react';
import { Client, NoticeCase } from '../types';
import { MessageSquare, Plus, Trash2, CheckCircle2, Clock, ChevronDown, ChevronUp, Send } from 'lucide-react';
import { DiscussionEntry, loadDiscussionsForCase, saveDiscussion, deleteDiscussion } from '../services/discussions';

interface ClientDiscussionViewProps {
  activeClient: Client | null;
  activeCase: NoticeCase | null;
}

export const ClientDiscussionView: React.FC<ClientDiscussionViewProps> = ({
  activeClient,
  activeCase,
}) => {
  const [discussions, setDiscussions] = useState<DiscussionEntry[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [form, setForm] = useState<Omit<DiscussionEntry, 'id' | 'createdAt'>>({
    caseId: activeCase?.id || '',
    date: new Date().toISOString().split('T')[0],
    mode: 'Call',
    topic: '',
    notes: '',
    questionsAsked: '',
    clientResponse: '',
    actionItems: '',
    followUpDate: '',
    status: 'Open',
  });

  useEffect(() => {
    const caseId = activeCase?.id || '';
    setForm((f) => ({ ...f, caseId }));
    if (caseId && !caseId.startsWith('temp_')) {
      loadDiscussionsForCase(caseId).then(setDiscussions).catch(() => setDiscussions([]));
    } else {
      setDiscussions([]);
    }
  }, [activeCase]);

  const caseDiss = discussions;

  const handleAdd = async () => {
    if (!form.topic.trim()) return;
    const entry: DiscussionEntry = {
      ...form,
      id: `disc_${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    setDiscussions((d) => [entry, ...d]);
    setShowForm(false);
    setForm({
      caseId: activeCase?.id || '',
      date: new Date().toISOString().split('T')[0],
      mode: 'Call',
      topic: '', notes: '', questionsAsked: '', clientResponse: '',
      actionItems: '', followUpDate: '', status: 'Open',
    });
    try { await saveDiscussion(entry); } catch (e: any) { alert(e.message); }
  };

  const handleDelete = async (id: string) => {
    setDiscussions((d) => d.filter((x) => x.id !== id));
    try { await deleteDiscussion(id); } catch (e: any) { alert(e.message); }
  };

  const handleStatusToggle = async (id: string) => {
    let toSave: DiscussionEntry | undefined;
    setDiscussions((d) => d.map((x) => {
      if (x.id !== id) return x;
      toSave = { ...x, status: x.status === 'Resolved' ? 'Open' : 'Resolved' };
      return toSave;
    }));
    if (toSave) { try { await saveDiscussion(toSave); } catch (e: any) { alert(e.message); } }
  };

  const statusColor = (s: DiscussionEntry['status']) => {
    if (s === 'Resolved') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    if (s === 'Pending Follow-up') return 'bg-amber-100 text-amber-700 border-amber-200';
    return 'bg-blue-100 text-blue-700 border-blue-200';
  };

  const modeColor = (m: DiscussionEntry['mode']) => {
    const map: Record<string, string> = {
      Call: 'bg-indigo-100 text-indigo-700',
      Meeting: 'bg-indigo-100 text-indigo-700',
      Email: 'bg-sky-100 text-sky-700',
      WhatsApp: 'bg-emerald-100 text-emerald-700',
      'In-Person': 'bg-rose-100 text-rose-700',
    };
    return map[m] || 'bg-gray-100 text-gray-700';
  };

  if (!activeCase) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
        <MessageSquare className="w-12 h-12 opacity-30" />
        <div className="text-sm font-semibold">No active notice case selected</div>
        <div className="text-xs text-gray-400">Select or upload a notice to track client discussions</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-[#F8FAFC] overflow-hidden">
      <div className="px-6 py-4 bg-white border-b border-gray-200 flex items-center justify-between shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-[#4338CA]" />
            <span className="text-sm font-bold text-gray-900">Client Discussion Log</span>
            <span className="text-xs px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full font-bold">
              {caseDiss.length} Entries
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-0.5">
            {activeClient?.legalName} · Notice {activeCase.noticeNumber} · {activeCase.formType}
          </div>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 px-4 py-2 bg-[#4338CA] hover:bg-[#3730A3] text-white text-xs font-bold rounded-xl transition-all shadow-sm cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          Log Discussion
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {showForm && (
          <div className="bg-white rounded-2xl border border-[#E0E7FF] shadow-sm p-5 space-y-4">
            <div className="text-xs font-bold text-[#4338CA] uppercase tracking-wider border-b border-gray-100 pb-2">
              New Discussion Entry
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-gray-600 mb-1">Date</label>
                <input
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA]"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-gray-600 mb-1">Mode</label>
                <select
                  value={form.mode}
                  onChange={(e) => setForm({ ...form, mode: e.target.value as any })}
                  className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA] bg-white"
                >
                  {['Call', 'Meeting', 'Email', 'WhatsApp', 'In-Person'].map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-gray-600 mb-1">Status</label>
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value as any })}
                  className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA] bg-white"
                >
                  {['Open', 'Resolved', 'Pending Follow-up'].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-gray-600 mb-1">Topic / Subject *</label>
              <input
                type="text"
                value={form.topic}
                onChange={(e) => setForm({ ...form, topic: e.target.value })}
                placeholder="e.g. Discussed ITC mismatch issue - client to provide vendor invoices"
                className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-gray-600 mb-1">Questions Asked to Client</label>
                <textarea
                  rows={3}
                  value={form.questionsAsked}
                  onChange={(e) => setForm({ ...form, questionsAsked: e.target.value })}
                  placeholder="1. Do you have the physical invoices?&#10;2. Were payments made within 180 days?"
                  className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA] resize-none font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-gray-600 mb-1">Client Response / Explanation</label>
                <textarea
                  rows={3}
                  value={form.clientResponse}
                  onChange={(e) => setForm({ ...form, clientResponse: e.target.value })}
                  placeholder="Client confirmed invoices available..."
                  className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA] resize-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-gray-600 mb-1">Discussion Notes / Summary</label>
              <textarea
                rows={3}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Detailed notes from the discussion..."
                className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA] resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-gray-600 mb-1">Action Items / Pending Tasks</label>
                <textarea
                  rows={2}
                  value={form.actionItems}
                  onChange={(e) => setForm({ ...form, actionItems: e.target.value })}
                  placeholder="1. Client to send GSTR-2B for Q1&#10;2. CA to prepare reconciliation"
                  className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA] resize-none font-mono"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-gray-600 mb-1">Follow-up Date</label>
                <input
                  type="date"
                  value={form.followUpDate}
                  onChange={(e) => setForm({ ...form, followUpDate: e.target.value })}
                  className="w-full px-3 py-1.5 text-xs border border-gray-300 rounded-lg focus:outline-none focus:border-[#4338CA]"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={!form.topic.trim()}
                className="flex items-center gap-1.5 px-5 py-1.5 bg-[#4338CA] hover:bg-[#3730A3] disabled:opacity-40 text-white text-xs font-bold rounded-lg transition-colors cursor-pointer"
              >
                <Send className="w-3 h-3" />
                Save Discussion
              </button>
            </div>
          </div>
        )}

        {caseDiss.length === 0 && !showForm && (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
            <MessageSquare className="w-10 h-10 opacity-30" />
            <div className="text-sm font-semibold text-gray-500">No discussions logged yet</div>
            <div className="text-xs text-gray-400">Click "Log Discussion" to record your first client conversation</div>
          </div>
        )}

        {caseDiss.map((d) => (
          <div key={d.id} className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
            <div
              className="flex items-center justify-between px-5 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => setExpandedId(expandedId === d.id ? null : d.id)}
            >
              <div className="flex items-center gap-3">
                <div className="text-xs text-gray-500 font-mono shrink-0">{d.date}</div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${modeColor(d.mode)}`}>
                  {d.mode}
                </span>
                <span className="text-xs font-bold text-gray-900 truncate max-w-xs">{d.topic}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`text-[10px] px-2 py-0.5 rounded-full border font-bold ${statusColor(d.status)}`}>
                  {d.status}
                </span>
                {d.followUpDate && (
                  <span className="text-[10px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 font-medium flex items-center gap-1">
                    <Clock className="w-2.5 h-2.5" />
                    Follow-up: {d.followUpDate}
                  </span>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); handleStatusToggle(d.id); }}
                  className="p-1 hover:bg-emerald-50 rounded text-gray-400 hover:text-emerald-600 cursor-pointer"
                  title="Toggle Resolved"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(d.id); }}
                  className="p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-600 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
                {expandedId === d.id ? (
                  <ChevronUp className="w-3.5 h-3.5 text-gray-400" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
                )}
              </div>
            </div>

            {expandedId === d.id && (
              <div className="px-5 pb-4 border-t border-gray-100 text-xs space-y-3 pt-3">
                {d.questionsAsked && (
                  <div>
                    <div className="font-bold text-gray-700 mb-1 uppercase text-[10px] tracking-wider">Questions Asked</div>
                    <div className="bg-indigo-50 rounded-lg p-3 text-gray-800 font-mono whitespace-pre-wrap border border-indigo-100">{d.questionsAsked}</div>
                  </div>
                )}
                {d.clientResponse && (
                  <div>
                    <div className="font-bold text-gray-700 mb-1 uppercase text-[10px] tracking-wider">Client Response</div>
                    <div className="bg-emerald-50 rounded-lg p-3 text-gray-800 whitespace-pre-wrap border border-emerald-100">{d.clientResponse}</div>
                  </div>
                )}
                {d.notes && (
                  <div>
                    <div className="font-bold text-gray-700 mb-1 uppercase text-[10px] tracking-wider">Discussion Notes</div>
                    <div className="bg-gray-50 rounded-lg p-3 text-gray-700 whitespace-pre-wrap border border-gray-200">{d.notes}</div>
                  </div>
                )}
                {d.actionItems && (
                  <div>
                    <div className="font-bold text-gray-700 mb-1 uppercase text-[10px] tracking-wider">Action Items</div>
                    <div className="bg-amber-50 rounded-lg p-3 text-gray-800 font-mono whitespace-pre-wrap border border-amber-100">{d.actionItems}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
