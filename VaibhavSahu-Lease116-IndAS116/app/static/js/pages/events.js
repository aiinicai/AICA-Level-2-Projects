// Modifications, reassessments and other lease events (terminations, impairment, restoration revisions, partial derecognition)
import { store, get, post, upload, toast, showError } from '../store.js';
import { common } from '../components.js';
import { money, date, num, titleCase, today, clone } from '../util.js';
import { PaymentTermsForm, defaultTerms, CATEGORIES } from './lease_forms.js';

const { ref, computed, watch, onMounted } = Vue;

export const EVENT_TYPES = {
  MODIFICATION: { label: 'Lease modification', ref: 'Ind AS 116.44–46' },
  REASSESSMENT: { label: 'Reassessment of the lease liability', ref: 'Ind AS 116.39–43' },
  TERMINATION: { label: 'Early termination', ref: 'Ind AS 116.46(a) / derecognition' },
  IMPAIRMENT: { label: 'Impairment of the ROU asset', ref: 'Ind AS 116.33; Ind AS 36' },
  RESTORATION_REVISION: { label: 'Change in restoration estimate', ref: 'Appendix A to Ind AS 16 / Ind AS 37' },
  ROU_DERECOGNITION: { label: 'Partial derecognition of ROU (finance sublease)', ref: 'Ind AS 116.B58, 67' },
};
export const MOD_NATURES = [
  { v: 'SEPARATE_LEASE', l: 'Additional right of use at a commensurate stand-alone price — separate lease', ref: '44' },
  { v: 'TERM_EXTENSION', l: 'Extension of the lease term', ref: '45(c), 46(b)' },
  { v: 'SCOPE_INCREASE', l: 'Increase in scope not at stand-alone price', ref: '45(c), 46(b)' },
  { v: 'CONSIDERATION_CHANGE', l: 'Change in consideration only', ref: '45(c), 46(b)' },
  { v: 'SCOPE_DECREASE', l: 'Decrease in scope (e.g. area surrendered)', ref: '46(a)' },
  { v: 'TERM_REDUCTION', l: 'Reduction of the lease term', ref: '46(a)' },
];
export const REASSESS_KINDS = [
  { v: 'LEASE_TERM', l: 'Change in lease term (option exercised / reasonable-certainty changed)', ref: '40(a), 20–21', rate: 'revised' },
  { v: 'PURCHASE_OPTION', l: 'Change in assessment of a purchase option', ref: '40(b)', rate: 'revised' },
  { v: 'RVG', l: 'Change in amounts expected under a residual value guarantee', ref: '42(a)', rate: 'unchanged' },
  { v: 'INDEX_RATE', l: 'Change in future payments from an index or rate (e.g. CPI reset)', ref: '42(b)', rate: 'unchanged' },
  { v: 'FLOATING_RATE', l: 'Change in floating interest rates', ref: '43', rate: 'revised' },
];
export const LESSOR_EVENT_TYPES = {
  MODIFICATION: { label: 'Lease modification (lessor)', ref: 'Ind AS 116.79–80, 87' },
  TERMINATION: { label: 'Early termination', ref: 'Ind AS 116 / Ind AS 109.3.2.3' },
  UGR_REVISION: { label: 'Reduction of unguaranteed residual value', ref: 'Ind AS 116.77' },
  ECL: { label: 'Expected credit loss allowance', ref: 'Ind AS 109.5.5.15(b)' },
};
export const LESSOR_MOD_NATURES = [
  { v: 'OPERATING_MODIFICATION', l: 'Operating lease — the modified lease is a new lease from the effective date', ref: '87', for: 'OPERATING' },
  { v: 'SEPARATE_LEASE', l: 'Adds the right to use additional assets at a stand-alone price — separate lease', ref: '79', for: 'ANY' },
  { v: 'FINANCE_REMEASURE', l: 'Finance lease — remains a finance lease: remeasure the net investment (Ind AS 109)', ref: '80(b)', for: 'FINANCE' },
  { v: 'FINANCE_TO_OPERATING', l: 'Finance lease — would have been an operating lease: new operating lease', ref: '80(a)', for: 'FINANCE' },
];
const PAY_MODES = [
  { v: 'KEEP', l: 'Keep the remaining scheduled payments (incl. option-period lines) within the new term' },
  { v: 'GENERATE', l: 'Generate revised payments from new terms' },
  { v: 'SCALE', l: 'Scale remaining payments by the scope decrease' },
  { v: 'MANUAL', l: 'Enter the revised payment lines' },
];

