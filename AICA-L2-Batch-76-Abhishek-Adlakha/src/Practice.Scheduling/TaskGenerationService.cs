using System.Data;
using System.Data.Common;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;

namespace Practice.Scheduling;

public sealed record GenerationResult(Guid RunId, string Status, int Created, int Existing, int Skipped, int Errors);

public sealed class TaskGenerationService(AppDbContext database, IClock clock)
{
    private const long AdvisoryLockKey = 6_406_172_026;

    public async Task<GenerationResult> GenerateAsync(
        DateOnly windowFrom,
        DateOnly windowTo,
        string trigger,
        Guid? actorUserId,
        string workerId,
        CancellationToken cancellationToken)
    {
        if (windowTo < windowFrom || windowTo.DayNumber - windowFrom.DayNumber > 366)
        {
            throw new ArgumentOutOfRangeException(nameof(windowTo), "Generation windows must contain between 1 and 367 days.");
        }

        var connection = database.Database.GetDbConnection();
        var openedHere = connection.State != ConnectionState.Open;
        if (openedHere) await connection.OpenAsync(cancellationToken);
        try
        {
            if (!await TryAcquireLockAsync(connection, cancellationToken))
            {
                return await RecordLockedRunAsync(windowFrom, windowTo, trigger, actorUserId, workerId, cancellationToken);
            }

            try
            {
                try
                {
                    return await GenerateLockedAsync(windowFrom, windowTo, trigger, actorUserId, workerId, cancellationToken);
                }
                catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
                {
                    throw;
                }
                catch (Exception exception)
                {
                    database.ChangeTracker.Clear();
                    var failed = NewRun(windowFrom, windowTo, trigger, actorUserId, workerId, clock.UtcNow, "FAILED");
                    failed.FinishedAtUtc = clock.UtcNow;
                    failed.ErrorCount = 1;
                    failed.ErrorSummary = exception.Message[..Math.Min(exception.Message.Length, 2000)];
                    database.TaskGenerationRuns.Add(failed);
                    await database.SaveChangesAsync(cancellationToken);
                    return Result(failed);
                }
            }
            finally
            {
                await ReleaseLockAsync(connection, cancellationToken);
            }
        }
        finally
        {
            if (openedHere) await connection.CloseAsync();
        }
    }

    private async Task<GenerationResult> GenerateLockedAsync(
        DateOnly windowFrom,
        DateOnly windowTo,
        string trigger,
        Guid? actorUserId,
        string workerId,
        CancellationToken cancellationToken)
    {
        var now = clock.UtcNow;
        var today = DateOnly.FromDateTime(now.ToOffset(TimeSpan.FromHours(5.5)).DateTime);
        var run = NewRun(windowFrom, windowTo, trigger, actorUserId, workerId, now, "RUNNING");
        database.TaskGenerationRuns.Add(run);

        var rules = await database.RecurrenceRules
            .Include(item => item.ClientService).ThenInclude(item => item.Client)
            .Include(item => item.ClientService).ThenInclude(item => item.Service)
            .Include(item => item.Months)
            .Include(item => item.Exceptions)
            .Where(item => item.IsActive && item.ClientService.IsActive && item.ClientService.Client.Status == "ACTIVE" && item.ClientService.Service.IsActive)
            .Where(item => item.EffectiveFrom <= windowTo && (item.EffectiveTo == null || item.EffectiveTo >= windowFrom))
            .AsSplitQuery()
            .ToListAsync(cancellationToken);

        var calendarIds = rules.Select(item => item.HolidayCalendarId).Distinct().ToArray();
        var holidays = await database.Holidays.Where(item => calendarIds.Contains(item.HolidayCalendarId) && item.HolidayDate >= windowFrom.AddDays(-7) && item.HolidayDate <= windowTo.AddDays(7))
            .ToListAsync(cancellationToken);
        var holidayMaps = holidays.GroupBy(item => item.HolidayCalendarId).ToDictionary(
            group => group.Key,
            group => (IReadOnlyDictionary<DateOnly, bool>)group.ToDictionary(item => item.HolidayDate, item => item.IsWorkingDayOverride));

        var possibleKeys = rules.SelectMany(rule => RecurrenceCalculator.Calculate(rule, windowFrom, windowTo, holidayMaps.GetValueOrDefault(rule.HolidayCalendarId)))
            .Select(item => item.OccurrenceKey).ToArray();
        var existingKeys = possibleKeys.Length == 0
            ? new HashSet<string>(StringComparer.Ordinal)
            : (await database.Tasks.Where(item => item.OccurrenceKey != null && possibleKeys.Contains(item.OccurrenceKey)).Select(item => item.OccurrenceKey!).ToListAsync(cancellationToken)).ToHashSet(StringComparer.Ordinal);

        foreach (var rule in rules)
        {
            var calendar = holidayMaps.GetValueOrDefault(rule.HolidayCalendarId) ?? new Dictionary<DateOnly, bool>();
            foreach (var occurrence in RecurrenceCalculator.Calculate(rule, windowFrom, windowTo, calendar))
            {
                if (occurrence.GenerateOnDate > today)
                {
                    AddRunItem(run, rule, occurrence, "SKIPPED", null, "Lead date has not been reached.");
                    run.SkippedCount++;
                    continue;
                }

                var exception = rule.Exceptions.SingleOrDefault(item => item.PeriodStart == occurrence.PeriodStart && item.PeriodEnd == occurrence.PeriodEnd);
                if (exception?.Action == "SKIP")
                {
                    AddRunItem(run, rule, occurrence, "SKIPPED", null, exception.Reason);
                    run.SkippedCount++;
                    continue;
                }

                if (existingKeys.Contains(occurrence.OccurrenceKey))
                {
                    AddRunItem(run, rule, occurrence, "EXISTING", null, "Occurrence already exists.");
                    run.ExistingCount++;
                    continue;
                }

                var agreement = rule.ClientService;
                var taskId = Guid.NewGuid();
                var task = new PracticeTask
                {
                    Id = taskId,
                    ClientId = agreement.ClientId,
                    ServiceId = agreement.ServiceId,
                    ClientServiceId = agreement.Id,
                    GstRegistrationId = agreement.GstRegistrationId,
                    RecurrenceRuleId = rule.Id,
                    OccurrenceKey = occurrence.OccurrenceKey,
                    Title = exception?.OverrideTitle ?? agreement.TitleOverride ?? $"{agreement.Service.Name} · {occurrence.PeriodStart:MMM yyyy}",
                    PeriodStart = occurrence.PeriodStart,
                    PeriodEnd = occurrence.PeriodEnd,
                    DueDate = exception?.OverrideDueDate ?? occurrence.DueDate,
                    StatusId = TaskSeed.NotStartedId,
                    Priority = exception?.OverridePriority ?? agreement.DefaultPriority,
                    BillableSnapshot = agreement.Service.DefaultBillable,
                    CreatedSource = "RECURRENCE",
                    CreatedByUserId = actorUserId,
                    CreatedAtUtc = now,
                    UpdatedByUserId = actorUserId,
                    UpdatedAtUtc = now
                };
                task.StatusHistory.Add(new TaskStatusHistory
                {
                    Id = Guid.NewGuid(), TaskId = taskId, ToStatusId = TaskSeed.NotStartedId,
                    ActorUserId = actorUserId, ChangedAtUtc = now, Reason = "Generated from recurrence rule.",
                    MetadataJson = JsonSerializer.Serialize(new { ruleId = rule.Id, ruleVersion = rule.RuleVersion, occurrence.OccurrenceKey })
                });
                var assigneeId = exception?.OverridePrimaryAssigneeId ?? rule.DefaultPrimaryAssigneeId;
                if (assigneeId.HasValue)
                {
                    task.Assignments.Add(new TaskAssignment
                    {
                        Id = Guid.NewGuid(), TaskId = taskId, EmployeeId = assigneeId.Value,
                        AssignmentRole = "PRIMARY", AssignedAtUtc = now, AssignedByUserId = actorUserId,
                        Remarks = "Assigned by recurrence rule."
                    });
                }
                database.Tasks.Add(task);
                AddRunItem(run, rule, occurrence, "CREATED", taskId, null);
                existingKeys.Add(occurrence.OccurrenceKey);
                run.CreatedCount++;
            }
        }

        run.Status = "COMPLETED";
        run.FinishedAtUtc = clock.UtcNow;
        await database.SaveChangesAsync(cancellationToken);
        return Result(run);
    }

