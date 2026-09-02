namespace Practice.BuildingBlocks.Auditing;

public interface IAuditWriter
{
    Task WriteAsync(AuditRecord record, CancellationToken cancellationToken = default);
}

public sealed record AuditRecord(
    string Action,
    string EntityType,
    string? EntityId = null,
    Guid? ActorUserId = null,
    string? Reason = null,
    string? DataJson = null,
    string? CorrelationId = null);
