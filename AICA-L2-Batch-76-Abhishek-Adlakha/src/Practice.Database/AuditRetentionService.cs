using System.Globalization;
using System.Text.Json;
using Npgsql;
using Practice.BuildingBlocks.Clock;

namespace Practice.Database;

public sealed record AuditRetentionResult(string Status, int ArchivedCount, int DeletedCount, string? ArchiveFile);

// Audit rows are append-only for the application: the runtime database role holds only SELECT and
// INSERT on the audit schema, so neither the API nor a compromised worker can erase history. This
// maintenance job therefore runs on its own elevated connection, which is configured separately
// and is absent by default. Nothing is ever deleted before it has been written to an archive file
// and that file has been flushed to disk.
public sealed class AuditRetentionService(IClock clock)
{
    public const string MaintenanceConnectionName = "PracticeAuditMaintenance";
    public const string ArchivePathSetting = "Audit:ArchivePath";

    public async Task<AuditRetentionResult> RunAsync(
        string? maintenanceConnectionString,
        string? archiveDirectory,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(maintenanceConnectionString) || string.IsNullOrWhiteSpace(archiveDirectory))
        {
            return new AuditRetentionResult("NOT_CONFIGURED", 0, 0, null);
        }

        var now = clock.UtcNow;
        var generalCutoff = now.AddMonths(-AuditRetention.GeneralRetentionMonths);
        var securityCutoff = now.AddMonths(-AuditRetention.SecurityRetentionMonths);

        await using var connection = new NpgsqlConnection(maintenanceConnectionString);
        await connection.OpenAsync(cancellationToken);

        var expired = await ReadExpiredAsync(connection, generalCutoff, securityCutoff, cancellationToken);
        if (expired.Count == 0)
        {
            return new AuditRetentionResult("NOTHING_EXPIRED", 0, 0, null);
        }

        Directory.CreateDirectory(archiveDirectory);
        var fileName = FormattableString.Invariant($"audit-archive-{now:yyyyMMdd-HHmmss}.jsonl");
        var archiveFile = Path.Combine(archiveDirectory, fileName);

        // Write and flush before deleting anything. If this throws, the rows stay in the database.
        await using (var stream = new FileStream(archiveFile, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        await using (var writer = new StreamWriter(stream))
        {
            foreach (var row in expired)
            {
                await writer.WriteLineAsync(JsonSerializer.Serialize(row).AsMemory(), cancellationToken);
            }
            await writer.FlushAsync(cancellationToken);
            await stream.FlushAsync(cancellationToken);
        }

        if (!File.Exists(archiveFile) || new FileInfo(archiveFile).Length == 0)
        {
            return new AuditRetentionResult("ARCHIVE_FAILED", 0, 0, null);
        }

        var deleted = await DeleteAsync(connection, expired.Select(row => row.Id).ToArray(), cancellationToken);
        return new AuditRetentionResult("PURGED", expired.Count, deleted, archiveFile);
    }

    private static async Task<List<ArchivedAuditEvent>> ReadExpiredAsync(
        NpgsqlConnection connection, DateTimeOffset generalCutoff, DateTimeOffset securityCutoff, CancellationToken cancellationToken)
    {
        const string sql = """
            SELECT id, occurred_at_utc, actor_user_id, action, entity_type, entity_id, reason, correlation_id, data_json
            FROM audit.audit_events
            WHERE occurred_at_utc < CASE
                WHEN action LIKE 'identity.%' OR action = ANY(@security) THEN @securityCutoff
                ELSE @generalCutoff
            END
            ORDER BY occurred_at_utc
            """;
        await using var command = new NpgsqlCommand(sql, connection);
        command.Parameters.AddWithValue("security", AuditRetention.SecurityActionList().ToArray());
        command.Parameters.AddWithValue("securityCutoff", securityCutoff);
        command.Parameters.AddWithValue("generalCutoff", generalCutoff);

        var rows = new List<ArchivedAuditEvent>();
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        while (await reader.ReadAsync(cancellationToken))
        {
            rows.Add(new ArchivedAuditEvent(
                reader.GetGuid(0),
                reader.GetFieldValue<DateTimeOffset>(1).ToString("O", CultureInfo.InvariantCulture),
                await reader.IsDBNullAsync(2, cancellationToken) ? null : reader.GetGuid(2),
                reader.GetString(3),
                reader.GetString(4),
                await reader.IsDBNullAsync(5, cancellationToken) ? null : reader.GetString(5),
                await reader.IsDBNullAsync(6, cancellationToken) ? null : reader.GetString(6),
                await reader.IsDBNullAsync(7, cancellationToken) ? null : reader.GetString(7),
                reader.GetString(8)));
        }
        return rows;
    }

    private static async Task<int> DeleteAsync(NpgsqlConnection connection, Guid[] ids, CancellationToken cancellationToken)
    {
        await using var command = new NpgsqlCommand("DELETE FROM audit.audit_events WHERE id = ANY(@ids)", connection);
        command.Parameters.AddWithValue("ids", ids);
        return await command.ExecuteNonQueryAsync(cancellationToken);
    }

    private sealed record ArchivedAuditEvent(
        Guid Id, string OccurredAtUtc, Guid? ActorUserId, string Action,
        string EntityType, string? EntityId, string? Reason, string? CorrelationId, string DataJson);
}
