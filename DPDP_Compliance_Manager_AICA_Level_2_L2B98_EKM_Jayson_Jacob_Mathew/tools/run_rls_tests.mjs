// Runs the tenant-isolation and security tests against an in-memory PostgreSQL (PGlite).
// usage: node tools/run_rls_tests.mjs        (writes tests/rls_results.json and prints a summary)
import { PGlite } from "@electric-sql/pglite";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const rd = (f) => readFileSync(resolve(root, f), "utf8");
const ids = JSON.parse(rd("tests/ids.json"));
const U = ids.users, T = ids.tenants, A = ids.activities, IT = ids.items, AC = ids.actions, E = ids.evidence, AS = ids.assessments;
const db = new PGlite();
for (const f of ["tests/supabase_stubs.sql", "sql/database_schema.sql", "sql/row_level_security.sql", "sql/seed_demo_data.sql"]) await db.exec(rd(f));

// Run sql as a user (or "anon" / "service"), inside a transaction that is always rolled back.
async function run(who, sql, params = []) {
  const ROLLBACK = new Error("rollback");
  let out;
  try {
    await db.transaction(async (tx) => {
      if (who === "anon") await tx.query("set local role anon");
      else if (who === "service") await tx.query("set local role service_role");
      else { await tx.query("set local role authenticated"); await tx.query("select set_config('request.jwt.claim.sub', $1, true)", [U[who]]); }
      try { const r = await tx.query(sql, params); out = { rows: r.rows, count: r.affectedRows ?? r.rows.length }; }
      catch (e) { out = { error: e.message }; }
      throw ROLLBACK;
    });
  } catch (e) { if (e !== ROLLBACK) out = { error: "harness: " + e.message }; }
  return out;
}
const results = [];
function rec(id, area, name, pass, detail = "") { results.push({ id, area, name, pass: !!pass, detail: pass ? "" : String(detail) }); }
const n = (r) => (r.error ? "ERR " + r.error : r.rows[0] ? Number(Object.values(r.rows[0])[0]) : 0);

