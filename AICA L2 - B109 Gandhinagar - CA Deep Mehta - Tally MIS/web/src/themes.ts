/** The five colour themes. The colours themselves live in styles.css as [data-theme='...'] blocks. */
export const THEMES = [
  { id: 'light', label: 'Light', note: 'Soft grey, green accent (default)', swatch: ['#f2f4f8', '#ffffff', '#2d4a2d'] },
  { id: 'dark', label: 'Dark', note: 'Easy on the eyes at night', swatch: ['#111512', '#1a211b', '#9ccba4'] },
  { id: 'ocean', label: 'Ocean', note: 'Cool blues', swatch: ['#eaf3fb', '#ffffff', '#0b5cab'] },
  { id: 'warm', label: 'Warm', note: 'Sand and terracotta', swatch: ['#f7f1e8', '#fffdf8', '#b4491f'] },
  { id: 'contrast', label: 'High contrast', note: 'Black on white, strong outlines', swatch: ['#ffffff', '#ffffff', '#000000'] },
] as const;

export type ThemeId = (typeof THEMES)[number]['id'];
const KEY = 'mis.theme';

export function storedTheme(): ThemeId {
  const asked = new URLSearchParams(location.search).get('theme'); // e.g. ?theme=ocean (used for screenshots)
  if (THEMES.some((t) => t.id === asked)) return asked as ThemeId;
  try {
    const v = localStorage.getItem(KEY);
    if (THEMES.some((t) => t.id === v)) return v as ThemeId;
  } catch { /* storage unavailable: use the default */ }
  return 'light';
}

/** Apply a theme to the page and remember the choice on this PC (it is not company data). */
export function applyTheme(id: ThemeId) {
  if (id === 'light') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', id);
  try { localStorage.setItem(KEY, id); } catch { /* ignore */ }
}
