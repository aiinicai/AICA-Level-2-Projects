# LucidBooks Theme (cream/orange, light-only)

**Date:** 2026-08-15

## Summary

Re-theme TaxFlow to match LucidBooks: warm cream/white light theme with an orange primary (`#ec5b13`). Remove dark mode entirely (themed light-only, no toggle). Sidebar becomes light cream with orange active states. Fonts match LucidBooks (Inter body, Public Sans sans, Plus Jakarta Sans display). Semantic status/chart colors (emerald/amber/red/blue) stay unchanged.

## Target palette (from LucidBooks tailwind.config.js)

| Token | Value | Notes |
|---|---|---|
| primary | `#ec5b13` (hsl 20 86% 50%) | brand orange |
| primary-foreground | white | |
| accent | `hsl(30 100% 55%)` | orange gradient end |
| secondary | warm orange tint (hsl 20 86% 60%) | replaces cyan #5ad4ff |
| background | cream `hsl(20 10% 97%)` | page bg |
| card / popover | white `hsl(0 0% 100%)` | |
| foreground | dark `hsl(22 30% 10%)` | text |
| border / input | warm `hsl(20 10% 85%)` | |
| muted | cream tint `hsl(20 10% 95%)` | |
| muted-foreground | warm gray `hsl(20 10% 45%)` | |
| sidebar | light cream `hsl(20 10% 95%)` | |
| ring | `#ec5b13` | |
| radius | 0.75rem (unchanged) | |

## Changes

1. **globals.css** — swap palette to cream/orange; delete the `.dark` block; recolor `.bg-gradient-brand`/`.text-gradient-brand` to orange gradient (e.g. `hsl(30 100% 55%)` → `#ec5b13`).
2. **Fonts** (`src/app/layout.tsx`) — load Plus Jakarta Sans (display) + Public Sans (sans) via `next/font`; keep Inter for body.
3. **Remove dark mode**:
   - `providers.tsx`: remove `next-themes` ThemeProvider (keep plain wrapper).
   - `app-header.tsx`: remove theme toggle button + `useTheme` import.
   - `settings/page.tsx`: remove Dark Mode preference card + `useTheme`.
4. **Sidebar** (`app-sidebar.tsx`) — dark navy → light cream: `bg-[#0a0d12]` → light cream, `border-white/10` → warm border, `text-slate-400` → muted warm gray, `hover:bg-white/10` → `hover:bg-primary/10`, active `text-[#2779ff]`/`bg-[#2779ff]/10` → orange `text-primary`/`bg-primary/10`, logo/avatar orange.
5. **Strip `dark:` classes** across all files (keep the light value): login, calendar, dashboard, master pages, notifications, search, settings, app-header, dashboard-layout, data-import.
6. **Replace hardcoded brand hexes** app-wide:
   - `#2779ff` → `#ec5b13`
   - `#1a6ae8` (hover) → darker orange `#d14f0a`
   - `#0a0d12` / `#14181f` (dark surfaces) → cream/white
   - `#f8f9fc` (bg) → cream `#faf7f3`
   - `#5ad4ff` / `#5f88ff` → orange tints
7. **Semantic colors unchanged** — emerald/amber/red/blue for status badges, charts, and dashboards.

## Verification

```powershell
npx tsc --noEmit
npx eslint src
npx vitest run
```

Visual check via dev server: sidebar light cream, primary buttons orange, login page cream bg, no dark toggle present.