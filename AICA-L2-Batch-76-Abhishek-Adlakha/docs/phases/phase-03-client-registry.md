# Phase 3 — Client registry, groups, GSTINs and controlled import

## Outcome

Phase 3 introduces the first business master while preserving the Phase 0–2 boundaries. A client is one legal/person engagement. Contacts, addresses, GST registrations and group memberships are separate relational records; services, tasks and billing remain deferred.

The development stack remains Docker-based on macOS. The production target remains native Windows Server 2019: IIS, .NET 10 and PostgreSQL as a Windows service. Windows and macOS users access the same HTTPS application through a browser on the office LAN.

## Database

Forward-only migration `20260820143034_AddClientRegistryAndImportStaging` adds the `clients` schema and:

- client categories and clients;
- contacts and effective-dated addresses;
- multiple GST registrations per client;
- client groups and effective-dated many-to-many memberships;
- approved source-value mappings and per-row reconciliation results in the existing `import` schema;
- nine configurable client field policies;
- least-privilege runtime grants for `practice_app`.

Database constraints enforce normalized unique client codes, PAN/TAN shapes, GSTIN shape/state relationships, globally unique GSTINs, one active primary GSTIN, one active primary contact/address per type, one current PRIMARY group, effective-date ordering, and reasoned client deactivation. PAN and TAN are indexed but deliberately not unique until duplicate cleansing is approved.

Seed categories are Individual, HUF, Partnership, LLP, Private Limited, Public Limited, Trust, Society, Proprietorship, OPC and Other. `Firm` is deliberately not a category.

## API and access control

The API supplies paginated client search by name, code, PAN or GSTIN; filters by lifecycle/category/group; aggregate create/read/update; deactivate/reactivate; client masters; and client-group creation/listing. Mutations require anti-forgery tokens and produce append-only audit events.

Existing permissions are activated: `clients.view`, `clients.create`, `clients.edit` and `clients.deactivate`. Phase 3 master access requires `ALL` for scoped permissions. `OWN` and `TEAM` client routing cannot be honestly evaluated until Phase 4 client-service responsibility exists, so the API rejects those scopes instead of overexposing client data.

## User interface

The authenticated workspace now opens on Client Registry for authorized users. It provides search, lifecycle filters, pagination, a client inspector, create/edit actions, deactivation/reactivation, category/group selection, optional primary contact/address and up to two GST registrations in the initial creation form. Administrator-configured required client fields are applied in both the form and server validation.

## Workbook dry-run

The Phase 1 profiler now has a client transform dry-run. It opens `Clients List.xlsm` read-only, reads only `Master Data`, normalizes proposed client fields and emits a JSON reconciliation report. Service columns and `Billing MIS` are not imported in Phase 3.

Run:

```bash
dotnet run --project tools/Practice.WorkbookProfiler --configuration Release -- \
  "Clients List.xlsm" --client-dry-run --output artifacts/phase-03-client-dry-run.json
```

The source SHA-256 is checked before and after analysis. Rows with `Firm`, unknown categories, missing codes/names, invalid PAN/TAN/GSTIN, duplicate client codes or repeated tax IDs remain exceptions. The command never writes to PostgreSQL. An approved database import is intentionally gated until the administrator reviews these mappings and exceptions; production workbook rows are not silently classified or imported.

## Verification

- `dotnet build PracticeManagement.slnx --configuration Release --no-restore`
- execute Architecture, Database, Identity and WorkbookProfiler check projects;
- `pnpm --dir web run build`;
- apply the forward migration in an isolated PostgreSQL database, reapply safely, and test application-role grants;
- test create/search/edit/deactivate/reactivate with zero, one and two GSTIN clients;
- run the client dry-run twice and compare row totals/source hash;
- confirm `Clients List.xlsm` hash remains unchanged.

## Deferred

No service catalogue or client-service configuration (Phase 4), tasks (Phase 5), recurrence (Phase 6), billing (Phases 7–8), or billing workbook import is included. Production workbook import remains blocked until the Phase 3 exception queue is reviewed and an approved batch is explicitly authorized.
