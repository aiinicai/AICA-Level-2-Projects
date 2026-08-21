using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Identity;
using Practice.Reporting;

namespace Practice.Api.Audit;

// Audit history is deliberately unscoped: audit.view is seeded without scope support, so a
// holder sees every recorded event. Do not add OWN/TEAM filtering here without changing the
// permission seed first, otherwise the trail would silently omit events an auditor expects.
public static class AuditEndpoints
{
    private static readonly TimeSpan IndiaOffset = TimeSpan.FromMinutes(330);
    private const int MaximumRangeDays = 366;

    public static IEndpointRouteBuilder MapAuditEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var audit = endpoints.MapGroup("/api/v1/admin/audit")
            .RequireAuthorization("password-current", PermissionCodes.AuditView);
        audit.MapGet("", SearchAsync);
        audit.MapGet("/filters", FiltersAsync);
        endpoints.MapGet("/api/v1/admin/operations", OperationsAsync)
            .RequireAuthorization("password-current", PermissionCodes.DiagnosticsView);
        return endpoints;
    }

    private static async Task<IResult> SearchAsync(
        DateOnly? from,
        DateOnly? to,
        string? action,
        string? entityType,
        string? entityId,
        Guid? actorUserId,
        int? page,
        int? pageSize,
        AppDbContext database,
        IClock clock,
        CancellationToken cancellationToken)
    {
        // Nullable so that an unparameterised request pages by default instead of failing
        // parameter binding, which Minimal APIs surface as a 500 rather than a 400.
        var selectedPage = Math.Max(1, page ?? 1);
        var selectedPageSize = Math.Clamp(pageSize is null or 0 ? 50 : pageSize.Value, 1, 100);

        var today = DateOnly.FromDateTime(clock.UtcNow.ToOffset(IndiaOffset).DateTime);
        var selectedFrom = from ?? today.AddDays(-30);
        var selectedTo = to ?? today;
        if (selectedTo < selectedFrom)
        {
            return Results.ValidationProblem(new Dictionary<string, string[]>
            {
                ["to"] = ["The end date cannot precede the start date."]
            });
        }
        if (selectedTo.DayNumber - selectedFrom.DayNumber > MaximumRangeDays)
        {
            return Results.ValidationProblem(new Dictionary<string, string[]>
            {
                ["to"] = ["The audit window cannot exceed 367 days."]
            });
        }

        var range = ReportingRules.UtcRange(selectedFrom, selectedTo, IndiaOffset);
        var query = database.AuditEvents.AsNoTracking()
            .Where(item => item.OccurredAtUtc >= range.StartUtc && item.OccurredAtUtc < range.EndExclusiveUtc);

        if (!string.IsNullOrWhiteSpace(action))
        {
            var trimmed = action.Trim();
            query = query.Where(item => item.Action == trimmed);
        }
        if (!string.IsNullOrWhiteSpace(entityType))
        {
            var trimmed = entityType.Trim();
            query = query.Where(item => item.EntityType == trimmed);
        }
        if (!string.IsNullOrWhiteSpace(entityId))
        {
            var trimmed = entityId.Trim();
            query = query.Where(item => item.EntityId == trimmed);
        }
        if (actorUserId is { } actor)
        {
            query = query.Where(item => item.ActorUserId == actor);
        }

        var totalCount = await query.CountAsync(cancellationToken);
        // Materialise the raw row before formatting so nothing here depends on client-side
        // translation of string conversions; the Phase 9 dashboard regressed exactly that way.
        var rows = await query
            .OrderByDescending(item => item.OccurredAtUtc).ThenByDescending(item => item.Id)
            .Skip((selectedPage - 1) * selectedPageSize).Take(selectedPageSize)
            .Select(item => new
            {
                item.Id,
                item.OccurredAtUtc,
                item.ActorUserId,
                item.Action,
                item.EntityType,
                item.EntityId,
                item.Reason,
                item.CorrelationId,
                item.DataJson,
                ActorName = database.Employees
                    .Where(employee => employee.UserId == item.ActorUserId)
                    .Select(employee => employee.DisplayName)
                    .FirstOrDefault()
            })
            .ToArrayAsync(cancellationToken);

        var items = rows.Select(row => new
        {
            id = row.Id,
            occurredAtUtc = row.OccurredAtUtc,
            actorUserId = row.ActorUserId,
            actorName = row.ActorName ?? (row.ActorUserId is null ? "System" : "Unknown user"),
            action = row.Action,
            entityType = row.EntityType,
            entityId = row.EntityId,
            reason = row.Reason,
            correlationId = row.CorrelationId,
            data = row.DataJson
        }).ToArray();

        return Results.Ok(new
        {
            items,
            page = selectedPage,
            pageSize = selectedPageSize,
            totalCount,
            totalPages = (int)Math.Ceiling(totalCount / (double)selectedPageSize),
            from = selectedFrom,
            to = selectedTo,
            definition = "Audit events recorded within the selected Asia/Kolkata date range, newest first. Audit history is append-only and unscoped."
        });
    }

    // One page an administrator can read without opening logs: can the database be reached, did
    // recurring generation last succeed, and is audit history being retained as configured.
    private static async Task<IResult> OperationsAsync(
        AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var canConnect = await database.Database.CanConnectAsync(cancellationToken);
        if (!canConnect)
        {
            return Results.Ok(new { databaseReachable = false, checkedAtUtc = clock.UtcNow });
        }

        var lastRun = await database.TaskGenerationRuns.AsNoTracking()
            .OrderByDescending(item => item.StartedAtUtc)
            .Select(item => new
            {
                item.Id, item.Trigger, item.Status, item.StartedAtUtc, item.FinishedAtUtc,
                item.CreatedCount, item.ExistingCount, item.SkippedCount, item.ErrorCount, item.ErrorSummary
            })
            .FirstOrDefaultAsync(cancellationToken);

        var now = clock.UtcNow;
        var auditTotal = await database.AuditEvents.CountAsync(cancellationToken);
        var oldestAudit = await database.AuditEvents.OrderBy(item => item.OccurredAtUtc)
            .Select(item => (DateTimeOffset?)item.OccurredAtUtc).FirstOrDefaultAsync(cancellationToken);
        var activeRules = await database.RecurrenceRules.CountAsync(item => item.IsActive, cancellationToken);

        // Generation is expected roughly every six hours; well past a day means the worker is not
        // running, which otherwise only shows up as tasks quietly failing to appear.
        var generationStale = lastRun is null || now - lastRun.StartedAtUtc > TimeSpan.FromHours(26);

        return Results.Ok(new
        {
            databaseReachable = true,
            checkedAtUtc = now,
            appliedMigrations = (await database.Database.GetAppliedMigrationsAsync(cancellationToken)).Count(),
            lastGenerationRun = lastRun,
            generationStale,
            activeRecurrenceRules = activeRules,
            audit = new
            {
                totalEvents = auditTotal,
                oldestEventUtc = oldestAudit,
                generalRetentionMonths = AuditRetention.GeneralRetentionMonths,
                securityRetentionMonths = AuditRetention.SecurityRetentionMonths
            }
        });
    }

    private static async Task<IResult> FiltersAsync(AppDbContext database, CancellationToken cancellationToken)
    {
        var actions = await database.AuditEvents.AsNoTracking()
            .Select(item => item.Action).Distinct().OrderBy(value => value).ToArrayAsync(cancellationToken);
        var entityTypes = await database.AuditEvents.AsNoTracking()
            .Select(item => item.EntityType).Distinct().OrderBy(value => value).ToArrayAsync(cancellationToken);
        var actors = await database.AuditEvents.AsNoTracking()
            .Where(item => item.ActorUserId != null)
            .Select(item => item.ActorUserId!.Value).Distinct()
            .Join(database.Employees.AsNoTracking(), userId => userId, employee => employee.UserId,
                (userId, employee) => new { UserId = userId, employee.DisplayName })
            .OrderBy(item => item.DisplayName).ToArrayAsync(cancellationToken);

        return Results.Ok(new
        {
            actions,
            entityTypes,
            actors = actors.Select(item => new { userId = item.UserId, displayName = item.DisplayName }).ToArray()
        });
    }
}
