import { FormEvent, useCallback, useEffect, useState } from "react";

type BootstrapStatus = { bootstrapRequired: boolean; loginUsername: string };
type Session = { id: string; mobileNumber: string; displayName: string; mustChangePassword: boolean; roles: string[]; permissions: Record<string, string> };
type RolePermission = { code: string; scopeCeiling: string };
type Role = { id: string; code: string; name: string; description: string; isSystem: boolean; isProtected: boolean; permissions: RolePermission[] };
type PermissionDefinition = { id: string; code: string; module: string; action: string; description: string; supportsScope: boolean };
type Employee = { id: string; employeeCode: string; displayName: string; mobileNumber: string | null; email: string | null; designation: string | null; department: string | null; managerEmployeeId: string | null; joinedOn: string | null; isActive: boolean; userId: string | null; accountActive: boolean; roles: string[] };
type Team = { id: string; code: string; name: string; managerEmployeeId: string | null; isActive: boolean; memberCount: number };
type FieldPolicy = { entityType: string; fieldKey: string; label: string; description: string; isSystemRequired: boolean; isAdministratorRequired: boolean };
type AuditEventItem = { id: string; occurredAtUtc: string; actorUserId: string | null; actorName: string; action: string; entityType: string; entityId: string | null; reason: string | null; correlationId: string | null; data: string };
type AuditPage = { items: AuditEventItem[]; page: number; pageSize: number; totalCount: number; totalPages: number; from: string; to: string; definition: string };
type AuditFilters = { actions: string[]; entityTypes: string[]; actors: { userId: string; displayName: string }[] };
type OperationsRun = { id: string; trigger: string; status: string; startedAtUtc: string; finishedAtUtc: string | null; createdCount: number; existingCount: number; skippedCount: number; errorCount: number; errorSummary: string | null };
type PersonMapping = { id: string; name: string; usedIn: string | null; employeeId: string | null; employeeName: string | null; mapped: boolean };
type PeopleMappingPage = { items: PersonMapping[]; employees: { id: string; employeeCode: string; displayName: string; hasLogin: boolean }[]; unmappedCount: number; totalCount: number };
type Operations = { databaseReachable: boolean; checkedAtUtc: string; appliedMigrations?: number; lastGenerationRun?: OperationsRun | null; generationStale?: boolean; activeRecurrenceRules?: number; audit?: { totalEvents: number; oldestEventUtc: string | null; generalRetentionMonths: number; securityRetentionMonths: number } };
type ClientListItem = { id: string; clientCode: string; displayName: string; category: string | null; pan: string | null; status: "ACTIVE" | "INACTIVE"; gstinCount: number; primaryGroup: string | null };
type ClientPage = { items: ClientListItem[]; page: number; pageSize: number; total: number; totalPages: number };
type ClientMaster = { categories: { id: string; code: string; name: string }[]; states: { code: string; name: string }[]; groups: { id: string; code: string; name: string }[]; requiredFields: string[]; codePrefix: string; nextClientCode: string };
type ClientContact = { id?: string; contactType: string; name: string; designation: string | null; phone: string | null; email: string | null; isPrimary: boolean; isActive: boolean; notes: string | null };
type ClientAddress = { id?: string; addressType: string; line1: string; line2: string | null; city: string | null; district: string | null; stateCode: string | null; postalCode: string | null; countryCode: string | null; isPrimary: boolean; isActive: boolean; validFrom: string | null; validTo: string | null };
type ClientTan = { id?: string; tan: string; deductorName: string | null; branch: string | null; effectiveFrom: string | null; effectiveTo: string | null; isPrimary: boolean; isActive: boolean; notes: string | null };
type ClientGstin = { id?: string; gstin: string; stateCode: string; tradeName: string | null; registrationStatus: string; effectiveFrom: string | null; effectiveTo: string | null; isPrimary: boolean; isActive: boolean; cancellationReason: string | null };
type ClientDetail = { id: string; clientCode: string; legacyCode: string | null; displayName: string; legalName: string | null; categoryId: string | null; pan: string | null; tan: string | null; onboardedOn: string | null; notes: string | null; contacts: ClientContact[]; addresses: ClientAddress[]; gstRegistrations: ClientGstin[]; tanRegistrations: ClientTan[]; groups: { groupId: string; membershipType: string; effectiveFrom: string; validTo: string | null; notes: string | null }[] };
type ServiceItem = { id: string; code: string; name: string; description: string | null; categoryId: string; category: string; defaultBillable: boolean; supportsRecurrence: boolean; supportsGstinScope: boolean; isActive: boolean; activeEnrollmentCount: number };
type Agreement = { id: string; clientId: string; clientCode: string; clientName: string; serviceId: string; serviceCode: string; serviceName: string; gstRegistrationId: string | null; gstin: string | null; engagementCode: string | null; titleOverride: string | null; effectiveFrom: string; effectiveTo: string | null; isActive: boolean; defaultPriority: string; responsibleTeamId: string | null; responsibleTeam: string | null; notes: string | null; deactivationReason: string | null };
type ServiceMasters = { categories: { id: string; code: string; name: string }[]; teams: { id: string; code: string; name: string }[]; clients: { id: string; clientCode: string; displayName: string; gstRegistrations: { id: string; gstin: string; stateCode: string; tradeName: string | null }[] }[]; requiredFields: string[] ; employees: { id: string; employeeCode: string; displayName: string }[] };
type WorkStatus = { id: string; code: string; label: string; color: string; isTerminal: boolean };
type TaskListItem = { id: string; taskNumber: number; title: string; dueDate: string; priority: string; billableSnapshot: boolean; rowVersion: number; clientId: string; clientCode: string; clientName: string; serviceId: string; serviceCode: string; serviceName: string; gstRegistrationId: string | null; gstin: string | null; status: WorkStatus; assignments: { id: string; employeeId: string; employeeName: string; role: string }[] };
type TaskPage = { items: TaskListItem[]; page: number; pageSize: number; totalCount: number; totalPages: number };
type TaskMasters = { agreements: { id: string; clientId: string; clientCode: string; clientName: string; serviceId: string; serviceName: string; gstRegistrationId: string | null; gstin: string | null; title: string; priority: string; billable: boolean }[]; statuses: WorkStatus[]; transitions: { fromStatusId: string; toStatusId: string; reasonRequired: boolean; completionDataRequired: boolean; requiredPermission: string }[]; employees: { id: string; employeeCode: string; displayName: string }[]; requiredFields: string[]; allowedViews: string[]; financialYears: { startYear: number; label: string; from: string; to: string }[] };
type TaskDetail = Omit<TaskListItem, "assignments"> & { description: string | null; clientServiceId: string | null; periodStart: string | null; periodEnd: string | null; completedAtUtc: string | null; cancelledAtUtc: string | null; cancellationReason: string | null; reopenedCount: number; createdSource: string; createdAtUtc: string; updatedAtUtc: string; assignments: { id: string; employeeId: string; employeeName: string; role: string; assignedAtUtc: string; unassignedAtUtc: string | null; remarks: string | null; unassignmentReason: string | null }[]; timeline: { id: string; fromStatus: string | null; toStatus: string; changedAtUtc: string; reason: string | null; completionNote: string | null; actor: string | null }[]; comments: { id: string; body: string; createdAtUtc: string; editedAtUtc: string | null; isRedacted: boolean; author: string | null }[] };
type CalendarTask = { id: string; taskNumber: number; title: string; dueDate: string; priority: string; createdSource: string; clientName: string; serviceName: string; status: { code: string; label: string; color: string; isTerminal: boolean }; primaryAssignee: string | null };
type CalendarData = { from: string; to: string; tasks: CalendarTask[]; countsByDate: Record<string, number> };
type ScheduleMasters = { agreements: { id: string; clientName: string; clientCode: string; serviceName: string; gstin: string | null; defaultPriority: string }[]; calendars: { id: string; code: string; name: string; timeZoneId: string }[]; employees: { id: string; employeeCode: string; displayName: string }[]; defaults: { holidayCalendarId: string; timeZoneId: string; sundayIsNonWorking: boolean; saturdayIsWorking: boolean; generationHorizonDays: number } };
type ScheduleRule = { id: string; clientServiceId: string; clientName: string; serviceName: string; gstin: string | null; frequencyCode: string; intervalCount: number; anchorDate: string; dueDay: number; dueMonthOffset: number; dueDayOffset: number; businessDayAdjustment: string; generateLeadDays: number; effectiveFrom: string; effectiveTo: string | null; ruleVersion: number; isActive: boolean; defaultPrimaryAssigneeId: string | null; assigneeName: string | null; rowVersion: number };
type GenerationRun = { id: string; windowFrom: string; windowTo: string; trigger: string; status: string; workerId: string; startedAtUtc: string; finishedAtUtc: string | null; createdCount: number; existingCount: number; skippedCount: number; errorCount: number; errorSummary: string | null };
type SchedulePreview = { periodStart: string; periodEnd: string; nominalDueDate: string; dueDate: string; generateOnDate: string; occurrenceKey: string };
type BillingEntityItem = { id: string; code: string; legalName: string; tradeName: string | null; pan: string | null; gstin: string | null; address: string | null; email: string | null; phone: string | null; currencyCode: string; effectiveFrom: string; effectiveTo: string | null; isActive: boolean; rowVersion: number; activeTermCount: number };
type BillingAgreement = { id: string; clientId: string; clientCode: string; clientName: string; serviceCode: string; serviceName: string; gstin: string | null; responsibleTeamId: string | null; team: string | null; effectiveFrom: string; effectiveTo: string | null };
type BillingMasters = { agreements: BillingAgreement[]; entities: { id: string; code: string; legalName: string; currencyCode: string; effectiveFrom: string; effectiveTo: string | null }[]; requiredEntityFields: string[]; requiredTermFields: string[]; frequencies: string[]; businessDayAdjustments: string[] };
type BillingTermItem = { id: string; clientServiceId: string; agreementIsActive: boolean; clientCode: string; clientName: string; serviceName: string; gstin: string | null; billingEntityId: string | null; billingEntityCode: string | null; billingEntityName: string | null; isBillable: boolean; pricingModel: string; amount: number | null; currencyCode: string; taxInclusive: boolean; effectiveFrom: string; effectiveTo: string | null; version: number; notes: string | null; schedule: null | { frequencyCode: string; intervalMonths: number | null; anchorDate: string | null; billingDay: number | null; businessDayAdjustment: string; oneTimeDate: string | null; months: number[] } };
type ProjectionMasters = { clients: { id: string; clientCode: string; displayName: string }[]; groups: { id: string; code: string; name: string }[]; services: { id: string; code: string; name: string }[]; entities: { id: string; code: string; legalName: string; currencyCode: string }[]; teams: { id: string; code: string; name: string; employeeId: string | null; employeeName: string | null }[]; defaults: { timeZoneId: string; financialYearStartMonth: number; groupRule: string; employeeRule: string } };
type ProjectionSummary = { key: string; label: string; currencyCode: string; amount: number; occurrenceCount: number };
type ProjectionDetail = { termId: string; termVersion: number; clientServiceId: string; clientId: string; clientCode: string; clientName: string; groupId: string | null; groupName: string; serviceId: string; serviceCode: string; serviceName: string; billingEntityId: string; billingEntityCode: string; billingEntityName: string; teamId: string | null; teamName: string | null; employeeId: string | null; employeeName: string | null; nominalDate: string; projectionDate: string; servicePeriodStart: string; servicePeriodEnd: string; amount: number; currencyCode: string; taxInclusive: boolean; frequencyCode: string; explanation: string };
type ProjectionReport = { from: string; to: string; asOf: string; generatedAtUtc: string; definition: string; assumptions: string[]; totals: ProjectionSummary[]; months: ProjectionSummary[]; quarters: ProjectionSummary[]; financialYears: ProjectionSummary[]; clients: ProjectionSummary[]; groups: ProjectionSummary[]; billingEntities: ProjectionSummary[]; services: ProjectionSummary[]; teams: ProjectionSummary[]; employees: ProjectionSummary[]; details: ProjectionDetail[] };
type DashboardMetricItem = { code: string; label: string; value: number; report: "CLIENTS" | "TASKS"; filter: string; definition: string };
type DashboardData = { today: string; selectedFrom: string; selectedTo: string; generatedAtUtc: string; scope: string; metrics: DashboardMetricItem[]; tasksByEmployee: { key: string; label: string; value: number }[]; projectionAvailable: boolean; projectionDefinition: string | null; currentMonthProjectionTotals: ProjectionSummary[]; currentMonthProjectionByEntity: ProjectionSummary[] };
type ReportCatalogItem = { code: "CLIENTS" | "TASKS" | "PROJECTION"; name: string; module: string; description: string; dimensions: string[]; exportable: boolean };
type ReportMasters = { clients: { id: string; clientCode: string; displayName: string }[]; services: { id: string; code: string; name: string }[]; employees: { id: string; employeeCode: string; displayName: string }[]; statuses: { code: string; label: string }[]; categories: { id: string; code: string; name: string }[]; groups: { id: string; code: string; name: string }[] };
type ClientReportRow = { id: string; clientCode: string; displayName: string; status: string; category: string | null; pan: string | null; gstinCount: number; primaryGroup: string | null };
type ClientReportPage = { items: ClientReportRow[]; page: number; pageSize: number; totalCount: number; totalPages: number; byStatus: { key: string; label: string; value: number }[]; byCategory: { key: string; label: string; value: number }[]; definition: string };
type TaskReportRow = { id: string; taskNumber: number; title: string; clientCode: string; clientName: string; serviceName: string; dueDate: string; statusCode: string; statusLabel: string; priority: string; billable: boolean; primaryAssignee: string | null };
type TaskReportPage = { items: TaskReportRow[]; page: number; pageSize: number; totalCount: number; totalPages: number; byStatus: { key: string; label: string; value: number }[]; byService: { key: string; label: string; value: number }[]; today: string; definition: string };

export function App() {
  const [bootstrap, setBootstrap] = useState<BootstrapStatus | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const refreshSession = useCallback(async () => {
    const response = await fetch("/api/v1/auth/me", { credentials: "same-origin" });
    setSession(response.ok ? await response.json() as Session : null);
  }, []);

  useEffect(() => {
    Promise.all([fetchJson<BootstrapStatus>("/api/v1/auth/status"), refreshSession()])
      .then(([status]) => setBootstrap(status))
      .catch(() => setNotice("The server is unavailable. Check that the application and database services are running."))
      .finally(() => setLoading(false));
  }, [refreshSession]);

  if (loading) return <CenteredMessage title="Opening secure workspace" detail="Checking server and session…" />;
  if (!bootstrap) return <CenteredMessage title="Server unavailable" detail={notice} />;
  if (bootstrap.bootstrapRequired) return <BootstrapRequired />;
  if (!session) return <Login onAuthenticated={setSession} />;
  if (session.mustChangePassword) return <ChangePassword session={session} onChanged={() => setSession(null)} />;
  return <AdminWorkspace session={session} onSignedOut={() => setSession(null)} />;
}

function Login({ onAuthenticated }: { onAuthenticated: (session: Session) => void }) {
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setError("");
    const data = new FormData(event.currentTarget);
    try {
      onAuthenticated(await mutateJson<Session>("/api/v1/auth/login", "POST", { mobileNumber: data.get("mobileNumber"), password: data.get("password") }));
    } catch (reason) { setError(messageFrom(reason)); }
    finally { setSubmitting(false); }
  }
  return <main className="auth-shell">
    <section className="brand-panel"><div className="eyebrow">CA Firm Practice Management</div><h1>One practice.<br />Clear control.</h1><p>Secure access for employees, managers and administrators across the office LAN.</p><small>Phase 9 of 12 · Dashboards and reports</small></section>
    <section className="auth-card" aria-labelledby="login-title"><div className="phase-badge">Phase 9</div><h2 id="login-title">Sign in</h2><p className="muted">Use your registered 10-digit mobile number.</p>
      <form onSubmit={submit} className="form-stack"><label>Mobile number<input name="mobileNumber" inputMode="numeric" autoComplete="username" pattern="[6-9][0-9]{9}" maxLength={10} required /></label><label>Password<input name="password" type="password" autoComplete="current-password" required /></label>{error ? <p className="error" role="alert">{error}</p> : null}<button className="primary" disabled={submitting}>{submitting ? "Signing in…" : "Sign in securely"}</button></form>
    </section>
  </main>;
}

function BootstrapRequired() {
  return <CenteredMessage title="Administrator setup required" detail="The database is ready, but no account exists yet."><div className="setup-box"><strong>Abhishek Adlakha</strong> must run the secure bootstrap command locally on the server. The password is entered without echo and is never stored in source code or chat. See <code>deploy/windows-server/README.md</code> for production, or the Phase 2 guide for Docker development.</div></CenteredMessage>;
}

function ChangePassword({ session, onChanged }: { session: Session; onChanged: () => void }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    try { await mutateJson("/api/v1/auth/change-password", "POST", { currentPassword: data.get("currentPassword"), newPassword: data.get("newPassword") }); onChanged(); }
    catch (reason) { setError(messageFrom(reason)); }
  }
  return <CenteredMessage title={`Welcome, ${session.displayName}`} detail="You must replace the temporary password before continuing."><form onSubmit={submit} className="form-stack compact-form"><label>Temporary password<input name="currentPassword" type="password" autoComplete="current-password" required /></label><label>New password<input name="newPassword" type="password" autoComplete="new-password" minLength={12} required /></label><small>Use at least 12 characters and do not include your mobile number.</small>{error ? <p className="error">{error}</p> : null}<button className="primary">Change password</button></form></CenteredMessage>;
}

