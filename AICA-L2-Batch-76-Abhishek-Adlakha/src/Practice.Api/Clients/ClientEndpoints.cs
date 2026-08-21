using System.Security.Claims;
using System.Text.Json;
using System.Globalization;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Builder;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;
using Practice.Reporting;

namespace Practice.Api.Clients;

public static class ClientEndpoints
{
    private static readonly string[] RequiredFieldError = ["This field is required by the current field policy."];
    public static IEndpointRouteBuilder MapClientEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var clients = endpoints.MapGroup("/api/v1/clients").RequireAuthorization("password-current");
        clients.MapGet("/masters", GetMastersAsync).RequireAuthorization(PermissionCodes.ClientsView);
        clients.MapGet("/", ListAsync).RequireAuthorization(PermissionCodes.ClientsView);
        clients.MapGet("/{id:guid}", GetAsync).RequireAuthorization(PermissionCodes.ClientsView);
        clients.MapPost("/", CreateAsync).RequireAuthorization(PermissionCodes.ClientsCreate).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        clients.MapPut("/{id:guid}", UpdateAsync).RequireAuthorization(PermissionCodes.ClientsEdit).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        clients.MapPost("/{id:guid}/status", ChangeStatusAsync).RequireAuthorization(PermissionCodes.ClientsDeactivate).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        clients.MapPost("/:export", ExportAsync).RequireAuthorization(PermissionCodes.ClientsView).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        clients.MapGet("/code-settings", GetCodeSettingsAsync).RequireAuthorization(PermissionCodes.ClientsView);
        clients.MapPut("/code-settings", UpdateCodeSettingsAsync).RequireAuthorization(PermissionCodes.ClientsEdit).WithMetadata(new RequireAntiforgeryTokenAttribute(true));

