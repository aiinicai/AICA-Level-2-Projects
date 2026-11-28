import React, { useEffect, useMemo, useState } from 'react';
import {
  Building2,
  Eye,
  EyeOff,
  Maximize2,
  Menu,
  Minimize2,
  Search,
  X,
} from 'lucide-react';
import {
  buildTraceableKpis,
  computeFinancialStatements,
  computeProjectKpiSummary,
  generateRuleBasedCommentary,
  reconcileTrialBalance,
} from './engine/kpiEngine';
import { MODULE_META, t } from './utils/i18n';
import type {
  CurrencyCode,
  FontSizeScale,
  LanguageCode,
  MisDataset,
  ModuleId,
  ReportingBasis,
  ThemeId,
  UserRole,
} from './types/mis';
import {
  CashFlowTreasuryView,
  ExecutiveDashboardView,
  FinancialMisView,
  ProjectPerformanceView,
} from './components/ModulesCore';
import {
  BudgetCostControlView,
  CollectionsView,
  ConstructionPlanningView,
  ContractsProcurementView,
  SalesInventoryView,
} from './components/ModulesOperations';
import {
  FeasibilityScenarioView,
  FinancingCovenantsView,
  HandoverWarrantyView,
  RentalPropertiesView,
  RiskComplianceView,
} from './components/ModulesTreasuryAndRisk';
import {
  AiAnalystView,
  DataUploadView,
  ReportsExportsView,
  SettingsAdminView,
  WorkflowControlsView,
} from './components/ModulesGovernance';
import { SetupWizardModal } from './components/SetupWizardModal';

const THEMES: { id: ThemeId; label: string; isDark: boolean }[] = [
  { id: 'navy-gold', label: 'Executive Navy & Gold', isDark: false },
  { id: 'corporate-blue', label: 'Corporate White & Blue', isDark: false },
  { id: 'midnight-dark', label: 'Midnight Dark', isDark: true },
  { id: 'emerald-finance', label: 'Emerald Finance', isDark: false },
  { id: 'graphite-copper', label: 'Graphite & Copper', isDark: true },
  { id: 'minimal-pro', label: 'Minimal Professional', isDark: false },
];

