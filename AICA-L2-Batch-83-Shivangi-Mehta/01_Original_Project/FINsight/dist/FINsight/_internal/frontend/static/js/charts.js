/*
 * FinSight — dependency-free chart component library (Stage 4).
 *
 * No external charting library, no CDN, no network access — everything
 * here is plain DOM/SVG built with vanilla JavaScript. See the Stage 4
 * blueprint addendum for why this replaces the originally-approved
 * Chart.js line item (the sandbox this project was built in cannot
 * vendor any external JS library, and the product is offline-first by
 * design regardless).
 *
 * Each function takes a container element and a plain-data object, and
 * renders one self-contained component into it. They do not know
 * anything about engagements, exceptions, or any other domain model —
 * later stages (Exception Centre, Review screens, etc.) can reuse these
 * by simply producing the same small data shapes. This is the "keep
 * chart components modular so additional visualizations can be added
 * later" requirement.
 *
 * Every component degrades explicitly to a labeled empty/zero state
 * rather than rendering a misleading chart when all values are zero —
 * important here because Stage 4 ships with no real engagement data
 * (that's Stage 5+).
 */
(function (global) {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";

  function svgEl(tag, attrs) {
    const el = document.createElementNS(SVG_NS, tag);
    for (const key in attrs) {
      el.setAttribute(key, attrs[key]);
    }
    return el;
  }

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    for (const key in attrs || {}) {
      if (key === "class") node.className = attrs[key];
      else if (key === "text") node.textContent = attrs[key];
      else node.setAttribute(key, attrs[key]);
    }
    (children || []).forEach((c) => c && node.appendChild(c));
    return node;
  }

  function polarToCartesian(cx, cy, r, angleDeg) {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  function sum(items, key) {
    return items.reduce((total, item) => total + (Number(item[key]) || 0), 0);
  }

  function resolveColor(colorToken) {
    // Accept either a CSS custom-property name ("risk-critical") or a
    // literal CSS color string ("#2f6f8f") so callers aren't forced to
    // register a token for one-off series colors.
    if (!colorToken) return "var(--fs-accent)";
    if (colorToken.indexOf("(") !== -1 || colorToken.indexOf("#") === 0) {
      return colorToken;
    }
    return `var(--fs-${colorToken})`;
  }

  function resolveContainer(target) {
    return typeof target === "string" ? document.getElementById(target) : target;
  }

  /* ---------------------------------------------------------------
   * Donut chart — used for Risk Distribution.
   * data: { segments: [{label, value, color}], centerLabel, emptyText }
   * ------------------------------------------------------------- */
  function renderDonut(target, data) {
    const container = resolveContainer(target);
    if (!container) return;
    container.innerHTML = "";

    const segments = (data.segments || []).filter((s) => Number(s.value) > 0);
    const total = sum(data.segments || [], "value");

    const size = 180;
    const cx = size / 2;
    const cy = size / 2;
    const r = 70;
    const strokeWidth = 22;
    const circumference = 2 * Math.PI * r;

    const svg = svgEl("svg", {
      viewBox: `0 0 ${size} ${size}`,
      width: size,
      height: size,
      role: "img",
      "aria-label": data.ariaLabel || "Donut chart",
    });

    if (total === 0) {
      svg.appendChild(
        svgEl("circle", {
          cx, cy, r,
          fill: "none",
          stroke: "var(--fs-track)",
          "stroke-width": strokeWidth,
        })
      );
    } else {
      let offset = 0;
      segments.forEach((seg) => {
        const fraction = Number(seg.value) / total;
        const dash = fraction * circumference;
        const circle = svgEl("circle", {
          cx, cy, r,
          fill: "none",
          stroke: resolveColor(seg.color),
          "stroke-width": strokeWidth,
          "stroke-dasharray": `${dash} ${circumference - dash}`,
          "stroke-dashoffset": -offset,
          transform: `rotate(-90 ${cx} ${cy})`,
        });
        svg.appendChild(circle);
        offset += dash;
      });
    }

    const centerValue = svgEl("text", {
      x: cx, y: cy - 2,
      "text-anchor": "middle",
      class: "fs-donut-center-value",
    });
    centerValue.textContent = total === 0 ? "0" : String(total);
    svg.appendChild(centerValue);

    const centerLabel = svgEl("text", {
      x: cx, y: cy + 16,
      "text-anchor": "middle",
      class: "fs-donut-center-label",
    });
    centerLabel.textContent = data.centerLabel || "Total";
    svg.appendChild(centerLabel);

    const legend = el("div", { class: "fs-legend" });
    (data.segments || []).forEach((seg) => {
      legend.appendChild(
        el("div", { class: "fs-legend-item" }, [
          el("span", {
            class: "fs-legend-swatch",
            style: `background:${resolveColor(seg.color)}`,
          }),
          el("span", { text: seg.label }),
          el("span", { class: "fs-legend-value", text: String(seg.value) }),
        ])
      );
    });

    const wrap = el("div", { class: "fs-donut-wrap" }, [svg, legend]);
    container.appendChild(wrap);

    if (total === 0) {
      container.appendChild(
        el("p", { class: "fs-chart-empty", text: data.emptyText || "No data yet." })
      );
    }
  }

  /* ---------------------------------------------------------------
   * Horizontal bar chart — used for Exceptions by Module and Query
   * Status.
   * data: { items: [{label, value, color}], emptyText }
   * ------------------------------------------------------------- */
  function renderBarChart(target, data) {
    const container = resolveContainer(target);
    if (!container) return;
    container.innerHTML = "";

    const items = data.items || [];
    const max = Math.max(1, ...items.map((i) => Number(i.value) || 0));
    const total = sum(items, "value");

    const chart = el("div", { class: "fs-barchart" });
    items.forEach((item) => {
      const value = Number(item.value) || 0;
      const pct = (value / max) * 100;
      chart.appendChild(
        el("div", { class: "fs-barchart-row" }, [
          el("span", { class: "fs-barchart-label", text: item.label }),
          el("div", { class: "fs-barchart-track" }, [
            el("div", {
              class: "fs-barchart-fill",
              style: `width:${pct}%; background:${resolveColor(item.color)}`,
            }),
          ]),
          el("span", { class: "fs-barchart-value", text: String(value) }),
        ])
      );
    });
    container.appendChild(chart);

    if (total === 0) {
      container.appendChild(
        el("p", { class: "fs-chart-empty", text: data.emptyText || "No data yet." })
      );
    }
  }

  /* ---------------------------------------------------------------
   * Coverage bars — used for Review / Data Coverage.
   * data: { rows: [{label, percent}], emptyText }
   * ------------------------------------------------------------- */
  function renderCoverage(target, data) {
    const container = resolveContainer(target);
    if (!container) return;
    container.innerHTML = "";

    const rows = data.rows || [];
    const hasAny = rows.some((r) => Number(r.percent) > 0);

    const wrap = el("div", { class: "fs-coverage" });
    rows.forEach((row) => {
      const pct = Math.max(0, Math.min(100, Number(row.percent) || 0));
      wrap.appendChild(
        el("div", { class: "fs-coverage-row" }, [
          el("div", { class: "fs-coverage-heading" }, [
            el("span", { text: row.label }),
            el("span", { class: "fs-coverage-pct", text: `${pct}%` }),
          ]),
          el("div", { class: "fs-coverage-track" }, [
            el("div", { class: "fs-coverage-fill", style: `width:${pct}%` }),
          ]),
        ])
      );
    });
    container.appendChild(wrap);

    if (!hasAny) {
      container.appendChild(
        el("p", { class: "fs-chart-empty", text: data.emptyText || "No data uploaded yet." })
      );
    }
  }

  /* ---------------------------------------------------------------
   * Gauge — used for the Overall Risk Score (0-100; NOT a "goodness"
   * score). Convention, per the approved Risk Engine (Blueprint
   * Section config.RISK_LEVEL_CUTOFFS): HIGHER SCORE = HIGHER RISK.
   *
   * data: { value, max, label, bands: [{upTo, color}], emptyText }
   *
   * `bands` are evaluated in ascending `upTo` order against the raw
   * score `value` (NOT a max-normalized percentage — the approved
   * cutoffs below are defined in absolute 0-100 terms, and comparing
   * the raw integer avoids floating-point edge cases exactly at a
   * boundary like 29/30 or 79/80). The first band whose `upTo >=
   * value` wins.
   *
   * Default bands mirror config.py's RISK_LEVEL_CUTOFFS exactly:
   *   0-29  = Low      (risk-low,      green)
   *   30-59 = Medium    (risk-medium,   amber)
   *   60-79 = High      (risk-high,     orange)
   *   80-100 = Critical (risk-critical, red)
   * A caller with a non-default `max` should pass its own `bands`,
   * since these defaults assume a 0-100 scale.
   * ------------------------------------------------------------- */
  function renderGauge(target, data) {
    const container = resolveContainer(target);
    if (!container) return;
    container.innerHTML = "";

    const max = Number(data.max) || 100;
    const value = Math.max(0, Math.min(max, Number(data.value) || 0));
    const pct = value / max;

    const size = 200;
    const cx = size / 2;
    const cy = size / 2 + 10;
    const r = 78;
    const strokeWidth = 18;
    const halfCirc = Math.PI * r;

    const bands = data.bands || [
      { upTo: 29, color: "risk-low" },
      { upTo: 59, color: "risk-medium" },
      { upTo: 79, color: "risk-high" },
      { upTo: max, color: "risk-critical" },
    ];
    const band = bands.find((b) => value <= b.upTo) || bands[bands.length - 1];

    const svg = svgEl("svg", {
      viewBox: `0 0 ${size} ${size / 2 + 30}`,
      width: size,
      height: size / 2 + 30,
      role: "img",
      "aria-label": data.ariaLabel || "Gauge chart",
    });

    svg.appendChild(
      svgEl("path", {
        d: `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`,
        fill: "none",
        stroke: "var(--fs-track)",
        "stroke-width": strokeWidth,
        "stroke-linecap": "round",
      })
    );

    if (value > 0) {
      const dash = pct * halfCirc;
      svg.appendChild(
        svgEl("path", {
          d: `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`,
          fill: "none",
          stroke: resolveColor(band.color),
          "stroke-width": strokeWidth,
          "stroke-linecap": "round",
          "stroke-dasharray": `${dash} ${halfCirc - dash}`,
        })
      );

      const needleAngle = -90 + pct * 180;
      const tip = polarToCartesian(cx, cy, r - strokeWidth / 2 - 6, needleAngle);
      svg.appendChild(
        svgEl("line", {
          x1: cx, y1: cy, x2: tip.x, y2: tip.y,
          stroke: "var(--fs-text)",
          "stroke-width": 2,
        })
      );
      svg.appendChild(svgEl("circle", { cx, cy, r: 4, fill: "var(--fs-text)" }));
    }

    container.appendChild(svg);
    container.appendChild(
      el("div", { class: "fs-gauge-wrap" }, [
        el("span", { class: "fs-gauge-value", text: `${value} / ${max}` }),
        el("span", {
          class: "fs-gauge-caption",
          text: value === 0 ? (data.emptyText || "No data yet.") : (data.label || "Overall Score"),
        }),
      ])
    );
  }

  global.FinCharts = {
    renderDonut,
    renderBarChart,
    renderCoverage,
    renderGauge,
  };
})(window);
