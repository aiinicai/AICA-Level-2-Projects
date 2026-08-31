"use strict";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const FRESH_SESSION_MESSAGE = "New session started - it carries zero conversation history.";
const LIVE_VIEW_DEFAULT_INTERVAL_MS = 1500;
const LIVE_VIEW_MIN_INTERVAL_MS = 500;
const LIVE_VIEW_MAX_INTERVAL_MS = 10000;
const PROVIDER_INDICATOR_STATES = Object.freeze({
  offline: { label: "Offline", className: "provider-offline" },
  live: { label: "Live", className: "provider-live" },
  cached: { label: "Cached", className: "provider-cached" },
  fallback: { label: "Fallback", className: "provider-fallback" },
  ready: { label: "Ready", className: "provider-ready" },
  unknown: { label: "Unknown", className: "provider-unknown" },
});

let freshSessionTimer = null;
let settingsOpener = null;
let storedSettings = null;
let liveViewEnabled = false;
let liveViewPollPending = false;
let previousMemoryIds = null;
let previousAuditIds = null;
const countFlashTimers = new WeakMap();

// Friendly labels lead the presentation, while the raw identifiers remain
// visible so reviewers can trace each state back to the architecture and data.
const DISPLAY_LABELS = Object.freeze({
  assertion_type: {
    "direct_self_statement": "Direct statement about themselves",
    "hypothetical": "Hypothetical - not a fact",
    "third_party": "About someone else",
    "quoted": "Quoted speech",
  },
  source_type: {
    "user_stated": "Stated by the user",
    "ai_inferred": "Inferred by the AI",
  },
  trust_tier: {
    "stated": "Highest - the user's own words",
    "confirmed_inference": "Confirmed inference",
    "unconfirmed_inference": "Unconfirmed inference",
  },
  reason_code: {
    "ok": "Passed all checks",
    "instruction_shaped": "Looks like an injected instruction",
    "hypothetical_framing": "Framed as hypothetical, not a fact",
    "not_first_person": "Not a first-person statement",
    "third_party_subject": "About a third party",
    "quoted_speech": "Quoted speech",
    "empty_or_trivial": "Empty or trivial",
    "not_inference_shaped": "Inference phrased as a user statement",
    "overclaims_certainty": "Inference stated as certain fact",
    "approved": "Passed all checks",
    "conflict_detected": "A contradiction was found",
    "parent_not_written": "Its supporting fact was not stored",
  },
  status: {
    "active": "Stored and active",
    "flagged_conflict": "Flagged - conflicts with an existing fact",
    "superseded": "Superseded by a newer fact",
    "deleted": "Deleted",
  },
  served_by: {
    "live": "live API",
    "cache": "cached real response",
    "cache_after_error": "cached real response (live call failed)",
    "stub": "offline engine",
    "fallback_after_error": "offline engine (live call failed)",
    "blocked_by_cap": "offline engine (daily limit reached)",
    "blocked_offline": "offline mode",
  },
  event_type: {
    "write": "Memory written",
    "write_rejected": "Write rejected",
    "contextual_read": "Contextual read",
    "full_export": "Full export",
    "update": "Memory updated",
    "delete": "Memory deleted",
    "access_denied": "Access denied",
  },
  request_shape: {
    "ordinary_query": "Ordinary question",
    "unscoped_dump_attempt": "Unscoped data-dump attempt",
    "legitimate_export_request": "Legitimate export request",
  },
});

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let body;
  try { body = await response.json(); } catch (_) { body = { detail: "Unreadable server response." }; }
  if (!response.ok) throw new Error(body.detail || body.error || `Request failed (${response.status}).`);
  return body;
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  window.setTimeout(() => node.classList.remove("show"), 3200);
}

function setBusy(button, busy) {
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
}

function activateEvidenceTab(tab, moveFocus = false) {
  $$(".evidence-tab").forEach((candidate) => {
    const selected = candidate === tab;
    candidate.setAttribute("aria-selected", String(selected));
    candidate.tabIndex = selected ? 0 : -1;
    const pane = $(`#${candidate.getAttribute("aria-controls")}`);
    pane.hidden = !selected;
  });
  if (moveFocus) tab.focus();
}

