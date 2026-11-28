import React, { useState } from 'react';
import { CheckCircle2, Download, FileSpreadsheet, FileText, Lock, Presentation, ShieldCheck, Upload } from 'lucide-react';
import {
  formatMoney,
  reconcileTrialBalance,
  type ExecutiveCommentaryBundle,
  type FinancialStatements,
  type ProjectKpiSummary,
  type ReconciliationResult,
} from '../engine/kpiEngine';
import {
  downloadUploadTemplate,
  exportBoardPowerPoint,
  exportMisExcelPack,
  exportMisPdfPack,
  parseTrialBalanceFile,
  UPLOAD_TEMPLATES,
} from '../utils/exportEngine';
import type {
  AccountClass,
  AccountingPolicyConfig,
  CurrencyCode,
  MisDataset,
  ReportingBasis,
  TrialBalanceRow,
  UserRole,
  WorkflowStage,
} from '../types/mis';

export const AiAnalystView: React.FC<{
  dataset: MisDataset;
  statements: FinancialStatements;
  projectKpis: ProjectKpiSummary[];
  commentary: ExecutiveCommentaryBundle;
  selectedPeriod: string;
}> = ({ statements, projectKpis, commentary, selectedPeriod }) => {
  const [question, setQuestion] = useState('');
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const askOnlineAi = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setAiError(null);
    try {
      const verifiedContext = {
        period: selectedPeriod,
        consolidatedStatementsOMR: statements,
        projects: projectKpis.map((p) => ({
          code: p.project.code,
          name: p.project.name,
          gdvOMR: p.gdvOMR,
          contractedSalesOMR: p.contractedSalesOMR,
          collectedOMR: p.collectedOMR,
          overdueReceivablesOMR: p.overdueReceivablesOMR,
          forecastFinalCostEAC: p.forecastFinalCostEAC,
          costOverrunVsRevisedOMR: p.costOverrunVsRevisedOMR,
          physicalProgressPct: p.physicalProgressPct,
          spi: p.spi,
          cpi: p.cpi,
        })),
      };
      const res = await fetch('/api/ai/commentary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() || undefined, verifiedContext }),
      });
      const data = (await res.json()) as { commentary?: string; error?: string };
      if (!res.ok) {
        setAiError(data.error || 'Online AI request failed.');
      } else {
        setAiResponse(data.commentary ?? '');
      }
    } catch (err) {
      setAiError(err instanceof Error ? err.message : 'Network error calling AI endpoint.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          AI & Rule-Based Management Analyst
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          All figures are computed strictly by the verified KPI engine; AI never fabricates numbers and distinguishes confirmed facts from hypotheses.
        </p>
      </div>

      {/* Offline Deterministic CFO Engine */}
      <div className="rounded-lg border p-5 space-y-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="flex items-center justify-between">
          <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
            Offline Verified Rule-Based CFO Commentary ({selectedPeriod})
          </h3>
          <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">100% Offline Capable</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 text-xs" style={{ color: 'var(--re-text-muted)' }}>
          <div className="space-y-2">
            <div className="font-semibold" style={{ color: 'var(--re-text)' }}>Executive Summary</div>
            <ul className="space-y-1.5 list-disc pl-4">
              {commentary.executiveSummary.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
            <div className="font-semibold pt-2" style={{ color: 'var(--re-text)' }}>Financial Highlights</div>
            <ul className="space-y-1.5 list-disc pl-4">
              {commentary.financialHighlights.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </div>
          <div className="space-y-2">
            <div className="font-semibold" style={{ color: 'var(--re-text)' }}>Board Questions</div>
            <ul className="space-y-1.5 list-disc pl-4">
              {commentary.managementQuestions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ul>
            <div className="font-semibold pt-2" style={{ color: 'var(--re-text)' }}>Management Action Plan</div>
            <div className="space-y-2">
              {commentary.actionPlan.map((a, i) => (
                <div key={i} className="p-2.5 rounded border" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
                  <div className="font-medium" style={{ color: 'var(--re-text)' }}>{a.action}</div>
                  <div className="mt-0.5 text-[11px]">{a.owner} · Due {a.deadline} · Priority: {a.priority}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Optional Online Gemini Analyst */}
      <div className="rounded-lg border p-5 space-y-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
          Optional Online Gemini Management Analyst (Grounded in Verified KPIs)
        </h3>
        <form onSubmit={askOnlineAi} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask e.g.: Which project drives the highest cash risk next quarter and what corrective action is needed?"
            className="flex-1 px-3 py-2 rounded-lg border text-xs"
            style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 rounded-lg text-xs font-medium whitespace-nowrap disabled:opacity-50"
            style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
          >
            {loading ? 'Analyzing Verified KPIs...' : 'Generate Online AI Brief'}
          </button>
        </form>
        {aiError && (
          <div className="p-3 rounded border text-xs text-amber-700 dark:text-amber-300" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
            {aiError}
          </div>
        )}
        {aiResponse && (
          <div className="p-4 rounded border text-xs whitespace-pre-wrap leading-relaxed" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)', color: 'var(--re-text)' }}>
            {aiResponse}
          </div>
        )}
      </div>
    </div>
  );
};

export const DataUploadView: React.FC<{
  dataset: MisDataset;
  selectedPeriod: string;
  companyFilterId: string | 'CONSOLIDATED';
  authToken: string | null;
  onDatasetUpdated: (ds: MisDataset) => void;
}> = ({ dataset, selectedPeriod, companyFilterId, authToken, onDatasetUpdated }) => {
  const [targetCompanyId, setTargetCompanyId] = useState(
    companyFilterId === 'CONSOLIDATED' ? dataset.companies[0].id : companyFilterId
  );
  const [previewRows, setPreviewRows] = useState<TrialBalanceRow[]>([]);
  const [detectedCols, setDetectedCols] = useState<Record<string, string>>({});
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [unmappedToFix, setUnmappedToFix] = useState<TrialBalanceRow[]>([]);

  const handleFile = async (file: File) => {
    const existingMap = new Map<string, TrialBalanceRow['accountClass']>();
    for (const m of dataset.glMappings) {
      existingMap.set(m.accountCode, m.targetClass);
    }
    const parsed = await parseTrialBalanceFile(file, targetCompanyId, selectedPeriod, existingMap);
    setDetectedCols(parsed.detectedColumns);
    setPreviewRows(parsed.rows);
    setUnmappedToFix(parsed.rows.filter((r) => r.accountClass === 'Unmapped'));
    setStatusMsg(`Parsed ${parsed.rows.length} rows from ${file.name}. Verify balance and save to SQLite.`);
  };

  const commitUpload = async () => {
    if (!authToken || previewRows.length === 0) return;
    const res = await fetch('/api/upload/trial-balance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({ companyId: targetCompanyId, period: selectedPeriod, rows: previewRows }),
    });
    const data = (await res.json()) as { dataset?: MisDataset; error?: string };
    if (res.ok && data.dataset) {
      onDatasetUpdated(data.dataset);
      setStatusMsg(`Saved ${previewRows.length} Trial Balance rows for ${selectedPeriod} into SQLite.`);
    } else {
      setStatusMsg(data.error || 'Upload commit failed.');
    }
  };

  const saveMapping = async (row: TrialBalanceRow, targetClass: AccountClass) => {
    if (!authToken) return;
    const res = await fetch('/api/mappings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        id: `map-${row.accountCode}`,
        accountCode: row.accountCode,
        accountNamePattern: row.accountName,
        targetClass,
        defaultProjectId: row.projectId,
        allocationRule: 'Saved Wizard Rule',
      }),
    });
    const data = (await res.json()) as { dataset?: MisDataset };
    if (res.ok && data.dataset) {
      onDatasetUpdated(data.dataset);
      setPreviewRows((prev) => prev.map((r) => (r.accountCode === row.accountCode ? { ...r, accountClass: targetClass } : r)));
      setUnmappedToFix((prev) => prev.filter((r) => r.accountCode !== row.accountCode));
      setStatusMsg(`Mapped GL account ${row.accountCode} → ${targetClass} (remembered for future months).`);
    }
  };

  const previewRec =
    previewRows.length > 0
      ? reconcileTrialBalance(previewRows, [], dataset.glMappings, dataset.policies.materialityThresholdOMR)
      : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            Smart Data Upload Centre & GL Mapping Wizard
          </h2>
          <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
            Drag-and-drop Excel (.xlsx) or CSV Trial Balances with auto-column detection, validation, and reusable GL rules
          </p>
        </div>
        <select
          aria-label="Target entity for TB upload"
          value={targetCompanyId}
          onChange={(e) => setTargetCompanyId(e.target.value)}
          className="px-3 py-1.5 rounded-lg border text-xs"
          style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
        >
          {dataset.companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.code} — {c.name}
            </option>
          ))}
        </select>
      </div>

      {/* Dropzone */}
      <label
        className="block rounded-lg border-2 border-dashed p-8 text-center cursor-pointer transition-colors"
        style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) void handleFile(f);
        }}
      >
        <Upload className="w-7 h-7 mx-auto mb-2" style={{ color: 'var(--re-accent)' }} />
        <div className="text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
          Drop ERP Trial Balance or Schedule (.xlsx, .xls, .csv)
        </div>
        <div className="text-xs mt-1" style={{ color: 'var(--re-text-muted)' }}>
          Or click to browse local files · Target Period: {selectedPeriod}
        </div>
        <input
          type="file"
          accept=".xlsx,.xls,.csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleFile(f);
          }}
        />
      </label>

      {statusMsg && (
        <div className="p-3 rounded-lg border text-xs font-medium" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}>
          {statusMsg}
        </div>
      )}

      {previewRec && (
        <div className="rounded-lg border p-5 space-y-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
                Upload Validation & Reconciliation Preview
              </h3>
              <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
                Period Dr: {previewRec.totalPeriodDebit.toFixed(3)} · Period Cr: {previewRec.totalPeriodCredit.toFixed(3)} · Diff: {previewRec.trialBalanceDiff.toFixed(3)} OMR · Detected Cols: {Object.values(detectedCols).filter(Boolean).length}
              </p>
            </div>
            <button
              type="button"
              onClick={commitUpload}
              className="px-4 py-2 rounded-lg text-xs font-medium"
              style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
            >
              Commit Trial Balance to Period {selectedPeriod}
            </button>
          </div>

          {unmappedToFix.length > 0 && (
            <div className="space-y-2 border-t pt-3" style={{ borderColor: 'var(--re-border)' }}>
              <div className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                GL Mapping Wizard: {unmappedToFix.length} unmapped account(s) detected
              </div>
              {unmappedToFix.map((row) => (
                <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 text-xs py-1">
                  <span>{row.accountCode} — {row.accountName}</span>
                  <select
                    aria-label={`Map account ${row.accountCode}`}
                    defaultValue=""
                    onChange={(e) => {
                      if (e.target.value) void saveMapping(row, e.target.value as AccountClass);
                    }}
                    className="px-2 py-1 rounded border text-xs"
                    style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
                  >
                    <option value="">Assign Account Class...</option>
                    <option value="Revenue">Revenue</option>
                    <option value="COGS">COGS</option>
                    <option value="OpEx">OpEx</option>
                    <option value="CashUnrestricted">Cash Unrestricted</option>
                    <option value="CashEscrow">Cash Escrow</option>
                    <option value="Receivables">Receivables</option>
                    <option value="InventoryWIP">Inventory & WIP</option>
                    <option value="Payables">Payables</option>
                    <option value="CustomerAdvances">Customer Advances</option>
                    <option value="Debt">Debt</option>
                  </select>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 11 Downloadable Excel Templates */}
      <div className="rounded-lg border overflow-hidden" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="p-4 border-b" style={{ borderColor: 'var(--re-border)' }}>
          <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
            Standardized Excel Upload Templates (11 Schedules)
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 p-4">
          {UPLOAD_TEMPLATES.map((tpl) => (
            <div key={tpl.id} className="p-3 rounded-lg border flex flex-col justify-between gap-3" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
              <div>
                <div className="text-xs font-semibold" style={{ color: 'var(--re-text)' }}>{tpl.name}</div>
                <div className="text-[11px] mt-1" style={{ color: 'var(--re-text-muted)' }}>{tpl.description}</div>
              </div>
              <button
                type="button"
                onClick={() => downloadUploadTemplate(tpl.id)}
                className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded border text-xs font-medium"
                style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
              >
                <Download className="w-3.5 h-3.5" /> Download .xlsx
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export const WorkflowControlsView: React.FC<{
  dataset: MisDataset;
  reconciliation: ReconciliationResult;
  selectedPeriod: string;
  currentUserRole: UserRole;
  authToken: string | null;
  onDatasetUpdated: (ds: MisDataset) => void;
}> = ({ dataset, reconciliation, selectedPeriod, currentUserRole, authToken, onDatasetUpdated }) => {
  const wf = dataset.workflows.find((w) => w.period === selectedPeriod) ?? dataset.workflows[dataset.workflows.length - 1];
  const [comment, setComment] = useState('');
  const [dept, setDept] = useState('Finance');
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const [adjDesc, setAdjDesc] = useState('');
  const [adjAmt, setAdjAmt] = useState('');

  const stages: WorkflowStage[] = [
    'Open',
    'Uploaded',
    'Validated',
    'KpiCalculated',
    'ExceptionReview',
    'Approved',
    'Published',
    'Locked',
  ];

  const transition = async (nextStage?: WorkflowStage) => {
    if (!authToken) return;
    setErrMsg(null);
    const res = await fetch('/api/workflow/transition', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        period: selectedPeriod,
        nextStage,
        comment: comment.trim() || undefined,
        department: comment.trim() ? dept : undefined,
      }),
    });
    const data = (await res.json()) as { dataset?: MisDataset; error?: string };
    if (res.ok && data.dataset) {
      onDatasetUpdated(data.dataset);
      setComment('');
    } else {
      setErrMsg(data.error || 'Workflow update rejected.');
    }
  };

  const submitAdjustment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authToken) return;
    const amt = Number(adjAmt);
    const res = await fetch('/api/adjustments', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        period: selectedPeriod,
        companyId: dataset.companies[0].id,
        projectId: dataset.projects[0].id,
        description: adjDesc,
        debitAccountClass: 'OpEx',
        creditAccountClass: 'Payables',
        amountOMR: amt,
      }),
    });
    const data = (await res.json()) as { dataset?: MisDataset; error?: string };
    if (res.ok && data.dataset) {
      onDatasetUpdated(data.dataset);
      setAdjDesc('');
      setAdjAmt('');
    } else {
      setErrMsg(data.error || 'Failed to submit adjustment.');
    }
  };

  const approveAdj = async (id: string) => {
    if (!authToken) return;
    const res = await fetch(`/api/adjustments/${id}/approve`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = (await res.json()) as { dataset?: MisDataset; error?: string };
    if (res.ok && data.dataset) onDatasetUpdated(data.dataset);
    else setErrMsg(data.error || 'Approval rejected.');
  };

  const currentStageIdx = stages.indexOf(wf.stage);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          Monthly MIS Closing Workflow & Maker-Checker Controls
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          Period {selectedPeriod} · Current Role: {currentUserRole} · Schedules: {wf.schedulesCompleted}/{wf.schedulesTotal} · Open Exceptions: {wf.openExceptions}
        </p>
      </div>

      {/* Stage Stepper */}
      <div className="rounded-lg border p-5 space-y-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {stages.map((s, idx) => {
            const active = s === wf.stage;
            const done = idx < currentStageIdx;
            return (
              <div
                key={s}
                className="p-2.5 rounded border text-center text-[11px] font-medium"
                style={{
                  borderColor: active ? 'var(--re-accent)' : 'var(--re-border)',
                  backgroundColor: active ? 'var(--re-accent-soft)' : 'var(--re-surface-alt)',
                  color: active || done ? 'var(--re-text)' : 'var(--re-text-muted)',
                }}
              >
                {done && <CheckCircle2 className="w-3.5 h-3.5 mx-auto mb-1 text-emerald-600" />}
                {s === 'Locked' && active && <Lock className="w-3.5 h-3.5 mx-auto mb-1 text-amber-600" />}
                {s}
              </div>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-2">
          {currentStageIdx < stages.length - 1 && (
            <button
              type="button"
              onClick={() => void transition(stages[currentStageIdx + 1])}
              className="px-4 py-2 rounded-lg text-xs font-medium"
              style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
            >
              Advance to {stages[currentStageIdx + 1]}
            </button>
          )}
          {wf.stage === 'Locked' && (
            <button
              type="button"
              onClick={() => void transition('Open')}
              className="px-4 py-2 rounded-lg border text-xs font-medium"
              style={{ borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            >
              Controlled Reopen (CFO Only)
            </button>
          )}
          <span className="text-xs ml-auto" style={{ color: 'var(--re-text-muted)' }}>
            Reconciliation Gate: {reconciliation.canPublish ? 'Passed (0.000 OMR diff)' : 'Blocked'}
          </span>
        </div>

        {errMsg && (
          <div className="p-3 rounded border text-xs text-rose-600 dark:text-rose-400" style={{ borderColor: 'var(--re-border)' }}>
            {errMsg}
          </div>
        )}
      </div>

      {/* Departmental Commentary + Maker-Checker Adjustments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border p-5 space-y-3" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Departmental Sign-Off Comments</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {wf.departmentalComments.map((c, idx) => (
              <div key={idx} className="p-2.5 rounded border text-xs" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
                <div className="font-semibold" style={{ color: 'var(--re-text)' }}>{c.department} · {c.author}</div>
                <div className="mt-0.5" style={{ color: 'var(--re-text-muted)' }}>{c.comment}</div>
              </div>
            ))}
          </div>
          <div className="flex gap-2 pt-2">
            <select
              aria-label="Department"
              value={dept}
              onChange={(e) => setDept(e.target.value)}
              className="px-2 py-1.5 rounded border text-xs"
              style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            >
              <option>Finance</option>
              <option>Quantity Surveying</option>
              <option>Sales & Collections</option>
              <option>Treasury</option>
            </select>
            <input
              type="text"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add review note..."
              className="flex-1 px-3 py-1.5 rounded border text-xs"
              style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            />
            <button
              type="button"
              onClick={() => void transition(undefined)}
              className="px-3 py-1.5 rounded text-xs font-medium"
              style={{ backgroundColor: 'var(--re-primary)', color: '#fff' }}
            >
              Post
            </button>
          </div>
        </div>

        <div className="rounded-lg border p-5 space-y-3" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Management Adjustments (Maker-Checker)</h3>
          <form onSubmit={submitAdjustment} className="flex flex-wrap gap-2">
            <input
              type="text"
              required
              value={adjDesc}
              onChange={(e) => setAdjDesc(e.target.value)}
              placeholder="Adjustment narration..."
              className="flex-1 min-w-[160px] px-3 py-1.5 rounded border text-xs"
              style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            />
            <input
              type="number"
              step="0.001"
              required
              value={adjAmt}
              onChange={(e) => setAdjAmt(e.target.value)}
              placeholder="OMR"
              className="w-28 px-3 py-1.5 rounded border text-xs font-mono-num"
              style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            />
            <button type="submit" className="px-3 py-1.5 rounded text-xs font-medium" style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}>
              Submit
            </button>
          </form>
          <div className="space-y-2 max-h-44 overflow-y-auto">
            {dataset.adjustments.map((a) => (
              <div key={a.id} className="p-2.5 rounded border flex items-center justify-between gap-2 text-xs" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
                <div>
                  <div className="font-medium" style={{ color: 'var(--re-text)' }}>{a.description}</div>
                  <div className="text-[11px]" style={{ color: 'var(--re-text-muted)' }}>
                    {formatMoney(a.amountOMR)} · Prepared by {a.preparedBy} · {a.status}
                  </div>
                </div>
                {a.status === 'Pending Approval' && currentUserRole === 'CFO_Admin' && (
                  <button
                    type="button"
                    onClick={() => void approveAdj(a.id)}
                    className="px-2.5 py-1 rounded text-[11px] font-medium bg-emerald-600 text-white"
                  >
                    Approve
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export const ReportsExportsView: React.FC<{
  dataset: MisDataset;
  statements: FinancialStatements;
  projectKpis: ProjectKpiSummary[];
  reconciliation: ReconciliationResult;
  commentary: ExecutiveCommentaryBundle;
  selectedPeriod: string;
  basis: ReportingBasis;
  currency: CurrencyCode;
  companyFilterId: string | 'CONSOLIDATED';
  masked: boolean;
}> = ({
  dataset,
  statements,
  projectKpis,
  reconciliation,
  commentary,
  selectedPeriod,
  basis,
  currency,
  companyFilterId,
  masked,
}) => {
  const company = dataset.companies.find((c) => c.id === companyFilterId) ?? null;
  const companyLabel = company ? company.name : 'Consolidated Real Estate Group (3 Entities)';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
          Reports, Board Presentations & Financial Validation Exports
        </h2>
        <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
          Generate publication-grade Excel MIS Workbooks (with live formulas), PDF Board Packs, and PowerPoint Decks
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg border p-5 flex flex-col justify-between gap-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div>
            <FileSpreadsheet className="w-6 h-6 mb-2 text-emerald-600" />
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
              Excel MIS & Validation Workbook (.xlsx)
            </h3>
            <p className="text-xs mt-1" style={{ color: 'var(--re-text-muted)' }}>
              Multi-sheet workbook containing Income Statement, Balance Sheet, Project EAC formulas, and Trial Balance reconciliation.
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              exportMisExcelPack(dataset, statements, projectKpis, reconciliation, selectedPeriod, basis, currency, companyLabel)
            }
            className="px-4 py-2 rounded-lg text-xs font-medium"
            style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
          >
            Download Excel MIS Pack
          </button>
        </div>

        <div className="rounded-lg border p-5 flex flex-col justify-between gap-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div>
            <FileText className="w-6 h-6 mb-2 text-rose-600" />
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
              Monthly Board MIS Pack (.pdf)
            </h3>
            <p className="text-xs mt-1" style={{ color: 'var(--re-text-muted)' }}>
              Formatted landscape executive pack with company branding, financial summary, project matrix, and management commentary.
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              exportMisPdfPack(company, statements, projectKpis, commentary, selectedPeriod, basis, currency, masked)
            }
            className="px-4 py-2 rounded-lg text-xs font-medium"
            style={{ backgroundColor: 'var(--re-primary)', color: '#fff' }}
          >
            Download Board PDF
          </button>
        </div>

        <div className="rounded-lg border p-5 flex flex-col justify-between gap-4" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div>
            <Presentation className="w-6 h-6 mb-2 text-amber-600" />
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>
              Board Presentation Deck (.pptx)
            </h3>
            <p className="text-xs mt-1" style={{ color: 'var(--re-text-muted)' }}>
              4-slide PowerPoint board deck covering executive KPIs, consolidated P&L/BS, project portfolio, and priority actions.
            </p>
          </div>
          <button
            type="button"
            onClick={() =>
              void exportBoardPowerPoint(companyLabel, statements, projectKpis, commentary, selectedPeriod, basis, currency, masked)
            }
            className="px-4 py-2 rounded-lg border text-xs font-medium"
            style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
          >
            Download PowerPoint (.pptx)
          </button>
        </div>
      </div>
    </div>
  );
};

export const SettingsAdminView: React.FC<{
  dataset: MisDataset;
  users: { id: string; name: string; email: string; role: UserRole }[];
  currentUserId: string;
  authToken: string | null;
  onSwitchUser: (userId: string) => void;
  onDatasetUpdated: (ds: MisDataset) => void;
  onOpenSetupWizard: () => void;
}> = ({ dataset, users, currentUserId, authToken, onSwitchUser, onDatasetUpdated, onOpenSetupWizard }) => {
  const [policies, setPolicies] = useState<AccountingPolicyConfig>(dataset.policies);
  const [licenseKey, setLicenseKey] = useState('');
  const [licensedTo, setLicensedTo] = useState(dataset.license.licensedTo);
  const [adminMsg, setAdminMsg] = useState<string | null>(null);

  const savePolicies = async () => {
    if (!authToken) return;
    const res = await fetch('/api/policies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
      body: JSON.stringify(policies),
    });
    const data = (await res.json()) as { dataset?: MisDataset; error?: string };
    if (res.ok && data.dataset) {
      onDatasetUpdated(data.dataset);
      setAdminMsg('Updated IFRS & Oman Tax accounting policies.');
    } else setAdminMsg(data.error || 'Policy update failed.');
  };

  const createBackup = async () => {
    if (!authToken) return;
    const res = await fetch('/api/backups/create', {
      method: 'POST',
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = (await res.json()) as { dataset?: MisDataset; error?: string };
    if (res.ok && data.dataset) {
      onDatasetUpdated(data.dataset);
      setAdminMsg('Created encrypted SQLite physical backup.');
    } else setAdminMsg(data.error || 'Backup failed.');
  };

  const restoreBackup = async (filename: string) => {
    if (!authToken) return;
    const res = await fetch('/api/backups/restore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
      body: JSON.stringify({ filename }),
    });
    const data = (await res.json()) as { dataset?: MisDataset; error?: string };
    if (res.ok && data.dataset) {
      onDatasetUpdated(data.dataset);
      setAdminMsg(`Restored database from ${filename}.`);
    } else setAdminMsg(data.error || 'Restore failed.');
  };

  const activateLicense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authToken) return;
    const res = await fetch('/api/license/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
      body: JSON.stringify({ licenseKey, licensedTo, edition: 'Permanent' }),
    });
    const data = (await res.json()) as { dataset?: MisDataset; error?: string };
    if (res.ok && data.dataset) {
      onDatasetUpdated(data.dataset);
      setLicenseKey('');
      setAdminMsg('Activated Permanent Enterprise License.');
    } else setAdminMsg(data.error || 'License activation failed.');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="font-display text-lg font-semibold" style={{ color: 'var(--re-text)' }}>
            Security, RBAC, Backups, Licensing & Setup
          </h2>
          <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>
            Manage role-based permissions, IFRS/Oman tax policies, SQLite backups, offline licensing, and Setup Wizard
          </p>
        </div>
        <button
          type="button"
          onClick={onOpenSetupWizard}
          className="px-3.5 py-2 rounded-lg text-xs font-medium"
          style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
        >
          Launch First-Time Setup Wizard
        </button>
      </div>

      {adminMsg && (
        <div className="p-3 rounded-lg border text-xs font-medium" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          {adminMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RBAC User Switcher */}
        <div className="rounded-lg border p-5 space-y-3" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" style={{ color: 'var(--re-accent)' }} />
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Role-Based Access Control (Active Session)</h3>
          </div>
          <div className="space-y-2">
            {users.map((u) => (
              <div key={u.id} className="p-2.5 rounded border flex items-center justify-between text-xs" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
                <div>
                  <div className="font-medium" style={{ color: 'var(--re-text)' }}>{u.name}</div>
                  <div className="text-[11px]" style={{ color: 'var(--re-text-muted)' }}>{u.role} · {u.email}</div>
                </div>
                <button
                  type="button"
                  onClick={() => onSwitchUser(u.id)}
                  className="px-3 py-1 rounded border text-xs font-medium"
                  style={
                    currentUserId === u.id
                      ? { backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)', borderColor: 'var(--re-accent)' }
                      : { borderColor: 'var(--re-border)', color: 'var(--re-text)' }
                  }
                >
                  {currentUserId === u.id ? 'Active' : 'Switch Role'}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* IFRS & Oman Tax Policy Config */}
        <div className="rounded-lg border p-5 space-y-3 text-xs" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>IFRS & Oman/GCC Tax Configuration</h3>
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span style={{ color: 'var(--re-text-muted)' }}>Materiality Threshold (OMR)</span>
              <input
                type="number"
                value={policies.materialityThresholdOMR}
                onChange={(e) => setPolicies({ ...policies, materialityThresholdOMR: Number(e.target.value) })}
                className="mt-1 w-full px-2.5 py-1.5 rounded border font-mono-num"
                style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
              />
            </label>
            <label className="block">
              <span style={{ color: 'var(--re-text-muted)' }}>Oman Corporate Tax (%)</span>
              <input
                type="number"
                value={policies.omanCorporateTaxRatePct}
                onChange={(e) => setPolicies({ ...policies, omanCorporateTaxRatePct: Number(e.target.value) })}
                className="mt-1 w-full px-2.5 py-1.5 rounded border font-mono-num"
                style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
              />
            </label>
            <label className="block">
              <span style={{ color: 'var(--re-text-muted)' }}>Oman VAT Rate (%)</span>
              <input
                type="number"
                value={policies.omanVatRatePct}
                onChange={(e) => setPolicies({ ...policies, omanVatRatePct: Number(e.target.value) })}
                className="mt-1 w-full px-2.5 py-1.5 rounded border font-mono-num"
                style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
              />
            </label>
            <label className="block">
              <span style={{ color: 'var(--re-text-muted)' }}>IFRS 9 Stage 1 ECL (%)</span>
              <input
                type="number"
                step="0.05"
                value={policies.ifrs9EclStage1Pct}
                onChange={(e) => setPolicies({ ...policies, ifrs9EclStage1Pct: Number(e.target.value) })}
                className="mt-1 w-full px-2.5 py-1.5 rounded border font-mono-num"
                style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
              />
            </label>
          </div>
          <label className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              checked={policies.ias23CapitalizeBorrowingCosts}
              onChange={(e) => setPolicies({ ...policies, ias23CapitalizeBorrowingCosts: e.target.checked })}
            />
            <span>Capitalize qualifying borrowing costs under IAS 23</span>
          </label>
          <button
            type="button"
            onClick={() => void savePolicies()}
            className="px-4 py-2 rounded-lg text-xs font-medium"
            style={{ backgroundColor: 'var(--re-primary)', color: '#fff' }}
          >
            Save Policy Rules
          </button>
        </div>

        {/* Backups & Restoration */}
        <div className="rounded-lg border p-5 space-y-3 text-xs" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <div className="flex items-center justify-between">
            <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>SQLite Database Backups & Restore</h3>
            <button
              type="button"
              onClick={() => void createBackup()}
              className="px-3 py-1.5 rounded text-xs font-medium"
              style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
            >
              Create Manual Backup
            </button>
          </div>
          <div className="space-y-2 max-h-44 overflow-y-auto">
            {dataset.backups.map((b) => (
              <div key={b.id} className="p-2.5 rounded border flex items-center justify-between gap-2" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
                <div className="min-w-0">
                  <div className="font-mono-num truncate" style={{ color: 'var(--re-text)' }}>{b.filename}</div>
                  <div className="text-[11px]" style={{ color: 'var(--re-text-muted)' }}>
                    {b.type} · {(b.sizeBytes / 1024).toFixed(1)} KB · {b.checksum}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => void restoreBackup(b.filename)}
                  className="px-2.5 py-1 rounded border text-[11px] shrink-0"
                  style={{ borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
                >
                  Restore
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Licensing & Audit Trail */}
        <div className="rounded-lg border p-5 space-y-3 text-xs" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <h3 className="font-display text-sm font-semibold" style={{ color: 'var(--re-text)' }}>Device Licensing & Audit Log</h3>
          <div className="p-3 rounded border space-y-1" style={{ borderColor: 'var(--re-border)', backgroundColor: 'var(--re-surface-alt)' }}>
            <div><strong>Device ID:</strong> <span className="font-mono-num">{dataset.license.deviceId}</span></div>
            <div><strong>Edition:</strong> {dataset.license.edition} ({dataset.license.status})</div>
            <div><strong>Licensed To:</strong> {dataset.license.licensedTo}</div>
            <div><strong>Signature:</strong> <span className="font-mono-num">{dataset.license.signatureHash}</span></div>
          </div>
          <form onSubmit={activateLicense} className="flex gap-2">
            <input
              type="text"
              value={licensedTo}
              onChange={(e) => setLicensedTo(e.target.value)}
              placeholder="Organization name"
              className="flex-1 px-2.5 py-1.5 rounded border text-xs"
              style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            />
            <input
              type="text"
              value={licenseKey}
              onChange={(e) => setLicenseKey(e.target.value)}
              placeholder="Signed License Key..."
              className="w-40 px-2.5 py-1.5 rounded border text-xs font-mono-num"
              style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            />
            <button type="submit" className="px-3 py-1.5 rounded text-xs font-medium" style={{ backgroundColor: 'var(--re-primary)', color: '#fff' }}>
              Activate
            </button>
          </form>
          <div className="pt-2">
            <div className="font-semibold mb-1.5" style={{ color: 'var(--re-text)' }}>Recent Immutable Audit Trail</div>
            <div className="space-y-1 max-h-28 overflow-y-auto font-mono-num text-[11px]" style={{ color: 'var(--re-text-muted)' }}>
              {dataset.auditLogs.slice(0, 8).map((a) => (
                <div key={a.id}>
                  {a.timestamp.slice(0, 16)} · {a.actor} · {a.action} · {a.entity}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
