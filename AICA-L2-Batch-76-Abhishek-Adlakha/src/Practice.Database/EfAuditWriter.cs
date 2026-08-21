using Practice.BuildingBlocks.Auditing;
using Practice.BuildingBlocks.Clock;
using Practice.Database.Entities;

namespace Practice.Database;

internal sealed class EfAuditWriter(AppDbContext database, IClock clock) : IAuditWriter
{
    public async Task WriteAsync(AuditRecord record, CancellationToken cancellationToken = default)
    {
        database.AuditEvents.Add(new AuditEvent
        {
            Id = Guid.NewGuid(),
            OccurredAtUtc = clock.UtcNow,
            ActorUserId = record.ActorUserId,
            Action = record.Action,
            EntityType = record.EntityType,
            EntityId = record.EntityId,
            Reason = record.Reason,
            CorrelationId = record.CorrelationId,
            DataJson = record.DataJson ?? "{}"
        });

        await database.SaveChangesAsync(cancellationToken);
    }
}
