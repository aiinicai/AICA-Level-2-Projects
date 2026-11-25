"use client";

import { useState } from "react";
import Link from "next/link";
import { validateSapExportSelection, generateSapExport, type SapExportValidation } from "@/actions/sapExport";
import type { RoleName } from "@prisma/client";

type AssetRow = { id: string; assetNumber: string; description: string; verificationStatus: string };

export default function SapExportClient({ assets, role }: { assets: AssetRow[]; role: RoleName }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [validation, setValidation] = useState<SapExportValidation | null>(null);
  const [result, setResult] = useState<{ batchId: string; includedCount: number; excludedCount: number } | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setValidation(null);
    setResult(null);
  }

  async function onValidate() {
    setPending(true);
    setError(null);
    try {
      setValidation(await validateSapExportSelection(Array.from(selected)));
    } catch (e) {
      setError((e as Error).message);
    }
    setPending(false);
  }

  async function onGenerate() {
    setPending(true);
    setError(null);
    try {
      setResult(await generateSapExport(Array.from(selected)));
    } catch (e) {
      setError((e as Error).message);
    }
    setPending(false);
  }

  return (
    <div className="space-y-4">
      <div className="card divide-y divide-line max-h-96 overflow-y-auto">
        {assets.map((a) => (
          <label key={a.id} className="p-3 flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={selected.has(a.id)} onChange={() => toggle(a.id)} />
            <span className="font-mono text-sm text-steel">{a.assetNumber}</span>
            <span className="text-sm text-muted flex-1">{a.description}</span>
            <span className="pill bg-steel-soft text-steel">{a.verificationStatus.replaceAll("_", " ")}</span>
          </label>
        ))}
        {assets.length === 0 && <p className="p-8 text-center text-muted text-sm">No verified assets in scope yet.</p>}
      </div>

      <div className="flex gap-2">
        <button onClick={onValidate} disabled={pending || selected.size === 0} className="btn-secondary">Validate selection</button>
        {validation && (
          <button onClick={onGenerate} disabled={pending} className="btn-primary">
            Generate export ({validation.selectedCount - validation.excluded.length} record(s))
          </button>
        )}
      </div>

      {error && <p className="text-sm text-bad">{error}</p>}

      {validation && (
        <div className="card p-5">
          <h2 className="text-sm font-semibold mb-3">Validation summary</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div><p className="font-mono text-lg font-semibold">{validation.selectedCount}</p><p className="text-xs text-muted">Selected</p></div>
            <div><p className="font-mono text-lg font-semibold text-warn">{validation.locationChangedCount}</p><p className="text-xs text-muted">Location changed</p></div>
            <div><p className="font-mono text-lg font-semibold text-bad">{validation.exceptionCount}</p><p className="text-xs text-muted">Open exceptions</p></div>
            <div><p className="font-mono text-lg font-semibold text-bad">{validation.excluded.length}</p><p className="text-xs text-muted">Excluded</p></div>
          </div>
          {validation.excluded.length > 0 && (
            <ul className="text-sm text-muted mt-3 list-disc pl-5">
              {validation.excluded.map((e) => <li key={e.assetId}>{e.assetNumber}: {e.reason}</li>)}
            </ul>
          )}
        </div>
      )}

      {result && (
        <div className="card p-5 space-y-2">
          <p className="pill bg-good-soft text-good">Export generated</p>
          <p className="text-sm">{result.includedCount} record(s) included, {result.excludedCount} excluded.</p>
          {role === "ADMIN" ? (
            <a href={`/api/sap-export/${result.batchId}/download`} className="btn-primary inline-flex">Download Excel</a>
          ) : (
            <p className="text-sm text-muted">Staged for Admin sign-off — an Admin must download the final file (design dossier, ADD05).</p>
          )}
          <Link href="/sap-export-history" className="text-xs text-steel hover:underline block">View export history →</Link>
        </div>
      )}
    </div>
  );
}
