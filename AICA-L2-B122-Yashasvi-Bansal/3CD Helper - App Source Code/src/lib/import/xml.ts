// Tiny dependency-free XML parser. Works inside Web Workers (where DOMParser is unavailable)
// and tolerates the quirks of Tally exports (invalid char refs, UTF-16 text already decoded).

export interface XNode {
  name: string;
  attrs: Record<string, string>;
  children: XNode[];
  text: string;
}

const ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };

function decode(s: string): string {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e: string) => {
    if (e[0] === "#") {
      const code = e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      if (!code || code < 32) return code === 9 || code === 10 || code === 13 ? String.fromCharCode(code) : "";
      try { return String.fromCodePoint(code); } catch { return ""; }
    }
    return ENTITIES[e.toLowerCase()] ?? m;
  });
}

export function parseXml(src: string): XNode {
  const root: XNode = { name: "#root", attrs: {}, children: [], text: "" };
  const stack: XNode[] = [root];
  let i = 0;
  const n = src.length;
  while (i < n) {
    const lt = src.indexOf("<", i);
    if (lt === -1) { stack[stack.length - 1].text += decode(src.slice(i)); break; }
    if (lt > i) stack[stack.length - 1].text += decode(src.slice(i, lt));
    if (src.startsWith("<!--", lt)) { const e = src.indexOf("-->", lt); i = e === -1 ? n : e + 3; continue; }
    if (src.startsWith("<![CDATA[", lt)) {
      const e = src.indexOf("]]>", lt);
      stack[stack.length - 1].text += src.slice(lt + 9, e === -1 ? n : e);
      i = e === -1 ? n : e + 3; continue;
    }
    if (src[lt + 1] === "?" || src[lt + 1] === "!") { const e = src.indexOf(">", lt); i = e === -1 ? n : e + 1; continue; }
    const gt = src.indexOf(">", lt);
    if (gt === -1) break;
    const raw = src.slice(lt + 1, gt);
    i = gt + 1;
    if (raw[0] === "/") {
      const name = raw.slice(1).trim().toUpperCase();
      for (let k = stack.length - 1; k > 0; k--) {
        if (stack[k].name === name) { stack.length = k; break; }
      }
      continue;
    }
    const selfClose = raw.endsWith("/");
    const body = selfClose ? raw.slice(0, -1) : raw;
    const m = body.match(/^([^\s/]+)/);
    if (!m) continue;
    const node: XNode = { name: m[1].toUpperCase(), attrs: {}, children: [], text: "" };
    const attrRe = /([^\s=]+)\s*=\s*("([^"]*)"|'([^']*)')/g;
    let a: RegExpExecArray | null;
    while ((a = attrRe.exec(body))) node.attrs[a[1].toUpperCase()] = decode(a[3] ?? a[4] ?? "");
    stack[stack.length - 1].children.push(node);
    if (!selfClose) stack.push(node);
  }
  return root;
}

export function child(node: XNode, name: string): XNode | undefined {
  return node.children.find((c) => c.name === name);
}
export function childText(node: XNode, name: string): string {
  return (child(node, name)?.text ?? "").trim();
}
export function findAll(node: XNode, name: string, out: XNode[] = []): XNode[] {
  for (const c of node.children) {
    if (c.name === name) out.push(c);
    else findAll(c, name, out);
  }
  return out;
}

/** Generic XML → table: picks the element name that repeats most and flattens its leaf children. */
export function xmlToTable(root: XNode): (string | number | null)[][] {
  const counts = new Map<string, number>();
  const walk = (nd: XNode) => {
    for (const c of nd.children) {
      if (c.children.length) counts.set(c.name, (counts.get(c.name) ?? 0) + 1);
      walk(c);
    }
  };
  walk(root);
  let best = "", bestCount = 0;
  counts.forEach((v, k) => { if (v > bestCount) { best = k; bestCount = v; } });
  if (!best) return [];
  const records = findAll(root, best);
  const cols: string[] = [];
  const rows = records.map((r) => {
    const rec: Record<string, string> = { ...r.attrs };
    for (const c of r.children) if (!c.children.length) rec[c.name] = c.text.trim();
    Object.keys(rec).forEach((k) => { if (!cols.includes(k)) cols.push(k); });
    return rec;
  });
  return [cols, ...rows.map((r) => cols.map((c) => r[c] ?? null))];
}
