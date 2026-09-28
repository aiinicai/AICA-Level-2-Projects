// Shared UI components
import { icon } from './icons.js';
import { store, download } from './store.js';
import { money, isNeg, date, pct, num, statusClass, titleCase } from './util.js';

const { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } = Vue;

export const AppIcon = {
  props: { name: String, size: { type: Number, default: 16 }, cls: String },
  template: `<span class="ic-wrap" v-html="svg" style="display:inline-flex"></span>`,
  computed: { svg() { return icon(this.name, this.size, this.cls || ''); } },
};

export const StatusBadge = {
  props: { status: String, dot: Boolean },
  template: `<span class="badge" :class="[cls, dot ? 'dot' : '']">{{ status || '—' }}</span>`,
  computed: { cls() { return statusClass(this.status); } },
};

export const Money = {
  props: { value: [String, Number], blank: String, absolute: Boolean },
  template: `<span class="num" :class="{neg: neg}">{{ text }}</span>`,
  computed: {
    text() { return money(this.value, { blank: this.blank, absolute: this.absolute }); },
    neg() { return isNeg(this.value); },
  },
};

export function fmtCell(col, v, row) {
  if (col.format) return col.format(v, row);
  switch (col.type) {
    case 'money': return money(v, { blank: '–', zeroDash: !!col.zeroDash });
    case 'date': return date(v);
    case 'pct': return v === null || v === undefined || v === '' ? '—' : num(v, 4);
    case 'rate': return num(v, 4);
    case 'bool': return v === true ? 'Yes' : v === false ? 'No' : '—';
    default: return v === null || v === undefined || v === '' ? '—' : v;
  }
}

