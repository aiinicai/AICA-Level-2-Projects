import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Search, Edit2, Trash2, X, Loader2, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

const MaterialsPage = () => {
    const { api, hasRole } = useAuth();
    const [materials, setMaterials] = useState([]);
    const [suppliers, setSuppliers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('all');
    const [showModal, setShowModal] = useState(false);
    const [editingMaterial, setEditingMaterial] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        name: '',
        sku: '',
        category: 'chemical',
        unit: 'kg',
        min_stock_level: 0,
        max_stock_level: 0,
        unit_price: 0,
        supplier_id: ''
    });

    const canEdit = hasRole(['admin', 'store_keeper']);

    const fetchData = useCallback(async () => {
        try {
            const [matRes, supRes] = await Promise.all([
                api().get('/materials'),
                api().get('/suppliers')
            ]);
            setMaterials(matRes.data);
            setSuppliers(supRes.data);
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
        setSaving(true);
        try {
            const payload = { ...form };
            if (!payload.supplier_id) delete payload.supplier_id;
            
            if (editingMaterial) {
                await api().put(`/materials/${editingMaterial.id}`, payload);
                toast.success('Material updated');
            } else {
                await api().post('/materials', payload);
                toast.success('Material created');
            }
            setShowModal(false);
            setEditingMaterial(null);
            resetForm();
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Operation failed');
        }
        setSaving(false);
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Delete this material?')) return;
        try {
            await api().delete(`/materials/${id}`);
            toast.success('Material deleted');
            fetchData();
        } catch (err) {
            toast.error('Failed to delete material');
        }
    };

    const resetForm = () => {
        setForm({ name: '', sku: '', category: 'chemical', unit: 'kg', min_stock_level: 0, max_stock_level: 0, unit_price: 0, supplier_id: '' });
    };

    const openEdit = (material) => {
        setEditingMaterial(material);
        setForm({
            name: material.name,
            sku: material.sku,
            category: material.category,
            unit: material.unit,
            min_stock_level: material.min_stock_level,
            max_stock_level: material.max_stock_level,
            unit_price: material.unit_price,
            supplier_id: material.supplier_id || ''
        });
        setShowModal(true);
    };

    const getStockStatus = (material) => {
        if (material.current_stock <= 0) return 'critical';
        if (material.current_stock < material.min_stock_level) return 'low';
        return 'ok';
    };

    const filteredMaterials = materials.filter(m => {
        const matchesSearch = m.name.toLowerCase().includes(search.toLowerCase()) || m.sku.toLowerCase().includes(search.toLowerCase());
        const matchesCategory = categoryFilter === 'all' || m.category === categoryFilter;
        return matchesSearch && matchesCategory;
    });

    return (
        <div className="space-y-6" data-testid="materials-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">RAW MATERIALS</h1>
                    <p className="text-slate-500 text-sm mt-1">Manage chemicals and packing materials</p>
                </div>
                {canEdit && (
                    <button 
                        onClick={() => { setShowModal(true); setEditingMaterial(null); resetForm(); }}
                        className="btn-primary flex items-center gap-2"
                        data-testid="add-material-btn"
                    >
                        <Plus size={16} /> Add Material
                    </button>
                )}
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search materials..."
                        className="input-default pl-10"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        data-testid="search-materials"
                    />
                </div>
                <div className="flex gap-2">
                    {['all', 'chemical', 'packing'].map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setCategoryFilter(cat)}
                            className={`px-4 py-2 text-xs font-bold uppercase tracking-wider rounded-sm transition-colors ${
                                categoryFilter === cat 
                                    ? 'bg-slate-900 text-white' 
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                            data-testid={`filter-${cat}`}
                        >
                            {cat === 'all' ? 'All' : cat}
                        </button>
                    ))}
                </div>
            </div>

            {/* Table */}
            <div className="card-default overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center p-12">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                ) : filteredMaterials.length === 0 ? (
                    <div className="text-center p-12 text-slate-500">
                        No materials found. Add your first material to get started.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>SKU</th>
                                    <th>Name</th>
                                    <th>Category</th>
                                    <th>Current Stock</th>
                                    <th>Min Level</th>
                                    <th>Unit Price</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredMaterials.map((material) => {
                                    const status = getStockStatus(material);
                                    return (
                                        <tr key={material.id} data-testid={`material-row-${material.id}`}>
                                            <td className="font-mono text-sm text-slate-600">{material.sku}</td>
                                            <td className="font-medium text-slate-900">{material.name}</td>
                                            <td>
                                                <span className={`status-badge ${material.category === 'chemical' ? 'stage-raw' : 'stage-packaging'}`}>
                                                    {material.category}
                                                </span>
                                            </td>
                                            <td className="font-mono">
                                                <span className={`font-medium ${
                                                    status === 'critical' ? 'text-red-600' : 
                                                    status === 'low' ? 'text-amber-600' : 'text-slate-900'
                                                }`}>
                                                    {material.current_stock}
                                                </span>
                                                <span className="text-slate-400 ml-1">{material.unit}</span>
                                            </td>
                                            <td className="font-mono text-slate-600">{material.min_stock_level} {material.unit}</td>
                                            <td className="font-mono">₹{material.unit_price.toFixed(2)}</td>
                                            <td>
                                                {status === 'ok' ? (
                                                    <span className="flex items-center gap-1 text-green-600 text-sm">
                                                        <CheckCircle2 size={14} /> OK
                                                    </span>
                                                ) : (
                                                    <span className={`flex items-center gap-1 text-sm ${status === 'critical' ? 'text-red-600' : 'text-amber-600'}`}>
                                                        <AlertTriangle size={14} /> {status === 'critical' ? 'Critical' : 'Low'}
                                                    </span>
                                                )}
                                            </td>
                                            <td>
                                                {canEdit && (
                                                    <div className="flex items-center gap-2">
                                                        <button 
                                                            onClick={() => openEdit(material)}
                                                            className="p-2 text-slate-400 hover:text-blue-600 transition-colors"
                                                            data-testid={`edit-material-${material.id}`}
                                                        >
                                                            <Edit2 size={16} />
                                                        </button>
                                                        {hasRole('admin') && (
                                                            <button 
                                                                onClick={() => handleDelete(material.id)}
                                                                className="p-2 text-slate-400 hover:text-red-600 transition-colors"
                                                                data-testid={`delete-material-${material.id}`}
                                                            >
                                                                <Trash2 size={16} />
                                                            </button>
                                                        )}
                                                    </div>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="material-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <h3 className="font-heading font-semibold text-lg">
                                {editingMaterial ? 'Edit Material' : 'Add Material'}
                            </h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-4 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">SKU</label>
                                    <input
                                        type="text"
                                        className="input-default font-mono"
                                        value={form.sku}
                                        onChange={(e) => setForm({ ...form, sku: e.target.value.toUpperCase() })}
                                        placeholder="MAT-001"
                                        required
                                        data-testid="material-sku-input"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Category</label>
                                    <select
                                        className="input-default"
                                        value={form.category}
                                        onChange={(e) => setForm({ ...form, category: e.target.value })}
                                        data-testid="material-category-select"
                                    >
                                        <option value="chemical">Chemical</option>
                                        <option value="packing">Packing Material</option>
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Material Name</label>
                                <input
                                    type="text"
                                    className="input-default"
                                    value={form.name}
                                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    required
                                    data-testid="material-name-input"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Unit</label>
                                    <select
                                        className="input-default"
                                        value={form.unit}
                                        onChange={(e) => setForm({ ...form, unit: e.target.value })}
                                        data-testid="material-unit-select"
                                    >
                                        <option value="kg">Kilograms (kg)</option>
                                        <option value="liters">Liters (L)</option>
                                        <option value="pieces">Pieces</option>
                                        <option value="grams">Grams (g)</option>
                                        <option value="ml">Milliliters (ml)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Unit Price (₹)</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        className="input-default font-mono"
                                        value={form.unit_price}
                                        onChange={(e) => setForm({ ...form, unit_price: parseFloat(e.target.value) || 0 })}
                                        required
                                        data-testid="material-price-input"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Min Stock Level</label>
                                    <input
                                        type="number"
                                        className="input-default font-mono"
                                        value={form.min_stock_level}
                                        onChange={(e) => setForm({ ...form, min_stock_level: parseFloat(e.target.value) || 0 })}
                                        required
                                        data-testid="material-min-stock-input"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Max Stock Level</label>
                                    <input
                                        type="number"
                                        className="input-default font-mono"
                                        value={form.max_stock_level}
                                        onChange={(e) => setForm({ ...form, max_stock_level: parseFloat(e.target.value) || 0 })}
                                        required
                                        data-testid="material-max-stock-input"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Preferred Supplier (Optional)</label>
                                <select
                                    className="input-default"
                                    value={form.supplier_id}
                                    onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
                                    data-testid="material-supplier-select"
                                >
                                    <option value="">-- Select Supplier --</option>
                                    {suppliers.filter(s => s.material_type === form.category || form.category === 'chemical' && s.material_type === 'chemicals').map(s => (
                                        <option key={s.id} value={s.id}>{s.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2" data-testid="save-material-btn">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingMaterial ? 'Update' : 'Create'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MaterialsPage;
