import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Ban,
  BarChart3,
  ClipboardList,
  Download,
  FileSpreadsheet,
  GitCompareArrows,
  HeartPulse,
  LayoutDashboard,
  Mail,
  Menu,
  MonitorDown,
  Plus,
  Receipt,
  RefreshCcw,
  ScrollText,
  Sparkles,
  Truck,
  Upload,
  X,
} from 'lucide-react';
import { api } from './api';
import { AppCtx, type Ctx, type TabId } from './ctx';
import type { BlockedCredit, DatasetKind, Engagement, EngagementState, FirmDetails, Kind, Row, Supplier } from './types';
import { invKey, rcmRegister, runAll } from './lib/engine';
import { biggestSheet, importWorkbook, readWorkbook, type Mapping } from './lib/importer';
import { categoryById } from './lib/rules';
import { downloadWorkbook, stamp } from './lib/excel';
import { fullWorkbook } from './lib/exports';
import { Btn, Busy, cx, Field, inputCls, Modal, Toasts, type Toast } from './components/ui';
import { KIND_LABEL, MappingModal, type PendingImport } from './components/MappingModal';
import { BlockModal, RemarkModal, SupplierModal } from './components/Dialogs';
import { useInstallPrompt } from './pwa';
import { useDevice } from './device';
import { PwaBanners } from './components/PwaBanners';
import ImportTab from './tabs/ImportTab';
import G2bTab from './tabs/G2bTab';
import DashboardTab from './tabs/DashboardTab';
import LedgerTab from './tabs/LedgerTab';
import SmartTab from './tabs/SmartTab';
import CdnTab from './tabs/CdnTab';
import RcmTab from './tabs/RcmTab';
import BlockedTab from './tabs/BlockedTab';
import FollowUpTab from './tabs/FollowUpTab';
import ReportsTab from './tabs/ReportsTab';
import HealthTab from './tabs/HealthTab';
import AuditTab from './tabs/AuditTab';

const NAV: { id: TabId; label: string; icon: ReactNode }[] = [
  { id: 'imp', label: 'Import & Settings', icon: <Upload className="w-4 h-4" /> },
  { id: 'g2b', label: 'GSTR-2B Invoices', icon: <FileSpreadsheet className="w-4 h-4" /> },
  { id: 'dash', label: 'Compliance Dashboard', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'recon', label: 'Reconciliation Ledger', icon: <GitCompareArrows className="w-4 h-4" /> },
  { id: 'smart', label: 'Smart Match Runs', icon: <Sparkles className="w-4 h-4" /> },
  { id: 'cdn', label: 'CDN Registry', icon: <Receipt className="w-4 h-4" /> },
  { id: 'rcm', label: 'RCM Purchase Bills', icon: <Truck className="w-4 h-4" /> },
  { id: 'blocked', label: 'Blocked Credits 17(5)', icon: <Ban className="w-4 h-4" /> },
  { id: 'follow', label: 'Supplier Follow-ups', icon: <Mail className="w-4 h-4" /> },
  { id: 'reports', label: 'Filing Reports', icon: <BarChart3 className="w-4 h-4" /> },
  { id: 'health', label: 'ITC Health Check', icon: <HeartPulse className="w-4 h-4" /> },
  { id: 'audit', label: 'Audit Logs', icon: <ScrollText className="w-4 h-4" /> },
];
const BOTTOM: TabId[] = ['imp', 'dash', 'recon', 'follow'];
const BOTTOM_LABEL: Partial<Record<TabId, string>> = { imp: 'Import', dash: 'Dashboard', recon: 'Ledger', follow: 'Follow-ups' };
const TAB_IDS = new Set<string>(['imp', 'g2b', 'dash', 'recon', 'smart', 'cdn', 'rcm', 'blocked', 'follow', 'reports', 'health', 'audit']);

/** Home-screen shortcuts open the app at ?tab=dash etc. */
function initialTab(): TabId {
  const fromUrl = new URLSearchParams(location.search).get('tab');
  if (fromUrl && TAB_IDS.has(fromUrl)) return fromUrl as TabId;
  const saved = store.get('gsr-tab');
  return saved && TAB_IDS.has(saved) ? (saved as TabId) : 'imp';
}