export const DataTable = {
  components: { AppIcon },
  props: {
    id: { type: String, default: 'dt' }, columns: Array, rows: Array, rowKey: { type: String, default: 'id' },
    pageSize: { type: Number, default: 25 }, searchable: { type: Boolean, default: true }, clickable: Boolean,
    totals: Object, dense: Boolean, maxHeight: String, exportName: String, loading: Boolean, emptyText: { type: String, default: 'No records' },
    serverTotal: Number,
  },
  emits: ['row-click', 'export'],
  setup(props, { emit }) {
    const q = ref('');
    const sortKey = ref(null);
    const sortDesc = ref(false);
    const page = ref(1);
    const size = ref(props.pageSize);
    const showCols = ref(false);
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem('lease116.cols.' + props.id) || 'null'); } catch (e) { saved = null; }
    const hidden = ref(new Set(saved || (props.columns || []).filter(c => c.hidden).map(c => c.key)));
    const visibleCols = computed(() => (props.columns || []).filter(c => !hidden.value.has(c.key)));
    const filtered = computed(() => {
      let r = props.rows || [];
      if (q.value) {
        const s = q.value.toLowerCase();
        r = r.filter(row => visibleCols.value.some(c => String(fmtCell(c, row[c.key], row) ?? '').toLowerCase().includes(s)));
      }
      if (sortKey.value) {
        const col = (props.columns || []).find(c => c.key === sortKey.value) || {};
        const numeric = ['money', 'num', 'pct', 'rate'].includes(col.type);
        r = [...r].sort((a, b) => {
          let x = a[sortKey.value], y = b[sortKey.value];
          if (numeric) { x = Number(x ?? -Infinity); y = Number(y ?? -Infinity); }
          else { x = String(x ?? ''); y = String(y ?? ''); }
          return (x < y ? -1 : x > y ? 1 : 0) * (sortDesc.value ? -1 : 1);
        });
      }
      return r;
    });
    const pages = computed(() => Math.max(1, Math.ceil(filtered.value.length / size.value)));
    const pageRows = computed(() => filtered.value.slice((page.value - 1) * size.value, page.value * size.value));
    watch(() => [q.value, props.rows], () => { page.value = 1; });
    function sortBy(c) {
      if (c.sortable === false) return;
      if (sortKey.value === c.key) sortDesc.value = !sortDesc.value; else { sortKey.value = c.key; sortDesc.value = false; }
    }
    function toggleCol(k) {
      const s = new Set(hidden.value);
      s.has(k) ? s.delete(k) : s.add(k);
      hidden.value = s;
      try { localStorage.setItem('lease116.cols.' + props.id, JSON.stringify([...s])); } catch (e) { /* ignore */ }
    }
    function cell(c, row) { return fmtCell(c, row[c.key], row); }
    function cls(c, row) {
      const out = [];
      if (['money', 'num', 'pct', 'rate'].includes(c.type)) out.push('num');
      if (c.type === 'money' && isNeg(row[c.key])) out.push('neg');
      if (c.wrap) out.push('wrap');
      if (c.cls) out.push(typeof c.cls === 'function' ? c.cls(row) : c.cls);
      return out;
    }
    return { q, sortKey, sortDesc, page, size, pages, pageRows, filtered, visibleCols, hidden, showCols, sortBy, toggleCol, cell, cls,
      emit, fmtCell };
  },
  template: `
  <div>
    <div class="dt-toolbar" v-if="searchable || $slots.toolbar">
      <div class="search-box" v-if="searchable" style="width:260px">
        <AppIcon name="search" :size="14"/>
        <input v-model="q" placeholder="Search…" aria-label="Search table">
      </div>
      <slot name="toolbar"></slot>
      <div class="spacer"></div>
      <span class="small muted">{{ filtered.length }} record{{ filtered.length === 1 ? '' : 's' }}</span>
      <div class="rel">
        <button class="btn sm" @click="showCols = !showCols" title="Choose columns"><AppIcon name="columns-3" :size="14"/> Columns</button>
        <div class="dt-cols" v-if="showCols" @mouseleave="showCols=false">
          <label class="check" v-for="c in columns" :key="c.key" style="display:flex;padding:3px 0">
            <input type="checkbox" :checked="!hidden.has(c.key)" @change="toggleCol(c.key)"> {{ c.label }}
          </label>
        </div>
      </div>
      <button v-if="exportName" class="btn sm" @click="emit('export','xlsx')"><AppIcon name="file-spreadsheet" :size="14"/> Excel</button>
      <button v-if="exportName" class="btn sm" @click="emit('export','csv')">CSV</button>
      <button v-if="exportName" class="btn sm" @click="emit('export','pdf')">PDF</button>
    </div>
    <div class="table-wrap" :style="maxHeight ? {maxHeight} : {}">
      <table class="t dt" :class="{compact: dense}">
        <thead><tr>
          <th v-for="c in visibleCols" :key="c.key" :class="[['money','num','pct','rate'].includes(c.type)?'num':'', c.sortable===false?'':'sortable']" @click="sortBy(c)" :title="c.title || ''">
            {{ c.label }}<span v-if="sortKey===c.key">{{ sortDesc ? ' ▾' : ' ▴' }}</span>
          </th>
        </tr></thead>
        <tbody>
          <tr v-if="loading"><td :colspan="visibleCols.length"><div class="progress"><i></i></div></td></tr>
          <tr v-else-if="!pageRows.length"><td :colspan="visibleCols.length" class="empty">{{ emptyText }}</td></tr>
          <tr v-for="(row, i) in pageRows" :key="row[rowKey] ?? i" :class="[clickable ? 'clickable' : '', row._cls || '']" @click="clickable && emit('row-click', row)">
            <td v-for="c in visibleCols" :key="c.key" :class="cls(c, row)">
              <slot :name="'cell-' + c.key" :row="row" :value="row[c.key]">{{ cell(c, row) }}</slot>
            </td>
          </tr>
          <tr v-if="totals && pageRows.length" class="total">
            <td v-for="(c, idx) in visibleCols" :key="c.key" :class="['money','num'].includes(c.type) ? 'num' : ''">
              {{ idx === 0 ? 'Total' : (totals[c.key] !== undefined ? fmtCell(c, totals[c.key], totals) : '') }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="dt-foot" v-if="pages > 1 || filtered.length > 10">
      <span>Rows per page</span>
      <select v-model.number="size" style="width:74px;min-height:26px;padding:2px 6px"><option :value="10">10</option><option :value="25">25</option><option :value="50">50</option><option :value="100">100</option><option :value="1000">All</option></select>
      <div class="spacer"></div>
      <span>Page {{ page }} of {{ pages }}</span>
      <button class="btn sm" :disabled="page<=1" @click="page--"><AppIcon name="chevron-left" :size="14"/></button>
      <button class="btn sm" :disabled="page>=pages" @click="page++"><AppIcon name="chevron-right" :size="14"/></button>
    </div>
  </div>`,
};

