const SET = [["firm_name", "Firm name"], ["gst_rate", "Default GST rate %"], ["ca_alert_email", "CA e-mail for alerts"], ["login_hint", "Login-screen hint (clear this in real use)"],
  ["smtp_host", "SMTP host (blank = simulated sending)"], ["smtp_port", "SMTP port"], ["smtp_user", "SMTP user / firm mailbox"], ["smtp_pass", "SMTP password / app password", "password"], ["smtp_from", "From address"],
  ["n8n_webhook_url", "n8n webhook URL"], ["tally_url", "Tally URL (default http://localhost:9000)"], ["tally_auto_post", "Auto-post to Tally when billing (1 = yes, 0 = no)"], ["tally_company", "Tally company name"], ["tally_fee_ledger", "Tally fee ledger"], ["tally_gst_ledger", "Tally GST ledger"], ["tally_bank_ledger", "Tally bank ledger"],
  ["ai_provider", "AI provider note (claude / chatgpt)"], ["openai_key", "OpenAI API key (optional)", "password"], ["openai_model", "OpenAI model (optional)"]];
WD.mod("admin", {
  nav: [{ id: "modules", l: "Module manager", sub: "module_manager", roles: ["ca"] }, { id: "users", l: "Users & logins", sub: "users", roles: ["ca"] }, { id: "import", l: "Bulk import (new office)", sub: "csv_tools", roles: ["ca", "manager"] }, { id: "settings", l: "Firm settings", sub: "firm_settings", roles: ["ca"] },
    { id: "audit", l: "Audit trail", sub: "audit_log", roles: ["ca", "manager"] }, { id: "data", l: "Backup, demo & CSV", sub: "backup", roles: ["ca"] }],
  views: {
    async modules(el) {
      const draw = async () => { const mods = await api("admin/modules");
        const tg = (checked, disabled, fn) => { const i = h("input", { type: "checkbox", checked, disabled, onchange: async e => { try { await fn(e.target.checked); toast("Saved – reloading menu"); setTimeout(() => location.reload(), 600); } catch (x) { toast(x.message, true); e.target.checked = !e.target.checked; } } }); return h("label", { class: "sw" }, i, h("i")); };
        el.replaceChildren(h("h2", {}, "Module manager"), h("p", { class: "mut" }, "Switch whole modules or single features on and off. Planned modules are already registered and will plug in here when they are built."),
          mods.map(m => h("div", { class: "mod" }, h("div", { class: "h" }, tg(m.enabled, m.core || m.status !== "ready", v => post(`admin/modules/${m.key}/toggle`, { enabled: v })), h("div", { class: "sp" }, h("b", {}, m.name), m.core ? " (core)" : "", m.status !== "ready" ? [" ", h("span", { class: "soon" }, "coming soon")] : "", h("div", { class: "mut" }, m.desc), m.requires.length ? h("div", { class: "mut" }, "Needs: " + m.requires.join(", ")) : "")),
            h("div", { class: "subs" }, m.subs.map(s => h("div", { class: "s" }, h("span", {}, s.name, s.status !== "ready" ? [" ", h("span", { class: "soon" }, "planned")] : ""), tg(s.enabled, !m.enabled || s.status !== "ready" || (m.key === "admin" && s.key === "module_manager"), v => post(`admin/modules/${m.key}/subs/${s.key}/toggle`, { enabled: v }))))))));
      }; await draw();
    },
    async users(el) {
      const gen = () => { const c = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"; return Array.from(crypto.getRandomValues(new Uint32Array(10)), n => c[n % c.length]).join("") + "@1"; };
      const F = [{ k: "username", l: "Login username (cannot change later)", req: 1 }, { k: "name", l: "Full name", req: 1 }, { k: "role", l: "Role", t: "select", o: [["employee", "Employee"], ["manager", "Manager"], ["ca", "CA / Admin"]] }, { k: "designation", l: "Designation" }, { k: "email", l: "E-mail" }, { k: "phone", l: "Phone" }, { k: "password", l: "Password (blank = unchanged when editing)", t: "text" }, { k: "active", l: "Active", t: "checkbox", d: 1 }];
      const draw = async () => { const rows = await api("admin/users");
        const open = (r) => { const m = formModal(r ? "Edit login – " + r.username : "Create employee login", F, r || { role: "employee", password: gen() }, async d => { if (!r && (d.password || "").length < 6) throw new Error("Password needs 6+ characters"); await (r ? put("admin/users/" + r.id, d) : post("admin/users", d)); if (d.password) toast("Share with the employee – username: " + d.username + "  password: " + d.password); draw(); });
          const pw = m.querySelector("input[type=text]:last-of-type"); m.querySelector(".box").append(h("button", { class: "btn sec sm", style: "margin-left:8px", onclick: e => { const pws = [...m.querySelectorAll("input")].find(i => i.value === "" || i.closest(".f").textContent.startsWith("Password")); const f = [...m.querySelectorAll(".f")].find(x => x.textContent.startsWith("Password")).querySelector("input"); f.value = gen(); } }, "Generate password")); };
        el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, "Users & logins"), h("span", { class: "sp" }), h("button", { class: "btn", onclick: () => open() }, "+ Create employee login")),
          h("p", { class: "mut" }, "Only the CA can create logins and set or reset passwords. Employees can change their own password after signing in."),
          table([{ k: "username", l: "Username" }, { k: "name", l: "Name" }, { k: "role", l: "Role" }, { k: "designation", l: "Designation" }, { l: "Active", f: r => r.active ? "Yes" : "No" }, { l: "", f: r => h("button", { class: "btn sec sm", onclick: () => open(r) }, "Edit / reset password") }], rows)); }; await draw();
    },
    async import(el) {
      const KINDS = [["clients", "Clients", "name, ctype, pan, gstin, email, phone, address"], ["employees", "Employees (logins)", "username, name, role, designation, email, phone, password – CA only"], ["assignments", "Pending / open assignments", "client, service, title, due_date, status, employee, fee, remarks"], ["applicability", "Compliance applicability", "client, compliance (code), employee"]];
      el.replaceChildren(h("h2", {}, "Bulk import – set up a new office quickly"), h("p", { class: "mut" }, "Do the steps in this order: 1 Clients → 2 Employees → 3 Assignments → 4 Applicability. For each: download the template, fill it in Excel, save as CSV, upload. Rows with problems are skipped and listed."),
        KINDS.map(([k, l, cols], n) => { const f = h("input", { type: "file", accept: ".csv" }), out = h("div", {});
          if (k === "employees" && !isCA()) return ""; if (k === "applicability" && !on("compliance", "applicability")) return "";
          return h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, `${n + 1}. ${l}`), h("div", { class: "mut" }, "Columns: " + cols),
            h("div", { class: "row", style: "margin-top:8px" }, h("a", { class: "btn sec sm", href: "/api/admin/import-template/" + k, style: "text-decoration:none" }, "Download template"), f,
              h("button", { class: "btn sm", onclick: () => f.files[0] ? act(async () => { const r = await post(k === "applicability" ? "compliance/applicability/import" : "admin/import/" + k, { csv: await readCsv(f.files[0]) }); out.replaceChildren(h("div", { class: r.errors.length ? "hint" : "mut" }, r.imported + " row(s) imported.", r.errors.map(e => h("div", {}, e)))); }) : toast("Choose a CSV file first", true) }, "Upload & import")), out); }));
    },
    async settings(el) {
      const s = await api("admin/settings"), inp = {};
      el.replaceChildren(h("h2", {}, "Firm settings & integrations"), h("div", { class: "card" }, SET.map(([k, l, t]) => h("div", { class: "f" }, h("label", {}, l), inp[k] = h("input", { type: t || "text", value: s[k] || "" }))),
        h("button", { class: "btn", onclick: () => act(async () => { const d = {}; for (const k in inp) d[k] = inp[k].value; await put("admin/settings", d); }, "Settings saved") }, "Save settings")),
        h("div", { class: "hint" }, "Leave SMTP blank to demonstrate: approved e-mails are saved as .eml files in the data/outbox folder instead of being sent."));
    },
    async audit(el) { const rows = await api("admin/audit?limit=300"); el.replaceChildren(h("h2", {}, "Audit trail – who did what"), table([{ k: "ts", l: "When" }, { k: "user", l: "User" }, { k: "action", l: "Action" }, { k: "detail", l: "Details" }], rows)); },
    async data(el) {
      const draw = async () => { const bk = await api("admin/backups"); const file = h("input", { type: "file", accept: ".csv" });
        el.replaceChildren(h("h2", {}, "Backup, demo data and CSV"),
          h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "Backup"), h("button", { class: "btn", onclick: () => act(async () => { await post("admin/backups"); draw(); }, "Backup created") }, "Create backup now"), bk.length ? table([{ k: "name", l: "File (in data/backups)" }, { k: "kb", l: "KB" }, { l: "", f: r => h("a", { href: "/api/admin/backups/" + r.name }, "Download") }], bk) : ""),
          on("admin", "csv_tools") ? h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "CSV (opens in Excel)"), h("div", { class: "row" }, ["clients", "assignments", "invoices", "audit"].map(n => h("a", { class: "btn sec sm", href: "/api/admin/export/" + n, style: "text-decoration:none" }, "Export " + n))),
            h("div", { class: "f" }, h("label", {}, "Import clients – CSV with header: name,pan,gstin,email,phone,ctype"), file), h("button", { class: "btn sec", onclick: () => file.files[0] && file.files[0].text().then(t => act(async () => { const r = await post("admin/import/clients", { csv: t }); toast(r.imported + " clients imported"); })) }, "Import")) : "",
          on("admin", "demo_data") ? h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "Demo data (fictional)"), h("p", { class: "mut" }, "Reset wipes ALL business data and reloads the fictional demo office. Use only for demonstrations."),
            h("button", { class: "btn bad", onclick: () => confirm("This deletes all data and reloads demo data. Continue?") && act(async () => { await post("admin/demo/reset", { confirm: true }); setTimeout(() => location.reload(), 500); }, "Demo reset") }, "Reset to demo data"), " ", h("button", { class: "btn sec", onclick: () => act(async () => { await post("admin/demo/load"); }, "Demo data loaded") }, "Load demo data (empty office only)")) : "");
      }; await draw();
    }
  }
});
