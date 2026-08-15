import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Search, Eye, X, Loader2, Check, Package } from 'lucide-react';
import { toast } from 'sonner';

const PurchaseOrdersPage = () => {
    const { api, hasRole } = useAuth();
    const [orders, setOrders] = useState([]);
    const [suppliers, setSuppliers] = useState([]);
    const [materials, setMaterials] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [showModal, setShowModal] = useState(false);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [selectedOrder, setSelectedOrder] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        supplier_id: '',
        items: [],
        order_date: new Date().toISOString().split('T')[0],
        expected_delivery: '',
        notes: ''
    });
    const [newItem, setNewItem] = useState({ material_id: '', quantity: 0, unit_price: 0 });

    const canEdit = hasRole(['admin', 'store_keeper']);

    const fetchData = useCallback(async () => {
        try {
            const [poRes, supRes, matRes] = await Promise.all([
                api().get('/purchase-orders'),
                api().get('/suppliers'),
                api().get('/materials')
            ]);
            setOrders(poRes.data);
            setSuppliers(supRes.data);
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
        if (form.items.length === 0) {
            toast.error('Add at least one item');
            return;
        }
        setSaving(true);
        try {
            await api().post('/purchase-orders', form);
            toast.success('Purchase order created');
            setShowModal(false);
            resetForm();
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Operation failed');
        }
        setSaving(false);
    };

    const handleStatusUpdate = async (orderId, newStatus) => {
        try {
            await api().put(`/purchase-orders/${orderId}`, { status: newStatus });
            toast.success(`Order ${newStatus}`);
            fetchData();
        } catch (err) {
            toast.error('Failed to update status');
        }
    };

    const handleReceive = async (orderId) => {
        try {
            await api().post(`/purchase-orders/${orderId}/receive`);
            toast.success('Order received and stock updated');
            setShowDetailModal(false);
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to receive order');
        }
    };

    const addItem = () => {
        if (!newItem.material_id || newItem.quantity <= 0) {
            toast.error('Select material and enter quantity');
            return;
        }
        const material = materials.find(m => m.id === newItem.material_id);
        setForm({
            ...form,
            items: [...form.items, {
                material_id: newItem.material_id,
                material_name: material.name,
                quantity: newItem.quantity,
                unit_price: newItem.unit_price || material.unit_price,
                unit: material.unit
            }]
        });
        setNewItem({ material_id: '', quantity: 0, unit_price: 0 });
    };

    const removeItem = (index) => {
        setForm({ ...form, items: form.items.filter((_, i) => i !== index) });
    };

    const resetForm = () => {
        setForm({
            supplier_id: '',
            items: [],
            order_date: new Date().toISOString().split('T')[0],
            expected_delivery: '',
            notes: ''
        });
        setNewItem({ material_id: '', quantity: 0, unit_price: 0 });
    };

    const getStatusBadge = (status) => {
        const badges = {
            pending: 'status-pending',
            approved: 'status-approved',
            received: 'status-received',
            cancelled: 'status-cancelled'
        };
        return badges[status] || 'status-pending';
    };

    const filteredOrders = orders.filter(o => {
        const matchesSearch = o.po_number.toLowerCase().includes(search.toLowerCase()) || o.supplier_name.toLowerCase().includes(search.toLowerCase());
        const matchesStatus = statusFilter === 'all' || o.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    return (
        <div className="space-y-6" data-testid="purchase-orders-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">PURCHASE ORDERS</h1>
                    <p className="text-slate-500 text-sm mt-1">Manage raw material purchase orders</p>
                </div>
                {canEdit && (
                    <button 
                        onClick={() => { setShowModal(true); resetForm(); }}
                        className="btn-primary flex items-center gap-2"
                        data-testid="create-po-btn"
                    >
                        <Plus size={16} /> Create PO
                    </button>
                )}
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search by PO number or supplier..."
                        className="input-default pl-10"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        data-testid="search-po"
                    />
                </div>
                <div className="flex gap-2 flex-wrap">
                    {['all', 'pending', 'approved', 'received', 'cancelled'].map((status) => (
                        <button
                            key={status}
                            onClick={() => setStatusFilter(status)}
                            className={`px-4 py-2 text-xs font-bold uppercase tracking-wider rounded-sm transition-colors ${
                                statusFilter === status 
                                    ? 'bg-slate-900 text-white' 
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                            data-testid={`filter-${status}`}
                        >
                            {status}
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
                ) : filteredOrders.length === 0 ? (
                    <div className="text-center p-12 text-slate-500">
                        No purchase orders found. Create your first PO to get started.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>PO Number</th>
                                    <th>Supplier</th>
                                    <th>Order Date</th>
                                    <th>Expected Delivery</th>
                                    <th>Total Amount</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredOrders.map((order) => (
                                    <tr key={order.id} data-testid={`po-row-${order.id}`}>
                                        <td className="font-mono font-medium text-slate-900">{order.po_number}</td>
                                        <td>{order.supplier_name}</td>
                                        <td className="font-mono text-sm">{order.order_date}</td>
                                        <td className="font-mono text-sm">{order.expected_delivery}</td>
                                        <td className="font-mono font-medium">₹{order.total_amount.toFixed(2)}</td>
                                        <td>
                                            <span className={`status-badge ${getStatusBadge(order.status)}`}>
                                                {order.status}
                                            </span>
                                        </td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <button 
                                                    onClick={() => { setSelectedOrder(order); setShowDetailModal(true); }}
                                                    className="p-2 text-slate-400 hover:text-blue-600 transition-colors"
                                                    data-testid={`view-po-${order.id}`}
                                                >
                                                    <Eye size={16} />
                                                </button>
                                                {canEdit && order.status === 'pending' && (
                                                    <button 
                                                        onClick={() => handleStatusUpdate(order.id, 'approved')}
                                                        className="p-2 text-slate-400 hover:text-green-600 transition-colors"
                                                        title="Approve"
                                                        data-testid={`approve-po-${order.id}`}
                                                    >
                                                        <Check size={16} />
                                                    </button>
                                                )}
                                                {canEdit && order.status === 'approved' && (
                                                    <button 
                                                        onClick={() => handleReceive(order.id)}
                                                        className="p-2 text-slate-400 hover:text-blue-600 transition-colors"
                                                        title="Receive"
                                                        data-testid={`receive-po-${order.id}`}
                                                    >
                                                        <Package size={16} />
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

            {/* Create PO Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="po-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <h3 className="font-heading font-semibold text-lg">Create Purchase Order</h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-4 space-y-4">
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Supplier</label>
                                <select
                                    className="input-default"
                                    value={form.supplier_id}
                                    onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
                                    required
                                    data-testid="po-supplier-select"
                                >
                                    <option value="">-- Select Supplier --</option>
                                    {suppliers.map(s => (
                                        <option key={s.id} value={s.id}>{s.name} ({s.material_type})</option>
                                    ))}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Order Date</label>
                                    <input
                                        type="date"
                                        className="input-default font-mono"
                                        value={form.order_date}
                                        onChange={(e) => setForm({ ...form, order_date: e.target.value })}
                                        required
                                        data-testid="po-order-date"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Expected Delivery</label>
                                    <input
                                        type="date"
                                        className="input-default font-mono"
                                        value={form.expected_delivery}
                                        onChange={(e) => setForm({ ...form, expected_delivery: e.target.value })}
                                        required
                                        data-testid="po-expected-delivery"
                                    />
                                </div>
                            </div>

                            {/* Items Section */}
                            <div className="border border-slate-200 rounded-sm p-4">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">Order Items</h4>
                                
                                {/* Add Item Row */}
                                <div className="flex gap-2 mb-4">
                                    <select
                                        className="input-default flex-1"
                                        value={newItem.material_id}
                                        onChange={(e) => {
                                            const mat = materials.find(m => m.id === e.target.value);
                                            setNewItem({ ...newItem, material_id: e.target.value, unit_price: mat?.unit_price || 0 });
                                        }}
                                        data-testid="po-item-material"
                                    >
                                        <option value="">Select Material</option>
                                        {materials.map(m => (
                                            <option key={m.id} value={m.id}>{m.name} ({m.sku})</option>
                                        ))}
                                    </select>
                                    <input
                                        type="number"
                                        className="input-default w-24 font-mono"
                                        placeholder="Qty"
                                        value={newItem.quantity || ''}
                                        onChange={(e) => setNewItem({ ...newItem, quantity: parseFloat(e.target.value) || 0 })}
                                        data-testid="po-item-qty"
                                    />
                                    <input
                                        type="number"
                                        step="0.01"
                                        className="input-default w-28 font-mono"
                                        placeholder="Price"
                                        value={newItem.unit_price || ''}
                                        onChange={(e) => setNewItem({ ...newItem, unit_price: parseFloat(e.target.value) || 0 })}
                                        data-testid="po-item-price"
                                    />
                                    <button type="button" onClick={addItem} className="btn-secondary px-4" data-testid="add-po-item">
                                        <Plus size={16} />
                                    </button>
                                </div>

                                {/* Items List */}
                                {form.items.length > 0 && (
                                    <div className="space-y-2">
                                        {form.items.map((item, idx) => (
                                            <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-sm">
                                                <div>
                                                    <p className="text-sm font-medium">{item.material_name}</p>
                                                    <p className="text-xs text-slate-500">{item.quantity} {item.unit} × ₹{item.unit_price}</p>
                                                </div>
                                                <div className="flex items-center gap-4">
                                                    <p className="font-mono font-medium">₹{(item.quantity * item.unit_price).toFixed(2)}</p>
                                                    <button type="button" onClick={() => removeItem(idx)} className="text-red-500 hover:text-red-700">
                                                        <X size={16} />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                        <div className="flex justify-end pt-2 border-t border-slate-200">
                                            <p className="font-mono font-bold text-lg">
                                                Total: ₹{form.items.reduce((sum, i) => sum + (i.quantity * i.unit_price), 0).toFixed(2)}
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Notes (Optional)</label>
                                <textarea
                                    className="input-default min-h-[60px]"
                                    value={form.notes}
                                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                                    data-testid="po-notes"
                                />
                            </div>

                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2" data-testid="save-po-btn">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    Create PO
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
            {showDetailModal && selectedOrder && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="po-detail-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <div>
                                <h3 className="font-heading font-semibold text-lg">{selectedOrder.po_number}</h3>
                                <p className="text-sm text-slate-500">{selectedOrder.supplier_name}</p>
                            </div>
                            <button onClick={() => setShowDetailModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-4 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Order Date</p>
                                    <p className="font-mono">{selectedOrder.order_date}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Expected Delivery</p>
                                    <p className="font-mono">{selectedOrder.expected_delivery}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Status</p>
                                    <span className={`status-badge ${getStatusBadge(selectedOrder.status)}`}>
                                        {selectedOrder.status}
                                    </span>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Total Amount</p>
                                    <p className="font-mono font-bold text-lg">₹{selectedOrder.total_amount.toFixed(2)}</p>
                                </div>
                            </div>

                            <div>
                                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Items</p>
                                <div className="border border-slate-200 rounded-sm overflow-hidden">
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Material</th>
                                                <th>Quantity</th>
                                                <th>Unit Price</th>
                                                <th>Total</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {selectedOrder.items.map((item, idx) => (
                                                <tr key={idx}>
                                                    <td>{item.material_name}</td>
                                                    <td className="font-mono">{item.quantity}</td>
                                                    <td className="font-mono">₹{item.unit_price}</td>
                                                    <td className="font-mono font-medium">₹{(item.quantity * item.unit_price).toFixed(2)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {selectedOrder.notes && (
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Notes</p>
                                    <p className="text-sm text-slate-600">{selectedOrder.notes}</p>
                                </div>
                            )}

                            {canEdit && selectedOrder.status === 'approved' && (
                                <div className="pt-4 border-t border-slate-200">
                                    <button 
                                        onClick={() => handleReceive(selectedOrder.id)}
                                        className="btn-primary w-full flex items-center justify-center gap-2"
                                        data-testid="receive-po-detail-btn"
                                    >
                                        <Package size={16} /> Mark as Received
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PurchaseOrdersPage;
