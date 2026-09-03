import React, { useRef, useState } from 'react';
import { SourceItem } from '../types';
import {
  Files,
  UploadCloud,
  FileText,
  FileSpreadsheet,
  FileCode,
  Image as ImageIcon,
  Eye,
  Edit3,
  Trash2,
  CheckSquare,
  Square,
  Loader2,
  Sparkles,
  Inbox
} from 'lucide-react';
import { parseFileToSourceItem } from '../utils/fileExtractor';

interface Props {
  sources: SourceItem[];
  selectedSourceIds: Set<string>;
  onToggleSelect: (id: string) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onAddSources: (newSources: SourceItem[]) => void;
  onViewSource: (source: SourceItem) => void;
  onRenameSource: (id: string, newName: string) => void;
  onDeleteSource: (id: string) => void;
}

export const SourceManagerPanel: React.FC<Props> = ({
  sources,
  selectedSourceIds,
  onToggleSelect,
  onSelectAll,
  onDeselectAll,
  onAddSources,
  onViewSource,
  onRenameSource,
  onDeleteSource,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const handleFiles = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setIsExtracting(true);
    const newItems: SourceItem[] = [];

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      try {
        const item = await parseFileToSourceItem(file);
        newItems.push(item);
      } catch (err) {
        console.error('Error extracting file:', file.name, err);
      }
    }

    if (newItems.length > 0) {
      onAddSources(newItems);
    }
    setIsExtracting(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const startRename = (source: SourceItem) => {
    setEditingId(source.id);
    setEditingName(source.name);
  };

  const saveRename = (id: string) => {
    if (editingName.trim()) {
      onRenameSource(id, editingName.trim());
    }
    setEditingId(null);
  };

  const getBadgeColor = (type: SourceItem['fileType']) => {
    switch (type) {
      case 'PDF':
        return 'bg-red-50 text-red-600 border-red-200';
      case 'DOCX':
        return 'bg-blue-50 text-blue-600 border-blue-200';
      case 'XLSX':
        return 'bg-emerald-50 text-emerald-600 border-emerald-200';
      case 'CSV':
        return 'bg-teal-50 text-teal-600 border-teal-200';
      case 'IMAGE':
        return 'bg-amber-50 text-amber-600 border-amber-200';
      case 'MD':
        return 'bg-purple-50 text-purple-600 border-purple-200';
      default:
        return 'bg-gray-50 text-gray-600 border-gray-200';
    }
  };

  const getFileIcon = (type: SourceItem['fileType']) => {
    switch (type) {
      case 'PDF':
      case 'DOCX':
        return <FileText className="w-3.5 h-3.5" />;
      case 'XLSX':
      case 'CSV':
        return <FileSpreadsheet className="w-3.5 h-3.5" />;
      case 'IMAGE':
        return <ImageIcon className="w-3.5 h-3.5" />;
      case 'MD':
        return <FileCode className="w-3.5 h-3.5" />;
      default:
        return <FileText className="w-3.5 h-3.5" />;
    }
  };

  const totalSelectedChars = sources
    .filter((s) => selectedSourceIds.has(s.id))
    .reduce((acc, curr) => acc + curr.charCount, 0);

  return (
    <section className="h-full flex flex-col bg-white select-none overflow-hidden">
      {/* Panel Header */}
      <div className="p-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Files className="w-4 h-4 text-blue-600" />
          <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Sources</h2>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-semibold font-mono">
            {sources.length}
          </span>
        </div>
        <div className="flex items-center space-x-2 text-xs">
          <button
            onClick={onSelectAll}
            className="text-blue-600 hover:text-blue-700 font-medium transition"
          >
            All
          </button>
          <span className="text-gray-300">•</span>
          <button
            onClick={onDeselectAll}
            className="text-gray-400 hover:text-gray-600 transition"
          >
            None
          </button>
        </div>
      </div>

      {/* Upload Source Button & Drag & Drop Target */}
      <div className="p-4 border-b border-gray-100">
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          className={`flex flex-col items-center justify-center p-3.5 border border-dashed rounded-xl cursor-pointer transition text-center ${
            isDragging
              ? 'border-blue-500 bg-blue-50/50'
              : 'border-gray-300 hover:border-blue-500/70 bg-gray-50/70 hover:bg-blue-50/20'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md,.png,.jpg,.jpeg"
            onChange={(e) => handleFiles(e.target.files)}
            className="hidden"
          />
          <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-1">
            <UploadCloud className="w-4 h-4" />
          </div>
          <p className="text-xs font-semibold text-gray-800">Upload Research Sources</p>
          <p className="text-[10px] text-gray-400 mt-0.5">PDF, DOCX, XLSX, CSV, PNG, TXT</p>
        </label>

        {isExtracting && (
          <div className="mt-2.5 text-xs text-blue-600 flex items-center justify-center gap-2 font-medium">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>Extracting document text...</span>
          </div>
        )}
      </div>

      {/* Sources List (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider px-1 mb-1">
          Active Sources ({selectedSourceIds.size})
        </h3>

        {sources.length === 0 ? (
          <div className="py-12 text-center text-gray-400 px-4">
            <Inbox className="w-8 h-8 mx-auto stroke-1 mb-2 text-gray-300" />
            <p className="text-xs font-medium text-gray-600">No sources uploaded</p>
            <p className="text-[11px] text-gray-400 mt-1">
              Add files to ground your local LM Studio assistant.
            </p>
          </div>
        ) : (
          sources.map((source) => {
            const isSelected = selectedSourceIds.has(source.id);
            const isEditing = editingId === source.id;

            return (
              <div
                key={source.id}
                className={`p-2.5 rounded-lg border transition-all ${
                  isSelected
                    ? 'bg-blue-50/70 border-blue-200 shadow-2xs'
                    : 'bg-white border-gray-100 hover:bg-gray-50 hover:border-gray-200'
                }`}
              >
                <div className="flex items-start gap-2.5">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => onToggleSelect(source.id)}
                    className="mt-1 rounded text-blue-600 focus:ring-blue-500 cursor-pointer h-4 w-4 border-gray-300"
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      {isEditing ? (
                        <input
                          type="text"
                          value={editingName}
                          autoFocus
                          onChange={(e) => setEditingName(e.target.value)}
                          onBlur={() => saveRename(source.id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveRename(source.id);
                            if (e.key === 'Escape') setEditingId(null);
                          }}
                          className="bg-white border border-blue-500 text-xs text-gray-900 px-1.5 py-0.5 rounded outline-none w-full"
                        />
                      ) : (
                        <span
                          onClick={() => onViewSource(source)}
                          className={`text-xs font-medium truncate cursor-pointer transition ${
                            isSelected ? 'text-blue-950 font-semibold hover:text-blue-700' : 'text-gray-700 hover:text-gray-900'
                          }`}
                          title={source.name}
                        >
                          {source.name}
                        </span>
                      )}

                      <span
                        className={`text-[9px] font-mono font-semibold uppercase px-1.5 py-0.5 rounded border flex items-center gap-1 shrink-0 ${getBadgeColor(
                          source.fileType
                        )}`}
                      >
                        {getFileIcon(source.fileType)}
                        <span>{source.fileType}</span>
                      </span>
                    </div>

                    {source.isGenerated && (
                      <div className="flex items-center gap-1 text-[9px] text-emerald-600 font-medium mt-0.5">
                        <Sparkles className="w-2.5 h-2.5" />
                        <span>Recursively generated</span>
                      </div>
                    )}

                    <p className={`text-[10px] line-clamp-1 mt-1 leading-relaxed ${
                      isSelected ? 'text-blue-600/80' : 'text-gray-400'
                    }`}>
                      {source.preview || 'No preview extracted'}
                    </p>

                    {/* Actions and Stats Bar */}
                    <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-gray-100 text-[10px] text-gray-400">
                      <span className="font-mono">{source.charCount.toLocaleString()} chars</span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => onViewSource(source)}
                          title="View Extracted Text"
                          className="p-1 rounded hover:bg-gray-100 hover:text-blue-600 transition text-gray-500"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => startRename(source)}
                          title="Rename Source"
                          className="p-1 rounded hover:bg-gray-100 hover:text-amber-600 transition text-gray-500"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => onDeleteSource(source.id)}
                          title="Delete Source"
                          className="p-1 rounded hover:bg-gray-100 hover:text-red-600 transition text-gray-500"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Sources Footer / Grounding Stats */}
      <div className="p-3.5 border-t border-gray-100 bg-[#f8f9fa] flex items-center justify-between text-xs text-gray-600">
        <span className="font-medium text-gray-700">
          {selectedSourceIds.size} of {sources.length} active
        </span>
        <span className="font-mono text-[10px] text-gray-400">
          {totalSelectedChars.toLocaleString()} chars in context
        </span>
      </div>
    </section>
  );
};
