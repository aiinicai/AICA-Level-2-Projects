import { useEffect, useState, type ReactNode } from 'react';
import { startTableCards } from './tableCards';
import { startRadioKeys } from './radioKeys';
import { onOutboxChange } from '../lib/outbox';
import { flushOutbox } from '../lib/storage';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useStore } from '../data/store';
import { useT, useTr } from '../i18n';
import { buildAlerts } from '../lib/alerts';
import { setDateLocale, todayIso } from '../lib/dates';
import { BRAND } from '../brand';
import { Icon } from './Icon';
import { Logo, useConfirm } from './common';

export interface NavDef { to: string; label: string; icon: string; count?: number }

/** Full navigation for admins — used by the sidebar (desktop) and the More page (mobile). */
export function useAdminSections() {
  const { s, me, scoped, client } = useStore();
  const alerts = buildAlerts(scoped.expenses, scoped.payments, todayIso(), { challans: scoped.challans, tallyMode: client?.tallyMode });
  const pendingReview = s.expenses.filter((e) => e.status === 'submitted').length;
  const openFindings = s.findings.filter((f) => f.status === 'open').length;
  const sections: { title?: string; items: NavDef[] }[] = me?.role === 'super_admin'
    ? [
        { items: [{ to: '/', label: 'Firm overview', icon: 'home' }, { to: '/review', label: 'Review queue', icon: 'check', count: pendingReview }] },
        { title: 'Selected client', items: [
          { to: '/mis', label: 'MIS dashboard', icon: 'chart' }, { to: '/ask', label: 'Ask your data', icon: 'radar' }, { to: '/entries', label: 'Expenses', icon: 'list' },
          { to: '/dues', label: 'Payments due', icon: 'wallet' }, { to: '/alerts', label: 'Alerts', icon: 'bell', count: alerts.length || undefined },
          { to: '/vendors', label: 'Vendors', icon: 'store' }, { to: '/reco', label: 'GST reco', icon: 'reco' }, { to: '/risk', label: 'Bill risk check', icon: 'radar' },
          { to: '/tds', label: 'TDS & Form 140', icon: 'shield' }, { to: '/gst', label: 'GST registers', icon: 'reco' }, { to: '/tally', label: 'Tally posting', icon: 'tally' },
          { to: '/bank', label: 'Bank statement', icon: 'bank' }, { to: '/inbox', label: 'Inbox', icon: 'inbox' }, { to: '/import', label: 'Import from Excel', icon: 'upload' },
          { to: '/reports', label: 'Reports', icon: 'download' }, { to: '/fy-close', label: 'Close the year', icon: 'lock' }, { to: '/settings', label: 'Client settings', icon: 'settings' }
        ] },
        { title: 'Platform', items: [
          { to: '/compliance', label: 'Compliance watch', icon: 'radar', count: openFindings || undefined },
          { to: '/masters', label: 'Tax masters', icon: 'sliders' }, { to: '/audit', label: 'Audit & health', icon: 'pulse' }, { to: '/privacy', label: 'Privacy & consent', icon: 'shield' }
        ] }
      ]
    : [
        { items: [
          { to: '/', label: 'Dashboard', icon: 'chart' }, { to: '/ask', label: 'Ask your data', icon: 'radar' }, { to: '/capture', label: 'Add expense', icon: 'camera' },
          { to: '/entries', label: 'Expenses', icon: 'list' }, { to: '/dues', label: 'Payments due', icon: 'wallet' },
          { to: '/alerts', label: 'Alerts', icon: 'bell', count: alerts.length || undefined }
        ] },
        { title: 'Manage', items: [
          { to: '/vendors', label: 'Vendors', icon: 'store' }, { to: '/risk', label: 'Bill risk check', icon: 'radar' }, { to: '/inbox', label: 'Inbox', icon: 'inbox' }, { to: '/import', label: 'Import from Excel', icon: 'upload' }, { to: '/bank', label: 'Bank statement', icon: 'bank' },
          { to: '/tds', label: 'TDS & challans', icon: 'shield' }, { to: '/gst', label: 'GST registers', icon: 'reco' }, { to: '/tally', label: 'Tally posting', icon: 'tally' },
          { to: '/reports', label: 'Reports', icon: 'download' }, { to: '/settings', label: 'Settings & team', icon: 'settings' }, { to: '/privacy', label: 'Privacy & consent', icon: 'shield' }
        ] }
      ];
  return { sections, alerts };
}

