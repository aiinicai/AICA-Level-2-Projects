import {createRoot} from 'react-dom/client';
import {registerSW} from 'virtual:pwa-register';
import App from './App.tsx';
import { ErrorBoundary } from './components/ErrorBoundary.tsx';
import './index.css';

// Handle PWA service worker safely:
// In production, register the service worker for offline use and installability.
// In development, clear any stale service workers to prevent iframe/Safari caching stalls.
if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  if (import.meta.env.PROD) {
    try {
      registerSW({
        immediate: true,
        onNeedRefresh() {
          console.log('Paisa Pal update available');
        },
        onOfflineReady() {
          console.log('Paisa Pal ready for offline use');
        },
      });
    } catch (err) {
      console.warn('Service worker registration failed or unsupported in this context:', err);
    }
  } else {
    // Unregister any old dev service workers
    navigator.serviceWorker.getRegistrations().then((registrations) => {
      for (const registration of registrations) {
        registration.unregister();
      }
    }).catch(() => {});
  }
}

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
);

