// Lease116 — application shell, router and bootstrap
import { store, get, post, toast, showError } from './store.js';
import { common, AppIcon, Modal } from './components.js';
import { today } from './util.js';
import { LoginPage } from './pages/login.js';
import { DashboardPage } from './pages/dashboard.js';
import { LeasesPage } from './pages/leases.js';
import { LeaseDetailPage } from './pages/lease_detail.js';
import { NewLeasePage, ReaderPage, ManualWizardPage } from './pages/new_lease.js';
import { EventsPage } from './pages/events.js';
import { JournalsPage } from './pages/journals.js';
import { DisclosuresPage } from './pages/disclosures.js';
import { ReportsPage } from './pages/reports.js';
import { ImportsPage } from './pages/imports.js';
import { PeriodsPage, ApprovalsPage, AuditPage } from './pages/controls.js';
import { SettingsPage } from './pages/settings.js';
import { PaymentsPage } from './pages/payments.js';

const { createApp, ref, computed, onMounted, watch } = Vue;

const ROUTES = [
  { path: /^\/login$/, comp: 'LoginPage', title: 'Sign in', public: true },
  { path: /^\/?$|^\/dashboard$/, comp: 'DashboardPage', title: 'Dashboard', nav: 'dashboard' },
  { path: /^\/leases$/, comp: 'LeasesPage', title: 'Lease register', nav: 'leases' },
  { path: /^\/leases\/(\d+)$/, comp: 'LeaseDetailPage', title: 'Lease', nav: 'leases', params: ['id'] },
  { path: /^\/new$/, comp: 'NewLeasePage', title: 'New lease', nav: 'new' },
  { path: /^\/new\/manual$/, comp: 'ManualWizardPage', title: 'New lease — manual entry', nav: 'new' },
  { path: /^\/extract\/(\d+)$/, comp: 'ReaderPage', title: 'Agreement reader — review', nav: 'new', params: ['id'] },
  { path: /^\/payments$/, comp: 'PaymentsPage', title: 'Payments', nav: 'payments' },
  { path: /^\/modifications$/, comp: 'EventsPage', title: 'Modifications', nav: 'modifications', props: { kind: 'MODIFICATION' } },
  { path: /^\/reassessments$/, comp: 'EventsPage', title: 'Reassessments', nav: 'reassessments', props: { kind: 'REASSESSMENT' } },
  { path: /^\/journals$/, comp: 'JournalsPage', title: 'Journals', nav: 'journals' },
  { path: /^\/disclosures$/, comp: 'DisclosuresPage', title: 'Disclosures', nav: 'disclosures' },
  { path: /^\/reports(?:\/([a-z_]+))?$/, comp: 'ReportsPage', title: 'Reports', nav: 'reports', params: ['code'] },
  { path: /^\/imports$/, comp: 'ImportsPage', title: 'Imports', nav: 'imports' },
  { path: /^\/periods$/, comp: 'PeriodsPage', title: 'Accounting periods', nav: 'periods' },
  { path: /^\/approvals$/, comp: 'ApprovalsPage', title: 'Approvals', nav: 'approvals' },
  { path: /^\/settings$/, comp: 'SettingsPage', title: 'Settings', nav: 'settings' },
  { path: /^\/audit$/, comp: 'AuditPage', title: 'Audit trail', nav: 'audit' },
];

const NAV = [
  { group: 'Overview' },
  { key: 'dashboard', label: 'Dashboard', icon: 'layout-dashboard', href: '#/dashboard' },
  { group: 'Leases' },
  { key: 'leases', label: 'Leases', icon: 'file-text', href: '#/leases' },
  { key: 'new', label: 'New lease', icon: 'file-plus', href: '#/new', perm: 'lease.write' },
  { key: 'payments', label: 'Payments', icon: 'wallet', href: '#/payments' },
  { group: 'Events' },
  { key: 'modifications', label: 'Modifications', icon: 'git-branch', href: '#/modifications' },
  { key: 'reassessments', label: 'Reassessments', icon: 'refresh-cw', href: '#/reassessments' },
  { group: 'Accounting' },
  { key: 'journals', label: 'Journals', icon: 'book-open', href: '#/journals', perm: 'journal.read' },
  { key: 'disclosures', label: 'Disclosures', icon: 'clipboard-list', href: '#/disclosures', perm: 'disclosure.read' },
  { key: 'reports', label: 'Reports', icon: 'chart-column', href: '#/reports', perm: 'report.read' },
  { group: 'Controls' },
  { key: 'approvals', label: 'Approvals', icon: 'circle-check', href: '#/approvals', badge: true },
  { key: 'periods', label: 'Accounting periods', icon: 'calendar-check', href: '#/periods' },
  { key: 'audit', label: 'Audit trail', icon: 'history', href: '#/audit', perm: 'audit.read' },
  { group: 'Data' },
  { key: 'imports', label: 'Imports', icon: 'upload', href: '#/imports' },
  { key: 'settings', label: 'Settings', icon: 'settings', href: '#/settings' },
];

