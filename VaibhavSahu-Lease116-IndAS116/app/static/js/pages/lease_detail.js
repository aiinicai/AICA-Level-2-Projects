// Lease detail — schedules, judgments, events, journals, documents, disclosures and audit trail for one lease
import { store, get, post, del, upload, toast, showError, confirmDialog, download } from '../store.js';
import { common } from '../components.js';
import { money, date, dateTime, num, titleCase, fyOf, decAdd, decSub, decSum, isNeg } from '../util.js';
import { typeLabel } from './leases.js';
import { monLabel, bucketLabel } from './dashboard.js';
import { ContractForm, OptionsEditor, AssessmentForm, PaymentTermsCard, PaymentScheduleEditor, CostsEditor, DepositForm,
  RestorationForm, RatePanel, DetailsForm } from './lease_forms.js';
import { EventForm, EVENT_TYPES, MOD_NATURES, REASSESS_KINDS } from './events.js';

const { ref, computed, watch, onMounted } = Vue;

const LIAB_COLS = [
  { key: 'period_end', label: 'Period end', type: 'date' }, { key: 'explain', label: '', sortable: false },
  { key: 'liab_open', label: 'Opening', type: 'money' }, { key: 'liab_additions', label: 'Additions', type: 'money' },
  { key: 'interest', label: 'Interest', type: 'money' }, { key: 'payments', label: 'Payments', type: 'money' },
  { key: 'liab_remeasurement', label: 'Remeasurement', type: 'money' }, { key: 'liab_modification', label: 'Modification', type: 'money' },
  { key: 'liab_derecognised', label: 'Derecognised', type: 'money' }, { key: 'liab_fx', label: 'Exchange difference', type: 'money', hidden: true },
  { key: 'liab_close', label: 'Closing', type: 'money' }, { key: 'liab_current', label: 'Current', type: 'money' },
  { key: 'liab_noncurrent', label: 'Non-current', type: 'money' }, { key: 'rounding_trueup', label: 'Rounding true-up', type: 'money', hidden: true },
];
const ROU_COLS = [
  { key: 'period_end', label: 'Period end', type: 'date' }, { key: 'explain', label: '', sortable: false },
  { key: 'rou_open', label: 'Opening NBV', type: 'money' }, { key: 'rou_additions', label: 'Additions', type: 'money' },
  { key: 'depreciation', label: 'Depreciation', type: 'money' }, { key: 'impairment', label: 'Impairment', type: 'money' },
  { key: 'rou_remeasurement', label: 'Remeasurement', type: 'money' }, { key: 'rou_modification', label: 'Modification', type: 'money' },
  { key: 'rou_derecognised', label: 'Derecognised', type: 'money' }, { key: 'rou_close', label: 'Closing NBV', type: 'money' },
  { key: 'rou_cost_close', label: 'Gross cost', type: 'money' }, { key: 'rou_accdep_close', label: 'Acc. depreciation', type: 'money' },
  { key: 'rou_accimp_close', label: 'Acc. impairment', type: 'money', hidden: true },
];
const PL_COLS = [
  { key: 'period_end', label: 'Period end', type: 'date' }, { key: 'interest', label: 'Interest on liability', type: 'money' },
  { key: 'depreciation', label: 'Depreciation', type: 'money' }, { key: 'impairment', label: 'Impairment', type: 'money' },
  { key: 'gain_loss', label: 'Gain / (loss) on events', type: 'money' }, { key: 'remeasurement_pl', label: 'Remeasurement in P&L (39)', type: 'money' },
  { key: 'variable_expense', label: 'Variable lease expense', type: 'money' }, { key: 'non_lease_expense', label: 'Non-lease expense', type: 'money' },
  { key: 'prov_unwinding', label: 'Provision unwinding', type: 'money' }, { key: 'dep_interest', label: 'Deposit interest income', type: 'money' },
  { key: 'cash_outflow', label: 'Total cash outflow', type: 'money' },
];
const PROV_COLS = [
  { key: 'period_end', label: 'Period end', type: 'date' }, { key: 'prov_open', label: 'Opening', type: 'money' },
  { key: 'prov_additions', label: 'Recognised', type: 'money' }, { key: 'prov_unwinding', label: 'Unwinding (finance cost)', type: 'money' },
  { key: 'prov_revision', label: 'Revision', type: 'money' }, { key: 'prov_settled', label: 'Settled', type: 'money' }, { key: 'prov_close', label: 'Closing', type: 'money' },
];
const DEP_COLS = [
  { key: 'period_end', label: 'Period end', type: 'date' }, { key: 'dep_open', label: 'Opening (amortised cost)', type: 'money' },
  { key: 'dep_additions', label: 'Initial fair value', type: 'money' }, { key: 'dep_interest', label: 'Interest income (EIR)', type: 'money' },
  { key: 'dep_refund', label: 'Refund', type: 'money' }, { key: 'dep_close', label: 'Closing', type: 'money' },
];
const ZERO_DASH = ['liab_additions', 'liab_remeasurement', 'liab_modification', 'liab_derecognised', 'liab_fx', 'rounding_trueup', 'rou_additions',
  'impairment', 'rou_remeasurement', 'rou_modification', 'rou_derecognised', 'gain_loss', 'remeasurement_pl', 'variable_expense', 'non_lease_expense',
  'prov_additions', 'prov_revision', 'prov_settled', 'dep_additions', 'dep_refund', 'rou_accimp_close'];
[LIAB_COLS, ROU_COLS, PL_COLS, PROV_COLS, DEP_COLS].forEach(cs => cs.forEach(c => { if (ZERO_DASH.includes(c.key)) c.zeroDash = true; }));
const FLOW_KEYS = ['liab_additions', 'interest', 'payments', 'liab_remeasurement', 'liab_modification', 'liab_derecognised', 'liab_fx', 'rounding_trueup',
  'rou_additions', 'depreciation', 'impairment', 'rou_remeasurement', 'rou_modification', 'rou_derecognised', 'gain_loss', 'remeasurement_pl',
  'variable_expense', 'non_lease_expense', 'prov_additions', 'prov_unwinding', 'prov_revision', 'prov_settled', 'dep_additions', 'dep_interest',
  'dep_refund', 'cash_outflow'];
const OPEN_KEYS = ['liab_open', 'rou_open', 'prov_open', 'dep_open'];
const CLOSE_KEYS = ['liab_close', 'liab_current', 'liab_noncurrent', 'rou_close', 'rou_cost_close', 'rou_accdep_close', 'rou_accimp_close', 'prov_close', 'dep_close'];

// lessor schedule: candidate columns (only columns with amounts are shown for a lease)
const LESSOR_COLS = [
  { key: 'period_end', label: 'Period end', type: 'date' }, { key: 'classification', label: 'Class', format: (v) => v ? v.charAt(0) + v.slice(1).toLowerCase() : '' },
  { key: 'ni_open', label: 'Opening NI', type: 'money', open: true }, { key: 'ni_additions', label: 'Additions', type: 'money', flow: true },
  { key: 'finance_income', label: 'Finance income', type: 'money', flow: true }, { key: 'ni_receipts', label: 'Receipts applied', type: 'money', flow: true },
  { key: 'ni_residual_returned', label: 'Residual returned', type: 'money', flow: true }, { key: 'ni_remeasurement', label: 'Remeasurement', type: 'money', flow: true },
  { key: 'ni_derecognised', label: 'Derecognised', type: 'money', flow: true }, { key: 'ni_close', label: 'Closing NI', type: 'money', close: true },
  { key: 'ni_current', label: 'Current', type: 'money', close: true, hidden: true }, { key: 'ni_noncurrent', label: 'Non-current', type: 'money', close: true, hidden: true },
  { key: 'lease_income', label: 'Lease income (SL)', type: 'money', flow: true }, { key: 'lease_payments_due', label: 'Payments due', type: 'money', flow: true },
  { key: 'accrued_adjustment', label: 'Accrued adj.', type: 'money', flow: true }, { key: 'accrued_close', label: 'Accrued / (deferred) income', type: 'money', close: true },
  { key: 'variable_income', label: 'Variable income', type: 'money', flow: true }, { key: 'non_lease_income', label: 'Non-lease revenue', type: 'money', flow: true },
  { key: 'receipts', label: 'Billed', type: 'money', flow: true }, { key: 'idc_amortisation', label: 'IDC amortised', type: 'money', flow: true },
  { key: 'dep_unwinding', label: 'Deposit unwinding', type: 'money', flow: true }, { key: 'dep_close', label: 'Deposit (carrying)', type: 'money', close: true },
  { key: 'ecl_charge', label: 'ECL charge', type: 'money', flow: true }, { key: 'loss_allowance_close', label: 'Loss allowance', type: 'money', close: true },
  { key: 'gain_loss', label: 'Gain / (loss)', type: 'money', flow: true },
];
function lessorCols(rows) {
  return LESSOR_COLS.filter(c => c.type !== 'money' || rows.some(r => Number(r[c.key] || 0) !== 0)).map(c => ({ ...c, zeroDash: c.flow }));
}
function lessorByFY(rows, startMonth) {
  const out = [];
  let cur = null;
  for (const r of rows) {
    const [a] = fyOf(r.period_end, startMonth);
    if (!cur || cur._fy !== a) {
      cur = { _fy: a, period_start: r.period_start, period_end: r.period_end, fy: 'FY ' + a.slice(0, 4) + '-' + String(Number(a.slice(0, 4)) + 1).slice(2) };
      LESSOR_COLS.filter(c => c.open).forEach(c => { cur[c.key] = r[c.key]; });
      LESSOR_COLS.filter(c => c.flow).forEach(c => { cur[c.key] = '0'; });
      out.push(cur);
    }
    LESSOR_COLS.filter(c => c.flow).forEach(c => { cur[c.key] = decAdd(cur[c.key], r[c.key] || '0'); });
    LESSOR_COLS.filter(c => c.close).forEach(c => { cur[c.key] = r[c.key]; });
    cur.classification = r.classification;
    cur.period_end = r.period_end;
  }
  return out;
}
const LESSOR_EVENT_LABELS = { MODIFICATION: 'Modification', TERMINATION: 'Early termination', UGR_REVISION: 'Unguaranteed residual revised', ECL: 'Expected credit loss allowance' };

function byFY(rows, startMonth) {
  const out = [];
  let cur = null;
  for (const r of rows) {
    const [a] = fyOf(r.period_end, startMonth);
    if (!cur || cur._fy !== a) {
      cur = { _fy: a, period_start: r.period_start, period_end: r.period_end, fy: 'FY ' + a.slice(0, 4) + '-' + String(Number(a.slice(0, 4)) + 1).slice(2) };
      OPEN_KEYS.forEach(k => { cur[k] = r[k]; });
      FLOW_KEYS.forEach(k => { cur[k] = '0'; });
      out.push(cur);
    }
    FLOW_KEYS.forEach(k => { cur[k] = decAdd(cur[k], r[k]); });
    CLOSE_KEYS.forEach(k => { cur[k] = r[k]; });
    cur.period_end = r.period_end;
  }
  return out;
}
function totalsOf(rows, cols) {
  const t = {};
  cols.forEach(c => { if (c.type === 'money' && FLOW_KEYS.includes(c.key)) t[c.key] = decSum(rows, c.key); });
  return t;
}

