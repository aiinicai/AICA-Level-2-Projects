/*
 * FinSight — Dashboard screen wiring (Stage 4, rewired Stage 14).
 *
 * Reads the server-rendered data payload out of the
 * #fs-dashboard-data <script type="application/json"> tag and hands it
 * to the reusable components in charts.js. This file knows about the
 * Dashboard's specific panel ids; charts.js itself stays generic so
 * later screens can call it with their own data shapes.
 *
 * Stage 14: the gauge/coverage panels were removed from the Dashboard
 * template (see dashboard/index.html and app/api/dashboard_bp.py for
 * why — no real risk-scoring algorithm exists to drive a gauge
 * honestly). renderGauge/renderCoverage in charts.js are left in place,
 * unused here, exactly like the SEBI applicability plumbing elsewhere
 * in this app — available for a future stage, not deleted.
 */
(function () {
  "use strict";

  function readDashboardData() {
    const node = document.getElementById("fs-dashboard-data");
    if (!node) return null;
    try {
      return JSON.parse(node.textContent);
    } catch (err) {
      console.error("FinSight dashboard: could not parse dashboard data payload", err);
      return null;
    }
  }

  // Dashboard-only color mapping (design-system.css's --fs-chart-*
  // tokens) — a lighter, more muted/professional palette than the
  // vivid --fs-risk-*/flat-accent colors used previously on these two
  // charts specifically. See the CSS comment above those tokens: this
  // does not touch any risk-level badge or label elsewhere in the app.
  const MODULE_BAR_COLORS = {
    ACCOUNTING: "chart-module-accounting",
    AUDIT: "chart-module-audit",
    TAX: "chart-module-tax",
  };

  function init() {
    const data = readDashboardData();
    if (!data || !window.FinCharts) return;

    FinCharts.renderDonut("fs-chart-risk-distribution", {
      segments: (data.risk_distribution || []).map((r) => ({
        label: r.label,
        value: r.value,
        color: "chart-risk-" + r.level,
      })),
      centerLabel: "Findings",
      emptyText: "No findings recorded yet.",
    });

    FinCharts.renderBarChart("fs-chart-exceptions-module", {
      items: (data.exceptions_by_module || []).map((m) => ({
        label: m.label,
        value: m.value,
        color: MODULE_BAR_COLORS[m.module_key] || null,
      })),
      emptyText: "No findings recorded yet.",
    });

    FinCharts.renderBarChart("fs-chart-query-status", {
      items: (data.query_status_bars || []).map((q) => ({
        label: q.label,
        value: q.value,
      })),
      emptyText: "No queries raised yet.",
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
