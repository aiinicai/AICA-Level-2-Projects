import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import './index.css';
import App from './App.jsx';
import PaymentPage from './pages/PaymentPage.jsx';
import { AuthProvider } from './contexts/AuthContext.jsx';

function PixelRouteTracker() {
  const location = useLocation();
  React.useEffect(() => {
    if (typeof window !== 'undefined' && window.fbq) {
      console.log('[GSTMitra DEBUG] Firing Meta Pixel PageView for route:', location.pathname);
      window.fbq('track', 'PageView');
    }
  }, [location.pathname, location.search]);
  return null;
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <PixelRouteTracker />
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/payment" element={<PaymentPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
