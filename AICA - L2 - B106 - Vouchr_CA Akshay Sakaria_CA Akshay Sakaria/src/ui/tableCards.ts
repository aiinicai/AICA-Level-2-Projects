// U1 — on phones, tables marked `cards-sm` show each row as a card (styles.css). This copies each column heading onto the
// cells of that column as data-label, and keeps it current when rows or the language change.

function label(table: HTMLTableElement) {
  const heads = [...table.querySelectorAll('thead th')].map((th) => th.textContent?.trim() ?? '');
  for (const tr of table.querySelectorAll('tbody tr')) {
    let col = 0;
    for (const td of tr.children) {
      const want = heads[col] ?? '';
      if (td.getAttribute('data-label') !== want) td.setAttribute('data-label', want);
      col += (td as HTMLTableCellElement).colSpan || 1;
    }
  }
}

export function startTableCards(root: HTMLElement = document.body): () => void {
  let queued = false;
  const run = () => { queued = false; root.querySelectorAll<HTMLTableElement>('table.cards-sm').forEach(label); };
  const obs = new MutationObserver(() => { if (!queued) { queued = true; requestAnimationFrame(run); } });
  obs.observe(root, { childList: true, subtree: true, characterData: true });
  run();
  return () => obs.disconnect();
}
