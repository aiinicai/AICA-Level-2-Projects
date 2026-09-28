// Standard reports (17) with filters and Excel / CSV / PDF export
import { store, get, download, showError } from '../store.js';
import { common } from '../components.js';
import { money, date, num, fyOf } from '../util.js';
import { STATUSES } from './leases.js';

const { ref, computed, watch, onMounted } = Vue;

const INFO = {
  lease_register: ['file-text', 'All leases with key terms, rates and balances at the reporting date'],
  liability_schedule: ['landmark', 'Opening, interest, payments, remeasurements and closing liability by period'],
  rou_schedule: ['building-2', 'ROU cost, depreciation, impairment and carrying amount by period'],
  combined_schedule: ['table-2', 'Liability and ROU movements side by side'],
  journal_report: ['book-open', 'Journal lines with GL accounts for the period'],
  gl_reconciliation: ['scale', 'Lease116 balances vs imported GL balances by account'],
  maturity_analysis: ['calendar', 'Undiscounted payments by time band per lease'],
  disclosure_report: ['clipboard-list', 'Para 53 disclosure amounts for the period'],
  expiry_report: ['hourglass', 'Leases by accounting lease-term end'],
  renewal_options: ['refresh-ccw', 'Extension, termination and purchase options with judgments'],
  modification_report: ['git-branch', 'Modifications, reassessments and terminations with impact'],
  deposit_report: ['wallet', 'Security deposits — fair value, prepaid rent and amortised cost'],
  fx_report: ['coins', 'Foreign-currency leases — closing rates and exchange differences'],
  impairment_report: ['trending-down', 'ROU impairment events'],
  exemption_report: ['shield-check', 'Short-term and low-value leases with validation'],
  audit_trail: ['history', 'All changes, approvals, exports and logins'],
  exceptions: ['triangle-alert', 'Missing contracts, rates, pending judgments, calculation issues'],
};
const PERIOD_REPORTS = ['liability_schedule', 'rou_schedule', 'combined_schedule', 'journal_report', 'disclosure_report', 'deposit_report', 'fx_report', 'exemption_report'];

