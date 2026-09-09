/**
 * server.js — Express REST API + Static File Server for Audit Observation Tracker
 * Serves the Vite production build and exposes SQLite-backed CRUD endpoints.
 */

const express = require('express');
const path = require('path');
const {
  initDb,
  db,
  mapAuditType,
  mapEngagement,
  mapObservation,
  mapChecklistItem,
  mapFirmProfile,
  DEFAULT_AUDIT_TYPES,
  DEFAULT_FIRM_PROFILE,
  DEFAULT_CHECKLIST_ITEMS,
  SEED_ENGAGEMENTS,
  SEED_OBSERVATIONS,
} = require('./database');

const app = express();
const PORT = process.env.PORT || 3000;

// ─── Middleware ──────────────────────────────────────────────────────────────

app.use(express.json({ limit: '50mb' }));

// Serve static files from the Vite build
const distPath = path.join(__dirname, '..', 'dist');
app.use(express.static(distPath));

// ─── Helper: getFYShortCode (mirrors frontend utility) ──────────────────────

function getFYShortCode(fy) {
  const cleaned = fy.replace(/[^\d-]/g, '');
  const parts = cleaned.split('-');
  if (parts.length === 2) {
    const y1 = parts[0].slice(-2);
    const y2 = parts[1].slice(-2);
    return `${y1}${y2}`;
  }
  return fy.replace(/[^\w]/g, '').slice(0, 4).toUpperCase();
}

// ═══════════════════════════════════════════════════════════════════════════
// AUDIT TYPES
// ═══════════════════════════════════════════════════════════════════════════

