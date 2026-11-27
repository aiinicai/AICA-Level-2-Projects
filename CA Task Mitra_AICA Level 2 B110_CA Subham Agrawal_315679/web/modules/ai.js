WD.mod("ai", {
  nav: [{ id: "brief", l: "Morning briefing", sub: "briefing" }, { id: "nl", l: "Create task in plain English", sub: "nl_task", roles: ["ca", "manager"] }],
  views: {
    async brief(el) {
      const b = await api("ai/briefing");
      el.replaceChildren(h("h2", {}, "Morning briefing"), h("div", { class: "card" }, h("p", { style: "font-size:15px" }, b.text), h("div", { class: "mut" }, b.ai_polished ? "Wording by OpenAI. Numbers come from your own data." : "Generated from your data. Add an OpenAI key in Firm settings to polish the wording.")),
        h("div", { class: "grid" }, stat("Overdue", b.stats.overdue), stat("Due in 3 days", b.stats.due_3_days), stat("Awaiting documents", b.stats.awaiting_docs), stat("In review", b.stats.in_review)),
        h("h3", {}, "Most urgent"), table([{ k: "due_date", l: "Due" }, { k: "client", l: "Client" }, { k: "title", l: "Task" }, { k: "who", l: "With" }], b.urgent));
    },
    async nl(el) {
      const t = h("textarea", { placeholder: "Example: Assign ABC Traders' October GST return to Riya before 20 November" }), out = h("div", {});
      el.replaceChildren(h("h2", {}, "Create a task in plain English"), h("div", { class: "card" }, t, h("div", { class: "row", style: "margin-top:8px" }, h("button", { class: "btn", onclick: () => act(async () => {
        const p = await post("ai/parse-task", { text: t.value }); const [cl, us, sv] = await Promise.all([api("work/clients"), api("admin/users"), api("work/services")]);
        const f = { client_id: p.client?.id, assigned_to: p.employee?.id, due_date: p.due_date, service_id: p.service?.id, title: p.title };
        out.replaceChildren(h("div", { class: "card" }, h("b", {}, "Please confirm – AI suggestions are never saved automatically"), h("p", { class: "mut" }, `Client: ${p.client?.name || "not found"} · Employee: ${p.employee?.name || "not found"} · Due: ${p.due_date || "not found"} · Service: ${p.service?.name || "not found"}`),
          h("button", { class: "btn ok", onclick: () => formModal("Confirm task", [{ k: "client_id", l: "Client", t: "select", o: opt(cl), req: 1 }, { k: "title", l: "Title", req: 1 }, { k: "service_id", l: "Service", t: "select", o: opt(sv) }, { k: "due_date", l: "Due date", t: "date" }, { k: "assigned_to", l: "Employee", t: "select", o: opt(us) }], f, async d => { await post("ai/create-task", d); toast("Task created"); }, "Create task") }, "Review & create")));
      }) }, "Understand"))), out);
    }
  }
});
WD.hooks.dashboard.push(async (grid) => { if (!on("ai", "briefing")) return; const b = await api("ai/briefing"); grid.append(dbox("☀️ Morning briefing", h("p", { style: "margin:0;font-size:14px" }, b.text), { wide: true, order: 1 })); });
WD.hooks.assignment.push(async (a, box, redraw) => {
  if (!on("ai", "checklist_ai") || ["Approved", "Closed"].includes(a.status)) return;
  box.append(h("div", { class: "card" }, h("b", {}, "AI suggestions "), h("button", { class: "btn sec sm", onclick: () => act(async () => {
    const r = await post("ai/checklist-suggest", { assignment_id: a.id }); const boxes = h("div", {}, r.items.map(i => h("label", { style: "display:block" }, h("input", { type: "checkbox", style: "width:auto", checked: true, value: i }), " " + i)));
    const m = modal("Suggested checklist (" + (r.ai_generated ? "OpenAI" : "built-in rules") + ")", h("div", {}, boxes, h("button", { class: "btn", onclick: () => act(async () => { await post(`work/assignments/${a.id}/checklist`, { items: [...boxes.querySelectorAll("input:checked")].map(i => i.value) }); m.close(); redraw(); }, "Added to checklist") }, "Add selected")));
  }) }, "Suggest checklist")));
});
