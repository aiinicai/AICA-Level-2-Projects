// Portfolio dashboard
import { store, get, post, toast, showError, confirmDialog } from '../store.js';
import { common } from '../components.js';
import { money, date, unitLabel } from '../util.js';

const { ref, computed, watch, onMounted } = Vue;

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export function bucketLabel(k) {
  if (k.startsWith('>')) return 'More than ' + k.slice(1) + ' yrs';
  const [a, b] = k.split('-');
  return a === '0' ? 'Within ' + b + ' yr' + (b === '1' ? '' : 's') : a + '–' + b + ' yrs';
}
export function monLabel(iso) { const [y, m] = iso.split('-'); return MONTHS[Number(m) - 1] + '-' + y.slice(2); }

export const DashboardPage = {
  components: common,
  setup() {
    const d = ref(null);
    const loading = ref(true);
    const alertTab = ref('expiring');
    async function load() {
      loading.value = true;
      try {
        const qs = new URLSearchParams({ as_of: store.asOf || '' });
        if (store.entityId) qs.set('entity_id', store.entityId);
        d.value = await get('/api/dashboard?' + qs.toString());
      } catch (e) { showError(e); } finally { loading.value = false; }
    }
    async function demo() {
      const ok = await confirmDialog('Load demonstration data',
        'Creates a DEMO entity with 12 illustrative leases (office, warehouse, vehicle, retail with impairment, USD lease, short-term, low-value, terminated branch, sale and leaseback; and as lessor: an operating lease with an interest-free deposit and a modification, and a finance lease with an expected-credit-loss allowance) and demo users.\n\nUse only in a practice workspace — not in a client database.', { ok: 'Load demo data' });
      if (!ok) return;
      try { const r = await post('/api/system/demo-data'); toast(`Demo data loaded (${r.created} leases)`, 'ok'); await window.__lease116.boot(); load(); }
      catch (e) { showError(e); }
    }
    onMounted(load);
    watch(() => [store.asOf, store.entityId], load);
    const k = computed(() => d.value?.kpis || {});
    const charts = computed(() => d.value?.charts || {});
    const maturity = computed(() => {
      const m = charts.value.maturity || {};
      const keys = Object.keys(m);
      return { labels: keys.map(bucketLabel), values: keys.map(x => m[x]) };
    });
    const byClass = computed(() => {
      const m = charts.value.rou_by_class || {};
      const keys = Object.keys(m).sort((a, b) => Number(m[b]) - Number(m[a]));
      return { labels: keys, values: keys.map(x => m[x]) };
    });
    const byMonth = computed(() => {
      const m = charts.value.payments_by_month || {};
      const keys = Object.keys(m).sort();
      return { labels: keys.map(monLabel), values: keys.map(x => m[x]) };
    });
    const al = computed(() => d.value?.alerts || {});
    const alertTabs = computed(() => {
      const a = al.value;
      const exp = (a.expiring?.['3']?.length || 0) + (a.expiring?.['6']?.length || 0) + (a.expiring?.['12']?.length || 0);
      return [
        { key: 'expiring', label: 'Expiring', count: exp },
        { key: 'renewals', label: 'Renewal options', count: (a.renewals_due || []).length },
        { key: 'events', label: 'Pending events', count: (a.upcoming_modifications || []).length },
        { key: 'unapproved', label: 'Unapproved', count: (a.unapproved || []).length },
        { key: 'rates', label: 'Missing rates', count: (a.missing_discount_rates || []).length },
        { key: 'contracts', label: 'Missing contracts', count: (a.missing_contracts || []).length },
        { key: 'exceptions', label: 'Exceptions', count: (a.exceptions || []).length },
      ];
    });
    const expiringRows = computed(() => {
      const e = al.value.expiring || {};
      return ['3', '6', '12'].flatMap(m => (e[m] || []).map(x => ({ ...x, window: 'Within ' + m + ' months' })));
    });
    const empty = computed(() => d.value && !d.value.kpis.total_leases);
    const lz = computed(() => d.value?.lessor || { count: 0, kpis: {} });
    const lMat = computed(() => ({ labels: (lz.value.maturity || []).map(m => m.bucket), values: (lz.value.maturity || []).map(m => m.amount) }));
    const lInc = computed(() => {
      const m = lz.value.income_by_month || {};
      const keys = Object.keys(m).sort();
      return { labels: keys.map(monLabel), values: keys.map(x => m[x]) };
    });
    const go = (h) => { location.hash = h; };
    return { go, store, d, loading, load, k, maturity, byClass, byMonth, al, alertTab, alertTabs, expiringRows, empty, demo, money, date, unitLabel,
      lz, lMat, lInc };
  },
  template: `
  <div>
    <div class="page-head">
      <div class="grow">
        <h1>Lease portfolio</h1>
        <div class="sub">Position as of {{ date(store.asOf) }}<span v-if="d"> · FY {{ date(d.fy[0]) }} – {{ date(d.fy[1]) }}</span> · amounts in {{ unitLabel() }} (functional currency) · approved runs, else latest draft</div>
      </div>
      <button class="btn" @click="load"><AppIcon name="refresh-cw" :size="14"/> Refresh</button>
      <a class="btn primary" href="#/new" v-if="store.can('lease.write')"><AppIcon name="file-plus" :size="14"/> New lease</a>
    </div>
    <div v-if="loading && !d" class="progress"><i></i></div>
    <template v-if="d">
      <div v-if="empty" class="card mb"><div class="card-body">
        <Empty icon="file-text" text="No leases yet. Upload a lease agreement for the AI reader, enter a lease manually, or import a lease register.">
          <div class="row" style="justify-content:center;margin-top:12px">
            <a class="btn primary" href="#/new"><AppIcon name="sparkles" :size="14"/> Read an agreement</a>
            <a class="btn" href="#/imports"><AppIcon name="upload" :size="14"/> Import register</a>
            <button class="btn" v-if="store.can('settings.write')" @click="demo"><AppIcon name="database" :size="14"/> Load demo data</button>
          </div>
        </Empty>
      </div></div>
      <div class="grid c4 mb">
        <Kpi label="Lease liabilities" icon="landmark" :value="k.total_liability" money :foot="'Current ' + money(k.current_liability) + ' · Non-current ' + money(k.noncurrent_liability)"/>
        <Kpi label="Right-of-use assets (NBV)" icon="building-2" :value="k.total_rou" money foot="Net of depreciation and impairment"/>
        <Kpi label="Interest expense — FY to date" icon="percent" :value="k.interest_ytd" money foot="Finance cost on lease liabilities"/>
        <Kpi label="Depreciation — FY to date" icon="trending-down" :value="k.depreciation_ytd" money foot="ROU asset depreciation"/>
      </div>
      <div class="grid c4 mb">
        <Kpi label="Lease cash outflow — this month" icon="wallet" :value="k.payments_this_month" money foot="Incl. variable and non-lease components"/>
        <Kpi label="Active leases" icon="file-text" :value="k.active_leases + ' / ' + k.total_leases" :foot="k.exempt_leases + ' exempt (short-term / low-value)'"/>
        <Kpi label="Awaiting approval" icon="circle-check" :value="(al.unapproved || []).length" foot="Leases without an approved calculation" :onclick="() => go('#/approvals')"/>
        <Kpi label="Exceptions" icon="triangle-alert" :value="(al.exceptions || []).length + (al.missing_discount_rates || []).length" foot="Calculation warnings and missing inputs" :onclick="() => go('#/reports/exceptions')"/>
      </div>
      <div class="grid c2 mb">
        <div class="card"><div class="card-head"><h3>Maturity analysis — undiscounted lease payments</h3><span class="sub">Ind AS 116.58 · Ind AS 107.39</span></div>
          <div class="card-body"><BarChart :labels="maturity.labels" :values="maturity.values" value-label="Undiscounted payments" :height="230"/></div></div>
        <div class="card"><div class="card-head"><h3>ROU assets by class</h3><span class="sub">Carrying amount · 53(j)</span></div>
          <div class="card-body"><BarChart :labels="byClass.labels" :values="byClass.values" horizontal value-label="ROU carrying amount" :height="230"/></div></div>
      </div>
      <div class="grid side mb">
        <div class="card"><div class="card-head"><h3>Lease cash outflow by month</h3><span class="sub">Past 12 and next 12 months</span></div>
          <div class="card-body"><BarChart :labels="byMonth.labels" :values="byMonth.values" value-label="Cash outflow" :height="240"/></div></div>
        <div class="card"><div class="card-head"><h3>Liability split</h3></div>
          <div class="card-body">
            <div class="small muted mb-sm">By entity</div>
            <div class="stat-line" v-for="(v, key) in (d.charts.liability_by_entity || {})" :key="'e'+key"><span>{{ key }}</span><span class="num">{{ money(v) }}</span></div>
            <div class="small muted mb-sm mt">By currency of the lease (restated in functional currency)</div>
            <div class="stat-line" v-for="(v, key) in (d.charts.liability_by_currency || {})" :key="'c'+key"><span>{{ key }}</span><span class="num">{{ money(v) }}</span></div>
            <div class="stat-line total"><span>Total</span><span class="num">{{ money(k.total_liability) }}</span></div>
          </div></div>
      </div>
      <template v-if="lz.count">
        <div class="row mb" style="margin-top:6px"><h2 class="grow" style="font-size:16px;margin:0">Leases where we are the lessor</h2>
          <span class="small muted">{{ lz.active }} active · {{ lz.finance_leases }} finance · {{ lz.operating_leases }} operating (incl. subleases)</span>
          <a class="btn sm" href="#/leases?role=LESSOR">Open lessor leases</a></div>
        <div class="grid c4 mb">
          <Kpi label="Net investment in finance leases" icon="landmark" :value="lz.kpis.net_investment" money :foot="'Current ' + money(lz.kpis.ni_current) + (Number(lz.kpis.loss_allowance) ? ' · loss allowance ' + money(lz.kpis.loss_allowance) : '')"/>
          <Kpi label="Operating lease income — FY to date" icon="trending-up" :value="lz.kpis.operating_income_ytd" money foot="Straight-line (Ind AS 116.81)"/>
          <Kpi label="Finance income — FY to date" icon="percent" :value="lz.kpis.finance_income_ytd" money :foot="Number(lz.kpis.variable_income_ytd) ? 'Variable income ' + money(lz.kpis.variable_income_ytd) : 'Constant periodic rate (para 75)'"/>
          <Kpi label="Lease payments billed — this month" icon="wallet" :value="lz.kpis.receipts_this_month" money :foot="'Deposits held ' + money(lz.kpis.deposits_received) + ' · accrued income ' + money(lz.kpis.accrued_income)"/>
        </div>
        <div class="grid c2 mb">
          <div class="card"><div class="card-head"><h3>Undiscounted lease payments to be received</h3><span class="sub">Ind AS 116.94 / 97</span></div>
            <div class="card-body"><BarChart :labels="lMat.labels" :values="lMat.values" value-label="Undiscounted receipts" :height="220"/></div></div>
          <div class="card"><div class="card-head"><h3>Lease income by month</h3><span class="sub">Finance, straight-line and variable income · past 12 and next 12 months</span></div>
            <div class="card-body"><BarChart :labels="lInc.labels" :values="lInc.values" value-label="Lease income" :height="220"/></div></div>
        </div>
      </template>
      <div class="card">
        <div class="card-head"><h3>Alerts and follow-ups</h3></div>
        <div class="card-body" style="padding-top:4px">
          <Tabs :tabs="alertTabs" v-model="alertTab"/>
          <table class="t compact" v-if="alertTab==='expiring'">
            <thead><tr><th>Lease</th><th>Description</th><th>Lease term ends</th><th>Window</th></tr></thead>
            <tbody><tr v-if="!expiringRows.length"><td colspan="4" class="empty">No leases expire in the next 12 months.</td></tr>
              <tr v-for="r in expiringRows" :key="r.id"><td><a :href="'#/leases/' + r.id">{{ r.lease_code }}</a></td><td>{{ r.description }}</td><td>{{ date(r.term_end) }}</td><td>{{ r.window }}</td></tr></tbody>
          </table>
          <table class="t compact" v-if="alertTab==='renewals'">
            <thead><tr><th>Lease</th><th>Option</th><th>Exercise date</th><th>Reasonably certain?</th></tr></thead>
            <tbody><tr v-if="!(al.renewals_due||[]).length"><td colspan="4" class="empty">No extension options fall due in the next 12 months.</td></tr>
              <tr v-for="r in al.renewals_due" :key="r.id + r.exercise_date"><td><a :href="'#/leases/' + r.id">{{ r.lease_code }}</a></td><td>{{ r.description }}</td><td>{{ date(r.exercise_date) }}</td>
                <td><span class="badge" :class="r.reasonably_certain === null ? 'warn' : 'info'">{{ r.reasonably_certain === true ? 'Yes' : r.reasonably_certain === false ? 'No' : 'Not assessed' }}</span></td></tr></tbody>
          </table>
          <table class="t compact" v-if="alertTab==='events'">
            <thead><tr><th>Lease</th><th>Event</th><th>Effective</th><th>Status</th></tr></thead>
            <tbody><tr v-if="!(al.upcoming_modifications||[]).length"><td colspan="4" class="empty">No events awaiting approval.</td></tr>
              <tr v-for="(r, i) in al.upcoming_modifications" :key="i"><td><a :href="'#/leases/' + r.id">{{ r.lease_code }}</a></td><td>{{ r.event }}</td><td>{{ date(r.effective_date) }}</td><td><StatusBadge :status="r.status"/></td></tr></tbody>
          </table>
          <table class="t compact" v-if="alertTab==='unapproved'">
            <thead><tr><th>Lease</th><th>Calculation status</th></tr></thead>
            <tbody><tr v-if="!(al.unapproved||[]).length"><td colspan="2" class="empty">All calculations are approved.</td></tr>
              <tr v-for="r in al.unapproved" :key="r.id"><td><a :href="'#/leases/' + r.id">{{ r.lease_code }}</a></td><td><StatusBadge :status="r.status"/></td></tr></tbody>
          </table>
          <table class="t compact" v-if="alertTab==='rates'">
            <thead><tr><th>Lease</th><th>Description</th></tr></thead>
            <tbody><tr v-if="!(al.missing_discount_rates||[]).length"><td colspan="2" class="empty">Every capitalised lease has a discount rate.</td></tr>
              <tr v-for="r in al.missing_discount_rates" :key="r.id"><td><a :href="'#/leases/' + r.id">{{ r.lease_code }}</a></td><td>{{ r.description }}</td></tr></tbody>
          </table>
          <table class="t compact" v-if="alertTab==='contracts'">
            <thead><tr><th>Lease</th><th>Description</th></tr></thead>
            <tbody><tr v-if="!(al.missing_contracts||[]).length"><td colspan="2" class="empty">Every lease has a document attached.</td></tr>
              <tr v-for="r in al.missing_contracts" :key="r.id"><td><a :href="'#/leases/' + r.id">{{ r.lease_code }}</a></td><td>{{ r.description }}</td></tr></tbody>
          </table>
          <table class="t compact" v-if="alertTab==='exceptions'">
            <thead><tr><th>Lease</th><th>Issues</th><th>First issue</th></tr></thead>
            <tbody><tr v-if="!(al.exceptions||[]).length"><td colspan="3" class="empty">No calculation warnings.</td></tr>
              <tr v-for="r in al.exceptions" :key="r.id"><td><a :href="'#/leases/' + r.id">{{ r.lease_code }}</a></td><td class="num">{{ r.count }}</td><td class="wrap">{{ r.first }}</td></tr></tbody>
          </table>
        </div>
      </div>
    </template>
  </div>`,
};
