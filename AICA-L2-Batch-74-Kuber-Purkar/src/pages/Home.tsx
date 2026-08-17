import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Calculator, Plus, Trash2, Users, ArrowLeft, Download, Printer, Server, ShieldCheck, Save, FolderOpen } from 'lucide-react';
import { loadClients, makeClient, normalizeConfig, saveClients } from '../lib/store';
import type { ClientRecord } from '../lib/store';
import { serverHealth, apiListClients, apiSaveClient, apiDeleteClient, type LicenseInfo } from '../lib/api';
import { LicenseGate } from '../components/LicenseGate';
import type { UnitMode } from '../types/cma';
import { runCma } from '../engine/cmaEngine';
import { downloadCmaExcel } from '../lib/excelExport';
import { ConfigScreen } from '../components/ConfigScreen';
import { ActualsScreen } from '../components/ActualsScreen';
import { SimulatorScreen } from '../components/SimulatorScreen';
import { ReportsScreen } from '../components/ReportsScreen';
import { RatioWorkingsScreen } from '../components/RatioWorkingsScreen';

const SINGLE_FILE = (import.meta as unknown as { env?: Record<string, string | undefined> }).env?.VITE_SINGLE_FILE === 'true';

const NAV = [
  { id: 'config', label: '1. Framework Setup' },
  { id: 'actuals', label: '2. Audited Ledgers' },
  { id: 'sim', label: '3. Projections Simulator' },
  { id: 'report', label: '4. CMA Report' },
  { id: 'workings', label: '5. Ratio Workings' },
];

