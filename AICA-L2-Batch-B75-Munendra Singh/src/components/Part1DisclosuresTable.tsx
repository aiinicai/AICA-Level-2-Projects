import React, { useState, useMemo } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Search, 
  Copy, 
  Check,
  BookOpen
} from 'lucide-react';
import { DisclosureItem, DisclosureStatus } from '../types';

interface Part1DisclosuresTableProps {
  disclosures: DisclosureItem[];
}

export const Part1DisclosuresTable: React.FC<Part1DisclosuresTableProps> = ({ disclosures }) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);

  const filteredDisclosures = useMemo(() => {
    return disclosures.filter((item) => {
      const matchesStatus = statusFilter === 'ALL' || item.status === statusFilter;
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        item.standard.toLowerCase().includes(q) ||
        (item.standardName && item.standardName.toLowerCase().includes(q)) ||
        item.requirement.toLowerCase().includes(q) ||
        item.observation.toLowerCase().includes(q);
      return matchesStatus && matchesSearch;
    });
  }, [disclosures, statusFilter, searchQuery]);

  const counts = useMemo(() => {
    return {
      total: disclosures.length,
      complied: disclosures.filter((d) => d.status === 'Complied').length,
      missing: disclosures.filter((d) => d.status === 'Missing').length,
      partial: disclosures.filter((d) => d.status === 'Partial').length,
    };
  }, [disclosures]);

  const getStatusBadge = (status: DisclosureStatus) => {
    switch (status) {
      case 'Complied':
        return (
          <span className="bg-green-700 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider inline-block">
            COMPLIED
          </span>
        );
      case 'Missing':
        return (
          <span className="bg-red-600 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider inline-block">
            MISSING
          </span>
        );
      case 'Partial':
      default:
        return (
          <span className="bg-orange-500 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider inline-block">
            PARTIAL
          </span>
        );
    }
  };

  const handleCopyTable = () => {
    const header = "Standard\tMandatory Disclosure Requirement\tStatus\tObservation / Details\n";
    const rows = filteredDisclosures
      .map((d) => `${d.standard}\t${d.requirement}\t${d.status}\t${d.observation}`)
      .join('\n');
    navigator.clipboard.writeText(header + rows);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="part-1-mandatory-disclosures" className="bg-white border-2 border-[#141414] shadow-dense mb-6 overflow-hidden">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between p-4 bg-[#F9F9F7] border-b border-[#141414] gap-3">
        <div>
          <h2 className="text-[11px] font-serif italic uppercase text-[#141414]/70 mb-0.5 tracking-wider">
            Statutory Verification Matrix • Part 1
          </h2>
          <h3 className="text-base sm:text-lg font-bold uppercase tracking-tight text-[#141414]">
            Part 1: Ind AS Mandatory Disclosure Check
          </h3>
          <p className="text-[10px] font-mono text-[#141414]/70 mt-0.5 uppercase">
            MANDATORY STANDARDS: IND AS 1, 7, 12, 16, 19, 23, 24, 33, 37, 107/109, 115, 116 // SCH III DIV II
          </p>
        </div>

        {/* Copy / Action */}
        <button
          id="copy-part-1-btn"
          onClick={handleCopyTable}
          className="self-start md:self-center inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase bg-white hover:bg-neutral-100 text-[#141414] border border-[#141414] transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-700" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'COPIED' : 'COPY TABLE'}</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 bg-[#E4E3E0] border-b border-[#141414]">
        {/* Status Filter Buttons */}
        <div className="flex flex-wrap gap-1 w-full sm:w-auto">
          <button
            id="filter-all-disclosures"
            onClick={() => setStatusFilter('ALL')}
            className={`px-2.5 py-1 text-[10px] font-mono font-bold uppercase transition border border-[#141414] ${
              statusFilter === 'ALL'
                ? 'bg-[#141414] text-white'
                : 'bg-white text-[#141414] hover:bg-neutral-100'
            }`}
          >
            ALL ({counts.total})
          </button>
          <button
            id="filter-missing-disclosures"
            onClick={() => setStatusFilter('Missing')}
            className={`px-2.5 py-1 text-[10px] font-mono font-bold uppercase transition border border-[#141414] ${
              statusFilter === 'Missing'
                ? 'bg-red-600 text-white'
                : 'bg-red-100 text-red-700 hover:bg-red-200'
            }`}
          >
            MISSING ({counts.missing})
          </button>
          <button
            id="filter-partial-disclosures"
            onClick={() => setStatusFilter('Partial')}
            className={`px-2.5 py-1 text-[10px] font-mono font-bold uppercase transition border border-[#141414] ${
              statusFilter === 'Partial'
                ? 'bg-orange-500 text-white'
                : 'bg-orange-100 text-orange-800 hover:bg-orange-200'
            }`}
          >
            PARTIAL ({counts.partial})
          </button>
          <button
            id="filter-complied-disclosures"
            onClick={() => setStatusFilter('Complied')}
            className={`px-2.5 py-1 text-[10px] font-mono font-bold uppercase transition border border-[#141414] ${
              statusFilter === 'Complied'
                ? 'bg-green-700 text-white'
                : 'bg-green-100 text-green-800 hover:bg-green-200'
            }`}
          >
            COMPLIED ({counts.complied})
          </button>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#141414]/60" />
          <input
            id="search-disclosures-input"
            type="text"
            placeholder="SEARCH STANDARD / KEYWORD..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-2.5 py-1 text-[11px] font-mono uppercase bg-white border border-[#141414] text-[#141414] focus:outline-none focus:ring-1 focus:ring-[#141414]"
          />
        </div>
      </div>

      {/* Structured Disclosure Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-[#141414]/20 text-left">
          <thead className="bg-[#141414] text-white text-[10px] uppercase font-bold tracking-widest font-mono">
            <tr>
              <th scope="col" className="py-2.5 px-4 w-40">
                Standard
              </th>
              <th scope="col" className="py-2.5 px-4 w-72">
                Mandatory Requirement
              </th>
              <th scope="col" className="py-2.5 px-4 w-28 text-center">
                Status
              </th>
              <th scope="col" className="py-2.5 px-4">
                Observation / Detail
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-[#141414]/10 text-[11px] text-[#141414]">
            {filteredDisclosures.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-6 text-center text-[#141414]/60 font-mono">
                  NO STATUTORY DISCLOSURES FOUND MATCHING FILTER CRITERIA.
                </td>
              </tr>
            ) : (
              filteredDisclosures.map((item, idx) => {
                const isMissing = item.status === 'Missing';
                return (
                  <tr
                    key={idx}
                    className={`hover:bg-[#F5F5F5] transition ${
                      isMissing ? 'bg-red-50/40' : ''
                    }`}
                  >
                    {/* Standard */}
                    <td className="py-2.5 px-4 font-bold text-[#141414] align-top">
                      <div className="font-mono text-xs">{item.standard}</div>
                      {item.standardName && (
                        <div className="text-[10px] font-serif italic text-[#141414]/70 mt-0.5">
                          {item.standardName}
                        </div>
                      )}
                      {item.applicableParagraph && (
                        <div className="text-[9px] font-mono uppercase text-[#141414]/60 mt-0.5">
                          PARA {item.applicableParagraph}
                        </div>
                      )}
                    </td>

                    {/* Requirement */}
                    <td className="py-2.5 px-4 font-medium text-[#141414] align-top leading-snug">
                      {item.requirement}
                    </td>

                    {/* Status */}
                    <td className="py-2.5 px-4 align-top text-center">
                      {getStatusBadge(item.status)}
                    </td>

                    {/* Observation / Details */}
                    <td className="py-2.5 px-4 align-top leading-snug text-[#141414]">
                      {item.observation.includes('Section/Note not found in uploaded file') ? (
                        <div className="font-bold text-red-600 font-mono flex items-center gap-1.5">
                          <XCircle className="w-3.5 h-3.5 shrink-0 stroke-[2.5]" />
                          <span>Section/Note not found in uploaded file.</span>
                        </div>
                      ) : (
                        <span className="font-serif italic text-[#141414]">{item.observation}</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
};

