// Settings: company & policies, controls, AI engine, IBR table, FX rates, GL mapping, master data, users, system
import { store, get, post, put, toast, showError, confirmDialog } from '../store.js';
import { common } from '../components.js';
import { money, date, dateTime, num, titleCase, clone, today } from '../util.js';

const { ref, computed, watch, onMounted } = Vue;
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

export const SettingsPage = {
  components: common,
  props: { route: Object },
  setup(props) {
    const tab = ref(props.route?.query?.tab || 'company');
    const cfg = ref(null);
    const company = ref(null);
    const caps = ref(null);
    const aiTest = ref(null);
    const rates = ref([]);
    const fx = ref([]);
    const maps = ref([]);
    const master = ref({ entities: [], asset_classes: [], counterparties: [], gl_roles: [] });
    const users = ref({ users: [], roles: [] });
    const newRate = ref(null);
    const newFx = ref(null);
    const edit = ref(null);
    const userEdit = ref(null);
    const busy = ref(false);
    const buckets = ref('');
    async function loadSettings() {
      const r = await get('/api/settings');
      cfg.value = r.settings; company.value = r.company;
      buckets.value = (r.settings.policies.maturity_buckets || []).join(', ');
    }
    async function loadTab() {
      try {
        if (['company', 'controls', 'ai'].includes(tab.value) && !cfg.value) await loadSettings();
        if (tab.value === 'ai' || tab.value === 'system') caps.value = caps.value || await get('/api/system/capabilities');
        if (tab.value === 'rates') rates.value = await get('/api/discount-rates');
        if (tab.value === 'fx') fx.value = await get('/api/fx-rates');
        if (tab.value === 'gl') { maps.value = await get('/api/gl-mappings'); master.value = await get('/api/master'); }
        if (tab.value === 'master' || tab.value === 'rates') master.value = await get('/api/master');
        if (tab.value === 'users' && store.can('users.manage')) users.value = await get('/api/users');
      } catch (e) { showError(e); }
    }
    onMounted(loadTab);
    watch(tab, loadTab);
    watch(() => props.route?.query?.tab, (t) => { if (t) tab.value = t; });
    const canWrite = computed(() => store.can('settings.write'));
    async function saveSettings(sections) {
      const reason = await confirmDialog('Save settings', 'Policy and control changes are recorded in the audit trail and apply to future calculations only (existing runs are immutable).', { input: 'Reason for the change', ok: 'Save' });
      if (reason === false) return;
      busy.value = true;
      try {
        const s = {};
        sections.forEach(k => { s[k] = clone(cfg.value[k]); });
        if (s.policies) {
          s.policies.maturity_buckets = buckets.value.split(',').map(x => parseInt(x.trim(), 10)).filter(n => n > 0);
          if (s.policies.low_value_threshold === '') s.policies.low_value_threshold = null;
        }
        const r = await put('/api/settings', { company: sections.includes('policies') ? company.value : {}, settings: s, _reason: reason });
        cfg.value = r.settings;
        toast('Settings saved', 'ok');
        await window.__lease116?.boot();
      } catch (e) { showError(e); } finally { busy.value = false; }
    }
    async function detect(probe = false) {
      try { aiTest.value = await post('/api/settings/ai/test', { probe }); } catch (e) { showError(e); }
    }
    // IBR
    function addRate() { newRate.value = { currency: 'INR', tenor_from_months: 0, tenor_to_months: 60, rate_pct: '', effective_date: today(), entity_id: '', rate_type: 'IBR', security: 'Secured', source: '', methodology: '', scope: 'PORTFOLIO' }; }
    async function saveRate() {
      try { await post('/api/discount-rates', newRate.value); toast('Rate saved as Draft — approval required', 'ok'); newRate.value = null; loadTab(); } catch (e) { showError(e); }
    }
    async function approveRate(r) {
      try { await post('/api/discount-rates/' + r.id + '/approve'); toast('Rate approved', 'ok'); loadTab(); } catch (e) { showError(e); }
    }
    // FX
    function addFx() { newFx.value = { from_ccy: 'USD', to_ccy: store.company?.functional_currency || 'INR', rate_date: today(), rate: '', rate_type: 'CLOSING', source: 'RBI reference rate' }; }
    async function saveFx() { try { await post('/api/fx-rates', newFx.value); toast('FX rate saved', 'ok'); newFx.value = null; loadTab(); } catch (e) { showError(e); } }
    // GL
    function addMap() { maps.value.push({ role: '', account_code: '', account_name: '', entity_id: null, asset_class_id: null, cost_centre: '', lease_type: '' }); }
    async function saveMaps() {
      try { await put('/api/gl-mappings', maps.value); toast('GL mapping saved', 'ok'); loadTab(); } catch (e) { showError(e); }
    }
    // master
    function editMaster(kind, obj) {
      const blank = { entities: { code: '', name: '', functional_currency: 'INR', cin: '', pan: '' },
        asset_classes: { code: '', name: '', short_term_election: false, non_lease_expedient: false, default_useful_life_months: '' },
        counterparties: { name: '', vendor_id: '', related_party: false, contact_person: '', email: '', phone: '', address: '', pan: '', gstin: '' } }[kind];
      edit.value = { kind, obj: { ...blank, ...(obj ? clone(obj) : {}) } };
    }
    async function saveMaster() {
      try { await post('/api/master/' + edit.value.kind, edit.value.obj); toast('Saved', 'ok'); edit.value = null; await loadTab(); await window.__lease116?.boot(); }
      catch (e) { showError(e); }
    }
    // users
    function editUser(u) {
      userEdit.value = u ? { ...clone(u), password: '' } : { username: '', full_name: '', email: '', role: 'PREPARER', active: true, all_entities: true, entity_ids: [], password: '' };
    }
    async function saveUser() {
      try { await post('/api/users', userEdit.value); toast('User saved', 'ok'); userEdit.value = null; loadTab(); } catch (e) { showError(e); }
    }
    // system
    async function backup() {
      try { const r = await post('/api/system/backup'); toast('Backup created: ' + r.file, 'ok', 9000); } catch (e) { showError(e); }
    }
    async function demo() {
      if (!(await confirmDialog('Load demonstration data', 'Adds a DEMO entity with 11 illustrative leases and demo users (password Lease@116). Use only in a practice workspace.', { ok: 'Load demo data' }))) return;
      try { const r = await post('/api/system/demo-data'); toast('Demo data loaded (' + r.created + ' leases)', 'ok'); await window.__lease116?.boot(); } catch (e) { showError(e); }
    }
    const entName = (id) => (master.value.entities.find(e => e.id === id) || {}).code || 'All';
    const acName = (id) => (master.value.asset_classes.find(e => e.id === id) || {}).name || 'All';
    const tabs = computed(() => [
      { key: 'company', label: 'Company & policies' }, { key: 'controls', label: 'Controls' }, { key: 'ai', label: 'AI engine' },
      { key: 'rates', label: 'Discount rates (IBR)' }, { key: 'fx', label: 'FX rates' }, { key: 'gl', label: 'GL mapping' },
      { key: 'master', label: 'Master data' }, ...(store.can('users.manage') ? [{ key: 'users', label: 'Users & roles' }] : []), { key: 'system', label: 'System' }]);
    return { store, tab, tabs, cfg, company, caps, aiTest, rates, fx, maps, master, users, newRate, newFx, edit, userEdit, busy, buckets, canWrite,
      saveSettings, detect, addRate, saveRate, approveRate, addFx, saveFx, addMap, saveMaps, editMaster, saveMaster, editUser, saveUser, backup, demo,
      entName, acName, MONTHS, money, date, dateTime, num, titleCase };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>Settings</h1><div class="sub">Entity policies and controls. Every change is audit-logged with old and new values and a reason.</div></div></div>
    <Tabs :tabs="tabs" v-model="tab"/>

    <div v-if="tab==='company' && cfg" class="grid c2">
      <div class="card"><div class="card-head"><h3>Company and framework</h3></div><div class="card-body"><fieldset :disabled="!canWrite" style="border:0;padding:0;margin:0"><div class="form-grid">
        <label class="field span-2">Workspace / company name<input v-model="company.name"></label>
        <label class="field">Framework<select v-model="company.framework"><option value="IND_AS_116">Ind AS 116 (India)</option><option value="IFRS_16">IFRS 16</option></select></label>
        <label class="field">Functional currency<input v-model="company.functional_currency" maxlength="3"></label>
        <label class="field">Financial year starts<select v-model.number="company.fy_start_month"><option v-for="(m, i) in MONTHS" :key="m" :value="i+1">{{ m }}</option></select></label>
        <label class="field">Number format<select v-model="cfg.display.number_format"><option value="INDIAN">Indian (12,34,567.00)</option><option value="INTERNATIONAL">International (1,234,567.00)</option></select></label>
      </div></fieldset></div>
        <div class="card-head" style="border-top:1px solid var(--border)"><h3>Deferred tax defaults</h3><span class="sub">Ind AS 12 support (not a tax computation)</span></div>
        <div class="card-body"><fieldset :disabled="!canWrite" style="border:0;padding:0;margin:0"><div class="form-grid">
          <label class="field">Tax rate %<input class="num" v-model="cfg.tax.tax_rate_pct"><span class="hint">e.g. 25.168 (s.115BAA incl. surcharge & cess) — confirm</span></label>
          <label class="field">Tax base of ROU<input class="num" v-model="cfg.tax.rou_tax_base"></label>
          <label class="field">Tax base of liability<input class="num" v-model="cfg.tax.liability_tax_base"></label>
          <label class="check"><input type="checkbox" v-model="cfg.tax.dta_recoverable"> DTA probable of recovery</label>
          <label class="check"><input type="checkbox" v-model="cfg.tax.offset_permitted"> Offset DTA/DTL (Ind AS 12.74)</label></div></fieldset></div>
        <div class="card-head" style="border-top:1px solid var(--border)"><h3>Journals</h3></div>
        <div class="card-body"><fieldset :disabled="!canWrite" style="border:0;padding:0;margin:0"><div class="form-grid">
          <label class="field">Payments credited to<select v-model="cfg.journal.payment_credit_role"><option value="LESSOR_PAYABLE">Lessor payable (AP)</option><option value="BANK">Bank</option></select></label>
          <label class="field">Tally company name<input v-model="cfg.journal.tally_company" placeholder="as in Tally"></label></div></fieldset></div>
      </div>
      <div class="card"><div class="card-head"><h3>Calculation policies</h3><span class="sub">Apply to new calculations; lease-level overrides available</span><div class="spacer"></div>
        <button v-if="canWrite" class="btn sm primary" :disabled="busy" @click="saveSettings(['policies','display','tax','journal'])"><AppIcon name="save" :size="13"/> Save</button></div>
        <div class="card-body"><fieldset :disabled="!canWrite" style="border:0;padding:0;margin:0"><div class="form-grid">
          <label class="field">Day count<select v-model="cfg.policies.daycount"><option value="ACT/365F">Actual/365 fixed (XNPV-consistent)</option><option value="MONTHS/12">Months/12 (periodic)</option></select></label>
          <label class="field">Rate convention<select v-model="cfg.policies.rate_convention"><option value="EFFECTIVE_ANNUAL">Effective annual</option><option value="NOMINAL_MONTHLY">Nominal, monthly compounding</option><option value="NOMINAL_QUARTERLY">Nominal, quarterly</option><option value="NOMINAL_SEMIANNUAL">Nominal, half-yearly</option></select></label>
          <label class="field">Depreciation<select v-model="cfg.policies.depreciation_method"><option value="DAILY">Straight-line, daily</option><option value="MONTHLY_EQUAL">Straight-line, equal monthly</option></select></label>
          <label class="field">Current / non-current<select v-model="cfg.policies.current_split_method"><option value="PRINCIPAL_12M">Principal reduction in next 12 months</option><option value="PV_12M">PV of next 12 months' payments</option></select></label>
          <label class="field">Operating lease income (lessor)<select v-model="cfg.policies.lessor_income_method"><option value="MONTHLY_EQUAL">Straight-line, equal monthly</option><option value="DAILY">Straight-line, daily</option></select><span class="hint">Ind AS 116.81 — both are straight-line bases</span></label>
          <label class="field">Rounding<select v-model="cfg.policies.rounding_method"><option value="BALANCE">Round balances; movements by difference</option><option value="INTEREST_TRUEUP">Round interest; true-up at end</option></select></label>
          <label class="field">Currency decimals<input class="num" v-model.number="cfg.policies.currency_decimals"></label>
          <label class="field">Maturity buckets (years)<input v-model="buckets"><span class="hint">e.g. 1, 2, 3, 4, 5 → "more than 5 years" is added</span></label>
          <label class="field">Low-value threshold (asset value when new)<input class="num" v-model="cfg.policies.low_value_threshold" placeholder="not set"><span class="hint">Entity policy — the standard sets no amount (BC100: ~US$5,000 was the Board's reference)</span></label>
          <label class="check"><input type="checkbox" v-model="cfg.policies.commencement_payment_paid"> Payment due on the commencement date is treated as paid at commencement</label>
          <label class="check"><input type="checkbox" v-model="cfg.policies.deposit_difference_as_prepaid_rent"> Deposit fair-value difference is prepaid rent</label>
          <label class="field span-all">Non-creditable GST policy<input v-model="cfg.policies.gst_non_creditable_policy"></label>
        </div></fieldset></div></div>
    </div>

    <div v-if="tab==='controls' && cfg" class="card"><div class="card-head"><h3>Internal controls</h3><div class="spacer"></div><button v-if="canWrite" class="btn sm primary" @click="saveSettings(['controls'])"><AppIcon name="save" :size="13"/> Save</button></div>
      <div class="card-body"><fieldset :disabled="!canWrite" style="border:0;padding:0;margin:0"><div class="col" style="gap:12px">
        <label class="check"><input type="checkbox" v-model="cfg.controls.segregation_of_duties"> Segregation of duties — the preparer cannot review or approve their own calculation or import</label>
        <label class="check"><input type="checkbox" v-model="cfg.controls.two_step_review"> Two-step review — a reviewer must start the review before an approver can approve</label>
        <label class="field" style="max-width:320px">Security deposit materiality for Ind AS 109 flag<input class="num" v-model="cfg.controls.materiality_deposit"></label>
        <div class="alert info"><AppIcon name="info"/><div>Other controls always on: immutable calculation runs with input hashes, period locks, reason-mandatory reopening, audit trail of every change / export / login, and explicit consent before any document is sent to a cloud AI service.</div></div>
      </div></fieldset></div></div>

    <div v-if="tab==='ai' && cfg" class="grid c2">
      <div class="card"><div class="card-head"><h3>Agreement reader engine</h3><div class="spacer"></div><button v-if="canWrite" class="btn sm primary" @click="saveSettings(['ai'])"><AppIcon name="save" :size="13"/> Save</button></div>
        <div class="card-body"><fieldset :disabled="!canWrite" style="border:0;padding:0;margin:0"><div class="col" style="gap:12px">
          <label class="field">Default engine<select v-model="cfg.ai.mode"><option value="rules">Offline rules + OCR + computer vision</option><option value="local">Offline + local AI model (Ollama / LM Studio)</option><option value="claude">Claude API (cloud) — requires consent per document</option></select></label>
          <div class="form-grid">
            <label class="field">Local server type<select v-model="cfg.ai.local.kind"><option value="ollama">Ollama</option><option value="openai">LM Studio / OpenAI-compatible</option></select></label>
            <label class="field">Server URL<input v-model="cfg.ai.local.base_url"></label>
            <label class="field">Text model<input v-model="cfg.ai.local.model" placeholder="e.g. qwen2.5:7b-instruct"></label>
            <label class="field">Vision model (OCR fallback)<input v-model="cfg.ai.local.vision_model" placeholder="optional, e.g. qwen2.5vl:7b"></label>
            <label class="field">OCR engine<select v-model="cfg.ai.ocr_engine"><option value="auto">Automatic</option><option value="rapidocr">RapidOCR (PP-OCR, ONNX)</option><option value="tesseract">Tesseract</option><option value="vision-llm">Local vision model</option></select></label>
          </div>
          <div class="row"><button type="button" class="btn sm" @click="detect(false)"><AppIcon name="search" :size="13"/> Detect local AI servers</button><button type="button" class="btn sm" @click="detect(true)" :disabled="!cfg.ai.local.model"><AppIcon name="play" :size="13"/> Test model</button></div>
          <div v-if="aiTest" class="alert" :class="(aiTest.local_servers||[]).length ? 'ok' : 'warn'"><AppIcon name="bot"/><div>
            <div v-if="!(aiTest.local_servers||[]).length">No local AI server found on localhost:11434 (Ollama) or :1234 (LM Studio). The rule engine and OCR work without one.</div>
            <div v-for="s in aiTest.local_servers" :key="s.base_url"><b>{{ s.kind }}</b> at {{ s.base_url }} — models: <button v-for="m in s.models" :key="m" type="button" class="chip" style="cursor:pointer;margin:2px" @click="cfg.ai.local.kind = s.kind; cfg.ai.local.base_url = s.base_url; cfg.ai.local.model = m">{{ m }}</button></div>
            <div v-if="aiTest.probe" class="small">Model test: OK {{ JSON.stringify(aiTest.probe) }}</div><div v-if="aiTest.probe_error" class="small neg">Model test failed: {{ aiTest.probe_error }}</div></div></div>
          <hr style="border:0;border-top:1px solid var(--border);width:100%">
          <label class="check"><input type="checkbox" v-model="cfg.ai.allow_cloud"> Allow cloud AI (Claude API) for this workspace</label>
          <div class="alert warn" v-if="cfg.ai.allow_cloud"><AppIcon name="triangle-alert"/><div class="small">Document text is sent to Anthropic only when a user explicitly confirms it for that document; each consent is audit-logged. Check your engagement letter / client confidentiality terms before enabling.</div></div>
          <div class="form-grid" v-if="cfg.ai.allow_cloud">
            <label class="field">Claude API key<input type="password" v-model="cfg.ai.claude.api_key" :placeholder="cfg.ai.claude.has_key ? 'stored (leave unchanged)' : 'sk-ant-…'" autocomplete="off"></label>
            <label class="field">Model<input v-model="cfg.ai.claude.model" placeholder="blank = latest available Sonnet"></label>
          </div>
        </div></fieldset></div></div>
      <div class="card"><div class="card-head"><h3>This computer</h3></div><div class="card-body" v-if="caps">
        <div class="stat-line"><span>Python</span><span>{{ caps.python }}</span></div><div class="stat-line"><span>Platform</span><span class="small">{{ caps.platform }}</span></div>
        <div class="stat-line"><span>PDF engine</span><span>{{ caps.pdf_engine }}</span></div><div class="stat-line"><span>Computer vision</span><span>{{ caps.computer_vision }}</span></div>
        <div class="stat-line"><span>OCR engines</span><span>{{ (caps.ocr_engines||[]).join(', ') || 'none — scanned PDFs need OCR' }}</span></div>
        <div class="stat-line"><span>Local AI servers</span><span>{{ (caps.local_llm_servers||[]).map(s => s.kind).join(', ') || 'none running' }}</span></div>
        <div class="stat-line"><span>Claude SDK</span><span>{{ caps.claude_sdk ? 'installed' : 'not installed' }}</span></div>
        <div class="small muted mt">To add a free local model: install Ollama from ollama.com, run <span class="mono">ollama pull qwen2.5:7b-instruct</span>, then click Detect.</div>
      </div></div>
    </div>

    <div v-if="tab==='rates'">
      <div class="row mb"><div class="grow small text-2">Portfolio IBR table by currency and tenor. New rates are Draft until approved; approved rates are locked (add a new effective date to change). Lease-specific rates are entered on the lease with support.</div>
        <button v-if="store.can('rate.write')" class="btn primary" @click="addRate"><AppIcon name="plus" :size="14"/> Add rate</button></div>
      <div class="card"><table class="t compact"><thead><tr><th>Currency</th><th>Tenor (months)</th><th class="num">Rate %</th><th>Effective</th><th>Entity</th><th>Security</th><th>Source / methodology</th><th>Status</th><th></th></tr></thead>
        <tbody><tr v-if="!rates.length"><td colspan="9" class="empty">No discount rates. Add the IBR build-up approved by management.</td></tr>
          <tr v-for="r in rates" :key="r.id"><td>{{ r.currency }}</td><td>{{ r.tenor_from_months }}–{{ r.tenor_to_months }}</td><td class="num">{{ num(r.rate_pct, 2) }}</td><td>{{ date(r.effective_date) }}</td><td>{{ entName(r.entity_id) }}</td><td>{{ r.security || '—' }}</td>
            <td class="small wrap">{{ r.source }}<span v-if="r.methodology"> — {{ r.methodology }}</span></td><td><StatusBadge :status="r.status"/></td>
            <td><button v-if="r.status==='Draft' && store.can('rate.approve')" class="btn sm primary" @click="approveRate(r)">Approve</button></td></tr></tbody></table></div>
      <Modal v-if="newRate" title="Add discount rate" @close="newRate=null"><div class="form-grid">
        <label class="field">Currency<input v-model="newRate.currency" maxlength="3"></label><label class="field">Tenor from (months)<input class="num" v-model.number="newRate.tenor_from_months"></label>
        <label class="field">Tenor to (months)<input class="num" v-model.number="newRate.tenor_to_months"></label><label class="field">Rate % p.a.<input class="num" v-model="newRate.rate_pct"></label>
        <label class="field">Effective from<input type="date" v-model="newRate.effective_date"></label>
        <label class="field">Entity<select v-model="newRate.entity_id"><option value="">All entities</option><option v-for="e in master.entities" :key="e.id" :value="e.id">{{ e.code }}</option></select></label>
        <label class="field">Security<select v-model="newRate.security"><option>Secured</option><option>Unsecured</option></select></label>
        <label class="field span-2">Source<input v-model="newRate.source" placeholder="e.g. bank term-loan sanction letter dated …"></label>
        <label class="field span-all">Methodology<textarea v-model="newRate.methodology" placeholder="Reference rate (e.g. G-sec / MCLR for tenor) + entity credit spread + security / term adjustments"></textarea></label></div>
        <template #foot><button class="btn" @click="newRate=null">Cancel</button><button class="btn primary" @click="saveRate">Save as Draft</button></template></Modal>
    </div>

    <div v-if="tab==='fx'">
      <div class="row mb"><div class="grow small text-2">Closing rates (balance-sheet retranslation), average rates (interest, P&amp;L) and spot rates (payments). Ind AS 21.</div>
        <button v-if="store.can('rate.write')" class="btn primary" @click="addFx"><AppIcon name="plus" :size="14"/> Add rate</button></div>
      <div class="card"><DataTable id="fx" :columns="[{key:'from_ccy',label:'From'},{key:'to_ccy',label:'To'},{key:'rate_date',label:'Date',type:'date'},{key:'rate',label:'Rate',type:'rate'},{key:'rate_type',label:'Type'},{key:'source',label:'Source'}]" :rows="fx" empty-text="No FX rates."/></div>
      <Modal v-if="newFx" title="Add FX rate" @close="newFx=null"><div class="form-grid">
        <label class="field">From currency<input v-model="newFx.from_ccy" maxlength="3"></label><label class="field">To currency<input v-model="newFx.to_ccy" maxlength="3"></label>
        <label class="field">Date<input type="date" v-model="newFx.rate_date"></label><label class="field">Rate<input class="num" v-model="newFx.rate"></label>
        <label class="field">Type<select v-model="newFx.rate_type"><option value="CLOSING">Closing</option><option value="AVERAGE">Average (period)</option><option value="SPOT">Spot (transaction)</option></select></label>
        <label class="field">Source<input v-model="newFx.source"></label></div>
        <template #foot><button class="btn" @click="newFx=null">Cancel</button><button class="btn primary" @click="saveFx">Save</button></template></Modal>
    </div>

    <div v-if="tab==='gl'">
      <div class="row mb"><div class="grow small text-2">Map each accounting role to your chart of accounts. The most specific match wins (entity, asset class, cost centre, lease type); unmapped roles use the default codes shown.</div>
        <template v-if="canWrite"><button class="btn" @click="addMap"><AppIcon name="plus" :size="14"/> Mapping</button><button class="btn primary" @click="saveMaps"><AppIcon name="save" :size="14"/> Save</button></template></div>
      <div class="card"><div class="table-wrap" style="max-height:620px"><table class="t compact"><thead><tr><th>Role</th><th>Account code</th><th>Account name</th><th>Entity</th><th>Asset class</th><th>Cost centre</th><th>Lease type</th><th></th></tr></thead>
        <tbody><tr v-for="(m, i) in maps" :key="i">
          <td><select v-model="m.role" :disabled="!canWrite"><option value="">—</option><option v-for="r in master.gl_roles" :key="r.role" :value="r.role">{{ titleCase(r.role) }} ({{ r.nature }})</option></select></td>
          <td><input v-model="m.account_code" :disabled="!canWrite" style="width:110px"></td><td><input v-model="m.account_name" :disabled="!canWrite"></td>
          <td><select v-model="m.entity_id" :disabled="!canWrite"><option :value="null">All</option><option v-for="e in master.entities" :key="e.id" :value="e.id">{{ e.code }}</option></select></td>
          <td><select v-model="m.asset_class_id" :disabled="!canWrite"><option :value="null">All</option><option v-for="a in master.asset_classes" :key="a.id" :value="a.id">{{ a.name }}</option></select></td>
          <td><input v-model="m.cost_centre" :disabled="!canWrite" style="width:100px"></td>
          <td><select v-model="m.lease_type" :disabled="!canWrite"><option value="">All</option><option value="STANDARD">Standard</option><option value="SHORT_TERM">Short-term</option><option value="LOW_VALUE">Low-value</option><option value="SUBLEASE">Sublease</option><option value="SALE_LEASEBACK">Sale & leaseback</option></select></td>
          <td><button v-if="canWrite" class="btn sm icon ghost" @click="maps.splice(i,1)"><AppIcon name="trash-2" :size="13"/></button></td></tr></tbody></table></div></div>
    </div>

    <div v-if="tab==='master'" class="col" style="gap:14px">
      <div class="card"><div class="card-head"><h3>Entities</h3><div class="spacer"></div><button v-if="canWrite" class="btn sm" @click="editMaster('entities')"><AppIcon name="plus" :size="13"/> Entity</button></div>
        <table class="t compact"><thead><tr><th>Code</th><th>Name</th><th>Functional ccy</th><th>CIN</th><th>PAN</th><th></th></tr></thead>
          <tbody><tr v-for="e in master.entities" :key="e.id"><td>{{ e.code }}</td><td>{{ e.name }}</td><td>{{ e.functional_currency }}</td><td>{{ e.cin || '—' }}</td><td>{{ e.pan || '—' }}</td><td class="right"><button v-if="canWrite" class="btn sm" @click="editMaster('entities', e)">Edit</button></td></tr></tbody></table></div>
      <div class="card"><div class="card-head"><h3>Asset classes</h3><span class="sub">Class-level elections: short-term exemption (para 8) and non-lease expedient (para 15)</span><div class="spacer"></div><button v-if="canWrite" class="btn sm" @click="editMaster('asset_classes')"><AppIcon name="plus" :size="13"/> Class</button></div>
        <table class="t compact"><thead><tr><th>Code</th><th>Name</th><th>Short-term election</th><th>Combine non-lease components</th><th></th></tr></thead>
          <tbody><tr v-for="a in master.asset_classes" :key="a.id"><td>{{ a.code }}</td><td>{{ a.name }}</td><td>{{ a.short_term_election ? 'Elected' : 'No' }}</td><td>{{ a.non_lease_expedient ? 'Elected' : 'No — separate' }}</td><td class="right"><button v-if="canWrite" class="btn sm" @click="editMaster('asset_classes', a)">Edit</button></td></tr></tbody></table></div>
      <div class="card"><div class="card-head"><h3>Counterparties</h3><div class="spacer"></div><button v-if="store.can('lease.write')" class="btn sm" @click="editMaster('counterparties')"><AppIcon name="plus" :size="13"/> Counterparty</button></div>
        <DataTable id="cps" :columns="[{key:'name',label:'Name'},{key:'vendor_id',label:'Vendor ID'},{key:'related_party',label:'Related party',type:'bool'},{key:'pan',label:'PAN'},{key:'gstin',label:'GSTIN'},{key:'contact_person',label:'Contact'},{key:'email',label:'Email'}]" :rows="master.counterparties" clickable @row-click="r => store.can('lease.write') && editMaster('counterparties', r)" :page-size="10"/></div>
      <Modal v-if="edit" :title="(edit.obj.id ? 'Edit ' : 'New ') + ({entities: 'entity', asset_classes: 'asset class', counterparties: 'counterparty'})[edit.kind]" @close="edit=null"><div class="form-grid">
        <template v-for="(v, k) in edit.obj" :key="k"><template v-if="k!=='id'">
          <label v-if="typeof v === 'boolean'" class="check"><input type="checkbox" v-model="edit.obj[k]"> {{ titleCase(k) }}</label>
          <label v-else class="field">{{ titleCase(k) }}<input v-model="edit.obj[k]"></label></template></template></div>
        <template #foot><button class="btn" @click="edit=null">Cancel</button><button class="btn primary" @click="saveMaster">Save</button></template></Modal>
    </div>

    <div v-if="tab==='users'">
      <div class="row mb"><div class="grow small text-2">Roles: Administrator, Lease Accountant, Preparer, Reviewer, Approver, Auditor (read-only with audit trail), Read-only. Users can be restricted to entities.</div>
        <button class="btn primary" @click="editUser(null)"><AppIcon name="plus" :size="14"/> User</button></div>
      <div class="card"><table class="t compact"><thead><tr><th>Username</th><th>Name</th><th>Role</th><th>Entities</th><th>Active</th><th>Last login</th><th></th></tr></thead>
        <tbody><tr v-for="u in users.users" :key="u.id"><td><b>{{ u.username }}</b></td><td>{{ u.full_name }}</td><td>{{ u.role_name }}</td><td>{{ u.all_entities ? 'All' : (u.entity_ids || []).length + ' selected' }}</td>
          <td><span class="badge" :class="u.active ? 'ok' : 'bad'">{{ u.active ? 'Active' : 'Disabled' }}</span></td><td>{{ dateTime(u.last_login) }}</td><td class="right"><button class="btn sm" @click="editUser(u)">Edit</button></td></tr></tbody></table></div>
      <div class="card mt"><div class="card-head"><h3>Role permissions</h3></div><table class="t compact"><thead><tr><th>Role</th><th>Permissions</th></tr></thead>
        <tbody><tr v-for="r in users.roles" :key="r.code"><td class="nowrap"><b>{{ r.name }}</b></td><td class="small">{{ r.permissions.join(', ') }}</td></tr></tbody></table></div>
      <Modal v-if="userEdit" :title="userEdit.id ? 'Edit user' : 'New user'" @close="userEdit=null"><div class="form-grid">
        <label class="field">Username<input v-model="userEdit.username" :disabled="!!userEdit.id"></label><label class="field">Full name<input v-model="userEdit.full_name"></label>
        <label class="field">Email<input v-model="userEdit.email"></label>
        <label class="field">Role<select v-model="userEdit.role"><option v-for="r in users.roles" :key="r.code" :value="r.code">{{ r.name }}</option></select></label>
        <label class="field">{{ userEdit.id ? 'Reset password (optional)' : 'Initial password' }}<input type="password" v-model="userEdit.password" autocomplete="new-password"><span class="hint">Min. 8 characters; user must change it at first sign-in</span></label>
        <label class="check"><input type="checkbox" v-model="userEdit.active"> Active</label>
        <label class="check"><input type="checkbox" v-model="userEdit.all_entities"> Access to all entities</label>
        <div class="field span-all" v-if="!userEdit.all_entities"><span>Entities</span><div class="row wrap"><label v-for="e in store.entities" :key="e.id" class="check"><input type="checkbox" :value="e.id" v-model="userEdit.entity_ids"> {{ e.code }}</label></div></div></div>
        <template #foot><button class="btn" @click="userEdit=null">Cancel</button><button class="btn primary" @click="saveUser">Save</button></template></Modal>
    </div>

    <div v-if="tab==='system'" class="grid c2">
      <div class="card"><div class="card-head"><h3>Installation</h3></div><div class="card-body" v-if="caps">
        <div class="stat-line"><span>Version</span><span>Lease116 v{{ caps.version }}</span></div>
        <div class="stat-line"><span>Data folder</span><span class="mono small">{{ caps.data_dir }}</span></div>
        <div class="stat-line"><span>Python</span><span>{{ caps.python }} ({{ caps.machine }})</span></div>
        <div class="small muted mt">All data (database, documents, backups) is stored in the data folder on this computer.</div></div></div>
      <div class="card"><div class="card-head"><h3>Maintenance</h3></div><div class="card-body col" style="gap:10px">
        <button v-if="canWrite" class="btn" @click="backup"><AppIcon name="database" :size="14"/> Back up database and documents now</button>
        <button v-if="canWrite" class="btn" @click="demo"><AppIcon name="layers" :size="14"/> Load demonstration portfolio</button>
        <a class="btn" href="/api/docs" target="_blank"><AppIcon name="external-link" :size="14"/> API documentation (OpenAPI)</a>
      </div></div>
    </div>
  </div>`,
};
