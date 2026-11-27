WD.hooks.dashboard = [];
const STATUSES = ["New", "In Progress", "Awaiting Documents", "In Review", "Approved", "Closed"];
const PRIO = [["Normal", "Normal"], ["High", "High"], ["Low", "Low"]];
async function openAssignment(id, refresh) {
  const box = h("div", {}); const m = modal("Assignment", box, { wide: true });
  const draw = async () => {
    const a = await api("work/assignments/" + id), users = (await api("admin/users").catch(() => [])).filter(u => u.role !== "ca" || true);
    const acts = [];
    const setS = (s, note) => act(async () => { await post(`work/assignments/${id}/status`, { status: s, note }); draw(); refresh && refresh(); }, "Updated");
    if (a.status === "New" || a.status === "Awaiting Documents") acts.push(h("button", { class: "btn sm", onclick: () => setS("In Progress") }, "Start / resume work"));
    if (["In Progress", "Awaiting Documents", "New"].includes(a.status) && on("work", "review_approval")) acts.push(h("button", { class: "btn sm ok", onclick: () => setS("In Review") }, "Submit for review"));
    if (isBoss() && a.status === "In Review") acts.push(h("button", { class: "btn sm ok", onclick: () => setS("Approved") }, "Approve"), h("button", { class: "btn sm bad", onclick: () => formModal("Send back", [{ k: "note", l: "What needs correction?", t: "textarea", req: 1 }], {}, d => setS("In Progress", d.note), "Send back") }, "Send back"));
    if (isBoss() && a.status === "Approved") acts.push(h("button", { class: "btn sm", onclick: () => setS("Closed") }, "Close assignment"));
    const assignee = isBoss() ? h("select", { onchange: e => e.target.value && act(async () => { await post(`work/assignments/${id}/assign`, { user_id: e.target.value }); draw(); refresh && refresh(); }, "Reassigned") },
      h("option", { value: "" }, "Reassign…"), users.filter(u => u.role !== "ca" || true).map(u => h("option", { value: u.id }, u.name))) : "";
    const list = (items, kind) => items.map(i => h("div", {}, h("label", {}, h("input", { type: "checkbox", style: "width:auto", checked: !!(i.done || i.received), onchange: () => act(async () => { await post(`work/${kind}/${i.id}/toggle`); }) }), " ", i.item || i.name)));
    const add = (ph, path, key) => { const i = h("input", { placeholder: ph }); return h("div", { class: "row" }, i, h("button", { class: "btn sec sm", onclick: () => i.value && act(async () => { await post(path, { [key]: i.value }); draw(); }) }, "Add")); };
    const hookBox = h("div", {});
    box.replaceChildren(
      h("div", { class: "card" }, h("b", {}, a.title), " ", badge(a.status), a.overdue ? [" ", h("span", { class: "badge b-od" }, "Overdue")] : "", h("div", { class: "mut" }, `${a.client} · ${a.service || "—"} · Due ${a.due_date || "—"} · Priority ${a.priority} · Assigned to ${a.employee || "nobody"}`),
        a.remarks ? h("div", { class: "pre" }, "Remarks: " + a.remarks) : "", a.fee ? h("div", { class: "mut" }, "Fee: " + money(a.fee) + " (" + (a.fee_mode === "custom" ? "custom" : "as per fee master") + ")") : "",
        a.review_note ? h("div", { class: "pre" }, "Reviewer note: " + a.review_note) : "", h("div", { class: "row", style: "margin-top:10px" }, acts, assignee, isBoss() ? h("button", { class: "btn sec sm", onclick: () => formModal("Edit assignment", [{ k: "title", l: "Title", req: 1 }, { k: "due_date", l: "Due date", t: "date" }, { k: "priority", l: "Priority", t: "select", o: PRIO }, { k: "remarks", l: "Remarks", t: "textarea" }, { k: "fee_mode", l: "Fee", t: "select", o: [["default", "As per fee master"], ["custom", "Custom amount"]] }, { k: "fee", l: "Custom fee (₹) – used only if Custom" }], a, async d => { await put("work/assignments/" + id, d); draw(); refresh && refresh(); }) }, "Edit details") : "")),
      on("work", "checklists") ? h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "Checklist"), list(a.checklist, "checklist"), add("Add a step…", `work/assignments/${id}/checklist`, "item")) : "",
      on("work", "doc_tracking") ? h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "Documents required"), list(a.docs, "docs"), add("Add a required document…", `work/assignments/${id}/docs`, "name")) : "",
      hookBox,
      on("work", "comments") ? h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "Discussion"), a.comments.map(c => h("div", { class: "mut" }, h("b", {}, c.uname || "?"), " (" + c.created + "): ", c.body)), add("Write a comment…", `work/assignments/${id}/comments`, "body")) : "");
    for (const hk of WD.hooks.assignment) { try { await hk(a, hookBox, draw); } catch (e) { } }
  }; await draw();
}
WD.openAssignment = openAssignment;
/* New assignment: plain-English box (if AI module on), fee choice (default / custom), remarks */
async function newAssignment(done) {
  const [cl, sv, us] = await Promise.all([api("work/clients"), api("work/services"), api("admin/users")]);
  const F = {}; const sel = (k, rows, ph = "—") => F[k] = h("select", {}, h("option", { value: "" }, ph), rows.map(([v, l]) => h("option", { value: v }, l)));
  const fld = (l, e) => h("div", { class: "f" }, h("label", {}, l), e);
  const feeNote = h("div", { class: "mut" }, ""), nl = h("textarea", { placeholder: "Or just type it: Assign ABC Traders' GSTR-3B for October to Riya before 20 November, fee 1500", style: "min-height:52px" });
  sel("client_id", opt(cl), "Select client"); sel("service_id", opt(sv)); sel("priority", PRIO.map(x => x), "Normal"); sel("assigned_to", opt(us.filter(u => u.active)), "(unassigned)");
  F.title = h("input"); F.due_date = h("input", { type: "date" }); F.remarks = h("textarea", { placeholder: "Remarks / instructions for the employee", style: "min-height:60px" });
  F.fee_mode = h("select", {}, h("option", { value: "default" }, "Default fee (from fee master)"), h("option", { value: "custom" }, "Custom fee")); F.fee = h("input", { type: "number", placeholder: "Custom fee (₹)", style: "display:none" });
  const refreshFee = async () => { F.fee.style.display = F.fee_mode.value === "custom" ? "" : "none";
    if (F.fee_mode.value === "default" && F.client_id.value && F.service_id.value && on("finance", "fee_master")) { const r = await api(`finance/fee-suggest?client_id=${F.client_id.value}&service_id=${F.service_id.value}`); feeNote.textContent = "Fee as per fee master: " + money(r.fee); } else feeNote.textContent = ""; };
  [F.client_id, F.service_id, F.fee_mode].forEach(e => e.onchange = refreshFee);
  const body = h("div", {}, on("ai", "nl_task") ? h("div", { class: "card", style: "background:#f6f8ff" }, h("b", {}, "✨ Create from plain English"), nl, h("button", { class: "btn sec sm", style: "margin-top:6px", onclick: () => act(async () => {
      const p = await post("ai/parse-task", { text: nl.value }); if (p.client) F.client_id.value = p.client.id; if (p.service) F.service_id.value = p.service.id; if (p.employee) F.assigned_to.value = p.employee.id;
      if (p.due_date) F.due_date.value = p.due_date; if (p.title) F.title.value = p.title; refreshFee(); toast("Form filled – please check it"); }) }, "Fill the form from this text")) : "",
    fld("Client *", F.client_id), fld("Service", F.service_id), fld("Title *", F.title), fld("Due date", F.due_date), fld("Priority", F.priority), fld("Assign to", F.assigned_to),
    on("finance") ? fld("Fee", h("div", {}, F.fee_mode, F.fee, feeNote)) : "", fld("Remarks", F.remarks),
    h("button", { class: "btn", onclick: () => act(async () => { const d = {}; for (const k in F) d[k] = F[k].value; if (!d.client_id || !d.title) throw new Error("Client and title are required");
      await post("work/assignments", d); m.close(); toast("Assignment created"); done && done(); }) }, "Create assignment"));
  const m = modal("New assignment", body);
}
WD.newAssignment = newAssignment;
const GROUPS = [["status", "Status"], ["service", "Service"], ["employee", "Employee"], ["client", "Client"], ["month", "Due month"], ["source", "Compliance / Manual"]];
WD.mod("work", {
  nav: [{ id: "dash", l: "Dashboard", sub: "dashboard" }, { id: "assign", l: "Assignments", sub: "assignments" }, { id: "clients", l: "Clients", sub: "client_master", roles: ["ca", "manager"] }, { id: "services", l: "Services", sub: "service_master", roles: ["ca", "manager"] }],
  views: {
    async dash(el) {
      const d = await api("work/dashboard"), boss = isBoss();
      const grid = h("div", { class: "dgrid", id: "hk" });
      el.replaceChildren(h("h2", {}, boss ? "Dashboard" : "My dashboard"), grid);
      const open = (q) => () => { WD.assignPreset = q; go("work", "assign"); };
      grid.append(dbox(boss ? "📋 Work – whole firm" : "📋 My work", [
        h("div", { class: "kpis" }, kpi("Total", d.total), kpi("Pending", d.pending, "amb"), kpi("Closed", d.closed, "grn"), kpi("Overdue", d.overdue, d.overdue ? "red" : ""), kpi("Due in 7 days", d.due_week), kpi("In review", d.in_review), kpi("Awaiting docs", d.awaiting_docs)),
        boss && d.by_employee ? table([{ k: "name", l: "Employee" }, { k: "total", l: "Total" }, { k: "pending", l: "Pending" }, { k: "in_review", l: "In review" }, { k: "closed", l: "Closed" }, { l: "Overdue", f: r => r.overdue ? h("b", { style: "color:var(--bad)" }, r.overdue) : 0 }], d.by_employee) : "",
        h("button", { class: "btn sec sm", onclick: open({ by: "status" }) }, "Open assignments →")], { order: 2, wide: boss }));
      if (!boss) grid.append(dbox("🆕 New orders from CA (last 7 days)", d.new_orders.length ? table([{ l: "Due", f: r => r.due_date || "—" }, { k: "title", l: "Task" }, { k: "client", l: "Client" }], d.new_orders, r => openAssignment(r.id, () => go("work", "dash"))) : h("p", { class: "mut" }, "No new tasks right now."), { order: 3 }));
      grid.append(dbox("⏰ Next deadlines", table([{ l: "Due", f: r => r.due_date }, { l: "Assignment", k: "title" }, { l: "Client", k: "client" }, { l: "Status", f: r => badge(r.status) }].concat(boss ? [{ l: "Employee", k: "employee" }] : []), d.upcoming, r => openAssignment(r.id, () => go("work", "dash"))), { order: 9 }));
      for (const hk of WD.hooks.dashboard) { try { await hk(grid, d); } catch (e) { } }
    },
    async assign(el) {
      let by = "status", grp = null, sel = new Set(), preset = WD.assignPreset; WD.assignPreset = null; if (preset) by = preset.by;
      const bulk = (status, label) => act(async () => { const r = await post("work/assignments/bulk-status", { ids: [...sel], status }); toast(`${label}: ${r.done} done` + (r.skipped.length ? `, ${r.skipped.length} skipped (wrong status)` : ""), r.done === 0); sel.clear(); drawList(); }); 
      const drawGroups = async () => {
        const g = await api("work/assignments-groups?by=" + by);
        el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, isBoss() ? "Assignments" : "My assignments"), h("span", { class: "sp" }),
          h("button", { class: "btn sec", onclick: () => { grp = "*"; drawList(); } }, "Show full list"), isBoss() ? h("button", { class: "btn", onclick: () => newAssignment(drawGroups) }, "+ New assignment") : ""),
          h("div", { class: "tabs" }, h("span", { class: "mut", style: "padding:5px" }, "Group by:"), GROUPS.map(([k, l]) => h("button", { class: k === by ? "on" : "", onclick: () => { by = k; drawGroups(); } }, l))),
          h("div", { class: "grpcards" }, g.groups.map(x => h("div", { class: "gcard", onclick: () => { grp = x.grp; drawList(); } }, h("b", {}, x.grp), h("span", { class: "n" }, x.total),
            h("div", { class: "m" }, `${x.pending} pending · ${x.done} closed`), h("div", { class: "m" }, `${x.in_review} in review · ${x.awaiting} awaiting docs`), x.overdue ? h("div", { class: "m", style: "color:var(--bad)" }, x.overdue + " overdue") : ""))));
      };
      const drawList = async () => {
        let q = grp === "*" ? "" : by === "status" ? "status=" + encodeURIComponent(grp) : `by=${by}&grp=${encodeURIComponent(grp)}`;
        const rows = await api("work/assignments?" + q); const boss = isBoss();
        const chk = r => h("input", { type: "checkbox", style: "width:auto", checked: sel.has(r.id), onchange: e => { e.target.checked ? sel.add(r.id) : sel.delete(r.id); bar(); } });
        const all = h("input", { type: "checkbox", style: "width:auto", onchange: e => { rows.forEach(r => e.target.checked ? sel.add(r.id) : sel.delete(r.id)); drawList(); } });
        const barBox = h("div", {}); const bar = () => barBox.replaceChildren(sel.size ? h("div", { class: "bulkbar" }, h("b", {}, sel.size + " selected"), h("span", { class: "sp" }),
          h("button", { class: "btn sm", onclick: () => bulk("In Review", "Submitted for review") }, "Submit for review"),
          boss ? [h("button", { class: "btn sm ok", onclick: () => bulk("Approved", "Approved") }, "Approve"), h("button", { class: "btn sm ok", onclick: () => confirm("Approve and close the selected assignments? Invoices are created automatically.") && bulk("Closed", "Closed") }, "Approve & close"), h("button", { class: "btn sm bad", onclick: () => formModal("Send back", [{ k: "note", l: "What needs correction?", t: "textarea", req: 1 }], {}, async d => { const r = await post("work/assignments/bulk-status", { ids: [...sel], status: "In Progress", note: d.note }); toast(r.done + " sent back"); sel.clear(); drawList(); }, "Send back") }, "Send back")] : "",
          h("button", { class: "btn sec sm", onclick: () => { sel.clear(); drawList(); } }, "Clear")) : ""); bar();
        el.replaceChildren(h("div", { class: "row" }, h("button", { class: "btn sec sm", onclick: () => { grp = null; sel.clear(); drawGroups(); } }, "← All groups"), h("h2", { style: "margin:0" }, grp === "*" ? "All assignments" : by === "status" ? grp : GROUPS.find(x => x[0] === by)[1] + ": " + grp), h("span", { class: "sp" }), h("span", { class: "mut" }, rows.length + " assignment(s)"), boss ? h("button", { class: "btn", onclick: () => newAssignment(drawList) }, "+ New") : ""),
          table([{ l: all, f: chk }, { l: "Due", f: r => [r.due_date || "—", r.overdue ? h("span", { class: "badge b-od" }, "Overdue") : ""] }, { l: "Assignment", k: "title" }, { l: "Client", k: "client" }, { l: "Status", f: r => badge(r.status) }, { l: "Employee", f: r => r.employee || "—" }, { l: "Fee", f: r => r.fee ? money(r.fee) : "" }], rows, r => openAssignment(r.id, drawList)), barBox);
      };
      if (preset && preset.grp) { grp = preset.grp; drawList(); } else drawGroups();
    },
    async clients(el) {
      const F = [{ k: "name", l: "Client name", req: 1 }, { k: "ctype", l: "Type", t: "select", o: ["Company", "Partnership", "Proprietorship", "Trust", "Individual", "HUF"].map(x => [x, x]) }, { k: "pan", l: "PAN" }, { k: "gstin", l: "GSTIN" }, { k: "email", l: "E-mail (used for document requests)" }, { k: "phone", l: "Phone" }, { k: "address", l: "Address", t: "textarea" }, { k: "active", l: "Active", t: "checkbox", d: 1 }];
      crud(el, { title: "Clients", load: () => api("work/clients"), fields: F, save: (d, r) => r ? put("work/clients/" + r.id, d) : post("work/clients", d), extra: () => on("admin", "csv_tools") && isCA() ? h("button", { class: "btn sec", onclick: () => go("admin", "import") }, "Bulk import (CSV)") : "", cols: [{ k: "name", l: "Name" }, { k: "ctype", l: "Type" }, { k: "pan", l: "PAN" }, { k: "gstin", l: "GSTIN" }, { k: "email", l: "E-mail" }, { l: "Active", f: r => r.active ? "Yes" : "No" }] });
    },
    async services(el) {
      crud(el, { title: "Services", load: () => api("work/services"), fields: [{ k: "name", l: "Service", req: 1 }, { k: "category", l: "Category" }, { k: "default_fee", l: "Default fee (₹)", t: "number" }], save: (d, r) => r ? put("work/services/" + r.id, d) : post("work/services", d), cols: [{ k: "name", l: "Service" }, { k: "category", l: "Category" }, { l: "Default fee", f: r => money(r.default_fee) }] });
    }
  }
});
