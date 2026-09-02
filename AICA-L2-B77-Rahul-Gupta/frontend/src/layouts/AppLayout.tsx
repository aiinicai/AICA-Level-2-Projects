/** Global application shell: sidebar, header, footer strip. */
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import {
  LayoutDashboard, Plus, FolderOpen, MessageSquareText, BadgeCheck,
  SlidersHorizontal, Lightbulb, FileText, Settings, Bell, HelpCircle,
  Building2, ChevronDown, Sparkles, ShieldCheck, BarChart3, GitBranch,
  FileSpreadsheet, Check,
} from "lucide-react";
import { api, IS_STATIC_DEMO } from "../services/api";
import { useCase } from "../hooks/useCase";
import { ProgressRing } from "../components/ui";
import type { CaseSummary } from "../types";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/new-valuation", label: "New Valuation", icon: Plus },
  { to: "/financials", label: "Financials", icon: FolderOpen },
  { to: "/interview", label: "AI Interview", icon: MessageSquareText },
  { to: "/valuations", label: "Valuations", icon: BadgeCheck },
  { to: "/simulation", label: "Simulation Lab", icon: SlidersHorizontal },
  { to: "/insights", label: "AI Insights", icon: Lightbulb },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings },
];

const PAGE_META: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Dashboard", subtitle: "Welcome back, Arjun! Here's what's happening with your valuations." },
  "/new-valuation": { title: "New Valuation", subtitle: "Create a new valuation case in a few simple steps." },
  "/financials": { title: "Financials", subtitle: "Upload, extract, and validate financial statements for accurate valuations." },
  "/interview": { title: "AI Interview", subtitle: "Intelligent interview to understand your business and drive accurate valuations." },
  "/valuations": { title: "Valuations", subtitle: "Comprehensive valuation analysis using multiple methods and AI-powered insights." },
  "/simulation": { title: "Simulation Lab", subtitle: "Model your assumptions, run scenarios, and understand value drivers." },
  "/insights": { title: "AI Insights", subtitle: "AI-generated analysis of business quality, drivers and risks." },
  "/reports": { title: "Reports", subtitle: "Generate professional valuation reports with AI-powered insights." },
  "/settings": { title: "Settings", subtitle: "Manage your AI, profile, notifications, and preferences." },
};

