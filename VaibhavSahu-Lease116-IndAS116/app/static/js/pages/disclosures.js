// Financial statement disclosures (Ind AS 116.47–60, 89–97; Ind AS 7.44A–E) — portfolio level
import { store, get, download, showError } from '../store.js';
import { common } from '../components.js';
import { money, date, num, fyOf, decAdd, monthEnd, addDays } from '../util.js';

const { ref, computed, watch, onMounted } = Vue;

const ROU_LINES = [
  { k: 'opening_nbv', l: 'Carrying amount at the beginning of the period', b: true },
  { k: 'additions', l: 'Additions (53(h))' },
  { k: 'remeasurement_modification', l: 'Remeasurements and modifications' },
  { k: 'derecognition', l: 'Derecognition / terminations', neg: true },
  { k: 'depreciation', l: 'Depreciation charge (53(a))', neg: true },
  { k: 'impairment', l: 'Impairment loss / (reversal)', neg: true },
  { k: 'closing_nbv', l: 'Carrying amount at the end of the period (53(j))', b: true },
  { k: 'closing_gross', l: 'Gross carrying amount', sub: true },
  { k: 'closing_acc_dep_imp', l: 'Accumulated depreciation and impairment', sub: true },
];

export const DisclosuresPage = {
  components: common,
  setup() {
    // disclosures are prepared at a period end: default to the last month-end on or before the 'As of' date
    const asOf = store.asOf || new Date().toISOString().slice(0, 10);
    const lastMe = monthEnd(asOf) === asOf ? asOf : addDays(asOf.slice(0, 8) + '01', -1);
    const [fs, fe] = fyOf(lastMe, store.company?.fy_start_month || 4);
    const f = ref({ start: fs, end: lastMe < fe ? lastMe : fe });
    const notMonthEnd = computed(() => f.value.end && monthEnd(f.value.end) !== f.value.end);
    const d = ref(null);
    const loading = ref(false);
    async function load() {
      loading.value = true;
      try {
        const qs = new URLSearchParams({ start: f.value.start, end: f.value.end });
        if (store.entityId) qs.set('entity_id', store.entityId);
        d.value = await get('/api/disclosures?' + qs.toString());
      } catch (e) { showError(e); } finally { loading.value = false; }
    }
    onMounted(load);
    watch(() => store.entityId, load);
    const classes = computed(() => (d.value?.rou_movement || []).filter(r => r.asset_class !== 'Total'));
    const totalRow = computed(() => (d.value?.rou_movement || []).find(r => r.asset_class === 'Total') || {});
    const lm = computed(() => d.value?.liability_movement || {});
    const mat = computed(() => d.value?.maturity || { rows: [] });
    const reconciles = computed(() => Number(totalRow.value.reconciliation_difference || 0) === 0 && Number(lm.value.reconciliation_difference || 0) === 0);
    function exp() {
      const qs = new URLSearchParams({ start: f.value.start, end: f.value.end });
      if (store.entityId) qs.set('entity_id', store.entityId);
      download('/api/disclosures/export?' + qs.toString(), 'Lease_note.xlsx');
    }
    const neg = (v) => (v === null || v === undefined ? v : (String(v).startsWith('-') ? String(v).slice(1) : (Number(v) ? '-' + v : v)));
    const i7 = computed(() => d.value?.ind_as_7 || {});
    const lessor = computed(() => d.value?.lessor || {});
    const hasLessor = computed(() => !!lessor.value.count);
    const lmv = computed(() => lessor.value.net_investment_movement || {});
    const lrc = computed(() => lessor.value.reconciliation || null);
    const lpr = computed(() => lessor.value.presentation || {});
    return { store, f, d, loading, load, classes, totalRow, lm, mat, reconciles, exp, ROU_LINES, neg, i7, lessor, hasLessor, lmv, lrc, lpr, notMonthEnd, money, date, num, decAdd };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>Lease disclosures</h1><div class="sub">Draft note to the financial statements — computed from approved calculation runs (latest drafts where not yet approved). Qualitative disclosures are prompts for management, never invented.</div></div>
      <button class="btn" v-if="store.can('export')" @click="exp"><AppIcon name="file-spreadsheet" :size="14"/> Export note (Excel)</button></div>
    <div class="card mb"><div class="card-body row wrap">
      <label class="field" style="width:160px">Period from<input type="date" v-model="f.start"></label><label class="field" style="width:160px">Period to<input type="date" v-model="f.end"></label>
      <button class="btn" style="align-self:end" @click="load"><AppIcon name="refresh-cw" :size="14"/> Apply</button>
      <div class="spacer"></div>
      <div v-if="d" class="alert" :class="reconciles ? 'ok' : 'bad'" style="align-self:end"><AppIcon :name="reconciles ? 'circle-check' : 'circle-x'"/><div>{{ reconciles ? 'Movements reconcile to closing balances' : 'Reconciliation difference — investigate before use' }}</div></div>
    </div></div>
    <div v-if="notMonthEnd" class="alert warn mb"><AppIcon name="triangle-alert"/><div class="grow">'Period to' is not a month-end. Schedules close at month-ends, so the balance-sheet presentation and the maturity analyses are only produced at a month-end — choose the reporting date (e.g. 31-Mar).</div></div>
    <div v-if="loading && !d" class="progress"><i></i></div>
    <template v-if="d">
      <div class="card mb"><div class="card-head"><h3>(a) Right-of-use assets — movement by class of underlying asset</h3><span class="sub">Ind AS 116.53(a), (h), (j); Schedule III</span></div>
        <div class="table-wrap"><table class="t">
          <thead><tr><th>Particulars</th><th class="num" v-for="c in classes" :key="c.asset_class">{{ c.asset_class }}</th><th class="num">Total</th></tr></thead>
          <tbody><tr v-for="ln in ROU_LINES" :key="ln.k" :class="ln.b ? 'total' : ''"><td :style="ln.sub ? 'padding-left:24px;color:var(--text-2)' : ''">{{ ln.l }}</td>
            <td class="num" v-for="c in classes" :key="c.asset_class">{{ ln.neg ? money(neg(c[ln.k])) : money(c[ln.k]) }}</td><td class="num">{{ ln.neg ? money(neg(totalRow[ln.k])) : money(totalRow[ln.k]) }}</td></tr>
            <tr><td class="small muted">Reconciliation difference (should be nil)</td><td class="num small" v-for="c in classes" :key="c.asset_class" :class="Number(c.reconciliation_difference) ? 'neg' : 'muted'">{{ money(c.reconciliation_difference) }}</td><td class="num small">{{ money(totalRow.reconciliation_difference) }}</td></tr></tbody></table></div></div>

      <div class="grid c2 mb">
        <div class="card"><div class="card-head"><h3>(b) Lease liabilities — movement</h3><span class="sub">Ind AS 7.44A–44E reconciliation</span></div><div class="card-body">
          <div class="stat-line total" style="border-top:0"><span>Opening balance</span><span class="num">{{ money(lm.opening) }}</span></div>
          <div class="stat-line"><span>Additions (new leases)</span><span class="num">{{ money(lm.additions) }}</span></div>
          <div class="stat-line"><span>Finance cost accrued (53(b))</span><span class="num">{{ money(lm.interest) }}</span></div>
          <div class="stat-line"><span>Payment of lease liabilities (principal + interest)</span><span class="num">({{ money(lm.payments) }})</span></div>
          <div class="stat-line"><span>Remeasurements and modifications</span><span class="num">{{ money(lm.remeasurement_modification) }}</span></div>
          <div class="stat-line"><span>Derecognition / terminations</span><span class="num">({{ money(lm.derecognition) }})</span></div>
          <div class="stat-line" v-if="Number(lm.fx)"><span>Exchange differences</span><span class="num">{{ money(lm.fx) }}</span></div>
          <div class="stat-line total"><span>Closing balance</span><span class="num">{{ money(lm.closing) }}</span></div>
          <div class="small mt" :class="Number(lm.reconciliation_difference) ? 'neg' : 'muted'">Reconciliation difference: {{ money(lm.reconciliation_difference) }}</div>
        </div></div>
        <div class="card"><div class="card-head"><h3>(c) Presentation in the balance sheet</h3><span class="sub">{{ d.presentation.reference }}</span></div><div class="card-body">
          <div class="stat-line"><span>Current lease liabilities (other financial liabilities — current)</span><span class="num">{{ money(d.presentation.current) }}</span></div>
          <div class="stat-line"><span>Non-current lease liabilities</span><span class="num">{{ money(d.presentation.non_current) }}</span></div>
          <div class="stat-line total"><span>Total lease liabilities</span><span class="num">{{ money(d.presentation.total) }}</span></div>
          <h4 class="mt mb-sm">Other information</h4>
          <div class="stat-line"><span>Weighted-average IBR on leases added in the period</span><span class="num">{{ d.weighted_average_rate_new_leases ? num(d.weighted_average_rate_new_leases, 2) + '%' : '—' }}</span></div>
          <div class="stat-line"><span>Leases committed but not commenced (59(b)(iv))</span><span class="num">{{ d.leases_not_yet_commenced.length }}</span></div>
          <div class="small text-2 mt">{{ d.cash_flow_classification }}</div>
        </div></div>
      </div>

      <div class="grid c2 mb">
        <div class="card"><div class="card-head"><h3>(d) Maturity analysis — contractual undiscounted cash flows</h3><span class="sub">{{ mat.reference }}</span></div><div class="card-body">
          <BarChart :labels="mat.rows.map(r => r.bucket)" :values="mat.rows.map(r => r.undiscounted)" value-label="Undiscounted" :height="200"/>
          <div class="stat-line mt" v-for="r in mat.rows" :key="r.bucket"><span>{{ r.bucket }}</span><span class="num">{{ money(r.undiscounted) }}</span></div>
          <div class="stat-line total"><span>Total undiscounted lease payments</span><span class="num">{{ money(mat.total_undiscounted) }}</span></div>
          <div class="stat-line"><span>Less: future finance charges</span><span class="num">({{ money(mat.future_finance_charges) }})</span></div>
          <div class="stat-line total"><span>Lease liabilities (carrying amount)</span><span class="num">{{ money(mat.carrying_amount) }}</span></div>
        </div></div>
        <div class="card"><div class="card-head"><h3>(e) Amounts recognised in profit or loss and cash flows</h3><span class="sub">Ind AS 116.53</span></div>
          <table class="t compact"><thead><tr><th>Ref</th><th>Item</th><th class="num">Amount</th></tr></thead>
            <tbody><template v-for="x in d.para53" :key="x.ref"><tr><td class="nowrap">{{ x.ref }}</td><td class="wrap">{{ x.item }}</td><td class="num">{{ money(x.amount) }}</td></tr>
              <tr v-for="(v, k) in (x.by_class || {})" :key="x.ref + k"><td></td><td class="small text-2" style="padding-left:20px">{{ k }}</td><td class="num small text-2">{{ money(v) }}</td></tr></template></tbody></table></div>
      </div>

      <div class="grid c2 mb">
        <div class="card"><div class="card-head"><h3>(f) Changes in liabilities arising from financing activities</h3><span class="sub">{{ i7.reference }}</span></div><div class="card-body">
          <div class="stat-line total" style="border-top:0"><span>Opening lease liabilities</span><span class="num">{{ money(i7.opening) }}</span></div>
          <div class="stat-line"><span>Financing cash flows</span><span class="num">{{ money(i7.cash_flows_financing) }}</span></div>
          <div class="stat-line"><span>Non-cash: new leases</span><span class="num">{{ money(i7.non_cash_new_leases) }}</span></div>
          <div class="stat-line"><span>Non-cash: interest accrued</span><span class="num">{{ money(i7.non_cash_interest_accrued) }}</span></div>
          <div class="stat-line"><span>Non-cash: remeasurement / modification</span><span class="num">{{ money(i7.non_cash_remeasurement_modification) }}</span></div>
          <div class="stat-line"><span>Non-cash: derecognition</span><span class="num">{{ money(i7.non_cash_derecognition) }}</span></div>
          <div class="stat-line" v-if="Number(i7.non_cash_exchange_differences)"><span>Non-cash: exchange differences</span><span class="num">{{ money(i7.non_cash_exchange_differences) }}</span></div>
          <div class="stat-line total"><span>Closing lease liabilities</span><span class="num">{{ money(i7.closing) }}</span></div>
        </div></div>
        <div class="card"><div class="card-head"><h3>(g) Qualitative disclosures — management input required</h3><span class="sub">Ind AS 116.59–60</span></div><div class="card-body">
          <div v-for="p in d.qualitative_prompts" :key="p.ref" class="judgment info"><div class="t">{{ p.ref }}</div><div class="d">{{ p.prompt }}</div>
            <div class="r" v-if="p.amount_undiscounted !== undefined">Undiscounted payments in optional periods not included in liabilities: {{ money(p.amount_undiscounted) }}</div>
            <div class="r" v-if="p.count !== undefined">Leases committed, not commenced: {{ p.count }}</div></div>
        </div></div>
      </div>

      <template v-if="hasLessor">
        <h2 style="font-size:16px;margin:18px 0 10px">(h) Lessor disclosures <span class="small muted" style="font-weight:400">{{ lessor.reference }}{{ lessor.includes_subleases ? ' · including subleases (intermediate lessor)' : '' }}</span></h2>
        <div class="grid c2 mb">
          <div class="card"><div class="card-head"><h3>(h)(i) Lease income</h3><span class="sub">Para 90 — tabular (para 91)</span></div>
            <table class="t compact"><thead><tr><th>Ref</th><th>Item</th><th class="num">Amount</th></tr></thead>
              <tbody><tr v-for="(x, i) in lessor.income_table" :key="i"><td class="nowrap">{{ x.ref }}</td><td class="wrap">{{ x.item }}</td><td class="num">{{ money(x.amount) }}</td></tr>
                <tr v-if="Number(lessor.income?.non_lease_revenue)"><td class="nowrap">Ind AS 115</td><td class="wrap small text-2">Non-lease components (services / CAM) — revenue, not lease income</td><td class="num small text-2">{{ money(lessor.income.non_lease_revenue) }}</td></tr>
                <tr v-for="(x, i) in (lessor.other_items || [])" :key="'o' + i"><td class="nowrap small text-2">{{ x.ref }}</td><td class="wrap small text-2">{{ x.item }}</td><td class="num small text-2">{{ money(x.amount) }}</td></tr></tbody></table></div>
          <div class="card"><div class="card-head"><h3>(h)(ii) Net investment in finance leases — movement</h3><span class="sub">Para 93</span></div><div class="card-body">
            <div class="stat-line total" style="border-top:0"><span>Opening balance</span><span class="num">{{ money(lmv.opening) }}</span></div>
            <div class="stat-line"><span>Additions (new finance leases)</span><span class="num">{{ money(lmv.additions) }}</span></div>
            <div class="stat-line"><span>Finance income</span><span class="num">{{ money(lmv.finance_income) }}</span></div>
            <div class="stat-line"><span>Lease payments received / receivable</span><span class="num">({{ money(lmv.receipts) }})</span></div>
            <div class="stat-line" v-if="Number(lmv.residual_returned)"><span>Unguaranteed residual realised (asset returned)</span><span class="num">({{ money(lmv.residual_returned) }})</span></div>
            <div class="stat-line" v-if="Number(lmv.remeasurement)"><span>Remeasurements / modifications</span><span class="num">{{ money(lmv.remeasurement) }}</span></div>
            <div class="stat-line" v-if="Number(lmv.derecognised)"><span>Derecognised (terminations / reclassification)</span><span class="num">({{ money(lmv.derecognised) }})</span></div>
            <div class="stat-line total"><span>Closing balance (gross)</span><span class="num">{{ money(lmv.closing) }}</span></div>
            <div class="stat-line" v-if="Number(lessor.loss_allowance?.closing)"><span>Less: loss allowance (Ind AS 109)</span><span class="num">({{ money(lessor.loss_allowance.closing) }})</span></div>
            <div class="small mt" :class="Number(lmv.reconciliation_difference) ? 'neg' : 'muted'">Reconciliation difference: {{ money(lmv.reconciliation_difference) }}</div>
          </div></div>
        </div>
        <div class="grid c2 mb">
          <div class="card"><div class="card-head"><h3>(h)(iii) Finance leases — maturity and reconciliation</h3><span class="sub">Para 94 · at {{ date(f.end) }}</span></div>
            <div class="card-body" v-if="(lessor.maturity_finance || []).length">
              <div class="stat-line" v-for="m in lessor.maturity_finance" :key="m.bucket"><span>{{ m.bucket }}</span><span class="num">{{ money(m.amount) }}</span></div>
              <template v-if="lrc">
                <div class="stat-line total"><span>Undiscounted lease payments receivable</span><span class="num">{{ money(lrc.undiscounted_lease_payments) }}</span></div>
                <div class="stat-line"><span>Less: unearned finance income</span><span class="num">({{ money(lrc.unearned_finance_income) }})</span></div>
                <div class="stat-line"><span>Add: discounted unguaranteed residual value</span><span class="num">{{ money(lrc.discounted_unguaranteed_residual) }}</span></div>
                <div class="stat-line total"><span>Net investment in finance leases</span><span class="num">{{ money(lrc.net_investment) }}</span></div>
                <div class="stat-line"><span>Less: loss allowance</span><span class="num">({{ money(lrc.loss_allowance) }})</span></div>
                <div class="stat-line total"><span>Net investment, net of loss allowance</span><span class="num">{{ money(lrc.net_investment_net_of_allowance) }}</span></div></template>
            </div><div class="card-body" v-else><Empty text="No finance leases at the period end."/></div></div>
          <div class="card"><div class="card-head"><h3>(h)(iv) Operating leases — maturity analysis</h3><span class="sub">Para 97 · at {{ date(f.end) }}</span></div>
            <div class="card-body" v-if="(lessor.maturity_operating || []).length">
              <BarChart :labels="lessor.maturity_operating.map(m => m.bucket)" :values="lessor.maturity_operating.map(m => m.amount)" value-label="Undiscounted receipts" :height="180"/>
              <div class="stat-line mt" v-for="m in lessor.maturity_operating" :key="m.bucket"><span>{{ m.bucket }}</span><span class="num">{{ money(m.amount) }}</span></div>
            </div><div class="card-body" v-else><Empty text="No operating leases at the period end."/></div></div>
        </div>
        <div class="grid c2 mb">
          <div class="card"><div class="card-head"><h3>(h)(v) Balance sheet — lessor</h3><span class="sub">Schedule III</span></div><div class="card-body">
            <div class="stat-line"><span>Net investment in finance leases — current</span><span class="num">{{ money(lpr.ni_current) }}</span></div>
            <div class="stat-line"><span>Net investment in finance leases — non-current</span><span class="num">{{ money(lpr.ni_noncurrent) }}</span></div>
            <div class="stat-line"><span>Accrued lease income (straight-lining) — asset</span><span class="num">{{ money(lpr.accrued_income_asset) }}</span></div>
            <div class="stat-line"><span>Deferred lease income — liability</span><span class="num">{{ money(lpr.deferred_income_liability) }}</span></div>
            <div class="stat-line"><span>Security deposits received — financial liability</span><span class="num">{{ money(lpr.deposits_received) }}</span></div>
            <div class="stat-line" v-if="Number(lpr.idc_carrying)"><span>Initial direct costs in the carrying amount of assets let out</span><span class="num">{{ money(lpr.idc_carrying) }}</span></div>
            <div class="small muted mt" v-if="lessor.current_method">Basis: {{ lessor.current_method }}</div>
          </div></div>
          <div class="card"><div class="card-head"><h3>(h)(vi) Qualitative disclosures — management input required</h3><span class="sub">Paras 92–96</span></div><div class="card-body">
            <div v-for="p in lessor.qualitative_prompts" :key="p.ref" class="judgment info"><div class="t">{{ p.ref }}</div><div class="d">{{ p.prompt }}</div></div>
            <div class="small text-2 mt" v-if="(lessor.operating_lease_assets || []).length">Assets subject to operating leases: {{ lessor.operating_lease_assets.map(a => a.lease_code + ' (' + (a.asset_class || '—') + ')').join('; ') }}</div>
          </div></div>
        </div>
      </template>
    </template>
  </div>`,
};
