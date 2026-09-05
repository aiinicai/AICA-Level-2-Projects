import React, { useState, useRef, useEffect } from 'react';
import { Client, NoticeFormType } from '../types';
import { AnalysisResponse, EXTRACTION_PROMPT, parsePastedAnalysis } from '../services/aiService';
import {
  X, Upload, Sparkles, AlertTriangle, UserPlus, Eye, Cpu,
  ClipboardCopy, Check, FileText, ExternalLink,
} from 'lucide-react';

type Method = 'manual' | 'api';

interface NoticeIntakeModalProps {
  isOpen: boolean;
  onClose: () => void;
  allClients: Client[];
  selectedClientId: string;
  onAnalyzeOnly: (text: string, formTypeHint: string, pdfDataUrl?: string, pdfFileName?: string, forceLocal?: boolean) => Promise<AnalysisResponse>;
  onManualAnalysis: (analysis: AnalysisResponse, pdfDataUrl?: string, pdfFileName?: string) => void;
  onSaveAnalysis: (clientId: string, analysis: AnalysisResponse, pdfDataUrl?: string, pdfFileName?: string) => Promise<void>;
  onOpenAddClient: (onAdded: (newClientId: string) => void, prefill?: { legalName?: string; gstin?: string }) => void;
}

const FORM_TYPES: { value: NoticeFormType; label: string }[] = [
  { value: 'DRC-01', label: 'DRC-01 — Show Cause Notice (s.73/74)' },
  { value: 'DRC-01A', label: 'DRC-01A — Intimation of Tax Ascertained' },
  { value: 'ASMT-10', label: 'ASMT-10 — Scrutiny of Returns (s.61)' },
  { value: 'ADT-01', label: 'ADT-01 — Departmental Audit (s.65)' },
  { value: 'REG-17', label: 'REG-17 — Cancellation of Registration (s.29)' },
  { value: 'RFD-08', label: 'RFD-08 — Refund Rejection Notice' },
  { value: 'DRC-07', label: 'DRC-07 — Summary of Order' },
  { value: 'MOV-06', label: 'MOV-06 — E-Way Bill Detention (s.129)' },
  { value: 'SCN', label: 'General Show Cause Notice' },
];