const EMPTY_FIRM: FirmDetails = { name: '', ca: '', memNo: '', email: '', phone: '' };
const LAST_KEY = 'gsr-last-engagement';
const store = {
  get: (k: string) => {
    try {
      return localStorage.getItem(k);
    } catch {
      return null;
    }
  },
  set: (k: string, v: string) => {
    try {
      localStorage.setItem(k, v);
    } catch {
      /* private mode */
    }
  },
};

const SAVE_KINDS: Record<Kind, DatasetKind[]> = {
  g2b: ['g2b', 'g2b_cdn', 'g2b_excl'],
  bks: ['bks', 'bks_cdn', 'bks_excl'],
  cdn_g2b: ['cdn_g2b'],
  cdn_bks: ['cdn_bks'],
  rcm: ['rcm'],
};

export default function App() {
  const [engs, setEngs] = useState<Engagement[] | null>(null);
  const [engId, setEngId] = useState<number | null>(null);
  const [st, setSt] = useState<EngagementState | null>(null);
  const [suppliers, setSuppliers] = useState<Record<string, Supplier>>({});
  const [firm, setFirm] = useState<FirmDetails>(EMPTY_FIRM);
  const [tab, setTab] = useState<TabId>(initialTab);
  const device = useDevice();
  const [drawer, setDrawer] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [busyText, setBusyText] = useState<string | null>(null);
  const [fatal, setFatal] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingImport | null>(null);
  const [blockRow, setBlockRow] = useState<Row | null>(null);
  const [remark, setRemark] = useState<{ key: string; label: string } | null>(null);
  const [supplier, setSupplier] = useState<{ gstin: string; name: string } | null>(null);
  const [engForm, setEngForm] = useState<Partial<Engagement> | null>(null);
  const [tol, setTol] = useState(100);
  const toastId = useRef(0);

  const toast = useCallback((msg: string, kind: 'ok' | 'error' = 'ok') => {
    const id = ++toastId.current;
    setToasts((t) => [...t, { id, msg, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === 'error' ? 6000 : 3500);
  }, []);

  /* ------------------------------- Loading -------------------------------- */

  const loadEngagements = useCallback(async () => {
    const list = await api.listEngagements();
    setEngs(list);
    return list;
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [list, sup, f] = await Promise.all([api.listEngagements(), api.suppliers(), api.firm()]);
        setEngs(list);
        setSuppliers(Object.fromEntries(sup.map((s) => [s.gstin, s])));
        setFirm({ ...EMPTY_FIRM, ...f });
        const last = Number(store.get(LAST_KEY));
        const pick = list.find((e) => e.id === last) ?? list[0];
        if (pick) setEngId(pick.id);
        else setEngForm({ name: '', gstin: '', period: '' });
      } catch (e) {
        setFatal((e as Error).message);
      }
    })();
  }, []);

  const reload = useCallback(async () => {
    if (engId == null) return;
    const s = await api.state(engId);
    setSt(s);
    setTol(s.engagement.tolerance);
  }, [engId]);

  useEffect(() => {
    if (engId == null) return;
    store.set(LAST_KEY, String(engId));
    setSt(null);
    reload().catch((e) => toast((e as Error).message, 'error'));
  }, [engId, reload, toast]);

  useEffect(() => store.set('gsr-tab', tab), [tab]);

  // Tolerance is saved with the engagement a moment after the user stops typing.
  useEffect(() => {
    if (!st || tol === st.engagement.tolerance) return;
    const t = setTimeout(() => {
      api
        .updateEngagement(st.engagement.id, { tolerance: tol })
        .then((e) => setSt((s) => (s ? { ...s, engagement: e } : s)))
        .catch((err) => toast((err as Error).message, 'error'));
    }, 600);
    return () => clearTimeout(t);
  }, [tol, st, toast]);

  const recon = useMemo(() => (st ? runAll(st.datasets, tol, st.blocked) : null), [st, tol]);

  const log = useCallback(
    async (tag: string, msg: string) => {
      if (engId == null) return;
      await api.log(engId, tag, msg).catch(() => {});
    },
    [engId]
  );

  /* ------------------------------- Import --------------------------------- */

  const startImport = useCallback(
    async (kind: Kind, file: File) => {
      setBusyText(`Reading ${file.name}...`);
      try {
        const wb = await readWorkbook(file);
        if (!wb.SheetNames.length) throw new Error('The workbook has no sheets.');
        setPending({ kind, file, wb, sheet: biggestSheet(wb) });
      } catch (e) {
        toast(`Could not read ${file.name}: ${(e as Error).message}`, 'error');
      } finally {
        setBusyText(null);
      }
    },
    [toast]
  );

  const confirmImport = async (mapping: Mapping, allSheets: boolean, sheet: string) => {
    if (!pending || engId == null) return;
    const p = pending;
    setPending(null);
    setBusyText('Importing and saving to the database...');
    try {
      const out = importWorkbook(p.wb, p.kind, mapping, { allSheets, sheet });
      const sets: Partial<Record<DatasetKind, Row[]>> =
        p.kind === 'g2b'
          ? { g2b: out.main, g2b_cdn: out.cdn, g2b_excl: out.excluded }
          : p.kind === 'bks'
            ? { bks: out.main, bks_cdn: out.cdn, bks_excl: out.excluded }
            : p.kind === 'rcm'
              ? { rcm: out.main }
              : { [p.kind]: out.cdn };
      const count = (sets[SAVE_KINDS[p.kind][0]] ?? []).length;
      if (!count && !out.excluded.length) throw new Error('No usable rows were found. Check the column mapping and sheet.');
      await api.saveDatasets(engId, p.file.name, sets);
      let autoBlocked = 0;
      if ((p.kind === 'g2b' || p.kind === 'bks') && out.blockedRows.length) {
        const res = await api.addBlocked(
          engId,
          out.blockedRows.map(({ row, catId, reason }) => {
            const c = categoryById(catId);
            return { gstin: row.gstin, invKey: invKey(row.inv), inv: row.inv, name: row.name, date: row.date, taxable: row.taxable, igst: row.igst, cgst: row.cgst, sgst: row.sgst, catId, catLbl: c.lbl, sec: c.sec, reason, origin: 'auto' as const };
          })
        );
        autoBlocked = res.added;
      }
      const parts = [`${count} ${p.kind === 'g2b' || p.kind === 'bks' ? 'invoices' : 'rows'}`];
      if (out.cdn.length && (p.kind === 'g2b' || p.kind === 'bks')) parts.push(`${out.cdn.length} credit/debit notes`);
      if (out.excluded.length) parts.push(`${out.excluded.length} rows excluded`);
      if (out.rcmCount) parts.push(`${out.rcmCount} possible RCM`);
      if (autoBlocked) parts.push(`${autoBlocked} possible 17(5) blocked`);
      const msg = `Imported ${KIND_LABEL[p.kind]} from "${p.file.name}" (${out.sheetsUsed} sheet${out.sheetsUsed === 1 ? '' : 's'}): ${parts.join(', ')}.`;
      await log('IMPORT', msg);
      await reload();
      toast(msg);
    } catch (e) {
      toast(`Import failed: ${(e as Error).message}`, 'error');
      await log('ERROR', `Import of "${p.file.name}" failed: ${(e as Error).message}`);
    } finally {
      setBusyText(null);
    }
  };

  const clearImport = async (kind: Kind) => {
    if (engId == null) return;
    await api.clearDatasets(engId, SAVE_KINDS[kind]);
    await log('IMPORT', `Cleared ${KIND_LABEL[kind]}.`);
    await reload();
    toast(`${KIND_LABEL[kind]} cleared.`);
  };

  /* --------------------------- Blocks and remarks ------------------------- */

  const confirmBlock = async (catId: string, reason: string) => {
    if (!blockRow || engId == null) return;
    const r = blockRow;
    setBlockRow(null);
    const c = categoryById(catId);
    try {
      await api.addBlocked(engId, [{ gstin: r.gstin, invKey: invKey(r.inv), inv: r.inv, name: r.name, date: r.date, taxable: r.taxable, igst: r.igst, cgst: r.cgst, sgst: r.sgst, catId, catLbl: c.lbl, sec: c.sec, reason, origin: 'manual' }]);
      await log('BLOCK', `Blocked ITC on invoice ${r.inv} (${r.gstin}) under Section ${c.sec}.`);
      await reload();
      toast(`Invoice ${r.inv} blocked under Section ${c.sec}.`);
    } catch (e) {
      toast((e as Error).message, 'error');
    }
  };

  const setActive = async (b: BlockedCredit, active: boolean) => {
    if (engId == null) return;
    try {
      await api.setBlockedActive(engId, b.id, active);
      await log('BLOCK', `${active ? 'Blocked again' : 'Released'}: invoice ${b.inv} (${b.gstin}).`);
      await reload();
      toast(`Invoice ${b.inv} ${active ? 'blocked again' : 'released'}.`);
    } catch (e) {
      toast((e as Error).message, 'error');
    }
  };

  const saveRemark = async (text: string) => {
    if (!remark || engId == null || !st) return;
    const { key } = remark;
    setRemark(null);
    try {
      await api.setRemark(engId, key, text);
      const remarks = { ...st.remarks };
      if (text.trim()) remarks[key] = text.trim();
      else delete remarks[key];
      setSt({ ...st, remarks });
      await log('NOTE', `${text.trim() ? 'Note saved' : 'Note deleted'} for ${key.replace('||', ' / ')}.`);
    } catch (e) {
      toast((e as Error).message, 'error');
    }
  };

  const saveSupplier = async (s: Supplier) => {
    setSupplier(null);
    try {
      const saved = await api.saveSupplier(s);
      setSuppliers((m) => ({ ...m, [saved.gstin]: saved }));
      await log('SUPPLIER', `Supplier ${saved.gstin} updated: MSME ${saved.msmeStatus}${saved.udyamNumber ? `, Udyam ${saved.udyamNumber}` : ''}.`);
      toast('Supplier details saved.');
    } catch (e) {
      toast((e as Error).message, 'error');
    }
  };

  const saveFirm = useCallback(
    async (f: FirmDetails) => {
      const saved = await api.saveFirm(f);
      setFirm(saved);
      toast('Firm details saved.');
    },
    [toast]
  );

  /* ------------------------------ Engagements ------------------------------ */

  const saveEngagement = async () => {
    if (!engForm) return;
    const name = (engForm.name ?? '').trim();
    if (!name) return toast('Enter the client name.', 'error');
    try {
      if (engForm.id) {
        await api.updateEngagement(engForm.id, { name, gstin: engForm.gstin ?? '', period: engForm.period ?? '' });
        await reload();
      } else {
        const e = await api.createEngagement({ name, gstin: engForm.gstin ?? '', period: engForm.period ?? '', tolerance: 100 });
        setEngId(e.id);
        setTab('imp');
      }
      await loadEngagements();
      setEngForm(null);
    } catch (e) {
      toast((e as Error).message, 'error');
    }
  };

  const deleteEngagement = async () => {
    if (!engForm?.id) return;
    if (!window.confirm(`Delete "${engForm.name}" and all its imported data, blocks and notes? This cannot be undone.`)) return;
    try {
      await api.deleteEngagement(engForm.id);
      const list = await loadEngagements();
      setEngForm(null);
      if (list[0]) setEngId(list[0].id);
      else {
        setEngId(null);
        setSt(null);
        setEngForm({ name: '', gstin: '', period: '' });
      }
      toast('Engagement deleted.');
    } catch (e) {
      toast((e as Error).message, 'error');
    }
  };

  const exportAll = () => {
    if (!st || !recon) return;
    downloadWorkbook(`GSTR2B_Recon_${st.engagement.name.replace(/[^\w]+/g, '_')}_${stamp()}`, fullWorkbook(st.datasets, recon, st.blocked, st.remarks, suppliers, tol));
    log('EXPORT', 'Full Excel workbook downloaded.');
  };

  /* -------------------------------- Render -------------------------------- */

  const ctx: Ctx | null = useMemo(
    () =>
      st && recon
        ? {
            eng: { ...st.engagement, tolerance: tol },
            ds: st.datasets,
            info: st.datasetInfo,
            blocked: st.blocked,
            remarks: st.remarks,
            recon,
            suppliers,
            firm,
            goto: (t) => {
              setTab(t);
              setDrawer(false);
              window.scrollTo({ top: 0 });
            },
            toast,
            log,
            reload,
            startImport,
            clearImport,
            openBlock: setBlockRow,
            unblock: (b) => setActive(b, false),
            reblock: (b) => setActive(b, true),
            openRemark: (key, label) => setRemark({ key, label }),
            openSupplier: (gstin, name) => setSupplier({ gstin, name }),
            saveFirm,
            busy: setBusyText,
          }
        : null,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [st, recon, suppliers, firm, tol, toast, log, reload, startImport, saveFirm]
  );

  if (fatal) {
    return (
      <div className="min-h-full flex items-center justify-center p-6">
        <div className="bg-white border border-red-200 rounded-xl p-6 max-w-md text-sm">
          <p className="font-bold text-red-700 mb-2">The app server is not reachable</p>
          <p className="text-slate-600">{fatal}</p>
          <p className="text-slate-500 mt-3 text-xs">Start the app with 1-Start-Localhost.bat (or 2-Start-Server-Host.bat), keep that window open, then reload this page.</p>
          <Btn className="mt-4" kind="primary" icon={<RefreshCcw className="w-3.5 h-3.5" />} onClick={() => location.reload()}>
            Reload
          </Btn>
        </div>
      </div>
    );
  }

  const phone = device.type === 'phone';
  const rail = device.rail;
  const goTab = (id: TabId) => {
    setTab(id);
    window.scrollTo({ top: 0 });
  };

  const nav = (onPick?: () => void) =>
    NAV.map((n) => (
      <button
        key={n.id}
        type="button"
        onClick={() => {
          goTab(n.id);
          onPick?.();
        }}
        className={cx(
          'nav-item w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-[0.8rem] text-left cursor-pointer',
          tab === n.id ? 'bg-teal-600 text-white font-semibold' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
        )}
      >
        {n.icon}
        <span className="truncate">{n.label}</span>
      </button>
    ));

  // Upright tablet / narrow window: icons only, labels as tooltips; the top button opens the full menu.
  const railNav = (
    <>
      <button type="button" onClick={() => setDrawer(true)} className="nav-item flex items-center justify-center h-11 rounded-md text-slate-300 hover:bg-slate-800 mb-1" aria-label="Open full menu" title="Menu">
        <Menu className="w-5 h-5" />
      </button>
      {NAV.map((n) => (
        <button
          key={n.id}
          type="button"
          title={n.label}
          aria-label={n.label}
          onClick={() => goTab(n.id)}
          className={cx('nav-item flex items-center justify-center h-11 rounded-md cursor-pointer', tab === n.id ? 'bg-teal-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white')}
        >
          {n.icon}
        </button>
      ))}
    </>
  );

  const counts = st && (
    <div className="mt-4 mx-1 p-3 rounded-lg bg-slate-800/60 text-[0.7rem] text-slate-400 grid grid-cols-2 gap-y-1">
      <span>2B invoices</span>
      <span className="text-right text-white nums">{st.datasets.g2b.length.toLocaleString('en-IN')}</span>
      <span>Books invoices</span>
      <span className="text-right text-white nums">{st.datasets.bks.length.toLocaleString('en-IN')}</span>
      <span>Blocked</span>
      <span className="text-right text-white nums">{st.blocked.filter((b) => b.active).length}</span>
      <span>RCM bills</span>
      <span className="text-right text-white nums">{rcmRegister(st.datasets).length}</span>
    </div>
  );

  return (
    <div className="min-h-full flex flex-col">
      {/* Header */}
      <header className="app-header sticky top-0 z-30 bg-slate-900 text-white border-b border-slate-950">
        <div className="flex items-center gap-2 px-3 sm:px-4 h-14">
          {phone && (
            <button type="button" className="p-2 -ml-1.5 rounded hover:bg-slate-800" onClick={() => setDrawer(true)} aria-label="Open menu">
              <Menu className="w-5 h-5" />
            </button>
          )}
          <div className="w-8 h-8 rounded-md bg-teal-600 flex items-center justify-center font-black text-[0.65rem] shrink-0">GST</div>
          <div className={cx('min-w-0 mr-2', phone ? 'hidden' : 'hidden md:block')}>
            <h1 className="text-sm font-bold leading-tight whitespace-nowrap">GSTR-2B Recon Suite</h1>
            {!rail && <p className="text-[0.65rem] text-slate-400 leading-tight">Smart matching · 17(5) · RCM · Rule 37A · GSTR-3B Table 4</p>}
          </div>
          <select
            className="min-w-0 flex-1 md:flex-none md:w-56 bg-slate-800 border border-slate-700 rounded-md text-xs px-2 py-1.5 text-white"
            value={engId ?? ''}
            onChange={(e) => setEngId(Number(e.target.value))}
            aria-label="Client / engagement"
          >
            {(engs ?? []).map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
                {e.period ? ` · ${e.period}` : ''}
              </option>
            ))}
          </select>
          <button type="button" className="p-1.5 rounded-md bg-slate-800 border border-slate-700 hover:bg-slate-700" title="New client / engagement" onClick={() => setEngForm({ name: '', gstin: '', period: '' })}>
            <Plus className="w-4 h-4" />
          </button>
          <div className="ml-auto flex items-center gap-2">
            {!phone && (
              <label className="flex items-center gap-1.5 text-[0.7rem] text-slate-300 whitespace-nowrap" title="Differences up to this amount count as matched">
                Tolerance ₹
                <input
                  type="number"
                  inputMode="decimal"
                  min={0}
                  value={tol}
                  onChange={(e) => setTol(Math.max(0, Number(e.target.value) || 0))}
                  className="tol-input w-16 bg-slate-800 border border-slate-700 rounded px-1.5 py-1 text-white text-xs nums"
                />
              </label>
            )}
            <InstallChip compact={phone} />
            {!phone && (
              <Btn kind="primary" small icon={<Download className="w-3.5 h-3.5" />} onClick={exportAll} disabled={!st}>
                {rail ? 'Export' : 'Full export'}
              </Btn>
            )}
          </div>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Computer / landscape tablet: full sidebar. Upright tablet: icon rail. Phone: none. */}
        {!phone && !rail && (
          <aside className="flex flex-col w-56 shrink-0 bg-slate-900 border-r border-slate-950 p-2 sticky top-14 h-[calc(100dvh-3.5rem)] overflow-y-auto">
            {nav()}
            {counts}
          </aside>
        )}
        {rail && <aside className="flex flex-col w-16 shrink-0 bg-slate-900 border-r border-slate-950 p-2 gap-0.5 sticky top-14 h-[calc(100dvh-3.5rem)] overflow-y-auto">{railNav}</aside>}

        {/* Full menu as a drawer (phone menu button, or rail's top button) */}
        {drawer && (phone || rail) && (
          <div className="fixed inset-0 z-40 bg-slate-900/60" onClick={() => setDrawer(false)}>
            <div className="w-72 max-w-[85vw] h-full bg-slate-900 p-2 overflow-y-auto fade-in" style={{ paddingTop: 'max(0.5rem, env(safe-area-inset-top))' }} onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between px-2 py-2 mb-1">
                <span className="text-white font-bold text-sm">GSTR-2B Recon Suite</span>
                <button type="button" onClick={() => setDrawer(false)} className="text-slate-400 p-1" aria-label="Close menu">
                  <X className="w-5 h-5" />
                </button>
              </div>
              {phone && (
                <label className="flex items-center justify-between gap-2 px-3 py-2 text-xs text-slate-300">
                  Tolerance ₹
                  <input type="number" inputMode="decimal" min={0} value={tol} onChange={(e) => setTol(Math.max(0, Number(e.target.value) || 0))} className="tol-input w-24 bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-white nums" />
                </label>
              )}
              {nav(() => setDrawer(false))}
              {phone && (
                <div className="px-1 mt-3">
                  <Btn kind="primary" className="w-full" icon={<Download className="w-3.5 h-3.5" />} onClick={exportAll} disabled={!st}>
                    Full Excel export
                  </Btn>
                </div>
              )}
              {counts}
            </div>
          </div>
        )}

        <main className={cx('flex-1 min-w-0', phone ? 'p-3 pb-28' : rail ? 'p-4 pb-8' : 'p-4 lg:p-5 pb-8')}>
          {!ctx ? (
            engs && engs.length === 0 ? null : <p className="text-sm text-slate-500 p-6">Loading...</p>
          ) : (
            <AppCtx.Provider value={ctx}>
              <div key={tab} className="fade-in">
                {tab === 'imp' && <ImportTab onEditEngagement={() => setEngForm({ ...ctx.eng })} />}
                {tab === 'g2b' && <G2bTab />}
                {tab === 'dash' && <DashboardTab />}
                {tab === 'recon' && <LedgerTab />}
                {tab === 'smart' && <SmartTab />}
                {tab === 'cdn' && <CdnTab />}
                {tab === 'rcm' && <RcmTab />}
                {tab === 'blocked' && <BlockedTab />}
                {tab === 'follow' && <FollowUpTab />}
                {tab === 'reports' && <ReportsTab />}
                {tab === 'health' && <HealthTab />}
                {tab === 'audit' && <AuditTab />}
              </div>
            </AppCtx.Provider>
          )}
        </main>
      </div>

      {/* Phone bottom bar */}
      {phone && (
        <nav className="fixed bottom-0 inset-x-0 z-30 bg-white border-t border-slate-200 grid grid-cols-5" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
          {BOTTOM.map((id) => {
            const n = NAV.find((x) => x.id === id)!;
            return (
              <button key={id} type="button" onClick={() => goTab(id)} className={cx('flex flex-col items-center justify-center gap-1 min-h-14 text-[0.65rem] font-medium', tab === id ? 'text-teal-700' : 'text-slate-500')}>
                {n.icon}
                <span className="truncate max-w-full px-1">{BOTTOM_LABEL[id]}</span>
              </button>
            );
          })}
          <button type="button" onClick={() => setDrawer(true)} className={cx('flex flex-col items-center justify-center gap-1 min-h-14 text-[0.65rem] font-medium', BOTTOM.includes(tab) ? 'text-slate-500' : 'text-teal-700')}>
            <ClipboardList className="w-4 h-4" />
            <span>More</span>
          </button>
        </nav>
      )}

      <PwaBanners phone={phone} />

      {pending && <MappingModal p={pending} onCancel={() => setPending(null)} onConfirm={confirmImport} />}
      {blockRow && <BlockModal row={blockRow} onCancel={() => setBlockRow(null)} onConfirm={confirmBlock} />}
      {remark && st && <RemarkModal label={remark.label} initial={st.remarks[remark.key] ?? ''} onCancel={() => setRemark(null)} onSave={saveRemark} />}
      {supplier && <SupplierModal gstin={supplier.gstin} name={supplier.name} current={suppliers[supplier.gstin]} onCancel={() => setSupplier(null)} onSave={saveSupplier} />}
      {engForm && (
        <Modal
          title={engForm.id ? 'Edit client / engagement' : engs?.length ? 'New client / engagement' : 'Welcome — set up your first client'}
          onClose={() => (engs?.length ? setEngForm(null) : undefined)}
          footer={
            <>
              {engForm.id && (
                <Btn kind="ghost" className="mr-auto text-red-600" onClick={deleteEngagement}>
                  Delete
                </Btn>
              )}
              {!!engs?.length && <Btn onClick={() => setEngForm(null)}>Cancel</Btn>}
              <Btn kind="primary" onClick={saveEngagement}>
                {engForm.id ? 'Save' : 'Create'}
              </Btn>
            </>
          }
        >
          <div className="flex flex-col gap-3">
            <p className="text-xs text-slate-500">Each client and period keeps its own imported files, blocked credits and notes in the database.</p>
            <Field label="Client name *">
              <input autoFocus className={inputCls} value={engForm.name ?? ''} onChange={(e) => setEngForm({ ...engForm, name: e.target.value })} placeholder="e.g. ABC Retailers Pvt Ltd" />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Client GSTIN">
                <input className={inputCls} value={engForm.gstin ?? ''} maxLength={15} onChange={(e) => setEngForm({ ...engForm, gstin: e.target.value.toUpperCase() })} placeholder="27AAAAA0000A1Z5" />
              </Field>
              <Field label="Period">
                <input className={inputCls} value={engForm.period ?? ''} onChange={(e) => setEngForm({ ...engForm, period: e.target.value })} placeholder="e.g. Oct 2026 or FY 2025-26" />
              </Field>
            </div>
          </div>
        </Modal>
      )}
      {busyText && <Busy text={busyText} />}
      <Toasts items={toasts} />
    </div>
  );
}

function InstallChip({ compact }: { compact: boolean }) {
  const { canInstall, install } = useInstallPrompt();
  if (!canInstall) return null;
  return (
    <Btn small kind="dark" className="border-slate-600" icon={<MonitorDown className="w-3.5 h-3.5" />} onClick={install}>
      {compact ? 'Install' : 'Install app'}
    </Btn>
  );
}
