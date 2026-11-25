"use client";

import { useState } from "react";
import Link from "next/link";
import { parseSapImportFile, confirmSapImport, type SapImportParseResult } from "@/actions/sapImport";
import type { SapImportRowError } from "@/lib/sapImport";

type ConfirmResult = {
  batchId: string;
  newRecords: number;
  updatedRecords: number;
  unchangedRecords: number;
  errorRecords: number;
};

export default function SapImportWizard() {
  const [parsing, setParsing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [parseResult, setParseResult] = useState<SapImportParseResult | null>(null);
  const [confirmResult, setConfirmResult] = useState<ConfirmResult | null>(null);

  async function onFileChange(formData: FormData) {
    setParsing(true);
    setParseResult(null);
    setConfirmResult(null);
    const result = await parseSapImportFile(formData);
    setParseResult(result);
    setParsing(false);
  }

  async function onConfirm() {
    if (!parseResult || !parseResult.success) return;
    setConfirming(true);
    const result = await confirmSapImport(parseResult.fileName, parseResult.validRows, parseResult.errors);
    setConfirmResult(result);
    setConfirming(false);
  }

  if (confirmResult) {
    return (
      <div className="card p-6 space-y-3">
        <p className="pill bg-good-soft text-good">Import complete</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2">
          <div><p className="font-mono text-lg font-semibold">{confirmResult.newRecords}</p><p className="text-xs text-muted">New</p></div>
          <div><p className="font-mono text-lg font-semibold">{confirmResult.updatedRecords}</p><p className="text-xs text-muted">Updated</p></div>
          <div><p className="font-mono text-lg font-semibold">{confirmResult.unchangedRecords}</p><p className="text-xs text-muted">Unchanged</p></div>
          <div><p className="font-mono text-lg font-semibold text-bad">{confirmResult.errorRecords}</p><p className="text-xs text-muted">Errors</p></div>
        </div>
        <div className="flex gap-2 pt-2">
          <Link href="/sap-import-history" className="btn-secondary">View import history</Link>
          <Link href="/assets" className="btn-primary">Go to assets</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <form action={onFileChange} className="card p-5 space-y-3">
        <label className="label" htmlFor="file">SAP export file (.xlsx or .csv)</label>
        <input id="file" name="file" type="file" accept=".xlsx,.xls,.csv" required className="input" />
        <button type="submit" disabled={parsing} className="btn-primary">{parsing ? "Validating…" : "Upload & validate"}</button>
      </form>

      {parseResult && !parseResult.success && (
        <div className="card p-5 border-bad">
          <p className="text-sm text-bad font-medium">{parseResult.error}</p>
          {parseResult.missingColumns && parseResult.missingColumns.length > 0 && (
            <ul className="text-sm text-muted mt-2 list-disc pl-5">
              {parseResult.missingColumns.map((c) => <li key={c}>{c}</li>)}
            </ul>
          )}
        </div>
      )}

      {parseResult && parseResult.success && (
        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="text-sm font-semibold mb-3">Preview — {parseResult.fileName}</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div><p className="font-mono text-lg font-semibold">{parseResult.preview.totalRows}</p><p className="text-xs text-muted">Total rows</p></div>
              <div><p className="font-mono text-lg font-semibold text-good">{parseResult.preview.newCount}</p><p className="text-xs text-muted">New assets</p></div>
              <div><p className="font-mono text-lg font-semibold text-steel">{parseResult.preview.existingCount}</p><p className="text-xs text-muted">Existing assets</p></div>
              <div><p className="font-mono text-lg font-semibold text-bad">{parseResult.preview.invalidRowCount}</p><p className="text-xs text-muted">Invalid rows</p></div>
              <div><p className="font-mono text-lg font-semibold text-warn">{parseResult.preview.duplicateInFileCount}</p><p className="text-xs text-muted">Duplicates in file</p></div>
            </div>
            {parseResult.unexpectedColumns.length > 0 && (
              <p className="text-xs text-warn mt-3">Unexpected columns ignored: {parseResult.unexpectedColumns.join(", ")}</p>
            )}
            <p className="text-xs text-muted mt-3">Blank values are expected and never block an import — only shown here for awareness.</p>
          </div>

          {parseResult.errors.length > 0 && (
            <div className="card p-5">
              <h2 className="text-sm font-semibold mb-3">Rows requiring attention ({parseResult.errors.length})</h2>
              <div className="max-h-56 overflow-y-auto text-sm space-y-1">
                {parseResult.errors.slice(0, 50).map((e: SapImportRowError, i: number) => (
                  <p key={i} className="text-muted">Row {e.rowNumber}{e.assetNumber ? ` (${e.assetNumber})` : ""}: {e.errorDetail}</p>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <button onClick={onConfirm} disabled={confirming || parseResult.validRows.length === 0} className="btn-primary">
              {confirming ? "Importing…" : `Confirm import of ${parseResult.validRows.length} row(s)`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