export const DecisionTable = {
  props: { kind: String },
  template: `
  <table class="t compact" v-if="kind==='REASSESSMENT'"><thead><tr><th>Trigger</th><th>Discount rate</th><th>Ref</th></tr></thead><tbody>
    <tr><td>Change in lease term — significant event within lessee's control or option exercised</td><td>Revised</td><td>40(a), 20–21</td></tr>
    <tr><td>Change in assessment of a purchase option</td><td>Revised</td><td>40(b)</td></tr>
    <tr><td>Change in amounts expected under a residual value guarantee</td><td>Unchanged</td><td>42(a)</td></tr>
    <tr><td>Change in payments from an index or rate (when cash flows change)</td><td>Unchanged</td><td>42(b)</td></tr>
    <tr><td>Change in floating interest rates</td><td>Revised (reflecting the rate change)</td><td>43</td></tr>
    <tr><td colspan="3" class="small text-2">Remeasurement adjusts the ROU asset; any reduction below zero goes to profit or loss (39).</td></tr></tbody></table>
  <table class="t compact" v-else><thead><tr><th>Modification</th><th>Accounting</th><th>Ref</th></tr></thead><tbody>
    <tr><td>Adds right to use one or more underlying assets, price commensurate with stand-alone price</td><td>Separate lease — original lease unchanged</td><td>44</td></tr>
    <tr><td>Extension of term / increase in scope (not a separate lease) / change in consideration</td><td>Remeasure liability at revised rate; corresponding ROU adjustment</td><td>45(c), 46(b)</td></tr>
    <tr><td>Decrease in scope or term</td><td>Reduce ROU proportionately; gain/loss in P&amp;L; remeasure remaining liability at revised rate</td><td>46(a)</td></tr>
    <tr><td colspan="3" class="small text-2">Effective date = date both parties agree to the modification. Rent concessions are not assumed to qualify for any expedient.</td></tr></tbody></table>`,
};

