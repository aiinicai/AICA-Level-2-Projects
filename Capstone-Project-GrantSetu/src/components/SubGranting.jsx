import React, { useState } from 'react';
import { useGrant } from '../context/GrantContext';
import { Network, PlusCircle, AlertOctagon, CheckCircle2, FileText, IndianRupee, ShieldAlert, Upload, Trash2, Download } from 'lucide-react';
import { formatINR, formatDate } from '../utils/formatters';
import { readFileAsBase64, downloadBase64File } from '../utils/fileHelper';

export const SubGranting = () => {
  const { grants, subGrants, addSubGrant, updateSubGrant } = useGrant();
  const [showModal, setShowModal] = useState(false);

  // Filter domestic non-FCRA grants vs FCRA grants
  const domesticGrants = grants.filter((g) => g.fundingType !== 'FCRA Foreign');
  const fcraGrants = grants.filter((g) => g.fundingType === 'FCRA Foreign');

  const [form, setForm] = useState({
    parentGrantId: domesticGrants[0] ? domesticGrants[0].id : '',
    subGranteeName: '',
    subGranteeDarpanId: '',
    subGranteePan: '',
    subGrantee12A: '',
    contactPerson: '',
    email: '',
    mouRefNo: `SVF/SUB-MOU/2025/${Math.floor(10 + Math.random() * 90)}`,
    mouDate: new Date().toISOString().slice(0, 10),
    sanctionedAmount: 500000,
    firstTranche: 250000,
    purpose: '',
    documents: []
  });

  const selectedParent = grants.find((g) => g.id === form.parentGrantId);
  const isFcraSelected = selectedParent?.fundingType === 'FCRA Foreign';

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    for (const f of files) {
      try {
        const doc = await readFileAsBase64(f);
        doc.category = 'Sub-Grant MoU';
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
    if (isFcraSelected) return;

    addSubGrant({
      ...form,
      parentGrantTitle: selectedParent ? selectedParent.title : '',
      fundingType: selectedParent ? selectedParent.fundingType : 'Domestic CSR'
    });
    setShowModal(false);
  };

  const handlePartnerUcToggle = (subGrantId, trancheId) => {
    const sub = subGrants.find((sg) => sg.id === subGrantId);
    if (!sub) return;
    const updatedTranches = (sub.tranches || []).map((t) => {
      if (t.id === trancheId) {
        return { ...t, ucSubmitted: !t.ucSubmitted };
      }
      return t;
    });
    updateSubGrant({ ...sub, tranches: updatedTranches });
  };

  return (
    <div className="sub-granting-view">
      <div className="card-header" style={{ marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Network size={24} style={{ color: 'var(--color-primary)' }} />
            Non-FCRA Sub-Granting Studio & Grassroots Partner ERP
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Award and monitor sub-grants to grassroots partner CBOs/NGOs under Domestic CSR & Govt Grants with partner UC compliance tracking.
          </p>
        </div>

        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <PlusCircle size={18} /> Award Sub-Grant to Partner
        </button>
      </div>

      {/* FCRA Statutory Warning Banner */}
      <div className="alert-banner" style={{ background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(245, 158, 11, 0.1) 100%)', borderColor: 'rgba(239, 68, 68, 0.4)' }}>
        <AlertOctagon size={28} style={{ color: 'var(--color-danger)', flexShrink: 0 }} />
        <div>
          <h4 style={{ fontWeight: 800, color: 'var(--color-danger)' }}>
            Statutory Rule Notice: FCRA 2020 Sub-Granting Prohibition (Section 7 Amendment)
          </h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Under the Foreign Contribution (Regulation) Amendment Act 2020, <strong>foreign contribution grants CANNOT be sub-granted</strong> or transferred to any other NGO/association. Sub-granting is legally permitted <strong>ONLY for Domestic CSR & Non-FCRA grants</strong>. GrantSetu automatically enforces this restriction.
          </p>
        </div>
      </div>

      {/* Sub-Grants List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Network size={18} style={{ color: 'var(--color-secondary)' }} />
            Active Sub-Grant Allocations ({subGrants.length} Partners)
          </h3>
        </div>

        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Partner NGO & Darpan</th>
                <th>Parent Grant</th>
                <th>MoU & Date</th>
                <th>Sanctioned (₹)</th>
                <th>Disbursed (₹)</th>
                <th>Partner UC Status</th>
                <th>MoU Documents</th>
              </tr>
            </thead>
            <tbody>
              {subGrants.map((sg) => {
                const pendingUc = (sg.tranches || []).some((t) => !t.ucSubmitted);
                return (
                  <tr key={sg.id}>
                    <td>
                      <strong>{sg.subGranteeName}</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Darpan: {sg.subGranteeDarpanId || 'Verified'} | Contact: {sg.contactPerson}
                      </div>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{sg.parentGrantTitle}</div>
                      <span className="badge badge-domestic">{sg.fundingType || 'Domestic CSR'}</span>
                    </td>
                    <td>
                      <strong>{sg.mouRefNo}</strong>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{formatDate(sg.mouDate)}</div>
                    </td>
                    <td>
                      <strong style={{ color: 'var(--text-main)' }}>{formatINR(sg.sanctionedAmount)}</strong>
                    </td>
                    <td>
                      <strong style={{ color: 'var(--color-success)' }}>{formatINR(sg.disbursedAmount)}</strong>
                    </td>
                    <td>
                      {(sg.tranches || []).map((t) => (
                        <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', margin: '2px 0' }}>
                          <button
                            className={`btn btn-sm ${t.ucSubmitted ? 'btn-secondary' : 'btn-outline'}`}
                            style={{ fontSize: '0.72rem', padding: '2px 6px' }}
                            onClick={() => handlePartnerUcToggle(sg.id, t.id)}
                          >
                            Tranche {t.trancheNo}: {t.ucSubmitted ? 'UC Verified' : 'UC Pending'}
                          </button>
                        </div>
                      ))}
                    </td>
                    <td>
                      {(sg.documents || []).length > 0 ? (
                        sg.documents.map((doc, dIdx) => (
                          <button
                            key={dIdx}
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: '0.74rem', padding: '3px 8px' }}
                            onClick={() => downloadBase64File(doc.dataUrl, doc.name)}
                          >
                            <Download size={12} /> {doc.name}
                          </button>
                        ))
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>No File</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Award Sub-Grant Modal */}
      {showModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
          <div className="card" style={{ width: '100%', maxWidth: '720px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="card-header">
              <h3 className="card-title">Award Sub-Grant to Partner Grassroots NGO</h3>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowModal(false)}>Close</button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Select Parent Domestic Grant</label>
                <select
                  className="form-control"
                  value={form.parentGrantId}
                  onChange={(e) => setForm({ ...form, parentGrantId: e.target.value })}
                  required
                >
                  <optgroup label="Domestic CSR & Govt Grants (Sub-Granting Allowed)">
                    {domesticGrants.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.title} ({g.fundingType}) - {formatINR(g.totalSanctionedAmount)}
                      </option>
                    ))}
                  </optgroup>

                  {fcraGrants.length > 0 && (
                    <optgroup label="FCRA Foreign Grants (PROHIBITED under FCRA Section 7)">
                      {fcraGrants.map((g) => (
                        <option key={g.id} value={g.id} disabled>
                          🚫 [FCRA BLOCKED] {g.title}
                        </option>
                      ))}
                    </optgroup>
                  )}
                </select>
              </div>

              {isFcraSelected && (
                <div className="alert-banner" style={{ background: 'rgba(239, 68, 68, 0.2)', borderColor: 'var(--color-danger)' }}>
                  <ShieldAlert size={20} style={{ color: 'var(--color-danger)' }} />
                  <span style={{ fontSize: '0.85rem', color: 'var(--color-danger)', fontWeight: 600 }}>
                    ERROR: Cannot sub-grant from an FCRA Foreign Grant. Please select a Domestic CSR or Govt Grant.
                  </span>
                </div>
              )}

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Sub-Recipient Partner NGO Name</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    placeholder="e.g. Gramin Mahila Vikas Sanstha"
                    value={form.subGranteeName}
                    onChange={(e) => setForm({ ...form, subGranteeName: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Partner NITI Aayog Darpan ID</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. MH/2019/0219481"
                    value={form.subGranteeDarpanId}
                    onChange={(e) => setForm({ ...form, subGranteeDarpanId: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Partner PAN Number</label>
                  <input
                    type="text"
                    className="form-control"
                    value={form.subGranteePan}
                    onChange={(e) => setForm({ ...form, subGranteePan: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Sub-Grant MoU Ref Number</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    value={form.mouRefNo}
                    onChange={(e) => setForm({ ...form, mouRefNo: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Sub-Grant Sanctioned Amount (₹)</label>
                  <input
                    type="number"
                    className="form-control"
                    required
                    value={form.sanctionedAmount}
                    onChange={(e) => setForm({ ...form, sanctionedAmount: Number(e.target.value) })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Tranche 1 Disbursement (₹)</label>
                  <input
                    type="number"
                    className="form-control"
                    required
                    value={form.firstTranche}
                    onChange={(e) => setForm({ ...form, firstTranche: Number(e.target.value) })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Purpose & Scope of Sub-Grant Work</label>
                <textarea
                  className="form-control"
                  rows={2}
                  value={form.purpose}
                  onChange={(e) => setForm({ ...form, purpose: e.target.value })}
                  placeholder="Describe field activities assigned to the partner NGO..."
                />
              </div>

              {/* Upload MoU File Dropzone */}
              <div className="form-group">
                <label className="form-label">Attach Sub-Grant MoU Agreement (PDF/Image)</label>
                <div style={{ border: '2px dashed var(--border-color)', borderRadius: 'var(--radius-md)', padding: '16px', textAlign: 'center', backgroundColor: 'var(--bg-dark)' }}>
                  <Upload size={24} style={{ color: 'var(--color-primary)', marginBottom: '6px' }} />
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Drag & drop or click to upload signed MoU</div>
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

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={isFcraSelected}>
                  Award Sub-Grant
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
