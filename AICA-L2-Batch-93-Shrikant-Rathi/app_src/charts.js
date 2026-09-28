/* ==================================================================
   Charts — hand-built SVG, one scale per chart, hover layer by default.
   Colours come from CSS tokens so both themes work.
   ================================================================== */
const CHARTS = {};
const CW = { full: 900, half: 520, two: 640, third: 360 };
function avail(frac = 1) {
  const el = document.getElementById("content"), pad = innerWidth <= 900 ? 32 : 56, gap = 16;
  const w = (el ? el.clientWidth : innerWidth) - pad;
  if ((frac === 0.5 && innerWidth <= 900) || (frac !== 0.5 && frac < 1 && innerWidth <= 1100)) frac = 1;
  const cw = frac === 1 ? w : (w - gap) * frac;
  return Math.max(280, Math.floor(cw - 38));
}
function measure() { CW.full = avail(1); CW.half = avail(0.5); CW.two = avail(2 / 3); CW.third = avail(1 / 3); }
let chartSeq = 0;
function niceTicks(min, max, n = 5) {
  if (min === max) { max = min + 1; }
  const span = max - min, step0 = span / n, p = Math.pow(10, Math.floor(Math.log10(step0))), f = step0 / p;
  const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p;  // no 2.5 step: axis labels print whole numbers, so 12.5% would read "13%"
  const lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step, out = [];
  for (let v = lo; v <= hi + step / 2; v += step) out.push(+v.toFixed(10));
  return out;
}
/** Axis ticks whose labels fit the space: a narrow (phone) chart gets fewer ticks instead of labels printed over each other. */
function fitTicks(lo, hi, px, fmt, n = 4) {
  let t;
  for (let k = n; k >= 1; k--) {
    t = niceTicks(lo, hi, k);
    const w = Math.max(...t.map(v => String(fmt(v)).length)) * 6.6 + 12;
    if (px / Math.max(1, t.length - 1) >= w) return t;
  }
  return t;
}
/** Keep an axis label inside the chart: the first and last labels are anchored inwards when centring would cut them. */
const tickAnchor = (x, txt, W) => { const h = String(txt).length * 3.4; return x - h < 0 ? "start" : x + h > W ? "end" : "middle"; };
const tipAttr = html => `data-tip="${esc(html)}"`;

