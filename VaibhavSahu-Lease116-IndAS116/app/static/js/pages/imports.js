// Bulk imports: Upload → Validate → Errors → Correct → Preview → Approve → Import
import { store, get, post, upload, download, toast, showError, confirmDialog } from '../store.js';
import { common } from '../components.js';
import { dateTime, titleCase } from '../util.js';

const { ref, computed, onMounted } = Vue;

const TEMPLATE_INFO = {
  lease_master: ['Lease register (master)', 'Creates Draft leases with payment terms, lock-in / renewal options, deposits and IDC.'],
  payments: ['Irregular payments', 'Adds manual payment lines to existing leases (variable, one-off, irregular schedules).'],
  discount_rates: ['IBR table', 'Portfolio incremental borrowing rates by currency and tenor band (imported as approved).'],
  opening_balances: ['Opening balances (cut-over)', 'Carries forward approved liability and ROU balances for leases migrated mid-life.'],
  gl_balances: ['GL balances', 'Trial-balance balances for the GL reconciliation report.'],
};

export const ImportsPage = {
  components: common,
  setup() {
    const data = ref({ templates: {}, batches: [] });
    const kind = ref('lease_master');
    const file = ref(null);
    const batch = ref(null);
    const busy = ref(false);
    async function load() { try { data.value = await get('/api/imports'); } catch (e) { showError(e); } }
    onMounted(load);
    async function send() {
      if (!file.value) { toast('Choose a file (.xlsx or .csv)', 'bad'); return; }
      busy.value = true;
      const fd = new FormData();
      fd.append('kind', kind.value);
      fd.append('file', file.value);
      try { const r = await upload('/api/imports', fd); batch.value = { ...r, template: kind.value }; load(); }
      catch (e) { showError(e); } finally { busy.value = false; }
    }
    async function openBatch(b) { try { batch.value = await get('/api/imports/' + b.id); } catch (e) { showError(e); } }
    async function approve() {
      const ok = await confirmDialog('Approve and import', 'Imports ' + batch.value.rows_valid + ' validated row(s). Leases are created as Draft and must still be calculated, reviewed and approved.', { ok: 'Import' });
      if (!ok) return;
      try { const r = await post('/api/imports/' + batch.value.id + '/approve'); toast(r.imported + ' row(s) imported', 'ok'); await openBatch(batch.value); load(); window.__lease116?.refreshCounts(); }
      catch (e) { showError(e); }
    }
    const stage = computed(() => {
      const b = batch.value;
      if (!b) return 0;
      if (b.status === 'Imported') return 6;
      if (b.status === 'Errors') return 2;
      if (b.status === 'Validated') return 4;
      return 1;
    });
    const previewCols = computed(() => {
      const r = (batch.value?.preview || [])[0];
      return r ? Object.keys(r).map(k => ({ key: k, label: k })) : [];
    });
    const batchCols = [{ key: 'id', label: '#', type: 'num' }, { key: 'template', label: 'Template', format: (v) => (TEMPLATE_INFO[v] || [v])[0] },
      { key: 'filename', label: 'File' }, { key: 'status', label: 'Status' }, { key: 'uploaded_at', label: 'Uploaded', format: (v) => dateTime(v) },
      { key: 'rows_total', label: 'Rows', type: 'num' }, { key: 'rows_valid', label: 'Valid', type: 'num' }, { key: 'rows_error', label: 'Errors', type: 'num' }];
    const STEPS = ['Upload', 'Validate', 'Errors', 'Correct', 'Preview', 'Approve', 'Import'];
    return { store, data, kind, file, batch, busy, send, openBatch, approve, stage, previewCols, batchCols, STEPS, TEMPLATE_INFO, download, titleCase };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>Imports</h1><div class="sub">Excel / CSV templates with row-level validation. Nothing is imported until a validated batch is approved by a different user (maker-checker).</div></div></div>
    <div class="grid c3 mb">
      <div v-for="(cols, k) in data.templates" :key="k" class="card"><div class="card-head"><AppIcon name="file-spreadsheet" :size="15"/><h3>{{ (TEMPLATE_INFO[k] || [k])[0] }}</h3></div>
        <div class="card-body"><div class="small text-2 mb-sm">{{ (TEMPLATE_INFO[k] || ['',''])[1] }}</div><div class="tiny muted mb-sm">{{ cols.length }} columns: {{ cols.slice(0, 6).join(', ') }}{{ cols.length > 6 ? '…' : '' }}</div>
          <div class="row"><button class="btn sm" @click="download('/api/imports/templates/' + k, 'template.xlsx')"><AppIcon name="download" :size="13"/> Template</button>
            <button class="btn sm" v-if="store.can('import.write')" @click="kind = k"><AppIcon name="upload" :size="13"/> Use</button></div></div></div>
    </div>
    <div class="card mb" v-if="store.can('import.write')"><div class="card-head"><h3>Upload and validate</h3></div><div class="card-body">
      <div class="stepper"><div v-for="(s, i) in STEPS" :key="s" class="step" :class="{on: i===stage, done: i<stage}" style="cursor:default"><span class="n">{{ i < stage ? '✓' : i + 1 }}</span>{{ s }}</div></div>
      <div class="row wrap" style="align-items:flex-end">
        <label class="field" style="width:260px">Template<select v-model="kind"><option v-for="(cols, k) in data.templates" :key="k" :value="k">{{ (TEMPLATE_INFO[k] || [k])[0] }}</option></select></label>
        <label class="field" style="width:340px">File (.xlsx or .csv)<input type="file" accept=".xlsx,.csv" @change="file = $event.target.files[0]"></label>
        <button class="btn primary" :disabled="busy" @click="send"><AppIcon name="shield-check" :size="14"/> Upload and validate</button>
      </div></div></div>
    <div class="card mb" v-if="batch"><div class="card-head"><h3>Batch #{{ batch.id }} — {{ (TEMPLATE_INFO[batch.template] || [batch.template])[0] }}</h3><StatusBadge :status="batch.status"/><div class="spacer"></div>
      <button v-if="batch.rows_error" class="btn sm" @click="download('/api/imports/' + batch.id + '/errors.csv', 'errors.csv')"><AppIcon name="download" :size="13"/> Error report</button>
      <button v-if="batch.status==='Validated' && store.can('import.approve')" class="btn sm primary" @click="approve"><AppIcon name="circle-check" :size="13"/> Approve and import</button></div>
      <div class="card-body">
        <div class="grid c3 mb"><Kpi label="Rows read" :value="batch.rows_total"/><Kpi label="Valid rows" :value="batch.rows_valid"/><Kpi label="Rows with errors" :value="batch.rows_error"/></div>
        <div v-if="batch.status==='Errors'" class="alert bad mb"><AppIcon name="circle-x"/><div>Correct the rows below in the spreadsheet and upload the file again. A batch with any error cannot be imported — partial imports are not allowed.</div></div>
        <div v-if="batch.status==='Validated' && !store.can('import.approve')" class="alert info mb"><AppIcon name="info"/><div>Validated. An approver must approve this batch (segregation of duties).</div></div>
        <div v-if="batch.status==='Imported'" class="alert ok mb"><AppIcon name="circle-check"/><div>Imported. New leases are in the register as Draft — calculate and submit them.</div></div>
        <template v-if="batch.errors && batch.errors.length"><h4 class="mb-sm">Errors</h4>
          <div class="table-wrap" style="max-height:300px"><table class="t compact"><thead><tr><th>Row</th><th>Errors</th><th>Data</th></tr></thead>
            <tbody><tr v-for="e in batch.errors" :key="e.row"><td>{{ e.row }}</td><td class="wrap"><div v-for="(m, i) in e.errors" :key="i" class="neg small">{{ m }}</div></td><td class="small mono wrap">{{ Object.entries(e.data).filter(x => x[1] && x[1] !== 'None').map(x => x[0] + '=' + x[1]).join('; ') }}</td></tr></tbody></table></div></template>
        <template v-if="batch.preview && batch.preview.length"><h4 class="mt mb-sm">Preview of validated rows</h4>
          <DataTable id="imp-preview" :columns="previewCols" :rows="batch.preview" :searchable="false" :page-size="10" row-key="__none"/></template>
      </div></div>
    <div class="card"><div class="card-head"><h3>Import history</h3></div>
      <DataTable id="batches" :columns="batchCols" :rows="data.batches" clickable @row-click="openBatch" :page-size="10" empty-text="No imports yet.">
        <template #cell-status="{ row }"><StatusBadge :status="row.status"/></template></DataTable></div>
  </div>`,
};
