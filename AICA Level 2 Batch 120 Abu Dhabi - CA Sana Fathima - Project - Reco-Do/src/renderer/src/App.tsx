import { HashRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ConfirmProvider, ToastProvider, TooltipProvider } from './components/ui'
import { Dashboard } from './pages/Dashboard'
import { ModulePage } from './pages/ModulePage'
import { ToolPage } from './pages/ToolPage'
import { WorkspacePage } from './pages/WorkspacePage'
import { loadPdfJs } from './lib/offlineAssets'
import { flushSessionSaves } from './lib/sessionSaves'
import { flushDraftSaves } from './lib/draftSaves'

// Configure the bundled pdf.js worker once, in the background (pdf.js loads as a separate chunk).
void loadPdfJs().catch(() => undefined)

// Closing the window waits for review decisions and draft reconciliations that are still being saved.
window.recoDo?.lifecycle?.onBeforeClose(async () => {
  await Promise.all([flushSessionSaves(), flushDraftSaves()])
})

function Shell(): React.JSX.Element {
  const location = useLocation()
  return (
    <div className="flex h-full">
      <a
        href="#main"
        onClick={(e) => {
          e.preventDefault()
          document.getElementById('main')?.focus()
        }}
        className="sr-only z-50 rounded-md bg-white px-3 py-2 text-sm font-semibold text-primary focus:not-sr-only focus:absolute focus:top-2 focus:left-2"
      >
        Skip to content
      </a>
      <Sidebar />
      <main id="main" tabIndex={-1} className="@container/main relative min-w-0 flex-1 overflow-y-auto px-5 pt-6 pb-8 outline-none min-[1200px]:px-8">
        <ErrorBoundary resetKey={location.pathname}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/module/:id" element={<ModulePage />} />
            <Route path="/tools/:id" element={<ToolPage />} />
            <Route path="/workspace/:id" element={<WorkspacePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  )
}

export function App(): React.JSX.Element {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <TooltipProvider>
          <ConfirmProvider>
            <HashRouter>
              <Shell />
            </HashRouter>
          </ConfirmProvider>
        </TooltipProvider>
      </ToastProvider>
    </ErrorBoundary>
  )
}
