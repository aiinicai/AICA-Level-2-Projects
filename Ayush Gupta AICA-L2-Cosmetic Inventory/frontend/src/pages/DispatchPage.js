import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Search, Eye, X, Loader2, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

const DispatchPage = () => {
    const { api, hasRole } = useAuth();
    const [records, setRecords] = useState([]);
    const [packagingRecords, setPackagingRecords] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [selectedRecord, setSelectedRecord] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        packaging_record_id: '',
        quantity_dispatched: 0,
        destination: '',
        dispatch_date: new Date().toISOString().split('T')[0],
        vehicle_number: '',
        driver_name: '',
        notes: ''
    });

    const canEdit = hasRole(['admin', 'store_keeper']);

    const fetchData = useCallback(async () => {
        try {
            const [dispRes, pkgRes] = await Promise.all([
                api().get('/dispatch-records'),
                api().get('/packaging-records?status=completed')
            ]);
            setRecords(dispRes.data);
            setPackagingRecords(pkgRes.data);
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
            await api().post('/dispatch-records', form);
            toast.success('Dispatch record created');
            setShowModal(false);
            resetForm();
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Operation failed');
        }
        setSaving(false);
    };

    const handleMarkDelivered = async (recordId) => {
        try {
            await api().put(`/dispatch-records/${recordId}`, { 
                status: 'delivered',
                delivered_date: new Date().toISOString().split('T')[0]
            });
            toast.success('Marked as delivered');
            fetchData();
        } catch (err) {
            toast.error('Failed to update status');
        }
    };

    const resetForm = () => {
        setForm({
            packaging_record_id: '',
            quantity_dispatched: 0,
            destination: '',
            dispatch_date: new Date().toISOString().split('T')[0],
            vehicle_number: '',
            driver_name: '',
            notes: ''
        });
    };

    const filteredRecords = records.filter(r =>
        r.dispatch_number.toLowerCase().includes(search.toLowerCase()) || 
        r.product_name.toLowerCase().includes(search.toLowerCase()) ||
        r.destination.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6" data-testid="dispatch-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">DISPATCH</h1>
                    <p className="text-slate-500 text-sm mt-1">Track product dispatches and deliveries</p>
                </div>
                {canEdit && (
                    <button 
                        onClick={() => { setShowModal(true); resetForm(); }}
                        className="btn-primary flex items-center gap-2"
                        data-testid="create-dispatch-btn"
                    >
                        <Plus size={16} /> New Dispatch
                    </button>
                )}
            </div>

            {/* Search */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input
                    type="text"
                    placeholder="Search dispatches..."
                    className="input-default pl-10"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    data-testid="search-dispatch"
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
                        No dispatch records found.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Dispatch #</th>
                                    <th>Product</th>
                                    <th>Batch #</th>
                                    <th>Quantity</th>
                                    <th>Destination</th>
                                    <th>Dispatch Date</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredRecords.map((record) => (
                                    <tr key={record.id} data-testid={`dispatch-row-${record.id}`}>
                                        <td className="font-mono font-medium">{record.dispatch_number}</td>
                                        <td>{record.product_name}</td>
                                        <td className="font-mono text-sm">{record.batch_number}</td>
                                        <td className="font-mono">{record.quantity_dispatched}</td>
                                        <td>{record.destination}</td>
                                        <td className="font-mono text-sm">{record.dispatch_date}</td>
                                        <td>
                                            <span className={`status-badge ${record.status === 'delivered' ? 'status-completed' : 'status-dispatched'}`}>
                                                {record.status}
                                            </span>
                                        </td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <button 
                                                    onClick={() => { setSelectedRecord(record); setShowDetailModal(true); }}
                                                    className="p-2 text-slate-400 hover:text-blue-600 transition-colors"
                                                    data-testid={`view-dispatch-${record.id}`}
                                                >
                                                    <Eye size={16} />
                                                </button>
                                                {canEdit && record.status === 'dispatched' && (
                                                    <button 
                                                        onClick={() => handleMarkDelivered(record.id)}
                                                        className="p-2 text-slate-400 hover:text-green-600 transition-colors"
                                                        title="Mark Delivered"
                                                        data-testid={`deliver-dispatch-${record.id}`}
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
                    <div className="bg-white rounded-sm w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="dispatch-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <h3 className="font-heading font-semibold text-lg">Create Dispatch</h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-4 space-y-4">
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Packaging Record</label>
                                <select
                                    className="input-default"
                                    value={form.packaging_record_id}
                                    onChange={(e) => {
                                        const pkg = packagingRecords.find(p => p.id === e.target.value);
                                        setForm({ 
                                            ...form, 
                                            packaging_record_id: e.target.value,
                                            quantity_dispatched: pkg?.units_packed || 0
                                        });
                                    }}
                                    required
                                    data-testid="dispatch-packaging-select"
                                >
                                    <option value="">-- Select Packaged Batch --</option>
                                    {packagingRecords.map(p => (
                                        <option key={p.id} value={p.id}>{p.batch_number} - {p.product_name} ({p.units_packed} units)</option>
                                    ))}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Quantity</label>
                                    <input
                                        type="number"
                                        className="input-default font-mono"
                                        value={form.quantity_dispatched || ''}
                                        onChange={(e) => setForm({ ...form, quantity_dispatched: parseInt(e.target.value) || 0 })}
                                        required
                                        data-testid="dispatch-quantity"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Dispatch Date</label>
                                    <input
                                        type="date"
                                        className="input-default font-mono"
                                        value={form.dispatch_date}
                                        onChange={(e) => setForm({ ...form, dispatch_date: e.target.value })}
                                        required
                                        data-testid="dispatch-date"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Destination</label>
                                <input
                                    type="text"
                                    className="input-default"
                                    value={form.destination}
                                    onChange={(e) => setForm({ ...form, destination: e.target.value })}
                                    placeholder="Warehouse / Distributor address"
                                    required
                                    data-testid="dispatch-destination"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Vehicle Number</label>
                                    <input
                                        type="text"
                                        className="input-default font-mono"
                                        value={form.vehicle_number}
                                        onChange={(e) => setForm({ ...form, vehicle_number: e.target.value.toUpperCase() })}
                                        placeholder="MH12AB1234"
                                        data-testid="dispatch-vehicle"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Driver Name</label>
                                    <input
                                        type="text"
                                        className="input-default"
                                        value={form.driver_name}
                                        onChange={(e) => setForm({ ...form, driver_name: e.target.value })}
                                        data-testid="dispatch-driver"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Notes (Optional)</label>
                                <textarea
                                    className="input-default min-h-[60px]"
                                    value={form.notes}
                                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                                    data-testid="dispatch-notes"
                                />
                            </div>

                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2" data-testid="save-dispatch-btn">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    Create Dispatch
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
            {showDetailModal && selectedRecord && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="dispatch-detail-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <div>
                                <h3 className="font-heading font-semibold text-lg">{selectedRecord.dispatch_number}</h3>
                                <p className="text-sm text-slate-500">{selectedRecord.product_name}</p>
                            </div>
                            <button onClick={() => setShowDetailModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-4 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Batch Number</p>
                                    <p className="font-mono">{selectedRecord.batch_number}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Quantity</p>
                                    <p className="font-mono text-lg font-medium">{selectedRecord.quantity_dispatched}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Status</p>
                                    <span className={`status-badge ${selectedRecord.status === 'delivered' ? 'status-completed' : 'status-dispatched'}`}>
                                        {selectedRecord.status}
                                    </span>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Dispatch Date</p>
                                    <p className="font-mono">{selectedRecord.dispatch_date}</p>
                                </div>
                            </div>
                            <div>
                                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Destination</p>
                                <p className="text-sm">{selectedRecord.destination}</p>
                            </div>
                            {selectedRecord.vehicle_number && (
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Vehicle</p>
                                        <p className="font-mono">{selectedRecord.vehicle_number}</p>
                                    </div>
                                    <div>
                                        <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Driver</p>
                                        <p>{selectedRecord.driver_name || '-'}</p>
                                    </div>
                                </div>
                            )}
                            {selectedRecord.notes && (
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Notes</p>
                                    <p className="text-sm text-slate-600">{selectedRecord.notes}</p>
                                </div>
                            )}

                            {canEdit && selectedRecord.status === 'dispatched' && (
                                <div className="pt-4 border-t border-slate-200">
                                    <button 
                                        onClick={() => { handleMarkDelivered(selectedRecord.id); setShowDetailModal(false); }}
                                        className="btn-primary w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700"
                                        data-testid="mark-delivered-btn"
                                    >
                                        <CheckCircle size={16} /> Mark as Delivered
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

export default DispatchPage;