// ---- 1. Row visibility per table: expected counts by persona -------------------------------
const vis = async (id, who, table, where, expected) => {
  const r = await run(who, `select count(*)::int c from ${table} ${where ? "where " + where : ""}`);
  rec(id, "visibility", `${who} sees ${expected} rows of ${table}${where ? " where " + where : ""}`, !r.error && r.rows[0].c === expected, r.error || `got ${r.rows?.[0]?.c}`);
};
let k = 0; const V = (...a) => vis("VIS-" + String(++k).padStart(3, "0"), ...a);
// anonymous sees nothing at all
for (const t of ["tenants", "profiles", "assessments", "evidence_records", "controls", "audit_events", "data_categories"]) {
  const r = await run("anon", `select count(*) c from public.${t}`);
  rec("ANON-" + t, "anonymous", `anonymous cannot read ${t}`, !!r.error, "anonymous read succeeded");
}
// the outsider has no membership anywhere
for (const t of ["tenants", "engagements", "processing_activities", "assessments", "assessment_items", "evidence_records", "corrective_actions", "report_runs", "audit_events", "departments", "vendors", "systems"]) await V("outsider", "public." + t, "", 0);
await V("outsider", "public.tenants", "", 0);
// school users see only the school
for (const who of ["a_admin", "a_lead", "a_coord", "a_evid", "a_view", "a_rev"]) {
  await V(who, "public.tenants", "", 1);
  await V(who, "public.processing_activities", `tenant_id <> '${T.TA}'`, 0);
  await V(who, "public.evidence_records", `tenant_id <> '${T.TA}'`, 0);
  await V(who, "public.assessments", `tenant_id <> '${T.TA}'`, 0);
  await V(who, "public.corrective_actions", `tenant_id <> '${T.TA}'`, 0);
}
await V("a_old", "public.tenants", "", 0);                  // disabled membership
await V("a_old", "public.processing_activities", "", 0);
// firm admin sees tenant metadata of own firm only, but no client content without an assignment
await V("fa1", "public.tenants", "", 2); await V("fa1", "public.engagements", "", 2);
await V("fa1", "public.processing_activities", "", 0); await V("fa1", "public.evidence_records", "", 0); await V("fa1", "public.assessments", "", 0);
await V("fa1", "public.tenants", `id = '${T.TC}'`, 0);
await V("fa2", "public.tenants", "", 1); await V("fa2", "public.tenants", `id = '${T.TA}'`, 0);
await V("fa2", "public.processing_activities", `tenant_id = '${T.TA}'`, 0);
// assigned consultant: school content yes, college no
await V("tm1", "public.processing_activities", `tenant_id = '${T.TA}'`, 8); await V("tm1", "public.processing_activities", `tenant_id = '${T.TB}'`, 0);
await V("tm1", "public.evidence_records", `tenant_id = '${T.TB}'`, 0);
await V("tm_un", "public.processing_activities", "", 0); await V("tm_un", "public.assessments", "", 0);
await V("tm2", "public.processing_activities", `tenant_id = '${T.TA}'`, 0); await V("tm2", "public.processing_activities", `tenant_id = '${T.TC}'`, 2);
// reviewer on both school and college
await V("rv1", "public.processing_activities", `tenant_id = '${T.TB}'`, 3); await V("rv1", "public.processing_activities", `tenant_id = '${T.TC}'`, 0);
// notes: firm-only notes hidden from clients
await V("a_admin", "public.engagement_notes", "", 1); await V("a_lead", "public.engagement_notes", "visibility = 'firm_only'", 0);
await V("tm1", "public.engagement_notes", `tenant_id = '${T.TA}'`, 2); await V("rv1", "public.engagement_notes", `tenant_id = '${T.TB}'`, 1);
// drafts and sharing: client roles see only approved + shared assessments
await V("a_lead", "public.assessments", "", 1); await V("a_lead", "public.assessments", "status <> 'approved'", 0);
await V("a_view", "public.assessments", "", 1); await V("tm1", "public.assessments", `tenant_id = '${T.TA}'`, 2);
await V("a_lead", "public.report_runs", "", 1); await V("a_lead", "public.report_runs", "status = 'draft'", 0); await V("tm1", "public.report_runs", "", 2);
// firm library visibility: other firm's controls and drafts
await V("tm1", "public.controls", "scope = 'firm'", 1); await V("tm2", "public.controls", "scope = 'firm'", 1);
await V("tm2", "public.control_versions", `id = '${ids.cv_f1_draft}'`, 0); await V("tm1", "public.control_versions", `id = '${ids.cv_f2}'`, 0);
await V("a_lead", "public.control_versions", `id = '${ids.cv_f1_draft}'`, 0);
await V("a_lead", "public.control_versions", `review_status <> 'approved'`, 0);
await V("a_admin", "public.data_categories", "", 10);
// audit: only users with view_audit see events, never another tenant's
await V("a_view", "public.audit_events", "", 0); await V("a_evid", "public.audit_events", "", 0);
await V("a_admin", "public.audit_events", `tenant_id <> '${T.TA}'`, 0); await V("a_admin", "public.audit_events", `tenant_id = '${T.TA}'`, (await run("service", `select count(*)::int c from public.audit_events where tenant_id='${T.TA}'`)).rows[0].c);
// scoped roles
await V("a_coord", "public.processing_activities", "", 8);
await V("a_evid", "public.evidence_records", "", 2);   // own upload (E2) + evidence on the item they own (E3); not E1, E4, E5
// platform admin has no automatic content access
await V("pa", "public.processing_activities", "", 0); await V("pa", "public.evidence_records", "", 0); await V("pa", "public.tenants", "", 0);
await V("pa", "public.controls", "scope = 'global'", 8);

