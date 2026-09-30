// Lease input forms used on the lease detail page and the manual wizard.
// Every judgment is explicit (Yes / No / Not assessed) and every override needs a reason.
import { store, get, post, put, patch, toast, showError, confirmDialog } from '../store.js';
import { common } from '../components.js';
import { money, date, num, clone, addMonths, addDays } from '../util.js';

const { ref, computed, watch, onMounted } = Vue;

export const CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD', 'JPY', 'CHF', 'AUD', 'CAD', 'HKD', 'SAR'];
export const FREQUENCIES = [{ v: 1, l: 'Monthly' }, { v: 3, l: 'Quarterly' }, { v: 6, l: 'Half-yearly' }, { v: 12, l: 'Annual' }];
export const CATEGORIES = [
  { v: 'FIXED', l: 'Fixed', ref: '27(a)' }, { v: 'IN_SUBSTANCE_FIXED', l: 'In-substance fixed', ref: '27(a), B42' },
  { v: 'INDEX_LINKED', l: 'Index-linked (CPI)', ref: '27(b), 28' }, { v: 'RATE_LINKED', l: 'Rate-linked', ref: '27(b), 28' },
  { v: 'VARIABLE', l: 'Variable — sales / usage (excluded)', ref: '38(b)' }, { v: 'RVG', l: 'Residual value guarantee', ref: '27(c)' },
  { v: 'PURCHASE_OPTION', l: 'Purchase option price', ref: '27(d)' }, { v: 'TERMINATION_PENALTY', l: 'Termination penalty', ref: '27(e)' },
  { v: 'INCENTIVE', l: 'Lease incentive receivable', ref: '27(a)' }, { v: 'NON_LEASE', l: 'Non-lease only (CAM / services)', ref: '12–16' },
];
export const catLabel = (v) => (CATEGORIES.find(c => c.v === v) || {}).l || v;

function norm(v) { return v === null || v === undefined ? '' : String(v); }

// --------------------------------------------------------------------------- contract / master data
const CONTRACT_KEYS = ['description', 'entity_id', 'asset_class_id', 'counterparty_id', 'asset_description', 'location', 'business_unit',
  'cost_centre', 'department', 'project', 'contract_number', 'contract_date', 'commencement_date', 'availability_date', 'contract_end',
  'enforceable_end', 'enforceable_rationale', 'currency', 'useful_life_end', 'ownership_transfers', 'non_lease_expedient', 'role',
  'lease_type', 'head_lease_id', 'notes'];