function handleEvidenceTabKeydown(event) {
  const tabs = $$(".evidence-tab");
  const current = tabs.indexOf(event.currentTarget);
  let next;
  if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
  else if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = tabs.length - 1;
  else return;
  event.preventDefault();
  activateEvidenceTab(tabs[next], true);
}

function updateEvidenceCount(selector, count, singular, plural) {
  const badge = $(selector);
  const next = String(count);
  const previous = badge.dataset.countValue;
  badge.textContent = next;
  badge.setAttribute("aria-label", `${next} ${count === 1 ? singular : plural}`);
  badge.dataset.countValue = next;

  // The initial API hydration is not a change the audience needs signalled.
  if (previous === undefined || previous === next) return;
  const priorTimer = countFlashTimers.get(badge);
  if (priorTimer !== undefined) window.clearTimeout(priorTimer);
  badge.classList.remove("count-changed");
  void badge.offsetWidth;
  badge.classList.add("count-changed");
  const timer = window.setTimeout(() => {
    badge.classList.remove("count-changed");
    countFlashTimers.delete(badge);
  }, 1200);
  countFlashTimers.set(badge, timer);
}

function liveViewInterval(search = window.location.search) {
  const rawValue = new URLSearchParams(search).get("live");
  if (rawValue === null) return null;
  const requested = rawValue === "1" ? LIVE_VIEW_DEFAULT_INTERVAL_MS : Number(rawValue);
  if (!Number.isFinite(requested)) return null;
  return Math.min(
    LIVE_VIEW_MAX_INTERVAL_MS,
    Math.max(LIVE_VIEW_MIN_INTERVAL_MS, requested),
  );
}

function newlySeenIds(items, previousIds) {
  const currentIds = new Set(items.map((item) => String(item.id)));
  const newIds = liveViewEnabled && previousIds !== null
    ? new Set([...currentIds].filter((id) => !previousIds.has(id)))
    : new Set();
  return { currentIds, newIds };
}

function captureRefreshFocus() {
  const active = document.activeElement;
  if (!(active instanceof HTMLElement)) return null;
  if (!$("#memory-table").contains(active)) return null;
  for (const attribute of ["data-confirm", "data-resolve", "data-delete"]) {
    if (active.hasAttribute(attribute)) {
      return { attribute, value: active.getAttribute(attribute) };
    }
  }
  return null;
}

function restoreRefreshFocus(focusTarget) {
  if (focusTarget === null) return;
  const replacement = $$(`[${focusTarget.attribute}]`).find(
    (candidate) => candidate.getAttribute(focusTarget.attribute) === focusTarget.value,
  );
  if (replacement) replacement.focus({ preventScroll: true });
}

async function withButton(button, action) {
  setBusy(button, true);
  try { return await action(); }
  catch (error) { toast(error.message); return null; }
  finally { setBusy(button, false); }
}

async function refreshStatus() {
  const status = await api("/api/status");
  const indicator = $("#provider-status");
  const category = summariseProviderState([status.llm, status.embeddings]);
  const display = PROVIDER_INDICATOR_STATES[category];
  indicator.className = `provider-indicator ${display.className}`;
  indicator.dataset.providerState = category;
  $("#provider-status-label").textContent = display.label;
  const providerDetail = [
    `LLM: ${status.llm.label} — ${status.llm.provider} / ${status.llm.model} [state: ${status.llm.state}]`,
    `Embeddings: ${status.embeddings.label} — ${status.embeddings.provider} / ${status.embeddings.model} [state: ${status.embeddings.state}]`,
  ];
  if (status.fallback_notice) providerDetail.push(status.fallback_notice);
  indicator.title = providerDetail.join(" | ");
  indicator.setAttribute("aria-label", `${display.label} provider status. ${providerDetail.join(" ")}. Open AI keys.`);

  const budget = $("#budget-status");
  budget.textContent = `Budget ${status.budget.calls_used}/${status.budget.cap}`;
  const nearCap = status.budget.cap > 0
    && status.budget.calls_used / status.budget.cap >= 0.8;
  budget.classList.toggle("near-cap", nearCap);
  const notice = $("#fallback-notice");
  notice.textContent = status.fallback_notice || "";
  notice.classList.toggle("hidden", !status.fallback_notice);
}

