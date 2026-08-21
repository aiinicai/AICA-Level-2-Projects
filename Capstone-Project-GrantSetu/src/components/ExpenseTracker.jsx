import React, { useState } from 'react';
import { useGrant } from '../context/GrantContext';
import {
  Receipt,
  PlusCircle,
  AlertTriangle,
  FileSpreadsheet,
  Trash2,
  Upload,
  Download,
  Eye,
  Paperclip
} from 'lucide-react';
import { formatINR } from '../utils/formatters';
import { readFileAsBase64, downloadBase64File } from '../utils/fileHelper';

export const ExpenseTracker = () => {
  const {
    grants,
    expenses,
    addExpense,
    deleteExpense,
    selectedGrantId,
    setSelectedGrantId
  } = useGrant();

  const [showModal, setShowModal] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);

  const activeGrants = grants.filter((g) => g.status === 'Active' || g.status === 'Pending Closure');
  const currentGrant = grants.find((g) => g.id === selectedGrantId) || activeGrants[0] || grants[0];

  const [form, setForm] = useState({
    grantId: currentGrant ? currentGrant.id : '',
    voucherNo: `SVF/25-26/${Math.floor(100 + Math.random() * 900)}`,
    date: new Date().toISOString().slice(0, 10),
    payeeName: '',
    category: currentGrant && currentGrant.budgetBreakdown ? currentGrant.budgetBreakdown[0]?.category : 'Program Expenses',
    amount: 50000,
    paymentMode: 'Bank NEFT',
    bankAccountUsed: currentGrant && currentGrant.fundingType === 'FCRA Foreign' ? 'FCRA Designated SBI New Delhi Main Branch Account' : 'Domestic HDFC Account',
    fcraTag: currentGrant && currentGrant.fundingType === 'FCRA Foreign' ? 'FCRA Foreign' : 'Domestic',
    receiptAttached: true,
    description: '',
    approvedBy: 'Dr. Anjali Deshmukh',
    documents: []
  });

  const handleGrantSelectChange = (grantId) => {
    setSelectedGrantId(grantId);
    const g = grants.find((item) => item.id === grantId);
    if (g) {
      setForm((prev) => ({
        ...prev,
        grantId: g.id,
        category: g.budgetBreakdown ? g.budgetBreakdown[0]?.category : 'Program Expenses',
        bankAccountUsed: g.fundingType === 'FCRA Foreign' ? 'FCRA Designated SBI New Delhi Main Branch Account' : 'Domestic HDFC Account',
        fcraTag: g.fundingType === 'FCRA Foreign' ? 'FCRA Foreign' : 'Domestic'
      }));
    }
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    for (const f of files) {
      try {
        const doc = await readFileAsBase64(f);
        doc.category = 'Vendor Invoice / Cash Bill';
        setForm((prev) => ({ ...prev, documents: [...prev.documents, doc] }));
      } catch (err) {
        console.error('File upload error:', err);
      }
    }
  };

  const removeDoc = (idx) => {
    setForm((prev) => ({
      ...prev,
      documents: prev.documents.filter((_, i) => i !== idx)
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const g = grants.find((item) => item.id === form.grantId);
    addExpense({
      ...form,
      grantTitle: g ? g.title : 'General Grant'
    });
    setShowModal(false);
  };

  const filteredExpenses = currentGrant
    ? expenses.filter((e) => e.grantId === currentGrant.id)
    : expenses;

  return (
    <div className="expense-tracker-view">
      <div className="card-header" style={{ marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Receipt size={24} style={{ color: 'var(--color-primary)' }} />
            Expense Vouching Ledger & Uploaded Receipts
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Log programmatic vouchers, attach vendor tax invoices, monitor FCRA fund segregation, and check BvA burn rates.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <select
            className="form-control"
            style={{ width: '280px', fontWeight: 600 }}
            value={currentGrant ? currentGrant.id : ''}
            onChange={(e) => handleGrantSelectChange(e.target.value)}
          >
            {grants.map((g) => (
              <option key={g.id} value={g.id}>
                {g.title}
              </option>
            ))}
          </select>

          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            <PlusCircle size={18} /> Log Voucher & Attach Bill
          </button>
        </div>
      </div>

      {/* Budget vs Actuals (BvA) Analysis Card */}
      {currentGrant && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <FileSpreadsheet size={18} style={{ color: 'var(--color-secondary)' }} />
              Budget vs Actuals (BvA) Matrix - {currentGrant.title}
            </h3>
            <span className={`badge ${currentGrant.fundingType === 'FCRA Foreign' ? 'badge-fcra' : 'badge-domestic'}`}>
              {currentGrant.fundingType}
            </span>
          </div>

          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Budget Line Item / Head</th>
                  <th>Allocated Budget (₹)</th>
                  <th>Actual Expenses (₹)</th>
                  <th>Variance Balance (₹)</th>
                  <th>Burn %</th>
                </tr>
              </thead>
              <tbody>
                {(currentGrant.budgetBreakdown || []).map((head, idx) => {
                  const allocated = head.allocated || 0;
                  const spent = head.spent || 0;
                  const variance = allocated - spent;
                  const burnRate = allocated > 0 ? Math.round((spent / allocated) * 100) : 0;
                  const isOverBudget = variance < 0;

                  return (
                    <tr key={idx}>
                      <td>
                        <strong>{head.category}</strong>
                      </td>
                      <td>{formatINR(allocated)}</td>
                      <td style={{ fontWeight: 600, color: 'var(--color-primary)' }}>{formatINR(spent)}</td>
                      <td style={{ fontWeight: 700, color: isOverBudget ? 'var(--color-danger)' : 'var(--color-success)' }}>
                        {formatINR(variance)} {isOverBudget && <AlertTriangle size={13} style={{ display: 'inline', marginLeft: '4px' }} />}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div className="progress-bar-bg" style={{ width: '80px' }}>
                            <div
                              className={`progress-bar-fill ${burnRate > 100 ? 'warning' : ''}`}
                              style={{ width: `${Math.min(100, burnRate)}%` }}
                            ></div>
                          </div>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{burnRate}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Expense Vouchers Ledger Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Receipt size={18} style={{ color: 'var(--color-primary)' }} />
            Voucher Transactions Ledger ({filteredExpenses.length} Records)
          </h3>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Voucher # & Date</th>
                <th>Payee & Particulars</th>
                <th>Budget Category</th>
                <th>Account & Tag</th>
                <th>Amount (₹)</th>
                <th>Receipt Invoice</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredExpenses.map((exp) => (
                <tr key={exp.id}>
                  <td>
                    <strong>{exp.voucherNo}</strong>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{exp.date}</div>
                  </td>
                  <td>
                    <strong>{exp.payeeName}</strong>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{exp.description || 'Verified Voucher'}</div>
                  </td>
                  <td>{exp.category}</td>
                  <td>
                    <span className={`badge ${exp.fcraTag === 'FCRA Foreign' ? 'badge-fcra' : 'badge-domestic'}`}>
                      {exp.fcraTag || 'Domestic'}
                    </span>
                  </td>
                  <td>
                    <strong style={{ color: 'var(--color-primary)', fontSize: '0.95rem' }}>{formatINR(exp.amount)}</strong>
                  </td>
                  <td>
                    {(exp.documents || []).length > 0 ? (
                      exp.documents.map((doc, dIdx) => (
                        <button
                          key={dIdx}
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '0.74rem', padding: '3px 8px' }}
                          onClick={() => downloadBase64File(doc.dataUrl, doc.name)}
                          title="Download Invoice File"
                        >
                          <Paperclip size={12} /> {doc.name}
                        </button>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>No Attachment</span>
                    )}
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => deleteExpense(exp.id)}
                      title="Delete Voucher"
                    >
                      <Trash2 size={14} style={{ color: 'var(--color-danger)' }} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Log Voucher Modal */}
      {showModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
          <div className="card" style={{ width: '100%', maxWidth: '650px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="card-header">
              <h3 className="card-title">Log Expense Voucher & Attach Invoice</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowModal(false)}>Close</button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Select Grant</label>
                  <select
                    className="form-control"
                    value={form.grantId}
                    onChange={(e) => handleGrantSelectChange(e.target.value)}
                    required
                  >
                    {grants.map((g) => (
                      <option key={g.id} value={g.id}>{g.title}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Voucher Number</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    value={form.voucherNo}
                    onChange={(e) => setForm({ ...form, voucherNo: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Date</label>
                  <input
                    type="date"
                    className="form-control"
                    required
                    value={form.date}
                    onChange={(e) => setForm({ ...form, date: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Payee / Vendor Name</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    placeholder="e.g. Force Motors Ltd / Staff Honorarium"
                    value={form.payeeName}
                    onChange={(e) => setForm({ ...form, payeeName: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Budget Head / Category</label>
                  <select
                    className="form-control"
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                  >
                    {(currentGrant?.budgetBreakdown || []).map((head, idx) => (
                      <option key={idx} value={head.category}>{head.category}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Amount (₹)</label>
                  <input
                    type="number"
                    className="form-control"
                    required
                    value={form.amount}
                    onChange={(e) => setForm({ ...form, amount: Number(e.target.value) })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Payment Bank Account Tag</label>
                <select
                  className="form-control"
                  value={form.fcraTag}
                  onChange={(e) => setForm({ ...form, fcraTag: e.target.value })}
                >
                  <option value="Domestic">Domestic HDFC Bank Account</option>
                  <option value="FCRA Foreign">FCRA Designated SBI New Delhi Main Branch Account</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Voucher Description / Particulars</label>
                <textarea
                  className="form-control"
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>

              {/* Upload Invoice Attachment Dropzone */}
              <div className="form-group">
                <label className="form-label">Upload Vendor Tax Invoice / Cash Bill Receipt</label>
                <div style={{ border: '2px dashed var(--border-color)', borderRadius: 'var(--radius-md)', padding: '16px', textAlign: 'center', backgroundColor: 'var(--bg-dark)' }}>
                  <Upload size={24} style={{ color: 'var(--color-primary)', marginBottom: '6px' }} />
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Drag & drop invoice PDF or image</div>
                  <input
                    type="file"
                    multiple
                    style={{ marginTop: '8px' }}
                    onChange={handleFileUpload}
                    accept=".pdf,.png,.jpg,.jpeg,.docx"
                  />
                </div>

                {form.documents.map((doc, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px', padding: '6px 12px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: '0.82rem' }}>📎 {doc.name} ({doc.size})</span>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => removeDoc(idx)}>
                      <Trash2 size={12} style={{ color: 'var(--color-danger)' }} />
                    </button>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Voucher & Receipt</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
