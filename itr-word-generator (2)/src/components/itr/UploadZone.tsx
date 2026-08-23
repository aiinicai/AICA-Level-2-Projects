/**
 * UploadZone Component - ITR Computation Studio
 * Provides clean, robust file upload via Drag & Drop, File Dialog,
 * Optional Encrypted PDF password helper, AI/Local parser switch,
 * Raw Text/JSON paste modal, and 1-click standard Indian ITR sample templates.
 */

import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  Layers,
  Sparkles,
  Zap,
  FolderOpen,
  ClipboardPaste,
  PlusCircle,
  KeyRound,
  FileCheck,
  ShieldCheck,
  Info,
} from 'lucide-react';
import { SAMPLE_ITR_DATASETS } from '../../utils/itrParser';
import { CompleteITRData } from '../../itr-types';

interface UploadZoneProps {
  onFileSelected: (file: File, useAI: boolean, password?: string) => void;
  onSampleSelected: (sample: CompleteITRData) => void;
  onRawTextSubmitted: (text: string, useAI: boolean) => void;
  isProcessing: boolean;
  hasApiKey: boolean;
  activeFileName?: string;
  onBlankSelected?: () => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onFileSelected,
  onSampleSelected,
  onRawTextSubmitted,
  isProcessing,
  hasApiKey,
  activeFileName,
  onBlankSelected,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [useAI, setUseAI] = useState(hasApiKey);
  const [showTextInput, setShowTextInput] = useState(false);
  const [pastedText, setPastedText] = useState('');
  const [pdfPassword, setPdfPassword] = useState('');
  const [showPasswordBox, setShowPasswordBox] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (isProcessing) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      onFileSelected(file, hasApiKey && useAI, pdfPassword);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      onFileSelected(file, hasApiKey && useAI, pdfPassword);
      e.target.value = '';
    }
  };

  const triggerBrowse = (e?: React.MouseEvent) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handlePasteSubmit = () => {
    if (pastedText.trim()) {
      onRawTextSubmitted(pastedText.trim(), hasApiKey && useAI);
      setShowTextInput(false);
    }
  };

  return (
    <section className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5 flex flex-col gap-3.5 shadow-sm">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.json,.txt,.xml"
        className="hidden"
        onChange={handleFileInputChange}
        id="itr-hidden-file-input"
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <FolderOpen className="w-4 h-4 text-blue-600" />
          <span>1. Upload & Extract ITR</span>
        </h2>
        <span className="text-[10px] font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded font-semibold border border-slate-200">
          PDF / JSON / XML / TXT
        </span>
      </div>

      {/* Primary Action: Direct Browse Button */}
      <div className="space-y-2">
        <button
          type="button"
          id="main-browse-file-btn"
          onClick={(e) => triggerBrowse(e)}
          disabled={isProcessing}
          className="w-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold py-3 px-4 rounded-lg shadow-sm flex items-center justify-center gap-2 text-xs uppercase tracking-wider cursor-pointer transition-all disabled:opacity-50"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Browse & Choose ITR File</span>
        </button>

        {/* Native File Selector as Alternative fallback */}
        <div className="flex items-center gap-2">
          <label className="text-[11px] font-medium text-slate-500 shrink-0">
            Or select file:
          </label>
          <input
            type="file"
            id="itr-direct-browse-input"
            accept=".pdf,.json,.txt,.xml"
            onChange={handleFileInputChange}
            disabled={isProcessing}
            className="block w-full text-xs text-slate-600
              file:mr-2.5 file:py-1 file:px-2.5 file:rounded file:border-0
              file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-800
              hover:file:bg-slate-200 file:cursor-pointer
              cursor-pointer border border-slate-200 rounded bg-white p-1
              hover:border-blue-400 transition-all text-[11px]"
          />
        </div>
      </div>

      {/* Primary Dropzone */}
      <div
        id="itr-file-dropzone"
        role="button"
        tabIndex={0}
        onClick={(e) => triggerBrowse(e)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            triggerBrowse();
          }
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-4 text-center transition-all cursor-pointer select-none group ${
          isDragOver
            ? 'border-blue-500 bg-blue-50/80 scale-[1.01]'
            : 'border-slate-300 bg-slate-50/50 hover:border-blue-500 hover:bg-blue-50/20'
        } ${isProcessing ? 'pointer-events-none opacity-60' : ''}`}
      >
        <div className="flex flex-col items-center justify-center text-center space-y-1.5">
          <div className="w-9 h-9 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center group-hover:scale-105 transition-transform shadow-xs">
            <UploadCloud className="h-4 w-4 stroke-[2]" />
          </div>
          <div>
            <p className="text-xs font-bold text-slate-800">
              Drag & Drop Your ITR File Here
            </p>
            <p className="text-[10px] text-slate-500">
              Supports ITR-V Ack, ITR 1-4, Computation sheets & e-Filing JSON
            </p>
          </div>
        </div>
      </div>

      {/* Active File Banner (Only shows when a file is actually active) */}
      {activeFileName && (
        <div className="space-y-1.5 pt-0.5">
          <div className="flex items-center justify-between text-xs bg-blue-50 px-2.5 py-1.5 rounded border border-blue-200">
            <span className="text-slate-800 font-medium truncate max-w-[200px]" title={activeFileName}>
              Loaded: <strong>{activeFileName}</strong>
            </span>
            <span className="text-emerald-700 font-bold uppercase text-[10px] tracking-wider flex items-center gap-1 shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Active Return
            </span>
          </div>
        </div>
      )}

      {/* Optional PDF Password & AI Extraction Row */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
          <div className="flex items-center space-x-2">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            <span className="text-[11px] font-semibold text-slate-700">AI Extraction</span>
          </div>
          <div className="flex items-center space-x-2">
            {hasApiKey ? (
              <label className="relative inline-flex items-center cursor-pointer" title="Enable Gemini AI assisted extraction">
                <input
                  type="checkbox"
                  id="gemini-ai-toggle"
                  checked={useAI}
                  onChange={(e) => setUseAI(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-8 h-4 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            ) : (
              <span className="text-[10px] text-slate-400 italic">AI extraction unavailable</span>
            )}
            <button
              type="button"
              onClick={() => setShowPasswordBox(!showPasswordBox)}
              className={`text-[10px] font-semibold flex items-center gap-1 cursor-pointer px-1.5 py-0.5 rounded border transition-colors ${
                showPasswordBox || pdfPassword ? 'bg-amber-50 text-amber-800 border-amber-300' : 'bg-white text-slate-600 border-slate-200'
              }`}
            >
              <KeyRound className="w-3 h-3" />
              <span>{pdfPassword ? 'Password Set' : 'PDF Password'}</span>
            </button>
            <button
              type="button"
              onClick={() => setShowTextInput(!showTextInput)}
              className="text-[10px] font-semibold text-slate-600 hover:text-blue-600 underline cursor-pointer flex items-center gap-1"
            >
              <ClipboardPaste className="w-3 h-3" />
              <span>{showTextInput ? 'Hide Paste' : 'Paste Text'}</span>
            </button>
          </div>
        </div>

        {/* PDF Password Input Drawer */}
        {showPasswordBox && (
          <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-bold text-amber-900 text-[11px] flex items-center gap-1">
                <KeyRound className="w-3.5 h-3.5 text-amber-700" /> Password for Encrypted ITR-V PDF
              </span>
              <span className="text-[10px] text-amber-700 font-mono">Format: pan+ddmmyyyy</span>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={pdfPassword}
                onChange={(e) => setPdfPassword(e.target.value.toLowerCase())}
                placeholder="e.g. abcde1234f15081985"
                className="w-full text-xs font-mono px-2.5 py-1.5 rounded border border-amber-300 bg-white text-slate-900 focus:ring-1 focus:ring-amber-500"
              />
              {pdfPassword && (
                <button
                  type="button"
                  onClick={() => setPdfPassword('')}
                  className="text-[10px] px-2 py-1 text-slate-600 hover:bg-slate-200 rounded cursor-pointer"
                >
                  Clear
                </button>
              )}
            </div>
            <p className="text-[10px] text-amber-800 leading-tight">
              Official Income Tax portal PDFs are encrypted with PAN (in lowercase) + Assessee Date of Birth (DDMMYYYY).
            </p>
          </div>
        )}

        {/* Paste text area */}
        {showTextInput && (
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
            <textarea
              rows={4}
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder="Paste ITR-V Acknowledgment, Computation text, or e-filing JSON directly here..."
              className="w-full text-[11px] font-mono p-2 rounded border border-slate-300 bg-white text-slate-800 focus:ring-1 focus:ring-blue-500"
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowTextInput(false)}
                className="text-[10px] px-2 py-1 text-slate-600 hover:bg-slate-200 rounded cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!pastedText.trim() || isProcessing}
                onClick={handlePasteSubmit}
                className="text-[10px] font-bold px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded shadow-xs disabled:opacity-50 inline-flex items-center gap-1 cursor-pointer"
              >
                <Zap className="w-3 h-3" />
                <span>Parse Text / JSON</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Privacy Notice */}
      <div className="flex items-center gap-1.5 text-[11px] text-slate-500 bg-slate-50 p-2 rounded border border-slate-100">
        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
        <span>Local parsing available • AI extraction optional</span>
      </div>

      {/* 1-Click Sample Templates for instant testing */}
      <div className="space-y-2 pt-1 border-t border-slate-100">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
            <Layers className="w-3 h-3 text-blue-600" /> Test with Sample ITR Return
          </span>
          {onBlankSelected && (
            <button
              type="button"
              onClick={onBlankSelected}
              className="text-[10px] font-semibold text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1 cursor-pointer"
            >
              <PlusCircle className="w-3 h-3" />
              <span>New Blank</span>
            </button>
          )}
        </div>

        {/* 4 Standard Samples Grid */}
        <div className="grid grid-cols-2 gap-1.5">
          {SAMPLE_ITR_DATASETS.map((sample) => (
            <button
              key={sample.id}
              type="button"
              onClick={() => onSampleSelected(sample.data)}
              className="p-2 rounded border border-slate-200 bg-slate-50/80 hover:bg-blue-50 hover:border-blue-400 text-left transition-all text-[10px] cursor-pointer group shadow-2xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800 group-hover:text-blue-700 block truncate">
                  {sample.label.split(':')[0]}
                </span>
                <span className="text-[9px] font-semibold px-1.5 py-0.2 bg-blue-100/60 text-blue-800 rounded font-mono">
                  {sample.data.personalInfo.formType}
                </span>
              </div>
              <span className="text-slate-500 text-[9px] block truncate mt-0.5">
                {sample.label.split(':')[1]?.trim() || sample.desc}
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
};
