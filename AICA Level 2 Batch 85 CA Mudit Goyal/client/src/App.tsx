import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { SettingsProvider } from './contexts/SettingsContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Invoices from './pages/Invoices';
import Attendance from './pages/Attendance';
import AttendanceRegister from './pages/AttendanceRegister';
import StaffPage from './pages/Staff';
import SettingsPage from './pages/Settings';

const Loading: React.FC = () => (
  <div className="min-h-screen grid place-items-center text-sm text-gray-500">Loading…</div>
);

const Protected: React.FC<{ children: React.ReactNode; adminOnly?: boolean }> = ({ children, adminOnly }) => {
  const { user, loading, isAdmin } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  // An admin-only page reached by a staff member is a wrong turn, not an
  // error — send them somewhere they can actually use.
  if (adminOnly && !isAdmin) return <Navigate to="/dashboard" replace />;
  return <Layout>{children}</Layout>;
};

const Routing: React.FC = () => (
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
    <Route path="/invoices" element={<Protected><Invoices /></Protected>} />
    <Route path="/attendance" element={<Protected><Attendance /></Protected>} />
    <Route path="/attendance/register" element={<Protected adminOnly><AttendanceRegister /></Protected>} />
    <Route path="/staff" element={<Protected adminOnly><StaffPage /></Protected>} />
    {/* Reachable by everyone: staff get the "My account" section, admins get all three. */}
    <Route path="/settings" element={<Protected><SettingsPage /></Protected>} />
    <Route path="*" element={<Navigate to="/dashboard" replace />} />
  </Routes>
);

const App: React.FC = () => (
  <AuthProvider>
    <SettingsProvider>
      <BrowserRouter>
        <Routing />
      </BrowserRouter>
    </SettingsProvider>
  </AuthProvider>
);

export default App;
