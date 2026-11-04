import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, HashRouter } from 'react-router-dom';
import { registerSW } from 'virtual:pwa-register';
import { StoreProvider } from './data/store';
import { ConfirmProvider, ToastProvider } from './ui/common';
import { App } from './App';
import { ErrorBoundary } from './ui/ErrorBoundary';
import { misconfigured } from './lib/backend';
import './styles.css';

// `npm run build:file` makes "Vouchr demo.html", opened straight from a folder (file://): no service worker there, and
// page addresses use # so they work without a web server.
const fileDemo = import.meta.env.MODE === 'file';
if (!fileDemo) registerSW({ immediate: true });
const Router = fileDemo ? HashRouter : BrowserRouter;

const root = ReactDOM.createRoot(document.getElementById('root')!);
if (misconfigured) {
  root.render(<div style={{ padding: 32, fontFamily: 'system-ui', maxWidth: 520 }}><h1>Vouchr is not configured</h1><p>This build has no server connection. Data would only be kept in this browser, so the app will not start. Ask your administrator to set the Supabase settings (or VITE_DEMO=true for a demo).</p></div>);
} else root.render(
  <React.StrictMode>
    <Router>
      <StoreProvider>
        <ToastProvider>
          <ConfirmProvider>
            <ErrorBoundary>
              <App />
            </ErrorBoundary>
          </ConfirmProvider>
        </ToastProvider>
      </StoreProvider>
    </Router>
  </React.StrictMode>
);
