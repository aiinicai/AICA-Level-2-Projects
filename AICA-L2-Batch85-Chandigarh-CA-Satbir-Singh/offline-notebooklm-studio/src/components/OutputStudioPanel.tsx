import React, { useState, useRef, useEffect } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { StudioNote, SourceItem, ArtifactType } from '../types';
import {
  FileText,
  HelpCircle,
  Table as TableIcon,
  BookOpen,
  MoreVertical,
  Share2,
  Edit3,
  Repeat,
  Download,
  Clock,
  Trash2,
  Plus,
  ArrowLeft,
  Copy,
  Check,
  Eye,
  Edit,
  Heading,
  List,
  Quote,
  Sparkles,
  Presentation,
  CheckCircle2,
  FileCode,
  StickyNote
} from 'lucide-react';
import confetti from 'canvas-confetti';

interface Props {
  notes: StudioNote[];
  activeNoteId: string | null;
  sources: SourceItem[];
  selectedSourceIds: Set<string>;
  onSelectNote: (id: string | null) => void;
  onAddNote: (note: Partial<StudioNote>) => void;
  onUpdateNote: (id: string, updates: Partial<StudioNote>) => void;
  onDeleteNote: (id: string) => void;
  onConvertToSource: (note: StudioNote) => void;
  onExportDocx: (content: string, title: string) => Promise<void>;
  onExportPptx: (content: string, title: string) => Promise<void>;
  onOpenReportModal: () => void;
  onOpenQuizModal: () => void;
  onOpenDataTableModal: () => void;
  onViewPromptAndSources: (note: StudioNote) => void;
  isGeneratingArtifact?: boolean;
}

