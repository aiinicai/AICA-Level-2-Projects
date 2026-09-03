import React, { useState, useMemo, useRef, useEffect } from "react";
import { CurrencyCode, UnitScale, ListedCompany } from "../types/financial";
import { NavTabId } from "./Navigation";
import {
  Sparkles,
  Download,
  Calendar,
  Building2,
  Users2,
  ChevronDown,
  Search,
  X,
  TrendingUp,
  Filter,
  Check,
  Zap,
  LogOut,
  User as UserIcon
} from "lucide-react";
import { LISTED_COMPANIES } from "../data/listedCompaniesDataset";
import { formatFinancialValue } from "../utils/formatUtils";
import { useAuth } from "../context/AuthContext";

interface TopBarProps {
  activeTab: NavTabId;
  companyName: string;
  selectedCompanyCode?: string;
  onSelectCompany?: (code: string) => void;
  currency: CurrencyCode;
  onChangeCurrency: (c: CurrencyCode) => void;
  scale: UnitScale;
  onChangeScale: (s: UnitScale) => void;
  selectedPeriod: string;
  availablePeriods: { label: string; value: string }[];
  onChangePeriod: (p: string) => void;
  isDemoData: boolean;
  onResetDemoData: () => void;
  onOpenAIModal: () => void;
  onExportPDF: () => void;
  onOpenUpload: () => void;
  healthScore?: number;
  companies?: ListedCompany[];
}

type FilterPreset = "all" | "custom" | "large_cap" | "high_growth" | "high_roce" | "low_debt";

