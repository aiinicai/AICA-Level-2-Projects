// U6 — chip groups (role="radiogroup" with role="radio" buttons) follow the ARIA radio pattern everywhere:
// one Tab stop per group (the selected chip), ←/→/↑/↓ move to the next chip and select it, Home/End jump to the ends.

const radiosOf = (g: Element) => [...g.querySelectorAll<HTMLElement>('[role="radio"]')].filter((r) => r.closest('[role="radiogroup"]') === g && !(r as HTMLButtonElement).disabled);

function tabStops(root: ParentNode) {
  for (const g of root.querySelectorAll('[role="radiogroup"]')) {
    const rs = radiosOf(g);
    const on = rs.find((r) => r.getAttribute('aria-checked') === 'true') ?? rs[0];
    for (const r of rs) { const want = r === on ? '0' : '-1'; if (r.getAttribute('tabindex') !== want) r.setAttribute('tabindex', want); }
  }
}

export function startRadioKeys(root: HTMLElement = document.body): () => void {
  const onKey = (e: KeyboardEvent) => {
    const t = e.target as HTMLElement | null;
    if (!t || t.getAttribute('role') !== 'radio') return;
    const g = t.closest('[role="radiogroup"]');
    if (!g) return;
    const rs = radiosOf(g);
    const i = rs.indexOf(t);
    const next = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? rs[(i + 1) % rs.length]
      : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? rs[(i - 1 + rs.length) % rs.length]
      : e.key === 'Home' ? rs[0] : e.key === 'End' ? rs[rs.length - 1] : undefined;
    if (!next) return;
    e.preventDefault();
    next.focus();
    next.click(); // selecting follows focus, as for native radio buttons
  };
  let queued = false;
  const obs = new MutationObserver(() => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; tabStops(root); }); } });
  obs.observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-checked'] });
  root.addEventListener('keydown', onKey);
  tabStops(root);
  return () => { obs.disconnect(); root.removeEventListener('keydown', onKey); };
}