// ---- 2. Writes that must be refused ---------------------------------------------------------
let w = 0;
const mustFail = async (who, name, sql, params = []) => { const r = await run(who, sql, params); rec("DENY-" + String(++w).padStart(3, "0"), "write-denied", `${who}: ${name}`, !!r.error || r.count === 0, "write was allowed (" + JSON.stringify(r.rows?.[0] ?? r.count) + ")"); };
const mustWork = async (who, name, sql, params = []) => { const r = await run(who, sql, params); rec("ALLOW-" + String(++w).padStart(3, "0"), "write-allowed", `${who}: ${name}`, !r.error && (r.count > 0 || r.rows.length >= 0), r.error); return r; };
// cross-tenant inserts and updates
await mustFail("a_lead", "insert activity into another tenant", `insert into public.processing_activities (tenant_id, name) values ('${T.TB}', 'x')`);
await mustFail("a_lead", "update another tenant's activity", `update public.processing_activities set name='hacked' where tenant_id='${T.TB}'`);
await mustFail("a_lead", "move own activity to another tenant", `update public.processing_activities set tenant_id='${T.TB}' where id='${A.adm}'`);
await mustFail("a_lead", "delete activity", `delete from public.processing_activities where id='${A.adm}'`);
await mustFail("b_lead", "insert evidence into the school", `insert into public.evidence_records (tenant_id, title, storage_path) values ('${T.TA}', 'x', '${T.TA}/x/y.pdf')`);
await mustFail("tm2", "insert activity into the school", `insert into public.processing_activities (tenant_id, name) values ('${T.TA}', 'x')`);
await mustFail("fa1", "firm admin edits school activity without assignment", `update public.processing_activities set name='x' where id='${A.adm}'`);
await mustFail("fa1", "firm admin inserts activity without assignment", `insert into public.processing_activities (tenant_id, name) values ('${T.TA}', 'x')`);
await mustFail("tm1", "insert activity into the college (not assigned)", `insert into public.processing_activities (tenant_id, name) values ('${T.TB}', 'x')`);
await mustFail("outsider", "create tenant", `insert into public.tenants (firm_id, name, institution_type) values ('${ids.firms.F1}', 'x', 'school')`);
await mustFail("outsider", "create firm membership for self", `insert into public.firm_memberships (firm_id, user_id, role) values ('${ids.firms.F1}', '${U.outsider}', 'firm_admin')`);
await mustFail("a_admin", "client admin grants self platform admin", `insert into public.platform_admins (user_id) values ('${U.a_admin}')`);
await mustFail("a_admin", "client admin reads platform_admins", `select * from public.platform_admins`);
await mustFail("tm1", "consultant adds himself as school client admin", `insert into public.tenant_memberships (tenant_id, user_id, role, status) values ('${T.TA}', '${U.tm1}', 'client_admin', 'active')`);
await mustFail("a_lead", "privacy lead creates client admin", `insert into public.tenant_memberships (tenant_id, user_id, role, status) values ('${T.TA}', '${U.outsider}', 'client_admin', 'active')`);
await mustFail("a_admin", "client admin adds member to another tenant", `insert into public.tenant_memberships (tenant_id, user_id, role, status) values ('${T.TB}', '${U.outsider}', 'client_admin', 'active')`);
await mustFail("a_view", "management viewer edits an activity", `update public.processing_activities set name='x' where id='${A.adm}'`);
await mustFail("a_rev", "client reviewer edits an activity", `update public.processing_activities set name='x' where id='${A.adm}'`);
await mustFail("a_evid", "evidence contributor edits an activity", `update public.processing_activities set name='x' where id='${A.adm}'`);
await mustFail("a_coord", "coordinator edits another department's activity", `update public.processing_activities set name='x' where id='${A.adm}'`);
await mustFail("a_lead", "client edits assessment item", `update public.assessment_items set result='implemented' where id='${IT.ntc}'`);
await mustFail("a_lead", "client edits assessment", `update public.assessments set title='x' where id='${AS.AS1}'`);
// audit and history are append-only
await mustFail("a_admin", "update an audit event", `update public.audit_events set action='x'`);
await mustFail("a_admin", "delete an audit event", `delete from public.audit_events`);
await mustFail("service", "service role deletes audit rows (append-only trigger)", `delete from public.audit_events`);
await mustFail("tm1", "forge an audit event", `insert into public.audit_events (tenant_id, action) values ('${T.TA}', 'forged')`);
await mustFail("rv1", "edit a review decision", `update public.review_decisions set decision='approved'`);
await mustFail("rv1", "delete a review decision", `delete from public.review_decisions`);
await mustFail("tm1", "edit a snapshot", `update public.assessment_snapshots set snapshot='{}'::jsonb`);
// status fields are not directly writable
await mustFail("tm1", "directly approve an assessment", `update public.assessments set status='approved' where id='${AS.AS2}'`);
await mustFail("rv1", "directly set shared_with_client", `update public.assessments set shared_with_client=true where id='${AS.ASB}'`);
await mustFail("a_lead", "directly close an action", `update public.corrective_actions set status='closed' where id='${AC["1"]}'`);
await mustFail("a_evid", "directly verify evidence", `update public.evidence_records set status='verified' where id='${E["2"]}'`);
await mustFail("tm1", "directly approve a control version", `update public.control_versions set review_status='approved' where id='${ids.cv_f1_draft}'`);
await mustFail("tm1", "directly verify a source version", `update public.legal_source_versions set verification_status='verified' where id='${ids.lsv.LSV3}'`);
// immutability of approved library and assessments (even for the service role)
await mustFail("service", "edit an approved control version", `update public.control_versions set statement='changed' where id='${ids.controls["NTC-01"]}'`);
await mustFail("service", "edit an approved legal source version", `update public.legal_source_versions set notes='changed' where id='${ids.lsv.LSV1}'`);
await mustFail("service", "edit item of an approved assessment", `update public.assessment_items set assessor_notes='changed' where id='${IT.ntc}'`);
await mustFail("service", "add an item to an approved assessment", `insert into public.assessment_items (tenant_id, assessment_id, control_version_id) values ('${T.TA}', '${AS.AS1}', '${ids.controls["BRC-01"]}')`);
// tenant_id can never be changed
await mustFail("service", "service role changes tenant of an activity", `update public.processing_activities set tenant_id='${T.TB}' where id='${A.adm}'`);
await mustFail("service", "service role changes tenant of an evidence record", `update public.evidence_records set tenant_id='${T.TB}' where id='${E["1"]}'`);
// composite foreign keys: no cross-tenant references
await mustFail("service", "link a school activity to a college system", `insert into public.activity_systems (tenant_id, activity_id, system_id) values ('${T.TA}', '${A.adm}', '${ids.vendors.b_erp}')`);
await mustFail("service", "assessment item pointing at another tenant's assessment", `insert into public.assessment_items (tenant_id, assessment_id, control_version_id) values ('${T.TB}', '${AS.AS2}', '${ids.controls["BRC-01"]}')`);
await mustFail("service", "action on another tenant's item", `insert into public.corrective_actions (tenant_id, assessment_item_id, title, issue, risk_level) values ('${T.TB}', '${IT.ntc}', 't', 'i', 'low')`);
// check constraints
await mustFail("service", "not_applicable result with applicable applicability", `update public.assessment_items set result='not_applicable' where id='${IT.a2_sec}'`);
await mustFail("service", "implemented_verified without verified evidence", `update public.assessment_items set result='implemented_verified', evidence_quality='verified' where id='${IT.a2_sec}'`);
await mustFail("service", "evidence path in another tenant folder", `insert into public.evidence_records (tenant_id, title, storage_path) values ('${T.TA}', 'x', '${T.TB}/x/y.pdf')`);
await mustFail("service", "assessment item using an unapproved control version", `insert into public.assessment_items (tenant_id, assessment_id, control_version_id) values ('${T.TA}', '${AS.AS2}', '${ids.cv_f1_draft}')`);
// Not Assessed must stay Not Assessed unless a result is set (rule: never counted as compliant) - checked in dashboard section
// anonymous calls to RPCs
for (const f of ["dashboard_metrics('" + T.TA + "')", "my_tenants()", "submit_assessment_for_review('" + AS.AS2 + "')"]) { const r = await run("anon", `select * from public.${f}`); rec("ANON-rpc-" + f.split("(")[0], "anonymous", `anonymous cannot call ${f.split("(")[0]}`, !!r.error, "allowed"); }
// app_private is not callable by anonymous
{ const r = await run("anon", `select app_private.is_active_user()`); rec("ANON-private", "anonymous", "anonymous cannot call app_private functions", !!r.error, "allowed"); }