export const Modal = {
  components: { AppIcon },
  props: { title: String, wide: Boolean, drawer: Boolean },
  emits: ['close'],
  setup(props, { emit }) {
    const onKey = (e) => { if (e.key === 'Escape') emit('close'); };
    onMounted(() => document.addEventListener('keydown', onKey));
    onBeforeUnmount(() => document.removeEventListener('keydown', onKey));
    return { emit };
  },
  template: `
  <teleport to="body">
    <template v-if="drawer">
      <div class="drawer-bg" @click="emit('close')"></div>
      <div class="drawer" role="dialog" :aria-label="title">
        <div class="modal-head"><h2 class="grow">{{ title }}</h2><slot name="head"></slot><button class="btn icon ghost" @click="emit('close')" aria-label="Close"><AppIcon name="x"/></button></div>
        <div class="modal-body"><slot></slot></div>
        <div class="modal-foot" v-if="$slots.foot"><slot name="foot"></slot></div>
      </div>
    </template>
    <div v-else class="modal-bg" @mousedown.self="emit('close')">
      <div class="modal" :class="{wide}" role="dialog" :aria-label="title">
        <div class="modal-head"><h2 class="grow">{{ title }}</h2><button class="btn icon ghost" @click="emit('close')" aria-label="Close"><AppIcon name="x"/></button></div>
        <div class="modal-body"><slot></slot></div>
        <div class="modal-foot" v-if="$slots.foot"><slot name="foot"></slot></div>
      </div>
    </div>
  </teleport>`,
};

export const Tabs = {
  props: { tabs: Array, modelValue: String },
  emits: ['update:modelValue'],
  template: `<div class="tabs" role="tablist"><button v-for="t in tabs" :key="t.key" role="tab" :class="{on: t.key===modelValue}" @click="$emit('update:modelValue', t.key)">{{ t.label }}<span v-if="t.count" class="badge" style="margin-left:6px">{{ t.count }}</span></button></div>`,
};

export const Kpi = {
  components: { AppIcon },
  props: { label: String, value: [String, Number], foot: String, icon: String, money: Boolean, onclick: Function },
  template: `<div class="tile" :style="onclick ? 'cursor:pointer' : ''" @click="onclick && onclick()">
    <div class="label"><AppIcon v-if="icon" :name="icon" :size="14"/>{{ label }}</div>
    <div class="value">{{ display }}</div>
    <div class="foot" v-if="foot">{{ foot }}</div></div>`,
  computed: { display() { return this.money ? money(this.value) : (this.value ?? '—'); } },
};

export const FlagList = {
  components: { AppIcon },
  props: { flags: Array, empty: { type: String, default: 'No judgment flags.' } },
  template: `<div>
    <div v-if="!flags || !flags.length" class="muted small">{{ empty }}</div>
    <div v-for="(f, i) in flags" :key="i" class="judgment" :class="{info: (f.severity||'')==='INFO'}">
      <div class="t"><AppIcon :name="(f.severity||'')==='INFO' ? 'info' : 'flag'" :size="13"/>{{ f.title }}<span class="badge warn" v-if="(f.severity||'REVIEW')!=='INFO'" style="margin-left:auto">Accounting judgment required</span></div>
      <div class="d">{{ f.detail }}</div>
      <div class="r" v-if="f.reference || f.ref">{{ f.reference || f.ref }}</div>
      <div class="r" v-if="f.assumptions && f.assumptions.length">Assumptions: {{ f.assumptions.join('; ') }}</div>
    </div></div>`,
};

