import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  LayoutDashboard, FileText, Building2, Users as UsersIcon, ListChecks,
  LogOut, Plus, Pencil, Trash2, Download, Search, AlertTriangle,
  X, ChevronDown, ChevronLeft, ChevronRight, ShieldCheck, Mail,
  Clock, IndianRupee, History, Menu, Check, UserPlus, Ban, RotateCcw,
  FileSpreadsheet, Printer
} from "lucide-react";
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import * as XLSX from "xlsx";

/* ============================== CONSTANTS ============================== */

const STAGES = ["CPC", "AO", "Assessment", "CIT(A)", "ITAT", "HC", "SC"];
const STATUSES = ["Ongoing", "Closed", "Completed"];
const ACTS = ["Income Tax Act, 1961", "Income Tax Act, 2025"];
const ENTITY_TYPES = ["Individual", "Company", "Partnership Firm", "LLP"];
const DEMAND_TYPES = ["Raised", "Estimated"];

const DEFAULT_NATURE = [
  "Assessment Proceedings", "Appellate Proceedings – CIT(A)", "Appellate Proceedings – ITAT",
  "Appellate Proceedings – High Court", "Appellate Proceedings – Supreme Court",
  "Demand Recovery Proceedings", "Refund Proceedings", "Rectification Proceedings (154)",
  "Revision Proceedings (263/264)", "Penalty Proceedings", "Reassessment Proceedings (147/148)",
  "Transfer Pricing Proceedings", "Survey/Search Related Proceedings", "Other Proceedings"
];

const DEFAULT_TEMPLATES = [
  "Filing of Return of Income", "Tax Audit Report Filing (Form 3CA/3CB-3CD)",
  "Response to Notice u/s 143(2)", "Response to Notice u/s 142(1)",
  "Filing of Appeal before CIT(A)", "Filing of Appeal before ITAT",
  "Rectification Application u/s 154", "Stay of Demand Application",
  "Lower/Nil TDS Certificate Application", "Advance Tax Computation & Compliance",
  "Transfer Pricing Study/Report", "Response to Reassessment Notice u/s 148"
];

const STATUS_COLOR = { Ongoing: "var(--amber)", Closed: "var(--slate)", Completed: "var(--emerald)" };
const CHART_COLORS = ["#14213D", "#1F7A5C", "#C97A2B", "#A83B2E", "#A8823C", "#5B7A99", "#7C8A6E", "#8E6C8A"];

const PAN_RE = /^[A-Za-z]{5}[0-9]{4}[A-Za-z]$/;

/* ============================== API HELPERS ============================== */

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let body = null;
  try { body = await response.json(); } catch { body = null; }
  if (!response.ok) throw new Error(body?.error || `Request failed (${response.status})`);
  return body;
}

function uid(prefix) {
  return prefix + "_" + Math.random().toString(36).slice(2, 10);
}
function todayISO(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}
function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtINR(n) {
  const num = Number(n) || 0;
  return "₹" + num.toLocaleString("en-IN");
}
function daysFromToday(iso) {
  if (!iso) return null;
  const a = new Date(new Date().toDateString());
  const b = new Date(iso + "T00:00:00");
  return Math.round((b - a) / 86400000);
}

/* ============================== SEED DATA ============================== */

function makeSeedDb() {
  const groups = [
    { group_id: "GRP001", group_name: "Sharma Family & Enterprises Group" },
    { group_id: "GRP002", group_name: "Nexa Industries Group" }
  ];
  const companies = [
    { company_id: "C001", group_id: "GRP001", entity_name: "Rohit Sharma", entity_type: "Individual", pan: "ABCDE1234F" },
    { company_id: "C002", group_id: "GRP001", entity_name: "Sharma Textiles Pvt Ltd", entity_type: "Company", pan: "ABCDE5678G" },
    { company_id: "C003", group_id: "GRP001", entity_name: "Sharma & Sons LLP", entity_type: "LLP", pan: "ABCDE9012H" },
    { company_id: "C004", group_id: "GRP002", entity_name: "Nexa Industries Ltd", entity_type: "Company", pan: "NEXAI1234K" },
    { company_id: "C005", group_id: "GRP002", entity_name: "Nexa Infra Partners", entity_type: "Partnership Firm", pan: "NEXAP5678L" }
  ];
  const users = [
    { user_id: "admin", name: "Admin (Consultant)", email: "admin@taxconsult.in", passwordHash: "e86f78a8a3caf0b60d8e74e5942aa6d86dc150cd3c03338aef25b7d2d7e3acc7", role: "Admin", group_id: null, status: "Active", created_at: todayISO(-120) },
    { user_id: "sharma_user", name: "Rohit Sharma", email: "rohit@sharmagroup.in", passwordHash: "3e7c19576488862816f13b512cacf3e4ba97dd97243ea0bd6a2ad1642d86ba72", role: "GroupUser", group_id: "GRP001", status: "Active", created_at: todayISO(-90) },
    { user_id: "nexa_user", name: "Priya Menon", email: "priya@nexaindustries.in", passwordHash: "3e7c19576488862816f13b512cacf3e4ba97dd97243ea0bd6a2ad1642d86ba72", role: "GroupUser", group_id: "GRP002", status: "Active", created_at: todayISO(-60) }
  ];
  const invitedEmails = [
    { email: "cfo@nexaindustries.in", group_id: "GRP002", invited_by: "admin", used: false }
  ];
  return { groups, companies, users, invitedEmails, masterNature: [...DEFAULT_NATURE], masterTemplates: [...DEFAULT_TEMPLATES] };
}

function makeSeedProceedings() {
  const base = [
    { company_id: "C001", group_id: "GRP001", ay: "2023-24", nature: "Appellate Proceedings – CIT(A)", status: "Ongoing", stage: "CIT(A)", issue: "Disallowance u/s 14A", demand: 845000, demandType: "Raised", nextHearingOffset: 4, dueOffset: 40 },
    { company_id: "C002", group_id: "GRP001", ay: "2022-23", nature: "Reassessment Proceedings (147/148)", status: "Ongoing", stage: "AO", issue: "Alleged escapement of income - unsecured loans", demand: 3120000, demandType: "Estimated", nextHearingOffset: 2, dueOffset: 15 },
    { company_id: "C002", group_id: "GRP001", ay: "2021-22", nature: "Appellate Proceedings – ITAT", status: "Ongoing", stage: "ITAT", issue: "Transfer pricing adjustment on export sales", demand: 5670000, demandType: "Raised", nextHearingOffset: 25, dueOffset: -5 },
    { company_id: "C003", group_id: "GRP001", ay: "2023-24", nature: "Rectification Proceedings (154)", status: "Completed", stage: "CPC", issue: "TDS credit mismatch rectified", demand: 0, demandType: "Raised", nextHearingOffset: null, dueOffset: -60 },
    { company_id: "C001", group_id: "GRP001", ay: "2024-25", nature: "Assessment Proceedings", status: "Ongoing", stage: "Assessment", issue: "Scrutiny - capital gains on property sale", demand: 210000, demandType: "Estimated", nextHearingOffset: 6, dueOffset: 20 },
    { company_id: "C004", group_id: "GRP002", ay: "2023-24", nature: "Appellate Proceedings – High Court", status: "Ongoing", stage: "HC", issue: "Validity of reopening beyond limitation", demand: 12500000, demandType: "Raised", nextHearingOffset: 45, dueOffset: 10 },
    { company_id: "C004", group_id: "GRP002", ay: "2022-23", nature: "Penalty Proceedings", status: "Ongoing", stage: "AO", issue: "Penalty u/s 270A on TP adjustment", demand: 980000, demandType: "Raised", nextHearingOffset: 1, dueOffset: -3 },
    { company_id: "C004", group_id: "GRP002", ay: "2024-25", nature: "Refund Proceedings", status: "Ongoing", stage: "CPC", issue: "Refund withheld pending verification", demand: 0, demandType: "Raised", nextHearingOffset: null, dueOffset: 30 },
    { company_id: "C005", group_id: "GRP002", ay: "2023-24", nature: "Demand Recovery Proceedings", status: "Ongoing", stage: "AO", issue: "Stay of demand pending appeal outcome", demand: 1450000, demandType: "Raised", nextHearingOffset: 12, dueOffset: 5 },
    { company_id: "C005", group_id: "GRP002", ay: "2021-22", nature: "Appellate Proceedings – ITAT", status: "Closed", stage: "ITAT", issue: "Depreciation on goodwill - decided in favour", demand: 0, demandType: "Raised", nextHearingOffset: null, dueOffset: -100 },
    { company_id: "C002", group_id: "GRP001", ay: "2024-25", nature: "Transfer Pricing Proceedings", status: "Ongoing", stage: "Assessment", issue: "TP study for royalty payments to AE", demand: 0, demandType: "Estimated", nextHearingOffset: 3, dueOffset: 25 },
    { company_id: "C003", group_id: "GRP001", ay: "2022-23", nature: "Survey/Search Related Proceedings", status: "Ongoing", stage: "AO", issue: "Follow-up assessment post survey u/s 133A", demand: 640000, demandType: "Estimated", nextHearingOffset: 20, dueOffset: -10 }
  ];
  const list = base.map((b, i) => {
    const fy = "20" + (20 + i % 5) + "-" + (21 + i % 5);
    return {
      s_no: i + 1,
      proceeding_id: uid("proc"),
      company_id: b.company_id,
      group_id: b.group_id,
      financial_year: yearBefore(b.ay),
      assessment_year: b.ay,
      tax_year: null,
      applicable_act: "Income Tax Act, 1961",
      relevant_section: sectionFor(b.nature),
      nature_of_proceeding: b.nature,
      proceeding_status: b.status,
      stage_of_proceeding: b.stage,
      issue_involved: b.issue,
      tax_demand_amount: b.demand,
      demand_type: b.demandType,
      demand_reference: b.demand > 0 ? (b.demandType === "Raised" ? "Demand / Order Ref. — Demo" : "Notice / Estimate Ref. — Demo") : "",
      demand_date: b.demand > 0 ? todayISO(-15) : null,
      estimated_demand_basis: b.demandType === "Estimated" ? "Departmental estimate / working assessment under monitoring." : "",
      description_of_matter: b.issue + ". Matter under active monitoring; refer remarks for latest update.",
      last_hearing_date: b.nextHearingOffset != null ? todayISO(b.nextHearingOffset - 30) : todayISO(-45),
      next_hearing_date: b.nextHearingOffset != null ? todayISO(b.nextHearingOffset) : null,
      proceeding_timeline_due_date: todayISO(b.dueOffset),
      consultant_name: "Admin (Consultant)",
      consultant_contact: "+91-98xxxxxx01",
      remarks: "Awaiting further correspondence from the department.",
      created_by: "admin",
      updated_by: "admin",
      created_at: todayISO(-30),
      updated_at: todayISO(-2),
      history: []
    };
  });
  return { list, nextSNo: list.length + 1 };
}
function yearBefore(ay) {
  const [a] = ay.split("-");
  const start = parseInt(a, 10) - 1;
  return start + "-" + String(start + 1).slice(2);
}
function sectionFor(nature) {
  if (nature.includes("154")) return "154";
  if (nature.includes("147/148")) return "147/148";
  if (nature.includes("263")) return "263";
  if (nature.includes("270A")) return "270A";
  if (nature.includes("CIT(A)")) return "246A";
  if (nature.includes("ITAT")) return "253";
  return "143(3)";
}

/* ============================== SMALL UI ATOMS ============================== */

function Stamp({ text, tone = "ink" }) {
  const toneColor = { ink: "var(--ink)", amber: "var(--amber)", emerald: "var(--emerald)", rust: "var(--rust)", slate: "var(--slate)" }[tone];
  return (
    <span className="stamp" style={{ color: toneColor, borderColor: toneColor }}>{text}</span>
  );
}

function StatusStamp({ status }) {
  const tone = status === "Ongoing" ? "amber" : status === "Completed" ? "emerald" : "slate";
  return <Stamp text={status} tone={tone} />;
}

function Card({ children, style, className = "" }) {
  return <div className={"lt-card " + className} style={style}>{children}</div>;
}

function Btn({ children, onClick, variant = "primary", size = "md", type = "button", disabled, title }) {
  return (
    <button type={type} title={title} disabled={disabled} onClick={onClick} className={`lt-btn lt-btn-${variant} lt-btn-${size}`}>
      {children}
    </button>
  );
}