export const ContractForm = {
  components: common,
  props: { lease: Object, editable: Boolean },
  emits: ['saved'],
  setup(props, { emit }) {
    const pick = (l) => Object.fromEntries(CONTRACT_KEYS.map(k => [k, l[k] ?? (k === 'non_lease_expedient' || k === 'head_lease_id' ? null : '')]));
    const form = ref(pick(props.lease));
    watch(() => props.lease, (l) => { form.value = pick(l); });
    const master = ref({ counterparties: [] });
    const leases = ref([]);
    const busy = ref(false);
    onMounted(async () => {
      try { master.value = await get('/api/master'); } catch (e) { /* ignore */ }
      try { leases.value = (await get('/api/leases?page_size=5000')).rows.filter(r => r.id !== props.lease.id && r.role === 'LESSEE'); } catch (e) { /* ignore */ }
    });
    const dirty = computed(() => CONTRACT_KEYS.filter(k => norm(form.value[k]) !== norm(props.lease[k])));
    async function save() {
      const payload = {};
      dirty.value.forEach(k => { payload[k] = form.value[k] === '' ? null : form.value[k]; });
      busy.value = true;
      try { await patch('/api/leases/' + props.lease.id, payload); toast('Contract details saved', 'ok'); emit('saved'); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    watch(() => form.value.role, (r) => {
      if (r === 'LESSOR' && ['SHORT_TERM', 'LOW_VALUE', 'SALE_LEASEBACK'].includes(form.value.lease_type)) form.value.lease_type = 'STANDARD';
    });
    const isLessor = computed(() => form.value.role === 'LESSOR');
    async function addCounterparty() {
      const name = await confirmDialog('New counterparty', isLessor.value ? 'Legal name of the lessee (tenant / licensee).' : 'Legal name of the lessor.', { input: 'Name', ok: 'Add' });
      if (!name) return;
      try {
        const r = await post('/api/master/counterparties', { name });
        master.value = await get('/api/master');
        form.value.counterparty_id = r.id;
      } catch (e) { showError(e); }
    }
    const reset = () => { form.value = pick(props.lease); };
    return { store, form, master, leases, dirty, save, busy, addCounterparty, reset, CURRENCIES, isLessor };
  },
  template: `
  <div class="card">
    <div class="card-head"><h3>Contract and master data</h3><span class="sub">Lease register fields (spec §1) — commencement is when the lessor makes the asset available (App. A)</span>
      <div class="spacer"></div>
      <template v-if="editable"><button class="btn sm" :disabled="!dirty.length" @click="reset">Discard</button>
      <button class="btn sm primary" :disabled="!dirty.length || busy" @click="save"><AppIcon name="save" :size="13"/> Save {{ dirty.length ? '(' + dirty.length + ')' : '' }}</button></template>
    </div>
    <div class="card-body">
      <fieldset :disabled="!editable" style="border:0;padding:0;margin:0">
      <div class="form-grid">
        <label class="field span-2"><span class="req">Description</span><input v-model="form.description"></label>
        <label class="field">Entity<select v-model="form.entity_id"><option v-for="e in store.entities" :key="e.id" :value="e.id">{{ e.code }} — {{ e.name }}</option></select></label>
        <label class="field">Asset class<select v-model="form.asset_class_id"><option :value="null">—</option><option v-for="a in store.assetClasses" :key="a.id" :value="a.id">{{ a.name }}</option></select></label>
        <label class="field span-2">{{ isLessor ? 'Lessee (counterparty)' : 'Lessor (counterparty)' }}
          <div class="row"><select v-model="form.counterparty_id"><option :value="null">—</option><option v-for="c in master.counterparties" :key="c.id" :value="c.id">{{ c.name }}{{ c.related_party ? ' (related party)' : '' }}</option></select>
          <button type="button" class="btn sm" @click="addCounterparty" v-if="editable"><AppIcon name="plus" :size="13"/></button></div></label>
        <label class="field span-2">Underlying asset / premises<input v-model="form.asset_description"></label>
        <label class="field span-2">Location<input v-model="form.location"></label>
        <label class="field">Business unit<input v-model="form.business_unit"></label>
        <label class="field">Cost centre<input v-model="form.cost_centre"></label>
        <label class="field">Department<input v-model="form.department"></label>
        <label class="field">Project<input v-model="form.project"></label>
        <label class="field">Contract / agreement no.<input v-model="form.contract_number"></label>
        <label class="field">Agreement date<input type="date" v-model="form.contract_date"></label>
        <label class="field"><span class="req">Commencement date</span><input type="date" v-model="form.commencement_date"><span class="hint">Date the asset is made available</span></label>
        <label class="field">Rent / availability date<input type="date" v-model="form.availability_date"></label>
        <label class="field"><span class="req">Contract end (non-extended)</span><input type="date" v-model="form.contract_end"></label>
        <label class="field">Enforceable period ends<input type="date" v-model="form.enforceable_end"><span class="hint">B34 cap — judgment; leave blank if not relevant</span></label>
        <label class="field span-2">Enforceability rationale<input v-model="form.enforceable_rationale" placeholder="e.g. both parties may terminate without more than an insignificant penalty after …"></label>
        <label class="field">Currency<input v-model="form.currency" list="ccy-list" maxlength="3" style="text-transform:uppercase"><datalist id="ccy-list"><option v-for="c in CURRENCIES" :key="c" :value="c"></option></datalist></label>
        <label class="field">Useful life of the asset ends<input type="date" v-model="form.useful_life_end"><span class="hint">Needed if ownership transfers or a purchase option is reasonably certain (para 32)</span></label>
        <label class="field">Our entity is the<select v-model="form.role"><option value="LESSEE">Lessee — we use the asset</option><option value="LESSOR">Lessor — we let out the asset</option></select>
          <span class="hint" v-if="isLessor">Classification inputs are on the Classification tab (paras 61–66)</span></label>
        <label class="field">Accounting model<select v-model="form.lease_type">
          <template v-if="!isLessor"><option value="STANDARD">Capitalise (ROU asset + liability)</option><option value="SHORT_TERM">Short-term exemption (para 6)</option>
          <option value="LOW_VALUE">Low-value exemption (para 6)</option></template>
          <option v-else value="STANDARD">Lessor lease — classify as finance / operating (paras 61–66)</option>
          <option value="SUBLEASE">Sublease (intermediate lessor, B58)</option>
          <option v-if="!isLessor" value="SALE_LEASEBACK">Sale and leaseback (paras 98–103)</option></select></label>
        <label class="field" v-if="form.lease_type==='SUBLEASE'">Head lease<select v-model="form.head_lease_id"><option :value="null">—</option><option v-for="l in leases" :key="l.id" :value="l.id">{{ l.lease_code }} — {{ l.description }}</option></select></label>
        <label class="field" v-if="!isLessor">Non-lease components<select v-model="form.non_lease_expedient">
          <option :value="null">Follow asset-class election</option><option :value="true">Combine (practical expedient, para 15)</option><option :value="false">Separate (para 12)</option></select></label>
        <div class="field" v-else><span>Non-lease components</span><div class="small text-2" style="padding-top:6px">Always separated by a lessor (para 17) — enter CAM / services as non-lease amounts</div></div>
        <label class="check" style="align-self:end;padding-bottom:8px" v-if="!isLessor"><input type="checkbox" v-model="form.ownership_transfers"> Ownership transfers at end of term</label>
        <label class="field span-all">Notes<textarea v-model="form.notes"></textarea></label>
      </div>
      </fieldset>
    </div>
  </div>`,
};

// --------------------------------------------------------------------------- options & lease term judgments
export const OptionsEditor = {
  components: common,
  props: { lease: Object, editable: Boolean, term: Object },
  emits: ['saved'],
  setup(props, { emit }) {
    const rows = ref(clone(props.lease.options || []));
    watch(() => props.lease, (l) => { rows.value = clone(l.options || []); });
    const busy = ref(false);
    const dirty = computed(() => JSON.stringify(rows.value) !== JSON.stringify(props.lease.options || []));
    function add(kind) {
      const end = props.lease.contract_end;
      rows.value.push({ kind, holder: 'LESSEE', exercise_date: kind === 'EXTENSION' && end ? addDays(end, 1) : (kind === 'PURCHASE' ? end : ''),
        extension_end_date: kind === 'EXTENSION' && end ? addDays(addMonths(addDays(end, 1), 60), -1) : '', price: '', renewal_escalation_pct: '',
        reasonably_certain: null, rationale: '', description: '' });
    }
    async function save() {
      const missing = rows.value.filter(r => r.reasonably_certain !== null && r.reasonably_certain !== undefined && !(r.rationale || '').trim());
      if (missing.length) { toast('Document the rationale for every reasonably-certain assessment (B37).', 'bad'); return; }
      busy.value = true;
      try { await put('/api/leases/' + props.lease.id + '/options', rows.value); toast('Options and judgments saved', 'ok'); emit('saved'); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    const question = (r) => r.kind === 'TERMINATION' ? 'Reasonably certain NOT to terminate?' : r.kind === 'PURCHASE' ? 'Reasonably certain to purchase?' : 'Reasonably certain to extend?';
    return { rows, add, save, busy, dirty, question, date };
  },
  template: `
  <div class="card">
    <div class="card-head"><h3>Options and lease-term judgments</h3><span class="sub">Ind AS 116.18–21, B34–B41 · assessed at commencement; reassessed only on significant events (para 20)</span>
      <div class="spacer"></div>
      <template v-if="editable">
        <button class="btn sm" @click="add('EXTENSION')"><AppIcon name="plus" :size="13"/> Extension</button>
        <button class="btn sm" @click="add('TERMINATION')"><AppIcon name="plus" :size="13"/> Termination</button>
        <button class="btn sm" @click="add('PURCHASE')"><AppIcon name="plus" :size="13"/> Purchase</button>
        <button class="btn sm primary" :disabled="!dirty || busy" @click="save"><AppIcon name="save" :size="13"/> Save</button>
      </template>
    </div>
    <div class="card-body flush">
      <div v-if="!rows.length" class="empty">No renewal, termination or purchase options recorded.</div>
      <div v-for="(r, i) in rows" :key="i" style="padding:12px 16px;border-bottom:1px solid var(--border)">
        <fieldset :disabled="!editable" style="border:0;padding:0;margin:0">
        <div class="form-grid">
          <label class="field">Option<select v-model="r.kind"><option value="EXTENSION">Extension / renewal</option><option value="TERMINATION">Termination</option><option value="PURCHASE">Purchase</option></select></label>
          <label class="field">Held by<select v-model="r.holder"><option value="LESSEE">Lessee</option><option value="LESSOR">Lessor</option><option value="BOTH">Both parties</option></select>
            <span class="hint" v-if="r.holder==='LESSOR'">Lessor-only options are ignored for the lease term (B35)</span></label>
          <label class="field">{{ r.kind==='EXTENSION' ? 'Extension period starts' : r.kind==='TERMINATION' ? 'Earliest termination (last day of occupation)' : 'Exercise date' }}<input type="date" v-model="r.exercise_date"></label>
          <label class="field" v-if="r.kind==='EXTENSION'">Extension period ends<input type="date" v-model="r.extension_end_date"></label>
          <label class="field" v-if="r.kind==='EXTENSION'">Rent uplift on renewal %<input class="num" v-model="r.renewal_escalation_pct" placeholder="0"></label>
          <label class="field" v-if="r.kind!=='EXTENSION'">{{ r.kind==='PURCHASE' ? 'Exercise price' : 'Termination penalty' }}<input class="num" v-model="r.price"></label>
          <label class="field span-2">Description<input v-model="r.description"></label>
          <div class="field span-2"><span>{{ question(r) }}</span><TriState v-model="r.reasonably_certain" :disabled="!editable"/>
            <span class="hint" v-if="r.reasonably_certain===null || r.reasonably_certain===undefined" style="color:var(--warn)">Accounting judgment required — calculation is blocked until assessed.</span></div>
          <label class="field span-2">Rationale (B37 factors: improvements, relocation cost, penalties, importance, past practice)<textarea v-model="r.rationale" style="min-height:40px"></textarea></label>
        </div>
        <div class="row" style="justify-content:flex-end" v-if="editable"><button class="btn sm danger" @click="rows.splice(i,1)"><AppIcon name="trash-2" :size="13"/> Remove</button></div>
        </fieldset>
      </div>
      <div v-if="term" class="card-body" style="background:var(--surface-2)">
        <div class="small"><b>Lease term (last calculation):</b> {{ date(term.commencement) }} to {{ date(term.term_end) }} · {{ term.term_months }} months · non-cancellable to {{ date(term.noncancellable_end) }}</div>
        <ul class="small text-2" style="margin:6px 0 0 18px;padding:0"><li v-for="(x, i) in term.explanation" :key="i">{{ x }}</li></ul>
      </div>
    </div>
  </div>`,
};

// --------------------------------------------------------------------------- lease identification & exemptions
export const AssessmentForm = {
  components: common,
  props: { lease: Object, editable: Boolean, threshold: [String, Number] },
  emits: ['saved'],
  setup(props, { emit }) {
    const blank = { identified_asset: null, substitution_rights: '', economic_benefits: null, directs_use: null, contains_lease: null,
      separate_components: null, allocation_method: '', exemption: 'NONE', asset_value_when_new: '', benefits_on_own: null,
      not_highly_dependent: null, conclusion: '', notes: '' };
    const pick = () => ({ ...blank, ...(props.lease.assessment || {}) });
    const form = ref(pick());
    watch(() => props.lease, () => { form.value = pick(); });
    const busy = ref(false);
    const auto = computed(() => {
      const f = form.value;
      if (f.identified_asset === false || f.substitution_rights === 'SUBSTANTIVE') return 'Not a lease — no identified asset (paras 9, B13–B20).';
      if (f.economic_benefits === false || f.directs_use === false) return 'Not a lease — the customer does not control the use of the asset (B21–B31).';
      if (f.identified_asset && f.economic_benefits && f.directs_use) return 'Contains a lease (para 9) — identified asset, substantially all economic benefits and right to direct use.';
      return 'Complete the three criteria to conclude.';
    });
    async function save() {
      busy.value = true;
      try { await put('/api/leases/' + props.lease.id + '/assessment', form.value); toast('Assessment saved', 'ok'); emit('saved'); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    return { form, save, busy, auto, money };
  },
  template: `
  <div class="grid c2">
    <div class="card">
      <div class="card-head"><h3>Does the contract contain a lease?</h3><span class="sub">Ind AS 116.9–11, B9–B31</span><div class="spacer"></div>
        <button v-if="editable" class="btn sm primary" :disabled="busy" @click="save"><AppIcon name="save" :size="13"/> Save assessment</button></div>
      <div class="card-body"><fieldset :disabled="!editable" style="border:0;padding:0;margin:0"><div class="col" style="gap:12px">
        <div class="field"><span>1. Is there an identified asset (explicitly or implicitly specified)? — B13</span><TriState v-model="form.identified_asset" :disabled="!editable"/></div>
        <label class="field">Supplier substitution rights — B14–B19<select v-model="form.substitution_rights">
          <option value="">Not assessed</option><option value="NONE">None</option><option value="NOT_SUBSTANTIVE">Exist but not substantive</option>
          <option value="SUBSTANTIVE?">Possibly substantive — review</option><option value="SUBSTANTIVE">Substantive (no identified asset)</option></select></label>
        <div class="field"><span>2. Right to obtain substantially all economic benefits from use? — B21–B23</span><TriState v-model="form.economic_benefits" :disabled="!editable"/></div>
        <div class="field"><span>3. Right to direct how and for what purpose the asset is used? — B24–B30</span><TriState v-model="form.directs_use" :disabled="!editable"/></div>
        <div class="alert info"><AppIcon name="info"/><div>{{ auto }}</div></div>
        <div class="field"><span>Conclusion: contract contains a lease</span><TriState v-model="form.contains_lease" :disabled="!editable"/></div>
        <label class="field">Conclusion narrative (for the file)<textarea v-model="form.conclusion"></textarea></label>
      </div></fieldset></div>
    </div>
    <div class="col" style="gap:14px">
      <div class="card">
        <div class="card-head"><h3>Components</h3><span class="sub">Ind AS 116.12–17</span></div>
        <div class="card-body"><fieldset :disabled="!editable" style="border:0;padding:0;margin:0"><div class="col" style="gap:12px">
          <div class="field"><span>Contract has separate non-lease components (CAM, services, maintenance)?</span><TriState v-model="form.separate_components" :disabled="!editable"/></div>
          <label class="field">Allocation basis<select v-model="form.allocation_method">
            <option value="">—</option><option value="RELATIVE_SSP">Relative stand-alone prices (para 13–14)</option>
            <option value="CONTRACT_SPLIT">Contractual split corroborated by observable prices</option>
            <option value="EXPEDIENT_COMBINE">Practical expedient — combine (para 15)</option></select></label>
        </div></fieldset></div>
      </div>
      <div class="card">
        <div class="card-head"><h3>Recognition exemptions</h3><span class="sub">Ind AS 116.5–8, B3–B8 — validated by the engine</span></div>
        <div class="card-body"><fieldset :disabled="!editable" style="border:0;padding:0;margin:0"><div class="col" style="gap:12px">
          <label class="field">Exemption applied<select v-model="form.exemption"><option value="NONE">None — capitalise</option><option value="SHORT_TERM">Short-term (≤ 12 months, no purchase option)</option><option value="LOW_VALUE">Low-value asset</option></select></label>
          <template v-if="form.exemption==='LOW_VALUE'">
            <label class="field">Value of the underlying asset when new<input class="num" v-model="form.asset_value_when_new"><span class="hint">Entity policy threshold: {{ threshold ? money(threshold) : 'not set (Settings → Policies)' }} · assessed on an absolute basis (B4)</span></label>
            <div class="field"><span>Lessee can benefit from the asset on its own or with readily available resources? — B5(a)</span><TriState v-model="form.benefits_on_own" :disabled="!editable"/></div>
            <div class="field"><span>Asset is not highly dependent on / interrelated with other assets? — B5(b)</span><TriState v-model="form.not_highly_dependent" :disabled="!editable"/></div>
          </template>
          <div v-if="form.exemption==='SHORT_TERM'" class="small text-2">The short-term exemption is an election by class of underlying asset (para 8). The engine confirms the lease term (including reasonably-certain options) is 12 months or less and that there is no purchase option.</div>
          <label class="field">Notes<textarea v-model="form.notes"></textarea></label>
        </div></fieldset></div>
      </div>
    </div>
  </div>`,
};

// --------------------------------------------------------------------------- payment terms (generator)
export function normTerms(cfg, lease) {
  const c = { ...defaultTerms(lease), ...clone(cfg || {}) };
  c.escalations = (c.escalations || []).map(e => ({ kind: 'PERCENT', every_months: 12, first_date: '', compounding: true, applies_to: 'LEASE', ...e, first_date: e.first_date || '' }));
  c.rent_free = (c.rent_free || []).map(r => ({ applies_to: 'LEASE', ...r }));
  c.steps = (c.steps || []).map(x => ({ non_lease_amount: '', ...x }));
  if (c.due_day === null || c.due_day === undefined) c.due_day = '';
  if (c.escalation_anchor === null || c.escalation_anchor === undefined) c.escalation_anchor = '';
  return c;
}

export function defaultTerms(lease) {
  return { amount: '', start_date: lease?.commencement_date || '', end_date: lease?.contract_end || '', frequency_months: 1, timing: 'ADVANCE',
    alignment: 'ANNIVERSARY', due_day: '', due_offset_days: 0, non_lease_amount: '0', category: 'FIXED', description: 'Rent',
    prorate_partial: true, escalations: [], rent_free: [], steps: [], escalation_anchor: '' };
}

export const PaymentTermsForm = {
  components: common,
  props: { modelValue: Object, editable: Boolean, compact: Boolean },
  emits: ['update:modelValue'],
  setup(props) {
    const cfg = computed(() => props.modelValue);
    const addEsc = () => cfg.value.escalations.push({ value: '', kind: 'PERCENT', every_months: 12, first_date: '', compounding: true, applies_to: 'LEASE' });
    const addFree = () => cfg.value.rent_free.push({ start: cfg.value.start_date || '', end: '', applies_to: 'LEASE' });
    const addStep = () => cfg.value.steps.push({ start: '', amount: '', non_lease_amount: '' });
    return { cfg, addEsc, addFree, addStep, FREQUENCIES, CATEGORIES };
  },
  template: `
  <fieldset :disabled="!editable" style="border:0;padding:0;margin:0">
    <div class="form-grid">
      <label class="field"><span class="req">Lease payment per period</span><input class="num" v-model="cfg.amount" placeholder="e.g. 450000"><span class="hint">Lease component only; excl. GST</span></label>
      <label class="field">Frequency<select v-model.number="cfg.frequency_months"><option v-for="f in FREQUENCIES" :key="f.v" :value="f.v">{{ f.l }}</option></select></label>
      <label class="field">Timing<select v-model="cfg.timing"><option value="ADVANCE">In advance</option><option value="ARREARS">In arrears</option></select></label>
      <label class="field">Period alignment<select v-model="cfg.alignment"><option value="ANNIVERSARY">Lease anniversary</option><option value="CALENDAR">Calendar months</option></select></label>
      <label class="field"><span class="req">Payments from</span><input type="date" v-model="cfg.start_date"></label>
      <label class="field"><span class="req">Payments to (last day covered)</span><input type="date" v-model="cfg.end_date"></label>
      <label class="field">Due day of month<input class="num" v-model="cfg.due_day" placeholder="period start"><span class="hint">e.g. 7 = on or before the 7th</span></label>
      <label class="field">Non-lease component per period<input class="num" v-model="cfg.non_lease_amount"><span class="hint">CAM / maintenance / services</span></label>
      <label class="field">Category<select v-model="cfg.category"><option v-for="c in CATEGORIES" :key="c.v" :value="c.v">{{ c.l }} ({{ c.ref }})</option></select></label>
      <label class="field">Line description<input v-model="cfg.description"></label>
      <label class="check" style="align-self:end;padding-bottom:8px"><input type="checkbox" v-model="cfg.prorate_partial"> Pro-rate broken periods</label>
    </div>
    <div class="mt">
      <div class="row"><h4 class="grow">Escalations <span class="muted small">— fixed escalations are fixed payments (27(a))</span></h4><button v-if="editable" type="button" class="btn sm" @click="addEsc"><AppIcon name="plus" :size="13"/> Escalation</button></div>
      <table class="t compact mt" v-if="cfg.escalations.length"><thead><tr><th>Increase</th><th>Type</th><th>Every (months)</th><th>First effective</th><th>Basis</th><th>Applies to</th><th></th></tr></thead>
        <tbody><tr v-for="(e, i) in cfg.escalations" :key="i">
          <td><input class="num" v-model="e.value" style="width:90px"></td>
          <td><select v-model="e.kind"><option value="PERCENT">%</option><option value="AMOUNT">Amount</option></select></td>
          <td><input class="num" v-model.number="e.every_months" style="width:70px"></td>
          <td><input type="date" v-model="e.first_date"></td>
          <td><select v-model="e.compounding"><option :value="true">On last rent (compound)</option><option :value="false">On base rent (simple)</option></select></td>
          <td><select v-model="e.applies_to"><option value="LEASE">Lease</option><option value="NON_LEASE">Non-lease</option><option value="BOTH">Both</option></select></td>
          <td><button v-if="editable" type="button" class="btn sm icon ghost" @click="cfg.escalations.splice(i,1)"><AppIcon name="trash-2" :size="13"/></button></td>
        </tr></tbody></table>
    </div>
    <div class="mt">
      <div class="row"><h4 class="grow">Rent-free / fit-out periods <span class="muted small">— nil payments; accounting still starts at commencement</span></h4><button v-if="editable" type="button" class="btn sm" @click="addFree"><AppIcon name="plus" :size="13"/> Rent-free</button></div>
      <table class="t compact mt" v-if="cfg.rent_free.length"><thead><tr><th>From</th><th>To (inclusive)</th><th>Applies to</th><th></th></tr></thead>
        <tbody><tr v-for="(r, i) in cfg.rent_free" :key="i"><td><input type="date" v-model="r.start"></td><td><input type="date" v-model="r.end"></td>
          <td><select v-model="r.applies_to"><option value="LEASE">Lease component</option><option value="BOTH">Lease and non-lease</option></select></td>
          <td><button v-if="editable" type="button" class="btn sm icon ghost" @click="cfg.rent_free.splice(i,1)"><AppIcon name="trash-2" :size="13"/></button></td></tr></tbody></table>
    </div>
    <div class="mt" v-if="!compact || cfg.steps.length">
      <div class="row"><h4 class="grow">Stepped rent table <span class="muted small">— overrides the amount from each date</span></h4><button v-if="editable" type="button" class="btn sm" @click="addStep"><AppIcon name="plus" :size="13"/> Step</button></div>
      <table class="t compact mt" v-if="cfg.steps.length"><thead><tr><th>From</th><th class="num">Lease amount / period</th><th class="num">Non-lease / period</th><th></th></tr></thead>
        <tbody><tr v-for="(s, i) in cfg.steps" :key="i"><td><input type="date" v-model="s.start"></td><td><input class="num" v-model="s.amount"></td><td><input class="num" v-model="s.non_lease_amount"></td>
          <td><button v-if="editable" type="button" class="btn sm icon ghost" @click="cfg.steps.splice(i,1)"><AppIcon name="trash-2" :size="13"/></button></td></tr></tbody></table>
    </div>
  </fieldset>`,
};

export const PaymentTermsCard = {
  components: { ...common, PaymentTermsForm },
  props: { lease: Object, editable: Boolean },
  emits: ['saved'],
  setup(props, { emit }) {
    const cfg = ref(normTerms(props.lease.generator_config, props.lease));
    watch(() => props.lease, (l) => { cfg.value = normTerms(l.generator_config, l); });
    const busy = ref(false);
    async function save() {
      busy.value = true;
      try {
        const r = await put('/api/leases/' + props.lease.id + '/payment-terms', cfg.value);
        toast(r.generated + ' payment line(s) generated from the terms', 'ok');
        emit('saved');
      } catch (e) { showError(e); } finally { busy.value = false; }
    }
    return { cfg, save, busy };
  },
  template: `
  <div class="card">
    <div class="card-head"><h3>Payment terms</h3><span class="sub">Generates the dated schedule (fixed, escalations, rent-free, steps, non-lease). Manual lines are kept.</span><div class="spacer"></div>
      <button v-if="editable" class="btn sm primary" :disabled="busy" @click="save"><AppIcon name="wand-sparkles" :size="13"/> Save and generate schedule</button></div>
    <div class="card-body"><PaymentTermsForm v-model="cfg" :editable="editable"/></div>
  </div>`,
};

// --------------------------------------------------------------------------- payment schedule (line level)
export const PaymentScheduleEditor = {
  components: common,
  props: { lease: Object, editable: Boolean, summary: Object },
  emits: ['saved'],
  setup(props, { emit }) {
    const rows = ref(clone(props.lease.payments || []));
    watch(() => props.lease, (l) => { rows.value = clone(l.payments || []); });
    const editing = ref(false);
    const busy = ref(false);
    const cls = computed(() => {
      const m = {};
      for (const p of (props.summary?.payments || [])) m[p.line_no + '|' + p.date] = p;
      return m;
    });
    const info = (r) => cls.value[r.line_no + '|' + r.date];
    function add() {
      rows.value.push({ line_no: rows.value.length + 1, date: '', period_start: '', period_end: '', lease_amount: '', non_lease_amount: '0',
        category: 'FIXED', include_override: null, override_reason: '', description: '', source: 'MANUAL' });
    }
    async function save() {
      busy.value = true;
      try { await put('/api/leases/' + props.lease.id + '/payments', rows.value); toast('Payment schedule saved', 'ok'); editing.value = false; emit('saved'); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    const totals = computed(() => {
      let la = 0, nl = 0;
      rows.value.forEach(r => { la += Number(r.lease_amount || 0); nl += Number(r.non_lease_amount || 0); });
      return { la: la.toFixed(2), nl: nl.toFixed(2) };
    });
    const cancel = () => { rows.value = clone(props.lease.payments || []); editing.value = false; };
    return { rows, editing, busy, add, save, cancel, info, totals, money, date, CATEGORIES, catLabel };
  },
  template: `
  <div class="card">
    <div class="card-head"><h3>Payment schedule</h3><span class="sub">{{ rows.length }} line(s) · inclusion in the liability is decided line by line with a reason (27–28, 38)</span><div class="spacer"></div>
      <template v-if="editable && !editing"><button class="btn sm" @click="editing=true"><AppIcon name="square-pen" :size="13"/> Edit lines</button></template>
      <template v-if="editing"><button class="btn sm" @click="add"><AppIcon name="plus" :size="13"/> Line</button><button class="btn sm" @click="cancel">Cancel</button>
        <button class="btn sm primary" :disabled="busy" @click="save"><AppIcon name="save" :size="13"/> Save lines</button></template>
    </div>
    <div class="alert info" v-if="editing" style="margin:10px 12px 0"><AppIcon name="info"/><div>Edits to generated lines are replaced if the payment terms are regenerated — add irregular payments as new (manual) lines. An inclusion override requires a reason.</div></div>
    <div class="table-wrap" style="max-height:560px">
      <table class="t compact">
        <thead><tr><th>#</th><th>Due date</th><th>Period</th><th class="num">Lease amount</th><th class="num">Non-lease</th><th>Category</th><th>Description</th><th>In liability?</th><th>Reason / override</th></tr></thead>
        <tbody>
          <tr v-if="!rows.length"><td colspan="9" class="empty">No payment lines. Enter payment terms and generate the schedule, or add lines manually.</td></tr>
          <tr v-for="(r, i) in rows" :key="i" :class="info(r) && !info(r).included ? 'muted-row' : ''">
            <td>{{ i + 1 }}</td>
            <template v-if="editing">
              <td><input type="date" v-model="r.date"></td>
              <td><div class="row" style="gap:4px"><input type="date" v-model="r.period_start"><input type="date" v-model="r.period_end"></div></td>
              <td><input class="num" v-model="r.lease_amount" style="width:120px"></td>
              <td><input class="num" v-model="r.non_lease_amount" style="width:100px"></td>
              <td><select v-model="r.category"><option v-for="c in CATEGORIES" :key="c.v" :value="c.v">{{ c.l }}</option></select></td>
              <td><input v-model="r.description"></td>
              <td><select v-model="r.include_override"><option :value="null">Engine decides</option><option :value="true">Force include</option><option :value="false">Force exclude</option></select></td>
              <td><input v-model="r.override_reason" :placeholder="r.include_override!==null && r.include_override!==undefined ? 'Reason required' : ''"></td>
            </template>
            <template v-else>
              <td class="nowrap">{{ date(r.date) }}</td>
              <td class="nowrap small text-2">{{ r.period_start ? date(r.period_start) + ' – ' + date(r.period_end) : '' }}</td>
              <td class="num">{{ money(r.lease_amount) }}</td>
              <td class="num">{{ money(r.non_lease_amount, {zeroDash:true}) }}</td>
              <td class="small">{{ catLabel(r.category) }}</td>
              <td class="small">{{ r.description }} <span v-if="r.source==='MANUAL'" class="chip">manual</span><span v-if="r.source==='OPTION'" class="chip">option period</span></td>
              <td><span v-if="info(r)" class="badge" :class="info(r).included ? 'ok' : 'draft'">{{ info(r).included ? 'Included' : 'Excluded' }}</span><span v-else class="muted small">—</span></td>
              <td class="small text-2 wrap">{{ r.override_reason || (info(r) ? info(r).inclusion_reason : '') }}</td>
            </template>
          </tr>
          <tr class="total" v-if="rows.length"><td colspan="3">Total (undiscounted)</td><td class="num">{{ money(totals.la) }}</td><td class="num">{{ money(totals.nl) }}</td><td colspan="4"></td></tr>
        </tbody>
      </table>
    </div>
  </div>`,
};

// --------------------------------------------------------------------------- ROU build-up inputs
export const CostsEditor = {
  components: common,
  props: { lease: Object, editable: Boolean },
  emits: ['saved'],
  setup(props, { emit }) {
    const rows = ref(clone(props.lease.costs || []));
    watch(() => props.lease, (l) => { rows.value = clone(l.costs || []); });
    const busy = ref(false);
    const add = (kind) => rows.value.push({ kind, date: props.lease.commencement_date || '', amount: '', description: '' });
    async function save() {
      busy.value = true;
      try { await put('/api/leases/' + props.lease.id + '/costs', rows.value); toast('ROU adjustments saved', 'ok'); emit('saved'); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    const KINDS = { IDC: 'Initial direct cost — 24(c)', INCENTIVE: 'Lease incentive received — 24(b)', PREPAID: 'Payment at / before commencement — 24(b)', OTHER: 'Other ROU adjustment' };
    return { rows, add, save, busy, KINDS, money };
  },
  template: `
  <div class="card">
    <div class="card-head"><h3>Initial direct costs, incentives and prepayments</h3><span class="sub">Ind AS 116.24 — ROU asset build-up</span><div class="spacer"></div>
      <template v-if="editable"><button class="btn sm" @click="add('IDC')"><AppIcon name="plus" :size="13"/> IDC</button><button class="btn sm" @click="add('INCENTIVE')"><AppIcon name="plus" :size="13"/> Incentive</button>
      <button class="btn sm" @click="add('PREPAID')"><AppIcon name="plus" :size="13"/> Prepayment</button><button class="btn sm primary" :disabled="busy" @click="save"><AppIcon name="save" :size="13"/> Save</button></template></div>
    <div class="card-body flush">
      <table class="t compact"><thead><tr><th>Type</th><th>Date</th><th class="num">Amount</th><th>Description</th><th></th></tr></thead>
        <tbody><tr v-if="!rows.length"><td colspan="5" class="empty">None recorded. Stamp duty, registration and brokerage borne by the lessee are initial direct costs.</td></tr>
          <tr v-for="(r, i) in rows" :key="i">
            <td><select v-model="r.kind" :disabled="!editable"><option v-for="(l, k) in KINDS" :key="k" :value="k">{{ l }}</option></select></td>
            <td><input type="date" v-model="r.date" :disabled="!editable"></td>
            <td><input class="num" v-model="r.amount" :disabled="!editable" style="width:140px"></td>
            <td><input v-model="r.description" :disabled="!editable"></td>
            <td><button v-if="editable" class="btn sm icon ghost" @click="rows.splice(i,1)"><AppIcon name="trash-2" :size="13"/></button></td></tr></tbody></table>
    </div>
  </div>`,
};

export const DepositForm = {
  components: common,
  props: { lease: Object, editable: Boolean },
  emits: ['saved'],
  setup(props, { emit }) {
    const blank = () => ({ amount: '', payment_date: props.lease.commencement_date || '', refund_date: props.lease.contract_end ? addDays(props.lease.contract_end, 1) : '',
      interest_bearing: false, contractual_rate_pct: '', market_rate_pct: '', treat_difference_as_prepaid_rent: true, notes: '' });
    const form = ref(props.lease.deposit ? { ...blank(), ...clone(props.lease.deposit) } : blank());
    watch(() => props.lease, (l) => { form.value = l.deposit ? { ...blank(), ...clone(l.deposit) } : blank(); });
    const busy = ref(false);
    const lessor = computed(() => props.lease.role === 'LESSOR' && props.lease.lease_type !== 'SUBLEASE');
    async function save(remove = false) {
      if (!remove && form.value.amount && form.value.market_rate_pct === '' && !form.value.interest_bearing) {
        toast('A market interest rate is required to fair-value an interest-free deposit (Ind AS 109).', 'bad'); return;
      }
      busy.value = true;
      try { await put('/api/leases/' + props.lease.id + '/deposit', remove ? null : form.value); toast(remove ? 'Deposit removed' : 'Deposit saved', 'ok'); emit('saved'); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    return { form, save, busy, lessor };
  },
  template: `
  <div class="card">
    <div class="card-head"><h3>{{ lessor ? 'Security deposit received from the lessee' : 'Refundable security deposit' }}</h3>
      <span class="sub">{{ lessor ? 'Financial liability — Ind AS 109 at fair value; excess received is a lease payment received in advance' : 'Financial asset — Ind AS 109 at fair value; difference to ROU as prepaid rent' }}</span><div class="spacer"></div>
      <template v-if="editable"><button class="btn sm danger" v-if="lease.deposit" @click="save(true)">Remove</button><button class="btn sm primary" :disabled="busy" @click="save(false)"><AppIcon name="save" :size="13"/> Save</button></template></div>
    <div class="card-body"><fieldset :disabled="!editable" style="border:0;padding:0;margin:0"><div class="form-grid">
      <label class="field">{{ lessor ? 'Amount received' : 'Amount paid' }}<input class="num" v-model="form.amount"></label>
      <label class="field">{{ lessor ? 'Received on' : 'Paid on' }}<input type="date" v-model="form.payment_date"></label>
      <label class="field">Expected refund date<input type="date" v-model="form.refund_date"></label>
      <label class="field">Market interest rate % p.a.<input class="num" v-model="form.market_rate_pct"><span class="hint">{{ lessor ? "Lessor's borrowing rate for a similar-tenor liability" : "Lessee's rate for a similar-tenor financial asset" }}</span></label>
      <label class="check" style="align-self:end;padding-bottom:8px"><input type="checkbox" v-model="form.interest_bearing"> Interest-bearing deposit</label>
      <label class="field" v-if="form.interest_bearing">Contractual rate % p.a.<input class="num" v-model="form.contractual_rate_pct"></label>
      <label class="check" style="align-self:end;padding-bottom:8px"><input type="checkbox" v-model="form.treat_difference_as_prepaid_rent"> {{ lessor ? 'Excess over fair value is a lease payment received in advance' : 'Difference is prepaid rent (added to ROU)' }}</label>
      <label class="field span-all">Notes<input v-model="form.notes"></label>
    </div></fieldset></div>
  </div>`,
};

export const RestorationForm = {
  components: common,
  props: { lease: Object, editable: Boolean },
  emits: ['saved'],
  setup(props, { emit }) {
    const blank = () => ({ estimated_cost: '', settlement_date: props.lease.contract_end ? addDays(props.lease.contract_end, 1) : '', discount_rate_pct: '',
      recognition_date: props.lease.commencement_date || '', cost_is_current_price: false, inflation_pct: '', notes: '' });
    const form = ref(props.lease.restoration ? { ...blank(), ...clone(props.lease.restoration) } : blank());
    watch(() => props.lease, (l) => { form.value = l.restoration ? { ...blank(), ...clone(l.restoration) } : blank(); });
    const busy = ref(false);
    async function save(remove = false) {
      busy.value = true;
      try { await put('/api/leases/' + props.lease.id + '/restoration', remove ? null : form.value); toast(remove ? 'Obligation removed' : 'Restoration obligation saved', 'ok'); emit('saved'); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    return { form, save, busy };
  },
  template: `
  <div class="card">
    <div class="card-head"><h3>Restoration / dismantling obligation</h3><span class="sub">Ind AS 37 provision; PV added to the ROU asset — 24(d)</span><div class="spacer"></div>
      <template v-if="editable"><button class="btn sm danger" v-if="lease.restoration" @click="save(true)">Remove</button><button class="btn sm primary" :disabled="busy" @click="save(false)"><AppIcon name="save" :size="13"/> Save</button></template></div>
    <div class="card-body"><fieldset :disabled="!editable" style="border:0;padding:0;margin:0"><div class="form-grid">
      <label class="field">Estimated cost<input class="num" v-model="form.estimated_cost"></label>
      <label class="check" style="align-self:end;padding-bottom:8px"><input type="checkbox" v-model="form.cost_is_current_price"> Estimate is at today's prices</label>
      <label class="field" v-if="form.cost_is_current_price">Inflation % p.a.<input class="num" v-model="form.inflation_pct"></label>
      <label class="field">Expected settlement<input type="date" v-model="form.settlement_date"></label>
      <label class="field">Pre-tax discount rate % (Ind AS 37.47)<input class="num" v-model="form.discount_rate_pct"></label>
      <label class="field">Obligation arises on<input type="date" v-model="form.recognition_date"></label>
      <label class="field span-all">Basis of estimate<input v-model="form.notes" placeholder="e.g. facility team estimate dated …"></label>
    </div></fieldset></div>
  </div>`,
};

// --------------------------------------------------------------------------- discount rate
export const RatePanel = {
  components: common,
  props: { lease: Object, editable: Boolean, initial: Object },
  emits: ['saved'],
  setup(props, { emit }) {
    const pick = (l) => ({ discount_rate_pct: l.discount_rate_pct ?? '', rate_basis: l.rate_basis || 'IBR', rate_source: l.rate_source || '', discount_rate_id: l.discount_rate_id ?? null });
    const form = ref(pick(props.lease));
    const pol = ref({ daycount: '', rate_convention: '', depreciation_method: '', current_split_method: '', commencement_payment_paid: '', ...(props.lease.policy_overrides || {}) });
    watch(() => props.lease, (l) => { form.value = pick(l); pol.value = { daycount: '', rate_convention: '', depreciation_method: '', current_split_method: '', commencement_payment_paid: '', ...(l.policy_overrides || {}) }; });
    const suggestion = ref(null);
    const busy = ref(false);
    async function lookup() {
      try {
        const l = props.lease;
        const months = l.commencement_date && l.contract_end ? Math.round((new Date(l.contract_end) - new Date(l.commencement_date)) / (86400000 * 30.4375)) : 0;
        suggestion.value = await post('/api/discount-rates/lookup', { currency: l.currency, tenor_months: months, date: l.commencement_date, entity_id: l.entity_id });
        suggestion.value.tenor = months;
      } catch (e) { showError(e); }
    }
    function apply() {
      const s = suggestion.value;
      form.value.discount_rate_pct = s.rate;
      form.value.discount_rate_id = s.id;
      form.value.rate_basis = 'IBR';
      form.value.rate_source = s.message + (s.methodology ? ' — ' + s.methodology : '') + (s.source ? ' (source: ' + s.source + ')' : '');
    }
    async function save() {
      busy.value = true;
      const overrides = Object.fromEntries(Object.entries(pol.value).filter(([, v]) => v !== '' && v !== null));
      try { await patch('/api/leases/' + props.lease.id, { ...form.value, policy_overrides: overrides }); toast('Discount rate saved', 'ok'); emit('saved'); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    return { form, pol, suggestion, lookup, apply, save, busy, num };
  },
  template: `
  <div class="grid c2">
    <div class="card">
      <div class="card-head"><h3>Discount rate</h3><span class="sub">Ind AS 116.26 — rate implicit in the lease if readily determinable, otherwise the lessee's IBR</span><div class="spacer"></div>
        <button v-if="editable" class="btn sm primary" :disabled="busy" @click="save"><AppIcon name="save" :size="13"/> Save</button></div>
      <div class="card-body"><fieldset :disabled="!editable" style="border:0;padding:0;margin:0"><div class="form-grid">
        <label class="field"><span class="req">Annual rate %</span><input class="num" v-model="form.discount_rate_pct" placeholder="e.g. 9.25"></label>
        <label class="field">Basis<select v-model="form.rate_basis"><option value="IBR">Incremental borrowing rate</option><option value="IMPLICIT">Rate implicit in the lease</option></select></label>
        <label class="field span-all">Source, methodology and approval<textarea v-model="form.rate_source" placeholder="Reference rate + credit spread + security / tenor adjustments; approved by …"></textarea></label>
      </div>
      <div class="row mt" v-if="editable"><button class="btn sm" @click="lookup"><AppIcon name="search" :size="13"/> Look up approved IBR table</button></div>
      <div v-if="suggestion" class="alert mt" :class="suggestion.rate ? 'ok' : 'warn'"><AppIcon :name="suggestion.rate ? 'circle-check' : 'triangle-alert'"/>
        <div class="grow">{{ suggestion.message }} <span class="muted">(tenor {{ suggestion.tenor }} months)</span></div>
        <button v-if="suggestion.rate && editable" class="btn sm" @click="apply">Apply</button></div>
      </fieldset></div>
    </div>
    <div class="card">
      <div class="card-head"><h3>Calculation conventions for this lease</h3><span class="sub">Blank = entity policy (Settings)</span></div>
      <div class="card-body"><fieldset :disabled="!editable" style="border:0;padding:0;margin:0"><div class="form-grid">
        <label class="field">Rate convention<select v-model="pol.rate_convention"><option value="">Entity policy</option><option value="EFFECTIVE_ANNUAL">Effective annual</option><option value="NOMINAL_MONTHLY">Nominal, compounded monthly</option><option value="NOMINAL_QUARTERLY">Nominal, compounded quarterly</option><option value="NOMINAL_SEMIANNUAL">Nominal, compounded half-yearly</option></select></label>
        <label class="field">Day count<select v-model="pol.daycount"><option value="">Entity policy</option><option value="ACT/365F">Actual/365 fixed (XNPV-consistent)</option><option value="MONTHS/12">Months/12 (periodic)</option></select></label>
        <label class="field">Depreciation<select v-model="pol.depreciation_method"><option value="">Entity policy</option><option value="DAILY">Straight-line, daily</option><option value="MONTHLY_EQUAL">Straight-line, equal monthly</option></select></label>
        <label class="field">Current / non-current split<select v-model="pol.current_split_method"><option value="">Entity policy</option><option value="PRINCIPAL_12M">Principal reduction in next 12 months</option><option value="PV_12M">PV of next 12 months' payments</option></select></label>
      </div></fieldset>
      <div v-if="initial" class="mt">
        <div class="stat-line"><span>Rate used in last calculation</span><span class="num">{{ num(initial.rate_pct, 4) }}%</span></div>
        <div class="stat-line"><span>Effective annual rate</span><span class="num">{{ num(initial.effective_annual_rate * 100, 6) }}%</span></div>
        <div class="stat-line"><span>Day count / convention</span><span>{{ initial.daycount }} · {{ initial.convention }}</span></div>
      </div></div>
    </div>
  </div>`,
};

// --------------------------------------------------------------------------- generic JSON details (lessor, sublease, SLB, cut-over, tax)
export const DETAIL_SPECS = {
  lessor_details: { title: 'Lessor classification and measurement inputs', sub: 'Ind AS 116.61–66 (classification), 67–80 (finance), 81–88 (operating)', fields: [
    { key: 'fair_value', label: 'Fair value of the underlying asset (at inception)', type: 'money', hint: 'Needed for the PV test 63(d)' },
    { key: 'carrying_amount', label: 'Carrying amount of the asset', type: 'money', hint: 'Derecognised on a finance lease' },
    { key: 'economic_life_months', label: 'Economic life of the asset (months)', type: 'int', hint: 'Needed for the term test 63(c)' },
    { key: 'unguaranteed_residual', label: 'Unguaranteed residual value (end of term)', type: 'money', hint: 'Needed to solve the implicit rate' },
    { key: 'residual_date', label: 'Residual value date (blank = day after the term)', type: 'date' },
    { key: 'lessor_idc', label: 'Lessor initial direct costs (brokerage, stamp duty borne)', type: 'money', hint: 'Finance: in the net investment (69); operating: added to the asset (83)' },
    { key: 'implicit_rate_pct', label: 'Rate implicit in the lease % (blank = solve)', type: 'pct' },
    { key: 'substantially_all_pct', label: '"Substantially all" benchmark % (policy, default 90)', type: 'pct' }, { key: 'major_part_pct', label: '"Major part" benchmark % (policy, default 75)', type: 'pct' },
    { key: 'income_method', label: 'Operating lease income basis', type: 'select', options: [['', 'Entity policy (Settings)'], ['MONTHLY_EQUAL', 'Straight-line — equal monthly'], ['DAILY', 'Straight-line — daily']] },
    { key: 'transfers_ownership', label: '63(a) Ownership transfers to the lessee', type: 'bool' }, { key: 'bargain_purchase_option', label: '63(b) Purchase option well below fair value', type: 'bool' },
    { key: 'specialised_asset', label: '63(e) Specialised asset', type: 'bool' }, { key: 'lessee_bears_cancellation_losses', label: "64(a) Lessee bears lessor's cancellation losses", type: 'bool' },
    { key: 'residual_fv_gains_to_lessee', label: '64(b) Residual fair-value gains / losses to lessee', type: 'bool' }, { key: 'bargain_renewal', label: '64(c) Secondary period at below-market rent', type: 'bool' },
    { key: 'manufacturer_dealer', label: 'Manufacturer / dealer lessor (paras 71–74)', type: 'bool' },
    { key: 'market_rate_pct', label: 'Market rate % (manufacturer / dealer with artificially low rate, para 73)', type: 'pct' },
    { key: 'classification_override', label: 'Record the classification (judgment)', type: 'select', options: [['', 'None — conclude from the indicators'], ['FINANCE', 'Finance lease'], ['OPERATING', 'Operating lease']] },
    { key: 'override_rationale', label: 'Rationale for the recorded classification (required)', type: 'textarea' }] },
  sublease_details: { title: 'Sublease inputs', sub: 'Ind AS 116.B58 — classified by reference to the ROU asset', fields: [
    { key: 'portion_subleased', label: 'Portion of head-lease ROU subleased (0–1)', type: 'text' },
    { key: 'implicit_rate_pct', label: 'Rate implicit in the sublease % (blank = head-lease rate, para 68)', type: 'pct' },
    { key: 'classification_override', label: 'Classification override', type: 'select', options: [['', 'None — use indicators'], ['FINANCE', 'Finance sublease'], ['OPERATING', 'Operating sublease']] },
    { key: 'override_rationale', label: 'Override rationale', type: 'textarea' }] },
  slb_details: { title: 'Sale and leaseback', sub: 'Ind AS 116.98–103 — transfer assessed under Ind AS 115', fields: [
    { key: 'is_sale', label: 'Transfer is a sale under Ind AS 115 (para 99)', type: 'tri' },
    { key: 'asset_description', label: 'Asset sold', type: 'text' }, { key: 'carrying_amount', label: 'Carrying amount before sale', type: 'money' },
    { key: 'sale_consideration', label: 'Sale consideration', type: 'money' }, { key: 'fair_value', label: 'Fair value of the asset', type: 'money' },
    { key: 'assessment_notes', label: 'Ind AS 115 assessment notes', type: 'textarea' }] },
  opening_balance: { title: 'Cut-over / opening balances', sub: 'Migrating a lease mid-life: carry forward approved balances', fields: [
    { key: 'cutover_date', label: 'Cut-over date (opening balances as at start of)', type: 'date' }, { key: 'liability', label: 'Lease liability', type: 'money' },
    { key: 'rou_cost', label: 'ROU gross carrying amount', type: 'money' }, { key: 'rou_acc_dep', label: 'Accumulated depreciation', type: 'money' },
    { key: 'rou_acc_imp', label: 'Accumulated impairment', type: 'money' },
    { key: 'use_implied_rate', label: 'Derive the rate implied by the opening liability', type: 'bool' }] },
  tax_settings: { title: 'Deferred tax settings (this lease)', sub: 'Ind AS 12 — blank = entity default', fields: [
    { key: 'tax_rate_pct', label: 'Tax rate %', type: 'pct' }, { key: 'rou_tax_base', label: 'Tax base of ROU asset', type: 'money' },
    { key: 'liability_tax_base', label: 'Tax base of lease liability', type: 'money' }, { key: 'dta_recoverable', label: 'DTA probable of recovery', type: 'bool' },
    { key: 'offset_permitted', label: 'DTA/DTL offset permitted (Ind AS 12.74)', type: 'bool' }] },
};

export const DetailsForm = {
  components: common,
  props: { lease: Object, field: String, editable: Boolean },
  emits: ['saved'],
  setup(props, { emit }) {
    const spec = computed(() => DETAIL_SPECS[props.field]);
    const form = ref(clone(props.lease[props.field] || {}));
    watch(() => props.lease, (l) => { form.value = clone(l[props.field] || {}); });
    const busy = ref(false);
    async function save() {
      busy.value = true;
      const out = Object.fromEntries(Object.entries(form.value).filter(([, v]) => v !== '' && v !== undefined));
      try { await patch('/api/leases/' + props.lease.id, { [props.field]: out }); toast(spec.value.title + ' saved', 'ok'); emit('saved'); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    return { spec, form, save, busy };
  },
  template: `
  <div class="card">
    <div class="card-head"><h3>{{ spec.title }}</h3><span class="sub">{{ spec.sub }}</span><div class="spacer"></div>
      <button v-if="editable" class="btn sm primary" :disabled="busy" @click="save"><AppIcon name="save" :size="13"/> Save</button></div>
    <div class="card-body"><fieldset :disabled="!editable" style="border:0;padding:0;margin:0"><div class="form-grid">
      <template v-for="f in spec.fields" :key="f.key">
        <label v-if="f.type==='bool'" class="check" style="align-self:end;padding-bottom:8px"><input type="checkbox" v-model="form[f.key]"> {{ f.label }}</label>
        <div v-else-if="f.type==='tri'" class="field span-2"><span>{{ f.label }}</span><TriState v-model="form[f.key]" :disabled="!editable"/></div>
        <label v-else-if="f.type==='select'" class="field">{{ f.label }}<select v-model="form[f.key]"><option v-for="o in f.options" :key="o[0]" :value="o[0]">{{ o[1] }}</option></select></label>
        <label v-else-if="f.type==='textarea'" class="field span-all">{{ f.label }}<textarea v-model="form[f.key]"></textarea></label>
        <label v-else-if="f.type==='date'" class="field">{{ f.label }}<input type="date" v-model="form[f.key]"></label>
        <label v-else class="field">{{ f.label }}<input :class="['money','pct','int'].includes(f.type) ? 'num' : ''" v-model="form[f.key]"><span class="hint" v-if="f.hint">{{ f.hint }}</span></label>
      </template>
    </div></fieldset></div>
  </div>`,
};