        var groups = endpoints.MapGroup("/api/v1/client-groups").RequireAuthorization("password-current");
        groups.MapGet("/", ListGroupsAsync).RequireAuthorization(PermissionCodes.ClientsView);
        groups.MapPost("/", CreateGroupAsync).RequireAuthorization(PermissionCodes.ClientsEdit).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        return endpoints;
    }

    private static async Task<IResult> GetMastersAsync(ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var categories = await database.ClientCategories.AsNoTracking().Where(x => x.IsActive).OrderBy(x => x.DisplayOrder)
            .Select(x => new { x.Id, x.Code, x.Name }).ToArrayAsync(cancellationToken);
        var states = await database.IndiaStates.AsNoTracking().Where(x => x.IsActive).OrderBy(x => x.Name)
            .Select(x => new { code = x.GstCode, x.Name }).ToArrayAsync(cancellationToken);
        var groups = await database.ClientGroups.AsNoTracking().Where(x => x.IsActive).OrderBy(x => x.Name)
            .Select(x => new { x.Id, x.Code, x.Name }).ToArrayAsync(cancellationToken);
        var requiredFields = await database.FieldDefinitions.AsNoTracking()
            .Where(x => x.EntityType == "clients.client" && x.IsActive && x.IsAdministratorRequired)
            .Select(x => x.FieldKey).ToArrayAsync(cancellationToken);
        var codePrefix = await ClientCodeSequence.GetPrefixAsync(database, cancellationToken);
        var nextClientCode = await ClientCodeSequence.NextCodeAsync(database, cancellationToken);
        return Results.Ok(new { categories, states, groups, requiredFields, codePrefix, nextClientCode });
    }

    private static async Task<IResult> ListAsync(string? search, string? status, Guid? categoryId, Guid? groupId,
        bool? hasGstin, string? sort, string? direction,
        int? page, int? pageSize, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var selectedPage = Math.Max(1, page ?? 1); var selectedPageSize = Math.Clamp(pageSize is null or <= 0 ? 25 : pageSize.Value, 1, 100);
        var query = await ApplyClientScopeAsync(database.Clients.AsNoTracking(), principal, PermissionCodes.ClientsView, database, cancellationToken);
        if (!string.IsNullOrWhiteSpace(status) && !status.Equals("ALL", StringComparison.OrdinalIgnoreCase))
        {
            var normalizedStatus = status.ToUpperInvariant();
            query = query.Where(x => x.Status == normalizedStatus);
        }
        if (categoryId is not null) query = query.Where(x => x.CategoryId == categoryId);
        if (hasGstin is not null)
        {
            query = hasGstin.Value
                ? query.Where(x => x.GstRegistrations.Any(g => g.IsActive))
                : query.Where(x => !x.GstRegistrations.Any(g => g.IsActive));
        }
        if (groupId is not null) query = query.Where(x => x.GroupMemberships.Any(m => m.GroupId == groupId && m.ValidTo == null));
        if (!string.IsNullOrWhiteSpace(search))
        {
            var term = search.Trim().ToUpperInvariant();
            query = query.Where(x => x.NormalizedClientCode.Contains(term) || x.NormalizedDisplayName.Contains(term) ||
                                     (x.Pan != null && x.Pan.Contains(term)) || x.GstRegistrations.Any(g => g.Gstin.Contains(term)));
        }
        var total = await query.CountAsync(cancellationToken);
        var items = await OrderClients(query, sort, direction)
            .Skip((selectedPage - 1) * selectedPageSize).Take(selectedPageSize).Select(x => new
            {
                x.Id, x.ClientCode, x.DisplayName, category = x.Category == null ? null : x.Category.Name,
                x.Pan, x.Status, gstinCount = x.GstRegistrations.Count(g => g.IsActive),
                primaryGroup = x.GroupMemberships.Where(m => m.MembershipType == "PRIMARY" && m.ValidTo == null).Select(m => m.Group.Name).FirstOrDefault()
            }).ToArrayAsync(cancellationToken);
        return Results.Ok(new { items, page = selectedPage, pageSize = selectedPageSize, total, totalPages = (int)Math.Ceiling(total / (double)selectedPageSize) });
    }

    // The register export carries the same filters and the same scope as the list, so it can never
    // reveal a client the caller cannot already see on screen.
    private static async Task<IResult> ExportAsync(
        ClientExportRequest request, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var format = (request.Format ?? "xlsx").Trim().ToLowerInvariant();
        if (format is not ("csv" or "xlsx"))
        {
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["format"] = ["Choose CSV or XLSX."] });
        }

        var query = await ApplyClientScopeAsync(database.Clients.AsNoTracking(), principal, PermissionCodes.ClientsView, database, cancellationToken);
        var filters = request.Filters ?? new ClientListFilters(null, null, null, null, null);
        if (!string.IsNullOrWhiteSpace(filters.Status) && !filters.Status.Equals("ALL", StringComparison.OrdinalIgnoreCase))
        {
            var normalizedStatus = filters.Status.ToUpperInvariant();
            query = query.Where(x => x.Status == normalizedStatus);
        }
        if (filters.CategoryId is not null) query = query.Where(x => x.CategoryId == filters.CategoryId);
        if (filters.GroupId is not null) query = query.Where(x => x.GroupMemberships.Any(m => m.GroupId == filters.GroupId && m.ValidTo == null));
        if (filters.HasGstin is not null)
        {
            query = filters.HasGstin.Value
                ? query.Where(x => x.GstRegistrations.Any(g => g.IsActive))
                : query.Where(x => !x.GstRegistrations.Any(g => g.IsActive));
        }
        if (!string.IsNullOrWhiteSpace(filters.Search))
        {
            var term = filters.Search.Trim().ToUpperInvariant();
            query = query.Where(x => x.NormalizedClientCode.Contains(term) || x.NormalizedDisplayName.Contains(term) ||
                                     (x.Pan != null && x.Pan.Contains(term)) || x.GstRegistrations.Any(g => g.Gstin.Contains(term)));
        }

        var rows = await OrderClients(query, request.Sort, request.Direction).Select(x => new
        {
            x.ClientCode, x.DisplayName, x.LegalName, category = x.Category == null ? null : x.Category.Name,
            x.Status, x.Pan, x.Tan,
            gstins = x.GstRegistrations.Where(g => g.IsActive).Select(g => g.Gstin).ToArray(),
            primaryGroup = x.GroupMemberships.Where(m => m.MembershipType == "PRIMARY" && m.ValidTo == null).Select(m => m.Group.Name).FirstOrDefault()
        }).ToArrayAsync(cancellationToken);

        var columns = new[]
        {
            new ExportColumn("Client code"), new ExportColumn("Client name"), new ExportColumn("Legal name"),
            new ExportColumn("Category"), new ExportColumn("Primary group"), new ExportColumn("Status"),
            new ExportColumn("PAN"), new ExportColumn("TAN"), new ExportColumn("Active GSTINs", true), new ExportColumn("GSTIN list")
        };
        var values = rows.Select(item => (IReadOnlyList<string>)
        [
            item.ClientCode, item.DisplayName, item.LegalName ?? string.Empty, item.category ?? string.Empty,
            item.primaryGroup ?? string.Empty, item.Status, item.Pan ?? string.Empty, item.Tan ?? string.Empty,
            item.gstins.Length.ToString(CultureInfo.InvariantCulture), string.Join(", ", item.gstins)
        ]);

        return format == "csv"
            ? Results.File(TabularExport.Csv(columns, values), "text/csv", "client-register.csv")
            : Results.File(TabularExport.Xlsx("Clients", columns, values),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "client-register.xlsx");
    }

    private static async Task<IResult> GetCodeSettingsAsync(AppDbContext database, CancellationToken cancellationToken) =>
        Results.Ok(new
        {
            prefix = await ClientCodeSequence.GetPrefixAsync(database, cancellationToken),
            nextClientCode = await ClientCodeSequence.NextCodeAsync(database, cancellationToken)
        });

    private static async Task<IResult> UpdateCodeSettingsAsync(
        ClientCodeSettingsRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        if (ClientCodeSequence.ValidatePrefix(request.Prefix) is { } problem)
        {
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["prefix"] = [problem] });
        }

        var prefix = request.Prefix!.Trim().ToUpperInvariant();
        var now = clock.UtcNow;
        await ClientCodeSequence.SetPrefixAsync(database, prefix, now, cancellationToken);
        database.AuditEvents.Add(IdentityService.CreateAudit(now, UserId(context.User), "settings.client_code_prefix_changed",
            "AppSetting", ClientCodeSequence.SettingKey, JsonSerializer.Serialize(new { prefix })));
        await database.SaveChangesAsync(cancellationToken);
        return Results.Ok(new { prefix, nextClientCode = await ClientCodeSequence.NextCodeAsync(database, cancellationToken) });
    }

    private static async Task<IResult> GetAsync(Guid id, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var scoped = await ApplyClientScopeAsync(database.Clients.AsNoTracking().Where(x => x.Id == id), principal, PermissionCodes.ClientsView, database, cancellationToken);
        var client = await scoped.Select(x => new
        {
            x.Id, x.ClientCode, x.LegacyCode, x.DisplayName, x.LegalName, x.CategoryId, category = x.Category == null ? null : x.Category.Name,
            x.Pan, x.Tan, x.OnboardedOn, x.Status, x.DeactivatedOn, x.DeactivationReason, x.Notes, x.CreatedAtUtc, x.UpdatedAtUtc,
            contacts = x.Contacts.OrderByDescending(c => c.IsPrimary).ThenBy(c => c.Name).Select(c => new { c.Id, c.ContactType, c.Name, c.Designation, c.Phone, c.Email, c.IsPrimary, c.IsActive, c.Notes }).ToArray(),
            addresses = x.Addresses.OrderByDescending(a => a.IsPrimary).Select(a => new { a.Id, a.AddressType, a.Line1, a.Line2, a.City, a.District, a.StateCode, a.PostalCode, a.CountryCode, a.IsPrimary, a.IsActive, a.ValidFrom, a.ValidTo }).ToArray(),
            gstRegistrations = x.GstRegistrations.OrderByDescending(g => g.IsPrimary).ThenBy(g => g.Gstin).Select(g => new { g.Id, g.Gstin, g.StateCode, g.TradeName, g.RegistrationStatus, g.EffectiveFrom, g.EffectiveTo, g.IsPrimary, g.IsActive, g.CancellationReason }).ToArray(),
            tanRegistrations = x.TanRegistrations.OrderByDescending(t => t.IsPrimary).ThenBy(t => t.Tan).Select(t => new { t.Id, t.Tan, t.DeductorName, t.Branch, t.EffectiveFrom, t.EffectiveTo, t.IsPrimary, t.IsActive, t.Notes }).ToArray(),
            groups = x.GroupMemberships.OrderByDescending(m => m.MembershipType).ThenBy(m => m.Group.Name).Select(m => new { membershipId = m.Id, m.GroupId, m.Group.Code, m.Group.Name, m.MembershipType, m.EffectiveFrom, m.ValidTo, m.Notes }).ToArray()
        }).SingleOrDefaultAsync(cancellationToken);
        return client is null ? Results.NotFound() : Results.Ok(client);
    }

    private static async Task<IResult> CreateAsync(ClientUpsertRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        // A blank code means "give me the next one". Codes stay a firm-wide serial rather than
        // something typed by hand, which is why the request no longer has to carry one.
        if (string.IsNullOrWhiteSpace(request.ClientCode))
        {
            request = request with { ClientCode = await ClientCodeSequence.NextCodeAsync(database, cancellationToken) };
        }
        var errors = await ValidateAsync(request, null, database, cancellationToken);
        if (errors.Count > 0) return Results.ValidationProblem(errors);
        var now = clock.UtcNow;
        var client = new Client { Id = Guid.NewGuid(), ClientCode = request.ClientCode.Trim(), NormalizedClientCode = ClientRules.NormalizeCode(request.ClientCode), LegacyCode = Clean(request.LegacyCode), DisplayName = request.DisplayName.Trim(), NormalizedDisplayName = ClientRules.NormalizeName(request.DisplayName), LegalName = Clean(request.LegalName), CategoryId = request.CategoryId, Pan = ClientRules.NormalizeTaxId(request.Pan), Tan = ClientRules.NormalizeTaxId(request.Tan), OnboardedOn = request.OnboardedOn, Status = "ACTIVE", Notes = Clean(request.Notes), CreatedAtUtc = now, UpdatedAtUtc = now };
        database.Clients.Add(client);
        AddChildren(client.Id, request, database, now);
        database.AuditEvents.Add(Audit(now, UserId(context.User), "clients.created", client.Id, new { client.ClientCode, client.DisplayName, gstinCount = request.GstRegistrations.Length, groupCount = request.Groups.Length }));
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/v1/clients/{client.Id}", new { client.Id, client.ClientCode, client.DisplayName });
    }

    private static async Task<IResult> UpdateAsync(Guid id, ClientUpsertRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var client = await database.Clients.Include(x => x.Contacts).Include(x => x.Addresses)
            .Include(x => x.GstRegistrations).Include(x => x.TanRegistrations).Include(x => x.GroupMemberships)
            .SingleOrDefaultAsync(x => x.Id == id, cancellationToken);
        if (client is null) return Results.NotFound();
        if (!await CanAccessClientAsync(id, context.User, PermissionCodes.ClientsEdit, database, cancellationToken)) return ScopeDenied();
        var errors = await ValidateAsync(request, id, database, cancellationToken);
        if (errors.Count > 0) return Results.ValidationProblem(errors);
        await using var transaction = await database.Database.BeginTransactionAsync(cancellationToken);
        var changed = ChangedFields(client, request);
        var updatedCode = string.IsNullOrWhiteSpace(request.ClientCode) ? client.ClientCode : request.ClientCode.Trim();
        client.ClientCode = updatedCode; client.NormalizedClientCode = ClientRules.NormalizeCode(updatedCode); client.LegacyCode = Clean(request.LegacyCode);
        client.DisplayName = request.DisplayName.Trim(); client.NormalizedDisplayName = ClientRules.NormalizeName(request.DisplayName); client.LegalName = Clean(request.LegalName); client.CategoryId = request.CategoryId;
        client.Pan = ClientRules.NormalizeTaxId(request.Pan); client.Tan = ClientRules.NormalizeTaxId(request.Tan); client.OnboardedOn = request.OnboardedOn; client.Notes = Clean(request.Notes); client.UpdatedAtUtc = clock.UtcNow;
        ReconcileChildren(client, request, database, clock.UtcNow);
        SyncPrimaryTan(client, request);
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(context.User), "clients.updated", client.Id, new { changedFields = changed, childCollectionsReconciled = true }));
        await database.SaveChangesAsync(cancellationToken);
        await transaction.CommitAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> ChangeStatusAsync(Guid id, ClientStatusRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        if (!await CanAccessClientAsync(id, context.User, PermissionCodes.ClientsDeactivate, database, cancellationToken)) return ScopeDenied();
        var client = await database.Clients.SingleOrDefaultAsync(x => x.Id == id, cancellationToken);
        if (client is null) return Results.NotFound();
        if (!request.IsActive && string.IsNullOrWhiteSpace(request.Reason)) return Results.ValidationProblem(new Dictionary<string, string[]> { ["reason"] = ["A reason is required to deactivate a client."] });
        client.Status = request.IsActive ? "ACTIVE" : "INACTIVE"; client.DeactivatedOn = request.IsActive ? null : DateOnly.FromDateTime(clock.UtcNow.Date); client.DeactivationReason = request.IsActive ? null : request.Reason.Trim(); client.UpdatedAtUtc = clock.UtcNow;
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(context.User), request.IsActive ? "clients.reactivated" : "clients.deactivated", client.Id, new { request.Reason }, request.Reason));
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> ListGroupsAsync(ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        return Results.Ok(await database.ClientGroups.AsNoTracking().OrderBy(x => x.Name).Select(x => new { x.Id, x.Code, x.Name, x.Description, x.IsActive, memberCount = x.Memberships.Count(m => m.ValidTo == null) }).ToArrayAsync(cancellationToken));
    }

    private static async Task<IResult> CreateGroupAsync(ClientGroupRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        if (!HasAllScope(context.User, PermissionCodes.ClientsEdit)) return ScopeDenied();
        var code = ClientRules.NormalizeCode(request.Code); var name = request.Name.Trim();
        if (code.Length is < 2 or > 50 || name.Length is < 2 or > 150) return Results.ValidationProblem(new Dictionary<string, string[]> { ["group"] = ["Group code and name must contain 2 to 50/150 characters."] });
        if (await database.ClientGroups.AnyAsync(x => x.Code == code || x.NormalizedName == ClientRules.NormalizeName(name), cancellationToken)) return Results.Conflict(new { message = "Group code or name already exists." });
        var group = new ClientGroup { Id = Guid.NewGuid(), Code = code, Name = name, NormalizedName = ClientRules.NormalizeName(name), Description = Clean(request.Description), IsActive = true, CreatedAtUtc = clock.UtcNow, UpdatedAtUtc = clock.UtcNow };
        database.ClientGroups.Add(group); database.AuditEvents.Add(Audit(clock.UtcNow, UserId(context.User), "clients.group_created", group.Id, new { group.Code, group.Name }));
        await database.SaveChangesAsync(cancellationToken); return Results.Created($"/api/v1/client-groups/{group.Id}", new { group.Id, group.Code, group.Name });
    }

    private static async Task<Dictionary<string, string[]>> ValidateAsync(ClientUpsertRequest request, Guid? currentId, AppDbContext database, CancellationToken cancellationToken)
    {
        var values = new Dictionary<string, string?> { ["clientCode"] = request.ClientCode, ["displayName"] = request.DisplayName, ["legalName"] = request.LegalName, ["categoryId"] = request.CategoryId?.ToString(), ["pan"] = request.Pan, ["tan"] = request.Tan, ["onboardedOn"] = request.OnboardedOn?.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), ["primaryContact"] = request.Contacts.Any(x => x.IsPrimary) ? "yes" : null, ["primaryAddress"] = request.Addresses.Any(x => x.IsPrimary) ? "yes" : null };
        var required = await database.FieldDefinitions.AsNoTracking().Where(x => x.EntityType == "clients.client" && x.IsActive && x.IsAdministratorRequired).Select(x => x.FieldKey).ToArrayAsync(cancellationToken);
        var errors = required.Where(key => !values.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value)).ToDictionary(key => key, _ => RequiredFieldError);
        // On create the code is auto-assigned before validation. On edit a blank code means "keep
        // the existing one", so only a supplied value is length-checked.
        var suppliedCode = (request.ClientCode ?? string.Empty).Trim();
        if (currentId is null ? suppliedCode.Length is < 1 or > 30 : suppliedCode.Length > 30)
        {
            errors["clientCode"] = ["Client code must contain 1 to 30 characters."];
        }
        if (request.DisplayName.Trim().Length is < 2 or > 250) errors["displayName"] = ["Client name must contain 2 to 250 characters."];
        var code = ClientRules.NormalizeCode(suppliedCode);
        if (code.Length > 0 && await database.Clients.AnyAsync(x => x.NormalizedClientCode == code && x.Id != currentId, cancellationToken)) errors["clientCode"] = ["Client code already exists."];
        var pan = ClientRules.NormalizeTaxId(request.Pan); var tan = ClientRules.NormalizeTaxId(request.Tan);
        if (!ClientRules.IsValidPan(pan)) errors["pan"] = ["PAN must use the format AAAAA9999A."];
        if (!ClientRules.IsValidTan(tan)) errors["tan"] = ["TAN must use the format AAAA99999A."];
        if (request.CategoryId is not null && !await database.ClientCategories.AnyAsync(x => x.Id == request.CategoryId && x.IsActive, cancellationToken)) errors["categoryId"] = ["Choose an active client category."];
        if (request.Contacts.GroupBy(x => x.ContactType.ToUpperInvariant()).Any(g => g.Count(x => x.IsPrimary && x.IsActive) > 1)) errors["contacts"] = ["Only one active primary contact is allowed per contact type."];
        if (request.Addresses.GroupBy(x => x.AddressType.ToUpperInvariant()).Any(g => g.Count(x => x.IsPrimary && x.IsActive) > 1)) errors["addresses"] = ["Only one active primary address is allowed per address type."];
        if (request.GstRegistrations.Count(x => x.IsPrimary && x.IsActive) > 1) errors["gstRegistrations"] = ["Only one active primary GSTIN is allowed."];
        foreach (var gst in request.GstRegistrations)
        {
            var gstin = ClientRules.NormalizeTaxId(gst.Gstin)!;
            if (!ClientRules.IsValidGstin(gstin)) { errors[$"gstRegistrations.{gst.Gstin}"] = ["GSTIN shape or checksum is invalid."]; continue; }
            if (gst.StateCode != gstin[..2]) errors[$"gstRegistrations.{gst.Gstin}"] = ["GSTIN state prefix must match the selected state."];
            if (await database.GstRegistrations.AnyAsync(x => x.Gstin == gstin && x.ClientId != currentId, cancellationToken)) errors[$"gstRegistrations.{gst.Gstin}"] = ["GSTIN is already registered to another client."];
        }
        if (request.Groups.GroupBy(x => x.GroupId).Any(g => g.Count() > 1)) errors["groups"] = ["A client cannot have duplicate membership in the same group."];
        if (request.Groups.Count(x => x.MembershipType.Equals("PRIMARY", StringComparison.OrdinalIgnoreCase) && x.ValidTo is null) > 1) errors["groups"] = ["Only one current PRIMARY group is allowed."];
        var groupIds = request.Groups.Select(x => x.GroupId).Distinct().ToArray();
        if (groupIds.Length > 0 && await database.ClientGroups.CountAsync(x => groupIds.Contains(x.Id) && x.IsActive, cancellationToken) != groupIds.Length) errors["groups"] = ["One or more client groups are invalid or inactive."];
        return errors;
    }

    private static void AddChildren(Guid clientId, ClientUpsertRequest request, AppDbContext database, DateTimeOffset now)
    {
        database.ClientContacts.AddRange(request.Contacts.Select(x => new ClientContact { Id = Guid.NewGuid(), ClientId = clientId, ContactType = x.ContactType.Trim().ToUpperInvariant(), Name = x.Name.Trim(), Designation = Clean(x.Designation), Phone = Clean(x.Phone), Email = Clean(x.Email)?.ToLowerInvariant(), IsPrimary = x.IsPrimary, IsActive = x.IsActive, Notes = Clean(x.Notes), CreatedAtUtc = now, UpdatedAtUtc = now }));
        database.ClientAddresses.AddRange(request.Addresses.Select(x => new ClientAddress { Id = Guid.NewGuid(), ClientId = clientId, AddressType = x.AddressType.Trim().ToUpperInvariant(), Line1 = x.Line1.Trim(), Line2 = Clean(x.Line2), City = Clean(x.City), District = Clean(x.District), StateCode = Clean(x.StateCode), PostalCode = Clean(x.PostalCode), CountryCode = string.IsNullOrWhiteSpace(x.CountryCode) ? "IN" : x.CountryCode.Trim().ToUpperInvariant(), IsPrimary = x.IsPrimary, IsActive = x.IsActive, ValidFrom = x.ValidFrom ?? DateOnly.FromDateTime(now.Date), ValidTo = x.ValidTo, CreatedAtUtc = now, UpdatedAtUtc = now }));
        database.GstRegistrations.AddRange(request.GstRegistrations.Select(x => new GstRegistration { Id = Guid.NewGuid(), ClientId = clientId, Gstin = ClientRules.NormalizeTaxId(x.Gstin)!, StateCode = x.StateCode, TradeName = Clean(x.TradeName), RegistrationStatus = x.RegistrationStatus.Trim().ToUpperInvariant(), EffectiveFrom = x.EffectiveFrom, EffectiveTo = x.EffectiveTo, IsPrimary = x.IsPrimary, IsActive = x.IsActive, CancellationReason = Clean(x.CancellationReason), CreatedAtUtc = now, UpdatedAtUtc = now }));
        database.TanRegistrations.AddRange((request.TanRegistrations ?? []).Select(x => new TanRegistration { Id = Guid.NewGuid(), ClientId = clientId, Tan = ClientRules.NormalizeTaxId(x.Tan)!, DeductorName = Clean(x.DeductorName), Branch = Clean(x.Branch), EffectiveFrom = x.EffectiveFrom, EffectiveTo = x.EffectiveTo, IsPrimary = x.IsPrimary, IsActive = x.IsActive, Notes = Clean(x.Notes), CreatedAtUtc = now, UpdatedAtUtc = now }));
        database.ClientGroupMemberships.AddRange(request.Groups.Select(x => new ClientGroupMembership { Id = Guid.NewGuid(), ClientId = clientId, GroupId = x.GroupId, MembershipType = x.MembershipType.Trim().ToUpperInvariant(), EffectiveFrom = x.EffectiveFrom ?? DateOnly.FromDateTime(now.Date), ValidTo = x.ValidTo, Notes = Clean(x.Notes) }));
    }

    // clients.tan is a denormalised copy of whichever TAN is primary. The registers, exports and
    // reports read that column, so it is refreshed here rather than in each caller.
    private static void SyncPrimaryTan(Client client, ClientUpsertRequest request)
    {
        var supplied = request.TanRegistrations;
        if (supplied is null) return;
        var primary = supplied.FirstOrDefault(x => x.IsPrimary && x.IsActive) ?? supplied.FirstOrDefault(x => x.IsActive);
        client.Tan = primary is null ? null : ClientRules.NormalizeTaxId(primary.Tan);
    }

    private static void ReconcileChildren(Client client, ClientUpsertRequest request, AppDbContext database, DateTimeOffset now)
    {
        var today = DateOnly.FromDateTime(now.Date);
        var contactIds = request.Contacts.Where(x => x.Id is not null).Select(x => x.Id!.Value).ToHashSet();
        foreach (var existing in client.Contacts.Where(x => !contactIds.Contains(x.Id))) { existing.IsActive = false; existing.IsPrimary = false; existing.UpdatedAtUtc = now; }
        foreach (var input in request.Contacts)
        {
            var contact = input.Id is null ? null : client.Contacts.SingleOrDefault(x => x.Id == input.Id);
            if (contact is null) { contact = new ClientContact { Id = Guid.NewGuid(), ClientId = client.Id, ContactType = "GENERAL", Name = string.Empty, CreatedAtUtc = now, UpdatedAtUtc = now }; database.ClientContacts.Add(contact); }
            contact.ContactType = input.ContactType.Trim().ToUpperInvariant(); contact.Name = input.Name.Trim(); contact.Designation = Clean(input.Designation); contact.Phone = Clean(input.Phone); contact.Email = Clean(input.Email)?.ToLowerInvariant(); contact.IsPrimary = input.IsPrimary; contact.IsActive = input.IsActive; contact.Notes = Clean(input.Notes); contact.UpdatedAtUtc = now;
        }
        var tanIds = (request.TanRegistrations ?? []).Where(x => x.Id is not null).Select(x => x.Id!.Value).ToHashSet();
        foreach (var existing in client.TanRegistrations.Where(x => !tanIds.Contains(x.Id))) { existing.IsActive = false; existing.IsPrimary = false; existing.UpdatedAtUtc = now; }
        foreach (var input in request.TanRegistrations ?? [])
        {
            var registration = input.Id is null ? null : client.TanRegistrations.SingleOrDefault(x => x.Id == input.Id);
            if (registration is null) { registration = new TanRegistration { Id = Guid.NewGuid(), ClientId = client.Id, Tan = string.Empty, CreatedAtUtc = now, UpdatedAtUtc = now }; database.TanRegistrations.Add(registration); }
            registration.Tan = ClientRules.NormalizeTaxId(input.Tan)!; registration.DeductorName = Clean(input.DeductorName); registration.Branch = Clean(input.Branch);
            registration.EffectiveFrom = input.EffectiveFrom; registration.EffectiveTo = input.EffectiveTo;
            registration.IsPrimary = input.IsPrimary; registration.IsActive = input.IsActive; registration.Notes = Clean(input.Notes); registration.UpdatedAtUtc = now;
        }

        var addressIds = request.Addresses.Where(x => x.Id is not null).Select(x => x.Id!.Value).ToHashSet();
        foreach (var existing in client.Addresses.Where(x => !addressIds.Contains(x.Id))) { existing.IsActive = false; existing.IsPrimary = false; existing.ValidTo ??= today; existing.UpdatedAtUtc = now; }
        foreach (var input in request.Addresses)
        {
            var address = input.Id is null ? null : client.Addresses.SingleOrDefault(x => x.Id == input.Id);
            if (address is null) { address = new ClientAddress { Id = Guid.NewGuid(), ClientId = client.Id, AddressType = "REGISTERED", Line1 = string.Empty, CountryCode = "IN", ValidFrom = input.ValidFrom ?? today, CreatedAtUtc = now, UpdatedAtUtc = now }; database.ClientAddresses.Add(address); }
            address.AddressType = input.AddressType.Trim().ToUpperInvariant(); address.Line1 = input.Line1.Trim(); address.Line2 = Clean(input.Line2); address.City = Clean(input.City); address.District = Clean(input.District); address.StateCode = Clean(input.StateCode); address.PostalCode = Clean(input.PostalCode); address.CountryCode = string.IsNullOrWhiteSpace(input.CountryCode) ? "IN" : input.CountryCode.Trim().ToUpperInvariant(); address.IsPrimary = input.IsPrimary; address.IsActive = input.IsActive; address.ValidFrom = input.ValidFrom ?? address.ValidFrom; address.ValidTo = input.ValidTo; address.UpdatedAtUtc = now;
        }
        var gstIds = request.GstRegistrations.Where(x => x.Id is not null).Select(x => x.Id!.Value).ToHashSet();
        foreach (var existing in client.GstRegistrations.Where(x => !gstIds.Contains(x.Id))) { existing.IsActive = false; existing.IsPrimary = false; existing.RegistrationStatus = "INACTIVE"; existing.EffectiveTo ??= today; existing.UpdatedAtUtc = now; }
        foreach (var input in request.GstRegistrations)
        {
            var gst = input.Id is null ? null : client.GstRegistrations.SingleOrDefault(x => x.Id == input.Id);
            if (gst is null) { gst = new GstRegistration { Id = Guid.NewGuid(), ClientId = client.Id, Gstin = string.Empty, StateCode = input.StateCode, RegistrationStatus = "ACTIVE", CreatedAtUtc = now, UpdatedAtUtc = now }; database.GstRegistrations.Add(gst); }
            gst.Gstin = ClientRules.NormalizeTaxId(input.Gstin)!; gst.StateCode = input.StateCode; gst.TradeName = Clean(input.TradeName); gst.RegistrationStatus = input.RegistrationStatus.Trim().ToUpperInvariant(); gst.EffectiveFrom = input.EffectiveFrom; gst.EffectiveTo = input.EffectiveTo; gst.IsPrimary = input.IsPrimary; gst.IsActive = input.IsActive; gst.CancellationReason = Clean(input.CancellationReason); gst.UpdatedAtUtc = now;
        }
        var membershipIds = request.Groups.Where(x => x.MembershipId is not null).Select(x => x.MembershipId!.Value).ToHashSet();
        foreach (var existing in client.GroupMemberships.Where(x => !membershipIds.Contains(x.Id))) existing.ValidTo ??= today;
        foreach (var input in request.Groups)
        {
            var membership = input.MembershipId is null ? null : client.GroupMemberships.SingleOrDefault(x => x.Id == input.MembershipId);
            if (membership is null) { membership = new ClientGroupMembership { Id = Guid.NewGuid(), ClientId = client.Id, GroupId = input.GroupId, MembershipType = "SECONDARY", EffectiveFrom = input.EffectiveFrom ?? today }; database.ClientGroupMemberships.Add(membership); }
            membership.GroupId = input.GroupId; membership.MembershipType = input.MembershipType.Trim().ToUpperInvariant(); membership.EffectiveFrom = input.EffectiveFrom ?? membership.EffectiveFrom; membership.ValidTo = input.ValidTo; membership.Notes = Clean(input.Notes);
        }
    }

    private static string[] ChangedFields(Client client, ClientUpsertRequest request)
    {
        var fields = new List<string>();
        if (!string.IsNullOrWhiteSpace(request.ClientCode) && client.NormalizedClientCode != ClientRules.NormalizeCode(request.ClientCode)) fields.Add("clientCode"); if (client.DisplayName != request.DisplayName.Trim()) fields.Add("displayName");
        if (client.LegalName != Clean(request.LegalName)) fields.Add("legalName"); if (client.CategoryId != request.CategoryId) fields.Add("categoryId"); if (client.Pan != ClientRules.NormalizeTaxId(request.Pan)) fields.Add("pan"); if (client.Tan != ClientRules.NormalizeTaxId(request.Tan)) fields.Add("tan"); if (client.OnboardedOn != request.OnboardedOn) fields.Add("onboardedOn"); if (client.Notes != Clean(request.Notes)) fields.Add("notes");
        return fields.ToArray();
    }

    private static IQueryable<Client> OrderClients(IQueryable<Client> query, string? sort, string? direction)
    {
        var descending = string.Equals(direction, "desc", StringComparison.OrdinalIgnoreCase);
        return (sort?.Trim().ToLowerInvariant()) switch
        {
            "code" => descending ? query.OrderByDescending(x => x.NormalizedClientCode) : query.OrderBy(x => x.NormalizedClientCode),
            "category" => descending
                ? query.OrderByDescending(x => x.Category!.Name).ThenBy(x => x.NormalizedDisplayName)
                : query.OrderBy(x => x.Category!.Name).ThenBy(x => x.NormalizedDisplayName),
            "status" => descending
                ? query.OrderByDescending(x => x.Status).ThenBy(x => x.NormalizedDisplayName)
                : query.OrderBy(x => x.Status).ThenBy(x => x.NormalizedDisplayName),
            "group" => descending
                ? query.OrderByDescending(x => x.GroupMemberships.Where(m => m.MembershipType == "PRIMARY" && m.ValidTo == null).Select(m => m.Group.Name).FirstOrDefault())
                    .ThenBy(x => x.NormalizedDisplayName)
                : query.OrderBy(x => x.GroupMemberships.Where(m => m.MembershipType == "PRIMARY" && m.ValidTo == null).Select(m => m.Group.Name).FirstOrDefault())
                    .ThenBy(x => x.NormalizedDisplayName),
            _ => descending
                ? query.OrderByDescending(x => x.NormalizedDisplayName).ThenByDescending(x => x.NormalizedClientCode)
                : query.OrderBy(x => x.NormalizedDisplayName).ThenBy(x => x.NormalizedClientCode)
        };
    }

    private static async Task<IQueryable<Client>> ApplyClientScopeAsync(IQueryable<Client> query, ClaimsPrincipal principal, string permission, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + permission);
        if (scope == "ALL") return query;
        var teamIds = await AccessibleTeamIdsAsync(principal, scope ?? "OWN", database, cancellationToken);
        return query.Where(client => database.ClientServices.Any(agreement => agreement.ClientId == client.Id && agreement.IsActive && agreement.ResponsibleTeamId != null && teamIds.Contains(agreement.ResponsibleTeamId.Value)));
    }
    private static async Task<bool> CanAccessClientAsync(Guid clientId, ClaimsPrincipal principal, string permission, AppDbContext database, CancellationToken cancellationToken)
    {
        var scoped = await ApplyClientScopeAsync(database.Clients.Where(x => x.Id == clientId), principal, permission, database, cancellationToken);
        return await scoped.AnyAsync(cancellationToken);
    }
    private static async Task<Guid[]> AccessibleTeamIdsAsync(ClaimsPrincipal principal, string scope, AppDbContext database, CancellationToken cancellationToken)
    {
        var userId = UserId(principal); var employeeId = await database.Employees.Where(x => x.UserId == userId && x.IsActive).Select(x => (Guid?)x.Id).SingleOrDefaultAsync(cancellationToken); if (employeeId is null) return [];
        var teamIds = database.TeamMemberships.Where(x => x.EmployeeId == employeeId && x.ValidTo == null).Select(x => x.TeamId);
        // TEAM reaches the teams this employee belongs to or personally manages, and stops there.
        // It deliberately does NOT follow direct reports into teams the manager is unconnected to:
        // that widened client visibility here beyond what the client report granted for the same
        // permission and ceiling. The narrower rule is now the single answer for both.
        if (scope == "TEAM")
        {
            teamIds = teamIds.Concat(database.Teams.Where(x => x.ManagerEmployeeId == employeeId && x.IsActive).Select(x => x.Id));
        }
        return await teamIds.Distinct().ToArrayAsync(cancellationToken);
    }
    private static bool HasAllScope(ClaimsPrincipal principal, string permission) => principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + permission) == "ALL";
    private static IResult ScopeDenied() => Results.Problem(statusCode: StatusCodes.Status403Forbidden, title: "Client scope denied", detail: "The client is not routed to a team within your permitted scope.");
    private static Guid UserId(ClaimsPrincipal principal) => Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
    private static string? Clean(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    private static AuditEvent Audit(DateTimeOffset at, Guid actor, string action, Guid entityId, object data, string? reason = null) => new() { Id = Guid.NewGuid(), OccurredAtUtc = at, ActorUserId = actor, Action = action, EntityType = "Client", EntityId = entityId.ToString(), Reason = reason, DataJson = JsonSerializer.Serialize(data) };
}