export const IssueList = {
  components: { AppIcon },
  props: { issues: Array },
  template: `<div v-if="issues && issues.length" class="col">
    <div v-for="(i, k) in issues" :key="k" class="alert" :class="i.severity==='ERROR' ? 'bad' : i.severity==='WARNING' ? 'warn' : 'info'">
      <AppIcon :name="i.severity==='ERROR' ? 'circle-x' : i.severity==='WARNING' ? 'triangle-alert' : 'info'"/>
      <div><b>{{ i.code || i.severity }}</b> — {{ i.message || i }}</div>
    </div></div>`,
};

function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

export const BarChart = {
  components: { AppIcon },
  props: { labels: Array, values: Array, horizontal: Boolean, height: { type: Number, default: 240 }, series: { type: Number, default: 1 },
    valueLabel: { type: String, default: 'Amount' }, highlightLast: Number },
  setup(props) {
    const canvas = ref(null);
    const table = ref(false);
    let chart = null;
    function render() {
      if (!canvas.value || table.value) return;
      if (chart) chart.destroy();
      const color = cssVar('--series-' + props.series) || '#2a78d6';
      const grid = cssVar('--chart-grid');
      const muted = cssVar('--chart-muted');
      const axis = cssVar('--chart-axis');
      const vals = (props.values || []).map(v => Number(v || 0));
      const fmt = (v) => money(String(v));
      chart = new Chart(canvas.value, {
        type: 'bar',
        data: { labels: props.labels, datasets: [{ label: props.valueLabel, data: vals, backgroundColor: color, borderRadius: 4,
          borderSkipped: 'start', maxBarThickness: props.horizontal ? 22 : 38, categoryPercentage: 0.8, barPercentage: 0.9 }] },
        options: {
          indexAxis: props.horizontal ? 'y' : 'x', responsive: true, maintainAspectRatio: false, animation: { duration: 250 },
          plugins: { legend: { display: false },
            tooltip: { backgroundColor: cssVar('--text'), titleColor: cssVar('--surface'), bodyColor: cssVar('--surface'), padding: 8,
              displayColors: false, callbacks: { label: (c) => `${props.valueLabel}: ${fmt(c.raw)}` } } },
          scales: {
            x: { grid: { color: props.horizontal ? grid : 'transparent', drawTicks: false }, border: { color: axis },
              ticks: { color: muted, font: { size: 11 }, callback: function (v) { const l = this.getLabelForValue ? this.getLabelForValue(v) : v; return props.horizontal ? compact(v) : l; } } },
            y: { grid: { color: props.horizontal ? 'transparent' : grid, drawTicks: false }, border: { color: axis, display: !props.horizontal },
              ticks: { color: muted, font: { size: 11 }, callback: function (v) { return props.horizontal ? this.getLabelForValue(v) : compact(v); } } },
          },
        },
      });
    }
    function compact(v) {
      const n = Number(v);
      const a = Math.abs(n);
      if (a >= 1e7) return (n / 1e7).toFixed(a >= 1e9 ? 0 : 1) + ' Cr';
      if (a >= 1e5) return (n / 1e5).toFixed(1) + ' L';
      if (a >= 1e3) return (n / 1e3).toFixed(0) + 'k';
      return String(n);
    }
    onMounted(() => nextTick(render));
    watch(() => [props.labels, props.values, store.theme, table.value], () => nextTick(render), { deep: true });
    onBeforeUnmount(() => chart && chart.destroy());
    return { canvas, table, money };
  },
  template: `<div>
    <div class="row" style="justify-content:flex-end;margin:-4px 0 4px"><div class="pill-tabs"><button :class="{on:!table}" @click="table=false">Chart</button><button :class="{on:table}" @click="table=true">Table</button></div></div>
    <div v-show="!table" class="chart-box" :style="{height: height + 'px'}"><canvas ref="canvas" role="img" :aria-label="valueLabel + ' chart'"></canvas></div>
    <div v-if="table" class="table-wrap" :style="{maxHeight: height + 'px'}"><table class="t compact"><thead><tr><th>Category</th><th class="num">{{ valueLabel }}</th></tr></thead>
      <tbody><tr v-for="(l, i) in labels" :key="i"><td>{{ l }}</td><td class="num">{{ money(values[i]) }}</td></tr></tbody></table></div>
    <div v-if="!labels || !labels.length" class="empty">No data</div>
  </div>`,
};

