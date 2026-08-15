import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Search, Loader2, ArrowDown, ArrowUp, Filter } from 'lucide-react';
import { toast } from 'sonner';

const StorePage = () => {
    const { api } = useAuth();
    const [materials, setMaterials] = useState([]);
    const [batches, setBatches] = useState([]);
    const [movements, setMovements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [activeTab, setActiveTab] = useState('inventory');

    const fetchData = useCallback(async () => {
        try {
            const [matRes, batchRes, movRes] = await Promise.all([
                api().get('/materials'),
                api().get('/batches'),
                api().get('/stock-movements')
            ]);
            setMaterials(matRes.data);
            setBatches(batchRes.data);
            setMovements(movRes.data);
        } catch (err) {
            toast.error('Failed to fetch data');
        }
        setLoading(false);
    }, [api]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const filteredMaterials = materials.filter(m => 
        m.name.toLowerCase().includes(search.toLowerCase()) || m.sku.toLowerCase().includes(search.toLowerCase())
    );

    const filteredBatches = batches.filter(b =>
        b.material_name.toLowerCase().includes(search.toLowerCase()) || b.batch_number.toLowerCase().includes(search.toLowerCase())
    );

    const filteredMovements = movements.filter(m =>
        m.material_name.toLowerCase().includes(search.toLowerCase())
    );

    const getStockClass = (material) => {
        if (material.current_stock <= 0) return 'text-red-600';
        if (material.current_stock < material.min_stock_level) return 'text-amber-600';
        return 'text-green-600';
    };

    return (
        <div className="space-y-6" data-testid="store-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">STORE INVENTORY</h1>
                    <p className="text-slate-500 text-sm mt-1">Current stock levels, batches, and movements</p>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b border-slate-200">
                {[
                    { id: 'inventory', label: 'Stock Levels' },
                    { id: 'batches', label: 'Batches' },
                    { id: 'movements', label: 'Movements' }
                ].map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                            activeTab === tab.id 
                                ? 'border-slate-900 text-slate-900' 
                                : 'border-transparent text-slate-500 hover:text-slate-700'
                        }`}
                        data-testid={`tab-${tab.id}`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Search */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                    type="text"
                    placeholder="Search..."
                    className="input-default pl-10"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    data-testid="search-store"
                />
            </div>

            {/* Content */}
            <div className="card-default overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center p-12">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                ) : (
                    <>
                        {/* Stock Levels Tab */}
                        {activeTab === 'inventory' && (
                            filteredMaterials.length === 0 ? (
                                <div className="text-center p-12 text-slate-500">No materials found.</div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>SKU</th>
                                                <th>Material</th>
                                                <th>Category</th>
                                                <th>Current Stock</th>
                                                <th>Min Level</th>
                                                <th>Max Level</th>
                                                <th>Stock Value</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredMaterials.map((mat) => (
                                                <tr key={mat.id} data-testid={`stock-row-${mat.id}`}>
                                                    <td className="font-mono text-sm">{mat.sku}</td>
                                                    <td className="font-medium">{mat.name}</td>
                                                    <td>
                                                        <span className={`status-badge ${mat.category === 'chemical' ? 'stage-raw' : 'stage-packaging'}`}>
                                                            {mat.category}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <span className={`font-mono font-medium ${getStockClass(mat)}`}>
                                                            {mat.current_stock} {mat.unit}
                                                        </span>
                                                    </td>
                                                    <td className="font-mono text-slate-500">{mat.min_stock_level}</td>
                                                    <td className="font-mono text-slate-500">{mat.max_stock_level}</td>
                                                    <td className="font-mono font-medium">₹{(mat.current_stock * mat.unit_price).toFixed(2)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )
                        )}

                        {/* Batches Tab */}
                        {activeTab === 'batches' && (
                            filteredBatches.length === 0 ? (
                                <div className="text-center p-12 text-slate-500">No batches found.</div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Batch Number</th>
                                                <th>Material</th>
                                                <th>Quantity</th>
                                                <th>Mfg Date</th>
                                                <th>Expiry Date</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredBatches.map((batch) => (
                                                <tr key={batch.id} data-testid={`batch-row-${batch.id}`}>
                                                    <td className="font-mono font-medium">{batch.batch_number}</td>
                                                    <td>{batch.material_name}</td>
                                                    <td className="font-mono">{batch.quantity}</td>
                                                    <td className="font-mono text-sm">{batch.manufacturing_date}</td>
                                                    <td className="font-mono text-sm">{batch.expiry_date}</td>
                                                    <td>
                                                        <span className={`status-badge ${
                                                            batch.status === 'in_stock' ? 'status-approved' :
                                                            batch.status === 'issued' ? 'status-issued' :
                                                            batch.status === 'consumed' ? 'status-received' :
                                                            'status-cancelled'
                                                        }`}>
                                                            {batch.status.replace('_', ' ')}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )
                        )}

                        {/* Movements Tab */}
                        {activeTab === 'movements' && (
                            filteredMovements.length === 0 ? (
                                <div className="text-center p-12 text-slate-500">No stock movements found.</div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Date</th>
                                                <th>Type</th>
                                                <th>Material</th>
                                                <th>Quantity</th>
                                                <th>Reference</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {filteredMovements.map((mov) => (
                                                <tr key={mov.id} data-testid={`movement-row-${mov.id}`}>
                                                    <td className="font-mono text-sm">{new Date(mov.created_at).toLocaleString()}</td>
                                                    <td>
                                                        <span className={`flex items-center gap-1 ${mov.movement_type === 'in' ? 'text-green-600' : 'text-red-600'}`}>
                                                            {mov.movement_type === 'in' ? <ArrowDown size={14} /> : <ArrowUp size={14} />}
                                                            {mov.movement_type.toUpperCase()}
                                                        </span>
                                                    </td>
                                                    <td className="font-medium">{mov.material_name}</td>
                                                    <td className="font-mono">{mov.quantity}</td>
                                                    <td className="text-sm text-slate-500">
                                                        {mov.reference_type.replace('_', ' ')}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

export default StorePage;