export function Shell({ children }: { children: ReactNode }) {
  const tr = useTr();
  const st = useStore();
  const { s, me, client } = st;
  const t = useT();
  const confirm = useConfirm();
  const nav = useNavigate();
  const { pathname } = useLocation();
  const [online, setOnline] = useState(navigator.onLine);

  useEffect(() => {
    const on = () => setOnline(true), off = () => setOnline(false);
    window.addEventListener('online', on); window.addEventListener('offline', off);
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  }, []);

  useEffect(() => startTableCards(), []); // phone card layout for wide tables
  useEffect(() => startRadioKeys(), []); // arrow keys in chip groups

  // offline outbox (live mode): send waiting files at start, when back online, and every 2 minutes
  const [waiting, setWaiting] = useState(0);
  useEffect(() => onOutboxChange(setWaiting), []);
  useEffect(() => {
    if (!online) return;
    const go = () => { flushOutbox(st.resolvePendingFile).catch(() => undefined); };
    go();
    const id = window.setInterval(go, 120_000);
    return () => window.clearInterval(id);
  }, [online, st.resolvePendingFile]);

  // language: dates and the page's lang attribute (screen readers, hyphenation)
  setDateLocale(s.lang);
  useEffect(() => { document.documentElement.lang = s.lang; }, [s.lang]);

  // Client brand colour drives the whole UI accent.
  useEffect(() => {
    const c = client?.brandColor ?? '#0f2a44';
    document.documentElement.style.setProperty('--brand', c);
    // readable text on the client's colour: dark text on light brand colours
    document.documentElement.style.setProperty('--brand-ink', luminance(c) > 0.5 ? '#14181f' : '#ffffff');
  }, [client?.brandColor]);

  const { sections, alerts } = useAdminSections();
  if (!me) return null;
  const role = me.role;
  const staffAlerts = alerts.filter((a) => a.kind === 'payment_overdue_30');
  const bellCount = role === 'sub_user' ? staffAlerts.length : alerts.length;

  const staffNav: NavDef[] = [
    { to: '/', label: t('home'), icon: 'home' },
    { to: '/entries', label: t('entries'), icon: 'list' },
    { to: '/capture', label: t('snap'), icon: 'camera' },
    { to: '/dues', label: t('dues'), icon: 'wallet' },
    { to: '/inbox', label: 'Inbox', icon: 'inbox' } // alerts stay on the bell in the header (U10)
  ];

  const mobileNav: NavDef[] = role === 'sub_user' ? staffNav
    : role === 'super_admin'
      ? [{ to: '/', label: 'Overview', icon: 'home' }, { to: '/review', label: 'Review', icon: 'check' }, { to: '/capture', label: 'Add', icon: 'camera' }, { to: '/compliance', label: 'Watch', icon: 'radar' }, { to: '/more', label: 'More', icon: 'more' }]
      : [{ to: '/', label: 'Dashboard', icon: 'chart' }, { to: '/entries', label: 'Expenses', icon: 'list' }, { to: '/capture', label: 'Add', icon: 'camera' }, { to: '/dues', label: 'Dues', icon: 'wallet' }, { to: '/more', label: 'More', icon: 'more' }];

  const displayName = client && role !== 'super_admin' ? client.name : BRAND.name;

  return (
    <div className={`shell ${role === 'sub_user' ? 'staff' : 'admin'}`}>
      {role !== 'sub_user' && (
        <aside className="sidebar">
          <div className="brandmark" style={{ padding: '4px 8px 14px' }}>
            <Logo name={displayName} url={role !== 'super_admin' ? client?.logoUrl : undefined} />
            <div className="ellipsis">{displayName}</div>
          </div>
          {sections.map((sec, i) => (
            <div key={i} className="stack" style={{ gap: 2 }}>
              {sec.title && <div className="nav-section">{tr(sec.title)}</div>}
              {sec.items.map((n) => (
                <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                  <Icon name={n.icon} size={18} /> {tr(n.label)}
                  {n.count ? <span className="nav-count">{n.count}</span> : null}
                </NavLink>
              ))}
            </div>
          ))}
          <div className="sidebar-foot">
            {BRAND.name} v0.1 · demo mode
          </div>
        </aside>
      )}

      <div className="main">
        <header className="topbar">
          <div className="brandmark grow">
            {role !== 'super_admin' && <span className={role === 'client_admin' ? 'mobile-only' : ''}><Logo name={displayName} url={client?.logoUrl} size={30} /></span>}
            {role === 'super_admin' ? (
              <select className="input sm" style={{ maxWidth: 260 }} value={st.clientId}
                onChange={(e) => st.setActiveClient(e.target.value)} aria-label={tr('Select client')}>
                {s.clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            ) : (
              <span className="ellipsis" style={{ fontSize: role === 'sub_user' ? 16 : 15 }}>
                {role === 'sub_user' ? displayName : <span className="muted small">{t('hello')}, {me.name.split(' ')[0]}</span>}
              </span>
            )}
          </div>
          <button className="icon-btn" onClick={() => st.setLang(s.lang === 'en' ? 'hi' : 'en')} title={t('language')} aria-label={t('language')}>
            <span style={{ fontWeight: 700, fontSize: 13 }}>{s.lang === 'en' ? 'अ' : 'A'}</span>
          </button>
          <button className="icon-btn" onClick={() => nav('/alerts')} aria-label={t('alerts')}>
            <Icon name="bell" />{bellCount > 0 && <span className="dot" />}
          </button>
          <button className="icon-btn" onClick={() => nav('/privacy')} aria-label={tr('Privacy & consent')} title={tr('Privacy & consent')}><Icon name="shield" /></button>
          <button className="icon-btn" onClick={async () => { if (await confirm(t('confirmLogout'), { ok: t('logout') })) { st.logout(); nav('/'); } }} aria-label={t('logout')} title={t('logout')}>
            <Icon name="logout" />
          </button>
        </header>
        {!online && <div className="banner warn" style={{ borderRadius: 0 }}><Icon name="alert" size={18} />{t('offline')}</div>}
        {waiting > 0 && <div className="banner info small" role="status" style={{ borderRadius: 0 }}><Icon name="upload" size={16} />{tr('{n} file(s) saved on this phone, waiting to upload — they are sent automatically when online.', { n: waiting })}</div>}
        <div key={pathname} className="route-anim">{children}</div>
      </div>

      {pathname !== '/capture' && <nav className="bottomnav">
        {mobileNav.map((n, i) => (
          <NavLink key={n.to} to={n.to} end={n.to === '/'} className={({ isActive }) => (i === 2 ? 'fab' : isActive ? 'active' : '')} aria-label={tr(n.label)}>
            <Icon name={n.icon} size={i === 2 ? 26 : 22} />
            {i !== 2 && <span>{tr(n.label)}</span>}
          </NavLink>
        ))}
      </nav>}
    </div>
  );
}

function luminance(hex: string): number {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex);
  if (!m) return 0;
  const n = parseInt(m[1], 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => v / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
