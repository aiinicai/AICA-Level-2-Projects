// Several files of the same layout (12 monthly Day Books, a ledger per branch …) read as one table.
import { detectHeaderRow } from "./mapping";
import type { SheetTable } from "./sources";

const sig = (row: unknown[]) => JSON.stringify((row ?? []).map((c) => String(c ?? "").trim().toLowerCase()).filter(Boolean));

/**
 * sheets come from different files (fileOf[i] = file of sheet i). When two or more files have a sheet
 * with the same column headings, a combined sheet (headings once, then every file's rows) is put first.
 */
export function combineSameLayout(sheets: SheetTable[], fileOf: string[]): SheetTable[] {
  const groups = new Map<string, { idx: number[]; hr: number[] }>();
  sheets.forEach((s, i) => {
    if (s.rows.length < 2) return;
    const hr = s.preMapped ? 0 : detectHeaderRow(s.rows);
    const k = `${s.preMapped ? "pm" : "x"}|${sig(s.rows[hr])}`;
    if (k.endsWith("[]")) return;
    const g = groups.get(k) ?? { idx: [], hr: [] };
    g.idx.push(i); g.hr.push(hr);
    groups.set(k, g);
  });
  const combined: SheetTable[] = [];
  groups.forEach((g) => {
    const files = new Set(g.idx.map((i) => fileOf[i]));
    if (files.size < 2) return;
    const first = sheets[g.idx[0]];
    const rows = [first.rows[g.hr[0]], ...g.idx.flatMap((i, n) => sheets[i].rows.slice(g.hr[n] + 1))];
    combined.push({ name: `All ${files.size} files combined`, rows, preMapped: first.preMapped });
  });
  return [...combined, ...sheets];
}
