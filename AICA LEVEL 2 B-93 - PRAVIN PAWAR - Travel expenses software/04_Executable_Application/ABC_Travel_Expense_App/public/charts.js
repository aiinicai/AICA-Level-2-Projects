/* Lightweight SVG charts (no external libraries) for ABC Travel & Expense */
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const inr = (n) => '₹' + Math.round(n).toLocaleString('en-IN');
  const compact = (n) => {
    const a = Math.abs(n);
    if (a >= 1e7) return '₹' + (n / 1e7).toFixed(a >= 1e8 ? 0 : 1) + 'Cr';
    if (a >= 1e5) return '₹' + (n / 1e5).toFixed(a >= 1e6 ? 0 : 1) + 'L';
    if (a >= 1e3) return '₹' + (n / 1e3).toFixed(a >= 1e4 ? 0 : 1) + 'K';
    return '₹' + Math.round(n);
  };
  function niceMax(v) {
    if (v <= 0) return 1;
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    const m = v / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
  }
  function tipLayer(el) {
    el.style.position = 'relative';
    let tip = el.querySelector('.chart-tip');
    if (!tip) { tip = document.createElement('div'); tip.className = 'chart-tip hidden'; el.appendChild(tip); }
    return {
      show(html, x, y) { tip.innerHTML = html; tip.style.left = x + 'px'; tip.style.top = y + 'px'; tip.classList.remove('hidden'); },
      hide() { tip.classList.add('hidden'); },
    };
  }
  function empty(el, msg) { el.innerHTML = `<div class="empty">${esc(msg || 'No data yet for this period.')}</div>`; }

  /* Horizontal bar chart: data = [{label, value, extra}] */
  function hbar(el, data, opt = {}) {
    const fmt = opt.format || inr;
    data = (data || []).slice(0, opt.max || 10);
    if (!data.length) return empty(el);
    const W = 470, rowH = 28, labelW = opt.labelW || 118, valW = 74, top = 6;
    const H = top + data.length * rowH + 6;
    const max = niceMax(Math.max(...data.map((d) => d.value)));
    const plotW = W - labelW - valW;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opt.title || 'bar chart')}">`;
    data.forEach((d, i) => {
      const y = top + i * rowH;
      const w = Math.max(5, (d.value / max) * plotW);
      const mc = opt.maxChars || 18; const lab = d.label.length > mc ? d.label.slice(0, mc - 1) + '…' : d.label;
      s += `<text x="${labelW - 8}" y="${y + rowH / 2 + 4}" text-anchor="end">${esc(lab)}</text>`;
      s += `<path class="bar" data-i="${i}" d="M${labelW},${y + 6} h${w - 4} a4,4 0 0 1 4,4 v${rowH - 20} a4,4 0 0 1 -4,4 h-${w - 4} z"/>`;
      s += `<text x="${labelW + w + 6}" y="${y + rowH / 2 + 4}" style="font-weight:600">${esc(fmt(d.value))}</text>`;
      s += `<rect data-i="${i}" x="0" y="${y}" width="${W}" height="${rowH}" fill="transparent" class="hit"/>`;
    });
    s += '</svg>';
    el.innerHTML = s;
    const tip = tipLayer(el);
    el.querySelectorAll('.hit').forEach((r) => {
      r.addEventListener('mousemove', (ev) => {
        const d = data[+r.dataset.i];
        el.querySelectorAll('.bar').forEach((b) => b.classList.toggle('hl', b.dataset.i === r.dataset.i));
        const box = el.getBoundingClientRect();
        tip.show(`<b>${esc(d.label)}</b><br>${esc(fmt(d.value))}${d.extra ? '<br>' + esc(d.extra) : ''}`, ev.clientX - box.left, ev.clientY - box.top);
      });
      r.addEventListener('mouseleave', () => { tip.hide(); el.querySelectorAll('.bar').forEach((b) => b.classList.remove('hl')); });
    });
  }

  /* Vertical column / line chart over categories: data=[{label,value,extra}] */
  function column(el, data, opt = {}) {
    const fmt = opt.format || inr; const axisFmt = opt.axisFormat || compact;
    data = data || [];
    if (!data.length) return empty(el);
    const W = 480, H = 230, L = 50, R = 10, T = 14, B = 30;
    const max = niceMax(Math.max(...data.map((d) => d.value)));
    const pw = W - L - R, ph = H - T - B;
    const bw = pw / data.length;
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(opt.title || 'chart')}">`;
    for (let i = 0; i <= 4; i++) {
      const y = T + ph - (ph * i) / 4;
      s += `<line class="gridline" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/>`;
      s += `<text x="${L - 6}" y="${y + 4}" text-anchor="end">${esc(axisFmt((max * i) / 4))}</text>`;
    }
    const step = Math.ceil(data.length / 7);
    if (opt.line) {
      const pts = data.map((d, i) => [L + bw * i + bw / 2, T + ph - (d.value / max) * ph]);
      s += `<path class="line" d="${pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ')}"/>`;
      pts.forEach((p, i) => { s += `<circle class="pt" cx="${p[0]}" cy="${p[1]}" r="4.5"/>`; void i; });
    }
    data.forEach((d, i) => {
      const x = L + bw * i;
      if (!opt.line) {
        const h = Math.max(5, (d.value / max) * ph);
        const bwi = Math.min(46, bw * 0.62);
        const bx = x + (bw - bwi) / 2, by = T + ph - h;
        if (d.value > 0) s += `<path class="bar" data-i="${i}" d="M${bx},${T + ph} v-${h - 4} a4,4 0 0 1 4,-4 h${bwi - 8} a4,4 0 0 1 4,4 v${h - 4} z"/>`;
      }
      if (i % step === 0) s += `<text x="${x + bw / 2}" y="${H - B + 16}" text-anchor="middle">${esc(d.label)}</text>`;
      s += `<rect class="hit" data-i="${i}" x="${x}" y="${T}" width="${bw}" height="${ph}" fill="transparent"/>`;
    });
    s += `<line class="gridline" x1="${L}" x2="${W - R}" y1="${T + ph}" y2="${T + ph}" style="stroke:var(--text-2)"/>`;
    s += '</svg>';
    el.innerHTML = s;
    const tip = tipLayer(el);
    el.querySelectorAll('.hit').forEach((r) => {
      r.addEventListener('mousemove', (ev) => {
        const d = data[+r.dataset.i];
        el.querySelectorAll('.bar').forEach((b) => b.classList.toggle('hl', b.dataset.i === r.dataset.i));
        const box = el.getBoundingClientRect();
        tip.show(`<b>${esc(d.label)}</b><br>${esc(fmt(d.value))}${d.extra ? '<br>' + esc(d.extra) : ''}`, ev.clientX - box.left, ev.clientY - box.top);
      });
      r.addEventListener('mouseleave', () => { tip.hide(); el.querySelectorAll('.bar').forEach((b) => b.classList.remove('hl')); });
    });
  }
  window.Charts = { hbar, column, inr, compact };
})();
