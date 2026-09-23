import { useMemo, useRef, useState } from "react";
import { AlertTriangle, FileSpreadsheet, Loader2, RefreshCw, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { StatusPill } from "@/components/widgets/DataTable";
import { relativeTime } from "@/lib/format";
import { DATASETS, DATE_FIELD_BY_DATASET } from "@/lib/data/demo-source";
import { applyMapping, autoMap, parseWorkbook, type ParsedWorkbook } from "@/lib/excel/parse";
import { importWorkbook } from "@/lib/excel.functions";
import { deleteSource } from "@/lib/accounting.functions";
import { useLiveData } from "@/lib/live-data";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";

const NONE = "__none__";

export function ExcelImportCard() {
  const { user, loading: authLoading } = useAuth();
  const { sources, loading: syncing, refresh } = useLiveData();
  const fileInput = useRef<HTMLInputElement>(null);

  const [open, setOpen] = useState(false);
  const [fileName, setFileName] = useState("");
  const [book, setBook] = useState<ParsedWorkbook | null>(null);
  const [sheet, setSheet] = useState("");
  const [datasetId, setDatasetId] = useState("sales_invoices");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [replaceId, setReplaceId] = useState<string | undefined>(undefined);
  const [parsing, setParsing] = useState(false);
  const [busy, setBusy] = useState(false);

  const excelSources = sources.filter((s) => s.provider === "excel");
  const dataset = DATASETS.find((d) => d.id === datasetId)!;
  const columns = book?.sheets[sheet]?.columns ?? [];
  const sheetRows = book?.sheets[sheet]?.rows ?? [];
  const dateField = DATE_FIELD_BY_DATASET[datasetId];

  const result = useMemo(
    () => (book ? applyMapping(sheetRows, dataset.fields, mapping, dateField) : null),
    [book, sheetRows, dataset, mapping, dateField],
  );
  const errors = result?.issues.filter((i) => i.level === "error") ?? [];
  const warnings = result?.issues.filter((i) => i.level === "warning") ?? [];
  const preview = result?.rows.slice(0, 5) ?? [];
  const mappedFields = dataset.fields.filter((f) => mapping[f.name]);

  const signedIn = Boolean(user) && !authLoading;

  const pickFile = (id?: string) => {
    setReplaceId(id);
    fileInput.current?.click();
  };

  const onFile = async (file: File) => {
    setParsing(true);
    try {
      const parsed = await parseWorkbook(file);
      const first = parsed.sheetNames[0];
      if (!first) throw new Error("This workbook has no sheets with data.");
      setBook(parsed);
      setFileName(file.name);
      setSheet(first);
      setMapping(autoMap(parsed.sheets[first]!.columns, dataset.fields));
      setOpen(true);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "That file could not be read.");
    } finally {
      setParsing(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const changeSheet = (name: string) => {
    setSheet(name);
    setMapping(autoMap(book?.sheets[name]?.columns ?? [], dataset.fields));
  };

  const changeDataset = (id: string) => {
    setDatasetId(id);
    const fields = DATASETS.find((d) => d.id === id)?.fields ?? [];
    setMapping(autoMap(columns, fields));
  };

  const submit = async () => {
    if (!result) return;
    setBusy(true);
    try {
      const res = await importWorkbook({
        data: {
          sourceId: replaceId,
          name: fileName || "Excel upload",
          dataset: datasetId,
          dateField,
          rows: result.rows,
        },
      });
      toast.success(`${res.imported.toLocaleString("en-IN")} rows imported`);
      setOpen(false);
      setBook(null);
      await refresh();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "The import failed.");
    } finally {
      setBusy(false);
    }
  };

  if (!signedIn) return null;

  return (
    <section className="panel p-4">
      <input
        ref={fileInput}
        type="file"
        accept=".xlsx,.xls,.csv"
        className="sr-only"
        aria-label="Choose a spreadsheet to upload"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void onFile(file);
        }}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Excel &amp; CSV uploads</h2>
          <p className="text-xs text-muted-foreground">
            Upload a sales, purchase or ledger sheet, match the columns once, and your dashboards use those figures.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => void refresh()} disabled={syncing}>
            {syncing ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <RefreshCw className="size-4" aria-hidden />}
            Refresh
          </Button>
          <Button size="sm" onClick={() => pickFile(undefined)} disabled={parsing}>
            {parsing ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Upload className="size-4" aria-hidden />}
            Upload workbook
          </Button>
        </div>
      </div>

      {excelSources.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          Nothing uploaded yet. Accepted files: .xlsx, .xls and .csv.
        </p>
      ) : (
        <ul className="mt-4 space-y-2">
          {excelSources.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-border p-3">
              <FileSpreadsheet className="size-5 text-muted-foreground" aria-hidden />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-semibold">{s.name}</span>
                  <StatusPill value={s.status === "connected" ? "Healthy" : "Pending"} />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {s.records.toLocaleString("en-IN")} rows ·{" "}
                  {s.lastSync ? `updated ${relativeTime(s.lastSync)}` : "not imported yet"}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => pickFile(s.id)} disabled={parsing}>
                <Upload className="size-4" aria-hidden /> Replace file
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Remove ${s.name}`}
                onClick={async () => {
                  await deleteSource({ data: { id: s.id } });
                  toast.success(`${s.name} removed`);
                  await refresh();
                }}
              >
                <Trash2 className="size-4" aria-hidden />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Match your columns</DialogTitle>
            <DialogDescription>
              {fileName} — tell us which column in your sheet holds each figure. We have guessed where we could.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="xl-sheet">Sheet</Label>
              <Select value={sheet} onValueChange={changeSheet}>
                <SelectTrigger id="xl-sheet">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(book?.sheetNames ?? []).map((n) => (
                    <SelectItem key={n} value={n}>
                      {n}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="xl-dataset">Import as</Label>
              <Select value={datasetId} onValueChange={changeDataset}>
                <SelectTrigger id="xl-dataset">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DATASETS.map((d) => (
                    <SelectItem key={d.id} value={d.id}>
                      {d.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="mt-2 space-y-2">
            {dataset.fields.map((f) => (
              <div key={f.name} className="flex flex-wrap items-center gap-2">
                <Label className="w-40 shrink-0 text-xs" htmlFor={`map-${f.name}`}>
                  {f.label}
                </Label>
                <Select
                  value={mapping[f.name] ?? NONE}
                  onValueChange={(v) =>
                    setMapping((m) => {
                      const next = { ...m };
                      if (v === NONE) delete next[f.name];
                      else next[f.name] = v;
                      return next;
                    })
                  }
                >
                  <SelectTrigger id={`map-${f.name}`} className="h-9 flex-1 min-w-[160px]">
                    <SelectValue placeholder="Not imported" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>Not imported</SelectItem>
                    {columns.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ))}
          </div>

          {(errors.length > 0 || warnings.length > 0) && (
            <ul className="space-y-1 rounded-lg border border-border p-3 text-xs">
              {[...errors, ...warnings].map((i, idx) => (
                <li key={idx} className={i.level === "error" ? "text-destructive" : "text-muted-foreground"}>
                  <AlertTriangle className="mr-1 inline size-3.5" aria-hidden />
                  {i.message}
                </li>
              ))}
            </ul>
          )}

          {preview.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-xs">
                <caption className="sr-only">Preview of the first rows that will be imported</caption>
                <thead className="bg-muted/50">
                  <tr>
                    {mappedFields.map((f) => (
                      <th key={f.name} scope="col" className="whitespace-nowrap px-2 py-1.5 text-left font-medium">
                        {f.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.map((r, idx) => (
                    <tr key={idx} className="border-t border-border">
                      {mappedFields.map((f) => (
                        <td key={f.name} className="whitespace-nowrap px-2 py-1.5">
                          {r[f.name] ?? "—"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <DialogFooter>
            <span className="mr-auto self-center text-xs text-muted-foreground">
              {(result?.rows.length ?? 0).toLocaleString("en-IN")} rows ready
            </span>
            <Button variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={busy || errors.length > 0}>
              {busy ? "Importing…" : replaceId ? "Replace data" : "Import rows"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
