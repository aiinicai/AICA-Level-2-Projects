import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { registerSW } from 'virtual:pwa-register';

// Register service worker for complete PWA installation support
registerSW({
  immediate: true,
  onNeedRefresh() {
    console.log('New content available, reload to update');
  },
  onOfflineReady() {
    console.log('App ready to work offline');
  }
});

// Suppress benign WebSocket errors from Vite HMR in cloud iframe preview
window.addEventListener('unhandledrejection', (event) => {
  const msg = event?.reason?.message || (typeof event?.reason === 'string' ? event.reason : '');
  if (msg && (msg.includes('WebSocket') || msg.includes('websocket'))) {
    event.preventDefault();
  }
});

createRoot(document.getElementById('root')!).render(<App />);
