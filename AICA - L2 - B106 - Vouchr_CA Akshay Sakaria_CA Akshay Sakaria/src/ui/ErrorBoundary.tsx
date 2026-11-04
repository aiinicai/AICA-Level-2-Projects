import { Component, type ReactNode } from 'react';
import { STORE_KEY } from '../data/store';

// Any crash shows a calm recovery screen instead of a blank page, and is recorded for the
// super-admin Audit & health panel (production: insert into system_events, component 'client_app').
export class ErrorBoundary extends Component<{ children: ReactNode }, { error?: Error }> {
  state: { error?: Error } = {};

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (raw) {
        const s = JSON.parse(raw);
        s.events = [{ id: Math.random().toString(36).slice(2), level: 'error', component: 'client_app', message: `Screen crashed: ${error.message}`, at: new Date().toISOString() }, ...(s.events ?? [])];
        localStorage.setItem(STORE_KEY, JSON.stringify(s));
      }
    } catch { /* storage unavailable */ }
  }

  render() {
    if (!this.state.error) return this.props.children;
    let hi = false;
    try { hi = JSON.parse(localStorage.getItem(STORE_KEY) ?? '{}').lang === 'hi'; } catch { /* default English */ }
    return (
      <div className="login">
        <div className="card login-card stack" style={{ textAlign: 'center' }}>
          <h1>{hi ? 'कुछ गड़बड़ हो गई' : 'Something went wrong'}</h1>
          <p className="muted">{hi ? 'आपकी सेव की गई एंट्री सुरक्षित हैं। समस्या की जानकारी सपोर्ट को भेज दी गई है।' : 'Your saved entries are safe. The problem has been reported to support.'}</p>
          <button className="btn primary lg block" onClick={() => location.assign('/')}>{hi ? 'ऐप फिर से खोलें' : 'Reload app'}</button>
        </div>
      </div>
    );
  }
}
