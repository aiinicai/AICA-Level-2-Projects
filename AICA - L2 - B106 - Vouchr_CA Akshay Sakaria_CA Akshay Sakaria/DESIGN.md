# Vouchr — design record (UI transformation, v0.5)

Evidence labels used below: **[observed]** seen/measured on a reference site, **[tested]** checked in this app in a browser or test, **[interpreted]** a design judgement, **[new]** original to Vouchr.

## 1. Product assessment (before)
- Functionally complete but visually generic: flat white cards, system font, one blue, no hierarchy between "money" numbers and labels, no motion, no empty-state art. **[tested]**
- Users are lay staff on cheap Android phones in daylight, plus a CA team on desktops. Hindi must look as good as English. **[interpreted from brief]**
- Risks: decoration that slows a ₹6,000 phone, low contrast in sunlight, Devanagari clipping with tight letter-spacing. **[interpreted]**

## 2. Design direction — "Calm precision on ledger paper" **[new]**
- Warm paper canvas (#f6f4ef) with faint ledger ruling that fades out; ink-navy brand; emerald only for "verified / compliant", amber for "due", red for "risk".
- Light-first (paper bills, daylight); a full dark theme follows the phone setting.
- The client's own brand colour replaces `--brand`; a second tone `--brand-2` is mixed from it, so every client looks like their own app.
- Craftsmanship borrowed from the references, not their branding: tight display type with negative tracking, hairline borders + soft elevation, staggered entrance motion, marquee of capabilities on login. **[observed: OrderBlock typography/grid/animations, Operator Desk CSS tokens]**

## 3. Design system (tokens in `src/styles.css` §1)
| Group | Tokens |
|---|---|
| Colour | `--canvas --surface(-2,-3) --line(-strong) --ink(-2,-3) --brand --brand-2 --brand-soft --accent --ok/--warn/--danger/--info (+ -soft)` |
| Type | Inter Variable (body), Manrope Variable (display), Noto Sans Devanagari Variable (Hindi) — self-hosted @fontsource 5.2.8; `--fs-display` clamp 30–46px, `--fs-h1` 22–28px, body 15px, tabular numerals for money |
| Radius | 6 / 10 / 14 / 16 / 20 / 26 px |
| Elevation | `--sh-1` … `--sh-3`, `--sh-glow` (brand glow on primary buttons) |
| Motion | `--t-instant 120ms` … `--t-xl 620ms`; `--ease-out`, `--ease-spring`, `--ease-snap` |
| Layers | sticky 20, nav 30, overlay 50, toast 60 |

Hindi: `html[lang="hi"]` resets letter-spacing to 0 so matras are not clipped. **[tested]**

## 4. Implementation summary
- `src/styles.css` rewritten in 12 sections (tokens, base, shell, surfaces, buttons, forms, status, lists, charts, capture, login, drawer/toast/tabs) + motion + reduced-motion.
- New components: `ui/Art.tsx` (receipt illustration, empty-state art), `ui/CountUp.tsx` (number roll-up), bilingual `ErrorBoundary`.
- Login: split layout — story panel with scene and capability marquee, sign-in card.
- Staff home hero with animated receipt + scan line; MIS hero KPI with sparkline; icon chips on KPI tiles.
- Route transitions keyed by path; drawers with focus trap; toast `role="alert"`.

## 5. Interaction & motion inventory (implemented)
| Motion | Where | Duration |
|---|---|---|
| `v-fade-up` stagger | page sections, cards | 260–420ms |
| `v-slide-in-right / -up` | drawers (desktop / phone) | 260ms |
| `v-pop`, `v-draw` | success tick | 420ms |
| `v-toast` | toasts | 260ms |
| `v-grow-y / -x` | bar charts, h-bars, sparkline | 620ms, 40ms stagger |
| `v-scan`, `v-float` | capture hero receipt | loop |
| `v-marquee` | login capability strip | loop |
| `v-pulse-dot` | live/health dots | loop |
| `v-shimmer` | skeleton loaders | loop |
| CountUp | KPI numbers | ~620ms |
All loops and entrances are switched off under `prefers-reduced-motion: reduce`.

## 6. Validation actually performed
- `npm run typecheck`, 54 unit tests incl. Hindi-coverage test — pass. **[tested]**
- Production demo build: precache 31 entries ≈ 984 KB. **[tested]**
- Prod preview sweep: 19 screens, all roles, EN + HI, 0 console errors. **[tested]**
- No horizontal overflow at 320 / 375 / 390 / 768 / 1024 / 1440 / 1920 px. **[tested]**
- Contrast measured light + dark; `--ok` darkened to #07754f to pass 4.5:1 on its soft background. **[tested]**
- Fonts: only the subsets a page uses are fetched. **[tested]**
- FCP 84 ms on local preview — indicative only, not a real-device number.

## 7. Critical quality audit — what was NOT verified
- Reference-site marquee and accordion transitions and Operator Desk input focus style were not measured; our versions are original.
- Reduced-motion checked by code review only — not emulated in a browser.
- Lighthouse not run; no real low-end Android device tested; no screen-reader pass (NVDA/TalkBack).
- Mistake disclosed: during reference study, localStorage/reload scripts were run once on the order-block.com tab instead of the Vouchr tab. Nothing was submitted; no data entered.
