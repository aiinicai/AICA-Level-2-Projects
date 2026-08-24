using System.Globalization;
using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;
using Practice.Scheduling;

namespace Practice.Api.Services;

public static class ServiceEndpoints
{
    private static readonly string[] RequiredFieldError = ["This field is required by the current field policy."];

    public static IEndpointRouteBuilder MapServiceEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var catalogue = endpoints.MapGroup("/api/v1/services").RequireAuthorization("password-current");
        catalogue.MapGet("/", ListCatalogueAsync).RequireAuthorization(PermissionCodes.ServicesView);
        catalogue.MapGet("/masters", GetMastersAsync).RequireAuthorization(PermissionCodes.ServicesView);
        catalogue.MapPost("/categories", CreateCategoryAsync).RequireAuthorization(PermissionCodes.ServicesCatalogueManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        catalogue.MapPost("/", CreateServiceAsync).RequireAuthorization(PermissionCodes.ServicesCatalogueManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        catalogue.MapPut("/{id:guid}", UpdateServiceAsync).RequireAuthorization(PermissionCodes.ServicesCatalogueManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        catalogue.MapPost("/{id:guid}/status", ChangeServiceStatusAsync).RequireAuthorization(PermissionCodes.ServicesCatalogueManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));

        var agreements = endpoints.MapGroup("/api/v1/client-services").RequireAuthorization("password-current");
        agreements.MapPost("/schedule-preview", PreviewEnrolmentScheduleAsync).RequireAuthorization(PermissionCodes.ServiceEnrollmentsView).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        agreements.MapGet("/", ListAgreementsAsync).RequireAuthorization(PermissionCodes.ServiceEnrollmentsView);
        agreements.MapGet("/{id:guid}", GetAgreementAsync).RequireAuthorization(PermissionCodes.ServiceEnrollmentsView);
        agreements.MapPost("/", CreateAgreementAsync).RequireAuthorization(PermissionCodes.ServiceEnrollmentsManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        agreements.MapPut("/{id:guid}", UpdateAgreementAsync).RequireAuthorization(PermissionCodes.ServiceEnrollmentsManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        agreements.MapPost("/{id:guid}/status", ChangeAgreementStatusAsync).RequireAuthorization(PermissionCodes.ServiceEnrollmentsManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        return endpoints;
    }

    private static async Task<IResult> ListCatalogueAsync(bool? includeInactive, AppDbContext database, CancellationToken cancellationToken)
    {
        var query = database.Services.AsNoTracking();
        if (includeInactive != true) query = query.Where(x => x.IsActive);
        return Results.Ok(await query.OrderBy(x => x.Category.DisplayOrder).ThenBy(x => x.Name).Select(x => new
        {
            x.Id, x.Code, x.Name, x.Description, x.CategoryId, category = x.Category.Name,
            x.DefaultBillable, x.SupportsRecurrence, x.SupportsGstinScope, x.IsActive,
            activeEnrollmentCount = x.ClientServices.Count(cs => cs.IsActive)
        }).ToArrayAsync(cancellationToken));
    }

    private static async Task<IResult> GetMastersAsync(ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var categories = await database.ServiceCategories.AsNoTracking().Where(x => x.IsActive).OrderBy(x => x.DisplayOrder).Select(x => new { x.Id, x.Code, x.Name }).ToArrayAsync(cancellationToken);
        var teams = await database.Teams.AsNoTracking().Where(x => x.IsActive).OrderBy(x => x.Name).Select(x => new { x.Id, x.Code, x.Name }).ToArrayAsync(cancellationToken);
        var requiredFields = await database.FieldDefinitions.AsNoTracking().Where(x => x.EntityType == "services.client_service" && x.IsActive && x.IsAdministratorRequired).Select(x => x.FieldKey).ToArrayAsync(cancellationToken);
        var scope = Scope(principal, PermissionCodes.ServiceEnrollmentsManage) ?? Scope(principal, PermissionCodes.ServiceEnrollmentsView);
        var clientQuery = database.Clients.AsNoTracking().Where(x => x.Status == "ACTIVE");
        if (scope is not null && scope != "ALL")
        {
            var accessibleTeams = await AccessibleTeamIdsAsync(principal, scope, database, cancellationToken);
            clientQuery = clientQuery.Where(x => database.ClientServices.Any(cs => cs.ClientId == x.Id && cs.IsActive && cs.ResponsibleTeamId != null && accessibleTeams.Contains(cs.ResponsibleTeamId.Value)));
        }
        var clients = await clientQuery.OrderBy(x => x.NormalizedDisplayName).Select(x => new
        {
            x.Id, x.ClientCode, x.DisplayName,
            gstRegistrations = x.GstRegistrations.Where(g => g.IsActive).OrderByDescending(g => g.IsPrimary).Select(g => new { g.Id, g.Gstin, g.StateCode, g.TradeName }).ToArray()
        }).ToArrayAsync(cancellationToken);
        // Offered so an enrolment can name the person its generated tasks go to.
        var employees = await database.Employees.AsNoTracking().Where(x => x.IsActive)
            .OrderBy(x => x.DisplayName).Select(x => new { x.Id, x.EmployeeCode, x.DisplayName }).ToArrayAsync(cancellationToken);
        return Results.Ok(new { categories, teams, clients, requiredFields, employees });
    }

    private static async Task<IResult> CreateCategoryAsync(ServiceCategoryRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var code = NormalizeCode(request.Code); var name = request.Name.Trim();
        if (code.Length is < 2 or > 50 || name.Length is < 2 or > 120) return Results.ValidationProblem(new Dictionary<string, string[]> { ["category"] = ["Category code and name must contain 2 to 50/120 characters."] });
        if (await database.ServiceCategories.AnyAsync(x => x.Code == code || x.NormalizedName == NormalizeName(name), cancellationToken)) return Results.Conflict(new { message = "Service category code or name already exists." });
        var category = new ServiceCategory { Id = Guid.NewGuid(), Code = code, Name = name, NormalizedName = NormalizeName(name), DisplayOrder = request.DisplayOrder, IsActive = true };
        database.ServiceCategories.Add(category); database.AuditEvents.Add(Audit(clock.UtcNow, UserId(context.User), "services.category_created", "ServiceCategory", category.Id, new { category.Code, category.Name }));
        await database.SaveChangesAsync(cancellationToken); return Results.Created($"/api/v1/services/categories/{category.Id}", new { category.Id, category.Code, category.Name });
    }

    private static async Task<IResult> CreateServiceAsync(ServiceUpsertRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var errors = await ValidateServiceAsync(request, null, database, cancellationToken); if (errors.Count > 0) return Results.ValidationProblem(errors);
        var now = clock.UtcNow; var service = new ServiceDefinition { Id = Guid.NewGuid(), CategoryId = request.CategoryId, Code = NormalizeCode(request.Code), Name = request.Name.Trim(), NormalizedName = NormalizeName(request.Name), Description = Clean(request.Description), DefaultBillable = request.DefaultBillable, SupportsRecurrence = request.SupportsRecurrence, SupportsGstinScope = request.SupportsGstinScope, IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now };
        database.Services.Add(service); database.AuditEvents.Add(Audit(now, UserId(context.User), "services.created", "ServiceDefinition", service.Id, new { service.Code, service.Name, service.DefaultBillable, service.SupportsRecurrence, service.SupportsGstinScope }));
        await database.SaveChangesAsync(cancellationToken); return Results.Created($"/api/v1/services/{service.Id}", new { service.Id, service.Code, service.Name });
    }

    private static async Task<IResult> UpdateServiceAsync(Guid id, ServiceUpsertRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var service = await database.Services.SingleOrDefaultAsync(x => x.Id == id, cancellationToken); if (service is null) return Results.NotFound();
        var errors = await ValidateServiceAsync(request, id, database, cancellationToken); if (errors.Count > 0) return Results.ValidationProblem(errors);
        var changed = new List<string>(); if (service.Name != request.Name.Trim()) changed.Add("name"); if (service.CategoryId != request.CategoryId) changed.Add("categoryId"); if (service.DefaultBillable != request.DefaultBillable) changed.Add("defaultBillable"); if (service.SupportsRecurrence != request.SupportsRecurrence) changed.Add("supportsRecurrence"); if (service.SupportsGstinScope != request.SupportsGstinScope) changed.Add("supportsGstinScope");
        service.CategoryId = request.CategoryId; service.Name = request.Name.Trim(); service.NormalizedName = NormalizeName(request.Name); service.Description = Clean(request.Description); service.DefaultBillable = request.DefaultBillable; service.SupportsRecurrence = request.SupportsRecurrence; service.SupportsGstinScope = request.SupportsGstinScope; service.UpdatedAtUtc = clock.UtcNow;
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(context.User), "services.updated", "ServiceDefinition", service.Id, new { changedFields = changed, defaultsApplyToNewEnrollmentsOnly = true }));
        await database.SaveChangesAsync(cancellationToken); return Results.NoContent();
    }

    private static async Task<IResult> ChangeServiceStatusAsync(Guid id, MasterStatusRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var service = await database.Services.SingleOrDefaultAsync(x => x.Id == id, cancellationToken); if (service is null) return Results.NotFound();
        if (!request.IsActive)
        {
            var active = await database.ClientServices.CountAsync(x => x.ServiceId == id && x.IsActive, cancellationToken);
            if (active > 0) return Results.Conflict(new { message = $"Service has {active} active client agreement(s). Deactivate those agreements first.", activeAgreementCount = active });
            if (string.IsNullOrWhiteSpace(request.Reason)) return Results.ValidationProblem(new Dictionary<string, string[]> { ["reason"] = ["A reason is required."] });
        }
        service.IsActive = request.IsActive; service.UpdatedAtUtc = clock.UtcNow; database.AuditEvents.Add(Audit(clock.UtcNow, UserId(context.User), request.IsActive ? "services.reactivated" : "services.deactivated", "ServiceDefinition", service.Id, new { request.Reason }, request.Reason));
        await database.SaveChangesAsync(cancellationToken); return Results.NoContent();
    }

    private static async Task<IResult> ListAgreementsAsync(Guid? clientId, bool? includeInactive, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = Scope(principal, PermissionCodes.ServiceEnrollmentsView)!; var query = database.ClientServices.AsNoTracking();
        if (includeInactive != true) query = query.Where(x => x.IsActive); if (clientId is not null) query = query.Where(x => x.ClientId == clientId);
        query = await ApplyScopeAsync(query, principal, scope, database, cancellationToken);
        return Results.Ok(await query.OrderBy(x => x.Client.DisplayName).ThenBy(x => x.Service.Name).Select(x => new
        {
            x.Id, x.ClientId, clientCode = x.Client.ClientCode, clientName = x.Client.DisplayName, x.ServiceId, serviceCode = x.Service.Code, serviceName = x.Service.Name,
            x.GstRegistrationId, gstin = x.GstRegistration == null ? null : x.GstRegistration.Gstin, x.EngagementCode, x.TitleOverride,
            x.EffectiveFrom, x.EffectiveTo, x.IsActive, x.DefaultPriority, x.ResponsibleTeamId, responsibleTeam = x.ResponsibleTeam == null ? null : x.ResponsibleTeam.Name,
            x.Notes, x.DeactivationReason
        }).ToArrayAsync(cancellationToken));
    }

    private static async Task<IResult> GetAgreementAsync(Guid id, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = Scope(principal, PermissionCodes.ServiceEnrollmentsView)!; var query = await ApplyScopeAsync(database.ClientServices.AsNoTracking().Where(x => x.Id == id), principal, scope, database, cancellationToken);
        var result = await query.Select(x => new { x.Id, x.ClientId, x.ServiceId, x.GstRegistrationId, x.EngagementCode, x.TitleOverride, x.EffectiveFrom, x.EffectiveTo, x.IsActive, x.DefaultPriority, x.ResponsibleTeamId, x.Notes, x.DeactivationReason }).SingleOrDefaultAsync(cancellationToken);
        return result is null ? Results.NotFound() : Results.Ok(result);
    }

    // Shows the dates a schedule would actually produce, before the agreement exists. It runs the
    // same calculator that generates the tasks, so the preview cannot drift from the real result.
    private static IResult PreviewEnrolmentScheduleAsync(EnrolmentPreviewRequest request, IClock clock)
    {
        var frequency = (request.FrequencyCode ?? string.Empty).Trim().ToUpperInvariant();
        if (frequency is not ("MONTHLY" or "QUARTERLY" or "HALF_YEARLY" or "YEARLY"))
        {
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["frequencyCode"] = ["Choose how often the work repeats."] });
        }
        if (request.DueDay is < 1 or > 31)
        {
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["dueDay"] = ["The due day must be between 1 and 31."] });
        }
        if (request.DueMonthOffset is < 0 or > 24)
        {
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["dueMonthOffset"] = ["The month offset must be between 0 and 24."] });
        }

        var rule = new RecurrenceRule
        {
            Id = Guid.Empty, ClientServiceId = Guid.Empty, HolidayCalendarId = Guid.Empty,
            FrequencyCode = frequency, IntervalCount = 1, AnchorDate = request.EffectiveFrom,
            DueRuleCode = "FIXED_DAY_OF_OFFSET_MONTH", DueDay = request.DueDay, DueMonthOffset = request.DueMonthOffset,
            DueDayOffset = 0, BusinessDayAdjustment = "NEXT_BUSINESS_DAY", GenerateLeadDays = 21,
            TimeZoneId = "Asia/Kolkata", EffectiveFrom = request.EffectiveFrom, RuleVersion = 1, IsActive = true
        };

        // Weekend and holiday adjustment needs the firm calendar, which the real generator applies.
        // The preview shows the nominal date so it never implies a shift that has not been checked.
        var from = request.EffectiveFrom;
        var to = request.EffectiveFrom.AddYears(frequency == "YEARLY" ? 4 : 2);
        var occurrences = RecurrenceCalculator.Calculate(rule, from, to)
            .Take(5)
            .Select(item => new { item.PeriodStart, item.PeriodEnd, dueDate = item.NominalDueDate })
            .ToArray();

        return Results.Ok(new { occurrences, generatedAtUtc = clock.UtcNow });
    }

    private static async Task<IResult> CreateAgreementAsync(ClientServiceRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var scopeError = await ValidateScopeAsync(context.User, request.ResponsibleTeamId, PermissionCodes.ServiceEnrollmentsManage, database, cancellationToken); if (scopeError is not null) return scopeError;
        var errors = await ValidateAgreementAsync(request, null, database, cancellationToken); if (errors.Count > 0) return Results.ValidationProblem(errors);
        var now = clock.UtcNow; var agreement = new ClientService { Id = Guid.NewGuid(), ClientId = request.ClientId, ServiceId = request.ServiceId, GstRegistrationId = request.GstRegistrationId, EngagementCode = Clean(request.EngagementCode), TitleOverride = Clean(request.TitleOverride), EffectiveFrom = request.EffectiveFrom, EffectiveTo = request.EffectiveTo, IsActive = true, DefaultPriority = request.DefaultPriority.ToUpperInvariant(), ResponsibleTeamId = request.ResponsibleTeamId, Notes = Clean(request.Notes), CreatedAtUtc = now, UpdatedAtUtc = now };
        database.ClientServices.Add(agreement); database.AuditEvents.Add(Audit(now, UserId(context.User), "services.client_service_created", "ClientService", agreement.Id, new { agreement.ClientId, agreement.ServiceId, agreement.GstRegistrationId, agreement.EffectiveFrom, agreement.DefaultPriority, agreement.ResponsibleTeamId }));

        if (request.Schedule is { } schedule)
        {
            var frequency = schedule.FrequencyCode.Trim().ToUpperInvariant();
            if (frequency is not ("MONTHLY" or "QUARTERLY" or "HALF_YEARLY" or "YEARLY"))
            {
                return Results.ValidationProblem(new Dictionary<string, string[]> { ["schedule.frequencyCode"] = ["Choose monthly, quarterly, half-yearly or yearly."] });
            }
            if (schedule.DueDay is < 1 or > 31)
            {
                return Results.ValidationProblem(new Dictionary<string, string[]> { ["schedule.dueDay"] = ["The due day must be between 1 and 31."] });
            }
            if (schedule.DueMonthOffset is < 0 or > 24)
            {
                return Results.ValidationProblem(new Dictionary<string, string[]> { ["schedule.dueMonthOffset"] = ["The month offset must be between 0 and 24."] });
            }
            if (schedule.PrimaryAssigneeId is { } assigneeId && !await database.Employees.AnyAsync(x => x.Id == assigneeId && x.IsActive, cancellationToken))
            {
                return Results.ValidationProblem(new Dictionary<string, string[]> { ["schedule.primaryAssigneeId"] = ["Choose an active employee."] });
            }

            var calendarId = await database.HolidayCalendars.Where(x => x.IsActive).Select(x => x.Id).FirstOrDefaultAsync(cancellationToken);
            if (calendarId == Guid.Empty)
            {
                return Results.ValidationProblem(new Dictionary<string, string[]> { ["schedule"] = ["No holiday calendar is configured, so a schedule cannot be created yet."] });
            }

            var actor = UserId(context.User);
            var rule = new RecurrenceRule
            {
                Id = Guid.NewGuid(), ClientServiceId = agreement.Id, HolidayCalendarId = calendarId,
                DefaultPrimaryAssigneeId = schedule.PrimaryAssigneeId,
                FrequencyCode = frequency, IntervalCount = 1, AnchorDate = request.EffectiveFrom,
                DueRuleCode = "FIXED_DAY_OF_OFFSET_MONTH", DueDay = schedule.DueDay, DueMonthOffset = schedule.DueMonthOffset,
                DueDayOffset = 0, BusinessDayAdjustment = "NEXT_BUSINESS_DAY", GenerateLeadDays = 21,
                TimeZoneId = "Asia/Kolkata", EffectiveFrom = request.EffectiveFrom, EffectiveTo = request.EffectiveTo,
                RuleVersion = 1, IsActive = true,
                CreatedByUserId = actor, UpdatedByUserId = actor, CreatedAtUtc = now, UpdatedAtUtc = now
            };
            database.RecurrenceRules.Add(rule);
            database.AuditEvents.Add(Audit(now, actor, "scheduling.rule_created", "RecurrenceRule", rule.Id,
                new { rule.ClientServiceId, rule.FrequencyCode, rule.DueDay, rule.DueMonthOffset, rule.DefaultPrimaryAssigneeId, source = "enrolment" }));
        }

        await database.SaveChangesAsync(cancellationToken); return Results.Created($"/api/v1/client-services/{agreement.Id}", new { agreement.Id });
    }

    private static async Task<IResult> UpdateAgreementAsync(Guid id, ClientServiceRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var agreement = await database.ClientServices.SingleOrDefaultAsync(x => x.Id == id, cancellationToken); if (agreement is null) return Results.NotFound();
        var currentAccess = await ValidateScopeAsync(context.User, agreement.ResponsibleTeamId, PermissionCodes.ServiceEnrollmentsManage, database, cancellationToken); if (currentAccess is not null) return currentAccess;
        var targetAccess = await ValidateScopeAsync(context.User, request.ResponsibleTeamId, PermissionCodes.ServiceEnrollmentsManage, database, cancellationToken); if (targetAccess is not null) return targetAccess;
        var errors = await ValidateAgreementAsync(request, id, database, cancellationToken); if (errors.Count > 0) return Results.ValidationProblem(errors);
        var changed = new List<string>(); if (agreement.ServiceId != request.ServiceId) changed.Add("serviceId"); if (agreement.GstRegistrationId != request.GstRegistrationId) changed.Add("gstRegistrationId"); if (agreement.EffectiveFrom != request.EffectiveFrom || agreement.EffectiveTo != request.EffectiveTo) changed.Add("effectiveDates"); if (!agreement.DefaultPriority.Equals(request.DefaultPriority, StringComparison.OrdinalIgnoreCase)) changed.Add("defaultPriority"); if (agreement.ResponsibleTeamId != request.ResponsibleTeamId) changed.Add("responsibleTeamId");
        agreement.ClientId = request.ClientId; agreement.ServiceId = request.ServiceId; agreement.GstRegistrationId = request.GstRegistrationId; agreement.EngagementCode = Clean(request.EngagementCode); agreement.TitleOverride = Clean(request.TitleOverride); agreement.EffectiveFrom = request.EffectiveFrom; agreement.EffectiveTo = request.EffectiveTo; agreement.DefaultPriority = request.DefaultPriority.ToUpperInvariant(); agreement.ResponsibleTeamId = request.ResponsibleTeamId; agreement.Notes = Clean(request.Notes); agreement.UpdatedAtUtc = clock.UtcNow;
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(context.User), "services.client_service_updated", "ClientService", agreement.Id, new { changedFields = changed })); await database.SaveChangesAsync(cancellationToken); return Results.NoContent();
    }

    private static async Task<IResult> ChangeAgreementStatusAsync(Guid id, MasterStatusRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var agreement = await database.ClientServices.SingleOrDefaultAsync(x => x.Id == id, cancellationToken); if (agreement is null) return Results.NotFound();
        var access = await ValidateScopeAsync(context.User, agreement.ResponsibleTeamId, PermissionCodes.ServiceEnrollmentsManage, database, cancellationToken); if (access is not null) return access;
        if (!request.IsActive && string.IsNullOrWhiteSpace(request.Reason)) return Results.ValidationProblem(new Dictionary<string, string[]> { ["reason"] = ["A reason is required to deactivate an agreement."] });
        if (request.IsActive)
        {
            var duplicate = await database.ClientServices.AnyAsync(x => x.Id != id && x.ClientId == agreement.ClientId && x.ServiceId == agreement.ServiceId && x.GstRegistrationId == agreement.GstRegistrationId && x.IsActive, cancellationToken);
            if (duplicate) return Results.Conflict(new { message = "Another active agreement already uses this client, service and GSTIN scope." });
            var validMasters = await database.Clients.AnyAsync(x => x.Id == agreement.ClientId && x.Status == "ACTIVE", cancellationToken) && await database.Services.AnyAsync(x => x.Id == agreement.ServiceId && x.IsActive, cancellationToken);
            if (!validMasters) return Results.Conflict(new { message = "The client and service must both be active before reactivation." });
        }
        agreement.IsActive = request.IsActive; agreement.DeactivatedAtUtc = request.IsActive ? null : clock.UtcNow; agreement.DeactivationReason = request.IsActive ? null : request.Reason.Trim(); agreement.EffectiveTo = request.IsActive ? agreement.EffectiveTo : agreement.EffectiveTo ?? DateOnly.FromDateTime(clock.UtcNow.Date); agreement.UpdatedAtUtc = clock.UtcNow;
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(context.User), request.IsActive ? "services.client_service_reactivated" : "services.client_service_deactivated", "ClientService", agreement.Id, new { request.Reason }, request.Reason)); await database.SaveChangesAsync(cancellationToken); return Results.NoContent();
    }

    private static async Task<Dictionary<string, string[]>> ValidateServiceAsync(ServiceUpsertRequest request, Guid? currentId, AppDbContext database, CancellationToken cancellationToken)
    {
        var errors = new Dictionary<string, string[]>(); var code = NormalizeCode(request.Code); var name = request.Name.Trim();
        if (code.Length is < 2 or > 50) errors["code"] = ["Service code must contain 2 to 50 characters."]; if (name.Length is < 2 or > 150) errors["name"] = ["Service name must contain 2 to 150 characters."];
        if (!await database.ServiceCategories.AnyAsync(x => x.Id == request.CategoryId && x.IsActive, cancellationToken)) errors["categoryId"] = ["Choose an active service category."];
        if (await database.Services.AnyAsync(x => x.Id != currentId && (x.Code == code || x.NormalizedName == NormalizeName(name)), cancellationToken)) errors["service"] = ["Service code or name already exists."];
        return errors;
    }

    private static async Task<Dictionary<string, string[]>> ValidateAgreementAsync(ClientServiceRequest request, Guid? currentId, AppDbContext database, CancellationToken cancellationToken)
    {
        var values = new Dictionary<string, string?> { ["clientId"] = request.ClientId.ToString(), ["serviceId"] = request.ServiceId.ToString(), ["effectiveFrom"] = request.EffectiveFrom.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), ["defaultPriority"] = request.DefaultPriority, ["responsibleTeamId"] = request.ResponsibleTeamId?.ToString() };
        var required = await database.FieldDefinitions.AsNoTracking().Where(x => x.EntityType == "services.client_service" && x.IsActive && x.IsAdministratorRequired).Select(x => x.FieldKey).ToArrayAsync(cancellationToken);
        var errors = required.Where(key => !values.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value)).ToDictionary(key => key, _ => RequiredFieldError);
        if (!await database.Clients.AnyAsync(x => x.Id == request.ClientId && x.Status == "ACTIVE", cancellationToken)) errors["clientId"] = ["Choose an active client."];
        var service = await database.Services.AsNoTracking().SingleOrDefaultAsync(x => x.Id == request.ServiceId && x.IsActive, cancellationToken); if (service is null) errors["serviceId"] = ["Choose an active service."];
        if (request.EffectiveTo is not null && request.EffectiveTo < request.EffectiveFrom) errors["effectiveTo"] = ["Effective-to date cannot precede effective-from date."];
        var priority = request.DefaultPriority.ToUpperInvariant(); if (priority is not ("LOW" or "NORMAL" or "HIGH" or "URGENT")) errors["defaultPriority"] = ["Priority must be LOW, NORMAL, HIGH, or URGENT."];
        if (request.ResponsibleTeamId is not null && !await database.Teams.AnyAsync(x => x.Id == request.ResponsibleTeamId && x.IsActive, cancellationToken)) errors["responsibleTeamId"] = ["Choose an active responsible team."];
        if (request.GstRegistrationId is not null)
        {
            if (service is not null && !service.SupportsGstinScope) errors["gstRegistrationId"] = ["This service does not support GSTIN-specific scope."];
            if (!await database.GstRegistrations.AnyAsync(x => x.Id == request.GstRegistrationId && x.ClientId == request.ClientId && x.IsActive, cancellationToken)) errors["gstRegistrationId"] = ["Choose an active GSTIN belonging to this client."];
        }
        if (await database.ClientServices.AnyAsync(x => x.Id != currentId && x.ClientId == request.ClientId && x.ServiceId == request.ServiceId && x.GstRegistrationId == request.GstRegistrationId && x.IsActive, cancellationToken)) errors["scope"] = ["An active agreement already exists for this client, service and GSTIN scope."];
        return errors;
    }

    private static async Task<IQueryable<ClientService>> ApplyScopeAsync(IQueryable<ClientService> query, ClaimsPrincipal principal, string scope, AppDbContext database, CancellationToken cancellationToken)
    {
        if (scope == "ALL") return query; var teams = await AccessibleTeamIdsAsync(principal, scope, database, cancellationToken); return query.Where(x => x.ResponsibleTeamId != null && teams.Contains(x.ResponsibleTeamId.Value));
    }

    private static async Task<IResult?> ValidateScopeAsync(ClaimsPrincipal principal, Guid? teamId, string permission, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = Scope(principal, permission)!; if (scope == "ALL") return null; if (teamId is null) return Results.Problem(statusCode: 403, title: "Responsible team required", detail: "OWN and TEAM access may manage only agreements assigned to an accessible team.");
        var teams = await AccessibleTeamIdsAsync(principal, scope, database, cancellationToken); return teams.Contains(teamId.Value) ? null : Results.Problem(statusCode: 403, title: "Client service scope denied", detail: "The responsible team is outside your permitted scope.");
    }

    private static async Task<Guid[]> AccessibleTeamIdsAsync(ClaimsPrincipal principal, string scope, AppDbContext database, CancellationToken cancellationToken)
    {
        var userId = UserId(principal); var employeeId = await database.Employees.Where(x => x.UserId == userId && x.IsActive).Select(x => (Guid?)x.Id).SingleOrDefaultAsync(cancellationToken); if (employeeId is null) return [];
        var teamIds = database.TeamMemberships.Where(x => x.EmployeeId == employeeId && x.ValidTo == null).Select(x => x.TeamId);
        // TEAM reaches teams this employee belongs to or personally manages, and stops there.
        // Kept identical to the client, reporting, scheduling and billing rules so one permission
        // and ceiling cannot mean different things in different modules.
        if (scope == "TEAM")
        {
            teamIds = teamIds.Concat(database.Teams.Where(x => x.ManagerEmployeeId == employeeId && x.IsActive).Select(x => x.Id));
        }
        return await teamIds.Distinct().ToArrayAsync(cancellationToken);
    }

    private static string? Scope(ClaimsPrincipal principal, string permission) => principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + permission);
    private static Guid UserId(ClaimsPrincipal principal) => Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
    private static string NormalizeCode(string value) => string.Concat(value.Trim().ToUpperInvariant().Select(c => char.IsAsciiLetterOrDigit(c) ? c : '_')).Trim('_');
    private static string NormalizeName(string value) => string.Join(' ', value.Trim().Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries)).ToUpperInvariant();
    private static string? Clean(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    private static AuditEvent Audit(DateTimeOffset at, Guid actor, string action, string entityType, Guid id, object data, string? reason = null) => new() { Id = Guid.NewGuid(), OccurredAtUtc = at, ActorUserId = actor, Action = action, EntityType = entityType, EntityId = id.ToString(), Reason = reason, DataJson = JsonSerializer.Serialize(data) };
}

public sealed record ServiceCategoryRequest(string Code, string Name, int DisplayOrder);
public sealed record ServiceUpsertRequest(Guid CategoryId, string Code, string Name, string? Description, bool DefaultBillable, bool SupportsRecurrence, bool SupportsGstinScope);
public sealed record ClientServiceRequest(Guid ClientId, Guid ServiceId, Guid? GstRegistrationId, string? EngagementCode, string? TitleOverride, DateOnly EffectiveFrom, DateOnly? EffectiveTo, string DefaultPriority, Guid? ResponsibleTeamId, string? Notes, EnrolmentScheduleRequest? Schedule = null);
// Set up the repeating schedule at the same time as the agreement, so enrolling a client for a
// monthly return does not require a second trip to the calendar. No statutory due date is assumed:
// the due day and the month offset are supplied by whoever knows the deadline.
public sealed record EnrolmentScheduleRequest(string FrequencyCode, short DueDay, short DueMonthOffset, Guid? PrimaryAssigneeId);
public sealed record MasterStatusRequest(bool IsActive, string Reason);
public sealed record EnrolmentPreviewRequest(string? FrequencyCode, short DueDay, short DueMonthOffset, DateOnly EffectiveFrom);
