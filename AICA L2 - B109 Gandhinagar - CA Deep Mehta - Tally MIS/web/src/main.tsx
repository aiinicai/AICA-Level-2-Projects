import { StrictMode, useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import '@fontsource/plus-jakarta-sans/latin-400.css';
import '@fontsource/plus-jakarta-sans/latin-500.css';
import '@fontsource/plus-jakarta-sans/latin-600.css';
import '@fontsource/plus-jakarta-sans/latin-700.css';
import '@fontsource/plus-jakarta-sans/latin-800.css';
import './styles.css';
import { api } from './api';
import { applyTheme, storedTheme } from './themes';
import { AppContext, storeCompany, storedCompany, type CompanyInfo, type SessionUser } from './state';
import { Layout } from './components/Layout';
import { Loading, ErrorState } from './components/ui';
import { HomePage } from './pages/Home';
import { Dashboard } from './pages/Dashboard';
import { PnlPage } from './pages/Pnl';
import { ArApPage } from './pages/ArAp';
import { BalanceSheetPage } from './pages/BalanceSheet';
import { SourcesPage } from './pages/Sources';
import { LedgerPage, VoucherPage } from './pages/Drill';
import { AppSettings, ComingSoon } from './pages/AppSettings';

applyTheme(storedTheme());
const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

function Shell() {
  const auth = useQuery<{ user: SessionUser }>({ queryKey: ['auth'], queryFn: () => api('/api/auth/state') });
  const companies = useQuery<CompanyInfo[]>({ queryKey: ['companies'], queryFn: () => api('/api/companies'), enabled: !!auth.data?.user });
  const [companyId, setCid] = useState<number | null>(storedCompany());
  useEffect(() => {
    const list = companies.data;
    if (list?.length && !list.some((c) => c.id === companyId)) setCid((list.find((c) => !c.is_demo) ?? list[0]).id);
  }, [companies.data, companyId]);
  const setCompanyId = useCallback((id: number) => { setCid(id); storeCompany(id); }, []);

  if (auth.isLoading) return <Loading />;
  if (auth.error || !auth.data) return <div className="content"><ErrorState error={auth.error ?? new Error('The app is not running')} /></div>;
  if (companies.isLoading) return <Loading />;
  const list = companies.data ?? [];
  const company = list.find((c) => c.id === companyId) ?? null;
  const NeedCompany = ({ el }: { el: JSX.Element }) => (company ? el : <SourcesPage />);
  const later = (title: string) => <ComingSoon title={title} />;
  return (
    <AppContext.Provider value={{ user: auth.data.user, demoMode: false, demoLoginRequired: false, companies: list, companyId: company?.id ?? null, company, setCompanyId, refreshCompanies: () => qc.invalidateQueries({ queryKey: ['companies'] }) }}>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/overview" element={<NeedCompany el={<Dashboard />} />} />
          <Route path="/pnl" element={<NeedCompany el={<PnlPage />} />} />
          <Route path="/receivables-payables" element={<NeedCompany el={<ArApPage />} />} />
          <Route path="/ledgers/:lid" element={<NeedCompany el={<LedgerPage />} />} />
          <Route path="/vouchers/:vid" element={<NeedCompany el={<VoucherPage />} />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/settings" element={<AppSettings />} />
          <Route path="/balance-sheet" element={<NeedCompany el={<BalanceSheetPage />} />} />
          <Route path="/settings/mapping" element={later('Ledger mapping')} />
          <Route path="/inventory" element={later('Inventory')} />
          <Route path="/insights" element={later('Insights & alerts')} />
          <Route path="/data-quality" element={later('Data quality')} />
          <Route path="*" element={<div className="state">Page not found</div>} />
        </Routes>
      </Layout>
    </AppContext.Provider>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <HashRouter><Shell /></HashRouter>
    </QueryClientProvider>
  </StrictMode>,
);
