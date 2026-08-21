import React, { useState } from 'react';
import { useGrant } from '../context/GrantContext';
import { Folder, Download, Search, FileText, Receipt, Network, ShieldCheck, FileCheck, Eye } from 'lucide-react';
import { downloadBase64File } from '../utils/fileHelper';

export const DocumentVault = () => {
  const { proposals, expenses, subGrants, ngoProfile } = useGrant();
  const [filterCategory, setFilterCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  // Collect all documents across the ERP
  const allDocs = [];

  // Proposal docs
  proposals.forEach((p) => {
    (p.documents || []).forEach((d) => {
      allDocs.push({
        ...d,
        sourceModule: 'Proposal Studio',
        entityTitle: p.title,
        entityId: p.id
      });
    });
  });

  // Expense docs
  expenses.forEach((e) => {
    (e.documents || []).forEach((d) => {
      allDocs.push({
        ...d,
        sourceModule: 'Expense Ledger',
        entityTitle: `${e.payeeName} (${e.voucherNo})`,
        entityId: e.id
      });
    });
  });

  // Sub-grant docs
  subGrants.forEach((sg) => {
    (sg.documents || []).forEach((d) => {
      allDocs.push({
        ...d,
        sourceModule: 'Sub-Granting',
        entityTitle: sg.subGranteeName,
        entityId: sg.id
      });
    });
  });

  const filteredDocs = allDocs.filter((doc) => {
    const matchesCat = filterCategory === 'All' || doc.sourceModule === filterCategory;
    const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          doc.entityTitle.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div className="document-vault-view">
      <div className="card-header" style={{ marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Folder size={24} style={{ color: 'var(--color-primary)' }} />
            Central NGO Document & Compliance Audit Vault
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Centralized repository of all uploaded proposal decks, vendor invoices, sub-grant MoUs, tax certificates, and UCs.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <div className="nav-search" style={{ width: '260px' }}>
            <Search size={15} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            className="form-control"
            style={{ width: '180px' }}
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
          >
            <option value="All">All Categories</option>
            <option value="Proposal Studio">Proposals</option>
            <option value="Expense Ledger">Vendor Invoices</option>
            <option value="Sub-Granting">Sub-Grant MoUs</option>
          </select>
        </div>
      </div>

      {/* Documents Grid / Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <FileText size={18} style={{ color: 'var(--color-secondary)' }} />
            Uploaded Audit Files ({filteredDocs.length} Documents)
          </h3>
        </div>

        {filteredDocs.length > 0 ? (
          <div className="table-responsive">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Document Name</th>
                  <th>Source Module</th>
                  <th>Associated Entity</th>
                  <th>Size & Format</th>
                  <th>Upload Date</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredDocs.map((doc, idx) => (
                  <tr key={idx}>
                    <td>
                      <strong style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        📎 {doc.name}
                      </strong>
                    </td>
                    <td>
                      <span className="badge badge-active">{doc.sourceModule}</span>
                    </td>
                    <td>
                      <div>{doc.entityTitle}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>ID: {doc.entityId}</div>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        {doc.size || 'Base64'} | {doc.type?.split('/')[1]?.toUpperCase() || 'FILE'}
                      </span>
                    </td>
                    <td>{doc.uploadedAt?.slice(0, 10) || 'N/A'}</td>
                    <td>
                      {doc.dataUrl ? (
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => downloadBase64File(doc.dataUrl, doc.name)}
                        >
                          <Download size={13} /> Download
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-subtle)' }}>Sample File</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Folder size={48} style={{ opacity: 0.3, marginBottom: '12px' }} />
            <p>No documents found matching your filter criteria.</p>
            <p style={{ fontSize: '0.82rem' }}>Upload files directly when creating Proposals, logging Expense Vouchers, or awarding Sub-Grants!</p>
          </div>
        )}
      </div>
    </div>
  );
};
