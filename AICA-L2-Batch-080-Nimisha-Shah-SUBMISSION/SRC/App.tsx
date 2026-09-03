import React, { useState, useMemo, useEffect } from "react";
import {
  LISTED_COMPANIES,
  ListedCompany,
  convertCompanyToFinancialPeriods,
  getResolvedCompanyFinancials,
} from "./data/listedCompaniesDataset";
import { CurrencyCode, UnitScale, DataQualityReport } from "./types/financial";
import { Navigation, NavTabId } from "./components/Navigation";
import { TopBar } from "./components/TopBar";
import { AICFOAssistantModal } from "./components/AICFOAssistantModal";
import allFinancialsUniverse from "./data/allFinancialsUniverse.json";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AuthView } from "./views/AuthView";

// Views
import { ExecutiveDashboard } from "./views/ExecutiveDashboard";
import { ProfitabilityAnalysis } from "./views/ProfitabilityAnalysis";
import { SolvencyDashboard } from "./views/SolvencyDashboard";
import { GrowthMomentumView } from "./views/GrowthMomentumView";
import { ValuationMultiplesView } from "./views/ValuationMultiplesView";
import { WorkingCapitalView } from "./views/WorkingCapitalView";
import { PeerBenchmarkView } from "./views/PeerBenchmarkView";
import { RedFlagsView } from "./views/RedFlagsView";
import { CompanyExplorerView } from "./views/CompanyExplorerView";
import { DataQualityView } from "./views/DataQualityView";
import { AdminView } from "./views/AdminView";
import { Menu, X, Building2 } from "lucide-react";

const STORAGE_KEY = "cfo_dashboard_companies_universe_v1";
const CUSTOM_STORAGE_KEY = "cfo_custom_appended_companies_v1";

const sanitizeCompanies = (list: ListedCompany[]): ListedCompany[] => {
  return list.map((c) => {
    if (c.name.startsWith("Enterprise ") && c.nseCode && !c.nseCode.startsWith("ENT")) {
      const cleanName = c.nseCode.toLowerCase().includes("bizedge") ? "BizEdge Profits" : `${c.nseCode} Limited`;
      return {
        ...c,
        name: cleanName,
        shortName: c.nseCode,
      };
    }
    return c;
  });
};

const getInitialCompanies = (): ListedCompany[] => {
  const baseUniverse = (allFinancialsUniverse as ListedCompany[]) || LISTED_COMPANIES;
  try {
    const customSaved = localStorage.getItem(CUSTOM_STORAGE_KEY);
    if (customSaved) {
      const customParsed = JSON.parse(customSaved);
      if (Array.isArray(customParsed) && customParsed.length > 0) {
        const customCodes = new Set(customParsed.map((r: any) => String(r.bseCode)));
        const retainedBase = baseUniverse.filter(c => !customCodes.has(c.bseCode));
        return sanitizeCompanies([...customParsed, ...retainedBase]);
      }
    }
  } catch (e) {
    console.error("Failed to load custom appended companies:", e);
  }
  return baseUniverse;
};

