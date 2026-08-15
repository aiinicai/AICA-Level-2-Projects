import { useState } from "react";
import "@/App.css";
import "@/index.css";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";

// Pages
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import SuppliersPage from "./pages/SuppliersPage";
import MaterialsPage from "./pages/MaterialsPage";
import PurchaseOrdersPage from "./pages/PurchaseOrdersPage";
import StorePage from "./pages/StorePage";
import ChemistReportsPage from "./pages/ChemistReportsPage";
import ProductionPage from "./pages/ProductionPage";
import PackagingPage from "./pages/PackagingPage";
import DispatchPage from "./pages/DispatchPage";
import ReportsPage from "./pages/ReportsPage";
import UsersPage from "./pages/UsersPage";
import ProductsPage from "./pages/ProductsPage";

// Components
import Sidebar from "./components/Sidebar";

const ProtectedRoute = ({ children }) => {
    const { user, loading } = useAuth();
    
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900"></div>
            </div>
        );
    }
    
    if (!user) {
        return <Navigate to="/login" replace />;
    }
    
    return children;
};

const AdminRoute = ({ children }) => {
    const { user, hasRole } = useAuth();
    
    if (!hasRole('admin')) {
        return <Navigate to="/dashboard" replace />;
    }
    
    return children;
};

const DashboardLayout = () => {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    
    return (
        <div className="flex min-h-screen bg-slate-50">
            <Sidebar collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />
            <main className={`flex-1 p-6 lg:p-8 transition-all duration-200 ${sidebarCollapsed ? 'lg:ml-0' : ''}`}>
                <div className="max-w-[1600px] mx-auto">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};

function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Toaster 
                    position="top-right" 
                    richColors 
                    toastOptions={{
                        style: {
                            borderRadius: '2px',
                            fontFamily: 'Inter, sans-serif'
                        }
                    }}
                />
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    
                    <Route path="/" element={
                        <ProtectedRoute>
                            <DashboardLayout />
                        </ProtectedRoute>
                    }>
                        <Route index element={<Navigate to="/dashboard" replace />} />
                        <Route path="dashboard" element={<Dashboard />} />
                        <Route path="suppliers" element={<SuppliersPage />} />
                        <Route path="materials" element={<MaterialsPage />} />
                        <Route path="products" element={<ProductsPage />} />
                        <Route path="purchase-orders" element={<PurchaseOrdersPage />} />
                        <Route path="store" element={<StorePage />} />
                        <Route path="chemist-reports" element={<ChemistReportsPage />} />
                        <Route path="production" element={<ProductionPage />} />
                        <Route path="packaging" element={<PackagingPage />} />
                        <Route path="dispatch" element={<DispatchPage />} />
                        <Route path="reports" element={<ReportsPage />} />
                        <Route path="users" element={
                            <AdminRoute>
                                <UsersPage />
                            </AdminRoute>
                        } />
                    </Route>
                    
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
            </BrowserRouter>
        </AuthProvider>
    );
}

export default App;
