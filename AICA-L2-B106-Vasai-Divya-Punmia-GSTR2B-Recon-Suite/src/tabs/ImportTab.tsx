import { useState } from 'react';
import { Database, Download, FileUp, Pencil, Save, Smartphone, Trash2 } from 'lucide-react';
import { useApp } from '../ctx';
import type { DatasetKind, FirmDetails, Kind } from '../types';
import { sampleWorkbook } from '../lib/importer';
import { downloadSample } from '../lib/excel';
import { useInstallPrompt } from '../pwa';
import { Badge, Btn, Card, cx, Field, inputCls, Notice, PageHead } from '../components/ui';
import { KIND_LABEL } from '../components/MappingModal';

const SLOTS: { kind: Kind; title: string; hint: string; main: DatasetKind; sample: 'g2b' | 'bks' | 'cdn' | 'rcm'; big?: boolean }[] = [
  { kind: 'g2b', title: '1. GSTR-2B file', hint: 'Excel downloaded from the GST portal (B2B, B2BA and CDNR sheets are all read), or any sheet with GSTIN, invoice no. and tax columns.', main: 'g2b', sample: 'g2b', big: true },
  { kind: 'bks', title: '2. Purchase register', hint: 'Export from Tally, Busy, SAP, Zoho or any Excel / CSV.', main: 'bks', sample: 'bks', big: true },
  { kind: 'cdn_g2b', title: 'Credit / debit notes — GSTR-2B', hint: 'Only if your notes are in a separate file.', main: 'cdn_g2b', sample: 'cdn' },
  { kind: 'cdn_bks', title: 'Credit / debit notes — books', hint: 'Only if your notes are in a separate file.', main: 'cdn_bks', sample: 'cdn' },
  { kind: 'rcm', title: 'Reverse-charge (RCM) bills', hint: 'GTA, advocate, security and other RCM bills.', main: 'rcm', sample: 'rcm' },
];

