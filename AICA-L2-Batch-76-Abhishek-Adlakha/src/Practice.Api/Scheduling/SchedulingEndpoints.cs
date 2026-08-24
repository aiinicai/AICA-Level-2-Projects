using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;
using Practice.Scheduling;

namespace Practice.Api.Scheduling;

public static class SchedulingEndpoints
{
    private static readonly Guid DefaultCalendarId = new("70a45f7b-dfde-4af0-a634-876797f19501");

    public static IEndpointRouteBuilder MapSchedulingEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var group = endpoints.MapGroup("/api/v1/scheduling").RequireAuthorization("password-current");
        group.MapGet("/masters", MastersAsync).RequireAuthorization(PermissionCodes.SchedulingView);
        group.MapGet("/rules", ListRulesAsync).RequireAuthorization(PermissionCodes.SchedulingView);
        group.MapPost("/rules", CreateRuleAsync).RequireAuthorization(PermissionCodes.SchedulingManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapPut("/rules/{id:guid}", VersionRuleAsync).RequireAuthorization(PermissionCodes.SchedulingManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapPost("/rules/{id:guid}/deactivate", DeactivateRuleAsync).RequireAuthorization(PermissionCodes.SchedulingManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapGet("/rules/{id:guid}/exceptions", ListExceptionsAsync).RequireAuthorization(PermissionCodes.SchedulingView);
        group.MapPost("/rules/{id:guid}/exceptions", AddExceptionAsync).RequireAuthorization(PermissionCodes.SchedulingManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapPost("/preview", PreviewAsync).RequireAuthorization(PermissionCodes.SchedulingView).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapPost("/generate", GenerateAsync).RequireAuthorization(PermissionCodes.SchedulingGenerate).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapGet("/runs", ListRunsAsync).RequireAuthorization(PermissionCodes.SchedulingView);
        group.MapGet("/holidays", ListHolidaysAsync).RequireAuthorization(PermissionCodes.SchedulingView);
        group.MapPost("/holidays", AddHolidayAsync).RequireAuthorization(PermissionCodes.HolidaysManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        return endpoints;
    }

    private static async Task<IResult> MastersAsync(ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var scopedAgreements = await ScopedAgreements(database.ClientServices.AsNoTracking().Where(item => item.IsActive && item.Client.Status == "ACTIVE" && item.Service.IsActive && item.Service.SupportsRecurrence), principal, PermissionCodes.SchedulingView, database, cancellationToken);
        var agreements = await scopedAgreements
            .OrderBy(item => item.Client.DisplayName).ThenBy(item => item.Service.Name)
            .Select(item => new { item.Id, item.ClientId, clientName = item.Client.DisplayName, clientCode = item.Client.ClientCode, item.ServiceId, serviceName = item.Service.Name, item.GstRegistrationId, gstin = item.GstRegistration == null ? null : item.GstRegistration.Gstin, item.DefaultPriority })
            .ToArrayAsync(cancellationToken);
        return Results.Ok(new
        {
            agreements,
            calendars = await database.HolidayCalendars.AsNoTracking().Where(item => item.IsActive).OrderBy(item => item.Name).Select(item => new { item.Id, item.Code, item.Name, item.TimeZoneId }).ToArrayAsync(cancellationToken),
            employees = await database.Employees.AsNoTracking().Where(item => item.IsActive).OrderBy(item => item.DisplayName).Select(item => new { item.Id, item.EmployeeCode, item.DisplayName }).ToArrayAsync(cancellationToken),
            defaults = new { holidayCalendarId = DefaultCalendarId, timeZoneId = "Asia/Kolkata", sundayIsNonWorking = true, saturdayIsWorking = true, generationHorizonDays = 45 }
        });
    }

    private static async Task<IResult> ListRulesAsync(bool? includeInactive, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var showAll = includeInactive == true;
        var query = database.RecurrenceRules.AsNoTracking().Where(item => showAll || item.IsActive);
        var scopedAgreements = await ScopedAgreements(database.ClientServices.AsNoTracking(), principal, PermissionCodes.SchedulingView, database, cancellationToken);
        var agreements = await scopedAgreements.Select(item => item.Id).ToArrayAsync(cancellationToken);
        query = query.Where(item => agreements.Contains(item.ClientServiceId));
        var rows = await query.OrderByDescending(item => item.IsActive).ThenBy(item => item.ClientService.Client.DisplayName).ThenBy(item => item.ClientService.Service.Name).ThenByDescending(item => item.RuleVersion)
            .Select(item => new
            {
                item.Id, item.ClientServiceId, clientName = item.ClientService.Client.DisplayName, serviceName = item.ClientService.Service.Name,
                gstin = item.ClientService.GstRegistration == null ? null : item.ClientService.GstRegistration.Gstin,
                item.FrequencyCode, item.IntervalCount, item.AnchorDate, item.DueDay, item.DueMonthOffset, item.DueDayOffset,
                item.BusinessDayAdjustment, item.GenerateLeadDays, item.EffectiveFrom, item.EffectiveTo, item.RuleVersion,
                item.IsActive, item.DefaultPrimaryAssigneeId, assigneeName = item.DefaultPrimaryAssignee == null ? null : item.DefaultPrimaryAssignee.DisplayName,
                months = item.Months.OrderBy(month => month.DisplayOrder).Select(month => month.MonthNumber), item.RowVersion
            }).ToArrayAsync(cancellationToken);
        return Results.Ok(rows);
    }

    private static async Task<IResult> CreateRuleAsync(RecurrenceRuleRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var validation = await ValidateRuleAsync(request, null, null, context.User, PermissionCodes.SchedulingManage, database, cancellationToken);
        if (validation.Count > 0) return Results.ValidationProblem(validation);
        var actor = UserId(context.User);
        var rule = MapRule(request, Guid.NewGuid(), 1, actor, clock.UtcNow);
        AddMonths(rule, request.Months);
        database.RecurrenceRules.Add(rule);
        database.AuditEvents.Add(Audit(clock.UtcNow, actor, "scheduling.rule_created", rule.Id, new { rule.ClientServiceId, rule.FrequencyCode, rule.RuleVersion }));
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/v1/scheduling/rules/{rule.Id}", new { rule.Id, rule.RuleVersion, rule.RowVersion });
    }

    private static async Task<IResult> VersionRuleAsync(Guid id, RecurrenceRuleRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var prior = await database.RecurrenceRules.SingleOrDefaultAsync(item => item.Id == id && item.IsActive, cancellationToken);
        if (prior is null) return Results.NotFound();
        if (prior.RowVersion != request.ExpectedVersion) return Results.Conflict(new { message = "The rule changed after it was loaded.", currentVersion = prior.RowVersion });
        var validation = await ValidateRuleAsync(request, prior.ClientServiceId, prior.Id, context.User, PermissionCodes.SchedulingManage, database, cancellationToken);
        if (validation.Count > 0) return Results.ValidationProblem(validation);
        if (request.EffectiveFrom <= prior.EffectiveFrom) return Results.ValidationProblem(new Dictionary<string, string[]> { ["effectiveFrom"] = ["A replacement version must start after the current version."] });

        var actor = UserId(context.User); var now = clock.UtcNow;
        prior.IsActive = false; prior.EffectiveTo = request.EffectiveFrom.AddDays(-1); prior.UpdatedAtUtc = now; prior.UpdatedByUserId = actor; prior.RowVersion++;
        var replacement = MapRule(request with { ClientServiceId = prior.ClientServiceId }, Guid.NewGuid(), prior.RuleVersion + 1, actor, now);
        AddMonths(replacement, request.Months);
        database.RecurrenceRules.Add(replacement);
        database.AuditEvents.Add(Audit(now, actor, "scheduling.rule_versioned", replacement.Id, new { previousRuleId = prior.Id, replacement.RuleVersion, replacement.EffectiveFrom }));
        await database.SaveChangesAsync(cancellationToken);
        return Results.Ok(new { replacement.Id, replacement.RuleVersion, replacement.RowVersion });
    }

    private static async Task<IResult> DeactivateRuleAsync(Guid id, RuleDeactivateRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.Reason)) return Results.ValidationProblem(new Dictionary<string, string[]> { ["reason"] = ["A deactivation reason is required."] });
        var scopedAgreements = await ScopedAgreements(database.ClientServices.AsNoTracking(), context.User, PermissionCodes.SchedulingManage, database, cancellationToken);
        var scopedIds = await scopedAgreements.Select(item => item.Id).ToArrayAsync(cancellationToken);
        var rule = await database.RecurrenceRules.SingleOrDefaultAsync(item => item.Id == id && scopedIds.Contains(item.ClientServiceId), cancellationToken);
        if (rule is null) return Results.NotFound();
        if (rule.RowVersion != request.ExpectedVersion) return Results.Conflict(new { message = "The rule changed after it was loaded.", currentVersion = rule.RowVersion });
        rule.IsActive = false; rule.EffectiveTo ??= DateOnly.FromDateTime(clock.UtcNow.ToOffset(TimeSpan.FromHours(5.5)).DateTime); rule.UpdatedAtUtc = clock.UtcNow; rule.UpdatedByUserId = UserId(context.User); rule.RowVersion++;
        database.AuditEvents.Add(Audit(clock.UtcNow, UserId(context.User), "scheduling.rule_deactivated", rule.Id, new { request.Reason }, request.Reason));
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> ListExceptionsAsync(Guid id, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var scopedAgreements = await ScopedAgreements(database.ClientServices.AsNoTracking(), principal, PermissionCodes.SchedulingView, database, cancellationToken);
        var agreementIds = await scopedAgreements.Select(item => item.Id).ToArrayAsync(cancellationToken);
        if (!await database.RecurrenceRules.AnyAsync(item => item.Id == id && agreementIds.Contains(item.ClientServiceId), cancellationToken)) return Results.NotFound();
        return Results.Ok(await database.RecurrenceExceptions.AsNoTracking().Where(item => item.RecurrenceRuleId == id).OrderBy(item => item.PeriodStart)
            .Select(item => new { item.Id, item.PeriodStart, item.PeriodEnd, item.Action, item.OverrideDueDate, item.OverrideTitle, item.OverridePrimaryAssigneeId, item.OverridePriority, item.Reason, item.CreatedAtUtc }).ToArrayAsync(cancellationToken));
    }

    private static async Task<IResult> AddExceptionAsync(Guid id, RecurrenceExceptionRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var scopedAgreements = await ScopedAgreements(database.ClientServices.AsNoTracking(), context.User, PermissionCodes.SchedulingManage, database, cancellationToken);
        var agreementIds = await scopedAgreements.Select(item => item.Id).ToArrayAsync(cancellationToken);
        if (!await database.RecurrenceRules.AnyAsync(item => item.Id == id && agreementIds.Contains(item.ClientServiceId), cancellationToken)) return Results.NotFound();
        var action = request.Action.Trim().ToUpperInvariant();
        var errors = new Dictionary<string, string[]>();
        if (request.PeriodEnd < request.PeriodStart) errors["periodEnd"] = ["Period-end cannot precede period-start."];
        if (action is not ("SKIP" or "OVERRIDE")) errors["action"] = ["Action must be SKIP or OVERRIDE."];
        if (string.IsNullOrWhiteSpace(request.Reason)) errors["reason"] = ["An exception reason is required."];
        if (action == "OVERRIDE" && request.OverrideDueDate is null && string.IsNullOrWhiteSpace(request.OverrideTitle) && request.OverridePrimaryAssigneeId is null && string.IsNullOrWhiteSpace(request.OverridePriority)) errors["action"] = ["An override must change at least one occurrence value."];
        if (errors.Count > 0) return Results.ValidationProblem(errors);
        var actor = UserId(context.User); var entity = new RecurrenceAdjustment
        {
            Id = Guid.NewGuid(), RecurrenceRuleId = id, PeriodStart = request.PeriodStart, PeriodEnd = request.PeriodEnd,
            Action = action, OverrideDueDate = request.OverrideDueDate, OverrideTitle = Clean(request.OverrideTitle),
            OverridePrimaryAssigneeId = request.OverridePrimaryAssigneeId, OverridePriority = Clean(request.OverridePriority)?.ToUpperInvariant(),
            Reason = request.Reason.Trim(), CreatedByUserId = actor, CreatedAtUtc = clock.UtcNow
        };
        database.RecurrenceExceptions.Add(entity);
        database.AuditEvents.Add(Audit(clock.UtcNow, actor, "scheduling.exception_created", id, new { entity.Id, entity.PeriodStart, entity.PeriodEnd, entity.Action }, entity.Reason));
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/v1/scheduling/rules/{id}/exceptions/{entity.Id}", new { entity.Id });
    }

    private static async Task<IResult> PreviewAsync(SchedulePreviewRequest request, AppDbContext database, CancellationToken cancellationToken)
    {
        if (request.WindowTo < request.WindowFrom || request.WindowTo.DayNumber - request.WindowFrom.DayNumber > 366) return Results.ValidationProblem(new Dictionary<string, string[]> { ["windowTo"] = ["Preview is limited to 367 days."] });
        var rule = MapRule(request.Rule, Guid.Empty, 1, Guid.Empty, DateTimeOffset.UnixEpoch);
        AddMonths(rule, request.Rule.Months);
        var holidayMap = await database.Holidays.AsNoTracking().Where(item => item.HolidayCalendarId == rule.HolidayCalendarId && item.HolidayDate >= request.WindowFrom.AddDays(-7) && item.HolidayDate <= request.WindowTo.AddDays(7)).ToDictionaryAsync(item => item.HolidayDate, item => item.IsWorkingDayOverride, cancellationToken);
        return Results.Ok(RecurrenceCalculator.Calculate(rule, request.WindowFrom, request.WindowTo, holidayMap));
    }

    private static async Task<IResult> GenerateAsync(GenerationRequest request, ClaimsPrincipal principal, TaskGenerationService generator, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var actor = UserId(principal);
        var result = await generator.GenerateAsync(request.WindowFrom, request.WindowTo, "MANUAL", actor, $"api:{Environment.MachineName}", cancellationToken);
        // The run itself is persisted as generator evidence; this records who triggered it.
        database.AuditEvents.Add(new AuditEvent
        {
            Id = Guid.NewGuid(), OccurredAtUtc = clock.UtcNow, ActorUserId = actor,
            Action = "scheduling.generation_requested", EntityType = "GenerationRun", EntityId = null,
            DataJson = JsonSerializer.Serialize(new { request.WindowFrom, request.WindowTo, trigger = "MANUAL" })
        });
        await database.SaveChangesAsync(cancellationToken);
        return Results.Ok(result);
    }

    private static async Task<IResult> ListRunsAsync(int take, AppDbContext database, CancellationToken cancellationToken) => Results.Ok(
        await database.TaskGenerationRuns.AsNoTracking().OrderByDescending(item => item.StartedAtUtc).Take(Math.Clamp(take == 0 ? 20 : take, 1, 100))
            .Select(item => new { item.Id, item.WindowFrom, item.WindowTo, item.Trigger, item.Status, item.WorkerId, item.StartedAtUtc, item.FinishedAtUtc, item.CreatedCount, item.ExistingCount, item.SkippedCount, item.ErrorCount, item.ErrorSummary }).ToArrayAsync(cancellationToken));

    private static async Task<IResult> ListHolidaysAsync(int year, Guid? calendarId, AppDbContext database, CancellationToken cancellationToken)
    {
        year = year is >= 2000 and <= 2200 ? year : DateTime.Today.Year;
        var from = new DateOnly(year, 1, 1); var to = new DateOnly(year, 12, 31); var selected = calendarId ?? DefaultCalendarId;
        return Results.Ok(await database.Holidays.AsNoTracking().Where(item => item.HolidayCalendarId == selected && item.HolidayDate >= from && item.HolidayDate <= to).OrderBy(item => item.HolidayDate).Select(item => new { item.Id, item.HolidayDate, item.Name, item.HolidayType, item.IsWorkingDayOverride, item.Notes }).ToArrayAsync(cancellationToken));
    }

    private static async Task<IResult> AddHolidayAsync(HolidayRequest request, ClaimsPrincipal principal, IClock clock, AppDbContext database, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.Name)) return Results.ValidationProblem(new Dictionary<string, string[]> { ["name"] = ["Holiday name is required."] });
        var entity = new Holiday { Id = Guid.NewGuid(), HolidayCalendarId = request.HolidayCalendarId ?? DefaultCalendarId, HolidayDate = request.Date, Name = request.Name.Trim(), HolidayType = request.HolidayType, IsWorkingDayOverride = request.IsWorkingDayOverride, Notes = Clean(request.Notes), CreatedAtUtc = clock.UtcNow };
        database.Holidays.Add(entity);
        // A holiday or working-day override changes every future due-date calculation, so the
        // change is auditable rather than only visible as a calendar row.
        database.AuditEvents.Add(new AuditEvent
        {
            Id = Guid.NewGuid(), OccurredAtUtc = clock.UtcNow, ActorUserId = UserId(principal),
            Action = "scheduling.holiday_added", EntityType = "Holiday", EntityId = entity.Id.ToString(),
            DataJson = JsonSerializer.Serialize(new { entity.HolidayCalendarId, entity.HolidayDate, entity.Name, entity.HolidayType, entity.IsWorkingDayOverride })
        });
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/v1/scheduling/holidays/{entity.Id}", new { entity.Id });
    }

    private static async Task<Dictionary<string, string[]>> ValidateRuleAsync(RecurrenceRuleRequest request, Guid? fixedAgreementId, Guid? currentRuleId, ClaimsPrincipal principal, string permission, AppDbContext database, CancellationToken cancellationToken)
    {
        var errors = new Dictionary<string, string[]>();
        var agreementId = fixedAgreementId ?? request.ClientServiceId;
        var scopedAgreements = await ScopedAgreements(database.ClientServices.AsNoTracking(), principal, permission, database, cancellationToken);
        var scoped = await scopedAgreements.AnyAsync(item => item.Id == agreementId && item.Service.SupportsRecurrence && item.IsActive && item.Client.Status == "ACTIVE", cancellationToken);
        if (!scoped) errors["clientServiceId"] = ["Choose an active recurring-service agreement within your scope."];
        if (request.DueDay is < 1 or > 31) errors["dueDay"] = ["Due day must be from 1 to 31."];
        if (request.IntervalCount is < 1 or > 24) errors["intervalCount"] = ["Interval must be from 1 to 24."];
        if (request.FrequencyCode.Trim().ToUpperInvariant() is not ("MONTHLY" or "QUARTERLY" or "HALF_YEARLY" or "YEARLY" or "CUSTOM_MONTHS")) errors["frequencyCode"] = ["Choose a supported recurrence frequency."];
        if (request.BusinessDayAdjustment.Trim().ToUpperInvariant() is not ("NONE" or "PREVIOUS_BUSINESS_DAY" or "NEXT_BUSINESS_DAY")) errors["businessDayAdjustment"] = ["Choose a supported business-day adjustment."];
        if (request.EffectiveTo < request.EffectiveFrom) errors["effectiveTo"] = ["Effective-to cannot precede effective-from."];
        if (request.FrequencyCode == "CUSTOM_MONTHS" && (request.Months.Length == 0 || request.Months.Any(month => month is < 1 or > 12))) errors["months"] = ["Choose one or more valid months for a custom schedule."];
        if (await database.RecurrenceRules.AnyAsync(item => item.ClientServiceId == agreementId && item.IsActive && item.Id != currentRuleId, cancellationToken)) errors["clientServiceId"] = ["This agreement already has an active recurrence rule; create a replacement version instead."];
        return errors;
    }

    private static RecurrenceRule MapRule(RecurrenceRuleRequest request, Guid id, int version, Guid actor, DateTimeOffset now) => new()
    {
        Id = id, ClientServiceId = request.ClientServiceId, HolidayCalendarId = request.HolidayCalendarId ?? DefaultCalendarId,
        DefaultPrimaryAssigneeId = request.DefaultPrimaryAssigneeId, FrequencyCode = request.FrequencyCode.Trim().ToUpperInvariant(), IntervalCount = request.IntervalCount,
        DueRuleCode = "FIXED_DAY_OF_OFFSET_MONTH", TimeZoneId = "Asia/Kolkata",
        AnchorDate = request.AnchorDate, DueDay = request.DueDay, DueMonthOffset = request.DueMonthOffset, DueDayOffset = request.DueDayOffset,
        BusinessDayAdjustment = request.BusinessDayAdjustment.Trim().ToUpperInvariant(), GenerateLeadDays = request.GenerateLeadDays,
        EffectiveFrom = request.EffectiveFrom, EffectiveTo = request.EffectiveTo, RuleVersion = version, IsActive = true,
        CreatedByUserId = actor, CreatedAtUtc = now, UpdatedByUserId = actor, UpdatedAtUtc = now
    };

    private static void AddMonths(RecurrenceRule rule, IEnumerable<short> months)
    {
        short order = 0;
        foreach (var month in months.Distinct().Order()) rule.Months.Add(new RecurrenceRuleMonth { RecurrenceRuleId = rule.Id, MonthNumber = month, DisplayOrder = order++ });
    }

    private static async Task<IQueryable<ClientService>> ScopedAgreements(IQueryable<ClientService> query, ClaimsPrincipal principal, string permission, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + permission) ?? "OWN";
        if (scope == "ALL") return query;
        var employeeId = await database.Employees.Where(item => item.UserId == UserId(principal) && item.IsActive).Select(item => (Guid?)item.Id).SingleOrDefaultAsync(cancellationToken);
        if (employeeId is null) return query.Where(_ => false);
        var teams = database.TeamMemberships.Where(item => item.EmployeeId == employeeId && item.ValidTo == null).Select(item => item.TeamId);
        if (scope == "TEAM") teams = teams.Concat(database.Teams.Where(item => item.ManagerEmployeeId == employeeId && item.IsActive).Select(item => item.Id));
        var ids = await teams.Distinct().ToArrayAsync(cancellationToken);
        return query.Where(item => item.ResponsibleTeamId != null && ids.Contains(item.ResponsibleTeamId.Value));
    }

