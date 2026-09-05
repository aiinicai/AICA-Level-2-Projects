import React, { useState } from 'react';
import {
  FileText,
  Edit3,
  Plus,
  Trash2,
  RefreshCw,
  Search,
  CheckCircle2,
  ArrowUp,
  ArrowDown,
  Sparkles,
  BookOpen,
  Printer,
  Copy,
  Check,
  Tag,
  AlertCircle,
  Eye,
} from 'lucide-react';
import { NoteToAccountItem, NoteCategory, EntityDetails } from '../types/accounting';
import { DEFAULT_STANDARD_NOTES } from '../utils/nonCorporateDefaults';

interface NotesToAccountsViewProps {
  entity: EntityDetails;
  notes: NoteToAccountItem[];
  onUpdateNotes: (notes: NoteToAccountItem[]) => void;
  onNavigateToTab?: (tab: any) => void;
}

export const NotesToAccountsView: React.FC<NotesToAccountsViewProps> = ({
  entity,
  notes,
  onUpdateNotes,
  onNavigateToTab,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);

  // Edit draft state
  const [draftTitle, setDraftTitle] = useState('');
  const [draftNumber, setDraftNumber] = useState<number | string>(1);
  const [draftCategory, setDraftCategory] = useState<NoteCategory>('POLICIES');
  const [draftContent, setDraftContent] = useState('');

  // Add new note modal/inline state
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newCategory, setNewCategory] = useState<NoteCategory>('CUSTOM');
  const [newContent, setNewContent] = useState('');

  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const categories: { id: string; label: string }[] = [
    { id: 'ALL', label: 'All Notes' },
    { id: 'POLICIES', label: 'Accounting Policies (AS 1-29)' },
    { id: 'CAPITAL', label: 'Capital Accounts' },
    { id: 'LOANS', label: 'Borrowings & Security' },
    { id: 'MSME', label: 'MSME Disclosures' },
    { id: 'RECEIVABLES_PAYABLES', label: 'Receivables & Payables' },
    { id: 'CONTINGENT', label: 'Contingent Liabilities' },
    { id: 'RELATED_PARTY', label: 'Related Party (AS 18)' },
    { id: 'STATUTORY', label: 'Statutory & Others' },
    { id: 'CUSTOM', label: 'Custom Notes' },
  ];

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Filter notes
  const filteredNotes = notes.filter(note => {
    const matchesCategory = selectedCategory === 'ALL' || note.category === selectedCategory;
    if (!matchesCategory) return false;
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      note.title.toLowerCase().includes(term) ||
      note.content.toLowerCase().includes(term) ||
      String(note.noteNumber).toLowerCase().includes(term)
    );
  });

  // Start editing note
  const handleStartEdit = (note: NoteToAccountItem) => {
    setEditingNoteId(note.id);
    setDraftTitle(note.title);
    setDraftNumber(note.noteNumber);
    setDraftCategory(note.category);
    setDraftContent(note.content);
  };

  // Save edited note
  const handleSaveEdit = (id: string) => {
    const updated = notes.map(n => {
      if (n.id !== id) return n;
      return {
        ...n,
        title: draftTitle.trim() || n.title,
        noteNumber: draftNumber,
        category: draftCategory,
        content: draftContent,
        lastModified: new Date().toISOString(),
      };
    });
    onUpdateNotes(updated);
    setEditingNoteId(null);
    showToast(`Saved changes to Note ${draftNumber}: "${draftTitle}".`);
  };

  // Toggle active status
  const handleToggleActive = (id: string) => {
    const updated = notes.map(n => {
      if (n.id !== id) return n;
      return { ...n, isActive: !n.isActive };
    });
    onUpdateNotes(updated);
  };

  // Delete note
  const handleDeleteNote = (id: string) => {
    if (confirm('Are you sure you want to remove this note from the financial statements?')) {
      onUpdateNotes(notes.filter(n => n.id !== id));
      showToast('Note removed from financial statements.');
    }
  };

  // Move up
  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const copy = [...notes];
    const temp = copy[index - 1];
    copy[index - 1] = copy[index];
    copy[index] = temp;
    onUpdateNotes(copy);
  };

  // Move down
  const handleMoveDown = (index: number) => {
    if (index >= notes.length - 1) return;
    const copy = [...notes];
    const temp = copy[index + 1];
    copy[index + 1] = copy[index];
    copy[index] = temp;
    onUpdateNotes(copy);
  };

  // Add new note
  const handleAddNewNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    const nextNumber = notes.length + 1;
    const newNote: NoteToAccountItem = {
      id: `note-${Date.now()}`,
      noteNumber: nextNumber,
      title: newTitle.trim(),
      category: newCategory,
      content: newContent.trim() || 'Details to be updated as per entity records.',
      isActive: true,
      isStandard: false,
      lastModified: new Date().toISOString(),
    };

    onUpdateNotes([...notes, newNote]);
    setIsAddingNew(false);
    setNewTitle('');
    setNewContent('');
    showToast(`Added new Note ${nextNumber}: "${newNote.title}".`);
  };

  // Reset to ICAI standard defaults
  const handleResetToDefaults = () => {
    if (confirm('Reset all Notes to Accounts to standard ICAI Non-Corporate defaults? Any custom amendments will be reverted.')) {
      onUpdateNotes(DEFAULT_STANDARD_NOTES);
      showToast('Reset all Notes to Accounts to standard ICAI non-corporate template.');
    }
  };

  // Reset a single note
  const handleResetSingleNote = (id: string) => {
    const std = DEFAULT_STANDARD_NOTES.find(s => s.id === id);
    if (!std) {
      alert('This is a custom note with no default template.');
      return;
    }
    const updated = notes.map(n => (n.id === id ? { ...std, lastModified: new Date().toISOString() } : n));
    onUpdateNotes(updated);
    showToast(`Reset Note "${std.title}" to standard wording.`);
  };

  // Insert variable into draft
  const handleInsertVariable = (token: string) => {
    setDraftContent(prev => prev + ' ' + token);
  };

  // Copy content to clipboard
  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Print notes view
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-4" id="notes-to-accounts-container">
      {/* Top Banner */}
      <div className="bg-[#141414] text-[#E4E3E0] p-4 border border-[#141414] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-[#86efac]" />
            <h2 className="text-sm font-bold font-mono uppercase tracking-wider text-white">
              Notes to Accounts (Non-Corporate Entities)
            </h2>
          </div>
          <p className="text-[11.5px] text-[#A3A29E] mt-1">
            Standard statutory notes and significant accounting policies (AS 1 to 29) applicable to <strong>{entity.name}</strong> ({entity.entityType}).
            Amend clauses, customize figures, or add new explanatory notes directly in software.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setIsAddingNew(true)}
            className="inline-flex items-center px-3 py-1.5 bg-[#86efac] hover:bg-[#6ee7b7] text-[#0f291e] text-[11px] font-mono font-bold transition shadow-xs"
            id="btn-add-new-note"
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            ADD NOTE
          </button>

          <button
            onClick={handlePrint}
            className="inline-flex items-center px-3 py-1.5 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
            title="Print or save as PDF"
            id="btn-print-notes"
          >
            <Printer className="w-3.5 h-3.5 mr-1 text-[#38bdf8]" />
            PRINT / PDF
          </button>

          <button
            onClick={handleResetToDefaults}
            className="inline-flex items-center px-2.5 py-1.5 bg-[#222222] hover:bg-[#2e2e2e] text-[#E4E3E0] text-[11px] font-mono border border-white/20 transition"
            title="Reset to ICAI Non-Corporate standard notes"
            id="btn-reset-all-notes"
          >
            <RefreshCw className="w-3 h-3 mr-1 text-[#fbbf24]" />
            RESET DEFAULTS
          </button>
        </div>
      </div>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="bg-[#dcfce7] border border-[#86efac] text-[#166534] p-3 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-[#166534] shrink-0" />
            <span>{toastMessage}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="text-[11px] underline text-[#166534] hover:text-[#14532d]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Search & Category Filter Toolbar */}
      <div className="bg-[#F4F3F0] p-3 border border-[#141414]/20 space-y-2.5">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#5E5E5E]" />
            <input
              type="text"
              placeholder="Search notes by title or content (e.g. depreciation, MSME)..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-white border border-[#141414]/30 text-xs font-mono"
              id="input-search-notes"
            />
          </div>

          <div className="text-xs font-mono text-[#5E5E5E] flex items-center gap-3">
            <span>
              TOTAL NOTES: <strong className="text-[#141414]">{notes.length}</strong>
            </span>
            <span>
              ACTIVE: <strong className="text-green-700">{notes.filter(n => n.isActive).length}</strong>
            </span>
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="flex flex-wrap gap-1.5 pt-1 border-t border-[#141414]/10">
          {categories.map(c => {
            const isSelected = selectedCategory === c.id;
            const count = c.id === 'ALL' ? notes.length : notes.filter(n => n.category === c.id).length;

            return (
              <button
                key={c.id}
                onClick={() => setSelectedCategory(c.id)}
                className={`text-[10.5px] font-mono px-2 py-0.5 border transition ${
                  isSelected
                    ? 'bg-[#141414] text-white border-[#141414] font-bold'
                    : 'bg-white text-[#5E5E5E] border-[#141414]/20 hover:bg-[#ECEAE5] hover:text-[#141414]'
                }`}
              >
                {c.label} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Add New Note Form Modal / Card */}
      {isAddingNew && (
        <form
          onSubmit={handleAddNewNote}
          className="bg-white border-2 border-[#141414] p-4 shadow-sm space-y-3 font-mono text-xs"
          id="form-add-new-note"
        >
          <div className="flex items-center justify-between border-b border-[#141414]/20 pb-2">
            <h4 className="font-bold text-xs uppercase text-[#141414] flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5 text-[#141414]" /> Add New Disclosure Note
            </h4>
            <button
              type="button"
              onClick={() => setIsAddingNew(false)}
              className="text-[11px] text-[#5E5E5E] hover:text-[#141414] underline"
            >
              [CANCEL]
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-2">
              <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">Note Title *</label>
              <input
                type="text"
                placeholder="e.g. Insurance Claim for Fire Loss / Expansion Project Note"
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                required
                className="w-full bg-[#F4F3F0] border border-[#141414] p-1.5 text-xs font-semibold"
                id="input-new-note-title"
              />
            </div>

            <div>
              <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">Category</label>
              <select
                value={newCategory}
                onChange={e => setNewCategory(e.target.value as NoteCategory)}
                className="w-full bg-[#F4F3F0] border border-[#141414] p-1.5 text-xs"
                id="select-new-note-category"
              >
                <option value="CUSTOM">Custom Note</option>
                <option value="POLICIES">Accounting Policies</option>
                <option value="CAPITAL">Capital Disclosure</option>
                <option value="LOANS">Borrowings & Security</option>
                <option value="MSME">MSME Disclosures</option>
                <option value="RECEIVABLES_PAYABLES">Receivables & Payables</option>
                <option value="CONTINGENT">Contingent Liabilities</option>
                <option value="RELATED_PARTY">Related Party</option>
                <option value="STATUTORY">Statutory Disclosures</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-[10.5px] uppercase font-bold text-[#141414] mb-1">
              Note Text / Explanatory Content *
            </label>
            <textarea
              rows={4}
              value={newContent}
              onChange={e => setNewContent(e.target.value)}
              placeholder="Enter full note disclosure text..."
              required
              className="w-full bg-[#F4F3F0] border border-[#141414] p-2 text-xs font-mono leading-relaxed"
              id="textarea-new-note-content"
            />
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setIsAddingNew(false)}
              className="px-3 py-1 bg-white border border-[#141414] text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1 bg-[#141414] text-white text-xs font-bold hover:bg-[#2e2e2e]"
              id="btn-submit-new-note"
            >
              SAVE NOTE
            </button>
          </div>
        </form>
      )}

      {/* Notes List */}
      <div className="space-y-4">
        {filteredNotes.length === 0 ? (
          <div className="bg-white p-8 text-center text-[#5E5E5E] font-mono text-xs border border-[#141414]/20">
            No notes matching selected criteria. Click <strong>Reset Defaults</strong> or <strong>Add Note</strong>.
          </div>
        ) : (
          filteredNotes.map((note, idx) => {
            const isEditing = editingNoteId === note.id;

            return (
              <div
                key={note.id}
                className={`bg-white border transition shadow-xs ${
                  note.isActive ? 'border-[#141414]/30' : 'border-[#141414]/15 opacity-60 bg-[#F9F8F6]'
                }`}
                id={`note-card-${note.noteNumber}`}
              >
                {/* Note Card Header */}
                <div className="bg-[#ECEAE5] p-2.5 border-b border-[#141414]/20 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 bg-[#141414] text-white font-mono text-[10px] font-bold">
                      NOTE {note.noteNumber}
                    </span>
                    <h3 className="font-mono text-xs font-bold text-[#141414]">{note.title}</h3>
                    <span className="text-[9.5px] font-mono px-1.5 py-0.2 bg-white border border-[#141414]/20 text-[#5E5E5E]">
                      {note.category}
                    </span>
                    {!note.isActive && (
                      <span className="text-[9.5px] font-mono px-1.5 py-0.2 bg-[#fef2f2] border border-[#fca5a5] text-[#b91c1c] font-bold">
                        EXCLUDED
                      </span>
                    )}
                  </div>

                  {/* Actions Bar */}
                  <div className="flex items-center space-x-1 font-mono text-xs">
                    {/* Active/Exclude toggle */}
                    <button
                      onClick={() => handleToggleActive(note.id)}
                      className={`text-[10px] font-mono px-2 py-0.5 border transition ${
                        note.isActive
                          ? 'bg-[#dcfce7] text-[#166534] border-[#86efac]'
                          : 'bg-[#fee2e2] text-[#991b1b] border-[#fca5a5]'
                      }`}
                      title="Click to toggle whether this note is included in financial statements"
                    >
                      {note.isActive ? 'INCLUDED' : 'EXCLUDED'}
                    </button>

                    {/* Amend / Edit Button */}
                    <button
                      onClick={() => (isEditing ? setEditingNoteId(null) : handleStartEdit(note))}
                      className={`inline-flex items-center px-2 py-0.5 border text-[10px] transition ${
                        isEditing
                          ? 'bg-[#141414] text-white border-[#141414]'
                          : 'bg-white hover:bg-[#E4E3E0] text-[#141414] border-[#141414]/20'
                      }`}
                      id={`btn-edit-note-${note.noteNumber}`}
                    >
                      <Edit3 className="w-3 h-3 mr-1 text-[#2563eb]" />
                      {isEditing ? 'CANCEL EDIT' : 'AMEND'}
                    </button>

                    {/* Move Up/Down */}
                    <button
                      onClick={() => handleMoveUp(idx)}
                      disabled={idx === 0}
                      className="p-1 bg-white hover:bg-[#E4E3E0] text-[#5E5E5E] disabled:opacity-30 border border-[#141414]/20"
                      title="Move note up"
                    >
                      <ArrowUp className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleMoveDown(idx)}
                      disabled={idx === notes.length - 1}
                      className="p-1 bg-white hover:bg-[#E4E3E0] text-[#5E5E5E] disabled:opacity-30 border border-[#141414]/20"
                      title="Move note down"
                    >
                      <ArrowDown className="w-3 h-3" />
                    </button>

                    {/* Copy Text */}
                    <button
                      onClick={() => handleCopy(note.content, note.id)}
                      className="p-1 bg-white hover:bg-[#E4E3E0] text-[#5E5E5E] border border-[#141414]/20"
                      title="Copy note text to clipboard"
                    >
                      {copiedId === note.id ? <Check className="w-3 h-3 text-green-700" /> : <Copy className="w-3 h-3" />}
                    </button>

                    {/* Reset single note if standard */}
                    {note.isStandard && (
                      <button
                        onClick={() => handleResetSingleNote(note.id)}
                        className="p-1 bg-white hover:bg-[#E4E3E0] text-[#5E5E5E] border border-[#141414]/20"
                        title="Reset this note to default standard text"
                      >
                        <RefreshCw className="w-3 h-3" />
                      </button>
                    )}

                    {/* Delete Note */}
                    <button
                      onClick={() => handleDeleteNote(note.id)}
                      className="p-1 bg-white hover:bg-red-50 text-red-700 border border-[#141414]/20"
                      title="Delete note"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>

                {/* Card Body: Edit Mode vs View Mode */}
                <div className="p-4">
                  {isEditing ? (
                    <div className="space-y-3 font-mono text-xs">
                      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                        <div>
                          <label className="block text-[10px] uppercase font-bold text-[#5E5E5E] mb-1">Note No.</label>
                          <input
                            type="text"
                            value={draftNumber}
                            onChange={e => setDraftNumber(e.target.value)}
                            className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs font-bold"
                          />
                        </div>

                        <div className="sm:col-span-2">
                          <label className="block text-[10px] uppercase font-bold text-[#5E5E5E] mb-1">Title</label>
                          <input
                            type="text"
                            value={draftTitle}
                            onChange={e => setDraftTitle(e.target.value)}
                            className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs font-bold"
                          />
                        </div>

                        <div>
                          <label className="block text-[10px] uppercase font-bold text-[#5E5E5E] mb-1">Category</label>
                          <select
                            value={draftCategory}
                            onChange={e => setDraftCategory(e.target.value as NoteCategory)}
                            className="w-full bg-[#F4F3F0] border border-[#141414] p-1 text-xs"
                          >
                            <option value="POLICIES">Accounting Policies</option>
                            <option value="CAPITAL">Capital Disclosure</option>
                            <option value="LOANS">Borrowings & Security</option>
                            <option value="MSME">MSME Disclosures</option>
                            <option value="RECEIVABLES_PAYABLES">Receivables & Payables</option>
                            <option value="CONTINGENT">Contingent Liabilities</option>
                            <option value="RELATED_PARTY">Related Party</option>
                            <option value="STATUTORY">Statutory Disclosures</option>
                            <option value="CUSTOM">Custom Note</option>
                          </select>
                        </div>
                      </div>

                      {/* Helper insert chips */}
                      <div className="flex flex-wrap items-center gap-1.5 text-[10px] bg-[#F4F3F0] p-1.5 border border-[#141414]/15">
                        <span className="text-[#5E5E5E] font-bold">INSERT ENTITY TAGS:</span>
                        <button
                          type="button"
                          onClick={() => handleInsertVariable(entity.name)}
                          className="px-1.5 py-0.5 bg-white border border-[#141414]/20 hover:bg-[#ECEAE5] text-[#141414]"
                        >
                          + {entity.name}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleInsertVariable(entity.financialYear)}
                          className="px-1.5 py-0.5 bg-white border border-[#141414]/20 hover:bg-[#ECEAE5] text-[#141414]"
                        >
                          + FY {entity.financialYear}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleInsertVariable(entity.balanceSheetDate)}
                          className="px-1.5 py-0.5 bg-white border border-[#141414]/20 hover:bg-[#ECEAE5] text-[#141414]"
                        >
                          + {entity.balanceSheetDate}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleInsertVariable('₹ Nil')}
                          className="px-1.5 py-0.5 bg-white border border-[#141414]/20 hover:bg-[#ECEAE5] text-[#141414]"
                        >
                          + ₹ Nil
                        </button>
                      </div>

                      {/* Content Textarea */}
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-[#5E5E5E] mb-1">
                          Full Statutory Content / Disclosure Text
                        </label>
                        <textarea
                          rows={8}
                          value={draftContent}
                          onChange={e => setDraftContent(e.target.value)}
                          className="w-full bg-[#F4F3F0] border border-[#141414] p-2 text-xs font-mono leading-relaxed focus:bg-white"
                          id={`textarea-edit-note-${note.noteNumber}`}
                        />
                      </div>

                      <div className="flex items-center justify-between pt-1">
                        <span className="text-[10px] text-[#5E5E5E]">
                          Words: {draftContent.split(/\s+/).filter(Boolean).length} | Chars: {draftContent.length}
                        </span>
                        <div className="flex space-x-2">
                          <button
                            type="button"
                            onClick={() => setEditingNoteId(null)}
                            className="px-3 py-1 bg-white border border-[#141414] text-xs hover:bg-[#ECEAE5]"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSaveEdit(note.id)}
                            className="px-4 py-1 bg-[#141414] hover:bg-[#2e2e2e] text-white text-xs font-bold shadow-xs"
                            id={`btn-save-note-${note.noteNumber}`}
                          >
                            SAVE AMENDMENTS
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="prose max-w-none text-xs text-[#141414] leading-relaxed font-sans whitespace-pre-line">
                      {note.content}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Bottom Guidance Banner */}
      <div className="bg-[#ECEAE5] p-3 border border-[#141414]/20 text-xs font-mono text-[#5E5E5E] flex items-start space-x-2">
        <AlertCircle className="w-4 h-4 text-[#141414] shrink-0 mt-0.5" />
        <div>
          <p className="font-bold text-[#141414]">Compliance with ICAI Non-Corporate Reporting Framework:</p>
          <p className="mt-0.5 text-[11px] leading-relaxed">
            Non-corporate entities (Sole Proprietorships, Partnership Firms, LLPs) in India are classified as Level II, Level III, or Level IV enterprises under the ICAI Framework.
            These standard notes incorporate all mandatory statutory disclosures, including Depreciation (AS 10), Inventories (AS 2), Revenue (AS 9), Partner remuneration & interest u/s 40(b), MSMED Act 2006, and Related Party Disclosures (AS 18).
          </p>
        </div>
      </div>
    </div>
  );
};
