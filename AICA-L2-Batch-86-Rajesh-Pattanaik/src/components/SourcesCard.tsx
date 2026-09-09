import React, { useRef, useState } from 'react';
import { BookOpen, Upload, RotateCcw, CheckCircle2, ShieldCheck } from 'lucide-react';

interface SourcesCardProps {
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
}

export const SourcesCard: React.FC<SourcesCardProps> = ({ value, onChange, disabled }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  const handleFile = (file: File) => {
    if (!file) return;

    setUploadStatus(`Reading "${file.name}"...`);

    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      if (content) {
        onChange(value ? `${value}\n\n--- [Uploaded Source: ${file.name}] ---\n${content}` : content);
        setUploadStatus(`Added "${file.name}" (${(file.size / 1024).toFixed(1)} KB)`);
        setTimeout(() => setUploadStatus(null), 3500);
      }
    };
    reader.onerror = () => {
      setUploadStatus(`Failed to read "${file.name}".`);
      setTimeout(() => setUploadStatus(null), 3500);
    };

    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-3.5 sm:p-4 flex flex-col justify-between transition-all">
      <div>
        <div className="flex items-center justify-between mb-1.5 flex-wrap gap-1">
          <label
            htmlFor="authoritative-sources-input"
            className="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5"
          >
            <span>③ Authoritative Research Sources</span>
            <span className="text-[10px] text-emerald-800 bg-emerald-50 border border-emerald-200 px-1.5 py-0.2 rounded font-semibold normal-case">
              Acts • Rules • Circulars • ICAI
            </span>
          </label>

          <div className="flex items-center gap-1.5">
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFile(e.target.files[0]);
                }
              }}
              accept=".txt,.md,.pdf,.json,.csv,.text"
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              className="text-[10px] font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 px-2.5 py-1 rounded-md flex items-center gap-1 cursor-pointer transition-colors"
              title="Upload text or reference document"
            >
              <Upload className="w-2.5 h-2.5 text-slate-600" />
              <span>Upload Source</span>
            </button>

            {value && !disabled && (
              <button
                type="button"
                onClick={() => onChange('')}
                className="text-[10px] font-semibold text-slate-400 hover:text-slate-700 flex items-center gap-1 cursor-pointer transition-colors ml-1"
                title="Clear sources"
              >
                <RotateCcw className="w-2.5 h-2.5" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>

        {uploadStatus && (
          <div className="mb-2 px-2.5 py-1 rounded bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span>{uploadStatus}</span>
          </div>
        )}

        {/* Drag & drop dropzone or paste area */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`relative rounded-lg transition-all ${
            dragOver ? 'ring-2 ring-emerald-500 bg-emerald-50/40' : ''
          }`}
        >
          <textarea
            id="authoritative-sources-input"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            placeholder="Paste statutory extracts (Acts, Rules, Notifications, Circulars, ICAI Guidance Notes) or drag & drop files here. (If omitted, a Limited Review is conducted)."
            rows={5}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400 focus:bg-white resize-y transition-all leading-relaxed"
          />
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between text-[11px] text-slate-500 pt-2 gap-1 font-medium">
        <div className="flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-emerald-600 shrink-0" />
          <span>Prefer Primary / Authoritative sources over secondary commentaries.</span>
        </div>
        <span className="text-slate-400 self-end sm:self-auto">{value.length} chars</span>
      </div>
    </div>
  );
};
