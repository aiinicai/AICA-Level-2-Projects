'use strict';

const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, '..', 'data', 'db.json');

function loadRaw() {
  const text = fs.readFileSync(DB_PATH, 'utf8');
  return JSON.parse(text);
}

function saveRaw(db) {
  const tmpPath = DB_PATH + '.tmp';
  fs.writeFileSync(tmpPath, JSON.stringify(db, null, 2), 'utf8');
  fs.renameSync(tmpPath, DB_PATH);
}

/**
 * Very small synchronous "database" wrapper. The app is designed for a
 * single small firm running on one machine, so a JSON file + an in-process
 * mutex-free read/modify/write cycle is more than sufficient, and keeps the
 * project dependency-free.
 */
class Db {
  constructor() {
    this.data = loadRaw();
    if (!this.data.meta.nextIds) {
      this.data.meta.nextIds = { staff: 1, revenue: 1 };
    }
  }

  reload() {
    this.data = loadRaw();
  }

  persist() {
    saveRaw(this.data);
  }

  nextId(kind) {
    const n = this.data.meta.nextIds[kind] || 1;
    this.data.meta.nextIds[kind] = n + 1;
    return n;
  }

  // ---------------- Managers ----------------
  listManagers() {
    return this.data.managers;
  }

  // ---------------- Assignments ----------------
  listAssignments() {
    return this.data.assignments;
  }

  getAssignment(id) {
    return this.data.assignments.find(a => a.id === id);
  }

  addAssignment({ name, managerId, status, notes }) {
    const slug = slugify(name);
    let id = 'assignment-' + slug;
    let n = 2;
    const existingIds = new Set(this.data.assignments.map(a => a.id));
    while (existingIds.has(id)) {
      id = `assignment-${slug}-${n}`;
      n += 1;
    }
    const assignment = {
      id,
      name: name.trim(),
      managerId: managerId || null,
      status: status === 'in-progress' ? 'in-progress' : (status === 'completed' ? 'completed' : 'in-progress'),
      notes: notes || '',
      createdAt: new Date().toISOString().slice(0, 10),
    };
    this.data.assignments.push(assignment);
    this.persist();
    return assignment;
  }

  updateAssignment(id, patch) {
    const a = this.getAssignment(id);
    if (!a) return null;
    if (typeof patch.name === 'string' && patch.name.trim()) a.name = patch.name.trim();
    if (typeof patch.managerId === 'string') a.managerId = patch.managerId;
    if (patch.status === 'in-progress' || patch.status === 'completed') a.status = patch.status;
    if (typeof patch.notes === 'string') a.notes = patch.notes;
    this.persist();
    return a;
  }

  deleteAssignment(id) {
    const idx = this.data.assignments.findIndex(a => a.id === id);
    if (idx === -1) return false;
    this.data.assignments.splice(idx, 1);
    // Detach (not delete) related staff/revenue so history & totals stay
    // auditable; they simply stop contributing once orphaned.
    this.data.staff.forEach(s => { if (s.assignmentId === id) s.assignmentId = null; });
    this.data.revenue.forEach(r => { if (r.assignmentId === id) r._orphanedAssignmentId = id; });
    this.data.revenue = this.data.revenue.filter(r => r.assignmentId !== id);
    this.persist();
    return true;
  }

  // ---------------- Staff / prime cost ----------------
  listStaff() {
    return this.data.staff;
  }

  addStaff({ name, designation, managerId, assignmentId, scope, cost, period, notes }) {
    const id = 'staff-' + this.nextId('staff');
    const staff = {
      id,
      name: (name || designation || 'Staff').trim(),
      designation: (designation || '').trim(),
      managerId: managerId || null,
      assignmentId: scope === 'dedicated' ? (assignmentId || null) : null,
      scope: ['dedicated', 'many', 'partner'].includes(scope) ? scope : 'dedicated',
      cost: Number(cost) || 0,
      period: period || '',
      notes: notes || '',
    };
    this.data.staff.push(staff);
    this.persist();
    return staff;
  }

  updateStaff(id, patch) {
    const s = this.data.staff.find(x => x.id === id);
    if (!s) return null;
    if (typeof patch.name === 'string') s.name = patch.name.trim();
    if (typeof patch.designation === 'string') s.designation = patch.designation.trim();
    if (typeof patch.managerId === 'string') s.managerId = patch.managerId;
    if (['dedicated', 'many', 'partner'].includes(patch.scope)) s.scope = patch.scope;
    if (s.scope === 'dedicated') {
      if (typeof patch.assignmentId === 'string') s.assignmentId = patch.assignmentId;
    } else {
      s.assignmentId = null;
    }
    if (patch.cost !== undefined && !Number.isNaN(Number(patch.cost))) s.cost = Number(patch.cost);
    if (typeof patch.period === 'string') s.period = patch.period;
    if (typeof patch.notes === 'string') s.notes = patch.notes;
    this.persist();
    return s;
  }

  deleteStaff(id) {
    const idx = this.data.staff.findIndex(s => s.id === id);
    if (idx === -1) return false;
    this.data.staff.splice(idx, 1);
    this.persist();
    return true;
  }

  // ---------------- Revenue (billing / credit notes) ----------------
  listRevenue() {
    return this.data.revenue;
  }

  addRevenue({ assignmentId, date, type, voucherType, mid, milestone, amount, otherCharges, notes }) {
    const id = 'rev-' + this.nextId('revenue');
    const entry = {
      id,
      assignmentId,
      date: date || new Date().toISOString().slice(0, 10),
      type: type === 'credit' ? 'credit' : 'billing',
      voucherType: voucherType || '',
      mid: mid || '',
      milestone: milestone || '',
      amount: Number(amount) || 0,
      otherCharges: Number(otherCharges) || 0,
      notes: notes || '',
    };
    this.data.revenue.push(entry);
    this.persist();
    return entry;
  }

  updateRevenue(id, patch) {
    const r = this.data.revenue.find(x => x.id === id);
    if (!r) return null;
    if (typeof patch.assignmentId === 'string') r.assignmentId = patch.assignmentId;
    if (typeof patch.date === 'string') r.date = patch.date;
    if (patch.type === 'credit' || patch.type === 'billing') r.type = patch.type;
    if (typeof patch.voucherType === 'string') r.voucherType = patch.voucherType;
    if (typeof patch.mid === 'string') r.mid = patch.mid;
    if (typeof patch.milestone === 'string') r.milestone = patch.milestone;
    if (patch.amount !== undefined && !Number.isNaN(Number(patch.amount))) r.amount = Number(patch.amount);
    if (patch.otherCharges !== undefined && !Number.isNaN(Number(patch.otherCharges))) r.otherCharges = Number(patch.otherCharges);
    if (typeof patch.notes === 'string') r.notes = patch.notes;
    this.persist();
    return r;
  }

  deleteRevenue(id) {
    const idx = this.data.revenue.findIndex(r => r.id === id);
    if (idx === -1) return false;
    this.data.revenue.splice(idx, 1);
    this.persist();
    return true;
  }
}

function slugify(name) {
  return String(name)
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'item';
}

module.exports = { Db, slugify, DB_PATH };