export const EventForm = {
  components: { ...common, PaymentTermsForm, DecisionTable },
  props: { lease: Object, kind: String, leases: Array },
  emits: ['saved', 'cancel'],
  setup(props, { emit }) {
    const leaseId = ref(props.lease?.id || '');
    const full = ref(props.lease || null);
    const f = ref({
      event_type: props.kind || 'MODIFICATION', subtype: props.kind === 'REASSESSMENT' ? 'LEASE_TERM' : 'TERM_EXTENSION',
      effective_date: today(), description: '',
      d: { revised_rate_pct: '', new_term_end: '', scope_decrease_fraction: '', additional_rou: false, commensurate_standalone_price: false,
        payments_mode: 'KEEP', new_payments: [], new_useful_life_end: '', purchase_option_rc: null, apply_after_payments: false,
        penalty: '', impairment_amount: '', recoverable_amount: '', cgu: '', rationale: '', new_estimated_cost: '', new_discount_rate_pct: '',
        new_settlement_date: '', fraction: '', new_unguaranteed_residual: '', asset_value_returned: '', loss_allowance: '' },
    });
    const lessorMode = computed(() => full.value?.role === 'LESSOR' && full.value?.lease_type !== 'SUBLEASE');
    const curClass = computed(() => full.value?.classification || 'OPERATING');
    const natures = computed(() => LESSOR_MOD_NATURES.filter(n => n.for === 'ANY' || n.for === curClass.value));
    const types = computed(() => lessorMode.value ? LESSOR_EVENT_TYPES : EVENT_TYPES);
    function lessorDefaults() {
      if (!lessorMode.value) return;
      if (!LESSOR_EVENT_TYPES[f.value.event_type]) f.value.event_type = 'MODIFICATION';
      if (f.value.event_type === 'MODIFICATION' && !natures.value.find(n => n.v === f.value.subtype)) {
        f.value.subtype = curClass.value === 'FINANCE' ? 'FINANCE_REMEASURE' : 'OPERATING_MODIFICATION';
        f.value.d.payments_mode = 'GENERATE';
      }
    }
    watch(lessorMode, lessorDefaults, { immediate: true });
    const terms = ref(defaultTerms(props.lease));
    if (terms.value) terms.value.start_date = f.value.effective_date;   // revised terms run from the effective date
    const preview = ref(null);
    const busy = ref(false);
    const file = ref(null);
    async function loadLease(id) {
      if (!id) { full.value = null; return; }
      try { full.value = await get('/api/leases/' + id); terms.value = { ...defaultTerms(full.value), start_date: f.value.effective_date }; } catch (e) { showError(e); }
    }
    watch(leaseId, (id) => { preview.value = null; if (!props.lease) loadLease(id); });
    watch(() => f.value.effective_date, (v) => { if (terms.value) terms.value.start_date = v; });
    watch(() => [f.value.event_type, f.value.subtype], () => {
      preview.value = null;
      if (lessorMode.value) { lessorDefaults(); return; }
      const t = f.value.event_type, s = f.value.subtype;
      if (t === 'MODIFICATION') {
        f.value.d.additional_rou = s === 'SEPARATE_LEASE' || s === 'SCOPE_INCREASE';
        f.value.d.commensurate_standalone_price = s === 'SEPARATE_LEASE';
        f.value.d.payments_mode = s === 'SCOPE_DECREASE' ? 'SCALE' : ['CONSIDERATION_CHANGE', 'SCOPE_INCREASE'].includes(s) ? 'GENERATE' : 'KEEP';
      }
      if (t === 'REASSESSMENT') f.value.d.payments_mode = ['INDEX_RATE', 'RVG', 'FLOATING_RATE'].includes(s) ? 'GENERATE' : 'KEEP';
      if (t === 'MODIFICATION' && !MOD_NATURES.find(x => x.v === s)) f.value.subtype = 'TERM_EXTENSION';
      if (t === 'REASSESSMENT' && !REASSESS_KINDS.find(x => x.v === s)) f.value.subtype = 'LEASE_TERM';
    });
    const needsRate = computed(() => {
      if (lessorMode.value) return false;
      const t = f.value.event_type, s = f.value.subtype;
      if (t === 'MODIFICATION') return s !== 'SEPARATE_LEASE';
      if (t === 'REASSESSMENT') return ['LEASE_TERM', 'PURCHASE_OPTION', 'FLOATING_RATE'].includes(s);
      return false;
    });
    const showPayments = computed(() => ['MODIFICATION', 'REASSESSMENT'].includes(f.value.event_type) && f.value.subtype !== 'SEPARATE_LEASE');
    function payload() {
      const t = f.value.event_type, d = f.value.d;
      const det = {};
      const put = (k) => { if (d[k] !== '' && d[k] !== null && d[k] !== undefined) det[k] = d[k]; };
      if (lessorMode.value) {
        if (t === 'MODIFICATION') {
          put('new_term_end');
          if (f.value.subtype === 'FINANCE_REMEASURE') put('new_unguaranteed_residual');
          if (f.value.subtype !== 'SEPARATE_LEASE') {
            det.payments_mode = d.payments_mode;
            if (d.payments_mode === 'GENERATE') det.new_payment_terms = clone(terms.value);
            if (d.payments_mode === 'MANUAL') det.new_payments = d.new_payments.filter(x => x.date);
          }
        }
        if (t === 'TERMINATION') { put('penalty'); put('asset_value_returned'); }
        if (t === 'UGR_REVISION') put('new_unguaranteed_residual');
        if (t === 'ECL') put('loss_allowance');
        return { event_type: t, subtype: t === 'MODIFICATION' ? f.value.subtype : null, effective_date: f.value.effective_date,
          description: f.value.description, details: det };
      }
      if (t === 'MODIFICATION' || t === 'REASSESSMENT') {
        ['revised_rate_pct', 'new_term_end', 'new_useful_life_end'].forEach(put);
        if (t === 'MODIFICATION') { put('scope_decrease_fraction'); det.additional_rou = !!d.additional_rou; det.commensurate_standalone_price = !!d.commensurate_standalone_price; }
        if (t === 'REASSESSMENT' && f.value.subtype === 'PURCHASE_OPTION') det.purchase_option_rc = d.purchase_option_rc;
        if (f.value.subtype !== 'SEPARATE_LEASE') {
          det.payments_mode = d.payments_mode;
          if (d.payments_mode === 'GENERATE') det.new_payment_terms = clone(terms.value);
          if (d.payments_mode === 'MANUAL') det.new_payments = d.new_payments.filter(x => x.date);
        }
      }
      if (t === 'TERMINATION') put('penalty');
      if (t === 'IMPAIRMENT') ['impairment_amount', 'recoverable_amount', 'cgu', 'rationale'].forEach(put);
      if (t === 'RESTORATION_REVISION') ['new_estimated_cost', 'new_discount_rate_pct', 'new_settlement_date'].forEach(put);
      if (t === 'ROU_DERECOGNITION') put('fraction');
      if (d.apply_after_payments) det.apply_after_payments = true;
      return { event_type: t, subtype: ['MODIFICATION', 'REASSESSMENT'].includes(t) ? f.value.subtype : null, effective_date: f.value.effective_date,
        description: f.value.description, details: det };
    }
    function check() {
      if (!leaseId.value) return 'Select the lease.';
      if (!f.value.effective_date) return 'Effective date is required.';
      if (!f.value.description.trim()) return 'Describe the event (e.g. addendum reference and what changed).';
      if (needsRate.value && !f.value.d.revised_rate_pct) return 'A revised discount rate at the effective date is required (Ind AS 116.' + (f.value.event_type === 'MODIFICATION' ? '45(c)' : '40–41 / 43') + ').';
      if (f.value.event_type === 'IMPAIRMENT' && !f.value.d.impairment_amount && !f.value.d.recoverable_amount) return 'Enter the impairment loss or the recoverable amount (Ind AS 36).';
      if (f.value.event_type === 'ROU_DERECOGNITION' && !f.value.d.fraction) return 'Enter the fraction of the ROU asset derecognised.';
      if (lessorMode.value && f.value.event_type === 'ECL' && f.value.d.loss_allowance === '') return 'Enter the loss allowance at the effective date (Ind AS 109).';
      if (lessorMode.value && f.value.event_type === 'UGR_REVISION' && f.value.d.new_unguaranteed_residual === '') return 'Enter the revised unguaranteed residual value.';
      return null;
    }
    async function doPreview() {
      const err = check();
      if (err) { toast(err, 'bad'); return; }
      busy.value = true;
      try { preview.value = await post('/api/leases/' + leaseId.value + '/events/preview', payload()); }
      catch (e) { preview.value = null; showError(e); } finally { busy.value = false; }
    }
    async function save() {
      const err = check();
      if (err) { toast(err, 'bad'); return; }
      busy.value = true;
      try {
        const p = payload();
        if (file.value) {
          const fd = new FormData();
          fd.append('file', file.value);
          fd.append('doc_type', 'Addendum / event evidence');
          const d = await upload('/api/leases/' + leaseId.value + '/documents', fd);
          p.document_id = d.id;
        }
        const r = await post('/api/leases/' + leaseId.value + '/events', p);
        toast('Event recorded and the lease recalculated — submit it for review and approval.', 'ok', 6000);
        emit('saved', { lease_id: Number(leaseId.value), ...r });
      } catch (e) { showError(e); } finally { busy.value = false; }
    }
    function addLine() { f.value.d.new_payments.push({ date: '', lease_amount: '', non_lease_amount: '0', category: 'FIXED', description: 'Revised rent' }); }
    const currentTermEnd = computed(() => full.value?.term_end);
    return { leaseId, full, f, terms, preview, busy, file, needsRate, showPayments, doPreview, save, addLine, currentTermEnd,
      EVENT_TYPES, MOD_NATURES, REASSESS_KINDS, PAY_MODES, CATEGORIES, money, date, num, titleCase, emit,
      lessorMode, curClass, natures, types, LESSOR_EVENT_TYPES };
  },
  template: `
  <div class="col" style="gap:14px">
    <div class="form-grid">
      <label class="field span-2" v-if="!lease"><span class="req">Lease</span><select v-model="leaseId"><option value="">Select…</option>
        <option v-for="l in leases" :key="l.id" :value="l.id">{{ l.lease_code }} — {{ l.description }} ({{ l.status }})</option></select></label>
      <label class="field"><span class="req">Event</span><select v-model="f.event_type"><option v-for="(t, k) in types" :key="k" :value="k">{{ t.label }}</option></select></label>
      <label class="field"><span class="req">Effective date</span><input type="date" v-model="f.effective_date"><span class="hint">Modification: date both parties agree</span></label>
      <label class="field span-2" v-if="f.event_type==='MODIFICATION' && lessorMode">Nature of modification ({{ curClass === 'FINANCE' ? 'finance lease' : 'operating lease' }})<select v-model="f.subtype"><option v-for="m in natures" :key="m.v" :value="m.v">{{ m.l }} (para {{ m.ref }})</option></select></label>
      <label class="field span-2" v-else-if="f.event_type==='MODIFICATION'">Nature of modification<select v-model="f.subtype"><option v-for="m in MOD_NATURES" :key="m.v" :value="m.v">{{ m.l }} ({{ m.ref }})</option></select></label>
      <label class="field span-2" v-if="f.event_type==='REASSESSMENT'">Trigger<select v-model="f.subtype"><option v-for="m in REASSESS_KINDS" :key="m.v" :value="m.v">{{ m.l }} ({{ m.ref }} — {{ m.rate }} rate)</option></select></label>
      <label class="field span-all"><span class="req">Description / evidence reference</span><input v-model="f.description" placeholder="e.g. Addendum No. 2 dated 15-Mar-2026: area reduced from 12,000 to 9,000 sq ft; rent revised"></label>
    </div>
    <div v-if="full && lessorMode" class="small text-2">Lessor lease · {{ curClass === 'FINANCE' ? 'finance lease' : 'operating lease' }} · lease term ends {{ date(currentTermEnd) }} · status {{ full.status }}</div>
    <div v-else-if="full" class="small text-2">Current lease term ends {{ date(currentTermEnd) }} · current rate {{ num(full.discount_rate_pct, 2) }}% · status {{ full.status }}</div>

    <template v-if="lessorMode">
      <template v-if="f.event_type==='MODIFICATION' && f.subtype!=='SEPARATE_LEASE'">
        <div class="form-grid">
          <label class="field">New lease term end<input type="date" v-model="f.d.new_term_end"><span class="hint">Blank = unchanged</span></label>
          <label class="field" v-if="f.subtype==='FINANCE_REMEASURE'">Revised unguaranteed residual value<input class="num" v-model="f.d.new_unguaranteed_residual"><span class="hint">Blank = unchanged</span></label>
          <div class="field span-2"><span>Measurement</span><div class="small text-2" style="padding-top:6px">{{ f.subtype==='FINANCE_REMEASURE' ? 'Net investment recalculated at the original rate implicit in the lease; difference in profit or loss (Ind AS 109.5.4.3).' : f.subtype==='FINANCE_TO_OPERATING' ? 'Underlying asset recognised at the net investment; straight-line income on the new terms (para 80(a)).' : 'Accrued / deferred lease income is carried into the modified lease and recognised with the remaining payments on a straight-line basis (para 87).' }}</div></div>
        </div>
        <label class="field">Revised payments<select v-model="f.d.payments_mode"><option v-for="m in PAY_MODES.filter(x => x.v !== 'SCALE')" :key="m.v" :value="m.v">{{ m.l }}</option></select></label>
        <div v-if="f.d.payments_mode==='GENERATE'" class="card"><div class="card-head"><h3>Revised payment terms (from the effective date)</h3></div>
          <div class="card-body"><PaymentTermsForm v-model="terms" editable compact/></div></div>
        <div v-if="f.d.payments_mode==='MANUAL'" class="card"><div class="card-head"><h3>Revised payment lines</h3><div class="spacer"></div><button class="btn sm" @click="addLine"><AppIcon name="plus" :size="13"/> Line</button></div>
          <table class="t compact"><thead><tr><th>Date</th><th class="num">Lease amount</th><th class="num">Non-lease</th><th>Category</th><th>Description</th><th></th></tr></thead>
            <tbody><tr v-if="!f.d.new_payments.length"><td colspan="6" class="empty">Add the remaining payments after the effective date.</td></tr>
              <tr v-for="(p, i) in f.d.new_payments" :key="i"><td><input type="date" v-model="p.date"></td><td><input class="num" v-model="p.lease_amount"></td><td><input class="num" v-model="p.non_lease_amount"></td>
                <td><select v-model="p.category"><option v-for="c in CATEGORIES" :key="c.v" :value="c.v">{{ c.l }}</option></select></td><td><input v-model="p.description"></td>
                <td><button class="btn sm icon ghost" @click="f.d.new_payments.splice(i,1)"><AppIcon name="trash-2" :size="13"/></button></td></tr></tbody></table></div>
      </template>
      <div v-if="f.event_type==='MODIFICATION' && f.subtype==='SEPARATE_LEASE'" class="alert info"><AppIcon name="info"/><div>A separate lease leaves this lease unchanged (para 79). After recording, create a new lessor lease for the additional asset from its own commencement date.</div></div>
      <div class="form-grid" v-if="f.event_type==='TERMINATION'">
        <label class="field">Termination payment receivable from the lessee<input class="num" v-model="f.d.penalty"></label>
        <label class="field" v-if="curClass==='FINANCE'">Value at which the returned asset is recognised<input class="num" v-model="f.d.asset_value_returned"><span class="hint">Blank = net investment less payment (no gain or loss)</span></label>
        <div class="small text-2 span-2" style="align-self:end">{{ curClass==='FINANCE' ? 'The net investment is derecognised; the returned asset and any termination payment are recognised; the difference goes to profit or loss.' : 'Accrued / deferred lease income and unamortised initial direct costs are released to profit or loss; any deposit is refunded at the termination date.' }}</div>
        <div class="alert info span-all" style="margin:0"><AppIcon name="info"/><div>Use early termination only where the lease ends on the date the termination is agreed. If the parties agree now to end the lease on a later date, record a <b>lease modification</b> that shortens the lease term instead (paras 79–80 / 87), so the termination payment and the straight-line balance are spread to the exit date.</div></div>
      </div>
      <div class="form-grid" v-if="f.event_type==='UGR_REVISION'">
        <label class="field"><span class="req">Revised unguaranteed residual value</span><input class="num" v-model="f.d.new_unguaranteed_residual"><span class="hint">Only a reduction is recognised (para 77)</span></label>
      </div>
      <div class="form-grid" v-if="f.event_type==='ECL'">
        <label class="field"><span class="req">Loss allowance at the effective date</span><input class="num" v-model="f.d.loss_allowance"><span class="hint">Cumulative allowance — the movement is charged / released</span></label>
        <div class="small text-2 span-2" style="align-self:end">Lifetime expected credit losses on lease receivables (simplified approach permitted, Ind AS 109.5.5.15(b)). Document the provision matrix / assessment.</div>
      </div>
    </template>

    <template v-if="!lessorMode && ['MODIFICATION','REASSESSMENT'].includes(f.event_type) && f.subtype!=='SEPARATE_LEASE'">
      <div class="form-grid">
        <label class="field" v-if="needsRate"><span class="req">Revised discount rate % (at effective date)</span><input class="num" v-model="f.d.revised_rate_pct"></label>
        <div class="field" v-else><span>Discount rate</span><div class="small text-2" style="padding-top:6px">Unchanged discount rate (para 42)</div></div>
        <label class="field">New lease term end<input type="date" v-model="f.d.new_term_end"><span class="hint">Blank = unchanged</span></label>
        <label class="field" v-if="f.event_type==='MODIFICATION' && f.subtype==='SCOPE_DECREASE'"><span class="req">Fraction of scope surrendered (0–1)</span><input class="num" v-model="f.d.scope_decrease_fraction" placeholder="e.g. 0.25"></label>
        <div class="field span-2" v-if="f.event_type==='REASSESSMENT' && f.subtype==='PURCHASE_OPTION'"><span>Purchase option now reasonably certain?</span><TriState v-model="f.d.purchase_option_rc"/></div>
        <label class="field">Revised useful-life end<input type="date" v-model="f.d.new_useful_life_end"><span class="hint">If depreciation period changes</span></label>
      </div>
      <div>
        <label class="field">Revised payments<select v-model="f.d.payments_mode"><option v-for="m in PAY_MODES" :key="m.v" :value="m.v">{{ m.l }}</option></select></label>
      </div>
      <div v-if="f.d.payments_mode==='GENERATE'" class="card"><div class="card-head"><h3>Revised payment terms (from the effective date)</h3></div>
        <div class="card-body"><PaymentTermsForm v-model="terms" editable compact/></div></div>
      <div v-if="f.d.payments_mode==='MANUAL'" class="card"><div class="card-head"><h3>Revised payment lines</h3><div class="spacer"></div><button class="btn sm" @click="addLine"><AppIcon name="plus" :size="13"/> Line</button></div>
        <table class="t compact"><thead><tr><th>Date</th><th class="num">Lease amount</th><th class="num">Non-lease</th><th>Category</th><th>Description</th><th></th></tr></thead>
          <tbody><tr v-if="!f.d.new_payments.length"><td colspan="6" class="empty">Add the remaining payments after the effective date.</td></tr>
            <tr v-for="(p, i) in f.d.new_payments" :key="i"><td><input type="date" v-model="p.date"></td><td><input class="num" v-model="p.lease_amount"></td><td><input class="num" v-model="p.non_lease_amount"></td>
              <td><select v-model="p.category"><option v-for="c in CATEGORIES" :key="c.v" :value="c.v">{{ c.l }}</option></select></td><td><input v-model="p.description"></td>
              <td><button class="btn sm icon ghost" @click="f.d.new_payments.splice(i,1)"><AppIcon name="trash-2" :size="13"/></button></td></tr></tbody></table></div>
    </template>
    <div v-if="!lessorMode && f.event_type==='MODIFICATION' && f.subtype==='SEPARATE_LEASE'" class="alert info"><AppIcon name="info"/><div>A separate lease leaves the original lease unchanged (para 44). After recording, create a new lease for the additional asset from its own commencement date.</div></div>

    <div class="form-grid" v-if="!lessorMode && f.event_type==='TERMINATION'">
      <label class="field">Termination penalty payable<input class="num" v-model="f.d.penalty"></label>
      <div class="small text-2 span-2" style="align-self:end">Liability and ROU asset are derecognised at the effective date; the difference (after the penalty) goes to profit or loss.</div>
    </div>
    <div class="form-grid" v-if="f.event_type==='IMPAIRMENT'">
      <label class="field">Impairment loss (or reversal as negative)<input class="num" v-model="f.d.impairment_amount"></label>
      <label class="field">— or — recoverable amount of the ROU asset<input class="num" v-model="f.d.recoverable_amount"></label>
      <label class="field">Cash-generating unit<input v-model="f.d.cgu"></label>
      <label class="field span-all">Basis (Ind AS 36 — value in use / FVLCD)<textarea v-model="f.d.rationale"></textarea></label>
    </div>
    <div class="form-grid" v-if="f.event_type==='RESTORATION_REVISION'">
      <label class="field">Revised estimated cost<input class="num" v-model="f.d.new_estimated_cost"></label>
      <label class="field">Revised discount rate %<input class="num" v-model="f.d.new_discount_rate_pct"></label>
      <label class="field">Revised settlement date<input type="date" v-model="f.d.new_settlement_date"></label>
    </div>
    <div class="form-grid" v-if="f.event_type==='ROU_DERECOGNITION'">
      <label class="field"><span class="req">Fraction of ROU derecognised (0–1)</span><input class="num" v-model="f.d.fraction"></label>
    </div>
    <div class="row wrap">
      <label class="check"><input type="checkbox" v-model="f.d.apply_after_payments"> Apply after payments due on the effective date</label>
      <div class="spacer"></div>
      <label class="small text-2 row">Evidence (addendum, notice): <input type="file" @change="file = $event.target.files[0]" style="width:auto;min-height:0;border:0;padding:0"></label>
    </div>

    <div v-if="preview" class="card">
      <div class="card-head"><h3>Impact preview</h3><span class="sub">Not saved — pre vs post, computed by the engine</span></div>
      <div class="card-body">
        <div v-if="preview.event && preview.lessor" class="grid c4 mb">
          <div class="tile"><div class="label">{{ preview.event.balance_label || 'Balance' }}</div><div class="value" style="font-size:17px">{{ money(preview.event.balance_before) }} → {{ money(preview.event.balance_after) }}</div></div>
          <div class="tile"><div class="label">Gain / (loss) in P&amp;L</div><div class="value" style="font-size:17px" :class="Number(preview.event.gain_loss) < 0 ? 'neg' : ''">{{ money(preview.event.gain_loss) }}</div></div>
          <div class="tile"><div class="label">Classification</div><div class="value" style="font-size:15px">{{ preview.event.classification_before }} → {{ preview.event.classification_after }}</div></div>
          <div class="tile"><div class="label">Reference</div><div class="value" style="font-size:13px">{{ preview.event.reference }}</div></div>
        </div>
        <div v-else-if="preview.event" class="grid c4 mb">
          <div class="tile"><div class="label">Lease liability</div><div class="value" style="font-size:17px">{{ money(preview.event.liability_before) }} → {{ money(preview.event.liability_after) }}</div></div>
          <div class="tile"><div class="label">ROU asset</div><div class="value" style="font-size:17px">{{ money(preview.event.rou_before) }} → {{ money(preview.event.rou_after) }}</div></div>
          <div class="tile"><div class="label">Gain / (loss) in P&amp;L</div><div class="value" style="font-size:17px" :class="Number(preview.event.gain_loss) < 0 ? 'neg' : ''">{{ money(preview.event.gain_loss) }}</div></div>
          <div class="tile"><div class="label">Rate · term end</div><div class="value" style="font-size:15px">{{ num(preview.event.rate_before_pct, 2) }}% → {{ num(preview.event.rate_after_pct, 2) }}%</div><div class="foot">{{ date(preview.event.term_end_before) }} → {{ date(preview.event.term_end_after) }}</div></div>
        </div>
        <table class="t compact" v-if="preview.event"><thead><tr><th>Step</th><th class="num">Amount</th><th>Explanation</th></tr></thead>
          <tbody><tr v-for="(s, i) in preview.event.steps" :key="i"><td>{{ s[0] }}</td><td class="num">{{ money(s[1]) }}</td><td class="small text-2 wrap">{{ s[2] }}</td></tr></tbody></table>
        <FlagList v-if="preview.event" :flags="preview.event.flags" class="mt"/>
        <IssueList :issues="preview.issues"/>
        <h4 class="mt">Journal entries at the effective date</h4>
        <table class="t compact mt" v-for="(p, i) in preview.postings" :key="i"><thead><tr><th colspan="3">{{ date(p.date) }} — {{ p.narration }}</th></tr></thead>
          <tbody><tr v-for="(l, j) in p.lines" :key="j"><td>{{ titleCase(l.role) }}</td><td class="num">{{ Number(l.debit) ? money(l.debit) : '' }}</td><td class="num">{{ Number(l.credit) ? money(l.credit) : '' }}</td></tr></tbody></table>
      </div>
    </div>
    <div class="row" style="justify-content:flex-end">
      <button class="btn" @click="emit('cancel')">Cancel</button>
      <button class="btn" :disabled="busy || !leaseId" @click="doPreview"><AppIcon name="eye" :size="14"/> Preview impact</button>
      <button class="btn primary" :disabled="busy || !leaseId" @click="save"><AppIcon name="save" :size="14"/> Record event</button>
    </div>
  </div>`,
};

