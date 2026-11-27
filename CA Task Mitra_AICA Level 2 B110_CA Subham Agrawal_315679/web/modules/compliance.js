const FREQ = [["monthly", "Monthly"], ["quarterly", "Quarterly"], ["annual", "Annual"]];
WD.mod("compliance", {
  nav: [{ id: "gen", l: "Generate work", sub: "generator", roles: ["ca", "manager"] }, { id: "cal", l: "Calendar", sub: "calendar" }, { id: "appl", l: "Applicability", sub: "applicability", roles: ["ca", "manager"] },
    { id: "master", l: "Compliance master", sub: "master", roles: ["ca", "manager"] }, { id: "ext", l: "Due-date extension", sub: "extension", roles: ["ca", "manager"] }, { id: "notice", l: "Notices", sub: "notices", roles: ["ca", "manager"] }],
  views: {
    async gen(el) {
      const f = h("select", {}, FREQ.map(([v, l]) => h("option", { value: v }, l))), p = h("input", { value: new Date().toISOString().slice(0, 7) }), out = h("div", {});
      f.onchange = () => p.value = { monthly: new Date().toISOString().slice(0, 7), quarterly: new Date().getFullYear() + "-Q" + (Math.floor(new Date().getMonth() / 3) + 1), annual: String(new Date().getFullYear() - 1) }[f.value];
      el.replaceChildren(h("h2", {}, "Generate assignments from compliance"), h("div", { class: "card" }, h("p", { class: "mut" }, "Creates one assignment per client for every applicable compliance, with the due date from the master and any extension. Running it again never creates duplicates."),
        h("div", { class: "f" }, h("label", {}, "Frequency"), f), h("div", { class: "f" }, h("label", {}, "Period – monthly 2026-10 · quarterly 2026-Q2 · annual = financial-year start year e.g. 2025 for FY 2025-26"), p),
        h("button", { class: "btn", onclick: () => act(async () => { const r = await post("compliance/generate", { freq: f.value, period: p.value }); out.replaceChildren(h("div", { class: "card" }, `Created ${r.created} assignment(s); ${r.skipped_duplicates} already existed.`)); }) }, "Generate"), out),
        h("div", { class: "hint" }, "Statutory due dates are configurable in the Compliance master and must be verified by the CA against current notifications."));
    },
    async cal(el) {
      const mth = h("input", { type: "month", style: "width:auto", value: WD.calMonth || new Date().toISOString().slice(0, 7) });
      const draw = async () => { WD.calMonth = mth.value; const rows = await api("compliance/calendar?month=" + mth.value);
        const by = {}; rows.forEach(r => (by[r.due_date] = by[r.due_date] || []).push(r));
        el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, isBoss() ? "Compliance calendar" : "My compliance calendar (only your work)"), h("span", { class: "sp" }), mth),
          Object.keys(by).length ? Object.entries(by).map(([d, items]) => h("div", { class: "card" }, h("b", {}, d), " ", h("span", { class: "mut" }, items.length + " due"), items.map(i => h("div", {}, `${i.client} – ${i.title} `, badge(i.status), " ", h("span", { class: "mut" }, i.employee || "")))) ) : h("p", { class: "mut" }, "No compliance work due this month."));
        mth.onchange = draw; }; await draw();
    },
    async appl(el) {
      const draw = async () => { const [rows, cl, co, us] = await Promise.all([api("compliance/applicability"), api("work/clients"), api("compliance/master"), api("admin/users")]);
        const imp = () => { const f = h("input", { type: "file", accept: ".csv" }); const out = h("div", {});
          modal("Import applicability from CSV", h("div", {}, h("p", { class: "mut" }, "Columns: client, compliance, employee. Client names must match the Clients list; compliance is the code, e.g. GSTR-3B; employee is a username or name (optional)."),
            h("a", { href: "/api/admin/import-template/applicability", class: "btn sec sm", style: "text-decoration:none" }, "Download template"), h("div", { class: "f", style: "margin-top:10px" }, f),
            h("button", { class: "btn", onclick: () => f.files[0] ? act(async () => { const r = await post("compliance/applicability/import", { csv: await readCsv(f.files[0]) }); out.replaceChildren(h("div", { class: "card" }, r.imported + " row(s) imported.", r.errors.map(e => h("div", { class: "mut" }, e)))); draw(); }) : toast("Choose a CSV file first", true) }, "Import"), out)); };
        el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, "Which compliance applies to which client"), h("span", { class: "sp" }), h("button", { class: "btn sec", onclick: imp }, "Import CSV"),
          h("button", { class: "btn", onclick: () => { const picks = h("div", { style: "max-height:200px;overflow:auto;border:1px solid #ddd;padding:6px;border-radius:7px" }, cl.map(c => h("label", { style: "display:block" }, h("input", { type: "checkbox", style: "width:auto", value: c.id }), " " + c.name)));
            const sel = h("select", {}, co.map(c => h("option", { value: c.id }, c.code + " – " + c.name))), emp = h("select", {}, h("option", { value: "" }, "(none)"), us.filter(u => u.role === "employee").map(u => h("option", { value: u.id }, u.name)));
            modal("Add applicability", h("div", {}, h("div", { class: "f" }, h("label", {}, "Compliance"), sel), h("div", { class: "f" }, h("label", {}, "Default employee"), emp), h("div", { class: "f" }, h("label", {}, "Clients"), picks),
              h("button", { class: "btn", onclick: () => act(async () => { await post("compliance/applicability", { compliance_id: sel.value, default_employee: emp.value, client_ids: [...picks.querySelectorAll("input:checked")].map(i => i.value) }); document.querySelector(".modal").remove(); draw(); }, "Added") }, "Add"))); } }, "+ Add")),
          table([{ k: "client", l: "Client" }, { k: "code", l: "Compliance" }, { k: "freq", l: "Frequency" }, { l: "Default employee", f: r => r.employee || "—" }, { l: "", f: r => h("button", { class: "btn sec sm", onclick: () => act(async () => { await api("compliance/applicability/" + r.id, { method: "DELETE" }); draw(); }) }, "Remove") }], rows)); }; await draw();
    },
    async master(el) {
      const sv = await api("work/services").catch(() => []);
      crud(el, { title: "Compliance master", load: () => api("compliance/master"), fields: [{ k: "code", l: "Code", req: 1 }, { k: "name", l: "Name", req: 1 }, { k: "category", l: "Category" }, { k: "freq", l: "Frequency", t: "select", o: FREQ, req: 1 }, { k: "due_day", l: "Due day of month", t: "number", req: 1 }, { k: "due_month", l: "Due month (annual only, 1-12)", t: "number" }, { k: "offset", l: "Months after period end (monthly/quarterly) or years after FY end (annual)", t: "number" }, { k: "service_id", l: "Linked service", t: "select", o: opt(sv) }, { k: "active", l: "Active", t: "checkbox", d: 1 }],
        save: (d, r) => r ? put("compliance/master/" + r.id, d) : post("compliance/master", d), cols: [{ k: "code", l: "Code" }, { k: "name", l: "Name" }, { k: "freq", l: "Frequency" }, { l: "Due", f: r => `day ${r.due_day}` + (r.due_month ? ` of month ${r.due_month}` : "") + `, +${r.offset}` }, { l: "Service", f: r => r.service || "—" }] });
    },
    async ext(el) {
      const draw = async () => { const [rows, co] = await Promise.all([api("compliance/extensions"), api("compliance/master")]);
        el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, "Due-date extensions"), h("span", { class: "sp" }),
          h("button", { class: "btn", onclick: () => formModal("Extend due date", [{ k: "compliance_id", l: "Compliance", t: "select", o: co.map(c => [c.id, c.code]), req: 1 }, { k: "period", l: "Period (e.g. 2026-10)", req: 1 }, { k: "new_due", l: "New due date", t: "date", req: 1 }, { k: "reason", l: "Reason / notification" }], {}, async d => { const r = await post("compliance/extensions", d); toast(r.assignments_updated + " open assignment(s) updated"); draw(); }) }, "+ Extend")),
          table([{ k: "code", l: "Compliance" }, { k: "period", l: "Period" }, { k: "new_due", l: "New due date" }, { k: "reason", l: "Reason" }], rows)); }; await draw();
    },
    async notice(el) {
      const cl = await api("work/clients");
      crud(el, { title: "Notices", load: () => api("compliance/notices"), fields: [{ k: "client_id", l: "Client", t: "select", o: opt(cl) }, { k: "notice_type", l: "Notice type", req: 1 }, { k: "ref_no", l: "Reference no." }, { k: "received_on", l: "Received on", t: "date" }, { k: "reply_due", l: "Reply due", t: "date" }, { k: "status", l: "Status", t: "select", o: [["Open", "Open"], ["Replied", "Replied"], ["Closed", "Closed"]] }, { k: "note", l: "Note", t: "textarea" }],
        save: (d, r) => r ? put("compliance/notices/" + r.id, d) : post("compliance/notices", d), cols: [{ k: "client", l: "Client" }, { k: "notice_type", l: "Notice" }, { k: "ref_no", l: "Ref" }, { k: "reply_due", l: "Reply due" }, { l: "Status", f: r => badge(r.status) }] });
    }
  }
});

WD.hooks.dashboard.push(async (grid) => {
  if (!on("compliance", "calendar")) return;
  const rows = await api("compliance/calendar?days=10"); const today = new Date().toISOString().slice(0, 10);
  const by = {}; rows.forEach(r => (by[r.due_date] = by[r.due_date] || []).push(r));
  grid.append(dbox(isBoss() ? "📅 Compliance calendar – next 10 days" : "📅 My compliance dates", Object.keys(by).length ? Object.entries(by).slice(0, 6).map(([d, it]) => h("div", { style: "margin-bottom:6px" }, h("b", { style: d < today ? "color:var(--bad)" : "" }, d + (d < today ? " (overdue)" : "")), " · ", it.length + " due",
    h("div", { class: "mut" }, [...new Set(it.map(i => i.title.split(" – ")[0]))].slice(0, 3).join(", ") + " – " + it.slice(0, 3).map(i => i.client).join(", ") + (it.length > 3 ? " +" + (it.length - 3) + " more" : "")))) : h("p", { class: "mut" }, "Nothing due in the next 10 days."),
    { order: 5, right: h("button", { class: "btn sec sm", onclick: () => go("compliance", "cal") }, "Full calendar") }));
});
