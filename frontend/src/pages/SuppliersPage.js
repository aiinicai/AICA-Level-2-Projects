import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Search, Edit2, Trash2, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const SuppliersPage = () => {
    const { api, hasRole } = useAuth();
    const [suppliers, setSuppliers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingSupplier, setEditingSupplier] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        name: '',
        contact_person: '',
        phone: '',
        email: '',
        address: '',
        material_type: 'chemicals'
    });

    const canEdit = hasRole(['admin', 'store_keeper']);

    const fetchSuppliers = useCallback(async () => {
        try {
            const res = await api().get('/suppliers');
            setSuppliers(res.data);
        } catch (err) {
            toast.error('Failed to fetch suppliers');
        }
        setLoading(false);
    }, [api]);

    useEffect(() => {
        fetchSuppliers();
    }, [fetchSuppliers]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            if (editingSupplier) {
                await api().put(`/suppliers/${editingSupplier.id}`, form);
                toast.success('Supplier updated');
            } else {
                await api().post('/suppliers', form);
                toast.success('Supplier created');
            }
            setShowModal(false);
            setEditingSupplier(null);
            setForm({ name: '', contact_person: '', phone: '', email: '', address: '', material_type: 'chemicals' });
            fetchSuppliers();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Operation failed');
        }
        setSaving(false);
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Delete this supplier?')) return;
        try {
            await api().delete(`/suppliers/${id}`);
            toast.success('Supplier deleted');
            fetchSuppliers();
        } catch (err) {
            toast.error('Failed to delete supplier');
        }
    };

    const openEdit = (supplier) => {
        setEditingSupplier(supplier);
        setForm({
            name: supplier.name,
            contact_person: supplier.contact_person,
            phone: supplier.phone,
            email: supplier.email,
            address: supplier.address,
            material_type: supplier.material_type
        });
        setShowModal(true);
    };

    const filteredSuppliers = suppliers.filter(s => 
        s.name.toLowerCase().includes(search.toLowerCase()) ||
        s.contact_person.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6" data-testid="suppliers-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">SUPPLIERS</h1>
                    <p className="text-slate-500 text-sm mt-1">Manage your raw material suppliers</p>
                </div>
                {canEdit && (
                    <button 
                        onClick={() => { setShowModal(true); setEditingSupplier(null); setForm({ name: '', contact_person: '', phone: '', email: '', address: '', material_type: 'chemicals' }); }}
                        className="btn-primary flex items-center gap-2"
                        data-testid="add-supplier-btn"
                    >
                        <Plus size={16} /> Add Supplier
                    </button>
                )}
            </div>

            {/* Search */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                    type="text"
                    placeholder="Search suppliers..."
                    className="input-default pl-10"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    data-testid="search-suppliers"
                />
            </div>

            {/* Table */}
            <div className="card-default overflow-hidden">
                {loading ? (
                    <div className="flex items-center justify-center p-12">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                ) : filteredSuppliers.length === 0 ? (
                    <div className="text-center p-12 text-slate-500">
                        No suppliers found. Add your first supplier to get started.
                    </div>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Contact Person</th>
                                <th>Phone</th>
                                <th>Email</th>
                                <th>Type</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredSuppliers.map((supplier) => (
                                <tr key={supplier.id} data-testid={`supplier-row-${supplier.id}`}>
                                    <td className="font-medium text-slate-900">{supplier.name}</td>
                                    <td>{supplier.contact_person}</td>
                                    <td className="font-mono text-sm">{supplier.phone}</td>
                                    <td className="text-slate-600">{supplier.email}</td>
                                    <td>
                                        <span className={`status-badge ${supplier.material_type === 'chemicals' ? 'stage-raw' : 'stage-packaging'}`}>
                                            {supplier.material_type}
                                        </span>
                                    </td>
                                    <td>
                                        {canEdit && (
                                            <div className="flex items-center gap-2">
                                                <button 
                                                    onClick={() => openEdit(supplier)}
                                                    className="p-2 text-slate-400 hover:text-blue-600 transition-colors"
                                                    data-testid={`edit-supplier-${supplier.id}`}
                                                >
                                                    <Edit2 size={16} />
                                                </button>
                                                {hasRole('admin') && (
                                                    <button 
                                                        onClick={() => handleDelete(supplier.id)}
                                                        className="p-2 text-slate-400 hover:text-red-600 transition-colors"
                                                        data-testid={`delete-supplier-${supplier.id}`}
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="supplier-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <h3 className="font-heading font-semibold text-lg">
                                {editingSupplier ? 'Edit Supplier' : 'Add Supplier'}
                            </h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-4 space-y-4">
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Company Name</label>
                                <input
                                    type="text"
                                    className="input-default"
                                    value={form.name}
                                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    required
                                    data-testid="supplier-name-input"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Contact Person</label>
                                <input
                                    type="text"
                                    className="input-default"
                                    value={form.contact_person}
                                    onChange={(e) => setForm({ ...form, contact_person: e.target.value })}
                                    required
                                    data-testid="supplier-contact-input"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Phone</label>
                                    <input
                                        type="tel"
                                        className="input-default"
                                        value={form.phone}
                                        onChange={(e) => setForm({ ...form, phone: e.target.value })}
                                        required
                                        data-testid="supplier-phone-input"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Email</label>
                                    <input
                                        type="email"
                                        className="input-default"
                                        value={form.email}
                                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                                        required
                                        data-testid="supplier-email-input"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Address</label>
                                <textarea
                                    className="input-default min-h-[80px]"
                                    value={form.address}
                                    onChange={(e) => setForm({ ...form, address: e.target.value })}
                                    required
                                    data-testid="supplier-address-input"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Material Type</label>
                                <select
                                    className="input-default"
                                    value={form.material_type}
                                    onChange={(e) => setForm({ ...form, material_type: e.target.value })}
                                    data-testid="supplier-type-select"
                                >
                                    <option value="chemicals">Chemicals</option>
                                    <option value="packing">Packing Materials</option>
                                </select>
                            </div>
                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2" data-testid="save-supplier-btn">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingSupplier ? 'Update' : 'Create'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SuppliersPage;
