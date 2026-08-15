import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
    FlaskConical, Package, Truck, Warehouse, AlertTriangle, 
    TrendingUp, Clock, CheckCircle2, ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard = () => {
    const { api, user } = useAuth();
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchStats = useCallback(async () => {
        try {
            const res = await api().get('/dashboard/stats');
            setStats(res.data);
        } catch (err) {
            console.error('Failed to fetch stats:', err);
        }
        setLoading(false);
    }, [api]);

    useEffect(() => {
        fetchStats();
    }, [fetchStats]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900"></div>
            </div>
        );
    }

    const stageCards = [
        { 
            label: 'Raw Materials', 
            value: stats?.materials?.total || 0, 
            icon: FlaskConical, 
            color: 'stage-raw',
            link: '/materials',
            sub: `${stats?.materials?.chemicals || 0} chemicals, ${stats?.materials?.packing || 0} packing`
        },
        { 
            label: 'Pending POs', 
            value: stats?.stages?.pending_po || 0, 
            icon: Clock, 
            color: 'stage-store',
            link: '/purchase-orders',
            sub: 'Awaiting approval'
        },
        { 
            label: 'In Production', 
            value: stats?.stages?.in_production || 0, 
            icon: Package, 
            color: 'stage-production',
            link: '/production',
            sub: 'Batches processing'
        },
        { 
            label: 'In Packaging', 
            value: stats?.stages?.in_packaging || 0, 
            icon: Warehouse, 
            color: 'stage-packaging',
            link: '/packaging',
            sub: 'Ready for packing'
        },
        { 
            label: 'Dispatched Today', 
            value: stats?.stages?.dispatched_today || 0, 
            icon: Truck, 
            color: 'stage-dispatch',
            link: '/dispatch',
            sub: 'Shipments out'
        },
    ];

    const lowStockItems = stats?.materials?.low_stock || [];
    const expiringBatches = stats?.expiring_batches || [];

    return (
        <div className="space-y-6" data-testid="dashboard">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">
                        DASHBOARD
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">
                        Welcome back, {user?.name}. Here's your inventory overview.
                    </p>
                </div>
                <div className="text-right">
                    <p className="font-mono text-sm text-slate-500">
                        {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                    </p>
                </div>
            </div>

            {/* Stage Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                {stageCards.map((card, idx) => (
                    <Link 
                        key={card.label}
                        to={card.link}
                        className={`card-default p-5 group animate-fadeIn`}
                        style={{ animationDelay: `${idx * 0.05}s` }}
                        data-testid={`stage-card-${card.label.toLowerCase().replace(/\s/g, '-')}`}
                    >
                        <div className="flex items-start justify-between">
                            <div className={`w-10 h-10 rounded-sm flex items-center justify-center ${card.color}`}>
                                <card.icon size={20} />
                            </div>
                            <ArrowRight size={16} className="text-slate-300 group-hover:text-slate-500 transition-colors" />
                        </div>
                        <div className="mt-4">
                            <p className="font-mono text-3xl font-medium text-slate-900">{card.value}</p>
                            <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mt-1">{card.label}</p>
                            <p className="text-xs text-slate-400 mt-1">{card.sub}</p>
                        </div>
                    </Link>
                ))}
            </div>

            {/* Quick Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="metric-card">
                    <p className="metric-label">Total Suppliers</p>
                    <p className="metric-value">{stats?.suppliers || 0}</p>
                </div>
                <div className="metric-card">
                    <p className="metric-label">Total Products</p>
                    <p className="metric-value">{stats?.products || 0}</p>
                </div>
                <div className="metric-card">
                    <p className="metric-label">Pending Reports</p>
                    <p className="metric-value">{stats?.stages?.pending_reports || 0}</p>
                </div>
            </div>

            {/* Alerts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Low Stock Alert */}
                <div className="card-default" data-testid="low-stock-alert">
                    <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-amber-100 rounded-sm flex items-center justify-center">
                                <AlertTriangle size={16} className="text-amber-600" />
                            </div>
                            <h3 className="font-heading font-semibold text-slate-900">Low Stock Alerts</h3>
                        </div>
                        <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-sm">
                            {lowStockItems.length} items
                        </span>
                    </div>
                    <div className="p-4 max-h-64 overflow-y-auto">
                        {lowStockItems.length === 0 ? (
                            <div className="flex items-center gap-3 text-green-600">
                                <CheckCircle2 size={18} />
                                <span className="text-sm">All stock levels are healthy</span>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {lowStockItems.map((item) => (
                                    <div key={item.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-sm">
                                        <div>
                                            <p className="text-sm font-medium text-slate-900">{item.name}</p>
                                            <p className="text-xs text-slate-500 uppercase">{item.category} • {item.sku}</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="font-mono text-sm text-red-600 font-medium">
                                                {item.current_stock} {item.unit}
                                            </p>
                                            <p className="text-xs text-slate-400">
                                                Min: {item.min_stock_level}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Expiring Batches */}
                <div className="card-default" data-testid="expiring-batches">
                    <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-rose-100 rounded-sm flex items-center justify-center">
                                <Clock size={16} className="text-rose-600" />
                            </div>
                            <h3 className="font-heading font-semibold text-slate-900">Expiring Soon</h3>
                        </div>
                        <span className="px-2 py-1 bg-rose-100 text-rose-700 text-xs font-bold rounded-sm">
                            {expiringBatches.length} batches
                        </span>
                    </div>
                    <div className="p-4 max-h-64 overflow-y-auto">
                        {expiringBatches.length === 0 ? (
                            <div className="flex items-center gap-3 text-green-600">
                                <CheckCircle2 size={18} />
                                <span className="text-sm">No batches expiring within 30 days</span>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {expiringBatches.map((batch) => (
                                    <div key={batch.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-sm">
                                        <div>
                                            <p className="text-sm font-medium text-slate-900">{batch.material_name}</p>
                                            <p className="font-mono text-xs text-slate-500">{batch.batch_number}</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="font-mono text-sm text-rose-600 font-medium">
                                                {batch.expiry_date}
                                            </p>
                                            <p className="text-xs text-slate-400">
                                                Qty: {batch.quantity}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Manufacturing Flow Visualization */}
            <div className="card-default p-6" data-testid="manufacturing-flow">
                <h3 className="font-heading font-semibold text-slate-900 mb-6">Manufacturing Flow</h3>
                <div className="flex items-center justify-between overflow-x-auto pb-2">
                    {[
                        { label: 'Raw Material', icon: FlaskConical, stage: 'raw' },
                        { label: 'Store', icon: Warehouse, stage: 'store' },
                        { label: 'Production', icon: Package, stage: 'production' },
                        { label: 'Packaging', icon: Package, stage: 'packaging' },
                        { label: 'Dispatch', icon: Truck, stage: 'dispatch' },
                    ].map((step, idx, arr) => (
                        <div key={step.label} className="flex items-center">
                            <div className="flex flex-col items-center">
                                <div className={`w-14 h-14 rounded-sm flex items-center justify-center stage-${step.stage}`}>
                                    <step.icon size={24} />
                                </div>
                                <p className="text-xs font-medium text-slate-600 mt-2 text-center">{step.label}</p>
                            </div>
                            {idx < arr.length - 1 && (
                                <div className="w-12 md:w-24 h-0.5 bg-slate-200 mx-2"></div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