export const NoticeIntakeModal: React.FC<NoticeIntakeModalProps> = ({
  isOpen,
  onClose,
  allClients,
  selectedClientId,
  onAnalyzeOnly,
  onManualAnalysis,
  onSaveAnalysis,
  onOpenAddClient,
}) => {
  const [clientId, setClientId] = useState(selectedClientId || allClients[0]?.id || '');
  const [method, setMethod] = useState<Method>('manual');
  const [formType, setFormType] = useState<NoticeFormType>('DRC-01');
  const [noticeText, setNoticeText] = useState('');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfDataUrl, setPdfDataUrl] = useState<string | undefined>();
  const [pastedResult, setPastedResult] = useState('');
  const [promptCopied, setPromptCopied] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [step, setStep] = useState<'input' | 'confirm'>('input');
  const [pendingPdfDataUrl, setPendingPdfDataUrl] = useState<string | undefined>();
  const [pendingAnalysis, setPendingAnalysis] = useState<AnalysisResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Keep the client selector in sync when the modal opens / clients change.
  useEffect(() => {
    if (isOpen) setClientId(selectedClientId || allClients[0]?.id || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, selectedClientId, allClients.length]);

  if (!isOpen) return null;

  const isPdf = !!pdfDataUrl;
  const hasTypedText = noticeText.trim() && !noticeText.startsWith('[Attached Document:');
  const hasInput = isPdf || hasTypedText;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPdfFile(file);
    setErrorMsg(null);
    const reader = new FileReader();

    if (file.type === 'application/pdf' || file.type.startsWith('image/')) {
      reader.onload = (ev) => {
        setPdfDataUrl(ev.target?.result as string);
        setNoticeText(`[Attached Document: ${file.name}]`);
      };
      reader.readAsDataURL(file);
    } else {
      reader.onload = (ev) => {
        setPdfDataUrl(undefined);
        setNoticeText((ev.target?.result as string) || '');
      };
      reader.readAsText(file);
    }
  };

  const buildManualPrompt = () => {
    const parts = [EXTRACTION_PROMPT];
    if (isPdf) {
      parts.push('\n\nThe GST notice is the PDF / image attached to this message. Read it and return only the JSON object.');
    } else {
      parts.push(`\n\nGST NOTICE TEXT TO ANALYSE:\n\n${noticeText.trim()}`);
    }
    return parts.join('');
  };

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(buildManualPrompt());
      setPromptCopied(true);
      setTimeout(() => setPromptCopied(false), 2500);
    } catch {
      setErrorMsg('Could not copy to clipboard. Select the prompt text manually.');
    }
  };

  const handleRunApi = async (forceOffline = false) => {
    if (!hasInput) {
      setErrorMsg('Upload a notice PDF/scan or paste the notice text first.');
      return;
    }
    setIsBusy(true);
    setErrorMsg(null);
    setPendingPdfDataUrl(pdfDataUrl);
    try {
      const analysis = await onAnalyzeOnly(noticeText, formType, pdfDataUrl, pdfFile?.name, forceOffline);
      setPendingAnalysis(analysis);
      setStep('confirm');
    } catch (err: any) {
      setErrorMsg(err.message || 'Error analysing notice.');
    } finally {
      setIsBusy(false);
    }
  };

  const handleLoadPasted = () => {
    if (!pastedResult.trim()) {
      setErrorMsg('Paste the JSON that Claude.ai returned.');
      return;
    }
    setIsBusy(true);
    setErrorMsg(null);
    try {
      const analysis = parsePastedAnalysis(pastedResult, hasTypedText ? noticeText.trim() : '');
      setPendingPdfDataUrl(pdfDataUrl);
      setPendingAnalysis(analysis);
      onManualAnalysis(analysis, pdfDataUrl, pdfFile?.name);
      setStep('confirm');
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not read the pasted result.');
    } finally {
      setIsBusy(false);
    }
  };

  // The taxpayer identified in the extracted notice, and the matching saved client (if any).
  const taxpayer = pendingAnalysis?.taxpayer;
  const matchedClient = taxpayer?.gstin
    ? allClients.find((c) => c.gstin?.trim().toUpperCase() === taxpayer.gstin)
    : undefined;
  const attachClientId = matchedClient?.id || (taxpayer?.gstin ? '' : clientId);

  const handleSaveToClient = async (targetId?: string) => {
    const id = targetId || attachClientId;
    if (!id) { setErrorMsg('This notice is not linked to a saved client yet — add the client first.'); return; }
    if (!pendingAnalysis) { setErrorMsg('Analysis result lost — please run it again.'); return; }
    setIsBusy(true);
    setErrorMsg(null);
    try {
      await onSaveAnalysis(id, pendingAnalysis, pendingPdfDataUrl, pdfFile?.name);
      handleClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Error saving to client.');
    } finally {
      setIsBusy(false);
    }
  };

  const handleAddClientFromNotice = () => {
    onOpenAddClient(
      (newId) => { setClientId(newId); handleSaveToClient(newId); },
      { legalName: taxpayer?.legalName, gstin: taxpayer?.gstin },
    );
  };

  const resetForm = () => {
    setStep('input');
    setNoticeText('');
    setPdfFile(null);
    setPdfDataUrl(undefined);
    setPastedResult('');
    setPendingPdfDataUrl(undefined);
    setPendingAnalysis(null);
    setErrorMsg(null);
    setMethod('manual');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleClose = () => {
    onClose();
    resetForm();
  };

  // ── CONFIRM STEP ───────────────────────────────────────────────
  if (step === 'confirm') {
    return (
      <Shell onClose={handleClose} title="Analysis ready" subtitle="Review it in the workspace, then attach it to a client.">
        <div className="p-6 space-y-4">
          <div className="flex items-start gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 p-3.5 text-xs text-emerald-800">
            <Check className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              The notice has been parsed and loaded into the <strong>Side-by-Side Analysis</strong> tab.
            </span>
          </div>

          <div className="space-y-2">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Taxpayer on this notice</div>

            {matchedClient ? (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5">
                <div className="text-sm font-bold text-slate-900">{matchedClient.legalName}</div>
                <div className="font-mono text-xs text-slate-500">{matchedClient.gstin}</div>
                <div className="mt-1.5 flex items-center gap-1 text-[11px] font-medium text-emerald-700">
                  <Check className="h-3.5 w-3.5" /> Matches a saved client — the notice will be added here.
                </div>
              </div>
            ) : taxpayer?.gstin ? (
              <div className="rounded-lg border border-amber-300 bg-amber-50 p-3.5">
                <div className="text-sm font-bold text-slate-900">{taxpayer.legalName || 'Taxpayer'}</div>
                <div className="font-mono text-xs text-slate-500">{taxpayer.gstin}</div>
                <div className="mt-1.5 text-[11px] text-amber-800">
                  Not a saved client yet. Add them to attach and save this notice.
                </div>
                <button
                  type="button"
                  onClick={handleAddClientFromNotice}
                  className="mt-2.5 flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-amber-700"
                >
                  <UserPlus className="h-3.5 w-3.5" /> Add “{taxpayer.legalName || taxpayer.gstin}” &amp; save
                </button>
              </div>
            ) : (
              <>
                <div className="text-[11px] text-slate-500">
                  No GSTIN was found in the notice — choose the client manually.
                </div>
                <div className="flex gap-2">
                  <select
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium focus:border-[#4338CA] focus:outline-none"
                  >
                    {allClients.length === 0 && <option value="">— No clients yet —</option>}
                    {allClients.map((c) => (
                      <option key={c.id} value={c.id}>{c.legalName} ({c.gstin})</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => onOpenAddClient((newId) => setClientId(newId))}
                    className="rounded-lg border border-[#4338CA] px-3 py-2 text-xs font-semibold text-[#4338CA] hover:bg-indigo-50"
                  >
                    + New
                  </button>
                </div>
              </>
            )}
          </div>

          {errorMsg && <ErrorNote>{errorMsg}</ErrorNote>}
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-4">
          <button
            type="button"
            onClick={handleClose}
            className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200"
          >
            <Eye className="h-3.5 w-3.5" /> Review without saving
          </button>
          <button
            type="button"
            disabled={isBusy || !attachClientId}
            onClick={() => handleSaveToClient()}
            className="flex items-center gap-2 rounded-lg bg-[#4338CA] px-5 py-2 text-xs font-semibold text-white hover:bg-[#3730A3] disabled:opacity-50"
          >
            {isBusy
              ? <><span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" /> Saving…</>
              : <><UserPlus className="h-4 w-4" /> Save to client record</>}
          </button>
        </div>
      </Shell>
    );
  }

  // ── INPUT STEP ─────────────────────────────────────────────────
  return (
    <Shell onClose={handleClose} title="Add a GST notice" subtitle="Upload the notice, extract the details, attach it to a client.">
      <div className="max-h-[62vh] space-y-5 overflow-y-auto p-6">

        {/* Method selector */}
        <div className="grid grid-cols-2 gap-2">
          <MethodCard
            active={method === 'manual'}
            onClick={() => { setMethod('manual'); setErrorMsg(null); }}
            title="Use Claude.ai"
            hint="Free with your subscription — copy a prompt, paste the result back"
          />
          <MethodCard
            active={method === 'api'}
            onClick={() => { setMethod('api'); setErrorMsg(null); }}
            title="Automatic"
            hint="One click — needs the workspace's Claude key configured on the server"
          />
        </div>

        {/* Form type */}
        <Field label="Notice form type">
          <select
            value={formType}
            onChange={(e) => setFormType(e.target.value as NoticeFormType)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium focus:border-[#4338CA] focus:outline-none"
          >
            {FORM_TYPES.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
          </select>
        </Field>

        {/* Upload */}
        <div
          onClick={() => fileInputRef.current?.click()}
          className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-5 text-center transition-colors hover:border-[#4338CA] hover:bg-indigo-50/40"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.doc,.docx,image/*"
            onChange={handleFileUpload}
            className="hidden"
          />
          <Upload className="mb-2 h-7 w-7 text-[#4338CA]" />
          <div className="text-xs font-semibold text-slate-800">
            {pdfFile ? `Selected: ${pdfFile.name}` : 'Upload notice PDF, scan, or image'}
          </div>
          <div className="mt-0.5 text-[11px] text-slate-500">Scanned PDF, JPG, PNG or DOCX</div>
        </div>

        <Field label="Or paste the notice text">
          <textarea
            rows={6}
            value={noticeText.startsWith('[Attached Document:') ? '' : noticeText}
            disabled={isPdf}
            onChange={(e) => setNoticeText(e.target.value)}
            placeholder={isPdf
              ? 'A document is attached — text box disabled. Remove the file to type instead.'
              : 'Paste the full notice text here…'}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs leading-relaxed focus:border-[#4338CA] focus:outline-none disabled:bg-slate-100 disabled:text-slate-400"
          />
        </Field>

        {/* ---- MANUAL METHOD ---- */}
        {method === 'manual' && (
          <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Extract with Claude.ai — no API cost
            </div>
            <ol className="space-y-1.5 text-xs text-slate-600">
              <li><strong>1.</strong> Copy the prompt below.</li>
              <li>
                <strong>2.</strong> Open{' '}
                <a href="https://claude.ai/new" target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 font-semibold text-[#4338CA] hover:underline">
                  claude.ai <ExternalLink className="h-3 w-3" />
                </a>
                {isPdf ? ', attach the same notice PDF, paste the prompt, send.' : ', paste the prompt, send.'}
              </li>
              <li><strong>3.</strong> Copy Claude's whole reply and paste it back below.</li>
            </ol>

            <button
              type="button"
              onClick={handleCopyPrompt}
              disabled={!hasInput}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-[#4338CA] bg-white px-4 py-2 text-xs font-semibold text-[#4338CA] hover:bg-indigo-50 disabled:opacity-50"
            >
              {promptCopied ? <><Check className="h-4 w-4" /> Prompt copied</> : <><ClipboardCopy className="h-4 w-4" /> Copy prompt for Claude.ai</>}
            </button>

            <Field label="Paste Claude's reply (the JSON block)">
              <textarea
                rows={5}
                value={pastedResult}
                onChange={(e) => setPastedResult(e.target.value)}
                placeholder='{ "noticeNumber": "...", "formType": "...", "issues": [ ... ] }'
                className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-[11px] leading-relaxed focus:border-[#4338CA] focus:outline-none"
              />
            </Field>
          </div>
        )}

        {/* ---- API METHOD ---- */}
        {method === 'api' && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-[11px] text-slate-600">
            Sends the notice to the server, which calls Claude and returns the details.
            If it reports that automatic extraction isn't configured, switch to <strong>Use Claude.ai</strong> above.
          </div>
        )}

        {errorMsg && <ErrorNote>{errorMsg}</ErrorNote>}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-4">
        <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
          {method === 'api'
            ? <><Cpu className="h-3.5 w-3.5 text-[#4338CA]" /> Claude API</>
            : <><FileText className="h-3.5 w-3.5 text-[#4338CA]" /> Claude.ai · manual</>}
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={handleClose} className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200">
            Cancel
          </button>
          {method === 'api' ? (
            <button
              type="button"
              disabled={isBusy || !hasInput}
              onClick={() => handleRunApi(false)}
              className="flex items-center gap-2 rounded-lg bg-[#4338CA] px-5 py-2 text-xs font-semibold text-white hover:bg-[#3730A3] disabled:opacity-50"
            >
              {isBusy
                ? <><span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" /> Analysing…</>
                : <><Sparkles className="h-4 w-4" /> Analyse with Claude</>}
            </button>
          ) : (
            <button
              type="button"
              disabled={isBusy || !pastedResult.trim()}
              onClick={handleLoadPasted}
              className="flex items-center gap-2 rounded-lg bg-[#4338CA] px-5 py-2 text-xs font-semibold text-white hover:bg-[#3730A3] disabled:opacity-50"
            >
              {isBusy
                ? <><span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" /> Loading…</>
                : <><Check className="h-4 w-4" /> Load pasted result</>}
            </button>
          )}
        </div>
      </div>
    </Shell>
  );
};

// ── Small presentational helpers ─────────────────────────────────
const Shell: React.FC<{ onClose: () => void; title: string; subtitle: string; children: React.ReactNode }> = ({
  onClose, title, subtitle, children,
}) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
    <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-indigo-50 p-2 text-[#4338CA]"><Sparkles className="h-5 w-5" /></div>
          <div>
            <h2 className="text-sm font-bold text-slate-900">{title}</h2>
            <p className="text-xs text-slate-500">{subtitle}</p>
          </div>
        </div>
        <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
          <X className="h-5 w-5" />
        </button>
      </div>
      {children}
    </div>
  </div>
);

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="space-y-1">
    <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</label>
    {children}
  </div>
);

const MethodCard: React.FC<{
  active: boolean; onClick: () => void; title: string; hint: string; disabled?: boolean;
}> = ({ active, onClick, title, hint, disabled }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    className={`rounded-lg border p-3 text-left transition-colors ${
      active
        ? 'border-[#4338CA] bg-indigo-50'
        : 'border-slate-200 bg-white hover:border-slate-300'
    } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
  >
    <div className={`text-xs font-bold ${active ? 'text-[#3730A3]' : 'text-slate-800'}`}>{title}</div>
    <div className="mt-0.5 text-[10px] leading-snug text-slate-500">{hint}</div>
  </button>
);

const ErrorNote: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
    <div>{children}</div>
  </div>
);
