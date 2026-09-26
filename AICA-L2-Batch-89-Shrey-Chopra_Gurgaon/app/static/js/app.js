// Financial Statement Flux Analyzer — frontend logic
// AICA Level 2 Capstone — Shrey Chopra. See footer for usage notice.

(function () {
  "use strict";

  const COMPARISON_HINTS = {
    mom: "Compares the uploaded periods as one calendar month vs. the immediately prior month.",
    qoq_end: "Compares the current period balance against the prior quarter-end balance.",
    yoy_end: "Compares the current period balance against the prior fiscal year-end (opening) balance.",
    yoy_same: "Compares the current period against the same period one year earlier.",
  };

  const UNIT_LABELS = { "1": "$", "1000": "$000s", "1000000": "$Mn" };

  let state = {
    statementType: "income_statement",
    runId: null,
    runData: null,
    unitScale: 1,
    sortField: null,
    sortDir: "desc",
    filters: { entity: "", category: "", severity: "", status: "", search: "" },
  };

  const $ = (id) => document.getElementById(id);

  // ---------- Statement toggle ----------
  const statementButtons = document.querySelectorAll(".statement-btn");
  statementButtons.forEach((btn, i) => {
    if (i === 0) btn.classList.add("active");
    btn.addEventListener("click", () => {
      statementButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.statementType = btn.dataset.value;
    });
  });

  // ---------- Comparison hint ----------
  const comparisonSelect = $("comparisonType");
  function updateComparisonHint() {
    $("comparisonHint").textContent = COMPARISON_HINTS[comparisonSelect.value] || "";
  }
  comparisonSelect.addEventListener("change", updateComparisonHint);
  updateComparisonHint();

  // ---------- File inputs ----------
  $("priorFile").addEventListener("change", (e) => {
    $("priorFileName").textContent = e.target.files[0] ? e.target.files[0].name : "No file selected";
  });
  $("currentFile").addEventListener("change", (e) => {
    $("currentFileName").textContent = e.target.files[0] ? e.target.files[0].name : "No file selected";
  });

  // ---------- AI toggle ----------
  $("aiToggle").addEventListener("change", (e) => {
    $("aiKeyRow").classList.toggle("hidden", !e.target.checked);
  });

  // ---------- Run ----------
  let useSample = false;
  $("useSampleBtn").addEventListener("click", () => {
    useSample = true;
    $("priorFileName").textContent = "(using bundled sample)";
    $("currentFileName").textContent = "(using bundled sample)";
    runAnalysis();
  });

  $("runBtn").addEventListener("click", () => {
    useSample = false;
    runAnalysis();
  });

  async function runAnalysis() {
    $("runError").textContent = "";
    const threshold = parseFloat($("thresholdInput").value) || 10;
    const comparisonType = comparisonSelect.value;
    const aiEnabled = $("aiToggle").checked;
    const apiKey = $("apiKeyInput").value;

    const fd = new FormData();
    fd.append("statement_type", state.statementType);
    fd.append("comparison_type", comparisonType);
    fd.append("threshold_pct", threshold);
    fd.append("ai_enabled", aiEnabled ? "true" : "false");
    fd.append("api_key", apiKey);

    let url = "/api/run";
    if (useSample) {
      url = "/api/run/sample";
    } else {
      const priorFile = $("priorFile").files[0];
      const currentFile = $("currentFile").files[0];
      if (!priorFile || !currentFile) {
        $("runError").textContent = "Please upload both a prior-period and current-period file, or use the sample data.";
        return;
      }
      fd.append("prior_file", priorFile);
      fd.append("current_file", currentFile);
    }

    $("runBtn").disabled = true;
    $("runBtn").textContent = "Running…";

    try {
      const res = await fetch(url, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        $("runError").textContent = data.error || "Something went wrong.";
        return;
      }
      state.runId = data.run_id;
      state.runData = data;
      // Reset view state for a fresh run
      state.sortField = null;
      state.sortDir = "desc";
      state.filters = { entity: "", category: "", severity: "", status: "", search: "" };
      populateFilterOptions();
      renderResults();
    } catch (err) {
      $("runError").textContent = "Network error: " + err.message;
    } finally {
      $("runBtn").disabled = false;
      $("runBtn").textContent = "Run Flux Analysis";
    }
  }

  // ---------- Unit toggle ----------
  document.querySelectorAll(".unit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".unit-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.unitScale = parseFloat(btn.dataset.unit);
      if (state.runData) renderResults();
    });
  });

  // ---------- Filters ----------
  function populateFilterOptions() {
    if (!state.runData) return;
    const rows = state.runData.rows;
    const entities = [...new Set(rows.map((r) => r.entity))].sort();
    const categories = [...new Set(rows.map((r) => r.category))].sort();

    fillSelect($("filterEntity"), entities, "All entities");
    fillSelect($("filterCategory"), categories, "All categories");
  }

  function fillSelect(select, values, allLabel) {
    const current = select.value;
    select.innerHTML = "";
    const allOpt = document.createElement("option");
    allOpt.value = "";
    allOpt.textContent = allLabel;
    select.appendChild(allOpt);
    values.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      select.appendChild(opt);
    });
    select.value = values.includes(current) ? current : "";
  }

  ["filterEntity", "filterCategory", "filterSeverity", "filterStatus"].forEach((id) => {
    $(id).addEventListener("change", (e) => {
      const key = id.replace("filter", "").toLowerCase();
      state.filters[key] = e.target.value;
      renderResults();
    });
  });
  $("filterSearch").addEventListener("input", (e) => {
    state.filters.search = e.target.value.trim().toLowerCase();
    renderResults();
  });
  $("clearFiltersBtn").addEventListener("click", () => {
    state.filters = { entity: "", category: "", severity: "", status: "", search: "" };
    ["filterEntity", "filterCategory", "filterSeverity", "filterStatus"].forEach((id) => ($(id).value = ""));
    $("filterSearch").value = "";
    renderResults();
  });

  function applyFilters(rows) {
    const f = state.filters;
    return rows.filter((r) => {
      if (f.entity && r.entity !== f.entity) return false;
      if (f.category && r.category !== f.category) return false;
      if (f.severity && (r.severity || "none") !== f.severity) return false;
      if (f.status && r.status !== f.status) return false;
      if (f.search && !r.line_item.toLowerCase().includes(f.search)) return false;
      return true;
    });
  }

  // ---------- Sorting ----------
  document.addEventListener("click", (e) => {
    const th = e.target.closest("th[data-sort]");
    if (!th) return;
    const field = th.dataset.sort;
    if (state.sortField === field) {
      state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
    } else {
      state.sortField = field;
      state.sortDir = "desc";
    }
    renderResults();
  });

  function applySort(rows) {
    if (!state.sortField) return rows;
    const field = state.sortField;
    const dir = state.sortDir === "asc" ? 1 : -1;
    const numericFields = ["prior_amount", "current_amount", "variance_usd", "variance_pct"];
    const sorted = [...rows].sort((a, b) => {
      let av = a[field], bv = b[field];
      if (numericFields.includes(field)) {
        return (av - bv) * dir;
      }
      av = (av || "").toString().toLowerCase();
      bv = (bv || "").toString().toLowerCase();
      if (av < bv) return -1 * dir;
      if (av > bv) return 1 * dir;
      return 0;
    });
    return sorted;
  }

  function updateSortHeaders() {
    document.querySelectorAll("th[data-sort]").forEach((th) => {
      th.classList.remove("sort-active");
      const existing = th.querySelector(".sort-arrow");
      if (existing) existing.remove();
      if (th.dataset.sort === state.sortField) {
        th.classList.add("sort-active");
        const arrow = document.createElement("span");
        arrow.className = "sort-arrow";
        arrow.textContent = state.sortDir === "asc" ? "▲" : "▼";
        th.appendChild(arrow);
      }
    });
  }

  // ---------- Render ----------
  function renderResults() {
    $("emptyState").classList.add("hidden");
    $("resultsContent").classList.remove("hidden");

    const meta = state.runData.meta;
    const allRows = state.runData.rows;
    const readiness = state.runData.readiness;
    const signoff = state.runData.signoff;

    $("resultsTitle").textContent = meta.statement_label + " Flux Analysis";
    $("resultsSubtitle").textContent =
      meta.comparison_label + " · Materiality threshold: " + meta.threshold_pct + "% (min. $1,000) · Values shown in " + UNIT_LABELS[String(state.unitScale)];

    const badge = $("readinessBadge");
    if (readiness.ready) {
      badge.textContent = "FINAL";
      badge.classList.add("final");
    } else {
      badge.textContent = "DRAFT";
      badge.classList.remove("final");
    }

    const aiNote = $("aiNote");
    if (meta.ai_note) {
      aiNote.textContent = meta.ai_note;
      aiNote.classList.remove("hidden");
    } else {
      aiNote.classList.add("hidden");
    }

    const entities = new Set(allRows.map((r) => r.entity));
    const material = allRows.filter((r) => r.is_material);
    const approved = allRows.filter((r) => r.status === "approved" && r.is_material);

    $("metricEntities").textContent = entities.size;
    $("metricLines").textContent = allRows.length;
    $("metricMaterial").textContent = material.length;
    $("metricApproved").textContent = approved.length + " / " + material.length;

    renderChart(allRows);

    const filtered = applyFilters(allRows);
    const sorted = applySort(filtered);
    renderTable(sorted);
    updateSortHeaders();

    $("filterCount").textContent =
      filtered.length === allRows.length
        ? "Showing all " + allRows.length + " line(s)."
        : "Showing " + filtered.length + " of " + allRows.length + " line(s) — filters applied.";

    renderSignoff(signoff, readiness);
  }

  function scaleVal(n) {
    return n / state.unitScale;
  }

  function fmt(n) {
    const scaled = scaleVal(n);
    const decimals = state.unitScale === 1 ? 0 : 2;
    return scaled.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  function renderChart(rows) {
    const byEntity = {};
    rows.forEach((r) => {
      byEntity[r.entity] = (byEntity[r.entity] || 0) + r.variance_usd;
    });
    const entries = Object.entries(byEntity);
    const maxAbs = Math.max(1, ...entries.map(([, v]) => Math.abs(v)));

    const chart = $("entityChart");
    chart.innerHTML = "";
    entries.forEach(([entity, value]) => {
      const heightPct = Math.max(4, (Math.abs(value) / maxAbs) * 100);
      const color = value >= 0 ? "#1E7A46" : "#B00020";
      const wrap = document.createElement("div");
      wrap.className = "entity-bar-wrap";
      wrap.innerHTML =
        '<div class="entity-bar-value">$' + fmt(value) + '</div>' +
        '<div class="entity-bar" style="height:' + heightPct + '%; background:' + color + '"></div>' +
        '<div class="entity-bar-label">' + entity + '</div>';
      chart.appendChild(wrap);
    });
  }

  function renderTable(rows) {
    const tbody = $("fluxTableBody");
    tbody.innerHTML = "";
    rows.forEach((r) => {
      const tr = document.createElement("tr");
      tr.dataset.rowId = r.row_id;
      if (r.is_material) tr.classList.add("material");
      if (r.status === "approved") tr.classList.add("status-approved");
      if (r.status === "rejected") tr.classList.add("status-rejected");

      const severityClass = "severity-" + (r.severity || "none");
      const severityLabel = (r.severity || "none").toUpperCase();

      tr.innerHTML =
        "<td>" + escapeHtml(r.entity) + "</td>" +
        "<td>" + escapeHtml(r.category) + "</td>" +
        "<td>" + escapeHtml(r.line_item) + "</td>" +
        '<td class="num">' + fmt(r.prior_amount) + "</td>" +
        '<td class="num">' + fmt(r.current_amount) + "</td>" +
        '<td class="num">' + fmt(r.variance_usd) + "</td>" +
        '<td class="num">' + r.variance_pct.toFixed(1) + "%</td>" +
        '<td><span class="severity-pill ' + severityClass + '">' + severityLabel + "</span></td>" +
        "<td></td><td></td><td></td><td></td>";

      const statusTd = tr.children[8];
      const statusSelect = document.createElement("select");
      statusSelect.className = "status-select";
      ["pending", "explained", "approved", "rejected"].forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = s.charAt(0).toUpperCase() + s.slice(1);
        if (s === r.status) opt.selected = true;
        statusSelect.appendChild(opt);
      });
      statusSelect.disabled = !r.is_material;
      statusSelect.addEventListener("change", () => updateRow(r.row_id, { status: statusSelect.value }));
      statusTd.appendChild(statusSelect);

      const reviewerTd = tr.children[9];
      const reviewerInput = document.createElement("input");
      reviewerInput.className = "reviewer-input";
      reviewerInput.placeholder = "Reviewer";
      reviewerInput.value = r.reviewer || "";
      reviewerInput.disabled = !r.is_material;
      reviewerInput.addEventListener("blur", () => updateRow(r.row_id, { reviewer: reviewerInput.value }));
      reviewerTd.appendChild(reviewerInput);

      const aiTd = tr.children[10];
      const aiBox = document.createElement("textarea");
      aiBox.className = "commentary-box readonly";
      aiBox.value = r.ai_commentary;
      aiBox.readOnly = true;
      aiBox.title = "System/AI-drafted note — reference only, never edited in place.";
      aiTd.appendChild(aiBox);

      const controllerTd = tr.children[11];
      const controllerBox = document.createElement("textarea");
      controllerBox.className = "commentary-box";
      controllerBox.value = r.controller_commentary;
      controllerBox.disabled = !r.is_material;
      controllerBox.title = "Controller's final position — this is what ships in a FINAL export.";
      controllerBox.addEventListener("blur", () => updateRow(r.row_id, { controller_commentary: controllerBox.value }));
      controllerTd.appendChild(controllerBox);

      tbody.appendChild(tr);
    });
  }

  async function updateRow(rowId, payload) {
    try {
      const res = await fetch("/api/run/" + state.runId + "/row/" + rowId, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok) {
        state.runData = data;
        renderResults();
      }
    } catch (err) {
      console.error(err);
    }
  }

  function renderSignoff(signoff, readiness) {
    $("signoffHint").textContent =
      readiness.n_material === 0
        ? "No lines breached the materiality threshold — nothing requires controller sign-off for this comparison."
        : readiness.n_approved + " of " + readiness.n_material + " material line(s) approved.";

    $("controllerName").value = signoff.controller_name || "";
    $("controllerTitle").value = signoff.controller_title || "";

    const statusEl = $("signoffStatus");
    if (readiness.ready) {
      statusEl.textContent = "✓ Signed off by " + signoff.controller_name + " (" + (signoff.controller_title || "—") + "). Exports will be FINAL.";
      statusEl.className = "signoff-status done";
    } else if (signoff.controller_name) {
      statusEl.textContent = "Signed by " + signoff.controller_name + ", but not all material lines are approved yet. Exports remain DRAFT.";
      statusEl.className = "signoff-status pending";
    } else {
      statusEl.textContent = "Not yet signed off. Exports remain DRAFT until a controller signs off with every material line approved.";
      statusEl.className = "signoff-status pending";
    }
  }

  $("signoffBtn").addEventListener("click", async () => {
    if (!state.runId) return;
    const name = $("controllerName").value.trim();
    const title = $("controllerTitle").value.trim();
    if (!name) {
      alert("Please enter the controller's name before signing off.");
      return;
    }
    try {
      const res = await fetch("/api/run/" + state.runId + "/signoff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ controller_name: name, controller_title: title }),
      });
      const data = await res.json();
      if (res.ok) {
        state.runData = data;
        renderResults();
      } else {
        alert(data.error || "Could not record sign-off.");
      }
    } catch (err) {
      alert("Network error: " + err.message);
    }
  });

  document.querySelectorAll(".btn-export").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!state.runId) return;
      window.location.href = "/api/run/" + state.runId + "/export/" + btn.dataset.fmt;
    });
  });

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }
})();