/** Multi-series line chart with crosshair tooltip. */
function lineChart({ series, labels, yFmt = v => fmtN(v, 0), height = 260, area = false, zero = false, xEvery, legend = true, yTitle = "", W = CW.half, yMin = null, yMax = null }) {
  const id = "c" + (++chartSeq), H = height, R = 16, Tp = yTitle ? 26 : 14, B = 30;
  const all = series.flatMap(s => s.values.filter(isNum));
  let lo = Math.min(...all), hi = Math.max(...all);
  if (zero) { lo = Math.min(0, lo); hi = Math.max(0, hi); }
  const pad = (hi - lo) * 0.06; const ticks = yMin != null ? niceTicks(yMin, yMax, 5) : niceTicks(area ? Math.min(lo, 0) : (zero && lo >= 0 ? 0 : lo - pad), hi + pad, 5);
  const y0 = ticks[0], y1 = ticks[ticks.length - 1], n = labels.length;
  const L = Math.max(44, 14 + 6.6 * Math.max(...ticks.map(t => String(yFmt(t)).length)));  // room for the widest y label
  const sx = i => L + (W - L - R) * (n === 1 ? 0.5 : i / (n - 1)), sy = v => Tp + (H - Tp - B) * (1 - (v - y0) / (y1 - y0));
  const lw = Math.max(...labels.map(l => String(l).length)) * 6.6 + 14;  // pixels one x label needs
  const every = Math.max(xEvery || 1, Math.ceil(n / Math.max(2, Math.floor((W - L - R) / lw))));
  let s = `<svg class="chart" data-chart="${id}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(series.map(x => x.name).join(", "))}">`;
  ticks.forEach(t => s += `<line class="grid" x1="${L}" x2="${W - R}" y1="${sy(t)}" y2="${sy(t)}"/><text class="tick" x="${L - 8}" y="${sy(t) + 4}" text-anchor="end">${esc(yFmt(t))}</text>`);
  if (zero && y0 < 0) s += `<line class="axis" x1="${L}" x2="${W - R}" y1="${sy(0)}" y2="${sy(0)}"/>`;
  labels.forEach((l, i) => { if ((i % every === 0 && sx(n - 1) - sx(i) >= lw) || i === n - 1) s += `<text class="tick" x="${sx(i)}" y="${H - 8}" text-anchor="${i === n - 1 && n > 1 ? "end" : i === 0 ? "start" : "middle"}">${esc(l)}</text>`; });
  if (yTitle) s += `<text class="tick" x="4" y="13">${esc(yTitle)}</text>`;
  series.forEach((se, k) => {
    const pts = se.values.map((v, i) => isNum(v) ? `${sx(i).toFixed(1)},${sy(v).toFixed(1)}` : null).filter(Boolean);
    if (area && k === 0) s += `<path d="M${pts[0]} L${pts.join(" L")} L${sx(n - 1)},${sy(Math.max(y0, 0))} L${sx(0)},${sy(Math.max(y0, 0))} Z" style="fill:${se.color};opacity:.10"/>`;
    s += `<polyline points="${pts.join(" ")}" style="fill:none;stroke:${se.color};stroke-width:${se.width || 2};${se.dash ? "stroke-dasharray:5 4;" : ""}stroke-linejoin:round;stroke-linecap:round"/>`;
    const lv = se.values[n - 1]; if (isNum(lv)) s += `<circle cx="${sx(n - 1)}" cy="${sy(lv)}" r="3.5" style="fill:${se.color};stroke:var(--surface);stroke-width:2"/>`;
  });
  s += `<g class="hover" style="display:none"><line class="xhair" y1="${Tp}" y2="${H - B}"/>${series.map(se => `<circle r="4" style="fill:${se.color};stroke:var(--surface);stroke-width:2"/>`).join("")}</g>`;
  s += `<rect class="hit" x="${L}" y="${Tp}" width="${W - L - R}" height="${H - Tp - B}" style="fill:transparent"/></svg>`;
  CHARTS[id] = { type: "line", W, L, R, n, sx, sy, series, labels, yFmt };
  const lg = legend && series.length > 1 ? `<div class="legend">${series.map(se => `<span><i class="sw ${se.dash ? "dash" : ""}" style="background:${se.color}"></i>${esc(se.name)}</span>`).join("")}</div>` : "";
  return lg + s;
}

