import React, { useState, useMemo } from 'react';
import { 
  FileText, 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  Bookmark, 
  Tag, 
  ShieldAlert, 
  ArrowRight,
  ExternalLink,
  BookOpen,
  Info
} from 'lucide-react';
import { ContractDocument, ExtractedClause, Finding } from '../types/contract';

interface ContractViewerProps {
  contract: ContractDocument;
  selectedFinding: Finding | null;
  onSelectFinding: (finding: Finding | null) => void;
}

export const ContractViewer: React.FC<ContractViewerProps> = ({
  contract,
  selectedFinding,
  onSelectFinding
}) => {
  const [currentPage, setCurrentPage] = useState<number>(selectedFinding ? selectedFinding.source.page : 1);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null);

  // Sync page with selected finding if changed from outside
  React.useEffect(() => {
    if (selectedFinding?.source?.page) {
      setCurrentPage(selectedFinding.source.page);
    }
  }, [selectedFinding]);

  const activePageData = useMemo(() => {
    const found = contract.pages.find(p => p.pageNumber === currentPage);
    return found || contract.pages[0] || { pageNumber: 1, text: contract.rawText };
  }, [contract, currentPage]);

  const clausesOnCurrentPage = useMemo(() => {
    return contract.clauses.filter(c => c.pageNumber === currentPage || !c.pageNumber);
  }, [contract.clauses, currentPage]);

  const filteredClauses = useMemo(() => {
    if (!searchQuery.trim()) return contract.clauses;
    const query = searchQuery.toLowerCase();
    return contract.clauses.filter(
      c => c.title.toLowerCase().includes(query) ||
           c.text.toLowerCase().includes(query) ||
           c.categories.some(cat => cat.toLowerCase().includes(query))
    );
  }, [contract.clauses, searchQuery]);

  const highlightSearchText = (text: string, query: string) => {
    if (!query.trim()) return text;
    const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, i) => 
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={i} className="bg-amber-200 text-amber-950 font-bold px-0.5 rounded">
          {part}
        </mark>
      ) : part
    );
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">
      {/* Header bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 uppercase">
              Document Viewer & Traceability
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {contract.fileName} ({contract.pageCount} Pages)
            </span>
          </div>
          <h2 className="text-base font-bold text-slate-900 mt-1">{contract.identity.title}</h2>
        </div>

        {/* Page Nav */}
        <div className="flex items-center space-x-2 text-xs">
          <button
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage <= 1}
            className="p-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 text-slate-700"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <span className="font-semibold text-slate-700 px-2 py-1 bg-slate-100 rounded-md">
            Page {currentPage} of {contract.pageCount}
          </span>

          <button
            onClick={() => setCurrentPage(prev => Math.min(contract.pageCount, prev + 1))}
            disabled={currentPage >= contract.pageCount}
            className="p-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 text-slate-700"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left 2 Cols: Document Reader */}
        <div className="lg:col-span-2 space-y-4">
          {/* Active Highlight Banner if a finding is selected */}
          {selectedFinding && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3.5 flex items-start justify-between gap-3 text-xs">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    selectedFinding.attention === 'RED' ? 'bg-rose-600 text-white' :
                    selectedFinding.attention === 'AMBER' ? 'bg-amber-500 text-white' :
                    'bg-blue-600 text-white'
                  }`}>
                    {selectedFinding.id} • {selectedFinding.attention}
                  </span>
                  <span className="font-bold text-slate-900">{selectedFinding.title}</span>
                </div>
                <p className="text-slate-600 font-mono text-[11px] bg-white p-2 rounded border border-indigo-100">
                  <span className="font-semibold text-indigo-700">Source Quote (Pg {selectedFinding.source.page}, Cl {selectedFinding.source.clause}):</span> "{selectedFinding.source.extractedText}"
                </p>
              </div>

              <button
                onClick={() => onSelectFinding(null)}
                className="text-indigo-600 hover:text-indigo-800 font-semibold text-[11px] shrink-0"
              >
                Clear Focus
              </button>
            </div>
          )}

          {/* Document Content Canvas */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 font-mono text-xs text-slate-800 leading-relaxed whitespace-pre-wrap selection:bg-indigo-100 min-h-[500px]">
            {highlightSearchText(activePageData.text, searchQuery)}
          </div>
        </div>

        {/* Right 1 Col: Clause Explorer & Finding Links */}
        <div className="space-y-4">
          {/* Search Clauses Box */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search contract text or clauses..."
                className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{filteredClauses.length} clauses indexed</span>
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="text-indigo-600 hover:underline">
                  Reset
                </button>
              )}
            </div>
          </div>

          {/* Clause List */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3 max-h-[550px] overflow-y-auto">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Extracted Clauses & Citations
            </h3>

            <div className="space-y-2.5">
              {filteredClauses.map(clause => {
                const linkedFindings = contract.findings.filter(f => 
                  f.source.clause.includes(clause.clauseNumber) || 
                  clause.associatedFindingIds.includes(f.id)
                );

                return (
                  <div
                    key={clause.id}
                    onClick={() => {
                      setSelectedClauseId(clause.id);
                      if (clause.pageNumber) {
                        setCurrentPage(clause.pageNumber);
                      }
                      if (linkedFindings.length > 0) {
                        onSelectFinding(linkedFindings[0]);
                      }
                    }}
                    className={`p-3 rounded-lg border transition cursor-pointer text-xs ${
                      selectedClauseId === clause.id
                        ? 'bg-indigo-50/70 border-indigo-300'
                        : 'bg-slate-50 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-bold text-slate-900 font-mono">
                        Cl. {clause.clauseNumber} • Pg {clause.pageNumber}
                      </span>
                      <div className="flex items-center space-x-1">
                        {clause.categories.map(cat => (
                          <span key={cat} className="px-1.5 py-0.2 rounded text-[10px] bg-slate-200 text-slate-700 font-medium">
                            {cat}
                          </span>
                        ))}
                      </div>
                    </div>

                    <h4 className="font-semibold text-slate-800 text-[11px] mb-1">{clause.title}</h4>
                    <p className="text-slate-500 font-mono text-[10px] line-clamp-2">
                      {clause.text}
                    </p>

                    {linkedFindings.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-200/80 flex items-center justify-between text-[10px]">
                        <span className="text-indigo-700 font-semibold flex items-center space-x-1">
                          <ShieldAlert className="w-3 h-3" />
                          <span>{linkedFindings.length} Professional Finding(s)</span>
                        </span>
                        <ArrowRight className="w-3 h-3 text-indigo-500" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