export const TopBar: React.FC<TopBarProps> = ({
  activeTab,
  companyName,
  selectedCompanyCode,
  onSelectCompany,
  currency,
  onChangeCurrency,
  scale,
  onChangeScale,
  selectedPeriod,
  availablePeriods,
  onChangePeriod,
  onOpenAIModal,
  onExportPDF,
  onOpenUpload,
  healthScore = 88,
  companies = LISTED_COMPANIES,
}) => {
  const { user, signOut, isAdmin } = useAuth();
  const isCrossCompanyTab =
    activeTab === "peer_benchmark" ||
    activeTab === "explorer" ||
    activeTab === "data_quality";

  const activeCompanyObj = companies.find((c) => c.bseCode === selectedCompanyCode) || companies[0];

  // Search dropdown state
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<FilterPreset>("all");
  const [visibleCount, setVisibleCount] = useState(100);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Focus input & reset pagination when search opens
  useEffect(() => {
    if (isSearchOpen) {
      setVisibleCount(100);
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
  }, [isSearchOpen]);

  // Reset pagination when query or filter changes
  useEffect(() => {
    setVisibleCount(100);
  }, [searchQuery, activeFilter]);

  const customCount = useMemo(() => {
    return companies.filter((c) => Number(c.bseCode) >= 600000 || !c.marketCap).length;
  }, [companies]);

  // Filtered and sorted companies
  const matchedCompanies = useMemo(() => {
    let list = companies;

    // Apply category preset
    if (activeFilter === "custom") {
      list = companies.filter((c) => Number(c.bseCode) >= 600000 || !c.marketCap);
    } else if (activeFilter === "large_cap") {
      list = [...companies].sort((a, b) => (b.marketCap || 0) - (a.marketCap || 0)).slice(0, 100);
    } else if (activeFilter === "high_growth") {
      list = companies.filter((c) => c.salesGrowthYoY >= 15);
    } else if (activeFilter === "high_roce") {
      list = companies.filter((c) => c.roce >= 15);
    } else if (activeFilter === "low_debt") {
      list = companies.filter((c) => c.debtToEquity < 0.5);
    }

    if (!searchQuery.trim()) {
      // Prioritize custom ingested companies at the very top, followed by market cap
      return [...list].sort((a, b) => {
        const aIsCustom = Number(a.bseCode) >= 600000 || !a.marketCap;
        const bIsCustom = Number(b.bseCode) >= 600000 || !b.marketCap;
        if (aIsCustom && !bIsCustom) return -1;
        if (!aIsCustom && bIsCustom) return 1;
        return (b.marketCap || 0) - (a.marketCap || 0);
      });
    }

    const q = searchQuery.toLowerCase().trim();
    return list.filter((c) => {
      const name = (c.name || "").toLowerCase();
      const nse = (c.nseCode || "").toLowerCase();
      const bse = String(c.bseCode || "").toLowerCase();
      const sector = (c.sector || "").toLowerCase();
      const ind = (c.industryGroup || "").toLowerCase();
      return name.includes(q) || nse.includes(q) || bse.includes(q) || sector.includes(q) || ind.includes(q);
    }).sort((a, b) => {
      const aStarts = (a.name || "").toLowerCase().startsWith(q) || (a.nseCode || "").toLowerCase().startsWith(q);
      const bStarts = (b.name || "").toLowerCase().startsWith(q) || (b.nseCode || "").toLowerCase().startsWith(q);
      if (aStarts && !bStarts) return -1;
      if (!aStarts && bStarts) return 1;
      return (b.marketCap || 0) - (a.marketCap || 0);
    });
  }, [companies, searchQuery, activeFilter]);

  // Sliced items for smooth virtual scrolling
  const visibleCompanies = useMemo(() => {
    return matchedCompanies.slice(0, visibleCount);
  }, [matchedCompanies, visibleCount]);

  // Handle scroll down to load more items seamlessly
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollTop + clientHeight >= scrollHeight - 80) {
      if (visibleCount < matchedCompanies.length) {
        setVisibleCount((prev) => Math.min(prev + 100, matchedCompanies.length));
      }
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-3 sm:px-6 sticky top-0 z-30 font-sans shadow-xs">
      <div className="flex items-center gap-3 min-w-0">
        {isCrossCompanyTab ? (
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-blue-900 text-white flex items-center justify-center font-bold text-xs shrink-0">
              <Users2 className="h-4 w-4 text-blue-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm sm:text-base font-bold text-slate-900">
                  Cross-Company Intelligence & Benchmark
                </h1>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-bold border border-blue-200 font-mono">
                  {companies.length.toLocaleString()} Universe
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium hidden sm:block">
                All 25+ Industry Groups • Live Corporate Financial State
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2.5" ref={dropdownRef}>
            <div className="h-9 w-9 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold text-xs shrink-0">
              <Building2 className="h-4 w-4 text-emerald-400" />
            </div>

            <div className="relative">
              {onSelectCompany ? (
                <div>
                  {/* Active Company Button that opens Search Combobox */}
                  <button
                    type="button"
                    onClick={() => setIsSearchOpen(!isSearchOpen)}
                    className="flex items-center justify-between gap-2 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-300 rounded-lg text-left transition-colors cursor-pointer max-w-[240px] sm:max-w-[360px] md:max-w-[420px]"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="font-bold text-slate-900 text-xs sm:text-sm truncate">
                          {activeCompanyObj?.name || companyName}
                        </span>
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-blue-100 text-blue-800 shrink-0">
                          {activeCompanyObj?.nseCode || "NSE"}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500 truncate flex items-center gap-1 font-mono">
                        <span>{activeCompanyObj?.industryGroup || activeCompanyObj?.sector}</span>
                        <span>•</span>
                        <span>M.Cap: {formatFinancialValue(activeCompanyObj?.marketCap || 0, 'INR', scale)}</span>
                      </div>
                    </div>
                    <ChevronDown className="h-4 w-4 text-slate-500 shrink-0" />
                  </button>

                  {/* Searchable Combobox Dropdown */}
                  {isSearchOpen && (
                    <div className="absolute top-full left-0 mt-1.5 w-[330px] sm:w-[500px] bg-white border border-slate-200 rounded-xl shadow-2xl z-50 overflow-hidden animate-fadeIn">
                      
                      {/* Search Header */}
                      <div className="p-3 border-b border-slate-100 bg-slate-50 flex items-center gap-2">
                        <Search className="w-4 h-4 text-slate-400 shrink-0" />
                        <input
                          ref={searchInputRef}
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder={`Search all ${companies.length.toLocaleString()} companies by name, ticker, sector...`}
                          className="w-full bg-transparent text-xs font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none"
                        />
                        {searchQuery && (
                          <button
                            onClick={() => setSearchQuery("")}
                            className="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-slate-600"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>

                      {/* Quick Filter Chips */}
                      <div className="px-3 py-2 bg-slate-50 border-b border-slate-200/80 flex items-center gap-1.5 overflow-x-auto text-[10px] font-mono">
                        <button
                          type="button"
                          onClick={() => setActiveFilter("all")}
                          className={`px-2 py-0.5 rounded-full transition-colors whitespace-nowrap cursor-pointer ${
                            activeFilter === "all" ? "bg-slate-900 text-white font-bold" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
                          }`}
                        >
                          All ({companies.length.toLocaleString()})
                        </button>
                        {customCount > 0 && (
                          <button
                            type="button"
                            onClick={() => setActiveFilter("custom")}
                            className={`px-2 py-0.5 rounded-full transition-colors whitespace-nowrap cursor-pointer ${
                              activeFilter === "custom" ? "bg-amber-600 text-white font-bold" : "bg-amber-50 text-amber-800 border border-amber-300 hover:bg-amber-100"
                            }`}
                          >
                            ⭐ Custom ({customCount})
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setActiveFilter("large_cap")}
                          className={`px-2 py-0.5 rounded-full transition-colors whitespace-nowrap cursor-pointer ${
                            activeFilter === "large_cap" ? "bg-blue-600 text-white font-bold" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
                          }`}
                        >
                          Top 100 Large Cap
                        </button>
                        <button
                          type="button"
                          onClick={() => setActiveFilter("high_roce")}
                          className={`px-2 py-0.5 rounded-full transition-colors whitespace-nowrap cursor-pointer ${
                            activeFilter === "high_roce" ? "bg-emerald-600 text-white font-bold" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
                          }`}
                        >
                          High ROCE (&gt;15%)
                        </button>
                        <button
                          type="button"
                          onClick={() => setActiveFilter("low_debt")}
                          className={`px-2 py-0.5 rounded-full transition-colors whitespace-nowrap cursor-pointer ${
                            activeFilter === "low_debt" ? "bg-purple-600 text-white font-bold" : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
                          }`}
                        >
                          Low Debt (D/E &lt; 0.5)
                        </button>
                      </div>

                      {/* Universe Status Banner */}
                      <div className="px-3 py-1.5 bg-slate-100/80 border-b border-slate-200/60 flex items-center justify-between text-[10px] font-mono text-slate-600">
                        <span>
                          {searchQuery
                            ? `Found ${matchedCompanies.length.toLocaleString()} matching companies`
                            : `Showing ${visibleCompanies.length} of ${matchedCompanies.length.toLocaleString()} companies (Scroll down for all)`}
                        </span>
                        <span className="text-emerald-700 font-bold flex items-center gap-1">
                          <Zap className="w-3 h-3 fill-emerald-600" />
                          <span>5,417 Universe</span>
                        </span>
                      </div>

                      {/* Search Results List with Seamless Infinite Scroll */}
                      <div 
                        onScroll={handleScroll}
                        className="max-h-80 overflow-y-auto divide-y divide-slate-100"
                      >
                        {visibleCompanies.length === 0 ? (
                          <div className="p-8 text-center text-xs text-slate-400">
                            No companies found matching "{searchQuery}"
                          </div>
                        ) : (
                          visibleCompanies.map((c) => {
                            const isSelected = c.bseCode === selectedCompanyCode;
                            return (
                              <button
                                key={c.bseCode}
                                type="button"
                                onClick={() => {
                                  onSelectCompany(c.bseCode);
                                  setIsSearchOpen(false);
                                  setSearchQuery("");
                                }}
                                className={`w-full p-2.5 text-left flex items-center justify-between hover:bg-blue-50/70 transition-colors cursor-pointer ${
                                  isSelected ? "bg-blue-50/90 font-bold" : ""
                                }`}
                              >
                                <div className="min-w-0 pr-2">
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-xs font-semibold text-slate-900 truncate">
                                      {c.name}
                                    </span>
                                    <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-slate-200 text-slate-700 shrink-0">
                                      {c.nseCode}
                                    </span>
                                    {isSelected && (
                                      <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                                    )}
                                  </div>
                                  <div className="text-[10px] text-slate-500 truncate mt-0.5 flex items-center gap-1 font-mono">
                                    <span>{c.sector}</span>
                                    <span>•</span>
                                    <span>BSE: {c.bseCode}</span>
                                  </div>
                                </div>

                                <div className="text-right shrink-0 font-mono text-[10px]">
                                  <div className="font-bold text-slate-900">
                                    {formatFinancialValue(c.marketCap, 'INR', scale)}
                                  </div>
                                  <div className="text-slate-400">
                                    ₹ {c.stockPrice.toLocaleString('en-IN')}
                                  </div>
                                </div>
                              </button>
                            );
                          })
                        )}

                        {/* Infinite scroll loader footer */}
                        {visibleCount < matchedCompanies.length && (
                          <div className="p-2 text-center text-[10px] font-mono text-slate-400 bg-slate-50">
                            Scroll down to load more ({matchedCompanies.length - visibleCount} remaining)...
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <h1 className="text-sm sm:text-base font-bold text-slate-900">{companyName}</h1>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 sm:gap-2.5">
        {!isCrossCompanyTab && (
          <div className="flex items-center gap-1.5 bg-slate-50 px-2.5 py-1 rounded border border-slate-200 text-xs">
            <Calendar className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            <select
              value={selectedPeriod}
              onChange={(e) => onChangePeriod(e.target.value)}
              className="bg-transparent font-medium text-slate-800 text-xs focus:outline-none cursor-pointer"
            >
              {availablePeriods.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Unit Denomination Switcher: Crores (₹) vs Millions (₹) */}
        <div className="flex items-center bg-slate-100 p-0.5 rounded border border-slate-200 text-[10px] font-bold">
          <button
            onClick={() => {
              onChangeCurrency("INR");
              onChangeScale("crores");
            }}
            className={`px-2 py-0.5 rounded transition-all cursor-pointer ${
              scale === "crores"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            ₹ Cr
          </button>
          <button
            onClick={() => {
              onChangeCurrency("INR");
              onChangeScale("millions");
            }}
            className={`px-2 py-0.5 rounded transition-all cursor-pointer ${
              scale === "millions"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            ₹ Mn
          </button>
        </div>

        {/* Executive AI Assistant Button */}
        <button
          onClick={onOpenAIModal}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-blue-700 to-indigo-700 hover:from-blue-600 hover:to-indigo-600 text-white rounded-lg text-xs font-semibold shadow-xs transition-all cursor-pointer"
        >
          <Sparkles className="h-3.5 w-3.5 text-blue-200" />
          <span className="hidden sm:inline">AI CFO Advisor</span>
        </button>

        {/* Export PDF Report */}
        <button
          onClick={onExportPDF}
          className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-50 hover:bg-slate-100 border border-slate-300 text-slate-700 rounded-lg text-xs font-medium transition-colors cursor-pointer"
          title="Export Board-Ready PDF Presentation"
        >
          <Download className="h-3.5 w-3.5 text-slate-600" />
          <span className="hidden md:inline">Export</span>
        </button>

        {/* User Profile & Logout Button */}
        {user && (
          <div className="flex items-center gap-2 pl-1.5 sm:pl-2.5 border-l border-slate-200">
            <div className="hidden xl:flex flex-col items-end text-[10px]">
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-slate-800 truncate max-w-[130px]">
                  {user.user_metadata?.full_name || user.email?.split('@')[0]}
                </span>
                {isAdmin ? (
                  <span className="text-[8px] font-bold px-1.5 py-0.2 rounded bg-purple-100 text-purple-700 border border-purple-200 uppercase tracking-wider">
                    ADMIN
                  </span>
                ) : (
                  <span className="text-[8px] font-medium px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200 uppercase tracking-wider">
                    USER
                  </span>
                )}
              </div>
              <span className="text-slate-400 font-mono text-[9px] truncate max-w-[150px]">
                {user.email}
              </span>
            </div>
            <button
              onClick={() => signOut()}
              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
              title="Sign Out of CFO Analytics Suite"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