// ---- 3. Writes that must work ---------------------------------------------------------------
await mustWork("a_lead", "update own tenant activity", `update public.processing_activities set description='ok' where id='${A.adm}'`);
await mustWork("a_coord", "coordinator edits own department's activity", `update public.processing_activities set description='ok' where id='${A.exam}'`);
await mustWork("a_lead", "insert activity", `insert into public.processing_activities (tenant_id, name) values ('${T.TA}', 'new activity')`);
await mustWork("tm1", "assigned consultant edits assessment item (draft assessment)", `update public.assessment_items set assessor_notes='n' where id='${IT.a2_sec}'`);
await mustWork("a_admin", "client admin adds an evidence contributor", `insert into public.tenant_memberships (tenant_id, user_id, role, status) values ('${T.TA}', '${U.outsider}', 'evidence_contributor', 'active')`);
await mustWork("a_evid", "evidence contributor requests-placeholder is insertable by editor", `select 1`);
await mustWork("fa1", "firm admin creates tenant for own firm", `insert into public.tenants (firm_id, name, institution_type) values ('${ids.firms.F1}', 'New Demo Tenant', 'school')`);
await mustWork("a_admin", "client admin edits own profile fields of tenant", `update public.tenants set description='ok' where id='${T.TA}'`);
{ const r = await run("a_admin", `update public.tenants set name='x' where id='${T.TA}' returning id`); rec("TEN-edit", "write-allowed", "client admin updates tenant via edit_profile", !r.error && r.count === 1, r.error || "no row"); }