function compactNum(v) {
  const n = Number(v);
  const a = Math.abs(n);
  if (a >= 1e7) return (n / 1e7).toFixed(a >= 1e9 ? 0 : 1) + ' Cr';
  if (a >= 1e5) return (n / 1e5).toFixed(1) + ' L';
  if (a >= 1e3) return (n / 1e3).toFixed(0) + 'k';
  return String(n);
}

// vertical hover guide for line charts (crosshair)
const crosshairPlugin = {
  id: 'l116crosshair',
  afterDatasetsDraw(chart) {
    const act = chart.tooltip && chart.tooltip.getActiveElements ? chart.tooltip.getActiveElements() : [];
    if (!act || !act.length) return;
    const x = act[0].element.x;
    const { top, bottom } = chart.chartArea;
    const ctx = chart.ctx;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(x, top);
    ctx.lineTo(x, bottom);
    ctx.lineWidth = 1;
    ctx.strokeStyle = cssVar('--chart-axis');
    ctx.stroke();
    ctx.restore();
  },
};

// Multi-series line chart: 2px lines, legend + direct identity, index tooltip with crosshair, table view.
export const LineChart = {
  components: { AppIcon },
  props: { labels: Array, series: Array, height: { type: Number, default: 260 }, stepped: Boolean, labelFormat: Function },
  setup(props) {
    const canvas = ref(null);
    const table = ref(false);
    let chart = null;
    const color = (s, i) => cssVar('--series-' + (s.color || i + 1));
    function render() {
      if (!canvas.value || table.value) return;
      if (chart) chart.destroy();
      const grid = cssVar('--chart-grid');
      const muted = cssVar('--chart-muted');
      const axis = cssVar('--chart-axis');
      const surface = cssVar('--surface');
      chart = new Chart(canvas.value, {
        type: 'line',
        plugins: [crosshairPlugin],
        data: {
          labels: (props.labels || []).map(l => props.labelFormat ? props.labelFormat(l) : l),
          datasets: (props.series || []).map((s, i) => ({
            label: s.label, data: (s.values || []).map(v => (v === null || v === undefined ? null : Number(v))),
            borderColor: color(s, i), backgroundColor: color(s, i), borderWidth: 2, pointRadius: 0, pointHoverRadius: 4,
            pointHoverBorderWidth: 2, pointHoverBorderColor: surface, tension: 0, stepped: props.stepped ? 'after' : false,
            borderDash: s.dashed ? [5, 4] : [], spanGaps: true,
          })),
        },
        options: {
          responsive: true, maintainAspectRatio: false, animation: { duration: 250 },
          interaction: { mode: 'index', intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: { backgroundColor: cssVar('--text'), titleColor: surface, bodyColor: surface, padding: 8, boxPadding: 4,
              callbacks: { label: (c) => ` ${c.dataset.label}: ${money(String(c.raw))}` } },
          },
          scales: {
            x: { grid: { display: false }, border: { color: axis }, ticks: { color: muted, font: { size: 11 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 9 } },
            y: { grid: { color: grid, drawTicks: false }, border: { display: false }, ticks: { color: muted, font: { size: 11 }, callback: (v) => compactNum(v) } },
          },
        },
      });
    }
    onMounted(() => nextTick(render));
    watch(() => [props.labels, props.series, store.theme, table.value], () => nextTick(render), { deep: true });
    onBeforeUnmount(() => chart && chart.destroy());
    const legend = computed(() => (props.series || []).map((s, i) => ({ label: s.label, color: 'var(--series-' + (s.color || i + 1) + ')', dashed: s.dashed })));
    const fmtLabel = (l) => props.labelFormat ? props.labelFormat(l) : l;
    return { canvas, table, legend, money, fmtLabel };
  },
  template: `<div>
    <div class="row" style="margin:-4px 0 6px">
      <div class="legend grow" v-if="legend.length > 1"><span v-for="l in legend" :key="l.label"><i :style="{background: l.color}"></i>{{ l.label }}</span></div>
      <div class="grow" v-else></div>
      <div class="pill-tabs"><button :class="{on:!table}" @click="table=false">Chart</button><button :class="{on:table}" @click="table=true">Table</button></div>
    </div>
    <div v-show="!table" class="chart-box" :style="{height: height + 'px'}"><canvas ref="canvas" role="img" aria-label="Line chart"></canvas></div>
    <div v-if="table" class="table-wrap" :style="{maxHeight: height + 'px'}"><table class="t compact"><thead><tr><th>Period</th><th class="num" v-for="s in series" :key="s.label">{{ s.label }}</th></tr></thead>
      <tbody><tr v-for="(l, i) in labels" :key="i"><td>{{ fmtLabel(l) }}</td><td class="num" v-for="s in series" :key="s.label">{{ money(s.values[i]) }}</td></tr></tbody></table></div>
  </div>`,
};

export const Field = {
  props: { label: String, hint: String, required: Boolean },
  template: `<label class="field"><span :class="{req: required}">{{ label }}</span><slot></slot><span class="hint" v-if="hint">{{ hint }}</span></label>`,
};

export const ExportMenu = {
  components: { AppIcon },
  props: { items: Array },
  setup() { const open = ref(false); return { open, download }; },
  template: `<div class="rel"><button class="btn" @click="open=!open"><AppIcon name="download" :size="14"/> Export <AppIcon name="chevron-down" :size="13"/></button>
    <div class="menu" v-if="open" @mouseleave="open=false"><button v-for="it in items" :key="it.label" @click="open=false; download(it.url, it.name)"><AppIcon :name="it.icon || 'file-down'" :size="14"/>{{ it.label }}</button></div></div>`,
};

export const Empty = {
  components: { AppIcon },
  props: { icon: { type: String, default: 'list' }, text: String },
  template: `<div class="empty"><AppIcon :name="icon" :size="32"/><div>{{ text }}</div><slot></slot></div>`,
};

// Yes / No / Not assessed tri-state selector (judgments must be explicit — never defaulted)
export const TriState = {
  props: { modelValue: { default: null }, yes: { type: String, default: 'Yes' }, no: { type: String, default: 'No' }, disabled: Boolean },
  emits: ['update:modelValue'],
  template: `<div class="btn-group" role="radiogroup">
    <button type="button" class="btn sm" :class="{on: modelValue === true}" :disabled="disabled" @click="$emit('update:modelValue', true)">{{ yes }}</button>
    <button type="button" class="btn sm" :class="{on: modelValue === false}" :disabled="disabled" @click="$emit('update:modelValue', false)">{{ no }}</button>
    <button type="button" class="btn sm" :class="{on: modelValue === null || modelValue === undefined}" :disabled="disabled" @click="$emit('update:modelValue', null)">Not assessed</button>
  </div>`,
};

export const common = { AppIcon, StatusBadge, Money, DataTable, Modal, Tabs, Kpi, FlagList, IssueList, BarChart, LineChart, Field, ExportMenu, Empty, TriState };
export { money, date, pct, num, titleCase };