function parseHash() {
  const h = location.hash.replace(/^#/, '') || '/dashboard';
  const [path, qs] = h.split('?');
  const query = Object.fromEntries(new URLSearchParams(qs || ''));
  for (const r of ROUTES) {
    const m = r.path.exec(path);
    if (m) {
      const params = {};
      (r.params || []).forEach((p, i) => { params[p] = m[i + 1]; });
      return { ...r, params, query, fullPath: h };
    }
  }
  return { ...ROUTES[1], params: {}, query, fullPath: h };
}

const App = {
  components: { ...common, LoginPage, DashboardPage, LeasesPage, LeaseDetailPage, NewLeasePage, ReaderPage, ManualWizardPage, EventsPage,
    JournalsPage, DisclosuresPage, ReportsPage, ImportsPage, PeriodsPage, ApprovalsPage, AuditPage, SettingsPage, PaymentsPage },
  setup() {
    const route = ref(parseHash());
    const menu = ref(false);
    const pwd = ref(null);
    const pageTitle = ref('');
    window.addEventListener('hashchange', () => {
      const prev = route.value.fullPath.split('?')[0];
      route.value = parseHash();
      if (route.value.fullPath.split('?')[0] !== prev) pageTitle.value = '';
      menu.value = false;
    });
    const nav = computed(() => NAV.filter(n => !n.perm || store.can(n.perm)));
    const title = computed(() => pageTitle.value || route.value.title);
    function setTitle(t) { pageTitle.value = t; }
    async function boot() {
      try {
        const me = await get('/api/auth/me');
        Object.assign(store, { user: me.user, company: me.company, entities: me.entities, assetClasses: me.asset_classes, version: me.version,
          numberFormat: me.display?.number_format || 'INDIAN' });
        if (!store.asOf) store.asOf = today();
        store.ready = true;
        refreshCounts();
        if (route.value.public) location.hash = '#/dashboard';
      } catch (e) {
        store.ready = true;
        if (!route.value.public) location.hash = '#/login';
      }
    }
    async function refreshCounts() {
      try { const a = await get('/api/approvals'); store.approvalsCount = (a.leases || []).filter(x => x.status !== 'Draft').length + (a.rates || []).length + (a.imports || []).length; } catch (e) { /* ignore */ }
    }
    async function logout() { await post('/api/auth/logout'); store.user = null; location.hash = '#/login'; }
    async function changePwd() {
      try { await post('/api/auth/change-password', { current: pwd.value.current, new: pwd.value.new }); toast('Password changed', 'ok'); pwd.value = null; store.user.must_change_password = false; }
      catch (e) { showError(e); }
    }
    function applyTheme() { document.documentElement.setAttribute('data-theme', store.theme); }
    function toggleTheme() { store.theme = store.theme === 'dark' ? 'light' : 'dark'; store.persist(); applyTheme(); }
    watch(() => [store.asOf, store.entityId, store.units], () => store.persist());
    onMounted(() => { applyTheme(); boot(); });
    window.__lease116 = { refreshCounts, boot, setTitle };
    return { store, route, nav, menu, logout, toggleTheme, title, pwd, changePwd, setTitle, boot };
  },
  template: `
  <div v-if="!store.ready" class="login-bg"><div class="progress" style="width:200px"><i></i></div></div>
  <LoginPage v-else-if="route.public || !store.user" @signed-in="boot"/>
  <div v-else class="shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">116</div><div class="brand-text"><div class="brand-name">Lease116</div><div class="brand-sub">Ind AS 116 · IFRS 16</div></div></div>
      <nav class="nav" aria-label="Main">
        <template v-for="n in nav" :key="n.key || n.group">
          <div v-if="n.group" class="nav-group">{{ n.group }}</div>
          <a v-else :href="n.href" :class="{active: route.nav === n.key}"><AppIcon :name="n.icon" :size="16"/><span>{{ n.label }}</span><span v-if="n.badge && store.approvalsCount" class="count">{{ store.approvalsCount }}</span></a>
        </template>
      </nav>
      <div class="sidebar-foot">{{ store.company?.name }}<br>Framework: {{ store.company?.framework === 'IFRS_16' ? 'IFRS 16' : 'Ind AS 116' }} · v{{ store.version }}</div>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="grow"><div class="title">{{ title }}</div></div>
        <label class="row small text-2 nowrap" title="Reporting date used by the dashboard and reports">As of
          <input type="date" v-model="store.asOf" style="width:150px;min-height:30px"></label>
        <select v-model="store.entityId" style="width:190px;min-height:30px" aria-label="Entity">
          <option value="">All entities</option><option v-for="e in store.entities" :key="e.id" :value="e.id">{{ e.code }} — {{ e.name }}</option>
        </select>
        <select v-model="store.units" style="width:112px;min-height:30px" aria-label="Units" title="Display units">
          <option value="ABSOLUTE">₹ absolute</option><option value="LAKHS">₹ lakh</option><option value="CRORES">₹ crore</option>
        </select>
        <button class="btn icon ghost" @click="toggleTheme" :title="store.theme==='dark' ? 'Light theme' : 'Dark theme'"><AppIcon :name="store.theme==='dark' ? 'sun' : 'moon'"/></button>
        <div class="rel">
          <button class="btn ghost" @click="menu=!menu"><AppIcon name="user"/> {{ store.user.full_name }} <span class="badge info">{{ store.user.role_name }}</span></button>
          <div class="menu" v-if="menu" @mouseleave="menu=false">
            <div class="small muted" style="padding:6px 9px">Signed in as <b>{{ store.user.username }}</b></div><hr>
            <button @click="pwd={current:'',new:''}; menu=false"><AppIcon name="key-round" :size="14"/> Change password</button>
            <a href="/api/docs" target="_blank"><AppIcon name="external-link" :size="14"/> API documentation</a>
            <hr><button @click="logout"><AppIcon name="log-out" :size="14"/> Sign out</button>
          </div>
        </div>
      </header>
      <div class="content">
        <div v-if="store.user.must_change_password && store.user.username==='admin'" class="alert warn mb">
          <AppIcon name="triangle-alert"/><div class="grow">The default administrator password is still in use. Change it before storing client data.</div>
          <button class="btn sm" @click="pwd={current:'',new:''}">Change now</button>
        </div>
        <component :is="route.comp" :key="route.fullPath.split('?')[0]" :route="route" v-bind="route.props || {}" @title="setTitle"></component>
      </div>
    </main>
  </div>
  <div class="toasts" aria-live="polite"><div v-for="t in store.toasts" :key="t.id" class="toast" :class="t.kind">{{ t.msg }}</div></div>
  <Modal v-if="store.confirm" :title="store.confirm.title" @close="store.confirm.resolve(false); store.confirm=null">
    <p style="white-space:pre-wrap">{{ store.confirm.message }}</p>
    <label v-if="store.confirm.input" class="field">{{ store.confirm.input }}<textarea v-model="store.confirm.value"></textarea></label>
    <template #foot><button class="btn" @click="store.confirm.resolve(false); store.confirm=null">Cancel</button>
      <button class="btn" :class="store.confirm.danger ? 'danger' : 'primary'" @click="store.confirm.resolve(store.confirm.input ? (store.confirm.value || '') : true); store.confirm=null">{{ store.confirm.ok || 'Confirm' }}</button></template>
  </Modal>
  <Modal v-if="pwd" title="Change password" @close="pwd=null">
    <div class="col"><label class="field">Current password<input type="password" v-model="pwd.current"></label>
    <label class="field">New password (min. 8 characters)<input type="password" v-model="pwd.new"></label></div>
    <template #foot><button class="btn" @click="pwd=null">Cancel</button><button class="btn primary" @click="changePwd">Change password</button></template>
  </Modal>`,
};

createApp(App).mount('#app');