public sealed record ClientUpsertRequest(string? ClientCode, string? LegacyCode, string DisplayName, string? LegalName, Guid? CategoryId, string? Pan, string? Tan, DateOnly? OnboardedOn, string? Notes, ClientContactInput[] Contacts, ClientAddressInput[] Addresses, GstRegistrationInput[] GstRegistrations, ClientGroupInput[] Groups, TanRegistrationInput[]? TanRegistrations = null);
public sealed record ClientContactInput(string ContactType, string Name, string? Designation, string? Phone, string? Email, bool IsPrimary, bool IsActive, string? Notes, Guid? Id = null);
public sealed record ClientAddressInput(string AddressType, string Line1, string? Line2, string? City, string? District, string? StateCode, string? PostalCode, string? CountryCode, bool IsPrimary, bool IsActive, DateOnly? ValidFrom, DateOnly? ValidTo, Guid? Id = null);
public sealed record GstRegistrationInput(string Gstin, string StateCode, string? TradeName, string RegistrationStatus, DateOnly? EffectiveFrom, DateOnly? EffectiveTo, bool IsPrimary, bool IsActive, string? CancellationReason, Guid? Id = null);
public sealed record ClientGroupInput(Guid GroupId, string MembershipType, DateOnly? EffectiveFrom, DateOnly? ValidTo, string? Notes, Guid? MembershipId = null);
public sealed record ClientStatusRequest(bool IsActive, string Reason);
public sealed record ClientGroupRequest(string Code, string Name, string? Description);

public sealed record ClientListFilters(string? Status, Guid? CategoryId, Guid? GroupId, bool? HasGstin, string? Search);
public sealed record ClientExportRequest(string? Format, ClientListFilters? Filters, string? Sort, string? Direction);
public sealed record ClientCodeSettingsRequest(string? Prefix);
public sealed record TanRegistrationInput(string Tan, string? DeductorName, string? Branch, DateOnly? EffectiveFrom, DateOnly? EffectiveTo, bool IsPrimary, bool IsActive, string? Notes, Guid? Id = null);
