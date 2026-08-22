import { useRef, useState } from "react";
import { FileSpreadsheet, UploadCloud, CheckCircle2 } from "lucide-react";
import { parseFile, type RawRow } from "@/lib/recon";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface Props {
  title: string;
  hint: string;
  onLoaded: (rows: RawRow[], fileName: string) => void;
}

export function UploadZone({ title, hint, onLoaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [preview, setPreview] = useState<RawRow[]>([]);
  const [headers, setHeaders] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const handle = async (file: File) => {
    setError(null);
    try {
      const { rows, headers } = await parseFile(file);
      if (!rows.length) {
        setError("No rows found in this file.");
        return;
      }
      setFileName(file.name);
      setHeaders(headers);
      setPreview(rows.slice(0, 5));
      onLoaded(rows, file.name);
    } catch {
      setError("Could not read this file. Please upload a valid Excel or CSV export.");
    }
  };

  return (
    <Card className="p-5">
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      <p className="mt-1 text-xs text-muted-foreground">{hint}</p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files?.[0];
          if (f) void handle(f);
        }}
        className={`mt-4 flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors ${
          dragging ? "border-primary bg-accent" : "border-border bg-muted/40"
        }`}
      >
        {fileName ? (
          <>
            <CheckCircle2 className="size-7 text-matched" />
            <p className="mt-2 text-sm font-medium text-foreground">{fileName}</p>
            <p className="text-xs text-muted-foreground">{headers.length} columns detected</p>
          </>
        ) : (
          <>
            <UploadCloud className="size-7 text-primary" />
            <p className="mt-2 text-sm text-muted-foreground">Drag &amp; drop or browse</p>
            <p className="text-xs text-muted-foreground">.xlsx, .xls or .csv</p>
          </>
        )}
        <Button variant="outline" size="sm" className="mt-4" onClick={() => inputRef.current?.click()}>
          <FileSpreadsheet /> {fileName ? "Replace file" : "Choose file"}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handle(f);
          }}
        />
      </div>

      {error && <p className="mt-3 text-sm text-risk">{error}</p>}

      {preview.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            First 5 rows
          </p>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted">
                <tr>
                  {headers.slice(0, 8).map((h) => (
                    <th key={h} className="whitespace-nowrap px-2 py-2 font-medium text-foreground">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.map((r, i) => (
                  <tr key={i} className="border-t border-border">
                    {headers.slice(0, 8).map((h) => (
                      <td key={h} className="whitespace-nowrap px-2 py-1.5 text-muted-foreground">
                        {String(r[h] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Card>
  );
}