export default function ImportTab({ onEditEngagement }: { onEditEngagement: () => void }) {
  const { eng, ds, info, startImport, clearImport, firm, saveFirm, toast } = useApp();
  return (
    <div className="flex flex-col gap-4">
      <PageHead
        title="Import & Settings"
        sub="Load the GSTR-2B and purchase register for this client. Each file opens a column-matching window before anything is saved. Reconciliation runs automatically once both are loaded."
      />

      <Card
        title="Client / engagement"
        right={
          <Btn small icon={<Pencil className="w-3 h-3" />} onClick={onEditEngagement}>
            Edit
          </Btn>
        }
      >
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
          <div>
            <span className="text-slate-500">Client</span>
            <p className="font-semibold text-slate-800">{eng.name}</p>
          </div>
          <div>
            <span className="text-slate-500">GSTIN</span>
            <p className="font-mono">{eng.gstin || '—'}</p>
          </div>
          <div>
            <span className="text-slate-500">Period</span>
            <p className="font-semibold">{eng.period || '—'}</p>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {SLOTS.filter((s) => s.big).map((s) => (
          <Slot key={s.kind} slot={s} count={ds[s.main].length} info={info[s.main]} extra={s.kind === 'g2b' ? ds.g2b_cdn.length + ds.g2b_excl.length : ds.bks_cdn.length + ds.bks_excl.length} onFile={(f) => startImport(s.kind, f)} onClear={() => clearImport(s.kind)} />
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {SLOTS.filter((s) => !s.big).map((s) => (
          <Slot key={s.kind} slot={s} count={ds[s.main].length} info={info[s.main]} onFile={(f) => startImport(s.kind, f)} onClear={() => clearImport(s.kind)} />
        ))}
      </div>

      <FirmCard firm={firm} onSave={saveFirm} onError={(m) => toast(m, 'error')} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Card title="Database & backup">
          <div className="flex flex-col gap-2 text-xs text-slate-600">
            <p>
              Everything is saved in a SQLite database on the computer running the app (<span className="font-mono">data\gstr2b_recon.db</span>). Download a copy before
              big changes, or regularly.
            </p>
            <a
              href="api/backup"
              className="self-start inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold px-3 py-2"
            >
              <Database className="w-3.5 h-3.5" />
              Download database backup
            </a>
          </div>
        </Card>
        <InstallCard />
      </div>
    </div>
  );
}

function Slot({
  slot,
  count,
  extra = 0,
  info,
  onFile,
  onClear,
}: {
  slot: (typeof SLOTS)[number];
  count: number;
  extra?: number;
  info?: { fileName: string; rowCount: number; importedAt: string };
  onFile: (f: File) => void;
  onClear: () => void;
}) {
  const [drag, setDrag] = useState(false);
  const loaded = count > 0 || extra > 0;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-3 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className={cx('font-bold text-slate-800', slot.big ? 'text-sm' : 'text-xs')}>{slot.title}</h3>
          <p className="text-[0.7rem] text-slate-500 mt-0.5">{slot.hint}</p>
        </div>
        <Btn small kind="ghost" icon={<Download className="w-3 h-3" />} onClick={() => downloadSample(sampleWorkbook(slot.sample), `Sample_${slot.kind}.xlsx`)} title="Download a sample file">
          Sample
        </Btn>
      </div>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onFile(f);
        }}
        className={cx(
          'flex flex-col items-center justify-center gap-1 border-2 border-dashed rounded-lg cursor-pointer text-center transition-colors',
          slot.big ? 'py-6' : 'py-4',
          drag ? 'border-teal-500 bg-teal-50' : 'border-slate-300 hover:border-teal-400 hover:bg-slate-50'
        )}
      >
        <FileUp className="w-6 h-6 text-teal-600" />
        <span className="text-xs font-semibold text-slate-700">{loaded ? 'Replace file' : 'Choose or drop a file'}</span>
        <span className="text-[0.65rem] text-slate-400">.xlsx, .xls or .csv</span>
        <input
          type="file"
          accept=".xlsx,.xls,.csv,.txt"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = '';
            if (f) onFile(f);
          }}
        />
      </label>
      {loaded && (
        <div className="flex items-center justify-between gap-2 text-[0.7rem]">
          <span className="min-w-0 truncate">
            <Badge tone="green">{count.toLocaleString('en-IN')} loaded</Badge> <span className="text-slate-500">{info?.fileName}</span>
            {info?.importedAt && <span className="text-slate-400"> · {info.importedAt}</span>}
          </span>
          <button
            type="button"
            className="text-slate-400 hover:text-red-600 p-1"
            title={`Clear ${KIND_LABEL[slot.kind]}`}
            onClick={() => window.confirm(`Remove the imported ${KIND_LABEL[slot.kind]} for this client?`) && onClear()}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

function FirmCard({ firm, onSave, onError }: { firm: FirmDetails; onSave: (f: FirmDetails) => Promise<void>; onError: (m: string) => void }) {
  const [f, setF] = useState(firm);
  const set = (k: keyof FirmDetails) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  return (
    <Card title="Your firm (printed on supplier notices and e-mails)">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <Field label="Company / CA firm name">
          <input className={inputCls} value={f.name} onChange={set('name')} placeholder="M/s ABC Retailers Ltd" />
        </Field>
        <Field label="Signatory / CA name">
          <input className={inputCls} value={f.ca} onChange={set('ca')} placeholder="CA Rohan Sen" />
        </Field>
        <Field label="Membership no.">
          <input className={inputCls} value={f.memNo} onChange={set('memNo')} placeholder="123456" />
        </Field>
        <Field label="Contact e-mail">
          <input className={inputCls} type="email" value={f.email} onChange={set('email')} placeholder="accounts@yourfirm.com" />
        </Field>
        <Field label="Contact phone">
          <input className={inputCls} value={f.phone} onChange={set('phone')} placeholder="+91 98765 43210" />
        </Field>
        <div className="flex items-end">
          <Btn kind="primary" icon={<Save className="w-3.5 h-3.5" />} onClick={() => onSave(f).catch((e) => onError((e as Error).message))}>
            Save firm details
          </Btn>
        </div>
      </div>
    </Card>
  );
}

function InstallCard() {
  const { canInstall, install, standalone, ios, secure } = useInstallPrompt();
  return (
    <Card title="Install on phone, tablet or desktop">
      <div className="flex flex-col gap-2 text-xs text-slate-600">
        {standalone ? (
          <Notice tone="ok">You are using the installed app.</Notice>
        ) : canInstall ? (
          <>
            <p>Install the app to open it from your home screen or Start menu like any other app.</p>
            <Btn kind="primary" className="self-start" icon={<Smartphone className="w-3.5 h-3.5" />} onClick={install}>
              Install app
            </Btn>
          </>
        ) : ios ? (
          <p>
            On iPhone / iPad: tap <b>Share</b>, then <b>Add to Home Screen</b>.
          </p>
        ) : !secure ? (
          <Notice tone="warn">
            Browsers allow installing only from <b>localhost</b> or an <b>https</b> address. On other computers and phones, open the network link and use the browser menu → <b>Add to Home
            screen</b> (a shortcut), or put the server behind https.
          </Notice>
        ) : (
          <p>
            Use the browser menu → <b>Install app</b> / <b>Add to Home screen</b>. (Chrome and Edge show it once the page has fully loaded.)
          </p>
        )}
      </div>
    </Card>
  );
}
