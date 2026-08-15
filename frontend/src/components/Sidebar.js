import { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
    LayoutDashboard, 
    FlaskConical, 
    Package, 
    Truck, 
    Users, 
    FileText,
    ShoppingCart,
    Warehouse,
    Beaker,
    PackageCheck,
    ChevronLeft,
    ChevronRight,
    LogOut,
    Settings,
    Menu,
    X,
    Sparkles
} from 'lucide-react';

const menuItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/suppliers', icon: Users, label: 'Suppliers' },
    { path: '/materials', icon: FlaskConical, label: 'Raw Materials' },
    { path: '/products', icon: Sparkles, label: 'Finished Products' },
    { path: '/purchase-orders', icon: ShoppingCart, label: 'Purchase Orders' },
    { path: '/store', icon: Warehouse, label: 'Store Inventory' },
    { path: '/chemist-reports', icon: Beaker, label: 'Chemist Reports' },
    { path: '/production', icon: Package, label: 'Production' },
    { path: '/packaging', icon: PackageCheck, label: 'Packaging' },
    { path: '/dispatch', icon: Truck, label: 'Dispatch' },
    { path: '/reports', icon: FileText, label: 'Reports' },
];

const adminItems = [
    { path: '/users', icon: Settings, label: 'User Management' },
];

const Sidebar = ({ collapsed, setCollapsed }) => {
    const { user, logout, hasRole } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [mobileOpen, setMobileOpen] = useState(false);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const NavContent = () => (
        <>
            {/* Logo */}
            <div className={`p-4 border-b border-slate-700 ${collapsed ? 'px-2' : ''}`}>
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white rounded-sm flex items-center justify-center flex-shrink-0">
                        <FlaskConical className="w-6 h-6 text-slate-900" />
                    </div>
                    {!collapsed && (
                        <div>
                            <h1 className="text-white font-heading text-lg font-bold tracking-tight">COSMETIC</h1>
                            <p className="text-slate-400 text-[10px] tracking-widest">INVENTORY</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-3 overflow-y-auto">
                <div className="space-y-1">
                    {menuItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            onClick={() => setMobileOpen(false)}
                            className={({ isActive }) => 
                                `sidebar-link ${isActive ? 'active' : ''} ${collapsed ? 'justify-center px-2' : ''}`
                            }
                            title={collapsed ? item.label : ''}
                        >
                            <item.icon size={20} />
                            {!collapsed && <span>{item.label}</span>}
                        </NavLink>
                    ))}
                </div>

                {hasRole('admin') && (
                    <div className="mt-6 pt-6 border-t border-slate-700">
                        <p className={`text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2 ${collapsed ? 'text-center' : 'px-4'}`}>
                            {collapsed ? 'ADM' : 'Admin'}
                        </p>
                        {adminItems.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                onClick={() => setMobileOpen(false)}
                                className={({ isActive }) => 
                                    `sidebar-link ${isActive ? 'active' : ''} ${collapsed ? 'justify-center px-2' : ''}`
                                }
                                title={collapsed ? item.label : ''}
                            >
                                <item.icon size={20} />
                                {!collapsed && <span>{item.label}</span>}
                            </NavLink>
                        ))}
                    </div>
                )}
            </nav>

            {/* User & Logout */}
            <div className={`p-4 border-t border-slate-700 ${collapsed ? 'px-2' : ''}`}>
                {!collapsed && user && (
                    <div className="mb-3 px-3">
                        <p className="text-white text-sm font-medium truncate">{user.name}</p>
                        <p className="text-slate-400 text-xs capitalize">{user.role.replace('_', ' ')}</p>
                    </div>
                )}
                <button 
                    onClick={handleLogout}
                    data-testid="logout-btn"
                    className={`sidebar-link text-red-400 hover:text-red-300 hover:bg-red-500/10 w-full ${collapsed ? 'justify-center px-2' : ''}`}
                >
                    <LogOut size={20} />
                    {!collapsed && <span>Logout</span>}
                </button>
            </div>
        </>
    );

    return (
        <>
            {/* Mobile Menu Button */}
            <button 
                onClick={() => setMobileOpen(true)}
                className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-slate-900 text-white rounded-sm shadow-lg"
                data-testid="mobile-menu-btn"
            >
                <Menu size={20} />
            </button>

            {/* Mobile Overlay */}
            {mobileOpen && (
                <div 
                    className="lg:hidden fixed inset-0 bg-black/50 z-40"
                    onClick={() => setMobileOpen(false)}
                />
            )}

            {/* Mobile Sidebar */}
            <aside className={`lg:hidden fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 transform transition-transform duration-200 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
                <button 
                    onClick={() => setMobileOpen(false)}
                    className="absolute top-4 right-4 text-slate-400 hover:text-white"
                >
                    <X size={20} />
                </button>
                <div className="flex flex-col h-full">
                    <NavContent />
                </div>
            </aside>

            {/* Desktop Sidebar */}
            <aside 
                className={`hidden lg:flex flex-col bg-slate-900 h-screen sticky top-0 transition-all duration-200 ${collapsed ? 'w-16' : 'w-64'}`}
                data-testid="sidebar"
            >
                <NavContent />
                
                {/* Collapse Toggle */}
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="absolute -right-3 top-20 w-6 h-6 bg-slate-900 border border-slate-700 rounded-full flex items-center justify-center text-slate-400 hover:text-white"
                    data-testid="collapse-sidebar-btn"
                >
                    {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
                </button>
            </aside>
        </>
    );
};

export default Sidebar;