app.get('/api/audit-types', (req, res) => {
  try {
    const rows = db.prepare('SELECT * FROM audit_types ORDER BY id').all();
    res.json(rows.map(mapAuditType));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/audit-types', (req, res) => {
  try {
    const { name, code, description, color } = req.body;
    const id = `at-${Date.now()}`;
    db.prepare(`
      INSERT INTO audit_types (id, name, code, description, color, is_default)
      VALUES (?, ?, ?, ?, ?, 0)
    `).run(id, name.trim(), code.trim().toUpperCase(), description?.trim() || null, color || null);
    const row = db.prepare('SELECT * FROM audit_types WHERE id = ?').get(id);
    res.json(mapAuditType(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/audit-types/:id', (req, res) => {
  try {
    const { name, code, description, color } = req.body;
    db.prepare(`
      UPDATE audit_types SET name = ?, code = ?, description = ?, color = ?, updated_at = datetime('now')
      WHERE id = ?
    `).run(name.trim(), code.trim().toUpperCase(), description?.trim() || null, color || null, req.params.id);
    const row = db.prepare('SELECT * FROM audit_types WHERE id = ?').get(req.params.id);
    res.json(mapAuditType(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/audit-types/:id', (req, res) => {
  try {
    db.prepare('DELETE FROM audit_types WHERE id = ?').run(req.params.id);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// ENGAGEMENTS
// ═══════════════════════════════════════════════════════════════════════════

app.get('/api/engagements', (req, res) => {
  try {
    const rows = db.prepare('SELECT * FROM engagements ORDER BY created_at DESC').all();
    res.json(rows.map(mapEngagement));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/engagements/:id', (req, res) => {
  try {
    const row = db.prepare('SELECT * FROM engagements WHERE id = ?').get(req.params.id);
    if (!row) return res.status(404).json({ error: 'Not found' });
    res.json(mapEngagement(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/engagements', (req, res) => {
  try {
    const data = req.body;
    const now = new Date().toISOString();

    // Auto-generate ID
    const year = new Date().getFullYear();
    const countRow = db.prepare('SELECT COUNT(*) as cnt FROM engagements').get();
    const count = (countRow?.cnt || 0) + 1;
    const id = `ENG-${year}-${String(count).padStart(3, '0')}`;

    db.prepare(`
      INSERT INTO engagements (id, client_name, client_pan_gstin, client_code, audit_type_id, financial_year, team_members, engagement_partner, start_date, end_date, branch_location, overall_status, notes, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      data.clientName.trim(),
      data.clientPanGstin?.trim() || null,
      data.clientCode?.trim().toUpperCase() || 'CLI',
      data.auditTypeId,
      data.financialYear.trim(),
      JSON.stringify(data.teamMembers || []),
      data.engagementPartner?.trim() || 'Engagement Partner',
      data.startDate || new Date().toISOString().split('T')[0],
      data.endDate || new Date().toISOString().split('T')[0],
      data.branchLocation?.trim() || null,
      data.overallStatus || 'In Progress',
      data.notes?.trim() || null,
      now,
      now
    );

    const row = db.prepare('SELECT * FROM engagements WHERE id = ?').get(id);
    res.json(mapEngagement(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/engagements/:id', (req, res) => {
  try {
    const data = req.body;
    const now = new Date().toISOString();

    db.prepare(`
      UPDATE engagements SET
        client_name = ?, client_pan_gstin = ?, client_code = ?, audit_type_id = ?,
        financial_year = ?, team_members = ?, engagement_partner = ?,
        start_date = ?, end_date = ?, branch_location = ?,
        overall_status = ?, notes = ?, updated_at = ?
      WHERE id = ?
    `).run(
      data.clientName.trim(),
      data.clientPanGstin?.trim() || null,
      data.clientCode?.trim().toUpperCase() || 'CLI',
      data.auditTypeId,
      data.financialYear.trim(),
      JSON.stringify(data.teamMembers || []),
      data.engagementPartner?.trim() || 'Engagement Partner',
      data.startDate || null,
      data.endDate || null,
      data.branchLocation?.trim() || null,
      data.overallStatus || 'In Progress',
      data.notes?.trim() || null,
      now,
      req.params.id
    );

    const row = db.prepare('SELECT * FROM engagements WHERE id = ?').get(req.params.id);
    res.json(mapEngagement(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/engagements/:id', (req, res) => {
  try {
    // Also delete linked observations
    db.prepare('DELETE FROM observations WHERE engagement_id = ?').run(req.params.id);
    db.prepare('DELETE FROM engagements WHERE id = ?').run(req.params.id);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/engagements/bulk', (req, res) => {
  try {
    const { engagements: newEngagements } = req.body;
    const now = new Date().toISOString();
    const insert = db.prepare(`
      INSERT OR IGNORE INTO engagements (id, client_name, client_pan_gstin, client_code, audit_type_id, financial_year, team_members, engagement_partner, start_date, end_date, branch_location, overall_status, notes, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const tx = db.transaction((engs) => {
      let added = 0;
      for (const eng of engs) {
        const result = insert.run(
          eng.id,
          eng.clientName,
          eng.clientPanGstin || null,
          eng.clientCode || 'CLI',
          eng.auditTypeId,
          eng.financialYear,
          JSON.stringify(eng.teamMembers || []),
          eng.engagementPartner || '',
          eng.startDate || null,
          eng.endDate || null,
          eng.branchLocation || null,
          eng.overallStatus || 'Planning',
          eng.notes || null,
          eng.createdAt || now,
          now
        );
        if (result.changes > 0) added++;
      }
      return added;
    });
    const count = tx(newEngagements || []);
    res.json({ added: count });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// OBSERVATIONS
// ═══════════════════════════════════════════════════════════════════════════

app.get('/api/observations', (req, res) => {
  try {
    const rows = db.prepare('SELECT * FROM observations ORDER BY created_at DESC').all();
    res.json(rows.map(mapObservation));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/observations/:id', (req, res) => {
  try {
    const row = db.prepare('SELECT * FROM observations WHERE id = ?').get(req.params.id);
    if (!row) return res.status(404).json({ error: 'Not found' });
    res.json(mapObservation(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Generate reference number for new observation
function generateObservationRefNo(engagementId) {
  const eng = db.prepare('SELECT * FROM engagements WHERE id = ?').get(engagementId);
  if (!eng) return `OBS-${Date.now()}`;

  const auditType = db.prepare('SELECT * FROM audit_types WHERE id = ?').get(eng.audit_type_id);
  const typeCode = auditType?.code || 'AUD';
  const fyCode = getFYShortCode(eng.financial_year);
  const clientCode = eng.client_code || 'CLI';

  const prefix = `${typeCode}-${fyCode}-${clientCode}-`;

  const existingObs = db.prepare('SELECT reference_no FROM observations WHERE engagement_id = ?').all(engagementId);
  let maxSeq = 0;
  for (const ob of existingObs) {
    if (ob.reference_no.startsWith(prefix)) {
      const seqStr = ob.reference_no.replace(prefix, '');
      const seqNum = parseInt(seqStr, 10);
      if (!isNaN(seqNum) && seqNum > maxSeq) {
        maxSeq = seqNum;
      }
    }
  }

  const nextSeq = String(maxSeq + 1).padStart(3, '0');
  return `${prefix}${nextSeq}`;
}

app.post('/api/observations', (req, res) => {
  try {
    const data = req.body;
    const now = new Date().toISOString();
    const id = `OBS-${Date.now()}`;
    const refNo = data.referenceNo || generateObservationRefNo(data.engagementId);

    db.prepare(`
      INSERT INTO observations (id, reference_no, engagement_id, date_of_observation, area_process, description, severity, financial_impact, root_cause, recommendation, discussion_stakeholder, date_of_discussion, management_response, status, rectification_status, target_rectification_date, actual_rectification_date, person_responsible, attachments, remarks, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id, refNo,
      data.engagementId,
      data.dateOfObservation || new Date().toISOString().split('T')[0],
      data.areaProcess?.trim() || 'General Audit Observation',
      data.description.trim(),
      data.severity || 'Medium',
      data.financialImpact !== undefined ? Number(data.financialImpact) : null,
      data.rootCause?.trim() || null,
      data.recommendation?.trim() || '',
      data.discussionStakeholder?.trim() || null,
      data.dateOfDiscussion || null,
      data.managementResponse?.trim() || null,
      data.status || 'Open',
      data.rectificationStatus || 'Not Started',
      data.targetRectificationDate || null,
      data.actualRectificationDate || null,
      data.personResponsible?.trim() || 'Audit Team',
      data.attachments?.trim() || null,
      data.remarks?.trim() || null,
      now, now
    );

    const row = db.prepare('SELECT * FROM observations WHERE id = ?').get(id);
    res.json(mapObservation(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/observations/:id', (req, res) => {
  try {
    const data = req.body;
    const now = new Date().toISOString();

    db.prepare(`
      UPDATE observations SET
        reference_no = ?, engagement_id = ?, date_of_observation = ?,
        area_process = ?, description = ?, severity = ?,
        financial_impact = ?, root_cause = ?, recommendation = ?,
        discussion_stakeholder = ?, date_of_discussion = ?,
        management_response = ?, status = ?, rectification_status = ?,
        target_rectification_date = ?, actual_rectification_date = ?,
        person_responsible = ?, attachments = ?, remarks = ?,
        updated_at = ?
      WHERE id = ?
    `).run(
      data.referenceNo, data.engagementId,
      data.dateOfObservation || null,
      data.areaProcess?.trim() || null,
      data.description.trim(),
      data.severity || 'Medium',
      data.financialImpact !== undefined ? Number(data.financialImpact) : null,
      data.rootCause?.trim() || null,
      data.recommendation?.trim() || null,
      data.discussionStakeholder?.trim() || null,
      data.dateOfDiscussion || null,
      data.managementResponse?.trim() || null,
      data.status || 'Open',
      data.rectificationStatus || 'Not Started',
      data.targetRectificationDate || null,
      data.actualRectificationDate || null,
      data.personResponsible?.trim() || null,
      data.attachments?.trim() || null,
      data.remarks?.trim() || null,
      now,
      req.params.id
    );

    const row = db.prepare('SELECT * FROM observations WHERE id = ?').get(req.params.id);
    res.json(mapObservation(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.patch('/api/observations/:id/status', (req, res) => {
  try {
    const { status } = req.body;
    db.prepare(`
      UPDATE observations SET status = ?, updated_at = datetime('now') WHERE id = ?
    `).run(status, req.params.id);
    const row = db.prepare('SELECT * FROM observations WHERE id = ?').get(req.params.id);
    res.json(mapObservation(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/observations/:id', (req, res) => {
  try {
    db.prepare('DELETE FROM observations WHERE id = ?').run(req.params.id);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// CHECKLIST ITEMS
// ═══════════════════════════════════════════════════════════════════════════

app.get('/api/checklist-items', (req, res) => {
  try {
    const rows = db.prepare('SELECT * FROM checklist_items ORDER BY audit_type_id, item_number').all();
    res.json(rows.map(mapChecklistItem));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/checklist-items', (req, res) => {
  try {
    const data = req.body;
    const id = `chk-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    const now = new Date().toISOString();

    db.prepare(`
      INSERT INTO checklist_items (id, audit_type_id, category, item_number, check_point, procedure_guidance, statutory_reference, risk_level, is_mandatory, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id, data.auditTypeId,
      data.category || 'General Verification',
      data.itemNumber || `CL-${Date.now()}`,
      data.checkPoint,
      data.procedureGuidance || null,
      data.statutoryReference || null,
      data.riskLevel || 'High',
      data.isMandatory !== undefined ? (data.isMandatory ? 1 : 0) : 1,
      now, now
    );

    const row = db.prepare('SELECT * FROM checklist_items WHERE id = ?').get(id);
    res.json(mapChecklistItem(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/checklist-items/:id', (req, res) => {
  try {
    const data = req.body;
    db.prepare(`
      UPDATE checklist_items SET
        audit_type_id = ?, category = ?, item_number = ?,
        check_point = ?, procedure_guidance = ?, statutory_reference = ?,
        risk_level = ?, is_mandatory = ?, updated_at = datetime('now')
      WHERE id = ?
    `).run(
      data.auditTypeId, data.category, data.itemNumber,
      data.checkPoint, data.procedureGuidance || null,
      data.statutoryReference || null,
      data.riskLevel || 'High',
      data.isMandatory ? 1 : 0,
      req.params.id
    );
    const row = db.prepare('SELECT * FROM checklist_items WHERE id = ?').get(req.params.id);
    res.json(mapChecklistItem(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/checklist-items/:id', (req, res) => {
  try {
    db.prepare('DELETE FROM checklist_items WHERE id = ?').run(req.params.id);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/checklist-items/bulk', (req, res) => {
  try {
    const { items, replace } = req.body;
    if (replace) {
      db.prepare('DELETE FROM checklist_items').run();
    }
    const now = new Date().toISOString();
    const insert = db.prepare(`
      INSERT OR IGNORE INTO checklist_items (id, audit_type_id, category, item_number, check_point, procedure_guidance, statutory_reference, risk_level, is_mandatory, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const tx = db.transaction((items) => {
      for (const item of items) {
        insert.run(
          item.id || `chk-${Date.now()}-${Math.floor(Math.random() * 100000)}`,
          item.auditTypeId,
          item.category || 'General',
          item.itemNumber || null,
          item.checkPoint,
          item.procedureGuidance || null,
          item.statutoryReference || null,
          item.riskLevel || 'High',
          item.isMandatory !== undefined ? (item.isMandatory ? 1 : 0) : 1,
          item.createdAt || now,
          now
        );
      }
    });
    tx(items || []);
    res.json({ count: (items || []).length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// FIRM PROFILE
// ═══════════════════════════════════════════════════════════════════════════

app.get('/api/firm-profile', (req, res) => {
  try {
    const row = db.prepare('SELECT * FROM firm_profile WHERE id = 1').get();
    res.json(mapFirmProfile(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/firm-profile', (req, res) => {
  try {
    const data = req.body;
    db.prepare(`
      INSERT INTO firm_profile (id, firm_name, frn, address, city, phone, email, partner_name, membership_no, website, updated_at)
      VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
      ON CONFLICT(id) DO UPDATE SET
        firm_name = excluded.firm_name,
        frn = excluded.frn,
        address = excluded.address,
        city = excluded.city,
        phone = excluded.phone,
        email = excluded.email,
        partner_name = excluded.partner_name,
        membership_no = excluded.membership_no,
        website = excluded.website,
        updated_at = datetime('now')
    `).run(
      data.firmName, data.frn, data.address, data.city,
      data.phone, data.email, data.partnerName,
      data.membershipNo, data.website || null
    );
    const row = db.prepare('SELECT * FROM firm_profile WHERE id = 1').get();
    res.json(mapFirmProfile(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// EXPORT / IMPORT / RESET
// ═══════════════════════════════════════════════════════════════════════════

app.get('/api/export/all', (req, res) => {
  try {
    const data = {
      version: '1.1',
      exportedAt: new Date().toISOString(),
      firmProfile: mapFirmProfile(db.prepare('SELECT * FROM firm_profile WHERE id = 1').get()),
      auditTypes: db.prepare('SELECT * FROM audit_types').all().map(mapAuditType),
      checklistItems: db.prepare('SELECT * FROM checklist_items').all().map(mapChecklistItem),
      engagements: db.prepare('SELECT * FROM engagements').all().map(mapEngagement),
      observations: db.prepare('SELECT * FROM observations').all().map(mapObservation),
    };
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/import/all', (req, res) => {
  try {
    const data = req.body;
    const now = new Date().toISOString();

    const tx = db.transaction(() => {
      // Import Firm Profile
      if (data.firmProfile) {
        const fp = data.firmProfile;
        db.prepare(`
          INSERT INTO firm_profile (id, firm_name, frn, address, city, phone, email, partner_name, membership_no, website, updated_at)
          VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          ON CONFLICT(id) DO UPDATE SET
            firm_name = excluded.firm_name, frn = excluded.frn, address = excluded.address,
            city = excluded.city, phone = excluded.phone, email = excluded.email,
            partner_name = excluded.partner_name, membership_no = excluded.membership_no,
            website = excluded.website, updated_at = excluded.updated_at
        `).run(fp.firmName, fp.frn, fp.address, fp.city, fp.phone, fp.email, fp.partnerName, fp.membershipNo, fp.website || null, now);
      }

      // Import Audit Types
      if (Array.isArray(data.auditTypes)) {
        db.prepare('DELETE FROM audit_types').run();
        const insert = db.prepare(`INSERT INTO audit_types (id, name, code, description, color, is_default) VALUES (?, ?, ?, ?, ?, ?)`);
        for (const at of data.auditTypes) {
          insert.run(at.id, at.name, at.code, at.description || null, at.color || null, at.isDefault ? 1 : 0);
        }
      }

      // Import Checklist Items
      if (Array.isArray(data.checklistItems)) {
        db.prepare('DELETE FROM checklist_items').run();
        const insert = db.prepare(`INSERT INTO checklist_items (id, audit_type_id, category, item_number, check_point, procedure_guidance, statutory_reference, risk_level, is_mandatory, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`);
        for (const item of data.checklistItems) {
          insert.run(item.id, item.auditTypeId, item.category, item.itemNumber || null, item.checkPoint, item.procedureGuidance || null, item.statutoryReference || null, item.riskLevel || 'High', item.isMandatory ? 1 : 0, item.createdAt || now, now);
        }
      }

      // Import Engagements
      if (Array.isArray(data.engagements)) {
        db.prepare('DELETE FROM engagements').run();
        const insert = db.prepare(`INSERT INTO engagements (id, client_name, client_pan_gstin, client_code, audit_type_id, financial_year, team_members, engagement_partner, start_date, end_date, branch_location, overall_status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`);
        for (const eng of data.engagements) {
          insert.run(eng.id, eng.clientName, eng.clientPanGstin || null, eng.clientCode || 'CLI', eng.auditTypeId, eng.financialYear, JSON.stringify(eng.teamMembers || []), eng.engagementPartner || '', eng.startDate || null, eng.endDate || null, eng.branchLocation || null, eng.overallStatus || 'Planning', eng.notes || null, eng.createdAt || now, now);
        }
      }

      // Import Observations
      if (Array.isArray(data.observations)) {
        db.prepare('DELETE FROM observations').run();
        const insert = db.prepare(`INSERT INTO observations (id, reference_no, engagement_id, date_of_observation, area_process, description, severity, financial_impact, root_cause, recommendation, discussion_stakeholder, date_of_discussion, management_response, status, rectification_status, target_rectification_date, actual_rectification_date, person_responsible, attachments, remarks, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`);
        for (const obs of data.observations) {
          insert.run(obs.id, obs.referenceNo, obs.engagementId, obs.dateOfObservation || null, obs.areaProcess || null, obs.description, obs.severity || 'Medium', obs.financialImpact !== undefined ? Number(obs.financialImpact) : null, obs.rootCause || null, obs.recommendation || null, obs.discussionStakeholder || null, obs.dateOfDiscussion || null, obs.managementResponse || null, obs.status || 'Open', obs.rectificationStatus || 'Not Started', obs.targetRectificationDate || null, obs.actualRectificationDate || null, obs.personResponsible || null, obs.attachments || null, obs.remarks || null, obs.createdAt || now, now);
        }
      }
    });

    tx();
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/reset-sample-data', (req, res) => {
  try {
    const tx = db.transaction(() => {
      // Clear all
      db.prepare('DELETE FROM observations').run();
      db.prepare('DELETE FROM engagements').run();
      db.prepare('DELETE FROM checklist_items').run();
      db.prepare('DELETE FROM audit_types').run();
      db.prepare('DELETE FROM firm_profile').run();

      // Re-seed
      for (const at of DEFAULT_AUDIT_TYPES) {
        db.prepare(`INSERT INTO audit_types (id, name, code, description, is_default) VALUES (?, ?, ?, ?, ?)`).run(at.id, at.name, at.code, at.description || null, at.isDefault ? 1 : 0);
      }
      db.prepare(`INSERT INTO firm_profile (id, firm_name, frn, address, city, phone, email, partner_name, membership_no, website) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(DEFAULT_FIRM_PROFILE.firmName, DEFAULT_FIRM_PROFILE.frn, DEFAULT_FIRM_PROFILE.address, DEFAULT_FIRM_PROFILE.city, DEFAULT_FIRM_PROFILE.phone, DEFAULT_FIRM_PROFILE.email, DEFAULT_FIRM_PROFILE.partnerName, DEFAULT_FIRM_PROFILE.membershipNo, DEFAULT_FIRM_PROFILE.website);
      for (const item of DEFAULT_CHECKLIST_ITEMS) {
        db.prepare(`INSERT INTO checklist_items (id, audit_type_id, category, item_number, check_point, procedure_guidance, statutory_reference, risk_level, is_mandatory) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(item.id, item.auditTypeId, item.category, item.itemNumber, item.checkPoint, item.procedureGuidance || null, item.statutoryReference || null, item.riskLevel, item.isMandatory ? 1 : 0);
      }
      for (const eng of SEED_ENGAGEMENTS) {
        db.prepare(`INSERT INTO engagements (id, client_name, client_pan_gstin, client_code, audit_type_id, financial_year, team_members, engagement_partner, start_date, end_date, branch_location, overall_status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(eng.id, eng.clientName, eng.clientPanGstin, eng.clientCode, eng.auditTypeId, eng.financialYear, JSON.stringify(eng.teamMembers), eng.engagementPartner, eng.startDate, eng.endDate, eng.branchLocation, eng.overallStatus, eng.notes, eng.createdAt, eng.updatedAt);
      }
      for (const obs of SEED_OBSERVATIONS) {
        db.prepare(`INSERT INTO observations (id, reference_no, engagement_id, date_of_observation, area_process, description, severity, financial_impact, root_cause, recommendation, discussion_stakeholder, date_of_discussion, management_response, status, rectification_status, target_rectification_date, actual_rectification_date, person_responsible, attachments, remarks, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(obs.id, obs.referenceNo, obs.engagementId, obs.dateOfObservation, obs.areaProcess, obs.description, obs.severity, obs.financialImpact || null, obs.rootCause || null, obs.recommendation, obs.discussionStakeholder || null, obs.dateOfDiscussion || null, obs.managementResponse || null, obs.status, obs.rectificationStatus, obs.targetRectificationDate || null, obs.actualRectificationDate || null, obs.personResponsible, obs.attachments || null, obs.remarks || null, obs.createdAt, obs.updatedAt);
      }
    });
    tx();
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/clear-client-data', (req, res) => {
  try {
    db.prepare('DELETE FROM observations').run();
    db.prepare('DELETE FROM engagements').run();
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// SPA FALLBACK — serve index.html for all non-API routes
// ═══════════════════════════════════════════════════════════════════════════

app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'));
});

// ─── Start Server ───────────────────────────────────────────────────────────

initDb().then(() => {
  app.listen(PORT, () => {
    console.log('');
    console.log('╔══════════════════════════════════════════════════════════════╗');
    console.log('║                                                              ║');
    console.log('║   🏛️  AUDIT OBSERVATION TRACKER                              ║');
    console.log('║   CA Audit Management & Reporting System                     ║');
    console.log('║                                                              ║');
    console.log(`║   🌐  Server running at: http://localhost:${PORT}              ║`);
    console.log('║   📂  Database: ./data/audit_tracker.db                      ║');
    console.log('║                                                              ║');
    console.log('║   Press Ctrl+C to stop the server.                           ║');
    console.log('║                                                              ║');
    console.log('╚══════════════════════════════════════════════════════════════╝');
    console.log('');

    // Auto-open browser
    const open = (url) => {
      const { exec } = require('child_process');
      const platform = process.platform;
      if (platform === 'win32') {
        exec(`start ${url}`);
      } else if (platform === 'darwin') {
        exec(`open ${url}`);
      } else {
        exec(`xdg-open ${url}`);
      }
    };

    // Small delay before opening browser to let server fully bind
    setTimeout(() => {
      open(`http://localhost:${PORT}`);
    }, 800);
  });
}).catch(err => {
  console.error('Fatal error initializing SQLite database:', err);
  process.exit(1);
});
