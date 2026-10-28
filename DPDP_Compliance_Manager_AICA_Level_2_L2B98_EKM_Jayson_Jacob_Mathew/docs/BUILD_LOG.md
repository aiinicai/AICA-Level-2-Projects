# Build log

Keep this file current. After every Lovable prompt, add a line. Do not paste secrets here.

## Status

| Phase | State |
|---|---|
| 0 Blueprint: screen map, dictionary, schema, security, seed, tests, prompts | Done (database layer tested in PGlite, 225 of 225) |
| Review of schema and tenant security model by someone other than the author | **Not done. Required before Phase 1 writes to a real database.** |
| 1 UI shell | Not started |
| 2 Supabase foundation | Not started |
| 3 Core workflow | Not started |
| 4 Reports and audit trail | Not started |
| 5 Pilot readiness | Not started |

## Environments

| Item | Value |
|---|---|
| Supabase test project | (create; never real data) |
| Lovable project | (name) |
| Source control | (connect GitHub when available) |
| Region / hosting decision | Open decision |

## Completed prompts

| Date | Prompt id | What changed | Files touched | Tested how | Result |
|---|---|---|---|---|---|

## Known errors

| Date | Where | Symptom | Next step |
|---|---|---|---|

## Open decisions (from the spec and found while building)

1. Client onboarding, evidence retention and engagement closure policy. Needed before production.
2. Hosting region, backup frequency, contractual terms with Supabase and Lovable. Needed before real data.
3. Whether client reviewers may approve anything. Today they have read access to the review trail only.
4. Whether firm reviewers may also verify evidence that they themselves requested.
5. Whether a firm administrator should be able to assign themselves (they can; the audit log records it).
6. Malware scanning for uploaded evidence. Not provided by default.
7. Email delivery provider for invitations and notifications.
8. Whether the Significant Data Fiduciary question is shown to clients or kept for the firm.
9. Legal controls: the demo library must be replaced with controls verified against the official text and commencement notifications.

## Next task

Have the schema and security files reviewed. Then run `LOVABLE_BUILD_PROMPTS.md` prompt P0 (project check) and P1 (UI shell).
