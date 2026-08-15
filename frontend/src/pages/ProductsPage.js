import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Search, Edit2, X, Loader2, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const ProductsPage = () => {
    const { api, hasRole } = useAuth();
    const [products, setProducts] = useState([]);
    const [materials, setMaterials] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingProduct, setEditingProduct] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        name: '',
        sku: '',
        category: 'shampoo',
        description: '',
        batch_size: 0,
        unit: 'liters',
        formula: []
    });
    const [newFormula, setNewFormula] = useState({ material_id: '', quantity: 0 });

    const canEdit = hasRole(['admin', 'production_manager']);

    const fetchData = useCallback(async () => {
        try {
            const [prodRes, matRes] = await Promise.all([
                api().get('/products'),
                api().get('/materials?category=chemical')
            ]);
            setProducts(prodRes.data);
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
        setSaving(true);
        try {
            if (editingProduct) {
                await api().put(`/products/${editingProduct.id}`, form);
                toast.success('Product updated');
            } else {
                await api().post('/products', form);
                toast.success('Product created');
            }
            setShowModal(false);
            setEditingProduct(null);
            resetForm();
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Operation failed');
        }
        setSaving(false);
    };

    const addFormulaMaterial = () => {
        if (!newFormula.material_id || newFormula.quantity <= 0) {
            toast.error('Select material and enter quantity');
            return;
        }
        const material = materials.find(m => m.id === newFormula.material_id);
        setForm({
            ...form,
            formula: [...form.formula, {
                material_id: newFormula.material_id,
                material_name: material.name,
                quantity: newFormula.quantity
            }]
        });
        setNewFormula({ material_id: '', quantity: 0 });
    };

    const removeFormulaMaterial = (index) => {
        setForm({ ...form, formula: form.formula.filter((_, i) => i !== index) });
    };

    const resetForm = () => {
        setForm({ name: '', sku: '', category: 'shampoo', description: '', batch_size: 0, unit: 'liters', formula: [] });
        setNewFormula({ material_id: '', quantity: 0 });
    };

    const openEdit = (product) => {
        setEditingProduct(product);
        setForm({
            name: product.name,
            sku: product.sku,
            category: product.category,
            description: product.description || '',
            batch_size: product.batch_size,
            unit: product.unit,
            formula: product.formula || []
        });
        setShowModal(true);
    };

    const getCategoryBadge = (category) => {
        const badges = {
            shampoo: 'bg-blue-100 text-blue-700',
            facewash: 'bg-green-100 text-green-700',
            serum: 'bg-purple-100 text-purple-700',
            moisturizer: 'bg-amber-100 text-amber-700'
        };
        return badges[category] || 'bg-slate-100 text-slate-600';
    };

    const filteredProducts = products.filter(p => 
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.sku.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6" data-testid="products-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">PRODUCTS</h1>
                    <p className="text-slate-500 text-sm mt-1">Manage product catalog and formulas</p>
                </div>
                {canEdit && (
                    <button 
                        onClick={() => { setShowModal(true); setEditingProduct(null); resetForm(); }}
                        className="btn-primary flex items-center gap-2"
                        data-testid="add-product-btn"
                    >
                        <Plus size={16} /> Add Product
                    </button>
                )}
            </div>

            {/* Search */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                    type="text"
                    placeholder="Search products..."
                    className="input-default pl-10"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    data-testid="search-products"
                />
            </div>

            {/* Products Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {loading ? (
                    <div className="col-span-full flex items-center justify-center p-12">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                ) : filteredProducts.length === 0 ? (
                    <div className="col-span-full text-center p-12 text-slate-500 card-default">
                        No products found. Add your first product to get started.
                    </div>
                ) : (
                    filteredProducts.map((product) => (
                        <div key={product.id} className="card-default p-5" data-testid={`product-card-${product.id}`}>
                            <div className="flex items-start justify-between mb-3">
                                <div>
                                    <p className="font-medium text-slate-900">{product.name}</p>
                                    <p className="font-mono text-xs text-slate-500">{product.sku}</p>
                                </div>
                                <span className={`status-badge ${getCategoryBadge(product.category)}`}>
                                    {product.category}
                                </span>
                            </div>
                            {product.description && (
                                <p className="text-sm text-slate-600 mb-3 line-clamp-2">{product.description}</p>
                            )}
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-slate-500">Batch Size:</span>
                                <span className="font-mono">{product.batch_size} {product.unit}</span>
                            </div>
                            {canEdit && (
                                <div className="flex gap-2 mt-4 pt-4 border-t border-slate-100">
                                    <button 
                                        onClick={() => openEdit(product)}
                                        className="btn-secondary flex-1 text-xs py-2 h-auto"
                                        data-testid={`edit-product-${product.id}`}
                                    >
                                        <Edit2 size={14} className="mr-1" /> Edit
                                    </button>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="product-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <h3 className="font-heading font-semibold text-lg">
                                {editingProduct ? 'Edit Product' : 'Add Product'}
                            </h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-4 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Product Name</label>
                                    <input
                                        type="text"
                                        className="input-default"
                                        value={form.name}
                                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                                        required
                                        data-testid="product-name-input"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">SKU</label>
                                    <input
                                        type="text"
                                        className="input-default font-mono"
                                        value={form.sku}
                                        onChange={(e) => setForm({ ...form, sku: e.target.value.toUpperCase() })}
                                        required
                                        data-testid="product-sku-input"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Category</label>
                                    <select
                                        className="input-default"
                                        value={form.category}
                                        onChange={(e) => setForm({ ...form, category: e.target.value })}
                                        data-testid="product-category-select"
                                    >
                                        <option value="shampoo">Shampoo</option>
                                        <option value="facewash">Facewash</option>
                                        <option value="serum">Serum</option>
                                        <option value="moisturizer">Moisturizer</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Batch Size</label>
                                    <input
                                        type="number"
                                        className="input-default font-mono"
                                        value={form.batch_size || ''}
                                        onChange={(e) => setForm({ ...form, batch_size: parseFloat(e.target.value) || 0 })}
                                        required
                                        data-testid="product-batch-size-input"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Unit</label>
                                    <select
                                        className="input-default"
                                        value={form.unit}
                                        onChange={(e) => setForm({ ...form, unit: e.target.value })}
                                        data-testid="product-unit-select"
                                    >
                                        <option value="liters">Liters</option>
                                        <option value="kg">Kilograms</option>
                                    </select>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Description (Optional)</label>
                                <textarea
                                    className="input-default min-h-[60px]"
                                    value={form.description}
                                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                                    data-testid="product-description-input"
                                />
                            </div>

                            {/* Formula Section */}
                            <div className="border border-slate-200 rounded-sm p-4">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">Formula (Optional)</h4>
                                
                                <div className="flex gap-2 mb-4">
                                    <select
                                        className="input-default flex-1"
                                        value={newFormula.material_id}
                                        onChange={(e) => setNewFormula({ ...newFormula, material_id: e.target.value })}
                                        data-testid="formula-material-select"
                                    >
                                        <option value="">Select Chemical</option>
                                        {materials.map(m => (
                                            <option key={m.id} value={m.id}>{m.name}</option>
                                        ))}
                                    </select>
                                    <input
                                        type="number"
                                        step="0.01"
                                        className="input-default w-28 font-mono"
                                        placeholder="Qty"
                                        value={newFormula.quantity || ''}
                                        onChange={(e) => setNewFormula({ ...newFormula, quantity: parseFloat(e.target.value) || 0 })}
                                        data-testid="formula-qty-input"
                                    />
                                    <button type="button" onClick={addFormulaMaterial} className="btn-secondary px-4">
                                        <Plus size={16} />
                                    </button>
                                </div>

                                {form.formula.length > 0 && (
                                    <div className="space-y-2">
                                        {form.formula.map((mat, idx) => (
                                            <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-sm">
                                                <span className="text-sm">{mat.material_name}</span>
                                                <div className="flex items-center gap-3">
                                                    <span className="font-mono text-sm">{mat.quantity}</span>
                                                    <button type="button" onClick={() => removeFormulaMaterial(idx)} className="text-red-500 hover:text-red-700">
                                                        <X size={16} />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2" data-testid="save-product-btn">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    {editingProduct ? 'Update' : 'Create'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProductsPage;
