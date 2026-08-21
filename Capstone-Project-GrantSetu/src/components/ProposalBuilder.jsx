import React, { useState } from 'react';
import { useGrant } from '../context/GrantContext';
import {
  FileText,
  PlusCircle,
  CheckCircle2,
  AlertCircle,
  IndianRupee,
  Upload,
  Trash2,
  Download,
  Globe,
  Sparkles
} from 'lucide-react';
import { formatINR, formatDate } from '../utils/formatters';
import { readFileAsBase64, downloadBase64File } from '../utils/fileHelper';

export const ProposalBuilder = () => {
  const { proposals, addProposal, sanctionProposalToGrant } = useGrant();
  
  const [showModal, setShowModal] = useState(false);
  const [sanctionModalProp, setSanctionModalProp] = useState(null);
  
  // Multi-currency exchange rates (FX to INR)
  const currencyRates = {
    INR: 1.0,
    USD: 86.5,  // 1 USD = 86.5 INR
    EUR: 90.2,  // 1 EUR = 90.2 INR
    GBP: 108.5  // 1 GBP = 108.5 INR
  };

  const [currency, setCurrency] = useState('INR');

  // New Proposal Form State
  const [formData, setFormData] = useState({
    title: '',
    donorName: '',
    fundingType: 'Domestic CSR',
    targetDomain: 'Healthcare & Nutrition',
    durationMonths: 12,
    projectLocation: 'Maharashtra',
    problemStatement: '',
    currency: 'INR',
    logFrame: {
      goal: '',
      outcome: '',
      outputs: [''],
      activities: ['']
    },
    budgetItems: [
      { category: 'Program Implementation', description: 'Core field operations', cost: 500000 },
      { category: 'Personnel & Field Staff', description: 'Coordinator salaries', cost: 200000 },
      { category: 'Admin & Management Overhead', description: 'Utilities & audit (max 5%)', cost: 35000 }
    ],
    documents: []
  });

  // Sanction Form State
  const [sanctionForm, setSanctionForm] = useState({
    sanctionOrderNo: '',
    sanctionDate: new Date().toISOString().slice(0, 10),
    startDate: new Date().toISOString().slice(0, 10),
    endDate: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    totalSanctionedAmount: 0,
    firstTrancheAmount: 0,
    bankAccountType: 'Domestic'
  });

  const totalRawBudget = formData.budgetItems.reduce((sum, item) => sum + (Number(item.cost) || 0), 0);
  const inrConvertedBudget = currency !== 'INR' ? Math.round(totalRawBudget * currencyRates[currency]) : totalRawBudget;

  const adminItem = formData.budgetItems.find((i) => i.category.toLowerCase().includes('admin'));
  const adminCost = adminItem ? Number(adminItem.cost) || 0 : 0;
  const adminPercent = totalRawBudget > 0 ? ((adminCost / totalRawBudget) * 100).toFixed(1) : 0;

  const handleBudgetItemChange = (index, field, value) => {
    const updated = [...formData.budgetItems];
    updated[index][field] = value;
    setFormData({ ...formData, budgetItems: updated });
  };

  const addBudgetItem = () => {
    setFormData({
      ...formData,
      budgetItems: [...formData.budgetItems, { category: 'Other Direct Expense', description: '', cost: 100000 }]
    });
  };

  const removeBudgetItem = (index) => {
    setFormData({
      ...formData,
      budgetItems: formData.budgetItems.filter((_, i) => i !== index)
    });
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    for (const f of files) {
      try {
        const doc = await readFileAsBase64(f);
        doc.category = 'Proposal Deck / DPR';
        setFormData((prev) => ({ ...prev, documents: [...prev.documents, doc] }));
      } catch (err) {
        console.error('File upload error:', err);
      }
    }
  };

  const removeDoc = (idx) => {
    setFormData((prev) => ({
      ...prev,
      documents: prev.documents.filter((_, i) => i !== idx)
    }));
  };

  const handleSaveProposal = (e) => {
    e.preventDefault();
    addProposal({
      ...formData,
      totalBudget: inrConvertedBudget
    });
    setShowModal(false);
  };

  const openSanctionModal = (prop) => {
    setSanctionModalProp(prop);
    setSanctionForm({
      sanctionOrderNo: `MO/CSR/${Math.floor(1000 + Math.random() * 9000)}`,
      sanctionDate: new Date().toISOString().slice(0, 10),
      startDate: new Date().toISOString().slice(0, 10),
      endDate: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      totalSanctionedAmount: prop.totalBudget,
      firstTrancheAmount: prop.totalBudget * 0.5,
      bankAccountType: prop.fundingType === 'FCRA Foreign' ? 'FCRA' : 'Domestic'
    });
  };

  const handleConfirmSanction = (e) => {
    e.preventDefault();
    if (!sanctionModalProp) return;
    sanctionProposalToGrant(sanctionModalProp.id, sanctionForm);
    setSanctionModalProp(null);
  };

  return (
    <div className="proposal-builder-view">
      <div className="card-header" style={{ marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={24} style={{ color: 'var(--color-primary)' }} />
            Grant Proposal Studio & Multi-Currency LogFrame
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Prepare proposal decks, attach Detailed Project Reports (DPRs), convert foreign currency budgets to INR, and sanction active grants.
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <PlusCircle size={18} /> Draft New Proposal
        </button>
      </div>

      {/* Proposals List Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '24px' }}>
        {proposals.map((prop) => (
          <div key={prop.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <span className={`badge ${prop.fundingType === 'FCRA Foreign' ? 'badge-fcra' : 'badge-domestic'}`}>
                  {prop.fundingType}
                </span>
                <span className={`badge ${prop.status === 'Approved' ? 'badge-active' : 'badge-draft'}`}>
                  {prop.status}
                </span>
              </div>

              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '6px' }}>{prop.title}</h3>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
                Donor: <strong>{prop.donorName}</strong> | Deadline: {formatDate(prop.submissionDeadline)}
              </div>

              <div style={{ backgroundColor: 'var(--bg-dark)', padding: '12px', borderRadius: 'var(--radius-md)', marginBottom: '16px', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Proposed Budget</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--color-primary)' }}>
                  {formatINR(prop.totalBudget)}
                </div>
              </div>

              {/* Attachments list */}
              {(prop.documents || []).length > 0 && (
                <div style={{ marginBottom: '14px' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Attached Files:</div>
                  {(prop.documents || []).map((doc, dIdx) => (
                    <button
                      key={dIdx}
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '0.74rem', padding: '2px 8px', marginRight: '6px' }}
                      onClick={() => downloadBase64File(doc.dataUrl, doc.name)}
                    >
                      <Download size={12} /> {doc.name}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.76rem', color: 'var(--text-subtle)' }}>ID: {prop.id}</span>
              {prop.status !== 'Approved' ? (
                <button className="btn btn-primary btn-sm" onClick={() => openSanctionModal(prop)}>
                  <CheckCircle2 size={14} /> Sanction Grant
                </button>
              ) : (
                <span className="badge badge-active">Active Grant</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* New Proposal Modal */}
      {showModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
          <div className="card" style={{ width: '100%', maxWidth: '800px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="card-header">
              <h3 className="card-title">Draft Proposal & Document Upload Studio</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowModal(false)}>Close</button>
            </div>

            <form onSubmit={handleSaveProposal}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Project Title</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Target Donor Name</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    value={formData.donorName}
                    onChange={(e) => setFormData({ ...formData, donorName: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Funding Category</label>
                  <select
                    className="form-control"
                    value={formData.fundingType}
                    onChange={(e) => setFormData({ ...formData, fundingType: e.target.value })}
                  >
                    <option value="Domestic CSR">Domestic Corporate Social Responsibility (CSR)</option>
                    <option value="FCRA Foreign">FCRA Foreign Contribution</option>
                    <option value="Govt Grant">Central / State Govt Scheme</option>
                    <option value="HNI Philanthropy">HNI Philanthropy / Foundation</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Budget Currency</label>
                  <select
                    className="form-control"
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                  >
                    <option value="INR">INR - Indian Rupee (₹)</option>
                    <option value="USD">USD - US Dollar ($ @ ₹86.5)</option>
                    <option value="EUR">EUR - Euro (€ @ ₹90.2)</option>
                    <option value="GBP">GBP - British Pound (£ @ ₹108.5)</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Problem Statement & Baseline Assessment</label>
                <textarea
                  className="form-control"
                  rows={3}
                  value={formData.problemStatement}
                  onChange={(e) => setFormData({ ...formData, problemStatement: e.target.value })}
                />
              </div>

              {/* Itemized Budget */}
              <div style={{ marginTop: '16px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <h4 style={{ fontWeight: 700, fontSize: '0.95rem' }}>Itemized Budget Breakdown ({currency})</h4>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={addBudgetItem}>
                    <PlusCircle size={14} /> Add Head
                  </button>
                </div>

                {formData.budgetItems.map((item, idx) => (
                  <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 2fr 1fr 40px', gap: '10px', marginBottom: '10px', alignItems: 'center' }}>
                    <input
                      type="text"
                      className="form-control"
                      value={item.category}
                      onChange={(e) => handleBudgetItemChange(idx, 'category', e.target.value)}
                    />
                    <input
                      type="text"
                      className="form-control"
                      value={item.description}
                      onChange={(e) => handleBudgetItemChange(idx, 'description', e.target.value)}
                    />
                    <input
                      type="number"
                      className="form-control"
                      value={item.cost}
                      onChange={(e) => handleBudgetItemChange(idx, 'cost', Number(e.target.value))}
                    />
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => removeBudgetItem(idx)}>
                      <Trash2 size={14} style={{ color: 'var(--color-danger)' }} />
                    </button>
                  </div>
                ))}

                <div style={{ textAlign: 'right', marginTop: '10px' }}>
                  {currency !== 'INR' && (
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      Raw Total: {currency} {totalRawBudget.toLocaleString()} @ FX Rate {currencyRates[currency]}
                    </div>
                  )}
                  <div style={{ fontWeight: 800, fontSize: '1.15rem', color: 'var(--color-primary)' }}>
                    Converted Total (INR): {formatINR(inrConvertedBudget)}
                  </div>
                </div>
              </div>

              {/* Upload Proposal Files Dropzone */}
              <div className="form-group">
                <label className="form-label">Upload Proposal Attachments (DPR / Pitch Deck / MoU Draft)</label>
                <div style={{ border: '2px dashed var(--border-color)', borderRadius: 'var(--radius-md)', padding: '16px', textAlign: 'center', backgroundColor: 'var(--bg-dark)' }}>
                  <Upload size={24} style={{ color: 'var(--color-primary)', marginBottom: '6px' }} />
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Drag & drop files or click to browse</div>
                  <input
                    type="file"
                    multiple
                    style={{ marginTop: '8px' }}
                    onChange={handleFileUpload}
                    accept=".pdf,.png,.jpg,.jpeg,.docx"
                  />
                </div>

                {formData.documents.map((doc, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', padding: '6px 12px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: '0.82rem' }}>📎 {doc.name} ({doc.size})</span>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => removeDoc(idx)}>
                      <Trash2 size={12} style={{ color: 'var(--color-danger)' }} />
                    </button>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Proposal</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sanction Modal */}
      {sanctionModalProp && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
          <div className="card" style={{ width: '100%', maxWidth: '550px' }}>
            <div className="card-header">
              <h3 className="card-title">Confirm Grant Sanction</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setSanctionModalProp(null)}>Cancel</button>
            </div>

            <form onSubmit={handleConfirmSanction}>
              <div className="form-group">
                <label className="form-label">Sanction Order Reference No.</label>
                <input
                  type="text"
                  className="form-control"
                  required
                  value={sanctionForm.sanctionOrderNo}
                  onChange={(e) => setSanctionForm({ ...sanctionForm, sanctionOrderNo: e.target.value })}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Total Sanctioned Amount (₹)</label>
                  <input
                    type="number"
                    className="form-control"
                    required
                    value={sanctionForm.totalSanctionedAmount}
                    onChange={(e) => setSanctionForm({ ...sanctionForm, totalSanctionedAmount: Number(e.target.value) })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">First Tranche Release (₹)</label>
                  <input
                    type="number"
                    className="form-control"
                    required
                    value={sanctionForm.firstTrancheAmount}
                    onChange={(e) => setSanctionForm({ ...sanctionForm, firstTrancheAmount: Number(e.target.value) })}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setSanctionModalProp(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary">
                  <Sparkles size={16} /> Confirm Sanction
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