export const ReportsPage = {
  components: common,
  props: { route: Object },
  setup(props) {
    const list = ref([]);
    const code = ref(props.route.params.code || '');
    const [fs] = fyOf(store.asOf || new Date().toISOString().slice(0, 10), store.company?.fy_start_month || 4);
    const f = ref({ as_of: store.asOf, start: fs, end: store.asOf, asset_class: '', currency: '', status: '', location: '', cost_centre: '', all_accounts: false });
    const rep = ref(null);
    const loading = ref(false);
    onMounted(async () => {
      try { list.value = (await get('/api/reports')).filter(r => r.code !== 'audit_trail' || store.can('audit.read')); } catch (e) { showError(e); }
      if (code.value) run();
    });
    function params(extra = {}) {
      const p = new URLSearchParams();
      Object.entries({ ...f.value, ...extra }).forEach(([k, v]) => { if (v !== '' && v !== null && v !== undefined && v !== false) p.set(k, v); });
      if (store.entityId) p.set('entity_id', store.entityId);
      return p.toString();
    }
    async function run() {
      if (!code.value) return;
      loading.value = true;
      try { rep.value = await get('/api/reports/' + code.value + '?' + params()); } catch (e) { rep.value = null; showError(e); } finally { loading.value = false; }
    }
    function pick(c) { code.value = c; rep.value = null; history.replaceState(null, '', '#/reports/' + c); run(); }
    watch(() => store.entityId, run);
    const cols = computed(() => (rep.value?.columns || []).map(c => ({ ...c, type: c.type === 'text' ? undefined : c.type,
      format: c.type === 'pct' ? (v) => (v === null || v === undefined || v === '' ? '—' : num(v, 2)) : undefined, wrap: ['description', 'message', 'basis', 'rationale', 'narration', 'item'].includes(c.key) })));
    const isPeriod = computed(() => PERIOD_REPORTS.includes(code.value));
    function exp(fmt) { download('/api/reports/' + code.value + '/export?' + params({ format: fmt }), code.value + '.' + fmt); }
    const title = computed(() => (list.value.find(r => r.code === code.value) || {}).title || 'Reports');
    return { store, list, code, f, rep, loading, run, pick, cols, isPeriod, exp, title, INFO, STATUSES, money, date };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>Reports</h1><div class="sub">Filterable standard reports — every report exports to Excel, CSV and PDF with filters and generation details in the header.</div></div></div>
    <div class="grid" style="grid-template-columns:280px minmax(0,1fr)">
      <div class="card" style="align-self:start"><div class="card-body flush">
        <button v-for="r in list" :key="r.code" class="menu-item" @click="pick(r.code)" :style="{display:'flex',gap:'10px',width:'100%',textAlign:'left',padding:'9px 12px',border:0,borderBottom:'1px solid var(--border)',background: r.code===code ? 'var(--surface-3)' : 'transparent',cursor:'pointer',font:'inherit',color:'var(--text)'}">
          <AppIcon :name="(INFO[r.code] || ['file-text'])[0]" :size="15"/><span><span style="font-weight:600;font-size:12.8px">{{ r.title }}</span><br><span class="tiny muted">{{ (INFO[r.code] || ['',''])[1] }}</span></span></button>
      </div></div>
      <div>
        <div v-if="!code" class="card"><Empty icon="chart-column" text="Choose a report on the left."/></div>
        <template v-else>
          <div class="card mb"><div class="card-head"><h3>{{ title }}</h3><div class="spacer"></div>
            <template v-if="rep && store.can('export')"><button class="btn sm" @click="exp('xlsx')"><AppIcon name="file-spreadsheet" :size="13"/> Excel</button><button class="btn sm" @click="exp('csv')">CSV</button><button class="btn sm" @click="exp('pdf')"><AppIcon name="printer" :size="13"/> PDF</button></template></div>
            <div class="card-body row wrap" style="align-items:flex-end">
              <label class="field" style="width:150px">As of<input type="date" v-model="f.as_of"></label>
              <template v-if="isPeriod"><label class="field" style="width:150px">From<input type="date" v-model="f.start"></label><label class="field" style="width:150px">To<input type="date" v-model="f.end"></label></template>
              <label class="field" style="width:170px">Asset class<select v-model="f.asset_class"><option value="">All</option><option v-for="a in store.assetClasses" :key="a.id" :value="a.name">{{ a.name }}</option></select></label>
              <label class="field" style="width:140px">Status<select v-model="f.status"><option value="">All</option><option v-for="s in STATUSES" :key="s">{{ s }}</option></select></label>
              <label class="field" style="width:90px">Currency<input v-model="f.currency" maxlength="3" placeholder="All"></label>
              <label class="field" style="width:150px">Location<input v-model="f.location" placeholder="contains…"></label>
              <label class="field" style="width:120px">Cost centre<input v-model="f.cost_centre"></label>
              <label v-if="code==='gl_reconciliation'" class="check" style="padding-bottom:8px"><input type="checkbox" v-model="f.all_accounts"> All accounts</label>
              <button class="btn primary" @click="run"><AppIcon name="play" :size="14"/> Run</button>
            </div></div>
          <div class="card">
            <div v-if="loading" class="card-body"><div class="progress"><i></i></div></div>
            <DataTable v-else-if="rep" :id="'rep-' + code" :columns="cols" :rows="rep.rows" :totals="rep.totals" :page-size="50" :row-key="'__none'">
              <template #cell-status="{ row }"><StatusBadge v-if="['Draft','Prepared','Under Review','Approved','Posted','Modified','Terminated','Archived','Rejected','Submitted'].includes(row.status)" :status="row.status"/><span v-else :class="row.status==='EXCEPTION' ? 'badge bad' : row.status==='Reconciled' ? 'badge ok' : ''">{{ row.status }}</span></template>
              <template #cell-severity="{ row }"><span class="badge" :class="row.severity==='ERROR' ? 'bad' : row.severity==='WARNING' ? 'warn' : 'info'">{{ row.severity }}</span></template>
            </DataTable>
          </div>
        </template>
      </div>
    </div>
  </div>`,
};