// ----------------------------------------------------------------------------- "How was this calculated?"
const ExplainDrawer = {
  components: common,
  props: { leaseId: [String, Number], periodEnd: String, summary: Object },
  emits: ['close'],
  setup(props) {
    const x = ref(null);
    onMounted(async () => {
      try { x.value = await get('/api/leases/' + props.leaseId + '/explain?period_end=' + props.periodEnd); } catch (e) { showError(e); }
    });
    const r = computed(() => x.value?.row || {});
    const det = computed(() => x.value?.detail?.detail || {});
    const days = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);
    const prevDay = (s) => { const d = new Date(s); d.setUTCDate(d.getUTCDate() - 1); return d.toISOString().slice(0, 10); };
    const liabCheck = computed(() => {
      const v = r.value;
      if (!v.period_end) return null;
      const calc = decSub(decAdd(v.liab_open, v.liab_additions, v.interest, v.liab_remeasurement, v.liab_modification, v.liab_fx || 0),
        decAdd(v.payments, v.liab_derecognised));
      return decSub(calc, v.liab_close);
    });
    const rouCheck = computed(() => {
      const v = r.value;
      if (!v.period_end) return null;
      const calc = decSub(decAdd(v.rou_open, v.rou_additions, v.rou_remeasurement, v.rou_modification), decAdd(v.depreciation, v.impairment, v.rou_derecognised));
      return decSub(calc, v.rou_close);
    });
    const initial = computed(() => x.value?.initial);
    const first = computed(() => initial.value && r.value.period_start && initial.value.measurement_date >= r.value.period_start && initial.value.measurement_date <= r.value.period_end);
    const maturity = computed(() => Object.entries(x.value?.detail?.maturity || {}));
    const isMonths = computed(() => (x.value?.daycount || '').startsWith('MONTHS'));
    return { x, r, det, days, prevDay, liabCheck, rouCheck, initial, first, maturity, isMonths, money, date, num, bucketLabel, isNeg };
  },
  template: `
  <Modal drawer :title="'How was ' + date(periodEnd) + ' calculated?'" @close="$emit('close')">
    <div v-if="!x" class="progress"><i></i></div>
    <div v-else class="col" style="gap:16px">
      <div class="small text-2">Period {{ date(r.period_start) }} to {{ date(r.period_end) }} · rate {{ num(r.rate_pct, 4) }}% p.a. · {{ x.daycount }} · amounts in {{ summary.currency }}</div>
      <div>
        <h3 class="mb-sm">Lease liability roll-forward</h3>
        <div class="stat-line"><span>Opening balance</span><span class="num">{{ money(r.liab_open) }}</span></div>
        <div class="stat-line" v-if="Number(r.liab_additions)"><span>Initial recognition (para 26)</span><span class="num">{{ money(r.liab_additions) }}</span></div>
        <div class="stat-line"><span>Add: interest (para 36(a))</span><span class="num">{{ money(r.interest) }}</span></div>
        <div class="stat-line"><span>Less: lease payments (para 36(b))</span><span class="num">({{ money(r.payments) }})</span></div>
        <div class="stat-line" v-if="Number(r.liab_remeasurement)"><span>Remeasurement (paras 39–43)</span><span class="num">{{ money(r.liab_remeasurement) }}</span></div>
        <div class="stat-line" v-if="Number(r.liab_modification)"><span>Modification (paras 44–46)</span><span class="num">{{ money(r.liab_modification) }}</span></div>
        <div class="stat-line" v-if="Number(r.liab_derecognised)"><span>Derecognised</span><span class="num">({{ money(r.liab_derecognised) }})</span></div>
        <div class="stat-line" v-if="Number(r.liab_fx || 0)"><span>Exchange difference (Ind AS 21)</span><span class="num">{{ money(r.liab_fx) }}</span></div>
        <div class="stat-line total"><span>Closing balance</span><span class="num">{{ money(r.liab_close) }}</span></div>
        <div class="small" :class="Number(liabCheck) ? 'neg' : 'pos'" style="margin-top:4px">Arithmetic check: difference {{ money(liabCheck) }}</div>
      </div>
      <div v-if="det.interest && det.interest.length">
        <h3 class="mb-sm">Interest — effective interest method</h3>
        <div class="formula mb-sm" v-if="!isMonths">Interest = Balance × [(1 + R)<sup>d/365</sup> − 1], R = effective annual rate, d = days outstanding. Balances change only on payment / event dates, so the period is split into sub-intervals.</div>
        <div class="formula mb-sm" v-else>Interest = Balance × [(1 + R)<sup>m/12</sup> − 1], m = months outstanding (MONTHS/12 convention).</div>
        <table class="t compact"><thead><tr><th>From</th><th>To</th><th class="num">Days</th><th class="num">Balance outstanding</th><th class="num">Growth factor</th><th class="num">Interest</th></tr></thead>
          <tbody><tr v-for="(p, i) in det.interest" :key="i"><td class="nowrap">{{ date(p.from) }}</td><td class="nowrap">{{ date(prevDay(p.to)) }}</td><td class="num">{{ days(p.from, p.to) }}</td>
            <td class="num">{{ money(p.balance) }}</td><td class="num mono">{{ num(p.factor, 10) }}</td><td class="num">{{ money(p.interest, {places: 4}) }}</td></tr></tbody></table>
        <div class="small muted mt">Closing balance is rounded to 2 decimals; interest for the period is the balancing movement (no silent plugs — rounding differences above tolerance are reported as exceptions).</div>
      </div>
      <div>
        <h3 class="mb-sm">Right-of-use asset</h3>
        <div class="stat-line"><span>Opening carrying amount</span><span class="num">{{ money(r.rou_open) }}</span></div>
        <div class="stat-line" v-if="Number(r.rou_additions)"><span>Initial recognition (para 24)</span><span class="num">{{ money(r.rou_additions) }}</span></div>
        <div class="stat-line"><span>Less: depreciation (paras 31–32)</span><span class="num">({{ money(r.depreciation) }})</span></div>
        <div class="stat-line" v-if="Number(r.impairment)"><span>Impairment (para 33)</span><span class="num">({{ money(r.impairment) }})</span></div>
        <div class="stat-line" v-if="Number(r.rou_remeasurement)"><span>Remeasurement adjustment (para 39)</span><span class="num">{{ money(r.rou_remeasurement) }}</span></div>
        <div class="stat-line" v-if="Number(r.rou_modification)"><span>Modification adjustment</span><span class="num">{{ money(r.rou_modification) }}</span></div>
        <div class="stat-line" v-if="Number(r.rou_derecognised)"><span>Derecognised</span><span class="num">({{ money(r.rou_derecognised) }})</span></div>
        <div class="stat-line total"><span>Closing carrying amount</span><span class="num">{{ money(r.rou_close) }}</span></div>
        <div class="small" :class="Number(rouCheck) ? 'neg' : 'pos'" style="margin-top:4px">Arithmetic check: difference {{ money(rouCheck) }}</div>
      </div>
      <div v-if="det.depreciation && det.depreciation.length">
        <h3 class="mb-sm">Depreciation — {{ det.method === 'MONTHLY_EQUAL' ? 'straight-line, equal monthly' : 'straight-line, daily' }}</h3>
        <div class="formula mb-sm">Depreciation = carrying amount at the start of the depreciation segment × (period weight ÷ total segment weight). A new segment starts at commencement and after every remeasurement, modification or impairment; weights are days (daily method) or months (equal monthly). Depreciation ends at the earlier of useful life and lease term (para 32) unless ownership transfers or a purchase option is reasonably certain.</div>
        <table class="t compact"><thead><tr><th>From</th><th>To</th><th class="num">Segment NBV at start</th><th class="num">Period weight</th><th class="num">Total segment weight</th><th class="num">Depreciation</th><th>Segment start</th><th>Depreciate to</th></tr></thead>
          <tbody><tr v-for="(p, i) in det.depreciation" :key="i"><td class="nowrap">{{ date(p.from) }}</td><td class="nowrap">{{ date(prevDay(p.to)) }}</td><td class="num">{{ money(p.segment_nbv) }}</td>
            <td class="num">{{ num(p.weight, 4) }}</td><td class="num">{{ num(p.segment_weight, 4) }}</td><td class="num">{{ money(p.depreciation, {places: 4}) }}</td><td class="nowrap">{{ date(p.segment_start) }}</td><td class="nowrap">{{ date(p.depreciation_end) }}</td></tr></tbody></table>
      </div>
      <div>
        <h3 class="mb-sm">Presentation at period end</h3>
        <div class="stat-line"><span>Current portion (principal reduction within 12 months)</span><span class="num">{{ money(r.liab_current) }}</span></div>
        <div class="stat-line"><span>Non-current portion</span><span class="num">{{ money(r.liab_noncurrent) }}</span></div>
        <div class="small muted mt" v-if="maturity.length">Undiscounted remaining payments by maturity bucket:</div>
        <div class="stat-line" v-for="m in maturity" :key="m[0]"><span>{{ bucketLabel(m[0]) }}</span><span class="num">{{ money(m[1]) }}</span></div>
      </div>
      <div v-if="first && initial">
        <h3 class="mb-sm">Initial measurement at {{ date(initial.measurement_date) }}</h3>
        <div class="formula mb-sm">Liability = Σ payment × 1 / (1 + R)<sup>t</sup>, t = years from commencement ({{ initial.daycount }}); R = {{ num(initial.effective_annual_rate * 100, 6) }}% effective annual</div>
        <table class="t compact"><thead><tr><th>Date</th><th class="num">Payment</th><th class="num">t (years)</th><th class="num">Discount factor</th><th class="num">Present value</th></tr></thead>
          <tbody><tr v-for="(p, i) in initial.pv_lines" :key="i"><td>{{ date(p.date) }}</td><td class="num">{{ money(p.amount) }}</td><td class="num mono">{{ num(p.years, 6) }}</td>
            <td class="num mono">{{ num(p.discount_factor, 8) }}</td><td class="num">{{ money(p.present_value) }}</td></tr>
            <tr class="total"><td>Total</td><td class="num">{{ money(initial.undiscounted_total) }}</td><td></td><td></td><td class="num">{{ money(initial.liability) }}</td></tr></tbody></table>
      </div>
    </div>
  </Modal>`,
};

