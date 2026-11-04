/// <reference types="vite/client" />
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Mount React Root
const rootElement = document.getElementById('root');
if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

// Register Service Worker for offline PWA capabilities (production cloud only, never localhost)
if (
  'serviceWorker' in navigator &&
  (import.meta as any).env?.PROD &&
  window.location.hostname !== 'localhost' &&
  window.location.hostname !== '127.0.0.1'
) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        console.log('Bullion Ledger PWA Service Worker registered:', registration.scope);
      })
      .catch((err) => {
        console.warn('Bullion Ledger Service Worker registration failed:', err);
      });
  });
}
