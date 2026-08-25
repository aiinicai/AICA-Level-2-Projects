namespace Practice.Database.Entities;

public sealed class IndiaState
{
    public required string GstCode { get; set; }
    public required string Name { get; set; }
    public bool IsUnionTerritory { get; set; }
    public bool IsActive { get; set; } = true;
}

public sealed class AppSetting
{
    public required string Key { get; set; }
    public required string ValueJson { get; set; }
    public required string Description { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
}

public sealed class HolidayCalendar
{
    public Guid Id { get; set; }
    public required string Code { get; set; }
    public required string Name { get; set; }
    public required string TimeZoneId { get; set; }
    public string? RegionCode { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTimeOffset CreatedAtUtc { get; set; }
    public ICollection<Holiday> Holidays { get; } = new List<Holiday>();
}

public sealed class Holiday
{
    public Guid Id { get; set; }
    public Guid HolidayCalendarId { get; set; }
    public HolidayCalendar HolidayCalendar { get; set; } = null!;
    public DateOnly HolidayDate { get; set; }
    public required string Name { get; set; }
    public required string HolidayType { get; set; }
    public bool IsWorkingDayOverride { get; set; }
    public string? Notes { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
}

public sealed class AuditEvent
{
    public Guid Id { get; set; }
    public DateTimeOffset OccurredAtUtc { get; set; }
    public Guid? ActorUserId { get; set; }
    public required string Action { get; set; }
    public required string EntityType { get; set; }
    public string? EntityId { get; set; }
    public string? Reason { get; set; }
    public string? CorrelationId { get; set; }
    public required string DataJson { get; set; }
}

public sealed class OutboxMessage
{
    public Guid Id { get; set; }
    public DateTimeOffset OccurredAtUtc { get; set; }
    public required string MessageType { get; set; }
    public required string PayloadJson { get; set; }
    public DateTimeOffset? ProcessedAtUtc { get; set; }
    public DateTimeOffset? NextAttemptAtUtc { get; set; }
    public int AttemptCount { get; set; }
    public string? LastError { get; set; }
}

public sealed class ImportRun
{
    public Guid Id { get; set; }
    public required string SourceFileName { get; set; }
    public required string SourceSha256 { get; set; }
    public required string Mode { get; set; }
    public required string Status { get; set; }
    public DateTimeOffset StartedAtUtc { get; set; }
    public DateTimeOffset? CompletedAtUtc { get; set; }
    public long SourceSizeBytes { get; set; }
    public string? ReportJson { get; set; }
    public string? ErrorSummary { get; set; }
    public ICollection<ImportIssue> Issues { get; } = new List<ImportIssue>();
}

public sealed class ImportIssue
{
    public long Id { get; set; }
    public Guid ImportRunId { get; set; }
    public ImportRun ImportRun { get; set; } = null!;
    public required string Severity { get; set; }
    public required string IssueCode { get; set; }
    public string? SheetName { get; set; }
    public int? RowNumber { get; set; }
    public string? ColumnName { get; set; }
    public string? RawValue { get; set; }
    public string? NormalizedValue { get; set; }
    public required string Message { get; set; }
}
