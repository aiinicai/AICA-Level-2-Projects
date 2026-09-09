/**
 * server.cjs — Express REST API + Static File Server for Audit Observation Tracker
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
} = require('./database.cjs');

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
    const rows = db.all('SELECT * FROM audit_types ORDER BY id');
    res.json(rows.map(mapAuditType));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/audit-types', (req, res) => {
  try {
    const { name, code, description, color } = req.body;
    const id = `at-${Date.now()}`;
    db.run(
      'INSERT INTO audit_types (id, name, code, description, color, is_default) VALUES (?, ?, ?, ?, ?, 0)',
      [id, name.trim(), code.trim().toUpperCase(), description?.trim() || null, color || null]
    );
    const row = db.get('SELECT * FROM audit_types WHERE id = ?', [id]);
    res.json(mapAuditType(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/audit-types/:id', (req, res) => {
  try {
    const { name, code, description, color } = req.body;
    db.run(
      "UPDATE audit_types SET name = ?, code = ?, description = ?, color = ?, updated_at = datetime('now') WHERE id = ?",
      [name.trim(), code.trim().toUpperCase(), description?.trim() || null, color || null, req.params.id]
    );
    const row = db.get('SELECT * FROM audit_types WHERE id = ?', [req.params.id]);
    res.json(mapAuditType(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/audit-types/:id', (req, res) => {
  try {
    db.run('DELETE FROM audit_types WHERE id = ?', [req.params.id]);
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
    const rows = db.all('SELECT * FROM engagements ORDER BY created_at DESC');
    res.json(rows.map(mapEngagement));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/engagements/:id', (req, res) => {
  try {
    const row = db.get('SELECT * FROM engagements WHERE id = ?', [req.params.id]);
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

    const year = new Date().getFullYear();
    const countRow = db.get('SELECT COUNT(*) as cnt FROM engagements');
    const count = (countRow?.cnt || 0) + 1;
    const id = `ENG-${year}-${String(count).padStart(3, '0')}`;

    db.run(
      `INSERT INTO engagements (id, client_name, client_pan_gstin, client_code, audit_type_id, financial_year, team_members, engagement_partner, start_date, end_date, branch_location, overall_status, notes, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
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
        now,
      ]
    );

    const row = db.get('SELECT * FROM engagements WHERE id = ?', [id]);
    res.json(mapEngagement(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/engagements/:id', (req, res) => {
  try {
    const data = req.body;
    const now = new Date().toISOString();

    db.run(
      `UPDATE engagements SET
        client_name = ?, client_pan_gstin = ?, client_code = ?, audit_type_id = ?,
        financial_year = ?, team_members = ?, engagement_partner = ?,
        start_date = ?, end_date = ?, branch_location = ?,
        overall_status = ?, notes = ?, updated_at = ?
      WHERE id = ?`,
      [
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
        req.params.id,
      ]
    );

    const row = db.get('SELECT * FROM engagements WHERE id = ?', [req.params.id]);
    res.json(mapEngagement(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/engagements/:id', (req, res) => {
  try {
    db.run('DELETE FROM observations WHERE engagement_id = ?', [req.params.id]);
    db.run('DELETE FROM engagements WHERE id = ?', [req.params.id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/engagements/bulk', (req, res) => {
  try {
    const { engagements: newEngagements } = req.body;
    const now = new Date().toISOString();
    let added = 0;
    for (const eng of newEngagements || []) {
      db.run(
        `INSERT OR IGNORE INTO engagements (id, client_name, client_pan_gstin, client_code, audit_type_id, financial_year, team_members, engagement_partner, start_date, end_date, branch_location, overall_status, notes, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
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
          now,
        ]
      );
      added++;
    }
    res.json({ added });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// OBSERVATIONS
// ═══════════════════════════════════════════════════════════════════════════

app.get('/api/observations', (req, res) => {
  try {
    const rows = db.all('SELECT * FROM observations ORDER BY created_at DESC');
    res.json(rows.map(mapObservation));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/observations/:id', (req, res) => {
  try {
    const row = db.get('SELECT * FROM observations WHERE id = ?', [req.params.id]);
    if (!row) return res.status(404).json({ error: 'Not found' });
    res.json(mapObservation(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

function generateObservationRefNo(engagementId) {
  const eng = db.get('SELECT * FROM engagements WHERE id = ?', [engagementId]);
  if (!eng) return `OBS-${Date.now()}`;

  const auditType = db.get('SELECT * FROM audit_types WHERE id = ?', [eng.audit_type_id]);
  const typeCode = auditType?.code || 'AUD';
  const fyCode = getFYShortCode(eng.financial_year);
  const clientCode = eng.client_code || 'CLI';

  const prefix = `${typeCode}-${fyCode}-${clientCode}-`;
  const existingObs = db.all('SELECT reference_no FROM observations WHERE engagement_id = ?', [engagementId]);
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

    db.run(
      `INSERT INTO observations (id, reference_no, engagement_id, date_of_observation, area_process, description, severity, financial_impact, root_cause, recommendation, discussion_stakeholder, date_of_discussion, management_response, status, rectification_status, target_rectification_date, actual_rectification_date, person_responsible, attachments, remarks, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
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
      ]
    );

    const row = db.get('SELECT * FROM observations WHERE id = ?', [id]);
    res.json(mapObservation(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/observations/:id', (req, res) => {
  try {
    const data = req.body;
    const now = new Date().toISOString();

    db.run(
      `UPDATE observations SET
        reference_no = ?, engagement_id = ?, date_of_observation = ?,
        area_process = ?, description = ?, severity = ?,
        financial_impact = ?, root_cause = ?, recommendation = ?,
        discussion_stakeholder = ?, date_of_discussion = ?,
        management_response = ?, status = ?, rectification_status = ?,
        target_rectification_date = ?, actual_rectification_date = ?,
        person_responsible = ?, attachments = ?, remarks = ?,
        updated_at = ?
      WHERE id = ?`,
      [
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
      ]
    );

    const row = db.get('SELECT * FROM observations WHERE id = ?', [req.params.id]);
    res.json(mapObservation(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.patch('/api/observations/:id/status', (req, res) => {
  try {
    const { status } = req.body;
    db.run("UPDATE observations SET status = ?, updated_at = datetime('now') WHERE id = ?", [status, req.params.id]);
    const row = db.get('SELECT * FROM observations WHERE id = ?', [req.params.id]);
    res.json(mapObservation(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/observations/:id', (req, res) => {
  try {
    db.run('DELETE FROM observations WHERE id = ?', [req.params.id]);
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
    const rows = db.all('SELECT * FROM checklist_items ORDER BY audit_type_id, item_number');
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

    db.run(
      `INSERT INTO checklist_items (id, audit_type_id, category, item_number, check_point, procedure_guidance, statutory_reference, risk_level, is_mandatory, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id, data.auditTypeId,
        data.category || 'General Verification',
        data.itemNumber || `CL-${Date.now()}`,
        data.checkPoint,
        data.procedureGuidance || null,
        data.statutoryReference || null,
        data.riskLevel || 'High',
        data.isMandatory !== undefined ? (data.isMandatory ? 1 : 0) : 1,
        now, now
      ]
    );

    const row = db.get('SELECT * FROM checklist_items WHERE id = ?', [id]);
    res.json(mapChecklistItem(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/checklist-items/:id', (req, res) => {
  try {
    const data = req.body;
    db.run(
      `UPDATE checklist_items SET
        audit_type_id = ?, category = ?, item_number = ?,
        check_point = ?, procedure_guidance = ?, statutory_reference = ?,
        risk_level = ?, is_mandatory = ?, updated_at = datetime('now')
      WHERE id = ?`,
      [
        data.auditTypeId, data.category, data.itemNumber,
        data.checkPoint, data.procedureGuidance || null,
        data.statutoryReference || null,
        data.riskLevel || 'High',
        data.isMandatory ? 1 : 0,
        req.params.id
      ]
    );
    const row = db.get('SELECT * FROM checklist_items WHERE id = ?', [req.params.id]);
    res.json(mapChecklistItem(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.delete('/api/checklist-items/:id', (req, res) => {
  try {
    db.run('DELETE FROM checklist_items WHERE id = ?', [req.params.id]);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/checklist-items/bulk', (req, res) => {
  try {
    const { items, replace } = req.body;
    if (replace) {
      db.run('DELETE FROM checklist_items');
    }
    const now = new Date().toISOString();
    for (const item of items || []) {
      db.run(
        `INSERT OR IGNORE INTO checklist_items (id, audit_type_id, category, item_number, check_point, procedure_guidance, statutory_reference, risk_level, is_mandatory, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
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
        ]
      );
    }
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
    const row = db.get('SELECT * FROM firm_profile WHERE id = 1');
    res.json(mapFirmProfile(row));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.put('/api/firm-profile', (req, res) => {
  try {
    const data = req.body;
    db.run(
      `INSERT INTO firm_profile (id, firm_name, frn, address, city, phone, email, partner_name, membership_no, website, updated_at)
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
        updated_at = datetime('now')`,
      [
        data.firmName, data.frn, data.address, data.city,
        data.phone, data.email, data.partnerName,
        data.membershipNo, data.website || null
      ]
    );
    const row = db.get('SELECT * FROM firm_profile WHERE id = 1');
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
      firmProfile: mapFirmProfile(db.get('SELECT * FROM firm_profile WHERE id = 1')),
      auditTypes: db.all('SELECT * FROM audit_types').map(mapAuditType),
      checklistItems: db.all('SELECT * FROM checklist_items').map(mapChecklistItem),
      engagements: db.all('SELECT * FROM engagements').map(mapEngagement),
      observations: db.all('SELECT * FROM observations').map(mapObservation),
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

    if (data.firmProfile) {
      const fp = data.firmProfile;
      db.run(
        `INSERT INTO firm_profile (id, firm_name, frn, address, city, phone, email, partner_name, membership_no, website, updated_at)
         VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET
           firm_name = excluded.firm_name, frn = excluded.frn, address = excluded.address,
           city = excluded.city, phone = excluded.phone, email = excluded.email,
           partner_name = excluded.partner_name, membership_no = excluded.membership_no,
           website = excluded.website, updated_at = excluded.updated_at`,
        [fp.firmName, fp.frn, fp.address, fp.city, fp.phone, fp.email, fp.partnerName, fp.membershipNo, fp.website || null, now]
      );
    }

    if (Array.isArray(data.auditTypes)) {
      db.run('DELETE FROM audit_types');
      for (const at of data.auditTypes) {
        db.run('INSERT INTO audit_types (id, name, code, description, color, is_default) VALUES (?, ?, ?, ?, ?, ?)', [at.id, at.name, at.code, at.description || null, at.color || null, at.isDefault ? 1 : 0]);
      }
    }

    if (Array.isArray(data.checklistItems)) {
      db.run('DELETE FROM checklist_items');
      for (const item of data.checklistItems) {
        db.run('INSERT INTO checklist_items (id, audit_type_id, category, item_number, check_point, procedure_guidance, statutory_reference, risk_level, is_mandatory, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [item.id, item.auditTypeId, item.category, item.itemNumber || null, item.checkPoint, item.procedureGuidance || null, item.statutoryReference || null, item.riskLevel || 'High', item.isMandatory ? 1 : 0, item.createdAt || now, now]);
      }
    }

    if (Array.isArray(data.engagements)) {
      db.run('DELETE FROM engagements');
      for (const eng of data.engagements) {
        db.run('INSERT INTO engagements (id, client_name, client_pan_gstin, client_code, audit_type_id, financial_year, team_members, engagement_partner, start_date, end_date, branch_location, overall_status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [eng.id, eng.clientName, eng.clientPanGstin || null, eng.clientCode || 'CLI', eng.auditTypeId, eng.financialYear, JSON.stringify(eng.teamMembers || []), eng.engagementPartner || '', eng.startDate || null, eng.endDate || null, eng.branchLocation || null, eng.overallStatus || 'Planning', eng.notes || null, eng.createdAt || now, now]);
      }
    }

    if (Array.isArray(data.observations)) {
      db.run('DELETE FROM observations');
      for (const obs of data.observations) {
        db.run('INSERT INTO observations (id, reference_no, engagement_id, date_of_observation, area_process, description, severity, financial_impact, root_cause, recommendation, discussion_stakeholder, date_of_discussion, management_response, status, rectification_status, target_rectification_date, actual_rectification_date, person_responsible, attachments, remarks, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [obs.id, obs.referenceNo, obs.engagementId, obs.dateOfObservation || null, obs.areaProcess || null, obs.description, obs.severity || 'Medium', obs.financialImpact !== undefined ? Number(obs.financialImpact) : null, obs.rootCause || null, obs.recommendation || null, obs.discussionStakeholder || null, obs.dateOfDiscussion || null, obs.managementResponse || null, obs.status || 'Open', obs.rectificationStatus || 'Not Started', obs.targetRectificationDate || null, obs.actualRectificationDate || null, obs.personResponsible || null, obs.attachments || null, obs.remarks || null, obs.createdAt || now, now]);
      }
    }

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/reset-sample-data', (req, res) => {
  try {
    db.run('DELETE FROM observations');
    db.run('DELETE FROM engagements');
    db.run('DELETE FROM checklist_items');
    db.run('DELETE FROM audit_types');
    db.run('DELETE FROM firm_profile');

    for (const at of DEFAULT_AUDIT_TYPES) {
      db.run('INSERT INTO audit_types (id, name, code, description, is_default) VALUES (?, ?, ?, ?, ?)', [at.id, at.name, at.code, at.description || null, at.isDefault ? 1 : 0]);
    }
    db.run('INSERT INTO firm_profile (id, firm_name, frn, address, city, phone, email, partner_name, membership_no, website) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [DEFAULT_FIRM_PROFILE.firmName, DEFAULT_FIRM_PROFILE.frn, DEFAULT_FIRM_PROFILE.address, DEFAULT_FIRM_PROFILE.city, DEFAULT_FIRM_PROFILE.phone, DEFAULT_FIRM_PROFILE.email, DEFAULT_FIRM_PROFILE.partnerName, DEFAULT_FIRM_PROFILE.membershipNo, DEFAULT_FIRM_PROFILE.website]);
    for (const item of DEFAULT_CHECKLIST_ITEMS) {
      db.run('INSERT INTO checklist_items (id, audit_type_id, category, item_number, check_point, procedure_guidance, statutory_reference, risk_level, is_mandatory) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [item.id, item.auditTypeId, item.category, item.itemNumber, item.checkPoint, item.procedureGuidance || null, item.statutoryReference || null, item.riskLevel, item.isMandatory ? 1 : 0]);
    }
    for (const eng of SEED_ENGAGEMENTS) {
      db.run('INSERT INTO engagements (id, client_name, client_pan_gstin, client_code, audit_type_id, financial_year, team_members, engagement_partner, start_date, end_date, branch_location, overall_status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [eng.id, eng.clientName, eng.clientPanGstin, eng.clientCode, eng.auditTypeId, eng.financialYear, JSON.stringify(eng.teamMembers), eng.engagementPartner, eng.startDate, eng.endDate, eng.branchLocation, eng.overallStatus, eng.notes, eng.createdAt, eng.updatedAt]);
    }
    for (const obs of SEED_OBSERVATIONS) {
      db.run('INSERT INTO observations (id, reference_no, engagement_id, date_of_observation, area_process, description, severity, financial_impact, root_cause, recommendation, discussion_stakeholder, date_of_discussion, management_response, status, rectification_status, target_rectification_date, actual_rectification_date, person_responsible, attachments, remarks, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', [obs.id, obs.referenceNo, obs.engagementId, obs.dateOfObservation, obs.areaProcess, obs.description, obs.severity, obs.financialImpact || null, obs.rootCause || null, obs.recommendation, obs.discussionStakeholder || null, obs.dateOfDiscussion || null, obs.managementResponse || null, obs.status, obs.rectificationStatus, obs.targetRectificationDate || null, obs.actualRectificationDate || null, obs.personResponsible, obs.attachments || null, obs.remarks || null, obs.createdAt, obs.updatedAt]);
    }

    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/clear-client-data', (req, res) => {
  try {
    db.run('DELETE FROM observations');
    db.run('DELETE FROM engagements');
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

    setTimeout(() => {
      open(`http://localhost:${PORT}`);
    }, 800);
  });
}).catch(err => {
  console.error('Fatal error initializing SQLite database:', err);
  process.exit(1);
});