/** Horizontal bars; each row may carry stacked segments. Optional limit line. */
function barH({ rows, fmt = v => fmtN(v, 1), limit = null, limitLabel = "", labelW = 190, W = CW.half, rowH = 26, max = null, valueText, ticksFmt }) {
  const stack = W < 420, LH = stack ? 16 : 0;  // phone: label row above each bar
  if (stack) labelW = 2;
  else labelW = Math.max(labelW, Math.min(Math.max(...rows.map(r => String(r.label).length)) * 6.8 + 14, Math.floor(W * 0.36)));  // wide charts (tablet portrait) show whole names
  const Tp = limit != null ? 20 : 6, H = Tp + rows.length * (rowH + LH) + 24, plotW = W - labelW - 70;
  const tot = r => r.segs.reduce((s, x) => s + Math.max(0, x.v), 0);
  const mx = max ?? Math.max(limit || 0, ...rows.map(tot)) * 1.04;
  const tf = ticksFmt || fmt, ticks = fitTicks(0, mx, plotW, tf, 4), top = ticks[ticks.length - 1], sx = v => v / top * plotW;
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img">`;
  ticks.forEach(t => s += `<line class="grid" x1="${labelW + sx(t)}" x2="${labelW + sx(t)}" y1="${Tp}" y2="${H - 20}"/><text class="tick" x="${labelW + sx(t)}" y="${H - 5}" text-anchor="${tickAnchor(labelW + sx(t), tf(t), W)}">${esc(tf(t))}</text>`);
  rows.forEach((r, i) => {
    const y0 = Tp + i * (rowH + LH), y = y0 + LH - (stack ? 3 : 0); let x = labelW;  // phone: the name sits tight on its own bar
    s += stack ? `<text class="lbl lbl-over" x="0" y="${y0 + 15}">${esc(fitLabel(r.label, Math.floor(W / 6.8)))}</text>`
      : `<text class="lbl" x="${labelW - 10}" y="${y + rowH / 2 + 4}" text-anchor="end">${esc(fitLabel(r.label, Math.floor((labelW - 12) / 6.8)))}</text>`;
    r.segs.forEach((g, j) => {
      const w = Math.max(0, sx(Math.max(0, g.v)) - (j < r.segs.length - 1 ? 1 : 0));
      if (w > 0) s += `<rect x="${x}" y="${y + 6}" width="${w}" height="${rowH - 12}" rx="${j === r.segs.length - 1 ? 3 : 0}" style="fill:${g.color}" ${tipAttr(`<b>${esc(r.label)}</b><br>${g.name ? g.name + ": " : ""}${fmt(g.v)}${r.tip ? "<br>" + r.tip : ""}`)}/>`;
      x += sx(Math.max(0, g.v));
    });
    s += `<text class="val" x="${x + 6}" y="${y + rowH / 2 + 4}">${esc(valueText ? valueText(r) : fmt(tot(r)))}</text>`;
  });
  if (limit != null) s += `<line class="limit" x1="${labelW + sx(limit)}" x2="${labelW + sx(limit)}" y1="${Tp - 4}" y2="${H - 20}"/><text class="limit-t" x="${labelW + sx(limit)}" y="12" text-anchor="${tickAnchor(labelW + sx(limit), limitLabel, W)}">${esc(limitLabel)}</text>`;
  return s + `</svg>`;
}

/** Diverging horizontal bars around zero (active weights, stress contributions). */
function divBar({ rows, fmt = v => fmtSPct(v), labelW = 190, W = CW.half, rowH = 24, pos = "var(--pos)", neg = "var(--neg)" }) {
  const stack = W < 420, LH = stack ? 16 : 0;  // phone: label row above each bar
  if (stack) labelW = 0;
  else labelW = Math.max(labelW, Math.min(Math.max(...rows.map(r => String(r.label).length)) * 6.8 + 14, Math.floor(W * 0.36)));
  const hasNeg = rows.some(r => r.v < 0), hasPos = rows.some(r => r.v > 0);
  const Tp = 6, H = Tp + rows.length * (rowH + LH) + 24, plotL = labelW + (hasNeg && hasPos ? 56 : 8), plotR = W - 62;
  const mn = Math.min(0, ...rows.map(r => r.v)), mx = Math.max(0, ...rows.map(r => r.v));
  const tf = t => t === 0 ? "0" : fmt(t), ticks = fitTicks(mn * 1.05, mx * 1.05 || (mn ? 0 : 1), plotR - plotL, tf, 4);
  const lo = ticks[0], hi = ticks[ticks.length - 1], sx = v => plotL + (v - lo) / (hi - lo || 1) * (plotR - plotL);
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img">`;
  ticks.forEach(t => s += `<line class="grid" x1="${sx(t)}" x2="${sx(t)}" y1="${Tp}" y2="${H - 20}"/><text class="tick" x="${sx(t)}" y="${H - 5}" text-anchor="${tickAnchor(sx(t), tf(t), W)}">${esc(tf(t))}</text>`);
  s += `<line class="axis" x1="${sx(0)}" x2="${sx(0)}" y1="${Tp}" y2="${H - 20}"/>`;
  rows.forEach((r, i) => {
    const y0 = Tp + i * (rowH + LH), y = y0 + LH - (stack ? 3 : 0), x0 = sx(Math.min(0, r.v)), w = Math.abs(sx(r.v) - sx(0));
    s += stack ? `<text class="lbl lbl-over" x="0" y="${y0 + 15}">${esc(fitLabel(r.label, Math.floor(W / 6.8)))}</text>`
      : `<text class="lbl" x="${labelW - 10}" y="${y + rowH / 2 + 4}" text-anchor="end">${esc(fitLabel(r.label, Math.floor((labelW - 12) / 6.8)))}</text>`;
    s += `<rect x="${x0}" y="${y + 5}" width="${Math.max(1, w)}" height="${rowH - 10}" rx="2" style="fill:${r.v >= 0 ? pos : neg}" ${tipAttr(`<b>${esc(r.label)}</b><br>${fmt(r.v)}${r.tip ? "<br>" + r.tip : ""}`)}/>`;
    const onRight = r.v >= 0 || !hasPos;
    const tx = r.v >= 0 ? sx(r.v) + 5 : hasPos ? sx(r.v) - 5 : sx(0) + 6;
    s += `<text class="val" x="${tx}" y="${y + rowH / 2 + 4}" text-anchor="${onRight ? "start" : "end"}">${esc(fmt(r.v))}</text>`;
  });
  return s + `</svg>`;
}

