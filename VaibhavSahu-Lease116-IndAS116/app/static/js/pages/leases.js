// Lease register
import { store, get, download, showError } from '../store.js';
import { common } from '../components.js';
import { money, date, num } from '../util.js';

const { ref, computed, watch, onMounted } = Vue;

export const TYPE_LABELS = {
  STANDARD: 'Capitalised (lessee)', SHORT_TERM: 'Short-term — exempt', LOW_VALUE: 'Low-value — exempt',
  SUBLEASE: 'Sublease (intermediate lessor)', SALE_LEASEBACK: 'Sale and leaseback', LESSOR: 'Lessor',
};
export function typeLabel(row) {
  if (row.role === 'LESSOR' && row.lease_type !== 'SUBLEASE') {
    const c = row.classification;
    return c === 'FINANCE' ? 'Lessor — finance lease' : c === 'OPERATING' ? 'Lessor — operating lease' : c === 'ENDED' ? 'Lessor — terminated' : 'Lessor';
  }
  return TYPE_LABELS[row.lease_type] || row.lease_type || '—';
}
export const STATUSES = ['Draft', 'Prepared', 'Under Review', 'Approved', 'Posted', 'Modified', 'Terminated', 'Archived'];

export const LeasesPage = {
  components: common,
  props: { route: Object },
  setup(props) {
    const rows = ref([]);
    const loading = ref(false);
    const f = ref({ status: props.route?.query?.status || '', asset_class: '', lease_type: '', role: props.route?.query?.role || '' });
    async function load() {
      loading.value = true;
      try {
        const qs = new URLSearchParams({ page_size: 5000, status: f.value.status === 'Archived' ? 'Archived' : '' });
        if (store.entityId) qs.set('entity_id', store.entityId);
        const r = await get('/api/leases?' + qs.toString());
        rows.value = r.rows.map(x => ({ ...x, type_label: typeLabel(x), term_end: x.term_end || x.contract_end }));
      } catch (e) { showError(e); } finally { loading.value = false; }
    }
    onMounted(load);
    watch(() => store.entityId, load);
    watch(() => f.value.status, (n, o) => { if (n === 'Archived' || o === 'Archived') load(); });
    const filtered = computed(() => rows.value.filter(r =>
      (!f.value.status || r.status === f.value.status) && (!f.value.asset_class || r.asset_class === f.value.asset_class) &&
      (!f.value.lease_type || r.type_label === f.value.lease_type) && (!f.value.role || (r.role || 'LESSEE') === f.value.role)));
    const classes = computed(() => [...new Set(rows.value.map(r => r.asset_class).filter(Boolean))].sort());
    const types = computed(() => [...new Set(rows.value.map(r => r.type_label))].sort());
    const columns = [
      { key: 'lease_code', label: 'Lease ID', cls: 'nowrap' },
      { key: 'description', label: 'Description', wrap: true },
      { key: 'lessor', label: 'Counterparty' },
      { key: 'asset_class', label: 'Asset class' },
      { key: 'entity_code', label: 'Entity', hidden: true },
      { key: 'role', label: 'Role', format: (v) => v === 'LESSOR' ? 'Lessor' : 'Lessee' },
      { key: 'type_label', label: 'Accounting' },
      { key: 'location', label: 'Location', hidden: true },
      { key: 'cost_centre', label: 'Cost centre', hidden: true },
      { key: 'commencement_date', label: 'Commencement', type: 'date' },
      { key: 'term_end', label: 'Lease term end', type: 'date' },
      { key: 'term_months', label: 'Term (months)', type: 'num', format: (v) => v ? num(v, 1) : '—', hidden: true },
      { key: 'currency', label: 'Ccy' },
      { key: 'discount_rate_pct', label: 'Rate %', type: 'rate', format: (v) => v ? num(v, 2) : '—' },
      { key: 'initial_liability', label: 'Initial liability', type: 'money' },
      { key: 'liability_now', label: 'Liability (latest period)', type: 'money' },
      { key: 'rou_now', label: 'ROU NBV (latest period)', type: 'money' },
      { key: 'net_investment_now', label: 'Net investment (lessor)', type: 'money' },
      { key: 'accrued_income_now', label: 'Accrued / (deferred) income (lessor)', type: 'money', hidden: true },
      { key: 'status', label: 'Status' },
      { key: 'calc_status', label: 'Calculation' },
      { key: 'flags_count', label: 'Judgments', type: 'num' },
    ];
    const totals = computed(() => {
      const inr = filtered.value.filter(r => (r.currency || 'INR') === (store.company?.functional_currency || 'INR'));
      const s = (k) => inr.reduce((a, r) => a + Number(r[k] || 0), 0).toFixed(2);
      return { initial_liability: s('initial_liability'), liability_now: s('liability_now'), rou_now: s('rou_now'), net_investment_now: s('net_investment_now'),
        accrued_income_now: s('accrued_income_now') };
    });
    const fcyCount = computed(() => filtered.value.filter(r => (r.currency || 'INR') !== (store.company?.functional_currency || 'INR')).length);
    function open(r) { location.hash = '#/leases/' + r.id; }
    function exportAs(fmt) {
      const qs = new URLSearchParams({ format: fmt, as_of: store.asOf || '' });
      if (store.entityId) qs.set('entity_id', store.entityId);
      if (f.value.status) qs.set('status', f.value.status);
      if (f.value.asset_class) qs.set('asset_class', f.value.asset_class);
      if (f.value.role) qs.set('role', f.value.role);
      download('/api/reports/lease_register/export?' + qs.toString(), 'Lease_register.' + fmt);
    }
    return { store, rows, loading, f, filtered, classes, types, columns, totals, fcyCount, open, exportAs, load, STATUSES, money, date };
  },
  template: `
  <div>
    <div class="page-head">
      <div class="grow"><h1>Lease register</h1><div class="sub">All leases in the workspace — click a lease to open its schedules, judgments, journals and audit trail.</div></div>
      <a class="btn" href="#/imports" v-if="store.can('import.write')"><AppIcon name="upload" :size="14"/> Import</a>
      <a class="btn primary" href="#/new" v-if="store.can('lease.write')"><AppIcon name="file-plus" :size="14"/> New lease</a>
    </div>
    <div class="card">
      <DataTable id="leases" :columns="columns" :rows="filtered" :loading="loading" clickable @row-click="open" :totals="totals" export-name="Lease register" @export="exportAs" :page-size="25">
        <template #toolbar>
          <select v-model="f.role" style="width:140px;min-height:30px" aria-label="Role"><option value="">Lessee and lessor</option><option value="LESSEE">Lessee only</option><option value="LESSOR">Lessor only</option></select>
          <select v-model="f.status" style="width:150px;min-height:30px" aria-label="Status"><option value="">All statuses</option><option v-for="s in STATUSES" :key="s">{{ s }}</option></select>
          <select v-model="f.asset_class" style="width:170px;min-height:30px" aria-label="Asset class"><option value="">All asset classes</option><option v-for="c in classes" :key="c">{{ c }}</option></select>
          <select v-model="f.lease_type" style="width:200px;min-height:30px" aria-label="Accounting"><option value="">All accounting types</option><option v-for="t in types" :key="t">{{ t }}</option></select>
        </template>
        <template #cell-lease_code="{ row }"><b>{{ row.lease_code }}</b></template>
        <template #cell-status="{ row }"><StatusBadge :status="row.status"/></template>
        <template #cell-calc_status="{ row }"><StatusBadge v-if="row.calc_status" :status="row.calc_status"/><span v-else class="muted small">Not calculated</span></template>
        <template #cell-flags_count="{ row }"><span v-if="row.flags_count" class="badge warn">{{ row.flags_count }}</span><span v-else class="muted">–</span></template>
        <template #cell-lessor="{ row }">{{ row.lessor || '—' }}<span v-if="row.related_party" class="badge info" style="margin-left:4px">RP</span></template>
      </DataTable>
    </div>
    <div class="small muted mt" v-if="fcyCount">Totals include functional-currency leases only; {{ fcyCount }} foreign-currency lease(s) are shown in their contract currency (see the FX report for restated amounts).</div>
  </div>`,
};
