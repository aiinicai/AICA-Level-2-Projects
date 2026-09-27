/**
 * Hospital CFO Copilot — Agentic CFO Financial Review Modal
 *
 * Renders the explicit multi-stage orchestrator execution timeline.
 * Shows live stage progress, per-stage metadata (tools used, records, status),
 * the formatted 10-section briefing with output taxonomy badges,
 * and the Human-in-the-Loop approval workflow.
 *
 * RBAC:
 * - CFO: Run, Inspect, Regenerate, Approve
 * - Finance/Billing Manager: Run, Inspect, Regenerate (cannot Approve)
 * - Department Manager: Read-only institutional review access
 * - Auditor: Read-only access to approved reports
 */

import React, { useState } from 'react';
import {
  AlertTriangle,
  Award,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Database,
  Download,
  FileSpreadsheet,
  Loader2,
  MinusCircle,
  Printer,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  XCircle,
  X,
} from 'lucide-react';
import {
  CfoFinancialReviewBrief,
  CfoReviewProgress,
  UserSession,
  AgentStageStatus,
  StageExecutionRecord,
} from '../types';
import { STAGE_DEFINITIONS, TOTAL_STAGES } from '../services/cfoFinancialReviewAgent';
import { formatINR } from '../utils/formatters';
import {
  exportCfoReviewToPdf,
  exportCfoReviewToExcel,
} from '../utils/reportExportUtils';

interface CfoFinancialReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: UserSession;
  brief: CfoFinancialReviewBrief | null;
  isRunning: boolean;
  progress: CfoReviewProgress | null;
  onRegenerate: () => void;
  onApprove: (brief: CfoFinancialReviewBrief, approvalNotes?: string) => Promise<void>;
  onSelectEncounter?: (encounterId: string) => void;
  hasData?: boolean;
}

// ────────────────────────────────────────────────────────────────────────────
// Stage status icon / colour helpers
// ────────────────────────────────────────────────────────────────────────────

function StageStatusIcon({ status }: { status: AgentStageStatus }) {
  switch (status) {
    case 'COMPLETED':
      return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
    case 'NO_DATA':
      return <Database className="h-4 w-4 text-slate-400" />;
    case 'SKIPPED':
      return <MinusCircle className="h-4 w-4 text-slate-400" />;
    case 'ERROR':
      return <XCircle className="h-4 w-4 text-rose-500" />;
    case 'RUNNING':
      return <Loader2 className="h-4 w-4 text-teal-600 animate-spin" />;
    default: // PENDING
      return <Clock className="h-4 w-4 text-slate-300" />;
  }
}