/** Grouped vertical columns (e.g. 6 fiscal years × 2 series). */
function colChart({ labels, series, fmt = v => fmtN(v, 0), height = 220, W = CW.half }) {
  const H = height, R = 10, Tp = 12, B = 28;
  const all = series.flatMap(s => s.values.filter(isNum));
  const ticks = niceTicks(Math.min(0, ...all), Math.max(0, ...all), 4), y0 = ticks[0], y1 = ticks[ticks.length - 1];
  const L = Math.max(44, 14 + 6.6 * Math.max(...ticks.map(t => String(fmt(t)).length)));
  const sy = v => Tp + (H - Tp - B) * (1 - (v - y0) / (y1 - y0));
  const gw = (W - L - R) / labels.length, bw = Math.min(26, (gw - 12) / series.length);
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img">`;
  ticks.forEach(t => s += `<line class="grid" x1="${L}" x2="${W - R}" y1="${sy(t)}" y2="${sy(t)}"/><text class="tick" x="${L - 8}" y="${sy(t) + 4}" text-anchor="end">${esc(fmt(t))}</text>`);
  labels.forEach((l, i) => {
    const gx = L + i * gw + (gw - bw * series.length - 2 * (series.length - 1)) / 2;
    series.forEach((se, k) => {
      const v = se.values[i]; if (!isNum(v)) return;
      const y = sy(Math.max(0, v)), h = Math.abs(sy(v) - sy(0));
      s += `<rect x="${gx + k * (bw + 2)}" y="${y}" width="${bw}" height="${Math.max(1, h)}" rx="3" style="fill:${se.color}" ${tipAttr(`<b>${esc(l)}</b><br>${esc(se.name)}: ${fmt(v)}`)}/>`;
    });
    s += `<text class="tick" x="${L + i * gw + gw / 2}" y="${H - 9}" text-anchor="middle">${esc(l)}</text>`;
  });
  s += `<line class="axis" x1="${L}" x2="${W - R}" y1="${sy(0)}" y2="${sy(0)}"/>`;
  const lg = series.length > 1 ? `<div class="legend">${series.map(se => `<span><i class="sw" style="background:${se.color}"></i>${esc(se.name)}</span>`).join("")}</div>` : "";
  return lg + s + `</svg>`;
}

