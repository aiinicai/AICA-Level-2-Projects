// Controls: accounting periods (locks), approvals queue (maker-checker) and the audit trail
import { store, get, post, download, toast, showError, confirmDialog } from '../store.js';
import { common } from '../components.js';
import { money, date, dateTime, addMonths, fyOf, titleCase } from '../util.js';

const { ref, computed, watch, onMounted } = Vue;

export const PeriodsPage = {
  components: common,
  setup() {
    const ref0 = ref(fyOf(store.asOf || new Date().toISOString().slice(0, 10), store.company?.fy_start_month || 4)[0]);
    const d = ref(null);
    async function load() { try { d.value = await get('/api/periods?fy=' + ref0.value); } catch (e) { showError(e); } }
    onMounted(load);
    function shift(n) { ref0.value = addMonths(ref0.value, 12 * n); load(); }
    async function lock(p) {
      const reason = await confirmDialog('Lock ' + date(p.period_end), 'Locking prevents approval of any calculation that changes results in this period. Post journals before locking.', { input: 'Comment (optional)', ok: 'Lock period' });
      if (reason === false) return;
      try { await post('/api/periods/' + p.period_end + '/lock', { reason }); toast('Period locked', 'ok'); load(); } catch (e) { showError(e); }
    }
    async function reopen(p) {
      const reason = await confirmDialog('Reopen ' + date(p.period_end), 'Authorised reopening procedure — the reason is recorded in the audit trail.', { input: 'Reason (mandatory)', ok: 'Reopen', danger: true });
      if (!reason) return;
      try { await post('/api/periods/' + p.period_end + '/reopen', { reason }); toast('Period reopened', 'ok'); load(); } catch (e) { showError(e); }
    }
    const fyLabel = computed(() => d.value ? 'FY ' + d.value.fy_start.slice(0, 4) + '-' + d.value.fy_end.slice(2, 4) : '');
    return { store, d, shift, lock, reopen, fyLabel, date, dateTime };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>Accounting periods</h1><div class="sub">Lock month-ends after journals are posted. Approvals that would change a locked period are blocked; only an Administrator can reopen, with a reason.</div></div>
      <div class="btn-group"><button class="btn" @click="shift(-1)"><AppIcon name="chevron-left" :size="14"/></button><button class="btn" style="min-width:110px;justify-content:center">{{ fyLabel }}</button><button class="btn" @click="shift(1)"><AppIcon name="chevron-right" :size="14"/></button></div></div>
    <div class="card"><table class="t">
      <thead><tr><th>Period ending</th><th>Status</th><th>Locked</th><th>Reopened</th><th>Comment / reason</th><th class="right">Action</th></tr></thead>
      <tbody><tr v-if="!d"><td colspan="6"><div class="progress"><i></i></div></td></tr>
        <tr v-for="p in (d ? d.periods : [])" :key="p.period_end"><td><b>{{ date(p.period_end) }}</b></td>
          <td><span class="badge" :class="p.status==='Locked' ? 'bad' : 'ok'"><AppIcon :name="p.status==='Locked' ? 'lock' : 'lock-open'" :size="11"/> {{ p.status }}</span></td>
          <td>{{ dateTime(p.locked_at) }}</td><td>{{ dateTime(p.reopened_at) }}</td><td class="small text-2">{{ p.reason || '' }}</td>
          <td class="right"><button v-if="p.status!=='Locked' && store.can('period.lock')" class="btn sm" @click="lock(p)"><AppIcon name="lock" :size="13"/> Lock</button>
            <button v-if="p.status==='Locked' && store.user.role==='ADMIN'" class="btn sm danger" @click="reopen(p)"><AppIcon name="lock-open" :size="13"/> Reopen</button></td></tr></tbody></table></div>
  </div>`,
};

export const ApprovalsPage = {
  components: common,
  setup() {
    const d = ref({ leases: [], rates: [], imports: [] });
    const loading = ref(false);
    async function load() {
      loading.value = true;
      try { d.value = await get('/api/approvals'); window.__lease116?.refreshCounts(); } catch (e) { showError(e); } finally { loading.value = false; }
    }
    onMounted(load);
    const groups = computed(() => [
      { key: 'Prepared', title: 'Submitted — awaiting review', rows: d.value.leases.filter(l => l.status === 'Prepared') },
      { key: 'Under Review', title: 'Under review — awaiting approval', rows: d.value.leases.filter(l => l.status === 'Under Review') },
      { key: 'Draft', title: 'Calculated drafts not yet submitted', rows: d.value.leases.filter(l => l.status === 'Draft') },
    ]);
    async function act(l, action) {
      let comment = null;
      if (action === 'return') { comment = await confirmDialog('Return ' + l.lease_code, 'Explain what the preparer must correct.', { input: 'Review comment', ok: 'Return', danger: true }); if (!comment) return; }
      if (action === 'approve') { comment = await confirmDialog('Approve ' + l.lease_code, 'Approve calculation run #' + l.run_no + '? Review the schedules and judgments before approving.', { input: 'Approval comment (optional)', ok: 'Approve' }); if (comment === false) return; }
      try { const r = await post('/api/leases/' + l.lease_id + '/workflow/' + action, { comment: comment || null }); toast(l.lease_code + ': ' + r.status, 'ok'); load(); } catch (e) { showError(e); }
    }
    async function approveRate(r) {
      if (!(await confirmDialog('Approve discount rate', r.currency + ' ' + r.tenor + ': ' + r.rate_pct + '% — confirm the methodology and supporting evidence have been reviewed.', { ok: 'Approve rate' }))) return;
      try { await post('/api/discount-rates/' + r.id + '/approve'); toast('Rate approved', 'ok'); load(); } catch (e) { showError(e); }
    }
    return { store, d, loading, groups, act, approveRate, money, date, dateTime };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>Approvals</h1><div class="sub">Maker-checker queue. Segregation of duties is enforced — a preparer cannot review or approve their own calculation.</div></div>
      <button class="btn" @click="load"><AppIcon name="refresh-cw" :size="14"/> Refresh</button></div>
    <div v-for="g in groups" :key="g.key" class="card mb"><div class="card-head"><h3>{{ g.title }}</h3><span class="badge">{{ g.rows.length }}</span></div>
      <table class="t compact"><thead><tr><th>Lease</th><th>Description</th><th>Run</th><th class="num">Initial liability</th><th>Pending events</th><th>Updated</th><th class="right">Actions</th></tr></thead>
        <tbody><tr v-if="!g.rows.length"><td colspan="7" class="empty">Nothing here.</td></tr>
          <tr v-for="l in g.rows" :key="l.lease_id"><td><a :href="'#/leases/' + l.lease_id"><b>{{ l.lease_code }}</b></a></td><td class="wrap">{{ l.description }}</td><td>#{{ l.run_no }} <StatusBadge :status="l.run_status"/></td>
            <td class="num">{{ money(l.initial_liability) }}</td><td>{{ (l.pending_events || []).join(', ') || '—' }}</td><td>{{ dateTime(l.updated_at) }}</td>
            <td class="right nowrap">
              <a class="btn sm" :href="'#/leases/' + l.lease_id"><AppIcon name="eye" :size="13"/> Open</a>
              <button v-if="l.status==='Prepared' && store.can('lease.review')" class="btn sm" @click="act(l, 'start_review')">Start review</button>
              <button v-if="['Prepared','Under Review'].includes(l.status) && store.can('lease.approve')" class="btn sm primary" @click="act(l, 'approve')">Approve</button>
              <button v-if="['Prepared','Under Review'].includes(l.status) && store.can('lease.review')" class="btn sm danger" @click="act(l, 'return')">Return</button>
              <button v-if="l.status==='Draft' && store.can('lease.submit')" class="btn sm" @click="act(l, 'submit')">Submit</button>
            </td></tr></tbody></table></div>
    <div class="grid c2">
      <div class="card"><div class="card-head"><h3>Discount rates awaiting approval</h3><span class="badge">{{ d.rates.length }}</span></div>
        <table class="t compact"><thead><tr><th>Currency</th><th>Tenor</th><th class="num">Rate %</th><th></th></tr></thead>
          <tbody><tr v-if="!d.rates.length"><td colspan="4" class="empty">None.</td></tr>
            <tr v-for="r in d.rates" :key="r.id"><td>{{ r.currency }}</td><td>{{ r.tenor }}</td><td class="num">{{ r.rate_pct }}</td><td class="right"><button v-if="store.can('rate.approve')" class="btn sm primary" @click="approveRate(r)">Approve</button></td></tr></tbody></table></div>
      <div class="card"><div class="card-head"><h3>Imports awaiting approval</h3><span class="badge">{{ d.imports.length }}</span></div>
        <table class="t compact"><thead><tr><th>Batch</th><th>Template</th><th>File</th><th class="num">Rows</th><th></th></tr></thead>
          <tbody><tr v-if="!d.imports.length"><td colspan="5" class="empty">None.</td></tr>
            <tr v-for="b in d.imports" :key="b.id"><td>#{{ b.id }}</td><td>{{ b.template }}</td><td>{{ b.filename }}</td><td class="num">{{ b.rows }}</td><td class="right"><a class="btn sm" href="#/imports">Review</a></td></tr></tbody></table></div>
    </div>
  </div>`,
};

export const AuditPage = {
  components: common,
  setup() {
    const rows = ref([]);
    const loading = ref(false);
    const f = ref({ object_type: '', q: '' });
    async function load() {
      loading.value = true;
      try {
        const qs = new URLSearchParams({ limit: 5000 });
        if (f.value.object_type) qs.set('object_type', f.value.object_type);
        if (f.value.q) qs.set('q', f.value.q);
        rows.value = await get('/api/audit?' + qs.toString());
      } catch (e) { showError(e); } finally { loading.value = false; }
    }
    onMounted(load);
    const show = (v) => v === null || v === undefined ? '—' : (typeof v === 'object' ? JSON.stringify(v) : String(v));
    const cols = [
      { key: 'at', label: 'Timestamp', format: (v) => dateTime(v) }, { key: 'username', label: 'User' }, { key: 'action', label: 'Action' },
      { key: 'object_type', label: 'Object' }, { key: 'object_label', label: 'Reference' }, { key: 'field', label: 'Field' },
      { key: 'old_value', label: 'Old value', wrap: true, format: show }, { key: 'new_value', label: 'New value', wrap: true, format: show },
      { key: 'reason', label: 'Reason', wrap: true }, { key: 'approval_status', label: 'Approval status' },
    ];
    const TYPES = ['Lease', 'LeaseEvent', 'LeaseAssessment', 'Document', 'DiscountRate', 'FxRate', 'ImportBatch', 'ReportingPeriod', 'Settings', 'GLMapping', 'User', 'Company', 'Report', 'Journals', 'Disclosure', 'System'];
    function exp(fmt) { download('/api/reports/audit_trail/export?format=' + fmt, 'audit_trail.' + fmt); }
    return { rows, loading, f, load, cols, TYPES, exp };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>Audit trail</h1><div class="sub">Append-only log: who changed what, when, old and new values, reason and approval status — including logins, exports and cloud-AI consents.</div></div>
      <button class="btn" @click="exp('xlsx')"><AppIcon name="file-spreadsheet" :size="14"/> Excel</button><button class="btn" @click="exp('pdf')"><AppIcon name="printer" :size="14"/> PDF</button></div>
    <div class="card">
      <DataTable id="audit" :columns="cols" :rows="rows" :loading="loading" :page-size="50" row-key="id">
        <template #toolbar>
          <select v-model="f.object_type" @change="load" style="width:170px;min-height:30px"><option value="">All objects</option><option v-for="t in TYPES" :key="t">{{ t }}</option></select>
        </template>
      </DataTable>
    </div>
  </div>`,
};