export const OutputStudioPanel: React.FC<Props> = ({
  notes,
  activeNoteId,
  sources,
  selectedSourceIds,
  onSelectNote,
  onAddNote,
  onUpdateNote,
  onDeleteNote,
  onConvertToSource,
  onExportDocx,
  onExportPptx,
  onOpenReportModal,
  onOpenQuizModal,
  onOpenDataTableModal,
  onViewPromptAndSources,
  isGeneratingArtifact = false,
}) => {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [renamingNoteId, setRenamingNoteId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit');
  const [copied, setCopied] = useState(false);
  const [shareToast, setShareToast] = useState(false);
  const [downloadMenuNoteId, setDownloadMenuNoteId] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  const activeNote = notes.find((n) => n.id === activeNoteId) || null;

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenuId(null);
        setDownloadMenuNoteId(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const formatTimeAgo = (dateStr: string) => {
    try {
      const diffMs = Date.now() - new Date(dateStr).getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      if (diffDays <= 0) return 'Today';
      if (diffDays === 1) return '1d ago';
      if (diffDays < 30) return `${diffDays}d ago`;
      if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
      return `${diffDays}d ago`;
    } catch {
      return 'Recently';
    }
  };

  const handleStartRename = (note: StudioNote, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingNoteId(note.id);
    setRenameValue(note.title);
    setOpenMenuId(null);
  };

  const handleSaveRename = (id: string) => {
    if (renameValue.trim()) {
      onUpdateNote(id, { title: renameValue.trim(), updatedAt: new Date().toISOString() });
    }
    setRenamingNoteId(null);
  };

  const handleShare = (note: StudioNote, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(`# ${note.title}\n\n${note.content}`);
    setOpenMenuId(null);
    setShareToast(true);
    setTimeout(() => setShareToast(false), 2500);
  };

  const handleConvert = (note: StudioNote, e: React.MouseEvent) => {
    e.stopPropagation();
    confetti({
      particleCount: 60,
      spread: 55,
      origin: { y: 0.8 },
      colors: ['#38bdf8', '#34d399', '#818cf8'],
    });
    onConvertToSource(note);
    setOpenMenuId(null);
  };

  const handleDownloadDocx = async (note: StudioNote, e: React.MouseEvent) => {
    e.stopPropagation();
    await onExportDocx(note.content, note.title);
    setOpenMenuId(null);
    setDownloadMenuNoteId(null);
  };

  const handleDownloadPptx = async (note: StudioNote, e: React.MouseEvent) => {
    e.stopPropagation();
    await onExportPptx(note.content, note.title);
    setOpenMenuId(null);
    setDownloadMenuNoteId(null);
  };

  const handleDownloadMd = (note: StudioNote, e: React.MouseEvent) => {
    e.stopPropagation();
    const blob = new Blob([note.content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${note.title.replace(/[^a-zA-Z0-9_-]/g, '_')}.md`;
    a.click();
    URL.revokeObjectURL(url);
    setOpenMenuId(null);
    setDownloadMenuNoteId(null);
  };

  const handleCopyNoteContent = () => {
    if (activeNote) {
      navigator.clipboard.writeText(activeNote.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const insertSnippet = (prefix: string, suffix: string = '') => {
    if (!activeNote) return;
    const textarea = document.getElementById('note-editor-textarea') as HTMLTextAreaElement | null;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = activeNote.content.substring(start, end) || 'text';
    const replacement = `${prefix}${selected}${suffix}`;
    const updated = activeNote.content.substring(0, start) + replacement + activeNote.content.substring(end);
    onUpdateNote(activeNote.id, { content: updated, updatedAt: new Date().toISOString() });
  };

  const getNoteIcon = (type: ArtifactType) => {
    switch (type) {
      case 'report':
        return <FileText className="w-4 h-4 text-amber-600" />;
      case 'quiz':
        return <HelpCircle className="w-4 h-4 text-sky-600" />;
      case 'datatable':
        return <TableIcon className="w-4 h-4 text-indigo-600" />;
      case 'study_guide':
        return <BookOpen className="w-4 h-4 text-purple-600" />;
      default:
        return <StickyNote className="w-4 h-4 text-gray-600" />;
    }
  };

  // If a note is currently opened in Detail / Editor Mode:
  if (activeNote) {
    const wordCount = activeNote.content.trim() ? activeNote.content.trim().split(/\s+/).length : 0;
    const charCount = activeNote.content.length;

    return (
      <section className="h-full flex flex-col bg-[#fafafa] overflow-hidden select-none">
        {/* Editor Top Navigation Header */}
        <div className="p-3.5 border-b border-gray-200 bg-white flex items-center justify-between">
          <div className="flex items-center space-x-2 min-w-0">
            <button
              onClick={() => onSelectNote(null)}
              className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-600 hover:text-gray-900 transition flex items-center gap-1 text-xs font-semibold"
              title="Back to Studio Notes"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Studio</span>
            </button>
            <div className="h-4 w-px bg-gray-200" />
            <div className="flex items-center space-x-1.5 min-w-0">
              {getNoteIcon(activeNote.type)}
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                {activeNote.type.replace('_', ' ')}
              </span>
            </div>
          </div>

          {/* View Toggle */}
          <div className="flex items-center bg-gray-100 p-0.5 rounded-lg border border-gray-200 text-xs">
            <button
              onClick={() => setViewMode('edit')}
              className={`px-2.5 py-1 rounded-md flex items-center gap-1 font-medium transition ${
                viewMode === 'edit'
                  ? 'bg-white text-gray-900 shadow-2xs font-semibold'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              <Edit className="w-3 h-3" />
              <span>Edit</span>
            </button>
            <button
              onClick={() => setViewMode('preview')}
              className={`px-2.5 py-1 rounded-md flex items-center gap-1 font-medium transition ${
                viewMode === 'preview'
                  ? 'bg-white text-gray-900 shadow-2xs font-semibold'
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              <Eye className="w-3 h-3" />
              <span>Preview</span>
            </button>
          </div>
        </div>

        {/* Note Title & Action Bar */}
        <div className="p-4 border-b border-gray-100 bg-white space-y-3">
          <div className="flex items-center justify-between gap-2">
            <input
              type="text"
              value={activeNote.title}
              onChange={(e) => onUpdateNote(activeNote.id, { title: e.target.value, updatedAt: new Date().toISOString() })}
              placeholder="Note title..."
              className="flex-1 font-semibold text-sm text-gray-900 bg-transparent border-b border-transparent hover:border-gray-200 focus:border-blue-500 focus:outline-none py-0.5 px-1 rounded transition"
            />
            <span className="text-[11px] text-gray-400 shrink-0 font-sans">
              {activeNote.sourcesCount || 0} source(s)
            </span>
          </div>

          {/* Quick Actions Row */}
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={(e) => handleConvert(activeNote, e)}
              className="flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-xs font-semibold shadow-2xs transition"
              title="Convert to Grounded Source in Left Panel"
            >
              <Repeat className="w-3.5 h-3.5" />
              <span className="truncate">To Source</span>
            </button>

            <button
              onClick={(e) => handleDownloadDocx(activeNote, e)}
              className="flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 text-xs font-semibold shadow-2xs transition"
              title="Download Word Document"
            >
              <FileText className="w-3.5 h-3.5 text-blue-600" />
              <span className="truncate">Word (.docx)</span>
            </button>

            <button
              onClick={(e) => handleDownloadPptx(activeNote, e)}
              className="flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white hover:bg-gray-50 text-gray-700 border border-gray-200 text-xs font-semibold shadow-2xs transition"
              title="Download PowerPoint Presentation"
            >
              <Presentation className="w-3.5 h-3.5 text-amber-600" />
              <span className="truncate">Slides (.pptx)</span>
            </button>
          </div>
        </div>

        {/* Formatting Snippets Bar (in edit mode) */}
        {viewMode === 'edit' && (
          <div className="px-4 py-1.5 border-b border-gray-100 bg-gray-50 flex items-center gap-1 text-xs text-gray-500 overflow-x-auto">
            <button
              onClick={() => insertSnippet('## ')}
              className="p-1 rounded hover:bg-gray-200 hover:text-gray-800 transition"
              title="Heading 2"
            >
              <Heading className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => insertSnippet('- ')}
              className="p-1 rounded hover:bg-gray-200 hover:text-gray-800 transition"
              title="Bullet Point"
            >
              <List className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => insertSnippet('> ')}
              className="p-1 rounded hover:bg-gray-200 hover:text-gray-800 transition"
              title="Quote Block"
            >
              <Quote className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => insertSnippet('**', '**')}
              className="px-1.5 py-0.5 rounded hover:bg-gray-200 hover:text-gray-800 font-bold transition"
              title="Bold"
            >
              B
            </button>
            <button
              onClick={() => insertSnippet('`', '`')}
              className="px-1.5 py-0.5 rounded hover:bg-gray-200 hover:text-gray-800 font-mono transition"
              title="Inline Code"
            >
              &lt;/&gt;
            </button>
          </div>
        )}

        {/* Editor & Preview Area */}
        <div className="flex-1 relative overflow-hidden bg-white">
          {viewMode === 'edit' ? (
            <textarea
              id="note-editor-textarea"
              value={activeNote.content}
              onChange={(e) => onUpdateNote(activeNote.id, { content: e.target.value, updatedAt: new Date().toISOString() })}
              placeholder="Write your note or structured synthesis here..."
              className="w-full h-full p-4 bg-transparent text-xs font-mono text-gray-800 placeholder-gray-400 focus:outline-none resize-none leading-relaxed"
            />
          ) : (
            <div className="w-full h-full p-5 overflow-y-auto text-xs leading-relaxed text-gray-800 space-y-3 select-text">
              <h1 className="text-base font-bold text-gray-900 pb-2 border-b border-gray-200">
                {activeNote.title}
              </h1>
              <div className="prose prose-sm max-w-none font-sans text-xs text-gray-800 leading-relaxed space-y-2">
                {activeNote.content ? (
                  <Markdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      table: ({ children }) => (
                        <div className="my-3 overflow-x-auto rounded-xl border border-gray-200 shadow-2xs bg-white">
                          <table className="w-full text-left border-collapse text-xs">
                            {children}
                          </table>
                        </div>
                      ),
                      thead: ({ children }) => (
                        <thead className="bg-[#f8f9fa] border-b border-gray-200 font-semibold text-gray-900">
                          {children}
                        </thead>
                      ),
                      tbody: ({ children }) => (
                        <tbody className="divide-y divide-gray-100 bg-white">
                          {children}
                        </tbody>
                      ),
                      tr: ({ children }) => (
                        <tr className="hover:bg-blue-50/30 transition">{children}</tr>
                      ),
                      th: ({ children }) => (
                        <th className="px-3.5 py-2 font-semibold text-gray-900 text-xs border-r border-gray-200 last:border-r-0 whitespace-nowrap bg-gray-50/80">
                          {children}
                        </th>
                      ),
                      td: ({ children }) => (
                        <td className="px-3.5 py-2 text-gray-700 text-xs border-r border-gray-100 last:border-r-0 align-top leading-relaxed">
                          {children}
                        </td>
                      ),
                    }}
                  >
                    {activeNote.content}
                  </Markdown>
                ) : (
                  <span className="text-gray-400 italic">Empty note.</span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-gray-100 bg-[#f8f9fa] text-xs text-gray-500 flex items-center justify-between">
          <span className="font-mono text-[11px]">
            {wordCount.toLocaleString()} words • {charCount.toLocaleString()} chars
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onViewPromptAndSources(activeNote)}
              className="hover:text-gray-900 flex items-center gap-1 transition font-medium text-[11px] text-gray-500 mr-2"
            >
              <Clock className="w-3 h-3" />
              <span>Prompt & Sources</span>
            </button>
            <button
              onClick={handleCopyNoteContent}
              className="hover:text-gray-900 flex items-center gap-1 transition font-medium text-xs text-gray-700"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>
      </section>
    );
  }

  // Primary Studio View (matching screenshot notebook.png)
  return (
    <section className="h-full flex flex-col bg-[#fafafa] overflow-hidden select-none relative">
      {/* Studio Header */}
      <div className="p-4 border-b border-gray-100 bg-white flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Studio</h2>
          </div>
        </div>
        <span className="text-[11px] font-medium text-gray-400">
          {notes.length} item{notes.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Main Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-20">
        {/* Quick Generation Tiles Grid (Reports, Quiz, Data Table) */}
        <div className="grid grid-cols-3 gap-2">
          {/* Reports Card */}
          <button
            onClick={onOpenReportModal}
            disabled={isGeneratingArtifact || sources.length === 0}
            className="flex flex-col items-start p-2.5 rounded-xl bg-[#fff8e1] hover:bg-[#ffecb3] text-[#b78103] transition border border-[#ffe082] shadow-2xs text-left group disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            title="Generate customized or structured reports"
          >
            <div className="w-6 h-6 rounded-lg bg-white/90 flex items-center justify-center mb-1.5 shadow-2xs">
              <FileText className="w-3.5 h-3.5 text-[#f57f17]" />
            </div>
            <span className="text-xs font-semibold leading-tight text-gray-900">Reports</span>
            <span className="text-[10px] text-amber-700 mt-0.5 opacity-90 truncate w-full">Format & styles</span>
          </button>

          {/* Quiz Card */}
          <button
            onClick={onOpenQuizModal}
            disabled={isGeneratingArtifact || sources.length === 0}
            className="flex flex-col items-start p-2.5 rounded-xl bg-[#e1f5fe] hover:bg-[#b3e5fc] text-[#0277bd] transition border border-[#b3e5fc] shadow-2xs text-left group disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            title="Create customized knowledge assessment quiz"
          >
            <div className="w-6 h-6 rounded-lg bg-white/90 flex items-center justify-center mb-1.5 shadow-2xs">
              <HelpCircle className="w-3.5 h-3.5 text-[#0288d1]" />
            </div>
            <span className="text-xs font-semibold leading-tight text-gray-900">Quiz</span>
            <span className="text-[10px] text-sky-700 mt-0.5 opacity-90 truncate w-full">Assessments</span>
          </button>

          {/* Data Table Card */}
          <button
            onClick={onOpenDataTableModal}
            disabled={isGeneratingArtifact || sources.length === 0}
            className="flex flex-col items-start p-2.5 rounded-xl bg-[#ede7f6] hover:bg-[#d1c4e9] text-[#4527a0] transition border border-[#d1c4e9] shadow-2xs text-left group disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            title="Customize and extract structured data tables"
          >
            <div className="w-6 h-6 rounded-lg bg-white/90 flex items-center justify-center mb-1.5 shadow-2xs">
              <TableIcon className="w-3.5 h-3.5 text-[#5e35b1]" />
            </div>
            <span className="text-xs font-semibold leading-tight text-gray-900">Data Table</span>
            <span className="text-[10px] text-purple-700 mt-0.5 opacity-90 truncate w-full">Metrics & tables</span>
          </button>
        </div>

        {/* Notes & Artifacts List */}
        <div className="space-y-1.5 pt-2">
          {notes.map((note) => (
            <div
              key={note.id}
              onClick={() => onSelectNote(note.id)}
              className="group relative flex items-center justify-between p-3 rounded-xl bg-white hover:bg-gray-50 border border-gray-200/80 hover:border-gray-300 shadow-2xs cursor-pointer transition"
            >
              <div className="flex items-center space-x-3 min-w-0 flex-1 pr-2">
                {/* Note Icon Container */}
                <div className="w-8 h-8 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center shrink-0">
                  {getNoteIcon(note.type)}
                </div>

                {/* Note Title & Subtitle */}
                <div className="min-w-0 flex-1">
                  {renamingNoteId === note.id ? (
                    <input
                      type="text"
                      value={renameValue}
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onBlur={() => handleSaveRename(note.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveRename(note.id);
                        if (e.key === 'Escape') setRenamingNoteId(null);
                      }}
                      className="w-full text-xs font-semibold text-gray-900 border-b border-blue-500 bg-transparent focus:outline-none"
                    />
                  ) : (
                    <h4 className="text-xs font-semibold text-gray-900 truncate group-hover:text-blue-600 transition">
                      {note.title}
                    </h4>
                  )}
                  <p className="text-[11px] text-gray-400 mt-0.5 flex items-center gap-1.5 truncate">
                    <span>{note.sourcesCount || 0} source{note.sourcesCount !== 1 ? 's' : ''}</span>
                    <span>•</span>
                    <span>{formatTimeAgo(note.createdAt)}</span>
                  </p>
                </div>
              </div>

              {/* Three dots context menu button */}
              <div className="relative shrink-0" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={() => setOpenMenuId(openMenuId === note.id ? null : note.id)}
                  className="p-1 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition"
                  title="Note options"
                >
                  <MoreVertical className="w-4 h-4" />
                </button>

                {/* Popover Dropdown Menu (Exact list from screenshot) */}
                {openMenuId === note.id && (
                  <div
                    ref={menuRef}
                    className="absolute right-0 top-7 z-30 w-52 bg-white rounded-xl shadow-xl border border-gray-200 py-1.5 text-xs text-gray-700 animate-in fade-in zoom-in-95 duration-100"
                  >
                    {/* Share */}
                    <button
                      onClick={(e) => handleShare(note, e)}
                      className="w-full px-3.5 py-2 flex items-center gap-2.5 hover:bg-gray-50 text-left font-medium text-gray-700 transition"
                    >
                      <Share2 className="w-4 h-4 text-gray-500" />
                      <span>Share</span>
                    </button>

                    {/* Rename */}
                    <button
                      onClick={(e) => handleStartRename(note, e)}
                      className="w-full px-3.5 py-2 flex items-center gap-2.5 hover:bg-gray-50 text-left font-medium text-gray-700 transition"
                    >
                      <Edit3 className="w-4 h-4 text-gray-500" />
                      <span>Rename</span>
                    </button>

                    {/* Convert to source */}
                    <button
                      onClick={(e) => handleConvert(note, e)}
                      className="w-full px-3.5 py-2 flex items-center gap-2.5 hover:bg-gray-50 text-left font-medium text-gray-700 transition"
                    >
                      <Repeat className="w-4 h-4 text-gray-500" />
                      <span>Convert to source</span>
                    </button>

                    {/* Download (with suboptions) */}
                    <div className="relative">
                      <button
                        onClick={() => setDownloadMenuNoteId(downloadMenuNoteId === note.id ? null : note.id)}
                        className="w-full px-3.5 py-2 flex items-center justify-between hover:bg-gray-50 text-left font-medium text-gray-700 transition"
                      >
                        <div className="flex items-center gap-2.5">
                          <Download className="w-4 h-4 text-gray-500" />
                          <span>Download</span>
                        </div>
                        <span className="text-[10px] text-gray-400">›</span>
                      </button>

                      {downloadMenuNoteId === note.id && (
                        <div className="bg-gray-50 border-y border-gray-100 py-1 px-1 space-y-0.5">
                          <button
                            onClick={(e) => handleDownloadDocx(note, e)}
                            className="w-full px-4 py-1.5 text-left text-[11px] font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-200/60 rounded flex items-center gap-2"
                          >
                            <FileText className="w-3 h-3 text-blue-600" />
                            <span>Word (.docx)</span>
                          </button>
                          <button
                            onClick={(e) => handleDownloadPptx(note, e)}
                            className="w-full px-4 py-1.5 text-left text-[11px] font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-200/60 rounded flex items-center gap-2"
                          >
                            <Presentation className="w-3 h-3 text-amber-600" />
                            <span>PowerPoint (.pptx)</span>
                          </button>
                          <button
                            onClick={(e) => handleDownloadMd(note, e)}
                            className="w-full px-4 py-1.5 text-left text-[11px] font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-200/60 rounded flex items-center gap-2"
                          >
                            <FileCode className="w-3 h-3 text-emerald-600" />
                            <span>Markdown (.md)</span>
                          </button>
                        </div>
                      )}
                    </div>

                    {/* View prompt and sources */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(null);
                        onViewPromptAndSources(note);
                      }}
                      className="w-full px-3.5 py-2 flex items-center gap-2.5 hover:bg-gray-50 text-left font-medium text-gray-700 transition"
                    >
                      <Clock className="w-4 h-4 text-gray-500" />
                      <span>View prompt and sources</span>
                    </button>

                    <div className="h-px bg-gray-100 my-1" />

                    {/* Delete */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteNote(note.id);
                        setOpenMenuId(null);
                      }}
                      className="w-full px-3.5 py-2 flex items-center gap-2.5 hover:bg-red-50 text-red-600 text-left font-medium transition"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                      <span>Delete</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Centered Bottom Action Pill: "+ Add note" (as seen in screenshot) */}
      <div className="absolute bottom-4 left-0 right-0 flex justify-center pointer-events-none z-10">
        <button
          onClick={() => {
            const newNote: Partial<StudioNote> = {
              title: `Note ${notes.length + 1}`,
              content: `# Note ${notes.length + 1}\n\nDraft your notes or click "Send to Report" from Grounded Chat.`,
              type: 'note',
              sourcesCount: selectedSourceIds.size,
              sourceNames: sources.filter((s) => selectedSourceIds.has(s.id)).map((s) => s.name),
              createdAt: new Date().toISOString(),
            };
            onAddNote(newNote);
          }}
          className="pointer-events-auto flex items-center gap-2 px-5 py-2.5 rounded-full bg-black text-white text-xs font-semibold shadow-lg hover:bg-gray-800 active:scale-95 transition"
        >
          <StickyNote className="w-3.5 h-3.5 text-white" />
          <span>Add note</span>
        </button>
      </div>

      {/* Share Toast */}
      {shareToast && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-40 px-3.5 py-1.5 bg-gray-900 text-white rounded-full text-xs font-medium shadow-md flex items-center gap-1.5 animate-in fade-in slide-in-from-top-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Note markdown copied to clipboard</span>
        </div>
      )}
    </section>
  );
};
