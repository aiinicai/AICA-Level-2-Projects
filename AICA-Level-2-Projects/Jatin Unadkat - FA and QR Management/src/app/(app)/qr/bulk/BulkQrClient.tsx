"use client";

import { useState } from "react";
import { generateBulkQr } from "@/actions/qr";
import { QR_SIZE_PRESETS } from "@/lib/qr";

type AssetRow = { id: string; assetNumber: string; description: string; hasQr: boolean };

export default function BulkQrClient({ assets }: { assets: AssetRow[] }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [sizePreset, setSizePreset] = useState("MEDIUM");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<{ jobId: string; assetCount: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => (prev.size === assets.length ? new Set() : new Set(assets.map((a) => a.id))));
  }

  async function onGenerate() {
    setPending(true);
    setError(null);
    setResult(null);
    try {
      const outcome = await generateBulkQr(Array.from(selected), sizePreset);
      setResult(outcome);
    } catch (e) {
      setError((e as Error).message);
    }
    setPending(false);
  }

  return (
    <div className="space-y-4">
      <div className="card p-4 flex flex-wrap gap-3 items-end">
        <div>
          <label className="label" htmlFor="sizePreset">Label size</label>
          <select id="sizePreset" value={sizePreset} onChange={(e) => setSizePreset(e.target.value)} className="input">
            {Object.entries(QR_SIZE_PRESETS).map(([key, v]) => (
              <option key={key} value={key}>{v.label} ({v.mm}×{v.mm} mm)</option>
            ))}
          </select>
        </div>
        <button type="button" onClick={toggleAll} className="btn-secondary">
          {selected.size === assets.length ? "Deselect all" : "Select all"}
        </button>
        <button type="button" onClick={onGenerate} disabled={pending || selected.size === 0} className="btn-primary">
          {pending ? "Generating…" : `Generate ${selected.size} label(s)`}
        </button>
      </div>

      {error && <p className="text-sm text-bad">{error}</p>}
      {result && (
        <div className="card p-4 flex items-center justify-between">
          <p className="text-sm">{result.assetCount} label(s) ready.</p>
          <a href={`/api/qr/bulk/${result.jobId}/download`} className="btn-primary">Download PDF</a>
        </div>
      )}

      <div className="card divide-y divide-line">
        {assets.map((a) => (
          <label key={a.id} className="p-3 flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={selected.has(a.id)} onChange={() => toggle(a.id)} />
            <span className="font-mono text-sm text-steel">{a.assetNumber}</span>
            <span className="text-sm text-muted flex-1">{a.description}</span>
            {!a.hasQr && <span className="pill bg-warn-soft text-warn">No QR yet</span>}
          </label>
        ))}
        {assets.length === 0 && <p className="p-8 text-center text-muted text-sm">No assets match this filter.</p>}
      </div>
    </div>
  );
}