/** Scatter with labelled highlights. */
function scatter({ points, xFmt, yFmt, xTitle, yTitle, height = 320, W = CW.two }) {
  const H = height, L = 60, R = 20, Tp = 16, B = 40;
  const xs = points.map(p => p.x), ys = points.map(p => p.y);
  const xt = niceTicks(Math.min(...xs), Math.max(...xs), 5), yt = niceTicks(Math.min(...ys), Math.max(...ys), 5);
  const sx = v => L + (W - L - R) * (v - xt[0]) / (xt[xt.length - 1] - xt[0]), sy = v => Tp + (H - Tp - B) * (1 - (v - yt[0]) / (yt[yt.length - 1] - yt[0]));
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img">`;
  yt.forEach(t => s += `<line class="grid" x1="${L}" x2="${W - R}" y1="${sy(t)}" y2="${sy(t)}"/><text class="tick" x="${L - 8}" y="${sy(t) + 4}" text-anchor="end">${esc(yFmt(t))}</text>`);
  xt.forEach(t => s += `<line class="grid" x1="${sx(t)}" x2="${sx(t)}" y1="${Tp}" y2="${H - B}"/><text class="tick" x="${sx(t)}" y="${H - B + 16}" text-anchor="middle">${esc(xFmt(t))}</text>`);
  s += `<text class="tick" x="${(L + W - R) / 2}" y="${H - 4}" text-anchor="middle">${esc(xTitle)}</text><text class="tick" x="${L}" y="12">${esc(yTitle)}</text>`;
  points.sort((a, b) => (a.hl ? 1 : 0) - (b.hl ? 1 : 0)).forEach(p => {
    s += `<circle cx="${sx(p.x)}" cy="${sy(p.y)}" r="${p.hl ? 7 : 5.5}" style="fill:${p.color};stroke:var(--surface);stroke-width:2;${p.hl ? "" : "opacity:.75"}" ${tipAttr(`<b>${esc(p.label)}</b><br>${xTitle}: ${xFmt(p.x)}<br>${yTitle}: ${yFmt(p.y)}${p.tip ? "<br>" + p.tip : ""}`)} ${p.click ? `data-click="${esc(p.click)}" style="cursor:pointer"` : ""}/>`;
    if (p.hl) s += `<text class="lbl" x="${sx(p.x) + 10}" y="${sy(p.y) + 4}">${esc(p.label)}</text>`;
  });
  return s + `</svg>`;
}

