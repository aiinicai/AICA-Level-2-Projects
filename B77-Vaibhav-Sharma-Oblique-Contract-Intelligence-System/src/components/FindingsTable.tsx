import React, { useState, useMemo } from 'react';
import { 
  Search, 
  Filter, 
  AlertCircle, 
  AlertTriangle, 
  Info, 
  CheckCircle2, 
  HelpCircle, 
  ShieldAlert, 
  X, 
  ExternalLink, 
  MessageSquare, 
  Check, 
  Clock, 
  CornerDownRight,
  FileText,
  UserCheck,
  Send,
  Sparkles,
  ChevronDown
} from 'lucide-react';
import { Finding, AttentionLevel, FindingStatus, AnalysisDomain, CAComment } from '../types/contract';

interface FindingsTableProps {
  findings: Finding[];
  selectedFinding: Finding | null;
  onSelectFinding: (finding: Finding | null) => void;
  onUpdateFindingStatus: (findingId: string, status: FindingStatus, comment?: string) => void;
  onAddComment: (findingId: string, commentText: string) => void;
  onJumpToViewer: (finding: Finding) => void;
}

export const FindingsTable: React.FC<FindingsTableProps> = ({
  findings,
  selectedFinding,
  onSelectFinding,
  onUpdateFindingStatus,
  onAddComment,
  onJumpToViewer
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedDomain, setSelectedDomain] = useState<string>('All');
  const [selectedAttention, setSelectedAttention] = useState<string>('All');
  const [selectedStatus, setSelectedStatus] = useState<string>('All');
  const [newCommentText, setNewCommentText] = useState<string>('');

  const domainsList = [
    'All',
    'Accounting',
    'GST',
    'TDS',
    'MSME',
    'Related Party',
    'Audit',
    'Financial Reporting',
    'Working Capital',
    'Internal Control'
  ];

  const filteredFindings = useMemo(() => {
    return findings.filter(f => {
      // Domain filter
      if (selectedDomain !== 'All' && !f.domains.includes(selectedDomain as AnalysisDomain)) {
        return false;
      }
      // Attention filter
      if (selectedAttention !== 'All' && f.attention !== selectedAttention) {
        return false;
      }
      // Status filter
      if (selectedStatus !== 'All' && f.status !== selectedStatus) {
        return false;
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = f.title.toLowerCase().includes(q);
        const matchesWhy = f.whyItMatters.toLowerCase().includes(q);
        const matchesClause = f.source.extractedText.toLowerCase().includes(q);
        const matchesId = f.id.toLowerCase().includes(q);
        if (!matchesTitle && !matchesWhy && !matchesClause && !matchesId) {
          return false;
        }
      }
      return true;
    });
  }, [findings, selectedDomain, selectedAttention, selectedStatus, searchQuery]);

  const handleCommentSubmit = (findingId: string) => {
    if (!newCommentText.trim()) return;
    onAddComment(findingId, newCommentText.trim());
    setNewCommentText('');
  };

  return (
    <div className="space-y-4">
      {/* Top Filter Bento Card */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-base font-bold text-gray-900 tracking-tight">Professional Findings Matrix</h1>
            <p className="text-xs text-gray-500">
              Clauses classified into Indian accounting, GST, TDS, MSME, and compliance impact.
            </p>
          </div>

          {/* Search box */}
          <div className="relative w-full sm:w-72">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search findings, clauses, or why..."
              className="w-full pl-8 pr-3 py-2 text-xs rounded-md border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Filters Row */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-gray-100 text-xs">
          {/* Attention Level Filter */}
          <div className="flex items-center space-x-1">
            <span className="font-semibold text-gray-600 mr-1 text-[11px] uppercase tracking-wider">Attention:</span>
            {['All', 'RED', 'AMBER', 'BLUE'].map(att => (
              <button
                key={att}
                onClick={() => setSelectedAttention(att)}
                className={`px-2.5 py-1 rounded text-xs font-semibold transition cursor-pointer ${
                  selectedAttention === att
                    ? att === 'RED'
                      ? 'bg-red-600 text-white'
                      : att === 'AMBER'
                      ? 'bg-orange-500 text-white'
                      : att === 'BLUE'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {att === 'All' ? 'All' : att}
              </button>
            ))}
          </div>

          <div className="h-4 w-px bg-gray-200 hidden sm:block" />

          {/* Domain Filter */}
          <div className="flex items-center space-x-1.5">
            <span className="font-semibold text-gray-600 text-[11px] uppercase tracking-wider">Domain:</span>
            <select
              value={selectedDomain}
              onChange={(e) => setSelectedDomain(e.target.value)}
              className="py-1 px-2 rounded border border-gray-300 bg-white text-gray-700 font-medium text-xs cursor-pointer"
            >
              {domainsList.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div className="h-4 w-px bg-gray-200 hidden sm:block" />

          {/* Status Filter */}
          <div className="flex items-center space-x-1.5">
            <span className="font-semibold text-gray-600 text-[11px] uppercase tracking-wider">CA Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="py-1 px-2 rounded border border-gray-300 bg-white text-gray-700 font-medium text-xs cursor-pointer"
            >
              <option value="All">All Statuses</option>
              <option value="New">New</option>
              <option value="Under Review">Under Review</option>
              <option value="Cleared">Cleared</option>
              <option value="Requires Information">Requires Information</option>
              <option value="Escalated">Escalated</option>
            </select>
          </div>

          <span className="ml-auto text-gray-400 font-mono text-[11px]">
            Showing {filteredFindings.length} of {findings.length} findings
          </span>
        </div>
      </div>

      {/* Main Table Bento Grid Card */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 font-bold uppercase tracking-widest text-[10px]">
              <tr>
                <th className="py-3 px-5 w-16">#</th>
                <th className="py-3 px-5">Finding & Core Issue</th>
                <th className="py-3 px-5">Domain</th>
                <th className="py-3 px-5 w-28">Attention</th>
                <th className="py-3 px-5 w-28">Source Ref</th>
                <th className="py-3 px-5 w-28">CA Status</th>
                <th className="py-3 px-5 text-right w-24">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredFindings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400">
                    No findings match the selected filters.
                  </td>
                </tr>
              ) : (
                filteredFindings.map((finding) => (
                  <tr 
                    key={finding.id}
                    onClick={() => onSelectFinding(finding)}
                    className={`hover:bg-gray-50 cursor-pointer transition ${
                      selectedFinding?.id === finding.id ? 'bg-blue-50/60 font-medium' : ''
                    }`}
                  >
                    {/* ID */}
                    <td className="py-3.5 px-5 font-mono font-bold text-gray-700">
                      {finding.id}
                    </td>

                    {/* Title & Why It Matters */}
                    <td className="py-3.5 px-5 max-w-md">
                      <div className="space-y-1">
                        <span className="font-bold text-gray-900 block text-xs">
                          {finding.title}
                        </span>
                        <p className="text-gray-500 line-clamp-1 text-[11px] leading-relaxed">
                          {finding.whyItMatters}
                        </p>
                      </div>
                    </td>

                    {/* Domains */}
                    <td className="py-3.5 px-5">
                      <div className="flex flex-wrap gap-1">
                        {finding.domains.map(d => (
                          <span key={d} className="px-1.5 py-0.2 rounded text-[10px] bg-gray-100 text-gray-700 font-medium border border-gray-200">
                            {d}
                          </span>
                        ))}
                      </div>
                    </td>

                    {/* Attention */}
                    <td className="py-3.5 px-5">
                      <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold inline-flex items-center space-x-1 ${
                        finding.attention === 'RED' ? 'bg-red-100 text-red-700' :
                        finding.attention === 'AMBER' ? 'bg-orange-100 text-orange-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        <span>{finding.attention}</span>
                      </span>
                    </td>

                    {/* Source */}
                    <td className="py-3.5 px-5 font-mono text-[11px] text-gray-500">
                      Pg {finding.source.page}, Cl {finding.source.clause}
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        finding.status === 'Cleared' ? 'bg-emerald-100 text-emerald-800' :
                        finding.status === 'Under Review' ? 'bg-blue-100 text-blue-800' :
                        finding.status === 'Escalated' ? 'bg-red-100 text-red-800 font-bold' :
                        finding.status === 'Requires Information' ? 'bg-orange-100 text-orange-800' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {finding.status}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="py-3.5 px-5 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectFinding(finding);
                        }}
                        className="px-2.5 py-1 rounded text-xs font-semibold bg-gray-100 hover:bg-gray-200 text-gray-800 border border-gray-300 transition"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slide-over Detail Inspector Drawer */}
      {selectedFinding && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-gray-950/50 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-2xl bg-white h-full shadow-2xl overflow-y-auto flex flex-col border-l border-gray-200">
            {/* Header */}
            <div className="p-5 bg-[#111827] text-white flex items-start justify-between gap-4 sticky top-0 z-10">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                    selectedFinding.attention === 'RED' ? 'bg-red-600 text-white' :
                    selectedFinding.attention === 'AMBER' ? 'bg-orange-500 text-white' :
                    'bg-blue-600 text-white'
                  }`}>
                    {selectedFinding.id} • {selectedFinding.attention}
                  </span>
                  <span className="text-[11px] text-gray-400 font-mono">
                    AI Confidence: {selectedFinding.confidence}
                  </span>
                </div>
                <h2 className="text-base font-bold text-white tracking-tight">{selectedFinding.title}</h2>
              </div>

              <button
                onClick={() => onSelectFinding(null)}
                className="p-1 rounded text-gray-400 hover:text-white hover:bg-gray-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content Body */}
            <div className="p-6 space-y-6 flex-1 text-xs text-gray-800">
              {/* Source Clause Quote Box */}
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-gray-700 uppercase tracking-widest text-[10px] flex items-center space-x-1.5">
                    <FileText className="w-3.5 h-3.5 text-blue-600" />
                    <span>Source: Page {selectedFinding.source.page}, Clause {selectedFinding.source.clause}</span>
                  </span>
                  <button
                    onClick={() => onJumpToViewer(selectedFinding)}
                    className="text-blue-600 hover:text-blue-800 font-semibold text-[11px] flex items-center space-x-1 cursor-pointer"
                  >
                    <span>View Full Text</span>
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
                <p className="font-mono text-gray-800 bg-white p-3 rounded-lg border border-gray-200 leading-relaxed">
                  "{selectedFinding.source.extractedText}"
                </p>
              </div>

              {/* WHY THIS MATTERS */}
              <div className="space-y-1.5">
                <h4 className="font-bold uppercase tracking-widest text-[10px] text-blue-900 flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                  <span>Why This Matters (CA Perspective)</span>
                </h4>
                <p className="text-gray-700 bg-blue-50/60 p-3.5 rounded-lg border border-blue-100 leading-relaxed">
                  {selectedFinding.whyItMatters}
                </p>
              </div>

              {/* POTENTIAL IMPACT */}
              <div className="space-y-1.5">
                <h4 className="font-bold uppercase tracking-widest text-[10px] text-gray-600">
                  Potential Professional Impact
                </h4>
                <p className="text-gray-700 bg-gray-50 p-3.5 rounded-lg border border-gray-200 leading-relaxed whitespace-pre-line">
                  {selectedFinding.potentialImpact}
                </p>
              </div>

              {/* WHAT TO VERIFY */}
              <div className="space-y-2">
                <h4 className="font-bold uppercase tracking-widest text-[10px] text-gray-600">
                  What To Verify (Audit & Compliance Steps)
                </h4>
                <ul className="space-y-1.5">
                  {selectedFinding.whatToVerify.map((item, idx) => (
                    <li key={idx} className="flex items-start space-x-2 text-gray-700 bg-gray-50 p-2 rounded border border-gray-100">
                      <CornerDownRight className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* EVIDENCE REQUIRED */}
              <div className="space-y-2">
                <h4 className="font-bold uppercase tracking-widest text-[10px] text-gray-600">
                  Targeted Evidence Required Checklist
                </h4>
                <ul className="space-y-1.5">
                  {selectedFinding.evidenceRequired.map((doc, idx) => (
                    <li key={idx} className="flex items-start space-x-2 text-emerald-950 bg-emerald-50/60 p-2 rounded border border-emerald-200">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                      <span>{doc}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* MANAGEMENT QUESTIONS */}
              <div className="space-y-2">
                <h4 className="font-bold uppercase tracking-widest text-[10px] text-gray-600">
                  Questions For Management / CFO
                </h4>
                <ul className="space-y-1.5">
                  {selectedFinding.managementQuestions.map((q, idx) => (
                    <li key={idx} className="flex items-start space-x-2 text-amber-950 bg-amber-50/60 p-2 rounded border border-amber-200">
                      <HelpCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                      <span className="font-medium">{q}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* STATUTORY FRAMEWORK */}
              <div className="space-y-1.5">
                <h4 className="font-bold uppercase tracking-widest text-[10px] text-gray-600">
                  Relevant Framework / Law To Confirm
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedFinding.frameworkToConfirm.map((fw, idx) => (
                    <span key={idx} className="px-2.5 py-1 rounded text-[11px] font-semibold bg-gray-100 text-gray-800 border border-gray-200">
                      {fw}
                    </span>
                  ))}
                </div>
              </div>

              {/* CA Review Action Bar */}
              <div className="pt-4 border-t border-gray-200 space-y-3">
                <h4 className="font-bold uppercase tracking-widest text-[10px] text-gray-600 flex items-center space-x-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-blue-600" />
                  <span>CA Professional Decision & Workflow</span>
                </h4>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <button
                    onClick={() => onUpdateFindingStatus(selectedFinding.id, 'Cleared')}
                    className="px-3 py-2 rounded bg-gray-900 hover:bg-black text-white text-[10px] font-bold uppercase tracking-wider transition"
                  >
                    Accept & Clear
                  </button>
                  <button
                    onClick={() => onUpdateFindingStatus(selectedFinding.id, 'Under Review')}
                    className="px-3 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-bold uppercase tracking-wider transition"
                  >
                    Review Req.
                  </button>
                  <button
                    onClick={() => onUpdateFindingStatus(selectedFinding.id, 'Requires Information')}
                    className="px-3 py-2 rounded bg-orange-500 hover:bg-orange-600 text-white text-[10px] font-bold uppercase tracking-wider transition"
                  >
                    Need Info
                  </button>
                  <button
                    onClick={() => onUpdateFindingStatus(selectedFinding.id, 'Escalated')}
                    className="px-3 py-2 rounded bg-red-600 hover:bg-red-700 text-white text-[10px] font-bold uppercase tracking-wider transition"
                  >
                    Escalate
                  </button>
                </div>
              </div>

              {/* Working Paper Audit Notes */}
              <div className="space-y-2 pt-2 border-t border-gray-200">
                <h4 className="font-bold uppercase tracking-widest text-[10px] text-gray-600 flex items-center space-x-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-gray-500" />
                  <span>CA Working Paper Notes ({selectedFinding.comments.length})</span>
                </h4>

                {selectedFinding.comments.length > 0 && (
                  <div className="space-y-2 max-h-36 overflow-y-auto">
                    {selectedFinding.comments.map(c => (
                      <div key={c.id} className="bg-gray-50 p-2.5 rounded border border-gray-200 text-[11px]">
                        <div className="flex items-center justify-between text-gray-400 mb-1">
                          <span className="font-semibold text-gray-700">{c.author}</span>
                          <span>{new Date(c.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                        <p className="text-gray-800">{c.text}</p>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newCommentText}
                    onChange={(e) => setNewCommentText(e.target.value)}
                    placeholder="Add audit note or verified fact..."
                    className="flex-1 px-3 py-1.5 text-xs rounded border border-gray-300 focus:ring-1 focus:ring-blue-500"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleCommentSubmit(selectedFinding.id);
                    }}
                  />
                  <button
                    onClick={() => handleCommentSubmit(selectedFinding.id)}
                    className="px-3 py-1.5 rounded bg-gray-900 hover:bg-gray-800 text-white font-bold uppercase tracking-widest text-[10px] shrink-0 flex items-center space-x-1"
                  >
                    <Send className="w-3 h-3" />
                    <span>Save</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
