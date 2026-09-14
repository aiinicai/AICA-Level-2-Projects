import React, { useEffect, useState, useCallback } from 'react';
import type { Client, Note } from '../types';
import { fetchNotes, updateNote, resetNote } from '../services/api';
import { API_BASE } from '../services/api';
import {
  BookOpen, Save, RotateCcw, Check, RefreshCw, Edit3, Eye,
  Table as TableIcon, FileText, ChevronDown, ChevronRight, Printer
} from 'lucide-react';

interface NotesAccountsProps {
  client: Client;
}

const fmtAmt = (v: string | number) => {
  const n = typeof v === 'string' ? parseFloat(v) : v;
  if (isNaN(n)) return v as string;
  if (n < 0) return `(${Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2 })})`;
  return n.toLocaleString('en-IN', { minimumFractionDigits: 2 });
};

const isAmountCol = (val: string, colIdx: number) =>
  colIdx > 0 && !isNaN(parseFloat(val)) && val.trim() !== '';

const isTotalRow = (row: string[]) =>
  row[0]?.toUpperCase().startsWith('TOTAL') ||
  row[0]?.toUpperCase().startsWith('GRAND TOTAL') ||
  row[0]?.toUpperCase().startsWith('NET BLOCK') ||
  row[0]?.toUpperCase().startsWith('SURPLUS');

const isSubRow = (row: string[]) =>
  row[0]?.trim().startsWith('(') ||
  row[0]?.trim().startsWith('   ') ||
  row[0]?.trim().startsWith('    ');

const isHeaderRow = (row: string[]) =>
  row.slice(1).every(v => v.trim() === '');