function CompanySelector() {
  const { cases, activeCase, setActiveCaseId } = useCase();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2.5 rounded-lg border border-line bg-surface pl-3.5 pr-3 py-2.5 min-w-[230px] hover:bg-page transition-colors"
      >
        <Building2 size={16} className="text-slate2" />
        <span className="text-sm font-semibold text-navy flex-1 text-left truncate">
          {activeCase?.company_name ?? "Select company"}
        </span>
        <ChevronDown size={15} className="text-slate2" />
      </button>
      {open && (
        <div className="absolute right-0 top-12 z-30 w-72 card shadow-pop p-1.5">
          {cases.map((c: CaseSummary) => (
            <button
              key={c.id}
              onClick={() => { setActiveCaseId(c.id); setOpen(false); }}
              className={`w-full flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-left hover:bg-page ${c.id === activeCase?.id ? "bg-primary-50" : ""}`}
            >
              <Building2 size={15} className="text-slate2 shrink-0" />
              <span className="flex-1 min-w-0">
                <span className="block text-sm font-semibold text-navy truncate">{c.company_name}</span>
                <span className="block text-xs text-slate3">{c.industry}</span>
              </span>
              {c.id === activeCase?.id && <Check size={15} className="text-primary" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ReadinessWidget() {
  const { activeCaseId } = useCase();
  const { data } = useQuery({
    queryKey: ["case", activeCaseId],
    queryFn: () => api.get<CaseSummary>(`/api/valuations/${activeCaseId}`),
    enabled: !!activeCaseId,
    refetchInterval: 30000,
  });
  const score = data?.readiness?.score ?? 0;
  const label = data?.readiness?.label ?? "—";
  return (
    <div className="card p-4 text-center">
      <p className="text-[13px] font-semibold text-navy mb-2.5">Valuation Readiness</p>
      <ProgressRing value={score} size={92} stroke={9} gradient>
        <span className="text-xl font-extrabold text-navy">{score}%</span>
        <span className="text-[11px] font-semibold text-mint-text">{label}</span>
      </ProgressRing>
      <p className="text-[11px] text-slate3 mt-2.5">Last updated: 2 min ago</p>
    </div>
  );
}

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const meta = PAGE_META[location.pathname] ?? { title: "CompanyVal AI", subtitle: "" };

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-[232px] shrink-0 bg-surface border-r border-line flex flex-col fixed inset-y-0 left-0 z-20">
        <div className="flex items-center gap-2.5 px-5 pt-5 pb-4">
          <img src={`${import.meta.env.BASE_URL}logo.svg`} alt="CompanyVal AI" className="h-9 w-9" />
          <div>
            <p className="text-[15px] font-extrabold text-primary leading-tight">CompanyVal AI</p>
            <p className="text-[10.5px] text-slate3 font-medium">AI-Powered Valuation</p>
          </div>
        </div>
        <nav className="px-3 flex-1 overflow-y-auto">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3.5 py-2.5 mb-1 text-sm font-semibold transition-colors ${
                  isActive ? "bg-primary text-white shadow-card" : "text-slate2 hover:bg-page hover:text-navy"
                }`
              }
            >
              <Icon size={17} strokeWidth={2.1} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 pb-4 space-y-3">
          <div className="card px-3.5 py-3 flex items-center gap-3">
            <span className="h-9 w-9 rounded-full bg-primary-50 text-primary text-xs font-extrabold flex items-center justify-center">AD</span>
            <div className="min-w-0">
              <p className="text-[13px] font-bold text-navy truncate">Arjun Demo</p>
              <p className="text-[11px] text-slate3">Analyst</p>
            </div>
          </div>
          <ReadinessWidget />
          <p className="text-[10.5px] text-slate3 text-center">© 2025 CompanyVal AI</p>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 ml-[232px] flex flex-col min-h-screen">
        {IS_STATIC_DEMO && (
          <div className="bg-primary-50 border-b border-primary-100/70 px-8 py-2 text-[12.5px] text-primary-700 flex items-center gap-2">
            <Sparkles size={13} className="shrink-0" />
            <span>
              <b>Static preview</b> — a GitHub Pages snapshot of the seeded demo, computed by the real
              engine. Simulation Lab is fully interactive; document upload, AI verification, the adaptive
              interview and report generation run in the full app —{" "}
              <a className="underline font-semibold" href="https://github.com/rahulguptaca/AICA-L2-B77-Ghaziabad-Capstone_Project#readme"
                target="_blank" rel="noreferrer">run it locally from the repo</a>.
            </span>
          </div>
        )}
        <header className="flex items-start justify-between gap-4 px-8 pt-6 pb-4">
          <div>
            <h1 className="text-[26px] font-extrabold text-navy leading-tight">{meta.title}</h1>
            <p className="text-sm text-slate2 mt-1">{meta.subtitle}</p>
          </div>
          <div className="flex items-center gap-3">
            <CompanySelector />
            <button className="btn-primary" onClick={() => navigate("/new-valuation")}>
              <Plus size={16} /> New Valuation
            </button>
            <button className="relative h-10 w-10 card flex items-center justify-center hover:bg-page" title="Notifications">
              <Bell size={17} className="text-slate2" />
              <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-mint ring-2 ring-white" />
            </button>
            <button className="h-10 w-10 card flex items-center justify-center hover:bg-page" title="Help">
              <HelpCircle size={17} className="text-slate2" />
            </button>
          </div>
        </header>

        <main className="flex-1 px-8 pb-6">
          <Outlet />
        </main>

        <footer className="mx-8 mb-6 card bg-primary-50/50 border-primary-100/60 px-6 py-3.5">
          <div className="flex items-center justify-between text-[13px] font-semibold text-primary-700">
            <span className="flex items-center gap-2"><Sparkles size={15} /> AI Powered Intelligence</span>
            <span className="flex items-center gap-2"><ShieldCheck size={15} /> Verified Accuracy</span>
            <span className="flex items-center gap-2"><BarChart3 size={15} /> Explainable Valuation</span>
            <span className="flex items-center gap-2"><GitBranch size={15} /> Scenario Simulation</span>
            <span className="flex items-center gap-2"><FileSpreadsheet size={15} /> Professional Reports</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