/** Shorten a label to n characters at a word boundary ("Sun Pharmaceutical Industries" -> "Sun Pharmaceutical…"). */
function fitText(t, n) {
  if (t.length <= n) return t;
  if (n < 4) return "";
  const cut = t.slice(0, n - 1), sp = cut.lastIndexOf(" ");
  return (sp >= Math.min(6, n - 2) ? cut.slice(0, sp) : cut).replace(/[\s,&·-]+$/, "") + "…";
}
/** Squarified treemap. */
function treemap({ items, W = CW.full, H = 380, colorFn, labelFn }) {
  const total = items.reduce((s, x) => s + x.value, 0), rects = [];
  const area = items.map(x => ({ ...x, a: x.value / total * W * H })).sort((a, b) => b.a - a.a);
  let x = 0, y = 0, w = W, h = H, row = [];
  const worst = (r, side) => { const s = r.reduce((t, i) => t + i.a, 0), mx = Math.max(...r.map(i => i.a)), mn = Math.min(...r.map(i => i.a)); return Math.max(side * side * mx / (s * s), s * s / (side * side * mn)); };
  const layout = r => {
    const s = r.reduce((t, i) => t + i.a, 0);
    if (w >= h) { const cw = s / h; let yy = y; r.forEach(i => { const ch = i.a / cw; rects.push({ ...i, x, y: yy, w: cw, h: ch }); yy += ch; }); x += cw; w -= cw; }
    else { const rh = s / w; let xx = x; r.forEach(i => { const cw = i.a / rh; rects.push({ ...i, x: xx, y, w: cw, h: rh }); xx += cw; }); y += rh; h -= rh; }
  };
  area.forEach(it => { const side = Math.min(w, h); if (!row.length || worst([...row, it], side) <= worst(row, side)) row.push(it); else { layout(row); row = [it]; } });
  if (row.length) layout(row);
  let s = `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img">`;
  rects.forEach(r => {
    s += `<rect x="${r.x + 1}" y="${r.y + 1}" width="${Math.max(0, r.w - 2)}" height="${Math.max(0, r.h - 2)}" rx="3" style="fill:${colorFn(r)}" ${tipAttr(r.tip)} ${r.click ? `data-click="${esc(r.click)}"` : ""} class="tm"/>`;
    let [a, b] = labelFn(r); const fit = n => Math.floor((r.w - 14) / n);
    const o = r.other ? " o" : "";  // light "other" box: dark text
    const n = fit(6.8);
    if (a.length > n) a = compactName(a);  // standard short forms before any cut: "Sun Pharma Inds", "Tata Consultancy"
    // a word would be cut in the middle ("Hindust… Aero", "Tata Consul…"): show the NSE symbol instead (full name in the tooltip)
    const whole = new Set(a.split(" ")), midCut = t => /…$/.test(t) && !whole.has(t.slice(0, -1).split(" ").pop());
    if (a.length > n && r.code && r.code.length * 8.6 <= r.w - 14) {  // capitals in bold run ~8.6px each
      const w0 = a.split(" "); let l1 = ""; while (w0.length && (l1 + " " + w0[0]).trim().length <= n) l1 = (l1 + " " + w0.shift()).trim();
      const tall = r.h > 52, rest = w0.join(" ");
      if (!l1 || (tall ? midCut(fitText(rest, n)) : midCut(fitText(a, n)) || fitText(a, n).split(" ").length < 2)) a = r.code;
    }
    if (r.w > 58 && r.h > 52 && a.length > n && a.split(" ")[0].length <= n) {
      // a tall box: the name wraps onto a second line instead of being cut ("Hindustan / Aeronautics")
      const words = a.split(" "); let l1 = "";
      while (words.length && (l1 + " " + words[0]).trim().length <= n) l1 = (l1 + " " + words.shift()).trim();
      if (!l1) l1 = fitText(words.shift(), n);
      let l2 = fitText(words.join(" "), n);
      if (midCut(l2)) { let k = ""; for (const w of words) { if ((k + " " + w).trim().length > n - 1) break; k = (k + " " + w).trim(); } l2 = k ? k + "…" : ""; }  // whole words only: "Grid…", never "Grid Cor…"
      s += l2 ? `<text class="tm-t${o}" x="${r.x + 8}" y="${r.y + 18}">${esc(l1)}</text><text class="tm-t${o}" x="${r.x + 8}" y="${r.y + 33}">${esc(l2)}</text><text class="tm-s${o}" x="${r.x + 8}" y="${r.y + 48}">${esc(b)}</text>`
        // no whole word fits a second line: "Kotak…" then the weight directly under it (no blank line between)
        : `<text class="tm-t${o}" x="${r.x + 8}" y="${r.y + 18}">${esc(l1.length < n ? l1 + "…" : l1)}</text><text class="tm-s${o}" x="${r.x + 8}" y="${r.y + 33}">${esc(b)}</text>`;
    } else if (r.w > 58 && r.h > 34 && !midCut(fitText(a, n))) s += `<text class="tm-t${o}" x="${r.x + 8}" y="${r.y + 18}">${esc(fitText(a, n))}</text><text class="tm-s${o}" x="${r.x + 8}" y="${r.y + 33}">${esc(b)}</text>`;
    else if (r.w > 34 && r.h > 18) s += `<text class="tm-s${o}" x="${r.x + 6}" y="${r.y + 15}">${esc(b)}</text>`;  // too small for a name: its weight (the name is in the tooltip)
  });
  return s + `</svg>`;
}
/** Sequential & diverging fills built from tokens with color-mix. */
const tmFill = t => `color-mix(in srgb, var(--tm-hi) ${Math.round(Math.max(0, Math.min(1, t)) * 100)}%, var(--tm-lo))`;  // treemap boxes: white text readable at every weight, both themes
/** Text colour for a seqFill(t) cell: white or black, whichever contrasts more with that exact fill in the current theme
 *  (a fixed "t > 0.5" cut-off put white on mid blues in light mode and on light blues in dark mode). */
