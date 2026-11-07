import { useState } from 'react';
import { Download } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { excelBlob, deliverBlob } from '@/lib/spreadsheet';
import { toCsv } from '@/lib/procurement';
export function ExportFiles({filename, rows}: {filename: string; rows: Record<string, unknown>[]}) {
 const [file, setFile] = useState<Blob | null>(null);
 const [busy, setBusy] = useState(false);
 return <div className="flex flex-wrap gap-2">
  <Button variant="outline" size="sm" disabled={!rows.length} onClick={() => deliverBlob(new Blob(['\uFEFF'+toCsv(rows)],{type:'text/csv;charset=utf-8'}),filename+'.csv')}><Download className="mr-2 size-4"/>CSV</Button>
  <Button variant="outline" size="sm" disabled={!rows.length || busy} onClick={() => {
   if(file) { deliverBlob(file,filename+'.xlsx'); setFile(null); return; }
   setBusy(true); void excelBlob(rows).then(setFile).catch(e => toast.error(String(e))).finally(() => setBusy(false));
  }}><Download className="mr-2 size-4"/>{busy ? 'Preparing…' : file ? 'Download Excel' : 'Prepare Excel'}</Button>
 </div>;
}