function Field({ label, children, required, hint }) {
  return (
    <label className="lt-field">
      <span className="lt-field-label">{label}{required && <span style={{ color: "var(--rust)" }}> *</span>}</span>
      {children}
      {hint && <span className="lt-field-hint">{hint}</span>}
    </label>
  );
}

function Select({ value, onChange, options, placeholder, disabled }) {
  return (
    <select className="lt-input" value={value || ""} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((o) => (typeof o === "string" ? <option key={o} value={o}>{o}</option> : <option key={o.value} value={o.value}>{o.label}</option>))}
    </select>
  );
}

function Modal({ title, onClose, children, wide }) {
  return (
    <div className="lt-modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className={"lt-modal" + (wide ? " lt-modal-wide" : "")}>
        <div className="lt-modal-head">
          <h3>{title}</h3>
          <button className="lt-icon-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="lt-modal-body">{children}</div>
      </div>
    </div>
  );
}

function ConfirmDialog({ text, onConfirm, onCancel }) {
  return (
    <Modal title="Please confirm" onClose={onCancel}>
      <p style={{ color: "var(--slate)", marginBottom: 20 }}>{text}</p>
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <Btn variant="ghost" onClick={onCancel}>Cancel</Btn>
        <Btn variant="danger" onClick={onConfirm}>Confirm</Btn>
      </div>
    </Modal>
  );
}

function StatCard({ icon, label, value, sub, tone }) {
  return (
    <Card className="lt-stat">
      <div className="lt-stat-icon" style={{ background: tone || "var(--ink)" }}>{icon}</div>
      <div>
        <div className="lt-stat-value">{value}</div>
        <div className="lt-stat-label">{label}</div>
        {sub && <div className="lt-stat-sub">{sub}</div>}
      </div>
    </Card>
  );
}

/* ============================== ROOT APP ============================== */

export default function LitigationTracker() {
  const [loading, setLoading] = useState(true);
  const [db, setDb] = useState(null);
  const [proc, setProc] = useState(null);
  const [sessionUserId, setSessionUserId] = useState(null);
  const [authScreen, setAuthScreen] = useState("login");
  const [toast, setToast] = useState(null);

  useEffect(() => { init(); }, []);

  async function init() {
    try {
      const data = await api("/api/bootstrap");
      setDb(data.db); setProc(data.proc); setSessionUserId(data.user.user_id);
    } catch (e) {
      setDb(null); setProc(null); setSessionUserId(null);
    } finally {
      setLoading(false);
    }
  }

  const persistDb = useCallback(async (next) => {
    try {
      const data = await api("/api/admin/state", { method: "PUT", body: JSON.stringify(next) });
      setDb(data.db);
    } catch (e) { console.error("API error:", e); throw e; }
  }, []);

  const persistProc = useCallback(async (next) => {
    try {
      const data = await api("/api/proceedings/state", { method: "PUT", body: JSON.stringify(next) });
      setProc(data.proc);
    } catch (e) { console.error("API error:", e); throw e; }
  }, []);

  const logAuth = useCallback(async () => {}, []);

  function notify(msg, tone = "ok") {
    setToast({ msg, tone });
    setTimeout(() => setToast(null), 3200);
  }

  const currentUser = useMemo(() => {
    if (!db || !sessionUserId) return null;
    return db.users.find((u) => u.user_id === sessionUserId) || null;
  }, [db, sessionUserId]);

  async function doLogin(userId, password) {
    try {
      const data = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ userId, password }) });
      setDb(data.db); setProc(data.proc); setSessionUserId(data.user.user_id);
      notify(`Welcome back, ${data.user.name.split(" ")[0]}.`);
    } catch (e) { notify(e.message, "error"); }
  }

  async function doLogout() {
    try { await api("/api/auth/logout", { method: "POST" }); } catch {}
    setSessionUserId(null); setDb(null); setProc(null);
  }

  async function doSignup({ name, email, userId, password }) {
    try {
      const data = await api("/api/auth/signup", { method: "POST", body: JSON.stringify({ name, email, userId, password }) });
      setDb(data.db); setProc(data.proc); setSessionUserId(data.user.user_id);
      notify(`Account created. Welcome aboard, ${data.user.name.split(" ")[0]}!`);
    } catch (e) { notify(e.message, "error"); }
  }

  if (loading) return <LoadingScreen />;

  if (!currentUser) {
    return (
      <div className="lt-root">
        <GlobalStyle />
        {authScreen === "login"
          ? <LoginScreen onLogin={doLogin} onSwitch={() => setAuthScreen("signup")} toast={toast} />
          : <SignupScreen onSignup={doSignup} onSwitch={() => setAuthScreen("login")} toast={toast} />}
      </div>
    );
  }

  return (
    <div className="lt-root">
      <GlobalStyle />
      <MainApp
        db={db} proc={proc} currentUser={currentUser}
        persistDb={persistDb} persistProc={persistProc}
        onLogout={doLogout} notify={notify} toast={toast}
      />
    </div>
  );
}