function AdminWorkspace({ session, onSignedOut }: { session: Session; onSignedOut: () => void }) {
  const [view, setView] = useState<"dashboard" | "reports" | "clients" | "services" | "tasks" | "calendar" | "billing" | "projection" | "audit" | "administration">("reports.view" in session.permissions ? "dashboard" : "tasks.view" in session.permissions ? "tasks" : "calendar.view" in session.permissions ? "calendar" : "clients.view" in session.permissions ? "clients" : "services.view" in session.permissions ? "services" : "billing.project" in session.permissions ? "projection" : "billing.view" in session.permissions ? "billing" : "administration");
  const [roles, setRoles] = useState<Role[]>([]); const [permissions, setPermissions] = useState<PermissionDefinition[]>([]); const [employees, setEmployees] = useState<Employee[]>([]); const [fields, setFields] = useState<FieldPolicy[]>([]); const [notice, setNotice] = useState("");
  const canManageRoles = "identity.roles.manage" in session.permissions; const canManageEmployees = "employees.manage" in session.permissions; const canManageFields = "settings.field_policies.manage" in session.permissions;
  const canViewRoles = "identity.roles.view" in session.permissions; const canViewEmployees = "employees.view" in session.permissions;
  const canViewOperations = "system.diagnostics.view" in session.permissions;
  const canMapPeople = "employees.manage" in session.permissions;
  const canManageTeams = "teams.manage" in session.permissions;
  const canAdminister = canViewRoles || canViewEmployees || canManageFields || canViewOperations;
  // Request only what this session may read, and only once administration is actually opened.
  // Loading all four sets on mount made every workspace fail with a bare 403 for anyone who
  // lacked one of them.
  const load = useCallback(async () => {
    try {
      const [roleData, permissionData, employeeData, fieldData] = await Promise.all([
        canViewRoles ? fetchJson<Role[]>("/api/v1/admin/roles") : Promise.resolve<Role[]>([]),
        canViewRoles ? fetchJson<PermissionDefinition[]>("/api/v1/admin/permissions") : Promise.resolve<PermissionDefinition[]>([]),
        canViewEmployees ? fetchJson<Employee[]>("/api/v1/admin/employees") : Promise.resolve<Employee[]>([]),
        fetchJson<FieldPolicy[]>("/api/v1/admin/field-policies")
      ]);
      setRoles(roleData); setPermissions(permissionData); setEmployees(employeeData); setFields(fieldData); setNotice("");
    }
    catch (reason) { setNotice(messageFrom(reason)); }
  }, [canViewRoles, canViewEmployees]);
  useEffect(() => { if (view === "administration" && canAdminister) void load(); }, [view, canAdminister, load]);
  async function signOut() { await mutateJson("/api/v1/auth/logout", "POST"); onSignedOut(); }
  const navigation = <nav className="workspace-nav">{"reports.view" in session.permissions ? <button className={view === "dashboard" ? "nav-active" : ""} onClick={() => setView("dashboard")}>Dashboard</button> : null}{"tasks.view" in session.permissions ? <button className={view === "tasks" ? "nav-active" : ""} onClick={() => setView("tasks")}>Tasks</button> : null}{"calendar.view" in session.permissions || "scheduling.view" in session.permissions ? <button className={view === "calendar" ? "nav-active" : ""} onClick={() => setView("calendar")}>Calendar</button> : null}{"clients.view" in session.permissions ? <button className={view === "clients" ? "nav-active" : ""} onClick={() => setView("clients")}>Clients</button> : null}{"services.view" in session.permissions ? <button className={view === "services" ? "nav-active" : ""} onClick={() => setView("services")}>Services</button> : null}{"billing.view" in session.permissions ? <button className={view === "billing" ? "nav-active" : ""} onClick={() => setView("billing")}>Billing</button> : null}{"billing.project" in session.permissions ? <button className={view === "projection" ? "nav-active" : ""} onClick={() => setView("projection")}>Projection</button> : null}{"reports.view" in session.permissions ? <button className={view === "reports" ? "nav-active" : ""} onClick={() => setView("reports")}>Reports</button> : null}{"audit.view" in session.permissions ? <button className={view === "audit" ? "nav-active" : ""} onClick={() => setView("audit")}>Audit</button> : null}{canAdminister ? <button className={view === "administration" ? "nav-active" : ""} onClick={() => setView("administration")}>Administration</button> : null}</nav>;
  if (view === "dashboard") return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <DashboardWorkspace />
    <footer><span>Every metric uses server-side {session.permissions["reports.view"]} scope</span><span>Asia/Kolkata business date</span></footer>
  </main>;
  if (view === "reports") return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <ReportsWorkspace session={session} onProjection={() => setView("projection")} />
    <footer><span>Report totals reconcile to the same filtered detail</span><span>Exports use the narrower view/export scope</span></footer>
  </main>;
  if (view === "clients") return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <ClientRegistry session={session} />
    <footer><span>Native Windows Server 2019 production target · HTTPS office LAN</span><span>Windows and macOS browser access</span></footer>
  </main>;
  if (view === "services") return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <ServiceWorkspace session={session} />
    <footer><span>Service defaults apply only to new agreements</span><span>Recurring rules are configured from Calendar</span></footer>
  </main>;
  if (view === "tasks") return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <TaskWorkspace session={session} />
    <footer><span>Manual and generated work · assignment and status history retained</span><span>Occurrence keys prevent duplicate generated tasks</span></footer>
  </main>;
  if (view === "calendar") return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <SchedulingWorkspace session={session} />
    <footer><span>Sunday non-working · Saturday currently working</span><span>India firm calendar · Asia/Kolkata</span></footer>
  </main>;
  if (view === "billing") return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <BillingWorkspace session={session} />
    <footer><span>Fixed fees are per billing event · GST exclusive unless marked inclusive</span><span>Use Projection to calculate expected fees</span></footer>
  </main>;
  if (view === "projection") return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <ProjectionWorkspace session={session} />
    <footer><span>Expected fees only · never invoices, revenue, receivables or payments</span><span>Currency totals always remain separate</span></footer>
  </main>;
  if (view === "audit") return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <AuditWorkspace />
    <footer><span>Audit events are append-only and cannot be edited or deleted</span><span>Asia/Kolkata business date</span></footer>
  </main>;
  if (!canAdminister) return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <section className="workspace-hero"><div><span className="phase-badge">Phase 10 active</span><h1>No workspace available</h1><p>This account has no permissions that grant a workspace yet. Ask an administrator to grant the access your role needs.</p></div></section>
    <footer><span>Every action and record is authorised on the server</span><span>Asia/Kolkata business date</span></footer>
  </main>;
  return <main className="workspace-shell">
    <header className="topbar"><div><div className="eyebrow">Practice Management</div>{navigation}</div><div className="user-menu"><span>{session.displayName}<small>{session.roles.join(" · ")}</small></span><button className="quiet" onClick={signOut}>Sign out</button></div></header>
    <section className="workspace-hero"><div><span className="phase-badge">Phase 9 active</span><h1>Identity & access</h1><p>Employees, roles, permissions and configurable field requirements are controlled here.</p></div><div className="metric-strip">{canViewEmployees ? <Metric value={employees.length} label="Employees" /> : null}{canViewRoles ? <Metric value={roles.length} label="Roles" /> : null}<Metric value={fields.filter(x => x.isAdministratorRequired).length} label="Required fields" /></div></section>
    {notice ? <p className="error">{notice}</p> : null}<div className="admin-grid">
      {canViewEmployees ? <section className="panel panel--wide"><div className="panel-title"><div><h2>Employees</h2><p>Login names are registered mobile numbers.</p></div></div><div className="record-list">{employees.map(employee => <div className="record" key={employee.id}><span className={`avatar ${employee.isActive ? "" : "avatar--off"}`}>{initials(employee.displayName)}</span><span><strong>{employee.displayName}</strong><small>{[employee.employeeCode, employee.mobileNumber, employee.roles.join(", ") || (employee.userId ? "No role" : "Cannot sign in yet")].filter(Boolean).join(" · ")}</small></span><span className={employeeStateClass(employee)}>{employeeState(employee)}</span></div>)}</div>{canManageEmployees ? <><EditEmployee employees={employees} onSaved={load} /><CreateEmployee roles={roles} onCreated={load} /></> : null}</section> : null}
      {canManageTeams ? <TeamsPanel employees={employees} /> : null}
      {canMapPeople ? <PeopleMappingPanel onChanged={load} /> : null}
      {canViewOperations ? <OperationsPanel /> : null}
      {canViewRoles ? <section className="panel"><div className="panel-title"><div><h2>Roles</h2><p>Six defaults plus administrator-created roles.</p></div></div><div className="tag-list">{roles.map(role => <span className="role-tag" key={role.id}>{role.name}{role.isProtected ? " · protected" : ""}</span>)}</div>{canManageRoles ? <><CreateRole onCreated={load} /><RolePermissions roles={roles} permissions={permissions} onSaved={load} /></> : null}</section> : null}
      <section className="panel"><div className="panel-title"><div><h2>Mandatory fields</h2><p>Grouped by the record they belong to. A label such as "Effective from" appears under more than one record because each is a separate setting. Locked rows are required by the system and cannot be switched off.</p></div></div>{fieldGroups(fields).map(group => <div className="policy-group" key={group.entityType}><h3>{group.label}</h3><div className="policy-list">{group.fields.map(field => <label className="policy" key={`${field.entityType}/${field.fieldKey}`}><span><strong>{field.label}</strong><small>{field.description}</small></span>{field.isSystemRequired ? <span className="state">Always required</span> : <input type="checkbox" checked={field.isAdministratorRequired} disabled={!canManageFields} onChange={() => updateField(field, !field.isAdministratorRequired, load, setNotice)} />}</label>)}</div></div>)}</section>
    </div><footer><span>Native Windows Server 2019 production target · HTTPS office LAN</span><span>Windows and macOS browser access</span></footer>
  </main>;
}

function DashboardWorkspace() {
  const month = monthRange(todayValue().slice(0, 7)); const [from, setFrom] = useState(month.from); const [to, setTo] = useState(month.to);
  const [data, setData] = useState<DashboardData | null>(null); const [drill, setDrill] = useState<DashboardMetricItem | null>(null); const [clientRows, setClientRows] = useState<ClientReportPage | null>(null); const [taskRows, setTaskRows] = useState<TaskReportPage | null>(null); const [notice, setNotice] = useState("");
  const load = useCallback(async () => { try { setData(await fetchJson<DashboardData>(`/api/v1/dashboard?from=${from}&to=${to}`)); setNotice(""); } catch (reason) { setNotice(messageFrom(reason)); } }, [from, to]);
  useEffect(() => { void load(); }, [load]);
  async function open(metric: DashboardMetricItem) { setDrill(metric); setClientRows(null); setTaskRows(null); try { if (metric.report === "CLIENTS") { const params = metric.filter === "WITH_GSTIN" ? "hasGstin=true" : `status=${metric.filter}`; setClientRows(await fetchJson<ClientReportPage>(`/api/v1/reports/clients?${params}&page=1&pageSize=20`)); } else { const selected = metric.filter === "COMPLETED" || metric.filter === "CANCELLED" ? `&from=${from}&to=${to}` : ""; setTaskRows(await fetchJson<TaskReportPage>(`/api/v1/reports/tasks?bucket=${metric.filter}${selected}&page=1&pageSize=20`)); } } catch (reason) { setNotice(messageFrom(reason)); } }
  const maxWorkload = Math.max(...(data?.tasksByEmployee.map(item => item.value) ?? []), 1);
  return <><section className="workspace-hero dashboard-hero"><div><span className="phase-badge">Phase 9 active</span><h1>Practice dashboard</h1><p>Scoped operational metrics with an exact report behind every card. Completed and cancelled counts use the selected local-date period.</p></div><div className="dashboard-period"><label>Period from<input type="date" value={from} onChange={event => setFrom(event.target.value)} /></label><label>Period to<input type="date" value={to} onChange={event => setTo(event.target.value)} /></label></div></section>
    {notice ? <p className="error">{notice}</p> : null}<section className="dashboard-cards">{data?.metrics.map(metric => <button key={metric.code} className={drill?.code === metric.code ? "dashboard-card dashboard-card--active" : "dashboard-card"} onClick={() => void open(metric)} title={metric.definition}><span>{metric.label}</span><strong>{metric.value.toLocaleString("en-IN")}</strong><small>Open matching records →</small></button>)}</section>
    <div className="dashboard-grid"><section className="panel"><div className="panel-title"><div><h2>Current workload by primary employee</h2><p>Current active assignments inside your report scope.</p></div></div><div className="workload-bars">{data?.tasksByEmployee.map(item => <article key={item.key}><span>{item.label}</span><div><i style={{ width: `${item.value / maxWorkload * 100}%` }} /></div><b>{item.value}</b></article>)}{!data?.tasksByEmployee.length ? <p className="muted">No currently assigned tasks are visible.</p> : null}</div></section>
      <section className="panel"><div className="panel-title"><div><h2>Current-month projected fees</h2><p>{data?.projectionDefinition ?? "Requires billing.project permission."}</p></div></div><div className="dashboard-projection">{data?.currentMonthProjectionTotals.map(item => <strong key={item.key}>{money(item.amount, item.currencyCode)}<small>{item.occurrenceCount} events</small></strong>)}{data?.currentMonthProjectionByEntity.map(item => <span key={item.key}>{item.label}<b>{money(item.amount, item.currencyCode)}</b></span>)}{data && !data.projectionAvailable ? <p className="muted">Projection values are hidden because this session does not have billing.project permission.</p> : null}{data?.projectionAvailable && !data.currentMonthProjectionTotals.length ? <p className="muted">No configured billing events fall in the current month.</p> : null}</div></section></div>
    {drill ? <section className="panel dashboard-drill"><div className="panel-title"><div><h2>{drill.label} · drill-down</h2><p>{drill.definition} Card: {drill.value}; report: {clientRows?.totalCount ?? taskRows?.totalCount ?? "loading"}.</p></div><button className="quiet" onClick={() => setDrill(null)}>Close</button></div>{clientRows ? <ClientReportTable page={clientRows} /> : null}{taskRows ? <TaskReportTable page={taskRows} /> : null}</section> : null}
    <small className="dashboard-refresh">Last refreshed {data ? new Date(data.generatedAtUtc).toLocaleString("en-IN") : "…"} · scope {data?.scope ?? "…"}</small>
  </>;
}

