import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./styles/index.css";
import AppLayout from "./layouts/AppLayout";
import { CaseProvider } from "./hooks/useCase";
import Dashboard from "./pages/Dashboard";
import NewValuation from "./pages/NewValuation";
import Financials from "./pages/Financials";
import Interview from "./pages/Interview";
import Valuations from "./pages/Valuations";
import SimulationLab from "./pages/SimulationLab";
import Insights from "./pages/Insights";
import Reports from "./pages/Reports";
import SettingsPage from "./pages/Settings";

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 15_000 } },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <CaseProvider>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/new-valuation" element={<NewValuation />} />
              <Route path="/financials" element={<Financials />} />
              <Route path="/interview" element={<Interview />} />
              <Route path="/valuations" element={<Valuations />} />
              <Route path="/simulation" element={<SimulationLab />} />
              <Route path="/insights" element={<Insights />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </CaseProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