export const NotesAccountsPage: React.FC<NotesAccountsProps> = ({ client }) => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [successId, setSuccessId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [expandedNotes, setExpandedNotes] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilter, setActiveFilter] = useState<'all' | 'bs' | 'pl' | 'disc'>('all');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchNotes(client.id);
      if (Array.isArray(data)) {
        setNotes(data);
        // Auto-expand first 3 notes
        setExpandedNotes(new Set(data.slice(0, 3).map((n: Note) => n.note_number)));
      }
    } catch (e) {
      console.error(e);
      setError('Failed to load notes. Please check that the backend is running.');
    } finally {
      setLoading(false);
    }
  }, [client.id]);

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      await fetch(`${API_BASE}/notes/${client.id}/regenerate`, { method: 'POST' });
      await loadData();
    } catch (e) {
      setError('Regeneration failed. Please try again.');
    } finally {
      setRegenerating(false);
    }
  };

  useEffect(() => { if (client) loadData(); }, [client.id]);

  const handleSave = async (note: Note) => {
    setSavingId(note.id);
    try {
      await updateNote(note.id, note.content);
      setSuccessId(note.id);
      setEditingId(null);
      setTimeout(() => setSuccessId(null), 2500);
      await loadData();
    } finally {
      setSavingId(null);
    }
  };

  const handleReset = async (note: Note) => {
    setSavingId(note.id);
    try {
      await resetNote(note.id);
      setEditingId(null);
      await loadData();
    } finally {
      setSavingId(null);
    }
  };

  const toggleExpand = (noteNum: string) => {
    setExpandedNotes(prev => {
      const next = new Set(prev);
      next.has(noteNum) ? next.delete(noteNum) : next.add(noteNum);
      return next;
    });
  };

  const getNoteSection = (num: string) => {
    const n = parseFloat(num);
    if (n < 4) return 'bs';
    if (n < 6) return 'bs';
    if (n < 8) return 'pl';
    return 'disc';
  };

  const filteredNotes = notes.filter(note => {
    const matchSearch = searchTerm === '' ||
      note.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      note.note_number.includes(searchTerm);
    const matchFilter = activeFilter === 'all' || getNoteSection(note.note_number) === activeFilter;
    return matchSearch && matchFilter;
  });

  const bsNotes = notes.filter(n => getNoteSection(n.note_number) === 'bs');
  const plNotes = notes.filter(n => getNoteSection(n.note_number) === 'pl');
  const discNotes = notes.filter(n => getNoteSection(n.note_number) === 'disc');

  return (
    <div className="space-y-5 max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <div className="bg-[#1B365D] text-white p-5 rounded-xl shadow space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-base font-black tracking-wider uppercase flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-orange-400" />
                NOTES ANNEXED TO AND FORMING PART OF THE FINANCIAL STATEMENTS
              </h1>
              <p className="text-xs text-slate-300 mt-1 font-medium">
                {client.name} | {client.entity_type} | {client.reporting_period} | Figures in {client.currency}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5 font-serif italic">
                Prepared under Schedule III Division I of the Companies Act, 2013 as per IGAAP
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 text-white rounded text-xs font-bold transition-colors disabled:opacity-60"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${regenerating ? 'animate-spin' : ''}`} />
                {regenerating ? 'Regenerating…' : 'Regenerate from TB'}
              </button>
              <button
                onClick={() => {
                  setExpandedNotes(new Set(notes.map(n => n.note_number)));
                  setTimeout(() => window.print(), 150);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-600 hover:bg-slate-500 text-white rounded text-xs font-bold transition-colors cursor-pointer"
              >
                <Printer className="w-3.5 h-3.5" />
                Print Notes to Accounts
              </button>

            </div>
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-6 pt-1 border-t border-white/20">
            {[
              { label: 'Total Notes', val: notes.length, color: 'text-white' },
              { label: 'BS Notes', val: bsNotes.length, color: 'text-sky-300' },
              { label: 'P&L Notes', val: plNotes.length, color: 'text-amber-300' },
              { label: 'Disclosure Notes', val: discNotes.length, color: 'text-emerald-300' },
              { label: 'Modified', val: notes.filter(n => n.is_modified).length, color: 'text-orange-300' },
            ].map(s => (
              <div key={s.label} className="text-center">
                <div className={`text-lg font-black font-mono ${s.color}`}>{s.val}</div>
                <div className="text-[10px] text-slate-400 font-semibold uppercase">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search notes…"
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="studio-input text-xs px-3 py-1.5 w-56"
        />
        <div className="flex gap-1">
          {(['all', 'bs', 'pl', 'disc'] as const).map(f => (
            <button
              key={f}
              onClick={() => setActiveFilter(f)}
              className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${
                activeFilter === f
                  ? 'bg-[#1B365D] text-white'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
              }`}
            >
              {f === 'all' ? 'All Notes' : f === 'bs' ? 'Balance Sheet' : f === 'pl' ? 'P&L Notes' : 'Disclosures'}
            </button>
          ))}
        </div>
        <div className="ml-auto flex gap-2">
          <button
            onClick={() => setExpandedNotes(new Set(notes.map(n => n.note_number)))}
            className="text-xs font-bold text-slate-600 dark:text-slate-400 hover:text-[#1B365D] dark:hover:text-blue-400 flex items-center gap-1"
          >
            <ChevronDown className="w-3.5 h-3.5" /> Expand All
          </button>
          <button
            onClick={() => setExpandedNotes(new Set())}
            className="text-xs font-bold text-slate-600 dark:text-slate-400 hover:text-[#1B365D] dark:hover:text-blue-400 flex items-center gap-1"
          >
            <ChevronRight className="w-3.5 h-3.5" /> Collapse All
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-lg text-xs text-rose-700 dark:text-rose-300 font-semibold flex items-center justify-between">
          <span>{error}</span>
          <button onClick={loadData} className="flex items-center gap-1 font-bold hover:underline">
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center p-16 gap-3 text-slate-500 text-xs font-semibold">
          <RefreshCw className="w-5 h-5 animate-spin text-orange-500" />
          Generating Schedule III notes from trial balance data…
        </div>
      ) : filteredNotes.length === 0 ? (
        <div className="p-12 text-center text-slate-500 text-xs font-semibold border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl">
          <FileText className="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          No notes found. Load sample data or upload a trial balance, then click "Regenerate from TB".
        </div>
      ) : (
        <div className="space-y-4">
          {filteredNotes.map((note) => {
            const isExpanded = expandedNotes.has(note.note_number);
            const isEditing = editingId === note.id;
            let parsedTable: { headers: string[]; rows: string[][] } | null = null;
            if (note.table_json) {
              try { parsedTable = JSON.parse(note.table_json); } catch { /* noop */ }
            }
            const hasFootnote = note.content && note.content.trim().length > 0;

            return (
              <div
                key={note.id}
                className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow print:break-inside-avoid"
              >
                {/* Note Header Band */}
                <div
                  className="bg-[#1B365D] text-white px-5 py-3 flex items-center justify-between cursor-pointer select-none"
                  onClick={() => toggleExpand(note.note_number)}
                >
                  <div className="flex items-center gap-3">
                    {isExpanded
                      ? <ChevronDown className="w-4 h-4 text-orange-400 shrink-0" />
                      : <ChevronRight className="w-4 h-4 text-orange-400 shrink-0" />}
                    <span className="bg-orange-500 text-white font-mono text-xs font-black px-2.5 py-1 rounded shrink-0">
                      Note {note.note_number}
                    </span>
                    <h3 className="text-sm font-black uppercase tracking-wide truncate">
                      {note.title}
                    </h3>
                  </div>
                  <div className="flex items-center gap-2 shrink-0" onClick={e => e.stopPropagation()}>
                    {note.is_modified && (
                      <span className="bg-orange-500 text-white text-[9px] font-black px-2 py-0.5 rounded uppercase tracking-wider">
                        MODIFIED
                      </span>
                    )}
                    <button
                      onClick={() => setEditingId(isEditing ? null : note.id)}
                      className="flex items-center gap-1 text-[10px] font-bold px-2.5 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors"
                    >
                      {isEditing ? <Eye className="w-3 h-3" /> : <Edit3 className="w-3 h-3" />}
                      {isEditing ? 'View' : 'Edit'}
                    </button>
                    {isEditing && (
                      <>
                        <button
                          onClick={() => handleReset(note)}
                          className="flex items-center gap-1 text-[10px] font-bold px-2.5 py-1 rounded bg-white/10 hover:bg-white/20 transition-colors"
                        >
                          <RotateCcw className="w-3 h-3" /> Reset
                        </button>
                        <button
                          onClick={() => handleSave(note)}
                          disabled={savingId === note.id}
                          className="flex items-center gap-1 text-[10px] font-bold px-2.5 py-1 rounded bg-orange-500 hover:bg-orange-600 transition-colors disabled:opacity-60"
                        >
                          {successId === note.id
                            ? <><Check className="w-3 h-3" /> Saved!</>
                            : <><Save className="w-3 h-3" /> Save</>}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Note Body */}
                {isExpanded && (
                  <div className="bg-white dark:bg-slate-950 divide-y divide-slate-200 dark:divide-slate-800">

                    {/* Structured Table */}
                    {parsedTable && (
                      <div>
                        <div className="flex items-center gap-1.5 px-5 py-2 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
                          <TableIcon className="w-3.5 h-3.5 text-orange-600" />
                          <span className="text-[10px] font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider">
                            Schedule III — {note.title}
                          </span>
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs border-collapse">
                            <thead>
                              <tr className="bg-[#2d4a73] dark:bg-[#1B365D] text-white">
                                {parsedTable.headers.map((h, hi) => (
                                  <th
                                    key={hi}
                                    className={`py-2.5 px-4 text-[11px] font-black uppercase tracking-wide whitespace-nowrap border-r border-white/10 last:border-0 ${
                                      hi === 0 ? 'text-left min-w-[220px]' : 'text-right min-w-[100px]'
                                    }`}
                                  >
                                    {h}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {parsedTable.rows.map((row, ri) => {
                                const isTotal = isTotalRow(row);
                                const isSub = isSubRow(row);
                                const isHdr = isHeaderRow(row);
                                return (
                                  <tr
                                    key={ri}
                                    className={`border-b border-slate-100 dark:border-slate-800 ${
                                      isTotal
                                        ? 'bg-[#1B365D]/8 dark:bg-[#1B365D]/30 font-black border-t-2 border-slate-400'
                                        : isHdr
                                        ? 'bg-slate-100 dark:bg-slate-800/60 font-bold'
                                        : 'hover:bg-slate-50 dark:hover:bg-slate-900/30 font-medium'
                                    }`}
                                  >
                                    {row.map((cell, ci) => {
                                      const isAmt = isAmountCol(cell, ci);
                                      const numVal = parseFloat(cell);
                                      return (
                                        <td
                                          key={ci}
                                          className={`py-2 px-4 border-r border-slate-100 dark:border-slate-800 last:border-0 ${
                                            ci === 0
                                              ? `${isSub ? 'pl-8' : ''} text-left ${
                                                  isTotal
                                                    ? 'text-[#1B365D] dark:text-blue-300 text-xs'
                                                    : isHdr
                                                    ? 'text-slate-700 dark:text-slate-300 text-[11px]'
                                                    : 'text-slate-800 dark:text-slate-200 text-[11px]'
                                                }`
                                              : `text-right font-mono bg-slate-50/80 dark:bg-slate-900/40 ${
                                                  isTotal
                                                    ? 'text-[#1B365D] dark:text-blue-300 text-xs border-t border-slate-400 dark:border-slate-500'
                                                    : 'text-slate-700 dark:text-slate-300 text-[11px]'
                                                } ${isAmt && !isNaN(numVal) && numVal < 0 ? 'text-rose-600 dark:text-rose-400' : ''}`
                                          }`}
                                        >
                                          {ci === 0
                                            ? cell
                                            : isAmt
                                            ? fmtAmt(cell)
                                            : cell || '–'}
                                        </td>
                                      );
                                    })}
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Explanatory Footnotes */}
                    {hasFootnote && (
                      <div className="px-5 py-3.5 bg-slate-50/60 dark:bg-slate-900/30">
                        {isEditing ? (
                          <div className="space-y-2">
                            <label className="text-[10px] font-black text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                              Edit Explanatory Footnotes & Management Disclosures:
                            </label>
                            <textarea
                              className="studio-input w-full h-40 font-mono text-xs p-3 leading-relaxed"
                              value={note.content}
                              onChange={(e) => {
                                const val = e.target.value;
                                setNotes(prev => prev.map(n =>
                                  n.id === note.id ? { ...n, content: val } : n
                                ));
                              }}
                            />
                          </div>
                        ) : (
                          <div className="space-y-1.5">
                            <div className="text-[10px] font-black text-slate-500 dark:text-slate-500 uppercase tracking-wider mb-2">
                              Explanatory Notes & Disclosures:
                            </div>
                            <div className="text-[11px] text-slate-700 dark:text-slate-300 leading-relaxed font-serif whitespace-pre-line">
                              {note.content}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Signature Block */}
      {!loading && filteredNotes.length > 0 && (
        <div className="mt-8 p-6 border-2 border-slate-300 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-950 print:block">
          <div className="text-center text-xs text-slate-500 dark:text-slate-400 font-serif italic mb-6">
            The above Notes form an integral part of the Financial Statements
          </div>
          <div className="grid grid-cols-2 gap-8 text-xs">
            <div className="space-y-6 border-t border-slate-300 dark:border-slate-700 pt-4">
              <div className="font-black text-[#1B365D] dark:text-blue-400 text-[11px] uppercase">For {client.name}</div>
              <div className="space-y-1">
                <div className="text-slate-500 dark:text-slate-400 font-semibold">Authorized Signatory</div>
                <div className="text-slate-700 dark:text-slate-300">Director / Managing Director</div>
                <div className="text-slate-500 dark:text-slate-400 font-mono text-[10px]">DIN: ____________</div>
              </div>
            </div>
            <div className="space-y-6 border-t border-slate-300 dark:border-slate-700 pt-4">
              <div className="font-black text-[#1B365D] dark:text-blue-400 text-[11px] uppercase">As per our Report of even date</div>
              <div className="space-y-1">
                <div className="text-slate-700 dark:text-slate-300 font-bold">FS BUILDER LITE</div>
                <div className="text-slate-500 dark:text-slate-400">Prepared by: {client.prepared_by}</div>
                <div className="text-slate-500 dark:text-slate-400">Reviewed by: {client.reviewed_by}</div>
                <div className="text-slate-400 dark:text-slate-500 font-mono text-[10px]">Date: {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
