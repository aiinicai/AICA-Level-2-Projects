using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.EntityFrameworkCore;
using Practice.Billing;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;

namespace Practice.Api.Billing;

public static class BillingEndpoints
{
    private static readonly string[] RequiredFieldError = ["This field is required by the current field policy."];

    public static IEndpointRouteBuilder MapBillingEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var group = endpoints.MapGroup("/api/v1/billing").RequireAuthorization("password-current");
        group.MapGet("/masters", MastersAsync).RequireAuthorization(PermissionCodes.BillingView);
        group.MapGet("/entities", ListEntitiesAsync).RequireAuthorization(PermissionCodes.BillingView);
        group.MapPost("/entities", CreateEntityAsync).RequireAuthorization(PermissionCodes.BillingConfigure).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapPut("/entities/{id:guid}", UpdateEntityAsync).RequireAuthorization(PermissionCodes.BillingConfigure).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapPost("/entities/{id:guid}/status", ChangeEntityStatusAsync).RequireAuthorization(PermissionCodes.BillingConfigure).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapGet("/terms", ListTermsAsync).RequireAuthorization(PermissionCodes.BillingView);
        group.MapPost("/terms", CreateTermAsync).RequireAuthorization(PermissionCodes.BillingConfigure).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapPost("/terms/{id:guid}/remove", DeleteTermAsync).RequireAuthorization(PermissionCodes.BillingConfigure).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapPost("/terms/{id:guid}/replace", ReplaceTermAsync).RequireAuthorization(PermissionCodes.BillingConfigure).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        return endpoints;
    }

    private static async Task<IResult> MastersAsync(ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = Scope(principal, PermissionCodes.BillingConfigure) ?? Scope(principal, PermissionCodes.BillingView)!;
        var agreements = await ApplyScopeAsync(database.ClientServices.AsNoTracking().Where(x => x.IsActive && x.Client.Status == "ACTIVE" && x.Service.IsActive), principal, scope, database, cancellationToken);
        return Results.Ok(new
        {
            agreements = await agreements.OrderBy(x => x.Client.DisplayName).ThenBy(x => x.Service.Name).Select(x => new
            {
                x.Id, x.ClientId, clientCode = x.Client.ClientCode, clientName = x.Client.DisplayName,
                serviceCode = x.Service.Code, serviceName = x.Service.Name, gstin = x.GstRegistration == null ? null : x.GstRegistration.Gstin,
                x.ResponsibleTeamId, team = x.ResponsibleTeam == null ? null : x.ResponsibleTeam.Name,
                x.EffectiveFrom, x.EffectiveTo
            }).ToArrayAsync(cancellationToken),
            entities = await database.BillingEntities.AsNoTracking().Where(x => x.IsActive).OrderBy(x => x.LegalName).Select(x => new { x.Id, x.Code, x.LegalName, x.CurrencyCode, x.EffectiveFrom, x.EffectiveTo }).ToArrayAsync(cancellationToken),
            requiredEntityFields = await RequiredFieldsAsync(database, "billing.billing_entity", cancellationToken),
            requiredTermFields = await RequiredFieldsAsync(database, "billing.billing_term", cancellationToken),
            frequencies = BillingRules.Frequencies,
            businessDayAdjustments = BillingRules.BusinessDayAdjustments
        });
    }

    private static async Task<IResult> ListEntitiesAsync(bool? includeInactive, AppDbContext database, CancellationToken cancellationToken)
    {
        var query = database.BillingEntities.AsNoTracking(); if (includeInactive != true) query = query.Where(x => x.IsActive);
        return Results.Ok(await query.OrderBy(x => x.LegalName).Select(x => new
        {
            x.Id, x.Code, x.LegalName, x.TradeName, x.Pan, x.Gstin, x.Address, x.Email, x.Phone,
            x.CurrencyCode, x.EffectiveFrom, x.EffectiveTo, x.IsActive, x.RowVersion,
            activeTermCount = x.Terms.Count(term => term.EffectiveTo == null || term.EffectiveTo >= DateOnly.FromDateTime(DateTime.UtcNow))
        }).ToArrayAsync(cancellationToken));
    }

    private static async Task<IResult> CreateEntityAsync(BillingEntityRequest request, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        if (!HasAllConfigure(principal)) return ScopeDenied("Only ALL-scope billing administrators may create legal billing entities.");
        var values = Normalize(request); var errors = await ValidateEntityAsync(values, null, database, cancellationToken); if (errors.Count > 0) return Results.ValidationProblem(errors);
        var now = clock.UtcNow; var entity = new BillingEntity
        {
            Id = Guid.NewGuid(), Code = values.Code, LegalName = values.LegalName, TradeName = values.TradeName,
            Pan = values.Pan, Gstin = values.Gstin, Address = values.Address, Email = values.Email, Phone = values.Phone,
            CurrencyCode = values.CurrencyCode, EffectiveFrom = values.EffectiveFrom, EffectiveTo = values.EffectiveTo,
            CreatedAtUtc = now, UpdatedAtUtc = now
        };
        database.BillingEntities.Add(entity); database.AuditEvents.Add(Audit(now, UserId(principal), "billing.entity_created", "BillingEntity", entity.Id, new { entity.Code, entity.LegalName }));
        await database.SaveChangesAsync(cancellationToken); return Results.Created($"/api/v1/billing/entities/{entity.Id}", new { entity.Id });
    }

    private static async Task<IResult> UpdateEntityAsync(Guid id, BillingEntityRequest request, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        if (!HasAllConfigure(principal)) return ScopeDenied("Only ALL-scope billing administrators may edit legal billing entities.");
        var entity = await database.BillingEntities.SingleOrDefaultAsync(x => x.Id == id, cancellationToken); if (entity is null) return Results.NotFound();
        if (entity.RowVersion != request.ExpectedVersion) return Results.Conflict(new { message = "The billing entity changed after it was opened. Reload and retry." });
        var values = Normalize(request); var errors = await ValidateEntityAsync(values, id, database, cancellationToken); if (errors.Count > 0) return Results.ValidationProblem(errors);
        var hasTerms = await database.BillingTerms.AnyAsync(x => x.BillingEntityId == id, cancellationToken);
        if (hasTerms && !string.Equals(entity.CurrencyCode, values.CurrencyCode, StringComparison.Ordinal)) return Results.Conflict(new { message = "The currency of a billing entity with fee history cannot be changed. Create a separate legal entity instead." });
        if (await database.BillingTerms.AnyAsync(x => x.BillingEntityId == id && (x.EffectiveFrom < values.EffectiveFrom || (values.EffectiveTo != null && (x.EffectiveTo == null || x.EffectiveTo > values.EffectiveTo))), cancellationToken)) return Results.Conflict(new { message = "The proposed entity dates would exclude existing fee history." });
        var old = new { entity.Code, entity.LegalName, entity.TradeName, entity.Pan, entity.Gstin, entity.Address, entity.Email, entity.Phone, entity.CurrencyCode, entity.EffectiveFrom, entity.EffectiveTo };
        entity.Code = values.Code; entity.LegalName = values.LegalName; entity.TradeName = values.TradeName; entity.Pan = values.Pan; entity.Gstin = values.Gstin;
        entity.Address = values.Address; entity.Email = values.Email; entity.Phone = values.Phone; entity.CurrencyCode = values.CurrencyCode;
        entity.EffectiveFrom = values.EffectiveFrom; entity.EffectiveTo = values.EffectiveTo; entity.RowVersion++; entity.UpdatedAtUtc = clock.UtcNow;
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(principal), "billing.entity_updated", "BillingEntity", entity.Id, new { old, current = values }));
        await database.SaveChangesAsync(cancellationToken); return Results.Ok(new { entity.Id, entity.RowVersion });
    }

    private static async Task<IResult> ChangeEntityStatusAsync(Guid id, BillingEntityStatusRequest request, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        if (!HasAllConfigure(principal)) return ScopeDenied("Only ALL-scope billing administrators may change legal billing entity status.");
        if (string.IsNullOrWhiteSpace(request.Reason)) return Validation("reason", "A reason is required.");
        var entity = await database.BillingEntities.SingleOrDefaultAsync(x => x.Id == id, cancellationToken); if (entity is null) return Results.NotFound();
        if (entity.RowVersion != request.ExpectedVersion) return Results.Conflict(new { message = "The billing entity changed after it was opened. Reload and retry." });
        if (!request.IsActive && await database.BillingTerms.AnyAsync(x => x.BillingEntityId == id && (x.EffectiveTo == null || x.EffectiveTo >= DateOnly.FromDateTime(clock.UtcNow.UtcDateTime)), cancellationToken))
            return Results.Conflict(new { message = "End or replace current and future fee terms before deactivating this billing entity." });
        entity.IsActive = request.IsActive; entity.RowVersion++; entity.UpdatedAtUtc = clock.UtcNow;
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(principal), request.IsActive ? "billing.entity_reactivated" : "billing.entity_deactivated", "BillingEntity", entity.Id, new { entity.Code }, request.Reason.Trim()));
        await database.SaveChangesAsync(cancellationToken); return Results.Ok(new { entity.Id, entity.IsActive, entity.RowVersion });
    }

    private static async Task<IResult> ListTermsAsync(Guid? clientServiceId, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = Scope(principal, PermissionCodes.BillingView)!; var agreements = await ApplyScopeAsync(database.ClientServices.AsNoTracking(), principal, scope, database, cancellationToken);
        var agreementIds = agreements.Select(x => x.Id); var query = database.BillingTerms.AsNoTracking().Where(x => agreementIds.Contains(x.ClientServiceId));
        if (clientServiceId is not null) query = query.Where(x => x.ClientServiceId == clientServiceId);
        return Results.Ok(await query.OrderBy(x => x.ClientService.Client.DisplayName).ThenBy(x => x.ClientService.Service.Name).ThenByDescending(x => x.EffectiveFrom).Select(x => new
        {
            x.Id, x.ClientServiceId,
            // The timeline shows terms for closed agreements too, so the screen needs to know which
            // ones can still be revised rather than offering an action that will be refused.
            agreementIsActive = x.ClientService.IsActive && x.ClientService.Client.Status == "ACTIVE" && x.ClientService.Service.IsActive,
            clientCode = x.ClientService.Client.ClientCode, clientName = x.ClientService.Client.DisplayName,
            serviceName = x.ClientService.Service.Name, gstin = x.ClientService.GstRegistration == null ? null : x.ClientService.GstRegistration.Gstin,
            x.BillingEntityId, billingEntityCode = x.BillingEntity == null ? null : x.BillingEntity.Code, billingEntityName = x.BillingEntity == null ? null : x.BillingEntity.LegalName,
            x.IsBillable, x.PricingModel, x.Amount, x.CurrencyCode, x.TaxInclusive, x.EffectiveFrom, x.EffectiveTo, x.Version, x.Notes,
            schedule = x.Schedule == null ? null : new { x.Schedule.FrequencyCode, x.Schedule.IntervalMonths, x.Schedule.AnchorDate, x.Schedule.BillingDay, x.Schedule.BusinessDayAdjustment, x.Schedule.OneTimeDate, months = x.Schedule.Months.OrderBy(month => month.Month).Select(month => month.Month).ToArray() }
        }).ToArrayAsync(cancellationToken));
    }

    private static async Task<IResult> CreateTermAsync(BillingTermRequest request, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var validation = await ValidateTermAsync(request, null, principal, database, cancellationToken); if (validation.Result is not null) return validation.Result;
        var version = await database.BillingTerms.Where(x => x.ClientServiceId == request.ClientServiceId).Select(x => (int?)x.Version).MaxAsync(cancellationToken) ?? 0;
        var term = NewTerm(request, version + 1, UserId(principal), clock.UtcNow); database.BillingTerms.Add(term);
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(principal), "billing.term_created", "BillingTerm", term.Id, AuditTerm(term)));
        return await SaveTermAsync(database, term, cancellationToken);
    }

    private static async Task<IResult> ReplaceTermAsync(Guid id, BillingTermRequest request, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var prior = await database.BillingTerms.Include(x => x.ClientService).SingleOrDefaultAsync(x => x.Id == id, cancellationToken); if (prior is null) return Results.NotFound();
        if (request.ClientServiceId != prior.ClientServiceId) return Validation("clientServiceId", "A replacement must belong to the same client-service agreement.");
        // The agreement is fixed when replacing, so "choose an active agreement" would be advice the
        // form cannot act on. Say what is actually wrong instead.
        var priorAgreement = await database.ClientServices.Include(x => x.Client).Include(x => x.Service)
            .SingleAsync(x => x.Id == prior.ClientServiceId, cancellationToken);
        if (!priorAgreement.IsActive || priorAgreement.Client.Status != "ACTIVE" || !priorAgreement.Service.IsActive)
        {
            var cause = !priorAgreement.IsActive ? "the client-service agreement has been closed"
                : priorAgreement.Client.Status != "ACTIVE" ? "the client is inactive"
                : "the service has been deactivated";
            return Validation("clientServiceId", $"This fee cannot be changed because {cause}. Reactivate it first, then revise the fee.");
        }
        if (request.EffectiveFrom <= prior.EffectiveFrom) return Validation("effectiveFrom", "A replacement must start after the prior term began.");
        if (prior.EffectiveTo is not null && request.EffectiveFrom > prior.EffectiveTo) return Results.Conflict(new { message = "This term already ended before the proposed replacement date. Create a new non-overlapping term instead." });
        var validation = await ValidateTermAsync(request, id, principal, database, cancellationToken); if (validation.Result is not null) return validation.Result;
        prior.EffectiveTo = request.EffectiveFrom.AddDays(-1);
        var term = NewTerm(request, prior.Version + 1, UserId(principal), clock.UtcNow); database.BillingTerms.Add(term);
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(principal), "billing.term_replaced", "BillingTerm", term.Id, new { priorTermId = prior.Id, priorEffectiveTo = prior.EffectiveTo, current = AuditTerm(term) }));
        return await SaveTermAsync(database, term, cancellationToken);
    }

    // Removal is a POST rather than a DELETE because it carries a reason, and Minimal APIs do not
    // infer a body on DELETE. It also matches how the other reasoned actions here are shaped.
    // Effective-dated history is not rewritten, so only the current version can be removed, and only
    // as a correction. Removing it reopens the version it replaced, which is the state that existed
    // before the mistake. Superseded versions stay, because they describe what was actually agreed.
    private static async Task<IResult> DeleteTermAsync(
        Guid id, DeleteTermRequest request, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var term = await database.BillingTerms.Include(x => x.ClientService)
            .SingleOrDefaultAsync(x => x.Id == id, cancellationToken);
        if (term is null) return Results.NotFound();

        var scope = Scope(principal, PermissionCodes.BillingConfigure)!;
        if (await ValidateAgreementScopeAsync(term.ClientService, principal, scope, database, cancellationToken) is { } denied) return denied;

        if (string.IsNullOrWhiteSpace(request.Reason))
        {
            return Validation("reason", "Give a reason for removing this fee, so the correction is explainable later.");
        }

        var latestVersion = await database.BillingTerms
            .Where(x => x.ClientServiceId == term.ClientServiceId)
            .MaxAsync(x => x.Version, cancellationToken);
        if (term.Version != latestVersion)
        {
            return Results.Conflict(new { message = "Only the current fee can be removed. Earlier versions record what was actually agreed and are kept." });
        }

        var prior = await database.BillingTerms
            .Where(x => x.ClientServiceId == term.ClientServiceId && x.Version < term.Version)
            .OrderByDescending(x => x.Version).FirstOrDefaultAsync(cancellationToken);

        var now = clock.UtcNow;
        if (prior is not null)
        {
            prior.EffectiveTo = null;
        }

        database.AuditEvents.Add(Audit(now, UserId(principal), "billing.term_removed", "BillingTerm", term.Id,
            new { term.ClientServiceId, term.Version, term.EffectiveFrom, term.Amount, term.CurrencyCode, reopenedPriorVersion = prior?.Version },
            request.Reason.Trim()));
        database.BillingTerms.Remove(term);
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<(IResult? Result, ClientService? Agreement)> ValidateTermAsync(BillingTermRequest request, Guid? ignoredTermId, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var agreement = await database.ClientServices.Include(x => x.Client).Include(x => x.Service).SingleOrDefaultAsync(x => x.Id == request.ClientServiceId, cancellationToken);
        if (agreement is null || !agreement.IsActive || agreement.Client.Status != "ACTIVE" || !agreement.Service.IsActive) return (Validation("clientServiceId", "Choose an active client-service agreement."), null);
        var scope = Scope(principal, PermissionCodes.BillingConfigure)!; if (await ValidateAgreementScopeAsync(agreement, principal, scope, database, cancellationToken) is { } denied) return (denied, null);
        var errors = new Dictionary<string, string[]>();
        if (request.EffectiveTo is not null && request.EffectiveTo < request.EffectiveFrom) errors["effectiveTo"] = ["Effective-to date cannot precede effective-from date."];
        if (request.EffectiveFrom < agreement.EffectiveFrom || (agreement.EffectiveTo is not null && (request.EffectiveTo is null || request.EffectiveTo > agreement.EffectiveTo))) errors["effectiveDates"] = ["Billing term dates must remain within the client-service agreement dates."];
        var required = await RequiredFieldsAsync(database, "billing.billing_term", cancellationToken); if (required.Contains("notes") && string.IsNullOrWhiteSpace(request.Notes)) errors["notes"] = RequiredFieldError;
        if (request.IsBillable)
        {
            if (request.Amount is null || request.Amount < 0) errors["amount"] = ["A non-negative fixed fee is required."];
            if (request.BillingEntityId is null) errors["billingEntityId"] = ["A billing entity is required."];
            var entity = request.BillingEntityId is null ? null : await database.BillingEntities.AsNoTracking().SingleOrDefaultAsync(x => x.Id == request.BillingEntityId && x.IsActive, cancellationToken);
            if (entity is null) errors["billingEntityId"] = ["Choose an active billing entity."];
            else
            {
                if (!string.Equals(request.CurrencyCode, entity.CurrencyCode, StringComparison.OrdinalIgnoreCase)) errors["currencyCode"] = ["The term currency must match the billing entity currency."];
                if (request.EffectiveFrom < entity.EffectiveFrom || (entity.EffectiveTo is not null && (request.EffectiveTo is null || request.EffectiveTo > entity.EffectiveTo))) errors["billingEntityDates"] = ["The billing entity must be effective for the complete term."];
            }
            if (request.Schedule is null) errors["schedule"] = ["A billing schedule is required for a billable term."];
            else
            {
                var scheduleErrors = BillingRules.ValidateSchedule(request.Schedule.FrequencyCode.Trim().ToUpperInvariant(), request.Schedule.AnchorDate, request.Schedule.BillingDay, request.Schedule.OneTimeDate, request.Schedule.Months, request.Schedule.BusinessDayAdjustment.Trim().ToUpperInvariant());
                if (scheduleErrors.Count > 0) errors["schedule"] = scheduleErrors.ToArray();
            }
        }
        else if (request.BillingEntityId is not null || request.Amount is not null || request.Schedule is not null) errors["isBillable"] = ["A non-billable term cannot have an entity, amount, or billing schedule."];
        var overlap = await database.BillingTerms.AnyAsync(x => x.ClientServiceId == request.ClientServiceId && x.Id != ignoredTermId && x.EffectiveFrom <= (request.EffectiveTo ?? DateOnly.MaxValue) && (x.EffectiveTo == null || x.EffectiveTo >= request.EffectiveFrom), cancellationToken);
        if (overlap) errors["effectiveDates"] = ["Billing terms for one client-service agreement cannot overlap."];
        return errors.Count > 0 ? (Results.ValidationProblem(errors), agreement) : (null, agreement);
    }

    private static BillingTerm NewTerm(BillingTermRequest request, int version, Guid actor, DateTimeOffset now)
    {
        var term = new BillingTerm
        {
            Id = Guid.NewGuid(), ClientServiceId = request.ClientServiceId, BillingEntityId = request.IsBillable ? request.BillingEntityId : null,
            IsBillable = request.IsBillable, PricingModel = "FIXED", Amount = request.IsBillable ? request.Amount : null,
            CurrencyCode = request.IsBillable ? request.CurrencyCode.Trim().ToUpperInvariant() : "INR", TaxInclusive = request.IsBillable && request.TaxInclusive,
            EffectiveFrom = request.EffectiveFrom, EffectiveTo = request.EffectiveTo, Version = version, Notes = Clean(request.Notes), CreatedAtUtc = now, CreatedByUserId = actor
        };
        if (request.IsBillable && request.Schedule is not null)
        {
            var frequency = request.Schedule.FrequencyCode.Trim().ToUpperInvariant(); term.Schedule = new BillingSchedule
            {
                BillingTermId = term.Id, FrequencyCode = frequency, IntervalMonths = BillingRules.IntervalMonths(frequency), AnchorDate = request.Schedule.AnchorDate,
                BillingDay = request.Schedule.BillingDay, OneTimeDate = request.Schedule.OneTimeDate,
                BusinessDayAdjustment = request.Schedule.BusinessDayAdjustment.Trim().ToUpperInvariant(), ProjectionTiming = "PER_BILLING_EVENT"
            };
            foreach (var month in request.Schedule.Months.Distinct().Order()) term.Schedule.Months.Add(new BillingScheduleMonth { BillingTermId = term.Id, Month = month });
        }
        return term;
    }

    private static async Task<IResult> SaveTermAsync(AppDbContext database, BillingTerm term, CancellationToken cancellationToken)
    {
        try { await database.SaveChangesAsync(cancellationToken); }
        catch (DbUpdateException exception) when (exception.InnerException?.Message.Contains("ex_billing_terms_no_overlap", StringComparison.Ordinal) == true || exception.InnerException?.Message.Contains("ux_billing_terms_agreement_version", StringComparison.Ordinal) == true)
        { return Results.Conflict(new { message = "Another billing-term change was saved first. Reload the timeline and retry." }); }
        return Results.Created($"/api/v1/billing/terms/{term.Id}", new { term.Id, term.Version });
    }

    private static async Task<Dictionary<string, string[]>> ValidateEntityAsync(BillingEntityRequest request, Guid? currentId, AppDbContext database, CancellationToken cancellationToken)
    {
        var errors = new Dictionary<string, string[]>(); var required = await RequiredFieldsAsync(database, "billing.billing_entity", cancellationToken);
        foreach (var (key, value) in new Dictionary<string, string?> { ["code"] = request.Code, ["legalName"] = request.LegalName, ["tradeName"] = request.TradeName, ["pan"] = request.Pan, ["gstin"] = request.Gstin, ["address"] = request.Address, ["email"] = request.Email }) if (required.Contains(key) && string.IsNullOrWhiteSpace(value)) errors[key] = RequiredFieldError;
        if (request.Code.Length is < 2 or > 30) errors["code"] = ["Code must contain 2 to 30 usable characters."];
        if (request.LegalName.Length is < 2 or > 200) errors["legalName"] = ["Legal name must contain 2 to 200 usable characters."];
        if (!ClientRules.IsValidPan(request.Pan)) errors["pan"] = ["PAN format is invalid."];
        if (request.Gstin is not null && !ClientRules.IsValidGstin(request.Gstin)) errors["gstin"] = ["GSTIN format or checksum is invalid."];
        if (request.CurrencyCode.Length != 3 || request.CurrencyCode.Any(c => !char.IsAsciiLetterUpper(c))) errors["currencyCode"] = ["Currency must be a three-letter ISO code."];
        if (request.EffectiveTo is not null && request.EffectiveTo < request.EffectiveFrom) errors["effectiveTo"] = ["Effective-to date cannot precede effective-from date."];
        if (await database.BillingEntities.AnyAsync(x => x.Id != currentId && x.Code == request.Code, cancellationToken)) errors["code"] = ["Billing entity code already exists."];
        if (request.Gstin is not null && await database.BillingEntities.AnyAsync(x => x.Id != currentId && x.Gstin == request.Gstin, cancellationToken)) errors["gstin"] = ["GSTIN is already assigned to another billing entity."];
        return errors;
    }

    private static BillingEntityRequest Normalize(BillingEntityRequest request) => request with
    {
        Code = ClientRules.NormalizeCode(request.Code), LegalName = Clean(request.LegalName) ?? string.Empty, TradeName = Clean(request.TradeName),
        Pan = ClientRules.NormalizeTaxId(request.Pan), Gstin = ClientRules.NormalizeTaxId(request.Gstin), Address = Clean(request.Address), Email = Clean(request.Email)?.ToLowerInvariant(),
        Phone = Clean(request.Phone), CurrencyCode = request.CurrencyCode.Trim().ToUpperInvariant()
    };

    private static async Task<IQueryable<ClientService>> ApplyScopeAsync(IQueryable<ClientService> query, ClaimsPrincipal principal, string scope, AppDbContext database, CancellationToken cancellationToken)
    { if (scope == "ALL") return query; var teams = await AccessibleTeamIdsAsync(principal, scope, database, cancellationToken); return query.Where(x => x.ResponsibleTeamId != null && teams.Contains(x.ResponsibleTeamId.Value)); }
    private static async Task<IResult?> ValidateAgreementScopeAsync(ClientService agreement, ClaimsPrincipal principal, string scope, AppDbContext database, CancellationToken cancellationToken)
    { if (scope == "ALL") return null; if (agreement.ResponsibleTeamId is null) return ScopeDenied("Scoped billing configuration requires a responsible team on the client-service agreement."); var teams = await AccessibleTeamIdsAsync(principal, scope, database, cancellationToken); return teams.Contains(agreement.ResponsibleTeamId.Value) ? null : ScopeDenied("The client-service agreement is outside your billing scope."); }
    private static async Task<Guid[]> AccessibleTeamIdsAsync(ClaimsPrincipal principal, string scope, AppDbContext database, CancellationToken cancellationToken)
    {
        var employeeId = await database.Employees.Where(x => x.UserId == UserId(principal) && x.IsActive).Select(x => (Guid?)x.Id).SingleOrDefaultAsync(cancellationToken); if (employeeId is null) return [];
        var teamIds = database.TeamMemberships.Where(x => x.EmployeeId == employeeId && x.ValidTo == null).Select(x => x.TeamId);
        // TEAM reaches teams this employee belongs to or personally manages, and stops there.
        // Kept identical to the client, reporting, scheduling and service rules.
        if (scope == "TEAM") { teamIds = teamIds.Concat(database.Teams.Where(x => x.ManagerEmployeeId == employeeId && x.IsActive).Select(x => x.Id)); }
        return await teamIds.Distinct().ToArrayAsync(cancellationToken);
    }
    private static Task<string[]> RequiredFieldsAsync(AppDbContext database, string entityType, CancellationToken cancellationToken) => database.FieldDefinitions.AsNoTracking().Where(x => x.EntityType == entityType && x.IsActive && x.IsAdministratorRequired).Select(x => x.FieldKey).ToArrayAsync(cancellationToken);
    private static bool HasAllConfigure(ClaimsPrincipal principal) => Scope(principal, PermissionCodes.BillingConfigure) == "ALL";
    private static string? Scope(ClaimsPrincipal principal, string permission) => principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + permission);
    private static Guid UserId(ClaimsPrincipal principal) => Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
    private static string? Clean(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    private static IResult Validation(string key, string message) => Results.ValidationProblem(new Dictionary<string, string[]> { [key] = [message] });
    private static IResult ScopeDenied(string detail) => Results.Problem(statusCode: 403, title: "Billing scope denied", detail: detail);
    private static object AuditTerm(BillingTerm term) => new { term.ClientServiceId, term.BillingEntityId, term.IsBillable, term.Amount, term.CurrencyCode, term.TaxInclusive, term.EffectiveFrom, term.EffectiveTo, term.Version, frequency = term.Schedule?.FrequencyCode };
    private static AuditEvent Audit(DateTimeOffset at, Guid actor, string action, string entityType, Guid id, object data, string? reason = null) => new() { Id = Guid.NewGuid(), OccurredAtUtc = at, ActorUserId = actor, Action = action, EntityType = entityType, EntityId = id.ToString(), Reason = reason, DataJson = JsonSerializer.Serialize(data) };
}

public sealed record BillingEntityRequest(string Code, string LegalName, string? TradeName, string? Pan, string? Gstin, string? Address, string? Email, string? Phone, string CurrencyCode, DateOnly EffectiveFrom, DateOnly? EffectiveTo, long ExpectedVersion = 0);
public sealed record BillingEntityStatusRequest(bool IsActive, string Reason, long ExpectedVersion);
public sealed record BillingScheduleRequest(string FrequencyCode, DateOnly? AnchorDate, int? BillingDay, string BusinessDayAdjustment, DateOnly? OneTimeDate, int[] Months);
public sealed record BillingTermRequest(Guid ClientServiceId, bool IsBillable, Guid? BillingEntityId, decimal? Amount, string CurrencyCode, bool TaxInclusive, DateOnly EffectiveFrom, DateOnly? EffectiveTo, string? Notes, BillingScheduleRequest? Schedule);
public sealed record DeleteTermRequest(string? Reason);
