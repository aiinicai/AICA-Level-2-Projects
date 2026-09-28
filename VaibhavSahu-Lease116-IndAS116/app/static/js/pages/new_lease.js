// New lease: AI agreement reader (upload → review → create) and the manual entry wizard
import { store, get, post, put, del, upload, toast, showError, confirmDialog } from '../store.js';
import { common } from '../components.js';
import { money, date, dateTime, num, titleCase, clone, addMonths, addDays, today } from '../util.js';
import { PaymentTermsForm, defaultTerms, CURRENCIES } from './lease_forms.js';

const { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } = Vue;

const STATUS_META = {
  AGREED: { l: 'Rules + AI agree', c: 'ok' }, RULE: { l: 'Rule-based', c: 'info' }, AI_VERIFIED: { l: 'AI · quote verified', c: 'ok' },
  AI_UNVERIFIED: { l: 'AI · not verified', c: 'warn' }, CONFLICT: { l: 'Conflict', c: 'bad' }, DERIVED: { l: 'Derived', c: 'modified' },
  MISSING: { l: 'Not found', c: 'draft' }, USER: { l: 'Edited by you', c: 'posted' },
};

// --------------------------------------------------------------------------- upload
export const NewLeasePage = {
  components: common,
  setup() {
    const settings = ref(null);
    const caps = ref(null);
    const recent = ref([]);
    const mode = ref('rules');
    const consent = ref(false);
    const forceOcr = ref(false);
    const over = ref(false);
    const busy = ref(false);
    const fileInput = ref(null);
    async function loadRecent() { try { recent.value = await get('/api/extractions'); } catch (e) { /* ignore */ } }
    onMounted(async () => {
      try { settings.value = (await get('/api/settings')).settings; } catch (e) { /* ignore */ }
      try { caps.value = await get('/api/system/capabilities'); } catch (e) { /* ignore */ }
      await loadRecent();
      const ai = settings.value?.ai;
      if (ai?.mode === 'local' && ai.local?.model) mode.value = 'local';
    });
    const localOk = computed(() => !!settings.value?.ai?.local?.model);
    const cloudOk = computed(() => !!(settings.value?.ai?.allow_cloud && settings.value?.ai?.claude?.has_key));
    async function send(file) {
      if (!file) return;
      if (mode.value === 'claude' && !consent.value) { toast('Confirm that this agreement may be sent to the Claude API, or choose an offline engine.', 'bad'); return; }
      busy.value = true;
      const fd = new FormData();
      fd.append('file', file);
      fd.append('mode', mode.value);
      fd.append('allow_cloud', mode.value === 'claude' && consent.value ? 'true' : 'false');
      fd.append('force_ocr', forceOcr.value ? 'true' : 'false');
      try {
        const r = await upload('/api/extractions', fd);
        location.hash = '#/extract/' + r.extraction_id;
      } catch (e) { showError(e); } finally { busy.value = false; }
    }
    function onDrop(e) { over.value = false; const f = e.dataTransfer.files[0]; send(f); }
    function onPick(e) { send(e.target.files[0]); e.target.value = ''; }
    const cols = [
      { key: 'id', label: '#', type: 'num' }, { key: 'filename', label: 'Document' }, { key: 'status', label: 'Status' },
      { key: 'engine', label: 'Engine' }, { key: 'missing', label: 'Missing essentials', type: 'num' }, { key: 'flags', label: 'Judgment flags', type: 'num' },
      { key: 'created_at', label: 'Read on', format: (v) => dateTime(v) }, { key: 'lease_id', label: 'Lease' },
      ...(store.can('document.delete') ? [{ key: 'actions', label: 'Delete', sortable: false }] : []),
    ];
    const open = (r) => { location.hash = '#/extract/' + r.id; };
    // Administrator housekeeping: reads that did not create a lease can be deleted; reads behind a lease are its evidence
    const unused = computed(() => recent.value.filter(r => !r.lease_id && r.status !== 'Running'));
    async function removeRead(r) {
      const ok = await confirmDialog('Delete agreement read #' + r.id,
        r.filename + '\n\nThis deletes the read, its uploaded copy and page previews from this PC. The audit trail keeps a record of the deletion. This cannot be undone.',
        { ok: 'Delete', danger: true });
      if (!ok) return;
      try { await del('/api/extractions/' + r.id); toast('Agreement read #' + r.id + ' deleted', 'ok'); await loadRecent(); } catch (e) { showError(e); }
    }
    async function removeUnused() {
      const n = unused.value.length;
      const ok = await confirmDialog('Delete ' + n + ' unused read' + (n === 1 ? '' : 's'),
        'Deletes every agreement read that was not used to create a lease (' + n + '), with the uploaded copies and page previews. Reads that created a lease are kept as its source evidence. The audit trail keeps a record. This cannot be undone.',
        { ok: 'Delete ' + n, danger: true });
      if (!ok) return;
      try { const r = await post('/api/extractions/delete-unused'); toast(r.deleted + ' read' + (r.deleted === 1 ? '' : 's') + ' deleted', 'ok'); await loadRecent(); } catch (e) { showError(e); }
    }
    return { store, settings, caps, recent, mode, consent, forceOcr, over, busy, fileInput, localOk, cloudOk, onDrop, onPick, cols, open,
      unused, removeRead, removeUnused };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>New lease</h1><div class="sub">Upload the agreement and let the reader propose the Ind AS 116 inputs with evidence — or enter the lease manually. Works for leases where your entity is the lessee or the lessor.</div></div>
      <a class="btn" href="#/new/manual"><AppIcon name="square-pen" :size="14"/> Manual entry</a><a class="btn" href="#/imports"><AppIcon name="upload" :size="14"/> Bulk import</a></div>
    <div class="grid side mb">
      <div class="card"><div class="card-head"><AppIcon name="sparkles" :size="16"/><h3>Agreement reader</h3><span class="sub">PDF (text or scanned), images, Word, text · leave-and-licence, lease deeds, equipment & vehicle leases</span></div>
        <div class="card-body">
          <div class="dropzone" :class="{over}" @dragover.prevent="over=true" @dragleave="over=false" @drop.prevent="onDrop" @click="fileInput.click()">
            <AppIcon :name="busy ? 'refresh-cw' : 'upload'" :size="30" :cls="busy ? 'spin' : ''"/>
            <div style="font-size:15px;font-weight:600;margin-top:8px">{{ busy ? 'Uploading…' : 'Drop the lease agreement here, or click to choose' }}</div>
            <div class="small muted mt">Scanned copies are deskewed and OCR'd on this computer. Stamp/seal marks and e-stamp pages are detected.</div>
            <input ref="fileInput" type="file" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.docx,.txt" style="display:none" @change="onPick">
          </div>
          <div class="mt">
            <div class="small text-2 mb-sm"><b>Reading engine</b></div>
            <div class="col" style="gap:6px">
              <label class="check"><input type="radio" value="rules" v-model="mode"> Offline — rules, OCR and computer vision only <span class="badge ok">No data leaves this PC</span></label>
              <label class="check" :style="!localOk ? 'opacity:.55' : ''"><input type="radio" value="local" v-model="mode" :disabled="!localOk"> Offline + local AI model ({{ settings?.ai?.local?.model || 'not configured' }}) <span class="badge ok">No data leaves this PC</span></label>
              <label class="check" :style="!cloudOk ? 'opacity:.55' : ''"><input type="radio" value="claude" v-model="mode" :disabled="!cloudOk"> Claude API (cloud) <span class="badge warn">Sends document text to Anthropic</span></label>
              <div v-if="!cloudOk" class="tiny muted" style="margin-left:22px">Cloud AI is disabled until an administrator allows it and stores an API key (Settings → AI engine).</div>
              <label v-if="mode==='claude'" class="check alert warn" style="margin-left:22px"><input type="checkbox" v-model="consent"> I confirm this agreement may be sent to the Claude API for extraction (client confidentiality considered). This consent is recorded in the audit trail.</label>
              <label class="check"><input type="checkbox" v-model="forceOcr"> Force OCR even if the PDF has a text layer</label>
            </div>
          </div>
        </div></div>
      <div class="card"><div class="card-head"><h3>How the reader works</h3></div><div class="card-body small text-2">
        <ol style="margin:0 0 0 16px;padding:0;line-height:1.7">
          <li>Pages are loaded; scans are deskewed and OCR'd; stamps and e-stamp certificates are detected.</li>
          <li>Rule engine reads Indian lease language (lock-in, licence fee, escalation, deposit, CAM, stamp duty, renewal, restoration…).</li>
          <li>Optional AI reader proposes values with quotes. Every quote is checked against the document text — unverifiable values are flagged, never silently accepted.</li>
          <li>You review each field with its source highlight, answer the judgment questions (lease term, IBR, deposit rate), then create a <b>Draft</b> lease.</li>
        </ol>
        <div class="mt" v-if="caps"><div class="row wrap" style="gap:6px">
          <span class="chip"><AppIcon name="scan-text" :size="12"/> OCR: {{ (caps.ocr_engines || []).join(', ') || 'none' }}</span>
          <span class="chip"><AppIcon name="eye" :size="12"/> Vision: {{ caps.computer_vision }}</span>
          <span class="chip"><AppIcon name="file-text" :size="12"/> PDF: {{ caps.pdf_engine }}</span>
          <span class="chip"><AppIcon name="bot" :size="12"/> Local AI servers: {{ (caps.local_llm_servers || []).length ? caps.local_llm_servers.map(s => s.kind).join(', ') : 'none detected' }}</span>
        </div></div>
      </div></div>
    </div>
    <div class="card"><div class="card-head"><h3>Recent agreement reads</h3></div>
      <DataTable id="extractions" :columns="cols" :rows="recent" clickable @row-click="open" :page-size="10" empty-text="No agreements read yet.">
        <template #cell-status="{ row }"><StatusBadge :status="row.status"/></template>
        <template #cell-lease_id="{ row }"><a v-if="row.lease_id" :href="'#/leases/' + row.lease_id" @click.stop>Lease #{{ row.lease_id }}</a><span v-else class="muted small">Not created</span></template>
        <template #cell-missing="{ row }"><span :class="row.missing ? 'badge bad' : 'muted'">{{ row.missing || '–' }}</span></template>
        <template #cell-actions="{ row }">
          <span v-if="row.lease_id" class="muted" :title="'Kept — source evidence of Lease #' + row.lease_id"><AppIcon name="lock" :size="13"/></span>
          <button v-else-if="row.status !== 'Running'" class="btn sm icon ghost" style="height:20px;width:24px;margin:-2px 0" :title="'Delete read #' + row.id" :aria-label="'Delete read #' + row.id" @click.stop="removeRead(row)"><AppIcon name="trash-2" :size="14"/></button>
        </template>
        <template #toolbar><button v-if="store.can('document.delete') && unused.length" class="btn sm" @click="removeUnused"><AppIcon name="trash-2" :size="13"/> Delete reads not used for a lease ({{ unused.length }})</button></template>
      </DataTable></div>
  </div>`,
};

// --------------------------------------------------------------------------- review
export const ReaderPage = {
  components: common,
  props: { route: Object },
  emits: ['title'],
  setup(props, { emit }) {
    const id = props.route.params.id;
    const x = ref(null);
    const schema = ref([]);
    const page = ref(1);
    const pageMode = ref('image');
    const pageText = ref('');
    const sel = ref(null);
    const edits = ref({});
    const answers = ref({ rc_continue_after_lock_in: null, rc_continue_rationale: '', rc_renewal: null, rc_renewal_rationale: '', rc_purchase: null,
      deposit_market_rate: '', discount_rate: '', discount_rate_source: '', restoration_estimate: '', restoration_rate: '', related_party: null });
    const create = ref({ entity_id: store.entities[0]?.id || '', lease_type: 'STANDARD', cost_centre: '', description: '', role: 'LESSEE' });
    const isLessor = computed(() => create.value.role === 'LESSOR');
    const rtab = ref('fields');
    const busy = ref(false);
    let timer = null;
    async function poll() {
      try {
        x.value = await get('/api/extractions/' + id);
        if (x.value.status === 'Running') { timer = setTimeout(poll, 1500); return; }
        if (x.value.status === 'Completed') {
          const doc = x.value.result.document;
          emit('title', 'Agreement reader — ' + doc.filename);
          if (!doc.page_info?.[0]?.has_preview) pageMode.value = 'text';
          const d = x.value.result.draft || {};
          create.value.description = (d.asset_class || 'Lease') + ' — ' + (d.location || d.description || doc.filename).slice(0, 120);
          if (x.value.result.fields?.variable_rent?.value) create.value.lease_type = 'STANDARD';
          loadText();
        }
      } catch (e) { showError(e); }
    }
    onMounted(async () => {
      try { schema.value = await get('/api/extraction-schema'); } catch (e) { /* ignore */ }
      poll();
    });
    onBeforeUnmount(() => clearTimeout(timer));
    const r = computed(() => x.value?.result || {});
    const fields = computed(() => r.value.fields || {});
    const docId = computed(() => x.value?.document_id);
    const pages = computed(() => r.value.document?.page_info || []);
    const pinfo = computed(() => pages.value.find(p => p.number === page.value) || {});
    const locked = computed(() => !!x.value?.lease_id || !store.can('lease.write'));
    const groups = computed(() => {
      const order = [];
      const by = {};
      for (const f of schema.value.length ? schema.value : Object.values(fields.value).map(v => ({ key: v.key, group: v.group }))) {
        if (!by[f.group]) { by[f.group] = []; order.push(f.group); }
        if (fields.value[f.key]) by[f.group].push({ ...f, ...fields.value[f.key], choices: f.choices || [] });
      }
      return order.map(g => ({ name: g, items: by[g] }));
    });
    const val = (k) => (k in edits.value ? edits.value[k] : fields.value[k]?.value);
    function setVal(k, v) { edits.value = { ...edits.value, [k]: v }; }
    const statusOf = (f) => (f.key in edits.value && String(edits.value[f.key] ?? '') !== String(f.value ?? '')) ? 'USER' : f.status;
    const evidencePages = computed(() => new Set(Object.values(fields.value).filter(f => f.page).map(f => f.page)));
    function select(f) {
      sel.value = f.key;
      if (f.page && f.page !== page.value) { page.value = f.page; loadText(); }
    }
    const boxes = computed(() => {
      const f = sel.value && fields.value[sel.value];
      return f && f.page === page.value ? (f.boxes || []) : [];
    });
    async function loadText() {
      if (!docId.value) return;
      try {
        const res = await fetch('/api/documents/' + docId.value + '/pages/' + page.value + '.txt', { credentials: 'same-origin' });
        pageText.value = res.ok ? await res.text() : '';
      } catch (e) { pageText.value = ''; }
    }
    function goPage(n) { page.value = n; loadText(); }
    const textParts = computed(() => {
      const f = sel.value && fields.value[sel.value];
      const t = pageText.value || '';
      if (!f || !f.quote || f.page !== page.value) return [t, '', ''];
      let i = t.indexOf(f.quote);
      let len = f.quote.length;
      if (i < 0) { const q = f.quote.slice(0, 40); i = t.toLowerCase().indexOf(q.toLowerCase()); len = q.length; }
      if (i < 0) return [t, '', ''];
      return [t.slice(0, i), t.slice(i, i + len), t.slice(i + len)];
    });
    watch(textParts, () => nextTick(() => { const m = document.querySelector('.page-text mark'); if (m) m.scrollIntoView({ block: 'center' }); }));
    watch(boxes, () => nextTick(() => {
      const h = document.querySelector('.page-canvas .hl');
      const c = document.querySelector('.page-canvas');
      if (h && c) c.scrollTo({ top: Math.max(0, h.offsetTop - c.clientHeight / 3), behavior: 'smooth' });
    }));
    const qByKey = computed(() => Object.fromEntries((r.value.questions || []).map(q => [q.key, q])));
    const missing = computed(() => (r.value.missing_essentials || []).filter(k => val(k) === null || val(k) === undefined || val(k) === ''));
    const pendingJudgments = computed(() => ['rc_continue_after_lock_in', 'rc_renewal', 'rc_purchase'].filter(k => qByKey.value[k] && (answers.value[k] === null || answers.value[k] === undefined)));
    async function confirm() {
      if (missing.value.length) { toast('Complete the essential fields first: ' + missing.value.map(k => fields.value[k]?.label || k).join(', '), 'bad'); return; }
      if (pendingJudgments.value.length) {
        const ok = await confirmDialog('Judgments not yet answered', 'Some lease-term judgments are unanswered. The lease will be created, but calculation stays blocked until each option is assessed ("Accounting judgment required"). Continue?', { ok: 'Create draft lease' });
        if (!ok) return;
      }
      if (!isLessor.value && create.value.lease_type === 'STANDARD' && !answers.value.discount_rate) {
        const ok = await confirmDialog('Discount rate missing', 'No IBR entered. The lease can be created, but it cannot be measured until a discount rate is recorded (Ind AS 116.26). Continue?', { ok: 'Create draft lease' });
        if (!ok) return;
      }
      if (isLessor.value && !val('lessee_name')) {
        const ok = await confirmDialog('Lessee not identified', 'Your entity is the lessor, so the counterparty is the lessee (tenant / licensee), which the reader did not find. The lease will be created without a counterparty — add it on the Contract tab. Continue?', { ok: 'Create draft lease' });
        if (!ok) return;
      }
      busy.value = true;
      try {
        const payload = { fields: edits.value, answers: answers.value, ...create.value };
        const lease = await post('/api/extractions/' + id + '/confirm', payload);
        toast('Draft ' + (isLessor.value ? 'lessor ' : '') + 'lease ' + lease.lease_code + ' created from the agreement', 'ok');
        location.hash = '#/leases/' + lease.id + (isLessor.value ? '?tab=classification' : '');
      } catch (e) { showError(e); } finally { busy.value = false; }
    }
    function adopt(f, alt) { setVal(f.key, alt.value); }
    const fmtVal = (f) => {
      const v = val(f.key);
      if (v === null || v === undefined || v === '') return '—';
      if (f.type === 'date') return date(v);
      if (f.type === 'amount') return money(v);
      if (f.type === 'bool') return v === true || v === 'true' ? 'Yes' : 'No';
      return String(v);
    };
    const confCls = (c) => c >= 0.8 ? '' : c >= 0.5 ? 'mid' : 'low';
    return { store, id, x, r, fields, groups, page, pageMode, pageText, pages, pinfo, docId, sel, select, boxes, goPage, textParts, evidencePages, val, setVal,
      statusOf, STATUS_META, answers, qByKey, create, confirm, busy, missing, rtab, locked, adopt, fmtVal, confCls, money, date, num, titleCase, isLessor };
  },
  template: `
  <div>
    <div v-if="!x || x.status==='Running'" class="card"><div class="card-body" style="padding:40px;text-align:center">
      <AppIcon name="scan-text" :size="34"/><h2 class="mt">Reading the agreement…</h2>
      <div class="small muted mt">{{ x?.result?.progress || 'Queued' }}</div><div class="progress mt" style="max-width:360px;margin:16px auto 0"><i></i></div>
      <div class="small muted mt">Scanned agreements can take a minute per few pages on this computer (OCR runs locally).</div></div></div>
    <div v-else-if="x.status==='Failed'" class="alert bad"><AppIcon name="circle-x"/><div><b>The document could not be read.</b><div class="small mono mt">{{ x.result?.error }}</div></div></div>
    <template v-else>
      <div class="page-head">
        <div class="grow"><h1>{{ r.document.filename }}</h1>
          <div class="sub">{{ r.document.pages }} page(s) · {{ titleCase(r.document.kind) }}<span v-if="r.document.ocr_used"> · OCR: {{ r.document.ocr_engine }}</span> · engine: {{ x.engine }}<span v-if="x.model"> ({{ x.model }})</span> · read in {{ r.timings?.total_s }} s</div></div>
        <a v-if="x.lease_id" class="btn primary" :href="'#/leases/' + x.lease_id"><AppIcon name="arrow-right" :size="14"/> Open lease #{{ x.lease_id }}</a>
      </div>
      <div v-if="r.warnings && r.warnings.length" class="alert warn mb"><AppIcon name="triangle-alert"/><div><div v-for="(w, i) in r.warnings" :key="i">{{ w }}</div></div></div>
      <div v-if="missing.length && !x.lease_id" class="alert bad mb"><AppIcon name="circle-alert"/><div><b>Essential inputs not found:</b> {{ missing.map(k => fields[k]?.label || k).join(', ') }} — enter them from the agreement before creating the lease. Nothing is assumed.</div></div>
      <div class="reader">
        <div class="page-viewer card">
          <div class="card-head"><div class="page-tabs" style="margin:0">
            <button v-for="p in pages" :key="p.number" :class="{on: p.number===page, has: evidencePages.has(p.number)}" @click="goPage(p.number)" :title="p.page_type + ' · ' + p.source">{{ p.number }}</button></div>
            <div class="spacer"></div>
            <div class="pill-tabs"><button :class="{on: pageMode==='image'}" :disabled="!pinfo.has_preview" @click="pageMode='image'">Page</button><button :class="{on: pageMode==='text'}" @click="pageMode='text'">Text</button></div></div>
          <div class="small muted" style="padding:6px 12px">Page {{ page }} · {{ titleCase(pinfo.page_type || '') }} · {{ pinfo.source === 'ocr' ? 'OCR (' + pinfo.ocr_engine + ')' : pinfo.source === 'pdf-text' ? 'PDF text layer' : titleCase(pinfo.source || '') }}<span v-if="pinfo.vision && Math.abs(pinfo.vision.skew_angle) >= 0.1"> · deskewed {{ num(pinfo.vision.skew_angle, 1) }}°</span><span v-if="pinfo.vision && pinfo.vision.stamps && pinfo.vision.stamps.length"> · {{ pinfo.vision.stamps.length }} stamp/seal mark(s)</span></div>
          <div v-if="pageMode==='image' && pinfo.has_preview" class="page-canvas">
            <div class="page-inner">
              <img :src="'/api/documents/' + docId + '/pages/' + page + '.png'" alt="Agreement page">
              <div v-for="(b, i) in boxes" :key="i" class="hl" :style="{left: (b[0]*100)+'%', top: (b[1]*100)+'%', width: ((b[2]-b[0])*100)+'%', height: ((b[3]-b[1])*100)+'%'}"></div>
            </div>
          </div>
          <div v-else class="page-text">{{ textParts[0] }}<mark>{{ textParts[1] }}</mark>{{ textParts[2] }}</div>
        </div>
        <div class="card">
          <div class="card-body" style="padding-bottom:0"><Tabs :tabs="[{key:'fields',label:'Extracted fields'},{key:'judgments',label:'Judgments',count:(r.questions||[]).length},{key:'flags',label:'Flags',count:(r.flags||[]).length},{key:'create',label:'Create lease'}]" v-model="rtab"/></div>
          <div v-if="rtab==='fields'">
            <div class="small muted" style="padding:0 12px 8px">Click a field to see its source on the page. Every value is editable; your edits are logged.</div>
            <template v-for="g in groups" :key="g.name">
              <div class="group-title">{{ g.name }}</div>
              <div v-for="f in g.items" :key="f.key" class="field-row" :class="{sel: sel===f.key}" @click="select(f)">
                <div><div class="lbl"><span :class="{req: f.essential}">{{ f.label }}</span></div>
                  <div class="meta"><span class="badge" :class="STATUS_META[statusOf(f)]?.c">{{ STATUS_META[statusOf(f)]?.l || statusOf(f) }}</span>
                    <span class="conf" :class="confCls(f.confidence)" v-if="f.confidence" :title="'Confidence ' + Math.round(f.confidence*100) + '%'"><i :style="{width: Math.round(f.confidence*100) + '%'}"></i></span>
                    <span class="tiny muted" v-if="f.page">p.{{ f.page }}</span><span class="tiny muted" v-if="f.ind_as_ref">{{ f.ind_as_ref }}</span></div></div>
                <div>
                  <template v-if="locked"><div style="padding-top:4px">{{ fmtVal(f) }}</div></template>
                  <select v-else-if="f.type==='bool'" :value="val(f.key)===true || val(f.key)==='true' ? 'true' : val(f.key)===false || val(f.key)==='false' ? 'false' : ''" @change="setVal(f.key, $event.target.value==='' ? null : $event.target.value==='true')" @focus="select(f)">
                    <option value="">—</option><option value="true">Yes</option><option value="false">No</option></select>
                  <select v-else-if="f.type==='choice' && f.choices.length" :value="val(f.key) ?? ''" @change="setVal(f.key, $event.target.value || null)" @focus="select(f)">
                    <option value="">—</option><option v-for="c in f.choices" :key="c" :value="c">{{ titleCase(c) }}</option></select>
                  <input v-else-if="f.type==='date'" type="date" :value="val(f.key) || ''" @input="setVal(f.key, $event.target.value || null)" @focus="select(f)">
                  <input v-else :class="['amount','percent','int','number'].includes(f.type) ? 'num' : ''" :value="val(f.key) ?? ''" @input="setVal(f.key, $event.target.value === '' ? null : $event.target.value)" @focus="select(f)">
                  <div class="tiny muted" v-if="f.type==='amount' && val(f.key)" style="margin-top:2px">{{ money(val(f.key)) }}</div>
                  <div class="quote" v-if="f.quote">“{{ f.quote.length > 260 ? f.quote.slice(0, 260) + '…' : f.quote }}”</div>
                  <div class="tiny muted" v-if="f.note" style="margin-top:4px">{{ f.note }}</div>
                  <div class="row wrap" v-if="f.alternatives && f.alternatives.length && !locked" style="gap:4px;margin-top:5px"><span class="tiny muted">Alternatives:</span>
                    <button v-for="(a, i) in f.alternatives" :key="i" class="chip" style="cursor:pointer" @click="adopt(f, a)" :title="a.quote || ''">{{ a.value }} <span class="muted">({{ a.source || a.method }})</span></button></div>
                </div>
              </div>
            </template>
          </div>
          <div v-if="rtab==='judgments'" class="card-body col" style="gap:14px">
            <div class="small text-2">These are accounting judgments — the reader never answers them for you. Answers are stored with the lease and shown in the audit trail.</div>
            <div v-if="qByKey.rc_continue_after_lock_in" class="judgment"><div class="t">{{ qByKey.rc_continue_after_lock_in.question }}</div><div class="d">{{ qByKey.rc_continue_after_lock_in.guidance }}</div>
              <div class="mt"><TriState v-model="answers.rc_continue_after_lock_in" yes="Yes — full term" no="No — lock-in only" :disabled="locked"/></div>
              <textarea class="mt" v-model="answers.rc_continue_rationale" placeholder="Rationale (B37 factors)" :disabled="locked"></textarea><div class="r">{{ qByKey.rc_continue_after_lock_in.ref }}</div></div>
            <div v-if="qByKey.rc_renewal" class="judgment"><div class="t">{{ qByKey.rc_renewal.question }}</div><div class="d">{{ qByKey.rc_renewal.guidance }}</div>
              <div class="mt"><TriState v-model="answers.rc_renewal" :disabled="locked"/></div><textarea class="mt" v-model="answers.rc_renewal_rationale" placeholder="Rationale" :disabled="locked"></textarea><div class="r">{{ qByKey.rc_renewal.ref }}</div></div>
            <div v-if="qByKey.rc_purchase" class="judgment"><div class="t">{{ qByKey.rc_purchase.question }}</div><div class="d">{{ qByKey.rc_purchase.guidance }}</div>
              <div class="mt"><TriState v-model="answers.rc_purchase" :disabled="locked"/></div><div class="r">{{ qByKey.rc_purchase.ref }}</div></div>
            <div class="judgment" v-if="!isLessor"><div class="t">{{ qByKey.discount_rate?.question || 'Incremental borrowing rate (IBR)' }}</div><div class="d">{{ qByKey.discount_rate?.guidance }}</div>
              <div class="form-grid mt"><label class="field">IBR % p.a.<input class="num" v-model="answers.discount_rate" :disabled="locked"></label><label class="field span-2">Source / methodology<input v-model="answers.discount_rate_source" :disabled="locked"></label></div><div class="r">Ind AS 116.26</div></div>
            <div class="judgment info" v-else><div class="t">Your entity is the lessor — no discount rate is needed here</div><div class="d">After creating the lease, complete the classification inputs (fair value, carrying amount and economic life of the asset; unguaranteed residual value for a finance lease) on the lease's Classification tab (Ind AS 116.61–66).</div><div class="r">Ind AS 116.61–70</div></div>
            <div v-if="qByKey.deposit_market_rate" class="judgment"><div class="t">{{ isLessor ? 'Market interest rate for the deposit received (Ind AS 109)' : qByKey.deposit_market_rate.question }}</div><div class="d">{{ isLessor ? 'The interest-free deposit received is a financial liability measured at fair value; the excess received is a lease payment received in advance.' : qByKey.deposit_market_rate.guidance }}</div>
              <div class="form-grid mt"><label class="field">Market rate % p.a.<input class="num" v-model="answers.deposit_market_rate" :disabled="locked" :placeholder="isLessor ? 'required' : 'defaults to the IBR'"></label></div><div class="r">{{ qByKey.deposit_market_rate.ref }}</div></div>
            <div v-if="qByKey.restoration_estimate && !isLessor" class="judgment"><div class="t">{{ qByKey.restoration_estimate.question }}</div><div class="d">{{ qByKey.restoration_estimate.guidance }}</div>
              <div class="form-grid mt"><label class="field">Estimated cost<input class="num" v-model="answers.restoration_estimate" :disabled="locked"></label><label class="field">Discount rate %<input class="num" v-model="answers.restoration_rate" :disabled="locked"></label></div><div class="r">{{ qByKey.restoration_estimate.ref }}</div></div>
            <div class="judgment info"><div class="t">{{ isLessor ? 'Is the lessee a related party?' : (qByKey.related_party?.question || 'Is the lessor a related party?') }}</div><div class="mt"><TriState v-model="answers.related_party" :disabled="locked"/></div><div class="r">Ind AS 24</div></div>
          </div>
          <div v-if="rtab==='flags'" class="card-body"><FlagList :flags="r.flags" empty="No judgment flags raised."/></div>
          <div v-if="rtab==='create'" class="card-body">
            <div v-if="x.lease_id" class="alert ok"><AppIcon name="circle-check"/><div class="grow">Lease #{{ x.lease_id }} was created from this agreement.</div><a class="btn sm" :href="'#/leases/' + x.lease_id">Open</a></div>
            <template v-else>
              <div class="judgment mb" style="margin-bottom:12px"><div class="t">Our entity in this agreement is the</div>
                <div class="row mt" style="gap:16px"><label class="check"><input type="radio" value="LESSEE" v-model="create.role"> Lessee / licensee — we use the asset</label>
                  <label class="check"><input type="radio" value="LESSOR" v-model="create.role"> Lessor / licensor — we let out the asset</label></div>
                <div class="d mt" v-if="isLessor">Counterparty: <b>{{ val('lessee_name') || 'lessee not found — add later' }}</b>. The lease is classified as finance or operating after you enter the classification inputs.</div>
                <div class="d mt" v-else>Counterparty: <b>{{ val('lessor_name') || 'lessor not found — add later' }}</b>.</div></div>
              <div class="form-grid">
                <label class="field span-2">Lease description<input v-model="create.description"></label>
                <label class="field">Entity<select v-model="create.entity_id"><option v-for="e in store.entities" :key="e.id" :value="e.id">{{ e.code }} — {{ e.name }}</option></select></label>
                <label class="field" v-if="!isLessor">Accounting model<select v-model="create.lease_type"><option value="STANDARD">Capitalise (ROU + liability)</option><option value="SHORT_TERM">Short-term exemption</option><option value="LOW_VALUE">Low-value exemption</option></select></label>
                <div class="field" v-else><span>Accounting model</span><div class="small text-2" style="padding-top:6px">Lessor lease — finance / operating (paras 61–66)</div></div>
                <label class="field">Cost centre<input v-model="create.cost_centre"></label>
              </div>
              <h4 class="mt mb-sm">Proposed draft</h4>
              <div class="stat-line"><span>Commencement → contract end</span><span>{{ date(val('commencement_date')) }} → {{ date(r.draft?.contract_end) }}</span></div>
              <div class="stat-line"><span>Rent per period · frequency · timing</span><span>{{ money(val('rent_amount')) }} · {{ titleCase(val('rent_frequency') || 'MONTHLY') }} · {{ titleCase(val('payment_timing') || 'ADVANCE') }}</span></div>
              <div class="stat-line"><span>Escalation</span><span>{{ val('escalation_pct') ? val('escalation_pct') + '% every ' + (val('escalation_every_months') || 12) + ' months' : 'None found' }}</span></div>
              <div class="stat-line"><span>{{ isLessor ? 'Security deposit (received)' : 'Security deposit' }}</span><span>{{ money(val('deposit_amount')) }}</span></div>
              <div class="stat-line" v-if="!isLessor"><span>Initial direct costs (stamp duty, brokerage)</span><span>{{ money(val('stamp_duty_amount')) }} · {{ money(val('brokerage_amount')) }}</span></div>
              <div class="stat-line" v-else><span>Lessor initial direct costs</span><span>{{ val('stamp_duty_borne_by') === 'LESSOR' ? money(val('stamp_duty_amount')) + ' (stamp duty borne by the lessor)' : 'Enter on the Classification tab' }}</span></div>
              <div class="stat-line" v-if="!isLessor"><span>IBR</span><span>{{ answers.discount_rate ? answers.discount_rate + '%' : 'Not entered' }}</span></div>
              <div v-if="r.draft?.assumptions?.length" class="alert warn mt"><AppIcon name="triangle-alert"/><div><b>Assumptions to confirm:</b><ul style="margin:4px 0 0 16px;padding:0"><li v-for="(a, i) in r.draft.assumptions" :key="i">{{ a }}</li></ul></div></div>
              <div class="row mt" style="justify-content:flex-end"><button class="btn primary" :disabled="busy || locked" @click="confirm"><AppIcon name="file-check" :size="14"/> Create draft lease</button></div>
              <div class="tiny muted mt">The lease is created as <b>Draft</b> with a generated payment schedule, options, deposit and initial direct costs. Review, calculate and submit it for approval.</div>
            </template>
          </div>
        </div>
      </div>
    </template>
  </div>`,
};

// --------------------------------------------------------------------------- manual wizard
export const ManualWizardPage = {
  components: { ...common, PaymentTermsForm },
  setup() {
    const step = ref(0);
    const b = ref({ description: '', entity_id: store.entities[0]?.id || '', asset_class_id: store.assetClasses[0]?.id || '', counterparty_id: null,
      asset_description: '', location: '', cost_centre: '', contract_number: '', contract_date: '', currency: store.company?.functional_currency || 'INR',
      lease_type: 'STANDARD', commencement_date: '', contract_end: '', tenure: '', discount_rate_pct: '', rate_basis: 'IBR', rate_source: '', discount_rate_id: null,
      asset_value_when_new: '', role: 'LESSEE' });
    const isLessor = computed(() => b.value.role === 'LESSOR');
    const steps = computed(() => isLessor.value ? ['Basics', 'Term & options', 'Lease payments receivable', 'Classification', 'Deposit received', 'Review']
      : ['Basics', 'Term & options', 'Payments', 'Discount rate', 'ROU inputs', 'Review']);
    const ld = ref({ fair_value: '', carrying_amount: '', economic_life_months: '', unguaranteed_residual: '', lessor_idc: '', implicit_rate_pct: '',
      transfers_ownership: false, bargain_purchase_option: false, specialised_asset: false, manufacturer_dealer: false,
      classification_override: '', override_rationale: '' });
    watch(isLessor, (v) => { if (v) b.value.lease_type = 'STANDARD'; });
    const master = ref({ counterparties: [] });
    const options = ref([]);
    const terms = ref(defaultTerms());
    const idc = ref([]);
    const dep = ref({ amount: '', market_rate_pct: '', refund_date: '' });
    const rest = ref({ estimated_cost: '', discount_rate_pct: '' });
    const suggestion = ref(null);
    const busy = ref(false);
    onMounted(async () => { try { master.value = await get('/api/master'); } catch (e) { /* ignore */ } });
    watch(() => [b.value.commencement_date, b.value.tenure], ([c, t]) => {
      if (c && t && Number(t) > 0) b.value.contract_end = addDays(addMonths(c, Number(t)), -1);
    });
    watch(() => [b.value.commencement_date, b.value.contract_end], ([c, e]) => {
      terms.value.start_date = c; terms.value.end_date = e;
      if (e && !dep.value.refund_date) dep.value.refund_date = addDays(e, 1);
    });
    function addOption(kind) {
      const e = b.value.contract_end;
      options.value.push({ kind, holder: 'LESSEE', exercise_date: kind === 'EXTENSION' && e ? addDays(e, 1) : '', extension_end_date: '', price: '',
        renewal_escalation_pct: '', reasonably_certain: null, rationale: '', description: '' });
    }
    async function addCounterparty() {
      const name = await confirmDialog('New counterparty', isLessor.value ? 'Legal name of the lessee (tenant / licensee).' : 'Legal name of the lessor.', { input: 'Name', ok: 'Add' });
      if (!name) return;
      try { const r = await post('/api/master/counterparties', { name }); master.value = await get('/api/master'); b.value.counterparty_id = r.id; } catch (e) { showError(e); }
    }
    async function lookup() {
      const c = b.value.commencement_date, e = b.value.contract_end;
      const months = c && e ? Math.round((new Date(e) - new Date(c)) / (86400000 * 30.4375)) : 0;
      try { suggestion.value = await post('/api/discount-rates/lookup', { currency: b.value.currency, tenor_months: months, date: c, entity_id: b.value.entity_id }); }
      catch (err) { showError(err); }
    }
    function applyRate() {
      const s = suggestion.value;
      b.value.discount_rate_pct = s.rate; b.value.discount_rate_id = s.id; b.value.rate_source = s.message;
    }
    const capitalise = computed(() => b.value.lease_type === 'STANDARD' && !isLessor.value);
    function validate(i) {
      const v = b.value;
      if (i === 0 && !v.description) return 'Enter a description.';
      if (i === 1 && (!v.commencement_date || !v.contract_end)) return 'Commencement and contract end dates are required.';
      if (i === 1 && v.contract_end < v.commencement_date) return 'Contract end precedes commencement.';
      if (i === 2 && (terms.value.amount === '' || !terms.value.start_date || !terms.value.end_date)) return 'Enter the payment amount and period.';
      if (i === 3 && capitalise.value && !v.discount_rate_pct) return 'A discount rate is required to measure the lease (Ind AS 116.26).';
      if (i === 3 && isLessor.value) {
        const l = ld.value;
        if (l.classification_override && !l.override_rationale.trim()) return 'Document the rationale for the recorded classification (Ind AS 116.62–65).';
        if (!l.classification_override && (!l.fair_value || !l.economic_life_months) && !l.transfers_ownership && !l.bargain_purchase_option && !l.specialised_asset)
          return 'Enter the fair value and economic life of the asset (for the PV and term tests), or record the classification with a rationale.';
      }
      if (i === 4 && isLessor.value && dep.value.amount && !dep.value.market_rate_pct) return 'A market interest rate is required to measure the interest-free deposit received (Ind AS 109).';
      return null;
    }
    function next() { const e = validate(step.value); if (e) { toast(e, 'bad'); return; } step.value++; }
    function goto(i) { for (let k = 0; k < i; k++) { const e = validate(k); if (e) { step.value = k; toast(e, 'bad'); return; } } step.value = i; }
    async function create() {
      for (let k = 0; k < 5; k++) { const e = validate(k); if (e) { step.value = k; toast(e, 'bad'); return; } }
      busy.value = true;
      const v = b.value;
      try {
        const lessorDetails = isLessor.value ? Object.fromEntries(Object.entries(ld.value).filter(([, x]) => x !== '' && x !== false)) : null;
        const lease = await post('/api/leases', { description: v.description, entity_id: v.entity_id, asset_class_id: v.asset_class_id, counterparty_id: v.counterparty_id,
          asset_description: v.asset_description, location: v.location, cost_centre: v.cost_centre, contract_number: v.contract_number, contract_date: v.contract_date,
          currency: (v.currency || 'INR').toUpperCase(), lease_type: v.lease_type, commencement_date: v.commencement_date, availability_date: v.commencement_date,
          contract_end: v.contract_end, role: v.role, lessor_details: lessorDetails,
          ...(isLessor.value ? {} : { discount_rate_pct: v.discount_rate_pct, rate_basis: v.rate_basis, rate_source: v.rate_source, discount_rate_id: v.discount_rate_id }) });
        const lid = lease.id;
        if (options.value.length) await put('/api/leases/' + lid + '/options', options.value);
        await put('/api/leases/' + lid + '/payment-terms', terms.value);
        const costs = idc.value.filter(c => c.amount);
        if (costs.length && !isLessor.value) await put('/api/leases/' + lid + '/costs', costs);
        if (dep.value.amount) await put('/api/leases/' + lid + '/deposit', { ...dep.value, payment_date: v.commencement_date, treat_difference_as_prepaid_rent: true });
        if (rest.value.estimated_cost && !isLessor.value) await put('/api/leases/' + lid + '/restoration', { ...rest.value, settlement_date: addDays(v.contract_end, 1), recognition_date: v.commencement_date });
        if (v.lease_type !== 'STANDARD' && !isLessor.value) await put('/api/leases/' + lid + '/assessment', { exemption: v.lease_type, asset_value_when_new: v.asset_value_when_new || null, benefits_on_own: true, not_highly_dependent: true });
        try { await post('/api/leases/' + lid + '/calculate'); toast('Lease ' + lease.lease_code + ' created and calculated (Draft)', 'ok'); }
        catch (e) { toast('Lease ' + lease.lease_code + ' created. Calculation pending: ' + e.message, 'bad', 8000); }
        location.hash = '#/leases/' + lid;
      } catch (e) { showError(e); } finally { busy.value = false; }
    }
    return { store, step, steps, master, b, options, terms, idc, dep, rest, suggestion, busy, addOption, addCounterparty, lookup, applyRate, next, goto, create,
      capitalise, money, date, num, CURRENCIES, isLessor, ld };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>New lease — manual entry</h1><div class="sub">Creates a Draft lease — as lessee or as lessor. Judgments are explicit; nothing is defaulted silently.</div></div><a class="btn" href="#/new"><AppIcon name="sparkles" :size="14"/> Use the agreement reader instead</a></div>
    <div class="stepper"><div v-for="(s, i) in steps" :key="s" class="step" :class="{on: i===step, done: i<step}" @click="goto(i)"><span class="n">{{ i < step ? '✓' : i + 1 }}</span>{{ s }}</div></div>
    <div class="card"><div class="card-body">
      <div v-if="step===0" class="form-grid">
        <div class="field span-all"><span class="req">Our entity is the</span>
          <div class="row" style="gap:18px;padding-top:4px"><label class="check"><input type="radio" value="LESSEE" v-model="b.role"> Lessee — we use the asset (ROU asset and lease liability)</label>
            <label class="check"><input type="radio" value="LESSOR" v-model="b.role"> Lessor — we let out the asset (finance / operating lease)</label></div></div>
        <label class="field span-2"><span class="req">Description</span><input v-model="b.description" placeholder="e.g. Office — 4th floor, Tower B, Andheri (E), Mumbai"></label>
        <label class="field">Entity<select v-model="b.entity_id"><option v-for="e in store.entities" :key="e.id" :value="e.id">{{ e.code }} — {{ e.name }}</option></select></label>
        <label class="field">Asset class<select v-model="b.asset_class_id"><option v-for="a in store.assetClasses" :key="a.id" :value="a.id">{{ a.name }}</option></select></label>
        <label class="field span-2">{{ isLessor ? 'Lessee (tenant / licensee)' : 'Lessor' }}<div class="row"><select v-model="b.counterparty_id"><option :value="null">—</option><option v-for="c in master.counterparties" :key="c.id" :value="c.id">{{ c.name }}</option></select><button class="btn sm" @click="addCounterparty"><AppIcon name="plus" :size="13"/></button></div></label>
        <label class="field span-2">Underlying asset<input v-model="b.asset_description"></label>
        <label class="field span-2">Location<input v-model="b.location"></label>
        <label class="field">Cost centre<input v-model="b.cost_centre"></label>
        <label class="field">Agreement no.<input v-model="b.contract_number"></label>
        <label class="field">Agreement date<input type="date" v-model="b.contract_date"></label>
        <label class="field">Currency<input v-model="b.currency" list="ccy-list2" maxlength="3"><datalist id="ccy-list2"><option v-for="c in CURRENCIES" :key="c" :value="c"></option></datalist></label>
        <label class="field" v-if="!isLessor">Accounting model<select v-model="b.lease_type"><option value="STANDARD">Capitalise (ROU + liability)</option><option value="SHORT_TERM">Short-term exemption</option><option value="LOW_VALUE">Low-value exemption</option></select></label>
        <div class="field" v-else><span>Accounting model</span><div class="small text-2" style="padding-top:6px">Lessor lease — classified as finance or operating (paras 61–66); exemptions apply to lessees only</div></div>
        <label class="field" v-if="b.lease_type==='LOW_VALUE' && !isLessor">Asset value when new<input class="num" v-model="b.asset_value_when_new"></label>
      </div>
      <div v-if="step===1">
        <div class="form-grid">
          <label class="field"><span class="req">Commencement date</span><input type="date" v-model="b.commencement_date"><span class="hint">When the lessor makes the asset available</span></label>
          <label class="field">Contract term (months)<input class="num" v-model="b.tenure" placeholder="e.g. 60"><span class="hint">Fills the contract end</span></label>
          <label class="field"><span class="req">Contract end (non-extended)</span><input type="date" v-model="b.contract_end"></label>
        </div>
        <div class="row mt"><h4 class="grow">Options</h4><button class="btn sm" @click="addOption('EXTENSION')"><AppIcon name="plus" :size="13"/> Extension</button><button class="btn sm" @click="addOption('TERMINATION')"><AppIcon name="plus" :size="13"/> Termination / lock-in exit</button><button class="btn sm" @click="addOption('PURCHASE')"><AppIcon name="plus" :size="13"/> Purchase</button></div>
        <div v-if="!options.length" class="small muted mt">No options. For a leave-and-licence with a lock-in shorter than the term, add a termination option at the end of the lock-in.</div>
        <div v-for="(o, i) in options" :key="i" class="judgment mt">
          <div class="form-grid">
            <label class="field">Option<select v-model="o.kind"><option value="EXTENSION">Extension</option><option value="TERMINATION">Termination</option><option value="PURCHASE">Purchase</option></select></label>
            <label class="field">Held by<select v-model="o.holder"><option value="LESSEE">Lessee</option><option value="LESSOR">Lessor</option><option value="BOTH">Both</option></select></label>
            <label class="field">{{ o.kind==='EXTENSION' ? 'Extension starts' : o.kind==='TERMINATION' ? 'Earliest exit (last day)' : 'Exercise date' }}<input type="date" v-model="o.exercise_date"></label>
            <label class="field" v-if="o.kind==='EXTENSION'">Extension ends<input type="date" v-model="o.extension_end_date"></label>
            <label class="field" v-if="o.kind==='EXTENSION'">Rent uplift %<input class="num" v-model="o.renewal_escalation_pct"></label>
            <label class="field" v-if="o.kind!=='EXTENSION'">{{ o.kind==='PURCHASE' ? 'Price' : 'Penalty' }}<input class="num" v-model="o.price"></label>
            <div class="field span-2"><span>{{ o.kind==='TERMINATION' ? 'Reasonably certain NOT to terminate?' : o.kind==='PURCHASE' ? 'Reasonably certain to purchase?' : 'Reasonably certain to extend?' }}</span><TriState v-model="o.reasonably_certain"/></div>
            <label class="field span-2">Rationale<input v-model="o.rationale"></label>
          </div>
          <div class="row" style="justify-content:flex-end"><button class="btn sm danger" @click="options.splice(i,1)">Remove</button></div>
        </div>
      </div>
      <div v-if="step===2"><div v-if="isLessor" class="alert info mb"><AppIcon name="info"/><div class="small">Rent receivable from the lessee. Enter CAM / service charges as the non-lease amount — a lessor always separates them (para 17; revenue under Ind AS 115).</div></div><PaymentTermsForm v-model="terms" editable/></div>
      <div v-if="step===3 && isLessor" class="col" style="gap:12px">
        <div class="small text-2">Classification is judged at inception from the indicators in Ind AS 116.63–64. Enter the fair value and economic life of the asset so the PV test (63(d)) and the term test (63(c)) can be performed; the unguaranteed residual value lets the rate implicit in the lease be solved (needed to measure a finance lease).</div>
        <div class="form-grid">
          <label class="field">Fair value of the asset (at inception)<input class="num" v-model="ld.fair_value"></label>
          <label class="field">Carrying amount of the asset<input class="num" v-model="ld.carrying_amount"><span class="hint">Derecognised if a finance lease</span></label>
          <label class="field">Economic life (months)<input class="num" v-model="ld.economic_life_months"></label>
          <label class="field">Unguaranteed residual value<input class="num" v-model="ld.unguaranteed_residual"></label>
          <label class="field">Rate implicit in the lease % (blank = solve)<input class="num" v-model="ld.implicit_rate_pct"></label>
          <label class="field">Lessor initial direct costs<input class="num" v-model="ld.lessor_idc"><span class="hint">Brokerage / stamp duty borne by you</span></label>
          <label class="check"><input type="checkbox" v-model="ld.transfers_ownership"> 63(a) Ownership transfers to the lessee</label>
          <label class="check"><input type="checkbox" v-model="ld.bargain_purchase_option"> 63(b) Purchase option well below fair value</label>
          <label class="check"><input type="checkbox" v-model="ld.specialised_asset"> 63(e) Specialised asset</label>
          <label class="check"><input type="checkbox" v-model="ld.manufacturer_dealer"> Manufacturer / dealer lessor</label>
          <label class="field">Record the classification (optional)<select v-model="ld.classification_override"><option value="">Conclude from the indicators</option><option value="FINANCE">Finance lease</option><option value="OPERATING">Operating lease</option></select></label>
          <label class="field span-2" v-if="ld.classification_override">Rationale (required)<input v-model="ld.override_rationale"></label>
        </div>
      </div>
      <div v-if="step===3 && !isLessor">
        <div v-if="!capitalise" class="alert info mb"><AppIcon name="info"/><div>Exempt leases are expensed straight-line — no discount rate needed.</div></div>
        <div class="form-grid">
          <label class="field"><span :class="{req: capitalise}">Discount rate % p.a.</span><input class="num" v-model="b.discount_rate_pct"></label>
          <label class="field">Basis<select v-model="b.rate_basis"><option value="IBR">Incremental borrowing rate</option><option value="IMPLICIT">Rate implicit in the lease</option></select></label>
          <label class="field span-2">Source / methodology<input v-model="b.rate_source"></label>
        </div>
        <div class="row mt"><button class="btn sm" @click="lookup"><AppIcon name="search" :size="13"/> Look up approved IBR table</button></div>
        <div v-if="suggestion" class="alert mt" :class="suggestion.rate ? 'ok' : 'warn'"><AppIcon :name="suggestion.rate ? 'circle-check' : 'triangle-alert'"/><div class="grow">{{ suggestion.message }}</div><button v-if="suggestion.rate" class="btn sm" @click="applyRate">Apply</button></div>
      </div>
      <div v-if="step===4 && isLessor" class="col" style="gap:12px">
        <div class="small text-2">Interest-free security deposit received from the lessee: a financial liability measured at fair value (Ind AS 109); the excess received over fair value is a lease payment received in advance.</div>
        <div class="form-grid"><label class="field">Security deposit received<input class="num" v-model="dep.amount"></label><label class="field">Market rate % (Ind AS 109)<input class="num" v-model="dep.market_rate_pct"></label><label class="field">Refund date<input type="date" v-model="dep.refund_date"></label></div>
      </div>
      <div v-if="step===4 && !isLessor" class="col" style="gap:14px">
        <div><div class="row"><h4 class="grow">Initial direct costs / incentives</h4><button class="btn sm" @click="idc.push({kind:'IDC', date: b.commencement_date, amount:'', description:'Stamp duty & registration'})"><AppIcon name="plus" :size="13"/> Add</button></div>
          <table class="t compact mt" v-if="idc.length"><thead><tr><th>Type</th><th class="num">Amount</th><th>Description</th><th></th></tr></thead><tbody>
            <tr v-for="(c, i) in idc" :key="i"><td><select v-model="c.kind"><option value="IDC">Initial direct cost — 24(c)</option><option value="INCENTIVE">Incentive received — 24(b)</option><option value="PREPAID">Prepayment — 24(b)</option></select></td>
              <td><input class="num" v-model="c.amount"></td><td><input v-model="c.description"></td><td><button class="btn sm icon ghost" @click="idc.splice(i,1)"><AppIcon name="trash-2" :size="13"/></button></td></tr></tbody></table></div>
        <div class="form-grid"><label class="field">Security deposit paid<input class="num" v-model="dep.amount"></label><label class="field">Market rate % (Ind AS 109)<input class="num" v-model="dep.market_rate_pct"></label><label class="field">Refund date<input type="date" v-model="dep.refund_date"></label></div>
        <div class="form-grid"><label class="field">Restoration cost estimate<input class="num" v-model="rest.estimated_cost"></label><label class="field">Provision discount rate %<input class="num" v-model="rest.discount_rate_pct"></label></div>
      </div>
      <div v-if="step===5">
        <div class="grid c2">
          <div><div class="stat-line"><span>Description</span><b>{{ b.description }}</b></div><div class="stat-line"><span>Commencement → end</span><span>{{ date(b.commencement_date) }} → {{ date(b.contract_end) }}</span></div>
            <div class="stat-line"><span>Payment</span><span>{{ money(terms.amount) }} every {{ terms.frequency_months }} month(s), {{ terms.timing.toLowerCase() }}</span></div>
            <div class="stat-line"><span>Escalations / rent-free</span><span>{{ terms.escalations.length }} / {{ terms.rent_free.length }}</span></div>
            <div class="stat-line"><span>Our entity is the</span><b>{{ isLessor ? 'Lessor' : 'Lessee' }}</b></div>
            <div class="stat-line" v-if="!isLessor"><span>Discount rate</span><span>{{ b.discount_rate_pct ? b.discount_rate_pct + '%' : '—' }}</span></div>
            <div class="stat-line" v-else><span>Fair value / economic life</span><span>{{ money(ld.fair_value) }} / {{ ld.economic_life_months || '—' }} months</span></div>
            <div class="stat-line"><span>Options</span><span>{{ options.length }} ({{ options.filter(o => o.reasonably_certain===null).length }} not assessed)</span></div>
            <div class="stat-line"><span>Deposit / restoration</span><span>{{ money(dep.amount) }} / {{ money(rest.estimated_cost) }}</span></div></div>
          <div class="alert info"><AppIcon name="info"/><div>The lease is created as <b>Draft</b> and calculated. Review the schedules, then submit for review. Options not yet assessed will block the calculation until a judgment is recorded.</div></div>
        </div>
      </div>
    </div>
    <div class="modal-foot"><button class="btn" :disabled="step===0" @click="step--"><AppIcon name="chevron-left" :size="14"/> Back</button><div class="spacer"></div>
      <button v-if="step < steps.length - 1" class="btn primary" @click="next">Next <AppIcon name="chevron-right" :size="14"/></button>
      <button v-else class="btn primary" :disabled="busy" @click="create"><AppIcon name="file-check" :size="14"/> Create and calculate</button></div></div>
  </div>`,
};
