/* ===== RESOLVE 360 — scoring.js =====
   Explainable priority score (0-100) and risk band. */

function score(r) {
  const W = CONFIG.WEIGHTS, C = CONFIG.CAPS;
  const s = W.severity * r.severity / C.severity
          + W.people * Math.min(r.people_affected / C.people, 1)
          + W.days * Math.min(r.days_open / C.days, 1)
          + W.loss * Math.min(r.estimated_loss_inr / C.loss, 1);
  return Math.min(100, s);
}

function risk(n) {
  return n >= CONFIG.HIGH_RISK ? 'High' : n >= CONFIG.MEDIUM_RISK ? 'Medium' : 'Low';
}

// Escape text before inserting it into HTML (protects against CSV injection of markup)
function esc(x) {
  return String(x).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