    private static Guid UserId(ClaimsPrincipal principal) => Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
    private static string? Clean(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    private static AuditEvent Audit(DateTimeOffset at, Guid actor, string action, Guid id, object data, string? reason = null) => new() { Id = Guid.NewGuid(), OccurredAtUtc = at, ActorUserId = actor, Action = action, EntityType = "RecurrenceRule", EntityId = id.ToString(), Reason = Clean(reason), DataJson = JsonSerializer.Serialize(data) };
}

public sealed record RecurrenceRuleRequest(Guid ClientServiceId, Guid? HolidayCalendarId, Guid? DefaultPrimaryAssigneeId, string FrequencyCode, short IntervalCount, DateOnly AnchorDate, short DueDay, short DueMonthOffset, short DueDayOffset, string BusinessDayAdjustment, short GenerateLeadDays, DateOnly EffectiveFrom, DateOnly? EffectiveTo, short[] Months, long ExpectedVersion = 0);
public sealed record SchedulePreviewRequest(RecurrenceRuleRequest Rule, DateOnly WindowFrom, DateOnly WindowTo);
public sealed record RuleDeactivateRequest(string Reason, long ExpectedVersion);
public sealed record GenerationRequest(DateOnly WindowFrom, DateOnly WindowTo);
public sealed record HolidayRequest(Guid? HolidayCalendarId, DateOnly Date, string Name, string HolidayType, bool IsWorkingDayOverride, string? Notes);
public sealed record RecurrenceExceptionRequest(DateOnly PeriodStart, DateOnly PeriodEnd, string Action, DateOnly? OverrideDueDate, string? OverrideTitle, Guid? OverridePrimaryAssigneeId, string? OverridePriority, string Reason);
