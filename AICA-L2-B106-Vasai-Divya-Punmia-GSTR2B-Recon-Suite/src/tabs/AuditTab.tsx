import { useEffect, useMemo, useState } from 'react';
import { RefreshCcw } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../ctx';
import type { LogEntry } from '../types';
import { downloadWorkbook, stamp } from '../lib/excel';
import { Badge, Btn, Card, DataTable, ExportBtn, PageHead, Pills, type BadgeTone } from '../components/ui';

const TONE: Record<string, BadgeTone> = { IMPORT: 'teal', BLOCK: 'red', NOTE: 'sky', SUPPLIER: 'violet', 'FOLLOW-UP': 'amber', EXPORT: 'green', ERROR: 'red', SYS: 'slate' };

export default function AuditTab() {
  const { eng, toast } = useApp();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [tag, setTag] = useState('ALL');
  const load = () =>
    api
      .logs(eng.id)
      .then(setLogs)
      .catch((e) => toast((e as Error).message, 'error'));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => void load(), [eng.id]);
  const tags = useMemo(() => ['ALL', ...Array.from(new Set(logs.map((l) => l.tag)))], [logs]);
  const rows = tag === 'ALL' ? logs : logs.filter((l) => l.tag === tag);
  return (
    <div className="flex flex-col gap-3">
      <PageHead
        title="Audit Logs"
        sub={`Every import, block, note, supplier change and download for ${eng.name}, saved in the database with date and time.`}
        right={
          <>
            <Btn icon={<RefreshCcw className="w-3.5 h-3.5" />} onClick={load}>
              Refresh
            </Btn>
            <ExportBtn onClick={() => downloadWorkbook(`Audit_log_${stamp()}`, [{ name: 'Audit log', rows: rows.map((l) => ({ 'Date & time': l.createdAt, Type: l.tag, Event: l.message })) }])} />
          </>
        }
      />
      <Pills value={tag} onChange={setTag} options={tags.map((t) => ({ id: t, label: t === 'ALL' ? 'All' : t, count: t === 'ALL' ? logs.length : logs.filter((l) => l.tag === t).length }))} />
      <Card pad={false}>
        <DataTable
          cols={[
            { h: 'Date & time', cell: (l: LogEntry) => <span className="font-mono text-slate-500">{l.createdAt}</span> },
            { h: 'Type', cell: (l: LogEntry) => <Badge tone={TONE[l.tag] ?? 'slate'}>{l.tag}</Badge> },
            { h: 'Event', cell: (l: LogEntry) => l.message, wrap: true },
          ]}
          rows={rows}
          empty="No events yet."
          maxH="70vh"
        />
      </Card>
    </div>
  );
}
