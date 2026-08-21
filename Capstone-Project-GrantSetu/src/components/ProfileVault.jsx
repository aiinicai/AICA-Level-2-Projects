import React, { useState } from 'react';
import { useGrant } from '../context/GrantContext';
import { Building2, ShieldCheck, CreditCard, Save, Calendar, CheckCircle } from 'lucide-react';
import { formatDate, getDaysRemaining } from '../utils/formatters';

export const ProfileVault = () => {
  const { ngoProfile, updateProfile } = useGrant();
  const [formData, setFormData] = useState({ ...ngoProfile });
  const [isEditing, setIsEditing] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    updateProfile(formData);
    setIsEditing(false);
  };

  const daysTo12A = getDaysRemaining(formData.twelveAValidTill);

  return (
    <div className="profile-vault-view">
      <div className="card-header" style={{ marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Building2 size={24} style={{ color: 'var(--color-primary)' }} />
            NGO Profile & Regulatory Credentials Vault
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Manage statutory certificates, FCRA SBI designated account, 12A/80G tax exemptions, and CSR-1 registration.
          </p>
        </div>
        {!isEditing ? (
          <button className="btn btn-primary" onClick={() => setIsEditing(true)}>
            Edit Credentials
          </button>
        ) : (
          <button className="btn btn-secondary" onClick={() => setIsEditing(false)}>
            Cancel
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit}>
        {/* NGO Basic Details */}
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>
            <Building2 size={18} style={{ color: 'var(--color-primary)' }} /> Organization Legal Registration
          </h3>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Full Organization Name</label>
              <input
                type="text"
                name="name"
                className="form-control"
                value={formData.name || ''}
                onChange={handleChange}
                disabled={!isEditing}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Short Name / Brand</label>
              <input
                type="text"
                name="shortName"
                className="form-control"
                value={formData.shortName || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
            </div>

            <div className="form-group">
              <label className="form-label">NITI Aayog NGO Darpan ID</label>
              <input
                type="text"
                name="darpanId"
                className="form-control"
                value={formData.darpanId || ''}
                onChange={handleChange}
                disabled={!isEditing}
                placeholder="e.g. MH/2018/0198472"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Registration Type</label>
              <select
                name="registrationType"
                className="form-control"
                value={formData.registrationType || ''}
                onChange={handleChange}
                disabled={!isEditing}
              >
                <option value="Public Charitable Trust">Public Charitable Trust</option>
                <option value="Registered Society">Registered Society (Act 1860)</option>
                <option value="Section 8 Company">Section 8 Company (Companies Act 2013)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Registration Number & Authority</label>
              <input
                type="text"
                name="registrationNo"
                className="form-control"
                value={formData.registrationNo || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
            </div>

            <div className="form-group">
              <label className="form-label">PAN Number</label>
              <input
                type="text"
                name="pan"
                className="form-control"
                value={formData.pan || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
            </div>
          </div>
        </div>

        {/* Tax Exemption & CSR Certificates */}
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>
            <ShieldCheck size={18} style={{ color: 'var(--color-secondary)' }} />
            12A, 80G Tax Certificates & CSR-1 Registration
          </h3>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">12A Certificate URN</label>
              <input
                type="text"
                name="twelveARef"
                className="form-control"
                value={formData.twelveARef || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
            </div>

            <div className="form-group">
              <label className="form-label">12A Expiry Date</label>
              <input
                type="date"
                name="twelveAValidTill"
                className="form-control"
                value={formData.twelveAValidTill || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
              <span style={{ fontSize: '0.75rem', color: daysTo12A <= 90 ? 'var(--color-warning)' : 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                Days remaining: <strong>{daysTo12A} days</strong>
              </span>
            </div>

            <div className="form-group">
              <label className="form-label">80G Tax Exemption URN</label>
              <input
                type="text"
                name="eightyGRef"
                className="form-control"
                value={formData.eightyGRef || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
            </div>

            <div className="form-group">
              <label className="form-label">MCA CSR-1 Registration No</label>
              <input
                type="text"
                name="csr1RegNo"
                className="form-control"
                value={formData.csr1RegNo || ''}
                onChange={handleChange}
                disabled={!isEditing}
                placeholder="e.g. CSR00018942"
              />
            </div>
          </div>
        </div>

        {/* FCRA Statutory Vault */}
        <div className="card" style={{ borderColor: 'rgba(99, 102, 241, 0.4)' }}>
          <h3 className="card-title" style={{ marginBottom: '16px', color: 'var(--color-secondary)' }}>
            <CreditCard size={18} />
            FCRA Statutory Bank Vault (State Bank of India Main Branch Rule)
          </h3>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
            As per FCRA Amendment 2020, foreign contribution funds must strictly be received into the designated SBI New Delhi Main Branch account before utilization.
          </p>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">FCRA Registration Number</label>
              <input
                type="text"
                name="fcraRegNo"
                className="form-control"
                value={formData.fcraRegNo || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
            </div>

            <div className="form-group">
              <label className="form-label">FCRA Validity Expiry</label>
              <input
                type="date"
                name="fcraValidTill"
                className="form-control"
                value={formData.fcraValidTill || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Designated FCRA Bank Name</label>
              <input
                type="text"
                name="fcraBankName"
                className="form-control"
                value={formData.fcraBankName || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Designated SBI Account Number</label>
              <input
                type="text"
                name="fcraAccountNo"
                className="form-control"
                value={formData.fcraAccountNo || ''}
                onChange={handleChange}
                disabled={!isEditing}
              />
            </div>
          </div>
        </div>

        {isEditing && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsEditing(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              <Save size={16} /> Save All Credentials
            </button>
          </div>
        )}
      </form>
    </div>
  );
};
