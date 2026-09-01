import { useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, CheckCircle2, Download, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { logAudit, run, uid } from "@/lib/db";
import { autoMap, downloadTemplate, mapRows, parseFile, type ParsedSheet, type ValidationIssue } from "@/lib/import";
import { FIELDS, SOURCES, type FieldKey, type SourceKey } from "@/lib/types";
import { useImports, useRefresh } from "@/lib/useData";

export function ImportPanel({ clientId }: { clientId: string }) {
  const [source, setSource] = useState<SourceKey>("tally_sales");
  const [file, setFile] = useState<File | null>(null);
  const [sheet, setSheet] = useState<ParsedSheet | null>(null);
  const [map, setMap] = useState<Partial<Record<FieldKey, string>>>({});
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [saving, setSaving] = useState(false);
  const imports = useImports(clientId);
  const refresh = useRefresh();

  async function onFile(f: File) {
    try {
      const parsed = await parseFile(f);
      setFile(f);
      setSheet(parsed);
      const guessed = autoMap(parsed.headers);
      setMap(guessed);
      setIssues(mapRows(parsed.rows.slice(0, 500), guessed).issues);
      toast.success(`${parsed.rows.length} rows read from ${f.name}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "The file could not be read.");
    }
  }

  function updateMap(field: FieldKey, header: string) {
    const next = { ...map, [field]: header === "__none" ? undefined : header };
    setMap(next);
    if (sheet) setIssues(mapRows(sheet.rows.slice(0, 500), next).issues);
  }

  async function save() {
    if (!sheet || !file) return;
    const { data, issues: allIssues } = mapRows(sheet.rows, map);
    const errors = allIssues.filter((i) => i.severity === "error");
    if (errors.length) {
      setIssues(allIssues);
      toast.error(`${errors.length} row(s) cannot be imported. Please correct the highlighted problems.`);
      return;
    }
    setSaving(true);
    const importId = uid();
    await run("INSERT INTO imports (id, client_id, source, filename, row_count, created_at) VALUES (?,?,?,?,?,?)", [
      importId,
      clientId,
      source,
      file.name,
      data.length,
      new Date().toISOString(),
    ]);
    for (const r of data) {
      await run(
        `INSERT INTO txns (id, client_id, source, import_id, invoice_no, invoice_date, party_name, party_gstin,
          taxable_value, gst_rate, cgst, sgst, igst, cess, place_of_supply, voucher_type, reverse_charge,
          doc_type, original_invoice_no, supply_type, hsn)
         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
        [
          uid(), clientId, source, importId, r.invoice_no, r.invoice_date, r.party_name, r.party_gstin,
          r.taxable_value, r.gst_rate, r.cgst, r.sgst, r.igst, r.cess, r.place_of_supply, r.voucher_type,
          r.reverse_charge, r.doc_type, r.original_invoice_no, r.supply_type, r.hsn,
        ],
      );
    }
    await run("INSERT INTO mappings (client_id, source, map_json) VALUES (?,?,?) ON CONFLICT(client_id, source) DO UPDATE SET map_json=excluded.map_json", [
      clientId, source, JSON.stringify(map),
    ]);
    await logAudit(clientId, "Import", `${SOURCES.find((s) => s.key === source)?.label}: ${file.name} (${data.length} rows)`);
    setSaving(false);
    setSheet(null);
    setFile(null);
    refresh(["txns", "imports", "audit", "recon"]);
    toast.success(`Imported ${data.length} rows.`);
  }

  async function removeImport(id: string, label: string) {
    await run("DELETE FROM txns WHERE import_id=?", [id]);
    await run("DELETE FROM imports WHERE id=?", [id]);
    await logAudit(clientId, "Import deleted", label);
    refresh(["txns", "imports", "audit", "recon"]);
    toast.success("Import removed.");
  }

  const errorCount = issues.filter((i) => i.severity === "error").length;

  return (
    <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">1. Choose data and upload</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>Type of data</Label>
            <Select value={source} onValueChange={(v) => setSource(v as SourceKey)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {SOURCES.map((s) => (
                  <SelectItem key={s.key} value={s.key}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">{SOURCES.find((s) => s.key === source)?.note}</p>
          </div>

          <Button variant="outline" className="w-full" onClick={() => downloadTemplate(source)}>
            <Download className="mr-2 h-4 w-4" /> Download sample template
          </Button>

          <div className="space-y-1.5">
            <Label htmlFor="file">Excel or CSV file</Label>
            <input
              id="file"
              type="file"
              accept=".xlsx,.xls,.csv"
              className="block w-full cursor-pointer rounded border border-input bg-card p-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm"
              onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
            />
          </div>

          {sheet && (
            <Button className="w-full" disabled={saving || errorCount > 0} onClick={save}>
              <Upload className="mr-2 h-4 w-4" /> {saving ? "Saving..." : `Import ${sheet.rows.length} rows`}
            </Button>
          )}
        </CardContent>
      </Card>

      <div className="space-y-6">
        {sheet ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">2. Map the columns of your file</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-muted-foreground">
                Columns were matched automatically where possible. Please confirm each row below.
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                {FIELDS.map((f) => (
                  <div key={f.key} className="space-y-1">
                    <Label className="text-xs">
                      {f.label} {f.required && <span className="text-destructive">*</span>}
                    </Label>
                    <Select value={map[f.key] ?? "__none"} onValueChange={(v) => updateMap(f.key, v)}>
                      <SelectTrigger className="h-9"><SelectValue placeholder="Not mapped" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none">Not mapped</SelectItem>
                        {sheet.headers.map((h) => (
                          <SelectItem key={h} value={h}>{h}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                ))}
              </div>

              <div className="rounded border border-border bg-secondary/50 p-3">
                {issues.length === 0 ? (
                  <p className="flex items-center gap-2 text-sm text-success">
                    <CheckCircle2 className="h-4 w-4" /> No problems found in the checked rows.
                  </p>
                ) : (
                  <>
                    <p className="mb-2 flex items-center gap-2 text-sm font-medium">
                      <AlertTriangle className="h-4 w-4 text-warning" />
                      {errorCount} error(s) and {issues.length - errorCount} warning(s)
                    </p>
                    <ul className="max-h-44 space-y-1 overflow-auto text-xs text-muted-foreground">
                      {issues.slice(0, 100).map((i, n) => (
                        <li key={n}>
                          Row {i.row} · {i.field}: {i.message}{" "}
                          <Badge variant={i.severity === "error" ? "destructive" : "secondary"}>{i.severity}</Badge>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        ) : null}

        <Card>
          <CardHeader><CardTitle className="text-base">Imported files</CardTitle></CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data type</TableHead>
                  <TableHead>File</TableHead>
                  <TableHead className="num">Rows</TableHead>
                  <TableHead>Imported on</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(imports.data ?? []).map((im) => (
                  <TableRow key={im.id}>
                    <TableCell>{SOURCES.find((s) => s.key === im.source)?.label ?? im.source}</TableCell>
                    <TableCell className="text-muted-foreground">{im.filename}</TableCell>
                    <TableCell className="num">{im.row_count}</TableCell>
                    <TableCell className="text-muted-foreground">{new Date(im.created_at).toLocaleString("en-IN")}</TableCell>
                    <TableCell>
                      <Button size="sm" variant="ghost" onClick={() => removeImport(im.id, `${im.filename}`)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {(imports.data ?? []).length === 0 && (
                  <TableRow><TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">No files imported yet.</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