export default function App() {
  const [dataset, setDataset] = useState<MisDataset | null>(null);
  const [users, setUsers] = useState<{ id: string; name: string; email: string; role: UserRole }[]>([]);
  const [currentUserId, setCurrentUserId] = useState('usr-cfo');
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [activeModule, setActiveModule] = useState<ModuleId>('executive');
  const [selectedPeriod, setSelectedPeriod] = useState('2026-11');
  const [basis, setBasis] = useState<ReportingBasis>('Monthly');
  const [currency, setCurrency] = useState<CurrencyCode>('OMR');
  const [companyFilterId, setCompanyFilterId] = useState<string | 'CONSOLIDATED'>('CONSOLIDATED');
  const [projectFilterId, setProjectFilterId] = useState<string | 'ALL'>('ALL');

  const [theme, setTheme] = useState<ThemeId>('navy-gold');
  const [lang, setLang] = useState<LanguageCode>('en');
  const [fontScale, setFontScale] = useState<FontSizeScale>('standard');
  const [masked, setMasked] = useState(false);
  const [presentationMode, setPresentationMode] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [globalSearch, setGlobalSearch] = useState('');
  const [wizardOpen, setWizardOpen] = useState(false);

  // Apply theme, RTL, dark class, and font scale cleanly
  useEffect(() => {
    const html = document.documentElement;
    html.setAttribute('data-theme', theme);
    html.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
    html.setAttribute('lang', lang);
    const themeDef = THEMES.find((x) => x.id === theme);
    if (themeDef?.isDark) html.classList.add('dark');
    else html.classList.remove('dark');
    const scaleMap: Record<FontSizeScale, string> = { compact: '0.92', standard: '1', large: '1.08' };
    html.style.setProperty('--re-font-scale', scaleMap[fontScale]);
  }, [theme, lang, fontScale]);

  const authenticateSession = async (userId: string) => {
    const res = await fetch('/api/auth/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId }),
    });
    if (res.ok) {
      const data = (await res.json()) as { token: string; user: { id: string } };
      setAuthToken(data.token);
      setCurrentUserId(data.user.id);
    }
  };

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const [bootRes] = await Promise.all([fetch('/api/bootstrap'), authenticateSession('usr-cfo')]);
        if (!bootRes.ok) throw new Error('Failed to load workspace data from SQLite server.');
        const data = (await bootRes.json()) as {
          dataset: MisDataset;
          users: { id: string; name: string; email: string; role: UserRole }[];
        };
        if (cancelled) return;
        setDataset(data.dataset);
        setUsers(data.users);
        const latest = data.dataset.periods[data.dataset.periods.length - 1];
        setSelectedPeriod(latest);
      } catch (err) {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : 'Initialization failed');
      }
    }
    void init();
    return () => {
      cancelled = true;
    };
  }, []);

  const currentUser = users.find((u) => u.id === currentUserId);
  const currentUserRole: UserRole = currentUser?.role ?? 'CFO_Admin';

  const statements = useMemo(() => {
    if (!dataset) return null;
    return computeFinancialStatements(
      dataset.trialBalance,
      dataset.periods,
      selectedPeriod,
      basis,
      companyFilterId,
      projectFilterId,
      dataset.policies,
      dataset.adjustments
    );
  }, [dataset, selectedPeriod, basis, companyFilterId, projectFilterId]);

  const projectKpis = useMemo(() => {
    if (!dataset) return [];
    return dataset.projects
      .filter((p) => (companyFilterId === 'CONSOLIDATED' ? true : p.companyId === companyFilterId))
      .filter((p) => (projectFilterId === 'ALL' ? true : p.id === projectFilterId))
      .map((p) =>
        computeProjectKpiSummary(p, dataset.units, dataset.budgets, dataset.contractors, dataset.constructionLogs, selectedPeriod)
      );
  }, [dataset, companyFilterId, projectFilterId, selectedPeriod]);

  const reconciliation = useMemo(() => {
    if (!dataset) return null;
    const idx = dataset.periods.indexOf(selectedPeriod);
    const prev = idx > 0 ? dataset.periods[idx - 1] : '';
    const currRows = dataset.trialBalance.filter(
      (r) => r.period === selectedPeriod && (companyFilterId === 'CONSOLIDATED' || r.companyId === companyFilterId)
    );
    const prevRows = dataset.trialBalance.filter(
      (r) => r.period === prev && (companyFilterId === 'CONSOLIDATED' || r.companyId === companyFilterId)
    );
    return reconcileTrialBalance(currRows, prevRows, dataset.glMappings, dataset.policies.materialityThresholdOMR);
  }, [dataset, selectedPeriod, companyFilterId]);

  const commentary = useMemo(() => {
    if (!dataset || !statements || !reconciliation) return null;
    return generateRuleBasedCommentary(dataset, statements, projectKpis, reconciliation, selectedPeriod);
  }, [dataset, statements, projectKpis, reconciliation, selectedPeriod]);

  const traceableKpis = useMemo(() => {
    if (!dataset || !statements) return [];
    return buildTraceableKpis(statements, projectKpis, dataset.facilities, selectedPeriod, currency, masked);
  }, [dataset, statements, projectKpis, selectedPeriod, currency, masked]);

  // Global quick search results across modules, projects & units
  const searchHits = useMemo(() => {
    const q = globalSearch.trim().toLowerCase();
    if (!q || !dataset) return null;
    const mods = MODULE_META.filter(
      (m) => m.labelEn.toLowerCase().includes(q) || m.labelAr.includes(q)
    ).slice(0, 4);
    const prjs = dataset.projects.filter(
      (p) => p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q)
    ).slice(0, 4);
    const units = dataset.units
      .filter((u) => u.unitCode.toLowerCase().includes(q) || (u.customerName ?? '').toLowerCase().includes(q))
      .slice(0, 5);
    return { mods, prjs, units };
  }, [globalSearch, dataset]);

  if (loadError) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="max-w-md rounded-lg border p-6 space-y-2" style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}>
          <h1 className="font-display text-base font-semibold text-rose-600">Unable to load RealEstate 360</h1>
          <p className="text-xs" style={{ color: 'var(--re-text-muted)' }}>{loadError}</p>
        </div>
      </div>
    );
  }

  if (!dataset || !statements || !reconciliation || !commentary) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="text-sm font-medium" style={{ color: 'var(--re-text-muted)' }}>
          Initializing RealEstate 360 Financial Engine & SQLite Workspace...
        </div>
      </div>
    );
  }

  const isArabic = lang === 'ar';
  const activeMeta = MODULE_META.find((m) => m.id === activeModule) ?? MODULE_META[0];
  const groups: ('Core MIS' | 'Operations & Delivery' | 'Treasury & Risk' | 'Governance & Tools')[] = [
    'Core MIS',
    'Operations & Delivery',
    'Treasury & Risk',
    'Governance & Tools',
  ];

  const renderSidebarContent = () => (
    <div className="flex flex-col h-full">
      <div className="px-4 py-4 border-b flex items-center justify-between gap-2" style={{ borderColor: 'rgba(148,163,184,0.18)' }}>
        <div className="flex items-center gap-2.5 min-w-0">
          <Building2 className="w-5 h-5 shrink-0" style={{ color: 'var(--re-accent)' }} />
          {!sidebarCollapsed && (
            <span className="font-display text-base font-bold tracking-tight truncate" style={{ color: 'var(--re-sidebar-text)' }}>
              {t(lang, 'brand')}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setSidebarCollapsed((c) => !c)}
          aria-label="Toggle sidebar width"
          className="hidden lg:inline-flex p-1 rounded hover:opacity-80"
          style={{ color: 'var(--re-sidebar-muted)' }}
        >
          <Menu className="w-4 h-4" />
        </button>
      </div>

      <nav aria-label="Primary MIS modules" className="flex-1 overflow-y-auto px-2.5 py-3 space-y-4">
        {groups.map((grp) => (
          <div key={grp} className="space-y-1">
            {!sidebarCollapsed && (
              <div className="px-2.5 text-[11px] font-medium" style={{ color: 'var(--re-sidebar-muted)' }}>
                {grp}
              </div>
            )}
            {MODULE_META.filter((m) => m.group === grp).map((mod) => {
              const active = activeModule === mod.id;
              return (
                <button
                  key={mod.id}
                  type="button"
                  onClick={() => {
                    setActiveModule(mod.id);
                    setMobileMenuOpen(false);
                  }}
                  title={isArabic ? mod.labelAr : mod.labelEn}
                  className="w-full text-left px-2.5 py-2 rounded-md text-xs font-medium transition-colors truncate"
                  style={
                    active
                      ? { backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }
                      : { color: 'var(--re-sidebar-text)' }
                  }
                >
                  {sidebarCollapsed ? (isArabic ? mod.labelAr : mod.labelEn).slice(0, 3) : isArabic ? mod.labelAr : mod.labelEn}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {!sidebarCollapsed && (
        <div className="p-3 border-t text-[11px] space-y-1" style={{ borderColor: 'rgba(148,163,184,0.18)', color: 'var(--re-sidebar-muted)' }}>
          <div className="truncate font-medium" style={{ color: 'var(--re-sidebar-text)' }}>
            {currentUser?.name ?? 'Nasser Al Harthy'}
          </div>
          <div>{currentUserRole}</div>
        </div>
      )}
    </div>
  );

  return (
    <div className="min-h-screen flex" style={{ backgroundColor: 'var(--re-bg)', color: 'var(--re-text)' }}>
      {/* Desktop Sidebar */}
      {!presentationMode && (
        <aside
          className={`hidden lg:block shrink-0 border-r transition-all duration-150 ${sidebarCollapsed ? 'w-16' : 'w-60'}`}
          style={{ backgroundColor: 'var(--re-sidebar)', borderColor: 'var(--re-border)' }}
        >
          {renderSidebarContent()}
        </aside>
      )}

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div className="w-64 h-full" style={{ backgroundColor: 'var(--re-sidebar)' }}>
            {renderSidebarContent()}
          </div>
          <button
            type="button"
            aria-label="Close navigation menu"
            className="flex-1 bg-black/50"
            onClick={() => setMobileMenuOpen(false)}
          />
        </div>
      )}

      {/* Main Column */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top Bar Contract: Breadcrumb/Title — Global Search — Primary Presentation/Privacy Action */}
        <header
          className="h-14 px-4 lg:px-6 border-b flex items-center justify-between gap-4 shrink-0"
          style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
        >
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation menu"
              className="lg:hidden p-1.5 rounded border"
              style={{ borderColor: 'var(--re-border)' }}
            >
              <Menu className="w-4 h-4" />
            </button>
            <h1 className="font-display text-sm sm:text-base font-semibold truncate whitespace-nowrap">
              {isArabic ? activeMeta.labelAr : activeMeta.labelEn}
            </h1>
          </div>

          <div className="relative hidden md:block w-72 lg:w-80">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--re-text-muted)' }} />
            <input
              type="text"
              value={globalSearch}
              onChange={(e) => setGlobalSearch(e.target.value)}
              placeholder={t(lang, 'searchPlaceholder')}
              aria-label="Global search"
              className="w-full pl-8 pr-7 py-1.5 rounded-lg border text-xs"
              style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            />
            {globalSearch && (
              <button
                type="button"
                aria-label="Clear search"
                onClick={() => setGlobalSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2"
                style={{ color: 'var(--re-text-muted)' }}
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
            {searchHits && (
              <div
                className="absolute left-0 right-0 mt-1 rounded-lg border shadow-lg z-40 p-2 space-y-2 text-xs"
                style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)' }}
              >
                {searchHits.mods.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => {
                      setActiveModule(m.id);
                      setGlobalSearch('');
                    }}
                    className="w-full text-left px-2 py-1.5 rounded hover:opacity-80 flex justify-between"
                    style={{ backgroundColor: 'var(--re-surface-alt)' }}
                  >
                    <span>{isArabic ? m.labelAr : m.labelEn}</span>
                    <span style={{ color: 'var(--re-text-muted)' }}>Module</span>
                  </button>
                ))}
                {searchHits.prjs.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => {
                      setProjectFilterId(p.id);
                      setActiveModule('project-performance');
                      setGlobalSearch('');
                    }}
                    className="w-full text-left px-2 py-1.5 rounded hover:opacity-80 flex justify-between"
                    style={{ backgroundColor: 'var(--re-surface-alt)' }}
                  >
                    <span>{p.code} — {p.name}</span>
                    <span style={{ color: 'var(--re-text-muted)' }}>Project</span>
                  </button>
                ))}
                {searchHits.units.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => {
                      setProjectFilterId(u.projectId);
                      setActiveModule('sales-inventory');
                      setGlobalSearch('');
                    }}
                    className="w-full text-left px-2 py-1.5 rounded hover:opacity-80 flex justify-between"
                    style={{ backgroundColor: 'var(--re-surface-alt)' }}
                  >
                    <span className="font-mono-num">{u.unitCode}</span>
                    <span style={{ color: 'var(--re-text-muted)' }}>{u.status}</span>
                  </button>
                ))}
                {searchHits.mods.length === 0 && searchHits.prjs.length === 0 && searchHits.units.length === 0 && (
                  <div className="px-2 py-1 text-center" style={{ color: 'var(--re-text-muted)' }}>No matching records</div>
                )}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setMobileFiltersOpen((o) => !o)}
              className="md:hidden px-2.5 py-1.5 rounded-lg border text-xs font-medium whitespace-nowrap"
              style={{ borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            >
              {mobileFiltersOpen ? 'Hide Filters' : 'Filters'}
            </button>
            <button
              type="button"
              onClick={() => setPresentationMode((p) => !p)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap"
              style={{ backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)' }}
            >
              {presentationMode ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              {presentationMode ? t(lang, 'exitPresent') : t(lang, 'present')}
            </button>
          </div>
        </header>

        {/* Workspace Toolbar: Single compact row on desktop, collapsible on mobile */}
        {!presentationMode && (
          <div
            className={`${mobileFiltersOpen ? 'flex' : 'hidden md:flex'} px-4 lg:px-6 py-2 border-b flex-wrap md:flex-nowrap items-center gap-2 text-xs overflow-x-auto`}
            style={{ backgroundColor: 'var(--re-surface-alt)', borderColor: 'var(--re-border)' }}
          >
            <select
              aria-label="Entity scope"
              value={companyFilterId}
              onChange={(e) => {
                setCompanyFilterId(e.target.value);
                setProjectFilterId('ALL');
              }}
              className="px-2 py-1.5 rounded border max-w-[190px] truncate"
              style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            >
              <option value="CONSOLIDATED">{t(lang, 'consolidated')}</option>
              {dataset.companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} — {isArabic ? c.nameAr : c.name}
                </option>
              ))}
            </select>

            <select
              aria-label="Project filter"
              value={projectFilterId}
              onChange={(e) => setProjectFilterId(e.target.value)}
              className="px-2 py-1.5 rounded border max-w-[180px] truncate"
              style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            >
              <option value="ALL">{t(lang, 'allProjects')}</option>
              {dataset.projects
                .filter((p) => companyFilterId === 'CONSOLIDATED' || p.companyId === companyFilterId)
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} — {isArabic ? p.nameAr : p.name}
                  </option>
                ))}
            </select>

            <select
              aria-label="Reporting period"
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="px-2 py-1.5 rounded border font-mono-num shrink-0"
              style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            >
              {[...dataset.periods].reverse().map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>

            <select
              aria-label="Reporting basis"
              value={basis}
              onChange={(e) => setBasis(e.target.value as ReportingBasis)}
              className="px-2 py-1.5 rounded border shrink-0"
              style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            >
              <option value="Monthly">Monthly</option>
              <option value="Quarterly">Quarterly</option>
              <option value="YTD">YTD</option>
              <option value="Annual">Annual (12M)</option>
              <option value="ITD">Inception-to-Date</option>
            </select>

            <select
              aria-label="Reporting currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value as CurrencyCode)}
              className="px-2 py-1.5 rounded border font-mono-num shrink-0"
              style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
            >
              <option value="OMR">OMR (.000)</option>
              <option value="AED">AED (.00)</option>
              <option value="SAR">SAR (.00)</option>
              <option value="USD">USD (.00)</option>
            </select>

            <div className="flex items-center gap-1.5 md:ml-auto shrink-0">
              <select
                aria-label="Aesthetic theme"
                value={theme}
                onChange={(e) => setTheme(e.target.value as ThemeId)}
                className="px-2 py-1.5 rounded border max-w-[155px]"
                style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
              >
                {THEMES.map((th) => (
                  <option key={th.id} value={th.id}>
                    {th.label}
                  </option>
                ))}
              </select>

              <select
                aria-label="Font scale"
                value={fontScale}
                onChange={(e) => setFontScale(e.target.value as FontSizeScale)}
                className="px-2 py-1.5 rounded border"
                style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
              >
                <option value="compact">A-</option>
                <option value="standard">A</option>
                <option value="large">A+</option>
              </select>

              <button
                type="button"
                onClick={() => setLang((l) => (l === 'en' ? 'ar' : 'en'))}
                className="px-2.5 py-1.5 rounded border font-medium whitespace-nowrap"
                style={{ backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }}
              >
                {lang === 'en' ? 'العربية' : 'English'}
              </button>

              <button
                type="button"
                onClick={() => setMasked((m) => !m)}
                aria-pressed={masked}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded border font-medium whitespace-nowrap"
                style={
                  masked
                    ? { backgroundColor: 'var(--re-accent)', color: 'var(--re-accent-fg)', borderColor: 'var(--re-accent)' }
                    : { backgroundColor: 'var(--re-surface)', borderColor: 'var(--re-border)', color: 'var(--re-text)' }
                }
              >
                {masked ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                {masked ? t(lang, 'maskOff') : t(lang, 'maskOn')}
              </button>
            </div>
          </div>
        )}

        {/* Active Module Viewport */}
        <main className="flex-1 p-4 lg:p-6 max-w-[1440px] w-full mx-auto">
          {activeModule === 'executive' && (
            <ExecutiveDashboardView
              dataset={dataset}
              statements={statements}
              projectKpis={projectKpis}
              traceableKpis={traceableKpis}
              reconciliation={reconciliation}
              commentary={commentary}
              selectedPeriod={selectedPeriod}
              basis={basis}
              currency={currency}
              companyFilterId={companyFilterId}
              projectFilterId={projectFilterId}
              masked={masked}
              isArabic={isArabic}
              onNavigate={setActiveModule}
              onSelectProject={(id) => setProjectFilterId(id)}
            />
          )}
          {activeModule === 'financial-mis' && (
            <FinancialMisView
              dataset={dataset}
              statements={statements}
              reconciliation={reconciliation}
              selectedPeriod={selectedPeriod}
              basis={basis}
              currency={currency}
              companyFilterId={companyFilterId}
              masked={masked}
            />
          )}
          {activeModule === 'cashflow-treasury' && (
            <CashFlowTreasuryView
              dataset={dataset}
              statements={statements}
              projectKpis={projectKpis}
              currency={currency}
              masked={masked}
            />
          )}
          {activeModule === 'project-performance' && (
            <ProjectPerformanceView projectKpis={projectKpis} currency={currency} masked={masked} />
          )}
          {activeModule === 'sales-inventory' && (
            <SalesInventoryView
              dataset={dataset}
              projectKpis={projectKpis}
              projectFilterId={projectFilterId}
              currency={currency}
              masked={masked}
            />
          )}
          {activeModule === 'collections' && (
            <CollectionsView dataset={dataset} projectKpis={projectKpis} currency={currency} masked={masked} />
          )}
          {activeModule === 'construction' && (
            <ConstructionPlanningView dataset={dataset} projectKpis={projectKpis} masked={masked} />
          )}
          {activeModule === 'budget-cost' && (
            <BudgetCostControlView dataset={dataset} projectFilterId={projectFilterId} currency={currency} masked={masked} />
          )}
          {activeModule === 'contracts' && (
            <ContractsProcurementView dataset={dataset} projectFilterId={projectFilterId} currency={currency} masked={masked} />
          )}
          {activeModule === 'financing' && (
            <FinancingCovenantsView dataset={dataset} currency={currency} masked={masked} />
          )}
          {activeModule === 'feasibility' && (
            <FeasibilityScenarioView projectKpis={projectKpis} currency={currency} masked={masked} />
          )}
          {activeModule === 'risk-compliance' && (
            <RiskComplianceView dataset={dataset} currency={currency} masked={masked} />
          )}
          {activeModule === 'handover-warranty' && (
            <HandoverWarrantyView dataset={dataset} currency={currency} masked={masked} />
          )}
          {activeModule === 'rental-properties' && (
            <RentalPropertiesView dataset={dataset} currency={currency} masked={masked} />
          )}
          {activeModule === 'ai-analyst' && (
            <AiAnalystView
              dataset={dataset}
              statements={statements}
              projectKpis={projectKpis}
              commentary={commentary}
              selectedPeriod={selectedPeriod}
            />
          )}
          {activeModule === 'data-upload' && (
            <DataUploadView
              dataset={dataset}
              selectedPeriod={selectedPeriod}
              companyFilterId={companyFilterId}
              authToken={authToken}
              onDatasetUpdated={setDataset}
            />
          )}
          {activeModule === 'workflow-controls' && (
            <WorkflowControlsView
              dataset={dataset}
              reconciliation={reconciliation}
              selectedPeriod={selectedPeriod}
              currentUserRole={currentUserRole}
              authToken={authToken}
              onDatasetUpdated={setDataset}
            />
          )}
          {activeModule === 'reports-exports' && (
            <ReportsExportsView
              dataset={dataset}
              statements={statements}
              projectKpis={projectKpis}
              reconciliation={reconciliation}
              commentary={commentary}
              selectedPeriod={selectedPeriod}
              basis={basis}
              currency={currency}
              companyFilterId={companyFilterId}
              masked={masked}
            />
          )}
          {activeModule === 'settings-admin' && (
            <SettingsAdminView
              dataset={dataset}
              users={users}
              currentUserId={currentUserId}
              authToken={authToken}
              onSwitchUser={(id) => void authenticateSession(id)}
              onDatasetUpdated={setDataset}
              onOpenSetupWizard={() => setWizardOpen(true)}
            />
          )}
        </main>
      </div>

      <SetupWizardModal
        open={wizardOpen}
        dataset={dataset}
        currency={currency}
        theme={theme}
        lang={lang}
        fontScale={fontScale}
        onClose={() => setWizardOpen(false)}
        onApplyPreferences={(prefs) => {
          setCurrency(prefs.currency);
          setTheme(prefs.theme);
          setLang(prefs.lang);
          setFontScale(prefs.fontScale);
        }}
      />
    </div>
  );
}
