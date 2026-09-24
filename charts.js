'use strict';

/* Minimal, dependency-free SVG chart helpers. Each function returns an SVG
 * element ready to be appended to the DOM. No external charting library is
 * used so the app has zero build step and works fully offline. */

const NS = 'http://www.w3.org/2000/svg';

function svgEl(tag, attrs) {
  const el = document.createElementNS(NS, tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  }
  return el;
}

function fmtCompact(n) {
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(n);
  if (abs >= 1e7) return sign + (abs / 1e7).toFixed(2) + 'Cr';
  if (abs >= 1e5) return sign + (abs / 1e5).toFixed(2) + 'L';
  if (abs >= 1e3) return sign + (abs / 1e3).toFixed(1) + 'k';
  return sign + abs.toFixed(0);
}

/**
 * Horizontal grouped bar chart comparing billing vs cost vs profit per
 * manager (or any labelled series).
 * data: [{ label, billing, cost, profit }]
 */
function barChart(data, opts) {
  const width = (opts && opts.width) || 520;
  const rowH = 64;
  const height = data.length * rowH + 30;
  const padLeft = 108;
  const padRight = 20;

  const maxVal = Math.max(1, ...data.map(d => Math.max(d.billing, d.cost)));

  const svg = svgEl('svg', {
    viewBox: `0 0 ${width} ${height}`,
    width: '100%',
    height,
    role: 'img',
    'aria-label': 'Billing and cost by manager',
  });

  data.forEach((d, i) => {
    const y0 = i * rowH + 14;
    const scale = (width - padLeft - padRight) / maxVal;

    const label = svgEl('text', {
      x: 0, y: y0 + 10,
      'font-size': 12.5, fill: '#16232a', 'font-weight': 600,
      'font-family': 'Inter, sans-serif',
    });
    label.textContent = d.label;
    svg.appendChild(label);

    // billing bar
    const bw = Math.max(1, d.billing * scale);
    svg.appendChild(svgEl('rect', {
      x: padLeft, y: y0, width: bw, height: 14, rx: 2, fill: '#0f6b5c',
    }));
    const bLbl = svgEl('text', {
      x: padLeft + bw + 6, y: y0 + 11, 'font-size': 11, fill: '#3c4a51',
      'font-family': 'IBM Plex Mono, monospace',
    });
    bLbl.textContent = fmtCompact(d.billing);
    svg.appendChild(bLbl);

    // cost bar
    const cw = Math.max(1, d.cost * scale);
    const cy = y0 + 20;
    svg.appendChild(svgEl('rect', {
      x: padLeft, y: cy, width: cw, height: 14, rx: 2, fill: '#a9822f',
    }));
    const cLbl = svgEl('text', {
      x: padLeft + cw + 6, y: cy + 11, 'font-size': 11, fill: '#3c4a51',
      'font-family': 'IBM Plex Mono, monospace',
    });
    cLbl.textContent = fmtCompact(d.cost);
    svg.appendChild(cLbl);

    // profit chip
    const pColor = d.profit >= 0 ? '#1e7a4c' : '#a23b2e';
    const pLbl = svgEl('text', {
      x: padLeft, y: cy + 30, 'font-size': 11.5, fill: pColor, 'font-weight': 700,
      'font-family': 'IBM Plex Mono, monospace',
    });
    pLbl.textContent = (d.profit >= 0 ? 'Profit ' : 'Loss ') + fmtCompact(Math.abs(d.profit));
    svg.appendChild(pLbl);
  });

  return svg;
}

/**
 * Donut chart for cost composition.
 * segments: [{ label, value, color }]
 */
function donutChart(segments, opts) {
  const size = (opts && opts.size) || 220;
  const stroke = (opts && opts.stroke) || 26;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;

  const total = segments.reduce((s, d) => s + Math.max(0, d.value), 0);

  const svg = svgEl('svg', {
    viewBox: `0 0 ${size} ${size}`,
    width: size, height: size,
    role: 'img',
    'aria-label': 'Cost composition',
  });

  svg.appendChild(svgEl('circle', {
    cx, cy, r, fill: 'none', stroke: '#e6e9e2', 'stroke-width': stroke,
  }));

  let offset = 0;
  if (total > 0) {
    segments.forEach(seg => {
      const value = Math.max(0, seg.value);
      if (value <= 0) return;
      const frac = value / total;
      const len = frac * circumference;
      const circle = svgEl('circle', {
        cx, cy, r, fill: 'none', stroke: seg.color, 'stroke-width': stroke,
        'stroke-dasharray': `${len} ${circumference - len}`,
        'stroke-dashoffset': -offset,
        transform: `rotate(-90 ${cx} ${cy})`,
        'stroke-linecap': 'butt',
      });
      svg.appendChild(circle);
      offset += len;
    });
  } else {
    svg.appendChild(svgEl('text', {
      x: cx, y: cy, 'text-anchor': 'middle', 'dominant-baseline': 'middle',
      'font-size': 12, fill: '#64726f', 'font-family': 'Inter, sans-serif',
    })).textContent = 'No cost yet';
  }

  const centerLabel = svgEl('text', {
    x: cx, y: cy - 4, 'text-anchor': 'middle', 'font-size': 12, fill: '#64726f',
    'font-family': 'Inter, sans-serif',
  });
  centerLabel.textContent = 'Total cost';
  svg.appendChild(centerLabel);

  const centerValue = svgEl('text', {
    x: cx, y: cy + 16, 'text-anchor': 'middle', 'font-size': 15, fill: '#16232a',
    'font-weight': 700, 'font-family': 'IBM Plex Mono, monospace',
  });
  centerValue.textContent = fmtCompact(total);
  svg.appendChild(centerValue);

  return svg;
}

window.Charts = { barChart, donutChart, fmtCompact };