function ReportsWorkspace({ session, onProjection }: { session: Session; onProjection: () => void }) {
  const month = monthRange(todayValue().slice(0, 7)); const [catalog, setCatalog] = useState<ReportCatalogItem[]>([]); const [masters, setMasters] = useState<ReportMasters | null>(null); const [selected, setSelected] = useState<"CLIENTS" | "TASKS" | "PROJECTION">("TASKS");
  const [clientStatus, setClientStatus] = useState("ALL"); const [clientCategory, setClientCategory] = useState(""); const [clientGroup, setClientGroup] = useState(""); const [hasGstin, setHasGstin] = useState("");
  const [bucket, setBucket] = useState(""); const [taskStatus, setTaskStatus] = useState(""); const [from, setFrom] = useState(month.from); const [to, setTo] = useState(month.to); const [employeeId, setEmployeeId] = useState(""); const [clientId, setClientId] = useState(""); const [serviceId, setServiceId] = useState(""); const [billable, setBillable] = useState("");
  const [clients, setClients] = useState<ClientReportPage | null>(null); const [tasks, setTasks] = useState<TaskReportPage | null>(null); const [notice, setNotice] = useState(""); const canExport = "reports.export" in session.permissions;
  useEffect(() => { void Promise.all([fetchJson<ReportCatalogItem[]>("/api/v1/reports/catalog"), fetchJson<ReportMasters>("/api/v1/reports/masters")]).then(([items, masterData]) => { setCatalog(items); setMasters(masterData); }).catch(reason => setNotice(messageFrom(reason))); }, []);
  const clientFilters = useCallback(() => ({ status: clientStatus, hasGstin: hasGstin === "" ? null : hasGstin === "true", categoryId: clientCategory || null, groupId: clientGroup || null, search: null }), [clientStatus, hasGstin, clientCategory, clientGroup]);
  const taskFilters = useCallback(() => ({ bucket: bucket || null, status: taskStatus || null, from: from || null, to: to || null, employeeId: employeeId || null, clientId: clientId || null, serviceId: serviceId || null, billable: billable === "" ? null : billable === "true", search: null }), [bucket, taskStatus, from, to, employeeId, clientId, serviceId, billable]);
  async function run(page = 1) { try { if (selected === "CLIENTS") { const filters = clientFilters(); const params = new URLSearchParams({ status: filters.status, page: String(page), pageSize: "50" }); if (filters.hasGstin !== null) params.set("hasGstin", String(filters.hasGstin)); if (filters.categoryId) params.set("categoryId", filters.categoryId); if (filters.groupId) params.set("groupId", filters.groupId); setClients(await fetchJson<ClientReportPage>(`/api/v1/reports/clients?${params}`)); setTasks(null); } else if (selected === "TASKS") { const filters = taskFilters(); const params = new URLSearchParams({ page: String(page), pageSize: "50" }); Object.entries(filters).forEach(([key, value]) => { if (value !== null && value !== "") params.set(key, String(value)); }); setTasks(await fetchJson<TaskReportPage>(`/api/v1/reports/tasks?${params}`)); setClients(null); } else onProjection(); setNotice(""); } catch (reason) { setNotice(messageFrom(reason)); } }
  async function exportRows(format: "csv" | "xlsx") { try { const report = selected.toLowerCase(); const filters = selected === "CLIENTS" ? clientFilters() : taskFilters(); await downloadFile(`/api/v1/reports/${report}:export`, { format, filters }, `${report}-report.${format}`); } catch (reason) { setNotice(messageFrom(reason)); } }
  return <><section className="workspace-hero reports-hero"><div><span className="phase-badge">Phase 9 active</span><h1>Reports</h1><p>Bounded, permission-scoped registers with filters, reconciled summaries and matching CSV/XLSX detail.</p></div></section>
    <section className="report-catalog">{catalog.map(item => <button key={item.code} className={selected === item.code ? "report-card report-card--active" : "report-card"} onClick={() => setSelected(item.code)}><small>{item.module}</small><strong>{item.name}</strong><span>{item.description}</span><i>{item.dimensions.join(" · ")}</i></button>)}</section>
    {notice ? <p className="error">{notice}</p> : null}{selected === "CLIENTS" ? <section className="panel report-filters"><label>Status<select value={clientStatus} onChange={event => setClientStatus(event.target.value)}><option value="ALL">All statuses</option><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></label><label>GSTIN coverage<select value={hasGstin} onChange={event => setHasGstin(event.target.value)}><option value="">All clients</option><option value="true">Has active GSTIN</option><option value="false">No active GSTIN</option></select></label><label>Category<select value={clientCategory} onChange={event => setClientCategory(event.target.value)}><option value="">All categories</option>{masters?.categories.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Primary group<select value={clientGroup} onChange={event => setClientGroup(event.target.value)}><option value="">All primary groups</option>{masters?.groups.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><ReportButtons onRun={() => void run()} onExport={exportRows} canExport={canExport} /></section> : null}
    {selected === "TASKS" ? <section className="panel report-filters report-filters--tasks"><label>Bucket<select value={bucket} onChange={event => setBucket(event.target.value)}><option value="">Due-date range</option><option value="OVERDUE">Overdue</option><option value="DUE_TODAY">Due today</option><option value="UPCOMING">Upcoming</option><option value="IN_PROCESS">In process</option><option value="COMPLETED">Completed in period</option><option value="CANCELLED">Cancelled in period</option></select></label><label>Status<select value={taskStatus} onChange={event => setTaskStatus(event.target.value)}><option value="">All statuses</option>{masters?.statuses.map(item => <option value={item.code} key={item.code}>{item.label}</option>)}</select></label><label>From<input type="date" value={from} onChange={event => setFrom(event.target.value)} /></label><label>To<input type="date" value={to} onChange={event => setTo(event.target.value)} /></label><label>Employee<select value={employeeId} onChange={event => setEmployeeId(event.target.value)}><option value="">All permitted employees</option>{masters?.employees.map(item => <option value={item.id} key={item.id}>{item.displayName}</option>)}</select></label><label>Client<select value={clientId} onChange={event => setClientId(event.target.value)}><option value="">All permitted clients</option>{masters?.clients.map(item => <option value={item.id} key={item.id}>{item.displayName}</option>)}</select></label><label>Service<select value={serviceId} onChange={event => setServiceId(event.target.value)}><option value="">All services</option>{masters?.services.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Billing flag<select value={billable} onChange={event => setBillable(event.target.value)}><option value="">Billable and non-billable</option><option value="true">Billable</option><option value="false">Non-billable</option></select></label><ReportButtons onRun={() => void run()} onExport={exportRows} canExport={canExport} /></section> : null}
    {selected === "PROJECTION" ? <section className="panel projection-report-link"><span>₹</span><div><h2>Use the explainable projection workspace</h2><p>It already provides month, client, primary-group, entity, service, team and manager totals with the same scoped CSV/XLSX detail.</p></div><button className="primary" onClick={onProjection}>Open projection</button></section> : null}
    {clients ? <><ReportSummary status={clients.byStatus} secondary={clients.byCategory} secondaryLabel="By category" /><section className="panel report-results"><ClientReportTable page={clients} /><ReportPager page={clients.page} totalPages={clients.totalPages} onPage={run} /></section></> : null}
    {tasks ? <><ReportSummary status={tasks.byStatus} secondary={tasks.byService} secondaryLabel="By service" /><section className="panel report-results"><TaskReportTable page={tasks} /><ReportPager page={tasks.page} totalPages={tasks.totalPages} onPage={run} /></section></> : null}
  </>;
}

function TeamsPanel({ employees }: { employees: Employee[] }) {
  const [teams, setTeams] = useState<Team[]>([]); const [notice, setNotice] = useState(""); const [open, setOpen] = useState(false);
  const load = useCallback(async () => {
    try { setTeams(await fetchJson<Team[]>("/api/v1/admin/teams")); setNotice(""); }
    catch (reason) { setNotice(messageFrom(reason)); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    try {
      await mutateJson("/api/v1/admin/teams", "POST", {
        code: data.get("code"), name: data.get("name"),
        managerEmployeeId: (data.get("managerEmployeeId") as string) || null
      });
      setOpen(false); form.reset(); await load();
    } catch (reason) { setNotice(messageFrom(reason)); }
  }
  return <section className="panel"><div className="panel-title"><div><h2>Teams</h2><p>A team is a group of staff who share the same clients. Putting a client service under a team is what lets team members see that client, so create a team before you expect anyone below administrator level to see work.</p></div><span className="state">{teams.length}</span></div>
    {notice ? <p className="error">{notice}</p> : null}
    <div className="record-list">{teams.map(team => <div className="record" key={team.id}><span><strong>{team.name}</strong><small>{team.code} · {team.memberCount} current member{team.memberCount === 1 ? "" : "s"}</small></span><span className={team.isActive ? "state" : "state state--warn"}>{team.isActive ? "Active" : "Inactive"}</span></div>)}
      {!teams.length ? <p className="muted">No teams yet. Everything is visible only to administrators until you add one.</p> : null}</div>
    {open
      ? <form className="employee-form" onSubmit={submit}>
          <label>Team code<input name="code" required maxLength={30} /><small>A short unique tag, for example GST or AUDIT. Used internally, not shown to clients.</small></label>
          <label>Team name<input name="name" required maxLength={100} /><small>What staff will recognise, for example "GST and Indirect Tax".</small></label>
          <label>Team manager<select name="managerEmployeeId"><option value="">No manager yet</option>{employees.map(employee => <option value={employee.id} key={employee.id}>{employee.displayName}</option>)}</select><small>The manager sees everything belonging to this team, even without being a member.</small></label>
          <div className="button-row form-span"><button className="primary">Create team</button><button type="button" className="quiet" onClick={() => setOpen(false)}>Cancel</button></div>
        </form>
      : <button className="secondary full" onClick={() => setOpen(true)}>Add a team</button>}
  </section>;
}

function EditEmployee({ employees, onSaved }: { employees: Employee[]; onSaved: () => Promise<void> }) {
  const [id, setId] = useState(""); const [error, setError] = useState("");
  const [departments, setDepartments] = useState<string[]>([]);
  const [newPassword, setNewPassword] = useState(""); const [showNew, setShowNew] = useState(false); const [passwordNote, setPasswordNote] = useState("");
  useEffect(() => { fetchJson<string[]>("/api/v1/admin/departments").then(setDepartments).catch(() => setDepartments([])); }, []);
  const employee = employees.find(item => item.id === id) ?? null;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form);
    try {
      await mutateJson(`/api/v1/admin/employees/${id}`, "PUT", {
        employeeCode: data.get("employeeCode"), displayName: data.get("displayName"),
        mobileNumber: (data.get("mobileNumber") as string) || null, email: (data.get("email") as string) || null,
        designation: (data.get("designation") as string) || null, department: (data.get("department") as string) || null,
        managerEmployeeId: (data.get("managerEmployeeId") as string) || null,
        joinedOn: (data.get("joinedOn") as string) || null, isActive: data.get("isActive") === "on"
      });
      setId(""); setError(""); await onSaved();
    } catch (reason) { setError(messageFrom(reason)); }
  }
  return <div className="access-editor"><label>Edit an employee<select value={id} onChange={event => { setId(event.target.value); setError(""); }}><option value="">Choose someone to edit</option>{employees.map(item => <option value={item.id} key={item.id}>{item.displayName} ({item.employeeCode})</option>)}</select></label>
    {employee ? <form className="employee-form" onSubmit={submit} key={employee.id}>
      <label>Employee code<input name="employeeCode" defaultValue={employee.employeeCode} required maxLength={30} /><small>Your internal staff reference. Must be unique.</small></label>
      <label>Name<input name="displayName" defaultValue={employee.displayName} required maxLength={200} /><small>Shown on tasks and reports.</small></label>
      <label>Mobile<input name="mobileNumber" defaultValue={employee.mobileNumber ?? ""} inputMode="numeric" maxLength={10} /><small>Contact number only. This does not change the number they sign in with.</small></label>
      <label>Email<input name="email" type="email" defaultValue={employee.email ?? ""} /><small>Optional. Not used for sign in.</small></label>
      <label>Designation<input name="designation" defaultValue={employee.designation ?? ""} /><small>For example Article, Paid Assistant, Manager.</small></label>
      <label>Department<input name="department" list="department-options" defaultValue={employee.department ?? ""} /><datalist id="department-options">{departments.map(item => <option value={item} key={item} />)}</datalist><small>Pick one already in use or type a new one, for example Audit or Taxation.</small></label>
      <label>Reports to<select name="managerEmployeeId" defaultValue={employee.managerEmployeeId ?? ""}><option value="">No manager</option>{employees.filter(item => item.id !== employee.id).map(item => <option value={item.id} key={item.id}>{item.displayName}</option>)}</select><small>Their manager can see their work under team-level permissions.</small></label>
      <label>Joined on<input name="joinedOn" type="date" defaultValue={employee.joinedOn ?? ""} /><small>Optional. Used for staff records only.</small></label>
      <label className="policy"><span><strong>Currently employed</strong><small>Turn off when someone leaves. Their past work and history stay intact.</small></span><input name="isActive" type="checkbox" defaultChecked={employee.isActive} /></label>
      {error ? <p className="error form-span">{error}</p> : null}
      <div className="button-row form-span"><button className="primary">Save changes</button><button type="button" className="quiet" onClick={() => setId("")}>Cancel</button></div>
    </form> : null}
    {employee ? (employee.userId
      ? <div className="password-reset">
          <h4>Reset their sign-in password</h4>
          <p className="muted">Issues a new temporary password. They are signed out everywhere and must choose their own password the next time they sign in. Read the new password to them; it is never shown again.</p>
          <label>New temporary password<span className="password-field"><input type={showNew ? "text" : "password"} value={newPassword} minLength={12} onChange={event => setNewPassword(event.target.value)} /><button type="button" className="quiet" onClick={() => setShowNew(current => !current)}>{showNew ? "Hide" : "Show"}</button></span><small>At least 12 characters, and it cannot contain their mobile number.</small></label>
          {passwordNote ? <p className={passwordNote.startsWith("Password") ? "muted" : "error"}>{passwordNote}</p> : null}
          <button type="button" className="secondary" disabled={newPassword.length < 12} onClick={async () => {
            try { await mutateJson(`/api/v1/admin/users/${employee.userId}/password`, "POST", { temporaryPassword: newPassword }); setPasswordNote("Password reset. Give it to them and they will be asked to change it."); setNewPassword(""); }
            catch (reason) { setPasswordNote(messageFrom(reason)); }
          }}>Reset password</button>
        </div>
      : <p className="muted">This person has no sign-in account, so there is no password to reset.</p>) : null}
  </div>;
}

function PeopleMappingPanel({ onChanged }: { onChanged: () => Promise<void> }) {
  const [data, setData] = useState<PeopleMappingPage | null>(null); const [notice, setNotice] = useState(""); const [busy, setBusy] = useState("");
  const load = useCallback(async () => {
    try { setData(await fetchJson<PeopleMappingPage>("/api/v1/admin/import/people")); setNotice(""); }
    catch (reason) { setNotice(messageFrom(reason)); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  async function assign(id: string, employeeId: string) {
    setBusy(id);
    try { await mutateJson(`/api/v1/admin/import/people/${id}`, "PUT", { employeeId: employeeId || null }); await load(); await onChanged(); }
    catch (reason) { setNotice(messageFrom(reason)); }
    finally { setBusy(""); }
  }
  async function createFor(item: PersonMapping) {
    setBusy(item.id);
    try { await mutateJson(`/api/v1/admin/import/people/${item.id}/employee`, "POST", { displayName: item.name, employeeCode: null }); await load(); await onChanged(); }
    catch (reason) { setNotice(messageFrom(reason)); }
    finally { setBusy(""); }
  }
  if (data && data.totalCount === 0) return null;
  return <section className="panel panel--wide"><div className="panel-title"><div><h2>People from the old spreadsheet</h2><p>Each name below owns work in the spreadsheet. Match it to a person, or add them as a new employee.</p></div><span className={data && data.unmappedCount === 0 ? "state" : "state state--warn"}>{data ? (data.unmappedCount === 0 ? "All matched" : `${data.unmappedCount} left`) : "Loading"}</span></div>
    {notice ? <p className="error">{notice}</p> : null}
    <div className="record-list">{data?.items.map(item => <div className="record mapping-row" key={item.id}>
      <span><strong>{item.name}</strong><small>{item.usedIn ?? "\u2014"}</small></span>
      <select aria-label={`Match ${item.name}`} value={item.employeeId ?? ""} disabled={busy === item.id} onChange={event => void assign(item.id, event.target.value)}>
        <option value="">Not matched yet</option>
        {data.employees.map(employee => <option value={employee.id} key={employee.id}>{employee.displayName} ({employee.employeeCode})</option>)}
      </select>
      {item.mapped ? <span className="state">Matched</span> : <button className="secondary" disabled={busy === item.id} onClick={() => void createFor(item)}>Add as new employee</button>}
    </div>)}</div>
    <small>New people added here can own work straight away. They cannot sign in until an administrator gives them a login.</small>
  </section>;
}

function OperationsPanel() {
  const [data, setData] = useState<Operations | null>(null); const [notice, setNotice] = useState("");
  useEffect(() => { fetchJson<Operations>("/api/v1/admin/operations").then(setData).catch(reason => setNotice(messageFrom(reason))); }, []);
  const run = data?.lastGenerationRun ?? null;
  const healthy = data?.databaseReachable && !data?.generationStale && (run?.errorCount ?? 0) === 0;
  return <section className="panel"><div className="panel-title"><div><h2>System health</h2><p>Database, recurring generation and audit retention at a glance.</p></div><span className={healthy ? "state" : "state state--warn"}>{data ? (healthy ? "Healthy" : "Needs attention") : "Checking"}</span></div>
    {notice ? <p className="error">{notice}</p> : null}
    <div className="ops-list">
      <span>Database<b>{data ? (data.databaseReachable ? "Reachable" : "Unreachable") : "—"}</b></span>
      <span>Applied migrations<b>{data?.appliedMigrations ?? "—"}</b></span>
      <span>Active recurrence rules<b>{data?.activeRecurrenceRules ?? "—"}</b></span>
      <span>Last generation<b>{run ? `${new Date(run.startedAtUtc).toLocaleString()} · ${run.status}` : "Never run"}</b></span>
      <span>Generated last run<b>{run ? `${run.createdCount} created, ${run.errorCount} errors` : "—"}</b></span>
      <span>Audit events stored<b>{data?.audit?.totalEvents ?? "—"}</b></span>
      <span>Oldest audit event<b>{data?.audit?.oldestEventUtc ? new Date(data.audit.oldestEventUtc).toLocaleDateString() : "—"}</b></span>
      <span>Retention<b>{data?.audit ? `${data.audit.generalRetentionMonths} months, security ${data.audit.securityRetentionMonths}` : "—"}</b></span>
    </div>
    {data?.generationStale ? <p className="error">No recurring generation has run in the last day. Check that the worker is running.</p> : null}
    {run?.errorSummary ? <p className="error">{run.errorSummary}</p> : null}
  </section>;
}

function AuditWorkspace() {
  const month = monthRange(todayValue().slice(0, 7));
  const [filters, setFilters] = useState<AuditFilters | null>(null); const [page, setPage] = useState<AuditPage | null>(null); const [notice, setNotice] = useState("");
  const [from, setFrom] = useState(month.from); const [to, setTo] = useState(todayValue()); const [action, setAction] = useState(""); const [entityType, setEntityType] = useState(""); const [actorUserId, setActorUserId] = useState(""); const [entityId, setEntityId] = useState("");
  const run = useCallback(async (requested = 1) => {
    try {
      const params = new URLSearchParams({ page: String(requested), pageSize: "50" });
      if (from) params.set("from", from); if (to) params.set("to", to);
      if (action) params.set("action", action); if (entityType) params.set("entityType", entityType);
      if (actorUserId) params.set("actorUserId", actorUserId); if (entityId.trim()) params.set("entityId", entityId.trim());
      setPage(await fetchJson<AuditPage>(`/api/v1/admin/audit?${params}`)); setNotice("");
    } catch (reason) { setNotice(messageFrom(reason)); }
  }, [from, to, action, entityType, actorUserId, entityId]);
  useEffect(() => { fetchJson<AuditFilters>("/api/v1/admin/audit/filters").then(setFilters).catch(reason => setNotice(messageFrom(reason))); void run(); }, []);
  return <><section className="workspace-hero"><div><span className="phase-badge">Phase 10 active</span><h1>Audit history</h1><p>Append-only record of significant changes. Audit history is not record-scoped, so every event in range is listed.</p></div><div className="metric-strip"><Metric value={page?.totalCount ?? 0} label="Events in range" /><Metric value={filters?.actions.length ?? 0} label="Recorded actions" /></div></section>
    <section className="panel report-filters report-filters--tasks"><label>From<input type="date" value={from} onChange={event => setFrom(event.target.value)} /></label><label>To<input type="date" value={to} onChange={event => setTo(event.target.value)} /></label><label>Action<select value={action} onChange={event => setAction(event.target.value)}><option value="">All actions</option>{filters?.actions.map(item => <option value={item} key={item}>{item}</option>)}</select></label><label>Entity type<select value={entityType} onChange={event => setEntityType(event.target.value)}><option value="">All entity types</option>{filters?.entityTypes.map(item => <option value={item} key={item}>{item}</option>)}</select></label><label>Actor<select value={actorUserId} onChange={event => setActorUserId(event.target.value)}><option value="">All actors</option>{filters?.actors.map(item => <option value={item.userId} key={item.userId}>{item.displayName}</option>)}</select></label><label>Entity id<input value={entityId} placeholder="Exact identifier" onChange={event => setEntityId(event.target.value)} /></label><div className="report-actions"><button className="primary" onClick={() => void run()}>Search audit</button></div></section>
    {notice ? <p className="error">{notice}</p> : null}
    {page ? <section className="panel report-results"><div className="report-table"><div className="audit-row report-row--head"><span>When</span><span>Actor</span><span>Action</span><span>Entity</span></div>{page.items.map(item => <article className="audit-row" key={item.id}><span>{new Date(item.occurredAtUtc).toLocaleString()}<small>{item.correlationId ?? "No correlation id"}</small></span><span>{item.actorName}</span><span><strong>{item.action}</strong>{item.reason ? <small>{item.reason}</small> : null}</span><span>{item.entityType}<small title={item.data}>{item.entityId ?? "—"}</small></span></article>)}{!page.items.length ? <p className="muted report-empty">No audit events match these filters.</p> : null}</div><ReportPager page={page.page} totalPages={page.totalPages} onPage={run} /></section> : null}
  </>;
}

function ReportButtons({ onRun, onExport, canExport }: { onRun: () => void; onExport: (format: "csv" | "xlsx") => Promise<void>; canExport: boolean }) { return <div className="report-actions"><button className="primary" onClick={onRun}>Run report</button>{canExport ? <><button className="secondary" onClick={() => void onExport("csv")}>CSV</button><button className="secondary" onClick={() => void onExport("xlsx")}>XLSX</button></> : null}</div>; }
function ReportSummary({ status, secondary, secondaryLabel }: { status: { key: string; label: string; value: number }[]; secondary: { key: string; label: string; value: number }[]; secondaryLabel: string }) { return <div className="report-summary"><section className="panel"><h2>By status</h2>{status.map(item => <span key={item.key}>{item.label}<b>{item.value}</b></span>)}</section><section className="panel"><h2>{secondaryLabel}</h2>{secondary.map(item => <span key={item.key}>{item.label}<b>{item.value}</b></span>)}</section></div>; }
function ClientReportTable({ page }: { page: ClientReportPage }) { return <div className="report-table"><div className="client-report-row report-row--head"><span>Client</span><span>Category / group</span><span>Tax profile</span><span>Status</span></div>{page.items.map(item => <article className="client-report-row" key={item.id}><span><strong>{item.displayName}</strong><small>{item.clientCode}</small></span><span>{item.category ?? "Unclassified"}<small>{item.primaryGroup ?? "No primary group"}</small></span><span>{item.pan ?? "PAN not recorded"}<small>{item.gstinCount} active GSTIN{item.gstinCount === 1 ? "" : "s"}</small></span><b className="state">{item.status}</b></article>)}{!page.items.length ? <p className="muted report-empty">No clients match these filters.</p> : null}</div>; }
function TaskReportTable({ page }: { page: TaskReportPage }) { return <div className="report-table"><div className="task-report-row report-row--head"><span>Task</span><span>Client / service</span><span>Due / status</span><span>Employee</span></div>{page.items.map(item => <article className="task-report-row" key={item.id}><span><strong>#{item.taskNumber} · {item.title}</strong><small>{item.billable ? "Billable" : "Non-billable"} · {item.priority}</small></span><span>{item.clientName}<small>{item.clientCode} · {item.serviceName}</small></span><span>{item.dueDate}<small>{item.statusLabel}</small></span><span>{item.primaryAssignee ?? "Unassigned"}</span></article>)}{!page.items.length ? <p className="muted report-empty">No tasks match these filters.</p> : null}</div>; }
function ReportPager({ page, totalPages, onPage }: { page: number; totalPages: number; onPage: (page: number) => Promise<void> }) { return <div className="pager"><button className="quiet" disabled={page <= 1} onClick={() => void onPage(page - 1)}>Previous</button><span>Page {page} of {Math.max(1, totalPages)}</span><button className="quiet" disabled={page >= totalPages} onClick={() => void onPage(page + 1)}>Next</button></div>; }

function ProjectionWorkspace({ session }: { session: Session }) {
  const financialYear = currentFinancialYearRange();
  const [from, setFrom] = useState(financialYear.from); const [to, setTo] = useState(financialYear.to); const [asOf, setAsOf] = useState(todayValue());
  const [clientId, setClientId] = useState(""); const [groupId, setGroupId] = useState(""); const [serviceId, setServiceId] = useState(""); const [entityId, setEntityId] = useState(""); const [teamId, setTeamId] = useState("");
  const [masters, setMasters] = useState<ProjectionMasters | null>(null); const [report, setReport] = useState<ProjectionReport | null>(null);
  const [dimension, setDimension] = useState<"months" | "quarters" | "financialYears" | "clients" | "groups" | "billingEntities" | "services" | "teams" | "employees">("months");
  const [notice, setNotice] = useState(""); const [loading, setLoading] = useState(false); const canExport = "reports.export" in session.permissions;
  const request = useCallback(() => ({ from, to, asOf, clientId: clientId || null, groupId: groupId || null, serviceId: serviceId || null, billingEntityId: entityId || null, teamId: teamId || null, employeeId: null }), [from, to, asOf, clientId, groupId, serviceId, entityId, teamId]);
  useEffect(() => { void fetchJson<ProjectionMasters>("/api/v1/billing-projections/masters").then(setMasters).catch(reason => setNotice(messageFrom(reason))); }, []);
  async function calculate() { setLoading(true); try { setReport(await mutateJson<ProjectionReport>("/api/v1/billing-projections:calculate", "POST", request())); setNotice(""); } catch (reason) { setNotice(messageFrom(reason)); } finally { setLoading(false); } }
  async function exportReport(format: "csv" | "xlsx") { try { await downloadFile("/api/v1/billing-projections:export", { format, projection: request() }, `billing-projection-${from.replaceAll("-", "")}-${to.replaceAll("-", "")}.${format}`); } catch (reason) { setNotice(messageFrom(reason)); } }
  const summaries = report?.[dimension] ?? [];
  return <><section className="workspace-hero projection-hero"><div><span className="phase-badge">Phase 8 active</span><h1>Billing projection</h1><p>Calculate expected fixed fees from effective-dated terms. Every result retains its source term, schedule and dimensional explanation.</p></div><div className="projection-total-strip">{report?.totals.length ? report.totals.map(total => <div key={total.key}><strong>{money(total.amount, total.currencyCode)}</strong><small>{total.occurrenceCount} billing events</small></div>) : <div><strong>—</strong><small>Calculate a period</small></div>}</div></section>
    <section className="projection-filters panel"><label>From<input type="date" value={from} onChange={event => setFrom(event.target.value)} /></label><label>To<input type="date" value={to} onChange={event => setTo(event.target.value)} /></label><label>As of<input type="date" value={asOf} onChange={event => setAsOf(event.target.value)} /></label><label>Client<select value={clientId} onChange={event => setClientId(event.target.value)}><option value="">All permitted clients</option>{masters?.clients.map(item => <option value={item.id} key={item.id}>{item.displayName} · {item.clientCode}</option>)}</select></label><label>Primary group<select value={groupId} onChange={event => setGroupId(event.target.value)}><option value="">All primary groups</option>{masters?.groups.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Service<select value={serviceId} onChange={event => setServiceId(event.target.value)}><option value="">All services</option>{masters?.services.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Billing entity<select value={entityId} onChange={event => setEntityId(event.target.value)}><option value="">All billing entities</option>{masters?.entities.map(item => <option value={item.id} key={item.id}>{item.legalName}</option>)}</select></label><label>Responsible team<select value={teamId} onChange={event => setTeamId(event.target.value)}><option value="">All responsible teams</option>{masters?.teams.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><button className="primary" disabled={loading} onClick={() => void calculate()}>{loading ? "Calculating…" : "Calculate projection"}</button></section>
    {notice ? <p className="error">{notice}</p> : null}{report ? <><section className="projection-definition"><strong>Projection, not billing issued.</strong><span>{report.definition}</span><small>As of {report.asOf} · generated {new Date(report.generatedAtUtc).toLocaleString("en-IN")} · Asia/Kolkata reporting context</small></section>
      <div className="projection-layout"><section className="panel projection-summary"><div className="panel-title"><div><h2>Dimensional totals</h2><p>Each total remains inside one currency.</p></div><select aria-label="Projection grouping" value={dimension} onChange={event => setDimension(event.target.value as typeof dimension)}><option value="months">Month</option><option value="quarters">Calendar quarter</option><option value="financialYears">Financial year</option><option value="clients">Client</option><option value="groups">Primary group</option><option value="billingEntities">Billing entity</option><option value="services">Service</option><option value="teams">Responsible team</option><option value="employees">Responsible manager</option></select></div><div className="projection-bars">{summaries.map(item => { const currencyMaximum = Math.max(...summaries.filter(candidate => candidate.currencyCode === item.currencyCode).map(candidate => candidate.amount), 1); return <article key={item.key}><span><strong>{item.label}</strong><small>{item.occurrenceCount} event{item.occurrenceCount === 1 ? "" : "s"}</small></span><div><i style={{ width: `${Math.max(2, item.amount / currencyMaximum * 100)}%` }} /></div><b>{money(item.amount, item.currencyCode)}</b></article>; })}{!summaries.length ? <p className="muted">No projected billing falls in this period and filter combination.</p> : null}</div></section>
        <aside className="panel projection-assumptions"><div className="panel-title"><div><h2>Calculation assumptions</h2><p>Visible with every result.</p></div></div><ul>{report.assumptions.map(item => <li key={item}>{item}</li>)}</ul>{canExport ? <div className="export-actions"><button className="secondary" onClick={() => void exportReport("csv")}>Export CSV</button><button className="secondary" onClick={() => void exportReport("xlsx")}>Export XLSX</button></div> : <small>Ask an administrator for reports.export permission to download detail.</small>}</aside></div>
      <section className="panel projection-detail"><div className="panel-title"><div><h2>Explainable billing events</h2><p>{report.details.length} rows · sorted by projection date</p></div></div><div className="projection-row projection-row--head"><span>Date / period</span><span>Client / group</span><span>Service / entity</span><span>Amount</span></div>{report.details.slice(0, 300).map(item => <article className="projection-row" key={`${item.termId}-${item.projectionDate}`} title={item.explanation}><span><strong>{item.projectionDate}</strong><small>{item.servicePeriodStart} to {item.servicePeriodEnd}</small></span><span><strong>{item.clientName}</strong><small>{item.clientCode} · {item.groupName}</small></span><span><strong>{item.serviceName}</strong><small>{item.billingEntityName} · Term v{item.termVersion} · {frequencyLabel(item.frequencyCode)}</small></span><span><strong>{money(item.amount, item.currencyCode)}</strong><small>{item.taxInclusive ? "Tax inclusive" : "Tax treatment separate"}</small></span></article>)}{report.details.length > 300 ? <p className="setup-box">Showing the first 300 events. Export CSV or XLSX for the complete scoped detail.</p> : null}</section></> : <section className="panel projection-empty"><span>₹</span><h2>Choose a period and calculate</h2><p>Current financial year dates are prefilled. Add filters only when you need a narrower projection.</p></section>}
  </>;
}

function BillingWorkspace({ session }: { session: Session }) {
  const [entities, setEntities] = useState<BillingEntityItem[]>([]); const [terms, setTerms] = useState<BillingTermItem[]>([]); const [masters, setMasters] = useState<BillingMasters | null>(null);
  const [editingEntity, setEditingEntity] = useState<BillingEntityItem | null>(null);
  const [agreementFilter, setAgreementFilter] = useState(""); const [showEntity, setShowEntity] = useState(false); const [showTerm, setShowTerm] = useState(false); const [replacement, setReplacement] = useState<BillingTermItem | null>(null); const [notice, setNotice] = useState("");
  const canConfigure = "billing.configure" in session.permissions; const allConfigure = session.permissions["billing.configure"] === "ALL";
  const load = useCallback(async () => { try { const [entityData, termData, masterData] = await Promise.all([fetchJson<BillingEntityItem[]>("/api/v1/billing/entities?includeInactive=true"), fetchJson<BillingTermItem[]>(`/api/v1/billing/terms${agreementFilter ? `?clientServiceId=${agreementFilter}` : ""}`), fetchJson<BillingMasters>("/api/v1/billing/masters")]); setEntities(entityData); setTerms(termData); setMasters(masterData); setNotice(""); } catch (reason) { setNotice(messageFrom(reason)); } }, [agreementFilter]);
  useEffect(() => { void load(); }, [load]);
  // Removing a fee is a correction, not a way to rewrite what was agreed, so it asks why and only
  // the current version can go. Removing a revision reopens the fee it replaced.
  async function removeTerm(term: BillingTermItem) {
    const reason = window.prompt(`Why is this fee being removed?\n\n${term.clientName} · ${term.serviceName}\nVersion ${term.version} from ${term.effectiveFrom}\n\nIf this replaced an earlier fee, that earlier fee becomes current again.`);
    if (!reason?.trim()) return;
    try { await mutateJson(`/api/v1/billing/terms/${term.id}/remove`, "POST", { reason }); await load(); }
    catch (error) { setNotice(messageFrom(error)); }
  }

  async function status(entity: BillingEntityItem) { const reason = window.prompt(`Reason to ${entity.isActive ? "deactivate" : "reactivate"} ${entity.legalName}`); if (!reason) return; try { await mutateJson(`/api/v1/billing/entities/${entity.id}/status`, "POST", { isActive: !entity.isActive, reason, expectedVersion: entity.rowVersion }); await load(); } catch (error) { setNotice(messageFrom(error)); } }
  return <><section className="workspace-hero billing-hero"><div><span className="phase-badge">Phase 7 active</span><h1>Billing configuration</h1><p>Legal billing entities and effective-dated fixed fees. Billing schedules are independent from task recurrence.</p></div><div className="metric-strip"><Metric value={entities.filter(x => x.isActive).length} label="Billing entities" /><Metric value={terms.length} label="Fee versions" /></div></section>
    {notice ? <p className="error">{notice}</p> : null}<section className="billing-toolbar"><label>Client service timeline<select value={agreementFilter} onChange={event => setAgreementFilter(event.target.value)}><option value="">All accessible agreements</option>{masters?.agreements.map(item => <option value={item.id} key={item.id}>{item.clientName} · {item.serviceName}{item.gstin ? ` · ${item.gstin}` : ""}</option>)}</select></label>{allConfigure ? <button className="secondary" onClick={() => setShowEntity(true)}>Add billing entity</button> : null}{canConfigure ? <button className="primary" disabled={!masters?.agreements.length || !masters?.entities.length} onClick={() => setShowTerm(true)}>Add fee term</button> : null}</section>
    {!masters?.entities.length ? <div className="setup-box"><strong>No legal billing entity has been confirmed.</strong><br />Add the firm’s validated legal entity before configuring billable fees. The workbook value <code>Cash</code> has intentionally not been created as an entity.</div> : null}
    <div className="billing-layout"><section className="panel"><div className="panel-title"><div><h2>Legal billing entities</h2><p>Historical entities remain retained when inactive.</p></div></div><div className="billing-entities">{entities.map(entity => <article className={entity.isActive ? "" : "catalogue-card--off"} key={entity.id}><span><strong>{entity.legalName}</strong><small>{entity.code}{entity.gstin ? ` · ${entity.gstin}` : " · GSTIN not recorded"}</small></span><span><b>{entity.currencyCode}</b><small>{entity.effectiveFrom}{entity.effectiveTo ? ` to ${entity.effectiveTo}` : " onward"}</small></span>{allConfigure ? <><button className="quiet" onClick={() => setEditingEntity(entity)}>Edit</button><button className="quiet" onClick={() => void status(entity)}>{entity.isActive ? "Deactivate" : "Reactivate"}</button></> : null}</article>)}</div></section>
      <section className="panel panel--wide"><div className="panel-title"><div><h2>Effective-dated fee timeline</h2><p>Each revision closes the previous fee without overwriting it, so past work stays priced as it was agreed. Only the current fee can be removed, and only as a correction.</p></div></div><div className="billing-terms">{terms.map(term => <article key={term.id}><span><strong>{term.clientName} · {term.serviceName}</strong><small>{term.clientCode}{term.gstin ? ` · ${term.gstin}` : " · Client-wide"} · Version {term.version}</small></span><span><strong>{term.isBillable && term.amount !== null ? money(term.amount, term.currencyCode) : "Non-billable"}</strong><small>{term.billingEntityName ?? "No billing entity"} · {term.schedule ? frequencyLabel(term.schedule.frequencyCode) : "No schedule"}</small></span><span><b>{term.effectiveFrom}</b><small>{term.effectiveTo ? `to ${term.effectiveTo}` : "Current"}</small></span><span className="term-actions">{canConfigure && term.effectiveTo === null && term.agreementIsActive ? <><button className="quiet" onClick={() => setReplacement(term)}>Revise fee</button><button className="quiet" onClick={() => void removeTerm(term)}>Remove</button></> : null}{canConfigure && term.effectiveTo === null && !term.agreementIsActive ? <small className="muted">Agreement closed</small> : null}</span></article>)}</div></section></div>
    {showEntity && masters ? <CreateBillingEntity masters={masters} onClose={() => setShowEntity(false)} onCreated={async () => { setShowEntity(false); await load(); }} /> : null}
    {editingEntity && masters ? <CreateBillingEntity masters={masters} existing={editingEntity} onClose={() => setEditingEntity(null)} onCreated={async () => { setEditingEntity(null); await load(); }} /> : null}
    {showTerm && masters ? <CreateBillingTerm masters={masters} onClose={() => setShowTerm(false)} onCreated={async () => { setShowTerm(false); await load(); }} /> : null}
    {replacement && masters ? <CreateBillingTerm masters={masters} replacement={replacement} onClose={() => setReplacement(null)} onCreated={async () => { setReplacement(null); await load(); }} /> : null}
  </>;
}

function CreateBillingEntity({ masters, existing, onClose, onCreated }: { masters: BillingMasters; existing?: BillingEntityItem | null; onClose: () => void; onCreated: () => Promise<void> }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    const body = { code: data.get("code"), legalName: data.get("legalName"), tradeName: data.get("tradeName") || null, pan: data.get("pan") || null, gstin: data.get("gstin") || null, address: data.get("address") || null, email: data.get("email") || null, phone: data.get("phone") || null, currencyCode: data.get("currencyCode"), effectiveFrom: data.get("effectiveFrom"), effectiveTo: data.get("effectiveTo") || null, expectedVersion: existing?.rowVersion ?? 0 };
    try {
      if (existing) await mutateJson(`/api/v1/billing/entities/${existing.id}`, "PUT", body);
      else await mutateJson("/api/v1/billing/entities", "POST", body);
      await onCreated();
    } catch (reason) { setError(messageFrom(reason)); }
  }
  const required = masters.requiredEntityFields;
  return <Modal title={existing ? "Edit billing entity" : "Add legal billing entity"} detail="The registered firm or legal entity that will issue invoices. This is a legal entity, not a payment mode: never enter Cash here." onClose={onClose}><form className="client-form" onSubmit={submit}>
    <label>Entity code<input name="code" required maxLength={30} defaultValue={existing?.code} /><small>Short internal tag, for example MAIN.</small></label>
    <label>Legal name<input name="legalName" required maxLength={200} defaultValue={existing?.legalName} /><small>Exactly as registered. This appears on invoices.</small></label>
    <label>Trade name<input name="tradeName" required={required.includes("tradeName")} defaultValue={existing?.tradeName ?? ""} /><small>The name you trade under, if different.</small></label>
    <label>PAN<input name="pan" required={required.includes("pan")} maxLength={10} defaultValue={existing?.pan ?? ""} /><small>The firm's own PAN.</small></label>
    <label>GSTIN<input name="gstin" required={required.includes("gstin")} maxLength={15} defaultValue={existing?.gstin ?? ""} /><small>The firm's own GST registration.</small></label>
    <label>Currency<input name="currencyCode" defaultValue={existing?.currencyCode ?? "INR"} required maxLength={3} /><small>Three-letter code. Totals are never mixed across currencies.</small></label>
    <label>Effective from<input name="effectiveFrom" type="date" defaultValue={existing?.effectiveFrom ?? todayValue()} required /><small>When this entity started issuing invoices.</small></label>
    <label>Effective to<input name="effectiveTo" type="date" defaultValue={existing?.effectiveTo ?? ""} /><small>Leave blank while it is still in use.</small></label>
    <label>Email<input name="email" type="email" required={required.includes("email")} defaultValue={existing?.email ?? ""} /><small>Shown on invoices.</small></label>
    <label>Phone<input name="phone" required={required.includes("phone")} defaultValue={existing?.phone ?? ""} /><small>Shown on invoices.</small></label>
    <label className="form-span">Registered address<input name="address" required={required.includes("address")} defaultValue={existing?.address ?? ""} /><small>The registered office address for invoicing.</small></label>
    {error ? <p className="error form-span">{error}</p> : null}
    <div className="button-row form-span"><button className="primary">{existing ? "Save entity" : "Create entity"}</button><button type="button" className="quiet" onClick={onClose}>Cancel</button></div>
  </form></Modal>;
}

function CreateBillingTerm({ masters, replacement, onClose, onCreated }: { masters: BillingMasters; replacement?: BillingTermItem; onClose: () => void; onCreated: () => Promise<void> }) {
  const [agreementId, setAgreementId] = useState(replacement?.clientServiceId ?? masters.agreements[0]?.id ?? ""); const [billable, setBillable] = useState(replacement?.isBillable ?? true); const [frequency, setFrequency] = useState(replacement?.schedule?.frequencyCode ?? "MONTHLY"); const [error, setError] = useState("");
  const agreement = masters.agreements.find(item => item.id === agreementId); const existingEntity = replacement?.billingEntityId ?? masters.entities[0]?.id ?? "";
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); const months = String(data.get("months") ?? "").split(",").map(value => Number(value.trim())).filter(value => Number.isInteger(value) && value > 0); const oneTime = frequency === "ONE_TIME"; const body = { clientServiceId: agreementId, isBillable: billable, billingEntityId: billable ? data.get("billingEntityId") : null, amount: billable ? Number(data.get("amount")) : null, currencyCode: billable ? data.get("currencyCode") : "INR", taxInclusive: billable && data.get("taxInclusive") === "on", effectiveFrom: data.get("effectiveFrom"), effectiveTo: data.get("effectiveTo") || null, notes: data.get("notes") || null, schedule: billable ? { frequencyCode: frequency, anchorDate: oneTime ? null : data.get("anchorDate"), billingDay: oneTime ? null : Number(data.get("billingDay")), businessDayAdjustment: data.get("businessDayAdjustment"), oneTimeDate: oneTime ? data.get("oneTimeDate") : null, months: frequency === "SPECIFIC_MONTH" || frequency === "CUSTOM_MONTHS" ? months : [] } : null }; try { await mutateJson(replacement ? `/api/v1/billing/terms/${replacement.id}/replace` : "/api/v1/billing/terms", "POST", body); await onCreated(); } catch (reason) { setError(messageFrom(reason)); } }
  return <Modal title={replacement ? "Replace fee term" : "Add fee term"} detail="The amount is the fixed fee for each billing event. Replacements preserve the earlier commercial history." onClose={onClose}><form className="client-form" onSubmit={submit}><label className="form-span">Client service agreement<select value={agreementId} disabled={!!replacement} onChange={event => setAgreementId(event.target.value)} required>{masters.agreements.map(item => <option value={item.id} key={item.id}>{item.clientName} · {item.serviceName}{item.gstin ? ` · ${item.gstin}` : ""}</option>)}</select></label><label className="check-label"><input type="checkbox" checked={billable} onChange={event => setBillable(event.target.checked)} />Billable fixed fee</label><label>Effective from<input name="effectiveFrom" type="date" min={replacement ? nextDay(replacement.effectiveFrom) : agreement?.effectiveFrom} defaultValue={replacement ? todayValue() : agreement?.effectiveFrom ?? todayValue()} required /></label><label>Effective to<input name="effectiveTo" type="date" max={agreement?.effectiveTo ?? undefined} /></label>{billable ? <><label>Billing entity<select name="billingEntityId" defaultValue={existingEntity} required>{masters.entities.map(item => <option value={item.id} key={item.id}>{item.legalName} · {item.code}</option>)}</select></label><label>Fee per billing event<input name="amount" type="number" min="0" step="0.01" defaultValue={replacement?.amount ?? ""} required /></label><label>Currency<input name="currencyCode" defaultValue={replacement?.currencyCode ?? "INR"} maxLength={3} required /></label><label>Frequency<select value={frequency} onChange={event => setFrequency(event.target.value)}>{masters.frequencies.map(item => <option value={item} key={item}>{frequencyLabel(item)}</option>)}</select></label>{frequency === "ONE_TIME" ? <label>One-time billing date<input name="oneTimeDate" type="date" defaultValue={replacement?.schedule?.oneTimeDate ?? todayValue()} required /></label> : <><label>Anchor date<input name="anchorDate" type="date" defaultValue={replacement?.schedule?.anchorDate ?? agreement?.effectiveFrom ?? todayValue()} required /></label><label>Billing day<input name="billingDay" type="number" min="1" max="31" defaultValue={replacement?.schedule?.billingDay ?? 1} required /></label></>}{frequency === "SPECIFIC_MONTH" || frequency === "CUSTOM_MONTHS" ? <label className="form-span">{frequency === "SPECIFIC_MONTH" ? "Billing month number" : "Billing months, comma separated"}<input name="months" defaultValue={replacement?.schedule?.months.join(",") ?? ""} placeholder={frequency === "SPECIFIC_MONTH" ? "4" : "1,4,7,10"} required /></label> : null}<label>Business-day adjustment<select name="businessDayAdjustment" defaultValue={replacement?.schedule?.businessDayAdjustment ?? "NONE"}>{masters.businessDayAdjustments.map(item => <option value={item} key={item}>{item === "NONE" ? "No adjustment" : item === "PREVIOUS" ? "Previous business day" : "Next business day"}</option>)}</select></label><label className="check-label"><input name="taxInclusive" type="checkbox" defaultChecked={replacement?.taxInclusive} />Fee includes applicable tax</label></> : null}<label className="form-span">Commercial notes<input name="notes" defaultValue={replacement?.notes ?? ""} required={masters.requiredTermFields.includes("notes")} /></label>{error ? <p className="error form-span">{error}</p> : null}<div className="button-row form-span"><button className="primary">{replacement ? "Create replacement" : "Create fee term"}</button><button type="button" className="quiet" onClick={onClose}>Cancel</button></div></form></Modal>;
}

function todayValue() { return new Date().toISOString().slice(0, 10); }
function currentFinancialYearRange() { const today = new Date(); const year = today.getMonth() + 1 >= 4 ? today.getFullYear() : today.getFullYear() - 1; return { from: `${year}-04-01`, to: `${year + 1}-03-31` }; }
function nextDay(value: string) { const date = new Date(`${value}T00:00:00Z`); date.setUTCDate(date.getUTCDate() + 1); return date.toISOString().slice(0, 10); }
function money(value: number, currency: string) { return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 2 }).format(value); }
function frequencyLabel(value: string) { return value.toLowerCase().split("_").map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(" "); }

function SchedulingWorkspace({ session }: { session: Session }) {
  const today = new Date();
  const [month, setMonth] = useState(`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`);
  const [calendar, setCalendar] = useState<CalendarData>({ from: "", to: "", tasks: [], countsByDate: {} });
  const [rules, setRules] = useState<ScheduleRule[]>([]); const [runs, setRuns] = useState<GenerationRun[]>([]); const [masters, setMasters] = useState<ScheduleMasters | null>(null);
  const [notice, setNotice] = useState(""); const [creating, setCreating] = useState(false);
  const canViewCalendar = "calendar.view" in session.permissions; const canViewScheduling = "scheduling.view" in session.permissions;
  const canManage = "scheduling.manage" in session.permissions; const canGenerate = "scheduling.generate" in session.permissions; const canManageHolidays = "scheduling.holidays.manage" in session.permissions;
  const range = monthRange(month);
  const load = useCallback(async () => {
    try {
      const calendarRequest = canViewCalendar ? fetchJson<CalendarData>(`/api/v1/calendar?from=${range.from}&to=${range.to}`) : Promise.resolve({ from: range.from, to: range.to, tasks: [], countsByDate: {} });
      const schedulingRequests = canViewScheduling ? Promise.all([fetchJson<ScheduleRule[]>("/api/v1/scheduling/rules?includeInactive=false"), fetchJson<GenerationRun[]>("/api/v1/scheduling/runs?take=8"), fetchJson<ScheduleMasters>("/api/v1/scheduling/masters")]) : Promise.resolve([[], [], null] as [ScheduleRule[], GenerationRun[], ScheduleMasters | null]);
      const [calendarData, [ruleData, runData, masterData]] = await Promise.all([calendarRequest, schedulingRequests]);
      setCalendar(calendarData); setRules(ruleData); setRuns(runData); setMasters(masterData); setNotice("");
    } catch (reason) { setNotice(messageFrom(reason)); }
  }, [canViewCalendar, canViewScheduling, range.from, range.to]);
  useEffect(() => { void load(); }, [load]);
  async function generate() { try { await mutateJson("/api/v1/scheduling/generate", "POST", { windowFrom: range.from, windowTo: range.to }); await load(); } catch (reason) { setNotice(messageFrom(reason)); } }
  async function addHoliday() { const date = window.prompt("Holiday date (YYYY-MM-DD)", `${month}-01`); if (!date) return; const name = window.prompt("Holiday name"); if (!name) return; try { await mutateJson("/api/v1/scheduling/holidays", "POST", { holidayCalendarId: masters?.defaults.holidayCalendarId ?? null, date, name, holidayType: "Firm", isWorkingDayOverride: false, notes: null }); await load(); } catch (reason) { setNotice(messageFrom(reason)); } }
  const days = calendarDays(month, calendar.tasks);
  const latestRun = runs[0];
  return <>
    <section className="workspace-hero calendar-hero"><div><span className="phase-badge">Phase 6 active</span><h1>Calendar & recurring work</h1><p>Versioned schedules create each occurrence once, with configurable holidays and visible generator health.</p></div><div className="metric-strip"><Metric value={calendar.tasks.length} label="Tasks this month" /><Metric value={rules.length} label="Active schedules" /><Metric value={latestRun?.errorCount ?? 0} label="Latest run errors" /></div></section>
    <section className="calendar-toolbar"><label>Month<input type="month" value={month} onChange={event => setMonth(event.target.value)} /></label><div className="button-row">{canGenerate ? <button className="secondary" onClick={() => void generate()}>Generate this month</button> : null}{canManageHolidays ? <button className="secondary" onClick={() => void addHoliday()}>Add holiday</button> : null}{canManage && masters ? <button className="primary" onClick={() => setCreating(true)}>New schedule</button> : null}</div></section>
    {notice ? <p className="error">{notice}</p> : null}
    {canViewCalendar ? <section className="panel calendar-panel"><div className="calendar-weekdays">{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => <span key={day}>{day}</span>)}</div><div className="calendar-grid">{days.map((day, index) => day ? <article className={`calendar-day ${day.date === localDate() ? "calendar-day--today" : ""}`} key={day.date}><strong>{Number(day.date.slice(-2))}</strong><div>{day.tasks.slice(0, 4).map(task => <span className="calendar-task" style={{ borderLeftColor: task.status.color }} key={task.id}><b>#{task.taskNumber}</b> {task.title}<small>{task.clientName} · {task.primaryAssignee ?? "Unassigned"}</small></span>)}{day.tasks.length > 4 ? <small>+{day.tasks.length - 4} more</small> : null}</div></article> : <span className="calendar-day calendar-day--blank" key={`blank-${index}`} />)}</div></section> : null}
    {canViewScheduling ? <div className="schedule-layout"><section className="panel"><div className="panel-title"><div><h2>Active schedules</h2><p>Editing creates a new effective-dated version; prior rules remain auditable.</p></div></div><div className="schedule-list">{rules.map(rule => <article key={rule.id}><span><strong>{rule.clientName}</strong><small>{rule.serviceName}{rule.gstin ? ` · ${rule.gstin}` : ""}</small></span><span><b>{rule.frequencyCode.replaceAll("_", " ")}</b><small>Due day {rule.dueDay} · {rule.generateLeadDays}-day lead</small></span><span className="state">v{rule.ruleVersion}</span></article>)}{rules.length === 0 ? <p className="muted">No recurring schedules have been configured.</p> : null}</div></section><aside className="panel"><div className="panel-title"><div><h2>Generator health</h2><p>Concurrent runs are locked and every outcome is retained.</p></div></div><div className="run-list">{runs.map(run => <article key={run.id}><span className={`state ${run.errorCount ? "state--warn" : ""}`}>{run.status}</span><strong>{run.createdCount} created · {run.existingCount} existing</strong><small>{new Date(run.startedAtUtc).toLocaleString()} · {run.trigger.toLowerCase()}</small></article>)}{runs.length === 0 ? <p className="muted">The worker has not recorded a run yet.</p> : null}</div></aside></div> : null}
    {creating && masters ? <CreateSchedule masters={masters} onClose={() => setCreating(false)} onCreated={async () => { setCreating(false); await load(); }} /> : null}
  </>;
}

function CreateSchedule({ masters, onClose, onCreated }: { masters: ScheduleMasters; onClose: () => void; onCreated: () => Promise<void> }) {
  const [error, setError] = useState(""); const [preview, setPreview] = useState<SchedulePreview[]>([]);
  function payload(form: HTMLFormElement) { const data = new FormData(form); return { clientServiceId: data.get("clientServiceId"), holidayCalendarId: data.get("holidayCalendarId"), defaultPrimaryAssigneeId: data.get("defaultPrimaryAssigneeId") || null, frequencyCode: data.get("frequencyCode"), intervalCount: Number(data.get("intervalCount")), anchorDate: data.get("anchorDate"), dueDay: Number(data.get("dueDay")), dueMonthOffset: Number(data.get("dueMonthOffset")), dueDayOffset: 0, businessDayAdjustment: data.get("businessDayAdjustment"), generateLeadDays: Number(data.get("generateLeadDays")), effectiveFrom: data.get("effectiveFrom"), effectiveTo: null, months: [], expectedVersion: 0 }; }
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const rule = payload(event.currentTarget); const action = ((event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null)?.value; try { if (action === "preview") { const start = String(rule.effectiveFrom); const year = Number(start.slice(0, 4)); setPreview(await mutateJson<SchedulePreview[]>("/api/v1/scheduling/preview", "POST", { rule, windowFrom: `${year}-01-01`, windowTo: `${year}-12-31` })); } else { await mutateJson("/api/v1/scheduling/rules", "POST", rule); await onCreated(); } setError(""); } catch (reason) { setError(messageFrom(reason)); } }
  const today = localDate();
  return <Modal title="Create recurring schedule" detail="Preview the rule before saving. No statutory due dates are assumed by the system." onClose={onClose}><form className="client-form" onSubmit={submit}><label className="form-span">Client service<select name="clientServiceId" required>{masters.agreements.map(item => <option value={item.id} key={item.id}>{item.clientName} · {item.serviceName}{item.gstin ? ` · ${item.gstin}` : ""}</option>)}</select></label><label>Frequency<select name="frequencyCode"><option value="MONTHLY">Monthly</option><option value="QUARTERLY">Quarterly</option><option value="HALF_YEARLY">Half-yearly</option><option value="YEARLY">Yearly</option></select></label><label>Interval<input name="intervalCount" type="number" min="1" max="24" defaultValue="1" required /></label><label>Anchor month<input name="anchorDate" type="date" defaultValue={today.slice(0, 8) + "01"} required /></label><label>Effective from<input name="effectiveFrom" type="date" defaultValue={today} required /></label><label>Due day<input name="dueDay" type="number" min="1" max="31" defaultValue="20" required /></label><label>Due month offset<input name="dueMonthOffset" type="number" min="0" max="24" defaultValue="1" required /></label><label>Business-day rule<select name="businessDayAdjustment"><option value="NEXT_BUSINESS_DAY">Next business day</option><option value="PREVIOUS_BUSINESS_DAY">Previous business day</option><option value="NONE">No adjustment</option></select></label><label>Generation lead days<input name="generateLeadDays" type="number" min="0" max="365" defaultValue="21" required /></label><label>Primary assignee<select name="defaultPrimaryAssigneeId"><option value="">Unassigned</option>{masters.employees.map(item => <option value={item.id} key={item.id}>{item.displayName}</option>)}</select></label><label>Holiday calendar<select name="holidayCalendarId">{masters.calendars.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>{preview.length ? <div className="preview-list form-span"><strong>Preview</strong>{preview.slice(0, 12).map(item => <span key={item.occurrenceKey}>{item.periodStart} – {item.periodEnd}<b>Due {item.dueDate}</b></span>)}</div> : null}{error ? <p className="error form-span">{error}</p> : null}<div className="button-row form-span"><button className="secondary" type="submit" name="action" value="preview">Preview year</button><button className="primary" type="submit" name="action" value="save">Save schedule</button><button className="quiet" type="button" onClick={onClose}>Cancel</button></div></form></Modal>;
}

function monthRange(month: string) { const year = Number(month.slice(0, 4)); const monthNumber = Number(month.slice(5, 7)); const last = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate(); return { from: `${month}-01`, to: `${month}-${String(last).padStart(2, "0")}` }; }
function calendarDays(month: string, tasks: CalendarTask[]): ({ date: string; tasks: CalendarTask[] } | null)[] { const range = monthRange(month); const first = new Date(`${range.from}T00:00:00Z`).getUTCDay(); const days = Number(range.to.slice(-2)); const byDate = new Map<string, CalendarTask[]>(); tasks.forEach(task => byDate.set(task.dueDate, [...(byDate.get(task.dueDate) ?? []), task])); return [...Array<null>(first).fill(null), ...Array.from({ length: days }, (_, index) => { const date = `${month}-${String(index + 1).padStart(2, "0")}`; return { date, tasks: byDate.get(date) ?? [] }; })]; }
function localDate() { const now = new Date(); const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000); return local.toISOString().slice(0, 10); }

function TaskWorkspace({ session }: { session: Session }) {
  const [page, setPage] = useState<TaskPage>({ items: [], page: 1, pageSize: 25, totalCount: 0, totalPages: 0 });
  const [masters, setMasters] = useState<TaskMasters | null>(null); const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [view, setView] = useState("mine"); const [status, setStatus] = useState(""); const [search, setSearch] = useState("");
  const [notice, setNotice] = useState(""); const [creating, setCreating] = useState(false);
  const canCreate = "tasks.create" in session.permissions; const canAssign = "tasks.assign" in session.permissions; const canChange = "tasks.change_status" in session.permissions; const canComment = "tasks.comment" in session.permissions;
  const load = useCallback(async (targetPage = 1) => { try { const params = new URLSearchParams({ view, page: String(targetPage), pageSize: "25" }); if (status) params.set("status", status); if (search.trim()) params.set("search", search.trim()); const [taskData, masterData] = await Promise.all([fetchJson<TaskPage>(`/api/v1/tasks/?${params}`), fetchJson<TaskMasters>("/api/v1/tasks/masters")]); setPage(taskData); setMasters(masterData); setNotice(""); } catch (reason) { setNotice(messageFrom(reason)); } }, [view, status, search]);
  useEffect(() => { void load(); }, [load]);
  async function openTask(id: string) { try { setDetail(await fetchJson<TaskDetail>(`/api/v1/tasks/${id}`)); } catch (reason) { setNotice(messageFrom(reason)); } }
  async function reloadSelected() { await load(page.page); if (detail) await openTask(detail.id); }
  async function changeStatus(target: WorkStatus, transition: TaskMasters["transitions"][number]) { if (!detail) return; const reason = transition.reasonRequired ? window.prompt(`Reason for ${target.label}`) : null; if (transition.reasonRequired && !reason) return; const completionNote = transition.completionDataRequired ? window.prompt("Completion note") : null; if (transition.completionDataRequired && !completionNote) return; try { await mutateJson(`/api/v1/tasks/${detail.id}/status`, "POST", { toStatusId: target.id, reason, completionNote, expectedVersion: detail.rowVersion }); await reloadSelected(); } catch (error) { setNotice(messageFrom(error)); } }
  async function assignPrimary(employeeId: string) { if (!detail || !employeeId) return; try { await mutateJson(`/api/v1/tasks/${detail.id}/assignments`, "POST", { employeeId, role: "PRIMARY", remarks: "Assigned from task workspace", expectedVersion: detail.rowVersion }); await reloadSelected(); } catch (error) { setNotice(messageFrom(error)); } }
  async function addComment(body: string) { if (!detail || !body.trim()) return; try { await mutateJson(`/api/v1/tasks/${detail.id}/comments`, "POST", { body, expectedVersion: detail.rowVersion }); await reloadSelected(); } catch (error) { setNotice(messageFrom(error)); } }
  const overdue = page.items.filter(item => !item.status.isTerminal && item.dueDate < new Date().toISOString().slice(0, 10)).length;
  const transitions = detail && masters ? masters.transitions.filter(item => item.fromStatusId === detail.status.id && item.requiredPermission in session.permissions).map(item => ({ rule: item, target: masters.statuses.find(statusItem => statusItem.id === item.toStatusId) })).filter(item => item.target) : [];
  return <><section className="workspace-hero client-hero"><div><span className="phase-badge">Phase 6 active</span><h1>Tasks</h1><p>Accountable manual and generated work with assignment history, controlled status transitions and a complete activity timeline.</p></div><div className="metric-strip"><Metric value={page.totalCount} label="Visible tasks" /><Metric value={overdue} label="Overdue here" /></div></section>
    {notice ? <p className="error">{notice}</p> : null}<div className="task-toolbar"><label>View<select value={view} onChange={event => setView(event.target.value)}>{(masters?.allowedViews ?? ["mine"]).map(item => <option key={item} value={item}>{item === "mine" ? "My tasks" : item === "team" ? "Team tasks" : "All tasks"}</option>)}</select></label><label>Status<select value={status} onChange={event => setStatus(event.target.value)}><option value="">All statuses</option>{masters?.statuses.map(item => <option value={item.code} key={item.id}>{item.label}</option>)}</select></label><label className="task-search">Search<input value={search} onChange={event => setSearch(event.target.value)} placeholder="Client, service or task" /></label>{canCreate ? <button className="primary" onClick={() => setCreating(true)}>Create task</button> : null}</div>
    <div className="task-layout"><section className="panel task-list"><div className="task-row task-row--head"><span>Task</span><span>Due</span><span>Owner</span><span>Status</span></div>{page.items.map(item => <button className={`task-row ${detail?.id === item.id ? "task-row--selected" : ""}`} key={item.id} onClick={() => void openTask(item.id)}><span><strong>#{item.taskNumber} · {item.title}</strong><small>{item.clientName} · {item.serviceName}{item.gstin ? ` · ${item.gstin}` : ""}</small></span><span><strong>{displayDate(item.dueDate)}</strong><small>{item.priority}{item.billableSnapshot ? " · Billable" : ""}</small></span><span><strong>{item.assignments.find(a => a.role === "PRIMARY")?.employeeName ?? "Unassigned"}</strong><small>{item.assignments.filter(a => a.role !== "PRIMARY").length} supporting</small></span><span className="task-status" style={{ borderColor: item.status.color, color: item.status.color }}>{item.status.label}</span></button>)}<div className="pager"><button className="quiet" disabled={page.page <= 1} onClick={() => void load(page.page - 1)}>Previous</button><span>Page {page.page} of {Math.max(1, page.totalPages)}</span><button className="quiet" disabled={page.page >= page.totalPages} onClick={() => void load(page.page + 1)}>Next</button></div></section>
      <aside className="panel task-inspector">{detail ? <><div className="panel-title"><div><h2>#{detail.taskNumber} · {detail.title}</h2><p>{detail.clientName} · {detail.serviceName}</p></div><span className="task-status" style={{ borderColor: detail.status.color, color: detail.status.color }}>{detail.status.label}</span></div><dl><dt>Due date</dt><dd>{displayDate(detail.dueDate)}</dd><dt>Priority</dt><dd>{detail.priority}</dd><dt>Scope</dt><dd>{detail.gstin ?? "Client-wide"}</dd><dt>Version</dt><dd>{detail.rowVersion}</dd></dl>
        {canChange && transitions.length ? <div className="task-actions">{transitions.map(({ rule, target }) => <button className="secondary" key={target!.id} onClick={() => void changeStatus(target!, rule)}>{target!.label}</button>)}</div> : null}
        {canAssign && masters ? <label className="task-assign">Assign / replace primary<select defaultValue="" onChange={event => { void assignPrimary(event.target.value); event.currentTarget.value = ""; }}><option value="">Choose employee</option>{masters.employees.map(item => <option value={item.id} key={item.id}>{item.displayName}</option>)}</select></label> : null}
        <section className="task-subsection"><h2>Assignments</h2>{detail.assignments.map(item => <div className={`timeline-item ${item.unassignedAtUtc ? "timeline-item--closed" : ""}`} key={item.id}><strong>{item.employeeName} · {item.role}</strong><small>{displayInstant(item.assignedAtUtc)}{item.unassignedAtUtc ? ` → closed ${displayInstant(item.unassignedAtUtc)}` : " · active"}</small></div>)}</section>
        <section className="task-subsection"><h2>Status timeline</h2>{detail.timeline.map(item => <div className="timeline-item" key={item.id}><strong>{item.fromStatus ? `${item.fromStatus} → ` : ""}{item.toStatus}</strong><small>{displayInstant(item.changedAtUtc)} · {item.actor ?? "System"}</small>{item.reason ? <p>{item.reason}</p> : null}{item.completionNote ? <p>{item.completionNote}</p> : null}</div>)}</section>
        <section className="task-subsection"><h2>Comments</h2>{canComment ? <CommentForm onSubmit={addComment} /> : null}{detail.comments.map(item => <div className="timeline-item" key={item.id}><strong>{item.author ?? "Employee"}</strong><small>{displayInstant(item.createdAtUtc)}</small><p>{item.body}</p></div>)}</section></> : <div className="empty-inspector"><span>↗</span><h2>Select a task</h2><p>Open a work item to see assignments, transitions and its complete timeline.</p></div>}</aside></div>
    {creating && masters ? <CreateTask masters={masters} onClose={() => setCreating(false)} onCreated={async (id) => { setCreating(false); await load(1); await openTask(id); }} /> : null}</>;
}

function CreateTask({ masters, onClose, onCreated }: { masters: TaskMasters; onClose: () => void; onCreated: (id: string) => Promise<void> }) {
  const [financialYear, setFinancialYear] = useState(""); const [periodStart, setPeriodStart] = useState(""); const [periodEnd, setPeriodEnd] = useState("");
  useEffect(() => {
    if (!financialYear) return;
    const year = masters.financialYears.find(item => String(item.startYear) === financialYear);
    if (year) { setPeriodStart(year.from); setPeriodEnd(year.to); }
  }, [financialYear, masters.financialYears]);
  const [agreementId, setAgreementId] = useState(masters.agreements[0]?.id ?? ""); const [error, setError] = useState(""); const agreement = masters.agreements.find(item => item.id === agreementId);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!agreement) return; const data = new FormData(event.currentTarget); try { const result = await mutateJson<{ id: string }>("/api/v1/tasks/", "POST", { clientId: agreement.clientId, serviceId: agreement.serviceId, clientServiceId: agreement.id, gstRegistrationId: agreement.gstRegistrationId, title: data.get("title"), description: data.get("description") || null, periodStart: data.get("periodStart") || null, periodEnd: data.get("periodEnd") || null, dueDate: data.get("dueDate"), priority: data.get("priority"), billable: data.get("billable") === "on", primaryAssigneeId: data.get("primaryAssigneeId") || null, secondaryAssigneeIds: data.get("secondaryAssigneeId") ? [data.get("secondaryAssigneeId")] : [], assignmentRemarks: data.get("assignmentRemarks") || null }); await onCreated(result.id); } catch (reason) { setError(messageFrom(reason)); } }
  return <Modal title="Create manual task" detail="This creates one accountable work item. It does not create a recurrence rule." onClose={onClose}>{masters.agreements.length ? <form className="client-form" onSubmit={submit}><label className="form-span">Client service agreement<select value={agreementId} onChange={event => setAgreementId(event.target.value)} required>{masters.agreements.map(item => <option value={item.id} key={item.id}>{item.clientName} · {item.serviceName}{item.gstin ? ` · ${item.gstin}` : ""}</option>)}</select></label><label>Task title<input name="title" defaultValue={agreement?.title} required maxLength={250} /><small>Defaults to the service name. Add the year or period if it helps staff recognise it.</small></label><label>Due date<input name="dueDate" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /><small>The date you intend to finish by. This is your internal deadline, not a statutory one.</small></label><label className="form-span">Which year is this work for?<select value={financialYear} onChange={event => setFinancialYear(event.target.value)}><option value="">Not tied to a year</option>{masters.financialYears.map(item => <option value={String(item.startYear)} key={item.startYear}>{item.label} ({item.from} to {item.to})</option>)}</select><small>Most statutory work belongs to a financial year rather than a single date. Choosing the year fills the period below, so an ITR filed now for FY 2025-26 is recorded against that year. Leave it blank for one-off work.</small></label><label>Period start<input name="periodStart" type="date" value={periodStart} onChange={event => { setPeriodStart(event.target.value); setFinancialYear(""); }} /><small>First day of the period this work covers.</small></label><label>Period end<input name="periodEnd" type="date" value={periodEnd} onChange={event => { setPeriodEnd(event.target.value); setFinancialYear(""); }} /><small>Last day of that period.</small></label><label>Priority<select name="priority" defaultValue={agreement?.priority ?? "NORMAL"}><option>LOW</option><option>NORMAL</option><option>HIGH</option><option>URGENT</option></select></label><label>Primary assignee<select name="primaryAssigneeId" required={masters.requiredFields.includes("primaryAssigneeId")}><option value="">Unassigned</option>{masters.employees.map(item => <option value={item.id} key={item.id}>{item.displayName}</option>)}</select></label><label>Secondary assignee<select name="secondaryAssigneeId"><option value="">None</option>{masters.employees.map(item => <option value={item.id} key={item.id}>{item.displayName}</option>)}</select></label><label className="check-label"><input name="billable" type="checkbox" defaultChecked={agreement?.billable} />Billable work item</label><label className="form-span">Description<input name="description" /></label><label className="form-span">Assignment remarks<input name="assignmentRemarks" /></label>{error ? <p className="error form-span">{error}</p> : null}<div className="button-row form-span"><button className="primary">Create task</button><button type="button" className="quiet" onClick={onClose}>Cancel</button></div></form> : <div className="setup-box">Create an active client service agreement before creating a task.</div>}</Modal>;
}

function CommentForm({ onSubmit }: { onSubmit: (body: string) => Promise<void> }) { const [body, setBody] = useState(""); return <form className="comment-form" onSubmit={event => { event.preventDefault(); void onSubmit(body).then(() => setBody("")); }}><input value={body} onChange={event => setBody(event.target.value)} placeholder="Add a work note" maxLength={4000} required /><button className="quiet">Add</button></form>; }

function displayDate(value: string) { return new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(`${value}T00:00:00`)); }
function displayInstant(value: string) { return new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value)); }

function ServiceWorkspace({ session }: { session: Session }) {
  const [services, setServices] = useState<ServiceItem[]>([]); const [agreements, setAgreements] = useState<Agreement[]>([]); const [masters, setMasters] = useState<ServiceMasters | null>(null);
  const [editingService, setEditingService] = useState<ServiceItem | null>(null);
  const [notice, setNotice] = useState(""); const [showService, setShowService] = useState(false); const [showAgreement, setShowAgreement] = useState(false); const [clientFilter, setClientFilter] = useState("");
  const canManageCatalogue = "services.catalogue.manage" in session.permissions; const canManageAgreements = "services.enrollments.manage" in session.permissions;
  const load = useCallback(async () => { try { const [catalogue, enrollmentData, masterData] = await Promise.all([fetchJson<ServiceItem[]>("/api/v1/services/?includeInactive=true"), fetchJson<Agreement[]>(`/api/v1/client-services/?includeInactive=true${clientFilter ? `&clientId=${clientFilter}` : ""}`), fetchJson<ServiceMasters>("/api/v1/services/masters")]); setServices(catalogue); setAgreements(enrollmentData); setMasters(masterData); setNotice(""); } catch (reason) { setNotice(messageFrom(reason)); } }, [clientFilter]);
  useEffect(() => { void load(); }, [load]);
  async function serviceStatus(service: ServiceItem) { const reason = service.isActive ? window.prompt(`Reason to deactivate ${service.name}`) : "Administrator reactivated service"; if (!reason) return; try { await mutateJson(`/api/v1/services/${service.id}/status`, "POST", { isActive: !service.isActive, reason }); await load(); } catch (error) { setNotice(messageFrom(error)); } }
  async function agreementStatus(item: Agreement) { const reason = item.isActive ? window.prompt(`Reason to close ${item.serviceName} for ${item.clientName}`) : "Administrator reactivated agreement"; if (!reason) return; try { await mutateJson(`/api/v1/client-services/${item.id}/status`, "POST", { isActive: !item.isActive, reason }); await load(); } catch (error) { setNotice(messageFrom(error)); } }
  return <><section className="workspace-hero client-hero"><div><span className="phase-badge">Phase 4 active</span><h1>Services</h1><p>A reusable catalogue and effective-dated agreements for each client and GSTIN scope.</p></div><div className="metric-strip"><Metric value={services.filter(x => x.isActive).length} label="Active services" /><Metric value={agreements.filter(x => x.isActive).length} label="Active agreements" /></div></section>
    {notice ? <p className="error">{notice}</p> : null}<div className="service-actions"><label>Client agreements<select value={clientFilter} onChange={event => setClientFilter(event.target.value)}><option value="">All accessible clients</option>{masters?.clients.map(client => <option value={client.id} key={client.id}>{client.displayName}</option>)}</select></label>{canManageCatalogue ? <button className="secondary" onClick={() => setShowService(true)}>Add service</button> : null}{canManageAgreements ? <button className="primary" onClick={() => setShowAgreement(true)}>Enroll client</button> : null}</div>
    <div className="service-grid"><section className="panel"><div className="panel-title"><div><h2>Service catalogue</h2><p>Defaults never overwrite existing client agreements.</p></div></div><div className="catalogue-list">{services.map(service => <div className={`catalogue-card ${service.isActive ? "" : "catalogue-card--off"}`} key={service.id}><span><strong>{service.name}</strong><small>{service.code} · {service.category}</small></span><span className="capability-tags">{service.supportsGstinScope ? <i>GSTIN scope</i> : null}{service.supportsRecurrence ? <i>Recurrence-ready</i> : null}{service.defaultBillable ? <i>Billable default</i> : null}</span><span><small>{service.activeEnrollmentCount} active agreement(s)</small>{canManageCatalogue ? <><button className="quiet" onClick={() => setEditingService(service)}>Edit</button><button className="quiet" onClick={() => void serviceStatus(service)}>{service.isActive ? "Deactivate" : "Reactivate"}</button></> : null}</span></div>)}</div></section>
      <section className="panel"><div className="panel-title"><div><h2>Client service agreements</h2><p>Each GSTIN is a distinct service scope.</p></div></div><div className="agreement-list">{agreements.map(item => <div className={`agreement-card ${item.isActive ? "" : "catalogue-card--off"}`} key={item.id}><span><strong>{item.clientName}</strong><small>{item.clientCode} · {item.serviceName}{item.gstin ? ` · ${item.gstin}` : " · Client-wide"}</small></span><span><strong>{item.defaultPriority}</strong><small>{item.effectiveFrom}{item.effectiveTo ? ` to ${item.effectiveTo}` : " onward"} · {item.responsibleTeam ?? "No team"}</small></span>{canManageAgreements ? <button className="quiet" onClick={() => void agreementStatus(item)}>{item.isActive ? "Close" : "Reactivate"}</button> : null}</div>)}</div></section></div>
    {showService && masters ? <CreateService masters={masters} onClose={() => setShowService(false)} onCreated={async () => { setShowService(false); await load(); }} /> : null}
    {editingService && masters ? <CreateService masters={masters} existing={editingService} onClose={() => setEditingService(null)} onCreated={async () => { setEditingService(null); await load(); }} /> : null}
    {showAgreement && masters ? <CreateAgreement services={services.filter(x => x.isActive)} masters={masters} onClose={() => setShowAgreement(false)} onCreated={async () => { setShowAgreement(false); await load(); }} /> : null}
  </>;
}

function CreateService({ masters, existing, onClose, onCreated }: { masters: ServiceMasters; existing?: ServiceItem | null; onClose: () => void; onCreated: () => Promise<void> }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    const body = { categoryId: data.get("categoryId"), code: data.get("code"), name: data.get("name"), description: data.get("description") || null, defaultBillable: data.get("defaultBillable") === "on", supportsRecurrence: data.get("supportsRecurrence") === "on", supportsGstinScope: data.get("supportsGstinScope") === "on" };
    try {
      if (existing) await mutateJson(`/api/v1/services/${existing.id}`, "PUT", body);
      else await mutateJson("/api/v1/services/", "POST", body);
      await onCreated();
    } catch (reason) { setError(messageFrom(reason)); }
  }
  return <Modal title={existing ? "Edit service" : "Add service"} detail="A service is something your firm does, such as GST return filing. These settings are defaults copied to new client agreements; changing them here does not alter agreements that already exist." onClose={onClose}><form className="client-form" onSubmit={submit}>
    <label>Category<select name="categoryId" required defaultValue={existing?.categoryId}>{masters.categories.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select><small>Groups the service on screens and reports, for example GST or Income Tax.</small></label>
    <label>Service code<input name="code" required maxLength={50} defaultValue={existing?.code} /><small>Short unique tag used internally, for example GSTR3B.</small></label>
    <label>Service name<input name="name" required maxLength={150} defaultValue={existing?.name} /><small>What staff will see, for example "GSTR-3B monthly return".</small></label>
    <label className="form-span">Description<input name="description" defaultValue={existing?.description ?? ""} /><small>Optional note about what the work involves.</small></label>
    <label className="check-label"><input name="defaultBillable" type="checkbox" defaultChecked={existing ? existing.defaultBillable : true} />Billable by default<small>Tick if this work is normally charged for. You can still override it per client.</small></label>
    <label className="check-label"><input name="supportsRecurrence" type="checkbox" defaultChecked={existing?.supportsRecurrence} />Can repeat on a schedule<small>Tick for work that happens again and again, such as monthly or yearly returns.</small></label>
    <label className="check-label"><input name="supportsGstinScope" type="checkbox" defaultChecked={existing?.supportsGstinScope} />Applies per GST registration<small>Tick if a client with several state GSTINs needs this done separately for each one.</small></label>
    {error ? <p className="error form-span">{error}</p> : null}
    <div className="button-row form-span"><button className="primary">{existing ? "Save service" : "Create service"}</button><button type="button" className="quiet" onClick={onClose}>Cancel</button></div>
  </form></Modal>;
}

function CreateAgreement({ services, masters, onClose, onCreated }: { services: ServiceItem[]; masters: ServiceMasters; onClose: () => void; onCreated: () => Promise<void> }) {
  const [clientId, setClientId] = useState(masters.clients[0]?.id ?? ""); const [serviceId, setServiceId] = useState(services[0]?.id ?? ""); const [error, setError] = useState(""); const [frequency, setFrequency] = useState("");
  const [dueDay, setDueDay] = useState("31"); const [dueMonth, setDueMonth] = useState("7"); const [dueOffset, setDueOffset] = useState("1");
  const [effectiveFrom, setEffectiveFrom] = useState(todayValue());
  const [preview, setPreview] = useState<{ periodStart: string; periodEnd: string; dueDate: string }[] | null>(null);

  // Yearly deadlines are stated as a date ("31 July"), which the calculator expresses as a number
  // of months after the period ends. Converting here keeps that arithmetic out of the user's head.
  const monthOffset = frequency === "YEARLY" ? yearlyOffsetFrom(effectiveFrom, Number(dueMonth)) : Number(dueOffset);

  useEffect(() => {
    if (!frequency) { setPreview(null); return; }
    let cancelled = false;
    setPreview(null);
    mutateJson<{ occurrences: { periodStart: string; periodEnd: string; dueDate: string }[] }>(
      "/api/v1/client-services/schedule-preview", "POST",
      { frequencyCode: frequency, dueDay: Number(dueDay), dueMonthOffset: monthOffset, effectiveFrom })
      .then(result => { if (!cancelled) setPreview(result.occurrences); })
      .catch(() => { if (!cancelled) setPreview([]); });
    return () => { cancelled = true; };
  }, [frequency, dueDay, monthOffset, effectiveFrom]);
  const client = masters.clients.find(item => item.id === clientId); const service = services.find(item => item.id === serviceId);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); try { await mutateJson("/api/v1/client-services/", "POST", { clientId, serviceId, gstRegistrationId: data.get("gstRegistrationId") || null, engagementCode: data.get("engagementCode") || null, titleOverride: data.get("titleOverride") || null, effectiveFrom: data.get("effectiveFrom"), effectiveTo: data.get("effectiveTo") || null, defaultPriority: data.get("defaultPriority"), responsibleTeamId: data.get("responsibleTeamId") || null, notes: data.get("notes") || null,
      schedule: frequency ? { frequencyCode: frequency, dueDay: Number(dueDay), dueMonthOffset: monthOffset, primaryAssigneeId: (data.get("primaryAssigneeId") as string) || null } : null }); await onCreated(); } catch (reason) { setError(messageFrom(reason)); } }
  return <Modal title="Enroll client service" detail="An agreement records that your firm does one service for one client. Everything below describes that arrangement, not a single piece of work." onClose={onClose}><form className="client-form" onSubmit={submit}><label>Client<select value={clientId} onChange={event => setClientId(event.target.value)} required>{masters.clients.map(item => <option value={item.id} key={item.id}>{item.displayName} · {item.clientCode}</option>)}</select></label><label>Service<select value={serviceId} onChange={event => setServiceId(event.target.value)} required>{services.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>GSTIN scope<select name="gstRegistrationId" disabled={!service?.supportsGstinScope}><option value="">Client-wide</option>{client?.gstRegistrations.map(item => <option value={item.id} key={item.id}>{item.gstin}</option>)}</select><small>Choose a GSTIN only when the work is filed separately per state registration. Otherwise leave it client-wide.</small></label><label>Effective from<input name="effectiveFrom" type="date" value={effectiveFrom} onChange={event => setEffectiveFrom(event.target.value)} required /><small>The date you started doing this work for the client. Tasks and fees before this date do not belong to this agreement.</small></label><label>Effective to<input name="effectiveTo" type="date" /><small>Leave blank while the work is ongoing. Set a date when you stop, instead of deleting the agreement, so past work and fees still make sense.</small></label><label>Default priority<select name="defaultPriority"><option>NORMAL</option><option>LOW</option><option>HIGH</option><option>URGENT</option></select><small>Priority given to tasks created from this agreement. Can be changed per task.</small></label><label>Responsible team<select name="responsibleTeamId" required={masters.requiredFields.includes("responsibleTeamId")}><option value="">No team</option>{masters.teams.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select><small>Which team owns this work. It also controls visibility: staff limited to their own team can only see clients whose agreements sit with that team. Leave blank and only administrators will see it.</small></label><label>Engagement code<input name="engagementCode" /><small>Optional reference of your own, for example an engagement letter number.</small></label><label>Title override<input name="titleOverride" /><small>Optional. Tasks are normally named after the service. Type something here only if you want this client's tasks to read differently.</small></label><label className="form-span">Notes<input name="notes" /></label>
    <div className="form-span profile-section">
      <h3>Repeating work</h3>
      <p className="muted">If this service is done again and again, set it up here and the system will create the tasks for you. Leave it as "Does not repeat" for one-off work.</p>
      <label>How often<select value={frequency} onChange={event => setFrequency(event.target.value)}><option value="">Does not repeat</option><option value="MONTHLY">Every month</option><option value="QUARTERLY">Every quarter</option><option value="HALF_YEARLY">Every six months</option><option value="YEARLY">Every year</option></select><small>The work period is measured from the effective-from date above.</small></label>
      {frequency === "YEARLY" ? <>
        <label>Deadline date<span className="deadline-picker"><select value={dueDay} onChange={event => setDueDay(event.target.value)} aria-label="Deadline day">{Array.from({ length: 31 }, (_, i) => i + 1).map(day => <option value={String(day)} key={day}>{day}</option>)}</select><select value={dueMonth} onChange={event => setDueMonth(event.target.value)} aria-label="Deadline month">{MONTH_NAMES.map((month, index) => <option value={String(index + 1)} key={month}>{month}</option>)}</select></span><small>The date the work is due each year, written the way you would say it. For a return covering April to March and filed by 31 July, choose 31 July.</small></label>
      </> : frequency ? <>
        <label>Due on day<select value={dueDay} onChange={event => setDueDay(event.target.value)}>{Array.from({ length: 31 }, (_, i) => i + 1).map(day => <option value={String(day)} key={day}>{day}</option>)}</select><small>Day of the month the work is due.</small></label>
        <label>Of which month<select value={dueOffset} onChange={event => setDueOffset(event.target.value)}>
          <option value="0">The same month the period ends</option>
          <option value="1">The month after the period ends</option>
          <option value="2">Two months after</option>
          <option value="3">Three months after</option>
        </select><small>A monthly return covering March and due in April is "the month after".</small></label>
      </> : null}
      {frequency ? <>
        <label>Person responsible<select name="primaryAssigneeId"><option value="">Nobody yet</option>{masters.employees?.map(item => <option value={item.id} key={item.id}>{item.displayName}</option>)}</select><small>Each generated task is assigned to this person automatically. You can reassign any individual task later.</small></label>
        <div className="form-span schedule-preview">
          <strong>What this will create</strong>
          {preview === null ? <p className="muted">Working it out…</p>
            : preview.length === 0 ? <p className="muted">No dates fall in the next few years. Check the deadline and the effective-from date.</p>
            : <ul>{preview.map(item => <li key={item.dueDate}><b>Due {formatLongDate(item.dueDate)}</b><span>for the period {formatLongDate(item.periodStart)} to {formatLongDate(item.periodEnd)}</span></li>)}</ul>}
          <small>Dates shown before any weekend or holiday adjustment, which the firm calendar applies when the task is created. If these look wrong, change the deadline above.</small>
        </div>
      </> : null}
    </div>
    {error ? <p className="error form-span">{error}</p> : null}<div className="button-row form-span"><button className="primary">Create agreement</button><button type="button" className="quiet" onClick={onClose}>Cancel</button></div></form></Modal>;
}

function Modal({ title, detail, onClose, children }: { title: string; detail: string; onClose: () => void; children: React.ReactNode }) { return <div className="modal-backdrop" role="presentation"><section className="modal-card" role="dialog" aria-modal="true"><div className="panel-title"><div><h2>{title}</h2><p>{detail}</p></div><button className="quiet" onClick={onClose}>Close</button></div>{children}</section></div>; }

function ClientRegistry({ session }: { session: Session }) {
  const [page, setPage] = useState<ClientPage>({ items: [], page: 1, pageSize: 25, total: 0, totalPages: 0 });
  const [masters, setMasters] = useState<ClientMaster | null>(null); const [search, setSearch] = useState(""); const [status, setStatus] = useState("ACTIVE");
  const [hasGstin, setHasGstin] = useState(""); const [groupId, setGroupId] = useState(""); const [sort, setSort] = useState("name"); const [direction, setDirection] = useState("asc");
  const [creating, setCreating] = useState(false); const [selected, setSelected] = useState<ClientListItem | null>(null); const [notice, setNotice] = useState("");
  const canCreate = "clients.create" in session.permissions; const canEdit = "clients.edit" in session.permissions; const canDeactivate = "clients.deactivate" in session.permissions;
  const queryString = useCallback((requestedPage: number) => {
    const params = new URLSearchParams({ status, page: String(requestedPage), pageSize: "25", sort, direction });
    if (search.trim()) params.set("search", search.trim());
    if (hasGstin) params.set("hasGstin", hasGstin);
    if (groupId) params.set("groupId", groupId);
    return params.toString();
  }, [search, status, hasGstin, groupId, sort, direction]);
  const load = useCallback(async (requestedPage = 1) => { try { const [clientPage, masterData] = await Promise.all([fetchJson<ClientPage>(`/api/v1/clients/?${queryString(requestedPage)}`), fetchJson<ClientMaster>("/api/v1/clients/masters")]); setPage(clientPage); setMasters(masterData); setNotice(""); } catch (reason) { setNotice(messageFrom(reason)); } }, [queryString]);
  useEffect(() => { void load(); }, [load]);
  async function exportClients(format: "xlsx" | "csv") {
    try {
      await downloadFile("/api/v1/clients/:export", {
        format,
        filters: { status, categoryId: null, groupId: groupId || null, hasGstin: hasGstin === "" ? null : hasGstin === "true", search: search.trim() || null },
        sort, direction
      }, `client-register.${format}`);
    } catch (reason) { setNotice(messageFrom(reason)); }
  }
  async function changeStatus(client: ClientListItem) { const reason = client.status === "ACTIVE" ? window.prompt("Reason for deactivation") : "Administrator reactivated client"; if (!reason) return; try { await mutateJson(`/api/v1/clients/${client.id}/status`, "POST", { isActive: client.status !== "ACTIVE", reason }); setSelected(null); await load(page.page); } catch (error) { setNotice(messageFrom(error)); } }
  const [profileId, setProfileId] = useState<string | null>(null);
  return <>
    <section className="workspace-hero client-hero"><div><span className="phase-badge">Phase 3 active</span><h1>Client registry</h1><p>One searchable master for legal identities, contacts, addresses, groups and every GST registration.</p></div><div className="metric-strip"><Metric value={page.total} label="Matching clients" /><Metric value={page.items.reduce((sum, item) => sum + item.gstinCount, 0)} label="GSTINs on page" /></div></section>
    <section className="client-toolbar"><label>Search clients<input value={search} onChange={event => setSearch(event.target.value)} placeholder="Name, code, PAN or GSTIN" /></label><label>Status<select value={status} onChange={event => setStatus(event.target.value)}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option><option value="ALL">All</option></select></label><label>GST registration<select value={hasGstin} onChange={event => setHasGstin(event.target.value)}><option value="">All clients</option><option value="true">Has a GSTIN</option><option value="false">No GSTIN</option></select></label><label>Group<select value={groupId} onChange={event => setGroupId(event.target.value)}><option value="">All groups</option>{masters?.groups.map(group => <option value={group.id} key={group.id}>{group.name}</option>)}</select></label><label>Sort by<select value={sort} onChange={event => setSort(event.target.value)}><option value="name">Client name</option><option value="code">Client code</option><option value="category">Category</option><option value="group">Group</option><option value="status">Status</option></select></label><label>Order<select value={direction} onChange={event => setDirection(event.target.value)}><option value="asc">A to Z</option><option value="desc">Z to A</option></select></label><button className="secondary" onClick={() => void load(1)}>Search</button><button className="secondary" onClick={() => void exportClients("xlsx")}>Export Excel</button><button className="secondary" onClick={() => void exportClients("csv")}>Export CSV</button>{canCreate ? <button className="primary" onClick={() => setCreating(true)}>Create client</button> : null}</section>
    {notice ? <p className="error">{notice}</p> : null}
    <div className="client-layout"><section className="panel client-table"><div className="client-row client-row--head"><span>Client code</span><span>Client</span><span>Category / group</span><span>Tax profile</span><span>Status</span></div>{page.items.map(client => <button className={`client-row ${selected?.id === client.id ? "client-row--selected" : ""}`} key={client.id} onClick={() => setSelected(client)}><span className="client-code">{client.clientCode}</span><span><strong>{client.displayName}</strong><small>{client.category ?? "Unclassified"}</small></span><span>{client.category ?? "Unclassified"}<small>{client.primaryGroup ?? "No primary group"}</small></span><span>{client.pan ?? "PAN not recorded"}<small>{client.gstinCount} GSTIN{client.gstinCount === 1 ? "" : "s"}</small></span><span className="state">{client.status}</span></button>)}</section>
      <aside className="panel client-inspector"><h2>{selected ? selected.displayName : "Client details"}</h2>{selected ? <><p className="muted">{selected.clientCode} · {selected.category ?? "Unclassified"}</p><dl><dt>PAN</dt><dd>{selected.pan ?? "Not recorded"}</dd><dt>GST registrations</dt><dd>{selected.gstinCount}</dd><dt>Primary group</dt><dd>{selected.primaryGroup ?? "Not assigned"}</dd></dl><button className="primary full" onClick={() => setProfileId(selected.id)}>{canEdit ? "Open full profile" : "View full profile"}</button>{canDeactivate ? <button className="secondary full" onClick={() => void changeStatus(selected)}>{selected.status === "ACTIVE" ? "Deactivate client" : "Reactivate client"}</button> : null}</> : <p className="muted">Select a client to inspect its profile and lifecycle status.</p>}</aside>
    </div>
    <div className="pager"><button className="quiet" disabled={page.page <= 1} onClick={() => void load(page.page - 1)}>Previous</button><span>Page {page.page} of {Math.max(1, page.totalPages)}</span><button className="quiet" disabled={page.page >= page.totalPages} onClick={() => void load(page.page + 1)}>Next</button></div>
    {profileId && masters ? <ClientProfile clientId={profileId} masters={masters} canEdit={canEdit} onClose={() => setProfileId(null)} onSaved={async () => { await load(page.page); }} /> : null}
    {creating && masters ? <CreateClient masters={masters} onClose={() => setCreating(false)} onCreated={async () => { setCreating(false); await load(1); }} /> : null}
  </>;
}


const CONTACT_TYPES: { value: string; label: string; hint: string }[] = [
  { value: "OWNER", label: "Owner / Proprietor", hint: "The individual who owns the business." },
  { value: "PARTNER", label: "Partner", hint: "A partner in a firm or LLP." },
  { value: "DIRECTOR", label: "Director", hint: "A director of a company." },
  { value: "AUTHORIZED_PERSON", label: "Authorised signatory", hint: "Signs returns and filings." },
  { value: "ACCOUNTANT", label: "Client's accountant", hint: "Their in-house accounts person, not your staff." },
  { value: "ACCOUNTS", label: "Accounts contact", hint: "Day-to-day accounts or billing queries." },
  { value: "TAX", label: "Tax contact", hint: "Handles tax matters." },
  { value: "GENERAL", label: "General contact", hint: "Anyone else you deal with." },
  { value: "OTHER", label: "Other", hint: "Use the note to explain." }
];
const ADDRESS_TYPES: { value: string; label: string; hint: string }[] = [
  { value: "REGISTERED", label: "Registered office", hint: "The address on record with the ROC or department." },
  { value: "BUSINESS", label: "Place of business", hint: "Where they actually operate." },
  { value: "COMMUNICATION", label: "Correspondence", hint: "Where you send post." },
  { value: "OTHER", label: "Other", hint: "Anything else." }
];

// The database has always supported many contacts, addresses and registrations per client; this is
// the screen that lets someone actually maintain them instead of editing two names in a prompt.
function ClientProfile({ clientId, masters, canEdit, onClose, onSaved }: { clientId: string; masters: ClientMaster; canEdit: boolean; onClose: () => void; onSaved: () => Promise<void> }) {
  const [detail, setDetail] = useState<ClientDetail | null>(null);
  const [contacts, setContacts] = useState<ClientContact[]>([]);
  const [addresses, setAddresses] = useState<ClientAddress[]>([]);
  const [gstins, setGstins] = useState<ClientGstin[]>([]); const [tans, setTans] = useState<ClientTan[]>([]);
  const [error, setError] = useState(""); const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchJson<ClientDetail>(`/api/v1/clients/${clientId}`)
      .then(loaded => { setDetail(loaded); setContacts(loaded.contacts ?? []); setAddresses(loaded.addresses ?? []); setGstins(loaded.gstRegistrations ?? []); setTans(loaded.tanRegistrations ?? []); })
      .catch(reason => setError(messageFrom(reason)));
  }, [clientId]);

  function addContact() {
    setContacts(current => [...current, { contactType: "OWNER", name: "", designation: null, phone: null, email: null, isPrimary: current.length === 0, isActive: true, notes: null }]);
  }
  function addAddress() {
    setAddresses(current => [...current, { addressType: "REGISTERED", line1: "", line2: null, city: null, district: null, stateCode: null, postalCode: null, countryCode: "IN", isPrimary: current.length === 0, isActive: true, validFrom: null, validTo: null }]);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail) return;
    const data = new FormData(event.currentTarget);
    setSaving(true);
    try {
      await mutateJson(`/api/v1/clients/${detail.id}`, "PUT", {
        clientCode: detail.clientCode,
        legacyCode: detail.legacyCode,
        displayName: data.get("displayName"),
        legalName: (data.get("legalName") as string) || null,
        categoryId: (data.get("categoryId") as string) || null,
        pan: (data.get("pan") as string) || null,
        onboardedOn: (data.get("onboardedOn") as string) || null,
        notes: (data.get("notes") as string) || null,
        contacts: contacts.filter(item => item.name.trim().length > 0),
        addresses: addresses.filter(item => item.line1.trim().length > 0),
        gstRegistrations: gstins.filter(item => item.gstin.trim().length > 0),
        tanRegistrations: tans.filter(item => item.tan.trim().length > 0),
        groups: detail.groups
      });
      await onSaved(); onClose();
    } catch (reason) { setError(messageFrom(reason)); }
    finally { setSaving(false); }
  }

  if (!detail) {
    return <Modal title="Client profile" detail="Loading the client record." onClose={onClose}>{error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>}</Modal>;
  }

  return <Modal title={detail.displayName} detail={`${detail.clientCode} · everything you hold about this client. The code is fixed once assigned.`} onClose={onClose}>
    <form className="client-form" onSubmit={save}>
      <label>Client name<input name="displayName" defaultValue={detail.displayName} required maxLength={250} disabled={!canEdit} /><small>The name you use day to day.</small></label>
      <label>Legal name<input name="legalName" defaultValue={detail.legalName ?? ""} disabled={!canEdit} /><small>The full name as registered, if it differs.</small></label>
      <label>Constitution<select name="categoryId" defaultValue={detail.categoryId ?? ""} disabled={!canEdit}><option value="">Not classified</option>{masters.categories.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select><small>Individual, Partnership, Private Limited and so on.</small></label>
      <label>PAN<input name="pan" defaultValue={detail.pan ?? ""} maxLength={10} disabled={!canEdit} /><small>Ten characters, for example ABCDE1234F.</small></label>
      <label>Client since<input name="onboardedOn" type="date" defaultValue={detail.onboardedOn ?? ""} disabled={!canEdit} /><small>When they became your client.</small></label>
      <label className="form-span">Notes<input name="notes" defaultValue={detail.notes ?? ""} disabled={!canEdit} /><small>Anything the team should know.</small></label>

      <div className="form-span profile-section">
        <h3>People</h3>
        <p className="muted">Owners, partners, directors, signatories and their accountant. Add as many as you need; tick one as the main contact.</p>
        {contacts.map((contact, index) => <div className="profile-row" key={contact.id ?? `new-${index}`}>
          <select aria-label="Role" value={contact.contactType} disabled={!canEdit} onChange={event => setContacts(current => current.map((item, i) => i === index ? { ...item, contactType: event.target.value } : item))}>
            {CONTACT_TYPES.map(type => <option value={type.value} key={type.value}>{type.label}</option>)}
          </select>
          <input aria-label="Name" placeholder="Full name" value={contact.name} disabled={!canEdit} onChange={event => setContacts(current => current.map((item, i) => i === index ? { ...item, name: event.target.value } : item))} />
          <input aria-label="Phone" placeholder="Phone" value={contact.phone ?? ""} disabled={!canEdit} onChange={event => setContacts(current => current.map((item, i) => i === index ? { ...item, phone: event.target.value || null } : item))} />
          <input aria-label="Email" placeholder="Email" value={contact.email ?? ""} disabled={!canEdit} onChange={event => setContacts(current => current.map((item, i) => i === index ? { ...item, email: event.target.value || null } : item))} />
          <label className="check-label"><input type="checkbox" checked={contact.isPrimary} disabled={!canEdit} onChange={() => setContacts(current => current.map((item, i) => ({ ...item, isPrimary: i === index })))} />Main</label>
          {canEdit ? <button type="button" className="quiet" onClick={() => setContacts(current => current.filter((_, i) => i !== index))}>Remove</button> : null}
        </div>)}
        {canEdit ? <button type="button" className="secondary" onClick={addContact}>Add a person</button> : null}
      </div>

      <div className="form-span profile-section">
        <h3>Addresses</h3>
        <p className="muted">Registered office, place of business and where you send post.</p>
        {addresses.map((address, index) => <div className="profile-row profile-row--address" key={address.id ?? `new-${index}`}>
          <select aria-label="Address type" value={address.addressType} disabled={!canEdit} onChange={event => setAddresses(current => current.map((item, i) => i === index ? { ...item, addressType: event.target.value } : item))}>
            {ADDRESS_TYPES.map(type => <option value={type.value} key={type.value}>{type.label}</option>)}
          </select>
          <input aria-label="Address line" placeholder="Address" value={address.line1} disabled={!canEdit} onChange={event => setAddresses(current => current.map((item, i) => i === index ? { ...item, line1: event.target.value } : item))} />
          <input aria-label="City" placeholder="City" value={address.city ?? ""} disabled={!canEdit} onChange={event => setAddresses(current => current.map((item, i) => i === index ? { ...item, city: event.target.value || null } : item))} />
          <select aria-label="State" value={address.stateCode ?? ""} disabled={!canEdit} onChange={event => setAddresses(current => current.map((item, i) => i === index ? { ...item, stateCode: event.target.value || null } : item))}>
            <option value="">State</option>{masters.states.map(state => <option value={state.code} key={state.code}>{state.name}</option>)}
          </select>
          <input aria-label="PIN code" placeholder="PIN" value={address.postalCode ?? ""} disabled={!canEdit} maxLength={10} onChange={event => setAddresses(current => current.map((item, i) => i === index ? { ...item, postalCode: event.target.value || null } : item))} />
          {canEdit ? <button type="button" className="quiet" onClick={() => setAddresses(current => current.filter((_, i) => i !== index))}>Remove</button> : null}
        </div>)}
        {canEdit ? <button type="button" className="secondary" onClick={addAddress}>Add an address</button> : null}
      </div>

      <div className="form-span profile-section">
        <h3>GST registrations</h3>
        <p className="muted">One line per state registration. A client registering in a new state is added here; the first 2 digits of the GSTIN must match the state.</p>
        {gstins.map((item, index) => <div className="profile-row profile-row--gst" key={item.id ?? `new-gst-${index}`}>
          <input aria-label="GSTIN" placeholder="27AAAAA0000A1Z5" value={item.gstin} maxLength={15} disabled={!canEdit} onChange={event => { const value = event.target.value.toUpperCase(); setGstins(current => current.map((row, i) => i === index ? { ...row, gstin: value, stateCode: value.slice(0, 2) } : row)); }} />
          <select aria-label="State" value={item.stateCode} disabled={!canEdit} onChange={event => setGstins(current => current.map((row, i) => i === index ? { ...row, stateCode: event.target.value } : row))}>
            <option value="">State</option>{masters.states.map(state => <option value={state.code} key={state.code}>{state.name}</option>)}
          </select>
          <select aria-label="Status" value={item.registrationStatus} disabled={!canEdit} onChange={event => setGstins(current => current.map((row, i) => i === index ? { ...row, registrationStatus: event.target.value } : row))}>
            <option value="ACTIVE">Active</option><option value="SUSPENDED">Suspended</option><option value="CANCELLED">Cancelled</option><option value="INACTIVE">Inactive</option>
          </select>
          <label className="check-label"><input type="checkbox" checked={item.isPrimary} disabled={!canEdit} onChange={() => setGstins(current => current.map((row, i) => ({ ...row, isPrimary: i === index })))} />Main</label>
          {canEdit ? <button type="button" className="quiet" onClick={() => setGstins(current => current.filter((_, i) => i !== index))}>Remove</button> : null}
        </div>)}
        {canEdit ? <button type="button" className="secondary" onClick={() => setGstins(current => [...current, { gstin: "", stateCode: "", tradeName: null, registrationStatus: "ACTIVE", effectiveFrom: null, effectiveTo: null, isPrimary: current.length === 0, isActive: true, cancellationReason: null }])}>Add a GST registration</button> : null}
      </div>

      <div className="form-span profile-section">
        <h3>TAN registrations</h3>
        <p className="muted">A deductor can hold more than one TAN, usually one per branch or division. Add each one here; the main TAN is the one shown in registers and reports.</p>
        {tans.map((item, index) => <div className="profile-row profile-row--gst" key={item.id ?? `new-tan-${index}`}>
          <input aria-label="TAN" placeholder="DELA12345B" value={item.tan} maxLength={10} disabled={!canEdit} onChange={event => { const value = event.target.value.toUpperCase(); setTans(current => current.map((row, i) => i === index ? { ...row, tan: value } : row)); }} />
          <input aria-label="Deductor name" placeholder="Deductor name" value={item.deductorName ?? ""} disabled={!canEdit} onChange={event => setTans(current => current.map((row, i) => i === index ? { ...row, deductorName: event.target.value || null } : row))} />
          <input aria-label="Branch" placeholder="Branch or division" value={item.branch ?? ""} disabled={!canEdit} onChange={event => setTans(current => current.map((row, i) => i === index ? { ...row, branch: event.target.value || null } : row))} />
          <label className="check-label"><input type="checkbox" checked={item.isPrimary} disabled={!canEdit} onChange={() => setTans(current => current.map((row, i) => ({ ...row, isPrimary: i === index })))} />Main</label>
          {canEdit ? <button type="button" className="quiet" onClick={() => setTans(current => current.filter((_, i) => i !== index))}>Remove</button> : null}
        </div>)}
        {canEdit ? <button type="button" className="secondary" onClick={() => setTans(current => [...current, { tan: "", deductorName: null, branch: null, effectiveFrom: null, effectiveTo: null, isPrimary: current.length === 0, isActive: true, notes: null }])}>Add a TAN</button> : null}
      </div>

      {error ? <p className="error form-span">{error}</p> : null}
      <div className="button-row form-span">{canEdit ? <button className="primary" disabled={saving}>{saving ? "Saving…" : "Save client"}</button> : null}<button type="button" className="quiet" onClick={onClose}>Close</button></div>
    </form>
  </Modal>;
}

function CreateClient({ masters, onClose, onCreated }: { masters: ClientMaster; onClose: () => void; onCreated: () => Promise<void> }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); const gstins = [1, 2].map(index => ({ gstin: String(data.get(`gstin${index}`) ?? "").trim(), stateCode: String(data.get(`state${index}`) ?? ""), tradeName: null, registrationStatus: "ACTIVE", effectiveFrom: null, effectiveTo: null, isPrimary: index === 1, isActive: true, cancellationReason: null })).filter(item => item.gstin); try { await mutateJson("/api/v1/clients/", "POST", { clientCode: data.get("clientCode"), legacyCode: null, displayName: data.get("displayName"), legalName: data.get("legalName") || null, categoryId: data.get("categoryId") || null, pan: data.get("pan") || null, tan: data.get("tan") || null, onboardedOn: data.get("onboardedOn") || null, notes: data.get("notes") || null, contacts: data.get("contactName") ? [{ contactType: "GENERAL", name: data.get("contactName"), designation: null, phone: data.get("phone") || null, email: data.get("email") || null, isPrimary: true, isActive: true, notes: null }] : [], addresses: data.get("address") ? [{ addressType: "REGISTERED", line1: data.get("address"), line2: null, city: data.get("city") || null, district: null, stateCode: data.get("addressState") || null, postalCode: data.get("postalCode") || null, countryCode: "IN", isPrimary: true, isActive: true, validFrom: null, validTo: null }] : [], gstRegistrations: gstins, groups: data.get("groupId") ? [{ groupId: data.get("groupId"), membershipType: "PRIMARY", effectiveFrom: null, validTo: null, notes: null }] : [] }); await onCreated(); } catch (reason) { setError(messageFrom(reason)); } }
  return <div className="modal-backdrop" role="presentation"><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="new-client-title"><div className="panel-title"><div><h2 id="new-client-title">Create client</h2><p>Fields marked by the administrator are validated by the server.</p></div><button className="quiet" onClick={onClose}>Close</button></div><form className="client-form" onSubmit={submit}><label>Client code<input name="clientCode" required /></label><label>Client name<input name="displayName" required /></label><label>Legal name<input name="legalName" /></label><label>Category<select name="categoryId" required={masters.requiredFields.includes("categoryId")}><option value="">Choose category</option>{masters.categories.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>PAN<input name="pan" maxLength={10} /></label><label>TAN<input name="tan" maxLength={10} /></label><label>Onboarding date<input name="onboardedOn" type="date" /></label><label>Primary group<select name="groupId"><option value="">No group</option>{masters.groups.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Contact name<input name="contactName" required={masters.requiredFields.includes("primaryContact")} /></label><label>Mobile<input name="phone" /></label><label>Email<input name="email" type="email" /></label><label>Registered address<input name="address" required={masters.requiredFields.includes("primaryAddress")} /></label><label>City<input name="city" /></label><label>State<select name="addressState"><option value="">Choose state</option>{masters.states.map(item => <option value={item.code} key={item.code}>{item.name}</option>)}</select></label><label>PIN code<input name="postalCode" inputMode="numeric" maxLength={6} /></label><span className="form-section">GST registrations (zero, one or two)</span>{[1, 2].map(index => <div className="gst-pair form-span" key={index}><label>GSTIN {index}<input name={`gstin${index}`} maxLength={15} /></label><label>State<select name={`state${index}`}><option value="">Choose state</option>{masters.states.map(item => <option value={item.code} key={item.code}>{item.name}</option>)}</select></label></div>)}<label className="form-span">Notes<input name="notes" /></label>{error ? <p className="error form-span">{error}</p> : null}<div className="button-row form-span"><button className="primary">Create client</button><button type="button" className="quiet" onClick={onClose}>Cancel</button></div></form></section></div>;
}

function CreateRole({ onCreated }: { onCreated: () => Promise<void> }) {
  const [open, setOpen] = useState(false); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const data = new FormData(event.currentTarget); try { await mutateJson("/api/v1/admin/roles", "POST", { name: data.get("name"), description: data.get("description") }); setOpen(false); await onCreated(); } catch (reason) { setError(messageFrom(reason)); } }
  if (!open) return <button className="secondary full" onClick={() => setOpen(true)}>Create another role</button>;
  return <form className="form-stack inline-form" onSubmit={submit}><label>Role name<input name="name" required maxLength={100} /></label><label>Description<input name="description" maxLength={500} /></label>{error ? <p className="error">{error}</p> : null}<div className="button-row"><button className="primary">Create</button><button type="button" className="quiet" onClick={() => setOpen(false)}>Cancel</button></div></form>;
}

function CreateEmployee({ roles, onCreated }: { roles: Role[]; onCreated: () => Promise<void> }) {
  const [open, setOpen] = useState(false); const [error, setError] = useState(""); const [showPassword, setShowPassword] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const form = event.currentTarget; const data = new FormData(form); try { await mutateJson("/api/v1/admin/employees", "POST", { employeeCode: data.get("employeeCode"), displayName: data.get("displayName"), mobileNumber: data.get("mobileNumber"), temporaryPassword: data.get("temporaryPassword"), roleIds: [data.get("roleId")], email: data.get("email") || null, designation: null, department: null, managerEmployeeId: null, joinedOn: null }); setOpen(false); form.reset(); await onCreated(); } catch (reason) { setError(messageFrom(reason)); } }
  if (!open) return <button className="secondary full" onClick={() => setOpen(true)}>Add employee login</button>;
  return <form className="employee-form" onSubmit={submit}><label>Employee code<input name="employeeCode" required /></label><label>Name<input name="displayName" required /></label><label>Mobile<input name="mobileNumber" inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength={10} required /></label><label>Email<input name="email" type="email" /></label><label>Role<select name="roleId" required>{roles.map(role => <option value={role.id} key={role.id}>{role.name}</option>)}</select></label><label>Temporary password<span className="password-field"><input name="temporaryPassword" type={showPassword ? "text" : "password"} minLength={12} required /><button type="button" className="quiet" onClick={() => setShowPassword(current => !current)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button></span><small>At least 12 characters. Read it to the employee; they must change it at first sign in.</small></label>{error ? <p className="error form-span">{error}</p> : null}<div className="button-row form-span"><button className="primary">Create employee</button><button type="button" className="quiet" onClick={() => setOpen(false)}>Cancel</button></div></form>;
}

function RolePermissions({ roles, permissions, onSaved }: { roles: Role[]; permissions: PermissionDefinition[]; onSaved: () => Promise<void> }) {
  const editableRoles = roles.filter(role => !role.isProtected);
  const [roleId, setRoleId] = useState("");
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const selectedRole = editableRoles.find(role => role.id === roleId);
  useEffect(() => {
    if (!selectedRole) { setAssignments({}); return; }
    const byCode = new Map(selectedRole.permissions.map(item => [item.code, item.scopeCeiling]));
    setAssignments(Object.fromEntries(permissions.filter(permission => byCode.has(permission.code)).map(permission => [permission.id, byCode.get(permission.code) ?? "OWN"])));
  }, [selectedRole, permissions]);
  async function save() {
    if (!roleId) return;
    try {
      await mutateJson(`/api/v1/admin/roles/${roleId}/permissions`, "PUT", { permissions: Object.entries(assignments).map(([permissionId, scope]) => ({ permissionId, scope })) });
      setError(""); await onSaved();
    } catch (reason) { setError(messageFrom(reason)); }
  }
  return <div className="access-editor"><label>Configure access<select value={roleId} onChange={event => setRoleId(event.target.value)}><option value="">Choose a role</option>{editableRoles.map(role => <option value={role.id} key={role.id}>{role.name}</option>)}</select></label>{selectedRole ? <><div className="permission-list">{permissions.map(permission => { const enabled = permission.id in assignments; return <div className="permission" key={permission.id}><label><input type="checkbox" checked={enabled} onChange={() => setAssignments(current => { const next = { ...current }; if (enabled) delete next[permission.id]; else next[permission.id] = permission.supportsScope ? "OWN" : "ALL"; return next; })} /><span><strong>{permission.code}</strong><small>{permission.description}</small></span></label>{permission.supportsScope && enabled ? <select aria-label={`${permission.code} scope`} value={assignments[permission.id]} onChange={event => setAssignments(current => ({ ...current, [permission.id]: event.target.value }))}><option value="OWN">Own</option><option value="TEAM">Team</option><option value="ALL">All</option></select> : null}</div>; })}</div>{error ? <p className="error">{error}</p> : null}<button className="primary full" type="button" onClick={save}>Save role access</button></> : null}</div>;
}

function CenteredMessage({ title, detail, children }: { title: string; detail: string; children?: React.ReactNode }) { return <main className="center-shell"><section className="message-card"><div className="eyebrow">CA Firm Practice Management</div><h1>{title}</h1><p>{detail}</p>{children}</section></main>; }
function Metric({ value, label }: { value: number; label: string }) { return <div><strong>{value}</strong><small>{label}</small></div>; }
function initials(name: string) { return name.split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase(); }
async function updateField(field: FieldPolicy, required: boolean, reload: () => Promise<void>, setNotice: (message: string) => void) { try { await mutateJson(`/api/v1/admin/field-policies/${encodeURIComponent(field.entityType)}/${encodeURIComponent(field.fieldKey)}`, "PUT", { isRequired: required }); await reload(); } catch (reason) { setNotice(messageFrom(reason)); } }
type ProblemPayload = { detail?: string; message?: string; title?: string; traceId?: string; errors?: Record<string, string[]> };
// Surface the ProblemDetails trace id so a reported error can be matched to a server log line
// instead of leaving support with only a bare status code.
function problemMessage(problem: ProblemPayload | null, status: number, fallback: string) {
  const validation = problem?.errors ? Object.values(problem.errors).flat().join(" ") : "";
  const detail = validation || problem?.detail || problem?.message || `${fallback} (${status}).`;
  return problem?.traceId ? `${detail} Reference ${problem.traceId}` : detail;
}
async function fetchJson<T>(url: string): Promise<T> { const response = await fetch(url, { credentials: "same-origin" }); if (!response.ok) { const problem = await response.json().catch(() => null) as ProblemPayload | null; throw new Error(problemMessage(problem, response.status, "Request failed")); } return response.json() as Promise<T>; }
async function mutateJson<T = unknown>(url: string, method: string, body?: unknown): Promise<T> { const csrf = await fetchJson<{ token: string }>("/api/v1/auth/csrf"); const response = await fetch(url, { method, credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-TOKEN": csrf.token }, body: body === undefined ? undefined : JSON.stringify(body) }); if (!response.ok) { const problem = await response.json().catch(() => null) as ProblemPayload | null; throw new Error(problemMessage(problem, response.status, "Request failed")); } return response.status === 204 ? undefined as T : response.json() as Promise<T>; }
async function downloadFile(url: string, body: unknown, filename: string) { const csrf = await fetchJson<{ token: string }>("/api/v1/auth/csrf"); const response = await fetch(url, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-TOKEN": csrf.token }, body: JSON.stringify(body) }); if (!response.ok) { const problem = await response.json().catch(() => null) as ProblemPayload | null; throw new Error(problemMessage(problem, response.status, "Export failed")); } const href = URL.createObjectURL(await response.blob()); const link = document.createElement("a"); link.href = href; link.download = filename; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(href); }
const FIELD_GROUP_LABELS: Record<string, string> = {
  "clients.client": "Client",
  "employees.employee": "Employee",
  "services.client_service": "Client service agreement",
  "tasks.task": "Task",
  "billing.billing_entity": "Billing entity",
  "billing.billing_term": "Billing term"
};
const FIELD_GROUP_ORDER = ["clients.client", "services.client_service", "tasks.task", "billing.billing_entity", "billing.billing_term", "employees.employee"];
function fieldGroups(fields: FieldPolicy[]) {
  const byEntity = new Map<string, FieldPolicy[]>();
  for (const field of fields) {
    const bucket = byEntity.get(field.entityType) ?? [];
    bucket.push(field);
    byEntity.set(field.entityType, bucket);
  }
  return [...byEntity.entries()]
    .sort((left, right) => {
      const leftRank = FIELD_GROUP_ORDER.indexOf(left[0]); const rightRank = FIELD_GROUP_ORDER.indexOf(right[0]);
      return (leftRank < 0 ? 99 : leftRank) - (rightRank < 0 ? 99 : rightRank);
    })
    .map(([entityType, group]) => ({
      entityType,
      label: FIELD_GROUP_LABELS[entityType] ?? entityType,
      fields: [...group].sort((left, right) => left.label.localeCompare(right.label))
    }));
}
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

// A yearly period ends 12 months after it starts, so the month it ends in is the month before the
// effective-from month. The offset is how far the chosen deadline month sits after that.
function yearlyOffsetFrom(effectiveFrom: string, deadlineMonth: number) {
  const startMonth = Number(effectiveFrom.slice(5, 7));
  if (!startMonth || !deadlineMonth) return 0;
  const periodEndMonth = startMonth === 1 ? 12 : startMonth - 1;
  return (deadlineMonth - periodEndMonth + 12) % 12;
}

function formatLongDate(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
}

function employeeState(employee: Employee) {
  if (!employee.isActive) return "Inactive";
  if (employee.userId === null) return "No login";
  return employee.accountActive ? "Active" : "Login disabled";
}
function employeeStateClass(employee: Employee) {
  return !employee.isActive || (employee.userId !== null && !employee.accountActive) ? "state state--warn" : "state";
}
function messageFrom(reason: unknown) { return reason instanceof Error ? reason.message : "The request could not be completed."; }
