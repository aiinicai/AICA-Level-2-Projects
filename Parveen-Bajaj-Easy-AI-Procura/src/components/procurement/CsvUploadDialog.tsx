import { useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { toCsvTemplate } from "@/lib/csv";
import { deliverBlob, readSpreadsheet, suggestMapping, mappedCsv } from "@/lib/spreadsheet";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ImportResult } from "@/lib/master-import";

type Preview = {
  fileName: string;
  rows: unknown[];
  issues: { line: number; message: string }[];
  ignoredColumns: string[];
};

export function CsvUploadDialog<T>({
  triggerLabel,
  title,
  description,
  templateHeaders,
  templateExample,
  templateFileName,
  existingCodes,
  parse,
  onImport,
  isPending,
}: {
  triggerLabel: string;
  title: string;
  description: string;
  templateHeaders: string[];
  templateExample: string[];
  templateFileName: string;
  existingCodes: string[];
  parse: (text: string, existingCodes: string[]) => ImportResult<T>;
  onImport: (rows: T[]) => Promise<void>;
  isPending: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [sheets, setSheets] = useState<{name: string; grid: string[][]}[]>([]);
  const [sheetIndex, setSheetIndex] = useState(0);
  const [mapping, setMapping] = useState<string[]>([]);
  const [reading, setReading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function reset() {
    setPreview(null);
    setSheets([]);
    if (fileRef.current) fileRef.current.value = "";
  }

  function downloadTemplate() {
    const blob = new Blob([toCsvTemplate(templateHeaders, templateExample)], {
      type: "text/csv;charset=utf-8",
    });
    deliverBlob(blob, templateFileName);
  }

  function updatePreview(grid: string[][], columns: string[], fileName: string) {
    const result = parse(mappedCsv(grid, templateHeaders, columns), existingCodes);
    setPreview({ fileName, rows: result.rows, issues: result.issues, ignoredColumns: (grid[0] ?? []).filter(h => !columns.includes(h)) });
  }
  async function readFile(file: File) {
    setReading(true); setPreview(null); setSheets([]);
    try {
      const loaded = await readSpreadsheet(file);
      const first = loaded[0];
      if (!first?.grid.length) throw new Error("No data found in the file.");
      const columns = suggestMapping(first.grid[0] ?? [], templateHeaders);
      setSheets(loaded); setSheetIndex(0); setMapping(columns);
      updatePreview(first.grid, columns, file.name);
    } catch (error) { toast.error(error instanceof Error ? error.message : "Could not read file"); }
    finally { setReading(false); }
  }

  async function submit() {
    if (!preview || preview.rows.length === 0) return;
    try {
      await onImport(preview.rows as T[]);
      setOpen(false);
      reset();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed");
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline">{triggerLabel}</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              ref={fileRef}
              type="file"
              accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className="max-w-xs text-sm"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void readFile(file);
              }}
            />
            <Button type="button" size="sm" variant="ghost" onClick={downloadTemplate}>
              Download template
            </Button>
          </div>

          {reading ? <p className="text-sm text-muted-foreground">Reading file…</p> : null}
          {sheets.length ? <div className="space-y-3">
            <Select value={String(sheetIndex)} onValueChange={v => {
              const index = Number(v); const sheet = sheets[index]; if (!sheet) return;
              const columns = suggestMapping(sheet.grid[0] ?? [], templateHeaders);
              setSheetIndex(index); setMapping(columns); updatePreview(sheet.grid, columns, preview?.fileName ?? sheet.name);
            }}><SelectTrigger aria-label="Worksheet"><SelectValue /></SelectTrigger><SelectContent>{sheets.map((sheet, i) => <SelectItem key={i} value={String(i)}>{sheet.name}</SelectItem>)}</SelectContent></Select>
            <div className="grid gap-3 sm:grid-cols-2">{templateHeaders.map((target, i) => <div key={target} className="space-y-1">
              <label className="text-xs text-muted-foreground">{target.replaceAll('_', ' ')}</label>
              <Select value={mapping[i] || '__none'} onValueChange={v => {
                const columns = [...mapping]; columns[i] = v === '__none' ? '' : v; setMapping(columns);
                const sheet = sheets[sheetIndex]; if (sheet) updatePreview(sheet.grid, columns, preview?.fileName ?? sheet.name);
              }}><SelectTrigger aria-label={`Map ${target}`}><SelectValue /></SelectTrigger><SelectContent>
                <SelectItem value="__none">Not mapped</SelectItem>{(sheets[sheetIndex]?.grid[0] ?? []).filter(Boolean).map((header, j) => <SelectItem key={j} value={header}>{header}</SelectItem>)}
              </SelectContent></Select>
            </div>)}</div>
          </div> : null}
          <p className="text-xs text-muted-foreground">
            Columns: <span className="font-mono">{templateHeaders.join(", ")}</span>
          </p>

          {preview ? (
            <div className="space-y-3 rounded-lg border border-border bg-background p-4">
              <p className="text-sm font-medium text-foreground">
                {preview.fileName}: {preview.rows.length} row
                {preview.rows.length === 1 ? "" : "s"} ready
                {preview.issues.length ? `, ${preview.issues.length} skipped` : ""}
              </p>

              {preview.ignoredColumns.length ? (
                <p className="text-xs text-muted-foreground">
                  Ignored columns: {preview.ignoredColumns.join(", ")}
                </p>
              ) : null}

              {preview.issues.length ? (
                <ul className="max-h-48 space-y-1 overflow-y-auto text-xs text-muted-foreground">
                  {preview.issues.slice(0, 25).map((issue) => (
                    <li key={`${issue.line}-${issue.message}`}>
                      <span className="num text-primary">Row {issue.line}</span> — {issue.message}
                    </li>
                  ))}
                  {preview.issues.length > 25 ? (
                    <li>…and {preview.issues.length - 25} more</li>
                  ) : null}
                </ul>
              ) : null}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button onClick={() => void submit()} disabled={!preview || preview.rows.length === 0 || isPending}>
            {isPending ? "Uploading…" : `Upload ${preview?.rows.length ?? 0} row${preview?.rows.length === 1 ? "" : "s"}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
