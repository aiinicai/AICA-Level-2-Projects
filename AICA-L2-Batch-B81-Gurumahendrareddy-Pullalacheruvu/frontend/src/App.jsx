import React from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AppProvider, useApp } from './lib/store'
import Shell from './components/Shell'
import Login from './pages/Login'
import Today from './pages/Today'
import RunwayBurn from './pages/RunwayBurn'
import Liquidity from './pages/Liquidity'
import MoneyIn from './pages/MoneyIn'
import MoneyOut from './pages/MoneyOut'
import CashCalendar from './pages/CashCalendar'
import PlanVsActual from './pages/PlanVsActual'
import Scenarios from './pages/Scenarios'
import CapitalDebt from './pages/CapitalDebt'
import BoardPack from './pages/BoardPack'
import Alerts from './pages/Alerts'
import Setup from './pages/Setup'
import Welcome from './pages/Welcome'
import SetupWizard from './pages/SetupWizard'

function Boot() {
  return (
    <div className="h-full grid place-items-center">
      <div className="text-center">
        <div className="w-9 h-9 rounded-xl bg-navy-700 grid place-items-center mx-auto mb-3 animate-pulse">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white"
               strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 17l6-6 4 4 8-8" /><path d="M15 6h6v6" />
          </svg>
        </div>
        <p className="text-[13px] text-ink-muted">Loading your position…</p>
      </div>
    </div>
  )
}

function Protected({ children }) {
  const { user, booting, firstRun } = useApp()
  const loc = useLocation()
  if (booting) return <Boot />
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />
  // Nothing set up yet: the twelve screens have nothing to say, so the first
  // question comes first.
  if (firstRun) return <Navigate to="/welcome" replace />
  return <Shell>{children}</Shell>
}

/** Signed in, but outside the twelve-tab shell — the two set-up screens. */
function Bare({ children }) {
  const { user, booting } = useApp()
  const loc = useLocation()
  if (booting) return <Boot />
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />
  return <div className="h-full overflow-y-auto bg-paper">{children}</div>
}

function Router() {
  const { user, booting } = useApp()
  return (
    <Routes>
      <Route path="/login" element={
        booting ? <Boot /> : user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/welcome"        element={<Bare><Welcome /></Bare>} />
      <Route path="/set-up"         element={<Bare><SetupWizard /></Bare>} />
      <Route path="/"               element={<Protected><Today /></Protected>} />
      <Route path="/runway-burn"    element={<Protected><RunwayBurn /></Protected>} />
      <Route path="/liquidity"      element={<Protected><Liquidity /></Protected>} />
      <Route path="/money-in"       element={<Protected><MoneyIn /></Protected>} />
      <Route path="/money-out"      element={<Protected><MoneyOut /></Protected>} />
      <Route path="/cash-calendar"  element={<Protected><CashCalendar /></Protected>} />
      <Route path="/plan-vs-actual" element={<Protected><PlanVsActual /></Protected>} />
      <Route path="/scenarios"      element={<Protected><Scenarios /></Protected>} />
      <Route path="/capital-debt"   element={<Protected><CapitalDebt /></Protected>} />
      <Route path="/board-pack"     element={<Protected><BoardPack /></Protected>} />
      <Route path="/alerts"         element={<Protected><Alerts /></Protected>} />
      <Route path="/setup"          element={<Protected><Setup /></Protected>} />
      <Route path="*"               element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return <AppProvider><Router /></AppProvider>
}
