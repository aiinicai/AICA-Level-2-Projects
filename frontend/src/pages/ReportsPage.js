import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Loader2, Download, Calendar, BarChart3, TrendingDown, Package } from 'lucide-react';
import { toast } from 'sonner';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const ReportsPage = () => {
    const { api } = useAuth();
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('consumption');
    const [dateRange, setDateRange] = useState({
        start: new Date(new Date().setMonth(new Date().getMonth() - 1)).toISOString().split('T')[0],
        end: new Date().toISOString().split('T')[0]
    });
    const [consumptionData, setConsumptionData] = useState([]);
    const [stageData, setStageData] = useState({});
    const [inventoryData, setInventoryData] = useState({ chemicals: { items: [], total_value: 0 }, packing: { items: [], total_value: 0 } });

    const COLORS = ['#7C3AED', '#2563EB', '#D97706', '#E11D48', '#10B981'];

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [consRes, stageRes, invRes] = await Promise.all([
                api().get(`/reports/consumption?start_date=${dateRange.start}&end_date=${dateRange.end}`),
                api().get('/reports/stage-wise'),
                api().get('/reports/inventory-summary')
            ]);
            setConsumptionData(consRes.data);
            setStageData(stageRes.data);
            setInventoryData(invRes.data);
        } catch (err) {
            toast.error('Failed to fetch report data');
        }
        setLoading(false);
    }, [api, dateRange]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const chartConsumptionData = consumptionData.map(item => ({
        name: item.material_name.length > 15 ? item.material_name.substring(0, 15) + '...' : item.material_name,
        quantity: item.total_quantity
    }));

    const stageChartData = Object.entries(stageData).map(([stage, data]) => ({
        name: stage.charAt(0).toUpperCase() + stage.slice(1),
        count: data.count
    }));

    const inventoryPieData = [
        { name: 'Chemicals', value: inventoryData.chemicals.total_value },
        { name: 'Packing', value: inventoryData.packing.total_value }
    ].filter(d => d.value > 0);

    return (
        <div className="space-y-6" data-testid="reports-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">REPORTS</h1>
                    <p className="text-slate-500 text-sm mt-1">Analytics and insights</p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b border-slate-200">
                {[
                    { id: 'consumption', label: 'Material Consumption', icon: TrendingDown },
                    { id: 'stages', label: 'Stage-wise Analysis', icon: BarChart3 },
                    { id: 'inventory', label: 'Inventory Summary', icon: Package }
                ].map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === tab.id 
                                ? 'border-slate-900 text-slate-900' 
                                : 'border-transparent text-slate-500 hover:text-slate-700'
                        }`}
                        data-testid={`report-tab-${tab.id}`}
                    >
                        <tab.icon size={16} />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Date Range Filter (for consumption) */}
            {activeTab === 'consumption' && (
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <Calendar size={18} className="text-slate-400" />
                        <input
                            type="date"
                            className="input-default w-40 font-mono"
                            value={dateRange.start}
                            onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                            data-testid="report-start-date"
                        />
                        <span className="text-slate-400">to</span>
                        <input
                            type="date"
                            className="input-default w-40 font-mono"
                            value={dateRange.end}
                            onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                            data-testid="report-end-date"
                        />
                    </div>
                    <button onClick={fetchData} className="btn-secondary" data-testid="apply-filter-btn">
                        Apply
                    </button>
                </div>
            )}

            {/* Content */}
            {loading ? (
                <div className="flex items-center justify-center p-12">
                    <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                </div>
            ) : (
                <>
                    {/* Consumption Report */}
                    {activeTab === 'consumption' && (
                        <div className="space-y-6">
                            <div className="card-default p-6">
                                <h3 className="font-heading font-semibold text-slate-900 mb-4">Material Consumption</h3>
                                {chartConsumptionData.length === 0 ? (
                                    <div className="text-center py-12 text-slate-500">No consumption data for selected period</div>
                                ) : (
                                    <div className="h-80">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <BarChart data={chartConsumptionData} layout="vertical" margin={{ left: 100 }}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                                <XAxis type="number" stroke="#64748b" fontSize={12} />
                                                <YAxis type="category" dataKey="name" stroke="#64748b" fontSize={12} width={100} />
                                                <Tooltip 
                                                    contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '2px' }}
                                                    labelStyle={{ fontWeight: 600 }}
                                                />
                                                <Bar dataKey="quantity" fill="#7C3AED" radius={[0, 2, 2, 0]} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}
                            </div>

                            {/* Consumption Details Table */}
                            <div className="card-default overflow-hidden">
                                <div className="p-4 border-b border-slate-100">
                                    <h3 className="font-heading font-semibold text-slate-900">Consumption Details</h3>
                                </div>
                                {consumptionData.length === 0 ? (
                                    <div className="text-center py-12 text-slate-500">No data available</div>
                                ) : (
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Material</th>
                                                <th>Total Consumed</th>
                                                <th>Movements</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {consumptionData.map((item, idx) => (
                                                <tr key={idx}>
                                                    <td className="font-medium">{item.material_name}</td>
                                                    <td className="font-mono">{item.total_quantity}</td>
                                                    <td className="font-mono text-slate-500">{item.movements.length}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Stage-wise Report */}
                    {activeTab === 'stages' && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                {Object.entries(stageData).map(([stage, data], idx) => (
                                    <div key={stage} className="card-default p-5" data-testid={`stage-stat-${stage}`}>
                                        <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                                            {stage.charAt(0).toUpperCase() + stage.slice(1)}
                                        </p>
                                        <p className="font-mono text-3xl font-medium" style={{ color: COLORS[idx % COLORS.length] }}>
                                            {data.count}
                                        </p>
                                        <p className="text-xs text-slate-400 mt-1">batches</p>
                                    </div>
                                ))}
                            </div>

                            <div className="card-default p-6">
                                <h3 className="font-heading font-semibold text-slate-900 mb-4">Production Stage Distribution</h3>
                                {stageChartData.length === 0 ? (
                                    <div className="text-center py-12 text-slate-500">No production data available</div>
                                ) : (
                                    <div className="h-80">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <BarChart data={stageChartData}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                                <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                                                <YAxis stroke="#64748b" fontSize={12} />
                                                <Tooltip 
                                                    contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '2px' }}
                                                />
                                                <Bar dataKey="count" fill="#2563EB" radius={[2, 2, 0, 0]} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Inventory Summary */}
                    {activeTab === 'inventory' && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="metric-card">
                                    <p className="metric-label">Chemical Stock Value</p>
                                    <p className="metric-value">₹{inventoryData.chemicals.total_value.toLocaleString()}</p>
                                </div>
                                <div className="metric-card">
                                    <p className="metric-label">Packing Stock Value</p>
                                    <p className="metric-value">₹{inventoryData.packing.total_value.toLocaleString()}</p>
                                </div>
                                <div className="metric-card">
                                    <p className="metric-label">Total Inventory Value</p>
                                    <p className="metric-value">₹{(inventoryData.chemicals.total_value + inventoryData.packing.total_value).toLocaleString()}</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* Pie Chart */}
                                <div className="card-default p-6">
                                    <h3 className="font-heading font-semibold text-slate-900 mb-4">Inventory Distribution</h3>
                                    {inventoryPieData.length === 0 ? (
                                        <div className="text-center py-12 text-slate-500">No inventory data</div>
                                    ) : (
                                        <div className="h-64">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <PieChart>
                                                    <Pie
                                                        data={inventoryPieData}
                                                        cx="50%"
                                                        cy="50%"
                                                        innerRadius={60}
                                                        outerRadius={80}
                                                        paddingAngle={5}
                                                        dataKey="value"
                                                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                                    >
                                                        {inventoryPieData.map((entry, index) => (
                                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                                        ))}
                                                    </Pie>
                                                    <Tooltip 
                                                        formatter={(value) => `₹${value.toLocaleString()}`}
                                                        contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '2px' }}
                                                    />
                                                </PieChart>
                                            </ResponsiveContainer>
                                        </div>
                                    )}
                                </div>

                                {/* Top Items */}
                                <div className="card-default">
                                    <div className="p-4 border-b border-slate-100">
                                        <h3 className="font-heading font-semibold text-slate-900">Top Stock Items by Value</h3>
                                    </div>
                                    <div className="p-4 max-h-64 overflow-y-auto">
                                        {[...inventoryData.chemicals.items, ...inventoryData.packing.items]
                                            .sort((a, b) => b.stock_value - a.stock_value)
                                            .slice(0, 10)
                                            .map((item, idx) => (
                                                <div key={item.id} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
                                                    <div>
                                                        <p className="text-sm font-medium">{item.name}</p>
                                                        <p className="text-xs text-slate-500">{item.current_stock} {item.unit}</p>
                                                    </div>
                                                    <p className="font-mono font-medium">₹{item.stock_value.toLocaleString()}</p>
                                                </div>
                                            ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default ReportsPage;