function statusBadgeClass(status: AgentStageStatus): string {
  switch (status) {
    case 'COMPLETED': return 'bg-emerald-50 text-emerald-800 border-emerald-200';
    case 'NO_DATA':   return 'bg-slate-100 text-slate-600 border-slate-200';
    case 'SKIPPED':   return 'bg-slate-100 text-slate-500 border-slate-200';
    case 'ERROR':     return 'bg-rose-50 text-rose-700 border-rose-200';
    case 'RUNNING':   return 'bg-teal-50 text-teal-800 border-teal-200';
    default:          return 'bg-slate-50 text-slate-400 border-slate-200';
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Single Stage Card (collapsed / expanded)
// ────────────────────────────────────────────────────────────────────────────

function StageCard({ stage, stepNumber }: { stage: StageExecutionRecord; stepNumber: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`rounded-lg border transition-all ${
      stage.status === 'COMPLETED' ? 'border-emerald-200 bg-white' :
      stage.status === 'NO_DATA'   ? 'border-slate-200 bg-slate-50/50' :
      stage.status === 'RUNNING'   ? 'border-teal-300 bg-teal-50/30 shadow-sm' :
      stage.status === 'ERROR'     ? 'border-rose-200 bg-rose-50/30' :
                                     'border-slate-100 bg-slate-50/20'
    }`}>
      {/* Card header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-3.5 py-2.5 text-left cursor-pointer"
      >
        {/* Step number */}
        <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
          stage.status === 'COMPLETED' ? 'bg-emerald-100 text-emerald-800' :
          stage.status === 'RUNNING'   ? 'bg-teal-100 text-teal-800' :
          stage.status === 'NO_DATA'   ? 'bg-slate-200 text-slate-600' :
          stage.status === 'ERROR'     ? 'bg-rose-100 text-rose-700' :
                                         'bg-slate-100 text-slate-400'
        }`}>{stepNumber}</span>

        {/* Status icon */}
        <StageStatusIcon status={stage.status} />

        {/* Stage name */}
        <span className="flex-1 text-xs font-semibold text-slate-800">{stage.stageName}</span>

        {/* Status badge */}
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold border ${statusBadgeClass(stage.status)}`}>
          {stage.status}
        </span>

        {/* Expand toggle */}
        {expanded
          ? <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          : <ChevronRight className="h-3.5 w-3.5 text-slate-400" />}
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-3 pt-0 space-y-2 border-t border-slate-100">
          {/* Purpose */}
          <p className="text-[11px] text-slate-500 italic leading-relaxed mt-2">{stage.purpose}</p>

          {/* Metadata pills */}
          <div className="flex flex-wrap gap-2 text-[11px]">
            {stage.toolsUsed.length > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-100 font-mono">
                🔧 Tools: {stage.toolsUsed.join(', ')}
              </span>
            )}
            {stage.recordsProcessed > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                📋 {stage.recordsProcessed} records processed
              </span>
            )}
            {stage.metricsReturned > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-100">
                📊 {stage.metricsReturned} metrics returned
              </span>
            )}
          </div>

          {/* Finding */}
          <div className={`rounded p-2.5 text-[11px] leading-relaxed ${
            stage.status === 'NO_DATA' ? 'bg-slate-100 text-slate-600 border border-slate-200' :
            stage.status === 'ERROR'   ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                                          'bg-slate-50 text-slate-700 border border-slate-200'
          }`}>
            <span className="font-semibold text-slate-600 mr-1">
              {stage.status === 'NO_DATA' ? 'NO DATA:' : stage.status === 'ERROR' ? 'ERROR:' : 'Finding:'}
            </span>
            {stage.errorMessage || stage.finding}
          </div>

          {/* Evidence IDs */}
          {stage.evidenceIds.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              <span className="text-[10px] text-slate-500 font-semibold mr-1">Evidence refs:</span>
              {stage.evidenceIds.slice(0, 8).map((id) => (
                <span key={id} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-white text-teal-800 border border-teal-100 shadow-2xs">
                  {id}
                </span>
              ))}
              {stage.evidenceIds.length > 8 && (
                <span className="text-[10px] text-slate-400">+{stage.evidenceIds.length - 8} more</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Pending stage (not yet reached)
// ────────────────────────────────────────────────────────────────────────────

function PendingStageRow({ stepNumber, name }: { stepNumber: number; name: string }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50/20 flex items-center gap-3 px-3.5 py-2.5 opacity-50">
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold bg-slate-100 text-slate-400">{stepNumber}</span>
      <Clock className="h-4 w-4 text-slate-300" />
      <span className="text-xs text-slate-400">{name}</span>
      <span className="ml-auto inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold border bg-slate-50 text-slate-400 border-slate-200">PENDING</span>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Markdown renderer with output taxonomy badges
// ────────────────────────────────────────────────────────────────────────────

function renderFormattedMarkdown(
  markdown: string,
  onSelectEncounter?: (id: string) => void
) {
  const lines = markdown.split('\n');
  return lines.map((line, idx) => {
    if (line.startsWith('# ')) {
      return (
        <h1 key={idx} className="text-xl font-black text-slate-900 tracking-tight mt-2 mb-4 pb-2 border-b border-slate-200">
          {line.replace('# ', '')}
        </h1>
      );
    }
    if (line.startsWith('## ')) {
      return (
        <h2 key={idx} className="text-sm font-bold uppercase tracking-wider text-teal-900 mt-6 mb-2.5 pb-1 border-b border-teal-100 flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-teal-600 inline-block" />
          {line.replace('## ', '')}
        </h2>
      );
    }
    if (line.startsWith('### ')) {
      return (
        <h3 key={idx} className="text-xs font-bold text-slate-700 mt-4 mb-1.5 uppercase tracking-wider">
          {line.replace('### ', '')}
        </h3>
      );
    }
    if (line.startsWith('|')) {
      // Simple table row
      return (
        <div key={idx} className="font-mono text-[10px] text-slate-600 leading-relaxed border-b border-slate-100 py-0.5 px-1 overflow-x-auto">
          {line}
        </div>
      );
    }
    if (line.startsWith('> NO_DATA') || line.startsWith('> NO MATERIAL FINDING')) {
      return (
        <div key={idx} className="my-2 flex items-start gap-2 bg-slate-100 border border-slate-200 rounded-lg px-3 py-2">
          <Database className="h-3.5 w-3.5 text-slate-500 shrink-0 mt-0.5" />
          <span className="text-[11px] text-slate-600 italic">{line.replace(/^> /, '')}</span>
        </div>
      );
    }
    if (line.startsWith('> ')) {
      return (
        <blockquote key={idx} className="my-2 border-l-2 border-teal-400 bg-teal-50/50 p-2.5 rounded-r text-xs text-slate-700 italic">
          {line.replace('> ', '')}
        </blockquote>
      );
    }
    if (line.startsWith('- ')) {
      const text = line.replace('- ', '');
      let badge: React.ReactNode = null;
      let cleanText = text;

      if (text.includes('**[FACT]**')) {
        badge = <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200 mr-1.5">FACT</span>;
        cleanText = text.replace('**[FACT]**', '').trim();
      } else if (text.includes('**[CALCULATED METRIC]**')) {
        badge = <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-200 mr-1.5">CALCULATED METRIC</span>;
        cleanText = text.replace('**[CALCULATED METRIC]**', '').trim();
      } else if (text.includes('**[AI OBSERVATION]**')) {
        badge = <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200 mr-1.5">AI OBSERVATION</span>;
        cleanText = text.replace('**[AI OBSERVATION]**', '').trim();
      } else if (text.includes('**[SUGGESTED ACTION]**')) {
        badge = <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-200 mr-1.5">SUGGESTED ACTION</span>;
        cleanText = text.replace('**[SUGGESTED ACTION]**', '').trim();
      } else if (text.includes('**[CRITICAL]**')) {
        badge = <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-200 mr-1.5">CRITICAL</span>;
        cleanText = text.replace('**[CRITICAL]**', '').trim();
      } else if (text.includes('**[HIGH]**')) {
        badge = <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-orange-100 text-orange-800 border border-orange-200 mr-1.5">HIGH</span>;
        cleanText = text.replace('**[HIGH]**', '').trim();
      }

      const encounterMatch = cleanText.match(/ENC-\d+/);
      const encId = encounterMatch ? encounterMatch[0] : null;

      return (
        <li key={idx} className="text-xs text-slate-800 leading-relaxed my-1.5 list-none flex items-start gap-1">
          <span className="text-slate-400 mt-0.5 mr-0.5 shrink-0">•</span>
          <div>
            {badge}
            <span
              dangerouslySetInnerHTML={{
                __html: cleanText
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\*(.*?)\*/g, '<em>$1</em>')
                  .replace(/`([^`]+)`/g, '<code class="bg-slate-100 px-1 py-0.5 rounded font-mono text-[11px] text-teal-800">$1</code>'),
              }}
            />
            {encId && onSelectEncounter && (
              <button
                onClick={() => onSelectEncounter(encId)}
                className="ml-2 text-[10px] font-semibold text-teal-700 hover:text-teal-900 underline cursor-pointer"
              >
                Inspect {encId} →
              </button>
            )}
          </div>
        </li>
      );
    }
    if (!line.trim()) return <div key={idx} className="h-1.5" />;
    return (
      <p
        key={idx}
        className="text-xs text-slate-700 leading-relaxed my-1"
        dangerouslySetInnerHTML={{
          __html: line
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code class="bg-slate-100 px-1 py-0.5 rounded font-mono text-[11px] text-teal-800">$1</code>'),
        }}
      />
    );
  });
}

// ────────────────────────────────────────────────────────────────────────────
// Main Modal
// ────────────────────────────────────────────────────────────────────────────

export const CfoFinancialReviewModal: React.FC<CfoFinancialReviewModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  brief,
  isRunning,
  progress,
  onRegenerate,
  onApprove,
  onSelectEncounter,
  hasData,
}) => {
  const [isApproving, setIsApproving] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'briefing' | 'evidence'>('timeline');

  if (!isOpen) return null;

  const canApprove = currentUser.role === 'CFO';
  const canRegenerate = currentUser.role === 'CFO' || currentUser.role === 'Finance/Billing Manager';
  const isApproved = brief?.status === 'APPROVED';

  // Build live stage log from progress or completed brief
  const liveStageLog: StageExecutionRecord[] = progress?.stageLog ?? brief?.stageExecutionLog ?? [];
  const liveStageIds = new Set(liveStageLog.map((s) => s.stageId));
  const currentStep = progress?.step ?? (brief ? TOTAL_STAGES : 0);

  const handleConfirmApproval = async () => {
    if (!brief || !canApprove) return;
    setIsApproving(true);
    try {
      await onApprove(brief, approvalNotes);
      setShowApprovalDialog(false);
    } finally {
      setIsApproving(false);
    }
  };

  // Summary badges for completed brief
  const completedCount = brief?.stageExecutionLog.filter((s) => s.status === 'COMPLETED').length ?? 0;
  const noDataCount   = brief?.stageExecutionLog.filter((s) => s.status === 'NO_DATA').length ?? 0;
  const errorCount    = brief?.stageExecutionLog.filter((s) => s.status === 'ERROR').length ?? 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-3 sm:p-4 overflow-y-auto">
      <div className="relative w-full max-w-4xl max-h-[93vh] flex flex-col rounded-2xl bg-white shadow-2xl border border-slate-200 overflow-hidden">

        {/* ── Header ── */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 bg-slate-50/75 shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-600 text-white shadow-xs">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">CFO Financial Review</h2>
                {brief && (
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${
                    isApproved
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      : 'bg-amber-100 text-amber-900 border border-amber-300'
                  }`}>
                    {isApproved ? <><CheckCircle2 className="h-3 w-3" /> Approved</> : <><Clock className="h-3 w-3" /> Draft</>}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Objective: Identify material financial matters requiring CFO attention based on the latest available financial data.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {brief && !isRunning && (
              <>
                <button
                  onClick={() => exportCfoReviewToPdf(brief, currentUser)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-teal-200 bg-teal-50 hover:bg-teal-100 px-3 py-1.5 text-xs font-semibold text-teal-800 transition cursor-pointer"
                  title="Download officially formatted boardroom PDF dossier"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>Download PDF</span>
                </button>
                <button
                  onClick={() => exportCfoReviewToExcel(brief, currentUser)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-800 transition cursor-pointer"
                  title="Export multi-sheet Excel spreadsheet (.xlsx)"
                >
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                  <span>Export Excel</span>
                </button>
              </>
            )}
            <button
              onClick={() => window.print()}
              disabled={isRunning || !brief}
              className="hidden sm:inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition cursor-pointer disabled:opacity-40"
            >
              <Printer className="h-3.5 w-3.5" />
              <span className="hidden md:inline">Print</span>
            </button>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* ── Tabs (only show after brief is ready) ── */}
        {(isRunning || brief) && (
          <div className="flex gap-0 border-b border-slate-200 bg-slate-50/50 px-6 shrink-0">
            {(['timeline', 'briefing', 'evidence'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                disabled={tab !== 'timeline' && isRunning}
                className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition cursor-pointer disabled:opacity-40 ${
                  activeTab === tab
                    ? 'border-teal-600 text-teal-900'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                {tab === 'timeline' ? '📋 Execution Timeline' :
                 tab === 'briefing' ? '📄 CFO Briefing' :
                                     '🔗 Evidence Citations'}
              </button>
            ))}
          </div>
        )}

        {/* ── Body ── */}
        <div className="flex-1 overflow-y-auto px-6 py-5">

          {/* EMPTY / INITIAL STATE */}
          {!brief && !isRunning && (
            <div className="py-16 text-center space-y-4">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 border border-teal-200">
                <Sparkles className="h-7 w-7 text-teal-700" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  {hasData === false
                    ? 'Insufficient financial data for a CFO review.'
                    : 'Ready to Execute CFO Financial Review'}
                </h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 leading-relaxed">
                  {hasData === false
                    ? 'Upload your hospital financial extracts to begin analysis.'
                    : 'Runs 10 specialist financial review stages using deterministic controlled tools. All financial figures are grounded in application data.'}
                </p>
              </div>
              <div className="max-w-xs mx-auto text-left space-y-1">
                {STAGE_DEFINITIONS.map((def) => (
                  <div key={def.id} className="flex items-center gap-2 text-[11px] text-slate-500">
                    <span className="h-5 w-5 flex items-center justify-center rounded-full bg-slate-100 text-slate-400 text-[10px] font-bold shrink-0">{def.stepNumber}</span>
                    <span>{def.name}</span>
                    {def.tools.length > 0 && <span className="text-slate-300 font-mono text-[10px]">→ {def.tools.join(', ')}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* EXECUTION TIMELINE TAB */}
          {(isRunning || (brief && activeTab === 'timeline')) && (
            <div className="space-y-3">
              {/* Running header */}
              {isRunning && (
                <div className="rounded-xl border border-teal-200 bg-teal-50/40 p-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-teal-700" />
                    <span className="text-xs font-bold text-teal-900">Executing CFO Financial Review</span>
                  </div>
                  <span className="text-xs text-teal-700 font-semibold">
                    Stage {progress?.step ?? 1} of {TOTAL_STAGES}
                  </span>
                </div>
              )}

              {/* Completed summary bar (brief exists, not running) */}
              {brief && !isRunning && (
                <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 flex flex-wrap items-center gap-3 text-xs">
                  <span className="font-semibold text-slate-700">Review Complete</span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
                    <CheckCircle2 className="h-3 w-3" /> {completedCount} Completed
                  </span>
                  {noDataCount > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-semibold">
                      <Database className="h-3 w-3" /> {noDataCount} No Data
                    </span>
                  )}
                  {errorCount > 0 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 font-semibold">
                      <XCircle className="h-3 w-3" /> {errorCount} Error
                    </span>
                  )}
                  <span className="text-slate-400 ml-auto">
                    Run ID: <code className="font-mono text-teal-800 font-bold">{brief.runId}</code>
                  </span>
                </div>
              )}

              {/* Stage cards */}
              <div className="space-y-2">
                {STAGE_DEFINITIONS.map((def) => {
                  const record = liveStageLog.find((s) => s.stageId === def.id);
                  if (record) {
                    return <StageCard key={def.id} stage={record} stepNumber={def.stepNumber} />;
                  }
                  // Currently running
                  if (isRunning && def.stepNumber === currentStep && !liveStageIds.has(def.id)) {
                    return (
                      <div key={def.id} className="rounded-lg border border-teal-300 bg-teal-50/40 flex items-center gap-3 px-3.5 py-2.5">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold bg-teal-100 text-teal-800">{def.stepNumber}</span>
                        <Loader2 className="h-4 w-4 text-teal-600 animate-spin" />
                        <span className="text-xs font-semibold text-teal-800">{def.name}</span>
                        <span className="ml-auto inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold border bg-teal-50 text-teal-800 border-teal-200">RUNNING</span>
                      </div>
                    );
                  }
                  return <PendingStageRow key={def.id} stepNumber={def.stepNumber} name={def.name} />;
                })}
              </div>
            </div>
          )}

          {/* CFO BRIEFING TAB */}
          {brief && !isRunning && activeTab === 'briefing' && (
            <div className="space-y-4">
              {/* Attribution bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 text-xs">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold border ${
                    brief.narrativeSource === 'ai_gemini'
                      ? 'bg-purple-50 text-purple-900 border-purple-200'
                      : 'bg-slate-100 text-slate-800 border-slate-300'
                  }`}>
                    <Sparkles className="h-3 w-3" />
                    {brief.narrativeSource === 'ai_gemini' ? 'AI-Synthesized via Gemini' : 'Deterministic Executive Briefing'}
                  </span>
                  <span className="text-slate-400">•</span>
                  <span className="text-slate-600">Generated: {new Date(brief.generatedAt).toLocaleString('en-IN')}</span>
                  <span className="text-slate-400">•</span>
                  <span className="text-slate-600">By: {brief.generatedBy} ({brief.userRole})</span>
                </div>
                {isApproved && brief.approvedBy && (
                  <div className="flex items-center gap-1 text-emerald-800 font-semibold bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                    <span>Approved by {brief.approvedBy} ({new Date(brief.approvedAt || '').toLocaleString('en-IN')})</span>
                  </div>
                )}
              </div>

              {/* Draft warning */}
              {!isApproved && (
                <div className="rounded-xl border border-amber-300 bg-amber-50/60 p-4 flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-700 shrink-0 mt-0.5" />
                  <div className="text-xs text-amber-950 space-y-1">
                    <div className="font-bold text-amber-900 text-sm">Draft — Awaiting CFO Review & Approval</div>
                    <p className="leading-relaxed">
                      This briefing was produced by {TOTAL_STAGES} specialist review stages using deterministic financial controls (C01–C08), AR ageing registers and TPA claims data.
                      In accordance with hospital governance bylaws, institutional sign-off requires human CFO verification before adoption.
                    </p>
                  </div>
                </div>
              )}

              {/* Briefing body */}
              <div className="prose prose-slate max-w-none bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-2">
                {renderFormattedMarkdown(brief.markdownContent, onSelectEncounter)}
              </div>
            </div>
          )}

          {/* EVIDENCE CITATIONS TAB */}
          {brief && !isRunning && activeTab === 'evidence' && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <ShieldCheck className="h-4 w-4 text-teal-600" />
                    Verified Evidence Citations ({brief.evidenceReferences.length} records)
                  </h3>
                  <span className="text-[11px] text-slate-500">
                    Tools: {brief.toolsUsed.join(', ')}
                  </span>
                </div>

                {brief.evidenceReferences.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No evidence references — run review with financial data loaded.</p>
                ) : (
                  <div className="space-y-2">
                    {(['EXCEPTION', 'ENCOUNTER', 'CLAIM', 'CONTROL', 'METRIC'] as const).map((type) => {
                      const refs = brief.evidenceReferences.filter((r) => r.type === type);
                      if (refs.length === 0) return null;
                      return (
                        <div key={type}>
                          <div className="text-[10px] font-bold uppercase text-slate-500 mb-1.5">{type}S ({refs.length})</div>
                          <div className="flex flex-wrap gap-1.5">
                            {refs.map((ref, i) => (
                              <span
                                key={i}
                                title={ref.detail || ref.id}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-white text-slate-700 border border-slate-200 shadow-2xs cursor-default"
                              >
                                <span className="text-teal-700 font-bold">[{ref.type}]</span>
                                <span>{ref.id}</span>
                                {ref.detail && <span className="text-slate-400 text-[10px] hidden sm:inline"> — {ref.detail.slice(0, 30)}</span>}
                              </span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Stage → evidence map */}
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">Stage Evidence Map</h3>
                <div className="space-y-1.5">
                  {brief.stageExecutionLog.map((stage) => (
                    <div key={stage.stageId} className="flex items-start gap-3 text-xs py-1.5 border-b border-slate-50 last:border-0">
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold border shrink-0 ${statusBadgeClass(stage.status)}`}>
                        {stage.status}
                      </span>
                      <span className="font-semibold text-slate-800 min-w-[140px] shrink-0">{stage.stageName}</span>
                      <div className="flex flex-wrap gap-1">
                        {stage.evidenceIds.length === 0 ? (
                          <span className="text-slate-400 text-[11px] italic">No evidence refs</span>
                        ) : stage.evidenceIds.slice(0, 6).map((id) => (
                          <span key={id} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-50 text-teal-800 border border-slate-200">{id}</span>
                        ))}
                        {stage.evidenceIds.length > 6 && <span className="text-[10px] text-slate-400">+{stage.evidenceIds.length - 6}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="border-t border-slate-200 px-6 py-4 bg-slate-50/75 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="text-xs text-slate-500 flex items-center gap-2">
            <span>Role: <strong>{currentUser.role}</strong></span>
            {!canApprove && (
              <span className="text-amber-800 text-[11px] font-medium bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                ℹ️ Approval authority restricted to Chief Financial Officer
              </span>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            {canRegenerate && brief && (
              <button
                onClick={onRegenerate}
                disabled={isRunning}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-2xs transition cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isRunning ? 'animate-spin' : ''}`} />
                Regenerate
              </button>
            )}

            {!brief && (
              <button
                onClick={onRegenerate}
                disabled={isRunning || hasData === false}
                title={hasData === false ? 'Upload hospital financial extracts to execute review' : undefined}
                className="inline-flex items-center gap-2 rounded-lg bg-teal-700 hover:bg-teal-800 px-5 py-2 text-xs font-bold text-white shadow-xs transition active:scale-95 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isRunning ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /><span>Executing Workflow...</span></>
                ) : (
                  <><Sparkles className="h-4 w-4" /><span>Run CFO Financial Review</span></>
                )}
              </button>
            )}

            {brief && !isApproved && canApprove && (
              <button
                onClick={() => setShowApprovalDialog(true)}
                disabled={isRunning || isApproving}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 px-4 py-2 text-xs font-bold text-white shadow-xs transition active:scale-95 cursor-pointer disabled:opacity-50"
              >
                <CheckCircle2 className="h-4 w-4" />
                Approve Briefing
              </button>
            )}

            {brief && isApproved && (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Official Approved Briefing
              </span>
            )}
          </div>
        </div>

        {/* ── CFO Approval Dialog ── */}
        {showApprovalDialog && (
          <div className="absolute inset-0 z-60 flex items-center justify-center bg-slate-900/40 p-4">
            <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <ShieldCheck className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Approve CFO Financial Briefing</h3>
                  <p className="text-xs text-slate-500">Governance Sign-Off & Official Dossier Filing</p>
                </div>
              </div>

              <div className="text-xs text-slate-600 space-y-2 bg-slate-50 p-3 rounded-lg border border-slate-200">
                <p>As <strong>{currentUser.name} (CFO)</strong>, you are certifying that you have reviewed the deterministic evidence, financial exposure items, AR ageing schedules and specialist stage outputs.</p>
                <p className="text-slate-500 text-[11px]">
                  Approval records an immutable event in the institutional audit log (<code className="font-mono text-teal-800">CFO_REVIEW_APPROVED</code>) and stores this briefing in the corporate governance register.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Optional CFO Sign-Off Commentary:</label>
                <textarea
                  rows={2}
                  value={approvalNotes}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setApprovalNotes(e.target.value)}
                  placeholder="e.g., Reviewed with Inpatient Billing Lead; priority recovery assigned for Q3 close."
                  className="w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-800 focus:outline-teal-600 focus:ring-1 focus:ring-teal-600"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  onClick={() => setShowApprovalDialog(false)}
                  disabled={isApproving}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmApproval}
                  disabled={isApproving}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 px-4 py-1.5 text-xs font-bold text-white transition cursor-pointer disabled:opacity-50"
                >
                  {isApproving ? (
                    <><Loader2 className="h-3.5 w-3.5 animate-spin" /><span>Filing Approval...</span></>
                  ) : (
                    <><Award className="h-3.5 w-3.5" /><span>Confirm & File Approval</span></>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
