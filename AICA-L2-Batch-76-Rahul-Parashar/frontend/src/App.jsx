import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useFinancials } from './context/FinancialsContext';
import UploadScreen from './components/upload/UploadScreen';
import DataHealthCheck from './components/upload/DataHealthCheck';
import AppShell from './components/layout/AppShell';

import Home from './pages/Home';
import RevenuePage from './pages/RevenuePage';
import RevenueMixPage from './pages/RevenueMixPage';
import RevenueQuarterlyPage from './pages/RevenueQuarterlyPage';
import CostPage from './pages/CostPage';
import CostBreakupPage from './pages/CostBreakupPage';
import CostCommonSizePage from './pages/CostCommonSizePage';
import ProfitabilityPage from './pages/ProfitabilityPage';
import ProfitabilityMarginsPage from './pages/ProfitabilityMarginsPage';
import ProfitabilityVariancePage from './pages/ProfitabilityVariancePage';
import BalanceSheetPage from './pages/BalanceSheetPage';
import BalanceSheetAssetsPage from './pages/BalanceSheetAssetsPage';
import BalanceSheetLiabilitiesPage from './pages/BalanceSheetLiabilitiesPage';
import LiquidityPage from './pages/LiquidityPage';
import LiquidityRatiosPage from './pages/LiquidityRatiosPage';
import LiquidityCyclePage from './pages/LiquidityCyclePage';
import CashFlowPage from './pages/CashFlowPage';
import ReturnsPage from './pages/ReturnsPage';
import ReturnsDupontPage from './pages/ReturnsDupontPage';
import DebtPage from './pages/DebtPage';
import DebtCoveragePage from './pages/DebtCoveragePage';

function App() {
  const { financials, dashboardReady } = useFinancials();

  if (!financials) {
    return <UploadScreen />;
  }

  if (!dashboardReady) {
    return <DataHealthCheck />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Home />} />
          <Route path="/revenue" element={<RevenuePage />} />
          <Route path="/revenue/mix" element={<RevenueMixPage />} />
          <Route path="/revenue/quarterly" element={<RevenueQuarterlyPage />} />
          <Route path="/cost" element={<CostPage />} />
          <Route path="/cost/breakup" element={<CostBreakupPage />} />
          <Route path="/cost/common-size" element={<CostCommonSizePage />} />
          <Route path="/profitability" element={<ProfitabilityPage />} />
          <Route path="/profitability/margins" element={<ProfitabilityMarginsPage />} />
          <Route path="/profitability/variance" element={<ProfitabilityVariancePage />} />
          <Route path="/balance-sheet" element={<BalanceSheetPage />} />
          <Route path="/balance-sheet/assets" element={<BalanceSheetAssetsPage />} />
          <Route path="/balance-sheet/liabilities" element={<BalanceSheetLiabilitiesPage />} />
          <Route path="/liquidity" element={<LiquidityPage />} />
          <Route path="/liquidity/ratios" element={<LiquidityRatiosPage />} />
          <Route path="/liquidity/cycle" element={<LiquidityCyclePage />} />
          <Route path="/cash-flow" element={<CashFlowPage />} />
          <Route path="/returns" element={<ReturnsPage />} />
          <Route path="/returns/dupont" element={<ReturnsDupontPage />} />
          <Route path="/debt" element={<DebtPage />} />
          <Route path="/debt/coverage" element={<DebtCoveragePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
