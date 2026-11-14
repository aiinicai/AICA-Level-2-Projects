import { Navigate, Route, Routes } from 'react-router-dom';
import { useStore } from './data/store';
import type { Role } from './data/types';
import { Shell } from './ui/Shell';
import { Login } from './pages/Login';
import { StaffHome } from './pages/StaffHome';
import { Capture } from './pages/Capture';
import { lazy, Suspense, type ReactElement } from 'react';
import { ConsentBlocked, ConsentGate } from './pages/ConsentGate';
import { clientConsent, userConsent } from './lib/consent';
import { todayIso } from './lib/dates';

// screens load on demand (smaller first download on phones)
const Entries = lazy(() => import('./pages/Entries').then((m) => ({ default: m.Entries })));
const Dues = lazy(() => import('./pages/Dues').then((m) => ({ default: m.Dues })));
const Import = lazy(() => import('./pages/Import').then((m) => ({ default: m.Import })));
const Risk = lazy(() => import('./pages/Risk').then((m) => ({ default: m.Risk })));
const Ask = lazy(() => import('./pages/Ask').then((m) => ({ default: m.Ask })));
const Privacy = lazy(() => import('./pages/Privacy').then((m) => ({ default: m.Privacy })));
const Alerts = lazy(() => import('./pages/Alerts').then((m) => ({ default: m.Alerts })));
const Mis = lazy(() => import('./pages/Mis').then((m) => ({ default: m.Mis })));
const Vendors = lazy(() => import('./pages/Vendors').then((m) => ({ default: m.Vendors })));
const Tally = lazy(() => import('./pages/Tally').then((m) => ({ default: m.Tally })));
const Settings = lazy(() => import('./pages/Settings').then((m) => ({ default: m.Settings })));
const FirmOverview = lazy(() => import('./pages/FirmOverview').then((m) => ({ default: m.FirmOverview })));
const Review = lazy(() => import('./pages/Review').then((m) => ({ default: m.Review })));
const Masters = lazy(() => import('./pages/Masters').then((m) => ({ default: m.Masters })));
const Compliance = lazy(() => import('./pages/Compliance').then((m) => ({ default: m.Compliance })));
const Audit = lazy(() => import('./pages/Audit').then((m) => ({ default: m.Audit })));
const Reco = lazy(() => import('./pages/Reco').then((m) => ({ default: m.Reco })));
const Tds = lazy(() => import('./pages/Tds').then((m) => ({ default: m.Tds })));
const FyClose = lazy(() => import('./pages/FyClose').then((m) => ({ default: m.FyClose })));
const GstRegisters = lazy(() => import('./pages/GstRegisters').then((m) => ({ default: m.GstRegisters })));
const Reports = lazy(() => import('./pages/Reports').then((m) => ({ default: m.Reports })));
const More = lazy(() => import('./pages/More').then((m) => ({ default: m.More })));
const Inbox = lazy(() => import('./pages/Inbox').then((m) => ({ default: m.Inbox })));
const Bank = lazy(() => import('./pages/Bank').then((m) => ({ default: m.Bank })));

function Only({ roles, children }: { roles: Role[]; children: ReactElement }) {
  const { me } = useStore();
  return me && roles.includes(me.role) ? children : <Navigate to="/" replace />;
}

const ADMINS: Role[] = ['client_admin', 'super_admin'];
const SUPER: Role[] = ['super_admin'];

export function App() {
  const { me, s, client } = useStore();
  if (!me) return <Login />;
  // DPDP: no use of the app without a valid consent; a company that withdrew (or whose engagement ended) is blocked
  const today = todayIso();
  if (me.role !== 'super_admin' && me.clientId) {
    const cc = clientConsent(s.consents, me.clientId, today);
    if (cc.state === 'withdrawn') return <ConsentBlocked reason="withdrawn" />;
    if (cc.state === 'expired' || (client?.engagementEndsOn && client.engagementEndsOn < today)) return <ConsentBlocked reason="expired" />;
  }
  if (!userConsent(s.consents, me.id, today)) return <ConsentGate />;

  const home = me.role === 'sub_user' ? <StaffHome /> : me.role === 'client_admin' ? <Mis /> : <FirmOverview />;

  return (
    <Shell>
      <Suspense fallback={<div className="content"><div className="card pad shimmer" style={{ height: 120 }} /></div>}>
      <Routes>
        <Route path="/" element={home} />
        <Route path="/capture" element={<Capture />} />
        <Route path="/entries" element={<Entries />} />
        <Route path="/dues" element={<Dues />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/mis" element={<Only roles={ADMINS}><Mis /></Only>} />
        <Route path="/vendors" element={<Only roles={ADMINS}><Vendors /></Only>} />
        <Route path="/tally" element={<Only roles={ADMINS}><Tally /></Only>} />
        <Route path="/settings" element={<Only roles={ADMINS}><Settings /></Only>} />
        <Route path="/review" element={<Only roles={SUPER}><Review /></Only>} />
        <Route path="/masters" element={<Only roles={SUPER}><Masters /></Only>} />
        <Route path="/compliance" element={<Only roles={SUPER}><Compliance /></Only>} />
        <Route path="/audit" element={<Only roles={SUPER}><Audit /></Only>} />
        <Route path="/reco" element={<Only roles={SUPER}><Reco /></Only>} />
        <Route path="/tds" element={<Only roles={ADMINS}><Tds /></Only>} />
        <Route path="/gst" element={<Only roles={ADMINS}><GstRegisters /></Only>} />
        <Route path="/fy-close" element={<Only roles={SUPER}><FyClose /></Only>} />
        <Route path="/inbox" element={<Inbox />} />
        <Route path="/bank" element={<Only roles={ADMINS}><Bank /></Only>} />
        <Route path="/reports" element={<Only roles={ADMINS}><Reports /></Only>} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/ask" element={<Only roles={ADMINS}><Ask /></Only>} />
        <Route path="/risk" element={<Only roles={ADMINS}><Risk /></Only>} />
        <Route path="/import" element={<Only roles={ADMINS}><Import /></Only>} />
        <Route path="/more" element={<Only roles={ADMINS}><More /></Only>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </Shell>
  );
}
