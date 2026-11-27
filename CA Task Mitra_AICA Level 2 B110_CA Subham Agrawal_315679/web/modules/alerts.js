WD.mod("alerts", {
  nav: [{ id: "rules", l: "Alert rules", sub: "rules", roles: ["ca", "manager"] }, { id: "log", l: "Alert log", sub: "log", roles: ["ca", "manager"] }],
  views: {
    async rules(el) {
      const co = await api("compliance/master").catch(() => []);
      crud(el, { title: "Alert rules", load: () => api("alerts/rules"), fields: [{ k: "name", l: "Rule name", req: 1 }, { k: "compliance_id", l: "Compliance", t: "select", o: co.map(c => [c.id, c.code + " – " + c.name]), req: 1 }, { k: "offsets", l: "Days relative to due date (e.g. -2,0,1 = 2 days before, on due date, 1 day after)" }, { k: "send_hour", l: "Send after hour (0-23)", t: "number" }, { k: "recipient", l: "Send to (blank = CA alert e-mail in settings)" }, { k: "active", l: "Active", t: "checkbox", d: 1 }],
        save: (d, r) => r ? put("alerts/rules/" + r.id, d) : post("alerts/rules", d),
        cols: [{ k: "name", l: "Rule" }, { k: "code", l: "Compliance" }, { k: "offsets", l: "Offsets" }, { k: "send_hour", l: "Hour" }, { l: "Active", f: r => r.active ? "Yes" : "No" }, { l: "", f: r => h("button", { class: "btn sec sm", onclick: e => { e.stopPropagation(); act(async () => { const x = await post(`alerts/rules/${r.id}/run`); toast(`${x.count} pending · ${x.channel || "-"} · ${x.message || ""}`); }); } }, "Send test now") }] });
    },
    async log(el) { const rows = await api("alerts/log"); el.replaceChildren(h("h2", {}, "Alert log"), table([{ k: "created", l: "Time" }, { k: "rule", l: "Rule" }, { k: "run_date", l: "Date" }, { k: "count", l: "Pending" }, { k: "channel", l: "Channel" }, { l: "Status", f: r => badge(r.status) }, { k: "message", l: "Message" }], rows)); }
  }
});
