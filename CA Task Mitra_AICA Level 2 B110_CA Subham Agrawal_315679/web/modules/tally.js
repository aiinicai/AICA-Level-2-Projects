WD.mod("tally", {
  nav: [{ id: "q", l: "Tally posting", sub: "connection", roles: ["ca", "manager"] }],
  views: {
    async q(el) {
      const draw = async () => { const rows = await api("tally/queue");
        el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, "Tally integration"), h("span", { class: "sp" }),
          h("button", { class: "btn sec", onclick: () => act(async () => { const r = await post("tally/test"); toast(r.message, !r.ok); }) }, "Test connection"), h("button", { class: "btn", onclick: () => act(async () => { const r = await post("tally/post-pending"); toast(`Posted ${r.posted}, failed ${r.failed}`, r.failed > 0); draw(); }) }, "Post pending to Tally")),
          h("p", { class: "mut" }, "Invoices and receipts are queued automatically. Open TallyPrime with your DEMO company loaded and port 9000 enabled (set the company name and ledgers in Firm settings), then press Post. Never connect a live client company while testing."),
          table([{ k: "created", l: "Queued" }, { k: "kind", l: "Type" }, { k: "ref", l: "Document" }, { l: "Amount", f: r => money(r.amount) }, { l: "Status", f: r => badge(r.status) }, { k: "message", l: "Message" }], rows)); }; await draw();
    }
  }
});
