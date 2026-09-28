// Run the n8n workflow's "Validate Payload" and "Compare With Last Run" code locally on examples/monitor_payload.json
// and write the alert email the committee would receive. Same code as the workflow (read from the .ts source).
// Usage: node tools/render_alert.js
const fs = require("fs"), path = require("path");
const root = path.resolve(__dirname, "..");
const src = fs.readFileSync(path.join(root, "n8n", "lookthrough_monitor.workflow.ts"), "utf8");
const codes = [...src.matchAll(/jsCode: `([\s\S]*?)`/g)].map(m => m[1]);
if (codes.length !== 2) throw new Error("expected 2 Code nodes, found " + codes.length);
const payload = JSON.parse(fs.readFileSync(path.join(root, "examples", "monitor_payload.json"), "utf8"));
const run = (code, input, nodes) => new Function("$input", "$", code)({ all: () => input }, name => ({ first: () => nodes[name] }));
const validated = run(codes[0], [{ json: { body: payload } }], {})[0];
const prevJuly = { as_on: "2026-07-31", value_cr: 46.1, breach_list: "Single stock: HDFC Bank | Sector: Financial Services" };
const out = run(codes[1], [{ json: prevJuly }], { "Validate Payload": validated })[0].json;
fs.writeFileSync(path.join(root, "examples", "monitor_alert_email.html"),
  `<!doctype html><meta charset="utf-8"><title>${out.subject}</title>\n<!-- Illustrative: previous run is a made-up July row; current run is the real 31-Aug-2026 payload. -->\n` + out.html);
console.log("subject:", out.subject, "| alert:", out.needsAlert, "| changes:", out.row.changes);
