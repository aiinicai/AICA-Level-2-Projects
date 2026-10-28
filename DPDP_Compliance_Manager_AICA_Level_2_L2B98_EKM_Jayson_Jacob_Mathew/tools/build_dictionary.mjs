// Generates docs/DATA_DICTIONARY.md from the live database comments. Edit the COMMENT lines in database_schema.sql, not the output.
import { PGlite } from "@electric-sql/pglite";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const db = new PGlite();
for (const f of ["tests/supabase_stubs.sql", "sql/database_schema.sql", "sql/row_level_security.sql"]) await db.exec(readFileSync(resolve(root, f), "utf8"));
const tables = (await db.query(`select c.relname t, obj_description(c.oid) d from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r' order by 1`)).rows;
const cols = (await db.query(`select c.table_name t, c.column_name col, c.data_type dt, c.udt_name u, c.is_nullable nl, c.column_default df, col_description((quote_ident(c.table_schema)||'.'||quote_ident(c.table_name))::regclass, c.ordinal_position) d from information_schema.columns c where c.table_schema='public' order by c.table_name, c.ordinal_position`)).rows;
const cons = (await db.query(`select conrelid::regclass::text t, contype, pg_get_constraintdef(oid) def from pg_constraint where connamespace='public'::regnamespace and contype in ('c','f') order by 1`)).rows;
const FALLBACK = {
  id: "Unique identifier.", tenant_id: "The client institution that owns this row. Never changes after creation; every policy checks it.", created_at: "When the row was created.", updated_at: "When the row last changed (set by the database).",
  created_by: "User who created the row.", name: "Display name.", title: "Short title.", assessment_id: "The assessment this row belongs to.", user_id: "The user concerned.", activity_id: "The processing activity concerned.",
  firm_id: "The CA firm concerned.", granted_at: "When access was granted.", granted_by: "Who granted access.", status: "Current status. Allowed values are in the rules below.", archived_at: "When the record was archived. Archived records are kept, never deleted.",
  description: "Free-text description.", engagement_id: "The engagement this row belongs to.", revoked_at: "When access was withdrawn.", approved_at: "When the approval was recorded.", assessed_at: "When the assessor last recorded a result.",
  assessment_item_id: "The assessment item concerned.", body: "Text of the note.", comments: "Reviewer comments.", evidence_id: "The evidence record concerned.", legal_source_id: "The legal source concerned.", notes: "Free-text notes.",
  reviewer_id: "The reviewer.", scope: "global (platform library) or firm (one firm's library).", vendor_id: "The vendor concerned.", version_no: "Version number. Approved versions are never edited; a change creates a new version.",
  action: "What happened, for example insert, update or export.", actor_id: "User who did it. Empty when the database itself did it.", actor_kind: "client or firm: which kind of user the capability applies to.", applicability_rationale: "Why the control applies, does not apply or needs legal review.",
  approved_by: "User who approved.", archived_reason: "Why the record was archived.", assessed_by: "User who made the assessment (set by the database, not the browser).", assessment_version: "Version of the assessment the report was built from.",
  author_id: "User who wrote the note.", capability: "A named permission, for example edit_assessment.", category_group: "Group for display, for example Student or Special case.", closed_at: "When the action was closed.", closure_verified_at: "When closure evidence was verified.",
  code: "Short stable code.", control_id: "The control this version belongs to.", corrective_action_id: "The corrective action this evidence supports.", data_category_id: "The data category concerned.", decided_at: "When the decision was made.", decision: "The reviewer's decision.",
  department_id: "The department that runs the activity.", dependencies: "Other work this action depends on.", due_at: "When the notification is due.", due_date: "Date the action is due.", effective_date: "Date from which the provision applies. Verify against the Gazette.",
  email: "Email address copied from the sign-in account.", entity_id: "Id of the row that changed.", entity_type: "Table of the row that changed.", full_name: "The user's name.", generated_at: "When the report was generated.", generated_by: "User who generated it.",
  issue: "What is wrong or missing.", issuing_authority: "Body that issued the source.", kind: "Notification kind.", limitations: "Stated limits of the work, shown on reports.", mime_type: "File type, checked against an allow-list.",
  occurred_at: "When it happened.", owner_department_id: "Department that owns the system.", owner_user_id: "Person responsible.", period_end: "Last day covered.", period_start: "First day covered.", provider_confirmed_at: "When the email provider confirmed delivery.",
  provider_message_id: "Id returned by the email provider.", published_on: "Date the source was published.", question_code: "Code of the applicability question.", question_text: "Text of the applicability question as asked.", rationale: "The reason for the decision.",
  recommendation: "What the assessor recommends.", related_id: "Id of the related row.", related_type: "Table of the related row.", report_type: "Kind of report.", retired_at: "When the version was retired.", reviewed_at: "When the review happened.",
  risk_accepted_at: "When management accepted the risk.", risk_level: "low, medium, high or critical. Set by a person, with the rationale.", risk_rationale: "Why this risk level was chosen.", role: "Role held.", shared_with_client: "Whether the client can see it.",
  size_bytes: "File size in bytes.", snapshot: "Frozen copy of the approved content as JSON.", source: "Where the item came from.", source_type: "act, rule, notification, guidance or other.", source_version_id: "The legal source version this relies on.",
  start_date: "Start date.", storage_bucket: "Storage bucket holding the file (private).", subject_id: "Id of the item that was decided on.", subject_version: "Version of the item that was decided on.", submitted_at: "When it was submitted for review.",
  system_id: "The system concerned.", target_date: "Date the owner aims to finish.", uploaded_at: "When the file was uploaded.", verified_at: "When it was verified.", verified_by: "User who verified it.", version_label: "Label of the retrieved version."
};
const grp = (m, k) => (m[k] ||= []);
const byT = {}; cols.forEach((c) => grp(byT, c.t).push(c));
const cT = {}; cons.forEach((c) => grp(cT, c.t.replace("public.", "")).push(c));
const tenantIsolated = new Set(cols.filter((c) => c.col === "tenant_id").map((c) => c.t));
let md = `# Data dictionary\n\nGenerated from the database comments by \`tools/build_dictionary.mjs\`. To change a description, edit the comment in \`sql/database_schema.sql\` and regenerate.\n\n**${tables.length} tables.** ${tenantIsolated.size} carry a \`tenant_id\` and are isolated per client; the rest are global reference data, firm-level data or identity tables (each is listed below as "Scope").\n\nAll ids are \`uuid\`. All timestamps are \`timestamptz\`. Every client table has \`id\`, \`tenant_id\`, \`created_at\` and \`updated_at\` unless noted. Composite foreign keys \`(id, tenant_id)\` stop a row from pointing at another client's row.\n\n`;
for (const t of tables) {
  md += `## ${t.t}\n\n${t.d || ""}\n\nScope: ${tenantIsolated.has(t.t) ? "one client (tenant)" : "not tenant-owned (global, firm-level or identity)"}\n\n| Column | Type | Required | Default | Meaning |\n|---|---|---|---|---|\n`;
  for (const c of byT[t.t] || []) md += `| \`${c.col}\` | ${c.dt === "USER-DEFINED" ? c.u : c.dt} | ${c.nl === "NO" ? "yes" : ""} | ${c.df ? "`" + c.df.replace(/\|/g, "\\|").slice(0, 40) + "`" : ""} | ${(c.d || FALLBACK[c.col] || "").replace(/\|/g, "\\|").replace(/\n/g, " ")} |\n`;
  const checks = (cT[t.t] || []).filter((c) => c.contype === "c");
  if (checks.length) md += `\nRules enforced by the database:\n\n` + checks.map((c) => "- `" + c.def.replace(/\s+/g, " ").slice(0, 300) + "`").join("\n") + "\n";
  md += "\n";
}
writeFileSync(resolve(root, "docs/DATA_DICTIONARY.md"), md);
console.log("tables:", tables.length, "columns:", cols.length, "bytes:", md.length, "still blank:", cols.filter((c) => !c.d && !FALLBACK[c.col]).map((c) => c.t + "." + c.col).join(","));