export default function Home() {
  const [clients, setClients] = React.useState<ClientRecord[]>(() => loadClients());
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [newName, setNewName] = React.useState('');
  const [tab, setTab] = React.useState('config');
  // 'checking' → probing server; 'local' → no server (pure static/dev); 'gate' → server present but unlicensed; 'server' → licensed server mode
  const [mode, setMode] = React.useState<'checking' | 'local' | 'gate' | 'server'>('checking');
  const [license, setLicense] = React.useState<LicenseInfo | null>(null);

  React.useEffect(() => {
    if (SINGLE_FILE) { setMode('local'); return; } // single-file edition: no server, no licensing
    let cancelled = false;
    (async () => {
      const health = await serverHealth();
      if (cancelled) return;
      if (!health) { setMode('local'); return; }
      setLicense(health);
      if (!health.licensed) { setMode('gate'); return; }
      const list = await apiListClients();
      if (cancelled) return;
      if (list) { setClients(list); saveClients(list); }
      setMode('server');
    })();
    return () => { cancelled = true; };
  }, []);

  const persist = (next: ClientRecord[], changed?: ClientRecord | { deletedId: string }) => {
    setClients(next);
    saveClients(next);
    if (mode !== 'server' || !changed) return;
    const done = (r: 'ok' | 'unlicensed' | 'offline') => {
      if (r === 'unlicensed') setMode('gate');
    };
    if ('deletedId' in changed) apiDeleteClient(changed.deletedId).then(done);
    else apiSaveClient(changed).then(done);
  };

  const active = clients.find(c => c.id === activeId) || null;

  const updateClient = (updated: ClientRecord) => {
    const normalized = { ...updated, config: normalizeConfig(updated.config), updatedAt: new Date().toISOString() };
    persist(clients.map(c => (c.id === normalized.id ? normalized : c)), normalized);
  };

  const result = React.useMemo(() => (active ? runCma(active.config, active.sim) : null), [active]);

  // ── Backup: download / restore all client data as one JSON file ──
  const fileRef = React.useRef<HTMLInputElement>(null);
  const exportBackup = () => {
    const blob = new Blob(
      [JSON.stringify({ app: 'cma-pro-builder', version: 1, exportedAt: new Date().toISOString(), clients }, null, 2)],
      { type: 'application/json' }
    );
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `cma-pro-backup-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const importBackup = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    f.text().then(t => {
      const data = JSON.parse(t);
      const list: ClientRecord[] = Array.isArray(data) ? data : data.clients;
      if (!Array.isArray(list)) throw new Error('bad');
      const map = new Map<string, ClientRecord>(clients.map(c => [c.id, c] as [string, ClientRecord]));
      for (const c of list) if (c && c.id && c.config) map.set(c.id, c);
      persist([...map.values()]);
    }).catch(() => alert('Invalid backup file — choose a cma-pro-backup JSON file.'));
  };

  // ── Probing server ──
  if (mode === 'checking') {
    return (
      <div className="bg-slate-950 min-h-screen flex items-center justify-center text-slate-500 text-sm">
        Loading…
      </div>
    );
  }

  // ── Activation gate (server present, not licensed) ──
  if (mode === 'gate' && license) {
    return <LicenseGate info={license} onActivated={(li) => { setLicense(li); if (li.licensed) { apiListClients().then(list => { if (list) { setClients(list); saveClients(list); } setMode('server'); }); } }} />;
  }

  // ── Client list view ──
  if (!active) {
    return (
      <div className="bg-slate-950 min-h-screen text-slate-200 font-sans antialiased">
        <header className="bg-slate-900/60 backdrop-blur-md border-b border-slate-800/80 px-6 py-5 sticky top-0 z-50">
          <div className="max-w-4xl mx-auto flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 text-white rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/30 border border-indigo-400/20 shrink-0">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight font-display">
                CMA <span className="text-indigo-400 font-normal">Pro Builder</span>
              </h1>
              <p className="text-[11px] text-slate-400 font-medium">
                Credit Monitoring Arrangement · CC / Term Loan appraisal suite
                {SINGLE_FILE && <span className="ml-2 bg-slate-800 text-slate-400 rounded-full px-2 py-0.5 text-[10px]">Single-File Edition</span>}
              </p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <Button variant="outline" size="sm" className="border-slate-700 text-xs" onClick={exportBackup} disabled={clients.length === 0}>
                <Save className="mr-1.5 h-3.5 w-3.5" /> Backup
              </Button>
              <Button variant="outline" size="sm" className="border-slate-700 text-xs" onClick={() => fileRef.current?.click()}>
                <FolderOpen className="mr-1.5 h-3.5 w-3.5" /> Restore
              </Button>
              <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={importBackup} />
              {mode === 'server' && license && (
                <div className="flex items-center gap-2 text-[11px] bg-emerald-950/50 border border-emerald-800/60 text-emerald-300 rounded-full px-3 py-1.5">
                  <Server className="h-3.5 w-3.5" />
                  <span>LAN server{license.keyType ? ` · ${license.keyType}${license.year ? ' ' + license.year : ''}` : ''}{license.expiry ? ` · valid till ${license.expiry}` : ''}</span>
                  <ShieldCheck className="h-3.5 w-3.5" />
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
          <Card className="bg-slate-900 border-slate-800 rounded-3xl shadow-xl">
            <CardContent className="pt-6 space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="New client / company name…"
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && newName.trim()) { const c = makeClient(newName.trim()); persist([...clients, c], c); setNewName(''); setActiveId(c.id); } }}
                  className="bg-slate-950 border-slate-700"
                />
                <Button onClick={() => { if (!newName.trim()) return; const c = makeClient(newName.trim()); persist([...clients, c], c); setNewName(''); setActiveId(c.id); }} className="bg-indigo-600 hover:bg-indigo-500">
                  <Plus className="mr-2 h-4 w-4" /> New Client
                </Button>
              </div>

              {clients.length === 0 && (
                <div className="text-center py-12 text-slate-500">
                  <Users className="h-10 w-10 mx-auto mb-3 opacity-40" />
                  <p>No clients yet. Create one to start building a CMA report.</p>
                </div>
              )}

              <div className="divide-y divide-slate-800">
                {clients.map(c => (
                  <div key={c.id} className="flex items-center justify-between py-3">
                    <button className="text-left flex-1 hover:text-indigo-300 transition-colors" onClick={() => { setActiveId(c.id); setTab('config'); }}>
                      <div className="font-medium text-slate-100">{c.name}</div>
                      <div className="text-xs text-slate-500">
                        FY {c.config.startYear}-{String(c.config.startYear + 1).slice(-2)} · {c.config.actualYears}A + 1E + {c.config.projectedYears}P ·
                        {' '}{c.config.loan.loanType.toUpperCase()} · updated {new Date(c.updatedAt).toLocaleDateString('en-IN')}
                      </div>
                    </button>
                    <Button variant="ghost" size="icon" onClick={() => persist(clients.filter(x => x.id !== c.id), { deletedId: c.id })}>
                      <Trash2 className="h-4 w-4 text-red-400" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <p className="text-center text-xs text-slate-600">Developed by Kuber R Purkar (7218973049)</p>
        </main>
      </div>
    );
  }

  // ── Client workspace ──
  return (
    <div className="bg-slate-950 min-h-screen text-slate-200 font-sans antialiased">
      <header className="bg-slate-900/60 backdrop-blur-md border-b border-slate-800/80 px-6 py-4 sticky top-0 z-50 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => setActiveId(null)} className="text-slate-400 hover:text-white">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight font-display">{active.name}</h1>
            <p className="text-[11px] text-slate-400">
              {active.config.actualYears} actual + 1 estimated + {active.config.projectedYears} projected ·
              {' '}{active.config.loan.loanType === 'both' ? 'CC + Term Loan' : active.config.loan.loanType === 'cc' ? 'Cash Credit' : 'Term Loan'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Select value={active.config.unit} onValueChange={v => updateClient({ ...active, config: { ...active.config, unit: v as UnitMode } })}>
            <SelectTrigger className="w-32 bg-slate-950 border-slate-700 h-9 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="rs">₹ Rupees</SelectItem>
              <SelectItem value="thousands">₹ '000</SelectItem>
              <SelectItem value="lakhs">₹ Lakhs</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" className="border-slate-700" onClick={() => result && downloadCmaExcel(result)}>
            <Download className="mr-2 h-4 w-4" /> Export Excel
          </Button>
          <Button variant="outline" size="sm" className="border-slate-700" onClick={() => { setTab('report'); setTimeout(() => window.print(), 300); }}>
            <Printer className="mr-2 h-4 w-4" /> Print / PDF
          </Button>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-4 md:px-6 py-6">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="grid w-full grid-cols-5 bg-slate-900 border border-slate-800 rounded-2xl p-1.5 h-auto">
            {NAV.map(n => (
              <TabsTrigger
                key={n.id}
                value={n.id}
                className="rounded-xl py-2.5 text-[11px] font-bold uppercase tracking-wider data-[state=active]:bg-indigo-600 data-[state=active]:text-white text-slate-400"
              >
                {n.label}
              </TabsTrigger>
            ))}
          </TabsList>
          <TabsContent value="config" className="mt-5"><ConfigScreen client={active} onChange={updateClient} /></TabsContent>
          <TabsContent value="actuals" className="mt-5"><ActualsScreen client={active} onChange={updateClient} /></TabsContent>
          <TabsContent value="sim" className="mt-5">{result && <SimulatorScreen client={active} onChange={updateClient} result={result} />}</TabsContent>
          <TabsContent value="report" className="mt-5">{result && <ReportsScreen client={active} result={result} />}</TabsContent>
          <TabsContent value="workings" className="mt-5">{result && <RatioWorkingsScreen client={active} result={result} />}</TabsContent>
        </Tabs>
      </main>

      <footer className="border-t border-slate-800/80 bg-slate-900/30 mt-16 px-6 py-6 text-center text-xs text-slate-600">
        <p>CMA Pro Builder · Credit Monitoring Arrangement suite</p>
        <p className="mt-1">Developed by Kuber R Purkar (7218973049)</p>
      </footer>
    </div>
  );
}