// ----------------------------------------------------------------------------- page
export const LeaseDetailPage = {
  components: { ...common, ExplainDrawer, ContractForm, OptionsEditor, AssessmentForm, PaymentTermsCard, PaymentScheduleEditor, CostsEditor,
    DepositForm, RestorationForm, RatePanel, DetailsForm, EventForm },
  props: { route: Object },
  emits: ['title'],
  setup(props, { emit }) {
    const id = props.route.params.id;
    const lease = ref(null);
    const res = ref({ run: null, summary: null });
    const tab = ref(props.route.query.tab || 'overview');
    const paySub = ref('terms');
    const liabSub = ref('periods');
    const rouSub = ref('rou');
    const view = ref('monthly');
    const busy = ref(false);
    const calcError = ref(null);
    const explainPe = ref(null);
    const settings = ref(null);
    const journals = ref(null);
    const jFy = ref('');
    const auditRows = ref(null);
    const tax = ref(null);
    const showEvent = ref(false);
    const inputsModal = ref(null);
    const docType = ref('Lease agreement');
    const openJe = ref({});

    async function load() {
      try {
        lease.value = await get('/api/leases/' + id);
        res.value = await get('/api/leases/' + id + '/result');
        emit('title', 'Lease ' + lease.value.lease_code);
        journals.value = null; auditRows.value = null; tax.value = null;
        loadTab();
      } catch (e) { showError(e); }
    }
    async function loadTab() {
      try {
        if (tab.value === 'journals' && !journals.value && store.can('journal.read')) {
          journals.value = await get('/api/leases/' + id + '/journals');
          if (!jFy.value) jFy.value = fyOf(store.asOf || lease.value.commencement_date, store.company?.fy_start_month || 4)[0];
        }
        if (tab.value === 'audit' && !auditRows.value) auditRows.value = await get('/api/leases/' + id + '/audit');
        if (tab.value === 'disclosures' && !tax.value) tax.value = await get('/api/leases/' + id + '/tax?as_of=' + (store.asOf || ''));
      } catch (e) { showError(e); }
    }
    onMounted(async () => {
      await load();
      try { settings.value = (await get('/api/settings')).settings; } catch (e) { /* ignore */ }
    });
    watch(tab, () => { loadTab(); history.replaceState(null, '', '#/leases/' + id + '?tab=' + tab.value); });
    watch(() => props.route.query.tab, (t) => { if (t && t !== tab.value) tab.value = t; });
    watch(() => store.asOf, () => { tax.value = null; if (tab.value === 'disclosures') loadTab(); });

    const s = computed(() => res.value?.summary || null);
    const kind = computed(() => s.value?.kind || null);
    const isLessor = computed(() => lease.value?.role === 'LESSOR' && lease.value?.lease_type !== 'SUBLEASE');
    const pos = ref(null);
    const lsub = ref('periods');
    async function loadPos() {
      pos.value = null;
      if (!['LESSOR', 'SUBLEASE'].includes(kind.value)) return;
      try { const r = await get('/api/leases/' + id + '/lessor-position?as_of=' + (store.asOf || '')); pos.value = r && r.available ? r : null; } catch (e) { /* ignore */ }
    }
    watch([kind, () => store.asOf, () => res.value?.run?.id], loadPos);
    // balances come from the last schedule row on / before the as-of date — label them when that is not the as-of date
    const posAt = computed(() => (pos.value && pos.value.row_period_end && pos.value.row_period_end !== store.asOf) ? ' — at ' + date(pos.value.row_period_end) : '');
    const lRows = computed(() => s.value?.rows || []);
    const lRowsView = computed(() => view.value === 'fy' ? lessorByFY(lRows.value, fyStart.value) : lRows.value);
    const lCols = computed(() => {
      const c = lessorCols(lRows.value).map(x => ({ ...x }));
      if (view.value === 'fy') c[0] = { key: 'fy', label: 'Financial year' };
      return c;
    });
    const lTotals = computed(() => {
      const t = {};
      lCols.value.forEach(c => { if (c.flow) t[c.key] = decSum(lRowsView.value, c.key); });
      return t;
    });
    const lFy = computed(() => {
      const [a, b] = fyOf(store.asOf || '2000-01-01', fyStart.value);
      const rows = lRows.value.filter(p => p.period_end >= a && p.period_end <= b);
      const sum = (k) => decSum(rows, k);
      return { finance_income: sum('finance_income'), lease_income: sum('lease_income'), variable_income: sum('variable_income'),
        non_lease_income: sum('non_lease_income'), receipts: sum('receipts'), dep_unwinding: sum('dep_unwinding'), idc_amortisation: sum('idc_amortisation'),
        ecl_charge: sum('ecl_charge'), gain_loss: sum('gain_loss'),
        selling_profit: (s.value?.classification === 'FINANCE' && lease.value?.commencement_date >= a && lease.value?.commencement_date <= b) ? s.value.selling_profit : '0',
        derecognition_gain: (s.value?.classification === 'FINANCE' && lease.value?.commencement_date >= a && lease.value?.commencement_date <= b) ? (s.value.derecognition_gain || '0') : '0' };
    });
    const lChart = computed(() => ({
      labels: lRows.value.map(p => p.period_end),
      series: lRows.value.some(p => Number(p.ni_close)) ? [{ label: 'Net investment', values: lRows.value.map(p => p.ni_close) }]
        : [{ label: 'Accrued / (deferred) lease income', values: lRows.value.map(p => p.accrued_close) }, { label: 'Deposit received (carrying)', values: lRows.value.map(p => p.dep_close) }],
    }));
    const clsLabel = (v) => v === 'FINANCE' ? 'Finance lease' : v === 'OPERATING' ? 'Operating lease' : v === 'ENDED' ? 'Terminated' : v === 'NOT_COMMENCED' ? 'Not commenced' : (v || '—');
    const metLabel = (m) => m === true ? 'Yes' : m === false ? 'No' : 'Not determinable';
    const periods = computed(() => s.value?.periods || []);
    const initial = computed(() => s.value?.initial || null);
    const term = computed(() => s.value?.term || null);
    const fyStart = computed(() => store.company?.fy_start_month || 4);
    const editable = computed(() => lease.value?.status === 'Draft' && store.can('lease.write'));
    const rowAsOf = computed(() => {
      const r = periods.value.filter(p => p.period_end <= (store.asOf || '9999'));
      return r.length ? r[r.length - 1] : null;
    });
    const liabRows = computed(() => view.value === 'fy' ? byFY(periods.value, fyStart.value) : periods.value);
    const liabCols = computed(() => {
      const c = LIAB_COLS.map(x => ({ ...x }));
      if (view.value === 'fy') c[0] = { key: 'fy', label: 'Financial year' };
      return c;
    });
    const rouCols = computed(() => {
      const c = ROU_COLS.map(x => ({ ...x }));
      if (view.value === 'fy') c[0] = { key: 'fy', label: 'Financial year' };
      return c;
    });
    const plCols = computed(() => { const c = PL_COLS.map(x => ({ ...x })); if (view.value === 'fy') c[0] = { key: 'fy', label: 'Financial year' }; return c; });
    const provCols = computed(() => { const c = PROV_COLS.map(x => ({ ...x })); if (view.value === 'fy') c[0] = { key: 'fy', label: 'Financial year' }; return c; });
    const depCols = computed(() => { const c = DEP_COLS.map(x => ({ ...x })); if (view.value === 'fy') c[0] = { key: 'fy', label: 'Financial year' }; return c; });
    const chart = computed(() => ({
      labels: periods.value.map(p => p.period_end),
      series: [{ label: 'Lease liability', values: periods.value.map(p => p.liab_close) },
        { label: 'ROU asset (carrying amount)', values: periods.value.map(p => p.rou_close) }],
    }));
    const hasProv = computed(() => periods.value.some(p => Number(p.prov_close) || Number(p.prov_additions)));
    const hasDep = computed(() => periods.value.some(p => Number(p.dep_close) || Number(p.dep_additions)));
    const isFx = computed(() => !!(s.value?.fx_periods && s.value.fx_periods.length));
    const fxCols = [
      { key: 'period_end', label: 'Period end', type: 'date' }, { key: 'closing_rate', label: 'Closing rate', type: 'rate' }, { key: 'avg_rate', label: 'Average rate', type: 'rate' },
      { key: 'liab_open', label: 'Opening liability', type: 'money' }, { key: 'interest', label: 'Interest (avg rate)', type: 'money' }, { key: 'payments', label: 'Payments (spot)', type: 'money' },
      { key: 'fx_difference', label: 'Exchange (gain)/loss', type: 'money' }, { key: 'liab_close', label: 'Closing liability (closing rate)', type: 'money' },
      { key: 'depreciation', label: 'Depreciation (historical)', type: 'money' }, { key: 'rou_close', label: 'ROU (historical rate)', type: 'money' },
    ];
    const payCols = [
      { key: 'no', label: '#', type: 'num' }, { key: 'date', label: 'Date', type: 'date' }, { key: 'opening', label: 'Opening', type: 'money' },
      { key: 'interest', label: 'Interest accrued', type: 'money' }, { key: 'payment', label: 'Payment', type: 'money' },
      { key: 'adjustment', label: 'Adjustment', type: 'money' }, { key: 'principal', label: 'Principal', type: 'money' },
      { key: 'closing', label: 'Closing', type: 'money' }, { key: 'note', label: 'Note', wrap: true },
    ];
    const tabs = computed(() => {
      const l = lease.value || {};
      const t = [{ key: 'overview', label: 'Overview' }, { key: 'contract', label: 'Contract & options' }, { key: 'assessment', label: 'Assessment' },
        { key: 'payments', label: 'Payments' }];
      if (l.role === 'LESSOR' && l.lease_type !== 'SUBLEASE') {
        t.splice(2, 0, { key: 'classification', label: 'Classification' });
        t.push({ key: 'lessor', label: 'Lessor schedule' });
      } else if (kind.value === 'LESSEE' || (!kind.value && l.lease_type !== 'SHORT_TERM' && l.lease_type !== 'LOW_VALUE' && l.role === 'LESSEE')) {
        t.push({ key: 'rate', label: 'Discount rate' }, { key: 'liability', label: 'Liability schedule' }, { key: 'rou', label: 'ROU schedule' });
      } else if (kind.value === 'SUBLEASE') {
        t.push({ key: 'lessor', label: 'Sublease schedule' });
      }
      t.push({ key: 'events', label: 'Events', count: (l.events || []).filter(e => e.status !== 'Rejected').length || null },
        { key: 'journals', label: 'Journals' }, { key: 'documents', label: 'Documents', count: (l.documents || []).length || null },
        { key: 'disclosures', label: 'Disclosures & tax' }, { key: 'audit', label: 'Audit trail' });
      return t;
    });
    const sumRows = (k) => decSum(s.value?.rows || [], k);
    const eventResult = (ev) => (s.value?.events || []).find(e => e.ref === 'EV-' + ev.id) || ev.result;

    // ---- actions
    async function calculate() {
      busy.value = true; calcError.value = null;
      try {
        const r = await post('/api/leases/' + id + '/calculate');
        toast('Calculated — run #' + r.run_no + ' (Draft)', 'ok');
        await load();
      } catch (e) { calcError.value = { message: e.message, issues: e.issues || [] }; } finally { busy.value = false; }
    }
    async function act(action) {
      let comment = null;
      const l = lease.value;
      if (action === 'return') { comment = await confirmDialog('Return to preparer', 'Explain what needs to be corrected.', { input: 'Review comment', ok: 'Return', danger: true }); if (!comment) return; }
      else if (action === 'reopen') { comment = await confirmDialog('Reopen for correction', 'The approved calculation stays in history. A new calculation must be reviewed and approved again. Use Events for modifications or reassessments — reopen only to correct errors.', { input: 'Reason for reopening (mandatory)', ok: 'Reopen', danger: true }); if (!comment) return; }
      else if (action === 'approve') { comment = await confirmDialog('Approve calculation', 'Approving records you as approver of run #' + (res.value.run?.run_no || '') + ' for ' + l.lease_code + '. Journals from approved runs can be posted.', { input: 'Approval comment (optional)', ok: 'Approve' }); if (comment === false) return; }
      else if (action === 'archive') { if (!(await confirmDialog('Archive lease', 'Archived leases are excluded from reports and the dashboard. History is kept.', { ok: 'Archive', danger: true }))) return; }
      else if (action === 'submit') { if (lease.value.stale && !(await confirmDialog('Inputs changed', 'Inputs were changed after the last calculation. Submit the existing calculation anyway?', { ok: 'Submit' }))) return; }
      busy.value = true;
      try {
        const r = await post('/api/leases/' + id + '/workflow/' + action, { comment: comment || null });
        toast('Status: ' + r.status, 'ok');
        await load();
        window.__lease116?.refreshCounts();
      } catch (e) { showError(e); } finally { busy.value = false; }
    }
    function exp(kind_) {
      const qs = new URLSearchParams({ period: store.asOf ? 'As of ' + date(store.asOf) : '', as_of: store.asOf || '' });
      download('/api/leases/' + id + '/export/' + kind_ + '?' + qs.toString(), kind_);
    }
    const asOfQs = computed(() => '?as_of=' + (store.asOf || ''));
    const exportItems = computed(() => [
      { label: 'Audit workpaper (Excel, live formulas)', url: '/api/leases/' + id + '/export/workpaper.xlsx' + asOfQs.value, icon: 'file-spreadsheet' },
      { label: 'Accounting memo (Word)', url: '/api/leases/' + id + '/export/memo.docx' + asOfQs.value, icon: 'file-text' },
      { label: 'Schedule — Excel', url: '/api/leases/' + id + '/export/schedule.xlsx', icon: 'table-2' },
      { label: 'Schedule — CSV', url: '/api/leases/' + id + '/export/schedule.csv', icon: 'file-down' },
      { label: 'Schedule — PDF', url: '/api/leases/' + id + '/export/schedule.pdf', icon: 'printer' },
    ]);
    async function withdraw(ev) {
      if (!(await confirmDialog('Withdraw event', 'The event is marked Rejected and excluded from the next calculation. Recalculate the lease afterwards.', { ok: 'Withdraw', danger: true }))) return;
      try { await del('/api/leases/' + id + '/events/' + ev.id); toast('Event withdrawn', 'ok'); await load(); } catch (e) { showError(e); }
    }
    function eventSaved() { showEvent.value = false; tab.value = 'events'; load(); }
    async function uploadDoc(e) {
      const f = e.target.files[0];
      if (!f) return;
      const fd = new FormData();
      fd.append('file', f);
      fd.append('doc_type', docType.value);
      try { await upload('/api/leases/' + id + '/documents', fd); toast('Document uploaded', 'ok'); e.target.value = ''; await load(); } catch (err) { showError(err); }
    }
    async function showInputs(run) {
      try { inputsModal.value = { run, data: await get('/api/leases/' + id + '/runs/' + run.id + '/inputs') }; } catch (e) { showError(e); }
    }
    const jList = computed(() => (journals.value || []).filter(j => {
      if (!jFy.value) return true;
      const [a, b] = fyOf(jFy.value, fyStart.value);
      return j.date >= a && j.date <= b;
    }));
    const jFys = computed(() => {
      const set = new Set((journals.value || []).map(j => fyOf(j.date, fyStart.value)[0]));
      return [...set].sort();
    });
    const auditCols = [
      { key: 'at', label: 'When', format: (v) => dateTime(v) }, { key: 'username', label: 'User' }, { key: 'action', label: 'Action' },
      { key: 'object_type', label: 'Object' }, { key: 'field', label: 'Field' }, { key: 'old_value', label: 'Old value', wrap: true, format: (v) => v === null || v === undefined ? '—' : (typeof v === 'object' ? JSON.stringify(v) : String(v)) },
      { key: 'new_value', label: 'New value', wrap: true, format: (v) => v === null || v === undefined ? '—' : (typeof v === 'object' ? JSON.stringify(v) : String(v)) },
      { key: 'reason', label: 'Reason', wrap: true }, { key: 'approval_status', label: 'Approval status' },
    ];
    const fyNow = computed(() => fyOf(store.asOf || '2000-01-01', fyStart.value));
    const fyFlows = computed(() => {
      const [a, b] = fyNow.value;
      const rows = periods.value.filter(p => p.period_end >= a && p.period_end <= b);
      return { interest: decSum(rows, 'interest'), depreciation: decSum(rows, 'depreciation'), payments: decSum(rows, 'payments'),
        cash: decSum(rows, 'cash_outflow'), variable: decSum(rows, 'variable_expense'), additions: decSum(rows, 'rou_additions') };
    });
    const threshold = computed(() => settings.value?.policies?.low_value_threshold);
    const labelEvt = (ev) => (EVENT_TYPES[ev.event_type] || {}).label || ev.event_type;
    const labelSub = (v) => ((MOD_NATURES.concat(REASSESS_KINDS)).find(x => x.v === v) || {}).l || (v ? titleCase(v) : '');
    const canEvent = computed(() => store.can('event.write') && ['Approved', 'Posted', 'Modified', 'Draft'].includes(lease.value?.status)
      && (kind.value === 'LESSEE' || (kind.value === 'LESSOR' && isLessor.value)));
    const labelEvtL = (ev) => isLessor.value ? (LESSOR_EVENT_LABELS[ev.event_type] || titleCase(ev.event_type)) : labelEvt(ev);
    return { store, id, lease, res, s, kind, posAt, periods, initial, term, tab, tabs, paySub, liabSub, rouSub, view, busy, calcError, explainPe,
      editable, rowAsOf, liabRows, liabCols, rouCols, plCols, provCols, depCols, chart, hasProv, hasDep, isFx, fxCols, payCols,
      calculate, act, exp, exportItems, withdraw, showEvent, eventSaved, uploadDoc, docType, showInputs, inputsModal, journals, jList, jFy, jFys,
      openJe, auditRows, auditCols, tax, fyNow, fyFlows, threshold, labelEvt, labelSub, eventResult, canEvent, load, totalsOf, sumRows,
      isLessor, pos, lsub, lRows, lRowsView, lCols, lTotals, lFy, lChart, clsLabel, metLabel, labelEvtL, decAdd,
      money, date, dateTime, num, titleCase, typeLabel, monLabel, bucketLabel, isNeg };
  },
  template: `
  <div v-if="!lease" class="progress"><i></i></div>
  <div v-else>
    <div class="page-head">
      <div class="grow">
        <div class="row wrap" style="gap:8px"><a href="#/leases" class="btn sm ghost"><AppIcon name="chevron-left" :size="14"/></a>
          <h1>{{ lease.lease_code }}</h1><StatusBadge :status="lease.status" dot/><span class="badge info">{{ typeLabel(lease) }}</span>
          <span class="chip" v-if="res.run">Calculation run #{{ res.run.run_no }} · {{ res.run.status }}<span v-if="res.run.version_no"> · v{{ res.run.version_no }}</span></span>
          <span class="chip" v-if="lease.related_party"><AppIcon name="users" :size="12"/> Related party</span>
        </div>
        <div class="sub">{{ lease.description }} · {{ isLessor ? 'Lessee' : 'Lessor' }}: {{ lease.lessor || 'not entered' }} · {{ lease.entity_code }} · {{ lease.asset_class || 'No class' }} · {{ lease.currency }}</div>
      </div>
      <div class="row wrap" style="justify-content:flex-end">
        <button v-if="lease.status==='Draft' && store.can('lease.calculate')" class="btn primary" :disabled="busy" @click="calculate"><AppIcon name="calculator" :size="14"/> Calculate</button>
        <button v-if="lease.status==='Draft' && store.can('lease.submit') && res.run" class="btn" :disabled="busy" @click="act('submit')"><AppIcon name="send" :size="14"/> Submit for review</button>
        <button v-if="lease.status==='Prepared' && store.can('lease.review')" class="btn" :disabled="busy" @click="act('start_review')"><AppIcon name="eye" :size="14"/> Start review</button>
        <button v-if="['Prepared','Under Review'].includes(lease.status) && store.can('lease.approve')" class="btn primary" :disabled="busy" @click="act('approve')"><AppIcon name="badge-check" :size="14"/> Approve</button>
        <button v-if="['Prepared','Under Review'].includes(lease.status) && store.can('lease.review')" class="btn danger" :disabled="busy" @click="act('return')"><AppIcon name="rotate-ccw" :size="14"/> Return</button>
        <button v-if="canEvent && lease.status!=='Draft'" class="btn" @click="showEvent=true"><AppIcon name="git-branch" :size="14"/> Record event</button>
        <button v-if="['Approved','Posted','Modified'].includes(lease.status) && store.can('lease.approve')" class="btn" :disabled="busy" @click="act('reopen')"><AppIcon name="lock-open" :size="14"/> Reopen</button>
        <ExportMenu v-if="res.run && store.can('export')" :items="exportItems"/>
        <button v-if="store.can('settings.write') && lease.status!=='Archived'" class="btn icon ghost" title="Archive" @click="act('archive')"><AppIcon name="trash-2" :size="14"/></button>
      </div>
    </div>

    <div v-if="calcError" class="alert bad mb"><AppIcon name="circle-x"/><div class="grow"><b>{{ calcError.message }}</b>
      <ul style="margin:4px 0 0 16px;padding:0"><li v-for="(i, k) in calcError.issues" :key="k">{{ i.message || i }}<span v-if="i.reference" class="muted"> ({{ i.reference }})</span></li></ul></div>
      <button class="btn sm ghost" @click="calcError=null"><AppIcon name="x" :size="13"/></button></div>
    <div v-if="lease.stale && lease.status==='Draft'" class="alert warn mb"><AppIcon name="triangle-alert"/><div class="grow">Inputs changed after the last calculation — recalculate before submitting.</div></div>
    <div v-if="!res.run && lease.status==='Draft'" class="alert info mb"><AppIcon name="info"/><div class="grow" v-if="isLessor">Not calculated yet. Complete the contract dates, options, payments (and any deposit received), then the <b>Classification</b> inputs — fair value, carrying amount and economic life of the asset (or record the classification with a rationale) — and click <b>Calculate</b>.</div>
      <div class="grow" v-else>Not calculated yet. Complete the contract dates, options (reasonably-certain judgments), payments and discount rate, then click <b>Calculate</b>.</div></div>
    <div v-if="lease.status!=='Draft' && lease.status!=='Archived'" class="alert info mb"><AppIcon name="lock"/><div class="grow">This lease is <b>{{ lease.status }}</b> — inputs are locked. Record a modification / reassessment as an event, or reopen for correction (reason required).</div></div>
    <div v-if="res.run && res.run.status!=='Approved' && res.run.status!=='Posted' && lease.status!=='Draft'" class="alert warn mb"><AppIcon name="hourglass"/><div class="grow">Calculation run #{{ res.run.run_no }} is {{ res.run.status }} — figures are provisional until approved.</div></div>
    <div v-if="isLessor && s && !s.segments" class="alert warn mb"><AppIcon name="triangle-alert"/><div class="grow">This calculation was produced by the previous lessor engine (before v1.1): the classification evidence, maturity analysis, reconciliation and lessor note are not available for it. {{ lease.status==='Draft' ? 'Click Calculate to recalculate with the current engine.' : 'Reopen the lease (reason: recalculation with lessor engine 2.0), recalculate and send it for approval again.' }}</div></div>

    <Tabs :tabs="tabs" v-model="tab"/>

    <!-- ================================================================ OVERVIEW -->
    <div v-if="tab==='overview'">
      <template v-if="kind==='LESSEE'">
        <div class="grid c6 mb">
          <Kpi label="Initial lease liability" :value="initial.liability" money :foot="'At ' + date(initial.measurement_date)"/>
          <Kpi label="Initial ROU asset" :value="initial.rou" money foot="Cost incl. IDC, restoration, prepaid"/>
          <Kpi :label="'Liability at ' + date(store.asOf)" :value="rowAsOf ? rowAsOf.liab_close : null" money :foot="rowAsOf ? 'Current ' + money(rowAsOf.liab_current) : 'Not commenced'"/>
          <Kpi :label="'ROU NBV at ' + date(store.asOf)" :value="rowAsOf ? rowAsOf.rou_close : null" money :foot="rowAsOf ? 'Period ended ' + date(rowAsOf.period_end) : ''"/>
          <Kpi label="Lease term" :value="(Number(term.term_months) % 1 === 0 ? Number(term.term_months) : num(term.term_months, 2)) + ' months'" :foot="date(term.commencement) + ' to ' + date(term.term_end)"/>
          <Kpi label="Discount rate" :value="num(initial.rate_pct, 2) + '%'" :foot="initial.daycount + ' · ' + titleCase(initial.convention)"/>
        </div>
        <div v-if="s.currency && s.currency !== (store.company?.functional_currency || 'INR')" class="alert info mb"><AppIcon name="coins"/><div>Amounts on this page are in {{ s.currency }} (contract currency). The functional-currency view (liability at closing rates, ROU at historical rates) is under Liability schedule → Functional currency.</div></div>
        <div class="grid side mb">
          <div class="card"><div class="card-head"><h3>Liability and ROU asset over the lease term</h3><span class="sub">Closing balances by period</span></div>
            <div class="card-body"><LineChart :labels="chart.labels" :series="chart.series" :label-format="monLabel" :height="260"/></div></div>
          <div class="card"><div class="card-head"><h3>Lease term determination</h3><span class="sub">Ind AS 116.18–21</span></div>
            <div class="card-body">
              <dl class="kv"><dt>Commencement</dt><dd>{{ date(term.commencement) }}</dd><dt>Non-cancellable period ends</dt><dd>{{ date(term.noncancellable_end) }}</dd>
                <dt>Contract end</dt><dd>{{ date(term.contract_end) }}</dd><dt>Lease term ends</dt><dd>{{ date(term.term_end) }}</dd>
                <dt>Longest possible end</dt><dd>{{ date(term.max_possible_end) }}</dd><dt>Purchase option reasonably certain</dt><dd>{{ term.purchase_option_rc ? 'Yes' : 'No' }}</dd></dl>
              <ul class="small text-2" style="margin:10px 0 0 16px;padding:0"><li v-for="(x, i) in term.explanation" :key="i">{{ x }}</li></ul>
            </div></div>
        </div>
        <div class="grid c2 mb">
          <div class="card"><div class="card-head"><h3>Judgments, flags and exceptions</h3><span class="sub">{{ (s.flags || []).length }} flag(s) · {{ (s.issues || []).length }} issue(s)</span></div>
            <div class="card-body"><IssueList :issues="s.issues"/><div class="mt" v-if="(s.issues||[]).length"></div><FlagList :flags="s.flags"/></div></div>
          <div class="card"><div class="card-head"><h3>Totals over the lease</h3></div>
            <div class="card-body">
              <div class="stat-line"><span>Undiscounted lease payments included in the liability</span><span class="num">{{ money(initial.undiscounted_total) }}</span></div>
              <div class="stat-line"><span>Total interest (finance cost)</span><span class="num">{{ money(s.totals.total_interest) }}</span></div>
              <div class="stat-line"><span>Total depreciation</span><span class="num">{{ money(s.totals.total_depreciation) }}</span></div>
              <div class="stat-line" v-if="Number(s.totals.total_impairment)"><span>Total impairment</span><span class="num">{{ money(s.totals.total_impairment) }}</span></div>
              <div class="stat-line" v-if="Number(s.totals.total_gain_loss)"><span>Gains / (losses) on events</span><span class="num">{{ money(s.totals.total_gain_loss) }}</span></div>
              <div class="stat-line"><span>Total payments through the liability</span><span class="num">{{ money(s.totals.total_payments) }}</span></div>
              <div class="stat-line total"><span>Closing liability / ROU at end of schedule</span><span class="num">{{ money(s.totals.final_liability) }} / {{ money(s.totals.final_rou) }}</span></div>
              <div class="small muted mt">Engine {{ s.engine_version }} · calculated {{ dateTime(s.calculated_at) }} · inputs hash {{ res.run.inputs_hash?.slice(0, 12) }}</div>
            </div></div>
        </div>
        <div class="card mb" v-if="s.slb"><div class="card-head"><h3>Sale and leaseback</h3><span class="sub">Ind AS 116.98–103 · {{ s.slb.is_sale ? 'Transfer is a sale' : 'Not a sale — financing' }}</span></div>
          <div class="card-body flush"><table class="t compact"><thead><tr><th>Step</th><th class="num">Amount</th><th>Explanation</th></tr></thead>
            <tbody><tr v-for="(x, i) in s.slb.steps" :key="i"><td>{{ x[0] }}</td><td class="num">{{ money(x[1]) }}</td><td class="small text-2 wrap">{{ x[2] }}</td></tr></tbody></table>
            <div class="card-body"><FlagList :flags="s.slb.flags"/></div></div></div>
      </template>

      <template v-else-if="kind==='EXEMPT'">
        <div class="alert mb" :class="s.valid ? 'ok' : 'bad'"><AppIcon :name="s.valid ? 'shield-check' : 'circle-x'"/>
          <div><b>{{ s.exemption === 'SHORT_TERM' ? 'Short-term' : 'Low-value' }} exemption {{ s.valid ? 'validated' : 'NOT supported' }}</b> — {{ s.reference }}
            <ul style="margin:4px 0 0 16px;padding:0"><li v-for="(r, i) in s.reasons" :key="i">{{ r }}</li></ul></div></div>
        <IssueList :issues="s.issues" class="mb"/>
        <div class="grid c4 mb"><Kpi label="Total straight-line expense" :value="s.total_expense" money/><Kpi label="Lease term" :value="num(s.term_months, 2) + ' months'"/></div>
        <div class="card"><div class="card-head"><h3>Expense schedule</h3><span class="sub">Straight-line over the lease term (para 6)</span></div>
          <DataTable id="exempt" :columns="[{key:'period_end',label:'Period end',type:'date'},{key:'expense',label:'Lease expense',type:'money'},{key:'variable_expense',label:'Variable expense',type:'money'},{key:'cash_paid',label:'Cash paid',type:'money'},{key:'accrued_liability',label:'Accrual / (prepayment)',type:'money'}]" :rows="s.rows" :searchable="false" row-key="period_end" dense :totals="{expense: sumRows('expense'), variable_expense: sumRows('variable_expense'), cash_paid: sumRows('cash_paid')}"/></div>
      </template>

      <template v-else-if="kind==='LESSOR' || kind==='SUBLEASE'">
        <div class="grid c6 mb">
          <Kpi label="Classification" :value="clsLabel(s.classification)" :foot="s.classification_final && s.classification_final !== s.classification ? 'Now: ' + clsLabel(s.classification_final) : (kind==='SUBLEASE' ? 'By reference to the head-lease ROU (B58)' : 'Paras 61–66')"/>
          <Kpi :label="kind==='LESSOR' ? 'Rate implicit in the lease' : 'Discount rate used'" :value="(s.implicit_rate_pct || s.rate_pct) ? num(s.implicit_rate_pct || s.rate_pct, 4) + '%' : 'Not needed'" :foot="s.rate_source ? titleCase(s.rate_source) : ''"/>
          <Kpi v-if="s.classification === 'FINANCE'" label="Net investment at commencement" :value="s.net_investment" money :foot="'Unearned finance income ' + money(s.unearned_finance_income)"/>
          <Kpi v-else label="Lease income over the term" :value="s.totals?.total_lease_income" money :foot="(s.income_method === 'DAILY' ? 'Straight-line, daily' : 'Straight-line, equal monthly') + ' (para 81)'"/>
          <Kpi v-if="pos && pos.classification === 'FINANCE'" :label="'Net investment at ' + date(pos.row_period_end || store.asOf)" :value="pos.ni_close" money :foot="'Current ' + money(pos.ni_current) + (Number(pos.loss_allowance) ? ' · allowance ' + money(pos.loss_allowance) : '')"/>
          <Kpi v-else :label="'Accrued / (deferred) income at ' + date((pos && pos.row_period_end) || store.asOf)" :value="pos ? pos.accrued_lease_income : null" money foot="Straight-lining balance"/>
          <Kpi :label="'Income — FY to ' + date(store.asOf)" :value="decAdd(lFy.finance_income, lFy.lease_income, lFy.variable_income)" money :foot="s.classification === 'FINANCE' ? 'Finance income ' + money(lFy.finance_income) : 'Straight-line ' + money(lFy.lease_income)"/>
          <Kpi v-if="s.term" label="Lease term" :value="(Number(s.term.term_months) % 1 === 0 ? Number(s.term.term_months) : num(s.term.term_months, 2)) + ' months'" :foot="date(s.term.commencement) + ' to ' + date(s.term.term_end)"/>
          <Kpi v-else label="Lease term" :value="'—'"/>
        </div>
        <div class="grid side mb">
          <div class="card"><div class="card-head"><h3>{{ lChart.series[0].label }} over the lease term</h3><span class="sub">Closing balances by period</span></div>
            <div class="card-body"><LineChart :labels="lChart.labels" :series="lChart.series" :label-format="monLabel" :height="240"/></div></div>
          <div class="card"><div class="card-head"><h3>Classification evidence</h3><span class="sub">{{ kind==='SUBLEASE' ? 'Ind AS 116.B58' : 'Ind AS 116.61–66' }}</span></div>
            <div class="card-body">
              <table class="t compact" v-if="s.indicators"><thead><tr><th>Ref</th><th>Indicator</th><th>Met?</th></tr></thead>
                <tbody><tr v-for="x in s.indicators" :key="x.code"><td class="nowrap">{{ x.code }}</td><td class="wrap small">{{ x.indicator }}<div v-if="x.note" class="tiny muted">{{ x.note }}</div></td>
                  <td><span class="badge" :class="x.met === true ? 'ok' : x.met === false ? 'draft' : 'warn'">{{ metLabel(x.met) }}</span></td></tr></tbody></table>
              <ul class="small text-2" style="margin:10px 0 0 16px;padding:0"><li v-for="(x, i) in (s.explanation || [])" :key="i">{{ x }}</li></ul>
            </div></div>
        </div>
        <div class="grid c2 mb">
          <div class="card"><div class="card-head"><h3>Judgments, flags and issues</h3><span class="sub">{{ (s.flags || []).length }} flag(s) · {{ (s.issues || []).length }} issue(s)</span></div>
            <div class="card-body"><IssueList :issues="s.issues"/><div class="mt" v-if="(s.issues||[]).length"></div><FlagList :flags="s.flags"/></div></div>
          <div class="card"><div class="card-head"><h3>Totals over the lease</h3></div>
            <div class="card-body">
              <template v-if="s.classification === 'FINANCE'">
                <div class="stat-line"><span>Gross investment (payments receivable + unguaranteed residual)</span><span class="num">{{ money(s.gross_investment) }}</span></div>
                <div class="stat-line"><span>Unearned finance income</span><span class="num">{{ money(s.unearned_finance_income) }}</span></div>
                <div class="stat-line"><span>PV of unguaranteed residual value</span><span class="num">{{ money(s.pv_unguaranteed_residual) }}</span></div>
                <div class="stat-line" v-if="Number(s.receivable_at_commencement)"><span>Lease payments received at / before commencement</span><span class="num">{{ money(s.receivable_at_commencement) }}</span></div>
                <div class="stat-line" v-if="Number(s.revenue)"><span>Selling profit / (loss) at commencement (paras 71–72)</span><span class="num">{{ money(s.selling_profit) }}</span></div>
                <div class="stat-line" v-if="Number(s.revenue)"><span>Revenue / cost of sale (manufacturer / dealer)</span><span class="num">{{ money(s.revenue) }} / {{ money(s.cost_of_sale) }}</span></div>
                <div class="stat-line" v-if="!Number(s.revenue)"><span>Gain / (loss) on derecognition of the asset (Ind AS 16.68) — other income</span><span class="num">{{ money(s.derecognition_gain || 0) }}</span></div>
              </template>
              <div class="stat-line"><span>Finance income over the term</span><span class="num">{{ money(s.totals?.total_finance_income) }}</span></div>
              <div class="stat-line"><span>Operating lease income over the term</span><span class="num">{{ money(s.totals?.total_lease_income) }}</span></div>
              <div class="stat-line" v-if="Number(s.totals?.total_variable_income)"><span>Variable lease income</span><span class="num">{{ money(s.totals?.total_variable_income) }}</span></div>
              <div class="stat-line" v-if="Number(s.totals?.total_non_lease_income)"><span>Non-lease revenue (Ind AS 115)</span><span class="num">{{ money(s.totals?.total_non_lease_income) }}</span></div>
              <div class="stat-line"><span>Lease payments billed</span><span class="num">{{ money(s.totals?.total_receipts) }}</span></div>
              <div class="stat-line" v-if="Number(s.totals?.total_deposit_unwinding)"><span>Deposit unwinding (finance cost)</span><span class="num">{{ money(s.totals?.total_deposit_unwinding) }}</span></div>
              <div class="stat-line" v-if="Number(s.totals?.total_gain_loss)"><span>Gains / (losses) on events</span><span class="num">{{ money(s.totals?.total_gain_loss) }}</span></div>
              <div class="small muted mt" v-if="res.run">Lessor engine {{ s.engine_version || '' }} · calculated {{ dateTime(s.calculated_at) }} · inputs hash {{ res.run.inputs_hash?.slice(0, 12) }}</div>
            </div></div>
        </div>
        <div class="card mb" v-if="s.deposit"><div class="card-head"><h3>Security deposit received</h3><span class="sub">Ind AS 109 — financial liability at fair value</span></div>
          <div class="card-body"><div class="grid c4"><Kpi label="Amount received" :value="s.deposit.amount_received" money/><Kpi label="Initial fair value" :value="s.deposit.initial_fair_value" money :foot="'Market rate ' + num(s.deposit.market_rate_pct, 2) + '%'"/>
            <Kpi label="Lease payment received in advance" :value="s.deposit.lease_payment_element" money foot="Excess over fair value"/><Kpi :label="'Carrying amount at ' + date(store.asOf)" :value="pos ? pos.deposit_carrying : null" money :foot="'Refund ' + date(s.deposit.refund_date)"/></div></div></div>
      </template>
      <template v-else-if="kind==='SLB_FAILED'">
        <div class="alert warn"><AppIcon name="triangle-alert"/><div>The transfer is not a sale (para 103): the seller-lessee continues to recognise the asset and recognises a financial liability (Ind AS 109) for the proceeds.</div></div>
      </template>
      <Empty v-else icon="calculator" text="No calculation yet."/>
    </div>

    <!-- ================================================================ CONTRACT -->
    <div v-if="tab==='contract'" class="col" style="gap:14px">
      <ContractForm :lease="lease" :editable="editable" @saved="load"/>
      <OptionsEditor :lease="lease" :editable="editable" :term="term" @saved="load"/>
      <DetailsForm v-if="lease.lease_type==='SUBLEASE'" :lease="lease" field="sublease_details" :editable="editable" @saved="load"/>
      <DetailsForm v-if="lease.lease_type==='SALE_LEASEBACK'" :lease="lease" field="slb_details" :editable="editable" @saved="load"/>
      <DetailsForm v-if="lease.role==='LESSEE' && lease.lease_type==='STANDARD'" :lease="lease" field="opening_balance" :editable="editable" @saved="load"/>
    </div>

    <!-- ================================================================ CLASSIFICATION (lessor) -->
    <div v-if="tab==='classification'" class="col" style="gap:14px">
      <div class="alert info"><AppIcon name="info"/><div class="small">The lease is classified at inception from the indicators in paras 63–64: enter the fair value, carrying amount and economic life of the asset so the PV and term tests can be performed. Enter the unguaranteed residual value (or the implicit rate) for a finance lease. Where you conclude the classification yourself, record it with a rationale — nothing is assumed.</div></div>
      <DetailsForm :lease="lease" field="lessor_details" :editable="editable" @saved="load"/>
      <div class="card" v-if="s && s.indicators"><div class="card-head"><h3>Result of the last calculation</h3><span class="sub">Suggested {{ clsLabel(s.suggested_classification) }} · recorded {{ clsLabel(s.classification) }}</span></div>
        <div class="card-body"><table class="t compact"><thead><tr><th>Ref</th><th>Indicator</th><th>Met?</th><th class="num">Value %</th><th>Evidence</th></tr></thead>
          <tbody><tr v-for="x in s.indicators" :key="x.code"><td>{{ x.code }}</td><td class="wrap">{{ x.indicator }}</td><td><span class="badge" :class="x.met === true ? 'ok' : x.met === false ? 'draft' : 'warn'">{{ metLabel(x.met) }}</span></td>
            <td class="num">{{ x.value ? num(x.value, 2) : '—' }}</td><td class="small text-2 wrap">{{ x.note }}</td></tr></tbody></table></div></div>
    </div>

    <!-- ================================================================ ASSESSMENT -->
    <div v-if="tab==='assessment'"><AssessmentForm :lease="lease" :editable="editable" :threshold="threshold" @saved="load"/></div>

    <!-- ================================================================ PAYMENTS -->
    <div v-if="tab==='payments'">
      <div class="pill-tabs mb"><button :class="{on: paySub==='terms'}" @click="paySub='terms'">Payment terms</button><button :class="{on: paySub==='schedule'}" @click="paySub='schedule'">Schedule ({{ (lease.payments||[]).length }})</button>
        <button v-if="!isLessor" :class="{on: paySub==='costs'}" @click="paySub='costs'">IDC, incentives, prepayments</button><button :class="{on: paySub==='deposit'}" @click="paySub='deposit'">{{ isLessor ? 'Security deposit received' : 'Security deposit' }}</button>
        <button v-if="!isLessor" :class="{on: paySub==='restoration'}" @click="paySub='restoration'">Restoration</button></div>
      <div v-if="isLessor && paySub==='terms'" class="alert info mb"><AppIcon name="info"/><div class="small">Lease payments receivable from the lessee. Enter CAM / service charges as non-lease amounts (revenue under Ind AS 115, para 17) and sales-based rent as variable lines (income when earned). Initial direct costs are entered on the Classification tab.</div></div>
      <PaymentTermsCard v-if="paySub==='terms'" :lease="lease" :editable="editable" @saved="load(); paySub='schedule'"/>
      <PaymentScheduleEditor v-if="paySub==='schedule'" :lease="lease" :editable="editable" :summary="s" @saved="load"/>
      <CostsEditor v-if="paySub==='costs'" :lease="lease" :editable="editable" @saved="load"/>
      <DepositForm v-if="paySub==='deposit'" :lease="lease" :editable="editable" @saved="load"/>
      <RestorationForm v-if="paySub==='restoration'" :lease="lease" :editable="editable" @saved="load"/>
    </div>

    <!-- ================================================================ RATE -->
    <div v-if="tab==='rate'"><RatePanel :lease="lease" :editable="editable" :initial="initial" @saved="load"/></div>

    <!-- ================================================================ LIABILITY -->
    <div v-if="tab==='liability'">
      <Empty v-if="kind!=='LESSEE'" icon="calculator" text="Calculate the lease to see the liability schedule."/>
      <template v-else>
        <div class="row mb wrap">
          <div class="pill-tabs"><button :class="{on: liabSub==='periods'}" @click="liabSub='periods'">By period</button><button :class="{on: liabSub==='payments'}" @click="liabSub='payments'">By payment</button>
            <button :class="{on: liabSub==='initial'}" @click="liabSub='initial'">Initial measurement</button><button v-if="isFx" :class="{on: liabSub==='fx'}" @click="liabSub='fx'">Functional currency</button></div>
          <div class="pill-tabs" v-if="liabSub==='periods'"><button :class="{on: view==='monthly'}" @click="view='monthly'">Monthly</button><button :class="{on: view==='fy'}" @click="view='fy'">Financial year</button></div>
          <div class="spacer"></div>
          <button class="btn sm" v-if="store.can('export')" @click="exp('schedule.xlsx')"><AppIcon name="file-spreadsheet" :size="13"/> Excel</button>
          <button class="btn sm" v-if="store.can('export')" @click="exp('workpaper.xlsx')"><AppIcon name="file-check" :size="13"/> Workpaper</button>
        </div>
        <div class="card" v-if="liabSub==='periods'">
          <DataTable dense id="liab" :columns="liabCols" :rows="liabRows" :searchable="false" row-key="period_end" :page-size="view==='fy' ? 50 : 25" :totals="totalsOf(liabRows, liabCols)">
            <template #cell-explain="{ row }"><button v-if="view==='monthly'" class="btn sm ghost icon" style="height:22px;width:22px" @click.stop="explainPe=row.period_end" title="How was this calculated?" aria-label="How was this calculated?"><AppIcon name="circle-help" :size="14"/></button></template>
          </DataTable>
        </div>
        <div class="card" v-if="liabSub==='payments'">
          <div class="card-head"><h3>Payment-level amortisation</h3><span class="sub">Interest accrued between payments on the effective-interest basis</span></div>
          <DataTable dense id="payrows" :columns="payCols" :rows="s.payment_rows" :searchable="false" row-key="no"/>
        </div>
        <div v-if="liabSub==='initial'" class="grid side">
          <div class="card"><div class="card-head"><h3>Present value of lease payments at {{ date(initial.measurement_date) }}</h3><span class="sub">Ind AS 116.26–28</span></div>
            <div class="card-body"><div class="formula mb-sm">PV = Σ payment × 1 / (1 + {{ num(initial.effective_annual_rate * 100, 6) }}%)<sup>t</sup> · t in years ({{ initial.daycount }}) · payments at commencement are treated as paid (not discounted)</div></div>
            <div class="table-wrap" style="max-height:520px"><table class="t compact"><thead><tr><th>Date</th><th>Category</th><th class="num">Payment</th><th class="num">t (years)</th><th class="num">Discount factor</th><th class="num">Present value</th></tr></thead>
              <tbody><tr v-for="(p, i) in initial.pv_lines" :key="i"><td>{{ date(p.date) }}</td><td class="small">{{ titleCase(p.category) }}</td><td class="num">{{ money(p.amount) }}</td><td class="num mono">{{ num(p.years, 6) }}</td><td class="num mono">{{ num(p.discount_factor, 8) }}</td><td class="num">{{ money(p.present_value) }}</td></tr>
                <tr class="total"><td colspan="2">Total</td><td class="num">{{ money(initial.undiscounted_total) }}</td><td></td><td></td><td class="num">{{ money(initial.liability) }}</td></tr></tbody></table></div></div>
          <div class="col" style="gap:14px">
            <div class="card"><div class="card-head"><h3>Measurement</h3></div><div class="card-body">
              <div class="stat-line"><span>PV (unrounded)</span><span class="num mono">{{ num(initial.liability_exact, 6) }}</span></div>
              <div class="stat-line total"><span>Lease liability recognised</span><span class="num">{{ money(initial.liability) }}</span></div>
              <div class="stat-line"><span>Rate / effective annual</span><span class="num">{{ num(initial.rate_pct, 4) }}% / {{ num(initial.effective_annual_rate * 100, 6) }}%</span></div>
              <div class="stat-line"><span>Depreciation to</span><span>{{ date(initial.depreciation_end) }}</span></div></div></div>
            <div class="card"><div class="card-head"><h3>Excluded from the liability</h3><span class="sub">{{ (initial.excluded||[]).length }} line(s)</span></div>
              <div class="table-wrap" style="max-height:300px"><table class="t compact"><thead><tr><th>Date</th><th class="num">Amount</th><th>Reason</th></tr></thead>
                <tbody><tr v-if="!(initial.excluded||[]).length"><td colspan="3" class="empty">None</td></tr><tr v-for="(p, i) in initial.excluded" :key="i"><td>{{ date(p.date) }}</td><td class="num">{{ money(p.amount) }}</td><td class="small text-2 wrap">{{ p.reason }}</td></tr></tbody></table></div></div>
          </div>
        </div>
        <div class="card" v-if="liabSub==='fx'">
          <div class="card-head"><h3>Functional-currency view</h3><span class="sub">Ind AS 21: liability (monetary) at closing rate, interest at average rate, payments at spot; ROU (non-monetary) at historical rate</span></div>
          <DataTable dense id="fx" :columns="fxCols" :rows="s.fx_periods" :searchable="false" row-key="period_end"/>
        </div>
      </template>
    </div>

    <!-- ================================================================ ROU -->
    <div v-if="tab==='rou'">
      <Empty v-if="kind!=='LESSEE'" icon="calculator" text="Calculate the lease to see the ROU schedule."/>
      <template v-else>
        <div class="row mb wrap">
          <div class="pill-tabs"><button :class="{on: rouSub==='rou'}" @click="rouSub='rou'">ROU asset</button><button :class="{on: rouSub==='pl'}" @click="rouSub='pl'">P&amp;L and cash</button>
            <button v-if="hasProv" :class="{on: rouSub==='prov'}" @click="rouSub='prov'">Restoration provision</button><button v-if="hasDep" :class="{on: rouSub==='dep'}" @click="rouSub='dep'">Security deposit</button></div>
          <div class="pill-tabs"><button :class="{on: view==='monthly'}" @click="view='monthly'">Monthly</button><button :class="{on: view==='fy'}" @click="view='fy'">Financial year</button></div>
        </div>
        <div class="grid side" v-if="rouSub==='rou'">
          <div class="card"><DataTable dense id="rou" :columns="rouCols" :rows="liabRows" :searchable="false" row-key="period_end" :totals="totalsOf(liabRows, rouCols)">
            <template #cell-explain="{ row }"><button v-if="view==='monthly'" class="btn sm ghost icon" style="height:22px;width:22px" @click.stop="explainPe=row.period_end" title="How was this calculated?" aria-label="How was this calculated?"><AppIcon name="circle-help" :size="14"/></button></template></DataTable></div>
          <div class="card"><div class="card-head"><h3>ROU asset at commencement</h3><span class="sub">Ind AS 116.24</span></div><div class="card-body">
            <div class="stat-line" v-for="(c, i) in initial.rou_components" :key="i"><span>{{ c[0] }} <span class="muted small">{{ c[2] }}</span></span><span class="num">{{ money(c[1]) }}</span></div>
            <div class="stat-line total"><span>Cost of ROU asset</span><span class="num">{{ money(initial.rou) }}</span></div>
            <div class="small muted mt">Depreciated to {{ date(initial.depreciation_end) }}</div></div></div>
        </div>
        <div class="card" v-if="rouSub==='pl'"><DataTable dense id="pl" :columns="plCols" :rows="liabRows" :searchable="false" row-key="period_end" :totals="totalsOf(liabRows, plCols)"/></div>
        <div class="card" v-if="rouSub==='prov'"><div class="card-head"><h3>Restoration provision</h3><span class="sub">Ind AS 37 — unwinding is a finance cost</span></div><DataTable dense id="prov" :columns="provCols" :rows="liabRows" :searchable="false" row-key="period_end" :totals="totalsOf(liabRows, provCols)"/></div>
        <div class="card" v-if="rouSub==='dep'"><div class="card-head"><h3>Security deposit — amortised cost</h3><span class="sub">Ind AS 109 effective interest</span></div>
          <div class="card-body" v-if="s.deposit"><div class="grid c4"><Kpi label="Cash paid" :value="s.deposit.amount_paid" money/><Kpi label="Initial fair value" :value="s.deposit.initial_fair_value" money/><Kpi label="Prepaid rent (to ROU)" :value="s.deposit.difference_prepaid_rent" money/><Kpi label="Market rate" :value="num(s.deposit.market_rate_pct, 2) + '%'"/></div></div>
          <DataTable dense id="dep" :columns="depCols" :rows="liabRows" :searchable="false" row-key="period_end" :totals="totalsOf(liabRows, depCols)"/></div>
      </template>
    </div>

    <!-- ================================================================ LESSOR SCHEDULE -->
    <div v-if="tab==='lessor'">
      <Empty v-if="!['LESSOR','SUBLEASE'].includes(kind)" icon="calculator" text="Calculate the lease to see the schedule."/>
      <template v-else>
        <div class="row mb wrap">
          <div class="pill-tabs"><button :class="{on: lsub==='periods'}" @click="lsub='periods'">By period</button>
            <button v-if="(s.pv_lines||[]).length" :class="{on: lsub==='initial'}" @click="lsub='initial'">Initial measurement</button>
            <button :class="{on: lsub==='position'}" @click="lsub='position'">Maturity &amp; reconciliation</button>
            <button v-if="s.deposit" :class="{on: lsub==='deposit'}" @click="lsub='deposit'">Security deposit</button>
            <button :class="{on: lsub==='payments'}" @click="lsub='payments'">Lease payments</button></div>
          <div class="pill-tabs" v-if="lsub==='periods'"><button :class="{on: view==='monthly'}" @click="view='monthly'">Monthly</button><button :class="{on: view==='fy'}" @click="view='fy'">Financial year</button></div>
          <div class="spacer"></div>
          <button class="btn sm" v-if="store.can('export')" @click="exp('schedule.xlsx')"><AppIcon name="file-spreadsheet" :size="13"/> Excel</button>
          <button class="btn sm" v-if="store.can('export') && isLessor" @click="exp('workpaper.xlsx')"><AppIcon name="file-check" :size="13"/> Workpaper</button>
        </div>
        <div class="card" v-if="lsub==='periods'">
          <DataTable dense id="lessor-sched" :columns="lCols" :rows="lRowsView" :searchable="false" row-key="period_end" :page-size="view==='fy' ? 50 : 25" :totals="lTotals"/>
        </div>
        <div v-if="lsub==='initial'" class="grid side">
          <div class="card"><div class="card-head"><h3>Net investment at commencement</h3><span class="sub">PV at the rate implicit in the lease ({{ num(s.implicit_rate_pct || s.rate_pct, 4) }}%) — paras 68–70</span></div>
            <div class="table-wrap" style="max-height:520px"><table class="t compact"><thead><tr><th>Date</th><th>Kind</th><th class="num">Amount</th><th class="num">t (years)</th><th class="num">Discount factor</th><th class="num">Present value</th></tr></thead>
              <tbody><tr v-for="(p, i) in s.pv_lines" :key="i"><td>{{ date(p.date) }}</td><td class="small">{{ p.kind }}</td><td class="num">{{ money(p.amount) }}</td><td class="num mono">{{ num(p.years, 6) }}</td><td class="num mono">{{ num(p.discount_factor, 8) }}</td><td class="num">{{ money(p.present_value) }}</td></tr>
                <tr class="total"><td colspan="2">Total</td><td class="num">{{ money(s.gross_investment) }}</td><td></td><td></td><td class="num">{{ money(s.net_investment) }}</td></tr></tbody></table></div></div>
          <div class="card"><div class="card-head"><h3>Commencement</h3></div><div class="card-body">
            <div class="stat-line"><span>Net investment recognised</span><span class="num">{{ money(s.net_investment) }}</span></div>
            <div class="stat-line"><span>Unearned finance income</span><span class="num">{{ money(s.unearned_finance_income) }}</span></div>
            <div class="stat-line" v-if="Number(s.receivable_at_commencement)"><span>Lease payments due at commencement</span><span class="num">{{ money(s.receivable_at_commencement) }}</span></div>
            <div class="stat-line" v-if="Number(s.revenue)"><span>Revenue / cost of sale — selling profit / (loss) (paras 71–72)</span><span class="num">{{ money(s.revenue) }} / {{ money(s.cost_of_sale) }} — {{ money(s.selling_profit) }}</span></div>
            <div class="stat-line" v-else><span>Gain / (loss) on derecognition of the asset (Ind AS 16.68) — not selling profit</span><span class="num">{{ money(s.derecognition_gain || 0) }}</span></div>
            <div class="small muted mt">{{ s.idc && s.idc.treatment ? 'Initial direct costs ' + money(s.idc.amount) + ': ' + s.idc.treatment : '' }}</div></div></div>
        </div>
        <div v-if="lsub==='position'" class="grid c2">
          <div class="card"><div class="card-head"><h3>Undiscounted lease payments to be received at {{ date(store.asOf) }}</h3><span class="sub">{{ pos && pos.classification==='FINANCE' ? 'Ind AS 116.94' : 'Ind AS 116.97' }} · {{ clsLabel(pos && pos.classification) }}</span></div>
            <div class="card-body" v-if="pos && pos.maturity && pos.maturity.length">
              <BarChart :labels="pos.maturity.map(m => m.bucket)" :values="pos.maturity.map(m => m.amount)" value-label="Undiscounted receipts" :height="190"/>
              <div class="stat-line mt" v-for="m in pos.maturity" :key="m.bucket"><span>{{ m.bucket }}</span><span class="num">{{ money(m.amount) }}</span></div>
              <div class="stat-line total"><span>Total</span><span class="num">{{ money(pos.total_undiscounted) }}</span></div></div>
            <div class="card-body" v-else><Empty text="No lease payments to be received after this date."/></div></div>
          <div class="card"><div class="card-head"><h3>{{ pos && pos.reconciliation ? 'Reconciliation to the net investment' : 'Balances' }}</h3><span class="sub">{{ pos && pos.reconciliation ? 'Ind AS 116.94' : 'Per schedule at ' + date(pos && pos.row_period_end || store.asOf) }}</span></div>
            <div class="card-body" v-if="pos && pos.reconciliation">
              <div class="stat-line"><span>Undiscounted lease payments receivable</span><span class="num">{{ money(pos.reconciliation.undiscounted_lease_payments) }}</span></div>
              <div class="stat-line"><span>Less: unearned finance income</span><span class="num">({{ money(pos.reconciliation.unearned_finance_income) }})</span></div>
              <div class="stat-line"><span>Present value of lease payments receivable</span><span class="num">{{ money(pos.reconciliation.pv_lease_payments) }}</span></div>
              <div class="stat-line"><span>Add: discounted unguaranteed residual value</span><span class="num">{{ money(pos.reconciliation.discounted_unguaranteed_residual) }}</span></div>
              <div class="stat-line total"><span>Net investment in the lease</span><span class="num">{{ money(pos.reconciliation.net_investment) }}</span></div>
              <div class="stat-line" v-if="pos.reconciliation.ni_per_schedule !== null"><span>Per schedule — difference</span><span class="num">{{ money(pos.reconciliation.ni_per_schedule) }} — {{ money(pos.reconciliation.difference) }}</span></div>
              <div class="small muted" v-else style="padding:4px 0">Present values at the end of {{ date(store.asOf) }} (includes finance income accrued since {{ date(pos.row_period_end) }}); choose a month-end 'As of' date to agree to the schedule.</div>
              <div class="stat-line"><span>Less: loss allowance (Ind AS 109){{ posAt }}</span><span class="num">({{ money(pos.loss_allowance) }})</span></div>
              <div class="stat-line"><span>Current / non-current{{ posAt }}</span><span class="num">{{ money(pos.ni_current) }} / {{ money(pos.ni_noncurrent) }}</span></div>
            </div>
            <div class="card-body" v-else-if="pos">
              <div class="stat-line"><span>Accrued / (deferred) lease income</span><span class="num">{{ money(pos.accrued_lease_income) }}</span></div>
              <div class="stat-line" v-if="Number(pos.idc_carrying)"><span>Initial direct costs (in the asset)</span><span class="num">{{ money(pos.idc_carrying) }}</span></div>
              <div class="stat-line" v-if="Number(pos.deposit_carrying)"><span>Security deposit received (carrying)</span><span class="num">{{ money(pos.deposit_carrying) }}</span></div>
              <div class="stat-line" v-if="Number(pos.loss_allowance)"><span>Loss allowance</span><span class="num">{{ money(pos.loss_allowance) }}</span></div>
            </div></div>
        </div>
        <div class="card" v-if="lsub==='deposit' && s.deposit"><div class="card-head"><h3>Security deposit received — amortised cost</h3><span class="sub">Ind AS 109 · unwinding is a finance cost</span></div>
          <div class="card-body"><div class="grid c4"><Kpi label="Amount received" :value="s.deposit.amount_received" money/><Kpi label="Initial fair value" :value="s.deposit.initial_fair_value" money/><Kpi label="Lease payment in advance" :value="s.deposit.lease_payment_element" money/><Kpi label="Market rate" :value="num(s.deposit.market_rate_pct, 2) + '%'"/></div></div>
          <DataTable dense id="lessor-dep" :columns="[{key:'period_end',label:'Period end',type:'date'},{key:'dep_open',label:'Opening',type:'money'},{key:'dep_additions',label:'Recognised',type:'money'},{key:'dep_unwinding',label:'Unwinding',type:'money'},{key:'dep_refund',label:'Refund',type:'money'},{key:'dep_close',label:'Closing',type:'money'}]"
            :rows="lRows.filter(r => Number(r.dep_open) || Number(r.dep_close) || Number(r.dep_additions) || Number(r.dep_refund))" :searchable="false" row-key="period_end"/></div>
        <div class="card" v-if="lsub==='payments'"><div class="card-head"><h3>Lease payments and their treatment</h3><span class="sub">Ind AS 116.70 · variable and non-lease amounts are not lease payments</span></div>
          <DataTable dense id="lessor-pay" :columns="[{key:'date',label:'Date',type:'date'},{key:'category',label:'Category',format: (v) => titleCase(v || '')},{key:'lease_amount',label:'Lease amount',type:'money'},{key:'non_lease_amount',label:'Non-lease',type:'money'},{key:'included',label:'Lease payment?',format: (v) => v ? 'Yes' : 'No'},{key:'inclusion_reason',label:'Treatment',wrap:true}]"
            :rows="s.payments || []" :searchable="true" row-key="line_no"/></div>
      </template>
    </div>

    <!-- ================================================================ EVENTS -->
    <div v-if="tab==='events'">
      <div class="row mb"><div class="grow small text-2" v-if="isLessor">Lessor events: modifications (para 87 for operating leases; paras 79–80 for finance leases), early termination, reduction of the unguaranteed residual value (para 77) and expected credit losses (Ind AS 109). Each event triggers a new calculation run; earlier approved runs are preserved.</div>
        <div class="grow small text-2" v-else>Modifications, reassessments, terminations, impairments and other events. Each recorded event triggers a new calculation run; earlier approved runs are preserved.</div>
        <button v-if="canEvent" class="btn primary" @click="showEvent=true"><AppIcon name="plus" :size="14"/> Record event</button></div>
      <div v-if="!(lease.events||[]).length" class="card"><Empty icon="git-branch" text="No events recorded for this lease."/></div>
      <div v-for="ev in lease.events" :key="ev.id" class="card mb">
        <div class="card-head"><AppIcon name="git-branch" :size="15"/><h3>{{ labelEvtL(ev) }}</h3><span class="sub">{{ isLessor ? titleCase(ev.subtype || '') : labelSub(ev.subtype) }} · effective {{ date(ev.effective_date) }}</span><div class="spacer"></div>
          <StatusBadge :status="ev.status"/><button v-if="ev.status!=='Approved' && ev.status!=='Rejected' && store.can('event.write')" class="btn sm danger" @click="withdraw(ev)">Withdraw</button></div>
        <div class="card-body">
          <div class="small mb-sm">{{ ev.description }}</div>
          <template v-if="eventResult(ev) && isLessor">
            <div class="grid c4 mb">
              <div class="tile"><div class="label">{{ eventResult(ev).balance_label || 'Balance' }}</div><div class="value" style="font-size:15px">{{ money(eventResult(ev).balance_before) }} → {{ money(eventResult(ev).balance_after) }}</div></div>
              <div class="tile"><div class="label">Gain / (loss)</div><div class="value" style="font-size:15px" :class="isNeg(eventResult(ev).gain_loss) ? 'neg' : ''">{{ money(eventResult(ev).gain_loss) }}</div></div>
              <div class="tile"><div class="label">Classification</div><div class="value" style="font-size:14px">{{ eventResult(ev).classification_before }} → {{ eventResult(ev).classification_after }}</div></div>
              <div class="tile"><div class="label">Reference</div><div class="value" style="font-size:13px">{{ eventResult(ev).reference }}</div></div>
            </div>
            <table class="t compact"><thead><tr><th>Step</th><th class="num">Amount</th><th>Explanation</th></tr></thead>
              <tbody><tr v-for="(x, i) in eventResult(ev).steps" :key="i"><td>{{ x[0] }}</td><td class="num">{{ money(x[1]) }}</td><td class="small text-2 wrap">{{ x[2] }}</td></tr></tbody></table>
            <FlagList v-if="(eventResult(ev).flags || []).length" :flags="eventResult(ev).flags" class="mt"/>
          </template>
          <template v-else-if="eventResult(ev)">
            <div class="grid c4 mb">
              <div class="tile"><div class="label">Liability</div><div class="value" style="font-size:15px">{{ money(eventResult(ev).liability_before) }} → {{ money(eventResult(ev).liability_after) }}</div></div>
              <div class="tile"><div class="label">ROU asset</div><div class="value" style="font-size:15px">{{ money(eventResult(ev).rou_before) }} → {{ money(eventResult(ev).rou_after) }}</div></div>
              <div class="tile"><div class="label">Gain / (loss)</div><div class="value" style="font-size:15px" :class="isNeg(eventResult(ev).gain_loss) ? 'neg' : ''">{{ money(eventResult(ev).gain_loss) }}</div></div>
              <div class="tile"><div class="label">Rate · term end</div><div class="value" style="font-size:14px">{{ num(eventResult(ev).rate_before_pct, 2) }}% → {{ num(eventResult(ev).rate_after_pct, 2) }}%</div><div class="foot">{{ date(eventResult(ev).term_end_before) }} → {{ date(eventResult(ev).term_end_after) }}</div></div>
            </div>
            <table class="t compact"><thead><tr><th>Step</th><th class="num">Amount</th><th>Explanation</th></tr></thead>
              <tbody><tr v-for="(x, i) in eventResult(ev).steps" :key="i"><td>{{ x[0] }}</td><td class="num">{{ money(x[1]) }}</td><td class="small text-2 wrap">{{ x[2] }}</td></tr></tbody></table>
            <div class="small muted mt">{{ eventResult(ev).reference }}</div>
          </template>
          <div v-else class="small muted">Result available after calculation.</div>
        </div>
      </div>
    </div>

    <!-- ================================================================ JOURNALS -->
    <div v-if="tab==='journals'">
      <Empty v-if="!store.can('journal.read')" icon="lock" text="Your role cannot view journals."/>
      <template v-else>
        <div class="row mb"><select v-model="jFy" style="width:160px;min-height:30px"><option value="">All years</option><option v-for="f in jFys" :key="f" :value="f">FY {{ f.slice(0,4) }}-{{ String(Number(f.slice(0,4))+1).slice(2) }}</option></select>
          <span class="small muted">{{ jList.length }} journal(s) · from calculation run #{{ res.run?.run_no }} ({{ res.run?.status }})</span><div class="spacer"></div>
          <a class="btn sm" href="#/journals">Portfolio journals &amp; ERP export</a></div>
        <div class="card"><div class="table-wrap" style="max-height:640px"><table class="t compact">
          <thead><tr><th></th><th>JE ref</th><th>Date</th><th>Event</th><th>Narration</th><th class="num">Debit</th><th class="num">Credit</th><th>Check</th></tr></thead>
          <tbody><tr v-if="!jList.length"><td colspan="8" class="empty">No journals in this period.</td></tr>
            <template v-for="j in jList" :key="j.je_ref">
              <tr class="clickable" @click="openJe[j.je_ref] = !openJe[j.je_ref]"><td><AppIcon :name="openJe[j.je_ref] ? 'chevron-down' : 'chevron-right'" :size="13"/></td><td class="mono nowrap">{{ j.je_ref }}</td><td class="nowrap">{{ date(j.date) }}</td><td class="nowrap">{{ j.event_label }}</td><td class="wrap small">{{ j.narration }}</td>
                <td class="num">{{ money(j.total_debit) }}</td><td class="num">{{ money(j.total_credit) }}</td><td><span class="badge" :class="j.balanced ? 'ok' : 'bad'">{{ j.balanced ? 'Balanced' : 'Unbalanced' }}</span></td></tr>
              <template v-if="openJe[j.je_ref]"><tr v-for="l in j.lines" :key="j.je_ref + l.line" style="background:var(--surface-2)"><td></td><td class="mono small">{{ l.account_code }}</td><td colspan="3" class="small">{{ l.account_name }} <span class="muted">({{ titleCase(l.role) }})</span></td>
                <td class="num small">{{ Number(l.debit) ? money(l.debit) : '' }}</td><td class="num small">{{ Number(l.credit) ? money(l.credit) : '' }}</td><td></td></tr></template>
            </template></tbody></table></div></div>
      </template>
    </div>

    <!-- ================================================================ DOCUMENTS -->
    <div v-if="tab==='documents'">
      <div class="card mb"><div class="card-head"><h3>Documents</h3><span class="sub">Agreements, addenda, IBR support, approvals — stored locally with SHA-256 hash</span><div class="spacer"></div>
        <template v-if="store.can('lease.write')"><select v-model="docType" style="width:200px;min-height:30px"><option>Lease agreement</option><option>Addendum / event evidence</option><option>IBR support</option><option>Valuation / impairment support</option><option>Approval</option><option>Other</option></select>
          <label class="btn sm primary"><AppIcon name="upload" :size="13"/> Upload<input type="file" @change="uploadDoc" style="display:none"></label></template></div>
        <table class="t compact"><thead><tr><th>Document</th><th>Type</th><th class="num">Size</th><th class="num">Pages</th><th>Uploaded</th><th></th></tr></thead>
          <tbody><tr v-if="!(lease.documents||[]).length"><td colspan="6" class="empty">No documents attached. Attach the executed agreement as audit evidence.</td></tr>
            <tr v-for="d in lease.documents" :key="d.id"><td><AppIcon name="file-text" :size="13"/> {{ d.filename }}</td><td>{{ d.doc_type }}</td><td class="num">{{ (d.size/1024).toFixed(0) }} KB</td><td class="num">{{ d.pages || '—' }}</td><td>{{ dateTime(d.uploaded_at) }}</td>
              <td class="right"><a class="btn sm" :href="'/api/documents/' + d.id + '/file'" target="_blank"><AppIcon name="external-link" :size="13"/> Open</a></td></tr></tbody></table></div>
      <div v-if="lease.source_extraction_id" class="alert info"><AppIcon name="sparkles"/><div class="grow">This lease was created from the AI agreement reader (extraction #{{ lease.source_extraction_id }}). The reviewed fields, source quotes and page highlights remain available.</div>
        <a class="btn sm" :href="'#/extract/' + lease.source_extraction_id">Open review</a></div>
    </div>

    <!-- ================================================================ DISCLOSURES & TAX -->
    <div v-if="tab==='disclosures'">
      <div v-if="kind==='LESSOR' || kind==='SUBLEASE'" class="grid c2 mb">
        <div class="card"><div class="card-head"><h3>Contribution to the lessor note — FY {{ fyNow[0].slice(0,4) }}-{{ String(Number(fyNow[0].slice(0,4))+1).slice(2) }}</h3><span class="sub">Ind AS 116.90 · to {{ date(store.asOf) }}</span></div>
          <div class="card-body">
            <div class="stat-line"><span>Finance leases — selling profit / (loss) — 90(a)(i)</span><span class="num">{{ money(lFy.selling_profit) }}</span></div>
            <div class="stat-line" v-if="Number(lFy.derecognition_gain)"><span>Gain / (loss) on derecognition of the asset — other income (Ind AS 16.68; not a para 90 item)</span><span class="num">{{ money(lFy.derecognition_gain) }}</span></div>
            <div class="stat-line"><span>Finance income on the net investment — 90(a)(ii)</span><span class="num">{{ money(lFy.finance_income) }}</span></div>
            <div class="stat-line"><span>Operating lease income — 90(b)</span><span class="num">{{ money(lFy.lease_income) }}</span></div>
            <div class="stat-line"><span>Variable lease income — 90(a)(iii) / 90(b)</span><span class="num">{{ money(lFy.variable_income) }}</span></div>
            <div class="stat-line"><span>Non-lease revenue (Ind AS 115)</span><span class="num">{{ money(lFy.non_lease_income) }}</span></div>
            <div class="stat-line" v-if="Number(lFy.dep_unwinding)"><span>Finance cost — deposit received (Ind AS 109)</span><span class="num">{{ money(lFy.dep_unwinding) }}</span></div>
            <div class="stat-line" v-if="Number(lFy.ecl_charge)"><span>Expected credit losses — lease receivables</span><span class="num">{{ money(lFy.ecl_charge) }}</span></div>
          </div></div>
        <div class="card"><div class="card-head"><h3>Maturity analysis at {{ date(store.asOf) }}</h3><span class="sub">{{ pos && pos.classification === 'FINANCE' ? 'Ind AS 116.94 (with reconciliation)' : 'Ind AS 116.97' }}</span></div>
          <div class="card-body" v-if="pos && (pos.maturity||[]).length">
            <div class="stat-line" v-for="m in pos.maturity" :key="m.bucket"><span>{{ m.bucket }}</span><span class="num">{{ money(m.amount) }}</span></div>
            <div class="stat-line total"><span>Total undiscounted</span><span class="num">{{ money(pos.total_undiscounted) }}</span></div>
            <template v-if="pos.reconciliation"><div class="stat-line"><span>Less: unearned finance income</span><span class="num">({{ money(pos.reconciliation.unearned_finance_income) }})</span></div>
              <div class="stat-line"><span>Add: discounted unguaranteed residual</span><span class="num">{{ money(pos.reconciliation.discounted_unguaranteed_residual) }}</span></div>
              <div class="stat-line total"><span>Net investment</span><span class="num">{{ money(pos.reconciliation.net_investment) }}</span></div></template>
          </div><div class="card-body" v-else><Empty text="No lease payments to be received after the reporting date."/></div></div>
      </div>
      <div v-if="kind==='LESSOR' || kind==='SUBLEASE'" class="small muted mb">Portfolio totals, the movement in the net investment (para 93) and the qualitative prompts (paras 92, 95–96) are on the Disclosures page.</div>
      <div v-if="kind!=='LESSEE' && kind!=='LESSOR' && kind!=='SUBLEASE'" class="card mb"><Empty icon="clipboard-list" text="Lease-level disclosure analysis applies to capitalised leases. Exempt lease amounts flow into the portfolio disclosures."/></div>
      <template v-if="kind==='LESSEE'">
        <div class="grid c2 mb">
          <div class="card"><div class="card-head"><h3>Contribution to the lease note — FY {{ fyNow[0].slice(0,4) }}-{{ String(Number(fyNow[0].slice(0,4))+1).slice(2) }}</h3><span class="sub">To {{ date(store.asOf) }}</span></div>
            <div class="card-body">
              <div class="stat-line"><span>Depreciation — 53(a)</span><span class="num">{{ money(fyFlows.depreciation) }}</span></div>
              <div class="stat-line"><span>Interest expense — 53(b)</span><span class="num">{{ money(fyFlows.interest) }}</span></div>
              <div class="stat-line"><span>Variable lease payments expensed — 53(e)</span><span class="num">{{ money(fyFlows.variable) }}</span></div>
              <div class="stat-line"><span>Total cash outflow — 53(g)</span><span class="num">{{ money(fyFlows.cash) }}</span></div>
              <div class="stat-line"><span>Additions to ROU — 53(h)</span><span class="num">{{ money(fyFlows.additions) }}</span></div>
              <div class="stat-line total" v-if="rowAsOf"><span>Carrying amount of ROU — 53(j)</span><span class="num">{{ money(rowAsOf.rou_close) }}</span></div>
            </div></div>
          <div class="card"><div class="card-head"><h3>Liability presentation and maturity at {{ date(rowAsOf?.period_end) }}</h3><span class="sub">47(b), 58</span></div>
            <div class="card-body" v-if="rowAsOf">
              <div class="stat-line"><span>Current lease liability</span><span class="num">{{ money(rowAsOf.liab_current) }}</span></div>
              <div class="stat-line"><span>Non-current lease liability</span><span class="num">{{ money(rowAsOf.liab_noncurrent) }}</span></div>
              <div class="stat-line total"><span>Total</span><span class="num">{{ money(rowAsOf.liab_close) }}</span></div>
              <div class="small muted mt mb-sm">Undiscounted contractual payments</div>
              <div class="stat-line" v-for="(v, k) in rowAsOf.maturity" :key="k"><span>{{ bucketLabel(k) }}</span><span class="num">{{ money(v) }}</span></div>
            </div><div class="card-body" v-else><Empty text="Lease not commenced at the reporting date."/></div></div>
        </div>
        <div class="card mb" v-if="tax && tax.available"><div class="card-head"><h3>Deferred tax — Ind AS 12</h3><span class="sub">Tax rate {{ tax.settings.tax_rate_pct }}% · ROU tax base {{ money(tax.settings.rou_tax_base) }} · liability tax base {{ money(tax.settings.liability_tax_base) }}</span></div>
          <div class="table-wrap"><table class="t compact"><thead><tr><th>Year end</th><th class="num">ROU carrying</th><th class="num">Taxable TD</th><th class="num">Liability carrying</th><th class="num">Deductible TD</th><th class="num">DTL</th><th class="num">DTA</th><th class="num">Net DTA/(DTL)</th><th class="num">P&amp;L movement</th></tr></thead>
            <tbody><tr v-for="r in tax.year_end_rows" :key="r.period_end"><td>{{ date(r.period_end) }}</td><td class="num">{{ money(r.rou_carrying) }}</td><td class="num">{{ money(r.taxable_temp_diff) }}</td><td class="num">{{ money(r.liability_carrying) }}</td><td class="num">{{ money(r.deductible_temp_diff) }}</td>
              <td class="num">{{ money(r.dtl) }}</td><td class="num">{{ money(r.dta) }}</td><td class="num">{{ money(r.net_dta_dtl) }}</td><td class="num">{{ money(r.movement_pl) }}</td></tr></tbody></table></div>
          <div class="card-body">
            <h4 class="mb-sm">Computation of income — Ind AS adjustments for FY {{ date(tax.fy[0]) }} to {{ date(tax.fy[1]) }}</h4>
            <div class="stat-line"><span>Add back: depreciation on ROU asset</span><span class="num">{{ money(tax.computation_adjustments.add_back_rou_depreciation) }}</span></div>
            <div class="stat-line"><span>Add back: interest on lease liability</span><span class="num">{{ money(tax.computation_adjustments.add_back_interest_on_lease_liability) }}</span></div>
            <div class="stat-line"><span>Add back: unwinding of restoration provision</span><span class="num">{{ money(tax.computation_adjustments.add_back_provision_unwinding) }}</span></div>
            <div class="stat-line"><span>Less: gains on modification / termination</span><span class="num">({{ money(tax.computation_adjustments.less_gain_on_modification_or_termination) }})</span></div>
            <div class="stat-line"><span>Less: lease rent paid / payable</span><span class="num">({{ money(tax.computation_adjustments.less_lease_rent_paid_or_payable) }})</span></div>
            <div class="stat-line total"><span>Net adjustment to book profit</span><span class="num">{{ money(tax.computation_adjustments.net_adjustment) }}</span></div>
            <div class="alert warn mt"><AppIcon name="triangle-alert"/><div class="small">{{ tax.disclaimer }}</div></div>
          </div></div>
        <DetailsForm :lease="lease" field="tax_settings" :editable="editable" @saved="load(); tax=null"/>
      </template>
    </div>

    <!-- ================================================================ AUDIT -->
    <div v-if="tab==='audit'">
      <div class="grid c2 mb">
        <div class="card"><div class="card-head"><h3>Calculation runs</h3><span class="sub">Immutable — each run stores its full inputs and hash</span></div>
          <table class="t compact"><thead><tr><th>Run</th><th>Status</th><th>Version</th><th>Calculated</th><th>Approved</th><th>Inputs hash</th><th></th></tr></thead>
            <tbody><tr v-for="r in lease.runs" :key="r.id"><td>#{{ r.run_no }}<span v-if="r.is_current" class="badge info" style="margin-left:4px">current</span></td><td><StatusBadge :status="r.status"/></td><td>{{ r.version_no ? 'v' + r.version_no : '—' }}</td>
              <td>{{ dateTime(r.created_at) }}</td><td>{{ dateTime(r.approved_at) }}</td><td class="mono small">{{ r.inputs_hash }}</td><td><button v-if="store.can('audit.read')" class="btn sm" @click="showInputs(r)">Inputs</button></td></tr></tbody></table></div>
        <div class="card"><div class="card-head"><h3>Approval history</h3></div><div class="card-body">
          <div v-if="!(lease.approvals||[]).length" class="muted small">No workflow actions yet.</div>
          <div class="timeline"><div class="item" v-for="(a, i) in lease.approvals" :key="i"><div class="small"><b>{{ titleCase(a.action) }}</b> · {{ a.from }} → {{ a.to }}</div><div class="tiny muted">{{ dateTime(a.at) }}</div><div class="small text-2" v-if="a.comment">“{{ a.comment }}”</div></div></div>
        </div></div>
      </div>
      <div class="card"><div class="card-head"><h3>Change log</h3><span class="sub">Who changed what, when, old and new values, reason</span></div>
        <DataTable id="lease-audit" :columns="auditCols" :rows="auditRows || []" :loading="!auditRows" row-key="at"/></div>
    </div>

    <ExplainDrawer v-if="explainPe" :lease-id="id" :period-end="explainPe" :summary="s" @close="explainPe=null"/>
    <Modal v-if="showEvent" title="Record a lease event" wide @close="showEvent=false"><EventForm :lease="lease" kind="MODIFICATION" @saved="eventSaved" @cancel="showEvent=false"/></Modal>
    <Modal v-if="inputsModal" :title="'Calculation inputs — run #' + inputsModal.run.run_no" wide @close="inputsModal=null">
      <div class="small muted mb-sm">SHA-256 {{ inputsModal.data.inputs_hash }} — re-running the engine on these inputs reproduces the run.</div>
      <pre class="formula" style="max-height:60vh;overflow:auto;white-space:pre-wrap">{{ JSON.stringify(inputsModal.data.inputs, null, 2) }}</pre>
    </Modal>
  </div>`,
};