export const EventsPage = {
  components: { ...common, EventForm, DecisionTable },
  props: { route: Object, kind: String },
  setup(props) {
    const rows = ref([]);
    const loading = ref(false);
    const showNew = ref(false);
    const leases = ref([]);
    const types = computed(() => props.kind === 'REASSESSMENT' ? 'REASSESSMENT' : 'MODIFICATION,TERMINATION');
    async function load() {
      loading.value = true;
      try {
        const qs = new URLSearchParams({ event_type: types.value });
        if (store.entityId) qs.set('entity_id', store.entityId);
        rows.value = await get('/api/events?' + qs.toString());
      } catch (e) { showError(e); } finally { loading.value = false; }
    }
    async function openNew() {
      try { leases.value = (await get('/api/leases?page_size=5000')).rows.filter(l => ['Approved', 'Posted', 'Modified'].includes(l.status)
        && ((l.role === 'LESSEE' && ['STANDARD', 'SALE_LEASEBACK'].includes(l.lease_type)) || (l.role === 'LESSOR' && l.lease_type !== 'SUBLEASE' && props.kind !== 'REASSESSMENT'))); }
      catch (e) { showError(e); }
      showNew.value = true;
    }
    function saved(r) { showNew.value = false; location.hash = '#/leases/' + r.lease_id + '?tab=events'; }
    function open(r) { location.hash = '#/leases/' + r.lease_id + '?tab=events'; }
    onMounted(load);
    watch(() => store.entityId, load);
    const columns = [
      { key: 'lease_code', label: 'Lease' }, { key: 'lease_description', label: 'Lease description', wrap: true },
      { key: 'event_type', label: 'Event', format: (v, r) => r && r.role === 'LESSOR' ? ((LESSOR_EVENT_TYPES[v] || {}).label || v) : ((EVENT_TYPES[v] || {}).label || v) },
      { key: 'role', label: 'Role', format: (v) => v === 'LESSOR' ? 'Lessor' : 'Lessee' },
      { key: 'subtype', label: 'Nature', format: (v) => ((MOD_NATURES.concat(REASSESS_KINDS, LESSOR_MOD_NATURES)).find(x => x.v === v) || {}).l || titleCase(v || '') || '—', wrap: true },
      { key: 'effective_date', label: 'Effective', type: 'date' }, { key: 'description', label: 'Description', wrap: true },
      { key: 'status', label: 'Status' },
      { key: 'liability_before', label: 'Liability before', type: 'money' }, { key: 'liability_after', label: 'Liability after', type: 'money' },
      { key: 'rou_before', label: 'ROU before', type: 'money', hidden: true }, { key: 'rou_after', label: 'ROU after', type: 'money', hidden: true },
      { key: 'balance_before', label: 'Lessor balance before', type: 'money', hidden: true }, { key: 'balance_after', label: 'Lessor balance after', type: 'money', hidden: true },
      { key: 'gain_loss', label: 'Gain / (loss)', type: 'money' },
    ];
    const title = computed(() => props.kind === 'REASSESSMENT' ? 'Reassessments' : 'Modifications and terminations');
    return { store, rows, loading, columns, showNew, openNew, saved, open, leases, title, load };
  },
  template: `
  <div>
    <div class="page-head">
      <div class="grow"><h1>{{ title }}</h1><div class="sub" v-if="kind==='REASSESSMENT'">Changes in lease term, purchase-option assessment, residual value guarantees, index/rate-linked payments and floating rates — distinct from modifications.</div>
        <div class="sub" v-else>Changes in scope or consideration not part of the original terms (Ind AS 116 App. A) and early terminations. Pre- and post-event schedules are preserved.</div></div>
      <button class="btn primary" v-if="store.can('event.write')" @click="openNew"><AppIcon name="plus" :size="14"/> Record {{ kind==='REASSESSMENT' ? 'reassessment' : 'modification' }}</button>
    </div>
    <div class="grid side">
      <div class="card">
        <DataTable :id="'events-' + kind" :columns="columns" :rows="rows" :loading="loading" clickable @row-click="open" empty-text="No events recorded yet.">
          <template #cell-lease_code="{ row }"><b>{{ row.lease_code }}</b></template>
          <template #cell-status="{ row }"><StatusBadge :status="row.status"/></template>
        </DataTable>
      </div>
      <div class="card"><div class="card-head"><h3>Decision guide</h3></div><div class="card-body flush"><DecisionTable :kind="kind"/></div></div>
    </div>
    <Modal v-if="showNew" :title="kind==='REASSESSMENT' ? 'Record a reassessment' : 'Record a modification'" wide @close="showNew=false">
      <EventForm :kind="kind" :leases="leases" @saved="saved" @cancel="showNew=false"/>
    </Modal>
  </div>`,
};
