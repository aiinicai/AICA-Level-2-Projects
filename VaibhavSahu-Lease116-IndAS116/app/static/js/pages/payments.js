// Portfolio payment calendar — scheduled lease payments (and lessor receipts) in a date window
import { store, get, showError } from '../store.js';
import { common } from '../components.js';
import { money, date, monthEnd, addMonths, decAdd, titleCase } from '../util.js';
import { monLabel } from './dashboard.js';
import { catLabel } from './lease_forms.js';

const { ref, computed, watch, onMounted } = Vue;

export const PaymentsPage = {
  components: common,
  setup() {
    const base = store.asOf || new Date().toISOString().slice(0, 10);
    const f = ref({ start: base.slice(0, 8) + '01', end: monthEnd(addMonths(base.slice(0, 8) + '01', 2)), direction: '' });
    const rows = ref([]);
    const loading = ref(false);
    async function load() {
      loading.value = true;
      try {
        const qs = new URLSearchParams({ start: f.value.start, end: f.value.end });
        if (store.entityId) qs.set('entity_id', store.entityId);
        rows.value = (await get('/api/payments?' + qs.toString())).rows;
      } catch (e) { showError(e); } finally { loading.value = false; }
    }
    onMounted(load);
    watch(() => store.entityId, load);
    const list = computed(() => rows.value.filter(r => !f.value.direction || r.direction === f.value.direction));
    const fc = computed(() => store.company?.functional_currency || 'INR');
    const pay = computed(() => list.value.filter(r => r.direction === 'Payment' && (r.currency || fc.value) === fc.value));
    const kpi = computed(() => ({
      total: decAdd(...pay.value.map(r => r.total)), lease: decAdd(...pay.value.map(r => r.lease_amount)),
      nonlease: decAdd(...pay.value.map(r => r.non_lease_amount)),
      variable: decAdd(...pay.value.filter(r => r.category === 'VARIABLE').map(r => r.total)),
      receipts: decAdd(...list.value.filter(r => r.direction === 'Receipt' && (r.currency || fc.value) === fc.value).map(r => r.total)),
      fcy: list.value.filter(r => (r.currency || fc.value) !== fc.value).length,
    }));
    const byMonth = computed(() => {
      const m = {};
      pay.value.forEach(r => { const k = monthEnd(r.date); m[k] = decAdd(m[k] || '0', r.total); });
      const keys = Object.keys(m).sort();
      return { labels: keys.map(monLabel), values: keys.map(k => m[k]) };
    });
    const cols = [
      { key: 'date', label: 'Due date', type: 'date' }, { key: 'lease_code', label: 'Lease' }, { key: 'counterparty', label: 'Counterparty' },
      { key: 'description', label: 'Lease description', wrap: true, hidden: true }, { key: 'line_description', label: 'Line', wrap: true },
      { key: 'category', label: 'Category', format: (v) => catLabel(v) }, { key: 'currency', label: 'Ccy' },
      { key: 'lease_amount', label: 'Lease component', type: 'money' }, { key: 'non_lease_amount', label: 'Non-lease', type: 'money', zeroDash: true },
      { key: 'total', label: 'Total', type: 'money' }, { key: 'included', label: 'In liability?' }, { key: 'direction', label: 'Type' },
      { key: 'status', label: 'Lease status' },
    ];
    const totals = computed(() => ({ lease_amount: decAdd(...list.value.map(r => r.lease_amount)), non_lease_amount: decAdd(...list.value.map(r => r.non_lease_amount)), total: decAdd(...list.value.map(r => r.total)) }));
    function open(r) { location.hash = '#/leases/' + r.lease_id + '?tab=payments'; }
    function preset(n) { const s = base.slice(0, 8) + '01'; f.value.start = s; f.value.end = monthEnd(addMonths(s, n - 1)); load(); }
    return { store, f, rows, list, loading, load, kpi, byMonth, cols, totals, open, preset, fc, money, date, titleCase };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>Payments</h1><div class="sub">Scheduled lease payments from the latest calculation (after modifications), with the liability-inclusion decision for each line.</div></div></div>
    <div class="card mb"><div class="card-body row wrap" style="align-items:flex-end">
      <label class="field" style="width:160px">From<input type="date" v-model="f.start"></label><label class="field" style="width:160px">To<input type="date" v-model="f.end"></label>
      <button class="btn" @click="load"><AppIcon name="refresh-cw" :size="14"/> Apply</button>
      <button class="btn ghost" @click="preset(1)">This month</button><button class="btn ghost" @click="preset(3)">Next 3 months</button><button class="btn ghost" @click="preset(12)">Next 12 months</button>
      <div class="spacer"></div>
      <label class="field" style="width:160px">Show<select v-model="f.direction"><option value="">Payments and receipts</option><option value="Payment">Payments (lessee)</option><option value="Receipt">Receipts (lessor)</option></select></label>
    </div></div>
    <div class="grid c4 mb">
      <Kpi label="Payments due in window" :value="kpi.total" money :foot="'Lease ' + money(kpi.lease) + ' · non-lease ' + money(kpi.nonlease)"/>
      <Kpi label="Variable payments (expected)" :value="kpi.variable" money foot="Excluded from liabilities (38(b))"/>
      <Kpi label="Lessor receipts" :value="kpi.receipts" money/>
      <Kpi label="Lines" :value="list.length" :foot="kpi.fcy ? kpi.fcy + ' foreign-currency line(s) excluded from totals' : 'All in ' + fc"/>
    </div>
    <div class="card mb" v-if="byMonth.labels.length > 1"><div class="card-head"><h3>Payments by month</h3><span class="sub">{{ fc }} leases</span></div><div class="card-body"><BarChart :labels="byMonth.labels" :values="byMonth.values" value-label="Payments" :height="200"/></div></div>
    <div class="card"><DataTable id="payments" :columns="cols" :rows="list" :loading="loading" clickable @row-click="open" :totals="totals" :page-size="50" row-key="__none">
      <template #cell-lease_code="{ row }"><b>{{ row.lease_code }}</b></template>
      <template #cell-included="{ row }"><span v-if="row.included===true" class="badge ok">Included</span><span v-else-if="row.included===false" class="badge draft" :title="row.inclusion_reason">Excluded</span><span v-else class="muted small" :title="row.inclusion_reason">n/a</span></template>
      <template #cell-status="{ row }"><StatusBadge :status="row.status"/></template>
    </DataTable></div>
  </div>`,
};
