import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// ── Service worker (PWA) ────────────────────────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        // A phone left open on the attendance screen for a whole shift would
        // otherwise never notice a new version.
        setInterval(() => registration.update(), 60 * 1000);

        registration.onupdatefound = () => {
          const installing = registration.installing;
          if (!installing) return;
          installing.onstatechange = () => {
            if (installing.state === 'installed' && navigator.serviceWorker.controller) {
              window.dispatchEvent(new CustomEvent('sw-update-available'));
            }
          };
        };
      })
      .catch((err) => console.error('[SW] registration failed:', err));
  });
}