function MainDashboard() {
  const { user, loading, isAdmin } = useAuth();

  const [companiesList, setCompaniesList] = useState<ListedCompany[]>(getInitialCompanies);
  const defaultCompany = companiesList.find((c) => c.bseCode === "500325" || c.name.toLowerCase().includes("reliance")) || companiesList[0];
  const [selectedCompanyCode, setSelectedCompanyCode] = useState<string>(defaultCompany.bseCode);
  
  const [isDemoData, setIsDemoData] = useState<boolean>(() => {
    try {
      return !localStorage.getItem(CUSTOM_STORAGE_KEY);
    } catch {
      return true;
    }
  });

  const currentCompany: ListedCompany = useMemo(() => {
    return companiesList.find((c) => 
      c.bseCode === selectedCompanyCode || 
      c.nseCode === selectedCompanyCode || 
      c.name.toLowerCase() === selectedCompanyCode.toLowerCase()
    ) || companiesList[0];
  }, [selectedCompanyCode, companiesList]);

  const [currency, setCurrency] = useState<CurrencyCode>("INR");
  const [scale, setScale] = useState<UnitScale>("crores");
  const [selectedPeriod, setSelectedPeriod] = useState<string>("latest");
  const [activeTab, setActiveTab] = useState<NavTabId>("executive");
  const [isAIModalOpen, setIsAIModalOpen] = useState<boolean>(false);
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);

  const saveCompanies = (newList: ListedCompany[]) => {
    const sanitized = sanitizeCompanies(newList);
    setCompaniesList(sanitized);
  };

  const handleSelectCompany = (code: string) => {
    const found = companiesList.find(
      (c) => c.bseCode === code || c.nseCode === code || c.name.toLowerCase() === code.toLowerCase()
    );
    if (found) {
      setSelectedCompanyCode(found.bseCode);
    }
  };

  const handleImportNewRecords = (newRecords: ListedCompany[], mode: "append" | "replace") => {
    if (!newRecords || newRecords.length === 0) return;

    if (mode === "replace") {
      setCompaniesList(sanitizeCompanies(newRecords));
      try {
        localStorage.setItem(CUSTOM_STORAGE_KEY, JSON.stringify(newRecords.slice(0, 100)));
      } catch (e) {}
      setSelectedCompanyCode(newRecords[0].bseCode);
    } else {
      const baseUniverseList = (allFinancialsUniverse as ListedCompany[]) || LISTED_COMPANIES;
      const baseBseCodes = new Set(baseUniverseList.map(c => c.bseCode));

      const preparedNewRecords = newRecords.map((record, i) => {
        const rawCode = String(record.bseCode || '').trim();
        const uniqueBse = (baseBseCodes.has(rawCode) || !rawCode)
          ? `${rawCode || '600000'}_custom_${i + 1}`
          : rawCode;

        return {
          ...record,
          bseCode: uniqueBse
        };
      });

      try {
        const existingCustom = JSON.parse(localStorage.getItem(CUSTOM_STORAGE_KEY) || "[]");
        const mergedCustom = [...preparedNewRecords, ...existingCustom.filter((e: any) => !preparedNewRecords.some(n => n.bseCode === e.bseCode))];
        localStorage.setItem(CUSTOM_STORAGE_KEY, JSON.stringify(mergedCustom));
      } catch (e) {}

      setCompaniesList((prevList) => {
        const existingWithoutSameCustomKey = prevList.filter(c => !preparedNewRecords.some(n => n.bseCode === c.bseCode));
        return sanitizeCompanies([...preparedNewRecords, ...existingWithoutSameCustomKey]);
      });

      setSelectedCompanyCode(preparedNewRecords[0].bseCode);
    }
    setIsDemoData(false);
  };

  const handleResetDemoData = () => {
    try {
      localStorage.removeItem(CUSTOM_STORAGE_KEY);
    } catch (e) {}
    const baseUniverse = (allFinancialsUniverse as ListedCompany[]) || LISTED_COMPANIES;
    setCompaniesList(baseUniverse);
    setSelectedCompanyCode("500325");
    setIsDemoData(true);
  };

  const availablePeriods = [
    { label: "Latest Reported Quarter (Q4 FY25)", value: "latest" },
    { label: "Preceding Full Year Actuals (FY24)", value: "PY" },
    { label: "Annualized Run-Rate (Q4 × 4)", value: "RunRate" },
  ];

  const currentFinancials = useMemo(() => {
    return getResolvedCompanyFinancials(currentCompany, selectedPeriod);
  }, [currentCompany, selectedPeriod]);

  const activeCompanyFlagsCount = useMemo(() => {
    let count = 0;
    if (currentFinancials.debtToEquity > 2.0) count++;
    if (currentFinancials.interestCoverage < 1.5 && currentFinancials.debt > 10) count++;
    if (currentFinancials.hasOperatingScissors) count++;
    if (currentFinancials.otherIncomeShareOfEbidt > 25) count++;
    if (currentFinancials.roce < 8.0 && currentFinancials.debt > 0) count++;
    if (currentFinancials.pat < 0) count++;
    return count;
  }, [currentFinancials]);

  // Loading state while checking active session
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center space-y-4 font-sans select-none">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-2xl shadow-blue-500/30 animate-pulse border border-blue-400/30">
          <Building2 className="w-7 h-7 text-white" />
        </div>
        <div className="text-center space-y-1">
          <div className="text-sm font-bold text-white tracking-tight">Enterprise CFO Analytics</div>
          <div className="text-xs font-mono text-slate-400">Verifying secure executive session...</div>
        </div>
      </div>
    );
  }

  // Authentication Gate: Render AuthView if user is not signed in
  if (!user) {
    return <AuthView />;
  }

  // Authenticated: Render Full CFO Enterprise Suite
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans antialiased">
      <div className="flex flex-1">
        {/* Desktop Sidebar */}
        <div className="hidden lg:block">
          <Navigation
            activeTab={activeTab}
            onSelectTab={(t) => setActiveTab(t)}
            redFlagCount={activeCompanyFlagsCount}
            companyCount={companiesList.length}
            dataQualityScore={99.4}
          />
        </div>

        {/* Mobile Navigation */}
        {isMobileNavOpen && (
          <div className="fixed inset-0 z-50 flex lg:hidden">
            <div className="fixed inset-0 bg-slate-900/60" onClick={() => setIsMobileNavOpen(false)} />
            <div className="relative z-10 w-72 bg-slate-900 shadow-2xl">
              <div className="flex items-center justify-between p-4 border-b border-slate-800">
                <span className="text-sm font-bold text-white">Menu Navigation</span>
                <button onClick={() => setIsMobileNavOpen(false)} className="text-slate-400 hover:text-white">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <Navigation
                activeTab={activeTab}
                onSelectTab={(t) => {
                  setActiveTab(t);
                  setIsMobileNavOpen(false);
                }}
                redFlagCount={activeCompanyFlagsCount}
                companyCount={companiesList.length}
                dataQualityScore={99.4}
              />
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-w-0 bg-slate-50">
          <div className="flex items-center border-b border-slate-200 bg-white sticky top-0 z-20">
            <button
              onClick={() => setIsMobileNavOpen(true)}
              className="lg:hidden p-3 text-slate-600 hover:text-slate-900"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="flex-1">
              <TopBar
                activeTab={activeTab}
                companyName={currentCompany.name}
                selectedCompanyCode={selectedCompanyCode}
                onSelectCompany={handleSelectCompany}
                currency={currency}
                onChangeCurrency={setCurrency}
                scale={scale}
                onChangeScale={setScale}
                selectedPeriod={selectedPeriod}
                availablePeriods={availablePeriods}
                onChangePeriod={setSelectedPeriod}
                isDemoData={isDemoData}
                onResetDemoData={handleResetDemoData}
                onOpenAIModal={() => setIsAIModalOpen(true)}
                onExportPDF={() => setActiveTab("explorer")}
                onOpenUpload={() => setActiveTab("data_quality")}
                healthScore={Math.round(Math.min(99, Math.max(40, currentFinancials.roce * 2.5 + (currentFinancials.debtToEquity < 1 ? 30 : 15))))}
                companies={companiesList}
              />
            </div>
          </div>

          <main className="flex-1 p-3 sm:p-4 md:p-5 max-w-7xl w-full mx-auto">
            {activeTab === "executive" && (
              <ExecutiveDashboard
                company={currentCompany}
                currency={currency}
                scale={scale}
                onNavigateTab={(tab) => setActiveTab(tab)}
                selectedPeriod={selectedPeriod}
              />
            )}
            {activeTab === "profitability" && (
              <ProfitabilityAnalysis 
                company={currentCompany} 
                selectedPeriod={selectedPeriod}
                currency={currency}
                scale={scale}
              />
            )}
            {activeTab === "solvency" && (
              <SolvencyDashboard 
                company={currentCompany} 
                selectedPeriod={selectedPeriod}
                currency={currency}
                scale={scale}
              />
            )}
            {activeTab === "growth" && (
              <GrowthMomentumView 
                company={currentCompany} 
                selectedPeriod={selectedPeriod}
                currency={currency}
                scale={scale}
              />
            )}
            {activeTab === "working_capital" && (
              <WorkingCapitalView 
                company={currentCompany}
                companies={companiesList}
                selectedPeriod={selectedPeriod}
                currency={currency}
                scale={scale}
              />
            )}
            {activeTab === "valuation" && (
              <ValuationMultiplesView 
                company={currentCompany} 
                onSelectCompany={handleSelectCompany} 
                companies={companiesList}
                selectedPeriod={selectedPeriod}
                currency={currency}
                scale={scale}
              />
            )}
            {activeTab === "peer_benchmark" && (
              <PeerBenchmarkView 
                currentCompany={currentCompany} 
                onSelectCompany={handleSelectCompany} 
                companies={companiesList}
                currency={currency}
                scale={scale}
              />
            )}
            {activeTab === "red_flags" && (
              <RedFlagsView 
                currentCompany={currentCompany} 
                onSelectCompany={handleSelectCompany} 
                companies={companiesList}
                selectedPeriod={selectedPeriod}
                currency={currency}
                scale={scale}
              />
            )}
            {activeTab === "explorer" && (
              <CompanyExplorerView 
                currentCompany={currentCompany} 
                onSelectCompany={handleSelectCompany} 
                companies={companiesList}
                currency={currency}
                scale={scale}
              />
            )}
            {activeTab === "data_quality" && (
              <DataQualityView
                report={{
                  qualityScore: 99.4,
                  totalRecords: companiesList.length,
                  dateRange: "FY23 - Q4 FY25",
                  isBalanced: true,
                  errors: [],
                  warnings: [],
                  missingFields: [],
                  fieldCompleteness: [],
                }}
                onImportNewRecords={handleImportNewRecords}
                onResetDemoData={handleResetDemoData}
                isDemoData={isDemoData}
                onNavigateTab={(tab) => setActiveTab(tab)}
                companies={companiesList}
                onSelectCompany={handleSelectCompany}
              />
            )}
            {activeTab === "admin" && isAdmin && (
              <AdminView />
            )}
          </main>
        </div>
      </div>

      <AICFOAssistantModal
        isOpen={isAIModalOpen}
        onClose={() => setIsAIModalOpen(false)}
        company={currentCompany}
        currentRecord={convertCompanyToFinancialPeriods(currentCompany)[0]}
        currency={currency}
        scale={scale}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainDashboard />
    </AuthProvider>
  );
}