function providerCategory(item) {
  // The compact label never upgrades a cached or synthetic answer to "Live".
  // Raw per-provider states remain in the tooltip for mixed-mode calls.
  if (["cache_after_error", "fallback_after_error", "blocked_by_cap"].includes(item.state)) return "fallback";
  if (item.state === "cache") return "cached";
  if (item.state === "live") return "live";
  if (item.state === "ready") return "ready";
  if (["offline", "stub", "blocked_offline"].includes(item.state)) return "offline";
  return "unknown";
}

function summariseProviderState(items) {
  const categories = new Set(items.map(providerCategory));
  return ["unknown", "fallback", "cached", "live", "ready", "offline"]
    .find((state) => categories.has(state)) || "unknown";
}

async function refreshSettings() {
  const settings = await api("/api/settings");
  storedSettings = settings;
  $("#settings-mode").textContent = settings.mode;
  $("#gemini-model").value = settings.gemini.model;
  $("#gemini-key").value = "";
  $("#voyage-key").value = "";
  $("#gemini-key-state").textContent = settings.gemini.configured
    ? "A Gemini key is stored (value hidden)." : "No Gemini key stored.";
  $("#voyage-key-state").textContent = settings.voyage.configured
    ? "A Voyage key is stored (value hidden)." : "No Voyage key stored.";
  return settings;
}

function renderSessionId(sessionId) {
  const node = $("#session-id");
  node.textContent = sessionId.length > 10 ? `${sessionId.slice(0, 9)}…` : sessionId;
  node.setAttribute("aria-label", `Session id ${sessionId}`);
}

function announceFreshSession() {
  const note = $("#session-note");
  note.textContent = FRESH_SESSION_MESSAGE;
  note.classList.add("show");
  if (freshSessionTimer !== null) window.clearTimeout(freshSessionTimer);
  freshSessionTimer = window.setTimeout(() => {
    note.classList.remove("show");
    freshSessionTimer = null;
  }, 8000);
}

async function createSession(announce = false) {
  const data = await api("/api/session/new", { method: "POST", body: "{}" });
  renderSessionId(data.session_id);
  if (announce) announceFreshSession();
  return data;
}

function restoreStoredSettings() {
  if (!storedSettings) return;
  $("#settings-mode").textContent = storedSettings.mode;
  $("#gemini-model").value = storedSettings.gemini.model;
  $("#gemini-key").value = "";
  $("#voyage-key").value = "";
  $("#gemini-key-state").textContent = storedSettings.gemini.configured
    ? "A Gemini key is stored (value hidden)." : "No Gemini key stored.";
  $("#voyage-key-state").textContent = storedSettings.voyage.configured
    ? "A Voyage key is stored (value hidden)." : "No Voyage key stored.";
  $("#settings-result").className = "result-box";
  $("#settings-result").textContent = "";
}

async function openSettingsDialog(opener) {
  await refreshSettings();
  restoreStoredSettings();
  settingsOpener = opener;
  $("#settings-dialog").showModal();
  $("#gemini-key").focus();
}

function cancelSettingsDialog() {
  restoreStoredSettings();
  $("#settings-dialog").close("cancel");
}

async function saveSettings(closeAfter) {
  const settings = await api("/api/settings", {
    method: "POST",
    body: JSON.stringify({
      gemini_api_key: $("#gemini-key").value,
      voyage_api_key: $("#voyage-key").value,
      gemini_model: $("#gemini-model").value.trim() || "gemini-3.5-flash",
    }),
  });
  storedSettings = settings;
  restoreStoredSettings();
  $("#settings-result").className = "result-box success";
  $("#settings-result").textContent = `Saved outside the application bundle. ${settings.mode}`;
  if (closeAfter) $("#settings-dialog").close("saved");
  await refreshStatus();
}