    private async Task<GenerationResult> RecordLockedRunAsync(DateOnly from, DateOnly to, string trigger, Guid? actor, string worker, CancellationToken cancellationToken)
    {
        var run = NewRun(from, to, trigger, actor, worker, clock.UtcNow, "SKIPPED_LOCKED");
        run.FinishedAtUtc = clock.UtcNow;
        run.ErrorSummary = "Another generator owns the scheduling lock.";
        database.TaskGenerationRuns.Add(run);
        await database.SaveChangesAsync(cancellationToken);
        return Result(run);
    }

    private static TaskGenerationRun NewRun(DateOnly from, DateOnly to, string trigger, Guid? actor, string worker, DateTimeOffset now, string status) => new()
    {
        Id = Guid.NewGuid(), WindowFrom = from, WindowTo = to, Trigger = trigger, Status = status,
        WorkerId = worker[..Math.Min(worker.Length, 150)], TriggeredByUserId = actor, StartedAtUtc = now
    };

    private static void AddRunItem(TaskGenerationRun run, RecurrenceRule rule, ScheduledOccurrence occurrence, string outcome, Guid? taskId, string? message) =>
        run.Items.Add(new TaskGenerationRunItem
        {
            RunId = run.Id, RecurrenceRuleId = rule.Id, OccurrenceKey = occurrence.OccurrenceKey,
            Outcome = outcome, TaskId = taskId, PeriodStart = occurrence.PeriodStart,
            PeriodEnd = occurrence.PeriodEnd, DueDate = occurrence.DueDate, Message = message
        });

    private static GenerationResult Result(TaskGenerationRun run) => new(run.Id, run.Status, run.CreatedCount, run.ExistingCount, run.SkippedCount, run.ErrorCount);

    private static async Task<bool> TryAcquireLockAsync(DbConnection connection, CancellationToken cancellationToken)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = "SELECT pg_try_advisory_lock(@lock_key)";
        var parameter = command.CreateParameter();
        parameter.ParameterName = "lock_key";
        parameter.Value = AdvisoryLockKey;
        command.Parameters.Add(parameter);
        return (bool)(await command.ExecuteScalarAsync(cancellationToken) ?? false);
    }

    private static async Task ReleaseLockAsync(DbConnection connection, CancellationToken cancellationToken)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = "SELECT pg_advisory_unlock(@lock_key)";
        var parameter = command.CreateParameter();
        parameter.ParameterName = "lock_key";
        parameter.Value = AdvisoryLockKey;
        command.Parameters.Add(parameter);
        await command.ExecuteScalarAsync(cancellationToken);
    }
}
