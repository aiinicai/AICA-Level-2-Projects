<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

## Rules

- Accounting file parsing and Excel generation live in `src/lib/spreadsheet.ts`, with browser-only lazy workbook loading; column mapping feeds the existing master validators to preserve approval workflows.
- Supplier identity is administered through `public.supplier_accounts`; database policies enforce supplier-scoped reads and deny supplier writes, independently of navigation.

- Offline support ships only through `src/lib/pwa.ts`, the single guarded registrar for `/sw.js`; never register a service worker from a route or component directly, and never in dev or a Lovable preview host. Why: a stale worker on a preview host keeps serving old or deleted files to anyone who has the page open.
- The browser install prompt is captured once in `src/lib/install.ts` (loaded from `__root.tsx`) and screens request it through `promptInstall()`; never add another `beforeinstallprompt` listener. Why: the event fires a single time, so a second listener leaves the install button permanently dead.
