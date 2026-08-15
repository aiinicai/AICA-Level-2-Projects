import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Search, Eye, X, Loader2, Check, Send } from 'lucide-react';
import { toast } from 'sonner';

const ChemistReportsPage = () => {
    const { api, hasRole, user } = useAuth();
    const [reports, setReports] = useState([]);
    const [products, setProducts] = useState([]);
    const [materials, setMaterials] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [showModal, setShowModal] = useState(false);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [selectedReport, setSelectedReport] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        product_id: '',
        batch_size: 0,
        materials_required: [],
        notes: ''
    });
    const [newMaterial, setNewMaterial] = useState({ material_id: '', quantity: 0 });

    const canEdit = hasRole(['admin', 'production_manager']);
    const canIssue = hasRole(['admin', 'store_keeper']);

    const fetchData = useCallback(async () => {
        try {
            const [repRes, prodRes, matRes] = await Promise.all([
                api().get('/chemist-reports'),
                api().get('/products'),
                api().get('/materials')
            ]);
            setReports(repRes.data);
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
        if (form.materials_required.length === 0) {
            toast.error('Add at least one material');
            return;
        }
        setSaving(true);
        try {
            await api().post('/chemist-reports', form);
            toast.success('Chemist report created');
            setShowModal(false);
            resetForm();
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Operation failed');
        }
        setSaving(false);
    };

    const handleApprove = async (reportId) => {
        try {
            await api().put(`/chemist-reports/${reportId}`, { status: 'approved', approved_by: user.id });
            toast.success('Report approved');
            fetchData();
        } catch (err) {
            toast.error('Failed to approve');
        }
    };

    const handleIssueMaterials = async (reportId) => {
        try {
            await api().post(`/chemist-reports/${reportId}/issue-materials`);
            toast.success('Materials issued successfully');
            setShowDetailModal(false);
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to issue materials');
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
            materials_required: [...form.materials_required, {
                material_id: newMaterial.material_id,
                material_name: material.name,
                quantity: newMaterial.quantity,
                unit: material.unit
            }]
        });
        setNewMaterial({ material_id: '', quantity: 0 });
    };

    const removeMaterial = (index) => {
        setForm({ ...form, materials_required: form.materials_required.filter((_, i) => i !== index) });
    };

    const resetForm = () => {
        setForm({ product_id: '', batch_size: 0, materials_required: [], notes: '' });
        setNewMaterial({ material_id: '', quantity: 0 });
    };

    const getStatusBadge = (status) => {
        const badges = {
            pending: 'status-pending',
            approved: 'status-approved',
            issued: 'status-issued',
            in_production: 'status-processing'
        };
        return badges[status] || 'status-pending';
    };

    const filteredReports = reports.filter(r => {
        const matchesSearch = r.report_number.toLowerCase().includes(search.toLowerCase()) || r.product_name.toLowerCase().includes(search.toLowerCase());
        const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    return (
        <div className="space-y-6" data-testid="chemist-reports-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">CHEMIST REPORTS</h1>
                    <p className="text-slate-500 text-sm mt-1">Material issue requests for production</p>
                </div>
                {canEdit && (
                    <button 
                        onClick={() => { setShowModal(true); resetForm(); }}
                        className="btn-primary flex items-center gap-2"
                        data-testid="create-report-btn"
                    >
                        <Plus size={16} /> Create Report
                    </button>
                )}
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search by report number or product..."
                        className="input-default pl-10"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        data-testid="search-reports"
                    />
                </div>
                <div className="flex gap-2 flex-wrap">
                    {['all', 'pending', 'approved', 'issued', 'in_production'].map((status) => (
                        <button
                            key={status}
                            onClick={() => setStatusFilter(status)}
                            className={`px-4 py-2 text-xs font-bold uppercase tracking-wider rounded-sm transition-colors ${
                                statusFilter === status 
                                    ? 'bg-slate-900 text-white' 
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                        >
                            {status.replace('_', ' ')}
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
                ) : filteredReports.length === 0 ? (
                    <div className="text-center p-12 text-slate-500">
                        No chemist reports found.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Report #</th>
                                    <th>Product</th>
                                    <th>Batch #</th>
                                    <th>Batch Size</th>
                                    <th>Status</th>
                                    <th>Created</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredReports.map((report) => (
                                    <tr key={report.id} data-testid={`report-row-${report.id}`}>
                                        <td className="font-mono font-medium text-slate-900">{report.report_number}</td>
                                        <td>{report.product_name}</td>
                                        <td className="font-mono text-sm">{report.batch_number}</td>
                                        <td className="font-mono">{report.batch_size}</td>
                                        <td>
                                            <span className={`status-badge ${getStatusBadge(report.status)}`}>
                                                {report.status.replace('_', ' ')}
                                            </span>
                                        </td>
                                        <td className="font-mono text-sm">{new Date(report.created_at).toLocaleDateString()}</td>
                                        <td>
                                            <div className="flex items-center gap-2">
                                                <button 
                                                    onClick={() => { setSelectedReport(report); setShowDetailModal(true); }}
                                                    className="p-2 text-slate-400 hover:text-blue-600 transition-colors"
                                                    data-testid={`view-report-${report.id}`}
                                                >
                                                    <Eye size={16} />
                                                </button>
                                                {canEdit && report.status === 'pending' && (
                                                    <button 
                                                        onClick={() => handleApprove(report.id)}
                                                        className="p-2 text-slate-400 hover:text-green-600 transition-colors"
                                                        title="Approve"
                                                        data-testid={`approve-report-${report.id}`}
                                                    >
                                                        <Check size={16} />
                                                    </button>
                                                )}
                                                {canIssue && report.status === 'approved' && (
                                                    <button 
                                                        onClick={() => handleIssueMaterials(report.id)}
                                                        className="p-2 text-slate-400 hover:text-blue-600 transition-colors"
                                                        title="Issue Materials"
                                                        data-testid={`issue-report-${report.id}`}
                                                    >
                                                        <Send size={16} />
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
                    <div className="bg-white rounded-sm w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="report-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <h3 className="font-heading font-semibold text-lg">Create Chemist Report</h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-4 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Product</label>
                                    <select
                                        className="input-default"
                                        value={form.product_id}
                                        onChange={(e) => setForm({ ...form, product_id: e.target.value })}
                                        required
                                        data-testid="report-product-select"
                                    >
                                        <option value="">-- Select Product --</option>
                                        {products.map(p => (
                                            <option key={p.id} value={p.id}>{p.name} ({p.category})</option>
                                        ))}
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
                                        data-testid="report-batch-size"
                                    />
                                </div>
                            </div>

                            {/* Materials Section */}
                            <div className="border border-slate-200 rounded-sm p-4">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">Materials Required</h4>
                                
                                <div className="flex gap-2 mb-4">
                                    <select
                                        className="input-default flex-1"
                                        value={newMaterial.material_id}
                                        onChange={(e) => setNewMaterial({ ...newMaterial, material_id: e.target.value })}
                                        data-testid="report-material-select"
                                    >
                                        <option value="">Select Material</option>
                                        {materials.filter(m => m.category === 'chemical').map(m => (
                                            <option key={m.id} value={m.id}>{m.name} (Stock: {m.current_stock} {m.unit})</option>
                                        ))}
                                    </select>
                                    <input
                                        type="number"
                                        className="input-default w-28 font-mono"
                                        placeholder="Qty"
                                        value={newMaterial.quantity || ''}
                                        onChange={(e) => setNewMaterial({ ...newMaterial, quantity: parseFloat(e.target.value) || 0 })}
                                        data-testid="report-material-qty"
                                    />
                                    <button type="button" onClick={addMaterial} className="btn-secondary px-4">
                                        <Plus size={16} />
                                    </button>
                                </div>

                                {form.materials_required.length > 0 && (
                                    <div className="space-y-2">
                                        {form.materials_required.map((mat, idx) => (
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

                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Notes (Optional)</label>
                                <textarea
                                    className="input-default min-h-[60px]"
                                    value={form.notes}
                                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                                    data-testid="report-notes"
                                />
                            </div>

                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2" data-testid="save-report-btn">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    Create Report
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
            {showDetailModal && selectedReport && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="report-detail-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <div>
                                <h3 className="font-heading font-semibold text-lg">{selectedReport.report_number}</h3>
                                <p className="text-sm text-slate-500">{selectedReport.product_name}</p>
                            </div>
                            <button onClick={() => setShowDetailModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-4 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Batch Number</p>
                                    <p className="font-mono">{selectedReport.batch_number}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Batch Size</p>
                                    <p className="font-mono">{selectedReport.batch_size}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Status</p>
                                    <span className={`status-badge ${getStatusBadge(selectedReport.status)}`}>
                                        {selectedReport.status.replace('_', ' ')}
                                    </span>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Created</p>
                                    <p className="font-mono text-sm">{new Date(selectedReport.created_at).toLocaleString()}</p>
                                </div>
                            </div>

                            <div>
                                <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Materials Required</p>
                                <div className="border border-slate-200 rounded-sm overflow-hidden">
                                    <table className="data-table">
                                        <thead>
                                            <tr>
                                                <th>Material</th>
                                                <th>Quantity</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {selectedReport.materials_required.map((mat, idx) => (
                                                <tr key={idx}>
                                                    <td>{mat.material_name}</td>
                                                    <td className="font-mono">{mat.quantity} {mat.unit}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {selectedReport.notes && (
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Notes</p>
                                    <p className="text-sm text-slate-600">{selectedReport.notes}</p>
                                </div>
                            )}

                            {canIssue && selectedReport.status === 'approved' && (
                                <div className="pt-4 border-t border-slate-200">
                                    <button 
                                        onClick={() => handleIssueMaterials(selectedReport.id)}
                                        className="btn-primary w-full flex items-center justify-center gap-2"
                                        data-testid="issue-materials-btn"
                                    >
                                        <Send size={16} /> Issue Materials
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

export default ChemistReportsPage;