function displayLabel(group, rawValue) {
  return DISPLAY_LABELS[group]?.[rawValue] ?? String(rawValue ?? "");
}

function labeledValue(group, rawValue, prefix = "") {
  const friendly = displayLabel(group, rawValue);
  return `<span class="friendly-label">${escapeHtml(prefix)}${escapeHtml(friendly)}</span>
    <small class="technical-detail">${escapeHtml(group)}: ${escapeHtml(rawValue)}</small>`;
}

function subjectKeyValue(rawValue) {
  const friendly = String(rawValue ?? "").replaceAll("_", " ");
  return `<span class="friendly-label">Subject: ${escapeHtml(friendly)}</span>
    <small class="technical-detail">subject_key: ${escapeHtml(rawValue)}</small>`;
}

function memoryTrustTier(memory) {
  if (memory.source_type === "user_stated") return "stated";
  return memory.confirmed_at ? "confirmed_inference" : "unconfirmed_inference";
}

function providerLine(provider) {
  if (!provider) return `<span class="friendly-label">No provider call required</span>`;
  return `<span class="friendly-label">Served by ${escapeHtml(displayLabel("served_by", provider.served_by))}</span>
    <small class="technical-detail">${escapeHtml(provider.provider_name)} / ${escapeHtml(provider.model)} · ${escapeHtml(provider.served_by)}</small>`;
}

function providerNote(candidate, makerProvider) {
  const providers = [makerProvider, ...Object.values(candidate.provider_calls || {})]
    .filter(Boolean);
  const servedBy = new Set(providers.map((provider) => provider.served_by));

  if (servedBy.has("fallback_after_error")) {
    return `<div class="provider-note attention">A live call failed; served by the offline engine. Governance continued normally.</div>`;
  }
  if (servedBy.has("cache_after_error")) {
    return `<div class="provider-note attention">A live call failed; served by a cached real response. Governance continued normally.</div>`;
  }
  if (servedBy.has("blocked_by_cap")) {
    return `<div class="provider-note attention">Daily live-call limit reached; the offline engine served this.</div>`;
  }
  if (servedBy.has("blocked_offline")) {
    return `<div class="provider-note offline">Running in offline mode - the deterministic engine served this. No API key is configured.</div>`;
  }
  return "";
}