function seqInk(t) {
  const cs = getComputedStyle(document.documentElement), hex = v => { const m = cs.getPropertyValue(v).trim().match(/^#([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i); return m ? m.slice(1).map(x => parseInt(x, 16)) : null; };
  const hi = hex("--seq-hi"), lo = hex("--seq-lo"); if (!hi || !lo) return t > 0.5 ? "#fff" : "var(--ink)";
  const k = Math.max(0.06, Math.min(1, t)), L = hi.map((h, i) => h * k + lo[i] * (1 - k)).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }).reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0);
  return 1.05 / (L + 0.05) >= (L + 0.05) / 0.05 ? "#fff" : "#000";
}
const seqFill = t => `color-mix(in srgb, var(--seq-hi) ${Math.round(Math.max(0.06, Math.min(1, t)) * 100)}%, var(--seq-lo))`;
const divFill = t => t >= 0 ? `color-mix(in srgb, var(--pos) ${Math.round(Math.min(1, t) * 85)}%, var(--mid))` : `color-mix(in srgb, var(--neg) ${Math.round(Math.min(1, -t) * 85)}%, var(--mid))`;
function rangeBar(lo, hi, cur) {
  const p = hi > lo ? (cur - lo) / (hi - lo) * 100 : 50;
  return `<div class="range" ${tipAttr(`52-week low ₹${fmtN(lo)} · high ₹${fmtN(hi)} · now ₹${fmtN(cur)}`)}><div class="range-track"><i style="left:${p}%"></i></div><div class="range-l"><span>₹${fmtN(lo, 0)}</span><span>₹${fmtN(hi, 0)}</span></div></div>`;
}
function spark(values, color = "var(--s1)") {
  const W = 90, H = 24, lo = Math.min(...values), hi = Math.max(...values);
  const pts = values.map((v, i) => `${(i / (values.length - 1) * W).toFixed(1)},${(H - 2 - (v - lo) / (hi - lo || 1) * (H - 4)).toFixed(1)}`).join(" ");
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" aria-hidden="true"><polyline points="${pts}" style="fill:none;stroke:${color};stroke-width:1.5"/></svg>`;
}

/* ---------- hover layer for line charts ---------- */
document.addEventListener("mousemove", e => {
  const svg = e.target.closest && e.target.closest("svg[data-chart]");
  $$("svg[data-chart] .hover").forEach(g => { if (!svg || !svg.contains(g)) g.style.display = "none"; });
  if (!svg) return;
  const c = CHARTS[svg.dataset.chart]; if (!c) return;
  const rect = svg.getBoundingClientRect(), vx = (e.clientX - rect.left) * c.W / rect.width;
  const i = Math.max(0, Math.min(c.n - 1, Math.round((vx - c.L) / ((c.W - c.L - c.R) / Math.max(1, c.n - 1)))));
  const g = $(".hover", svg); g.style.display = "";
  $(".xhair", g).setAttribute("x1", c.sx(i)); $(".xhair", g).setAttribute("x2", c.sx(i));
  $$("circle", g).forEach((ci, k) => { const v = c.series[k].values[i]; if (isNum(v)) { ci.setAttribute("cx", c.sx(i)); ci.setAttribute("cy", c.sy(v)); ci.style.display = ""; } else ci.style.display = "none"; });
  showTip(`<b>${esc(c.labels[i])}</b>` + c.series.map(se => `<div class="tip-row"><i class="sw ${se.dash ? "dash" : ""}" style="background:${se.color}"></i>${esc(se.name)}<b>${esc(c.yFmt(se.values[i]))}</b></div>`).join(""), e);
});
document.addEventListener("mouseover", e => { const t = e.target.closest && e.target.closest("[data-tip]"); if (t) showTip(t.getAttribute("data-tip"), e); });
document.addEventListener("mouseout", e => { const t = e.target.closest && (e.target.closest("[data-tip]") || e.target.closest("svg[data-chart]")); if (t && !t.contains(e.relatedTarget)) hideTip(); });
// touch screens have no hover: a tap (or click) on an ⓘ shows its note and does nothing else, so an ⓘ inside a
// sortable column heading explains the column instead of re-sorting the table; a tap anywhere else closes it
document.addEventListener("click", e => {
  const i = e.target.closest && e.target.closest(".i[data-tip]");
  if (i) { e.preventDefault(); e.stopPropagation(); showTip(i.getAttribute("data-tip"), e); return; }
  if (!(e.target.closest && e.target.closest("[data-tip], svg[data-chart], #tip"))) hideTip();
}, true);
function showTip(html, e) {
  const t = $("#tip"); t.innerHTML = html; t.hidden = false;
  const r = t.getBoundingClientRect(); let x = e.clientX + 14, y = e.clientY + 14;
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14; if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
  t.style.left = x + "px"; t.style.top = y + "px";
}
function hideTip() { const t = $("#tip"); if (t) t.hidden = true; }