function LoadingScreen() {
  return (
    <div style={{ minHeight: 420, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Inter, sans-serif", color: "#14213D" }}>
      <GlobalStyle />
      <div style={{ textAlign: "center" }}>
        <div className="lt-spinner" />
        <div style={{ marginTop: 14, fontSize: 14, color: "#6B7280" }}>Opening the case files…</div>
      </div>
    </div>
  );
}

/* ============================== AUTH SCREENS ============================== */

function AuthShell({ children, footer }) {
  return (
    <div className="lt-auth-wrap">
      <div className="lt-auth-side">
        <div className="lt-auth-brand">
          <Stamp text="LT" tone="ink" />
          <div>
            <div className="lt-auth-title">Litigation Tracker</div>
            <div className="lt-auth-sub">Direct Tax proceedings, by group, by year, in one file room.</div>
          </div>
        </div>
        <ul className="lt-auth-points">
          <li><ShieldCheck size={16} /> Role-based access — each client group sees only its own matters</li>
          <li><Clock size={16} /> Never miss a hearing — 7-day and overdue alerts on the dashboard</li>
          <li><IndianRupee size={16} /> Track demand outstanding across every entity and year</li>
        </ul>
        <div style={{ marginTop: 14, fontSize: 11.5, lineHeight: 1.5, color: "#6B7280" }}>Privacy-first application: data is processed by the local application server and stored in the local SQLite database; no AI or external cloud API is configured.</div>
        <div className="lt-auth-demo">
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Try it instantly</div>
          <div>Admin — <code>admin</code> / <code>Admin@123</code></div>
          <div>Group user — <code>sharma_user</code> / <code>User@123</code></div>
        </div>
      </div>
      <div className="lt-auth-form-side">
        <div className="lt-auth-card">{children}</div>
        {footer}
      </div>
    </div>
  );
}

function LoginScreen({ onLogin, onSwitch, toast }) {
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  return (
    <AuthShell footer={
      <div className="lt-auth-switch">New client group? <button onClick={onSwitch}>Create an account</button></div>
    }>
      <h2>Sign in</h2>
      <p className="lt-auth-lead">Enter the User ID your consultant gave you.</p>
      {toast && <Toast toast={toast} />}
      <form onSubmit={(e) => { e.preventDefault(); onLogin(userId.trim(), password); }}>
        <Field label="User ID" required>
          <input className="lt-input" autoFocus value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="e.g. admin" />
        </Field>
        <Field label="Password" required>
          <input className="lt-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        </Field>
        <Btn type="submit" size="lg">Sign in</Btn>
      </form>
    </AuthShell>
  );
}

function SignupScreen({ onSignup, onSwitch, toast }) {
  const [form, setForm] = useState({ name: "", email: "", userId: "", password: "" });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  return (
    <AuthShell footer={
      <div className="lt-auth-switch">Already have an account? <button onClick={onSwitch}>Sign in</button></div>
    }>
      <h2>Create account</h2>
      <p className="lt-auth-lead">Your email must already be on the Admin's invite list — unless you're the very first person setting this workspace up.</p>
      {toast && <Toast toast={toast} />}
      <form onSubmit={(e) => { e.preventDefault(); if (form.name && form.email && form.userId && form.password) onSignup(form); }}>
        <Field label="Full name" required><input className="lt-input" value={form.name} onChange={set("name")} /></Field>
        <Field label="Email" required><input className="lt-input" type="email" value={form.email} onChange={set("email")} /></Field>
        <Field label="Choose a User ID" required><input className="lt-input" value={form.userId} onChange={set("userId")} /></Field>
        <Field label="Choose a password" required><input className="lt-input" type="password" value={form.password} onChange={set("password")} /></Field>
        <Btn type="submit" size="lg">Create account</Btn>
      </form>
    </AuthShell>
  );
}

function Toast({ toast }) {
  return <div className={"lt-toast lt-toast-" + toast.tone}>{toast.msg}</div>;
}

/* ============================== MAIN APP SHELL ============================== */

const NAV = [
  { key: "dashboard", label: "Litigation Dashboard", icon: LayoutDashboard, adminOnly: false },
  { key: "proceedings", label: "Proceedings", icon: FileText, adminOnly: false },
  { key: "companies", label: "Tax Entities", icon: Building2, adminOnly: true },
  { key: "users", label: "User Access", icon: UsersIcon, adminOnly: true },
  { key: "master", label: "Master Data", icon: ListChecks, adminOnly: true }
];

function MainApp({ db, proc, currentUser, persistDb, persistProc, onLogout, notify, toast }) {
  const [tab, setTab] = useState("dashboard");
  const [navOpen, setNavOpen] = useState(false);
  const isAdmin = currentUser.role === "Admin";
  const group = db.groups.find((g) => g.group_id === currentUser.group_id);

  const scopedProceedings = useMemo(() => {
    if (isAdmin) return proc.list;
    return proc.list.filter((p) => p.group_id === currentUser.group_id);
  }, [proc, isAdmin, currentUser]);

  return (
    <div className="lt-shell">
      <aside className={"lt-sidebar" + (navOpen ? " lt-sidebar-open" : "")}>
        <div className="lt-sidebar-brand">
          <Stamp text="LT" tone="ink" />
          <span>Litigation Tracker</span>
        </div>
        <nav>
          {NAV.filter((n) => !n.adminOnly || isAdmin).map((n) => (
            <button key={n.key} className={"lt-nav-item" + (tab === n.key ? " active" : "")} onClick={() => { setTab(n.key); setNavOpen(false); }}>
              <n.icon size={17} /> {n.label}
            </button>
          ))}
        </nav>
        <div className="lt-sidebar-foot">
          <div className="lt-user-chip">
            <div className="lt-user-avatar">{currentUser.name.split(" ").map((s) => s[0]).slice(0, 2).join("")}</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{currentUser.name}</div>
              <div style={{ fontSize: 11, color: "#9CA3AF" }}>{isAdmin ? "Admin" : (group ? group.group_name : "Group user")}</div>
            </div>
          </div>
          <button className="lt-nav-item" onClick={onLogout}><LogOut size={16} /> Log out</button>
        </div>
      </aside>

      <div className="lt-main">
        <header className="lt-topbar">
          <button className="lt-icon-btn lt-only-mobile" onClick={() => setNavOpen((v) => !v)}><Menu size={20} /></button>
          <div className="lt-topbar-title">{NAV.find((n) => n.key === tab)?.label}</div>
          <div className="lt-topbar-badge">
            {isAdmin ? <Stamp text="Admin · All groups" tone="ink" /> : <Stamp text={group ? group.group_name : "Group"} tone="slate" />}
          </div>
        </header>
        <main className="lt-content">
          {toast && <Toast toast={toast} />}
          {tab === "dashboard" && <Dashboard db={db} proceedings={scopedProceedings} isAdmin={isAdmin} />}
          {tab === "proceedings" && (
            <ProceedingsScreen db={db} proc={proc} persistProc={persistProc} currentUser={currentUser} isAdmin={isAdmin} scoped={scopedProceedings} notify={notify} />
          )}
          {tab === "companies" && isAdmin && <CompaniesScreen db={db} persistDb={persistDb} notify={notify} />}
          {tab === "users" && isAdmin && <UsersScreen db={db} persistDb={persistDb} currentUser={currentUser} notify={notify} />}
          {tab === "master" && isAdmin && <MasterListsScreen db={db} persistDb={persistDb} notify={notify} />}
        </main>
      </div>
    </div>
  );
}

/* ============================== DASHBOARD ============================== */

function Dashboard({ db, proceedings, isAdmin }) {
  const [filters, setFilters] = useState({ group_id: "", company_id: "", ay: "", nature: "", status: "", stage: "", act: "" });

  const companiesInScope = useMemo(
    () => (filters.group_id ? db.companies.filter((c) => c.group_id === filters.group_id) : db.companies),
    [db, filters.group_id]
  );

  const filtered = useMemo(() => proceedings.filter((p) => {
    if (filters.group_id && p.group_id !== filters.group_id) return false;
    if (filters.company_id && p.company_id !== filters.company_id) return false;
    if (filters.ay && p.assessment_year !== filters.ay) return false;
    if (filters.nature && p.nature_of_proceeding !== filters.nature) return false;
    if (filters.status && p.proceeding_status !== filters.status) return false;
    if (filters.stage && p.stage_of_proceeding !== filters.stage) return false;
    if (filters.act && p.applicable_act !== filters.act) return false;
    return true;
  }), [proceedings, filters]);

  const companyName = (id) => db.companies.find((c) => c.company_id === id)?.entity_name || id;
  const groupName = (id) => db.groups.find((g) => g.group_id === id)?.group_name || id;

  const ongoing = filtered.filter((p) => p.proceeding_status === "Ongoing");
  const closed = filtered.filter((p) => p.proceeding_status === "Closed");
  const completed = filtered.filter((p) => p.proceeding_status === "Completed");
  const totalRaisedDemand = ongoing.filter((p) => p.demand_type === "Raised").reduce((s, p) => s + (Number(p.tax_demand_amount) || 0), 0);
  const totalEstimatedDemand = ongoing.filter((p) => p.demand_type === "Estimated").reduce((s, p) => s + (Number(p.tax_demand_amount) || 0), 0);
  const totalDemand = totalRaisedDemand + totalEstimatedDemand;
  const next7 = filtered.filter((p) => p.next_hearing_date && daysFromToday(p.next_hearing_date) >= 0 && daysFromToday(p.next_hearing_date) <= 7);
  const next30 = filtered.filter((p) => p.next_hearing_date && daysFromToday(p.next_hearing_date) >= 0 && daysFromToday(p.next_hearing_date) <= 30);
  const overdue = filtered.filter((p) => p.proceeding_timeline_due_date && daysFromToday(p.proceeding_timeline_due_date) < 0 && p.proceeding_status === "Ongoing");
  const highDemand = [...ongoing].sort((a, b) => Number(b.tax_demand_amount || 0) - Number(a.tax_demand_amount || 0)).slice(0, 4);
  const raisedDemand = ongoing.filter((p) => p.demand_type === "Raised").reduce((s, p) => s + (Number(p.tax_demand_amount) || 0), 0);
  const estimatedDemand = ongoing.filter((p) => p.demand_type === "Estimated").reduce((s, p) => s + (Number(p.tax_demand_amount) || 0), 0);

  const byGroup = useMemo(() => {
    const m = {};
    filtered.forEach((p) => { m[p.group_id] = (m[p.group_id] || 0) + 1; });
    return Object.entries(m).map(([k, v]) => ({ name: groupName(k), value: v }));
  }, [filtered, db]);

  const byCompany = useMemo(() => {
    const m = {};
    filtered.forEach((p) => { m[p.company_id] = (m[p.company_id] || 0) + 1; });
    return Object.entries(m).map(([k, v]) => ({ name: companyName(k), value: v }));
  }, [filtered, db]);

  const byNature = useMemo(() => {
    const m = {};
    filtered.forEach((p) => { m[p.nature_of_proceeding] = (m[p.nature_of_proceeding] || 0) + 1; });
    return Object.entries(m).map(([k, v]) => ({ name: k, value: v }));
  }, [filtered]);

  const byStage = useMemo(() => {
    const m = {};
    STAGES.forEach((s) => (m[s] = 0));
    filtered.forEach((p) => { m[p.stage_of_proceeding] = (m[p.stage_of_proceeding] || 0) + 1; });
    return Object.entries(m).map(([k, v]) => ({ name: k, value: v }));
  }, [filtered]);

  const byStatus = [
    { name: "Ongoing", value: ongoing.length },
    { name: "Closed", value: closed.length },
    { name: "Completed", value: completed.length }
  ];

  const byYear = useMemo(() => {
    const m = {};
    filtered.forEach((p) => {
      const y = p.assessment_year || "—";
      if (!m[y]) m[y] = { name: y, count: 0, demand: 0 };
      m[y].count += 1;
      m[y].demand += Number(p.tax_demand_amount) || 0;
    });
    return Object.values(m).sort((a, b) => a.name.localeCompare(b.name));
  }, [filtered]);

  const clearFilters = () => setFilters({ group_id: "", company_id: "", ay: "", nature: "", status: "", stage: "", act: "" });
  const hasFilters = Object.values(filters).some(Boolean);
  const filterLabel = hasFilters ? "Filtered proceedings" : "Litigation Dashboard";

  return (
    <div className="lt-dashboard">
      <section className="lt-dashboard-hero">
        <div>
          <div className="lt-eyebrow">DIRECT TAX PROCEEDINGS</div>
          <h2 className="lt-dashboard-title">{filterLabel}</h2>
          <p className="lt-dashboard-subtitle">
            {isAdmin ? "Centralized monitoring of assessment, appellate, recovery and other direct-tax proceedings across client groups, entities and assessment years." : "Monitor assessments, appeals, hearings, demands and procedural timelines for your client group."}
          </p>
        </div>
        <div className="lt-dashboard-hero-meta">
          <div className="lt-live-dot"><span /> Live data</div>
          <div className="lt-hero-caption">{filtered.length} matters in current view</div>
        </div>
      </section>

      <Card className="lt-filterbar lt-filterbar-premium">
        <div className="lt-filter-label"><span>Filter proceedings</span><small>Refine by group, entity, year, nature, stage or Act</small></div>
        {isAdmin && <Select value={filters.group_id} onChange={(v) => setFilters((f) => ({ ...f, group_id: v, company_id: "" }))} options={db.groups.map((g) => ({ value: g.group_id, label: g.group_name }))} placeholder="All groups" />}
        <Select value={filters.company_id} onChange={(v) => setFilters((f) => ({ ...f, company_id: v }))} options={companiesInScope.map((c) => ({ value: c.company_id, label: c.entity_name }))} placeholder="All companies" />
        <input className="lt-input" placeholder="Assessment year" value={filters.ay} onChange={(e) => setFilters((f) => ({ ...f, ay: e.target.value }))} style={{ maxWidth: 160 }} />
        <Select value={filters.nature} onChange={(v) => setFilters((f) => ({ ...f, nature: v }))} options={db.masterNature} placeholder="All natures" />
        <Select value={filters.status} onChange={(v) => setFilters((f) => ({ ...f, status: v }))} options={STATUSES} placeholder="All statuses" />
        <Select value={filters.stage} onChange={(v) => setFilters((f) => ({ ...f, stage: v }))} options={STAGES} placeholder="All stages" />
        <Select value={filters.act} onChange={(v) => setFilters((f) => ({ ...f, act: v }))} options={ACTS} placeholder="All Acts" />
        {hasFilters && <button className="lt-link-btn" onClick={clearFilters}>Clear filters</button>}
      </Card>

      <section className="lt-dashboard-kpis">
        <div className="lt-kpi lt-kpi-ink">
          <div className="lt-kpi-top"><span className="lt-kpi-icon"><FileText size={18} /></span><span className="lt-kpi-tag">Case Register</span></div>
          <div className="lt-kpi-value">{filtered.length}</div>
          <div className="lt-kpi-label">Total proceedings</div>
          <div className="lt-kpi-foot"><span>{completed.length} completed</span><span>{closed.length} closed</span></div>
        </div>
        <div className="lt-kpi lt-kpi-amber">
          <div className="lt-kpi-top"><span className="lt-kpi-icon"><Clock size={18} /></span><span className="lt-kpi-tag">Live Matters</span></div>
          <div className="lt-kpi-value">{ongoing.length}</div>
          <div className="lt-kpi-label">Ongoing proceedings</div>
          <div className="lt-kpi-foot"><span>{next7.length} hearings in 7 days</span><span>{next30.length} in 30 days</span></div>
        </div>
        <div className="lt-kpi lt-kpi-rust">
          <div className="lt-kpi-top"><span className="lt-kpi-icon"><IndianRupee size={18} /></span><span className="lt-kpi-tag">Tax Demand</span></div>
          <div className="lt-kpi-value lt-kpi-value-compact">{fmtINR(totalDemand)}</div>
          <div className="lt-kpi-label">Tax demand tracked</div>
          <div className="lt-kpi-foot"><span>Raised: {fmtINR(totalRaisedDemand)}</span><span>Estimated: {fmtINR(totalEstimatedDemand)}</span></div>
        </div>
        <div className="lt-kpi lt-kpi-emerald">
          <div className="lt-kpi-top"><span className="lt-kpi-icon"><AlertTriangle size={18} /></span><span className="lt-kpi-tag">Statutory Alerts</span></div>
          <div className="lt-kpi-value">{overdue.length}</div>
          <div className="lt-kpi-label">Overdue / statutory alerts</div>
          <div className="lt-kpi-foot"><span className={overdue.length ? "lt-foot-alert" : ""}>{overdue.length ? "Action required" : "No overdue items"}</span></div>
        </div>
      </section>

      <section className="lt-dashboard-insight-strip">
        <div className="lt-insight-label"><span className="lt-insight-kicker">TAX DEMAND CLASSIFICATION</span><strong>Current demand position</strong><small>Outstanding demand in ongoing proceedings</small></div>
        <div className="lt-insight-metric"><span>Raised demand</span><strong>{fmtINR(raisedDemand)}</strong></div>
        <div className="lt-insight-metric"><span>Estimated demand</span><strong>{fmtINR(estimatedDemand)}</strong></div>
        <div className="lt-insight-metric lt-insight-total"><span>Total demand tracked</span><strong>{fmtINR(totalDemand)}</strong></div>
      </section>

      <section className="lt-stage-rail">
        <div className="lt-stage-rail-head"><div><div className="lt-card-kicker">LITIGATION PROGRESSION</div><h4>Proceedings by stage</h4></div><span className="lt-card-chip">CPC → AO → CIT(A) → ITAT → HC → SC</span></div>
        <div className="lt-stage-items">
          {byStage.map((item) => (
            <div className={"lt-stage-item" + (item.value ? " has-value" : "")} key={item.name}>
              <span className="lt-stage-code">{item.name}</span><strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="lt-dashboard-grid lt-dashboard-grid-top">
        <Card className="lt-dashboard-card lt-dashboard-card-wide">
          <div className="lt-card-heading-row">
            <div>
              <div className="lt-card-kicker">ASSESSMENT YEAR</div>
              <h4>Assessment Year-wise Proceedings & Demand</h4>
            </div>
            <span className="lt-card-chip">AY trend</span>
          </div>
          <ResponsiveContainer width="100%" height={290}>
            <LineChart data={byYear} margin={{ top: 8, right: 12, left: -12, bottom: 4 }}>
              <defs>
                <linearGradient id="ltDemandFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#A83B2E" stopOpacity={0.20} />
                  <stop offset="100%" stopColor="#A83B2E" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="4 4" stroke="#ECE7DA" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#7A8290" }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="l" allowDecimals={false} tick={{ fontSize: 11, fill: "#7A8290" }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="r" orientation="right" tick={{ fontSize: 11, fill: "#7A8290" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #E6E0D2", boxShadow: "0 12px 30px rgba(20,33,61,.10)" }} formatter={(v, n) => (n === "demand" ? fmtINR(v) : v)} />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
              <Line yAxisId="l" type="monotone" dataKey="count" name="Proceedings" stroke="#14213D" strokeWidth={3} dot={{ r: 3, strokeWidth: 2, fill: "#fff" }} activeDot={{ r: 5 }} />
              <Line yAxisId="r" type="monotone" dataKey="demand" name="Demand" stroke="#A83B2E" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card className="lt-dashboard-card">
          <div className="lt-card-heading-row">
            <div>
              <div className="lt-card-kicker">PROCEEDING STATUS</div>
              <h4>Status of Proceedings</h4>
            </div>
            <span className="lt-card-chip">Current status</span>
          </div>
          <div className="lt-status-panel">
            <div className="lt-donut-wrap">
              <ResponsiveContainer width="100%" height={190}>
                <PieChart>
                  <Pie data={byStatus} dataKey="value" nameKey="name" outerRadius={70} innerRadius={49} paddingAngle={3}>
                    {byStatus.map((e, i) => <Cell key={i} fill={[STATUS_COLOR.Ongoing, STATUS_COLOR.Closed, STATUS_COLOR.Completed][i]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #E6E0D2" }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="lt-donut-center"><strong>{filtered.length}</strong><span>matters</span></div>
            </div>
            <div className="lt-status-list">
              <div><span className="lt-status-dot" style={{ background: STATUS_COLOR.Ongoing }} /> <span>Ongoing</span><strong>{ongoing.length}</strong></div>
              <div><span className="lt-status-dot" style={{ background: STATUS_COLOR.Completed }} /> <span>Completed</span><strong>{completed.length}</strong></div>
              <div><span className="lt-status-dot" style={{ background: STATUS_COLOR.Closed }} /> <span>Closed</span><strong>{closed.length}</strong></div>
            </div>
          </div>
          <div className="lt-health-callout"><ShieldCheck size={16} /><span>Use the filters above to review status, stage and timelines for a specific group or entity.</span></div>
        </Card>
      </section>

      <section className="lt-dashboard-grid lt-dashboard-grid-mid">
        {isAdmin && (
          <Card className="lt-dashboard-card">
            <div className="lt-card-heading-row"><div><div className="lt-card-kicker">CLIENT GROUPS</div><h4>Group-wise Proceedings</h4></div></div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={byGroup} margin={{ left: -18, right: 8 }}>
                <CartesianGrid strokeDasharray="4 4" stroke="#ECE7DA" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#7A8290" }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#7A8290" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #E6E0D2" }} />
                <Bar dataKey="value" fill="#14213D" radius={[8, 8, 0, 0]} barSize={42} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        )}
        <Card className="lt-dashboard-card">
          <div className="lt-card-heading-row"><div><div className="lt-card-kicker">PROCEEDING STAGE</div><h4>Stage-wise Proceedings</h4></div></div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={byStage} margin={{ left: -18, right: 8 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#ECE7DA" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#7A8290" }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#7A8290" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #E6E0D2" }} />
              <Bar dataKey="value" fill="#A8823C" radius={[8, 8, 0, 0]} barSize={34} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card className="lt-dashboard-card">
          <div className="lt-card-heading-row"><div><div className="lt-card-kicker">TAX ENTITIES</div><h4>Entity-wise Proceedings</h4></div></div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={byCompany} layout="vertical" margin={{ left: 10, right: 8 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#ECE7DA" horizontal={false} />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 10, fill: "#7A8290" }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 10, fill: "#7A8290" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #E6E0D2" }} />
              <Bar dataKey="value" fill="#5B7A99" radius={[0, 8, 8, 0]} barSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </section>

      <section className="lt-dashboard-grid lt-dashboard-grid-bottom">
        <Card className="lt-dashboard-card">
          <div className="lt-card-heading-row"><div><div className="lt-card-kicker">HEARING CALENDAR</div><h4>Hearings in the Next 7 Days</h4></div><span className="lt-count-pill">{next7.length}</span></div>
          {next7.length === 0 ? <Empty text="Nothing on the calendar in the next 7 days." /> : (
            <div className="lt-priority-list">
              {[...next7].sort((a, b) => a.next_hearing_date.localeCompare(b.next_hearing_date)).map((p) => (
                <div className="lt-priority-row" key={p.proceeding_id}>
                  <div className="lt-priority-marker lt-marker-amber"><Clock size={15} /></div>
                  <div className="lt-priority-main"><strong>{companyName(p.company_id)}</strong><span>{p.issue_involved}</span></div>
                  <div className="lt-priority-meta"><strong>{fmtDate(p.next_hearing_date)}</strong><span>{p.stage_of_proceeding}</span></div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="lt-dashboard-card">
          <div className="lt-card-heading-row"><div><div className="lt-card-kicker">STATUTORY ACTION</div><h4>Overdue / Action Required</h4></div><span className={overdue.length ? "lt-count-pill lt-count-pill-danger" : "lt-count-pill"}>{overdue.length}</span></div>
          {overdue.length === 0 ? <Empty text="No open proceedings are past their due date." /> : (
            <div className="lt-priority-list">
              {[...overdue].sort((a, b) => a.proceeding_timeline_due_date.localeCompare(b.proceeding_timeline_due_date)).map((p) => (
                <div className="lt-priority-row" key={p.proceeding_id}>
                  <div className="lt-priority-marker lt-marker-rust"><AlertTriangle size={15} /></div>
                  <div className="lt-priority-main"><strong>{companyName(p.company_id)}</strong><span>{p.issue_involved}</span></div>
                  <div className="lt-priority-meta lt-danger-text"><strong>{Math.abs(daysFromToday(p.proceeding_timeline_due_date))} days</strong><span>{fmtDate(p.proceeding_timeline_due_date)}</span></div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="lt-dashboard-card">
          <div className="lt-card-heading-row"><div><div className="lt-card-kicker">DEMAND MONITOR</div><h4>Highest Demand Proceedings</h4></div><span className="lt-count-pill">Top {Math.min(4, highDemand.length)}</span></div>
          {highDemand.length === 0 ? <Empty text="No demand exposure in the current view." /> : (
            <div className="lt-demand-list">
              {highDemand.map((p) => (
                <div className="lt-demand-row" key={p.proceeding_id}>
                  <div className="lt-demand-company"><strong>{companyName(p.company_id)}</strong><span>{p.assessment_year} · {p.stage_of_proceeding}</span></div>
                  <div className="lt-demand-value">{fmtINR(p.tax_demand_amount)}</div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>

      <Card className="lt-dashboard-card lt-nature-card">
        <div className="lt-card-heading-row"><div><div className="lt-card-kicker">PROCEEDING NATURE</div><h4>Nature of Proceedings</h4></div><span className="lt-card-chip">Matter mix</span></div>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie data={byNature} dataKey="value" nameKey="name" outerRadius={86} innerRadius={40} paddingAngle={2}>
              {byNature.map((e, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #E6E0D2" }} />
            <Legend wrapperStyle={{ fontSize: 11.5 }} />
          </PieChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}

function Empty({ text }) {
  return <div className="lt-empty">{text}</div>;
}

/* ============================== PROCEEDINGS SCREEN ============================== */

function ProceedingsScreen({ db, proc, persistProc, currentUser, isAdmin, scoped, notify }) {
  const [filters, setFilters] = useState({ group_id: "", company_id: "", ay: "", nature: "", status: "", stage: "", act: "", q: "" });
  const [sortKey, setSortKey] = useState("next_hearing_date");
  const [sortDir, setSortDir] = useState("asc");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null); // proceeding object or "new"
  const [historyFor, setHistoryFor] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [remarksDraft, setRemarksDraft] = useState({});
  const pageSize = 8;

  const companiesInScope = useMemo(() => (filters.group_id ? db.companies.filter((c) => c.group_id === filters.group_id) : db.companies), [db, filters.group_id]);

  const filtered = useMemo(() => {
    let rows = scoped.filter((p) => {
      if (filters.group_id && p.group_id !== filters.group_id) return false;
      if (filters.company_id && p.company_id !== filters.company_id) return false;
      if (filters.ay && p.assessment_year !== filters.ay) return false;
      if (filters.nature && p.nature_of_proceeding !== filters.nature) return false;
      if (filters.status && p.proceeding_status !== filters.status) return false;
      if (filters.stage && p.stage_of_proceeding !== filters.stage) return false;
      if (filters.act && p.applicable_act !== filters.act) return false;
      if (filters.q && !(`${p.issue_involved} ${p.description_of_matter}`.toLowerCase().includes(filters.q.toLowerCase()))) return false;
      return true;
    });
    rows = [...rows].sort((a, b) => {
      const av = a[sortKey] ?? "", bv = b[sortKey] ?? "";
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return rows;
  }, [scoped, filters, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageRows = filtered.slice((page - 1) * pageSize, page * pageSize);

  const companyName = (id) => db.companies.find((c) => c.company_id === id)?.entity_name || id;
  const groupName = (id) => db.groups.find((g) => g.group_id === id)?.group_name || id;

  function toggleSort(key) {
    if (sortKey === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(key); setSortDir("asc"); }
  }

  async function saveRemarks(p) {
    const value = remarksDraft[p.proceeding_id];
    if (value === undefined || value === p.remarks) return;
    const history = [...(p.history || []), { at: new Date().toISOString(), by: currentUser.user_id, field: "remarks", from: p.remarks, to: value }];
    const nextList = proc.list.map((r) => (r.proceeding_id === p.proceeding_id ? { ...r, remarks: value, updated_by: currentUser.user_id, updated_at: todayISO(), history } : r));
    await persistProc({ ...proc, list: nextList });
    notify("Remarks updated.");
  }

  async function saveProceeding(form, isNew) {
    if (form.next_hearing_date && form.last_hearing_date && form.next_hearing_date < form.last_hearing_date) {
      notify("Next hearing date can't be before the last hearing date.", "error"); return;
    }
    if (!form.company_id || !form.assessment_year || !form.nature_of_proceeding || !form.proceeding_status || !form.stage_of_proceeding) {
      notify("Company, year, nature, status and stage are required.", "error"); return;
    }
    const company = db.companies.find((c) => c.company_id === form.company_id);
    if (isNew) {
      const row = {
        ...form,
        s_no: proc.nextSNo,
        proceeding_id: uid("proc"),
        group_id: company.group_id,
        created_by: currentUser.user_id,
        updated_by: currentUser.user_id,
        created_at: todayISO(),
        updated_at: todayISO(),
        history: []
      };
      await persistProc({ list: [row, ...proc.list], nextSNo: proc.nextSNo + 1 });
      notify("Proceeding added.");
    } else {
      const before = proc.list.find((r) => r.proceeding_id === form.proceeding_id);
      const history = [...(before.history || [])];
      Object.keys(form).forEach((k) => {
        if (form[k] !== before[k] && k !== "remarks") history.push({ at: new Date().toISOString(), by: currentUser.user_id, field: k, from: before[k], to: form[k] });
      });
      const nextList = proc.list.map((r) => (r.proceeding_id === form.proceeding_id ? { ...form, group_id: company.group_id, updated_by: currentUser.user_id, updated_at: todayISO(), history } : r));
      await persistProc({ ...proc, list: nextList });
      notify("Proceeding updated.");
    }
    setEditing(null);
  }

  async function deleteProceeding(id) {
    await persistProc({ ...proc, list: proc.list.filter((r) => r.proceeding_id !== id) });
    setConfirmDelete(null);
    notify("Proceeding deleted.");
  }

  function exportCSV() {
    const cols = ["s_no", "company_id", "group_id", "financial_year", "assessment_year", "applicable_act", "relevant_section", "nature_of_proceeding", "proceeding_status", "stage_of_proceeding", "issue_involved", "tax_demand_amount", "demand_type", "demand_reference", "demand_date", "estimated_demand_basis", "last_hearing_date", "next_hearing_date", "proceeding_timeline_due_date", "consultant_name", "remarks"];
    const rows = filtered.map((p) => cols.map((c) => {
      let v = p[c];
      if (c === "company_id") v = companyName(p.company_id);
      if (c === "group_id") v = groupName(p.group_id);
      v = v === null || v === undefined ? "" : String(v);
      return `"${v.replace(/"/g, '""')}"`;
    }).join(","));
    const csv = [cols.join(","), ...rows].join("\n");
    downloadBlob(csv, "proceedings_export.csv", "text/csv");
  }

  function exportExcel() {
    const rows = filtered.map((p) => ({
      "S.No": p.s_no, Entity: companyName(p.company_id), Group: groupName(p.group_id),
      "FY": p.financial_year, "AY": p.assessment_year, "Act": p.applicable_act, "Section": p.relevant_section,
      "Nature": p.nature_of_proceeding, "Status": p.proceeding_status, "Stage": p.stage_of_proceeding,
      "Issue": p.issue_involved, "Demand (₹)": p.tax_demand_amount, "Demand Type": p.demand_type, "Demand / Estimate Ref.": p.demand_reference, "Demand / Estimate Date": p.demand_date, "Estimated Demand Basis": p.estimated_demand_basis,
      "Last Hearing": p.last_hearing_date, "Next Hearing": p.next_hearing_date, "Due Date": p.proceeding_timeline_due_date,
      "Consultant": p.consultant_name, "Remarks": p.remarks
    }));
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Proceedings");
    XLSX.writeFile(wb, "proceedings_export.xlsx");
  }

  return (
    <div>
      <Card className="lt-filterbar">
        {isAdmin && <Select value={filters.group_id} onChange={(v) => setFilters((f) => ({ ...f, group_id: v, company_id: "" }))} options={db.groups.map((g) => ({ value: g.group_id, label: g.group_name }))} placeholder="All groups" />}
        <Select value={filters.company_id} onChange={(v) => setFilters((f) => ({ ...f, company_id: v }))} options={companiesInScope.map((c) => ({ value: c.company_id, label: c.entity_name }))} placeholder="All companies" />
        <input className="lt-input" placeholder="AY e.g. 2023-24" value={filters.ay} onChange={(e) => setFilters((f) => ({ ...f, ay: e.target.value }))} style={{ maxWidth: 150 }} />
        <Select value={filters.nature} onChange={(v) => setFilters((f) => ({ ...f, nature: v }))} options={db.masterNature} placeholder="All natures" />
        <Select value={filters.status} onChange={(v) => setFilters((f) => ({ ...f, status: v }))} options={STATUSES} placeholder="All statuses" />
        <Select value={filters.stage} onChange={(v) => setFilters((f) => ({ ...f, stage: v }))} options={STAGES} placeholder="All stages" />
        <div className="lt-search">
          <Search size={14} />
          <input placeholder="Search issue…" value={filters.q} onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))} />
        </div>
      </Card>

      <div className="lt-toolbar">
        <div style={{ color: "var(--slate)", fontSize: 13 }}>{filtered.length} proceeding{filtered.length !== 1 ? "s" : ""}</div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="ghost" onClick={exportCSV}><Download size={15} /> CSV</Btn>
          <Btn variant="ghost" onClick={exportExcel}><FileSpreadsheet size={15} /> Excel</Btn>
          <Btn variant="ghost" onClick={() => window.print()}><Printer size={15} /> Print / PDF</Btn>
          {isAdmin && <Btn onClick={() => setEditing("new")}><Plus size={15} /> Add proceeding</Btn>}
        </div>
      </div>

      <Card style={{ overflowX: "auto", padding: 0 }}>
        <table className="lt-table">
          <thead>
            <tr>
              <th>Entity</th>
              <th onClick={() => toggleSort("assessment_year")} className="sortable">AY</th>
              <th>Nature</th>
              <th>Section</th>
              <th onClick={() => toggleSort("proceeding_status")} className="sortable">Status</th>
              <th>Stage</th>
              <th>Issue</th>
              <th>Demand</th>
              <th onClick={() => toggleSort("next_hearing_date")} className="sortable">Next hearing</th>
              <th onClick={() => toggleSort("proceeding_timeline_due_date")} className="sortable">Due date</th>
              <th style={{ minWidth: 180 }}>Remarks</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((p) => {
              const overdue = p.proceeding_timeline_due_date && daysFromToday(p.proceeding_timeline_due_date) < 0 && p.proceeding_status === "Ongoing";
              return (
                <tr key={p.proceeding_id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{companyName(p.company_id)}</div>
                    {isAdmin && <div style={{ fontSize: 11, color: "#9CA3AF" }}>{groupName(p.group_id)}</div>}
                  </td>
                  <td>{p.assessment_year}</td>
                  <td className="lt-truncate" style={{ maxWidth: 160 }}>{p.nature_of_proceeding}</td>
                  <td>{p.relevant_section || "—"}</td>
                  <td><StatusStamp status={p.proceeding_status} /></td>
                  <td>{p.stage_of_proceeding}</td>
                  <td className="lt-truncate" style={{ maxWidth: 180 }} title={p.issue_involved}>{p.issue_involved}</td>
                  <td><div style={{fontWeight:600}}>{fmtINR(p.tax_demand_amount)}</div><div style={{fontSize:11,color:"#7A8290"}}>{p.demand_type}{p.demand_reference ? ` · ${p.demand_reference}` : ""}</div></td>
                  <td style={{ color: p.next_hearing_date && daysFromToday(p.next_hearing_date) <= 7 && daysFromToday(p.next_hearing_date) >= 0 ? "var(--amber)" : undefined, fontWeight: p.next_hearing_date && daysFromToday(p.next_hearing_date) <= 7 ? 600 : 400 }}>{fmtDate(p.next_hearing_date)}</td>
                  <td style={{ color: overdue ? "var(--rust)" : undefined, fontWeight: overdue ? 600 : 400 }}>{fmtDate(p.proceeding_timeline_due_date)}{overdue && " ⚠"}</td>
                  <td>
                    <input
                      className="lt-input lt-remarks-input"
                      value={remarksDraft[p.proceeding_id] ?? p.remarks ?? ""}
                      onChange={(e) => setRemarksDraft((d) => ({ ...d, [p.proceeding_id]: e.target.value }))}
                      onBlur={() => saveRemarks(p)}
                    />
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button className="lt-icon-btn" title="History" onClick={() => setHistoryFor(p)}><History size={15} /></button>
                      {isAdmin && <button className="lt-icon-btn" title="Edit" onClick={() => setEditing(p)}><Pencil size={15} /></button>}
                      {isAdmin && <button className="lt-icon-btn" title="Delete" onClick={() => setConfirmDelete(p)}><Trash2 size={15} color="var(--rust)" /></button>}
                    </div>
                  </td>
                </tr>
              );
            })}
            {pageRows.length === 0 && <tr><td colSpan={12}><Empty text="No proceedings match these filters." /></td></tr>}
          </tbody>
        </table>
      </Card>

      <div className="lt-pagination">
        <button className="lt-icon-btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft size={16} /></button>
        <span>Page {page} of {totalPages}</span>
        <button className="lt-icon-btn" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}><ChevronRight size={16} /></button>
      </div>

      {editing && (
        <ProceedingFormModal
          db={db} isNew={editing === "new"}
          initial={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSave={(form) => saveProceeding(form, editing === "new")}
        />
      )}
      {historyFor && (
        <Modal title={`History — ${companyName(historyFor.company_id)}`} onClose={() => setHistoryFor(null)}>
          {(!historyFor.history || historyFor.history.length === 0) ? <Empty text="No changes recorded yet." /> : (
            <div className="lt-history-list">
              {[...historyFor.history].reverse().map((h, i) => (
                <div key={i} className="lt-history-item">
                  <div style={{ fontSize: 12, color: "#9CA3AF" }}>{new Date(h.at).toLocaleString("en-IN")} · {h.by}</div>
                  <div><b>{h.field}</b>: <span style={{ color: "#9CA3AF" }}>{String(h.from ?? "—")}</span> → <span style={{ fontWeight: 600 }}>{String(h.to ?? "—")}</span></div>
                </div>
              ))}
            </div>
          )}
        </Modal>
      )}
      {confirmDelete && (
        <ConfirmDialog text={`Delete this proceeding for ${companyName(confirmDelete.company_id)} (AY ${confirmDelete.assessment_year})? This can't be undone.`} onConfirm={() => deleteProceeding(confirmDelete.proceeding_id)} onCancel={() => setConfirmDelete(null)} />
      )}
    </div>
  );
}

function downloadBlob(content, filename, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function ProceedingFormModal({ db, isNew, initial, onClose, onSave }) {
  const [form, setForm] = useState(() => initial ? { ...initial } : {
    proceeding_id: null, company_id: "", financial_year: "", assessment_year: "", tax_year: "",
    applicable_act: ACTS[0], relevant_section: "", nature_of_proceeding: "", proceeding_status: "Ongoing",
    stage_of_proceeding: "AO", issue_involved: "", tax_demand_amount: 0, demand_type: "Raised",
    demand_reference: "", demand_date: "", estimated_demand_basis: "",
    description_of_matter: "", last_hearing_date: "", next_hearing_date: "", proceeding_timeline_due_date: "",
    consultant_name: "", consultant_contact: "", remarks: ""
  });
  const [natureList, setNatureList] = useState(db.masterNature);
  const [addingNature, setAddingNature] = useState(false);
  const [newNature, setNewNature] = useState("");
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target && e.target.value !== undefined ? e.target.value : e }));

  return (
    <Modal title={isNew ? "Add proceeding" : "Edit proceeding"} onClose={onClose} wide>
      <div className="lt-form-grid">
        <Field label="Company / Entity" required>
          <Select value={form.company_id} onChange={(v) => setForm((f) => ({ ...f, company_id: v }))} options={db.companies.map((c) => ({ value: c.company_id, label: `${c.entity_name} (${db.groups.find((g) => g.group_id === c.group_id)?.group_name})` }))} placeholder="Select entity" />
        </Field>
        <Field label="Applicable Act" required>
          <Select value={form.applicable_act} onChange={(v) => setForm((f) => ({ ...f, applicable_act: v }))} options={ACTS} />
        </Field>
        <Field label="Financial Year"><input className="lt-input" placeholder="2023-24" value={form.financial_year} onChange={set("financial_year")} /></Field>
        <Field label="Assessment Year" required><input className="lt-input" placeholder="2024-25" value={form.assessment_year} onChange={set("assessment_year")} /></Field>
        <Field label="Tax Year" hint="Only if the 2025 Act applies"><input className="lt-input" value={form.tax_year || ""} onChange={set("tax_year")} /></Field>
        <Field label="Nature of Proceeding" required>
          {!addingNature ? (
            <div style={{ display: "flex", gap: 6 }}>
              <Select value={form.nature_of_proceeding} onChange={(v) => setForm((f) => ({ ...f, nature_of_proceeding: v }))} options={natureList} placeholder="Select nature" />
              <Btn variant="ghost" size="sm" onClick={() => setAddingNature(true)}><Plus size={14} /></Btn>
            </div>
          ) : (
            <div style={{ display: "flex", gap: 6 }}>
              <input className="lt-input" placeholder="New nature…" value={newNature} onChange={(e) => setNewNature(e.target.value)} />
              <Btn size="sm" onClick={() => { if (newNature.trim()) { setNatureList((l) => [...l, newNature.trim()]); setForm((f) => ({ ...f, nature_of_proceeding: newNature.trim() })); setNewNature(""); setAddingNature(false); } }}><Check size={14} /></Btn>
            </div>
          )}
        </Field>
        <Field label="Relevant Section"><input className="lt-input" value={form.relevant_section} onChange={set("relevant_section")} placeholder="e.g. 143(3), 148, 246A, 253" /></Field>
        <div style={{ gridColumn: "1 / -1", padding: "10px 0 2px", borderTop: "1px solid #ECE7DA", marginTop: 4 }}><div style={{fontSize:12,fontWeight:700,textTransform:"uppercase",letterSpacing:".08em",color:"#7A8290"}}>Tax demand details</div><div style={{fontSize:12,color:"#7A8290",marginTop:3}}>For an estimated demand, record the estimate/notice reference, date and the basis of calculation. Estimated demand is tracked separately from raised demand.</div></div>
        <Field label="Status" required><Select value={form.proceeding_status} onChange={(v) => setForm((f) => ({ ...f, proceeding_status: v }))} options={STATUSES} /></Field>
        <Field label="Stage" required><Select value={form.stage_of_proceeding} onChange={(v) => setForm((f) => ({ ...f, stage_of_proceeding: v }))} options={STAGES} /></Field>
        <Field label="Demand classification" hint="Raised = formal demand; Estimated = working / provisional exposure"><Select value={form.demand_type} onChange={(v) => setForm((f) => ({ ...f, demand_type: v, estimated_demand_basis: v === "Raised" ? "" : f.estimated_demand_basis }))} options={DEMAND_TYPES} /></Field>
        <Field label={form.demand_type === "Estimated" ? "Estimated demand amount (₹)" : "Raised demand amount (₹)"}>
          <input className="lt-input" type="number" min="0" value={form.tax_demand_amount} onChange={set("tax_demand_amount")} />
        </Field>
        <Field label={form.demand_type === "Estimated" ? "Estimate / Notice reference" : "Demand / Order reference"}>
          <input className="lt-input" value={form.demand_reference || ""} onChange={set("demand_reference")} placeholder={form.demand_type === "Estimated" ? "e.g. Notice / working estimate ref." : "e.g. Demand notice / order no."} />
        </Field>
        <Field label={form.demand_type === "Estimated" ? "Estimate date" : "Demand / Order date"}>
          <input className="lt-input" type="date" value={form.demand_date || ""} onChange={set("demand_date")} />
        </Field>
        {form.demand_type === "Estimated" && (
          <Field label="Basis of estimated demand" hint="Explain how the estimate was derived"><textarea className="lt-input" rows={2} value={form.estimated_demand_basis || ""} onChange={set("estimated_demand_basis")} placeholder="e.g. Estimated from notice, assessment worksheet, TP adjustment, etc." /></Field>
        )}
        <Field label="Last hearing date"><input className="lt-input" type="date" value={form.last_hearing_date || ""} onChange={set("last_hearing_date")} /></Field>
        <Field label="Next hearing date"><input className="lt-input" type="date" value={form.next_hearing_date || ""} onChange={set("next_hearing_date")} /></Field>
        <Field label="Statutory / timeline due date"><input className="lt-input" type="date" value={form.proceeding_timeline_due_date || ""} onChange={set("proceeding_timeline_due_date")} /></Field>
        <Field label="Consultant name"><input className="lt-input" value={form.consultant_name} onChange={set("consultant_name")} /></Field>
        <Field label="Consultant contact"><input className="lt-input" value={form.consultant_contact} onChange={set("consultant_contact")} /></Field>
        <Field label="Issue involved" required><input className="lt-input" value={form.issue_involved} onChange={set("issue_involved")} /></Field>
      </div>
      <Field label="Description of matter"><textarea className="lt-input" rows={3} value={form.description_of_matter} onChange={set("description_of_matter")} /></Field>
      <Field label="Remarks"><textarea className="lt-input" rows={2} value={form.remarks} onChange={set("remarks")} /></Field>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
        <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
        <Btn onClick={() => onSave({ ...form, tax_demand_amount: Number(form.tax_demand_amount) || 0 })}>{isNew ? "Add proceeding" : "Save changes"}</Btn>
      </div>
    </Modal>
  );
}

/* ============================== COMPANIES SCREEN ============================== */

function CompaniesScreen({ db, persistDb, notify }) {
  const [editing, setEditing] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  async function save(form, isNew) {
    if (!PAN_RE.test(form.pan || "")) { notify("PAN must be in the format AAAAA9999A.", "error"); return; }
    const dupe = db.companies.some((c) => c.pan.toUpperCase() === form.pan.toUpperCase() && c.company_id !== form.company_id);
    if (dupe) { notify("This PAN is already used by another entity.", "error"); return; }
    if (isNew) {
      const row = { ...form, company_id: uid("co"), pan: form.pan.toUpperCase() };
      await persistDb({ ...db, companies: [...db.companies, row] });
      notify("Entity added.");
    } else {
      await persistDb({ ...db, companies: db.companies.map((c) => (c.company_id === form.company_id ? { ...form, pan: form.pan.toUpperCase() } : c)) });
      notify("Entity updated.");
    }
    setEditing(null);
  }
  async function remove(id) {
    await persistDb({ ...db, companies: db.companies.filter((c) => c.company_id !== id) });
    setConfirmDelete(null);
    notify("Entity removed.");
  }

  return (
    <div>
      <div className="lt-toolbar">
        <div style={{ color: "var(--slate)", fontSize: 13 }}>{db.companies.length} entities across {db.groups.length} groups</div>
        <Btn onClick={() => setEditing("new")}><Plus size={15} /> Add entity</Btn>
      </div>
      <Card style={{ padding: 0, overflowX: "auto" }}>
        <table className="lt-table">
          <thead><tr><th>Entity</th><th>Type</th><th>PAN</th><th>Group</th><th></th></tr></thead>
          <tbody>
            {db.companies.map((c) => (
              <tr key={c.company_id}>
                <td style={{ fontWeight: 600 }}>{c.entity_name}</td>
                <td>{c.entity_type}</td>
                <td><code>{c.pan}</code></td>
                <td>{db.groups.find((g) => g.group_id === c.group_id)?.group_name}</td>
                <td>
                  <div style={{ display: "flex", gap: 4 }}>
                    <button className="lt-icon-btn" onClick={() => setEditing(c)}><Pencil size={15} /></button>
                    <button className="lt-icon-btn" onClick={() => setConfirmDelete(c)}><Trash2 size={15} color="var(--rust)" /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      {editing && <CompanyFormModal db={db} isNew={editing === "new"} initial={editing === "new" ? null : editing} onClose={() => setEditing(null)} onSave={(f) => save(f, editing === "new")} />}
      {confirmDelete && <ConfirmDialog text={`Remove ${confirmDelete.entity_name}? Proceedings tied to this entity will remain but lose their entity link.`} onConfirm={() => remove(confirmDelete.company_id)} onCancel={() => setConfirmDelete(null)} />}
    </div>
  );
}

function CompanyFormModal({ db, isNew, initial, onClose, onSave }) {
  const [form, setForm] = useState(initial || { company_id: null, group_id: db.groups[0]?.group_id || "", entity_name: "", entity_type: "Individual", pan: "" });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  return (
    <Modal title={isNew ? "Add entity" : "Edit entity"} onClose={onClose}>
      <Field label="Entity name" required><input className="lt-input" value={form.entity_name} onChange={set("entity_name")} /></Field>
      <Field label="Entity type" required><Select value={form.entity_type} onChange={(v) => setForm((f) => ({ ...f, entity_type: v }))} options={ENTITY_TYPES} /></Field>
      <Field label="Group" required><Select value={form.group_id} onChange={(v) => setForm((f) => ({ ...f, group_id: v }))} options={db.groups.map((g) => ({ value: g.group_id, label: g.group_name }))} /></Field>
      <Field label="PAN" required hint="Format: AAAAA9999A"><input className="lt-input" style={{ textTransform: "uppercase" }} maxLength={10} value={form.pan} onChange={set("pan")} /></Field>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
        <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
        <Btn onClick={() => onSave(form)}>{isNew ? "Add entity" : "Save changes"}</Btn>
      </div>
    </Modal>
  );
}

/* ============================== USERS SCREEN ============================== */

function UsersScreen({ db, persistDb, currentUser, notify }) {
  const [editing, setEditing] = useState(null);
  const [inviting, setInviting] = useState(false);
  const [confirmToggle, setConfirmToggle] = useState(null);

  async function createUser(form) {
    if (db.users.some((u) => u.user_id === form.user_id)) { notify("That User ID already exists.", "error"); return; }
    const row = { ...form, role: "GroupUser", status: "Active", created_at: todayISO() };
    await persistDb({ ...db, users: [...db.users, row] });
    notify(`User created. Share the User ID "${form.user_id}" and temp password with them.`);
    setEditing(null);
  }
  async function toggleStatus(u) {
    await persistDb({ ...db, users: db.users.map((x) => (x.user_id === u.user_id ? { ...x, status: x.status === "Active" ? "Inactive" : "Active" } : x)) });
    setConfirmToggle(null);
    notify(u.status === "Active" ? "User deactivated." : "User reactivated.");
  }
  async function resetPassword(u, pwd) {
    try {
      await api(`/api/admin/users/${encodeURIComponent(u.user_id)}/password`, { method: "POST", body: JSON.stringify({ password: pwd }) });
      notify(`Password reset for ${u.user_id}.`);
    } catch (e) { notify(e.message, "error"); }
  }
  async function changeGroup(u, group_id) {
    await persistDb({ ...db, users: db.users.map((x) => (x.user_id === u.user_id ? { ...x, group_id } : x)) });
    notify("Group updated.");
  }
  async function inviteEmail(email, group_id) {
    if (db.invited_emails.some((i) => i.email.toLowerCase() === email.toLowerCase())) { notify("That email is already invited.", "error"); return; }
    await persistDb({ ...db, invited_emails: [...db.invited_emails, { email, group_id, invited_by: currentUser.user_id, used: false }] });
    notify("Invite added — they can now self sign up with that email.");
    setInviting(false);
  }

  return (
    <div>
      <div className="lt-toolbar">
        <div style={{ color: "var(--slate)", fontSize: 13 }}>{db.users.length} users</div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="ghost" onClick={() => setInviting(true)}><Mail size={15} /> Invite email</Btn>
          <Btn onClick={() => setEditing("new")}><UserPlus size={15} /> Create user</Btn>
        </div>
      </div>

      <Card style={{ padding: 0, overflowX: "auto" }}>
        <table className="lt-table">
          <thead><tr><th>User</th><th>Role</th><th>Group</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {db.users.map((u) => (
              <tr key={u.user_id}>
                <td><div style={{ fontWeight: 600 }}>{u.name}</div><div style={{ fontSize: 12, color: "#9CA3AF" }}>{u.user_id} · {u.email}</div></td>
                <td>{u.role === "Admin" ? <Stamp text="Admin" tone="ink" /> : <Stamp text="Group user" tone="slate" />}</td>
                <td>
                  {u.role === "Admin" ? "—" : (
                    <Select value={u.group_id || ""} onChange={(v) => changeGroup(u, v)} options={db.groups.map((g) => ({ value: g.group_id, label: g.group_name }))} />
                  )}
                </td>
                <td>{u.status === "Active" ? <Stamp text="Active" tone="emerald" /> : <Stamp text="Inactive" tone="rust" />}</td>
                <td>
                  <div style={{ display: "flex", gap: 4 }}>
                    <button className="lt-icon-btn" title="Reset password" onClick={() => { const pwd = prompt(`New temporary password for ${u.user_id}:`); if (pwd) resetPassword(u, pwd); }}><RotateCcw size={15} /></button>
                    {u.user_id !== currentUser.user_id && (
                      <button className="lt-icon-btn" title={u.status === "Active" ? "Deactivate" : "Reactivate"} onClick={() => setConfirmToggle(u)}>
                        {u.status === "Active" ? <Ban size={15} color="var(--rust)" /> : <Check size={15} color="var(--emerald)" />}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <h4><Mail size={15} style={{ verticalAlign: -2 }} /> Pending invites</h4>
        {db.invited_emails.filter((i) => !i.used).length === 0 ? <Empty text="No pending invites." /> : (
          <table className="lt-mini-table">
            <thead><tr><th>Email</th><th>Group</th><th>Invited by</th></tr></thead>
            <tbody>
              {db.invited_emails.filter((i) => !i.used).map((i) => (
                <tr key={i.email}><td>{i.email}</td><td>{db.groups.find((g) => g.group_id === i.group_id)?.group_name}</td><td>{i.invited_by}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {editing && <UserFormModal db={db} onClose={() => setEditing(null)} onSave={createUser} />}
      {inviting && <InviteModal db={db} onClose={() => setInviting(false)} onSave={inviteEmail} />}
      {confirmToggle && <ConfirmDialog text={`${confirmToggle.status === "Active" ? "Deactivate" : "Reactivate"} ${confirmToggle.name}?`} onConfirm={() => toggleStatus(confirmToggle)} onCancel={() => setConfirmToggle(null)} />}
    </div>
  );
}

function UserFormModal({ db, onClose, onSave }) {
  const [form, setForm] = useState({ user_id: "", name: "", email: "", password: "", group_id: db.groups[0]?.group_id || "" });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  return (
    <Modal title="Create user" onClose={onClose}>
      <Field label="Full name" required><input className="lt-input" value={form.name} onChange={set("name")} /></Field>
      <Field label="Email" required><input className="lt-input" type="email" value={form.email} onChange={set("email")} /></Field>
      <Field label="User ID" required><input className="lt-input" value={form.user_id} onChange={set("user_id")} /></Field>
      <Field label="Temporary password" required><input className="lt-input" value={form.password} onChange={set("password")} /></Field>
      <Field label="Group" required><Select value={form.group_id} onChange={(v) => setForm((f) => ({ ...f, group_id: v }))} options={db.groups.map((g) => ({ value: g.group_id, label: g.group_name }))} /></Field>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
        <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
        <Btn onClick={() => form.user_id && form.name && form.email && form.password && onSave(form)}>Create user</Btn>
      </div>
    </Modal>
  );
}

function InviteModal({ db, onClose, onSave }) {
  const [email, setEmail] = useState("");
  const [group_id, setGroupId] = useState(db.groups[0]?.group_id || "");
  return (
    <Modal title="Invite by email" onClose={onClose}>
      <Field label="Email" required hint="They'll be able to self sign up with this email"><input className="lt-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
      <Field label="Group" required><Select value={group_id} onChange={setGroupId} options={db.groups.map((g) => ({ value: g.group_id, label: g.group_name }))} /></Field>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 16 }}>
        <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
        <Btn onClick={() => email && onSave(email, group_id)}>Send invite</Btn>
      </div>
    </Modal>
  );
}

/* ============================== MASTER LISTS SCREEN ============================== */

function MasterListsScreen({ db, persistDb, notify }) {
  return (
    <div className="lt-master-grid">
      <MasterListCard title="Nature of Proceedings" items={db.masterNature} onAdd={async (v) => { await persistDb({ ...db, masterNature: [...db.masterNature, v] }); notify("Added to Nature of Proceedings."); }} onRemove={async (v) => { await persistDb({ ...db, masterNature: db.masterNature.filter((x) => x !== v) }); notify("Removed."); }} />
      <MasterListCard title="Common Assignment Templates" items={db.masterTemplates} onAdd={async (v) => { await persistDb({ ...db, masterTemplates: [...db.masterTemplates, v] }); notify("Added to Assignment Templates."); }} onRemove={async (v) => { await persistDb({ ...db, masterTemplates: db.masterTemplates.filter((x) => x !== v) }); notify("Removed."); }} />
      <MasterListCard title="Groups" items={db.groups.map((g) => `${g.group_id} — ${g.group_name}`)} readOnly hint="Groups are created implicitly when you add an entity to a new Group ID from the Companies screen." />
    </div>
  );
}

function MasterListCard({ title, items, onAdd, onRemove, readOnly, hint }) {
  const [val, setVal] = useState("");
  return (
    <Card>
      <h4>{title}</h4>
      {hint && <div className="lt-field-hint" style={{ marginBottom: 10 }}>{hint}</div>}
      {!readOnly && (
        <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
          <input className="lt-input" placeholder="Add new item…" value={val} onChange={(e) => setVal(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && val.trim()) { onAdd(val.trim()); setVal(""); } }} />
          <Btn size="sm" onClick={() => { if (val.trim()) { onAdd(val.trim()); setVal(""); } }}><Plus size={14} /></Btn>
        </div>
      )}
      <ul className="lt-master-list">
        {items.map((it) => (
          <li key={it}>
            <span>{it}</span>
            {!readOnly && <button className="lt-icon-btn" onClick={() => onRemove(it)}><X size={13} /></button>}
          </li>
        ))}
      </ul>
    </Card>
  );
}

/* ============================== GLOBAL STYLE ============================== */

function GlobalStyle() {
  return (
    <style>{`
      @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap');
      .lt-root, .lt-root * { box-sizing: border-box; }
      .lt-root {
        --ink:#14213D; --paper:#FBF9F4; --line:#E6E0D2; --slate:#5B6472; --emerald:#1F7A5C; --amber:#C97A2B; --rust:#A83B2E; --gold:#A8823C;
        font-family: 'Inter', sans-serif; color: #1F2430; background: var(--paper); min-height: 100%;
      }
      .lt-root h1,.lt-root h2,.lt-root h3,.lt-root h4 { font-family: 'Source Serif 4', serif; color: var(--ink); margin: 0 0 6px; }
      .lt-root h4 { font-size: 14.5px; font-weight: 600; display:flex; align-items:center; gap:6px; margin-bottom: 12px; }
      .lt-spinner { width: 28px; height: 28px; border: 3px solid #E6E0D2; border-top-color: var(--ink); border-radius: 50%; animation: ltspin .8s linear infinite; margin: 0 auto; }
      @keyframes ltspin { to { transform: rotate(360deg); } }

      /* stamp */
      .stamp { display:inline-block; font-family:'Source Serif 4',serif; font-weight:700; font-size:11px; letter-spacing:1px; text-transform:uppercase;
        padding:3px 9px; border:1.5px solid; border-radius:3px; transform: rotate(-2deg); background: rgba(255,255,255,0.5); white-space:nowrap; }

      /* auth */
      .lt-auth-wrap { display:grid; grid-template-columns: 1.1fr 1fr; min-height: 640px; }
      @media (max-width:820px){ .lt-auth-wrap{ grid-template-columns:1fr; } }
      .lt-auth-side { background: var(--ink); color: #EDEBE2; padding: 46px 40px; display:flex; flex-direction:column; justify-content:space-between; }
      .lt-auth-brand { display:flex; gap:14px; align-items:flex-start; }
      .lt-auth-title { font-family:'Source Serif 4',serif; font-size: 26px; font-weight:700; color:#fff; }
      .lt-auth-sub { font-size: 13px; color: #B9C0D4; margin-top: 4px; max-width: 320px; }
      .lt-auth-points { list-style:none; padding:0; margin: 34px 0; display:flex; flex-direction:column; gap: 14px; }
      .lt-auth-points li { display:flex; gap: 10px; align-items:flex-start; font-size: 13.5px; color:#D8DCE8; }
      .lt-auth-demo { background: rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.15); border-radius:8px; padding: 14px 16px; font-size: 12.5px; color:#C6CCDC; }
      .lt-auth-demo code { background: rgba(255,255,255,0.12); padding: 1px 5px; border-radius:3px; color:#fff; }
      .lt-auth-form-side { display:flex; flex-direction:column; align-items:center; justify-content:center; padding: 40px; }
      .lt-auth-card { width: 100%; max-width: 360px; }
      .lt-auth-card h2 { font-size: 22px; }
      .lt-auth-lead { font-size: 13px; color: var(--slate); margin-bottom: 20px; }
      .lt-auth-switch { margin-top: 16px; font-size: 13px; color: var(--slate); }
      .lt-auth-switch button { border:none; background:none; color: var(--ink); font-weight:600; cursor:pointer; text-decoration: underline; }

      .lt-field { display:block; margin-bottom: 14px; }
      .lt-field-label { display:block; font-size: 12.5px; font-weight:600; color:#3A4150; margin-bottom: 5px; }
      .lt-field-hint { display:block; font-size: 11px; color:#9CA3AF; margin-top: 3px; }
      .lt-input { width:100%; padding: 9px 11px; border:1.5px solid var(--line); border-radius: 7px; font-size: 13.5px; font-family:'Inter',sans-serif; background:#fff; color:#1F2430; outline:none; transition: border-color .15s; }
      .lt-input:focus { border-color: var(--ink); box-shadow: 0 0 0 3px rgba(20,33,61,0.08); }
      textarea.lt-input { resize: vertical; }

      .lt-btn { font-family:'Inter',sans-serif; font-weight:600; border-radius:7px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; border:1.5px solid transparent; transition: all .15s; white-space:nowrap; }
      .lt-btn-md { padding: 9px 16px; font-size: 13.5px; }
      .lt-btn-sm { padding: 6px 10px; font-size: 12.5px; }
      .lt-btn-lg { padding: 11px 20px; font-size: 14.5px; width:100%; justify-content:center; }
      .lt-btn-primary { background: var(--ink); color:#fff; }
      .lt-btn-primary:hover { background:#0D1730; }
      .lt-btn-ghost { background:#fff; color: var(--ink); border-color: var(--line); }
      .lt-btn-ghost:hover { border-color: var(--ink); }
      .lt-btn-danger { background: var(--rust); color:#fff; }
      .lt-btn:disabled { opacity:.5; cursor:not-allowed; }

      .lt-icon-btn { border:none; background:transparent; cursor:pointer; padding:6px; border-radius:6px; display:inline-flex; color: var(--slate); }
      .lt-icon-btn:hover { background: rgba(20,33,61,0.07); }
      .lt-icon-btn:disabled { opacity: .35; cursor:not-allowed; }
      .lt-link-btn { border:none; background:none; color: var(--ink); font-size:12.5px; text-decoration:underline; cursor:pointer; }

      /* shell */
      .lt-shell { display:flex; min-height: 100vh; background: var(--paper); }
      .lt-sidebar { width: 232px; background: var(--ink); color:#EDEBE2; padding: 20px 14px; display:flex; flex-direction:column; flex-shrink:0; }
      .lt-sidebar-brand { display:flex; align-items:center; gap:10px; font-family:'Source Serif 4',serif; font-weight:700; font-size:16px; color:#fff; padding: 6px 8px 22px; }
      .lt-nav-item { display:flex; align-items:center; gap:10px; width:100%; text-align:left; background:none; border:none; color:#C6CCDC; padding: 10px 12px; border-radius:8px; font-size:13.5px; font-weight:500; cursor:pointer; margin-bottom:2px; }
      .lt-nav-item:hover { background: rgba(255,255,255,0.06); color:#fff; }
      .lt-nav-item.active { background: rgba(255,255,255,0.12); color:#fff; }
      .lt-sidebar-foot { margin-top:auto; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.12); }
      .lt-user-chip { display:flex; gap:9px; align-items:center; padding: 6px 8px 14px; color:#fff; }
      .lt-user-avatar { width:32px; height:32px; border-radius:50%; background: var(--gold); color:#fff; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; flex-shrink:0; }
      .lt-main { flex:1; min-width:0; display:flex; flex-direction:column; }
      .lt-topbar { display:flex; align-items:center; gap:12px; padding: 16px 28px; border-bottom: 1px solid var(--line); background:#fff; }
      .lt-topbar-title { font-family:'Source Serif 4',serif; font-size: 19px; font-weight:700; color: var(--ink); flex:1; }
      .lt-content { padding: 22px 28px 60px; flex:1; }
      .lt-only-mobile { display:none; }

      @media (max-width: 880px) {
        .lt-sidebar { position:fixed; z-index:40; height:100vh; transform: translateX(-100%); transition: transform .2s; }
        .lt-sidebar-open { transform: translateX(0); }
        .lt-only-mobile { display:inline-flex; }
        .lt-content { padding: 16px; }
        .lt-topbar { padding: 12px 16px; }
      }

      .lt-card { background:#fff; border:1px solid var(--line); border-radius: 12px; padding: 18px 20px; }
      .lt-filterbar { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-bottom: 16px; }
      .lt-filterbar .lt-input, .lt-filterbar select { max-width: 200px; }
      .lt-search { display:flex; align-items:center; gap:6px; border:1.5px solid var(--line); border-radius:7px; padding: 7px 11px; background:#fff; color:#9CA3AF; }
      .lt-search input { border:none; outline:none; font-size:13.5px; color:#1F2430; }

      /* premium dashboard */
      .lt-dashboard { max-width: 1560px; margin: 0 auto; }
      .lt-dashboard-hero { display:flex; justify-content:space-between; align-items:flex-end; gap:18px; padding: 4px 0 18px; }
      .lt-eyebrow { font-size:10.5px; font-weight:800; letter-spacing:1.6px; color:var(--gold); margin-bottom:6px; }
      .lt-dashboard-title { font-size:28px !important; line-height:1.1; margin-bottom:6px !important; }
      .lt-dashboard-subtitle { margin:0; font-size:13px; color:var(--slate); max-width:700px; line-height:1.55; }
      .lt-dashboard-hero-meta { display:flex; flex-direction:column; align-items:flex-end; gap:5px; padding-bottom:2px; }
      .lt-live-dot { display:flex; align-items:center; gap:7px; font-size:11.5px; font-weight:700; color:var(--emerald); }
      .lt-live-dot span { width:8px; height:8px; border-radius:50%; background:var(--emerald); box-shadow:0 0 0 4px rgba(31,122,92,.10); }
      .lt-hero-caption { font-size:11px; color:#9299A4; }
      .lt-filterbar-premium { padding:12px 14px; background:rgba(255,255,255,.92); box-shadow:0 5px 18px rgba(20,33,61,.04); }
      .lt-filter-label { display:flex; flex-direction:column; min-width:175px; margin-right:2px; }
      .lt-filter-label span { font-size:12px; font-weight:700; color:var(--ink); }
      .lt-filter-label small { font-size:10px; color:#98A0AB; margin-top:2px; }
      .lt-dashboard-kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:14px; }
      .lt-kpi { position:relative; overflow:hidden; background:#fff; border:1px solid var(--line); border-radius:14px; padding:16px 17px; box-shadow:0 7px 20px rgba(20,33,61,.045); }
      .lt-kpi:after { content:""; position:absolute; inset:auto -22px -32px auto; width:115px; height:115px; border-radius:50%; background:currentColor; opacity:.045; }
      .lt-kpi-ink { color:var(--ink); }
      .lt-kpi-amber { color:var(--amber); }
      .lt-kpi-rust { color:var(--rust); }
      .lt-kpi-emerald { color:var(--emerald); }
      .lt-kpi-top { display:flex; align-items:center; justify-content:space-between; gap:8px; }
      .lt-kpi-icon { width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center; background:currentColor; color:#fff; }
      .lt-kpi-tag { font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:800; color:#8E95A0; }
      .lt-kpi-value { margin-top:12px; font-family:'Source Serif 4',serif; font-size:28px; font-weight:700; color:var(--ink); line-height:1; }
      .lt-kpi-value-compact { font-size:22px; }
      .lt-kpi-label { font-size:12px; font-weight:600; color:var(--slate); margin-top:5px; }
      .lt-kpi-foot { display:flex; gap:12px; margin-top:10px; font-size:10.5px; color:#989FA9; flex-wrap:wrap; }
      .lt-foot-alert { color:var(--rust); font-weight:700; }
      .lt-dashboard-insight-strip { display:grid; grid-template-columns:1.3fr 1fr 1fr 1fr; gap:1px; margin:0 0 14px; background:#E8E2D5; border:1px solid #E3DDCF; border-radius:12px; overflow:hidden; box-shadow:0 5px 16px rgba(20,33,61,.035); }
      .lt-insight-label, .lt-insight-metric { background:#fff; padding:13px 15px; min-width:0; }
      .lt-insight-label { display:flex; flex-direction:column; justify-content:center; }
      .lt-insight-kicker { font-size:9px; letter-spacing:1.25px; color:#A0A6B0; font-weight:800; }
      .lt-insight-label strong { margin-top:3px; font-size:13px; color:var(--ink); }
      .lt-insight-label small { margin-top:2px; font-size:10px; color:#98A0AB; }
      .lt-insight-metric { display:flex; flex-direction:column; justify-content:center; }
      .lt-insight-metric span { font-size:10px; color:#8A919D; }
      .lt-insight-metric strong { margin-top:3px; font-family:'Source Serif 4',serif; font-size:17px; color:var(--ink); }
      .lt-insight-total strong { color:var(--rust); }
      .lt-stage-rail { background:#fff; border:1px solid var(--line); border-radius:12px; padding:14px 16px; margin-bottom:16px; box-shadow:0 6px 18px rgba(20,33,61,.035); }
      .lt-stage-rail-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:11px; }
      .lt-stage-rail-head h4 { margin-bottom:0; font-size:15px; }
      .lt-stage-items { display:grid; grid-template-columns:repeat(7,1fr); gap:8px; }
      .lt-stage-item { border:1px solid #EEE9DD; background:#FBFAF7; border-radius:9px; padding:10px 8px; text-align:center; }
      .lt-stage-item.has-value { background:#F5F7FB; border-color:#DCE2EE; }
      .lt-stage-code { display:block; font-size:10px; color:#8A919D; letter-spacing:.6px; font-weight:800; }
      .lt-stage-item strong { display:block; margin-top:3px; font-family:'Source Serif 4',serif; font-size:18px; color:var(--ink); }
      @media (max-width: 1180px) { .lt-dashboard-insight-strip { grid-template-columns:1fr 1fr; } .lt-stage-items { grid-template-columns:repeat(4,1fr); } }
      @media (max-width: 760px) { .lt-dashboard-insight-strip { grid-template-columns:1fr; } .lt-stage-rail-head { flex-direction:column; } .lt-stage-items { grid-template-columns:repeat(2,1fr); } }

      .lt-dashboard-grid { display:grid; gap:16px; margin-bottom:16px; }
      .lt-dashboard-grid-top { grid-template-columns:1.45fr .85fr; }
      .lt-dashboard-grid-mid { grid-template-columns:repeat(3,1fr); }
      .lt-dashboard-grid-bottom { grid-template-columns:repeat(3,1fr); }
      .lt-dashboard-card { min-width:0; box-shadow:0 7px 22px rgba(20,33,61,.035); }
      .lt-dashboard-card-wide { min-height:350px; }
      .lt-card-heading-row { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:10px; }
      .lt-card-heading-row h4 { margin-bottom:0; font-size:15px; }
      .lt-card-kicker { font-size:9.5px; letter-spacing:1.35px; color:#A0A6B0; font-weight:800; margin-bottom:4px; }
      .lt-card-chip, .lt-count-pill { display:inline-flex; align-items:center; justify-content:center; padding:4px 8px; border-radius:999px; background:#F3F1EA; color:#6D7480; font-size:10px; font-weight:700; white-space:nowrap; }
      .lt-count-pill-danger { background:#F9E7E3; color:var(--rust); }
      .lt-status-panel { display:grid; grid-template-columns:1fr .9fr; align-items:center; min-height:185px; }
      .lt-donut-wrap { position:relative; min-width:0; }
      .lt-donut-center { position:absolute; left:50%; top:50%; transform:translate(-50%,-47%); display:flex; flex-direction:column; align-items:center; line-height:1; }
      .lt-donut-center strong { font-family:'Source Serif 4',serif; font-size:24px; color:var(--ink); }
      .lt-donut-center span { margin-top:4px; font-size:9px; color:#98A0AB; text-transform:uppercase; letter-spacing:.8px; }
      .lt-status-list { display:flex; flex-direction:column; gap:12px; padding-right:4px; }
      .lt-status-list > div { display:grid; grid-template-columns:auto 1fr auto; gap:7px; align-items:center; font-size:11.5px; color:var(--slate); }
      .lt-status-list strong { color:var(--ink); font-size:12px; }
      .lt-status-dot { width:8px; height:8px; border-radius:50%; }
      .lt-health-callout { margin-top:8px; display:flex; gap:8px; align-items:flex-start; padding:10px 11px; border-radius:9px; background:#F5F8F6; color:#557265; font-size:10.5px; line-height:1.4; }
      .lt-priority-list, .lt-demand-list { display:flex; flex-direction:column; }
      .lt-priority-row, .lt-demand-row { display:flex; align-items:center; gap:10px; padding:10px 0; border-top:1px solid #F0ECE2; }
      .lt-priority-row:first-child, .lt-demand-row:first-child { border-top:0; }
      .lt-priority-marker { width:30px; height:30px; border-radius:9px; display:flex; align-items:center; justify-content:center; flex:0 0 30px; }
      .lt-marker-amber { background:#FBF1E5; color:var(--amber); }
      .lt-marker-rust { background:#F9E7E3; color:var(--rust); }
      .lt-priority-main, .lt-demand-company { min-width:0; flex:1; display:flex; flex-direction:column; gap:3px; }
      .lt-priority-main strong, .lt-demand-company strong { font-size:11.5px; color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .lt-priority-main span, .lt-demand-company span { font-size:10.5px; color:#8A919D; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .lt-priority-meta { display:flex; flex-direction:column; align-items:flex-end; gap:3px; min-width:86px; }
      .lt-priority-meta strong { font-size:10.5px; color:var(--ink); }
      .lt-priority-meta span { font-size:9.5px; color:#9CA3AF; }
      .lt-danger-text strong { color:var(--rust); }
      .lt-demand-value { font-family:'Source Serif 4',serif; font-size:15px; font-weight:700; color:var(--rust); white-space:nowrap; }
      .lt-nature-card { margin-bottom:0; }
      @media (max-width: 1180px) { .lt-dashboard-grid-top { grid-template-columns:1fr; } .lt-dashboard-grid-mid, .lt-dashboard-grid-bottom { grid-template-columns:1fr 1fr; } .lt-dashboard-kpis { grid-template-columns:repeat(2,1fr); } }
      @media (max-width: 760px) { .lt-dashboard-hero { flex-direction:column; align-items:flex-start; } .lt-dashboard-hero-meta { align-items:flex-start; } .lt-dashboard-grid-mid, .lt-dashboard-grid-bottom { grid-template-columns:1fr; } .lt-dashboard-kpis { grid-template-columns:1fr; } .lt-status-panel { grid-template-columns:1fr; } .lt-status-list { padding:0 16px 10px; } }
      .lt-stat-grid { display:grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 20px; }
      @media (max-width: 1100px) { .lt-stat-grid { grid-template-columns: repeat(2,1fr); } }
      .lt-stat { display:flex; gap:14px; align-items:center; }
      .lt-stat-icon { width:40px; height:40px; border-radius:10px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
      .lt-stat-value { font-family:'Source Serif 4',serif; font-size: 21px; font-weight:700; color: var(--ink); line-height:1.1; }
      .lt-stat-label { font-size:12px; color: var(--slate); margin-top:2px; }
      .lt-stat-sub { font-size:11px; color:#9CA3AF; margin-top:2px; }

      .lt-chart-grid { display:grid; grid-template-columns: repeat(2,1fr); gap: 16px; margin-bottom: 20px; }
      @media (max-width: 900px) { .lt-chart-grid { grid-template-columns: 1fr; } }
      .lt-alert-grid { display:grid; grid-template-columns: repeat(2,1fr); gap: 16px; }
      @media (max-width: 900px) { .lt-alert-grid { grid-template-columns: 1fr; } }

      .lt-toolbar { display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px; flex-wrap:wrap; gap:10px; }

      .lt-table { width:100%; border-collapse: collapse; font-size: 13px; }
      .lt-table th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.4px; color:#9CA3AF; padding: 12px 14px; border-bottom: 1.5px solid var(--line); font-weight:700; }
      .lt-table th.sortable { cursor:pointer; user-select:none; }
      .lt-table th.sortable:hover { color: var(--ink); }
      .lt-table td { padding: 11px 14px; border-bottom: 1px solid #F0ECE0; vertical-align: middle; }
      .lt-table tr:last-child td { border-bottom:none; }
      .lt-truncate { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .lt-remarks-input { font-size:12.5px; padding:6px 8px; }

      .lt-mini-table { width:100%; border-collapse:collapse; font-size:12.5px; }
      .lt-mini-table th { text-align:left; font-size:10.5px; text-transform:uppercase; color:#9CA3AF; padding:6px 8px; border-bottom:1px solid var(--line); }
      .lt-mini-table td { padding:8px; border-bottom:1px solid #F5F1E6; }
      .lt-mini-table .lt-truncate { max-width:160px; }

      .lt-pagination { display:flex; align-items:center; justify-content:center; gap: 12px; margin-top: 14px; font-size:13px; color: var(--slate); }

      .lt-empty { text-align:center; color:#9CA3AF; font-size:13px; padding: 26px 10px; }

      .lt-modal-backdrop { position:fixed; inset:0; background: rgba(20,20,25,0.45); display:flex; align-items:center; justify-content:center; z-index:100; padding:20px; }
      .lt-modal { background:#fff; border-radius:14px; width:100%; max-width: 480px; max-height:88vh; overflow-y:auto; }
      .lt-modal-wide { max-width: 760px; }
      .lt-modal-head { display:flex; justify-content:space-between; align-items:center; padding: 18px 22px; border-bottom:1px solid var(--line); position:sticky; top:0; background:#fff; z-index:2; }
      .lt-modal-head h3 { font-size:17px; margin:0; }
      .lt-modal-body { padding: 20px 22px 24px; }
      .lt-form-grid { display:grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
      @media (max-width:560px) { .lt-form-grid { grid-template-columns: 1fr; } }

      .lt-toast { position: fixed; top: 18px; right: 18px; z-index: 200; padding: 11px 16px; border-radius:8px; font-size:13px; font-weight:600; box-shadow: 0 8px 24px rgba(0,0,0,0.15); }
      .lt-toast-ok { background: var(--emerald); color:#fff; }
      .lt-toast-error { background: var(--rust); color:#fff; }

      .lt-history-list { display:flex; flex-direction:column; gap:12px; max-height: 50vh; overflow-y:auto; }
      .lt-history-item { border-left: 2px solid var(--line); padding-left: 10px; font-size:13px; }

      .lt-master-grid { display:grid; grid-template-columns: repeat(3,1fr); gap:16px; }
      @media (max-width: 1000px) { .lt-master-grid { grid-template-columns: 1fr; } }
      .lt-master-list { list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:6px; max-height: 320px; overflow-y:auto; }
      .lt-master-list li { display:flex; justify-content:space-between; align-items:center; font-size:12.5px; padding: 7px 10px; background: var(--paper); border-radius:6px; border:1px solid var(--line); }

      @media print {
        .lt-sidebar, .lt-topbar, .lt-filterbar, .lt-toolbar, .lt-pagination { display:none !important; }
        .lt-shell { display:block; }
        .lt-content { padding:0; }
      }
    `}</style>
  );
}
