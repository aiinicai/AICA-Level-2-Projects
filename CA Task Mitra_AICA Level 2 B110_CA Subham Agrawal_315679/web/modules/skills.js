WD.mod("skills", {
  nav: [{ id: "lib", l: "Skills library", sub: "library" }],
  views: {
    async lib(el) {
      const [rows, sv] = await Promise.all([api("skills/skills"), api("work/services")]);
      const F = [{ k: "name", l: "Skill name", req: 1 }, { k: "description", l: "What it does" }, { k: "instructions", l: "Instructions (paste your skill / prompt here)", t: "textarea", req: 1 }, { k: "docs_needed", l: "Documents the employee must attach" }, { k: "provider", l: "Opens in", t: "select", o: [["claude", "Claude"], ["chatgpt", "ChatGPT"], ["gemini", "Gemini (copy only)"]] }, { k: "active", l: "Active", t: "checkbox", d: 1 }];
      el.replaceChildren(h("div", { class: "row" }, h("h2", { style: "margin:0" }, "AI skills library"), h("span", { class: "sp" }), h("button", { class: "btn", onclick: () => formModal(isCA() ? "New skill" : "Suggest a new skill (needs CA approval)", F, {}, async d => { const r = await post("skills/skills", d); toast(r.status === "pending" ? "Sent to the CA for approval" : "Skill added"); go("skills", "lib"); }) }, isCA() ? "+ New skill" : "+ Suggest a skill")),
        h("p", { class: "mut" }, (isCA() ? "" : "Only the CA can edit skills. Skills you suggest become available after the CA approves them. ") + "Skills live in the software. Link a skill to a service and it appears on every matching assignment with a Run button. Use only your firm's approved AI account and avoid live client identifiers."),
        table([{ l: "Skill", f: r => [r.name, r.status === "pending" ? [" ", badge("Pending")] : ""] }, { k: "description", l: "Purpose" }, { l: "Linked services", f: r => r.service_ids.map(i => (sv.find(s => s.id === i) || {}).name).filter(Boolean).join(", ") || "—" }, { k: "runs", l: "Runs" },
          { l: "", f: r => !isCA() ? (r.status === "pending" ? h("span", { class: "mut" }, "Waiting for CA approval") : "") : h("span", {}, r.status === "pending" ? [h("button", { class: "btn ok sm", onclick: () => act(async () => { await post(`skills/skills/${r.id}/approve`); go("skills", "lib"); }, "Approved") }, "Approve"), " ", h("button", { class: "btn bad sm", onclick: () => act(async () => { await post(`skills/skills/${r.id}/reject`); go("skills", "lib"); }) }, "Reject"), " "] : "", h("button", { class: "btn sec sm", onclick: () => formModal("Edit skill", F, r, async d => { await put("skills/skills/" + r.id, d); go("skills", "lib"); }) }, "Edit"), " ",
            on("skills", "service_link") ? h("button", { class: "btn sec sm", onclick: () => { const boxes = h("div", {}, sv.map(s => h("label", { style: "display:block" }, h("input", { type: "checkbox", style: "width:auto", value: s.id, checked: r.service_ids.includes(s.id) }), " " + s.name))); const m = modal("Link to services", h("div", {}, boxes, h("button", { class: "btn", onclick: () => act(async () => { await post(`skills/skills/${r.id}/link`, { service_ids: [...boxes.querySelectorAll("input:checked")].map(i => +i.value) }); m.close(); go("skills", "lib"); }, "Linked") }, "Save"))); } }, "Link services") : "") }], rows));
    }
  }
});
async function runSkill(s, aid) {
  const r = await post(`skills/skills/${s.id}/run`, { assignment_id: aid });
  try { await navigator.clipboard.writeText(r.prompt); } catch (e) { }
  const m = modal("Run: " + s.name, h("div", {}, h("p", {}, "The skill prompt is copied to your clipboard. ", r.url ? "Claude/ChatGPT opens in a new tab with it filled in; if the text is cut off, just paste it." : "Paste it into your AI chat."), h("div", { class: "pre" }, r.prompt), h("p", { class: "mut" }, r.note),
    r.url ? h("a", { class: "btn", href: r.url, target: "_blank", style: "text-decoration:none" }, "Open " + (r.provider === "chatgpt" ? "ChatGPT" : "Claude")) : ""), { wide: true });
  if (r.url) window.open(r.url, "_blank");
}
WD.hooks.assignment.push(async (a, box) => {
  if (!on("skills", "launcher")) return; const sk = await api("skills/for-assignment/" + a.id); if (!sk.length) return;
  box.append(h("div", { class: "card" }, h("b", {}, "AI skills for this task"), h("div", { class: "row", style: "margin-top:8px" }, sk.map(s => h("button", { class: "btn", title: s.description, onclick: () => runSkill(s, a.id) }, "▶ " + s.name))), h("div", { class: "mut" }, "Attach: " + sk.map(s => s.docs_needed).filter(Boolean).join(" · "))));
});
