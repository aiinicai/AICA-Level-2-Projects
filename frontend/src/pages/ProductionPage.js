import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Plus, Search, Eye, X, Loader2, Play, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

const ProductionPage = () => {
    const { api, hasRole } = useAuth();
    const [batches, setBatches] = useState([]);
    const [reports, setReports] = useState([]);
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [stageFilter, setStageFilter] = useState('all');
    const [showModal, setShowModal] = useState(false);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [selectedBatch, setSelectedBatch] = useState(null);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        product_id: '',
        chemist_report_id: '',
        quantity_produced: 0,
        start_date: new Date().toISOString().split('T')[0],
        notes: ''
    });

    const canEdit = hasRole(['admin', 'production_manager']);

    const fetchData = useCallback(async () => {
        try {
            const [batchRes, repRes, prodRes] = await Promise.all([
                api().get('/production-batches'),
                api().get('/chemist-reports?status=issued'),
                api().get('/products')
            ]);
            setBatches(batchRes.data);
            setReports(repRes.data);
            setProducts(prodRes.data);
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
            await api().post('/production-batches', form);
            toast.success('Production batch started');
            setShowModal(false);
            resetForm();
            fetchData();
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Operation failed');
        }
        setSaving(false);
    };

    const handleUpdateStage = async (batchId, newStage) => {
        try {
            const updateData = { stage: newStage };
            if (newStage === 'completed') {
                updateData.end_date = new Date().toISOString().split('T')[0];
                updateData.quality_check = 'passed';
            }
            await api().put(`/production-batches/${batchId}`, updateData);
            toast.success(`Batch moved to ${newStage}`);
            fetchData();
        } catch (err) {
            toast.error('Failed to update stage');
        }
    };

    const resetForm = () => {
        setForm({
            product_id: '',
            chemist_report_id: '',
            quantity_produced: 0,
            start_date: new Date().toISOString().split('T')[0],
            notes: ''
        });
    };

    const getStageBadge = (stage) => {
        const badges = {
            processing: 'stage-production',
            packaging: 'stage-packaging',
            dispatch: 'stage-dispatch',
            completed: 'status-completed'
        };
        return badges[stage] || 'status-pending';
    };

    const filteredBatches = batches.filter(b => {
        const matchesSearch = b.batch_number.toLowerCase().includes(search.toLowerCase()) || b.product_name.toLowerCase().includes(search.toLowerCase());
        const matchesStage = stageFilter === 'all' || b.stage === stageFilter;
        return matchesSearch && matchesStage;
    });

    return (
        <div className="space-y-6" data-testid="production-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-heading text-3xl font-bold tracking-tight text-slate-900">PRODUCTION</h1>
                    <p className="text-slate-500 text-sm mt-1">Track production batches through processing</p>
                </div>
                {canEdit && (
                    <button 
                        onClick={() => { setShowModal(true); resetForm(); }}
                        className="btn-primary flex items-center gap-2"
                        data-testid="start-production-btn"
                    >
                        <Plus size={16} /> Start Production
                    </button>
                )}
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input
                        type="text"
                        placeholder="Search by batch number or product..."
                        className="input-default pl-10"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        data-testid="search-production"
                    />
                </div>
                <div className="flex gap-2 flex-wrap">
                    {['all', 'processing', 'packaging', 'dispatch', 'completed'].map((stage) => (
                        <button
                            key={stage}
                            onClick={() => setStageFilter(stage)}
                            className={`px-4 py-2 text-xs font-bold uppercase tracking-wider rounded-sm transition-colors ${
                                stageFilter === stage 
                                    ? 'bg-slate-900 text-white' 
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                        >
                            {stage}
                        </button>
                    ))}
                </div>
            </div>

            {/* Kanban-style Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {loading ? (
                    <div className="col-span-full flex items-center justify-center p-12">
                        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
                    </div>
                ) : filteredBatches.length === 0 ? (
                    <div className="col-span-full text-center p-12 text-slate-500 card-default">
                        No production batches found.
                    </div>
                ) : (
                    filteredBatches.map((batch) => (
                        <div key={batch.id} className="card-default p-4" data-testid={`production-card-${batch.id}`}>
                            <div className="flex items-start justify-between mb-3">
                                <div>
                                    <p className="font-mono font-medium text-slate-900">{batch.batch_number}</p>
                                    <p className="text-sm text-slate-600">{batch.product_name}</p>
                                </div>
                                <span className={`status-badge ${getStageBadge(batch.stage)}`}>
                                    {batch.stage}
                                </span>
                            </div>
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-slate-500">Quantity:</span>
                                    <span className="font-mono">{batch.quantity_produced}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-500">Start Date:</span>
                                    <span className="font-mono">{batch.start_date}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-500">QC Status:</span>
                                    <span className={`font-medium ${batch.quality_check === 'passed' ? 'text-green-600' : batch.quality_check === 'failed' ? 'text-red-600' : 'text-amber-600'}`}>
                                        {batch.quality_check}
                                    </span>
                                </div>
                            </div>
                            <div className="flex gap-2 mt-4 pt-4 border-t border-slate-100">
                                <button 
                                    onClick={() => { setSelectedBatch(batch); setShowDetailModal(true); }}
                                    className="btn-secondary flex-1 text-xs py-2 h-auto"
                                    data-testid={`view-batch-${batch.id}`}
                                >
                                    <Eye size={14} className="mr-1" /> View
                                </button>
                                {canEdit && batch.stage === 'processing' && (
                                    <button 
                                        onClick={() => handleUpdateStage(batch.id, 'packaging')}
                                        className="btn-primary flex-1 text-xs py-2 h-auto"
                                        data-testid={`move-to-packaging-${batch.id}`}
                                    >
                                        <Play size={14} className="mr-1" /> To Packaging
                                    </button>
                                )}
                                {canEdit && batch.stage === 'packaging' && (
                                    <button 
                                        onClick={() => handleUpdateStage(batch.id, 'dispatch')}
                                        className="btn-primary flex-1 text-xs py-2 h-auto"
                                    >
                                        <Play size={14} className="mr-1" /> To Dispatch
                                    </button>
                                )}
                                {canEdit && batch.stage === 'dispatch' && (
                                    <button 
                                        onClick={() => handleUpdateStage(batch.id, 'completed')}
                                        className="btn-primary flex-1 text-xs py-2 h-auto bg-green-600 hover:bg-green-700"
                                    >
                                        <CheckCircle size={14} className="mr-1" /> Complete
                                    </button>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Start Production Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="production-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <h3 className="font-heading font-semibold text-lg">Start Production Batch</h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="p-4 space-y-4">
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Chemist Report (Materials Issued)</label>
                                <select
                                    className="input-default"
                                    value={form.chemist_report_id}
                                    onChange={(e) => {
                                        const report = reports.find(r => r.id === e.target.value);
                                        setForm({ 
                                            ...form, 
                                            chemist_report_id: e.target.value,
                                            product_id: report?.product_id || '',
                                            quantity_produced: report?.batch_size || 0
                                        });
                                    }}
                                    required
                                    data-testid="production-report-select"
                                >
                                    <option value="">-- Select Report --</option>
                                    {reports.map(r => (
                                        <option key={r.id} value={r.id}>{r.report_number} - {r.product_name} (Batch: {r.batch_number})</option>
                                    ))}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Product</label>
                                    <select
                                        className="input-default"
                                        value={form.product_id}
                                        onChange={(e) => setForm({ ...form, product_id: e.target.value })}
                                        required
                                        data-testid="production-product-select"
                                    >
                                        <option value="">-- Select --</option>
                                        {products.map(p => (
                                            <option key={p.id} value={p.id}>{p.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Quantity</label>
                                    <input
                                        type="number"
                                        className="input-default font-mono"
                                        value={form.quantity_produced || ''}
                                        onChange={(e) => setForm({ ...form, quantity_produced: parseFloat(e.target.value) || 0 })}
                                        required
                                        data-testid="production-quantity"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Start Date</label>
                                <input
                                    type="date"
                                    className="input-default font-mono"
                                    value={form.start_date}
                                    onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                                    required
                                    data-testid="production-start-date"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Notes (Optional)</label>
                                <textarea
                                    className="input-default min-h-[60px]"
                                    value={form.notes}
                                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                                    data-testid="production-notes"
                                />
                            </div>
                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="btn-secondary flex-1">Cancel</button>
                                <button type="submit" disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2" data-testid="save-production-btn">
                                    {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                                    Start Production
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Detail Modal */}
            {showDetailModal && selectedBatch && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-sm w-full max-w-lg max-h-[90vh] overflow-y-auto" data-testid="production-detail-modal">
                        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                            <div>
                                <h3 className="font-heading font-semibold text-lg">{selectedBatch.batch_number}</h3>
                                <p className="text-sm text-slate-500">{selectedBatch.product_name}</p>
                            </div>
                            <button onClick={() => setShowDetailModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="p-4 space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Stage</p>
                                    <span className={`status-badge ${getStageBadge(selectedBatch.stage)}`}>
                                        {selectedBatch.stage}
                                    </span>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Quality Check</p>
                                    <span className={`font-medium ${selectedBatch.quality_check === 'passed' ? 'text-green-600' : selectedBatch.quality_check === 'failed' ? 'text-red-600' : 'text-amber-600'}`}>
                                        {selectedBatch.quality_check}
                                    </span>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Quantity</p>
                                    <p className="font-mono">{selectedBatch.quantity_produced}</p>
                                </div>
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Start Date</p>
                                    <p className="font-mono">{selectedBatch.start_date}</p>
                                </div>
                                {selectedBatch.end_date && (
                                    <div>
                                        <p className="text-xs font-bold uppercase tracking-wider text-slate-500">End Date</p>
                                        <p className="font-mono">{selectedBatch.end_date}</p>
                                    </div>
                                )}
                            </div>
                            {selectedBatch.notes && (
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Notes</p>
                                    <p className="text-sm text-slate-600">{selectedBatch.notes}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ProductionPage;
