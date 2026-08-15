import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Search, Eye, X, Loader2, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

const PackagingPage = () => {
    const { api, hasRole } = useAuth();
    const [records, setRecords] = useState([]);
    const [productionBatches, setProductionBatches] = useState([]);
    const [materials, setMaterials] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [selectedRecord, setSelectedRecord] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        production_batch_id: '',
        packaging_materials: [],
        units_packed: 0,
        unit_size: '100ml',
        start_date: new Date().toISOString().split('T')[0]
    });
    const [newMaterial, setNewMaterial] = useState({ material_id: '', quantity: 0 });

    const canEdit = hasRole(['admin', 'production_manager']);

    const fetchData = useCallback(async () => {
        try {
            const [recRes, batchRes, matRes] = await Promise.all([
                api().get('/packaging-records'),
                api().get('/production-batches?stage=packaging'),
                api().get('/materials?category=packing')
            ]);
            setRecords(recRes.data);
            setProductionBatches(batchRes.data);
            setMaterials(matRes.data);
        } catch (err) {
            toast.error('Failed to fetch data');
        }
        setLoading(false);
    }, [api]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (form.packaging_materials.length === 0) {
            toast.error('Add at least one packaging material');
            return;
        }
        setSaving(true);
        try {
            await api().post('/packaging-records', form);
            toast.success('Packaging record created');
            setShowModal(false);
            resetForm();
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Operation failed');
        }
        setSaving(false);
    };

    const handleComplete = async (recordId) => {
        try {
            await api().put(`/packaging-records/${recordId}`, { 
                status: 'completed',
                end_date: new Date().toISOString().split('T')[0]
            });
            toast.success('Packaging completed');
            fetchData();
        } catch (err) {
            toast.error('Failed to update status');
        }
    };

    const addMaterial = () => {
        if (!newMaterial.material_id || newMaterial.quantity <= 0) {
            toast.error('Select material and enter quantity');
            return;
        }
        const material = materials.find(m => m.id === newMaterial.material_id);
        setForm({
            ...form,
            packaging_materials: [...form.packaging_materials, {
                material_id: newMaterial.material_id,
                material_name: material.name,
                quantity: newMaterial.quantity,
                unit: material.unit
            }]
        });
        setNewMaterial({ material_id: '', quantity: 0 });
    };

    const removeMaterial = (index) => {
        setForm({ ...form, packaging_materials: form.packaging_materials.filter((_, i) => i !== index) });
    };

    const resetForm = () => {
        setForm({
            production_batch_id: '',
            packaging_materials: [],
            units_packed: 0,
            unit_size: '100ml',
            start_date: new Date().toISOString().split('T')[0]
        });
        setNewMaterial({ material_id: '', quantity: 0 });
    };

    const filteredRecords = records.filter(r =>
        r.batch_number.toLowerCase().includes(search.toLowerCase()) || 
        r.product_name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6" data-testid="packaging-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">PACKAGING</h1>
                    <p className="text-slate-500 text-sm mt-1">Track packaging of finished products</p>
                </div>
                {canEdit && (
                    <button 
                        onClick={() => { setShowModal(true); resetForm(); }}
                        className="btn-primary flex items-center gap-2"
                        data-testid="create-packaging-btn"
                    >
                        <Plus size={16} /> New Packaging
                    </button>
                )}
            </div>

            {/* Search */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                    type="text"
                    placeholder="Search packaging records..."
                    className="input-default pl-10"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    data-testid="search-packaging"
                />
            </div>

            {/* Table */}
            <div className="card-default overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center p-12">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                ) : filteredRecords.length === 0 ? (
                    <div className="text-center p-12 text-slate-500">
                        No packaging records found.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Batch #</th>
                                    <th>Product</th>
                                    <th>Units Packed</th>
                                    <th>Unit Size</th>
                                    <th>Status</th>
                                    <th>Start Date</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredRecords.map((record) => (
                                    <tr key={record.id} data-testid={`packaging-row-${record.id}`}>
                                        <td className="font-mono font-medium">{record.batch_number}</td>
                                        <td>{record.product_name}</td>
                                        <td className="font-mono">{record.units_packed}</td>
                                        <td className="font-mono">{record.unit_size}</td>
                                        <td>
                                            <span className={`status-badge ${record.status === 'completed' ? 'status-completed' : 'status-processing'}`}>
                                                {record.status.replace('_', ' ')}
                                            </span>
                                        </td>
                                        <td className="font-mono text-sm">{record.start_date}</td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <button 
                                                    onClick={() => { setSelectedRecord(record); setShowDetailModal(true); }}
                                                    className="p-2 text-slate-400 hover:text-blue-600 transition-colors"
                                                    data-testid={`view-packaging-${record.id}`}
                                                >
                                                    <Eye size={16} />
                                                </button>
                                                {canEdit && record.status === 'in_progress' && (
                                                    <button 
                                                        onClick={() => handleComplete(record.id)}
                                                        className="p-2 text-slate-400 hover:text-green-600 transition-colors"
                                                        title="Mark Complete"
                                                        data-testid={`complete-packaging-${record.id}`}
                                                    >
                                                        <CheckCircle size={16} />
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Create Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="packaging-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <h3 className="font-heading font-semibold text-lg">Create Packaging Record</h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-4 space-y-4">
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Production Batch</label>
                                <select
                                    className="input-default"
                                    value={form.production_batch_id}
                                    onChange={(e) => setForm({ ...form, production_batch_id: e.target.value })}
                                    required
                                    data-testid="packaging-batch-select"
                                >
                                    <option value="">-- Select Batch --</option>
                                    {productionBatches.map(b => (
                                        <option key={b.id} value={b.id}>{b.batch_number} - {b.product_name}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Units to Pack</label>
                                    <input
                                        type="number"
                                        className="input-default font-mono"
                                        value={form.units_packed || ''}
                                        onChange={(e) => setForm({ ...form, units_packed: parseInt(e.target.value) || 0 })}
                                        required
                                        data-testid="packaging-units"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Unit Size</label>
                                    <select
                                        className="input-default"
                                        value={form.unit_size}
                                        onChange={(e) => setForm({ ...form, unit_size: e.target.value })}
                                        data-testid="packaging-unit-size"
                                    >
                                        <option value="50ml">50ml</option>
                                        <option value="100ml">100ml</option>
                                        <option value="200ml">200ml</option>
                                        <option value="250ml">250ml</option>
                                        <option value="500ml">500ml</option>
                                        <option value="1L">1L</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Start Date</label>
                                    <input
                                        type="date"
                                        className="input-default font-mono"
                                        value={form.start_date}
                                        onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                                        required
                                        data-testid="packaging-start-date"
                                    />
                                </div>
                            </div>

                            {/* Packaging Materials */}
                            <div className="border border-slate-200 rounded-sm p-4">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">Packaging Materials Used</h4>
                                
                                <div className="flex gap-2 mb-4">
                                    <select
                                        className="input-default flex-1"
                                        value={newMaterial.material_id}
                                        onChange={(e) => setNewMaterial({ ...newMaterial, material_id: e.target.value })}
                                        data-testid="packaging-material-select"
                                    >
                                        <option value="">Select Material</option>
                                        {materials.map(m => (
                                            <option key={m.id} value={m.id}>{m.name} (Stock: {m.current_stock})</option>
                                        ))}
                                    </select>
                                    <input
                                        type="number"
                                        className="input-default w-28 font-mono"
                                        placeholder="Qty"
                                        value={newMaterial.quantity || ''}
                                        onChange={(e) => setNewMaterial({ ...newMaterial, quantity: parseInt(e.target.value) || 0 })}
                                        data-testid="packaging-material-qty"
                                    />
                                    <button type="button" onClick={addMaterial} className="btn-secondary px-4">
                                        <Plus size={16} />
                                    </button>
                                </div>

                                {form.packaging_materials.length > 0 && (
                                    <div className="space-y-2">
                                        {form.packaging_materials.map((mat, idx) => (
                                            <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-sm">
                                                <div>
                                                    <p className="text-sm font-medium">{mat.material_name}</p>
                                                    <p className="text-xs text-slate-500">{mat.quantity} {mat.unit}</p>
                                                </div>
                                                <button type="button" onClick={() => removeMaterial(idx)} className="text-red-500 hover:text-red-700">
                                                    <X size={16} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2" data-testid="save-packaging-btn">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    Create Record
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
            {showDetailModal && selectedRecord && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="packaging-detail-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <div>
                                <h3 className="font-heading font-semibold text-lg">{selectedRecord.batch_number}</h3>
                                <p className="text-sm text-slate-500">{selectedRecord.product_name}</p>
                            </div>
                            <button onClick={() => setShowDetailModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-4 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Units Packed</p>
                                    <p className="font-mono text-lg font-medium">{selectedRecord.units_packed}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Unit Size</p>
                                    <p className="font-mono">{selectedRecord.unit_size}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Status</p>
                                    <span className={`status-badge ${selectedRecord.status === 'completed' ? 'status-completed' : 'status-processing'}`}>
                                        {selectedRecord.status.replace('_', ' ')}
                                    </span>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Start Date</p>
                                    <p className="font-mono">{selectedRecord.start_date}</p>
                                </div>
                            </div>

                            <div>
                                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Packaging Materials</p>
                                <div className="border border-slate-200 rounded-sm overflow-hidden">
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Material</th>
                                                <th>Quantity</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {selectedRecord.packaging_materials.map((mat, idx) => (
                                                <tr key={idx}>
                                                    <td>{mat.material_name}</td>
                                                    <td className="font-mono">{mat.quantity}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PackagingPage;
