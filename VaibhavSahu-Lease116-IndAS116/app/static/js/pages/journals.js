// Portfolio journals: review, account summary, ERP exports (CSV / Excel / Tally XML / SAP) and period posting
import { store, get, post, download, toast, showError, confirmDialog } from '../store.js';
import { common } from '../components.js';
import { money, date, monthEnd, decAdd, decSub, titleCase } from '../util.js';

const { ref, computed, watch, onMounted } = Vue;

export const JournalsPage = {
  components: common,
  setup() {
    const base = store.asOf || new Date().toISOString().slice(0, 10);
    const f = ref({ start: base.slice(0, 8) + '01', end: monthEnd(base), summarise: false });
    const rows = ref([]);
    const loading = ref(false);
    const open = ref({});
    const q = ref('');
    const view = ref('entries');
    const postResult = ref(null);
    function qs(extra = {}) {
      const p = new URLSearchParams({ start: f.value.start, end: f.value.end, summarise: f.value.summarise ? 'true' : 'false', ...extra });
      if (store.entityId) p.set('entity_id', store.entityId);
      return p.toString();
    }
    async function load() {
      loading.value = true;
      try { rows.value = await get('/api/journals?' + qs()); open.value = {}; } catch (e) { showError(e); } finally { loading.value = false; }
    }
    onMounted(load);
    watch(() => [f.value.summarise, store.entityId], load);
    const list = computed(() => {
      if (!q.value) return rows.value;
      const s = q.value.toLowerCase();
      return rows.value.filter(j => [j.je_ref, j.lease_code, j.event_label, j.narration].some(x => String(x || '').toLowerCase().includes(s)) ||
        j.lines.some(l => (l.account_code + ' ' + l.account_name).toLowerCase().includes(s)));
    });
    const tot = computed(() => ({
      dr: decAdd(...list.value.map(j => j.total_debit)), cr: decAdd(...list.value.map(j => j.total_credit)),
      unbalanced: list.value.filter(j => !j.balanced).length, posted: list.value.filter(j => j.posted).length,
      unapproved: list.value.filter(j => j.run_status && !['Approved', 'Posted'].includes(j.run_status)).length,
    }));
    const accounts = computed(() => {
      const m = {};
      for (const j of list.value) for (const l of j.lines) {
        const k = l.account_code;
        if (!m[k]) m[k] = { account_code: k, account_name: l.account_name, debit: '0', credit: '0' };
        m[k].debit = decAdd(m[k].debit, l.debit); m[k].credit = decAdd(m[k].credit, l.credit);
      }
      return Object.values(m).map(a => ({ ...a, net: decSub(a.debit, a.credit) })).sort((a, b) => a.account_code.localeCompare(b.account_code));
    });
    const accCols = [{ key: 'account_code', label: 'Account' }, { key: 'account_name', label: 'Account name' }, { key: 'debit', label: 'Debit', type: 'money' },
      { key: 'credit', label: 'Credit', type: 'money' }, { key: 'net', label: 'Net Dr / (Cr)', type: 'money' }];
    const accTot = computed(() => ({ debit: decAdd(...accounts.value.map(a => a.debit)), credit: decAdd(...accounts.value.map(a => a.credit)), net: decAdd(...accounts.value.map(a => a.net)) }));
    function exp(fmt) { download('/api/journals/export?' + qs({ format: fmt }), 'journals.' + fmt); }
    async function postPeriod() {
      const pe = monthEnd(f.value.end);
      const ok = await confirmDialog('Post journals for ' + date(pe), 'Posts journals from APPROVED calculations for the month ending ' + date(pe) + '. Leases without an approved calculation are skipped. Posting is recorded in the audit trail; lock the period afterwards to prevent changes.', { ok: 'Post journals' });
      if (!ok) return;
      try {
        postResult.value = await post('/api/journals/post', { period_end: pe, entity_id: store.entityId || null });
        toast(postResult.value.posted + ' journal(s) posted', 'ok');
        load();
      } catch (e) { showError(e); }
    }
    function thisMonth() { f.value.start = base.slice(0, 8) + '01'; f.value.end = monthEnd(base); load(); }
    function fy() {
      const sm = store.company?.fy_start_month || 4;
      const [y, m] = base.split('-').map(Number);
      const sy = m >= sm ? y : y - 1;
      f.value.start = sy + '-' + String(sm).padStart(2, '0') + '-01';
      f.value.end = base; load();
    }
    return { store, f, rows, list, loading, open, q, view, tot, accounts, accCols, accTot, exp, postPeriod, postResult, load, thisMonth, fy, money, date, titleCase };
  },
  template: `
  <div>
    <div class="page-head"><div class="grow"><h1>Journals</h1><div class="sub">Generated from calculation runs (approved where available, otherwise latest draft — flagged). GL accounts resolve from Settings → GL mapping.</div></div>
      <button class="btn" v-if="store.can('journal.post')" @click="postPeriod"><AppIcon name="send" :size="14"/> Post period</button></div>
    <div class="card mb"><div class="card-body row wrap">
      <label class="field" style="width:160px">From<input type="date" v-model="f.start"></label>
      <label class="field" style="width:160px">To<input type="date" v-model="f.end"></label>
      <button class="btn" style="align-self:end" @click="load"><AppIcon name="refresh-cw" :size="14"/> Apply</button>
      <button class="btn ghost" style="align-self:end" @click="thisMonth">This month</button><button class="btn ghost" style="align-self:end" @click="fy">FY to date</button>
      <label class="check" style="align-self:end;padding-bottom:8px"><input type="checkbox" v-model="f.summarise"> Summarise by event (one entry per period and event)</label>
      <div class="spacer"></div>
      <div class="row" style="align-self:end" v-if="store.can('export')">
        <button class="btn sm" @click="exp('xlsx')"><AppIcon name="file-spreadsheet" :size="13"/> Excel</button><button class="btn sm" @click="exp('csv')">CSV</button>
        <button class="btn sm" @click="exp('tally')" title="Tally Prime / ERP 9 — Import Data → Vouchers">Tally XML</button><button class="btn sm" @click="exp('sap')" title="SAP-style upload (posting keys 40/50)">SAP CSV</button></div>
    </div></div>
    <div class="grid c4 mb">
      <Kpi label="Journal entries" :value="list.length" :foot="tot.posted + ' posted'"/>
      <Kpi label="Total debits" :value="tot.dr" money/>
      <Kpi label="Total credits" :value="tot.cr" money/>
      <Kpi label="Checks" :value="tot.unbalanced ? tot.unbalanced + ' unbalanced' : 'All balanced'" :foot="tot.unapproved ? tot.unapproved + ' from unapproved runs' : 'All from approved runs'"/>
    </div>
    <div v-if="postResult" class="alert info mb"><AppIcon name="info"/><div class="grow"><b>{{ postResult.posted }} journal(s) posted.</b><div v-if="postResult.skipped.length" class="small">Skipped: {{ postResult.skipped.join('; ') }}</div></div><button class="btn sm ghost" @click="postResult=null"><AppIcon name="x" :size="13"/></button></div>
    <div class="row mb"><div class="pill-tabs"><button :class="{on: view==='entries'}" @click="view='entries'">Entries</button><button :class="{on: view==='accounts'}" @click="view='accounts'">Account summary</button></div>
      <div class="search-box" style="width:260px"><AppIcon name="search" :size="14"/><input v-model="q" placeholder="Search lease, account, narration…"></div></div>
    <div class="card" v-if="view==='entries'"><div class="table-wrap" style="max-height:640px"><table class="t compact">
      <thead><tr><th></th><th>JE ref</th><th>Date</th><th>Lease</th><th>Event</th><th>Narration</th><th class="num">Debit</th><th class="num">Credit</th><th>Status</th></tr></thead>
      <tbody><tr v-if="loading"><td colspan="9"><div class="progress"><i></i></div></td></tr>
        <tr v-else-if="!list.length"><td colspan="9" class="empty">No journals for this period.</td></tr>
        <template v-for="j in list" :key="j.je_ref">
          <tr class="clickable" @click="open[j.je_ref] = !open[j.je_ref]"><td><AppIcon :name="open[j.je_ref] ? 'chevron-down' : 'chevron-right'" :size="13"/></td><td class="mono nowrap">{{ j.je_ref }}</td><td class="nowrap">{{ date(j.date) }}</td>
            <td class="nowrap"><a v-if="j.lease_id" :href="'#/leases/' + j.lease_id + '?tab=journals'" @click.stop>{{ j.lease_code }}</a><span v-else>{{ j.lease_code }}</span></td><td class="nowrap">{{ j.event_label }}</td><td class="wrap small">{{ j.narration }}</td>
            <td class="num">{{ money(j.total_debit) }}</td><td class="num">{{ money(j.total_credit) }}</td>
            <td><span v-if="j.posted" class="badge posted">Posted</span><span v-else-if="j.run_status && !['Approved','Posted'].includes(j.run_status)" class="badge warn">{{ j.run_status }} run</span><span v-else class="badge approved">Ready</span>
              <span v-if="!j.balanced" class="badge bad">Unbalanced</span></td></tr>
          <template v-if="open[j.je_ref]"><tr v-for="l in j.lines" :key="j.je_ref + '-' + l.line" style="background:var(--surface-2)"><td></td><td class="mono small">{{ l.account_code }}</td><td colspan="4" class="small">{{ l.account_name }} <span class="muted">({{ titleCase(l.role) }})</span><span v-if="l.cost_centre" class="muted"> · CC {{ l.cost_centre }}</span></td>
            <td class="num small">{{ Number(l.debit) ? money(l.debit) : '' }}</td><td class="num small">{{ Number(l.credit) ? money(l.credit) : '' }}</td><td></td></tr></template>
        </template></tbody></table></div></div>
    <div class="card" v-else><DataTable id="jacc" :columns="accCols" :rows="accounts" row-key="account_code" :totals="accTot" :searchable="false"/></div>
  </div>`,
};
