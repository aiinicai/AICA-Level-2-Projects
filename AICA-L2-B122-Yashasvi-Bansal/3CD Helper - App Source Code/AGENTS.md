<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.

## What Lovable manages

Rules outside this block are the project's own. Change the pieces below in
Lovable, not by hand. With the [Lovable MCP](https://mcp.lovable.dev)
connected, `send_message` asks Lovable to do it; otherwise ask the user to
use the editor.

- **Database.** Do not add or edit `supabase/migrations/` or `drizzle/`.
  Ask Lovable to change the schema.
- **Generated files.** Do not edit a file whose header says it is automatically
  generated.
- **AI gateway.** Keep model calls on Lovable's gateway, and keep
  `LOVABLE_API_KEY` out of browser code.
- **Connectors.** Lovable provides native connectors. `list_connectors` shows
  which are enabled; `add_connector` only returns the dashboard link. When a
  connector is enabled, calls go through the connector gateway and need
  `LOVABLE_API_KEY`. When Lovable does not provide one, users can bring their
  own key and store it in Secrets.
- **Secrets.** Lovable manages them. Do not put secret values in the repo.
<!-- LOVABLE:END -->

## Project rules
- Screens live in `src/components/screens/`; route files in `src/routes/` stay thin wrappers. Why: ported from a React Router app with multi-export page modules.
- Signed-in pages live under `src/routes/_authenticated/` (client-only gate redirecting to `/login`); `/app/onboarding` uses `app_.onboarding.tsx` to skip the firm-required layout. Why: firm workspace needs a firm before showing the app shell.
- All data access is browser-side through the generated Cloud client with RLS; firm isolation is enforced by RLS helper functions (`is_firm_member`, `can_edit_firm`, `is_firm_admin`). Why: preserves the original app's security model.
- Firm roles live in `firm_members`, never on `profiles`. Why: prevents privilege escalation.
- tsconfig keeps `strictNullChecks` but relaxes other strict flags. Why: ported code was written non-strict; TanStack Router requires strictNullChecks.
- Installable app is manifest-only (no service worker). Why: app needs network for data; avoids stale-cache problems in preview.