// ---- 4. RPC rules, maker-checker and state machine ------------------------------------------
const rpc = async (id, who, name, sql, expectOk, params = []) => { const r = await run(who, sql, params); rec(id, "rpc", `${who}: ${name}`, expectOk ? !r.error : !!r.error, expectOk ? r.error : "was allowed"); return r; };
await rpc("RPC-01", "a_lead", "client cannot submit assessment for review", `select public.submit_assessment_for_review('${AS.AS2}')`, false);
await rpc("RPC-02", "tm1", "submitting without a reviewer is refused", `select public.submit_assessment_for_review('${AS.AS2}')`, false);
await rpc("RPC-03", "tm_un", "unassigned consultant cannot submit", `select public.submit_assessment_for_review('${AS.AS2}')`, false);
{ // maker-checker: submitter cannot approve; reviewer can
}
// multi-step flows need a single transaction: use a custom helper
async function flow(who, steps) {
  const ROLLBACK = new Error("rb"); const log = [];
  try { await db.transaction(async (tx) => {
    for (const s of steps) {
      if (s.as && s.as !== "service") { await tx.query("reset role"); await tx.query("select set_config('request.jwt.claim.sub',$1,true)", [U[s.as]]); }
      await tx.query("reset role"); await tx.query("savepoint st");
      if (s.as === "service") await tx.query("set local role service_role"); else if (s.as) { await tx.query("set local role authenticated"); }
      try { const r = await tx.query(s.sql, s.params || []); log.push({ ok: true, rows: r.rows }); await tx.query("release savepoint st"); } catch (e) { await tx.query("rollback to savepoint st"); log.push({ ok: false, error: e.message }); }
    } throw ROLLBACK; }); } catch (e) { if (e !== ROLLBACK) log.push({ ok: false, error: "harness " + e.message }); }
  return log;
}
{
  const L = await flow(null, [
    { as: "tm1", sql: `update public.assessments set reviewer_id='${U.rv1}' where id='${AS.AS2}'` },
    { as: "tm1", sql: `select public.submit_assessment_for_review('${AS.AS2}')` },
    { as: "tm1", sql: `select public.decide_assessment('${AS.AS2}','approved')` },
    { as: "rv1", sql: `select public.decide_assessment('${AS.AS2}','approved')` },
    { as: "rv1", sql: `select status, shared_with_client from public.assessments where id='${AS.AS2}'` },
    { as: "rv1", sql: `update public.assessment_items set assessor_notes='late edit' where id='${IT.a2_sec}'` },
  ]);
  rec("RPC-04", "maker-checker", "preparer cannot approve own assessment", L[1].ok && !L[2].ok, "preparer approved");
  rec("RPC-05", "maker-checker", "reviewer approves submitted assessment", L[3].ok, L[3].error);
  rec("RPC-06", "state-machine", "approved assessment is frozen against item edits", !L[5].ok || L[5].rows?.length === 0, "edit after approval allowed");
}
{
  const L = await flow(null, [
    { as: "rv1", sql: `select public.decide_assessment('${AS.AS2}','approved')` },              // not submitted
    { as: "a_lead", sql: `select public.decide_assessment('${AS.AS1}','approved')` },
    { as: "tm1", sql: `select public.reopen_assessment('${AS.AS1}','x')` },
    { as: "rv1", sql: `select public.reopen_assessment('${AS.AS1}','Correction needed (demo)')` },
    { as: "rv1", sql: `select status, version_no from public.assessments where id='${AS.AS1}'` },
  ]);
  rec("RPC-07", "state-machine", "cannot approve an assessment that was never submitted", !L[0].ok, "allowed");
  rec("RPC-08", "rpc", "client cannot decide assessments", !L[1].ok, "allowed");
  rec("RPC-09", "rpc", "consultant cannot reopen an approved assessment", !L[2].ok, "allowed");
  rec("RPC-10", "versioning", "reviewer reopens approved assessment and version rises", L[3].ok && L[4].rows?.[0]?.version_no === 2 && L[4].rows?.[0]?.status !== "approved", L[3].error || JSON.stringify(L[4].rows));
}
{ // evidence
  const L = await flow(null, [
    { sql: `insert into storage.objects (bucket_id, name) values ('evidence','${T.TA}/${E["3"]}/bus-vendor-contract.pdf')` },
    { as: "a_evid", sql: `select public.confirm_evidence_upload('${E["3"]}','contract.pdf','application/pdf',90000,'${"9".repeat(64)}')` },
    { as: "a_evid", sql: `select status, uploaded_by from public.evidence_records where id='${E["3"]}'` },
    { as: "a_evid", sql: `select public.decide_evidence('${E["3"]}','verified')` },
    { as: "rv1", sql: `select public.decide_evidence('${E["3"]}','verified')` },
    { as: "a_rev", sql: `select public.decide_evidence('${E["2"]}','verified')` },
    { as: "a_lead", sql: `select public.confirm_evidence_upload('${E["1"]}','x.pdf','application/pdf',1,'${"1".repeat(64)}')` },
    { as: "b_lead", sql: `select public.confirm_evidence_upload('${E["3"]}','x.pdf','application/pdf',1,'${"1".repeat(64)}')` },
    { as: "a_lead", sql: `select public.confirm_evidence_upload('${E["3"]}','x.exe','application/x-msdownload',1,'${"1".repeat(64)}')` },
  ]);
  rec("EVD-01", "evidence", "contributor confirms upload of requested evidence", L[1].ok, L[1].error);
  rec("EVD-02", "evidence", "uploader is recorded as the contributor", L[2].rows?.[0]?.uploaded_by === U.a_evid && L[2].rows?.[0]?.status === "submitted", JSON.stringify(L[2].rows));
  rec("EVD-03", "maker-checker", "uploader cannot verify own evidence", !L[3].ok, "uploader verified own evidence");
  rec("EVD-04", "evidence", "firm reviewer verifies evidence uploaded by the client", L[4].ok, L[4].error);
  rec("EVD-08", "evidence", "client roles cannot verify evidence (independent firm review)", !L[3].ok && !L[5].ok, "client verified");
  rec("EVD-05", "evidence", "cannot re-confirm an upload on an already submitted/verified record", !L[6].ok, "allowed");
  rec("EVD-06", "isolation", "another tenant cannot confirm upload on this evidence", !L[7].ok, "allowed");
  rec("EVD-07", "evidence", "disallowed file type is rejected", !L[8].ok, "allowed");
}
{ // actions
  const L = await flow(null, [
    { as: "a_lead", sql: `select public.set_action_status('${AC["1"]}','in_progress')` },
    { as: "a_view", sql: `select public.set_action_status('${AC["1"]}','in_progress')` },
    { as: "a_lead", sql: `select public.close_corrective_action('${AC["1"]}')` },
    { as: "a_lead", sql: `select public.close_corrective_action('${AC["5"]}')` },
    { as: "tm1", sql: `select public.close_corrective_action('${AC["5"]}')` },
    { as: "rv1", sql: `select public.close_corrective_action('${AC["5"]}')` },
    { as: "a_admin", sql: `select public.accept_risk('${AC["3"]}','')` },
    { as: "a_admin", sql: `select public.accept_risk('${AC["3"]}','Management accepts the risk for the stated period (demo rationale).')` },
    { as: "b_lead", sql: `select public.set_action_status('${AC["1"]}','in_progress')` },
  ]);
  rec("ACT-01", "actions", "action owner moves action to in progress", L[0].ok, L[0].error);
  rec("ACT-02", "actions", "viewer cannot change action status", !L[1].ok, "allowed");
  rec("ACT-03", "actions", "cannot close an action with no closure evidence", !L[2].ok, "allowed");
  rec("ACT-04", "maker-checker", "client privacy lead cannot close action awaiting firm review", !L[3].ok, "client closed it");
  rec("ACT-05", "actions", "reviewer closes action that has verified closure evidence", L[5].ok, L[5].error);
  rec("ACT-06", "actions", "accept risk needs a rationale", !L[6].ok, "allowed");
  rec("ACT-07", "actions", "client admin can accept risk with a rationale", L[7].ok, L[7].error);
  rec("ACT-08", "isolation", "other tenant cannot change this action", !L[8].ok, "allowed");
}
{ // library governance
  const L = await flow(null, [
    { as: "tm1", sql: `select public.set_control_version_status('${ids.cv_f1_draft}','in_review')` },
    { as: "tm1", sql: `select public.set_control_version_status('${ids.cv_f1_draft}','approved')` },
    { as: "rv1", sql: `select public.set_control_version_status('${ids.cv_f1_draft}','approved')` },
    { as: "tm2", sql: `select public.set_control_version_status('${ids.cv_f1_draft}','in_review')` },
    { as: "tm1", sql: `select public.set_source_version_status('${ids.lsv.LSV3}','in_review')` },
    { as: "rv1", sql: `select public.set_source_version_status('${ids.lsv.LSV3}','approved')` },
    { as: "rv1", sql: `select public.set_source_version_status('${ids.lsv.LSV3}','approved', true, 'In Force — Verified')` },
    { as: "a_lead", sql: `select public.set_source_version_status('${ids.lsv.LSV3}','approved')` },
  ]);
  rec("LIB-01", "library", "author submits own control version for review", L[0].ok, L[0].error);
  rec("LIB-02", "maker-checker", "author cannot approve own control version", !L[1].ok, "allowed");
  rec("LIB-03", "library", "control version cannot be approved against an unapproved legal source", !L[2].ok, "approved against unapproved source");
  rec("LIB-04", "isolation", "other firm cannot change this firm's control version", !L[3].ok, "allowed");
  rec("LIB-05", "library", "non-demo source version cannot be approved without verification", !L[5].ok, "approved while unverified");
  rec("LIB-07", "library", "reviewer verifies and approves non-demo source version with verified commencement", L[6].ok, L[6].error);
  rec("LIB-06", "library", "client user cannot approve library items", !L[7].ok, "allowed");
}
{ // dashboard
  const D = await run("a_lead", `select public.dashboard_metrics('${T.TA}') d`);
  const d = D.rows?.[0]?.d;
  rec("DSH-01", "dashboard", "dashboard returns metrics for own tenant", !!d && !D.error, D.error);
  rec("DSH-02", "isolation", "dashboard refuses another tenant", !!(await run("a_lead", `select public.dashboard_metrics('${T.TB}')`)).error, "allowed");
  rec("DSH-03", "isolation", "unrelated user gets no dashboard", !!(await run("outsider", `select public.dashboard_metrics('${T.TA}')`)).error, "allowed");
  const MT = await run("a_lead", `select * from public.my_tenants()`);
  rec("DSH-04", "isolation", "my_tenants lists only own tenant", MT.rows?.length === 1, JSON.stringify(MT.rows));
  const MT2 = await run("fa1", `select * from public.my_tenants()`);
  rec("DSH-05", "isolation", "firm admin my_tenants lists own firm's two tenants", MT2.rows?.length === 2, JSON.stringify(MT2.rows));
  globalThis.__dash = d;
}
// ---- 5. Structural checks (run as the database owner) ----------------------------------------
{
  const q = async (s) => (await db.query(s)).rows;
  const noRls = await q(`select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r' and not c.relrowsecurity`);
  rec("STR-01", "structure", "RLS is enabled on every public table", noRls.length === 0, noRls.map((r) => r.relname).join(","));
  const noPol = await q(`select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and c.relkind='r' and c.relrowsecurity and not exists (select 1 from pg_policy p where p.polrelid=c.oid)`);
  rec("STR-02", "structure", "every RLS table has a policy (platform_admins is deliberately empty)", noPol.every((r) => r.relname === "platform_admins"), noPol.map((r) => r.relname).join(","));
  const noTenant = await q(`select table_name from information_schema.tables t where table_schema='public' and table_type='BASE TABLE' and not exists (select 1 from information_schema.columns c where c.table_schema='public' and c.table_name=t.table_name and c.column_name='tenant_id')`);
  const allowed = new Set(["profiles","platform_admins","firms","firm_memberships","tenants","data_categories","legal_sources","legal_source_versions","controls","control_versions","role_capabilities"]);
  rec("STR-03", "structure", "every table without tenant_id is a known global or firm-level table", noTenant.every((r) => allowed.has(r.table_name)), noTenant.filter((r) => !allowed.has(r.table_name)).map((r) => r.table_name).join(","));
  const anon = await q(`select table_name from information_schema.role_table_grants where table_schema='public' and grantee='anon' limit 5`);
  rec("STR-04", "structure", "anonymous role holds no table privileges", anon.length === 0, JSON.stringify(anon));
  const del = await q(`select table_name from information_schema.role_table_grants where table_schema='public' and grantee='authenticated' and privilege_type='DELETE' order by 1`);
  const delOk = new Set(["firm_memberships","tenant_memberships","engagement_assignments","engagement_notes","applicability_decisions","assessment_items","activity_systems","activity_vendors","activity_data_categories"]);
  rec("STR-05", "structure", "DELETE is granted only on join and working tables", del.every((r) => delOk.has(r.table_name)), del.filter((r) => !delOk.has(r.table_name)).map((r) => r.table_name).join(","));
  const pub = await q(`select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and has_function_privilege('anon', p.oid, 'execute')`);
  rec("STR-06", "structure", "anonymous role can execute no public function", pub.length === 0, JSON.stringify(pub));
  const sdef = await q(`select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('public','app_private') and p.prosecdef and (p.proconfig is null or not exists (select 1 from unnest(p.proconfig) c where c like 'search_path=%'))`);
  rec("STR-07", "structure", "every SECURITY DEFINER function pins search_path", sdef.length === 0, sdef.map((r) => r.proname).join(","));
  const bucket = await q(`select public, file_size_limit from storage.buckets where id='evidence'`);
  rec("STR-08", "structure", "evidence bucket is private with a size limit", bucket[0] && bucket[0].public === false && Number(bucket[0].file_size_limit) > 0, JSON.stringify(bucket));
  const demoOnly = await q(`select count(*)::int c from public.tenants where not is_demo`);
  rec("STR-09", "structure", "all seeded tenants are flagged demo", demoOnly[0].c === 0, "");
  const unver = await q(`select count(*)::int c from public.legal_source_versions where approval_state='approved' and not is_demo and verification_status <> 'verified'`);
  rec("STR-10", "structure", "no non-demo approved legal source lacks verification", unver[0].c === 0, "");
  const pw = await q(`select count(*)::int c from auth.users where encrypted_password is not null`);
  rec("STR-11", "structure", "seed users carry no password", pw[0].c === 0, "");
}
// ---- 6. Storage policies ---------------------------------------------------------------------
async function storage(who, op, path, bucket = "evidence") {
  const sql = op === "select" ? `select count(*)::int c from storage.objects where bucket_id=$1 and name=$2`
    : `insert into storage.objects (bucket_id, name) values ($1,$2)`;
  return run(who, sql, [bucket, path]);
}
await db.exec(`insert into storage.objects (bucket_id, name) values ('evidence','${T.TA}/${E["1"]}/security-policy.pdf'),('evidence','${T.TB}/${E["b1"]}/policy.pdf')`);
{
  let r;
  r = await storage("a_lead", "select", `${T.TA}/${E["1"]}/security-policy.pdf`); rec("STO-01", "storage", "own tenant member can read own evidence object", r.rows?.[0]?.c === 1, r.error || JSON.stringify(r.rows));
  r = await storage("b_lead", "select", `${T.TA}/${E["1"]}/security-policy.pdf`); rec("STO-02", "storage", "other tenant cannot read this object", r.rows?.[0]?.c === 0, r.error || JSON.stringify(r.rows));
  r = await storage("outsider", "select", `${T.TA}/${E["1"]}/security-policy.pdf`); rec("STO-03", "storage", "outsider cannot read object", r.rows?.[0]?.c === 0, r.error || "");
  r = await storage("anon", "select", `${T.TA}/${E["1"]}/security-policy.pdf`); rec("STO-04", "storage", "anonymous cannot read object", !!r.error || r.rows?.[0]?.c === 0, "");
  r = await storage("tm1", "select", `${T.TA}/${E["1"]}/security-policy.pdf`); rec("STO-05", "storage", "assigned consultant can read object", r.rows?.[0]?.c === 1, r.error || "");
  r = await storage("tm1", "select", `${T.TB}/${E["b1"]}/policy.pdf`); rec("STO-06", "storage", "consultant not assigned to the college cannot read its object", r.rows?.[0]?.c === 0, r.error || "");
  r = await storage("fa1", "select", `${T.TA}/${E["1"]}/security-policy.pdf`); rec("STO-07", "storage", "firm admin without assignment cannot read object", r.rows?.[0]?.c === 0, r.error || "");
  r = await storage("a_evid", "insert", `${T.TA}/${E["3"]}/bus-vendor-contract.pdf`); rec("STO-08", "storage", "contributor can upload to the path of a placeholder record", !r.error, r.error);
  r = await storage("a_evid", "insert", `${T.TA}/${ids.activities.adm}/random.pdf`); rec("STO-09", "storage", "cannot upload to a path with no evidence record", !!r.error, "allowed");
  r = await storage("a_evid", "insert", `${T.TB}/${E["b1"]}/policy.pdf`); rec("STO-10", "storage", "cannot upload into another tenant's folder", !!r.error, "allowed");
  r = await storage("a_view", "insert", `${T.TA}/${E["3"]}/bus-vendor-contract.pdf`); rec("STO-11", "storage", "viewer cannot upload", !!r.error, "allowed");
  r = await run("a_evid", `update storage.objects set name='x' where bucket_id='evidence'`); rec("STO-12", "storage", "no one can rename objects", r.count === 0 || !!r.error, "");
  r = await run("a_lead", `delete from storage.objects where bucket_id='evidence'`); rec("STO-13", "storage", "no one can delete objects", r.count === 0 || !!r.error, "");
}
// ---- 7. Disabled membership and self-escalation ---------------------------------------------
{
  const L = await flow(null, [
    { as: "a_admin", sql: `update public.tenant_memberships set role='management_viewer' where user_id='${U.a_rev}' returning 1` },
    { as: "a_view", sql: `update public.tenant_memberships set role='client_admin' where user_id='${U.a_view}' returning 1` },
    { as: "a_lead", sql: `update public.profiles set full_name='x' where id='${U.a_admin}' returning 1` },
    { as: "a_lead", sql: `update public.profiles set full_name='Renamed Self (demo)' where id='${U.a_lead}' returning 1` },
  ]);
  rec("ESC-01", "escalation", "client admin can change a member's role in own tenant", L[0].ok && L[0].rows.length === 1, L[0].error);
  rec("ESC-02", "escalation", "viewer cannot promote self", !L[1].ok || L[1].rows.length === 0, "promoted self");
  rec("ESC-03", "escalation", "user cannot edit another user's profile", !L[2].ok || L[2].rows.length === 0, "edited other profile");
  rec("ESC-04", "escalation", "user can edit own profile name", L[3].ok && L[3].rows.length === 1, L[3].error);
}
// ---- report -----------------------------------------------------------------------------------
const failed = results.filter((r) => !r.pass);
writeFileSync(resolve(root, "tests/rls_results.json"), JSON.stringify({ total: results.length, failed: failed.length, results }, null, 1));
console.log(`tests: ${results.length}  passed: ${results.length - failed.length}  failed: ${failed.length}`);
for (const f of failed) console.log("FAIL", f.id, "|", f.name, "|", f.detail);
