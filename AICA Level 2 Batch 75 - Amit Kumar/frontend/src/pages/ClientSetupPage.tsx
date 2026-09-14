import React, { useState } from 'react';
import type { Client } from '../types';
import { createClient, updateClient } from '../services/api';
import { Save, Check } from 'lucide-react';

interface ClientSetupProps {
  client: Client;
  onClientUpdated: () => void;
}

export const ClientSetupPage: React.FC<ClientSetupProps> = ({ client, onClientUpdated }) => {
  const [formData, setFormData] = useState({
    name: client.name || '',
    entity_type: client.entity_type || 'Private Limited Company',
    reporting_period: client.reporting_period || 'FY 2024-25',
    previous_year_period: client.previous_year_period || 'FY 2023-24',
    currency: client.currency || 'INR (in Lakhs)',
    accounting_framework: client.accounting_framework || 'IGAAP',
    schedule_format: client.schedule_format || 'Schedule III Division I',
    prepared_by: client.prepared_by || 'CA Staff',
    reviewed_by: client.reviewed_by || 'CA Partner'
  });

  
  const [metaData, setMetaData] = useState({
    client_name: client.name || '',
    cin_number: '',
    financial_year_ended: ''
  });
  const [directors, setDirectors] = useState([
    { name: '', designation: 'Director', din: '' },
    { name: '', designation: 'Director', din: '' }
  ]);
  const [csAvailable, setCsAvailable] = useState(false);
  const [cs, setCs] = useState({ name: '', membership_no: '' });
  const [cfoAvailable, setCfoAvailable] = useState(false);
  const [cfo, setCfo] = useState({ name: '' });

  React.useEffect(() => {
    if (client?.id) {
      fetch(`/api/client-metadata/${client.id}`).then(r => r.json()).then(d => {
        if(d.client_name) setMetaData(d);
      });
      fetch(`/api/client-metadata/${client.id}/directors`).then(r => r.json()).then(d => {
        if(d && d.length > 0) {
            setDirectors([d[0] || {name:'', designation:'Director', din:''}, d[1] || {name:'', designation:'Director', din:''}]);
        }
      });
      fetch(`/api/client-metadata/${client.id}/cs`).then(r => r.json()).then(d => {
        if (d && d.name) {
          setCsAvailable(true);
          setCs(d);
        }
      });
      fetch(`/api/client-metadata/${client.id}/cfo`).then(r => r.json()).then(d => {
        if (d && d.name) {
          setCfoAvailable(true);
          setCfo(d);
        }
      });
    }
  }, [client]);

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (client?.id) {
        await updateClient(client.id, formData);
      } else {
        await createClient(formData);
      }

      await fetch(`/api/client-metadata/${client.id || 1}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(metaData)
      });
      await fetch(`/api/client-metadata/${client.id || 1}/directors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(directors.filter(d => d.name))
      });
      if (csAvailable) {
        await fetch(`/api/client-metadata/${client.id || 1}/cs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cs)
        });
      }
      if (cfoAvailable) {
        await fetch(`/api/client-metadata/${client.id || 1}/cfo`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(cfo)
        });
      }

      setSuccess(true);
      onClientUpdated();
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="border-b border-ca-border pb-4">
        <h1 className="text-xl font-bold text-navy-900 uppercase tracking-tight">CLIENT & ENGAGEMENT SETUP</h1>
        <p className="text-xs text-ca-muted mt-0.5">Configure client parameters, entity classification, and audit sign-off roles.</p>
      </div>

      {success && (
        <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-semibold rounded flex items-center gap-2">
          <Check className="w-4 h-4 text-emerald-600" />
          Client and Engagement parameters saved successfully!
        </div>
      )}

      <form onSubmit={handleSubmit} className="ca-card space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-xs font-bold text-navy-900 uppercase">Client / Entity Name *</label>
            <input
              type="text"
              required
              className="w-full text-xs p-2.5 border border-ca-border rounded bg-white text-ca-text focus:outline-none focus:border-orange-600"
              value={metaData.client_name}
              onChange={(e) => { setFormData({ ...formData, name: e.target.value }); setMetaData({ ...metaData, client_name: e.target.value }); }}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-navy-900 uppercase">Entity Type *</label>
            <select
              className="w-full text-xs p-2.5 border border-ca-border rounded bg-white text-ca-text focus:outline-none focus:border-orange-600 font-semibold"
              value={formData.entity_type}
              onChange={(e) => setFormData({ ...formData, entity_type: e.target.value })}
            >
              <option value="Private Limited Company">Private Limited Company</option>
              <option value="Public Limited Company">Public Limited Company</option>
              <option value="Limited Liability Partnership (LLP)">Limited Liability Partnership (LLP)</option>
              <option value="Partnership Firm">Partnership Firm</option>
              <option value="Sole Proprietorship">Sole Proprietorship</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-navy-900 uppercase">Current Reporting Period *</label>
            <input
              type="text"
              required
              placeholder="e.g. FY 2024-25"
              className="w-full text-xs p-2.5 border border-ca-border rounded bg-white text-ca-text focus:outline-none focus:border-orange-600"
              value={formData.reporting_period}
              onChange={(e) => setFormData({ ...formData, reporting_period: e.target.value })}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-navy-900 uppercase">Previous Year Period *</label>
            <input
              type="text"
              required
              placeholder="e.g. FY 2023-24"
              className="w-full text-xs p-2.5 border border-ca-border rounded bg-white text-ca-text focus:outline-none focus:border-orange-600"
              value={formData.previous_year_period}
              onChange={(e) => setFormData({ ...formData, previous_year_period: e.target.value })}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-navy-900 uppercase">Reporting Currency / Unit *</label>
            <select
              className="w-full text-xs p-2.5 border border-ca-border rounded bg-white text-ca-text focus:outline-none focus:border-orange-600"
              value={formData.currency}
              onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
            >
              <option value="INR (in Lakhs)">INR (in Lakhs)</option>
              <option value="INR (in Crores)">INR (in Crores)</option>
              <option value="INR (Absolute)">INR (Absolute)</option>
              <option value="INR (in Thousands)">INR (in Thousands)</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-navy-900 uppercase">Accounting Framework</label>
            <input
              type="text"
              disabled
              className="w-full text-xs p-2.5 border border-slate-200 rounded bg-slate-100 text-slate-500 font-bold"
              value={formData.accounting_framework}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-navy-900 uppercase">Schedule Format</label>
            <input
              type="text"
              disabled
              className="w-full text-xs p-2.5 border border-slate-200 rounded bg-slate-100 text-slate-500 font-bold"
              value={formData.schedule_format}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-navy-900 uppercase">Prepared By (CA Audit Staff) *</label>
            <input
              type="text"
              required
              className="w-full text-xs p-2.5 border border-ca-border rounded bg-white text-ca-text focus:outline-none focus:border-orange-600"
              value={formData.prepared_by}
              onChange={(e) => setFormData({ ...formData, prepared_by: e.target.value })}
            />
          </div>

          <div className="space-y-1 md:col-span-2">
            <label className="text-xs font-bold text-navy-900 uppercase">Reviewed By (CA Partner) *</label>
            <input
              type="text"
              required
              className="w-full text-xs p-2.5 border border-ca-border rounded bg-white text-ca-text focus:outline-none focus:border-orange-600"
              value={formData.reviewed_by}
              onChange={(e) => setFormData({ ...formData, reviewed_by: e.target.value })}
            />
          </div>
        </div>

        <div className="border-t border-ca-border pt-4 flex justify-end">
          <button type="submit" disabled={saving} className="ca-button-primary text-xs">
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Client Setup'}
          </button>
        </div>
      </form>
    </div>
  );
};