function renderPipeline(report) {
  const candidates = report.candidates.map((candidate, index) => {
    const rejected = candidate.outcome === "rejected";
    const checker = candidate.provider_calls?.checker;
    const entailment = candidate.provider_calls?.entailment;
    const embedding = candidate.provider_calls?.embedding;
    const stopped = `<div class="stage stopped"><strong>Stopped</strong>Not reached because the checker refused this candidate.</div>`;
    return `<div class="candidate-pipeline">
      <div class="candidate-title">Candidate ${index + 1} · ${escapeHtml(candidate.content_sha256.slice(0, 12))}…</div>
      <div class="stage-flow">
        <div class="stage pass"><strong>Maker</strong>${labeledValue("assertion_type", candidate.assertion_type)}${labeledValue("source_type", candidate.source_type)}${subjectKeyValue(candidate.subject_key)}</div>
        <div class="stage ${rejected ? "reject" : "pass"}"><strong>Checker</strong><span class="friendly-label">${rejected ? "Rejected by checker." : "Approved to continue."}</span>${labeledValue("reason_code", candidate.reason_code)}${providerLine(checker)}${rejected ? `<small class="technical-detail">Audit row: ${escapeHtml(candidate.audit_row_ids.join(", "))}</small>` : ""}</div>
        ${rejected ? stopped + stopped + stopped : `
        <div class="stage pass"><strong>Provenance</strong>${labeledValue("source_type", candidate.source_type, "Source: ")}${labeledValue("trust_tier", candidate.trust_tier, "Trust: ")}</div>
        <div class="stage pass"><strong>Contradiction</strong><span class="friendly-label">Compared against ${escapeHtml(candidate.checked_count)} existing ${candidate.checked_count === 1 ? "fact" : "facts"}.</span><span class="friendly-label">${candidate.conflict_memory_ids.length ? `Contradiction with ${candidate.conflict_memory_ids.length === 1 ? "memory" : "memories"} #${escapeHtml(candidate.conflict_memory_ids.join(", #"))}.` : "No contradiction found."}</span>${providerLine(entailment)}</div>
        <div class="stage pass"><strong>Write</strong><span class="friendly-label">Stored as memory #${escapeHtml(candidate.memory_id)}.</span>${labeledValue("status", candidate.status)}${providerLine(embedding)}</div>`}
      </div>
      ${providerNote(candidate, report.maker_provider)}
    </div>`;
  }).join("");
  $("#pipeline").className = "";
  $("#pipeline").innerHTML = `<div class="stage pass"><strong>Maker</strong><span class="friendly-label">Proposed ${report.candidate_count} candidate ${report.candidate_count === 1 ? "fact" : "facts"}.</span>${providerLine(report.maker_provider)}</div>${candidates || "<p>No candidate fact was proposed.</p>"}`;
}

async function refreshMemories() {
  const data = await api("/api/memories");
  const seen = newlySeenIds(data.memories, previousMemoryIds);
  previousMemoryIds = seen.currentIds;
  updateEvidenceCount("#memory-count", data.count, "memory", "memories");
  if (!data.memories.length) {
    $("#memory-table").innerHTML = "<p class='note'>The store is empty.</p>";
    return;
  }
  const conflicts = data.memories.filter((item) => item.status === "flagged_conflict");
  const rows = data.memories.map((item) => {
    const classes = [item.source_type === "ai_inferred" ? "inference" : "", item.status === "flagged_conflict" ? "conflict" : "", item.status === "superseded" ? "superseded" : "", seen.newIds.has(String(item.id)) ? "row-changed" : ""].join(" ");
    const other = conflicts.find((candidate) => candidate.id !== item.id && candidate.subject_key === item.subject_key);
    const badge = item.trust_tier === "unconfirmed_inference" ? "<span class='badge inference'>unconfirmed inference</span>" : item.status === "flagged_conflict" ? "<span class='badge conflict'>conflict</span>" : "";
    return `<tr class="${classes}" data-memory-id="${item.id}">
      <td><strong>#${item.id}</strong> ${escapeHtml(item.content)}<br>${badge}</td>
      <td>${escapeHtml(item.subject_key)}<br>${escapeHtml(item.source_type)}<br>${escapeHtml(item.trust_tier)}</td>
      <td>${escapeHtml(item.status)}<br><small>${escapeHtml(item.created_at)}</small><br><small>${escapeHtml(item.source_session_id)}</small></td>
      <td><div class="row-actions">
        ${item.trust_tier === "unconfirmed_inference" ? `<button data-confirm="${item.id}">Confirm</button>` : ""}
        ${other ? `<button data-resolve="${item.id}" data-other="${other.id}">Keep this</button>` : ""}
        <button data-delete="${item.id}" class="danger">Delete</button>
      </div></td>
    </tr>`;
  }).join("");
  $("#memory-table").innerHTML = `<table><thead><tr><th>Memory</th><th>Governance</th><th>State &amp; provenance</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table>`;

  $$('[data-confirm]').forEach((button) => button.addEventListener("click", () => withButton(button, async () => {
    await api(`/api/memory/${button.dataset.confirm}/confirm`, { method: "POST", body: "{}" });
    toast("Inference confirmed and audit row appended."); await refreshAll();
  })));
  $$('[data-resolve]').forEach((button) => button.addEventListener("click", () => withButton(button, async () => {
    await api("/api/conflict/resolve", { method: "POST", body: JSON.stringify({ keep_id: Number(button.dataset.resolve), supersede_id: Number(button.dataset.other) }) });
    toast("Conflict resolved; both status changes were audited."); await refreshAll();
  })));
  $$('[data-delete]').forEach((button) => button.addEventListener("click", () => withButton(button, async () => {
    const id = button.dataset.delete;
    const plan = await api(`/api/memory/${id}/cascade`);
    const confirmed = window.confirm(`Delete memory ${id}? This physically erases ${plan.memory_ids.length} memory row(s) and ${plan.embedding_ids.length} embedding row(s).`);
    if (!confirmed) return;
    await api(`/api/memory/${id}`, { method: "DELETE", body: JSON.stringify({ confirmed: true }) });
    toast("Cascade physically erased; structural audit evidence retained."); await refreshAll();
  })));
}

function renderChain(chain) {
  const node = $("#chain-summary");
  node.className = `chain-summary ${chain.valid ? "valid" : "invalid"}`;
  node.textContent = chain.valid ? `✓ Chain valid · ${chain.rows_checked} rows` : `✕ Chain broken at row ${chain.broken_at_row_id}`;
}

async function refreshAudit() {
  const data = await api("/api/audit");
  const seen = newlySeenIds(data.rows, previousAuditIds);
  previousAuditIds = seen.currentIds;
  updateEvidenceCount("#audit-count", data.count, "audit row", "audit rows");
  renderChain(data.chain);
  $("#audit-table").innerHTML = data.rows.length ? data.rows.map((row) => `
    <article class="audit-row${seen.newIds.has(String(row.id)) ? " row-changed" : ""}" data-audit-id="${row.id}">
      <div class="audit-row-head"><span>#${row.id} · ${escapeHtml(row.event_type)}</span><span>${escapeHtml(row.timestamp)}</span></div>
      <div>actor: ${escapeHtml(row.actor)} · memory: ${escapeHtml(row.memory_id ?? "—")}</div>
      <pre class="audit-detail">${escapeHtml(JSON.stringify(row.detail, null, 2))}</pre>
      <div class="hash-link">${escapeHtml(row.prev_row_hash.slice(0, 10))}… → ${escapeHtml(row.row_hash.slice(0, 10))}…</div>
    </article>`).join("") : "<p class='note'>No audited operations yet.</p>";
}

async function refreshEvidence() {
  await Promise.all([refreshMemories(), refreshAudit()]);
}

async function refreshAll() {
  await Promise.all([refreshEvidence(), refreshStatus(), refreshSettings()]);
}

async function pollLiveView() {
  if (liveViewPollPending) return;
  liveViewPollPending = true;
  const focusTarget = captureRefreshFocus();
  try {
    // These are the same renderers used by action-driven refreshes. Polling
    // deliberately excludes settings and never invokes tab activation.
    // Wait for both branches even if one fails so focus restoration happens
    // only after every DOM update from this tick has settled.
    await Promise.allSettled([refreshEvidence(), refreshStatus()]);
  } catch (_) {
    // A recording should survive a transient request failure without a toast.
  } finally {
    restoreRefreshFocus(focusTarget);
    liveViewPollPending = false;
  }
}

function enableLiveView(interval) {
  liveViewEnabled = true;
  const indicator = $("#live-view-status");
  indicator.hidden = false;
  indicator.title = `Auto-refreshing every ${interval} ms`;
}

$$(".evidence-tab").forEach((tab) => {
  tab.addEventListener("click", () => activateEvidenceTab(tab));
  tab.addEventListener("keydown", handleEvidenceTabKeydown);
});

$("#new-session").addEventListener("click", (event) => withButton(event.currentTarget, () => createSession(true)));
$("#provider-status").addEventListener("click", (event) => withButton(event.currentTarget, () => openSettingsDialog(event.currentTarget)));
$("#open-settings").addEventListener("click", (event) => withButton(event.currentTarget, () => openSettingsDialog(event.currentTarget)));
$("#save-settings").addEventListener("click", (event) => withButton(event.currentTarget, () => saveSettings(false)));
$("#save-settings-close").addEventListener("click", (event) => withButton(event.currentTarget, () => saveSettings(true)));
$("#cancel-settings").addEventListener("click", cancelSettingsDialog);

const settingsDialog = $("#settings-dialog");
settingsDialog.addEventListener("cancel", (event) => {
  event.preventDefault();
  cancelSettingsDialog();
});
settingsDialog.addEventListener("click", (event) => {
  if (event.target !== settingsDialog) return;
  const bounds = settingsDialog.getBoundingClientRect();
  const outside = event.clientX < bounds.left || event.clientX > bounds.right
    || event.clientY < bounds.top || event.clientY > bounds.bottom;
  if (outside) cancelSettingsDialog();
});
settingsDialog.addEventListener("close", () => {
  const opener = settingsOpener;
  settingsOpener = null;
  if (opener) opener.focus();
});
$("#test-settings").addEventListener("click", (event) => withButton(event.currentTarget, async () => {
  const report = await api("/api/settings/test", { method: "POST", body: "{}" });
  const rows = Object.entries(report.results).map(([name, result]) =>
    `${name}: ${result.message}`);
  const configured = Object.values(report.results).filter((item) => item.configured);
  const succeeded = configured.length > 0 && configured.every((item) => item.success);
  $("#settings-result").className = `result-box ${succeeded ? "success" : "failure"}`;
  $("#settings-result").textContent = `${rows.join(" ")} Budget: ${report.budget.calls_used}/${report.budget.cap}.`;
  await refreshStatus();
}));
$("#clear-settings").addEventListener("click", (event) => withButton(event.currentTarget, async () => {
  const settings = await api("/api/settings/clear", { method: "POST", body: "{}" });
  $("#settings-result").className = "result-box success";
  $("#settings-result").textContent = settings.mode;
  await refreshAll();
}));
$("#send-turn").addEventListener("click", (event) => withButton(event.currentTarget, async () => {
  const text = $("#turn-text").value.trim();
  if (!text) throw new Error("Enter a direct user turn first.");
  const report = await api("/api/turn", { method: "POST", body: JSON.stringify({ text }) });
  renderPipeline(report); await refreshAll();
}));
$("#run-query").addEventListener("click", (event) => withButton(event.currentTarget, async () => {
  const text = $("#query-text").value.trim();
  if (!text) throw new Error("Enter a question first.");
  const result = await api("/api/query", { method: "POST", body: JSON.stringify({ text }) });
  const node = $("#query-result");
  if (!result.allowed) {
    node.className = "result-box failure";
    node.textContent = `REFUSED: ${result.reason} No memory content returned.`;
  } else {
    node.className = "result-box success";
    node.innerHTML = `<strong>${result.returned_count} of ${result.top_k_max} max</strong>${result.hits.map((hit) => `<p>#${hit.id} · score ${hit.similarity.toFixed(3)} · ${escapeHtml(hit.source_type)} · ${escapeHtml(hit.source_session_id)}<br>${escapeHtml(hit.content)}</p>`).join("") || "<p>No matches.</p>"}`;
  }
  await refreshAll();
}));
$("#run-export").addEventListener("click", (event) => withButton(event.currentTarget, async () => {
  const result = await api("/api/export", { method: "POST", body: JSON.stringify({ passphrase: $("#passphrase").value }) });
  const node = $("#export-result");
  if (result.succeeded) {
    const rows = result.memories.map((memory) => {
      const trustTier = memoryTrustTier(memory);
      const classes = [
        memory.source_type === "ai_inferred" ? "inference" : "",
        memory.status === "flagged_conflict" ? "conflict" : "",
      ].join(" ");
      return `<tr class="${classes}">
        <td><strong>#${escapeHtml(memory.id)}</strong> ${escapeHtml(memory.content)}</td>
        <td>${subjectKeyValue(memory.subject_key)}</td>
        <td>${labeledValue("source_type", memory.source_type, "Source: ")}${labeledValue("trust_tier", trustTier, "Trust: ")}</td>
        <td>${labeledValue("status", memory.status)}
          <span class="friendly-label">Created ${escapeHtml(memory.created_at)}</span>
          <small class="technical-detail">created_at: ${escapeHtml(memory.created_at)}</small>
          <span class="friendly-label">Source session ${escapeHtml(memory.source_session_id)}</span>
          <small class="technical-detail">source_session_id: ${escapeHtml(memory.source_session_id)}</small>
        </td>
      </tr>`;
    }).join("");
    node.className = "result-box success";
    node.innerHTML = `<p class="export-confirmation">Gate confirmed: complete export returned ${result.memories.length} row(s).</p>
      <h3 class="export-heading">Complete record returned under the Section 11 access right</h3>
      <div class="table-scroll export-scroll">
        <table class="export-table">
          <thead><tr><th>Memory</th><th>Subject</th><th>Source &amp; trust</th><th>State &amp; provenance</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4">No active records were available to export.</td></tr>'}</tbody>
        </table>
      </div>`;
  } else {
    node.className = "result-box failure";
    node.textContent = `REFUSED: ${result.reason} Zero rows returned.`;
  }
  await refreshAll();
}));

$$('.scenario-button').forEach((button) => button.addEventListener("click", () => withButton(button, async () => {
  const result = await api(`/api/scenario/${button.dataset.scenario}`, { method: "POST", body: "{}" });
  const node = $("#scenario-result");
  node.className = `result-box ${result.passed ? "success" : "failure"}`;
  node.innerHTML = `<strong>Scenario ${escapeHtml(result.id)}: ${result.passed ? "PASS" : "FAIL"}</strong><br>${escapeHtml(result.what_it_proves)}<br><small>${result.audit_rows_written} audit row(s) written</small>`;
  await refreshAll();
})));

$("#run-all").addEventListener("click", (event) => withButton(event.currentTarget, async () => {
  const result = await api("/api/scenario/all", { method: "POST", body: "{}" });
  const node = $("#scenario-result");
  node.className = `result-box ${result.passed ? "success" : "failure"}`;
  node.innerHTML = result.results.map((item) => `<div><strong>${escapeHtml(item.id)}</strong> ${item.passed ? "PASS" : "FAIL"} · ${escapeHtml(item.title)}</div>`).join("");
  await refreshAll();
}));

async function resetDemo() {
  const result = await api("/api/reset", { method: "POST", body: "{}" });
  renderSessionId(result.session_id);
  $("#repair").classList.add("hidden");
  $("#tamper").classList.remove("hidden");
  $("#scenario-result").innerHTML = "";
  $("#pipeline").className = "pipeline-empty";
  $("#pipeline").textContent = "Send a turn to see Maker → Checker → Provenance → Contradiction → Write.";
  await refreshAll();
}

$("#reset").addEventListener("click", (event) => withButton(event.currentTarget, resetDemo));
$("#repair").addEventListener("click", (event) => withButton(event.currentTarget, resetDemo));
$("#refresh-memories").addEventListener("click", (event) => withButton(event.currentTarget, refreshEvidence));
$("#verify-chain").addEventListener("click", (event) => {
  activateEvidenceTab($("#audit-tab"));
  return withButton(event.currentTarget, refreshAudit);
});
$("#tamper").addEventListener("click", (event) => {
  activateEvidenceTab($("#audit-tab"));
  return withButton(event.currentTarget, async () => {
    const result = await api("/api/audit/tamper", { method: "POST", body: "{}" });
    renderChain(result.chain);
    $("#repair").classList.remove("hidden");
    $("#tamper").classList.add("hidden");
    toast(`Tamper detected at audit row ${result.chain.broken_at_row_id}.`);
    await refreshAudit();
  });
});

window.addEventListener("DOMContentLoaded", async () => {
  const interval = liveViewInterval();
  if (interval !== null) enableLiveView(interval);
  try { await createSession(false); await refreshAll(); }
  catch (error) { toast(error.message); }
  // No query-string opt-in means this timer code path is never reached.
  if (interval !== null) window.setInterval(pollLiveView, interval);
});
