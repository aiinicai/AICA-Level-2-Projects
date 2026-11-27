WD.mod("comms", {
  nav: [{ id: "ann", l: "Announcements", sub: "announcements" }, { id: "queue", l: "E-mail drafts & approval", sub: "drafts" }],
  views: {
    async ann(el) {
      const draw = async () => { const rows = await api("comms/announcements"), us = isBoss() ? await api("admin/users") : [];
        const F = [{ k: "title", l: "Title", req: 1 }, { k: "body", l: "Message", t: "textarea" }, { k: "to_user", l: "To (blank = whole firm)", t: "select", o: opt(us.filter(u => u.active && u.role !== "ca")) }, { k: "pinned", l: "Pin to top", t: "checkbox" }];
        el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, "Announcements & messages"), h("span", { class: "sp" }), isBoss() ? h("button", { class: "btn", onclick: () => formModal("New announcement / message", F, {}, async d => { await post("comms/announcements", d); draw(); }, "Publish") }, "+ New") : ""),
          rows.length ? rows.map(r => h("div", { class: "card", style: r.seen || isBoss() ? "" : "border-left:4px solid var(--pri)" }, h("b", {}, (r.pinned ? "📌 " : "") + r.title), " ", r.to_user ? h("span", { class: "badge b-Pending" }, "To " + r.to_name) : h("span", { class: "badge" }, "Whole firm"),
            h("div", { class: "mut" }, r.author + " · " + r.created), h("p", { style: "white-space:pre-wrap;margin:6px 0" }, r.body || ""),
            !isBoss() && !r.seen ? h("button", { class: "btn sec sm", onclick: () => act(async () => { await post(`comms/announcements/${r.id}/seen`); draw(); }) }, "Mark as read") : "",
            isBoss() ? h("button", { class: "btn sec sm", onclick: () => confirm("Delete this announcement?") && act(async () => { await post(`comms/announcements/${r.id}/delete`); draw(); }) }, "Delete") : "")) : h("p", { class: "mut" }, "No announcements yet.")); }; await draw();
    },
    async queue(el) {
      const draw = async () => { const rows = await api("comms/drafts");
        const send = r => act(async () => { const x = await post(`comms/drafts/${r.id}/approve`); draw(); toast("E-mail " + x.status + " – " + x.result); });
        el.replaceChildren(h("h2", {}, isBoss() ? "E-mail drafts – approval queue" : "My e-mail drafts"), h("p", { class: "mut" }, "Employees draft; nothing leaves the office until the CA or manager approves and sends it from here."),
          table([{ k: "created", l: "Created" }, { k: "client", l: "Client" }, { k: "subject", l: "Subject" }, { k: "author", l: "Drafted by" }, { l: "Status", f: r => badge(r.status) }, { l: "Result", f: r => r.result || "" },
            { l: "", f: r => isBoss() && ["Draft", "Failed"].includes(r.status) ? h("span", {}, h("button", { class: "btn sm ok", onclick: () => send(r) }, "Approve & send"), " ", h("button", { class: "btn sec sm", onclick: () => formModal("Edit draft", [{ k: "to_email", l: "To", req: 1 }, { k: "subject", l: "Subject", req: 1 }, { k: "body", l: "Message", t: "textarea" }], r, async d => { await put("comms/drafts/" + r.id, d); draw(); }) }, "Edit"), " ", h("button", { class: "btn sec sm", onclick: () => act(async () => { await post(`comms/drafts/${r.id}/reject`); draw(); }) }, "Reject")) : "" }], rows, r => modal("Draft e-mail", h("div", {}, h("div", { class: "mut" }, "To: " + (r.to_email || "(no e-mail on client)")), h("b", {}, r.subject), h("div", { class: "pre" }, r.body)), { wide: true }))); }; await draw();
    }
  }
});
WD.hooks.dashboard.push(async (grid) => {
  if (on("comms", "drafts")) {
    const d = await api("comms/drafts"), cnt = st => d.filter(x => x.status === st).length;
    grid.append(dbox("✉️ E-mails", [h("div", { class: "kpis" }, isBoss() ? kpi("Pending approval", cnt("Draft"), cnt("Draft") ? "amb" : "") : kpi("My drafts waiting", cnt("Draft"), cnt("Draft") ? "amb" : ""), kpi("Sent", cnt("Sent"), "grn"), kpi("Failed", cnt("Failed"), cnt("Failed") ? "red" : "")),
      isBoss() && cnt("Draft") ? h("button", { class: "btn sm", onclick: () => go("comms", "queue") }, "Review & approve") : ""], { order: 6 }));
  }
  if (on("comms", "announcements")) {
    const a = (await api("comms/announcements")).slice(0, 4);
    grid.append(dbox("📢 Announcements", a.length ? a.map(r => h("div", { style: "margin-bottom:8px" }, h("b", {}, (r.pinned ? "📌 " : "") + r.title), r.to_user ? [" ", h("span", { class: "badge b-Pending" }, "for " + (isBoss() ? r.to_name : "you"))] : "", h("div", { class: "mut" }, (r.body || "").slice(0, 110) + " · " + r.created.slice(0, 10)))) : h("p", { class: "mut" }, "No announcements."),
      { order: 7, right: h("button", { class: "btn sec sm", onclick: () => go("comms", "ann") }, isBoss() ? "Post / view all" : "View all") }));
  }
});
WD.hooks.assignment.push(async (a, box, redraw) => {
  if (!on("comms", "drafts") || a.status === "Approved" || a.status === "Closed") return;
  box.append(h("div", { class: "card" }, h("b", {}, "Client documents "), h("button", { class: "btn sm bad", onclick: () => {
    const pre = a.docs.filter(d => !d.received).map(d => d.name).join("\n");
    formModal("Documents insufficient – draft e-mail to client", [{ k: "docs", l: "Missing documents (one per line)", t: "textarea", req: 1 }, { k: "note", l: "Extra note for the client (optional)", t: "textarea" }], { docs: pre }, async d => { const r = await post("comms/drafts/missing-docs", { assignment_id: a.id, docs: d.docs.split("\n").map(x => x.trim()).filter(Boolean), note: d.note }); toast(r.status); redraw(); }, "Create draft");
  } }, "Documents insufficient → draft e-mail"), h("div", { class: "mut" }, "The draft goes to the CA's approval queue; it is not sent automatically.")));
});
