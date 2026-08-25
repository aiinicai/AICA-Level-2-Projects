import { access, readFile } from "node:fs/promises";

const requiredFiles = ["index.html", "src/main.tsx", "src/app/App.tsx", "src/app/styles.css"];

await Promise.all(requiredFiles.map((file) => access(new URL(`../${file}`, import.meta.url))));

const appSource = await readFile(new URL("../src/app/App.tsx", import.meta.url), "utf8");
if (!appSource.includes("Phase 9 active") || !appSource.includes("DashboardWorkspace") || !appSource.includes("ReportsWorkspace") || !appSource.includes("ProjectionWorkspace")) {
  throw new Error("Phase 9 dashboard, scoped reports, and projection workspaces are missing from the application shell.");
}

for (const endpoint of [
  "/api/v1/auth/login",
  "/api/v1/admin/roles",
  "/api/v1/admin/field-policies",
  "/api/v1/admin/employees",
  "/api/v1/clients/",
  "/api/v1/services/",
  "/api/v1/client-services/",
  "/api/v1/tasks/",
  "/api/v1/calendar",
  "/api/v1/scheduling/rules",
  "/api/v1/scheduling/preview",
  "/api/v1/scheduling/generate",
  "/api/v1/billing/entities",
  "/api/v1/billing/terms",
  "/api/v1/billing-projections:calculate",
  "/api/v1/billing-projections:export",
  "/api/v1/dashboard",
  "/api/v1/reports/catalog",
  "/api/v1/reports/masters",
  "/api/v1/reports/clients",
  "/api/v1/reports/tasks",
  "/api/v1/reports/${report}:export",
  "/api/v1/admin/audit/filters",
]) {
  if (!appSource.includes(endpoint)) throw new Error(`Required endpoint is missing from the application shell: ${endpoint}`);
}

if (!appSource.includes("AuditWorkspace")) {
  throw new Error("The Phase 10 audit workspace is missing from the application shell.");
}

// The audit navigation and its data load must both stay behind audit.view. The workspace
// renders only for that view, so an unauthorised session never issues the request.
if (!appSource.includes('"audit.view" in session.permissions')) {
  throw new Error("The audit workspace must be gated on the audit.view permission.");
}

// Administration data must not be fetched by sessions that cannot read it, and the entry point
// must be hidden rather than failing with a bare 403 once opened.
if (!appSource.includes("canAdminister")) {
  throw new Error("The administration workspace must be gated on the permissions it reads.");
}
if (!appSource.includes('view === "administration" && canAdminister')) {
  throw new Error("Administration data must load only when that view is opened by a permitted session.");
}

console.log("Web Phase 9 reporting and Phase 10 audit workspace checks passed.");
