using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.DependencyInjection;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Scheduling;

namespace Practice.Worker;

public sealed record WorkerOptions(bool RunOnce);

public sealed partial class Worker(
    ILogger<Worker> logger,
    IClock clock,
    IServiceScopeFactory scopeFactory,
    IHostApplicationLifetime lifetime,
    IConfiguration configuration,
    WorkerOptions options) : BackgroundService
{
    private static readonly TimeSpan RetentionInterval = TimeSpan.FromHours(24);
    private DateTimeOffset _lastRetentionUtc = DateTimeOffset.MinValue;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        LogWorkerStarted(logger, clock.UtcNow);
        await GenerateAsync(stoppingToken);
        await ApplyRetentionAsync(stoppingToken);
        if (options.RunOnce)
        {
            lifetime.StopApplication();
            return;
        }

        // Generation stays on its six-hour cycle; retention only needs a daily pass, so the same
        // timer drives both and retention skips ticks until a day has elapsed.
        using var timer = new PeriodicTimer(TimeSpan.FromHours(6));
        while (await timer.WaitForNextTickAsync(stoppingToken))
        {
            await GenerateAsync(stoppingToken);
            await ApplyRetentionAsync(stoppingToken);
        }
    }

    private async Task ApplyRetentionAsync(CancellationToken cancellationToken)
    {
        if (clock.UtcNow - _lastRetentionUtc < RetentionInterval)
        {
            return;
        }

        try
        {
            await using var scope = scopeFactory.CreateAsyncScope();
            var retention = scope.ServiceProvider.GetRequiredService<AuditRetentionService>();
            var result = await retention.RunAsync(
                configuration.GetConnectionString(AuditRetentionService.MaintenanceConnectionName),
                configuration[AuditRetentionService.ArchivePathSetting],
                cancellationToken);
            _lastRetentionUtc = clock.UtcNow;
            if (result.Status == "NOT_CONFIGURED")
            {
                LogRetentionNotConfigured(logger);
            }
            else
            {
                LogRetentionFinished(logger, result.Status, result.ArchivedCount, result.DeletedCount, result.ArchiveFile);
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception exception)
        {
            // A failed purge must never stop generation, and must never leave rows deleted without
            // an archive: the service writes the file before it deletes anything.
            LogRetentionFailed(logger, exception);
        }
    }

    private async Task GenerateAsync(CancellationToken cancellationToken)
    {
        try
        {
            await using var scope = scopeFactory.CreateAsyncScope();
            var generator = scope.ServiceProvider.GetRequiredService<TaskGenerationService>();
            var today = DateOnly.FromDateTime(clock.UtcNow.ToOffset(TimeSpan.FromHours(5.5)).DateTime);
            var result = await generator.GenerateAsync(today.AddDays(-30), today.AddDays(45), "SCHEDULED", null, $"worker:{Environment.MachineName}", cancellationToken);
            LogGenerationFinished(logger, result.RunId, result.Status, result.Created, result.Existing, result.Skipped, result.Errors);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception exception)
        {
            LogGenerationFailed(logger, exception);
        }
    }

    [LoggerMessage(
        EventId = 1000,
        Level = LogLevel.Information,
        Message = "Phase 6 scheduling worker started at {StartedAt}.")]
    private static partial void LogWorkerStarted(ILogger logger, DateTimeOffset startedAt);

    [LoggerMessage(EventId = 1001, Level = LogLevel.Information, Message = "Generation run {RunId} finished with {Status}: {Created} created, {Existing} existing, {Skipped} skipped, {Errors} errors.")]
    private static partial void LogGenerationFinished(ILogger logger, Guid runId, string status, int created, int existing, int skipped, int errors);

    [LoggerMessage(EventId = 1002, Level = LogLevel.Error, Message = "Scheduled task generation failed.")]
    private static partial void LogGenerationFailed(ILogger logger, Exception exception);

    [LoggerMessage(EventId = 1003, Level = LogLevel.Information, Message = "Audit retention finished with {Status}: {Archived} archived, {Deleted} deleted to {ArchiveFile}.")]
    private static partial void LogRetentionFinished(ILogger logger, string status, int archived, int deleted, string? archiveFile);

    [LoggerMessage(EventId = 1004, Level = LogLevel.Warning, Message = "Audit retention is not configured; no audit history will be archived or removed.")]
    private static partial void LogRetentionNotConfigured(ILogger logger);

    [LoggerMessage(EventId = 1005, Level = LogLevel.Error, Message = "Audit retention failed. No audit rows were deleted without a written archive.")]
    private static partial void LogRetentionFailed(ILogger logger, Exception exception);
}
